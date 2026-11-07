#pragma once

#include "qcommon/msg_mp.hpp"

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    // CODREF(sv_send_client_gamestate): CODOL CL_ParseGameStateMessage
    // 0x0046DEA0 proves these command/configstring domains. Reference-server
    // command ids differ and are not reused here.
    //
    // CODDIFF(1649370): every INDEX below was re-derived for out.exe against
    // 3.3.3.3 and the table does NOT move by one delta - see
    // re/olfinal/configstrings-1649370.json for the per-entry evidence. The
    // fixed low region (0, 5, 6, 8, 9, 13, 15, 16 and the ncs dvar pair range
    // 24..663) did not move at all, the player-name block moved +477, the main
    // body moved +517, the weapon block moved +517 AND grew from 900 to 1700
    // entries, and everything above it moved +5446. The whole map was read out
    // of one function pair, CG_ConfigStringModified A 0x57A300 <-> C 0x60FD80,
    // plus the deferred-asset loader A 0x57A080 <-> C 0x60F650 whose explicit
    // for-loop bounds pin the ranges the dispatcher only tests.
    constexpr std::uint8_t ServerCommandSnapshot = 0;
    constexpr std::uint8_t ServerCommandGameState = 3;
    constexpr std::uint8_t ServerCommandConfigString = 4;
    constexpr std::uint16_t ServerInfoConfigStringIndex = 0;
    constexpr std::uint16_t SystemInfoConfigStringIndex = 1;
    constexpr std::uint16_t GameNameConfigStringIndex = 2;
    // CODREF(sv_send_client_gamestate): configstring 15 is the match END time in
    // server-time milliseconds, and it is what drives the HUD countdown.
    //
    // CG_ConfigStringModified sub_C1A300 case 0xF routes to sub_C19830, which is
    // just `atoi(configstring 15)` stored at cg+0xEC. The consumer sub_C121C0
    // then computes
    //     seconds = (cg[0xEC] - *(DWORD *)(cgs[0x357C] + 13612)) / 1000
    // where +13612 is the current server time - i.e. REMAINING SECONDS. So the
    // value is an absolute end time, not a duration and not a start time.
    //
    // The retail olevents capture carries `15  15000` immediately before
    // `16  -33.000000 106.000000 4.000000`, the map center this file already
    // owns, which is how the index was anchored.
    //
    // ui_timelimit (463/464 here) only feeds the menu text; it does NOT drive the
    // clock. Without configstring 15 the HUD has no end time and no countdown.
    constexpr std::uint16_t MatchEndTimeConfigStringIndex = 15;
    constexpr std::uint16_t MapCenterConfigStringIndex = 16;
    // CODOL CL_ApplyConfigStringDvars pairs names at 24..343 with values at
    // 344..663. These build-stable slots are the native post-systeminfo
    // owners for the three mode HUD dvars.
    constexpr std::uint16_t UiScoreLimitConfigStringIndex = 463;
    constexpr std::uint16_t UiTimeLimitConfigStringIndex = 464;
    constexpr std::uint16_t UiHalfTimeConfigStringIndex = 465;
    // MEASURED, NOT NAMED. `d 479 1` is sent once in the retail dm match, on
    // the frame it is decided, and 479 is never written again. In the same
    // name/value pairing as the three above it -- names at 24..343, values at
    // 344..663 -- so its dvar name lives at configstring 159, which this demo's
    // gamestate does not carry. The INDEX and the VALUE and the MOMENT are all
    // measured; what it is called is not, and 120 is the record of what naming
    // a field you have not identified costs.
    constexpr std::uint16_t MatchEndUiConfigStringIndex = 479;
    // The map's marker/objective string. Retail CLEARS it at the podium -- `d
    // 792` with no value, on the +17000 frame -- after using it during the
    // match to attach an icon to an entity
    // (`\ent\381\offs\0 0 0\mat\-1\offmat\-1\flags\8`).
    constexpr std::uint16_t ObjectiveMarkerConfigStringIndex = 792;
    // THE HINT STRING BAND -- the "hold F to open" prompt's text.
    //
    // The client resolves playerState.cursorHintString by adding this base and
    // nothing else: `mov esi,[edi+0xC71E4]; add esi,0x358; call CL_GetConfigString`
    // in sub_45A720. The same 856/96 pair appears independently in the weapon-def
    // loader sub_4E8490, which registers a weapon's own hint string through the
    // generic allocator sub_4EC5D0 with base=0x358 and max=0x60.
    //
    // Cross-checked a third way: the band descriptor table at out.exe 0xDA9808 --
    // 12-byte {start, count, flag} entries -- carries {856, 96} at entry 14, and
    // every other band this header already declares (models 2568/1024, sounds
    // 3624/512, effects 4136/400, materials 4872/1024, script menus 4808/64,
    // weapons 5960/1700, dvar names 24/320, dvar values 344/320) appears in that
    // same table with the numbers derived here one at a time. See
    // re/demo-re/18-hint-strings.md.
    //
    // The retail zm demos use 863..884 of it, so the first seven slots belong to
    // something the server does not own yet; allocation therefore starts at the
    // low end and simply takes free slots, exactly as sub_4EC5D0 does.
    constexpr std::uint16_t HintStringConfigStringBase = 856;
    constexpr std::uint16_t HintStringConfigStringCount = 96;
    // WHERE THE SERVER'S OWN HINT STRINGS START, and it is not zero.
    //
    // All five retail zm captures put their first server-written hint string at
    // configstring 863 -- relative index 7 -- and none of them ever writes below it,
    // while the 7-31 capture publishes relative indices 3, 4, 5 and 6 on its doors and
    // debris. So slots 0..6 are populated by something that is not a server
    // configstring write, and the same is true of the low part of every other band
    // (the model band appears in that capture only from 2979). Whatever fills them,
    // retail's server does not take them, and neither will this one: allocating from 7
    // costs nothing and imitates the only behaviour that has been observed.
    //
    // See re/demo-re/19-entity-numbering-and-triggers.md section 5.
    constexpr std::uint16_t HintStringFirstServerSlot = 7;
    // The value a playerState carries when there is no hint string. NOT zero:
    // the client's own fade-out path writes 0xFFFFFFFF into its cache
    // (sub_45BA10 @0x45BACC), and the clean retail zm capture idles there.
    // Zero is the index of configstring 856, which is a real slot.
    constexpr std::int32_t NoHintStringIndex = -1;
    // The fog. Eleven tokens, the first of which is a START TIME: the retail
    // gamestate carries `791 0.000113538 166 173 150 1 0 0 0.5 70 90` and the
    // podium frame re-sends the same ten values with the first zeroed.
    constexpr std::uint16_t FogConfigStringIndex = 13;
    // CODOL's snapshot consumer decodes base + clientNum into the encrypted
    // clientInfo display-name field. base + 40 owns the separate clan string
    // and must not be used as a player-name fallback.
    //
    // CODDIFF(1649370): 1975 -> 2452, and this is the ONE entry that moves by
    // +477 instead of the +517 the rest of the body uses. CL_GetClientName
    // A 0x4FAEA0 <-> C 0x516A20 is a confirmed pair (identical
    // MultiByteToWideChar 0xFDE9 / WideCharToMultiByte 0x3A8 / strncpy 0x45
    // body); A does `add ecx, 0x7B7` before CL_GetConfigString where C does
    // `lea esi, [edi+0x994]`. Three more C sites use the same
    // `add reg, 0x994; call 0x514880` idiom.
    //
    // A BYTE SCAN FOR 1975 IN out.exe FINDS THREE HITS AND THEY ARE ALL LIES:
    // every one decodes as the rel32 operand of a `je`, and one of them sits
    // inside the STRONG cross-build counterpart of an A function that really
    // does use 1975. Decode the instruction before believing the value.
    constexpr std::uint16_t PlayerNameConfigStringBase = 2452;
    constexpr std::uint16_t PlayerNameConfigStringCount = 18;
    // The timescale ramp: "%i %i %g %g" = start time, duration, from, to.
    // CODOL CG_ConfigStringModified routes it to A 0x579F30 / C 0x60F4A0,
    // which feeds the value straight into the frame-time scale.
    // CODDIFF(1649370): 6415 -> 11861, +5446. It is the first index above the
    // 32-entry block the deferred-asset loader walks on both builds
    // (A 6383..6414 at 0x57A206, C 11829..11860 at 0x60FC09).
    constexpr std::uint16_t TimescaleConfigStringIndex = 11861;
    constexpr std::uint16_t NorthYawConfigStringIndex = 2554;
    // CODREF: CG_ConfigStringModified 0x0060FD80 handles 2557..2562 as the SIX
    // vision sets. 2557, 2560, 2561 and 2562 each strncpy the name into the same
    // 0x40-byte buffer the server-command dispatcher writes -- base+0x192578 +
    // 0x40 * type -- and then call the applier 0x0046CEF0 with the type and the
    // blend time; 2558 and 2559 reach it through 0x0060F010, which computes that
    // displacement as (type << 6) + 0x192578 and can substitute a per-mode
    // override before it. The value is `"<name>" <blendMs>` -- the same two
    // tokens the 'N' command carries (HANDOFF section 99).
    //
    // MEASURED (re/demo-re/olevents/configstrings.tsv, the LIVE retail server):
    //   2557 "zm_prototype_sh" 1000    2560 "thermal_mp" 1000
    //   2558 "default_night_mp" 1000   2561 "zm_prototype_sh" 1000
    //   2559 "thermal_mp" 1000         2562 "zm_prototype_sh" 1000
    // so the naked, pain and type 5 slots all carry the MAP's own grade and only
    // night/missilecam/thermal name a shared set.
    constexpr std::uint16_t VisionNakedConfigStringIndex = 2557;
    constexpr std::uint16_t VisionNightConfigStringIndex = 2558;
    constexpr std::uint16_t VisionMissilecamConfigStringIndex = 2559;
    constexpr std::uint16_t VisionThermalConfigStringIndex = 2560;
    constexpr std::uint16_t VisionPainConfigStringIndex = 2561;
    constexpr std::uint16_t VisionOverlayConfigStringIndex = 2562;
    constexpr std::uint16_t MiniMapConfigStringIndex = 2555;
    constexpr std::string_view GameNameConfigString = "cod";
    constexpr std::uint16_t ModelConfigStringBase = 2568;
    constexpr std::uint16_t ModelConfigStringCount = 1024;
    // Category18 table at DA9808+18*12: base7669,count4096,reserved1.
    // 514880 subtracts base+reserved to reach the zero-based NCS alias.
    // 74A420 -> 661B80 -> 7858B0 inserts that alias into the animation tree;
    // 540040 -> 785870 resolves the packet alias, NOT the flat relative index.
    // Thus flat relative476 names l_1, but its packet alias is475.
    constexpr std::uint16_t AnimConfigStringBase = 7669;
    constexpr std::uint16_t AnimConfigStringCount = 4096;
    constexpr std::optional<std::uint16_t> SV_AnimationAliasFromConfigString(
        const std::uint32_t configString)
    {
        if (configString <= AnimConfigStringBase ||
            configString >= std::uint32_t{AnimConfigStringBase} + AnimConfigStringCount)
            return std::nullopt;
        return static_cast<std::uint16_t>(configString - AnimConfigStringBase - 1u);
    }
    constexpr std::uint16_t EffectConfigStringBase = 4136;
    constexpr std::uint16_t EffectConfigStringCount = 400;
    // THE KILL FEED'S TEXT. Retail's dm gamestate carries a 173-entry band of
    // LOCALIZED STRING NAMES at 1413..1585 and this server sends none of it;
    // the first three are the obituary's own formats.
    //
    // THIS IS A TEST OF A HYPOTHESIS, NOT A KNOWN FIX. The carrier that tells
    // the client a kill happened has NOT been identified: `@` fires on 28 of
    // this match's 29 kills but is a binary svc2 record on the profile/stats
    // channel, and the client's command dispatcher (sub_613A40) leaves 0x40 in
    // its DEFAULT case, so `@` is the XP record and not the feed. If the client
    // draws the obituary itself from the death it already receives, then the
    // only thing missing is this text and the feed appears. If nothing appears,
    // the hypothesis is dead and the carrier is one of the verbs the dispatcher
    // does handle -- `y` is the first suspect, 25 sends in the demo and none
    // from us.
    constexpr std::uint16_t ObituaryConfigStringBase = 1413;
    constexpr std::uint16_t SoundAliasConfigStringBase = 3624;
    // THE SERVER OWNS THE SOUND ALIAS TABLE, and this server never wrote a
    // single entry of it - which is why every UI sound has been silent.
    //
    // MEASURED. `p <n>` plays alias index n, and alias n is configstring
    // 3624+n. In the retail dm demo the gamestate ships 79 alias entries
    // spanning indices 9..3628 and the match hands out 45 MORE live, as each
    // sound is first needed:
    //
    //     index 11  cs 3635  mp_hit_alert   in retail's GAMESTATE
    //     index 15  cs 3639  mp_hit_kill    assigned live at serverTime 0
    //     index 29  cs 3653  mp_headshot    assigned live at 207600
    //
    // resolveSoundAliasEventParameters asks the CLIENT's configstrings for a
    // name, and the client only has what a server put there. Retail's client
    // could resolve `mp_hit_alert` because retail's server had written it. Ours
    // ships 22 configstrings in total, none in this range, so the lookup was
    // always going to fail - silently, because that path only logs on success.
    //
    // These are retail's own index/name pairs rather than a layout of our own,
    // and they are assigned LIVE with `d` rather than added to the gamestate,
    // which keeps SvGameStateFixtureBytes and section 101b out of it entirely.
    // THESE WERE RETAIL'S OWN INDICES (11, 15, 29) AND THAT WAS WRONG HERE.
    // The client's alias table is MAP-OWNED, not empty: loading mp_rust_long
    // fills indices 1..24 with that map's ambience -- 11 was
    // emt_insects_desert_05 and 15 was emt_metal_rattle_squeak. Retail could
    // use 11 and 15 because retail's server owned the whole table and handed
    // out every entry itself; this server inherits a table someone else filled.
    //
    // Writing over live entries WHILE THE CLIENT WAS STILL LOADING took both
    // clients down with "unable to join game session" on 2026-08-23 05:17: the
    // server logged a two-byte netchan packet and then heard nothing from
    // either client again. Bisected by disabling this alone, which restored
    // clients=2 active=2 with zero rejections.
    //
    // 100..102 WAS ALSO WRONG, in the opposite direction, and the client said
    // so: those indices are free but OUTSIDE the initialised band, so every
    // `p` played a different sound instead of a wrong one.
    //
    // CODREF: `p <n>` reaches sub_452770(n@<ax>, ...) which resolves the name
    // through sub_514880. That reads a per-configstring TYPE byte,
    // byte_77D8250[cs], and only returns the alias string when it is 21 and the
    // string is non-empty; anything else falls into sub_661C50/sub_661F00 and
    // returns something else entirely. An index the client never initialised
    // fails that test, which is exactly "a sound plays, and it is a different
    // one each time".
    //
    // MEASURED, the band retail actually uses: its gamestate ships three alias
    // entries -- 9 airconditioner_running_loop, 10 uk_spawn_music_mp_cross_fire,
    // 11 mp_hit_alert -- and the match hands out 12..54 live. Our map fills
    // 1..24 with its own ambience, so 25..27 is the first free slot inside the
    // band retail proves works, and it overwrites nothing.
    constexpr std::uint16_t SvHitAlertSoundAliasIndex = 25;
    constexpr std::uint16_t SvKillSoundAliasIndex = 26;
    constexpr std::uint16_t SvHeadshotSoundAliasIndex = 27;
    // THE MEDAL/SPLASH SOUND, and it is `mp_last_stand` despite the name.
    //
    // MEASURED by RATIO rather than by co-occurrence, because at a 300 ms window
    // every sound in a firefight looks like it co-occurs with everything. For
    // each alias, how many of its plays land beside a `w 0 ...` splash and how
    // many do not (Tools/olfinal/sound-events.py and the splash-exclusive
    // companion):
    //
    //     alias                     plays   with splash   without
    //     mp_last_stand                18            18         0   <- SPLASH ONLY
    //     mp_headshot                   4             4         0   <- headshot medal
    //     bullet_impact_headshot_2      4             4         0
    //     mp_hit_alert                 84            13        71   <- per HIT
    //     mp_hit_kill                  28            14        14   <- per KILL
    //
    // There are 20 `w 0` splashes in that match and mp_last_stand fired on 18
    // of them and NEVER without one. A sound that only ever plays beside a
    // banner is the banner's sound; the CODOL name is just a name.
    constexpr std::uint16_t SvSplashSoundAliasIndex = 28;
    constexpr std::uint16_t SoundAliasConfigStringCount = 512;
    constexpr std::uint16_t SoundAliasConstantStringBase = 0x200;
    constexpr std::uint16_t SoundAliasEventParameterLimit = 0x4000;
    static_assert(
        SoundAliasConfigStringBase + SoundAliasConfigStringCount ==
        EffectConfigStringBase);
    static_assert(SoundAliasEventParameterLimit == (1u << 14));

    // THE ANNOUNCER. `p <n>` HAS TWO BANDS AND ONLY THE LOW ONE WAS EVER
    // DECODED - which is why section 140d had to write `p 2131` down as
    // "unmeasured", and why every announcer line has been missing since the
    // first played match.
    //
    //   n <  512   configstring 3624+n, everything above: the SOUND ALIAS band,
    //              512 entries, and it is the MAP's. Handed out live as sounds
    //              are first needed, so index 15 is a different sound in every
    //              match.
    //   n >= 512   the client's OWN constant-string table, CCS type 5, which no
    //              server ever writes. n - 512 indexes the CONCATENATION of the
    //              `ncs_snd_*` blocks of the loaded zones, in load order. THE
    //              SERVER NEEDS NO CONFIGSTRING AND NO PRECACHE FOR ANY OF
    //              THEM: the client already holds the lot, which is exactly why
    //              retail's gamestate does not carry cs 4986 and the sound
    //              played anyway.
    //
    // Only three zones in an MP match contribute an ncs_snd block at all -
    // localized_common_mp (1537 entries), common_gametype_mp (99) and the
    // level's own tiny one - so the whole announcer band is FIXED PER BUILD
    // rather than per match. 392 of the first block are `uk_1mc_*`; 1MC is the
    // ship's announcing system.
    //
    // THE BASE IS SOLVED, NOT ASSERTED. Tools/olfinal/name-announcers.py tries
    // every base against ten anchors taken from two retail dm demos and reports
    // which survive; 512 is the only one, and it agrees with the
    // SoundAliasConstantStringBase above that was read off out.exe from the
    // other side. Five anchors cross the block boundary, so a wrong zone load
    // order fails rather than merely shifting:
    //
    //   p 1414 uk_1mc_free_for_all    BOTH demos, the first announcer of the
    //                                 match - and the gametype IS dm
    //   p 2131 uk_victory_music       demo 1, the exact frame the match ends,
    //                                 and that recorder came FIRST
    //   p 2128 uk_defeat_music        demo 2, its LAST command, and that
    //                                 recorder LOST
    //   p 1620 uk_1mc_winning_fight   demo 1 0:58.9, same frame as the map's
    //                                 own UK_winning_music_mp_cross_fire
    //   p 1494 uk_1mc_losing_fight    demo 2 92600, same frame as uk_losing_music
    //   p 1277 uk_1mc_achieve_uav     demo 2, twice, each exactly 3.0 s BEFORE
    //   p 1605 uk_1mc_use_uav         demo 2, twice, each exactly 3.0 s AFTER
    //
    // MEASURED, EVERY ONE, with the frame it landed on. Nothing here is a name
    // that looked plausible.
    constexpr std::uint16_t SvAnnouncerFreeForAll = 1414;
    constexpr std::uint16_t SvAnnouncerOnYourOwn = 1515;
    constexpr std::uint16_t SvAnnouncerWinningFight = 1620;
    constexpr std::uint16_t SvAnnouncerLosingFight = 1494;
    // RETAIL SENT `uk_1mc_timesup` AT EXACTLY 30.0 s REMAINING, not the
    // `uk_1mc_thirty_seconds` sitting five entries earlier at 1572. That is a
    // surprise and it is what the demo says: dm demo 1, serverTime 601700,
    // against a match end configstring of 631700, on the same frame as
    // `d 3677 ui_mp_timer_countdown`. The line the clip actually SPEAKS is
    // unmeasured - one played match settles it, and 1572 is one edit away.
    constexpr std::uint16_t SvAnnouncerTimesUp = 1577;
    constexpr std::uint16_t SvAnnouncerSpawnMusic = 2130;
    constexpr std::uint16_t SvAnnouncerLosingMusic = 2129;
    constexpr std::uint16_t SvAnnouncerVictoryMusic = 2131;
    constexpr std::uint16_t SvAnnouncerDefeatMusic = 2128;
    // THE ONE VALUE HERE NO DEMO SENDS. Both dm recorders' matches produced a
    // losing stinger and neither produced a winning one - demo 1's lead change
    // used the MAP's own UK_winning_music_mp_cross_fire out of the low band,
    // which is per-map and no use to a server that hosts any map. 2132 is
    // `uk_winning_music`, the block-2 neighbour of the three music entries that
    // ARE measured (2128/2129/2130/2131 are defeat/losing/spawn/victory, in
    // that order), so it is chosen by symmetry rather than measured. Labelled
    // because the difference matters if it ever plays the wrong thing.
    constexpr std::uint16_t SvAnnouncerWinningMusic = 2132;
    static_assert(
        SvAnnouncerFreeForAll >= SoundAliasConstantStringBase,
        "an announcer parameter below the base would address the map's alias "
        "table instead, and play whatever ambience that index happens to hold");
    constexpr std::uint16_t ServerMaterialConfigStringBase = 4872;
    constexpr std::uint16_t ServerMaterialConfigStringCount = 1024;
    constexpr std::uint16_t ScriptMenuConfigStringBase = 4808;
    constexpr std::uint16_t ScriptMenuConfigStringCount = 64;
    static_assert(
        ScriptMenuConfigStringBase + ScriptMenuConfigStringCount ==
        ServerMaterialConfigStringBase);
    // CODDIFF(1649370): the weapon block is the only one whose SIZE changed.
    // The dispatcher's first test is `index - 5443 <= 0x383` on 3.3.3.3 and
    // `index - 5960 <= 0x6A3` here, and the deferred-asset loop that follows
    // the block starts at 6343 = 5443 + 900 there and 7660 = 5960 + 1700 here.
    // 1700 does not fit in ten bits, which is why WeaponIndexBits widened.
    // SEED RETAIL'S 34 WEAPON CONFIG STRINGS AT GAMESTATE BUILD (12.127).
    //
    // THE EXPERIMENT, and it is an ANIMATION experiment despite touching weapons.
    // Measured on the same binary minutes apart (12.126):
    //
    //     retail demo : 50 zones, ~37 weapon zones, generic_human = 123 entries
    //     this server : 18 zones,   3 weapon zones, generic_human = 519 entries
    //
    // Every measured zombie defect follows from that descriptor table (12.124,
    // 12.125): the wrong table changes descriptor[2].flag and .parent, so the one
    // node the wire can seed comes out a one-shot leaf that reaches playback 1.0
    // and can never restart -- the T-pose, the freeze, the slide.
    //
    // The values are read verbatim from the retail capture's own gamestate and
    // not one of them is chosen here.
    //
    // WHAT WOULD FALSIFY IT: if generic_human still reads 519 with all 34 seeded
    // and the zone list grown, the weapon set is not what determines the table
    // and this comes straight back out.
    constexpr bool SvSeedRetailWeaponSet = false;   // REVERTED 12.127: broke the client, see below

    constexpr std::uint16_t WeaponConfigStringBase = 5960;
    constexpr std::uint16_t WeaponConfigStringCount = 1700;
    // CODDIFF(1649370): THE WEAPON INDEX BOUND LIVES HERE AND NOWHERE ELSE.
    // `> 0x3FF` -- 3.3.3.3's ten-bit bound -- was written into NINE separate places in
    // this tree, and correcting one of them left the other eight rejecting exactly the
    // weapons a real class produces: the live gamestate reports firstDynamicWeapon=1224,
    // so every modular weapon is above 1023. This project has now paid for the same
    // one-struct-many-files mistake three times (bind()'s gamestate fixture, the
    // per-weapon attachment count, this), so the bound is defined once and derived from
    // the block size it actually comes from.
    constexpr std::uint16_t MaximumWeaponAssetIndex = WeaponConfigStringCount - 1;
    static_assert(
        MaximumWeaponAssetIndex < (1u << 11),
        "a weapon index has to fit the eleven bits the gamestate writes");
    // CODDIFF(1649370): 6800 -> 12246, +5446, NOT the +608 a global vote
    // proposed. 7408 would land inside the weapon block itself. out.exe's
    // consumer sub_590A60 reads byte_77DB226, and that address minus the
    // configstring class table byte_77D8250 is exactly 0x2FD6 = 12246.
    constexpr std::uint16_t WeaponCountConfigStringIndex = 12246;
    constexpr std::array<std::string_view, 3> RequiredScriptMenus{
        "team_marinesopfor",
        "changeclass_marines",
        "changeclass_opfor",
    };

    struct SvModularWeaponConfigString
    {
        // CODDIFF(sv_send_client_gamestate): typed source representation of
        // CODOL's compact weapon-configstring bitstream, not a native struct.
        std::uint16_t baseWeaponAssetIndex{};
        std::uint8_t value8{};
        std::uint16_t optionalValue9{};
        std::vector<std::uint16_t> attachmentAssetIndexes;

        bool operator==(const SvModularWeaponConfigString &) const = default;
    };

    struct SvSdObjectiveMaterials
    {
        std::uint16_t targetA{};
        std::uint16_t targetB{};
        std::uint16_t defendA{};
        std::uint16_t defendB{};
        std::uint16_t defuseA{};
        std::uint16_t defuseB{};
        std::uint16_t bomb{};
        std::uint16_t escort{};

        bool operator==(const SvSdObjectiveMaterials &) const = default;
    };

    struct SvGameState
    {
        // OLMOD(gamestate-source-owner): validated source aggregate used to
        // build one CODOL gamestate message. It is not native server_t or the
        // client's parsed gameState_t memory layout.
        struct UiGameRules
        {
            std::uint32_t scoreLimit{};
            std::uint32_t timeLimitMinutes{};
            bool halfTime{};

            bool operator==(const UiGameRules &) const = default;
        };

        std::string mapName;
        std::string gameType;
        std::uint32_t configStringChecksum{};
        std::uint32_t checksumFeed{};
        std::array<float, 3> mapCenter{};
        std::optional<float> northYawDegrees;
        struct MiniMap
        {
            std::string material;
            std::array<float, 2> upperLeft{};
            std::array<float, 2> lowerRight{};

            bool operator==(const MiniMap &) const = default;
        };
        std::optional<MiniMap> miniMap;
        // Server time the current match started, in milliseconds. Only used to
        // derive configstring 15, the absolute match END time the HUD counts
        // down from. ZERO IS A VALID VALUE - configureGameState resets the world
        // (`snapshot_ = {}`) so the world this gamestate describes starts at
        // serverTime 0 - so it must not be used as an "unknown" sentinel.
        std::uint32_t matchStartServerTime{};
        std::optional<UiGameRules> uiGameRules;
        std::optional<SvSdObjectiveMaterials> sdObjectiveMaterials;
        // Hit-marker material, resolved for every gametype. Optional because a
        // missing icon must cost the match its damage feedback and nothing
        // else, unlike the SD objective materials whose absence fails the
        // gamestate outright.
        std::optional<std::uint16_t> damageFeedbackMaterial;
        // OLMOD(factory_ammo): names resolved at map load, not hardcoded NCS IDs.
        std::array<std::uint16_t, 2> factoryAmmoMaterials{}; // fill, background
        // OLMOD(factory-clock-materials): source metadata, no native ABI growth.
        std::optional<std::uint16_t> firstDynamicServerMaterial;
        std::array<std::uint16_t,2> factoryClockMaterials{}; // face, glass
        std::uint16_t zombieFallbackPistol{};
        std::array<std::uint16_t, 2> zombieReviveMaterials{}; // rescue, treatment
        // The killing blow's own marker. CODOL ships kill_feedback next to
        // damage_feedback in the material configstrings; whether it is the red
        // one is a property of the asset, so the server names it rather than
        // recolouring the damage marker itself.
        std::optional<std::uint16_t> killFeedbackMaterial;
        // The hit marker's other half. IW4 _damagefeedback.gsc shows the elem
        // and plays MP_hit_alert as two independent side effects, so a missing
        // alias silences the hit without hiding the marker.
        std::optional<std::uint16_t> damageFeedbackSound;
        // THE KILL SOUND, `mp_hit_kill`. NAMED, not guessed: verb `p <n>` plays
        // a sound by alias INDEX, and alias index n is configstring
        // SoundAliasConfigStringBase + n, so the retail dm demo names every
        // sound it played. Tools/olfinal/name-local-sounds.py resolves them:
        //
        //     p 11  x84  cs 3635  mp_hit_alert     <- the hit marker's, and the
        //                                             alias this server already
        //                                             asks for by name
        //     p 15  x28  cs 3639  mp_hit_kill      <- this one
        //     p 29  x4   cs 3653  mp_headshot
        //     p 13  x18  cs 3637  mp_last_stand
        //
        // 28 plays against 84 hit alerts is the right ratio for kills against
        // hits, and mp_hit_kill's name says the rest.
        std::optional<std::uint16_t> killFeedbackSound;
        // Scavenger's world pickup owns both assets by name. The weapon index
        // draws the ET_ITEM bag; the sound is queued only for the collector.
        std::optional<std::uint16_t> scavengerBagWeaponAssetIndex;
        std::optional<std::uint16_t> scavengerPickupSound;
        // OLMOD(splash-sound): the medal banner has no sound of its own on
        // this build. CG_ServerCommand's 'w' verb reaches sub_C1C860, whose
        // audio comes from COLUMN 9 of mp/splashTable.csv - it reads
        // cells[cols*row + 9] at VA 0x0057C9D8, skips an empty cell or the
        // literal "null" (0x00C65970), skips rows whose column 11 is
        // "challenge" (0x00C61214), and otherwise plays the alias through
        // VA 0x00443E40. In 3.3.3.3's shipped table only 31 of 518 rows carry
        // an inline alias and EVERY medal row - 15 HEADSHOT, 28 REVENGE,
        // 29 DOUBLEKILL, 32 FIRSTBLOOD, 33 BUZZKILL - is a backreference,
        // i.e. a repeated value, so a retail client plays nothing for them
        // either. This is the server saying it out loud instead.
        std::optional<std::uint16_t> splashSound;
        // TODO(CODOL): audition mode. Non-empty means every damage-feedback
        // alert plays the NEXT alias in this list instead of the hit sound,
        // and logs which one, so the right sound can be picked by ear.
        std::vector<std::pair<std::uint16_t, std::string>> soundAuditions;
        std::vector<std::string> playerNames;
        std::map<std::uint16_t, std::string> configStrings;
        std::map<std::uint16_t, std::uint16_t> simpleWeaponConfigStrings;
        std::map<std::uint16_t, SvModularWeaponConfigString>
            modularWeaponConfigStrings;
        std::array<std::string, ScriptMenuConfigStringCount> scriptMenus;
    };

    void SV_PopulateRequiredConfigStrings(SvGameState &gameState);
    [[nodiscard]] std::optional<std::vector<std::uint16_t>> SV_RegisterDynamicServerMaterials(
        SvGameState &gameState, std::uint16_t firstDynamic,
        std::span<const std::string> names,
        const std::map<std::uint16_t,std::string> &existing);

    // OLMOD_PERF_BASELINE=1 disables everything added on 2026-08-23 that runs
    // per frame or per trace -- the six vision configstrings, the per-client
    // vision command, the death overlay and the slow-trace reporter -- so the
    // two-player feel can be compared against the earlier behaviour without
    // reverting any of it. Read once; an environment lookup per trace would
    // itself be a cost.
    [[nodiscard]] bool SV_PerfBaseline();

    // THE GAMESTATE FIXTURE, AND THERE IS EXACTLY ONE OF IT.
    //
    // These are the bytes SV_WriteGameState produces for
    //   mapName "mp_crash", gameType "tdm", plus TimescaleConfigStringIndex
    //   "0 0 1 1", after SV_PopulateRequiredConfigStrings
    // and they are checked in TWO places that cannot see each other: the golden
    // in ServerCoreTests, and EngineBindings::bind()'s message_bindings stage,
    // which runs at launch where no unit test reaches.
    //
    // THEY USED TO BE TWO LITERAL COPIES AND THEY DRIFTED TWICE. The first time
    // was ServerCommandEof moving from 3.3.3.3's 6 to this build's 5; the second
    // was the vision configstrings, where the test and the writer were updated
    // and bind() was not -- so bind() failed at stage=message_bindings on the
    // next launch and the whole dedicated never came up. The copy that broke
    // carried a comment predicting exactly that and asking for this.
    //
    // REGENERATED 2026-09-01 for retail's ten measured serverinfo keys
    // (formatServerInfo; see re/demo-re/20-zm-actor-lifecycle.md 12.13 and 12.19).
    // 187 -> 280 bytes. cs 0 now reads
    //   \2482\24\2485\4\2490\214\2491\0\3056\2\g_gametype\tdm
    //   \g_hardcore\0\mapname\mp_crash\scr_game_allowkillcam\0\scr_team_fftype\0
    //
    // VERIFIED BY DIFF, not taken on trust from the writer that produced it: against
    // the previous fixture these bytes share a 27-byte identical PREFIX and a 129-byte
    // identical SUFFIX, and the ONLY differing region is the serverinfo value itself.
    // So every other configstring (2 "cod", 16 "0 0 0", 2557..2562, 11861 "0 0 1 1")
    // and the whole 0x05 / clientNum / feed / 0x05 tail are byte-for-byte unchanged.
    // The ASCII of every configstring was also read back out of the new bytes.
    //
    // EngineBindings::bind() re-derives this at every launch (stage=message_bindings)
    // and ServerCoreTests compares the same array -- ONE fixture, no second copy. If
    // formatServerInfo changes again, regenerate BOTH this and the hard-coded
    // serverinfo literal in ServerCoreTests' SD HUD test IN THE SAME COMMIT; that
    // literal is a second expectation and it failed first when it was missed.
    // bind() writes into a 512-byte buffer for this reason -- 256 overflowed at 280.
    inline constexpr std::array<std::uint8_t, 280> SvGameStateFixtureBytes{
        0x03, 0x00, 0x00, 0x00, 0x00, 0x6D, 0x70, 0x5F, 0x63, 0x72,
        0x61, 0x73, 0x68, 0x00, 0x74, 0x64, 0x6D, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x04, 0x0A, 0x00, 0x09, 0x5C, 0x32, 0x34, 0x38,
        0x32, 0x5C, 0x32, 0x34, 0x5C, 0x32, 0x34, 0x38, 0x35, 0x5C,
        0x34, 0x5C, 0x32, 0x34, 0x39, 0x30, 0x5C, 0x32, 0x31, 0x34,
        0x5C, 0x32, 0x34, 0x39, 0x31, 0x5C, 0x30, 0x5C, 0x33, 0x30,
        0x35, 0x36, 0x5C, 0x32, 0x5C, 0x67, 0x5F, 0x67, 0x61, 0x6D,
        0x65, 0x74, 0x79, 0x70, 0x65, 0x5C, 0x74, 0x64, 0x6D, 0x5C,
        0x67, 0x5F, 0x68, 0x61, 0x72, 0x64, 0x63, 0x6F, 0x72, 0x65,
        0x5C, 0x30, 0x5C, 0x6D, 0x61, 0x70, 0x6E, 0x61, 0x6D, 0x65,
        0x5C, 0x6D, 0x70, 0x5F, 0x63, 0x72, 0x61, 0x73, 0x68, 0x5C,
        0x73, 0x63, 0x72, 0x5F, 0x67, 0x61, 0x6D, 0x65, 0x5F, 0x61,
        0x6C, 0x6C, 0x6F, 0x77, 0x6B, 0x69, 0x6C, 0x6C, 0x63, 0x61,
        0x6D, 0x5C, 0x30, 0x5C, 0x73, 0x63, 0x72, 0x5F, 0x74, 0x65,
        0x61, 0x6D, 0x5F, 0x66, 0x66, 0x74, 0x79, 0x70, 0x65, 0x5C,
        0x30, 0x00, 0x00, 0x63, 0x6F, 0x64, 0x00, 0x20, 0x00, 0x30,
        0x20, 0x30, 0x20, 0x30, 0x00, 0xFD, 0xC9, 0x22, 0x6D, 0x70,
        0x5F, 0x63, 0x72, 0x61, 0x73, 0x68, 0x22, 0x20, 0x30, 0x00,
        0x22, 0x64, 0x65, 0x66, 0x61, 0x75, 0x6C, 0x74, 0x5F, 0x6E,
        0x69, 0x67, 0x68, 0x74, 0x5F, 0x6D, 0x70, 0x22, 0x20, 0x30,
        0x00, 0x22, 0x74, 0x68, 0x65, 0x72, 0x6D, 0x61, 0x6C, 0x5F,
        0x6D, 0x70, 0x22, 0x20, 0x30, 0x00, 0x57, 0x22, 0x74, 0x68,
        0x65, 0x72, 0x6D, 0x61, 0x6C, 0x5F, 0x6D, 0x70, 0x22, 0x20,
        0x30, 0x00, 0x22, 0x6D, 0x70, 0x5F, 0x63, 0x72, 0x61, 0x73,
        0x68, 0x22, 0x20, 0x30, 0x00, 0x22, 0x6D, 0x70, 0x5F, 0x63,
        0x72, 0x61, 0x73, 0x68, 0x22, 0x20, 0x30, 0x00, 0xE5, 0x02,
        0x30, 0x20, 0x30, 0x20, 0x31, 0x20, 0x31, 0x00, 0x00, 0x00,
        0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x05
    };
    [[nodiscard]] std::optional<std::string> SV_EncodePlayerName(
        std::string_view username);
    [[nodiscard]] std::optional<std::uint16_t>
        SV_EffectConfigStringToEventParameter(std::uint16_t configStringIndex);
    [[nodiscard]] std::optional<std::uint16_t>
        SV_EffectEventParameterToConfigString(std::uint16_t eventParameter);
    [[nodiscard]] bool SV_SetMapCenterConfigString(
        SvGameState &gameState,
        std::string_view value);
    [[nodiscard]] bool SV_SetMiniMapConfigStrings(
        SvGameState &gameState,
        float northYawDegrees,
        SvGameState::MiniMap miniMap);
    [[nodiscard]] bool SV_AddSimpleWeaponConfigString(
        SvGameState &gameState,
        std::uint16_t weaponAssetIndex,
        std::uint16_t baseWeaponAssetIndex);
    [[nodiscard]] bool SV_AddModularWeaponConfigString(
        SvGameState &gameState,
        std::uint16_t weaponAssetIndex,
        SvModularWeaponConfigString configString);
    [[nodiscard]] std::optional<SvModularWeaponConfigString>
        SV_ParseModularWeaponConfigString(std::string_view value);
    [[nodiscard]] std::optional<std::uint16_t> SV_RegisterModularWeaponConfigString(
        SvGameState &gameState,
        std::uint16_t firstDynamicWeaponAssetIndex,
        SvModularWeaponConfigString configString);
    [[nodiscard]] bool SV_ValidateGameState(const SvGameState &gameState);
    [[nodiscard]] bool SV_WriteWeaponConfigStrings(
        MsgWriter &message,
        const SvGameState &gameState);
    // The bit-packed VALUE of one modular weapon config string: base(11) value8(8)
    // [bit value9(9)] count(4) attachments(14 each). Factored out because the LIVE
    // config-string update command (below) must emit exactly the same bits the
    // gamestate does -- confirmed against out.exe's reader sub_472C70.
    void SV_WriteModularWeaponConfigStringValue(
        MsgWriter &message,
        const SvModularWeaponConfigString &configString);
    // The LIVE config-string update command out.exe applies mid-match with no
    // reset: verb '%' (37), then bit(1)=high-range, WriteBits(assetIndex, 11)
    // (index - WeaponConfigStringDynamicBase 5960), then the weapon value.
    // Confirmed chain: CL_ParseBinaryCommand -> sub_614AC0 case 0 -> sub_612640 ->
    // CL_SetConfigString. Sent as a reliable BINARY command, like the 'J'/'K'
    // scoreboard patches. See handoff §157c. `message` must be a fresh writer.
    void SV_WriteWeaponConfigStringUpdateCommand(
        MsgWriter &message,
        std::uint16_t weaponAssetIndex,
        const SvModularWeaponConfigString &configString);
    // 5960: the high updatable range base sub_612640 adds to its 11-bit index.
    // It equals WeaponConfigStringBase, which is why a weapon asset index rides
    // straight through as the 11-bit field.
    constexpr std::uint16_t WeaponConfigStringDynamicBase = 5960;
    [[nodiscard]] bool SV_WriteGameState(
        MsgWriter &message,
        const SvGameState &gameState,
        std::uint32_t clientNum,
        std::uint32_t reliableSequence);
}
