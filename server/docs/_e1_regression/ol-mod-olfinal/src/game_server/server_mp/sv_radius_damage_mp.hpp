#pragma once

#include "sv_collision_mp.hpp"
#include "sv_damage_mp.hpp"

namespace CodolGameServer
{
    // OLMOD(radius-damage-input): frame-local, already damageable live players.
    // The owner supplies retained eye positions and linked absolute bounds;
    // these are not reconstructed from a standing-height approximation.
    struct SvPlayerRadiusDamageTarget
    {
        std::uint32_t clientNum{};
        std::uint8_t spawnGeneration{};
        std::array<float, 3> origin{};
        std::array<float, 3> eyePosition{};
        TraceBounds absoluteBounds;
        float shieldProtection{};
    };

    struct SvRadiusDamageCone
    {
        float angleCos{ -1.0f };
        std::array<float, 3> direction{};
    };

    struct SvPlayerRadiusDamageRequest
    {
        std::array<float, 3> origin{};
        float radius{};
        float innerDamage{};
        float outerDamage{};
        std::optional<SvRadiusDamageCone> cone;
        std::optional<std::uint32_t> inflictorEntityNum;
        std::optional<std::uint32_t> ignoreClientNum;
        // CODDIFF(radius-trace-mask): explicit until the OLfinal mask is
        // recovered. Ghosts G_RadiusDamage uses 0x802011; this is not a default.
        std::uint32_t contentMask{};
    };

    struct SvRadiusDamageTraceRequest
    {
        std::array<float, 3> start{};
        std::array<float, 3> end{};
        std::uint32_t targetClientNum{};
        std::optional<std::uint32_t> inflictorEntityNum;
        std::uint32_t contentMask{};
    };

    // CODREF(CanDamage): G_LocationalTracePassed ignores BOTH the target and
    // inflictor. Do not equate the second exclusion with passOwnerEntityNum in
    // the existing point trace schema without checking its native semantics.
    using SvRadiusDamageTracePassed = std::function<std::optional<bool>(
        const SvRadiusDamageTraceRequest &)>;

    using SvRadiusDamageEntityTracePassed = std::function<std::optional<bool>(
        const SvRadiusDamageTraceRequest &, const SvCollisionEntity &)>;

    [[nodiscard]] bool SV_IsRadiusDamageTraceRequestValid(
        const SvRadiusDamageTraceRequest &request);

    // CODREF(SV_PointSightTraceToEntity): both independent exclusions also
    // exclude their owned entities. World/static geometry runs before the
    // filtered entity narrow phase. False means obstructed; nullopt means an
    // unavailable query, never an implicit clear line through cover.
    [[nodiscard]] std::optional<bool> SV_TestRadiusDamageVisibility(
        const SvRadiusDamageTraceRequest &request,
        std::span<const SvCollisionEntity> entities,
        const SvRadiusDamageTracePassed &worldAndStaticModels,
        const SvRadiusDamageEntityTracePassed &entityTrace);

    struct SvPlayerRadiusDamageResult
    {
        std::uint32_t clientNum{};
        std::uint8_t spawnGeneration{};
        float distance{};
        float unoccludedDamage{};
        float exposure{};
        float shieldProtection{};
        std::int32_t damage{};
        std::array<float, 3> direction{};
    };

    // CODREF(G_RadiusDamage/CanDamage): IW4 822FC968/822FB8E8 and Ghosts
    // 1401274C0/140124FF0 agree on player bounds falloff and five-point exposure.
    // Returns every in-radius, non-ignored target (including zero damage, for
    // shield feedback). Nullopt rejects the whole calculation on malformed
    // input or a missing trace. Providers must be read-only; no health, event,
    // shield feedback, glass, script damage or missile retirement is committed.
    // The consumer must revalidate life ownership before dispatching results,
    // skip damage <= 0 (Ghosts G_DamageClient 140126BB7), and use the existing
    // damage/script boundary. Shield flags differ by title: IW4 69, Ghosts 133.
    [[nodiscard]] std::optional<std::vector<SvPlayerRadiusDamageResult>>
    SV_ComputePlayerRadiusDamage(
        const SvPlayerRadiusDamageRequest &request,
        std::span<const SvPlayerRadiusDamageTarget> targets,
        const SvRadiusDamageTracePassed &tracePassed);
}
