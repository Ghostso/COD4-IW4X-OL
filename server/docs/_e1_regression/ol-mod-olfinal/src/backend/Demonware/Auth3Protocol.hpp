#pragma once

#include "AuthSession.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace AlwaysofflineRe::Demonware
{
    struct Auth3Result
    {
        std::uint32_t titleId{};
        std::uint32_t authTask{};
        std::uint32_t ivSeed{};
        std::uint64_t userId{};
        std::string username;
        std::string json;
    };

    class Auth3Protocol
    {
    public:
        explicit Auth3Protocol(
            AuthSession &session,
            PlayerIdentityStore *identityStore = nullptr);

        [[nodiscard]] Auth3Result authenticate(std::string_view requestJson);
        [[nodiscard]] static std::string httpResponse(std::string_view json);

    private:
        AuthSession &session_;
        PlayerIdentityStore *identityStore_{};
    };
}
