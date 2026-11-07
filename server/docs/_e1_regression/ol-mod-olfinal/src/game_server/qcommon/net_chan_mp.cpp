#include "net_chan_mp.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <limits>
#include <optional>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::array<std::uint8_t, 4> OobPrefix{ 0xFF, 0xFF, 0xFF, 0xFF };
        constexpr std::size_t ClientHeaderSize = 13;

        std::uint32_t readU32(const std::span<const std::uint8_t> data, const std::size_t offset)
        {
            return static_cast<std::uint32_t>(data[offset]) |
                static_cast<std::uint32_t>(data[offset + 1]) << 8 |
                static_cast<std::uint32_t>(data[offset + 2]) << 16 |
                static_cast<std::uint32_t>(data[offset + 3]) << 24;
        }

        void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
        {
            output.push_back(static_cast<std::uint8_t>(value));
            output.push_back(static_cast<std::uint8_t>(value >> 8));
            output.push_back(static_cast<std::uint8_t>(value >> 16));
            output.push_back(static_cast<std::uint8_t>(value >> 24));
        }

        class ClientCommandReader
        {
        public:
            explicit ClientCommandReader(const std::span<const std::uint8_t> data)
                : data_(data)
            {
            }

            std::optional<std::uint32_t> readBits(const std::uint32_t count)
            {
                if (count > 32)
                    return std::nullopt;
                std::uint32_t value{};
                for (std::uint32_t index = 0; index < count; ++index)
                {
                    auto bitInByte = bit_ & 7u;
                    if (!bitInByte)
                    {
                        if (readCount_ >= data_.size())
                            return std::nullopt;
                        bit_ = readCount_++ * 8u;
                        bitInByte = 0;
                    }
                    value |= ((data_[bit_ / 8u] >> bitInByte) & 1u) << index;
                    ++bit_;
                }
                return value;
            }

            std::optional<std::uint8_t> readByte()
            {
                if (readCount_ >= data_.size())
                    return std::nullopt;
                return data_[readCount_++];
            }

            std::optional<std::uint32_t> readLong()
            {
                if (data_.size() - readCount_ < sizeof(std::uint32_t))
                    return std::nullopt;
                const auto value = readU32(data_, readCount_);
                readCount_ += sizeof(std::uint32_t);
                return value;
            }

            std::optional<std::uint16_t> readShort()
            {
                if (data_.size() - readCount_ < sizeof(std::uint16_t))
                    return std::nullopt;
                const auto value = static_cast<std::uint16_t>(data_[readCount_]) |
                    static_cast<std::uint16_t>(data_[readCount_ + 1]) << 8;
                readCount_ += sizeof(std::uint16_t);
                return value;
            }

            std::optional<std::string> readString(const std::size_t capacity)
            {
                const auto terminator = std::find(
                    data_.begin() + static_cast<std::ptrdiff_t>(readCount_),
                    data_.end(),
                    0);
                if (terminator == data_.end())
                    return std::nullopt;
                const auto size = static_cast<std::size_t>(
                    terminator - data_.begin()) - readCount_;
                if (size >= capacity)
                    return std::nullopt;
                std::string value(
                    reinterpret_cast<const char *>(data_.data() + readCount_), size);
                readCount_ += size + 1;
                return value;
            }

            // For diagnostics only: where the bit cursor stands, so a rejected usercmd
            // can be lined up against the raw bytes by hand.
            [[nodiscard]] std::size_t consumedBits() const { return bit_; }

        private:
            std::span<const std::uint8_t> data_;
            std::size_t readCount_{};
            std::size_t bit_{};
        };

        struct ParsedClientCommands
        {
            ClientCommandKind terminal{ ClientCommandKind::Invalid };
            std::uint32_t moveCommandCount{};
            std::vector<ClientReliableCommand> reliableCommands;
            std::vector<UserCmd> userCommands;
            ClientPredictedState predictedState;
            std::uint32_t rejectedCommandTime{};
            std::uint32_t rejectedCommandBaselineTime{};
            std::string reason;
        };

        std::uint32_t bitMask(const std::uint32_t bits)
        {
            return bits == 32 ? std::numeric_limits<std::uint32_t>::max() :
                (1u << bits) - 1u;
        }

        std::optional<std::uint32_t> readKey(
            ClientCommandReader &reader,
            const std::uint32_t key,
            const std::uint32_t bits)
        {
            const auto encoded = reader.readBits(bits);
            if (!encoded)
                return std::nullopt;
            return *encoded ^ (key & bitMask(bits));
        }

        template <typename ReadValue>
        bool readDelta(
            ClientCommandReader &reader,
            const std::uint32_t key,
            const std::uint32_t bits,
            const std::uint32_t baseline,
            std::uint32_t &value,
            ReadValue readValue)
        {
            const auto changed = reader.readBits(1);
            if (!changed)
                return false;
            if (!*changed)
            {
                value = baseline;
                return true;
            }
            const auto encoded = readValue();
            if (!encoded)
                return false;
            value = static_cast<std::uint32_t>(*encoded) ^ (key & bitMask(bits));
            return true;
        }

        std::uint8_t movementMask(const UserCmd &command)
        {
            std::uint8_t result{};
            if (command.forwardMove > 10)
                result |= 1;
            else if (command.forwardMove < -10)
                result |= 2;
            if (command.rightMove > 10)
                result |= 4;
            else if (command.rightMove < -10)
                result |= 8;
            return result;
        }

        void setMovementMask(UserCmd &command, const std::uint8_t mask)
        {
            command.forwardMove = mask & 1 ? 127 : mask & 2 ? -127 : 0;
            command.rightMove = mask & 4 ? 127 : mask & 8 ? -127 : 0;
        }

        // WHAT THE DECODER SAW, SO A REJECTION CAN BE REPLAYED OFFLINE.
        // The usercmd reader survives hundreds of commands and then desyncs, which means a
        // width or a gate is wrong on a field the IDLE path never exercises -- it only shows
        // once a player is spawned and pressing things. A rejection reason names the last
        // check to fail, never the field that consumed the wrong number of bits, and those
        // are different fields by construction: the trailer is simply where the damage
        // becomes visible.
        //
        // So record the branch taken and every conditional gate, and let the caller print it
        // beside the raw bits. Then the desync can be found by hand against the bit stream
        // instead of by another cycle per guess.
        struct UserCmdTrace
        {
            std::uint32_t deltaTime{};
            std::uint32_t changed{};
            std::uint32_t full{};
            std::uint32_t buttons{};
            bool selectedLocation{};
            bool selectedDirection{};
            bool conditional{};
            std::size_t bitsAtTrailer{};
        };

        bool readDeltaUserCmd(
            ClientCommandReader &reader,
            const std::uint32_t key,
            const UserCmd &baseline,
            UserCmd &command,
            std::string &reason,
            UserCmdTrace *const trace = nullptr)
        {
            command = baseline;
            const auto deltaTime = reader.readBits(1);
            if (!deltaTime)
            {
                reason = "client usercmd omits its command time encoding";
                return false;
            }
            if (trace)
                trace->deltaTime = *deltaTime;
            if (*deltaTime)
            {
                const auto delta = reader.readByte();
                if (!delta)
                {
                    reason = "client usercmd has a truncated command time delta";
                    return false;
                }
                command.commandTime = baseline.commandTime + *delta;
            }
            else
            {
                const auto absolute = reader.readLong();
                if (!absolute)
                {
                    reason = "client usercmd has a truncated absolute command time";
                    return false;
                }
                command.commandTime = *absolute;
            }

            const auto changed = readKey(reader, key, 1);
            if (!changed)
            {
                reason = "client usercmd omits its delta branch";
                return false;
            }
            if (trace)
                trace->changed = *changed;
            if (!*changed)
            {
                const auto trailer = reader.readBits(3);
                if (!trailer || *trailer != 7)
                {
                    reason = "client usercmd has an invalid unchanged trailer";
                    return false;
                }
                return true;
            }

            const auto full = readKey(reader, key, 1);
            if (!full)
            {
                reason = "client usercmd omits its full-delta flag";
                return false;
            }
            if (trace)
                trace->full = *full;
            const auto fieldKey = *full ? key : command.commandTime ^ key;
            const auto attack = readKey(reader, fieldKey, 1);
            if (!attack)
            {
                reason = "client usercmd omits its primary button";
                return false;
            }
            command.buttons = (command.buttons & ~1u) | (*attack & 1u);

            const auto readShort = [&reader]() { return reader.readShort(); };
            const auto readByte = [&reader]() { return reader.readByte(); };
            const auto readBits = [&reader](const std::uint32_t bits) {
                return reader.readBits(bits);
            };
            std::uint32_t value{};
            for (std::size_t index = 0; index < 2; ++index)
            {
                if (!readDelta(
                        reader, fieldKey, 16, baseline.angles[index], value, readShort))
                {
                    reason = "client usercmd has a truncated view-angle delta";
                    return false;
                }
                command.angles[index] = static_cast<std::uint16_t>(value);
            }
            if (!readDelta(
                    reader,
                    fieldKey,
                    4,
                    movementMask(baseline),
                    value,
                    [&]() { return readBits(4); }))
            {
                reason = "client usercmd has a truncated movement delta";
                return false;
            }
            setMovementMask(command, static_cast<std::uint8_t>(value));

            const auto expectedTrailer = *full ? 5u : 2u;
            if (!*full)
            {
                const auto trailer = reader.readBits(3);
                if (!trailer || *trailer != expectedTrailer)
                {
                    reason = "client usercmd has an invalid partial-delta trailer";
                    return false;
                }
                return true;
            }

            const auto extendedKey = command.commandTime ^ key;
            if (!readDelta(
                    reader, extendedKey, 16, baseline.angles[2], value, readShort))
            {
                reason = "client usercmd has a truncated roll-angle delta";
                return false;
            }
            command.angles[2] = static_cast<std::uint16_t>(value);
            if (!readDelta(
                    reader,
                    extendedKey,
                    29,
                    baseline.buttons >> 1,
                    value,
                    [&]() { return readBits(29); }))
            {
                reason = "client usercmd has a truncated button delta";
                return false;
            }
            command.buttons = (value << 1) | (command.buttons & 1u);
            if (trace)
                trace->buttons = command.buttons;

            // CODDIFF(1649370): THESE ARE WEAPON INDICES AND THEY ARE ELEVEN BITS HERE.
            // sv_gamestate_mp.cpp already carries the derivation -- "the weapon block grew
            // 900 -> 1700 entries, so the weapon index widened 10 -> 11", WeaponIndexBits =
            // 11 -- and this decoder is 3.3.3.3's verbatim, still reading ten.
            //
            // It fails exactly the way a one-bit-per-field shortfall must. A delta field
            // costs nothing while it is UNCHANGED, so an idle client parses perfectly: the
            // log shows hundreds of clean commands. The moment a player spawns and holds a
            // weapon the field starts changing, three fields read one bit short each, and
            // the stream slips. The reported failure is always the trailer, which is merely
            // where the damage becomes visible -- the trace shows buttons decoding to
            // 0x146574C3 and gates opening at random by then.
            constexpr std::uint32_t UserCmdWeaponIndexBits = 11;
            const std::array weaponIndexFields{
                std::pair{ &command.weapon, baseline.weapon },
                std::pair{
                    &command.lastWeaponAltModeSwitch,
                    baseline.lastWeaponAltModeSwitch },
                std::pair{ &command.offHandIndex, baseline.offHandIndex },
            };
            for (const auto [field, baselineField] : weaponIndexFields)
            {
                if (!readDelta(
                        reader,
                        extendedKey,
                        UserCmdWeaponIndexBits,
                        baselineField,
                        value,
                        [&]() { return readBits(UserCmdWeaponIndexBits); }))
                {
                    reason = "client usercmd has a truncated weapon-index field delta";
                    return false;
                }
                *field = static_cast<std::uint16_t>(value);
            }
            if (trace)
            {
                trace->selectedLocation = (command.buttons & 0x20000u) != 0;
                trace->selectedDirection = (command.buttons & 0x200000u) != 0;
                trace->conditional = (command.buttons & 4u) != 0;
            }
            if (command.buttons & 0x20000u)
            {
                for (std::size_t index = 0; index < command.selectedLocation.size(); ++index)
                {
                    if (!readDelta(
                            reader,
                            extendedKey,
                            8,
                            baseline.selectedLocation[index],
                            value,
                            readByte))
                    {
                        reason = "client usercmd has a truncated selected-location delta";
                        return false;
                    }
                    command.selectedLocation[index] = static_cast<std::uint8_t>(value);
                }
            }
            if (command.buttons & 0x200000u)
            {
                for (std::size_t index = 0; index < command.selectedDirection.size(); ++index)
                {
                    if (!readDelta(
                            reader,
                            extendedKey,
                            8,
                            baseline.selectedDirection[index],
                            value,
                            readByte))
                    {
                        reason = "client usercmd has a truncated selected-direction delta";
                        return false;
                    }
                    command.selectedDirection[index] = static_cast<std::uint8_t>(value);
                }
            }
            if (command.buttons & 4u)
            {
                const auto baselineAngle = static_cast<std::uint16_t>(
                    static_cast<std::int16_t>(baseline.conditionalAngle * 182.0444488525391f));
                if (!readDelta(
                        reader, extendedKey, 16, baselineAngle, value, readShort))
                {
                    reason = "client usercmd has a truncated conditional angle delta";
                    return false;
                }
                command.conditionalAngle = static_cast<float>(
                    static_cast<std::int16_t>(value)) * 0.0054931640625f;
                if (!readDelta(
                        reader,
                        extendedKey,
                        8,
                        baseline.conditionalByte,
                        value,
                        [&]() { return readBits(8); }))
                {
                    reason = "client usercmd has a truncated conditional byte delta";
                    return false;
                }
                command.conditionalByte = static_cast<std::uint8_t>(value);
                if (!readDelta(
                        reader,
                        extendedKey,
                        11,
                        baseline.conditionalElevenBits,
                        value,
                        [&]() { return readBits(11); }))
                {
                    reason = "client usercmd has a truncated conditional 11-bit delta";
                    return false;
                }
                command.conditionalElevenBits = static_cast<std::uint16_t>(value);
            }
            if (trace)
                trace->bitsAtTrailer = reader.consumedBits();
            const auto trailer = reader.readBits(3);
            if (!trailer || *trailer != expectedTrailer)
            {
                reason = "client usercmd has an invalid full-delta trailer";
                return false;
            }
            return true;
        }

        ParsedClientCommands parseClientCommands(
            const std::span<const std::uint8_t> commands,
            const std::uint32_t userCmdKey,
            const UserCmd &defaultUserCmd)
        {
            constexpr std::size_t MaxReliableCommandsPerPacket = 256;
            constexpr std::size_t MaxReliableCommandLength = 1024;
            ClientCommandReader reader(commands);
            ParsedClientCommands result;
            while (true)
            {
                const auto terminal = reader.readBits(3);
                if (!terminal)
                {
                    result.reason = "client command stream ended before its terminal";
                    return result;
                }
                if (*terminal == ClientCommandReliable)
                {
                    if (result.reliableCommands.size() >= MaxReliableCommandsPerPacket)
                    {
                        result.reason = "client command stream exceeds the reliable command limit";
                        return result;
                    }
                    const auto sequence = reader.readLong();
                    auto command = reader.readString(MaxReliableCommandLength);
                    if (!sequence || !command)
                    {
                        result.reason = "client reliable command is truncated";
                        return result;
                    }
                    result.reliableCommands.push_back({
                        .sequence = *sequence,
                        .command = std::move(*command),
                    });
                    continue;
                }
                if (*terminal > ClientCommandEof)
                {
                    result.reason = "client command stream has an unknown terminal";
                    return result;
                }
                result.terminal = static_cast<ClientCommandKind>(*terminal);
                if (result.terminal == ClientCommandKind::MoveDelta ||
                    result.terminal == ClientCommandKind::MoveNoDelta)
                {
                    const auto commandCount = reader.readByte();
                    if (!commandCount)
                    {
                        result.terminal = ClientCommandKind::Invalid;
                        result.reason = "client move command omits its command count";
                        return result;
                    }
                    result.moveCommandCount = *commandCount;
                    if (!result.moveCommandCount || result.moveCommandCount > 32)
                    {
                        result.terminal = ClientCommandKind::Invalid;
                        result.reason = "client move command count is outside 1..32";
                        return result;
                    }
                    // THE CHAIN START IS THE ACKNOWLEDGED PLAYERSTATE BASELINE.
                    //
                    // CODREF(cl_write_packet): OLFinal 1649370 CL_WritePacket
                    // 0x005B2C10 calls MSG_SetDefaultUserCmd 0x0066F170 once before
                    // choosing clc_move/clc_moveNoDelta, stores that local command as
                    // the first baseline, then advances the baseline only inside the
                    // packet's MSG_WriteDeltaUsercmdKey loop. It never starts a packet
                    // from the previous packet's usercmd.
                    //
                    // The previous-command override was fatal during Wetwork's turret
                    // intro. It retained button 0x4 across the packet boundary, so this
                    // reader entered the optional 35-bit conditional block even though
                    // the client had encoded against a zeroed default and omitted it.
                    // Every spawned-player packet then failed at the trailer and no
                    // mouse input reached pmove.
                    auto baseline = defaultUserCmd;
                    result.userCommands.reserve(result.moveCommandCount);
                    for (std::uint32_t index = 0; index < result.moveCommandCount; ++index)
                    {
                        UserCmd command;
                        UserCmdTrace trace{};
                        if (!readDeltaUserCmd(
                                reader, userCmdKey, baseline, command,
                                result.reason, &trace))
                        {
                            // Say what the decoder BELIEVED before it failed. The reason
                            // names the last check; the fault is upstream of it, in whatever
                            // consumed the wrong number of bits. The gates are what matter:
                            // three conditional blocks hang off button bits 0x20000,
                            // 0x200000 and 0x4, and each of them only ever fires once a
                            // player is spawned and pressing things -- which is exactly the
                            // moment this decoder started failing after hundreds of clean
                            // commands.
                            result.reason += " [buttons=0x" + [&] {
                                char hex[16]{};
                                std::snprintf(hex, sizeof(hex), "%08X", trace.buttons);
                                return std::string(hex);
                            }() +
                                " deltaTime=" + std::to_string(trace.deltaTime) +
                                " changed=" + std::to_string(trace.changed) +
                                " full=" + std::to_string(trace.full) +
                                " gates=" + (trace.selectedLocation ? "L" : "-") +
                                (trace.selectedDirection ? "D" : "-") +
                                (trace.conditional ? "C" : "-") +
                                " bitsAtTrailer=" + std::to_string(trace.bitsAtTrailer) +
                                "]";
                            result.terminal = ClientCommandKind::Invalid;
                            return result;
                        }
                        // COD's SV_UserMove still accepts the packet when a
                        // client repeats an old command in its move window.
                        // Server-side command watermarks discard it after
                        // netchan state and ACKs have advanced. Rejecting the
                        // whole packet would make the client retransmit the
                        // same window forever.
                        result.userCommands.push_back(command);
                        baseline = command;
                    }
                    for (auto &predictedValue : result.predictedState.values)
                    {
                        const auto value = reader.readLong();
                        if (!value)
                        {
                            result.terminal = ClientCommandKind::Invalid;
                            result.reason = "client move command has truncated predicted state";
                            return result;
                        }
                        predictedValue = *value;
                    }
                    const auto eof = reader.readBits(3);
                    if (!eof || *eof != ClientCommandEof)
                    {
                        result.terminal = ClientCommandKind::Invalid;
                        result.reason = "client move command is not followed by EOF";
                        return result;
                    }
                }
                return result;
            }
        }
    }

    bool NET_IsConnectionlessPacket(const std::span<const std::uint8_t> packet)
    {
        return packet.size() >= OobPrefix.size() &&
            std::equal(OobPrefix.begin(), OobPrefix.end(), packet.begin());
    }

    std::vector<std::uint8_t> Netchan_XorCommands(
        const std::span<const std::uint8_t> payload,
        const std::uint32_t seed,
        const std::string_view reliableCommand)
    {
        auto key = static_cast<std::uint8_t>(seed);
        std::size_t commandIndex{};
        std::vector<std::uint8_t> result;
        result.reserve(payload.size());
        for (std::size_t index = 0; index < payload.size(); ++index)
        {
            std::uint8_t commandByte{};
            if (!reliableCommand.empty())
            {
                if (commandIndex >= reliableCommand.size() || !reliableCommand[commandIndex])
                    commandIndex = 0;
                commandByte = static_cast<std::uint8_t>(reliableCommand[commandIndex++]);
            }
            key ^= static_cast<std::uint8_t>(commandByte << (index & 1));
            result.push_back(payload[index] ^ key);
        }
        return result;
    }

    std::uint32_t Com_HashKey(const std::string_view value, const std::size_t maxLength)
    {
        std::int32_t hash{};
        const auto length = std::min(value.size(), maxLength);
        for (std::size_t index = 0; index < length && value[index]; ++index)
        {
            hash += static_cast<std::int8_t>(value[index]) *
                static_cast<std::int32_t>(119 + index);
        }
        const auto unsignedHash = static_cast<std::uint32_t>(hash);
        return unsignedHash ^ ((unsignedHash ^ (unsignedHash >> 10)) >> 10);
    }

    NetchanProcessResult Netchan_Process(
        NetchanState &chan,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t challenge,
        const std::uint32_t checksumFeed,
        const std::string_view serverReliableCommand,
        const UserCmd &defaultUserCmd,
        const NetchanReliableCommandResolver &reliableCommandResolver,
        const NetchanDefaultUserCmdResolver &defaultUserCmdResolver)
    {
        // Two very different refusals wore one message, which cost a cycle: the dispatcher in
        // sv_main_mp.cpp already routes out-of-band packets to SV_ConnectionlessPacket before
        // this, so reaching here with an OOB packet would be a ROUTING bug, while a short packet
        // is just a short packet. Name which, and how big.
        if (packet.size() < 5)
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .reason = "netchan packet too short: " +
                    std::to_string(packet.size()) + " bytes, minimum 5",
            };
        }
        if (NET_IsConnectionlessPacket(packet))
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .reason = "out-of-band packet reached the netchan path (" +
                    std::to_string(packet.size()) + " bytes) -- the dispatcher should have "
                    "sent this to SV_ConnectionlessPacket",
            };
        }

        // CODREF(netchan_fragment): CODOL 0x005A5960 uses sequence flags
        // 0x80000000 fragmented, 0x40000000 reliable and 0x20000000 fragment
        // acknowledgement. Its fragment header is index, last-index,
        // 1154-byte stride and payload length; it is not the older
        // qport/start/length layout.
        std::vector<std::uint8_t> reassembled;
        std::vector<std::uint8_t> fragmentControlReply;
        auto effectivePacket = packet;
        const auto rawSequence = readU32(packet, 0);
        if ((rawSequence & 0x80000000u) != 0)
        {
            constexpr std::size_t FragmentHeaderSize = 10;
            if (packet.size() < FragmentHeaderSize)
            {
                return {
                    .kind = NetchanProcessKind::Rejected,
                    .reason = "truncated CODOL client netchan fragment header",
                };
            }
            const auto sequence = rawSequence & NetchanSequenceMask;
            const auto reliable = (rawSequence & 0x40000000u) != 0;
            const auto acknowledgement = (rawSequence & 0x20000000u) != 0;
            const auto fragmentIndex = packet[4];
            const auto lastFragmentIndex = packet[5];
            const auto fragmentStride = static_cast<std::uint16_t>(
                static_cast<std::uint16_t>(packet[6]) |
                static_cast<std::uint16_t>(packet[7]) << 8);
            const auto fragmentLength = static_cast<std::uint16_t>(
                static_cast<std::uint16_t>(packet[8]) |
                static_cast<std::uint16_t>(packet[9]) << 8);

            if (acknowledgement)
            {
                if (packet.size() < FragmentHeaderSize + 16 || reliable ||
                    fragmentStride != NetchanFragmentSize ||
                    sequence != chan.outgoingSequence)
                {
                    return {
                        .kind = NetchanProcessKind::Rejected,
                        .packet = { .sequence = sequence },
                        .reason = "invalid CODOL fragment acknowledgement",
                    };
                }
                for (std::size_t index = 0;
                     index < chan.fragmentAcknowledgements.size(); ++index)
                {
                    chan.fragmentAcknowledgements[index] |= readU32(
                        packet, FragmentHeaderSize + index * sizeof(std::uint32_t));
                }
                return {
                    .kind = NetchanProcessKind::FragmentAcknowledgement,
                    .packet = { .sequence = sequence },
                    .reason = "CODOL fragment acknowledgement consumed",
                };
            }

            if (!sequence || fragmentIndex > lastFragmentIndex ||
                lastFragmentIndex >= NetchanMaximumFragments ||
                fragmentStride != NetchanFragmentSize ||
                fragmentLength > fragmentStride ||
                packet.size() < FragmentHeaderSize + fragmentLength ||
                (fragmentIndex != lastFragmentIndex &&
                    fragmentLength != fragmentStride))
            {
                return {
                    .kind = NetchanProcessKind::Rejected,
                    .reason = "invalid CODOL client netchan fragment bounds",
                };
            }
            if (chan.incomingSequenceReceived && sequence <= chan.incomingSequence)
            {
                std::vector<std::uint8_t> controlReply;
                if (reliable && sequence == chan.incomingSequence)
                {
                    appendU32(controlReply, sequence | 0xA0000000u);
                    controlReply.push_back(fragmentIndex);
                    controlReply.push_back(lastFragmentIndex);
                    controlReply.push_back(static_cast<std::uint8_t>(fragmentStride));
                    controlReply.push_back(static_cast<std::uint8_t>(fragmentStride >> 8));
                    controlReply.push_back(static_cast<std::uint8_t>(fragmentLength));
                    controlReply.push_back(static_cast<std::uint8_t>(fragmentLength >> 8));
                    for (std::size_t index = 0; index < 4; ++index)
                        appendU32(controlReply, std::numeric_limits<std::uint32_t>::max());
                }
                return {
                    .kind = controlReply.empty()
                        ? NetchanProcessKind::Duplicate
                        : NetchanProcessKind::FragmentPending,
                    .packet = { .sequence = sequence },
                    .controlReply = std::move(controlReply),
                    .reason = "duplicate or out-of-order CODOL client netchan fragment",
                };
            }
            if (sequence != chan.fragmentSequence)
            {
                chan.fragmentSequence = sequence;
                chan.fragmentLength = 0;
                chan.fragmentStride = fragmentStride;
                chan.lastFragmentIndex = lastFragmentIndex;
                chan.receivedFragmentBits.fill(0);
                chan.fragmentBuffer.assign(
                    (static_cast<std::size_t>(lastFragmentIndex) + 1) *
                        fragmentStride,
                    0);
            }
            if (chan.fragmentStride != fragmentStride ||
                chan.lastFragmentIndex != lastFragmentIndex ||
                chan.fragmentBuffer.size() > NetchanMaximumFragmentedMessage)
            {
                return {
                    .kind = NetchanProcessKind::Rejected,
                    .packet = { .sequence = sequence },
                    .reason = "CODOL client netchan fragmented message is too large",
                };
            }
            const auto fragmentMask = 1u << (fragmentIndex & 31u);
            auto &fragmentWord = chan.receivedFragmentBits[fragmentIndex >> 5u];
            if ((fragmentWord & fragmentMask) == 0)
            {
                const auto fragmentStart =
                    static_cast<std::size_t>(fragmentIndex) * fragmentStride;
                std::copy_n(
                    packet.begin() + FragmentHeaderSize,
                    fragmentLength,
                    chan.fragmentBuffer.begin() + fragmentStart);
                fragmentWord |= fragmentMask;
                chan.fragmentLength += fragmentLength;
            }

            if (reliable)
            {
                appendU32(fragmentControlReply, sequence | 0xA0000000u);
                fragmentControlReply.push_back(fragmentIndex);
                fragmentControlReply.push_back(lastFragmentIndex);
                fragmentControlReply.push_back(static_cast<std::uint8_t>(fragmentStride));
                fragmentControlReply.push_back(static_cast<std::uint8_t>(fragmentStride >> 8));
                fragmentControlReply.push_back(static_cast<std::uint8_t>(fragmentLength));
                fragmentControlReply.push_back(static_cast<std::uint8_t>(fragmentLength >> 8));
                for (const auto acknowledgementWord : chan.receivedFragmentBits)
                    appendU32(fragmentControlReply, acknowledgementWord);
            }

            bool complete = true;
            for (std::uint32_t index = 0; index <= lastFragmentIndex; ++index)
            {
                complete &= (chan.receivedFragmentBits[index >> 5u] &
                    (1u << (index & 31u))) != 0;
            }
            if (!complete)
            {
                return {
                    .kind = NetchanProcessKind::FragmentPending,
                    .packet = { .sequence = sequence },
                    .controlReply = std::move(fragmentControlReply),
                    .reason = "CODOL client netchan fragment buffered",
                };
            }
            reassembled.reserve(4 + chan.fragmentLength);
            appendU32(reassembled, sequence);
            reassembled.insert(
                reassembled.end(),
                chan.fragmentBuffer.begin(),
                chan.fragmentBuffer.begin() + chan.fragmentLength);
            chan.fragmentBuffer.clear();
            chan.fragmentLength = 0;
            chan.receivedFragmentBits.fill(0);
            effectivePacket = reassembled;
        }

        if (effectivePacket.size() < ClientHeaderSize + 1)
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .controlReply = std::move(fragmentControlReply),
                .reason = "CODOL client netchan payload is shorter than its header",
            };
        }

        ClientNetchanPacket parsed{
            .sequence = readU32(effectivePacket, 0),
            .serverId = effectivePacket[4],
            .messageAcknowledge = readU32(effectivePacket, 5),
            .reliableAcknowledge = readU32(effectivePacket, 9),
            .encodedCommands = effectivePacket.subspan(ClientHeaderSize),
        };
        if (!parsed.sequence || parsed.sequence > NetchanSequenceMask)
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .packet = parsed,
                .controlReply = std::move(fragmentControlReply),
                .reason = "fragmented or invalid CODOL client netchan sequence",
            };
        }
        if (parsed.messageAcknowledge > NetchanSequenceMask)
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .packet = parsed,
                .controlReply = std::move(fragmentControlReply),
                .reason = "client message acknowledge is outside the netchan sequence range",
            };
        }
        if (chan.incomingSequenceReceived && parsed.sequence <= chan.incomingSequence)
        {
            return {
                .kind = NetchanProcessKind::Duplicate,
                .packet = parsed,
                .controlReply = std::move(fragmentControlReply),
                .reason = "duplicate or out-of-order CODOL client netchan sequence",
            };
        }

        std::string resolvedServerReliableCommand(serverReliableCommand);
        if (reliableCommandResolver)
        {
            auto resolved = reliableCommandResolver(parsed.reliableAcknowledge);
            if (!resolved)
            {
                return {
                    .kind = NetchanProcessKind::Rejected,
                    .packet = parsed,
                    .controlReply = std::move(fragmentControlReply),
                    .reason = "client reliable acknowledge exceeds the server sequence",
                };
            }
            resolvedServerReliableCommand = std::move(*resolved);
        }
        const auto resolvedDefaultUserCmd = defaultUserCmdResolver
            ? defaultUserCmdResolver(parsed.messageAcknowledge)
            : defaultUserCmd;

        auto decoded = Netchan_XorCommands(
            parsed.encodedCommands,
            challenge ^ parsed.serverId ^ parsed.messageAcknowledge,
            resolvedServerReliableCommand);
        const auto userCmdKey = checksumFeed ^ parsed.messageAcknowledge ^
            Com_HashKey(resolvedServerReliableCommand);
        auto commands = parseClientCommands(
            decoded, userCmdKey, resolvedDefaultUserCmd);
        if (commands.terminal == ClientCommandKind::Invalid)
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .packet = parsed,
                .userCmdKey = userCmdKey,
                .decodedCommands = std::move(decoded),
                .reliableCommands = std::move(commands.reliableCommands),
                .userCommands = std::move(commands.userCommands),
                .predictedState = commands.predictedState,
                .terminalCommand = commands.terminal,
                .moveCommandCount = commands.moveCommandCount,
                .rejectedCommandTime = commands.rejectedCommandTime,
                .rejectedCommandBaselineTime = commands.rejectedCommandBaselineTime,
                .controlReply = std::move(fragmentControlReply),
                .reason = std::move(commands.reason),
            };
        }

        auto lastClientReliableSequence = chan.lastClientReliableSequence;
        auto lastClientReliableCommand = chan.lastClientReliableCommand;
        std::vector<ClientReliableCommand> newReliableCommands;
        newReliableCommands.reserve(commands.reliableCommands.size());
        for (const auto &command : commands.reliableCommands)
        {
            if (command.sequence <= lastClientReliableSequence)
                continue;
            // CODREF(1649370 reliable command ring): once a client command
            // cursor exists, every new record must be the next sequence.  A
            // jump cannot be repaired by accepting the later text: the next
            // usercmd key is derived from the reliable ring entry, so doing so
            // turns all following packets into plausible-looking XOR noise.
            // The first observed record may start above one because connection
            // setup can precede this source-side slot, as in the captured
            // sequence-7 fixture.
            if (lastClientReliableSequence != 0 &&
                command.sequence != lastClientReliableSequence + 1)
            {
                return {
                    .kind = NetchanProcessKind::Rejected,
                    .packet = parsed,
                    .userCmdKey = userCmdKey,
                    .decodedCommands = std::move(decoded),
                    .reliableCommands = std::move(commands.reliableCommands),
                    .userCommands = std::move(commands.userCommands),
                    .predictedState = commands.predictedState,
                    .terminalCommand = commands.terminal,
                    .moveCommandCount = commands.moveCommandCount,
                    .controlReply = std::move(fragmentControlReply),
                    .reason = "client reliable command sequence skipped from " +
                        std::to_string(lastClientReliableSequence) + " to " +
                        std::to_string(command.sequence),
                };
            }
            lastClientReliableSequence = command.sequence;
            lastClientReliableCommand = command.command;
            newReliableCommands.push_back(command);
        }

        chan.incomingSequence = parsed.sequence;
        chan.incomingSequenceReceived = true;
        chan.messageAcknowledge = parsed.messageAcknowledge;
        chan.reliableAcknowledge = parsed.reliableAcknowledge;
        chan.lastClientReliableSequence = lastClientReliableSequence;
        chan.lastClientReliableCommand = std::move(lastClientReliableCommand);

        return {
            .kind = NetchanProcessKind::Accepted,
            .packet = parsed,
            .userCmdKey = userCmdKey,
            .decodedCommands = std::move(decoded),
            .reliableCommands = std::move(newReliableCommands),
            .userCommands = std::move(commands.userCommands),
            .predictedState = commands.predictedState,
            .terminalCommand = commands.terminal,
            .moveCommandCount = commands.moveCommandCount,
            .controlReply = std::move(fragmentControlReply),
        };
    }

    std::vector<std::uint8_t> Netchan_Transmit(
        NetchanState &chan,
        const std::uint32_t challenge,
        const std::uint32_t reliableAcknowledge,
        const std::span<const std::uint8_t> commands,
        const std::string_view clientReliableCommand)
    {
        if (!chan.outgoingSequence || chan.outgoingSequence > NetchanSequenceMask || commands.empty())
            return {};

        if (chan.unsentFragments)
            return {};

        const auto sequence = chan.outgoingSequence;
        auto encoded = Netchan_XorCommands(
            commands, challenge ^ sequence, clientReliableCommand);
        std::vector<std::uint8_t> payload;
        payload.reserve(sizeof(reliableAcknowledge) + encoded.size());
        appendU32(payload, reliableAcknowledge);
        payload.insert(payload.end(), encoded.begin(), encoded.end());
        if (payload.size() >= NetchanFragmentSize)
        {
            if (payload.size() > NetchanMaximumFragmentedMessage)
                return {};
            chan.unsentFragments = true;
            // CODREF(1649370 Netchan_TransmitNextFragment 0x6743D0):
            // fragmented messages use CODOL's selective-repeat transport.
            // Bit 30 declares that mode, the peer returns bit 29 plus the
            // 128-bit acknowledgement bitmap, and outgoingSequence advances
            // only after every fragment is acknowledged.  Sending these as
            // bit-31-only fire-and-forget packets made one lost gamestate or
            // large snapshot fragment discard the complete message.
            chan.reliableFragments = true;
            chan.unsentLength = static_cast<std::uint32_t>(payload.size());
            chan.unsentBuffer = std::move(payload);
            chan.fragmentSendCount.fill(0);
            chan.fragmentAcknowledgements.fill(0);
            chan.lowestFragmentSendCount = 0;
            return Netchan_TransmitNextFragment(chan);
        }

        ++chan.outgoingSequence;
        std::vector<std::uint8_t> result;
        result.reserve(4 + payload.size());
        appendU32(result, sequence);
        result.insert(result.end(), payload.begin(), payload.end());
        return result;
    }

    std::vector<std::uint8_t> Netchan_TransmitNextFragment(NetchanState &chan)
    {
        if (!chan.unsentFragments || chan.unsentBuffer.size() != chan.unsentLength)
            return {};

        const auto fragmentCount = static_cast<std::uint32_t>(
            (chan.unsentLength + NetchanFragmentSize - 1) / NetchanFragmentSize);
        if (!fragmentCount || fragmentCount > NetchanMaximumFragments ||
            chan.unsentLength > NetchanMaximumFragmentedMessage)
        {
            return {};
        }
        bool allAcknowledged = chan.reliableFragments;
        if (chan.reliableFragments)
        {
            for (std::uint32_t index = 0; index < fragmentCount; ++index)
            {
                allAcknowledged &= (chan.fragmentAcknowledgements[index >> 5u] &
                    (1u << (index & 31u))) != 0;
            }
        }
        if (allAcknowledged)
        {
            ++chan.outgoingSequence;
            chan.unsentFragments = false;
            chan.reliableFragments = false;
            chan.unsentLength = 0;
            chan.unsentBuffer.clear();
            return {};
        }

        std::uint32_t fragmentIndex{};
        if (chan.reliableFragments)
        {
            while (true)
            {
                for (fragmentIndex = 0; fragmentIndex < fragmentCount; ++fragmentIndex)
                {
                    if (chan.fragmentSendCount[fragmentIndex] <=
                            chan.lowestFragmentSendCount &&
                        (chan.fragmentAcknowledgements[fragmentIndex >> 5u] &
                            (1u << (fragmentIndex & 31u))) == 0)
                    {
                        goto fragment_selected;
                    }
                }
                ++chan.lowestFragmentSendCount;
            }
        }
        else
        {
            // OLMOD(netchan-owned-buffer): unlike native netchan_t, the source
            // retains the complete immutable message and derives progress from
            // send counts instead of advancing a raw buffer pointer.
            fragmentIndex = 0;
            while (fragmentIndex < fragmentCount &&
                chan.fragmentSendCount[fragmentIndex] != 0)
            {
                ++fragmentIndex;
            }
            if (fragmentIndex >= fragmentCount)
                return {};
        }

fragment_selected:
        ++chan.fragmentSendCount[fragmentIndex];
        const auto fragmentStart =
            static_cast<std::size_t>(fragmentIndex) * NetchanFragmentSize;
        const auto fragmentLength = std::min(
            NetchanFragmentSize, chan.unsentBuffer.size() - fragmentStart);
        const auto lastFragmentIndex = static_cast<std::uint8_t>(fragmentCount - 1);

        std::vector<std::uint8_t> result;
        result.reserve(10 + fragmentLength);
        appendU32(
            result,
            chan.outgoingSequence |
                (chan.reliableFragments ? 0xC0000000u : 0x80000000u));
        result.push_back(static_cast<std::uint8_t>(fragmentIndex));
        result.push_back(lastFragmentIndex);
        result.push_back(static_cast<std::uint8_t>(NetchanFragmentSize));
        result.push_back(static_cast<std::uint8_t>(NetchanFragmentSize >> 8));
        result.push_back(static_cast<std::uint8_t>(fragmentLength));
        result.push_back(static_cast<std::uint8_t>(fragmentLength >> 8));
        result.insert(
            result.end(),
            chan.unsentBuffer.begin() + fragmentStart,
            chan.unsentBuffer.begin() + fragmentStart + fragmentLength);

        if (!chan.reliableFragments && fragmentIndex + 1 == fragmentCount)
        {
            ++chan.outgoingSequence;
            chan.unsentFragments = false;
            chan.unsentLength = 0;
            chan.unsentBuffer.clear();
        }
        return result;
    }
}
