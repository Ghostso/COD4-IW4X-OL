#include "sv_bullet_mp.hpp"
#include "sv_gamestate_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::uint32_t TraceHitTypeMaximum = 4;

        std::optional<std::int32_t> entityBulletDamage(const SvDamageableEntityView &target,
            const std::int32_t base, const float locationMultiplier)
        {
            if (!target.usesWeaponHitLocationMultipliers)
                return std::max(1, base);
            // OLMOD(zombie-hit-location): use the weapon's actual native table
            // after range/penetration attenuation, as the player path does.
            // Recorded26/31 and49/58 pairs fit its1.2 head entry. The original
            // cyborg server's additional critical modifiers remain unrecovered.
            const auto scaled = static_cast<float>(base) * locationMultiplier;
            if (!std::isfinite(scaled) || scaled < 0.0f || scaled >= 2147483648.0f)
                return std::nullopt;
            return std::max(1, static_cast<std::int32_t>(scaled));
        }

        bool finiteVector(const std::array<float, 3> &value)
        {
            return std::ranges::all_of(value, [](const float component) {
                return std::isfinite(component);
            });
        }

        bool validTraceResult(const TraceResult &trace)
        {
            return std::isfinite(trace.fraction) && trace.fraction >= 0.0f &&
                trace.fraction <= 1.0f && finiteVector(trace.normal) &&
                trace.hitType <= TraceHitTypeMaximum &&
                (trace.hitType != TraceHitTypeEntity ||
                    trace.hitId <= BulletNoneEntityNum);
        }

        // OLMOD(bullet-command-transaction): native Bullet_Process exposes
        // per-pellet glass mutation to the next trace immediately. Source must
        // preserve that visibility while still rolling the whole usercmd back
        // if a later pellet or effect fails validation.
        class GlassCommandRollback final
        {
        public:
            GlassCommandRollback(
                SvGlassDamageState &damageState,
                SvGlassState &glassState)
                : damageState_(damageState),
                  glassState_(glassState),
                  originalDamageState_(damageState),
                  originalGlassState_(glassState)
            {
            }

            GlassCommandRollback(const GlassCommandRollback &) = delete;
            GlassCommandRollback &operator=(const GlassCommandRollback &) = delete;

            ~GlassCommandRollback()
            {
                if (!committed_)
                {
                    damageState_ = std::move(originalDamageState_);
                    glassState_ = std::move(originalGlassState_);
                }
            }

            void commit()
            {
                committed_ = true;
            }

        private:
            SvGlassDamageState &damageState_;
            SvGlassState &glassState_;
            SvGlassDamageState originalDamageState_;
            SvGlassState originalGlassState_;
            bool committed_{};
        };
    }

    bool SV_IsBulletTraceInputValid(const SvBulletTraceInput &input)
    {
        // OLMOD(bullet-trace-source-schema): admission bounds protect native
        // trace calls; they are not a recovered CODOL Bullet_Trace wrapper.
        return finiteVector(input.start) && finiteVector(input.end) &&
            input.firingEntityNum <= MaximumServerCollisionEntityNum &&
            input.glassPieceCount <= SvGlassPieceCount &&
            input.lastSurfaceType < BulletSurfaceTypeCount &&
            !(input.worldOnly && input.entitiesOnly);
    }

    // SECTION 191z: THIRTEEN WAYS TO REFUSE A SHOT AND ONE WORD FOR ALL OF THEM.
    //
    // `client_events_rejected` names the STAGE and nothing else, and the bullet
    // path has thirteen distinct `Failed` returns behind it. A player reporting
    // "it hits and never hurts them" cannot be told apart from a bad trace, an
    // unresolved endpos or a rejected payload, so the first alt-fire shot cost a
    // whole read of the file to narrow by hand.
    //
    // A pointer to a literal, written on the frame thread and read on the same
    // one. No field is added to any struct: SvBulletExecutionStatus is reached
    // through the entity and this project has broken an address-keyed buffer
    // twice by growing something that looked inert (section 184h).
    namespace
    {
        thread_local const char *lastBulletFireFailure = nullptr;
    }

    SvBulletFireExecutionResult SV_BulletFireFailed(const char *const reason)
    {
        lastBulletFireFailure = reason;
        return SvBulletFireExecutionResult::Failed;
    }

    const char *SV_LastBulletFireFailure()
    {
        return lastBulletFireFailure ? lastBulletFireFailure : "unset";
    }

    bool SV_IsBulletImpactEventValid(const SvBulletImpactEvent &event)
    {
        // OLMOD(bullet-impact-source-schema): only the currently recovered
        // ordinary EV_BULLET_HIT form accepts zero additional impact flags.
        // A melee hit asserts NONE of the bullet-only fields -- 36 of 36 in the
        // retail demo -- so requiring them absent is what keeps the two shapes
        // from drifting into each other.
        if (event.melee &&
            (event.surfaceType != 0 || event.hitEntityNum != BulletNoneEntityNum))
        {
            return false;
        }
        return finiteVector(event.position) && event.weaponAssetIndex > 0 &&
            event.weaponAssetIndex <= MaximumWeaponAssetIndex &&
            event.sourceEntityNum <= MaximumServerCollisionEntityNum &&
            event.hitEntityNum <= BulletNoneEntityNum &&
            event.surfaceType < BulletSurfaceTypeCount &&
            event.impactFlags == 0;
    }

    std::optional<SvBulletTraceResult> SV_BulletTrace(
        const SvBulletTraceInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver)
    {
        // CODREF(bullet_trace): BO1 0x005F3DE0, Ghosts 0x140109F10 and BO2
        // 0x005AC950 all build a locational point trace, resolve entity/glass
        // identity, lerp the hit position and classify ignore/surface state.
        // CODDIFF(bullet_trace): CODOL's retained SV_Trace clears locational
        // state, so the adapter enters the confirmed lower CM point-trace path
        // with CODOL's 0x0280E831 mask instead of copying a reference ABI.
        if (!SV_IsBulletTraceInputValid(input) || !traceRunner)
            return std::nullopt;

        const SvPointTraceRequest request{
            .start = input.start,
            .end = input.end,
            .contentMask = BulletLocationalContentMask,
            .filter = {
                .passEntityNum = input.passFiringEntity
                    ? std::optional{ input.firingEntityNum }
                    : std::nullopt,
            },
            .mode = input.rifleBullet
                ? SvPointTraceMode::RifleLocational
                : SvPointTraceMode::BulletLocational,
            .allowChildren = true,
            .worldOnly = input.worldOnly,
            .entitiesOnly = input.entitiesOnly,
        };
        const auto traceResult = traceRunner(request);
        if (!traceResult || !validTraceResult(*traceResult))
        {
            return std::nullopt;
        }

        SvBulletTraceResult result{ .trace = *traceResult };
        if (result.trace.hitType == TraceHitTypeGlass)
        {
            if (!result.trace.hitId ||
                result.trace.hitId > input.glassPieceCount)
            {
                return std::nullopt;
            }
            result.glassPieceIndex = result.trace.hitId - 1;
        }
        if (result.trace.hitType == TraceHitTypeEntity &&
            result.trace.hitId <= MaximumServerCollisionEntityNum)
        {
            result.hitEntityNum = result.trace.hitId;
            if (!ignoreHitResolver)
                return std::nullopt;
            const auto ignore = ignoreHitResolver(
                input, result.trace, *result.hitEntityNum);
            if (!ignore)
                return std::nullopt;
            result.ignoreHitEntity = *ignore;
            if (result.trace.partGroup == BulletShieldPartGroup)
                result.trace.surfaceFlags = BulletShieldSurfaceFlags;
        }

        for (std::size_t axis = 0; axis != result.hitPosition.size(); ++axis)
        {
            result.hitPosition[axis] = input.start[axis] +
                (input.end[axis] - input.start[axis]) * result.trace.fraction;
        }
        if (!finiteVector(result.hitPosition))
            return std::nullopt;

        result.depthSurfaceType = static_cast<std::uint8_t>(
            (result.trace.surfaceFlags >> 20) & 0x1F);
        if (result.trace.surfaceFlags & 0x100)
            result.depthSurfaceType = 0;
        else if (!result.depthSurfaceType)
            result.depthSurfaceType = input.lastSurfaceType;
        return result;
    }

    bool SV_ApplyBulletGlassDamage(
        const SvBulletTraceResult &trace,
        const std::uint32_t damage,
        const std::int32_t levelTime,
        const std::array<float, 3> &damageDirection,
        const SvGlassMapMetadata &metadata,
        const SvGlassDirectionEncoder &directionEncoder,
        SvGlassDamageState &damageState,
        SvGlassState &glassState)
    {
        // CODDIFF(bullet_process): Ghosts exposes the later authoritative glass
        // owner shape; CODOL confirms wire/collision consumers but lacks its
        // server producer. Source updates damage and snapshot state atomically.
        if (!trace.glassPieceIndex || !damage ||
            *trace.glassPieceIndex >= metadata.initialPieces.size())
        {
            return false;
        }

        auto candidateDamageState = damageState;
        auto candidateGlassState = glassState;
        const auto result = candidateDamageState.damagePiece(
            *trace.glassPieceIndex, damage, levelTime);
        if (!result)
            return false;
        if (result->stateChanged)
        {
            std::optional<SvGlassImpact> impact;
            if (result->state == SvGlassPieceState::Destroyed)
            {
                const auto quantized = SV_QuantizeGlassImpact(
                    metadata,
                    *trace.glassPieceIndex,
                    trace.hitPosition,
                    damageDirection,
                    directionEncoder);
                if (!quantized)
                    return false;
                impact = quantized->impact;
            }
            if (!candidateGlassState.setPieceState(
                    *trace.glassPieceIndex, result->state, impact))
            {
                return false;
            }
        }

        damageState = std::move(candidateDamageState);
        glassState = std::move(candidateGlassState);
        return true;
    }

    SvBulletFireExecutionResult SV_ExecuteBulletFire(
        const SvBulletFireExecutionInput &input,
        const SvGlassMapMetadata &glassMetadata,
        const SvBulletEndposRunner &endposRunner,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassDirectionEncoder &directionEncoder,
        const std::span<const SvDamageablePlayerView> damageablePlayers,
        const std::span<const SvDamageableEntityView> damageableEntities,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        std::vector<SvEntityDamagePayload> &entityDamagePayloads,
        std::vector<SvBulletImpactEvent> &bulletImpactEvents,
        SvBulletExecutionStatus *const executionStatus,
        const SvBulletPenetrationDepthResolver &penetrationDepthResolver)
    {
        // CODREF(bullet_process): BO1 0x005F4190, Ghosts 0x140109AA0 and BO2
        // 0x005AD850 all consume Bullet_Trace before impact presentation and
        // typed G_Damage dispatch. The static-BSP penetration continuation
        // below follows COD4 Bullet_FirePenetrate's reverse trace, material
        // depth loss and next-hit processing.
        // OLMOD(bullet-command-transaction): all outputs are candidate-owned;
        // SvServerWorld::clientThink commits client/entity/glass/damage/event
        // state together after the complete usercmd succeeds.
        if (!input.plan.shotCount || !std::isfinite(input.plan.maxRange) ||
            input.plan.maxRange <= 0.0f ||
            !SV_IsWeaponFireBasisValid(input.basis) ||
            !std::isfinite(input.spread.firing) || input.spread.firing < 0.0f ||
            !SV_IsWeaponDamageCurveValid(input.damageCurve) ||
            input.weaponAssetIndex == 0 ||
            input.weaponAssetIndex > MaximumWeaponAssetIndex ||
            std::ranges::any_of(
                input.hitLocationMultipliers,
                [](const float multiplier) {
                    return !std::isfinite(multiplier) || multiplier < 0.0f ||
                        multiplier > 20.0f;
                }) ||
            input.firingEntityNum > MaximumServerCollisionEntityNum)
        {
            return SV_BulletFireFailed("input-invalid");
        }
        if (input.plan.methodOfDeath == 3)
            return SvBulletFireExecutionResult::DeferredImpact;
        if (!endposRunner || !traceRunner)
            return SV_BulletFireFailed("endpos-or-trace-runner-missing");

        auto candidateDamagePayloads = playerDamagePayloads;
        auto candidateEntityDamagePayloads = entityDamagePayloads;
        auto candidateImpactEvents = bulletImpactEvents;
        GlassCommandRollback glassRollback(glassDamageState, glassState);
        auto randomSeed = input.plan.randomSeed;
        // CODREF(bullet_process): BO1 and Ghosts process the first trace before
        // entering the reverse trace/depth loop.
        // TODO(CODOL): native Bullet_Process calls G_Damage for each pellet, so
        // script policy and a lethal transition can remove that target before
        // the next pellet. This source function stages the complete command
        // before Lua dispatch and therefore cannot yet reproduce that nested
        // per-pellet script boundary without a command-effect executor.
        auto deferredImpact = input.plan.penetrate && !penetrationDepthResolver;
        for (std::uint8_t shot{}; shot < input.plan.shotCount; ++shot)
        {
            std::optional<SvEntityDamagePayload> pendingEntityDamage;
            bool hitDamageablePlayer{};
            const auto endpos = endposRunner({
                .randomSeed = randomSeed,
                .spread = input.spread.firing,
                .maxRange = input.plan.maxRange,
                .basis = input.basis,
            });
            if (!endpos)
                return SV_BulletFireFailed("endpos-unresolved");
            randomSeed = endpos->randomSeed;

            const auto trace = SV_BulletTrace({
                .start = input.basis.muzzleTrace,
                .end = endpos->end,
                .firingEntityNum = input.firingEntityNum,
                .glassPieceCount = static_cast<std::uint32_t>(
                    glassMetadata.initialPieces.size()),
                .rifleBullet = input.rifleBullet,
                .passFiringEntity = input.passFiringEntity,
            }, traceRunner, ignoreHitResolver);
            if (!trace)
                return SV_BulletFireFailed("trace-unresolved");
            if (executionStatus)
            {
                // Multi-projectile weapons retain the last processed trace.
                *executionStatus = {
                    .traced = true,
                    .commandTime = input.commandTime,
                    .start = input.basis.muzzleTrace,
                    .end = endpos->end,
                    .trace = trace->trace,
                    .hitEntityNum = trace->hitEntityNum,
                };
            }
            if (trace->trace.hitType == 0)
                continue;

            const auto delta = std::array{
                trace->hitPosition[0] - input.basis.muzzleTrace[0],
                trace->hitPosition[1] - input.basis.muzzleTrace[1],
                trace->hitPosition[2] - input.basis.muzzleTrace[2],
            };
            const auto distance = std::sqrt(
                delta[0] * delta[0] + delta[1] * delta[1] +
                delta[2] * delta[2]);
            const auto damage = SV_CalculateBulletDamage({
                .curve = input.damageCurve,
                .distance = distance,
            });
            if (!damage || *damage < 0)
                return SV_BulletFireFailed("damage-curve");
            if (trace->hitEntityNum && !trace->ignoreHitEntity &&
                trace->trace.partGroup != BulletShieldPartGroup)
            {
                // CODDIFF(bullet_process): native G_Damage dispatches through
                // gentity type and handler ownership. The source bridge uses
                // disjoint, generation-safe player/entity capability views;
                // player precedence mirrors native G_DamageClient selection.
                const auto target = std::ranges::find(
                    damageablePlayers,
                    *trace->hitEntityNum,
                    &SvDamageablePlayerView::entityNum);
                if (target != damageablePlayers.end())
                {
                    if (!*damage)
                        continue;
                    if (trace->trace.partGroup >= HitLocationCount)
                        return SV_BulletFireFailed("player-part-group");
                    const auto payload = SV_BuildPlayerDamagePayload({
                        .targetClientNum = target->clientNum,
                        .inflictorEntityNum = input.firingEntityNum,
                        .attackerEntityNum = input.firingEntityNum,
                        .baseDamage = *damage,
                        .hitLocationMultiplier =
                            input.hitLocationMultipliers[trace->trace.partGroup],
                        .methodOfDeath = input.plan.methodOfDeath,
                        .weaponAssetIndex = input.weaponAssetIndex,
                        .point = trace->hitPosition,
                        .direction = endpos->direction,
                        .hitLocation = static_cast<std::uint8_t>(
                            trace->trace.partGroup),
                        .boneIndex = trace->trace.partName,
                    });
                    if (!payload)
                        return SV_BulletFireFailed("player-payload-build");
                    candidateDamagePayloads.push_back(*payload);
                    if (executionStatus)
                        executionStatus->playerDamageStaged = true;
                    hitDamageablePlayer = true;
                }

                if (!hitDamageablePlayer)
                {
                    const auto entityTarget = std::ranges::find(
                        damageableEntities,
                        *trace->hitEntityNum,
                        &SvDamageableEntityView::entityNum);
                    if (entityTarget != damageableEntities.end() && *damage)
                    {
                        if (trace->trace.partGroup >= HitLocationCount)
                            return SV_BulletFireFailed("entity-part-group");
                        const auto entityDamage = entityBulletDamage(*entityTarget, *damage,
                            input.hitLocationMultipliers[trace->trace.partGroup]);
                        if (!entityDamage)
                            return SV_BulletFireFailed("entity-location-damage");
                        const SvEntityDamagePayload payload{
                            .targetEntityNum = entityTarget->entityNum,
                            .targetGeneration = entityTarget->generation,
                            .inflictorEntityNum = input.firingEntityNum,
                            .attackerEntityNum = input.firingEntityNum,
                            .damage = *entityDamage,
                            .methodOfDeath = input.plan.methodOfDeath,
                            .weaponAssetIndex = input.weaponAssetIndex,
                            .point = trace->hitPosition,
                            .direction = endpos->direction,
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
                            return SV_BulletFireFailed("entity-payload-invalid");
                        }
                        pendingEntityDamage = payload;
                        if (executionStatus)
                            executionStatus->entityDamageStaged = true;
                    }
                }
            }
            if (trace->glassPieceIndex)
            {
                if (!*damage)
                    continue;
                if (!SV_ApplyBulletGlassDamage(
                        *trace,
                        static_cast<std::uint32_t>(*damage),
                        input.levelTime,
                        endpos->direction,
                        glassMetadata,
                        directionEncoder,
                        glassDamageState,
                        glassState))
                {
                    return SV_BulletFireFailed("glass-damage");
                }
                continue;
            }

            if (trace->trace.partGroup == BulletShieldPartGroup)
            {
                deferredImpact = true;
                continue;
            }
            if (!trace->ignoreHitEntity &&
                !(trace->trace.surfaceFlags & 4))
            {
                // CODREF(bullet_process): BO1/Ghosts create Bullet_ImpactEffect
                // before synchronous G_Damage for ordinary player and entity
                // hits alike. Keep presentation independent from whether the
                // typed damage receiver is a player or generic entity.
                // TODO(CODOL): restore native head/kill additional impact flags
                // after the corresponding CODOL eventParm2 consumer is closed.
                if (!directionEncoder)
                    return SV_BulletFireFailed("impact-direction-encoder-missing");
                const auto direction = directionEncoder(trace->trace.normal);
                if (!direction)
                    return SV_BulletFireFailed("impact-direction-encode");
                const SvBulletImpactEvent impact{
                    .position = trace->hitPosition,
                    .weaponAssetIndex = input.weaponAssetIndex,
                    .sourceEntityNum = static_cast<std::uint16_t>(
                        input.firingEntityNum),
                    .hitEntityNum = static_cast<std::uint16_t>(
                        trace->hitEntityNum.value_or(BulletNoneEntityNum)),
                    .direction = *direction,
                    .surfaceType = trace->depthSurfaceType,
                };
                if (!SV_IsBulletImpactEventValid(impact))
                    return SV_BulletFireFailed("impact-event-invalid");
                candidateImpactEvents.push_back(impact);
            }
            if (pendingEntityDamage)
                candidateEntityDamagePayloads.push_back(*pendingEntityDamage);
            // TODO(CODOL): the impact presentation is complete, but an
            // unregistered non-player entity still requires the specialized
            // vehicle/scriptable/destructible branch of general G_Damage.
            if (trace->hitEntityNum && !trace->ignoreHitEntity &&
                !hitDamageablePlayer &&
                std::ranges::none_of(
                    damageableEntities,
                    [trace](const auto &target) {
                        return target.entityNum == *trace->hitEntityNum;
                    }))
            {
                deferredImpact = true;
            }

            // CODREF(bullet_penetration): OLFinal sub_5923C0 and COD4
            // Bullet_FirePenetrate carry the forward trace back through this
            // loop for as many as five surfaces. A forward trace made from
            // inside a brush commonly returns the brush's exit face first;
            // only the next iteration can reach the player behind it.
            if (!input.plan.penetrate || !penetrationDepthResolver ||
                trace->hitEntityNum || trace->glassPieceIndex ||
                trace->trace.partGroup == BulletShieldPartGroup ||
                !trace->depthSurfaceType)
            {
                continue;
            }

            constexpr float PenetrationAdvance = 0.135f;
            constexpr float ReverseTraceAdvance = 0.01f;
            float damageMultiplier = 1.0f;
            auto penetrationEntry = *trace;
            for (std::uint8_t penetrationIndex{};
                 penetrationIndex != 5;
                 ++penetrationIndex)
            {
                if (penetrationEntry.hitEntityNum ||
                    penetrationEntry.glassPieceIndex ||
                    penetrationEntry.trace.partGroup == BulletShieldPartGroup ||
                    !penetrationEntry.depthSurfaceType)
                {
                    break;
                }
                const auto entryDepth = penetrationDepthResolver(
                    input.weaponAssetIndex,
                    penetrationEntry.depthSurfaceType);
                if (!entryDepth)
                {
                    deferredImpact = true;
                    break;
                }
                if (!std::isfinite(*entryDepth) || *entryDepth <= 0.0f)
                    break;

                const auto entryNormalDot = std::max(
                    0.125f,
                    -(penetrationEntry.trace.normal[0] * endpos->direction[0] +
                        penetrationEntry.trace.normal[1] * endpos->direction[1] +
                        penetrationEntry.trace.normal[2] * endpos->direction[2]));
                std::array<float, 3> throughStart{};
                for (std::size_t axis{}; axis != throughStart.size(); ++axis)
                {
                    throughStart[axis] = penetrationEntry.hitPosition[axis] +
                        endpos->direction[axis] *
                            (PenetrationAdvance / entryNormalDot);
                }
                const auto throughTrace = SV_BulletTrace({
                    .start = throughStart,
                    .end = endpos->end,
                    .firingEntityNum = input.firingEntityNum,
                    .glassPieceCount = static_cast<std::uint32_t>(
                        glassMetadata.initialPieces.size()),
                    .lastSurfaceType = penetrationEntry.depthSurfaceType,
                    .rifleBullet = input.rifleBullet,
                    .passFiringEntity = input.passFiringEntity,
                    .entitiesOnly = true,
                }, traceRunner, ignoreHitResolver);
                if (!throughTrace)
                    return SV_BulletFireFailed("penetration-forward-trace");

                const auto forwardHit = throughTrace->trace.hitType != 0;
                std::array<float, 3> reverseStart = endpos->end;
                if (forwardHit)
                {
                    reverseStart = throughTrace->hitPosition;
                    if (!throughTrace->hitEntityNum)
                    {
                        const auto reverseNormalDot = std::max(
                            0.125f,
                            throughTrace->trace.normal[0] * endpos->direction[0] +
                            throughTrace->trace.normal[1] * endpos->direction[1] +
                            throughTrace->trace.normal[2] * endpos->direction[2]);
                        for (std::size_t axis{};
                             axis != reverseStart.size();
                             ++axis)
                        {
                            reverseStart[axis] -= endpos->direction[axis] *
                                (ReverseTraceAdvance / reverseNormalDot);
                        }
                    }
                }
                std::array<float, 3> reverseEnd{};
                for (std::size_t axis{}; axis != reverseEnd.size(); ++axis)
                {
                    reverseEnd[axis] = penetrationEntry.hitPosition[axis] -
                        endpos->direction[axis] * ReverseTraceAdvance;
                }
                const auto reverseIgnoreEntity = throughTrace->hitEntityNum
                    .value_or(input.firingEntityNum);
                const auto reverseTrace = SV_BulletTrace({
                    .start = reverseStart,
                    .end = reverseEnd,
                    .firingEntityNum = reverseIgnoreEntity,
                    .glassPieceCount = static_cast<std::uint32_t>(
                        glassMetadata.initialPieces.size()),
                    .lastSurfaceType = throughTrace->depthSurfaceType,
                    .rifleBullet = input.rifleBullet,
                    .passFiringEntity = true,
                    .worldOnly = true,
                }, traceRunner, ignoreHitResolver);
                if (!reverseTrace)
                    return SV_BulletFireFailed("penetration-reverse-trace");

                const auto reverseHit = reverseTrace->trace.hitType != 0;
                const auto allSolid =
                    (reverseHit && reverseTrace->trace.allSolid) ||
                    (throughTrace->trace.startSolid &&
                        reverseTrace->trace.startSolid);
                auto maximumDepth = *entryDepth;
                if (reverseHit || allSolid)
                {
                    if (reverseHit && reverseTrace->depthSurfaceType)
                    {
                        const auto exitDepth = penetrationDepthResolver(
                            input.weaponAssetIndex,
                            reverseTrace->depthSurfaceType);
                        if (!exitDepth)
                        {
                            deferredImpact = true;
                            break;
                        }
                        if (!std::isfinite(*exitDepth) || *exitDepth <= 0.0f)
                            break;
                        maximumDepth = std::min(maximumDepth, *exitDepth);
                    }

                    const auto thicknessStart = allSolid
                        ? reverseStart
                        : reverseTrace->hitPosition;
                    const auto thicknessEnd = allSolid
                        ? reverseEnd
                        : penetrationEntry.hitPosition;
                    const auto wallDelta = std::array{
                        thicknessEnd[0] - thicknessStart[0],
                        thicknessEnd[1] - thicknessStart[1],
                        thicknessEnd[2] - thicknessStart[2],
                    };
                    const auto wallThickness = std::max(1.0f, std::sqrt(
                        wallDelta[0] * wallDelta[0] +
                        wallDelta[1] * wallDelta[1] +
                        wallDelta[2] * wallDelta[2]));
                    damageMultiplier -= wallThickness / maximumDepth;
                    if (!std::isfinite(damageMultiplier) ||
                        damageMultiplier <= 0.0f)
                    {
                        break;
                    }
                }
                if (!forwardHit)
                    break;
                if (executionStatus)
                {
                    executionStatus->traced = true;
                    executionStatus->commandTime = input.commandTime;
                    executionStatus->start = throughStart;
                    executionStatus->end = endpos->end;
                    executionStatus->trace = throughTrace->trace;
                    executionStatus->hitEntityNum = throughTrace->hitEntityNum;
                }
                if (throughTrace->trace.partGroup == BulletShieldPartGroup ||
                    throughTrace->glassPieceIndex)
                {
                    deferredImpact = true;
                    break;
                }

                bool throughHitDamageablePlayer{};
                bool throughHitDamageableEntity{};
                if (throughTrace->hitEntityNum &&
                    !throughTrace->ignoreHitEntity)
                {
                    const auto throughDelta = std::array{
                        throughTrace->hitPosition[0] - input.basis.muzzleTrace[0],
                        throughTrace->hitPosition[1] - input.basis.muzzleTrace[1],
                        throughTrace->hitPosition[2] - input.basis.muzzleTrace[2],
                    };
                    const auto throughDistance = std::sqrt(
                        throughDelta[0] * throughDelta[0] +
                        throughDelta[1] * throughDelta[1] +
                        throughDelta[2] * throughDelta[2]);
                    const auto throughDamage = SV_CalculateBulletDamage({
                        .curve = input.damageCurve,
                        .distance = throughDistance,
                        .damageMultiplier = damageMultiplier,
                    });
                    if (!throughDamage || *throughDamage < 0)
                        return SV_BulletFireFailed(
                            "penetration-damage-curve");

                    const auto target = std::ranges::find(
                        damageablePlayers,
                        *throughTrace->hitEntityNum,
                        &SvDamageablePlayerView::entityNum);
                    if (target != damageablePlayers.end() && *throughDamage)
                    {
                        if (throughTrace->trace.partGroup >= HitLocationCount)
                            return SV_BulletFireFailed(
                                "penetration-player-part-group");
                        const auto payload = SV_BuildPlayerDamagePayload({
                            .targetClientNum = target->clientNum,
                            .inflictorEntityNum = input.firingEntityNum,
                            .attackerEntityNum = input.firingEntityNum,
                            .baseDamage = *throughDamage,
                            .hitLocationMultiplier = input.hitLocationMultipliers[
                                throughTrace->trace.partGroup],
                            .methodOfDeath = input.plan.methodOfDeath,
                            .weaponAssetIndex = input.weaponAssetIndex,
                            .point = throughTrace->hitPosition,
                            .direction = endpos->direction,
                            .hitLocation = static_cast<std::uint8_t>(
                                throughTrace->trace.partGroup),
                            .boneIndex = throughTrace->trace.partName,
                        });
                        if (!payload)
                            return SV_BulletFireFailed(
                                "penetration-player-payload-build");
                        candidateDamagePayloads.push_back(*payload);
                        throughHitDamageablePlayer = true;
                        if (executionStatus)
                            executionStatus->playerDamageStaged = true;
                    }
                    if (!throughHitDamageablePlayer && *throughDamage)
                    {
                        const auto entityTarget = std::ranges::find(
                            damageableEntities,
                            *throughTrace->hitEntityNum,
                            &SvDamageableEntityView::entityNum);
                        if (entityTarget != damageableEntities.end())
                        {
                            if (throughTrace->trace.partGroup >= HitLocationCount)
                                return SV_BulletFireFailed(
                                    "penetration-entity-part-group");
                            const auto entityDamage = entityBulletDamage(*entityTarget, *throughDamage,
                                input.hitLocationMultipliers[throughTrace->trace.partGroup]);
                            if (!entityDamage)
                                return SV_BulletFireFailed("penetration-entity-location-damage");
                            const SvEntityDamagePayload payload{
                                .targetEntityNum = entityTarget->entityNum,
                                .targetGeneration = entityTarget->generation,
                                .inflictorEntityNum = input.firingEntityNum,
                                .attackerEntityNum = input.firingEntityNum,
                                .damage = *entityDamage,
                                .methodOfDeath = input.plan.methodOfDeath,
                                .weaponAssetIndex = input.weaponAssetIndex,
                                .point = throughTrace->hitPosition,
                                .direction = endpos->direction,
                                .hitLocation = static_cast<std::uint8_t>(
                                    throughTrace->trace.partGroup),
                                .boneIndex = throughTrace->trace.partName,
                            };
                            if (!SV_IsEntityDamagePayloadValid(
                                    payload,
                                    MaximumGameEntities,
                                    MethodOfDeathCount,
                                    HitLocationCount))
                            {
                                return SV_BulletFireFailed(
                                    "penetration-entity-payload-invalid");
                            }
                            candidateEntityDamagePayloads.push_back(payload);
                            throughHitDamageableEntity = true;
                            if (executionStatus)
                                executionStatus->entityDamageStaged = true;
                        }
                    }
                }

                if (!throughTrace->ignoreHitEntity &&
                    !(throughTrace->trace.surfaceFlags & 4))
                {
                    if (!directionEncoder)
                        return SV_BulletFireFailed(
                            "penetration-direction-encoder-missing");
                    const auto direction = directionEncoder(
                        throughTrace->trace.normal);
                    if (!direction)
                        return SV_BulletFireFailed(
                            "penetration-direction-encode");
                    const SvBulletImpactEvent impact{
                        .position = throughTrace->hitPosition,
                        .weaponAssetIndex = input.weaponAssetIndex,
                        .sourceEntityNum = static_cast<std::uint16_t>(
                            input.firingEntityNum),
                        .hitEntityNum = static_cast<std::uint16_t>(
                            throughTrace->hitEntityNum.value_or(
                                BulletNoneEntityNum)),
                        .direction = *direction,
                        .surfaceType = throughTrace->depthSurfaceType,
                    };
                    if (!SV_IsBulletImpactEventValid(impact))
                        return SV_BulletFireFailed(
                            "penetration-impact-event-invalid");
                    candidateImpactEvents.push_back(impact);
                }
                if (throughTrace->hitEntityNum)
                {
                    if (!throughTrace->ignoreHitEntity &&
                        !throughHitDamageablePlayer &&
                        !throughHitDamageableEntity)
                    {
                        deferredImpact = true;
                    }
                    break;
                }
                penetrationEntry = *throughTrace;
            }
        }
        playerDamagePayloads = std::move(candidateDamagePayloads);
        entityDamagePayloads = std::move(candidateEntityDamagePayloads);
        bulletImpactEvents = std::move(candidateImpactEvents);
        glassRollback.commit();
        const auto result = deferredImpact
            ? SvBulletFireExecutionResult::DeferredImpact
            : SvBulletFireExecutionResult::Applied;
        if (executionStatus)
            executionStatus->result = result;
        return result;
    }
}
