#pragma once

#include "sv_trajectory_mp.hpp"
#include "sv_native_entitystate_mp.hpp"
#include "sv_entity_mp.hpp"
#include "sv_collision_mp.hpp"
#include "sv_damage_mp.hpp"
#include "sv_grenade_explosion_mp.hpp"
#include "sv_zm_special_policy.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <variant>
#include <string>

namespace CodolGameServer
{
    struct SvEntityState;
    inline constexpr std::uint8_t SvEntityTypeMissile = 4;

    // Source-owned missile presentation. Keep this outside WorldClientState.
    // CODREF(1649370): ET_MISSILE table 0xDA7A20; retail dm entity482/life2.
    struct SvMissileNetworkState
    {
        std::uint32_t number{};
        std::uint16_t weapon{};
        std::uint16_t owner{};
        std::uint16_t ground{};
        std::uint32_t eFlags{};
        SvNativeTrajectory position;
        SvNativeTrajectory angles;
        float scale{1.0f};
        std::uint32_t launchTime{};
        // CODREF(1649370): CG_EntityEvent 5362B0/5363BB uses cent+392
        // (es+94) to select per-surface grenade sounds/effects. Checkpoint45.
        std::uint8_t surfaceType{};
        std::uint8_t eventSequence{};
        std::array<SvEntityEvent,4> events{};
        bool operator==(const SvMissileNetworkState &) const = default;
    };

    // A command candidate requests a spawn before an entity number is allocated.
    // initial.number must be zero; the world supplies a generation-safe handle.
    struct SvMissileSpawnRequest
    {
        SvMissileNetworkState initial;
        std::uint32_t fuseDeadline{};
        bool operator==(const SvMissileSpawnRequest &) const = default;
    };

    // World side storage, never embedded in a client/native image.
    struct SvServerMissile
    {
        SvEntityHandle handle;
        SvMissileNetworkState network;
        std::uint32_t fuseDeadline{};
        std::uint32_t lastUpdateTime{};
        std::uint8_t ownerSpawnGeneration{};
        bool hasRunFrame{};
        std::optional<std::array<float,3>> contactNormal;
        bool operator==(const SvServerMissile &) const = default;
    };

    // The caller supplies the retained trace with this missile's actual mask
    // and collision policy. No guessed grenade mask is supplied here.
    using SvMissileFlightTrace = std::function<std::optional<TraceResult>(
        const SvServerMissile &, const std::array<float,3> &, const std::array<float,3> &)>;

    struct SvMissileFlightStep
    {
        std::uint32_t atTime{};
        std::array<float,3> origin{};
        std::array<float,3> angles{};
        std::optional<TraceResult> impact;
        std::uint32_t impactTime{};
        bool fuseDue{};
        bool operator==(const SvMissileFlightStep &) const = default;
    };

    // Completed simulation result. The runner resolves flight, contact and
    // think before returning; it must not publish external side effects.
    // Runtime origin/angles are distinct from the retained network trajectory
    // base. Free flight moves the former without rebasing the latter.
    struct SvMissileFrameUpdate
    {
        SvMissileNetworkState network;
        std::array<float,3> origin{};
        std::array<float,3> angles{};
        std::uint32_t fuseDeadline{};
        std::optional<std::array<float,3>> contactNormal;
        std::optional<SvFactorySpecialImpact> factoryImpact;
    };
    struct SvMissileRetirement {};
    struct SvMissilePlayerDamage
    {
        SvPlayerDamagePayload payload;
        std::uint32_t spawnSequence{};
        std::uint8_t spawnGeneration{};
    };
    // OLMOD(missile-detonation-transaction): immutable results, not inline
    // effects. The world allocates the visual event and journals script damage
    // only when missile removal and the native frame mirror both commit.
    struct SvMissileDetonation
    {
        // Underwater suppression can omit presentation while retaining damage.
        std::optional<SvGrenadeExplosionEvent> effect;
        std::vector<SvMissilePlayerDamage> playerDamage;
        std::string weaponName;
        std::optional<SvFactorySpecialImpact> factoryImpact;
    };
    using SvMissileFrameResult = std::variant<SvMissileFrameUpdate,
        SvMissileRetirement, SvMissileDetonation>;
    using SvMissileFrameRunner = std::function<std::optional<SvMissileFrameResult>(
        const SvServerMissile &, const std::array<float,3> &, std::uint32_t)>;

    // Compute without publication. Impact resolution precedes fuse handling;
    // the owner must complete those continuations before committing this step.
    // Free flight preserves the original network trajectory/time/base.
    [[nodiscard]] std::optional<SvMissileFlightStep> SV_ComputeMissileFlightStep(
        const SvServerMissile &missile, const std::array<float,3> &currentOrigin,
        std::uint32_t atTime, const SvTrajectoryEvaluator &evaluate,
        const SvMissileFlightTrace &trace);

    using SvMissileDirectionEncoder = std::function<std::optional<std::uint8_t>(
        const std::array<float,3> &)>;

    // Resolve an already admitted WEAPSTICKINESS_ALL contact with the world.
    // Player/mover attachment and special surface continuations are separate.
    // Does not run think, emit external effects, or change the input missile.
    [[nodiscard]] std::optional<SvMissileFrameUpdate> SV_StickMissileToWorld(
        const SvServerMissile &missile, const SvMissileFlightStep &step,
        bool timedDetonation, const SvMissileDirectionEncoder &encodeDirection);

    // Only the recovered grenade fields are admitted; unrelated union payload
    // must not silently cross the serializer boundary.
    [[nodiscard]] std::optional<SvEntityState> SV_ProjectMissileEntity(
        const SvMissileNetworkState &missile);
    [[nodiscard]] bool SV_IsMissileEntityValid(const SvEntityState &entity);
}
