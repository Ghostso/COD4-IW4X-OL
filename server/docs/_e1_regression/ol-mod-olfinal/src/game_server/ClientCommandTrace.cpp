#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "ClientCommandTrace.hpp"

#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <share.h>
#include <cstring>
#include <filesystem>
#include <mutex>
#include <string>
#include <vector>
#include <thread>

namespace
{
    // ---- the target -----------------------------------------------------------------------
    //
    // sub_614C00, verified against C:\Games\OLfinal\out.exe rather than taken from a note:
    //
    //     RVA 0x214C00   55 8b ec 83 ec 08  53 56 57  8b f8  a1 ...
    //                    push ebp / mov ebp,esp / sub esp,8 / push ebx / push esi / push edi
    //                    mov edi, eax          <- EAX is the sequence number on entry
    //
    // SIX BYTES, NOT FIVE. The first three instructions occupy 1 + 2 + 3 bytes, so a five-byte
    // steal would cut `sub esp, 8` in half and the client would die on the first command.
    // FrameHook's HookSize of 5 is correct only because Com_Frame's prologue happens to land on
    // a boundary at five (55 8b ec 56 57). The size is a property of the TARGET, not the hook.
    constexpr std::size_t ClientCommandDispatchRva = 0x214C00;
    constexpr std::size_t StolenBytes = 6;

    // The command text is NOT an argument. sub_614C00 reads it out of a 512-slot ring:
    //
    //     base = dword_331C0C8 ^ 0xD362501F        (RVA 0x2F1C0C8, obfuscated pointer)
    //     cmd  = base + 524628 + ((seq & 0x1FF) << 10)
    //
    // 512 slots of 1024 bytes. `(seq & 0x1FF)` is where the ring size is stated by the image
    // itself, independently of the wire measurement that first established it.
    constexpr std::size_t CommandRingBaseRva = 0x2F1C0C8;
    constexpr std::uint32_t CommandRingBaseKey = 0xD362501F;
    constexpr std::size_t CommandRingOffset = 524628;
    constexpr std::size_t CommandRingSlots = 512;
    constexpr std::size_t CommandRingStride = 1024;

    std::uint8_t *Trampoline{};
    std::uint8_t *Target{};
    const std::uint8_t *ModuleBase{};

    std::mutex Gate;
    FILE *Output{};
    std::atomic<std::uint64_t> Recorded{};
    std::atomic<std::uint64_t> Unreadable{};
    std::atomic<bool> Recording{};
    std::string OutputPath;
    DWORD StartedAt{};

    /// Is this address safe to read? A ring pointer that has not been built yet is null or
    /// garbage, and a trace that faults inside the dispatch it observes is worse than no trace.
    bool readable(const void *address, const std::size_t bytes)
    {
        if (!address)
            return false;

        MEMORY_BASIC_INFORMATION info{};

        if (!VirtualQuery(address, &info, sizeof(info)))
            return false;

        if (info.State != MEM_COMMIT)
            return false;

        constexpr DWORD NoAccess = PAGE_NOACCESS | PAGE_GUARD;

        if (info.Protect & NoAccess)
            return false;

        const auto *start = static_cast<const std::uint8_t *>(info.BaseAddress);
        const auto *end = start + info.RegionSize;

        return static_cast<const std::uint8_t *>(address) + bytes <= end;
    }

    /// The command text for a sequence number, or an empty string if the ring cannot be read.
    std::string commandAt(const std::uint32_t sequence)
    {
        if (!ModuleBase)
            return {};

        const auto *slotPointer = reinterpret_cast<const std::uint32_t *>(
            ModuleBase + CommandRingBaseRva);

        if (!readable(slotPointer, sizeof(std::uint32_t)))
            return {};

        const auto obfuscated = *slotPointer;

        if (!obfuscated)
            return {};

        const auto base = obfuscated ^ CommandRingBaseKey;
        const auto *text = reinterpret_cast<const char *>(
            base + CommandRingOffset +
            ((sequence & (CommandRingSlots - 1)) * CommandRingStride));

        if (!readable(text, CommandRingStride))
            return {};

        // A '!' RECORD IS BINARY AND MUST NOT BE NUL-TERMINATED.
        //
        // Measured on the first live run: all 85 '!' records came out as ONE BYTE, "!", because
        // the sub-frame carries a NUL at offset 1 and a NUL-bounded read stops there. Half the
        // traffic -- the live configstring updates and BOTH scoreboard records -- collapsed into
        // one indistinguishable row. The comment in record() warned about exactly that, and the
        // bug was upstream of the code it warned about.
        //
        // The framing is '!' at 0, a uint16 LENGTH at +2, payload from +4. So the record is
        // 4 + length bytes and the payload's first byte is the inner verb sub_614AC0 switches on.
        if (*text == '!')
        {
            std::uint16_t length{};
            std::memcpy(&length, text + 2, sizeof(length));

            // CLAMPED TO THE SLOT. A length read out of a slot that was not written this cycle
            // is whatever was there before, and trusting it would walk off the ring.
            return std::string(text, std::min<std::size_t>(
                4u + static_cast<std::size_t>(length), CommandRingStride));
        }

        // BOUNDED BY THE SLOT, NOT BY THE NUL. A slot that has never been written holds
        // whatever was there before, and strlen on it would run off the end of the ring.
        const auto *end = static_cast<const char *>(
            std::memchr(text, '\0', CommandRingStride));

        return std::string(text, end ? static_cast<std::size_t>(end - text) : CommandRingStride);
    }

    /// Escape for a CSV field. A reliable command carries quotes and commas routinely --
    /// `s ui_DMKillScore "50"` has both -- and a trace that cannot be parsed is not a trace.
    std::string escape(const std::string &value)
    {
        std::string out;
        out.reserve(value.size() + 2);

        for (const auto c : value)
        {
            if (c == '"')
                out += "\"\"";
            else if (static_cast<unsigned char>(c) < 0x20)
                out += ' ';                       // a newline in a field would end the row
            else
                out += c;
        }

        return out;
    }

    void __cdecl record(const std::uint32_t sequence)
    {
        if (!Recording.load(std::memory_order_relaxed))
            return;

        const auto text = commandAt(sequence);

        if (text.empty())
        {
            Unreadable.fetch_add(1, std::memory_order_relaxed);
            return;
        }

        // THE VERB, AND THE INNER VERB WHEN IT IS A SUB-FRAME. A '!' record is a binary
        // sub-frame: '!' then a uint16 length at +2 and the payload at +4, whose first byte
        // selects the handler in sub_614AC0. Logging only the '!' would collapse % @ J K --
        // four different handlers, one of them the scoreboard -- into one indistinguishable
        // row, which is the shape of a finding being deleted by its own instrument.
        const auto verb = text.front();
        char inner = 0;
        const char *dispatch = "sub_613A40";

        if (verb == '!')
        {
            if (text.size() > 4)
                inner = text[4];
            dispatch = "sub_614AC0";
        }
        else if (verb == 'd' || verb == 'k' || verb == 'x' || verb == 't')
        {
            dispatch = "sub_614C00";
        }

        // HEX FOR A BINARY RECORD, TEXT FOR A TEXT ONE. escape() turns every byte below 0x20
        // into a space, which is right for a stray control character in a command string and
        // destroys a binary payload -- and the binary ones are the records we cannot decode
        // offline, so they are the whole reason this exists.
        std::string rendered;

        if (verb == '!')
        {
            static constexpr char Digits[] = "0123456789abcdef";
            rendered.reserve(text.size() * 2);

            for (const auto c : text)
            {
                const auto byte = static_cast<unsigned char>(c);
                rendered += Digits[byte >> 4];
                rendered += Digits[byte & 0x0F];
            }
        }
        else
        {
            rendered = escape(text);
        }

        const std::lock_guard lock(Gate);

        if (!Output)
            return;

        std::fprintf(Output, "%lu,%u,%c,%s,%s,%zu,\"%s\"\n",
                     static_cast<unsigned long>(GetTickCount() - StartedAt),
                     sequence,
                     verb,
                     inner ? std::string(1, inner).c_str() : "",
                     dispatch,
                     text.size(),
                     rendered.c_str());

        // FLUSHED EVERY ROW, DELIBERATELY. At ~2.4 commands a second the cost is nothing, and
        // the alternative has already cost this project a session: a watcher's output sat in a
        // block buffer and its log read 0 bytes through the whole run it was watching. A trace
        // that is only readable after a clean exit is no use for a client that crashes.
        std::fflush(Output);

        Recorded.fetch_add(1, std::memory_order_relaxed);
    }

    __declspec(naked) void dispatchHook()
    {
        __asm
        {
            pushfd
            pushad                  // EAX survives; PUSHAD stores, it does not clobber
            push eax                // the sequence number, __cdecl argument
            call record
            add esp, 4
            popad
            popfd
            jmp [Trampoline]        // the stolen prologue, then back to target + 6
        }
    }
}

namespace CodolGameServer
{
    bool installClientCommandTrace(const EngineBindings &bindings)
    {
        if (!bindings.valid())
            return false;

        // DERIVED FROM THE EXECUTABLE, the same rule diagnosticPath uses and for the same
        // reason: the client's working directory is the game folder and the dedicated's is not,
        // so a relative path works in one process and silently writes nothing in the other.
        std::wstring buffer(MAX_PATH, L'\0');
        const auto size = GetModuleFileNameW(
            nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));

        if (!size)
            return false;

        buffer.resize(size);

        const auto file = std::filesystem::path(buffer).parent_path() /
            L"Ayria" / L"Logs" / L"client-commands.csv";

        std::error_code ignored;
        std::filesystem::create_directories(file.parent_path(), ignored);

        const auto path = file.string();

        {
            const std::lock_guard lock(Gate);

            if (Output)
            {
                std::fclose(Output);
                Output = nullptr;
            }

            // ABSOLUTE PATH, and the caller is responsible for making it one. A diagnostic that
            // wrote to a relative path once produced nothing at all and looked like a hook that
            // never fired -- the client's working directory is not where anybody looks.
            // _fsopen WITH _SH_DENYWR, NOT fopen. The CRT's fopen denies sharing outright:
            // measured, neither PowerShell nor python could open the file while the client
            // held it, so the trace was only readable after the client stopped recording --
            // useless for watching a ten-minute demo go past, and worse than useless if the
            // client crashes, which is one of the things worth tracing.
            Output = _fsopen(path.c_str(), "w", _SH_DENYWR);

            if (!Output)
                return false;

            std::fprintf(Output, "ms,sequence,verb,inner,dispatch,bytes,text\n");
            std::fflush(Output);
            OutputPath = path;
        }

        StartedAt = GetTickCount();
        Recorded.store(0);
        Unreadable.store(0);

        // ALREADY INSTALLED IS NOT AN ERROR. Re-running the diagnostic should start a new file
        // against the hook that is already there, not patch the prologue a second time -- the
        // second patch would copy the JMP as its own "original" and the client would recurse
        // into itself on the next command.
        if (Trampoline)
        {
            Recording.store(true);
            return true;
        }

        ModuleBase = bindings.module();

        auto *target = const_cast<std::uint8_t *>(ModuleBase) + ClientCommandDispatchRva;

        // REFUSE A PROLOGUE THAT IS NOT THE ONE THAT WAS MEASURED. If a build moves this
        // function, patching six bytes of whatever is there now is how a client dies with no
        // explanation. Checking costs one comparison and turns a crash into a log line.
        static constexpr std::uint8_t Expected[StolenBytes] =
            { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08 };

        if (!std::equal(std::begin(Expected), std::end(Expected), target))
        {
            const std::lock_guard lock(Gate);
            std::fprintf(Output,
                         "0,0,?,,REFUSED,0,\"prologue at RVA 0x%zX is not 55 8B EC 83 EC 08 -- "
                         "this build moved sub_614C00; nothing was patched\"\n",
                         ClientCommandDispatchRva);
            std::fflush(Output);
            return false;
        }

        auto *trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr, StolenBytes + 5, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));

        if (!trampoline)
            return false;

        std::copy_n(target, StolenBytes, trampoline);
        trampoline[StolenBytes] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + StolenBytes + 1) =
            static_cast<std::int32_t>(
                (target + StolenBytes) - (trampoline + StolenBytes + 5));

        DWORD oldProtection{};

        if (!VirtualProtect(target, StolenBytes, PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return false;
        }

        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) =
            static_cast<std::int32_t>(
                reinterpret_cast<std::uint8_t *>(&dispatchHook) - (target + 5));
        target[5] = 0x90;                         // the sixth stolen byte, padded

        VirtualProtect(target, StolenBytes, oldProtection, &oldProtection);
        FlushInstructionCache(GetCurrentProcess(), target, StolenBytes);

        Target = target;
        Trampoline = trampoline;
        Recording.store(true);

        return true;
    }

    void stopClientCommandTrace()
    {
        // THE HOOK IS LEFT IN PLACE ON PURPOSE. Unpatching means writing six bytes back into a
        // function another thread may be executing at that instant, for no gain -- the hook
        // costs a predictable branch and a flag test once every few hundred milliseconds. Only
        // the RECORDING stops.
        Recording.store(false);

        const std::lock_guard lock(Gate);

        if (Output)
        {
            std::fflush(Output);
            std::fclose(Output);
            Output = nullptr;
        }
    }

    std::string clientCommandTraceStatus()
    {
        const std::lock_guard lock(Gate);

        if (!Trampoline)
            return "client command trace: not installed";

        return "client command trace: " +
            std::string(Recording.load() ? "RECORDING" : "stopped") + ", " +
            std::to_string(Recorded.load()) + " command(s) written, " +
            std::to_string(Unreadable.load()) + " unreadable, -> " + OutputPath;
    }
}

// ============================================================================================
// THE PLAYERSTATE MIRROR
//
// A READER ON A THREAD, NOT A HOOK. We already run inside out.exe, so the client's decoded
// playerState is simply memory we can read. A trampoline would put our code on the engine's
// own execution path for no gain -- and that path is the one that killed three clients at once
// when it was per-frame. Reading cannot.
// ============================================================================================

namespace
{
    // cgBase = dword_1C1D188[dword_82C3B58] ^ 0xFBB2C97A, and the playerState is at cg + 0.
    //
    // Read straight off sub_613A40's own prologue, which resolves it in three instructions
    // before switching on the verb character:
    //     mov edx, dword_82C3B58
    //     mov esi, dword_1C1D188[edx*4]
    //     xor esi, 0FBB2C97Ah
    // All three globals live in .data, whose virtual size is 229.8 MB against 10.5 MB on disk.
    constexpr std::size_t CgIndexRva = 0x7EC3B58;      // dword_82C3B58
    constexpr std::size_t CgArrayRva = 0x181D188;      // dword_1C1D188
    constexpr std::uint32_t CgKey = 0xFBB2C97A;

    // playerstate-0x00DA8540.tsv: 246 netfields, offsets 0x0 .. 0x3B74. One word past the last.
    constexpr std::size_t PlayerStateBytes = 0x3B78;

    std::atomic<bool> PsRecording{};
    std::atomic<std::uint64_t> PsSamples{};
    std::atomic<std::uint64_t> PsChanges{};
    std::atomic<std::uint64_t> PsUnresolved{};
    std::mutex PsGate;
    FILE *PsOutput{};
    std::string PsPath;
    unsigned PsInterval = 50;

    const std::uint8_t *resolveCg()
    {
        if (!ModuleBase)
            return nullptr;

        const auto *index = reinterpret_cast<const std::uint32_t *>(ModuleBase + CgIndexRva);

        if (!readable(index, sizeof(std::uint32_t)))
            return nullptr;

        const auto *slot = reinterpret_cast<const std::uint32_t *>(
            ModuleBase + CgArrayRva + (static_cast<std::size_t>(*index) * 4));

        if (!readable(slot, sizeof(std::uint32_t)))
            return nullptr;

        const auto obfuscated = *slot;

        // AN UNSET SLOT XORS TO THE KEY ITSELF. Zero ^ key is a 4 GB-ish pointer that VirtualQuery
        // would reject anyway, but saying it here makes the "not in a match yet" case explicit
        // rather than a mystery in the unresolved counter.
        if (!obfuscated)
            return nullptr;

        const auto *cg = reinterpret_cast<const std::uint8_t *>(obfuscated ^ CgKey);

        return readable(cg, PlayerStateBytes) ? cg : nullptr;
    }

    // ---- THE REGIONS WORTH MIRRORING --------------------------------------------------------
    //
    // ps    cg + 0          the 246-field playerState, already 116/120 verified
    // ci    cg + 0x180C50   clientInfo, stride 0x450 -- names, models, ranks. Read off
    //                       CG_DrawCompassBlip: clientInfo = cg + 0x180C50 + 0x450*clientNum
    // clc   the command-ring base, which IS clientConnection: its ring sits at +524628, so its
    //                       header holds the sequence counters. Sampled to find the snapshot
    //                       boundary EMPIRICALLY -- the only callers of the command dispatcher
    //                       are five sites inside one 158 KB function, which is not something to
    //                       hook, and a counter ticking ~20/s is the boundary either way.
    struct Region
    {
        const char *name;
        std::size_t offset;
        std::size_t bytes;
        bool fromCg;
    };

    constexpr Region Regions[] = {
        { "ps",  0x000000, PlayerStateBytes, true  },
        { "ci",  0x180C50, 0x450 * 18,       true  },
        { "clc", 0x000000, 0x400,            false },
    };

    const std::uint8_t *resolveClc()
    {
        if (!ModuleBase)
            return nullptr;

        const auto *p = reinterpret_cast<const std::uint32_t *>(ModuleBase + CommandRingBaseRva);

        if (!readable(p, sizeof(std::uint32_t)) || !*p)
            return nullptr;

        const auto *clc = reinterpret_cast<const std::uint8_t *>(*p ^ CommandRingBaseKey);

        return readable(clc, 0x400) ? clc : nullptr;
    }

    void playerStateThread()
    {
        constexpr std::size_t Count = sizeof(Regions) / sizeof(Regions[0]);
        std::vector<std::uint8_t> previous[Count], current[Count];
        bool seeded[Count]{};

        for (std::size_t r = 0; r < Count; ++r)
            current[r].resize(Regions[r].bytes);

        while (PsRecording.load(std::memory_order_relaxed))
        {
            const auto *cg = resolveCg();
            const auto *clc = resolveClc();

            if (!cg)
            {
                PsUnresolved.fetch_add(1, std::memory_order_relaxed);
                Sleep(PsInterval);
                continue;
            }

            PsSamples.fetch_add(1, std::memory_order_relaxed);

            // commandTime is playerState index 0 at offset 0 -- the field demoq.py prints first
            // on every change. It is the join key: both sides can quote it, and neither has to
            // guess at the other's clock.
            std::uint32_t commandTime{};
            std::memcpy(&commandTime, cg, sizeof(commandTime));

            const std::lock_guard lock(PsGate);

            if (!PsOutput)
                break;

            for (std::size_t r = 0; r < Count; ++r)
            {
                const auto *base = Regions[r].fromCg ? cg + Regions[r].offset : clc;

                if (!base || !readable(base, Regions[r].bytes))
                    continue;

                std::memcpy(current[r].data(), base, Regions[r].bytes);

                if (!seeded[r])
                {
                    previous[r] = current[r];
                    seeded[r] = true;
                    continue;
                }

                for (std::size_t offset = 0; offset + 4 <= Regions[r].bytes; offset += 4)
                {
                    std::uint32_t was{}, now{};
                    std::memcpy(&was, previous[r].data() + offset, 4);
                    std::memcpy(&now, current[r].data() + offset, 4);

                    if (was == now)
                        continue;

                    std::fprintf(PsOutput, "%lu,%u,%s,0x%05zX,%u,%u" "\n",
                                 static_cast<unsigned long>(GetTickCount() - StartedAt),
                                 commandTime, Regions[r].name, offset, was, now);
                    PsChanges.fetch_add(1, std::memory_order_relaxed);
                }

                previous[r] = current[r];
            }

            std::fflush(PsOutput);

            Sleep(PsInterval);
        }
    }
}

namespace CodolGameServer
{
    bool installPlayerStateTrace(const EngineBindings &bindings, const unsigned intervalMs)
    {
        if (!bindings.valid())
            return false;

        ModuleBase = bindings.module();
        PsInterval = intervalMs ? intervalMs : 50;

        std::wstring buffer(MAX_PATH, L'\0');
        const auto size = GetModuleFileNameW(
            nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));

        if (!size)
            return false;

        buffer.resize(size);

        const auto file = std::filesystem::path(buffer).parent_path() /
            L"Ayria" / L"Logs" / L"client-ps.csv";

        std::error_code ignored;
        std::filesystem::create_directories(file.parent_path(), ignored);

        {
            const std::lock_guard lock(PsGate);

            if (PsOutput)
            {
                std::fclose(PsOutput);
                PsOutput = nullptr;
            }

            PsOutput = _fsopen(file.string().c_str(), "w", _SH_DENYWR);

            if (!PsOutput)
                return false;

            std::fprintf(PsOutput, "ms,commandTime,region,offset,was,now\n");
            std::fflush(PsOutput);
            PsPath = file.string();
        }

        if (!StartedAt)
            StartedAt = GetTickCount();

        PsSamples.store(0);
        PsChanges.store(0);
        PsUnresolved.store(0);

        if (PsRecording.exchange(true))
            return true;                      // a thread is already running; it picks up the new file

        std::thread(playerStateThread).detach();

        return true;
    }

    void stopPlayerStateTrace()
    {
        PsRecording.store(false);

        Sleep(120);                           // let the sampler notice before the file closes

        const std::lock_guard lock(PsGate);

        if (PsOutput)
        {
            std::fflush(PsOutput);
            std::fclose(PsOutput);
            PsOutput = nullptr;
        }
    }

    std::string playerStateTraceStatus()
    {
        const std::lock_guard lock(PsGate);

        return "playerstate trace: " +
            std::string(PsRecording.load() ? "RECORDING" : "stopped") + ", " +
            std::to_string(PsSamples.load()) + " sample(s), " +
            std::to_string(PsChanges.load()) + " word change(s), " +
            std::to_string(PsUnresolved.load()) + " sample(s) with no cg (not in a match), -> " +
            PsPath;
    }

    // ---- com_maxfps: what it is set to, and what the client actually reaches ----

    bool startFpsProbe(
        const EngineBindings &bindings,
        const bool set,
        const std::uint32_t value,
        const unsigned sampleMs)
    {
        // All three read off out.exe 1649370; image base 0x400000, so RVA = VA - 0x400000.
        constexpr std::size_t MaxFpsDvarPointerRva = 0x7258770;  // dword_7658770
        constexpr std::size_t FrameCounterRva      = 0x2F3A08C;  // dword_333A08C, ++ per Com_Frame
        constexpr std::size_t ConnectionStateRva   = 0x72446B0;  // dword_76446B0
        constexpr std::size_t DvarIntValueOffset   = 12;

        const auto *base = bindings.module();
        if (!base)
            return false;

        std::thread([base, set, value, sampleMs] {
            const auto readDvar = [base]() -> std::uint32_t * {
                const auto pointer = *reinterpret_cast<const std::uintptr_t *>(
                    base + MaxFpsDvarPointerRva);
                return pointer
                    ? reinterpret_cast<std::uint32_t *>(pointer + DvarIntValueOffset)
                    : nullptr;
            };
            const auto *counter =
                reinterpret_cast<const volatile std::uint32_t *>(base + FrameCounterRva);
            const auto *state =
                reinterpret_cast<const volatile std::uint32_t *>(base + ConnectionStateRva);

            auto *maxfps = readDvar();
            const auto before = maxfps ? *maxfps : 0u;

            // WRITE THE VALUE DIRECTLY RATHER THAN THROUGH Dvar_SetInt, because the question
            // is what the LIMITER does with it, not whether the dvar setter clamps. Zero is
            // inside the registered range either way.
            if (set && maxfps)
                *maxfps = value;

            const auto window = sampleMs ? sampleMs : 3000u;
            const auto startFrames = *counter;
            const auto startTicks = GetTickCount64();
            Sleep(window);
            const auto endFrames = *counter;
            const auto elapsed = GetTickCount64() - startTicks;

            const auto frames = endFrames - startFrames;
            const auto fps = elapsed
                ? (static_cast<double>(frames) * 1000.0 / static_cast<double>(elapsed))
                : 0.0;
            const auto now = maxfps ? *maxfps : 0u;
            const auto minMsec = now ? (1000u / now) : 1u;

            char line[320]{};
            std::snprintf(
                line, sizeof(line),
                "fps-probe com_maxfps before=%u now=%u minMsec=%u | frames=%u over %llu ms "
                "= %.1f fps | connectionState=%u (Com_Frame clamps to 30 when this is "
                "neither 0 nor 10)",
                before, now, minMsec, frames,
                static_cast<unsigned long long>(elapsed), fps,
                static_cast<unsigned>(*state));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }).detach();
        return true;
    }
}
