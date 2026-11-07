#include "sv_scoreboard_mp.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace CodolGameServer
{
    namespace
    {
        // mp/playerdata.def.  aarScoreboard is indexedArray[19]; consecutive rows sit
        // 198 bytes apart because several of its fields live outside the row block on
        // their own stride.
        //
        // VERIFIED ON 1649370's OWN def, and the answer is that these numbers are RIGHT.
        // Section 49 concluded the opposite -- same version 233, different formatChecksum
        // (0x4A6CC345 against 3.3.3.3's 0xE32D50D6), different enum field set, therefore a
        // different row layout -- and that inference was wrong. The def really does differ
        // everywhere it was measured to: 8 structs against 4, 40 indexed arrays against
        // 26, size 15767 against 14426, offset table 3927 entries against 3414. The
        // aarScoreboard ROW is nonetheless byte-for-byte identical, including all five
        // bit-addressed fields.
        //
        // Tools/olfinal/decode-playerdata-offsets.py resolves it offline from the zone.
        // out.exe never hardcodes these offsets -- sub_50C570 asks for
        // {"aarScoreboard", "<row>", "isMe"} by NAME and sub_50F2C0/sub_50F410 walk the
        // def, converting an accumulated INDEX through the table at def+0x38 -- so the
        // def is the only source, and an indexed array shows up in that table as 19
        // repetitions of one index block with a constant delta per column. Calibrated by
        // reproducing all twenty-one of the offsets below from 3.3.3.3's def, `isMe`
        // included, whose entry 1256 is a BIT offset = byte 157 bit 0.
        //
        // CONFIRMED TWICE, BY DECODERS THAT SHARE NO CODE. Tools/ffa/parse-structureddatadef.py
        // was written in an earlier session and walks the asset as a depth-first zone stream;
        // fed 1649370's def it reports `consumed 22940 of 22940 bytes EXACT`, which is a real
        // check because the stream has no alignment padding and a wrong record layout cannot
        // reach the last byte. It names every field and agrees with the shape-based decode on
        // all of them, `isMe`'s bit offset included. Section 49 had that parser available and
        // never ran it on this build's def.
        //
        // THE ONE REAL DIFFERENCE: this build's row block has 27 columns, not 26. The extra
        // one is `damage`, at byte 15071 with a per-row stride of 4, so it lives outside the
        // row the way dw_userID_hi/lo (9626/9630, stride 8), netcafe_privileges (9426) and
        // qq_membership (9430) already do. It is an OLfinal-only column and nothing here
        // writes it.
        constexpr std::uint32_t RowBase = 67;
        constexpr std::uint32_t RowStride = 198;

        // Field offsets relative to a row's base.  Read out of the def's own offset
        // table: a property's stored `offset` is an INDEX and the table entry is the
        // byte offset -- or, for a bool, the BIT offset. Every one of these is confirmed
        // against 1649370's table as well as 3.3.3.3's; they agree.
        constexpr std::uint32_t FieldAssists = 0;      // 67
        constexpr std::uint32_t FieldClan = 5;         // 72,  char[65]
        constexpr std::uint32_t FieldDeaths = 70;      // 137
        constexpr std::uint32_t FieldDowns = 74;       // 141
        constexpr std::uint32_t FieldGp = 78;          // 145
        constexpr std::uint32_t FieldHeadshots = 82;   // 149
        constexpr std::uint32_t FieldHits = 86;        // 153
        constexpr std::uint32_t FieldIsMe = 90;        // 157, bit 0
        constexpr std::uint32_t FieldKills = 91;       // 158
        constexpr std::uint32_t FieldKillstreak = 95;  // 162
        constexpr std::uint32_t FieldName = 99;        // 166, char[65]
        constexpr std::uint32_t FieldObjectives = 164; // 231
        constexpr std::uint32_t FieldPing = 168;       // 235
        constexpr std::uint32_t FieldRank = 172;       // 239, byte
        constexpr std::uint32_t FieldRevives = 173;    // 240
        constexpr std::uint32_t FieldScore = 177;      // 244
        constexpr std::uint32_t FieldShots = 181;      // 248
        constexpr std::uint32_t FieldSkill = 185;      // 252
        constexpr std::uint32_t FieldStatusIcon = 189; // 256
        constexpr std::uint32_t FieldTeam = 193;       // 260, byte
        constexpr std::uint32_t FieldXp = 194;         // 261

        // Match-level fields, at fixed offsets rather than per row. Both CONFIRMED on
        // 1649370: scoreLimit is table index 67 here and 64 there, teamScores index 585
        // here and 560 there, and both resolve to the same bytes on both builds. 9782 is
        // followed by 9786 and 9790 in both tables, which is what makes [1] then [2]
        // readable rather than assumed.
        constexpr std::uint32_t OffsetRoundNumber = 59;
        constexpr std::uint32_t OffsetScoreLimit = 63;
        constexpr std::uint32_t OffsetTeamScores = 9782;  // [1] then [2]
        // Out-of-row indexed columns. The def places hi then lo at an
        // eight-byte stride; the podium card consumer stores the two named
        // properties as one account identity.
        constexpr std::uint32_t OffsetUserIds = 9626;
        constexpr std::uint32_t UserIdStride = 8;

        // The row splits into three runs so that clan and name - the two
        // char[65] fields - are never overwritten.  The client fills those in
        // itself from live client info after reading the numeric columns, so
        // clobbering them would only be wasteful rather than wrong, but leaving
        // them alone keeps the update to 67 bytes a row instead of 198.
        constexpr std::uint32_t RunOneBegin = FieldAssists;
        constexpr std::uint32_t RunOneEnd = FieldClan;
        constexpr std::uint32_t RunTwoBegin = FieldDeaths;
        constexpr std::uint32_t RunTwoEnd = FieldName;
        constexpr std::uint32_t RunThreeBegin = FieldObjectives;
        constexpr std::uint32_t RunThreeEnd = RowStride;

        void writeInt32(
            std::span<std::uint8_t> run,
            const std::uint32_t runBegin,
            const std::uint32_t field,
            const std::int32_t value)
        {
            const auto at = field - runBegin;
            const auto raw = static_cast<std::uint32_t>(value);
            run[at] = static_cast<std::uint8_t>(raw);
            run[at + 1] = static_cast<std::uint8_t>(raw >> 8);
            run[at + 2] = static_cast<std::uint8_t>(raw >> 16);
            run[at + 3] = static_cast<std::uint8_t>(raw >> 24);
        }

        void writeUInt32(
            std::span<std::uint8_t> run,
            const std::uint32_t at,
            const std::uint32_t value)
        {
            run[at] = static_cast<std::uint8_t>(value);
            run[at + 1] = static_cast<std::uint8_t>(value >> 8);
            run[at + 2] = static_cast<std::uint8_t>(value >> 16);
            run[at + 3] = static_cast<std::uint8_t>(value >> 24);
        }
    }

    std::vector<SvProfilePatch> SV_BuildScoreboardProfilePatches(
        const std::span<const SvScoreboardEntry> entries,
        const SvScoreboardMatchState &match)
    {
        std::vector<SvProfilePatch> patches;
        patches.reserve(entries.size() * 4 + 3);

        for (const auto &entry : entries)
        {
            if (entry.clientNum >= SvScoreboardRowCount)
                continue;
            const auto rowBase = RowBase + RowStride * entry.clientNum;

            SvProfilePatch one{ .offset = rowBase + RunOneBegin,
                                .data = std::vector<std::uint8_t>(
                                    RunOneEnd - RunOneBegin) };
            writeInt32(one.data, RunOneBegin, FieldAssists, entry.assists);
            patches.push_back(std::move(one));

            // deaths, downs, gp, headshots, hits, isMe, kills, killstreak.
            // isMe is a single bit at bit 0 of its byte and the client writes it
            // itself, so the byte is left zero.
            SvProfilePatch two{ .offset = rowBase + RunTwoBegin,
                                .data = std::vector<std::uint8_t>(
                                    RunTwoEnd - RunTwoBegin) };
            writeInt32(two.data, RunTwoBegin, FieldDeaths, entry.deaths);
            writeInt32(two.data, RunTwoBegin, FieldDowns, entry.downs);
            writeInt32(two.data, RunTwoBegin, FieldGp, entry.gp);
            writeInt32(two.data, RunTwoBegin, FieldHeadshots, entry.headshots);
            writeInt32(two.data, RunTwoBegin, FieldHits, entry.hits);
            writeInt32(two.data, RunTwoBegin, FieldKills, entry.kills);
            writeInt32(two.data, RunTwoBegin, FieldKillstreak, entry.killstreak);
            patches.push_back(std::move(two));

            // objectives, ping, rank, revives, score, shots, skill, status_icon,
            // team, xp.  rank and team are single bytes the client overwrites
            // from live client info immediately after reading this row.
            SvProfilePatch three{ .offset = rowBase + RunThreeBegin,
                                  .data = std::vector<std::uint8_t>(
                                      RunThreeEnd - RunThreeBegin) };
            writeInt32(three.data, RunThreeBegin, FieldObjectives, entry.objectives);
            writeInt32(three.data, RunThreeBegin, FieldPing, entry.ping);
            writeInt32(three.data, RunThreeBegin, FieldRevives, entry.revives);
            writeInt32(three.data, RunThreeBegin, FieldScore, entry.score);
            writeInt32(three.data, RunThreeBegin, FieldShots, entry.shots);
            writeInt32(three.data, RunThreeBegin, FieldSkill, entry.skill);
            writeInt32(three.data, RunThreeBegin, FieldStatusIcon, entry.statusIcon);
            writeInt32(three.data, RunThreeBegin, FieldXp, entry.xp);
            static_cast<void>(FieldRank);
            static_cast<void>(FieldTeam);
            patches.push_back(std::move(three));
        }

        // Retail's initial AAR patch writes eight bytes for each occupied
        // client row at 9626 + 8*r. Preserve the profile def's hi/lo order;
        // `userId` is the same XUID already authenticated by the connection.
        for (const auto &entry : entries)
        {
            if (entry.clientNum >= SvScoreboardRowCount)
                continue;
            SvProfilePatch identity{
                .offset = OffsetUserIds + UserIdStride * entry.clientNum,
                .data = std::vector<std::uint8_t>(UserIdStride),
            };
            writeUInt32(identity.data, 0,
                static_cast<std::uint32_t>(entry.userId >> 32));
            writeUInt32(identity.data, 4,
                static_cast<std::uint32_t>(entry.userId));
            patches.push_back(std::move(identity));
        }

        // MEASURED (retail dm, final transaction seq=1427): this changes from
        // zero to one on the exact frame the match ends. It is separate from
        // the row XP/GP update and is the root AAR completion marker.
        SvProfilePatch round{ .offset = OffsetRoundNumber,
                              .data = std::vector<std::uint8_t>(4) };
        writeInt32(round.data, 0, 0, match.roundNumber);
        patches.push_back(std::move(round));

        SvProfilePatch limit{ .offset = OffsetScoreLimit,
                              .data = std::vector<std::uint8_t>(4) };
        writeInt32(limit.data, 0, 0, match.scoreLimit);
        patches.push_back(std::move(limit));

        // aarTeamScores[1] and [2] are adjacent, and CG_InitScoreboardFromProfile
        // reads them straight into the two team-score words that the 'C' and 'D'
        // commands otherwise set.
        SvProfilePatch teams{ .offset = OffsetTeamScores,
                              .data = std::vector<std::uint8_t>(8) };
        writeInt32(teams.data, 0, 0, match.teamScoreTf);
        writeInt32(teams.data, 0, 4, match.teamScoreSc);
        patches.push_back(std::move(teams));

        return patches;
    }

    std::vector<std::vector<std::uint8_t>> SV_FrameProfilePatchCommands(
        const std::span<const SvProfilePatch> patches,
        const std::size_t maximumPayload)
    {
        std::vector<std::vector<std::uint8_t>> commands;
        if (patches.empty())
            return commands;

        // Each run costs a 4-byte offset, a 1-byte length and its bytes, and a
        // run's length is written as a single byte, so 255 is the hard ceiling
        // sub_C1BF70 can express.
        constexpr std::size_t RunHeader = 5;
        constexpr std::size_t RunMaximum = 255;

        std::vector<std::uint8_t> current{ SvProfilePatchLoadOnly };
        const auto flush = [&]() {
            if (current.size() > 1)
                commands.push_back(std::move(current));
            current = std::vector<std::uint8_t>{ SvProfilePatchLoadOnly };
        };

        for (const auto &patch : patches)
        {
            if (patch.data.empty() || patch.data.size() > RunMaximum)
                continue;
            if (current.size() + RunHeader + patch.data.size() > maximumPayload)
                flush();
            if (current.size() + RunHeader + patch.data.size() > maximumPayload)
                continue;
            current.push_back(static_cast<std::uint8_t>(patch.offset));
            current.push_back(static_cast<std::uint8_t>(patch.offset >> 8));
            current.push_back(static_cast<std::uint8_t>(patch.offset >> 16));
            current.push_back(static_cast<std::uint8_t>(patch.offset >> 24));
            current.push_back(static_cast<std::uint8_t>(patch.data.size()));
            current.insert(current.end(), patch.data.begin(), patch.data.end());
        }
        flush();

        // Only the last command rebuilds, so the client never redraws a
        // half-updated scoreboard.
        if (!commands.empty())
            commands.back()[0] = SvProfilePatchLoadAndRebuild;
        return commands;
    }
}
