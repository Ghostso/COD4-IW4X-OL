#include "sv_weapon_movement_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    namespace
    {
        bool finiteVector(const std::array<float, 3> &value)
        {
            return std::ranges::all_of(value, [](const float component) {
                return std::isfinite(component);
            });
        }

        bool validClientState(const SvWeaponMovementClientState &state)
        {
            // OLMOD(server-weapon-movement-owner): validation protects the
            // reconstructed persistent owner; it is not a native BG stage.
            return std::isfinite(state.damagePitch) &&
                std::isfinite(state.damageRoll) &&
                std::isfinite(state.lastIdleFactor) &&
                finiteVector(state.baseAngles) &&
                finiteVector(state.baseOrigin) &&
                finiteVector(state.recoilAngles) &&
                finiteVector(state.recoilSpeed) &&
                finiteVector(state.swayAngles) &&
                finiteVector(state.swayOrigin) &&
                finiteVector(state.swayViewAngles);
        }

        bool validFrameInput(const SvWeaponMovementFrameInput &input)
        {
            // OLMOD(server-weapon-movement-frame): generic builder validation.
            // The native adapter adds stricter current guards such as nonzero
            // frame time and unsupported shellshock rejection.
            return input.playerState && std::isfinite(input.xyspeed) &&
                input.xyspeed >= 0.0f && std::isfinite(input.frameTime) &&
                input.frameTime >= 0.0f && input.shellShockDuration >= 0 &&
                input.shellShockFadeTime >= 0;
        }

        bool validCalculatedState(const SvWeaponMovementState &state)
        {
            // OLMOD(native-weapon-movement-output-guard): native stages mutate
            // caller-owned state; reject non-finite or detached outputs before
            // projecting them into the persistent candidate.
            return state.playerState && state.weaponIdleTime &&
                std::isfinite(state.xyspeed) && state.xyspeed >= 0.0f &&
                std::isfinite(state.frameTime) && state.frameTime >= 0.0f &&
                std::isfinite(state.lastIdleFactor) &&
                std::isfinite(state.damagePitch) &&
                std::isfinite(state.damageRoll) &&
                finiteVector(state.baseAngles) &&
                finiteVector(state.baseOrigin) &&
                finiteVector(state.recoilAngles) &&
                finiteVector(state.recoilSpeed) &&
                finiteVector(state.swayAngles) &&
                finiteVector(state.swayOrigin) &&
                finiteVector(state.swayViewAngles) &&
                finiteVector(state.bobAngles) &&
                state.shellShockDuration >= 0 &&
                state.shellShockFadeTime >= 0;
        }
    }

    bool SV_IsWeaponMovementOutputValid(
        const SvNativeWeaponMovementOutput &output)
    {
        // OLMOD(server-gun-angle-publication): final transaction guard before
        // gun angles can feed muzzle calculation and snapshot-side state.
        return finiteVector(output.viewAngles) &&
            finiteVector(output.weaponAngles) &&
            std::isfinite(output.gunPitch) && std::isfinite(output.gunYaw);
    }

    bool SV_BuildViewMovementState(
        const SvWeaponMovementFrameInput &input,
        SvWeaponMovementClientState &clientState,
        SvViewMovementState &output)
    {
        // CODDIFF(g_build_weapon_state): field order is exact CODOL viewState_t;
        // values come from the reconstructed server owner because the CODOL
        // server G_BuildWeaponState wrapper and gclient layout were removed.
        if (!validFrameInput(input) || !validClientState(clientState))
            return false;

        output = {
            .playerState = input.playerState->bytes.data(),
            .damageTime = clientState.damageTime,
            .time = input.time,
            .damagePitch = clientState.damagePitch,
            .damageRoll = clientState.damageRoll,
            .xyspeed = input.xyspeed,
            .frameTime = input.frameTime,
            .lastIdleFactor = clientState.lastIdleFactor,
            .weaponIdleTime = &clientState.weaponIdleTime,
        };
        return true;
    }

    bool SV_BuildWeaponMovementState(
        const SvWeaponMovementFrameInput &input,
        SvWeaponMovementClientState &clientState,
        SvWeaponMovementState &output)
    {
        // CODDIFF(g_build_weapon_state): construct exact native weaponState_t
        // from source-owned equivalents of reference-server gclient fields.
        // No BO1/Ghosts/BO2 offsets are copied into this CODOL layout.
        if (!validFrameInput(input) || !validClientState(clientState))
            return false;

        output = {
            .playerState = input.playerState->bytes.data(),
            .xyspeed = input.xyspeed,
            .frameTime = input.frameTime,
            .lastIdleFactor = clientState.lastIdleFactor,
            .time = input.time,
            .damageTime = clientState.damageTime,
            .damagePitch = clientState.damagePitch,
            .damageRoll = clientState.damageRoll,
            .weaponIdleTime = &clientState.weaponIdleTime,
            .baseAngles = clientState.baseAngles,
            .baseOrigin = clientState.baseOrigin,
            .recoilAngles = clientState.recoilAngles,
            .recoilSpeed = clientState.recoilSpeed,
            .swayAngles = clientState.swayAngles,
            .swayOrigin = clientState.swayOrigin,
            .swayViewAngles = clientState.swayViewAngles,
            .shellShockStart = input.shellShockStart,
            .shellShockDuration = input.shellShockDuration,
            .shellShockFadeTime = input.shellShockFadeTime,
        };
        return true;
    }

    bool SV_SaveWeaponMovementState(
        const SvWeaponMovementState &input,
        SvWeaponMovementClientState &clientState)
    {
        // CODDIFF(g_build_weapon_state): mirrors the semantic save-back present
        // in all three reference servers while enforcing source pointer
        // ownership and atomic candidate publication.
        if (!validCalculatedState(input) ||
            input.weaponIdleTime != &clientState.weaponIdleTime)
        {
            return false;
        }

        auto next = clientState;
        next.lastIdleFactor = input.lastIdleFactor;
        next.baseAngles = input.baseAngles;
        next.baseOrigin = input.baseOrigin;
        next.recoilAngles = input.recoilAngles;
        next.recoilSpeed = input.recoilSpeed;
        next.swayAngles = input.swayAngles;
        next.swayOrigin = input.swayOrigin;
        next.swayViewAngles = input.swayViewAngles;
        if (!validClientState(next))
            return false;

        clientState = next;
        return true;
    }
}
