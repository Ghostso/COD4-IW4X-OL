#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "EngineBindings.hpp"
#include "server_mp/sv_client_events_mp.hpp"
#include "server_mp/sv_snapshot_mp.hpp"
#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <map>
#include <optional>
#include <string>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(g_build_weapon_state): these playerState_s offsets are read by
        // the refreshed CODOL shared stages at 0x00430990..0x00431DE0. The
        // names are constrained by CODOL consumers; neighboring layout stays
        // opaque and no reference-server offset is imported here.
        //
        // CODDIFF(1649370): THIS WHOLE BLOCK WAS 3.3.3.3's AND NONE OF IT WAS PORTED.
        // Every constant below was byte-identical to ..\ol-mod-ffa's copy of this file
        // while sv_native_playerstate_mp.cpp -- the same struct, in this tree -- had
        // already moved all of them. That is the failure this project keeps paying for:
        // one struct, two files, and only one gets updated. The symptom was total, not
        // subtle: runServerWeaponMovement read currentWeapon from 0x340, which on this
        // build is inside the held-weapon state array, got a value past its bound and
        // refused EVERY command with weapon_movement_rejected. Nothing moved, ever.
        //
        // Confirmed by Tools/olfinal/audit-native-offsets.py against the extracted
        // playerstate netfield table. Four are direct table hits; WeaponFlags is
        // bracketed by 0x344 and 0x34C at the same +0xB8 shift, and shows up as A-only
        // 0x348 / C-only 0x400 -- the same relocation seen from both sides.
        constexpr std::size_t ViewAnglesOffset = 0x160;
        constexpr std::size_t EFlagsOffset = 0x104;
        constexpr std::size_t LinkEntityOffset = 0x248;
        constexpr std::size_t SelectedOffhandOffset = 0x3E4;
        constexpr std::size_t CurrentWeaponOffset = 0x3F8;
        constexpr std::size_t WeaponFlagsOffset = 0x400;
        constexpr std::size_t WeaponPositionFractionOffset = 0x404;
        constexpr std::int32_t UnlinkedEntityNum = 2047;
        constexpr std::uint32_t TurretViewFlags = 0x0C00;
        constexpr std::uint8_t OffhandWeaponFlag = 0x02;
        // sub_434C20 is the deepest retained movement stage used below; its
        // highest direct WeaponDef read is +3148.
        constexpr std::size_t WeaponMovementDefinitionBytes = 3152;

        template <typename Value>
        Value readNativeValue(
            const SvNativePlayerState &playerState,
            const std::size_t offset)
        {
            Value value{};
            std::memcpy(
                &value,
                playerState.bytes.data() + offset,
                sizeof(value));
            return value;
        }

        bool finiteVector(const std::array<float, 3> &value)
        {
            return std::ranges::all_of(value, [](const float component) {
                return std::isfinite(component);
            });
        }

        bool readableNativeSpan(const void *const address, const std::size_t length)
        {
            if (!address)
                return false;
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
                const auto regionEnd = reinterpret_cast<std::uintptr_t>(
                    memory.BaseAddress) +
                    static_cast<std::uintptr_t>(memory.RegionSize);
                if (regionEnd <= cursor)
                    return false;
                cursor = std::min(regionEnd, end);
            }
            return true;
        }

        void callViewDamageKick(
            void *const function,
            SvViewMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CODOL 0x004318B0 receives
            // viewState_t in ESI and output angles in EDI.
            __asm
            {
                push esi
                push edi
                mov esi, state
                mov edi, angles
                call function
                pop edi
                pop esi
            }
        }

        void callViewBobAngles(
            void *const function,
            SvViewMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CODOL 0x00431C40 receives
            // viewState_t in ECX and angles on the stack.
            __asm
            {
                push angles
                mov ecx, state
                call function
                add esp, 4
            }
        }

        void callViewAdsBob(
            void *const function,
            SvViewMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CODOL 0x00431DE0 receives output
            // angles in EDI and viewState_t on the stack.
            __asm
            {
                push edi
                push state
                mov edi, angles
                call function
                add esp, 4
                pop edi
            }
        }

        void callWeaponRecoil(
            void *const function,
            SvWeaponMovementState *const state)
        {
            // CODREF(g_build_weapon_state): CODOL 0x004310F0 receives the
            // caller-owned weaponState_t in EDX.
            __asm
            {
                mov edx, state
                call function
            }
        }

        void callWeaponBob(
            void *const function,
            SvWeaponMovementState *const state)
        {
            // CODREF(g_build_weapon_state): CODOL 0x004312F0 receives the
            // caller-owned weaponState_t in EDI.
            __asm
            {
                push edi
                mov edi, state
                call function
                pop edi
            }
        }

        void callSetWeaponAngles(
            void *const function,
            SvWeaponMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): 3.3.3.3's 0x00431460 receives the
            // output angles in EAX and weaponState_t in ECX.
            //
            // CODDIFF(1649370): both moved, and they SWAPPED sides. out.exe's
            // sub_434F90 opens
            //     434f99  mov ebx, [ebp+arg_0]   <- output angles, off the STACK
            //     434f9c  fst dword ptr [ebx]    <- writes angles[0..2]
            //     434fa6  mov edi, eax           <- weaponState_t, in EAX
            // so the angles are a stack argument and the state is the register
            // one. Passing them the 3.3.3.3 way put the state in EAX where the
            // callee expects nothing, left ECX unread, and pushed no stack
            // argument at all - so the callee wrote three floats through
            // whatever happened to sit at [ebp+arg_0].
            __asm
            {
                push angles
                mov eax, state
                call function
                add esp, 4
            }
        }

        // CODDIFF(1649370): THIS WAS THE WRONG FUNCTION, AND ITS ARGUMENTS WERE
        // BACKWARDS. `AnglesToQuaternionRva` 0x3853E0 is sub_7853E0, which reads its
        // angles through ESI and writes FOUR floats through EDX - an
        // angles-to-QUATERNION. 3.3.3.3's nine-float AnglesToAxis 0x0062C1A0 has
        // no counterpart on this build. Passing the pointers the other way round
        // read an uninitialised axis AS the angles and stamped a quaternion over
        // the caller's angle vector. Section 73f.
        //
        // AngleVectors sub_767890 is what 1649370 has: four STACK arguments,
        // __cdecl, three destinations. AnglesToAxis is AngleVectors with the
        // SECOND row inverted, which is the (forward, LEFT, up) the composition
        // below and MatrixMultiply both expect.
        void callAngleVectors(
            void *const function,
            const float *const angles,
            float *const axis)
        {
            auto *const forward = axis;
            auto *const right = axis + 3;
            auto *const up = axis + 6;
            __asm
            {
                push up
                push right
                push forward
                push angles
                mov eax, function
                call eax
                add esp, 10h
            }
            for (std::size_t component{ 3 }; component != 6; ++component)
                axis[component] = -axis[component];
        }

        void callMatrixMultiply(
            void *const function,
            const float *const weaponAxis,
            const float *const viewAxis,
            float *const outputAxis)
        {
            // CODREF(g_build_weapon_state): CODOL MatrixMultiply 0x00629730
            // receives the left/weapon axis on the stack, right/view axis in
            // EAX and output in EDX. This is weaponAxis * viewAxis.
            __asm
            {
                mov eax, viewAxis
                mov edx, outputAxis
                push weaponAxis
                call function
                add esp, 4
            }
        }

        void callAxisToAngles(
            void *const function,
            const float *const axis,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CODOL AxisToAngles 0x0062AE50
            // receives output angles in EAX and the input axis in ECX.
            __asm
            {
                mov eax, angles
                mov ecx, axis
                call function
            }
        }

        // MEASURE WHAT THE ENGINE ACTUALLY WRITES, RATHER THAN TRUST A CARRIED SIZE.
        //
        // sv_weapon_movement_mp.hpp is byte-identical to ..\ol-mod-ffa's copy, so both
        // structs handed to these native stages are 3.3.3.3's layout and NOTHING has
        // established their footprint on 1649370. This project has already been bitten
        // twice by exactly that -- playerState_s 0x3564 -> 0x3BBC and characterInfo
        // 0x3B8 -> 0x450, both cases of handing the engine a buffer shorter than it
        // believes it owns -- and the first cycle that actually reached these calls
        // killed the dedicated with a wild write (0xC0000005 op=1 target=0x001B0000).
        //
        // A guessed size would be a fourth guess. Instead give the native stage a
        // buffer with a large zero tail, snapshot it, and report the highest byte that
        // changed. The tail is ZERO rather than a fill pattern on purpose: a native
        // read past the struct then sees a null pointer or a 0.0f, not 0xCDCDCDCD.
        // The slack also means an overrun lands in slack instead of on a return address,
        // so the measurement can be taken at all.
        constexpr std::size_t NativeStateSlack = 512;

        template <typename State, typename Invoke>
        bool measureNativeStateWrite(
            const char *const stage,
            const State &state,
            Invoke &&invoke)
        {
            alignas(16) std::array<std::byte, sizeof(State) + NativeStateSlack> storage{};
            std::memcpy(storage.data(), &state, sizeof(State));
            auto before = storage;
            const auto completed =
                invoke(reinterpret_cast<State *>(storage.data()));
            std::size_t highest{};
            for (std::size_t index = storage.size(); index-- > 0;)
            {
                if (storage[index] != before[index])
                {
                    highest = index + 1;
                    break;
                }
            }
            // A HIGH-WATER OF ZERO IS STILL A HIGH-WATER. `!seen` made a stage that
            // writes nothing -- view_movement, which really does write through 0 --
            // report on EVERY frame: 6452 lines in a 110-second run, one of the three
            // things that pushed tick time to 8ms. Remember that the stage has been
            // reported at all, not just how far it wrote.
            static std::map<std::string, std::optional<std::size_t>> reported;
            auto &seen = reported[stage];
            if (!seen || highest > *seen)
            {
                seen = highest;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("native state write ") + stage +
                        " declared=" + std::to_string(sizeof(State)) +
                        " wroteThrough=" + std::to_string(highest) +
                        (highest > sizeof(State) ? " *** PAST THE DECLARED END ***" : "") +
                        (completed ? "" : " (stage faulted)"));
            }
            return completed;
        }

        bool invokeViewMovement(
            void *const damageKick,
            void *const idleAngles,
            void *const bobAngles,
            void *const adsBob,
            SvViewMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CG_OffsetFirstPersonView
            // 0x0051D3B0 establishes damage kick -> idle -> bob -> ADS bob.
            // OLMOD(native-weapon-movement-call-guard): SEH contains a native
            // fault but cannot undo mutation through an invalid native pointer.
            bool completed{};
            __try
            {
                callViewDamageKick(damageKick, state, angles);
                reinterpret_cast<void (__cdecl *)(
                    SvViewMovementState *, float *)>(idleAngles)(state, angles);
                callViewBobAngles(bobAngles, state, angles);
                callViewAdsBob(adsBob, state, angles);
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        bool invokeWeaponMovement(
            void *const base,
            void *const sway,
            void *const recoil,
            void *const bob,
            void *const setAngles,
            SvWeaponMovementState *const state,
            float *const angles)
        {
            // CODREF(g_build_weapon_state): CG_AddViewWeapon 0x0055C8A0 runs
            // Base -> Sway -> Recoil -> Bob -> SetAngles. SetOrigin is a render
            // output stage and is not needed to publish server gun pitch/yaw.
            // OLMOD(native-weapon-movement-call-guard): source supplies a
            // transaction-local state and commits it only after validation.
            bool completed{};
            __try
            {
                reinterpret_cast<void (__cdecl *)(
                    std::int32_t, SvWeaponMovementState *)>(base)(-1, state);
                reinterpret_cast<void (__cdecl *)(
                    SvWeaponMovementState *)>(sway)(state);
                callWeaponRecoil(recoil, state);
                callWeaponBob(bob, state);
                callSetWeaponAngles(setAngles, state, angles);
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        bool invokeAdsComposition(
            void *const angleVectors,
            void *const matrixMultiply,
            void *const axisToAngles,
            const float *const weaponAngles,
            const float *const viewAngles,
            float *const outputAngles)
        {
            // CODREF(g_build_weapon_state): CODOL client producer 0x00559D10
            // and BO1/BO2/Ghosts server wrappers all reduce the composed axis
            // directly to gun angles. Client quaternion rendering is excluded.
            bool completed{};
            __try
            {
                std::array<float, 9> weaponAxis{};
                std::array<float, 9> viewAxis{};
                std::array<float, 9> outputAxis{};
                callAngleVectors(angleVectors, weaponAngles, weaponAxis.data());
                callAngleVectors(angleVectors, viewAngles, viewAxis.data());
                callMatrixMultiply(
                    matrixMultiply,
                    weaponAxis.data(),
                    viewAxis.data(),
                    outputAxis.data());
                callAxisToAngles(axisToAngles, outputAxis.data(), outputAngles);
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }
    }

    std::optional<SvNativeWeaponMovementOutput>
        EngineBindings::runServerWeaponMovement(
            const SvWeaponMovementFrameInput &input,
            SvWeaponMovementClientState &clientState,
            const SvResolvedLoadout *const resolvedLoadout) const
    {
        // CODDIFF(g_build_weapon_state): CODOL retains these shared BG stages
        // but not its authoritative server wrapper or gclient layout. This
        // adapter therefore reconstructs the wrapper around native primitives;
        // it is not a binary-identical recovered CODOL G_BuildWeaponState.
        if (!valid() || !input.playerState || !resolvedLoadout ||
            input.frameTime <= 0.0f ||
            input.shellShockStart != 0 || input.shellShockDuration != 0 ||
            input.shellShockFadeTime != 3000 ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return std::nullopt;
        }

        const auto eFlags = readNativeValue<std::uint32_t>(
            *input.playerState, EFlagsOffset);
        const auto linkEntity = readNativeValue<std::int32_t>(
            *input.playerState, LinkEntityOffset);
        // TODO(CODOL): Resolve server-owned linked/turret view context. Active
        // shellshock also remains rejected above until the confirmed native
        // index/time/duration fields are mapped to this stage's start/fade
        // inputs. Exit this guard only with both owners and conversion semantics.
        if ((eFlags & TurretViewFlags) != 0 || linkEntity != UnlinkedEntityNum)
            return std::nullopt;

        const auto weaponFlags = readNativeValue<std::uint8_t>(
            *input.playerState, WeaponFlagsOffset);
        // CODREF(1649370): this is the active-offhand selector, not an
        // unsupported alternate-overlay state. PM_OffHandPrepare 0x429640
        // enters weapon state 17 and sets ps+0x400 bit 2 at 0x429663. Every
        // retained view/weapon movement stage below tests the same bit and then
        // reads the selected offhand from ps+0x3E4 instead of the current gun
        // at ps+0x3F8 (for example 0x4353F2..0x435405).
        //
        // Rejecting the bit discarded every command from a natural grenade
        // preparation onward. A high-latency client visibly replayed a shot as
        // snapshots kept rolling it back to the last accepted command. Pmove
        // has already checked the selection against the held-weapon array; keep
        // the native definition boundary fail-closed before invoking consumers.
        if ((weaponFlags & OffhandWeaponFlag) != 0)
        {
            const auto selectedOffhand = readNativeValue<std::uint32_t>(
                *input.playerState, SelectedOffhandOffset);
            if (!selectedOffhand ||
                selectedOffhand > EngineBindings::MaximumWeaponAssetIndex)
            {
                return std::nullopt;
            }
            const auto *const definitionSlot = module_ +
                WeaponDefinitionsRva + selectedOffhand * sizeof(void *);
            if (!readableNativeSpan(definitionSlot, sizeof(void *)))
                return std::nullopt;
            const auto *const definition =
                *reinterpret_cast<const std::uint8_t *const *>(definitionSlot);
            if (!readableNativeSpan(definition, WeaponMovementDefinitionBytes))
                return std::nullopt;
        }

        const auto currentWeapon = readNativeValue<std::uint32_t>(
            *input.playerState, CurrentWeaponOffset);
        // CODDIFF(1649370): 0x3FF is 3.3.3.3's TEN-BIT weapon index; this build writes
        // eleven and its registry holds 1700. The live gamestate reports
        // firstDynamicWeapon=1224, so a modular weapon -- the only kind a real class
        // produces -- is ALWAYS above 1023 and this rejected all of them.
        if (currentWeapon > EngineBindings::MaximumWeaponAssetIndex)
            return std::nullopt;
        const SvResolvedWeapon *weapon{};
        // The alt has to live here too, and it must stay OUT of the loadout.
        SvResolvedWeapon altWeapon{};
        if (currentWeapon != 0)
        {
            weapon = SV_FindResolvedWeapon(
                *resolvedLoadout, static_cast<std::uint16_t>(currentWeapon));
            if (!weapon || weapon->weaponAssetIndex != currentWeapon)
            {
                // AND THIS IS WHERE ALT-FIRE DIED, ONE LAYER PAST WHERE IT WAS
                // FIXED. sect.190 gave the FIRE path SV_SetAltWeaponLookup so a
                // shot with an alt selected would not return Invalid and reject
                // the whole command. Weapon movement resolves the weapon too,
                // out of the same frozen loadout, and nobody taught it.
                //
                // Measured 2026-09-04 with the real button (0x08000000): the
                // switch fired sixteen times, 1224->1225 and 1235->1236, and
                // check-alt-fire.py reported `switches happened and clientThink
                // was rejected afterwards, stages: weapon_movement_rejected`.
                // From the player's chair that is "the UI changed and the gun
                // did not" -- netfield 39 goes out, and every command after it
                // is thrown away.
                //
                // The alt STILL must not be added to SvResolvedLoadout: that
                // struct sits inside the client state the address-keyed native
                // buffer is sized against, and growing a struct in that
                // position is what broke the death animation twice (sect.184h).
                // A lookup costs nothing and moves nothing.
                if (!SV_LookupAltWeapon(
                        static_cast<std::uint16_t>(currentWeapon), altWeapon))
                {
                    // CODREF(OLfinal live): key 4 selects the granted UAV via
                    // retained PM_Weapon. It is held inventory, not a class gun
                    // or an alt. Keep running the same native movement stages.
                    // The action slot may already be consumed while the native
                    // return to the gun is pending; entitlement is held inventory.
                    const auto uav = resolveUavWeapon();
                    const auto held = readNativeValue<std::array<std::uint32_t, 15>>(
                        *input.playerState, 0x2F4);
                    if (!uav || uav->weaponAssetIndex != currentWeapon ||
                        std::ranges::find(held, currentWeapon) == held.end())
                        return std::nullopt;
                    altWeapon.weaponAssetIndex = uav->weaponAssetIndex;
                    altWeapon.aimDownSight = uav->aimDownSight;
                    altWeapon.hasOverlayReticle = uav->hasOverlayReticle;
                }
                weapon = &altWeapon;
            }
        }
        // CODREF(pmove): PM_Weapon deliberately selects CODOL's native null
        // weapon while mantle weapon-inactive or PMF_LADDER is active. It is
        // engine-owned state, not a loadout entitlement; nonzero weapons remain
        // constrained to the loadout, resolved alts or the held native UAV.

        const auto weaponPositionFraction = readNativeValue<float>(
            *input.playerState, WeaponPositionFractionOffset);
        if (!std::isfinite(weaponPositionFraction) ||
            weaponPositionFraction < 0.0f || weaponPositionFraction > 1.0f)
        {
            return std::nullopt;
        }

        auto candidateState = clientState;
        // OLMOD(server-weapon-movement-transaction): reference servers persist
        // these fields in gclient. Source keeps an equivalent candidate owner
        // so a later native/event failure cannot partially advance recoil/sway.
        SvViewMovementState viewState{};
        if (!SV_BuildViewMovementState(input, candidateState, viewState))
            return std::nullopt;

        std::array<float, 3> viewOffsets{};
        SV_SetCurrentNativeStage("view_movement");
        if (!measureNativeStateWrite(
                "view_movement", viewState,
                [&](SvViewMovementState *const measured) {
                    const auto ok = invokeViewMovement(
                        viewMovementDamageKick_,
                        viewMovementIdleAngles_,
                        viewMovementBobAngles_,
                        viewMovementAdsBob_,
                        measured,
                        viewOffsets.data());
                    viewState = *measured;
                    return ok;
                }) ||
            !finiteVector(viewOffsets) || !std::isfinite(viewState.lastIdleFactor))
        {
            return std::nullopt;
        }
        candidateState.lastIdleFactor = viewState.lastIdleFactor;

        SvNativeWeaponMovementOutput output{};
        const auto baseViewAngles = readNativeValue<std::array<float, 3>>(
            *input.playerState, ViewAnglesOffset);
        if (!finiteVector(baseViewAngles))
            return std::nullopt;
        for (std::size_t index = 0; index < output.viewAngles.size(); ++index)
            output.viewAngles[index] = baseViewAngles[index] + viewOffsets[index];
        if (!finiteVector(output.viewAngles))
            return std::nullopt;

        SvWeaponMovementState weaponState{};
        SV_SetCurrentNativeStage("weapon_movement");
        if (!SV_BuildWeaponMovementState(input, candidateState, weaponState) ||
            !measureNativeStateWrite(
                "weapon_movement", weaponState,
                [&](SvWeaponMovementState *const measured) {
                    const auto ok = invokeWeaponMovement(
                        weaponMovementBase_,
                        weaponMovementSway_,
                        weaponMovementRecoil_,
                        weaponMovementBob_,
                        setWeaponMovementAngles_,
                        measured,
                        output.weaponAngles.data());
                    weaponState = *measured;
                    return ok;
                }) ||
            !finiteVector(output.weaponAngles) ||
            !SV_SaveWeaponMovementState(weaponState, candidateState))
        {
            return std::nullopt;
        }

        SV_SetCurrentNativeStage("ads_composition");
        auto gunAngles = output.viewAngles;
        // CODREF(g_build_weapon_state): current weapon owns ADS capability;
        // overlay reticle selection normally uses that weapon. The alternate
        // overlay branch has already failed closed above.
        if (weapon && weapon->aimDownSight && !weapon->hasOverlayReticle &&
            weaponPositionFraction != 0.0f &&
            !invokeAdsComposition(
                angleVectors_,
                matrixMultiply_,
                axisToAngles_,
                output.weaponAngles.data(),
                output.viewAngles.data(),
                gunAngles.data()))
        {
            return std::nullopt;
        }
        if (!finiteVector(gunAngles))
            return std::nullopt;

        SV_SetCurrentNativeStage("none");
        output.gunPitch = gunAngles[0];
        output.gunYaw = gunAngles[1];
        clientState = candidateState;
        return output;
    }
}
