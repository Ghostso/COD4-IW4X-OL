#pragma once

#include "sv_snapshot_mp.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    // BATTLECHATTER - the player's own voice. "Reloading!", "Grenade out!", the
    // kill confirmation. IW4's maps/mp/gametypes/_battlechatter_mp.gsc is the
    // reference and every number below is read off it or off CODOL's own data.
    //
    // THE VOCABULARY IS CODOL'S AND IT IS SMALL: eleven `<voice>_f1_inform_*`
    // lines per faction voice, in the same CCS band as the announcer (191n), so
    // they need NO configstring and NO precache - the client already holds them.
    //
    //   uk_ 1674..1684        ab_ 947..957
    //
    // Eight of IW4's nine bcSounds exist here. `inform_casualty_generic` does
    // NOT, so the "casualty" trigger has nothing to say and is absent below
    // rather than substituted with a line that means something else.
    // THE VOICE HAS A GENDER AND A FACTION, AND `f1` WAS NEVER A FIXED PREFIX.
    //
    // The first version of this file shipped `uk_f1_*` for everybody, and a
    // player on a MALE character was answered by a woman. `f1` is not part of
    // the prefix: it is FEMALE VOICE 1. There are four per faction, and the
    // shipped file tree names them outright:
    //
    //   codo_mp/tf/{f1,f2,m1,m2}/uk_1_inform_*     alias  uk_<gender><n>_inform_*
    //   codo_mp/sc/{f1,f2,m1,m2}/ab_1_inform_*     alias  ab_<gender><n>_inform_*
    //   codo_mp/ancr/tf141  uk_    codo_mp/ancr/scar  ab_    codo_mp/ancr/rbt  rb_
    //
    // So `tf` is the uk_ voice and `sc` is the ab_ voice, which is exactly this
    // server's own SvCharacterFaction::Tf / ::Sc - the mapping needed no
    // invention at all. Gender comes from SvCharacterCustomization::female,
    // which the server has held all along and this feature simply never read.
    //
    // INDEX 1 OF THE TWO, because IW4 builds its own prefix as
    // `getTeamVoicePrefix( team ) + "1_"` and always takes voice 1. Picking
    // between 1 and 2 per player would be inventing a rule retail does not have.
    enum class SvBattleChatterLine : std::uint8_t
    {
        AttackFlashbang = 0,
        AttackGrenade,
        AttackSmoke,
        AttackStiel,
        AttackStun,
        AttackThwC4,
        KillfirmGeneric,
        KillfirmInfantry,
        PlantClaymore,
        ReloadingGeneric,
        SuppressedGeneric,
        Count,
    };

    // The eleven lines of one voice are contiguous and alphabetical, and the
    // four voices of one faction are 52 apart. Both are asserted below against
    // parameters read directly out of the ncs table, so a wrong assumption
    // fails the build instead of playing the wrong line.
    constexpr std::uint16_t SvBattleChatterVoiceStride = 52;
    constexpr std::uint16_t SvBattleChatterTfFemaleBase = 1674;
    constexpr std::uint16_t SvBattleChatterScFemaleBase = 947;

    [[nodiscard]] constexpr std::uint16_t SvBattleChatterParameter(
        const SvCharacterFaction faction,
        const bool female,
        const SvBattleChatterLine line)
    {
        const std::uint16_t base = faction == SvCharacterFaction::Tf
            ? SvBattleChatterTfFemaleBase
            : SvBattleChatterScFemaleBase;
        // f1, f2, m1, m2 -- so male is two strides past female.
        const std::uint16_t gender = female ? 0u : 2u * SvBattleChatterVoiceStride;
        return static_cast<std::uint16_t>(
            base + gender + static_cast<std::uint16_t>(line));
    }

    // MEASURED, straight out of localized_common_mp's ncs_snd table. Every one
    // of these was printed by name-announcers.py before the arithmetic above
    // was written, so these assertions check the FORMULA rather than restating
    // it.
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Tf, true, SvBattleChatterLine::ReloadingGeneric)
        == 1683, "uk_f1_inform_reloading_generic");
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Tf, false, SvBattleChatterLine::ReloadingGeneric)
        == 1787, "uk_m1_inform_reloading_generic");
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Sc, true, SvBattleChatterLine::ReloadingGeneric)
        == 956, "ab_f1_inform_reloading_generic");
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Sc, false, SvBattleChatterLine::ReloadingGeneric)
        == 1060, "ab_m1_inform_reloading_generic");
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Tf, true, SvBattleChatterLine::KillfirmInfantry)
        == 1681, "uk_f1_inform_killfirm_infantry");
    static_assert(
        SvBattleChatterParameter(
            SvCharacterFaction::Tf, true, SvBattleChatterLine::AttackFlashbang)
        == 1674, "uk_f1_inform_attack_flashbang");

    // EV_RELOAD_START_NOTIFY, and this is the id the LIVE RING actually
    // carries -- it was already measured and already written down in this tree
    // before battlechatter existed.
    //
    // sv_client_events_mp.cpp names EventReloadStartNotify = 0x1D beside
    // EventReloadAddAmmo = 0x1E, with: "Every one of the four is corroborated
    // by the live ring from the two-magazine run: 0x1E and 0x1D appear around a
    // reload". THAT IS A MEASUREMENT OF THIS BUILD, from a person emptying two
    // magazines on 2026-08-21.
    //
    // The first version of this file used 27 (EV_RELOAD_START) off the name
    // table instead, and the reload line never fired once in a played match
    // while the kill line worked -- the name table says what an id MEANS, not
    // which ids this build's Pmove emits. 29 is also the semantically right
    // one: IW4's trigger is `waittill( "reload_start" )`, and a GSC notify is
    // driven by the NOTIFY event, not the state change.
    constexpr std::int32_t SvEventReloadStartNotify = 0x1D;

    // READ OFF THE GAME'S OWN ALIAS RECORD, not chosen. The sound asset for
    // `uk_f1_inform_reloading_generic` is 988 bytes - nine alternate takes of
    // 108 bytes - and every one carries mindist 7.0, maxdist 1400.0. The
    // announcer's `uk_1mc_timesup` carries 360/600 by comparison, which is why
    // one is a world sound and the other is nearly UI.
    constexpr float SvBattleChatterAudibleRadius = 1400.0f;
    // CODREF: _battlechatter_mp.gsc isSpeakerInRange -- `distSq = 1000 * 1000`.
    // If a teammate is already speaking within this, the line is DROPPED, not
    // queued. Chatter is ambience; two people shouting over each other is worse
    // than silence.
    constexpr float SvBattleChatterSuppressionRadius = 1000.0f;
    // CODREF: _battlechatter_mp.gsc timeHack -- `wait ( 2.0 )`, commented there
    // as a workaround for a soundalias notify that never arrives. A speaker
    // holds the floor for two seconds whatever the clip's real length is.
    constexpr std::uint32_t SvBattleChatterSpeakerHoldMs = 2000;

    // WHO HEARS IT. A DELIBERATE DIVERGENCE FROM RETAIL, CHOSEN BY THE PLAYER.
    //
    // IW4 delivers with `playSoundToTeam( alias, team, self )`: the speaker's
    // TEAM, excluding the speaker. In free-for-all nobody has a team, so it
    // reaches nobody - which is why the retail dm demo carries zero
    // battlechatter. It is not missing from the demo, it is structurally silent
    // in that mode, and probably deliberately so: an enemy calling "reloading"
    // is a position give-away.
    //
    // IT SHIPPED ON Everyone TO BE TESTED, AND THE PLAYER KEPT IT -- then went
    // further and kept hearing their OWN callouts too, having heard it in a
    // played match: "it works the way you say it. Let's keep self audition,
    // it's pretty cool. Can come back at a later time later in dev to change
    // it." So the default below is EveryoneIncludingSpeaker, and it is a
    // PRODUCT DECISION with a name on it rather than a bug or a leftover
    // debugging switch. Revisit when that call is revisited, not before.
    //
    // The faithful path stays one predicate away - `OLMOD_BATTLECHATTER_TEAM=1`
    // - and nothing else about the feature changes with it. That is the whole
    // reason delivery is a per-client `p` rather than a world sound entity: an
    // entity would be positional but reaches EVERY client, because
    // shouldArchiveWorldEntity has no per-client visibility stage
    // (sv_snapshot_mp.cpp, and its own TODO says the dedicated one was never
    // recovered). Team-only would then be an unbuilt subsystem rather than a
    // predicate, and "assume teams works" would be assuming untested code.
    //
    // THE COST, STATED: `p` is a LOCAL sound, so this has no direction and no
    // falloff - it is full volume or nothing. The radius above is applied
    // server-side to stand in for the attenuation the client would have done.
    enum class SvBattleChatterAudience : std::uint8_t
    {
        Everyone,
        Team,
        // THE DEFAULT, and not what IW4 does: it excludes the speaker in every
        // mode. This began as a testing aid -- with one human driving two
        // clients, every line lands on the window nobody is watching, and the
        // feature could not be confirmed to make a sound at all -- and the
        // player then chose to keep it after hearing it in a played match.
        // `OLMOD_BATTLECHATTER_EXCLUDE_SELF=1` restores retail's behaviour.
        EveryoneIncludingSpeaker,
    };

    struct SvBattleChatterListener
    {
        std::uint32_t clientNum{};
        std::array<float, 3> origin{};
        SvTeam team{ SvTeam::None };
        bool alive{};
    };

    struct SvBattleChatterSpeaker
    {
        std::uint32_t clientNum{};
        std::array<float, 3> origin{};
        std::uint32_t untilServerTime{};
    };

    // THE GENDER COMES OFF THE BODY MODEL NAME, because the character
    // definition's own flag does not work.
    //
    // MEASURED IN A LIVE MATCH: two players, one on `fpa_raider_sc_m` and one
    // on `fpa_pingoles_sc_f`, and BOTH resolved to the male voice --
    // SvCharacterCustomization::female was false for the female character.
    // `presentation.female = characterDefinition[2] != 0` is evidently reading
    // something that is not the gender, and correcting THAT is out of scope
    // here: `female` is written into clientInfo and the client may pick a body
    // from it, so changing it risks the rendering path to fix a sound.
    //
    // The model name carries it unambiguously. Checked against every `fpa_`
    // body model in the shipped zones -- 456 of them -- by taking the LAST
    // bare `m` or `f` component: 279 male, 173 female, 4 unresolved, and the
    // four are `fpa_tightjeans_*`, trousers mis-slotted as a body. The naming
    // is `<slot>_<name>_<faction>_<gender>[_variant...]`, and the variant
    // suffixes (`_ter`, `_basic`, `_red`, `_a`, `_00_hrt`) are why this looks
    // for the token anywhere rather than at the end.
    //
    // Empty means "the name did not say", NOT "male" - the caller decides.
    [[nodiscard]] std::optional<bool> SV_BattleChatterFemaleFromModelName(
        std::string_view bodyModelName);

    [[nodiscard]] float SV_BattleChatterDistanceSquared(
        const std::array<float, 3> &left, const std::array<float, 3> &right);

    // Is this line dropped because somebody nearby is already talking?
    // CODREF: isSpeakerInRange -- the speaker's own entry counts, which is what
    // stops one player chattering twice inside the hold.
    [[nodiscard]] bool SV_BattleChatterSuppressed(
        std::uint32_t clientNum,
        const std::array<float, 3> &origin,
        std::span<const SvBattleChatterSpeaker> speakers,
        std::uint32_t currentServerTime);

    // Who receives the line. Empty means nobody, and nobody is a legitimate
    // answer - out of range, or a team of one.
    [[nodiscard]] std::vector<std::uint32_t> SV_BattleChatterAudience(
        std::uint32_t speakerClientNum,
        const std::array<float, 3> &speakerOrigin,
        SvTeam speakerTeam,
        std::span<const SvBattleChatterListener> listeners,
        SvBattleChatterAudience audience);
}
