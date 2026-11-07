#pragma once

#include "sv_native_playerstate_mp.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace CodolGameServer
{
    // OLMOD(server-weapon-movement-owner): source-level owner corresponding to
    // persistent gclient fields copied by BO1/Ghosts/BO2
    // G_BuildWeaponState/G_SaveWeaponState. CODOL's removed server gclient
    // layout is unknown, so this is a semantic owner, not a native CODOL type.
    struct SvWeaponMovementClientState
    {
        std::int32_t damageTime{};
        float damagePitch{};
        float damageRoll{};
        std::int32_t weaponIdleTime{};
        float lastIdleFactor{};
        std::array<float, 3> baseAngles{};
        std::array<float, 3> baseOrigin{};
        std::array<float, 3> recoilAngles{};
        std::array<float, 3> recoilSpeed{};
        std::array<float, 3> swayAngles{};
        std::array<float, 3> swayOrigin{};
        std::array<float, 3> swayViewAngles{};

        bool operator==(const SvWeaponMovementClientState &) const = default;
    };

    // OLMOD(server-weapon-movement-frame): per-command values owned outside the
    // persistent state. Native playerState owns shellshock index/time/duration
    // at confirmed CODOL offsets, but start/fade conversion remains guarded.
    struct SvWeaponMovementFrameInput
    {
        const SvNativePlayerState *playerState{};
        float xyspeed{};
        float frameTime{};
        std::int32_t time{};
        std::int32_t shellShockStart{};
        std::int32_t shellShockDuration{};
        std::int32_t shellShockFadeTime{ 3000 };
    };

    // CODREF(g_build_weapon_state): exact x86 CODOL viewState_t layout recovered
    // from CG_OffsetFirstPersonView 0x0051D3B0 and shared stage consumers. This
    // remains caller-owned and may enter native code only through the guard.
    //
    // CONFIRMED ON out.exe. The addresses above are 3.3.3.3's -- this file was
    // byte-identical to that tree and its comments were never re-derived -- but
    // every offset in it is right on this build, read off the two bound stages:
    //     sub_4353E0  ViewMovementDamageKickRva 0x0353E0
    //         a2[0] playerState   a2[1] damageTime   a2[2] time
    //         a2[3] damagePitch   a2[4] damageRoll
    //     sub_4355D0  ViewMovementIdleAnglesRva 0x0355D0
    //         a1[6] frameTime   a1[7] lastIdleFactor, read AND written
    //         **((int **)a1 + 8) -- weaponIdleTime dereferenced as a pointer
    struct SvViewMovementState
    {
        const void *playerState{};
        std::int32_t damageTime{};
        std::int32_t time{};
        float damagePitch{};
        float damageRoll{};
        float xyspeed{};
        float frameTime{};
        float lastIdleFactor{};
        std::int32_t *weaponIdleTime{};
    };

    // CODREF(g_build_weapon_state): exact x86 CODOL weaponState_t layout
    // recovered from CG_AddViewWeapon 0x0055C8A0 and 0x00430990..0x00431550.
    // Build points weaponIdleTime into the candidate owner for rollback.
    //
    // CONFIRMED ON out.exe, size and all five angle arrays, off the bound
    // stages themselves rather than the 3.3.3.3 addresses above:
    //     sub_434520  WeaponMovementBaseRva  0x034520   a2[0] playerState, a2[1] xyspeed
    //     sub_434680  WeaponMovementSwayRva  0x034680   a1[2] frameTime
    //         a1[21], a1[22]                            swayAngles  +0x54
    //         a1[33] + a1[34] - a1[4] vs a1[35]         shellShockStart +0x84,
    //             duration +0x88, time +0x10, fadeTime +0x8C -- and 0x8C + 4
    //             is the 0x90 the size assert claims
    //     sub_434E20  WeaponMovementBobRva   0x034E20
    //         a1[30], a1[31], a1[32]                    bobAngles   +0x78
    //     sub_434F90  SetWeaponMovementAnglesRva 0x034F90
    //         a1[9], a1[10], a1[11]                     baseAngles  +0x24
    //         a1[15], a1[16], a1[17]                    recoilAngles +0x3C
    struct SvWeaponMovementState
    {
        const void *playerState{};
        float xyspeed{};
        float frameTime{};
        float lastIdleFactor{};
        std::int32_t time{};
        std::int32_t damageTime{};
        float damagePitch{};
        float damageRoll{};
        std::int32_t *weaponIdleTime{};
        std::array<float, 3> baseAngles{};
        std::array<float, 3> baseOrigin{};
        std::array<float, 3> recoilAngles{};
        std::array<float, 3> recoilSpeed{};
        std::array<float, 3> swayAngles{};
        std::array<float, 3> swayOrigin{};
        std::array<float, 3> swayViewAngles{};
        std::array<float, 3> bobAngles{};
        std::int32_t shellShockStart{};
        std::int32_t shellShockDuration{};
        std::int32_t shellShockFadeTime{};
    };

    struct SvNativeWeaponMovementOutput
    {
        // OLMOD(server-gun-angle-publication): validated source projection of
        // native stage outputs; this is not a recovered CODOL structure.
        std::array<float, 3> viewAngles{};
        std::array<float, 3> weaponAngles{};
        float gunPitch{};
        float gunYaw{};

        bool operator==(const SvNativeWeaponMovementOutput &) const = default;
    };

    [[nodiscard]] bool SV_IsWeaponMovementOutputValid(
        const SvNativeWeaponMovementOutput &output);

    // CODREF(g_build_weapon_state): compile-time guards make the ABI evidence
    // executable and prevent silent layout drift in the x86 target.
    static_assert(sizeof(void *) != 4 || sizeof(SvViewMovementState) == 0x24);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvViewMovementState, damageTime) == 0x04);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvViewMovementState, lastIdleFactor) == 0x1C);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvViewMovementState, weaponIdleTime) == 0x20);
    static_assert(sizeof(void *) != 4 || sizeof(SvWeaponMovementState) == 0x90);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, lastIdleFactor) == 0x0C);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, weaponIdleTime) == 0x20);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, baseAngles) == 0x24);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, recoilAngles) == 0x3C);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, swayAngles) == 0x54);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, bobAngles) == 0x78);
    static_assert(sizeof(void *) != 4 ||
        offsetof(SvWeaponMovementState, shellShockStart) == 0x84);

    [[nodiscard]] bool SV_BuildViewMovementState(
        const SvWeaponMovementFrameInput &input,
        SvWeaponMovementClientState &clientState,
        SvViewMovementState &output);
    [[nodiscard]] bool SV_BuildWeaponMovementState(
        const SvWeaponMovementFrameInput &input,
        SvWeaponMovementClientState &clientState,
        SvWeaponMovementState &output);
    [[nodiscard]] bool SV_SaveWeaponMovementState(
        const SvWeaponMovementState &input,
        SvWeaponMovementClientState &clientState);
}
