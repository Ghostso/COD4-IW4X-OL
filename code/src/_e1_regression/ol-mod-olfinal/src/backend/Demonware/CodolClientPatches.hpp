#pragma once

#include <cstdint>
#include <span>

namespace AlwaysofflineRe::Demonware
{
    // Exposed for deterministic tests. The runtime path validates the known
    // CODOL image and protects every affected page before changing any bytes.
    bool patchCodolStartupBuffer(std::span<std::uint8_t> image);
    [[nodiscard]] bool shouldRequestCodolInventory(
        std::uint32_t profileKind,
        std::uint32_t operation,
        bool succeeded,
        std::uint32_t errorCode);
    [[nodiscard]] bool shouldInvalidateCodolCurrentCharacterCache(
        std::uint32_t profileKind,
        std::uint32_t operation,
        bool succeeded,
        std::uint32_t errorCode);
    [[nodiscard]] std::uint32_t requestCodolProfileReload(std::uint32_t profileKind);
    [[nodiscard]] bool getCodolProfileReloadStatus(
        std::uint32_t profileKind,
        std::uint32_t &generation,
        std::uint32_t &state,
        std::uint32_t &errorCode);
    [[nodiscard]] std::uint32_t requestCodolInventoryRefresh();
    [[nodiscard]] bool getCodolInventoryRefreshStatus(
        std::uint32_t &generation,
        std::uint32_t &state,
        std::uint32_t &errorCode);
    bool installCodolStartupPatches();
}
