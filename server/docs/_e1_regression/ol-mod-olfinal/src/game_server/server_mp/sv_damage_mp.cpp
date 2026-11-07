#include "sv_damage_mp.hpp"
#include "sv_gamestate_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    namespace
    {
        bool finiteVector(const std::optional<std::array<float, 3>> &value)
        {
            return !value ||
                std::ranges::all_of(*value, [](const float component) {
                    return std::isfinite(component);
                });
        }

        bool validEntityReference(
            const std::optional<std::uint32_t> entityNum,
            const std::uint32_t maximumEntities)
        {
            return !entityNum || *entityNum < maximumEntities;
        }
    }

    bool SV_IsPlayerDamagePayloadValid(
        const SvPlayerDamagePayload &payload,
        const SvPlayerDamagePayloadLimits &limits)
    {
        // OLMOD(player-damage-script-boundary): source admission policy before
        // queued Lua dispatch; no native health mutation occurs here.
        return limits.maximumClients > 0 && limits.maximumEntities > 0 &&
            limits.methodOfDeathCount > 0 && limits.hitLocationCount > 0 &&
            payload.targetClientNum < limits.maximumClients &&
            validEntityReference(
                payload.inflictorEntityNum, limits.maximumEntities) &&
            validEntityReference(
                payload.attackerEntityNum, limits.maximumEntities) &&
            payload.damage > 0 &&
            payload.weaponAssetIndex <= MaximumWeaponAssetIndex &&
            payload.methodOfDeath < limits.methodOfDeathCount &&
            payload.hitLocation < limits.hitLocationCount &&
            finiteVector(payload.point) && finiteVector(payload.direction);
    }

    std::optional<SvPlayerDamagePayload> SV_BuildPlayerDamagePayload(
        const SvPlayerDamageBuildInput &input)
    {
        // CODREF(g_damage): BO1 PlayerCmd_finishPlayerDamage 0x006080A0 and
        // Ghosts G_DamageClient 0x140126B70 validate target/weapon/MOD/hitloc
        // before the script damage boundary. The hit-location multiplier is
        // applied before the immutable payload reaches gameplay script.
        // CODDIFF(g_damage): this is a transaction input builder, not a
        // recovered G_DamageClient implementation; it deliberately owns no
        // knockback, protection, pain, last-stand, or entity-handler effects.
        if (input.targetClientNum >= MaximumGameClients ||
            input.inflictorEntityNum >= MaximumGameEntities ||
            input.attackerEntityNum >= MaximumGameEntities ||
            input.baseDamage <= 0 ||
            !std::isfinite(input.hitLocationMultiplier) ||
            input.hitLocationMultiplier < 0.0f ||
            input.hitLocationMultiplier > 20.0f ||
            input.methodOfDeath >= MethodOfDeathCount ||
            // FALLING IS THE ONE METHOD WITH NO WEAPON. PM_CrashLand raises
            // EV_LANDING_PAIN out of pmove with a damage parameter and nothing
            // else; there is no firing weapon to name. Demanding a nonzero
            // index here would either drop every fall -- the held weapon is
            // legitimately 0 during the unarmed window after a spawn -- or
            // force the caller to invent an attribution the engine never made.
            (!input.weaponAssetIndex &&
                input.methodOfDeath != SvMethodOfDeathFalling) ||
            input.weaponAssetIndex > MaximumWeaponAssetIndex ||
            input.hitLocation >= HitLocationCount ||
            !finiteVector(input.point) || !finiteVector(input.direction))
        {
            return std::nullopt;
        }
        const auto scaled = static_cast<float>(input.baseDamage) *
            input.hitLocationMultiplier;
        constexpr auto Int32UpperExclusive = 2147483648.0f;
        if (!std::isfinite(scaled) || scaled >= Int32UpperExclusive)
        {
            return std::nullopt;
        }
        const auto damage = std::max(1, static_cast<std::int32_t>(scaled));
        return SvPlayerDamagePayload{
            .targetClientNum = input.targetClientNum,
            .inflictorEntityNum = input.inflictorEntityNum,
            .attackerEntityNum = input.attackerEntityNum,
            .damage = damage,
            .damageFlags = input.damageFlags,
            .methodOfDeath = input.methodOfDeath,
            .weaponAssetIndex = input.weaponAssetIndex,
            .point = input.point,
            .direction = input.direction,
            .hitLocation = input.hitLocation,
            .timeOffset = input.timeOffset,
            .boneIndex = input.boneIndex,
        };
    }

    bool SV_IsEntityDamageStateValid(const SvEntityDamageState &state)
    {
        // OLMOD(entity-damage-owner-registration): only positive-health state
        // may be registered or replaced as a live damage owner. Terminal state
        // is retained for status/events but no longer exported as capability.
        return state.health > 0;
    }

    bool SV_IsEntityDamagePayloadValid(
        const SvEntityDamagePayload &payload,
        const std::uint32_t maximumEntities,
        const std::uint32_t methodOfDeathCount,
        const std::uint32_t hitLocationCount)
    {
        // OLMOD(entity-damage-transaction): current producers are ordinary
        // bullets and therefore require a nonzero frozen weapon. Radius,
        // missile, melee and script producers need separate recovered policy.
        return maximumEntities > 0 && methodOfDeathCount > 0 &&
            hitLocationCount > 0 &&
            payload.targetEntityNum < maximumEntities &&
            validEntityReference(payload.inflictorEntityNum, maximumEntities) &&
            validEntityReference(payload.attackerEntityNum, maximumEntities) &&
            payload.damage > 0 && payload.weaponAssetIndex > 0 &&
            payload.weaponAssetIndex <= MaximumWeaponAssetIndex &&
            payload.methodOfDeath < methodOfDeathCount &&
            payload.hitLocation < hitLocationCount &&
            finiteVector(payload.point) && finiteVector(payload.direction);
    }
}
