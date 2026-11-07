#pragma once

#include <cstdint>
#include <string>

namespace CodolGameServer
{
    // The splash - CODOL's medal banner. CG_ServerCommand's 'w' verb reaches
    // sub_C1C860 (CODREF: 0x0051C860), which indexes mp/splashTable.csv by ROW,
    // reads its display duration out of column 4 and its icon out of column 11,
    // and stores the result in one of five simultaneous display slots.
    //
    //   w <slot> <row> <points>
    //
    // EVERY ROW BELOW IS THIS BUILD'S. They are read out of OLfinal's own
    // shipped mp/splashTable.csv - 619 rows by 14 columns, kept at
    // re/demo-re/splashtable-olfinal/ with the parse in the .txt beside it -
    // extracted from code_post_gfx_mp.ff, which is where the asset lives (it is
    // in neither common_mp.ff nor common_gametype_mp.ff).
    //
    // THE ROWS USED TO BE 3.3.3.3's AND THAT WAS A LIVE BUG. This header
    // previously carried 3.3.3.3's numbering with a comment asserting it was
    // "THIS build's". On OLfinal row 32 is SPLASHES_MULTIKILL, so every first
    // blood in every match this project has played showed a MULTIKILL banner.
    // Nothing could catch it: the wire was well formed and the banner drew.
    //
    // A SPLASH IS A MEDAL, NOT A KILL. The retail dm demo sends 20 of these in
    // ten minutes against 28 kills, and every one of them names a medal:
    //
    //   w 0 12 0      round_start                    once, 2.6 s in
    //   w 0 16 50     SPLASHES_HEADSHOT              4x
    //   w 0 18 0      SPLASHES_LONGSHOT              2x
    //   w 0 29 50     SPLASHES_REVENGE               5x
    //   w 0 34 100    SPLASHES_BUZZKILL              4x
    //   w 0 38 0      SPLASHES_FIRST_PLACE_KILL      3x
    //   w 0 406 0     destroyed_uav                  1x
    //
    // Reading `w 0 <row> 50` as "a kill" is what made the kill sound look
    // wrong: 28 mp_hit_kill plays against "8 kill splashes" is 28 kills against
    // 9 MEDALS, and the two numbers were never comparable. See section 113.
    inline constexpr std::uint32_t SvSplashSlotDefault = 0;
    // Slot 2 is the announcer/callout line, not the player's own banner: the
    // demo sends `w 2 4 0` (announcer_line), `w 2 368 0`
    // (used_strike_helicopter), `w 2 392 0` (callout_destroyed_helicopter) and
    // `w 2 393 0` (callout_destroyed_uav) - all match-wide events, all with 0
    // points. sub_C1C860 clamps the slot to 0..4.
    inline constexpr std::uint32_t SvSplashSlotCallout = 2;
    // Row 4 is `announcer_line`, and the splash table's row for it is EMPTY in
    // every column - no text, no icon, and no sound. It is the banner the
    // announcer speaks under, not the announcer itself: the demo pairs all
    // fourteen of its `w 2 4 0` with a high-band `p` on the same frame, and the
    // three that carry no banner are the killstreak callouts. So sending this
    // without a `p` shows nothing and says nothing.
    inline constexpr std::uint32_t SvSplashAnnouncerLine = 4;
    inline constexpr std::int32_t SvSplashAnnouncerLinePoints = 0;

    // WIRED. Each of these has an exact trigger that needs no invented
    // constant, and the point values are the demo's own.
    inline constexpr std::uint32_t SvSplashHeadshot = 16;
    inline constexpr std::int32_t SvSplashHeadshotPoints = 50;
    inline constexpr std::uint32_t SvSplashRevenge = 29;
    inline constexpr std::int32_t SvSplashRevengePoints = 50;
    inline constexpr std::uint32_t SvSplashFirstBlood = 33;
    // First blood does not occur in the demo - the recorder did not get it - so
    // its point value is the one thing here with no measurement behind it. 0
    // matches every other medal the demo sends with no bonus, and is the value
    // that cannot be wrong on the scoreboard.
    inline constexpr std::int32_t SvSplashFirstBloodPoints = 0;
    inline constexpr std::uint32_t SvSplashFirstPlaceKill = 38;
    inline constexpr std::int32_t SvSplashFirstPlaceKillPoints = 0;

    // MEDALS QUEUE, ONE EVERY 1500 ms. sub_C1C860 stores one splash per display
    // slot, so two sent on the same frame means the second overwrites the first
    // before it ever draws.
    //
    // MEASURED in the retail dm demo: the smallest gap between two slot-0
    // splashes is exactly 1500 ms and occurs FOUR times, never smaller - and
    // three bursts are several medals from ONE kill, spaced by exactly that:
    //
    //   t=143000 REVENGE(50) -> t=144500 BUZZKILL(100) -> t=146000 FIRSTPLACE(0)
    //   t=236400 BUZZKILL    -> t=237900 FIRSTPLACE
    //   t=513400 BUZZKILL    -> t=514900 LONGSHOT
    //
    // So a retail server does not decide which medal to show - it shows all of
    // them, in order, and the queue is what makes that visible.
    inline constexpr std::uint32_t SvSplashReleaseIntervalMilliseconds = 1500;
    // A player cannot earn medals faster than the queue drains for long, but a
    // client that stops draining must not grow one without bound. Anything past
    // this is dropped AND SAID SO - a silently truncated queue reads as a medal
    // that was never awarded.
    inline constexpr std::size_t SvSplashQueueLimit = 8;

    // THE POINTS ARE THE BANNER'S, NOT THE SCOREBOARD'S. Retail awards the
    // bonus as well as displaying it; this server displays it and dm.lua does
    // not add it, so a headshot reads "+50" in the banner while the scoreboard
    // moves by the kill's 50 alone. Sending 0 instead would be a smaller lie
    // and a bigger divergence, so the demo's value is sent and the seam is
    // named here: the bonus belongs in dm.lua, where scoring lives.

    // NOT WIRED, each because its trigger needs a constant that is in neither
    // the table nor the demo:
    //   30 DOUBLEKILL, 31 TRIPLEKILL, 32 MULTIKILL - a multi-kill WINDOW.
    //      MEASURED, and the answer is a REFUTATION rather than a value: the
    //      retail dm match contains ZERO multi-kill splashes, and its only pair
    //      of kills less than four seconds apart - t=240600 and t=242800, 2200
    //      ms - produced a REVENGE and nothing else. So this build does NOT use
    //      the 4000 ms window the IW games are known for; it is under 2200 ms,
    //      or it is not purely a time window at all. Porting 4 seconds because
    //      that is what CoD does would have been wrong and nothing in the build
    //      would have said so.
    //   18 LONGSHOT - a distance threshold.
    //   34 BUZZKILL - "ended a killstreak", which needs a streak length.
    //   20 AVENGER, 22 DEFENDER - per-pair damage history over a time window.
    //   406 destroyed_uav and the slot-2 callouts - killstreak entities this
    //      server does not spawn yet.

    // Hit locations, for the headshot trigger. TWO THINGS, AND ONLY ONE OF THEM
    // IS SETTLED.
    //
    // SETTLED (section 51g): the NAME table is 19 entries - none / helmet /
    // head / neck / torso_upper / torso_lower / the arm, hand, leg and foot
    // pairs / gun - identical in content and order on out.exe (0x00E4FB30,
    // 0x00E5AFB0) and 3.3.3.3 (0x00CD83B8, 0x00CDF3C8). The older comment here
    // claimed the block had "NO head entry, so picking one would be a guess";
    // that was a raw string block read as a table, which is the exact trap
    // section 51g exists to record.
    //
    // SETTLED TOO, LIVE: SvPlayerDamagePayload::hitLocation is the trace's PART
    // GROUP, and section 51h had left open whether partGroup is the NAME index
    // - BulletShieldPartGroup is 19, one past the 19 names, which fits both "one
    // space with a synthetic 19 for the shield" and "two similar spaces".
    //
    // The server logs every kill's part group, and one played match answered it:
    // 17 kills, part groups 2 (x11), 5 (x3), 4 (x2) and 6 (x1), each always
    // paired with the same bone - and the player reports the HEADSHOT medal
    // firing correctly. So partGroup 2 IS head, and the name table's order is
    // the part-group order.
    //
    // ONE THING IS STILL ODD AND IS NOT THIS CONSTANT: 11 of 17 kills reading as
    // head is a high rate for two players with rifles. It is recorded rather
    // than explained - see the locational-hitbox note about the gentity word
    // that scales the broadphase. It does not affect the medal, which is right.
    inline constexpr std::uint8_t SvHitLocationHelmet = 1;
    inline constexpr std::uint8_t SvHitLocationHead = 2;

    [[nodiscard]] std::string SV_BuildSplashCommand(
        std::uint32_t slot,
        std::uint32_t row,
        std::int32_t points);
}
