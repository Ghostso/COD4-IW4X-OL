#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace CodolGameServer
{
    constexpr std::uint8_t WeaponAttachmentSlotCount = 16;
    constexpr std::size_t MaximumModularWeaponAttachmentCount = 15;

    struct NamedWeaponAttachment
    {
        std::uint8_t slot{};
        std::string name;

        bool operator==(const NamedWeaponAttachment &) const = default;
    };

    [[nodiscard]] std::optional<std::vector<NamedWeaponAttachment>>
        SV_MergeWeaponAttachments(
            std::span<const NamedWeaponAttachment> defaults,
            std::span<const NamedWeaponAttachment> equipped);

    [[nodiscard]] bool SV_ShouldRefreshClientLoadouts(
        bool gameStateConfigured,
        std::uint32_t activeClients,
        bool refreshRequested);
}
