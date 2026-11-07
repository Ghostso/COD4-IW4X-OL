#pragma once

namespace CodolGameServer
{
    // THE NOCLIP HOTKEY, CLIENT SIDE. Starts one detached thread that watches a
    // single key and tells the dedicated when it goes down and comes up. Safe to
    // call more than once; only the first call starts anything.
    //
    // A THREAD, NOT A FRAME HOOK. `never-hook-a-per-frame-function-in-the-client`
    // was written after a per-frame client hook killed three clients at once, and
    // nothing here needs frame accuracy: a key held by a human lasts hundreds of
    // milliseconds and 30 Hz resolves it with room to spare.
    void startClientNoclipHotkey();
    // Default-off local test aid; F6 (configurable), Apostrophe/Numpad+ add one
    // battery to the focused player without altering score.
    void startClientBatteryHotkey();
}
