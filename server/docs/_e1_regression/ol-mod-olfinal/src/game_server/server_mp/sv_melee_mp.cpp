#include "sv_melee_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    std::array<float, 3> SV_MeleeTraceEnd(
        const SvWeaponFireBasis &basis, const float range)
    {
        return {
            basis.muzzleTrace[0] + basis.forward[0] * range,
            basis.muzzleTrace[1] + basis.forward[1] * range,
            basis.muzzleTrace[2] + basis.forward[2] * range,
        };
    }

    SvMeleeAttackResult SV_ExecuteMeleeAttack(
        const SvMeleeAttackInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassMapMetadata &glassMetadata,
        const SvGlassDirectionEncoder &directionEncoder,
        const std::span<const SvDamageablePlayerView> damageablePlayers,
        const std::span<const SvDamageableEntityView> damageableEntities,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        std::vector<SvEntityDamagePayload> &entityDamagePayloads,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState)
    {
        if (!traceRunner)
            return SvMeleeAttackResult::Failed;
        // CODDIFF(weapon_melee): the weapon here is whatever the attacker is
        // holding, because CODOL melees with the equipped weapon rather than
        // swapping to a knife asset. The payload validator
        // (SV_IsEntityDamagePayloadValid) refuses weaponAssetIndex 0, and the
        // entityState this is dispatched from carries knife=0 on this build, so
        // taking the knife index instead of the held one would produce a
        // payload that is silently rejected -- which is exactly the shape of
        // the bug being fixed.
        if (!input.weaponAssetIndex ||
            input.weaponAssetIndex > MaximumWeaponAssetIndex ||
            !input.meleeDamage ||
            input.firingEntityNum > MaximumServerCollisionEntityNum)
        {
            return SvMeleeAttackResult::Failed;
        }
        const auto &forward = input.basis.forward;
        const auto forwardLengthSquared = forward[0] * forward[0] +
            forward[1] * forward[1] + forward[2] * forward[2];
        if (!std::isfinite(forwardLengthSquared) ||
            forwardLengthSquared <= 0.0f)
        {
            return SvMeleeAttackResult::Failed;
        }
        if (!std::ranges::all_of(input.basis.muzzleTrace, [](const float v) {
                return std::isfinite(v);
            }))
        {
            return SvMeleeAttackResult::Failed;
        }

        const auto end = SV_MeleeTraceEnd(input.basis, SvMeleeRange);
        // CODREF(weapon_melee): BO1's Melee_Trace 0x82489730 is a bounded
        // forward trace from the attacker's weapon origin. SV_BulletTrace is
        // already exactly that primitive on this build -- a locational trace
        // that reports partGroup/partName -- so melee reuses it rather than
        // introducing a second, differently-behaved trace path.
        const auto trace = SV_BulletTrace(
            {
                .start = input.basis.muzzleTrace,
                .end = end,
                .firingEntityNum = input.firingEntityNum,
                // NOT ZERO, AND THAT WAS THE GLASS BUG. SV_BulletTrace treats
                // this as the bound a glass hitId must fall inside, and rejects
                // the whole trace when it does not:
                //
                //     if (!hitId || hitId > input.glassPieceCount)
                //         return std::nullopt;
                //
                // With the count left at 0 that condition is true for EVERY
                // glass pane -- hitId is one-based -- so a swing at a window
                // produced no trace at all, became SvMeleeAttackResult::Failed,
                // and SV_HandleClientEventsDetailed turned that into
                // SvClientEventResult::Failed. The reported symptom is that the
                // glass does not break; the actual cost was that the whole
                // usercmd was rejected (ClientEventsRejected), taking the
                // player's movement for that command with it. Bullets were
                // unaffected because SV_ExecuteBulletFire has always passed the
                // real pane count.
                .glassPieceCount = input.glassPieceCount,
                .lastSurfaceType = 0,
                .rifleBullet = false,
            },
            traceRunner,
            ignoreHitResolver);
        if (!trace)
            return SvMeleeAttackResult::Failed;

        // GLASS FIRST. A glass hit carries hitType TraceHitTypeGlass, so it
        // never sets hitEntityNum, and the player checks below would read it as
        // a miss and drop it on the floor.
        if (trace->glassPieceIndex)
        {
            // CODREF(bullet_process): identical to SV_ExecuteBulletFire's own
            // glass branch, deliberately -- the same helper, the same candidate
            // ownership, the same one-swing-one-damage-number rule. Melee has
            // no shot loop, so there is exactly one pane per swing.
            if (!SV_ApplyBulletGlassDamage(
                    *trace,
                    input.meleeDamage,
                    input.levelTime,
                    input.basis.forward,
                    glassMetadata,
                    directionEncoder,
                    glassDamageState,
                    glassState))
            {
                return SvMeleeAttackResult::Failed;
            }
            return SvMeleeAttackResult::Glass;
        }

        if (trace->trace.hitType == 0 || !trace->hitEntityNum ||
            trace->ignoreHitEntity)
        {
            return SvMeleeAttackResult::Missed;
        }
        // CODREF(weapon_melee): BO1 returns without damaging when the swing
        // lands on the riot shield's part group.
        if (trace->trace.partGroup == BulletShieldPartGroup)
            return SvMeleeAttackResult::Missed;
        if (trace->trace.partGroup >= HitLocationCount)
            return SvMeleeAttackResult::Failed;

        const auto target = std::ranges::find(
            damageablePlayers,
            *trace->hitEntityNum,
            &SvDamageablePlayerView::entityNum);
        if (target == damageablePlayers.end())
        {
            const auto entityTarget = std::ranges::find(
                damageableEntities,
                *trace->hitEntityNum,
                &SvDamageableEntityView::entityNum);
            if (entityTarget == damageableEntities.end())
                return SvMeleeAttackResult::Missed;

            const SvEntityDamagePayload payload{
                .targetEntityNum = entityTarget->entityNum,
                .targetGeneration = entityTarget->generation,
                .inflictorEntityNum = input.firingEntityNum,
                .attackerEntityNum = input.firingEntityNum,
                .damage = input.meleeDamage,
                .methodOfDeath = SvMethodOfDeathMelee,
                .weaponAssetIndex = input.weaponAssetIndex,
                .point = trace->hitPosition,
                .direction = input.basis.forward,
                .hitLocation = static_cast<std::uint8_t>(
                    trace->trace.partGroup),
                .boneIndex = trace->trace.partName,
            };
            if (!SV_IsEntityDamagePayloadValid(
                    payload,
                    MaximumGameEntities,
                    MethodOfDeathCount,
                    HitLocationCount))
            {
                return SvMeleeAttackResult::Failed;
            }
            entityDamagePayloads.push_back(payload);
            return SvMeleeAttackResult::Applied;
        }

        // CODDIFF(weapon_melee): no hit-location multiplier. BO1's
        // Weapon_Melee_internal damages with the weapon's melee number and
        // never scales it by the part group -- a knife to the foot kills -- so
        // the multiplier is 1.0 and partGroup is carried only so the obituary
        // and hit feedback name the right location.
        const auto payload = SV_BuildPlayerDamagePayload({
            .targetClientNum = target->clientNum,
            .inflictorEntityNum = input.firingEntityNum,
            .attackerEntityNum = input.firingEntityNum,
            .baseDamage = input.meleeDamage,
            .hitLocationMultiplier = 1.0f,
            .methodOfDeath = SvMethodOfDeathMelee,
            .weaponAssetIndex = input.weaponAssetIndex,
            .point = trace->hitPosition,
            .direction = input.basis.forward,
            .hitLocation = static_cast<std::uint8_t>(trace->trace.partGroup),
            .boneIndex = trace->trace.partName,
        });
        if (!payload)
            return SvMeleeAttackResult::Failed;

        playerDamagePayloads.push_back(*payload);
        return SvMeleeAttackResult::Applied;
    }

    SvMeleeAttackResult SV_ExecuteMeleeAttack(
        const SvMeleeAttackInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassMapMetadata &glassMetadata,
        const SvGlassDirectionEncoder &directionEncoder,
        const std::span<const SvDamageablePlayerView> damageablePlayers,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState)
    {
        std::vector<SvEntityDamagePayload> entityDamagePayloads;
        return SV_ExecuteMeleeAttack(
            input,
            traceRunner,
            ignoreHitResolver,
            glassMetadata,
            directionEncoder,
            damageablePlayers,
            {},
            playerDamagePayloads,
            entityDamagePayloads,
            glassDamageState,
            glassState);
    }
}
