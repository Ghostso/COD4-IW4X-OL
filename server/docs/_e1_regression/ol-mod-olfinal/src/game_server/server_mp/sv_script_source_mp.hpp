#pragma once

#include <cstddef>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    enum class SvGameplaySourceLoadError
    {
        None,
        InvalidSelection,
        NoSource,
        ReadFailed,
        SourceTooLarge,
    };

    struct SvGameplaySource
    {
        std::string sourceName;
        std::string source;
        std::vector<std::string> files;
    };

    struct SvGameplaySourceLoadResult
    {
        SvGameplaySourceLoadError error{};
        SvGameplaySource gameplaySource;
        std::string detail;

        [[nodiscard]] bool succeeded() const;
    };

    struct SvMapScriptMetadata
    {
        std::optional<std::string> miniMapMaterial;

        bool operator==(const SvMapScriptMetadata &) const = default;
    };

    [[nodiscard]] std::string_view SV_GameplaySourceLoadErrorName(
        SvGameplaySourceLoadError error);
    [[nodiscard]] bool SV_IsValidGameplaySourceSelection(
        std::string_view value);
    [[nodiscard]] SvGameplaySourceLoadResult SV_LoadGameplaySource(
        const std::filesystem::path &scriptRoot,
        std::string_view mapName,
        std::string_view gameType,
        std::size_t maximumSourceBytes = 1024 * 1024);
    [[nodiscard]] std::optional<SvMapScriptMetadata> SV_LoadMapScriptMetadata(
        const std::filesystem::path &scriptRoot,
        std::string_view mapName,
        // Metadata execution has separate allocator and instruction limits,
        // but campaign map chunks also carry measured movement tables. Match
        // the gameplay source-size ceiling so those maps reach their early
        // metadata return instead of failing the file-size precheck.
        std::size_t maximumSourceBytes = 1024 * 1024);
}
