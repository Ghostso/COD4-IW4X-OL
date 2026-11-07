#pragma once

#include <string_view>

namespace OlMod::RuntimeLog
{
    enum class Channel
    {
        Backend,
        GameServer,
    };

    [[nodiscard]] bool consoleEnabled();
    void write(Channel channel, std::string_view message);

    /// Whether the per-frame diagnostics should be emitted. OFF unless OLMOD_VERBOSE_LOG is set.
    ///
    /// They report values that change every frame -- an interpolation fraction, a command
    /// sequence, a sampled bone height -- so the change-detectors guarding them can never
    /// throttle anything, and they held the steady-state log at ~180 lines a second. Answered
    /// once and cached; the environment cannot change inside a process.
    [[nodiscard]] bool verbose();
}
