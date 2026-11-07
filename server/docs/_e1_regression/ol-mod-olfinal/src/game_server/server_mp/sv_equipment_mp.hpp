#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

namespace CodolGameServer
{
    struct SvPlayerState;

    struct SvOffhandWeapon
    {
        std::uint16_t weaponAssetIndex{};
        std::uint16_t ammoIndex{};
        std::uint16_t clipIndex{};
        std::uint16_t clipCapacity{};
        std::uint8_t offhandClass{};
        std::uint8_t spawnCount{};
        std::string weaponName;
        bool operator==(const SvOffhandWeapon &) const = default;
    };

    // Side storage only: never embed this in WorldClientState.
    struct SvResolvedEquipment
    {
        std::array<SvOffhandWeapon, 2> weapons; // lethal, tactical
        bool operator==(const SvResolvedEquipment &) const = default;
    };

    [[nodiscard]] bool SV_IsEquipmentValid(const SvResolvedEquipment &equipment);
    [[nodiscard]] const SvOffhandWeapon *SV_FindOffhandWeapon(
        const SvResolvedEquipment &equipment, std::uint16_t weaponAssetIndex);
    // Atomically grant into the existing fifteen inventory/clip/pool slots.
    // Caller owns the once-per-life guard; this is an explicit ammo grant.
    [[nodiscard]] bool SV_EquipOffhandLoadout(
        SvPlayerState &playerState, const SvResolvedEquipment &equipment);

    // OLMOD(factory_special_reward): replace one equipment slot, preserving
    // both firearms and the other equipment's ammunition. Caller owns payment,
    // life validation and native publication. Failure changes neither argument.
    [[nodiscard]] bool SV_ReplaceOffhandReward(
        SvPlayerState &playerState, SvResolvedEquipment &equipment,
        std::size_t slot, const SvOffhandWeapon &replacement);
}
