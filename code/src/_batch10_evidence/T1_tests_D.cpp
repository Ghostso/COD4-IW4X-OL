// Independent, offline verification of the transport lifecycle contract:
// loopback binding, start() idempotency, stop() state cleanup and rebinding.
//
// No game process and no injection are involved. Every case binds a real UDP
// socket on the loopback interface and an ephemeral port, so the production
// game port is never occupied or disturbed.

#include "server_mp/sv_network_mp.hpp"
#include "win32/win_net.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <thread>
#include <vector>

namespace
{
    using CodolGameServer::AnyIpv4Address;
    using CodolGameServer::NetPacketResult;
    using CodolGameServer::NetUdpSocket;
    using CodolGameServer::PeerAddress;
    using CodolGameServer::SocketAlreadyBoundError;
    using CodolGameServer::SvOutboundPacket;
    using CodolGameServer::SvUdpTransport;

    // INADDR_ANY is zero, and PeerAddress::ipv4 is host byte order.
    static_assert(AnyIpv4Address == 0, "INADDR_ANY must be zero in host byte order");

    constexpr std::uint32_t LoopbackIpv4 = 0x7F000001u;

    int Checks{};
    int Failures{};

    void require(const bool condition, const char *const message)
    {
        ++Checks;
        if (condition)
        {
            std::cout << "  ok   " << message << '\n';
            return;
        }
        ++Failures;
        std::cout << "  FAIL " << message << '\n';
    }

    std::uint16_t differentPort(const std::uint16_t port)
    {
        return static_cast<std::uint16_t>(port == 65535 ? port - 1 : port + 1);
    }

    void testLoopbackEphemeralBinding()
    {
        std::cout << "[1/8] loopback ephemeral bind\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0, 127.0.0.1) succeeds");
        const auto status = transport.status();
        require(status.bound, "bound is set");
        require(status.port != 0, "an ephemeral port was assigned");
        transport.stop();
    }

    void testRepeatedStartKeepsBinding()
    {
        std::cout << "[2/8] repeated start(0) is idempotent\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "first start(0) succeeds");
        const auto first = transport.status();
        require(first.port != 0, "the first bind assigned an ephemeral port");

        // E-1: drive the real send path so the counter under test is non-zero.
        // A datagram addressed to the transport's own loopback port is a legal
        // local send; it needs no peer, no client and no public network.
        const std::array<SvOutboundPacket, 1> outbound{ {
            SvOutboundPacket{
                .peer = { LoopbackIpv4, first.port },
                .data = { 0x01, 0x02, 0x03, 0x04 } },
        } };
        transport.NET_SendPackets(outbound, 1000);
        const auto beforeRestart = transport.status();
        require(beforeRestart.packetsSent > 0, "the send path makes packetsSent non-zero");
        require(beforeRestart.packetsReceived == 0, "the send path leaves packetsReceived alone");

        require(transport.start(0, LoopbackIpv4), "second start(0) succeeds");
        const auto second = transport.status();
        require(second.port == first.port, "the bound port is unchanged");
        require(
            second.packetsSent == beforeRestart.packetsSent,
            "the non-zero send counter survives the repeated start");
        require(second.packetsReceived == 0, "the repeated start does not fabricate a receive count");

        // The repeated start must not have invalidated the socket: it still sends.
        transport.NET_SendPackets(outbound, 1001);
        const auto afterSecondSend = transport.status();
        require(
            afterSecondSend.packetsSent == beforeRestart.packetsSent + 1,
            "the socket still sends after the repeated start");
        require(afterSecondSend.bound, "the transport is still bound after the repeated start");
        std::cout << "       packetsSent=" << beforeRestart.packetsSent
                  << " after repeated start=" << second.packetsSent
                  << " after second send=" << afterSecondSend.packetsSent << '\n';
        transport.stop();
    }

    void testDifferentPortDoesNotDisturbBinding()
    {
        std::cout << "[3/8] a different explicit port cannot steal a live binding\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        const auto bound = transport.status();
        require(!transport.start(differentPort(bound.port), LoopbackIpv4), "start(other) fails");
        const auto conflict = transport.status();
        require(conflict.bound, "the transport is still bound");
        require(conflict.port == bound.port, "the bound port is untouched");
        require(
            conflict.lastSocketError == SocketAlreadyBoundError,
            "the conflict is reported as SocketAlreadyBoundError");
        transport.stop();
    }

    void testStopClearsState()
    {
        std::cout << "[4/8] stop() clears the state\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound, "bound is cleared");
        require(stopped.port == 0, "port is cleared");
        require(
            stopped.packetsReceived == 0 && stopped.packetsSent == 0,
            "the counters are zeroed");
        require(
            stopped.lastPacketReceivedTime == 0 && stopped.lastPacketSentTime == 0,
            "the timestamps are zeroed");
    }

    void testRepeatedStop()
    {
        std::cout << "[5/8] repeated stop() is idempotent\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound && stopped.port == 0, "the second stop() leaves a clean state");
    }

    void testRebindAfterStop()
    {
        std::cout << "[6/8] rebinding after stop()\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        require(transport.start(0, LoopbackIpv4), "start(0) after stop() succeeds");
        const auto rebound = transport.status();
        require(rebound.bound && rebound.port != 0, "the transport is bound again");
        require(
            rebound.packetsReceived == 0 && rebound.packetsSent == 0,
            "the counters restart at zero");
        require(rebound.lastSocketError == 0, "a successful start() clears the sticky error");
        transport.stop();
    }

    void testStickyErrorAcrossStop()
    {
        std::cout << "[7/8] stop() retains the sticky socket error\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        const auto bound = transport.status();
        require(!transport.start(differentPort(bound.port), LoopbackIpv4), "start(other) fails");
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound && stopped.port == 0, "stop() cleared the binding");
        require(
            stopped.lastSocketError == SocketAlreadyBoundError,
            "the sticky error survives stop()");
    }

    void testOccupiedPortFails()
    {
        std::cout << "[8/8] an occupied loopback port fails to start\n";
        NetUdpSocket holder;
        require(holder.NET_IPSocket(0, LoopbackIpv4), "the holder binds an ephemeral port");
        const auto heldPort = holder.port();
        require(heldPort != 0, "the holder has a non-zero port");
        SvUdpTransport blocked;
        require(!blocked.start(heldPort, LoopbackIpv4), "binding the occupied port fails");
        const auto failed = blocked.status();
        require(!failed.bound, "a failed start leaves the transport unbound");
        require(failed.port == 0, "a failed start leaves the port at zero");
        require(failed.lastSocketError != 0, "a failed start records a socket error");
        blocked.stop();
    }

    void testDefaultAddressStaysInaddrAny()
    {
        std::cout << "[extra] the default address stays INADDR_ANY\n";
        // A default-bound socket must accept traffic addressed to loopback; a
        // narrower default (one interface) would not.
        NetUdpSocket receiver;
        require(receiver.NET_IPSocket(0), "the default address binds");
        const auto receiverPort = receiver.port();
        require(receiverPort != 0, "the default address binds an ephemeral port");

        NetUdpSocket sender;
        require(sender.NET_IPSocket(0, LoopbackIpv4), "the loopback sender binds");
        const std::array<std::uint8_t, 4> payload{ 0xDE, 0xAD, 0xBE, 0xEF };
        require(
            sender.NET_SendPacket({ LoopbackIpv4, receiverPort }, payload),
            "a loopback datagram is sent to the default-bound port");

        PeerAddress from{};
        std::array<std::uint8_t, 32> buffer{};
        std::size_t size{};
        auto received = NetPacketResult::Empty;
        for (int attempt = 0; attempt < 200; ++attempt)
        {
            received = receiver.NET_GetPacket(from, buffer, size);
            if (received != NetPacketResult::Empty)
                break;
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        require(received == NetPacketResult::Received, "the default-bound socket receives it");
        require(size == payload.size(), "the payload length matches");
        require(
            std::equal(payload.begin(), payload.end(), buffer.begin()),
            "the payload bytes match");

        // The transport's own default overload must bind as well.
        SvUdpTransport defaultBound;
        require(defaultBound.start(0), "SvUdpTransport::start(0) uses the default address");
        const auto status = defaultBound.status();
        require(status.bound && status.port != 0, "the default overload reports a bound port");
        defaultBound.stop();
    }
}

int main()
{
    std::cout << "=== ol_transport_lifecycle_tests ===\n";
    testLoopbackEphemeralBinding();
    testRepeatedStartKeepsBinding();
    testDifferentPortDoesNotDisturbBinding();
    testStopClearsState();
    testRepeatedStop();
    testRebindAfterStop();
    testStickyErrorAcrossStop();
    testOccupiedPortFails();
    testDefaultAddressStaysInaddrAny();
    std::cout << "checks=" << Checks << " failures=" << Failures << '\n';
    return Failures == 0 ? 0 : 1;
}
