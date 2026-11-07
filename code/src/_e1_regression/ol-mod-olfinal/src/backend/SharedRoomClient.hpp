#pragma once

#include "Demonware/AuthSession.hpp"
#include "SharedRoomSessionOwner.hpp"

#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe
{
    class SharedRoomClient
    {
    public:
        using Reporter = std::function<void(std::string_view)>;

        explicit SharedRoomClient(Reporter reporter = {});

        [[nodiscard]] bool connect(
            const Demonware::AuthIdentity &identity,
            std::uint16_t bridgePort);
        [[nodiscard]] bool disconnect(std::uint64_t userId);
        [[nodiscard]] bool setReady(std::uint64_t userId, bool ready);
        [[nodiscard]] std::optional<FrozenRoomRoster> freeze(
            std::uint64_t generation);
        [[nodiscard]] std::optional<std::vector<std::uint8_t>>
            canonicalizeSessionDescriptor(
                std::uint64_t userId,
                std::span<const std::uint8_t> descriptor);

    private:
        struct Connection
        {
            std::uint64_t userId{};
            std::uint64_t token{};
        };

        [[nodiscard]] std::uint64_t nextRequestId();

        std::mutex mutex_;
        Reporter reporter_;
        std::optional<Connection> connection_;
        std::uint64_t nextRequestId_{1};
    };
}
