#pragma once

#include <bit>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace CodolGameServer
{
    // RETAIL'S STATIC ENTITY NUMBERS ARE DATA, NOT A RULE THIS SERVER GETS TO INVENT.
    //
    // Every map ships a `<map>_const.ff` next to `<map>.ff`, holding one rawfile:
    // `mp/constbaselines/bl_pc_<map>_<gametype>.bin`. It is an array of full 280-byte
    // entityState_t records -- the client loads it at map load (sub_515340 ->
    // sub_6613E0), indexes it by entity number into `dword_77CE488`, and resolves any
    // entity arriving with snapshot flag 0x10 against it (sub_470F60).
    //
    // So the entity number IS the identity: publish a door at the wrong number and the
    // client gives it an unrelated entity's origin, model and solid. This project spent
    // a long time trying to reproduce the numbering by walking the map entity string and
    // plateaued at 288/397 -- because the gaps encode which entities take a slot, which
    // is not recoverable from the entity list alone. The table below ends that: it is
    // read straight out of the shipped asset.
    //
    // Extraction and the full write-up: re/demo-re/16-const-baselines.md.
    // Regenerate with Tools/gen-const-baselines.py.
    struct SvConstBaselineEntry
    {
        // Retail's entity number. Ascending, no duplicates, lowest is 37 --
        // which is FirstDynamicServerEntityNum, derived independently here.
        std::uint16_t entityNum{};
        // ET_SCRIPTMOVER (6), ET_FX (8), ET_LIGHT (11). Every brush model is 6.
        std::uint8_t eType{};
        // The `*N` brush model index, entityState +0x09C, 10 bits. Non-zero
        // exactly when this entity is a script_brushmodel; the netfield table
        // mis-names this field `clientNum` (see 16-const-baselines.md).
        std::uint16_t brushModelIndex{};
        // The XModel configstring index, entityState +0x05C, 10 bits. Zero on
        // every brush model -- a brush model carries no xmodel.
        std::uint16_t xmodelIndex{};

        // The rest of the record, so the server can DELTA AGAINST IT rather than
        // against a zeroed struct. That is the whole point of snapshot flag
        // 0x10: fields equal to the baseline are never sent, which is why
        // retail's static scriptmovers assert almost nothing on the wire.
        std::uint32_t solid{};
        std::uint32_t eFlags{};
        // Floats are carried as their raw bit patterns and bit_cast back, not as
        // decimal literals. These are compared for EXACT equality against the
        // server's own map parse to decide whether a field is sent at all, and a
        // lossy round trip through a decimal literal would turn a silent entity
        // into a chatty one.
        std::uint32_t originBits[3]{};   // lerp.pos.trBase, netfields 1/2/4
        std::uint32_t anglesBits[3]{};   // lerp.apos.trBase, netfields 10/3/9
        std::uint32_t scaleBits{};       // netfield 46, +0x054
        std::uint16_t field0058{};       // netfield 27, +0x058, 11 bits
        std::uint16_t field00E4{};       // netfield 25, +0x0E4, 8 bits
        std::uint16_t field0098{};       // netfield 47, +0x098, 5 bits
        std::int32_t field0070{};        // netfield 21, +0x070, codec -7
        std::uint8_t positionTrajectoryType{};  // netfield 15, +0x00C
        std::uint8_t angleTrajectoryType{};     // netfield 12, +0x030
        // THE TRAJECTORY, WHICH IS WHERE AN UNMODELLED FIELD STOPS BEING HARMLESS.
        //
        // An entity published on a table number inherits every field the server does not
        // override, and the server can only override what it MODELS. Leaving these out
        // meant a prop could take a VELOCITY (`pos.trDelta`) and an angular velocity
        // (`apos.trDelta`) from its row and quietly drift and spin. Six of factory's
        // script-model rows carry exactly that -- entities 475..480, the zapper arms, at
        // trType 1 with deltas like (-141, 0, -79) and a -180 spin.
        //
        // Carried here so the writer compares against the truth and sends this server's
        // own value where it differs, instead of comparing zero against zero and calling
        // it unchanged.
        std::uint32_t positionTrajectoryTime{};      // +0x010
        std::uint32_t positionTrajectoryDuration{};  // +0x014
        std::uint32_t angleTrajectoryTime{};         // +0x034
        std::uint32_t angleTrajectoryDuration{};     // +0x038
        std::uint32_t positionTrajectoryDeltaBits[3]{};  // +0x024/028/02C
        std::uint32_t angleTrajectoryDeltaBits[3]{};     // +0x048/04C/050
        std::uint32_t surfType{};                    // +0x090
    };

    struct SvConstBaselineTable
    {
        std::string_view mapName;
        // The gametype token the asset was keyed on. The client only loads the
        // file when `mp/constBaselinesTable.csv` lists this map/gametype pair,
        // and it FAILS CLOSED: a rejected pair loads no baselines at all and
        // every static entity silently resolves to a zeroed struct.
        std::string_view gameType;
        std::span<const SvConstBaselineEntry> entries;
    };

    // Null when this build ships no extracted table for the map, which is the
    // normal case for every map whose `_const.ff` is still packed inside an
    // `.ifs`. Callers must degrade to sequential numbering rather than fail.
    // KEYED ON THE PAIR. A zombie map has one gametype, so map alone was a unique
    // key and this took only a map. mp_nuked ships THIRTEEN tables and `dd` is laid
    // out first, so a map-only lookup hands a deathmatch server domination's entity
    // numbering -- and the numbering IS the identity (see the note above): a door
    // published on the wrong number becomes some other entity's origin, model and
    // solid on the client. Falls back to the map's first table when the pair is
    // unknown, which is what a one-gametype map wants.
    [[nodiscard]] const SvConstBaselineTable *SV_ConstBaselineTable(
        std::string_view mapName,
        std::string_view gameType);

    // The retail entity number for a `*N` brush model, or nullopt when the map
    // has no table or the index is not in it. `brushModelIndex` is the clip
    // handle the map entity string's `model` key parses to -- retail's `*N` and
    // this server's clipHandle are the same number.
    [[nodiscard]] inline std::optional<std::uint32_t>
        SV_ConstBaselineBrushModelEntityNum(
            const SvConstBaselineTable *const table,
            const std::uint32_t brushModelIndex)
    {
        if (!table || !brushModelIndex)
            return std::nullopt;
        for (const auto &entry : table->entries)
        {
            if (entry.brushModelIndex == brushModelIndex)
                return entry.entityNum;
        }
        return std::nullopt;
    }

    // RETAIL'S NUMBER FOR A script_model. Unlike a brush model there is no `*N` to key on,
    // so the key is the ORIGIN -- both sides parse it out of the same map entity string, so
    // the float32s are bit-identical rather than merely close.
    //
    // 126 of factory's 134 reachable script-model rows are unique by origin alone. The
    // other 8 are CO-LOCATED PAIRS differing only in xmodel (391/392 and 389/390 -- props
    // that sit in the same spot), so `xmodelIndex` breaks those ties WHEN this server's
    // model configstring band agrees with retail's. It may not, which is why a failed
    // tie-break returns nothing rather than guessing: an entity on the wrong number
    // inherits a stranger's baseline, and sequential numbering merely costs wire bytes.
    // The single script-model row at this origin, or null when there is none or more than
    // one. Used to MEASURE this server's model configstring band against retail's: a prop
    // with exactly one candidate row needs no tie-break, so the pair of model indices is a
    // clean observation of the offset between the two bands.
    [[nodiscard]] inline const SvConstBaselineEntry *
        SV_ConstBaselineScriptModelRowByOrigin(
            const SvConstBaselineTable *const table,
            const float *const origin)
    {
        if (!table)
            return nullptr;
        const SvConstBaselineEntry *match = nullptr;
        for (std::size_t slot = 1; slot < table->entries.size(); ++slot)
        {
            const auto &entry = table->entries[slot];
            if (entry.eType != 6 || entry.brushModelIndex != 0)
                continue;
            if (std::bit_cast<float>(entry.originBits[0]) != origin[0] ||
                std::bit_cast<float>(entry.originBits[1]) != origin[1] ||
                std::bit_cast<float>(entry.originBits[2]) != origin[2])
            {
                continue;
            }
            if (match)
                return nullptr;
            match = &entry;
        }
        return match;
    }

    [[nodiscard]] inline std::optional<std::uint32_t>
        SV_ConstBaselineScriptModelEntityNum(
            const SvConstBaselineTable *const table,
            const float *const origin,   // three floats: x, y, z
            const std::uint16_t xmodelIndex)
    {
        if (!table)
            return std::nullopt;
        const SvConstBaselineEntry *match = nullptr;
        const SvConstBaselineEntry *tieBreak = nullptr;
        std::size_t matches = 0;
        // Slot 0 is skipped for the same reason as everywhere else: the client cannot
        // reach it, so this server must not claim it.
        for (std::size_t slot = 1; slot < table->entries.size(); ++slot)
        {
            const auto &entry = table->entries[slot];
            if (entry.eType != 6 || entry.brushModelIndex != 0)
                continue;
            if (std::bit_cast<float>(entry.originBits[0]) != origin[0] ||
                std::bit_cast<float>(entry.originBits[1]) != origin[1] ||
                std::bit_cast<float>(entry.originBits[2]) != origin[2])
            {
                continue;
            }
            ++matches;
            match = &entry;
            if (xmodelIndex && entry.xmodelIndex == xmodelIndex)
                tieBreak = tieBreak ? nullptr : &entry;
        }
        if (matches == 1)
            return match->entityNum;
        if (matches > 1 && tieBreak)
            return tieBreak->entityNum;
        return std::nullopt;
    }

    // The baseline the CLIENT will resolve this entity number against, or null when it
    // will resolve a zeroed struct instead. A server that deltas against anything else
    // corrupts the entity: every field ships as `value ^ baseline`, so disagreeing about
    // the baseline is not a missed optimisation, it is wrong data on the wire.
    //
    // SLOT 0 IS DELIBERATELY UNREACHABLE, because it is unreachable in the client. The
    // index array `dword_77CE488` is zero-filled and the guard in sub_470F60 is
    // `v2 > 0`, so "slot 0" and "not in the table" are the same answer there and the
    // entity falls back to a zeroed struct. Factory's slot 0 is entity 37 -- which the
    // retail demo duly shows arriving with eType 0 while the file says 6. Returning the
    // real record here would make this server the only one of the two using it.
    [[nodiscard]] inline const SvConstBaselineEntry *SV_ConstBaselineEntityState(
        const SvConstBaselineTable *const table,
        const std::uint32_t entityNum)
    {
        if (!table || table->entries.empty())
            return nullptr;
        for (std::size_t slot = 1; slot < table->entries.size(); ++slot)
        {
            if (table->entries[slot].entityNum == entityNum)
                return &table->entries[slot];
        }
        return nullptr;
    }
}
