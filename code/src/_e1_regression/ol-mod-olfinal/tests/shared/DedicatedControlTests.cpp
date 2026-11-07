#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <WS2tcpip.h>

#include "shared/DedicatedControl.hpp"
#include "shared/ProcessRole.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
    constexpr std::uint32_t FrameMagic = 0x43444C4F;

    void require(const bool condition, const char *const message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

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

    std::uint16_t readU16(const std::array<std::uint8_t, 24> &input, const std::size_t offset)
    {
        return static_cast<std::uint16_t>(input[offset]) |
            static_cast<std::uint16_t>(input[offset + 1] << 8);
    }

    bool transferAll(const SOCKET socket, const void *data, const std::size_t size, const bool sendData)
    {
        auto *bytes = static_cast<const char *>(data);
        std::size_t offset{};
        while (offset < size)
        {
            const auto transferred = sendData
                ? send(socket, bytes + offset, static_cast<int>(size - offset), 0)
                : recv(socket, const_cast<char *>(bytes) + offset,
                    static_cast<int>(size - offset), 0);
            if (transferred <= 0)
                return false;
            offset += static_cast<std::size_t>(transferred);
        }
        return true;
    }

    OlMod::DedicatedControl::ResponseStatus submitRaw(
        const std::uint16_t port,
        const std::vector<std::uint8_t> &request)
    {
        WSADATA winsock{};
        require(WSAStartup(MAKEWORD(2, 2), &winsock) == 0, "WSAStartup succeeds");
        const auto socketHandle = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        require(socketHandle != INVALID_SOCKET, "raw client socket opens");
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(port);
        require(connect(socketHandle, reinterpret_cast<const sockaddr *>(&address),
            sizeof(address)) == 0, "raw client connects");
        require(transferAll(socketHandle, request.data(), request.size(), true),
            "raw request sends");
        std::array<std::uint8_t, 24> response{};
        require(transferAll(socketHandle, response.data(), response.size(), false),
            "raw response receives");
        closesocket(socketHandle);
        WSACleanup();
        require(readU16(response, 4) == OlMod::DedicatedControl::ProtocolVersion,
            "raw response preserves protocol version");
        return static_cast<OlMod::DedicatedControl::ResponseStatus>(readU16(response, 6));
    }

    std::vector<std::uint8_t> malformedRequest(
        const std::uint32_t magic,
        const std::uint32_t payloadSize,
        const std::uint32_t checksum,
        const bool appendPayload)
    {
        std::vector<std::uint8_t> request;
        appendU32(request, magic);
        appendU16(request, OlMod::DedicatedControl::ProtocolVersion);
        appendU16(request, static_cast<std::uint16_t>(
            OlMod::DedicatedControl::MessageType::Booking));
        appendU32(request, payloadSize);
        appendU64(request, 77);
        appendU32(request, checksum);
        if (appendPayload)
            request.push_back('x');
        return request;
    }
}

int main()
{
    try
    {
        using namespace OlMod::DedicatedControl;
        _putenv_s("OLMOD_PROCESS_ROLE", "");
        require(OlMod::processRole() == OlMod::ProcessRole::Combined,
            "combined is the default process role");
        _putenv_s("OLMOD_PROCESS_ROLE", "client");
        require(OlMod::runsBackend(OlMod::processRole()) &&
            !OlMod::runsGameServer(OlMod::processRole()),
            "client role hosts the transitional backend but not gameplay");
        _putenv_s("OLMOD_PROCESS_ROLE", "DeDiCaTeD");
        require(!OlMod::runsBackend(OlMod::processRole()) &&
            OlMod::runsGameServer(OlMod::processRole()),
            "dedicated role hosts gameplay but not the backend control plane");
        _putenv_s("OLMOD_PROCESS_ROLE", "");

        const GameServerEndpointStatus endpointStatus{
            .sessionConfigured = true,
            .enabled = true,
            .bound = true,
            .port = 28960,
        };
        const auto encodedEndpointStatus = encodeEndpointStatus(endpointStatus);
        require(decodeEndpointStatus(encodedEndpointStatus) == endpointStatus,
            "dedicated endpoint status roundtrips through the control codec");
        auto malformedEndpointStatus = encodedEndpointStatus;
        malformedEndpointStatus[4] = 2;
        require(!decodeEndpointStatus(malformedEndpointStatus) &&
            !decodeEndpointStatus("short"),
            "dedicated endpoint status rejects unknown schemas and sizes");

        const GameplayStatus gameplayStatus{
            .serverTime = 3550,
            .sd = {
                .roundConfigured = 1,
                .roundArmed = 1,
                .bombConfigured = 1,
                .bombPhase = 1,
                .attackers = 1,
                .defenders = 1,
                .attackersAlive = 1,
                .defendersAlive = 1,
                .carrierClientNum = std::numeric_limits<std::uint32_t>::max(),
                .planterClientNum = std::numeric_limits<std::uint32_t>::max(),
                .defuserClientNum = std::numeric_limits<std::uint32_t>::max(),
            },
            .clients = {
                {
                    .clientNum = 0,
                    .gameplayState = 2,
                    .team = 1,
                    .reliableSequence = 4,
                    .reliableAcknowledge = 3,
                    .peerIpv4 = 0x7F000001,
                    .peerPort = 30099,
                    .lastPacketReceivedTime = 3440,
                    .incomingSequence = 42,
                    .outgoingSequence = 44,
                    .messageAcknowledge = 41,
                    .udpSendAttempts = 53,
                    .udpSendSucceeded = 52,
                    .udpSendFailed = 1,
                    .udpBytesSent = 65'432,
                    .lastUdpSendTime = 3540,
                    .lastUdpSendBytes = 1200,
                    .lastUdpSendError = 10054,
                    .pendingUserCmdCount = 3,
                    .oldestPendingUserCmdTime = 3400,
                    .newestPendingUserCmdTime = 3432,
                    .lastReceivedUserCmdTime = 3432,
                    .lastDispatchedUserCmdTime = 3400,
                    .lastExecutedUserCmdTime = 3384,
                    .lastDiscardedUserCmdTime = 3368,
                    .discardedUnsupportedUserCmds = 2,
                    .lastDiscardedRejectedUserCmdTime = 3376,
                    .discardedRejectedUserCmds = 3,
                    .clientThinkLastAttemptedCommandTime = 3400,
                    .clientThinkLastCommittedCommandTime = 3384,
                    .clientThinkFailureStage = 17,
                    .clientThinkFailureCount = 4,
                    .lastDispatchedButtons = 0x401,
                    .lastDispatchedAngles = { 1024, 2048, 0 },
                    .lastDispatchedWeapon = 73,
                    .lastDispatchedOffhand = 4,
                    .lastDispatchedForwardMove = 127,
                    .lastDispatchedRightMove = -127,
                    .snapshotPlayerEntityMask = 3,
                    .snapshotClientInfoMask = 3,
                    // Schema 5: the locational hit readout. Frida cannot sample
                    // it - CodolGameServerControl.py --pid <dedicated> kills the
                    // dedicated two runs out of three - so this is the only
                    // route by which a live hit height ever reaches a tool.
                    .origin = { 12.5f, -30.25f, 64.0f },
                    .viewAngles = { -3.5f, 137.25f, 0.0f },
                    .health = 70,
                    .bulletCommandTime = 3400,
                    .bulletStart = { 12.5f, -30.25f, 124.0f },
                    .bulletEnd = { 512.0f, -30.25f, 100.0f },
                    .bulletFraction = 0.4375f,
                    .bulletHitType = 1,
                    .bulletHitEntityNum = 1,
                    .bulletModelIndex = 2,
                    .bulletPartName = 1626,
                    .bulletPartGroup = 5,
                    .bulletResult = 0,
                    .objectives = {{{ 1, 17 }, { 1, 18 }, { 0, 0 }}},
                    .recentReliableCommands = {
                        { 3, "p 512" },
                        { 4, "E 0 100" },
                    },
                },
            },
        };
        const auto encodedGameplayStatus = encodeGameplayStatus(gameplayStatus);
        require(
            decodeGameplayStatus(encodedGameplayStatus) == gameplayStatus,
            "dedicated gameplay status roundtrips transport, usercmd, snapshot projection, SD, objectives and reliable commands");
        const auto decodedGameplayStatus =
            decodeGameplayStatus(encodedGameplayStatus);
        require(
            decodedGameplayStatus &&
                decodedGameplayStatus->clients.size() == 1 &&
                decodedGameplayStatus->clients.front().origin ==
                    std::array<float, 3>{ 12.5f, -30.25f, 64.0f } &&
                decodedGameplayStatus->clients.front().viewAngles ==
                    std::array<float, 3>{ -3.5f, 137.25f, 0.0f } &&
                decodedGameplayStatus->clients.front().bulletFraction ==
                    0.4375f &&
                decodedGameplayStatus->clients.front().bulletHitEntityNum == 1 &&
                decodedGameplayStatus->clients.front().bulletPartName == 1626 &&
                decodedGameplayStatus->clients.front().bulletPartGroup == 5,
            "the locational hit readout survives the control socket with exact float bit patterns");
        require(
            !decodeGameplayStatus(
                encodedGameplayStatus.substr(0, encodedGameplayStatus.size() - 1)) &&
                !decodeGameplayStatus(encodedGameplayStatus + "tail"),
            "dedicated gameplay status rejects truncated and trailing payloads");

        std::atomic_uint32_t accepted{};
        Server server;
        const auto start = [&] {
            return server.start(0, [&](const Message &message) {
                if (message.type != MessageType::Booking)
                    return Response{ .status = ResponseStatus::UnsupportedMessage };
                if (message.payload.empty())
                    return Response{ .status = ResponseStatus::InvalidMessage };
                ++accepted;
                return Response{
                    .status = ResponseStatus::Accepted,
                    .payload = "queued:" + message.payload,
                };
            });
        };

        require(start() && server.running() && server.port() != 0,
            "control server binds an ephemeral loopback port");
        const auto booking = submit("127.0.0.1", server.port(), {
            .type = MessageType::Booking,
            .requestId = 41,
            .payload = "map=mp_test;gametype=dm",
        });
        require(booking.delivered && booking.requestId == 41 &&
            booking.status == ResponseStatus::Accepted &&
            booking.payload == "queued:map=mp_test;gametype=dm" &&
            accepted.load() == 1,
            "booking roundtrip returns the matching accepted ACK");

        const auto unsupported = submit("127.0.0.1", server.port(), {
            .type = static_cast<MessageType>(99),
            .requestId = 42,
            .payload = "unsupported",
        });
        require(unsupported.delivered &&
            unsupported.status == ResponseStatus::UnsupportedMessage,
            "unknown message type is rejected by the receiver");

        const auto oversized = submit("127.0.0.1", server.port(), {
            .type = MessageType::Booking,
            .requestId = 43,
            .payload = std::string(MaximumPayloadSize + 1, 'x'),
        });
        require(!oversized.delivered, "sender rejects oversized payloads locally");
        require(submitRaw(server.port(), malformedRequest(0, 0, 0, false)) ==
            ResponseStatus::InvalidMessage, "invalid frame magic is rejected");
        require(submitRaw(server.port(), malformedRequest(
            FrameMagic, MaximumPayloadSize + 1, 0, false)) ==
            ResponseStatus::InvalidMessage, "oversized wire payload is rejected");
        require(submitRaw(server.port(), malformedRequest(FrameMagic, 1, 0, true)) ==
            ResponseStatus::InvalidMessage, "payload checksum mismatch is rejected");

        server.stop();
        require(!server.running() && server.port() == 0,
            "control server stops and clears its bound port");
        require(start() && server.port() != 0, "control server restarts cleanly");
        server.stop();
        extern void runDedicatedSessionTests();
        extern void runClientSessionBridgeTests();
        runDedicatedSessionTests();
        runClientSessionBridgeTests();
        std::cout << "Dedicated control tests passed\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception &error)
    {
        std::cerr << "Dedicated control tests failed: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
