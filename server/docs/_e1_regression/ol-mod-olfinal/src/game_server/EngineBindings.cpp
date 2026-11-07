#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "EngineBindings.hpp"
#include <charconv>

#include "PlayerDataDef.hpp"
#include "../shared/ProcessRole.hpp"
#include "../shared/RuntimeLog.hpp"
#include "server_mp/sv_gamestate_mp.hpp"
#include "server_mp/sv_snapshot_mp.hpp"
#include "server_mp/sv_alpha_barrett_assets_mp.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <thread>
#include <limits>
#include <mutex>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        int captureNativeException(
            EXCEPTION_POINTERS *const exception,
            NativeExceptionDetails *const details) noexcept
        {
            if (exception && exception->ExceptionRecord && details)
            {
                const auto *const record = exception->ExceptionRecord;
                details->code = record->ExceptionCode;
                details->address = record->ExceptionAddress;
                if (record->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
                    record->NumberParameters >= 2)
                {
                    details->accessType = record->ExceptionInformation[0];
                    details->faultAddress = reinterpret_cast<const void *>(
                        record->ExceptionInformation[1]);
                }
#if defined(_M_IX86)
                if (const auto *const context = exception->ContextRecord)
                {
                    details->eax = context->Eax;
                    details->ebx = context->Ebx;
                    details->ecx = context->Ecx;
                    details->edx = context->Edx;
                    details->esi = context->Esi;
                    details->edi = context->Edi;
                    details->ebp = context->Ebp;
                    details->esp = context->Esp;
                    details->eip = context->Eip;
                }
#endif
            }
            return EXCEPTION_EXECUTE_HANDLER;
        }

        constexpr std::size_t NativeServerEntitySize = 0x2C8;
        constexpr std::uint32_t NativeServerEntityCapacity = 2046;
        constexpr std::uint32_t NativeServerDObjCapacity = 2048;
        // Bring-up only. BG_PlayerAnimation can run several times per server frame
        // (once for each admitted usercmd), and zombie gameplay changes the reported
        // lerp state on nearly every call. Formatting and synchronously writing those
        // transitions caused observable frame stalls even with the console hidden.
        constexpr bool NativeServerAnimationStateDiagnostics = false;
        // CODDIFF(1649370): THE DObj POOL STRIDE IS 0xD8, NOT 3.3.3.3's 0xCC. Every
        // inlined lookup in out.exe multiplies the map entry by 216: the allocator
        // sub_66BEE0 (`&unk_77E9720 + 216 * v5`), the predicate sub_74E160, and both
        // bulk walkers sub_66BFF0/sub_66C050. At 0xCC every DObj after index 0 was the
        // wrong object by 12*index bytes.
        constexpr std::size_t NativeServerDObjSize = 0xD8;
        std::atomic<std::byte *> ServerDObjEntityBase{};
        std::atomic<std::uint16_t *> ServerDObjMap{};
        std::atomic<std::uint8_t *> ServerDObjInUse{};
        std::atomic<std::uint32_t *> ServerDObjFreeCount{};
        std::atomic<std::byte *> ServerDObjPool{};
        std::atomic<void *> ServerDObjCreateTarget{};
        std::atomic<void *> ServerDObjGetTarget{};
        std::atomic<void *> DObjFreeTarget{};

        // OLMOD(native-fault-detail): an exception CODE alone cannot tell a
        // null WeaponDef string apart from Com_Error longjmp'ing on a thread
        // with no error frame, and those two want opposite fixes. Both read
        // 0xC0000005 and both come out of the same call. The FAULTING
        // INSTRUCTION separates them in one line: subtract the module base and
        // the RVA lands straight in IDA.
        struct NativeFault
        {
            std::uint32_t code;
            std::uint32_t address;    // ExceptionAddress, absolute
            std::uint32_t operation;  // 0 read, 1 write, 8 execute
            std::uint32_t target;     // the address it touched
        };

        int captureNativeFault(
            EXCEPTION_POINTERS *const pointers,
            NativeFault &fault) noexcept
        {
            if (!pointers || !pointers->ExceptionRecord)
                return EXCEPTION_EXECUTE_HANDLER;
            const auto *const record = pointers->ExceptionRecord;
            fault.code = record->ExceptionCode;
            fault.address =
                reinterpret_cast<std::uint32_t>(record->ExceptionAddress);
            if (record->NumberParameters >= 2)
            {
                fault.operation = static_cast<std::uint32_t>(
                    record->ExceptionInformation[0]);
                fault.target = static_cast<std::uint32_t>(
                    record->ExceptionInformation[1]);
            }
            return EXCEPTION_EXECUTE_HANDLER;
        }

        // OLMOD(silent-death-witness): __try is not enough. The dedicated
        // process died inside BG_AnimParseAnimScript with NOTHING in the log -
        // no exception code, no stage - which a __try cannot produce and so
        // cannot explain. A vectored handler runs BEFORE any SEH frame and
        // before anything can unwind or exit, so it gets to write the line even
        // when the process is about to disappear.
        //
        // It only WITNESSES: it returns EXCEPTION_CONTINUE_SEARCH so normal
        // handling is unchanged, and it filters to the codes worth a line so
        // that ordinary handled exceptions do not fill the log.
        std::atomic<std::uint8_t *> VectoredWitnessModule{};
        std::atomic<const char *> CurrentNativeStage{"none"};
        std::atomic<std::uint32_t> VectoredWitnessCount{};
        void *VectoredWitnessHandle{};

        // A local readability probe, because the file's readableSpan is defined
        // a couple of thousand lines further down and this runs before it.
        bool witnessCanRead(const void *const address, const std::size_t length)
        {
            MEMORY_BASIC_INFORMATION info{};
            if (!address || !VirtualQuery(address, &info, sizeof(info)))
                return false;
            if (info.State != MEM_COMMIT)
                return false;
            constexpr DWORD Readable = PAGE_READONLY | PAGE_READWRITE |
                PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                PAGE_EXECUTE_WRITECOPY;
            if (!(info.Protect & Readable) ||
                (info.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
            {
                return false;
            }
            const auto start = reinterpret_cast<std::uintptr_t>(info.BaseAddress);
            const auto end = start + info.RegionSize;
            const auto want = reinterpret_cast<std::uintptr_t>(address) + length;
            return want <= end;
        }

        // ARMED FROM TWO PLACES NOW. The dedicated arms it around native animation
        // init; the CLIENT arms it at startup, because the crash worth catching
        // (HANDOFF section 152w) happens in the client and a CODOL client that
        // crashes exits tidily with no dump -- the handler is the only thing that
        // runs before its own TopLevelExceptionFilter swallows the context.
        long __stdcall vectoredFaultWitness(EXCEPTION_POINTERS *pointers);

        void armVectoredFaultWitnessImpl(std::uint8_t *const module)
        {
            if (VectoredWitnessHandle)
                return;
            VectoredWitnessModule.store(module);
            VectoredWitnessHandle =
                AddVectoredExceptionHandler(1, vectoredFaultWitness);
            char armed[128]{};
            std::snprintf(
                armed, sizeof(armed),
                "native fault witness armed=%u module=0x%08X",
                VectoredWitnessHandle ? 1u : 0u,
                static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(module)));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, armed);
        }

        long __stdcall vectoredFaultWitness(EXCEPTION_POINTERS *const pointers)
        {
            if (!pointers || !pointers->ExceptionRecord)
                return EXCEPTION_CONTINUE_SEARCH;
            const auto *const record = pointers->ExceptionRecord;
            const auto code = record->ExceptionCode;
            const bool interesting =
                code == EXCEPTION_ACCESS_VIOLATION ||
                code == EXCEPTION_STACK_OVERFLOW ||
                code == EXCEPTION_ILLEGAL_INSTRUCTION ||
                code == EXCEPTION_PRIV_INSTRUCTION ||
                code == EXCEPTION_IN_PAGE_ERROR ||
                code == EXCEPTION_INT_DIVIDE_BY_ZERO;
            // Ten is enough to see a pattern and few enough that a fault inside
            // a loop cannot bury the rest of the log.
            if (!interesting || VectoredWitnessCount.fetch_add(1) >= 10)
                return EXCEPTION_CONTINUE_SEARCH;
            const auto *const module = VectoredWitnessModule.load();
            const auto address =
                reinterpret_cast<std::uintptr_t>(record->ExceptionAddress);
            const auto base = reinterpret_cast<std::uintptr_t>(module);
            char line[224]{};
            std::snprintf(
                line, sizeof(line),
                "native fault witness code=0x%08lX rva=0x%07X op=%u "
                "target=0x%08X thread=%lu stage=%s",
                static_cast<unsigned long>(code),
                static_cast<std::uint32_t>(
                    module && address >= base ? address - base : address),
                record->NumberParameters >= 2
                    ? static_cast<std::uint32_t>(record->ExceptionInformation[0])
                    : 0xFFFFFFFFu,
                record->NumberParameters >= 2
                    ? static_cast<std::uint32_t>(record->ExceptionInformation[1])
                    : 0u,
                GetCurrentThreadId(),
                // WHICH NATIVE STAGE. An RVA says where the engine died; it does not say
                // which of ol-mod's calls put it there, and every stage in clientThink
                // reaches the same shared BG code. The breadcrumb costs one atomic store
                // per native call and turns "0xC0000005 at 0x411310" into a named suspect.
                SV_CurrentNativeStage());
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);

            // THE RVA SAYS WHERE; THE REGISTERS SAY WHY. The zhunt load crash
            // (HANDOFF section 152w) dies at sub_59CC70+0x1A5 writing [edi+3ECh],
            // where edi is sub_53F5F0's return -- 0 when the record's type tag at
            // +0xF8 is neither 1 nor 2. Without edi and ebx in hand that is a
            // hypothesis; with them it is a reading.
            //
            // Hooking sub_53F5F0 or sub_59CC70 would answer the same question and
            // is NOT an option: both are per-frame, and a per-frame client hook
            // crashed three clients at once. A vectored handler costs nothing until
            // the fault actually happens.
            if (const auto *const context = pointers->ContextRecord)
            {
                char registers[224]{};
                std::snprintf(
                    registers, sizeof(registers),
                    "native fault registers eax=0x%08lX ebx=0x%08lX ecx=0x%08lX "
                    "edx=0x%08lX esi=0x%08lX edi=0x%08lX ebp=0x%08lX esp=0x%08lX",
                    context->Eax, context->Ebx, context->Ecx, context->Edx,
                    context->Esi, context->Edi, context->Ebp, context->Esp);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, registers);

                // Read the record ebx points at, guarded -- a handler that faults
                // while reporting a fault tells nobody anything. +0x194 is the
                // entity index sub_53F5F0 keys on and +0x1CC is the weapon index.
                std::uint32_t entityIndex{};
                std::uint32_t weaponIndex{};
                bool recordRead{};
                __try
                {
                    const auto *const record =
                        reinterpret_cast<const std::uint8_t *>(context->Ebx);
                    entityIndex =
                        *reinterpret_cast<const std::uint32_t *>(record + 0x194);
                    weaponIndex =
                        *reinterpret_cast<const std::uint16_t *>(record + 0x1CC);
                    recordRead = true;
                }
                __except (EXCEPTION_EXECUTE_HANDLER)
                {
                    recordRead = false;
                }
                char record[160]{};
                std::snprintf(
                    record, sizeof(record),
                    "native fault record readable=%u entityIndex=%lu weaponIndex=%lu",
                    recordRead ? 1u : 0u,
                    static_cast<unsigned long>(entityIndex),
                    static_cast<unsigned long>(weaponIndex));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, record);
            }
            // THE FAULTING INSTRUCTION IS NOT THE QUESTION - HOW WE GOT THERE
            // IS. 0x4888CC said the DB's load pump faulted; it did not say
            // which call reached it.
            //
            // AN EBP CHAIN IS THE WRONG INSTRUMENT HERE and was tried first:
            // the pump is FPO - `sub_4888B0` opens `push ecx; push esi` with no
            // `mov ebp, esp` at all - so EBP at the fault belongs to whatever
            // frame-pointer function ran last, and walking it produced three
            // plausible-looking addresses that were not on the path.
            //
            // So scan the raw stack instead. Every dword in the next kilobyte
            // that points into .text AND is preceded by a `call` is a return
            // address or a very good imitation of one; the E8/FF15/FF five- and
            // six-byte forms cover almost every call MSVC emits. This over-
            // reports - stale slots survive below ESP - so it is labelled a
            // SCAN, not a stack, and the order is address order, not call
            // order.
            if (const auto *const context = pointers->ContextRecord)
            {
                char frames[352]{};
                int written = std::snprintf(frames, sizeof(frames), "  stack scan");
                const auto limit = base + 0x0E5D6000;
                auto esp = static_cast<std::uintptr_t>(context->Esp);
                int found = 0;
                for (std::uintptr_t slot = esp; slot < esp + 0x400 && found < 14;
                     slot += 4)
                {
                    if (!witnessCanRead(
                            reinterpret_cast<const void *>(slot), sizeof(std::uintptr_t)))
                    {
                        break;
                    }
                    const auto value =
                        *reinterpret_cast<const std::uintptr_t *>(slot);
                    if (value < base + 0x1000 || value >= limit)
                        continue;
                    const auto *const before =
                        reinterpret_cast<const std::uint8_t *>(value);
                    if (!witnessCanRead(before - 6, 6))
                        continue;
                    const bool afterCall =
                        before[-5] == 0xE8 ||
                        (before[-6] == 0xFF && (before[-5] & 0x38) == 0x10) ||
                        (before[-2] == 0xFF && (before[-1] & 0xF8) == 0xD0);
                    if (!afterCall)
                        continue;
                    if (written < 0 ||
                        static_cast<std::size_t>(written) >= sizeof(frames))
                    {
                        break;
                    }
                    const auto added = std::snprintf(
                        frames + written, sizeof(frames) - written,
                        " 0x%07X",
                        static_cast<std::uint32_t>(value - base));
                    if (added > 0)
                        written += added;
                    ++found;
                }
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, frames);
            }
            return EXCEPTION_CONTINUE_SEARCH;
        }

        bool tryCallVoid(
            const std::uint8_t *const function,
            NativeFault &fault) noexcept
        {
            __try
            {
                reinterpret_cast<void(__cdecl *)()>(function)();
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        // OLMOD(weapon-registry-stages): the lookup and the register live
        // inside ONE native resolver call, so a fault in either surfaced
        // identically. Calling the lookup separately first splits them: if this
        // faults the table is corrupt, and if only the resolver faults the
        // REGISTRATION is what dies.
        bool tryWeaponLookup(
            void *const function,
            const char *const name,
            std::uint32_t &result,
            NativeFault &fault) noexcept
        {
            __try
            {
                result = reinterpret_cast<std::uint32_t(__cdecl *)(const char *)>(
                    function)(name);
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool tryWeaponResolve(
            void *const function,
            const char *const name,
            std::uint32_t &result,
            NativeFault &fault) noexcept
        {
            __try
            {
                result = reinterpret_cast<std::uint32_t(__cdecl *)(
                    const char *, void *)>(function)(name, nullptr);
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        const char *invokeConfigStringGet(
            void *const function,
            const std::uint32_t index) noexcept
        {
            // CODDIFF(1649370): the index goes in ESI. See EngineBindings.hpp.
            // ESI is callee-saved under cdecl and is an ARGUMENT here, so the
            // callee is free to clobber it - save it across the call.
            if (!function)
                return nullptr;
            const char *result{};
            __asm
            {
                push esi
                mov esi, index
                mov edx, function
                call edx
                mov result, eax
                pop esi
            }
            return result;
        }

        void *invokeServerDObjGet(
            void *const function,
            void *const entity) noexcept
        {
            if (!function || !entity)
                return nullptr;
            void *result{};
            __asm
            {
                mov eax, entity
                mov edx, function
                call edx
                mov result, eax
            }
            return result;
        }

        bool invokeCCSGetConstantString(
            void *const function,
            const std::uint32_t constantType,
            const std::uint32_t index,
            const char *&value) noexcept
        {
            if (!function)
                return false;
            std::uint32_t succeeded{};
            const char *resolved{};
            __try
            {
                __asm
                {
                    mov eax, constantType
                    mov ecx, index
                    lea edx, resolved
                    push edx
                    mov edx, function
                    call edx
                    add esp, 4
                    mov succeeded, eax
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            value = resolved;
            return succeeded != 0;
        }

        bool invokeDirectionToAngles(void *const function,
            const float *const direction, float *const output) noexcept
        {
            // CODREF(1649370): vectoangles 764C10, ESI=input, EDI=output;
            // no stack arguments. 764D20 is the signed-angle variant.
            __try
            {
                __asm
                {
                    mov esi, direction
                    mov edi, output
                    mov eax, function
                    call eax
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
        }

        bool tryLinkXAssetEntry(
            void *const function,
            const std::uint32_t type,
            void **const header,
            void *&entry,
            NativeFault &fault) noexcept
        {
            __try
            {
                entry = reinterpret_cast<void *(__cdecl *)(
                    std::uint32_t, void **)>(function)(type, header);
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool trySetXAssetEntryZone(
            void *const entry,
            const std::uint8_t zone,
            NativeFault &fault) noexcept
        {
            if (!entry || !zone)
                return false;
            __try
            {
                auto *const bytes = static_cast<std::uint8_t *>(entry);
                if (!bytes[16])
                    bytes[16] = zone;
                return bytes[16] != 0;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool tryInitializeGfxImage(
            void *const function,
            void *const image,
            NativeFault &fault) noexcept
        {
            __try
            {
                reinterpret_cast<void(__cdecl *)(void **, void *)>(function)(
                    reinterpret_cast<void **>(image), image);
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool tryInternScriptString(
            void *const function,
            const char *const value,
            std::uint16_t &result,
            NativeFault &fault) noexcept
        {
            __try
            {
                const auto interned =
                    reinterpret_cast<std::uint32_t(__cdecl *)(
                        const char *, std::uint32_t, std::uint32_t)>(function)(
                        value, 4, static_cast<std::uint32_t>(
                                      std::strlen(value) + 1));
                if (!interned ||
                    interned > std::numeric_limits<std::uint16_t>::max())
                {
                    return false;
                }
                result = static_cast<std::uint16_t>(interned);
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool tryQueueXModelStream(
            void *const function,
            void *const model,
            const std::uint8_t priority,
            NativeFault &fault) noexcept
        {
            __try
            {
                __asm
                {
                    mov esi, model
                    movzx eax, priority
                    push eax
                    mov eax, function
                    call eax
                    add esp, 4
                }
                return true;
            }
            __except (captureNativeFault(GetExceptionInformation(), fault))
            {
                return false;
            }
        }

        bool invokeEvaluateTrajectory(void *const function,
            const SvNativeTrajectory *const trajectory, const std::int32_t atTime,
            float *const output) noexcept
        {
            // CODREF(1649370): 410BD0, EAX=time, ECX=plain trajectory, EDI=out.
            // Callee's EAX result is incidental; all three coordinates are output.
            __try
            {
                __asm
                {
                    mov eax, atTime
                    mov ecx, trajectory
                    mov edi, output
                    mov edx, function
                    call edx
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
        }

        bool invokeDObjFree(
            void *const function,
            void *const dobj) noexcept
        {
            if (!function || !dobj)
                return false;
            __try
            {
                __asm
                {
                    mov esi, dobj
                    mov eax, function
                    call eax
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        void *__cdecl serverDObjGetAdapter(const std::int32_t entityNum)
        {
            const auto *const base = ServerDObjEntityBase.load(
                std::memory_order_acquire);
            if (!base || entityNum < 0 ||
                static_cast<std::uint32_t>(entityNum) >=
                    NativeServerEntityCapacity)
            {
                return nullptr;
            }
            // THE FUNCTION THIS USED TO CALL IS A PREDICATE ON THIS BUILD, NOT A GETTER.
            // ServerDObjGetRva 0x34E160 is sub_74E160 in out.exe, and it decompiles to
            //     v1 = word_77E7F20[(a1 - &unk_31437A0) / 712];
            //     return v1 && (&unk_77E9720 + 216 * v1) != 0;
            // -- a BOOL. It returned literally 1, which is non-null, so every caller sailed
            // past its null check and then failed on the first read through the "pointer".
            // The live log caught it as `dobj=1`.
            //
            // out.exe has no standalone getter to re-point at: every call site inlines the
            // same two lines (sub_4EC9E0 among them), which is very likely why a signature
            // port picked the predicate -- it is the only function shaped like one. So inline
            // it here too, from the map and pool this project already binds, and drop the RVA
            // dependency for this operation entirely. ServerDObjGetTarget stays bound because
            // other checks look for it; nothing reads it any more.
            static_cast<void>(base);
            auto *const map = ServerDObjMap.load(std::memory_order_acquire);
            auto *const pool = ServerDObjPool.load(std::memory_order_acquire);
            if (!map || !pool)
                return nullptr;
            const auto dobjIndex = map[entityNum];
            if (!dobjIndex || dobjIndex >= NativeServerDObjCapacity)
                return nullptr;
            return pool +
                static_cast<std::size_t>(dobjIndex) * NativeServerDObjSize;
        }

        void __cdecl serverDObjFreeAdapter(
            const std::int32_t entityNum,
            const std::int32_t)
        {
            auto *const map = ServerDObjMap.load(std::memory_order_acquire);
            auto *const inUse = ServerDObjInUse.load(std::memory_order_acquire);
            auto *const freeCount = ServerDObjFreeCount.load(
                std::memory_order_acquire);
            auto *const pool = ServerDObjPool.load(std::memory_order_acquire);
            auto *const freeDObj = DObjFreeTarget.load(
                std::memory_order_acquire);
            if (!map || !inUse || !freeCount || !pool || !freeDObj ||
                entityNum < 0 || static_cast<std::uint32_t>(entityNum) >=
                    NativeServerEntityCapacity)
            {
                return;
            }
            __try
            {
                const auto dobjIndex = map[entityNum];
                if (!dobjIndex || dobjIndex >= NativeServerDObjCapacity)
                    return;
                ++*freeCount;
                inUse[dobjIndex] = 0;
                map[entityNum] = 0;
                invokeDObjFree(
                    freeDObj,
                    pool + static_cast<std::size_t>(dobjIndex) *
                        NativeServerDObjSize);
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
            }
        }

        void *__cdecl serverDObjCreateAdapter(
            void *const models,
            const std::uint16_t modelCount,
            void *const tree,
            const std::int32_t entityNum,
            const std::int32_t,
            const std::int32_t,
            const std::int32_t)
        {
            auto *const function = ServerDObjCreateTarget.load(
                std::memory_order_acquire);
            if (!function || !models || !modelCount || entityNum < 0 ||
                static_cast<std::uint32_t>(entityNum) >=
                    NativeServerEntityCapacity)
            {
                return nullptr;
            }
            void *result{};
            __asm
            {
                mov eax, entityNum
                push tree
                movzx ecx, modelCount
                push ecx
                push models
                mov edx, function
                call edx
                add esp, 12
                mov result, eax
            }
            return result;
        }

        constexpr std::array<std::uint8_t, 5> ComFramePrefix{
            0x55, 0x8B, 0xEC, 0x56, 0x57,
        };
        constexpr std::array<std::uint8_t, 6> DBFindXAssetHeaderPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8,
        };
        constexpr std::array<std::uint8_t, 10> DBLinkXAssetEntryPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x24, 0x8B, 0x45, 0x0C, 0x8B,
        };
        constexpr std::array<std::uint8_t, 6> MsgInitPrefix{
            0x55, 0x8B, 0xEC, 0x57, 0x33, 0xFF,
        };
        constexpr std::array<std::uint8_t, 9> MsgWriteBitsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08, 0x83, 0x3F, 0x00,
        };
        constexpr std::array<std::uint8_t, 9> MsgWriteStringPrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x04, 0x04, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 9> LevelZoneLoadPrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x28, 0x0E, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 7> CollisionMapLoadPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x50, 0xA1,
        };
        constexpr std::array<std::uint8_t, 7> CollisionWorldLinkPrefix{
            0x68, 0x1C, 0x60, 0x00, 0x00, 0x6A, 0x00,
        };
        constexpr std::array<std::uint8_t, 8> CCSClearPrefix{
            0x56, 0x33, 0xF6, 0x68, 0x00, 0x7D, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 9> CCSInitializePrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x44, 0x02, 0x00, 0x00,
        };
        // Prefix guards stop before loader-relocated absolute operands. The
        // opcode and addressing form remain fixed while ASLR rewrites the
        // following image address.
        constexpr std::array<std::uint8_t, 6> CCSGetConstantStringPrefix{
            0x55, 0x8B, 0xEC, 0x8B, 0x04, 0xC5,
        };
        constexpr std::array<std::uint8_t, 9> TracePrefix{
            0x55, 0x8B, 0xEC, 0x8B, 0x45, 0x1C, 0x8B, 0x4D, 0x18,
        };
        constexpr std::array<std::uint8_t, 9> WorldTracePrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0xD8, 0x00, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 7> TransformedBrushModelTracePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x4C, 0xA1,
        };
        constexpr std::array<std::uint8_t, 9> TransformedCapsuleTracePrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x90, 0x00, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 7> CalcTraceExtentsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20, 0xA1,
        };
        constexpr std::array<std::uint8_t, 7> PointTraceToEntitiesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x2C, 0xA1,
        };
        constexpr std::array<std::uint8_t, 9> DObjGeomTracelinePartBitsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x18, 0x33, 0xC0, 0x89,
        };
        constexpr std::array<std::uint8_t, 9>
            DObjContentsTracelinePartBitsPrefix{
                0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x0C, 0x8B, 0x4D, 0x08,
            };
        // `push ebp; mov ebp,esp; and esp,-8; sub esp,364h`. Byte-identical to
        // 3.3.3.3's DObjTraceline at 0x00645DD0 for the whole prologue.
        // OLMOD(section-84): and READ BACK off out.exe at VA 0x007825F0
        // (DObjTracelineRva 0x3825F0) -- same nine bytes, same 0x364 frame.
        // The guard is what enforces it; this line records that it was looked
        // at on the host and not only inherited.
        constexpr std::array<std::uint8_t, 9> DObjTracelinePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x81, 0xEC, 0x64,
        };
        constexpr std::array<std::uint8_t, 9> DObjContentsTracelinePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x38, 0x8B, 0x4D, 0x18,
        };
        constexpr std::array<std::uint8_t, 7> PointTraceStaticModelsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x58, 0xA1,
        };
        constexpr std::array<std::uint8_t, 9> DObjCalcSkelPrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0xB0, 0x00, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 16> SVLinkEntityPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x3C, 0x53, 0x56, 0x8B, 0xF0, 0x8B, 0xCE, 0x81,
        };
        // Stop before loader-relocated absolute address operands.
        constexpr std::array<std::uint8_t, 9> SVUnlinkEntityPrefix{
            0xD9, 0xEE, 0x56, 0x8B, 0xF0, 0x8B, 0xCE, 0x81, 0xE9,
        };
        constexpr std::array<std::uint8_t, 10> SVTracePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x81, 0xEC, 0xCC, 0x00,
        };
        constexpr std::array<std::uint8_t, 9> BGGetPlayerEyePositionPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x14, 0x53, 0x8B, 0x5D,
        };
        constexpr std::array<std::uint8_t, 9> BulletEndposPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x14,
        };
        constexpr std::array<std::uint8_t, 12> ByteDirectionsPrefix{
            0x4F, 0x96, 0x06, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x44, 0xC4, 0x59, 0x3F,
        };
        constexpr std::array<std::uint8_t, 9> ViewMovementDamageKickPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x0C, 0x53, 0x8B, 0x5E,
        };
        constexpr std::array<std::uint8_t, 9> ViewMovementIdleAnglesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x0C,
        };
        constexpr std::array<std::uint8_t, 9> ViewMovementBobAnglesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x18, 0x53, 0x8B, 0x5D,
        };
        constexpr std::array<std::uint8_t, 9> ViewMovementAdsBobPrefix{
            0x55, 0x8B, 0xEC, 0xD9, 0xEE, 0x83, 0xEC, 0x14, 0x53,
        };
        constexpr std::array<std::uint8_t, 9> WeaponMovementBasePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x24, 0x53, 0x8B, 0x5D,
        };
        constexpr std::array<std::uint8_t, 9> WeaponMovementSwayPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x38, 0x53, 0x8B, 0x5D,
        };
        constexpr std::array<std::uint8_t, 9> WeaponMovementRecoilPrefix{
            0x55, 0x8B, 0xEC, 0x8B, 0x02, 0x83, 0xEC, 0x2C, 0xF6,
        };
        constexpr std::array<std::uint8_t, 9> WeaponMovementBobPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0xD9, 0xE8, 0x53,
        };
        constexpr std::array<std::uint8_t, 9> SetWeaponMovementAnglesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0xD9, 0xEE, 0x53,
        };
        // `push ebp; mov ebp,esp; sub esp,20h; push esi; mov esi,[ebp+8]`
        constexpr std::array<std::uint8_t, 9> AngleVectorsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20, 0x56, 0x8B, 0x75,
        };
        constexpr std::array<std::uint8_t, 9> AnglesToQuaternionPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x34, 0xD9, 0x46, 0x04,
        };
        constexpr std::array<std::uint8_t, 9> MatrixMultiplyPrefix{
            0x55, 0x8B, 0xEC, 0x8B, 0x4D, 0x08, 0xD9, 0x01, 0xD8,
        };
        constexpr std::array<std::uint8_t, 9> AxisToAnglesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x28, 0x56, 0x57, 0x8B,
        };
        constexpr std::array<std::uint8_t, 9> PmoveSinglePrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x64, 0x01, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 9> PMSetPitchValuesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x28, 0xA1, 0x40, 0xF2,
        };
        constexpr std::array<std::uint8_t, 7> PlayerStateToEntityStatePrefix{
            0x55, 0x8B, 0xEC, 0x53, 0x8B, 0x5D, 0x08,
        };
        constexpr std::array<std::uint8_t, 6> BGAnimScriptEventPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x15,
        };
        constexpr std::array<std::uint8_t, 9> BGFindAnimsPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x53, 0x56, 0x57, 0x8B, 0xF0,
        };
        constexpr std::array<std::uint8_t, 9> BGAnimParseAnimScriptPrefix{
            0x55, 0x8B, 0xEC, 0xB8, 0x10, 0x88, 0x00, 0x00, 0xE8,
        };
        constexpr std::array<std::uint8_t, 5> BGLoadAnimTreesPrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC,
        };
        constexpr std::array<std::uint8_t, 4> ScrCreateObjectPrefix{
            0x55, 0x8B, 0xEC, 0xA1,
        };
        constexpr std::array<std::uint8_t, 6> DBIsXAssetDefaultPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x45,
        };
        // sub_74AF50, NOT the per-tree worker sub_74AAF0 this used to name.
        // `mov ebx, [ebp+8]` at the end is the allocator argument; the anim
        // user arrives in EDI. The old prefix was
        //     0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x20, 0x8B, 0x15, 0x28
        // and it passed, because the worker is a real function too.
        constexpr std::array<std::uint8_t, 13> ScrPrecacheAnimTreesPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0xA1, 0x30, 0xF7, 0x27, 0x08, 0x53,
            0x8B, 0x5D, 0x08,
        };
        constexpr std::array<std::uint8_t, 7> BGFindAnimTreesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x1C, 0xA1,
        };
        constexpr std::array<std::uint8_t, 9> BGFinalizePlayerAnimsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x2C, 0x53, 0x56, 0x8B,
        };
        constexpr std::array<std::uint8_t, 11>
            NativeLerpFrameAccessorInitializePrefix{
                0x55, 0x8B, 0xEC, 0x8B, 0x4D, 0x0C, 0x53, 0x8B, 0x5D, 0x08, 0x56,
            };
        constexpr std::array<std::uint8_t, 9> BGPlayerAnimationPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x53, 0x8B, 0x5D, 0x0C, 0x56,
        };
        constexpr std::array<std::uint8_t, 8> BGUpdatePlayerDObjPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x81, 0xEC,
        };
        constexpr std::array<std::uint8_t, 7> WorldCharacterModelResolvePrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x0C, 0x85,
        };
        constexpr std::array<std::uint8_t, 12> MantleCreateAnimsPrefix{
            0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x44, 0x01, 0x00, 0x00, 0xA1, 0x40, 0xF2,
        };
        constexpr std::array<std::uint8_t, 9> HunkAllocXAnimPrefix{
            0x55, 0x8B, 0xEC, 0x5D, 0xE9, 0x07, 0x00, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 10> DObjFreePrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x86, 0xC0, 0x00, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 8> ServerDObjCreatePrefix{
            0x55, 0x8B, 0xEC, 0x53, 0x56, 0x57, 0x8B, 0xF0,
        };
        constexpr std::array<std::uint8_t, 3> ServerDObjGetSuffix{
            0x8B, 0xC8, 0xB8,
        };
        constexpr std::array<std::uint8_t, 6> WeaponLookupPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x8B, 0x4D,
        };
        constexpr std::array<std::uint8_t, 6> WeaponResolverPrefix{
            0x55, 0x8B, 0xEC, 0x56, 0x8B, 0x75,
        };
        constexpr std::array<std::uint8_t, 6> AttachmentLookupPrefix{
            0x55, 0x8B, 0xEC, 0x8B, 0x55, 0x08,
        };
        constexpr std::array<std::uint8_t, 6> WeaponRegistryResetPrefix{
            0x51, 0x68, 0x90, 0x1A, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 8> WeaponRegistryInitializePrefix{
            0x55, 0x8B, 0xEC, 0xB8, 0x64, 0x1F, 0x00, 0x00,
        };
        constexpr std::array<std::uint8_t, 6> ZoneLoadedPrefix{
            0x55, 0x8B, 0xEC, 0x53, 0x8B, 0x1D,
        };
        constexpr std::array<std::uint8_t, 7> WeaponSlotReadStagedPrefix{
            0x55, 0x8B, 0xEC, 0x8D, 0x04, 0x80, 0x80,
        };
        // CODDIFF(1649370): was 3.3.3.3's 55 8B EC 83 E4 F8 -- a stack-aligning
        // prologue this build's function does not have. sub_6B87C0 opens by reading
        // its cache directly:  mov eax, ds:0E567C0h / cmp eax, -1 / jnz short.
        //
        // Bytes 1..4 are a RELOCATED absolute operand. That would disqualify them from
        // a cross-build signature (the byte-signature relocation trap), and it does not
        // disqualify them here: this guard's whole job is to ask whether the image is
        // still the one the RVA was derived against, so pinning the operand makes it
        // stricter, not wronger.
        constexpr std::array<std::uint8_t, 10> CurrentCharacterGetPrefix{
            0xA1, 0xC0, 0x67, 0xE5, 0x00, 0x83, 0xF8, 0xFF, 0x75, 0x1F,
        };
        // sub_50FF30, the profile read. No relocated operand in the first nine bytes.
        constexpr std::array<std::uint8_t, 9> CharacterSlotGetPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x64,
        };
        constexpr std::array<std::uint8_t, 5> CharacterCurrentItemsCopyPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x57,
        };
        // sub_619AD0. Bytes 6..10 are the relocated /GS cookie address, pinned on purpose
        // for the same reason CurrentCharacterGetPrefix pins its operand: this guard asks
        // whether the image is still the one the RVA was derived against.
        constexpr std::array<std::uint8_t, 16> CharacterRecordFillDefaultsPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x44, 0xA1, 0x40,
            0xF2, 0xE3, 0x00, 0x33, 0xC5, 0x89, 0x45, 0xFC,
        };
        // sub_61B6C0, and this one guards itself: the `6A 2C` at bytes 12..13 is the
        // `push 0x2C` of its own opening memset, which is the ELEVEN-POINTER output size
        // this port depends on. A build whose selection-name array stopped being eleven
        // dwords would fail this guard on exactly the byte that says so.
        constexpr std::array<std::uint8_t, 16> CharacterRecordToSelectionNamesPrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08, 0x8B, 0x45,
            0x08, 0x53, 0x56, 0x57, 0x6A, 0x2C, 0x6A, 0x00,
        };
        constexpr std::array<std::uint8_t, 6> CharacterSelectionResolvePrefix{
            0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08,
        };
        constexpr std::array<std::uint8_t, 7> ConfigStringGetPrefix{
            0x55, 0x8B, 0xEC, 0x51, 0x81, 0xFE, 0xD9,
        };
        constexpr std::uint32_t AssetTypeMapEnts = 19;
        // CODOL's zone table names this `addon_map_ents` at type 42. The
        // Wetwork zone carries its entity string here (asset
        // maps/mp/coop_training_mp_cargoship.mapents), while ordinary MP maps
        // keep theirs in type 19 beside the clipmap.
        constexpr std::uint32_t AssetTypeAddonMapEnts = 42;
        constexpr std::uint32_t AssetTypeFxMap = 20;
        constexpr std::uint32_t AssetTypeClipMapSp = 14;
        constexpr std::uint32_t AssetTypeClipMapMp = 15;
        constexpr std::uint32_t AssetTypeComWorld = 16;
        constexpr std::uint32_t AssetTypeXModel = 4;
        constexpr std::uint32_t AssetTypeSound = 11;
        constexpr std::uint32_t AssetTypeFx = 30;
        constexpr std::uint32_t ConstantStringTypeSoundAlias = 5;
        constexpr std::uint32_t AssetTypeStringTable = 37;
        constexpr std::uint32_t AssetTypeRawFile = 36;
        constexpr std::size_t MaximumMapEntityChars = 16 * 1024 * 1024;
        // CODREF(fxglass): SETTLED (section 93) against every map the game ships, offline.
        // Section 71c could not settle either of these because the only map this project runs
        // has no glass at all -- `fxglass header map=mp_rust_long definitions=0 pieceLimit=0`.
        // It never needed a glass map to be RUN: the FxWorld is asset type 20 in the map's own
        // fastfile and all 975 fastfiles are on disk.
        // CODOL-main Tools/olfinal/fxglass-map-survey.py reads 37 of them and finds THREE exact
        // relations, each holding on every map with glass (27 of the 37; the other ten are all
        // zero, mp_rust_long among them):
        //
        //     pieceWordCount == ceil(pieceLimit / 32)         37/37   the availability bitset
        //     pieceLimit     == initialPieceCount + 1024      27/27   <- the one that matters
        //     geometryLimit  == 8 * pieceLimit                37/37
        //
        // The second one means MaximumFxGlassPieceLimit IS NOT A FREE CONSTANT, the same way
        // section 59b's lastChanged width was not: the map compiler sizes the piece array as the
        // initial pieces plus a FIXED 1024 of headroom for the fragments breaking glass creates,
        // and 1024 is SvGlassPieceCount -- the same number out.exe's own sparse-list reader
        // hardcodes as its terminator (sub_447500 @0x447527: `i = BITS(11); 1024 ends it`).
        // So given the initialPieceCount check below, `pieceLimit <= 2048` FOLLOWS. It is not a
        // plausibility guess; it is exactly the largest value the other check permits, which is
        // why the static_assert ties them together rather than leaving two numbers to drift.
        //
        // The observed maxima, for whoever has to judge a future map:
        //     definitionCount   41   mp_terminal_cls      pieceLimit   1903   mp_conflict
        //     initialPieceCount 879  mp_conflict          cellCount    203    mp_battlecity
        // 1903 is 93% of this bound and 879 is 86% of SvGlassPieceCount, so neither has much
        // slack left -- if a map is ever refused here, these are the numbers to print first.
        // definitionCount has no relation of its own; 1024 against an observed 41 is a plain
        // plausibility bound and is left loose on purpose (section 51h: do not tighten one).
        constexpr std::uint32_t MaximumFxGlassDefinitionCount = 1024;
        constexpr std::uint32_t MaximumFxGlassPieceLimit = 2048;
        static_assert(MaximumFxGlassPieceLimit == 2 * SvGlassPieceCount);
        // CODDIFF(1649370): 0x94D40 was 3.3.3.3's. CL_ParseGamestate hands
        // BG_FindAnims its context directly and says what the offset is:
        //     454c63  mov eax, dword_827F730
        //     454c68  add eax, 0ACE70h
        //     454c77  call sub_404D80
        // and sub_404D80 fills a1+4, a1+8, a1+12, a1+16 from there.
        constexpr std::size_t AnimTreeContextOffset = 0xACE70;
        // The HANDLE is twelve bytes below the context, and it is a different
        // thing: BG_FinalizePlayerAnims reads a pointer there and dereferences
        // it for the animation count.
        //     v1 = *((_DWORD *)dword_827F734 + 177049);   // +0xACE64
        //     *((_DWORD *)dword_827F734 + 26624) = *v1;   // +0x1A000
        // Checking the context slot for "is the anim tree there" was checking
        // a word nothing writes.
        constexpr std::size_t AnimTreeHandleOffset = 0xACE64;
        // Both of these are offsets into the SAME installed anim-condition
        // block, and neither is this project's to choose: the engine derives
        // the characterInfo array at +0xAF350 and reads the anim tree at
        // +0xACE64/+0xACE70 whatever we do. On 3.3.3.3 the array sat BELOW the
        // anim tree; on this build it sits ABOVE it, so the assert is written
        // in the direction this build's addresses actually run. What matters
        // either way is only that the two do not overlap.
        static_assert(
            AnimTreeContextOffset + 4 * sizeof(std::uint32_t) <=
                EngineBindings::ServerCharacterInfoBaseOffset,
            "the anim tree handle and context must not run into the derived "
            "characterInfo array inside the shared anim-condition storage");
        constexpr std::size_t CharacterInfoModelNameOffset = 24;
        constexpr std::size_t CharacterInfoAttachmentNamesOffset = 32;
        constexpr std::size_t CharacterInfoAttachmentTagNamesOffset = 72;
        // CODDIFF(1649370): BOTH OF THESE WERE 3.3.3.3's AND BOTH ARE +100 HERE, which is
        // the same +0x64 shift sv_native_characterinfo_mp.cpp already derived for
        // 0x1F4..0x208 -> 0x258..0x26C. These two sat in the same struct and were missed.
        //
        // Read straight off BG_UpdatePlayerDObj (sub_40AB30, RVA 0x00AB30), where a5 is the
        // characterInfo:
        //   *(_DWORD *)(a5 + 660)  is the REBUILD flag -- the early-out is
        //       `if (*(a5 + 924) == v12 && !*(a5 + 660)) return 0;`
        //       and the function clears it on the way out with `v18[165] = 0` (165*4 = 660).
        //   *(_DWORD *)(a5 + 900)  is the ANIM TREE -- it is loaded into v46 and passed as
        //       the third argument of the DObj create, which is `tree` in this project's own
        //       serverDObjCreateAdapter signature.
        // Neither 560 nor 800 appears anywhere in that function.
        //
        // The consequence of the first one is not cosmetic: writing the dirty flag to 560
        // left the engine's flag at 660 clear, so BG_UpdatePlayerDObj took its early-out and
        // never rebuilt the player DObj at all.
        constexpr std::size_t CharacterInfoDObjDirtyOffset = 660;
        constexpr std::size_t CharacterInfoAnimTreeOffset = 900;
        constexpr std::size_t WorldCharacterModelEntrySize = 16;
        constexpr char EmptyCharacterModelName[] = "";
        constexpr std::size_t DObjModelCountOffset = 9;
        constexpr std::size_t DObjBoneCountOffset = 10;
        constexpr std::size_t DObjModelHideMaskOffset = 12;
        constexpr std::size_t DObjSkelStateOffset = 20;
        constexpr std::size_t DObjSkelStateSize = 136;
        constexpr std::size_t DObjSkelPartBitsOffset = 116;
        constexpr std::size_t DObjSkelEpochOffset = 148;
        constexpr std::size_t DObjPoseMatricesOffset = 152;
        constexpr std::size_t DObjBoneHideBitsOffset = 160;
        constexpr std::size_t DObjModelPointersOffset = 192;
        // CONFIRMED AGAINST out.exe, AND IT IS A VECTOR. The DObj constructor
        // sub_781960 writes THREE floats here and nothing else touches them:
        //     *(float *)(dobj + 200) = 1.0;
        //     *(float *)(dobj + 204) = 1.0;
        //     *(float *)(dobj + 208) = 1.0;
        //     *(_DWORD *)(dobj + 212) = -1;
        // so 200 is the X component of a per-axis model scale, not a scalar, and
        // the object reaches 216 -- which independently confirms the 0xD8 stride,
        // because 0xCC would have cut off both 208 and 212. Writing only X while
        // Y and Z keep whatever they hold is a non-uniform scale: harmless while
        // every modelScale is 1.0, and a stretched model the moment one is not.
        //
        // The same function confirms two more of this block by construction:
        // memset(dobj + 20, 0, 0x88) is exactly DObjSkelStateOffset 20 and
        // DObjSkelStateSize 136, and it zeroes 160..188 across DObjBoneHideBitsOffset.
        constexpr std::size_t DObjScaleOffset = 200;
        constexpr std::size_t DObjScaleComponentCount = 3;
        struct NativeDObjModel
        {
            void *model{};
            std::uint16_t boneName{};
            std::uint8_t ignoreCollision{};
            std::uint8_t pad{};
            std::array<std::byte, 36> reserved{};
        };
        static_assert(sizeof(NativeDObjModel) == 44);
        constexpr std::size_t XModelBoneCountOffset = 4;
        constexpr std::size_t XModelNameOffset = 0;
        constexpr std::size_t XModelBoneClassificationOffset = 60;
        constexpr std::size_t XModelGeometryOffset = 312;
        constexpr std::size_t XModelGeometryEntrySize = 28;
        constexpr std::size_t XModelGeometryPointerOffset = 24;
        // CODREF(bg_update_player_dobj): THE SHARED ANIMATION CLOCK. Two
        // millisecond times live in the anim-condition block, and every native
        // animation call reads them. Neither is written anywhere in the image
        // through the anim-condition base, which is why a displacement scan on
        // that base finds only reads and concludes "nothing sets these" - CODOL
        // writes them through the OUTER structure the block is embedded in, at
        // `lea eax, [ebx + 0xC7088]` (VA 0x00448351, 0x005249C2), so the same
        // words are `outer + 0x15DE60` and `outer + 0x15DE64`:
        //
        //   VA 0x00524931  mov [esi+0x000AE4C8], edi   <- the frame time
        //   VA 0x00524937  mov [esi+0x0015DE60], edi   <- mirrored here
        //   VA 0x00524A43  mov ecx, [edi+0x3574]       <- the snapshot time
        //   VA 0x00524A49  mov [edi+0x0015DE64], ecx   <- mirrored here
        //
        // What each one drives, read from the consumers:
        //   +0x96DD8  deadlines. BG_SetLerpFrameAnimation VA 0x00409D1B writes
        //             characterInfo +0x338 = now + 400, and VA 0x00409E12 reads
        //             the remainder back as `+0x338 - now`. PmoveSingle
        //             VA 0x00419FD8/0x00419FF8 compares playerState +0x33C
        //             against it with jge/jle.
        //   +0x96DDC  the lerp-frame advance. VA 0x0040A302 SKIPS the entire
        //             advance when it equals lerpFrame +0x38, VA 0x0040A385
        //             takes `now - lerpFrame+0x38` as the elapsed milliseconds,
        //             and VA 0x0040A3B5 stores it back into lerpFrame +0x38.
        //
        // This project owns the block on the server and zero-fills it, so both
        // clocks read 0 forever. The +0x96DDC consumer then compares 0 against
        // a lerp frame whose time is also 0, takes its skip branch on every
        // frame after the first, and no animation ever advances: the posed
        // skeleton freezes on whichever animation was latched last. That is the
        // per-life hitbox fault - full height on life one, and stuck on the
        // animation the respawn happened to publish for every life after.
        //
        // CODDIFF(bg_update_player_dobj): BO1 and Ghosts reach these times
        // through their own bgs/level globals; nothing of either layout is
        // reused. Only the two CODOL offsets and the server's own clock.
        // CODDIFF(1649370): THIS WHOLE BLOCK IS RELOCATED BY +0x18530 AND WAS NOT PORTED.
        // The shared anim-condition storage moved its derived characterInfo array from
        // 3.3.3.3's 0x96E20 to this build's 0xAF350 -- a delta of 0x18530, already carried
        // by ServerCharacterInfoBaseOffset. Everything that lives just BEFORE that array
        // moved with it, and these nine did not.
        //
        // Four of them are confirmed directly against out.exe, not inferred from the delta.
        // BG_UpdatePlayerDObj (sub_40AB30) reaches the callbacks through the storage base:
        //     (*((void (__cdecl **)(...))dword_827F730 + 179402))(...)   7 args -> CREATE
        //     (*((... **)dword_827F730 + 179403))(&v53, v39, a5, a2)     4 args -> APPEND
        //     (*((... **)dword_827F730 + 179404))(*(_DWORD *)a4, a2)     2 args -> FREE
        // which are byte offsets 717608, 717612 and 717616 -- exactly 0x96DF8, 0x96DFC and
        // 0x96E00 plus 0x18530. The argument counts match this project's own adapter
        // signatures. And both that function and sub_407EA0 test
        //     *((_BYTE *)dword_827F730 + 717596)
        // which is 0x96DEC + 0x18530, the asymmetric anim-script flag.
        //
        // The old values were wrong twice over. 0x96DD8..0x96E04 all sit BELOW
        // AnimTreeContextOffset 0xACE70, and BG_FindAnimTrees memsets 0xACE70 bytes from
        // the base -- so the callbacks this project installed were not merely in the wrong
        // place, they were inside the region the engine zeroes on every anim-tree load.
        // The corrected offsets sit above it, between the anim array and the characterInfo
        // array, which is where a clock and a callback table belong.
        constexpr std::size_t AnimFrameTimeOffset = 0xAF308;
        constexpr std::size_t AnimSnapshotTimeOffset = 0xAF30C;
        constexpr std::size_t AnimUserOffset = 0xAF314;
        constexpr std::size_t AnimTreeMaskOffset = 0xAF318;
        constexpr std::size_t AsymmetricAnimScriptFlagOffset = 0xAF31C;
        // CODDIFF(1649370): THIS TABLE WAS 3.3.3.3's TWICE OVER -- WRONG OFFSETS AND
        // WRONG FUNCTIONS -- AND IT IS AN ARRAY INITIALISER, WHICH IS WHY EVERY PORTER
        // AND EVERY AUDITOR WALKED PAST IT. The four named offsets right below were
        // ported to this build's 0xAF3xx long ago and the ten pairs feeding the same
        // block were not, so the loop wrote ten pointers to 0x96DF0..0x96E1C, which
        // NOTHING on out.exe reads (a displacement scan of .text finds zero consumers
        // for nine of those ten offsets and 48 for 0xAF350), and left every slot the
        // engine actually reads at zero.
        //
        // THAT IS THE `BG_UpdatePlayerDObj` FAULT, AND IT WAS NEVER AN ABI MISMATCH.
        // sub_40AB30 reaches its callbacks as `mov edx, [ecx + 0xAF324]; push eax;
        // call edx` at 0x0040AD1F, with no null check -- so a zero slot is CALLED, and
        // the witness reports `code=0xC0000005 op=8 target=0x00000000`. op 8 is a DEP
        // violation: the CPU tried to EXECUTE address zero. Only 0xAF32C is guarded
        // (`test eax, eax; je` at 0x0040AE28), which is why the one slot this project
        // deliberately nulls was never the one that crashed.
        //
        // Read off out.exe's OWN INSTALLER, which is the same function on both builds
        // and matches instruction for instruction, in the same order, differing only in
        // relocated globals:
        //     3.3.3.3 0x00445924   mov [edi+0x15DE7C], 0x004453E0
        //     out.exe 0x00454750   mov [ebx+0x180C24], 0x00453420
        // and a second copy of the same block at 0x00448140 / 0x004565E0. Both builds
        // install through the OUTER structure the anim-condition block is embedded in,
        // so each offset here is `outer - 0xC7088` on 3.3.3.3 and `outer - 0xD1900` on
        // out.exe -- the two deltas this file's storage comment already states. The
        // outer table itself moved by a flat 0x22DA8, and (0x22DA8 - 0xD1900 + 0xC7088)
        // is exactly the +0x18530 shift ServerCharacterInfoBaseOffset already carries.
        // Two independent measurements landing on the same delta for all ten slots.
        //
        // THREE MORE CONFIRMATIONS, none of which shares a step with that arithmetic:
        //   * entries 6 and 7 come out at RVA 0x368220, which is HunkAllocXAnimRva --
        //     already bound and prefix-guarded here from a different derivation.
        //   * the get-DObj entry comes out at 0x053600, and its body is
        //     `movzx eax, word [eax*2 + 0x7855720]` against 3.3.3.3's
        //     `[eax*2 + 0x2EF4858]` -- the same client DObj map sub_53DF40 indexes at
        //     0x0053DFC9 to find the DObj it hands BG_UpdatePlayerDObj.
        //   * the CONSUMER COUNT per slot matches across builds: 2/1/1/2/3/1/1/1 for
        //     0x96DF4..0x96E1C against 0xAF324..0xAF34C.
        constexpr std::array<std::pair<std::size_t, std::size_t>, 10>
            ServerAnimationCallbackRvas{
                std::pair{ std::size_t{ 0xAF320 }, std::size_t{ 0x053430 } },
                std::pair{ std::size_t{ 0xAF324 }, std::size_t{ 0x053420 } },
                std::pair{ std::size_t{ 0xAF328 }, std::size_t{ 0x0535B0 } },
                std::pair{ std::size_t{ 0xAF32C }, std::size_t{ 0x0534A0 } },
                std::pair{ std::size_t{ 0xAF330 }, std::size_t{ 0x26BF60 } },
                std::pair{ std::size_t{ 0xAF334 }, std::size_t{ 0x053600 } },
                std::pair{ std::size_t{ 0xAF338 }, std::size_t{ 0x368220 } },
                std::pair{ std::size_t{ 0xAF33C }, std::size_t{ 0x368220 } },
                std::pair{ std::size_t{ 0xAF348 }, std::size_t{ 0x049030 } },
                std::pair{ std::size_t{ 0xAF34C }, std::size_t{ 0x048FF0 } },
            };
        constexpr std::size_t ServerCreateDObjCallbackOffset = 0xAF328;
        constexpr std::size_t ServerAppendWeaponModelCallbackOffset = 0xAF32C;
        constexpr std::size_t ServerFreeDObjCallbackOffset = 0xAF330;
        constexpr std::size_t ServerGetDObjCallbackOffset = 0xAF334;
        // The four named offsets and the table are the SAME four slots, and they drifted
        // apart for four sections without anything noticing. Tie them together so the
        // next half-port cannot compile: this is an `==` against the thing that fixes
        // it, not a bound that every smaller value satisfies.
        static_assert(
            ServerCreateDObjCallbackOffset == ServerAnimationCallbackRvas[2].first &&
            ServerAppendWeaponModelCallbackOffset ==
                ServerAnimationCallbackRvas[3].first &&
            ServerFreeDObjCallbackOffset == ServerAnimationCallbackRvas[4].first &&
            ServerGetDObjCallbackOffset == ServerAnimationCallbackRvas[5].first,
            "the stock callback table and the four adapter slots must name the same "
            "four offsets -- they were 0x96DF8..0x96E04 and 0xAF328..0xAF334 at once");
        static_assert(
            ServerAnimationCallbackRvas[6].second == EngineBindings::HunkAllocXAnimRva &&
            ServerAnimationCallbackRvas[7].second == EngineBindings::HunkAllocXAnimRva,
            "out.exe's installer writes HunkAllocXAnim into both of these slots, and "
            "that binding is derived independently and prefix-guarded");
        constexpr std::size_t NumberOfPlayerAnimationsOffset = 0x1A000;
        constexpr std::uint32_t MaximumPlayerAnimations = 1024;
        // CODREF(bg_update_player_dobj): the locomotion animation table sits
        // immediately after that count. CODOL's anim-script state setter
        // sub_AA94C0 (VA 0x004094C0) reads it as
        //   *dword_7EB7B84 + 0x1A004 + 0x204 * movetype
        // (0x0040950F `lea ebx, [eax + ecx + 0x1A004]` after `imul eax, eax,
        // 0x204`), takes the first dword there as the script count, and returns
        // -1 without selecting anything when it is zero. Its stride back
        // through states is 0x5EBC = 0x204 * 47, so one state holds 47
        // movetypes. Both anim globals hold ONE pointer: CODOL's own loader
        // does `mov esi, [0x7817B80]` at 0x00445DAF and calls
        // BG_AnimParseAnimScript 0x00409040, whose first act (0x0040905E) is
        // `mov [0x7817B84], esi`. BO1 keeps the same pair in
        // BG_AnimParseAnimScript 0x006F4E10; Ghosts in 0x1400E5A30.
        //
        // OLMOD(section-84): CONFIRMED ON out.exe, WHOSE COUNTERPART IS
        // sub_407C00, and the arithmetic is instruction-for-instruction the
        // same with two operands changed:
        //
        //   3.3.3.3 0x00409501  imul eax, eax, 204h
        //           0x00409508  lea  ebx, [eax+ecx+1A004h]   ecx = [0x07817B84]
        //           0x0040951E  sub  ebx, 5EBCh
        //   out.exe 0x00407C41  imul eax, eax, 204h
        //           0x00407C48  lea  esi, [eax+ecx+1A004h]   ecx = [0x0827F734]
        //           0x00407C5E  sub  esi, 5EBCh
        //
        // So 0x1A004, 0x204 and 47 = 0x5EBC/0x204 all carry, and THE ANIM
        // GLOBALS PAIR ON THIS BUILD IS 0x0827F730/0x0827F734, not 3.3.3.3's
        // 0x07817B80/0x07817B84 -- the second is the anim-script blob, the
        // first is the characterInfo array sub_407E10 indexes at +0xAF350
        // stride 0x450 (0x00407E37..0x00407E43). 0xAF350 occurs ZERO times in
        // 3.3.3.3's .text, which is what makes that one unambiguous.
        constexpr std::size_t AnimScriptStateTableOffset = 0x1A004;
        constexpr std::size_t AnimScriptItemsStride = 0x204;
        constexpr std::size_t AnimScriptMoveTypeCount = 47;
        // CODREF(bg_update_player_dobj): BG_AnimUpdatePlayerConditions
        // sub_AA97B0 (VA 0x004097B0) is the FIRST call PmoveSingle makes
        // (0x0041DBC2) and writes 64-bit condition slots into the same derived
        // characterInfo, at +0x288 through +0x31C. sub_AA94C0 writes the
        // movetype condition at +0x2A0 only once it has selected an animation,
        // so a zero there after a live command is its failure signature and a
        // zero at +0x288 means the derived characterInfo is not the one the
        // native code writes.
        //
        // CODDIFF(1649370): 0x288 AND 0x2A0 WERE 3.3.3.3'S. sub_407790 -- the
        // condition walker BG_AnimScriptEvent calls to pick an animation -- reads
        // `*(DWORD *)(characterInfo + 8 * conditionIndex + 748)` and its partner at
        // +752, so the array base on this build is 748 = 0x2EC with an 8-byte
        // stride. That is +100 from 3.3.3.3, and it is the SAME +100 already
        // measured for two of its neighbours: CharacterInfoDObjDirtyOffset
        // 560 -> 660 and CharacterInfoAnimTreeOffset 800 -> 900. Three fields in
        // one region agreeing on the shift is what makes this a relocation rather
        // than a coincidence.
        //
        // The movetype slot is carried by INDEX, not re-derived: 0x2A0 - 0x288 = 24
        // is condition slot 3, so it is 748 + 24 = 772 here. Whatever established
        // slot 3 on the other build still holds; only the base moved.
        constexpr std::size_t CharacterInfoConditionBaseOffset = 0x2EC;
        constexpr std::size_t CharacterInfoMoveTypeConditionOffset = 0x304;
        // CODDIFF(1649370): THIS WAS 38 AND out.exe SAYS 19. The condition NAME
        // table at VA 0x00E60828 terminates with {0, 0xFFFFFFFF} at index 19
        // (VA 0x00E608C0), and the parallel condition-TYPE table sub_407790
        // indexes as dword_E608C8[2 * conditionIndex] begins one entry later at
        // VA 0x00E608C8 with nineteen entries of its own. Counting 38 made
        // `nonzero=N/38` below read nineteen real condition slots plus nineteen
        // slots of unrelated characterInfo at 0x384..0x41C, so the number it
        // printed was the measurement plus its neighbours. See
        // SvNativeAnimConditionCount for the full name list.
        constexpr std::size_t CharacterInfoConditionCount =
            SvNativeAnimConditionCount;
        static_assert(
            CharacterInfoConditionBaseOffset == SvNativeAnimConditionBaseOffset,
            "the condition array base is stated once, off sub_407790's "
            "*(DWORD *)(characterInfo + 8 * conditionIndex + 748)");
        // CODDIFF(1649370): ALL SIX OF THESE WERE 3.3.3.3'S, BYTE FOR BYTE.
        // 0x2B371B8 has ZERO cross-references in out.exe - the engine neither
        // reads nor writes it - so Scr_BeginLoadAnimTrees' reproduction was
        // setting the anim-tree loading state in a place nothing looks at, and
        // the script parse's asset lookups took the LOAD path instead of the
        // register-for-precache one. That is what reached the asset database's
        // inline load pump and killed the process.
        //
        // The real block is the one CL_ParseGamestate writes at 0x454C1A:
        //     454c21  mov byte_789C640, 1     loading      +0x118
        //     454c28  mov dword_789C634, edi  count        +0x10C
        //     454c2e  mov dword_789C534, edi  parsing      +0x00C
        //     454c34  call sub_74CED0         Scr_CreateObject
        //     454c4d  mov dword_789C528, eax  the object   +0x000
        //     454c52  mov dword_789C52C, edi  secondary    +0x004
        //     454c58  mov dword_789C680, edi  scratch      +0x158
        // and the anim-tree machinery reads that same family - sub_74A7B0,
        // sub_74AAF0, sub_74ACF0, sub_74B010, sub_74D4F0.
        //
        // Two of the six offsets happen to be unchanged; the struct's head is
        // stable and its tail moved. That is exactly why porting an offset
        // "because it still looks right" does not work.
        constexpr std::size_t ScrAnimTreeObjectRva = 0x749C528;
        constexpr std::size_t ScrAnimLoadingOffset = 0x118;
        constexpr std::size_t ScrAnimTreeCountOffset = 0x10C;
        constexpr std::size_t ScrAnimTreeParsingOffset = 0x00C;
        constexpr std::size_t ScrSecondaryAnimTreeObjectOffset = 0x004;
        constexpr std::size_t ScrAnimTreeScratchOffset = 0x158;
        constexpr std::size_t ItemDefinitionSize = 40;
        // CODDIFF(1649370): 12 is 3.3.3.3's, and on this build it is the
        // DISPLAY KEY, not the internal name. The definition gained a field
        // ahead of it. Dumped live from item 10001:
        //     +8  = m4_mp                  <- the weapon asset name
        //     +12 = sf_weapon_m4_mp_name   <- localisation key
        //     +16 = sf_weapon_m4_mp_desc   +20 = wea_m4_item_icon
        // Reading +12 handed the weapon resolver "sf_weapon_m4_mp_name", which
        // is not a weapon, so it returned 0 and every class in every loadout
        // was skipped with base_weapon_resolver. The two strings differ by a
        // suffix, which is why this read as "the item is missing on this build"
        // for as long as only the id was logged.
        constexpr std::size_t ItemDefinitionNameOffset = 8;
        // THE ITEM RECORD'S OWN CATEGORY AND SLOT, at +4 and +6. A definition is
        // {u16 id, u16 slot, u16 flags, u16 recordEntry, char *name, ...} -- the same
        // four leading shorts Tools/olfinal/marketplace-decode.py reads out of the
        // zone, and the engine's own use of them pins both:
        //
        //   sub_61B7D0 tests `*(BYTE *)(definition + 5) == 2` before it will treat an
        //   item as a character -- that is the HIGH BYTE of the u16 at +4, so the
        //   category lives in flags >> 8: 2 is a character, 3 is a character piece.
        //
        //   +6 is which RECORD ENTRY the piece occupies, and the engine published the
        //   proof itself. Character 569 resolved live to
        //       record=569,555,525,552,1139,561,-,564
        //   and the zone gives those pieces recordEntry 1,2,3,4,5 and 7 -- exactly the
        //   entries sub_619AD0 put them in. A character's own entry is 0.
        //
        // This is what makes a stored outfit placeable: the profile keeps equipped
        // pieces DENSELY (slots[0..8] = 545,18481,2137,0,...) while the record is
        // keyed by entry, and only the item table can map one to the other.
        constexpr std::size_t ItemDefinitionFlagsOffset = 4;
        constexpr std::size_t ItemDefinitionRecordEntryOffset = 6;
        constexpr std::uint16_t ItemCategoryCharacter = 2;
        constexpr std::uint16_t ItemCategoryCharacterPiece = 3;
        constexpr std::string_view WeaponItemsTableName =
            "mp/coWeapItemsWEA.csv";
        constexpr std::size_t WeaponItemsFirstSlotColumn = 10;
        constexpr std::size_t WeaponItemsSlotTripleCount = 10;
        // CODDIFF(1649370): the last five were `mp/coweapitems/gri.csv` -- a
        // SUBDIRECTORY form that does not exist in this build's zone. Decrypted
        // `common_marketplace_lite.ff` (ff_init_common_marketplace_V95.ifs) and
        // listed its StringTable assets: sixteen tables, every one of them flat
        // `mp/coweapitemsXXX.csv`, and the string `coweapitems/` appears
        // nowhere in the zone. The lookup returned no table for the tenth entry
        // and the old loop treated that as fatal, so EVERY equipped attachment
        // failed as `equipped_attachment_slot` no matter which slot it was in.
        //
        // The same zone settles the two tables not listed here. Its WEA table's
        // slot-name column uses exactly these fourteen -- iro mag rai sco hbs
        // muz cam sto gri bas bip sra cqc ret -- so `mp/coweapitemsdec.csv` is
        // not a loadout slot, and `rof` (slot 14 in SlotNames) has no table on
        // this build because nothing equips it.
        constexpr std::array<std::pair<std::string_view, std::uint8_t>, 14>
            AttachmentSlotTables{
                std::pair{ "mp/coweapitemsbas.csv", std::uint8_t{ 3 } },
                std::pair{ "mp/coweapitemscqc.csv", std::uint8_t{ 13 } },
                std::pair{ "mp/coweapitemshbs.csv", std::uint8_t{ 4 } },
                std::pair{ "mp/coweapitemsiro.csv", std::uint8_t{ 10 } },
                std::pair{ "mp/coweapitemsmuz.csv", std::uint8_t{ 2 } },
                std::pair{ "mp/coweapitemsrai.csv", std::uint8_t{ 6 } },
                std::pair{ "mp/coweapitemsret.csv", std::uint8_t{ 15 } },
                std::pair{ "mp/coweapitemssco.csv", std::uint8_t{ 1 } },
                std::pair{ "mp/coweapitemssto.csv", std::uint8_t{ 5 } },
                std::pair{ "mp/coweapitemsgri.csv", std::uint8_t{ 7 } },
                std::pair{ "mp/coweapitemsbip.csv", std::uint8_t{ 8 } },
                std::pair{ "mp/coweapitemssra.csv", std::uint8_t{ 9 } },
                std::pair{ "mp/coweapitemsmag.csv", std::uint8_t{ 11 } },
                std::pair{ "mp/coweapitemscam.csv", std::uint8_t{ 12 } },
            };
        // CODDIFF(1649370): THE WHOLE WeaponDef MOVED. Every offset below was
        // 3.3.3.3's, and the struct grew in seven separate places between the
        // builds, so no single delta fixes it -- the shift is +268 at the head,
        // +308 across the ammo block, +312, +320, +344, +348 and +352 by the
        // tail. `Tools/olfinal/struct-offset-uses.py` lists every instruction
        // that touches an offset in either image; each value here is named by
        // out.exe's OWN code, with the deriving function in the comment. The
        // three that carry no function reference are bracketed on both sides by
        // confirmed neighbours at fixed stride, which pins them exactly.
        constexpr std::size_t WeaponTypeOffset = 1416;          // sub_42BF80 == 3
        constexpr std::size_t WeaponClassOffset = 1420;         // sub_421DE0 == 11
        constexpr std::size_t WeaponPenetrateTypeOffset = 1424; // between 1420/1428
        constexpr std::size_t WeaponImpactTypeOffset = 1428;    // sub_421DE0 == 2
        constexpr std::size_t WeaponFireTypeOffset = 1432;      // sub_426320
        constexpr std::size_t WeaponAmmoIndexOffset = 2028;     // sub_42EC80 writes it
        constexpr std::size_t WeaponClipIndexOffset = 2036;     // sub_42EE90 writes it
        constexpr std::size_t WeaponMaxAmmoOffset = 2040;       // sub_42BF80
        constexpr std::size_t WeaponShotCountOffset = 2044;     // between 2040/2048
        constexpr std::size_t WeaponMeleeDamageOffset = 2072;   // sub_4BC1D0
        constexpr std::size_t WeaponFireDelayOffset = 2088;     // sub_426320
        constexpr std::size_t WeaponDropTimeOffset = 2188;      // sub_423CF0 putaway
        constexpr std::size_t WeaponRaiseTimeOffset = 2192;     // sub_424470 raise
        constexpr std::size_t WeaponOverlayReticleOffset = 2348;// sub_421DE0 != 3
        constexpr std::size_t WeaponHipSpreadStandMinOffset = 2384;  // sub_423060,
        constexpr std::size_t WeaponHipSpreadCrouchMinOffset = 2388; // whose eleven
        constexpr std::size_t WeaponHipSpreadProneMinOffset = 2392;  // field reads
        constexpr std::size_t WeaponHipSpreadStandMaxOffset = 2396;  // match
        constexpr std::size_t WeaponHipSpreadCrouchMaxOffset = 2400; // sub_422AA0's
        constexpr std::size_t WeaponHipSpreadProneMaxOffset = 2404;  // exactly
        constexpr std::size_t WeaponAdsSpreadOffset = 3096;     // sub_56C510
        constexpr std::size_t WeaponDamageOffset = 3344;        // sub_591790
        constexpr std::size_t WeaponDamageRangeOffset = 3368;   // sub_432510 indexed
        constexpr std::size_t WeaponHitLocationMultipliersOffset = 3404;
        constexpr std::size_t WeaponRifleBulletOffset = 3802;   // sub_5923C0
        constexpr std::size_t WeaponBulletExplosiveDamageOffset = 3810;
        // CODREF(1649370): BG_DualWieldActive 0x433030 gates the second
        // hand on this WeaponDef byte plus ownedWeaponRecord[1].
        constexpr std::size_t WeaponDualWieldCapableOffset = 0xEEC;
        constexpr std::size_t WeaponClipSizeOffset = 3688;      // sub_432E90
        constexpr std::size_t WeaponFireTimeOffset = 3696;      // sub_433360
        constexpr std::size_t WeaponAimDownSightOffset = 3806;  // sub_433910, sub_434680
        constexpr std::size_t WeaponAmmoCountClipRelativeOffset = 3865; // sub_42BF80
        // CODDIFF(1649370): 6 was 3.3.3.3's highest fire type. out.exe compares
        // this field against 7, 8, 9 and 10 as well (sub_426320 tests == 10), so
        // the old bound rejected four fire types that exist on this build.
        constexpr std::int32_t MaximumWeaponFireType = 10;
        // CODDIFF(1649370): 40 IS 3.3.3.3's AND IT WAS WRONG BY TWELVE BYTES PER RECORD,
        // and this file already said so eight hundred lines away: "indexes
        // CharacterItemDefinitionTable at stride 52 by the u16 at +2". The constant that
        // actually places the record was never moved to match -- section 51k's rule, and
        // the third time it has cost this port.
        //
        // out.exe writes the same three-instruction sequence at FOUR independent sites and
        // every one of them uses 0x34. The first is the exact counterpart of the code
        // below, `baseItemDefinition + 2` and all:
        //     0044E1F0  movzx eax, word ptr [eax + 2]     <- the record index
        //     0044E1F4  cmp   eax, [0x7798900]            <- the count
        //     0044E1FC  imul  eax, eax, 0x34              <- THE STRIDE
        //     0044E1FF  add   eax, [0x77988FC]            <- the table
        // and 0x0061B859, 0x00619C1D and 0x00660A94 agree. `tools/runtime/
        // CodolCharacterCategoryDump.py` has read the same table with the same 0x34 on a
        // live client since section 67, across 54 records and twelve characters.
        //
        // WHAT IT COST, and it is not cosmetic: the two bytes read out of this record are
        // the FEMALE flag and the COLOUR selector. At record index 0 the two strides agree
        // and every measurement this project has taken was on character 0; at index 1 they
        // are already twelve bytes apart, so any player on a character other than the
        // first would have been given another character's sex and colour -- silently, with
        // no error, which is section 48d's failure mode exactly.
        constexpr std::size_t CharacterItemDefinitionSize = 52;
        static_assert(
            CharacterItemDefinitionSize == 0x34,
            "out.exe indexes CharacterItemDefinitionTable with imul reg, reg, 0x34 at "
            "0x0044E1FC, 0x0061B859, 0x00619C1D and 0x00660A94");
        // TODO(CODOL): this is a recovery fallback, not a general character
        // contract. Exit when the character definition -> viewhands CCS owner
        // is recovered so each character resolves its own first-person model.
        constexpr std::string_view GenericCharacterViewhands = "viewhands_tf141";
        // CODREF(bg_update_player_dobj): CODOL
        // CODOL_CharacterCustomization_CopyCurrentItems 0x00568860 and
        // CODOL_CharacterCustomization_ResolveSelectionIds 0x0040CA30 close
        // this record-to-name ordering. The later 76-bit pack is only transport
        // and must not be treated as proof that every resolved model is visible.
        constexpr std::array<std::uint8_t, 12> CharacterRecordToSelectionName{
            11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 9,
        };

        // CODDIFF(character_item_record): TWELVE bytes on OLfinal, not eight, and the
        // difference is not padding -- there is a whole dword this build's decode needs
        // and 3.3.3.3's shape does not have.
        //
        // Read off sub_619E90, which is the function this file binds as
        // CharacterCurrentItemsCopyRva, so this is its own call site and not a nearby
        // one:
        //
        //     619ed0  lea ebx, [ecx+4]        ; ecx = the destination, entry 0 presence
        //     619ee6  lea esi, [ebx-4]        ; the entry BASE is destination + 12k
        //     619ef3  mov dword ptr [ebx+4], 0    ; the high dword, at +8
        //     619efa  mov byte ptr [ebx], 0       ; the presence byte, at +4
        //     619f00  add ebx, 0Ch            ; TWELVE, twelve times
        //     619f08  cmp byte ptr [ecx+4], 0 ; entry 0's presence, again at +4
        //
        // and its only caller memsets the destination to 0x90 = 144 = 12 x 12 before
        // every call (0x618bad). At eight bytes an array of twelve is 96, so the engine
        // wrote FORTY-EIGHT BYTES PAST IT -- and it does that on BOTH arms, because the
        // sub_6206B0-said-no path at 0x619eb0 still walks all twelve entries at stride
        // twelve. A stack overrun in the frame thread, latent only because
        // captureClientLoadoutRequest cannot currently reach the call.
        //
        // The decode needs the pair: sub_619E90 finishes with
        //     ROL32(dword_E4DD90 ^ *(dword *)entry ^ *(dword *)(entry + 8), 8)
        // (0x619f20), and its caller repeats that at four more sites. An eight-byte
        // record has nowhere to put the low dword, so no correct decode was possible
        // from it either -- the two defects are the same defect.
        struct NativeCharacterItemRecord
        {
            std::uint32_t encodedLow{};
            std::uint8_t present{};
            std::array<std::uint8_t, 3> padding{};
            std::uint32_t encodedHigh{};
        };

        // == and not <=. The three carried numbers section 59 and section 60 found all
        // survived a bound, because every value smaller than the answer satisfies one.
        static_assert(sizeof(NativeCharacterItemRecord) == 12);
        static_assert(sizeof(NativeCharacterItemRecord) * 12 == 0x90);

        // sub_619E90's own tail, at 0x619f20:
        //     ROL32(dword_E4DD90 ^ *(dword *)entry ^ *(dword *)(entry + 8), 8)
        // Three operands. The previous version XORed the key with one dword and rotated,
        // which is 3.3.3.3's shape and cannot be right here -- the record it reads from
        // did not have a second dword to XOR.
        [[nodiscard]] constexpr std::uint32_t decodeCharacterItemId(
            const NativeCharacterItemRecord &record,
            const std::uint32_t decodeKey) noexcept
        {
            return std::rotl(
                decodeKey ^ record.encodedLow ^ record.encodedHigh, 8);
        }

        // The inverse of decodeCharacterItemId, and the reason section 48b's "forge the
        // whole record" plan is not needed. With encodedLow left at zero the decode
        // reduces to ROL32(key ^ encodedHigh, 8) == id, so encodedHigh is
        // ROR32(id, 8) ^ key and nothing has to be inverted at runtime.
        //
        // sub_810B20 is the engine's own writer and would do the same job. It is not
        // called here because it takes its arguments in EAX and ESI and this does not
        // need it: one entry, one dword, and the arithmetic is checked by
        // decodeCharacterItemId round-tripping it in the unit tests.
        [[nodiscard]] constexpr NativeCharacterItemRecord encodeCharacterItemId(
            const std::uint32_t itemId, const std::uint32_t decodeKey) noexcept
        {
            NativeCharacterItemRecord record{};
            record.present = 1;
            record.encodedLow = 0;
            record.encodedHigh = std::rotr(itemId, 8) ^ decodeKey;
            return record;
        }

        // AND IT IS PINNED TO A DWORD THAT WAS MEASURED, NOT TO ITSELF. Section 51j's rule
        // is that a symmetric round trip passes even when both sides are wrong, so
        // asserting encode-then-decode would prove nothing about either.
        //
        // 0x5FCE6C73 is the literal dword sitting at manager+0xFB2 in
        // C:\Games\OLfinal\codol_1649370_full.bin -- a recording of a real client -- and
        // 0x7ECE6C71 is that same profile's obfuscation key from manager+0x11138. The
        // client wrote those bytes; nothing in this tree did. If this encoder ever stops
        // producing them it stops agreeing with the engine, and the build fails here
        // rather than a player rendering as the wrong character with no error at all.
        // Tools/olfinal/decode-profile-blob.py --path "characterClasses[0].slots[0]"
        // reads 545 back out of them.
        static_assert(
            encodeCharacterItemId(545u, 0x7ECE6C71u).encodedHigh == 0x5FCE6C73u);
        static_assert(
            encodeCharacterItemId(686u, 0x7ECE6C71u).encodedHigh == 0xD0CE6C73u);
        static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).encodedLow == 0u);
        static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).present == 1u);
        // The pair is consistent as well, which is worth exactly what section 51j says it
        // is worth -- nothing on its own, and something once the line above anchors one
        // side of it to a byte the engine wrote.
        static_assert(
            decodeCharacterItemId(
                encodeCharacterItemId(2127u, 0xA5A5A5A5u), 0xA5A5A5A5u) == 2127u);

        // OLMOD(section-67-resolution-gate): ON BY DEFAULT SINCE SECTION 69, because the
        // exit condition this gate was written with has been met and it was stated so it
        // could be checked rather than judged.
        //
        // It was off for one section, and for a measured reason: with resolution on, the
        // first two live runs produced five correct-slot names and then FAULTED in the
        // DObj build that follows, with `op=8 target=0x00000000` and a poisoned mirror,
        // where the stub it replaced failed earlier, cleaner, and still let the player
        // spawn. That was the right call at the time and the wrong diagnosis: the fault
        // was ten unported callback slots (section 69), not this path. With the table
        // ported the same run reports
        //
        //   character models RESOLVED entity=0 characterItem=545 variant=2 count=5
        //     record=545,532,525,529,1099,115,-,-,-,-,-,-
        //   player DObj rebuild entity=0 selectionChanged=1 dobjMissing=1
        //   native server player DObj active entity=0
        //
        // then 1113 snapshots at 20/s with `dropped=0 frameReject=none:0`, no fault of
        // any kind, and the only refusal the documented once-per-connect think sync.
        // BOTH halves of the exit condition, measured on the same run: the DObj build
        // survives, and the record is still identical to
        // CodolCharacterCategoryDump.py --resolve.
        //
        // The switch stays as a kill switch -- OLMOD_RESOLVE_CHARACTER_MODELS=0 restores
        // the stub -- because this is the path that decides whether a player can be shot
        // at all (section 55) and a way to turn it off without a rebuild is worth one
        // getenv. Any value other than "0" leaves it on, so a stale "=1" in someone's
        // environment keeps meaning what it used to mean.
        [[nodiscard]] bool characterModelResolutionEnabled() noexcept
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                std::size_t size = 0;
                if (getenv_s(&size, value.data(), value.size(),
                        "OLMOD_RESOLVE_CHARACTER_MODELS") != 0 || size < 2)
                {
                    return true;
                }
                return value[0] != '0';
            }();
            return enabled;
        }

        // sub_61B6C0's fourth argument, overridable so it can be MEASURED rather than
        // argued about. Section 67d establishes the range (1 or 2) and out.exe's own
        // fallback (2); it does not establish the meaning, and the first live run with 2
        // produced three names in the right family and two in the wrong one:
        //
        //   name 0  fpa_goose_ss_m_11          expected the fpa_infbasea family
        //   name 1  boo_empty_ss_s             expected the boo_infbasea family
        //   name 2  fja_infbasea_tf_m_wht_00   right
        //   name 3  han_infbasea_tf_m_00       right
        //   name 4  hea_socomb_sc_m            right, and exact
        //
        // Two `_ss_` among three that are not is a variant split, so the value is worth
        // one cycle rather than one more argument.
        //
        // AND SECTION 166 SETTLED WHICH VALUE, off the client rather than off a cycle.
        // CG_SetupClientCharacterInfo 0x00541800 builds the resolver's request from the
        // clientState this server sends and puts `*(int *)(clientState + 0x154) + 1` in
        // it -- the FACTION FIELD PLUS ONE -- then hands it to the in-match resolver
        // 0x0080E600, whose 0x0080E110 leg uses it as sub_61B6C0's fourth argument.
        // So the selector is not a free constant at all: THE CLIENT DERIVES IT FROM THE
        // FACTION THIS SERVER PUTS ON THE WIRE, and any other value here resolves a
        // character the client will never ask for.
        //
        // It was 2 while the wire carried faction 0, and the two sides disagreed on
        // every name that carries a faction: the dedicated built and precached
        // `fpa_goose_ss_m_11` / `fja_infbasea_tf_m_wht_00` while the client's own
        // characterInfo held `fpa_goose_ss_m_15` / `fja_infbasea_sc_m_wht_00`. The env
        // override stays, because measuring it is still worth one cycle -- it just no
        // longer decides the value.
        [[nodiscard]] int characterVariantSelectorOverride() noexcept
        {
            static const int selector = [] {
                std::array<char, 8> value{};
                std::size_t size = 0;
                if (getenv_s(&size, value.data(), value.size(),
                        "OLMOD_CHARACTER_VARIANT") != 0 || size < 2)
                {
                    return 0;
                }
                const int parsed = value[0] - '0';
                // Anything out of range is not an override at all. Out.exe's own
                // fallback for a value that is neither 1 nor 2 is what its caller at
                // 0x61D81B does, and that belongs to the faction rule below now.
                return (parsed == 1 || parsed == 2) ? parsed : 0;
            }();
            return selector;
        }

        // THE ONE PLACE THE SELECTOR IS DECIDED, so the dedicated cannot drift from the
        // client again. The client's rule is faction + 1 (0x00541800), and this side
        // holds the same faction it puts on the wire.
        [[nodiscard]] int characterVariantSelector(
            const SvCharacterFaction faction) noexcept
        {
            if (const auto forced = characterVariantSelectorOverride(); forced)
                return forced;
            return static_cast<int>(faction) + 1;
        }

        // sub_619AD0(record, characterItemId). __cdecl, two stack arguments, no return
        // value that matters. It makes TWO passes over the twelve-entry record: the first
        // marks which entries are occupied and which extra entries each occupying item
        // claims, and the second FILLS every entry still empty from the character's own
        // per-slot default table. That second pass is why this port supplies one id.
        using CharacterRecordFillDefaults = void(__cdecl *)(void *, int);

        // sub_61B6C0(names, record, baseItemId, variant). __cdecl, four stack arguments,
        // `add esp, 0x10` at its only call site. It memsets `names` to 0x2C -- ELEVEN
        // char* -- and maps record entries 1..9 to names 0..8 and entry 11 to name 9,
        // skipping entries 0 and 10. Entry 0 is not lost: sub_619E90's tail decodes it
        // separately and it is what `baseItemId` is.
        using CharacterRecordToSelectionNames =
            void(__cdecl *)(void *, const void *, int, int);

        // sub_50FF30 reads the public profile and can fault if the profile is not parsed,
        // so it is called behind the same guard as every other native read here.
        std::optional<int> invokeCharacterSlotGet(
            int(__cdecl *const function)(int, int),
            const int characterIndex,
            const int slot) noexcept
        {
            if (!function)
                return std::nullopt;
            __try
            {
                return function(characterIndex, slot);
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return std::nullopt;
            }
        }

        // ecx = element index (-1 for a scalar field), edx = the field name,
        // one stack dword = the class index. Plain `retn`, so this pops it.
        // The engine has already un-obfuscated the value and subtracted one, so
        // what comes back is the item id, or 0 for an empty slot.
        std::optional<std::int32_t> invokeWeaponClassFieldGet(
            void *const function,
            const std::int32_t elementIndex,
            const char *const field,
            const std::int32_t classIndex) noexcept
        {
            if (!function || !field)
                return std::nullopt;
            std::int32_t value{};
            __try
            {
                __asm
                {
                    mov ecx, elementIndex
                    mov edx, field
                    push classIndex
                    call function
                    add esp, 4
                    mov value, eax
                }
                return value;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return std::nullopt;
            }
        }

        // The member index goes in EAX; see the CODDIFF on characterCurrentItemsCopy_.
        // `records` must have room for TWELVE entries: the engine writes all twelve on
        // both arms, including the one where its own gate said no.
        bool invokeCharacterItemsCopy(
            void *const function,
            const std::uint32_t memberIndex,
            NativeCharacterItemRecord *const records) noexcept
        {
            if (!function || !records)
                return false;
            __try
            {
                __asm
                {
                    mov eax, memberIndex
                    push records
                    call function
                    add esp, 4
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        bool invokeLevelZoneLoad(
            void *function,
            const char *mapName,
            const char *gameType) noexcept
        {
            __try
            {
                __asm
                {
                    push mapName
                    mov ecx, gameType
                    call function
                    add esp, 4
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        bool invokeCollisionMapLoad(
            void *function,
            const char *bspName,
            const char *gameType,
            const char *mapName) noexcept
        {
            __try
            {
                __asm
                {
                    mov ecx, mapName
                    push gameType
                    push bspName
                    call function
                    add esp, 8
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        bool invokeNoArgument(void *function) noexcept
        {
            __try
            {
                __asm
                {
                    call function
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        bool invokeSVLinkEntity(
            void *const function,
            void *const entity,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !entity)
                return false;
            bool completed{};
            __try
            {
                __asm
                {
                    mov eax, entity
                    mov edx, function
                    call edx
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        bool invokeSVUnlinkEntity(
            void *const function,
            void *const entity) noexcept
        {
            if (!function || !entity)
                return false;
            bool completed{};
            __try
            {
                __asm
                {
                    mov eax, entity
                    mov edx, function
                    call edx
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        bool invokeBGFindAnims(
            void *const function,
            std::byte *const animTreeContext) noexcept
        {
            bool completed{};
            __try
            {
                __asm
                {
                    mov eax, animTreeContext
                    mov edx, function
                    call edx
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        // CODDIFF(character_customization): UNCALLED on OLfinal. This is the
        // 3.3.3.3 thunk for WorldCharacterModelResolve 0x0040C980, and that
        // function is absent from OLfinal entirely (§16a), so
        // resolveCharacterModelNames() will need a different thunk against
        // sub_61B6C0 rather than this one. Kept because it is the precise record
        // of the calling convention the 3.3.3.3 path used -- faction, selection
        // ids, female, colour in, a sparse 11-slot model-id list out -- which is
        // what the OLfinal replacement has to reproduce the MEANING of.
        std::optional<std::uint32_t> invokeWorldCharacterModelResolve(
            void *const function,
            const std::uint32_t faction,
            const std::uint16_t *const selectionIds,
            const std::uint32_t female,
            const std::uint32_t color,
            std::uint16_t *const modelIds) noexcept
        {
            if (!function || !selectionIds || !modelIds)
                return std::nullopt;
            std::uint32_t result{};
            __try
            {
                __asm
                {
                    push color
                    push female
                    push selectionIds
                    push modelIds
                    mov eax, faction
                    mov edx, function
                    call edx
                    add esp, 16
                    mov result, eax
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return std::nullopt;
            }
            return result;
        }

        // BGUpdatePlayerDObj = sub_40AB30. Read off the game's own call site,
        // sub_53DF40 @0x53DFF5:
        //     movzx ecx, cl        ; ECX = a BOOL -- set when [esi+194h] == [eax+3BB0h]
        //                          ;   and the type is not 2, i.e. "this is our client".
        //                          ;   ZERO is what a dedicated server means.
        //     mov edx, [ebp+arg_0] ; EDX = a POINTER from the caller
        //     push edi             ; a3 = characterInfo   (base +0xAF350, stride 0x450)
        //     push edx             ; a2 = esi+0xF4        (the entityState)
        //     push eax             ; a1 = the EXISTING DObj for this entity, or 0
        //     call sub_40AB30 / add esp, 0Ch      ; THREE stack args, caller cleans
        //
        // CODDIFF(1649370): 3.3.3.3's BG_UpdatePlayerDObj 0x0040B700 reads FOUR stack
        // arguments -- [ebp+8], +0Ch, +10h and +14h -- and out.exe's sub_40AB30 reads
        // only THREE. The fourth (3.3.3.3's attachIgnoreCollision) is gone here, so the
        // `push 0` that supplied it is dropped and the cleanup goes 16 -> 12. It was
        // self-balancing rather than harmful, because this is a caller-cleans call and
        // this code cleaned what it pushed; it was still describing the wrong function.
        //
        // A CORRECTION TO WHAT THIS COMMENT USED TO SAY, because it named the wrong
        // defect and would have sent the next reader at the arguments. It read a1 as
        // "an ANIM TABLE entry, NOT the existing DObj" and concluded the convention was
        // unportable without the model work. a1 is `unk_77E9720 + idx*0xD8` where
        // `idx = word[entityNumber*2 + 0x7855720]` -- and 0x7855720 is the client DObj
        // MAP, the same table out.exe's own get-DObj callback sub_453600 indexes at
        // 0x00453606. It is the existing DObj, which is what this code was already
        // passing. ECX 0 and EDX -1 were right too: sub_40AB30 tests EDX against -1 at
        // 0x0040AC0A and takes a documented skip branch, so -1 is a handled sentinel and
        // not a wrong pointer. Every argument was correct and the crash was somewhere
        // else entirely -- see the callback table above.
        bool invokeBGUpdatePlayerDObj(
            void *const function,
            void *const existingDObj,
            void *const entityState,
            void *const characterInfo,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !entityState || !characterInfo)
                return false;
            bool completed{};
            __try
            {
                __asm
                {
                    push characterInfo
                    push entityState
                    push existingDObj
                    mov edx, -1
                    xor ecx, ecx
                    mov eax, function
                    call eax
                    add esp, 12
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        // BGPlayerAnimation = sub_40A960, and IDA gives it outright:
        //     int __usercall sub_40A960@<eax>(_DWORD *a1@<edi>, int a2, int a3, int a4)
        // EDI plus THREE stack args. The game's call site sub_53DD40 @0x53DE89 does
        //     push eax   ; eax = 0     -> a4
        //     push ebx   ; esi+0xF4    -> a3, the entity
        //     push edx                 -> a2
        //     call sub_40A960 / add esp, 0Ch
        // This pushed only TWO and cleaned 8, so the engine read a4 out of ol-mod's own
        // stack frame -- the same defect that made SVTrace return garbage. The third
        // argument is now pushed as the 0 the game passes, and the cleanup matches.
        //
        // a2 stays -1: the game passes edx there and edx's owner is not established at
        // that call site.
        //
        // RE-READ AGAINST out.exe ALONGSIDE invokeBGUpdatePlayerDObj, and this one is
        // right. sub_40A960 reads [ebp+8], +0Ch and +10h and nothing further, so THREE
        // is the count on this build too, and out.exe's own call site 0x0053DE89 pushes
        // `eax`=0, `ebx`=the entityState and `edx` in that order before `add esp, 0Ch`.
        // EDI is the characterInfo: 0x0053DE1F derives it as
        // `lea edi, [ecx + eax + 0xAF350]`, the same per-client array at the same
        // offset this file already carries.
        bool invokeBGPlayerAnimation(
            void *const function,
            void *const entityState,
            void *const characterInfo,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !entityState || !characterInfo)
                return false;
            bool completed{};
            __try
            {
                __asm
                {
                    push edi
                    mov edi, characterInfo
                    push 0
                    push entityState
                    push -1
                    mov eax, function
                    call eax
                    add esp, 0Ch
                    pop edi
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        bool invokeNativeLerpFrameAccessorInitialize(
            void *const function,
            std::byte *const frame,
            const std::uint32_t selector,
            const std::uint32_t setKey,
            const std::uint32_t getKey,
            const std::byte *const zeroVector,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !frame || !zeroVector ||
                selector >= SvNativeLerpFrameSelectorCount)
                return false;
            auto *const encodedSet = frame +
                SvNativeLerpFrameSetAccessorOffset;
            auto *const encodedGet = frame +
                SvNativeLerpFrameGetAccessorOffset;
            auto *const protectedValue = frame +
                SvNativeLerpFrameProtectedValueOffset;
            bool completed{};
            __try
            {
                __asm
                {
                    push edi
                    mov edi, encodedGet
                    push setKey
                    push encodedSet
                    push encodedGet
                    push selector
                    mov eax, encodedSet
                    mov edx, getKey
                    mov ecx, function
                    call ecx
                    add esp, 16

                    mov ecx, encodedSet
                    mov ecx, dword ptr [ecx]
                    xor ecx, setKey
                    mov eax, encodedGet
                    xor ecx, eax
                    push protectedValue
                    push zeroVector
                    call ecx
                    add esp, 8
                    pop edi
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        bool invokeDObjGeomTracelinePartBits(
            void *const function,
            void *const dobj,
            std::array<std::uint32_t, 8> &partBits,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !dobj)
                return false;
            bool completed{};
            auto *const output = partBits.data();
            __try
            {
                __asm
                {
                    push esi
                    mov esi, output
                    push dobj
                    mov eax, function
                    call eax
                    add esp, 4
                    pop esi
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        // CODREF(sv_trace): the CONTENTS variant, sub_CE6B40 (VA 0x00646B40).
        // SV_PointTraceToEntity picks between the two on the entity's svFlags
        // at gentity +0x112: bit 2 clear takes the locational pair
        // (sub_CE69A0 + DObjTraceline 0x00645DD0, handed the pointtrace's
        // priority map at +0x54), bit 2 set takes this one plus 0x00646A70 and
        // is handed the content mask at +0x4C instead. It therefore needs that
        // second argument; the locational variant does not.
        bool invokeDObjContentsTracelinePartBits(
            void *const function,
            void *const dobj,
            const std::uint32_t contentMask,
            std::array<std::uint32_t, 8> &partBits,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !dobj)
                return false;
            bool completed{};
            auto *const output = partBits.data();
            __try
            {
                __asm
                {
                    push esi
                    mov esi, output
                    push contentMask
                    push dobj
                    mov eax, function
                    call eax
                    add esp, 8
                    pop esi
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        // CODREF(sv_trace): what DObjTraceline writes through ECX. Read off the
        // ONE caller 1649370 still has (0x0046E280) plus the function's own
        // prologue, which zeroes +4, +8..+0x10 and the three words at +0x14:
        //
        //     +0x00  fraction   SEEDED BY THE CALLER with the running best -
        //                       0x0046E1FC loads it from the trace_t before the
        //                       call, so this is a max, not an out-only field
        //     +0x04  surfaceFlags        -> trace_t +0x10
        //     +0x08  normal[3]  MODEL SPACE -> rotated back at 3.3.3.3's
        //                       0x005FB7DC before it reaches trace_t +4
        //     +0x14  modelIndex          -> trace_t +0x1E
        //     +0x16  partName            -> trace_t +0x20
        //     +0x18  partGroup           -> trace_t +0x22
        struct NativeDObjTraceResult
        {
            float fraction;
            std::uint32_t surfaceFlags;
            std::array<float, 3> normal;
            std::uint16_t modelIndex;
            std::uint16_t partName;
            std::uint16_t partGroup;
            std::uint16_t pad001A;
        };

        static_assert(sizeof(NativeDObjTraceResult) == 0x1C);
        static_assert(offsetof(NativeDObjTraceResult, surfaceFlags) == 0x04);
        static_assert(offsetof(NativeDObjTraceResult, normal) == 0x08);
        static_assert(offsetof(NativeDObjTraceResult, modelIndex) == 0x14);
        static_assert(offsetof(NativeDObjTraceResult, partName) == 0x16);
        static_assert(offsetof(NativeDObjTraceResult, partGroup) == 0x18);

        // AngleVectors, sub_767890: four STACK arguments, __cdecl, three
        // separate three-float destinations. The axis this project wants is
        // Quake's AnglesToAxis, which is AngleVectors with the SECOND row
        // inverted - so the caller negates it.
        //
        // THE BINDING THIS REPLACED WROTE INTO ITS OWN INPUT. `anglesToQuaternion_`
        // is sub_7853E0, which reads the angles through ESI and writes FOUR
        // floats through EDX, and NativeWeaponMovementBindings' wrapper passes
        // them the other way round - so it read a matrix as angles and stamped
        // a quaternion over the caller's angle vector. The entity mirror is
        // what caught it: `check=source entity=0 offset=353`, and 353 is 0x161,
        // inside currentAngles[1]. Section 73f.
        bool invokeAngleVectors(
            void *const function,
            const std::array<float, 3> &angles,
            std::array<float, 9> &axis,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function)
                return false;
            bool completed{};
            const auto *const anglesPointer = angles.data();
            auto *const forwardPointer = axis.data();
            auto *const rightPointer = axis.data() + 3;
            auto *const upPointer = axis.data() + 6;
            __try
            {
                __asm
                {
                    push upPointer
                    push rightPointer
                    push forwardPointer
                    push anglesPointer
                    mov eax, function
                    call eax
                    add esp, 10h
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            if (completed)
            {
                // AnglesToAxis = AngleVectors + VectorInverse(axis[1]).
                for (std::size_t component{ 3 }; component != 6; ++component)
                    axis[component] = -axis[component];
            }
            return completed;
        }

        // ECX = the result, EDX = the END point, then DObj / START / priority
        // map on the stack, caller cleans 12. Taken from 0x0046E26D..0x0046E285,
        // where the cleanup is shared with the DObjCalcSkel wrapper's two
        // arguments - `add esp, 14h` for 2 + 3 dwords.
        bool invokeDObjTraceline(
            void *const function,
            void *const dobj,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const std::uint8_t *const priorityMap,
            NativeDObjTraceResult &result,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !dobj || !priorityMap)
                return false;
            bool completed{};
            auto *const resultPointer = &result;
            const auto *const startPointer = start.data();
            const auto *const endPointer = end.data();
            __try
            {
                __asm
                {
                    mov ecx, resultPointer
                    mov edx, endPointer
                    push priorityMap
                    push startPointer
                    push dobj
                    mov eax, function
                    call eax
                    add esp, 0Ch
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        // CODREF(out.exe 46E235..46E24E and 783290): contents geometry uses
        // five caller-cleaned stack arguments, unlike the player tracer.
        bool invokeDObjContentsTraceline(
            void *const function, void *const dobj,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const std::uint32_t contentMask,
            NativeDObjTraceResult &result,
            NativeExceptionDetails *const exceptionDetails) noexcept
        {
            if (!function || !dobj || !contentMask)
                return false;
            using Function = void (__cdecl *)(void *, const float *,
                const float *, std::uint32_t, NativeDObjTraceResult *);
            __try
            {
                reinterpret_cast<Function>(function)(
                    dobj, start.data(), end.data(), contentMask, &result);
                return true;
            }
            __except (captureNativeException(GetExceptionInformation(), exceptionDetails))
            {
                return false;
            }
        }

        bool invokeDObjCalcSkel(
            void *const function,
            void *const dobj,
            const std::array<std::uint32_t, 8> &partBits,
            NativeExceptionDetails *const exceptionDetails = nullptr) noexcept
        {
            if (!function || !dobj)
                return false;
            bool completed{};
            const auto *const requestedParts = partBits.data();
            __try
            {
                __asm
                {
                    push dobj
                    mov ecx, requestedParts
                    mov eax, function
                    call eax
                    add esp, 4
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        // CODREF(client_spawn): zero a player's whole animation subtree, the
        // way sub_BB89E0 does at VA 0x00518A62..0x00518A81. Both walkers are
        // plain __cdecl: find(tree, value, node) and
        // setCompleteGoalWeight(tree, node, weight, flag, rate).
        void clearNativeXAnimTree(
            void *const freeInfo,
            void *const tree) noexcept
        {
            if (!freeInfo || !tree)
                return;
            __try
            {
                auto *const children = reinterpret_cast<std::uint16_t *>(
                    static_cast<std::byte *>(tree) + 4);
                // BO1 XAnimClearTree issues ONE call and asserts the field is
                // then zero, because XAnimFreeInfo drains the whole sibling
                // chain. Loop anyway, bounded, so a partial drain cannot leave
                // a node attached - and so this can never spin.
                for (std::size_t guard{}; *children && guard < 64; ++guard)
                {
                    reinterpret_cast<void(__cdecl *)(void *, int)>(freeInfo)(
                        tree, *children);
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
            }
        }

        void *createNativeXAnimTree(
            void *const allocator,
            void *const anims) noexcept
        {
            if (!allocator || !anims)
                return nullptr;
            __try
            {
                auto *const tree = reinterpret_cast<void *(__cdecl *)(
                    std::size_t)>(allocator)(sizeof(void *) * 2);
                if (!tree)
                    return nullptr;
                auto **const fields = static_cast<void **>(tree);
                fields[0] = anims;
                fields[1] = nullptr;
                return tree;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return nullptr;
            }
        }

        // CODREF(xanim_shared_actor_blend): exact out.exe caller 527D49
        // establishes this x86 register/stack contract. This uses the
        // same type-8 ancestor weighting, flags0 and 0.2s as our actor wire.
        // CODDIFF(0x7869E0,0x786860): collision-only server poses use notifyType0.
        // Client notifyType2 appends to 0x81AA7B0; this server has no client
        // drain, so copying the render-side flag grows that queue indefinitely.
        // The independently serialized client animation/FX events keep type2.
        bool setActorHitAnimation(std::uint8_t *module, void *dobj,
            std::uint32_t node) noexcept
        {
            void *function = module + 0x3891D0;
            __try
            {
                __asm {
                    push 0
                    push 03F800000h
                    push 03E4CCCCDh
                    push 03F800000h
                    push 0
                    push dobj
                    mov ecx, node
                    xor eax, eax
                    call function
                    add esp, 24
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
        }

        // CODREF(xanim_shared_actor_blend): 5401DA/549932 invoke 788200 with
        // EDI=DObj and elapsed seconds on stack; it owns native clock/blends.
        bool advanceActorHitAnimation(std::uint8_t *module, void *dobj,
            float seconds) noexcept
        {
            void *function = module + 0x388200;
            __try
            {
                __asm {
                    push seconds
                    mov edi, dobj
                    call function
                    add esp, 4
                }
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
        }

        bool invokeBGAnimParseAnimScript(
            void *const function,
            std::byte *const loadAnims,
            std::byte *const animScriptData,
            std::uint32_t &animationCount,
            NativeExceptionDetails &exceptionDetails) noexcept
        {
            auto *const count = &animationCount;
            bool completed{};
            __try
            {
                // CODDIFF(1649370): TWO stack arguments, not one. sub_407530
                // loads both - `mov eax, [ebp+arg_0]` for the count and
                // `mov ebx, [ebp+arg_4]` right after - and arg_4 is not
                // decorative: it goes straight into ECX of the script parser
                // at 0x407663 (`mov ecx, ebx; call sub_4064A0`). Pushing only
                // the count left that ECX reading whatever sat above `count`
                // on our stack, and it killed the process outright rather than
                // raising anything this __try could catch.
                //
                // CL_ParseGamestate calls it `push 0; push &count` at 0x454CD6,
                // so arg_4 is zero.
                __asm
                {
                    push 0
                    push count
                    mov ecx, loadAnims
                    mov esi, animScriptData
                    mov eax, function
                    call eax
                    add esp, 8
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), &exceptionDetails))
            {
                completed = false;
            }
            return completed;
        }

        bool invokeScrBeginLoadAnimTrees(
            std::uint8_t *const module,
            void *const createObject) noexcept
        {
            if (!module || !createObject)
                return false;
            __try
            {
                auto *const state = reinterpret_cast<std::byte *>(
                    module + ScrAnimTreeObjectRva);
                *reinterpret_cast<std::uint8_t *>(
                    state + ScrAnimLoadingOffset) = 1;
                *reinterpret_cast<std::uint32_t *>(
                    state + ScrAnimTreeCountOffset) = 0;
                *reinterpret_cast<std::uint32_t *>(
                    state + ScrAnimTreeParsingOffset) = 0;

                std::uint32_t object{};
                auto *const variable = reinterpret_cast<std::uint32_t *(
                    __cdecl *)(std::uint32_t *)>(createObject)(&object);
                if (!variable || !object)
                    return false;
                variable[1] = 23;
                variable[0] = 0;
                *reinterpret_cast<std::uint32_t *>(state) = object;
                *reinterpret_cast<std::uint32_t *>(
                    state + ScrSecondaryAnimTreeObjectOffset) = 0;
                *reinterpret_cast<std::uint32_t *>(
                    state + ScrAnimTreeScratchOffset) = 0;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        bool invokeBGLoadAnimTrees(
            void *const function,
            const char *const gameType,
            const char *const mapName) noexcept
        {
            bool completed{};
            __try
            {
                __asm
                {
                    push mapName
                    mov esi, gameType
                    mov eax, function
                    call eax
                    add esp, 4
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        bool invokeScrPrecacheAnimTrees(
            void *const function,
            void *const allocator,
            const std::int32_t animUser) noexcept
        {
            if (!function)
                return false;
            __try
            {
                // sub_74AF50 is __usercall: the anim USER in EDI, the allocator
                // on the stack. See the CODDIFF on ScrPrecacheAnimTreesRva -
                // this used to be a plain __cdecl(void*, int) call into the
                // wrong function entirely.
                __asm
                {
                    push allocator
                    mov edi, animUser
                    mov eax, function
                    call eax
                    add esp, 4
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        void invokeScrClearObject(
            void *const function,
            const std::uint32_t object) noexcept
        {
            __asm
            {
                mov ecx, object
                mov eax, function
                call eax
            }
        }

        bool invokeScrEndLoadAnimTrees(std::uint8_t *const module) noexcept
        {
            // CODDIFF(1649370): THIS USED TO BE FORTY LINES REPRODUCING
            // Scr_EndLoadAnimTrees BY HAND, ON 3.3.3.3'S ADDRESSES. The
            // vectored witness caught it: `rva=0x01F82A2 op=1 target=0x3`, a
            // WRITE to address 3, and 0x1F82A0 was this function's own
            // ScrClearObjectRva. Every constant in it - the object variable
            // table, the temp arena, the loading flag, Scr_ClearObject,
            // Scr_RemoveRefToObject, TempMallocAlignStrict - was carried over
            // unchanged from the other build.
            //
            // out.exe HAS the function. sub_74B010 takes no arguments and
            // CL_ParseGamestate calls it at 0x454D3D, between BG_FindAnimTrees
            // and BG_FinalizePlayerAnims, which is exactly where this sits.
            // Reproducing an engine function is only worth doing when the
            // engine does not expose one.
            constexpr std::size_t ScrEndLoadAnimTreesRva = 0x034B010;
            if (!module)
                return false;
            __try
            {
                reinterpret_cast<void(__cdecl *)()>(
                    module + ScrEndLoadAnimTreesRva)();
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            return true;
        }

        struct MapEnts
        {
            const char *name;
            const char *entityString;
            std::int32_t numEntityChars;
        };

        // MapEnts.trigger, the three flat arrays that follow numEntityChars. Sizes are
        // fixed by the fastfile the offline extractor already parses
        // (Tools/gen-mapent-numbering.py): model 8 bytes, hull 32, slab 20.
        struct MapTriggerModel
        {
            std::uint32_t contents;
            std::uint16_t hullCount;
            std::uint16_t firstHull;
        };

        struct MapTriggerHull
        {
            std::array<float, 3> midpoint;
            std::array<float, 3> halfSize;
            std::uint32_t contents;
            std::uint16_t slabCount;
            std::uint16_t firstSlab;
        };

        struct MapTriggerSlab
        {
            std::array<float, 3> direction;
            float midPoint;
            float halfSize;
        };

        static_assert(sizeof(MapTriggerModel) == 8);
        static_assert(sizeof(MapTriggerHull) == 32);
        static_assert(sizeof(MapTriggerSlab) == 20);

        // A SEPARATE VIEW, not an extension of MapEnts above: readMapEntityString
        // checks the asset is at least sizeof(MapEnts) bytes, and widening that struct
        // would tighten a check on a path that four maps already load correctly.
        struct MapEntsWithTriggers
        {
            const char *name;
            const char *entityString;
            std::int32_t numEntityChars;
            std::int32_t modelCount;
            const MapTriggerModel *models;
            std::int32_t hullCount;
            const MapTriggerHull *hulls;
            std::int32_t slabCount;
            const MapTriggerSlab *slabs;
        };

        struct NativeFxGlassInitPieceState
        {
            std::array<float, 4> quaternion;
            std::array<float, 3> origin;
            float radius;
            std::array<float, 2> textureCoordinateOrigin;
            std::uint32_t supportMask;
            float doubledArea;
            std::uint8_t definitionIndex;
            std::uint8_t vertexCount;
            std::uint8_t fanDataCount;
            std::uint8_t padding;
        };

        struct NativeFxGlassSystem
        {
            std::int32_t time;
            std::int32_t previousTime;
            std::uint32_t definitionCount;
            std::uint32_t pieceLimit;
            std::uint32_t pieceWordCount;
            std::uint32_t initialPieceCount;
            std::uint32_t cellCount;
            std::uint32_t activePieceCount;
            std::uint32_t firstFreePiece;
            std::uint32_t geometryLimit;
            std::uint32_t geometryCount;
            std::uint32_t initialGeometryCount;
            std::array<const void *, 11> runtimePointers;
            const NativeFxGlassInitPieceState *initialPieceStates;
            const void *initialGeometry;
            std::uint8_t needsCompaction;
            std::uint8_t initialCount;
            std::uint16_t padding;
            float effectChanceAccumulator;
            std::int32_t lastPieceDeletionTime;
        };

        struct NativeFxWorld
        {
            const char *name;
            NativeFxGlassSystem glassSystem;
        };

        static_assert(sizeof(NativeFxGlassInitPieceState) == 52);
        static_assert(offsetof(NativeFxGlassSystem, initialPieceStates) == 92);
        static_assert(sizeof(NativeFxGlassSystem) == 112);
        static_assert(offsetof(NativeFxWorld, glassSystem) == 4);
        static_assert(sizeof(NativeFxWorld) == 116);

        struct StringTableCell
        {
            const char *value;
            std::uint32_t hash;
        };

        struct StringTable
        {
            const char *name;
            std::int32_t columnCount;
            std::int32_t rowCount;
            const StringTableCell *values;
        };

        static_assert(sizeof(StringTableCell) == 8);
        static_assert(sizeof(StringTable) == 16);

        struct NativeTraceResult
        {
            float fraction;
            std::array<float, 3> normal;
            std::uint32_t surfaceFlags;
            std::uint32_t contents;
            std::uint32_t hitType;
            std::uint16_t hitId;
            std::uint16_t modelIndex;
            std::uint16_t partName;
            std::uint16_t partGroup;
            std::uint8_t allSolid;
            std::uint8_t startSolid;
            std::uint8_t walkable;
            std::uint8_t unknownEnd;
        };

        static_assert(sizeof(NativeTraceResult) == 0x28);
        static_assert(sizeof(TraceBounds) == 0x18);
        static_assert(offsetof(NativeTraceResult, hitType) == 0x18);
        static_assert(offsetof(NativeTraceResult, hitId) == 0x1C);
        static_assert(offsetof(NativeTraceResult, modelIndex) == 0x1E);
        static_assert(offsetof(NativeTraceResult, partName) == 0x20);
        static_assert(offsetof(NativeTraceResult, partGroup) == 0x22);
        static_assert(offsetof(NativeTraceResult, allSolid) == 0x24);

        bool invokePointTraceStaticModels(
            void *const function,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const std::uint32_t contentMask,
            NativeTraceResult &result,
            NativeExceptionDetails *const exceptionDetails) noexcept
        {
            if (!function || !contentMask)
                return false;
            auto *const output = &result;
            const auto *const startPointer = start.data();
            const auto *const endPointer = end.data();
            __try
            {
                // CODREF(out.exe 46E807..46E816 / 66A3D0): not cdecl.
                __asm
                {
                    push edi
                    mov edi, output
                    mov edx, contentMask
                    mov ecx, endPointer
                    push startPointer
                    mov eax, function
                    call eax
                    add esp, 4
                    pop edi
                }
                return true;
            }
            __except (captureNativeException(GetExceptionInformation(), exceptionDetails))
            {
                return false;
            }
        }

        struct NativeWorldTraceCallbacks
        {
            bool (__cdecl *isGlassSolid)(std::int32_t pieceIndex);
        };

        static_assert(sizeof(NativeWorldTraceCallbacks) == 4);

        struct NativeBrushModel
        {
            TraceBounds bounds;
            std::array<std::byte, 12> unknown0018;
            std::uint32_t leafBrushContents;
            std::uint32_t leafTerrainContents;
            std::array<std::byte, 28> unknown002C;
        };

        static_assert(sizeof(NativeBrushModel) == 72);
        static_assert(offsetof(NativeBrushModel, leafBrushContents) == 0x24);
        static_assert(offsetof(NativeBrushModel, leafTerrainContents) == 0x28);

        thread_local const SvGlassState *activeGlassState{};

        bool __cdecl SV_Glass_IsPieceSolid(const std::int32_t pieceIndex)
        {
            return pieceIndex >= 0 && activeGlassState &&
                activeGlassState->isPieceSolid(
                    static_cast<std::uint32_t>(pieceIndex));
        }

        bool installBrushTraceGlassBridge(std::uint8_t *const module)
        {
            // CODREF(brush_trace_glass): both sites store the engine's own glass callback into a
            // stack local -- `mov [ebp-disp], offset callback` -- and the mod redirects them at
            // SV_Glass_IsPieceSolid. Identified on 1649370 by the callback ADDRESS rather than by
            // position: each build contains exactly TWO such stores, the owning functions
            // correspond (the second is TransformedBrushModelTrace, which this file already binds),
            // and the callback body is byte-identical in both -- `32 C0 C3`, xor al,al / ret.
            //
            // THE DISPLACEMENT IS PER SITE ON THIS BUILD and that is why the guard had to change
            // shape. 3.3.3.3 uses -0x4C at both sites, so one shared 3-byte prefix covered them.
            // out.exe uses -0x4C at 0x268302 and -0x48 at 0x2684CB, because the two functions'
            // stack frames drifted independently. A single prefix silently fails the second site,
            // which is exactly how this presented: bind() reaching stage=glass_bridge and refusing.
            struct CallbackInstruction
            {
                std::size_t rva;
                std::uint8_t displacement;
            };
            constexpr std::array<CallbackInstruction, 2> CallbackInstructions{
                CallbackInstruction{ 0x268302, 0xB4 },   // -0x4C
                CallbackInstruction{ 0x2684CB, 0xB8 },   // -0x48
            };
            constexpr std::size_t CallbackOperandOffset = 3;
            constexpr std::size_t OriginalGlassCallbackRva = 0x450A40;

            const auto original = reinterpret_cast<std::uintptr_t>(
                module + OriginalGlassCallbackRva);
            const auto replacement = reinterpret_cast<std::uintptr_t>(
                &SV_Glass_IsPieceSolid);
            static_assert(sizeof(original) == sizeof(std::uint32_t));

            std::array<std::uint32_t, CallbackInstructions.size()>
                previousOperands{};
            for (std::size_t index = 0;
                 index != CallbackInstructions.size();
                 ++index)
            {
                const auto rva = CallbackInstructions[index].rva;
                const auto *const instruction = module + rva;
                const std::array<std::uint8_t, 3> expected{
                    0xC7, 0x45, CallbackInstructions[index].displacement,
                };
                if (!std::equal(expected.begin(), expected.end(), instruction))
                    return false;
                std::memcpy(
                    &previousOperands[index],
                    instruction + CallbackOperandOffset,
                    sizeof(previousOperands[index]));
                if (previousOperands[index] !=
                        static_cast<std::uint32_t>(original) &&
                    previousOperands[index] !=
                        static_cast<std::uint32_t>(replacement))
                {
                    return false;
                }
            }

            auto *const first = module + CallbackInstructions.front().rva +
                CallbackOperandOffset;
            auto *const last = module + CallbackInstructions.back().rva +
                CallbackOperandOffset + sizeof(std::uint32_t);
            const auto patchLength = static_cast<SIZE_T>(last - first);
            DWORD oldProtection{};
            if (!VirtualProtect(
                    first,
                    patchLength,
                    PAGE_EXECUTE_READWRITE,
                    &oldProtection))
            {
                return false;
            }
            const auto replacement32 = static_cast<std::uint32_t>(replacement);
            for (const auto &instruction : CallbackInstructions)
            {
                std::memcpy(
                    module + instruction.rva + CallbackOperandOffset,
                    &replacement32,
                    sizeof(replacement32));
            }
            FlushInstructionCache(GetCurrentProcess(), first, patchLength);
            DWORD ignored{};
            if (VirtualProtect(
                    first,
                    patchLength,
                    oldProtection,
                    &ignored))
            {
                return true;
            }

            for (std::size_t index = 0;
                 index != CallbackInstructions.size();
                 ++index)
            {
                std::memcpy(
                    module + CallbackInstructions[index].rva +
                        CallbackOperandOffset,
                    &previousOperands[index],
                    sizeof(previousOperands[index]));
            }
            FlushInstructionCache(GetCurrentProcess(), first, patchLength);
            static_cast<void>(VirtualProtect(
                first, patchLength, oldProtection, &ignored));
            return false;
        }

        class ScopedGlassState final
        {
        public:
            explicit ScopedGlassState(const SvGlassState &glassState)
                : previous_(activeGlassState)
            {
                activeGlassState = &glassState;
            }

            ~ScopedGlassState()
            {
                activeGlassState = previous_;
            }

            ScopedGlassState(const ScopedGlassState &) = delete;
            ScopedGlassState &operator=(const ScopedGlassState &) = delete;

        private:
            const SvGlassState *previous_;
        };

        bool validTraceInput(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            const std::uint32_t contentMask)
        {
            const auto finiteVector = [](const auto &vector) {
                return std::ranges::all_of(vector, [](const float value) {
                    return std::isfinite(value);
                });
            };
            return contentMask && finiteVector(start) && finiteVector(end) &&
                finiteVector(bounds.midpoint) && finiteVector(bounds.halfSize) &&
                std::ranges::none_of(bounds.halfSize, [](const float value) {
                    return value < 0.0f;
                });
        }

        std::optional<TraceResult> decodeTraceResult(
            const NativeTraceResult &native)
        {
            if (!std::isfinite(native.fraction) || native.fraction < 0.0f ||
                native.fraction > 1.0f ||
                std::ranges::any_of(native.normal, [](const float value) {
                    return !std::isfinite(value);
                }) ||
                native.hitId > 2047 || native.allSolid > 1 ||
                native.startSolid > 1 || native.walkable > 1)
            {
                return std::nullopt;
            }
            return TraceResult{
                .fraction = native.fraction,
                .normal = native.normal,
                .surfaceFlags = native.surfaceFlags,
                .contents = native.contents,
                .hitType = native.hitType,
                .hitId = native.hitId,
                .modelIndex = native.modelIndex,
                .partName = native.partName,
                .partGroup = native.partGroup,
                .allSolid = native.allSolid != 0,
                .startSolid = native.startSolid != 0,
                .walkable = native.walkable != 0,
            };
        }

        NativeTraceResult encodeTraceResult(const TraceResult &trace)
        {
            NativeTraceResult native{};
            native.fraction = trace.fraction;
            native.normal = trace.normal;
            native.surfaceFlags = trace.surfaceFlags;
            native.contents = trace.contents;
            native.hitType = trace.hitType;
            native.hitId = trace.hitId;
            native.modelIndex = trace.modelIndex;
            native.partName = trace.partName;
            native.partGroup = trace.partGroup;
            native.allSolid = trace.allSolid ? 1 : 0;
            native.startSolid = trace.startSolid ? 1 : 0;
            native.walkable = trace.walkable ? 1 : 0;
            return native;
        }

        struct NativeIgnoreEntParams
        {
            std::int32_t baseEntity{};
            std::int32_t parentEntity{};
            std::uint8_t ignoreSelf{};
            std::uint8_t ignoreParent{};
            std::uint8_t ignoreSiblings{};
            std::uint8_t ignoreChildren{};
        };

        static_assert(sizeof(NativeIgnoreEntParams) == 12);

        // NativePointTrace and its invoker are GONE, deliberately.
        // 0x0046E6D0 is out.exe's CLIENT trace-to-entities and this build
        // has no server-side twin, so nothing here can fill that struct
        // usefully; traceServerLocationalEntities does the per-entity work
        // instead. Section 73. The two RVAs stay bound and guarded because
        // both addresses are real and verify-bindings counts them.

        // THIS MARSHALLING WAS 3.3.3.3's AND FOUR OF EIGHT ARGUMENTS WERE WRONG.
        //
        // The whole function was byte-identical to ..\ol-mod-ffa. On 1649370 the target
        // is
        //     void __usercall sub_46E780(
        //         float *end@<ecx>, Bounds *bounds@<edx>,
        //         trace_t *results, float *start, int passEntityNum, int contentMask,
        //         unsigned __int8, char)          // SIX stack args, CALLER cleans 0x18
        //
        // read out of the decompilation: `*a3` is compared against 0.0 so a3 is the
        // trace_t whose first float is the fraction; `a2[3] + a2[4] + a2[5] == 0.0`
        // selects the point-trace branch, so a2 is a six-float Bounds -- exactly this
        // project's TraceBounds{midpoint[3], halfSize[3]}; and a4 and a1 are the two
        // endpoints, each offset by the bounds midpoint, with a4's components landing in
        // the LOWER slots of the pair, which makes a4 the start and a1 the end.
        //
        // The image proves the mapping without any of that reasoning. sub_46EA60 is a
        // pure passthrough:
        //     sub_46EA60(a, b, c, d, e, f)
        //         -> ecx = c, edx = d, push a, b, e, f, 0, 0; add esp, 18h
        // which is plain SV_Trace(results, start, end, bounds, passEntityNum,
        // contentMask) in the natural CoD order. sub_46E9C0 and sub_46EA10 are its point
        // -trace siblings and both pass a fixed zero-Bounds global in edx.
        //
        // What the carried version did: ecx got a POINTER TO AN IGNORE STRUCT where the
        // engine wanted the end position, edx got the END where it wanted the bounds,
        // a5 got the bounds POINTER where it wanted an int entity number, and a7/a8 were
        // never pushed at all, so the engine read two arguments out of this frame's
        // stack. Measured consequence, over 1349 hits in one run: ZERO upward normals,
        // every hit at fraction 0.0000 with the same hitId 2046, walkable never set --
        // so groundEntityNum was ENTITYNUM_NONE on every frame and the player rose about
        // one unit per pmove call, forever.
        void reportTraceWriteHighWater(
            const std::array<std::byte, sizeof(NativeTraceResult) + 512> &padded,
            const bool completed)
        {
            std::size_t highest{};
            for (auto index = padded.size(); index-- > 0;)
            {
                if (padded[index] != std::byte{})
                {
                    highest = index + 1;
                    break;
                }
            }
            static std::size_t reported{};
            if (highest <= reported)
                return;
            reported = highest;
            char line[192]{};
            std::snprintf(
                line, sizeof(line),
                "native state write sv_trace declared=%u wroteThrough=%u%s%s",
                static_cast<unsigned>(sizeof(NativeTraceResult)),
                static_cast<unsigned>(highest),
                highest > sizeof(NativeTraceResult)
                    ? " *** PAST THE DECLARED END ***"
                    : "",
                completed ? "" : " (faulted)");
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }

        bool invokeSVTrace(
            void *const function,
            const NativeIgnoreEntParams &ignore,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            const std::uint32_t contentMask,
            NativeTraceResult &result,
            NativeExceptionDetails &exceptionDetails) noexcept
        {
            if (!function || !contentMask)
                return false;
            const auto *const startPointer = start.data();
            const auto *const endPointer = end.data();
            const auto *const boundsPointer = &bounds;
            const auto mask = contentMask;
            // A5 IS AN ENTITY NUMBER, NOT A POINTER. The engine builds its own
            // {passEntity, -1, 1} triple from it; the 12-byte params struct this call
            // used to hand over in ECX is 3.3.3.3's shape and has no slot here, so the
            // owner-entity half of the filter is simply not expressible through this
            // entry point. Passing the base entity is what every wrapper in the image
            // does.
            const auto passEntity = ignore.baseEntity;
            const std::int32_t flagA7{};
            const std::int32_t flagA8{};
            // IS trace_t BIGGER THAN 0x28 ON THIS BUILD? NativeTraceResult is
            // byte-identical to the 3.3.3.3 tree, on a build where entityState grew
            // 0x110 -> 0x118 and playerState 0x3564 -> 0x3BBC. If it grew, the engine
            // writes past what we model and reads back fields we never initialise --
            // which is what a groundEntityNum flipping 2046/2047 on consecutive slices
            // at an unchanged origin looks like, because a deterministic trace cannot
            // otherwise give two answers.
            //
            // Same harness as section 43f: hand it the struct followed by a zeroed tail
            // and report the highest byte that changed. Zero rather than a fill pattern,
            // so a read past the end sees a null or a 0.0f; the slack absorbs an
            // overrun, which is what makes the measurement survivable.
            alignas(16) std::array<std::byte, sizeof(NativeTraceResult) + 512> padded{};
            auto *const resultPointer = padded.data();
            bool completed{};
            __try
            {
                __asm
                {
                    mov ecx, endPointer
                    mov edx, boundsPointer
                    push flagA8
                    push flagA7
                    push mask
                    push passEntity
                    push startPointer
                    push resultPointer
                    call function
                    add esp, 18h
                }
                completed = true;
            }
            __except (captureNativeException(
                GetExceptionInformation(), &exceptionDetails))
            {
                completed = false;
            }
            std::memcpy(&result, padded.data(), sizeof(result));
            reportTraceWriteHighWater(padded, completed);
            return completed;
        }

        const char *traceDifferenceName(
            const SvTraceComparisonDifference difference)
        {
            switch (difference)
            {
            case SvTraceComparisonDifference::None: return "none";
            case SvTraceComparisonDifference::Fraction: return "fraction";
            case SvTraceComparisonDifference::Normal: return "normal";
            case SvTraceComparisonDifference::SurfaceFlags:
                return "surface_flags";
            case SvTraceComparisonDifference::Contents: return "contents";
            case SvTraceComparisonDifference::HitType: return "hit_type";
            case SvTraceComparisonDifference::HitId: return "hit_id";
            case SvTraceComparisonDifference::ModelIndex: return "model_index";
            case SvTraceComparisonDifference::PartName: return "part_name";
            case SvTraceComparisonDifference::PartGroup: return "part_group";
            case SvTraceComparisonDifference::AllSolid: return "all_solid";
            case SvTraceComparisonDifference::StartSolid: return "start_solid";
            case SvTraceComparisonDifference::Walkable: return "walkable";
            }
            return "unknown";
        }

        std::optional<std::size_t> readableBytes(const void *address)
        {
            MEMORY_BASIC_INFORMATION memory{};
            if (!address || !VirtualQuery(address, &memory, sizeof(memory)) ||
                memory.State != MEM_COMMIT ||
                (memory.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
            {
                return std::nullopt;
            }
            const auto cursor = reinterpret_cast<std::uintptr_t>(address);
            const auto end = reinterpret_cast<std::uintptr_t>(memory.BaseAddress) +
                memory.RegionSize;
            if (cursor >= end)
                return std::nullopt;
            return end - cursor;
        }

        bool writableBytes(const void *const address, const std::size_t size)
        {
            if (!address || !size)
                return false;
            auto cursor = reinterpret_cast<std::uintptr_t>(address);
            if (size > std::numeric_limits<std::uintptr_t>::max() - cursor)
                return false;
            const auto end = cursor + size;
            while (cursor < end)
            {
                MEMORY_BASIC_INFORMATION memory{};
                if (!VirtualQuery(
                        reinterpret_cast<const void *>(cursor),
                        &memory,
                        sizeof(memory)) ||
                    memory.State != MEM_COMMIT ||
                    (memory.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
                {
                    return false;
                }
                const auto protection = memory.Protect & 0xFF;
                if (protection != PAGE_READWRITE &&
                    protection != PAGE_WRITECOPY &&
                    protection != PAGE_EXECUTE_READWRITE &&
                    protection != PAGE_EXECUTE_WRITECOPY)
                {
                    return false;
                }
                const auto regionEnd = reinterpret_cast<std::uintptr_t>(
                    memory.BaseAddress) +
                    static_cast<std::uintptr_t>(memory.RegionSize);
                if (regionEnd <= cursor)
                    return false;
                cursor = std::min<std::uintptr_t>(regionEnd, end);
            }
            return true;
        }

        bool readableSpan(const void *address, const std::size_t length)
        {
            if (!address)
                return false;
            if (!length)
                return true;

            auto cursor = reinterpret_cast<std::uintptr_t>(address);
            if (length > std::numeric_limits<std::uintptr_t>::max() - cursor)
                return false;
            const auto end = cursor + length;
            while (cursor < end)
            {
                MEMORY_BASIC_INFORMATION memory{};
                if (!VirtualQuery(
                        reinterpret_cast<const void *>(cursor),
                        &memory,
                        sizeof(memory)) ||
                    memory.State != MEM_COMMIT ||
                    (memory.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
                {
                    return false;
                }
                const auto regionEnd = reinterpret_cast<std::uintptr_t>(memory.BaseAddress) +
                    static_cast<std::uintptr_t>(memory.RegionSize);
                if (regionEnd <= cursor)
                    return false;
                cursor = std::min<std::uintptr_t>(regionEnd, end);
            }
            return true;
        }

        bool dobjGeomDiagnosticsEnabled()
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                const auto size = GetEnvironmentVariableA(
                    "OLMOD_DOBJ_GEOM_DIAGNOSTICS",
                    value.data(),
                    static_cast<DWORD>(value.size()));
                return size == 1 && value[0] == '1';
            }();
            return enabled;
        }

        bool hitboxDiagnosticsEnabled()
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                const auto size = GetEnvironmentVariableA(
                    "OLMOD_HITBOX_DIAGNOSTICS",
                    value.data(),
                    static_cast<DWORD>(value.size()));
                return size == 1 && value[0] == '1';
            }();
            return enabled;
        }

        // OLMOD(capsule-entity-collision): section 74 kill switch. out.exe's
        // 0x0046E780 is the CLIENT general trace, and its entity half walks the
        // client's own centity array -- the array a dedicated server never
        // fills. Setting this to 1 restores that call for a bisect; anything
        // else, including leaving it unset, uses the source per-entity path.
        bool nativeCapsuleTraceEnabled()
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                const auto size = GetEnvironmentVariableA(
                    "OLMOD_NATIVE_CAPSULE_TRACE",
                    value.data(),
                    static_cast<DWORD>(value.size()));
                return size == 1 && value[0] == '1';
            }();
            return enabled;
        }

        bool nativeTraceComparisonEnabled()
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                const auto size = GetEnvironmentVariableA(
                    "OLMOD_NATIVE_TRACE_COMPARISON",
                    value.data(),
                    static_cast<DWORD>(value.size()));
                return size == 1 && value[0] == '1';
            }();
            return enabled;
        }

        std::optional<std::string> readStringObject(const std::uint8_t *object)
        {
            const auto objectBytes = readableBytes(object);
            if (!objectBytes || *objectBytes < sizeof(const char *))
                return std::nullopt;
            const auto *text = *reinterpret_cast<const char *const *>(object);
            const auto textBytes = readableBytes(text);
            if (!textBytes)
                return std::nullopt;
            constexpr std::size_t MaximumLength = 128;
            const auto limit = std::min(*textBytes, MaximumLength);
            const auto end = std::find(text, text + limit, '\0');
            if (end == text || end == text + limit)
                return std::nullopt;
            return std::string(text, end);
        }

        bool validBookingName(const std::string_view value)
        {
            return !value.empty() && value.size() <= 64 &&
                std::ranges::all_of(value, [](const char character) {
                    return character == '_' || character == '-' ||
                        (character >= '0' && character <= '9') ||
                        (character >= 'A' && character <= 'Z') ||
                        (character >= 'a' && character <= 'z');
                });
        }

        bool asciiCaseInsensitiveEqual(
            const std::string_view left,
            const std::string_view right)
        {
            if (left.size() != right.size())
                return false;
            return std::ranges::equal(left, right, [](char a, char b) {
                const auto lower = [](const char value) {
                    return value >= 'A' && value <= 'Z'
                        ? static_cast<char>(value - 'A' + 'a')
                        : value;
                };
                return lower(a) == lower(b);
            });
        }

        std::optional<std::string> readCString(
            const char *text,
            const std::size_t maximumLength)
        {
            const auto textBytes = readableBytes(text);
            if (!textBytes)
                return std::nullopt;
            const auto limit = std::min(*textBytes, maximumLength);
            const auto end = std::find(text, text + limit, '\0');
            if (end == text || end == text + limit)
                return std::nullopt;
            return std::string(text, end);
        }

        std::optional<std::string> readStringTableCell(
            const StringTableCell &cell,
            const std::size_t maximumLength = 128)
        {
            if (!cell.value)
                return std::string{};
            const auto textBytes = readableBytes(cell.value);
            if (!textBytes)
                return std::nullopt;
            const auto limit = std::min(*textBytes, maximumLength);
            const auto end = std::find(cell.value, cell.value + limit, '\0');
            if (end == cell.value + limit)
                return std::nullopt;
            return std::string(cell.value, end);
        }

        std::optional<std::uint8_t> parseWeaponAttachmentSlot(
            const std::string_view name)
        {
            constexpr std::array<std::string_view, WeaponAttachmentSlotCount>
                SlotNames{
                    "wea", "sco", "muz", "bas", "hbs", "sto", "rai", "gri",
                    "bip", "sra", "iro", "mag", "cam", "cqc", "rof", "ret",
                };
            const auto slot = std::ranges::find(SlotNames, name);
            if (slot == SlotNames.end())
                return std::nullopt;
            return static_cast<std::uint8_t>(slot - SlotNames.begin());
        }

        const StringTable *readStringTable(
            const EngineBindings::DBFindXAssetHeader findAsset,
            const EngineBindings::DBIsXAssetDefault isDefault,
            const std::string_view name,
            const std::int32_t minimumColumns)
        {
            if (!findAsset)
                return nullptr;
            // A table that is in the pool but not loaded still comes back as
            // the default even with allowDefault=false, so ask separately too.
            const auto header =
                findAsset(AssetTypeStringTable, name.data(), false);
            if (header.data && isDefault &&
                isDefault(AssetTypeStringTable, name.data()))
            {
                return nullptr;
            }
            const auto *table = static_cast<const StringTable *>(header.data);
            if (!readableSpan(table, sizeof(*table)) ||
                table->columnCount < minimumColumns || table->columnCount > 256 ||
                table->rowCount <= 0 || table->rowCount > 4096 || !table->values)
            {
                return nullptr;
            }
            const auto tableName = readCString(table->name, 128);
            if (!tableName || !asciiCaseInsensitiveEqual(*tableName, name))
                return nullptr;
            const auto cellCount = static_cast<std::size_t>(table->columnCount) *
                static_cast<std::size_t>(table->rowCount);
            if (!readableSpan(table->values, cellCount * sizeof(StringTableCell)))
                return nullptr;
            return table;
        }

        std::optional<const StringTableCell *> findStringTableRow(
            const StringTable &table,
            const std::string_view key)
        {
            for (std::int32_t rowIndex = 0; rowIndex < table.rowCount; ++rowIndex)
            {
                const auto *row = table.values +
                    static_cast<std::size_t>(rowIndex) * table.columnCount;
                const auto rowName = readStringTableCell(row[0]);
                if (!rowName)
                    return std::nullopt;
                if (*rowName == key)
                    return row;
            }
            return static_cast<const StringTableCell *>(nullptr);
        }
    }

    std::string_view ServerAnimationInitializationStatusName(
        const ServerAnimationInitializationStatus status)
    {
        switch (status)
        {
        case ServerAnimationInitializationStatus::NotInitialized:
            return "not_initialized";
        case ServerAnimationInitializationStatus::Ready: return "ready";
        case ServerAnimationInitializationStatus::InvalidBinding:
            return "invalid_binding";
        case ServerAnimationInitializationStatus::WrongThread:
            return "wrong_thread";
        case ServerAnimationInitializationStatus::ContextBusy:
            return "context_busy";
        case ServerAnimationInitializationStatus::BeginLoadAnimTreesFailed:
            return "begin_load_anim_trees_failed";
        case ServerAnimationInitializationStatus::LoadAnimTreesFailed:
            return "load_anim_trees_failed";
        case ServerAnimationInitializationStatus::
                AnimationScriptAssetsUnavailable:
            return "animation_script_assets_unavailable";
        case ServerAnimationInitializationStatus::FindAnimsFailed:
            return "find_anims_failed";
        case ServerAnimationInitializationStatus::ParseAnimScriptFailed:
            return "parse_anim_script_failed";
        case ServerAnimationInitializationStatus::PrecacheAnimTreesFailed:
            return "precache_anim_trees_failed";
        case ServerAnimationInitializationStatus::FindAnimTreesFailed:
            return "find_anim_trees_failed";
        case ServerAnimationInitializationStatus::EndLoadAnimTreesFailed:
            return "end_load_anim_trees_failed";
        case ServerAnimationInitializationStatus::FinalizePlayerAnimsFailed:
            return "finalize_player_anims_failed";
        case ServerAnimationInitializationStatus::InvalidOutput:
            return "invalid_output";
        }
        return "unknown";
    }

    const char *SV_CurrentNativeStage()
    {
        const auto *const stage = CurrentNativeStage.load(std::memory_order_acquire);
        return stage ? stage : "none";
    }

    void SV_SetCurrentNativeStage(const char *const stage)
    {
        CurrentNativeStage.store(stage ? stage : "none", std::memory_order_release);
    }

    bool EngineBindings::bind()
    {
        // OLMOD(engine-binding-transaction): resolved pointers are staged in
        // this long-lived adapter, but validity is published only after build,
        // prefix, runtime-slot, message, and glass-bridge checks all succeed.
        // A failed rebind must also revoke a previously committed publication.
        bindingCommitted_.store(false, std::memory_order_release);
        module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module_)
            return false;

        const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module_);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return false;
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(module_ + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->FileHeader.TimeDateStamp != ExpectedTimestamp ||
            nt->OptionalHeader.SizeOfImage != ExpectedImageSize)
        {
            return false;
        }

        const auto nativeEntityPrefixFailure =
            !std::equal(
                SVLinkEntityPrefix.begin(),
                SVLinkEntityPrefix.end(),
                module_ + SVLinkEntityRva)
            ? "SV_LinkEntity"
            : !std::equal(
                  SVUnlinkEntityPrefix.begin(),
                  SVUnlinkEntityPrefix.end(),
                  module_ + SVUnlinkEntityRva)
            ? "SV_UnlinkEntity"
            : !std::equal(
                  SVTracePrefix.begin(),
                  SVTracePrefix.end(),
                  module_ + SVTraceRva)
            ? "SV_Trace"
            : nullptr;
        if (nativeEntityPrefixFailure)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("native entity binding prefix mismatch function=") +
                    nativeEntityPrefixFailure);
            return false;
        }

        const auto playerDObjPrefixFailure =
            !std::equal(
                NativeLerpFrameAccessorInitializePrefix.begin(),
                NativeLerpFrameAccessorInitializePrefix.end(),
                module_ + NativeLerpFrameAccessorInitializeRva)
            ? "native lerp-frame accessor initializer"
            : !std::equal(
                BGPlayerAnimationPrefix.begin(),
                BGPlayerAnimationPrefix.end(),
                module_ + BGPlayerAnimationRva)
            ? "BG_PlayerAnimation"
            :
            !std::equal(
                BGUpdatePlayerDObjPrefix.begin(),
                BGUpdatePlayerDObjPrefix.end(),
                module_ + BGUpdatePlayerDObjRva)
            ? "BG_UpdatePlayerDObj"
            // CODDIFF(character_customization): the world character model
            // resolver is checked on 3.3.3.3 and CANNOT be checked here. It
            // does not exist in OLfinal -- see re/OLFINAL-FFA-HANDOFF.md §16a
            // and §18d. OLfinal replaced the whole selector/slot-base/name-table
            // scheme with an item-driven one, so there is no counterpart address
            // to guard, and leaving the 3.3.3.3 RVA here would have guarded an
            // unrelated function that happens to live there.
            : !std::equal(
                  DObjFreePrefix.begin(),
                  DObjFreePrefix.end(),
                  module_ + DObjFreeRva)
            ? "DObjFree"
            : !std::equal(
                  ServerDObjCreatePrefix.begin(),
                  ServerDObjCreatePrefix.end(),
                  module_ + ServerDObjCreateRva)
            ? "Com_ServerDObjCreate"
            : !std::equal(
                  ServerDObjGetSuffix.begin(),
                  ServerDObjGetSuffix.end(),
                  module_ + ServerDObjGetRva + 5)
            ? "Com_GetServerDObj"
            : nullptr;
        if (playerDObjPrefixFailure)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("player DObj binding prefix mismatch function=") +
                    playerDObjPrefixFailure);
            return false;
        }

        if (!std::equal(ComFramePrefix.begin(), ComFramePrefix.end(), module_ + ComFrameRva) ||
            !std::equal(
                DBFindXAssetHeaderPrefix.begin(),
                DBFindXAssetHeaderPrefix.end(),
                module_ + DBFindXAssetHeaderRva) ||
            !std::equal(
                DBIsXAssetDefaultPrefix.begin(),
                DBIsXAssetDefaultPrefix.end(),
                module_ + DBIsXAssetDefaultRva) ||
            !std::equal(
                DBLinkXAssetEntryPrefix.begin(),
                DBLinkXAssetEntryPrefix.end(),
                module_ + DBLinkXAssetEntryRva) ||
            !std::equal(MsgInitPrefix.begin(), MsgInitPrefix.end(), module_ + MsgInitRva) ||
            !std::equal(
                MsgWriteBitsPrefix.begin(),
                MsgWriteBitsPrefix.end(),
                module_ + MsgWriteBitsRva) ||
            !std::equal(
                MsgWriteStringPrefix.begin(),
                MsgWriteStringPrefix.end(),
                module_ + MsgWriteStringRva) ||
            !std::equal(
                LevelZoneLoadPrefix.begin(),
                LevelZoneLoadPrefix.end(),
                module_ + LevelZoneLoadRva) ||
            !std::equal(
                CollisionMapLoadPrefix.begin(),
                CollisionMapLoadPrefix.end(),
                module_ + CollisionMapLoadRva) ||
            !std::equal(
                CollisionWorldLinkPrefix.begin(),
                CollisionWorldLinkPrefix.end(),
                module_ + CollisionWorldLinkRva) ||
            !std::equal(
                CCSClearPrefix.begin(),
                CCSClearPrefix.end(),
                module_ + CCSClearRva) ||
            !std::equal(
                CCSInitializePrefix.begin(),
                CCSInitializePrefix.end(),
                module_ + CCSInitializeRva) ||
            !std::equal(
                CCSGetConstantStringPrefix.begin(),
                CCSGetConstantStringPrefix.end(),
                module_ + CCSGetConstantStringRva) ||
            !std::equal(TracePrefix.begin(), TracePrefix.end(), module_ + TraceRva) ||
            !std::equal(
                WorldTracePrefix.begin(),
                WorldTracePrefix.end(),
                module_ + WorldTraceRva) ||
            !std::equal(
                TransformedBrushModelTracePrefix.begin(),
                TransformedBrushModelTracePrefix.end(),
                module_ + TransformedBrushModelTraceRva) ||
            !std::equal(
                TransformedCapsuleTracePrefix.begin(),
                TransformedCapsuleTracePrefix.end(),
                module_ + TransformedCapsuleTraceRva) ||
            !std::equal(
                CalcTraceExtentsPrefix.begin(),
                CalcTraceExtentsPrefix.end(),
                module_ + CalcTraceExtentsRva) ||
            !std::equal(
                PointTraceToEntitiesPrefix.begin(),
                PointTraceToEntitiesPrefix.end(),
                module_ + PointTraceToEntitiesRva) ||
            !std::equal(
                DObjGeomTracelinePartBitsPrefix.begin(),
                DObjGeomTracelinePartBitsPrefix.end(),
                module_ + DObjGeomTracelinePartBitsRva) ||
            !std::equal(
                DObjContentsTracelinePartBitsPrefix.begin(),
                DObjContentsTracelinePartBitsPrefix.end(),
                module_ + DObjContentsTracelinePartBitsRva) ||
            !std::equal(
                DObjTracelinePrefix.begin(),
                DObjTracelinePrefix.end(),
                module_ + DObjTracelineRva) ||
            !std::equal(DObjContentsTracelinePrefix.begin(),
                DObjContentsTracelinePrefix.end(), module_ + DObjContentsTracelineRva) ||
            !std::equal(PointTraceStaticModelsPrefix.begin(),
                PointTraceStaticModelsPrefix.end(), module_ + PointTraceStaticModelsRva) ||
            !std::equal(
                DObjCalcSkelPrefix.begin(),
                DObjCalcSkelPrefix.end(),
                module_ + DObjCalcSkelRva) ||
            !std::equal(
                BGGetPlayerEyePositionPrefix.begin(),
                BGGetPlayerEyePositionPrefix.end(),
                module_ + BGGetPlayerEyePositionRva) ||
            !std::equal(
                BulletEndposPrefix.begin(),
                BulletEndposPrefix.end(),
                module_ + BulletEndposRva) ||
            !std::equal(
                ByteDirectionsPrefix.begin(),
                ByteDirectionsPrefix.end(),
                module_ + ByteDirectionsRva) ||
            !std::equal(
                ViewMovementDamageKickPrefix.begin(),
                ViewMovementDamageKickPrefix.end(),
                module_ + ViewMovementDamageKickRva) ||
            !std::equal(
                ViewMovementIdleAnglesPrefix.begin(),
                ViewMovementIdleAnglesPrefix.end(),
                module_ + ViewMovementIdleAnglesRva) ||
            !std::equal(
                ViewMovementBobAnglesPrefix.begin(),
                ViewMovementBobAnglesPrefix.end(),
                module_ + ViewMovementBobAnglesRva) ||
            !std::equal(
                ViewMovementAdsBobPrefix.begin(),
                ViewMovementAdsBobPrefix.end(),
                module_ + ViewMovementAdsBobRva) ||
            !std::equal(
                WeaponMovementBasePrefix.begin(),
                WeaponMovementBasePrefix.end(),
                module_ + WeaponMovementBaseRva) ||
            !std::equal(
                WeaponMovementSwayPrefix.begin(),
                WeaponMovementSwayPrefix.end(),
                module_ + WeaponMovementSwayRva) ||
            !std::equal(
                WeaponMovementRecoilPrefix.begin(),
                WeaponMovementRecoilPrefix.end(),
                module_ + WeaponMovementRecoilRva) ||
            !std::equal(
                WeaponMovementBobPrefix.begin(),
                WeaponMovementBobPrefix.end(),
                module_ + WeaponMovementBobRva) ||
            !std::equal(
                SetWeaponMovementAnglesPrefix.begin(),
                SetWeaponMovementAnglesPrefix.end(),
                module_ + SetWeaponMovementAnglesRva) ||
            !std::equal(
                AnglesToQuaternionPrefix.begin(),
                AnglesToQuaternionPrefix.end(),
                module_ + AnglesToQuaternionRva) ||
            !std::equal(
                AngleVectorsPrefix.begin(),
                AngleVectorsPrefix.end(),
                module_ + AngleVectorsRva) ||
            !std::equal(
                MatrixMultiplyPrefix.begin(),
                MatrixMultiplyPrefix.end(),
                module_ + MatrixMultiplyRva) ||
            !std::equal(
                AxisToAnglesPrefix.begin(),
                AxisToAnglesPrefix.end(),
                module_ + AxisToAnglesRva) ||
            !std::equal(
                PmoveSinglePrefix.begin(),
                PmoveSinglePrefix.end(),
                module_ + PmoveSingleRva) ||
            !std::equal(
                PMSetPitchValuesPrefix.begin(),
                PMSetPitchValuesPrefix.end(),
                module_ + PMSetPitchValuesRva) ||
            !std::equal(
                PlayerStateToEntityStatePrefix.begin(),
                PlayerStateToEntityStatePrefix.end(),
                module_ + PlayerStateToEntityStateRva) ||
            !std::equal(
                BGAnimScriptEventPrefix.begin(),
                BGAnimScriptEventPrefix.end(),
                module_ + BGAnimScriptEventRva) ||
            !std::equal(
                BGFindAnimsPrefix.begin(),
                BGFindAnimsPrefix.end(),
                module_ + BGFindAnimsRva) ||
            !std::equal(
                BGAnimParseAnimScriptPrefix.begin(),
                BGAnimParseAnimScriptPrefix.end(),
                module_ + BGAnimParseAnimScriptRva) ||
            !std::equal(
                BGLoadAnimTreesPrefix.begin(),
                BGLoadAnimTreesPrefix.end(),
                module_ + BGLoadAnimTreesRva) ||
            !std::equal(
                ScrCreateObjectPrefix.begin(),
                ScrCreateObjectPrefix.end(),
                module_ + ScrCreateObjectRva) ||
            !std::equal(
                ScrPrecacheAnimTreesPrefix.begin(),
                ScrPrecacheAnimTreesPrefix.end(),
                module_ + ScrPrecacheAnimTreesRva) ||
            !std::equal(
                BGFindAnimTreesPrefix.begin(),
                BGFindAnimTreesPrefix.end(),
                module_ + BGFindAnimTreesRva) ||
            !std::equal(
                BGFinalizePlayerAnimsPrefix.begin(),
                BGFinalizePlayerAnimsPrefix.end(),
                module_ + BGFinalizePlayerAnimsRva) ||
            !std::equal(
                MantleCreateAnimsPrefix.begin(),
                MantleCreateAnimsPrefix.end(),
                module_ + MantleCreateAnimsRva) ||
            !std::equal(
                HunkAllocXAnimPrefix.begin(),
                HunkAllocXAnimPrefix.end(),
                module_ + HunkAllocXAnimRva) ||
            !std::equal(
                WeaponLookupPrefix.begin(),
                WeaponLookupPrefix.end(),
                module_ + WeaponLookupRva) ||
            !std::equal(
                WeaponResolverPrefix.begin(),
                WeaponResolverPrefix.end(),
                module_ + WeaponResolverRva) ||
            !std::equal(
                AttachmentLookupPrefix.begin(),
                AttachmentLookupPrefix.end(),
                module_ + AttachmentLookupRva) ||
            !std::equal(
                WeaponRegistryResetPrefix.begin(),
                WeaponRegistryResetPrefix.end(),
                module_ + WeaponRegistryResetRva) ||
            !std::equal(
                WeaponRegistryInitializePrefix.begin(),
                WeaponRegistryInitializePrefix.end(),
                module_ + WeaponRegistryInitializeRva) ||
            !std::equal(
                ZoneLoadedPrefix.begin(),
                ZoneLoadedPrefix.end(),
                module_ + ZoneLoadedRva) ||
            // CODDIFF(client_loadout_capture): WeaponSlotReadStaged is NOT guarded
            // here, because no 1649370 address for it has been established -- the only
            // one in this tree is CodolWeaponResolve.py's 0x1945B0, and that file
            // targets codoMP_client_shipRetail.exe.
            //
            // CurrentCharacterGet IS guarded now, and the TODO that used to sit here
            // is RESOLVED ON ITS OWN TERMS. It said: "currentCharacterIndex" is at
            // 0x00DCAB98 and 65 functions reference it, so the string alone does not
            // pick the accessor out of the family -- the exit condition is a body match
            // against 0x0068A0E0's shape, not another string hit.
            //
            // sub_6B87C0 is that body, in thirteen instructions:
            //     mov eax, dword_E567C0 / cmp eax, -1 / jnz ret
            //     push 0 / push offset "currentCharacterIndex" / call sub_512120
            //     mov dword_E567C0, eax / test eax,eax / jns ret / xor eax,eax / mov back
            // -- a cached lookup that clamps a negative to zero, which is exactly
            // 0x0068A0E0's shape, and dword_E567C0 is written by nothing but its own
            // two stores. The 65 string references are the CONSUMERS.
            //
            // It was also never really unestablished: CodolMatchFlow.py's 1649370 block
            // carries CURRENT_CHARACTER_GET_RVA = 0x2B87C0 and calls it every run.
            !std::equal(
                CharacterCurrentItemsCopyPrefix.begin(),
                CharacterCurrentItemsCopyPrefix.end(),
                module_ + CharacterCurrentItemsCopyRva) ||
            !std::equal(
                CurrentCharacterGetPrefix.begin(),
                CurrentCharacterGetPrefix.end(),
                module_ + CurrentCharacterGetRva) ||
            !std::equal(
                CharacterSlotGetPrefix.begin(),
                CharacterSlotGetPrefix.end(),
                module_ + CharacterSlotGetRva) ||
            !std::equal(
                CharacterRecordFillDefaultsPrefix.begin(),
                CharacterRecordFillDefaultsPrefix.end(),
                module_ + CharacterRecordFillDefaultsRva) ||
            !std::equal(
                CharacterRecordToSelectionNamesPrefix.begin(),
                CharacterRecordToSelectionNamesPrefix.end(),
                module_ + CharacterRecordToSelectionNamesRva) ||
            // CODDIFF(character_customization): CharacterSelectionResolve is
            // absent by design on OLfinal -- §16a. Not guarded, not bound.
            !std::equal(
                ConfigStringGetPrefix.begin(),
                ConfigStringGetPrefix.end(),
                module_ + ConfigStringGetRva))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "engine binding validation failed stage=function_prefixes");
            return false;
        }

        dbFindXAssetHeader_ = reinterpret_cast<DBFindXAssetHeader>(
            module_ + DBFindXAssetHeaderRva);
        dbIsXAssetDefault_ = reinterpret_cast<DBIsXAssetDefault>(
            module_ + DBIsXAssetDefaultRva);
        dbLinkXAssetEntry_ = reinterpret_cast<DBLinkXAssetEntry>(
            module_ + DBLinkXAssetEntryRva);
        msgInit_ = module_ + MsgInitRva;
        msgWriteBits_ = module_ + MsgWriteBitsRva;
        msgWriteString_ = module_ + MsgWriteStringRva;
        levelZoneLoad_ = module_ + LevelZoneLoadRva;
        collisionMapLoad_ = module_ + CollisionMapLoadRva;
        collisionWorldLink_ = module_ + CollisionWorldLinkRva;
        ccsClear_ = module_ + CCSClearRva;
        ccsInitialize_ = reinterpret_cast<CCSInitialize>(module_ + CCSInitializeRva);
        ccsGetConstantString_ = module_ + CCSGetConstantStringRva;
        trace_ = reinterpret_cast<Trace>(module_ + TraceRva);
        worldTrace_ = module_ + WorldTraceRva;
        transformedBrushModelTrace_ = module_ + TransformedBrushModelTraceRva;
        transformedCapsuleTrace_ = module_ + TransformedCapsuleTraceRva;
        calcTraceExtents_ = module_ + CalcTraceExtentsRva;
        pointTraceToEntities_ = module_ + PointTraceToEntitiesRva;
        dobjGeomTracelinePartBits_ =
            module_ + DObjGeomTracelinePartBitsRva;
        dobjContentsTracelinePartBits_ =
            module_ + DObjContentsTracelinePartBitsRva;
        dobjTraceline_ = module_ + DObjTracelineRva;
        dobjContentsTraceline_ = module_ + DObjContentsTracelineRva;
        pointTraceStaticModels_ = module_ + PointTraceStaticModelsRva;
        dobjCalcSkel_ = module_ + DObjCalcSkelRva;
        gEntities_ = module_ + GEntitiesRva;
        serverGameEntitiesPointer_ = reinterpret_cast<void **>(
            module_ + ServerGameEntitiesPointerRva);
        serverGameEntityCount_ = reinterpret_cast<std::uint32_t *>(
            module_ + ServerGameEntityCountRva);
        svLinkEntity_ = module_ + SVLinkEntityRva;
        svUnlinkEntity_ = module_ + SVUnlinkEntityRva;
        svTrace_ = module_ + SVTraceRva;
        bgGetPlayerEyePosition_ = reinterpret_cast<BGGetPlayerEyePosition>(
            module_ + BGGetPlayerEyePositionRva);
        bulletEndpos_ = module_ + BulletEndposRva;
        viewMovementDamageKick_ = module_ + ViewMovementDamageKickRva;
        viewMovementIdleAngles_ = module_ + ViewMovementIdleAnglesRva;
        viewMovementBobAngles_ = module_ + ViewMovementBobAnglesRva;
        viewMovementAdsBob_ = module_ + ViewMovementAdsBobRva;
        weaponMovementBase_ = module_ + WeaponMovementBaseRva;
        weaponMovementSway_ = module_ + WeaponMovementSwayRva;
        weaponMovementRecoil_ = module_ + WeaponMovementRecoilRva;
        weaponMovementBob_ = module_ + WeaponMovementBobRva;
        setWeaponMovementAngles_ = module_ + SetWeaponMovementAnglesRva;
        anglesToQuaternion_ = module_ + AnglesToQuaternionRva;
        angleVectors_ = module_ + AngleVectorsRva;
        matrixMultiply_ = module_ + MatrixMultiplyRva;
        axisToAngles_ = module_ + AxisToAnglesRva;
        pmoveSingle_ = module_ + PmoveSingleRva;
        pmSetPitchValues_ = module_ + PMSetPitchValuesRva;
        playerStateToEntityState_ = module_ + PlayerStateToEntityStateRva;
        bgAnimScriptEvent_ = module_ + BGAnimScriptEventRva;
        bgFindAnims_ = module_ + BGFindAnimsRva;
        bgAnimParseAnimScript_ = module_ + BGAnimParseAnimScriptRva;
        bgLoadAnimTrees_ = module_ + BGLoadAnimTreesRva;
        scrCreateObject_ = module_ + ScrCreateObjectRva;
        scrPrecacheAnimTrees_ = module_ + ScrPrecacheAnimTreesRva;
        bgFindAnimTrees_ = module_ + BGFindAnimTreesRva;
        bgFinalizePlayerAnims_ = module_ + BGFinalizePlayerAnimsRva;
        nativeLerpFrameAccessorInitialize_ =
            module_ + NativeLerpFrameAccessorInitializeRva;
        bgPlayerAnimation_ = module_ + BGPlayerAnimationRva;
        bgUpdatePlayerDObj_ = module_ + BGUpdatePlayerDObjRva;
        // CODDIFF(character_customization): left null on OLfinal. §16a.
        worldCharacterModelResolve_ = nullptr;
        mantleCreateAnims_ = module_ + MantleCreateAnimsRva;
        mantleAnims_ = reinterpret_cast<void **>(module_ + MantleAnimsRva);
        hunkAllocXAnim_ = module_ + HunkAllocXAnimRva;
        xanimFreeInfo_ = module_ + XAnimFreeInfoRva;
        dobjFree_ = module_ + DObjFreeRva;
        serverDObjGet_ = module_ + ServerDObjGetRva;
        serverDObjCreate_ = module_ + ServerDObjCreateRva;
        nativeLerpFrameZeroVector_ =
            reinterpret_cast<const std::byte *>(
                module_ + NativeLerpFrameZeroVectorRva);
        nativeLerpFrameSetKey_ =
            reinterpret_cast<const std::uint32_t *>(
                module_ + NativeLerpFrameSetKeyRva);
        nativeLerpFrameGetKey_ =
            reinterpret_cast<const std::uint32_t *>(
                module_ + NativeLerpFrameGetKeyRva);
        nativePlayerStateAccessorSetKey_ =
            reinterpret_cast<const std::uint32_t *>(
                module_ + NativePlayerStateAccessorSetKeyRva);
        nativePlayerStateAccessorGetKey_ =
            reinterpret_cast<const std::uint32_t *>(
                module_ + NativePlayerStateAccessorGetKeyRva);
        ServerDObjEntityBase.store(
            static_cast<std::byte *>(gEntities_), std::memory_order_release);
        ServerDObjMap.store(
            reinterpret_cast<std::uint16_t *>(module_ + ServerDObjMapRva),
            std::memory_order_release);
        ServerDObjInUse.store(
            reinterpret_cast<std::uint8_t *>(module_ + ServerDObjInUseRva),
            std::memory_order_release);
        ServerDObjFreeCount.store(
            reinterpret_cast<std::uint32_t *>(
                module_ + ServerDObjFreeCountRva),
            std::memory_order_release);
        ServerDObjPool.store(
            reinterpret_cast<std::byte *>(module_ + ServerDObjPoolRva),
            std::memory_order_release);
        DObjFreeTarget.store(dobjFree_, std::memory_order_release);
        ServerDObjGetTarget.store(
            serverDObjGet_, std::memory_order_release);
        ServerDObjCreateTarget.store(
            serverDObjCreate_, std::memory_order_release);
        pmoveTraceHandlerSlot_ = reinterpret_cast<Trace *>(
            module_ + PmoveHandlersRva);
        clientPmoveTrace_ = trace_;
        animConditionBasePointer_ = reinterpret_cast<std::byte **>(
            module_ + AnimConditionBasePointerRva);
        animScriptDataPointer_ = reinterpret_cast<std::byte **>(
            module_ + AnimScriptDataPointerRva);
        if (!writableBytes(pmoveTraceHandlerSlot_, sizeof(Trace) * 2) ||
            pmoveTraceHandlerSlot_[0] != clientPmoveTrace_ ||
            pmoveTraceHandlerSlot_[1] != nullptr ||
            !writableBytes(animConditionBasePointer_, sizeof(void *)) ||
            !writableBytes(animScriptDataPointer_, sizeof(void *)) ||
            !writableBytes(mantleAnims_, sizeof(void *) * 2))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "engine binding validation failed stage=runtime_slots");
            return false;
        }
        // CODDIFF(client_loadout_capture): unbound on OLfinal -- no address is
        // established on 1649370 for either. Every consumer already null-checks
        // these (currentCharacterIndex() and readStagedWeaponSlot() return
        // nullopt), so the loadout-capture path degrades rather than misreads.
        // Leaving them pointing at the 3.3.3.3 RVAs would have been the silent
        // failure instead: a plausible address, called through a function
        // pointer, on a build where it is some unrelated function.
        // weaponSlotReadStaged_ IS still unestablished: the only address anywhere in this
        // tree is CodolWeaponResolve.py's 0x1945B0, and that file targets
        // codoMP_client_shipRetail.exe -- 3.3.3.3. Leaving it null is correct.
        weaponSlotReadStaged_ = 0;
        // ...but out.exe builds the same values itself, and THAT is bindable. See
        // LoadoutRecordBuildRva for why the earlier "no such ladder" scan missed it.
        loadoutRecordBuild_ = reinterpret_cast<LoadoutRecordBuild>(
            module_ + LoadoutRecordBuildRva);
        // ...but the VALUES it was for are reachable through the profile
        // document instead -- see WeaponClassFieldGetRva.
        weaponClassFieldGet_ = module_ + WeaponClassFieldGetRva;
        // currentCharacterGet_ IS NOT, and the comment above used to say it was. See the
        // CODDIFF on CurrentCharacterGetRva: CodolMatchFlow.py's 1649370 block has had
        // the address all along and exercises it every run.
        currentCharacterGet_ = reinterpret_cast<CurrentCharacterGet>(
            module_ + CurrentCharacterGetRva);
        characterSlotGet_ = reinterpret_cast<CharacterSlotGet>(
            module_ + CharacterSlotGetRva);
        characterRecordFillDefaults_ = module_ + CharacterRecordFillDefaultsRva;
        characterRecordToSelectionNames_ =
            module_ + CharacterRecordToSelectionNamesRva;
        characterCurrentItemsCopy_ = module_ + CharacterCurrentItemsCopyRva;
        // CODDIFF(character_customization): absent by design on OLfinal. §16a.
        characterSelectionResolve_ = 0;
        configStringGet_ = module_ + ConfigStringGetRva;
        weaponLookup_ = reinterpret_cast<WeaponLookup>(module_ + WeaponLookupRva);
        weaponResolver_ = reinterpret_cast<WeaponResolver>(module_ + WeaponResolverRva);
        attachmentLookup_ = reinterpret_cast<AttachmentLookup>(
            module_ + AttachmentLookupRva);
        weaponRegistryReset_ = reinterpret_cast<WeaponRegistryReset>(
            module_ + WeaponRegistryResetRva);
        weaponRegistryInitialize_ = reinterpret_cast<WeaponRegistryInitialize>(
            module_ + WeaponRegistryInitializeRva);
        weaponKnifeStatsLoad_ = reinterpret_cast<WeaponKnifeStatsLoad>(
            module_ + WeaponKnifeStatsLoadRva);
        zoneLoaded_ = reinterpret_cast<ZoneLoaded>(module_ + ZoneLoadedRva);
        if (!validateMessageBindings())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "engine binding validation failed stage=message_bindings");
            return false;
        }
        if (!installBrushTraceGlassBridge(module_))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "engine binding validation failed stage=glass_bridge");
            return false;
        }
        static_cast<void>(CCS_Initialized());
        bindingCommitted_.store(true, std::memory_order_release);
        return true;
    }

    bool EngineBindings::valid() const
    {
        // OLMOD(engine-binding-transaction): non-null staged pointers cannot
        // substitute for the successful completion of bind(). In particular,
        // message validation and glass-bridge failures happen after assignment.
        return bindingCommitted_.load(std::memory_order_acquire) && module_ &&
            dbFindXAssetHeader_ &&
            dbIsXAssetDefault_ &&
            msgInit_ && msgWriteBits_ &&
            msgWriteString_ && levelZoneLoad_ && collisionMapLoad_ &&
            collisionWorldLink_ && ccsClear_ && ccsInitialize_ &&
            trace_ && worldTrace_ && transformedBrushModelTrace_ &&
            transformedCapsuleTrace_ && calcTraceExtents_ &&
            pointTraceToEntities_ && dobjGeomTracelinePartBits_ &&
            dobjContentsTracelinePartBits_ && dobjTraceline_ &&
            dobjContentsTraceline_ && pointTraceStaticModels_ &&
            dobjCalcSkel_ && gEntities_ && svLinkEntity_ &&
            svUnlinkEntity_ && svTrace_ && bgGetPlayerEyePosition_ &&
            bulletEndpos_ &&
            viewMovementDamageKick_ && viewMovementIdleAngles_ &&
            viewMovementBobAngles_ && viewMovementAdsBob_ &&
            weaponMovementBase_ && weaponMovementSway_ &&
            weaponMovementRecoil_ && weaponMovementBob_ &&
            setWeaponMovementAngles_ && anglesToQuaternion_ && angleVectors_ &&
            matrixMultiply_ &&
            axisToAngles_ &&
            pmoveSingle_ && pmSetPitchValues_ &&
            playerStateToEntityState_ && bgAnimScriptEvent_ &&
            bgFindAnims_ && bgAnimParseAnimScript_ &&
            bgLoadAnimTrees_ && scrCreateObject_ &&
            scrPrecacheAnimTrees_ && bgFindAnimTrees_ &&
            bgFinalizePlayerAnims_ && nativeLerpFrameAccessorInitialize_ &&
            bgPlayerAnimation_ &&
            bgUpdatePlayerDObj_ &&
            mantleCreateAnims_ && mantleAnims_ &&
            hunkAllocXAnim_ && dobjFree_ && serverDObjGet_ &&
            serverDObjCreate_ && nativeLerpFrameZeroVector_ &&
            nativeLerpFrameSetKey_ && nativeLerpFrameGetKey_ &&
            pmoveTraceHandlerSlot_ && clientPmoveTrace_ &&
            animConditionBasePointer_ && animScriptDataPointer_ &&
            characterCurrentItemsCopy_ &&
            configStringGet_ && weaponLookup_ && dbLinkXAssetEntry_ &&
            weaponResolver_ && attachmentLookup_ && weaponRegistryReset_ &&
            weaponRegistryInitialize_ && zoneLoaded_;
        // CODDIFF(character_customization, client_loadout_capture): four
        // pointers that 3.3.3.3 requires here are deliberately NOT part of
        // validity on OLfinal -- worldCharacterModelResolve_ and
        // characterSelectionResolve_ because §16a establishes the subsystem is
        // absent from the build, weaponSlotReadStaged_ and currentCharacterGet_
        // because no 1649370 address is established for either.
        //
        // Keeping them in this conjunction is what made the first version of
        // this change fail silently: every target still built and all six test
        // suites still passed, while valid() would have returned false on the
        // first frame and taken the entire engine binding with it. Nothing in
        // the SERVER frame calls any of the four; see
        // clientLoadoutBindingsAvailable() for the one path that does.
    }

    std::optional<std::array<float,3>> EngineBindings::directionToAngles(
        const std::array<float,3> &direction) const
    {
        constexpr std::size_t rva = 0x364C10; // CODREF(out.exe vectoangles 764C10).
        constexpr std::array<std::uint8_t, 16> prefix{
            0x55,0x8B,0xEC,0xD9,0x46,0x04,0x83,0xEC,0x08,0xD9,0xEE,0xD9,0xC0,0xDD,0xEA,0xDF};
        if (!bindingCommitted_.load(std::memory_order_acquire) || !module_ ||
            !std::ranges::all_of(direction, [](float x) { return std::isfinite(x); }) ||
            !readableSpan(module_ + rva,prefix.size()) ||
            !std::equal(prefix.begin(),prefix.end(),module_ + rva)) return std::nullopt;
        std::array<float,3> angles;
        angles.fill(std::numeric_limits<float>::quiet_NaN());
        const NativeStageScope stage("vectoangles");
        if (!invokeDirectionToAngles(module_ + rva,direction.data(),angles.data()) ||
            !std::ranges::all_of(angles, [](float x) { return std::isfinite(x); }))
            return std::nullopt;
        return angles;
    }

    std::optional<SvGrenadeLaunchParameters> EngineBindings::resolveGrenadeLaunchParameters(
        const std::uint16_t weapon) const
    {
        if (!bindingCommitted_.load(std::memory_order_acquire) || !module_ ||
            !weapon || weapon > MaximumWeaponAssetIndex) return std::nullopt;
        const auto *address = module_ + WeaponDefinitionsRva + weapon * sizeof(void *);
        if (!readableSpan(address,sizeof(void *))) return std::nullopt;
        const auto *definition = *reinterpret_cast<const std::uint8_t *const *>(address);
        constexpr std::size_t requiredBytes = 3838; // final confirmed bool +3837
        if (!readableSpan(definition,requiredBytes)) return std::nullopt;
        return SV_ReadGrenadeLaunchParameters(weapon,{definition,requiredBytes});
    }

    std::optional<SvGrenadeBlastParameters> EngineBindings::resolveGrenadeBlastParameters(
        const std::uint16_t weapon) const
    {
        if (!bindingCommitted_.load(std::memory_order_acquire) || !module_ ||
            !weapon || weapon > MaximumWeaponAssetIndex) return std::nullopt;
        const auto *address = module_ + WeaponDefinitionsRva + weapon * sizeof(void *);
        if (!readableSpan(address,sizeof(void *))) return std::nullopt;
        const auto *definition = *reinterpret_cast<const std::uint8_t *const *>(address);
        constexpr std::size_t requiredBytes = 3834; // Checkpoint50: effect-up +3833.
        if (!readableSpan(definition,requiredBytes)) return std::nullopt;
        return SV_ReadGrenadeBlastParameters(weapon,{definition,requiredBytes});
    }

    std::optional<std::array<float, 3>> EngineBindings::evaluateTrajectory(
        const SvNativeTrajectory &trajectory, const std::int32_t atTime) const
    {
        // OLfinal-only retained entry; no replacement physics formula.
        constexpr std::size_t EvaluateTrajectoryRva = 0x10BD0; // out.exe 0x410BD0
        constexpr std::array<std::uint8_t, 16> prefix{
            0x55,0x8B,0xEC,0x83,0xE4,0xF8,0x83,0xEC,0x18,0x53,0x56,0x8B,0xF1,0x8B,0x0E,0x83};
        if (!bindingCommitted_.load(std::memory_order_acquire) || !module_ ||
            !readableSpan(module_ + EvaluateTrajectoryRva, prefix.size()) ||
            !std::equal(prefix.begin(), prefix.end(), module_ + EvaluateTrajectoryRva))
            return std::nullopt;
        const NativeStageScope stage("BG_EvaluateTrajectory");
        return SV_EvaluateTrajectory(trajectory, atTime,
            [&](const auto &input, auto time, auto &point) {
                return invokeEvaluateTrajectory(module_ + EvaluateTrajectoryRva,
                    &input, time, point.data());
            });
    }

    bool EngineBindings::clientLoadoutBindingsAvailable() const
    {
        // Separate from valid() on purpose. These two drive
        // captureClientLoadoutRequest, which is how a CLIENT reports its own
        // loadout -- so their absence degrades exactly that and must not read as
        // "the engine is not bound".
        return weaponSlotReadStaged_ != 0 && currentCharacterGet_ != nullptr;
    }

    bool EngineBindings::observeGameThread() noexcept
    {
        const auto currentThread = GetCurrentThreadId();
        auto expected = std::uint32_t{};
        if (gameThreadId_.compare_exchange_strong(
                expected,
                currentThread,
                std::memory_order_acq_rel,
                std::memory_order_acquire))
        {
            return true;
        }
        return expected == currentThread;
    }

    bool EngineBindings::nativeServerEntityBindingsAvailable() const
    {
        return valid() && gEntities_ && serverGameEntitiesPointer_ &&
            serverGameEntityCount_ && svLinkEntity_ && svUnlinkEntity_ &&
            svTrace_ && writableBytes(
                serverGameEntitiesPointer_, sizeof(*serverGameEntitiesPointer_)) &&
            writableBytes(
                serverGameEntityCount_, sizeof(*serverGameEntityCount_));
    }

    std::span<std::byte, SvNativeCharacterInfoSize>
        EngineBindings::serverCharacterInfo(
            const std::size_t entityNum) const noexcept
    {
        // CODREF(bg_update_player_dobj): one buffer, two consumers.
        // BG_UpdatePlayerDObj 0x0040B700 is HANDED this pointer, but
        // sub_AA94C0 (VA 0x004094C0) DERIVES it from the anim-condition base
        // while PM_Footsteps runs inside PmoveSingle. Handing the DObj path a
        // private allocation left the derived one reading zeroes, so
        // sub_AA91C0 returned null, no legs animation was ever selected, and
        // every player stayed on animation record 0 - a crouched pose that put
        // the whole locational hit skeleton ~20 units below the drawn body.
        return std::span<std::byte, SvNativeCharacterInfoSize>(
            serverAnimConditionStorage_.data() +
                ServerCharacterInfoBaseOffset +
                entityNum * SvNativeCharacterInfoSize,
            SvNativeCharacterInfoSize);
    }

    bool EngineBindings::installServerAnimConditionStorage(
        std::byte *&previousBase) const noexcept
    {
        if (!animConditionBasePointer_)
            return false;

        auto *const slot = reinterpret_cast<void *volatile *>(
            animConditionBasePointer_);
        previousBase = static_cast<std::byte *>(
            InterlockedCompareExchangePointer(slot, nullptr, nullptr));
        if (InterlockedCompareExchangePointer(
                slot,
                serverAnimConditionStorage_.data(),
                previousBase) != previousBase)
        {
            return false;
        }

        // CODREF(bg_update_player_dobj): stamp the shared animation clock. It
        // belongs here rather than at the call sites because EVERY native
        // animation, DObj and locational-trace call reaches the block through
        // this install, and a clock that is right for one of them and stale for
        // the next reproduces the same frozen-animation fault in a narrower
        // window. Both words carry the same server time: CODOL separates a
        // local frame time from a snapshot server time because the client has
        // both, and a dedicated server has only its own.
        auto *const context = serverAnimConditionStorage_.data();
        *reinterpret_cast<std::uint32_t *>(context + AnimFrameTimeOffset) =
            serverAnimationTimeMilliseconds_;
        *reinterpret_cast<std::uint32_t *>(context + AnimSnapshotTimeOffset) =
            serverAnimationTimeMilliseconds_;
        return true;
    }

    bool EngineBindings::restoreServerAnimConditionStorage(
        std::byte *const previousBase) const noexcept
    {
        if (!animConditionBasePointer_)
            return false;

        return InterlockedCompareExchangePointer(
                   reinterpret_cast<void *volatile *>(
                       animConditionBasePointer_),
                   previousBase,
                   serverAnimConditionStorage_.data()) ==
            serverAnimConditionStorage_.data();
    }

    std::uint8_t *EngineBindings::module() const
    {
        return module_;
    }

    EngineBindings::DBFindXAssetHeader EngineBindings::dbFindXAssetHeader() const
    {
        return dbFindXAssetHeader_;
    }

    void EngineBindings::MSG_Init(
        msg_t &message,
        std::uint8_t *data,
        const std::int32_t length) const
    {
        const auto function = msgInit_;
        auto *messagePointer = &message;
        const auto bufferLength = length;
        auto *bufferData = data;
        __asm
        {
            push esi
            mov esi, messagePointer
            push bufferLength
            push bufferData
            call function
            add esp, 8
            pop esi
        }
    }

    void EngineBindings::MSG_WriteBits(
        msg_t &message,
        const std::int32_t value,
        const std::uint32_t bits) const
    {
        const auto function = msgWriteBits_;
        auto *messagePointer = &message;
        __asm
        {
            push edi
            mov edi, messagePointer
            mov edx, bits
            push value
            call function
            add esp, 4
            pop edi
        }
    }

    void EngineBindings::MSG_WriteString(msg_t &message, const char *value) const
    {
        const auto function = msgWriteString_;
        auto *messagePointer = &message;
        __asm
        {
            push esi
            mov esi, messagePointer
            mov ecx, value
            call function
            pop esi
        }
    }

    bool EngineBindings::CCS_Initialized() const
    {
        if (!module_ || *reinterpret_cast<const std::uint32_t *>(
                module_ + ConstantConfigStringsInitializedRva) == 0)
        {
            constantConfigStringChecksum_.store(0, std::memory_order_relaxed);
            return false;
        }
        const auto checksum = *reinterpret_cast<const std::uint32_t *>(
            module_ + ConstantConfigStringChecksumRva);
        if (!checksum)
        {
            constantConfigStringChecksum_.store(0, std::memory_order_relaxed);
            return false;
        }
        constantConfigStringChecksum_.store(checksum, std::memory_order_relaxed);
        return true;
    }

    bool EngineBindings::beginLevelZoneLoad(
        const std::string_view mapName,
        const std::string_view gameType) const
    {
        if (!levelZoneLoad_ || mapName.empty() || gameType.empty() ||
            mapName.find('\0') != mapName.npos ||
            gameType.find('\0') != gameType.npos ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }

        const std::string map(mapName);
        const std::string game(gameType);
        const auto *mapPointer = map.c_str();
        const auto *gamePointer = game.c_str();
        return invokeLevelZoneLoad(levelZoneLoad_, mapPointer, gamePointer);
    }

    bool EngineBindings::zoneLoaded(const std::string_view name) const
    {
        if (!zoneLoaded_ || name.empty() || name.find('\0') != name.npos)
            return false;
        const std::string terminated(name);
        return zoneLoaded_(terminated.c_str());
    }

    bool EngineBindings::initializeLevelWorld(
        const std::string_view mapName,
        const std::string_view gameType) const
    {
        if (!collisionMapLoad_ || !collisionWorldLink_ || !dbFindXAssetHeader_ ||
            !validBookingName(mapName) || !validBookingName(gameType) ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }

        const std::string map(mapName);
        const std::string game(gameType);

        // A CAMPAIGN LEVEL IS NOT AT THE MULTIPLAYER PATH OR ASSET TYPE.
        //
        // This built exactly one candidate -- ClipMapMp at "maps/mp/<map>.d3dbsp" --
        // and returned false when it missed, which is what
        // `world initialization failed map=coop_training_mp_cargoship` was: the
        // ZONE loaded fine (zoneLoaded passed, `map asset load requested` logged),
        // only the clipmap lookup missed. HANDOFF section 152s.
        //
        // Serving the multiplayer `mp_cargoship` instead is NOT a substitute: the
        // client loads `coop_training_mp_cargoship` (its own gamestate says so, and
        // so does the retail coop capture), so the two sides hold different levels
        // and the level checksum rejects the join.
        //
        // Try the four combinations and REPORT which one resolved, so a miss names
        // itself instead of collapsing to "failed". 14 is the stock SP ClipMap next
        // to ClipMapMp's 15; the campaign path convention drops the "mp/".
        struct BspCandidate
        {
            std::uint32_t assetType;
            std::string name;
        };
        // A CAMPAIGN LEVEL BORROWS THE MULTIPLAYER MAP'S COLLISION. Measured by
        // decrypting the fastfiles: mp_nuked's zone carries
        // `maps/mp/mp_nuked.d3dbsp`, while coop_training_mp_cargoship's THREE
        // fastfiles (.ff, _const, _load) and its 235-file lf_ archive carry no
        // .d3dbsp at all. The campaign level is built on mp_cargoship -- its own
        // name says so -- so the last `mp_`-prefixed component is the map whose
        // clipmap it reuses.
        std::string borrowed;
        if (const auto at = map.rfind("mp_"); at != std::string::npos && at != 0)
            borrowed = map.substr(at);
        std::vector<BspCandidate> candidates{
            { AssetTypeClipMapMp, "maps/mp/" + map + ".d3dbsp" },
            { AssetTypeClipMapSp, "maps/mp/" + map + ".d3dbsp" },
            { AssetTypeClipMapMp, "maps/" + map + ".d3dbsp" },
            { AssetTypeClipMapSp, "maps/" + map + ".d3dbsp" },
        };
        if (!borrowed.empty())
        {
            candidates.push_back(
                { AssetTypeClipMapMp, "maps/mp/" + borrowed + ".d3dbsp" });
            candidates.push_back(
                { AssetTypeClipMapSp, "maps/mp/" + borrowed + ".d3dbsp" });
        }
        const BspCandidate *chosen{};
        for (const auto &candidate : candidates)
        {
            if (findXAsset(candidate.assetType, candidate.name.c_str(), false).data)
            {
                chosen = &candidate;
                break;
            }
        }
        if (!chosen)
        {
            std::string tried;
            for (const auto &candidate : candidates)
            {
                tried += (tried.empty() ? "" : ", ") +
                    std::to_string(candidate.assetType) + ":" + candidate.name;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "no clipmap for " + map + " -- tried " + tried);
            return false;
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "clipmap resolved type=" + std::to_string(chosen->assetType) +
                " name=" + chosen->name);

        const std::string &bspName = chosen->name;
        if (!invokeCollisionMapLoad(
                collisionMapLoad_, bspName.c_str(), game.c_str(), map.c_str()) ||
            !invokeNoArgument(collisionWorldLink_) ||
            !resetNativeServerEntityMirrorAfterWorldInitialization())
        {
            return false;
        }

        return findXAsset(
            AssetTypeComWorld, bspName.c_str(), true).data != nullptr;
    }

    bool EngineBindings::resetNativeServerEntityMirrorAfterWorldInitialization()
        const
    {
        releaseActorHitPoses();
        actorHitPosesEnabled_ = false;
        for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
        {
            auto *const slot = reinterpret_cast<std::byte *>(gEntities_) +
                entityNum * SvNativeServerEntity::Size;
            if (!writableBytes(slot, SvNativeServerEntity::Size))
                return false;
            static_cast<void>(mirror);
        }
        // OLMOD(native-player-dobj-lifetime): level world initialization is
        // the only proven recovery boundary after a caught native DObj or
        // animation exception. COD's original void APIs do not expose a
        // recoverable failure protocol for partially mutated DObj/XAnim state.
        for (std::uint32_t entityNum{};
             entityNum < nativeServerCharacterInfo_.size();
             ++entityNum)
        {
            serverDObjFreeAdapter(static_cast<std::int32_t>(entityNum), 0);
        }
        nativeServerCharacterInfo_ = {};
        for (std::size_t entityNum{};
             entityNum < ServerCharacterInfoSlotCount;
             ++entityNum)
        {
            std::ranges::fill(serverCharacterInfo(entityNum), std::byte{});
        }
        nativeServerPlayerDObjPoisoned_ = false;
        nativeServerPlayerDObjFailure_.clear();
        nativeServerPlayerDObjObservedSuccess_ = false;
        nativeServerDObjGeomDiagnosticsLogged_ = {};
        for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
        {
            auto *const slot = reinterpret_cast<std::byte *>(gEntities_) +
                entityNum * SvNativeServerEntity::Size;
            if (mirror.source.shape == SvCollisionShape::ScriptModelDObj)
                serverDObjFreeAdapter(static_cast<std::int32_t>(entityNum), 0);
            std::memcpy(slot, mirror.baseline.bytes.data(),
                SvNativeServerEntity::Size);
        }
        nativeServerEntityMirror_.clear();
        return true;
    }

    bool EngineBindings::publishNativeServerEntityData(
        const std::uint32_t entityCount) const
    {
        if (!nativeServerEntityBindingsAvailable() || !entityCount ||
            entityCount > SvNativeServerEntity::Capacity)
        {
            return false;
        }

        const auto publishedEntities = *serverGameEntitiesPointer_;
        if (publishedEntities && publishedEntities != gEntities_)
            return false;

        // CODOL inlines the newer SV_LocateGameData entity publication in
        // G_Spawn. This embedded-server path owns the same fixed array but
        // does not run the native allocator before CM starts consuming it.
        *serverGameEntityCount_ = std::max(
            *serverGameEntityCount_, entityCount);
        *serverGameEntitiesPointer_ = gEntities_;
        return *serverGameEntitiesPointer_ == gEntities_ &&
            *serverGameEntityCount_ >= entityCount;
    }

    bool EngineBindings::nativeServerEntityMirrorMatches(
        const std::span<const SvCollisionEntity> entities) const
    {
        if (!nativeServerEntityBindingsAvailable() || entities.empty() ||
            nativeServerEntityMirror_.size() != entities.size() ||
            *serverGameEntitiesPointer_ != gEntities_ ||
            *serverGameEntityCount_ <= entities.back().entityNum)
        {
            if (mirrorMismatchLogCounter_++ < 12)
            {
                char line[224]{};
                std::snprintf(
                    line,
                    sizeof(line),
                    "native entity mirror MISMATCH check=preconditions "
                    "available=%u mirror=%zu entities=%zu base=%p vs %p "
                    "count=%lu back=%lu",
                    nativeServerEntityBindingsAvailable() ? 1u : 0u,
                    nativeServerEntityMirror_.size(),
                    entities.size(),
                    serverGameEntitiesPointer_ ? *serverGameEntitiesPointer_
                                               : nullptr,
                    gEntities_,
                    static_cast<unsigned long>(
                        serverGameEntityCount_ ? *serverGameEntityCount_ : 0),
                    static_cast<unsigned long>(
                        entities.empty() ? 0 : entities.back().entityNum));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
            return false;
        }

        // OLMOD(mirror-mismatch-diagnostics): "the mirror does not match" is
        // four different facts and the caller could only ever see one bit of
        // it. Name which check failed, for which entity, and - for the byte
        // image - the FIRST OFFSET that differs, because that offset is the
        // field. Sampled; a mismatch is normally a one-off during a rebuild.
        const auto report = [this](
                                const char *const which,
                                const std::uint32_t entityNum,
                                const std::size_t offset) {
            if (mirrorMismatchLogCounter_++ >= 12)
                return false;
            char line[192]{};
            std::snprintf(
                line,
                sizeof(line),
                "native entity mirror MISMATCH check=%s entity=%lu offset=%zd",
                which,
                static_cast<unsigned long>(entityNum),
                static_cast<std::ptrdiff_t>(offset));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
            return false;
        };
        for (const auto &entity : entities)
        {
            const auto mirror = nativeServerEntityMirror_.find(entity.entityNum);
            if (mirror == nativeServerEntityMirror_.end())
                return report("absent", entity.entityNum, 0);
            SvNativeEntityState entityState;
            const SvNativeEntityState *entityStatePointer{};
            if (entity.shape == SvCollisionShape::Capsule)
            {
                std::memcpy(
                    entityState.bytes.data(),
                    mirror->second.sourceProjection.bytes.data(),
                    SvNativeEntityState::Size);
                entityStatePointer = &entityState;
            }
            const auto projection = SV_BuildNativeServerEntity(
                entity, entityStatePointer);
            if (!projection)
                return report("projection-failed", entity.entityNum, 0);
            if (mirror->second.sourceProjection != *projection)
            {
                std::size_t offset{};
                while (offset != SvNativeServerEntity::Size &&
                    mirror->second.sourceProjection.bytes[offset] ==
                        projection->bytes[offset])
                {
                    ++offset;
                }
                return report("source", entity.entityNum, offset);
            }
            const auto *const slot = static_cast<const std::byte *>(gEntities_) +
                static_cast<std::size_t>(entity.entityNum) *
                    SvNativeServerEntity::Size;
            if (!readableSpan(slot, SvNativeServerEntity::Size))
                return report("unreadable", entity.entityNum, 0);
            if (std::memcmp(
                    slot,
                    mirror->second.linkedImage.bytes.data(),
                    SvNativeServerEntity::Size) != 0)
            {
                std::size_t offset{};
                while (offset != SvNativeServerEntity::Size &&
                    slot[offset] == mirror->second.linkedImage.bytes[offset])
                {
                    ++offset;
                }
                return report("linked-image", entity.entityNum, offset);
            }
        }
        return true;
    }

        // CODDIFF(character_customization): OLfinal DOES NOT HAVE the model
        // resolution scheme this block was written against, and it is the only
        // place in this port where the right answer is to call a DIFFERENT
        // function rather than the same one at a different address.
        //
        // 3.3.3.3 resolves a character presentation in three steps:
        // CharacterSelectionResolve 0x0040CA30 and
        // WorldCharacterModelResolve 0x0040C980 turn the selection ids into a
        // sparse 11-slot model-id list, then each non-zero id is walked through
        // a per-slot base array (WorldCharacterModelSlotBases) and a 16-byte
        // stride name table (WorldCharacterModelNameTable) to produce names.
        // NONE of those four exist in OLfinal -- nine automated methods, two
        // structural searches and a fingerprint pass all failed on them because
        // they were searching for counterparts that are not there. See
        // re/OLFINAL-FFA-HANDOFF.md §16a, and §18d for the re-check on 1649370.
        //
        // OLfinal replaced the whole scheme with an ITEM-DRIVEN one, read out of
        // out.exe (build 1649370):
        //
        //   sub_61B6C0(char *dst[11], const void *record, u16 characterItemId,
        //              int ctx)
        //     memsets dst for 0x2C bytes and fills it with `char *` model names.
        //     `record` is 12 entries of 12 bytes; entry k is
        //     {u32 a @+0, u8 enable @+4, u32 b @+8} and the item id is
        //     ROL32(*(u32 *)0x00E4DD90 ^ b ^ a, 8). Entry 0 and entry 10 are
        //     skipped; entries 1..9 fill dst[0..8] and entry 11 fills dst[9],
        //     so dst[10] is always left null.
        //   sub_80E110 resolves one item id: sub_660C90(id) walks the item
        //     registry this file already binds -- ItemBucketOffsets,
        //     ItemLookup/Count, ItemDefinitions at stride 40 -- and requires
        //     the definition's type byte at +5 to be 2, then indexes
        //     CharacterItemDefinitionTable at stride 52 by the u16 at +2.
        //
        // TWO THINGS ARE STILL UNKNOWN, and both would be guesses:
        //   * `ctx` (sub_61B6C0's 4th argument, reaching sub_80DEF0)
        //   * which of our 11 selectionIds belongs in which of the 12 record
        //     entries, given that two entries are skipped
        // Synthesising the record is otherwise trivial -- the encoding inverts
        // as a = 0, b = key ^ ROR32(id, 8) -- so this is a short follow-up, but
        // it has to be done against a running server rather than guessed. A
        // wrong slot mapping produces a plausible, fully-populated, WRONG set
        // of model names, which is exactly the failure mode this project keeps
        // paying for.
        //
        // So the path FAILS LOUDLY here rather than pretending. The cost is
        // bounded and known: updateNativeServerPlayerDObj's caller logs the
        // stage and continues, so players still spawn, move and shoot; what
        // they lack is a server DObj, which means no rendered body components
        // and the locational trace falls back to the capsule.
        // TODO(CODOL): implement via sub_61B6C0 once `ctx` and the slot mapping
        // are read from a live server; exit condition is a resolved name set
        // that matches what the client renders for the same customization.
    std::vector<std::string> EngineBindings::characterModelNames(
        const std::uint32_t entityNum) const
    {
        if (entityNum >= characterModelNames_.size())
            return {};
        return characterModelNames_[entityNum];
    }

    bool EngineBindings::resolveCharacterModelNames(
        const SvCharacterCustomization &customization,
        std::array<const char *, 11> &modelNames,
        std::size_t &resolvedModelCount,
        std::string *const filledRecord,
        const int variantSelectorOverride) const
    {
        if (filledRecord)
            filledRecord->clear();
        modelNames = {};
        resolvedModelCount = 0;
        if (!module_ || !characterRecordFillDefaults_ ||
            !characterRecordToSelectionNames_)
        {
            return false;
        }
        // OFF BY DEFAULT until the DObj build after it stops faulting -- see the gate.
        if (!characterModelResolutionEnabled())
            return false;
        // NO CHARACTER, NO RESOLUTION, AND SAY SO RATHER THAN GUESSING. Every match this
        // build ran before section 67 arrived here with a zero, because nothing carried
        // the id; a zero must fail the same way the stub did rather than resolve to
        // whatever definition index 0 happens to be.
        if (customization.characterItemId == 0)
            return false;
        if (!readableSpan(
                module_ + CharacterItemDecodeKeyRva, sizeof(std::uint32_t)))
        {
            return false;
        }
        const auto decodeKey = *reinterpret_cast<const std::uint32_t *>(
            module_ + CharacterItemDecodeKeyRva);
        // The key is 0xFFFFFFFF in the IMAGE and a real value at runtime, so a
        // still-unwritten key is a "not ready yet", not a defect. Resolving against it
        // would encode entry 0 as something the engine then decodes to garbage.
        if (decodeKey == 0xFFFFFFFFu)
            return false;

        // TWELVE entries of TWELVE bytes. The engine writes all 144 (section 65a: an
        // eight-byte entry made this a 48-byte stack overrun on both arms), and entry 0
        // is the only one this side fills.
        std::array<
            NativeCharacterItemRecord,
            OlMod::DedicatedSession::CharacterItemCount> record{};
        record[0] = encodeCharacterItemId(customization.characterItemId, decodeKey);
        // THE EQUIPPED OUTFIT, BEFORE THE DEFAULTS. sub_619AD0 fills only the entries
        // that are still EMPTY, so a piece written here survives and the character's
        // own default for that entry is the thing that gets displaced -- which is
        // exactly what wearing an outfit means. Writing nothing here is the old
        // behaviour and yields the character's stock set, entry for entry.
        //
        // Entries are already correct by construction: the capture placed each piece at
        // the entry its item definition claims. Nothing is re-derived here, and entry 0
        // is never overwritten -- the character is the input this whole function is
        // keyed on.
        for (std::size_t entry = 1;
            entry < record.size() && entry < customization.recordItemIds.size();
            ++entry)
        {
            const auto itemId = customization.recordItemIds[entry];
            if (!itemId)
                continue;
            record[entry] = encodeCharacterItemId(itemId, decodeKey);
            // SAME SELF-CHECK AS ENTRY 0, and for the same reason: a key that moved
            // under us encodes something the engine decodes to a different item, and
            // the failure would show up as the wrong model rather than as an error.
            if (decodeCharacterItemId(record[entry], decodeKey) != itemId)
                return false;
        }
        // Cheap self-check, and it is not redundant with the unit test: the test proves
        // the arithmetic, this proves the arithmetic was applied to THIS key. A key that
        // changed under us produces a record the engine would resolve silently wrong.
        if (decodeCharacterItemId(record[0], decodeKey) !=
            customization.characterItemId)
        {
            return false;
        }

        reinterpret_cast<CharacterRecordFillDefaults>(
            characterRecordFillDefaults_)(
                record.data(), static_cast<int>(customization.characterItemId));

        // OLMOD(section-67-record-witness): DECODE WHAT THE ENGINE PUT THERE. Two of the
        // five names the first live run produced were the wrong family -- fpa_goose and
        // boo_empty where the client's own tables say fpa_infbasea and boo_infbasea -- and
        // changing the variant selector moved the SUFFIXES without moving those two, so
        // the cause is upstream of the naming.
        //
        // Names are a lossy view of the record: they are what sub_80E110 made of it. The
        // ids ARE the record, and comparing them against
        //     545 cha_infbasea -> [0, 532, 525, 529, 1099, 115, 0, 0, 0, 0, 0, 0]
        // says in one line whether sub_619AD0 filled the entries this side expected or
        // whether the dedicated process resolves 545 to a different character record than
        // the client does. Those are two very different defects and the names cannot tell
        // them apart.
        //
        // TODO(CODOL): remove with the resolution gate.
        std::string filled;
        for (std::size_t index = 0; index < record.size(); ++index)
        {
            filled += (index ? "," : "");
            filled += record[index].present
                ? std::to_string(decodeCharacterItemId(record[index], decodeKey))
                : std::string{ "-" };
        }

        std::array<const char *, CharacterSelectionNameCount> names{};
        static_assert(sizeof(names) == 0x2C,
            "sub_61B6C0 memsets its output to 0x2C and its prefix guard pins that "
            "`push 2Ch`; eleven pointers is the contract, not a convenience");
        reinterpret_cast<CharacterRecordToSelectionNames>(
            characterRecordToSelectionNames_)(
                names.data(), record.data(),
                static_cast<int>(customization.characterItemId),
                variantSelectorOverride
                    ? variantSelectorOverride
                    : characterVariantSelector(customization.faction));

        // A resolved slot is a non-null pointer to a readable string. sub_61B6C0 leaves
        // an unresolved slot exactly as the memset left it, so counting non-null entries
        // is the engine's own answer to "how many models does this character have".
        //
        // COMPACT. DO NOT KEEP THE SLOT INDEX -- THAT IS THE SPARSE-COUNT CRASH.
        // `resolvedModelCount` is a POPULATION COUNT, and every consumer downstream reads
        // it as a LENGTH: the DObj fill writes modelNames[1 .. resolvedModelCount) into
        // the attachment array, and the post-check compares the created DObj's models
        // against modelNames[0 .. resolvedModelCount). Writing them at their ORIGINAL
        // index leaves a null inside that range the moment sub_61B6C0 answers sparsely,
        // and it does:
        //
        //   545 -> fpa_goose, boo_empty, fja_infbasea, han_infbasea, hea_socomb, -, ...
        //          count=5, slots 0..4          DENSE   -- spawns
        //   686 -> fpa_cowprestigea, boo_empty, fja_indian, han_cowprestigea,
        //          hea_zmcowboy, -, heg_cowprestigea, -, ...
        //          count=6, slots 0,1,2,3,4,6   SPARSE  -- attachment[4] = nullptr
        //
        // BG_UpdatePlayerDObj 0x0040AB30 walks the attachment array reading the FIRST
        // BYTE of every candidate before it checks whether the string is empty
        // (`if (!*(_BYTE *)*v16) break;` at 0x0040AD5A), so that null is dereferenced,
        // and the access violation poisons the native entity mirror -> endFrame rolls
        // back -> the frame publishes no playerStates -> every snapshot is rejected as
        // `missing_playerstate` and the player sits on the loading screen forever.
        // The M4A1 fixture spawned only because character 545 happens to be dense.
        //
        // The engine's own loop breaks at the first EMPTY string, so a hole is a
        // truncation to it either way; compacting keeps the models the character
        // actually has and can never place a null in the range.
        std::string slots;
        for (std::size_t index = 0; index < names.size(); ++index)
        {
            if (!names[index])
                continue;
            if (!readableSpan(
                    reinterpret_cast<const std::uint8_t *>(names[index]), 1))
            {
                // A non-null pointer that cannot be read is worse than a null one: it
                // would reach the DObj build and fault there instead of here.
                modelNames = {};
                resolvedModelCount = 0;
                return false;
            }
            slots += (resolvedModelCount ? "," : "") + std::to_string(index);
            modelNames[resolvedModelCount] = names[index];
            ++resolvedModelCount;
        }
        if (filledRecord)
            *filledRecord = filled + "|slots=" + slots;
        // ZERO NAMES IS A FAILURE, NOT AN EMPTY SUCCESS. Section 48d's whole warning is
        // that this path degrades silently; a character that resolves to nothing has not
        // resolved, and reporting true here would build a DObj out of eleven nulls.
        return resolvedModelCount != 0;
    }

    std::vector<std::string> EngineBindings::characterResolvedModelNames(
        const SvCharacterCustomization &customization) const
    {
        std::vector<std::string> resolved;
        if (customization.characterItemId == 0)
            return resolved;
        std::array<const char *, 11> names{};
        std::size_t count{};
        if (!resolveCharacterModelNames(customization, names, count, nullptr))
            return resolved;
        for (std::size_t index = 0; index < count; ++index)
        {
            if (names[index] && *names[index])
                resolved.emplace_back(names[index]);
        }
        return resolved;
    }

    std::string EngineBindings::characterBodyModelName(
        const SvCharacterCustomization &customization) const
    {
        if (customization.characterItemId == 0)
            return {};
        std::array<const char *, 11> names{};
        std::size_t count{};
        if (!resolveCharacterModelNames(customization, names, count, nullptr))
            return {};
        // The body is the `fpa_` entry. Named rather than taken by position, because
        // the resolver's slot order is the engine's and this project has already paid
        // once for reading a slot index as a length (section 67's sparse list).
        for (std::size_t index = 0; index < count; ++index)
        {
            if (!names[index] || !*names[index])
                continue;
            const std::string name{ names[index] };
            if (name.rfind("fpa_", 0) == 0)
                return name;
        }
        return {};
    }

    std::vector<std::string> EngineBindings::characterOutfitAttachmentModels(
        const SvCharacterCustomization &customization) const
    {
        // WHAT THE CLIENT WOULD NOT WORK OUT FOR ITSELF, and nothing more.
        //
        // A remote client resolves all eleven of a player's models from ONE wire field
        // -- the character item id -- by letting sub_619AD0 fill every empty record
        // entry from that character's own per-slot defaults. So the defaults are
        // already on screen and must NOT be attached again; attaching a model the
        // client also derives would draw it twice.
        //
        // The difference is the outfit. Resolve the record TWICE against the same
        // engine, once with the player's equipped pieces and once with entry 0 alone,
        // and the names present in the first and absent from the second are exactly the
        // models the wire has to carry.
        std::vector<std::string> extras;
        if (customization.characterItemId == 0)
            return extras;

        std::array<const char *, 11> equippedNames{};
        std::size_t equippedCount{};
        if (!resolveCharacterModelNames(
                customization, equippedNames, equippedCount, nullptr))
        {
            return extras;
        }

        auto defaultsOnly = customization;
        defaultsOnly.recordItemIds = {};
        defaultsOnly.recordItemIds[0] = customization.characterItemId;
        std::array<const char *, 11> defaultNames{};
        std::size_t defaultCount{};
        if (!resolveCharacterModelNames(
                defaultsOnly, defaultNames, defaultCount, nullptr))
        {
            return extras;
        }

        for (std::size_t index = 0; index < equippedCount; ++index)
        {
            if (!equippedNames[index])
                continue;
            const std::string_view name{ equippedNames[index] };
            if (name.empty())
                continue;
            // COMPARE BY NAME, NOT BY SLOT. The resolver COMPACTS its output (a sparse
            // slot list is the DObj crash from section 67), so the same model can sit at
            // a different index in the two answers and index equality would report a
            // change that is not one.
            const auto isDefault = std::ranges::any_of(
                std::span{ defaultNames.data(), defaultCount },
                [&](const char *const candidate) {
                    return candidate && name == candidate;
                });
            if (isDefault)
                continue;
            if (std::ranges::find(extras, std::string{ name }) == extras.end())
                extras.emplace_back(name);
        }
        return extras;
    }

    bool EngineBindings::updateNativeServerPlayerDObj(
        const std::uint32_t entityNum,
        const SvCharacterCustomization &customization,
        const std::uint8_t spawnGeneration,
        std::string &failureStage,
        bool &irreversibleMutationStarted) const
    {
        irreversibleMutationStarted = false;
        failureStage = "binding_or_thread";
        if (!valid() || entityNum >= nativeServerCharacterInfo_.size() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }
        failureStage = "animation_not_ready";
        if (serverAnimationInitializationStatus() !=
            ServerAnimationInitializationStatus::Ready)
        {
            return false;
        }
        failureStage = "empty_selection";
        if (static_cast<std::uint8_t>(customization.faction) > 1 ||
            customization.color > 3 ||
            std::ranges::none_of(customization.selectionIds, [](const auto id) {
                return id != 0;
            }))
        {
            return false;
        }

        // CODDIFF(character_customization): OLfinal has no counterpart for
        // 3.3.3.3's selector/slot-base/name-table model resolution, so this
        // goes through resolveCharacterModelNames() instead. See that
        // function for the OLfinal API that replaces it and for exactly what
        // is still unknown.
        std::array<const char *, 11> modelNames{};
        std::size_t resolvedModelCount{};
        std::string filledRecord;
        failureStage = "model_resolution_unported_olfinal";
        if (!resolveCharacterModelNames(
                customization, modelNames, resolvedModelCount, &filledRecord))
        {
            // SAY WHAT THE INPUT WAS, ONCE PER ENTITY. The port sketched in sec 48
            // forges a twelve-entry item record out of `selectionIds` and hands it to
            // sub_61B6C0, and the whole design rests on those ids being marketplace
            // item ids in the namespace sub_80E110 looks up. Nothing has ever printed
            // them. If they are zeros, or small enum values, the blocker is NOT the
            // resolver ABI at all and sec 48 would be built on sand.
            //
            // Deduped on the value, so a steady player is silent after one line and a
            // change -- a respawn with a different class, another client -- reports
            // again. See sec 44a: an instrument must be silent when healthy, and this
            // path is not healthy yet, so it gets exactly one line per distinct input.
            static std::array<std::uint32_t, 18> reportedSelectionHash{};
            std::uint32_t hash = 2166136261u;
            const auto mix = [&hash](const std::uint32_t value) {
                hash = (hash ^ value) * 16777619u;
            };
            for (const auto id : customization.selectionIds)
                mix(id);
            mix(customization.modelIndex);
            mix(customization.viewmodelIndex);
            mix(static_cast<std::uint32_t>(customization.faction));
            mix(customization.color);
            mix(customization.female ? 1u : 0u);
            if (entityNum < reportedSelectionHash.size() &&
                reportedSelectionHash[entityNum] != hash)
            {
                reportedSelectionHash[entityNum] = hash;
                std::string line = "character customization entity=" +
                    std::to_string(entityNum) + " faction=" +
                    std::to_string(static_cast<std::uint32_t>(customization.faction)) +
                    " female=" + std::to_string(customization.female ? 1 : 0) +
                    " colour=" + std::to_string(customization.color) +
                    " modelIndex=" + std::to_string(customization.modelIndex) +
                    " viewmodel=" + std::to_string(customization.viewmodelIndex) +
                    " selectionIds=";
                for (std::size_t index = 0;
                    index < customization.selectionIds.size(); ++index)
                {
                    line += (index ? "," : "") +
                        std::to_string(customization.selectionIds[index]);
                }
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
            return false;
        }

        // OLMOD(section-67-resolution-report): PRINT WHAT IT RESOLVED, ONCE PER DISTINCT
        // RESULT PER ENTITY. Section 48d's standing warning is that a wrong resolver
        // returns a plausible, fully populated, WRONG set of names and reports success,
        // and until section 67 there was nothing to compare against. There is now:
        //
        //     tools/runtime/CodolCharacterCategoryDump.py --resolve
        //     545 cha_infbasea -> fpa_infbasea boo_infbasea fja_infbasea
        //                         han_infbasea00 hea_socomb
        //
        // Those came out of the CLIENT's own tables and share no code with this path, so
        // the two agreeing is a real check rather than this file agreeing with itself
        // (section 67c, and [[codol-judge-output-with-a-foreign-decoder]]).
        //
        // TODO(CODOL): remove once a resolved character has been confirmed against that
        // list on a live run and the DObj it produces has been seen. This is deliberately
        // NOT silent-when-healthy (section 44a) because "healthy" is exactly what has not
        // been established yet.
        {
            static std::array<std::uint32_t, 18> reportedResolutionHash{};
            std::uint32_t hash = 2166136261u;
            const auto mix = [&hash](const std::uint32_t value) {
                hash = (hash ^ value) * 16777619u;
            };
            mix(customization.characterItemId);
            for (const auto *const name : modelNames)
            {
                for (const auto *cursor = name; cursor && *cursor; ++cursor)
                    mix(static_cast<std::uint8_t>(*cursor));
                mix(0u);
            }
            if (!hash)
                hash = 1u;
            if (entityNum < reportedResolutionHash.size() &&
                reportedResolutionHash[entityNum] != hash)
            {
                reportedResolutionHash[entityNum] = hash;
                std::string line = "character models RESOLVED entity=" +
                    std::to_string(entityNum) + " characterItem=" +
                    std::to_string(customization.characterItemId) + " faction=" +
                    std::to_string(static_cast<int>(customization.faction)) +
                    " variant=" +
                    std::to_string(
                        characterVariantSelector(customization.faction)) +
                    " count=" +
                    std::to_string(resolvedModelCount) + " record=" + filledRecord +
                    " names=";
                for (std::size_t index = 0; index < modelNames.size(); ++index)
                {
                    line += (index ? "," : "");
                    line += modelNames[index] ? modelNames[index] : "-";
                }
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }

        // KEEP THE NAMES. They cost one small vector per entity and they are
        // the exact strings the podium's precache burst needs -- see
        // driveMatchEndSequence. Stored unconditionally on a successful
        // resolution rather than inside the dedupe above, because the dedupe is
        // an INSTRUMENT (one log line per distinct input) and using its
        // once-only branch to populate state is how a value goes missing on the
        // second identical resolve.
        if (entityNum < characterModelNames_.size())
        {
            auto &cached = characterModelNames_[entityNum];
            cached.clear();
            for (const auto *const name : modelNames)
            {
                if (name && *name)
                    cached.emplace_back(name);
            }
            // AND THE OTHER VARIANT'S NAMES TOO, because the CLIENT does not
            // necessarily pick the same one. Measured: this server resolved
            // `fpa_goose_ss_m_11` for a player while that player's client held
            // `fpa_goose_ss_m_15` in its own characterInfo -- same character, different
            // variant selector, different model NAME.
            //
            // That is what made players invisible. BG_UpdatePlayerDObj registers the
            // base model BY NAME and bails at its first branch when the name registers
            // to nothing, so precaching the server's variant left the client asking for
            // an asset nobody had loaded. The corpse path is let through that same
            // branch by its `eType == 2` escape, which is why a dead player still drew
            // -- with a fallback body, the "completely different model" a player
            // reported seeing.
            //
            // sub_61B6C0's caller at 0x61D81B treats anything that is not 1 or 2 as its
            // own fallback, so the selector space is exactly {1, 2}: resolve the other
            // one and keep any name it adds. Whichever the client picks is then
            // resident. This runs on a character CHANGE, not per frame.
            //
            // ONCE PER CHARACTER PER ENTITY. updateNativeServerPlayerDObj resolves on
            // every call, so an unguarded second resolve here doubles a cost that is
            // already paid too often -- measured by a player as "extremely laggy".
            // ONCE PER CHARACTER PER ENTITY, AND KEPT. updateNativeServerPlayerDObj
            // resolves on every call, so an unguarded second resolve doubles a cost
            // that is already paid too often -- a player measured that as "extremely
            // laggy". But `cached` is CLEARED and refilled on every call, so guarding
            // the resolve alone would drop the alternate names on the second call and
            // quietly undo the fix. Hold them separately and re-append every time.
            static std::array<std::pair<std::uint16_t, std::vector<std::string>>, 18>
                AlternateVariantNames{};
            if (entityNum < AlternateVariantNames.size())
            {
                auto &[resolvedFor, alternates] = AlternateVariantNames[entityNum];
                if (resolvedFor != customization.characterItemId)
                {
                    resolvedFor = customization.characterItemId;
                    alternates.clear();
                    const auto otherSelector =
                        characterVariantSelector(customization.faction) == 1 ? 2 : 1;
                    std::array<const char *, 11> otherNames{};
                    std::size_t otherCount{};
                    if (resolveCharacterModelNames(
                            customization, otherNames, otherCount, nullptr,
                            otherSelector))
                    {
                        for (std::size_t index = 0; index < otherCount; ++index)
                        {
                            const auto *const name = otherNames[index];
                            if (name && *name)
                                alternates.emplace_back(name);
                        }
                    }
                }
                for (const auto &name : alternates)
                {
                    if (std::ranges::find(cached, name) == cached.end())
                        cached.emplace_back(name);
                }
            }
        }

        auto &slot = nativeServerCharacterInfo_[entityNum];
        const auto characterInfoBytes = serverCharacterInfo(entityNum);
        auto *const characterInfo = characterInfoBytes.data();
        auto *tree = *reinterpret_cast<void **>(
            characterInfo + CharacterInfoAnimTreeOffset);
        if (!tree)
        {
            auto *const anims = *reinterpret_cast<void *const *>(
                serverAnimConditionStorage_.data() + AnimTreeContextOffset);
            failureStage = "animation_tree_source";
            if (!anims)
                return false;
            tree = createNativeXAnimTree(hunkAllocXAnim_, anims);
            failureStage = "animation_tree_allocation";
            if (!tree)
                return false;
            // HunkAllocXAnim has process/level lifetime and no matching free
            // contract. Any later rejection must not retry this transaction.
            irreversibleMutationStarted = true;
        }

        // OLMOD(character-presentation-cache-key): this packed value is only
        // source-side cache identity. It is not a CODOL characterInfo_t field
        // or wire value; all native selectors are still passed separately to
        // CODOL_CharacterCustomization_ResolveModelIds above.
        const auto worldModelContext =
            static_cast<std::uint32_t>(customization.faction) |
            (customization.female ? 1u << 8 : 0u) |
            (static_cast<std::uint32_t>(customization.color) << 16);
        // CODREF(bg_update_player_dobj): the fourth term is the DObj's own
        // existence, and it has to be here. The other three ask whether the
        // PRESENTATION changed; none of them notices that the server DObj was
        // freed underneath an otherwise untouched characterInfo. That is
        // exactly what a death does: the corpse hand-off releases the player's
        // DObj, the respawn re-uses the same character with the same selection
        // ids and leaves infoValid set, so this test found nothing to do, the
        // dirty word at +0x1C was never raised, and BG_UpdatePlayerDObj
        // 0x0040B700 was handed a null DObj with no reason to rebuild it.
        //
        // The player then had no bones at all. Measured 2026-08-17: before a
        // death the locational trace poses `bones=135 highestZ=63.87` and head
        // shots land at hitZ 58-59; after the respawn that line never appears
        // again, and every trace reports the capsule as a perfect candidate -
        // nativeLinked=1, contents=0x02000000, svFlags=0x02, absZ tracking the
        // new origin, ray 0.8 units off its axis - then runs 1144 units into a
        // wall, because CM_PointTraceToEntities admits the entity and
        // DObjTraceline finds nothing to test.
        // CODREF(bg_update_player_dobj): the fifth term. A DObj that still
        // EXISTS but offers no traceline bones is exactly as useless to the
        // locational trace as a missing one, and it is what a death actually
        // leaves behind: measured 2026-08-17, after a respawn this function is
        // called with all four earlier terms false - no skip, no failure, no
        // rebuild logged, dobjMissing=0 - while prepareNativeServerDObjPose
        // takes its `requestedBones` early-out, so the player poses no
        // skeleton and DObjTraceline has nothing to test. sub_CE69A0 skips
        // models flagged in DObj_s +0x0C, the hide mask, which nothing in this
        // project writes and the corpse hand-off sets.
        auto *const presentDObj = serverDObjGetAdapter(
            static_cast<std::int32_t>(entityNum));
        auto tracelineBonesAvailable = false;
        if (presentDObj)
        {
            std::array<std::uint32_t, 8> existingPartBits{};
            tracelineBonesAvailable = invokeDObjGeomTracelinePartBits(
                    dobjGeomTracelinePartBits_,
                    presentDObj,
                    existingPartBits) &&
                std::ranges::any_of(existingPartBits, [](const auto bits) {
                    return bits != 0;
                });
        }
        // CODREF(client_spawn): a NEW LIFE must re-initialise the animation
        // state. The lerp frames at characterInfo +0x160 (legs) and +0x1A0
        // (torso) are set up once, behind slot.lerpFramesInitialized, which
        // only clears inside this branch. A respawn changes neither the
        // selection ids nor the model context nor infoValid, so without this
        // term the branch never runs and the DEATH pose survives into the next
        // life: the server skeleton stays collapsed at roughly waist height,
        // hittable low and never in the head, on every life after the first
        // and for both players. Measured 2026-08-17 - first life head shots
        // land at hitZ 58-61 against targetMaxsZ=70, and after one respawn a
        // full magazine at the head scores nothing while the capsule remains a
        // flawless trace candidate.
        //
        // The demo says the wire side of the respawn is already correct:
        // retail never removes and re-adds the entity, it re-asserts solid
        // 0x66010F (maxs[2] 70) straight out of the dead 0x340000, which this
        // project also does. The fault was only ever this server-local
        // carry-over.
        if (slot.selectionIds != customization.selectionIds ||
            slot.worldModelContext != worldModelContext ||
            // CODREF(client_end_frame): a new LIFE is a presentation change,
            // and the reference server frees the DObj for it. BO1
            // ClientEndFrame 0x005FD1D0 does, at 0x005FDD2A:
            //
            //   cmp  [ebp+bChanged], 0
            //   jz   short loc_5FDD3C
            //   call G_SafeDObjFree(ent)          <- FREE it
            //   call Com_GetServerDObj(ent->s.number)   <- now NULL
            //   call BG_UpdatePlayerDObj(-1, pDObj, es, ci, attachIgnoreCollision)
            //   call BG_PlayerAnimation(-1, es, ci)
            //
            // so a changed presentation is rebuilt from a NULL DObj, not
            // updated in place. This project never freed one: the same DObj was
            // handed back every frame for the life of the level, carrying its
            // skeleton and model state across every death. That is the state
            // that survived a respawn - not characterInfo, not the lerp frames,
            // and not the torso animation, all of which were tested and cleared.
            //
            // e6e64e7 added this term for the wrong reason and 98954f9 removed
            // it for the wrong reason; both missed that the wipe alone rebuilds
            // nothing while the DObj persists.
            slot.spawnGeneration != spawnGeneration ||
            // (superseded reasoning kept for the record)
            //
            // e6e64e7 added a per-LIFE rebuild on the diagnosis that "the death
            // pose survives the respawn". That diagnosis was wrong. At the time
            // BG_SetLerpFrameAnimation VA 0x00409BF0 was bailing at 0x00409C2E
            // on every frame for every player, because the get-DObj callback
            // read a map this project's DObjs are not in, so NO animation was
            // ever set and the pose was not animation-driven at all. There was
            // no death pose to survive; the "correct" life-one pose was a
            // default that two different characters produced identically to 0.1
            // units.
            //
            // With that fixed and the animation clock running, the wipe is
            // purely destructive. MEASURED 2026-08-17 16:52-16:53: across a
            // respawn the legs asset and fraction are IDENTICAL (0x55C9C768,
            // 1.000) while the posed height falls 63.87 -> 37.38 and the
            // highest bone drops from 133 to 71. The single difference is the
            // TORSO lerp frame - alive it holds populated state at t=13750,
            // after the wipe it is zeroed at t=0 - and it can never be rebuilt,
            // because torsoAnim is 0 on this server and 0x0040A2C0 exits to
            // 0x0040A5E7 when the index is zero. The wipe destroys the only
            // thing holding the upper body up.
            //
            // A new life does not need this term now: the animation advances
            // and follows the published index on its own. The other four terms
            // still cover a genuinely changed or missing presentation.
            //
            // TODO(CODOL): torsoAnim being permanently 0 is a SEPARATE and
            // still-open defect - retail carries 10-17 distinct torso values
            // per life (2d-quindecies) and this build reached 1547 exactly once
            // before falling to zero, so the machinery works and the selection
            // does not. Exit when torsoAnim varies with weapon state.
            !*reinterpret_cast<const std::uint32_t *>(characterInfo) ||
            !presentDObj || !tracelineBonesAvailable)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "player DObj rebuild entity=" + std::to_string(entityNum) +
                    " selectionChanged=" +
                    std::to_string(
                        slot.selectionIds != customization.selectionIds) +
                    " contextChanged=" +
                    std::to_string(slot.worldModelContext != worldModelContext) +
                    " infoInvalid=" +
                    std::to_string(
                        !*reinterpret_cast<const std::uint32_t *>(characterInfo)) +
                    " dobjMissing=" + std::to_string(!presentDObj) +
                    " noTracelineBones=" +
                    std::to_string(presentDObj && !tracelineBonesAvailable) +
                    // TODO(CODOL): the two DObj maps, side by side. animMap is
                    // the word BG_SetLerpFrameAnimation's callback reads; a
                    // zero there with a non-zero srvMap means no animation has
                    // ever been set for this player. Remove once confirmed.
                    [this, entityNum] {
                        const auto word = [this, entityNum](const std::size_t rva) {
                            const auto *const table =
                                reinterpret_cast<const std::uint16_t *>(
                                    module_ + rva);
                            return readableSpan(table + entityNum,
                                       sizeof(std::uint16_t))
                                ? std::to_string(table[entityNum])
                                : std::string("unreadable");
                        };
                        return " animMap=" + word(ServerAnimDObjMapRva) +
                            " srvMap=" + word(ServerDObjMapRva);
                    }());
            // CODREF(client_end_frame): BO1 ClientEndFrame calls
            // G_SafeDObjFree(ent) at 0x005FDD34 before re-reading the DObj, so
            // BG_UpdatePlayerDObj is handed NULL and builds a fresh one. The
            // free must happen HERE, before the `existingDObj` read below, for
            // that read to come back null exactly as Com_GetServerDObj does at
            // 0x005FDD42. serverDObjFreeAdapter is this project's own
            // equivalent - it clears the map slot, returns the pool entry and
            // calls the native DObjFree - and is already installed as the
            // free-DObj callback at animBase +0x96E00.
            // CODREF(client_spawn): CLEAR the XAnim tree first. The tree
            // object survives this rebuild - it is read above and written back
            // below - so its node list is the one piece of animation state a
            // life boundary would otherwise carry. XAnimFreeInfo returns those
            // nodes to the pool and leaves the tree's children field at 0, i.e.
            // exactly the `{anims, 0}` a freshly created tree has, which is
            // what makes life N's inputs identical to life 1's.
            // MEASURED 2026-08-17 17:29: treeRoot=10 both before the death and
            // after the respawn, with a fresh DObj and the correct animation
            // asset, and the pose still 51.21 against 65.26.
            // XAnimFreeInfo VA 0x006497C0 dereferences the anim-condition
            // base at VA 0x07817B80 (0x006497CA) and, when it is non-null,
            // CALLS the callback at +0x96E10 with the clock at +0x96DD8. This
            // branch runs long before the install below, so without this scope
            // the clear would read whichever context the client left in that
            // global and call a foreign function pointer out of it. Install our
            // own storage for the duration, exactly as every other native
            // animation call in this file does.
            std::byte *previousTreeContext{};
            if (installServerAnimConditionStorage(previousTreeContext))
            {
                clearNativeXAnimTree(xanimFreeInfo_, tree);
                static_cast<void>(
                    restoreServerAnimConditionStorage(previousTreeContext));
            }
            if (presentDObj)
                serverDObjFreeAdapter(static_cast<std::int32_t>(entityNum), 0);
            std::ranges::fill(characterInfoBytes, std::byte{});
            slot.spawnGeneration = spawnGeneration;
            slot.lerpFramesInitialized = false;
            // CODREF(bg_update_player_dobj): infoValid +0x00, modelName +0x18,
            // ten attachment names +0x20 and ten attachment tags +0x48 are the
            // exact CODOL fields consumed by BG_UpdatePlayerDObj 0x0040B700.
            // Stable empty strings are required: the native loop dereferences
            // every candidate slot before checking its first character.
            *reinterpret_cast<std::uint32_t *>(characterInfo) = 1;
            *reinterpret_cast<const char **>(
                characterInfo + CharacterInfoModelNameOffset) =
                modelNames[0] ? modelNames[0] : EmptyCharacterModelName;
            for (std::size_t index = 0; index < 10; ++index)
            {
                *reinterpret_cast<const char **>(
                    characterInfo + CharacterInfoAttachmentNamesOffset +
                    sizeof(const char *) * index) = EmptyCharacterModelName;
                *reinterpret_cast<const char **>(
                    characterInfo + CharacterInfoAttachmentTagNamesOffset +
                    sizeof(const char *) * index) = EmptyCharacterModelName;
            }
            // NEVER A NULL IN THIS ARRAY. resolveCharacterModelNames now compacts, so
            // the range is dense at the source -- but the native loop at 0x0040AD5A
            // dereferences every slot before testing it, so a null here is an access
            // violation inside the engine rather than a bad model, and the stable empty
            // string above is the only thing that terminates the walk safely. One
            // sparse resolve cost a whole session of `missing_playerstate`; this is the
            // last line of defence and it costs a compare.
            for (std::size_t index = 1;
                index < resolvedModelCount && index <= 10; ++index)
            {
                if (!modelNames[index])
                    break;
                *reinterpret_cast<const char **>(
                    characterInfo + CharacterInfoAttachmentNamesOffset +
                    sizeof(const char *) * (index - 1)) = modelNames[index];
            }
            *reinterpret_cast<std::uint32_t *>(
                characterInfo + CharacterInfoDObjDirtyOffset) = 1;
            *reinterpret_cast<void **>(
                characterInfo + CharacterInfoAnimTreeOffset) = tree;
            slot.selectionIds = customization.selectionIds;
            slot.worldModelContext = worldModelContext;
        }

        if (!slot.lerpFramesInitialized)
        {
            failureStage = "lerp_frame_binding";
            if (!readableSpan(
                    nativeLerpFrameZeroVector_, 3 * sizeof(float)) ||
                !readableSpan(
                    nativeLerpFrameSetKey_, sizeof(*nativeLerpFrameSetKey_)) ||
                !readableSpan(
                    nativeLerpFrameGetKey_, sizeof(*nativeLerpFrameGetKey_)))
            {
                return false;
            }
            // CODDIFF(1649370): the initializer accepts 0..32, not 0..33 -- its own
            // `cmp ebx, 0x20; ja` says so, on both builds. Picking modulo 34 handed it an
            // out-of-range selector about one spawn in thirty-four, and the torso call below
            // rolled the same dice again, so the DObj bring-up failed intermittently for a
            // reason nothing in the log could point at.
            //
            // AND THE RANDOMNESS ITSELF WAS WRONG, not just its range. sub_403C70's
            // selector chooses which of 34 accessor VARIANTS to install, and each variant
            // has its own key triple and its own permutation of the object's address
            // bytes -- so ciphertext written by one is noise to another. Two different
            // objects may legitimately use different variants, which is why legs and
            // torso differ here; what must never vary is the variant used for ONE object
            // across its lifetime. Fixed values make that guarantee and make a failure
            // reproducible, which a QueryPerformanceCounter never can.
            constexpr std::uint32_t selector = 0;
            constexpr std::uint32_t TorsoSelectorOffset = 17;
            static_assert(selector < SvNativeLerpFrameSelectorCount);
            NativeExceptionDetails accessorException{};
            failureStage = "lerp_frame_legs_initialize";
            if (!invokeNativeLerpFrameAccessorInitialize(
                    nativeLerpFrameAccessorInitialize_,
                    characterInfo +
                        SvNativeCharacterInfoLegsLerpFrameOffset,
                    selector,
                    *nativeLerpFrameSetKey_,
                    *nativeLerpFrameGetKey_,
                    nativeLerpFrameZeroVector_,
                    &accessorException))
            {
                char details[112]{};
                std::snprintf(
                    details,
                    sizeof(details),
                    "lerp_frame_legs_initialize code=0x%08lX address=%p",
                    static_cast<unsigned long>(accessorException.code),
                    accessorException.address);
                failureStage = details;
                return false;
            }
            failureStage = "lerp_frame_torso_initialize";
            if (!invokeNativeLerpFrameAccessorInitialize(
                    nativeLerpFrameAccessorInitialize_,
                    characterInfo +
                        SvNativeCharacterInfoTorsoLerpFrameOffset,
                    (selector + TorsoSelectorOffset) %
                        SvNativeLerpFrameSelectorCount,
                    *nativeLerpFrameSetKey_,
                    *nativeLerpFrameGetKey_,
                    nativeLerpFrameZeroVector_,
                    &accessorException))
            {
                char details[112]{};
                std::snprintf(
                    details,
                    sizeof(details),
                    "lerp_frame_torso_initialize code=0x%08lX address=%p",
                    static_cast<unsigned long>(accessorException.code),
                    accessorException.address);
                failureStage = details;
                return false;
            }
            failureStage = "lerp_frame_accessor_validation";
            if (!SV_AreNativeLerpFrameAccessorsValid(
                    characterInfoBytes,
                    static_cast<std::uint32_t>(
                        reinterpret_cast<std::uintptr_t>(characterInfo)),
                    static_cast<std::uint32_t>(
                        reinterpret_cast<std::uintptr_t>(module_)),
                    *nativeLerpFrameSetKey_,
                    *nativeLerpFrameGetKey_))
            {
                return false;
            }
            slot.lerpFramesInitialized = true;
        }

        auto *const entity = static_cast<std::byte *>(gEntities_) +
            static_cast<std::size_t>(entityNum) * SvNativeServerEntity::Size;
        failureStage = "animation_projection";
        SvNativeEntityState nativeEntityStateImage;
        // CODDIFF(bg_update_player_dobj): gentity_s embeds entityState_s as
        // its first 0x110 bytes, but SvNativeEntityState also carries ol-mod
        // address-ownership metadata. Import only the native image here;
        // animation projection reads opaque animation words and must not treat
        // gentity_s +0x110 (isLinked) as that source-side metadata.
        std::memcpy(
            nativeEntityStateImage.bytes.data(),
            entity,
            SvNativeEntityState::Size);
        if (!SV_ProjectNativePlayerAnimationToCharacterInfo(
                nativeEntityStateImage,
                characterInfoBytes))
        {
            return false;
        }
        auto *const existingDObj = serverDObjGetAdapter(
            static_cast<std::int32_t>(entityNum));
        std::byte *previousContext{};
        failureStage = "condition_context";
        if (!installServerAnimConditionStorage(previousContext))
            return false;
        NativeExceptionDetails updateException{};
        // CODREF(bg_update_player_dobj): CODOL 0x0040B700, BO1 0x0040F700
        // and Ghosts 0x140070070 are void-style native updates. Once entered,
        // DObj map, characterInfo and model ownership may already differ even
        // when the SEH adapter reports an exception.
        irreversibleMutationStarted = true;
        const auto updated = invokeBGUpdatePlayerDObj(
            bgUpdatePlayerDObj_, existingDObj, entity, characterInfo,
            &updateException);
        NativeExceptionDetails animationException{};
        // CODREF(bg_update_player_dobj): CODOL BG_PlayerAnimation 0x0040B5D0,
        // BO1 0x0040D9D0 and Ghosts 0x14006CEF0 mutate characterInfo lerp
        // frames/XAnim state and expose no native rollback result.
        const auto animated = updated && invokeBGPlayerAnimation(
            bgPlayerAnimation_, entity, characterInfo, &animationException);
        // TODO(CODOL): the animation state itself, read straight out of
        // characterInfo the instant BG_PlayerAnimation returns, while the
        // condition storage is still installed. This answers, in one line,
        // every question the pose measurements cannot: whether the XAnim tree
        // ever gained a node (word[tree+4] - the root every walker starts from,
        // created on demand by 0x0064BBC0 and reachable only if
        // BG_SetLerpFrameAnimation did NOT bail at 0x00409C2E), whether the
        // lerp frames hold an animation number and asset at all, whether the
        // fraction is still pinned at the 1.0 that VA 0x0040A4AE writes, and
        // whether the clock reached the block. Edge-triggered per entity.
        // Remove once a respawned player poses at full height.
        if constexpr (NativeServerAnimationStateDiagnostics)
        if (animated && entityNum < nativeServerAnimationReport_.size())
        {
            const auto *const info = characterInfo;
            const auto *const reportedTree = *reinterpret_cast<void *const *>(
                info + CharacterInfoAnimTreeOffset);
            const auto u32 = [info](const std::size_t off) {
                return *reinterpret_cast<const std::uint32_t *>(info + off);
            };
            const auto f32 = [info](const std::size_t off) {
                return *reinterpret_cast<const float *>(info + off);
            };
            constexpr std::size_t Legs = SvNativeCharacterInfoLegsLerpFrameOffset;
            constexpr std::size_t Torso = SvNativeCharacterInfoTorsoLerpFrameOffset;
            const auto treeRoot = reportedTree && readableSpan(reportedTree, 8)
                ? *reinterpret_cast<const std::uint16_t *>(
                      static_cast<const std::byte *>(reportedTree) + 4)
                : 0xFFFFu;
            char line[352]{};
            std::snprintf(
                line,
                sizeof(line),
                "server animation state entity=%lu treeRoot=%u "
                "wantLegs=%lu wantTorso=%lu "
                "legs{num=%lu asset=0x%08lX frac=%.3f t=%lu} "
                "torso{num=%lu asset=0x%08lX frac=%.3f t=%lu} clock=%lu",
                static_cast<unsigned long>(entityNum),
                static_cast<unsigned int>(treeRoot),
                static_cast<unsigned long>(u32(0x1F4)),
                static_cast<unsigned long>(u32(0x1F8)),
                static_cast<unsigned long>(u32(Legs + 0x10)),
                static_cast<unsigned long>(u32(Legs + 0x14)),
                f32(Legs + 0x34),
                static_cast<unsigned long>(u32(Legs + 0x38)),
                static_cast<unsigned long>(u32(Torso + 0x10)),
                static_cast<unsigned long>(u32(Torso + 0x14)),
                f32(Torso + 0x34),
                static_cast<unsigned long>(u32(Torso + 0x38)),
                static_cast<unsigned long>(
                    *reinterpret_cast<const std::uint32_t *>(
                        serverAnimConditionStorage_.data() +
                        AnimSnapshotTimeOffset)));
            // THE DEDUPE KEY MUST NOT CONTAIN THE CLOCK. `clock=` is the anim
            // snapshot time and it advances every frame, so the comparison
            // below could never match and this line was written on EVERY
            // frame, for every animated entity, for the life of the match --
            // a state report that only means anything when the state CHANGES.
            //
            // Measured 2026-08-24: with the server console on, the flood cost
            // ~17ms of a ~72ms frame against a 50ms budget. Compare the state
            // without the clock; still print the clock, because when the
            // state does change the time it changed at is the useful half.
            // AND CUTTING AT " clock=" WAS NOT ENOUGH -- THERE ARE THREE CLOCKS,
            // NOT ONE. `legs{... t=%lu}` and `torso{... t=%lu}` are the lerp
            // frame times and they advance every frame exactly as clock= does,
            // and both sit INSIDE the prefix that cut kept. So the key still
            // changed every frame, the comparison still never matched, and the
            // flood this comment describes was still running: measured
            // 2026-08-25 with two players, 206 of 237 log lines in a ten second
            // window were this line, symmetric across both entities.
            //
            // Build the key from the state fields instead of slicing the
            // formatted line, so a later field addition cannot silently
            // reintroduce a clock into it.
            char stateLine[256]{};
            std::snprintf(
                stateLine,
                sizeof(stateLine),
                "%lu/%u/%lu/%lu/%lu/%08lX/%.3f/%lu/%08lX/%.3f",
                static_cast<unsigned long>(entityNum),
                static_cast<unsigned int>(treeRoot),
                static_cast<unsigned long>(u32(0x1F4)),
                static_cast<unsigned long>(u32(0x1F8)),
                static_cast<unsigned long>(u32(Legs + 0x10)),
                static_cast<unsigned long>(u32(Legs + 0x14)),
                f32(Legs + 0x34),
                static_cast<unsigned long>(u32(Torso + 0x10)),
                static_cast<unsigned long>(u32(Torso + 0x14)),
                f32(Torso + 0x34));
            const std::string_view stateKey(stateLine);
            auto &previous = nativeServerAnimationReport_[entityNum];
            if (previous != stateKey)
            {
                previous = stateKey;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        const auto restored = restoreServerAnimConditionStorage(previousContext);
        failureStage = "native_update";
        if (!updated)
        {
            char details[96]{};
            std::snprintf(
                details,
                sizeof(details),
                "native_update code=0x%08lX address=%p",
                static_cast<unsigned long>(updateException.code),
                updateException.address);
            failureStage = details;
            return false;
        }
        failureStage = "native_animation";
        if (!animated)
        {
            char details[96]{};
            std::snprintf(
                details,
                sizeof(details),
                "native_animation code=0x%08lX address=%p",
                static_cast<unsigned long>(animationException.code),
                animationException.address);
            failureStage = details;
            return false;
        }
        failureStage = "condition_context_restore";
        if (!restored)
            return false;
        failureStage = "server_dobj_missing";
        const auto *const createdDObj = static_cast<const std::byte *>(
            serverDObjGetAdapter(static_cast<std::int32_t>(entityNum)));
        if (!createdDObj)
            return false;
        failureStage = "server_dobj_layout";
        if (!readableSpan(
                createdDObj,
                DObjModelPointersOffset + sizeof(const void *)) ||
            static_cast<std::uint32_t>(
                *reinterpret_cast<const std::uint8_t *>(
                    createdDObj + DObjModelCountOffset)) != resolvedModelCount)
        {
            return false;
        }
        const auto *const modelPointers = *reinterpret_cast<void *const *const *>(
            createdDObj + DObjModelPointersOffset);
        if (!modelPointers ||
            !readableSpan(modelPointers, sizeof(*modelPointers) * resolvedModelCount))
        {
            return false;
        }
        for (std::size_t index = 0; index < resolvedModelCount; ++index)
        {
            failureStage = "server_dobj_model";
            const auto expectedModel = findXAsset(
                AssetTypeXModel, modelNames[index], false).data;
            if (!expectedModel || modelPointers[index] != expectedModel)
                return false;
        }
        failureStage = {};
        return true;
    }

    bool EngineBindings::prepareNativeServerDObjPose(
        void *const dobjValue,
        const std::array<std::uint32_t, 8> &partBits,
        NativeExceptionDetails &exceptionDetails,
        const std::uint32_t poseEntityNum) const
    {
        auto *const dobj = static_cast<std::byte *>(dobjValue);
        if (!writableBytes(dobj, NativeServerDObjSize))
            return false;

        const auto requestedBones = std::ranges::any_of(
            partBits, [](const std::uint32_t bits) { return bits != 0; });
        if (!requestedBones)
            return true;

        const auto epoch = *reinterpret_cast<const std::uint32_t *>(
            dobj + DObjSkelEpochOffset);
        const auto *const matrices = *reinterpret_cast<void *const *>(
            dobj + DObjPoseMatricesOffset);
        const auto currentEpoch =
            epoch == nativeServerDObjSkelEpoch_ && matrices;
        if (currentEpoch)
        {
            const auto *const calculated =
                reinterpret_cast<const std::uint32_t *>(
                    dobj + DObjSkelPartBitsOffset);
            const auto upToDate = std::ranges::equal(
                partBits,
                std::span<const std::uint32_t, 8>(calculated, 8),
                [](const std::uint32_t requested,
                   const std::uint32_t available) {
                    return (requested & ~available) == 0;
                });
            if (upToDate)
                return true;
        }
        else
        {
            const auto boneCount = *reinterpret_cast<const std::uint8_t *>(
                dobj + DObjBoneCountOffset);
            if (!boneCount)
                return false;
            const auto allocationSize =
                (static_cast<std::size_t>(boneCount) * 32 + 15) &
                ~std::size_t{ 15 };
            const auto allocationOffset =
                (nativeServerDObjSkelArenaUsed_ + 15) & ~std::size_t{ 15 };
            if (allocationOffset > nativeServerDObjSkelArena_.size() ||
                allocationSize >
                    nativeServerDObjSkelArena_.size() - allocationOffset)
            {
                return false;
            }

            // BO1 and Ghosts keep this ownership in
            // SV_DObjCreateSkelForBones: the server supplies frame-scoped
            // matrix memory, while the retained shared DObjCalcSkel performs
            // all animation and hierarchy math.
            std::memset(dobj + DObjSkelStateOffset, 0, DObjSkelStateSize);
            auto *const allocation =
                nativeServerDObjSkelArena_.data() + allocationOffset;
            std::memset(allocation, 0, allocationSize);
            *reinterpret_cast<std::uint32_t *>(dobj + DObjSkelEpochOffset) =
                nativeServerDObjSkelEpoch_;
            *reinterpret_cast<void **>(dobj + DObjPoseMatricesOffset) =
                allocation;
            nativeServerDObjSkelArenaUsed_ = allocationOffset + allocationSize;
        }

        if (!invokeDObjCalcSkel(
                dobjCalcSkel_, dobj, partBits, &exceptionDetails))
        {
            return false;
        }
        const auto *const calculated = reinterpret_cast<const std::uint32_t *>(
            dobj + DObjSkelPartBitsOffset);
        if (hitboxDiagnosticsEnabled())
            logNativeServerDObjSkeleton(dobj, poseEntityNum);
        return std::ranges::equal(
            partBits,
            std::span<const std::uint32_t, 8>(calculated, 8),
            [](const std::uint32_t requested,
               const std::uint32_t available) {
                return (requested & ~available) == 0;
            });
    }

    // OLMOD(player-dobj-lifecycle-diagnostics): edge-triggered, because the
    // sampled version hid the transition it existed to catch - one client's
    // steady-state skips consumed the 1-in-200 counter and the other client's
    // change after a respawn never printed. Report only when a player's DObj
    // state actually changes, so a respawn produces exactly one line.
    // TODO(CODOL): remove once a respawned player keeps a traceable DObj.
    // AND THE LATCH HAS TO BE RELEASED, or the first transient blinds the rest
    // of the match. MEASURED 2026-08-19 over all 31 sessions in
    // CodolGameServer.log: entity 0 reports `customization_absent` exactly once
    // per session and the model-resolution failure follows IN THE SAME SECOND,
    // 31 times out of 31 - the very next mirror pass already has the
    // customization. One mirror pass runs before the snapshot publishes it, so
    // every match opens with a one-frame gap that is not a failure at all.
    // Because the slot is shared by four states, that single transient latched
    // it for the whole session and `dobj_absent`, `no_traceline_bones` and
    // `healthy` COULD NOT FIRE FOR ENTITY 0 IN ANY SESSION EVER RECORDED. None
    // of the three has ever appeared in the log, and that silence was the
    // instrument being blind, not the server being well.
    void EngineBindings::releasePlayerDObjReportedState(
        const std::uint32_t entityNum,
        const PlayerDObjState state) const
    {
        if (entityNum >= playerDObjReportedState_.size())
            return;
        // Only clear the state we are contradicting. Clearing unconditionally
        // would let a stale report re-print every time the condition it
        // describes was re-entered from a DIFFERENT state.
        if (playerDObjReportedState_[entityNum] != state)
            return;
        playerDObjReportedState_[entityNum] = PlayerDObjState::Unknown;
    }

    void EngineBindings::reportPlayerDObjState(
        const std::uint32_t entityNum,
        const PlayerDObjState state,
        const char *const detail) const
    {
        if (entityNum >= playerDObjReportedState_.size())
            return;
        if (playerDObjReportedState_[entityNum] == state)
            return;
        playerDObjReportedState_[entityNum] = state;
        const auto *name = "healthy";
        switch (state)
        {
        case PlayerDObjState::CustomizationAbsent:
            name = "customization_absent";
            break;
        case PlayerDObjState::DObjAbsent:
            name = "dobj_absent";
            break;
        case PlayerDObjState::NoTracelineBones:
            name = "no_traceline_bones";
            break;
        case PlayerDObjState::Healthy:
            break;
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "player DObj state entity=" + std::to_string(entityNum) + " " +
                name + (detail ? detail : ""));
    }

    void EngineBindings::logNativeCapsuleCandidacy(
        const std::span<const SvCollisionEntity> entities,
        const std::optional<TraceResult> &result) const
    {
        // Report unconditionally, sampled. The first attempt gated on
        // `hitType == TraceHitTypeEntity` to keep only the misses, and that
        // suppressed every line: a trace that reaches nothing but world still
        // reports hitType 1, so the interesting case was the one filtered out
        // (measured 2026-08-17: `hitType=1 hitEntity=none`). There is no
        // reliable did-it-resolve-an-entity flag on this side - hitId 0 is a
        // legitimate entity - so take every eighth trace and let the hits serve
        // as the control for the misses.
        if (!gEntities_ || nativeCapsuleCandidacyLogCounter_++ % 8 != 0)
            return;
        static_cast<void>(result);
        // CODDIFF(1649370): +8, with everything past the embedded entityState.
        // Derived in sv_native_server_entity_mp.cpp from SV_LinkEntity.
        //
        // FOUR OF THE NINE OFFSETS IN THIS BLOCK WERE STILL 3.3.3.3's, sitting
        // either side of a comment that states the rule refuting them. Whoever
        // ported the middle five did not port the ends: isLinked 0x110,
        // svFlags 0x112, inUse 0x113 and ownerNum 0x160 all stayed. 0x110..0x117
        // is the LAST EIGHT BYTES OF THE EMBEDDED entityState on this build, so
        // three of the four were reading entityState tail bytes and printing
        // them as link state, and this diagnostic reported plausible garbage on
        // every line it ever wrote.
        constexpr std::size_t IsLinkedOffset = 0x118;
        constexpr std::size_t ServerFlagsOffset = 0x11A;
        constexpr std::size_t BoundsOffset = 0x11C;
        constexpr std::size_t ContentsOffset = 0x134;
        // CODREF(sv_link_entity): the ABSOLUTE box. Nothing in this project
        // writes it - SV_LinkEntity owns it and recomputes it from origin plus
        // bounds - so it is the one word that goes stale when an entity moves
        // or changes size without being relinked, and CM_CalcTraceExtents
        // decides candidacy on it. Both members are TraceBounds
        // (midpoint, halfSize), which is why +0x114 + 24 lands on contents.
        constexpr std::size_t AbsoluteBoundsOffset = 0x138;
        constexpr std::size_t CurrentOriginOffset = 0x150;
        // CODREF(sv_trace): the trace's ignore filter is the last thing that
        // can drop a correctly linked, correctly boxed entity. traceServerPoint
        // passes ignoreSelf/ignoreParent/ignoreSiblings all set, and the native
        // resolves those against gentity ownerNum - which
        // SV_ToNativeServerEntity never writes. In a fixed-slot mirror that
        // word therefore carries whatever the slot's previous occupant left,
        // and a value that happens to match the shooter or its parent makes the
        // entity a "sibling" and excludes it silently.
        //
        // ownerNum IS AT +0x168 HERE, not 3.3.3.3's 0x160. entityShared_t runs
        // isLinked/modelType/svFlags/inUse 0x118..0x11B, box 0x11C, contents
        // 0x134, absBox 0x138, currentOrigin 0x150, currentAngles 0x15C, and
        // SV_LinkEntity 0x0074EF10 writes every one of those: `*(BYTE*)(a1+280)
        // = 1`, `*(BYTE*)(a1+282) & 6`, `a1+284` bounds, `a1+308` contents,
        // `a1+312` absBox, `a1+336` origin. currentAngles therefore occupies
        // 0x15C..0x167 and 0x160 is its YAW -- a float, printed here as a
        // signed int.
        constexpr std::size_t OwnerNumOffset = 0x168;
        constexpr std::size_t IsInUseOffset = 0x11B;
        constexpr std::size_t EntityTypeOffset = 0x04;
        std::string report;
        for (const auto &entity : entities)
        {
            if (entity.shape != SvCollisionShape::Capsule)
                continue;
            const auto *const native = static_cast<const std::byte *>(gEntities_) +
                static_cast<std::size_t>(entity.entityNum) *
                    SvNativeServerEntity::Size;
            if (!readableSpan(native, SvNativeServerEntity::Size))
                continue;
            std::array<float, 3> origin{};
            std::memcpy(
                origin.data(), native + CurrentOriginOffset, sizeof(origin));
            TraceBounds bounds{};
            std::memcpy(&bounds, native + BoundsOffset, sizeof(bounds));
            TraceBounds absolute{};
            std::memcpy(&absolute, native + AbsoluteBoundsOffset, sizeof(absolute));
            char entry[352]{};
            std::snprintf(
                entry,
                sizeof(entry),
                " #%u{nativeLinked=%u svFlags=0x%02X contents=0x%08lX "
                "owner=%d inUse=%u eType=%lu "
                "origin=%.1f,%.1f,%.1f sourceOrigin=%.1f,%.1f,%.1f "
                "boundsZ=%.1f..%.1f absZ=%.1f..%.1f absXY=%.1f,%.1f+-%.1f,%.1f}",
                entity.entityNum,
                static_cast<unsigned int>(
                    *reinterpret_cast<const std::uint8_t *>(
                        native + IsLinkedOffset)),
                static_cast<unsigned int>(
                    *reinterpret_cast<const std::uint8_t *>(
                        native + ServerFlagsOffset)),
                static_cast<unsigned long>(
                    *reinterpret_cast<const std::uint32_t *>(
                        native + ContentsOffset)),
                *reinterpret_cast<const std::int32_t *>(
                    native + OwnerNumOffset),
                static_cast<unsigned int>(
                    *reinterpret_cast<const std::uint8_t *>(
                        native + IsInUseOffset)),
                static_cast<unsigned long>(
                    *reinterpret_cast<const std::uint32_t *>(
                        native + EntityTypeOffset)),
                origin[0], origin[1], origin[2],
                entity.origin[0], entity.origin[1], entity.origin[2],
                bounds.midpoint[2] - bounds.halfSize[2],
                bounds.midpoint[2] + bounds.halfSize[2],
                absolute.midpoint[2] - absolute.halfSize[2],
                absolute.midpoint[2] + absolute.halfSize[2],
                absolute.midpoint[0], absolute.midpoint[1],
                absolute.halfSize[0], absolute.halfSize[1]);
            report += entry;
        }
        if (report.empty())
            return;
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "native capsule candidacy" + report);
    }

    void EngineBindings::logNativeServerDObjSkeleton(
        const std::byte *const dobj,
        const std::uint32_t entityNum) const
    {
        // OLMOD(locational-skeleton-diagnostics): "the hit skeleton is low" is a
        // statement about these numbers and nothing else, so report them.
        // DObjCalcSkel writes one DObjAnimMat per bone - quat[4], trans[3],
        // transWeight, 32 bytes - into the frame-scoped matrix block this
        // function just handed it, in the model space whose origin is the
        // entity origin. A standing CODOL player's eye is at
        // PM_GetStandHeight = round(playerSizeScale * 60) (sub_AB24D0 and VA
        // 0x004124D0 are ONE 3.3.3.3 address, the i64's +0x6A0000 rebase), and
        // the eye sits in the head, so the tallest bone of a standing player
        // belongs near 60.
        //
        // OLMOD(section-84): 60 IS READ OFF out.exe NOW, and so are its six
        // siblings. The height family is SEVEN adjacent functions with one
        // shape -- `fld1` or `fld [playerState + sizeScale]`, `fmul qword
        // [k]`, round -- so scanning that prologue finds all of them at once
        // and the multipliers ARE the heights:
        //
        //   3.3.3.3 0x00412410..0x00412530   out.exe 0x004104B0..0x004105D0
        //   15  70  50  30  60  40  11       15  70  50  30  60  40  11
        //
        // Same seven values in the same order, so PM_GetStandHeight here is
        // sub_410570 and the 60 carries. The scan also reads the size-scale
        // offset straight off the engine: `fld [eax+98h]` on 3.3.3.3 against
        // `fld [eax+0ACh]` here, which is what
        // sv_native_playerstate_mp.cpp's PlayerSizeScaleOffset already says. Measured hits put confirmed-standing
        // chests at 31-40 where they belong at 44-56; this says whether the
        // bones themselves are there, and if not, which one breaks the chain.
        // TODO(CODOL): remove once the posed skeleton is confirmed to stand at
        // full height.
        // One pose is enough to answer the question, so report the FIRST one and
        // then sample. Every locational trace bumps the epoch and recalculates
        // each live player, so the interval is in recalculated skeletons, not
        // frames - a short burst of fire produces the first lines.
        constexpr std::uint32_t SkeletonSampleInterval = 300;
        const auto sampled =
            nativeServerDObjSkeletonLogCounter_++ % SkeletonSampleInterval == 0;
        const auto boneCount = *reinterpret_cast<const std::uint8_t *>(
            dobj + DObjBoneCountOffset);
        const auto *const matrices = *reinterpret_cast<
            const std::byte *const *>(dobj + DObjPoseMatricesOffset);
        constexpr std::size_t AnimMatSize = 32;
        constexpr std::size_t AnimMatTranslationOffset = 16;
        if (!boneCount || !matrices ||
            !readableSpan(matrices, boneCount * AnimMatSize))
        {
            return;
        }
        auto highest = -std::numeric_limits<float>::infinity();
        auto lowest = std::numeric_limits<float>::infinity();
        std::size_t highestBone{};
        std::uint32_t zeroTranslations{};
        std::string tail;
        for (std::size_t bone{}; bone < boneCount; ++bone)
        {
            const auto *const translation = matrices + bone * AnimMatSize +
                AnimMatTranslationOffset;
            std::array<float, 3> position{};
            std::memcpy(position.data(), translation, sizeof(position));
            if (!std::isfinite(position[2]))
                continue;
            if (position[0] == 0.0f && position[1] == 0.0f &&
                position[2] == 0.0f)
            {
                ++zeroTranslations;
            }
            if (position[2] > highest)
            {
                highest = position[2];
                highestBone = bone;
            }
            lowest = std::min(lowest, position[2]);
            if (bone < 12)
            {
                char entry[32]{};
                std::snprintf(
                    entry, sizeof(entry), " %zu:%.1f", bone, position[2]);
                tail += entry;
            }
        }
        // CODREF(bg_update_player_dobj): sub_C9AD60 (VA 0x005FAD60) multiplies a
        // live player's whole locational box by entityState +0x54 when it is
        // not 1.0, and BG_UpdatePlayerDObj carries the same word into DObj_s
        // +0xC8 as the model scale. A uniform scale there is the one thing that
        // reproduces every measured hit height at once - a 0.7 would put the
        // neck at 38.5 against the 36.0 and 38.9 actually measured - so read
        // both rather than trusting the source-side value.
        // Report a CHANGE in this entity's posed height as well as the
        // periodic sample: without the entity number these lines could not be
        // attributed at all, and a player whose skeleton collapses after a
        // respawn is exactly the case that has to be visible the frame it
        // happens rather than whenever the sampler next fires.
        const auto heightBucket = static_cast<std::int32_t>(highest / 8.0f);
        auto &lastBucket = entityNum < nativeServerDObjSkeletonHeight_.size()
            ? nativeServerDObjSkeletonHeight_[entityNum]
            : nativeServerDObjSkeletonHeightScratch_;
        const auto changed = lastBucket != heightBucket;
        lastBucket = heightBucket;
        if (!sampled && !changed)
            return;
        constexpr std::size_t DObjModelScaleOffset = 0xC8;
        const auto modelScale = *reinterpret_cast<const float *>(
            dobj + DObjModelScaleOffset);
        char line[384]{};
        std::snprintf(
            line,
            sizeof(line),
            "server dobj skeleton entity=%u bones=%u highestZ=%.2f atBone=%zu "
            "lowestZ=%.2f zeroTranslations=%u dobjScale=%.4f first12Z=%s",
            entityNum,
            static_cast<unsigned int>(boneCount),
            highest,
            highestBone,
            lowest,
            zeroTranslations,
            modelScale,
            tail.c_str());
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, line);
    }

    // CODREF(xanim_shared_actor_blend): CODOL 52FBE0 builds matched agent
    // body/head DObjs; 5400B0 advances to the command clock, applies type8,
    // then 549870 advances the remaining elapsed time. BO1/Ghosts shared XAnim
    // clock comparison is in shared-actor-blend-20260917.md. This is a server
    // owner adapter, not a recovered CODOL AI/controller or client-state copy.
    void EngineBindings::releaseActorHitPoses() const
    {
        for (std::size_t i=0; i<actorHitPoseOwners_.size(); ++i)
        {
            auto &owner=actorHitPoseOwners_[i];
            if (owner.tree[0]) clearNativeXAnimTree(xanimFreeInfo_,owner.tree.data());
            if (owner.dobj && serverDObjGetAdapter(static_cast<int>(i))==owner.dobj)
                serverDObjFreeAdapter(static_cast<int>(i),0);
            owner={};
        }
    }

    void EngineBindings::synchronizeActorHitPoses(
        const std::span<const SvCollisionEntity> entities,
        const std::uint32_t serverTime) const
    {
        if (!actorHitPosesEnabled_) return;
        std::array<bool,2048> present{};
        for (const auto &entity:entities)
            if (entity.actorHitPose && entity.entityNum<present.size())
                present[entity.entityNum]=true;
        const auto release=[this](std::size_t i) {
            auto &owner=actorHitPoseOwners_[i];
            if (owner.tree[0]) clearNativeXAnimTree(xanimFreeInfo_,owner.tree.data());
            if (owner.dobj && serverDObjGetAdapter(static_cast<int>(i))==owner.dobj)
                serverDObjFreeAdapter(static_cast<int>(i),0);
            owner={};
        };
        for (std::size_t i=0;i<present.size();++i)
            if (!present[i] && (actorHitPoseOwners_[i].dobj ||
                actorHitPoseOwners_[i].failed)) release(i);

        // CODREF(xanim_shared_actor_blend): 40B210 family3 record, populated
        // once by the native parser during this level's opt-in load.
        void *anims{};
        std::memcpy(&anims,serverAnimConditionStorage_.data()+708228+3*20,sizeof(anims));
        if (!anims || !readableSpan(anims,12)) return;
        const auto nodeCount=*static_cast<const std::uint32_t *>(anims);
        if (nodeCount<2 || nodeCount>4096) return;
        std::byte *previousContext{};
        if (!installServerAnimConditionStorage(previousContext)) return;
        for (const auto &entity:entities)
        {
            if (!entity.actorHitPose || entity.entityNum>=present.size() ||
                entity.entityNum<MaximumGameClients) continue;
            const auto &pose=*entity.actorHitPose;
            auto &owner=actorHitPoseOwners_[entity.entityNum];
            if ((owner.dobj || owner.failed) && (owner.source.generation!=pose.generation ||
                owner.source.body!=pose.body || owner.source.head!=pose.head || owner.source.lower!=pose.lower))
                release(entity.entityNum);
            if (owner.failed) continue;
            const auto fail=[&](const char *stage) {
                release(entity.entityNum);
                owner.source=pose;
                owner.failed=true;
                if (actorHitPoseLogCount_++<64)
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "ZMPOSE refused entity="+std::to_string(entity.entityNum)+" stage="+stage);
            };
            // CODREF(xanim_shared_actor_blend): 785870 alias BST is a u16 key,
            // u16 node, two pointers. Validate membership before native calls.
            const std::uint8_t *link{};
            std::memcpy(&link,static_cast<const std::byte *>(anims)+4,sizeof(link));
            std::uint16_t node{};
            for (unsigned depth=0;link && depth<64;++depth)
            {
                if (!readableSpan(link,12)) break;
                std::uint16_t key{};
                std::memcpy(&key,link,2);
                if (key==pose.animation) {std::memcpy(&node,link+2,2);break;}
                std::memcpy(&link,link+(key>pose.animation?4:8),sizeof(link));
            }
            if (!node || node>=nodeCount) {fail("animation-alias");continue;}
            const auto fresh=!owner.dobj;
            if (fresh)
            {
                if (serverDObjGetAdapter(static_cast<int>(entity.entityNum)))
                {fail("foreign-owner");continue;}
                std::array<NativeDObjModel,3> models{};
                bool resolved=true;
                const std::array<std::uint16_t,3> indices{pose.body,pose.head,pose.lower};
                const auto modelCount=pose.lower?3u:2u;
                for (std::size_t i=0;i<modelCount;++i)
                {
                    const auto name=readCString(nativeConfigString(ModelConfigStringBase+indices[i]),128);
                    if (!indices[i] || !name || name->empty()) {resolved=false;break;}
                    models[i].model=findXAsset(AssetTypeXModel,name->c_str(),false).data;
                    // Native agent ignoreCollision bit0 applies to attachment0.
                    // Empty attachment tag merges shared skeleton bones (52FBE0).
                    // Agent mask bit0 excludes head/neck-cap; lower body is solid
                    // to bullets, matching native multipart agent composition.
                    models[i].ignoreCollision=i==1?1:0;
                    if (!models[i].model || !readableSpan(models[i].model,316))
                    {resolved=false;break;}
                }
                if (!resolved) {fail("models");continue;}
                owner.tree={static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(anims)),0};
                owner.dobj=serverDObjCreateAdapter(models.data(),modelCount,owner.tree.data(),
                    static_cast<int>(entity.entityNum),0,0,0);
                if (!owner.dobj || !readableSpan(owner.dobj,NativeServerDObjSize))
                {fail("dobj-create");continue;}
                std::fill_n(reinterpret_cast<float *>(
                    static_cast<std::byte *>(owner.dobj)+DObjScaleOffset),
                    DObjScaleComponentCount,entity.modelScale);
                owner.updatedTime=pose.animationStartTime<=serverTime
                    ? pose.animationStartTime : serverTime;
                if (actorHitPoseLogCount_++<64)
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "ZMPOSE created entity="+std::to_string(entity.entityNum)+
                        " generation="+std::to_string(pose.generation)+
                        " animation="+std::to_string(pose.animation)+
                        " node="+std::to_string(node)+" treeNodes="+std::to_string(nodeCount));
            }
            if (serverDObjGetAdapter(static_cast<int>(entity.entityNum))!=owner.dobj)
            {fail("owner-changed");continue;}
            const auto changed=fresh || owner.source.animation!=pose.animation ||
                owner.source.animationStartTime!=pose.animationStartTime;
            // Advance the previous clip before its successor's goal is installed.
            const auto commandTime=changed && !fresh
                ? std::clamp(pose.animationStartTime,owner.updatedTime,serverTime)
                : owner.updatedTime;
            if (commandTime>owner.updatedTime &&
                !advanceActorHitAnimation(module_,owner.dobj,(commandTime-owner.updatedTime)*0.001f))
            {fail("previous-clock");continue;}
            if (changed && !setActorHitAnimation(module_,owner.dobj,node))
            {fail("goal");continue;}
            if (serverTime>commandTime &&
                !advanceActorHitAnimation(module_,owner.dobj,(serverTime-commandTime)*0.001f))
            {fail("clock");continue;}
            owner.updatedTime=serverTime;
            owner.source=pose;
        }
        static_cast<void>(restoreServerAnimConditionStorage(previousContext));
    }

    bool EngineBindings::prepareNativeServerDObjPoses(
        const std::span<const SvCollisionEntity> entities,
        const std::uint32_t contentMask,
        NativeExceptionDetails &exceptionDetails) const
    {
        nativeServerDObjSkelArenaUsed_ = 0;
        if (++nativeServerDObjSkelEpoch_ == 0)
            ++nativeServerDObjSkelEpoch_;

        for (const auto &entity : entities)
        {
            if (entity.shape != SvCollisionShape::Capsule &&
                entity.shape != SvCollisionShape::ScriptModelDObj)
            {
                continue;
            }
            auto *const dobj = serverDObjGetAdapter(
                static_cast<std::int32_t>(entity.entityNum));
            if (!dobj)
            {
                if (entity.bodyRole == SvCollisionBodyRole::Player)
                {
                    reportPlayerDObjState(
                        entity.entityNum, PlayerDObjState::DObjAbsent);
                }
                continue;
            }

            // CODREF(sv_trace): pose the bones the trace will actually read.
            // SV_PointTraceToEntity 0x005FB510 chooses its part-bit source at
            // 0x005FB717 on `test byte ptr [gentity + 0x112], 4` - svFlags bit
            // 2 - and this project sets exactly that bit for every
            // ScriptModelDObj and clears it for player capsules
            // (sv_native_server_entity_mp.cpp). Bit clear takes the locational
            // pair sub_CE69A0 + DObjTraceline 0x00645DD0 with the pointtrace's
            // priority map; bit set takes sub_CE6B40 + 0x00646A70 with its
            // content mask. Asking the locational variant for a script model's
            // bones leaves every bone the contents trace reads uncomputed, and
            // an uncomputed bone keeps the zeroed matrix this function just
            // allocated - so the whole skeleton collapses onto the model origin
            // and becomes one large volume that swallows bullets and reports
            // hit location 0. Measured on 2026-08-17: 36-bone script models
            // posed with every translation at zero, and a respawned player
            // behind one absorbed a full magazine at entity 324 with group=0
            // while the same weapon had just scored 59-unit head shots.
            std::array<std::uint32_t, 8> partBits{};
            const auto reportEmptyPartBits = [&](const std::array<std::uint32_t, 8> &bits) {
                // OLMOD(player-dobj-lifecycle-diagnostics): a live player whose
                // DObj yields no traceline bones is invisible to the bone test
                // while remaining a perfect broadphase candidate, and
                // prepareNativeServerDObjPose returns true without posing or
                // logging anything. Name it.
                if (entity.bodyRole != SvCollisionBodyRole::Player)
                    return;
                if (std::ranges::any_of(bits, [](const auto v) { return v != 0; }))
                    return;
                char line[176]{};
                std::snprintf(
                    line,
                    sizeof(line),
                    " models=%u hideMask=0x%08lX",
                    static_cast<unsigned int>(
                        *reinterpret_cast<const std::uint8_t *>(
                            static_cast<const std::byte *>(dobj) +
                            DObjModelCountOffset)),
                    static_cast<unsigned long>(
                        *reinterpret_cast<const std::uint32_t *>(
                            static_cast<const std::byte *>(dobj) +
                            DObjModelHideMaskOffset)));
                reportPlayerDObjState(
                    entity.entityNum, PlayerDObjState::NoTracelineBones, line);
            };
            const auto partBitsRecovered =
                entity.shape == SvCollisionShape::ScriptModelDObj
                ? invokeDObjContentsTracelinePartBits(
                      dobjContentsTracelinePartBits_,
                      dobj,
                      contentMask,
                      partBits,
                      &exceptionDetails)
                : invokeDObjGeomTracelinePartBits(
                      dobjGeomTracelinePartBits_,
                      dobj,
                      partBits,
                      &exceptionDetails);
            if (!partBitsRecovered)
                return false;
            reportEmptyPartBits(partBits);
            if (entity.bodyRole == SvCollisionBodyRole::Player &&
                std::ranges::any_of(partBits, [](const auto bits) {
                    return bits != 0;
                }))
            {
                reportPlayerDObjState(
                    entity.entityNum, PlayerDObjState::Healthy);
            }
            if (!prepareNativeServerDObjPose(
                    dobj, partBits, exceptionDetails, entity.entityNum))
            {
                return false;
            }
        }
        return true;
    }

    void EngineBindings::logNativeServerDObjGeomDiagnostics(
        const std::uint32_t entityNum,
        const std::span<const std::uint8_t> priorityMap) const
    {
        if (!dobjGeomDiagnosticsEnabled() ||
            entityNum >= nativeServerDObjGeomDiagnosticsLogged_.size() ||
            nativeServerDObjGeomDiagnosticsLogged_[entityNum])
        {
            return;
        }
        nativeServerDObjGeomDiagnosticsLogged_[entityNum] = true;

        const auto *const entity = static_cast<const std::byte *>(gEntities_) +
            static_cast<std::size_t>(entityNum) * SvNativeServerEntity::Size;
        const auto *const dobj = static_cast<const std::byte *>(
            serverDObjGetAdapter(static_cast<std::int32_t>(entityNum)));
        if (!readableSpan(entity, SvNativeServerEntity::Size) ||
            !readableSpan(dobj, NativeServerDObjSize))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "DObj geom diagnostics unavailable entity=" +
                    std::to_string(entityNum));
            return;
        }

        const auto svFlags = *reinterpret_cast<const std::uint8_t *>(
            entity + 0x112);
        const auto modelCount = *reinterpret_cast<const std::uint8_t *>(
            dobj + DObjModelCountOffset);
        const auto modelHideMask = *reinterpret_cast<const std::uint32_t *>(
            dobj + DObjModelHideMaskOffset);
        const auto *const poseMatrices = *reinterpret_cast<void *const *>(
            dobj + DObjPoseMatricesOffset);
        const auto *const models = *reinterpret_cast<void *const *const *>(
            dobj + DObjModelPointersOffset);
        char summary[320]{};
        std::snprintf(
            summary,
            sizeof(summary),
            "DObj geom diagnostics entity=%lu svFlags=0x%02X dobj=%p "
            "models=%u modelHideMask=0x%08lX poseMatrices=%p "
            "modelArray=%p priorityBytes=%zu knownPriorityBytes=%zu",
            static_cast<unsigned long>(entityNum),
            static_cast<unsigned int>(svFlags),
            dobj,
            static_cast<unsigned int>(modelCount),
            static_cast<unsigned long>(modelHideMask),
            poseMatrices,
            models,
            priorityMap.size(),
            KnownLocationalPriorityCount);
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, summary);

        if (!modelCount || !models ||
            !readableSpan(models, sizeof(*models) * modelCount))
        {
            return;
        }

        std::size_t globalBoneIndex{};
        for (std::size_t modelIndex{}; modelIndex < modelCount; ++modelIndex)
        {
            const auto *const model = static_cast<const std::byte *>(
                models[modelIndex]);
            if (!readableSpan(model, XModelGeometryOffset + sizeof(void *)))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "DObj geom model unreadable entity=" +
                        std::to_string(entityNum) + " model=" +
                        std::to_string(modelIndex));
                continue;
            }

            const auto boneCount = *reinterpret_cast<const std::uint8_t *>(
                model + XModelBoneCountOffset);
            const auto *const modelNamePointer =
                *reinterpret_cast<const char *const *>(model + XModelNameOffset);
            const auto modelName = readCString(modelNamePointer, 128);
            const auto *const classifications =
                *reinterpret_cast<const std::uint8_t *const *>(
                    model + XModelBoneClassificationOffset);
            const auto *const geometry = *reinterpret_cast<const std::byte *const *>(
                model + XModelGeometryOffset);
            const auto modelHidden = modelIndex < 32 &&
                (modelHideMask & (std::uint32_t{ 1 } << modelIndex)) != 0;
            const auto classificationsReadable =
                readableSpan(classifications, boneCount);
            const auto geometryReadable = readableSpan(
                geometry,
                static_cast<std::size_t>(boneCount) *
                    XModelGeometryEntrySize);

            std::uint32_t geometryCount{};
            std::uint32_t activeGeometryCount{};
            std::uint32_t priorityEligibleCount{};
            std::uint32_t hiddenBoneCount{};
            std::uint32_t unknownClassificationCount{};
            std::uint8_t maximumClassification{};
            std::uint8_t maximumPriority{};
            for (std::size_t boneIndex{}; boneIndex < boneCount; ++boneIndex)
            {
                const auto classification = classificationsReadable
                    ? classifications[boneIndex]
                    : std::uint8_t{};
                maximumClassification = std::max(
                    maximumClassification, classification);
                if (classification >= KnownLocationalPriorityCount)
                    ++unknownClassificationCount;
                const auto priority = classification < priorityMap.size()
                    ? priorityMap[classification]
                    : std::uint8_t{};
                maximumPriority = std::max(maximumPriority, priority);

                const auto absoluteBoneIndex = globalBoneIndex + boneIndex;
                const auto hideWord = absoluteBoneIndex < 256
                    ? *reinterpret_cast<const std::uint32_t *>(
                          dobj + DObjBoneHideBitsOffset +
                          sizeof(std::uint32_t) * (absoluteBoneIndex >> 5))
                    : std::uint32_t{ 0xFFFFFFFF };
                const auto boneHidden = absoluteBoneIndex >= 256 ||
                    (hideWord &
                        (std::uint32_t{ 0x80000000 } >>
                            (absoluteBoneIndex & 31))) != 0;
                if (boneHidden)
                    ++hiddenBoneCount;

                const auto geometryPresent = geometryReadable &&
                    *reinterpret_cast<void *const *>(
                        geometry + boneIndex * XModelGeometryEntrySize +
                        XModelGeometryPointerOffset) != nullptr;
                if (geometryPresent)
                    ++geometryCount;
                if (!modelHidden && !boneHidden && geometryPresent)
                {
                    ++activeGeometryCount;
                    if (priority >= 2)
                        ++priorityEligibleCount;
                }
            }

            char details[512]{};
            std::snprintf(
                details,
                sizeof(details),
                "DObj geom model entity=%lu model=%zu ptr=%p name=%s bones=%u "
                "modelHidden=%u classifications=%p readable=%u maxIndex=%u "
                "unknownIndexes=%lu geometry=%p readable=%u nonNull=%lu "
                "hiddenBones=%lu activeGeometry=%lu priorityEligible=%lu "
                "maxPriority=%u",
                static_cast<unsigned long>(entityNum),
                modelIndex,
                model,
                modelName ? modelName->c_str() : "<unreadable>",
                static_cast<unsigned int>(boneCount),
                modelHidden ? 1u : 0u,
                classifications,
                classificationsReadable ? 1u : 0u,
                static_cast<unsigned int>(maximumClassification),
                static_cast<unsigned long>(unknownClassificationCount),
                geometry,
                geometryReadable ? 1u : 0u,
                static_cast<unsigned long>(geometryCount),
                static_cast<unsigned long>(hiddenBoneCount),
                static_cast<unsigned long>(activeGeometryCount),
                static_cast<unsigned long>(priorityEligibleCount),
                static_cast<unsigned int>(maximumPriority));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, details);
            globalBoneIndex += boneCount;
        }
    }

    bool EngineBindings::synchronizeNativeServerEntities(
        const SvNativeEntityMirrorPhase phase,
        const std::span<const SvCollisionEntity> entities,
        const std::span<const SvNativeEntityStateSource> entityStates,
        const std::uint32_t serverTime) const
    {
        // Take the clock before anything can install the block. A server frame
        // always runs a mirror phase before any native animation call, so this
        // is the earliest point the time is both known and current.
        serverAnimationTimeMilliseconds_ = serverTime;
        // OLMOD(native-entity-mirror-transaction): this function is the
        // project-owned bridge from source-authoritative entities to CODOL's
        // retained fixed g_entities array. It is not presented as a recovered
        // monolithic COD server function. Native operations inside the bridge
        // are called out by their own CODREF markers below.
        const auto failed = [this](
            const std::string_view stage,
            const std::optional<std::uint32_t> entityNum = std::nullopt) {
            auto details = std::string(stage);
            if (entityNum)
                details += " entity=" + std::to_string(*entityNum);
            if (details != nativeServerEntityMirrorFailure_)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "native entity mirror failed stage=" + details);
                nativeServerEntityMirrorFailure_ = std::move(details);
            }
            return false;
        };
        const auto synchronized = [this, entities] {
            if (!entities.empty() &&
                (!nativeServerEntityMirrorObservedSuccess_ ||
                    !nativeServerEntityMirrorFailure_.empty()))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "native entity mirror synchronized entities=" +
                        std::to_string(entities.size()));
                nativeServerEntityMirrorObservedSuccess_ = true;
            }
            nativeServerEntityMirrorFailure_.clear();
            return true;
        };
        if (!nativeServerEntityBindingsAvailable() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return failed("binding_or_thread");
        }

        struct DesiredEntity
        {
            SvCollisionEntity source;
            SvNativeServerEntity projection;
            const SvNativeEntityState *entityState{};
            const SvCharacterCustomization *customization{};
            std::uint8_t spawnGeneration{};
        };
        struct TouchedEntity
        {
            std::uint32_t entityNum{};
            SvNativeServerEntity backup;
            const DesiredEntity *desired{};
            bool previouslyOwned{};
        };
        struct EntityStateUpdate
        {
            const DesiredEntity *desired{};
            SvNativeServerEntity backup;
        };
        const bool incrementalCollision =
            phase == SvNativeEntityMirrorPhase::IncrementalCollision;

        std::vector<DesiredEntity> desired;
        desired.reserve(entities.size());
        std::optional<std::uint32_t> previousEntityNum;
        std::size_t entityStateIndex{};
        for (const auto &entity : entities)
        {
            if (previousEntityNum && entity.entityNum <= *previousEntityNum)
                return failed("source_order", entity.entityNum);
            const SvNativeEntityState *entityState{};
            const SvCharacterCustomization *customization{};
            std::uint8_t spawnGeneration{};
            if (entity.shape == SvCollisionShape::Capsule)
            {
                if (entityStateIndex >= entityStates.size() ||
                    entityStates[entityStateIndex].entityNum != entity.entityNum)
                {
                    return failed("entity_state_missing", entity.entityNum);
                }
                entityState = entityStates[entityStateIndex++].state;
                customization =
                    entityStates[entityStateIndex - 1].customization;
                spawnGeneration =
                    entityStates[entityStateIndex - 1].spawnGeneration;
                if (!entityState)
                    return failed("entity_state_null", entity.entityNum);
            }
            auto projection = SV_BuildNativeServerEntity(entity, entityState);
            if (!projection)
                return failed("projection", entity.entityNum);
            desired.push_back(
                { entity, std::move(*projection), entityState, customization,
                  spawnGeneration });
            previousEntityNum = entity.entityNum;
        }
        if (entityStateIndex != entityStates.size())
            return failed("entity_state_orphan");

        // CODREF(bg_update_player_dobj): CODOL BG_UpdatePlayerDObj 0x0040B700;
        // BO1 0x0040F700, Ghosts 0x140070070, BO2 0x0093C2D0. Native COD
        // servers update the live-player DObj from their end-frame ownership.
        // This adapter runs only for SvNativeEntityMirrorPhase::Presentation,
        // after the collision mirror commit, because the DObj consumes the
        // final gentity/entityState image. Collision-only clientThink commits
        // must never multiply this all-player work by usercmd count.
        // CODDIFF(bg_update_player_dobj): unlike slot/link replacement, native
        // player DObj/XAnim calls expose no rollback result. Pre-native source
        // staging is recoverable; an irreversible failure fail-stops this owner
        // until initializeLevelWorld performs its explicit cleanup.
        std::optional<std::uint32_t> failedPlayerDObjEntity;
        std::string failedPlayerDObjStage;
        const auto ensurePlayerDObjs = [this, &desired,
                                           &failedPlayerDObjEntity,
                                           &failedPlayerDObjStage] {
            if (nativeServerPlayerDObjPoisoned_)
            {
                failedPlayerDObjStage = "poisoned";
                return false;
            }
            // The characterInfo BYTES now live in the shared anim-condition
            // region rather than inside the slot, so copying the slot alone no
            // longer rolls this transaction back. Save both halves.
            struct CharacterInfoBackup
            {
                std::uint32_t entityNum{};
                NativeServerCharacterInfoSlot slot;
                std::array<std::byte, SvNativeCharacterInfoSize> bytes{};
            };
            std::vector<CharacterInfoBackup> backups;
            backups.reserve(desired.size());
            for (const auto &entry : desired)
            {
                if (entry.source.bodyRole == SvCollisionBodyRole::Player &&
                    entry.source.entityNum < nativeServerCharacterInfo_.size() &&
                    entry.customization)
                {
                    CharacterInfoBackup backup{
                        .entityNum = entry.source.entityNum,
                        .slot = nativeServerCharacterInfo_[
                            entry.source.entityNum],
                    };
                    std::ranges::copy(
                        serverCharacterInfo(entry.source.entityNum),
                        backup.bytes.begin());
                    backups.push_back(backup);
                }
            }
            bool priorIrreversibleMutation{};
            for (const auto &entry : desired)
            {
                if (entry.source.bodyRole != SvCollisionBodyRole::Player ||
                    entry.source.entityNum >= nativeServerCharacterInfo_.size() ||
                    !entry.customization)
                {
                    if (entry.source.bodyRole == SvCollisionBodyRole::Player &&
                        !entry.customization)
                    {
                        reportPlayerDObjState(
                            entry.source.entityNum,
                            PlayerDObjState::CustomizationAbsent);
                    }
                    continue;
                }
                // The customization has arrived, so the report above is now
                // stale. Drop it silently -- the arrival is the NORMAL case and
                // an instrument must be quiet when nothing is wrong - but drop
                // it, because leaving it latched is what kept the three later
                // states from ever reporting.
                releasePlayerDObjReportedState(
                    entry.source.entityNum,
                    PlayerDObjState::CustomizationAbsent);
                std::string failureStage;
                bool irreversibleMutationStarted{};
                const auto dobjUpdated = updateNativeServerPlayerDObj(
                    entry.source.entityNum,
                    *entry.customization,
                    entry.spawnGeneration,
                    failureStage,
                    irreversibleMutationStarted);
                // OLMOD(player-dobj-lifecycle-diagnostics): report the decision
                // rather than inferring it. A player that has no DObj after a
                // respawn can get there three ways - this loop never reaching
                // the entity because its customization is absent, the update
                // bailing at one of its guards, or the update running and
                // deciding nothing needed rebuilding - and they are
                // indistinguishable from the trace side.
                // TODO(CODOL): remove once a respawned player keeps its DObj.
                if (!dobjUpdated)
                {
                    // Deduped on (entity, stage). This is a KNOWN degraded path --
                    // model_resolution_unported_olfinal, sec 16a -- and it fired twice
                    // per frame, 3981 lines in a 110-second run. A permanent condition
                    // is worth saying once per distinct condition, not 36 times a
                    // second; the count is not the information, the stage is.
                    static std::string reported;
                    auto details = std::to_string(entry.source.entityNum) +
                        " stage=" + failureStage;
                    if (reported != details)
                    {
                        reported = details;
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "player DObj update failed entity=" + details);
                    }
                }
                if (dobjUpdated)
                {
                    priorIrreversibleMutation =
                        priorIrreversibleMutation || irreversibleMutationStarted;
                    if (!nativeServerPlayerDObjObservedSuccess_ ||
                        !nativeServerPlayerDObjFailure_.empty())
                    {
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "native server player DObj active entity=" +
                                std::to_string(entry.source.entityNum));
                    }
                    nativeServerPlayerDObjObservedSuccess_ = true;
                    nativeServerPlayerDObjFailure_.clear();
                    continue;
                }
                for (const auto &backup : backups)
                {
                    nativeServerCharacterInfo_[backup.entityNum] = backup.slot;
                    std::ranges::copy(
                        backup.bytes,
                        serverCharacterInfo(backup.entityNum).begin());
                }
                // AN UNPORTED SUBSYSTEM MUST NOT STOP THE WORLD. OLfinal has no
                // counterpart for 3.3.3.3's selector/slot-base/name-table model
                // resolution (section 16a), so resolveCharacterModelNames always
                // fails here and the surrounding comments already call that a
                // by-design degradation. It was not degrading. It failed the entity
                // mirror, which made SvServerWorld::endFrame roll back and return
                // false, which made the frame return before publishing -- so
                // worldFrame_->serverTime froze, every following snapshot was
                // rejected as duplicate_server_time, and the player who had just
                // spawned correctly saw the world stop dead. Cosmetic absence, total
                // desync.
                //
                // Continuing is safe HERE and only here: the resolution fails at the
                // top of the update, before any native or hunk mutation, so the
                // rollback above is complete and irreversibleMutationStarted is
                // false. Any other stage, and anything that has already touched
                // native state, keeps the fail-stop -- that guard exists because a
                // half-mutated DObj pool cannot be recovered short of level restart.
                if (failureStage == "model_resolution_unported_olfinal" &&
                    !priorIrreversibleMutation && !irreversibleMutationStarted)
                {
                    const auto details = std::string(failureStage) + " entity=" +
                        std::to_string(entry.source.entityNum);
                    if (details != nativeServerPlayerDObjFailure_)
                    {
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "native server player DObj SKIPPED (unported, "
                            "non-fatal) stage=" + details);
                        nativeServerPlayerDObjFailure_ = details;
                    }
                    continue;
                }
                // CODDIFF(bg_update_player_dobj): caught exceptions are an
                // ol-mod boundary. Original COD callers have no rollback
                // result. If this batch entered any native/hunk mutation, the
                // only safe owner is fail-stop until level initialization
                // frees player DObjs and resets characterInfo/XAnim state.
                nativeServerPlayerDObjPoisoned_ =
                    priorIrreversibleMutation || irreversibleMutationStarted;
                const auto details =
                    std::string(failureStage) + " entity=" +
                    std::to_string(entry.source.entityNum);
                if (details != nativeServerPlayerDObjFailure_)
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "native server player DObj unavailable stage=" +
                            details);
                    nativeServerPlayerDObjFailure_ = details;
                }
                failedPlayerDObjEntity = entry.source.entityNum;
                failedPlayerDObjStage = std::move(failureStage);
                return false;
            }
            return true;
        };
        const auto playerDObjFailed = [&failed, &failedPlayerDObjEntity,
                                          &failedPlayerDObjStage] {
            const auto stage = failedPlayerDObjStage.empty()
                ? std::string("player_dobj")
                : std::string("player_dobj_") + failedPlayerDObjStage;
            return failed(stage, failedPlayerDObjEntity);
        };

        std::uint32_t requiredEntityCount{};
        if (!desired.empty())
            requiredEntityCount = desired.back().source.entityNum + 1;
        for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
        {
            static_cast<void>(mirror);
            requiredEntityCount = std::max(requiredEntityCount, entityNum + 1);
        }
        if (requiredEntityCount &&
            !publishNativeServerEntityData(requiredEntityCount))
        {
            return failed("game_data_publication");
        }

        const auto findDesired = [&desired](const std::uint32_t entityNum)
            -> const DesiredEntity * {
            const auto found = std::ranges::lower_bound(
                desired, entityNum, {}, [](const DesiredEntity &entry) {
                    return entry.source.entityNum;
                });
            return found != desired.end() &&
                    found->source.entityNum == entityNum
                ? &*found
                : nullptr;
        };
        const auto nativeSlot = [this](const std::uint32_t entityNum) {
            return reinterpret_cast<std::byte *>(gEntities_) +
                entityNum * SvNativeServerEntity::Size;
        };
        const auto readSlot = [&nativeSlot](const std::uint32_t entityNum) {
            SvNativeServerEntity result;
            std::memcpy(result.bytes.data(), nativeSlot(entityNum),
                SvNativeServerEntity::Size);
            return result;
        };
        struct NativeLinkResult
        {
            bool contextInstalled{};
            bool invoked{};
            bool contextRestored{};
        };
        // CODREF(sv_link_entity): CODOL SV_LinkEntity 0x005FAE70 uses
        // EAX=gentity_s*. BO1 0x0071F960, Ghosts 0x14020A6C0, and BO2
        // 0x007077A0 confirm solid/bounds/DObj/CM-link ownership, but not this
        // project's fixed-slot transaction or CODOL x86 ABI.
        const auto invokeNativeLink = [this](
                                                void *const entity,
                                                NativeExceptionDetails *const
                                                    exceptionDetails = nullptr) {
            std::byte *previousContext{};
            if (!installServerAnimConditionStorage(previousContext))
                return NativeLinkResult{};

            const auto invoked = invokeSVLinkEntity(
                svLinkEntity_, entity, exceptionDetails);
            const auto restored =
                restoreServerAnimConditionStorage(previousContext);
            return NativeLinkResult{
                .contextInstalled = true,
                .invoked = invoked,
                .contextRestored = restored,
            };
        };
        const auto scriptModelDObjMatches = [this](
                                                    const SvCollisionEntity &source) {
            if (source.shape != SvCollisionShape::ScriptModelDObj)
                return true;
            const auto *const dobj = static_cast<const std::byte *>(
                serverDObjGetAdapter(static_cast<std::int32_t>(source.entityNum)));
            const auto model = findXAsset(
                AssetTypeXModel, source.modelName.c_str(), false).data;
            if (!dobj || !model ||
                !readableSpan(
                    dobj,
                    DObjScaleOffset +
                        sizeof(float) * DObjScaleComponentCount) ||
                *reinterpret_cast<const std::uint8_t *>(
                    dobj + DObjModelCountOffset) != 1)
            {
                return false;
            }
            const auto *const models = *reinterpret_cast<void *const *const *>(
                dobj + DObjModelPointersOffset);
            return models && readableSpan(models, sizeof(*models)) &&
                models[0] == model &&
                std::all_of(
                    reinterpret_cast<const float *>(dobj + DObjScaleOffset),
                    reinterpret_cast<const float *>(dobj + DObjScaleOffset) +
                        DObjScaleComponentCount,
                    [&source](const float component) {
                        return component == source.modelScale;
                    });
        };
        // FIVE WAYS TO FAIL, ONE MESSAGE. `native entity mirror failed stage=script_model_dobj`
        // named the lambda, not the arm, and the arms have nothing in common: an already-live
        // DObj, a missing XModel asset, a refused engine create, an unwritable DObj, and a
        // post-write mismatch. Two of them would indict a per-build constant (AssetTypeXModel,
        // DObjScaleOffset) and two would indict the adapter RVAs, so the message has to separate
        // them or the next cycle buys nothing. Logged once per (entity, arm).
        const auto dobjNote = [this](
                                  const std::string_view arm,
                                  const SvCollisionEntity &source) {
            auto details = std::string("script_model_dobj/") + std::string(arm) +
                " entity=" + std::to_string(source.entityNum) +
                " model=" + (source.modelName.empty()
                    ? std::string("<empty>") : source.modelName) +
                " scale=" + std::to_string(source.modelScale);
            if (details != scriptModelDObjFailure_)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "script model dobj refused " + details);
                scriptModelDObjFailure_ = std::move(details);
            }
            return false;
        };
        const auto createScriptModelDObj = [this, &scriptModelDObjMatches, &dobjNote](
                                                   const SvCollisionEntity &source) {
            if (source.shape != SvCollisionShape::ScriptModelDObj)
                return true;
            if (serverDObjGetAdapter(
                    static_cast<std::int32_t>(source.entityNum)))
            {
                return dobjNote("already_live", source);
            }
            NativeDObjModel descriptor{
                .model = findXAsset(
                    AssetTypeXModel, source.modelName.c_str(), false).data,
            };
            if (!descriptor.model)
                return dobjNote("xmodel_not_found", source);
            auto *const dobj = static_cast<std::byte *>(serverDObjCreateAdapter(
                &descriptor,
                1,
                nullptr,
                static_cast<std::int32_t>(source.entityNum),
                0,
                0,
                0));
            if (!dobj)
                return dobjNote("create_returned_null", source);
            if (!writableBytes(
                    dobj,
                    DObjScaleOffset +
                        sizeof(float) * DObjScaleComponentCount))
            {
                serverDObjFreeAdapter(
                    static_cast<std::int32_t>(source.entityNum), 0);
                return dobjNote("scale_offset_unwritable", source);
            }
            std::fill_n(
                reinterpret_cast<float *>(dobj + DObjScaleOffset),
                DObjScaleComponentCount,
                source.modelScale);
            if (scriptModelDObjMatches(source))
                return true;
            // READBACK MISMATCH: DUMP THE OBJECT INSTEAD OF GUESSING WHICH OFFSET MOVED.
            // The scale check cannot be the one failing -- it writes and reads the SAME
            // address, so it agrees whether or not DObjScaleOffset is right. That leaves
            // DObjModelCountOffset (9) and DObjModelPointersOffset (192), both bare literals
            // carried from 3.3.3.3. Two values in this object are KNOWN: the model pointer
            // findXAsset just returned, and the float 1.0 written above. Print the header and
            // both known values, and the true offsets can be recovered offline by searching
            // the dump for them -- no second cycle spent on a guess.
            {
                const auto *const bytes = static_cast<const std::byte *>(
                    serverDObjGetAdapter(
                        static_cast<std::int32_t>(source.entityNum)));
                const auto *const model = findXAsset(
                    AssetTypeXModel, source.modelName.c_str(), false).data;
                std::string dump;
                // The whole object, so the true offsets of the model pointer and the
                // scale can be found by SEARCHING the dump for the two known values
                // rather than trusting DObjModelPointersOffset/DObjScaleOffset, which
                // are 3.3.3.3's and sized for that build's 0xCC struct.
                constexpr std::size_t DumpBytes = NativeServerDObjSize;
                if (bytes && readableSpan(bytes, DumpBytes))
                {
                    static constexpr char Hex[] = "0123456789abcdef";
                    dump.reserve(DumpBytes * 2);
                    for (std::size_t index{}; index < DumpBytes; ++index)
                    {
                        const auto value =
                            static_cast<std::uint8_t>(bytes[index]);
                        dump += Hex[value >> 4];
                        dump += Hex[value & 0xF];
                    }
                }
                else
                {
                    dump = "<unreadable>";
                }
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "script model dobj readback entity=" +
                        std::to_string(source.entityNum) + " model=" +
                        source.modelName + " dobj=" +
                        std::to_string(reinterpret_cast<std::uintptr_t>(bytes)) +
                        " wantModelPtr=" +
                        std::to_string(reinterpret_cast<std::uintptr_t>(model)) +
                        " wantScale=" + std::to_string(source.modelScale) +
                        " header=" + dump);
            }
            serverDObjFreeAdapter(
                static_cast<std::int32_t>(source.entityNum), 0);
            return dobjNote("readback_mismatch", source);
        };
        const auto freeScriptModelDObj = [](const SvCollisionEntity &source) {
            if (source.shape == SvCollisionShape::ScriptModelDObj)
                serverDObjFreeAdapter(static_cast<std::int32_t>(source.entityNum), 0);
        };

        std::vector<TouchedEntity> touched;
        touched.reserve(incrementalCollision
            ? desired.size()
            : nativeServerEntityMirror_.size() + desired.size());
        std::vector<EntityStateUpdate> entityStateUpdates;
        entityStateUpdates.reserve(desired.size());
        for (const auto &[entityNum, mirror] : nativeServerEntityMirror_)
        {
            const auto *const target = findDesired(entityNum);
            // A native ClientThink links the one player whose command just
            // moved; it does not reinterpret every other linked gentity as
            // absent.  IncrementalCollision carries that same update-set
            // meaning, while Collision and Presentation remain full desired
            // images and therefore retain removal detection.
            if (incrementalCollision && !target)
                continue;
            auto *const slot = nativeSlot(entityNum);
            if (!writableBytes(slot, SvNativeServerEntity::Size))
                return failed("owned_slot_memory", entityNum);
            const auto actual = readSlot(entityNum);
            if (!target || target->source != mirror.source ||
                actual != mirror.linkedImage ||
                !scriptModelDObjMatches(mirror.source))
            {
                touched.push_back({ entityNum, actual, target, true });
            }
            else if (target->projection != mirror.sourceProjection)
            {
                entityStateUpdates.push_back({ target, actual });
            }
        }
        for (const auto &target : desired)
        {
            if (nativeServerEntityMirror_.contains(target.source.entityNum))
                continue;
            auto *const slot = nativeSlot(target.source.entityNum);
            if (!writableBytes(slot, SvNativeServerEntity::Size))
                return failed("new_slot_memory", target.source.entityNum);
            const auto baseline = readSlot(target.source.entityNum);
            if (!SV_IsNativeServerEntityAvailableBaseline(baseline))
                return failed("baseline_owned", target.source.entityNum);
            touched.push_back({
                target.source.entityNum, baseline, &target, false,
            });
        }
        if (touched.empty() && entityStateUpdates.empty())
        {
            if (phase == SvNativeEntityMirrorPhase::Presentation &&
                !ensurePlayerDObjs())
                return playerDObjFailed();
            if (phase == SvNativeEntityMirrorPhase::Presentation)
                synchronizeActorHitPoses(entities, serverTime);
            return synchronized();
        }
        for (const auto &entry : entityStateUpdates)
        {
            if (!entry.desired->entityState)
            {
                return failed(
                    "entity_state_source",
                    entry.desired->source.entityNum);
            }
        }
        std::ranges::sort(touched, {}, &TouchedEntity::entityNum);

        // OLMOD(native-entity-mirror-rollback): restore only the state owned by
        // this bridge: native slot bytes, native link state, and script-model
        // DObjs. Live-player characterInfo/DObj animation is outside this
        // rollback today and is explicitly tracked above.
        const auto rollback = [&]() {
            bool restored = true;
            for (const auto &entry : touched)
            {
                auto *const slot = nativeSlot(entry.entityNum);
                const auto current = readSlot(entry.entityNum);
                // CODREF(sv_unlink_entity): CODOL SV_UnlinkEntity 0x005FAC80
                // uses EAX=gentity_s* and removes the retained fixed svEntity
                // from CM without freeing entity lifetime. Ghosts
                // 0x14020BEE0 confirms the separate unlink responsibility.
                if (SV_IsNativeServerEntityLinked(current) &&
                    !invokeSVUnlinkEntity(svUnlinkEntity_, slot))
                {
                    restored = false;
                }
            }
            for (const auto &entry : touched)
            {
                const auto old = nativeServerEntityMirror_.find(entry.entityNum);
                if (entry.desired &&
                    entry.desired->source.shape ==
                        SvCollisionShape::ScriptModelDObj)
                {
                    freeScriptModelDObj(entry.desired->source);
                }
                else if (old != nativeServerEntityMirror_.end())
                {
                    freeScriptModelDObj(old->second.source);
                }
            }
            for (const auto &entry : touched)
            {
                auto *const slot = nativeSlot(entry.entityNum);
                auto backup = entry.backup;
                const auto relink = entry.previouslyOwned &&
                    SV_IsNativeServerEntityLinked(backup);
                if (relink)
                    SV_ClearNativeServerEntityLinkedFlag(backup);
                std::memcpy(slot, backup.bytes.data(),
                    SvNativeServerEntity::Size);
                const auto old = nativeServerEntityMirror_.find(entry.entityNum);
                if (old != nativeServerEntityMirror_.end() &&
                    !createScriptModelDObj(old->second.source))
                {
                    restored = false;
                }
                if (relink)
                {
                    const auto link = invokeNativeLink(slot);
                    if (!link.contextInstalled || !link.invoked ||
                        !link.contextRestored)
                    {
                        restored = false;
                    }
                }
            }
            return restored;
        };

        // CODREF(sv_unlink_entity): every owned touched slot must leave the CM
        // tree before its gentity bytes or DObj ownership are replaced.
        for (const auto &entry : touched)
        {
            if (entry.previouslyOwned &&
                !invokeSVUnlinkEntity(
                    svUnlinkEntity_, nativeSlot(entry.entityNum)))
            {
                if (!rollback())
                    return failed("rollback_after_unlink", entry.entityNum);
                return failed("native_unlink", entry.entityNum);
            }
        }
        for (const auto &entry : touched)
        {
            const auto old = nativeServerEntityMirror_.find(entry.entityNum);
            if (old != nativeServerEntityMirror_.end())
                freeScriptModelDObj(old->second.source);
        }

        // Copying every retained native owner for each usercmd was the measured
        // Factory rubber-band: ~2.7 ms per command, roughly 140 commands/s.
        // An incremental command changes one player, so stage only that entry;
        // full frame phases still stage the complete ownership map.
        auto stagedMirror = incrementalCollision
            ? decltype(nativeServerEntityMirror_){}
            : nativeServerEntityMirror_;
        if (incrementalCollision)
            stagedMirror.reserve(desired.size());
        for (const auto &entry : touched)
        {
            auto *const slot = nativeSlot(entry.entityNum);
            if (!entry.desired)
            {
                const auto old = stagedMirror.find(entry.entityNum);
                if (old == stagedMirror.end())
                {
                    if (!rollback())
                        return failed("rollback_after_owner", entry.entityNum);
                    return failed("missing_owner", entry.entityNum);
                }
                std::memcpy(slot, old->second.baseline.bytes.data(),
                    SvNativeServerEntity::Size);
                stagedMirror.erase(old);
                continue;
            }

            if (!createScriptModelDObj(entry.desired->source))
            {
                if (!rollback())
                    return failed("rollback_after_dobj", entry.entityNum);
                return failed("script_model_dobj", entry.entityNum);
            }

            // CODDIFF(sv_link_entity): CODOL's retained function owns linking,
            // but the source-to-gentity projection and address-secured origin
            // relocation are ol-mod responsibilities because the authoritative
            // source object is not a native gentity_s.
            SV_CopyNativeServerEntityToSlot(
                *reinterpret_cast<SvNativeServerEntity *>(slot),
                entry.desired->projection,
                entry.desired->entityState);
            NativeExceptionDetails linkException{};
            const auto link = invokeNativeLink(slot, &linkException);
            if (!link.contextInstalled)
            {
                if (!rollback())
                {
                    return failed(
                        "rollback_after_link_condition_context",
                        entry.entityNum);
                }
                return failed("link_condition_context", entry.entityNum);
            }
            if (!link.invoked)
            {
                char stage[512]{};
                std::snprintf(
                    stage,
                    sizeof(stage),
                    "native_link code=0x%08lX address=%p access=%lu fault=%p "
                    "shape=%u origin=%.3f,%.3f,%.3f "
                    "bounds=%.3f,%.3f,%.3f contents=0x%08lX "
                    "eax=%p ecx=%p edx=%p esi=%p edi=%p",
                    static_cast<unsigned long>(linkException.code),
                    linkException.address,
                    static_cast<unsigned long>(linkException.accessType),
                    linkException.faultAddress,
                    static_cast<unsigned int>(entry.desired->source.shape),
                    entry.desired->source.origin[0],
                    entry.desired->source.origin[1],
                    entry.desired->source.origin[2],
                    entry.desired->source.bounds.midpoint[0],
                    entry.desired->source.bounds.halfSize[0],
                    entry.desired->source.bounds.halfSize[2],
                    static_cast<unsigned long>(entry.desired->source.contents),
                    reinterpret_cast<void *>(linkException.eax),
                    reinterpret_cast<void *>(linkException.ecx),
                    reinterpret_cast<void *>(linkException.edx),
                    reinterpret_cast<void *>(linkException.esi),
                    reinterpret_cast<void *>(linkException.edi));
                if (!rollback())
                {
                    return failed(
                        std::string("rollback_after_") + stage,
                        entry.entityNum);
                }
                return failed(stage, entry.entityNum);
            }
            if (!link.contextRestored)
            {
                if (!rollback())
                {
                    return failed(
                        "rollback_after_link_condition_context_restore",
                        entry.entityNum);
                }
                return failed(
                    "link_condition_context_restore", entry.entityNum);
            }
            const auto linkedImage = readSlot(entry.entityNum);
            if (!SV_ValidateNativeServerEntityLinkResult(
                    linkedImage, entry.desired->source))
            {
                if (!rollback())
                    return failed("rollback_after_validation", entry.entityNum);
                return failed("post_link_validation", entry.entityNum);
            }
            const auto old = nativeServerEntityMirror_.find(entry.entityNum);
            stagedMirror[entry.entityNum] = {
                .source = entry.desired->source,
                .baseline = old != nativeServerEntityMirror_.end()
                    ? old->second.baseline
                    : entry.backup,
                .sourceProjection = entry.desired->projection,
                .linkedImage = linkedImage,
            };
        }

        for (std::size_t index = 0; index < entityStateUpdates.size(); ++index)
        {
            const auto &entry = entityStateUpdates[index];
            auto *const slot = reinterpret_cast<SvNativeServerEntity *>(
                nativeSlot(entry.desired->source.entityNum));
            SV_CopyNativeEntityStateToServerEntity(
                *slot, *entry.desired->entityState);
            const auto linkedImage = readSlot(
                entry.desired->source.entityNum);
            if (!SV_ValidateNativeServerEntityLinkResult(
                    linkedImage, entry.desired->source))
            {
                for (std::size_t restoreIndex = 0;
                     restoreIndex <= index;
                     ++restoreIndex)
                {
                    const auto &restore = entityStateUpdates[restoreIndex];
                    *reinterpret_cast<SvNativeServerEntity *>(nativeSlot(
                        restore.desired->source.entityNum)) = restore.backup;
                }
                if (!rollback())
                {
                    return failed(
                        "rollback_after_state_update",
                        entry.desired->source.entityNum);
                }
                return failed(
                    "state_update_validation",
                    entry.desired->source.entityNum);
            }
            if (incrementalCollision)
            {
                auto mirror = nativeServerEntityMirror_.at(
                    entry.desired->source.entityNum);
                mirror.source = entry.desired->source;
                mirror.sourceProjection = entry.desired->projection;
                mirror.linkedImage = linkedImage;
                stagedMirror.insert_or_assign(
                    entry.desired->source.entityNum, std::move(mirror));
            }
            else
            {
                auto &mirror = stagedMirror.at(
                    entry.desired->source.entityNum);
                mirror.source = entry.desired->source;
                mirror.sourceProjection = entry.desired->projection;
                mirror.linkedImage = linkedImage;
            }
        }
        // OLMOD(native-entity-mirror-transaction): slot/link validation has
        // committed. A live-player DObj failure must reject the enclosing
        // source mutation so its owner can rebuild the previous source image;
        // silently accepting it leaves entityState and DObj ownership split.
        // CODDIFF(bg_update_player_dobj): the retained functions are void and
        // have no recoverable native failure contract. synchronizeNativeServerEntities
        // therefore fail-stops this owner after any hunk/DObj/animation failure;
        // initializeLevelWorld is the explicit cleanup/reset boundary.
        if (incrementalCollision)
        {
            for (auto &[entityNum, mirror] : stagedMirror)
            {
                nativeServerEntityMirror_.insert_or_assign(
                    entityNum, std::move(mirror));
            }
        }
        else
        {
            nativeServerEntityMirror_ = std::move(stagedMirror);
        }
        if (phase == SvNativeEntityMirrorPhase::Presentation &&
            !ensurePlayerDObjs())
            return playerDObjFailed();
        if (phase == SvNativeEntityMirrorPhase::Presentation)
            synchronizeActorHitPoses(entities, serverTime);
        return synchronized();
    }

    bool EngineBindings::initializeMantleAnimations() const
    {
        if (!valid() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }

        const auto validOutput = [this] {
            return mantleAnims_[0] && mantleAnims_[1] &&
                readableSpan(mantleAnims_[0], sizeof(std::uint32_t)) &&
                readableSpan(mantleAnims_[1], sizeof(std::uint32_t));
        };
        if (mantleAnims_[0])
            return validOutput();

        // CODOL sub_445730 performs this process-lifetime initialization
        // before weapon registry rebuild and player animation script parsing.
        if (!invokeNoArgument(mantleCreateAnims_))
            return false;
        return validOutput();
    }

    ServerAnimationInitializationStatus
        EngineBindings::initializeServerAnimationContext(
            const std::string_view mapName,
            const std::string_view gameType) const
    {
        auto status = serverAnimationInitializationStatus_.load(
            std::memory_order_acquire);
        if (status != ServerAnimationInitializationStatus::NotInitialized)
        {
            return status;
        }
        if (!serverAnimationInitializationStatus_.compare_exchange_strong(
                status,
                ServerAnimationInitializationStatus::ContextBusy,
                std::memory_order_acq_rel,
                std::memory_order_acquire))
        {
            return status;
        }

        const auto fail = [this](
            const ServerAnimationInitializationStatus failure) {
            serverAnimationInitializationStatus_.store(
                failure, std::memory_order_release);
            return failure;
        };
        if (!valid() || mapName.empty() || gameType.empty())
            return fail(ServerAnimationInitializationStatus::InvalidBinding);
        if (gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
            return fail(ServerAnimationInitializationStatus::WrongThread);

        // Arm the witness for the whole of this function. Everything from here
        // to the end is native code that has never completed in this process,
        // and one of those calls has already killed it without a word.
        armVectoredFaultWitnessImpl(module_);
        serverAnimConditionStorage_.fill(std::byte{});
        serverLoadAnimStorage_.fill(std::byte{});
        auto *const serverContext = serverAnimConditionStorage_.data();
        *reinterpret_cast<std::int32_t *>(serverContext + AnimUserOffset) = 0;
        const auto *deathFxOptIn = std::getenv("OLMOD_FACTORY_DEATH_FX");
        const bool loadActorHitTree = mapName == "zm_factory_sh" &&
            deathFxOptIn && std::string_view(deathFxOptIn) == "1";
        // CODREF(xanim_shared_actor_blend): 40B210 resolves six family records
        // at context+708228+20*family, selected by context+0xAF318. Family3 is
        // generic_human in the native actor client. FFA keeps mask0 unchanged.
        *reinterpret_cast<std::uint32_t *>(serverContext + AnimTreeMaskOffset) =
            loadActorHitTree ? 8u : 0u;
        *reinterpret_cast<std::uint8_t *>(
            serverContext + AsymmetricAnimScriptFlagOffset) = 0;
        // CODOL sub_445730 installs this complete callback block before
        // BG_FindAnims. The shared animation parser calls these slots
        // indirectly, so a context containing only AllocXAnim is invalid.
        for (const auto [offset, rva] : ServerAnimationCallbackRvas)
            *reinterpret_cast<void **>(serverContext + offset) = module_ + rva;
        // OLMOD(server-dobj-lookup-boundary): the get-DObj slot must resolve
        // through the SERVER map, and CODOL's own function for this slot does
        // not.
        //
        // One 0xCC-stride DObj pool at VA 0x02E8E850 is reached through two
        // independent maps. ServerDObjCreate VA 0x0059E740 registers a server
        // DObj in VA 0x02E8D050 ONLY - its single map write is at 0x0059E755
        // and it returns at 0x0059E7B6, so the 0x02EF4858 write at 0x0059E7EE
        // belongs to a different function. But CODOL's stock callback for this
        // slot, RVA 0x0455D0, indexes the OTHER table: `movzx eax, word
        // [eax*2 + 0x02EF4858]` at 0x004455D6, returning null when that word is
        // zero.
        //
        // BG_SetLerpFrameAnimation VA 0x00409BF0 calls this slot at 0x00409C24
        // and BAILS at 0x00409C2E when it returns null - so with the stock
        // function installed, no animation is EVER set for any player on this
        // server, on any frame, and the posed skeleton is whatever DObjCalcSkel
        // produces with nothing driving it. MEASURED live 2026-08-17: at a
        // respawn this project logged `animMap=0 srvMap=278` for a player whose
        // DObj was present and healthy - present in the server map, absent from
        // the one the stock callback reads.
        //
        // serverDObjGetAdapter takes the same entity number the native caller
        // passes (`[entity+0]`, entityState.number) and resolves it through
        // ServerDObjGet VA 0x0059E570 against the server map, which is where
        // this project's DObjs actually live. The native call site pushes two
        // arguments and cleans 8 bytes itself, so a one-argument __cdecl
        // adapter is ABI-compatible with the slot.
        *reinterpret_cast<void **>(
            serverContext + ServerGetDObjCallbackOffset) =
            reinterpret_cast<void *>(&serverDObjGetAdapter);

        std::byte *previousConditionBase{};
        if (!installServerAnimConditionStorage(previousConditionBase))
            return fail(ServerAnimationInitializationStatus::ContextBusy);
        auto *const scriptSlot = reinterpret_cast<void *volatile *>(
            animScriptDataPointer_);
        auto *const previousScriptData = static_cast<std::byte *>(
            InterlockedCompareExchangePointer(scriptSlot, nullptr, nullptr));
        if (previousScriptData && previousScriptData != serverContext)
        {
            static_cast<void>(
                restoreServerAnimConditionStorage(previousConditionBase));
            return fail(ServerAnimationInitializationStatus::ContextBusy);
        }
        bool scriptLoadingBegun{};
        const auto logStage = [](const std::string_view stage) {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("server animation stage=") + std::string(stage));
        };
        const auto restoreFailedContext = [&] {
            logStage("failure_cleanup_begin");
            if (scriptLoadingBegun)
            {
                logStage("failure_end_load_anim_trees_begin");
                static_cast<void>(invokeScrEndLoadAnimTrees(module_));
                scriptLoadingBegun = false;
                logStage("failure_end_load_anim_trees_complete");
            }
            logStage("failure_globals_restore_begin");
            InterlockedCompareExchangePointer(
                scriptSlot, previousScriptData, serverContext);
            static_cast<void>(
                restoreServerAnimConditionStorage(previousConditionBase));
            logStage("failure_globals_restore_complete");
        };
        const std::string stableMapName(mapName);
        const std::string stableGameType(gameType);
        logStage("begin_load_anim_trees_begin");
        if (!invokeScrBeginLoadAnimTrees(module_, scrCreateObject_))
        {
            restoreFailedContext();
            return fail(ServerAnimationInitializationStatus::
                BeginLoadAnimTreesFailed);
        }
        scriptLoadingBegun = true;
        logStage("begin_load_anim_trees_complete");
        logStage("load_anim_trees_begin");
        if (!invokeBGLoadAnimTrees(
                bgLoadAnimTrees_,
                stableGameType.c_str(),
                stableMapName.c_str()))
        {
            restoreFailedContext();
            return fail(ServerAnimationInitializationStatus::
                LoadAnimTreesFailed);
        }
        logStage("load_anim_trees_complete");
        constexpr std::array animationScriptAssets{
            "mp/playeranim_defines.script",
            "mp/playeranim.script",
        };
        for (const auto *const assetName : animationScriptAssets)
        {
            const auto asset = findXAsset(
                AssetTypeRawFile, assetName, false);
            const auto isDefault = dbIsXAssetDefault_(
                AssetTypeRawFile, assetName);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("server animation rawfile=") + assetName +
                    " present=" + (asset.data && !isDefault ? "true" : "false") +
                    " default=" + (isDefault ? "true" : "false"));
            if (!asset.data || isDefault)
            {
                restoreFailedContext();
                return fail(ServerAnimationInitializationStatus::
                    AnimationScriptAssetsUnavailable);
            }
        }
        logStage("find_anims_begin");
        if (!invokeBGFindAnims(
                bgFindAnims_, serverContext + AnimTreeContextOffset))
        {
            restoreFailedContext();
            return fail(ServerAnimationInitializationStatus::FindAnimsFailed);
        }
        logStage("find_anims_complete");
        auto animationCount = MaximumPlayerAnimations;
        {
            char details[192]{};
            std::snprintf(
                details,
                sizeof(details),
                "server animation parser input scratch=%p context=%p count=%u thread=%lu",
                static_cast<void *>(serverLoadAnimStorage_.data()),
                static_cast<void *>(serverContext),
                animationCount,
                static_cast<unsigned long>(GetCurrentThreadId()));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, details);
        }
        NativeExceptionDetails parseException{};
        logStage("parse_anim_script_begin");
        if (!invokeBGAnimParseAnimScript(
                bgAnimParseAnimScript_,
                serverLoadAnimStorage_.data(),
                serverContext,
                animationCount,
                parseException))
        {
            char details[160]{};
            std::snprintf(
                details,
                sizeof(details),
                "server animation parser exception code=0x%08lX address=%p count=%u",
                static_cast<unsigned long>(parseException.code),
                parseException.address,
                animationCount);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, details);
            restoreFailedContext();
            return fail(
                ServerAnimationInitializationStatus::ParseAnimScriptFailed);
        }
        logStage("parse_anim_script_complete");
        logStage("precache_anim_trees_begin");
        if (!invokeScrPrecacheAnimTrees(
                scrPrecacheAnimTrees_, hunkAllocXAnim_, 0))
        {
            restoreFailedContext();
            return fail(
                ServerAnimationInitializationStatus::PrecacheAnimTreesFailed);
        }
        logStage("precache_anim_trees_complete");
        logStage("find_anim_trees_begin");
        if (!invokeNoArgument(bgFindAnimTrees_))
        {
            restoreFailedContext();
            return fail(
                ServerAnimationInitializationStatus::FindAnimTreesFailed);
        }
        logStage("find_anim_trees_complete");
        logStage("end_load_anim_trees_begin");
        const auto endLoadAnimTreesCompleted = invokeScrEndLoadAnimTrees(module_);
        scriptLoadingBegun = false;
        if (!endLoadAnimTreesCompleted)
        {
            restoreFailedContext();
            return fail(
                ServerAnimationInitializationStatus::EndLoadAnimTreesFailed);
        }
        logStage("end_load_anim_trees_complete");
        logStage("finalize_player_anims_begin");
        if (!invokeNoArgument(bgFinalizePlayerAnims_))
        {
            restoreFailedContext();
            return fail(
                ServerAnimationInitializationStatus::FinalizePlayerAnimsFailed);
        }
        logStage("finalize_player_anims_complete");
        actorHitPosesEnabled_ = loadActorHitTree;
        actorHitPoseLogCount_ = 0;
        if (loadActorHitTree)
        {
            void *actorAnims{};
            std::memcpy(&actorAnims,serverContext+708228+3*20,sizeof(actorAnims));
            const auto nodes=actorAnims && readableSpan(actorAnims,12)
                ? *static_cast<std::uint32_t *>(actorAnims) : 0u;
            actorHitPosesEnabled_=nodes>1 && nodes<=4096;
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZMPOSE init treeNodes="+std::to_string(nodes)+
                " enabled="+std::to_string(actorHitPosesEnabled_));
        }

        const auto finalAnimationCount = *reinterpret_cast<const std::uint32_t *>(
            serverContext + NumberOfPlayerAnimationsOffset);
        const auto animTree = *reinterpret_cast<void *const *>(
            serverContext + AnimTreeHandleOffset);
        if (!animationCount || animationCount > MaximumPlayerAnimations ||
            !finalAnimationCount ||
            finalAnimationCount > MaximumPlayerAnimations || !animTree ||
            *animScriptDataPointer_ != serverContext ||
            !restoreServerAnimConditionStorage(previousConditionBase))
        {
            // SIX CONDITIONS, ONE STATUS. "invalid_output" was true of all of
            // them, and three of the values it reads were 3.3.3.3 offsets, so
            // say which one is unhappy rather than making the next run guess.
            char detail[256]{};
            std::snprintf(
                detail, sizeof(detail),
                "server animation invalid output parsed=%u final=%u "
                "animTree=0x%08X scriptData=0x%08X context=0x%08X restored=%u",
                animationCount,
                finalAnimationCount,
                static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(animTree)),
                static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(
                    *animScriptDataPointer_)),
                static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(serverContext)),
                restoreServerAnimConditionStorage(previousConditionBase)
                    ? 1u : 0u);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, detail);
            InterlockedCompareExchangePointer(
                scriptSlot, previousScriptData, serverContext);
            return fail(ServerAnimationInitializationStatus::InvalidOutput);
        }

        // Parsing can use the client callbacks installed above. Runtime player
        // updates must instead own the server DObj map. CODOL's retained
        // 0x00445460 callback is client-only and marks the held model as
        // collidable; BO1/BO2 server callbacks exclude the ordinary held model
        // from collision, while Ghosts disables the callback. Keep it detached
        // until a CODOL server policy is recovered instead of changing native
        // locational traces with a presentation callback.
        *reinterpret_cast<void **>(
            serverContext + ServerCreateDObjCallbackOffset) =
            reinterpret_cast<void *>(&serverDObjCreateAdapter);
        *reinterpret_cast<void **>(
            serverContext + ServerAppendWeaponModelCallbackOffset) = nullptr;
        *reinterpret_cast<void **>(
            serverContext + ServerFreeDObjCallbackOffset) =
            reinterpret_cast<void *>(&serverDObjFreeAdapter);
        *reinterpret_cast<void **>(
            serverContext + ServerGetDObjCallbackOffset) =
            reinterpret_cast<void *>(&serverDObjGetAdapter);

        logServerAnimScriptTable(finalAnimationCount);

        serverAnimationInitializationStatus_.store(
            ServerAnimationInitializationStatus::Ready,
            std::memory_order_release);
        return ServerAnimationInitializationStatus::Ready;
    }

    void EngineBindings::logServerAnimScriptTable(
        const std::uint32_t animationCount) const
    {
        // OLMOD(locomotion-anim-diagnostics): the parse reports success by
        // filling the animation array, but the locomotion selector reads a
        // SECOND table and an empty one there is silent - every player simply
        // stays on animation record 0. Report the table the selector will
        // actually walk, so the two failures are distinguishable without a
        // debugger on the dedicated.
        // TODO(CODOL): remove once the locomotion path is proven to select an
        // animation live - the exit condition is a non-zero movetype condition
        // in the per-command line below.
        const auto *const context = serverAnimConditionStorage_.data();
        std::string populated;
        std::uint32_t populatedCount{};
        for (std::size_t moveType = 0; moveType < AnimScriptMoveTypeCount;
             ++moveType)
        {
            const auto scripts = *reinterpret_cast<const std::uint32_t *>(
                context + AnimScriptStateTableOffset +
                moveType * AnimScriptItemsStride);
            if (!scripts)
                continue;
            ++populatedCount;
            populated += ' ' + std::to_string(moveType) + ':' +
                std::to_string(scripts);
        }
        // THE EVENT TABLE, WHICH THIS INSTRUMENT COULD NEVER SEE. The line
        // above walks the MOVETYPE state table at +0x1A004 -- the locomotion
        // selector's input -- and says nothing whatever about scriptEvents at
        // +0x25F80, which is the table BG_AnimScriptEvent sub_407E10 walks and
        // the ONLY thing that can make a death return -1. Every one of the
        // thirteen runs that failed every death it saw printed a healthy
        // `populated=43/47` here, because the healthy half was the only half
        // being read. Report both, so "the parse worked" and "the parse worked
        // for the table the death event uses" stop being the same sentence.
        //
        // Counted, not sampled: sub_407790 opens `mov eax,[eax]` / `test eax,eax`
        // / `jle` on the first dword of each animScript_t, so that dword is
        // numItems and <= 0 there is exactly the silent -1. DEATH (1) and
        // RAISEWEAPON (7) are named because they are the only two events this
        // server fires; a healthy OLfinal mp/playeranim.script gives DEATH 24
        // sets and RAISEWEAPON 13.
        std::string events;
        std::uint32_t populatedEvents{};
        for (std::size_t event = 0; event < SvNativeAnimScriptEventCount;
             ++event)
        {
            const auto offset = SV_NativeAnimScriptEventOffset(
                static_cast<std::int32_t>(event));
            if (!offset)
                continue;
            const auto items =
                *reinterpret_cast<const std::int32_t *>(context + *offset);
            if (!items)
                continue;
            ++populatedEvents;
            events += ' ' + std::to_string(event) + ':' + std::to_string(items);
        }
        const auto eventItems = [context](const std::int32_t event) {
            const auto offset = SV_NativeAnimScriptEventOffset(event);
            return offset
                ? *reinterpret_cast<const std::int32_t *>(context + *offset)
                : -1;
        };
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "server animation scriptAnims anims=" +
                std::to_string(animationCount) + " populated=" +
                std::to_string(populatedCount) + '/' +
                std::to_string(AnimScriptMoveTypeCount) + populated +
                " | scriptEvents populated=" + std::to_string(populatedEvents) +
                '/' + std::to_string(SvNativeAnimScriptEventCount) +
                " DEATH=" + std::to_string(eventItems(1)) +
                " RAISEWEAPON=" + std::to_string(eventItems(7)) + events);
    }

    void EngineBindings::logServerAnimScriptEvent(
        const std::int32_t animationEvent) const
    {
        // THE ONE READING THAT SEPARATES THE TWO REMAINING CAUSES OF -1.
        // BG_AnimScriptEvent sub_407E10 returns -1 only when its walker
        // sub_407790 never writes the out-parameter the caller pre-seeded with
        // -1 at 0x00407E4B, and that happens in exactly two ways: the event has
        // no sets (`numItems <= 0` at 0x004077B0), or every set's conditions
        // failed. OLfinal's own mp/playeranim.script ends the DEATH block with
        // an unconditional `default` set of eleven animations, and sub_407790
        // cannot reject a zero-condition set -- its inner loop simply does not
        // run -- so for DEATH the second cause is impossible and an empty table
        // is the whole answer. Nothing in this project has ever read that dword.
        //
        // AND IT READS THE TABLE FROM BOTH BASES, because they are two globals.
        // sub_407E10 takes the script table from dword_827F734 (0x00407E14) and
        // the characterInfo from dword_827F730 (0x00407E37).
        // installServerAnimConditionStorage installs only the second; the first
        // holds whatever the last sub_407530 in this process left there, and
        // this project never writes it after initialisation. If `live` and
        // `ours` differ, every death since that moment walked a foreign script
        // block -- which no existing line could have shown.
        const auto offset = SV_NativeAnimScriptEventOffset(animationEvent);
        if (!offset || !animScriptDataPointer_)
            return;
        const auto *const ours = serverAnimConditionStorage_.data();
        const auto *const live = static_cast<const std::byte *>(
            InterlockedCompareExchangePointer(
                reinterpret_cast<void *volatile *>(animScriptDataPointer_),
                nullptr,
                nullptr));
        const auto read = [offset](const std::byte *const base) {
            return base && readableSpan(base + *offset, sizeof(std::int32_t))
                ? *reinterpret_cast<const std::int32_t *>(base + *offset)
                : std::numeric_limits<std::int32_t>::min();
        };
        char detail[224]{};
        std::snprintf(
            detail,
            sizeof(detail),
            "server animation scriptEvent event=%d offset=0x%zX "
            "ours=0x%08X items=%d live=0x%08X items=%d same=%u",
            animationEvent,
            *offset,
            static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(ours)),
            read(ours),
            static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(live)),
            read(live),
            live == ours ? 1u : 0u);
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, detail);
    }

    void EngineBindings::logServerAnimConditions(
        const SvNativePlayerState &playerState) const
    {
        // OLMOD(locomotion-anim-diagnostics): read back the conditions the
        // native PmoveSingle just wrote through the derived characterInfo. A
        // zero at +0x288 means the relocation is still wrong; a non-zero
        // +0x288 with a zero +0x2A0 means the conditions arrive but the
        // locomotion selector still refuses to pick an animation.
        // CODDIFF(1649370): 0x144 IS 3.3.3.3'S clientNum OFFSET. This build keeps
        // clientNum at ps+0x158 -- audit-ported-offsets has ClientNumOffset moving
        // 0x144 -> 0x158 -- and the engine itself indexes the characterInfo array
        // with it: sub_407E10 does `mov ecx, [edi+158h]` then
        // `imul ecx, 450h; lea ecx, [ecx+edx+0AF350h]`. Reading 0x144 got some
        // other field, which is almost always >= 18, so this diagnostic returned
        // WITHOUT LOGGING ANYTHING -- a silent instrument, which reads exactly like
        // a healthy one.
        constexpr std::size_t CharacterInfoSlotOffset = 0x158;
        const auto slot = *reinterpret_cast<const std::uint32_t *>(
            playerState.bytes.data() + CharacterInfoSlotOffset);
        if (slot >= ServerCharacterInfoSlotCount)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "server animation conditions: ps+0x158 is " +
                    std::to_string(slot) + ", not a characterInfo slot");
            return;
        }
        const auto characterInfo = serverCharacterInfo(slot);
        const auto read = [&characterInfo](const std::size_t offset) {
            std::uint64_t value{};
            std::memcpy(&value, characterInfo.data() + offset, sizeof(value));
            return value;
        };
        std::uint32_t nonZero{};
        for (std::size_t index = 0; index < CharacterInfoConditionCount; ++index)
        {
            if (read(CharacterInfoConditionBaseOffset + index * sizeof(std::uint64_t)))
                ++nonZero;
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "server animation conditions slot=" + std::to_string(slot) +
                " weapon=" + std::to_string(read(CharacterInfoConditionBaseOffset)) +
                " movetype=" +
                std::to_string(read(CharacterInfoMoveTypeConditionOffset)) +
                " nonzero=" + std::to_string(nonZero) + '/' +
                std::to_string(CharacterInfoConditionCount));
    }

    ServerAnimationInitializationStatus
        EngineBindings::serverAnimationInitializationStatus() const
    {
        return serverAnimationInitializationStatus_.load(
            std::memory_order_acquire);
    }

    bool EngineBindings::CCS_Clear() const
    {
        if (!ccsClear_ ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }
        if (!invokeNoArgument(ccsClear_))
            return false;
        constantConfigStringChecksum_.store(0, std::memory_order_relaxed);
        return !CCS_Initialized();
    }

    bool EngineBindings::CCS_EnsureInitialized() const
    {
        if (CCS_Initialized())
            return true;
        if (!ccsInitialize_)
            return false;
        ccsInitialize_();
        return CCS_Initialized();
    }

    std::uint32_t EngineBindings::CCS_GetChecksum() const
    {
        static_cast<void>(CCS_Initialized());
        return constantConfigStringChecksum_.load(std::memory_order_relaxed);
    }

    XAssetHeader EngineBindings::findXAsset(
        const std::uint32_t type,
        const char *const name,
        const bool allowDefault) const
    {
        if (!dbFindXAssetHeader_ || !name)
            return {};
        const auto header = dbFindXAssetHeader_(type, name, allowDefault);
        // allowDefault=false only suppresses the default on the MISS path. An
        // asset that is in the pool but not yet loaded still comes back as the
        // default placeholder, so the strict answer needs the second question
        // too - which is exactly the pair the game's own weapon resolver asks.
        if (!allowDefault && header.data && dbIsXAssetDefault_ &&
            dbIsXAssetDefault_(type, name))
        {
            return {};
        }
        return header;
    }

    const char *EngineBindings::nativeConfigString(
        const std::uint32_t index) const
    {
        if (!configStringGet_)
            return nullptr;
        return invokeConfigStringGet(configStringGet_, index);
    }

    std::optional<std::string> EngineBindings::readConfigString(
        const std::uint16_t index,
        const std::size_t maximumLength) const
    {
        if (!configStringGet_ || !maximumLength || !CCS_Initialized())
            return std::nullopt;
        const auto *value = nativeConfigString(index);
        if (readableSpan(value, 1) && !*value)
            return std::string{};
        return readCString(value, maximumLength);
    }

    std::optional<std::uint16_t>
        EngineBindings::firstDynamicWeaponAssetIndex() const
    {
        if (!module_)
            return std::nullopt;
        auto *const types = module_ + ConfigStringTypesRva;
        std::optional<std::uint16_t> configuredBoundary;
        for (std::uint16_t index = 1; index < WeaponConfigStringCount; ++index)
        {
            const auto type = types[WeaponConfigStringBase + index];
            // CODDIFF(1649370): the configstring class enum gained two members,
            // so both sentinels shift +2 - 3.3.3.3 asks for `19 || >= 21`.
            // The gamestate parser is the source: A 0x46DBF6 rejects an index
            // unless `type >= 0x15 || type == 19`, C 0x472E56 unless
            // `type >= 0x17 || type == 21`, and the weapon-count consumers
            // A 0x57A26E / C 0x590A6F test the same pair of values.
            if (type == 21 || type >= 23)
            {
                configuredBoundary = index;
                break;
            }
        }
        if (!configuredBoundary)
            return std::nullopt;

        const auto *const registryCount = reinterpret_cast<const std::uint32_t *>(
            module_ + WeaponRegistryCountRva);
        if (!readableSpan(registryCount, sizeof(*registryCount)) ||
            *registryCount < *configuredBoundary)
        {
            return configuredBoundary;
        }

        // The shipped type table fixes the modular boundary at 1224. Runtime
        // alpha WeaponDefs are ordinary base weapons, so adding them before the
        // map's normal weapon walk can push later shipped WeaponDefs beyond
        // that static boundary. The registry remains dense: skip and retag
        // every plain WeaponDef until the first actual "** ..." entry. The
        // returned index must describe the native table itself because both
        // pmove and the outgoing gamestate use it as the weapon identity.
        const auto last = std::min<std::uint32_t>(
            *registryCount, WeaponConfigStringCount - 1);
        for (std::uint32_t index = *configuredBoundary; index <= last; ++index)
        {
            const auto name = readWeaponDefinitionName(index);
            if (!name)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "dynamic weapon boundary entry unreadable index=" +
                        std::to_string(index));
                return std::nullopt;
            }
            if (SV_ParseModularWeaponConfigString(*name))
                return static_cast<std::uint16_t>(index);
            if (name->starts_with("**"))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "dynamic weapon boundary entry malformed index=" +
                        std::to_string(index) + " name=" + std::string(*name));
                return std::nullopt;
            }
            types[WeaponConfigStringBase + index] = 19;
        }

        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "dynamic weapon boundary unavailable configured=" +
                std::to_string(*configuredBoundary) + " registryCount=" +
                std::to_string(*registryCount));
        return std::nullopt;
    }

    std::optional<std::vector<SvModularWeaponConfigString>>
        EngineBindings::readDynamicWeaponConfigStrings(
            const std::uint16_t firstDynamicWeaponAssetIndex) const
    {
        if (!module_ || !firstDynamicWeaponAssetIndex ||
            firstDynamicWeaponAssetIndex >= WeaponConfigStringCount)
        {
            return std::nullopt;
        }
        const auto *registryCount = reinterpret_cast<const std::uint32_t *>(
            module_ + WeaponRegistryCountRva);
        if (!readableSpan(registryCount, sizeof(*registryCount)) ||
            *registryCount < firstDynamicWeaponAssetIndex ||
            *registryCount >= WeaponConfigStringCount)
        {
            const auto count = readableSpan(registryCount, sizeof(*registryCount))
                ? *registryCount
                : std::numeric_limits<std::uint32_t>::max();
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "dynamic weapon registry range unavailable first=" +
                    std::to_string(firstDynamicWeaponAssetIndex) +
                    " count=" + std::to_string(count));
            return std::nullopt;
        }

        std::vector<SvModularWeaponConfigString> result;
        result.reserve(*registryCount - firstDynamicWeaponAssetIndex + 1);
        for (auto index = static_cast<std::uint32_t>(
                 firstDynamicWeaponAssetIndex);
             index <= *registryCount;
             ++index)
        {
            const auto name = readWeaponDefinitionName(index);
            const auto configString = name
                ? SV_ParseModularWeaponConfigString(*name)
                : std::nullopt;
            if (!configString)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "dynamic weapon registry entry invalid index=" +
                        std::to_string(index) + " name=" +
                        (name ? std::string(*name) : "<unreadable>"));
                return std::nullopt;
            }

            result.push_back(*configString);
        }
        return result;
    }

    std::optional<std::uint16_t>
        EngineBindings::registerModularWeaponConfigString(
            const std::string_view configString) const
    {
        if (!weaponLookup_ || !weaponResolver_ || configString.empty() ||
            configString.size() >= 128 ||
            configString.find('\0') != std::string_view::npos ||
            !SV_ParseModularWeaponConfigString(configString))
        {
            return std::nullopt;
        }

        const std::string nativeName(configString);
        const auto weaponAssetIndex = weaponResolver_(
            nativeName.c_str(), nullptr);
        if (!weaponAssetIndex ||
            weaponAssetIndex >= WeaponConfigStringCount ||
            weaponLookup_(nativeName.c_str()) != weaponAssetIndex)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "campaign modular weapon registration failed definition=\"" +
                    nativeName + "\" resolved=" +
                    std::to_string(weaponAssetIndex));
            return std::nullopt;
        }

        return static_cast<std::uint16_t>(weaponAssetIndex);
    }

    std::optional<ClientBookingSelection> EngineBindings::readClientBookingSelection() const
    {
        // OLMOD(booking-selection-refusal-reasons): section 75. THIS READER HAS
        // FIVE SILENT `return std::nullopt` PATHS AND ONE CALLER THAT TREATS ALL
        // OF THEM AS "the client did not book anything".
        //
        // scan-image-literals.py reports every one of the five offsets below as
        // ABSENT FROM out.exe -- 3.3.3.3 mentions 0xF730 thirty-eight times,
        // 0xF738 fourteen, 0xF73C twenty-six, and this build mentions none of
        // them at all. They are offsets into the CLIENT's room singleton and
        // they are the other build's, so this function cannot have succeeded
        // once on 1649370.
        //
        // Nothing noticed, because CODOL_GameServerConfigureBooking falls back
        // to the map and gametype in its command string and every cycle passes
        // those explicitly. What is actually lost is the SAFETY NET: section 28c
        // records that `playlistMapRotateSequentially 0` makes each side roll
        // its own map, and that booking one the client did not roll wedges the
        // session at `clients=1 active=0` WITH NO ERROR. This reader exists to
        // catch exactly that, and it has been dead the whole time.
        //
        // Naming the paths does not fix the offsets. It stops the next reader
        // believing the silence (section 36g).
        const auto refuse = [this](const char *const reason)
            -> std::optional<ClientBookingSelection> {
            if (bookingSelectionRefusalLogCounter_++ < 4)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("client booking selection unavailable reason=") +
                        reason +
                        // THE OFFSETS ARE 1649370'S NOW -- section 187i. This line used
                        // to end "(the offsets are 3.3.3.3's -- section 75)", and after
                        // the port that sentence was simply false: it named a cause
                        // that had been fixed and would have sent the next reader
                        // straight back to a solved problem. A refusal says WHICH gate
                        // refused and nothing more.
                        " -- offsets are 1649370's (section 187i); this is the room"
                        " not being ready yet, or a selection this build does not"
                        " express as a playlist");
            }
            return std::nullopt;
        };
        if (!module_)
            return refuse("module");
        const auto roomSlot = module_ + RoomSingletonRva;
        const auto slotBytes = readableBytes(roomSlot);
        if (!slotBytes || *slotBytes < sizeof(std::uint8_t *))
            return refuse("room-slot-unreadable");
        const auto *room = *reinterpret_cast<std::uint8_t *const *>(roomSlot);
        const auto roomBytes = readableBytes(room);
        // PORTED TO 1649370. Section 187i. These were 3.3.3.3's, and the cost was not
        // a failed read -- it was the server SERVING ZOMBIES:
        //
        //   client booking selection unavailable reason=selection-kind
        //   SessionStart queued map=zm_factory_sh gametype=zm members=1
        //   gamestate configuration ACCEPTED                  <- the zombies one
        //   connectionless rejected ... XUID is not in the session roster
        //   SessionStart queued map=mp_rust_long gametype=dm members=2   <- too late
        //
        // Unable to read the selection, this fell back to a zombies default, committed
        // THAT gamestate, and then rejected every client who had booked deathmatch.
        // They all timed out, and no client has reached `active` unattended since.
        //
        // THE VALUES WERE ALREADY IN THE TREE. tools/runtime/CodolMatchFlow.py carries
        // both builds' room layouts and reads this exact object with frida, correctly:
        //
        //   {"selection_kind": "playlist", "game_type": "dm",
        //    "map_name": "mp_rust_long", "playlist_slot": 11, "rotation_index": 0}
        //
        // Its note records the derivation rather than asserting the numbers: "the whole
        // 0xF7xx booking block moves +0xEC0 and the active flag moves +0x18", corroborated
        // against the `mgr+632` host flag a live session read in StartMatch's gate. So
        // this is a port from a measured sibling, not a re-derivation -- and the frida
        // read stays available as a field-by-field oracle if any of it is ever doubted.
        // REVERTED TO 3.3.3.3's ON PURPOSE. Section 187p.
        //
        // The ported 1649370 offsets (67056/67060/67064/67068/67100) are CORRECT and
        // are kept below for whoever finishes this. They made the dedicated read the
        // client's real booking and self-book it -- which is the right behaviour and
        // immediately served `cha`, Charge, a TEAM mode, because that is what the menu
        // had selected. Two players on one side cannot damage each other, so shooting
        // stopped working.
        //
        // Three attempts to pin the gametype downstream all missed: the export next to
        // readClientBookingSelection is not on the path, and pinning the SessionStart
        // control message logged `PINNED cha -> dm` while configureGameState still
        // reported `booked=cha` -- the gamestate takes its gametype from the stored
        // booking, not from that message. Rather than keep guessing at which record
        // wins, this puts the server back where it was when deathmatch last worked
        // (17:20:09 and 17:47:59, both `booked=dm`): unable to read the client booking,
        // so configure-session's `--gametype dm` is the only session-start there is.
        //
        // THE PORTED VALUES, for when team assignment can put two players on opposing
        // sides -- do not re-derive them, they are measured and corroborated
        // (tools/runtime/CodolMatchFlow.py, and §187i):
        //     SelectionKind 67056  GameType 67060  MapName 67064
        //     PlaylistSlot  67068  RotationIndex 67100
        constexpr std::size_t SelectionKindOffset = 63280;
        constexpr std::size_t GameTypeOffset = 63284;
        constexpr std::size_t MapNameOffset = 63288;
        constexpr std::size_t PlaylistSlotOffset = 63292;
        constexpr std::size_t RotationIndexOffset = 63324;
        if (!roomBytes || *roomBytes <= RotationIndexOffset)
            return refuse("room-too-small");

        const auto selectionKind = readStringObject(room + SelectionKindOffset);
        const auto gameType = readStringObject(room + GameTypeOffset);
        const auto mapName = readStringObject(room + MapNameOffset);
        if (!selectionKind || *selectionKind != "playlist")
            return refuse("selection-kind");
        if (!gameType || !mapName ||
            !validBookingName(*gameType) || !validBookingName(*mapName))
        {
            return refuse("map-or-gametype-name");
        }
        return ClientBookingSelection{
            .mapName = *mapName,
            .gameType = *gameType,
            .playlistSlot = room[PlaylistSlotOffset],
            .rotationIndex = static_cast<std::int8_t>(room[RotationIndexOffset]),
        };
    }

    bool EngineBindings::readStagedWeaponSlot(
        const std::uint32_t slotIndex,
        ClientWeaponSelection &selection) const
    {
        OlMod::DedicatedSession::WeaponRequest request;
        return readStagedWeaponRequest(slotIndex, request) &&
            resolveWeaponRequest(request, selection);
    }

    // MEASURED AFTER THE FACT, AND IT IS NOT THE PLAYER'S CLASS. This reads A
    // document and returns structured data -- five classes, two weapons each,
    // attachment ids -- but not the loaded player profile:
    //
    //   two clients report byte-identical loadouts while holding an M4 and a
    //     CheyTac;
    //   editing a class in the UI moves no returned value;
    //   the ids (10000, 10009, 10014 ...) appear NOWHERE in mp_coweapitemswea.csv,
    //     the 838-row weapon table where m4a1tech_mp is 42.
    //
    // Most likely sub_7F9090()+160 is not the loaded player profile in this
    // calling context. The fix is to stop asking the client at all: the server
    // already holds the blob and mp/playerdata.def decodes it -- see handoff
    // section 155c and Tools/olfinal/playerdata-def.py.
    bool EngineBindings::readProfileWeaponRequest(
        const std::uint32_t classIndex,
        const bool secondary,
        OlMod::DedicatedSession::WeaponRequest &request) const
    {
        if (!weaponClassFieldGet_ ||
            classIndex >= OlMod::DedicatedSession::LoadoutClassCount)
        {
            return false;
        }
        const auto *const base = secondary ? "secondaryBase" : "primaryBase";
        const auto *const attach =
            secondary ? "secondaryAttach" : "primaryAttach";
        const auto index = static_cast<std::int32_t>(classIndex);
        const auto itemId = invokeWeaponClassFieldGet(
            weaponClassFieldGet_, -1, base, index);
        // NO WEAPON IS NOT A FAILURE. A class with an empty secondary is a
        // legal class, and refusing it here would drop the whole loadout the
        // way the staged reader used to.
        if (!itemId || *itemId < 0 || *itemId > 0xFFFF)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::StagedSlot,
                std::memory_order_relaxed);
            return false;
        }
        OlMod::DedicatedSession::WeaponRequest candidate{
            .itemId = static_cast<std::uint32_t>(*itemId),
        };
        for (std::int32_t slot = 0;
             slot < static_cast<std::int32_t>(
                 OlMod::DedicatedSession::AttachmentCount);
             ++slot)
        {
            const auto attachment = invokeWeaponClassFieldGet(
                weaponClassFieldGet_, slot, attach, index);
            if (!attachment || *attachment < 0 || *attachment > 0xFFFF)
                continue;
            candidate.attachmentItemIds[static_cast<std::size_t>(slot)] =
                static_cast<std::uint32_t>(*attachment);
        }
        request = candidate;
        return true;
    }

    // THE CLIENT'S LIVE LOADOUT, straight out of the record out.exe builds for itself.
    //
    // This is the answer to the question captureClientLoadoutRequest has been getting
    // wrong: readProfileWeaponRequest returns a document that is provably not the
    // player's class (identical across two clients holding different guns, unmoved by
    // edits), and the staged path is unbound. Both were substitutes for asking the
    // client what it is actually holding, which is what sub_7C5BA0 answers.
    //
    // ONE CLASS, NOT FIVE. The record covers the CURRENT class only -- sub_7C5A50 indexes
    // dword_7889B20 by the live class index and walks four weapon slots inside it. So this
    // fills classes[0] and sets bit 0 of classMask; the caller's existing loop still gets
    // its chance at the rest. A player spawning with the weapon they are looking at is
    // worth more than five classes of the wrong one.
    // ALL FIVE CLASSES, from the profile document the client itself edits.
    //
    // This is what makes an in-match class switch change the weapon. The record
    // path above holds only the CURRENTLY SELECTED class; mirroring it left
    // custom1..custom5 identical, so switching class re-resolved the same gun.
    // The structured profile document holds all five, per character, and reading
    // it is a bounded MEMORY READ -- not the sub_50FF30 native call that
    // profileSlotProbeEnabled() gates off for its bridge-thread safety. See
    // ProfileManagerRva and Tools/olfinal/decode-profile-blob.py, which validates
    // this exact key/rotate/offset scheme against a live dump.
    //
    // Attachments are deliberately NOT read here yet: the record/`--loadout` paths
    // already omit them because a stale attachment id names a tag the weapon model
    // does not have and faults the client at spawn. The base weapon is the whole
    // of what the player is asking to change; attachments are a measured follow-up.
    // THE SCHEMA, ASKED OF THE DEF BY NAME. See PlayerDataDef.hpp for why.
    //
    // The eight constants below were each measured by hand off this build's def, and six
    // of them are DIFFERENT on 3.3.3.3 (605/14/5 there is 576/10/1; 1607/37 is 1154/36).
    // They are kept as the fallback for a def this walker cannot read, and as a
    // cross-check the caller logs -- not as the answer. The two attachment ordinals were
    // never measured at all: they were derived as `weaponOrdinal - AttachmentCount`,
    // arithmetic the source itself called numerology after it landed on the wrong weapon
    // once (sections 187g and 187m). The def NAMES them.
    EngineBindings::ProfileLayout EngineBindings::resolveProfileLayout(
        const void *const def)
    {
        constexpr auto attachmentCount =
            static_cast<std::uint32_t>(OlMod::DedicatedSession::AttachmentCount);
        ProfileLayout layout{
            .characterSlotsBase = CharacterClassesBaseIndex + CharacterSlotsOrdinal,
            .characterStride = CharacterClassIndexStride,
            .characterCount =
                static_cast<std::uint32_t>(OlMod::DedicatedSession::CharacterItemCount),
            .slotCount = static_cast<std::uint32_t>(CharacterProfileSlotCount),
            .weaponClassBase = WeaponClassesBaseIndex,
            .weaponClassStride = WeaponClassIndexStride,
            // Twelve characters of five classes, on this build.
            .weaponClassCount = static_cast<std::uint32_t>(
                OlMod::DedicatedSession::CharacterItemCount) * WeaponClassesPerCharacter,
            .classesPerCharacter = WeaponClassesPerCharacter,
            .primaryBase = WeaponClassPrimaryBaseOrdinal,
            .secondaryBase = WeaponClassSecondaryBaseOrdinal,
            .primaryAttach = WeaponClassPrimaryBaseOrdinal - attachmentCount,
            .secondaryAttach = WeaponClassSecondaryBaseOrdinal - attachmentCount,
            .attachCount = attachmentCount,
            .byName = false,
        };

        const auto schema = PlayerDataDef::open(def, readableSpan);
        if (!schema)
            return layout;

        const auto characters = schema->resolve("characterClasses");
        const auto slots = schema->resolve("characterClasses[0].slots");
        const auto weapons = schema->resolve("weaponClasses");
        const auto primary = schema->resolve("weaponClasses[0].primaryBase");
        const auto secondary = schema->resolve("weaponClasses[0].secondaryBase");
        const auto primaryAttach = schema->resolve("weaponClasses[0].primaryAttach");
        const auto secondaryAttach = schema->resolve("weaponClasses[0].secondaryAttach");
        if (!characters || !slots || !weapons || !primary || !secondary ||
            !primaryAttach || !secondaryAttach)
        {
            return layout;
        }
        // Every ordinal is measured from the class element's own base, so a class that
        // moves as a whole does not move its fields. A field BELOW that base is not an
        // ordinal of this struct and means the walk went somewhere unexpected.
        if (primary->index < weapons->index || secondary->index < weapons->index ||
            primaryAttach->index < weapons->index ||
            secondaryAttach->index < weapons->index)
        {
            return layout;
        }

        layout.characterSlotsBase = slots->index;
        layout.characterStride = characters->stride;
        layout.characterCount = characters->count;
        // THE ARRAY IS SIZED BY THE WIRE FORMAT, NOT BY THE DEF. profileSlots is
        // CharacterProfileSlotCount wide because that is what a LoadoutRequest carries;
        // a def declaring more would be a write past the end, so take the smaller.
        layout.slotCount = std::min(
            slots->count, static_cast<std::uint32_t>(CharacterProfileSlotCount));
        layout.weaponClassBase = weapons->index;
        layout.weaponClassStride = weapons->stride;
        layout.weaponClassCount = weapons->count;
        // weaponClasses is FLAT -- sixty entries that are twelve characters of five
        // classes -- and the def does not say where the split is, only how long the whole
        // array is. Dividing is the one honest way to get it, and a def whose two arrays
        // do not divide evenly is one this partitioning does not describe, so the
        // measured five stands rather than a rounded-down guess.
        if (characters->count && weapons->count % characters->count == 0)
            layout.classesPerCharacter = weapons->count / characters->count;
        layout.primaryBase = primary->index - weapons->index;
        layout.secondaryBase = secondary->index - weapons->index;
        layout.primaryAttach = primaryAttach->index - weapons->index;
        layout.secondaryAttach = secondaryAttach->index - weapons->index;
        layout.attachCount = std::min(
            { primaryAttach->count, secondaryAttach->count, attachmentCount });
        layout.byName = true;
        const auto perks = schema->resolve("weaponClasses[0].perks");
        if (perks && perks->index >= weapons->index && perks->stride &&
            perks->count <= OlMod::DedicatedSession::PerkSlotCount &&
            perks->index - weapons->index + perks->count * perks->stride <=
                weapons->stride)
        {
            layout.perksBase = perks->index - weapons->index;
            layout.perksCount = perks->count;
            layout.perksStride = perks->stride;
        }
        // CODREF(out.exe 1649370): 0x50FC20 reads these class item fields;
        // 0x50FD20 reads lethalDoubleAmmo/tacticalDoubleAmmo via 0x50F410's
        // category-2 bit reader. Booleans are not obfuscated integer fields.
        const auto rewards = schema->resolve("weaponClasses[0].killstreaks");
        if (rewards && rewards->index >= weapons->index && rewards->stride &&
            rewards->count >= OlMod::DedicatedSession::RewardSlotCount &&
            rewards->index - weapons->index + rewards->count * rewards->stride <=
                weapons->stride)
        {
            layout.rewardsBase = rewards->index;
            layout.rewardsStride = rewards->stride;
        }
        constexpr std::array names{ "lethal", "tactical" };
        for (std::size_t slot{}; slot < names.size(); ++slot)
        {
            const auto field = schema->resolve(
                "weaponClasses[0]." + std::string(names[slot]));
            if (field && field->category == PlayerDataDef::CategoryInt &&
                field->index >= weapons->index &&
                field->index - weapons->index < weapons->stride)
                layout.equipmentBase[slot] = field->index - weapons->index;
            const auto count = schema->resolve(
                "weaponClasses[0]." + std::string(names[slot]) + "DoubleAmmo");
            if (count && count->category == PlayerDataDef::CategoryBool &&
                count->index >= weapons->index &&
                count->index - weapons->index < weapons->stride)
                layout.equipmentDoubleAmmoBase[slot] = count->index - weapons->index;
        }
        return layout;
    }

    bool EngineBindings::readProfileWeaponClasses(
        OlMod::DedicatedSession::LoadoutRequest &request) const
    {
        if (!module_ || !dbFindXAssetHeader_ || !currentCharacterGet_)
            return false;

        auto *const manager = module_ + ProfileManagerRva;
        if (!readableSpan(manager, ProfileObfuscatedFlagOffset + 1))
            return false;
        const auto key = *reinterpret_cast<const std::uint32_t *>(
            manager + ProfileDecodeKeyOffset);
        const bool obfuscated =
            *reinterpret_cast<const std::uint8_t *>(
                manager + ProfileObfuscatedFlagOffset) != 0;
        const auto *const dataBuffer = manager + ProfileDataBufferOffset;

        // def = *(DB_FindXAssetHeader(39, "mp/playerdata.def") + 8); its +0x38 is
        // the index -> byte-offset table sub_50F410 converts through.
        const auto header = findXAsset(
            AssetTypeStructuredDataDef, "mp/playerdata.def", false);
        if (!header.data ||
            !readableSpan(
                header.data,
                PlayerDataDefBufferPointerOffset + sizeof(void *)))
        {
            return false;
        }
        const auto *const def = *reinterpret_cast<std::uint8_t *const *>(
            static_cast<const std::uint8_t *>(header.data) +
            PlayerDataDefBufferPointerOffset);
        if (!readableSpan(
                def, PlayerDataDefOffsetTablePtrOffset + sizeof(void *)))
        {
            return false;
        }
        const auto *const offsetTable =
            *reinterpret_cast<const std::uint32_t *const *>(
                def + PlayerDataDefOffsetTablePtrOffset);

        // WHICH FIELDS THIS DEF PUTS WHERE. Everything below used to be a constant of
        // build 1649370; resolveProfileLayout asks the def by name instead. The line says
        // which path ran and names every value it disagrees with, so a def change is a
        // visible event rather than a loadout that quietly reads the wrong property.
        const auto layout = resolveProfileLayout(def);
        {
            const auto compare = [](const char *const name,
                                    const std::uint32_t got,
                                    const std::uint32_t measured) {
                return got == measured
                    ? std::string()
                    : " " + std::string(name) + "=" + std::to_string(got) +
                        "(measured " + std::to_string(measured) + ")";
            };
            std::string line = layout.byName
                ? "profile layout BY NAME:"
                : "profile layout FALLBACK -- the def did not walk, using build 1649370's "
                  "measured ordinals:";
            line += " characterSlots=" + std::to_string(layout.characterSlotsBase) +
                "/" + std::to_string(layout.characterStride) +
                " x" + std::to_string(layout.slotCount) +
                " weaponClasses=" + std::to_string(layout.weaponClassBase) +
                "/" + std::to_string(layout.weaponClassStride) +
                " x" + std::to_string(layout.weaponClassCount) +
                " (" + std::to_string(layout.characterCount) + " characters x " +
                std::to_string(layout.classesPerCharacter) + ")" +
                " primary=" + std::to_string(layout.primaryBase) +
                " secondary=" + std::to_string(layout.secondaryBase) +
                " primaryAttach=" + std::to_string(layout.primaryAttach) +
                " secondaryAttach=" + std::to_string(layout.secondaryAttach) +
                " x" + std::to_string(layout.attachCount);
            if (layout.byName)
            {
                const auto disagreement =
                    compare("characterSlots",
                            layout.characterSlotsBase,
                            CharacterClassesBaseIndex + CharacterSlotsOrdinal) +
                    compare("characterStride",
                            layout.characterStride, CharacterClassIndexStride) +
                    compare("weaponClassBase",
                            layout.weaponClassBase, WeaponClassesBaseIndex) +
                    compare("weaponClassStride",
                            layout.weaponClassStride, WeaponClassIndexStride) +
                    compare("primary",
                            layout.primaryBase, WeaponClassPrimaryBaseOrdinal) +
                    compare("secondary",
                            layout.secondaryBase, WeaponClassSecondaryBaseOrdinal);
                line += disagreement.empty()
                    ? " -- agrees with every measured ordinal"
                    : " -- DISAGREES WITH THE MEASURED ORDINALS:" + disagreement;
            }
            static std::string reported;
            if (reported != line)
            {
                reported = line;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }

        // BOUNDED BY characterClasses, NOT BY THE ITEM RECORD. CharacterItemCount is the
        // width of the twelve-entry item record sub_619E90 fills, which is a DIFFERENT
        // array that merely happens to be twelve long on this build too -- the note on
        // CharacterProfileSlotCount says as much, and the same conflation is what read
        // past the end of the nine-wide `slots`. The def knows how many characters there
        // are; ask it.
        // THE UNLOCK-ALL CHECK BELONGS HERE, NOT ON resolveWeaponItem.
        //
        // It was hung off the first weapon resolution, and that is a DEDICATED-side path:
        // the dedicated got there first and the client never ran it at all, so the probe
        // answered from a process with no player in it and the gate then made it answer
        // nothing. This function is the client's own profile read -- it is what logs
        // `profile layout BY NAME` and `client loadout classes` under
        // [client/game-server] -- so it runs in the process the patch is applied to, and
        // late enough that the inventory exists.
        {
            static std::once_flag checked;
            std::call_once(checked, [this] {
                char *value = nullptr;
                std::size_t size = 0;
                if (_dupenv_s(&value, &size, "OLMOD_UNLOCK_ALL") != 0 || !value)
                    return;
                const bool wanted = value[0] == '1';
                free(value);
                if (wanted)
                    reportUnlockAllCoverage();
            });
        }
        {
            static std::once_flag swept;
            std::call_once(swept, [this] {
                char *value = nullptr;
                std::size_t size = 0;
                if (_dupenv_s(&value, &size, "OLMOD_AUDIT_ITEM_NAMES") != 0 || !value)
                    return;
                const bool wanted = value[0] == '1';
                free(value);
                if (!wanted)
                    return;
                // ON ITS OWN THREAD, AND THIS IS NOT A TIDINESS POINT. Run inline it
                // stalled the client BRIDGE thread for 60,249 item lookups, which is the
                // thread `--capture-from` talks to -- so the loadout capture never
                // answered, the host sat at `clients=1 active=0`, and the player sat on
                // the loading screen watching nothing happen. A diagnostic that stops the
                // game is worse than no diagnostic.
                std::thread([this] { auditItemNames(); }).detach();
            });
        }

        const auto rawCharacter = currentCharacterGet_();
        if (rawCharacter < 0 ||
            rawCharacter >= static_cast<int>(layout.characterCount))
        {
            return false;
        }
        const auto characterIndex = static_cast<std::uint32_t>(rawCharacter);

        // index -> byte offset -> deobfuscated dword, every step bounds-checked.
        // Declared before the character-item read below uses it.
        // The document is 0x8000 bytes; a byte offset at or past that is a corrupt
        // table read, not a value. An unwritten field decodes to ROL32(key, 8),
        // which is far above 0xFFFF and so is rejected as a weapon id anyway.
        const auto readIndex =
            [&](const std::uint32_t index) -> std::optional<std::uint32_t> {
            if (!readableSpan(offsetTable + index, sizeof(std::uint32_t)))
                return std::nullopt;
            const auto byteOffset = offsetTable[index];
            if (byteOffset + sizeof(std::uint32_t) > ProfileDocumentSize)
                return std::nullopt;
            if (!readableSpan(dataBuffer + byteOffset, sizeof(std::uint32_t)))
                return std::nullopt;
            const auto raw = *reinterpret_cast<const std::uint32_t *>(
                dataBuffer + byteOffset);
            return obfuscated ? std::rotl(raw ^ key, 8) : raw;
        };

        const auto weaponId = [](const std::optional<std::uint32_t> &value) {
            return value && *value != 0 && *value <= 0xFFFFu;
        };

        // THE CHARACTER ITEMS, from the document too, so the capture needs no room
        // (the record path's items come from the room cache, which is empty until a
        // room join). characterClasses[character].slots[0..8]. valid() requires slot
        // 0 to be non-zero, so a document with no character read fails cleanly here.
        std::array<std::uint32_t, OlMod::DedicatedSession::CharacterItemCount>
            characterItemIds{};
        const auto characterSlotBase = layout.characterSlotsBase +
            characterIndex * layout.characterStride;
        std::array<std::uint32_t, CharacterProfileSlotCount> profileSlots{};
        for (std::uint32_t slot = 0; slot < layout.slotCount; ++slot)
        {
            const auto item = readIndex(characterSlotBase + slot);
            if (item && *item <= 0xFFFFu)
                profileSlots[slot] = *item;
        }
        // The profile's order is not the record's -- see the placer.
        placeCharacterItemsByRecordEntry(profileSlots, characterItemIds);
        // SAY WHICH CHARACTER THIS DOCUMENT READ, AND WHAT ITS SLOTS HOLD.
        //
        // THIS is the path that runs. The same line was first put on the profile-slot
        // probe at ~10002 and printed NOTHING for a whole cycle, because that path
        // needs a room cache that is empty until a room join -- the comment above says
        // so outright and I instrumented the other one anyway.
        //
        // What it decides: the room roster carries real, DISTINCT character items per
        // player (measured 2056 and 686 in one cycle, and 545 for everyone before
        // that), while every model request this server makes still carries one item.
        // So either this document read returns the same character whatever the player
        // picked, or it returns the right one and the value is lost downstream. Those
        // are different bugs and nothing currently logged separates them.
        //
        // Deduped on the whole tuple: one line if it never changes, two if it does.
        {
            std::string line = "character document: index=" +
                std::to_string(characterIndex) + " slots=";
            for (std::size_t entry = 0; entry < profileSlots.size(); ++entry)
                line += (entry ? "," : "") + std::to_string(profileSlots[entry]);
            line += " record0=" + std::to_string(characterItemIds.front());
            static std::string reported;
            if (reported != line)
            {
                reported = line;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        if (!characterItemIds.front())
            return false;

        std::array<OlMod::DedicatedSession::ClassRequest,
                   OlMod::DedicatedSession::LoadoutClassCount> classes{};
        std::uint8_t classMask = 0;
        for (std::uint32_t classIndex = 0;
             classIndex < OlMod::DedicatedSession::LoadoutClassCount; ++classIndex)
        {
            const auto slot =
                characterIndex * layout.classesPerCharacter + classIndex;
            // The def says how many classes the array holds AND how many of them belong
            // to one character. Reading past the first walks into whatever property
            // follows weaponClasses; past the second, into the NEXT character's loadout,
            // which is the more dangerous of the two because it yields a real weapon.
            if (classIndex >= layout.classesPerCharacter ||
                slot >= layout.weaponClassCount)
            {
                continue;
            }
            const auto base =
                layout.weaponClassBase + slot * layout.weaponClassStride;
            const auto primary = readIndex(base + layout.primaryBase);
            const auto secondary =
                readIndex(base + layout.secondaryBase);
            // BOTH OR NEITHER. valid() enforces present == (itemId != 0) for every
            // weapon under a set bit, so a class with an empty secondary cannot be
            // registered half-filled -- it is left absent, its bit clear.
            if (!weaponId(primary) || !weaponId(secondary))
                continue;
            classes[classIndex].weapons[0].itemId = *primary;
            classes[classIndex].weapons[1].itemId = *secondary;

            // AND THE ATTACHMENTS. Section 187.
            //
            // Ordinals: primary at 22, secondary at 29 -- a gap of exactly SEVEN --
            // and AttachmentCount is SIX, so each weapon is one item id followed by its
            // six attachments. The stride of 37 holds both (22..35) with one spare.
            // mp/playerdata.def names the properties primaryBase and primaryAttach, and
            // decode-profile-blob.py reads the second as an indexed array. Confirmed
            // live: EQUIPPED=1 reached the modular string carrying id 6206, which is an
            // id retail itself publishes.
            //
            // An ordinal that is zero or out of range is skipped here;
            // resolveWeaponItem applies the real validation, including the strict
            // attachmentSupportedByWeapon test that this feature turned out to need.
            // ATTACHMENTS PRECEDE THEIR WEAPON. Section 187m, and this is measured.
            //
            // A full dump of the 37-ordinal class block:
            //
            //   class=0 weapons=10609/10028
            //     16=for_gripvtlong2ak104ss  17=sco_targetfinderak104ss
            //     22=ak104ss_mp   <- PRIMARY      23=red_rmrtmp      29=tmp_mp <- SECONDARY
            //   class=2 weapons=10015/10042
            //     16=red_rmrl86   17=mag_extclipl86
            //     22=l86_mp       <- PRIMARY      29=stinger_mp <- SECONDARY
            //
            // 16 and 17 name the PRIMARY's own parts in both classes, and 23 names
            // `red_rmrtmp` while `tmp_mp` sits at 29 -- the SECONDARY. So each weapon's
            // six attachments come BEFORE it: 16..21 then the primary at 22, 23..28 then
            // the secondary at 29.
            //
            // This code read 23..28 and gave them to the PRIMARY -- the secondary's
            // attachments on the wrong gun. That is why only the one at 23 ever showed
            // up, why everything else answered "not supported by this weapon", and why
            // the translated id built a variant whose index the client did not share,
            // which refused every bullet (§187l).
            //
            // The "gap of exactly SEVEN" I built the first reading on was right about
            // the width and wrong about the ORDER: six attachments then the weapon, not
            // the weapon then six attachments.
            const auto readAttachments = [&](const std::uint32_t firstAttachmentOrdinal,
                                              const std::size_t weaponSlot) {
                auto &attachments =
                    classes[classIndex].weapons[weaponSlot].attachmentItemIds;
                for (std::size_t entry = 0; entry < layout.attachCount; ++entry)
                {
                    const auto value = readIndex(
                        base + firstAttachmentOrdinal +
                        static_cast<std::uint32_t>(entry));
                    if (!value || !*value || *value > 0xFFFFu)
                        continue;
                    attachments[entry] = *value;
                    // WHICH CLASS, WHICH WEAPON SLOT, WHICH ORDINAL, AND WHAT THE ITEM
                    // IS CALLED. Section 187e: item 25703 resolves to `red_rmrtmp`, a
                    // TMP-specific model, and the profile presents it for an MSR and an
                    // M4. Either 25703 is a GENERIC red-dot whose per-weapon model must
                    // come from the weapon's own table by type, or this read is
                    // misattributing one class's attachment to another class's weapon.
                    // Those two need opposite fixes and the difference is visible here:
                    // if the same id appears under one classIndex only, the read is
                    // right and the id is generic; if it appears under several, the
                    // ordinal arithmetic is wrong.
                    static std::mutex ordinalMutex;
                    static std::set<std::string> ordinalReported;
                    const auto itemName = readItemInternalName(*value);
                    auto line = "profile attach class=" + std::to_string(classIndex) +
                        " weaponSlot=" + std::to_string(weaponSlot) +
                        " ordinal=" + std::to_string(firstAttachmentOrdinal + entry) +
                        " item=" + std::to_string(*value) +
                        " name=" + (itemName ? *itemName : std::string("<none>")) +
                        " weaponItem=" +
                        std::to_string(classes[classIndex].weapons[weaponSlot].itemId);
                    const std::lock_guard lock(ordinalMutex);
                    if (ordinalReported.insert(line).second)
                    {
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer, line);
                    }
                }
            };
            // AND THESE ORDINALS NOW COME FROM THE DEF, WHICH NAMES THEM.
            //
            // Two readings of this got shipped before the def was asked. The first put
            // the attachments AFTER their weapon -- ordinals 30..35 for the secondary --
            // and the provenance line said what they really are:
            //
            //   class=0 weaponSlot=1 ordinal=32 item=60006 name=emp_grenade_mp
            //   class=1 weaponSlot=1 ordinal=32 item=60005 name=smoke_grenade_mp
            //   class=2 weaponSlot=1 ordinal=34 item=60186 name=fragshort_grenade_mp
            //
            // the LETHAL and TACTICAL equipment slots, which is why every one of them
            // failed readAttachmentModelSlot with "has no model slot". Section 187m then
            // put them BEFORE the weapon (`weaponOrdinal - AttachmentCount`), which lands
            // on 16 and 23 and is right -- but only because six happens to be both the
            // array's width and the distance to it. The comment that came with it also
            // asserted this def has "NO secondaryAttach"; it has one, at ordinal 23, six
            // wide, on BOTH builds. That claim was never checked against the def.
            //
            // resolveProfileLayout asks for the names primaryAttach and secondaryAttach
            // directly, so neither the distance nor the width is inferred any more.
            readAttachments(layout.primaryAttach, 0);
            readAttachments(layout.secondaryAttach, 1);

            auto &equipment = classes[classIndex].equipment;
            for (std::size_t equipmentSlot{}; equipmentSlot < 2; ++equipmentSlot)
            {
                if (layout.equipmentBase[equipmentSlot])
                {
                    const auto value = readIndex(base + *layout.equipmentBase[equipmentSlot]);
                    if (value && *value <= 0xFFFFu)
                        equipment.itemIds[equipmentSlot] = *value;
                }
                if (layout.equipmentDoubleAmmoBase[equipmentSlot])
                {
                    const auto index = base + *layout.equipmentDoubleAmmoBase[equipmentSlot];
                    if (readableSpan(offsetTable + index, sizeof(std::uint32_t)))
                    {
                        const auto bit = offsetTable[index];
                        if ((bit >> 3) < ProfileDocumentSize &&
                            readableSpan(dataBuffer + (bit >> 3), 1) &&
                            (dataBuffer[bit >> 3] & (1u << (bit & 7))))
                            equipment.doubleAmmoMask |= 1u << equipmentSlot;
                    }
                }
            }
            for (std::uint32_t entry = 0; entry < layout.perksCount; ++entry)
            {
                const auto value = readIndex(
                    base + layout.perksBase + entry * layout.perksStride);
                if (value && *value <= 0xFFFFu)
                    classes[classIndex].perkItemIds[entry] = *value;
            }

            classMask |= static_cast<std::uint8_t>(1u << classIndex);
        }

        if (!classMask)
            return false;
        request.characterIndex = characterIndex;
        request.characterItemIds = characterItemIds;
        request.classes = classes;
        request.classMask = classMask;
        request.rewardItemIds = {};
        // Native 0x7C633D reads three slots from weaponClasses[0], regardless
        // of the selected character/class. Keep raw ID+1 values on this bridge.
        if (layout.rewardsBase)
            for (std::size_t slot{}; slot < request.rewardItemIds.size(); ++slot)
            {
                const auto value = readIndex(*layout.rewardsBase +
                    static_cast<std::uint32_t>(slot) * layout.rewardsStride);
                if (value && *value <= 0xFFFFu)
                    request.rewardItemIds[slot] = *value;
            }
        return true;
    }

    bool EngineBindings::readLoadoutRecord(
        OlMod::DedicatedSession::LoadoutRequest &request) const
    {
        if (!loadoutRecordBuild_)
            return false;

        // ZEROED, and the whole 160 bytes of it. sub_7C6480 qmemcpy's exactly this much
        // around the record, and a field the callee does not write must read as "nothing"
        // rather than as whatever was on the stack.
        std::array<unsigned short, LoadoutRecordWords> record{};

        // WHOSE RECORD ARE WE AFTER. Read the owner's cache keys first; with them the
        // slot is chosen rather than guessed.
        std::uint32_t ownerKeys[2]{};
        bool haveOwnerKeys = false;
        for (const auto rva : {LoadoutOwnerPrimaryRva, LoadoutOwnerFallbackRva})
        {
            if (!readableSpan(module_ + rva, sizeof(std::uint32_t)))
                continue;
            const auto owner =
                *reinterpret_cast<const std::uint32_t *>(module_ + rva);
            if (!owner)
                continue;
            const auto *at = reinterpret_cast<const std::uint8_t *>(
                static_cast<std::uintptr_t>(owner)) + LoadoutOwnerKeyOffset;
            if (!readableSpan(at, sizeof(ownerKeys)))
                continue;
            ownerKeys[0] = reinterpret_cast<const std::uint32_t *>(at)[0];
            ownerKeys[1] = reinterpret_cast<const std::uint32_t *>(at)[1];
            haveOwnerKeys = true;
            break;
        }

        // THE CACHE FIRST. A populated slot is the record the client built for itself,
        // and reading it costs nothing and risks nothing.
        std::size_t populated = 0;
        for (std::size_t slot = 0; slot < LoadoutRecordCacheSlots; ++slot)
        {
            const auto at = module_ + LoadoutRecordCacheRva +
                slot * LoadoutRecordCacheStride + LoadoutRecordCacheOffset;
            if (!readableSpan(at, LoadoutRecordWords * sizeof(unsigned short)))
                continue;

            const auto *words = reinterpret_cast<const unsigned short *>(at);

            // The record's first two dwords are the cache keys. When the owner's keys are
            // readable, take only the slot that matches; otherwise fall back to "any
            // populated slot" and let the count below report the ambiguity.
            if (haveOwnerKeys)
            {
                const auto *keys = reinterpret_cast<const std::uint32_t *>(at);
                if (keys[0] != ownerKeys[0] || keys[1] != ownerKeys[1])
                    continue;
            }

            const auto primary = words[LoadoutRecordWeaponWord];
            const auto secondary =
                words[LoadoutRecordWeaponWord + LoadoutRecordWeaponStride];
            if (!primary || !secondary)
                continue;

            if (!populated)
                std::copy_n(words, LoadoutRecordWords, record.begin());
            ++populated;
        }

        // AND SAY IF THE CHOICE WAS AMBIGUOUS. One populated slot is the local player's
        // loadout; several means this is picking one of them and the keys would have to
        // disambiguate. Silence here would make a wrong class look like a decode bug.
        if (populated > 1)
        {
            static std::size_t LastPopulated;
            if (populated != LastPopulated)
            {
                LastPopulated = populated;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "client loadout cache has " + std::to_string(populated) +
                        " populated slots -- taking the first");
            }
        }

        // Only rebuild if the cache had nothing. This is the native call the probe gate
        // exists to worry about, so it is the fallback and not the first move.
        if (!populated)
            static_cast<void>(loadoutRecordBuild_(record.data()));

        // FOUR WEAPONS IS TWO CLASSES, NOT ONE. sub_7C5A50 writes four 7-word weapon
        // groups, and WeaponsPerClass is 2 -- so the record carries classes 0 and 1 back
        // to back. Reading only the first two threw half of it away and produced a
        // one-class request, and EVERY SessionStart that has ever been accepted on this
        // build logged classMask=3. The one-class ones queue and never commit.
        //
        // ALL OR NOTHING PER CLASS, because valid() enforces
        // `present != (weapon.itemId != 0)`: a class whose bit is set must have every
        // weapon filled, and a class whose bit is clear must have none.
        std::array<OlMod::DedicatedSession::ClassRequest,
                   LoadoutRecordClasses> staged{};
        std::array<bool, LoadoutRecordClasses> stagedComplete{};
        bool complete = false;

        for (std::size_t classIndex = 0; classIndex < LoadoutRecordClasses; ++classIndex)
        {
            bool whole = true;
            for (std::size_t slot = 0;
                 slot < OlMod::DedicatedSession::WeaponsPerClass; ++slot)
            {
                const auto weaponIndex =
                    classIndex * OlMod::DedicatedSession::WeaponsPerClass + slot;
                const auto at =
                    LoadoutRecordWeaponWord + weaponIndex * LoadoutRecordWeaponStride;
                if (at + OlMod::DedicatedSession::AttachmentCount >= record.size())
                {
                    whole = false;
                    break;
                }

                const auto itemId = record[at];
                if (!itemId)
                {
                    whole = false;
                    break;
                }

                auto &weapon = staged[classIndex].weapons[slot];
                weapon.itemId = itemId;
                for (std::size_t index = 0;
                     index < OlMod::DedicatedSession::AttachmentCount; ++index)
                {
                    weapon.attachmentItemIds[index] = record[at + 1 + index];
                }
            }
            stagedComplete[classIndex] = whole;
            complete = complete || whole;
        }

        // THE CHARACTER ITEMS COME FROM THE RECORD TOO, and that is the point of this
        // path: valid() needs characterItemIds.front(), and the only other source for it
        // is sub_50FF30, whose call is exactly what OLMOD_PROBE_PROFILE_SLOTS gates off.
        // Words 12..23 are the same twelve ids, already decoded by the client for itself.
        for (std::size_t index = 0;
             index < OlMod::DedicatedSession::CharacterItemCount; ++index)
        {
            request.characterItemIds[index] =
                record[LoadoutRecordCharacterWord + index];
        }

        // AND THE INDEX THE WAY THE ENGINE TAKES IT. sub_6B87C0 reads a cached dvar and
        // clamps negatives to zero; it does not call sub_50FF30 and is not what the probe
        // gate protects, so it is safe to use here where currentCharacterIndex() is not.
        if (currentCharacterGet_)
        {
            const auto raw = currentCharacterGet_();
            if (raw >= 0 &&
                raw < static_cast<int>(OlMod::DedicatedSession::CharacterItemCount))
            {
                request.characterIndex = static_cast<std::uint32_t>(raw);
            }
        }

        // MIRROR THE CAPTURED CLASS ACROSS EVERY SLOT.
        //
        // The record reports ONE class -- weapons 2 and 3 read zero -- but the player's UI
        // has five, and the spawn asks for whichever slot they have selected. Registering
        // only class 0 left `snapshot build rejected failure=missing_playerstate` and both
        // clients stuck on 等待玩家数据 with active=2 and snapshots=0, while a two-class
        // fixture on the same stack produced snapshots immediately.
        //
        // Mirroring is not a guess about which slot they will pick: it makes every slot
        // resolve to the weapons they are actually holding. When the record eventually
        // yields more than one real class, the loop below already prefers the real one.
        //
        // AND IT DID NOT FIX missing_playerstate. classMask=31 was accepted and the spawn
        // still had no playerstate, so the class COUNT was never the cause -- the third
        // hypothesis about this failure to die on contact with the log, after "classMask=1
        // is refused" and "four weapon groups are two classes". Kept because every slot
        // resolving to the player's real weapons is right on its own terms, not because it
        // fixed anything. The open question is why a playerstate is not built for these
        // weapon ids when the 3.3.3.3 fixture's ids spawn on the same stack.
        const auto *source = stagedComplete[0] ? &staged[0] : nullptr;
        for (std::size_t classIndex = 0; classIndex < LoadoutRecordClasses; ++classIndex)
        {
            if (stagedComplete[classIndex])
                source = &staged[classIndex];
        }
        if (source)
        {
            for (auto &target : request.classes)
                target = *source;
        }
        for (std::size_t classIndex = 0; classIndex < LoadoutRecordClasses; ++classIndex)
        {
            if (stagedComplete[classIndex])
                request.classes[classIndex] = staged[classIndex];
        }

        if (!complete)
        {
            // SHOW THE BYTES. "it did not work" is not a measurement, and this failing
            // silently is what made the previous build look like it had not been deployed.
            // Dumping the head of the record separates "sub_7C5BA0 wrote nothing" from
            // "it wrote something and the offsets are wrong" -- two different bugs that
            // are indistinguishable from a bare false.
            static std::string LastRecordDump;
            std::string dump = "client loadout record REJECTED, words 0..31:";
            for (std::size_t index = 0; index < 32 && index < record.size(); ++index)
                dump += " " + std::to_string(record[index]);
            if (dump != LastRecordDump)
            {
                LastRecordDump = dump;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, dump);
            }
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::StagedSlot,
                std::memory_order_relaxed);
            return false;
        }

        std::string report = "client loadout record:";
        for (std::size_t classIndex = 0; classIndex < request.classes.size(); ++classIndex)
        {
            if (!request.classes[classIndex].weapons[0].itemId)
                continue;
            request.classMask |= static_cast<std::uint8_t>(1u << classIndex);
            report += " class" + std::to_string(classIndex) + " " +
                std::to_string(request.classes[classIndex].weapons[0].itemId) + "/" +
                std::to_string(request.classes[classIndex].weapons[1].itemId);
        }
        // NAME THE WEAPONS, not just their ids. `tmp_mp` only reached the log because
        // that weapon happened to FAIL its default-attachment read; a weapon that
        // resolves cleanly went unnamed, which is backwards -- the id alone cannot be
        // checked against a fastfile and a name can. This is the cheap half of the
        // question "is this weapon's asset even loaded for this map".
        for (std::size_t classIndex = 0; classIndex < request.classes.size(); ++classIndex)
        {
            if (!(request.classMask & (1u << classIndex)))
                continue;
            for (const auto &weapon : request.classes[classIndex].weapons)
            {
                const auto name = readItemInternalName(weapon.itemId);
                report += " [" + std::to_string(weapon.itemId) + "=" +
                    (name ? *name : std::string("<no internal name>")) + "]";
            }
            break;   // one class is enough; they are mirrors of each other
        }
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, report);
        return true;
    }

    bool EngineBindings::readStagedWeaponRequest(
        const std::uint32_t slotIndex,
        OlMod::DedicatedSession::WeaponRequest &request) const
    {
        if (!weaponSlotReadStaged_ || slotIndex >= 120)
            return false;

        std::array<std::uint32_t, 6> attachments{};
        std::uint32_t itemId{};
        const auto function = weaponSlotReadStaged_;
        auto *attachmentOutput = attachments.data();
        auto *itemOutput = &itemId;
        const auto nativeSlotIndex = slotIndex;
        __asm
        {
            mov eax, nativeSlotIndex
            mov edx, attachmentOutput
            push itemOutput
            call function
            add esp, 4
        }
        if (!itemId || itemId > 0xFFFF ||
            std::ranges::any_of(attachments, [](const auto attachmentItemId) {
                return attachmentItemId > 0xFFFF;
            }))
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::StagedSlot,
                std::memory_order_relaxed);
            return false;
        }

        request = {
            .itemId = itemId,
            .attachmentItemIds = attachments,
        };
        return true;
    }

    std::optional<ClientWeaponSelection> EngineBindings::resolveWeaponSelection(
        const OlMod::DedicatedSession::WeaponRequest &request) const
    {
        ClientWeaponSelection selection;
        if (!resolveWeaponRequest(request, selection))
            return std::nullopt;
        return selection;
    }

    bool EngineBindings::resolveWeaponRequest(
        const OlMod::DedicatedSession::WeaponRequest &request,
        ClientWeaponSelection &selection) const
    {
        if (!request.itemId || request.itemId > 0xFFFF)
            return false;
        selection = { .itemId = request.itemId };
        if (!resolveWeaponItem(
                request.itemId, request.attachmentItemIds, selection))
        {
            return false;
        }
        if (!readWeaponDefinition(selection.weaponAssetIndex, selection))
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::WeaponDefinition,
                std::memory_order_relaxed);
            return false;
        }
        selection.attachmentItemIds = request.attachmentItemIds;
        return true;
    }

    bool EngineBindings::readWeaponDefinition(
        const std::uint32_t weaponAssetIndex,
        ClientWeaponSelection &selection) const
    {
        if (!module_ || !weaponAssetIndex ||
            weaponAssetIndex > MaximumWeaponAssetIndex)
            return false;

        const auto *definitionSlot = module_ + WeaponDefinitionsRva +
            weaponAssetIndex * sizeof(void *);
        if (!readableSpan(definitionSlot, sizeof(void *)))
            return false;
        const auto *definition = *reinterpret_cast<std::uint8_t *const *>(
            definitionSlot);
        if (!readableSpan(
                definition,
                WeaponAmmoCountClipRelativeOffset + sizeof(std::uint8_t)))
        {
            return false;
        }

        // SECTION 190: WHAT ALT WEAPON DOES THIS WEAPON HAVE, AND DID IT LINK?
        //
        // out.exe's sub_42F060 is the linker and it is unambiguous: THREE
        // name -> index pairs on the weapon definition, each name resolved once
        // at load through BG_FindWeaponIndexForName (sub_42F2F0) and written
        // back as an index.
        //
        //     +3880 name -> +3892 index      (error "1222 %s %s" if unresolved)
        //     +3884 name -> +3896 index      (error "1223 %s %s")
        //     +3888 name -> +3900 index      (error "1223 %s %s")
        //
        // and +3900 is the one sub_426BC0 reads on the FIRE path, gated on the
        // byte flag at +3876.
        //
        // WHY THIS PROBE AND NOT A WIRE CHANGE. The first live run of the
        // section 190 probe said `lastWeaponAltModeSwitch` NEVER MOVES -- a
        // whole match of the player pressing alt-fire and not one edge. The
        // client only consults that field when a weapon-switch button is down
        // (sub_429E10), and it then indexes the weapon table with it, so a
        // weapon with no linked alt has nothing to name. Whether these three
        // fields are populated at all on the weapons we serve is the question
        // that decides the whole job, and it is a read, not a guess.
        //
        // ONCE PER WEAPON ASSET INDEX, on the loadout-resolution path. Nothing
        // here runs per frame -- section 188d.
        if (readableSpan(definition, 3904))
        {
            static std::mutex altLinkageMutex;
            static std::set<std::uint32_t> altLinkageSeen;
            auto report = false;
            {
                const std::lock_guard<std::mutex> guard(altLinkageMutex);
                report = altLinkageSeen.size() < 64 &&
                    altLinkageSeen.insert(weaponAssetIndex).second;
            }
            // AND SWEEP EVERY BASE WEAPON ONCE, because "the weapons in this
            // loadout have no alt" and "nothing in this build has an alt" are
            // different findings and the per-loadout probe cannot tell them
            // apart.
            //
            // THE FIRST SWEEP CORRECTED THIS FILE'S OWN READING, which is why
            // it was worth taking. +3880/+3884/+3888 are NOT an alt-weapon
            // link: all 57 definitions that carry them are the underbarrel
            // launchers `uni_gl_<host>_mp`, and the three names are
            // frag_grenade_mp / flash_grenade_mp / flash_grenade_mp (or
            // molotovcocktail_mp on the molotov variants). They are the
            // launcher's PROJECTILE types. sub_42FA00 was over-read.
            //
            // But the sweep found the real thing on the way past: an ALT
            // WEAPON IS AN ORDINARY BASE WEAPON ASSET, `uni_gl_famasss_mp` at
            // 1065 next to `famasss_mp`, one per host rifle, and it pairs with
            // an attachment we already resolve (`gre_unifamasss->188`).
            //
            // So sweep the field that DOES carry the relation. sub_42FA00 reads
            // a weapon name off definition+12 and inherits that weapon's whole
            // attachment table through mp/coAltWeaponAttachmentTable.csv --
            // source weapon +12, destination the weapon being iterated. On
            // `uni_gl_famasss_mp` that names `famasss_mp`, so +12 is THE HOST,
            // stored on the alt. Inverting this table gives host -> alt for
            // every weapon we serve, which is the table the fix needs.
            //
            // One pass, once per process, at loadout-resolution time.
            {
                static std::once_flag baseSweepOnce;
                std::call_once(baseSweepOnce, [&] {
                    std::uint32_t hosted{};
                    std::uint32_t readable{};
                    std::uint32_t printed{};
                    for (std::uint32_t index = 1;
                         index < BaseWeaponAssetCount; ++index)
                    {
                        const auto *const slot =
                            reinterpret_cast<const std::uint8_t *const *>(
                                module_ + WeaponDefinitionsRva) + index;
                        if (!readableSpan(slot, sizeof(*slot)) || !*slot)
                            continue;
                        const auto *const def = *slot;
                        if (!readableSpan(def, 3904))
                            continue;
                        ++readable;
                        const auto text = [&](const std::size_t offset) {
                            const auto value = readCString(
                                *reinterpret_cast<const char *const *>(
                                    def + offset),
                                128);
                            return value ? *value : std::string();
                        };
                        // FIVE NAME FIELDS, not one. sub_431490 (the engine's
                        // OWN modular-name builder) reads +3716 as the parent
                        // weapon's name, and sub_42F240 links +3736 -> +3740
                        // with its own error id ("1063 %s %s"). Print them
                        // together so one pass settles which field carries the
                        // alt relation instead of three cycles settling one
                        // each.
                        const auto host = text(12);
                        const auto parent = text(3716);
                        const auto linked = text(3736);
                        if (host.empty() && parent.empty() && linked.empty())
                            continue;
                        ++hosted;
                        if (printed < 200)
                        {
                            ++printed;
                            const auto self = readWeaponDefinitionName(index);
                            OlMod::RuntimeLog::write(
                                OlMod::RuntimeLog::Channel::GameServer,
                                "alt host link index=" +
                                    std::to_string(index) + " name=" +
                                    (self ? *self : std::string("?")) +
                                    " inv1436=" +
                        std::to_string(
                            *reinterpret_cast<const std::int32_t *>(
                                def + 1436)) +
                        " host=" + (host.empty() ? "-" : host) +
                                    " parent3716=" +
                                    (parent.empty() ? "-" : parent) +
                                    " link3736=" +
                                    (linked.empty() ? "-" : linked) + "->" +
                                    std::to_string(
                                        *reinterpret_cast<const std::uint32_t *>(
                                            def + 3740)) +
                                    " class=" +
                                    std::to_string(
                                        *reinterpret_cast<const std::int32_t *>(
                                            def + WeaponClassOffset)) +
                                    " type=" +
                                    std::to_string(
                                        *reinterpret_cast<const std::int32_t *>(
                                            def + WeaponTypeOffset)) +
                                    " fire=" +
                                    std::to_string(
                                        *reinterpret_cast<const std::int32_t *>(
                                            def + WeaponFireTypeOffset)) +
                                    " flag3876=" +
                                    std::to_string(
                                        static_cast<unsigned>(def[3876])));
                        }
                    }
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "alt host link SWEEP readable=" +
                            std::to_string(readable) + " hosted=" +
                            std::to_string(hosted) + " printed=" +
                            std::to_string(printed) + " of " +
                            std::to_string(BaseWeaponAssetCount) + " slots");
                });
            }
            if (report)
            {
                const auto linkName = [&](const std::size_t offset) {
                    const auto *const pointer =
                        *reinterpret_cast<const char *const *>(
                            definition + offset);
                    const auto text = readCString(pointer, 128);
                    return text && !text->empty() ? *text : std::string("-");
                };
                const auto linkIndex = [&](const std::size_t offset) {
                    return *reinterpret_cast<const std::uint32_t *>(
                        definition + offset);
                };
                const auto named = [&](const std::uint32_t index) {
                    if (!index)
                        return std::string("-");
                    const auto name = readWeaponDefinitionName(index);
                    return name ? *name : std::string("?");
                };
                // THE ALT WEAPON IS +3716 -> +3720, NOT +3880..+3900.
                //
                // sub_42EF60 is its linker and it is in the registration chain
                // sub_42F1E0 runs on EVERY weapon, modular ones included:
                //
                //     altName = def[+3716]
                //     def[+3720] = 0
                //     if (*altName) {
                //         index = def->name[0] == '*' ? sub_431490(self)
                //                                     : BG_FindWeaponIndex(altName)
                //         def[+3720] = index
                //     }
                //
                // and the live sweep found 46 host/alt pairs among the base
                // assets, bidirectional: the HOST carries +3716 naming the alt
                // (`g36css_mp` -> `altfireg36css_mp`), the ALT carries +12
                // naming the host. Two of them are in this player's own
                // loadout -- csg12ss_mp and g36css_mp.
                //
                // THE MODULAR BRANCH IS WHAT THIS PRINT IS FOR. When the name
                // starts with '*' the engine BUILDS the modular alt itself
                // through sub_431490 rather than looking one up, so a modular
                // weapon that inherits +3716 from its base should already have
                // an alt with no help from us. Whether ours does is the whole
                // remaining question, and it is one string and one index.
                const auto self = readWeaponDefinitionName(weaponAssetIndex);
                const auto altIndex = linkIndex(3720);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "weapon alt linkage index=" +
                        std::to_string(weaponAssetIndex) + " name=" +
                        (self ? *self : std::string("?")) +
                        " alt3716=" + linkName(3716) +
                        " altIndex3720=" + std::to_string(altIndex) +
                        "(" + named(altIndex) + ")" +
                        " host12=" + linkName(12) +
                        " inv1436=" +
                        std::to_string(
                            *reinterpret_cast<const std::int32_t *>(
                                definition + 1436)) +
                        " grenades=" + linkName(3880) + "," +
                        linkName(3884) + "," + linkName(3888) +
                        " flag3876=" +
                        std::to_string(static_cast<unsigned>(definition[3876])));
            }
        }

        const auto ammoIndex = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponAmmoIndexOffset);
        const auto clipIndex = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponClipIndexOffset);
        const auto clipSize = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponClipSizeOffset);
        const auto maxAmmoMultiplier = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponMaxAmmoOffset);
        const auto weaponType = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponTypeOffset);
        const auto weaponClass = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponClassOffset);
        const auto penetrateType = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponPenetrateTypeOffset);
        const auto impactType = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponImpactTypeOffset);
        const auto fireType = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponFireTypeOffset);
        const auto shotCount = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponShotCountOffset);
        const auto meleeDamage = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponMeleeDamageOffset);
        const auto fireDelay = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponFireDelayOffset);
        const auto dropTime = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponDropTimeOffset);
        const auto raiseTime = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponRaiseTimeOffset);
        const auto fireTime = *reinterpret_cast<const std::int32_t *>(
            definition + WeaponFireTimeOffset);
        const auto hipSpreadStandMin = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadStandMinOffset);
        const auto hipSpreadCrouchMin = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadCrouchMinOffset);
        const auto hipSpreadProneMin = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadProneMinOffset);
        const auto hipSpreadStandMax = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadStandMaxOffset);
        const auto hipSpreadCrouchMax = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadCrouchMaxOffset);
        const auto hipSpreadProneMax = *reinterpret_cast<const float *>(
            definition + WeaponHipSpreadProneMaxOffset);
        const auto adsSpread = *reinterpret_cast<const float *>(
            definition + WeaponAdsSpreadOffset);
        SvWeaponDamageCurve damageCurve{};
        for (std::size_t index = 0; index < damageCurve.damage.size(); ++index)
        {
            damageCurve.damage[index] =
                *reinterpret_cast<const std::int32_t *>(
                    definition + WeaponDamageOffset + index * sizeof(std::int32_t));
            damageCurve.ranges[index] = *reinterpret_cast<const float *>(
                definition + WeaponDamageRangeOffset + index * sizeof(float));
        }
        std::array<float, HitLocationCount> hitLocationMultipliers{};
        for (std::size_t index = 0;
            index < hitLocationMultipliers.size(); ++index)
        {
            hitLocationMultipliers[index] = *reinterpret_cast<const float *>(
                definition + WeaponHitLocationMultipliersOffset +
                index * sizeof(float));
        }
        // CODDIFF(1649370): the ammo and clip index bounds were 3.3.3.3's
        // ten-bit ones, 0x3FF and 0x3FE. Both fields are ELEVEN bits on this
        // build, and that is measured on the wire rather than inferred:
        // mining the playerstate trailing sections out of 6160/6160 real
        // retail snapshots gives ammo indexes up to 1188 and clip indexes up
        // to 1297, neither of which ten bits can express. With the old bounds
        // this check rejected any weapon whose ammo or clip index sat above
        // 1023 -- on a build with a 1300-entry base weapon table, most of
        // them -- so the loadout resolver failed here no matter how correct
        // the field offsets above it were. The clip bound stays one below the
        // index bound because all-ones is the absent-clip sentinel.
        // A WEAPON WITH NO CLIP IS LEGAL, AND THIS REJECTED ONE. The comment above names
        // all-ones as the absent-clip sentinel and the bound below is set one under it for
        // exactly that reason -- and then `clipIndex <= 0` threw out the sentinel itself,
        // which reads back as -1. raygun_mp is an energy weapon with no magazine:
        //
        //   weapon definition rejected index=1235 ammo=1203 clip=-1 clipSize=1 maxAmmo=1
        //     type=0 class=1 penetrate=0 impact=0 fire=1 shots=1 fireDelay=0 fireTime=250
        //     drop=250 raise=250 spreadStand=0.000/0.000 ads=0.000 curveOk=1
        //
        // Every other field is sane. Twenty-five conditions, one `return false`, and the
        // log line written to identify WHICH is what made this a one-line fix instead of
        // twenty-five re-derived offsets -- the reason that line prints them all.
        const bool absentClip = clipIndex == -1;
        if (ammoIndex <= 0 || ammoIndex > 0x7FF ||
            (!absentClip && (clipIndex <= 0 || clipIndex > 0x7FE)) ||
            clipSize <= 0 || clipSize > 0x1FF ||
            maxAmmoMultiplier <= 0 || weaponType < 0 ||
            weaponType > std::numeric_limits<std::uint8_t>::max() ||
            weaponClass < 0 ||
            weaponClass > std::numeric_limits<std::uint8_t>::max() ||
            penetrateType < 0 ||
            penetrateType > std::numeric_limits<std::uint8_t>::max() ||
            impactType < 0 ||
            impactType > std::numeric_limits<std::uint8_t>::max() ||
            fireType < 0 ||
            fireType > MaximumWeaponFireType || fireDelay < 0 ||
            shotCount < 0 ||
            shotCount > std::numeric_limits<std::uint8_t>::max() ||
            meleeDamage <= 0 ||
            meleeDamage > std::numeric_limits<std::uint16_t>::max() ||
            fireDelay > std::numeric_limits<std::int16_t>::max() ||
            dropTime < 0 || dropTime > std::numeric_limits<std::int16_t>::max() ||
            raiseTime < 0 || raiseTime > std::numeric_limits<std::int16_t>::max() ||
            fireTime <= 0 || fireTime > std::numeric_limits<std::int16_t>::max() ||
            !std::isfinite(hipSpreadStandMin) || hipSpreadStandMin < 0.0f ||
            !std::isfinite(hipSpreadCrouchMin) || hipSpreadCrouchMin < 0.0f ||
            !std::isfinite(hipSpreadProneMin) || hipSpreadProneMin < 0.0f ||
            !std::isfinite(hipSpreadStandMax) ||
            hipSpreadStandMax < hipSpreadStandMin ||
            !std::isfinite(hipSpreadCrouchMax) ||
            hipSpreadCrouchMax < hipSpreadCrouchMin ||
            !std::isfinite(hipSpreadProneMax) ||
            hipSpreadProneMax < hipSpreadProneMin ||
            !std::isfinite(adsSpread) || adsSpread < 0.0f ||
            !SV_IsWeaponDamageCurveValid(damageCurve) ||
            std::ranges::any_of(
                hitLocationMultipliers,
                [](const float multiplier) {
                    return !std::isfinite(multiplier) || multiplier < 0.0f ||
                        multiplier > 20.0f;
                }))
        {
            // TWENTY-FIVE OFFSETS, ONE `return false`. Every one of them is a
            // WeaponDef field position carried over from 3.3.3.3, and this
            // check reads all of them before rejecting - so the values it read
            // say which offsets moved, and the ones that look sane say which
            // did not. Reading them out of the log beats re-deriving all
            // twenty-five from out.exe when most are probably still right.
            char fields[416]{};
            std::snprintf(
                fields, sizeof(fields),
                "weapon definition rejected index=%u ammo=%d clip=%d clipSize=%d "
                "maxAmmo=%d type=%d class=%d penetrate=%d impact=%d fire=%d "
                "shots=%d melee=%d fireDelay=%d fireTime=%d drop=%d raise=%d "
                "spreadStand=%.3f/%.3f ads=%.3f curveOk=%u",
                weaponAssetIndex, ammoIndex, clipIndex, clipSize,
                maxAmmoMultiplier, weaponType, weaponClass, penetrateType,
                impactType, fireType, shotCount, meleeDamage, fireDelay,
                fireTime, dropTime, raiseTime, hipSpreadStandMin,
                hipSpreadStandMax, adsSpread,
                SV_IsWeaponDamageCurveValid(damageCurve) ? 1u : 0u);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, fields);
            return false;
        }

        auto maxAmmo = static_cast<std::uint64_t>(maxAmmoMultiplier);
        if (definition[WeaponAmmoCountClipRelativeOffset])
            maxAmmo *= static_cast<std::uint32_t>(clipSize);
        if (maxAmmo > 0x7FF)
        {
            // A `return false` with no line is the failure mode this phase is
            // about: the caller reports `weapon_definition` and nothing says
            // WHICH of the twenty-five reads disagreed. 0x7FF is a wire width,
            // and a wire width from the other build is exactly what section 32f
            // caught in the weapon index bound.
            char capped[192]{};
            std::snprintf(
                capped, sizeof(capped),
                "weapon definition max ammo out of range index=%u maxAmmo=%llu "
                "multiplier=%d clipSize=%d clipRelative=%u",
                weaponAssetIndex, static_cast<unsigned long long>(maxAmmo),
                maxAmmoMultiplier, clipSize,
                static_cast<unsigned>(
                    definition[WeaponAmmoCountClipRelativeOffset]));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, capped);
            return false;
        }

        selection.ammoIndex = static_cast<std::uint32_t>(ammoIndex);
        selection.clipIndex = clipIndex;
        selection.clipSize = static_cast<std::uint32_t>(clipSize);
        selection.maxAmmo = static_cast<std::uint32_t>(maxAmmo);
        selection.weaponType = static_cast<std::uint32_t>(weaponType);
        selection.weaponClass = static_cast<std::uint32_t>(weaponClass);
        selection.penetrateType = static_cast<std::uint32_t>(penetrateType);
        selection.impactType = static_cast<std::uint32_t>(impactType);
        selection.fireType = static_cast<std::uint32_t>(fireType);
        selection.shotCount = static_cast<std::uint32_t>(shotCount);
        selection.meleeDamage = static_cast<std::uint32_t>(meleeDamage);
        selection.fireDelayMilliseconds = static_cast<std::uint32_t>(fireDelay);
        selection.fireTimeMilliseconds = static_cast<std::uint32_t>(fireTime);
        selection.dropTimeMilliseconds = static_cast<std::uint32_t>(dropTime);
        selection.raiseTimeMilliseconds = static_cast<std::uint32_t>(raiseTime);
        selection.hipSpreadStandMin = hipSpreadStandMin;
        selection.hipSpreadCrouchMin = hipSpreadCrouchMin;
        selection.hipSpreadProneMin = hipSpreadProneMin;
        selection.hipSpreadStandMax = hipSpreadStandMax;
        selection.hipSpreadCrouchMax = hipSpreadCrouchMax;
        selection.hipSpreadProneMax = hipSpreadProneMax;
        selection.adsSpread = adsSpread;
        selection.damageCurve = damageCurve;
        selection.hitLocationMultipliers = hitLocationMultipliers;
        selection.aimDownSight = definition[WeaponAimDownSightOffset] != 0;
        selection.hasOverlayReticle =
            *reinterpret_cast<const std::int32_t *>(
                definition + WeaponOverlayReticleOffset) != 0;
        selection.rifleBullet = definition[WeaponRifleBulletOffset] != 0;
        selection.bulletExplosiveDamage =
            definition[WeaponBulletExplosiveDamageOffset] != 0;
        selection.dualWieldCapable =
            definition[WeaponDualWieldCapableOffset] != 0;
        return true;
    }

    const std::uint8_t *EngineBindings::readItemDefinition(
        const std::uint32_t itemId) const
    {
        if (!module_ || !itemId || itemId > 0xFFFF)
            return nullptr;

        const auto *definitionSlot = module_ + ItemDefinitionsRva;
        const auto *definitionCountSlot = module_ + ItemDefinitionCountRva;
        const auto *lookupSlot = module_ + ItemLookupRva;
        const auto *lookupCountSlot = module_ + ItemLookupCountRva;
        const auto *bucketOffsets = module_ + ItemBucketOffsetsRva;
        if (!readableSpan(definitionSlot, sizeof(void *)) ||
            !readableSpan(definitionCountSlot, sizeof(std::uint32_t)) ||
            !readableSpan(lookupSlot, sizeof(void *)) ||
            !readableSpan(lookupCountSlot, sizeof(std::uint32_t)))
        {
            return nullptr;
        }

        const auto *definitions = *reinterpret_cast<std::uint8_t *const *>(definitionSlot);
        const auto definitionCount = *reinterpret_cast<const std::uint32_t *>(
            definitionCountSlot);
        const auto *lookup = *reinterpret_cast<std::uint16_t *const *>(lookupSlot);
        const auto lookupCount = *reinterpret_cast<const std::uint32_t *>(lookupCountSlot);
        const auto bucket = itemId / 1000;
        if (!definitions || !lookup || !definitionCount || !lookupCount ||
            !readableSpan(bucketOffsets + bucket * sizeof(std::uint16_t), sizeof(std::uint16_t)))
        {
            return nullptr;
        }

        const auto lookupIndex = itemId % 1000 +
            *reinterpret_cast<const std::uint16_t *>(
                bucketOffsets + bucket * sizeof(std::uint16_t));
        if (lookupIndex >= lookupCount ||
            !readableSpan(lookup + lookupIndex, sizeof(std::uint16_t)))
        {
            return nullptr;
        }
        const auto definitionIndex = lookup[lookupIndex];
        if (!definitionIndex || definitionIndex >= definitionCount)
            return nullptr;

        const auto *definition = definitions + definitionIndex * ItemDefinitionSize;
        if (!readableSpan(definition, ItemDefinitionSize))
            return nullptr;
        return definition;
    }

    bool EngineBindings::characterOptionSelectionMask(
        const std::uint16_t characterItemId,
        const std::span<const std::uint16_t> equippedItemIds,
        std::array<std::uint32_t, 12> &mask,
        std::string *const witness) const
    {
        mask = {};
        if (witness)
            witness->clear();
        if (!module_ || !characterItemId)
            return false;

        // THE CHARACTER DEFINITION, by the same two steps sub_80E600 opens with:
        // the item registry gives a definition whose type byte at +5 must be 2, and
        // its u16 at +2 indexes CharacterItemDefinitionTable at stride 52.
        const auto *const characterItem = readItemDefinition(characterItemId);
        if (!characterItem || characterItem[5] != 2)
            return false;
        const auto *const tableSlot = module_ + CharacterItemDefinitionTableRva;
        const auto *const countSlot = module_ + CharacterItemDefinitionCountRva;
        if (!readableSpan(tableSlot, sizeof(const std::uint8_t *)) ||
            !readableSpan(countSlot, sizeof(std::uint32_t)))
        {
            return false;
        }
        const auto *const definitions =
            *reinterpret_cast<std::uint8_t *const *>(tableSlot);
        const auto definitionCount =
            *reinterpret_cast<const std::uint32_t *>(countSlot);
        const auto definitionIndex =
            *reinterpret_cast<const std::uint16_t *>(characterItem + 2);
        if (!definitions || definitionIndex >= definitionCount)
            return false;
        const auto *const definition =
            definitions + definitionIndex * CharacterItemDefinitionSize;
        if (!readableSpan(definition, CharacterItemDefinitionSize))
            return false;

        // charDef+36 IS THE OPTION COUNT AND charDef+40 THE OPTION LIST. Both live
        // inside the 52-byte definition this file already reads for `female` and the
        // colour selector, so no new stride or table is being guessed here.
        const auto optionCount =
            *reinterpret_cast<const std::uint32_t *>(definition + 36);
        const auto *const options =
            *reinterpret_cast<std::uint16_t *const *>(definition + 40);
        if (!optionCount || !options ||
            !readableSpan(reinterpret_cast<const std::uint8_t *>(options),
                optionCount * sizeof(std::uint16_t)))
        {
            return false;
        }

        // A BOUND, NOT A CHECK, IF IT WERE SILENT. Twelve dwords address 384 options
        // and no more; a character with a longer list can still be dressed in anything
        // inside the first 384, and the witness says so rather than the count being
        // quietly clamped. The engine reads the same twelve dwords, so this is its
        // limit too, not ours.
        constexpr std::uint32_t MaskBitCount = 384;
        const auto addressable = std::min<std::uint32_t>(optionCount, MaskBitCount);

        std::string matched;
        std::string unmatched;
        std::size_t selected = 0;
        for (const auto itemId : equippedItemIds)
        {
            if (!itemId || itemId == characterItemId)
                continue;
            std::uint32_t index = addressable;
            for (std::uint32_t candidate = 0; candidate != addressable; ++candidate)
            {
                if (options[candidate] == itemId)
                {
                    index = candidate;
                    break;
                }
            }
            if (index == addressable)
            {
                // NOT IN THE LIST, SO NO BIT. Setting a bit for an id the option list
                // does not hold would select whatever option happens to sit at that
                // index -- which is exactly the failure section 182 measured when the
                // raw item ids were sent as the mask and the client drew pieces
                // unrelated to the loadout.
                unmatched += " " + std::to_string(itemId);
                continue;
            }
            mask[index / 32] |= std::uint32_t{ 1 } << (index % 32);
            // NAME IT. sub_80E600 classifies each selected option into one of twelve
            // slots by its resolved model NAME, and OVERWRITES -- ascending option
            // index, last writer wins. So two pieces whose names classify the same way
            // silently collide and the higher index is what the player sees. Numbers
            // cannot show that; names can.
            const auto name = readItemInternalName(itemId);
            matched += " " + std::to_string(itemId) + "@" + std::to_string(index) +
                (name ? "(" + *name + ")" : "(unnamed)");
            ++selected;
        }

        if (witness)
        {
            *witness = "character option mask character=" +
                std::to_string(characterItemId) + " options=" +
                std::to_string(optionCount) +
                (optionCount > MaskBitCount
                    ? " (ONLY THE FIRST 384 ARE ADDRESSABLE)"
                    : "") +
                " selected=" + std::to_string(selected) +
                " bits=" + (matched.empty() ? " none" : matched) +
                " NOT AN OPTION FOR THIS CHARACTER=" +
                (unmatched.empty() ? " none" : unmatched);
            // AND WHEN NOTHING MATCHED, SAY WHAT THE LIST ACTUALLY HOLDS. A line that
            // only reports "your ids are not in it" costs a whole second cycle to ask
            // the obvious follow-up; this one answers "then what IS in it" the first
            // time. Section 183g: ask what the instrument would have printed had
            // something been there.
            if (!selected)
            {
                *witness += " -- THE LIST STARTS";
                for (std::uint32_t index = 0;
                    index != std::min<std::uint32_t>(addressable, 16); ++index)
                {
                    *witness += " " + std::to_string(options[index]);
                }
                if (addressable > 16)
                    *witness += " ...";
            }
        }
        return true;
    }

    void EngineBindings::placeCharacterItemsByRecordEntry(
        const std::span<const std::uint32_t> profileSlots,
        std::array<std::uint32_t,
            OlMod::DedicatedSession::CharacterItemCount> &record) const
    {
        // The placement rule itself lives in sv_snapshot_mp.hpp so it can be tested
        // without an engine; this side supplies the one thing only a live process has,
        // which is the item table.
        static_assert(OlMod::DedicatedSession::CharacterItemCount ==
            SvCharacterRecordEntryCount,
            "the session record and the character record must be the same twelve "
            "entries, or an outfit lands in the wrong slot");
        SV_PlaceCharacterItemsByRecordEntry(
            profileSlots,
            [this](const std::uint32_t itemId) {
                return characterItemRecordEntry(itemId);
            },
            record);
    }

    std::optional<std::uint32_t> EngineBindings::characterItemRecordEntry(
        const std::uint32_t itemId) const
    {
        // WHICH RECORD ENTRY THIS ITEM OCCUPIES, or nullopt if it is not part of a
        // character at all. Silence is the right answer for a weapon or an emblem: the
        // caller is placing a character record and must not guess an entry for an item
        // the engine would never put in one.
        const auto *definition = readItemDefinition(itemId);
        if (!definition)
            return std::nullopt;
        const auto flags = *reinterpret_cast<const std::uint16_t *>(
            definition + ItemDefinitionFlagsOffset);
        const auto recordEntry = *reinterpret_cast<const std::uint16_t *>(
            definition + ItemDefinitionRecordEntryOffset);
        switch (static_cast<std::uint16_t>(flags >> 8))
        {
        case ItemCategoryCharacter:
            // A character IS entry 0, whatever its own recordEntry field says.
            return 0u;
        case ItemCategoryCharacterPiece:
            // Entry 0 is reserved for the character, so a piece claiming it is a
            // misread rather than a piece; refuse instead of overwriting the character.
            if (!recordEntry ||
                recordEntry >= OlMod::DedicatedSession::CharacterItemCount)
            {
                return std::nullopt;
            }
            return recordEntry;
        default:
            return std::nullopt;
        }
    }

    std::optional<std::string> EngineBindings::readItemInternalName(
        const std::uint32_t itemId) const
    {
        const auto *definition = readItemDefinition(itemId);
        if (!definition)
            return std::nullopt;
        const auto *name = *reinterpret_cast<const char *const *>(
            definition + ItemDefinitionNameOffset);
        const auto internalName = readCString(name, 128);
        if (!internalName || !validBookingName(*internalName))
            return std::nullopt;

        return internalName;
    }

    namespace
    {
        // THE __try MUST LIVE SOMEWHERE WITHOUT DESTRUCTORS (C2712), and the register
        // arguments mean inline asm rather than a function pointer: sub_5E3760 is
        // __usercall with the item in EAX and the out-record in EDI, which no C++ calling
        // convention expresses.
        //
        // Guarded because a wrong RVA here does not return a wrong answer, it executes
        // whatever bytes are at that address. A fault must be reported as "the probe is
        // broken", never mistaken for "the item is not owned".
        __declspec(noinline) bool invokeOwnershipResolver(
            const void *const function,
            const int itemId,
            void *const destination,
            int &returned)
        {
            int value = 0;
            __try
            {
                __asm
                {
                    pushad
                    mov  eax, itemId
                    mov  edi, destination
                    call function
                    mov  value, eax
                    popad
                }
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
            returned = value;
            return true;
        }
    }

    namespace
    {
        // BESIDE THE RUNTIME LOG, NOT BESIDE THE WORKING DIRECTORY.
        //
        // weapon-slots.csv was opened on the relative path "Ayria\Logs\...", which works
        // from the CLIENT (its working directory is the game folder) and silently does
        // nothing from the DEDICATED, whose is not. The audit ran, reported its counts,
        // wrote no file, and said nothing about it -- `if (stream)` swallowed the failure.
        // RuntimeLog already solves this by deriving the path from the executable.
        std::filesystem::path diagnosticPath(const wchar_t *const fileName)
        {
            std::wstring buffer(MAX_PATH, L'\0');
            const auto size = GetModuleFileNameW(
                nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
            if (!size)
                return {};
            buffer.resize(size);
            return std::filesystem::path(buffer).parent_path() /
                L"Ayria" / L"Logs" / fileName;
        }
    }

    // EVERY ITEM ID TO ITS NAME, ONCE, TO A FILE.
    //
    // Written to a CSV rather than the runtime log because it is 20,000-odd lines: a log
    // is for events, and burying a cycle's real events under a data dump would make the
    // next problem harder to see, not easier.
    //
    // The range is the catalogue's own: ids 100..60348 per re/demo-re/marketplace/items.csv.
    // Ids that resolve to nothing are skipped rather than written as blanks, so the file's
    // line count IS the number of items this client can name.
    void EngineBindings::auditItemNames() const
    {
        if (!module_ || !dbFindXAssetHeader_)
            return;
        if (OlMod::processRole() == OlMod::ProcessRole::Dedicated)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "item name sweep: skipped in the dedicated -- the item tables it needs "
                "belong to the client");
            return;
        }

        const auto path = diagnosticPath(L"item-names.csv");
        std::ofstream out(path, std::ios::trunc);
        if (!out)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "item name sweep: cannot write " + path.string());
            return;
        }
        out << "itemId,name\n";

        std::uint32_t named = 0;
        for (std::uint32_t itemId = 100; itemId <= 60348; ++itemId)
        {
            const auto name = readItemInternalName(itemId);
            if (!name || name->empty())
                continue;
            out << itemId << ',' << *name << '\n';
            ++named;
        }
        out.close();

        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "item name sweep: " + std::to_string(named) +
                " of 60249 ids resolve to a name -> " + path.string() +
                " (the extracted marketplace tables name only 905)");
    }

    // ASK THE RESOLVER, DO NOT REASON ABOUT IT.
    //
    // Everything else here is inference from a decompilation: sub_5E3760's branches say
    // that a forced sub_5E3550 makes any non-excluded item report owned. That is a
    // HYPOTHESIS about control flow, and this project's own rule is that a decompiled
    // constant is a hypothesis -- a decompiled BRANCH is no better.
    //
    // So call it. The ids probed are chosen to be undeniable: they sit past position
    // 10,000 in the grant list, and only the first ~8,460 records fit in the client's
    // receive buffer, so the inventory hash CANNOT hold them. If they report owned, the
    // only thing that can have said so is the patch.
    //
    // `melhammer_mp` and `molotovcocktail_mp` are named, equippable and visible in a
    // loadout, so the log can be checked against the game rather than only against itself.
    //
    // TWO NATIVE CALLS, not 21,753: enough to decide the question, few enough not to be
    // the per-frame client call this project forbids.
    void EngineBindings::probeOwnership() const
    {
        if (!module_)
            return;

        // THE PATCH IS IN THE CLIENT; THIS MUST NOT RUN IN THE DEDICATED.
        //
        // The first run of this probe reported all four items NOT owned -- including item
        // 686, the character the player was wearing at that moment. The control caught it:
        // the patch logs under [client/game-server] and the probe logged under
        // [dedicated/game-server]. Two processes, both out.exe. The dedicated has no
        // logged-in player and no inventory, so "not owned" is the CORRECT answer there
        // and says nothing whatever about the client.
        //
        // Without the 686 control that would have read as "the patch does not work", and
        // the next hours would have gone into a patch that was fine.
        if (OlMod::processRole() == OlMod::ProcessRole::Dedicated)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ownership probe: skipped -- this is the DEDICATED process and the patch "
                "is applied in the CLIENT; an answer from here would mean nothing");
            return;
        }
        const auto *const resolver = module_ + OwnershipResolverRva;
        if (!readableSpan(resolver, 16))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ownership probe: the resolver is not readable at its RVA -- nothing "
                "below would mean anything");
            return;
        }

        struct Probe { std::uint32_t itemId; const char *name; const char *why; };
        static constexpr std::array<Probe, 7> Probes{ {
            { 686, "cha_COWprestigeA", "the character worn now -- owned either way, so a "
                                       "NO here means the probe itself is wrong" },
            { 14368, "melhammer_mp", "grant position 10630, far past the wire's 8460" },
            { 14386, "molotovcocktail_mp", "grant position 10666, far past the wire's 8460" },
            { 24308, "muz_slnc45smgveprlaborday", "grant position 10479, likewise" },
            // NEVER SOLD -- no sku maps to these, so no purchase could ever have granted
            // them and they cannot be in the inventory by any legitimate route. 1,675 of
            // the catalogue's 21,740 are like this. If they report owned, the patch does
            // not care whether an item was ever purchasable.
            { 11281, "scope_med", "NEVER SOLD -- no sku grants it" },
            { 17097, "shotgun_fn2000", "NEVER SOLD -- no sku grants it" },
            { 10435, "cam_kawaiirsrt3", "NEVER SOLD -- no sku grants it" },
        } };

        for (const auto &[itemId, name, why] : Probes)
        {
            // The resolver writes up to +44; give it far more than it can need.
            std::array<std::uint32_t, 32> record{};
            int returned = 0;
            if (!invokeOwnershipResolver(
                    resolver, static_cast<int>(itemId), record.data(), returned))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("ownership probe: FAULTED calling the resolver for ") +
                        name + " -- the RVA or the calling convention is wrong, and "
                        "nothing else here means anything");
                return;
            }

            const auto owned = *reinterpret_cast<const std::uint16_t *>(
                reinterpret_cast<const std::uint8_t *>(record.data()) + 4);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ownership probe: item " + std::to_string(itemId) + " " + name + " -> " +
                    (owned ? "OWNED" : "NOT owned") + " (returned " +
                    std::to_string(returned) + ", quantity " +
                    std::to_string(static_cast<std::int32_t>(record[2])) + ") -- " + why);
        }
    }

    // DOES "OWN EVERYTHING" ACTUALLY MEAN EVERYTHING?
    //
    // installUnlockAllPatch forces sub_5E3550 to return true, which makes sub_5E3760 --
    // the ownership resolver behind 94 call sites -- report any item the inventory hash
    // does not hold as owned with quantity -1. But it checks an EXCLUSION LIST first, and
    // the patch deliberately does not touch that path. So the honest statement is
    // "everything except that list", and this reads the list rather than assuming it is
    // empty.
    //
    // A PURE MEMORY READ ON PURPOSE. Calling the resolver 21,753 times to count the
    // answers would be the direct measurement, but it means invoking client UI code from
    // the bridge thread -- and this project already has a rule against per-frame client
    // calls it cannot vouch for. The list IS the answer: with the patch in, owned ==
    // not-excluded, so counting the exclusions counts the exceptions exactly.
    //
    // It reads LATE rather than at patch time: sub_5DE440 fills the list from a
    // comma-separated string at runtime, so a read during startup would report an empty
    // list whether or not one arrives later.
    void EngineBindings::reportUnlockAllCoverage() const
    {
        if (!module_)
            return;

        const auto *const countAt = module_ + ExcludedItemsCountRva;
        if (!readableSpan(countAt, sizeof(std::uint32_t)))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "unlock-all coverage: the exclusion count is not readable -- cannot say "
                "whether every item is owned");
            return;
        }
        const auto excluded = *reinterpret_cast<const std::uint32_t *>(countAt);

        if (!excluded)
        {
            // AN EMPTY LIST AND A WRONG ADDRESS READ THE SAME. This said "EMPTY, this is
            // all of them" and called it proof, and a zero from any unrelated page would
            // have said exactly that -- the guard below only catches an implausibly LARGE
            // count. So do not conclude from the zero: ASK THE RESOLVER.
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "unlock-all coverage: the exclusion count reads 0 -- which is what a WRONG "
                "RVA also reads, so it proves nothing on its own; the probe below is the "
                "measurement");
            probeOwnership();
            return;
        }

        // A list this long is not a blocklist, it is a bad pointer or a bad RVA. Say so
        // rather than printing thousands of lines of nonsense.
        if (excluded > 4096)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "unlock-all coverage: the exclusion count reads " +
                    std::to_string(excluded) + ", which is not a plausible blocklist -- "
                    "treat the RVA as wrong rather than the list as real");
            return;
        }

        std::string listing = "unlock-all coverage: " + std::to_string(excluded) +
            " item(s) are EXCLUDED and stay unowned:";
        const auto *const arrayAt = module_ + ExcludedItemsArrayRva;
        if (readableSpan(arrayAt, sizeof(std::uint32_t)))
        {
            const auto *const items =
                *reinterpret_cast<const std::uint32_t *const *>(arrayAt);
            if (readableSpan(items, excluded * sizeof(std::uint32_t)))
            {
                for (std::uint32_t entry = 0; entry < excluded; ++entry)
                    listing += " " + std::to_string(items[entry]);
            }
            else
            {
                listing += " (the list itself is not readable)";
            }
        }
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, listing);
        probeOwnership();
    }

    // THE WHOLE WEAPON TABLE, IN ONE PASS, WITHOUT ANYBODY EQUIPPING ANYTHING.
    //
    // The offline copy of this table cannot answer this: codol_stringtable_extract.py
    // resolves 57% of its string-pool back-references and prints another weapon's text for
    // the rest -- the type95techslime row comes out carrying SF_WEAPON_AA12GATOR_MP_DESC.
    // The loaded table is the only trustworthy copy, and the server already has it.
    void EngineBindings::auditRewardTable() const
    {
        // Checkpoint 70: runtime ID/name/cost/icon/alternate cost are columns
        // 0/1/4/15/40. Preserve every column, including any header rows.
        const auto log = [](const std::string &message) {
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "reward table audit: " + message);
        };
        const auto *table = readStringTable(dbFindXAssetHeader_, dbIsXAssetDefault_,
            "mp/coKillstreakStatsTable.csv", 41);
        if (!table)
        {
            log("table unavailable or invalid");
            return;
        }
        const auto fileName = L"reward-table-" + std::to_wstring(GetCurrentProcessId()) + L".csv";
        std::ofstream output(diagnosticPath(fileName.c_str()), std::ios::trunc);
        if (!output)
        {
            log("cannot open output");
            return;
        }
        std::size_t unreadable = 0;
        for (std::int32_t r = 0; r < table->rowCount; ++r)
        {
            for (std::int32_t c = 0; c < table->columnCount; ++c)
            {
                if (c) output << ',';
                const auto cell = readStringTableCell(
                    table->values[static_cast<std::size_t>(r) * table->columnCount + c]);
                if (!cell) ++unreadable;
                output << '"';
                for (const char ch : cell.value_or("<UNREADABLE>"))
                {
                    if (ch == '"') output << '"';
                    output << ch;
                }
                output << '"';
            }
            output << '\n';
        }
        output.flush();
        log(std::to_string(table->rowCount) + " rows, " +
            std::to_string(table->columnCount) + " columns, " +
            std::to_string(unreadable) + " unreadable cells; output=" +
            (output ? "complete" : "WRITE FAILED"));
    }

    std::optional<SvRewardWeapon> EngineBindings::resolveUavWeapon() const
    {
        if (!module_ || !weaponLookup_) return std::nullopt;
        // CODREF(1649370): loaded coKillstreakStatsTable row uav, column13.
        // Index1188 in the retail demo is load-order evidence, not an ABI.
        constexpr auto name = "killstreak_uav_mp";
        const auto index = weaponLookup_(name);
        if (!index || index > MaximumWeaponAssetIndex) return std::nullopt;
        const auto actualName = readWeaponDefinitionName(index);
        if (!actualName || *actualName != name) return std::nullopt;
        const auto *address = module_ + WeaponDefinitionsRva + index * sizeof(void *);
        if (!readableSpan(address, sizeof(void *))) return std::nullopt;
        const auto *definition = *reinterpret_cast<const std::uint8_t *const *>(address);
        if (!readableSpan(definition, WeaponAimDownSightOffset + 1)) return std::nullopt;
        const auto ammo = *reinterpret_cast<const std::int32_t *>(definition + WeaponAmmoIndexOffset);
        const auto clip = *reinterpret_cast<const std::int32_t *>(definition + WeaponClipIndexOffset);
        const auto capacity = *reinterpret_cast<const std::int32_t *>(definition + WeaponClipSizeOffset);
        if (ammo <= 0 || ammo > 2047 || clip <= 0 || clip > 2046 ||
            capacity <= 0 || capacity > 511) return std::nullopt;
        return SvRewardWeapon{static_cast<std::uint16_t>(index),
            static_cast<std::uint16_t>(ammo), static_cast<std::uint16_t>(clip),
            static_cast<std::uint16_t>(capacity),
            definition[WeaponAimDownSightOffset] != 0,
             *reinterpret_cast<const std::int32_t *>(definition + WeaponOverlayReticleOffset) != 0};
    }

    std::optional<std::uint16_t> EngineBindings::resolveBaseWeaponAssetIndex(
        const std::string_view weaponName) const
    {
        if (!module_ || !weaponLookup_ || weaponName.empty())
            return std::nullopt;
        const std::string ownedName(weaponName);
        const auto index = weaponLookup_(ownedName.c_str());
        if (!index || index >= BaseWeaponAssetCount)
            return std::nullopt;
        const auto actualName = readWeaponDefinitionName(index);
        if (!actualName || *actualName != weaponName)
            return std::nullopt;
        return static_cast<std::uint16_t>(index);
    }

    std::optional<SvResolvedRewards> EngineBindings::resolveSessionRewards(
        const OlMod::DedicatedSession::LoadoutRequest &request) const
    {
        if (!OlMod::DedicatedSession::valid(request)) return std::nullopt;
        const auto *table = readStringTable(dbFindXAssetHeader_, dbIsXAssetDefault_,
            "mp/coKillstreakStatsTable.csv", 41);
        auto resolved = SV_ResolveProfileRewards(request.rewardItemIds,
            [&](std::uint32_t catalogId) -> std::optional<SvRewardDefinition> {
                if (!table) return std::nullopt;
                const auto name = readItemInternalName(catalogId);
                if (!name) return std::nullopt;
                for (std::int32_t r = 0; r < table->rowCount; ++r)
                {
                    const auto *row = table->values +
                        static_cast<std::size_t>(r) * table->columnCount;
                    const auto rowName = readStringTableCell(row[1]);
                    if (!rowName || *rowName != *name) continue;
                    SvRewardDefinition result;
                    const auto read = [&](std::int32_t column, std::uint32_t &value) {
                        const auto text = readStringTableCell(row[column]);
                        if (!text || text->empty()) return false;
                        const auto parsed = std::from_chars(text->data(),
                            text->data() + text->size(), value);
                        return parsed.ec == std::errc{} &&
                            parsed.ptr == text->data() + text->size();
                    };
                    if (!read(0, result.runtimeId) || !read(4, result.normalCost) ||
                        !read(40, result.persistentCost)) return std::nullopt;
                    return result;
                }
                return std::nullopt;
            });
        if (!resolved || !request.characterItemIds[0] ||
            std::ranges::all_of(resolved->definitions, [](const auto &reward) {
                return reward.runtimeId == 0;
            })) return resolved;
        // Native 7DD7B0 -> 7DD6D0: selected character catalog name, then
        // property columns 2,8,14,...; property presence selects column 40.
        // characterItemIds is the twelve-entry outfit record, NOT an array
        // indexed by characterIndex. Entry zero is already a catalog ID.
        const auto characterName = readItemInternalName(request.characterItemIds[0]);
        const auto *characters = readStringTable(dbFindXAssetHeader_, dbIsXAssetDefault_,
            "mp/coCharItemStatsTable.csv", 3);
        if (!characterName || !characters) return std::nullopt;
        for (std::int32_t r = 0; r < characters->rowCount; ++r)
        {
            const auto *row = characters->values +
                static_cast<std::size_t>(r) * characters->columnCount;
            const auto name = readStringTableCell(row[0]);
            if (!name || *name != *characterName) continue;
            for (std::int32_t c = 2; c < characters->columnCount; c += 6)
            {
                const auto property = readStringTableCell(row[c]);
                if (!property) return std::nullopt;
                if (property->empty()) break;
                if (*property == "modPersistKillstreak")
                {
                    resolved->persistentCosts = true;
                    break;
                }
            }
            break;
        }
        return resolved;
    }

    void EngineBindings::auditWeaponItemsTable() const
    {
        if (!dbFindXAssetHeader_)
            return;
        const auto *table = readStringTable(
            dbFindXAssetHeader_, dbIsXAssetDefault_, WeaponItemsTableName, 40);
        if (!table)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "weapon table audit: the weapon items table is not loaded");
            return;
        }

        const auto show = [](const std::string &value) {
            std::string shown;
            for (const auto character : value)
            {
                shown += (character >= 32 && character < 127)
                    ? std::string(1, character)
                    : "<" + std::to_string(static_cast<unsigned char>(character)) + ">";
            }
            return shown;
        };

        std::int32_t refused = 0;
        std::int32_t blank = 0;
        std::int32_t audited = 0;
        // HOW MANY WEAPONS OF EACH SLOT THE GAME ACTUALLY HAS. The player counted 647
        // primaries in his inventory and the table has 838 rows -- but a row is any
        // weapon, including secondaries, launchers and melee, so 647 may be complete or
        // may be 191 short and nothing offline can say which. Column 4 classifies the
        // row (SF_WEAPON_PRIMARY / SF_WEAPON_SECONDARY / ...), and the OFFLINE copy of
        // this table cannot be used for it: the extractor resolved 2 of 838 of those
        // cells, the rest being string-pool back-references it dropped. Here they read.
        std::map<std::string, std::int32_t> slots;
        constexpr std::size_t WeaponItemsSlotColumn = 4;
        for (std::int32_t rowIndex = 0; rowIndex < table->rowCount; ++rowIndex)
        {
            const auto *row = table->values +
                static_cast<std::size_t>(rowIndex) * table->columnCount;
            const auto weaponName = readStringTableCell(row[0]);
            if (!weaponName || weaponName->empty())
                continue;
            ++audited;

            if (static_cast<std::int32_t>(WeaponItemsSlotColumn) < table->columnCount)
            {
                const auto slot = readStringTableCell(row[WeaponItemsSlotColumn]);
                ++slots[slot && !slot->empty() ? *slot : std::string("<blank>")];
            }

            for (std::size_t triple = 0; triple < WeaponItemsSlotTripleCount; ++triple)
            {
                const auto column = WeaponItemsFirstSlotColumn + triple * 3;
                if (static_cast<std::int32_t>(column + 2) >= table->columnCount)
                    break;
                const auto slotName = readStringTableCell(row[column]);
                const auto defaultName = readStringTableCell(row[column + 1]);
                const auto enabled = readStringTableCell(row[column + 2]);
                if (!slotName || !defaultName || !enabled)
                {
                    ++refused;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "weapon table audit: " + *weaponName + " triple " +
                            std::to_string(triple) + " has a cell that will not read");
                    break;
                }
                // The same three skips readDefaultWeaponAttachments makes, in the same
                // order -- an audit that applied a different rule would report weapons
                // that work and miss ones that do not.
                if (slotName->empty() && defaultName->empty() && enabled->empty())
                    continue;
                if (!slotName->empty() && defaultName->empty() && enabled->empty())
                    continue;
                if (*enabled == "n" || *enabled == "y")
                    continue;
                // THE SAME BLANK RULE THE PARSER USES. Counted apart rather than passed
                // over: these ARE the rows that used to drop a class, and an audit that
                // simply stopped mentioning them would make the fix look like the problem
                // had never existed.
                if (enabled->empty())
                {
                    ++blank;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "weapon table audit: " + *weaponName + " has a BLANK enabled cell" +
                            " -- slot='" + show(*slotName) + "' default='" +
                            show(*defaultName) + "' triple " + std::to_string(triple) +
                            "; tolerated as not-enabled");
                    break;
                }
                ++refused;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "weapon table audit: " + *weaponName + " REFUSES -- enabled='" +
                        show(*enabled) + "' (" + std::to_string(enabled->size()) +
                        " bytes) slot='" + show(*slotName) + "' default='" +
                        show(*defaultName) + "' triple " + std::to_string(triple) +
                        " column " + std::to_string(column + 2));
                break;
            }
        }

        // AND WRITE THE ROWS OUT, so the slot census can be JOINED against the item
        // names offline instead of guessing from counts. The player has 647 primaries and
        // the table has 657: the ten are findable only by name, and only by pairing this
        // list with item-names.csv -- a weapon the table has but the catalogue does not
        // back can never be owned or listed, however the ownership patch behaves.
        {
            const auto rowsPath = diagnosticPath(L"weapon-slots.csv");
            std::ofstream rows(rowsPath, std::ios::trunc);
            if (!rows)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "weapon table audit: cannot write " + rowsPath.string() +
                        " -- the slot census below is all there is");
            }
            else
            {
                rows << "weapon,slot\n";
                for (std::int32_t rowIndex = 0; rowIndex < table->rowCount; ++rowIndex)
                {
                    const auto *row = table->values +
                        static_cast<std::size_t>(rowIndex) * table->columnCount;
                    const auto weaponName = readStringTableCell(row[0]);
                    if (!weaponName || weaponName->empty())
                        continue;
                    std::string slot("<blank>");
                    if (static_cast<std::int32_t>(WeaponItemsSlotColumn) <
                            table->columnCount)
                    {
                        const auto cell = readStringTableCell(row[WeaponItemsSlotColumn]);
                        if (cell && !cell->empty())
                            slot = *cell;
                    }
                    rows << *weaponName << ',' << slot << '\n';
                }
            }
        }

        for (const auto &[slot, count] : slots)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "weapon table audit: slot '" + slot + "' has " + std::to_string(count) +
                    " weapon(s)");
        }

        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "weapon table audit: " + std::to_string(audited) + " named rows of " +
                std::to_string(table->rowCount) + ", " + std::to_string(refused) +
                " would refuse their default attachments, " + std::to_string(blank) +
                " tolerated for a blank enabled cell");
    }

    std::optional<std::vector<NamedWeaponAttachment>>
        EngineBindings::readDefaultWeaponAttachments(
            const std::string_view weaponName) const
    {
        // SAY WHICH EXIT FIRED. There are eight ways out of this function and the caller
        // reports `default_attachments` for every one of them, so a weapon that is simply
        // missing from the table is indistinguishable from a table that is not loaded or a
        // cell that would not read. readAttachmentModelSlot below already solved this with
        // a per-table outcome string; this is the same idea, edge-triggered on the message
        // so a healthy weapon says nothing.
        const auto refuse = [this, weaponName](const char *why)
            -> std::optional<std::vector<NamedWeaponAttachment>>
        {
            auto message = "default attachments unavailable for '" +
                std::string(weaponName) + "': " + why;
            if (message != lastDefaultAttachmentRefusal_)
            {
                lastDefaultAttachmentRefusal_ = message;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, message);
            }
            return std::nullopt;
        };

        if (!dbFindXAssetHeader_)
            return refuse("DB_FindXAssetHeader unbound");
        if (!validBookingName(weaponName))
            return refuse("the weapon name is not a usable identifier");
        const auto *table = readStringTable(
            dbFindXAssetHeader_, dbIsXAssetDefault_, WeaponItemsTableName, 40);
        if (!table)
            return refuse("the weapon items table is not loaded");
        const auto foundRow = findStringTableRow(*table, weaponName);
        if (!foundRow || !*foundRow)
            return refuse("no row for this weapon in the weapon items table");
        const auto *row = *foundRow;

        std::vector<NamedWeaponAttachment> defaults;
        defaults.reserve(WeaponItemsSlotTripleCount);
        for (std::size_t triple = 0; triple < WeaponItemsSlotTripleCount; ++triple)
        {
            const auto column = WeaponItemsFirstSlotColumn + triple * 3;
            const auto slotName = readStringTableCell(row[column]);
            const auto defaultName = readStringTableCell(row[column + 1]);
            const auto enabled = readStringTableCell(row[column + 2]);
            if (!slotName || !defaultName || !enabled)
                return refuse("a slot/default/enabled cell would not read");
            if (slotName->empty() && defaultName->empty() && enabled->empty())
                continue;
            // Some weapon rows declare an optional model slot without a
            // built-in component (for example CSG12 SRA and USP BAS).
            if (!slotName->empty() && defaultName->empty() && enabled->empty())
                continue;
            if (*enabled == "n")
                continue;
            // A BLANK `enabled` BESIDE A REAL DEFAULT IS NOT ENABLED. This dropped the
            // whole class for 19 of the table's 838 weapons -- every type95 variant
            // INCLUDING the base type95_mp, plus ak47ornate, akbpcoral, famasnya and
            // famasnyb -- and a dropped class is a player who edits his loadout, spawns,
            // and finds the gun he picked is simply not there. Measured by
            // auditWeaponItemsTable; all nineteen are the same shape, `iro`/`iro_default`
            // with an empty third cell (`cam` on three of them).
            //
            // WHICH WAY TO READ A BLANK IS A JUDGEMENT, so it is made in the direction
            // that cannot build a wrong gun. Reading it as ENABLED would add a default
            // attachment nobody asked for, and a wrong attachment id names a tag the
            // model does not have and faults the client at spawn (section 187). Reading
            // it as NOT enabled can at worst omit one built-in component, and the row
            // immediately above already treats an empty third cell as "not enabled" when
            // the default is empty too. Logged once per weapon so a missing iron sight
            // has somewhere to be traced to.
            if (enabled->empty())
            {
                auto message = "default attachment slot '" + *slotName + "' of '" +
                    std::string(weaponName) + "' has a BLANK enabled cell beside default '" +
                    *defaultName + "' -- treating it as not enabled";
                if (message != lastBlankEnabledNote_)
                {
                    lastBlankEnabledNote_ = message;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, message);
                }
                continue;
            }
            if (*enabled != "y")
            {
                // SHOW THE BYTES, for the same reason the defaultName case below does:
                // "neither y nor n" is a verdict and a verdict cannot be checked. It cost
                // a player his class on type95techslime_mp and there was no way to tell
                // from the log whether the cell was empty, localised, or something the
                // reader mis-sliced -- and the OFFLINE copy of this table cannot settle
                // it either, because the extractor resolves only 57% of its string-pool
                // back-references and prints another weapon's text for the rest.
                std::string shown;
                for (const auto character : *enabled)
                {
                    shown += (character >= 32 && character < 127)
                        ? std::string(1, character)
                        : "<" + std::to_string(static_cast<unsigned char>(character)) + ">";
                }
                return refuse(("an 'enabled' cell is neither y nor n: '" + shown +
                               "' (" + std::to_string(enabled->size()) + " bytes) in slot '" +
                               *slotName + "', default '" + *defaultName + "', triple " +
                               std::to_string(triple) + " at column " +
                               std::to_string(column + 2)).c_str());
            }
            // AN ENABLED SLOT WITH NO DEFAULT IS A SLOT, NOT A FAILURE. The case above
            // only covers a row that leaves `enabled` blank; tmp_mp marks the slot "y"
            // and still names no built-in component. Refusing the whole weapon for that
            // skipped the entire class, and a class with no weapons is a SessionStart
            // that queues and never commits -- which is what kept a player at active=0.
            if (defaultName->empty())
                continue;
            if (!validBookingName(*defaultName))
            {
                // SHOW THE BYTES rather than calling it unusable. "not an identifier" is
                // a verdict, and a verdict cannot be checked; the value can.
                std::string shown;
                for (const auto character : *defaultName)
                {
                    shown += (character >= 32 && character < 127)
                        ? std::string(1, character)
                        : "<" + std::to_string(static_cast<unsigned char>(character)) + ">";
                }
                return refuse(("default attachment name is not usable: '" + shown +
                               "' in slot '" + *slotName + "'").c_str());
            }
            const auto slot = parseWeaponAttachmentSlot(*slotName);
            if (!slot || *slot == 0)
                return refuse("a slot name does not parse");
            defaults.push_back({ .slot = *slot, .name = *defaultName });
        }
        return defaults;
    }

    std::optional<std::uint8_t> EngineBindings::readAttachmentModelSlot(
        const std::string_view attachmentName) const
    {
        if (!dbFindXAssetHeader_ || !validBookingName(attachmentName))
            return std::nullopt;
        // FOURTEEN TABLE LOOKUPS AND ONE `std::nullopt`. Absent table, absent
        // row, ambiguous row and "in none of them" all leave by the same
        // return, and the caller reports `equipped_attachment_slot` for every
        // one of them - so record a character per table and let the log say
        // which of the four it was. `-` table missing, `?` row read failed,
        // `.` row absent, `y` matched.
        std::string outcome;
        outcome.reserve(AttachmentSlotTables.size());
        std::optional<std::uint8_t> result;
        bool ambiguous = false;
        for (const auto &[tableName, slot] : AttachmentSlotTables)
        {
            const auto *table = readStringTable(dbFindXAssetHeader_, dbIsXAssetDefault_, tableName, 1);
            if (!table)
            {
                outcome += '-';
                continue;
            }
            const auto row = findStringTableRow(*table, attachmentName);
            if (!row)
            {
                outcome += '?';
                continue;
            }
            if (!*row)
            {
                outcome += '.';
                continue;
            }
            outcome += 'y';
            if (result)
                ambiguous = true;
            else
                result = slot;
        }
        if (!result || ambiguous ||
            outcome.find_first_of("-?") != std::string::npos)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "attachment slot unresolved name=" +
                    std::string(attachmentName) + " tables=" + outcome +
                    " slot=" +
                    (result ? std::to_string(*result) : std::string("none")) +
                    (ambiguous ? " AMBIGUOUS" : ""));
        }
        if (ambiguous)
            return std::nullopt;
        return result;
    }

    std::uint32_t EngineBindings::registerGameplayDvars() const
    {
        // CG_Init's own seven, in its own order, each one faulting on its own
        // so a bad block names itself instead of taking the other six with it.
        if (!module_)
            return 0;
        constexpr std::array Blocks{
            GameplayDvarsRegisterRva,
            GameLogDvarsRegisterRva,
            VehicleDvarsRegisterRva,
            PlayerDvarsRegisterRva,
            ActorDvarsRegisterRva,
            MiscDvarsRegisterRva,
            ScoreDvarsRegisterRva,
        };
        std::uint32_t registered{};
        for (const auto rva : Blocks)
        {
            NativeFault fault{};
            if (!tryCallVoid(module_ + rva, fault))
            {
                char failure[192]{};
                std::snprintf(
                    failure, sizeof(failure),
                    "gameplay dvar block faulted block=0x%07X at rva=0x%07X "
                    "op=%u target=0x%08X code=0x%08X",
                    static_cast<std::uint32_t>(rva),
                    fault.address >= reinterpret_cast<std::uint32_t>(module_)
                        ? fault.address -
                              reinterpret_cast<std::uint32_t>(module_)
                        : fault.address,
                    fault.operation, fault.target, fault.code);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, failure);
                break;
            }
            ++registered;
        }
        return registered;
    }

    bool EngineBindings::characterPresentationResolverAvailable() const
    {
        return characterSelectionResolve_ != nullptr;
    }

    bool EngineBindings::weaponRegistryInitialized() const
    {
        constexpr auto BaseWeaponCount = BaseWeaponAssetCount;
        if (!module_)
            return false;
        const auto *weaponCount = reinterpret_cast<const std::uint32_t *>(
            module_ + WeaponRegistryCountRva);
        const auto *attachmentModelCount =
            reinterpret_cast<const std::uint16_t *>(
                module_ + AttachmentModelCountRva);
        const auto *mappingCounts = module_ + PerWeaponAttachmentCountsRva;
        if (!readableSpan(weaponCount, sizeof(*weaponCount)) ||
            !readableSpan(attachmentModelCount, sizeof(*attachmentModelCount)) ||
            !readableSpan(mappingCounts, BaseWeaponCount) || !*weaponCount ||
            *weaponCount >= WeaponConfigStringCount || *attachmentModelCount <= 2)
        {
            return false;
        }

        return std::any_of(
            mappingCounts,
            mappingCounts + std::min(*weaponCount, BaseWeaponCount),
            [](const std::uint8_t count) { return count != 0; });
    }

    WeaponRegistryInitializationStatus
        EngineBindings::ensureWeaponRegistryInitialized() const
    {
        if (!module_ || !weaponRegistryReset_ || !weaponRegistryInitialize_ ||
            !zoneLoaded_ || !configStringGet_ || !weaponResolver_ ||
            !weaponLookup_)
        {
            return WeaponRegistryInitializationStatus::InitializationFailed;
        }
        if (weaponRegistryInitialized())
            return WeaponRegistryInitializationStatus::Ready;
        if (!zoneLoaded_("common_mp"))
            return WeaponRegistryInitializationStatus::CommonAssetsUnavailable;

        // VOLATILE IS LOAD-BEARING. MSVC gives a non-volatile local that is
        // modified inside __try an INDETERMINATE value once an exception
        // unwinds, so every counter here read as garbage on exactly the path
        // worth measuring: one run reported stage=5 with walked=1 and
        // mismatches=0 while also naming a mismatch at index 1, which cannot
        // all be true at once. The char buffers were always fine - they are
        // memory writes - and it was the register-cached scalars that lied.
        volatile bool initialized{};
        volatile std::uint32_t failedIndex{};
        volatile std::uint32_t failedResolvedIndex{};
        volatile std::uint32_t defaultWeapon{};
        volatile std::uint32_t exceptionCode{};
        volatile std::uint32_t walked{};
        volatile std::uint32_t named{};
        char failedName[128]{};
        // OLMOD(weapon-registry-stages): four native calls behind one __try
        // reported one exception code and no way to tell WHICH of them raised
        // it, which reads as "the registry is broken" when it is one call. Each
        // stage now faults on its own, and `stage` in the log below names it.
        //  1 reset  2 configstring walk  3 default resolve  4 initialize  5 verify
        volatile std::uint32_t stage{1};
        // `stage` records PROGRESS and is overwritten as the function walks on
        // past a break; `faultStage` records where a fault actually happened
        // and is written once. Reading progress as the fault site said stage=5
        // for three runs while the real fault was the resolver at stage 22.
        volatile std::uint32_t faultStage{};
        // Not volatile, and it does not need to be: its address is taken, so
        // MSVC keeps it in memory and the __try rule about register-cached
        // locals does not reach it. Same reason the char buffers always read
        // back correctly while every scalar counter here did not.
        NativeFault fault{};
        char firstNames[6][96]{};
        char firstMismatch[6][96]{};
        volatile std::uint32_t mismatches{};
        volatile std::uint32_t faults{};
        char beforeAfter[192]{};
        const auto registryWord = [this](const std::size_t rva) -> std::uint32_t {
            const auto *const word =
                reinterpret_cast<const std::uint32_t *>(module_ + rva);
            return readableSpan(word, sizeof(*word)) ? *word : 0xFFFFFFFFu;
        };
        char preReset[192]{};
        std::snprintf(
            preReset, sizeof(preReset),
            "before reset count=%u cache=%u counter=%u initialized=%u",
            registryWord(WeaponRegistryCountRva),
            registryWord(WeaponRegistryLookupCacheRva),
            registryWord(0x1588634u),
            weaponRegistryInitialized() ? 1u : 0u);
        // THE GAMEPLAY DVARS FIRST, because registering a weapon reads one.
        // sub_432130 loads mp/gametypeWeaponCustomTable.csv and asks, per
        // weapon, whether the current gametype is in that row's '|'-separated
        // list - and sub_432000 does it with `mov ecx, [edx+0Ch]` on the
        // g_gametype dvar, unguarded. In a dedicated process that dvar has
        // never been registered, because the only thing that registers it is
        // CG_Init, so edx was 0 and the read of 0xC was the whole fault.
        //
        // Nothing here is a workaround: it calls the game's own registration
        // blocks, and it does so ONCE, gated on the dvar the fault named.
        char dvarState[256]{};
        {
            auto *const gametypeDvar = reinterpret_cast<void **>(
                module_ + GametypeDvarRva);
            const auto before = readableSpan(gametypeDvar, sizeof(*gametypeDvar))
                ? *gametypeDvar : nullptr;
            std::uint32_t registered{};
            if (!before)
                registered = registerGameplayDvars();
            const auto after = readableSpan(gametypeDvar, sizeof(*gametypeDvar))
                ? *gametypeDvar : nullptr;
            const auto *const value =
                after && readableSpan(static_cast<const char *>(after) + 0xC, 4)
                    ? *reinterpret_cast<const char *const *>(
                          static_cast<const char *>(after) + 0xC)
                    : nullptr;
            std::snprintf(
                dvarState, sizeof(dvarState),
                "gameplay dvars blocks=%u g_gametype before=0x%08X after=0x%08X "
                "value=%.64s",
                registered,
                static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(before)),
                static_cast<std::uint32_t>(
                    reinterpret_cast<std::uintptr_t>(after)),
                readableSpan(value, 1) ? value : "<null>");
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, dvarState);
        __try
        {
            // 1:1 WITH THE GAME'S OWN REBUILD. CL_ParseGamestate does this at
            // sub_453760+0x12D0, and the lazy Com_Frame rebuild sub_4FE120
            // agrees on every step the two share:
            //
            //     if (weaponCount == 0) { registryMode = 2; reset(); }
            //     for (i = 1; i < 0x6A4; ++i) walk(i, 1);   // skip '*' names
            //     defaultWeapon = resolve("defaultweapon_mp", nullptr);
            //     [knife block, guarded off - see below]
            //     initialize(1);
            //     loadKnifeStatsTable();
            //     for (i = 1; i < 0x6A4; ++i) walk(i, 0);   // now the '*' ones
            //
            // Three things this used to get wrong, all of them measurable:
            // the reset was UNCONDITIONAL, the mode word was never set, and
            // initialize() was called with no argument at all.
            //
            // THE COUNT AND THE MEMO ARE NOT OURS TO ZERO. That was written on
            // the theory that a stale count would make WeaponLookup walk the
            // table the reset had just emptied. The game never touches them
            // here, and it does not have to: it only resets when the count is
            // already 0, so the reset and the count agree by construction.
            // Live logs then measured `before reset count=0` and the zeroing
            // changed nothing, which is the same answer from the other side.
            if (registryWord(WeaponRegistryCountRva) == 0)
            {
                auto *const registryMode = reinterpret_cast<std::uint32_t *>(
                    module_ + WeaponRegistryModeRva);
                if (readableSpan(registryMode, sizeof(*registryMode)))
                    *registryMode = 2;
                weaponRegistryReset_();
            }
            initialized = true;
            std::snprintf(
                beforeAfter, sizeof(beforeAfter),
                "after reset count=%u cache=%u counter=%u attachModels=%u map0=%u",
                registryWord(WeaponRegistryCountRva),
                registryWord(WeaponRegistryLookupCacheRva),
                registryWord(0x1588634u),
                static_cast<std::uint32_t>(
                    *reinterpret_cast<const std::uint16_t *>(
                        module_ + AttachmentModelCountRva)),
                static_cast<std::uint32_t>(
                    *(module_ + PerWeaponAttachmentCountsRva)));
            // ORDER IS NOT THE BUG. Running weaponRegistryInitialize_ before
            // the walk instead of after was measured and the resolver faulted
            // identically (fault=22), so the reset -> walk -> initialize order
            // the game itself uses is kept.
            //
            // THE WALK IS sub_59B560, ONE INDEX AT A TIME. Its whole prefix is
            // reproduced here rather than called, because on a mismatch it ends
            // in Com_Error("181 %s %d %d") and Com_Error LONGJMPS - through
            // this __try, and through a jmp_buf this thread may never have set.
            // The decision tree is the game's:
            //
            //     lea esi, [edi+1748h]      ; base 5960 + index
            //     call CL_GetConfigString   ; index in ESI
            //     test al, al / jz          ; empty -> skip
            //     cmp [ebp+arg_0], 0 / jz   ; pass 0 does NOT skip modular
            //     cmp al, '*'    / jz       ; pass 1 skips modular names
            //     push 0 / push esi / call WeaponResolver
            //     cmp eax, edi              ; resolved index must BE the index
            //
            // Pass 0's modular tail (sub_431F30, sub_80C220, sub_660C90 and the
            // deferred list at 0x82CA590) is not ported, so pass 0 here stops
            // after the resolve. That is a KNOWN GAP, not an equivalence claim:
            // it registers the '*' names but does not queue their reload.
            static_assert(
                WeaponConfigStringBase == WeaponWalkConfigStringBase,
                "the walk base has to be the one sub_59B560 adds to the index");
            static_assert(
                WeaponConfigStringCount == WeaponWalkEntryCount,
                "the walk bound has to be CL_ParseGamestate's `cmp edi, 6A4h`");
            stage = 2;
            for (std::uint32_t pass = 0; pass < 2; ++pass)
            {
                // Pass 1 first, exactly as CL_ParseGamestate orders them: the
                // plain weapons register before anything modular refers to one.
                const bool skipModular = pass == 0;
                if (!initialized)
                    break;
                for (std::uint32_t index = 1;
                     index < WeaponConfigStringCount;
                     ++index)
                {
                    walked = index;
                    const auto *const name = nativeConfigString(
                        WeaponConfigStringBase + index);
                    if (!name || !*name)
                        continue;
                    if (skipModular ? *name == '*' : *name != '*')
                        continue;
                    // OLMOD(weapon-registry-stages): the first names this walk
                    // sees, recorded BEFORE anything is asked to resolve them.
                    // A stage-2 fault says the resolver died on a name; only
                    // the name itself says whether the accessor handed it a
                    // weapon or rubbish, and that distinction was the whole of
                    // the __fastcall/ESI bug.
                    if (named < 6)
                    {
                        std::snprintf(
                            firstNames[named], sizeof(firstNames[named]),
                            "%u:%s", index, name);
                    }
                    ++named;
                    std::uint32_t resolvedIndex{};
                    if (!tryWeaponResolve(
                            reinterpret_cast<void *>(weaponResolver_), name,
                            resolvedIndex, fault))
                    {
                        ++faults;
                        exceptionCode = fault.code;
                        faultStage = 20 + pass;
                        initialized = false;
                        failedIndex = index;
                        std::snprintf(
                            failedName, sizeof(failedName), "%s", name);
                        break;
                    }
                    if (resolvedIndex != index)
                    {
                        // Record the first handful rather than stopping at one:
                        // whether the whole table is shifted or only index 1
                        // disagrees is the difference between an off-by-one and
                        // an expectation that was never true for the default
                        // weapon, and one sample cannot tell them apart.
                        if (mismatches < 6)
                        {
                            std::snprintf(
                                firstMismatch[mismatches],
                                sizeof(firstMismatch[0]),
                                "%u->%u:%s", index, resolvedIndex, name);
                        }
                        ++mismatches;
                        if (!failedIndex)
                        {
                            failedIndex = index;
                            failedResolvedIndex = resolvedIndex;
                            std::snprintf(
                                failedName, sizeof(failedName), "%s", name);
                        }
                        initialized = false;
                        if (mismatches >= 6)
                            break;
                    }
                }
                if (pass == 0)
                {
                    // Between the passes, and only there: CL_ParseGamestate
                    // resolves the default weapon, completes the registry, and
                    // loads the knife stats table before it walks the modular
                    // names. The knife block at 0x454A98 is skipped - it is
                    // guarded on an obfuscated mode word (`[eax+0x180C1C] == 2`
                    // read through dword_1C1D188 ^ 0xFBB2C97A) and it only
                    // populates a deferred-reload list.
                    stage = 3;
                    defaultWeapon = weaponResolver_("defaultweapon_mp", nullptr);
                    stage = 4;
                    // `push 1; call sub_42FE80` at 0x454B41 and 0x4FE1AC. The
                    // parameter is not optional and was never being passed.
                    static_cast<void>(weaponRegistryInitialize_(1));
                    if (weaponKnifeStatsLoad_)
                        weaponKnifeStatsLoad_();
                    stage = 5;
                }
            }
            std::uint32_t verifyLookup{};
            if (!tryWeaponLookup(
                    reinterpret_cast<void *>(weaponLookup_),
                    "defaultweapon_mp", verifyLookup, fault))
            {
                exceptionCode = fault.code;
                faultStage = 51;
                initialized = false;
            }
            else
            {
                initialized = initialized && defaultWeapon != 0 &&
                    verifyLookup == defaultWeapon;
            }
        }
        __except (captureNativeFault(GetExceptionInformation(), fault))
        {
            exceptionCode = fault.code;
            if (!faultStage)
                faultStage = 90 + stage;
            initialized = false;
        }
        if (!initialized)
        {
            const auto *const weaponCount = reinterpret_cast<const std::uint32_t *>(
                module_ + WeaponRegistryCountRva);
            char details[320]{};
            std::snprintf(
                details,
                sizeof(details),
                "weapon registry rebuild failed stage=%u fault=%u index=%u resolved=%u "
                "name=%s default=%u count=%u walked=%u named=%u faults=%u "
                "exception=0x%08X",
                stage,
                faultStage,
                failedIndex,
                failedResolvedIndex,
                failedName,
                defaultWeapon,
                readableSpan(weaponCount, sizeof(*weaponCount)) ? *weaponCount : 0,
                walked,
                named,
                faults,
                exceptionCode);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, details);
            // No std::string in this function: it carries a __try, and MSVC
            // refuses object unwinding alongside it (C2712).
            char seen[640]{};
            int written = std::snprintf(
                seen, sizeof(seen), "weapon registry first names");
            for (const auto &entry : firstNames)
            {
                if (!*entry || written < 0 ||
                    static_cast<std::size_t>(written) >= sizeof(seen))
                {
                    continue;
                }
                const auto added = std::snprintf(
                    seen + written, sizeof(seen) - written, " [%s]", entry);
                if (added > 0)
                    written += added;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, seen);
            const auto *const registryWords =
                reinterpret_cast<const std::uint32_t *>(
                    module_ + WeaponRegistryCountRva);
            char globals[160]{};
            std::snprintf(
                globals, sizeof(globals),
                "weapon registry globals count=%u next=0x%08X",
                readableSpan(registryWords, sizeof(*registryWords))
                    ? registryWords[0] : 0,
                readableSpan(registryWords + 1, sizeof(*registryWords))
                    ? registryWords[1] : 0);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, globals);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, preReset);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, beforeAfter);
            // WHERE it faulted, as an RVA that pastes straight into IDA, and
            // WHAT it touched. 0x02F060 reading address 0 is a null WeaponDef
            // string; anything inside 0x0F82E0 is Com_Error, which means the
            // engine RAISED this rather than tripping over it.
            char where[224]{};
            std::snprintf(
                where, sizeof(where),
                "weapon registry fault at rva=0x%07X op=%u target=0x%08X "
                "code=0x%08X",
                fault.address >= reinterpret_cast<std::uint32_t>(module_)
                    ? fault.address - reinterpret_cast<std::uint32_t>(module_)
                    : fault.address,
                fault.operation,
                fault.target,
                fault.code);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, where);
            // Com_Error's own state. sub_4F82E0 bumps the depth, keeps the
            // level, formats the message, and THEN longjmps - so a non-zero
            // depth here says the engine reported a real error and the text is
            // its own words, not our guess about them.
            const auto *const errorDepth =
                reinterpret_cast<const std::uint32_t *>(
                    module_ + ComErrorDepthRva);
            const auto *const errorLevel =
                reinterpret_cast<const std::uint32_t *>(
                    module_ + ComErrorLevelRva);
            const auto *const errorText =
                reinterpret_cast<const char *>(module_ + ComErrorTextRva);
            char reported[352]{};
            std::snprintf(
                reported, sizeof(reported),
                "weapon registry com_error depth=%u level=%u text=%.240s",
                readableSpan(errorDepth, sizeof(*errorDepth)) ? *errorDepth : 0,
                readableSpan(errorLevel, sizeof(*errorLevel)) ? *errorLevel : 0,
                readableSpan(errorText, 241) ? errorText : "<unreadable>");
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, reported);
            char mism[640]{};
            int mwritten = std::snprintf(
                mism, sizeof(mism), "weapon registry mismatches=%u", mismatches);
            for (const auto &entry : firstMismatch)
            {
                if (!*entry || mwritten < 0 ||
                    static_cast<std::size_t>(mwritten) >= sizeof(mism))
                {
                    continue;
                }
                const auto added = std::snprintf(
                    mism + mwritten, sizeof(mism) - mwritten, " [%s]", entry);
                if (added > 0)
                    mwritten += added;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, mism);
        }
        return initialized && weaponRegistryInitialized()
            ? WeaponRegistryInitializationStatus::Ready
            : WeaponRegistryInitializationStatus::InitializationFailed;
    }

    AlphaWeaponPortStatus EngineBindings::installAlphaWeaponPorts() const
    {
        const auto enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_ALPHA_WEAPONS",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        if (!enabled)
            return AlphaWeaponPortStatus::Disabled;

        const auto convertedBarrettEnabled =
            GetEnvironmentVariableA(
                "OLMOD_ALPHA_BARRETT_METADATA", nullptr, 0) > 1;

        // ConfigStringTypes is loaded with the shipped weapon boundary: slot
        // 1224 and later are tagged as modular weapon strings. Native weapon
        // resolution appends our linked alpha WeaponDefs at that same boundary,
        // but does not retag the new ordinary definitions. The DEDICATED must
        // retag them while it derives the outgoing modular boundary. The CLIENT
        // must not: runtime-only alpha base names are absent from its constant
        // configstring table, so type 19 makes CL_GetConfigString return null and
        // sub_59B560 dereference it. Its gamestate hook restores the same native
        // registry entries directly and leaves those empty wire slots tagged as
        // dynamic, which makes the accessor return the safe empty gamestate
        // string until the real "** ..." row. Type 19 is this build's ordinary
        // weapon type; type 21 and >=23 are the measured dynamic sentinels used
        // by firstDynamicWeaponAssetIndex.
        const auto markAlphaBaseWeapon = [this](const std::uint32_t index) {
            if (!module_ || !index || index >= BaseWeaponAssetCount)
                return false;
            if (OlMod::processRole() == OlMod::ProcessRole::Client)
                return true;
            auto *const type = module_ + ConfigStringTypesRva +
                WeaponConfigStringBase + index;
            if (!readableSpan(type, sizeof(*type)))
                return false;
            *type = 19;
            return true;
        };

        const auto previous = alphaWeaponPortStatus_.load(
            std::memory_order_acquire);
        switch (previous)
        {
        case AlphaWeaponPortStatus::InvalidDefinition:
        case AlphaWeaponPortStatus::LinkFailed:
        case AlphaWeaponPortStatus::RegistrationFailed:
            return previous;
        case AlphaWeaponPortStatus::SourceAssetMissing:
            // A converted Barrett closure legitimately disappears with the
            // front-end common_mp generation and is rebuilt below after the
            // booked map loads. Missing retained assets remain terminal when
            // that opt-in conversion is not active.
            if (!convertedBarrettEnabled)
                return previous;
            alphaWeaponPortStatus_.store(
                AlphaWeaponPortStatus::WaitingForWeaponRegistry,
                std::memory_order_release);
            break;
        case AlphaWeaponPortStatus::Ready:
        {
            // A new map/gamestate generation rebuilds the native weapon
            // registry without unloading the cloned XAssets. The assets stay
            // valid, but their runtime indices disappear. Verify every active
            // port before accepting the cached Ready state and fall through to
            // the normal resolver path when the engine has reset the table.
            bool allRegistered = module_ && weaponLookup_;
            for (const auto &port : SV_AlphaWeaponPorts())
            {
                if (!allRegistered)
                    break;
                if (port.lineage == SvAlphaWeaponLineage::MissingModelFamily ||
                    (port.lineage ==
                            SvAlphaWeaponLineage::ConvertedPresentation &&
                        !convertedBarrettEnabled))
                {
                    continue;
                }
                std::uint32_t index{};
                NativeFault fault{};
                allRegistered = tryWeaponLookup(
                                    reinterpret_cast<void *>(weaponLookup_),
                                    port.alphaName, index, fault) &&
                    index != 0 && markAlphaBaseWeapon(index);
            }
            if (allRegistered)
                return previous;
            alphaWeaponPortStatus_.store(
                AlphaWeaponPortStatus::WaitingForWeaponRegistry,
                std::memory_order_release);
            break;
        }
        default:
            break;
        }

        const auto publish = [this](const AlphaWeaponPortStatus status) {
            alphaWeaponPortStatus_.store(status, std::memory_order_release);
            return status;
        };
        if (!module_ || !zoneLoaded_ || !dbLinkXAssetEntry_ ||
            !weaponLookup_ || !weaponResolver_)
        {
            return publish(AlphaWeaponPortStatus::InvalidDefinition);
        }
        if (gameThreadId_.load(std::memory_order_acquire) !=
            GetCurrentThreadId())
        {
            return publish(AlphaWeaponPortStatus::WrongThread);
        }
        if (!zoneLoaded_("common_mp"))
            return publish(AlphaWeaponPortStatus::WaitingForCommonAssets);
        if (!weaponRegistryInitialized())
            return publish(AlphaWeaponPortStatus::WaitingForWeaponRegistry);

        constexpr std::uint32_t WeaponAssetType = 28;
        constexpr std::uint32_t StringTableAssetType = 37;
        constexpr std::size_t XAssetEntryPoolRva = 0x1F9B120;
        constexpr std::size_t XAssetEntryCount = 120000;
        constexpr std::size_t XAssetEntrySize = 28;
        constexpr std::size_t XAssetEntryTypeOffset = 0;
        constexpr std::size_t XAssetEntryDataOffset = 8;
        constexpr std::size_t XAssetEntryZoneOffset = 16;
        const auto assetZoneForHeader = [this](
                                                const std::uint32_t type,
                                                const void *const header)
            -> std::optional<std::uint8_t> {
            if (!header)
                return std::nullopt;
            const auto *const entries = module_ + XAssetEntryPoolRva;
            for (std::size_t index{}; index < XAssetEntryCount; ++index)
            {
                const auto *const entry = entries + index * XAssetEntrySize;
                if (!readableSpan(entry, XAssetEntrySize))
                    return std::nullopt;
                std::uint32_t entryType{};
                const void *entryHeader{};
                std::memcpy(
                    &entryType, entry + XAssetEntryTypeOffset,
                    sizeof(entryType));
                std::memcpy(
                    &entryHeader, entry + XAssetEntryDataOffset,
                    sizeof(entryHeader));
                if (entryType == type && entryHeader == header &&
                    entry[XAssetEntryZoneOffset] != 0)
                {
                    return entry[XAssetEntryZoneOffset];
                }
            }
            return std::nullopt;
        };
        struct PublishedModelTable
        {
            std::array<char, 96> path{};
            std::vector<StringTableCell> cells;
            StringTable header{};
        };
        static std::vector<PublishedModelTable> publishedModelTables(
            SV_AlphaWeaponPorts().size());

        const auto ensureModelTable = [this, &publish](
                                          const SvAlphaWeaponPort &port,
                                          const std::size_t portIndex) {
            std::array<char, 96> sourcePath{};
            std::array<char, 96> targetPath{};
            const auto converted =
                port.lineage == SvAlphaWeaponLineage::ConvertedPresentation;
            const auto sourceLength = converted
                ? std::snprintf(
                      sourcePath.data(), sourcePath.size(),
                      "<converted-alpha-Barrett-table>")
                : std::snprintf(
                      sourcePath.data(), sourcePath.size(),
                      "mp/coWeapModels/%s.csv", port.sourceName);
            const auto targetLength = std::snprintf(
                targetPath.data(), targetPath.size(),
                "mp/coWeapModels/%s.csv", port.alphaName);
            if (sourceLength <= 0 || targetLength <= 0 ||
                static_cast<std::size_t>(sourceLength) >= sourcePath.size() ||
                static_cast<std::size_t>(targetLength) >= targetPath.size())
            {
                return publish(AlphaWeaponPortStatus::InvalidDefinition);
            }

            if (const auto *const existing = readStringTable(
                    dbFindXAssetHeader_, dbIsXAssetDefault_,
                    targetPath.data(), 4))
            {
                const auto row = findStringTableRow(*existing, port.alphaName);
                return row && *row
                    ? AlphaWeaponPortStatus::Ready
                    : publish(AlphaWeaponPortStatus::InvalidDefinition);
            }

            const StringTable *source{};
            if (!converted)
            {
                source = readStringTable(
                    dbFindXAssetHeader_, dbIsXAssetDefault_,
                    sourcePath.data(), 4);
                if (!source)
                    return publish(AlphaWeaponPortStatus::SourceAssetMissing);
            }

            auto &storage = publishedModelTables[portIndex];
            if (storage.cells.empty())
            {
                std::int32_t columnCount{};
                std::int32_t rowCount{};
                if (converted)
                {
                    const auto rows = SV_AlphaBarrettModelTable();
                    if (rows.empty())
                        return publish(AlphaWeaponPortStatus::InvalidDefinition);
                    columnCount = static_cast<std::int32_t>(rows.front().size());
                    rowCount = static_cast<std::int32_t>(rows.size());
                    storage.cells.reserve(rows.size() * rows.front().size());
                    for (const auto &row : rows)
                    {
                        for (std::size_t column{}; column < row.size(); ++column)
                        {
                            const auto value = column == 0
                                ? std::string_view{ port.alphaName }
                                : row[column];
                            storage.cells.push_back({
                                value.data(), SV_StringTableHash(value),
                            });
                        }
                    }
                }
                else
                {
                    columnCount = source->columnCount;
                    rowCount = source->rowCount;
                    const auto cellCount =
                        static_cast<std::size_t>(columnCount) *
                        static_cast<std::size_t>(rowCount);
                    storage.cells.assign(
                        source->values, source->values + cellCount);
                    std::size_t patchedRows{};
                    for (std::int32_t rowIndex{};
                         rowIndex < rowCount; ++rowIndex)
                    {
                        auto &cell = storage.cells[
                            static_cast<std::size_t>(rowIndex) * columnCount];
                        const auto value = readStringTableCell(cell);
                        if (!value)
                        {
                            storage.cells.clear();
                            return publish(
                                AlphaWeaponPortStatus::InvalidDefinition);
                        }
                        if (*value == port.sourceName)
                        {
                            cell.value = port.alphaName;
                            cell.hash = SV_StringTableHash(port.alphaName);
                            ++patchedRows;
                        }
                    }
                    if (!patchedRows)
                    {
                        storage.cells.clear();
                        return publish(AlphaWeaponPortStatus::InvalidDefinition);
                    }
                }
                std::copy_n(
                    targetPath.data(), static_cast<std::size_t>(targetLength) + 1,
                    storage.path.data());
                storage.header = {
                    storage.path.data(), columnCount,
                    rowCount, storage.cells.data(),
                };
            }

            void *linkedHeader = &storage.header;
            void *entry{};
            NativeFault fault{};
            if (!tryLinkXAssetEntry(
                    reinterpret_cast<void *>(dbLinkXAssetEntry_),
                    StringTableAssetType, &linkedHeader, entry, fault) ||
                !entry || !linkedHeader)
            {
                char failure[288]{};
                std::snprintf(
                    failure, sizeof(failure),
                    "alpha weapon model table link failed target=%s "
                    "source=%s rva=0x%07X op=%u targetAddress=0x%08X "
                    "code=0x%08X",
                    targetPath.data(), sourcePath.data(),
                    fault.address >= reinterpret_cast<std::uint32_t>(module_)
                        ? fault.address -
                              reinterpret_cast<std::uint32_t>(module_)
                        : fault.address,
                    fault.operation, fault.target, fault.code);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, failure);
                return publish(AlphaWeaponPortStatus::LinkFailed);
            }

            const auto *const target = readStringTable(
                dbFindXAssetHeader_, dbIsXAssetDefault_,
                targetPath.data(), 4);
            const auto row = target
                ? findStringTableRow(*target, port.alphaName)
                : std::optional<const StringTableCell *>{};
            if (!target || !row || !*row)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "alpha weapon model table verification failed target=" +
                        std::string(targetPath.data()) + " lookup=" +
                        (target ? "present" : "missing") + " row=" +
                        (row && *row ? "present" : "missing"));
                return publish(AlphaWeaponPortStatus::LinkFailed);
            }
            return AlphaWeaponPortStatus::Ready;
        };

        struct PublishedBarrettImage
        {
            std::array<char, 128> name{};
            std::array<std::byte, 16> loadDef{};
            std::array<std::byte, AlphaBarrettOlfinalGfxImageSize> header{};
            void *linked{};
        };
        struct PublishedBarrettMaterial
        {
            std::array<char, 128> name{};
            std::vector<std::array<std::byte, 12>> textures;
            std::vector<std::byte> constants;
            std::vector<std::byte> stateBits;
            std::array<std::byte, AlphaBarrettOlfinalMaterialSize> header{};
            void *linked{};
        };
        struct PublishedBarrettSurfs
        {
            std::array<char, 128> name{};
            std::array<std::byte, 48> header{};
            void *linked{};
        };
        struct PublishedBarrettModel
        {
            std::array<char, 128> name{};
            std::vector<std::uint16_t> boneNames;
            std::vector<std::byte> parentList;
            std::vector<std::byte> quaternions;
            std::vector<std::byte> translations;
            std::vector<std::byte> partClassification;
            std::vector<std::byte> baseMatrices;
            std::vector<void *> materials;
            std::vector<std::byte> boneInfo;
            std::array<std::byte, 360> header{};
            void *linked{};
        };
        struct PublishedBarrettAnimation
        {
            std::array<char, 128> name{};
            std::vector<std::uint16_t> boneNames;
            std::vector<std::byte> notify;
            std::vector<std::byte> dataByte;
            std::vector<std::byte> dataShort;
            std::vector<std::byte> dataInt;
            std::vector<std::byte> randomDataShort;
            std::vector<std::byte> randomDataByte;
            std::vector<std::byte> randomDataInt;
            std::vector<std::byte> indices;
            std::array<std::byte, 1> emptyStreamSentinel{};
            std::array<std::byte, 88> header{};
            std::string sourceName;
            void *linked{};
        };
        struct PublishedBarrettAssets
        {
            bool attempted{};
            bool ready{};
            std::vector<std::unique_ptr<PublishedBarrettImage>> images;
            std::vector<std::unique_ptr<PublishedBarrettMaterial>> materials;
            std::vector<std::unique_ptr<PublishedBarrettSurfs>> surfs;
            std::vector<std::unique_ptr<PublishedBarrettModel>> models;
            std::vector<std::unique_ptr<PublishedBarrettAnimation>> animations;
        };
        static PublishedBarrettAssets publishedBarrettAssets;

        std::array<char, 32768> barrettMetadataPath{};
        const auto barrettMetadataLength = GetEnvironmentVariableA(
            "OLMOD_ALPHA_BARRETT_METADATA",
            barrettMetadataPath.data(),
            static_cast<DWORD>(barrettMetadataPath.size()));
        const auto barrettMetadataEnabled =
            barrettMetadataLength > 0 &&
            barrettMetadataLength < barrettMetadataPath.size();
        constexpr std::uint32_t XModelAssetType = 4;
        const auto barrettSafeMaterialsEnabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_ALPHA_BARRETT_SAFE_MATERIALS",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        // common_mp is loaded once for the front end and again for the booked
        // map. The engine removes every runtime-linked entry owned by the old
        // generation during that transition, while this process-local cache
        // naturally survives. Use the private base model as the generation
        // sentinel and rebuild the closure from the immutable metadata when it
        // disappears. At that point every private entry from the same zone has
        // already been unlinked, so releasing its old backing storage is safe.
        if (barrettMetadataEnabled && publishedBarrettAssets.ready &&
            !findXAsset(
                XModelAssetType, "viewmodel_barrett", false).data)
        {
            publishedBarrettAssets = {};
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "alpha Barrett asset generation expired; rebuilding closure");
        }
        if (barrettMetadataEnabled && !publishedBarrettAssets.attempted)
        {
            publishedBarrettAssets.attempted = true;
            const auto failBarrettAssets = [&publish](
                                               const AlphaWeaponPortStatus status,
                                               const std::string &reason) {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "alpha Barrett asset publication failed: " + reason);
                return publish(status);
            };
            std::string loadError;
            const auto bundle = SV_LoadAlphaBarrettBundle(
                std::filesystem::path(barrettMetadataPath.data()), loadError);
            if (!bundle)
            {
                return failBarrettAssets(
                    AlphaWeaponPortStatus::InvalidDefinition, loadError);
            }

            constexpr std::uint32_t MaterialAssetType = 5;
            constexpr std::uint32_t GfxImageAssetType = 10;
            constexpr std::uint32_t XAnimAssetType = 2;
            constexpr std::size_t GfxImageInitializeRva = 0x7E7470;
            constexpr std::array<std::uint8_t, 7> GfxImageInitializePrefix{
                0x8B, 0x44, 0x24, 0x04, 0x83, 0xEC, 0x20,
            };
            if (!readableSpan(
                    module_ + GfxImageInitializeRva,
                    GfxImageInitializePrefix.size()) ||
                !std::equal(
                    GfxImageInitializePrefix.begin(),
                    GfxImageInitializePrefix.end(),
                    module_ + GfxImageInitializeRva))
            {
                return failBarrettAssets(
                    AlphaWeaponPortStatus::InvalidDefinition,
                    "GfxImage initializer bytes differ");
            }

            // Runtime links otherwise inherit loading zone 0 and are swept as
            // defaults during the following map transition. All converted
            // dependencies use stable ol-mod storage, so give them the same
            // resident lifetime as the retained CheyTac WeaponDef clone.
            const auto retainedBarrettOwner = findXAsset(
                WeaponAssetType, "cheytac_mp", false).data;
            const auto retainedBarrettZone = retainedBarrettOwner
                ? assetZoneForHeader(WeaponAssetType, retainedBarrettOwner)
                : std::optional<std::uint8_t>{};
            if (!retainedBarrettZone)
            {
                return failBarrettAssets(
                    AlphaWeaponPortStatus::SourceAssetMissing,
                    "retained CheyTac WeaponDef source zone is missing");
            }

            const auto address32 = [](const void *const pointer)
                -> std::optional<std::uint32_t> {
                const auto value = reinterpret_cast<std::uintptr_t>(pointer);
                if (!value || value > std::numeric_limits<std::uint32_t>::max())
                    return std::nullopt;
                return static_cast<std::uint32_t>(value);
            };
            publishedBarrettAssets.images.reserve(bundle->imageMetadata.size());
            for (const auto &source : bundle->imageMetadata)
            {
                auto storage = std::make_unique<PublishedBarrettImage>();
                if (source.name.size() + 1 > storage->name.size())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "image name is too long: " + source.name);
                }
                std::copy(source.name.begin(), source.name.end(),
                    storage->name.begin());
                const auto loadDefAddress = address32(storage->loadDef.data());
                const auto nameAddress = address32(storage->name.data());
                if (!loadDefAddress || !nameAddress ||
                    !SV_BuildOlfinalAlphaBarrettImage(
                        source, *loadDefAddress, *nameAddress,
                        storage->header, storage->loadDef))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "cannot construct image: " + source.name);
                }
                publishedBarrettAssets.images.push_back(std::move(storage));
            }

            for (auto &storage : publishedBarrettAssets.images)
            {
                if (const auto existing = findXAsset(
                        GfxImageAssetType, storage->name.data(), false).data)
                {
                    storage->linked = existing;
                    continue;
                }
                NativeFault fault{};
                if (!tryInitializeGfxImage(
                        module_ + GfxImageInitializeRva,
                        storage->header.data(), fault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "image initializer fault name=%s rva=0x%07X op=%u "
                        "target=0x%08X code=0x%08X",
                        storage->name.data(),
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }

                void *linkedHeader = storage->header.data();
                void *entry{};
                if (!tryLinkXAssetEntry(
                        reinterpret_cast<void *>(dbLinkXAssetEntry_),
                        GfxImageAssetType, &linkedHeader, entry, fault) ||
                    !entry || !linkedHeader ||
                    !trySetXAssetEntryZone(
                        entry, *retainedBarrettZone, fault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "image link fault name=%s rva=0x%07X op=%u "
                        "target=0x%08X code=0x%08X",
                        storage->name.data(),
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }
                storage->linked = linkedHeader;
                if (findXAsset(
                        GfxImageAssetType, storage->name.data(), false).data !=
                    storage->linked)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed,
                        "image lookup differs after link: " +
                            std::string(storage->name.data()));
                }
            }

            std::map<std::string, std::string, std::less<>>
                retainedBarrettMaterials;
            for (const auto &source : bundle->materials)
                retainedBarrettMaterials.emplace(source.name, source.cloneSource);
            std::set<std::string, std::less<>> retainedBarrettMaterialNames;

            publishedBarrettAssets.materials.reserve(bundle->materials.size());
            for (const auto &source : bundle->materials)
            {
                const auto finalTemplate = static_cast<const std::byte *>(
                    findXAsset(MaterialAssetType,
                        source.cloneSource.c_str(), false).data);
                if (!readableSpan(finalTemplate, AlphaBarrettOlfinalMaterialSize))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::SourceAssetMissing,
                        "material template is missing: " + source.cloneSource);
                }

                const auto templateSpan =
                    std::span<const std::byte, AlphaBarrettOlfinalMaterialSize>{
                        finalTemplate, AlphaBarrettOlfinalMaterialSize };
                bool routingCompatible =
                    SV_OlfinalAlphaBarrettMaterialLayoutCompatible(
                        source, templateSpan);
                const std::byte *templateTextures{};
                const std::byte *templateConstants{};
                if (routingCompatible)
                {
                    std::memcpy(&templateTextures, finalTemplate + 92,
                        sizeof(templateTextures));
                    std::memcpy(&templateConstants, finalTemplate + 96,
                        sizeof(templateConstants));
                    routingCompatible =
                        readableSpan(templateTextures,
                            source.textures.size() * 12) &&
                        readableSpan(templateConstants,
                            source.constants.size());
                }
                for (std::size_t index{};
                     routingCompatible && index < source.textures.size();
                     ++index)
                {
                    routingCompatible = std::equal(
                        source.textures[index].slotHeader.begin(),
                        source.textures[index].slotHeader.end(),
                        templateTextures + index * 12);
                }
                for (std::size_t offset{};
                     routingCompatible && offset < source.constants.size();
                     offset += 32)
                {
                    // The first four bytes identify the material constant.
                    // The remaining 28 bytes are the material-specific value
                    // that the alpha port intentionally replaces.
                    routingCompatible = std::equal(
                        source.constants.begin() + offset,
                        source.constants.begin() + offset + 4,
                        templateConstants + offset);
                }
                if (barrettSafeMaterialsEnabled || !routingCompatible)
                {
                    retainedBarrettMaterialNames.insert(source.name);
                    continue;
                }

                auto storage = std::make_unique<PublishedBarrettMaterial>();
                if (source.name.size() + 1 > storage->name.size())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "material name is too long: " + source.name);
                }
                std::copy(source.name.begin(), source.name.end(),
                    storage->name.begin());
                storage->textures.resize(source.textures.size());
                storage->constants = source.constants;
                storage->stateBits = source.stateBits;
                for (std::size_t index{}; index < source.textures.size(); ++index)
                {
                    std::copy(source.textures[index].slotHeader.begin(),
                        source.textures[index].slotHeader.end(),
                        storage->textures[index].begin());
                    const auto image = findXAsset(GfxImageAssetType,
                        source.textures[index].image.c_str(), false).data;
                    const auto imageAddress = address32(image);
                    if (!imageAddress)
                    {
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::SourceAssetMissing,
                            "material image is missing: " +
                                source.textures[index].image);
                    }
                    std::memcpy(storage->textures[index].data() + 8,
                        &*imageAddress, sizeof(*imageAddress));
                }

                const auto nameAddress = address32(storage->name.data());
                const auto texturesAddress = address32(
                    storage->textures.empty() ? nullptr : storage->textures.data());
                const auto constantsAddress = address32(
                    storage->constants.empty() ? nullptr : storage->constants.data());
                const auto stateBitsAddress = address32(
                    storage->stateBits.empty() ? nullptr : storage->stateBits.data());
                if (!nameAddress ||
                    (!storage->textures.empty() && !texturesAddress) ||
                    (!storage->constants.empty() && !constantsAddress) ||
                    (!storage->stateBits.empty() && !stateBitsAddress) ||
                    !SV_BuildOlfinalAlphaBarrettMaterial(source, templateSpan,
                        *nameAddress, texturesAddress.value_or(0),
                        constantsAddress.value_or(0),
                        stateBitsAddress.value_or(0), storage->header))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "cannot construct material: " + source.name);
                }
                publishedBarrettAssets.materials.push_back(std::move(storage));
            }

            for (auto &storage : publishedBarrettAssets.materials)
            {
                if (const auto existing = findXAsset(
                        MaterialAssetType, storage->name.data(), false).data)
                {
                    storage->linked = existing;
                    continue;
                }
                void *linkedHeader = storage->header.data();
                void *entry{};
                NativeFault fault{};
                if (!tryLinkXAssetEntry(
                        reinterpret_cast<void *>(dbLinkXAssetEntry_),
                        MaterialAssetType, &linkedHeader, entry, fault) ||
                    !entry || !linkedHeader ||
                    !trySetXAssetEntryZone(
                        entry, *retainedBarrettZone, fault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "material link fault name=%s rva=0x%07X op=%u "
                        "target=0x%08X code=0x%08X",
                        storage->name.data(),
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }
                storage->linked = linkedHeader;
                if (findXAsset(
                        MaterialAssetType, storage->name.data(), false).data !=
                    storage->linked)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed,
                        "material lookup differs after link: " +
                            std::string(storage->name.data()));
                }
            }

            constexpr std::uint32_t XModelSurfsAssetType = 3;
            constexpr std::size_t ScriptStringInternRva = 0x34BD10;
            constexpr std::size_t XModelStreamQueueRva = 0x09A2B0;
            const auto exactPrefix = [this](
                                         const std::size_t rva,
                                         const std::initializer_list<std::uint8_t>
                                             expected) {
                return readableSpan(module_ + rva, expected.size()) &&
                    std::equal(expected.begin(), expected.end(), module_ + rva);
            };
            if (!exactPrefix(ScriptStringInternRva,
                    { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x14 }) ||
                !exactPrefix(XModelStreamQueueRva,
                    { 0x55, 0x8B, 0xEC, 0xA1 }))
            {
                return failBarrettAssets(
                    AlphaWeaponPortStatus::InvalidDefinition,
                    "XModel helper bytes differ");
            }

            publishedBarrettAssets.animations.reserve(bundle->animations.size());
            for (const auto &source : bundle->animations)
            {
                auto storage = std::make_unique<PublishedBarrettAnimation>();
                if (source.name.size() + 1 > storage->name.size())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XAnim name is too long: " + source.name);
                }
                std::copy(source.name.begin(), source.name.end(),
                    storage->name.begin());
                storage->sourceName = source.sourceName;
                storage->header = source.header;
                storage->notify = source.notify;
                storage->dataByte = source.dataByte;
                storage->dataShort = source.dataShort;
                storage->dataInt = source.dataInt;
                storage->randomDataShort = source.randomDataShort;
                storage->randomDataByte = source.randomDataByte;
                storage->randomDataInt = source.randomDataInt;
                storage->indices = source.indices;
                storage->boneNames.resize(source.boneNames.size());

                for (std::size_t index{}; index < source.boneNames.size(); ++index)
                {
                    NativeFault fault{};
                    if (!tryInternScriptString(module_ + ScriptStringInternRva,
                            source.boneNames[index].c_str(),
                            storage->boneNames[index], fault))
                    {
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::LinkFailed,
                            "XAnim bone intern failed animation=" + source.name +
                                " bone=" + source.boneNames[index]);
                    }
                }
                for (std::size_t index{}; index < source.notifyNames.size(); ++index)
                {
                    std::uint16_t interned{};
                    NativeFault fault{};
                    if (!tryInternScriptString(module_ + ScriptStringInternRva,
                            source.notifyNames[index].c_str(), interned, fault))
                    {
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::LinkFailed,
                            "XAnim notify intern failed animation=" + source.name +
                                " notify=" + source.notifyNames[index]);
                    }
                    std::memcpy(storage->notify.data() + index * 8,
                        &interned, sizeof(interned));
                }

                const auto setAnimationPointer = [&address32, &source, &storage](
                                                     const std::size_t pointer,
                                                     const void *const data,
                                                     const bool empty) {
                    if (!source.pointerPresence[pointer])
                        return true;
                    const auto target = empty
                        ? static_cast<const void *>(
                              storage->emptyStreamSentinel.data())
                        : data;
                    const auto address = address32(target);
                    if (!address)
                        return false;
                    std::memcpy(storage->header.data() + 48 + pointer * 4,
                        &*address, sizeof(*address));
                    return true;
                };
                const auto nameAddress = address32(storage->name.data());
                if (!nameAddress)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XAnim name address is invalid: " + source.name);
                }
                std::memcpy(storage->header.data(),
                    &*nameAddress, sizeof(*nameAddress));
                if (!setAnimationPointer(0, storage->boneNames.data(),
                        storage->boneNames.empty()) ||
                    !setAnimationPointer(1, storage->dataByte.data(),
                        storage->dataByte.empty()) ||
                    !setAnimationPointer(2, storage->dataShort.data(),
                        storage->dataShort.empty()) ||
                    !setAnimationPointer(3, storage->dataInt.data(),
                        storage->dataInt.empty()) ||
                    !setAnimationPointer(4, storage->randomDataShort.data(),
                        storage->randomDataShort.empty()) ||
                    !setAnimationPointer(5, storage->randomDataByte.data(),
                        storage->randomDataByte.empty()) ||
                    !setAnimationPointer(6, storage->randomDataInt.data(),
                        storage->randomDataInt.empty()) ||
                    !setAnimationPointer(7, storage->indices.data(),
                        storage->indices.empty()) ||
                    !setAnimationPointer(8, storage->notify.data(),
                        storage->notify.empty()))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XAnim stream address is invalid: " + source.name);
                }

                void *linkedHeader = storage->header.data();
                void *entry{};
                NativeFault fault{};
                if (!tryLinkXAssetEntry(
                    reinterpret_cast<void *>(dbLinkXAssetEntry_),
                        XAnimAssetType, &linkedHeader, entry, fault) ||
                    !entry || !linkedHeader ||
                    !trySetXAssetEntryZone(entry, *retainedBarrettZone, fault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "XAnim link fault name=%s rva=0x%07X op=%u "
                        "target=0x%08X code=0x%08X",
                        storage->name.data(),
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address - reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }
                storage->linked = findXAsset(
                    XAnimAssetType, storage->name.data(), false).data;
                if (!storage->linked || !readableSpan(storage->linked, 88))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed,
                        "XAnim lookup differs after link: " + source.name);
                }
                publishedBarrettAssets.animations.push_back(std::move(storage));
            }

            std::set<std::string, std::less<>> resourceNames;
            for (const auto &model : bundle->models)
                resourceNames.insert(model.resources.begin(), model.resources.end());
            std::map<std::string, PublishedBarrettSurfs *, std::less<>>
                surfsByName;
            publishedBarrettAssets.surfs.reserve(resourceNames.size());
            for (const auto &resourceName : resourceNames)
            {
                auto storage = std::make_unique<PublishedBarrettSurfs>();
                if (resourceName.size() + 1 > storage->name.size())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XModelSurfs name is too long: " + resourceName);
                }
                std::copy(resourceName.begin(), resourceName.end(),
                    storage->name.begin());
                const auto nameAddress = address32(storage->name.data());
                if (!nameAddress)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XModelSurfs name address is invalid: " + resourceName);
                }
                std::memcpy(storage->header.data(),
                    &*nameAddress, sizeof(*nameAddress));

                if (const auto existing = findXAsset(
                        XModelSurfsAssetType, storage->name.data(), false).data)
                {
                    storage->linked = existing;
                }
                else
                {
                    void *linkedHeader = storage->header.data();
                    void *entry{};
                    NativeFault fault{};
                    if (!tryLinkXAssetEntry(
                            reinterpret_cast<void *>(dbLinkXAssetEntry_),
                            XModelSurfsAssetType,
                            &linkedHeader, entry, fault) ||
                        !entry || !linkedHeader ||
                        !trySetXAssetEntryZone(
                            entry, *retainedBarrettZone, fault))
                    {
                        char detail[256]{};
                        std::snprintf(detail, sizeof(detail),
                            "XModelSurfs link fault name=%s rva=0x%07X "
                            "op=%u target=0x%08X code=0x%08X",
                            storage->name.data(),
                            fault.address >=
                                    reinterpret_cast<std::uint32_t>(module_)
                                ? fault.address -
                                      reinterpret_cast<std::uint32_t>(module_)
                                : fault.address,
                            fault.operation, fault.target, fault.code);
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::LinkFailed, detail);
                    }
                    storage->linked = linkedHeader;
                }
                if (findXAsset(
                        XModelSurfsAssetType,
                        storage->name.data(), false).data != storage->linked)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed,
                        "XModelSurfs lookup differs after link: " + resourceName);
                }
                surfsByName.emplace(resourceName, storage.get());
                publishedBarrettAssets.surfs.push_back(std::move(storage));
            }

            std::size_t retainedMaterialFallbacks{};
            const auto resolveBarrettMaterial = [this,
                                                    &retainedMaterialFallbacks,
                                                    &retainedBarrettMaterials,
                                                    &retainedBarrettMaterialNames](
                                                    const std::string &name) {
                if (retainedBarrettMaterialNames.contains(name))
                {
                    const auto retained = retainedBarrettMaterials.find(name);
                    if (retained != retainedBarrettMaterials.end())
                    {
                        ++retainedMaterialFallbacks;
                        return findXAsset(MaterialAssetType,
                            retained->second.c_str(), false).data;
                    }
                }
                if (const auto exact = findXAsset(
                        MaterialAssetType, name.c_str(), false).data)
                {
                    return exact;
                }
                ++retainedMaterialFallbacks;
                const char *fallback = "mc/mtl_weapon_m16";
                if (name.find("reticle") != std::string::npos)
                    fallback = "mc/mtl_ret_acog02_acota31ncm_alpha";
                else if (name.find("lens") != std::string::npos ||
                         name.find("screen") != std::string::npos)
                    fallback = "mc/mtl_weapon_lens_eot_exps";
                else if (name.find("acog") != std::string::npos)
                    fallback = "mc/mtl_weapon_acog_2_alpha";
                return findXAsset(MaterialAssetType, fallback, false).data;
            };
            const auto writePointer = [&address32](
                                          auto &destination,
                                          const std::size_t offset,
                                          const void *const pointer) {
                const auto address = address32(pointer);
                if (!address || offset + sizeof(*address) > destination.size())
                    return false;
                std::memcpy(destination.data() + offset,
                    &*address, sizeof(*address));
                return true;
            };

            publishedBarrettAssets.models.reserve(bundle->models.size());
            for (const auto &source : bundle->models)
            {
                auto storage = std::make_unique<PublishedBarrettModel>();
                if (source.name.size() + 1 > storage->name.size())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XModel name is too long: " + source.name);
                }
                std::copy(source.name.begin(), source.name.end(),
                    storage->name.begin());
                storage->header = source.header;
                const auto skeleton = bundle->skeletons.find(source.skeletonKey);
                if (skeleton == bundle->skeletons.end())
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XModel skeleton is missing: " + source.skeletonKey);
                }
                storage->parentList = skeleton->second.parentList;
                storage->quaternions = skeleton->second.quaternions;
                storage->translations = skeleton->second.translations;
                storage->partClassification =
                    skeleton->second.partClassification;
                storage->baseMatrices = skeleton->second.baseMatrices;
                storage->boneInfo = source.boneInfo;
                storage->boneNames.resize(skeleton->second.boneNames.size());
                for (std::size_t index{};
                     index < skeleton->second.boneNames.size(); ++index)
                {
                    NativeFault fault{};
                    if (!tryInternScriptString(
                            module_ + ScriptStringInternRva,
                            skeleton->second.boneNames[index].c_str(),
                            storage->boneNames[index], fault))
                    {
                        char detail[256]{};
                        std::snprintf(detail, sizeof(detail),
                            "script-string intern failed model=%s bone=%s "
                            "rva=0x%07X code=0x%08X",
                            source.name.c_str(),
                            skeleton->second.boneNames[index].c_str(),
                            fault.address >=
                                    reinterpret_cast<std::uint32_t>(module_)
                                ? fault.address -
                                      reinterpret_cast<std::uint32_t>(module_)
                                : fault.address,
                            fault.code);
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::LinkFailed, detail);
                    }
                }

                storage->materials.reserve(source.materials.size());
                for (const auto &materialName : source.materials)
                {
                    const auto material = resolveBarrettMaterial(materialName);
                    if (!material)
                    {
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::SourceAssetMissing,
                            "XModel material is missing: " + materialName);
                    }
                    storage->materials.push_back(material);
                }

                if (!writePointer(storage->header, 0, storage->name.data()) ||
                    !writePointer(storage->header, 44,
                        storage->boneNames.data()) ||
                    !writePointer(storage->header, 48,
                        storage->parentList.data()) ||
                    !writePointer(storage->header, 52,
                        storage->quaternions.data()) ||
                    !writePointer(storage->header, 56,
                        storage->translations.data()) ||
                    !writePointer(storage->header, 60,
                        storage->partClassification.data()) ||
                    !writePointer(storage->header, 64,
                        storage->baseMatrices.data()) ||
                    !writePointer(storage->header, 68,
                        storage->materials.data()) ||
                    !writePointer(storage->header, 312,
                        storage->boneInfo.data()))
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::InvalidDefinition,
                        "XModel storage address is invalid: " + source.name);
                }
                for (std::size_t lod{}; lod < source.resources.size(); ++lod)
                {
                    const auto surfs = surfsByName.find(source.resources[lod]);
                    if (surfs == surfsByName.end() ||
                        !writePointer(storage->header, 72 + lod * 56 + 8,
                            surfs->second->linked) ||
                        !writePointer(storage->header, 72 + lod * 56 + 12,
                            surfs->second->name.data()))
                    {
                        return failBarrettAssets(
                            AlphaWeaponPortStatus::InvalidDefinition,
                            "XModel resource is invalid: " + source.resources[lod]);
                    }
                }

                void *linkedHeader = storage->header.data();
                void *entry{};
                NativeFault fault{};
                if (!tryLinkXAssetEntry(
                        reinterpret_cast<void *>(dbLinkXAssetEntry_),
                        XModelAssetType, &linkedHeader, entry, fault) ||
                    !entry || !linkedHeader ||
                    !trySetXAssetEntryZone(
                        entry, *retainedBarrettZone, fault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "XModel link fault name=%s rva=0x%07X op=%u "
                        "target=0x%08X code=0x%08X",
                        source.name.c_str(),
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }
                storage->linked = linkedHeader;

                if (findXAsset(
                        XModelAssetType, storage->name.data(), false).data !=
                    storage->linked)
                {
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed,
                        "XModel lookup differs after link: " + source.name);
                }
                publishedBarrettAssets.models.push_back(std::move(storage));
            }

            for (const auto &storage : publishedBarrettAssets.models)
            {
                NativeFault queueFault{};
                if (!tryQueueXModelStream(
                        module_ + XModelStreamQueueRva,
                        storage->linked, 0, queueFault))
                {
                    char detail[256]{};
                    std::snprintf(detail, sizeof(detail),
                        "native XModel stream queue fault name=%s "
                        "rva=0x%07X op=%u target=0x%08X code=0x%08X",
                        storage->name.data(),
                        queueFault.address >=
                                reinterpret_cast<std::uint32_t>(module_)
                            ? queueFault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : queueFault.address,
                        queueFault.operation, queueFault.target,
                        queueFault.code);
                    return failBarrettAssets(
                        AlphaWeaponPortStatus::LinkFailed, detail);
                }
            }

            // Queue every linked type-4 asset through the engine's model-
            // stream worker. Do
            // not call the three post-link helpers here: racing that worker
            // lets two loaders see the same null XModelSurfs pointer and can
            // hand the renderer a null index source. Wait for the native
            // attach -> renderer init -> LOD rebuild sequence instead. Bit 3
            // at XModel +349 is set only by the final rebuild step.
            constexpr DWORD StreamWaitMilliseconds = 15000;
            const auto streamDeadline = GetTickCount64() +
                StreamWaitMilliseconds;
            bool streamsReady{};
            do
            {
                streamsReady = std::ranges::all_of(
                    publishedBarrettAssets.surfs,
                    [this](const auto &storage) {
                        const auto *const linked = static_cast<
                            const std::byte *>(storage->linked);
                        void *surfaces{};
                        std::uint16_t surfaceCount{};
                        if (!readableSpan(linked, storage->header.size()))
                            return false;
                        std::memcpy(
                            &surfaces, linked + 4, sizeof(surfaces));
                        std::memcpy(
                            &surfaceCount, linked + 8, sizeof(surfaceCount));
                        return surfaces && surfaceCount;
                    }) &&
                    std::ranges::all_of(
                        publishedBarrettAssets.models,
                        [this](const auto &storage) {
                            const auto *const linked = static_cast<
                                const std::byte *>(storage->linked);
                            return readableSpan(linked, 350) &&
                                (static_cast<std::uint8_t>(linked[349]) &
                                    0x08u) != 0;
                        });
                if (!streamsReady)
                {
                    Sleep(1);
                }
            }
            while (!streamsReady && GetTickCount64() < streamDeadline);
            if (!streamsReady)
            {
                return failBarrettAssets(
                    AlphaWeaponPortStatus::LinkFailed,
                    "native XModel streaming did not finish within 15 seconds");
            }

            publishedBarrettAssets.ready = true;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "alpha Barrett asset closure ready images=" +
                    std::to_string(publishedBarrettAssets.images.size()) +
                    " materials=" +
                    std::to_string(publishedBarrettAssets.materials.size()) +
                    " surfs=" +
                    std::to_string(publishedBarrettAssets.surfs.size()) +
                    " models=" +
                    std::to_string(publishedBarrettAssets.models.size()) +
                    " safeMaterials=" +
                    std::to_string(retainedBarrettMaterialNames.size()) +
                    " retainedMaterialFallbacks=" +
                    std::to_string(retainedMaterialFallbacks));
        }

        const auto ports = SV_AlphaWeaponPorts();
        for (std::size_t portIndex{}; portIndex < ports.size(); ++portIndex)
        {
            const auto &port = ports[portIndex];
            if (port.lineage == SvAlphaWeaponLineage::ConvertedPresentation &&
                !barrettMetadataEnabled)
            {
                continue;
            }
            if (port.lineage == SvAlphaWeaponLineage::ConvertedPresentation &&
                !publishedBarrettAssets.ready)
            {
                return publish(AlphaWeaponPortStatus::SourceAssetMissing);
            }
            if (port.lineage == SvAlphaWeaponLineage::MissingModelFamily)
                continue;
            if (!port.alphaName || !*port.alphaName || !port.sourceName ||
                !*port.sourceName)
            {
                return publish(AlphaWeaponPortStatus::InvalidDefinition);
            }
            // The requested 0.0.2.2 presentation is composite. Its directly
            // serialized viewmodel_barrett uses viewmodel_m8210, while the
            // exact mp/coWeapModels/barrett_mp.csv row adds the matching
            // wea_barrett_barrett_*_vmgun body. Both meshes share weapon-space
            // coordinates and the alpha archive carries the four measured
            // material variants. Publish the converted table for Barrett just
            // like the retained model tables used by the compatibility ports.
            const auto modelTableStatus = ensureModelTable(port, portIndex);
            if (modelTableStatus != AlphaWeaponPortStatus::Ready)
                return modelTableStatus;

            auto target = findXAsset(
                WeaponAssetType, port.alphaName, false).data;
            if (!target)
            {
                const auto source = findXAsset(
                    WeaponAssetType, port.sourceName, false).data;
                if (!source || !readableSpan(source, OlfinalWeaponDefSize))
                {
                    return publish(AlphaWeaponPortStatus::SourceAssetMissing);
                }

                std::array<std::byte, OlfinalWeaponDefSize> definition{};
                std::memcpy(definition.data(), source, definition.size());
                const auto nameAddress = reinterpret_cast<std::uintptr_t>(
                    port.alphaName);
                if (nameAddress > std::numeric_limits<std::uint32_t>::max() ||
                    !SV_PatchAlphaWeaponDefinition(
                        definition,
                        static_cast<std::uint32_t>(nameAddress),
                        port.tuning))
                {
                    return publish(AlphaWeaponPortStatus::InvalidDefinition);
                }

                if (port.lineage == SvAlphaWeaponLineage::ConvertedPresentation)
                {
                    // CODREF(alpha_weapondef): the alpha loader keeps sixteen
                    // first-person XModels at +0x14 and sixteen world XModels
                    // at +0x54. Barrett selects viewmodel_barrett and weapon_m82
                    // in element zero of those arrays. OLfinal reduced the two
                    // arrays to two entries apiece at +0x10/+0x14 and
                    // +0x18/+0x1C. The retained CheyTac clone has tag_origin in
                    // both element-zero fields. Install the complete alpha base
                    // pair before linking the WeaponDef; keep the alternate
                    // element and the six later auxiliary models source-owned.
                    constexpr std::size_t ViewModelOffset = 0x10;
                    constexpr std::size_t WorldModelOffset = 0x18;
                    const auto viewModel = findXAsset(
                        XModelAssetType, "viewmodel_barrett", false).data;
                    const auto worldModel = findXAsset(
                        XModelAssetType, "weapon_m82", false).data;
                    const auto viewModelAddress =
                        reinterpret_cast<std::uintptr_t>(viewModel);
                    const auto worldModelAddress =
                        reinterpret_cast<std::uintptr_t>(worldModel);
                    if (!viewModel || !worldModel ||
                        viewModelAddress >
                            std::numeric_limits<std::uint32_t>::max() ||
                        worldModelAddress >
                            std::numeric_limits<std::uint32_t>::max())
                    {
                        return publish(AlphaWeaponPortStatus::SourceAssetMissing);
                    }
                    const auto viewModelAddress32 =
                        static_cast<std::uint32_t>(viewModelAddress);
                    const auto worldModelAddress32 =
                        static_cast<std::uint32_t>(worldModelAddress);
                    std::memcpy(definition.data() + ViewModelOffset,
                        &viewModelAddress32, sizeof(viewModelAddress32));
                    std::memcpy(definition.data() + WorldModelOffset,
                        &worldModelAddress32, sizeof(worldModelAddress32));

                    struct AnimationSlot
                    {
                        std::size_t slot;
                        std::string_view name;
                    };
                    // Exact alpha Barrett array-0 identities. The 0.0.2.2
                    // WeaponDef loader reads 48 XStrings at +0xEC. Its packed
                    // block-3 pointers advance in the same order as the
                    // directly serialized viewmodel_barrett XAnimParts; the
                    // three inline strings at 34/46/47 corroborate ADS fire,
                    // up and down independently. OLfinal extends this enum to
                    // 62 without reordering these original slots.
                    constexpr std::array AnimationSlots{
                        AnimationSlot{ 1, "alpha_barrett_idle" },
                        AnimationSlot{ 2, "alpha_barrett_idle" },
                        AnimationSlot{ 3, "alpha_barrett_fire" },
                        AnimationSlot{ 5, "alpha_barrett_fire" },
                        AnimationSlot{ 9, "alpha_barrett_reload" },
                        AnimationSlot{ 11, "alpha_barrett_reload_empty" },
                        AnimationSlot{ 15, "alpha_barrett_pullout" },
                        AnimationSlot{ 16, "alpha_barrett_pullout" },
                        AnimationSlot{ 17, "alpha_barrett_breach" },
                        AnimationSlot{ 18, "alpha_barrett_putaway" },
                        AnimationSlot{ 21, "alpha_barrett_pullout_quick" },
                        AnimationSlot{ 22, "alpha_barrett_putaway_quick" },
                        AnimationSlot{ 23, "alpha_barrett_pullout" },
                        AnimationSlot{ 24, "alpha_barrett_putaway" },
                        AnimationSlot{ 25, "alpha_barrett_sprint_in" },
                        AnimationSlot{ 26, "alpha_barrett_sprint_loop" },
                        AnimationSlot{ 27, "alpha_barrett_sprint_out" },
                        AnimationSlot{ 34, "alpha_barrett_ads_fire" },
                        AnimationSlot{ 35, "alpha_barrett_ads_fire" },
                        AnimationSlot{ 46, "alpha_barrett_ads_up" },
                        AnimationSlot{ 47, "alpha_barrett_ads_down" },
                    };
                    constexpr std::size_t AnimationArrayOffset = 0x7C;
                    std::set<std::string_view> closedAnimations;
                    for (const auto &[slot, name] : AnimationSlots)
                    {
                        const auto animation = std::ranges::find_if(
                            publishedBarrettAssets.animations,
                            [name](const auto &candidate) {
                                return candidate->name.data() == name;
                            });
                        if (animation == publishedBarrettAssets.animations.end())
                        {
                            return publish(
                                AlphaWeaponPortStatus::InvalidDefinition);
                        }
                        const auto replacement = reinterpret_cast<std::uintptr_t>(
                            (*animation)->name.data());
                        if (replacement >
                            std::numeric_limits<std::uint32_t>::max())
                        {
                            return publish(
                                AlphaWeaponPortStatus::InvalidDefinition);
                        }
                        const auto replacement32 =
                            static_cast<std::uint32_t>(replacement);
                        std::memcpy(definition.data() + AnimationArrayOffset +
                                slot * sizeof(replacement32),
                            &replacement32, sizeof(replacement32));
                        closedAnimations.insert(name);
                    }
                    if (closedAnimations.size() !=
                        publishedBarrettAssets.animations.size())
                        return publish(AlphaWeaponPortStatus::InvalidDefinition);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "alpha Barrett WeaponDef XAnim slots patched assets=" +
                            std::to_string(closedAnimations.size()) +
                            " slots=" + std::to_string(AnimationSlots.size()) +
                            " viewModel=viewmodel_barrett worldModel=weapon_m82");
                }

                void *linkedHeader = definition.data();
                void *entry{};
                NativeFault fault{};
                if (!tryLinkXAssetEntry(
                        reinterpret_cast<void *>(dbLinkXAssetEntry_),
                        WeaponAssetType,
                        &linkedHeader,
                        entry,
                        fault) ||
                    !entry || !linkedHeader)
                {
                    char failure[256]{};
                    std::snprintf(
                        failure, sizeof(failure),
                        "alpha weapon link failed name=%s source=%s "
                        "rva=0x%07X op=%u target=0x%08X code=0x%08X",
                        port.alphaName, port.sourceName,
                        fault.address >=
                                reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.operation, fault.target, fault.code);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, failure);
                    return publish(AlphaWeaponPortStatus::LinkFailed);
                }

                // DB_LinkXAssetEntry allocates with the current loading-zone
                // byte. At this late runtime boundary that byte is zero, which
                // makes an otherwise valid new WeaponDef a default placeholder
                // and causes the native resolver to reject it. Give the clone
                // its retained source's resident zone before asking the DB or
                // weapon registry for it. This is the same ownership lifetime
                // as every shallow pointer copied from that source definition.
                const auto sourceZone = assetZoneForHeader(
                    WeaponAssetType, source);
                if (!sourceZone || !trySetXAssetEntryZone(
                        entry, *sourceZone, fault))
                {
                    char failure[256]{};
                    std::snprintf(
                        failure, sizeof(failure),
                        "alpha weapon zone promotion failed name=%s source=%s "
                        "zone=%u rva=0x%07X code=0x%08X",
                        port.alphaName, port.sourceName,
                        sourceZone ? *sourceZone : 0,
                        fault.address >= reinterpret_cast<std::uint32_t>(module_)
                            ? fault.address -
                                  reinterpret_cast<std::uint32_t>(module_)
                            : fault.address,
                        fault.code);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, failure);
                    return publish(AlphaWeaponPortStatus::LinkFailed);
                }

                target = findXAsset(
                    WeaponAssetType, port.alphaName, false).data;
                // A failed lookup earlier in session setup can leave a default
                // entry for this name. Linking the real definition replaces
                // that entry's engine-owned header, so DB lookup may correctly
                // return a different pointer than the linker's transient
                // output. findXAsset already rejects default entries; require
                // the resolved header and its full WeaponDef extent here.
                if (!target || !readableSpan(target, OlfinalWeaponDefSize))
                {
                    char failure[256]{};
                    std::snprintf(
                        failure, sizeof(failure),
                        "alpha weapon post-link verification failed name=%s "
                        "lookup=%p linked=%p readable=%u",
                        port.alphaName, target, linkedHeader,
                        target && readableSpan(target, OlfinalWeaponDefSize)
                            ? 1u
                            : 0u);
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, failure);
                    return publish(AlphaWeaponPortStatus::LinkFailed);
                }
            }

            std::uint32_t index{};
            NativeFault fault{};
            if (!tryWeaponResolve(
                    reinterpret_cast<void *>(weaponResolver_),
                    port.alphaName,
                    index,
                    fault) ||
                !index || index > MaximumWeaponAssetIndex ||
                weaponLookup_(port.alphaName) != index)
            {
                char failure[224]{};
                std::snprintf(
                    failure, sizeof(failure),
                    "alpha weapon registration failed name=%s index=%u "
                    "rva=0x%07X op=%u target=0x%08X code=0x%08X",
                    port.alphaName, index,
                    fault.address >= reinterpret_cast<std::uint32_t>(module_)
                        ? fault.address -
                              reinterpret_cast<std::uint32_t>(module_)
                        : fault.address,
                    fault.operation, fault.target, fault.code);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, failure);
                return publish(AlphaWeaponPortStatus::RegistrationFailed);
            }
            if (!markAlphaBaseWeapon(index))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "alpha weapon base configstring type failed name=" +
                        std::string(port.alphaName) + " index=" +
                        std::to_string(index));
                return publish(AlphaWeaponPortStatus::RegistrationFailed);
            }

        }
        return publish(AlphaWeaponPortStatus::Ready);
    }

    void EngineBindings::auditAlphaWeaponModelPointers() const
    {
        const auto enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_ALPHA_WEAPON_MODEL_AUDIT",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        if (!enabled ||
            alphaWeaponModelAuditComplete_.load(std::memory_order_acquire) ||
            !module_ || !zoneLoaded_ || !dbFindXAssetHeader_ ||
            gameThreadId_.load(std::memory_order_acquire) !=
                GetCurrentThreadId() ||
            !zoneLoaded_("common_mp"))
        {
            return;
        }

        constexpr std::uint32_t WeaponAssetType = 28;
        constexpr std::uint32_t XModelAssetType = 4;
        constexpr std::array<std::size_t, 10> ModelOffsets{
            16, 20, 24, 28, 32, 36, 40, 44, 48, 52,
        };
        const auto *const definition = static_cast<const std::byte *>(
            findXAsset(WeaponAssetType, "cheytac_mp", false).data);
        if (!readableSpan(definition, ModelOffsets.back() + sizeof(void *)))
            return;

        std::string report = "alpha weapon model audit weapon=cheytac_mp";
        for (const auto offset : ModelOffsets)
        {
            const void *model{};
            std::memcpy(&model, definition + offset, sizeof(model));
            std::optional<std::string> name;
            if (readableSpan(model, sizeof(const char *)))
            {
                const char *namePointer{};
                std::memcpy(&namePointer, model, sizeof(namePointer));
                name = readCString(namePointer, 128);
            }
            char field[192]{};
            std::snprintf(
                field, sizeof(field), " +0x%02zX=%s@%p", offset,
                name ? name->c_str() : model ? "<unreadable>" : "<null>",
                model);
            report += field;
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, report);

        const auto auditModelTable = [this](
                                             const std::string_view weaponName)
            -> std::optional<std::pair<std::string, const std::byte *>> {
            std::array<char, 96> path{};
            const auto length = std::snprintf(
                path.data(), path.size(), "mp/coWeapModels/%.*s.csv",
                static_cast<int>(weaponName.size()), weaponName.data());
            if (length <= 0 || static_cast<std::size_t>(length) >= path.size())
                return std::nullopt;
            const auto *const table = readStringTable(
                dbFindXAssetHeader_, dbIsXAssetDefault_, path.data(), 4);
            if (!table)
                return std::nullopt;
            const auto row = findStringTableRow(*table, weaponName);
            if (!row || !*row)
                return std::nullopt;
            const auto viewName = readStringTableCell((*row)[3]);
            if (!viewName || viewName->empty())
                return std::nullopt;
            const auto *const model = static_cast<const std::byte *>(findXAsset(
                XModelAssetType, viewName->c_str(), false).data);
            if (!readableSpan(model, 360))
                return std::nullopt;
            return std::pair{*viewName, model};
        };
        const auto auditRig = [this](
                                  const std::string_view weaponName,
                                  const std::string_view modelName,
                                  const std::byte *const model) {
            const auto boneCount = static_cast<std::uint8_t>(model[4]);
            const auto rootCount = static_cast<std::uint8_t>(model[5]);
            const auto surfaceCount = static_cast<std::uint8_t>(model[6]);
            const std::uint16_t *boneNames{};
            const std::uint8_t *parents{};
            const std::int16_t *quaternions{};
            const float *translations{};
            const float *baseMatrices{};
            std::memcpy(&boneNames, model + 44, sizeof(boneNames));
            std::memcpy(&parents, model + 48, sizeof(parents));
            std::memcpy(&quaternions, model + 52, sizeof(quaternions));
            std::memcpy(&translations, model + 56, sizeof(translations));
            std::memcpy(&baseMatrices, model + 64, sizeof(baseMatrices));
            const auto childCount = boneCount >= rootCount
                ? static_cast<std::size_t>(boneCount - rootCount)
                : 0;
            std::string rig = "alpha weapon rig audit weapon=" +
                std::string(weaponName) + " model=" + std::string(modelName) +
                " bones=" + std::to_string(boneCount) + " roots=" +
                std::to_string(rootCount) + " surfaces=" +
                std::to_string(surfaceCount);
            if (!boneCount || rootCount > boneCount ||
                !readableSpan(boneNames, boneCount * sizeof(*boneNames)) ||
                (childCount &&
                    (!readableSpan(parents, childCount) ||
                        !readableSpan(
                            quaternions, childCount * 4 * sizeof(*quaternions)) ||
                        !readableSpan(
                            translations, childCount * 3 * sizeof(*translations)))) ||
                !readableSpan(
                    baseMatrices, static_cast<std::size_t>(boneCount) * 8 *
                        sizeof(*baseMatrices)))
            {
                rig += " storage=<invalid>";
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, rig);
                return;
            }
            rig += " names=";
            for (std::size_t index{}; index < boneCount; ++index)
            {
                if (index)
                    rig += ',';
                const auto name = internedAttachmentName(boneNames[index]);
                rig += name ? *name : "#" + std::to_string(boneNames[index]);
                if (index >= rootCount)
                {
                    rig += "<" + std::to_string(parents[index - rootCount]);
                }
            }
            rig += " bindT=";
            for (std::size_t index{}; index < boneCount; ++index)
            {
                if (index)
                    rig += ';';
                const auto *const matrix = baseMatrices + index * 8;
                char transform[96]{};
                std::snprintf(
                    transform, sizeof(transform), "%zu:%.3f,%.3f,%.3f",
                    index, matrix[4], matrix[5], matrix[6]);
                rig += transform;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, rig);
        };

        const auto cheytacRig = auditModelTable("cheytac_mp");
        const auto barrettRig = auditModelTable("barrett_mp");
        if (!cheytacRig || !barrettRig)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "alpha weapon rig audit waiting cheytac=" +
                    std::to_string(cheytacRig.has_value()) + " barrett=" +
                    std::to_string(barrettRig.has_value()));
            return;
        }
        auditRig("cheytac_mp", cheytacRig->first, cheytacRig->second);
        auditRig("barrett_mp", barrettRig->first, barrettRig->second);
        alphaWeaponModelAuditComplete_.store(true, std::memory_order_release);
    }

    void EngineBindings::auditXModelSurfaces() const
    {
        const auto enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_XMODEL_SURFACE_AUDIT",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        if (!enabled ||
            xmodelSurfaceAuditComplete_.load(std::memory_order_acquire) ||
            !module_ || !zoneLoaded_ || !dbFindXAssetHeader_ ||
            gameThreadId_.load(std::memory_order_acquire) !=
                GetCurrentThreadId() ||
            !zoneLoaded_("common_mp"))
        {
            return;
        }

        constexpr std::uint32_t XModelAssetType = 4;
        constexpr std::size_t XModelLod0ModelSurfsOffset = 0x50;
        constexpr std::size_t XModelSurfsSize = 0x30;
        constexpr std::size_t XModelSurfsNameOffset = 0x00;
        constexpr std::size_t XModelSurfsSurfacesOffset = 0x04;
        constexpr std::size_t XModelSurfsCountOffset = 0x08;
        constexpr std::size_t XSurfaceSize = 0x54;
        constexpr std::size_t XSurfaceVertCountOffset = 0x04;
        constexpr std::size_t XSurfaceTriCountOffset = 0x06;
        constexpr std::size_t XSurfaceBlendCountsOffset = 0x14;
        constexpr std::size_t XSurfaceBlendPointerOffset = 0x1C;
        constexpr std::size_t XSurfaceVertexPointerOffset = 0x20;
        constexpr std::size_t XSurfaceRigidListCountOffset = 0x28;
        constexpr std::size_t XSurfaceRigidListPointerOffset = 0x2C;
        constexpr std::size_t XSurfaceIndexPointerOffset = 0x10;
        constexpr std::size_t PackedVertexSize = 0x20;
        constexpr std::size_t RigidVertListSize = 0x0C;
        constexpr std::uint16_t MaximumSurfaceCount = 64;

        const auto fail = [this](const std::string &reason) {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "xmodel surface audit: " + reason);
            xmodelSurfaceAuditComplete_.store(true, std::memory_order_release);
        };
        const auto *const model = static_cast<const std::byte *>(findXAsset(
            XModelAssetType, "viewmodel_riot_shield_mp", false).data);
        if (!readableSpan(
                model, XModelLod0ModelSurfsOffset + sizeof(void *)))
        {
            return;
        }

        const std::byte *modelSurfs{};
        std::memcpy(
            &modelSurfs, model + XModelLod0ModelSurfsOffset,
            sizeof(modelSurfs));
        if (!readableSpan(modelSurfs, XModelSurfsSize))
        {
            return;
        }

        const char *namePointer{};
        const std::byte *surfaces{};
        std::uint16_t surfaceCount{};
        std::memcpy(
            &namePointer, modelSurfs + XModelSurfsNameOffset,
            sizeof(namePointer));
        std::memcpy(
            &surfaces, modelSurfs + XModelSurfsSurfacesOffset,
            sizeof(surfaces));
        std::memcpy(
            &surfaceCount, modelSurfs + XModelSurfsCountOffset,
            sizeof(surfaceCount));
        const auto name = readCString(namePointer, 128);
        if (!name || surfaceCount > MaximumSurfaceCount)
        {
            fail("invalid XModelSurfs header");
            return;
        }
        // XModelSurfs is a fastfile placeholder until the loose main/models
        // resource streams. Keep waiting instead of consuming the one-shot
        // audit before the control has ever been rendered.
        if (!surfaceCount || !surfaces)
            return;
        if (!readableSpan(
                surfaces, static_cast<std::size_t>(surfaceCount) * XSurfaceSize))
        {
            fail("unreadable XModelSurfs array");
            return;
        }

        const auto fileName = L"xmodel-surfaces-" +
            std::to_wstring(GetCurrentProcessId()) + L".bin";
        const auto path = diagnosticPath(fileName.c_str());
        std::ofstream output(path, std::ios::binary | std::ios::trunc);
        if (!output)
        {
            fail("cannot open output " + path.string());
            return;
        }

        const auto writeU32 = [&output](const std::uint32_t value) {
            output.write(
                reinterpret_cast<const char *>(&value), sizeof(value));
        };
        output.write("OLXSAUD1", 8);
        writeU32(1);
        writeU32(surfaceCount);
        writeU32(static_cast<std::uint32_t>(XSurfaceSize));
        writeU32(static_cast<std::uint32_t>(name->size()));
        output.write(name->data(), static_cast<std::streamsize>(name->size()));

        for (std::uint16_t index{}; index < surfaceCount; ++index)
        {
            const auto *const surface = surfaces +
                static_cast<std::size_t>(index) * XSurfaceSize;
            std::uint16_t vertCount{};
            std::uint16_t triCount{};
            std::array<std::uint16_t, 4> blendCounts{};
            std::uint32_t rigidListCount{};
            const std::byte *blendData{};
            const std::byte *vertexData{};
            const std::byte *rigidListData{};
            const std::byte *indexData{};
            std::memcpy(
                &vertCount, surface + XSurfaceVertCountOffset,
                sizeof(vertCount));
            std::memcpy(
                &triCount, surface + XSurfaceTriCountOffset,
                sizeof(triCount));
            std::memcpy(
                blendCounts.data(), surface + XSurfaceBlendCountsOffset,
                sizeof(blendCounts));
            std::memcpy(
                &blendData, surface + XSurfaceBlendPointerOffset,
                sizeof(blendData));
            std::memcpy(
                &vertexData, surface + XSurfaceVertexPointerOffset,
                sizeof(vertexData));
            std::memcpy(
                &rigidListCount, surface + XSurfaceRigidListCountOffset,
                sizeof(rigidListCount));
            std::memcpy(
                &rigidListData, surface + XSurfaceRigidListPointerOffset,
                sizeof(rigidListData));
            std::memcpy(
                &indexData, surface + XSurfaceIndexPointerOffset,
                sizeof(indexData));

            const auto blendWordCount =
                static_cast<std::size_t>(blendCounts[0]) +
                3u * blendCounts[1] + 5u * blendCounts[2] +
                7u * blendCounts[3];
            const auto blendBytes = 2u * blendWordCount;
            const auto vertexBytes =
                static_cast<std::size_t>(vertCount) * PackedVertexSize;
            const auto rigidListBytes =
                static_cast<std::size_t>(rigidListCount) * RigidVertListSize;
            const auto indexBytes = static_cast<std::size_t>(triCount) * 6u;
            if ((blendBytes && !readableSpan(blendData, blendBytes)) ||
                (vertexBytes && !readableSpan(vertexData, vertexBytes)) ||
                (rigidListBytes &&
                    !readableSpan(rigidListData, rigidListBytes)) ||
                (indexBytes && !readableSpan(indexData, indexBytes)))
            {
                output.close();
                std::error_code ignored;
                std::filesystem::remove(path, ignored);
                fail("unreadable CPU geometry on surface " +
                    std::to_string(index));
                return;
            }

            writeU32(XSurfaceSize);
            output.write(
                reinterpret_cast<const char *>(surface), XSurfaceSize);
            const auto writeSpan = [&output, &writeU32](
                                       const std::byte *data,
                                       const std::size_t size) {
                writeU32(static_cast<std::uint32_t>(size));
                if (size)
                {
                    output.write(
                        reinterpret_cast<const char *>(data),
                        static_cast<std::streamsize>(size));
                }
            };
            writeSpan(blendData, blendBytes);
            writeSpan(vertexData, vertexBytes);
            writeSpan(rigidListData, rigidListBytes);
            writeSpan(indexData, indexBytes);
        }
        output.flush();
        if (!output)
        {
            output.close();
            std::error_code ignored;
            std::filesystem::remove(path, ignored);
            fail("output write failed");
            return;
        }
        output.close();

        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "xmodel surface audit: model=viewmodel_riot_shield_mp surfs=" +
                *name + " count=" + std::to_string(surfaceCount) +
                " output=" + path.string());
        xmodelSurfaceAuditComplete_.store(true, std::memory_order_release);
    }

    void EngineBindings::auditAlphaBarrettAssetTemplates() const
    {
        // CODREF(1649370): Load_Material 0x00488250 reads a 104-byte header,
        // with its asset name at +0x10, texture count at +0x51, and texture
        // table at +0x5C. Load_GfxImage 0x00487380 reads a 52-byte header,
        // resolves its name at +0x30, and Load_GfxImageLoadDef 0x00487300
        // reads the 16-byte load definition reached through +0. The renderer
        // initializer 0x00BE7470 clears +0 and retains that definition at
        // +0x2C. Alpha Load_GfxImage 0x004B2E30 instead reads 32 bytes and
        // resolves its name at +0x1C. This diagnostic records the exact final
        // structures so the converter does not infer them from alpha's
        // incompatible layouts.
        constexpr std::uint32_t MaterialAssetType = 5;
        constexpr std::uint32_t GfxImageAssetType = 10;
        constexpr std::size_t MaterialHeaderSize = 104;
        constexpr std::size_t MaterialNameOffset = 0x10;
        constexpr std::size_t MaterialTextureCountOffset = 0x51;
        constexpr std::size_t MaterialTextureTableOffset = 0x5C;
        constexpr std::size_t MaterialTextureRowSize = 12;
        constexpr std::size_t MaterialTextureSemanticOffset = 7;
        constexpr std::size_t MaterialTextureImageOffset = 8;
        constexpr std::uint8_t WaterSemantic = 11;
        constexpr std::size_t GfxImageHeaderSize = 52;
        constexpr std::size_t GfxImageLoadDefOffset = 0x2C;
        constexpr std::size_t GfxImageNameOffset = 0x30;
        constexpr std::size_t GfxImageLoadDefSize = 16;
        constexpr std::size_t GfxImageLoadDefDataSizeOffset = 0x0C;
        constexpr std::size_t GfxImagePayloadHeadSize = 64;

        const auto log = [](const std::string &message) {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "alpha Barrett template audit: " + message);
        };
        if (!module_ || !dbFindXAssetHeader_ || !dbIsXAssetDefault_)
        {
            log("asset database bindings unavailable");
            return;
        }
        if (!zoneLoaded_ || !zoneLoaded_("common_mp"))
        {
            log("common_mp is not resident");
            return;
        }

        const auto path = diagnosticPath(
            (L"alpha-barrett-final-templates-" +
                std::to_wstring(GetCurrentProcessId()) + L".tsv").c_str());
        std::ofstream output(path, std::ios::trunc);
        if (!output)
        {
            log("cannot write " + path.string());
            return;
        }

        const auto hex = [](const void *const address,
                             const std::size_t length) {
            if (!address || !readableSpan(address, length))
                return std::string{ "<unreadable>" };
            static constexpr char Digits[] = "0123456789abcdef";
            const auto *const bytes = static_cast<const std::uint8_t *>(address);
            std::string result(length * 2, '0');
            for (std::size_t index{}; index < length; ++index)
            {
                result[index * 2] = Digits[bytes[index] >> 4];
                result[index * 2 + 1] = Digits[bytes[index] & 0xFu];
            }
            return result;
        };
        const auto pointerText = [](const void *const address) {
            char value[16]{};
            std::snprintf(value, sizeof(value), "0x%08X",
                static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(address)));
            return std::string{ value };
        };
        const auto safeName = [](const char *const name) {
            if (!name)
                return std::string{ "<null>" };
            if (!readableSpan(name, 1))
                return std::string{ "<unreadable>" };
            if (!*name)
                return std::string{ "<empty>" };
            return readCString(name, 256).value_or("<unreadable>");
        };

        output << "kind\towner\tindex\tname\taddress\theader_hex\tdata\n";
        std::set<const void *> writtenImages;
        std::size_t materialCount{};
        std::size_t textureCount{};
        std::size_t imageCount{};
        std::size_t missingCount{};

        // CODREF(1649370): DB_InitPool 0x0049C690 threads 120,000
        // 28-byte XAssetEntry rows starting at 0x0239B120. Enumerate only
        // resident Material rows and record likely optic controls. This keeps
        // the template list tied to names that actually exist in this build;
        // several alpha/IW4 material names are absent from OLfinal common_mp.
        constexpr std::size_t XAssetEntryPoolRva = 0x1F9B120;
        constexpr std::size_t XAssetEntryCount = 120000;
        constexpr std::size_t XAssetEntrySize = 28;
        constexpr std::size_t XAssetEntryTypeOffset = 0;
        constexpr std::size_t XAssetEntryDataOffset = 8;
        const auto *const assetEntries = module_ + XAssetEntryPoolRva;
        std::size_t opticCandidateCount{};
        for (std::size_t index{}; index < XAssetEntryCount; ++index)
        {
            const auto *const entry = assetEntries + index * XAssetEntrySize;
            if (!readableSpan(entry, XAssetEntrySize))
                break;
            std::uint32_t type{};
            const std::uint8_t *material{};
            std::memcpy(&type, entry + XAssetEntryTypeOffset, sizeof(type));
            std::memcpy(&material, entry + XAssetEntryDataOffset,
                sizeof(material));
            if (type != MaterialAssetType ||
                !readableSpan(material, MaterialNameOffset + sizeof(char *)))
            {
                continue;
            }
            const auto *const name =
                *reinterpret_cast<const char *const *>(
                    material + MaterialNameOffset);
            const auto materialName = safeName(name);
            const auto alphaLensCounts =
                material[0x51] == 3 && material[0x52] == 2 &&
                material[0x53] == 4;
            if (materialName.find("scope") == std::string::npos &&
                materialName.find("lens") == std::string::npos &&
                materialName.find("optic") == std::string::npos &&
                materialName.find("thermal") == std::string::npos &&
                materialName.find("acog") == std::string::npos &&
                !alphaLensCounts)
            {
                continue;
            }
            output << "material-candidate\tpool\t" << index << '\t'
                   << materialName << '\t' << pointerText(material)
                   << '\t' << hex(material, MaterialHeaderSize) << "\t\n";
            ++opticCandidateCount;
        }

        const auto writeImage = [&](const std::string_view owner,
                                    const void *const image) {
            if (!image || !writtenImages.insert(image).second)
                return;
            if (!readableSpan(image, GfxImageHeaderSize))
            {
                output << "image\t" << owner << "\t\t<unreadable>\t"
                       << pointerText(image) << "\t<unreadable>\t\n";
                return;
            }
            const auto *const imageBytes = static_cast<const std::uint8_t *>(image);
            const auto *const imageName =
                *reinterpret_cast<const char *const *>(
                    imageBytes + GfxImageNameOffset);
            const auto *const loadDef =
                *reinterpret_cast<const std::uint8_t *const *>(
                    imageBytes + GfxImageLoadDefOffset);
            std::string loadDefHex{ "<null>" };
            std::string payloadHeadHex{ "<null>" };
            std::uint32_t dataSize{};
            if (loadDef && readableSpan(loadDef, GfxImageLoadDefSize))
            {
                loadDefHex = hex(loadDef, GfxImageLoadDefSize);
                std::memcpy(&dataSize,
                    loadDef + GfxImageLoadDefDataSizeOffset,
                    sizeof(dataSize));
                const auto payloadHeadSize = std::min<std::size_t>(
                    dataSize, GfxImagePayloadHeadSize);
                payloadHeadHex = payloadHeadSize
                    ? hex(loadDef + GfxImageLoadDefSize, payloadHeadSize)
                    : std::string{};
            }
            output << "image\t" << owner << "\t\t" << safeName(imageName)
                   << '\t' << pointerText(image) << '\t'
                   << hex(image, GfxImageHeaderSize) << '\t'
                   << "loadDef=" << pointerText(loadDef)
                   << ",loadDefHex=" << loadDefHex
                   << ",dataSize=" << dataSize
                   << ",payloadHead=" << payloadHeadHex << '\n';
            ++imageCount;
        };

        // These are the three final rendering categories the alpha bundle
        // needs: ordinary opaque weapon material, scope body, and translucent
        // lens. The world lens is a control for a view/world technique split.
        static constexpr std::array<const char *, 5> Materials{
            "mc/mtl_weapon_m16",
            "mc/mtl_weapon_acog_2_alpha",
            "mc/mtl_ret_acog02_acota31ncm_alpha",
            "mc/mtl_weapon_lens_eot_exps",
            "mc/mtl_wea_javelin_javelin_lens",
        };
        for (const auto *const requestedName : Materials)
        {
            const auto *const material = static_cast<const std::uint8_t *>(
                findXAsset(MaterialAssetType, requestedName, false).data);
            if (!material || !readableSpan(material, MaterialHeaderSize))
            {
                output << "material\t\t\t" << requestedName
                       << "\t<missing>\t\t\n";
                ++missingCount;
                continue;
            }
            const auto *const resolvedName =
                *reinterpret_cast<const char *const *>(
                    material + MaterialNameOffset);
            const auto count = material[MaterialTextureCountOffset];
            const auto *const table =
                *reinterpret_cast<const std::uint8_t *const *>(
                    material + MaterialTextureTableOffset);
            output << "material\t\t\t" << safeName(resolvedName) << '\t'
                   << pointerText(material) << '\t'
                   << hex(material, MaterialHeaderSize) << '\t'
                   << "requested=" << requestedName << ",textures="
                   << static_cast<unsigned>(count) << ",table="
                   << pointerText(table) << '\n';
            ++materialCount;

            if (!count)
                continue;
            if (!table || !readableSpan(
                    table, static_cast<std::size_t>(count) *
                        MaterialTextureRowSize))
            {
                output << "texture-table\t" << requestedName
                       << "\t\t<unreadable>\t" << pointerText(table)
                       << "\t\tcount=" << static_cast<unsigned>(count) << '\n';
                continue;
            }
            for (std::size_t index{}; index < count; ++index)
            {
                const auto *const row =
                    table + index * MaterialTextureRowSize;
                const auto semantic = row[MaterialTextureSemanticOffset];
                const auto *const image =
                    semantic == WaterSemantic
                    ? nullptr
                    : *reinterpret_cast<const void *const *>(
                          row + MaterialTextureImageOffset);
                std::string imageName{ "<null>" };
                if (semantic == WaterSemantic)
                {
                    imageName = "<water>";
                }
                else if (image && readableSpan(image, GfxImageHeaderSize))
                {
                    imageName = safeName(
                        *reinterpret_cast<const char *const *>(
                            static_cast<const std::uint8_t *>(image) +
                            GfxImageNameOffset));
                }
                output << "texture\t" << requestedName << '\t' << index
                       << '\t' << imageName << '\t' << pointerText(image)
                       << '\t' << hex(row, MaterialTextureRowSize)
                       << "\tsemantic=" << static_cast<unsigned>(semantic)
                       << '\n';
                ++textureCount;
                if (semantic != WaterSemantic)
                    writeImage(requestedName, image);
            }
        }

        // The alpha bundle reuses this final image by name. Record it even if
        // none of the four material controls happens to reference it.
        const auto *const detailImage =
            findXAsset(GfxImageAssetType, "detail_gray_01", false).data;
        if (detailImage)
            writeImage("direct:detail_gray_01", detailImage);
        else
            ++missingCount;

        output.close();
        log("materials=" + std::to_string(materialCount) + "/" +
            std::to_string(Materials.size()) + " textures=" +
            std::to_string(textureCount) + " uniqueImages=" +
            std::to_string(imageCount) + " opticCandidates=" +
            std::to_string(opticCandidateCount) + " missing=" +
            std::to_string(missingCount) + " -> " + path.string());
    }

    bool EngineBindings::attachmentModelResolutionAvailable(
        const std::uint32_t baseWeaponAssetIndex,
        const std::uint32_t attachmentIndex) const
    {
        // 500 was 3.3.3.3's, and this is the SAME array weaponRegistryInitialized
        // bounds - so it is the same constant, shared now rather than repeated.
        constexpr auto BaseWeaponCount = BaseWeaponAssetCount;
        constexpr std::uint32_t MaximumAttachmentsPerWeapon = 64;
        if (!baseWeaponAssetIndex || baseWeaponAssetIndex >= BaseWeaponCount ||
            !attachmentIndex)
        {
            return false;
        }
        const auto *mappingCount = module_ + PerWeaponAttachmentCountsRva +
            baseWeaponAssetIndex;
        const auto *mappings = reinterpret_cast<const std::uint32_t *>(
            module_ + AttachmentMappingsRva) +
            baseWeaponAssetIndex * MaximumAttachmentsPerWeapon;
        const auto *attachmentModelCount =
            reinterpret_cast<const std::uint16_t *>(
                module_ + AttachmentModelCountRva);
        const auto *noneModel = reinterpret_cast<const std::uint16_t *>(
            module_ + NoneAttachmentModelIndexRva);
        if (!readableSpan(mappingCount, sizeof(*mappingCount)) ||
            !readableSpan(attachmentModelCount, sizeof(*attachmentModelCount)) ||
            !readableSpan(noneModel, sizeof(*noneModel)) ||
            *mappingCount > MaximumAttachmentsPerWeapon ||
            !readableSpan(mappings, *mappingCount * sizeof(*mappings)))
        {
            return false;
        }

        auto modelIndex = *noneModel;
        const auto mapping = std::find_if(
            mappings,
            mappings + *mappingCount,
            [attachmentIndex](const std::uint32_t value) {
                return static_cast<std::uint16_t>(value) == attachmentIndex;
            });
        if (mapping != mappings + *mappingCount)
            modelIndex = static_cast<std::uint16_t>(*mapping >> 16);
        if (modelIndex >= *attachmentModelCount)
            return false;

        const auto *model = reinterpret_cast<const void *const *>(
            module_ + AttachmentModelDefinitionsRva) + modelIndex;
        return readableSpan(model, sizeof(*model)) && *model;
    }

    std::optional<std::string> EngineBindings::internedAttachmentName(
        const std::uint32_t attachmentId) const
    {
        if (!module_ || !attachmentId || attachmentId >= 0x3FFD)
            return std::nullopt;
        const auto *const slot = reinterpret_cast<const char *const *>(
            module_ + InternedStringTableRva) + attachmentId;
        if (!readableSpan(reinterpret_cast<const std::uint8_t *>(slot),
                sizeof(*slot)) || !*slot)
        {
            return std::nullopt;
        }
        return readCString(*slot, 128);
    }

    std::optional<std::uint32_t> EngineBindings::attachmentIdForWeapon(
        const std::uint32_t targetWeaponAssetIndex,
        const std::uint32_t canonicalAttachmentId) const
    {
        // Section 187h. Two passes over word_198C0A0[128 * weapon], the same
        // (nameId, modelIndex) pair table sub_42F9B0 walks:
        //   1. find the MODEL the canonical id names, anywhere it is registered;
        //   2. find the entry in the TARGET weapon carrying that same model.
        // Both RMRs are model 17, both extended magazines model 10, so the model is
        // what survives the change of weapon while the id does not.
        constexpr std::uint32_t MaximumAttachmentsPerWeapon = 64;
        if (!module_ || !canonicalAttachmentId || !targetWeaponAssetIndex ||
            targetWeaponAssetIndex >= BaseWeaponAssetCount)
        {
            return std::nullopt;
        }
        const auto entriesFor = [&](const std::uint32_t weapon)
            -> std::span<const std::uint32_t> {
            const auto *const count =
                module_ + PerWeaponAttachmentCountsRva + weapon;
            const auto *const rows = reinterpret_cast<const std::uint32_t *>(
                module_ + AttachmentMappingsRva) +
                weapon * MaximumAttachmentsPerWeapon;
            if (!readableSpan(count, sizeof(*count)) ||
                *count > MaximumAttachmentsPerWeapon ||
                !readableSpan(rows, *count * sizeof(*rows)))
            {
                return {};
            }
            return { rows, *count };
        };

        std::optional<std::uint16_t> model;
        for (std::uint32_t weapon = 1;
            weapon < BaseWeaponAssetCount && !model; ++weapon)
        {
            for (const auto row : entriesFor(weapon))
            {
                if (static_cast<std::uint16_t>(row) == canonicalAttachmentId)
                {
                    model = static_cast<std::uint16_t>(row >> 16);
                    break;
                }
            }
        }
        if (!model)
            return std::nullopt;

        for (const auto row : entriesFor(targetWeaponAssetIndex))
        {
            if (static_cast<std::uint16_t>(row >> 16) == *model)
                return static_cast<std::uint16_t>(row);
        }
        return std::nullopt;
    }

    std::uint32_t EngineBindings::attachmentTableCountForWeapon(
        const std::uint32_t baseWeaponAssetIndex) const
    {
        // byte_1988638[weapon] -- the per-weapon attachment count sub_42F9B0 bounds its
        // walk with and sub_42F910 increments as it registers. Zero means the weapon has
        // registered nothing, which is a very different statement from "this attachment
        // is not supported". Section 187.
        if (!module_ || !baseWeaponAssetIndex ||
            baseWeaponAssetIndex >= BaseWeaponAssetCount)
        {
            return 0;
        }
        const auto *const mappingCount = module_ + PerWeaponAttachmentCountsRva +
            baseWeaponAssetIndex;
        if (!readableSpan(mappingCount, sizeof(*mappingCount)))
            return 0;
        return *mappingCount;
    }

    bool EngineBindings::attachmentSupportedByWeapon(
        const std::uint32_t baseWeaponAssetIndex,
        const std::uint32_t attachmentIndex) const
    {
        // THE SAME TABLE attachmentModelResolutionAvailable WALKS, ASKED THE OTHER
        // QUESTION: not "which model" but "is it in here at all".
        //
        // out.exe sub_42F9B0, the engine's own lookup, exactly:
        //     v2 = byte_1988638[weapon];                       per-weapon COUNT
        //     if (!v2) return dword_198B8A0[word_19DDECC];     NONE model
        //     for (i = &word_198C0A0[128*weapon]; *i != attachment; i += 2)
        //         if (++v3 >= v2) return dword_198B8A0[word_19DDECC];   NOT FOUND
        //     return dword_198B8A0[i[1]];                      FOUND
        //
        // 128 u16 per weapon is 64 (attachment, model) pairs, which is the same layout
        // this file reads as uint32_t[64] with the attachment in the low half. And
        // sub_42F910 never registers a pair whose model is the none model, so anything
        // present here is genuinely supported. Section 187.
        constexpr auto BaseWeaponCount = BaseWeaponAssetCount;
        constexpr std::uint32_t MaximumAttachmentsPerWeapon = 64;
        if (!baseWeaponAssetIndex || baseWeaponAssetIndex >= BaseWeaponCount ||
            !attachmentIndex)
        {
            return false;
        }
        const auto *const mappingCount = module_ + PerWeaponAttachmentCountsRva +
            baseWeaponAssetIndex;
        const auto *const mappings = reinterpret_cast<const std::uint32_t *>(
            module_ + AttachmentMappingsRva) +
            baseWeaponAssetIndex * MaximumAttachmentsPerWeapon;
        if (!readableSpan(mappingCount, sizeof(*mappingCount)) ||
            *mappingCount > MaximumAttachmentsPerWeapon ||
            !readableSpan(mappings, *mappingCount * sizeof(*mappings)))
        {
            return false;
        }
        return std::any_of(
            mappings, mappings + *mappingCount,
            [attachmentIndex](const std::uint32_t value) {
                return static_cast<std::uint16_t>(value) == attachmentIndex;
            });
    }

    std::optional<std::string> EngineBindings::readWeaponDefinitionName(
        const std::uint32_t weaponAssetIndex) const
    {
        if (!module_ || weaponAssetIndex >= WeaponConfigStringCount)
            return std::nullopt;
        const auto *slot = reinterpret_cast<const std::uint8_t *const *>(
            module_ + WeaponDefinitionsRva) + weaponAssetIndex;
        if (!readableSpan(slot, sizeof(*slot)) || !*slot ||
            !readableSpan(*slot, sizeof(const char *)))
        {
            return std::nullopt;
        }
        return readCString(
            *reinterpret_cast<const char *const *>(*slot), 512);
    }

    std::uint16_t EngineBindings::altWeaponAssetIndex(
        const std::uint32_t weaponAssetIndex) const
    {
        if (!module_ || !weaponAssetIndex ||
            weaponAssetIndex >= WeaponConfigStringCount)
        {
            return 0;
        }
        const auto *const slot = reinterpret_cast<const std::uint8_t *const *>(
            module_ + WeaponDefinitionsRva) + weaponAssetIndex;
        if (!readableSpan(slot, sizeof(*slot)) || !*slot ||
            !readableSpan(*slot, 3724))
        {
            return 0;
        }
        const auto alt =
            *reinterpret_cast<const std::uint32_t *>(*slot + 3720);
        // A BOUND, AND IT IS THE ONE THE WIRE ALREADY USES. An out-of-range
        // index here would be written into the native playerState and handed
        // to Pmove, which indexes dword_1988B50 with it unchecked.
        return alt && alt <= MaximumWeaponAssetIndex
            ? static_cast<std::uint16_t>(alt)
            : std::uint16_t{};
    }

    bool EngineBindings::readWeaponSelection(
        const std::uint32_t weaponAssetIndex,
        ClientWeaponSelection &selection) const
    {
        if (!readWeaponDefinition(weaponAssetIndex, selection))
            return false;
        selection.weaponAssetIndex = weaponAssetIndex;
        const auto name = readWeaponDefinitionName(weaponAssetIndex);
        if (name)
            selection.weaponName = *name;
        return true;
    }



    // itemId -> weapon name, from Ayria\Logs\weapon-aliases.csv. Empty when the file is
    // absent, which is the normal case and costs nothing.
    std::optional<std::string> EngineBindings::aliasedWeaponName(
        const std::uint32_t itemId) const
    {
        static const std::map<std::uint32_t, std::string> aliases = [] {
            std::map<std::uint32_t, std::string> loaded;
            const auto path = diagnosticPath(L"weapon-aliases.csv");
            std::ifstream file(path);
            if (!file)
                return loaded;
            std::string line;
            while (std::getline(file, line))
            {
                const auto comma = line.find(',');
                if (comma == std::string::npos || line.starts_with('#'))
                    continue;
                const auto id = line.substr(0, comma);
                auto name = line.substr(comma + 1);
                while (!name.empty() && (name.back() == '\r' || name.back() == ' '))
                    name.pop_back();
                if (name.empty())
                    continue;
                try
                {
                    loaded.emplace(
                        static_cast<std::uint32_t>(std::stoul(id)), name);
                }
                catch (const std::exception &)
                {
                    // A malformed row is skipped, not fatal: the rest of the file is
                    // still worth having and a loadout must not fail over a typo here.
                }
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "weapon aliases: " + std::to_string(loaded.size()) + " from " +
                    path.string());
            return loaded;
        }();

        const auto found = aliases.find(itemId);
        if (found == aliases.end())
            return std::nullopt;

        // SAY IT ONCE. An alias is a deliberate override of what an id means, and a
        // loadout that silently carried a different weapon than its id implies would be
        // unexplainable from the logs.
        static std::mutex mutex;
        static std::set<std::uint32_t> reported;
        {
            const std::lock_guard lock(mutex);
            if (reported.insert(itemId).second)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "weapon alias: item " + std::to_string(itemId) + " -> '" +
                        found->second + "' (no marketplace item names this weapon)");
            }
        }
        return found->second;
    }

    bool EngineBindings::resolveWeaponItem(
        const std::uint32_t itemId,
        const std::array<std::uint32_t, 6> &attachmentItemIds,
        ClientWeaponSelection &selection) const
    {
        if (!weaponLookup_ || !weaponResolver_ || !attachmentLookup_)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::NativeResolverUnavailable,
                std::memory_order_relaxed);
            return false;
        }

        // A WEAPON THE STORE CANNOT SELL YOU.
        //
        // raygun_mp and thundergun_chicken_mp are weapon assets in common_gametype_mp --
        // they are LOADED IN EVERY MULTIPLAYER MATCH -- and neither has a marketplace
        // item, so no id names them and the class screen can never offer one. That is
        // what "missing items" meant: not unowned, unreachable.
        //
        // The resolver two lines below takes a NAME, not an id. The id is only how the
        // name is normally found. So an alias file maps an unused id onto a weapon name
        // and the rest of the path is unchanged -- registration, attachments, the
        // modular string, all of it.
        //
        // Ayria\Logs\weapon-aliases.csv, `itemId,weaponName`, read once. A FILE rather
        // than a constant so adding a weapon costs an edit and a re-host instead of a
        // rebuild, and it can be empty or missing with no effect at all.
        auto internalName = aliasedWeaponName(itemId);
        const bool aliased = internalName.has_value();
        if (!internalName)
            internalName = readItemInternalName(itemId);
        if (!internalName)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::ItemName,
                std::memory_order_relaxed);
            return false;
        }

        // Session configuration resolves the booked classes immediately after
        // world initialization, in the same frame that makes the weapon
        // registry available. Install a requested alpha alias at that first
        // usable boundary so its class is not discarded before the ordinary
        // per-frame installer gets a chance to run.
        if (aliased && *internalName == "barrett_heartbeat_mp")
        {
            const auto alphaStatus = installAlphaWeaponPorts();
            if (alphaStatus != AlphaWeaponPortStatus::Ready)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "alpha weapon early install unavailable name=" +
                        *internalName + " status=" +
                        std::to_string(static_cast<std::uint32_t>(
                            alphaStatus)));
            }
        }

        const auto resolvedWeaponAssetIndex = weaponResolver_(
            internalName->c_str(), nullptr);
        // CODDIFF(1649370): the bound was 0x400 = 1024, which is 3.3.3.3's
        // base weapon table. This build's is BaseWeaponAssetCount = 0x514 =
        // 1300, measured from the gap between PerWeaponAttachmentCountsRva and
        // AttachmentModelCountRva, so every base weapon from 1024 up was being
        // rejected as out of range by a constant from the other build.
        if (!resolvedWeaponAssetIndex ||
            resolvedWeaponAssetIndex >= BaseWeaponAssetCount)
        {
            // The ITEM ID alone cannot tell "this id is not a weapon" apart
            // from "the registry never registered it", and those want opposite
            // fixes. The name and the index the resolver actually returned do.
            // `sf_weapon_m4_mp_name` is a LOCALISATION KEY, not a weapon
            // asset name, so ItemDefinitionNameOffset is pointing at the wrong
            // field on this build - another constant carried from 3.3.3.3.
            // Rather than guess which neighbouring offset holds the internal
            // name, report every readable string in the definition and let the
            // log name it. Guessing +8 and then +16 costs two launches; this
            // costs none.
            std::string fields;
            if (const auto *const definition = readItemDefinition(itemId))
            {
                for (std::size_t offset = 0; offset + 4 <= ItemDefinitionSize;
                     offset += 4)
                {
                    const auto *const candidate =
                        *reinterpret_cast<const char *const *>(
                            definition + offset);
                    const auto text = readCString(candidate, 64);
                    if (text && !text->empty() && validBookingName(*text))
                        fields += " +" + std::to_string(offset) + "=" + *text;
                }
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "base weapon resolve failed item=" + std::to_string(itemId) +
                    " name=" + *internalName + " resolved=" +
                    std::to_string(resolvedWeaponAssetIndex) + " bound=" +
                    std::to_string(BaseWeaponAssetCount) +
                    " definitionStrings" + (fields.empty() ? " none" : fields));
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::BaseWeaponResolver,
                std::memory_order_relaxed);
            return false;
        }
        if (weaponLookup_(internalName->c_str()) != resolvedWeaponAssetIndex)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::BaseWeaponLookup,
                std::memory_order_relaxed);
            return false;
        }

        const auto alphaNetworkAssetIndex =
            SV_AlphaWeaponNetworkAssetIndex(*internalName);
        selection.baseWeaponAssetIndex = alphaNetworkAssetIndex
            ? *alphaNetworkAssetIndex
            : resolvedWeaponAssetIndex;
        selection.weaponName = *internalName;
        selection.modularValue8 = 0;
        selection.modularValue9 = 0;
        // ONCE PER PROCESS, AND ONLY IF ASKED. This is the first point at which the
        // weapon items table is certainly loaded, so it is where the whole-table audit can
        // run -- see auditWeaponItemsTable, which answers "which guns would refuse" for
        // all of them instead of one per player who happens to pick one.
        {
            static std::once_flag audited;
            std::call_once(audited, [this] {
                char *value = nullptr;
                std::size_t size = 0;
                if (_dupenv_s(&value, &size, "OLMOD_AUDIT_WEAPON_TABLE") == 0 && value)
                {
                    const bool wanted = value[0] == '1';
                    free(value);
                    if (wanted)
                        auditWeaponItemsTable();
                }

            });
        }
        auto defaults = readDefaultWeaponAttachments(*internalName);
        // A WEAPON WITH NO ROW IN THE WEAPON ITEMS TABLE HAS NO DEFAULTS -- IT IS NOT A
        // FAILURE. raygun_mp is absent from that table, which is exactly WHY it can never
        // appear in a class screen, and refusing it here dropped the whole class and made
        // UpdateLoadout fail: `default attachments unavailable for 'raygun_mp': no row for
        // this weapon in the weapon items table`.
        //
        // NARROWED TO ALIASED WEAPONS ON PURPOSE. For an ordinary item a missing row is a
        // real problem -- a mistyped name, a table that did not load -- and swallowing it
        // would hide the failure this refusal was written to catch. An alias, by
        // definition, names a weapon the tables do not carry.
        if (!defaults && aliased)
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "weapon alias: '" + *internalName + "' has no weapon-items row, so it has "
                "no default attachments -- carrying on with none");
            defaults.emplace();
        }
        if (!defaults)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::DefaultAttachments,
                std::memory_order_relaxed);
            return false;
        }
        std::vector<NamedWeaponAttachment> equipped;
        equipped.reserve(attachmentItemIds.size());
        for (const auto attachmentItemId : attachmentItemIds)
        {
            if (!attachmentItemId)
                continue;
            // AN ATTACHMENT THAT DOES NOT RESOLVE IS SKIPPED, NOT FATAL.
            //
            // Every one of these used to `return false`, which fails the WHOLE weapon
            // and spawns the player holding nothing. That was survivable only while
            // this list was always empty; section 186f's fix fills it from the profile,
            // so one stale id in a five-class document would have cost the player their
            // gun. Skipping costs them one attachment and says which.
            //
            // AND THE FULL VALIDATION HAPPENS HERE, not in the merge below. The merged
            // loop's attachmentLookup_ / attachmentModelResolutionAvailable checks are
            // still fatal -- correctly, because a DEFAULT that cannot resolve means the
            // weapon itself is wrong -- so an equipped attachment must clear those same
            // two gates before it is allowed to join the list.
            static std::mutex attachmentLogMutex;
            static std::set<std::string> attachmentLogReported;
            const auto report = [](const std::string &line) {
                const std::lock_guard lock(attachmentLogMutex);
                if (attachmentLogReported.insert(line).second)
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, line);
                }
            };
            const auto skip = [&](const char *const why) {
                report("attachment skipped item=" +
                    std::to_string(attachmentItemId) + " weapon=" +
                    selection.weaponName + " " + why);
            };
            auto attachmentName = readItemInternalName(attachmentItemId);
            if (!attachmentName)
            {
                skip("has no internal name");
                continue;
            }
            const auto slot = readAttachmentModelSlot(*attachmentName);
            if (!slot)
            {
                skip("has no model slot");
                continue;
            }
            auto equippedIndex = attachmentLookup_(attachmentName->c_str());
            if (!equippedIndex || equippedIndex >= 0x3FFF)
            {
                skip("is not in the attachment registry");
                continue;
            }
            // AND TRANSLATE IT TO THIS WEAPON FIRST. Section 187h.
            //
            // The profile stores one generic attachment item and hangs it on several
            // weapons, but the modular string wants that weapon's OWN id: 6206 for a
            // TMP's red dot, 14268 for an M9's, both model 17. Without this step the
            // canonical name resolves to another weapon's id, the strict test below
            // correctly rejects it, and the player gets nothing.
            if (const auto translated = attachmentIdForWeapon(
                    resolvedWeaponAssetIndex, equippedIndex);
                translated && *translated != equippedIndex)
            {
                // NOT a skip -- the attachment is being KEPT, under this weapon's
                // own id. Reusing skip() here printed "attachment skipped ...
                // translated to", which reads as the opposite of what happened.
                report("attachment translated item=" +
                    std::to_string(attachmentItemId) + " weapon=" +
                    selection.weaponName + " -> id " +
                    std::to_string(*translated));
                equippedIndex = *translated;
                const auto translatedName = internedAttachmentName(equippedIndex);
                if (translatedName)
                    attachmentName = translatedName;
            }

            // THE STRICT TEST, NOT THE LOOKUP. Section 187.
            //
            // attachmentModelResolutionAvailable answers "which model" and returns the
            // engine's NONE model when a weapon has no entry for an attachment -- which
            // reads as available and is how a red dot ended up on an MSR, faulting both
            // clients at spawn with `1073 tag_reticle_red_dot ..._vmchar`. A reticle
            // mounts on a tag the weapon's model does not carry, so nothing downstream
            // could have caught it.
            //
            // DEFAULTS KEEP THE LENIENT CHECK in the merge below, deliberately: they are
            // the weapon's own and the none model is a legitimate answer for them. Only
            // an attachment the PLAYER chose has to prove the weapon supports it.
            if (!attachmentSupportedByWeapon(
                    resolvedWeaponAssetIndex, equippedIndex))
            {
                skip("is not supported by this weapon");
                continue;
            }
            if (!attachmentModelResolutionAvailable(
                    resolvedWeaponAssetIndex, equippedIndex))
            {
                skip("has no model for this weapon");
                continue;
            }
            equipped.push_back({
                .slot = *slot,
                .name = *attachmentName,
            });
        }
        const auto effectiveAttachments = SV_MergeWeaponAttachments(
            *defaults, equipped);
        if (!effectiveAttachments)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::AttachmentMerge,
                std::memory_order_relaxed);
            return false;
        }

        // THE STRING WE PUBLISH, SAID OUT LOUD, because it is the whole weapon
        // attachment channel and nothing has ever printed it. Retail's own, read out
        // of the dm demo at cs 7184.. (= WeaponConfigStringBase 5960 + the
        // firstDynamicWeapon 1224 this server prints every match):
        //
        //     ** 682 0 0 9930 8738 6747 10545 9321 6690 6825
        //     ** 652 0 0 8738
        //     ** 249 0 0                          <- a weapon with no attachments
        //
        // So the format is `** <weapon> <n> <n> <attachment...>` and the question this
        // line answers is whether OUR trailing numbers look like retail's. Deduped, so
        // a stable loadout prints once per distinct weapon.
        std::string modularName = "** " +
            std::to_string(selection.baseWeaponAssetIndex) + " 0 0";
        for (const auto &attachment : *effectiveAttachments)
        {
            const auto attachmentIndex = attachmentLookup_(attachment.name.c_str());
            if (!attachmentIndex || attachmentIndex >= 0x3FFF)
            {
                loadoutResolveFailure_.store(
                    ClientLoadoutResolveFailure::AttachmentLookup,
                    std::memory_order_relaxed);
                return false;
            }
            if (!attachmentModelResolutionAvailable(
                    resolvedWeaponAssetIndex, attachmentIndex))
            {
                loadoutResolveFailure_.store(
                    ClientLoadoutResolveFailure::AttachmentModelResolution,
                    std::memory_order_relaxed);
                return false;
            }
            if (selection.attachmentCount >=
                selection.attachmentAssetIndexes.size())
            {
                loadoutResolveFailure_.store(
                    ClientLoadoutResolveFailure::AttachmentCapacity,
                    std::memory_order_relaxed);
                return false;
            }
            selection.attachmentAssetIndexes[selection.attachmentCount++] =
                attachmentIndex;
            modularName += " " + std::to_string(attachmentIndex);
        }

        {
            std::string equippedReport;
            for (const auto &attachment : equipped)
                equippedReport += " " + attachment.name;
            if (equippedReport.empty())
                equippedReport = " (none)";
            static std::mutex reportMutex;
            static std::set<std::string> reported;
            const std::lock_guard lock(reportMutex);
            if (reported.insert(modularName).second)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "modular weapon \"" + modularName + "\" weapon=" +
                    selection.weaponName + " attachments=" +
                    std::to_string(selection.attachmentCount) +
                    " defaults=" + std::to_string(defaults->size()) +
                    " EQUIPPED=" + std::to_string(equipped.size()) +
                    equippedReport +
                    // IS THE WEAPON'S ATTACHMENT TABLE EVEN POPULATED WHEN WE ASK?
                    //
                    // attachmentSupportedByWeapon rejected 25703 (red_rmrtmp) on an M4,
                    // and an M4 with a red dot is an ordinary loadout -- so either that
                    // is true or byte_1988638[weapon] is still zero at resolve time and
                    // the strict test rejects everything. Printing the COUNT and how
                    // many of the weapon's OWN DEFAULTS are in the table separates
                    // those: defaults are by definition supported, so if they are not
                    // in it either, the table is the problem and not the id.
                    " tableCount=" + std::to_string(
                        attachmentTableCountForWeapon(resolvedWeaponAssetIndex)) +
                    // THE TABLE ITSELF, AS TEXT. defaultsInTable came back 0/1, 0/4 and
                    // 1/3 with tableCount 10..19 -- the tables are populated and the
                    // weapons' OWN DEFAULTS are missing from them, which can only mean
                    // the key we compute is not the key they are stored under.
                    //
                    // sub_42F910 interns dword_198B8A0[model]->name -- the attachment
                    // MODEL's name -- so the low half is an interned name id, not an
                    // attachment index. dword_1978640[id] is that id's char*, so the
                    // entries can be printed rather than guessed at.
                    " table=" + [&] {
                        std::string out;
                        const auto count =
                            attachmentTableCountForWeapon(resolvedWeaponAssetIndex);
                        const auto *const mappings =
                            reinterpret_cast<const std::uint32_t *>(
                                module_ + AttachmentMappingsRva) +
                            resolvedWeaponAssetIndex * 64;
                        const auto *const interned =
                            reinterpret_cast<const char *const *>(
                                module_ + InternedStringTableRva);
                        if (!readableSpan(mappings, count * sizeof(std::uint32_t)))
                            return std::string{ "<unreadable>" };
                        for (std::uint32_t entry = 0;
                            entry < count && entry < 12; ++entry)
                        {
                            const auto nameId =
                                static_cast<std::uint16_t>(mappings[entry]);
                            const auto *const slot = interned + nameId;
                            const char *text = "<?>";
                            if (readableSpan(
                                    reinterpret_cast<const std::uint8_t *>(slot),
                                    sizeof(*slot)) && *slot)
                            {
                                text = *slot;
                            }
                            out += " " + std::to_string(nameId) + ":" +
                                std::string(text).substr(0, 24) + "->" +
                                std::to_string(mappings[entry] >> 16);
                        }
                        return out;
                    }() +
                    " defaultsInTable=" + [&] {
                        std::size_t found = 0;
                        for (const auto &attachment : *defaults)
                        {
                            const auto index =
                                attachmentLookup_(attachment.name.c_str());
                            if (index && attachmentSupportedByWeapon(
                                    resolvedWeaponAssetIndex, index))
                            {
                                ++found;
                            }
                        }
                        return std::to_string(found) + "/" +
                            std::to_string(defaults->size());
                    }() +
                    // WHY THE SPLIT MATTERS. Our `** 646 0 0 8738 9321` and
                    // `** 992 0 0 9321` are BYTE-IDENTICAL to retail's cs 7184 and
                    // cs 7204, so the format and the ids are right. But retail also
                    // publishes `** 992 0 0 6206 9321`, `** 646 0 0 14268 8738 9321`
                    // and `** 534 0 0 9930 4415 5153 8738 6747 10545` -- EVERY
                    // ATTACHMENT COMBINATION IS ITS OWN WEAPON STRING, and those
                    // variants carry ids ours never produce. Matching retail's
                    // DEFAULT variant exactly is what publishing defaults-only looks
                    // like, so the number that decides it is EQUIPPED, not the total."
                    " -- retail's defaults-only variants look exactly like ours;"
                    " EQUIPPED=0 means the player's choices never arrive");
            }
        }

        const auto *registryCount = reinterpret_cast<const std::uint32_t *>(
            module_ + WeaponRegistryCountRva);
        if (!readableSpan(registryCount, sizeof(*registryCount)) ||
            *registryCount >= WeaponConfigStringCount)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::ModularWeaponDependency,
                std::memory_order_relaxed);
            return false;
        }
        const auto registryCountBefore = *registryCount;

        // The dedicated's map reset moves its private barrett_mp base from
        // 1234 to 1154, while the client keeps Barrett at 1234 and has
        // chicken_melee_mp at 1154. Session preparation already resolved the
        // canonical Barrett variant before that reset, when both processes
        // agreed on 1234. Reuse that retained dynamic WeaponDef afterwards.
        // Building a fresh "** 1154" is correct only inside the dedicated and
        // sends the client a fully functional knife; building a new
        // "** 1234" after reset would inherit the dedicated's now-unrelated
        // killstreak WeaponDef. If the proven canonical variant disappeared,
        // refuse the loadout instead of constructing either wrong weapon.
        if (alphaNetworkAssetIndex &&
            *alphaNetworkAssetIndex != resolvedWeaponAssetIndex &&
            !weaponLookup_(modularName.c_str()))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "alpha canonical modular weapon unavailable name=" +
                    *internalName + " localBase=" +
                    std::to_string(resolvedWeaponAssetIndex) +
                    " networkBase=" +
                    std::to_string(*alphaNetworkAssetIndex) +
                    " modular=" + modularName);
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::ModularWeaponDependency,
                std::memory_order_relaxed);
            return false;
        }
        const auto modularWeaponAssetIndex = weaponResolver_(
            modularName.c_str(), nullptr);
        if (!modularWeaponAssetIndex ||
            modularWeaponAssetIndex > MaximumWeaponAssetIndex ||
            weaponLookup_(modularName.c_str()) != modularWeaponAssetIndex)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::ModularWeaponResolver,
                std::memory_order_relaxed);
            return false;
        }
        const auto registryCountAfter = *registryCount;
        if (registryCountAfter < registryCountBefore ||
            registryCountAfter >= WeaponConfigStringCount ||
            modularWeaponAssetIndex > registryCountAfter)
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::ModularWeaponDependency,
                std::memory_order_relaxed);
            return false;
        }
        std::vector<SvModularWeaponConfigString> discoveredDependencies;
        for (auto index = registryCountBefore + 1;
             index <= registryCountAfter;
             ++index)
        {
            if (index == modularWeaponAssetIndex)
                continue;
            const auto dependencyName = readWeaponDefinitionName(index);
            const auto dependency = dependencyName
                ? SV_ParseModularWeaponConfigString(*dependencyName)
                : std::nullopt;
            if (!dependency)
            {
                loadoutResolveFailure_.store(
                    ClientLoadoutResolveFailure::ModularWeaponDependency,
                    std::memory_order_relaxed);
                return false;
            }
            discoveredDependencies.push_back(*dependency);
        }
        if (!discoveredDependencies.empty())
        {
            modularDependencyCache_.insert_or_assign(
                modularName, discoveredDependencies);
        }
        const auto cachedDependencies = modularDependencyCache_.find(modularName);
        if (cachedDependencies != modularDependencyCache_.end())
        {
            selection.modularDependencies = cachedDependencies->second;
        }

        // The resolver above has now built the equipped modular WeaponDef.
        // The fields copied before attachment assembly belong to the base
        // weapon, so retaining them makes authoritative fire ignore every
        // attachment modifier (spread, damage, timing, ammo, and ADS). Read
        // the completed definition back from its registered slot so native
        // prediction and the source server fire path use the same weapon.
        if (!readWeaponDefinition(modularWeaponAssetIndex, selection))
        {
            loadoutResolveFailure_.store(
                ClientLoadoutResolveFailure::WeaponDefinition,
                std::memory_order_relaxed);
            return false;
        }
        selection.weaponAssetIndex = modularWeaponAssetIndex;
        loadoutResolveFailure_.store(
            ClientLoadoutResolveFailure::None,
            std::memory_order_relaxed);
        return true;
    }

    ClientLoadoutResolveFailure EngineBindings::loadoutResolveFailure() const
    {
        return loadoutResolveFailure_.load(std::memory_order_relaxed);
    }

    std::optional<SvResolvedPerks> EngineBindings::resolveSessionPerks(
        const OlMod::DedicatedSession::LoadoutRequest &request,
        const std::uint32_t classIndex) const
    {
        if (!OlMod::DedicatedSession::valid(request) ||
            classIndex >= request.classes.size() ||
            !(request.classMask & (1u << classIndex)))
            return std::nullopt;

        SvResolvedPerks result;
        result.itemIds = request.classes[classIndex].perkItemIds;
        if (std::ranges::all_of(result.itemIds,
                [](const auto item) { return item <= 1; }))
            return result;

        // CODREF(1649370): sub_413980 looks up column 1 (canonical name),
        // reads column 0 (decimal bit index), and rejects indices >= 96.
        // sub_4442E0 sets ps+0x584 + 4*(index>>5), bit (index&31).
        // The row ordinal is NOT the perk index. BO1 BG_SetPerk 0x60E0E0
        // and Ghosts PlayerCmd_SetPerk 0x14011A760 confirm bitset ownership;
        // their perk counts and player-state offsets are different.
        const auto *table = readStringTable(
            dbFindXAssetHeader_, dbIsXAssetDefault_, "mp/coPerkStatsTable.csv", 2);
        if (!table)
            return std::nullopt;
        result = SV_ResolveProfilePerks(result.itemIds,
            [&](const std::uint32_t item) -> std::optional<std::uint32_t> {
            const auto name = readItemInternalName(item);
            if (name)
            {
                for (std::int32_t rowIndex = 0; rowIndex < table->rowCount; ++rowIndex)
                {
                    const auto *row = table->values + rowIndex * table->columnCount;
                    const auto rowName = readStringTableCell(row[1]);
                    if (!rowName || *rowName != *name)
                        continue;
                    const auto indexText = readStringTableCell(row[0]);
                    std::uint32_t index{};
                    if (!indexText || indexText->empty())
                        break;
                    const auto parsed = std::from_chars(indexText->data(),
                        indexText->data() + indexText->size(), index);
                    if (parsed.ec != std::errc{} ||
                        parsed.ptr != indexText->data() + indexText->size() || index >= 96)
                        break;
                    return index;
                }
            }
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "perk omitted from class=" + std::to_string(classIndex) +
                    " item=" + std::to_string(item) + " name=" +
                    name.value_or("<unresolved>"));
            // Unknown catalog entries cannot grant a perk. Preserve the source
            // profile while publishing an empty runtime slot.
            return std::nullopt;
        });
        const auto *abilityTable = readStringTable(dbFindXAssetHeader_,
            dbIsXAssetDefault_, "mp/coAbilityModifiersTable.csv", 7);
        if (!abilityTable || table->columnCount < 27)
            return std::nullopt;

        const auto number = [](const auto &cell, float fallback) -> std::optional<float> {
            const auto text = readStringTableCell(cell);
            if (!text || text->empty())
                return fallback;
            float value{};
            const auto parsed = std::from_chars(text->data(), text->data() + text->size(), value);
            if (parsed.ec != std::errc{} || parsed.ptr != text->data() + text->size() ||
                !std::isfinite(value))
                return std::nullopt;
            return value;
        };
        std::unordered_map<std::string, float> additions;
        for (std::int32_t r = 0; r < table->rowCount; ++r)
        {
            const auto *row = table->values + r * table->columnCount;
            const auto index = number(row[0], -1);
            if (!index || *index < 0 || *index >= 96 || std::floor(*index) != *index)
                continue;
            const auto i = static_cast<std::uint32_t>(*index);
            if (!(result.bits[i >> 5] & (1u << (i & 31))))
                continue;
            for (std::size_t c = 15; c < 27; c += 2)
            {
                const auto modifier = readStringTableCell(row[c]);
                if (!modifier || modifier->empty())
                    continue;
                const auto amount = number(row[c + 1], 0);
                if (!amount)
                    return std::nullopt;
                additions[*modifier] += *amount;
            }
        }
        // The live asset describes additive deltas, defaults, and clamps.
        // Retail DM corroborates Fast Hands' 1.5 switch / 1.6 offhand scales
        // and Marathon's -1 sprint sentinel (default 4, delta -7, minimum -1).
        // The native consumers divide durations by these speed scales.
        for (std::int32_t r = 0; r < abilityTable->rowCount; ++r)
        {
            const auto *row = abilityTable->values + r * abilityTable->columnCount;
            const auto name = readStringTableCell(row[1]);
            if (!name || !additions.contains(*name))
                continue;
            const auto id = number(row[0], -1);
            const auto valueIndex = number(row[2], -1);
            const auto initial = number(row[3], 0);
            const auto minimum = number(row[4], -std::numeric_limits<float>::max());
            const auto maximum = number(row[5], std::numeric_limits<float>::max());
            if (!id || *id < 0 || *id >= 192 || std::floor(*id) != *id ||
                !valueIndex || !initial || !minimum || !maximum || *minimum > *maximum)
                return std::nullopt;
            const auto modifierId = static_cast<std::uint32_t>(*id);
            result.abilities.mask[modifierId >> 5] |= 0x80000000u >> (modifierId & 31);
            const auto value = std::clamp(*initial + additions.at(*name), *minimum, *maximum);
            result.abilities.resolvedValues[modifierId] = value;
            if (*valueIndex >= 0)
            {
                if (*valueIndex >= 36 || std::floor(*valueIndex) != *valueIndex)
                    return std::nullopt;
                result.abilities.values[static_cast<std::size_t>(*valueIndex)] = value;
            }
            if (*name == "modMoveSpeedScale")
                result.abilities.moveSpeedScale = value;
            if (*name == "modFallDamageScale")
                result.abilities.fallDamageScale = value;
            if (*name == "modKillstreakShift")
                result.abilities.killstreakShift = value;
            additions.erase(*name);
        }
        if (!additions.empty())
            return std::nullopt;
        return result;
    }

    std::optional<SvResolvedEquipment> EngineBindings::resolveSessionEquipment(
        const OlMod::DedicatedSession::LoadoutRequest &request,
        const std::uint32_t classIndex) const
    {
        if (!module_ || !weaponLookup_ || !OlMod::DedicatedSession::valid(request) ||
            classIndex >= request.classes.size() || !(request.classMask & (1u << classIndex)))
            return std::nullopt;
        SvResolvedEquipment result{};
        const auto &equipment = request.classes[classIndex].equipment;
        for (std::size_t slot = 0; slot < result.weapons.size(); ++slot)
        {
            const auto raw = equipment.itemIds[slot];
            if (raw <= 1) continue;
            // CODREF(1649370): profile +1 encoding (50FD05), verified against
            // the item catalog and all five live classes. Base offhand assets
            // are already loaded; lookup does not allocate modular weapons.
            const auto name = readItemInternalName(raw - 1);
            if (!name) return std::nullopt;
            const auto index = weaponLookup_(name->c_str());
            if (!index || index > MaximumWeaponAssetIndex) return std::nullopt;
            const auto *address = module_ + WeaponDefinitionsRva + index * sizeof(void *);
            if (!readableSpan(address, sizeof(void *))) return std::nullopt;
            const auto *definition = *reinterpret_cast<const std::uint8_t *const *>(address);
            if (!readableSpan(definition, WeaponClipSizeOffset + 4)) return std::nullopt;
            const auto read = [definition](std::size_t offset) {
                return *reinterpret_cast<const std::int32_t *>(definition + offset);
            };
            // 429E10 asserts type1 and nonzero offhandClass(+1436).
            const auto kind = read(1436);
            const auto ammo = read(WeaponAmmoIndexOffset);
            const auto clip = read(WeaponClipIndexOffset);
            const auto capacity = read(WeaponClipSizeOffset);
            if (read(WeaponTypeOffset) != 1 || kind <= 0 || kind > 255 ||
                ammo <= 0 || ammo > 0x7FF || clip <= 0 || clip > 0x7FE ||
                capacity <= 0 || capacity > 0x1FF) return std::nullopt;
            // Retail semtex spawn: clip1/reserve0. The profile's explicit
            // double-ammo flag adds the second grenade, within native capacity.
            const auto count = 1u + ((equipment.doubleAmmoMask >> slot) & 1u);
            if (count > static_cast<std::uint32_t>(capacity)) return std::nullopt;
            result.weapons[slot] = {
                .weaponAssetIndex = static_cast<std::uint16_t>(index),
                .ammoIndex = static_cast<std::uint16_t>(ammo),
                .clipIndex = static_cast<std::uint16_t>(clip),
                .clipCapacity = static_cast<std::uint16_t>(capacity),
                .offhandClass = static_cast<std::uint8_t>(kind),
                .spawnCount = static_cast<std::uint8_t>(count),
                .weaponName = *name,
            };
        }
        return SV_IsEquipmentValid(result) ? std::optional{result} : std::nullopt;
    }

    std::optional<SvOffhandWeapon> EngineBindings::resolveFactorySpecialEquipment(std::string_view name) const
    {
        // CODREF(1649370): same type/slot/ammo fields as the validated session
        // equipment resolver. Only known Factory reconstruction assets enter.
        if(name!="trap_fire_zm" && name!="trap_freeze_zm" && name!="trap_shock_zm" &&
           name!="trap_shrink_zm" && name!="zombie_cymbal_monkey")return std::nullopt;
        if(!module_ || !weaponLookup_)return std::nullopt;
        const std::string ownedName(name);
        const auto index=weaponLookup_(ownedName.c_str());
        if(!index || index>MaximumWeaponAssetIndex)return std::nullopt;
        const auto *address=module_+WeaponDefinitionsRva+index*sizeof(void *);
        if(!readableSpan(address,sizeof(void *)))return std::nullopt;
        const auto *definition=*reinterpret_cast<const std::uint8_t *const *>(address);
        if(!readableSpan(definition,WeaponClipSizeOffset+4))return std::nullopt;
        const auto read=[definition](std::size_t offset){return *reinterpret_cast<const std::int32_t *>(definition+offset);};
        const auto ammo=read(WeaponAmmoIndexOffset),clip=read(WeaponClipIndexOffset),capacity=read(WeaponClipSizeOffset),kind=read(1436);
        if(read(WeaponTypeOffset)!=1 || ammo<=0 || ammo>0x7FF || clip<=0 || clip>0x7FE ||
            capacity<=0 || capacity>0x1FF || kind<=0 || kind>255)return std::nullopt;
        // Original Prototype freeze pickup adds three charges. Other counts
        // follow bounded native capacity as provisional reward policy.
        return SvOffhandWeapon{static_cast<std::uint16_t>(index),static_cast<std::uint16_t>(ammo),
            static_cast<std::uint16_t>(clip),static_cast<std::uint16_t>(capacity),
            static_cast<std::uint8_t>(kind),static_cast<std::uint8_t>(std::min(capacity,3)),ownedName};
    }

    void EngineBindings::auditEquippedEquipment() const
    {
        OlMod::DedicatedSession::LoadoutRequest request;
        if (!readProfileWeaponClasses(request))
        {
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "EQUIPMENT_AUDIT profile unavailable");
            return;
        }
        for (std::size_t c{}; c < request.classes.size(); ++c)
        {
            if (!(request.classMask & (1u << c)))
                continue;
            const auto &equipment = request.classes[c].equipment;
            std::string line = "EQUIPMENT_AUDIT character=" +
                std::to_string(request.characterIndex) + " class=" + std::to_string(c + 1);
            for (std::size_t slot{}; slot < equipment.itemIds.size(); ++slot)
            {
                const auto raw = equipment.itemIds[slot];
                const auto name = raw > 1 ? readItemInternalName(raw - 1) : std::optional<std::string>{"none"};
                line += std::string(slot ? " tactical=" : " lethal=") +
                    std::to_string(raw) + "/" + name.value_or("<unresolved>");
            }
            line += " doubleAmmoMask=" + std::to_string(equipment.doubleAmmoMask);
            const auto resolved = resolveSessionEquipment(request, static_cast<std::uint32_t>(c));
            if (resolved)
                for (const auto &weapon : resolved->weapons)
                    line += " grant=" + std::to_string(weapon.weaponAssetIndex) +
                        "/" + std::to_string(weapon.clipIndex) + "/" + std::to_string(weapon.spawnCount);
            else
                line += " grant=<unresolved>";
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
        }
    }

    void EngineBindings::auditEquippedPerks() const
    {
        OlMod::DedicatedSession::LoadoutRequest request;
        if (!readProfileWeaponClasses(request))
        {
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "PERK_AUDIT profile unavailable");
            return;
        }
        for (std::uint32_t c = 0; c < request.classes.size(); ++c)
        {
            const auto resolved = resolveSessionPerks(request, c);
            std::string line = "PERK_AUDIT character=" + std::to_string(request.characterIndex) +
                " class=" + std::to_string(c + 1);
            if (!resolved)
            {
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line + " unresolved");
                continue;
            }
            line += " profile=";
            for (const auto item : resolved->itemIds)
                line += std::to_string(item) + ",";
            line += " bits=";
            for (const auto word : resolved->bits)
                line += std::to_string(word) + ",";
            line += " abilityMask=";
            for (const auto word : resolved->abilities.mask)
                line += std::to_string(word) + ",";
            line += " values=";
            for (std::size_t i = 0; i < resolved->abilities.values.size(); ++i)
                if (resolved->abilities.values[i] != 0)
                    line += std::to_string(i) + ":" + std::to_string(resolved->abilities.values[i]) + ",";
            line += " move=" + std::to_string(resolved->abilities.moveSpeedScale) +
                " fall=" + std::to_string(resolved->abilities.fallDamageScale);
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, line);
        }
    }

    std::optional<ClientWeaponLoadout> EngineBindings::resolveClientWeaponLoadout(
        const std::string_view selectedLoadout) const
    {
        const auto characterIndex = currentCharacterIndex();
        if (!characterIndex)
            return std::nullopt;
        return resolveClientWeaponLoadout(selectedLoadout, *characterIndex);
    }

    std::optional<std::uint32_t> EngineBindings::currentCharacterIndex() const
    {
        // publicProfileReady() FIRST. sub_6B87C0 resolves "currentCharacterIndex"
        // through the profile on its first call, so it has the same precondition as
        // sub_50FF30 -- see the CODDIFF on CharacterSlotGetRva.
        if (!currentCharacterGet_ || !publicProfileReady() ||
            !profileSlotProbeEnabled())
        {
            return std::nullopt;
        }
        const auto characterIndex = currentCharacterGet_();
        if (characterIndex < 0 || characterIndex >= 12)
        {
            // SAY WHAT THE VALUE WAS. "currentCharacterIndex unavailable" is the answer this
            // gave for a number that is sitting right there, and it refused every loadout
            // capture on this build.
            //
            // 12 IS OUR BOUND, NOT THE ENGINE'S. out.exe's own consumers -- sub_6B87C0 and
            // sub_7C5BA0, which is the function that actually indexes the table -- do only
            // `if (index < 0) index = 0` and then scale by 156 with no upper check. So this
            // is stricter than the code it is modelling, and may simply be wrong here.
            // Widening it on that reasoning alone would be inventing a bound; report the
            // value and let a measurement decide.
            if (lastCharacterIndexRefusal_ != characterIndex)
            {
                lastCharacterIndexRefusal_ = characterIndex;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "currentCharacterIndex out of our 0..11 range: " +
                        std::to_string(characterIndex) +
                        " (out.exe itself only clamps negatives)");
            }
            return std::nullopt;
        }
        lastCharacterIndexRefusal_ = -2;
        return static_cast<std::uint32_t>(characterIndex);
    }

    bool EngineBindings::profileSlotProbeEnabled()
    {
        // OFF BY DEFAULT, and this is a calibration decision rather than caution.
        //
        // Reading the roster is a bounded memory read behind readableSpan and is
        // demonstrably safe -- it ran on a live client and produced the 686 measurement.
        // CALLING sub_50FF30 is a native call on the bridge thread, and its safety is NOT
        // established: it walks the public profile, formats two strings and reads through
        // a manager the game thread also owns.
        //
        // Six ClientException reports exist on this build with the same innermost frame,
        // sub_779510 +0x230, and THREE OF THEM PREDATE THIS BATCH. Today's three share a
        // different caller frame from the older three, which is suggestive and is not a
        // demonstration -- the probe ran twice with no crash, and did not run at all in
        // two runs that crashed. Nothing isolates a cause either way.
        //
        // So the unvalidated call stays off the path everyone else runs, and turns on for
        // whoever is deliberately measuring: OLMOD_PROBE_PROFILE_SLOTS=1.
        static const bool enabled = [] {
            char *value{};
            std::size_t size{};
            if (_dupenv_s(&value, &size, "OLMOD_PROBE_PROFILE_SLOTS") != 0 || !value)
                return false;
            const auto on = value[0] == '1';
            std::free(value);
            return on;
        }();
        return enabled;
    }

    bool EngineBindings::publicProfileReady() const
    {
        // The chain CodolMatchFlow.py's readPublicProfileState walks, with every hop
        // range-checked, because this runs on the bridge thread in a process whose own
        // crash handler will take an access violation before __except sees it.
        if (!module_)
            return false;
        // ProfileManagerRva IS THE MANAGER, not a pointer to it. CodolMatchFlow.py's
        // readPublicProfileState does `profileManager.add(PUBLIC_PROFILE_OFFSET)` on
        // `module.base.add(PROFILE_MANAGER_RVA)` -- no dereference anywhere, and the
        // arithmetic checks out against what it printed live this session:
        // 0x400000 + 0xE14BC48 + 0x10 = 0xE54BC58, which is the address it reported.
        //
        // The first version of this dereferenced twice and returned false forever, which
        // read as "the profile is never ready" on a run where it demonstrably was.
        const auto *profile = module_ + ProfileManagerRva + PublicProfileOffset;
        if (!readableSpan(profile, ProfileParsedOffset + 1))
            return false;
        if (!profile[ProfileParsedOffset])
            return false;
        // EQUALITY, not a mask test. `chunkMask === PROFILE_REQUIRED_CHUNK_MASK` is what
        // the tool checks, so extra bits set is NOT ready, and a subset test would call
        // a half-loaded profile ready.
        if (*reinterpret_cast<const std::uint32_t *>(profile + ProfileChunkMaskOffset) !=
            ProfileRequiredChunkMask)
        {
            return false;
        }
        // And no operation in flight.
        return *reinterpret_cast<const std::int32_t *>(
            profile + ProfileOperationOffset) == 0;
    }

    std::string EngineBindings::reportClientCharacterInfo() const
    {
        // MEASURE THE FAILING SIDE. A player being invisible is a statement about the
        // CLIENT's DObj, and every instrument this project has for it reads the
        // dedicated's own mirror instead -- which has been healthy in every run where a
        // player did not draw. This reads what the client itself will hand
        // BG_UpdatePlayerDObj.
        //
        // sub_53DF40 picks the block with
        //     (char *)dword_827F730 + 1104 * entityState.clientNum + 717648
        // for ET_PLAYER, and passes it as BG_UpdatePlayerDObj's third argument. The
        // layout is the one this file already writes on the server side: infoValid at
        // +0x00, the base model name at +0x18, ten attachment names at +0x20.
        constexpr std::size_t ClientCharacterInfoBasePointerRva = 0x7E7F730;
        constexpr std::size_t ClientCharacterInfoArrayOffset = 717648;
        constexpr std::size_t ClientCharacterInfoStride = 1104;
        constexpr std::uint32_t ReportedClients = 4;
        if (!module_)
            return {};
        const auto *const basePointer = module_ + ClientCharacterInfoBasePointerRva;
        if (!readableSpan(basePointer, sizeof(void *)))
            return {};
        // THIS RUNS OFF THE GAME THREAD, so a read can catch the engine mid-write. The
        // first version reported BASE NULL and UNREADABLE at random and those were its
        // OWN artifacts, not findings -- an instrument's noise must not be mistaken for
        // the signal it is looking for. A transient null is simply not reported.
        const auto *const base = *reinterpret_cast<const std::uint8_t *const *>(
            basePointer);
        if (!base)
            return {};

        // WHICH CLIENT PROCESS IS THIS. Both instances log to one file under one tag,
        // so "one is fine and the other is not" was only ever inferable from the DObj
        // pointers happening to differ. Say it outright.
        std::string report =
            "client characterInfo: pid=" + std::to_string(GetCurrentProcessId());
        for (std::uint32_t clientNum = 0; clientNum < ReportedClients; ++clientNum)
        {
            const auto *const info = base + ClientCharacterInfoArrayOffset +
                ClientCharacterInfoStride * clientNum;
            if (!readableSpan(info, CharacterInfoAttachmentNamesOffset))
            {
                report += " [" + std::to_string(clientNum) + "]=UNREADABLE";
                continue;
            }
            const auto valid = *reinterpret_cast<const std::uint32_t *>(info);
            // THE DObj HANDLE ITSELF, which is the thing a player being invisible is
            // actually about. sub_40AB30 reads it at +900 and bails at its very first
            // branch when the block has no models; a handle of zero on a player whose
            // characterInfo is otherwise valid says the build never produced a DObj,
            // which is a different defect from failing to resolve a character.
            constexpr std::size_t CharacterInfoDObjHandleOffset = 900;
            const auto dobj = readableSpan(
                    info + CharacterInfoDObjHandleOffset, sizeof(std::uint32_t))
                ? *reinterpret_cast<const std::uint32_t *>(
                      info + CharacterInfoDObjHandleOffset)
                : 0u;
            const auto *const name = *reinterpret_cast<const char *const *>(
                info + CharacterInfoModelNameOffset);
            // A NULL MODEL POINTER AND AN EMPTY STRING ARE DIFFERENT ANSWERS and the
            // difference is the whole point: one says the client never resolved a
            // character, the other says it resolved one and got nothing.
            // AN EMPTY NAME MUST READ AS EMPTY. readCString returns nullopt for a
            // zero-length string as well as for an unreadable one, and this probe
            // printed both as UNREADABLE -- so section 165c wrote the empty-name case
            // off as instrument noise while it was sitting in the log as the invisible
            // player itself, `valid=1 model=UNREADABLE`, run after run. Check the first
            // byte here rather than change readCString, whose other callers rely on
            // "non-empty or nothing".
            const auto model = !name
                ? std::string{ "NULL" }
                : (!readableSpan(name, 1)
                    ? std::string{ "UNREADABLE" }
                    : (!*name
                        ? std::string{ "EMPTY" }
                        : readCString(name, 128)
                              .value_or(std::string{ "UNREADABLE" })));
            // AND THE POINTER ITSELF, because UNREADABLE has been read as instrument
            // noise for a whole session and section 166 says it cannot be. cgame hands
            // every one of these slots a PERMANENT 64-byte buffer out of one pool at
            // init (0x0044B310 and 0x004555D0 walk 19 + 18 blocks of stride 1104 and
            // deal out 25 buffers each; the pool is memset 0xE740 = 37 * 1600). Nothing
            // writes the POINTER afterwards -- CG_SetupClientCharacterInfo 0x00541800
            // strncpy's INTO it. So a slot whose pointer cannot be read is not a race:
            // it says this probe is not looking at that process's characterInfo at all.
            // Print it and the question stops being arguable.
            const auto hex = [](const void *const value) {
                static constexpr char Digits[] = "0123456789abcdef";
                auto bits = reinterpret_cast<std::uintptr_t>(value);
                std::string out(sizeof(bits) * 2, '0');
                for (std::size_t index = out.size(); index-- > 0; bits >>= 4)
                    out[index] = Digits[bits & 0xFu];
                return "0x" + out;
            };
            // THE REBUILD FLAG AND THE ATTACHMENT SLOTS. BG_UpdatePlayerDObj 0x0040AB30
            // walks the ten names at +0x20 and STOPS AT THE FIRST EMPTY ONE, registering
            // every non-empty one as an XModel. When the character resolver returns no
            // names at all, 0x00541800's second loop is off by one slot and writes a TAG
            // STRING into an attachment MODEL slot -- which is what "tag index 0 kills
            // the whole player's DObj" was. A `tag_` here names that defect on sight.
            constexpr std::size_t CharacterInfoRebuildFlagOffset = 660;
            const auto rebuild = readableSpan(
                    info + CharacterInfoRebuildFlagOffset, sizeof(std::uint32_t))
                ? *reinterpret_cast<const std::uint32_t *>(
                      info + CharacterInfoRebuildFlagOffset)
                : 0u;
            std::string attachments;
            constexpr std::uint32_t ReportedAttachments = 4;
            for (std::uint32_t slot = 0; slot < ReportedAttachments; ++slot)
            {
                const auto *const attachName =
                    *reinterpret_cast<const char *const *>(
                        info + CharacterInfoAttachmentNamesOffset +
                        sizeof(void *) * slot);
                if (!attachName || !readableSpan(attachName, 1))
                    break;
                if (!*attachName)
                    break;
                const auto value = readCString(attachName, 128)
                    .value_or(std::string{ "UNREADABLE" });
                attachments += (attachments.empty() ? "" : ",") + value;
            }
            // THE REQUEST CG_SetupClientCharacterInfo BUILDS, at clientInfo + 1024.
            // Section 166b: 0x00541800 fills it from the clientState this server sends
            // and MEMSETS IT TO ZERO on its one early return
            // (`if (*(int *)(clientState + 0x150) <= 0)`). So this one field separates
            // the only two ways a name can come back empty, with no inference left:
            //
            //   request all zero      -> the modelIndex gate fired. The client's
            //                            clientState has no model index: a WIRE fault,
            //                            ours, on the way in.
            //   request populated     -> the gate passed and the resolver 0x0080E600
            //                            returned NO NAMES for that characterItemId --
            //                            the client cannot resolve that character,
            //                            which is an ITEM-TABLE fault, not a wire one.
            constexpr std::size_t CharacterInfoResolverRequestOffset = 1024;
            std::string request{ "?" };
            const auto *const requestBytes =
                info + CharacterInfoResolverRequestOffset;
            if (readableSpan(requestBytes, 64))
            {
                const auto word = [requestBytes](const std::size_t index) {
                    return *reinterpret_cast<const std::uint32_t *>(
                        requestBytes + index * sizeof(std::uint32_t));
                };
                bool bitsetSet = false;
                for (std::size_t index = 4; index < 16; ++index)
                    bitsetSet = bitsetSet || word(index) != 0;
                request = "model=" + std::to_string(word(0)) + ",variant=" +
                    std::to_string(word(1)) + ",female=" +
                    std::to_string(word(2)) + ",item=" +
                    std::to_string(word(3)) +
                    (bitsetSet ? ",overrides" : ",no-overrides");
                if (!word(0) && !word(1) && !word(2) && !word(3) && !bitsetSet)
                    request = "ALL-ZERO (the modelIndex gate fired)";
            }
            // THE CLIENT'S OWN RECEIVED clientState, which is the only thing that can
            // separate "never arrived" from "arrived and was discarded". Section 168.
            //
            // The clientinfo loop inside sub_54B3F0 walks it:
            //     mov ebx, [esp+0x24]      ; the CG object
            //     add ebx, 0x56C1C         ; clientState = ebx - 4  ->  CG + 0x56C18
            //     ...
            //     add ebx, 0x160           ; and the stride is 0x160
            // and dword_827F730 is CG + 858368 (0x4557FE), so the array sits at
            // dword_827F730 - 503016. Fields are the ones 0x00541800 reads: the model
            // index at +0x150, the character item at +0x7C, and the plain body model
            // index at +0x14 that the fallback 0x00541BD0 turns into a name.
            constexpr std::ptrdiff_t ClientStateArrayFromCharacterInfoBase = -503016;
            constexpr std::size_t ClientStateStride = 0x160;
            std::string received{ "?" };
            const auto *const clientState = base +
                ClientStateArrayFromCharacterInfoBase +
                ClientStateStride * clientNum;
            if (readableSpan(clientState, 0x158))
            {
                const auto word = [clientState](const std::size_t offset) {
                    return *reinterpret_cast<const std::uint32_t *>(
                        clientState + offset);
                };
                received = "model=" + std::to_string(word(0x150)) + ",item=" +
                    std::to_string(word(0x7C) & 0xFFFFu) + ",body=" +
                    std::to_string(word(0x14));
            }
            report += " [" + std::to_string(clientNum) + "] cs{" + received +
                // NO BATTERY READ HERE. `+0x0A4` was read from this struct for one run, to
                // settle whether the zm meter's numerator is ever non-zero -- it is not,
                // measured `battery=0` with `valid=1` -- and the client CRASHED while
                // firing shortly after, 0xC0000005 on a corrupted pointer. Isolated by
                // reverting to the last commit and firing again: no fault, so the read is
                // the prime suspect and it is gone.
                //
                // Why it was unsafe: this function RUNS OFF THE GAME THREAD, as the comment
                // above says, and the loop's only structural guard covers the first 32
                // bytes (CharacterInfoAttachmentNamesOffset). A read 164 bytes in, across
                // four slots including ones no client occupies, is a check-then-use race
                // against a struct the engine is rebuilding. A local readableSpan does not
                // close that.
                //
                // The answer it produced is recorded in re/demo-re/17-zm-hud-and-battery.md,
                // so re-adding it buys nothing.
                " req{" + request + "} valid=" +
                std::to_string(valid) + " dobj=" + std::to_string(dobj) +
                " namePtr=" + hex(name) + " rebuild=" + std::to_string(rebuild) +
                " model=" + model +
                " attach=" + (attachments.empty() ? std::string{ "-" } : attachments);
        }
        return report;
    }

    std::string EngineBindings::reportSessionMemberItemHandles() const
    {
        if (!module_)
            return "session member roster: NO MODULE";
        const auto *countSlot = module_ + SessionMemberCountRva;
        if (!readableSpan(countSlot, sizeof(std::uint32_t)))
            return "session member roster: COUNT UNREADABLE";
        const auto count = *reinterpret_cast<const std::uint32_t *>(countSlot);
        const auto *handles = module_ + SessionMemberItemHandlesRva;
        if (!readableSpan(handles, SessionMemberStride * SessionMemberCapacity))
            return "session member roster: count=" + std::to_string(count) +
                " HANDLES UNREADABLE";

        // Every slot, not just the first `count` of them: a roster that reports zero
        // while carrying handles and one that is genuinely empty are different findings,
        // and reading only `count` entries cannot tell them apart.
        // THE CHARACTER-ITEM DECODE KEY, FROM WHICHEVER PROCESS THIS IS.
        //
        // The record entries the engine wants are `rotr(itemId, 8) ^ decodeKey`
        // (encodeCharacterItemId), and this server puts RAW ids on the wire -- which is
        // why the client renders items unrelated to the loadout (section 182c). Whether
        // the server can encode FOR the client turns on one fact and nothing else:
        //
        //   same value in both processes -> the key is global, the server can encode.
        //   different values             -> it is per-profile, the server CANNOT, and
        //                                   the wire must carry something the client
        //                                   encodes with its own key.
        //
        // This reporter already runs in BOTH processes -- the log carries its output as
        // "session member roster" from the dedicated and "client-side session member
        // roster" from the client -- so printing the key here compares them with no new
        // plumbing and no guess about which side is which.
        std::string report = "session member roster: ";
        if (readableSpan(module_ + CharacterItemDecodeKeyRva, sizeof(std::uint32_t)))
        {
            char key[40]{};
            std::snprintf(key, sizeof(key), "decodeKey=0x%08X ",
                *reinterpret_cast<const std::uint32_t *>(
                    module_ + CharacterItemDecodeKeyRva));
            report += key;
        }
        else
        {
            report += "decodeKey=UNREADABLE ";
        }
        report += "count=" + std::to_string(count);
        std::size_t withHandles = 0;
        std::string detail;
        for (std::size_t member = 0; member < SessionMemberCapacity; ++member)
        {
            const auto *slot = handles + SessionMemberStride * member;
            std::string ids;
            bool any = false;
            for (std::size_t index = 0; index < SessionMemberItemHandleCount; ++index)
            {
                const auto handle = *reinterpret_cast<const std::uint32_t *>(
                    slot + index * sizeof(std::uint32_t));
                any = any || handle != 0;
                ids += (index ? "," : "") + std::to_string(handle);
            }
            if (!any)
                continue;
            ++withHandles;
            detail += " [" + std::to_string(member) + "]=" + ids;
        }
        report += " membersWithItemHandles=" + std::to_string(withHandles) + detail;
        if (!withHandles)
            report += " (roster empty)";

        return report;
    }

    std::string EngineBindings::reportProfileCharacterSlots() const
    {
        // A SEPARATE CALL, AND A SEPARATE LOG LINE, on purpose. The roster report above is a
        // bounded memory read and is safe. This one makes a NATIVE CALL whose safety on the
        // bridge thread is not established, so if it takes the process down the roster line
        // has already been written. An instrument that dies before it reports is worth
        // nothing (section 44a).
        if (!profileSlotProbeEnabled())
            return {};
        const auto characterIndex = currentCharacterIndex();
        std::string report = "profile character slots: currentCharacter=";
        report += characterIndex ? std::to_string(*characterIndex) : "UNAVAILABLE";
        if (!characterIndex || !characterSlotGet_)
            return report + " slots=NOT READABLE";

        // The question this exists to answer: the roster's twelve item handles and the
        // profile's characterClasses[<character>].slots[0..11] are two sources for what
        // might be the same twelve ids. If they agree, there is one source. If they do
        // not, they are different things and only one of them is section 48's input.
        std::string slots;
        std::size_t nonZero = 0;
        // NINE, not CharacterItemCount's twelve -- see CharacterProfileSlotCount.
        for (std::size_t index = 0; index < CharacterProfileSlotCount; ++index)
        {
            const auto value = invokeCharacterSlotGet(
                characterSlotGet_, static_cast<int>(*characterIndex),
                static_cast<int>(index));
            slots += (index ? "," : "");
            slots += value ? std::to_string(*value) : "x";
            if (value && *value)
                ++nonZero;
        }
        return report + " slots=" + slots + " nonZero=" + std::to_string(nonZero);
    }

    std::optional<OlMod::DedicatedSession::LoadoutRequest>
        EngineBindings::captureClientLoadoutRequest() const
    {
        // ONE LINE THAT SAYS WHAT WAS SERVED AND FROM WHERE. `profile` = the five
        // real classes; `record-mirror` = the fallback one class copied across all
        // five. When two clients hold different classes and a switch changes the gun
        // this must read `profile`; if it says `record-mirror`, the switch is a no-op
        // and the profile read failed -- exactly the difference the party needs.
        const auto reportLoadoutClasses =
            [this](const OlMod::DedicatedSession::LoadoutRequest &request,
                   const char *const source) {
                std::string report =
                    std::string("client loadout classes source=") + source +
                    " character=" + std::to_string(request.characterIndex) +
                    " classMask=" + std::to_string(request.classMask);
                for (std::size_t classIndex = 0;
                     classIndex < request.classes.size(); ++classIndex)
                {
                    if (!(request.classMask & (1u << classIndex)))
                        continue;
                    const auto &weapons = request.classes[classIndex].weapons;
                    const auto name = readItemInternalName(weapons[0].itemId);
                    report += " class" + std::to_string(classIndex) + " " +
                        std::to_string(weapons[0].itemId) + "/" +
                        std::to_string(weapons[1].itemId) +
                        " [" + (name ? *name : std::string("?")) + "]";
                }
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, report);
            };

        // THE CLIENT'S OWN RECORD FIRST, AND IT NEEDS NONE OF THE GATES BELOW.
        //
        // Everything after this point runs through sub_50FF30, and sub_50FF30 is switched
        // OFF BY DEFAULT: profileSlotProbeEnabled() wants OLMOD_PROBE_PROFILE_SLOTS=1
        // because calling it on the bridge thread has unestablished safety. That gate sits
        // inside currentCharacterIndex(), so the very first thing this function did was
        // refuse -- which is why binding the record changed nothing until now, and why the
        // failure read as "currentCharacterIndex unavailable" rather than as a disabled
        // probe.
        //
        // sub_7C5BA0 is not that function. It is the record builder the client runs for
        // itself, it carries the character item ids as well as the weapons, and it needs
        // neither the probe nor our character index. So try it before anything is gated.
        {
            // THE FIVE REAL CLASSES, FIRST, AND WITH NO ROOM. The profile document
            // holds all five per character and is loaded whenever the client is
            // logged in, so this answers even a client sitting at the menu -- which
            // is what lets a player join through the dev panel instead of being
            // driven in. It is the source that makes an in-match class switch change
            // the weapon; the record path below only ever held the one selected
            // class and needs the room cache besides.
            OlMod::DedicatedSession::LoadoutRequest fromProfile{};
            if (readProfileWeaponClasses(fromProfile) &&
                OlMod::DedicatedSession::valid(fromProfile))
            {
                reportLoadoutClasses(fromProfile, "profile");
                lastLoadoutRefusal_ = nullptr;
                return fromProfile;
            }
            // FALLBACK: the one-class record, mirrored. Needs the room cache, and
            // makes a switch a no-op, but one correct class still beats none.
            OlMod::DedicatedSession::LoadoutRequest fromClientRecord{};
            if (readLoadoutRecord(fromClientRecord) &&
                OlMod::DedicatedSession::valid(fromClientRecord))
            {
                reportLoadoutClasses(fromClientRecord, "record-mirror");
                lastLoadoutRefusal_ = nullptr;
                return fromClientRecord;
            }
        }

        // NAME THE GATE THAT CLOSED. Every return below used to be a bare nullopt, so the
        // only thing a capture failure could say was "NO_LOADOUT" -- which is the outcome,
        // not the cause, and it is what made a fix look like it had not run when the truth
        // was that the function returned four gates earlier. Edge-triggered on the reason,
        // so a healthy client says nothing at all and a stuck one says it once.
        const auto refuse = [this](const char *reason)
            -> std::optional<OlMod::DedicatedSession::LoadoutRequest>
        {
            if (lastLoadoutRefusal_ != reason)
            {
                lastLoadoutRefusal_ = reason;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("client loadout capture refused: ") + reason);
            }
            return std::nullopt;
        };

        const auto characterIndex = currentCharacterIndex();
        if (!characterIndex)
            return refuse("currentCharacterIndex unavailable");
        if (!module_ || !characterCurrentItemsCopy_ ||
            !readableSpan(
                module_ + CharacterItemDecodeKeyRva,
                sizeof(std::uint32_t)))
        {
            return refuse("character item bindings unavailable");
        }

        // THE ITEM IDS COME FROM THE PROFILE, NOT FROM THE ROSTER. sub_619E90's index is
        // a SESSION MEMBER index (section 65c) and this is a character index; the two
        // arrays are 18 and 12 long and are not interchangeable. sub_50FF30 is indexed
        // the way this function actually has an index for -- it formats
        // characterClasses[<character>].slots[<slot>] and reads the public profile -- and
        // CodolMatchFlow.py already calls it on this build every run.
        if (!characterSlotGet_)
            return refuse("characterSlotGet unbound");
        if (!publicProfileReady())
            return refuse("public profile not ready");
        if (!profileSlotProbeEnabled())
            return refuse("profile slot probe disabled");

        OlMod::DedicatedSession::LoadoutRequest request{
            .characterIndex = *characterIndex,
        };
        // NINE. request.characterItemIds is twelve wide because the RECORD is; the
        // PROFILE's slots array is not, and reading its tenth entry is a fault.
        static_assert(CharacterProfileSlotCount <=
            OlMod::DedicatedSession::CharacterItemCount);
        std::array<std::uint32_t, CharacterProfileSlotCount> profileSlots{};
        for (std::size_t index = 0; index < CharacterProfileSlotCount; ++index)
        {
            const auto slot = invokeCharacterSlotGet(
                characterSlotGet_, static_cast<int>(*characterIndex),
                static_cast<int>(index));
            if (!slot)
                continue;
            if (*slot < 0 || *slot > 0xFFFF)
                return refuse("character slot out of range");
            profileSlots[index] = static_cast<std::uint32_t>(*slot);
        }
        // SAY WHICH CHARACTER THIS IS AND WHAT ITS TWELVE SLOTS HOLD.
        //
        // Every model request this server has ever made carries item=545 and resolves
        // to fpa_goose_ss_m_15 -- one item and one model across every session in 30 MB
        // of log -- and the only character index ever printed is 0, from the
        // presentation stub. That is consistent with TWO different worlds: the player
        // really is on character 0, or currentCharacterGet_ is not reading their
        // selection at all. Nothing currently logged separates them, because the index
        // is only ever printed when it is OUT OF RANGE.
        //
        // Deduped on the whole tuple, so a player who never changes character prints
        // one line and a player who does prints a second. That is the measurement:
        // pick a different character in the menu and see whether this moves.
        {
            std::string line = "character capture: index=" +
                std::to_string(*characterIndex) + " slots=";
            for (std::size_t index = 0; index < profileSlots.size(); ++index)
                line += (index ? "," : "") + std::to_string(profileSlots[index]);
            static std::string reported;
            if (reported != line)
            {
                reported = line;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        // Same packing as the document path, same placer.
        placeCharacterItemsByRecordEntry(profileSlots, request.characterItemIds);
        if (currentCharacterIndex() != characterIndex)
            return refuse("character index moved mid-read");
        if (!request.characterItemIds.front())
            return refuse("character slot 0 is empty");

        // THE CLIENT'S OWN RECORD FIRST. It is the only source that reflects what the
        // player is looking at; the profile path below reads a document that is not the
        // player's class and the staged path is unbound on this build.
        const auto fromRecord = readLoadoutRecord(request);

        for (std::uint32_t classIndex = 0;
             classIndex < request.classes.size(); ++classIndex)
        {
            // Class 0 came from the record, and nothing below is a better source for it.
            if (fromRecord && classIndex == 0)
                continue;

            OlMod::DedicatedSession::ClassRequest loadoutClass;
            // THE PROFILE FIRST, the staged array only if it is ever bound.
            // readProfileWeaponRequest reads weaponClasses[<class>] out of the
            // stored document, which is the loadout the player actually saved;
            // the staged path stays as written for any build where its address
            // IS established.
            const auto firstSlot = *characterIndex * 10 + classIndex * 2;
            const auto primary =
                readProfileWeaponRequest(classIndex, false, loadoutClass.weapons[0]) ||
                readStagedWeaponRequest(firstSlot, loadoutClass.weapons[0]);
            if (!primary)
                continue;
            // A SECONDARY IS OPTIONAL. Insisting on one dropped every class
            // that had none, which is most of them early on.
            if (!readProfileWeaponRequest(classIndex, true, loadoutClass.weapons[1]))
            {
                static_cast<void>(readStagedWeaponRequest(
                    firstSlot + 1, loadoutClass.weapons[1]));
            }
            request.classes[classIndex] = loadoutClass;
            request.classMask |= static_cast<std::uint8_t>(1u << classIndex);
        }
        if (currentCharacterIndex() != characterIndex)
            return refuse("character index moved during the class walk");
        if (!OlMod::DedicatedSession::valid(request))
        {
            return refuse(fromRecord ? "request invalid despite the client record"
                                     : "request invalid and the client record was empty");
        }
        lastLoadoutRefusal_ = nullptr;
        return request;
    }

    std::optional<ClientCharacterPresentation>
        EngineBindings::resolveClientCharacterPresentation(
            const std::uint32_t characterIndex) const
    {
        const auto request = captureClientLoadoutRequest();
        if (!request || request->characterIndex != characterIndex)
            return std::nullopt;
        const auto presentation = resolveSessionCharacterPresentation(*request);
        if (currentCharacterIndex() != characterIndex)
            return std::nullopt;
        return presentation;
    }

    std::optional<ClientCharacterPresentation>
        EngineBindings::resolveSessionCharacterPresentation(
            const OlMod::DedicatedSession::LoadoutRequest &request) const
    {
        // CODREF(character_customization): CODOL
        // CopyCurrentItems 0x00568860, BuildClientInfo 0x00569B90 and
        // ResolveSelectionIds 0x0040CA30 establish the item-name -> eleven
        // selection-ID pipeline below. BO1/Ghosts have no marketplace-derived
        // equivalent; they constrain server presentation ownership only.
        // CODDIFF(g_update_client_info): this source adapter recreates CODOL's
        // retained client-side selection input from frozen session assets. It
        // is not the deleted dedicated G_UpdateClientInfo producer.
        characterPresentationResolveFailure_.store(
            ClientCharacterPresentationResolveFailure::InvalidRequest,
            std::memory_order_relaxed);
        characterPresentationResolveRecordIndex_.store(
            0xFFFFFFFFu, std::memory_order_relaxed);
        characterPresentationResolveItemId_.store(0, std::memory_order_relaxed);
        if (!module_ || !characterSelectionResolve_ || !configStringGet_ ||
            !OlMod::DedicatedSession::valid(request))
        {
            return std::nullopt;
        }

        std::array<std::string, 11> internalNames{};
        std::array<const char *, 11> internalNamePointers{};
        for (std::size_t recordIndex = 0;
             recordIndex < request.characterItemIds.size(); ++recordIndex)
        {
            const auto nameIndex = CharacterRecordToSelectionName[recordIndex];
            const auto itemId = request.characterItemIds[recordIndex];
            if (nameIndex == internalNames.size() || !itemId)
                continue;
            const auto internalName = readItemInternalName(itemId);
            if (!internalName)
            {
                characterPresentationResolveFailure_.store(
                    ClientCharacterPresentationResolveFailure::ItemName,
                    std::memory_order_relaxed);
                characterPresentationResolveRecordIndex_.store(
                    static_cast<std::uint32_t>(recordIndex),
                    std::memory_order_relaxed);
                characterPresentationResolveItemId_.store(
                    itemId, std::memory_order_relaxed);
                return std::nullopt;
            }
            internalNames[nameIndex] = *internalName;
            internalNamePointers[nameIndex] = internalNames[nameIndex].c_str();
        }

        ClientCharacterPresentation presentation{
            .characterIndex = request.characterIndex,
        };
        const auto selectionResolver = characterSelectionResolve_;
        const auto *names = internalNamePointers.data();
        auto *selectionIds = presentation.selectionIds.data();
        __asm
        {
            mov eax, names
            push selectionIds
            call selectionResolver
            add esp, 4
        }
        if (std::ranges::none_of(presentation.selectionIds, [](const auto value) {
                return value != 0;
            }))
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::Selection,
                std::memory_order_relaxed);
            return std::nullopt;
        }

        const auto *baseItemDefinition = readItemDefinition(
            request.characterItemIds[0]);
        const auto *characterDefinitionsSlot =
            module_ + CharacterItemDefinitionTableRva;
        const auto *characterDefinitionCountSlot =
            module_ + CharacterItemDefinitionCountRva;
        if (!baseItemDefinition ||
            !readableSpan(characterDefinitionsSlot, sizeof(const std::uint8_t *)) ||
            !readableSpan(characterDefinitionCountSlot, sizeof(std::uint32_t)))
        {
            characterPresentationResolveFailure_.store(
                baseItemDefinition
                    ? ClientCharacterPresentationResolveFailure::
                        CharacterDefinitionTable
                    : ClientCharacterPresentationResolveFailure::
                        BaseItemDefinition,
                std::memory_order_relaxed);
            characterPresentationResolveRecordIndex_.store(
                0, std::memory_order_relaxed);
            characterPresentationResolveItemId_.store(
                request.characterItemIds[0], std::memory_order_relaxed);
            return std::nullopt;
        }
        const auto characterDefinitionIndex =
            *reinterpret_cast<const std::uint16_t *>(baseItemDefinition + 2);
        const auto *characterDefinitions =
            *reinterpret_cast<std::uint8_t *const *>(characterDefinitionsSlot);
        const auto characterDefinitionCount =
            *reinterpret_cast<const std::uint32_t *>(characterDefinitionCountSlot);
        if (!characterDefinitions ||
            characterDefinitionIndex >= characterDefinitionCount)
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::CharacterDefinitionTable,
                std::memory_order_relaxed);
            return std::nullopt;
        }
        const auto *characterDefinition = characterDefinitions +
            characterDefinitionIndex * CharacterItemDefinitionSize;
        if (!readableSpan(characterDefinition, CharacterItemDefinitionSize) ||
            characterDefinition[2] > 1)
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::CharacterDefinition,
                std::memory_order_relaxed);
            return std::nullopt;
        }
        presentation.female = characterDefinition[2] != 0;
        const auto colorSelector =
            CODOL_CharacterColorSelectorFromDefinitionValue(
                characterDefinition[3]);
        if (!colorSelector)
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::CharacterDefinition,
                std::memory_order_relaxed);
            return std::nullopt;
        }
        presentation.color = *colorSelector;

        if (!CCS_EnsureInitialized())
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::ConstantConfigStrings,
                std::memory_order_relaxed);
            return std::nullopt;
        }
        for (std::uint16_t index = 1; index <= MaximumWeaponAssetIndex; ++index)
        {
            // OLMOD(character-viewhands-bootstrap): resolving a CCS index by
            // the fixed tf141 name avoids a numeric index, but is still a
            // character-specific recovery fallback. It is deliberately kept
            // separate from the proven selection parser above.
            const auto name = readCString(
                nativeConfigString(ModelConfigStringBase + index), 128);
            if (name && *name == GenericCharacterViewhands)
            {
                presentation.viewmodelIndex = index;
                break;
            }
        }
        if (!presentation.viewmodelIndex)
        {
            characterPresentationResolveFailure_.store(
                ClientCharacterPresentationResolveFailure::ViewmodelConfigString,
                std::memory_order_relaxed);
            return std::nullopt;
        }
        characterPresentationResolveFailure_.store(
            ClientCharacterPresentationResolveFailure::None,
            std::memory_order_relaxed);
        return presentation;
    }

    ClientCharacterPresentationResolveStatus
        EngineBindings::characterPresentationResolveStatus() const
    {
        return {
            .failure = characterPresentationResolveFailure_.load(
                std::memory_order_relaxed),
            .recordIndex = characterPresentationResolveRecordIndex_.load(
                std::memory_order_relaxed),
            .itemId = characterPresentationResolveItemId_.load(
                std::memory_order_relaxed),
        };
    }

    std::optional<ClientWeaponLoadout>
        EngineBindings::resolveSessionWeaponLoadout(
            const OlMod::DedicatedSession::LoadoutRequest &request,
            const std::uint32_t classIndex) const
    {
        if (!OlMod::DedicatedSession::valid(request) ||
            classIndex >= request.classes.size() ||
            !(request.classMask & (1u << classIndex)))
        {
            return std::nullopt;
        }
        ClientWeaponLoadout loadout{
            .characterIndex = request.characterIndex,
            .classIndex = classIndex,
        };
        const auto &loadoutClass = request.classes[classIndex];
        if (!resolveWeaponRequest(loadoutClass.weapons[0], loadout.primary) ||
            !resolveWeaponRequest(loadoutClass.weapons[1], loadout.secondary))
        {
            return std::nullopt;
        }
        return loadout;
    }

    std::optional<ClientWeaponLoadout> EngineBindings::resolveClientWeaponLoadout(
        const std::string_view selectedLoadout,
        const std::uint32_t characterIndex) const
    {
        loadoutResolveFailure_.store(
            ClientLoadoutResolveFailure::None,
            std::memory_order_relaxed);
        if (selectedLoadout.size() != 7 ||
            !selectedLoadout.starts_with("custom") || selectedLoadout[6] < '1' ||
            selectedLoadout[6] > '5' || characterIndex >= 12)
        {
            return std::nullopt;
        }

        const auto classIndex = static_cast<std::uint32_t>(selectedLoadout[6] - '1');
        const auto firstSlot = characterIndex * 10 + classIndex * 2;
        ClientWeaponLoadout loadout{
            .characterIndex = characterIndex,
            .classIndex = classIndex,
        };
        OlMod::DedicatedSession::ClassRequest loadoutClass;
        if (!readStagedWeaponRequest(firstSlot, loadoutClass.weapons[0]) ||
            !readStagedWeaponRequest(firstSlot + 1, loadoutClass.weapons[1]) ||
            !resolveWeaponRequest(loadoutClass.weapons[0], loadout.primary) ||
            !resolveWeaponRequest(loadoutClass.weapons[1], loadout.secondary))
        {
            return std::nullopt;
        }
        return loadout;
    }

    std::optional<std::string> EngineBindings::readMapEntityString(
        const std::string_view mapName) const
    {
        if (!dbFindXAssetHeader_ || !validBookingName(mapName))
            return std::nullopt;

        // A CAMPAIGN MAP NAMES ITS MapEnts ".mapents"; AN MP MAP REUSES THE BSP
        // NAME. Measured by decrypting both zones:
        //
        //   mp_nuked                    maps/mp/mp_nuked.d3dbsp        (no .mapents)
        //   coop_training_mp_cargoship  maps/mp/....mapents            (no .d3dbsp)
        //
        // Building only the .d3dbsp form made this return nullopt on every coop
        // level, which surfaced as `world spawn pending stage=map_entity_asset`,
        // then no entities, then `spawn refused ... NO_SPAWN_POINT` -- a fully
        // rendered map the player cannot stand in. HANDOFF section 152t.
        const std::string map(mapName);
        struct MapEntsCandidate
        {
            std::uint32_t assetType;
            std::string name;
        };
        const std::array<MapEntsCandidate, 2> candidates{
            MapEntsCandidate{
                AssetTypeMapEnts, "maps/mp/" + map + ".d3dbsp" },
            MapEntsCandidate{
                AssetTypeAddonMapEnts, "maps/mp/" + map + ".mapents" },
        };
        std::string assetPath;
        const MapEnts *mapEnts{};
        std::optional<std::size_t> mapEntsBytes;
        for (const auto &candidate : candidates)
        {
            const auto header =
                findXAsset(candidate.assetType, candidate.name.c_str(), false);
            const auto *const found = static_cast<const MapEnts *>(header.data);
            const auto bytes = readableBytes(found);
            if (bytes && *bytes >= sizeof(*found))
            {
                assetPath = candidate.name;
                mapEnts = found;
                mapEntsBytes = bytes;
                break;
            }
        }
        if (!mapEnts)
            return std::nullopt;

        const auto assetName = readCString(mapEnts->name, 256);
        if (!assetName || *assetName != assetPath || !mapEnts->entityString ||
            mapEnts->numEntityChars <= 0 ||
            static_cast<std::size_t>(mapEnts->numEntityChars) > MaximumMapEntityChars)
        {
            return std::nullopt;
        }

        const auto entityChars = static_cast<std::size_t>(mapEnts->numEntityChars);
        if (!readableSpan(mapEnts->entityString, entityChars))
            return std::nullopt;

        std::string result(mapEnts->entityString, entityChars);
        while (!result.empty() && result.back() == '\0')
            result.pop_back();
        if (result.empty() || result.find('\0') != std::string::npos)
            return std::nullopt;
        return result;
    }

    std::optional<std::vector<SvZmVolumeHull>>
        EngineBindings::resolveTriggerModelHulls(
            const std::string_view mapName,
            const std::uint32_t triggerModel) const
    {
        if (!dbFindXAssetHeader_ || !validBookingName(mapName))
            return std::nullopt;

        const std::string map(mapName);
        const std::array<std::string, 2> assetPaths{
            "maps/mp/" + map + ".d3dbsp",
            "maps/mp/" + map + ".mapents",
        };
        const MapEntsWithTriggers *mapEnts{};
        for (const auto &candidate : assetPaths)
        {
            const auto header =
                findXAsset(AssetTypeMapEnts, candidate.c_str(), false);
            const auto *const found =
                static_cast<const MapEntsWithTriggers *>(header.data);
            const auto bytes = readableBytes(found);
            if (bytes && *bytes >= sizeof(*found))
            {
                mapEnts = found;
                break;
            }
        }
        if (!mapEnts)
            return std::nullopt;

        // EVERY BOUND CHECKED BEFORE ANY READ. These arrays are reached through
        // pointers in a foreign process image; a wrong stride still yields plausible
        // floats, so refuse rather than return something shaped correctly.
        constexpr std::int32_t MaximumTriggerModels = 4096;
        constexpr std::int32_t MaximumTriggerHulls = 65535;
        constexpr std::int32_t MaximumTriggerSlabs = 65535;
        if (mapEnts->modelCount <= 0 || mapEnts->modelCount > MaximumTriggerModels ||
            mapEnts->hullCount < 0 || mapEnts->hullCount > MaximumTriggerHulls ||
            mapEnts->slabCount < 0 || mapEnts->slabCount > MaximumTriggerSlabs ||
            !mapEnts->models || !mapEnts->hulls)
        {
            return std::nullopt;
        }
        if (triggerModel >= static_cast<std::uint32_t>(mapEnts->modelCount))
            return std::nullopt;
        if (!readableSpan(mapEnts->models,
                static_cast<std::size_t>(mapEnts->modelCount)) ||
            !readableSpan(mapEnts->hulls,
                static_cast<std::size_t>(mapEnts->hullCount)))
        {
            return std::nullopt;
        }
        if (mapEnts->slabCount > 0 &&
            (!mapEnts->slabs ||
             !readableSpan(mapEnts->slabs,
                 static_cast<std::size_t>(mapEnts->slabCount))))
        {
            return std::nullopt;
        }

        const auto &model = mapEnts->models[triggerModel];
        if (static_cast<std::int32_t>(model.firstHull) + model.hullCount >
            mapEnts->hullCount)
        {
            return std::nullopt;
        }

        std::vector<SvZmVolumeHull> hulls;
        hulls.reserve(model.hullCount);
        for (std::uint16_t index = 0; index < model.hullCount; ++index)
        {
            const auto &hull = mapEnts->hulls[model.firstHull + index];
            if (static_cast<std::int32_t>(hull.firstSlab) + hull.slabCount >
                mapEnts->slabCount)
            {
                return std::nullopt;
            }
            SvZmVolumeHull out{
                .midpoint = hull.midpoint,
                .halfSize = hull.halfSize,
            };
            out.slabs.reserve(hull.slabCount);
            for (std::uint16_t slab = 0; slab < hull.slabCount; ++slab)
            {
                const auto &source = mapEnts->slabs[hull.firstSlab + slab];
                out.slabs.push_back(SvZmVolumeSlab{
                    .direction = source.direction,
                    .midPoint = source.midPoint,
                    .halfSize = source.halfSize,
                });
            }
            hulls.push_back(std::move(out));
        }
        return hulls;
    }

    std::optional<SvGlassMapMetadata>
        EngineBindings::resolveGlassMapMetadata(
            const std::string_view mapName) const
    {
        if (!dbFindXAssetHeader_ || !dbIsXAssetDefault_ ||
            !validBookingName(mapName))
        {
            return std::nullopt;
        }

        const std::string map(mapName);
        std::vector<std::string> assetPaths{
            "maps/mp/" + map + ".d3dbsp",
        };
        // The campaign zone is an add-on layered over the stock multiplayer
        // cargo ship. Its own fastfile has no FxWorld, just as it has no
        // clipmap, so resolve the same borrowed mp_cargoship world used by
        // initializeLevelWorld.
        if (const auto at = map.rfind("mp_"); at != std::string::npos && at != 0)
            assetPaths.push_back("maps/mp/" + map.substr(at) + ".d3dbsp");

        const NativeFxWorld *world{};
        std::string assetPath;
        for (const auto &candidate : assetPaths)
        {
            if (dbIsXAssetDefault_(AssetTypeFxMap, candidate.c_str()))
                continue;
            const auto header = findXAsset(
                AssetTypeFxMap, candidate.c_str(), false);
            const auto *const found =
                static_cast<const NativeFxWorld *>(header.data);
            if (!readableSpan(found, sizeof(*found)))
                continue;
            const auto assetName = readCString(found->name, 256);
            if (!assetName || *assetName != candidate)
                continue;
            world = found;
            assetPath = candidate;
            break;
        }
        if (!world)
            return std::nullopt;

        const auto &glass = world->glassSystem;
        // Kept after section 93 settled both bounds, because it is the line that says WHICH
        // number refused a map, and the two live maxima have only 7% and 14% of slack. It costs
        // one line per map load and it is silent on a map with no glass.
        {
            char glassLine[192]{};
            std::snprintf(
                glassLine, sizeof(glassLine),
                "fxglass header map=%.32s definitions=%u pieceLimit=%u "
                "pieceWords=%u initialPieces=%u cells=%u active=%u",
                std::string(mapName).c_str(),
                glass.definitionCount, glass.pieceLimit, glass.pieceWordCount,
                glass.initialPieceCount, glass.cellCount, glass.activePieceCount);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, glassLine);
        }
        if (glass.definitionCount > MaximumFxGlassDefinitionCount ||
            glass.pieceLimit > MaximumFxGlassPieceLimit ||
            glass.initialPieceCount > SvGlassPieceCount ||
            glass.initialPieceCount > glass.pieceLimit ||
            // The two relations section 93 measured on 27 of 27 glassed maps. A map that
            // breaks either was not built by this game's compiler, and reading its piece
            // array on the strength of a header that disagrees with itself is the thing
            // these bounds exist to prevent.
            (glass.pieceLimit &&
                (glass.pieceWordCount != ((glass.pieceLimit + 31) >> 5) ||
                    glass.pieceLimit != glass.initialPieceCount + SvGlassPieceCount)) ||
            (glass.initialPieceCount &&
                (!glass.definitionCount || !readableSpan(
                    glass.initialPieceStates,
                    static_cast<std::size_t>(glass.initialPieceCount) *
                        sizeof(*glass.initialPieceStates)))))
        {
            return std::nullopt;
        }

        SvGlassMapMetadata result;
        result.definitionCount = glass.definitionCount;
        result.initialPieces.reserve(glass.initialPieceCount);
        for (std::uint32_t index = 0; index < glass.initialPieceCount; ++index)
        {
            const auto &piece = glass.initialPieceStates[index];
            const auto finite = [](const auto &values) {
                return std::ranges::all_of(values, [](const float value) {
                    return std::isfinite(value);
                });
            };
            if (!finite(piece.quaternion) || !finite(piece.origin) ||
                !finite(piece.textureCoordinateOrigin) ||
                !std::isfinite(piece.radius) || piece.radius < 0.0f ||
                !std::isfinite(piece.doubledArea) || piece.doubledArea < 0.0f ||
                piece.definitionIndex >= glass.definitionCount)
            {
                return std::nullopt;
            }
            result.initialPieces.push_back({
                .quaternion = piece.quaternion,
                .origin = piece.origin,
                .radius = piece.radius,
                .textureCoordinateOrigin = piece.textureCoordinateOrigin,
                .supportMask = piece.supportMask,
                .doubledArea = piece.doubledArea,
                .definitionIndex = piece.definitionIndex,
                .vertexCount = piece.vertexCount,
                .fanDataCount = piece.fanDataCount,
            });
        }
        return result;
    }

    std::optional<std::uint8_t> EngineBindings::directionToByte(
        const std::array<float, 3> &direction) const
    {
        if (!valid() || !std::ranges::all_of(
                direction, [](const float value) {
                    return std::isfinite(value);
                }))
        {
            return std::nullopt;
        }

        constexpr std::size_t DirectionCount = 162;
        const auto *const directions = reinterpret_cast<
            const std::array<float, 3> *>(module_ + ByteDirectionsRva);
        float bestDot{};
        std::uint8_t best{};
        for (std::size_t index = 0; index < DirectionCount; ++index)
        {
            const auto &candidate = directions[index];
            if (!std::ranges::all_of(candidate, [](const float value) {
                    return std::isfinite(value);
                }))
            {
                return std::nullopt;
            }
            const auto dot = direction[0] * candidate[0] +
                direction[1] * candidate[1] +
                direction[2] * candidate[2];
            if (!std::isfinite(dot))
                return std::nullopt;
            if (dot > bestDot)
            {
                bestDot = dot;
                best = static_cast<std::uint8_t>(index);
            }
        }
        return best;
    }

    std::vector<std::pair<std::uint16_t, std::string>>
        EngineBindings::modelConfigStringBand() const
    {
        // MAP LOAD ONLY. One pass over up to 1024 configstrings; section 119q is
        // the record of what this kind of scan does when run per frame.
        std::vector<std::pair<std::uint16_t, std::string>> band;
        if (!configStringGet_ || !CCS_Initialized())
            return band;
        for (std::uint16_t index = 1; index < ModelConfigStringCount; ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(ModelConfigStringBase + index), 128);
            if (candidate && !candidate->empty())
                band.emplace_back(index, *candidate);
        }
        return band;
    }

    std::optional<std::array<float,3>> EngineBindings::weaponDisplayBodyCenter(
        const std::uint16_t weaponAssetIndex) const
    {
        // CODREF(actor_grounded_adapter): 520263 -> 51FE00 -> 431B00 selects
        // WeaponDef+24 for a plain weapon; modular records use 5236-byte entries
        // at019E30F0, count01988634, world-model count+146 and pointers+4444.
        // Only read an exact-name resident record, never call the assembler or
        // allocate a native model during a box roll. Live M9/AK/trap/box captures
        // corroborate the XModel Bounds at+140. Root tags must be zero: child
        // attachment bounds use a different coordinate frame.
        const auto name=readWeaponDefinitionName(weaponAssetIndex);
        if(!name || name->empty())return std::nullopt;
        const std::uint8_t *model{};
        if(name->front()=='*') {
            constexpr std::uintptr_t RecordCountRva=0x1588634;
            constexpr std::uintptr_t RecordsRva=0x15E30F0;
            constexpr std::size_t Stride=5236;
            const auto *count=reinterpret_cast<const std::uint32_t *>(module_+RecordCountRva);
            if(!readableSpan(count,sizeof(*count)) || *count>WeaponConfigStringCount)return std::nullopt;
            for(std::uint32_t i=0;i<*count;++i) {
                const auto *record=module_+RecordsRva+Stride*i;
                if(!readableSpan(record,Stride))return std::nullopt;
                const auto candidate=readCString(reinterpret_cast<const char *>(record),128);
                if(!candidate || *candidate!=*name)continue;
                if(!record[146]) {
                    const auto parent=*reinterpret_cast<const std::uint32_t *>(record+152);
                    if(!parent || parent>=*count)return std::nullopt;
                    record=module_+RecordsRva+Stride*parent;
                    if(!readableSpan(record,Stride))return std::nullopt;
                }
                if(!record[146] || record[146]>32 ||
                    *reinterpret_cast<const std::uint16_t *>(record+4412)!=0)return std::nullopt;
                model=*reinterpret_cast<const std::uint8_t *const *>(record+4444);
                break;
            }
        } else {
            const auto *slot=module_+WeaponDefinitionsRva+sizeof(void *)*weaponAssetIndex;
            if(!readableSpan(slot,sizeof(void *)))return std::nullopt;
            const auto *definition=*reinterpret_cast<const std::uint8_t *const *>(slot);
            if(!readableSpan(definition,28))return std::nullopt;
            model=*reinterpret_cast<const std::uint8_t *const *>(definition+24);
        }
        if(!readableSpan(model,0x158))return std::nullopt;
        const auto modelName=readCString(*reinterpret_cast<const char *const *>(model),128);
        if(!modelName || *modelName=="tag_origin" ||
            findXAsset(AssetTypeXModel,modelName->c_str(),false).data!=model)return std::nullopt;
        TraceBounds bounds{};
        std::memcpy(&bounds,model+0x140,sizeof(bounds));
        const auto bounded=[](float x){return std::isfinite(x) && std::abs(x)<512.0f;};
        if(!std::ranges::all_of(bounds.midpoint,bounded) ||
            !std::ranges::all_of(bounds.halfSize,[&](float x){return bounded(x) && x>=0;}) ||
            bounds.halfSize[0]<=0 || bounds.halfSize[1]<=0)return std::nullopt;
        return bounds.midpoint;
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveModelConfigStringIndex(
            const std::string_view modelName) const
    {
        if (!configStringGet_ || !dbFindXAssetHeader_ || !CCS_Initialized() ||
            modelName.empty() || modelName.size() >= 128 ||
            modelName.front() == '*' ||
            modelName.find('\0') != std::string_view::npos)
        {
            return std::nullopt;
        }
        // Spawning one actor used to walk all 1023 model configstrings for the
        // body and then do the same walk for its head.  The measured Factory
        // opening burst consequently stopped the authoritative frame for
        // 170-320 ms on every successful spawn.
        //
        // This is deliberately a validated hint rather than a process-lifetime
        // asset-index cache.  The client and dedicated rebuild this namespace at
        // every map load; before reusing an index, read that slot from the CURRENT
        // configstring table and require its text to remain byte-for-byte equal.
        // A new map therefore turns a stale hint into one ordinary full scan, then
        // refreshes it.  This keeps the map-generation safety of the original
        // resolver while reducing steady-state actor spawns from 2046 native
        // configstring reads to two.  Consult it before DB_FindXAssetHeader too:
        // byte-for-byte equality in the current model configstring band already
        // proves the model is published for this map, and the native asset lookup
        // was still being paid twice for every otherwise-cached zombie spawn.
        static std::mutex modelHintMutex;
        static std::unordered_map<std::string, std::uint16_t> modelHints;
        const std::string requestedModelName(modelName);
        const auto &key = requestedModelName;
        {
            std::scoped_lock lock(modelHintMutex);
            if (const auto hint = modelHints.find(key); hint != modelHints.end())
            {
                const auto candidate = readCString(
                    nativeConfigString(ModelConfigStringBase + hint->second), 128);
                if (candidate &&
                    _stricmp(
                        candidate->c_str(), requestedModelName.c_str()) == 0)
                    return hint->second;
                modelHints.erase(hint);
            }
        }
        if (!findXAsset(
                AssetTypeXModel, requestedModelName.c_str(), false).data)
        {
            return std::nullopt;
        }
        for (std::uint16_t index = 1; index < ModelConfigStringCount; ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(ModelConfigStringBase + index), 128);
            // Fastfile asset names are case-insensitive. Add-on map entities do
            // not always preserve the configstring band's spelling (Wetwork has
            // `cs_cargoship_door_PUll_EDGE` while its native band publishes
            // `cs_cargoship_door_pull_edge`). Treating those as different models
            // allocated a second configstring index and made the server's static
            // entity delta disagree with the client's const-baseline model.
            if (candidate &&
                _stricmp(
                    candidate->c_str(), requestedModelName.c_str()) == 0)
            {
                std::scoped_lock lock(modelHintMutex);
                modelHints.insert_or_assign(key, index);
                return index;
            }
        }
        return std::nullopt;
    }

    std::vector<std::pair<std::uint16_t, std::string>>
        EngineBindings::animConfigStringBand() const
    {
        // MAP LOAD ONLY, and for the same reason modelConfigStringBand is: this is
        // one pass over 4096 configstrings and has no business running per frame.
        //
        // It exists because per-state animation selection has to be built from THIS
        // engine's own strings. `codol-ship-the-games-own-strings`: the names are in
        // the fastfiles, and the band is where the engine puts the ones it actually
        // holds. Guessing at `ai_zombie_*` spellings and hoping resolve() catches the
        // misses is how invented values get on the wire.
        std::vector<std::pair<std::uint16_t, std::string>> band;
        if (!configStringGet_ || !CCS_Initialized())
            return band;
        for (std::uint16_t index = 1; index < AnimConfigStringCount; ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(AnimConfigStringBase + index), 128);
            if (candidate && !candidate->empty())
                band.emplace_back(*SV_AnimationAliasFromConfigString(
                    AnimConfigStringBase + index), *candidate);
        }
        return band;
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveAnimConfigStringIndex(
            const std::string_view animName) const
    {
        // AssetTypeXAnim is 2 in CODOL's own XAssetType enum, read out of out.exe's
        // asset-type name pointer array at 0xA5C808 (20-zm-actor-lifecycle.md 12.57).
        // The three ids this file already uses -- xmodel 4, fx 30, fx_map 20 -- come
        // from the same table, which is what makes 2 safe to add.
        constexpr std::uint32_t AssetTypeXAnim = 2;
        if (!configStringGet_ || !dbFindXAssetHeader_ || !CCS_Initialized() ||
            animName.empty() || animName.size() >= 128 ||
            animName.find('\0') != std::string_view::npos)
        {
            return std::nullopt;
        }
        // RESIDENCY FIRST, exactly as the model resolver does. A name the engine does
        // not hold must come back empty rather than matching a stale band entry.
        if (!findXAsset(
                AssetTypeXAnim, std::string(animName).c_str(), false).data)
        {
            return std::nullopt;
        }
        for (std::uint16_t index = 1; index < AnimConfigStringCount; ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(AnimConfigStringBase + index), 128);
            if (candidate && *candidate == animName)
            {
                // 514880 subtracts band base AND its reserved-slot flag (1)
                // before 661C50. 74A420/7858B0 put that zero-based NCS alias
                // into the tree map consumed by 540040/785870. Packet aliases
                // are not the flat configstring-relative index.
                return SV_AnimationAliasFromConfigString(AnimConfigStringBase + index);
            }
        }
        return std::nullopt;
    }

    std::optional<std::uint8_t> EngineBindings::resolveScriptModelAnimationTree(
        const std::span<const std::uint16_t> aliases) const
    {
        // CODREF(cl_parse_packet_anims): exact out.exe 527290 resolves ET6
        // ES+98 through registry789C534/count789C634 and definition byte+10.
        // 785870 maps packet aliases through the definition+4 BST. Read only
        // at map setup; no native allocation/calls or per-frame registry scan.
        if (!module_ || !bindingCommitted_.load(std::memory_order_acquire) ||
            aliases.empty() || aliases.size()>8 ||
            std::ranges::any_of(aliases,[](auto a){return !a || a>0xFFF;}))
            return std::nullopt;
        const auto *countAddress=module_+0x749C634;
        if (!readableSpan(countAddress,4)) return std::nullopt;
        std::uint32_t count{};std::memcpy(&count,countAddress,4);
        if (!count || count>64 || !readableSpan(module_+0x749C534,4*(count+1)))
            return std::nullopt;
        std::optional<std::uint8_t> result;
        for (std::uint32_t i=1;i<=count;++i) {
            const std::uint8_t *definition{};
            std::memcpy(&definition,module_+0x749C534+4*i,sizeof(definition));
            if (!definition || !readableSpan(definition,12)) continue;
            const auto wireId=definition[10];
            std::uint32_t nodeCount{};std::memcpy(&nodeCount,definition,4);
            if (!wireId || wireId>31 || !nodeCount || nodeCount>4096) continue;
            bool matches=true;
            for (const auto alias:aliases) {
                const std::uint8_t *link{};std::memcpy(&link,definition+4,sizeof(link));
                std::uint16_t node{};
                for (unsigned depth=0;link && depth<64;++depth) {
                    if (!readableSpan(link,12)) break;
                    std::uint16_t key{};std::memcpy(&key,link,2);
                    if (key==alias) {std::memcpy(&node,link+2,2);break;}
                    std::memcpy(&link,link+(key>alias?4:8),sizeof(link));
                }
                if (!node || node>=nodeCount) {matches=false;break;}
            }
            if (!matches) continue;
            // OLMOD(script_model_tree_resolution): ambiguity fails closed;
            // sharing an alias is not permission to pick an arbitrary tree.
            if (result) return std::nullopt;
            result=wireId;
        }
        return result;
    }

    std::optional<std::vector<std::pair<std::uint16_t, float>>>
        EngineBindings::animationNotifyTimes(const std::string_view animName) const
    {
        if (!bindingCommitted_.load(std::memory_order_acquire) || !dbFindXAssetHeader_ ||
            animName.empty() || animName.size() >= 128 ||
            animName.find('\0') != std::string_view::npos)
            return std::nullopt;
        const auto *parts = static_cast<const std::uint8_t *>(
            findXAsset(2, std::string(animName).c_str(), false).data);
        // CODREF(out.exe): 485B40 loads88bytes; 485AC0 resolves u16 marker
        // names in8byte entries. 789E20 reads count+27, pointer+80, frameCount+14,
        // framerate+40, and returns entry.time * frameCount / framerate.
        if (!parts || !readableSpan(parts, 88))
            return std::nullopt;
        const char *name{};
        std::memcpy(&name, parts, sizeof(name));
        const auto residentName = readCString(name, 128);
        if (!residentName || *residentName != animName)
            return std::nullopt; // refuse a default/missing asset substitution
        const auto count = parts[27];
        std::vector<std::pair<std::uint16_t, float>> result;
        if (!count)
            return result;
        std::uint16_t frames{};
        float rate{};
        const std::uint8_t *markers{};
        std::memcpy(&frames, parts + 14, sizeof(frames));
        std::memcpy(&rate, parts + 40, sizeof(rate));
        std::memcpy(&markers, parts + 80, sizeof(markers));
        if (!frames || !std::isfinite(rate) || rate <= 0 || !markers ||
            !readableSpan(markers, std::size_t{count} * 8))
            return std::nullopt;
        result.reserve(count);
        for (std::size_t i = 0; i < count; ++i)
        {
            std::uint16_t id{};
            float normalized{};
            std::memcpy(&id, markers + 8*i, sizeof(id));
            std::memcpy(&normalized, markers + 8*i + 4, sizeof(normalized));
            const auto seconds = normalized * static_cast<double>(frames) / rate;
            if (!std::isfinite(normalized) || normalized < 0 || normalized > 1 ||
                !std::isfinite(seconds) || seconds > std::numeric_limits<float>::max())
                return std::nullopt;
            result.emplace_back(id, static_cast<float>(seconds));
        }
        return result;
    }

    std::optional<std::string>
        EngineBindings::animationNotifyName(const std::uint16_t nameId) const
    {
        if (!bindingCommitted_.load(std::memory_order_acquire) || !module_ || !nameId)
            return std::nullopt;
        // CODREF(out.exe): 786B28 loads the marker's u16 ID into ESI;
        // 786860 uses that ID to form pool+20*ID+4 for its notify queue.
        // This is not the attachment/configstring namespace.
        constexpr std::size_t NotifyStringPoolRva = 0x0749C524;
        const auto *slot = module_ + NotifyStringPoolRva;
        if (!readableSpan(slot, sizeof(std::uint32_t)))
            return std::nullopt;
        std::uint32_t pool{};
        std::memcpy(&pool, slot, sizeof(pool));
        const auto address = std::uint64_t{pool} + 20u * nameId + 4u;
        if (!pool || address > std::numeric_limits<std::uint32_t>::max())
            return std::nullopt;
        return readCString(reinterpret_cast<const char *>(
            static_cast<std::uintptr_t>(address)), 128);
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveWeaponConfigStringIndex(
            const std::string_view weaponName) const
    {
        if (!configStringGet_ || !CCS_Initialized() || weaponName.empty() ||
            weaponName.size() >= 128 ||
            weaponName.find('\0') != std::string_view::npos)
        {
            return std::nullopt;
        }
        for (std::uint16_t index = 1; index < WeaponConfigStringCount; ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(WeaponConfigStringBase + index), 128);
            if (candidate && *candidate == weaponName)
                return index;
        }
        // Dynamic modular definitions live in the native WeaponDef registry.
        // CL_GetConfigString does not consistently expose that tail after the
        // retained server has replaced its own gamestate, so use the registry's
        // lookup for the exact raw definition as the authoritative fallback.
        if (weaponLookup_ && SV_ParseModularWeaponConfigString(weaponName))
        {
            const std::string nativeName(weaponName);
            const auto index = weaponLookup_(nativeName.c_str());
            if (index && index < WeaponConfigStringCount)
                return static_cast<std::uint16_t>(index);
        }
        return std::nullopt;
    }

    // CODREF(actor_head_attachment): exact CODOL XModel boneNames at +44,
    // numBones at +4; DObj assembly 0x52FBE0/0x781110 keeps the base skeleton
    // first. BO1/Ghosts attachment comparisons are in the head-attachment review.
    // OLMOD(death_fx_resolution): resident map-load lookup, no asset loading or
    // fallback bone zero. Attachment-local indices are not actor bone indices.
    std::optional<std::uint8_t> EngineBindings::modelBoneIndex(
        const std::string_view modelName, const std::string_view boneName) const
    {
        if (!module_ || modelName.empty() || modelName.size() >= 128 || boneName.empty() ||
            modelName.find('\0') != std::string_view::npos ||
            boneName.find('\0') != std::string_view::npos)
            return std::nullopt;
        const auto *model = static_cast<const std::byte *>(
            findXAsset(AssetTypeXModel, std::string(modelName).c_str(), false).data);
        if (!readableSpan(model, 360)) return std::nullopt;
        const auto count = static_cast<std::uint8_t>(model[4]);
        const std::uint16_t *names{};
        std::memcpy(&names, model + 44, sizeof(names));
        if (!count || !readableSpan(names, count * sizeof(*names)))
            return std::nullopt;
        // CODDIFF(actor_head_attachment): XModel boneNames are script-string
        // IDs, not weapon attachment IDs. CODOL 0x485300 retains these IDs in
        // the pool at VA 0x789C524; 0x4EAAD0 resolves text as pool+20*id+4.
        // AK live server/client reads confirmed j_neck at base bone20 and
        // j_spinelower at bone5. The attachment table returned weapon names
        // for the same numeric IDs, disabling every death-FX model change.
        constexpr std::size_t ScriptStringPoolRva = 0x749C524;
        const std::byte *scriptStrings{};
        if (!readableSpan(module_ + ScriptStringPoolRva, sizeof(scriptStrings)))
            return std::nullopt;
        std::memcpy(&scriptStrings, module_ + ScriptStringPoolRva, sizeof(scriptStrings));
        if (!scriptStrings) return std::nullopt;
        for (std::uint16_t i = 0; i < count && i < 255; ++i)
            if (names[i])
            {
                const auto *text = reinterpret_cast<const char *>(
                    scriptStrings + 20u * names[i] + 4u);
                if (const auto name = readCString(text, 128); name && *name == boneName)
                    return static_cast<std::uint8_t>(i);
            }
        return std::nullopt;
    }

    // CODREF(actor_head_attachment): 0x781110 appends XModel bone arrays;
    // 0x783440 resolves the composed index. Map-load only, resident assets only.
    std::optional<std::uint8_t> EngineBindings::attachmentBoneIndex(
        const std::string_view body, const std::string_view attachment,
        const std::string_view bone) const
    {
        if (!module_ || body.empty() || body.size()>=128 ||
            body.find('\0')!=std::string_view::npos) return std::nullopt;
        const auto local=modelBoneIndex(attachment,bone);
        if(!local || modelBoneIndex(body,bone))return std::nullopt;
        const auto *model=static_cast<const std::byte *>(
            findXAsset(AssetTypeXModel,std::string(body).c_str(),false).data);
        if(!readableSpan(model,360))return std::nullopt;
        const auto count=static_cast<std::uint8_t>(model[4]);
        if(!count || static_cast<unsigned>(count)+*local>=255)return std::nullopt;
        return static_cast<std::uint8_t>(count+*local);
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveEffectEventParameter(
            const std::string_view effectName) const
    {
        if (!configStringGet_ || !dbFindXAssetHeader_ || !CCS_Initialized() ||
            effectName.empty() || effectName.size() >= 128 ||
            effectName.find('\0') != std::string_view::npos)
        {
            return std::nullopt;
        }
        if (!findXAsset(
                AssetTypeFx, std::string(effectName).c_str(), false).data)
        {
            return std::nullopt;
        }
        for (std::uint16_t eventParameter = 1;
             eventParameter < EffectConfigStringCount;
             ++eventParameter)
        {
            const auto configStringIndex =
                SV_EffectEventParameterToConfigString(eventParameter);
            if (!configStringIndex)
                return std::nullopt;
            const auto candidate = readCString(
                nativeConfigString(*configStringIndex), 128);
            if (candidate && *candidate == effectName)
                return eventParameter;
        }
        return std::nullopt;
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveSoundAliasEventParameter(
            const std::string_view aliasName) const
    {
        const std::array names{ std::string(aliasName) };
        auto result = resolveSoundAliasEventParameters(names);
        return result.empty() ? std::nullopt : result.front();
    }

    std::vector<std::optional<std::uint16_t>>
        EngineBindings::resolveSoundAliasEventParameters(
            const std::span<const std::string> aliasNames) const
    {
        std::vector<std::optional<std::uint16_t>> result(aliasNames.size());
        if (!configStringGet_ || !ccsGetConstantString_ ||
            !CCS_Initialized() || aliasNames.empty())
        {
            return result;
        }
        std::unordered_map<std::string_view, std::vector<std::size_t>> unresolved;
        for (std::size_t index{}; index < aliasNames.size(); ++index)
        {
            const auto &name = aliasNames[index];
            // CODREF(sound_alias_event): do NOT gate on the sound ASSET being
            // loaded. The server's only job is to put an alias INDEX on the
            // wire; the client owns playback and looks the asset up itself. A
            // dedicated server loads no sound assets, so
            // findXAsset(AssetTypeSound, ...) fails for every name and
            // this filter emptied `unresolved` before either scan below could
            // run - which is why the resolver has NEVER answered on this build.
            // MEASURED: 63 level loads, every one logging `sound=unavailable`,
            // including the damage-feedback hit alert, while the material
            // lookups beside it resolve fine (material=125 killMaterial=144).
            // The dm demo confirms the wire needs only a small index - its 98
            // sound events are eType 26 (SoundAliasAsMaster) carrying 14/27.
            if (name.empty() || name.size() >= 128 ||
                name.find('\0') != std::string::npos)
            {
                continue;
            }
            unresolved[name].push_back(index);
        }

        for (std::uint16_t aliasIndex = 1;
             aliasIndex < SoundAliasConfigStringCount && !unresolved.empty();
             ++aliasIndex)
        {
            const auto candidate = readCString(
                nativeConfigString(SoundAliasConfigStringBase + aliasIndex),
                128);
            if (!candidate)
                continue;
            const auto match = unresolved.find(*candidate);
            if (match != unresolved.end())
            {
                for (const auto index : match->second)
                    result[index] = aliasIndex;
                unresolved.erase(match);
            }
        }

        for (std::uint32_t relativeIndex = 0;
             !unresolved.empty() &&
             relativeIndex <
                 SoundAliasEventParameterLimit -
                     SoundAliasConstantStringBase;
             ++relativeIndex)
        {
            const char *candidate{};
            if (!invokeCCSGetConstantString(
                    ccsGetConstantString_,
                    ConstantStringTypeSoundAlias,
                    relativeIndex,
                    candidate))
            {
                break;
            }
            const auto name = readCString(candidate, 128);
            if (name)
            {
                const auto match = unresolved.find(*name);
                if (match != unresolved.end())
                {
                    for (const auto index : match->second)
                    {
                        result[index] = static_cast<std::uint16_t>(
                            SoundAliasConstantStringBase + relativeIndex);
                    }
                    unresolved.erase(match);
                }
            }
        }
        return result;
    }

    std::optional<std::uint16_t> EngineBindings::resolveScriptAnimation(
        const std::string_view name) const
    {
        // CODREF(1649370): 785950/58EB5B resolve animation names in CCS type
        // 18. CG_ScriptMover 5221B5 maps that key to a tree-local XAnim entry.
        // Use the retained getter, including every loaded constant-string chunk.
        if (name.empty() || !ccsGetConstantString_ || !CCS_Initialized())
            return std::nullopt;
        std::optional<std::uint16_t> prefixed;
        for (std::uint32_t key = 1; key <= 0xFFF; ++key)
        {
            const char *candidate{};
            if (!invokeCCSGetConstantString(ccsGetConstantString_, 18, key, candidate))
                break;
            const auto text = readCString(candidate, 256);
            if (!text) continue;
            if (*text == name) return static_cast<std::uint16_t>(key);
            if (text->starts_with('%') && std::string_view(*text).substr(1) == name)
                prefixed = static_cast<std::uint16_t>(key);
        }
        return prefixed;
    }

    std::vector<std::pair<std::uint16_t, std::string>>
        EngineBindings::collectServerSoundAliasAuditions() const
    {
        // TODO(CODOL): audition support. CCS type 5 is the networked sound
        // alias pool - CCS_GetConstantString indexes a per-type list head table
        // with stride 8, at VA 0x077D8188 HERE (section 84; 3.3.3.3's is
        // 0x02DF7CE8, and that is the number this comment used to carry) - and
        // 1432 of its 1507
        // entries carry ab_/uk_/za_/rb_ language prefixes, i.e. announcer
        // voice-over. Return the remainder, which is every alias a server can
        // actually reference on this build. Remove with the audition mode.
        std::vector<std::pair<std::uint16_t, std::string>> auditions;
        if (!ccsGetConstantString_ || !CCS_Initialized())
            return auditions;
        for (std::uint32_t relativeIndex = 0; relativeIndex < 16384;
             ++relativeIndex)
        {
            const char *candidate{};
            if (!invokeCCSGetConstantString(
                    ccsGetConstantString_,
                    ConstantStringTypeSoundAlias,
                    relativeIndex,
                    candidate))
            {
                break;
            }
            const auto name = readCString(candidate, 128);
            if (!name || name->size() < 3)
                continue;
            const auto prefix = name->substr(0, 3);
            if (prefix == "ab_" || prefix == "uk_" || prefix == "za_" ||
                prefix == "rb_")
            {
                continue;
            }
            const auto parameter = static_cast<std::uint32_t>(
                SoundAliasConstantStringBase) + relativeIndex;
            if (!parameter || parameter >= SoundAliasEventParameterLimit)
                continue;
            auditions.emplace_back(
                static_cast<std::uint16_t>(parameter), *name);
        }
        return auditions;
    }

    void EngineBindings::logServerSoundAliasTables(
        const std::size_t limit) const
    {
        // TODO(CODOL): diagnostic only. BO1 G_PlaySoundAlias 0x00694460 shows
        // the server's job is to supply an alias INDEX - it stuffs it into
        // entityState.loopSoundId on a TempEntity of event 4, which is exactly
        // the eType 26 the dm demo carries 98 of. Our own resolver asks the two
        // index sources by NAME and has answered nothing on every level load,
        // so print what those sources hold.
        char header[160]{};
        std::snprintf(
            header,
            sizeof(header),
            "sound alias tables: configStringGet=%u ccsGetConstantString=%u "
            "ccsInitialized=%u base=%u count=%u",
            configStringGet_ ? 1u : 0u,
            ccsGetConstantString_ ? 1u : 0u,
            CCS_Initialized() ? 1u : 0u,
            static_cast<unsigned int>(SoundAliasConfigStringBase),
            static_cast<unsigned int>(SoundAliasConfigStringCount));
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, header);
        if (!configStringGet_ || !CCS_Initialized())
            return;

        std::size_t shown{};
        for (std::uint16_t aliasIndex = 1;
             aliasIndex < SoundAliasConfigStringCount && shown < limit;
             ++aliasIndex)
        {
            const auto candidate = readCString(
                nativeConfigString(SoundAliasConfigStringBase + aliasIndex), 128);
            if (!candidate || candidate->empty())
                continue;
            ++shown;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "sound alias configstring " + std::to_string(aliasIndex) +
                    " = " + *candidate);
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "sound alias configstrings non-empty: " + std::to_string(shown));

        // CCS type 5 is NOT the only constant-string table, and it is not the
        // UI one. CCS_GetConstantString indexes a per-TYPE list head table with
        // stride 8 and then walks that type's chain.
        //
        // OLMOD(section-84): the two VAs here were 3.3.3.3's and this code calls
        // out.exe. CCSGetConstantStringRva 0x261C50 puts the function at VA
        // 0x00661C50, whose body is instruction-for-instruction 3.3.3.3's
        // 0x005851F0 with ONE operand changed: `mov eax, [eax*8 + 0x77D8188]`
        // at 0x00661C53 against `[eax*8 + 0x2DF7CE8]` at 0x005851F3. So the
        // shape and the stride carry over and THE HEAD TABLE IS AT 0x077D8188
        // on this build. Nothing in this tree dereferences it -- the walk goes
        // through the bound function -- but the number was wrong to quote.
        // Type 5
        // holds 1507 entries and every feedback-word match in it is
        // voice-over - ab_1mc_hardpoint, uk_ac130_fco_directhit,
        // za_m1_killstreak1 - so the announcer table is what this project has
        // been searching for a hit marker. Enumerate every type instead.
        static constexpr std::string_view Wanted[]{
            "hit", "alert", "medal", "challenge", "reward", "level_up",
            "splash", "headshot", "killstreak", "point", "score", "ui_",
        };
        if (!ccsGetConstantString_)
            return;
        for (std::uint32_t type = 0; type < 16; ++type)
        {
            std::size_t total{};
            std::size_t matched{};
            std::string firstNames;
            for (std::uint32_t relativeIndex = 0; relativeIndex < 16384;
                 ++relativeIndex)
            {
                const char *candidate{};
                if (!invokeCCSGetConstantString(
                        ccsGetConstantString_, type, relativeIndex, candidate))
                {
                    break;
                }
                const auto name = readCString(candidate, 128);
                if (!name || name->empty())
                    continue;
                ++total;
                if (total <= 3)
                    firstNames += " " + *name;
                if (matched >= limit)
                    continue;
                if (!std::ranges::any_of(
                        Wanted, [&](const std::string_view want) {
                            return name->find(want) != std::string::npos;
                        }))
                {
                    continue;
                }
                ++matched;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "ccs type=" + std::to_string(type) + " index=" +
                        std::to_string(relativeIndex) + " = " + *name);
            }
            if (!total)
                continue;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ccs type=" + std::to_string(type) + " total=" +
                    std::to_string(total) + " matched=" +
                    std::to_string(matched) + " first:" + firstNames);
        }
    }

    std::optional<std::uint16_t>
        EngineBindings::resolveServerMaterialConfigStringIndex(
            const std::string_view materialName) const
    {
        if (!configStringGet_ || !CCS_Initialized() || materialName.empty() ||
            materialName.size() >= 64 ||
            materialName.find('\0') != std::string_view::npos)
        {
            return std::nullopt;
        }
        for (std::uint16_t index = 1;
             index < ServerMaterialConfigStringCount;
             ++index)
        {
            const auto candidate = readCString(
                nativeConfigString(ServerMaterialConfigStringBase + index), 64);
            if (candidate && *candidate == materialName)
                return index;
        }
        return std::nullopt;
    }

    // CODREF(actor_grounded_adapter): CODOL514880 reads class>=23 from
    // 77D8250 through the parsed gamestate string table. Original Factory
    // registers clock names at5170/5171; never assume those session indices.
    std::optional<std::uint16_t> EngineBindings::firstDynamicServerMaterialIndex() const
    {
        if (!module_ || !CCS_Initialized()) return std::nullopt;
        const auto *types=module_+ConfigStringTypesRva+ServerMaterialConfigStringBase;
        if (!readableSpan(types,ServerMaterialConfigStringCount)) return std::nullopt;
        for (std::uint16_t i=1;i<ServerMaterialConfigStringCount;++i)
            if (types[i]>=23) return i;
        return std::nullopt;
    }

    std::optional<SvBrushModelCollision>
        EngineBindings::resolveBrushModelCollision(
            const std::uint32_t clipHandle) const
    {
        if (!module_)
            return std::nullopt;

        const auto *const collisionMap = module_ + CollisionMapRva;
        constexpr std::size_t BrushModelCountOffset = 0x90;
        constexpr std::size_t BrushModelsOffset = 0x94;
        if (!readableSpan(
                collisionMap + BrushModelCountOffset,
                sizeof(std::uint32_t) + sizeof(NativeBrushModel *)))
        {
            return std::nullopt;
        }

        std::uint32_t modelCount{};
        const NativeBrushModel *models{};
        std::memcpy(
            &modelCount,
            collisionMap + BrushModelCountOffset,
            sizeof(modelCount));
        std::memcpy(
            &models,
            collisionMap + BrushModelsOffset,
            sizeof(models));
        if (!modelCount || clipHandle >= modelCount || !models ||
            modelCount >
                std::numeric_limits<std::size_t>::max() /
                    sizeof(NativeBrushModel) ||
            !readableSpan(
                models,
                static_cast<std::size_t>(modelCount) *
                    sizeof(NativeBrushModel)))
        {
            return std::nullopt;
        }

        const auto &model = models[clipHandle];
        const auto contents =
            model.leafBrushContents | model.leafTerrainContents;
        const SvBrushModelCollision result{
            .clipHandle = clipHandle,
            .bounds = model.bounds,
            .contents = contents,
        };
        return SV_EncodeBrushModelSolid(result) ? std::optional{ result }
                                                : std::nullopt;
    }

    std::optional<bool> EngineBindings::contactBrushModel(
        const std::array<float, 3> &origin,
        const TraceBounds &bounds,
        const std::array<float, 3> &brushOrigin,
        const std::array<float, 3> &brushAngles,
        const SvBrushModelCollision &brushModel) const
    {
        const auto entity = SV_LinkBrushModelCollisionEntity(
            MaximumServerCollisionEntityNum,
            std::nullopt,
            brushOrigin,
            brushAngles,
            brushModel);
        if (!entity)
            return std::nullopt;

        TraceResult initialTrace{
            .fraction = 1.0f,
        };
        const auto trace = traceTransformedBrushModel(
            initialTrace,
            origin,
            origin,
            bounds,
            *entity,
            SvGlassState{});
        return trace ? std::optional{ trace->startSolid } : std::nullopt;
    }

    std::optional<TraceResult> EngineBindings::traceCapsule(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const std::int32_t passEntityNum,
        const std::uint32_t contentMask) const
    {
        if (!trace_ || !validTraceInput(start, end, bounds, contentMask))
        {
            return std::nullopt;
        }

        NativeTraceResult native{};
        trace_(&native, start.data(), end.data(), &bounds, passEntityNum, contentMask);
        return decodeTraceResult(native);
    }

    std::optional<TraceResult> EngineBindings::traceWorld(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const std::uint32_t contentMask,
        const SvGlassState &glassState) const
    {
        if (!worldTrace_ || !validTraceInput(start, end, bounds, contentMask))
            return std::nullopt;

        // OLMOD(slow-trace-report): section 97h found the frame thread parked at
        // out.exe+0x266938 -- a function whose only direct caller is itself, sitting
        // immediately below WorldTrace, i.e. the engine's RECURSIVE clipmap descent.
        // Traces of 199217 us, 111549 us and 459473 us were measured on this map.
        // A 459 ms trace stalls a whole frame on its own, which is what two players
        // moving feels like.
        //
        // The input is NOT degenerate -- validTraceInput above already rejects
        // non-finite starts, ends, midpoints and half-sizes, and negative extents --
        // so this says WHICH query goes deep rather than assuming why.
        //
        // Silent while nothing is wrong, and capped so the reporter can never become
        // the thing it is measuring.
        // Two clock reads per world trace is small, but this is the one addition
        // that scales with TRACE count rather than frame count, so the baseline
        // switch has to reach it too.
        struct SlowTraceReport
        {
            const std::array<float, 3> &start;
            const std::array<float, 3> &end;
            const TraceBounds &bounds;
            std::uint32_t contentMask;
            std::chrono::steady_clock::time_point began{
                std::chrono::steady_clock::now() };

            ~SlowTraceReport()
            {
                constexpr std::uint64_t slowMicroseconds = 50'000;
                constexpr int reportLimit = 16;
                static int reported{};
                const auto finished = std::chrono::steady_clock::now();
                const auto elapsed = static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::microseconds>(
                        finished - began).count());

                // OLMOD(trace-census): section 103d put 50 ms of a 63 ms frame in
                // clientThink, and section 97g priced a trace at ~250 us against tens
                // of microseconds for a real CoD trace. Whether that is a handful of
                // very expensive descents or a flood of cheap ones decides the fix,
                // and nothing here knew which. Two counters per trace, reported on a
                // wall-clock interval so it needs no plumbing through frame timing.
                {
                    static std::uint64_t censusCount{};
                    static std::uint64_t censusMicroseconds{};
                    static auto censusBegan = finished;
                    ++censusCount;
                    censusMicroseconds += elapsed;
                    const auto window = static_cast<std::uint64_t>(
                        std::chrono::duration_cast<std::chrono::microseconds>(
                            finished - censusBegan).count());
                    if (window >= 5'000'000 && !SV_PerfBaseline())
                    {
                        char census[224]{};
                        std::snprintf(census, sizeof(census),
                            "TRACE CENSUS %llu traces in %llu ms = %llu/s, "
                            "%llu us in traces (%.1f%% of wall), mean %.1f us",
                            static_cast<unsigned long long>(censusCount),
                            static_cast<unsigned long long>(window / 1000),
                            static_cast<unsigned long long>(
                                censusCount * 1'000'000 / (window | 1)),
                            static_cast<unsigned long long>(censusMicroseconds),
                            100.0 * static_cast<double>(censusMicroseconds) /
                                static_cast<double>(window | 1),
                            static_cast<double>(censusMicroseconds) /
                                static_cast<double>(censusCount | 1));
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer, census);
                        censusCount = 0;
                        censusMicroseconds = 0;
                        censusBegan = finished;
                    }
                }

                if (elapsed < slowMicroseconds || reported >= reportLimit ||
                    SV_PerfBaseline())
                    return;
                ++reported;
                char line[256]{};
                std::snprintf(line, sizeof(line),
                    "SLOW TRACE %llu us start=%.2f,%.2f,%.2f end=%.2f,%.2f,%.2f "
                    "half=%.0f,%.0f,%.0f mask=0x%08X",
                    static_cast<unsigned long long>(elapsed),
                    start[0], start[1], start[2], end[0], end[1], end[2],
                    bounds.halfSize[0], bounds.halfSize[1], bounds.halfSize[2],
                    contentMask);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        } slowTraceReport{ start, end, bounds, contentMask };

        NativeTraceResult native{};
        NativeWorldTraceCallbacks callbacks{
            .isGlassSolid = SV_Glass_IsPieceSolid,
        };
        const ScopedGlassState scopedGlassState(glassState);
        const auto function = worldTrace_;
        auto *const resultPointer = &native;
        const auto *const startPointer = start.data();
        const auto *const endPointer = end.data();
        const auto *const boundsPointer = &bounds;
        const auto *const callbacksPointer = &callbacks;
        const auto mask = contentMask;
        __asm
        {
            push edi
            mov edi, endPointer
            mov edx, mask
            push callbacksPointer
            push boundsPointer
            push startPointer
            push resultPointer
            call function
            add esp, 10h
            pop edi
        }
        return decodeTraceResult(native);
    }

    std::optional<TraceResult> EngineBindings::traceTransformedCapsule(
        const TraceResult &initialTrace,
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const SvCollisionEntity &entity) const
    {
        // OLMOD(zm-player-collision-profile): opt-in five-second aggregate of
        // actual native actor capsule cost. No per-entity file writes, model
        // resolution or DObj work is added to the Pmove path.
        struct ActorCapsuleCost
        {
            bool enabled{};
            std::chrono::steady_clock::time_point began{};
            ~ActorCapsuleCost()
            {
                if (!enabled) return;
                const auto now = std::chrono::steady_clock::now();
                const auto ns = static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(now-began).count());
                static thread_local auto window = now;
                static thread_local std::uint64_t calls{}, total{}, peak{};
                ++calls; total += ns; peak = std::max(peak,ns);
                const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now-window).count();
                if (elapsed < 5000) return;
                char line[240]{};
                std::snprintf(line,sizeof(line),
                    "zombie player capsule cost windowMs=%lld calls=%llu totalUs=%.3f meanUs=%.3f maxUs=%.3f",
                    static_cast<long long>(elapsed),static_cast<unsigned long long>(calls),
                    total/1000.0,total/(1000.0*calls),peak/1000.0);
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,line);
                calls=total=peak=0;window=now;
            }
        };
        static const bool profileActorCapsules = [] {
            std::array<char,8> value{};
            return GetEnvironmentVariableA("OLMOD_ZM_PLAYER_COLLISION_PROFILE",value.data(),
                static_cast<DWORD>(value.size()))==1 && value[0]=='1';
        }();
        ActorCapsuleCost cost;
        cost.enabled = profileActorCapsules && entity.bodyRole==SvCollisionBodyRole::Actor && entity.contents==1u;
        if (cost.enabled) cost.began=std::chrono::steady_clock::now();
        if (!transformedCapsuleTrace_ ||
            !validTraceInput(start, end, bounds, entity.contents) ||
            !SV_IsCollisionEntityValid(entity))
        {
            return std::nullopt;
        }

        auto native = encodeTraceResult(initialTrace);
        const auto function = transformedCapsuleTrace_;
        auto *const resultPointer = &native;
        const auto *const startPointer = start.data();
        const auto *const endPointer = end.data();
        const auto *const boundsPointer = &bounds;
        const auto *const targetBoundsPointer = &entity.bounds;
        const auto *const targetOriginPointer = entity.origin.data();
        const auto targetContents = entity.contents;
        // CODREF(sv_trace): 1649370's convention is NOT 3.3.3.3's. Section 74.
        //
        //                    3.3.3.3 0x0058B330      1649370 0x00668560
        //   [ebp+08] arg1    result                  result
        //   [ebp+0C] arg2    start                   start
        //   [ebp+10] arg3    bounds                  bounds
        //   [ebp+14] arg4    targetBounds            contents
        //   [ebp+18] arg5    contents                targetOrigin
        //   ECX              targetOrigin            targetBounds
        //   end              EAX                     EDX
        //
        // Measured four ways, not read off a name. Both of out.exe's own call
        // sites agree (0x0046DC81 in the box clip, 0x0046E3F6 in the point
        // clip) and so do both of 3.3.3.3's (0x005FB4D1 server, 0x00458DCE
        // client). The callee settles it too: 0x0058B330 pushes its incoming
        // EAX straight into 0x00588BC0 and reads [ebp+14]/[ebp+18], while
        // 0x00668560 saves incoming ECX to [ebp-0x34], pushes incoming EDX,
        // and reads [ebp+18] as the vector 0x0058B330 takes in ECX.
        __asm
        {
            mov edx, endPointer
            mov ecx, targetBoundsPointer
            push targetOriginPointer
            push targetContents
            push boundsPointer
            push startPointer
            push resultPointer
            call function
            add esp, 14h
        }
        return decodeTraceResult(native);
    }

    std::optional<TraceResult> EngineBindings::traceTransformedBrushModel(
        const TraceResult &initialTrace,
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const SvCollisionEntity &entity,
        const SvGlassState &glassState) const
    {
        if (!transformedBrushModelTrace_ ||
            entity.shape != SvCollisionShape::BrushModel ||
            !entity.brushModelClipHandle ||
            !validTraceInput(start, end, bounds, entity.contents) ||
            !SV_IsCollisionEntityValid(entity))
        {
            return std::nullopt;
        }

        auto native = encodeTraceResult(initialTrace);
        const ScopedGlassState scopedGlassState(glassState);
        const auto function = transformedBrushModelTrace_;
        auto *const resultPointer = &native;
        const auto *const startPointer = start.data();
        const auto *const endPointer = end.data();
        const auto *const boundsPointer = &bounds;
        const auto targetContents = entity.contents;
        const auto clipHandle = *entity.brushModelClipHandle;
        const auto *const targetOriginPointer = entity.origin.data();
        const auto *const targetAnglesPointer = entity.angles.data();
        // CODREF(sv_trace): 1649370's convention is NOT 3.3.3.3's. Section 74.
        //
        //                    3.3.3.3 0x0058B230      1649370 0x00668470
        //   [ebp+08] arg1    start                   result
        //   [ebp+0C] arg2    end                     end
        //   [ebp+10] arg3    bounds                  bounds
        //   [ebp+14] arg4    clipHandle              clipHandle
        //   [ebp+18] arg5    contents                contents
        //   [ebp+1C] arg6    targetOrigin            targetAngles
        //   ECX              targetAngles            targetOrigin
        //   EDX              result                  start
        //
        // The callee names arg1 and the angles by itself: 0x0058B230 does
        // `fld [ecx]` / `fld [ecx+4]` on the angles and `fld [ebx]` .. `[ebx+8]`
        // on [ebp+8], where 0x00668470 does the zero test on [ebp+1C] through
        // EDI and reads the three start floats through EDX. Both call sites on
        // each build agree (0x005FB4A7, 0x00458D7B there; 0x0046DC2F,
        // 0x0046E3A1 here). CARRYING 3.3.3.3's FORM HANDED THE CALLEE A
        // 12-BYTE vec3 AS ITS 40-BYTE RESULT BUFFER.
        __asm
        {
            mov ecx, targetOriginPointer
            mov edx, startPointer
            push targetAnglesPointer
            push targetContents
            push clipHandle
            push boundsPointer
            push endPointer
            push resultPointer
            call function
            add esp, 18h
        }
        return decodeTraceResult(native);
    }

    void EngineBindings::compareNativeServerCapsuleTrace(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const std::uint32_t contentMask,
        const SvGlassState &glassState,
        const std::span<const SvCollisionEntity> entities,
        const SvTraceEntityFilter &filter,
        const TraceResult &sourceTrace) const
    {
        // This comparison invokes a second native SV_Trace for every source
        // collision query. Keep it opt-in after source/native parity has been
        // established; at two clients it can execute hundreds of times per
        // second and disturb the authoritative 20 Hz frame cadence.
        if (!nativeTraceComparisonEnabled())
            return;
        const auto capsuleExtent = bounds.halfSize[0] + bounds.halfSize[1] +
            bounds.halfSize[2];
        if (gameThreadId_.load(std::memory_order_acquire) !=
                GetCurrentThreadId() ||
            capsuleExtent == 0.0f || glassState.nonSolidPieceCount() != 0 ||
            !nativeServerEntityMirrorMatches(entities))
        {
            return;
        }

        const NativeIgnoreEntParams ignore{
            .baseEntity = filter.passEntityNum
                ? static_cast<std::int32_t>(*filter.passEntityNum)
                : 2047,
            .parentEntity = filter.passOwnerEntityNum
                ? static_cast<std::int32_t>(*filter.passOwnerEntityNum)
                : -1,
        };
        NativeTraceResult nativeResult{};
        NativeExceptionDetails exceptionDetails{};
        const ScopedGlassState scopedGlassState(glassState);
        if (!invokeSVTrace(
                svTrace_,
                ignore,
                start,
                end,
                bounds,
                contentMask,
                nativeResult,
                exceptionDetails))
        {
            ++nativeTraceUnavailableCount_;
            char failure[160]{};
            std::snprintf(
                failure,
                sizeof(failure),
                "native_exception code=0x%08lX address=%p",
                static_cast<unsigned long>(exceptionDetails.code),
                exceptionDetails.address);
            if (failure != nativeTraceComparisonFailure_)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("native trace comparison unavailable stage=") +
                        failure);
                nativeTraceComparisonFailure_ = failure;
            }
            return;
        }

        const auto nativeTrace = decodeTraceResult(nativeResult);
        if (!nativeTrace)
        {
            ++nativeTraceUnavailableCount_;
            if (nativeTraceComparisonFailure_ != "invalid_result")
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "native trace comparison unavailable stage=invalid_result");
                nativeTraceComparisonFailure_ = "invalid_result";
            }
            return;
        }

        if (!nativeTraceComparisonFailure_.empty())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "native trace comparison recovered");
            nativeTraceComparisonFailure_.clear();
        }
        ++nativeTraceComparisonCount_;
        const auto difference = SV_CompareTraceResults(
            sourceTrace, *nativeTrace);
        if (difference == SvTraceComparisonDifference::None)
        {
            if (!nativeTraceComparisonObservedSuccess_)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "native trace comparison active owner=source");
                nativeTraceComparisonObservedSuccess_ = true;
            }
        }
        else
        {
            ++nativeTraceMismatchCount_;
            const auto differenceBit = std::uint32_t{ 1 } <<
                static_cast<std::uint8_t>(difference);
            if (!(nativeTraceLoggedDifferenceMask_ & differenceBit))
            {
                nativeTraceLoggedDifferenceMask_ |= differenceBit;
                char details[512]{};
                std::snprintf(
                    details,
                    sizeof(details),
                    "native trace mismatch field=%s source_fraction=%.6f "
                    "native_fraction=%.6f source_hit=%lu/%u "
                    "native_hit=%lu/%u source_contents=0x%08lX "
                    "native_contents=0x%08lX start=[%.3f,%.3f,%.3f] "
                    "end=[%.3f,%.3f,%.3f]",
                    traceDifferenceName(difference),
                    static_cast<double>(sourceTrace.fraction),
                    static_cast<double>(nativeTrace->fraction),
                    static_cast<unsigned long>(sourceTrace.hitType),
                    static_cast<unsigned int>(sourceTrace.hitId),
                    static_cast<unsigned long>(nativeTrace->hitType),
                    static_cast<unsigned int>(nativeTrace->hitId),
                    static_cast<unsigned long>(sourceTrace.contents),
                    static_cast<unsigned long>(nativeTrace->contents),
                    static_cast<double>(start[0]),
                    static_cast<double>(start[1]),
                    static_cast<double>(start[2]),
                    static_cast<double>(end[0]),
                    static_cast<double>(end[1]),
                    static_cast<double>(end[2]));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, details);
            }
        }

        if ((nativeTraceComparisonCount_ & 0xFFF) == 0)
        {
            char summary[192]{};
            std::snprintf(
                summary,
                sizeof(summary),
                "native trace comparison summary comparisons=%llu "
                "mismatches=%llu unavailable=%llu owner=source",
                static_cast<unsigned long long>(nativeTraceComparisonCount_),
                static_cast<unsigned long long>(nativeTraceMismatchCount_),
                static_cast<unsigned long long>(nativeTraceUnavailableCount_));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, summary);
        }
    }

    std::optional<TraceResult> EngineBindings::traceServerCapsule(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const std::uint32_t contentMask,
        const SvGlassState &glassState,
        const std::span<const SvCollisionEntity> entities,
        const SvTraceEntityFilter &filter) const
    {
        if (!SV_IsTraceEntityFilterValid(filter))
            return std::nullopt;

        // CODREF(sv_trace): THIS BUILD HAS NO SV_Trace. Section 74.
        //
        // The comment this replaces said CODOL's server Pmove handler owns
        // collision through SV_Trace and the linked g_entities tree, and on
        // 3.3.3.3 that is true -- SVTrace 0x005FB940 has exactly one caller,
        // reaches 0x0058D500 and 0x0058D790, and those reach 0x005FB390 and
        // 0x005FB510, which read the gentity at stride 0x2C8. 1649370 has
        // none of them. SVTraceRva 0x0046E780 is the counterpart of
        // 3.3.3.3's 0x00459940, the GENERAL trace -- a thin wrapper calls it
        // on both builds, it has 37 callers here to that one's 24, and its
        // box walker's leaf 0x0046DCF0 is instruction-for-instruction
        // identical to 3.3.3.3's CLIENT leaf 0x00458E40 (319 of 319) and 6%
        // similar to the server's 0x0058D200. Its per-entity clip 0x0046DAE0
        // reads the client centity array through
        // dword_1C1D188[dword_82C3B60] ^ 0x2168F672 at stride 0x270 with the
        // entityState at +0xF4 -- the SAME array section 73 measured EMPTY on
        // a live dedicated, which is why the locational point trace returned
        // hitType=0 with a healthy DObj standing in the ray. The two shared
        // clip helpers confirm it from the other side: 0x0058B230 and
        // 0x0058B330 have FOUR callers each there and 0x00668470 and
        // 0x00668560 have TWO here -- the two that are gone are the server
        // clips.
        //
        // So the entity half of every capsule query on this server was dead.
        // The world half was not, because WorldTrace is genuinely shared,
        // which is why a player has always stood on the ground and walked.
        if (nativeCapsuleTraceEnabled())
        {
            if (!nativeServerEntityMirrorObservedSuccess_ ||
                !nativeServerEntityMirrorFailure_.empty() || entities.empty() ||
                nativeServerEntityMirror_.size() != entities.size() ||
                gameThreadId_.load(std::memory_order_acquire) !=
                    GetCurrentThreadId() ||
                *serverGameEntitiesPointer_ != gEntities_ ||
                *serverGameEntityCount_ <= entities.back().entityNum)
            {
                return std::nullopt;
            }

            const NativeIgnoreEntParams ignore{
                .baseEntity = filter.passEntityNum
                    ? static_cast<std::int32_t>(*filter.passEntityNum)
                    : 2047,
                .parentEntity = filter.passOwnerEntityNum
                    ? static_cast<std::int32_t>(*filter.passOwnerEntityNum)
                    : -1,
            };
            NativeTraceResult nativeResult{};
            NativeExceptionDetails exceptionDetails{};
            const ScopedGlassState scopedGlassState(glassState);
            if (!invokeSVTrace(
                    svTrace_,
                    ignore,
                    start,
                    end,
                    bounds,
                    contentMask,
                    nativeResult,
                    exceptionDetails))
            {
                return std::nullopt;
            }
            return decodeTraceResult(nativeResult);
        }

        auto aggregate = traceWorld(
            start, end, bounds, contentMask, glassState);
        if (!aggregate)
            return aggregate;

        const auto worldFraction = aggregate->fraction;
        std::size_t considered{};
        std::size_t improved{};
        if (aggregate->fraction != 0.0f)
        {
            for (const auto &entity : entities)
            {
                if (!SV_IsCollisionEntityValid(entity))
                    return std::nullopt;
                if (!SV_ShouldClipToEntity(entity, filter, contentMask))
                    continue;
                if (!SV_ShouldBroadphaseClipToEntity(
                        start, end, bounds, entity))
                    continue;

                if (entity.shape == SvCollisionShape::ScriptModelDObj)
                    continue;
                ++considered;
                const auto entityTrace = entity.shape ==
                        SvCollisionShape::BrushModel
                    ? traceTransformedBrushModel(
                          *aggregate,
                          start,
                          end,
                          bounds,
                          entity,
                          glassState)
                    : traceTransformedCapsule(
                          *aggregate, start, end, bounds, entity);
                if (!entityTrace)
                    return std::nullopt;
                if (SV_ApplyEntityTraceHit(
                        *aggregate, *entityTrace, entity))
                {
                    ++improved;
                }
                if (aggregate->fraction == 0.0f)
                    break;
            }
        }
        // OLMOD(capsule-entity-collision): SILENT while nothing collides. It
        // reports only when an ENTITY beat the world, which is the capability
        // this build did not have before section 74 and the one thing a
        // one-player map cannot produce. Sampled, because pmove traces run
        // many times per frame.
        if (improved != 0 && capsuleEntityTraceLogCounter_++ < 12)
        {
            char line[224]{};
            std::snprintf(
                line,
                sizeof(line),
                "capsule entity trace entities=%zu considered=%zu improved=%zu "
                "fraction %.6f -> %.6f hitType=%u hitId=%u",
                entities.size(),
                considered,
                improved,
                worldFraction,
                aggregate->fraction,
                static_cast<unsigned int>(aggregate->hitType),
                static_cast<unsigned int>(aggregate->hitId));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }
        compareNativeServerCapsuleTrace(
            start,
            end,
            bounds,
            contentMask,
            glassState,
            entities,
            filter,
            *aggregate);
        return aggregate;
    }

    // CODREF(sv_trace): 3.3.3.3's SV_PointTraceToEntity 0x005FB510, done here.
    //
    // WHY IT IS HERE AND NOT A CALL. On 3.3.3.3 the clipmap walker
    // CM_PointTraceToEntities 0x0058D790 calls SV_PointTraceToEntity for every
    // entity in the SERVER's sector tree, and that function reads the gentity
    // at stride 0x2C8 from the pointer at 0x03150048, tests svFlags bit 2 at
    // gentity +0x112 to pick the locational pair, builds an orientation from
    // the entity's own currentOrigin +0x148 and currentAngles +0x154, carries
    // the ray into model space, calls DObjTraceline, and rotates the hit normal
    // back out at 0x005FB7DC.
    //
    // 1649370 DOES NOT CONTAIN THAT FUNCTION. Both builds also carry a CLIENT
    // twin - byte-identical outer, different leaf - and out.exe kept only the
    // twin: its leaf reads a heap centity array through the obfuscated slot
    // dword_1C1D188[dword_82C3B60] ^ 0x2168F672 at stride 0x270 with the
    // entityState at +0xF4, offsets the ray by a GLOBAL vec3 rather than by any
    // entity, and copies the normal without rotating it. The image has no
    // `test byte [reg + 0x11A], 4` anywhere, and DObjTraceline has one fewer
    // caller here than on 3.3.3.3 - the server leaf's. Section 73.
    //
    // So the ray this project handed 0x0046E6D0 was transformed into a space no
    // player is in and matched against a list the dedicated never fills, which
    // is why section 55's probe returned `fraction=1.0 hitType=0` before the
    // DObj existed and returned exactly the same after it did (section 72).
    bool EngineBindings::traceServerLocationalEntities(
        const SvPointTraceRequest &request,
        const std::span<const std::uint8_t> priorityMap,
        const std::span<const SvCollisionEntity> entities,
        TraceResult &aggregate,
        NativeExceptionDetails &exceptionDetails) const
    {
        if (!dobjTraceline_ || !angleVectors_ || priorityMap.empty())
            return false;

        std::uint32_t considered{};
        std::uint32_t traced{};
        std::uint32_t improved{};
        const auto entryFraction = aggregate.fraction;
        for (const auto &entity : entities)
        {
            if (entity.shape != SvCollisionShape::Capsule &&
                entity.shape != SvCollisionShape::ScriptModelDObj)
            {
                continue;
            }
            if (aggregate.fraction == 0.0f)
                break;
            if (!SV_ShouldClipToEntity(
                    entity, request.filter, request.contentMask) ||
                !SV_ShouldBroadphaseClipToEntity(
                    request.start, request.end, PointTraceBounds, entity))
            {
                continue;
            }
            ++considered;
            auto *const dobj = serverDObjGetAdapter(
                static_cast<std::int32_t>(entity.entityNum));
            if (!dobj)
            {
                // This retail image retains actor presentation but lacks the
                // native SP actor/DObj server setup present in earlier CODOL
                // builds. Keep the authored actor body in the bullet path so
                // campaign enemies can take damage and release their finite
                // agent slots while that native setup remains unavailable.
                if (entity.bodyRole != SvCollisionBodyRole::Actor)
                    continue;
                const auto actorTrace = traceTransformedCapsule(
                    aggregate,
                    request.start,
                    request.end,
                    PointTraceBounds,
                    entity);
                if (!actorTrace)
                    return false;
                ++traced;
                if (SV_ApplyEntityTraceHit(aggregate, *actorTrace, entity))
                    ++improved;
                continue;
            }

            // AnglesToAxis then `local = axis * (world - origin)`, which is
            // what 0x0062C1A0 plus 0x0062A4A0 compute on the A side: the
            // orientation there is a 4x3, nine floats of axis followed by the
            // entity origin, and the transform is the transpose applied to the
            // offset point.
            std::array<float, 9> axis{};
            if (!invokeAngleVectors(
                    angleVectors_,
                    entity.angles,
                    axis,
                    &exceptionDetails))
            {
                return false;
            }
            if (!std::ranges::all_of(axis, [](const float value) {
                    return std::isfinite(value);
                }))
            {
                continue;
            }

            const auto toLocal = [&axis, &entity](
                                     const std::array<float, 3> &world) {
                const std::array<float, 3> offset{
                    world[0] - entity.origin[0],
                    world[1] - entity.origin[1],
                    world[2] - entity.origin[2],
                };
                std::array<float, 3> local{};
                for (std::size_t row{}; row != local.size(); ++row)
                {
                    local[row] = offset[0] * axis[row * 3] +
                        offset[1] * axis[row * 3 + 1] +
                        offset[2] * axis[row * 3 + 2];
                }
                return local;
            };

            NativeDObjTraceResult result{};
            // SEED IT. The engine's own caller loads the running best fraction
            // into this field before the call (0x0046E1FC), so leaving it zero
            // asks the traceline to beat zero and it never reports a hit.
            result.fraction = aggregate.fraction;
            if (!invokeDObjTraceline(
                    dobjTraceline_,
                    dobj,
                    toLocal(request.start),
                    toLocal(request.end),
                    priorityMap.data(),
                    result,
                    &exceptionDetails))
            {
                return false;
            }
            ++traced;
            if (!std::isfinite(result.fraction) ||
                result.fraction >= aggregate.fraction ||
                result.fraction < 0.0f)
            {
                continue;
            }
            ++improved;

            if (hitboxDiagnosticsEnabled() &&
                entity.bodyRole == SvCollisionBodyRole::Player &&
                hitboxTraceLogCounter_++ < 128)
            {
                std::array<float, 3> impact{};
                for (std::size_t component{}; component != impact.size(); ++component)
                {
                    impact[component] = request.start[component] +
                        (request.end[component] - request.start[component]) *
                            result.fraction;
                }
                const auto localX = impact[0] - entity.origin[0];
                const auto localY = impact[1] - entity.origin[1];
                const auto localZ = impact[2] - entity.origin[2];
                const auto radial = std::sqrt(localX * localX + localY * localY);
                char line[512]{};
                std::snprintf(
                    line,
                    sizeof(line),
                    "hitbox trace entity=%lu partGroup=%u partName=%u "
                    "modelIndex=%u fraction=%.6f impact=(%.2f %.2f %.2f) "
                    "local=(%.2f %.2f %.2f) radial=%.2f "
                    "origin=(%.2f %.2f %.2f) yaw=%.2f boundsZ=%.2f..%.2f "
                    "scale=%.3f sample=%lu/128",
                    static_cast<unsigned long>(entity.entityNum),
                    static_cast<unsigned int>(result.partGroup),
                    static_cast<unsigned int>(result.partName),
                    static_cast<unsigned int>(result.modelIndex),
                    result.fraction,
                    impact[0], impact[1], impact[2],
                    localX, localY, localZ, radial,
                    entity.origin[0], entity.origin[1], entity.origin[2],
                    entity.angles[1],
                    entity.bounds.midpoint[2] - entity.bounds.halfSize[2],
                    entity.bounds.midpoint[2] + entity.bounds.halfSize[2],
                    entity.modelScale,
                    static_cast<unsigned long>(hitboxTraceLogCounter_));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }

            aggregate.fraction = result.fraction;
            aggregate.surfaceFlags = result.surfaceFlags;
            aggregate.modelIndex = result.modelIndex;
            aggregate.partName = result.partName;
            aggregate.partGroup = result.partGroup;
            aggregate.contents = entity.contents;
            aggregate.hitType = TraceHitTypeEntity;
            aggregate.hitId = static_cast<std::uint16_t>(entity.entityNum);
            // back out of model space, the way 0x00415830 does it there
            for (std::size_t component{}; component != 3; ++component)
            {
                aggregate.normal[component] =
                    result.normal[0] * axis[component] +
                    result.normal[1] * axis[3 + component] +
                    result.normal[2] * axis[6 + component];
            }
            if (!std::ranges::all_of(aggregate.normal, [](const float value) {
                    return std::isfinite(value);
                }))
            {
                aggregate.normal = { 0.0f, 0.0f, 1.0f };
            }
            aggregate.walkable = aggregate.normal[2] >= 0.7f;
        }
        if (locationalEntityTraceLogCounter_++ < 12)
        {
            char line[224]{};
            std::snprintf(
                line,
                sizeof(line),
                "locational entity trace entities=%zu considered=%lu "
                "traced=%lu improved=%lu fraction %.6f -> %.6f partGroup=%u",
                entities.size(),
                static_cast<unsigned long>(considered),
                static_cast<unsigned long>(traced),
                static_cast<unsigned long>(improved),
                entryFraction,
                aggregate.fraction,
                static_cast<unsigned int>(aggregate.partGroup));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }
        return true;
    }

    std::optional<bool> EngineBindings::traceTransformedDObjContentsPassed(
        const SvRadiusDamageTraceRequest &request,
        const SvCollisionEntity &entity) const
    {
        auto *const dobj = serverDObjGetAdapter(static_cast<std::int32_t>(entity.entityNum));
        if (!dobj || !dobjContentsTraceline_ || !angleVectors_)
            return std::nullopt;
        NativeExceptionDetails exceptionDetails{};
        std::byte *previousAnimConditionBase{};
        if (!installServerAnimConditionStorage(previousAnimConditionBase))
            return std::nullopt;
        // CODREF(Ghosts SV_PointSightTraceToEntity 14020AFF8..14020B022):
        // script models pose contents-selected bones and trace model geometry.
        // No player hit-location priority map is involved in this branch.
        std::array<float, 9> axis{};
        const auto prepared = prepareNativeServerDObjPoses(
                std::span(&entity, 1), request.contentMask, exceptionDetails) &&
            invokeAngleVectors(angleVectors_, entity.angles, axis, &exceptionDetails) &&
            std::ranges::all_of(axis, [](float v) { return std::isfinite(v); });
        NativeDObjTraceResult result{ .fraction = 1.0f };
        bool invoked = false;
        if (prepared)
        {
            const auto local = [&](const std::array<float, 3> &point) {
                std::array<float, 3> output{};
                for (std::size_t row = 0; row < 3; ++row)
                    for (std::size_t column = 0; column < 3; ++column)
                        output[row] += (point[column] - entity.origin[column]) *
                            axis[row * 3 + column];
                return output;
            };
            const auto start = local(request.start);
            const auto end = local(request.end);
            if (std::ranges::all_of(start, [](float v) { return std::isfinite(v); }) &&
                std::ranges::all_of(end, [](float v) { return std::isfinite(v); }))
            {
                invoked = invokeDObjContentsTraceline(dobjContentsTraceline_, dobj,
                    start, end, request.contentMask, result, &exceptionDetails);
            }
        }
        const auto restored = restoreServerAnimConditionStorage(previousAnimConditionBase);
        if (!invoked || !restored || !std::isfinite(result.fraction) ||
            result.fraction < 0.0f || result.fraction > 1.0f)
            return std::nullopt;
        return result.fraction == 1.0f;
    }

    std::optional<bool> EngineBindings::traceRadiusDamageVisibility(
        const SvRadiusDamageTraceRequest &request,
        const SvGlassState &glassState,
        const std::span<const SvCollisionEntity> entities) const
    {
        if (gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId() ||
            !nativeServerEntityMirrorMatches(entities))
            return std::nullopt;
        return SV_TestRadiusDamageVisibility(request, entities,
            [this, &glassState](const SvRadiusDamageTraceRequest &ray) -> std::optional<bool> {
                const auto world = traceWorld(ray.start, ray.end, PointTraceBounds,
                    ray.contentMask, glassState);
                if (!world)
                    return std::nullopt;
                if (world->fraction < 1.0f || world->startSolid || world->allSolid)
                    return false;
                // CODREF(out.exe 46E7C2 / 46E80D): WorldTrace does not itself
                // trace static map models. Keep the second retained stage.
                auto native = encodeTraceResult(*world);
                NativeExceptionDetails exceptionDetails{};
                if (!invokePointTraceStaticModels(pointTraceStaticModels_, ray.start,
                        ray.end, ray.contentMask, native, &exceptionDetails))
                    return std::nullopt;
                const auto models = decodeTraceResult(native);
                if (!models)
                    return std::nullopt;
                return models->fraction == 1.0f && !models->startSolid && !models->allSolid;
            },
            [this, &glassState](const SvRadiusDamageTraceRequest &ray,
                               const SvCollisionEntity &entity) -> std::optional<bool> {
                if (entity.shape == SvCollisionShape::ScriptModelDObj)
                    return traceTransformedDObjContentsPassed(ray, entity);
                // CODREF(Ghosts 14020AE30..14020AE56 / 14020B07E): with the
                // radius caller's NULL priority map, player entities take
                // collision geometry rather than player locational bones.
                const TraceResult initial{ .fraction = 1.0f };
                const auto trace = entity.shape == SvCollisionShape::BrushModel
                    ? traceTransformedBrushModel(initial, ray.start, ray.end,
                        PointTraceBounds, entity, glassState)
                    : traceTransformedCapsule(initial, ray.start, ray.end,
                        PointTraceBounds, entity);
                if (!trace)
                    return std::nullopt;
                return trace->fraction == 1.0f && !trace->startSolid && !trace->allSolid;
            });
    }

    std::optional<TraceResult> EngineBindings::traceServerPoint(
        const SvPointTraceRequest &request,
        const SvGlassState &glassState,
        const std::span<const SvCollisionEntity> entities) const
    {
        // OLMOD(point-trace-refusal-reasons): this function had FOUR silent
        // `return std::nullopt` paths and a caller that can only print
        // "unavailable". Section 36g's rule - an instrument that cannot fire is
        // worse than none - applies to a refusal as much as to a fault, and the
        // first time one of them fired it cost a whole cycle to learn which.
        // Sampled, so a burst of bullets cannot flood the log.
        const auto refuse = [this](const char *const reason) {
            if (pointTraceRefusalLogCounter_++ < 12)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("server point trace REFUSED reason=") + reason);
            }
            return std::optional<TraceResult>{};
        };
        if (!SV_IsPointTraceRequestValid(request))
            return refuse("request-invalid");
        if (request.mode != SvPointTraceMode::CollisionOnly)
        {
            if (gameThreadId_.load(std::memory_order_acquire) !=
                GetCurrentThreadId())
            {
                return refuse("not-game-thread");
            }
            if (!nativeServerEntityMirrorMatches(entities))
                return refuse("entity-mirror-mismatch");
        }
        if (request.mode == SvPointTraceMode::CollisionOnly)
        {
            return traceServerCapsule(
                request.start,
                request.end,
                PointTraceBounds,
                request.contentMask,
                glassState,
                entities,
                request.filter);
        }

        const auto priorityMap = SV_GetLocationalPriorityMap(request.mode);
        if (priorityMap.empty())
            return refuse("no-priority-map");
        NativeExceptionDetails exceptionDetails{};
        const auto traceStaticWorld = [&]() -> std::optional<TraceResult> {
            const auto world = traceWorld(
                request.start,
                request.end,
                PointTraceBounds,
                request.contentMask,
                glassState);
            if (!world || world->fraction == 0.0f)
                return world;

            // CODREF(out.exe sub_46E780): bullet traces set bStaticModels=1.
            // WorldTrace covers BSP only; CM_PointTraceStaticModels is a
            // separate retained stage and can replace the aggregate with a
            // nearer model hit carrying the material surface flags required by
            // penetration. Apply it to both the forward aggregate and the
            // reverse world-only thickness trace.
            auto native = encodeTraceResult(*world);
            if (!invokePointTraceStaticModels(
                    pointTraceStaticModels_,
                    request.start,
                    request.end,
                    request.contentMask,
                    native,
                    &exceptionDetails))
            {
                return std::nullopt;
            }
            return decodeTraceResult(native);
        };
        const auto worldTrace = request.entitiesOnly
            ? std::optional{ TraceResult{ .fraction = 1.0f } }
            : traceStaticWorld();
        if (!worldTrace)
            return refuse("world-trace-failed");
        if (request.worldOnly)
            return worldTrace;
        if (!request.entitiesOnly && worldTrace->fraction == 0.0f)
            return worldTrace;

        // THE ENGINE'S OWN WALKER IS NOT USABLE HERE. calcTraceExtents_ and
        // pointTraceToEntities_ stay bound and guarded because both addresses
        // are real and verified, but 0x0046E6D0 is out.exe's CLIENT
        // trace-to-entities: it enumerates a heap centity array the dedicated
        // never fills and offsets the ray by a global rather than by an entity.
        // 1649370 has no server-side twin, so the per-entity work is this
        // project's - see traceServerLocationalEntities above and section 73.
        std::byte *previousAnimConditionBase{};
        if (!installServerAnimConditionStorage(previousAnimConditionBase))
            return refuse("anim-condition-storage");
        // DObj pose calculation is the expensive part of locational tracing.
        // The old path posed every live DObj before the trace's own broadphase
        // rejected almost all of them. Build the exact same candidate set first
        // and only pose models whose bounds intersect this ray.
        std::vector<SvCollisionEntity> locationalCandidates;
        locationalCandidates.reserve(std::min<std::size_t>(entities.size(), 16));
        for (const auto &entity : entities)
        {
            if (entity.shape != SvCollisionShape::Capsule &&
                entity.shape != SvCollisionShape::ScriptModelDObj)
            {
                continue;
            }
            if (!SV_ShouldClipToEntity(
                    entity, request.filter, request.contentMask) ||
                !SV_ShouldBroadphaseClipToEntity(
                    request.start, request.end, PointTraceBounds, entity))
            {
                continue;
            }
            locationalCandidates.push_back(entity);
        }
        const std::span<const SvCollisionEntity> candidateView{
            locationalCandidates };
        const auto posesPrepared = prepareNativeServerDObjPoses(
            candidateView, request.contentMask, exceptionDetails);
        auto aggregate = *worldTrace;
        auto invoked = posesPrepared &&
            traceServerLocationalEntities(
                request, priorityMap, candidateView, aggregate, exceptionDetails);
        const auto animConditionBaseRestored =
            restoreServerAnimConditionStorage(previousAnimConditionBase);
        if (invoked)
        {
            // Actor DObjs are valid presentation objects, but CODOL's retained
            // locational walker does not reliably return their entity id on a
            // dedicated server.  The live Factory trace proves the failure:
            // actors 700..707 are linked and pass broadphase within a few units
            // of the shot axis, while the result remains a farther world hit
            // with no entity id.  That makes the otherwise complete generic
            // entity-damage path unreachable.
            //
            // Overlay only non-client capsules here.  Players retain native
            // DObj locational hit groups, and actors remain absent from the
            // ordinary Pmove collision view.  Starting from the native/world
            // aggregate also means an actor can win only when its capsule is
            // nearer than the wall already hit by the shot.
            for (const auto &entity : candidateView)
            {
                if (entity.entityNum < MaximumGameClients ||
                    entity.shape != SvCollisionShape::Capsule)
                {
                    continue;
                }
                // OLMOD(actor_skeletal_precedence): an admitted posed actor
                // already received a native bone trace, including its misses.
                // A nearer broad capsule must not erase partGroup/partName or
                // turn an actual gap between posed limbs into a body hit.
                if (entity.actorHitPose && entity.entityNum<actorHitPoseOwners_.size() &&
                    actorHitPoseOwners_[entity.entityNum].dobj &&
                    !actorHitPoseOwners_[entity.entityNum].failed &&
                    serverDObjGetAdapter(static_cast<int>(entity.entityNum))==
                        actorHitPoseOwners_[entity.entityNum].dobj)
                    continue;
                const auto capsuleTrace = traceTransformedCapsule(
                    aggregate,
                    request.start,
                    request.end,
                    PointTraceBounds,
                    entity);
                if (!capsuleTrace)
                {
                    invoked = false;
                    break;
                }
                static_cast<void>(SV_ApplyEntityTraceHit(
                    aggregate, *capsuleTrace, entity));
                if (aggregate.fraction == 0.0f)
                    break;
            }
            // OLMOD(locational-candidacy-diagnostics): report the words the
            // NATIVE trace reads, not the source mirror it was built from. The
            // capsule log in Appmain prints SvCollisionEntity::linked, which is
            // this project's own flag; CM_PointTraceToEntities instead reads
            // gentity +0x110 isLinked, +0x112 svFlags and +0x12C contents, and
            // SV_ToNativeServerEntity deliberately writes isLinked as ZERO and
            // leaves SV_LinkEntity to set it. A respawned player that the
            // source believes is linked but the native never linked looks
            // exactly like the measured symptom: capsule present, linked=1,
            // maxsZ=70, ray 2.5 units off its axis, and no hit for a whole
            // magazine while the same setup hit at 103 units before the death.
            // TODO(CODOL): remove once a post-respawn player is hittable.
        }
        if (!invoked || !animConditionBaseRestored)
        {
            char details[384]{};
            std::snprintf(
                details,
                sizeof(details),
                "native locational point trace unavailable code=0x%08lX "
                "address=%p access=%llu fault=%p "
                "eax=%p ebx=%p ecx=%p edx=%p esi=%p edi=%p "
                "ebp=%p esp=%p eip=%p",
                static_cast<unsigned long>(exceptionDetails.code),
                exceptionDetails.address,
                static_cast<unsigned long long>(exceptionDetails.accessType),
                exceptionDetails.faultAddress,
                reinterpret_cast<void *>(exceptionDetails.eax),
                reinterpret_cast<void *>(exceptionDetails.ebx),
                reinterpret_cast<void *>(exceptionDetails.ecx),
                reinterpret_cast<void *>(exceptionDetails.edx),
                reinterpret_cast<void *>(exceptionDetails.esi),
                reinterpret_cast<void *>(exceptionDetails.edi),
                reinterpret_cast<void *>(exceptionDetails.ebp),
                reinterpret_cast<void *>(exceptionDetails.esp),
                reinterpret_cast<void *>(exceptionDetails.eip));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, details);
            return std::nullopt;
        }
        return aggregate;
    }

    bool EngineBindings::validateMessageBindings() const
    {
        std::array<std::uint8_t, 64> buffer{};
        msg_t message{};
        MSG_Init(message, buffer.data(), static_cast<std::int32_t>(buffer.size()));
        if (message.overflowed || message.readOnly || message.data != buffer.data() ||
            message.maxsize != static_cast<std::int32_t>(buffer.size()) || message.cursize ||
            message.bit)
        {
            return false;
        }

        MSG_WriteBits(message, 0x78, 8);
        if (message.overflowed || message.cursize != 1 || message.bit != 8 ||
            buffer[0] != 0x78)
        {
            return false;
        }

        MSG_Init(message, buffer.data(), static_cast<std::int32_t>(buffer.size()));
        MSG_WriteString(message, "codol");
        if (message.overflowed || message.cursize != 6 ||
            std::memcmp(buffer.data(), "codol\0", 6) != 0)
        {
            return false;
        }

        // 512, NOT 256. The serverinfo now carries retail's ten measured keys
        // (see formatServerInfo) and the gamestate is ~277 bytes; at 256 this
        // writer overflowed and the stage failed for lack of room rather than
        // for a real mismatch.
        std::array<std::uint8_t, 512> gameStateBuffer{};
        EngineMsgWriter writer(*this, gameStateBuffer);
        SvGameState gameState{
            .mapName = "mp_crash",
            .gameType = "tdm",
        };
        SV_PopulateRequiredConfigStrings(gameState);
        gameState.configStrings.emplace(TimescaleConfigStringIndex, "0 0 1 1");
        // OLMOD_PERF_BASELINE deliberately suppresses the vision configstrings, so
        // SvGameStateFixtureBytes stops describing what the writer produces and this
        // stage would fail on the mode rather than on a defect -- which took the
        // dedicated down once already. The write is still exercised; only the byte
        // comparison is skipped, and only in the diagnostic mode.
        if (SV_PerfBaseline())
            return SV_WriteGameState(writer, gameState, 0, 0);
        return SV_WriteGameState(writer, gameState, 0, 0) &&
            std::ranges::equal(writer.data(), SvGameStateFixtureBytes);
    }

    EngineMsgWriter::EngineMsgWriter(
        const EngineBindings &bindings,
        const std::span<std::uint8_t> buffer)
        : bindings_(bindings)
    {
        if (buffer.size() > static_cast<std::size_t>(std::numeric_limits<std::int32_t>::max()))
        {
            message_.overflowed = 1;
            return;
        }
        bindings_.MSG_Init(
            message_, buffer.data(), static_cast<std::int32_t>(buffer.size()));
    }

    void EngineMsgWriter::MSG_WriteData(const std::span<const std::uint8_t> value)
    {
        if (message_.overflowed || message_.cursize < 0 ||
            message_.maxsize < message_.cursize ||
            value.size() > static_cast<std::size_t>(message_.maxsize - message_.cursize))
        {
            message_.overflowed = 1;
            return;
        }
        if (value.empty())
            return;
        std::memcpy(message_.data + message_.cursize, value.data(), value.size());
        message_.cursize += static_cast<std::int32_t>(value.size());
    }

    void EngineMsgWriter::MSG_WriteBits(
        const std::int32_t value,
        const std::uint32_t bits)
    {
        if (!message_.overflowed)
            bindings_.MSG_WriteBits(message_, value, bits);
    }

    void EngineMsgWriter::MSG_WriteString(const std::string_view value)
    {
        if (message_.overflowed || value.find('\0') != std::string_view::npos)
        {
            message_.overflowed = 1;
            return;
        }
        const std::string terminated(value);
        bindings_.MSG_WriteString(message_, terminated.c_str());
    }

    bool EngineMsgWriter::overflowed() const
    {
        return message_.overflowed != 0;
    }

    std::span<const std::uint8_t> EngineMsgWriter::data() const
    {
        if (message_.cursize <= 0)
            return {};
        return { message_.data, static_cast<std::size_t>(message_.cursize) };
    }

    // Let the CLIENT arm the same witness. The dedicated arms it around native
    // animation init; the client has no equivalent choke point, and the crash worth
    // catching happens there. HANDOFF section 152w.
    void armNativeFaultWitness(void *const module)
    {
        armVectoredFaultWitnessImpl(static_cast<std::uint8_t *>(module));
    }
}
