#pragma once

#include "sv_main_mp.hpp"
#include "win32/win_net.hpp"

#include <array>
#include <cstdint>
#include <mutex>
#include <optional>
#include <span>
#include <unordered_map>

namespace CodolGameServer
{
    struct SvNetworkStatus
    {
        bool bound{};
        std::uint16_t port{};
        std::uint32_t packetsReceived{};
        std::uint32_t packetsSent{};
        std::uint32_t lastPacketReceivedTime{};
        std::uint32_t lastPacketSentTime{};
        int lastSocketError{};
    };

    struct SvPeerNetworkStatus
    {
        PeerAddress peer{};
        std::uint64_t sendAttempts{};
        std::uint64_t sendSucceeded{};
        std::uint64_t sendFailed{};
        std::uint64_t bytesSent{};
        std::uint32_t lastSendTime{};
        std::uint32_t lastSendBytes{};
        int lastSendError{};

        bool operator==(const SvPeerNetworkStatus &) const = default;
    };

    class SvUdpTransport
    {
    public:
        // Binds the transport. bindAddress is an IPv4 address in HOST byte order
        // (the PeerAddress::ipv4 convention); the default is every interface,
        // which is what production callers already used.
        //
        // Idempotent while a socket is already open:
        //   port == 0           -> the live binding already satisfies an
        //                          ephemeral request; return true, unchanged
        //   port == bound port  -> return true, unchanged
        //   other non-zero port -> return false with lastSocketError ==
        //                          SocketAlreadyBoundError; the binding, its
        //                          counters and its timestamps are untouched
        // Call stop() before start() to change the port or the address.
        bool start(
            std::uint16_t port = 28960,
            std::uint32_t bindAddress = AnyIpv4Address);
        // Releases the socket and returns the transport to its unbound state:
        // bound=false, port=0, counters and timestamps zeroed, peer and nonce
        // state cleared. lastSocketError is retained (it is the sticky record of
        // the last socket failure, cleared by the next successful start()). If
        // the socket cannot be released, the bound state is left intact and
        // lastSocketError carries the failure instead of a clean stop.
        void stop();
        void NET_Frame(ServerCore &server, std::uint32_t nowMilliseconds);
        void NET_SendPackets(
            std::span<const SvOutboundPacket> packets,
            std::uint32_t nowMilliseconds);
        [[nodiscard]] SvNetworkStatus status() const;
        [[nodiscard]] std::optional<SvPeerNetworkStatus> peerStatus(
            PeerAddress peer) const;

    private:
        static constexpr std::size_t MaxPacketsPerFrame = 64;
        static constexpr std::size_t MaxPacketSize = 65'507;

        NetUdpSocket socket_;
        std::array<std::uint8_t, MaxPacketSize> receiveBuffer_{};
        SvNetworkStatus status_{};
        std::unordered_map<std::uint64_t, SvPeerNetworkStatus> peerStatus_;
        std::uint32_t nonce_{};
        mutable std::mutex mutex_;

        bool NET_SendPacket(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds);
    };
}
