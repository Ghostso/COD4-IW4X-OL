#pragma once

#include "sv_script_builtin_mp.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    enum class SvLuaLogLevel : std::uint8_t
    {
        Info,
        Error,
    };

    enum class SvLuaLogKind : std::uint8_t
    {
        Print,
        CompileError,
        RuntimeError,
        HostError,
    };

    struct SvLuaLogEntry
    {
        SvLuaLogLevel level{};
        SvLuaLogKind kind{};
        std::uint64_t generation{};
        std::string sourceName;
        std::string message;
        std::string traceback;
    };

    struct SvLuaRuntimeStatus
    {
        std::uint64_t generation{};
        bool loaded{};
        std::string sourceName;
        std::size_t scheduledThreadCount{};

        bool operator==(const SvLuaRuntimeStatus &) const = default;
    };

    struct SvLuaRuntimeLimits
    {
        std::size_t maximumMemoryBytes{ 8 * 1024 * 1024 };
        std::uint64_t maximumInstructionsPerRun{ 1'000'000 };
        std::uint32_t instructionHookInterval{ 1'000 };
        std::size_t maximumSourceBytes{ 1024 * 1024 };
        std::size_t maximumScheduledThreads{ 256 };
        std::size_t maximumThreadResumesPerFrame{ 64 };
    };

    class SvLuaRuntime
    {
    public:
        explicit SvLuaRuntime(
            const SvScriptBuiltinRegistry &builtins,
            SvLuaRuntimeLimits limits = {});
        ~SvLuaRuntime();

        SvLuaRuntime(const SvLuaRuntime &) = delete;
        SvLuaRuntime &operator=(const SvLuaRuntime &) = delete;
        SvLuaRuntime(SvLuaRuntime &&) = delete;
        SvLuaRuntime &operator=(SvLuaRuntime &&) = delete;

        [[nodiscard]] bool reload(
            std::string_view sourceName,
            std::string_view source);
        [[nodiscard]] bool dispatchWorldEvents(
            std::span<const SvWorldEvent> events);
        [[nodiscard]] bool dispatchTouchNotifications(
            const SvClientImpactScriptNotificationBatch &notifications);
        [[nodiscard]] bool advance(std::uint32_t serverTime);
        void reset();

        [[nodiscard]] SvLuaRuntimeStatus status() const;
        [[nodiscard]] std::vector<SvLuaLogEntry> takeLogs();

    private:
        struct Impl;
        std::unique_ptr<Impl> impl_;
    };
}
