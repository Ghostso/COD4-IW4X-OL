#pragma once

#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace AlwaysofflineRe::Demonware
{
    enum class Endpoint
    {
        auth,
        lobby,
    };

    struct RecoveredService
    {
        Endpoint endpoint;
        std::uint8_t id;
        std::uint32_t legacyDispatcherRva;
        std::string_view name;
    };

    [[nodiscard]] std::span<const RecoveredService> recoveredServices();
    [[nodiscard]] std::optional<RecoveredService> findRecoveredService(Endpoint endpoint, std::uint8_t id);
}
