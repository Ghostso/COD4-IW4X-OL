#pragma once

#include "sv_missile_mp.hpp"
#include "sv_weapon_fire_mp.hpp"
#include <span>

namespace CodolGameServer
{
    // Recovered launch fields, not a replacement WeaponDef. Other projectile
    // properties (contact, activation, rotation policy) remain separate owners.
    struct SvGrenadeLaunchParameters
    {
        std::uint16_t weapon{};
        std::int32_t speed{};
        std::int32_t speedUp{};
        std::int32_t fuseMilliseconds{};
        bool cookOffHold{};
        bool timedDetonation{};
        bool operator==(const SvGrenadeLaunchParameters &) const = default;
    };

    [[nodiscard]] std::optional<SvGrenadeLaunchParameters> SV_ReadGrenadeLaunchParameters(
        std::uint16_t weapon, std::span<const std::uint8_t> definition);

    struct SvGrenadeLaunchRequest
    {
        SvGrenadeLaunchParameters parameters;
        SvWeaponFireBasis basis;
        std::array<float,3> playerVelocity{};
        // Caller owns rotation policy/randomness. Copy its seed along with the
        // command candidate; a failed launch must not advance a global RNG.
        std::array<float,3> angularVelocity{};
        std::uint32_t time{};
        std::uint16_t owner{};
        std::int32_t heldFuseMilliseconds{};
        bool rotate{};
    };

    using SvDirectionToAngles = std::function<bool(
        const std::array<float,3> &, std::array<float,3> &)>;

    // Ordinary player throw (no extra horizontal/relative-up speed or distance
    // activation). Negative held timers belong to the separate in-hand/throwback
    // event path. This computes a spawn request without consuming ammo or fuse.
    [[nodiscard]] std::optional<SvMissileSpawnRequest> SV_ComputeGrenadeLaunch(
        const SvGrenadeLaunchRequest &request, const SvDirectionToAngles &toAngles);
}
