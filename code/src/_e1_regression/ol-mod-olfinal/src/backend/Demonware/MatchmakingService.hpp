#pragma once

#include "LanDiscovery.hpp"
#include "ServiceRegistry.hpp"

#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <span>
#include <unordered_map>

#include <nlohmann/json.hpp>

namespace AlwaysofflineRe::Demonware
{
    struct GameServerEndpoint
    {
        std::uint32_t ipv4{};
        std::uint16_t port{};
    };

    class MatchmakingService
    {
    public:
        using GameServerProvider = std::function<std::optional<GameServerEndpoint>()>;
        using GameServerConfigurator = std::function<bool(
            std::span<const std::uint8_t>)>;
        using SessionDescriptorCanonicalizer = std::function<
            std::optional<std::vector<std::uint8_t>>(
                std::span<const std::uint8_t>)>;
        using SessionUpdatePublisher = std::function<void(const nlohmann::json &)>;
        using SessionTerminatePublisher = std::function<void()>;

        explicit MatchmakingService(
            bool startNetworking = true,
            GameServerProvider gameServerProvider = {},
            GameServerConfigurator gameServerConfigurator = {},
            SessionUpdatePublisher sessionUpdatePublisher = {},
            SessionTerminatePublisher sessionTerminatePublisher = {});
        void registerTasks(ServiceRegistry &registry) const;
        [[nodiscard]] bool ingestLanPacket(
            std::span<const std::uint8_t> packet,
            std::uint32_t sourceAddress) const;
        [[nodiscard]] LanDiscovery &messageBus() const { return discovery_; }
        void setSessionDescriptorCanonicalizer(
            SessionDescriptorCanonicalizer canonicalizer);

    private:
        [[nodiscard]] ServiceResponse createSession(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse updateSession(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse deleteSession(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse findSessions(const ServiceRequest &request) const;
        void writeSessionRecordTail(
            ByteBuffer &object,
            const LanDiscovery::RemoteSession &session) const;
        [[nodiscard]] ServiceResponse submitPerformance(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getPerformanceValues(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse updatePlayers(const ServiceRequest &request) const;

        mutable std::mutex localMutex_;
        mutable nlohmann::json localProperties_ = nlohmann::json::object();
        mutable std::mutex performanceMutex_;
        mutable std::unordered_map<
            std::uint64_t,
            std::unordered_map<std::uint32_t, std::int64_t>> performanceValues_;
        mutable LanDiscovery discovery_;
        GameServerProvider gameServerProvider_;
        GameServerConfigurator gameServerConfigurator_;
        SessionUpdatePublisher sessionUpdatePublisher_;
        SessionTerminatePublisher sessionTerminatePublisher_;
        SessionDescriptorCanonicalizer sessionDescriptorCanonicalizer_;
    };
}
