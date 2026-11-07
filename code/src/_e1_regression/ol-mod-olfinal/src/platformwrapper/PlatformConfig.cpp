#include "PlatformConfig.hpp"

#include <nlohmann/json.hpp>

#include <charconv>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <system_error>

namespace
{
    using json = nlohmann::json;

    std::string readText(const std::filesystem::path &path)
    {
        std::ifstream stream(path, std::ios::binary);
        if (!stream)
            return {};
        return {std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
    }

    void trim(std::string &value)
    {
        const auto first = value.find_first_not_of(" \t\r\n");
        if (first == std::string::npos)
        {
            value.clear();
            return;
        }
        const auto last = value.find_last_not_of(" \t\r\n");
        value = value.substr(first, last - first + 1);
    }

    bool parsePlatformId(std::string value, std::uint64_t &result)
    {
        trim(value);
        if (value.starts_with("0x") || value.starts_with("0X"))
            value.erase(0, 2);
        if (value.empty())
            return false;

        std::uint64_t parsed{};
        const auto conversion = std::from_chars(
            value.data(), value.data() + value.size(), parsed, 16);
        if (conversion.ec != std::errc{} || conversion.ptr != value.data() + value.size())
            return false;

        // The archived file stores the low account ID. A full platform ID is also accepted.
        result = parsed <= 0xFFFFFFFFull ? 0x0110000100000000ull | parsed : parsed;
        return true;
    }

    template <typename T>
    void assignInteger(const json &document, const char *key, T &target)
    {
        const auto iterator = document.find(key);
        if (iterator != document.end() && iterator->is_number_unsigned())
            target = iterator->get<T>();
    }

    void assignString(const json &document, const char *key, std::string &target)
    {
        const auto iterator = document.find(key);
        if (iterator != document.end() && iterator->is_string() && !iterator->get_ref<const std::string &>().empty())
            target = iterator->get<std::string>();
    }
}

namespace OlMod::Platformwrapper
{
    RuntimePaths runtimePathsFromModule(const std::filesystem::path &modulePath)
    {
        const auto plugins = modulePath.parent_path().lexically_normal();
        const auto ayriaRoot = plugins.parent_path().lexically_normal();
        return RuntimePaths{
            ayriaRoot,
            ayriaRoot.parent_path().lexically_normal(),
            ayriaRoot / L"Assets" / L"Platformwrapper",
            ayriaRoot / L"Assets" / L"Platformwrapper" / L"Platform.json",
        };
    }

    PlatformConfig loadPlatformConfig(const RuntimePaths &paths)
    {
        PlatformConfig config;
        // Read the archived account-ID file first. Platform.json is the canonical
        // source and may intentionally replace this migration value.
        const auto legacyUserId = readText(paths.assets / L"UserID.txt");
        if (!legacyUserId.empty())
            parsePlatformId(legacyUserId, config.platformUserId);

        const auto contents = readText(paths.config);
        if (!contents.empty())
        {
            const auto document = json::parse(contents, nullptr, false);
            if (document.is_object() && document.value("schemaVersion", 0u) == 1u)
            {
                assignInteger(document, "titleId", config.titleId);
                assignInteger(document, "gameVersion", config.gameVersion);
                assignInteger(document, "zoneId", config.zoneId);
                assignInteger(document, "serverId", config.serverId);
                assignString(document, "authEndpoint", config.authEndpoint);
                assignString(document, "lobbyEndpoint", config.lobbyEndpoint);
                if (const auto iterator = document.find("platformUserId");
                    iterator != document.end() && iterator->is_string())
                {
                    parsePlatformId(iterator->get<std::string>(), config.platformUserId);
                }
            }
        }

        // A launcher-owned process override lets multiple local clients use
        // independent platform identities without rewriting shared assets.
        char *processUserId{};
        std::size_t processUserIdSize{};
        if (_dupenv_s(
                &processUserId,
                &processUserIdSize,
                "OLMOD_PLATFORM_USER_ID") == 0 &&
            processUserId)
        {
            std::uint64_t parsed{};
            if (parsePlatformId(processUserId, parsed))
                config.platformUserId = parsed;
            std::free(processUserId);
        }

        return config;
    }

    std::string platformIdString(const std::uint64_t platformUserId)
    {
        std::ostringstream stream;
        stream << std::uppercase << std::hex << std::setw(16) << std::setfill('0')
               << platformUserId;
        return stream.str();
    }

    std::string authenticationDescriptor(const PlatformConfig &config)
    {
        return config.authEndpoint + ';' + config.lobbyEndpoint + ';' +
            std::to_string(config.titleId);
    }
}
