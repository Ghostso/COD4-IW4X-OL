#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "SharedRoomControl.hpp"
#include "SharedRoomSessionOwner.hpp"
#include "../shared/DedicatedControl.hpp"

#include <atomic>
#include <iostream>
#include <string>

namespace
{
    std::atomic_bool Running{ true };

    BOOL WINAPI onConsoleControl(const DWORD event)
    {
        if (event != CTRL_C_EVENT && event != CTRL_BREAK_EVENT &&
            event != CTRL_CLOSE_EVENT)
        {
            return FALSE;
        }
        Running.store(false);
        return TRUE;
    }
}

int main()
{
    AlwaysofflineRe::SharedRoomSessionOwner owner;
    AlwaysofflineRe::SharedRoomControl::Handler handler(owner);
    OlMod::DedicatedControl::Server server;
    const auto port = AlwaysofflineRe::SharedRoomControl::configuredPort();
    const auto bind = OlMod::DedicatedControl::hostIsRemote()
        ? std::string("0.0.0.0")
        : std::string(OlMod::DedicatedControl::DefaultHostAddress);
    if (!server.start(port, [&handler](const auto &message) {
            return handler(message);
        }))
    {
        std::cerr << "Failed to start shared room owner on " << bind << ':'
                  << port << " error=" << server.lastSocketError() << '\n';
        return 1;
    }
    SetConsoleCtrlHandler(onConsoleControl, TRUE);
    std::cout << "OL-Mod shared room owner listening on " << bind << ':'
              << server.port() << " host="
              << OlMod::DedicatedControl::configuredHostAddress() << '\n';
    while (Running.load())
        Sleep(100);
    server.stop();
    return 0;
}
