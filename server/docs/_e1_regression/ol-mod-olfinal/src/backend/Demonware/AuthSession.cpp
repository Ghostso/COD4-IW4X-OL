#include "AuthSession.hpp"

#include <charconv>
#include <cstdlib>
#include <string_view>
#include <system_error>
#include <utility>

namespace
{
    bool parsePlatformUserId(std::string_view value, std::uint64_t &output)
    {
        if (value.starts_with("0x") || value.starts_with("0X"))
            value.remove_prefix(2);
        if (value.empty())
            return false;

        std::uint64_t parsed{};
        const auto result = std::from_chars(
            value.data(), value.data() + value.size(), parsed, 16);
        if (result.ec != std::errc{} || result.ptr != value.data() + value.size() || !parsed)
            return false;
        output = parsed <= 0xFFFFFFFFull
            ? 0x0110000100000000ull | parsed
            : parsed;
        return true;
    }
}

namespace AlwaysofflineRe::Demonware
{
    AuthSession::AuthSession()
    {
        char *configured{};
        std::size_t size{};
        if (_dupenv_s(&configured, &size, "OLMOD_PLATFORM_USER_ID") == 0 && configured)
        {
            std::uint64_t parsed{};
            if (parsePlatformUserId(configured, parsed))
                identity_.userId = parsed;
            std::free(configured);
        }
    }

    AuthIdentity AuthSession::snapshot() const
    {
        std::scoped_lock lock(mutex_);
        return identity_;
    }

    void AuthSession::update(AuthIdentity identity)
    {
        std::scoped_lock lock(mutex_);
        identity_ = std::move(identity);
    }
}
