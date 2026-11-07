#pragma once

#include "qcommon/net_chan_mp.hpp"
#include "qcommon/net_types.hpp"
#include "sv_gamestate_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    // STEP 1 OF THE ROUND SYSTEM (12.131.3). Publishes the four `ui_hud_*` client
    // dvars retail sets, on ClientEnterWorld, so the `回合 N/8` HUD stops showing
    // leftover client state. Round 1 is a constant: there is no round loop yet and
    // this deliberately does not pretend otherwise.
    constexpr bool SvPublishZmRoundHud = true;

    // OLMOD(client-system-source-owner): capacities for source diagnostics and
    // reliable-command storage; they are not recovered native client_t fields.
    constexpr std::size_t ClientCommandPrefixCapacity = 64;
    // OLMOD(section-82): THIS ONE IS NOT OURS TO CHOOSE. The comment above says these
    // are source-side capacities, and for ClientCommandPrefixCapacity that is true --
    // but `reliableCommandResolver` in sv_client_mp.cpp reproduces the CLIENT'S OWN
    // indexing, because the client XORs its packet with
    // `serverCommands[reliableAcknowledge & mask]`. Pick a different mask and the two
    // sides derive the key from different slots the moment a sequence exceeds it.
    //
    // out.exe's CL_ParseCommandString is sub_4737E0 and says the mask outright:
    //
    //   3.3.3.3  sub_46E3B0    and ebx, 0FFh    shl ebx,0Ah   lea esi,[ebx+ecx+40154h]
    //   out.exe  sub_4737E0    and ebx, 1FFh    shl ebx,0Ah   lea esi,[ebx+ecx+80154h]
    //
    // Same 1024-byte slots, same `push 3FFh` strncpy, same `xor ecx, 0D362501Fh`
    // pointer cookie -- and 512 entries where 3.3.3.3 has 256. The sequence field and
    // the ring base both move by 0x40000, which is exactly the extra 256 slots.
    //
    // **128 WAS NEITHER BUILD'S NUMBER.** It also made the staleness guard in
    // reliableCommandResolver return an empty key for any gap of 128..511, which is a
    // second way to desync the same XOR.
    constexpr std::size_t ServerReliableCommandCapacity = 512;
    constexpr std::uint32_t ReliableKeyComplaintLimit = 8;
    static_assert(std::has_single_bit(ServerReliableCommandCapacity));
    constexpr std::uint16_t LocalSoundEventParameterMaximum = 0x3E80;
    [[nodiscard]] std::optional<std::string>
        SV_BuildPlayLocalSoundCommand(std::uint16_t eventParameter);

    // OLMOD(client-connection-state): semantic source state machine matching
    // observed CODOL transitions, not native enum ordinals or storage.
    enum class ClientState : std::uint8_t
    {
        Free,
        Connected,
        ClientLoading,
        Active,
    };

    enum class ServerReliableCommandKind : std::uint8_t
    {
        Text,
        Binary,
    };

    // OLMOD(server-reliable-command-ring): typed source storage for the exact
    // text/binary XOR-key behavior consumed by the recovered netchan writer.
    struct ServerReliableCommand
    {
        ServerReliableCommandKind kind{ ServerReliableCommandKind::Text };
        std::string text;
        std::vector<std::uint8_t> payload;

        [[nodiscard]] std::string_view xorKey() const
        {
            return kind == ServerReliableCommandKind::Binary
                ? std::string_view{ "!" }
                : std::string_view{ text };
        }
    };

    // OLMOD(client-ingress-diagnostics): parsed control and rejection views;
    // these never participate in native wire layout.
    struct ClientMenuResponse
    {
        std::uint32_t sequence{};
        std::uint32_t serverId{};
        std::uint32_t menuIndex{};
        std::string menuName;
        std::string response;

        bool operator==(const ClientMenuResponse &) const = default;
    };

    struct ClientPacketRejectStatus
    {
        std::uint32_t sequence{};
        std::uint8_t serverId{};
        std::uint32_t messageAcknowledge{};
        std::uint32_t reliableAcknowledge{};
        std::uint32_t decodedCommandsSize{};
        std::uint32_t rejectedCommandTime{};
        std::uint32_t rejectedCommandBaselineTime{};
        std::array<std::uint8_t, ClientCommandPrefixCapacity> decodedCommandsPrefix{};
        std::string reason;
    };

    enum class SvSnapshotAssemblyFailure : std::uint8_t
    {
        None,
        WorldFrameUnavailable,
        SnapshotBuilderUnavailable,
        DuplicateServerTime,
        SnapshotBuilderEmpty,
        NetchanTransmitEmpty,
    };

    [[nodiscard]] std::string_view SV_SnapshotAssemblyFailureName(
        SvSnapshotAssemblyFailure failure);

    // OLMOD(client-system-source-owner): aggregate owner for connection,
    // snapshot, command, gameplay and diagnostics state in ol_game_server.
    // TODO(CODOL): do not assign native offsets or collapse this into client_t
    // until the removed dedicated layout and lifecycle are independently
    // recovered; retire source-only fields by responsibility, not resemblance.
    struct ClientSlot
    {
        struct SnapshotHistoryEntry
        {
            bool valid{};
            bool initializesBaselineCache{};
            std::uint32_t messageNum{};
            // CODDIFF(sv_build_client_snapshot): BO1/Ghosts client frames own
            // playerState plus indexes into global snapshot entity/client
            // rings. ol-mod's source frame is already an immutable aggregate,
            // so history shares that aggregate instead of deep-copying every
            // entity/client/glass vector once per connected client.
            std::shared_ptr<const SvSnapshotFrame> frame;
        };

        ClientState state{ ClientState::Free };
        PeerAddress peer{};
        std::uint64_t xuid{};
        std::uint64_t sessionGeneration{};
        std::uint32_t challenge{};
        std::uint32_t connectTime{};
        std::uint32_t lastPacketTime{};
        NetchanState netchan;
        std::uint32_t reliableSequence{};
        // OLMOD(reliable-key-desync-witness): how many times this client's inbound key
        // could not be resolved. Bounded so a wedged client cannot flood the log --
        // the FIRST few carry the diagnosis and the rest are the same line forever.
        std::uint32_t reliableKeyComplaints{};
        std::array<ServerReliableCommand, ServerReliableCommandCapacity>
            reliableCommands;
        std::uint32_t profileStatsReceivedMask{};
        std::uint32_t profileStatsRequiredMask{ 0x07FFFFFFu };
        // Last reported reason the gamestate gate stayed shut, so the log prints once per
        // distinct combination rather than once per packet. Purely diagnostic, and it is the
        // line that identified GAMESTATE_NOT_CONFIGURED as the map-load hang on 2026-08-30.
        std::string gameStateGateReport;
        bool profileStatsComplete{};
        std::uint32_t gamestateMessageNum{};
        std::uint32_t gameStateUpdateStage{};
        std::uint32_t lastSnapshotServerTime{};
        // CODREF(sv_send_client_messages): BO1/BO2/Ghosts admit a client only
        // after nextSnapshotTime and publish rateDelayed beside that decision.
        // These are source-side scheduling fields, not asserted CODOL client_t
        // offsets. Internet rate-window ownership remains TODO(CODOL).
        std::uint32_t nextSnapshotTime{};
        std::uint32_t lastSnapshotTime{};
        bool rateDelayed{};
        bool snapshotSent{};
        SvSnapshotAssemblyFailure snapshotAssemblyFailure{};
        std::uint64_t snapshotAssemblyAttempts{};
        std::uint64_t snapshotAssemblyFailures{};
        bool baselineCacheAcknowledged{};
        std::optional<std::uint32_t> baselineCacheInitializationMessage;
        // THE NEWEST FLAGGED MESSAGE, WHICH IS THE ONLY FLAGGED FRAME THE CLIENT CAN
        // STILL BE HOLDING ENTITIES FOR (section 170). out.exe stores the entities of a
        // flagged frame in dword_C89E050, a FLAT array with no frame number, and
        // CL_ParseSnapshot resets its cursor dword_C89E04C to zero at 0x00472223 on every
        // frame that carries the flag. So that array holds exactly ONE generation: the
        // newest flagged frame the client has parsed. sub_470E90 0x00470e97 reads an
        // entity baseline row out of it whenever the BASELINE frame's snapFlags carry
        // bit 8, indexed by list position alone.
        //
        // baselineCacheInitializationMessage cannot answer this question: it is reset the
        // moment the client acknowledges it (sv_client_mp.cpp, the acknowledged-snapshot
        // block), which is precisely when the selection below needs to know. This one is
        // monotone for the life of a connection and is cleared only where
        // snapshotHistory is cleared, because both describe the same client generation.
        std::optional<std::uint32_t> newestFlaggedSnapshotMessage;
        std::shared_ptr<const SvSnapshotFrame> baselineFrame;
        std::int32_t deltaMessage{ -1 };
        std::uint32_t lastMoveCommandCount{};
        // OLMOD(pending-usercmd-queue): these checkpoints separate packet
        // receipt, game-thread dispatch, successful authoritative execution,
        // and temporary restoration-only discard. They are project ownership
        // fields, not asserted offsets in a recovered CODOL client_t.
        std::optional<UserCmd> lastReceivedUserCmd;
        std::optional<UserCmd> lastDispatchedUserCmd;
        std::optional<UserCmd> lastExecutedUserCmd;
        std::optional<UserCmd> lastDiscardedUnsupportedUserCmd;
        std::uint32_t discardedUnsupportedUserCmds{};
        std::optional<UserCmd> lastDiscardedRejectedUserCmd;
        std::uint32_t discardedRejectedUserCmds{};
        std::optional<UserCmd> lastDroppedOverflowUserCmd;
        std::uint32_t droppedOverflowUserCmds{};
        std::deque<UserCmd> pendingUserCmds;
        std::uint32_t lastQueuedUserCmdTime{};
        std::optional<ClientMenuResponse> lastMenuResponse;
        // Reliable command texts this slot has already had reported as
        // unhandled. Bounded so the instrument is SILENT once a client's
        // vocabulary is known instead of printing at the command rate.
        std::set<std::string> reportedUnhandledCommands;
        ClientGameplayState gameplayState{ ClientGameplayState::Inactive };
        std::string selectedLoadout;
        std::uint32_t loadoutSequence{};
        std::uint32_t spawnSequence{};
        // Zero-based multiplayer rank from the authenticated connection's
        // userinfo. IW4's match-bonus GSC calls getRank()+1 when deriving SPM.
        std::uint16_t rank{};
        SvCharacterFaction characterFaction{ SvCharacterFaction::Tf };
        SvTeam team{ SvTeam::None };
        std::string pendingSelectedLoadout;
        std::uint32_t pendingLoadoutSequence{};
        SvCharacterFaction pendingCharacterFaction{ SvCharacterFaction::Tf };
        SvTeam pendingTeam{ SvTeam::None };
        ClientPredictedState predictedState;
        std::uint32_t acceptedPackets{};
        std::uint32_t duplicatePackets{};
        std::uint32_t rejectedPackets{};
        std::optional<ClientPacketRejectStatus> lastPacketReject;
        std::uint32_t lastDecodedCommandsSize{};
        std::array<std::uint8_t, ClientCommandPrefixCapacity> lastDecodedCommandsPrefix{};
        std::array<SnapshotHistoryEntry, SnapshotHistoryCapacity> snapshotHistory;
        std::string name;
        std::string userInfo;
    };

    struct SvClientScore
    {
        std::int32_t score{};
        std::int32_t deaths{};
        std::int32_t kills{};
        std::int32_t assists{};
        std::int32_t objectives{};
        std::int32_t downs{};
        std::int32_t revives{};
        std::int32_t headshots{};
        std::int32_t killstreak{};
        // Per-match earnings shown by the AAR scoreboard. Retail updates xp
        // and gp in the same aarScoreboard row as kills/score before the
        // outcome notification appears.
        std::int32_t xp{};
        std::int32_t gp{};

        bool operator==(const SvClientScore &) const = default;
    };

    // OLMOD(client-ingress-diagnostics): read-only flattened status returned to
    // control/log tooling; duplicated values have no gameplay ownership.
    struct ClientIngressStatus
    {
        PeerAddress peer{};
        std::uint64_t xuid{};
        std::string name;
        ClientState state{ ClientState::Free };
        std::uint32_t profileStatsReceivedMask{};
        std::uint32_t profileStatsRequiredMask{};
        bool profileStatsComplete{};
        std::uint32_t gameStateUpdateStage{};
        std::uint32_t gamestateMessageNum{};
        std::uint64_t sessionGeneration{};
        bool sessionGenerationActive{};
        std::uint32_t lastPacketTime{};
        std::uint32_t incomingSequence{};
        std::uint32_t outgoingSequence{};
        std::uint32_t messageAcknowledge{};
        std::uint32_t reliableAcknowledge{};
        std::uint32_t lastClientReliableSequence{};
        std::string lastClientReliableCommand;
        std::int32_t deltaMessage{ -1 };
        std::uint32_t lastMoveCommandCount{};
        SvSnapshotAssemblyFailure snapshotAssemblyFailure{};
        std::uint64_t snapshotAssemblyAttempts{};
        std::uint64_t snapshotAssemblyFailures{};
        std::optional<UserCmd> lastReceivedUserCmd;
        std::optional<UserCmd> lastDispatchedUserCmd;
        std::optional<UserCmd> lastExecutedUserCmd;
        std::optional<UserCmd> lastDiscardedUnsupportedUserCmd;
        std::uint32_t discardedUnsupportedUserCmds{};
        std::optional<UserCmd> lastDiscardedRejectedUserCmd;
        std::uint32_t discardedRejectedUserCmds{};
        std::optional<UserCmd> lastDroppedOverflowUserCmd;
        std::uint32_t droppedOverflowUserCmds{};
        std::optional<ClientMenuResponse> lastMenuResponse;
        // Reliable command texts this slot has already had reported as
        // unhandled. Bounded so the instrument is SILENT once a client's
        // vocabulary is known instead of printing at the command rate.
        std::set<std::string> reportedUnhandledCommands;
        ClientGameplayState gameplayState{ ClientGameplayState::Inactive };
        std::string selectedLoadout;
        std::uint32_t loadoutSequence{};
        std::uint32_t spawnSequence{};
        SvCharacterFaction characterFaction{ SvCharacterFaction::Tf };
        SvTeam team{ SvTeam::None };
        std::string pendingSelectedLoadout;
        std::uint32_t pendingLoadoutSequence{};
        SvCharacterFaction pendingCharacterFaction{ SvCharacterFaction::Tf };
        SvTeam pendingTeam{ SvTeam::None };
        std::uint32_t acceptedPackets{};
        std::uint32_t duplicatePackets{};
        std::uint32_t rejectedPackets{};
        std::optional<ClientPacketRejectStatus> lastPacketReject;
        std::uint32_t decodedCommandsSize{};
        std::array<std::uint8_t, ClientCommandPrefixCapacity> decodedCommandsPrefix{};
    };

    struct ServerReliableCommandRecord
    {
        std::uint32_t sequence{};
        std::string command;

        bool operator==(const ServerReliableCommandRecord &) const = default;
    };

    struct ServerReliableCommandStatus
    {
        std::uint32_t sequence{};
        std::uint32_t acknowledge{};
        std::vector<ServerReliableCommandRecord> recentCommands;

        bool operator==(const ServerReliableCommandStatus &) const = default;
    };

    [[nodiscard]] bool SV_CopyClientReliableCommandStatus(
        const ClientIngressStatus &status,
        std::uint32_t &sequence,
        std::span<char> command,
        std::uint32_t &commandLength);
    [[nodiscard]] bool SV_CopyStatusText(
        std::string_view value,
        std::span<char> output,
        std::uint32_t &valueLength);
    [[nodiscard]] UserCmd SV_DefaultUserCmdFromPlayerState(
        const SvPlayerState &playerState);
    // CODREF(cl_write_packet): CODOL out.exe 1649370 CL_WritePacket
    // 0x005B2C10 (RVA 0x1B2C10) computes
    //     count = cl.cmdNumber - outPackets[..].cmdNumber;
    //     if (count > 32) count = 32;
    // and then chains that many MSG_WriteDeltaUsercmdKey 0x0066F410 deltas
    // into one packet. THIRTY-TWO IS CODOL'S OWN MAX_PACKET_USERCMDS, read off
    // the client that actually talks to us. What stood here was Ghosts'
    // retained-eight, which silently discarded player input the moment more
    // than eight commands arrived together -- and a CODOL client will hand a
    // server up to thirty-two in ONE packet.
    // re/demo-re/30-codols-own-usercmd-numbers.md carries the working.
    //
    // RAISING IT IS INERT AT THE CURRENT 50 ms FRAME, AND THAT IS THE POINT.
    // Per-hour runtime-perf samples over live matches: at 50 ms the queue
    // peaks at 7 of 8 and NEVER reaches capacity; at the 100 ms frame it sat
    // AT capacity in 33% of samples, and every one of those was a dropped
    // usercmd. The ceiling was the defect; the tick rate was not.
    inline constexpr std::size_t PendingUserCmdCapacity = 32;
    [[nodiscard]] bool SV_QueuePendingUserCmd(
        ClientSlot &client,
        const UserCmd &command);
    [[nodiscard]] std::optional<ClientMenuResponse> SV_ParseMenuResponse(
        std::string_view command,
        std::uint32_t expectedServerId,
        const SvGameState &gameState);
    // Whether the class menu picks a SIDE or only a model. CODOL routes both
    // through the same changeclass_marines / changeclass_opfor menus, so the
    // gametype is the only thing that can tell them apart. Deliberately has no
    // default: a teamless mode that forgets to say so would land both players on
    // one team and silently make them unable to damage each other.
    enum class SvTeamPolicy : std::uint8_t
    {
        Teams,
        FreeForAll,
    };

    [[nodiscard]] bool SV_DispatchMenuResponse(
        ClientSlot &client,
        const ClientMenuResponse &response,
        SvTeamPolicy teamPolicy,
        bool allowGenericClassMenu = false);

    // OLMOD(client-transport-adapters): host-facing result objects preserve
    // explicit ownership of the one-datagram ingress/egress boundary.
    enum class ConnectionlessResultKind : std::uint8_t
    {
        Ignored,
        Reply,
        Connected,
        ClientProgress,
        Rejected,
    };

    struct ConnectionlessResult
    {
        ConnectionlessResultKind kind{ ConnectionlessResultKind::Ignored };
        std::vector<std::uint8_t> reply;
        std::size_t clientSlot{ static_cast<std::size_t>(-1) };
        std::uint32_t challenge{};
        std::string reason;
    };

    struct ClientPacketResult
    {
        NetchanProcessKind kind{ NetchanProcessKind::Rejected };
        std::vector<std::uint8_t> reply;
        std::vector<std::uint8_t> decodedCommands;
        std::vector<ClientReliableCommand> reliableCommands;
        std::vector<UserCmd> userCommands;
        std::size_t clientSlot{ static_cast<std::size_t>(-1) };
        std::string reason;
    };

    struct SvClientMessage
    {
        PeerAddress peer{};
        std::vector<std::uint8_t> plaintext;
    };

    // A CRASHED CLIENT HOLDS ITS SLOT UNTIL ONE OF THESE EXPIRES, AND IT CANNOT
    // REJOIN WHILE IT DOES. A CODOL client that crashes exits tidily and simply
    // stops sending (see codol-client-crash-reports-are-already-captured), so the
    // server sees only silence and waits out the full timeout.
    //
    // These were 80 s connecting / 240 s active. Four minutes to reclaim a seat is
    // unusable when a player crashes mid-match and wants straight back in, and the
    // zhunt load crash (HANDOFF section 152w) lands in the CONNECTING state, so
    // that one cost 80 s every time.
    //
    // Silence is unambiguous once the lifecycle reaches Playing: nothing
    // legitimate stops sending for 15 s during gameplay. A gamestate
    // acknowledgement and even an early move packet can arrive before the map
    // load finishes, so the connecting grace remains in force until Playing.
    // Large maps (za_island, mp_battlecity, Wetwork) genuinely take tens of
    // seconds to load.
    //
    // Override without a rebuild: OLMOD_CLIENT_TIMEOUT_MS, OLMOD_CONNECT_TIMEOUT_MS.
    struct SvClientTimeouts
    {
        std::uint32_t connectingMilliseconds{ 45'000 };
        std::uint32_t activeMilliseconds{ 15'000 };
    };

    struct SessionRosterMember
    {
        std::uint64_t xuid{};
        std::string username;

        bool operator==(const SessionRosterMember &) const = default;
    };

    // OLMOD(client-system-source-owner): source coordinator spanning recovered
    // netchan/snapshot responsibilities and explicit backend/gameplay adapters;
    // no method or data-member layout is asserted as a native CODOL class.
    // THE ROUND THE ZM HUD SHOWS. Set by the gametype script through `zmsetround`;
    // publishZmRoundHud re-sends the four `ui_hud_*` dvars to every settled client
    // whenever it changes.
    void SV_SetZmRound(std::uint32_t round, std::uint32_t goal);

    class SvClientSystem
    {
    public:
        using GameStateBuilder = std::function<std::vector<std::uint8_t>(
            const SvGameState &,
            std::uint32_t clientNum,
            std::uint32_t reliableSequence)>;
        using SnapshotBuilder = std::function<std::vector<std::uint8_t>(
            const SvSnapshotFrame &,
            const SvSnapshotFrame *baseline,
            std::uint32_t clientNum,
            std::uint8_t deltaMessageDistance,
            bool initializeBaselineCache,
            const SvClientPrediction *clientPrediction)>;
        using LoadoutProvider = std::function<std::optional<SvResolvedLoadout>(
            std::uint64_t xuid,
            std::string_view selectedLoadout)>;

        explicit SvClientSystem(
            std::size_t maxClients = 18,
            std::uint32_t challengeLifetimeMilliseconds = 30'000,
            GameStateBuilder gameStateBuilder = {},
            SnapshotBuilder snapshotBuilder = {},
            SvClientTimeouts timeouts = {});

        ConnectionlessResult SV_ConnectionlessPacket(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        ClientPacketResult SV_PacketEvent(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds);
        [[nodiscard]] std::vector<SvClientMessage> SV_SendClientMessages(
            std::uint32_t nowMilliseconds,
            std::size_t maximumBytesPerFrame =
                std::numeric_limits<std::size_t>::max());
        std::size_t SV_CheckTimeouts(std::uint32_t nowMilliseconds);

        // AUTOMATED BRING-UP ONLY. Selects a class for any Active client that has not
        // picked one, exactly as if the client's own changeclass menu had answered, so
        // a headless test can reach a spawned player with nobody at the keyboard.
        // Returns the number of clients it picked for. Off unless OLMOD_AUTO_LOADOUT=1.
        std::size_t autoSelectMissingLoadouts(std::uint32_t nowMilliseconds);

        struct TimeoutDrop
        {
            // WHY the slot was released. A timeout is the ~15s silence sweep; a
            // leave is the reliable `leave` command out.exe sends the instant the
            // player presses exit. Both free the slot the same way, but the log
            // and any future match-end bookkeeping want to tell them apart.
            enum class Cause : std::uint8_t { Timeout, Leave };
            std::uint32_t clientNum{};
            std::uint64_t xuid{};
            ClientState state{ ClientState::Free };
            std::uint32_t lastPacketTime{};
            std::uint32_t profileStatsReceivedMask{};
            std::uint32_t profileStatsRequiredMask{};
            bool profileStatsComplete{};
            std::uint32_t gameStateUpdateStage{};
            std::uint64_t sessionGeneration{};
            bool sessionGenerationActive{};
            std::uint32_t messageAcknowledge{};
            std::uint32_t reliableAcknowledge{};
            Cause cause{ Cause::Timeout };
        };
        [[nodiscard]] std::vector<TimeoutDrop> takeTimeoutDrops();
        // Release one client slot and record the drop, the single path both the
        // timeout sweep and the explicit `leave` command go through so a leaving
        // player is removed exactly like a timed-out one -- immediately, not after
        // the silence window.
        void dropClientSlot(std::size_t clientNum, TimeoutDrop::Cause cause);
        void reset();
        bool configureGameState(
            SvGameState gameState,
            std::uint64_t sessionGeneration = 0);
        bool setWorldFrame(
            SvSnapshotFrame frame,
            SvSnapshotFrameValidationFailure *failure = nullptr);
        void clearWorldFrame();
        void setGameplayAuthorityReady(bool ready);
        [[nodiscard]] bool stageSessionRoster(
            std::uint64_t generation,
            std::span<const SessionRosterMember> members);
        [[nodiscard]] bool commitSessionRoster(std::uint64_t generation);
        [[nodiscard]] bool rollbackSessionRoster(std::uint64_t generation);
        // Append one modular weapon into the live gamestate's dynamic block
        // (dense, contiguous) and BROADCAST its config string to every connected
        // client via the '%' update command -- the retail behaviour, no world
        // rebuild. Safe because the appended block is byte-identical to what
        // SessionStart builds (no strip, §161a), so the slot equals each client's
        // next-free registration index and the 181 check passes
        // ([[codol-181-is-weapon-index-vs-slot]]). The builder turns
        // (assetIndex, spec) into the reliable command payload; it lives in
        // Appmain because it needs the engine MsgWriter. Returns the weapon asset
        // index, or nullopt if the gamestate is not configured or full.
        using WeaponConfigStringCommandBuilder =
            std::function<std::vector<std::uint8_t>(
                std::uint16_t, const SvModularWeaponConfigString &)>;
        [[nodiscard]] std::optional<std::uint16_t> registerDynamicWeaponConfigString(
            SvModularWeaponConfigString configString,
            std::uint16_t firstDynamicWeaponAssetIndex,
            const WeaponConfigStringCommandBuilder &buildCommand);
        [[nodiscard]] std::optional<SvResolvedLoadout> resolveAndCommitPendingLoadout(
            std::uint32_t clientNum,
            const LoadoutProvider &provider);

        [[nodiscard]] std::size_t connectedClientCount() const;
        [[nodiscard]] std::size_t pendingChallengeCount(std::uint32_t nowMilliseconds) const;
        [[nodiscard]] std::size_t activeClientCount() const;
        [[nodiscard]] std::size_t gameStateReadyClientCount() const;
        [[nodiscard]] bool gameStateConfigured() const;
        [[nodiscard]] std::uint32_t gameStateMessagesSent() const;
        [[nodiscard]] std::uint32_t gameStateUpdatesReceived() const;
        [[nodiscard]] std::uint32_t snapshotMessagesSent() const;
        [[nodiscard]] std::uint32_t fullSnapshotMessagesSent() const;
        [[nodiscard]] std::uint32_t deltaSnapshotMessagesSent() const;
        [[nodiscard]] std::uint32_t latestMessageAcknowledge() const;
        [[nodiscard]] std::uint32_t latestOutgoingSequence() const;
        [[nodiscard]] std::optional<ClientIngressStatus> clientIngressStatus(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<ServerReliableCommandStatus>
            serverReliableCommandStatus(
                std::uint32_t clientNum,
                std::size_t maximumCommands = 32) const;
        [[nodiscard]] std::vector<UserCmd> pendingUserCmds(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<UserCmd> dispatchNextPendingUserCmd(
            std::uint32_t clientNum);
        [[nodiscard]] bool commitExecutedUserCmd(
            std::uint32_t clientNum,
            std::uint32_t commandTime);
        [[nodiscard]] bool discardUnsupportedUserCmd(
            std::uint32_t clientNum,
            std::uint32_t commandTime);
        [[nodiscard]] bool discardRejectedUserCmd(
            std::uint32_t clientNum,
            std::uint32_t commandTime);
        [[nodiscard]] const std::vector<ClientSlot> &clients() const;

        [[nodiscard]] bool queueReliableCommand(
            std::uint32_t clientNum,
            std::string command);
        // Preflight a contiguous reliable-command reservation. Callers that
        // must commit a world transaction only after its native command can be
        // queued use this while holding their ServerCore transaction lock.
        [[nodiscard]] bool canQueueReliableCommands(
            std::uint32_t clientNum,
            std::size_t count = 1) const;
        // The LIVE configstring update - verb `d`, the capability this server
        // has never had (HANDOFF section 107b). Writes the value into the
        // gamestate so anyone who connects later reads it there, and pushes
        // `d <index> <value>` to everyone who already has a gamestate. Returns
        // the number of clients it was queued to; 0 when nothing changed.
        std::size_t SV_SetConfigString(std::uint16_t index, std::string value);
        [[nodiscard]] std::optional<std::string> configString(
            std::uint16_t index) const;
        [[nodiscard]] bool queueReliableBinaryCommand(
            std::uint32_t clientNum,
            std::vector<std::uint8_t> payload);
        [[nodiscard]] bool queueLocalSound(
            std::uint32_t clientNum,
            std::uint16_t eventParameter);
        [[nodiscard]] bool beginNextRound(bool switchTeams);
        [[nodiscard]] bool setTeamScore(SvTeam team, std::int32_t score);
        [[nodiscard]] bool setClientScore(
            std::uint32_t clientNum,
            SvClientScore score);
        [[nodiscard]] bool addClientScore(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] bool addClientKills(
            std::uint32_t clientNum,
            std::int32_t delta);
        // Deaths are a scoreboard column, never a limit. Unlike kills they are
        // not awarded by script - dm.lua has no counterpart to addkill for the
        // victim - so the server counts them itself off the kill event.
        [[nodiscard]] bool addClientDeaths(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] bool addClientDowns(std::uint32_t clientNum);
        [[nodiscard]] bool addClientRevives(std::uint32_t clientNum);
        [[nodiscard]] bool addClientHeadshots(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] bool addClientStreak(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] bool addClientXp(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] std::optional<SvClientScore> clientScore(
            std::uint32_t clientNum) const;
        // Broadcasts the retail "player joined" line for any client that has
        // become active since the last call.
        void announceConnectionChanges();
        // The client only ever asks for the scoreboard with a reliable 's', so a
        // server-side event that changes it - the match ending - has to push it.
        void publishZmRoundHud(std::uint32_t frameNumber);
        void pushScoreboardToConnected();
        // Retail marks the root AAR transaction complete with
        // aarRoundNumber=1 on the match-ending frame.
        void setAarRoundNumber(std::int32_t roundNumber);
        // The highest KILL COUNT in the match and the slot holding it, over
        // connected clients only. Free-for-all is scored per player, and because
        // every FFA player is teamless every TEAM score stays 0 - so a team-scored
        // limit can never fire and this is what the limit has to read instead.
        //
        // Kills, not score: a kill awards display points while the shipped
        // limit is 30, so comparing the limit against the score ends the match on
        // the first kill. cha avoids this by counting its limit on addteamscore's
        // 1-per-kill, which is exactly what this mirrors. Ties resolve to the
        // player with fewer deaths and then the lowest slot, matching the
        // shipped FFA placement ordering while keeping the result deterministic.
        [[nodiscard]] std::optional<std::pair<std::uint32_t, std::int32_t>>
            bestClientKills() const;
        // The first `count` clients by kills, best first. Equal kills prefer
        // fewer deaths and then the lower slot, exactly as bestClientKills
        // does, so the limit, outcome and podium never disagree.
        [[nodiscard]] std::vector<std::pair<std::uint32_t, std::int32_t>>
            topClientsByKills(std::size_t count) const;
        [[nodiscard]] bool addTeamScoreForClient(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] std::optional<std::int32_t> teamScore(SvTeam team) const;

    private:
        struct SessionRoster
        {
            std::uint64_t generation{};
            std::vector<SessionRosterMember> members;
        };

        struct ChallengeRecord
        {
            bool valid{};
            bool connected{};
            PeerAddress peer{};
            std::uint64_t xuid{};
            std::uint64_t sessionGeneration{};
            std::uint32_t challenge{};
            std::uint32_t issuedTime{};
        };

        static constexpr std::size_t ChallengeCapacity = 1024;

        ChallengeRecord &SV_GetChallenge(
            PeerAddress peer,
            std::uint64_t xuid,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        ChallengeRecord *findChallenge(
            PeerAddress peer,
            std::uint64_t xuid,
            std::uint32_t challenge,
            std::uint32_t nowMilliseconds);
        ConnectionlessResult SV_GetChallenge(
            PeerAddress peer,
            std::string_view arguments,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        ConnectionlessResult SV_DirectConnect(
            PeerAddress peer,
            std::string_view arguments,
            std::uint32_t nowMilliseconds);
        ConnectionlessResult SV_ProfileStats(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds);
        ConnectionlessResult SV_GameStateUpdate(
            PeerAddress peer,
            std::string_view arguments,
            std::uint32_t nowMilliseconds);
        [[nodiscard]] std::vector<std::uint8_t> buildSnapshotMessage(
            ClientSlot &client,
            std::uint32_t clientNum);
        void queueScoreboardResponse(std::uint32_t clientNum);
        bool commitPendingLoadout(
            std::uint32_t clientNum,
            std::uint32_t pendingSequence);
        [[nodiscard]] bool sessionAllowsXuid(std::uint64_t xuid) const;
        [[nodiscard]] const SessionRoster *sessionRosterForGeneration(
            std::uint64_t generation) const;
        [[nodiscard]] const SessionRosterMember *sessionMemberForXuid(
            const SessionRoster &roster,
            std::uint64_t xuid) const;
        [[nodiscard]] std::uint64_t sessionGenerationForXuid(
            std::uint64_t xuid) const;
        [[nodiscard]] bool clientGenerationIsActive(const ClientSlot &client) const;

        std::vector<ChallengeRecord> challenges_;
        std::vector<ClientSlot> clients_;
        // 12.132: per-client round-HUD publication state.
        std::map<std::uint32_t, std::uint32_t> zmRoundHudFirstFrame_;
        std::map<std::uint32_t, std::uint32_t> zmRoundHudSent_;
        std::vector<TimeoutDrop> timeoutDrops_;
        std::optional<SessionRoster> pendingRoster_;
        std::optional<SessionRoster> activeRoster_;
        // clientNum -> the ENCODED name it was announced under. The name has
        // to outlive the slot: a client is announced as gone once its slot is
        // already Free, and by then its roster entry is not reachable.
        std::map<std::uint32_t, std::string> connectionAnnounced_;
        std::uint32_t challengeLifetimeMilliseconds_;
        SvClientTimeouts timeouts_;
        std::uint32_t nonce_{};
        GameStateBuilder gameStateBuilder_;
        SnapshotBuilder snapshotBuilder_;
        // Whether this match has sides at all. Derived in one place so the class
        // menu and the loadout commit cannot disagree about it - they gate on the
        // same SvTeam::None and would otherwise have to each know the gametype.
        [[nodiscard]] SvTeamPolicy teamPolicy() const
        {
            return gameState_.gameType == "dm"
                ? SvTeamPolicy::FreeForAll
                : SvTeamPolicy::Teams;
        }

        SvGameState gameState_;
        std::shared_ptr<const SvSnapshotFrame> worldFrame_;
        bool gameStateConfigured_{};
        bool worldFrameConfigured_{};
        bool gameplayAuthorityReady_{};
        std::array<std::int32_t, 2> teamScores_{};
        std::vector<SvClientScore> clientScores_;
        std::int32_t aarRoundNumber_{};
        std::uint32_t gameStateMessagesSent_{};
        std::uint32_t gameStateUpdatesReceived_{};
        std::uint32_t snapshotMessagesSent_{};
        std::uint32_t fullSnapshotMessagesSent_{};
        std::uint32_t deltaSnapshotMessagesSent_{};
        // OLMOD(snapshot-send-ring): source-owned cursor implementing the
        // native cross-client fairness responsibility without claiming a
        // CODOL serverStatic_t layout.
        std::size_t nextSnapshotSendClient_{};
    };
}
