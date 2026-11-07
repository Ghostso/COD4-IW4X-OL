#pragma once

#include "sv_collision_mp.hpp"
#include "sv_damage_mp.hpp"
#include "sv_weapon_fire_mp.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <vector>

namespace CodolGameServer
{
    // CODREF(bullet_trace): CODOL's retained locational CM path and event
    // consumers confirm these title-local masks/ranges. They are values, not a
    // claim that the source types below reproduce native BulletTraceResults.
    //
    // OLMOD(section-85): ALL FOUR OF THE INTERESTING ONES ARE NOW READ OFF
    // out.exe, and the surface count came from the table rather than from the
    // literal pool that defeated section 79g.
    //
    // THE SURFACE TABLE IS A 20-BYTE RECORD whose third dword is the material
    // flags word, and for a surface type that word is `index << 20`. So the
    // table IS the enum and reading it needs no reader:
    //
    //   3.3.3.3  name field of `bark` at 0x00CD9C48
    //   out.exe  name field of `bark` at 0x00E51548
    //   both     bark=1 brick=2 carpet=3 cloth=4 concrete=5 dirt=6 flesh=7
    //            foliage=8 glass=9 grass=10 gravel=11 ice=12 metal=13 mud=14
    //            paper=15 plaster=16 rock=17 sand=18 snow=19 water=20 wood=21
    //            asphalt=22 ceramic=23 plastic=24 rubber=25 cushion=26
    //            fruit=27 paintedmetal=28 riotshield=29 slush=30, then
    //            `opaqueglass` ALIASED back to 9 and the non-surface flag
    //            names (clipmissile, playerclip, portal, ladder...) after it
    //
    // Same names, same order, same top value on both builds, so the index space
    // is 0..30 and THIRTY-ONE is this build's count too. The literal pool that
    // section 79g refused to count is a different thing in reverse-use order;
    // the flags word is what the engine actually indexes with.
    inline constexpr std::uint8_t BulletSurfaceTypeCount = 31;
    // 0x01D00000 IS riotshield's own flags word in that table (out.exe
    // 0x00E51778), and the shield branch writes it verbatim: out.exe
    // `mov ecx, 13h / cmp word [esi+22h], cx / mov [esi+10h], 1D00000h` at
    // 0x005919A1..0x005919AC, against 3.3.3.3's identical sequence at
    // 0x0055A5A8..0x0055A5B3. So the PART GROUP and the FLAGS come out of one
    // read, and 19 = 0x13 is measured here rather than inherited.
    inline constexpr std::uint32_t BulletShieldSurfaceFlags = 0x01D00000;
    inline constexpr std::uint16_t BulletShieldPartGroup = 19;
    // 0x0280E831 occurs EIGHT times in each image, and in both the single
    // occurrence of 0x01D00000 sits inside a function that also carries one of
    // them -- 3.3.3.3 sub_55A4A0, out.exe sub_5918B0. That pairing is what
    // identifies the counterpart; the equal counts are what make it a
    // measurement rather than a coincidence.
    inline constexpr std::uint32_t BulletLocationalContentMask = 0x0280E831;
    inline constexpr std::uint16_t BulletWorldEntityNum = 2046;
    inline constexpr std::uint16_t BulletNoneEntityNum = 2047;

    struct SvBulletImpactEvent
    {
        // OLMOD(bullet-impact-source-schema): validated source event later
        // encoded by the recovered CODOL ET_EVENTS writer.
        std::array<float, 3> position{};
        std::uint16_t weaponAssetIndex{};
        std::uint16_t sourceEntityNum{};
        std::uint16_t hitEntityNum{ BulletNoneEntityNum };
        std::uint8_t direction{};
        std::uint8_t surfaceType{};
        std::uint8_t impactFlags{};
        // A KNIFE, NOT A BULLET. EV_MELEE_HIT is its own event entity (eType 98
        // = 23 + 75) and the demo gives it a shape of its own: origin, the
        // attacker in field 9, the weapon in field 16 and eventParm 1 -- in all
        // 36 retail assertions -- with NO surface, NO impact flags and NO hit
        // entity. Carried as a flag rather than a second vector because these
        // live in the same staged list and are spawned by the same loop; the
        // list is heap-backed, so this adds nothing to SvGameEntity and cannot
        // move the address-keyed buffer (sect.184h).
        bool melee{};

        bool operator==(const SvBulletImpactEvent &) const = default;
    };

    struct SvBulletTraceInput
    {
        // OLMOD(bullet-trace-source-schema): source request assembled around a
        // retained native point-trace primitive, not a native CODOL structure.
        std::array<float, 3> start{};
        std::array<float, 3> end{};
        std::uint32_t firingEntityNum{};
        std::uint32_t glassPieceCount{};
        std::uint8_t lastSurfaceType{};
        bool rifleBullet{};
        // OLMOD(section-94): the trace normally PASSES the shooter, which is correct and is
        // also the reason nothing on this server has ever hit a player: with one client in the
        // map the shooter is the only candidate there is, so every bullet reports
        // hitEntity=none and the whole damage path below stays unreached. Setting this false
        // makes him a legal candidate. NOTHING IN THE GAME PATH SETS IT -- it is written by the
        // OLMOD_BULLET_SELF_DAMAGE_PROBE probe alone, on the shape section 74 used to reach
        // entity-vs-entity capsule collision without a second player.
        bool passFiringEntity{ true };
        bool worldOnly{};
        bool entitiesOnly{};

        bool operator==(const SvBulletTraceInput &) const = default;
    };

    struct SvBulletTraceResult
    {
        // CODDIFF(bullet_trace): normalized projection of CODOL TraceResult plus
        // BO1/Ghosts/BO2 Bullet_Trace responsibilities absent from the client.
        TraceResult trace;
        std::optional<std::uint32_t> hitEntityNum;
        std::optional<std::uint32_t> glassPieceIndex;
        std::array<float, 3> hitPosition{};
        bool ignoreHitEntity{};
        std::uint8_t depthSurfaceType{};

        bool operator==(const SvBulletTraceResult &) const = default;
    };

    using SvBulletLocationalTraceRunner =
        std::function<std::optional<TraceResult>(
            const SvPointTraceRequest &request)>;
    using SvBulletIgnoreHitResolver =
        std::function<std::optional<bool>(
            const SvBulletTraceInput &input,
            const TraceResult &trace,
            std::uint32_t hitEntityNum)>;
    using SvBulletEndposRunner = std::function<
        std::optional<SvBulletEndposResult>(
            const SvBulletEndposRequest &request)>;
    using SvBulletPenetrationDepthResolver = std::function<
        std::optional<float>(
            std::uint16_t weaponAssetIndex,
            std::uint8_t surfaceType)>;

    struct SvBulletFireExecutionInput
    {
        // OLMOD(bullet-command-transaction): immutable command input assembled
        // from separately audited weapon plan, basis and frozen weapon data.
        std::uint32_t commandTime{};
        SvBulletFirePlan plan;
        SvWeaponFireBasis basis;
        SvWeaponSpreadResult spread;
        SvWeaponDamageCurve damageCurve;
        std::array<float, HitLocationCount> hitLocationMultipliers{};
        std::uint16_t weaponAssetIndex{};
        std::uint32_t firingEntityNum{};
        std::int32_t levelTime{};
        bool rifleBullet{};
        // Forwarded to SvBulletTraceInput::passFiringEntity. See the note there.
        bool passFiringEntity{ true };

        bool operator==(const SvBulletFireExecutionInput &) const = default;
    };

    enum class SvBulletFireExecutionResult : std::uint8_t
    {
        Applied,
        DeferredImpact,
        Failed,
    };

    // Failed, and WHICH of the thirteen refusals it was. See the note in the
    // implementation: the stage name alone cannot separate a bad trace from a
    // rejected payload, and a player only ever sees "it does not hurt them".
    SvBulletFireExecutionResult SV_BulletFireFailed(const char *reason);
    [[nodiscard]] const char *SV_LastBulletFireFailure();

    struct SvBulletExecutionStatus
    {
        // OLMOD(bullet-execution-diagnostic): read-only checkpoint projection;
        // it is not gameplay ownership and multi-pellet fire retains the last
        // processed trace only.
        bool traced{};
        std::uint32_t commandTime{};
        std::array<float, 3> start{};
        std::array<float, 3> end{};
        TraceResult trace;
        std::optional<std::uint32_t> hitEntityNum;
        bool playerDamageStaged{};
        bool entityDamageStaged{};
        SvBulletFireExecutionResult result{ SvBulletFireExecutionResult::Failed };

        bool operator==(const SvBulletExecutionStatus &) const = default;
    };

    [[nodiscard]] bool SV_IsBulletTraceInputValid(
        const SvBulletTraceInput &input);

    [[nodiscard]] bool SV_IsBulletImpactEventValid(
        const SvBulletImpactEvent &event);

    // CODDIFF(bullet_trace): caller-owned Bullet_Trace transaction only. The
    // trace runner must supply
    // authoritative locational DObj/static-model results; this function does
    // not apply damage, create impacts, consume ammo, or advance event state.
    [[nodiscard]] std::optional<SvBulletTraceResult> SV_BulletTrace(
        const SvBulletTraceInput &input,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver);

    [[nodiscard]] bool SV_ApplyBulletGlassDamage(
        const SvBulletTraceResult &trace,
        std::uint32_t damage,
        std::int32_t levelTime,
        const std::array<float, 3> &damageDirection,
        const SvGlassMapMetadata &metadata,
        const SvGlassDirectionEncoder &directionEncoder,
        SvGlassDamageState &damageState,
        SvGlassState &glassState);

    // CODREF(bullet_process): executes ordinary bullet damage plus the first
    // recovered static-BSP penetration continuation. Glass mutation, typed
    // damage and impacts share one source command transaction; additional
    // walls, typed penetration targets and explosive bullets remain deferred.
    [[nodiscard]] SvBulletFireExecutionResult SV_ExecuteBulletFire(
        const SvBulletFireExecutionInput &input,
        const SvGlassMapMetadata &glassMetadata,
        const SvBulletEndposRunner &endposRunner,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassDirectionEncoder &directionEncoder,
        std::span<const SvDamageablePlayerView> damageablePlayers,
        std::span<const SvDamageableEntityView> damageableEntities,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        std::vector<SvEntityDamagePayload> &entityDamagePayloads,
        std::vector<SvBulletImpactEvent> &bulletImpactEvents,
        SvBulletExecutionStatus *executionStatus = nullptr,
        const SvBulletPenetrationDepthResolver &penetrationDepthResolver = {});

    // OLMOD(bullet-execution-compatibility): source-only convenience entry for
    // callers that intentionally have no registered non-player damage targets.
    [[nodiscard]] inline SvBulletFireExecutionResult SV_ExecuteBulletFire(
        const SvBulletFireExecutionInput &input,
        const SvGlassMapMetadata &glassMetadata,
        const SvBulletEndposRunner &endposRunner,
        const SvBulletLocationalTraceRunner &traceRunner,
        const SvBulletIgnoreHitResolver &ignoreHitResolver,
        const SvGlassDirectionEncoder &directionEncoder,
        std::span<const SvDamageablePlayerView> damageablePlayers,
        SvGlassDamageState &glassDamageState,
        SvGlassState &glassState,
        std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
        std::vector<SvBulletImpactEvent> &bulletImpactEvents)
    {
        std::vector<SvEntityDamagePayload> entityDamagePayloads;
        return SV_ExecuteBulletFire(
            input,
            glassMetadata,
            endposRunner,
            traceRunner,
            ignoreHitResolver,
            directionEncoder,
            damageablePlayers,
            {},
            glassDamageState,
            glassState,
            playerDamagePayloads,
            entityDamagePayloads,
            bulletImpactEvents,
            nullptr);
    }
}
