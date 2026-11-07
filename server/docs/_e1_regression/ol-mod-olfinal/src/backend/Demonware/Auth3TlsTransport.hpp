#pragma once

#include "Auth3Protocol.hpp"

#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class Auth3TlsTransport
    {
    public:
        using Diagnostic = std::function<void(std::string_view)>;

        Auth3TlsTransport(
            AuthSession &session,
            std::string hostname,
            Diagnostic diagnostic = {},
            PlayerIdentityStore *identityStore = nullptr);
        ~Auth3TlsTransport();

        Auth3TlsTransport(const Auth3TlsTransport &) = delete;
        Auth3TlsTransport &operator=(const Auth3TlsTransport &) = delete;

        void reset();
        void receive(std::span<const std::uint8_t> encrypted);
        [[nodiscard]] std::vector<std::uint8_t> takeOutput(std::size_t limit);

    private:
        struct Impl;
        std::unique_ptr<Impl> impl_;
    };
}
