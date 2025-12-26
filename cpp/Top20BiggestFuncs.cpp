#include "llvm/IR/Function.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Module.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <utility>
#include <vector>

using namespace llvm;

namespace {

struct Top20BiggestFuncsPass : PassInfoMixin<Top20BiggestFuncsPass> {
  double Fraction = 0.20;

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
