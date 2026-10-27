// Builder-authored scalar integration probe. Not Zucchini, not a C++ proof.
// Input restriction avoids overflowing 2*q; results are checked before addition.
#include <cstdint>
#include <iostream>
#include <limits>
#include <tuple>
static auto assemble(std::int64_t a, std::int64_t b, std::int64_t f, std::int64_t q) {
    constexpr auto max = std::numeric_limits<std::int64_t>::max();
    if (a < 0 || b < 0 || f < 0 || q > max/2) return std::make_tuple(-1,a,b,f);
    if (q <= 0 || a < 2*q || b < q) return std::make_tuple(0,a,b,f);
    if (f > max-q) return std::make_tuple(-1,a,b,f);
    return std::make_tuple(1,a-2*q,b-q,f+q);
}
int main() {
    std::int64_t a,b,f,q;
    while (std::cin >> a >> b >> f >> q) {
        auto [s,oa,ob,of] = assemble(a,b,f,q);
        std::cout << s << ' ' << oa << ' ' << ob << ' ' << of << '\n';
    }
    return std::cin.eof() ? 0 : 2;
}
