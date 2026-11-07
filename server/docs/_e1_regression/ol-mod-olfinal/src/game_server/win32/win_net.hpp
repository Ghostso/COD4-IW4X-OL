#pragma once

#include "qcommon/net_types.hpp"

#include <cstddef>
#include <cstdint>
#include <span>

namespace CodolGameServer
{
    enum class NetPacketResult : std::uint8_t
    {
        Empty,
        Received,
        Error,
    };

    // IPv4 bind address in HOST byte order, matching PeerAddress::ipv4. Zero is
    // INADDR_ANY -- every local interface -- which is what every caller relied
    // on before an address could be named at all.
    inline constexpr std::uint32_t AnyIpv4Address = 0;

    // Reported through lastError() by SvUdpTransport::start when a live binding
    // already exists and a different explicit port was requested. Numerically
    // WSAEALREADY; win_net.cpp static_asserts that equality so it cannot drift.
    inline constexpr int SocketAlreadyBoundError = 10037;

    class NetUdpSocket
    {
    public:
        NetUdpSocket() = default;
        ~NetUdpSocket();
        NetUdpSocket(const NetUdpSocket &) = delete;
        NetUdpSocket &operator=(const NetUdpSocket &) = delete;

        // Binds an IPv4 UDP socket to bindAddress:port. bindAddress is host byte
        // order (see AnyIpv4Address); port 0 asks the OS for an ephemeral port.
        bool NET_IPSocket(
            std::uint16_t port,
            std::uint32_t bindAddress = AnyIpv4Address);
        // Releases the socket. Returns true when the handle is released or was
        // already released. Returns false when closesocket failed: lastError()
        // then holds the Winsock error and the handle stays open, so a caller
        // cannot mistake a failed close for a clean stop.
        bool close();
        NetPacketResult NET_GetPacket(
            PeerAddress &peer,
            std::span<std::uint8_t> buffer,
            std::size_t &packetSize);
        bool NET_SendPacket(PeerAddress peer, std::span<const std::uint8_t> packet);

        [[nodiscard]] bool open() const;
        [[nodiscard]] std::uint16_t port() const;
        [[nodiscard]] int lastError() const;

    private:
        std::uintptr_t socket_{ static_cast<std::uintptr_t>(-1) };
        std::uint16_t port_{};
        int lastError_{};
        bool winsockStarted_{};
    };
}
