#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <WS2tcpip.h>

#include <iostream>
#include <unordered_map>

#include "win_net.hpp"

namespace CodolGameServer
{
    static_assert(
        SocketAlreadyBoundError == WSAEALREADY,
        "SocketAlreadyBoundError must mirror WSAEALREADY");

    namespace
    {
        constexpr auto InvalidSocket = static_cast<std::uintptr_t>(INVALID_SOCKET);
        std::unordered_map<std::uintptr_t, std::uint32_t> socketDiagnostics;
    }

    NetUdpSocket::~NetUdpSocket()
    {
        close();
    }

    bool NetUdpSocket::NET_IPSocket(
        const std::uint16_t port,
        const std::uint32_t bindAddress)
    {
        // A handle that could not be released must not be silently overwritten:
        // that would leak it and hide the failure.
        if (!close())
            return false;
        WSADATA winsock{};
        const auto startupError = WSAStartup(MAKEWORD(2, 2), &winsock);
        if (startupError != 0)
        {
            lastError_ = startupError;
            return false;
        }
        winsockStarted_ = true;

        const auto socketHandle = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (socketHandle == INVALID_SOCKET)
        {
            lastError_ = WSAGetLastError();
            close();
            return false;
        }
        socket_ = static_cast<std::uintptr_t>(socketHandle);

        u_long nonBlocking = 1;
        if (ioctlsocket(socketHandle, FIONBIO, &nonBlocking) == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            close();
            return false;
        }

        const BOOL broadcast = TRUE;
        if (setsockopt(
                socketHandle,
                SOL_SOCKET,
                SO_BROADCAST,
                reinterpret_cast<const char *>(&broadcast),
                sizeof(broadcast)) == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            close();
            return false;
        }

        sockaddr_in address{};
        address.sin_family = AF_INET;
        // bindAddress is host byte order (PeerAddress::ipv4 convention); the
        // socket layer wants network byte order.
        address.sin_addr.s_addr = htonl(bindAddress);
        address.sin_port = htons(port);
        if (bind(
                socketHandle,
                reinterpret_cast<const sockaddr *>(&address),
                sizeof(address)) == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            close();
            return false;
        }

        sockaddr_in boundAddress{};
        int boundAddressSize = sizeof(boundAddress);
        if (getsockname(
                socketHandle,
                reinterpret_cast<sockaddr *>(&boundAddress),
                &boundAddressSize) == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            close();
            return false;
        }
        port_ = ntohs(boundAddress.sin_port);
        lastError_ = 0;
        std::clog << "[dedicated/game-server] udp bound socket=" << socket_
                  << " port=" << port_ << " address="
                  << ((bindAddress >> 24) & 0xFFu) << "."
                  << ((bindAddress >> 16) & 0xFFu) << "."
                  << ((bindAddress >> 8) & 0xFFu) << "."
                  << (bindAddress & 0xFFu) << std::endl;
        return true;
    }

    bool NetUdpSocket::close()
    {
        if (socket_ != InvalidSocket)
        {
            if (closesocket(static_cast<SOCKET>(socket_)) == SOCKET_ERROR)
            {
                // Leave the handle marked open: the caller must be able to see
                // that the socket was not released instead of reporting a clean
                // stop. A later close() retries.
                lastError_ = WSAGetLastError();
                return false;
            }
            socket_ = InvalidSocket;
        }
        port_ = 0;
        if (winsockStarted_)
        {
            WSACleanup();
            winsockStarted_ = false;
        }
        return true;
    }

    NetPacketResult NetUdpSocket::NET_GetPacket(
        PeerAddress &peer,
        const std::span<std::uint8_t> buffer,
        std::size_t &packetSize)
    {
        packetSize = 0;
        if (!open() || buffer.empty())
            return NetPacketResult::Error;

        sockaddr_in source{};
        int sourceSize = sizeof(source);
        const auto received = recvfrom(
            static_cast<SOCKET>(socket_),
            reinterpret_cast<char *>(buffer.data()),
            static_cast<int>(buffer.size()),
            0,
            reinterpret_cast<sockaddr *>(&source),
            &sourceSize);
        if (received == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            const auto diagnostic = socketDiagnostics[socket_];
            if (diagnostic < 8 && lastError_ != WSAEWOULDBLOCK)
            {
                ++socketDiagnostics[socket_];
                std::clog << "[dedicated/game-server] udp recv error socket="
                          << socket_ << " port=" << port_
                          << " error=" << lastError_ << std::endl;
            }
            if (lastError_ == WSAEWOULDBLOCK || lastError_ == WSAECONNRESET)
            {
                lastError_ = 0;
                return NetPacketResult::Empty;
            }
            return NetPacketResult::Error;
        }

        lastError_ = 0;
        peer = {
            .ipv4 = ntohl(source.sin_addr.s_addr),
            .port = ntohs(source.sin_port),
        };
        packetSize = static_cast<std::size_t>(received);
        return NetPacketResult::Received;
    }

    bool NetUdpSocket::NET_SendPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet)
    {
        if (!open() || packet.empty())
            return false;
        sockaddr_in destination{};
        destination.sin_family = AF_INET;
        destination.sin_addr.s_addr = htonl(peer.ipv4);
        destination.sin_port = htons(peer.port);
        const auto sent = sendto(
            static_cast<SOCKET>(socket_),
            reinterpret_cast<const char *>(packet.data()),
            static_cast<int>(packet.size()),
            0,
            reinterpret_cast<const sockaddr *>(&destination),
            sizeof(destination));
        if (sent == SOCKET_ERROR)
        {
            lastError_ = WSAGetLastError();
            return false;
        }
        lastError_ = 0;
        return static_cast<std::size_t>(sent) == packet.size();
    }

    bool NetUdpSocket::open() const
    {
        return socket_ != InvalidSocket;
    }

    std::uint16_t NetUdpSocket::port() const
    {
        return port_;
    }

    int NetUdpSocket::lastError() const
    {
        return lastError_;
    }
}
