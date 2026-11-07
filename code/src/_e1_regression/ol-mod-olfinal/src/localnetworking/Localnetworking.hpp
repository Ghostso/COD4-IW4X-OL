#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <Windows.h>

#include "RuntimePaths.hpp"
#include "../shared/LocalnetServer.hpp"

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

namespace OlMod::Localnetworking
{
    [[nodiscard]] std::uint32_t fnv1a32(std::string_view value);
    [[nodiscard]] std::uint32_t syntheticIpv4(std::string_view hostname);

    class Bridge
    {
    public:
        static Bridge &instance();

        bool start(const RuntimePaths &paths, std::uint16_t firstPort = 4200);
        [[nodiscard]] bool claimsHost(std::string_view hostname);
        void associatePort(std::string_view hostname, std::uint16_t networkPort);
        [[nodiscard]] SOCKET createDatagramSocket(
            const IServer::Address &clientAddress,
            const IServer::Address &serverAddress,
            std::string_view hostname);
        [[nodiscard]] std::uint16_t backendPort() const;
        void log(std::string_view message);

    private:
        Bridge() = default;
        Bridge(const Bridge &) = delete;
        Bridge &operator=(const Bridge &) = delete;

        struct State;
        State *state_{};
    };

    bool installWinsockHooks();
    void setModuleHandle(HMODULE module);
    [[nodiscard]] std::optional<RuntimePaths> currentRuntimePaths();
}
