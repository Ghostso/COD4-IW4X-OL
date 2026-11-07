#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "EngineBindings.hpp"

#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <atomic>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ranges>
#include <set>
#include <string>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
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
        static_assert(offsetof(NativeTraceResult, hitType) == 0x18);
        static_assert(offsetof(NativeTraceResult, modelIndex) == 0x1E);
        static_assert(offsetof(NativeTraceResult, partName) == 0x20);
        static_assert(offsetof(NativeTraceResult, partGroup) == 0x22);
        static_assert(offsetof(NativeTraceResult, allSolid) == 0x24);

        // CODREF(pmove): CODOL PM_playerTrace dispatches the 0x28-byte trace_t
        // through pmoveHandlers[pm->handler].trace. The client image retains
        // only handler 0, so the embedded server temporarily replaces that
        // trace callback while keeping the native PmoveSingle implementation.
        struct ServerPmoveTraceContext
        {
            const EngineBindings *bindings{};
            const SvGlassState *glassState{};
            std::span<const SvCollisionEntity> entities;
            bool failed{};
        };

        thread_local ServerPmoveTraceContext *activeServerPmoveTrace{};
        std::atomic<EngineBindings::Trace> clientPmoveTraceFallback{};
        // OLMOD(pmove-handler-swap-owner): the handler slot is process-global,
        // while the authoritative trace inputs are game-thread local. Serialize
        // the short swap and route incidental foreign-thread calls back to the
        // original client trace. TODO(CODOL): remove this bridge when a genuine
        // CODOL server handler table or an equivalent non-global call boundary
        // is recovered and validated against both client and dedicated use.
        std::atomic_flag serverPmoveHandlerSwap = ATOMIC_FLAG_INIT;

        // sub_5BEB50: `lea eax, [edi+ebx+20h]` / `lea ecx, [edi+ebx+24h]`.
        // sub_411360 / sub_5BEB50 both address it as `[playerState + 0x10]`.
        constexpr std::size_t NativeProtectedPlayerStateValueOffset = 0x010;
        constexpr std::size_t NativePlayerStateSetAccessorOffset = 0x020;
        constexpr std::size_t NativePlayerStateGetAccessorOffset = 0x024;

        struct NativePmoveExceptionDetails
        {
            std::uint32_t code{};
            const void *address{};
            std::uint32_t targetCommandTime{};
            std::uint32_t playerCommandTime{};
            std::uint32_t sliceCommandTime{};
            std::uint32_t sliceIndex{};
            std::uint32_t buttons{};
            std::int32_t pmType{};
            std::uint32_t pmFlags{};
            std::uint32_t pmoveControlFlags{};
            std::uint32_t numTouch{};
            std::uint8_t mantleStarted{};
            std::array<float, 3> mantleEndPosition{};
            std::int32_t mantleDuration{};
            std::int32_t viewChangeTime{};
            // An access violation's INSTRUCTION address says where it died; the
            // faulting DATA address and the access kind say why, and the registers
            // say which pointer carried it there. Only the first was being captured,
            // so 4200 identical lines could not distinguish a null deref from a wild
            // callback.
            std::uint32_t accessType{0xFFFFFFFFu};
            const void *faultAddress{};
            std::uint32_t eax{};
            std::uint32_t ecx{};
            std::uint32_t edx{};
            std::uint32_t esi{};
            std::uint32_t edi{};
            std::uint32_t esp{};
        };

        int captureNativePmoveException(
            EXCEPTION_POINTERS *const exception,
            NativePmoveExceptionDetails *const details) noexcept
        {
            if (exception && exception->ExceptionRecord && details)
            {
                const auto *const record = exception->ExceptionRecord;
                details->code = record->ExceptionCode;
                details->address = record->ExceptionAddress;
                if (record->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
                    record->NumberParameters >= 2)
                {
                    details->accessType = static_cast<std::uint32_t>(
                        record->ExceptionInformation[0]);
                    details->faultAddress = reinterpret_cast<const void *>(
                        record->ExceptionInformation[1]);
                }
#if defined(_M_IX86)
                if (const auto *const context = exception->ContextRecord)
                {
                    details->eax = context->Eax;
                    details->ecx = context->Ecx;
                    details->edx = context->Edx;
                    details->esi = context->Esi;
                    details->edi = context->Edi;
                    details->esp = context->Esp;
                }
#endif
            }
            return EXCEPTION_EXECUTE_HANDLER;
        }

        void logNativePmoveExceptionOnce(
            const NativePmoveExceptionDetails &details)
        {
            struct ExceptionKey
            {
                std::uint32_t code{};
                const void *address{};
                std::uint32_t targetCommandTime{};

                bool operator==(const ExceptionKey &) const = default;
            };

            static thread_local ExceptionKey lastLogged{};
            static thread_local bool hasLogged{};
            const ExceptionKey key{
                .code = details.code,
                .address = details.address,
                .targetCommandTime = details.targetCommandTime,
            };
            if (hasLogged && key == lastLogged)
                return;
            lastLogged = key;
            hasLogged = true;

            const auto imageBase = reinterpret_cast<std::uintptr_t>(
                GetModuleHandleW(nullptr));
            const auto exceptionAddress = reinterpret_cast<std::uintptr_t>(
                details.address);
            const auto imageRva = exceptionAddress >= imageBase
                ? exceptionAddress - imageBase
                : 0;
            char message[1024]{};
            std::snprintf(
                message,
                sizeof(message),
                "native pmove exception code=0x%08lX address=0x%08lX "
                "image_rva=0x%08lX target=%lu player=%lu slice=%lu "
                "slice_index=%lu buttons=0x%08lX pm_type=%ld "
                "pm_flags=0x%08lX control=0x%08lX touches=%lu "
                "mantle_started=%u mantle_end=[%.3f,%.3f,%.3f] "
                "mantle_duration=%ld view_change_time=%ld "
                "access=%lu fault=0x%08lX eax=0x%08lX ecx=0x%08lX edx=0x%08lX "
                "esi=0x%08lX edi=0x%08lX esp=0x%08lX",
                static_cast<unsigned long>(details.code),
                static_cast<unsigned long>(exceptionAddress),
                static_cast<unsigned long>(imageRva),
                static_cast<unsigned long>(details.targetCommandTime),
                static_cast<unsigned long>(details.playerCommandTime),
                static_cast<unsigned long>(details.sliceCommandTime),
                static_cast<unsigned long>(details.sliceIndex),
                static_cast<unsigned long>(details.buttons),
                static_cast<long>(details.pmType),
                static_cast<unsigned long>(details.pmFlags),
                static_cast<unsigned long>(details.pmoveControlFlags),
                static_cast<unsigned long>(details.numTouch),
                static_cast<unsigned int>(details.mantleStarted),
                static_cast<double>(details.mantleEndPosition[0]),
                static_cast<double>(details.mantleEndPosition[1]),
                static_cast<double>(details.mantleEndPosition[2]),
                static_cast<long>(details.mantleDuration),
                static_cast<long>(details.viewChangeTime),
                static_cast<unsigned long>(details.accessType),
                static_cast<unsigned long>(
                    reinterpret_cast<std::uintptr_t>(details.faultAddress)),
                static_cast<unsigned long>(details.eax),
                static_cast<unsigned long>(details.ecx),
                static_cast<unsigned long>(details.edx),
                static_cast<unsigned long>(details.esi),
                static_cast<unsigned long>(details.edi),
                static_cast<unsigned long>(details.esp));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, message);
        }

        static_assert(
            0x96E20 + 64 * 0x3B8 + 0x320 <=
            EngineBindings::ServerAnimConditionStorageSize);

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

        void writeNoHitTrace(void *const result)
        {
            if (!result)
                return;
            NativeTraceResult native{};
            native.fraction = 1.0f;
            native.hitId = 2047;
            std::memcpy(result, &native, sizeof(native));
        }

        // WHAT THE PMOVE'S TRACE ACTUALLY ANSWERS.
        // The server is walking the player upward at almost exactly one unit per pmove
        // call, with groundEntityNum = ENTITYNUM_NONE on every single frame. That is the
        // shape of PM_CorrectAllSolid unsticking a player it believes is inside solid,
        // and only the trace can say whether it is. A no-hit answer would make him FALL,
        // so "the trace is not working" is not one hypothesis but two with opposite
        // signatures -- print the counts and one sample and they separate.
        void reportServerPmoveTrace(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            const NativeTraceResult &native,
            const bool failed)
        {
            static std::uint32_t calls{};
            static std::uint32_t allSolid{};
            static std::uint32_t startSolid{};
            static std::uint32_t hits{};
            static std::uint32_t failures{};
            static std::uint32_t reportedAt{};
            // WHICH WAY DO THE HIT NORMALS POINT. The last CALL is usually a miss and
            // says nothing; what matters is whether a DOWNWARD trace ever comes back
            // with an upward normal, because `walkable` is normal.z >= 0.7 and without
            // one the player can never be standing on anything.
            static std::uint32_t normalUp{};
            static std::uint32_t normalFlat{};
            static std::uint32_t normalDown{};
            static std::uint32_t downwardHits{};
            static std::uint32_t downwardUpNormal{};
            static std::array<float, 3> lastHitStart{};
            static std::array<float, 3> lastHitEnd{};
            static NativeTraceResult lastHit{};
            // A DOWNWARD HIT WITH AN UPWARD NORMAL IS NOT YET GROUND. PM_GroundTrace
            // also needs `walkable`, and it is the ENGINE that sets it -- so count it
            // rather than recompute it, and keep the last DOWNWARD hit separately: the
            // last hit overall is usually an upward trace into a ceiling and says
            // nothing about what the player is standing on.
            static std::uint32_t walkableHits{};
            // THE GROUND PROBE IS ONE SPECIFIC TRACE AND IT IS THE ONLY ONE THAT MATTERS
            // HERE. PM_GroundTrace drops straight down a couple of units from the origin;
            // everything else in a pmove is slide moves and the 64-unit airborne check.
            // The player is standing still with zero velocity when the pmove decides he
            // has no ground, so what that one trace answers IS the defect.
            static std::uint32_t groundProbes{};
            static std::uint32_t groundProbeHits{};
            static std::uint32_t groundProbeWalkable{};
            static std::uint32_t groundProbeStartSolid{};
            static std::array<float, 3> lastProbeStart{};
            static std::array<float, 3> lastProbeEnd{};
            static NativeTraceResult lastProbe{};
            static std::array<float, 3> lastDownStart{};
            static std::array<float, 3> lastDownEnd{};
            static NativeTraceResult lastDown{};
            static TraceBounds lastDownBounds{};
            ++calls;
            const auto drop = start[2] - end[2];
            if (drop > 0.0f && drop <= 2.0f && start[0] == end[0] &&
                start[1] == end[1])
            {
                ++groundProbes;
                lastProbeStart = start;
                lastProbeEnd = end;
                lastProbe = native;
                if (native.fraction < 1.0f)
                    ++groundProbeHits;
                if (native.walkable)
                    ++groundProbeWalkable;
                if (native.startSolid)
                    ++groundProbeStartSolid;
            }
            if (failed)
                ++failures;
            if (native.allSolid)
                ++allSolid;
            if (native.startSolid)
                ++startSolid;
            if (native.fraction < 1.0f)
            {
                ++hits;
                lastHitStart = start;
                lastHitEnd = end;
                lastHit = native;
                if (native.normal[2] >= 0.7f)
                    ++normalUp;
                else if (native.normal[2] > -0.7f)
                    ++normalFlat;
                else
                    ++normalDown;
                if (native.walkable)
                    ++walkableHits;
                if (end[2] < start[2])
                {
                    ++downwardHits;
                    lastDownStart = start;
                    lastDownEnd = end;
                    lastDown = native;
                    lastDownBounds = bounds;
                    if (native.normal[2] >= 0.7f)
                        ++downwardUpNormal;
                }
            }
            // Once every 600 calls was a probe; the answer it produced is now a
            // standing question -- can a downward trace still find an upward normal --
            // so report far less often and let the counters carry it.
            if (calls - reportedAt < 6000)
                return;
            reportedAt = calls;
            char line[448]{};
            std::snprintf(
                line, sizeof(line),
                "pmove-trace calls=%u hits=%u allSolid=%u startSolid=%u failed=%u "
                "normalZ up=%u flat=%u down=%u downwardHits=%u withUpNormal=%u "
                "walkable=%u probes=%u probeHits=%u probeWalkable=%u "
                "probeStartSolid=%u lastProbe{%.2f,%.2f,%.2f -> %.2f frac=%.4f "
                "walkable=%u startSolid=%u allSolid=%u hitId=%u normal=%.3f,%.3f,%.3f} "
                "lastDown{%.1f,%.1f,%.1f -> %.1f,%.1f,%.1f "
                "half=%.1f,%.1f,%.1f mid=%.1f,%.1f,%.1f frac=%.4f walkable=%u "
                "startSolid=%u hitId=%u contents=0x%08X normal=%.3f,%.3f,%.3f}",
                calls, hits, allSolid, startSolid, failures,
                normalUp, normalFlat, normalDown, downwardHits, downwardUpNormal,
                walkableHits,
                groundProbes, groundProbeHits, groundProbeWalkable,
                groundProbeStartSolid,
                lastProbeStart[0], lastProbeStart[1], lastProbeStart[2],
                lastProbeEnd[2], lastProbe.fraction,
                static_cast<unsigned>(lastProbe.walkable),
                static_cast<unsigned>(lastProbe.startSolid),
                static_cast<unsigned>(lastProbe.allSolid),
                static_cast<unsigned>(lastProbe.hitId),
                lastProbe.normal[0], lastProbe.normal[1], lastProbe.normal[2],
                lastDownStart[0], lastDownStart[1], lastDownStart[2],
                lastDownEnd[0], lastDownEnd[1], lastDownEnd[2],
                lastDownBounds.halfSize[0], lastDownBounds.halfSize[1],
                lastDownBounds.halfSize[2],
                lastDownBounds.midpoint[0], lastDownBounds.midpoint[1],
                lastDownBounds.midpoint[2],
                lastDown.fraction,
                static_cast<unsigned>(lastDown.walkable),
                static_cast<unsigned>(lastDown.startSolid),
                static_cast<unsigned>(lastDown.hitId), lastDown.contents,
                lastDown.normal[0], lastDown.normal[1], lastDown.normal[2]);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }

        void __cdecl SV_ServerPmoveTrace(
            void *const result,
            const float *const start,
            const float *const end,
            const TraceBounds *const bounds,
            const std::int32_t passEntityNum,
            const std::uint32_t contentMask) noexcept
        {
            auto *const context = activeServerPmoveTrace;
            if (!context)
            {
                const auto fallback = clientPmoveTraceFallback.load(
                    std::memory_order_acquire);
                if (fallback)
                    fallback(result, start, end, bounds, passEntityNum, contentMask);
                else
                    writeNoHitTrace(result);
                return;
            }

            try
            {
                if (!result || !start || !end || !bounds || !context->bindings ||
                    !context->glassState)
                {
                    context->failed = true;
                    writeNoHitTrace(result);
                    return;
                }

                SvTraceEntityFilter filter;
                if (passEntityNum >= 0 &&
                    passEntityNum <=
                        static_cast<std::int32_t>(MaximumServerCollisionEntityNum))
                {
                    filter.passEntityNum = static_cast<std::uint32_t>(passEntityNum);
                    const auto entity = std::ranges::find(
                        context->entities,
                        static_cast<std::uint32_t>(passEntityNum),
                        &SvCollisionEntity::entityNum);
                    if (entity != context->entities.end())
                        filter.passOwnerEntityNum = entity->ownerEntityNum;
                }
                else if (passEntityNum != -1 && passEntityNum != 2047)
                {
                    context->failed = true;
                    writeNoHitTrace(result);
                    return;
                }

                const std::array<float, 3> traceStart{ start[0], start[1], start[2] };
                const std::array<float, 3> traceEnd{ end[0], end[1], end[2] };
                const auto trace = context->bindings->traceServerCapsule(
                    traceStart,
                    traceEnd,
                    *bounds,
                    contentMask,
                    *context->glassState,
                    context->entities,
                    filter);
                if (!trace)
                {
                    context->failed = true;
                    writeNoHitTrace(result);
                    return;
                }
                const auto native = encodeTraceResult(*trace);
                reportServerPmoveTrace(
                    traceStart, traceEnd, *bounds, native, false);
                std::memcpy(result, &native, sizeof(native));
            }
            catch (...)
            {
                context->failed = true;
                writeNoHitTrace(result);
            }
        }

        class ScopedServerPmoveContext final
        {
        public:
            explicit ScopedServerPmoveContext(ServerPmoveTraceContext &context)
                : previous_(activeServerPmoveTrace)
            {
                activeServerPmoveTrace = &context;
            }

            ~ScopedServerPmoveContext()
            {
                activeServerPmoveTrace = previous_;
            }

            ScopedServerPmoveContext(const ScopedServerPmoveContext &) = delete;
            ScopedServerPmoveContext &operator=(
                const ScopedServerPmoveContext &) = delete;

        private:
            ServerPmoveTraceContext *previous_;
        };

        class ScopedAtomicFlag final
        {
        public:
            explicit ScopedAtomicFlag(std::atomic_flag &flag) : flag_(flag) {}
            ~ScopedAtomicFlag()
            {
                flag_.clear(std::memory_order_release);
            }

            ScopedAtomicFlag(const ScopedAtomicFlag &) = delete;
            ScopedAtomicFlag &operator=(const ScopedAtomicFlag &) = delete;

        private:
            std::atomic_flag &flag_;
        };

        // OLMOD(bullet-fire-probe): section 75. BIT 0 IS FIRE.
        //
        // Measured live on 3.3.3.3 by edge-triggered logging of decoded usercmds
        // against a scripted key sequence, and two entries of that same table
        // reproduce on OLfinal independently -- crouch 0x00000200 in section 45j's
        // per-frame stance trace, and jump 0x00000400 in the run a person drove on
        // 2026-08-20. Two corroborated bits is why this one is carried across rather
        // than guessed at.
        inline constexpr std::uint32_t UserCmdButtonFire = 0x00000001;
        // OLMOD(section-79f): TWELVE FRAMES WAS ABOUT 240 ms AND PROVED NOTHING.
        // The bit reached the native pmove -- the stance trace on the same slices
        // reports cmdIn=0x00000001 cmdOut=0x00000001 -- with wState=0, which is
        // WEAPON_READY, and the weapon state machine did not move.
        //
        // OLMOD(section-85): AND `cmdOut` IS NOT A DIFFERENT COPY. It is
        // `pmove.cmd.buttons` read AFTER invokeNativeServerPmove returns, and the
        // adapter's own two gates mutate that field in place -- so cmdOut=1 means
        // the bit survived both of them and was live in the pmove_t at the moment
        // PmoveSingle was called. Section 80a's conclusion that this writes "a copy
        // PM_Weapon does not read" does not survive the layout: pmove.cmd is at
        // pmove+4 and buttons at +4 of that, static_asserted in
        // sv_native_pmove_mp.hpp, which is exactly where the engine looks. What was
        // missing was never the write; it was any way to see WHICH gate refused,
        // and the probe prints all four of them now.
        inline constexpr std::uint32_t BulletFireProbeFrames = 120;
        // The same offsets the pmove adapter below uses, hoisted so the probe can
        // read them without reaching into a function scope.
        inline constexpr std::size_t ProbePmTypeOffset = 0x004;
        inline constexpr std::size_t ProbeHealthOffset = 0x20C;
        // OLMOD(section-79f): AND PRINT WHAT IT IS INJECTING INTO. A probe that
        // reports only the button it set cannot distinguish "the engine ignored it"
        // from "the weapon was busy" -- and the nearest other reader,
        // player-kinematics, is a DIFFERENT COPY at a different stage, so comparing
        // the two lines produces a false answer rather than no answer.
        inline constexpr std::size_t ProbeWeaponTimeOffset = 0x2C0;
        inline constexpr std::size_t ProbeWeaponDelayOffset = 0x2C4;
        inline constexpr std::size_t ProbeWeaponStateOffset = 0x2CC;
        inline constexpr std::size_t ProbeCurrentWeaponOffset = 0x3F8;
        // OLMOD(section-85): AND THE FOUR THINGS PM_Weapon ACTUALLY ASKS BEFORE IT
        // WILL THINK AT ALL, read off out.exe rather than guessed.
        //
        // PmoveSingle calls PM_Weapon = sub_42B4E0 unconditionally at 0x0041D263.
        // PM_Weapon's FIRST act is `sub_42AED0(ps)`; a non-zero return takes the
        // long weapon-think branch at 0x0042B597 and a zero return takes a short
        // one that cannot fire. sub_42AED0 is small enough to read whole:
        //
        //   cmp dword [ps+04h], 8       ; pm_type >= 8 -> also zeroes ps+3F8h
        //   jl  ...                     ;                 and returns 0
        //   test dword [ps+0Ch], 400h   ; pm_flags  -> returns 0
        //   test dword [ps+104h], 0C00h ; eFlags    -> returns 0
        //   <obfuscated read of the PROTECTED value at ps+10h>
        //   shr eax, 1Eh / and al, 1    ; BIT 30 of the second dword
        //   test dl, dl / sete al       ; return !bit30
        //
        // So the weapon thinks only when pm_type < 8, pm_flags & 0x400 is clear,
        // eFlags & 0xC00 is clear, AND BIT 30 OF THE PROTECTED SECOND DWORD IS
        // CLEAR -- the same dword section 76a found the stance gate's bit 22 and
        // bit 24 in, and the same dword THIS SERVER fills with otherFlags. A probe
        // that does not print these four cannot tell "the engine ignored the
        // button" from "this server set a bit that switched the weapon off", which
        // is exactly the state section 80a left it in.
        // OLMOD(section-86): AND THE PROBE MUST RELEASE THE TRIGGER BEFORE IT
        // PULLS IT. The gate that actually refused was `pm_flags & 0x400`, on
        // every frame of every window, and PmoveSingle clears that bit in
        // exactly ONE place -- 0x0041CEA6 on out.exe, 0x0041DDBB on 3.3.3.3,
        // identical logic:
        //
        //     cmp dword [ps+04h], 8            pm_type < 8
        //     jge  skip
        //     test dword [pmove+8], 101h       cmd.buttons & 0x101
        //     jne  skip
        //     and dword [ps+0Ch], 0FFFFFBFFh   clear PMF_RESPAWNED
        //
        // `pmove+8` is cmd.buttons. So the respawn latch clears only on a frame
        // where NEITHER bit 0 (fire) NOR bit 8 is held -- and this probe held
        // bit 0 from its very first frame, so the latch never cleared and
        // PM_Weapon refused for the whole window. A person releases the trigger
        // between magazines without thinking about it, which is why their fire
        // worked and 120 injected frames did not.
        inline constexpr std::uint32_t BulletFireProbeReleaseFrames = 12;
        inline constexpr std::size_t ProbePmFlagsOffset = 0x00C;
        inline constexpr std::size_t ProbeEFlagsOffset = 0x104;
        inline constexpr std::uint32_t ProbePmFlagsWeaponGate = 0x00000400;
        inline constexpr std::uint32_t ProbeEFlagsWeaponGate = 0x00000C00;
        inline constexpr std::uint32_t ProbeProtectedWeaponGateBit = 30;
        inline constexpr std::int32_t ProbePmTypeWeaponLimit = 8;

        bool bulletFireProbeEnabled()
        {
            static const bool enabled = [] {
                std::array<char, 8> value{};
                const auto size = GetEnvironmentVariableA(
                    "OLMOD_BULLET_FIRE_PROBE",
                    value.data(),
                    static_cast<DWORD>(value.size()));
                return size == 1 && value[0] == '1';
            }();
            return enabled;
        }

        std::int32_t readNativeInt(
            const std::byte *const playerState,
            const std::size_t offset)
        {
            std::int32_t value{};
            std::memcpy(&value, playerState + offset, sizeof(value));
            return value;
        }

        void writeNativeInt(
            std::byte *const playerState,
            const std::size_t offset,
            const std::int32_t value)
        {
            std::memcpy(playerState + offset, &value, sizeof(value));
        }

        void callPMSetPitchValues(
            void *const function,
            std::byte *const playerState,
            SvNativePmove *const pmove)
        {
            // CODDIFF(1649370): THE PLAYERSTATE ARRIVES IN ECX ON THIS BUILD, NOT EAX.
            // out.exe's PM_SetPitchValues (sub_41DB40, RVA 0x01DB40) is __usercall and IDA
            // types it `__cdecl sub_41DB40(int a1)` with a ecx variable that is never
            // assigned -- the giveaway for an incoming register argument. The body uses it
            // as the playerState and nothing else:
            //     ((void (__cdecl *)(_DWORD *, _BYTE *))(
            //         dword_E60B78 ^ v1[9] ^ (unsigned int)(v1 + 8)))(v1 + 4, v22);
            // i.e. the accessor pair at +0x24/+0x20 decoded against base +0x10 -- the same
            // pair PmoveSingle uses. The stack argument is the pmove, used for +288/+292.
            //
            // Passing it in eax left ecx holding whatever the caller had, which the log
            // caught as `ecx=0x00000010` and a read fault at 0x34 -- exactly [ecx+0x10+0x14].
            __asm
            {
                push pmove
                mov ecx, playerState
                call function
                add esp, 4
            }
        }

        SvNativePmoveFailure invokeNativeServerPmove(
            void *const pmoveSingle,
            void *const pmSetPitchValues,
            EngineBindings::Trace *const handlerSlot,
            const EngineBindings::Trace expectedTrace,
            SvNativePmove *const pmove,
            const bool finalSlice)
        {
            // CODREF(pmove): this is the server-owned prefix of CODOL Pmove
            // 0x0041E860: command gating, 1000 ms backlog clamp, <=66 ms
            // PmoveSingle slices, oldcmd carry-forward, and PM_SetPitchValues.
            // Ghosts Pmove 0x140082BE0 confirms the same server responsibility.
            // CODDIFF(pmove): CODOL's retained function then writes two fields
            // in a client-only object and cannot be called as a server handler;
            // this adapter deliberately stops after PM_SetPitchValues.
            static_assert(sizeof(EngineBindings::Trace) == sizeof(LONG));
            constexpr std::size_t CommandTimeOffset = 0x000;
            constexpr std::size_t PmTypeOffset = 0x004;
            constexpr std::size_t PmFlagsOffset = 0x00C;
            // CODDIFF(1649370): 0x014 -> 0x028. OLfinal inserts 20 bytes into
            // playerState between +0x10 and this field: the netfield tables pair
            // them on (3 bits, same codec) at A 0x014 / C 0x028, and both
            // neighbours corroborate it independently -- the field above is
            // otherFlags, which changed codec in place at +0x10, and the field
            // below is bobCycle, which section 34 had already moved 0x018 ->
            // 0x02C from the other direction.
            constexpr std::size_t PmoveControlFlagsOffset = 0x028;
            constexpr std::int32_t MaximumBacklog = 1000;
            constexpr std::int32_t MaximumSlice = 66;
            constexpr std::uint32_t MaximumSlices = 16;

            if (!pmoveSingle || !pmSetPitchValues || !handlerSlot ||
                !expectedTrace || !pmove || !pmove->playerState)
            {
                return SvNativePmoveFailure::InvalidBinding;
            }

            const auto expectedBits = static_cast<LONG>(
                reinterpret_cast<std::uintptr_t>(expectedTrace));
            const auto callbackBits = static_cast<LONG>(
                reinterpret_cast<std::uintptr_t>(&SV_ServerPmoveTrace));
            auto *const slot = reinterpret_cast<volatile LONG *>(handlerSlot);
            if (InterlockedCompareExchange(slot, callbackBits, expectedBits) !=
                expectedBits)
            {
                return SvNativePmoveFailure::HandlerSlotBusy;
            }

            bool completed{};
            bool traceRestored{};
            auto failure = SvNativePmoveFailure::None;
            NativePmoveExceptionDetails exceptionDetails{
                .targetCommandTime = pmove->cmd.commandTime,
                .playerCommandTime = static_cast<std::uint32_t>(readNativeInt(
                    pmove->playerState, CommandTimeOffset)),
                .buttons = pmove->cmd.buttons,
                .pmType = readNativeInt(pmove->playerState, PmTypeOffset),
                .pmFlags = static_cast<std::uint32_t>(readNativeInt(
                    pmove->playerState, PmFlagsOffset)),
                .pmoveControlFlags = static_cast<std::uint32_t>(readNativeInt(
                    pmove->playerState, PmoveControlFlagsOffset)),
            };
            __try
            {
                __try
                {
                    const auto pmFlags = readNativeInt(
                        pmove->playerState, PmFlagsOffset);
                    if ((pmFlags & 0x80000) != 0 ||
                        (pmove->cmd.buttons & 0x200000) != 0)
                    {
                        pmove->cmd.buttons &= 0x80300;
                        pmove->cmd.forwardMove = 0;
                        pmove->cmd.rightMove = 0;
                    }
                    if ((readNativeInt(
                            pmove->playerState, PmoveControlFlagsOffset) & 4) != 0)
                    {
                        pmove->cmd.buttons &= 0xFFFFFBF9;
                        pmove->cmd.forwardMove = 0;
                        pmove->cmd.rightMove = 0;
                    }

                    const auto targetCommandTime = static_cast<std::int32_t>(
                        pmove->cmd.commandTime);
                    auto commandTime = readNativeInt(
                        pmove->playerState, CommandTimeOffset);
                    if (targetCommandTime < commandTime)
                    {
                        failure = SvNativePmoveFailure::
                            NonIncreasingCommandTime;
                        __leave;
                    }
                    if (static_cast<std::int64_t>(targetCommandTime) >
                        static_cast<std::int64_t>(commandTime) + MaximumBacklog)
                    {
                        commandTime = targetCommandTime - MaximumBacklog;
                        writeNativeInt(
                            pmove->playerState,
                            CommandTimeOffset,
                            commandTime);
                    }

                    pmove->numTouch = 0;
                    std::uint32_t sliceCount{};
                    while (commandTime != targetCommandTime)
                    {
                        // OLMOD(pmove-slice-bound): after the native 1000 ms
                        // clamp, ceil(1000 / 66) is 16. The explicit guard only
                        // fails a corrupted/non-advancing reconstruction; it
                        // does not reduce the CODOL driver's valid domain.
                        if (++sliceCount > MaximumSlices)
                        {
                            failure = SvNativePmoveFailure::SliceLimitExceeded;
                            __leave;
                        }
                        auto delta = targetCommandTime - commandTime;
                        if (delta > MaximumSlice)
                            delta = MaximumSlice;
                        const auto sliceCommandTime = commandTime + delta;
                        exceptionDetails.playerCommandTime =
                            static_cast<std::uint32_t>(commandTime);
                        exceptionDetails.sliceCommandTime =
                            static_cast<std::uint32_t>(sliceCommandTime);
                        exceptionDetails.sliceIndex = sliceCount;
                        exceptionDetails.buttons = pmove->cmd.buttons;
                        pmove->cmd.commandTime = static_cast<std::uint32_t>(
                            sliceCommandTime);
                        reinterpret_cast<void (__cdecl *)(SvNativePmove *, int)>(
                            pmoveSingle)(
                            pmove,
                            finalSlice && sliceCommandTime >= targetCommandTime);
                        commandTime = readNativeInt(
                            pmove->playerState, CommandTimeOffset);
                        if (commandTime != sliceCommandTime)
                        {
                            failure = SvNativePmoveFailure::
                                CommandTimeNotAdvanced;
                            __leave;
                        }
                        pmove->oldcmd = pmove->cmd;
                    }
                    if (commandTime != targetCommandTime)
                    {
                        failure = SvNativePmoveFailure::
                            CommandTimeNotAdvanced;
                        __leave;
                    }
                    callPMSetPitchValues(
                        pmSetPitchValues,
                        pmove->playerState,
                        pmove);
                    completed = true;
                }
                __finally
                {
                    MemoryBarrier();
                    traceRestored = InterlockedCompareExchange(
                        slot, expectedBits, callbackBits) == callbackBits;
                }
            }
            __except (captureNativePmoveException(
                GetExceptionInformation(), &exceptionDetails))
            {
                completed = false;
                failure = SvNativePmoveFailure::NativeException;
                exceptionDetails.numTouch = pmove->numTouch >= 0
                    ? static_cast<std::uint32_t>(pmove->numTouch)
                    : 0;
                exceptionDetails.mantleStarted = pmove->mantleStarted;
                exceptionDetails.mantleEndPosition = pmove->mantleEndPosition;
                exceptionDetails.mantleDuration = pmove->mantleDuration;
                exceptionDetails.viewChangeTime = pmove->viewChangeTime;
                logNativePmoveExceptionOnce(exceptionDetails);
            }
            if (!traceRestored)
                return SvNativePmoveFailure::HandlerRestoreFailed;
            if (!completed && failure == SvNativePmoveFailure::None)
                return SvNativePmoveFailure::CommandTimeNotAdvanced;
            return completed ? SvNativePmoveFailure::None : failure;
        }

        // INITIALIZE THE PLAYERSTATE'S OWN ACCESSOR PAIR. This is the same encoder and the
        // same register/stack convention as the characterInfo lerp frames -- eax and the
        // third push are the SET slot, edi and the second push are the GET slot, edx is the
        // get key and the first push is the set key -- but the slots live in the
        // playerState and are keyed on two different cookies. Read straight off the
        // engine's own initializer, sub_5BEB50.
        //
        // Only the pair is written. sub_5BEB50 goes on to call the set accessor with a
        // protected value that lives in a SEPARATE obfuscated buffer, not at frame+0x24 the
        // way a characterInfo lerp frame does, and that buffer is not modelled here yet --
        // so do the part that is understood and leave the part that is not.
        bool invokeNativePlayerStateAccessorInitialize(
            void *const function,
            std::byte *const playerState,
            const std::uint32_t selector,
            const std::uint32_t setKey,
            const std::uint32_t getKey) noexcept
        {
            if (!function || !playerState ||
                selector >= SvNativeLerpFrameSelectorCount)
            {
                return false;
            }
            auto *const encodedSet =
                playerState + NativePlayerStateSetAccessorOffset;
            auto *const encodedGet =
                playerState + NativePlayerStateGetAccessorOffset;
            bool completed{};
            __try
            {
                __asm
                {
                    push edi
                    push setKey
                    push encodedSet
                    push encodedGet
                    push selector
                    mov eax, encodedSet
                    mov edx, getKey
                    mov edi, encodedGet
                    mov ecx, function
                    call ecx
                    add esp, 16
                    pop edi
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        bool validNativeCommand(const UserCmd &command)
        {
            return std::isfinite(command.conditionalAngle) &&
                command.weapon <= EngineBindings::MaximumWeaponAssetIndex &&
                command.offHandIndex <= EngineBindings::MaximumWeaponAssetIndex &&
                command.lastWeaponAltModeSwitch <=
                    EngineBindings::MaximumWeaponAssetIndex &&
                command.conditionalElevenBits <= 0x7FF;
        }

        std::optional<std::int32_t> invokeNativeAnimScriptEvent(
            void *const function,
            SvNativePlayerState &playerState,
            const std::int32_t event,
            const std::int32_t isContinue,
            const std::int32_t force,
            std::uint32_t &randomSeed) noexcept
        {
            if (!function)
                return std::nullopt;
            auto *const nativeState = playerState.bytes.data();
            auto *const seed = &randomSeed;
            std::int32_t result{};
            bool completed{};
            __try
            {
                // THE PLAYERSTATE IS IN EDI ON THIS BUILD, NOT EAX. sub_407E10's very
                // first use of a register it never wrote is `mov ecx, [edi+158h]` --
                // ps+0x158 is ClientNumOffset here -- and it turns that into
                // `dword_827F730 + 0x450*clientNum + 0xAF350`, the characterInfo entry,
                // which it hands to sub_407790 to resolve the anim. EAX is dead on
                // entry: 0x407E26 `lea eax, [ebp+var_4]` overwrites it before any read.
                //
                // So the 3.3.3.3 convention this was carried from (EAX = playerState,
                // 0x004096D0) left EDI holding whatever the compiler last put there.
                // The read does not fault reliably -- it lands wherever EDI points, and
                // __except swallows it when it does -- so the symptom is a spawn
                // animation that silently does not happen, or happens off the WRONG
                // client's characterInfo, differently on every run.
                //
                // ESI is a real input too and was already correct: 0x407E1C
                // `imul ecx, 204h` scales it by AnimScriptItemsStride to index the
                // script-event array at animScriptData + 0x25F80.
                __asm
                {
                    push seed
                    push force
                    push isContinue
                    mov esi, event
                    mov edi, nativeState
                    mov edx, function
                    call edx
                    add esp, 0Ch
                    mov result, eax
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed ? std::optional{ result } : std::nullopt;
        }
    }

    namespace
    {
        // Called from writeNativeProtectedPlayerStateFlags, which is __try/__except and
        // therefore cannot hold a std::string of its own.
        // WHAT THE ENGINE KEEPS IN THE PROTECTED FLAGS WORD, whenever it changes.
        // Crouch and prone are TOGGLES on this build and the engine edge-detects them
        // against held state in this word, so watching it change is how its bit layout
        // gets named. Deduped on the value, so a stationary player is silent.
        void reportProtectedFlagsChange(
            const std::uint32_t flags,
            const bool decoded)
        {
            // DEDUPE ON THE PAIR, NOT THE VALUE. A getter that starts failing while the
            // value happens to be unchanged is exactly the transition worth seeing, and
            // deduping on the value alone would swallow it.
            static std::uint32_t reported{ 0xFFFFFFFFu };
            static int reportedDecoded{ -1 };
            if (flags == reported && static_cast<int>(decoded) == reportedDecoded)
                return;
            reported = flags;
            reportedDecoded = static_cast<int>(decoded);
            char line[128]{};
            std::snprintf(
                line, sizeof(line),
                "protected flags now 0x%08X decoded=%u%s", flags,
                decoded ? 1u : 0u,
                decoded ? "" : "  (GETTER FAILED -- this is OUR fallback, not the"
                               " engine's word; nothing may be concluded from it)");
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, line);
        }

        void reportProtectedFlagsWrite(
            const std::uint32_t flags,
            const std::array<std::uint32_t, 3> &before,
            const std::array<std::uint32_t, 3> &after,
            const std::uint32_t pairLow,
            const std::uint32_t pairHigh,
            const bool completed)
        {
            // SILENT UNLESS THE WRITE ITSELF FAILED. The old condition here -- "the
            // value is neither 0 nor 1u<<12" -- was only correct while ol-mod owned the
            // whole word. It does not any more: the engine keeps its own state in it
            // (stance and toggle bits at least), so any value is legitimate. What is
            // still never legitimate is the setter not completing.
            if (completed)
                return;
            static std::string reported;
            char line[224]{};
            std::snprintf(
                line, sizeof(line),
                "protected flags NOT PLAINTEXT in=0x%08X test1800=%u pre=%08X,%08X,%08X "
                "post=%08X,%08X,%08X pair=%08X,%08X ok=%u",
                flags, (flags & 0x1800u) ? 1u : 0u,
                before[0], before[1], before[2],
                after[0], after[1], after[2],
                pairLow, pairHigh, completed ? 1u : 0u);
            if (reported != line)
            {
                reported = line;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
    }

    bool EngineBindings::writeNativeProtectedPlayerStateFlags(
        SvNativePlayerState &state,
        std::uint32_t &plaintextFlags) const
    {
        // playerState +0x10 IS NOT A PLAIN DWORD ON THIS BUILD.
        //
        // ol-mod stores otherFlags there as a plaintext uint32, and nothing in this tree
        // maps 0x14, 0x18, 0x1C, 0x20 or 0x24 at all. That gap is the shape of the answer:
        // ps+0x10 is a THREE-DWORD PROTECTED VALUE whose accessor pair lives at
        // ps+0x20/+0x24, and the engine only ever reads it through the getter.
        //
        // BG_PlayerStateToEntityState, sub_411360 at 0x0041143E:
        //     lea  eax, [esi+10h]        ; the protected object
        //     lea  ecx, [eax+10h]        ; ps+0x20, the paired ADDRESS
        //     xor  ecx, [eax+14h]        ; ^ the stored dword at ps+0x24
        //     xor  ecx, ds:0x00E60B78    ; ^ the get key
        //     push edx / push eax / call ecx
        //     mov  eax, [ebp-0Ch]        ; the SECOND dword of the plaintext
        //     test eax, 1800h            ; bits 11 and 12
        //     sete al / lea eax, [eax*4+1]
        //     mov  [edi+4], eax          ; eType = 1 (ET_PLAYER) or 5 (ET_INVISIBLE)
        //
        // So a server that writes the flags plaintext gets them decoded into noise, the
        // 0x1800 test fails, and every player is published as ET_INVISIBLE. That is
        // exactly what the live log said: `converted state mismatch eType converted=5
        // playerState=1`, and 5 is ET_INVISIBLE in this build's own etype dispatch table.
        //
        // The set side is read from the engine's own playerState initializer sub_5BEB50,
        // which loops at the 0x3BBC playerState stride, at 0x005BEEC3:
        //     lea  eax, [eax+ebx+10h]    ; the same object
        //     lea  edi, [eax+14h]        ; ps+0x24, the paired ADDRESS
        //     xor  edi, [eax+10h]        ; ^ the stored dword at ps+0x20
        //     xor  edi, ds:0x00E60B74    ; ^ the SET key -- the other cookie
        //     push ecx / push edx / call edi / add esp, 8   ; set(value, object), cdecl
        // Note the two sides are MIRRORED: the getter is keyed on ps+0x20 and stores at
        // ps+0x24, the setter is keyed on ps+0x24 and stores at ps+0x20.
        //
        // Take whatever ol-mod already wrote plaintext and say it the way the engine
        // reads it. The flags are the SECOND dword; the other two have no established
        // owner yet, and zero is what the buffer already held.
        if (!nativePlayerStateAccessorSetKey_)
            return false;
        auto *const bytes = state.bytes.data();
        auto *const object = bytes + NativeProtectedPlayerStateValueOffset;
        std::uint32_t storedSet{};
        std::memcpy(&storedSet, object + 0x10, sizeof(storedSet));
        const auto pairedAddress = static_cast<std::uint32_t>(
            reinterpret_cast<std::uintptr_t>(object + 0x14));
        auto *const setFunction = reinterpret_cast<void *>(
            storedSet ^ pairedAddress ^ *nativePlayerStateAccessorSetKey_);
        std::uint32_t flags{};
        std::memcpy(&flags, object, sizeof(flags));
        // The engine is about to overwrite this dword with its encoded form. Hand the
        // plaintext back so the caller can restore ol-mod's model after the call --
        // without that, the server reads its own otherFlags as noise and, worse, feeds
        // that noise back in as the flags to protect on the very next frame.
        plaintextFlags = flags;
        std::array<std::uint32_t, 3> value{ 0, flags, 0 };
        auto *const valueBytes = value.data();
        std::array<std::uint32_t, 3> before{};
        std::memcpy(before.data(), object, sizeof(before));
        bool completed{};
        __try
        {
            __asm
            {
                mov eax, object
                push eax
                mov ecx, valueBytes
                push ecx
                mov edx, setFunction
                call edx
                add esp, 8
            }
            completed = true;
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            completed = false;
        }
        std::array<std::uint32_t, 3> after{};
        std::memcpy(after.data(), object, sizeof(after));
        std::uint32_t pairLow{};
        std::uint32_t pairHigh{};
        std::memcpy(&pairLow, object + 0x10, sizeof(pairLow));
        std::memcpy(&pairHigh, object + 0x14, sizeof(pairHigh));
        reportProtectedFlagsWrite(
            flags, before, after, pairLow, pairHigh, completed);
        return completed;
    }

    bool EngineBindings::readNativeProtectedPlayerStateFlags(
        const SvNativePlayerState &state,
        std::uint32_t &flags) const
    {
        // THE GETTER, WHICH SECTION 44d DELIBERATELY LEFT UNMODELLED. Its ABI is read
        // straight off PmoveSingle at 0x0041CBCE, where the engine does exactly this:
        //     v4 = dword_E60B78 ^ (unsigned)(ps + 0x20) ^ *(ps + 0x24);
        //     v4(ps + 0x10, out);        // __cdecl(object, outBuffer), caller cleans 8
        // Note the get and set sides take their arguments in OPPOSITE orders -- get is
        // (object, out) and set is (value, object) -- which is of a piece with the pair
        // itself being mirrored (section 43j).
        if (!nativePlayerStateAccessorGetKey_)
            return false;
        auto *const bytes = const_cast<std::byte *>(state.bytes.data());
        auto *const object = bytes + NativeProtectedPlayerStateValueOffset;
        std::uint32_t storedGet{};
        std::memcpy(&storedGet, object + 0x14, sizeof(storedGet));
        const auto pairedAddress = static_cast<std::uint32_t>(
            reinterpret_cast<std::uintptr_t>(object + 0x10));
        auto *const getFunction = reinterpret_cast<void *>(
            storedGet ^ pairedAddress ^ *nativePlayerStateAccessorGetKey_);
        std::array<std::uint32_t, 3> value{};
        auto *const valueBytes = value.data();
        bool completed{};
        __try
        {
            __asm
            {
                mov ecx, valueBytes
                push ecx
                mov eax, object
                push eax
                mov edx, getFunction
                call edx
                add esp, 8
            }
            completed = true;
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            completed = false;
        }
        if (completed)
            flags = value[1];
        return completed;
    }

    void EngineBindings::captureNativeProtectedPlayerStateFlags(
        SvNativePlayerState &state,
        const std::uint32_t fallbackPlaintextFlags) const
    {
        // THE ENGINE KEEPS STATE IN THIS WORD, SO TAKE ITS VERSION BACK.
        //
        // Until now this function wrote the value that had just been protected straight
        // back over ps+0x10, which threw away everything the native stage had stored
        // there. That is why crouch and prone toggled forever: those are TOGGLES on this
        // build, the engine edge-detects them against its own held state, and that state
        // lives in exactly this word -- so resetting it to a constant every frame made
        // every frame look like a fresh press. Stand, crouch, stand, crouch.
        //
        // Read the engine's own view instead and leave THAT as ol-mod's plaintext. The
        // fallback is the previous behaviour, for the case where the getter cannot be
        // decoded at all.
        // REPORT WHETHER WE COULD READ IT, NOT JUST WHAT WE READ.
        //
        // This discarded the getter's result, so a FAILED decode left `flags` holding
        // fallbackPlaintextFlags -- this server's own constant -- and the line below
        // printed it as if it were the engine's view. Two different answers, one word,
        // and no way to tell them apart afterwards. That ambiguity cost section 175:
        // `protected flags now 0x00001000`, one line for a whole session, was read as
        // "the engine froze its stance state" when it may only have meant "the getter
        // never worked and you are looking at your own input".
        std::uint32_t flags{ fallbackPlaintextFlags };
        const auto decoded = readNativeProtectedPlayerStateFlags(state, flags);
        reportProtectedFlagsChange(flags, decoded);
        std::memcpy(
            state.bytes.data() + NativeProtectedPlayerStateValueOffset,
            &flags,
            sizeof(flags));
    }

    bool EngineBindings::rebindNativePlayerStateAccessors(
        SvNativePlayerState &state) const
    {
        // AN ADDRESS-KEYED POINTER DOES NOT SURVIVE BEING COPIED.
        //
        // CODOL stores a function pointer as key ^ function ^ THE PAIRED SLOT'S OWN
        // ADDRESS, so the encoding is only valid at the address it was written at. Every
        // `auto candidate = state;` in this project relocates the playerState into a new
        // buffer, and the pair inside it silently stops decoding to a function.
        //
        // That is measured, not argued. BG_PlayerStateToEntityState reaches
        //     xor ecx, ds:0x00E60B78    <- this exact get key
        //     push edx / push eax / call ecx
        // at 0x0041144C, and with a relocated pair the dedicated jumped somewhere
        // different on every single command -- 0x00198A90 (its own stack), 0x00DAF2AC (a
        // data table), 0x0041144C (its own code) -- with 0xC0000096 privileged-instruction
        // faults from executing whatever it landed on. A MOVING FAULT ADDRESS IS THE
        // SIGNATURE OF A ZEROED OBFUSCATED SLOT; this project had that written down. What
        // it did not have was the rule that COPYING THE BUFFER causes the same thing.
        //
        // The pmove already re-keyed its own slice buffer, which is exactly why the pmove
        // works while everything downstream of it did not. This is that same operation
        // with ONE definition, so the next caller that copies a playerState cannot forget.
        if (!nativeLerpFrameAccessorInitialize_ ||
            !nativePlayerStateAccessorSetKey_ || !nativePlayerStateAccessorGetKey_)
        {
            return false;
        }
        auto *const bytes = state.bytes.data();
        // THE SELECTOR PICKS AN ACCESSOR VARIANT, AND A VALUE ENCODED WITH ONE VARIANT
        // CAN ONLY BE DECODED WITH THAT VARIANT. It must not be random.
        //
        // sub_403C70 is a 34-way switch -- cases 0..32 plus a default -- and each case
        // installs a DIFFERENT getter/setter pair:
        //     case 0:  *set = key ^ sub_401720 ^ addr;   *get = key ^ sub_4017C0 ^ addr;
        //     case 1:  *set = key ^ sub_401840 ^ addr;   *get = key ^ sub_4018D0 ^ addr;
        //     ...
        // The pairs are the same SHAPE -- read three dwords, xor with the object's own
        // address bytes and a key triple, write three dwords -- but not the same
        // FUNCTION. sub_4017C0 uses keys 0x00E60224/0x00E609A0/0x00E609A4 and one
        // permutation of the address bytes; sub_4018D0 uses 0x00E609A8/0x00E609AC/
        // 0x00E609B0 and a different permutation. Ciphertext written by one is noise to
        // the other.
        //
        // This used to be `(QueryPerformanceCounter ^ buffer address) % 33`, a fresh
        // random variant on EVERY call -- and this is called once per pmove slice, again
        // in the converter, and again in runServerAnimationEvent. So whatever the engine
        // stored through one variant was read back through another, and the result
        // differed run to run and frame to frame. That is the shape of the viewmodel
        // being wrong on some cycles and right on others with no code change between
        // them, and of groundEntityNum answering two ways at one origin.
        //
        // A fixed variant is self-consistent: the choice is stored IN the slot, so
        // whatever is installed is what the engine uses to decode.
        constexpr std::uint32_t StableAccessorSelector = 0;
        static_assert(StableAccessorSelector < SvNativeLerpFrameSelectorCount);
        return invokeNativePlayerStateAccessorInitialize(
            nativeLerpFrameAccessorInitialize_,
            bytes,
            StableAccessorSelector,
            *nativePlayerStateAccessorSetKey_,
            *nativePlayerStateAccessorGetKey_);
    }

    std::optional<std::int32_t> EngineBindings::runServerDeathAnimation(
        SvNativePlayerState &playerState,
        const std::uint32_t randomSeed,
        const SvDeathAnimationConditions &conditions) const
    {
        // CODREF(player_die): CODOL BG_AnimScriptEvent 0x004096D0 uses
        // EAX=playerState, ESI=event and stack isContinue/force/randomSeed*.
        // ON 1649370 IT IS EDI=playerState, ESI=event, same three stack args --
        // sub_407E10, and see invokeNativeAnimScriptEvent for how the image says so.
        // BO1 player_die 0x00613690 and Ghosts player_die 0x1401280B0 call the
        // death event only after finishPlayerDamage chooses the die handler.
        //
        // OLMOD(section-84): the id is READ OFF 1649370's OWN name table now, at
        // VA 0x00E60410 -- 8-byte entries, `{const char *name, 0xFFFFFFFF}`.
        // DEATH is entry 1 there, as it is on 3.3.3.3. See runServerSpawnAnimation
        // for the table and for why "identical to 3.3.3.3" is a RESULT here and a
        // defect two enums over.
        // AND SET WHAT THE SCRIPT SELECTS BY. sub_407790 walks the sets in
        // scriptEvents[DEATH] and returns without writing its out-parameter when
        // every set's conditions fail -- which is what -1 has meant on every
        // death this server has ever produced. CoD conditions death animations
        // on HITLOCATION, DAMAGETYPE and HITDIRECTION, and nothing here wrote
        // any of the three, so no set could ever match.
        //
        // THE OFFSETS ARE CALIBRATED, NOT ASSUMED. Conditions live at
        // characterInfo + 0x2EC + 8*index. This tree's own
        // CharacterInfoMoveTypeConditionOffset is 0x304, which is 0x18 past the
        // base -- exactly three entries -- and MOVETYPE is entry 3 of out.exe's
        // condition name table at 0x00E60828. Its parallel type table at
        // 0x00E608C8 then agrees name-for-values on every populated entry:
        // 1 WEAPONCLASS -> RIFLE/SNIPER/MG, 7 WEAPON_POSITION -> HIP/ADS,
        // 11 HITLOCATION -> HIT_TORSO/HEAD/NECK/LEGS. So 10/11/12 are
        // DAMAGETYPE / HITLOCATION / HITDIRECTION and their condType is 1,
        // ANIM_CONDTYPE_VALUE -- plain integers, not the bitflags MOVETYPE uses.
        constexpr std::int32_t AnimEventDeath = 1;
        return runServerAnimationEvent(
            playerState, AnimEventDeath, randomSeed, &conditions);
    }

    std::optional<std::int32_t> EngineBindings::runServerSpawnAnimation(
        SvNativePlayerState &playerState,
        const std::uint32_t randomSeed) const
    {
        // CODREF(client_spawn): a new life must re-establish the TORSO
        // animation, and only an event can do it.
        //
        // ClientSpawn zeroes both playerState +0x0C8 (legsAnim) and +0x0D0
        // (torsoAnim). The legs recover on their own because PmoveSingle's
        // locomotion selector runs every frame and writes them; the torso has
        // no per-frame driver at all - it is written by the body-part dispatch
        // in sub_AA9260 (VA 0x00409260) only when an anim-script item of type 2
        // (TORSO) or 3 (BOTH) is selected, which happens on weapon EVENTS. So
        // after a death sets torsoAnim to index 0, nothing ever moves it again
        // and the upper body has no animation.
        //
        // MEASURED 2026-08-17: torsoAnim takes real values during play - 614,
        // 616, 1547, 1605, 1638, 1640 - and reads 0 for the whole of every life
        // after the first. Retail carries 10-17 distinct torso values per life
        // (2d-quindecies). RAISEWEAPON is the event CoD fires when a weapon is
        // brought up, which is exactly what a spawning player does.
        //
        // OLMOD(section-84): THE ID IS NOW READ OFF 1649370. This comment used
        // to say "event 7 in THIS BUILD'S OWN event table at VA 0x00CE4A20" and
        // 0x00CE4A20 IS 3.3.3.3's TABLE -- out.exe's own 0x00CE4A20 is .rdata
        // holding IME strings ("RemoveList", "RepositionCandWindow"). That is
        // section 81a's rebase hazard in its other form: an address that is real
        // on ONE image, described as the host's.
        //
        // out.exe's table is at VA 0x00E60410. Same 8-byte entry
        // `{const char *name, 0xFFFFFFFF}`, same order, and ENTRIES 0..32 ARE
        // NAME-FOR-NAME IDENTICAL to 3.3.3.3's 0x00CE4A20:
        //
        //   0 PAIN   1 DEATH   2 FIREWEAPON   3 JUMP   4 JUMPBK   5 LAND
        //   6 DROPWEAPON   7 RAISEWEAPON   8 CLIMBMOUNT ... 32 SPAWN
        //
        // 1649370 APPENDS seven and inserts none -- 33 HOLDFIRE, 34 HOLDFIRELOOP,
        // 35 HOLDFIRECANCEL, 36 SIDEROLLING_LEFT, 37 SIDEROLLING_RIGHT,
        // 38 ADSTURRET_DEPLOY, 39 ADSTURRET_UNDEPLOY -- so 7 is correct and is
        // now a MEASUREMENT rather than an inheritance.
        //
        // AND THAT IS THE OPPOSITE OUTCOME TO SECTION 80 ON THE SAME BUILD. The
        // predictable-event enum INSERTED entries and shifted eight ids; this
        // one appended. "1649370 shifted the enums" is not a build-wide rule --
        // it is PER TABLE, so every enum has to be read, and an identical answer
        // is worth as much as a different one.
        constexpr std::int32_t AnimEventRaiseWeapon = 7;
        return runServerAnimationEvent(
            playerState, AnimEventRaiseWeapon, randomSeed);
    }

    void EngineBindings::writeServerAnimSelectionConditions(
        const SvNativePlayerState &playerState,
        const SvDeathAnimationConditions &conditions) const
    {
        // Same slot derivation as logServerAnimConditions, including the reason
        // it is 0x158 and not 3.3.3.3's 0x144.
        constexpr std::size_t CharacterInfoSlotOffset = 0x158;
        constexpr std::size_t ConditionBaseOffset = 0x2EC;
        constexpr std::size_t ConditionStride = 8;
        constexpr std::size_t DamageTypeCondition = 10;
        constexpr std::size_t HitLocationCondition = 11;
        constexpr std::size_t HitDirectionCondition = 12;
        const auto slot = *reinterpret_cast<const std::uint32_t *>(
            playerState.bytes.data() + CharacterInfoSlotOffset);
        if (slot >= ServerCharacterInfoSlotCount)
            return;
        const auto characterInfo = serverCharacterInfo(slot);
        const auto write = [&characterInfo](
                               const std::size_t condition,
                               const std::uint32_t value) {
            const std::uint64_t widened = value;
            std::memcpy(
                characterInfo.data() + ConditionBaseOffset +
                    condition * ConditionStride,
                &widened,
                sizeof(widened));
        };
        write(DamageTypeCondition, conditions.damageType);
        write(HitLocationCondition, conditions.hitLocation);
        write(HitDirectionCondition, conditions.hitDirection);
    }

    std::optional<std::int32_t> EngineBindings::runServerAnimationEvent(
        SvNativePlayerState &playerState,
        const std::int32_t animationEvent,
        const std::uint32_t randomSeed,
        const SvDeathAnimationConditions *const conditions) const
    {
        if (!valid() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return std::nullopt;
        }

        // OLMOD(player_die-native-adapter): execute against copied state and
        // isolated animation-condition storage so a failed candidate cannot
        // partially mutate the authoritative world.
        // TODO(CODOL): replace the supplied seed and isolated global subset
        // after the CODOL server animation context owner is recovered.
        auto candidate = playerState;
        auto candidateSeed = randomSeed;
        // The copy above relocated the buffer, so its obfuscated accessor pair no longer
        // decodes. Same defect as the converter -- see rebindNativePlayerStateAccessors.
        if (!rebindNativePlayerStateAccessors(candidate))
            return std::nullopt;
        // AND HAND THE ENGINE ps+0x10 IN THE FORM IT READS. THIS IS THE T-POSE.
        //
        // Rebinding fixes the accessor PAIR and does nothing to the VALUE. This
        // tree keeps otherFlags at ps+0x10 as a plaintext uint32 and converts it
        // to the engine's protected form only for the duration of a native call
        // -- section 44d's rule, which playerStateToEntityState and the pmove
        // both already follow. This function rebound and never converted, so
        // every animation event handed the engine plaintext where it expects
        // ciphertext.
        //
        // BG_AnimScriptEvent's tail (out.exe sub_407980) decodes that word and
        // refuses the whole event when bit 0x20000000 comes back set, clearing
        // the animation index on its way out:
        //
        //     if (legs & 0x3FF) legs = ((((legs>>10)&3)+1)%4) << 10;
        //     return -1;
        //
        // which is BOTH halves of the signature at once -- durationMs=-1 AND
        // ps legs=2048/3072/1024/0, band kept and index gone. Measured on a real
        // death with Tools/olfinal/anim-event-flag-probe.py: the word decoded to
        // 0xe4001126, which is our 0x1000 read as ciphertext. Not a flag --
        // noise, and about half of all noise has bit 29 set.
        //
        // WHICH IS WHY THIS SURVIVED SINCE AUGUST. sect.171f measured failures
        // interleaving with successes minutes apart on both sides of every
        // commit; sect.171i recorded "works 6/6 and no fix explains it". A coin
        // flip per death is what a garbage decode looks like, and any edit that
        // moves a buffer re-rolls it -- so every recurrence read as a fresh
        // regression from whatever changed last, mine included. The condition
        // hunt could not converge either: DEATH set 23 carries zero conditions
        // and matches unconditionally, so the walk was never the failure.
        std::uint32_t plaintextProtectedFlags{};
        if (!writeNativeProtectedPlayerStateFlags(
                candidate, plaintextProtectedFlags))
        {
            return std::nullopt;
        }
        std::byte *previousAnimConditionBase{};
        if (!installServerAnimConditionStorage(previousAnimConditionBase))
            return std::nullopt;
        // AFTER the isolated storage is installed and BEFORE the event runs --
        // serverCharacterInfo reads through whatever base is currently
        // installed, so writing either side of this pair goes somewhere else.
        if (conditions)
            writeServerAnimSelectionConditions(candidate, *conditions);
        const auto duration = invokeNativeAnimScriptEvent(
            bgAnimScriptEvent_, candidate, animationEvent, 0, 1, candidateSeed);
        // AND PUT IT BACK, which is the other half and not optional.
        // `playerState = std::move(candidate)` below publishes this buffer to
        // the authoritative world, so leaving the protected form in it hands
        // ol-mod's own readers ciphertext where they expect plaintext. Measured
        // live: with only the conversion above, deaths animated correctly and
        // EVERY PLAYER FROZE IN PLACE. The engine owns ps+0x10 for the duration
        // of the call and this tree owns it for the rest of the frame.
        captureNativeProtectedPlayerStateFlags(
            candidate, plaintextProtectedFlags);
        // -1 IS THE ENGINE SAYING "NO ANIMATION MATCHED", AND IT HAS EXACTLY TWO
        // CAUSES. sub_407790 walks the sets in scriptEvents[event] and returns
        // without writing its out-parameter either when the event has no sets at
        // all, or when every set's conditions fail against this client's
        // characterInfo. A zeroed characterInfo fails EVERY condition of either
        // type, so "the conditions were never computed" and "this build has no
        // animation for this event" are indistinguishable from the return value.
        // Dump the conditions on that path only, so a healthy run stays silent.
        // ORDER MATTERS AND SO DOES THE SECOND LINE. The conditions read below
        // has been the only witness on this path since 118e, and it cannot
        // distinguish the two causes of -1: sub_407790 returns without writing
        // its out-parameter both when scriptEvents[event] has no sets at all
        // (`numItems <= 0` at 0x004077B0) and when every set's conditions
        // failed. Those need different fixes and the log said the same word for
        // both. logServerAnimScriptEvent reads the numItems dword itself, from
        // both anim-script bases, WHILE the isolated storage is still installed.
        if (duration && *duration < 0)
        {
            logServerAnimScriptEvent(animationEvent);
            logServerAnimConditions(candidate);
        }
        // AND THE SAME TWO LINES ON THE FIRST SUCCESS OF EACH RUN, WHICH IS THE
        // ONLY REASON EITHER OF THEM CAN ANSWER ANYTHING.
        //
        // Logging only the failing path was the instinct "a healthy run stays
        // silent", and it cost 2026-09-04. The T-pose turned out to be an
        // OLD, SESSION-WIDE flake -- whole sessions come up all-animated or
        // all-T-posed and have since at least 2026-08-23 (09-02 13h: 20 failures
        // and no successes; the hour before it, 7 successes and no failures) --
        // so the question was never "what does a failure look like" but "what is
        // DIFFERENT about a session that works". Sixty-four failure lines, all
        // reading items=24 same=1, and not one line from a working session to
        // compare them against. That is filtering on the very thing being
        // measured (never-filter-on-what-you-are-measuring): the discriminator
        // can only live in the difference, and the difference was never recorded.
        //
        // ONE line per event per run, so a healthy session stays quiet without
        // staying mute.
        else if (duration)
        {
            static std::set<std::int32_t> baselinedEvents;
            if (baselinedEvents.insert(animationEvent).second)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "server animation BASELINE (first success this run) event=" +
                        std::to_string(animationEvent) + " durationMs=" +
                        std::to_string(*duration));
                logServerAnimScriptEvent(animationEvent);
                logServerAnimConditions(candidate);
            }
        }
        const auto restored =
            restoreServerAnimConditionStorage(previousAnimConditionBase);
        if (!duration || !restored)
            return std::nullopt;
        playerState = std::move(candidate);
        return duration;
    }

    std::optional<SvNativePmoveOutput> EngineBindings::runServerPmove(
        SvNativePlayerState &playerState,
        const UserCmd &command,
        const std::optional<UserCmd> &oldCommand,
        const std::uint32_t traceMask,
        const bool finalSlice,
        const SvGlassState &glassState,
        const std::span<const SvCollisionEntity> entities,
        SvNativePmoveFailure *const failure) const
    {
        // OLMOD(native-pmove-transaction): native shared movement runs on a
        // copied playerState. Trace callback/global animation storage changes
        // are scoped, every recovered output is validated, and only a fully
        // successful command replaces the authoritative state.
        const auto fail = [failure](const SvNativePmoveFailure value) {
            if (failure)
                *failure = value;
            return std::optional<SvNativePmoveOutput>{};
        };
        if (failure)
            *failure = SvNativePmoveFailure::None;
        if (!valid() || !traceMask)
            return fail(SvNativePmoveFailure::InvalidBinding);
        if (!validNativeCommand(command) ||
            (oldCommand && !validNativeCommand(*oldCommand)))
        {
            return fail(SvNativePmoveFailure::InvalidCommand);
        }
        if (gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
            return fail(SvNativePmoveFailure::WrongThread);
        if (activeServerPmoveTrace)
            return fail(SvNativePmoveFailure::ReentrantCall);
        if (serverPmoveHandlerSwap.test_and_set(std::memory_order_acquire))
        {
            return fail(SvNativePmoveFailure::HandlerSlotBusy);
        }
        const ScopedAtomicFlag scopedSwap(serverPmoveHandlerSwap);

        clientPmoveTraceFallback.store(
            clientPmoveTrace_, std::memory_order_release);

        auto candidate = playerState;

        // THE ACCESSOR PAIR IS SALTED WITH ITS OWN ADDRESS, so it has to be built on the
        // COPY pmove actually runs on. PmoveSingle decodes
        //     mov eax, [esi+24h] / xor eax, (esi+0x20) / xor eax, dword_E60B78 / call eax
        // and the encoder stores `key ^ function ^ the paired slot's ADDRESS`, so encoding
        // against one buffer and decoding against another yields the real function XORed
        // with the distance between them.
        //
        // The first attempt initialized the authoritative playerState and let `candidate` be
        // copied from it, which MOVED the failure rather than fixing it: the fault went from
        // access=8 on a wild address to access=0 inside something callable, with edi holding
        // 0x0041CBDC -- the instruction immediately after PmoveSingle's own `call eax`.
        // Almost-a-real-pointer is exactly what an address-delta XOR produces.
        //
        // Building it here also makes it per-slice, which is what a value keyed on an
        // address that varies between calls actually needs.
        if (!rebindNativePlayerStateAccessors(candidate))
            return fail(SvNativePmoveFailure::InvalidBinding);
        // THE PMOVE READS ps+0x10 THROUGH THE GETTER TOO, AND SECTION 44d ONLY EVER
        // WROTE THE PROTECTED FORM BEFORE THE CONVERTER.
        //
        // PmoveSingle at 0x0041CBCE decodes the same pair section 43j found --
        //     v4 = dword_E60B78 ^ (unsigned)(ps + 0x20) ^ *(ps + 0x24)
        //     v4(ps + 0x10, out)
        //     if ( (out[1] & 0x10000000) != 0 )
        //         ps->velocity[2] = flt_E60B7C;        // 0x0041CC11
        // and again at 0x0041D961. out[1] is the SAME second dword whose 0x1800 bits
        // decide eType in BG_PlayerStateToEntityState.
        //
        // SV_OverlayPlayerStateToNative leaves ps+0x10 as PLAINTEXT otherFlags at the
        // top of the think, and the pmove runs before the converter re-states it. So the
        // getter decoded plaintext as ciphertext, the flags came back as noise, and bit
        // 28 of that noise was set about half the time -- which assigned a global
        // straight into velocity[2]. Measured: vel.z 0 -> 81.41 on the first slice of a
        // player standing still on the ground with zero buttons, no jump stamped
        // (jumpTime=0, jumpOriginZ=0), no mantle and pm_flags 0; 81.41 recurring as a
        // hard ceiling with gravity decaying it in between; and groundEntityNum flipping
        // 2046/2047 on consecutive slices, because the pair is re-keyed per slice so the
        // noise differs every call.
        //
        // Same shape as the converter: protect before, restore after. The accessor pair
        // was already re-keyed above, which is what makes the setter decodable at all.
        std::uint32_t plaintextProtectedFlags{};
        if (!writeNativeProtectedPlayerStateFlags(candidate, plaintextProtectedFlags))
            return fail(SvNativePmoveFailure::InvalidBinding);

        SvNativePmove pmove{
            .playerState = candidate.bytes.data(),
            .cmd = SV_ToNativeUserCmd(command),
            // TODO(CODOL): Replace the zero oldcmd with the native
            // SV_ClientEnterWorld baseline once that server contract is
            // recovered. The source-level owner keeps the absence explicit.
            .oldcmd = oldCommand
                ? SV_ToNativeUserCmd(*oldCommand)
                : SvNativeUserCmd{},
            .traceMask = std::bit_cast<std::int32_t>(traceMask),
            .handler = 0,
        };
        ServerPmoveTraceContext traceContext{
            .bindings = this,
            .glassState = &glassState,
            .entities = entities,
        };
        const ScopedServerPmoveContext scopedContext(traceContext);
        // CODREF(pmove): "now" INSIDE pmove is this command's time, not the
        // frame's. PmoveSingle compares playerState +0x33C against the shared
        // animation clock at animBase +0x96DD8 with jge/jle at VA 0x00419FD8
        // and 0x00419FF8, and a backlog replays several commands within one
        // server frame - so stamping the frame time here would run every
        // command of that backlog against the same "now" and expire nothing in
        // order. commandTime is the value the comparison is written against.
        serverAnimationTimeMilliseconds_ = command.commandTime;
        std::byte *previousAnimConditionBase{};
        if (!installServerAnimConditionStorage(previousAnimConditionBase))
            return fail(SvNativePmoveFailure::AnimConditionInstallFailed);
        // WHAT THE PMOVE IS ACTUALLY HANDED, AND WHAT IT DOES TO VELOCITY.
        // PmoveSingle derives its frametime from cmd.commandTime - oldcmd.commandTime,
        // and `.oldcmd` here carries an explicit zeroed stub whenever oldCommand is
        // absent. A zero oldcmd makes that difference the whole commandTime, which the
        // engine clamps -- so every command would run with the clamp value as its
        // frametime instead of the real 10-30 ms. Print both times and the velocity on
        // each side of the call; a stub that is quietly always taken looks exactly like
        // a physics bug.
        std::array<float, 3> velocityBefore{};
        std::memcpy(velocityBefore.data(), candidate.bytes.data() + 0x3C,
            sizeof(velocityBefore));
        // CAPTURE oldcmd BEFORE THE CALL. PmoveSingle copies pm->cmd into pm->oldcmd on
        // the way out, so reading it afterwards always shows the two equal and makes the
        // derived msec look like a stuck zero. It is not: oldcmd is correct on entry,
        // and PmoveSingle derives its frametime from ps->commandTime anyway.
        const auto oldCommandTimeAtEntry = pmove.oldcmd.commandTime;
        // THE EDGE THE ENGINE ACTUALLY SEES.
        // Crouch and prone are toggles and they fire on every frame, which means the
        // engine is seeing a RISING edge on every frame -- cmd.buttons carrying the bit
        // while oldcmd.buttons does not. Whether that is true is a two-value question and
        // it has never been asked, because the earlier instrument read oldcmd AFTER the
        // call, where PmoveSingle has already copied cmd into it. Deduped on the pair, so
        // holding a button is one line and tapping it is two.
        // EVERY FRAME OF A STANCE EPISODE, NOT JUST THE EDGES.
        // Deduping on (cmd, oldcmd) hid the frames that matter. The edges themselves are
        // clean -- oldcmd genuinely differs from cmd on a press and on a release -- but
        // PMF_DUCKED went from set to clear BETWEEN two logged lines with no input at
        // all, so whatever un-ducks him happens on a frame the dedupe threw away.
        // OLMOD(bullet-fire-probe): section 75. THE BULLET PATH HAS NEVER RUN.
        //
        // sv_bullet_mp turns a hit into a location and a multiplier and nothing has
        // ever reached it. The fire event is a PREDICTABLE EVENT out.exe's own
        // PM_Weapon emits, so it needs a real fire input, and `buttons` has been
        // 0x00000000 in every headless run on record. A person played for ten minutes
        // on 2026-08-20 and the only bits that appeared at all were 0x10000000 and
        // 0x00000400 -- jump; the log holds zero bullet lines.
        //
        // So this supplies the ONE thing no existing caller does, which is the same
        // shape as section 74's capsule probe. It sets the fire bit on the usercmd
        // going in and lets the ENGINE produce the event, the ammo decrement and the
        // 0x31 the decoder waits for. Nothing is synthesised except the button, so a
        // synthetic event cannot flatter the port.
        if (bulletFireProbeEnabled())
        {
            static std::uint32_t probeFrames{};
            const auto probeHealth =
                readNativeInt(candidate.bytes.data(), ProbeHealthOffset);
            const auto probePmType =
                readNativeInt(candidate.bytes.data(), ProbePmTypeOffset);
            if (probeFrames < BulletFireProbeFrames && probeHealth > 0 &&
                probePmType == 0)
            {
                ++probeFrames;
                // OLMOD(section-87): KEEP THE CLIENT'S OWN BUTTONS, SO THE LINE
                // CAN BE ATTRIBUTED. Section 86c could not say whether a bullet
                // trace came from this injection or from a person at the client
                // window, because the only button value printed was the one
                // AFTER the OR. Printing both makes every line self-attributing:
                // `real=0x00000000 buttons=0x00000001` is this probe and nothing
                // else, and `real=0x00000001` is a human trigger the probe did
                // not need to supply.
                const auto probeRealButtons = pmove.cmd.buttons;
                // Leave the first frames ALONE so PmoveSingle can clear
                // PMF_RESPAWNED, then hold fire. Injecting from frame one is
                // what made every previous window silent.
                if (probeFrames > BulletFireProbeReleaseFrames)
                    pmove.cmd.buttons |= UserCmdButtonFire;
                // Every one of the first twelve, then one in twelve. The opening
                // window is where a state transition would appear at all; the rest
                // is there to catch a gate longer than the window.
                if (probeFrames <= 12 || probeFrames % 12 == 0)
                {
                    // OLMOD(section-85): NAME THE GATE, DO NOT JUST REPORT SILENCE.
                    // `gate=----` means PM_Weapon was allowed to think and did
                    // nothing with the button, which is a real finding. Any letter
                    // present means this server refused it before the engine ever
                    // saw it, and says which one:
                    //   T pm_type >= 8      F pm_flags & 0x400
                    //   E eFlags & 0xC00    P protected bit 30 set
                    const auto probePmFlags = static_cast<std::uint32_t>(
                        readNativeInt(candidate.bytes.data(), ProbePmFlagsOffset));
                    const auto probeEFlags = static_cast<std::uint32_t>(
                        readNativeInt(candidate.bytes.data(), ProbeEFlagsOffset));
                    std::uint32_t probeProtected{};
                    std::memcpy(
                        &probeProtected,
                        candidate.bytes.data() +
                            NativeProtectedPlayerStateValueOffset,
                        sizeof(probeProtected));
                    const char gate[5] = {
                        probePmType >= ProbePmTypeWeaponLimit ? 'T' : '-',
                        (probePmFlags & ProbePmFlagsWeaponGate) != 0 ? 'F' : '-',
                        (probeEFlags & ProbeEFlagsWeaponGate) != 0 ? 'E' : '-',
                        ((probeProtected >> ProbeProtectedWeaponGateBit) & 1u) != 0
                            ? 'P'
                            : '-',
                        '\0',
                    };
                    char line[320]{};
                    std::snprintf(
                        line, sizeof(line),
                        "bullet fire probe frame=%lu/%lu phase=%s "
                        "real=0x%08lX buttons=0x%08lX "
                        "cmdWeapon=%lu health=%ld weap=%ld wState=%ld wTime=%ld "
                        "wDelay=%ld gate=%s pmFlags=%08lX eFlags=%08lX "
                        "protected=%08lX",
                        static_cast<unsigned long>(probeFrames),
                        static_cast<unsigned long>(BulletFireProbeFrames),
                        probeFrames > BulletFireProbeReleaseFrames
                            ? "hold"
                            : "release",
                        static_cast<unsigned long>(probeRealButtons),
                        static_cast<unsigned long>(pmove.cmd.buttons),
                        static_cast<unsigned long>(pmove.cmd.weapon),
                        static_cast<long>(probeHealth),
                        static_cast<long>(readNativeInt(
                            candidate.bytes.data(), ProbeCurrentWeaponOffset)),
                        static_cast<long>(readNativeInt(
                            candidate.bytes.data(), ProbeWeaponStateOffset)),
                        static_cast<long>(readNativeInt(
                            candidate.bytes.data(), ProbeWeaponTimeOffset)),
                        static_cast<long>(readNativeInt(
                            candidate.bytes.data(), ProbeWeaponDelayOffset)),
                        gate,
                        static_cast<unsigned long>(probePmFlags),
                        static_cast<unsigned long>(probeEFlags),
                        static_cast<unsigned long>(probeProtected));
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer, line);
                }
            }
        }
        const auto oldButtonsAtEntry = pmove.oldcmd.buttons;
        const auto cmdButtonsAtEntry = pmove.cmd.buttons;
        std::uint32_t pmFlagsBefore{};
        std::int32_t viewHeightTargetBefore{};
        float viewHeightCurrentBefore{};
        // eFlags TOO, because that is the middle link of the chain. sub_417D10 at
        // 0x00417F3C..0x00417F68 drives pm_flags PRONE/DUCKED from eFlags & 0xC00 --
        // `test eax, 0C00h; jz` and then clear 0x2 / set 0x1 -- so a stance that never
        // happens is either a button that never became an eFlags request, or a request
        // that never became a pm_flag. Printing only pm_flags cannot tell those apart.
        std::uint32_t eFlagsBefore{};
        std::memcpy(&eFlagsBefore, candidate.bytes.data() + 0x104,
            sizeof(eFlagsBefore));
        std::memcpy(&pmFlagsBefore, candidate.bytes.data() + 0x0C,
            sizeof(pmFlagsBefore));
        std::memcpy(&viewHeightTargetBefore, candidate.bytes.data() + 0x16C,
            sizeof(viewHeightTargetBefore));
        std::memcpy(&viewHeightCurrentBefore, candidate.bytes.data() + 0x170,
            sizeof(viewHeightCurrentBefore));
        const auto invocationFailure = invokeNativeServerPmove(
                pmoveSingle_,
                pmSetPitchValues_,
                pmoveTraceHandlerSlot_,
                clientPmoveTrace_,
                &pmove,
                finalSlice);
        {
            // Capped so a long crouch cannot flood the log, and gated on the command or
            // the stance being non-idle so a stationary standing player is silent.
            // FIRE ON THE STANCE BUTTON, NOT ON "ANY INPUT AT ALL".
            //
            // The old condition was `any button or any pm_flag`, capped at 400 lines for
            // the whole session -- so it spent its entire budget in the opening seconds
            // on walking and shooting, and has NEVER ONCE recorded a crouch that happened
            // after the fault appears. Every stance reading in sections 174-176 came from
            // frames where nobody was crouching.
            //
            // 0x100 and 0x200 are the crouch and prone bits (sub_417D10 clears 0x300 and
            // re-sets one of them). Watch cmd AND oldcmd so a press and its release both
            // land, and give it a budget of its own so ordinary movement cannot starve it.
            constexpr std::uint32_t StanceButtons = 0x100u | 0x200u;
            const auto stanceInput =
                ((cmdButtonsAtEntry | pmove.cmd.buttons | oldButtonsAtEntry) &
                    StanceButtons) != 0;
            // AND THE FRAMES AFTER THE PRESS, NOT ONLY THE PRESS. Section 177b asks
            // why vhCur fails to converge, and convergence is by definition something
            // that happens over CONSECUTIVE frames -- but this log only ever fired
            // while a stance button was down, so every sample it has taken is from the
            // press itself and the question could not be answered from it.
            //
            // A press opens a window of 30 frames (~1.5 s at 20 Hz) that logs
            // unconditionally, which is what turns a set of isolated presses into a
            // trace of the lerp. The window is re-armed by each press and the total
            // budget still bounds the whole thing.
            constexpr std::uint32_t StanceFollowFrames = 30;
            static std::uint32_t stanceFollow{};
            if (stanceInput)
                stanceFollow = StanceFollowFrames;
            static std::uint32_t stanceLines{};
            if (stanceFollow && stanceLines < 400)
            {
                --stanceFollow;
                ++stanceLines;
                std::uint32_t pmFlagsAfterStance{};
                std::uint32_t eFlagsAfterStance{};
                std::int32_t viewHeightTargetAfter{};
                float viewHeightCurrentAfter{};
                std::memcpy(&eFlagsAfterStance, candidate.bytes.data() + 0x104,
                    sizeof(eFlagsAfterStance));
                std::memcpy(&pmFlagsAfterStance, candidate.bytes.data() + 0x0C,
                    sizeof(pmFlagsAfterStance));
                std::memcpy(&viewHeightTargetAfter, candidate.bytes.data() + 0x16C,
                    sizeof(viewHeightTargetAfter));
                std::memcpy(&viewHeightCurrentAfter, candidate.bytes.data() + 0x170,
                    sizeof(viewHeightCurrentAfter));
                // THE LERP ITSELF, WHICH THIS LINE HAS NEVER PRINTED. Section 177a
                // concluded "vhCur never converges on vhTgt" from 0x16C and 0x170
                // alone -- but 0x170 does not move toward 0x16C. It moves toward the
                // LERP TARGET at 0x178, starting from the LERP TIME at 0x174. If those
                // two disagree with 0x16C then vhCur is converging correctly on the
                // wrong number, which is a different defect with a different fix, and
                // no measurement so far could tell the two apart.
                // ps+0x158 is clientNum, the same offset sv_native_playerstate_mp
                // reads it from.
                std::int32_t stanceClientNum{};
                std::memcpy(&stanceClientNum, candidate.bytes.data() + 0x158,
                    sizeof(stanceClientNum));
                std::int32_t viewHeightLerpTimeAfter{};
                std::int32_t viewHeightLerpTargetAfter{};
                std::int32_t viewHeightLerpDownAfter{};
                std::memcpy(&viewHeightLerpTimeAfter,
                    candidate.bytes.data() + 0x174, sizeof(viewHeightLerpTimeAfter));
                std::memcpy(&viewHeightLerpTargetAfter,
                    candidate.bytes.data() + 0x178, sizeof(viewHeightLerpTargetAfter));
                std::memcpy(&viewHeightLerpDownAfter,
                    candidate.bytes.data() + 0x17C, sizeof(viewHeightLerpDownAfter));
                // The plaintext ol-mod put there, not the encoded dword sitting in
                // the struct -- reading ps+0x10 raw would print the cookie.
                std::uint32_t stanceOtherFlags{};
                std::memcpy(&stanceOtherFlags,
                    candidate.bytes.data() + NativeProtectedPlayerStateValueOffset,
                    sizeof(stanceOtherFlags));
                char stance[480]{};
                std::snprintf(
                    stance, sizeof(stance),
                    // DOES THE ENGINE WRITE STANCE BACK INTO cmd.buttons?
                    // sub_417D10, the stance handler, does exactly that -- it clears
                    // 0x100|0x200 and re-sets one of them (`buttons & 0xFFFFFCFF | 0x100`,
                    // `v45 | 0x200`). If those bits are persistent STATE the engine
                    // stores in the command rather than input, ol-mod discards them every
                    // frame by rebuilding pmove.cmd from the client's usercmd, and the
                    // stance re-derives from nothing. cmdIn -> cmdOut says so directly.
                    // AND THE TWO BITS THE STANCE HANDLER ACTUALLY GATES ON.
                    // Section 76a: out.exe's sub_417D10 makes TWO reads of the
                    // protected value at ps+0x10 through the obfuscated accessor
                    // pair -- 0x00417E55 and 0x00417FCE -- takes bit 22 and bit 24
                    // of the SECOND dword, and `jne`s past the stance transition
                    // when either is set. 3.3.3.3's 0x00419270 makes NO such read,
                    // which is why nothing in dest1yo's tree has an opinion about
                    // these bits. The second dword is the one ol-mod fills with
                    // otherFlags, and it is the same dword
                    // BG_PlayerStateToEntityState tests 0x1800 in at 0x00411454.
                    // So this server owns the two bits that decide whether a crouch
                    // is allowed to happen, and has never once printed them.
                    // CLIENT NUMBER FIRST, AND IT IS NOT COSMETIC. This line has
                    // never carried one, and TWO PLAYERS' frames interleave in it.
                    // Section 177a read "vhCur wanders between 40.0 and 47.4 and
                    // never converges" off exactly such a trace -- and one player
                    // prone near 40 beside one crouched near 47, sampled
                    // alternately, IS that range. Measured 2026-09-02: with a client
                    // number available, a single crouch and a single prone each
                    // showed a clean monotone descent to their target. Same trap as
                    // [[an-instrument-that-maps-two-answers-onto-one-word]].
                    "stance c=%d t=%u cmdIn=0x%08X cmdOut=0x%08X oldcmd=0x%08X "
                    "pmFlags %08X->%08X eFlags %08X->%08X req0xC00=%u->%u "
                    "vhTgt %d->%d vhCur %.1f->%.1f "
                    "vhLerpTgt=%d vhLerpTime=%d vhLerpDown=%d "
                    // otherFlags here is the PROTECTED word read RAW, which is the
                    // COOKIE for most of a frame -- section 175. It is kept only so the
                    // line's shape is unchanged; never read a flag out of it. Use
                    // `protected flags now ... decoded=1` for that word.
                    "otherFlagsRAW=%08X(cookie) gate22=%u gate24=%u",
                    stanceClientNum,
                    pmove.cmd.commandTime, cmdButtonsAtEntry, pmove.cmd.buttons,
                    oldButtonsAtEntry,
                    pmFlagsBefore, pmFlagsAfterStance,
                    eFlagsBefore, eFlagsAfterStance,
                    static_cast<unsigned>((eFlagsBefore & 0xC00u) != 0),
                    static_cast<unsigned>((eFlagsAfterStance & 0xC00u) != 0),
                    viewHeightTargetBefore, viewHeightTargetAfter,
                    viewHeightCurrentBefore, viewHeightCurrentAfter,
                    viewHeightLerpTargetAfter, viewHeightLerpTimeAfter,
                    viewHeightLerpDownAfter,
                    stanceOtherFlags,
                    static_cast<unsigned>((stanceOtherFlags >> 22) & 1u),
                    static_cast<unsigned>((stanceOtherFlags >> 24) & 1u));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, stance);
            }
            // SILENT UNLESS THE PMOVE MOVES A PLAYER NOBODY IS DRIVING. This found the
            // protected-value read by printing every slice, which is far too loud to
            // leave on -- but the condition it caught states itself exactly: a command
            // with no buttons and no movement that still produces vertical velocity.
            // Keep it armed against that, per section 44g, and let the first few slices
            // through so a spawn is always visible.
            static std::uint32_t pmoveCalls{};
            std::array<float, 3> velocityNow{};
            std::memcpy(velocityNow.data(), candidate.bytes.data() + 0x3C,
                sizeof(velocityNow));
            const auto idleCommand = pmove.cmd.buttons == 0 &&
                pmove.cmd.forwardMove == 0 && pmove.cmd.rightMove == 0;
            const auto unexplained = idleCommand && velocityNow[2] != 0.0f &&
                velocityBefore[2] == 0.0f;
            if (pmoveCalls < 4 || unexplained)
            {
                ++pmoveCalls;
                std::array<float, 3> velocityAfter{};
                std::memcpy(velocityAfter.data(), candidate.bytes.data() + 0x3C,
                    sizeof(velocityAfter));
                std::array<float, 3> originAfter{};
                std::memcpy(originAfter.data(), candidate.bytes.data() + 0x30,
                    sizeof(originAfter));
                std::uint32_t groundAfter{};
                std::memcpy(&groundAfter, candidate.bytes.data() + 0xC0,
                    sizeof(groundAfter));
                // IS THE ENGINE JUMPING HIM? PM_CheckJump stamps jumpTime and records
                // jumpOriginZ, and sets a pm_flag. Mantle, buttons, pm_flags and the
                // whole usercmd are zero, so if a jump is being triggered these three
                // say so and nothing else has to be inferred.
                std::uint32_t jumpTimeAfter{};
                float jumpOriginZAfter{};
                std::uint32_t pmFlagsAfter{};
                std::uint32_t commandTimeAfter{};
                std::memcpy(&jumpTimeAfter, candidate.bytes.data() + 0xD0,
                    sizeof(jumpTimeAfter));
                std::memcpy(&jumpOriginZAfter, candidate.bytes.data() + 0xD4,
                    sizeof(jumpOriginZAfter));
                std::memcpy(&pmFlagsAfter, candidate.bytes.data() + 0x0C,
                    sizeof(pmFlagsAfter));
                std::memcpy(&commandTimeAfter, candidate.bytes.data() + 0x00,
                    sizeof(commandTimeAfter));
                char line[512]{};
                std::snprintf(
                    line, sizeof(line),
                    "pmove-slice %u cmd=%u oldcmd=%u msec=%d hadOld=%u final=%u "
                    "vel %.2f,%.2f,%.2f -> %.2f,%.2f,%.2f org.z=%.2f ground=%u "
                    "buttons=0x%08X traceMask=0x%08X "
                    // A MANTLE LIFTS THE PLAYER AND REPLAYS THE WEAPON ANIMATION --
                    // both reported symptoms from one cause. pmove_t carries the mantle
                    // state outright, so ask it rather than infer it.
                    "mantle{started=%u duration=%d} "
                    "jump{time=%u originZ=%.2f} pmFlags=0x%08X psCmdTime=%u "
                    "xySpeed=%.2f numTouch=%d",
                    pmoveCalls,
                    pmove.cmd.commandTime, oldCommandTimeAtEntry,
                    static_cast<int>(pmove.cmd.commandTime) -
                        static_cast<int>(oldCommandTimeAtEntry),
                    oldCommand ? 1u : 0u, finalSlice ? 1u : 0u,
                    velocityBefore[0], velocityBefore[1], velocityBefore[2],
                    velocityAfter[0], velocityAfter[1], velocityAfter[2],
                    originAfter[2], groundAfter,
                    pmove.cmd.buttons,
                    static_cast<unsigned>(pmove.traceMask),
                    static_cast<unsigned>(pmove.mantleStarted),
                    pmove.mantleDuration,
                    jumpTimeAfter, jumpOriginZAfter, pmFlagsAfter,
                    commandTimeAfter,
                    pmove.xySpeed, pmove.numTouch);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        // ps+0x10 is the engine's storage for the duration of the call and ol-mod's
        // plaintext for the rest of the frame. Section 44d's rule, on the other stage.
        captureNativeProtectedPlayerStateFlags(candidate, plaintextProtectedFlags);
        const auto animConditionBaseRestored =
            restoreServerAnimConditionStorage(previousAnimConditionBase);
        if (invocationFailure != SvNativePmoveFailure::None)
            return fail(invocationFailure);
        if (!animConditionBaseRestored)
            return fail(SvNativePmoveFailure::AnimConditionRestoreFailed);
        if (traceContext.failed)
            return fail(SvNativePmoveFailure::TraceFailed);

        auto output = SV_ReadNativePmoveOutput(pmove);
        if (!output)
            return fail(SvNativePmoveFailure::InvalidOutput);
        // OLMOD(locomotion-anim-diagnostics): sample the conditions the command
        // just wrote. Every command would drown the log, so report one in
        // roughly ten seconds of two-client traffic.
        static std::atomic<std::uint32_t> animConditionSampleCounter{};
        constexpr std::uint32_t AnimConditionSampleInterval = 600;
        if (animConditionSampleCounter.fetch_add(1, std::memory_order_relaxed) %
                AnimConditionSampleInterval == 0)
        {
            logServerAnimConditions(candidate);
        }
        playerState = std::move(candidate);
        return output;
    }
}
