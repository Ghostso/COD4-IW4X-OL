#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <TlHelp32.h>

#include "DisconnectWitness.hpp"

#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

// WHO DISCONNECTS THE CLIENT, AND WHY THIS IS A HOOK RATHER THAN MORE READING.
//
// On mp_battlecity the client now reaches cls.state 10 (ACTIVE), acks reliable commands,
// sends button input -- and then zeroes cls.state about a second later. Not a Com_Error
// (`com_errorMessage` stays empty), not a fault (no ClientException), and nothing the
// server sends accounts for it. Six server-side theories died against that one second.
//
// Scanning .text for every write to cls.state (0x076446B0) finds exactly five, and only
// ONE stores 0: the `mov dword ptr [0x076446B0], 0` at 0x0077C343, inside sub_77C290. Its
// three callers fan out to 97 call sites, far too many to narrow by reading, so the
// caller's return address is the answer and a hook is the only way to read it.
//
// OFF UNLESS OLMOD_DISCONNECT_WITNESS=1. It patches the client's own code; not something
// to leave armed by default.

namespace
{
    // THE WRITE ITSELF, NOT THE FUNCTION ENTRY. Two reasons, both measured:
    //
    //  1. Hooking sub_77C290's entry was armed (log: "disconnect witness installed" at
    //     21:09:50) and the client still went cls.state 10 -> 0 at 21:12:08 without the
    //     hook firing. Whatever reaches the write does not come through the prologue.
    //  2. That prologue is `55 8B EC 83 E4 F8` -- push ebp / mov ebp,esp / AND ESP,-8.
    //     A five-byte steal cuts `and esp,-8` in half, so the trampoline would have
    //     executed a truncated instruction. It was wrong even where it did fire.
    //
    // The write is `C7 05 B0 46 64 07 00 00 00 00` at 0x0077C343 -- ten bytes, so a
    // five-byte jump plus five NOPs fits with room to spare and nothing is split.
    // (My earlier scan printed 0x0077C345 because it reported where the ADDRESS OPERAND
    // sits, not where the instruction starts.)
    constexpr std::size_t ClsStateWriteRva = 0x0037C343;
    constexpr std::size_t StolenSize = 10;
    constexpr std::size_t HookSize = 5;
    constexpr std::uint8_t ExpectedWrite[StolenSize] = {
        0xC7, 0x05, 0xB0, 0x46, 0x64, 0x07, 0x00, 0x00, 0x00, 0x00 };

    // AND Com_Error, BECAUSE "NO ERROR" MAY HAVE BEEN A FALSE READ.
    //
    // `com_errorMessage` was empty every time the client left, and that was taken as
    // proof Com_Error never ran. It only proves the MESSAGE was empty -- a Com_Error
    // raised with an empty or unresolved string reads exactly the same from outside, and
    // that would also explain the blank dialog body seen all evening.
    //
    // Com_Error is sub_4F8350 (re/FINAL-BUILD-BRINGUP.md section 6). It opens with
    // `E8 7B F9 FF FF` -- a five-byte RELATIVE call to sub_4F7CD0. Five bytes is a clean
    // steal, but a relative call CANNOT simply be copied to a trampoline at a different
    // address: its target is encoded as a delta. The installer rewrites that delta below.
    constexpr std::size_t ComErrorRva = 0x000F8350;
    constexpr std::size_t ComErrorStolen = 5;
    constexpr std::uint8_t ExpectedComError[ComErrorStolen] = {
        0xE8, 0x7B, 0xF9, 0xFF, 0xFF };

    std::uint8_t *ComErrorTrampoline{};
    volatile long ComErrorReported{};

    void __cdecl recordComError(const std::uint32_t returnAddress)
    {
        if (InterlockedExchange(&ComErrorReported, 1) != 0)
            return;
        auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        const auto base = reinterpret_cast<std::uintptr_t>(module);
        char line[192]{};
        std::snprintf(line, sizeof(line),
            "COM_ERROR raised, called from 0x%08X (module+0x%X) -- resolve with "
            "Tools/olfinal/xrefs.py --callers",
            returnAddress,
            static_cast<unsigned>(returnAddress - base));
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
    }

    __declspec(naked) void comErrorHook()
    {
        __asm
        {
            pushfd
            pushad
            // Entry hook: [esp] held the return address, and pushfd(4) + pushad(32) put
            // it at esp+36.
            mov eax, [esp + 36]
            push eax
            call recordComError
            add esp, 4
            popad
            popfd
            jmp dword ptr [ComErrorTrampoline]
        }
    }

    std::uint8_t *Trampoline{};
    volatile long Reported{};

    // Called from the naked stub with the caller's return address. Logs ONCE: the
    // disconnect can cascade, and the first one is the one that matters.
    void __cdecl recordDisconnect(const std::uint32_t returnAddress)
    {
        if (InterlockedExchange(&Reported, 1) != 0)
            return;
        auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        const auto base = reinterpret_cast<std::uintptr_t>(module);
        char line[192]{};
        std::snprintf(line, sizeof(line),
            "CL_DISCONNECT called from 0x%08X (module+0x%X) -- resolve with "
            "Tools/olfinal/xrefs.py",
            returnAddress,
            static_cast<unsigned>(returnAddress - base));
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
    }



    // THE CONFIGSTRING VALIDATOR, AND ITS ARGUMENT IS THE ANSWER.
    //
    // sub_514540 is what raises XBOXLIVE_CANTJOINSESSION as ERR_SERVERDISCONNECT
    // (measured: com_errorCode = 2 written from sub_4F82E0+0x11F, caller frame
    // sub_514540+0xA5). Decoded, it is a per-configstring check:
    //
    //     mov  ebx, [ebp+8]            <- a CONFIGSTRING INDEX
    //     cmp  ebx, 0x31D9             range check, else a different raise at +0x76
    //     mov  al, [ebx + 0x77D8250]   its TYPE byte, in the CCS block
    //     cmp  al, 0x17 / jae ok
    //     cmp  al, 0x15 / je  ok
    //     call sub_661610              the CCS clear
    //     push XBOXLIVE_CANTJOINSESSION / push 2 / raise
    //
    // So it rejects ONE configstring by index. Logging that index names it outright --
    // far better than guessing which band is at fault. The dmz loot band was the obvious
    // suspect and has already been RULED OUT by running with OLMOD_DMZ_LOOT_BAND=0: the
    // kick happened anyway, at 02:50:12.
    //
    // The prologue is `55 8B EC 83 EC 10` -- push ebp / mov ebp,esp / SUB ESP,0x10 -- so
    // six bytes are stolen, not five. Five would cut `sub esp,0x10` in half, the same
    // mistake made on sub_77C290 earlier tonight.
    constexpr std::size_t ValidatorRva = 0x00114540;
    constexpr std::size_t ValidatorStolen = 6;
    constexpr std::uint8_t ExpectedValidator[ValidatorStolen] = {
        0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10 };

    std::uint8_t *ValidatorTrampoline{};
    volatile long ValidatorReported{};

    void __cdecl recordValidator(const std::uint32_t configString,
                                 const std::uint32_t returnAddress)
    {
        // Every call is logged, capped -- the rejected one is not necessarily the first,
        // and knowing which indices PASSED is as useful as the one that failed.
        if (InterlockedIncrement(&ValidatorReported) > 40)
            return;
        auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        const auto base = reinterpret_cast<std::uintptr_t>(module);
        // The type byte it is about to test, read the same way it does.
        std::uint32_t type = 0xFFFFFFFF;
        if (configString < 0x31D9)
        {
            type = *reinterpret_cast<const std::uint8_t *>(
                base + (0x077D8250 - 0x00400000) + configString);
        }
        char line[200]{};
        std::snprintf(line, sizeof(line),
            "CS VALIDATE index=%u typeByte=0x%02X (accepts 0x15 or >=0x17) "
            "from module+0x%X",
            configString, type,
            static_cast<unsigned>(returnAddress - base));
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
    }

    __declspec(naked) void validatorHook()
    {
        __asm
        {
            pushfd
            pushad
            // At entry [esp] is the return address and [esp+4] the first argument; after
            // pushfd(4) + pushad(32) those sit at esp+36 and esp+40.
            mov eax, [esp + 36]
            push eax
            mov eax, [esp + 44]
            push eax
            call recordValidator
            add esp, 8
            popad
            popfd
            jmp dword ptr [ValidatorTrampoline]
        }
    }

    // A HARDWARE WATCHPOINT, BECAUSE BOTH SOFTWARE HOOKS CAME BACK EMPTY.
    //
    // Measured 2026-09-04: the hook on the only `mov dword [cls.state], 0` in the image
    // was armed and never fired; the hook on Com_Error was armed and never fired; there
    // is no ClientException and no match end -- and cls.state still goes 10 -> 0 about a
    // second after the client enters. A value that changes with no instruction touching
    // its address is a value being wiped as part of something larger: a memset over the
    // whole `cls` struct, which references no address a scanner can find.
    //
    // The CPU does not care how the write happens. DR0 + DR7 make it trap on the ADDRESS,
    // so a `rep stosd` inside memset is caught exactly like a `mov`. The exception's
    // address is the instruction AFTER the write, which is enough to name the function.
    //
    // ARMED ON EVERY THREAD IN THE PROCESS. Debug registers are per-thread, and there is
    // no guarantee the wipe happens on the one that installs this.
    void armClsStateWatchpoint()
    {
        // cls.state is 0x076446B0 absolute against a 0x400000 image base, so
        // 0x072446B0 from the module. Derived from the constant rather than typed as a
        // second literal: the first attempt hand-wrote 0x036446B0, armed on the wrong
        // address entirely, and duly caught an unrelated write (0x03A446B0 in the log).
        constexpr DWORD_PTR ClsStateAbsolute = 0x076446B0;
        constexpr DWORD_PTR AssumedImageBase = 0x00400000;
        auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        const auto target = reinterpret_cast<DWORD_PTR>(module) +
            (ClsStateAbsolute - AssumedImageBase);

        auto *const snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if (snapshot == INVALID_HANDLE_VALUE)
            return;
        THREADENTRY32 entry{};
        entry.dwSize = sizeof(entry);
        const auto self = GetCurrentProcessId();
        std::size_t armed = 0;
        if (Thread32First(snapshot, &entry))
        {
            do
            {
                if (entry.th32OwnerProcessID != self)
                    continue;
                auto *const thread = OpenThread(
                    THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME,
                    FALSE, entry.th32ThreadID);
                if (!thread)
                    continue;
                const auto isSelf = entry.th32ThreadID == GetCurrentThreadId();
                if (!isSelf)
                    SuspendThread(thread);
                CONTEXT context{};
                context.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                if (GetThreadContext(thread, &context))
                {
                    context.Dr0 = target;
                    // AND DR1 ON com_errorCode. Only one instruction in the image writes
                    // it (sub_4F7DA0+0x21E, `= ecx`) and that is the drop handler storing
                    // the code it was already given -- so whoever SETS it to 2 does so
                    // through a pointer, exactly as cls.state was wiped through one. The
                    // same hardware trap answers the same shape of question.
                    context.Dr1 = reinterpret_cast<DWORD_PTR>(module) +
                        (0x033E7904 - AssumedImageBase);
                    // DR7: enable DR0 and DR1 locally (bits 0 and 2); for each, R/W = 01
                    // (write) and LEN = 11 (four bytes) -- DR0 at bits 16-19, DR1 at 20-23.
                    context.Dr7 = (context.Dr7 & ~static_cast<DWORD_PTR>(0xFF000F)) |
                        0x1 | 0x4 |
                        (0x1 << 16) | (0x3 << 18) |
                        (0x1 << 20) | (0x3 << 22);
                    context.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                    if (SetThreadContext(thread, &context))
                        ++armed;
                }
                if (!isSelf)
                    ResumeThread(thread);
                CloseHandle(thread);
            } while (Thread32Next(snapshot, &entry));
        }
        CloseHandle(snapshot);
        char line[160]{};
        std::snprintf(line, sizeof(line),
            "WATCHPOINTS armed on %zu thread(s): cls.state 0x%08X + com_errorCode 0x%08X",
            armed, static_cast<unsigned>(target),
            static_cast<unsigned>(reinterpret_cast<DWORD_PTR>(
                GetModuleHandleW(nullptr)) + (0x033E7904 - AssumedImageBase)));
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
    }

    LONG CALLBACK watchpointHandler(EXCEPTION_POINTERS *const pointers)
    {
        if (pointers->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
            return EXCEPTION_CONTINUE_SEARCH;
        // DR6 bit 0 = DR0 (cls.state), bit 1 = DR1 (com_errorCode). Anything else is a
        // real single-step and is none of our business.
        const auto which = pointers->ContextRecord->Dr6 & 0x3;
        if (which == 0)
            return EXCEPTION_CONTINUE_SEARCH;
        const auto isErrorCode = (which & 0x2) != 0;
        pointers->ContextRecord->Dr6 = 0;
        // NOT ONE-SHOT. The first attempt logged once and spent itself on a routine write
        // at 23:01:29 -- ninety seconds BEFORE the client entered the match at 23:02:57 --
        // so the transition that matters was never seen. cls.state is written on every
        // rung of the connect ladder; the interesting one is late and writes 0.
        //
        // Capped so a loop cannot bury the log, and the NEW VALUE is printed: a debug
        // write breakpoint traps AFTER the store, so the value at the address is what was
        // just written. `= 0` after the client has entered is the one to read.
        static volatile long reported = 0;
        if (InterlockedIncrement(&reported) <= 24)
        {
            auto *const module =
                reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
            const auto at = reinterpret_cast<std::uintptr_t>(
                pointers->ExceptionRecord->ExceptionAddress);
            const auto base = reinterpret_cast<std::uintptr_t>(module);
            const auto watched = isErrorCode ? 0x033E7904u : 0x076446B0u;
            const auto written = *reinterpret_cast<const std::uint32_t *>(
                base + (watched - 0x00400000));
            char line[240]{};
            std::snprintf(line, sizeof(line),
                "%s = %u WRITTEN by the instruction before 0x%08X (module+0x%X) "
                "-- resolve with Tools/olfinal/xrefs.py; caller frame [ebp+4]=0x%08X",
                isErrorCode ? "com_errorCode" : "cls.state",
                written,
                static_cast<unsigned>(at),
                static_cast<unsigned>(at - base),
                static_cast<unsigned>(
                    pointers->ContextRecord->Ebp
                        ? *reinterpret_cast<const std::uint32_t *>(
                              pointers->ContextRecord->Ebp + 4)
                        : 0));
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    __declspec(naked) void clDisconnectHook()
    {
        __asm
        {
            pushfd
            pushad
            // The caller lives at [ebp+4]: this site is inside sub_77C290, whose
            // prologue established the frame, so ebp+4 is the return address into
            // whoever asked for the disconnect.
            mov eax, [ebp + 4]
            push eax
            call recordDisconnect
            add esp, 4
            popad
            popfd
            // Into the trampoline: it performs the real cls.state write, then jumps
            // back past the whole ten-byte instruction. A JMP, not a CALL.
            jmp dword ptr [Trampoline]
        }
    }
}

namespace CodolGameServer
{
    DisconnectWitnessResult installDisconnectWitness()
    {
        const auto *const requested = std::getenv("OLMOD_DISCONNECT_WITNESS");
        if (!requested || *requested != '1')
            return DisconnectWitnessResult::NotRequested;
        if (Trampoline)
            return DisconnectWitnessResult::AlreadyInstalled;

        auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return DisconnectWitnessResult::UnsupportedHost;
        const auto *const dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return DisconnectWitnessResult::UnsupportedHost;
        const auto *const nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(
            module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            ClsStateWriteRva + StolenSize >= nt->OptionalHeader.SizeOfImage)
        {
            return DisconnectWitnessResult::UnsupportedHost;
        }

        auto *const target = module + ClsStateWriteRva;

        // REFUSE UNLESS THE INSTRUCTION IS EXACTLY THE ONE MEASURED. Writing five bytes
        // over something else is how a debugging aid becomes a crash unrelated to the bug.
        if (!std::equal(std::begin(ExpectedWrite), std::end(ExpectedWrite), target))
            return DisconnectWitnessResult::UnexpectedBytes;

        auto *const trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr, StolenSize + 5, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
        if (!trampoline)
            return DisconnectWitnessResult::UnsupportedHost;

        // BUILD THE TRAMPOLINE BEFORE WRITING THE JUMP, or it relocates its own jump.
        // The stolen bytes are one absolute `mov [imm32], imm32` -- position independent,
        // so copying it is safe. The trampoline performs the real write, then returns
        // past the whole instruction.
        std::copy_n(target, StolenSize, trampoline);
        trampoline[StolenSize] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + StolenSize + 1) =
            static_cast<std::int32_t>(
                (target + StolenSize) - (trampoline + StolenSize + 5));

        DWORD oldProtection{};
        if (!VirtualProtect(target, StolenSize, PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return DisconnectWitnessResult::UnsupportedHost;
        }
        Trampoline = trampoline;
        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&clDisconnectHook) - (target + 5));
        // NOP the five bytes the jump does not cover, so nothing half-decoded is left
        // behind if execution ever lands past the jump.
        std::fill(target + HookSize, target + StolenSize, std::uint8_t{ 0x90 });
        FlushInstructionCache(GetCurrentProcess(), target, StolenSize);
        VirtualProtect(target, StolenSize, oldProtection, &oldProtection);

        // Com_Error, same pattern, with the relative call relocated.
        auto *const comError = module + ComErrorRva;
        if (std::equal(std::begin(ExpectedComError), std::end(ExpectedComError), comError))
        {
            auto *const tramp = static_cast<std::uint8_t *>(VirtualAlloc(
                nullptr, ComErrorStolen + 5, MEM_COMMIT | MEM_RESERVE,
                PAGE_EXECUTE_READWRITE));
            if (tramp)
            {
                // RELOCATE THE CALL. Its operand is a delta from the END of the
                // instruction, so the same bytes at a new address would call somewhere
                // else entirely. Resolve the original destination, then re-encode the
                // delta from the trampoline.
                const auto originalDelta =
                    *reinterpret_cast<const std::int32_t *>(comError + 1);
                auto *const destination = comError + ComErrorStolen + originalDelta;
                tramp[0] = 0xE8;
                *reinterpret_cast<std::int32_t *>(tramp + 1) =
                    static_cast<std::int32_t>(destination - (tramp + 5));
                tramp[ComErrorStolen] = 0xE9;
                *reinterpret_cast<std::int32_t *>(tramp + ComErrorStolen + 1) =
                    static_cast<std::int32_t>(
                        (comError + ComErrorStolen) - (tramp + ComErrorStolen + 5));

                DWORD previous{};
                if (VirtualProtect(comError, ComErrorStolen, PAGE_EXECUTE_READWRITE,
                        &previous))
                {
                    ComErrorTrampoline = tramp;
                    comError[0] = 0xE9;
                    *reinterpret_cast<std::int32_t *>(comError + 1) =
                        static_cast<std::int32_t>(
                            reinterpret_cast<std::uint8_t *>(&comErrorHook) -
                            (comError + 5));
                    FlushInstructionCache(GetCurrentProcess(), comError, ComErrorStolen);
                    VirtualProtect(comError, ComErrorStolen, previous, &previous);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "Com_Error witness armed too");
                }
                else
                {
                    VirtualFree(tramp, 0, MEM_RELEASE);
                }
            }
        }
        else
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "Com_Error witness NOT armed -- sub_4F8350 is not the expected call");
        }
        // The configstring validator, six stolen bytes with a NOP of padding.
        {
            auto *const validator = module + ValidatorRva;
            if (std::equal(std::begin(ExpectedValidator), std::end(ExpectedValidator),
                    validator))
            {
                auto *const tramp = static_cast<std::uint8_t *>(VirtualAlloc(
                    nullptr, ValidatorStolen + 5, MEM_COMMIT | MEM_RESERVE,
                    PAGE_EXECUTE_READWRITE));
                if (tramp)
                {
                    std::copy_n(validator, ValidatorStolen, tramp);
                    tramp[ValidatorStolen] = 0xE9;
                    *reinterpret_cast<std::int32_t *>(tramp + ValidatorStolen + 1) =
                        static_cast<std::int32_t>(
                            (validator + ValidatorStolen) - (tramp + ValidatorStolen + 5));
                    DWORD previous{};
                    if (VirtualProtect(validator, ValidatorStolen,
                            PAGE_EXECUTE_READWRITE, &previous))
                    {
                        ValidatorTrampoline = tramp;
                        validator[0] = 0xE9;
                        *reinterpret_cast<std::int32_t *>(validator + 1) =
                            static_cast<std::int32_t>(
                                reinterpret_cast<std::uint8_t *>(&validatorHook) -
                                (validator + 5));
                        validator[5] = 0x90;
                        FlushInstructionCache(
                            GetCurrentProcess(), validator, ValidatorStolen);
                        VirtualProtect(validator, ValidatorStolen, previous, &previous);
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "configstring validator witness armed");
                    }
                    else
                    {
                        VirtualFree(tramp, 0, MEM_RELEASE);
                    }
                }
            }
            else
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "configstring validator NOT armed -- sub_514540 prologue differs");
            }
        }

        // The watchpoint last: it is the one that cannot be evaded, and it is armed
        // after the software hooks so their own writes cannot trip it.
        AddVectoredExceptionHandler(1, &watchpointHandler);
        armClsStateWatchpoint();
        return DisconnectWitnessResult::Installed;
    }

    const char *disconnectWitnessResultName(const DisconnectWitnessResult result)
    {
        switch (result)
        {
        case DisconnectWitnessResult::NotRequested: return "not requested";
        case DisconnectWitnessResult::Installed: return "installed";
        case DisconnectWitnessResult::AlreadyInstalled: return "already installed";
        case DisconnectWitnessResult::UnexpectedBytes:
            return "UNEXPECTED BYTES -- 0x0077C343 is not this build's cls.state=0 "
                   "write, nothing was written";
        case DisconnectWitnessResult::UnsupportedHost: return "unsupported host";
        }
        return "unknown";
    }
}
