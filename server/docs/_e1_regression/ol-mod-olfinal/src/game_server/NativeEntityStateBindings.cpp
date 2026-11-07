#define NOMINMAX
#include <unordered_map>
#include <Windows.h>

#include "EngineBindings.hpp"
#include "../shared/RuntimeLog.hpp"

#include <array>
#include <cstdio>
#include <cstring>
#include <string>

#include <utility>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(client_think_real): 3.3.3.3's BG_PlayerStateToEntityState
        // 0x00413AB0 receives playerState_s in ECX and entityState_s in EAX.
        //
        // CODDIFF(1649370): the playerState moved OFF the registers. out.exe's
        // sub_4116F0 opens
        //     4116f4  mov ebx, [ebp+arg_0]    <- playerState_s, off the STACK
        //     4116f9  mov edi, eax            <- entityState_s, still in EAX
        //     411703  mov eax, [ebx+104h]     <- reads through ebx, the input
        //     41170c  mov [edi+8], eax        <- writes through edi, the output
        // and its frame declares exactly one argument slot. EAX was right; the
        // playerState was going into ECX, which nothing reads, while the stack
        // slot the callee does read got whatever was already there.
        //
        // The SEH shell is an ol-mod process boundary; it does not change the
        // native converter's register ABI or state ownership.
        bool invokePlayerStateToEntityState(
            void *const function,
            std::byte *const playerStateBytes,
            std::byte *const entityStateBytes)
        {
            bool completed{};
            __try
            {
                __asm
                {
                    mov eax, entityStateBytes
                    push playerStateBytes
                    mov edx, function
                    call edx
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
    }

    bool EngineBindings::playerStateToEntityState(
        SvNativePlayerState &playerState,
        SvNativeEntityState &entityState,
        SvNativeEntityStateProjection &projection) const
    {
        // OLMOD(playerstate-entitystate-transaction): the native function can
        // mutate both inputs, so source publication waits until conversion,
        // animation-context restoration and typed projection all succeed.
        if (!valid() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return false;
        }

        auto playerCandidate = playerState;
        auto entityCandidate = entityState;
        std::byte *previousAnimConditionBase{};
        if (!installServerAnimConditionStorage(previousAnimConditionBase))
            return false;
        // WHAT THIS CALL IS ACTUALLY HANDED. The converter reaches sub_411280 as
        // sub_411280(ps+0x10C, ps+0x108, ps+0x12C) -- the predictable-event copier --
        // ending in `mov [edi+eax*8+0xB8], esi`: edi is the entityState this server puts
        // in EAX, 0xB8 is its event array (which makes 0xD0 index 3, the event slot this
        // build is already known to use), and eax is an index computed from those three
        // playerState words. A fault there is an index THIS SERVER supplied, so print the
        // inputs rather than guess which one is wrong.
        {
            // ONE static for the whole server again, and worse: the line
            // carries seq@108, which advances on nearly every command, so even
            // per-identity change detection would not throttle it. This is a
            // bring-up diagnostic that has served its purpose, so it is capped
            // per entity-state buffer -- the first few conversions per client
            // are what anyone ever reads, and the steady state was ~140 lines
            // a second under RuntimeLog's global lock.
            static std::unordered_map<std::uintptr_t, std::uint32_t>
                reportedByEntityState;
            constexpr std::uint32_t ReportsPerEntityState = 64;
            auto &reportsForThisEntityState =
                reportedByEntityState[reinterpret_cast<std::uintptr_t>(
                    entityCandidate.bytes.data())];
            static std::string reported;
            const auto *const bytes = playerCandidate.bytes.data();
            const auto word = [bytes](const std::size_t offset) {
                std::uint32_t value{};
                std::memcpy(&value, bytes + offset, sizeof(value));
                return value;
            };
            char line[352]{};
            std::snprintf(
                line, sizeof(line),
                "playerstate->entitystate inputs es=0x%08X esSize=%u eFlags@104=0x%08X "
                "seq@108=%u parms@12C=%u events@10C=%u,%u,%u,%u,%u,%u,%u,%u",
                static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(
                    entityCandidate.bytes.data())),
                static_cast<unsigned>(entityCandidate.bytes.size()),
                word(0x104), word(0x108), word(0x12C),
                word(0x10C), word(0x110), word(0x114), word(0x118),
                word(0x11C), word(0x120), word(0x124), word(0x128));
            if (reported != line &&
                reportsForThisEntityState < ReportsPerEntityState)
            {
                ++reportsForThisEntityState;
                reported = line;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        // RE-KEY THE COPY BEFORE THE ENGINE DECODES A POINTER OUT OF IT.
        // `auto playerCandidate = playerState;` above relocated the buffer, and CODOL's
        // function pointers are keyed on the slot's own ADDRESS -- so without this the
        // converter's `xor ecx, ds:0x00E60B78 / call ecx` at 0x0041144C jumps to a
        // different wild address on every command. Measured: 0x00198A90, 0x00DAF2AC,
        // 0x0041144C, plus privileged-instruction faults from executing what it hit.
        //
        // The size hypothesis this replaced is RETIRED, not forgotten: with a kilobyte of
        // slack on each buffer the engine wrote through ps+72 of 15292 and es+226 of 280.
        // Neither struct is too small, so entityState_s 0x118 and playerState_s 0x3BBC
        // both stand.
        if (!rebindNativePlayerStateAccessors(playerCandidate))
            return false;
        // The pair is valid again, so the protected value behind it can be written. Order
        // matters: the setter is decoded THROUGH the pair, so it has to be re-keyed first.
        std::uint32_t plaintextProtectedFlags{};
        if (!writeNativeProtectedPlayerStateFlags(
                playerCandidate, plaintextProtectedFlags))
        {
            return false;
        }
        const auto completed = [&] {
            const NativeStageScope stage{ "playerstate_to_entitystate" };
            return invokePlayerStateToEntityState(
                playerStateToEntityState_,
                playerCandidate.bytes.data(),
                entityCandidate.bytes.data());
        }();
        // The engine's SET accessor replaced ps+0x10 with its encoded form, and that is
        // the dword ol-mod reads otherFlags from. Leaving it there made the server's own
        // otherFlags a different random number every frame -- which the snapshot frame
        // validator then refused (`playerstate domain refused otherFlags=...`), so no
        // snapshot ever reached the client.
        captureNativeProtectedPlayerStateFlags(
            playerCandidate, plaintextProtectedFlags);
        const auto animConditionBaseRestored =
            restoreServerAnimConditionStorage(previousAnimConditionBase);
        if (completed)
            SV_MarkNativeEntityStateSecureOriginBound(entityCandidate);
        SvEntityOriginKeys originKeys;
        for (std::size_t index = 0; index < originKeys.values.size(); ++index)
        {
            originKeys.values[index] = *reinterpret_cast<const std::uint32_t *>(
                module_ + EntityOriginKeyRvas[index]);
        }
        const auto entityProjection = SV_ReadNativeEntityState(
            entityCandidate, originKeys);
        if (!completed || !animConditionBaseRestored || !entityProjection)
        {
            static std::string reported;
            auto details = std::string("completed=") + (completed ? "1" : "0") +
                " animConditionRestored=" + (animConditionBaseRestored ? "1" : "0") +
                " projection=" + (entityProjection ? "1" : "0");
            if (reported != details)
            {
                reported = details;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "playerstate->entitystate refused " + details);
            }
            return false;
        }

        playerState = std::move(playerCandidate);
        // CODDIFF(client_think_real): entityState origin words are encrypted
        // with their field addresses. SvNativeEntityState assignment relocates
        // them from the temporary native-call buffer to this persistent owner.
        entityState = std::move(entityCandidate);
        projection = *entityProjection;
        return true;
    }
}
