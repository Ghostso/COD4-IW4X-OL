#pragma once

#include "Crypto.hpp"
#include "ServiceRegistry.hpp"

#include <array>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <span>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    enum class LobbyPhase
    {
        clientHeader,
        clientAuth,
        established,
    };

    struct DecodedLobbyMessage
    {
        std::uint32_t sequence{};
        std::uint8_t messageType{};
        std::vector<std::uint8_t> payload;
    };

    [[nodiscard]] std::vector<std::uint8_t> encodeEncryptedLobbyMessage(
        std::span<const std::uint8_t> payload,
        std::span<const std::uint8_t> aesKey,
        std::span<const std::uint8_t> hmacKey,
        std::uint32_t sequence,
        std::span<const std::uint8_t> iv,
        std::uint8_t messageType = 0x86);
    [[nodiscard]] DecodedLobbyMessage decodeEncryptedLobbyMessage(
        std::span<const std::uint8_t> frame,
        std::span<const std::uint8_t> aesKey,
        std::span<const std::uint8_t> hmacKey);

    class LobbyProtocol
    {
    public:
        using Diagnostic = std::function<void(std::string_view)>;

        explicit LobbyProtocol(ServiceRegistry &registry, Diagnostic diagnostic = {});

        void reset();
        void setSessionKey(std::span<const std::uint8_t> sessionKey);
        void receive(std::span<const std::uint8_t> data);
        void queuePush(std::vector<std::uint8_t> payload, std::uint8_t messageType = 2);
        [[nodiscard]] std::vector<std::uint8_t> takeOutput(std::size_t limit);
        [[nodiscard]] LobbyPhase phase() const { return phase_; }
        [[nodiscard]] const SessionKeys &keys() const { return keys_; }

    private:
        void processFrame(std::span<const std::uint8_t> frame);
        void processClientHeader(std::span<const std::uint8_t> frame);
        void processClientAuth(std::span<const std::uint8_t> frame);
        void processServiceMessage(std::span<const std::uint8_t> frame);
        void flushQueuedPushes();
        void emit(std::span<const std::uint8_t> data);
        void report(std::string_view message) const;

        ServiceRegistry &registry_;
        Diagnostic diagnostic_;
        LobbyPhase phase_{ LobbyPhase::clientHeader };
        std::array<std::uint8_t, 24> sessionKey_{};
        SessionKeys keys_{};
        std::vector<std::uint8_t> transcript_;
        std::vector<std::uint8_t> input_;
        std::vector<std::uint8_t> output_;
        std::uint32_t outgoingSequence_{};
        std::mutex pushMutex_;
        std::deque<DecodedLobbyMessage> queuedPushes_;
    };
}
