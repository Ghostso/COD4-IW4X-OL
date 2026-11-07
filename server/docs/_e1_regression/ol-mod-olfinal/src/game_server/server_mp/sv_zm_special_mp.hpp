#pragma once
#include "sv_missile_mp.hpp"
#include "sv_weapon_fire_mp.hpp"

namespace CodolGameServer {
// Reconstruction-only flight/activation adapter. Uses native missile transport;
// parameters below are temporary gameplay policy, not original CODOL timings.
[[nodiscard]] std::optional<SvMissileSpawnRequest> SV_LaunchFactorySpecial(
    SvFactorySpecialKind kind, const SvWeaponFireBasis &basis,
    std::uint16_t owner, std::uint32_t now);
[[nodiscard]] SvMissileFrameResult SV_StepFactorySpecial(
    SvFactorySpecialKind kind, const SvServerMissile &missile,
    const std::array<float,3> &origin, std::uint32_t now,
    const SvTrajectoryEvaluator &evaluate, const SvMissileFlightTrace &trace, bool sticky=false);
}
