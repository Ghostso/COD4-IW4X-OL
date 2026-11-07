#include "sv_script_source_mp.hpp"

#include <lua.hpp>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iterator>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::size_t MapMetadataMaximumMemoryBytes = 512 * 1024;
        constexpr std::uint64_t MapMetadataMaximumInstructions = 100'000;
        constexpr int MapMetadataInstructionHookInterval = 1'000;

        struct MapMetadataLuaLimits
        {
            std::size_t usedBytes{};
            std::uint64_t remainingInstructions{
                MapMetadataMaximumInstructions };
        };

        void *allocateMapMetadataLua(
            void *userData,
            void *pointer,
            const std::size_t oldSize,
            const std::size_t newSize)
        {
            auto &limits = *static_cast<MapMetadataLuaLimits *>(userData);
            const auto accountedOldSize = pointer ? oldSize : 0;
            if (!newSize)
            {
                std::free(pointer);
                limits.usedBytes -= std::min(
                    limits.usedBytes, accountedOldSize);
                return nullptr;
            }
            if (newSize > accountedOldSize &&
                newSize - accountedOldSize >
                    MapMetadataMaximumMemoryBytes - std::min(
                        MapMetadataMaximumMemoryBytes, limits.usedBytes))
            {
                return nullptr;
            }
            auto *resized = std::realloc(pointer, newSize);
            if (!resized)
                return nullptr;
            limits.usedBytes = limits.usedBytes -
                std::min(limits.usedBytes, accountedOldSize) + newSize;
            return resized;
        }

        void mapMetadataInstructionHook(lua_State *state, lua_Debug *)
        {
            auto *limits = *static_cast<MapMetadataLuaLimits **>(
                lua_getextraspace(state));
            if (!limits ||
                limits->remainingInstructions <=
                    MapMetadataInstructionHookInterval)
            {
                if (limits)
                    limits->remainingInstructions = 0;
                static_cast<void>(luaL_error(
                    state, "map metadata instruction budget exceeded"));
                return;
            }
            limits->remainingInstructions -=
                MapMetadataInstructionHookInterval;
        }

        std::optional<std::string> readSourceFile(
            const std::filesystem::path &path,
            const std::size_t maximumSourceBytes)
        {
            std::error_code error;
            if (!std::filesystem::is_regular_file(path, error) || error)
                return std::nullopt;
            const auto size = std::filesystem::file_size(path, error);
            if (error || size > maximumSourceBytes)
                return std::nullopt;
            std::ifstream stream(path, std::ios::binary);
            if (!stream)
                return std::nullopt;
            std::string source{
                std::istreambuf_iterator<char>(stream),
                std::istreambuf_iterator<char>() };
            return !stream.bad() && source.size() == size
                ? std::optional{ std::move(source) }
                : std::nullopt;
        }
    }

    std::string_view SV_GameplaySourceLoadErrorName(
        const SvGameplaySourceLoadError error)
    {
        switch (error)
        {
        case SvGameplaySourceLoadError::None: return "none";
        case SvGameplaySourceLoadError::InvalidSelection: return "invalid_selection";
        case SvGameplaySourceLoadError::NoSource: return "no_source";
        case SvGameplaySourceLoadError::ReadFailed: return "read_failed";
        case SvGameplaySourceLoadError::SourceTooLarge: return "source_too_large";
        }
        return "unknown";
    }

    bool SvGameplaySourceLoadResult::succeeded() const
    {
        return error == SvGameplaySourceLoadError::None;
    }

    bool SV_IsValidGameplaySourceSelection(const std::string_view value)
    {
        return !value.empty() && value.size() <= 64 &&
            std::ranges::all_of(value, [](const unsigned char character) {
                return character == '_' || character == '-' ||
                    character >= '0' && character <= '9' ||
                    character >= 'A' && character <= 'Z' ||
                    character >= 'a' && character <= 'z';
            });
    }

    SvGameplaySourceLoadResult SV_LoadGameplaySource(
        const std::filesystem::path &scriptRoot,
        const std::string_view mapName,
        const std::string_view gameType,
        const std::size_t maximumSourceBytes)
    {
        if (!maximumSourceBytes ||
            !SV_IsValidGameplaySourceSelection(mapName) ||
            !SV_IsValidGameplaySourceSelection(gameType))
        {
            return {
                .error = SvGameplaySourceLoadError::InvalidSelection,
                .detail = "map or gametype name is invalid",
            };
        }

        const std::array candidates{
            scriptRoot / "common.lua",
            scriptRoot / "gametypes" / (std::string(gameType) + ".lua"),
            scriptRoot / "maps" / (std::string(mapName) + ".lua"),
        };
        SvGameplaySource result;
        result.sourceName = "gametype/" + std::string(gameType) + "/map/" +
            std::string(mapName);
        for (const auto &path : candidates)
        {
            std::error_code error;
            if (!std::filesystem::exists(path, error))
            {
                if (error)
                {
                    return {
                        .error = SvGameplaySourceLoadError::ReadFailed,
                        .detail = path.string(),
                    };
                }
                continue;
            }
            if (!std::filesystem::is_regular_file(path, error) || error)
            {
                return {
                    .error = SvGameplaySourceLoadError::ReadFailed,
                    .detail = path.string(),
                };
            }
            const auto fileSize = std::filesystem::file_size(path, error);
            if (error || fileSize > maximumSourceBytes ||
                result.source.size() > maximumSourceBytes - fileSize)
            {
                return {
                    .error = SvGameplaySourceLoadError::SourceTooLarge,
                    .detail = path.string(),
                };
            }
            std::ifstream stream(path, std::ios::binary);
            if (!stream)
            {
                return {
                    .error = SvGameplaySourceLoadError::ReadFailed,
                    .detail = path.string(),
                };
            }
            std::string source{
                std::istreambuf_iterator<char>(stream),
                std::istreambuf_iterator<char>() };
            if (stream.bad() || source.size() != fileSize)
            {
                return {
                    .error = SvGameplaySourceLoadError::ReadFailed,
                    .detail = path.string(),
                };
            }
            const auto relative = path.lexically_relative(scriptRoot).generic_string();
            const std::string prefix = "-- source: " + relative + "\ndo\n";
            constexpr std::string_view suffix = "\nend\n";
            const auto remaining = maximumSourceBytes - result.source.size();
            if (prefix.size() > remaining ||
                source.size() > remaining - prefix.size() ||
                suffix.size() > remaining - prefix.size() - source.size())
            {
                return {
                    .error = SvGameplaySourceLoadError::SourceTooLarge,
                    .detail = path.string(),
                };
            }
            result.source.append(prefix);
            result.source.append(source);
            result.source.append(suffix);
            result.files.push_back(relative);
        }
        if (result.files.empty())
        {
            return {
                .error = SvGameplaySourceLoadError::NoSource,
                .detail = scriptRoot.string(),
            };
        }
        return {
            .gameplaySource = std::move(result),
        };
    }

    std::optional<SvMapScriptMetadata> SV_LoadMapScriptMetadata(
        const std::filesystem::path &scriptRoot,
        const std::string_view mapName,
        const std::size_t maximumSourceBytes)
    {
        if (!maximumSourceBytes || !SV_IsValidGameplaySourceSelection(mapName))
            return std::nullopt;
        const auto path = scriptRoot / "maps" /
            (std::string(mapName) + ".lua");
        const auto source = readSourceFile(path, maximumSourceBytes);
        if (!source)
            return std::nullopt;

        MapMetadataLuaLimits limits;
        auto *state = lua_newstate(allocateMapMetadataLua, &limits);
        if (!state)
            return std::nullopt;
        *static_cast<MapMetadataLuaLimits **>(lua_getextraspace(state)) =
            &limits;
        lua_sethook(
            state,
            mapMetadataInstructionHook,
            LUA_MASKCOUNT,
            MapMetadataInstructionHookInterval);
        const auto close = [&state]() {
            lua_close(state);
            state = nullptr;
        };
        const auto chunkName = "@" + path.generic_string();
        if (luaL_loadbufferx(
                state, source->data(), source->size(), chunkName.c_str(), "t") !=
                LUA_OK || lua_pcall(state, 0, 1, 0) != LUA_OK ||
            !lua_istable(state, -1))
        {
            close();
            return std::nullopt;
        }

        SvMapScriptMetadata result;
        lua_getfield(state, -1, "minimap_material");
        if (!lua_isnil(state, -1))
        {
            std::size_t length{};
            const auto *material = lua_type(state, -1) == LUA_TSTRING
                ? lua_tolstring(state, -1, &length)
                : nullptr;
            if (!material || !length || length > 255 ||
                std::string_view(material, length).find_first_of("\"\\") !=
                    std::string_view::npos ||
                std::string_view(material, length).find('\0') !=
                    std::string_view::npos)
            {
                close();
                return std::nullopt;
            }
            result.miniMapMaterial.emplace(material, length);
        }
        close();
        return result;
    }
}
