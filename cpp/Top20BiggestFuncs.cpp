#include "llvm/IR/Function.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Instructions.h"
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
  uint64_t BasicBlockCount;
  uint64_t BranchCount;
  uint64_t ConditionalBranchCount;
  uint64_t SwitchCount;
  uint64_t CallCount;
  uint64_t LoadCount;
  uint64_t StoreCount;
  uint64_t AllocaCount;
  uint64_t PhiCount;
  uint64_t GetElementPtrCount;
  uint64_t CastCount;
  uint64_t CompareCount;
  uint64_t SelectCount;
  uint64_t ReturnCount;
  uint64_t IntegerOpCount;
  uint64_t FloatOpCount;
  uint64_t VectorOpCount;
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

bool isIntegerArithmeticOrBitwise(const Instruction &I) {
  switch (I.getOpcode()) {
  case Instruction::Add:
  case Instruction::Sub:
  case Instruction::Mul:
  case Instruction::UDiv:
  case Instruction::SDiv:
  case Instruction::URem:
  case Instruction::SRem:
  case Instruction::Shl:
  case Instruction::LShr:
  case Instruction::AShr:
  case Instruction::And:
  case Instruction::Or:
  case Instruction::Xor:
    return true;
  default:
    return false;
  }
}

bool isFloatArithmetic(const Instruction &I) {
  switch (I.getOpcode()) {
  case Instruction::FAdd:
  case Instruction::FSub:
  case Instruction::FMul:
  case Instruction::FDiv:
  case Instruction::FRem:
    return true;
  default:
    return false;
  }
}

bool touchesVectorType(const Instruction &I) {
  if (I.getType()->isVectorTy())
    return true;
  for (const Use &Operand : I.operands()) {
    if (Operand->getType()->isVectorTy())
      return true;
  }
  return false;
}

double computeDensity(uint64_t Part, uint64_t Whole) {
  if (Whole == 0)
    return 0.0;
  return static_cast<double>(Part) / static_cast<double>(Whole);
}

json::Object makeFunctionObject(const FunctionStat &Func, size_t Rank,
                                uint64_t Total, uint64_t SelectedTotal,
                                bool IncludeSelectedWeight) {
  json::Object Result{
      {"rank", static_cast<int64_t>(Rank + 1)},
      {"name", Func.Name},
      {"instruction_count", static_cast<int64_t>(Func.InstructionCount)},
      {"module_share_percent", computeSharePercent(Func.InstructionCount, Total)},
      {"basic_blocks", static_cast<int64_t>(Func.BasicBlockCount)},
      {"branches", static_cast<int64_t>(Func.BranchCount)},
      {"conditional_branches", static_cast<int64_t>(Func.ConditionalBranchCount)},
      {"switches", static_cast<int64_t>(Func.SwitchCount)},
      {"calls", static_cast<int64_t>(Func.CallCount)},
      {"loads", static_cast<int64_t>(Func.LoadCount)},
      {"stores", static_cast<int64_t>(Func.StoreCount)},
      {"allocas", static_cast<int64_t>(Func.AllocaCount)},
      {"phi_nodes", static_cast<int64_t>(Func.PhiCount)},
      {"getelementptrs", static_cast<int64_t>(Func.GetElementPtrCount)},
      {"casts", static_cast<int64_t>(Func.CastCount)},
      {"compares", static_cast<int64_t>(Func.CompareCount)},
      {"selects", static_cast<int64_t>(Func.SelectCount)},
      {"returns", static_cast<int64_t>(Func.ReturnCount)},
      {"integer_ops", static_cast<int64_t>(Func.IntegerOpCount)},
      {"float_ops", static_cast<int64_t>(Func.FloatOpCount)},
      {"vector_ops", static_cast<int64_t>(Func.VectorOpCount)},
      {"memory_ops",
       static_cast<int64_t>(Func.LoadCount + Func.StoreCount +
                            Func.AllocaCount + Func.GetElementPtrCount)},
      {"call_density", computeDensity(Func.CallCount, Func.InstructionCount)},
      {"memory_density",
       computeDensity(Func.LoadCount + Func.StoreCount + Func.AllocaCount +
                          Func.GetElementPtrCount,
                      Func.InstructionCount)},
      {"branch_density", computeDensity(Func.BranchCount + Func.SwitchCount,
                                        Func.InstructionCount)},
      {"conditional_branch_density",
       computeDensity(Func.ConditionalBranchCount + Func.SwitchCount,
                      Func.InstructionCount)},
      {"phi_density", computeDensity(Func.PhiCount, Func.InstructionCount)},
      {"vector_density", computeDensity(Func.VectorOpCount, Func.InstructionCount)},
      {"float_density", computeDensity(Func.FloatOpCount, Func.InstructionCount)},
      {"integer_density", computeDensity(Func.IntegerOpCount, Func.InstructionCount)},
  };
  if (IncludeSelectedWeight) {
    Result["selected_weight_percent"] =
        computeSharePercent(Func.InstructionCount, SelectedTotal);
  }
  return Result;
}

json::Object makeSemanticProfile(const std::vector<FunctionStat> &FuncCounts,
                                 size_t Count) {
  const size_t Limit = std::min(Count, FuncCounts.size());
  uint64_t Insts = 0;
  uint64_t BasicBlocks = 0;
  uint64_t Branches = 0;
  uint64_t ConditionalBranches = 0;
  uint64_t Switches = 0;
  uint64_t Calls = 0;
  uint64_t Loads = 0;
  uint64_t Stores = 0;
  uint64_t Allocas = 0;
  uint64_t Phis = 0;
  uint64_t GEPs = 0;
  uint64_t Casts = 0;
  uint64_t Compares = 0;
  uint64_t Selects = 0;
  uint64_t Returns = 0;
  uint64_t IntegerOps = 0;
  uint64_t FloatOps = 0;
  uint64_t VectorOps = 0;

  for (size_t I = 0; I < Limit; ++I) {
    const auto &Func = FuncCounts[I];
    Insts += Func.InstructionCount;
    BasicBlocks += Func.BasicBlockCount;
    Branches += Func.BranchCount;
    ConditionalBranches += Func.ConditionalBranchCount;
    Switches += Func.SwitchCount;
    Calls += Func.CallCount;
    Loads += Func.LoadCount;
    Stores += Func.StoreCount;
    Allocas += Func.AllocaCount;
    Phis += Func.PhiCount;
    GEPs += Func.GetElementPtrCount;
    Casts += Func.CastCount;
    Compares += Func.CompareCount;
    Selects += Func.SelectCount;
    Returns += Func.ReturnCount;
    IntegerOps += Func.IntegerOpCount;
    FloatOps += Func.FloatOpCount;
    VectorOps += Func.VectorOpCount;
  }

  const uint64_t MemoryOps = Loads + Stores + Allocas + GEPs;
  const uint64_t BranchOps = Branches + Switches;
  const double FunctionCount = static_cast<double>(Limit);
  const double BasicBlocksPerFunction =
      FunctionCount == 0.0 ? 0.0 : static_cast<double>(BasicBlocks) / FunctionCount;
  const double LoopLikeScore =
      computeDensity(Phis + ConditionalBranches, Insts);

  return json::Object{
      {"function_count", static_cast<int64_t>(Limit)},
      {"instruction_count", static_cast<int64_t>(Insts)},
      {"basic_blocks", static_cast<int64_t>(BasicBlocks)},
      {"branches", static_cast<int64_t>(Branches)},
      {"conditional_branches", static_cast<int64_t>(ConditionalBranches)},
      {"switches", static_cast<int64_t>(Switches)},
      {"calls", static_cast<int64_t>(Calls)},
      {"loads", static_cast<int64_t>(Loads)},
      {"stores", static_cast<int64_t>(Stores)},
      {"allocas", static_cast<int64_t>(Allocas)},
      {"phi_nodes", static_cast<int64_t>(Phis)},
      {"getelementptrs", static_cast<int64_t>(GEPs)},
      {"casts", static_cast<int64_t>(Casts)},
      {"compares", static_cast<int64_t>(Compares)},
      {"selects", static_cast<int64_t>(Selects)},
      {"returns", static_cast<int64_t>(Returns)},
      {"integer_ops", static_cast<int64_t>(IntegerOps)},
      {"float_ops", static_cast<int64_t>(FloatOps)},
      {"vector_ops", static_cast<int64_t>(VectorOps)},
      {"memory_ops", static_cast<int64_t>(MemoryOps)},
      {"call_density", computeDensity(Calls, Insts)},
      {"memory_density", computeDensity(MemoryOps, Insts)},
      {"branch_density", computeDensity(BranchOps, Insts)},
      {"conditional_branch_density",
       computeDensity(ConditionalBranches + Switches, Insts)},
      {"phi_density", computeDensity(Phis, Insts)},
      {"alloca_density", computeDensity(Allocas, Insts)},
      {"vector_density", computeDensity(VectorOps, Insts)},
      {"float_density", computeDensity(FloatOps, Insts)},
      {"integer_density", computeDensity(IntegerOps, Insts)},
      {"compare_density", computeDensity(Compares, Insts)},
      {"select_density", computeDensity(Selects, Insts)},
      {"basic_blocks_per_function", BasicBlocksPerFunction},
      {"loop_like_score", LoopLikeScore},
  };
}

struct Top20BiggestFuncsPass : PassInfoMixin<Top20BiggestFuncsPass> {
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &) {
    std::vector<FunctionStat> FuncCounts;
    FuncCounts.reserve(M.size());

    for (Function &F : M) {
      if (F.isDeclaration())
        continue;

      FunctionStat Stat{};
      Stat.Name = F.getName().str();
      Stat.BasicBlockCount = F.size();
      for (Instruction &I : instructions(F)) {
        ++Stat.InstructionCount;
        if (isa<BranchInst>(I)) {
          ++Stat.BranchCount;
          if (cast<BranchInst>(I).isConditional())
            ++Stat.ConditionalBranchCount;
        }
        if (isa<SwitchInst>(I))
          ++Stat.SwitchCount;
        if (isa<CallBase>(I))
          ++Stat.CallCount;
        if (isa<LoadInst>(I))
          ++Stat.LoadCount;
        if (isa<StoreInst>(I))
          ++Stat.StoreCount;
        if (isa<AllocaInst>(I))
          ++Stat.AllocaCount;
        if (isa<PHINode>(I))
          ++Stat.PhiCount;
        if (isa<GetElementPtrInst>(I))
          ++Stat.GetElementPtrCount;
        if (I.isCast())
          ++Stat.CastCount;
        if (isa<CmpInst>(I))
          ++Stat.CompareCount;
        if (isa<SelectInst>(I))
          ++Stat.SelectCount;
        if (isa<ReturnInst>(I))
          ++Stat.ReturnCount;
        if (isIntegerArithmeticOrBitwise(I))
          ++Stat.IntegerOpCount;
        if (isFloatArithmetic(I))
          ++Stat.FloatOpCount;
        if (touchesVectorType(I))
          ++Stat.VectorOpCount;
      }

      FuncCounts.push_back(std::move(Stat));
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
        TopFunctions.emplace_back(
            makeFunctionObject(FuncCounts[I], I, Total, TopSum, true));
      }

      json::Array FunctionInstructionCounts;
      for (size_t I = 0; I < FuncCounts.size(); ++I) {
        FunctionInstructionCounts.emplace_back(
            makeFunctionObject(FuncCounts[I], I, Total, TopSum, false));
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
          {"module_semantic_profile",
           makeSemanticProfile(FuncCounts, FuncCounts.size())},
          {"selected_semantic_profile", makeSemanticProfile(FuncCounts, K)},
          {"translation_unit_aggregation",
           std::move(TranslationUnitAggregation)},
          {"top_functions", std::move(TopFunctions)},
          {"function_instruction_counts", std::move(FunctionInstructionCounts)},
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
