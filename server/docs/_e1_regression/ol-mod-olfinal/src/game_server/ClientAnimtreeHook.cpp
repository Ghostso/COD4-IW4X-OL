#include "ClientAnimtreeHook.hpp"

#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <span>
#include <string>

#include <Windows.h>
#include <tlhelp32.h>

namespace CodolGameServer
{
    namespace
    {
        // File offsets from the 3.19.26.13 client image, base 0x400000.
        constexpr std::uintptr_t ResolveCallRva = 0xB28B;    // 0x0040B28B
        constexpr std::uintptr_t ResolveRva     = 0x34ACF0;  // 0x0074ACF0
        // The loaded-zone table (12.126): count at `dword_1E2ACF4`, entries at
        // `unk_29C9DE8` with a 164-byte stride and the name inline at +8. Held as
        // RVAs so this does not assume the image loaded at its preferred base.
        constexpr std::uintptr_t ZoneCountRva = 0x1A2ACF4;   // 0x01E2ACF4
        constexpr std::uintptr_t ZoneTableRva = 0x25C9DE8;   // 0x029C9DE8
        constexpr std::size_t ZoneStride = 164;
        constexpr std::size_t ZoneNameOffset = 8;

        // The name->asset lookup structures, derived in 12.138 from `sub_74ACF0`,
        // `sub_74C610` and `sub_74D1E0`:
        //   string table   *(void **)dword_789C524, 20-byte stride,
        //                  +0..+1 refcount, +3 length, +4.. name inline
        //   buckets        0x7A5F100, u16 each, index ((kind*101) + sid*2) & 0xFFFF
        //   registry       0x7A7F100, 16-byte entries, 4096 per bank,
        //                  +0 value, +4 u16 next, +6 type, +8 key=(kind<<16)|(sid>>8)
        // `sub_74C610` MOVES a matched node to the front of its chain, so which of
        // two same-key entries wins is access-order dependent -- which is what this
        // walk is here to expose.
        constexpr std::uintptr_t StringTablePtrRva = 0x749C524;  // 0x0789C524
        constexpr std::uintptr_t KindRva           = 0x749C528;  // 0x0789C528
        constexpr std::uintptr_t BucketsRva        = 0x765F100;  // 0x07A5F100
        constexpr std::uintptr_t RegistryRva       = 0x767F100;  // 0x07A7F100
        constexpr std::size_t StringStride = 20;

        // `call sub_74ACF0` -- E8 with the rel32 the shipped image carries.
        constexpr std::array<std::uint8_t, 5> OriginalCall{
            0xE8, 0x60, 0xFA, 0x33, 0x00 };

        // THE BUILD SITE (12.143). `sub_785C20` is the animtree constructor and is
        // called from exactly one place -- `sub_74AAF0 + 0x12B`:
        //
        //     0074AC1A  51              push ecx                ; the NAME
        //     0074AC1B  E8 00 B0 03 00  call sub_785C20         ; <- replaced
        //     0074AC20  83 C4 0C        add  esp, 0Ch           ; cdecl, 3 args
        //     0074AC2C  8B D8           mov  ebx, eax           ; the built tree
        //
        // 12.140's hook watches which asset is CHOSEN; this one watches each one
        // being BUILT, which is a level below and is where a 519-entry tree and a
        // 123-entry tree diverge.
        constexpr std::uintptr_t BuildCallRva = 0x34AC1B;   // 0x0074AC1B
        constexpr std::uintptr_t BuildRva     = 0x385C20;   // 0x00785C20
        constexpr std::array<std::uint8_t, 5> OriginalBuildCall{
            0xE8, 0x00, 0xB0, 0x03, 0x00 };

        // THE POPULATE SITE (12.145). `sub_74AA00` finds `animtrees/<name>.atr`
        // (asset type 36), reads it, and hands it to Scr_AnimTreeParse. Called from
        // one place, `sub_74AAF0 + 0xCA`:
        //
        //     0074ABB9  51              push ecx                 ; the NAME
        //     0074ABBA  E8 41 FE FF FF  call sub_74AA00          ; <- replaced
        //     0074ABBF  83 C4 0C        add  esp, 0Ch            ; cdecl, 3 args
        //
        // A deterministic parser cannot turn identical bytes into 519 members here
        // and 123 there, so the question is whether the INPUT differs. The hook
        // repeats the asset lookup itself and logs the size the loader would read:
        // `v4 = *(DWORD *)(asset + 8) + 1`.
        constexpr std::uintptr_t PopulateCallRva = 0x34ABBA;  // 0x0074ABBA
        constexpr std::uintptr_t PopulateRva     = 0x34AA00;  // 0x0074AA00
        constexpr std::uintptr_t FindAssetRva    = 0x009D3B0; // 0x0049D3B0
        constexpr std::array<std::uint8_t, 5> OriginalPopulateCall{
            0xE8, 0x41, 0xFE, 0xFF, 0xFF };

        // THE NODE ALLOCATOR (12.146). `sub_788540` is the only creator of animtree
        // nodes (12.109.2) and its KEY arrives in EAX (12.112.1), so a plain C hook
        // cannot see it -- this one is a naked thunk that logs EAX and jumps
        // through, leaving the caller's stack and return address untouched.
        //
        // WHY: the wire can only ever carry key 0 or 2 (12.105, 12.110.1), yet the
        // demo's actors carry key 112 with ancestors 20/100/101/102 (12.113). One
        // of those two facts has a hole in it and only observation will say which.
        //
        // Keys 0 and 2 are skipped and the log is capped: node creation is a hot
        // path and 12.100 measured hundreds of nodes churning per 30s.
        constexpr std::uintptr_t AllocRva = 0x388540;   // 0x00788540
        constexpr std::array<std::uintptr_t, 5> AllocCallRvas{
            0x38731C,   // 0x0078731C  sub_7872D0  (clone)
            0x3886F8,   // 0x007886F8  sub_7886D0  (root)
            0x38878C,   // 0x0078878C  sub_7886D0  (ancestor)
            0x38888F,   // 0x0078888F  sub_7887E0  (asset-bearing leaf)
            0x38A097,   // 0x0078A097  sub_78A050  (clone)
        };
        // THE RECORD CONSUMER (12.149). `sub_527B40(a1@eax = record, a2, a3)` is
        // the only consumer of the dispatched command records, called once from
        // sub_5400B0 at 0x5401F7. Rather than chase which array fills them
        // (12.116.3, still open), read the records themselves as they are applied:
        //     +4  type      +16 entity      +20 KEY (record+20)      +48 flags
        // That is exactly what this server would have to reproduce.
        constexpr std::uintptr_t ApplyRva     = 0x127B40;   // 0x00527B40
        constexpr std::uintptr_t ApplyCallRva = 0x1401F7;   // 0x005401F7
        // THE WRITE WATCH (12.153). Static search for the producer is hopeless --
        // 212 candidates for +0x14 alone (12.150) and the base is a pointer, so an
        // offset names nothing. Instead: learn a live record's address from the
        // consumer, then put a HARDWARE write breakpoint on its `record+20` and let
        // the writer identify itself.
        //
        // DR0 is armed on every thread (the writer need not be ours), a vectored
        // handler logs the faulting EIP, and it disarms after the first hit so this
        // cannot storm the game. Separate opt-in from the hooks:
        // CODOL_ANIMTREE_WRITE_WATCH=1.
        std::atomic<std::uintptr_t> watchTarget{ 0 };
        std::atomic<bool> watchArmed{ false };
        std::atomic<int> watchHits{ 0 };
        void *watchHandle{};
        std::uintptr_t originalApply{};
        std::atomic<int> applyLogged{ 0 };

        std::uintptr_t originalAlloc{};
        std::atomic<int> allocLogged{ 0 };

        using PopulateFn = int (__cdecl *)(const char *, int, int);
        using FindAssetFn = int (__cdecl *)(int, const char *);
        PopulateFn originalPopulate{};
        FindAssetFn findAsset{};
        std::atomic<int> populateOrdinal{ 0 };

        using BuildFn = void *(__cdecl *)(const char *, int, int);
        BuildFn originalBuild{};
        std::atomic<int> buildOrdinal{ 0 };

        using ResolveFn = void *(__cdecl *)(const char *);

        ResolveFn originalResolve{};
        std::atomic<bool> installed{ false };
        std::atomic<int> resolveOrdinal{ 0 };

        // THE HOOK. Calls through and returns the original's result unchanged; the
        // only added effect is one log line per resolve. Six run per map load, one
        // per column of `sub_40B210`'s hard-coded name list, plus one for
        // "multiplayer" from the separate call site this hook does NOT touch.
        // GUARDED READS IN POD-ONLY HELPERS. __try cannot appear in a function
        // that needs object unwinding (C2712), so the SEH lives here and the
        // std::string work stays in the caller.
        bool readEntryCount(const void *p, std::uint32_t &out)
        {
            __try
            {
                out = *reinterpret_cast<const std::uint32_t *>(p);
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        bool copyName(const char *name, char *out, std::size_t cap)
        {
            __try
            {
                std::size_t i = 0;
                for (; i + 1 < cap && name[i]; ++i)
                    out[i] = name[i];
                out[i] = 0;
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        // POD-only, SEH-guarded like the others: the zone table is read from the
        // client's own memory during ITS load, so a partially built table must not
        // fault the load path.
        int readZones(char *out, std::size_t cap, std::uint32_t &count)
        {
            __try
            {
                auto *const module =
                    reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
                if (!module)
                    return 0;
                count = *reinterpret_cast<const std::uint32_t *>(
                    module + ZoneCountRva);
                if (count > 256)
                    return 0;
                const auto *const table = module + ZoneTableRva;
                std::size_t used = 0;
                for (std::uint32_t i = 0; i < count && used + 2 < cap; ++i)
                {
                    const char *n = reinterpret_cast<const char *>(
                        table + ZoneStride * i + ZoneNameOffset);
                    if (!*n)
                        continue;
                    if (used)
                        out[used++] = ',';
                    for (std::size_t k = 0; k < 48 && n[k] && used + 1 < cap; ++k)
                        out[used++] = n[k];
                }
                out[used] = 0;
                return 1;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
        }

        // ONE CHUNK OF THE STRING-TABLE SCAN, guarded on its own. The first cut
        // scanned 65536 entries inside a single __try; in-process that runs off the
        // end of the allocation and the fault killed the whole walk, which is why
        // the first run logged `chain=unreadable`. An external ReadProcessMemory
        // probe survived the same bug because its reads fail per-call instead of
        // faulting. Chunking means a fault ends the SCAN, not the function.
        int scanChunk(
            const std::uint8_t *table,
            std::uint32_t first,
            std::uint32_t last,
            const char *name,
            std::size_t nameLen,
            std::uint32_t &sid)
        {
            __try
            {
                for (std::uint32_t i = first; i < last; ++i)
                {
                    const auto *rec = table + StringStride * i;
                    if (!*reinterpret_cast<const std::uint16_t *>(rec))
                        continue;                        // refcount 0 -> dead slot
                    const char *n = reinterpret_cast<const char *>(rec + 4);
                    std::size_t k = 0;
                    while (k < nameLen && n[k] == name[k])
                        ++k;
                    if (k == nameLen && !n[k])
                    {
                        sid = i;
                        return 1;                        // found
                    }
                }
                return 0;                                // not in this chunk
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return -1;                               // ran off the table
            }
        }

        int walkChainInner(
            std::uint8_t *module,
            std::uint32_t kind,
            std::uint32_t sid,
            char *out,
            std::size_t cap)
        {
            __try
            {
                const auto bucketIndex = ((kind * 101u) + sid * 2u) & 0xFFFFu;
                const auto key = ((kind << 16) | (sid >> 8)) & 0xFFFFFFFFu;
                auto slot = *reinterpret_cast<const std::uint16_t *>(
                    module + BucketsRva + bucketIndex * 2u);
                std::size_t used = static_cast<std::size_t>(std::snprintf(
                    out, cap, "sid=%u bucket=%u key=0x%08X chain:",
                    sid, bucketIndex, key));
                for (int depth = 0; slot && depth < 16 && used + 72 < cap; ++depth)
                {
                    const auto *entry = module + RegistryRva +
                        static_cast<std::uintptr_t>(
                            (kind & 1u) * 4096u + slot) * 16u;
                    const auto value =
                        *reinterpret_cast<const std::uint32_t *>(entry);
                    const auto next =
                        *reinterpret_cast<const std::uint16_t *>(entry + 4);
                    const auto entryKey =
                        *reinterpret_cast<const std::uint32_t *>(entry + 8);
                    std::uint32_t count = 0;
                    if (value > 0x10000u)
                        count = *reinterpret_cast<const std::uint32_t *>(value);
                    used += static_cast<std::size_t>(std::snprintf(
                        out + used, cap - used,
                        " [slot=%u val=0x%08X n=%u key=0x%08X%s]",
                        slot, value, count, entryKey,
                        entryKey == key ? " KEYMATCH" : ""));
                    slot = next;
                }
                return 1;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
        }

        int walkChain(const char *name, char *out, std::size_t cap)
        {
            auto *const module =
                reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
            if (!module || !name)
                return 0;
            std::uint32_t kind{};
            const std::uint8_t *strTable{};
            {
                __try
                {
                    kind = *reinterpret_cast<const std::uint32_t *>(
                        module + KindRva);
                    strTable = *reinterpret_cast<std::uint8_t *const *>(
                        module + StringTablePtrRva);
                }
                __except (EXCEPTION_EXECUTE_HANDLER)
                {
                    return 0;
                }
            }
            if (!strTable)
                return 0;
            std::size_t nameLen = 0;
            while (nameLen < 63 && name[nameLen])
                ++nameLen;
            std::uint32_t sid = 0xFFFFFFFFu;
            std::uint32_t scanned = 0;
            constexpr std::uint32_t Chunk = 256;
            for (std::uint32_t base = 0; base < 65536u; base += Chunk)
            {
                const auto r = scanChunk(
                    strTable, base, base + Chunk, name, nameLen, sid);
                if (r == 1)
                    break;
                if (r < 0)
                    break;                               // end of the table
                scanned = base + Chunk;
            }
            if (sid == 0xFFFFFFFFu)
            {
                // Report the ACTUAL pointers rather than guessing why the scan
                // found nothing: a wrong module base or a table that is not yet
                // populated at resolve time look identical from the miss alone.
                std::snprintf(
                    out, cap,
                    "sid=none scanned=%u module=0x%08X strTable=0x%08X kind=%u",
                    scanned,
                    static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(module)),
                    static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(strTable)),
                    kind);
                return 1;
            }
            if (!walkChainInner(module, kind, sid, out, cap))
            {
                std::snprintf(out, cap, "sid=%u chainwalk=faulted", sid);
                return 1;
            }
            return 1;
        }

        // Repeat the loader's own lookup and read the size field. SEH-guarded and
        // POD-only: this runs inside the client's map load.
        int readAssetSize(const char *path, std::uint32_t &out)
        {
            __try
            {
                if (!findAsset)
                    return 0;
                const auto asset = findAsset(36, path);
                if (!asset)
                    return 0;
                out = *reinterpret_cast<const std::uint32_t *>(
                    static_cast<std::uintptr_t>(asset) + 8);
                return 1;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
        }

        extern "C" void __cdecl logNodeKey(
            unsigned int key, unsigned int asset, unsigned int parent,
            unsigned int caller)
        {
            if (key < 3)
                return;
            if (allocLogged.fetch_add(1) >= 4000)
                return;
            // WHICH MINTER. Without this the log cannot tell a wire-driven mint
            // (sub_7887E0, key = record+20) from a clone (sub_7872D0, key copied
            // from a source node) -- and that distinction is the whole question.
            const auto rva = caller - 0x400000u;
            const char *site =
                rva == 0x38731Cu + 5 ? "clone7872D0" :
                rva == 0x3886F8u + 5 ? "root7886D0"  :
                rva == 0x38878Cu + 5 ? "anc7886D0"   :
                rva == 0x38888Fu + 5 ? "leaf7887E0"  :
                rva == 0x38A097u + 5 ? "clone78A050" : "?";
            char buf[32]{};
            std::snprintf(buf, sizeof(buf), "0x%08X", caller);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ANIMTREENODE key=" + std::to_string(key) +
                " asset=" + std::to_string(asset) +
                " parent=" + std::to_string(parent) +
                " from=" + site + " ret=" + buf);
        }

        // [esp+36] is the return address into whichever call site invoked us --
        // pushad (32) + pushfd (4) above the thunk's own return slot.
        LONG CALLBACK watchVeh(EXCEPTION_POINTERS *info)
        {
            if (info->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP)
                return EXCEPTION_CONTINUE_SEARCH;
            const auto eip = static_cast<unsigned>(info->ContextRecord->Eip);
            if (watchHits.fetch_add(1) < 12)
            {
                char buf[64]{};
                std::snprintf(buf, sizeof(buf), "0x%08X", eip);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("ANIMTREEWRITER eip=") + buf);
            }
            // Disarm: clear DR7 on this thread so one writer does not storm the log.
            info->ContextRecord->Dr7 = 0;
            return EXCEPTION_CONTINUE_EXECUTION;
        }

        void armWriteWatch(std::uintptr_t address)
        {
            if (watchArmed.exchange(true))
                return;
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "CODOL_ANIMTREE_WRITE_WATCH", value.data(), value.size());
            if (!size || value[0] == '0' || value[0] == 'n' || value[0] == 'N')
                return;
            watchTarget.store(address);
            if (!watchHandle)
                watchHandle = AddVectoredExceptionHandler(1, watchVeh);
            // DR0 = address, 4-byte WRITE watch, local enable.
            const auto snap =
                CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
            if (snap == INVALID_HANDLE_VALUE)
                return;
            THREADENTRY32 te{ sizeof(te) };
            const auto self = GetCurrentProcessId();
            int armedCount = 0;
            if (Thread32First(snap, &te))
            {
                do
                {
                    if (te.th32OwnerProcessID != self)
                        continue;
                    // NEVER THE CALLING THREAD. The first cut suspended every
                    // thread including this one and the process deadlocked
                    // instantly -- the client froze mid-demo (12.153). Our own
                    // debug registers are set without suspending, since a thread
                    // can safely set its own context.
                    if (te.th32ThreadID == GetCurrentThreadId())
                        continue;
                    const auto th = OpenThread(
                        THREAD_GET_CONTEXT | THREAD_SET_CONTEXT |
                            THREAD_SUSPEND_RESUME,
                        FALSE, te.th32ThreadID);
                    if (!th)
                        continue;
                    CONTEXT ctx{};
                    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                    SuspendThread(th);
                    if (GetThreadContext(th, &ctx))
                    {
                        ctx.Dr0 = address;
                        // len=4 (0b11), rw=write (0b01), L0 enable
                        ctx.Dr7 = (ctx.Dr7 & ~0xFul) | 1ul |
                            (0x1ul << 16) | (0x3ul << 18);
                        ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                        if (SetThreadContext(th, &ctx))
                            ++armedCount;
                    }
                    ResumeThread(th);
                    CloseHandle(th);
                } while (Thread32Next(snap, &te));
            }
            CloseHandle(snap);
            // And this thread, context-set only, no suspend.
            {
                CONTEXT ctx{};
                ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                const auto me = GetCurrentThread();
                if (GetThreadContext(me, &ctx))
                {
                    ctx.Dr0 = address;
                    ctx.Dr7 = (ctx.Dr7 & ~0xFul) | 1ul |
                        (0x1ul << 16) | (0x3ul << 18);
                    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS;
                    if (SetThreadContext(me, &ctx))
                        ++armedCount;
                }
            }
            char buf[96]{};
            std::snprintf(
                buf, sizeof(buf), "0x%08X on %d threads",
                static_cast<unsigned>(address), armedCount);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("ANIMTREEWATCH armed at ") + buf);
        }

        // POD-only helper: __try cannot share a function with objects that need
        // unwinding (C2712) -- the same fault as 12.140's first cut.
        int readRecord(
            unsigned int record, unsigned int *type, unsigned int *ent,
            unsigned int *key, unsigned int *flags)
        {
            __try
            {
                const auto *r = reinterpret_cast<const unsigned int *>(record);
                *type = r[1]; *ent = r[4]; *key = r[5]; *flags = r[12];
                return 1;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
        }

        extern "C" void __cdecl logApply(unsigned int record)
        {
            if (applyLogged.fetch_add(1) >= 3000)
                return;
            unsigned int type = 0, ent = 0, key = 0, flags = 0;
            if (!readRecord(record, &type, &ent, &key, &flags))
                return;
            if (!key)
                return;                       // key 0 dominates; only the rest matter
            char addrBuf[32]{};
            std::snprintf(addrBuf, sizeof(addrBuf), "0x%08X", record);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ANIMTREEAPPLY type=" + std::to_string(type) +
                " ent=" + std::to_string(ent) +
                " key=" + std::to_string(key) +
                " flags=" + std::to_string(flags) +
                " rec=" + addrBuf);
            // Arm on the first record that carries a real key: that buffer slot is
            // the one a producer must have written.
            if (key > 2)
                armWriteWatch(static_cast<std::uintptr_t>(record) + 20);
        }

        __declspec(naked) void applyThunk()
        {
            __asm
            {
                pushad
                pushfd
                push eax                 // a1 = the record
                call logApply
                add  esp, 4
                popfd
                popad
                jmp  dword ptr [originalApply]
            }
        }

        __declspec(naked) void nodeAllocThunk()
        {
            __asm
            {
                pushad
                pushfd
                mov  ebx, [esp+36]      // return address = which call site
                mov  ecx, [esp+48]      // a4 = parent
                mov  edx, [esp+44]      // a3 = asset
                push ebx
                push ecx
                push edx
                push eax                // the key
                call logNodeKey
                add  esp, 16
                popfd
                popad
                jmp  dword ptr [originalAlloc]
            }
        }

        int __cdecl populateHook(const char *name, int a2, int a3)
        {
            const auto result =
                originalPopulate ? originalPopulate(name, a2, a3) : 0;
            const auto ordinal = populateOrdinal.fetch_add(1);
            char nameBuffer[80]{};
            const bool haveName =
                name && copyName(name, nameBuffer, sizeof(nameBuffer));
            char path[128]{};
            std::snprintf(
                path, sizeof(path), "animtrees/%s.atr",
                haveName ? nameBuffer : "");
            std::uint32_t size{};
            const bool haveSize = haveName && readAssetSize(path, size) != 0;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ANIMTREEASSET n=" + std::to_string(ordinal) +
                " name=" + (haveName ? std::string(nameBuffer)
                                     : std::string("<unreadable>")) +
                " assetSize=" +
                (haveSize ? std::to_string(size) : std::string("unreadable")) +
                " a3=" + std::to_string(a3) +
                " ok=" + std::to_string(result));
            return result;
        }

        void *__cdecl buildHook(const char *name, int a2, int a3)
        {
            void *const result =
                originalBuild ? originalBuild(name, a2, a3) : nullptr;
            const auto ordinal = buildOrdinal.fetch_add(1);
            std::uint32_t entries{};
            const bool haveEntries = result && readEntryCount(result, entries);
            char nameBuffer[80]{};
            const bool haveName =
                name && copyName(name, nameBuffer, sizeof(nameBuffer));
            char pointerBuffer[32]{};
            std::snprintf(
                pointerBuffer, sizeof(pointerBuffer), "0x%08X",
                static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(result)));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ANIMTREEBUILD n=" + std::to_string(ordinal) +
                " name=" + (haveName ? std::string(nameBuffer)
                                     : std::string(name ? "<unreadable>" : "<null>")) +
                " a2=" + std::to_string(a2) +
                " a3=" + std::to_string(a3) +
                " -> " + pointerBuffer +
                " entries=" +
                (haveEntries ? std::to_string(entries) : std::string("unreadable")));
            return result;
        }

        void *__cdecl resolveHook(const char *name)
        {
            void *const result = originalResolve ? originalResolve(name) : nullptr;
            const auto ordinal = resolveOrdinal.fetch_add(1);
            std::uint32_t entries{};
            const bool haveEntries = result && readEntryCount(result, entries);
            char nameBuffer[80]{};
            const bool haveName = name && copyName(name, nameBuffer, sizeof(nameBuffer));
            char zoneBuffer[2048]{};
            std::uint32_t zoneCount{};
            const bool haveZones =
                readZones(zoneBuffer, sizeof(zoneBuffer), zoneCount) != 0;
            char chainBuffer[1024]{};
            const bool haveChain = walkChain(name, chainBuffer, sizeof(chainBuffer)) != 0;
            char pointerBuffer[32]{};
            std::snprintf(
                pointerBuffer, sizeof(pointerBuffer), "0x%08X",
                static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(result)));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ANIMTREERESOLVE n=" + std::to_string(ordinal) +
                " name=" + (haveName ? std::string(nameBuffer)
                                     : std::string(name ? "<unreadable>" : "<null>")) +
                " -> " + pointerBuffer +
                " entries=" +
                (haveEntries ? std::to_string(entries) : std::string("unreadable")) +
                " zones=" +
                (haveZones ? std::to_string(zoneCount) : std::string("?")) +
                " [" + std::string(zoneBuffer) + "] " +
                (haveChain ? std::string(chainBuffer) : std::string("chain=unreadable")));
            return result;
        }
    }

    AnimtreeHookResult installClientAnimtreeHook()
    {
        if (installed.load())
            return AnimtreeHookResult::AlreadyInstalled;

        std::array<char, 8> value{};
        const auto size = GetEnvironmentVariableA(
            "CODOL_ANIMTREE_RESOLVE_HOOK", value.data(), value.size());
        // DEFAULT OFF. Two changes broke the client earlier in this session
        // (12.127, 12.131); a patch that rewrites the client's own load path opts
        // in explicitly rather than shipping enabled.
        const auto enabled = size &&
            value[0] != '0' && value[0] != 'n' && value[0] != 'N' &&
            value[0] != 'f' && value[0] != 'F';
        if (!enabled)
            return AnimtreeHookResult::Disabled;

        std::array<char, 8> traceValue{};
        const auto traceSize = GetEnvironmentVariableA(
            "CODOL_ANIMTREE_TRACE", traceValue.data(), traceValue.size());
        // The resolver/build/populate hooks below are the production fix.  The
        // allocator and record-consumer hooks are old RE instruments: each adds a
        // thunk, atomic and formatted file write to animation hot paths, producing
        // thousands of events exactly when a zombie wave appears.  Keep those
        // instruments available, but never install them during ordinary play.
        const auto traceDiagnostics = traceSize &&
            traceValue[0] != '0' && traceValue[0] != 'n' &&
            traceValue[0] != 'N' && traceValue[0] != 'f' &&
            traceValue[0] != 'F';

        auto *const module =
            reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return AnimtreeHookResult::UnsupportedHost;
        const auto *const dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return AnimtreeHookResult::UnsupportedHost;
        const auto *const nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(
            module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE)
            return AnimtreeHookResult::UnsupportedHost;
        const auto imageSize = nt->OptionalHeader.SizeOfImage;
        if (ResolveCallRva + OriginalCall.size() > imageSize ||
            ResolveRva >= imageSize)
        {
            return AnimtreeHookResult::UnsupportedHost;
        }

        auto *const site = module + ResolveCallRva;
        // VERIFY BEFORE WRITING, the same discipline as installClientProcessPatches.
        // A build whose bytes differ is a build this offset was not derived from.
        if (!std::equal(OriginalCall.begin(), OriginalCall.end(), site))
            return AnimtreeHookResult::UnexpectedBytes;

        originalResolve = reinterpret_cast<ResolveFn>(module + ResolveRva);

        const auto target = reinterpret_cast<std::uintptr_t>(&resolveHook);
        const auto next = reinterpret_cast<std::uintptr_t>(site) + 5;
        const auto relative = static_cast<std::int32_t>(target - next);

        std::array<std::uint8_t, 5> replacement{ 0xE8 };
        std::memcpy(replacement.data() + 1, &relative, sizeof(relative));

        DWORD oldProtection{};
        if (!VirtualProtect(
                site, replacement.size(), PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            return AnimtreeHookResult::ProtectionFailed;
        }
        std::ranges::copy(replacement, site);
        FlushInstructionCache(GetCurrentProcess(), site, replacement.size());
        DWORD ignored{};
        VirtualProtect(site, replacement.size(), oldProtection, &ignored);

        // AND THE BUILD SITE. Verified independently; if its bytes do not match the
        // resolve hook still stands, because the two answer different questions.
        auto *const buildSite = module + BuildCallRva;
        if (BuildCallRva + OriginalBuildCall.size() <= imageSize &&
            BuildRva < imageSize &&
            std::equal(
                OriginalBuildCall.begin(), OriginalBuildCall.end(), buildSite))
        {
            originalBuild = reinterpret_cast<BuildFn>(module + BuildRva);
            const auto buildTarget =
                reinterpret_cast<std::uintptr_t>(&buildHook);
            const auto buildNext =
                reinterpret_cast<std::uintptr_t>(buildSite) + 5;
            const auto buildRelative =
                static_cast<std::int32_t>(buildTarget - buildNext);
            std::array<std::uint8_t, 5> buildReplacement{ 0xE8 };
            std::memcpy(
                buildReplacement.data() + 1, &buildRelative,
                sizeof(buildRelative));
            DWORD buildOld{};
            if (VirtualProtect(
                    buildSite, buildReplacement.size(),
                    PAGE_EXECUTE_READWRITE, &buildOld))
            {
                std::ranges::copy(buildReplacement, buildSite);
                FlushInstructionCache(
                    GetCurrentProcess(), buildSite, buildReplacement.size());
                DWORD buildIgnored{};
                VirtualProtect(
                    buildSite, buildReplacement.size(), buildOld,
                    &buildIgnored);
            }
        }
        // AND THE POPULATE SITE, verified independently like the others.
        auto *const popSite = module + PopulateCallRva;
        if (PopulateCallRva + OriginalPopulateCall.size() <= imageSize &&
            PopulateRva < imageSize && FindAssetRva < imageSize &&
            std::equal(
                OriginalPopulateCall.begin(), OriginalPopulateCall.end(),
                popSite))
        {
            originalPopulate = reinterpret_cast<PopulateFn>(module + PopulateRva);
            findAsset = reinterpret_cast<FindAssetFn>(module + FindAssetRva);
            const auto popTarget = reinterpret_cast<std::uintptr_t>(&populateHook);
            const auto popNext = reinterpret_cast<std::uintptr_t>(popSite) + 5;
            const auto popRelative =
                static_cast<std::int32_t>(popTarget - popNext);
            std::array<std::uint8_t, 5> popReplacement{ 0xE8 };
            std::memcpy(
                popReplacement.data() + 1, &popRelative, sizeof(popRelative));
            DWORD popOld{};
            if (VirtualProtect(
                    popSite, popReplacement.size(), PAGE_EXECUTE_READWRITE,
                    &popOld))
            {
                std::ranges::copy(popReplacement, popSite);
                FlushInstructionCache(
                    GetCurrentProcess(), popSite, popReplacement.size());
                DWORD popIgnored{};
                VirtualProtect(
                    popSite, popReplacement.size(), popOld, &popIgnored);
            }
        }
        // AND THE FIVE NODE-ALLOCATOR CALL SITES. Each is verified to be an E8
        // whose rel32 actually targets sub_788540 before it is touched, so a wrong
        // offset refuses instead of redirecting something else.
        if (traceDiagnostics && AllocRva < imageSize)
        {
            originalAlloc =
                reinterpret_cast<std::uintptr_t>(module) + AllocRva;
            for (const auto callRva : AllocCallRvas)
            {
                if (callRva + 5 > imageSize)
                    continue;
                auto *const site = module + callRva;
                if (site[0] != 0xE8)
                    continue;
                std::int32_t rel{};
                std::memcpy(&rel, site + 1, sizeof(rel));
                const auto target =
                    reinterpret_cast<std::uintptr_t>(site) + 5 + rel;
                if (target != originalAlloc)
                    continue;               // not the call we derived
                const auto thunk =
                    reinterpret_cast<std::uintptr_t>(&nodeAllocThunk);
                const auto next = reinterpret_cast<std::uintptr_t>(site) + 5;
                const auto newRel = static_cast<std::int32_t>(thunk - next);
                std::array<std::uint8_t, 5> rep{ 0xE8 };
                std::memcpy(rep.data() + 1, &newRel, sizeof(newRel));
                DWORD old{};
                if (VirtualProtect(
                        site, rep.size(), PAGE_EXECUTE_READWRITE, &old))
                {
                    std::ranges::copy(rep, site);
                    FlushInstructionCache(GetCurrentProcess(), site, rep.size());
                    DWORD ign{};
                    VirtualProtect(site, rep.size(), old, &ign);
                }
            }
        }
        // AND THE RECORD CONSUMER, verified by rel32 target like the allocator sites.
        if (traceDiagnostics && ApplyRva < imageSize &&
            ApplyCallRva + 5 <= imageSize)
        {
            auto *const site = module + ApplyCallRva;
            originalApply =
                reinterpret_cast<std::uintptr_t>(module) + ApplyRva;
            if (site[0] == 0xE8)
            {
                std::int32_t rel{};
                std::memcpy(&rel, site + 1, sizeof(rel));
                if (reinterpret_cast<std::uintptr_t>(site) + 5 + rel ==
                    originalApply)
                {
                    const auto thunk =
                        reinterpret_cast<std::uintptr_t>(&applyThunk);
                    const auto next =
                        reinterpret_cast<std::uintptr_t>(site) + 5;
                    const auto newRel =
                        static_cast<std::int32_t>(thunk - next);
                    std::array<std::uint8_t, 5> rep{ 0xE8 };
                    std::memcpy(rep.data() + 1, &newRel, sizeof(newRel));
                    DWORD old{};
                    if (VirtualProtect(
                            site, rep.size(), PAGE_EXECUTE_READWRITE, &old))
                    {
                        std::ranges::copy(rep, site);
                        FlushInstructionCache(
                            GetCurrentProcess(), site, rep.size());
                        DWORD ign{};
                        VirtualProtect(site, rep.size(), old, &ign);
                    }
                }
            }
        }
        installed.store(true);
        return AnimtreeHookResult::Installed;
    }

    const char *animtreeHookResultName(const AnimtreeHookResult result)
    {
        switch (result)
        {
        case AnimtreeHookResult::Installed: return "installed";
        case AnimtreeHookResult::AlreadyInstalled: return "already installed";
        case AnimtreeHookResult::Disabled: return "disabled";
        case AnimtreeHookResult::UnsupportedHost: return "unsupported host";
        case AnimtreeHookResult::UnexpectedBytes: return "unexpected bytes";
        case AnimtreeHookResult::ProtectionFailed: return "protection failed";
        }
        return "unknown";
    }
}
