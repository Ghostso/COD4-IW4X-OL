#include "sv_weapon_fire_mp.hpp"
#include "sv_gamestate_mp.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer
{
    namespace
    {
        // OLMOD(native-fire-basis-guard): source-only finite/vector helpers for
        // the normalized basis admission below. They do not reproduce CODOL's
        // general vector library or enter the retained native ABI directly.
        bool finiteVector(const std::array<float, 3> &value)
        {
            return std::ranges::all_of(value, [](const float component) {
                return std::isfinite(component);
            });
        }

        float lengthSquared(const std::array<float, 3> &value)
        {
            return value[0] * value[0] + value[1] * value[1] +
                value[2] * value[2];
        }

        float dot(
            const std::array<float, 3> &left,
            const std::array<float, 3> &right)
        {
            return left[0] * right[0] + left[1] * right[1] +
                left[2] * right[2];
        }

        std::array<float, 3> cross(
            const std::array<float, 3> &left,
            const std::array<float, 3> &right)
        {
            return {
                left[1] * right[2] - left[2] * right[1],
                left[2] * right[0] - left[0] * right[2],
                left[0] * right[1] - left[1] * right[0],
            };
        }
    }

    bool SV_IsWeaponFireBasisValid(const SvWeaponFireBasis &basis)
    {
        // OLMOD(native-fire-basis-guard): this validates the normalized source
        // adapter before it crosses into retained CODOL x86 code. It is not a
        // recovered COD predicate or a substitute for FireWeapon weaponParms.
        constexpr float AxisTolerance = 0.002f;
        if (!basis.weaponAssetIndex ||
            basis.weaponAssetIndex > MaximumWeaponAssetIndex ||
            !std::isfinite(basis.weaponPositionFraction) ||
            basis.weaponPositionFraction < 0.0f ||
            basis.weaponPositionFraction > 1.0f ||
            !finiteVector(basis.muzzleTrace) || !finiteVector(basis.forward) ||
            !finiteVector(basis.right) || !finiteVector(basis.up))
        {
            return false;
        }

        const auto unitLength = [](const std::array<float, 3> &axis) {
            return std::abs(lengthSquared(axis) - 1.0f) <= AxisTolerance;
        };
        return unitLength(basis.forward) && unitLength(basis.right) &&
            unitLength(basis.up) &&
            std::abs(dot(basis.forward, basis.right)) <= AxisTolerance &&
            std::abs(dot(basis.forward, basis.up)) <= AxisTolerance &&
            std::abs(dot(basis.right, basis.up)) <= AxisTolerance &&
            std::abs(dot(cross(basis.forward, basis.right), basis.up) + 1.0f)
                <= AxisTolerance;
    }

    bool SV_IsBulletEndposRequestValid(
        const SvBulletEndposRequest &request)
    {
        // OLMOD(native-bullet-endpos-guard): Bullet_Endpos 0x0055AEB0 trusts
        // all pointers and floating-point inputs. The source/native boundary
        // therefore rejects malformed requests before invoking its custom ABI.
        return SV_IsWeaponFireBasisValid(request.basis) &&
            std::isfinite(request.spread) && request.spread >= 0.0f &&
            std::isfinite(request.maxRange) && request.maxRange > 0.0f &&
            request.maxRange <= StandardBulletRange;
    }

    std::uint32_t SV_SeedBulletRandom(
        const std::uint32_t commandTime,
        const SvPlayerHand hand) noexcept
    {
        // CODREF(fire_weapon): CODOL's retained client fire path at
        // 0x0055F5A1 reads playerState.commandTime (or the local clock only
        // when no playerState exists), adds 10 for the left-hand event, and
        // executes these exact four 214013*x+2531011 rounds before the shot
        // loop. Bullet_RandomDir 0x0055AE10 then advances the same seed twice
        // per Bullet_Endpos call. BO2 Bullet_Fire 0x005AED50 instead calls
        // BG_seedRandWithGameTime, so its XOR/shift seed is not imported.
        auto seed = commandTime + (hand == SvPlayerHand::Left ? 10u : 0u);
        for (auto index = 0; index < 4; ++index)
            seed = seed * 214013u + 2531011u;
        return seed;
    }

    bool SV_IsWeaponDamageCurveValid(const SvWeaponDamageCurve &curve)
    {
        // OLMOD(weapon-damage-curve-guard): CODOL weapon assets are trusted by
        // native gameplay. This fail-closed source check protects the recovered
        // six-point calculation from incomplete or corrupt registry data.
        return std::ranges::all_of(curve.damage, [](const auto damage) {
            return damage >= 0;
        }) && std::ranges::all_of(curve.ranges, [](const auto range) {
            return std::isfinite(range) && range >= 0.0f &&
                range <= MaximumWeaponDamageRange;
        }) && curve.ranges.front() > 0.0f && curve.ranges.back() > 0.0f;
    }

    std::optional<std::int32_t> SV_CalculateBulletDamage(
        const SvBulletDamageInput &input)
    {
        // CODREF(bullet_process): BO1 Bullet_GetDamage 0x005F4820 and Ghosts
        // 0x140109390 establish range falloff ownership, while BO2
        // BG_GetWeaponDamageForRange 0x0098D3A0 supplies the six-point control
        // flow selected by CODOL's native WeaponDef arrays at +0xBB4/+0xBCC.
        // CODDIFF(bullet_process): only the CODOL-confirmed six-point asset
        // shape is copied; BO2 structure offsets and attachment layout are not.
        // OLMOD(weapon-damage-input-guard): native WeaponDef storage and callers
        // are trusted. The source rejects malformed copied curves, multipliers,
        // overflow, and impossible interpolation before publishing damage.
        if (!SV_IsWeaponDamageCurveValid(input.curve) ||
            !std::isfinite(input.distance) || input.distance < 0.0f ||
            !std::isfinite(input.damageMultiplier) ||
            input.damageMultiplier < 0.0f ||
            !std::isfinite(input.damageRangeScale) ||
            input.damageRangeScale <= 0.0f)
        {
            return std::nullopt;
        }

        std::array<float, WeaponDamageCurvePointCount> scaledRanges{};
        for (std::size_t index = 0; index < scaledRanges.size(); ++index)
        {
            scaledRanges[index] =
                input.curve.ranges[index] * input.damageRangeScale;
            if (!std::isfinite(scaledRanges[index]))
                return std::nullopt;
        }

        std::int32_t damage{};
        if (input.distance <= scaledRanges.front())
        {
            damage = input.curve.damage.front();
        }
        else if (input.distance > scaledRanges.back())
        {
            damage = input.curve.damage.back();
        }
        else
        {
            std::size_t previousIndex = 0;
            bool foundRange = false;
            for (std::size_t index = 1; index < scaledRanges.size(); ++index)
            {
                if (scaledRanges[index] < 0.001f)
                    continue;
                if (scaledRanges[index] <= input.distance)
                {
                    previousIndex = index;
                    continue;
                }

                const auto rangeWidth =
                    scaledRanges[index] - scaledRanges[previousIndex];
                if (rangeWidth <= 0.0f)
                    return std::nullopt;
                const auto lerpAmount =
                    (input.distance - scaledRanges[previousIndex]) /
                    rangeWidth;
                if (!std::isfinite(lerpAmount) || lerpAmount < 0.0f ||
                    lerpAmount > 1.0f)
                {
                    return std::nullopt;
                }
                const auto interpolated =
                    static_cast<float>(input.curve.damage[previousIndex]) *
                        (1.0f - lerpAmount) +
                    static_cast<float>(input.curve.damage[index]) * lerpAmount;
                if (!std::isfinite(interpolated) || interpolated < 0.0f ||
                    static_cast<double>(interpolated) >
                        std::numeric_limits<std::int32_t>::max())
                {
                    return std::nullopt;
                }
                damage = static_cast<std::int32_t>(interpolated);
                foundRange = true;
                break;
            }
            // BO2 falls back to damage[0] when distance equals the final
            // active range exactly; only distances beyond it use damage[5].
            if (!foundRange)
                damage = input.curve.damage.front();
        }

        const auto scaledDamage =
            static_cast<float>(damage) * input.damageMultiplier;
        if (!std::isfinite(scaledDamage) || scaledDamage < 0.0f ||
            static_cast<double>(scaledDamage) >
                std::numeric_limits<std::int32_t>::max())
        {
            return std::nullopt;
        }
        return static_cast<std::int32_t>(scaledDamage);
    }

    std::optional<SvBulletFirePlan> SV_BuildBulletFirePlan(
        const SvBulletFirePlanInput &input)
    {
        // OLMOD(bullet-fire-plan-admission): this normalized plan is the source
        // transaction's substitute for native weaponParms/WeaponDef ownership.
        // Invalid copied weapon metadata must fail before a command can stage
        // endpos, trace, presentation, or damage side effects.
        if (input.weaponType != WeaponTypeBullet ||
            !SV_IsWeaponDamageCurveValid(input.damageCurve))
        {
            return std::nullopt;
        }

        const auto spreadWeapon =
            input.weaponClass == WeaponClassSpread &&
            !input.bulletExplosiveDamage;
        if (spreadWeapon &&
            (!input.shotCount ||
                input.damageCurve.ranges.back() > StandardBulletRange))
            return std::nullopt;

        // CODREF(fire_weapon): CODOL 0x0055F51A..0x0055F571 selects MOD 3 for
        // explosive bullets, otherwise rifleFlag+1; class 4 plus non-explosive
        // selects shotCount and damageRange[5], otherwise one shot at the
        // 0x46000000 (8192.0f) range constant. The recovered hand seed is
        // initialized before this same shot loop. BO1 Bullet_Fire 0x005F38A0
        // and Ghosts Bullet_Fire_Internal 0x140108DD0 confirm the surrounding
        // weaponParms, anti-lag, shot-loop, and penetration responsibilities.
        return SvBulletFirePlan{
            .randomSeed = SV_SeedBulletRandom(input.commandTime, input.hand),
            .shotCount = spreadWeapon ? input.shotCount : std::uint8_t{ 1 },
            .methodOfDeath = input.bulletExplosiveDamage
                ? std::uint8_t{ 3 }
                : static_cast<std::uint8_t>(input.rifleBullet ? 2 : 1),
            .maxRange = spreadWeapon
                ? input.damageCurve.ranges.back()
                : StandardBulletRange,
            .penetrate = input.penetrateType != 0 &&
                !input.bulletExplosiveDamage,
        };
    }

    std::optional<SvWeaponSpreadResult> SV_CalculateWeaponSpread(
        const SvWeaponSpreadInput &input)
    {
        // CODREF(fire_weapon): COD4 FireWeapon uses the hip cone until
        // fWeaponPosFrac is exactly 1.0, then selects the ADS cone. Its reticle
        // contracts independently through CG_TransitionToAds, so the visual
        // transition is not the ballistic interpolation rule. Recovered OLFinal
        // CG_FireWeapon uses the same full-ADS boundary.
        // CODDIFF(fire_weapon): playerSizeScale * 11/40/60 is an ol-mod CODOL
        // adapter difference; none of the three reference functions contains
        // that scaling. Do not promote it to recovered native behavior without
        // a CODOL player-size/view-height producer or runtime trace.
        // CODREF(coAbilityModifiersTable): modBulletSpreadScale is modifier 6,
        // default 1.0. The selectable Steady Aim row adds -0.2, producing the
        // live CODOL multiplier 0.8. As in CoD4 BG_GetSpreadForWeapon, it scales
        // the resolved hip minimum and maximum before ADS selection.
        // OLMOD(weapon-spread-input-guard): reference implementations trust
        // playerState and WeaponDef. The source boundary validates its copied
        // scalar view because those owners are reconstructed independently.
        const std::array values{
            input.viewHeightCurrent,
            input.playerSizeScale,
            input.weaponPositionFraction,
            input.normalizedAimSpreadScale,
            input.hipSpreadStandMin,
            input.hipSpreadCrouchMin,
            input.hipSpreadProneMin,
            input.hipSpreadStandMax,
            input.hipSpreadCrouchMax,
            input.hipSpreadProneMax,
            input.adsSpread,
            input.perkSpreadScale,
        };
        if (!std::ranges::all_of(values, [](const float value) {
                return std::isfinite(value);
            }) || input.playerSizeScale <= 0.0f ||
            input.weaponPositionFraction < 0.0f ||
            input.weaponPositionFraction > 1.0f ||
            input.normalizedAimSpreadScale < 0.0f ||
            input.normalizedAimSpreadScale > 1.0f ||
            input.spreadOverride < 0 || input.spreadOverrideState < 0 ||
            input.spreadOverrideState > 2 ||
            input.hipSpreadStandMin < 0.0f ||
            input.hipSpreadCrouchMin < 0.0f ||
            input.hipSpreadProneMin < 0.0f ||
            input.hipSpreadStandMax < input.hipSpreadStandMin ||
            input.hipSpreadCrouchMax < input.hipSpreadCrouchMin ||
            input.hipSpreadProneMax < input.hipSpreadProneMin ||
            input.adsSpread < 0.0f || input.perkSpreadScale < 0.0f ||
            input.perkSpreadScale > 1.0f)
        {
            return std::nullopt;
        }

        SvWeaponSpreadResult result{};
        if (input.spreadOverrideState == 2)
        {
            result.minimum = static_cast<float>(input.spreadOverride);
            result.maximum = result.minimum;
        }
        else
        {
            const auto proneHeight = input.playerSizeScale * 11.0f;
            const auto crouchHeight = input.playerSizeScale * 40.0f;
            const auto standHeight = input.playerSizeScale * 60.0f;
            if (input.viewHeightCurrent <= crouchHeight)
            {
                const auto fraction =
                    (input.viewHeightCurrent - proneHeight) /
                    (crouchHeight - proneHeight);
                result.minimum =
                    (input.hipSpreadCrouchMin - input.hipSpreadProneMin) *
                        fraction +
                    input.hipSpreadProneMin;
                result.maximum =
                    (input.hipSpreadCrouchMax - input.hipSpreadProneMax) *
                        fraction +
                    input.hipSpreadProneMax;
            }
            else
            {
                const auto fraction =
                    (input.viewHeightCurrent - crouchHeight) /
                    (standHeight - crouchHeight);
                result.minimum =
                    (input.hipSpreadStandMin - input.hipSpreadCrouchMin) *
                        fraction +
                    input.hipSpreadCrouchMin;
                result.maximum =
                    (input.hipSpreadStandMax - input.hipSpreadCrouchMax) *
                        fraction +
                    input.hipSpreadCrouchMax;
            }
        }
        if (input.spreadOverrideState == 1)
            result.maximum = static_cast<float>(input.spreadOverride);

        result.minimum *= input.perkSpreadScale;
        result.maximum *= input.perkSpreadScale;

        result.firing = input.weaponPositionFraction == 1.0f
            ? (result.maximum - input.adsSpread) *
                    input.normalizedAimSpreadScale +
                input.adsSpread
            : (result.maximum - result.minimum) *
                    input.normalizedAimSpreadScale +
                result.minimum;
        if (!std::isfinite(result.minimum) || !std::isfinite(result.maximum) ||
            !std::isfinite(result.firing) || result.minimum < 0.0f ||
            result.maximum < result.minimum || result.firing < 0.0f)
        {
            return std::nullopt;
        }
        return result;
    }
}
