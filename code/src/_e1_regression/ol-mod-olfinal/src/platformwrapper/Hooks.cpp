#include "Hooks.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <mhook-lib/mhook.h>

#include <array>
#include <mutex>

extern "C"
{
    void __cdecl Invoke(std::uint32_t gameId, void **interfacePointer);
    void *__cdecl CreateObj(int type);
    int __cdecl InitCrossContextByOpenID(void *context);
}

namespace
{
    struct Hook
    {
        void *trampoline{};
    };

    Hook TencentHook;
    Hook TensafeHook;
    Hook CrossShellHook;

    bool install(HMODULE module, const char *exportName, void *replacement, Hook &hook)
    {
        if (!module)
            return false;
        const auto target = reinterpret_cast<void *>(GetProcAddress(module, exportName));
        if (!target)
            return false;
        if (target == replacement)
            return true;
        hook.trampoline = target;
        return Mhook_SetHook(&hook.trampoline, replacement) != FALSE;
    }

    bool rollback(Hook &hook)
    {
        if (!hook.trampoline)
            return true;
        auto *trampoline = hook.trampoline;
        if (!Mhook_Unhook(&trampoline))
            return false;
        hook.trampoline = nullptr;
        return true;
    }
}

namespace OlMod::Platformwrapper
{
    bool installCodolHooks(const RuntimePaths &paths)
    {
        static std::mutex mutex;
        static bool installed{};
        static bool rollbackFailed{};
        std::lock_guard lock(mutex);
        if (installed)
            return true;
        if (rollbackFailed)
            return false;

        const auto tenProxy = LoadLibraryW((paths.gameRoot / L"TenProxy.dll").c_str());
        const auto terSafe = LoadLibraryW((paths.gameRoot / L"TerSafe.dll").c_str());
        const auto crossShell = LoadLibraryW(
            (paths.gameRoot / L"Cross" / L"CrossShell.dll").c_str());

        const auto success =
            install(tenProxy, "Invoke", reinterpret_cast<void *>(&Invoke), TencentHook) &&
            install(terSafe, "CreateObj", reinterpret_cast<void *>(&CreateObj), TensafeHook) &&
            install(crossShell, "InitCrossContextByOpenID",
                reinterpret_cast<void *>(&InitCrossContextByOpenID), CrossShellHook);
        if (success)
        {
            installed = true;
            return true;
        }

        const auto crossRollback = rollback(CrossShellHook);
        const auto tensafeRollback = rollback(TensafeHook);
        const auto tencentRollback = rollback(TencentHook);
        rollbackFailed = !(crossRollback && tensafeRollback && tencentRollback);
        return false;
    }
}
