#pragma once

#include "sv_bullet_mp.hpp"
#include "sv_damage_mp.hpp"
#include "sv_gamestate_mp.hpp"
#include "sv_weapon_fire_mp.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace CodolGameServer
{
    // MELEE IS SERVER-AUTHORITATIVE, AND THAT IS MEASURED RATHER THAN ASSUMED.
    //
    // out.exe's event table carries sixteen melee ids. Mining the 84-demo
    // corpus with Tools/demo-re/melee-events.py (1514 melee events across 35
    // demos) says two things that decide this whole module:
    //
    //   EV_MELEE_HIT  0x4B      0 occurrences
    //   EV_MELEE_MISS 0x4C      0 occurrences
    //
    // A real server never raises either, so the client does not report whether
    // a swing connected. And codol_codecs.EVENT_WIDTH bounds every melee id at
    // TWO bits of parameter -- entity numbers on this build run to 2046 and
    // need eleven -- so no melee event could name a victim even if one fired.
    // Every one of the 1514 carried parameter 0.
    //
    // Therefore the server traces. That is also what BO1 does:
    // Weapon_Melee_internal (CoDMP.map g_weapon.obj, 0x82489C40) calls
    // Melee_Trace and then G_Damage with rand()%5 + weapDef->meleeDamage, and
    // FireWeaponMelee 0x8248A3D0 sources its range/width/height from the
    // player_meleeRange / player_meleeWidth / player_meleeHeight dvars.
    //
    // CODDIFF(weapon_melee): the range dvars remain unrecovered on this build.
    // The damage is recovered: OLfinal 0x4BC1D0 reads WeaponDef +0x818 and
    // passes it to the melee trace helper. Its alpha counterpart 0x4D1830
    // reads +0x5F8, which lets alpha weapon clones preserve their own value.
    //
    // SvMethodOfDeathMelee moved to sv_damage_mp.hpp, beside the other
    // nineteen methods, when the obituary needed the same set (section 191q).
    // It is still 8 and it is still read off out.exe 0x00DBA318.

    // CHOSEN, not measured. 64 units is the melee reach every IW/Treyarch title
    // in this lineage ships as player_meleeRange, and it is the distance at
    // which the swing animation visibly connects.
    inline constexpr float SvMeleeRange = 64.0f;

    // OLMOD(melee-attack-input): source view assembled by the client-event
    // dispatcher. Not a native CODOL structure.
    struct SvMeleeAttackInput
    {
        SvWeaponFireBasis basis;
        std::uint16_t weaponAssetIndex{};
        std::uint16_t meleeDamage{};
        std::uint32_t firingEntityNum{};
        // Both exist only for the glass branch. glassPieceCount is the bound
        // SV_BulletTrace validates a glass hitId against; leaving it 0 does not
        // merely skip glass, it makes SV_BulletTrace REJECT every glass hit --
        // see the note on the glass branch in SV_ExecuteMeleeAttack.
        std::int32_t levelTime{};
        std::uint32_t glassPieceCount{};

        bool operator==(const SvMeleeAttackInput &) const = default;
    };

    enum class SvMeleeAttackResult : std::uint8_t
    {
        // The swing connected with a damageable player and a payload is staged.
        Applied,
        // The swing broke or weakened a glass pane. Distinct from Applied
        // because no player damage payload is staged, and distinct from Missed
        // because the world did change and the caller must commit it.
        Glass,
        // The swing was valid and simply did not connect. This is the common
        // case and it is NOT a failure: melee misses constantly.
        Missed,
        Failed,
    };

    // OLMOD(melee-command-transaction): mirrors SV_ExecuteBulletFire. All
    // output is candidate-owned; the caller commits only if the complete
    // usercmd succeeds. A miss leaves every output untouched.
    [[nodiscard]] SvMeleeAttackResult SV_ExecuteMeleeAttack(
        const SvMeleeAttackInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassMapMetadata &glassMetadata,
        const SvGlassDirectionEncoder &directionEncoder,
        std::span<const SvDamageablePlayerView> damageablePlayers,
        std::span<const SvDamageableEntityView> damageableEntities,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        std::vector<SvEntityDamagePayload> &entityDamagePayloads,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState);

    // Compatibility entry for callers that intentionally expose only players.
    [[nodiscard]] SvMeleeAttackResult SV_ExecuteMeleeAttack(
        const SvMeleeAttackInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassMapMetadata &glassMetadata,
        const SvGlassDirectionEncoder &directionEncoder,
        std::span<const SvDamageablePlayerView> damageablePlayers,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState);

    // Exposed for tests: where the swing trace ends, given a basis.
    [[nodiscard]] std::array<float, 3> SV_MeleeTraceEnd(
        const SvWeaponFireBasis &basis, float range);
}
