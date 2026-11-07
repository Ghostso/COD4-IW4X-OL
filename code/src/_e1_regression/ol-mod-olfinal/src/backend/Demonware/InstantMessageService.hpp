#pragma once

#include "AuthSession.hpp"
#include "LanDiscovery.hpp"
#include "ServiceRegistry.hpp"

#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class InstantMessageService
    {
    public:
        using PushSink = std::function<void(std::vector<std::uint8_t>, std::uint8_t)>;
        using BookingSink = std::function<void(std::string_view)>;

        explicit InstantMessageService(
            AuthSession &session,
            PushSink pushSink = {},
            LanDiscovery *messageBus = nullptr,
            BookingSink bookingSink = {});

        void registerTasks(ServiceRegistry &registry) const;
        [[nodiscard]] static std::optional<std::vector<std::uint8_t>> decodeInstantPush(
            std::string_view eventJson,
            std::uint64_t localUserId);

    private:
        [[nodiscard]] ServiceResponse task5(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task14(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task18(const ServiceRequest &request) const;
        void publish(
            std::uint64_t recipient,
            std::span<const std::uint8_t> message,
            bool invokeLocalReceiver,
            bool broadcastEvent) const;
        [[nodiscard]] std::optional<std::vector<std::uint8_t>> decodeLocalCommand(
            std::span<const std::uint8_t> message) const;

        AuthSession &session_;
        PushSink pushSink_;
        LanDiscovery *messageBus_{};
        BookingSink bookingSink_;
    };
}
