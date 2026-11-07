#pragma once

#include <cstdint>
#include <filesystem>
#include <mutex>
#include <string>
#include <string_view>

namespace AlwaysofflineRe::Demonware
{
    inline constexpr std::string_view DefaultUsername = "Alwaysoffline";

    [[nodiscard]] std::string loadConfiguredUsername(
        const std::filesystem::path &path = L"./Ayria/Assets/Alwaysoffline/Identity.json");

    class PlayerIdentityStore
    {
    public:
        explicit PlayerIdentityStore(
            std::filesystem::path assetRoot = L"./Ayria/Assets/Alwaysoffline",
            std::filesystem::path migrationSeed =
                L"./Ayria/Assets/Alwaysoffline/Identity.json");

        [[nodiscard]] std::string resolveDisplayName(
            std::uint32_t titleId,
            std::uint64_t userId);
        void setDisplayName(
            std::uint32_t titleId,
            std::uint64_t userId,
            std::string_view displayName);
        [[nodiscard]] std::filesystem::path identityPath(
            std::uint32_t titleId,
            std::uint64_t userId) const;

    private:
        std::filesystem::path assetRoot_;
        std::filesystem::path migrationSeed_;
        std::mutex mutex_;
    };
}
