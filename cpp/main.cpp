// main.cpp
#include <iostream>
#include <vector>

static long long heavy_sum(const std::vector<int>& v) {
    long long s = 0;
    for (int x : v) s += x;
    return s;
}

static int heavy_branch(int x) {
    int r = 0;
    for (int i = 0; i < 500; ++i) {
        if ((x + i) % 3 == 0) r += i;
        else if ((x + i) % 5 == 0) r -= i;
        else r ^= (x + i);
    }
    return r;
}

int small(int x) { return x + 1; }

int main() {
    std::vector<int> v;
    v.reserve(1000);
    for (int i = 0; i < 1000; ++i) v.push_back(i);

    std::cout << heavy_sum(v) << "\n";
    std::cout << heavy_branch(7) << "\n";
    std::cout << small(1) << "\n";
    return 0;
}
