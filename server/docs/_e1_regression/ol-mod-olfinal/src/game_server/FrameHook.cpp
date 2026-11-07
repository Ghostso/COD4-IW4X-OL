#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "FrameHook.hpp"

#include <algorithm>
#include <cstdint>

namespace
{
    constexpr std::size_t HookSize = 5;
    void *OriginalComFrame{};
    CodolGameServer::FrameCallback Callback{};

    void __cdecl runServerFrame()
    {
        if (Callback)
            Callback(GetTickCount());
    }

    __declspec(naked) void comFrameHook()
    {
        __asm
        {
            call dword ptr [OriginalComFrame]
            pushfd
            pushad
            call runServerFrame
            popad
            popfd
            ret
        }
    }
}

namespace CodolGameServer
{
    bool installFrameHook(const EngineBindings &bindings, const FrameCallback callback)
    {
        if (!bindings.valid() || !callback || OriginalComFrame)
            return false;

        auto *target = bindings.module() + EngineBindings::ComFrameRva;
        auto *trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr,
            HookSize + 5,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE));
        if (!trampoline)
            return false;

        std::copy_n(target, HookSize, trampoline);
        trampoline[HookSize] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + HookSize + 1) =
            static_cast<std::int32_t>((target + HookSize) - (trampoline + HookSize + 5));

        DWORD oldProtection{};
        if (!VirtualProtect(target, HookSize, PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return false;
        }

        OriginalComFrame = trampoline;
        Callback = callback;
        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&comFrameHook) - (target + 5));
        FlushInstructionCache(GetCurrentProcess(), target, HookSize);
        VirtualProtect(target, HookSize, oldProtection, &oldProtection);
        return true;
    }
}
