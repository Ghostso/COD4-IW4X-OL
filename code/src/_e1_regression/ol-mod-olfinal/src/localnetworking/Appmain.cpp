#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "Localnetworking.hpp"

#include <filesystem>

extern "C" __declspec(dllexport) void __cdecl onStartup(bool)
{
    const auto paths = OlMod::Localnetworking::currentRuntimePaths();
    if (!paths)
        return;

    std::error_code error;
    std::filesystem::create_directories(paths->logs, error);
    std::filesystem::create_directories(paths->assets, error);
    std::filesystem::create_directories(paths->plugins, error);

    auto &bridge = OlMod::Localnetworking::Bridge::instance();
    if (!bridge.start(*paths))
        return;
    if (!OlMod::Localnetworking::installWinsockHooks())
        bridge.log("Failed to install one or more Winsock hooks.");
}

extern "C" __declspec(dllexport) void __cdecl onInitialized(bool)
{
}

extern "C" __declspec(dllexport) bool __cdecl onMessage(const void *, std::uint32_t)
{
    return false;
}

BOOL WINAPI DllMain(const HINSTANCE module, const DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        OlMod::Localnetworking::setModuleHandle(module);
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
