#pragma once

// For WeaponConfigStringCount, which the obituary parameter is defined in
// terms of. sv_gamestate_mp depends on nothing but qcommon/msg_mp.
#include "sv_gamestate_mp.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

namespace CodolGameServer
{
    // CODREF(g_damage): CODOL wire/client consumers and reference G_Damage
    // families constrain these title-level counts. Source schemas below do not
    // reproduce native gentity/gclient layouts or a script-VM stack frame.
    inline constexpr std::uint32_t MaximumGameClients = 18;
    inline constexpr std::uint32_t MaximumGameEntities = 2048;
    // CODDIFF(1649370): 21 was neither build's number. out.exe registers exactly
    // TWENTY methods of death, and it registers them one at a time into a
    // contiguous WORD array so the order is not a guess:
    //
    //   0 UNKNOWN            5 GRENADE_SPLASH   10 GAS              15 SUICIDE
    //   1 PISTOL_BULLET      6 PROJECTILE       11 DOGBITE          16 TRIGGER_HURT
    //   2 RIFLE_BULLET       7 PROJECTILE_SPL   12 SPECIAL_ATTACK   17 EXPLOSIVE
    //   3 EXPLOSIVE_BULLET   8 MELEE            13 CRUSH            18 IMPACT
    //   4 GRENADE            9 HEAD_SHOT        14 FALLING          19 PUNISH
    //
    // read off sub_4EDE90 at 0x004EED35..0x004EEEC4, which pushes each name to
    // the string allocator and stores the returned id into word_032B360C,
    // word_032B360E, ... word_032B3632, stepping two bytes; `script_vehicle`
    // begins an unrelated group at word_032B3634. 3.3.3.3 has EIGHTEEN -- it
    // carries neither MOD_PUNISH nor MOD_SPECIAL_ATTACK anywhere in its image --
    // so this is a per-build enum that GREW, not a shared constant, and 21 was
    // one past the end even here. SV_BuildBulletFirePlan's own 1/2/3 land on
    // PISTOL_BULLET / RIFLE_BULLET / EXPLOSIVE_BULLET in this order, which is
    // what says the order is read right and not merely plausible.
    inline constexpr std::uint32_t MethodOfDeathCount = 20;
    // NOT SETTLED, and it is ENGINE rather than the SOURCE it was filed as:
    // EngineBindings.cpp reads exactly this many floats out of the native
    // WeaponDef at WeaponHitLocationMultipliersOffset, so a wrong value reads
    // past the array. out.exe's hit-location NAME table is 19 entries -- none,
    // helmet, head, neck, torso_upper, torso_lower, then the arm/hand/leg/foot
    // pairs, then gun -- at 0x00E4FB30 and 0x00E5AFB0, and 3.3.3.3's is the
    // same 19 in the same order at 0x00CD83B8 and 0x00CDF3C8, so the NAMED
    // domain is 0..18 on both. But partGroup is not the name index:
    // BulletShieldPartGroup is 19, outside it. Do not tighten this to 19 until
    // the WeaponDef array's real length is read; scanning for +0xD4C alone does
    // not answer it, because the only hits are a HUD constructor.
    inline constexpr std::size_t HitLocationCount = 21;

    // READ OFF out.exe 2026-08-23, 0x00E4FB30 and 0x00E5AFB0, and the table is
    // TWENTY entries, not nineteen: entry 19 IS `shield`. The comment above
    // says the name table is 19 and calls BulletShieldPartGroup=19 "outside
    // it"; it is inside it, so "one space with a synthetic 19" was the right
    // reading of the two that note left open.
    //
    //   0 none  1 helmet  2 head  3 neck  4 torso_upper  5 torso_lower
    //   6..11 the arm and hand pairs   12..17 the leg and foot pairs
    //   18 gun  19 shield
    // WHICH death animation the anim script selects, and the ONLY reason
    // BG_AnimScriptEvent(DEATH) has ever returned -1 on this server: CoD picks
    // a death by these three, and nothing here wrote any of them.
    //
    // Values are this build's own, read off out.exe's condition tables at
    // 0x00E60828 / 0x00E608C8 -- see EngineBindings::runServerDeathAnimation
    // for the calibration. All three are ANIM_CONDTYPE_VALUE (condType 1), so
    // they are plain integers and not bitflags.
    struct SvDeathAnimationConditions
    {
        std::uint32_t hitLocation{};    // 0 TORSO  1 HEAD  2 NECK  3 LEGS
        std::uint32_t damageType{};     // 0 BULLET 1 EXPLOSION_LIGHT 2 EXPLOSION
        std::uint32_t hitDirection{};   // 0 FRONT  1 LEFT  2 RIGHT 3 BACK

        bool operator==(const SvDeathAnimationConditions &) const = default;
    };

    inline constexpr std::uint8_t SvAnimHitLocationHelmetPart = 1;
    inline constexpr std::uint8_t SvAnimHitLocationHeadPart = 2;
    inline constexpr std::uint8_t SvAnimHitLocationNeckPart = 3;
    inline constexpr std::uint8_t SvAnimHitLocationFirstLegPart = 12;
    inline constexpr std::uint8_t SvAnimHitLocationLastLegPart = 17;

    // The anim script's own HITLOCATION values -- out.exe 0x00E606C0, condition
    // 11, condType 1 (a VALUE, not bitflags).
    inline constexpr std::uint32_t SvAnimHitLocationTorso = 0;
    inline constexpr std::uint32_t SvAnimHitLocationHead = 1;
    inline constexpr std::uint32_t SvAnimHitLocationNeck = 2;
    inline constexpr std::uint32_t SvAnimHitLocationLegs = 3;

    // DAMAGETYPE -- out.exe 0x00E60688, condition 10.
    inline constexpr std::uint32_t SvAnimDamageTypeBullet = 0;
    inline constexpr std::uint32_t SvAnimDamageTypeExplosionLight = 1;
    inline constexpr std::uint32_t SvAnimDamageTypeExplosion = 2;

    // HITDIRECTION -- out.exe 0x00E606E8, condition 12.
    inline constexpr std::uint32_t SvAnimHitDirectionFront = 0;
    inline constexpr std::uint32_t SvAnimHitDirectionLeft = 1;
    inline constexpr std::uint32_t SvAnimHitDirectionRight = 2;
    inline constexpr std::uint32_t SvAnimHitDirectionBack = 3;

    // The method-of-death enum, read off the 20 names from MOD_UNKNOWN at
    // out.exe 0x00DBA318 -- exactly MethodOfDeathCount above.
    // MOD_FALLING. Index 14 of the twenty methods out.exe registers, listed
    // in the table at the top of this header.
    inline constexpr std::uint8_t SvMethodOfDeathUnknown = 0;
    inline constexpr std::uint8_t SvMethodOfDeathPistolBullet = 1;
    inline constexpr std::uint8_t SvMethodOfDeathRifleBullet = 2;
    inline constexpr std::uint8_t SvMethodOfDeathFalling = 14;
    inline constexpr std::uint8_t SvMethodOfDeathExplosiveBullet = 3;
    inline constexpr std::uint8_t SvMethodOfDeathGrenade = 4;
    inline constexpr std::uint8_t SvMethodOfDeathGrenadeSplash = 5;
    inline constexpr std::uint8_t SvMethodOfDeathProjectile = 6;
    inline constexpr std::uint8_t SvMethodOfDeathProjectileSplash = 7;
    // CODREF(mod_enum): 8 is read straight out of out.exe's own MOD table at
    // 0x00DBA318, which indexes MOD_UNKNOWN 0 .. MOD_MELEE 8 .. MOD_FALLING 14.
    // MOD_FALLING lands on 14 there, which is the value section 156's fall
    // damage arrived at by a completely different route -- so the table's
    // indexing is validated, not merely plausible. It lived in sv_melee_mp.hpp
    // until the obituary needed the same set.
    inline constexpr std::uint8_t SvMethodOfDeathMelee = 8;
    inline constexpr std::uint8_t SvMethodOfDeathHeadShot = 9;
    inline constexpr std::uint8_t SvMethodOfDeathDogBite = 11;
    inline constexpr std::uint8_t SvMethodOfDeathCrush = 13;
    inline constexpr std::uint8_t SvMethodOfDeathSuicide = 15;
    inline constexpr std::uint8_t SvMethodOfDeathTriggerHurt = 16;
    inline constexpr std::uint8_t SvMethodOfDeathExplosive = 17;
    inline constexpr std::uint8_t SvMethodOfDeathImpact = 18;

    [[nodiscard]] constexpr bool SV_IsBulletPaintMethodOfDeath(
        const std::uint8_t methodOfDeath)
    {
        return methodOfDeath == SvMethodOfDeathPistolBullet ||
            methodOfDeath == SvMethodOfDeathRifleBullet ||
            methodOfDeath == SvMethodOfDeathHeadShot;
    }

    [[nodiscard]] constexpr bool SV_IsExplosivePaintMethodOfDeath(
        const std::uint8_t methodOfDeath)
    {
        return methodOfDeath == SvMethodOfDeathExplosiveBullet ||
            methodOfDeath == SvMethodOfDeathGrenade ||
            methodOfDeath == SvMethodOfDeathGrenadeSplash ||
            methodOfDeath == SvMethodOfDeathProjectile ||
            methodOfDeath == SvMethodOfDeathProjectileSplash ||
            methodOfDeath == SvMethodOfDeathExplosive;
    }

    // THE OBITUARY'S ONE PAYLOAD, AND THE CLIENT WROTE THE RULE.
    //
    // CG_Obituary (out.exe 0x00531080) reads a 12-bit parameter and branches on
    // it exactly once:
    //
    //     if ((parm & 0xFFF) >= 0x6A4)      // 1700 == WeaponConfigStringCount
    //         icon = killicondied, then switch (parm - 1700):
    //             8 killiconmelee   9 killiconheadshot  11 hud_obit_dogs
    //            13 killiconcrush  14 killiconfalling   15 killiconsuicide
    //            16 killicondied   18 killiconimpact    default: killicondied
    //     else
    //         icon = weaponDef[parm]->killIcon
    //
    // Those eight switch cases land on MOD_MELEE, MOD_HEAD_SHOT, MOD_DOGBITE,
    // MOD_CRUSH, MOD_FALLING, MOD_SUICIDE, MOD_TRIGGER_HURT and MOD_IMPACT of
    // the twenty-name table above -- eight independent agreements between a
    // switch and a string array that were read by different routes.
    //
    // AND RETAIL'S OWN CHOICE IS MEASURED, not inferred from the branch. Across
    // the 145 obituaries of the dm demo the parameter is 1708 twelve times
    // (1700 + MELEE), 1709 eight times (1700 + HEAD_SHOT), 1718 once
    // (1700 + IMPACT), and a plain weapon index the other 124. So a method with
    // an icon is sent as the method; everything else is sent as the weapon.
    [[nodiscard]] constexpr bool SV_MethodOfDeathHasKillIcon(
        const std::uint8_t methodOfDeath)
    {
        return methodOfDeath == SvMethodOfDeathMelee ||
            methodOfDeath == SvMethodOfDeathHeadShot ||
            methodOfDeath == SvMethodOfDeathDogBite ||
            methodOfDeath == SvMethodOfDeathCrush ||
            methodOfDeath == SvMethodOfDeathFalling ||
            methodOfDeath == SvMethodOfDeathSuicide ||
            methodOfDeath == SvMethodOfDeathTriggerHurt ||
            methodOfDeath == SvMethodOfDeathImpact;
    }

    [[nodiscard]] constexpr std::uint16_t SV_ObituaryEventParameter(
        const std::uint8_t methodOfDeath,
        const std::uint16_t weaponAssetIndex)
    {
        if (SV_MethodOfDeathHasKillIcon(methodOfDeath))
        {
            return static_cast<std::uint16_t>(
                WeaponConfigStringCount + methodOfDeath);
        }
        // A weapon index at or past the configstring band would index the
        // client's weapon table out of range, so it takes the same road as no
        // weapon at all: 1700 + MOD_UNKNOWN reaches the switch default, which
        // is the generic `killicondied` the branch already set.
        if (!weaponAssetIndex || weaponAssetIndex >= WeaponConfigStringCount)
        {
            return static_cast<std::uint16_t>(
                WeaponConfigStringCount + SvMethodOfDeathUnknown);
        }
        return weaponAssetIndex;
    }

    static_assert(SV_ObituaryEventParameter(SvMethodOfDeathMelee, 1284) == 1708);
    static_assert(SV_ObituaryEventParameter(SvMethodOfDeathHeadShot, 1284) == 1709);
    static_assert(SV_ObituaryEventParameter(SvMethodOfDeathImpact, 0) == 1718);
    // MOD_RIFLE_BULLET has no icon of its own, so the weapon survives -- this
    // is the demo's own most common obituary, 23 of the 145.
    static_assert(SV_ObituaryEventParameter(2, 1260) == 1260);
    static_assert(SV_ObituaryEventParameter(2, 0) == 1700);

    struct SvDamageablePlayerView
    {
        // OLMOD(damage-capability-view): immutable command-local capability,
        // rebuilt from authoritative live player/entity ownership.
        std::uint32_t entityNum{};
        std::uint32_t clientNum{};

        bool operator==(const SvDamageablePlayerView &) const = default;
    };

    enum class SvEntityDamageKind : std::uint8_t
    {
        Generic,
        Destructible,
    };

    struct SvDamageableEntityView
    {
        // OLMOD(damage-capability-view): generation prevents a queued hit from
        // mutating a different entity after slot reuse.
        std::uint32_t entityNum{};
        std::uint32_t generation{};
        SvEntityDamageKind kind{};

        // OLMOD(zombie-hit-location): authoritative capability, not a native
        // gentity field. Generic props retain their existing unscaled damage.
        bool usesWeaponHitLocationMultipliers{};

        bool operator==(const SvDamageableEntityView &) const = default;
    };

    struct SvEntityDamageState
    {
        // CODDIFF(g_damage): source owner for explicitly registered generic or
        // destructible targets. CODOL server gentity fields and handler table
        // are absent, so this is semantic state rather than a native layout.
        SvEntityDamageKind kind{};
        std::int32_t health{};
        bool canTakeDamage{};
        bool cannotDie{};
        std::uint32_t stageIndex{};

        bool operator==(const SvEntityDamageState &) const = default;
    };

    struct SvEntityDamageRuntimeStatus
    {
        std::uint32_t entityNum{};
        std::uint32_t generation{};
        SvEntityDamageState state;
        std::uint16_t modelIndex{};

        bool operator==(const SvEntityDamageRuntimeStatus &) const = default;
    };

    struct SvEntityDamagePayload
    {
        // OLMOD(entity-damage-transaction): typed immutable input staged by a
        // recovered producer and consumed only after generation validation.
        std::uint32_t targetEntityNum{};
        std::uint32_t targetGeneration{};
        std::optional<std::uint32_t> inflictorEntityNum;
        std::optional<std::uint32_t> attackerEntityNum;
        std::int32_t damage{};
        std::uint32_t damageFlags{};
        std::uint8_t methodOfDeath{};
        std::uint16_t weaponAssetIndex{};
        std::optional<std::array<float, 3>> point;
        std::optional<std::array<float, 3>> direction;
        std::uint8_t hitLocation{};
        std::int32_t timeOffset{};
        std::uint16_t boneIndex{};

        bool operator==(const SvEntityDamagePayload &) const = default;
    };

    enum class SvEntityDamagePresentationEventKind : std::uint8_t
    {
        SoundAlias,
        SoundAliasAsMaster,
        WorldFx,
    };

    struct SvEntityDamagePresentationEvent
    {
        SvEntityDamagePresentationEventKind kind{};
        std::uint32_t eventParameter{};

        bool operator==(const SvEntityDamagePresentationEvent &) const = default;
    };

    struct SvEntityDamageMutation
    {
        // OLMOD(entity-damage-handler-result): pure candidate returned by the
        // source handler; the world transaction validates and commits it.
        SvEntityDamageState state;
        std::optional<std::uint16_t> modelIndex;
        // Pure presentation plan. The transaction owner supplies the target's
        // authoritative origin and publishes these only after the full
        // usercmd candidate succeeds.
        std::vector<SvEntityDamagePresentationEvent> presentationEvents;

        bool operator==(const SvEntityDamageMutation &) const = default;
    };

    using SvEntityDamageHandler = std::function<
        std::optional<SvEntityDamageMutation>(
            const SvEntityDamagePayload &payload,
            const SvEntityDamageState &state,
            std::uint16_t modelIndex)>;

    struct SvPlayerDamagePayload
    {
        // CODDIFF(g_damage): typed source/script boundary corresponding to the
        // validated argument set of G_DamageClient/Scr_PlayerDamage.
        std::uint32_t targetClientNum{};
        std::optional<std::uint32_t> inflictorEntityNum;
        std::optional<std::uint32_t> attackerEntityNum;
        std::int32_t damage{};
        std::uint32_t damageFlags{};
        std::uint8_t methodOfDeath{};
        std::uint16_t weaponAssetIndex{};
        std::optional<std::array<float, 3>> point;
        std::optional<std::array<float, 3>> direction;
        std::uint8_t hitLocation{};
        std::int32_t timeOffset{};
        std::uint16_t boneIndex{};

        bool operator==(const SvPlayerDamagePayload &) const = default;
    };

    struct SvPlayerDamagePayloadLimits
    {
        std::uint32_t maximumClients{};
        std::uint32_t maximumEntities{};
        std::uint32_t methodOfDeathCount{};
        std::uint32_t hitLocationCount{};

        bool operator==(const SvPlayerDamagePayloadLimits &) const = default;
    };

    struct SvPlayerDamageBuildInput
    {
        std::uint32_t targetClientNum{};
        std::uint32_t inflictorEntityNum{};
        std::uint32_t attackerEntityNum{};
        std::int32_t baseDamage{};
        float hitLocationMultiplier{};
        std::uint32_t damageFlags{};
        std::uint8_t methodOfDeath{};
        std::uint16_t weaponAssetIndex{};
        std::array<float, 3> point{};
        std::array<float, 3> direction{};
        std::uint8_t hitLocation{};
        std::int32_t timeOffset{};
        std::uint16_t boneIndex{};

        bool operator==(const SvPlayerDamageBuildInput &) const = default;
    };

    // CODDIFF(g_damage): validates the C++ -> gameplay-script boundary only.
    // The native
    // Bullet_Trace/Bullet_Process and G_DamageClient state checks remain the
    // authoritative producers and must succeed before this payload is queued.
    [[nodiscard]] bool SV_IsPlayerDamagePayloadValid(
        const SvPlayerDamagePayload &payload,
        const SvPlayerDamagePayloadLimits &limits);
    [[nodiscard]] std::optional<SvPlayerDamagePayload>
    SV_BuildPlayerDamagePayload(const SvPlayerDamageBuildInput &input);
    // OLMOD(entity-damage-owner-registration): despite the historical name,
    // this admits a live initial owner. A committed terminal runtime state may
    // have health <= 0 and is intentionally excluded from future capabilities.
    [[nodiscard]] bool SV_IsEntityDamageStateValid(
        const SvEntityDamageState &state);
    [[nodiscard]] bool SV_IsEntityDamagePayloadValid(
        const SvEntityDamagePayload &payload,
        std::uint32_t maximumEntities,
        std::uint32_t methodOfDeathCount,
        std::uint32_t hitLocationCount);
}
