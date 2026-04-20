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

struct Top20BiggestFuncsPass : PassInfoMixin<Top20BiggestFuncsPass> {
  PreservedAnalyses run(Module &M, ModuleAnalysisManager &) {
    std::vector<std::pair<std::string, uint64_t>> FuncCounts;
    FuncCounts.reserve(M.size());

    for (Function &F : M) {
      if (F.isDeclaration())
        continue;

      uint64_t Cnt = 0;
      for (Instruction &I : instructions(F)) {
        (void)I;
        ++Cnt;
      }

      FuncCounts.emplace_back(F.getName().str(), Cnt);
    }

    if (FuncCounts.empty()) {
      errs() << "[top20] no defined functions\n";
      return PreservedAnalyses::all();
    }

    std::sort(FuncCounts.begin(), FuncCounts.end(),
              [](auto &a, auto &b) { return a.second > b.second; });

    const size_t N = FuncCounts.size();
    const double Fraction = std::clamp(TopFraction.getValue(), 0.0, 1.0);
    const size_t K = std::max<size_t>(1, (size_t)std::ceil(Fraction * (double)N));

    uint64_t Total = 0;
    for (auto &p : FuncCounts) Total += p.second;

    errs() << "[top20] functions defined: " << N << "\n";
    errs() << "[top20] selecting top " << K << " ("
           << (Fraction * 100.0) << "%)\n";

    uint64_t TopSum = 0;
    for (size_t i = 0; i < K; ++i) TopSum += FuncCounts[i].second;

    errs() << "[top20] total IR insts: " << Total
           << ", top sum: " << TopSum
           << " (" << (100.0 * (double)TopSum / (double)Total) << "%)\n";

    errs() << "[top20] Top functions by IR instruction count:\n";
    for (size_t i = 0; i < K; ++i) {
      errs() << "  " << (i + 1) << ") " << FuncCounts[i].first
             << " : " << FuncCounts[i].second << "\n";
    }

    if (!TopOutputPath.empty()) {
      json::Array TopFunctions;
      for (size_t i = 0; i < K; ++i) {
        json::Object Func{
            {"rank", static_cast<int64_t>(i + 1)},
            {"name", FuncCounts[i].first},
            {"instruction_count", static_cast<int64_t>(FuncCounts[i].second)},
        };
        TopFunctions.emplace_back(std::move(Func));
      }

      json::Object Root{
          {"module_name", M.getModuleIdentifier()},
          {"functions_defined", static_cast<int64_t>(N)},
          {"selected_count", static_cast<int64_t>(K)},
          {"fraction", Fraction},
          {"total_ir_insts", static_cast<int64_t>(Total)},
          {"selected_ir_insts", static_cast<int64_t>(TopSum)},
          {"selected_share_percent",
           Total == 0 ? 0.0 : (100.0 * (double)TopSum / (double)Total)},
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
