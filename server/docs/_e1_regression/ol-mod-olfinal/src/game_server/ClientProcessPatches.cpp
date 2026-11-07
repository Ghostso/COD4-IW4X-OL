#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "ClientProcessPatches.hpp"
#include "EngineBindings.hpp"
#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <span>
#include <cstddef>
#include <cstring>
#include <cmath>
#include <limits>
#include <string>
#include <string_view>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(1649370): HUD 466450 reads battery_multiplier at46659E,
        // multiplies by1000 at4665DA and uses that divisor at4665EC/466610.
        // The distributed EB4B bypass leaves1000 even in Factory (retail1.2).
        // Intercept the divide; keep native whole/remainder/percentage rendering.
        constexpr std::size_t BatteryDivideRva = 0x665E9;
        constexpr std::array<std::uint8_t, 7> BatteryDivideBytes{
            0x8B, 0xC7, 0x99, 0xF7, 0x7C, 0x24, 0x0C};
        void *BatteryDivideContinuation{};
        using BatteryDvarLookup = const std::uint8_t *(__cdecl *)(const char *);
        BatteryDvarLookup FindBatteryDvar{};

        int __cdecl readBatteryDisplayDivisor()
        {
            // CODREF(1649370): same lookup ABI and type1(float)/string conversion
            // as4665A3..4665D6. Lookup each draw: no stale pointer across maps.
            const auto *dvar = FindBatteryDvar("battery_multiplier");
            if (!dvar)
                return 1000;
            double multiplier{};
            if (dvar[8] == 1)
            {
                float value{};
                std::memcpy(&value, dvar + 12, sizeof(value));
                multiplier = value;
            }
            else
            {
                const char *value{};
                std::memcpy(&value, dvar + 12, sizeof(value));
                multiplier = value ? std::atof(value) : 0.0;
            }
            return clientBatteryDisplayDivisor(multiplier);
        }

        __declspec(naked) void clientBatteryDisplayStub()
        {
            __asm
            {
                pushfd
                pushad
                mov ebx, esp
                sub esp, 528
                and esp, 0FFFFFFF0h
                fxsave [esp]
                call readBatteryDisplayDivisor
                // Original ESP+12:36 saved bytes plus12. Preserve all other state.
                mov [ebx+48], eax
                fxrstor [esp]
                mov esp, ebx
                popad
                popfd
                mov eax, edi
                cdq
                idiv dword ptr [esp+12]
                jmp dword ptr [BatteryDivideContinuation]
            }
        }
        // CODOL WndProc calls SetThreadExecutionState at its entry -- 0x00643FE0
        // on 3.3.3.3, 0x00780860 on out.exe (1649370).
        //
        // CODREF(client_window_proc): all four constants below were re-derived
        // for 1649370 by IMPORT SIGNATURE, which is the one anchor that survives
        // an unrelated build: an import is named in the file, so
        // `call [SetThreadExecutionState]` means the same thing everywhere even
        // though the IAT slot moved 0x00B5B244 -> 0x0E9D34A8 and out.exe's table
        // was rebuilt by its unpacker. Each build contains EXACTLY ONE call site
        // for that API, so there was nothing to disambiguate. CL_MouseEvent and
        // its caller were pinned the same way -- {ClipCursor,
        // InterlockedExchange, QueryPerformanceCounter} and {GetCursorPos,
        // GetForegroundWindow, ScreenToClient} each match exactly one function
        // in out.exe, and the caller is 0xB0 bytes in BOTH builds.
        //
        // ClientWindowHandle is a data global, so it is positional: inside that
        // caller pair every .data reference aligns at an identical byte offset,
        // 0x03749AAC appears at +0x10 and +0x4F and maps to 0x081AA758 both
        // times, and its neighbour 0x03749ABC -> 0x081AA768 keeps the same +0x10
        // adjacency.
        // See Tools/olfinal/import-signature.py in the CODOL-main tree.
        // Mouse polling can deliver substantially more window messages than
        // game frames, so retain the display request from the frame callback.
        constexpr std::size_t ExecutionStateCallRva = 0x380880;
        constexpr std::array<std::uint8_t, 6> ExecutionStateCall{
            0xFF, 0x15, 0xA8, 0x34, 0x9D, 0x0E,
        };
        constexpr std::size_t RelocatedAddressOffset = 2;
        constexpr std::size_t RelocatedAddressSize = 4;
        // The original WINAPI call consumes the preceding `push 2`. Keep
        // that stack effect when removing the call or MainWndProc returns
        // with ESP shifted and eventually trips its /GS cookie check.
        constexpr std::array<std::uint8_t, 6> ExecutionStateReplacement{
            0x83, 0xC4, 0x04, 0x90, 0x90, 0x90,
        };
        constexpr std::size_t ClientMouseEventCallRva = 0x37ADF2;
        constexpr std::array<std::uint8_t, 5> ClientMouseEventCall{
            0xE8, 0x99, 0x66, 0xE3, 0xFF,
        };
        constexpr std::size_t ClientMouseEventRva = 0x1B1490;
        constexpr std::size_t ClientWindowHandleRva = 0x7DAA758;

        // CODREF(1649370): CL_ParseGamestate performs two calls to
        // sub_59B560. 0x454A54 walks ordinary weapon configstrings with arg 1;
        // after defaultweapon/defaultknife and registry finalization,
        // 0x454B55 walks modular strings with arg 0. The latter is the exact
        // boundary where runtime-only alpha WeaponDefs must be restored after
        // the parser's registry clear and before "** <base> ..." is resolved.
        constexpr std::size_t ClientModularWeaponWalkCallRva = 0x54B55;
        constexpr std::size_t ClientWeaponWalkRva = 0x19B560;
        constexpr std::size_t RelativeCallSize = 5;

        // CODREF(1649370): sub_4DAE70 consumes an effect descriptor through its
        // second argument. Its first dereference is `mov edx,[esi]` followed by
        // `mov eax,[edx+18h]`. Wetwork can supply a valid descriptor holder with
        // a null effect pointer. The first crash was reached through CG_AddLoopFx,
        // but a later trace reached the same worker through out.exe+0x131C7B;
        // there are 18 native callers. Guard the shared worker entry so every
        // missing effect degrades to no visual. Its verified six-byte prologue is
        // `push ebp; mov ebp,esp; sub esp,20h`.
        constexpr std::size_t ClientLoopFxWorkerRva = 0xDAE70;
        constexpr std::array<std::uint8_t, 6> ClientLoopFxWorkerPrologue{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20,
        };

        // CODREF(1649370): CG_EntityEvent 0x00532A60 resolves the event's
        // weapon index through dword_1988B50. At 0x00532A76 it reads
        // WeaponDef+0xEF3 before the function's own null check at 0x00532A9C.
        // A weaponless event therefore faults at out.exe+0x0132A76. Detour only
        // the seven-byte read and preserve both original destinations.
        constexpr std::size_t ClientEntityEventWeaponReadRva = 0x132A76;
        constexpr std::array<std::uint8_t, 7>
            ClientEntityEventWeaponRead{
                0x80, 0xB9, 0xF3, 0x0E, 0x00, 0x00, 0x00,
            };
        constexpr std::size_t ClientEntityEventWeaponReadResumeRva = 0x132A7D;
        constexpr std::size_t ClientEntityEventNullWeaponRva = 0x132A8C;

        // CG_EntityEvent accepts event ids 0..184. Its default jump-table arm
        // calls Com_Error for anything larger, turning a stale network event
        // into a client drop. Guard the six-byte function prologue so invalid
        // ids are discarded before the native dispatcher indexes its name table.
        constexpr std::size_t ClientEntityEventRva = 0x132910;
        constexpr std::array<std::uint8_t, 6> ClientEntityEventPrologue{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8,
        };
        constexpr std::size_t ClientEntityEventResumeRva = 0x132916;
        constexpr std::uint32_t MaximumClientEntityEvent = 184;

        // sub_421A70 is BG_GetAmmoInClip(ps, weapon, hand). Its first ten
        // bytes build a frame and resolve dword_1988B50[weapon], then +0xA
        // dereferences WeaponDef+0x7F4 without accepting weapon 0.
        constexpr std::size_t ClientAmmoLookupRva = 0x21A70;
        constexpr std::array<std::uint8_t, 10> ClientAmmoLookupEntry{
            0x55, 0x8B, 0xEC, 0x8B, 0x0C, 0x85, 0x50, 0x8B, 0x98, 0x01,
        };
        constexpr std::size_t ClientAmmoLookupResumeRva = 0x21A7A;

        // sub_42C0E0 totals ammo/inventory state across the player's 15 weapon
        // slots. The loop skips a zero slot but assumes every nonzero index has
        // a registered WeaponDef. Respawn can retain an unavailable index; skip
        // it exactly like an empty slot instead of reading null+0x7EC.
        constexpr std::size_t ClientWeaponInventoryReadRva = 0x2C146;
        constexpr std::array<std::uint8_t, 7> ClientWeaponInventoryRead{
            0x8B, 0x0C, 0x85, 0x50, 0x8B, 0x98, 0x01,
        };
        constexpr std::size_t ClientWeaponInventoryResumeRva = 0x2C14D;
        constexpr std::size_t ClientWeaponInventorySkipRva = 0x2C187;

        // sub_5A41E0 resolves a UI expression operator from a 20 x 3 x 3
        // function-pointer table. It trusts the operator and both operand type
        // tags; corrupted post-respawn values can index past the table and make
        // sub_5A43E0 call a garbage pointer. Invalid expressions already have a
        // native no-operation path when this resolver returns null.
        constexpr std::size_t ClientUiOperatorResolverRva = 0x1A41E0;
        constexpr std::array<std::uint8_t, 6> ClientUiOperatorResolverPrologue{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x17,
        };
        constexpr std::size_t ClientUiOperatorResolverResumeRva = 0x1A41E6;

        // CODREF(1649370 sub_4834F0): after rsa_verify_hash_ex returns
        // CRYPT_OK, 0x0048371A converts its out-stat at [esp+8] into AL. The
        // eight original bytes are `cmp [esp+8],1; sete al`. Locally repacked
        // zones cannot reproduce Tencent's signing key, so the opt-in
        // replacement accepts that verdict while leaving every earlier SHA-256
        // comparison and every later zone-name/block check intact.
        constexpr std::size_t UnsignedFastfileVerificationRva = 0x8371A;
        constexpr std::array<std::uint8_t, 8>
            UnsignedFastfileVerification{
                0x83, 0x7C, 0x24, 0x08, 0x01, 0x0F, 0x94, 0xC0,
            };
        constexpr std::array<std::uint8_t, 8>
            UnsignedFastfileVerificationReplacement{
                0xB0, 0x01, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90,
            };

        using ClientMouseEvent = BOOL (*)();
        ClientMouseEvent OriginalClientMouseEvent{};
        void *OriginalClientWeaponWalk{};
        void *ClientLoopFxWorkerContinuation{};
        void *ClientEntityEventWeaponReadContinuation{};
        void *ClientEntityEventNullWeaponContinuation{};
        void *ClientEntityEventContinuation{};
        void *ClientAmmoLookupContinuation{};
        void *ClientWeaponInventoryContinuation{};
        void *ClientWeaponInventorySkipContinuation{};
        void *ClientUiOperatorResolverContinuation{};
        ClientAlphaWeaponPrepareCallback AlphaWeaponPrepareCallback{};
        SRWLOCK RawMouseLock = SRWLOCK_INIT;
        LONG RawMouseDeltaX{};
        LONG RawMouseDeltaY{};
        std::uint32_t RawMouseEventCount{};
        WNDPROC PreviousWindowProcedure{};
        HWND RawInputWindow{};

        enum class ExecutionStateCallState
        {
            Original,
            Patched,
            Unexpected,
        };

        ExecutionStateCallState inspectExecutionStateCall(
            const std::span<const std::uint8_t> image)
        {
            if (ExecutionStateCallRva > image.size() ||
                ExecutionStateCall.size() > image.size() - ExecutionStateCallRva)
            {
                return ExecutionStateCallState::Unexpected;
            }

            const auto actual = image.subspan(
                ExecutionStateCallRva, ExecutionStateCall.size());
            if (std::ranges::equal(actual, ExecutionStateReplacement))
            {
                return ExecutionStateCallState::Patched;
            }

            for (std::size_t index = 0; index != ExecutionStateCall.size(); ++index)
            {
                if (index >= RelocatedAddressOffset &&
                    index < RelocatedAddressOffset + RelocatedAddressSize)
                {
                    continue;
                }
                if (actual[index] != ExecutionStateCall[index])
                    return ExecutionStateCallState::Unexpected;
            }
            return ExecutionStateCallState::Original;
        }

        bool executionStateImportMatches(
            const std::uint8_t *const module,
            const std::size_t imageSize)
        {
            std::uint32_t iatAddress{};
            std::memcpy(
                &iatAddress,
                module + ExecutionStateCallRva + RelocatedAddressOffset,
                sizeof(iatAddress));
            const auto moduleStart = reinterpret_cast<std::uintptr_t>(module);
            const auto moduleEnd = moduleStart + imageSize;
            if (iatAddress < moduleStart ||
                iatAddress > moduleEnd - sizeof(void *))
            {
                return false;
            }

            const auto imported = *reinterpret_cast<void *const *>(
                static_cast<std::uintptr_t>(iatAddress));
            const auto kernel32 = GetModuleHandleW(L"kernel32.dll");
            const auto expected = kernel32
                ? GetProcAddress(kernel32, "SetThreadExecutionState")
                : nullptr;
            return expected && imported == reinterpret_cast<void *>(expected);
        }

        bool drainRawMouseDelta(int *const deltaX, int *const deltaY)
        {
            AcquireSRWLockExclusive(&RawMouseLock);
            const auto eventCount = RawMouseEventCount;
            if (eventCount)
            {
                *deltaX = RawMouseDeltaX;
                *deltaY = RawMouseDeltaY;
                RawMouseDeltaX = 0;
                RawMouseDeltaY = 0;
                RawMouseEventCount = 0;
            }
            ReleaseSRWLockExclusive(&RawMouseLock);
            return eventCount != 0;
        }

        __declspec(naked) void clientMouseEventRawInputStub()
        {
            __asm
            {
                push ebp
                mov ebp, esp
                push edi
                sub esp, 8
                lea eax, [ebp-12]
                push eax
                lea ecx, [ebp-8]
                push ecx
                call drainRawMouseDelta
                add esp, 8
                test al, al
                jz use_legacy_delta
                mov edi, [ebp-8]
                mov edx, [ebp-12]
                mov [ebp+16], edx
            use_legacy_delta:
                push dword ptr [ebp+16]
                push dword ptr [ebp+12]
                push dword ptr [ebp+8]
                call dword ptr [OriginalClientMouseEvent]
                add esp, 12
                mov edi, [ebp-4]
                mov esp, ebp
                pop ebp
                ret
            }
        }

        __declspec(naked) void clientAlphaWeaponModularWalkStub()
        {
            __asm
            {
                // The patched site is inside a 1..1699 loop. Restore the alpha
                // bases once, immediately before its first modular lookup.
                cmp edi, 1
                jne invoke_native_walk
                pushfd
                pushad
                call dword ptr [AlphaWeaponPrepareCallback]
                popad
                popfd
            invoke_native_walk:
                // The original call's return address is already on the stack;
                // tail-jump so sub_59B560 returns directly to CL_ParseGamestate.
                jmp dword ptr [OriginalClientWeaponWalk]
            }
        }

        __declspec(naked) void clientLoopFxNullGuardStub()
        {
            __asm
            {
                mov eax, [esp+8]
                test eax, eax
                jz missing_effect
                cmp dword ptr [eax], 0
                jz missing_effect
                // Replay the displaced native prologue, then resume after the
                // six-byte entry detour.
                push ebp
                mov ebp, esp
                sub esp, 20h
                jmp dword ptr [ClientLoopFxWorkerContinuation]
            missing_effect:
                xor eax, eax
                ret
            }
        }

        __declspec(naked) void clientEntityEventWeaponGuardStub()
        {
            __asm
            {
                test ecx, ecx
                jz null_weapon
                cmp byte ptr [ecx+0EF3h], 0
                jmp dword ptr [ClientEntityEventWeaponReadContinuation]
            null_weapon:
                jmp dword ptr [ClientEntityEventNullWeaponContinuation]
            }
        }

        void __cdecl recordRejectedClientEntityEvent(
            const std::uint32_t event, const std::uint8_t *const entity)
        {
            static volatile long reported{};
            if (InterlockedIncrement(&reported) > 16)
                return;
            const auto number = entity
                ? *reinterpret_cast<const std::uint32_t *>(entity + 0xF4)
                : 0xFFFFFFFFu;
            const auto type = entity
                ? *reinterpret_cast<const std::uint32_t *>(entity + 0xF8)
                : 0xFFFFFFFFu;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "client rejected invalid entity event=" +
                    std::to_string(event) + " entity=" +
                    std::to_string(number) + " eType=" +
                    std::to_string(type));
        }

        __declspec(naked) void clientEntityEventRangeGuardStub()
        {
            __asm
            {
                cmp dword ptr [esp+4], 0B8h
                jbe valid_event
                pushfd
                pushad
                mov eax, [esp+20]
                push eax
                mov eax, [esp+44]
                push eax
                call recordRejectedClientEntityEvent
                add esp, 8
                popad
                popfd
                xor eax, eax
                ret 8
            valid_event:
                push ebp
                mov ebp, esp
                and esp, 0FFFFFFF8h
                jmp dword ptr [ClientEntityEventContinuation]
            }
        }

        __declspec(naked) void clientAmmoLookupWeaponGuardStub()
        {
            __asm
            {
                test eax, eax
                jz no_ammo
                mov ecx, dword ptr [eax*4+01988B50h]
                test ecx, ecx
                jz no_ammo
                push ebp
                mov ebp, esp
                jmp dword ptr [ClientAmmoLookupContinuation]
            no_ammo:
                xor eax, eax
                ret
            }
        }

        __declspec(naked) void clientWeaponInventoryGuardStub()
        {
            __asm
            {
                cmp eax, 06A3h
                ja missing_weapon
                mov ecx, dword ptr [eax*4+01988B50h]
                cmp ecx, 10000h
                jb missing_weapon
                jmp dword ptr [ClientWeaponInventoryContinuation]
            missing_weapon:
                jmp dword ptr [ClientWeaponInventorySkipContinuation]
            }
        }

        __declspec(naked) void clientUiOperatorResolverGuardStub()
        {
            __asm
            {
                cmp eax, 13h
                ja invalid_expression
                test edi, edi
                jz invalid_expression
                cmp dword ptr [edi], 2
                ja invalid_expression
                mov edx, [esp+4]
                test edx, edx
                jz invalid_expression
                cmp dword ptr [edx], 2
                ja invalid_expression
                push ebp
                mov ebp, esp
                push ecx
                mov edx, [edi]
                jmp dword ptr [ClientUiOperatorResolverContinuation]
            invalid_expression:
                xor eax, eax
                ret 4
            }
        }

        LRESULT CALLBACK rawInputWindowProcedure(
            const HWND window,
            const UINT message,
            const WPARAM wParam,
            const LPARAM lParam)
        {
            if (message == WM_INPUT)
            {
                RAWINPUT input{};
                UINT size = sizeof(input);
                if (GetRawInputData(
                        reinterpret_cast<HRAWINPUT>(lParam),
                        RID_INPUT,
                        &input,
                        &size,
                        sizeof(RAWINPUTHEADER)) == size &&
                    input.header.dwType == RIM_TYPEMOUSE &&
                    !(input.data.mouse.usFlags & MOUSE_MOVE_ABSOLUTE) &&
                    (input.data.mouse.lLastX || input.data.mouse.lLastY))
                {
                    AcquireSRWLockExclusive(&RawMouseLock);
                    RawMouseDeltaX += input.data.mouse.lLastX;
                    RawMouseDeltaY += input.data.mouse.lLastY;
                    ++RawMouseEventCount;
                    ReleaseSRWLockExclusive(&RawMouseLock);
                }
            }
            return CallWindowProcA(
                PreviousWindowProcedure, window, message, wParam, lParam);
        }

        bool validHostImage(
            std::uint8_t *const module,
            const IMAGE_NT_HEADERS *&nt)
        {
            if (!module)
                return false;
            const auto *const dos =
                reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
            if (dos->e_magic != IMAGE_DOS_SIGNATURE)
                return false;
            nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(
                module + dos->e_lfanew);
            return nt->Signature == IMAGE_NT_SIGNATURE &&
                nt->FileHeader.Machine == IMAGE_FILE_MACHINE_I386 &&
                nt->FileHeader.TimeDateStamp == EngineBindings::ExpectedTimestamp &&
                nt->OptionalHeader.SizeOfImage == EngineBindings::ExpectedImageSize;
        }
    }

    bool patchClientExecutionStateBuffer(const std::span<std::uint8_t> image)
    {
        const auto state = inspectExecutionStateCall(image);
        if (state == ExecutionStateCallState::Patched)
            return true;
        if (state != ExecutionStateCallState::Original)
            return false;
        std::ranges::copy(
            ExecutionStateReplacement,
            image.begin() + ExecutionStateCallRva);
        return true;
    }

    bool patchClientRawMouseCallBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientMouseEventCallRva > image.size() ||
            ClientMouseEventCall.size() > image.size() - ClientMouseEventCallRva)
        {
            return false;
        }
        auto actual = image.subspan(
            ClientMouseEventCallRva, ClientMouseEventCall.size());
        const auto nextInstruction = imageBase + ClientMouseEventCallRva +
            ClientMouseEventCall.size();
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, 5> patched{ 0xE8 };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(actual, patched))
            return true;
        if (!std::ranges::equal(actual, ClientMouseEventCall))
            return false;
        std::ranges::copy(patched, actual.begin());
        return true;
    }

    bool patchClientAlphaWeaponGamestateCallBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientModularWeaponWalkCallRva > image.size() ||
            RelativeCallSize >
                image.size() - ClientModularWeaponWalkCallRva)
        {
            return false;
        }

        auto call = image.subspan(
            ClientModularWeaponWalkCallRva, RelativeCallSize);
        if (call[0] != 0xE8)
            return false;
        std::int32_t presentDisplacement{};
        std::memcpy(
            &presentDisplacement, call.data() + 1,
            sizeof(presentDisplacement));
        const auto nextInstruction = imageBase +
            ClientModularWeaponWalkCallRva + RelativeCallSize;
        const auto presentTarget = static_cast<std::uintptr_t>(
            static_cast<std::intptr_t>(nextInstruction) +
            presentDisplacement);
        if (presentTarget == replacement)
            return true;
        if (presentTarget != imageBase + ClientWeaponWalkRva)
            return false;

        const auto replacementDisplacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::memcpy(
            call.data() + 1, &replacementDisplacement,
            sizeof(replacementDisplacement));
        return true;
    }

    bool patchClientLoopFxWorkerEntryBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientLoopFxWorkerRva > image.size() ||
            ClientLoopFxWorkerPrologue.size() >
                image.size() - ClientLoopFxWorkerRva)
        {
            return false;
        }

        auto entry = image.subspan(
            ClientLoopFxWorkerRva, ClientLoopFxWorkerPrologue.size());
        const auto nextInstruction = imageBase + ClientLoopFxWorkerRva +
            RelativeCallSize;
        const auto replacementDisplacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientLoopFxWorkerPrologue.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90,
        };
        std::memcpy(
            patched.data() + 1,
            &replacementDisplacement,
            sizeof(replacementDisplacement));
        if (std::ranges::equal(entry, patched))
            return true;
        if (!std::ranges::equal(entry, ClientLoopFxWorkerPrologue))
            return false;

        std::ranges::copy(patched, entry.begin());
        return true;
    }

    bool patchClientEntityEventWeaponGuardBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientEntityEventWeaponReadRva > image.size() ||
            ClientEntityEventWeaponRead.size() >
                image.size() - ClientEntityEventWeaponReadRva)
        {
            return false;
        }
        auto site = image.subspan(
            ClientEntityEventWeaponReadRva,
            ClientEntityEventWeaponRead.size());
        const auto nextInstruction = imageBase +
            ClientEntityEventWeaponReadRva + RelativeCallSize;
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientEntityEventWeaponRead.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90, 0x90,
        };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, ClientEntityEventWeaponRead))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    bool patchClientEntityEventRangeGuardBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientEntityEventRva > image.size() ||
            ClientEntityEventPrologue.size() > image.size() - ClientEntityEventRva)
        {
            return false;
        }
        auto site = image.subspan(
            ClientEntityEventRva, ClientEntityEventPrologue.size());
        const auto nextInstruction =
            imageBase + ClientEntityEventRva + RelativeCallSize;
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientEntityEventPrologue.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90,
        };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, ClientEntityEventPrologue))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    bool patchClientAmmoLookupWeaponGuardBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientAmmoLookupRva > image.size() ||
            ClientAmmoLookupEntry.size() > image.size() - ClientAmmoLookupRva)
        {
            return false;
        }
        auto site = image.subspan(
            ClientAmmoLookupRva, ClientAmmoLookupEntry.size());
        const auto nextInstruction =
            imageBase + ClientAmmoLookupRva + RelativeCallSize;
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientAmmoLookupEntry.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90, 0x90, 0x90, 0x90, 0x90,
        };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, ClientAmmoLookupEntry))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    bool patchClientWeaponInventoryGuardBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientWeaponInventoryReadRva > image.size() ||
            ClientWeaponInventoryRead.size() >
                image.size() - ClientWeaponInventoryReadRva)
        {
            return false;
        }
        auto site = image.subspan(
            ClientWeaponInventoryReadRva, ClientWeaponInventoryRead.size());
        const auto nextInstruction = imageBase +
            ClientWeaponInventoryReadRva + RelativeCallSize;
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientWeaponInventoryRead.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90, 0x90,
        };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, ClientWeaponInventoryRead))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    bool patchClientUiOperatorResolverGuardBuffer(
        const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase,
        const std::uintptr_t replacement)
    {
        if (ClientUiOperatorResolverRva > image.size() ||
            ClientUiOperatorResolverPrologue.size() >
                image.size() - ClientUiOperatorResolverRva)
        {
            return false;
        }
        auto site = image.subspan(
            ClientUiOperatorResolverRva,
            ClientUiOperatorResolverPrologue.size());
        const auto nextInstruction = imageBase +
            ClientUiOperatorResolverRva + RelativeCallSize;
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, ClientUiOperatorResolverPrologue.size()> patched{
            0xE9, 0, 0, 0, 0, 0x90,
        };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, ClientUiOperatorResolverPrologue))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    bool patchUnsignedFastfileVerificationBuffer(
        const std::span<std::uint8_t> image)
    {
        if (UnsignedFastfileVerificationRva > image.size() ||
            UnsignedFastfileVerification.size() >
                image.size() - UnsignedFastfileVerificationRva)
        {
            return false;
        }
        auto site = image.subspan(
            UnsignedFastfileVerificationRva,
            UnsignedFastfileVerification.size());
        if (std::ranges::equal(
                site, UnsignedFastfileVerificationReplacement))
        {
            return true;
        }
        if (!std::ranges::equal(site, UnsignedFastfileVerification))
            return false;
        std::ranges::copy(
            UnsignedFastfileVerificationReplacement, site.begin());
        return true;
    }

    int clientBatteryDisplayDivisor(const double multiplier)
    {
        // OLMOD(battery_hud_guard): native missing-dvar path produces zero.
        // Retain default1000 for invalid/unrepresentable input, including startup.
        const double units = multiplier * 1000.0;
        if (!std::isfinite(units) || units < 1.0 ||
            units > static_cast<double>(std::numeric_limits<int>::max()))
            return 1000;
        return static_cast<int>(units);
    }

    bool patchClientBatteryDisplayBuffer(const std::span<std::uint8_t> image,
        const std::uintptr_t imageBase, const std::uintptr_t replacement)
    {
        // OLMOD(battery_hud_patch): only the verified distributed bypass build.
        if (image.size() < BatteryDivideRva + BatteryDivideBytes.size() ||
            image[0x6659C] != 0xEB || image[0x6659D] != 0x4B)
            return false;
        auto site = image.subspan(BatteryDivideRva, BatteryDivideBytes.size());
        std::array<std::uint8_t, 7> patched{0xE9, 0, 0, 0, 0, 0x90, 0x90};
        const auto displacement = static_cast<std::int32_t>(
            replacement - (imageBase + BatteryDivideRva + 5));
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(site, patched))
            return true;
        if (!std::ranges::equal(site, BatteryDivideBytes))
            return false;
        std::ranges::copy(patched, site.begin());
        return true;
    }

    ClientProcessPatchResult installClientBatteryDisplayPatch()
    {
        auto *module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        const IMAGE_NT_HEADERS *nt{};
        if (!module || !validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;
        auto *site = module + BatteryDivideRva;
        // Check the full expected instruction sequence before making code writable.
        const std::span<std::uint8_t> image(module, nt->OptionalHeader.SizeOfImage);
        std::array<std::uint8_t, 7> expected{0xE9, 0, 0, 0, 0, 0x90, 0x90};
        const auto displacement = static_cast<std::int32_t>(
            reinterpret_cast<std::uintptr_t>(&clientBatteryDisplayStub) -
            (reinterpret_cast<std::uintptr_t>(site) + 5));
        std::memcpy(expected.data() + 1, &displacement, sizeof(displacement));
        if (std::ranges::equal(std::span(site, 7), expected))
            return ClientProcessPatchResult::AlreadyPatched;
        if (image[0x6659C] != 0xEB || image[0x6659D] != 0x4B ||
            !std::ranges::equal(std::span(site, 7), BatteryDivideBytes))
            return ClientProcessPatchResult::UnexpectedBytes;
        DWORD protection{};
        if (!VirtualProtect(site, 7, PAGE_EXECUTE_READWRITE, &protection))
            return ClientProcessPatchResult::ProtectionFailed;
        FindBatteryDvar = reinterpret_cast<BatteryDvarLookup>(module + 0x36F190);
        BatteryDivideContinuation = module + 0x665F0;
        const auto patched = patchClientBatteryDisplayBuffer(image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(&clientBatteryDisplayStub));
        FlushInstructionCache(GetCurrentProcess(), site, 7);
        DWORD ignored{};
        VirtualProtect(site, 7, protection, &ignored);
        return patched ? ClientProcessPatchResult::Patched
                       : ClientProcessPatchResult::UnexpectedBytes;
    }

    ClientProcessPatchResult installClientAlphaWeaponGamestatePatch(
        const ClientAlphaWeaponPrepareCallback callback)
    {
        if (!callback)
            return ClientProcessPatchResult::UnexpectedTarget;
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const call = module + ClientModularWeaponWalkCallRva;
        std::int32_t presentDisplacement{};
        if (call[0] != 0xE8)
            return ClientProcessPatchResult::UnexpectedBytes;
        std::memcpy(
            &presentDisplacement, call + 1, sizeof(presentDisplacement));
        const auto presentTarget = call + RelativeCallSize +
            presentDisplacement;
        if (presentTarget == reinterpret_cast<std::uint8_t *>(
                &clientAlphaWeaponModularWalkStub))
        {
            return ClientProcessPatchResult::AlreadyPatched;
        }
        if (presentTarget != module + ClientWeaponWalkRva)
            return ClientProcessPatchResult::UnexpectedTarget;

        OriginalClientWeaponWalk = module + ClientWeaponWalkRva;
        AlphaWeaponPrepareCallback = callback;
        DWORD oldProtection{};
        if (!VirtualProtect(
                call, RelativeCallSize, PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            OriginalClientWeaponWalk = nullptr;
            AlphaWeaponPrepareCallback = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto patched = patchClientAlphaWeaponGamestateCallBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(
                &clientAlphaWeaponModularWalkStub));
        FlushInstructionCache(
            GetCurrentProcess(), call, RelativeCallSize);
        DWORD ignored{};
        VirtualProtect(call, RelativeCallSize, oldProtection, &ignored);
        if (!patched)
        {
            OriginalClientWeaponWalk = nullptr;
            AlphaWeaponPrepareCallback = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientLoopFxNullGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const entry = module + ClientLoopFxWorkerRva;
        ClientLoopFxWorkerContinuation =
            module + ClientLoopFxWorkerRva + ClientLoopFxWorkerPrologue.size();
        DWORD oldProtection{};
        if (!VirtualProtect(
                entry,
                ClientLoopFxWorkerPrologue.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            ClientLoopFxWorkerContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = entry[0] == 0xE9;
        const auto patched = patchClientLoopFxWorkerEntryBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(&clientLoopFxNullGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), entry, ClientLoopFxWorkerPrologue.size());
        DWORD ignored{};
        VirtualProtect(
            entry, ClientLoopFxWorkerPrologue.size(), oldProtection, &ignored);
        if (!patched)
        {
            ClientLoopFxWorkerContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientEntityEventWeaponGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const site = module + ClientEntityEventWeaponReadRva;
        ClientEntityEventWeaponReadContinuation =
            module + ClientEntityEventWeaponReadResumeRva;
        ClientEntityEventNullWeaponContinuation =
            module + ClientEntityEventNullWeaponRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                site,
                ClientEntityEventWeaponRead.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            ClientEntityEventWeaponReadContinuation = nullptr;
            ClientEntityEventNullWeaponContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = site[0] == 0xE9;
        const auto patched = patchClientEntityEventWeaponGuardBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(
                &clientEntityEventWeaponGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), site, ClientEntityEventWeaponRead.size());
        DWORD ignored{};
        VirtualProtect(
            site,
            ClientEntityEventWeaponRead.size(),
            oldProtection,
            &ignored);
        if (!patched)
        {
            ClientEntityEventWeaponReadContinuation = nullptr;
            ClientEntityEventNullWeaponContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientEntityEventRangeGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const site = module + ClientEntityEventRva;
        ClientEntityEventContinuation = module + ClientEntityEventResumeRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                site, ClientEntityEventPrologue.size(),
                PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            ClientEntityEventContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = site[0] == 0xE9;
        const auto patched = patchClientEntityEventRangeGuardBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(&clientEntityEventRangeGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), site, ClientEntityEventPrologue.size());
        DWORD ignored{};
        VirtualProtect(
            site, ClientEntityEventPrologue.size(), oldProtection, &ignored);
        if (!patched)
        {
            ClientEntityEventContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientAmmoLookupWeaponGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const site = module + ClientAmmoLookupRva;
        ClientAmmoLookupContinuation = module + ClientAmmoLookupResumeRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                site,
                ClientAmmoLookupEntry.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            ClientAmmoLookupContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = site[0] == 0xE9;
        const auto patched = patchClientAmmoLookupWeaponGuardBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(
                &clientAmmoLookupWeaponGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), site, ClientAmmoLookupEntry.size());
        DWORD ignored{};
        VirtualProtect(
            site,
            ClientAmmoLookupEntry.size(),
            oldProtection,
            &ignored);
        if (!patched)
        {
            ClientAmmoLookupContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientWeaponInventoryGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const site = module + ClientWeaponInventoryReadRva;
        ClientWeaponInventoryContinuation =
            module + ClientWeaponInventoryResumeRva;
        ClientWeaponInventorySkipContinuation =
            module + ClientWeaponInventorySkipRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                site, ClientWeaponInventoryRead.size(),
                PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            ClientWeaponInventoryContinuation = nullptr;
            ClientWeaponInventorySkipContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = site[0] == 0xE9;
        const auto patched = patchClientWeaponInventoryGuardBuffer(
            image,
            reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(&clientWeaponInventoryGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), site, ClientWeaponInventoryRead.size());
        DWORD ignored{};
        VirtualProtect(
            site, ClientWeaponInventoryRead.size(), oldProtection, &ignored);
        if (!patched)
        {
            ClientWeaponInventoryContinuation = nullptr;
            ClientWeaponInventorySkipContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    ClientProcessPatchResult installClientUiOperatorResolverGuardPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        auto *const site = module + ClientUiOperatorResolverRva;
        ClientUiOperatorResolverContinuation =
            module + ClientUiOperatorResolverResumeRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                site, ClientUiOperatorResolverPrologue.size(),
                PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            ClientUiOperatorResolverContinuation = nullptr;
            return ClientProcessPatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto alreadyPatched = site[0] == 0xE9;
        const auto patched = patchClientUiOperatorResolverGuardBuffer(
            image, reinterpret_cast<std::uintptr_t>(module),
            reinterpret_cast<std::uintptr_t>(
                &clientUiOperatorResolverGuardStub));
        FlushInstructionCache(
            GetCurrentProcess(), site, ClientUiOperatorResolverPrologue.size());
        DWORD ignored{};
        VirtualProtect(
            site, ClientUiOperatorResolverPrologue.size(),
            oldProtection, &ignored);
        if (!patched)
        {
            ClientUiOperatorResolverContinuation = nullptr;
            return ClientProcessPatchResult::UnexpectedBytes;
        }
        return alreadyPatched
            ? ClientProcessPatchResult::AlreadyPatched
            : ClientProcessPatchResult::Patched;
    }

    UnsignedFastfilePatchResult installUnsignedFastfilePatch()
    {
        const auto *const requested =
            std::getenv("OLMOD_ALLOW_UNSIGNED_FASTFILES");
        if (!requested || std::string_view(requested) != "1")
            return UnsignedFastfilePatchResult::NotRequested;

        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return UnsignedFastfilePatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return UnsignedFastfilePatchResult::UnsupportedHost;

        auto *const site = module + UnsignedFastfileVerificationRva;
        const auto alreadyPatched = std::ranges::equal(
            std::span<const std::uint8_t>(
                site, UnsignedFastfileVerification.size()),
            UnsignedFastfileVerificationReplacement);
        DWORD oldProtection{};
        if (!VirtualProtect(
                site, UnsignedFastfileVerification.size(),
                PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            return UnsignedFastfilePatchResult::ProtectionFailed;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto patched = patchUnsignedFastfileVerificationBuffer(image);
        FlushInstructionCache(
            GetCurrentProcess(), site,
            UnsignedFastfileVerification.size());
        DWORD ignored{};
        VirtualProtect(
            site, UnsignedFastfileVerification.size(),
            oldProtection, &ignored);
        if (!patched)
            return UnsignedFastfilePatchResult::UnexpectedBytes;
        return alreadyPatched
            ? UnsignedFastfilePatchResult::AlreadyPatched
            : UnsignedFastfilePatchResult::Patched;
    }

    ClientProcessPatchResult installClientProcessPatches()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return ClientProcessPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientProcessPatchResult::UnsupportedHost;

        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto state = inspectExecutionStateCall(image);
        if (state == ExecutionStateCallState::Patched)
            return ClientProcessPatchResult::AlreadyPatched;
        if (state != ExecutionStateCallState::Original)
            return ClientProcessPatchResult::UnexpectedBytes;
        if (!executionStateImportMatches(module, image.size()))
            return ClientProcessPatchResult::UnexpectedTarget;

        auto *const call = module + ExecutionStateCallRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                call,
                ExecutionStateCall.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            return ClientProcessPatchResult::ProtectionFailed;
        }
        std::ranges::copy(ExecutionStateReplacement, call);
        FlushInstructionCache(
            GetCurrentProcess(), call, ExecutionStateCall.size());
        DWORD ignored{};
        VirtualProtect(
            call, ExecutionStateCall.size(), oldProtection, &ignored);
        return ClientProcessPatchResult::Patched;
    }

    // sub_5E3550 on out.exe: `a1 == onboardCharacterID || (a1 > 0 && sub_80A5E0(a1))`,
    // the predicate that lets sub_5E3760 report an item owned when the inventory hash does
    // not have it. Image base 0x400000, so RVA 0x1E3550.
    constexpr std::size_t UnlockAllPredicateRva = 0x1E3550;

    // mov al, 1 ; ret.  The original opens with `push ecx` and closes `pop ecx ; ret`, so
    // returning before the push leaves the stack exactly as the caller left it -- and the
    // function's own success path is literally `b0 01 59 c3`, the same AL.
    constexpr std::array<std::uint8_t, 3> UnlockAllReplacement{ 0xB0, 0x01, 0xC3 };

    // THE GUARD SKIPS THE RELOCATED OPERANDS. Byte 4..7 is the address of the
    // "onboardCharacterID" string and 9..12 a call displacement; both move when the image
    // is rebased, so a signature that included them would fail on a perfectly good client
    // and, worse, could match somewhere else after a rebase. Only the fixed opcodes and
    // the distinctive `cmp esi,eax / jnz / mov al,1 / pop ecx / ret` tail are checked.
    struct UnlockAllSignatureByte { std::size_t offset; std::uint8_t value; };
    constexpr std::array<UnlockAllSignatureByte, 15> UnlockAllSignature{ {
        { 0, 0x51 }, { 1, 0x6A }, { 2, 0x00 }, { 3, 0x68 },
        { 8, 0xE8 },
        { 13, 0x83 }, { 14, 0xC4 }, { 15, 0x08 },
        { 16, 0x3B }, { 17, 0xF0 },
        { 18, 0x75 }, { 19, 0x04 },
        { 20, 0xB0 }, { 21, 0x01 }, { 22, 0x59 },
    } };

    UnlockAllPatchResult installUnlockAllPatch()
    {
        const auto *const requested = std::getenv("OLMOD_UNLOCK_ALL");
        if (!requested || *requested != '1')
            return UnlockAllPatchResult::NotRequested;

        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return UnlockAllPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return UnlockAllPatchResult::UnsupportedHost;
        if (UnlockAllPredicateRva + 24 >= nt->OptionalHeader.SizeOfImage)
            return UnlockAllPatchResult::UnsupportedHost;

        auto *const predicate = module + UnlockAllPredicateRva;

        if (std::ranges::equal(
                std::span(predicate, UnlockAllReplacement.size()),
                UnlockAllReplacement))
        {
            return UnlockAllPatchResult::AlreadyPatched;
        }

        for (const auto &[offset, value] : UnlockAllSignature)
        {
            if (predicate[offset] != value)
                return UnlockAllPatchResult::UnexpectedBytes;
        }

        DWORD oldProtection{};
        if (!VirtualProtect(
                predicate,
                UnlockAllReplacement.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            return UnlockAllPatchResult::ProtectionFailed;
        }
        std::ranges::copy(UnlockAllReplacement, predicate);
        FlushInstructionCache(
            GetCurrentProcess(), predicate, UnlockAllReplacement.size());
        DWORD ignored{};
        VirtualProtect(
            predicate, UnlockAllReplacement.size(), oldProtection, &ignored);
        return UnlockAllPatchResult::Patched;
    }

    const char *unlockAllPatchResultName(const UnlockAllPatchResult result)
    {
        switch (result)
        {
        case UnlockAllPatchResult::NotRequested:   return "not requested";
        case UnlockAllPatchResult::Patched:        return "patched";
        case UnlockAllPatchResult::AlreadyPatched: return "already patched";
        case UnlockAllPatchResult::UnsupportedHost: return "unsupported host";
        case UnlockAllPatchResult::UnexpectedBytes: return "UNEXPECTED BYTES -- not this build";
        case UnlockAllPatchResult::ProtectionFailed: return "VirtualProtect failed";
        }
        return "unknown";
    }

    // players/config_mp.cfg IN PLAIN TEXT. Both sites are the tail of an inlined strcmp
    // against "config_mp.cfg"; flipping 0x75 (jnz) to 0xEB (jmp) takes the branch every
    // time, so the write's re-encrypt pass and the read's decrypt are both skipped. The
    // displacement byte is left alone, so each patch is ONE byte and the jump target
    // stays the compiler's own.
    constexpr std::size_t ConfigWriteEncryptGateRva = 0xFDBCC;
    constexpr std::size_t ConfigReadDecryptGateRva = 0xF3119;
    constexpr std::array<std::uint8_t, 2> ConfigWriteGateOriginal{ 0x75, 0x6E };
    constexpr std::array<std::uint8_t, 2> ConfigWriteGatePatched{ 0xEB, 0x6E };
    constexpr std::array<std::uint8_t, 2> ConfigReadGateOriginal{ 0x75, 0x34 };
    constexpr std::array<std::uint8_t, 2> ConfigReadGatePatched{ 0xEB, 0x34 };

    PlaintextConfigPatchResult installPlaintextConfigPatch()
    {
        // ON BY DEFAULT, AND THE REASON IS A TRAP RATHER THAN A PREFERENCE.
        //
        // Once a client has written players/config_mp.cfg as plain text, a LATER launch
        // WITHOUT this patch decrypts it, gets garbage, fails the "starts with //" check at
        // 0x004F3144, and silently ignores the whole file -- so every bind, the sensitivity
        // and the fov revert to defaults and are then overwritten with an encrypted file of
        // defaults. Leaving the patch opt-in means one forgotten environment variable costs
        // a player their settings, with no error anywhere.
        //
        // Default-on removes that asymmetry: the patched client reads both forms sensibly
        // (a plaintext file directly, an old encrypted one discarded exactly once), and
        // OLMOD_PLAINTEXT_CONFIG=0 is there for anyone who wants the stock behaviour back.
        const auto *const requested = std::getenv("OLMOD_PLAINTEXT_CONFIG");
        if (requested && *requested == '0')
            return PlaintextConfigPatchResult::NotRequested;

        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return PlaintextConfigPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return PlaintextConfigPatchResult::UnsupportedHost;
        const auto imageSize = nt->OptionalHeader.SizeOfImage;
        if (ConfigWriteEncryptGateRva + 2 > imageSize ||
            ConfigReadDecryptGateRva + 2 > imageSize)
        {
            return PlaintextConfigPatchResult::UnsupportedHost;
        }

        auto *const writeGate = module + ConfigWriteEncryptGateRva;
        auto *const readGate = module + ConfigReadDecryptGateRva;
        const auto matches = [](const std::uint8_t *at,
                                const std::array<std::uint8_t, 2> &want) {
            return std::equal(want.begin(), want.end(), at);
        };

        if (matches(writeGate, ConfigWriteGatePatched) &&
            matches(readGate, ConfigReadGatePatched))
        {
            return PlaintextConfigPatchResult::AlreadyPatched;
        }
        // BOTH OR NEITHER. Patching only the writer leaves plaintext on disk that the
        // reader would try to decrypt; patching only the reader leaves an encrypted file
        // being executed. A half-applied pair is worse than none, so refuse unless both
        // sites are exactly the bytes they were read from.
        if (!matches(writeGate, ConfigWriteGateOriginal) ||
            !matches(readGate, ConfigReadGateOriginal))
        {
            return PlaintextConfigPatchResult::UnexpectedBytes;
        }

        for (auto *const site : { writeGate, readGate })
        {
            DWORD oldProtection{};
            if (!VirtualProtect(site, 2, PAGE_EXECUTE_READWRITE, &oldProtection))
                return PlaintextConfigPatchResult::ProtectionFailed;
            *site = 0xEB;
            FlushInstructionCache(GetCurrentProcess(), site, 2);
            DWORD ignored{};
            VirtualProtect(site, 2, oldProtection, &ignored);
        }
        return PlaintextConfigPatchResult::Patched;
    }

    const char *plaintextConfigPatchResultName(
        const PlaintextConfigPatchResult result)
    {
        switch (result)
        {
        case PlaintextConfigPatchResult::NotRequested:     return "not requested";
        case PlaintextConfigPatchResult::Patched:          return "patched";
        case PlaintextConfigPatchResult::AlreadyPatched:   return "already patched";
        case PlaintextConfigPatchResult::UnexpectedBytes:  return "UNEXPECTED BYTES -- not this build, nothing written";
        case PlaintextConfigPatchResult::UnsupportedHost:  return "unsupported host";
        case PlaintextConfigPatchResult::ProtectionFailed: return "VirtualProtect failed";
        }
        return "unknown";
    }

    // `push 0C8h` supplying the MAX argument of com_maxfps' registration. Five bytes,
    // and only the imm32 at +1 is rewritten so the opcode and the stack effect are
    // untouched. The DEFAULT push at 0xFC40F is deliberately left alone.
    constexpr std::size_t MaxFpsCeilingPushRva = 0xFC408;
    constexpr std::array<std::uint8_t, 5> MaxFpsCeilingPushOriginal{
        0x68, 0xC8, 0x00, 0x00, 0x00,
    };

    MaxFpsCeilingPatchResult installMaxFpsCeilingPatch()
    {
        const auto *const requested = std::getenv("OLMOD_MAXFPS_CEILING");
        if (!requested || !*requested)
            return MaxFpsCeilingPatchResult::NotRequested;
        const auto ceiling = std::strtoul(requested, nullptr, 10);
        if (ceiling < 1 || ceiling > 10000)
            return MaxFpsCeilingPatchResult::NotRequested;

        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        if (!module)
            return MaxFpsCeilingPatchResult::UnsupportedHost;
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return MaxFpsCeilingPatchResult::UnsupportedHost;
        if (MaxFpsCeilingPushRva + MaxFpsCeilingPushOriginal.size() >
            nt->OptionalHeader.SizeOfImage)
        {
            return MaxFpsCeilingPatchResult::UnsupportedHost;
        }

        auto *const site = module + MaxFpsCeilingPushRva;
        const auto wanted = static_cast<std::uint32_t>(ceiling);
        std::uint32_t present{};
        std::memcpy(&present, site + 1, sizeof(present));
        if (site[0] == 0x68 && present == wanted)
            return MaxFpsCeilingPatchResult::AlreadyPatched;
        if (!std::equal(
                MaxFpsCeilingPushOriginal.begin(),
                MaxFpsCeilingPushOriginal.end(),
                site))
        {
            return MaxFpsCeilingPatchResult::UnexpectedBytes;
        }

        DWORD oldProtection{};
        if (!VirtualProtect(
                site,
                MaxFpsCeilingPushOriginal.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            return MaxFpsCeilingPatchResult::ProtectionFailed;
        }
        std::memcpy(site + 1, &wanted, sizeof(wanted));
        FlushInstructionCache(
            GetCurrentProcess(), site, MaxFpsCeilingPushOriginal.size());
        DWORD ignored{};
        VirtualProtect(
            site, MaxFpsCeilingPushOriginal.size(), oldProtection, &ignored);
        return MaxFpsCeilingPatchResult::Patched;
    }

    const char *maxFpsCeilingPatchResultName(
        const MaxFpsCeilingPatchResult result)
    {
        switch (result)
        {
        case MaxFpsCeilingPatchResult::NotRequested:     return "not requested";
        case MaxFpsCeilingPatchResult::Patched:          return "patched";
        case MaxFpsCeilingPatchResult::AlreadyPatched:   return "already patched";
        case MaxFpsCeilingPatchResult::UnexpectedBytes:  return "UNEXPECTED BYTES -- not this build, nothing written";
        case MaxFpsCeilingPatchResult::UnsupportedHost:  return "unsupported host";
        case MaxFpsCeilingPatchResult::ProtectionFailed: return "VirtualProtect failed";
        }
        return "unknown";
    }

    ClientRawInputPatchResult installClientRawInputPatch()
    {
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return ClientRawInputPatchResult::UnsupportedHost;
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        if (ClientMouseEventCallRva > image.size() ||
            ClientMouseEventCall.size() > image.size() - ClientMouseEventCallRva)
        {
            return ClientRawInputPatchResult::UnexpectedBytes;
        }

        const auto replacement = reinterpret_cast<std::uintptr_t>(
            &clientMouseEventRawInputStub);
        const auto imageBase = reinterpret_cast<std::uintptr_t>(module);
        const auto nextInstruction = imageBase + ClientMouseEventCallRva +
            ClientMouseEventCall.size();
        const auto displacement = static_cast<std::int32_t>(
            replacement - nextInstruction);
        std::array<std::uint8_t, 5> patched{ 0xE8 };
        std::memcpy(patched.data() + 1, &displacement, sizeof(displacement));
        const auto actual = image.subspan(
            ClientMouseEventCallRva, ClientMouseEventCall.size());
        if (std::ranges::equal(actual, patched))
            return ClientRawInputPatchResult::AlreadyPatched;
        if (!std::ranges::equal(actual, ClientMouseEventCall))
            return ClientRawInputPatchResult::UnexpectedBytes;

        OriginalClientMouseEvent = reinterpret_cast<ClientMouseEvent>(
            module + ClientMouseEventRva);
        auto *const call = module + ClientMouseEventCallRva;
        DWORD oldProtection{};
        if (!VirtualProtect(
                call,
                ClientMouseEventCall.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            return ClientRawInputPatchResult::ProtectionFailed;
        }
        std::ranges::copy(patched, call);
        FlushInstructionCache(
            GetCurrentProcess(), call, ClientMouseEventCall.size());
        DWORD ignored{};
        VirtualProtect(
            call, ClientMouseEventCall.size(), oldProtection, &ignored);
        return ClientRawInputPatchResult::Patched;
    }

    bool maintainClientRawInputWindow()
    {
        if (RawInputWindow)
            return true;
        auto *const module = reinterpret_cast<std::uint8_t *>(
            GetModuleHandleW(nullptr));
        const IMAGE_NT_HEADERS *nt{};
        if (!validHostImage(module, nt))
            return false;
        const auto window = *reinterpret_cast<HWND *>(
            module + ClientWindowHandleRva);
        if (!window || !IsWindow(window))
            return false;

        SetLastError(ERROR_SUCCESS);
        const auto previous = reinterpret_cast<WNDPROC>(SetWindowLongPtrA(
            window,
            GWLP_WNDPROC,
            reinterpret_cast<LONG_PTR>(&rawInputWindowProcedure)));
        if (!previous)
            return false;
        PreviousWindowProcedure = previous;

        RAWINPUTDEVICE device{
            .usUsagePage = 0x01,
            .usUsage = 0x02,
            .dwFlags = 0,
            .hwndTarget = window,
        };
        if (!RegisterRawInputDevices(&device, 1, sizeof(device)))
        {
            SetWindowLongPtrA(
                window, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(previous));
            PreviousWindowProcedure = nullptr;
            return false;
        }
        RawInputWindow = window;
        return true;
    }

    const char *clientProcessPatchResultName(
        const ClientProcessPatchResult result)
    {
        switch (result)
        {
        case ClientProcessPatchResult::Patched:
            return "patched";
        case ClientProcessPatchResult::AlreadyPatched:
            return "already_patched";
        case ClientProcessPatchResult::UnsupportedHost:
            return "unsupported_host";
        case ClientProcessPatchResult::UnexpectedBytes:
            return "unexpected_bytes";
        case ClientProcessPatchResult::UnexpectedTarget:
            return "unexpected_target";
        case ClientProcessPatchResult::ProtectionFailed:
            return "protection_failed";
        }
        return "unknown";
    }

    const char *unsignedFastfilePatchResultName(
        const UnsignedFastfilePatchResult result)
    {
        switch (result)
        {
        case UnsignedFastfilePatchResult::NotRequested:
            return "not_requested";
        case UnsignedFastfilePatchResult::Patched:
            return "patched";
        case UnsignedFastfilePatchResult::AlreadyPatched:
            return "already_patched";
        case UnsignedFastfilePatchResult::UnsupportedHost:
            return "unsupported_host";
        case UnsignedFastfilePatchResult::UnexpectedBytes:
            return "unexpected_bytes";
        case UnsignedFastfilePatchResult::ProtectionFailed:
            return "protection_failed";
        }
        return "unknown";
    }

    const char *clientRawInputPatchResultName(
        const ClientRawInputPatchResult result)
    {
        switch (result)
        {
        case ClientRawInputPatchResult::Patched:
            return "patched";
        case ClientRawInputPatchResult::AlreadyPatched:
            return "already_patched";
        case ClientRawInputPatchResult::UnsupportedHost:
            return "unsupported_host";
        case ClientRawInputPatchResult::UnexpectedBytes:
            return "unexpected_bytes";
        case ClientRawInputPatchResult::ProtectionFailed:
            return "protection_failed";
        }
        return "unknown";
    }

    const char *tclsMappingResultName(const TclsMappingResult result)
    {
        switch (result)
        {
        case TclsMappingResult::NotRequested:
            return "not_requested";
        case TclsMappingResult::AlreadyVisible:
            return "HELD (another process had it; we hold a handle so it cannot vanish)";
        case TclsMappingResult::Published:
            return "PUBLISHED from inside the client";
        case TclsMappingResult::BlobUnreadable:
            return "blob_unreadable";
        case TclsMappingResult::CreateFailed:
            return "create_failed";
        case TclsMappingResult::MapFailed:
            return "map_failed";
        }
        return "unknown";
    }

    namespace
    {
        // Held for the life of the process. Closing it would unpublish the name the moment
        // this function returned, which is the one thing that must not happen.
        HANDLE TclsMappingHandle = nullptr;

        std::string tclsMappingName()
        {
            return "TCLS_SHAREDMEMEMORY" + std::to_string(GetCurrentProcessId());
        }
    }

    TclsMappingResult publishTclsMapping()
    {
        if (TclsMappingHandle)
            return TclsMappingResult::Published;

        std::array<char, MAX_PATH> blobPath{};
        const auto pathSize = GetEnvironmentVariableA(
            "OLMOD_TCLS_BLOB", blobPath.data(), static_cast<DWORD>(blobPath.size()));

        if (!pathSize || pathSize >= blobPath.size())
            return TclsMappingResult::NotRequested;

        const auto name = tclsMappingName();

        // OPEN-OR-CREATE, AND HOLD THE HANDLE. NEVER JUST LOOK.
        //
        // The first version of this asked OpenFileMapping whether the name was there, closed
        // the handle, and returned AlreadyVisible without publishing anything. Measured
        // 2026-09-05, that is precisely what kept the bug alive:
        //
        //     19:12:42  tcls mapping ALREADY VISIBLE      <- from inside pid 364
        //     19:12:43  [P364] OpenFileMapping ... fail! Error code = 2
        //
        // Same process, same name, one second apart, ours succeeding and TenProxy's failing. A
        // named section dies when its LAST handle closes, and SampleLauncher disposes its handle
        // the moment its process poll stops seeing the client -- so the name existed while we
        // looked and was gone when TenProxy asked. Looking without holding is what made the
        // window; a diagnostic that releases the thing it is measuring changes the outcome.
        //
        // CreateFileMapping opens an existing name or makes a new one, and this process holds
        // that handle for its whole life. After this call the name cannot go away while the
        // client is running, whoever else lets go of it.
        const auto mapping = CreateFileMappingA(
            INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, 4096, name.c_str());

        if (!mapping)
            return TclsMappingResult::CreateFailed;

        const auto alreadyThere = GetLastError() == ERROR_ALREADY_EXISTS;

        // HOLDING SOMEBODY ELSE'S MAPPING IS NOT THE SAME AS IT BEING RIGHT.
        //
        // This used to keep the handle and leave the bytes alone, on the reasoning that whoever
        // made it had put the correct blob in. That is false the moment a STALE publisher is
        // still alive: SampleLauncher pre-publishes a window of 512 mappings and holds them for
        // its whole life, so a second run leaves the first run's mappings in the prefix. A new
        // client landing on one gets an OLD login blob, TenProxy reads stale credentials, and
        // the client never authenticates -- measured 2026-09-05, `tcls mapping HELD` on every
        // launch while the auth server saw nothing at all for twenty minutes.
        //
        // We have the blob on disk. Write it either way: ours is the one built for THIS run,
        // and overwriting a correct copy with an identical correct copy costs nothing.
        const auto alreadyHeld = alreadyThere;

        // Read the blob SampleLauncher composed -- a file crosses a boundary a named mapping
        // cannot, and it already knows how to compose one.
        const auto file = CreateFileA(
            blobPath.data(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);

        if (file == INVALID_HANDLE_VALUE)
        {
            TclsMappingHandle = mapping;
            return TclsMappingResult::BlobUnreadable;
        }

        std::array<std::uint8_t, 4096> blob{};
        DWORD read = 0;
        const auto ok = ReadFile(file, blob.data(), static_cast<DWORD>(blob.size()), &read, nullptr);
        CloseHandle(file);

        if (!ok || !read)
        {
            // KEEP THE HANDLE EVEN SO. An empty mapping under the right name is still better
            // than no name at all -- OpenFileMapping succeeds and TenProxy reads zeroes, which
            // fails somewhere later and more legibly than [100] before a socket is opened.
            TclsMappingHandle = mapping;
            return TclsMappingResult::BlobUnreadable;
        }

        const auto view = MapViewOfFile(mapping, FILE_MAP_WRITE, 0, 0, 4096);

        if (!view)
        {
            // HOLD IT ANYWAY. Closing here would delete the name and put us back in exactly the
            // state this function exists to prevent: a mapping that was there a moment ago.
            TclsMappingHandle = mapping;
            return TclsMappingResult::MapFailed;
        }

        std::memcpy(view, blob.data(), read);
        UnmapViewOfFile(view);

        TclsMappingHandle = mapping;
        return alreadyHeld ? TclsMappingResult::AlreadyVisible : TclsMappingResult::Published;
    }
}
