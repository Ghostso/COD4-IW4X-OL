#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    constexpr std::uint32_t NetchanSequenceMask = 0x1FFFFFFFu;
    constexpr std::size_t NetchanFragmentSize = 1154;
    constexpr std::size_t NetchanMaximumFragments = 128;
    constexpr std::size_t NetchanMaximumFragmentedMessage = 0x20000;
    constexpr std::uint8_t ClientCommandReliable = 2;
    constexpr std::uint8_t ClientCommandEof = 3;
    constexpr std::uint8_t ServerCommandReliable = 1;
    constexpr std::uint8_t ServerCommandReliableBinary = 2;
    // 3.3.3.3 ends a server message with 6; OLfinal ends it with 5, and this constant was
    // carried across unchanged. MEASURED on two independent corpora and recorded in
    // re/demo-re/01-container.md sec 4 and 06-olevents.md sec 2: it is the final byte of
    // 54,682/54,682 demo snapshot payloads, the end token of the gamestate's configstring
    // block, and the byte after the gamestate's clientNum/checksumFeed pair -- every slot
    // where 3.3.3.3 writes 6. The rest of the table is unchanged: 0 snapshot, 1
    // serverCommand, 2 binary serverCommand, 3 gamestate, 4 configstring block start.
    // OLfinal has no opcode 6 at all, so a message terminated with 6 is not merely read
    // wrong -- it falls through to the parse loop's error exit.
    constexpr std::uint8_t ServerCommandEof = 5;

    struct ClientReliableCommand
    {
        std::uint32_t sequence{};
        std::string command;
    };

    struct UserCmd
    {
        std::uint32_t commandTime{};
        std::uint32_t buttons{};
        std::array<std::uint16_t, 3> angles{};
        std::uint16_t weapon{};
        std::uint16_t offHandIndex{};
        // Legacy names above/below are retained for the diagnostics ABI.
        // CODREF(1649370): 0x5B2241 writes cg.equippedOffHand through
        // clientActive+0x3C64 into native usercmd+0x18: THIS member is the
        // equipped offhand. The preceding +0x16 member comes from the
        // per-weapon lookup at cg+0xC7238, not cg.equippedOffHand.
        std::uint16_t lastWeaponAltModeSwitch{};
        std::int8_t forwardMove{};
        std::int8_t rightMove{};
        float conditionalAngle{};
        std::uint8_t conditionalByte{};
        std::uint16_t conditionalElevenBits{};
        std::array<std::uint8_t, 3> selectedLocation{};
        std::array<std::uint8_t, 2> selectedDirection{};

        bool operator==(const UserCmd &) const = default;
    };

    struct ClientPredictedState
    {
        std::array<std::uint32_t, 5> values{};

        bool operator==(const ClientPredictedState &) const = default;
    };

    enum class ClientCommandKind : std::uint8_t
    {
        MoveDelta = 0,
        MoveNoDelta = 1,
        Reliable = 2,
        Eof = 3,
        Invalid = 0xFF,
    };

    struct ClientNetchanPacket
    {
        std::uint32_t sequence{};
        std::uint8_t serverId{};
        std::uint32_t messageAcknowledge{};
        std::uint32_t reliableAcknowledge{};
        std::span<const std::uint8_t> encodedCommands;
    };

    struct NetchanState
    {
        std::uint32_t incomingSequence{};
        std::uint32_t outgoingSequence{ 1 };
        std::uint32_t messageAcknowledge{};
        std::uint32_t reliableAcknowledge{};
        std::uint32_t lastClientReliableSequence{};
        std::string lastClientReliableCommand;
        bool incomingSequenceReceived{};
        // CODREF(netchan_fragment): CODOL 0x005A5490/0x005A55F0/
        // 0x005A5720 retain one outgoing message under a stable sequence and
        // send indexed 1154-byte fragments until completion.
        bool unsentFragments{};
        bool reliableFragments{};
        std::uint32_t unsentLength{};
        std::vector<std::uint8_t> unsentBuffer;
        std::array<std::uint8_t, NetchanMaximumFragments> fragmentSendCount{};
        std::array<std::uint32_t, 4> fragmentAcknowledgements{};
        std::uint32_t lowestFragmentSendCount{};

        // CODREF(netchan_fragment): CODOL Netchan_Process 0x005A5960 owns a
        // separate receive sequence, aggregate length and four-word bitmap.
        std::uint32_t fragmentSequence{};
        std::uint32_t fragmentLength{};
        std::uint16_t fragmentStride{};
        std::uint8_t lastFragmentIndex{};
        std::array<std::uint32_t, 4> receivedFragmentBits{};
        std::vector<std::uint8_t> fragmentBuffer;
    };

    enum class NetchanProcessKind : std::uint8_t
    {
        Accepted,
        FragmentPending,
        FragmentAcknowledgement,
        Duplicate,
        Rejected,
    };

    struct NetchanProcessResult
    {
        NetchanProcessKind kind{ NetchanProcessKind::Rejected };
        ClientNetchanPacket packet;
        // OLMOD(section-88): THE KEY THE USERCMD DELTAS WERE READ WITH, so a
        // captured stream can be REPLAYED. Every `changed` bit in a usercmd is
        // keyed, so a capture decoded under one key is noise under another --
        // which is why the first attempt to turn a real capture into a golden
        // produced `changed=0 full=0 bitsAtTrailer=0` instead of the field it
        // was aimed at. It is `checksumFeed ^ messageAcknowledge ^
        // Com_HashKey(serverReliableCommand)`, and none of those three are
        // recoverable from the decoded bytes.
        std::uint32_t userCmdKey{};
        std::vector<std::uint8_t> decodedCommands;
        std::vector<ClientReliableCommand> reliableCommands;
        std::vector<UserCmd> userCommands;
        ClientPredictedState predictedState;
        ClientCommandKind terminalCommand{ ClientCommandKind::Invalid };
        std::uint32_t moveCommandCount{};
        std::uint32_t rejectedCommandTime{};
        std::uint32_t rejectedCommandBaselineTime{};
        std::vector<std::uint8_t> controlReply;
        std::string reason;
    };

    using NetchanReliableCommandResolver = std::function<
        std::optional<std::string>(std::uint32_t reliableAcknowledge)>;
    using NetchanDefaultUserCmdResolver = std::function<
        UserCmd(std::uint32_t messageAcknowledge)>;
    [[nodiscard]] bool NET_IsConnectionlessPacket(std::span<const std::uint8_t> packet);
    [[nodiscard]] std::vector<std::uint8_t> Netchan_XorCommands(
        std::span<const std::uint8_t> payload,
        std::uint32_t seed,
        std::string_view reliableCommand = {});
    [[nodiscard]] std::uint32_t Com_HashKey(
        std::string_view value,
        std::size_t maxLength = 32);
    [[nodiscard]] NetchanProcessResult Netchan_Process(
        NetchanState &chan,
        std::span<const std::uint8_t> packet,
        std::uint32_t challenge,
        std::uint32_t checksumFeed = 0,
        std::string_view serverReliableCommand = {},
        const UserCmd &defaultUserCmd = {},
        const NetchanReliableCommandResolver &reliableCommandResolver = {},
        const NetchanDefaultUserCmdResolver &defaultUserCmdResolver = {});
    [[nodiscard]] std::vector<std::uint8_t> Netchan_Transmit(
        NetchanState &chan,
        std::uint32_t challenge,
        std::uint32_t reliableAcknowledge,
        std::span<const std::uint8_t> commands,
        std::string_view clientReliableCommand = {});
    [[nodiscard]] std::vector<std::uint8_t> Netchan_TransmitNextFragment(
        NetchanState &chan);
}
