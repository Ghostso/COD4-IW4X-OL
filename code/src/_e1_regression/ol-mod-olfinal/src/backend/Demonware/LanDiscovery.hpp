#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include <nlohmann/json.hpp>

namespace AlwaysofflineRe::Demonware
{
    class LanDiscovery
    {
    public:
        using EventHandler = std::function<void(std::uint64_t, std::string_view)>;

        struct RemoteSession
        {
            std::uint32_t address{};
            std::uint64_t id{};
            nlohmann::json properties = nlohmann::json::object();
            std::chrono::steady_clock::time_point updatedAt;
        };

        explicit LanDiscovery(std::uint64_t localId, bool startNetworking = true);
        ~LanDiscovery();

        LanDiscovery(const LanDiscovery &) = delete;
        LanDiscovery &operator=(const LanDiscovery &) = delete;

        void broadcastUpdate(const nlohmann::json &properties);
        void broadcastTerminate();
        void broadcast(std::string_view event, std::string_view payload);
        void subscribe(std::string event, EventHandler handler);
        [[nodiscard]] std::vector<RemoteSession> activeSessions() const;

        [[nodiscard]] bool ingestPacket(
            std::span<const std::uint8_t> packet,
            std::uint32_t sourceAddress);
        [[nodiscard]] static std::vector<std::uint8_t> encodePacket(
            std::string_view event,
            std::uint64_t origin,
            std::string_view payload);

    private:
        class State;

        std::uint64_t localId_{};
        mutable std::mutex sessionsMutex_;
        mutable std::vector<RemoteSession> sessions_;
        mutable std::unordered_map<std::uint64_t, std::uint32_t> nodeAddresses_;
        std::mutex handlersMutex_;
        std::unordered_map<std::string, EventHandler> handlers_;
        std::unique_ptr<State> state_;
    };
}
