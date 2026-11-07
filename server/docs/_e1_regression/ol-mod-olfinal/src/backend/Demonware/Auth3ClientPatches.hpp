#pragma once

#include <cstdint>
#include <span>

namespace AlwaysofflineRe::Demonware
{
    // Exposed for deterministic signature tests; the runtime path protects the
    // affected executable pages before applying the same byte changes.
    bool patchAuth3ValidationBuffer(std::span<std::uint8_t> image);
    bool installAuth3ClientPatches();
}
