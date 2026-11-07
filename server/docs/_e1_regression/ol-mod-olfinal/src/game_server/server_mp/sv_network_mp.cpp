#include "sv_network_mp.hpp"

#include <iostream>
#include <unordered_map>

#include "../../shared/RuntimeLog.hpp"

namespace CodolGameServer
{
    namespace
    {
        std::unordered_map<std::uint64_t, std::uint32_t> transportPacketDiagnostics;

        std::uint64_t peerKey(const PeerAddress peer)
        {
            return (static_cast<std::uint64_t>(peer.ipv4) << 16) | peer.port;
        }
    }

    // REGRESSION HARNESS (isolated copy only): this is the pre-T-1 start()
    // body, kept with the new two-argument signature so the E-1 test compiles.
    bool SvUdpTransport::start(
        const std::uint16_t port,
        const std::uint32_t bindAddress)
    {
        const std::lock_guard lock(mutex_);
        if (socket_.open() && socket_.port() == port)
            return true;
        socket_.close();
        status_ = {};
        peerStatus_.clear();
        if (!socket_.NET_IPSocket(port, bindAddress))
        {
            status_.lastSocketError = socket_.lastError();
            return false;
        }
        status_.bound = true;
        status_.port = socket_.port();
        return true;
    }

    void SvUdpTransport::stop()
    {
        const std::lock_guard lock(mutex_);
        if (!socket_.close())
        {
            // The handle is still live. Report the failure and leave the bound
            // state intact rather than pretending the transport stopped cleanly.
            status_.lastSocketError = socket_.lastError();
            return;
        }
        status_.bound = false;
        status_.port = 0;
        status_.packetsReceived = 0;
        status_.packetsSent = 0;
        status_.lastPacketReceivedTime = 0;
        status_.lastPacketSentTime = 0;
        // lastSocketError is deliberately retained: it is the sticky record of
        // the last socket failure and is cleared by the next successful start().
        peerStatus_.clear();
        nonce_ = 0;
    }

    void SvUdpTransport::NET_Frame(
        ServerCore &server,
        const std::uint32_t nowMilliseconds)
    {
        const std::lock_guard lock(mutex_);
        if (!socket_.open())
            return;

        for (std::size_t packetIndex = 0; packetIndex < MaxPacketsPerFrame; ++packetIndex)
        {
            PeerAddress peer{};
            std::size_t packetSize{};
            const auto received = socket_.NET_GetPacket(peer, receiveBuffer_, packetSize);
            if (received == NetPacketResult::Empty)
                break;
            if (received == NetPacketResult::Error)
            {
                status_.lastSocketError = socket_.lastError();
                break;
            }

            ++status_.packetsReceived;
            status_.lastPacketReceivedTime = nowMilliseconds;
            const auto diagnosticKey = peerKey(peer);
            if (transportPacketDiagnostics[diagnosticKey]++ < 8)
            {
                const auto packetType = packetSize
                    ? static_cast<unsigned int>(receiveBuffer_.front())
                    : 0u;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "udp packet peer=" + std::to_string(peer.ipv4) + ":" +
                    std::to_string(peer.port) + " bytes=" +
                    std::to_string(packetSize) + " type=" +
                    std::to_string(packetType));
            }
            nonce_ = nonce_ * 1664525u + 1013904223u;
            const auto entropy = nonce_ ^ nowMilliseconds ^ peer.ipv4 ^
                (static_cast<std::uint32_t>(peer.port) << 16);
            const auto result = server.NET_DtlsPacket(
                peer,
                std::span(receiveBuffer_).first(packetSize),
                nowMilliseconds,
                entropy);
            if (!result.reply.empty())
                NET_SendPacket(peer, result.reply, nowMilliseconds);
        }
    }

    void SvUdpTransport::NET_SendPackets(
        const std::span<const SvOutboundPacket> packets,
        const std::uint32_t nowMilliseconds)
    {
        const std::lock_guard lock(mutex_);
        if (!socket_.open())
            return;
        for (const auto &packet : packets)
        {
            if (!packet.data.empty())
                NET_SendPacket(packet.peer, packet.data, nowMilliseconds);
        }
    }

    bool SvUdpTransport::NET_SendPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds)
    {
        auto &peerStatus = peerStatus_[peerKey(peer)];
        peerStatus.peer = peer;
        ++peerStatus.sendAttempts;
        peerStatus.lastSendTime = nowMilliseconds;
        peerStatus.lastSendBytes = static_cast<std::uint32_t>(packet.size());

        const auto sent = socket_.NET_SendPacket(peer, packet);
        peerStatus.lastSendError = socket_.lastError();
        status_.lastSocketError = peerStatus.lastSendError;
        if (!sent)
        {
            ++peerStatus.sendFailed;
            return false;
        }

        ++peerStatus.sendSucceeded;
        peerStatus.bytesSent += packet.size();
        ++status_.packetsSent;
        status_.lastPacketSentTime = nowMilliseconds;
        return true;
    }

    SvNetworkStatus SvUdpTransport::status() const
    {
        const std::lock_guard lock(mutex_);
        return status_;
    }

    std::optional<SvPeerNetworkStatus> SvUdpTransport::peerStatus(
        const PeerAddress peer) const
    {
        const std::lock_guard lock(mutex_);
        const auto found = peerStatus_.find(peerKey(peer));
        return found == peerStatus_.end()
            ? std::nullopt
            : std::optional{ found->second };
    }
}
