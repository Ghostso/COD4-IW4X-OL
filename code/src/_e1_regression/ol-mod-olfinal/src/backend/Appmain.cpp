#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "Servers.hpp"
#include "Demonware/CodolClientPatches.hpp"
#include "../shared/ProcessRole.hpp"

#include <exception>
#include <mutex>
#include <string>

namespace
{
    AlwaysofflineRe::ServerFactory Factory;
    bool StartupPatchesInstalled = true;
}

extern "C" __declspec(dllexport) IServer *__cdecl Createserver(const char *hostname)
{
    if (!hostname || !OlMod::runsBackend(OlMod::processRole()))
        return nullptr;

    if (!StartupPatchesInstalled)
    {
        static std::once_flag warning;
        std::call_once(warning, [] {
            AlwaysofflineRe::log("Refused to apply CODOL startup patches to an unknown executable image.");
        });
    }

    try
    {
        auto *server = Factory.create(hostname);
        if (server)
        {
            AlwaysofflineRe::log(
                std::string("Claimed ") + hostname + " as " +
                AlwaysofflineRe::serverKindName(AlwaysofflineRe::classifyHostname(hostname)) + '.');
        }
        return server;
    }
    catch (const std::exception &error)
    {
        AlwaysofflineRe::log(std::string("Createserver failed: ") + error.what());
        return nullptr;
    }
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl CODOL_RequestProfileReload(
    const std::uint32_t profileKind)
{
    return AlwaysofflineRe::Demonware::requestCodolProfileReload(profileKind);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GetProfileReloadStatus(
    const std::uint32_t profileKind,
    std::uint32_t *generation,
    std::uint32_t *state,
    std::uint32_t *errorCode)
{
    if (!generation || !state || !errorCode)
        return false;
    return AlwaysofflineRe::Demonware::getCodolProfileReloadStatus(
        profileKind, *generation, *state, *errorCode);
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl CODOL_RequestInventoryRefresh()
{
    return AlwaysofflineRe::Demonware::requestCodolInventoryRefresh();
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GetInventoryRefreshStatus(
    std::uint32_t *generation,
    std::uint32_t *state,
    std::uint32_t *errorCode)
{
    if (!generation || !state || !errorCode)
        return false;
    return AlwaysofflineRe::Demonware::getCodolInventoryRefreshStatus(
        *generation, *state, *errorCode);
}

BOOL WINAPI DllMain(const HINSTANCE module, const DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(module);
        if (OlMod::runsBackend(OlMod::processRole()))
        {
            StartupPatchesInstalled =
                AlwaysofflineRe::Demonware::installCodolStartupPatches();
        }
    }
    return TRUE;
}
