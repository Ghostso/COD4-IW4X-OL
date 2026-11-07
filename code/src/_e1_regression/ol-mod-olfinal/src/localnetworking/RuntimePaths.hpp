#pragma once

#include <filesystem>
#include <string_view>

namespace OlMod::Localnetworking
{
    struct RuntimePaths
    {
        std::filesystem::path root;
        std::filesystem::path plugins;
        std::filesystem::path logs;
        std::filesystem::path assets;
    };

    [[nodiscard]] RuntimePaths runtimePathsFromModule(
        const std::filesystem::path &modulePath);
    [[nodiscard]] bool isLocalnetPluginFilename(std::wstring_view filename);
}
