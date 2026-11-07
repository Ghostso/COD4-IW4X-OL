#include "IdentityConfig.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <nlohmann/json.hpp>

#include <array>
#include <charconv>
#include <fstream>
#include <stdexcept>
#include <system_error>

namespace
{
    using Json = nlohmann::json;

    void validateDisplayName(const std::string_view displayName)
    {
        if (displayName.empty() || displayName.size() > 16)
            throw std::runtime_error("display name must contain 1 to 16 bytes");
        for (const auto character : displayName)
        {
            const auto byte = static_cast<unsigned char>(character);
            if (byte < 0x20 || byte > 0x7E)
                throw std::runtime_error("display name must contain printable ASCII only");
        }
    }

    std::string userIdDirectory(const std::uint64_t userId)
    {
        std::array<char, 16> buffer{};
        const auto result = std::to_chars(
            buffer.data(), buffer.data() + buffer.size(), userId, 16);
        if (result.ec != std::errc{})
            throw std::runtime_error("could not encode player user ID");
        std::string value(buffer.data(), result.ptr);
        for (auto &character : value)
        {
            if (character >= 'a' && character <= 'f')
                character = static_cast<char>(character - 'a' + 'A');
        }
        return value;
    }

    std::string loadDisplayName(const std::filesystem::path &path)
    {
        std::ifstream input(path);
        if (!input)
            throw std::runtime_error("could not open player identity profile");
        const auto document = Json::parse(input, nullptr, false);
        if (!document.is_object() ||
            document.value("schemaVersion", 0) != 1 ||
            !document.contains("displayName") ||
            !document["displayName"].is_string())
        {
            throw std::runtime_error(
                "player identity profile must use schemaVersion 1 and contain a string displayName");
        }
        auto displayName = document["displayName"].get<std::string>();
        validateDisplayName(displayName);
        return displayName;
    }

    void saveDisplayName(
        const std::filesystem::path &path,
        const std::string_view displayName)
    {
        validateDisplayName(displayName);
        std::error_code error;
        std::filesystem::create_directories(path.parent_path(), error);
        if (error)
            throw std::system_error(error, "could not create player identity directory");

        auto temporary = path;
        temporary += L".writing";
        {
            std::ofstream output(temporary, std::ios::trunc);
            if (!output)
                throw std::runtime_error("could not create player identity profile");
            output << Json{
                { "schemaVersion", 1 },
                { "displayName", displayName },
            }.dump(2) << '\n';
            if (!output)
            {
                output.close();
                std::filesystem::remove(temporary, error);
                throw std::runtime_error("could not write player identity profile");
            }
        }
        if (!MoveFileExW(
                temporary.c_str(), path.c_str(),
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        {
            const auto nativeError = GetLastError();
            std::filesystem::remove(temporary, error);
            throw std::system_error(
                static_cast<int>(nativeError), std::system_category(),
                "could not commit player identity profile");
        }
    }
}

namespace AlwaysofflineRe::Demonware
{
    std::string loadConfiguredUsername(const std::filesystem::path &path)
    {
        std::ifstream input(path);
        if (!input)
            return std::string(DefaultUsername);

        const auto document = nlohmann::json::parse(input, nullptr, false);
        if (!document.is_object() || !document.contains("username") || !document["username"].is_string())
            throw std::runtime_error("identity config must contain a string username");

        auto username = document["username"].get<std::string>();
        validateDisplayName(username);
        return username;
    }

    PlayerIdentityStore::PlayerIdentityStore(
        std::filesystem::path assetRoot,
        std::filesystem::path migrationSeed)
        : assetRoot_(std::move(assetRoot)),
          migrationSeed_(std::move(migrationSeed))
    {
    }

    std::string PlayerIdentityStore::resolveDisplayName(
        const std::uint32_t titleId,
        const std::uint64_t userId)
    {
        if (!titleId || !userId)
            throw std::runtime_error("player identity requires a title and user ID");
        std::scoped_lock lock(mutex_);
        const auto path = identityPath(titleId, userId);
        std::error_code error;
        const auto status = std::filesystem::status(path, error);
        if (error == std::errc::no_such_file_or_directory)
            error.clear();
        else if (error)
            throw std::system_error(error, "could not inspect player identity profile");
        if (std::filesystem::is_regular_file(status))
            return loadDisplayName(path);
        if (std::filesystem::exists(status))
            throw std::runtime_error("player identity profile path is not a regular file");

        const auto displayName = loadConfiguredUsername(migrationSeed_);
        saveDisplayName(path, displayName);
        return displayName;
    }

    void PlayerIdentityStore::setDisplayName(
        const std::uint32_t titleId,
        const std::uint64_t userId,
        const std::string_view displayName)
    {
        if (!titleId || !userId)
            throw std::runtime_error("player identity requires a title and user ID");
        std::scoped_lock lock(mutex_);
        saveDisplayName(identityPath(titleId, userId), displayName);
    }

    std::filesystem::path PlayerIdentityStore::identityPath(
        const std::uint32_t titleId,
        const std::uint64_t userId) const
    {
        return assetRoot_ / std::to_string(titleId) /
            userIdDirectory(userId) / L"Identity.json";
    }
}
