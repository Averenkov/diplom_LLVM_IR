#include "llvm/IR/Function.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Module.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <system_error>
#include <utility>
#include <vector>

using namespace llvm;

namespace {

cl::opt<double> TopFraction(
    "top-fraction",
    cl::desc("Fraction of the largest functions to select"),
    cl::init(0.20));

cl::opt<std::string> TopOutputPath(
    "top20-output",
    cl::desc("Write analysis results to a JSON file"),
    cl::init(""));

struct FunctionStat {
  std::string Name;
  uint64_t InstructionCount;
};

double computeSharePercent(uint64_t Part, uint64_t Whole) {
  if (Whole == 0)
    return 0.0;
  return 100.0 * static_cast<double>(Part) / static_cast<double>(Whole);
}

double computeStdDev(const std::vector<FunctionStat> &FuncCounts, double Mean) {
  if (FuncCounts.empty())
    return 0.0;

  double Variance = 0.0;
  for (const auto &Func : FuncCounts) {
    const double Delta = static_cast<double>(Func.InstructionCount) - Mean;
    Variance += Delta * Delta;
  }
  Variance /= static_cast<double>(FuncCounts.size());
  return std::sqrt(Variance);
}

double computeMedian(const std::vector<FunctionStat> &SortedAscending) {
  if (SortedAscending.empty())
    return 0.0;

  const size_t N = SortedAscending.size();
  if (N % 2 == 1)
    return static_cast<double>(SortedAscending[N / 2].InstructionCount);

  return (static_cast<double>(SortedAscending[(N / 2) - 1].InstructionCount) +
          static_cast<double>(SortedAscending[N / 2].InstructionCount)) /
         2.0;
}

double computeHHI(const std::vector<FunctionStat> &FuncCounts, uint64_t Total) {
  if (FuncCounts.empty() || Total == 0)
    return 0.0;

  double HHI = 0.0;
  for (const auto &Func : FuncCounts) {
    const double Share =
        static_cast<double>(Func.InstructionCount) / static_cast<double>(Total);
    HHI += Share * Share;
  }
  return HHI;
}

double computeGini(const std::vector<FunctionStat> &SortedAscending,
                   uint64_t Total) {
  if (SortedAscending.empty() || Total == 0)
    return 0.0;

  const size_t N = SortedAscending.size();
  double WeightedSum = 0.0;
  for (size_t I = 0; I < N; ++I)
    WeightedSum += (static_cast<double>(I) + 1.0) *
                   static_cast<double>(SortedAscending[I].InstructionCount);

  const double Numerator =
      2.0 * WeightedSum / static_cast<double>(Total) - static_cast<double>(N) - 1.0;
  return Numerator / static_cast<double>(N);
}

uint64_t sumTopN(const std::vector<FunctionStat> &FuncCounts, size_t Count) {
  const size_t Limit = std::min(Count, FuncCounts.size());
  uint64_t Sum = 0;
  for (size_t I = 0; I < Limit; ++I)
    Sum += FuncCounts[I].InstructionCount;
  return Sum;
}

struct Top20BiggestFuncsPass : PassInfoMixin<Top20BiggestFuncsPass> {
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &) {
    std::vector<FunctionStat> FuncCounts;
    FuncCounts.reserve(M.size());

    for (Function &F : M) {
      if (F.isDeclaration())
        continue;

      uint64_t Cnt = 0;
      for (Instruction &I : instructions(F)) {
        (void)I;
        ++Cnt;
      }

      FuncCounts.push_back({F.getName().str(), Cnt});
    }

    if (FuncCounts.empty()) {
      errs() << "[top20] no defined functions\n";
      return PreservedAnalyses::all();
    }

    std::sort(FuncCounts.begin(), FuncCounts.end(),
              [](const auto &A, const auto &B) {
                return A.InstructionCount > B.InstructionCount;
              });

    const size_t N = FuncCounts.size();
    const double Fraction = std::clamp(TopFraction.getValue(), 0.0, 1.0);
    const size_t K = std::max<size_t>(1, (size_t)std::ceil(Fraction * (double)N));

    uint64_t Total = 0;
    for (const auto &Func : FuncCounts)
      Total += Func.InstructionCount;

    errs() << "[top20] functions defined: " << N << "\n";
    errs() << "[top20] selecting top " << K << " ("
           << (Fraction * 100.0) << "%)\n";

    uint64_t TopSum = 0;
    for (size_t I = 0; I < K; ++I)
      TopSum += FuncCounts[I].InstructionCount;

    errs() << "[top20] total IR insts: " << Total
           << ", top sum: " << TopSum
           << " (" << computeSharePercent(TopSum, Total) << "%)\n";

    errs() << "[top20] Top functions by IR instruction count:\n";
    for (size_t I = 0; I < K; ++I) {
      errs() << "  " << (I + 1) << ") " << FuncCounts[I].Name
             << " : " << FuncCounts[I].InstructionCount << "\n";
    }

    if (!TopOutputPath.empty()) {
      const double Mean = static_cast<double>(Total) / static_cast<double>(N);
      std::vector<FunctionStat> AscendingFuncCounts = FuncCounts;
      std::sort(AscendingFuncCounts.begin(), AscendingFuncCounts.end(),
                [](const auto &A, const auto &B) {
                  return A.InstructionCount < B.InstructionCount;
                });

      const double Median = computeMedian(AscendingFuncCounts);
      const double StdDev = computeStdDev(FuncCounts, Mean);
      const uint64_t Top1Sum = sumTopN(FuncCounts, 1);
      const uint64_t Top3Sum = sumTopN(FuncCounts, 3);
      const uint64_t Top5Sum = sumTopN(FuncCounts, 5);
      const double HHI = computeHHI(FuncCounts, Total);
      const double Gini = computeGini(AscendingFuncCounts, Total);

      json::Array TopFunctions;
      for (size_t I = 0; I < K; ++I) {
        json::Object Func{
            {"rank", static_cast<int64_t>(I + 1)},
            {"name", FuncCounts[I].Name},
            {"instruction_count",
             static_cast<int64_t>(FuncCounts[I].InstructionCount)},
            {"module_share_percent",
             computeSharePercent(FuncCounts[I].InstructionCount, Total)},
            {"selected_weight_percent",
             computeSharePercent(FuncCounts[I].InstructionCount, TopSum)},
        };
        TopFunctions.emplace_back(std::move(Func));
      }

      json::Object TranslationUnitAggregation{
          {"aggregation_scope", "translation_unit"},
          {"aggregation_method", "weighted-top-fraction-by-ir-count"},
          {"aggregation_basis", "llvm_ir_instruction_count"},
          {"selection_fraction", Fraction},
          {"selected_function_count", static_cast<int64_t>(K)},
          {"selected_ir_share_percent", computeSharePercent(TopSum, Total)},
          {"dominant_function_share_percent", computeSharePercent(Top1Sum, Total)},
          {"top_3_share_percent", computeSharePercent(Top3Sum, Total)},
          {"top_5_share_percent", computeSharePercent(Top5Sum, Total)},
          {"mean_function_size", Mean},
          {"median_function_size", Median},
          {"stddev_function_size", StdDev},
          {"size_concentration_hhi", HHI},
          {"size_gini", Gini},
      };

      json::Object Root{
          {"module_name", M.getModuleIdentifier()},
          {"functions_defined", static_cast<int64_t>(N)},
          {"selected_count", static_cast<int64_t>(K)},
          {"fraction", Fraction},
          {"total_ir_insts", static_cast<int64_t>(Total)},
          {"selected_ir_insts", static_cast<int64_t>(TopSum)},
          {"selected_share_percent", computeSharePercent(TopSum, Total)},
          {"translation_unit_aggregation",
           std::move(TranslationUnitAggregation)},
          {"top_functions", std::move(TopFunctions)},
      };

      std::error_code EC;
      raw_fd_ostream OS(TopOutputPath, EC, sys::fs::OF_Text);
      if (EC) {
        errs() << "[top20] failed to open JSON output '" << TopOutputPath
               << "': " << EC.message() << "\n";
      } else {
        OS << formatv("{0:2}\n", json::Value(std::move(Root)));
      }
    }

    return PreservedAnalyses::all();
  }
};

}

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
  return {LLVM_PLUGIN_API_VERSION, "top20-biggest-funcs", LLVM_VERSION_STRING,
          [](PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](StringRef Name, ModulePassManager &MPM,
                   ArrayRef<PassBuilder::PipelineElement>) {
                  if (Name == "top20-biggest-funcs") {
                    MPM.addPass(Top20BiggestFuncsPass());
                    return true;
                  }
                  return false;
                });
          }};
}
