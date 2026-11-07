#pragma once
#include <cstdint>
#include <optional>

namespace CodolGameServer {
// CODREF(out.exe613A40): cg is table[selector] XOR FBB2C97A, NOT
// table[localClientNum]. Live clients use selectors5 and3. The64-entry bound
// is a conservative read guard, not a recovered native array declaration.
template<class Read>
std::optional<std::uint32_t> resolveBatteryClientNum(std::uintptr_t base,Read read) {
    std::uint32_t selector{},encoded{},client{},commandTime{},pmType{},health{};
    if(!base || !read(base+0x7EC3B58,selector) || selector>=64 ||
        !read(base+0x181D188+selector*4,encoded) || !encoded)return {};
    const auto cg=static_cast<std::uintptr_t>(encoded^0xFBB2C97Au);
    // CODREF(out.exe411360): replicated health stats[0] is +1A4 (420).
    // +20C is a server Pmove shadow and remains zero in both live clients.
    if(!read(cg,commandTime) || !commandTime || !read(cg+4,pmType) || pmType!=0 ||
        !read(cg+0x1A4,health) || !health || !read(cg+0x158,client) || client>=18)return {};
    return client;
}
}
