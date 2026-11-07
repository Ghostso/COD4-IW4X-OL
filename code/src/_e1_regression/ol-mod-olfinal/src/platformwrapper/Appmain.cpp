#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "Hooks.hpp"
#include "Tencent.hpp"

#include <cstdint>
#include <filesystem>

namespace
{
    HMODULE Module;
}

extern "C" __declspec(dllexport) void __cdecl onStartup(bool)
{
    std::wstring modulePath(32768, L'\0');
    const auto length = GetModuleFileNameW(
        Module, modulePath.data(), static_cast<DWORD>(modulePath.size()));
    if (!length || length == modulePath.size())
        return;
    modulePath.resize(length);

    const auto paths = OlMod::Platformwrapper::runtimePathsFromModule(modulePath);
    std::error_code error;
    std::filesystem::create_directories(paths.assets, error);
    OlMod::Platformwrapper::setRuntimePaths(paths);
    if (!OlMod::Platformwrapper::installCodolHooks(paths))
        return;
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
        Module = module;
        DisableThreadLibraryCalls(module);
    }
    return TRUE;
}
