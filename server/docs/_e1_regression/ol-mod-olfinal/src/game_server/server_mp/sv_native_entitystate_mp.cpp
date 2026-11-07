#include "sv_native_entitystate_mp.hpp"
#include "../../shared/RuntimeLog.hpp"

#include <string>

#include <algorithm>
#include <bit>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <limits>
#include <type_traits>

namespace CodolGameServer
{
    namespace
    {
        // OLMOD(native-entitystate-source-view): this file exposes a validated
        // source-side view over only the CODOL entityState_s fields confirmed
        // by native conversion writes and snapshot consumers. It is not a
        // replacement entityState_s definition and leaves all other bytes
        // opaque.
        // CODDIFF(1649370): entityState_s grew TWICE between the builds -- a
        // 16-bit field at 0x60 pushes everything from there by +4, and another
        // dword before 0xA4 makes it +8 from there on -- and the struct itself
        // went 0x110 -> 0x118 bytes. The map is the two builds' extracted
        // ET_PLAYER netfield tables aligned on (bits, codec), which agree field
        // for field, and BG_PlayerStateToEntityState (A sub_4131A0 <-> C
        // sub_411360) settles the one run the tables cannot: three consecutive
        // 16-bit fields at 0x60/0x64/0x68 where the aligner cannot tell which
        // one this build inserted. It reads es+96 <- ps and es+100 <- ps on the
        // A side against es+100 and es+104 here, so 0x60 -> 0x64 and 0x64 ->
        // 0x68 and the NEW field is the one at 0x60.
        //
        // Writing 3.3.3.3's offsets into this build's entityState is worse than
        // reading a wrong value: 0xD0 is an EVENT slot here (codec -94), so the
        // weapon index went into an event field and FIRED EVENTS every frame.
        // legsAnim and torsoAnim also widened 11 -> 12 bits on the wire.
        constexpr std::size_t NumberOffset = 0x00;
        constexpr std::size_t EntityTypeOffset = 0x04;
        constexpr std::size_t EntityFlagsOffset = 0x08;
        constexpr std::size_t PositionTrajectoryTypeOffset = 0x0C;
        constexpr std::size_t PositionTrajectoryTimeOffset = 0x10;
        constexpr std::size_t PositionTrajectoryDurationOffset = 0x14;
        constexpr std::array<std::size_t, 3> OriginOffsets{ 0x18, 0x1C, 0x20 };
        constexpr std::array<std::size_t, 3> PositionTrajectoryDeltaOffsets{
            0x24, 0x28, 0x2C,
        };
        constexpr std::size_t AngleTrajectoryTypeOffset = 0x30;
        constexpr std::size_t AngleTrajectoryTimeOffset = 0x34;
        constexpr std::size_t AngleTrajectoryDurationOffset = 0x38;
        constexpr std::array<std::size_t, 3> AngleOffsets{ 0x3C, 0x40, 0x44 };
        constexpr std::array<std::size_t, 3> AngleTrajectoryDeltaOffsets{
            0x48, 0x4C, 0x50,
        };
        constexpr std::size_t MovementDirOffset = 0x5C;
        // BG_UpdatePlayerDObj copies ET_PLAYER +0x54 into DObj_s::scale
        // (+0xC8) before shared skeleton and locational trace calculation.
        constexpr std::size_t PlayerSizeScaleOffset = 0x54;
        constexpr std::size_t GroundEntityOffset = 0x8C;
        constexpr std::size_t ClientNumOffset = 0xA0;
        constexpr std::size_t UnknownA0Offset = 0xA4;
        constexpr std::size_t SolidOffset = 0xAC;
        // ET_ACTOR field 29. Demo agentState field 8 and entityState +0x9C
        // carry the same presentation model selector.
        constexpr std::size_t ModelIndexOffset = 0x9C;
        // ET_PLAYER index 24, SEVEN bits on the wire. See SvEntityState::time2 for what
        // a real server puts here and why this build was sending nothing.
        constexpr std::size_t Time2Offset = 0x7C;
        constexpr std::uint32_t MaximumTime2 = 0x7F;
        constexpr std::size_t EventSequenceOffset = 0xB4;
        constexpr std::size_t EventsOffset = 0xB8;
        constexpr std::size_t WeaponAssetIndexOffset = 0xD8;
        constexpr std::size_t PresentationWeaponAssetIndexOffset = 0xDA;
        constexpr std::size_t OffhandWeaponAssetIndexOffset = 0x64;
        constexpr std::size_t CoKnifeStatsIndexOffset = 0x68;
        constexpr std::size_t UnknownE0Offset = 0xE8;
        // CODREF(bg_update_player_dobj): the sense follows playerState's, which
        // sv_native_playerstate_mp.cpp derives from CODOL's body-part table.
        // OLMOD(section-84): and BOTH are confirmed against out.exe's own
        // ET_PLAYER netfield table -- 0xDC and 0xE0, twelve bits each, which is
        // an animation index either side. See the playerState file for the
        // 0x00E60558 body-part table this build actually carries.
        // BG_PlayerStateToEntityState's field copier sub_AB31A0 (VA 0x004131A0)
        // forwards playerState +0x0C8 -> entityState +0xD4 at 0x0041321C and
        // +0x0D0 -> +0xD8 at 0x00413228, so legs stays at +0xD4 and torso at
        // +0xD8 across the conversion.
        constexpr std::size_t LegsAnimOffset = 0xDC;
        constexpr std::size_t TorsoAnimOffset = 0xE0;
        constexpr std::uint32_t MaximumEntityNumber = 2047;
        constexpr std::uint32_t MaximumEntityFlags = 0x3FFFFFFF;
        constexpr std::uint32_t MaximumWeaponAssetIndex = 0x7FF;
        constexpr std::uint32_t PlayerEntityType = 1;

        template <typename Value>
        void writeValue(
            SvNativeEntityState &state,
            const std::size_t offset,
            const Value &value)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            std::memcpy(state.bytes.data() + offset, &value, sizeof(value));
        }

        template <typename Value>
        Value readValue(
            const SvNativeEntityState &state,
            const std::size_t offset)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            Value value{};
            std::memcpy(&value, state.bytes.data() + offset, sizeof(value));
            return value;
        }

        float decodeSecureOrigin(
            const SvNativeEntityState &state,
            const std::size_t offset,
            const std::uint32_t key)
        {
            const auto encoded = readValue<std::uint32_t>(state, offset);
            const auto fieldAddress = static_cast<std::uint32_t>(
                reinterpret_cast<std::uintptr_t>(state.bytes.data() + offset));
            return std::bit_cast<float>(encoded ^ fieldAddress ^ ~key);
        }

        void relocateSecureOriginWords(
            SvNativeEntityState &destination,
            const SvNativeEntityState &source)
        {
            // CODREF(client_think_real): CODOL
            // BG_PlayerToEntity_SetTrajectory 0x00413360 binds each encrypted
            // origin word to its field address. BO1/Ghosts retain the same
            // secure-trajectory responsibility although their layouts differ.
            // OLMOD(address-bound-entitystate-owner): C++ value copies must
            // preserve plaintext while moving that address-bound native image.
            if (!source.secureOriginAddressBound)
                return;
            for (const auto offset : OriginOffsets)
            {
                auto encoded = readValue<std::uint32_t>(source, offset);
                const auto sourceAddress = static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(
                        source.bytes.data() + offset));
                const auto destinationAddress = static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(
                        destination.bytes.data() + offset));
                encoded ^= sourceAddress ^ destinationAddress;
                writeValue(destination, offset, encoded);
            }
        }

        std::optional<SvNativeEntityStateProjection> readProjection(
            const SvNativeEntityState &state,
            const SvEntityOriginKeys *const originKeys)
        {
            // TWENTY-SIX TERMS, ONE `return std::nullopt`. Every one of these bounds is a
            // claim about THIS build, and a rejection that names none of them is the exact
            // shape that cost this project three cycles on the pinned usercmd queue. Make
            // the conjunction say which term refused and with what value; a bound that is
            // still 3.3.3.3's then identifies itself the first time it fires.
            // The reporter is declared HERE, in front of the first refusal, because THREE
            // returns in this function sat ahead of the old lambda and said nothing at
            // all -- which is why this function was still the open question after the
            // twelve-bit animation bound was fixed and its named terms went quiet.
            const auto report = [](const char *const term, const std::string &value) {
                static std::string reported;
                auto details = std::string(term) + "=" + value;
                if (details != reported)
                {
                    reported = details;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "entitystate projection refused " + details);
                }
                return std::optional<SvNativeEntityStateProjection>{};
            };
            const auto refuse = [&report](
                                    const char *const term,
                                    const std::int64_t value) {
                return report(term, std::to_string(value));
            };
            if (originKeys && !state.secureOriginAddressBound)
                return refuse("secureOriginAddressUnbound", 1);
            const auto number = readValue<std::uint32_t>(state, NumberOffset);
            const auto nativeEntityType = readValue<std::uint32_t>(
                state, EntityTypeOffset);
            const auto eFlags = readValue<std::uint32_t>(state, EntityFlagsOffset);
            const auto nativeEventSequence = readValue<std::uint32_t>(
                state, EventSequenceOffset);
            const auto weaponAssetIndex = readValue<std::uint16_t>(
                state, WeaponAssetIndexOffset);
            const auto presentationWeaponAssetIndex = readValue<std::uint16_t>(
                state, PresentationWeaponAssetIndexOffset);
            const auto nativeOffhandWeaponAssetIndex = readValue<std::uint32_t>(
                state, OffhandWeaponAssetIndexOffset);
            const auto nativeCoKnifeStatsIndex = readValue<std::uint32_t>(
                state, CoKnifeStatsIndexOffset);
            const auto unk00E0 = readValue<std::uint32_t>(state, UnknownE0Offset);
            const auto legsAnim = readValue<std::uint32_t>(state, LegsAnimOffset);
            const auto torsoAnim = readValue<std::uint32_t>(state, TorsoAnimOffset);
            const auto positionTrajectoryType = readValue<std::uint32_t>(
                state, PositionTrajectoryTypeOffset);
            const auto positionTrajectoryTime = readValue<std::uint32_t>(
                state, PositionTrajectoryTimeOffset);
            const auto positionTrajectoryDuration = readValue<std::uint32_t>(
                state, PositionTrajectoryDurationOffset);
            const auto angleTrajectoryType = readValue<std::uint32_t>(
                state, AngleTrajectoryTypeOffset);
            const auto angleTrajectoryTime = readValue<std::uint32_t>(
                state, AngleTrajectoryTimeOffset);
            const auto angleTrajectoryDuration = readValue<std::uint32_t>(
                state, AngleTrajectoryDurationOffset);
            const auto movementDir = readValue<std::int32_t>(
                state, MovementDirOffset);
            const auto playerSizeScale = nativeEntityType == PlayerEntityType
                ? readValue<float>(state, PlayerSizeScaleOffset)
                : 0.0f;
            const auto groundEntityNum = readValue<std::uint32_t>(
                state, GroundEntityOffset);
            const auto clientNum = readValue<std::uint32_t>(state, ClientNumOffset);
            const auto unk00A0 = readValue<std::uint32_t>(state, UnknownA0Offset);
            const auto solid = readValue<std::uint32_t>(state, SolidOffset);
            const auto time2 = readValue<std::uint32_t>(state, Time2Offset);
            if (number > MaximumEntityNumber)
                return refuse("number", number);
            if (nativeEntityType > std::numeric_limits<std::uint8_t>::max())
                return refuse("eType", nativeEntityType);
            if (eFlags > MaximumEntityFlags)
                return refuse("eFlags", eFlags);
            if (nativeEventSequence > std::numeric_limits<std::uint8_t>::max())
                return refuse("eventSequence", nativeEventSequence);
            if (weaponAssetIndex > MaximumWeaponAssetIndex)
                return refuse("weaponAssetIndex", weaponAssetIndex);
            if (presentationWeaponAssetIndex > MaximumWeaponAssetIndex)
                return refuse("presentationWeaponAssetIndex", presentationWeaponAssetIndex);
            if (nativeOffhandWeaponAssetIndex >
                std::numeric_limits<std::uint16_t>::max())
            {
                return refuse("offhandWeaponAssetIndex", nativeOffhandWeaponAssetIndex);
            }
            if (nativeCoKnifeStatsIndex > std::numeric_limits<std::uint16_t>::max())
                return refuse("coKnifeStatsIndex", nativeCoKnifeStatsIndex);
            if (legsAnim > MaximumEntityAnimationIndex)
                return refuse("legsAnim", legsAnim);
            if (torsoAnim > MaximumEntityAnimationIndex)
                return refuse("torsoAnim", torsoAnim);
            if (positionTrajectoryType > std::numeric_limits<std::uint8_t>::max())
                return refuse("positionTrajectoryType", positionTrajectoryType);
            if (angleTrajectoryType > std::numeric_limits<std::uint8_t>::max())
                return refuse("angleTrajectoryType", angleTrajectoryType);
            if (movementDir < std::numeric_limits<std::int8_t>::min() ||
                movementDir > std::numeric_limits<std::int8_t>::max())
            {
                return refuse("movementDir", movementDir);
            }
            if (nativeEntityType == PlayerEntityType &&
                (!std::isfinite(playerSizeScale) || playerSizeScale < 0.0f))
            {
                return refuse(
                    "playerSizeScale",
                    static_cast<std::int64_t>(playerSizeScale * 1000.0f));
            }
            if (clientNum > 0x3F)
                return refuse("clientNum", clientNum);
            // 28 bits. At 0x1FFF this REFUSED THE WHOLE ENTITYSTATE PROJECTION the
            // moment the engine put a real value at +0xA4 -- a latent kill, not a
            // clamped field.
            if (unk00A0 > 0x0FFFFFFF)
                return refuse("unk00A0", unk00A0);
            if (solid > 0xFFFFFF)
                return refuse("solid", solid);
            // SEVEN BITS IS THE WHOLE FIELD. A wider value would be silently truncated on
            // the wire and decode as something else entirely on the client.
            if (time2 > MaximumTime2)
                return refuse("time2", time2);
            if (groundEntityNum > MaximumEntityNumber)
                return refuse("groundEntityNum", groundEntityNum);

            SvNativeEntityStateProjection result{
                .number = number,
                .eType = static_cast<std::uint8_t>(nativeEntityType),
                .clientNum = static_cast<std::uint8_t>(clientNum),
                .eFlags = eFlags,
                .playerSizeScale = playerSizeScale,
                .movementDir = movementDir,
                .positionTrajectoryType =
                    static_cast<std::uint8_t>(positionTrajectoryType),
                .positionTrajectoryTime = positionTrajectoryTime,
                .positionTrajectoryDuration = positionTrajectoryDuration,
                .angleTrajectoryType = static_cast<std::uint8_t>(angleTrajectoryType),
                .angleTrajectoryTime = angleTrajectoryTime,
                .angleTrajectoryDuration = angleTrajectoryDuration,
                .groundEntityNum = groundEntityNum,
                .unk00A0 = unk00A0,
                .time2 = static_cast<std::uint8_t>(time2),
                .solid = solid,
                .eventSequence = static_cast<std::uint8_t>(nativeEventSequence),
                .weaponAssetIndex = weaponAssetIndex,
                .presentationWeaponAssetIndex = presentationWeaponAssetIndex,
                .offhandWeaponAssetIndex = static_cast<std::uint16_t>(
                    nativeOffhandWeaponAssetIndex),
                .coKnifeStatsIndex = static_cast<std::uint16_t>(
                    nativeCoKnifeStatsIndex),
                .unk00E0 = unk00E0,
                .legsAnim = static_cast<std::uint16_t>(legsAnim),
                .torsoAnim = static_cast<std::uint16_t>(torsoAnim),
            };
            for (std::size_t index = 0; index < result.angles.size(); ++index)
            {
                result.angles[index] = readValue<float>(state, AngleOffsets[index]);
                result.positionTrajectoryDelta[index] = readValue<float>(
                    state, PositionTrajectoryDeltaOffsets[index]);
                result.angleTrajectoryDelta[index] = readValue<float>(
                    state, AngleTrajectoryDeltaOffsets[index]);
                if (originKeys)
                {
                    result.origin[index] = decodeSecureOrigin(
                        state, OriginOffsets[index], originKeys->values[index]);
                }
            }
            // FOUR VECTORS, AND WHICH ONE REFUSES IS THE WHOLE DIAGNOSIS. A bad origin
            // means a wrong decode key (S43h); a bad angle or trajectory delta means the
            // native converter wrote into a field this build moved. Print the vector, so
            // one cycle separates those instead of three.
            const auto finiteVector = [](const std::array<float, 3> &value) {
                return std::ranges::all_of(
                    value, [](const float part) { return std::isfinite(part); });
            };
            const auto reportVector = [&report](
                                          const char *const term,
                                          const std::array<float, 3> &value) {
                char text[128]{};
                std::snprintf(
                    text, sizeof(text), "%g,%g,%g", value[0], value[1], value[2]);
                return report(term, text);
            };
            if (originKeys && !finiteVector(result.origin))
                return reportVector("origin", result.origin);
            if (!finiteVector(result.angles))
                return reportVector("angles", result.angles);
            if (!finiteVector(result.positionTrajectoryDelta))
            {
                return reportVector(
                    "positionTrajectoryDelta", result.positionTrajectoryDelta);
            }
            if (!finiteVector(result.angleTrajectoryDelta))
                return reportVector("angleTrajectoryDelta", result.angleTrajectoryDelta);
            for (std::size_t index = 0; index < result.events.size(); ++index)
            {
                result.events[index] = readValue<SvEntityEvent>(
                    state,
                    EventsOffset + index * sizeof(SvEntityEvent));
                // THE BOUND IS A BYTE, NOT THE WIDTH TABLE'S LENGTH. This refused
                // `event=1:180` on a live client -- against SvEntityEventCount, which
                // was 3.3.3.3's 162 and is 170 here. Codec -94 writes the id as a raw
                // byte, and the client's own decoder answers an id past the width table
                // with a zero-width parameter instead of refusing, so refusing here made
                // this server stricter than the game it is speaking to and blocked the
                // player's entityState outright. Print the SLOT as well as the value:
                // 0xD0 is this build's third event slot, so which slot matters.
                if (result.events[index].event < 0 ||
                    result.events[index].event > SvMaximumEntityEventId)
                {
                    return report(
                        "event",
                        std::to_string(index) + ":" +
                            std::to_string(result.events[index].event));
                }
            }
            return result;
        }
    }

    SvNativeEntityState::SvNativeEntityState(
        const SvNativeEntityState &other)
    {
        *this = other;
    }

    SvNativeEntityState::SvNativeEntityState(
        SvNativeEntityState &&other) noexcept
    {
        *this = other;
    }

    SvNativeEntityState &SvNativeEntityState::operator=(
        const SvNativeEntityState &other)
    {
        if (this == &other)
            return *this;
        bytes = other.bytes;
        secureOriginAddressBound = other.secureOriginAddressBound;
        relocateSecureOriginWords(*this, other);
        return *this;
    }

    SvNativeEntityState &SvNativeEntityState::operator=(
        SvNativeEntityState &&other) noexcept
    {
        return *this = static_cast<const SvNativeEntityState &>(other);
    }

    bool SV_SetNativeEntityStateSolid(
        SvNativeEntityState &state,
        const std::uint32_t solid)
    {
        if (solid > 0xFFFFFF)
            return false;
        writeValue(state, SolidOffset, solid);
        return true;
    }

    bool SV_SetNativeEntityStateModelIndex(
        SvNativeEntityState &state,
        const std::uint16_t modelIndex)
    {
        if (modelIndex > 0xFFF)
            return false;
        writeValue(state, ModelIndexOffset, modelIndex);
        return true;
    }

    bool SV_SetNativeEntityStatePlayerSizeScale(
        SvNativeEntityState &state,
        const float playerSizeScale)
    {
        if (!std::isfinite(playerSizeScale) || playerSizeScale < 0.0f)
            return false;
        writeValue(state, PlayerSizeScaleOffset, playerSizeScale);
        return true;
    }

    bool SV_SetNativeEntityStateUnknownA0(
        SvNativeEntityState &state,
        const std::uint32_t value)
    {
        // The FOURTH copy of this bound, and the last. 28 bits, not 3.3.3.3's
        // 13 -- and the uint16_t parameter silently truncated anything wider
        // before the check even ran.
        if (value > 0x0FFFFFFF)
            return false;
        writeValue(state, UnknownA0Offset, value);
        return true;
    }

    void SV_MarkNativeEntityStateSecureOriginBound(
        SvNativeEntityState &state)
    {
        state.secureOriginAddressBound = true;
    }

    void SV_ResetNativeEntityState(
        SvNativeEntityState &state,
        const std::uint32_t number,
        const std::uint8_t eType,
        const std::uint32_t eFlags,
        const std::uint16_t weaponAssetIndex)
    {
        state = {};
        writeValue(state, NumberOffset, number);
        writeValue(state, EntityTypeOffset, static_cast<std::uint32_t>(eType));
        if (eType == 1 && number <= 0x3F)
            writeValue(state, ClientNumOffset, number);
        writeValue(state, EntityFlagsOffset, eFlags);
        writeValue(
            state,
            WeaponAssetIndexOffset,
            weaponAssetIndex);
        // CODDIFF(bg_player_to_entity_set_misc): CODOL 0x004131A0 writes the
        // current weapon to +0xD0, then normally mirrors it to the presentation
        // selector at +0xD2. For WeaponDef +0x488 (decimal 1160) value 3 it
        // instead takes playerState +0x344. This reset helper has no WeaponDef
        // or complete playerState context, so equality is only the ordinary
        // loadout bootstrap. The retained native conversion must replace it
        // before special/alternate weapon presentation is considered restored.
        // TODO(CODOL): expose the typed +0x344 owner and special WeaponDef
        // classification, then remove this bootstrap equality from any state
        // that can reach a client before BG_PlayerStateToEntityState runs.
        writeValue(
            state,
            PresentationWeaponAssetIndexOffset,
            weaponAssetIndex);
    }

    std::optional<SvNativeEntityStateProjection> SV_ReadNativeEntityState(
        const SvNativeEntityState &state)
    {
        return readProjection(state, nullptr);
    }

    std::optional<SvNativeEntityStateProjection> SV_ReadNativeEntityState(
        const SvNativeEntityState &state,
        const SvEntityOriginKeys &originKeys)
    {
        return readProjection(state, &originKeys);
    }
}
