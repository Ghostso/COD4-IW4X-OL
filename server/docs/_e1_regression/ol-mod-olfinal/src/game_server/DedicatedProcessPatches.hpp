#pragma once

#include <cstdint>
#include <optional>
#include <span>

namespace CodolGameServer
{
    enum class DedicatedProcessPatchResult
    {
        Patched,
        AlreadyPatched,
        UnsupportedHost,
        UnexpectedBytes,
        UnexpectedSingleInstanceBytes,
        UnexpectedClientFrameBytes,
        UnexpectedFrontendStartupBytes,
        UnexpectedFocusStartupBytes,
        UnexpectedAccessibilityStartupBytes,
        UnexpectedCursorVisibilityBytes,
        UnexpectedInputFrameStartupBytes,
        UnexpectedAudioStartupBytes,
        ProtectionFailed,
    };

    // Exposed for deterministic tests. Runtime installation additionally
    // validates the CODOL PE timestamp and image size before changing memory.
    bool patchDedicatedSingleInstanceBuffer(std::span<std::uint8_t> image);
    bool patchClientInstanceSingleInstanceBuffer(
        std::span<std::uint8_t> image,
        std::uint32_t instance);
    bool installClientInstanceSingleInstancePatch(std::uint32_t instance);
    [[nodiscard]] std::optional<std::uint32_t>
        configuredClientInstance();
    bool patchDedicatedClientFrameBuffer(std::span<std::uint8_t> image);
    bool patchDedicatedFrontendStartupBuffer(std::span<std::uint8_t> image);
    bool patchDedicatedFocusStartupBuffer(std::span<std::uint8_t> image);
    bool patchDedicatedAccessibilityStartupBuffer(
        std::span<std::uint8_t> image);
    bool patchDedicatedCursorVisibilityBuffer(std::span<std::uint8_t> image);
    bool patchDedicatedInputFrameStartupBuffer(std::span<std::uint8_t> image);
    bool patchDedicatedAudioStartupBuffer(std::span<std::uint8_t> image);
    DedicatedProcessPatchResult patchDedicatedProcessBuffer(
        std::span<std::uint8_t> image);
    DedicatedProcessPatchResult installDedicatedProcessPatches();
    const char *dedicatedProcessPatchResultName(DedicatedProcessPatchResult result);
}
