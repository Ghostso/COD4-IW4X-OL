#include <atomic>
#include "sv_client_mp.hpp"

#include "../../shared/RuntimeLog.hpp"

#include "qcommon/com_math.hpp"
#include "sv_scoreboard_mp.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <iterator>
#include <limits>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <iostream>

namespace CodolGameServer
{
    namespace
    {
        // OLMOD(section-85): off by default, and read ONCE. See the capture site
        // in SV_ProcessClientPacket for what it is for and why a captured sample
        // is the only oracle this direction of the wire has.
        bool userCmdSampleCaptureEnabled()
        {
            static const bool enabled = [] {
                const auto *const value = std::getenv("OLMOD_USERCMD_SAMPLE");
                return value && value[0] == '1' && value[1] == '\0';
            }();
            return enabled;
        }
    }

    std::string_view SV_SnapshotAssemblyFailureName(
        const SvSnapshotAssemblyFailure failure)
    {
        switch (failure)
        {
        case SvSnapshotAssemblyFailure::None:
            return "none";
        case SvSnapshotAssemblyFailure::WorldFrameUnavailable:
            return "world_frame_unavailable";
        case SvSnapshotAssemblyFailure::SnapshotBuilderUnavailable:
            return "snapshot_builder_unavailable";
        case SvSnapshotAssemblyFailure::DuplicateServerTime:
            return "duplicate_server_time";
        case SvSnapshotAssemblyFailure::SnapshotBuilderEmpty:
            return "snapshot_builder_empty";
        case SvSnapshotAssemblyFailure::NetchanTransmitEmpty:
            return "netchan_transmit_empty";
        }
        return "unknown";
    }

    std::optional<std::string> SV_BuildPlayLocalSoundCommand(
        const std::uint16_t eventParameter)
    {
        if (!eventParameter || eventParameter > LocalSoundEventParameterMaximum)
            return std::nullopt;
        return "p " + std::to_string(eventParameter);
    }

    namespace
    {
        constexpr std::uint8_t OobPrefix[]{ 0xFF, 0xFF, 0xFF, 0xFF };
        constexpr std::uint8_t ProfileStatsPrefix[]{
            0xFF, 0xFF, 0xFF, 0xFF, 's', 't', 'a', 't', 's', 0,
        };
        constexpr std::size_t ProfileStatsChunkCount = 27;
        constexpr std::size_t ProfileStatsChunkSize = 1238;

        bool isLanPeer(const PeerAddress peer)
        {
            const auto first = static_cast<std::uint8_t>(peer.ipv4 >> 24);
            const auto second = static_cast<std::uint8_t>(peer.ipv4 >> 16);
            return first == 10 || first == 127 ||
                (first == 169 && second == 254) ||
                (first == 172 && second >= 16 && second <= 31) ||
                (first == 192 && second == 168);
        }

        bool timePrecedes(
            const std::uint32_t nowMilliseconds,
            const std::uint32_t targetMilliseconds)
        {
            return static_cast<std::int32_t>(
                nowMilliseconds - targetMilliseconds) < 0;
        }

        // TODO(CODOL): replace temporary handshake diagnostics with the
        // structured runtime event stream once the two-client path is stable.
        std::unordered_map<std::uint64_t, std::uint8_t> challengeDiagnostics;

        void appendLittleU32(
            std::vector<std::uint8_t> &output,
            const std::uint32_t value)
        {
            output.push_back(static_cast<std::uint8_t>(value));
            output.push_back(static_cast<std::uint8_t>(value >> 8));
            output.push_back(static_cast<std::uint8_t>(value >> 16));
            output.push_back(static_cast<std::uint8_t>(value >> 24));
        }

        void appendLittleU16(
            std::vector<std::uint8_t> &output,
            const std::uint16_t value)
        {
            output.push_back(static_cast<std::uint8_t>(value));
            output.push_back(static_cast<std::uint8_t>(value >> 8));
        }

        void appendPendingServerCommands(
            std::vector<std::uint8_t> &output,
            const ClientSlot &client)
        {
            for (auto sequence = client.netchan.reliableAcknowledge + 1;
                 sequence <= client.reliableSequence;
                 ++sequence)
            {
                const auto &command = client.reliableCommands[
                    sequence & (ServerReliableCommandCapacity - 1)];
                output.push_back(command.kind == ServerReliableCommandKind::Binary
                    ? ServerCommandReliableBinary
                    : ServerCommandReliable);
                appendLittleU32(output, sequence);
                if (command.kind == ServerReliableCommandKind::Binary)
                {
                    appendLittleU16(
                        output, static_cast<std::uint16_t>(command.payload.size()));
                    output.insert(
                        output.end(), command.payload.begin(), command.payload.end());
                }
                else
                {
                    output.insert(
                        output.end(), command.text.begin(), command.text.end());
                    output.push_back(0);
                }
            }
        }

        std::optional<std::string_view> takeCommandToken(std::string_view &command)
        {
            const auto start = command.find_first_not_of(" \t\r\n");
            if (start == std::string_view::npos)
            {
                command = {};
                return std::nullopt;
            }
            command.remove_prefix(start);
            const auto end = command.find_first_of(" \t\r\n");
            const auto token = command.substr(0, end);
            command = end == std::string_view::npos ? std::string_view{} : command.substr(end);
            return token;
        }

        bool parseUnsignedCommandToken(
            const std::string_view token,
            std::uint32_t &value)
        {
            const auto result = std::from_chars(token.data(), token.data() + token.size(), value);
            return result.ec == std::errc{} && result.ptr == token.data() + token.size();
        }

        std::uint32_t readLittleU32(
            const std::span<const std::uint8_t> data,
            const std::size_t offset)
        {
            return static_cast<std::uint32_t>(data[offset]) |
                static_cast<std::uint32_t>(data[offset + 1]) << 8 |
                static_cast<std::uint32_t>(data[offset + 2]) << 16 |
                static_cast<std::uint32_t>(data[offset + 3]) << 24;
        }

        UserCmd defaultUserCmdFromFrame(
            const SvSnapshotFrame &frame,
            const std::uint32_t clientNum)
        {
            UserCmd result;
            const auto playerState = std::find_if(
                frame.playerStates.begin(),
                frame.playerStates.end(),
                [clientNum](const SvPlayerState &state) {
                    return state.clientNum == clientNum;
                });
            if (playerState == frame.playerStates.end())
                return result;
            return SV_DefaultUserCmdFromPlayerState(*playerState);
        }

        struct ParsedMessage
        {
            std::string command;
            std::string_view arguments;
        };

        std::string_view trimLeft(std::string_view value)
        {
            const auto first = value.find_first_not_of(" \t\r\n");
            return first == std::string_view::npos ? std::string_view{} : value.substr(first);
        }

        std::optional<ParsedMessage> parseMessage(const std::span<const std::uint8_t> packet)
        {
            if (packet.size() < std::size(OobPrefix) ||
                !std::equal(std::begin(OobPrefix), std::end(OobPrefix), packet.begin()))
            {
                return std::nullopt;
            }

            auto body = std::string_view(
                reinterpret_cast<const char *>(packet.data() + std::size(OobPrefix)),
                packet.size() - std::size(OobPrefix));
            if (const auto terminator = body.find('\0'); terminator != std::string_view::npos)
                body = body.substr(0, terminator);
            body = trimLeft(body);
            if (body.empty())
                return std::nullopt;

            const auto separator = body.find_first_of(" \t\r\n");
            auto command = std::string(body.substr(0, separator));
            std::transform(command.begin(), command.end(), command.begin(), [](const unsigned char value) {
                return static_cast<char>(std::tolower(value));
            });
            const auto arguments = separator == std::string_view::npos
                ? std::string_view{}
                : trimLeft(body.substr(separator));
            return ParsedMessage{ std::move(command), arguments };
        }

        std::optional<std::string_view> takeToken(std::string_view &input)
        {
            input = trimLeft(input);
            if (input.empty())
                return std::nullopt;
            const auto separator = input.find_first_of(" \t\r\n");
            const auto token = input.substr(0, separator);
            input = separator == std::string_view::npos
                ? std::string_view{}
                : input.substr(separator);
            return token;
        }

        std::optional<std::string_view> takeQuoted(std::string_view &input)
        {
            input = trimLeft(input);
            if (input.size() < 2 || input.front() != '"')
                return std::nullopt;
            const auto closing = input.find_last_of('"');
            if (!closing)
                return std::nullopt;
            const auto value = input.substr(1, closing - 1);
            if (!trimLeft(input.substr(closing + 1)).empty())
                return std::nullopt;
            input = {};
            return value;
        }

        template <typename Integer>
        std::optional<Integer> parseInteger(const std::string_view value, const int base)
        {
            Integer result{};
            const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result, base);
            if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
                return std::nullopt;
            return result;
        }

        std::optional<std::unordered_map<std::string, std::string>> parseUserInfo(
            const std::string_view userInfo)
        {
            if (userInfo.empty() || userInfo.front() != '\\' || userInfo.size() > 1024)
                return std::nullopt;

            std::unordered_map<std::string, std::string> values;
            std::size_t cursor = 1;
            while (cursor <= userInfo.size())
            {
                const auto keyEnd = userInfo.find('\\', cursor);
                if (keyEnd == std::string_view::npos || keyEnd == cursor)
                    return std::nullopt;
                const auto valueStart = keyEnd + 1;
                const auto valueEnd = userInfo.find('\\', valueStart);
                const auto key = userInfo.substr(cursor, keyEnd - cursor);
                const auto value = userInfo.substr(
                    valueStart,
                    valueEnd == std::string_view::npos
                        ? userInfo.size() - valueStart
                        : valueEnd - valueStart);
                values.insert_or_assign(std::string(key), std::string(value));
                if (valueEnd == std::string_view::npos)
                    break;
                cursor = valueEnd + 1;
            }
            return values;
        }

        std::vector<std::uint8_t> makeReply(const std::string_view text)
        {
            std::vector<std::uint8_t> result(std::begin(OobPrefix), std::end(OobPrefix));
            result.insert(result.end(), text.begin(), text.end());
            return result;
        }

        bool expired(
            const std::uint32_t now,
            const std::uint32_t then,
            const std::uint32_t lifetime)
        {
            return now - then > lifetime;
        }

        std::uint32_t mix32(std::uint32_t value)
        {
            value ^= value >> 16;
            value *= 0x7FEB352Du;
            value ^= value >> 15;
            value *= 0x846CA68Bu;
            value ^= value >> 16;
            return value;
        }

        ConnectionlessResult reject(const std::string_view wireReason, const std::string_view reason)
        {
            return {
                .kind = ConnectionlessResultKind::Rejected,
                .reply = makeReply(std::string("error\n") + std::string(wireReason)),
                .reason = std::string(reason),
            };
        }

        bool parseLoadoutNumber(
            const std::string_view response,
            const std::string_view prefix,
            const std::uint32_t first,
            const std::uint32_t last)
        {
            if (!response.starts_with(prefix))
                return false;
            const auto suffix = response.substr(prefix.size());
            std::uint32_t number{};
            return !suffix.empty() && parseUnsignedCommandToken(suffix, number) &&
                number >= first && number <= last;
        }
    }

    std::optional<ClientMenuResponse> SV_ParseMenuResponse(
        std::string_view command,
        const std::uint32_t expectedServerId,
        const SvGameState &gameState)
    {
        const auto name = takeCommandToken(command);
        const auto serverIdToken = takeCommandToken(command);
        const auto menuIndexToken = takeCommandToken(command);
        const auto response = takeCommandToken(command);
        if (!name || *name != "mr" || !serverIdToken || !menuIndexToken || !response ||
            takeCommandToken(command) || response->empty())
        {
            return std::nullopt;
        }

        std::uint32_t serverId{};
        std::uint32_t menuIndex{};
        if (!parseUnsignedCommandToken(*serverIdToken, serverId) ||
            !parseUnsignedCommandToken(*menuIndexToken, menuIndex) ||
            serverId != expectedServerId || menuIndex >= ScriptMenuConfigStringCount)
        {
            return std::nullopt;
        }
        const auto &menu = gameState.scriptMenus[menuIndex];
        if (menu.empty())
            return std::nullopt;
        return ClientMenuResponse{
            .serverId = serverId,
            .menuIndex = menuIndex,
            .menuName = menu,
            .response = std::string(*response),
        };
    }

    bool SV_DispatchMenuResponse(
        ClientSlot &client,
        const ClientMenuResponse &response,
        const SvTeamPolicy teamPolicy,
        const bool allowGenericClassMenu)
    {
        // OLMOD(factory-generic-class-response): the interactive UI may answer
        // the generic changeclass menu even when q2 opened its marines wrapper.
        // out.exe 5C9910/5DD4F0 resolve the RESPONSE menu name independently.
        // Explicit Factory caller policy; never treat back/noop as a class.
        const bool genericClass = allowGenericClassMenu &&
            response.menuName == "changeclass";
        if (client.state != ClientState::Active ||
            (!genericClass && response.menuName != "changeclass_marines" &&
                response.menuName != "changeclass_opfor") ||
            (!parseLoadoutNumber(response.response, "custom", 1, 5) &&
                !parseLoadoutNumber(response.response, "class", 0, 4)))
        {
            return false;
        }
        client.pendingSelectedLoadout = response.response;
        client.pendingLoadoutSequence = response.sequence;
        const auto requestedFaction = genericClass
            ? client.characterFaction
            : (response.menuName == "changeclass_opfor"
                ? SvCharacterFaction::Sc : SvCharacterFaction::Tf);
        // Free-for-all keeps the faction, because that is what picks the player
        // model, but takes no team from it. Teamless is how FFA is represented:
        // SvServerWorld::onSameTeam is false whenever either side is None, so
        // everyone can damage everyone with no special case anywhere else.
        const auto requestedTeam = teamPolicy == SvTeamPolicy::FreeForAll
            ? SvTeam::None
            : (requestedFaction == SvCharacterFaction::Sc
                ? SvTeam::Sc
                : SvTeam::Tf);
        // COD class menus can be replayed by the client after entering the
        // game.  A replay selects a loadout, but does not renegotiate the
        // authoritative team; accepting it here would silently move a player
        // between SD sides and make the round state oscillate.
        if (client.gameplayState == ClientGameplayState::Playing &&
            (client.team == SvTeam::Tf || client.team == SvTeam::Sc))
        {
            client.pendingCharacterFaction = client.characterFaction;
            client.pendingTeam = client.team;
        }
        else
        {
            client.pendingCharacterFaction = requestedFaction;
            client.pendingTeam = requestedTeam;
        }
        return true;
    }

    SvClientSystem::SvClientSystem(
        const std::size_t maxClients,
        const std::uint32_t challengeLifetimeMilliseconds,
        GameStateBuilder gameStateBuilder,
        SnapshotBuilder snapshotBuilder,
        const SvClientTimeouts timeouts)
        : challenges_(ChallengeCapacity),
          clients_(maxClients),
          challengeLifetimeMilliseconds_(challengeLifetimeMilliseconds),
          timeouts_(timeouts),
          gameStateBuilder_(std::move(gameStateBuilder)),
          snapshotBuilder_(std::move(snapshotBuilder)),
          clientScores_(maxClients)
    {
        if (!maxClients)
            throw std::invalid_argument("server must have at least one client slot");
        if (!challengeLifetimeMilliseconds)
            throw std::invalid_argument("challenge lifetime must be non-zero");
        // Let a live session retune these without a rebuild -- a player who keeps
        // crashing wants the seat back NOW, and a bad network wants the opposite.
        // Bounded at 1..600000: a zero would disable the timeout entirely and
        // strand every crashed client's slot forever, which is the bug this is
        // here to fix.
        const auto fromEnvironment = [](const char *const name,
                                         std::uint32_t &target) {
            std::array<char, 16> value{};
            std::size_t length{};
            if (getenv_s(&length, value.data(), value.size(), name) != 0 ||
                length <= 1)
            {
                return;
            }
            std::uint32_t parsed{};
            const auto *const first = value.data();
            const auto *const last = first + std::strlen(value.data());
            const auto [pointer, error] = std::from_chars(first, last, parsed);
            if (error != std::errc{} || pointer != last || !parsed ||
                parsed > 600'000)
            {
                return;
            }
            target = parsed;
        };
        fromEnvironment("OLMOD_CLIENT_TIMEOUT_MS", timeouts_.activeMilliseconds);
        fromEnvironment(
            "OLMOD_CONNECT_TIMEOUT_MS", timeouts_.connectingMilliseconds);
        if (!timeouts_.connectingMilliseconds || !timeouts_.activeMilliseconds)
            throw std::invalid_argument("client timeouts must be non-zero");
    }

    ConnectionlessResult SvClientSystem::SV_ConnectionlessPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        if (packet.size() > 4096)
            return reject("EXE_CONNECT_PACKET_TOO_LARGE", "connectionless packet exceeds 4096 bytes");
        if (packet.size() >= std::size(ProfileStatsPrefix) &&
            std::equal(
                std::begin(ProfileStatsPrefix),
                std::end(ProfileStatsPrefix),
                packet.begin()))
        {
            return SV_ProfileStats(peer, packet, nowMilliseconds);
        }
        const auto message = parseMessage(packet);
        if (!message)
            return {};
        if (message->command == "getchallenge")
            return SV_GetChallenge(peer, message->arguments, nowMilliseconds, entropy);
        if (message->command == "connect")
            return SV_DirectConnect(peer, message->arguments, nowMilliseconds);
        if (message->command == "gamestateupdate")
            return SV_GameStateUpdate(peer, message->arguments, nowMilliseconds);
        if (message->command == "heartbeat")
            return { .kind = ConnectionlessResultKind::Reply, .reply = makeReply("heartbeatresponse") };
        return {};
    }

    ConnectionlessResult SvClientSystem::SV_ProfileStats(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds)
    {
        constexpr auto HeaderSize = std::size(ProfileStatsPrefix) + 3;
        if (packet.size() <= HeaderSize || packet.size() - HeaderSize > ProfileStatsChunkSize)
            return reject("EXE_BAD_STATS", "profile stats chunk has an invalid size");

        const auto chunkIndex = packet[std::size(ProfileStatsPrefix)];
        if (chunkIndex >= ProfileStatsChunkCount)
            return reject("EXE_BAD_STATS", "profile stats chunk index is out of range");

        const auto slot = std::find_if(clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
            return client.state != ClientState::Free && client.peer == peer;
        });
        if (slot == clients_.end())
            return reject("EXE_BAD_STATS", "profile stats arrived before direct connect");

        const auto chunkBit = 1u << chunkIndex;
        slot->profileStatsReceivedMask |= chunkBit;
        const auto payloadSize = packet.size() - HeaderSize;
        if (payloadSize < ProfileStatsChunkSize)
            slot->profileStatsRequiredMask = (chunkBit << 1) - 1;
        const auto remainingMask =
            slot->profileStatsRequiredMask & ~slot->profileStatsReceivedMask;
        slot->profileStatsComplete = remainingMask == 0;
        slot->lastPacketTime = nowMilliseconds;

        return {
            .kind = ConnectionlessResultKind::Reply,
            .reply = makeReply("statResponse " + std::to_string(remainingMask)),
            .clientSlot = static_cast<std::size_t>(slot - clients_.begin()),
        };
    }

    ConnectionlessResult SvClientSystem::SV_GameStateUpdate(
        const PeerAddress peer,
        std::string_view arguments,
        const std::uint32_t nowMilliseconds)
    {
        const auto stageText = takeToken(arguments);
        const auto stage = stageText ? parseInteger<std::uint32_t>(*stageText, 10) : std::nullopt;
        if (!stage || *stage < 1 || *stage > 6 || !trimLeft(arguments).empty())
            return {};

        const auto slot = std::find_if(clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
            return client.state != ClientState::Free && client.peer == peer;
        });
        if (slot == clients_.end() || slot->state < ClientState::ClientLoading)
            return {};
        if (*stage < slot->gameStateUpdateStage ||
            *stage > slot->gameStateUpdateStage + 1)
        {
            return {};
        }

        slot->lastPacketTime = nowMilliseconds;
        if (*stage > slot->gameStateUpdateStage)
        {
            slot->gameStateUpdateStage = *stage;
            ++gameStateUpdatesReceived_;
        }
        if (slot->gameStateUpdateStage == 6)
        {
            slot->state = ClientState::Active;
            // CODREF(sv_client_enter_world): BO1/Kisak SV_ClientEnterWorld and
            // Ghosts 0x1401F2210 both schedule the first
            // active snapshot from the current server time. Reusing the
            // zero-initialized field breaks wrap-safe comparisons once the
            // host tick count is more than INT32_MAX milliseconds old.
            slot->nextSnapshotTime = nowMilliseconds;
            // AND THE RESET THAT HAS TO COME WITH IT -- `client->deltaMessage = -1`.
            // Section 167: this branch cited SV_ClientEnterWorld for the snapshot
            // schedule and took only that line from it. A CLIENT ENTERING THE WORLD HAS
            // JUST THROWN ITS SNAPSHOT STATE AWAY: it loaded the map, reinitialised
            // cgame -- which is what re-deals every characterInfo name buffer out of a
            // freshly memset pool (0x004555D0) -- and remembers nothing it acknowledged
            // while it was loading. Every one of those acknowledgements was still being
            // used here as a delta baseline.
            //
            // MEASURED, both ends of the same frame. The dedicated wrote each observer
            // its clientInfos ONCE and then skipped them forever, correctly, because its
            // baseline said the client already knew:
            //     clientinfo WIRE observer=0 baseline=NONE  0:model6/item545(FULL)
            //     clientinfo WIRE observer=1 baseline=NONE  0:model6/item545(FULL)
            //     clientinfo WIRE observer=0 baseline=yes   0:model6/item545(skipped)
            //     clientinfo WIRE observer=1 baseline=yes   0:model6/item545(skipped)
            // while inside one of the two clients every entry sat at
            //     req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY
            // -- present, flagged for rebuild, and with no model index, which is
            // CG_SetupClientCharacterInfo 0x00541800's one early return. So that client
            // never wrote a model name again and nobody could see that player. Which
            // client it bit depended only on whether it acknowledged a snapshot before
            // entering the world, which is why it looked random and moved between
            // players from run to run.
            //
            // The persistent entity-baseline cache has to go with it: leaving
            // baselineCacheAcknowledged set would hand the very next snapshot
            // `baselineFrame` and undo this completely, since that path does not consult
            // deltaMessage at all. The client's cache died with its map load.
            slot->deltaMessage = -1;
            slot->snapshotHistory = {};
            slot->baselineCacheAcknowledged = false;
            slot->baselineCacheInitializationMessage.reset();
            // Section 170: the client's flat entity array died with its map load too --
            // CL_ClearState zeroes dword_C89E050 and its cursor at 0x005becb0/0x005bec9c.
            // Cleared beside snapshotHistory because they describe one generation: keeping
            // it would let the next selection name a flagged frame from the previous life
            // of this connection, which is the defect with extra steps.
            slot->newestFlaggedSnapshotMessage.reset();
            slot->baselineFrame.reset();
            if (slot->gameplayState == ClientGameplayState::Inactive)
                slot->gameplayState = ClientGameplayState::WaitingForLoadout;
        }
        return {
            .kind = ConnectionlessResultKind::ClientProgress,
            .clientSlot = static_cast<std::size_t>(slot - clients_.begin()),
        };
    }

    ClientPacketResult SvClientSystem::SV_PacketEvent(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds)
    {
        // CODREF(sv_user_move): BO1/Ghosts/BO2 SV_ExecuteClientMessage and
        // SV_UserMove resolve one connected client, decode netchan state and
        // admit a bounded ordered usercmd batch before game-side dispatch.
        const auto slot = std::find_if(clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
            return client.state != ClientState::Free && client.peer == peer;
        });
        if (slot == clients_.end())
        {
            return {
                .kind = NetchanProcessKind::Rejected,
                .reason = "netchan packet has no connected client slot",
            };
        }

        const auto slotIndex = static_cast<std::size_t>(slot - clients_.begin());
        // CODDIFF(sv_user_move): source snapshot history owns immutable frames,
        // not native client_t frame-ring offsets. An exact acknowledged frame
        // is preferred; the latest world frame is the current compatibility
        // baseline when that archive generation is unavailable.
        const auto defaultUserCmdResolver = [&](const std::uint32_t messageAcknowledge) {
            const auto &entry = slot->snapshotHistory[
                messageAcknowledge % SnapshotHistoryCapacity];
            if (entry.valid && entry.frame &&
                entry.messageNum == messageAcknowledge)
            {
                return defaultUserCmdFromFrame(
                    *entry.frame, static_cast<std::uint32_t>(slotIndex));
            }
            if (worldFrameConfigured_ && worldFrame_)
            {
                return defaultUserCmdFromFrame(
                    *worldFrame_, static_cast<std::uint32_t>(slotIndex));
            }
            return UserCmd{};
        };
        // OLMOD(reliable-key-desync-witness): SAY WHICH BRANCH TOOK THE KEY AWAY.
        //
        // A REMOTE client wedged permanently mid-match 2026-08-25 (HANDOFF 150e): its ack
        // counter froze at 1835/103 and never moved again while two local clients carried on,
        // and it posted no ClientException because a netchan that no longer decodes cannot
        // carry one. The freeze correlates exactly with the DEATH/RESPAWN reliable burst --
        // eight commands in three seconds, SIX of them on one serverTime.
        //
        // Both non-(B) branches below can wedge a client for good, and neither says so:
        //   nullopt      the packet is rejected. If the client keeps acking that same number,
        //                every future packet is rejected too -- a permanent one-way freeze.
        //   empty key    the XOR key diverges from the one the client used, so every later
        //                packet decodes to garbage. Also permanent.
        // A local client acks instantly and its gap never grows; a remote one, mid-burst, is
        // exactly where a gap comes from -- which is why this has only ever bitten remotely.
        //
        // Silent while healthy, and it reports the VALUES rather than a verdict: whichever
        // branch fires names itself, instead of a fourth guess being made about which did.
        const auto reliableCommandResolver = [&](const std::uint32_t reliableAcknowledge)
            -> std::optional<std::string> {
            if (reliableAcknowledge > slot->reliableSequence)
            {
                if (slot->reliableKeyComplaints < ReliableKeyComplaintLimit)
                {
                    ++slot->reliableKeyComplaints;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "reliable key REJECTED client=" +
                            std::to_string(static_cast<std::uint32_t>(slotIndex)) +
                            " xuid=" + std::to_string(slot->xuid) +
                            " ack=" + std::to_string(reliableAcknowledge) +
                            " > serverSequence=" + std::to_string(slot->reliableSequence) +
                            " -- this packet is dropped, and if the client keeps acking this "
                            "number every later packet is dropped too (HANDOFF 150e)");
                }
                return std::nullopt;
            }
            if (reliableAcknowledge && reliableAcknowledge <= slot->reliableSequence &&
                slot->reliableSequence - reliableAcknowledge <
                    ServerReliableCommandCapacity)
            {
                return std::string(slot->reliableCommands[
                    reliableAcknowledge & (ServerReliableCommandCapacity - 1)].xorKey());
            }
            // ack==0 is the ordinary pre-first-command case and is CORRECT here. A non-zero
            // ack reaching this line is a stale-gap desync and is not.
            if (reliableAcknowledge &&
                slot->reliableKeyComplaints < ReliableKeyComplaintLimit)
            {
                ++slot->reliableKeyComplaints;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "reliable key EMPTY client=" +
                        std::to_string(static_cast<std::uint32_t>(slotIndex)) +
                        " xuid=" + std::to_string(slot->xuid) +
                        " ack=" + std::to_string(reliableAcknowledge) +
                        " serverSequence=" + std::to_string(slot->reliableSequence) +
                        " gap=" + std::to_string(slot->reliableSequence - reliableAcknowledge) +
                        " capacity=" + std::to_string(ServerReliableCommandCapacity) +
                        " -- the client keyed on a real command and this side keyed on nothing; "
                        "every later packet decodes to garbage (HANDOFF 150e)");
            }
            return std::string{};
        };
        auto processed = Netchan_Process(
            slot->netchan,
            packet,
            slot->challenge,
            gameStateConfigured_ ? gameState_.checksumFeed : 0,
            {},
            {},
            reliableCommandResolver,
            defaultUserCmdResolver);
        // OLMOD(section-85): CAPTURE ONE REAL USERCMD SAMPLE, BECAUSE THE GOLDEN
        // NEEDS A CAPTURED ONE AND HAS NEVER HAD IT.
        //
        // The two red goldens (section 58f) are red because their wire sample is
        // HAND-BUILT and encodes the three weapon-index deltas at TEN bits where
        // this build reads ELEVEN. Section 58f rejected both cheap repairs for
        // stated reasons: an offline Python mirror disagreed with the reader at
        // the first keyed bit, and building the writer inside the test is the
        // symmetric round trip section 51j proved passes even when both sides are
        // wrong.
        //
        // A CAPTURED sample is neither. The bytes come from a real CODOL client,
        // so the test would compare this reader against the shipped WRITER --
        // which is the only independent oracle that exists for this direction of
        // the wire, because a demo records what a server SENDS and contains no
        // usercmds at all.
        //
        // Everything the test needs is already in the result: `decodedCommands`
        // is the de-XORed command stream, and the baseline the first command
        // deltas against is whatever `defaultUserCmdResolver` returns for this
        // packet's messageAcknowledge. Capture both, plus the decoded values, so
        // the golden's expectations are transcribed rather than invented.
        //
        // Gated on OLMOD_USERCMD_SAMPLE and on a command that actually EXERCISES
        // the eleven-bit fields -- an idle client encodes them as unchanged and
        // an unchanged delta costs no bits, which is exactly why the reader
        // survived hundreds of commands before it ever failed.
        //
        // OLMOD(section-86): AND "EXERCISES" MEANS CHANGED, NOT NON-ZERO. The
        // first gate here was `weapon != 0`, and the three samples it caught all
        // carried weapon=1224 against a baseline of weapon=1224 -- unchanged, so
        // the eleven-bit path was not walked and the sample could not have shown
        // the defect the goldens are red for. Compare against the BASELINE, which
        // is the thing the delta is relative to. A weapon switch produces one.
        const auto sampleBaseline = userCmdSampleCaptureEnabled() &&
                processed.kind == NetchanProcessKind::Accepted
            ? defaultUserCmdResolver(processed.packet.messageAcknowledge)
            : UserCmd{};
        const auto sampleExercisesWeaponFields =
            !processed.userCommands.empty() &&
            (processed.userCommands.front().weapon != sampleBaseline.weapon ||
                processed.userCommands.front().offHandIndex !=
                    sampleBaseline.offHandIndex ||
                processed.userCommands.front().lastWeaponAltModeSwitch !=
                    sampleBaseline.lastWeaponAltModeSwitch);
        if (userCmdSampleCaptureEnabled() &&
            processed.kind == NetchanProcessKind::Accepted &&
            processed.terminalCommand == ClientCommandKind::MoveDelta &&
            sampleExercisesWeaponFields)
        {
            static std::uint32_t userCmdSamples{};
            if (userCmdSamples < 3)
            {
                ++userCmdSamples;
                const auto &baseline = sampleBaseline;
                const auto hex = [](const std::span<const std::uint8_t> bytes) {
                    std::string out;
                    out.reserve(bytes.size() * 2);
                    for (const auto byte : bytes)
                    {
                        char pair[3]{};
                        std::snprintf(pair, sizeof(pair), "%02X", byte);
                        out += pair;
                    }
                    return out;
                };
                const auto &first = processed.userCommands.front();
                char head[512]{};
                std::snprintf(
                    head, sizeof(head),
                    "usercmd sample %lu commands=%lu seq=%u serverId=%u "
                    "msgAck=%u relAck=%u challenge=%u checksumFeed=%u "
                    "userCmdKey=%u",
                    static_cast<unsigned long>(userCmdSamples),
                    static_cast<unsigned long>(processed.moveCommandCount),
                    processed.packet.sequence,
                    processed.packet.serverId,
                    processed.packet.messageAcknowledge,
                    processed.packet.reliableAcknowledge,
                    slot->challenge,
                    gameStateConfigured_ ? gameState_.checksumFeed : 0,
                    processed.userCmdKey);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, head);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "usercmd sample bytes=" + hex(processed.decodedCommands));
                char decoded[512]{};
                std::snprintf(
                    decoded, sizeof(decoded),
                    "usercmd sample decoded commandTime=%u buttons=0x%08X "
                    "angles=%u,%u,%u weapon=%u offHand=%u altSwitch=%u "
                    "fwd=%d right=%d",
                    first.commandTime, first.buttons,
                    first.angles[0], first.angles[1], first.angles[2],
                    first.weapon, first.offHandIndex,
                    first.lastWeaponAltModeSwitch,
                    static_cast<int>(first.forwardMove),
                    static_cast<int>(first.rightMove));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, decoded);
                char base[512]{};
                std::snprintf(
                    base, sizeof(base),
                    "usercmd sample baseline commandTime=%u buttons=0x%08X "
                    "angles=%u,%u,%u weapon=%u offHand=%u altSwitch=%u "
                    "fwd=%d right=%d",
                    baseline.commandTime, baseline.buttons,
                    baseline.angles[0], baseline.angles[1], baseline.angles[2],
                    baseline.weapon, baseline.offHandIndex,
                    baseline.lastWeaponAltModeSwitch,
                    static_cast<int>(baseline.forwardMove),
                    static_cast<int>(baseline.rightMove));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, base);
                char predicted[256]{};
                std::snprintf(
                    predicted, sizeof(predicted),
                    "usercmd sample predicted=%u,%u,%u,%u,%u",
                    processed.predictedState.values[0],
                    processed.predictedState.values[1],
                    processed.predictedState.values[2],
                    processed.predictedState.values[3],
                    processed.predictedState.values[4]);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, predicted);
            }
        }
        // CODREF(netchan_fragment): incomplete fragments and standalone server
        // fragment acknowledgements are transport progress, not complete
        // SV_UserMove messages, and therefore cannot advance gameplay ACKs.
        if (processed.kind == NetchanProcessKind::FragmentPending ||
            processed.kind == NetchanProcessKind::FragmentAcknowledgement)
        {
            // A fragment is live traffic and must keep the client out of the
            // inactivity timeout, but it is not a complete usercmd packet and
            // must not advance ACK, movement, or snapshot state yet.
            slot->lastPacketTime = nowMilliseconds;
            return {
                .kind = processed.kind,
                .reply = std::move(processed.controlReply),
                .clientSlot = slotIndex,
                .reason = std::move(processed.reason),
            };
        }
        if (processed.kind != NetchanProcessKind::Accepted)
        {
            if (processed.kind == NetchanProcessKind::Duplicate)
                ++slot->duplicatePackets;
            else
            {
                ++slot->rejectedPackets;
                ClientPacketRejectStatus reject{
                    .sequence = processed.packet.sequence,
                    .serverId = processed.packet.serverId,
                    .messageAcknowledge = processed.packet.messageAcknowledge,
                    .reliableAcknowledge = processed.packet.reliableAcknowledge,
                    .decodedCommandsSize = static_cast<std::uint32_t>(
                        processed.decodedCommands.size()),
                    .rejectedCommandTime = processed.rejectedCommandTime,
                    .rejectedCommandBaselineTime = processed.rejectedCommandBaselineTime,
                    .reason = processed.reason,
                };
                std::copy_n(
                    processed.decodedCommands.begin(),
                    std::min(
                        processed.decodedCommands.size(),
                        reject.decodedCommandsPrefix.size()),
                    reject.decodedCommandsPrefix.begin());
                slot->lastPacketReject = std::move(reject);
            }
            return {
                .kind = processed.kind,
                .clientSlot = slotIndex,
                .reason = std::move(processed.reason),
            };
        }

        slot->lastPacketTime = nowMilliseconds;
        // WHICH FRAME THE CLIENT'S PERSISTENT CACHE HOLDS, KEYED ON THE ACKNOWLEDGED
        // FRAME'S OWN FLAG (section 169). This used to demand that the acknowledgement
        // match the ONE initializer thought to be in flight, because SnapshotBaselineFlag
        // was being used as a cache-generation handshake. It is not a handshake: it is
        // the wire's statement that a message was written against no baseline, so it now
        // rides every such frame and any one of them the client acknowledges is a frame
        // the client provably stored (CL_ParseSnapshot copies it at 0x00472745). Asking
        // the acknowledged snapshot whether it carried the flag is therefore both simpler
        // and generation-agnostic, and it cannot lose an acknowledgement to a fresher
        // initializer having been armed in the meantime.
        //
        // Note this records WHAT THE CLIENT CACHED. It is deliberately never used as a
        // delta source -- see the invariant at the snapshot assembly.
        {
            const auto acknowledge = processed.packet.messageAcknowledge;
            const auto &acknowledgedSnapshot =
                slot->snapshotHistory[acknowledge % SnapshotHistoryCapacity];
            if (acknowledgedSnapshot.valid && acknowledgedSnapshot.frame &&
                acknowledgedSnapshot.messageNum == acknowledge &&
                acknowledgedSnapshot.initializesBaselineCache)
            {
                slot->baselineFrame = acknowledgedSnapshot.frame;
                slot->baselineCacheAcknowledged = true;
            }
            if (slot->baselineCacheInitializationMessage &&
                acknowledge >= *slot->baselineCacheInitializationMessage)
            {
                slot->baselineCacheInitializationMessage.reset();
            }
        }
        ++slot->acceptedPackets;
        slot->lastDecodedCommandsSize = static_cast<std::uint32_t>(
            processed.decodedCommands.size());
        slot->lastDecodedCommandsPrefix.fill(0);
        std::copy_n(
            processed.decodedCommands.begin(),
            std::min(processed.decodedCommands.size(), slot->lastDecodedCommandsPrefix.size()),
            slot->lastDecodedCommandsPrefix.begin());
        if (processed.terminalCommand == ClientCommandKind::MoveDelta)
            slot->deltaMessage = static_cast<std::int32_t>(slot->netchan.messageAcknowledge);
        else if (processed.terminalCommand == ClientCommandKind::MoveNoDelta)
            slot->deltaMessage = -1;
        slot->lastMoveCommandCount = processed.moveCommandCount;
        // THE RE-ASSERTION IS GONE, AND ITS JOB IS DONE BY THE ENTER-WORLD RESET
        // (section 169). It re-sent the clientInfos section alone against a null
        // baseline while the rest of the message still deltaed against a real one -- a
        // section-local empty baseline with nothing on the wire to declare it, which is
        // exactly the defect it was built to work around. What actually recovers a client
        // whose cgame threw its characterInfo away on a map load is the reset above:
        // deltaMessage = -1 clears the history and the cache state, the next snapshot has
        // no baseline, SnapshotBaselineFlag goes out with it, and the client rebuilds
        // every clientInfo from a section it is TOLD is absolute. That is also what retail
        // does, and it is why retail needs no re-assertion of its own.
        if (!processed.userCommands.empty())
        {
            const auto &latest = processed.userCommands.back();
            // SECTION 190: THE ALT-MODE EDGE. `lastWeaponAltModeSwitch` is a
            // WEAPON ASSET INDEX -- validNativeCommand already bounds it by
            // MaximumWeaponAssetIndex, and out.exe's sub_429E10 uses it to
            // index the weapon-definition table `dword_1988B50` directly. It
            // is decoded, validated, and consumed by nothing.
            //
            // Two u16 compares per accepted move packet, and it writes only
            // when the value MOVES, which is only when the player presses the
            // key. Section 188d's lesson is the reason it is shaped this way:
            // the two instruments that killed the death animation did their
            // work -- a string and a mutex -- on EVERY frame, whether or not
            // anything had happened.
            // SECTION 190: THE BUTTON VOCABULARY, because the alt switch is a
            // BUTTON, not the field this probe started from.
            //
            // Measured 2026-09-02: both players pressed alt-fire on a weapon
            // that HAS an alt (csg12ss_mp -> 1229, ak104ss_mp -> 1234, both
            // built by the engine and both present) and the server's
            // ps->weapon never moved off 1228 / 1233 for a single frame. The
            // client's HUD moved; nothing else did. No reliable command
            // carries it either -- every UNHANDLED client command this match
            // was the `n <N>` alias verb.
            //
            // out.exe names the bit: sub_426BC0 selects between playerState
            // +0x3E8 and +0x3F0 with `cmd.buttons & 0x100000` when the fire
            // type is 7 (Option Shot), and sub_429E10's weapon-switch gate
            // reads oldcmd.buttons bits 0x4000 / 0x8000 / 0x10000. So the
            // question is whether that bit reaches us at all -- and section
            // 186 is the precedent that says it might not: every HELD button
            // decoded as released for months because the delta baseline was
            // wrong.
            //
            // FIRST SIGHTING PER BIT, never per press. One OR and one compare
            // per accepted move packet, and it goes quiet the moment the
            // vocabulary is known -- which is the only shape an always-on
            // instrument may have (section 188d).
            {
                static std::uint32_t seenButtonBits{};
                static std::uint32_t buttonReports{};
                const auto fresh = latest.buttons & ~seenButtonBits;
                if (fresh && buttonReports < 32)
                {
                    ++buttonReports;
                    seenButtonBits |= latest.buttons;
                    char line[192]{};
                    std::snprintf(
                        line, sizeof(line),
                        "button bits FIRST SIGHTING client=%u new=0x%08X "
                        "all=0x%08X cmdWeapon=%u",
                        static_cast<unsigned>(slotIndex),
                        fresh, seenButtonBits, latest.weapon);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, line);
                }
                else if (fresh)
                {
                    seenButtonBits |= latest.buttons;
                }
            }
            // AND A POSITIVE CONTROL, because the first live run produced NO
            // edge at all and a silent instrument is indistinguishable from an
            // instrument that never ran. This says the field is being read and
            // what it holds; if the edge below never fires AND this says 0,
            // the client is genuinely not sending one.
            {
                static std::array<bool, 32> altSeeded{};
                if (slotIndex < altSeeded.size() && !altSeeded[slotIndex])
                {
                    altSeeded[slotIndex] = true;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "altmode baseline client=" +
                            std::to_string(
                                static_cast<std::uint32_t>(slotIndex)) +
                            " value=" +
                            std::to_string(latest.lastWeaponAltModeSwitch) +
                            " cmdWeapon=" + std::to_string(latest.weapon));
                }
            }
            if (slot->lastReceivedUserCmd &&
                slot->lastReceivedUserCmd->lastWeaponAltModeSwitch !=
                    latest.lastWeaponAltModeSwitch)
            {
                static std::uint32_t altModeEdges{};
                if (altModeEdges < 40)
                {
                    ++altModeEdges;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "altmode switch client=" +
                            std::to_string(
                                static_cast<std::uint32_t>(slotIndex)) +
                            " from=" +
                            std::to_string(
                                slot->lastReceivedUserCmd
                                    ->lastWeaponAltModeSwitch) +
                            " to=" +
                            std::to_string(latest.lastWeaponAltModeSwitch) +
                            " cmdWeapon=" + std::to_string(latest.weapon) +
                            " offHand=" + std::to_string(latest.offHandIndex));
                }
            }
            if (!slot->lastReceivedUserCmd ||
                latest.commandTime > slot->lastReceivedUserCmd->commandTime)
            {
                slot->lastReceivedUserCmd = latest;
            }
            slot->predictedState = processed.predictedState;
        }
        bool clientLeft = false;
        for (const auto &reliableCommand : processed.reliableCommands)
        {
            // THE PLAYER PRESSED EXIT. out.exe sends this reliable command the
            // instant the player leaves a match; ignoring it (it logged as
            // UNHANDLED) left the slot occupied until the ~15s active timeout, so
            // a player who left and rejoined raced their own lingering slot. Drop
            // it now, exactly the way a timeout does, and stop touching the slot.
            if (reliableCommand.command == "leave")
            {
                dropClientSlot(slotIndex, TimeoutDrop::Cause::Leave);
                clientLeft = true;
                break;
            }
            if (reliableCommand.command == "s")
                queueScoreboardResponse(static_cast<std::uint32_t>(slotIndex));
            auto menuResponse = SV_ParseMenuResponse(
                reliableCommand.command,
                processed.packet.serverId,
                gameState_);
            if (menuResponse)
            {
                menuResponse->sequence = reliableCommand.sequence;
                // OLMOD(factory-generic-class-response): the Factory entry
                // owner installed the native NCS table (generic at1). Other
                // maps retain their legacy parser and dispatch behavior.
                const bool factoryClassMenu = gameState_.gameType == "zm" &&
                    gameState_.mapName == "zm_factory_sh" &&
                    gameState_.scriptMenus[1] == "changeclass";
                const bool accepted = SV_DispatchMenuResponse(
                    *slot, *menuResponse, teamPolicy(), factoryClassMenu);
                if (factoryClassMenu)
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "Factory class response index=" +
                            std::to_string(menuResponse->menuIndex) + " menu=" +
                            menuResponse->menuName + " choice=" + menuResponse->response +
                            " accepted=" + (accepted ? "1" : "0"));
                slot->lastMenuResponse = std::move(menuResponse);
                continue;
            }
            // ANYTHING ELSE WAS BEING DROPPED WITHOUT A WORD, and that silence
            // is why section 109c's request/response protocol has never been
            // checkable end to end -- the asking half exists and nothing has
            // ever read the answer except the one shape the parser expects.
            //
            // The answer worth watching for is `mr <n> bad`. out.exe's `u`
            // handler (sub_610DB0) resolves its argument through
            // sub_514880(_, n + 4808) -- the CONFIGSTRING getter, whose class
            // table byte_77D8250 is the same one WeaponCountConfigStringIndex
            // is derived from -- so `u 10` means "open the menu NAMED IN
            // CONFIGSTRING 4818", not "screen ten". An empty configstring makes
            // the client reply `mr 10 bad` and do nothing. This server fills
            // three of those sixty-four slots.
            if (reliableCommand.command == "s")
                continue;
            // FIRST-TIME-ONLY CANNOT BE COUNTED, AND COUNTING IS THE TEST.
            //
            // `n <k>` is the one channel left that could carry alt-fire: key 3
            // emits NO usercmd button at all -- measured 2026-09-04 with a
            // control in the same window, two left-clicks giving exactly two
            // 0x00000001 edges and five presses of 3 giving none. Dedupe was
            // right while these were noise; it is wrong now, because the whole
            // question is whether some `n <k>` arrives once per press.
            // OLMOD_LOG_CLIENT_COMMANDS=1 logs EVERY one, capped.
            static const bool logEveryCommand = [] {
                const char *const value =
                    std::getenv("OLMOD_LOG_CLIENT_COMMANDS");
                return value && value[0] && value[0] != '0';
            }();
            if (logEveryCommand)
            {
                static std::uint32_t commandLines{};
                if (commandLines < 400)
                {
                    ++commandLines;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "client command EVERY client=" +
                            std::to_string(slotIndex) + " text=\"" +
                            reliableCommand.command + "\"");
                }
            }
            else if (slot->reportedUnhandledCommands.size() < 32 &&
                slot->reportedUnhandledCommands
                    .insert(reliableCommand.command).second)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "client command UNHANDLED client=" +
                        std::to_string(slotIndex) + " text=\"" +
                        reliableCommand.command + "\" (first time only)");
            }
        }
        // The slot is Free now -- nothing below may dereference it. Ack the packet
        // and let the next frame's census pick up the departure.
        if (clientLeft)
        {
            return {
                .kind = NetchanProcessKind::Accepted,
                .clientSlot = slotIndex,
            };
        }
        if (slot->gameplayState == ClientGameplayState::Playing &&
            gameplayAuthorityReady_)
        {
            // CODREF(sv_user_move): BO1 0x0070BCE0 and BO2 0x006F0AE0
            // dispatch accepted commands directly; Ghosts 0x1401F59B0 may
            // defer them to SV_ProcessClientThinks 0x1401F4450.
            // OLMOD(pending-usercmd-queue): packet ingestion and game-thread
            // execution are separate in the embedded dedicated process, so
            // ol-mod owns this queue. BO1/BO2 dispatch directly from
            // SV_UserMove; Ghosts defers into an eight-slot ring and is the
            // matching reference for this split architecture.
            // TODO(CODOL): replace this project boundary if a CODOL dedicated
            // SV_UserMove/SV_ProcessClientThinks implementation is recovered.
            // WHAT THE WIRE ACTUALLY CARRIES, BEFORE ANY QUEUE OR BUDGET TOUCHES IT.
            //
            // Section 185: the pmove sees cmdIn=0 for five consecutive frames while a
            // player is prone, and the engine re-derives the stance from cmd.buttons
            // EVERY frame (sub_417D10 LABEL_131), so no button means standing. Two
            // explanations remain and they need opposite fixes: the client sends the
            // toggle and stops, or the client sustains it and this server loses it
            // between arrival and the pmove. cmdIn is the DECODED usercmd, so the only
            // step it does not cover is this one -- ingress, the eight-slot queue and
            // its overflow drops.
            //
            // Armed by a stance bit ARRIVING and then unconditional for a window, so
            // the frames that matter (the ones with NO stance bit) are not filtered out
            // by the very condition being measured. Section 184h paid for that lesson.
            {
                constexpr std::uint32_t StanceButtons = 0x100u | 0x200u;
                static std::uint32_t arrivalWindow{};
                static std::uint32_t arrivalLines{};
                for (const auto &command : processed.userCommands)
                {
                    if ((command.buttons & StanceButtons) != 0)
                        arrivalWindow = 120;
                    if (!arrivalWindow || arrivalLines >= 400)
                        continue;
                    --arrivalWindow;
                    ++arrivalLines;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "usercmd arrival c=" + std::to_string(slotIndex) +
                        " t=" + std::to_string(command.commandTime) +
                        " buttons=0x" + [](std::uint32_t v) {
                            char b[16]{};
                            std::snprintf(b, sizeof(b), "%08X", v);
                            return std::string{ b };
                        }(command.buttons) +
                        " pending=" + std::to_string(slot->pendingUserCmds.size()) +
                        " droppedOverflow=" +
                        std::to_string(slot->droppedOverflowUserCmds));
                }
            }
            for (const auto &command : processed.userCommands)
                static_cast<void>(SV_QueuePendingUserCmd(*slot, command));
        }
        else if (!gameplayAuthorityReady_ && slot->lastReceivedUserCmd)
        {
            slot->pendingUserCmds.clear();
            slot->lastQueuedUserCmdTime =
                slot->lastReceivedUserCmd->commandTime;
        }
        if (!processed.controlReply.empty())
        {
            // OLMOD(fragment-control-before-gamestate): the host transport can
            // return one datagram per ingress callback. A completed reliable
            // fragment must publish its ACK first, but must not advance a
            // Connected client to ClientLoading until the gamestate datagram
            // is actually transmitted. The next accepted packet retries that
            // unchanged state transition.
            return {
                .kind = NetchanProcessKind::Accepted,
                .reply = std::move(processed.controlReply),
                .decodedCommands = std::move(processed.decodedCommands),
                .reliableCommands = std::move(processed.reliableCommands),
                .userCommands = std::move(processed.userCommands),
                .clientSlot = slotIndex,
            };
        }
        constexpr std::array<std::uint8_t, 1> Eof{ ServerCommandEof };
        auto commands = std::vector<std::uint8_t>(Eof.begin(), Eof.end());
        // A GAMESTATE THAT IS NEVER SENT SAYS NOTHING, and it is the head of a deadlock:
        // no gamestate -> the client never reaches ClientLoading -> it never sends
        // gamestateupdate 1..6 -> it never becomes Active -> activeClients stays 0 ->
        // configurePendingWorldSpawn returns at its first line -> no world, no spawn
        // points, no snapshots. On screen that is a client sitting in the menu or on a
        // loading screen forever, with `clients=1 active=0 snapshots=0` in the runtime
        // line and not one other complaint anywhere. Four terms can hold it shut and the
        // log named none of them. Once per distinct combination per client, so a stuck
        // client prints one line rather than one per packet.
        if (slot->state == ClientState::Connected)
        {
            std::string blocked;
            if (!slot->profileStatsComplete)
                blocked += " PROFILE_STATS_INCOMPLETE(" +
                    std::to_string(slot->profileStatsReceivedMask) + "/" +
                    std::to_string(slot->profileStatsRequiredMask) + ")";
            if (!clientGenerationIsActive(*slot))
                blocked += " GENERATION_INACTIVE";
            if (!gameStateConfigured_)
                blocked += " GAMESTATE_NOT_CONFIGURED";
            if (!gameStateBuilder_)
                blocked += " NO_GAMESTATE_BUILDER";
            if (!blocked.empty() && slot->gameStateGateReport != blocked)
            {
                slot->gameStateGateReport = blocked;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "gamestate NOT sent client=" + std::to_string(slotIndex) + blocked);
            }
        }
        if (slot->state == ClientState::Connected && slot->profileStatsComplete &&
            clientGenerationIsActive(*slot) && gameStateConfigured_ &&
            gameStateBuilder_)
        {
            auto gameStateCommands = gameStateBuilder_(
                gameState_,
                static_cast<std::uint32_t>(slotIndex),
                0);
            if (!gameStateCommands.empty())
            {
                slot->state = ClientState::ClientLoading;
                slot->gamestateMessageNum = slot->netchan.outgoingSequence;
                commands = std::move(gameStateCommands);
                ++gameStateMessagesSent_;
            }
        }
        else if (slot->state == ClientState::Active)
        {
            return {
                .kind = NetchanProcessKind::Accepted,
                .reply = std::move(processed.controlReply),
                .decodedCommands = std::move(processed.decodedCommands),
                .reliableCommands = std::move(processed.reliableCommands),
                .userCommands = std::move(processed.userCommands),
                .clientSlot = slotIndex,
            };
        }
        auto reply = Netchan_Transmit(
            slot->netchan,
            slot->challenge,
            slot->netchan.lastClientReliableSequence,
            commands,
            slot->netchan.lastClientReliableCommand);
        return {
            .kind = NetchanProcessKind::Accepted,
            .reply = std::move(reply),
            .decodedCommands = std::move(processed.decodedCommands),
            .reliableCommands = std::move(processed.reliableCommands),
            .userCommands = std::move(processed.userCommands),
            .clientSlot = slotIndex,
        };
    }

    std::vector<SvClientMessage> SvClientSystem::SV_SendClientMessages(
        const std::uint32_t nowMilliseconds,
        const std::size_t maximumBytesPerFrame)
    {
        // CODREF(sv_send_client_messages): BO1 0x0071E100 and BO2
        // 0x00703CF0 gate on nextSnapshotTime, start after lastClientSent and
        // progress pending fragments before constructing a new snapshot.
        // Ghosts 0x140206C40/0x1402070B0 separates build/send/flush but keeps
        // the same byte-budgeted ring ownership.
        // CODREF(netchan_fragment): pending fragments now progress before a
        // new snapshot using CODOL's indexed fragment owner.
        // OLMOD(snapshot-send-ring): the cursor and caller-supplied budget are
        // source ownership because CODOL retains no serverStatic_t owner.
        std::vector<SvClientMessage> messages;
        if (clients_.empty() || !maximumBytesPerFrame)
            return messages;

        std::size_t bytesSent{};
        const auto startClient = nextSnapshotSendClient_ % clients_.size();
        for (std::size_t offset{}; offset < clients_.size(); ++offset)
        {
            const auto clientNum = (startClient + offset) % clients_.size();
            auto &client = clients_[clientNum];
            if (client.state == ClientState::Free ||
                timePrecedes(nowMilliseconds, client.nextSnapshotTime))
            {
                continue;
            }

            const auto hasPendingFragment = client.netchan.unsentFragments;
            if (!hasPendingFragment && client.state != ClientState::Active)
                continue;

            // CODDIFF(sv_send_client_messages): CODOL has no retained server
            // scheduler. The source budget is supplied by the caller rather
            // than guessed from absent CODOL Live_GetNecessaryBandwidth dvars.
            // As in BO1/BO2, one admitted message may cross the budget; the
            // next due client resumes the ring on the following call.
            if (bytesSent >= maximumBytesPerFrame)
            {
                client.rateDelayed = true;
                nextSnapshotSendClient_ = clientNum;
                return messages;
            }

            auto plaintext = hasPendingFragment
                ? Netchan_TransmitNextFragment(client.netchan)
                : buildSnapshotMessage(
                      client, static_cast<std::uint32_t>(clientNum));
            if (!plaintext.empty())
            {
                bytesSent += plaintext.size();
                messages.push_back({
                    .peer = client.peer,
                    .plaintext = std::move(plaintext),
                });
                client.rateDelayed = false;
                client.lastSnapshotTime = nowMilliseconds;
                // BO1 SV_SendMessageToClient 0x0071CDB0 bypasses rate delay for
                // loopback/LAN peers. Remote rate-window calculation requires
                // the missing per-client rate/snapshotMsec owner.
                if (isLanPeer(client.peer))
                {
                    client.nextSnapshotTime = nowMilliseconds;
                }
                else
                {
                    // TODO(CODOL): replace the 20 Hz source cadence with the
                    // recovered remote client rate and snapshotMsec contract.
                    client.nextSnapshotTime = nowMilliseconds + 50;
                }
                nextSnapshotSendClient_ = (clientNum + 1) % clients_.size();
            }
        }

        // Ghosts advances the full-send generation after a complete sweep so
        // repeated small budgets do not permanently privilege client zero.
        nextSnapshotSendClient_ = (startClient + 1) % clients_.size();
        return messages;
    }

    std::size_t SvClientSystem::SV_CheckTimeouts(const std::uint32_t nowMilliseconds)
    {
        std::size_t dropped{};
        for (std::size_t clientNum = 0; clientNum < clients_.size(); ++clientNum)
        {
            auto &client = clients_[clientNum];
            if (client.state == ClientState::Free)
                continue;
            // A gamestate acknowledgement makes the network slot Active before
            // the client finishes loading the map. out.exe can also send a move
            // packet while it is still on the loading screen, before the world
            // owns a spawn or can execute that command. Keep the connecting grace
            // through that whole interval. Once the lifecycle reaches Playing,
            // the short active timeout still frees a crashed player's seat
            // promptly.
            const auto gameplayTrafficStarted =
                client.gameplayState == ClientGameplayState::Playing;
            const auto timeout = client.state == ClientState::Active &&
                    gameplayTrafficStarted
                ? timeouts_.activeMilliseconds
                : timeouts_.connectingMilliseconds;
            if (!expired(nowMilliseconds, client.lastPacketTime, timeout))
                continue;

            dropClientSlot(clientNum, TimeoutDrop::Cause::Timeout);
            ++dropped;
        }
        return dropped;
    }

    void SvClientSystem::dropClientSlot(
        const std::size_t clientNum, const TimeoutDrop::Cause cause)
    {
        auto &client = clients_[clientNum];
        if (client.state == ClientState::Free)
            return;

        timeoutDrops_.push_back({
            .clientNum = static_cast<std::uint32_t>(clientNum),
            .xuid = client.xuid,
            .state = client.state,
            .lastPacketTime = client.lastPacketTime,
            .profileStatsReceivedMask = client.profileStatsReceivedMask,
            .profileStatsRequiredMask = client.profileStatsRequiredMask,
            .profileStatsComplete = client.profileStatsComplete,
            .gameStateUpdateStage = client.gameStateUpdateStage,
            .sessionGeneration = client.sessionGeneration,
            .sessionGenerationActive = clientGenerationIsActive(client),
            .messageAcknowledge = client.netchan.messageAcknowledge,
            .reliableAcknowledge = client.netchan.reliableAcknowledge,
            .cause = cause,
        });

        for (auto &challenge : challenges_)
        {
            if (challenge.valid && challenge.connected &&
                challenge.peer == client.peer && challenge.xuid == client.xuid &&
                challenge.challenge == client.challenge)
            {
                challenge.connected = false;
            }
        }
        client = {};
    }

    std::vector<SvClientSystem::TimeoutDrop> SvClientSystem::takeTimeoutDrops()
    {
        auto drops = std::move(timeoutDrops_);
        timeoutDrops_.clear();
        return drops;
    }

    std::vector<std::uint8_t> SvClientSystem::buildSnapshotMessage(
        ClientSlot &client,
        const std::uint32_t clientNum)
    {
        // CODREF(sv_build_client_snapshot): BO1 0x0071BE50, BO2
        // 0x006FEB10 and Ghosts 0x140202690 all select one client-owned
        // playerState and message baseline while referring to server-wide
        // entity/client archives. BO1 builds a point-PVS list; BO2/Ghosts
        // instead archive every linked, non-SVF_NOCLIENT entity before this
        // per-client step. CODOL-local visibility policy remains an upstream
        // world-publication question, not a serializer-side distance filter.
        ++client.snapshotAssemblyAttempts;
        const auto reject = [&client](const SvSnapshotAssemblyFailure failure) {
            client.snapshotAssemblyFailure = failure;
            ++client.snapshotAssemblyFailures;
            return std::vector<std::uint8_t>{};
        };
        if (!worldFrameConfigured_ || !worldFrame_)
            return reject(SvSnapshotAssemblyFailure::WorldFrameUnavailable);
        if (!snapshotBuilder_)
            return reject(SvSnapshotAssemblyFailure::SnapshotBuilderUnavailable);
        if (client.snapshotSent &&
            client.lastSnapshotServerTime == worldFrame_->serverTime)
        {
            return reject(SvSnapshotAssemblyFailure::DuplicateServerTime);
        }

        const auto messageNum = client.netchan.outgoingSequence;
        const auto acknowledge = client.deltaMessage;
        const SvSnapshotFrame *baseline{};
        std::uint8_t deltaMessageDistance{};
        std::optional<std::uint32_t> baselineMessage;
        bool baselineWasFlagged = false;
        // CODREF(sv_write_snapshot_to_client): all three references reject
        // acknowledgements outside packetBackup before selecting a delta
        // frame. SnapshotHistoryCapacity is source storage for that bounded
        // message-number contract, not a recovered client_t layout.
        const auto selectBaseline = [&](const std::uint32_t candidate) {
            if (candidate >= messageNum ||
                messageNum - candidate > SnapshotDeltaWindow)
            {
                return false;
            }
            const auto &entry =
                client.snapshotHistory[candidate % SnapshotHistoryCapacity];
            if (!entry.valid || !entry.frame || entry.messageNum != candidate)
                return false;
            baseline = entry.frame.get();
            deltaMessageDistance =
                static_cast<std::uint8_t>(messageNum - candidate);
            baselineMessage = candidate;
            baselineWasFlagged = entry.initializesBaselineCache;
            return true;
        };
        // ENTITIES HAVE A SECOND BASELINE, AND IT HAS NO IDENTITY (section 170). The
        // frame ring is not the only place out.exe keeps entity rows. sub_470E90
        // 0x00470e97 tests the BASELINE frame's snapFlags, and when bit 8 is set it reads
        //     &dword_C89E050[70 * listPosition]
        // -- a FLAT array indexed by list position alone, with no frame number and no
        // generation. CL_ParseSnapshot resets its cursor at 0x00472223
        //     mov dword ptr [0xc89e04c], 0
        // inside the flag-8 block, so the array is refilled from position zero by EVERY
        // flagged frame and holds exactly ONE generation: the newest flagged frame the
        // client has parsed. (The whole image writes that cursor at four addresses only:
        // 0x470edf read, 0x470f3b increment, 0x472223 reset, 0x5bec9c CL_ClearState --
        // `python Tools/olfinal/scan-out-exe.py 0xC89E04C`.)
        //
        // So naming a flagged frame as a delta baseline is only correct when it is the
        // NEWEST flagged frame we have emitted. Before 09d722f that held for free because
        // the flag rode one frame per session; now it rides a RUN of frames whenever the
        // client has no acknowledgement, and naming whichever member of that run the
        // acknowledgement happens to point at decodes the run's OLDEST rows against the
        // client's NEWEST array. Two ways that shows up, both indistinguishable to a
        // player from the invisible-player bug this replaced: an entity present in our
        // baseline but absent from the client's array decodes against the memset-zero row
        // at 0x0047114A (modelIndex 0, origin 0), and every XOR field lands on
        // `value ^ (baseSent ^ baseHeld)` PERMANENTLY, because from then on we believe the
        // client holds what we sent. Measured, by
        // `python Tools/olfinal/check-entity-baseline.py`: retail names a stale flagged
        // baseline in 0 of 84 demos; replaying this fix's flag placement onto our own 50
        // recordings names one in 8 of them, 23 frames, at drift 1 and 2.
        //
        // THE RULE, and it is the whole fix: an acknowledgement that names a frame WE SENT
        // FLAGGED must not select a ring delta. It selects the newest flagged frame
        // instead, which is the only one the client's flat array can still hold.
        //
        // WHY DELTA > 0 AND NOT RETAIL'S DELTA == 0 BRIDGE. Retail exits a flagged run
        // through delta==0 frames with the flag CLEAR, which the client decodes against
        // its persistent cache &unk_C89A490 (0x00472246 -> 0x00472268). That path is
        // checked by ONE BIT -- dword_C89E010 & 8, which is nothing but the cached frame's
        // own snapFlags word (0xC89A490 + 0x3B80 = 0xC89E010). It carries no frame number,
        // so a cache generation the client does not hold is a SILENT misdecode, which is
        // the failure class we are removing. The delta>0 path is policed: 0x004722c0 the
        // named frame's valid bit, 0x004722e8 `frames[deltaNum & 31].messageNum ==
        // deltaNum`, then four ring-freshness bounds (0x004722f0 entities against a 25600
        // -entry ring, 0x0047230c clientInfos, 0x0047234f clients, 0x00472368 glass), and
        // every failure is `*msg = 1` -- one discarded snapshot, no disconnect (0x00473c09
        // just breaks the parse loop). The DECODE is identical either way: sub_470E90
        // branches on the baseline frame's own snapFlags, and a flagged frame keeps them
        // in the 32-entry ring (stored unconditionally at 0x004727e8, snapFlags copied at
        // 0x00472849). So this is retail's bridge plus the client's own identity check,
        // and every way it can go wrong -- the flagged frame lost, reordered, or its parse
        // errored -- costs one frame instead of corrupting the session.
        //
        // Retail never sends this shape (0 of 422,478 delta frames in 84 demos name a
        // flagged baseline). Retail also never enters the flagged state mid-match (0 of 83
        // demos) and its runs sit pre-spawn where the world is static, so its unverified
        // cache path is harmless in the only place retail creates it. Ours is mid-match.
        //
        // Convergence, which the rejected "refuse the ack" guard did not have: while the
        // acknowledgement still names a flagged frame we emit a DELTA, not another full,
        // so newestFlaggedSnapshotMessage is FROZEN and the acknowledgement walks onto an
        // unflagged frame within one round trip at any acknowledgement lag. The rejected
        // guard emitted another flagged frame every tick, advancing the target in lockstep
        // with the ack -- a permanent full-snapshot stream. Measured lag on our own wire is
        // 1-2 frames for 97% of snapshots, so this state lasts one or two frames.
        //
        // And if the newest flagged frame has aged out of SnapshotDeltaWindow or its
        // history entry is gone, selectBaseline fails, `baseline` stays null, and the next
        // line makes this a fresh FULL frame -- which re-arms
        // newestFlaggedSnapshotMessage. That is the liveness rule, and it needs no timer.
        if (acknowledge > 0)
        {
            const auto acknowledged = static_cast<std::uint32_t>(acknowledge);
            const auto &acknowledgedEntry =
                client.snapshotHistory[acknowledged % SnapshotHistoryCapacity];
            const auto acknowledgedFrameWasFlagged =
                acknowledged < messageNum && acknowledgedEntry.valid &&
                acknowledgedEntry.frame &&
                acknowledgedEntry.messageNum == acknowledged &&
                acknowledgedEntry.initializesBaselineCache;
            if (acknowledgedFrameWasFlagged)
            {
                if (client.newestFlaggedSnapshotMessage)
                    selectBaseline(*client.newestFlaggedSnapshotMessage);
            }
            else
            {
                selectBaseline(acknowledged);
            }
        }

        // CODREF(sv_build_client_snapshot): Ghosts keeps the persistent
        // no-delta entity baseline behind
        // clientHeader.hasAckedBaselineData. Sending the bit-8 snapshot is
        // insufficient: until its message number is acknowledged, the client
        // and server cannot prove that they own the same cache generation.
        // AND SnapshotBaselineFlag IS NOT "THIS MESSAGE INITIALIZES THE CACHE" (section
        // 169). It is the ONLY thing on this wire that tells out.exe which baseline to
        // decode against, and the client reads it as "every section of this message is
        // encoded against an EMPTY baseline". CL_ParseSnapshot 0x0047222E clears its
        // baseline pointer, KEEPS the null if the flag is set (0x0047223D), and otherwise
        // deltas against its PERSISTENT cached snapshot (0x00472246 -> 0x00472268) whose
        // valid bit dword_C89E010 is that snapshot's own snapFlags word, written by the
        // struct copy at 0x00472849. Any extra condition here writes ABSOLUTE values into
        // a message the client decodes as a DELTA -- and the codec is a symmetric XOR
        // (writeUnsignedDelta's `value ^ (baseline & mask)` against the client's
        // `readBits ^ (mask & baseline)` at 0x0066FE68), so a field whose held value
        // already equals the transmitted one decodes to V ^ V = ZERO.
        //
        // The old condition also required !baselineCacheAcknowledged and no initializer
        // in flight, so it went FALSE while `baseline` was still null -- one round trip,
        // every run, of unflagged empty-baseline frames. The flag is exactly "no
        // baseline", nothing else.
        const auto initializeBaselineCache = !baseline;
        // A CLIENT THAT ASKS FOR A NON-DELTA SNAPSHOT MUST GET ONE. Section 167:
        // deltaMessage == -1 is the client saying, through clc_moveNoDelta, that it has
        // NO usable snapshot state -- which is exactly what it says after a map load,
        // because loading reinitialises cgame and that re-deals every characterInfo name
        // buffer out of a freshly memset pool (0x004555D0). Substituting the persistent
        // baseline frame there answers "I have nothing" with a delta against a frame the
        // client no longer holds, and every field equal to that frame is then NEVER SENT
        // AGAIN. For clientInfos that is permanent: modelIndex stays zero,
        // CG_SetupClientCharacterInfo 0x00541800 takes its early return, no model name is
        // ever written, and nobody can see that player for the rest of the match.
        //
        // The persistent cache is Ghosts' hasAckedBaselineData, and it is an ENTITY
        // baseline optimisation; it was never a licence to withhold a full snapshot from
        // a client that has just told us it has nothing.
        //
        // AND IT IS NOT A BASELINE WE CAN NAME ON THIS WIRE AT ALL (section 169). This
        // used to restore `baseline = client.baselineFrame.get()` when the acknowledgement
        // fell outside the history window -- while leaving deltaMessageDistance at ZERO,
        // and distance zero is precisely what the client reads as "non-delta"
        // (0x004721AC/0x004721AE). Worse, what the client kept of that snapshot is not its
        // contents: sub_472830 copies only the header words 0x3B7C..0x3BB8, i.e.
        // firstClientInfo (+0x3BAC) and numClients (+0x3B9C) -- bare INDICES into a
        // 608-entry ring (capacity at 0x005C8939) that recycles in about fifteen seconds
        // at two players. The server keeps entries; the client keeps a window that moves.
        // Sending a full snapshot instead is correct by construction and costs one frame.
        //
        // THE INVARIANT FROM HERE DOWN, and SV_WriteSnapshot asserts it:
        //     deltaMessageDistance > 0  <=>  baseline != nullptr  <=>  flag CLEAR.
        // `baseline` is now assigned in exactly one place, paired with its distance.
        // AND SAY WHICH BASELINE THIS SNAPSHOT IS AGAINST. Two changes above depend on
        // a client actually reaching `deltaMessage == -1` after a map load; if it never
        // does, they are inert and this line says so instead of leaving it to be
        // inferred from a symptom. Deduped, so it is silent once a client settles.
        //
        // AND WHICH OF THE THREE STATES THIS SLOT IS IN (section 170). "rearm" is the
        // acknowledgement naming a frame we sent flagged, answered with a delta onto the
        // NEWEST flagged frame rather than the acked one; it should appear for one or two
        // frames after a run and then never again for that connection. "persistent" is
        // gone with the substitution that produced it -- `baseline` now comes from
        // snapshotHistory or nowhere.
        {
            const char *const source = baseline
                ? (baselineWasFlagged ? "rearm(flagged-baseline)" : "acked")
                : "none(FULL)";
            static std::array<const char *, MaximumGameClients> reportedSource{};
            const auto slotIndex = static_cast<std::size_t>(clientNum);
            if (slotIndex < reportedSource.size() &&
                reportedSource[slotIndex] != source)
            {
                reportedSource[slotIndex] = source;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "snapshot baseline client=" + std::to_string(clientNum) +
                        " source=" + source + " deltaMessage=" +
                        std::to_string(acknowledge) + " cacheAcked=" +
                        std::to_string(client.baselineCacheAcknowledged ? 1 : 0));
            }
        }
        // THE SECOND HALF OF THE SAME INSTRUMENT (section 170). SV_WriteSnapshot already
        // asserts the WIRE half of the baseline contract -- distance and
        // SnapshotBaselineFlag agreeing with `baseline` -- and that half is blind to this
        // one, because a stale flagged baseline is perfectly well-formed on the wire. The
        // ENTITY half can only be checked here, since only the slot knows which frames
        // went out flagged.
        //
        // out.exe keeps the entity rows of a flagged frame in the flat array
        // dword_C89E050, refilled from position zero by every flagged frame (cursor reset
        // 0x00472223), and sub_470E90 0x00470e97 reads a baseline row from it whenever the
        // BASELINE frame's snapFlags carry bit 8. So a flagged baseline that is not the
        // newest flagged frame we emitted decodes this message's entities against a
        // DIFFERENT generation than it was written with, and nothing on the wire says so.
        //
        // Silent while the invariant holds, which after this section's change is every
        // frame -- the selection above cannot construct the violating case, so a line here
        // means someone reintroduced it. The two failures print different fields rather
        // than sharing one word: a stale generation names both message numbers and the
        // drift between them, a missing generation names neither.
        {
            const bool staleFlaggedGeneration = baseline && baselineWasFlagged &&
                client.newestFlaggedSnapshotMessage && baselineMessage &&
                *baselineMessage != *client.newestFlaggedSnapshotMessage;
            const bool unrecordedFlaggedGeneration =
                baseline && baselineWasFlagged &&
                !client.newestFlaggedSnapshotMessage;
            if (staleFlaggedGeneration || unrecordedFlaggedGeneration)
            {
                const auto line = staleFlaggedGeneration
                    ? "SNAPSHOT BASELINE MISMATCH kind=entity-generation observer=" +
                        std::to_string(clientNum) + " message=" +
                        std::to_string(messageNum) + " distance=" +
                        std::to_string(deltaMessageDistance) + " baselineMessage=" +
                        std::to_string(*baselineMessage) + " newestFlagged=" +
                        std::to_string(*client.newestFlaggedSnapshotMessage) +
                        // Signed on purpose. An unsigned difference would print a
                        // ten-digit number instead of the truth if a future change ever
                        // named a flagged frame NEWER than the recorded one, and an
                        // instrument that misreports the failure it exists to catch is
                        // worse than none.
                        " drift=" +
                        std::to_string(
                            static_cast<std::int64_t>(
                                *client.newestFlaggedSnapshotMessage) -
                            static_cast<std::int64_t>(*baselineMessage)) +
                        " -- the client's flat entity array holds newestFlagged, so"
                        " sub_470E90 will read every entity baseline row from the WRONG"
                        " generation"
                    : "SNAPSHOT BASELINE MISMATCH kind=entity-generation-unrecorded"
                        " observer=" + std::to_string(clientNum) + " message=" +
                        std::to_string(messageNum) + " distance=" +
                        std::to_string(deltaMessageDistance) + " baselineMessage=" +
                        (baselineMessage ? std::to_string(*baselineMessage) : "none") +
                        " -- this baseline was emitted flagged but no flagged message is"
                        " recorded for the slot, so which generation the client holds is"
                        " unknown";
                static std::array<std::size_t, MaximumGameClients> reportedEntityMismatch{};
                const auto digest = std::hash<std::string>{}(line);
                const auto slotIndex = static_cast<std::size_t>(clientNum);
                if (slotIndex < reportedEntityMismatch.size() &&
                    reportedEntityMismatch[slotIndex] != digest)
                {
                    reportedEntityMismatch[slotIndex] = digest;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, line);
                }
            }
        }
        // OLMOD(snapshot-message-assembly): the project writer owns CODOL wire
        // serialization and reliable-command prefixing; Netchan_Transmit owns
        // encryption/fragment admission. Keeping these failures before history
        // publication prevents an unsent candidate becoming a future baseline.
        // THE CLIENT'S OWN PREDICTION, WHICH DECIDES THE LEADING BIT OF
        // THE PLAYERSTATE SECTION. Parsed since the netchan existed, stored on
        // the slot, and consumed by nothing until now. values[0..2] are the
        // float bits of the origin it predicted, values[3] is the command time
        // it predicted to; values[4] has only ever been observed as zero.
        SvClientPrediction clientPrediction{};
        if (client.lastReceivedUserCmd)
        {
            static_assert(
                sizeof(clientPrediction.origin) ==
                sizeof(std::uint32_t) * 3);
            std::memcpy(
                clientPrediction.origin.data(),
                client.predictedState.values.data(),
                sizeof(clientPrediction.origin));
            clientPrediction.commandTime = client.predictedState.values[3];
            clientPrediction.valid = true;
        }
        // (Section 169: the one-shot clientInfos re-assertion that used to be armed here
        // is deleted. It wrote the clientInfos section against a NULL baseline while the
        // rest of the message still deltaed against a real one, with nothing on the wire
        // to declare it -- which is the defect, not a cure for it. What actually recovers
        // a client whose cgame threw its characterInfo away is the enter-world reset:
        // deltaMessage = -1, history and cache state cleared, so the next snapshot has no
        // baseline and carries SnapshotBaselineFlag to say so.)
        auto commands = snapshotBuilder_(
            *worldFrame_, baseline, clientNum, deltaMessageDistance,
            initializeBaselineCache, &clientPrediction);
        if (commands.empty())
            return reject(SvSnapshotAssemblyFailure::SnapshotBuilderEmpty);
        std::vector<std::uint8_t> reliableCommands;
        appendPendingServerCommands(reliableCommands, client);
        if (!reliableCommands.empty())
        {
            reliableCommands.insert(
                reliableCommands.end(), commands.begin(), commands.end());
            commands = std::move(reliableCommands);
        }
        auto plaintext = Netchan_Transmit(
            client.netchan,
            client.challenge,
            client.netchan.lastClientReliableSequence,
            commands,
            client.netchan.lastClientReliableCommand);
        if (plaintext.empty())
            return reject(SvSnapshotAssemblyFailure::NetchanTransmitEmpty);

        // CODDIFF(sv_build_client_snapshot): message/baseline ownership remains
        // per client, while immutable entity/client/glass storage is shared in
        // place of COD's global circular snapshot archives.
        auto &entry = client.snapshotHistory[messageNum % SnapshotHistoryCapacity];
        entry = {
            .valid = true,
            .initializesBaselineCache = initializeBaselineCache,
            .messageNum = messageNum,
            .frame = worldFrame_,
        };
        if (initializeBaselineCache)
        {
            client.baselineCacheInitializationMessage = messageNum;
            // THE ONLY GENERATION THE CLIENT'S FLAT ENTITY ARRAY CAN HOLD (section 170).
            // Every flagged frame refills dword_C89E050 from position zero -- the cursor
            // reset at 0x00472223 -- so the newest one we have EMITTED is the newest one
            // the client can possibly be holding entities for. Recorded here, at the same
            // instant the flag actually goes on the wire, so it can never describe a
            // message we decided not to send. Unlike
            // baselineCacheInitializationMessage this is NOT cleared on acknowledgement:
            // the acknowledgement is precisely when the selection above needs it.
            client.newestFlaggedSnapshotMessage = messageNum;
        }
        client.lastSnapshotServerTime = worldFrame_->serverTime;
        client.snapshotSent = true;
        client.snapshotAssemblyFailure = SvSnapshotAssemblyFailure::None;
        ++snapshotMessagesSent_;
        if (deltaMessageDistance)
            ++deltaSnapshotMessagesSent_;
        else
            ++fullSnapshotMessagesSent_;
        return plaintext;
    }

    bool SvClientSystem::queueReliableCommand(
        const std::uint32_t clientNum,
        std::string command)
    {
        if (clientNum >= clients_.size() || command.empty() ||
            command.size() >= 1024)
        {
            return false;
        }
        // `a <index>` enters out.exe's CG_SelectWeapon path immediately.  A
        // dynamic index that is not present in this gamestate's weapon block
        // resolves to a null definition and crashes at out.exe+0x19B79B before
        // the client can report a useful error.  Wetwork exposed this with the
        // retail demo's `a 1198`: this live gamestate started its dynamic block
        // at 1163 and registered only 1163..1168.
        //
        // The first modular entry is the engine-provided dynamic boundary. Base
        // weapons below it are already loaded; at or above it, an `a` request is
        // valid only when this gamestate actually registered that exact slot.
        if (gameStateConfigured_ && command.starts_with("a ") &&
            !gameState_.modularWeaponConfigStrings.empty())
        {
            const auto token = std::string_view(command).substr(2);
            std::uint32_t requested{};
            const auto [end, error] = std::from_chars(
                token.data(), token.data() + token.size(), requested);
            const auto firstDynamic = static_cast<std::uint32_t>(
                gameState_.modularWeaponConfigStrings.begin()->first -
                WeaponConfigStringBase);
            if (error == std::errc{} && end == token.data() + token.size() &&
                requested >= firstDynamic &&
                (requested >= WeaponConfigStringCount ||
                    !gameState_.modularWeaponConfigStrings.contains(
                        static_cast<std::uint16_t>(
                            WeaponConfigStringBase + requested))))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "reliable weapon select REFUSED client=" +
                        std::to_string(clientNum) + " command=\"" + command +
                        "\" firstDynamic=" + std::to_string(firstDynamic) +
                        " -- the gamestate has no definition for that slot");
                return false;
            }
        }
        auto &client = clients_[clientNum];
        if (client.state == ClientState::Free ||
            client.reliableSequence - client.netchan.reliableAcknowledge >=
                ServerReliableCommandCapacity)
        {
            return false;
        }
        ++client.reliableSequence;
        client.reliableCommands[
            client.reliableSequence & (ServerReliableCommandCapacity - 1)] =
            {
                .kind = ServerReliableCommandKind::Text,
                .text = std::move(command),
            };
        return true;
    }

    bool SvClientSystem::canQueueReliableCommands(
        const std::uint32_t clientNum,
        const std::size_t count) const
    {
        if (clientNum >= clients_.size() || !count ||
            count > ServerReliableCommandCapacity)
        {
            return false;
        }
        const auto &client = clients_[clientNum];
        if (client.state == ClientState::Free)
            return false;
        const auto pending = client.reliableSequence -
            client.netchan.reliableAcknowledge;
        // Keep the same capacity interpretation as both reliable enqueue
        // paths: a ring with exactly `ServerReliableCommandCapacity` pending
        // entries is full, and an exact final reservation still fits.
        return pending <= ServerReliableCommandCapacity - count;
    }

    std::size_t SvClientSystem::SV_SetConfigString(
        const std::uint16_t index,
        std::string value)
    {
        // MEASURED (C-2021-7-25[1-19-26]dm.demo, re/demo-re/12-dm-timeline.txt):
        // a real free-for-all sends 123 distinct `d` records, 326 sends, from
        // serverTime 0 to the last second of the match. They are NOT mostly
        // player names. They are how a match acquires content it did not have
        // when the gamestate was built:
        //
        //   3636..3678  sound aliases, pushed as each killstreak/weapon is
        //               first used - `d 3648 mp_killstreak_carepackage` at 1:33
        //   12254..12278 model bone/tag names, pushed as each vehicle or model
        //               is first damaged - `d 12267 right_wheel_02_jnt` at 6:15
        //   864..871    localized pickup strings
        //   792..794    an attach record, `\ent\381\offs\0 0 0\mat\154\flags\0`
        //   15, 464     the match clock and ui_timelimit, CLEARED at 9:48.7
        //   11861       the end-of-match timescale ramp
        //   2557        the vision set switched to `mp_cross_fire_tp` at 10:05.7
        //
        // Without this the gamestate is the only configstring this server can
        // ever produce, which is why our own recordings carry 22 configstrings
        // against retail's 417 and not one `d` command.
        //
        // THE PLAYER-NAME RANGE IS REFUSED HERE ON PURPOSE. cs 2452+N is owned
        // by gameState.playerNames and SV_ValidateGameState checks the two agree
        // exactly; a raw write here would desynchronise them silently. It also
        // has no caller: section 107b predicted a late joiner would leave the
        // first client without the second's name, and MEASURING our own paired
        // recordings refuted it -- C-2026-8-23[2-50-4] and [2-50-15] BOTH carry
        // EDITz and EDITz2 at 2452/2453, because the lobby allocates the whole
        // roster before either client connects, so this session model has no
        // late joiner at all. When one exists, it gets a name-aware entry point
        // that moves playerNames and the configstring together.
        if (!gameStateConfigured_ ||
            (index >= PlayerNameConfigStringBase &&
                index < PlayerNameConfigStringBase + PlayerNameConfigStringCount))
        {
            return 0;
        }
        const auto existing = gameState_.configStrings.find(index);
        if (existing != gameState_.configStrings.end() &&
            existing->second == value)
        {
            return 0;
        }
        const auto command = "d " + std::to_string(index) + " " + value;
        if (command.size() >= 1024)
            return 0;
        gameState_.configStrings.insert_or_assign(index, std::move(value));

        // A client that has NOT been sent its gamestate yet must not get the
        // `d`: it would arrive describing a configstring the client has no
        // table for, and the value is already in the gamestate it is about to
        // receive. gamestateMessageNum is set when that message goes out.
        std::size_t queued{};
        for (std::uint32_t clientNum{}; clientNum < clients_.size(); ++clientNum)
        {
            if (clients_[clientNum].state == ClientState::Free ||
                !clients_[clientNum].gamestateMessageNum)
            {
                continue;
            }
            if (queueReliableCommand(clientNum, command))
                ++queued;
        }
        return queued;
    }

    std::optional<std::string> SvClientSystem::configString(
        const std::uint16_t index) const
    {
        const auto entry = gameState_.configStrings.find(index);
        return entry == gameState_.configStrings.end()
            ? std::nullopt
            : std::optional<std::string>(entry->second);
    }

    bool SvClientSystem::queueReliableBinaryCommand(
        const std::uint32_t clientNum,
        std::vector<std::uint8_t> payload)
    {
        // THE SAME BOUND AS SvProfilePatchMaximumPayload, and it used to be a second copy
        // spelled 0x3FC right here. A bare literal in a comparison is one of the three
        // documented ways a carried constant hides from every auditor in this tree: it is
        // not a constexpr, so audit-carried-constants cannot see it, and
        // audit-duplicate-constants is blind to a name with only one declaration site.
        //
        // OLMOD(section-85): CONFIRMED SAFE ON out.exe, and it is not the engine's
        // number at all -- it is a cap two bytes under the engine's real ceiling. The
        // client's store reads at most `push 400h` into a 0x404 frame and keeps at most
        // `push 3FFh` characters, identically on both builds (sub_46E3B0 / sub_4737E0),
        // so `verb + payload` may be 1023 and the payload 0x3FE. See
        // SvProfilePatchMaximumPayload's own comment for the instruction-level
        // comparison. Naming it still means a future correction lands in one place
        // instead of one and a half.
        if (clientNum >= clients_.size() || payload.empty() ||
            payload.size() > SvProfilePatchMaximumPayload)
        {
            return false;
        }
        auto &client = clients_[clientNum];
        if (client.state == ClientState::Free ||
            client.reliableSequence - client.netchan.reliableAcknowledge >=
                ServerReliableCommandCapacity)
        {
            return false;
        }
        ++client.reliableSequence;
        client.reliableCommands[
            client.reliableSequence & (ServerReliableCommandCapacity - 1)] =
            {
                .kind = ServerReliableCommandKind::Binary,
                .payload = std::move(payload),
            };
        return true;
    }

    std::optional<std::uint16_t> SvClientSystem::registerDynamicWeaponConfigString(
        SvModularWeaponConfigString configString,
        const std::uint16_t firstDynamicWeaponAssetIndex,
        const WeaponConfigStringCommandBuilder &buildCommand)
    {
        if (!gameStateConfigured_ || !firstDynamicWeaponAssetIndex)
            return std::nullopt;
        // APPEND into the gamestate's dynamic block, then BROADCAST the new
        // weapon to every connected client -- the retail behaviour, seamless.
        // The '%' write only trips out.exe's 181 index-vs-slot check
        // ([[codol-181-is-weapon-index-vs-slot]]) when the weapon's slot does
        // NOT equal the client's monotonic registration counter. That is a
        // GAMESTATE-ALIGNMENT problem, not a reason to avoid broadcasting: the
        // strip in refreshMemberLoadout (§161a) used to desync the count by one,
        // so the broadcast landed on the wrong slot. With the strip gone the
        // appended block is byte-identical to what SessionStart builds, so the
        // slot equals every client's next-free counter and the broadcast lands
        // clean -- and each client HAS the weapon before it renders another
        // player holding it, so no render crash either. NEW ONLY BROADCASTS:
        // SV_RegisterModularWeaponConfigString returns the existing index for a
        // duplicate without growing the table, so a weapon everyone already has
        // is not re-pushed.
        const auto before = gameState_.modularWeaponConfigStrings.size();
        const auto assetIndex = SV_RegisterModularWeaponConfigString(
            gameState_, firstDynamicWeaponAssetIndex, std::move(configString));
        if (!assetIndex)
            return std::nullopt;
        if (buildCommand &&
            gameState_.modularWeaponConfigStrings.size() != before)
        {
            const auto entry = gameState_.modularWeaponConfigStrings.find(
                static_cast<std::uint16_t>(
                    WeaponConfigStringBase + *assetIndex));
            if (entry != gameState_.modularWeaponConfigStrings.end())
            {
                const auto payload = buildCommand(*assetIndex, entry->second);
                if (!payload.empty())
                {
                    for (std::uint32_t clientNum = 0;
                         clientNum < clients_.size(); ++clientNum)
                    {
                        if (clients_[clientNum].state != ClientState::Free)
                        {
                            static_cast<void>(queueReliableBinaryCommand(
                                clientNum, payload));
                        }
                    }
                }
            }
        }
        return assetIndex;
    }





    bool SvClientSystem::queueLocalSound(
        const std::uint32_t clientNum,
        const std::uint16_t eventParameter)
    {
        const auto command = SV_BuildPlayLocalSoundCommand(eventParameter);
        return command && queueReliableCommand(clientNum, *command);
    }

    bool SvClientSystem::beginNextRound(const bool switchTeams)
    {
        const auto active = std::ranges::count_if(
            clients_, [](const ClientSlot &client) {
                return client.state == ClientState::Active &&
                    client.gameplayState == ClientGameplayState::Playing &&
                    (client.team == SvTeam::Tf || client.team == SvTeam::Sc);
            });
        if (!active)
            return false;
        for (auto &client : clients_)
        {
            if (client.state != ClientState::Active ||
                client.gameplayState != ClientGameplayState::Playing ||
                (client.team != SvTeam::Tf && client.team != SvTeam::Sc))
            {
                continue;
            }
            if (switchTeams)
            {
                client.team = client.team == SvTeam::Tf
                    ? SvTeam::Sc
                    : SvTeam::Tf;
                client.characterFaction = client.team == SvTeam::Tf
                    ? SvCharacterFaction::Tf
                    : SvCharacterFaction::Sc;
            }
            ++client.spawnSequence;
            if (!client.spawnSequence)
                ++client.spawnSequence;
            // (Section 169: the per-spawn clientInfo re-assertion that used to sit here
            // is deleted. `req{ALL-ZERO} valid=1 rebuild=1` was never a LOST clientInfo,
            // so re-sending could not have cured it -- the observer received the bytes
            // and decoded them against a baseline the message was not written with, and
            // a re-assertion against a section-local empty baseline is another instance
            // of that same defect rather than a retry for it.)
            client.pendingUserCmds.clear();
            client.lastQueuedUserCmdTime = client.lastReceivedUserCmd
                ? client.lastReceivedUserCmd->commandTime
                : 0;
        }
        return true;
    }

    bool SvClientSystem::setTeamScore(
        const SvTeam team,
        const std::int32_t score)
    {
        const auto index = team == SvTeam::Tf
            ? 0u
            : team == SvTeam::Sc ? 1u : teamScores_.size();
        if (index >= teamScores_.size())
            return false;
        teamScores_[index] = score;
        return true;
    }

    bool SvClientSystem::setClientScore(
        const std::uint32_t clientNum,
        const SvClientScore score)
    {
        if (clientNum >= clientScores_.size())
            return false;
        clientScores_[clientNum] = score;
        return true;
    }

    bool SvClientSystem::addClientScore(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto score = static_cast<std::int64_t>(
            clientScores_[clientNum].score) + delta;
        clientScores_[clientNum].score = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(score, 0, 1'000'000));
        return true;
    }

    bool SvClientSystem::addClientKills(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto kills = static_cast<std::int64_t>(
            clientScores_[clientNum].kills) + delta;
        clientScores_[clientNum].kills = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(kills, 0, 1'000'000));
        return true;
    }

    bool SvClientSystem::addClientDeaths(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto deaths = static_cast<std::int64_t>(
            clientScores_[clientNum].deaths) + delta;
        clientScores_[clientNum].deaths = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(deaths, 0, 1'000'000));
        if (delta > 0)
            clientScores_[clientNum].killstreak = 0;
        return true;
    }

    bool SvClientSystem::addClientStreak(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
            return false;
        const auto streak = static_cast<std::int64_t>(
            clientScores_[clientNum].killstreak) + delta;
        clientScores_[clientNum].killstreak = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(streak, 0, 1'000'000));
        return true;
    }

    bool SvClientSystem::addClientDowns(const std::uint32_t clientNum)
    {
        if (clientNum>=clients_.size() || clients_[clientNum].state==ClientState::Free) return false;
        auto &score=clientScores_[clientNum];
        score.downs=std::min(score.downs+1,1'000'000);
        return true;
    }

    bool SvClientSystem::addClientRevives(const std::uint32_t clientNum)
    {
        if (clientNum >= clients_.size() || clients_[clientNum].state == ClientState::Free)
            return false;
        clientScores_[clientNum].revives = std::min(clientScores_[clientNum].revives + 1, 1'000'000);
        return true;
    }

    bool SvClientSystem::addClientHeadshots(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto headshots = static_cast<std::int64_t>(
            clientScores_[clientNum].headshots) + delta;
        clientScores_[clientNum].headshots = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(headshots, 0, 1'000'000));
        return true;
    }

    bool SvClientSystem::addClientXp(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto xp = static_cast<std::int64_t>(
            clientScores_[clientNum].xp) + delta;
        clientScores_[clientNum].xp = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(
                xp, 0, std::numeric_limits<std::int32_t>::max()));
        return true;
    }

    std::optional<SvClientScore> SvClientSystem::clientScore(
        const std::uint32_t clientNum) const
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return std::nullopt;
        }
        return clientScores_[clientNum];
    }

    void SvClientSystem::announceConnectionChanges()
    {
        // MEASURED (dm demo, seq 12/105/590): a client joining mid-match makes
        // the server broadcast
        //   f "MP_CONNECTED<FE><base64 name><FE>^7"
        // and the recording client gets its own at serverTime 0. The 0xFE pair
        // and the base64 are the same encoding SV_EncodePlayerName already
        // produces for the player-name configstring, so this reuses it rather
        // than inventing a second one.
        //
        // CODREF: CG_ServerCommand 0x0057D560 cases 'e' and 'f' both reach
        // sub_AE2EA0 with argv(1) as the text.
        for (std::uint32_t clientNum{}; clientNum < clients_.size(); ++clientNum)
        {
            if (clients_[clientNum].state != ClientState::Active ||
                connectionAnnounced_.contains(clientNum))
            {
                continue;
            }
            // Claimed BEFORE the roster lookup, exactly as this did when it was a
            // set: a slot whose name cannot be encoded must not be retried every
            // frame. The name is filled in below once there is one, and a slot
            // still holding the empty string is simply not announced as leaving.
            connectionAnnounced_.insert_or_assign(clientNum, std::string{});
            const auto *roster = activeRoster_
                ? sessionMemberForXuid(*activeRoster_, clients_[clientNum].xuid)
                : nullptr;
            if (!roster)
                continue;
            const auto encoded = SV_EncodePlayerName(roster->username);
            if (!encoded)
                continue;
            connectionAnnounced_.insert_or_assign(clientNum, *encoded);
            std::string text = "f \"MP_CONNECTED";
            text.push_back(static_cast<char>(0xFE));
            text.append(*encoded);
            text.push_back(static_cast<char>(0xFE));
            text.append("^7\"");
            for (std::uint32_t target{}; target < clients_.size(); ++target)
            {
                if (clients_[target].state != ClientState::Free)
                    static_cast<void>(queueReliableCommand(target, text));
            }
        }
        // MEASURED (retail 2021 corpus, verb 'e', 9 distinct / 35 total):
        //   e "<FE>base64<FE>^7 EXE_LEFTGAME"
        // The same 0xFE-wrapped base64 name as 'f', with the reason INSIDE the
        // quotes after `^7 ` and no MP_ prefix. CG_ServerCommand case 101 ('e')
        // and case 102 ('f') reach the same sink 0x0044D170, so the pair is one
        // feature and this tree was sending half of it.
        //
        // CODDIFF(leave-reason): retail also uses EXE_TIMEDOUT and
        // EXE_PLAYERKICKED_BOT_BALANCE. A slot going Free is all this sees, so
        // every departure is announced as EXE_LEFTGAME; telling a timeout apart
        // means carrying the cause out of takeTimeoutDrops, which is a separate
        // change.
        for (auto it = connectionAnnounced_.begin();
             it != connectionAnnounced_.end();)
        {
            if (it->first < clients_.size() &&
                clients_[it->first].state != ClientState::Free)
            {
                it = std::next(it);
                continue;
            }
            if (it->second.empty())
            {
                it = connectionAnnounced_.erase(it);
                continue;
            }
            std::string text = "e \"";
            text.push_back(static_cast<char>(0xFE));
            text.append(it->second);
            text.push_back(static_cast<char>(0xFE));
            text.append("^7 EXE_LEFTGAME\"");
            for (std::uint32_t target{}; target < clients_.size(); ++target)
            {
                if (clients_[target].state != ClientState::Free)
                    static_cast<void>(queueReliableCommand(target, text));
            }
            it = connectionAnnounced_.erase(it);
        }
    }

    // THE ZM ROUND HUD, ON A LATER TICK (12.132).
    //
    // 12.131 sent these four dvars inside the `gameStateUpdateStage == 6` branch
    // -- the frame the client turns Active -- and the client stalled at
    // "waiting for connection". `queueReliableCommand` refuses once
    // `reliableSequence - reliableAcknowledge >= ServerReliableCommandCapacity`,
    // and at enter-world the client has acknowledged NOTHING, so four commands
    // pushed into that window is exactly where the reliable stream desyncs.
    //
    // Retail's own timing said so and 12.131 did not read it: the gamestate goes
    // out at 10950 and `s ui_hud_round "1"` at 20250 -- NINE SECONDS LATER, not
    // at enter-world.
    //
    // So the gate here is the property that actually matters, not a timer:
    // the client must have acknowledged EVERYTHING already queued
    // (`reliableAcknowledge == reliableSequence`), which means the queue is empty
    // and the client is settled. A frame delay is layered on top so this cannot
    // fire in the transition frame even if the counters momentarily agree.
    namespace
    {
        // THE LIVE ROUND, set by the gametype script through `zmsetround` and read
        // here. Atomic for the same reason gZmActorWalkAnim is: the script runs on
        // the server thread but this publisher is reached from the client system,
        // and a torn read would put a nonsense round on a player's HUD.
        std::atomic<std::uint32_t> gZmRound{ 1 };
        std::atomic<std::uint32_t> gZmRoundGoal{ 8 };
    }

    void SV_SetZmRound(const std::uint32_t round, const std::uint32_t goal)
    {
        gZmRound.store(round ? round : 1u);
        gZmRoundGoal.store(goal);
    }

    void SvClientSystem::publishZmRoundHud(const std::uint32_t frameNumber)
    {
        if constexpr (!SvPublishZmRoundHud)
            return;
        if (gameState_.gameType != "zm")
            return;
        const auto round = gZmRound.load();
        const auto goal = gZmRoundGoal.load();
        const std::array<std::string, 4> roundHud{
            "s ui_hud_final_round \"0\"",
            "s ui_hud_special_round \"0\"",
            "s ui_hud_round \"" + std::to_string(round) + "\"",
            "s ui_hud_round_goal \"" + std::to_string(goal) + "\"",
        };
        // 200 frames at the 20 Hz snapshot rate is ~10 s, which is retail's own
        // gamestate-to-round-HUD gap. It is a floor, not a schedule.
        constexpr std::uint32_t settleFrames = 200;
        for (std::uint32_t clientNum{}; clientNum < clients_.size(); ++clientNum)
        {
            const auto &client = clients_[clientNum];
            if (client.state == ClientState::Free)
            {
                zmRoundHudFirstFrame_.erase(clientNum);
                zmRoundHudSent_.erase(clientNum);
                continue;
            }
            if (client.state != ClientState::Active)
                continue;
            const auto [entry, inserted] =
                zmRoundHudFirstFrame_.try_emplace(clientNum, frameNumber);
            if (inserted)
                continue;
            // RE-SENT WHEN THE ROUND CHANGES, not once per life. The first cut
            // recorded "sent" in a set and never spoke again, which was correct
            // while the round was a constant and is wrong now that a director
            // advances it. The map holds the round each client was last told.
            const auto sent = zmRoundHudSent_.find(clientNum);
            if (sent != zmRoundHudSent_.end() && sent->second == round)
                continue;
            if (frameNumber - entry->second < settleFrames)
                continue;
            // THE SAFETY CONDITION. An empty reliable queue guarantees room for
            // all four and proves the client is keeping up.
            if (client.netchan.reliableAcknowledge != client.reliableSequence)
                continue;
            bool all = true;
            for (const auto &command : roundHud)
            {
                if (!queueReliableCommand(clientNum, command.c_str()))
                {
                    all = false;
                    break;
                }
            }
            if (all)
                zmRoundHudSent_[clientNum] = round;
        }
    }

    void SvClientSystem::pushScoreboardToConnected()
    {
        for (std::uint32_t clientNum{}; clientNum < clients_.size(); ++clientNum)
        {
            if (clients_[clientNum].state != ClientState::Free)
                queueScoreboardResponse(clientNum);
        }
    }

    void SvClientSystem::setAarRoundNumber(const std::int32_t roundNumber)
    {
        aarRoundNumber_ = std::max(0, roundNumber);
    }

    std::optional<std::pair<std::uint32_t, std::int32_t>>
        SvClientSystem::bestClientKills() const
    {
        std::optional<std::pair<std::uint32_t, std::int32_t>> best;
        std::int32_t bestDeaths{};
        for (std::size_t index = 0; index < clients_.size(); ++index)
        {
            if (clients_[index].state == ClientState::Free)
                continue;
            const auto score = clientScores_[index].kills;
            const auto deaths = clientScores_[index].deaths;
            if (!best || score > best->second ||
                (score == best->second && deaths < bestDeaths))
            {
                best = { static_cast<std::uint32_t>(index), score };
                bestDeaths = deaths;
            }
        }
        return best;
    }

    std::vector<std::pair<std::uint32_t, std::int32_t>>
        SvClientSystem::topClientsByKills(const std::size_t count) const
    {
        std::vector<std::pair<std::uint32_t, std::int32_t>> ranked;
        ranked.reserve(clients_.size());
        for (std::size_t index = 0; index < clients_.size(); ++index)
        {
            if (clients_[index].state == ClientState::Free)
                continue;
            ranked.emplace_back(
                static_cast<std::uint32_t>(index), clientScores_[index].kills);
        }
        // IW4 _gamescore.gsc::getBetterPlayer independently gives the shipped
        // order: score first, then fewer deaths. In CODOL FFA the primary score
        // is 50*kills, while the score limit itself remains kill-count based.
        // stable_sort preserves the lower slot when both values are equal.
        std::ranges::stable_sort(
            ranked, [this](const auto &left, const auto &right) {
                if (left.second != right.second)
                    return left.second > right.second;
                return clientScores_[left.first].deaths <
                    clientScores_[right.first].deaths;
            });
        if (ranked.size() > count)
            ranked.resize(count);
        return ranked;
    }

    bool SvClientSystem::addTeamScoreForClient(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return false;
        }
        const auto team = clients_[clientNum].team;
        const auto index = team == SvTeam::Tf
            ? 0u
            : team == SvTeam::Sc ? 1u : teamScores_.size();
        if (index >= teamScores_.size())
            return false;
        const auto score = static_cast<std::int64_t>(teamScores_[index]) + delta;
        teamScores_[index] = static_cast<std::int32_t>(
            std::clamp<std::int64_t>(score, 0, 1'000'000));
        return true;
    }

    std::optional<std::int32_t> SvClientSystem::teamScore(const SvTeam team) const
    {
        const auto index = team == SvTeam::Tf
            ? 0u
            : team == SvTeam::Sc ? 1u : teamScores_.size();
        return index < teamScores_.size()
            ? std::optional{ teamScores_[index] }
            : std::nullopt;
    }

    void SvClientSystem::queueScoreboardResponse(const std::uint32_t clientNum)
    {
        if (clientNum >= clients_.size())
            return;

        const auto connectedClientCount = static_cast<std::uint32_t>(std::count_if(
            clients_.begin(), clients_.end(), [](const ClientSlot &client) {
                return client.state != ClientState::Free;
            }));
        const auto &target = clients_[clientNum];
        const auto pendingCount = target.reliableSequence -
            target.netchan.reliableAcknowledge;
        if (target.state == ClientState::Free)
            return;

        // OLMOD(scoreboard-response): CODOL's removed dedicated producer is
        // unavailable. This source producer is constrained by the retained
        // client chain CL_ParseServerMessage 0x0046E6A0 -> sub_46E470 ->
        // sub_57E330 -> sub_57BF70 -> CG_InitScoreboardFromProfile 0x0057B760.
        //
        // CODDIFF(scoreboard-response): this used to send C/D/E, which set the
        // two team scores and one row's score and nothing else - so kills,
        // deaths and assists had no producer and their columns never moved. The
        // reason no command produces them is that no command can: 0x0057B760
        // rebuilds every row out of the mp/playerdata.def profile blob, and the
        // blob is written by the 'J' patch stream. C/D/E are gone because the
        // rebuild sets the team scores and the score column too.
        std::vector<SvScoreboardEntry> entries;
        entries.reserve(connectedClientCount);
        for (std::uint32_t scoreClientNum{};
             scoreClientNum < clients_.size() &&
                 scoreClientNum < SvScoreboardRowCount;
             ++scoreClientNum)
        {
            if (clients_[scoreClientNum].state == ClientState::Free)
                continue;
            const auto &score = clientScores_[scoreClientNum];
            entries.push_back({
                .clientNum = scoreClientNum,
                .userId = clients_[scoreClientNum].xuid,
                .score = score.score,
                .kills = score.kills,
                .deaths = score.deaths,
                .assists = score.assists,
                .headshots = score.headshots,
                .objectives = score.objectives,
                .downs = score.downs,
                .revives = score.revives,
                .killstreak = score.killstreak,
                .xp = score.xp,
                .gp = score.gp,
            });
        }

        const auto commands = SV_FrameProfilePatchCommands(
            SV_BuildScoreboardProfilePatches(
                entries,
                {
                    .roundNumber = aarRoundNumber_,
                    .scoreLimit = gameState_.uiGameRules
                        ? static_cast<std::int32_t>(
                              gameState_.uiGameRules->scoreLimit)
                        : 0,
                    .teamScoreTf = teamScores_[0],
                    .teamScoreSc = teamScores_[1],
                }),
            SvProfilePatchMaximumPayload);
        if (pendingCount + commands.size() > ServerReliableCommandCapacity)
            return;
        for (const auto &command : commands)
            static_cast<void>(queueReliableBinaryCommand(clientNum, command));
    }

    void SvClientSystem::reset()
    {
        std::fill(challenges_.begin(), challenges_.end(), ChallengeRecord{});
        std::fill(clients_.begin(), clients_.end(), ClientSlot{});
        nonce_ = 0;
        worldFrame_.reset();
        worldFrameConfigured_ = false;
        teamScores_ = {};
        std::fill(clientScores_.begin(), clientScores_.end(), SvClientScore{});
        aarRoundNumber_ = 0;
        gameStateMessagesSent_ = 0;
        gameStateUpdatesReceived_ = 0;
        snapshotMessagesSent_ = 0;
        fullSnapshotMessagesSent_ = 0;
        deltaSnapshotMessagesSent_ = 0;
        nextSnapshotSendClient_ = 0;
        pendingRoster_.reset();
        activeRoster_.reset();
    }

    bool SvClientSystem::stageSessionRoster(
        const std::uint64_t generation,
        const std::span<const SessionRosterMember> members)
    {
        if (!generation || members.empty() || members.size() > clients_.size())
            return false;
        std::vector<SessionRosterMember> normalized(members.begin(), members.end());
        if (std::ranges::any_of(normalized, [](const auto &member) {
                return !member.xuid || !SV_EncodePlayerName(member.username);
            }))
        {
            return false;
        }
        std::ranges::sort(normalized, {}, &SessionRosterMember::xuid);
        if (std::ranges::adjacent_find(
                normalized,
                {},
                &SessionRosterMember::xuid) != normalized.end())
        {
            return false;
        }
        if (pendingRoster_)
        {
            return pendingRoster_->generation == generation &&
                pendingRoster_->members == normalized;
        }
        pendingRoster_ = SessionRoster{
            .generation = generation,
            .members = std::move(normalized),
        };
        // A MEMBER THAT IS ALREADY CONNECTED MUST BE MOVED TO ITS ORDINAL, OR
        // THE OWNER OF THE SEAT IT IS SITTING IN IS REFUSED AS SERVER-FULL --
        // the 房间人数已满 box.
        //
        // The roster fixes each member's slot by its ordinal in the
        // xuid-sorted member list, and the gamestate commits player names in
        // that same order, so the ordinals cannot simply be reassigned around
        // whoever happens to be seated. A client that connects BEFORE the
        // session is staged has no roster to place it and takes the first
        // free slot; when the roster then arrives, that slot is somebody
        // else's ordinal. Measured on three consecutive cycles 2026-08-24:
        //
        //     17:13:11  SessionStart queued members=2
        //     17:13:12  connectionless rejected reason=the session roster
        //                 client slot is occupied
        //     17:13:15  commitSessionRoster rosterMembers=[69420,69421]
        //                 connectedClients=[69421@gen0]
        //
        // 69421 was already sitting in slot 0, which is 69420's ordinal, and
        // 69420 got the box every time. Note this is NOT the same hole as the
        // challenge rebinding a few lines into findChallenge: that already
        // handles a generation-0 challenge presented AFTER the roster exists.
        // This is the client that finished connecting BEFORE it.
        //
        // ONLY A CLIENT THAT HAS NOT BEEN SENT A GAMESTATE MAY MOVE. Its slot
        // index is its clientNum and nothing has told it that number yet;
        // past Connected it has, so it keeps its seat and the collision falls
        // through to the reject, which is at least honest about itself.
        for (std::size_t ordinal = 0;
             ordinal < pendingRoster_->members.size(); ++ordinal)
        {
            const auto xuid = pendingRoster_->members[ordinal].xuid;
            auto &seat = clients_[ordinal];
            if (seat.state != ClientState::Free && seat.xuid == xuid)
                continue;
            if (seat.state != ClientState::Free &&
                seat.state != ClientState::Connected)
            {
                continue;
            }
            const auto seated = std::find_if(
                clients_.begin(),
                clients_.end(),
                [&](const ClientSlot &client) {
                    return client.state == ClientState::Connected &&
                        client.xuid == xuid;
                });
            if (seated == clients_.end())
                continue;
            std::clog << "[dedicated/game-server] session roster relocates "
                      << "client xuid=" << xuid << " slot="
                      << (seated - clients_.begin()) << " -> " << ordinal
                      << " generation=" << generation << '\n';
            std::swap(seat, *seated);
        }
        return true;
    }

    bool SvClientSystem::commitSessionRoster(const std::uint64_t generation)
    {
        if (!pendingRoster_ || pendingRoster_->generation != generation)
            return false;
        activeRoster_ = std::move(pendingRoster_);
        pendingRoster_.reset();
        // The adoption below did not fire on its first live run and the code alone cannot say
        // why -- the client's xuid and the roster's are both plausible and only one comparison
        // separates them. Print both sides before deciding, once per commit.
        {
            std::string members;
            if (activeRoster_)
            {
                for (const auto &member : activeRoster_->members)
                    members += (members.empty() ? "" : ",") + std::to_string(member.xuid);
            }
            std::string connected;
            for (const auto &client : clients_)
            {
                if (client.state == ClientState::Free)
                    continue;
                connected += (connected.empty() ? "" : ",") + std::to_string(client.xuid) +
                    "@gen" + std::to_string(client.sessionGeneration);
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "commitSessionRoster generation=" + std::to_string(generation) +
                    " rosterMembers=[" + members + "] connectedClients=[" +
                    (connected.empty() ? std::string("none") : connected) + "]");
        }
        for (auto &client : clients_)
        {
            if (client.state == ClientState::Free ||
                client.sessionGeneration == generation)
            {
                continue;
            }
            // A client that is IN the new roster is not a leftover from some
            // previous session -- it is this session's player, which connected
            // during setup and is now being told which session it belongs to.
            // Wiping it on generation alone is what made every live run end in
            // "netchan packet has no connected client slot": the client
            // completed DTLS and connected, SessionStart committed a roster
            // carrying a new generation twenty seconds later, and the slot it
            // was already using was thrown away underneath it. Adopt it
            // instead, and keep wiping only the clients the new roster does
            // not name.
            const auto inRoster = activeRoster_ &&
                std::ranges::any_of(
                    activeRoster_->members,
                    [&client](const SessionRosterMember &member) {
                        return member.xuid && member.xuid == client.xuid;
                    });
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("commitSessionRoster ") +
                    (inRoster ? "ADOPTING" : "WIPING") + " client xuid=" +
                    std::to_string(client.xuid) + " gen=" +
                    std::to_string(client.sessionGeneration) + " -> " +
                    std::to_string(generation));
            if (inRoster)
            {
                client.sessionGeneration = generation;
                continue;
            }
            client = {};
        }
        for (auto &challenge : challenges_)
        {
            if (challenge.valid && challenge.sessionGeneration != generation)
                challenge = {};
        }
        return true;
    }

    bool SvClientSystem::rollbackSessionRoster(const std::uint64_t generation)
    {
        if (!pendingRoster_ || pendingRoster_->generation != generation)
            return false;
        // The other half of the enumeration. Exactly three places clear a client slot:
        // SV_CheckTimeouts, which records a TimeoutDrop and is therefore never silent;
        // commitSessionRoster; and here. A live run loses its client with no timeout logged, so
        // it is one of the two roster paths.
        //
        // IT IS commitSessionRoster, not this one. This path only runs on a FAILED configure,
        // and the log separates them cleanly: every ACCEPTED configure is followed within a
        // second by clients=0, while the single run that FAILED at stage=server_commit_failed
        // kept its client alive for twenty more seconds. Failure spares the client; success
        // takes it.
        for (auto &client : clients_)
        {
            if (client.state == ClientState::Free ||
                client.sessionGeneration != generation)
            {
                continue;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "rollbackSessionRoster WIPING client xuid=" +
                    std::to_string(client.xuid) + " gen=" +
                    std::to_string(client.sessionGeneration) +
                    " rolledBack=" + std::to_string(generation));
            client = {};
        }
        for (auto &challenge : challenges_)
        {
            if (challenge.valid && challenge.sessionGeneration == generation)
                challenge = {};
        }
        pendingRoster_.reset();
        return true;
    }

    bool SvClientSystem::sessionAllowsXuid(const std::uint64_t xuid) const
    {
        const auto &roster = pendingRoster_ ? pendingRoster_ : activeRoster_;
        return !roster || sessionMemberForXuid(*roster, xuid);
    }

    const SvClientSystem::SessionRoster *
    SvClientSystem::sessionRosterForGeneration(
        const std::uint64_t generation) const
    {
        if (pendingRoster_ && pendingRoster_->generation == generation)
            return &*pendingRoster_;
        if (activeRoster_ && activeRoster_->generation == generation)
            return &*activeRoster_;
        return nullptr;
    }

    const SessionRosterMember *SvClientSystem::sessionMemberForXuid(
        const SessionRoster &roster,
        const std::uint64_t xuid) const
    {
        const auto member = std::ranges::lower_bound(
            roster.members, xuid, {}, &SessionRosterMember::xuid);
        return member != roster.members.end() && member->xuid == xuid
            ? &*member
            : nullptr;
    }

    std::uint64_t SvClientSystem::sessionGenerationForXuid(
        const std::uint64_t xuid) const
    {
        if (pendingRoster_ && sessionMemberForXuid(*pendingRoster_, xuid))
        {
            return pendingRoster_->generation;
        }
        if (activeRoster_ && sessionMemberForXuid(*activeRoster_, xuid))
        {
            return activeRoster_->generation;
        }
        return 0;
    }

    bool SvClientSystem::clientGenerationIsActive(const ClientSlot &client) const
    {
        if (!client.sessionGeneration)
            return !pendingRoster_ && !activeRoster_;
        return activeRoster_ &&
            client.sessionGeneration == activeRoster_->generation;
    }

    bool SvClientSystem::configureGameState(
        SvGameState gameState,
        const std::uint64_t sessionGeneration)
    {
        if (sessionGeneration &&
            (!pendingRoster_ || pendingRoster_->generation != sessionGeneration))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "gamestate commit rejected roster generation requested=" +
                    std::to_string(sessionGeneration) + " pending=" +
                    std::to_string(
                        pendingRoster_ ? pendingRoster_->generation : 0));
            return false;
        }
        if (sessionGeneration)
        {
            std::vector<std::string> expectedNames;
            expectedNames.reserve(pendingRoster_->members.size());
            std::ranges::transform(
                pendingRoster_->members,
                std::back_inserter(expectedNames),
                &SessionRosterMember::username);
            if (gameState.playerNames != expectedNames)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "gamestate commit rejected player names gameState=" +
                        std::to_string(gameState.playerNames.size()) +
                        " roster=" + std::to_string(expectedNames.size()));
                return false;
            }
        }
        if (!SV_ValidateGameState(gameState))
        {
            const auto weaponCount = gameState.configStrings.find(
                WeaponCountConfigStringIndex);
            const auto firstModular = gameState.modularWeaponConfigStrings.empty()
                ? 0
                : gameState.modularWeaponConfigStrings.begin()->first;
            const auto lastModular = gameState.modularWeaponConfigStrings.empty()
                ? 0
                : gameState.modularWeaponConfigStrings.rbegin()->first;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "gamestate commit rejected validation configStrings=" +
                    std::to_string(gameState.configStrings.size()) +
                    " simpleWeapons=" +
                    std::to_string(gameState.simpleWeaponConfigStrings.size()) +
                    " modularWeapons=" +
                    std::to_string(gameState.modularWeaponConfigStrings.size()) +
                    " modularRange=" + std::to_string(firstModular) + ".." +
                    std::to_string(lastModular) + " weaponCount=" +
                    (weaponCount == gameState.configStrings.end()
                        ? std::string("<missing>")
                        : weaponCount->second));
            return false;
        }
        gameState_ = std::move(gameState);
        gameStateConfigured_ = true;
        teamScores_ = {};
        std::fill(clientScores_.begin(), clientScores_.end(), SvClientScore{});
        for (auto &client : clients_)
        {
            client.gameplayState = ClientGameplayState::Inactive;
            client.selectedLoadout.clear();
            client.loadoutSequence = 0;
            client.spawnSequence = 0;
            client.characterFaction = SvCharacterFaction::Tf;
            client.team = SvTeam::None;
            client.pendingSelectedLoadout.clear();
            client.pendingLoadoutSequence = 0;
            client.pendingCharacterFaction = SvCharacterFaction::Tf;
            client.pendingTeam = SvTeam::None;
            client.lastMenuResponse.reset();
        }
        clearWorldFrame();
        if (sessionGeneration)
        {
            // Generation was validated before any state mutation, so commit
            // cannot fail and gamestate/identity become visible together.
            static_cast<void>(commitSessionRoster(sessionGeneration));
        }
        return true;
    }

    bool SvClientSystem::setWorldFrame(
        SvSnapshotFrame frame,
        SvSnapshotFrameValidationFailure *failure)
    {
        if (!SV_ValidateSnapshotFrame(frame, failure))
            return false;
        worldFrame_ = std::make_shared<const SvSnapshotFrame>(std::move(frame));
        worldFrameConfigured_ = true;
        return true;
    }

    void SvClientSystem::clearWorldFrame()
    {
        worldFrame_.reset();
        worldFrameConfigured_ = false;
        for (auto &client : clients_)
        {
            client.snapshotHistory = {};
            client.lastSnapshotServerTime = 0;
            client.snapshotSent = false;
            client.baselineCacheAcknowledged = false;
            client.baselineCacheInitializationMessage.reset();
            // Section 170: see the enter-world reset. snapshotHistory is cleared three
            // lines up, so the flagged-generation marker has to go with it.
            client.newestFlaggedSnapshotMessage.reset();
            client.baselineFrame.reset();
        }
    }

    void SvClientSystem::setGameplayAuthorityReady(const bool ready)
    {
        gameplayAuthorityReady_ = ready;
        if (ready)
            return;
        for (auto &client : clients_)
        {
            client.pendingUserCmds.clear();
            client.lastQueuedUserCmdTime = client.lastReceivedUserCmd
                ? client.lastReceivedUserCmd->commandTime
                : 0;
        }
    }

    std::size_t SvClientSystem::autoSelectMissingLoadouts(
        const std::uint32_t nowMilliseconds)
    {
        // WHY THIS EXISTS. Every gate from SessionStart to a spawned player is automatic
        // except one: the class pick, which arrives as a changeclass menu response from the
        // client's own UI. That single human step made every test cycle need somebody
        // watching the screen, and the things still being debugged -- movement, the
        // viewmodel, the DObj -- are all AFTER it. So synthesize the same response the
        // client would send, through the same dispatcher, and let the rest of the flow run
        // untouched.
        //
        // Deliberately NOT a gameplay behaviour: it is off unless OLMOD_AUTO_LOADOUT=1, it
        // only ever fires for a client that has been Active for a while without choosing,
        // and it picks custom1 -- the first class the session roster registered. A real pick
        // arriving first wins, because pendingSelectedLoadout is then already set.
        static const bool enabled = [] {
            char *value{};
            std::size_t size{};
            if (_dupenv_s(&value, &size, "OLMOD_AUTO_LOADOUT") != 0 || !value)
                return false;
            const auto on = value[0] == '1';
            std::free(value);
            return on;
        }();
        if (!enabled)
            return 0;

        // EVERY MILLISECOND OF THIS GRACE IS A FRAME THE CLIENT CAN DIE IN.
        //
        // While a client is Active with no loadout, SV_BuildPlayerState publishes
        // `viewmodelIndex = 0` and `currentWeaponAssetIndex = 0` (sv_snapshot_mp.cpp,
        // the !effectivePlaying branch). A viewmodel index of zero makes the CLIENT's
        // sub_53F5F0 return null -- its record's type tag is neither 1 nor 2 -- and
        // sub_59CC70 writes through it unchecked. Measured from a remote player's own
        // log: rva=0x019CE15, edi=0, target=0x3EC, weaponIndex=0. HANDOFF section 152y.
        //
        // Four seconds is why only REMOTE players die: on loopback the spawn lands
        // almost immediately, so few or no frames are drawn unarmed; over a VPN the
        // client sits in the window and eventually draws one.
        //
        // 500 ms keeps the intent -- a human class pick still wins, because a real
        // pick sets pendingSelectedLoadout and this loop skips any client that has one
        // -- while cutting the exposure eightfold. OLMOD_AUTO_LOADOUT_GRACE_MS retunes
        // it without a rebuild; 0 is refused because it would fire before the client
        // has finished connecting.
        //
        // THIS SHORTENS THE WINDOW, IT DOES NOT CLOSE IT. The real fix is to stop
        // publishing a zero viewmodel index at all, which needs a valid stand-in and
        // is a bigger change than a tired session should make.
        static const std::uint32_t GraceMilliseconds = [] {
            constexpr std::uint32_t fallback = 500;
            char *value{};
            std::size_t size{};
            if (_dupenv_s(&value, &size, "OLMOD_AUTO_LOADOUT_GRACE_MS") != 0 || !value)
                return fallback;
            std::uint32_t parsed{};
            const auto *const first = value;
            const auto *const last = value + std::strlen(value);
            const auto [pointer, error] = std::from_chars(first, last, parsed);
            const auto ok = error == std::errc{} && pointer == last && parsed &&
                parsed <= 60'000;
            std::free(value);
            return ok ? parsed : fallback;
        }();
        std::size_t picked{};
        for (std::uint32_t clientNum{}; clientNum < clients_.size(); ++clientNum)
        {
            auto &client = clients_[clientNum];
            if (client.state != ClientState::Active ||
                client.gameplayState == ClientGameplayState::Playing ||
                !client.pendingSelectedLoadout.empty() ||
                !client.selectedLoadout.empty())
            {
                continue;
            }
            if (!client.connectTime ||
                nowMilliseconds - client.connectTime < GraceMilliseconds)
            {
                continue;
            }
            ClientMenuResponse response{
                .sequence = client.pendingLoadoutSequence + 1,
                .serverId = 0,
                .menuIndex = 0,
                .menuName = "changeclass_marines",
                .response = "custom1",
            };
            if (!SV_DispatchMenuResponse(client, response, teamPolicy()))
                continue;
            ++picked;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "auto loadout selected client=" + std::to_string(clientNum) +
                    " class=custom1 (OLMOD_AUTO_LOADOUT)");
        }
        return picked;
    }

    bool SvClientSystem::commitPendingLoadout(
        const std::uint32_t clientNum,
        const std::uint32_t pendingSequence)
    {
        if (clientNum >= clients_.size())
            return false;
        auto &client = clients_[clientNum];
        // SvTeam::None means two different things here: "the client has not picked
        // a side yet", which must not commit, and "this gametype has no sides",
        // which must. Refusing both left every free-for-all player stuck in
        // WaitingForLoadout - the class menu was accepted, the pending sequence
        // climbed with every retry, and the loadout could never commit, so nobody
        // ever spawned or received a weapon.
        //
        // The other two conditions already establish that a class WAS chosen, so
        // for a teamless gametype the team check has nothing left to add.
        if (client.state != ClientState::Active ||
            client.pendingSelectedLoadout.empty() ||
            client.pendingLoadoutSequence != pendingSequence ||
            (client.pendingTeam == SvTeam::None &&
                teamPolicy() != SvTeamPolicy::FreeForAll))
        {
            return false;
        }

        const auto enteringPlaying =
            client.gameplayState != ClientGameplayState::Playing;
        client.selectedLoadout = std::move(client.pendingSelectedLoadout);
        client.loadoutSequence = client.pendingLoadoutSequence;
        client.characterFaction = client.pendingCharacterFaction;
        client.team = client.pendingTeam;
        client.pendingSelectedLoadout.clear();
        client.pendingLoadoutSequence = 0;
        client.pendingTeam = SvTeam::None;
        client.gameplayState = ClientGameplayState::Playing;
        if (enteringPlaying)
        {
            ++client.spawnSequence;
            if (!client.spawnSequence)
                ++client.spawnSequence;
            // (Section 169: the per-spawn clientInfo re-assertion that used to sit here
            // is deleted. `req{ALL-ZERO} valid=1 rebuild=1` was never a LOST clientInfo,
            // so re-sending could not have cured it -- the observer received the bytes
            // and decoded them against a baseline the message was not written with, and
            // a re-assertion against a section-local empty baseline is another instance
            // of that same defect rather than a retry for it.)
            client.pendingUserCmds.clear();
            client.lastQueuedUserCmdTime = client.lastReceivedUserCmd
                ? client.lastReceivedUserCmd->commandTime
                : 0;
        }
        return true;
    }

    std::optional<SvResolvedLoadout>
    SvClientSystem::resolveAndCommitPendingLoadout(
        const std::uint32_t clientNum,
        const LoadoutProvider &provider)
    {
        if (!gameplayAuthorityReady_ || !provider || clientNum >= clients_.size())
            return std::nullopt;
        const auto &client = clients_[clientNum];
        if (client.state != ClientState::Active ||
            client.pendingSelectedLoadout.empty())
        {
            return std::nullopt;
        }

        const auto pendingSequence = client.pendingLoadoutSequence;
        auto loadout = provider(client.xuid, client.pendingSelectedLoadout);
        if (!loadout || !SV_IsResolvedLoadoutValid(*loadout) ||
            !commitPendingLoadout(clientNum, pendingSequence))
        {
            return std::nullopt;
        }
        return loadout;
    }

    SvClientSystem::ChallengeRecord &SvClientSystem::SV_GetChallenge(
        const PeerAddress peer,
        const std::uint64_t xuid,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        for (auto &record : challenges_)
        {
            if (record.valid && !record.connected && record.peer == peer &&
                record.xuid == xuid &&
                record.sessionGeneration == sessionGenerationForXuid(xuid) &&
                !expired(nowMilliseconds, record.issuedTime, challengeLifetimeMilliseconds_))
            {
                return record;
            }
        }

        auto *selected = &challenges_.front();
        for (auto &record : challenges_)
        {
            if (!record.valid || expired(nowMilliseconds, record.issuedTime, challengeLifetimeMilliseconds_))
            {
                selected = &record;
                break;
            }
            if (record.issuedTime < selected->issuedTime)
                selected = &record;
        }

        auto challenge = mix32(
            entropy ^ nowMilliseconds ^ peer.ipv4 ^
            (static_cast<std::uint32_t>(peer.port) << 16) ^ ++nonce_);
        challenge &= 0x7FFFFFFFu;
        if (!challenge)
            challenge = 1;
        *selected = {
            .valid = true,
            .peer = peer,
            .xuid = xuid,
            .sessionGeneration = sessionGenerationForXuid(xuid),
            .challenge = challenge,
            .issuedTime = nowMilliseconds,
        };
        const auto diagnosticKey =
            (static_cast<std::uint64_t>(peer.ipv4) << 16) | peer.port;
        if (challengeDiagnostics[diagnosticKey]++ < 3)
        {
            std::clog << "[dedicated/game-server] challenge issued peer="
                      << peer.ipv4 << ':' << peer.port
                      << " xuid=" << xuid
                      << " value=" << challenge
                      << " generation=" << selected->sessionGeneration << '\n';
        }
        return *selected;
    }

    SvClientSystem::ChallengeRecord *SvClientSystem::findChallenge(
        const PeerAddress peer,
        const std::uint64_t xuid,
        const std::uint32_t challenge,
        const std::uint32_t nowMilliseconds)
    {
        for (auto &record : challenges_)
        {
            // The UDP source port may change between getchallenge and
            // connect (especially when the client recreates its socket).
            // Challenge identity is the address/XUID/session tuple; the
            // challenge value itself still prevents unrelated connects.
            const auto currentGeneration = sessionGenerationForXuid(xuid);
            if (record.valid && record.peer.ipv4 == peer.ipv4 &&
                record.xuid == xuid &&
                (record.sessionGeneration == currentGeneration ||
                    (record.sessionGeneration == 0 && currentGeneration != 0)) &&
                record.challenge == challenge &&
                !expired(nowMilliseconds, record.issuedTime, challengeLifetimeMilliseconds_))
            {
                // The client may request a challenge just before the queued
                // SessionStart publishes its roster. Bind that provisional
                // challenge to the current session generation on connect.
                record.sessionGeneration = currentGeneration;
                return &record;
            }
        }
        const auto diagnosticKey =
            (static_cast<std::uint64_t>(peer.ipv4) << 16) | peer.port;
        if (challengeDiagnostics[diagnosticKey]++ < 6)
        {
            std::clog << "[dedicated/game-server] challenge lookup failed peer="
                      << peer.ipv4 << ':' << peer.port
                      << " xuid=" << xuid
                      << " value=" << challenge
                      << " generation=" << sessionGenerationForXuid(xuid)
                      << " pending=" << pendingChallengeCount(nowMilliseconds)
                      << '\n';
        }
        return nullptr;
    }

    ConnectionlessResult SvClientSystem::SV_GetChallenge(
        const PeerAddress peer,
        std::string_view arguments,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        const auto clientIndex = takeToken(arguments);
        const auto xuidText = takeQuoted(arguments);
        if (!clientIndex || !parseInteger<std::uint32_t>(*clientIndex, 10) || !xuidText)
            return reject("EXE_BAD_CHALLENGE", "malformed CODOL getchallenge request");
        const auto xuid = parseInteger<std::uint64_t>(*xuidText, 16);
        if (!xuid || !*xuid)
            return reject("EXE_BAD_CHALLENGE", "getchallenge has an invalid XUID");
        if (!sessionAllowsXuid(*xuid))
            return reject("EXE_BAD_CHALLENGE", "getchallenge XUID is not in the session roster");

        auto &record = SV_GetChallenge(peer, *xuid, nowMilliseconds, entropy);
        return {
            .kind = ConnectionlessResultKind::Reply,
            .reply = makeReply("challengeResponse " + std::to_string(record.challenge)),
            .challenge = record.challenge,
        };
    }

    ConnectionlessResult SvClientSystem::SV_DirectConnect(
        const PeerAddress peer,
        std::string_view arguments,
        const std::uint32_t nowMilliseconds)
    {
        const auto outerXuidText = takeToken(arguments);
        const auto userInfoText = takeQuoted(arguments);
        if (!outerXuidText || !userInfoText)
            return reject("EXE_BAD_CHALLENGE", "malformed CODOL connect request");
        const auto outerXuid = parseInteger<std::uint64_t>(*outerXuidText, 16);
        const auto userInfo = parseUserInfo(*userInfoText);
        if (!outerXuid || !*outerXuid || !userInfo)
            return reject("EXE_BAD_CHALLENGE", "connect identity or userinfo is invalid");

        const auto challengeItem = userInfo->find("challenge");
        const auto innerXuidItem = userInfo->find("xuid");
        if (challengeItem == userInfo->end() || innerXuidItem == userInfo->end())
            return reject("EXE_BAD_CHALLENGE", "connect userinfo omits challenge or XUID");
        const auto challenge = parseInteger<std::uint32_t>(challengeItem->second, 10);
        const auto innerXuid = parseInteger<std::uint64_t>(innerXuidItem->second, 16);
        if (!challenge || !innerXuid || *innerXuid != *outerXuid)
            return reject("EXE_BAD_CHALLENGE", "connect userinfo identity does not match");
        if (!sessionAllowsXuid(*outerXuid))
            return reject("EXE_BAD_CHALLENGE", "connect XUID is not in the session roster");

        auto *challengeRecord = findChallenge(
            peer,
            *outerXuid,
            *challenge,
            nowMilliseconds);
        if (!challengeRecord)
            return reject("EXE_BAD_CHALLENGE", "connect challenge is unknown or expired");

        const auto *roster = sessionRosterForGeneration(
            challengeRecord->sessionGeneration);
        const auto *rosterMember = roster
            ? sessionMemberForXuid(*roster, *outerXuid)
            : nullptr;
        const auto name = userInfo->find("name");
        const auto rankItem = userInfo->find("rank");
        const auto parsedRank = rankItem == userInfo->end()
            ? std::optional<std::uint32_t>{}
            : parseInteger<std::uint32_t>(rankItem->second, 10);
        // Rank is presentation/progression input rather than connection
        // authority. Old clients that omit it continue at rank zero, and a
        // malformed value cannot turn an otherwise authenticated connect into
        // EXE_BAD_CHALLENGE. The 16-bit cap is far above CODOL's shipped rank
        // table while still making the later SPM calculation bounded.
        const auto rank = parsedRank && *parsedRank <= 0xFFFFu
            ? static_cast<std::uint16_t>(*parsedRank)
            : std::uint16_t{};
        if (rosterMember)
        {
            const auto expectedName = SV_EncodePlayerName(rosterMember->username);
            if (!expectedName || name == userInfo->end() ||
                name->second != *expectedName)
            {
                return reject(
                    "EXE_BAD_CHALLENGE",
                    "connect userinfo name does not match the session roster");
            }
        }

        const auto duplicateIdentity = std::find_if(
            clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
                return client.state != ClientState::Free &&
                    client.xuid == *outerXuid &&
                    client.sessionGeneration == challengeRecord->sessionGeneration &&
                    client.peer != peer;
            });
        if (duplicateIdentity != clients_.end())
            return reject("EXE_BAD_CHALLENGE", "connect XUID is already owned by another peer");

        auto existing = std::find_if(clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
            return client.state != ClientState::Free && client.peer == peer &&
                client.xuid == *outerXuid &&
                client.sessionGeneration == challengeRecord->sessionGeneration;
        });
        auto slot = existing;
        if (slot == clients_.end())
        {
            if (rosterMember)
            {
                const auto ordinal = static_cast<std::size_t>(
                    rosterMember - roster->members.data());
                slot = clients_.begin() + static_cast<std::ptrdiff_t>(ordinal);
                if (slot->state != ClientState::Free)
                {
                    return reject(
                        "EXE_SERVERISFULL",
                        "the session roster client slot is occupied");
                }
            }
            else
            {
                slot = std::find_if(
                    clients_.begin(),
                    clients_.end(),
                    [](const ClientSlot &client) {
                        return client.state == ClientState::Free;
                    });
            }
        }
        if (slot == clients_.end())
            return reject("EXE_SERVERISFULL", "all CODOL client slots are occupied");

        const auto slotIndex = static_cast<std::size_t>(slot - clients_.begin());
        *slot = {
            .state = ClientState::Connected,
            .peer = peer,
            .xuid = *outerXuid,
            .sessionGeneration = challengeRecord->sessionGeneration,
            .challenge = *challenge,
            .connectTime = existing == clients_.end() ? nowMilliseconds : existing->connectTime,
            .lastPacketTime = nowMilliseconds,
            // CODREF(sv_direct_connect): BO1/Kisak SV_DirectConnect and Ghosts
            // 0x1401F25B0 initialize nextSnapshotTime from svs.time
            // after accepting the client. This is scheduling state, not a
            // sentinel where zero means immediately due.
            .nextSnapshotTime = nowMilliseconds,
            .rank = rank,
            .name = name == userInfo->end() ? std::string{} : name->second,
            .userInfo = std::string(*userInfoText),
        };
        challengeRecord->connected = true;
        return {
            .kind = ConnectionlessResultKind::Connected,
            .reply = makeReply("connectResponse"),
            .clientSlot = slotIndex,
            .challenge = *challenge,
        };
    }

    std::size_t SvClientSystem::connectedClientCount() const
    {
        return static_cast<std::size_t>(std::count_if(
            clients_.begin(),
            clients_.end(),
            [](const ClientSlot &client) { return client.state != ClientState::Free; }));
    }

    std::size_t SvClientSystem::pendingChallengeCount(
        const std::uint32_t nowMilliseconds) const
    {
        return static_cast<std::size_t>(std::count_if(
            challenges_.begin(),
            challenges_.end(),
            [&](const ChallengeRecord &record) {
                return record.valid && !record.connected &&
                    !expired(nowMilliseconds, record.issuedTime, challengeLifetimeMilliseconds_);
            }));
    }

    std::size_t SvClientSystem::activeClientCount() const
    {
        return static_cast<std::size_t>(std::count_if(
            clients_.begin(),
            clients_.end(),
            [](const ClientSlot &client) { return client.state == ClientState::Active; }));
    }

    std::size_t SvClientSystem::gameStateReadyClientCount() const
    {
        return static_cast<std::size_t>(std::count_if(
            clients_.begin(),
            clients_.end(),
            [&](const ClientSlot &client) {
                return client.state == ClientState::Connected &&
                    client.profileStatsComplete &&
                    (!pendingRoster_ || client.sessionGeneration ==
                        pendingRoster_->generation);
            }));
    }

    bool SvClientSystem::gameStateConfigured() const
    {
        return gameStateConfigured_;
    }

    std::uint32_t SvClientSystem::gameStateMessagesSent() const
    {
        return gameStateMessagesSent_;
    }

    std::uint32_t SvClientSystem::gameStateUpdatesReceived() const
    {
        return gameStateUpdatesReceived_;
    }

    std::uint32_t SvClientSystem::snapshotMessagesSent() const
    {
        return snapshotMessagesSent_;
    }

    std::uint32_t SvClientSystem::fullSnapshotMessagesSent() const
    {
        return fullSnapshotMessagesSent_;
    }

    std::uint32_t SvClientSystem::deltaSnapshotMessagesSent() const
    {
        return deltaSnapshotMessagesSent_;
    }

    std::uint32_t SvClientSystem::latestMessageAcknowledge() const
    {
        std::uint32_t latest{};
        for (const auto &client : clients_)
        {
            if (client.state != ClientState::Free)
                latest = std::max(latest, client.netchan.messageAcknowledge);
        }
        return latest;
    }

    std::uint32_t SvClientSystem::latestOutgoingSequence() const
    {
        std::uint32_t latest{};
        for (const auto &client : clients_)
        {
            if (client.state != ClientState::Free)
                latest = std::max(latest, client.netchan.outgoingSequence);
        }
        return latest;
    }

    std::optional<ClientIngressStatus> SvClientSystem::clientIngressStatus(
        const std::uint32_t clientNum) const
    {
        if (clientNum >= clients_.size())
            return std::nullopt;
        const auto &client = clients_[clientNum];
        if (client.state == ClientState::Free)
            return std::nullopt;
        return ClientIngressStatus{
            .peer = client.peer,
            .xuid = client.xuid,
            .name = client.name,
            .state = client.state,
            .profileStatsReceivedMask = client.profileStatsReceivedMask,
            .profileStatsRequiredMask = client.profileStatsRequiredMask,
            .profileStatsComplete = client.profileStatsComplete,
            .gameStateUpdateStage = client.gameStateUpdateStage,
            .gamestateMessageNum = client.gamestateMessageNum,
            .sessionGeneration = client.sessionGeneration,
            .sessionGenerationActive = clientGenerationIsActive(client),
            .lastPacketTime = client.lastPacketTime,
            .incomingSequence = client.netchan.incomingSequence,
            .outgoingSequence = client.netchan.outgoingSequence,
            .messageAcknowledge = client.netchan.messageAcknowledge,
            .reliableAcknowledge = client.netchan.reliableAcknowledge,
            .lastClientReliableSequence = client.netchan.lastClientReliableSequence,
            .lastClientReliableCommand = client.netchan.lastClientReliableCommand,
            .deltaMessage = client.deltaMessage,
            .lastMoveCommandCount = client.lastMoveCommandCount,
            .snapshotAssemblyFailure = client.snapshotAssemblyFailure,
            .snapshotAssemblyAttempts = client.snapshotAssemblyAttempts,
            .snapshotAssemblyFailures = client.snapshotAssemblyFailures,
            .lastReceivedUserCmd = client.lastReceivedUserCmd,
            .lastDispatchedUserCmd = client.lastDispatchedUserCmd,
            .lastExecutedUserCmd = client.lastExecutedUserCmd,
            .lastDiscardedUnsupportedUserCmd =
                client.lastDiscardedUnsupportedUserCmd,
            .discardedUnsupportedUserCmds =
                client.discardedUnsupportedUserCmds,
            .lastDiscardedRejectedUserCmd =
                client.lastDiscardedRejectedUserCmd,
            .discardedRejectedUserCmds = client.discardedRejectedUserCmds,
            .lastDroppedOverflowUserCmd = client.lastDroppedOverflowUserCmd,
            .droppedOverflowUserCmds = client.droppedOverflowUserCmds,
            .lastMenuResponse = client.lastMenuResponse,
            .gameplayState = client.gameplayState,
            .selectedLoadout = client.selectedLoadout,
            .loadoutSequence = client.loadoutSequence,
            .spawnSequence = client.spawnSequence,
            .characterFaction = client.characterFaction,
            .team = client.team,
            .pendingSelectedLoadout = client.pendingSelectedLoadout,
            .pendingLoadoutSequence = client.pendingLoadoutSequence,
            .pendingCharacterFaction = client.pendingCharacterFaction,
            .pendingTeam = client.pendingTeam,
            .acceptedPackets = client.acceptedPackets,
            .duplicatePackets = client.duplicatePackets,
            .rejectedPackets = client.rejectedPackets,
            .lastPacketReject = client.lastPacketReject,
            .decodedCommandsSize = client.lastDecodedCommandsSize,
            .decodedCommandsPrefix = client.lastDecodedCommandsPrefix,
        };
    }

    std::optional<ServerReliableCommandStatus>
        SvClientSystem::serverReliableCommandStatus(
            const std::uint32_t clientNum,
            const std::size_t maximumCommands) const
    {
        if (clientNum >= clients_.size() ||
            clients_[clientNum].state == ClientState::Free)
        {
            return std::nullopt;
        }
        const auto &client = clients_[clientNum];
        ServerReliableCommandStatus status{
            .sequence = client.reliableSequence,
            .acknowledge = client.netchan.reliableAcknowledge,
        };
        const auto available = std::min<std::size_t>(
            { maximumCommands, ServerReliableCommandCapacity,
              client.reliableSequence });
        if (!available)
            return status;
        const auto first = client.reliableSequence -
            static_cast<std::uint32_t>(available) + 1;
        status.recentCommands.reserve(available);
        for (auto sequence = first; sequence <= client.reliableSequence;
             ++sequence)
        {
            status.recentCommands.push_back({
                .sequence = sequence,
                .command = [&]() {
                    const auto &command = client.reliableCommands[
                        sequence & (ServerReliableCommandCapacity - 1)];
                    if (command.kind == ServerReliableCommandKind::Text)
                        return command.text;
                    // A profile patch is opaque bytes, so the diagnostic shows
                    // its verb and size - which is the part worth reading, since
                    // 'K' loading without a rebuild is exactly what a split
                    // update looks like on the wire.
                    if (!command.payload.empty() &&
                        (command.payload[0] == SvProfilePatchLoadAndRebuild ||
                            command.payload[0] == SvProfilePatchLoadOnly))
                    {
                        return std::string{ "!" } +
                            static_cast<char>(command.payload[0]) + " " +
                            std::to_string(command.payload.size());
                    }
                    return std::string{ "!binary" };
                }(),
            });
        }
        return status;
    }

    std::vector<UserCmd> SvClientSystem::pendingUserCmds(
        const std::uint32_t clientNum) const
    {
        if (clientNum >= clients_.size())
            return {};
        const auto &commands = clients_[clientNum].pendingUserCmds;
        return { commands.begin(), commands.end() };
    }

    bool SV_QueuePendingUserCmd(
        ClientSlot &client,
        const UserCmd &command)
    {
        // CODREF(cl_write_packet): the window is PendingUserCmdCapacity, which
        // is CODOL's own MAX_PACKET_USERCMDS (32) off CL_WritePacket 0x005B2C10
        // -- the most one CODOL client can hand a server in one packet.
        // CODREF(sv_process_client_thinks): the DEFERRAL is Ghosts'
        // (SV_UserMove 0x1401F59B0 -> SV_ProcessClientThinks 0x1401F4450);
        // BO1 SV_UserMove 0x0070BCE0 and CODOL's own client-side
        // CG_PredictPlayerState 0x00464A90 both execute every accepted command
        // immediately instead. re/demo-re/30-codols-own-usercmd-numbers.md.
        if (command.commandTime <= client.lastQueuedUserCmdTime)
            return false;

        client.pendingUserCmds.push_back(command);
        while (client.pendingUserCmds.size() > PendingUserCmdCapacity)
        {
            // OLMOD(pending-usercmd-queue): unlike Ghosts, game-side execution
            // can fail transactionally after dispatch.  Never let later packet
            // ingress evict that exact queue front before commit or an explicit
            // recovery discard resolves its ownership.
            const auto dispatchedFrontPending =
                client.lastDispatchedUserCmd &&
                client.pendingUserCmds.front().commandTime ==
                    client.lastDispatchedUserCmd->commandTime &&
                (!client.lastExecutedUserCmd ||
                    client.lastDispatchedUserCmd->commandTime >
                        client.lastExecutedUserCmd->commandTime);
            if (dispatchedFrontPending)
            {
                // OLMOD(pending-usercmd-latest-tail): preserve the exact
                // in-flight front, but keep Ghosts' low-latency newest-command
                // policy for every uncommitted slot behind it. Dropping the
                // new tail here retains an increasingly stale backlog and can
                // turn sustained two-client ingress into seconds of input lag.
                const auto oldestUndispatched = std::next(
                    client.pendingUserCmds.begin());
                client.lastDroppedOverflowUserCmd = *oldestUndispatched;
                ++client.droppedOverflowUserCmds;
                client.pendingUserCmds.erase(oldestUndispatched);
                continue;
            }

            // CODREF(sv_process_client_thinks): without an in-flight project
            // transaction, retain the newest full-capacity deferred window.
            client.lastDroppedOverflowUserCmd = client.pendingUserCmds.front();
            ++client.droppedOverflowUserCmds;
            client.pendingUserCmds.pop_front();
        }
        client.lastQueuedUserCmdTime = command.commandTime;
        return true;
    }

    std::optional<UserCmd> SvClientSystem::dispatchNextPendingUserCmd(
        const std::uint32_t clientNum)
    {
        // CODDIFF(sv_process_client_thinks): this is the project game-thread
        // dequeue boundary, not a recovered copy of Ghosts' cumulative-time
        // budget or BO1/BO2's immediate SV_UserMove dispatch.
        if (clientNum >= clients_.size())
            return std::nullopt;
        auto &client = clients_[clientNum];
        if (!gameplayAuthorityReady_ || client.state != ClientState::Active ||
            client.gameplayState != ClientGameplayState::Playing ||
            client.pendingUserCmds.empty())
        {
            return std::nullopt;
        }

        const auto &command = client.pendingUserCmds.front();
        // A failed game-side attempt remains at the front and may be
        // dispatched again. commandTime wrap policy is not recovered yet.
        if (client.lastDispatchedUserCmd &&
            command.commandTime < client.lastDispatchedUserCmd->commandTime)
        {
            return std::nullopt;
        }
        client.lastDispatchedUserCmd = command;
        return command;
    }

    bool SvClientSystem::commitExecutedUserCmd(
        const std::uint32_t clientNum,
        const std::uint32_t commandTime)
    {
        // OLMOD(pending-usercmd-queue): native SV_ClientThink copies one
        // lastUsercmd before entering game code and has no rollback result.
        // This stricter checkpoint commits only after the source transaction
        // succeeds and must still own the exact dispatched queue front.
        // FIVE SILENT REFUSALS, AND THE PENDING QUEUE JUST GROWS. `cmdAge=-1` in the
        // runtime line means lastExecutedUserCmd was never set at all, while thinkCommands
        // counts a hundred a second and pending sits at 8 -- so commands arrive, are
        // dispatched, and then nothing here commits them. Which of these five stopped it is
        // not recoverable from the outside: every one of them returns the same false.
        static std::string LastCommitRefusal;
        const auto refuse = [clientNum, commandTime](const char *const why) {
            auto details = "client=" + std::to_string(clientNum) +
                " commandTime=" + std::to_string(commandTime) + " " + why;
            if (details != LastCommitRefusal)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "usercmd commit refused " + details);
                LastCommitRefusal = std::move(details);
            }
            return false;
        };
        if (clientNum >= clients_.size())
            return refuse("clientNum_out_of_range");
        auto &client = clients_[clientNum];
        if (!gameplayAuthorityReady_)
            return refuse("gameplay_authority_not_ready");
        if (client.gameplayState != ClientGameplayState::Playing)
            return refuse("not_playing");
        if (!client.lastDispatchedUserCmd)
            return refuse("nothing_dispatched");
        if (client.lastDispatchedUserCmd->commandTime != commandTime)
            return refuse("dispatched_time_mismatch");
        if (client.lastExecutedUserCmd &&
            commandTime <= client.lastExecutedUserCmd->commandTime)
        {
            return refuse("command_time_not_advancing");
        }
        auto &commands = client.pendingUserCmds;
        if (commands.empty())
            return refuse("pending_queue_empty");
        if (commands.front().commandTime != commandTime)
            return refuse("pending_front_mismatch");
        client.lastExecutedUserCmd = commands.front();
        commands.pop_front();
        return true;
    }

    bool SvClientSystem::discardUnsupportedUserCmd(
        const std::uint32_t clientNum,
        const std::uint32_t commandTime)
    {
        // OLMOD(pending-usercmd-queue): exact-front recovery operation for the
        // project transaction; no BO1/BO2/Ghosts equivalent returns failure
        // from ClientThink after dispatch.
        if (clientNum >= clients_.size())
            return false;
        auto &client = clients_[clientNum];
        if (!gameplayAuthorityReady_ ||
            client.gameplayState != ClientGameplayState::Playing ||
            !client.lastDispatchedUserCmd ||
            client.lastDispatchedUserCmd->commandTime != commandTime)
        {
            return false;
        }
        auto &commands = client.pendingUserCmds;
        if (commands.empty() || commands.front().commandTime != commandTime)
            return false;

        // TODO(CODOL): Remove this recovery-only discard path after every
        // valid server-only usercmd event has an authoritative handler. Until
        // then, retain diagnostics without letting one unsupported event block
        // all later commands indefinitely.
        client.lastDiscardedUnsupportedUserCmd = commands.front();
        ++client.discardedUnsupportedUserCmds;
        commands.pop_front();
        return true;
    }

    bool SvClientSystem::discardRejectedUserCmd(
        const std::uint32_t clientNum,
        const std::uint32_t commandTime)
    {
        // OLMOD(pending-usercmd-queue): keep rejected-command ownership
        // separate from both native-style dispatch and successful execution.
        if (clientNum >= clients_.size())
            return false;
        auto &client = clients_[clientNum];
        if (!gameplayAuthorityReady_ ||
            client.gameplayState != ClientGameplayState::Playing ||
            !client.lastDispatchedUserCmd ||
            client.lastDispatchedUserCmd->commandTime != commandTime)
        {
            return false;
        }
        auto &commands = client.pendingUserCmds;
        if (commands.empty() || commands.front().commandTime != commandTime)
            return false;

        // TODO(CODOL): Remove this compatibility path once all valid command
        // event and native Pmove inputs have authoritative implementations.
        // Deterministic command failures must not pin every later usercmd.
        client.lastDiscardedRejectedUserCmd = commands.front();
        ++client.discardedRejectedUserCmds;
        commands.pop_front();
        return true;
    }

    UserCmd SV_DefaultUserCmdFromPlayerState(const SvPlayerState &playerState)
    {
        UserCmd result;
        for (std::size_t index = 0; index < 2; ++index)
        {
            result.angles[index] = BG_AngleToShort(
                playerState.viewAngles[index] - playerState.deltaAngles[index]);
        }
        result.weapon = playerState.currentWeaponAssetIndex;
        // CODREF(MSG_SetDefaultUserCmd): OLFinal out.exe 0x0066F170 builds
        // the first usercmd delta baseline from the acknowledged playerstate.
        // When protected playerstate flag 0x1000 is present it reconstructs
        // the level-driven stance buttons from eFlags, plus ADS from the
        // weapon-position fraction. Leaving these buttons zero made every
        // packet boundary look like a stance release and caused the client to
        // fight the authoritative view-height transition.
        if (playerState.otherFlags & 0x1000u)
        {
            if (playerState.eFlags & 0x8u)
                result.buttons |= 0x100u;
            else if (playerState.eFlags & 0x4u)
                result.buttons |= 0x200u;
            if (playerState.weaponPositionFraction != 0.0f)
                result.buttons |= 0x800u;
            result.conditionalElevenBits = 0x7FFu;
        }
        return result;
    }

    bool SV_CopyClientReliableCommandStatus(
        const ClientIngressStatus &status,
        std::uint32_t &sequence,
        const std::span<char> command,
        std::uint32_t &commandLength)
    {
        sequence = status.lastClientReliableSequence;
        return SV_CopyStatusText(
            status.lastClientReliableCommand, command, commandLength);
    }

    bool SV_CopyStatusText(
        const std::string_view value,
        const std::span<char> output,
        std::uint32_t &valueLength)
    {
        if (output.empty())
            return false;
        valueLength = static_cast<std::uint32_t>(value.size());
        const auto copiedLength = std::min(value.size(), output.size() - 1);
        std::copy_n(value.begin(), copiedLength, output.begin());
        output[copiedLength] = '\0';
        return true;
    }

    const std::vector<ClientSlot> &SvClientSystem::clients() const
    {
        return clients_;
    }
}
