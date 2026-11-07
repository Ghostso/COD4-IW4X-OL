#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace CodolGameServer
{
    // The scoreboard is not built from reliable commands.  CG_ServerCommand
    // (CODREF: 0x0057D560) has exactly one scoreboard writer, 'E', and it writes
    // a row's score and nothing else; kills, deaths and assists have no command
    // at all.  CG_InitScoreboardFromProfile (CODREF: 0x0057B760) rebuilds every
    // row from the mp/playerdata.def profile blob, which the server fills with
    // the binary command 'J'.
    //
    // See re/OLMOD-SCOREBOARD.md in the research tree for the derivation of every
    // constant below, including how the offsets were read out of the shipped
    // def asset rather than inferred from traffic.

    // OLMOD(section-81): `sub_C1BF70` AND `0x0057BF70` ARE THE SAME 3.3.3.3 ADDRESS.
    // The CODOL i64 is rebased +0x6A0000, so 3.3.3.3's sub_57BF70 is named sub_C1BF70
    // inside it. Written side by side they read as two builds; out.exe's own
    // 0x00C1BF70 is an unrelated function. **NOTHING BELOW HAS BEEN CHECKED ON THE
    // HOST**, and SvProfilePatchMaximumPayload's own comment already says so.
    //
    // 3.3.3.3's sub_57BF70 reads the payload after the verb byte as a sparse patch
    // stream and copies each run into the profile data at +128. Its two profile-slot
    // offsets are `add eax, 0x91B8` and `add eax, 0x90`, and NEITHER immediate occurs
    // in out.exe -- so the profile record moved and the counterpart has to be found
    // by shape, not by rebasing this address.
    // 'J' loads into profile slot 0 and then rebuilds the scoreboard; 'K' loads
    // without rebuilding, which is what makes a multi-command update possible.
    inline constexpr std::uint8_t SvProfilePatchLoadAndRebuild = 'J';
    inline constexpr std::uint8_t SvProfilePatchLoadOnly = 'K';

    // CG_InitScoreboardFromProfile walks aarScoreboard[0..18] and uses the loop
    // counter as both the profile index and the row's client number, so a row is
    // addressed by client number directly.
    inline constexpr std::size_t SvScoreboardRowCount = 19;

    // The largest binary payload queueReliableBinaryCommand will accept.
    //
    // OLMOD(section-85): SETTLED, and the answer is that this was never an
    // ENGINE constant to carry -- it is a self-imposed cap, and the engine
    // limit that constrains it is IDENTICAL on both builds. The client's
    // reliable-command store is 3.3.3.3 sub_46E3B0 / out.exe sub_4737E0
    // (section 82a), and the two agree instruction for instruction on every
    // number that bounds a command string:
    //
    //   sub esp, 408h ... lea eax,[ebp-404h] ; push 400h   read at most 1024
    //   push 3FFh ; shl ebx, 0Ah ; lea esi,[ebx+ecx+K]     store at most 1023
    //   mov byte [esi+3FFh], 0                             and NUL-terminate
    //
    // Only the ring mask (0FFh vs 1FFh), the ring base (40154h vs 80154h) and
    // the globals differ. So the real ceiling for `verb + payload` is 1023
    // characters, i.e. 0x3FE of payload, on BOTH builds -- and 0x3FC is two
    // under it either way. Not "3.3.3.3's number until proven otherwise": the
    // thing that would make it wrong has been read here and is the same.
    //
    // Section 81b's route to this -- find out.exe's counterpart of the profile
    // patch READER, 3.3.3.3's sub_57BF70 -- is still unwalked and is no longer
    // needed for this constant. That reader's own bound is `cmp eax, 7FFCh` on
    // a 4-byte patch offset (0x0057BFD8), which is a different quantity.
    inline constexpr std::size_t SvProfilePatchMaximumPayload = 0x3FC;

    struct SvScoreboardEntry
    {
        std::uint32_t clientNum{};
        // The callsign/player-card builder reads these same 64 bits from
        // aarScoreboard[row].dw_userID_hi/lo before binding the podium slot.
        std::uint64_t userId{};
        std::int32_t score{};
        std::int32_t kills{};
        std::int32_t deaths{};
        std::int32_t assists{};
        std::int32_t headshots{};
        std::int32_t objectives{};
        std::int32_t downs{};
        std::int32_t revives{};
        std::int32_t killstreak{};
        std::int32_t ping{};
        std::int32_t xp{};
        std::int32_t gp{};
        std::int32_t skill{};
        std::int32_t hits{};
        std::int32_t shots{};
        std::int32_t statusIcon{};

        bool operator==(const SvScoreboardEntry &) const = default;
    };

    struct SvScoreboardMatchState
    {
        std::int32_t roundNumber{};
        std::int32_t scoreLimit{};
        std::int32_t teamScoreTf{};
        std::int32_t teamScoreSc{};

        bool operator==(const SvScoreboardMatchState &) const = default;
    };

    // One patch run: a byte offset into the 14,426-byte profile blob and the
    // bytes to write there.  Exposed so a test can assert the offsets without
    // reaching through the command framing.
    struct SvProfilePatch
    {
        std::uint32_t offset{};
        std::vector<std::uint8_t> data;

        bool operator==(const SvProfilePatch &) const = default;
    };

    std::vector<SvProfilePatch> SV_BuildScoreboardProfilePatches(
        std::span<const SvScoreboardEntry> entries,
        const SvScoreboardMatchState &match);

    // Frames the patches into binary commands, each no larger than
    // maximumPayload.  Every command but the last carries 'K' so the client only
    // rebuilds once, after the whole update has landed.
    std::vector<std::vector<std::uint8_t>> SV_FrameProfilePatchCommands(
        std::span<const SvProfilePatch> patches,
        std::size_t maximumPayload);
}
