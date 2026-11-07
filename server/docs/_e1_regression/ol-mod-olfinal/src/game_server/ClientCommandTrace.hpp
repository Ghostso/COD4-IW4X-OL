#pragma once

#include <string>

#include "EngineBindings.hpp"

namespace CodolGameServer
{
    /// WATCH EVERY RELIABLE COMMAND THE CLIENT DISPATCHES, AS IT DISPATCHES IT.
    ///
    /// Theatre playback runs the real client code path in out.exe -- the same parse, the same
    /// dispatch, the same handlers as a live match -- so a hook here observes retail server
    /// output being consumed by the retail client, for a demo we also decode offline. That is
    /// the one thing the wire alone cannot give: what the client DOES with each verb.
    ///
    /// THE TARGET IS sub_614C00 (RVA 0x214C00) AND NOT THE 126-CASE SWITCH BELOW IT. See
    /// re/demo-re/23-client-command-dispatch.md: the vocabulary has THREE dispatch sites --
    /// sub_613A40's switch, sub_614AC0 for '!' sub-frames, and sub_614C00 itself for the
    /// disconnect paths. sub_614C00 is the only one that sees all of them, before the split.
    ///
    /// RATE IS THE SAFETY ARGUMENT, and it is measured rather than assumed. The retail dm demo
    /// carries 1478 reliable commands across 621 s -- about 2.4/s. A Frida hook on the PER-FRAME
    /// sub_54FDA0 crashed all three running clients at once on 2026-08-24 at 100-180 fps; the
    /// two probes that were fine the same day fired only on rare paths. This is the rare kind.
    ///
    /// It is OFF unless asked for, writes to a file, and never touches the dispatch it observes.
    /// Writes Ayria\Logs\client-commands.csv beside the EXECUTABLE. Not a relative path:
    /// weapon-slots.csv was opened relatively once, which works from the client and silently
    /// does nothing from the dedicated, and the audit reported its counts either way.
    bool installClientCommandTrace(const EngineBindings &bindings);

    /// Stop recording and flush. Safe to call when nothing was ever installed.
    void stopClientCommandTrace();

    /// One line for the diagnostic's reply: where it is writing and how many it has seen.
    std::string clientCommandTraceStatus();

    /// MIRROR THE CLIENT'S OWN PLAYERSTATE WHILE IT PLAYS A DEMO, TO Ayria\Logs\client-ps.csv.
    ///
    /// NO HOOK. We are already inside the process, so this is a detached thread reading memory
    /// on a timer -- it cannot perturb the code it observes, which a trampoline always can.
    /// Hooks are for EVENTS; state only ever needed a reader, and the whole
    /// never-hook-a-per-frame-function hazard simply does not apply.
    ///
    /// WHY IT IS WORTH 246 FIELDS. playerstate-0x00DA8540.tsv carries 246 netfields across 15,220
    /// bytes and has never been checked against anything but itself. Theatre playback decodes a
    /// RETAIL demo into that struct with the retail client's own code, and we decode the same
    /// bytes offline -- so every field where the two disagree is either our codec being wrong or
    /// a field we have mis-named, and every field where they agree is verified.
    ///
    /// Emits a row only when a 4-byte word CHANGES, the same rule demoq.py prints on, so the two
    /// sides are directly comparable rather than needing to be aligned first.
    bool installPlayerStateTrace(const EngineBindings &bindings, unsigned intervalMs);

    void stopPlayerStateTrace();

    std::string playerStateTraceStatus();

    /// WHAT com_maxfps IS AND WHAT THE CLIENT ACTUALLY ACHIEVES, MEASURED.
    ///
    /// The dvar is registered at 0x004FC400 with default 200, min 0, MAX 200, so nothing in
    /// the graphics menu can ask for more. Com_Frame's limiter (0x004FE220, whose own
    /// profiler scope is literally "max fps spin") then does
    ///
    ///     if (maxfps > 0) minMsec = 1000 / maxfps;        // INTEGER division: 200 -> 5 ms
    ///     while (timeGetTime() - last < minMsec) Sleep(1);
    ///
    /// and Sleep(1) plus a millisecond-granular clock overshoot 5 ms to about 5.3, which is
    /// the ~186-190 a player sees. Zero SKIPS the limiter entirely -- minMsec stays 1 -- and
    /// zero is inside the dvar's own range, so it is the only route past that ceiling.
    ///
    /// `set` writes the value; sampling always runs. Reports to the game-server log after
    /// `sampleMs`, never on the bridge's request path -- a multi-second measurement returned
    /// synchronously is exactly what stalled a match once.
    bool startFpsProbe(
        const EngineBindings &bindings,
        bool set,
        std::uint32_t value,
        unsigned sampleMs);
}
