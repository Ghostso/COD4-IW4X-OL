#pragma once

#include <array>
#include <cstdint>
#include <functional>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace OlMod::DedicatedControl
{
    constexpr std::uint16_t ProtocolVersion = 2;
    constexpr std::uint16_t DefaultPort = 28961;
    constexpr std::uint16_t DefaultClientBridgePort = 28962;
    constexpr std::string_view DefaultHostAddress = "127.0.0.1";
    constexpr std::uint32_t LoopbackHostIpv4 = 0x7F000001;
    constexpr std::uint32_t MaximumPayloadSize = 16 * 1024;
    constexpr std::uint32_t MaximumRecentReliableCommands = 128;

    enum class MessageType : std::uint16_t
    {
        Booking = 1,
        CaptureLoadout = 2,
        SessionStart = 3,
        ConfigureSession = 4,
        QueryEndpoint = 5,
        QueryGameplayStatus = 6,
        // A player holding the noclip key. Sent by the CLIENT plugin, which
        // already carries OLMOD_DEDICATED_CONTROL_PORT and the platform user
        // id, and reaches a remote dedicated unchanged because the control
        // listener binds 0.0.0.0 whenever OLMOD_HOST_ADDRESS is not loopback.
        SetNoclip = 7,
        // Refresh ONE roster member's loadout live, mid-match, with no world
        // rebuild: payload is u64 userId + encode(LoadoutRequest). The dedicated
        // re-registers the member's weapons into the running gamestate and pushes
        // their config strings to every client. See §157c and the handler.
        UpdateLoadout = 8,
        // RUN A DIAGNOSTIC IN THE LIVE CLIENT, so an audit does not cost a cycle.
        //
        // Every measurement today needed a full restart: kill the stack, rebuild, relaunch,
        // and the player had to queue up again -- for a question that is a loop over a
        // table the running client already has. Payload is the diagnostic's name.
        //
        // It TRIGGERS and returns; it does not carry results back. The work runs on a
        // detached thread and writes to the log or a CSV, because doing it on the request
        // path would put it on the same thread the loadout capture needs, which is exactly
        // what stalled a match earlier.
        RunDiagnostic = 9,
        // AUDITION ONE ANNOUNCER LINE, so naming a clip does not cost a match.
        //
        // The announcer band is 392 lines the client already holds (191n) and the
        // demo only proves WHEN retail sent each one, never what the recording
        // SAYS. Reasoning about a filename is not a measurement -- retail sent
        // `uk_1mc_timesup` at exactly 30 s remaining, and whether that clip
        // speaks "time's up" or "thirty seconds" cannot be read off its name.
        //
        // Payload is the u16 event parameter. Broadcast to every Active client,
        // on the game thread, exactly as the match announcer sends it.
        PlayAnnouncer = 10,
        // REPLAY A RAW RELIABLE COMMAND, byte for byte, into the running match.
        //
        // The kill feed is carried by something we have not decoded. Retail's
        // own bytes are in the demo; replaying them and watching the screen
        // turns an unbounded reverse-engineering job into a bounded experiment,
        // which is what this project's runtime tools are for.
        //
        // A MALFORMED BINARY COMMAND CAN DESYNC OR CRASH A CLIENT, so this is
        // refused unless OLMOD_ALLOW_RAW_COMMAND=1. Payload is the raw bytes
        // INCLUDING the verb.
        SendRawCommand = 11,
        // OLMOD(debug_battery): decimal client slot, loopback-only opt-in Factory test request.
        // Empty legacy requests remain solo-only; never guess among local peers.
        DebugGrantBattery = 12,
        RoomConnect = 16,
        RoomDisconnect = 17,
        RoomSetReady = 18,
        RoomFreeze = 19,
        RoomCanonicalizeSession = 20,
    };

    enum class ResponseStatus : std::uint16_t
    {
        Accepted = 0,
        InvalidMessage = 1,
        UnsupportedMessage = 2,
        Rejected = 3,
    };

    struct Message
    {
        MessageType type{};
        std::uint64_t requestId{};
        std::string payload;

        // TRANSPORT-SUPPLIED AND NEVER ENCODED: the address this request
        // arrived from, host order, filled in by Server before it calls the
        // handler. Zero on the sending side and zero for anything that did
        // not come off a socket. It is how the room owner learns where a
        // member's bridge lives without the member having to guess which of
        // its own addresses is reachable from the owner.
        std::uint32_t peerIpv4{};
    };

    struct SubmitResult
    {
        bool delivered{};
        ResponseStatus status{ResponseStatus::Rejected};
        std::uint64_t requestId{};
        int socketError{};
        std::string payload;
    };

    struct Response
    {
        ResponseStatus status{ResponseStatus::Rejected};
        std::string payload;
    };

    // EDGE PLUS KEEP-ALIVE, NOT LEVEL. The sender pushes one message when the
    // key goes down, one when it comes up, and a repeat every half second in
    // between. holdMilliseconds is how long the dedicated should keep flying
    // the player without hearing again -- so a LOST key-up expires instead of
    // leaving somebody stuck in the air forever, which is the failure mode
    // that matters when the sender is a friend's machine across the internet.
    struct NoclipRequest
    {
        std::uint64_t userId{};
        bool enabled{};
        std::uint32_t holdMilliseconds{};

        bool operator==(const NoclipRequest &) const = default;
    };

    struct GameServerEndpointStatus
    {
        bool sessionConfigured{};
        bool enabled{};
        bool bound{};
        std::uint16_t port{};

        bool operator==(const GameServerEndpointStatus &) const = default;
    };

    struct GameplayObjectiveStatus
    {
        std::uint32_t state{};
        std::uint32_t icon{};

        bool operator==(const GameplayObjectiveStatus &) const = default;
    };

    struct GameplayReliableCommandStatus
    {
        std::uint32_t sequence{};
        std::string command;

        bool operator==(const GameplayReliableCommandStatus &) const = default;
    };

    struct GameplayClientStatus
    {
        std::uint32_t clientNum{};
        std::uint32_t gameplayState{};
        std::uint32_t team{};
        std::uint32_t reliableSequence{};
        std::uint32_t reliableAcknowledge{};
        std::uint32_t peerIpv4{};
        std::uint16_t peerPort{};
        std::uint32_t lastPacketReceivedTime{};
        std::uint32_t incomingSequence{};
        std::uint32_t outgoingSequence{};
        std::uint32_t messageAcknowledge{};
        std::uint64_t udpSendAttempts{};
        std::uint64_t udpSendSucceeded{};
        std::uint64_t udpSendFailed{};
        std::uint64_t udpBytesSent{};
        std::uint32_t lastUdpSendTime{};
        std::uint32_t lastUdpSendBytes{};
        std::int32_t lastUdpSendError{};
        std::uint32_t pendingUserCmdCount{};
        std::uint32_t oldestPendingUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t newestPendingUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t lastReceivedUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t lastDispatchedUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t lastExecutedUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t lastDiscardedUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t discardedUnsupportedUserCmds{};
        std::uint32_t lastDiscardedRejectedUserCmdTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t discardedRejectedUserCmds{};
        std::uint32_t clientThinkLastAttemptedCommandTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t clientThinkLastCommittedCommandTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::uint32_t clientThinkFailureStage{};
        std::uint32_t clientThinkFailureCount{};
        std::uint32_t lastDispatchedButtons{};
        std::array<std::uint32_t, 3> lastDispatchedAngles{};
        std::uint32_t lastDispatchedWeapon{};
        std::uint32_t lastDispatchedOffhand{};
        std::int32_t lastDispatchedForwardMove{};
        std::int32_t lastDispatchedRightMove{};
        std::uint32_t snapshotPlayerEntityMask{};
        std::uint32_t snapshotClientInfoMask{};
        // Schema 5. The locational hit readout, over the control socket rather
        // than through Frida: CodolGameServerControl.py --pid <dedicated>
        // terminated the dedicated two runs out of three, so a Frida probe can
        // never be the way this is sampled during a live match. Origin plus the
        // last committed bullet trace is enough to compute the world point the
        // server resolved a hit to, and therefore its height above the target's
        // feet - which is the one measurement that separates a collapsed hit
        // skeleton from a mis-aimed trace.
        std::array<float, 3> origin{};
        std::array<float, 3> viewAngles{};
        std::uint32_t health{};
        std::uint32_t bulletCommandTime{
            std::numeric_limits<std::uint32_t>::max() };
        std::array<float, 3> bulletStart{};
        std::array<float, 3> bulletEnd{};
        float bulletFraction{};
        std::uint32_t bulletHitType{};
        std::uint32_t bulletHitEntityNum{ 2047 };
        std::uint32_t bulletModelIndex{};
        std::uint32_t bulletPartName{};
        std::uint32_t bulletPartGroup{};
        std::uint32_t bulletResult{};
        std::array<GameplayObjectiveStatus, 3> objectives{};
        std::vector<GameplayReliableCommandStatus> recentReliableCommands;

        bool operator==(const GameplayClientStatus &) const = default;
    };

    struct GameplaySdStatus
    {
        std::uint32_t roundConfigured{};
        std::uint32_t roundArmed{};
        std::uint32_t roundCompleted{};
        std::uint32_t roundsPlayed{};
        std::uint32_t roundWinner{};
        std::uint32_t roundEndReason{};
        std::uint32_t bombConfigured{};
        std::uint32_t bombPhase{};
        std::uint32_t attackers{};
        std::uint32_t defenders{};
        std::uint32_t attackersAlive{};
        std::uint32_t defendersAlive{};
        std::uint32_t carrierClientNum{};
        std::uint32_t planterClientNum{};
        std::uint32_t defuserClientNum{};
        std::uint32_t plantedSiteLabel{};
        std::uint32_t phaseStartServerTime{};
        std::uint32_t plantedServerTime{};

        bool operator==(const GameplaySdStatus &) const = default;
    };

    struct GameplayStatus
    {
        std::uint32_t serverTime{};
        GameplaySdStatus sd;
        std::vector<GameplayClientStatus> clients;

        bool operator==(const GameplayStatus &) const = default;
    };

    using MessageHandler = std::function<Response(const Message &)>;

    class Server
    {
    public:
        Server();
        ~Server();
        Server(const Server &) = delete;
        Server &operator=(const Server &) = delete;

        bool start(std::uint16_t port, MessageHandler handler);
        void stop();
        [[nodiscard]] bool running() const;
        [[nodiscard]] std::uint16_t port() const;
        [[nodiscard]] int lastSocketError() const;

    private:
        struct State;
        std::unique_ptr<State> state_;
    };

    [[nodiscard]] SubmitResult submit(
        std::string_view host,
        std::uint16_t port,
        const Message &message,
        std::uint32_t timeoutMilliseconds = 500);

    [[nodiscard]] std::string encodeEndpointStatus(
        const GameServerEndpointStatus &status);
    [[nodiscard]] std::optional<GameServerEndpointStatus> decodeEndpointStatus(
        std::string_view payload);
    // a.b.c.d from the same host-order convention LoopbackHostIpv4 uses.
    [[nodiscard]] std::string ipv4Text(std::uint32_t ipv4);

    [[nodiscard]] std::string encodeNoclipRequest(const NoclipRequest &request);
    [[nodiscard]] std::optional<NoclipRequest> decodeNoclipRequest(
        std::string_view payload);

    [[nodiscard]] std::string encodeGameplayStatus(const GameplayStatus &status);
    [[nodiscard]] std::optional<GameplayStatus> decodeGameplayStatus(
        std::string_view payload);

    [[nodiscard]] std::uint16_t configuredPort();
    [[nodiscard]] std::uint16_t configuredClientBridgePort();

    // OLMOD_HOST_ADDRESS names the ONE machine that runs the room owner, the
    // dedicated and the game socket. Unset means 127.0.0.1, so an environment
    // that does not mention it behaves exactly as it did before remote play
    // existed. Every peer -- host included -- sets the SAME value.
    [[nodiscard]] std::string configuredHostAddress();
    [[nodiscard]] std::uint32_t configuredHostIpv4();
    [[nodiscard]] bool hostIsRemote();
}
