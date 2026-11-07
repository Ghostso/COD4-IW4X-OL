#pragma once

#include <cstdint>
#include <filesystem>
#include <string>

namespace OlMod::Platformwrapper
{
    struct PlatformConfig
    {
        std::uint32_t titleId{1004};
        std::uint32_t gameVersion{42};
        std::uint32_t zoneId{83886082};
        std::uint32_t serverId{1};
        std::uint64_t platformUserId{0x01100001DEADC0DEull};
        std::string authEndpoint{"auth3.qq.com:3074"};
        std::string lobbyEndpoint{"lsg.qq.com:3074"};
    };

    struct RuntimePaths
    {
        std::filesystem::path ayriaRoot;
        std::filesystem::path gameRoot;
        std::filesystem::path assets;
        std::filesystem::path config;
    };

    [[nodiscard]] RuntimePaths runtimePathsFromModule(
        const std::filesystem::path &modulePath);
    [[nodiscard]] PlatformConfig loadPlatformConfig(const RuntimePaths &paths);
    [[nodiscard]] std::string platformIdString(std::uint64_t platformUserId);
    [[nodiscard]] std::string authenticationDescriptor(const PlatformConfig &config);
}
