#pragma once

#include "IdentityConfig.hpp"

#include <array>
#include <cstdint>
#include <mutex>
#include <string>

namespace AlwaysofflineRe::Demonware
{
    struct AuthIdentity
    {
        std::uint32_t titleId{ 1004 };
        std::uint64_t userId{ 0x1100001DEADC0DEULL };
        std::string username{ DefaultUsername };
        std::array<std::uint8_t, 24> sessionKey{};
    };

    class AuthSession
    {
    public:
        AuthSession();

        [[nodiscard]] AuthIdentity snapshot() const;
        void update(AuthIdentity identity);

    private:
        mutable std::mutex mutex_;
        AuthIdentity identity_;
    };
}
