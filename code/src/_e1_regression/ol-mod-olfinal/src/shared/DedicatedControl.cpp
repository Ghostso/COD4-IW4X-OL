#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <bit>
#include <WinSock2.h>
#include <WS2tcpip.h>

#include "DedicatedControl.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <charconv>
#include <cstdlib>
#include <limits>
#include <span>
#include <thread>
#include <utility>
#include <vector>

namespace
{
    constexpr std::uint32_t FrameMagic = 0x43444C4F; // OLDC
    constexpr std::uint32_t EndpointStatusMagic = 0x4553444F; // ODSE
    constexpr std::uint32_t GameplayStatusMagic = 0x5352444F; // ODRS
    constexpr std::uint32_t NoclipRequestMagic = 0x434E444F; // ODNC
    constexpr std::size_t RequestHeaderSize = 24;
    constexpr std::size_t ResponseHeaderSize = 24;

    void appendU16(std::vector<std::uint8_t> &output, const std::uint16_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        for (std::uint32_t shift = 0; shift < 32; shift += 8)
            output.push_back(static_cast<std::uint8_t>(value >> shift));
    }

    void appendU64(std::vector<std::uint8_t> &output, const std::uint64_t value)
    {
        for (std::uint32_t shift = 0; shift < 64; shift += 8)
            output.push_back(static_cast<std::uint8_t>(value >> shift));
    }

    void appendFloat(std::vector<std::uint8_t> &output, const float value)
    {
        appendU32(output, std::bit_cast<std::uint32_t>(value));
    }

    std::uint16_t readU16(const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        return static_cast<std::uint16_t>(input[offset]) |
            static_cast<std::uint16_t>(input[offset + 1] << 8);
    }

    std::uint32_t readU32(const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        std::uint32_t result{};
        for (std::uint32_t shift = 0; shift < 32; shift += 8)
            result |= static_cast<std::uint32_t>(input[offset + shift / 8]) << shift;
        return result;
    }

    std::uint64_t readU64(const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        std::uint64_t result{};
        for (std::uint32_t shift = 0; shift < 64; shift += 8)
            result |= static_cast<std::uint64_t>(input[offset + shift / 8]) << shift;
        return result;
    }

    float readFloat(
        const std::span<const std::uint8_t> input,
        const std::size_t offset)
    {
        return std::bit_cast<float>(readU32(input, offset));
    }

    bool canRead(
        const std::span<const std::uint8_t> input,
        const std::size_t offset,
        const std::size_t size)
    {
        return offset <= input.size() && size <= input.size() - offset;
    }

    std::uint32_t checksum(const std::span<const std::uint8_t> input)
    {
        std::uint32_t result = 2166136261u;
        for (const auto value : input)
        {
            result ^= value;
            result *= 16777619u;
        }
        return result;
    }

    bool sendAll(const SOCKET socket, const std::span<const std::uint8_t> data)
    {
        std::size_t offset{};
        while (offset < data.size())
        {
            const auto sent = send(
                socket,
                reinterpret_cast<const char *>(data.data() + offset),
                static_cast<int>(data.size() - offset),
                0);
            if (sent <= 0)
                return false;
            offset += static_cast<std::size_t>(sent);
        }
        return true;
    }

    bool receiveAll(const SOCKET socket, const std::span<std::uint8_t> data)
    {
        std::size_t offset{};
        while (offset < data.size())
        {
            const auto received = recv(
                socket,
                reinterpret_cast<char *>(data.data() + offset),
                static_cast<int>(data.size() - offset),
                0);
            if (received <= 0)
                return false;
            offset += static_cast<std::size_t>(received);
        }
        return true;
    }

    std::vector<std::uint8_t> encodeRequest(const OlMod::DedicatedControl::Message &message)
    {
        const auto payload = std::span(
            reinterpret_cast<const std::uint8_t *>(message.payload.data()),
            message.payload.size());
        std::vector<std::uint8_t> output;
        output.reserve(RequestHeaderSize + payload.size());
        appendU32(output, FrameMagic);
        appendU16(output, OlMod::DedicatedControl::ProtocolVersion);
        appendU16(output, static_cast<std::uint16_t>(message.type));
        appendU32(output, static_cast<std::uint32_t>(payload.size()));
        appendU64(output, message.requestId);
        appendU32(output, checksum(payload));
        output.insert(output.end(), payload.begin(), payload.end());
        return output;
    }

    std::vector<std::uint8_t> encodeResponse(
        const std::uint64_t requestId,
        const OlMod::DedicatedControl::Response &response)
    {
        const auto payload = std::span(
            reinterpret_cast<const std::uint8_t *>(response.payload.data()),
            response.payload.size());
        std::vector<std::uint8_t> output;
        output.reserve(ResponseHeaderSize + payload.size());
        appendU32(output, FrameMagic);
        appendU16(output, OlMod::DedicatedControl::ProtocolVersion);
        appendU16(output, static_cast<std::uint16_t>(response.status));
        appendU32(output, static_cast<std::uint32_t>(payload.size()));
        appendU64(output, requestId);
        appendU32(output, checksum(payload));
        output.insert(output.end(), payload.begin(), payload.end());
        return output;
    }

    void closeSocket(SOCKET &socket)
    {
        if (socket == INVALID_SOCKET)
            return;
        closesocket(socket);
        socket = INVALID_SOCKET;
    }
}

namespace OlMod::DedicatedControl
{
    struct Server::State
    {
        std::atomic_bool running{};
        std::atomic<SOCKET> listener{INVALID_SOCKET};
        std::thread worker;
        MessageHandler handler;
        std::atomic_uint16_t port{};
        std::atomic_int lastSocketError{};
        bool winsockStarted{};
    };

    Server::Server() : state_(std::make_unique<State>())
    {
    }

    Server::~Server()
    {
        stop();
    }

    bool Server::start(const std::uint16_t port, MessageHandler handler)
    {
        stop();
        if (!handler)
            return false;

        WSADATA winsock{};
        if (const auto error = WSAStartup(MAKEWORD(2, 2), &winsock); error != 0)
        {
            state_->lastSocketError = error;
            return false;
        }
        state_->winsockStarted = true;

        auto listener = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (listener == INVALID_SOCKET)
        {
            state_->lastSocketError = WSAGetLastError();
            stop();
            return false;
        }

        // Loopback is the default because a control listener reachable from
        // the network is a decision, never an accident. hostIsRemote() asks the
        // only question that matters: is this stack being addressed over a
        // network at all? If it is, every control listener has to accept from
        // there, because the room owner, the dedicated and each client's bridge
        // are no longer guaranteed to share a machine.
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(
            hostIsRemote() ? INADDR_ANY : INADDR_LOOPBACK);
        address.sin_port = htons(port);
        if (bind(listener, reinterpret_cast<const sockaddr *>(&address), sizeof(address)) != 0 ||
            listen(listener, 4) != 0)
        {
            state_->lastSocketError = WSAGetLastError();
            closesocket(listener);
            stop();
            return false;
        }

        sockaddr_in bound{};
        int boundSize = sizeof(bound);
        if (getsockname(listener, reinterpret_cast<sockaddr *>(&bound), &boundSize) != 0)
        {
            state_->lastSocketError = WSAGetLastError();
            closesocket(listener);
            stop();
            return false;
        }

        state_->listener.store(listener);
        state_->handler = std::move(handler);
        state_->port.store(ntohs(bound.sin_port));
        state_->lastSocketError.store(0);
        state_->running.store(true);
        state_->worker = std::thread([state = state_.get()] {
            while (state->running.load())
            {
                sockaddr_in peer{};
                int peerSize = sizeof(peer);
                auto client = accept(
                    state->listener.load(),
                    reinterpret_cast<sockaddr *>(&peer),
                    &peerSize);
                if (client == INVALID_SOCKET)
                {
                    if (state->running.load())
                        state->lastSocketError.store(WSAGetLastError());
                    break;
                }

                DWORD timeout = 500;
                setsockopt(client, SOL_SOCKET, SO_RCVTIMEO,
                    reinterpret_cast<const char *>(&timeout), sizeof(timeout));
                setsockopt(client, SOL_SOCKET, SO_SNDTIMEO,
                    reinterpret_cast<const char *>(&timeout), sizeof(timeout));

                std::array<std::uint8_t, RequestHeaderSize> header{};
                Response response{ .status = ResponseStatus::InvalidMessage };
                std::uint64_t requestId{};
                if (receiveAll(client, header))
                {
                    requestId = readU64(header, 12);
                    const auto payloadSize = readU32(header, 8);
                    if (readU32(header, 0) == FrameMagic &&
                        readU16(header, 4) == ProtocolVersion &&
                        payloadSize <= MaximumPayloadSize)
                    {
                        std::vector<std::uint8_t> payload(payloadSize);
                        if (receiveAll(client, payload) &&
                            checksum(payload) == readU32(header, 20))
                        {
                            Message message{
                                .type = static_cast<MessageType>(readU16(header, 6)),
                                .requestId = requestId,
                                .payload = payload.empty()
                                    ? std::string{}
                                    : std::string(
                                        reinterpret_cast<const char *>(payload.data()),
                                        payload.size()),
                                .peerIpv4 = ntohl(peer.sin_addr.s_addr),
                            };
                            try
                            {
                                response = state->handler(message);
                                if (response.payload.size() > MaximumPayloadSize)
                                {
                                    response = { .status = ResponseStatus::Rejected };
                                }
                            }
                            catch (...)
                            {
                                response = { .status = ResponseStatus::Rejected };
                            }
                        }
                    }
                }
                const auto encodedResponse = encodeResponse(requestId, response);
                static_cast<void>(sendAll(client, encodedResponse));
                shutdown(client, SD_BOTH);
                closesocket(client);
            }
        });
        return true;
    }

    void Server::stop()
    {
        if (!state_)
            return;
        state_->running.store(false);
        const auto listener = state_->listener.exchange(INVALID_SOCKET);
        if (listener != INVALID_SOCKET)
        {
            shutdown(listener, SD_BOTH);
            closesocket(listener);
        }
        if (state_->worker.joinable())
            state_->worker.join();
        state_->handler = {};
        state_->port.store(0);
        if (state_->winsockStarted)
        {
            WSACleanup();
            state_->winsockStarted = false;
        }
    }

    bool Server::running() const
    {
        return state_ && state_->running.load();
    }

    std::uint16_t Server::port() const
    {
        return state_ ? state_->port.load() : 0;
    }

    int Server::lastSocketError() const
    {
        return state_ ? state_->lastSocketError.load() : 0;
    }

    SubmitResult submit(
        const std::string_view host,
        const std::uint16_t port,
        const Message &message,
        const std::uint32_t timeoutMilliseconds)
    {
        SubmitResult result{.requestId = message.requestId};
        if (host.empty() || !port || message.payload.size() > MaximumPayloadSize)
            return result;

        WSADATA winsock{};
        if (const auto error = WSAStartup(MAKEWORD(2, 2), &winsock); error != 0)
        {
            result.socketError = error;
            return result;
        }
        auto socketHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (socketHandle == INVALID_SOCKET)
        {
            result.socketError = WSAGetLastError();
            WSACleanup();
            return result;
        }

        const auto timeout = static_cast<DWORD>(timeoutMilliseconds);
        setsockopt(socketHandle, SOL_SOCKET, SO_RCVTIMEO,
            reinterpret_cast<const char *>(&timeout), sizeof(timeout));
        setsockopt(socketHandle, SOL_SOCKET, SO_SNDTIMEO,
            reinterpret_cast<const char *>(&timeout), sizeof(timeout));
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_port = htons(port);
        if (InetPtonA(AF_INET, std::string(host).c_str(), &address.sin_addr) != 1 ||
            connect(socketHandle, reinterpret_cast<const sockaddr *>(&address), sizeof(address)) != 0)
        {
            result.socketError = WSAGetLastError();
            closesocket(socketHandle);
            WSACleanup();
            return result;
        }

        const auto request = encodeRequest(message);
        std::array<std::uint8_t, ResponseHeaderSize> responseHeader{};
        if (sendAll(socketHandle, request) &&
            receiveAll(socketHandle, responseHeader) &&
            readU32(responseHeader, 0) == FrameMagic &&
            readU16(responseHeader, 4) == ProtocolVersion &&
            readU64(responseHeader, 12) == message.requestId &&
            readU32(responseHeader, 8) <= MaximumPayloadSize)
        {
            const auto payloadSize = readU32(responseHeader, 8);
            std::vector<std::uint8_t> payload(payloadSize);
            if (receiveAll(socketHandle, payload) &&
                checksum(payload) == readU32(responseHeader, 20))
            {
                result.delivered = true;
                result.status = static_cast<ResponseStatus>(
                    readU16(responseHeader, 6));
                if (!payload.empty())
                {
                    result.payload.assign(
                        reinterpret_cast<const char *>(payload.data()),
                        payload.size());
                }
            }
        }
        if (!result.delivered)
        {
            result.socketError = WSAGetLastError();
        }
        shutdown(socketHandle, SD_BOTH);
        closesocket(socketHandle);
        WSACleanup();
        return result;
    }

    std::string encodeEndpointStatus(const GameServerEndpointStatus &status)
    {
        std::array<std::uint8_t, 8> payload{};
        payload[0] = static_cast<std::uint8_t>(EndpointStatusMagic);
        payload[1] = static_cast<std::uint8_t>(EndpointStatusMagic >> 8);
        payload[2] = static_cast<std::uint8_t>(EndpointStatusMagic >> 16);
        payload[3] = static_cast<std::uint8_t>(EndpointStatusMagic >> 24);
        payload[4] = 1;
        payload[5] = static_cast<std::uint8_t>(
            (status.sessionConfigured ? 1 : 0) |
            (status.enabled ? 2 : 0) |
            (status.bound ? 4 : 0));
        payload[6] = static_cast<std::uint8_t>(status.port);
        payload[7] = static_cast<std::uint8_t>(status.port >> 8);
        return {
            reinterpret_cast<const char *>(payload.data()),
            payload.size(),
        };
    }

    std::optional<GameServerEndpointStatus> decodeEndpointStatus(
        const std::string_view payload)
    {
        if (payload.size() != 8)
            return std::nullopt;
        const auto bytes = std::span(
            reinterpret_cast<const std::uint8_t *>(payload.data()),
            payload.size());
        if (readU32(bytes, 0) != EndpointStatusMagic || bytes[4] != 1 ||
            (bytes[5] & ~std::uint8_t{7}) != 0)
        {
            return std::nullopt;
        }
        return GameServerEndpointStatus{
            .sessionConfigured = (bytes[5] & 1) != 0,
            .enabled = (bytes[5] & 2) != 0,
            .bound = (bytes[5] & 4) != 0,
            .port = readU16(bytes, 6),
        };
    }

    std::string ipv4Text(const std::uint32_t ipv4)
    {
        std::string text;
        for (int shift = 24; shift >= 0; shift -= 8)
        {
            if (shift != 24)
                text.push_back('.');
            text += std::to_string(
                static_cast<unsigned>((ipv4 >> shift) & 0xFFu));
        }
        return text;
    }

    std::string encodeNoclipRequest(const NoclipRequest &request)
    {
        std::vector<std::uint8_t> output;
        appendU32(output, NoclipRequestMagic);
        output.push_back(1);
        appendU64(output, request.userId);
        output.push_back(request.enabled ? 1 : 0);
        appendU32(output, request.holdMilliseconds);
        return {
            reinterpret_cast<const char *>(output.data()),
            output.size(),
        };
    }

    std::optional<NoclipRequest> decodeNoclipRequest(
        const std::string_view payload)
    {
        if (payload.size() != 18)
            return std::nullopt;
        const auto bytes = std::span(
            reinterpret_cast<const std::uint8_t *>(payload.data()),
            payload.size());
        if (readU32(bytes, 0) != NoclipRequestMagic || bytes[4] != 1 ||
            bytes[13] > 1)
        {
            return std::nullopt;
        }
        // ZERO IS A REAL VALUE HERE and means "resolve me by the address I am
        // sending from". That is the CLIENT's case: it knows its platform user
        // id and the server knows the xuid out.exe sent in its connect string,
        // and those are different numbers. A non-zero id is the TOOL's case --
        // name one slot exactly, and fail rather than fall back.
        return NoclipRequest{
            .userId = readU64(bytes, 5),
            .enabled = bytes[13] != 0,
            .holdMilliseconds = readU32(bytes, 14),
        };
    }

    std::string encodeGameplayStatus(const GameplayStatus &status)
    {
        std::vector<std::uint8_t> output;
        appendU32(output, GameplayStatusMagic);
        appendU16(output, 5);
        appendU16(output, static_cast<std::uint16_t>(status.clients.size()));
        appendU32(output, status.serverTime);
        const std::array sd{
            status.sd.roundConfigured, status.sd.roundArmed,
            status.sd.roundCompleted, status.sd.roundsPlayed,
            status.sd.roundWinner, status.sd.roundEndReason,
            status.sd.bombConfigured, status.sd.bombPhase,
            status.sd.attackers, status.sd.defenders,
            status.sd.attackersAlive, status.sd.defendersAlive,
            status.sd.carrierClientNum, status.sd.planterClientNum,
            status.sd.defuserClientNum, status.sd.plantedSiteLabel,
            status.sd.phaseStartServerTime, status.sd.plantedServerTime,
        };
        for (const auto value : sd)
            appendU32(output, value);
        for (const auto &client : status.clients)
        {
            appendU32(output, client.clientNum);
            appendU32(output, client.gameplayState);
            appendU32(output, client.team);
            appendU32(output, client.reliableSequence);
            appendU32(output, client.reliableAcknowledge);
            appendU32(output, client.peerIpv4);
            appendU16(output, client.peerPort);
            appendU16(output, 0);
            appendU32(output, client.lastPacketReceivedTime);
            appendU32(output, client.incomingSequence);
            appendU32(output, client.outgoingSequence);
            appendU32(output, client.messageAcknowledge);
            appendU64(output, client.udpSendAttempts);
            appendU64(output, client.udpSendSucceeded);
            appendU64(output, client.udpSendFailed);
            appendU64(output, client.udpBytesSent);
            appendU32(output, client.lastUdpSendTime);
            appendU32(output, client.lastUdpSendBytes);
            appendU32(output, static_cast<std::uint32_t>(
                client.lastUdpSendError));
            appendU32(output, client.pendingUserCmdCount);
            appendU32(output, client.oldestPendingUserCmdTime);
            appendU32(output, client.newestPendingUserCmdTime);
            appendU32(output, client.lastReceivedUserCmdTime);
            appendU32(output, client.lastDispatchedUserCmdTime);
            appendU32(output, client.lastExecutedUserCmdTime);
            appendU32(output, client.lastDiscardedUserCmdTime);
            appendU32(output, client.discardedUnsupportedUserCmds);
            appendU32(output, client.snapshotPlayerEntityMask);
            appendU32(output, client.snapshotClientInfoMask);
            appendU32(output, client.lastDiscardedRejectedUserCmdTime);
            appendU32(output, client.discardedRejectedUserCmds);
            appendU32(output, client.clientThinkLastAttemptedCommandTime);
            appendU32(output, client.clientThinkLastCommittedCommandTime);
            appendU32(output, client.clientThinkFailureStage);
            appendU32(output, client.clientThinkFailureCount);
            appendU32(output, client.lastDispatchedButtons);
            for (const auto angle : client.lastDispatchedAngles)
                appendU32(output, angle);
            appendU32(output, client.lastDispatchedWeapon);
            appendU32(output, client.lastDispatchedOffhand);
            appendU32(output, static_cast<std::uint32_t>(
                client.lastDispatchedForwardMove));
            appendU32(output, static_cast<std::uint32_t>(
                client.lastDispatchedRightMove));
            for (const auto value : client.origin)
                appendFloat(output, value);
            for (const auto value : client.viewAngles)
                appendFloat(output, value);
            appendU32(output, client.health);
            appendU32(output, client.bulletCommandTime);
            for (const auto value : client.bulletStart)
                appendFloat(output, value);
            for (const auto value : client.bulletEnd)
                appendFloat(output, value);
            appendFloat(output, client.bulletFraction);
            appendU32(output, client.bulletHitType);
            appendU32(output, client.bulletHitEntityNum);
            appendU32(output, client.bulletModelIndex);
            appendU32(output, client.bulletPartName);
            appendU32(output, client.bulletPartGroup);
            appendU32(output, client.bulletResult);
            for (const auto &objective : client.objectives)
            {
                appendU32(output, objective.state);
                appendU32(output, objective.icon);
            }
            appendU32(output, static_cast<std::uint32_t>(
                client.recentReliableCommands.size()));
            for (const auto &command : client.recentReliableCommands)
            {
                if (command.command.size() > 1023)
                    return {};
                appendU32(output, command.sequence);
                appendU16(output, static_cast<std::uint16_t>(command.command.size()));
                output.insert(
                    output.end(), command.command.begin(), command.command.end());
            }
        }
        if (output.size() > MaximumPayloadSize ||
            status.clients.size() > std::numeric_limits<std::uint16_t>::max())
        {
            return {};
        }
        return {
            reinterpret_cast<const char *>(output.data()), output.size()
        };
    }

    std::optional<GameplayStatus> decodeGameplayStatus(
        const std::string_view payload)
    {
        const auto input = std::span(
            reinterpret_cast<const std::uint8_t *>(payload.data()),
            payload.size());
        constexpr std::size_t HeaderSize = 12 + 18 * sizeof(std::uint32_t);
        if (!canRead(input, 0, HeaderSize) ||
            readU32(input, 0) != GameplayStatusMagic ||
            (readU16(input, 4) < 1 || readU16(input, 4) > 5))
        {
            return std::nullopt;
        }
        GameplayStatus status{ .serverTime = readU32(input, 8) };
        std::array<std::uint32_t *, 18> sd{
            &status.sd.roundConfigured, &status.sd.roundArmed,
            &status.sd.roundCompleted, &status.sd.roundsPlayed,
            &status.sd.roundWinner, &status.sd.roundEndReason,
            &status.sd.bombConfigured, &status.sd.bombPhase,
            &status.sd.attackers, &status.sd.defenders,
            &status.sd.attackersAlive, &status.sd.defendersAlive,
            &status.sd.carrierClientNum, &status.sd.planterClientNum,
            &status.sd.defuserClientNum, &status.sd.plantedSiteLabel,
            &status.sd.phaseStartServerTime, &status.sd.plantedServerTime,
        };
        std::size_t offset = 12;
        for (auto *const value : sd)
        {
            *value = readU32(input, offset);
            offset += 4;
        }
        const auto clientCount = readU16(input, 6);
        const auto schema = readU16(input, 4);
        status.clients.reserve(clientCount);
        for (std::uint16_t clientIndex{}; clientIndex < clientCount; ++clientIndex)
        {
            constexpr std::size_t Schema1FixedClientSize =
                6 * sizeof(std::uint32_t) + 3 * 2 * sizeof(std::uint32_t);
            constexpr std::size_t Schema2TransportSize = 68;
            constexpr std::size_t Schema3GameplayDiagnosticsSize = 40;
            constexpr std::size_t Schema4ClientThinkDiagnosticsSize = 56;
            constexpr std::size_t Schema5LocationalDiagnosticsSize = 84;
            const auto fixedClientSize = Schema1FixedClientSize +
                (schema >= 2 ? Schema2TransportSize : 0) +
                (schema >= 3 ? Schema3GameplayDiagnosticsSize : 0) +
                (schema >= 4 ? Schema4ClientThinkDiagnosticsSize : 0) +
                (schema >= 5 ? Schema5LocationalDiagnosticsSize : 0);
            if (!canRead(input, offset, fixedClientSize))
                return std::nullopt;
            GameplayClientStatus client;
            client.clientNum = readU32(input, offset);
            client.gameplayState = readU32(input, offset + 4);
            client.team = readU32(input, offset + 8);
            client.reliableSequence = readU32(input, offset + 12);
            client.reliableAcknowledge = readU32(input, offset + 16);
            offset += 20;
            if (schema >= 2)
            {
                client.peerIpv4 = readU32(input, offset);
                client.peerPort = readU16(input, offset + 4);
                if (readU16(input, offset + 6) != 0)
                    return std::nullopt;
                client.lastPacketReceivedTime = readU32(input, offset + 8);
                client.incomingSequence = readU32(input, offset + 12);
                client.outgoingSequence = readU32(input, offset + 16);
                client.messageAcknowledge = readU32(input, offset + 20);
                client.udpSendAttempts = readU64(input, offset + 24);
                client.udpSendSucceeded = readU64(input, offset + 32);
                client.udpSendFailed = readU64(input, offset + 40);
                client.udpBytesSent = readU64(input, offset + 48);
                client.lastUdpSendTime = readU32(input, offset + 56);
                client.lastUdpSendBytes = readU32(input, offset + 60);
                client.lastUdpSendError = static_cast<std::int32_t>(
                    readU32(input, offset + 64));
                offset += Schema2TransportSize;
            }
            if (schema >= 3)
            {
                client.pendingUserCmdCount = readU32(input, offset);
                client.oldestPendingUserCmdTime = readU32(input, offset + 4);
                client.newestPendingUserCmdTime = readU32(input, offset + 8);
                client.lastReceivedUserCmdTime = readU32(input, offset + 12);
                client.lastDispatchedUserCmdTime = readU32(input, offset + 16);
                client.lastExecutedUserCmdTime = readU32(input, offset + 20);
                client.lastDiscardedUserCmdTime = readU32(input, offset + 24);
                client.discardedUnsupportedUserCmds = readU32(input, offset + 28);
                client.snapshotPlayerEntityMask = readU32(input, offset + 32);
                client.snapshotClientInfoMask = readU32(input, offset + 36);
                offset += Schema3GameplayDiagnosticsSize;
            }
            if (schema >= 4)
            {
                client.lastDiscardedRejectedUserCmdTime = readU32(input, offset);
                client.discardedRejectedUserCmds = readU32(input, offset + 4);
                client.clientThinkLastAttemptedCommandTime =
                    readU32(input, offset + 8);
                client.clientThinkLastCommittedCommandTime =
                    readU32(input, offset + 12);
                client.clientThinkFailureStage = readU32(input, offset + 16);
                client.clientThinkFailureCount = readU32(input, offset + 20);
                client.lastDispatchedButtons = readU32(input, offset + 24);
                for (std::size_t index{};
                     index < client.lastDispatchedAngles.size(); ++index)
                {
                    client.lastDispatchedAngles[index] =
                        readU32(input, offset + 28 + index * 4);
                }
                client.lastDispatchedWeapon = readU32(input, offset + 40);
                client.lastDispatchedOffhand = readU32(input, offset + 44);
                client.lastDispatchedForwardMove = static_cast<std::int32_t>(
                    readU32(input, offset + 48));
                client.lastDispatchedRightMove = static_cast<std::int32_t>(
                    readU32(input, offset + 52));
                offset += Schema4ClientThinkDiagnosticsSize;
            }
            if (schema >= 5)
            {
                for (std::size_t index{}; index < client.origin.size(); ++index)
                {
                    client.origin[index] = readFloat(input, offset + index * 4);
                    client.viewAngles[index] =
                        readFloat(input, offset + 12 + index * 4);
                }
                client.health = readU32(input, offset + 24);
                client.bulletCommandTime = readU32(input, offset + 28);
                for (std::size_t index{};
                     index < client.bulletStart.size(); ++index)
                {
                    client.bulletStart[index] =
                        readFloat(input, offset + 32 + index * 4);
                    client.bulletEnd[index] =
                        readFloat(input, offset + 44 + index * 4);
                }
                client.bulletFraction = readFloat(input, offset + 56);
                client.bulletHitType = readU32(input, offset + 60);
                client.bulletHitEntityNum = readU32(input, offset + 64);
                client.bulletModelIndex = readU32(input, offset + 68);
                client.bulletPartName = readU32(input, offset + 72);
                client.bulletPartGroup = readU32(input, offset + 76);
                client.bulletResult = readU32(input, offset + 80);
                offset += Schema5LocationalDiagnosticsSize;
            }
            for (auto &objective : client.objectives)
            {
                objective.state = readU32(input, offset);
                objective.icon = readU32(input, offset + 4);
                offset += 8;
            }
            const auto commandCount = readU32(input, offset);
            offset += 4;
            if (commandCount > MaximumRecentReliableCommands)
                return std::nullopt;
            client.recentReliableCommands.reserve(commandCount);
            for (std::uint32_t commandIndex{};
                 commandIndex < commandCount; ++commandIndex)
            {
                if (!canRead(input, offset, 6))
                    return std::nullopt;
                GameplayReliableCommandStatus command{
                    .sequence = readU32(input, offset),
                };
                const auto commandSize = readU16(input, offset + 4);
                offset += 6;
                if (commandSize > 1023 || !canRead(input, offset, commandSize))
                    return std::nullopt;
                command.command.assign(
                    reinterpret_cast<const char *>(input.data() + offset),
                    commandSize);
                offset += commandSize;
                client.recentReliableCommands.push_back(std::move(command));
            }
            status.clients.push_back(std::move(client));
        }
        return offset == input.size() ? std::optional{ std::move(status) }
                                      : std::nullopt;
    }

    std::uint16_t configuredPortValue(
        const char *const variable,
        const std::uint16_t fallback)
    {
        char *configured{};
        std::size_t configuredSize{};
        if (_dupenv_s(
                &configured,
                &configuredSize,
                variable) != 0 ||
            !configured || !*configured)
        {
            std::free(configured);
            return fallback;
        }
        std::uint32_t value{};
        const auto end = configured + std::char_traits<char>::length(configured);
        const auto parsed = std::from_chars(configured, end, value);
        const auto valid = parsed.ec == std::errc{} && parsed.ptr == end &&
            value && value <= 0xFFFF;
        std::free(configured);
        if (!valid)
            return fallback;
        return static_cast<std::uint16_t>(value);
    }

    std::uint16_t configuredPort()
    {
        return configuredPortValue(
            "OLMOD_DEDICATED_CONTROL_PORT", DefaultPort);
    }

    std::uint16_t configuredClientBridgePort()
    {
        return configuredPortValue(
            "OLMOD_CLIENT_BRIDGE_PORT", DefaultClientBridgePort);
    }

    std::string configuredHostAddress()
    {
        char *configured{};
        std::size_t configuredSize{};
        if (_dupenv_s(&configured, &configuredSize, "OLMOD_HOST_ADDRESS") != 0 ||
            !configured || !*configured)
        {
            std::free(configured);
            return std::string(DefaultHostAddress);
        }
        std::string value(configured);
        std::free(configured);
        // An unparseable address falls back to loopback rather than to a
        // half-configured stack: a typo must not leave listeners open to the
        // network while nothing can actually reach them.
        in_addr parsed{};
        if (inet_pton(AF_INET, value.c_str(), &parsed) != 1)
            return std::string(DefaultHostAddress);
        return value;
    }

    std::uint32_t configuredHostIpv4()
    {
        in_addr parsed{};
        if (inet_pton(AF_INET, configuredHostAddress().c_str(), &parsed) != 1)
            return LoopbackHostIpv4;
        return ntohl(parsed.s_addr);
    }

    bool hostIsRemote()
    {
        return configuredHostIpv4() != LoopbackHostIpv4;
    }
}
