#pragma once

#include "qcommon/net_chan_mp.hpp"
#include "sv_collision_mp.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

namespace CodolGameServer
{
    // CODREF(pmove): CODOL usercmd_s=0x2C and pmove_t=0x12C are confirmed by
    // CG_PredictPlayerState/Pmove/PmoveSingle/PM_SetPitchValues read-write
    // sites. Static assertions below are the native x86 ABI gate.
    //
    // CHECKED ON 1649370 AND UNCHANGED -- recorded because "identical to the
    // 3.3.3.3 tree" is a suspicion, and the way to retire one is to check it,
    // not to leave it ambiguous. Pmove is A 0x41E860 / C 0x41DCD0 (each called
    // from exactly one site, and each calling PmoveSingle from exactly one),
    // and the two walk their pmove_t with the SAME displacements: 0x00, 0x04,
    // 0x08, 0x0C, 0x1E, 0x28, 0x60 and 0x128. That last one is the final dword
    // of a 0x12C struct, and 0x1E is cmd + 0x1A = forwardMove, so both layouts
    // held. Every displacement that DID move between the two profiles is a
    // playerState offset reached through pmove_t's first member -- 0x2A8/0x2AC
    // -> 0x30C/0x310 and 0x28/0x2C/0x30 -> 0x3C/0x40/0x44 -- which the netfield
    // tables agree with, so the differences corroborate section 34 rather than
    // contradicting this.
    struct SvNativeUserCmd
    {
        std::uint32_t commandTime{};
        std::uint32_t buttons{};
        std::array<std::uint32_t, 3> angles{};
        std::uint16_t weapon{};
        std::uint16_t offHandIndex{};
        std::uint16_t lastWeaponAltModeSwitch{};
        std::int8_t forwardMove{};
        std::int8_t rightMove{};
        float conditionalAngle{};
        std::uint8_t conditionalByte{};
        std::uint8_t padding21{};
        std::uint16_t conditionalElevenBits{};
        std::array<std::uint8_t, 3> selectedLocation{};
        std::array<std::uint8_t, 2> selectedDirection{};
        std::array<std::uint8_t, 3> padding29{};

        bool operator==(const SvNativeUserCmd &) const = default;
    };

    static_assert(sizeof(SvNativeUserCmd) == 0x2C);
    static_assert(offsetof(SvNativeUserCmd, buttons) == 0x04);
    static_assert(offsetof(SvNativeUserCmd, angles) == 0x08);
    static_assert(offsetof(SvNativeUserCmd, weapon) == 0x14);
    static_assert(offsetof(SvNativeUserCmd, forwardMove) == 0x1A);
    static_assert(offsetof(SvNativeUserCmd, conditionalAngle) == 0x1C);

    struct SvNativePmove
    {
        std::byte *playerState{};
        SvNativeUserCmd cmd;
        SvNativeUserCmd oldcmd;
        std::int32_t traceMask{};
        std::int32_t numTouch{};
        std::array<std::int32_t, 32> touchEntities{};
        TraceBounds bounds;
        float xySpeed{};
        std::int32_t proneChange{};
        std::uint8_t mantleStarted{};
        std::array<std::uint8_t, 3> padding105{};
        std::array<float, 3> mantleEndPosition{};
        std::int32_t mantleDuration{};
        std::int32_t viewChangeTime{};
        float viewChange{};
        float torsoPitch{};
        float waistPitch{};
        std::uint8_t handler{};
        std::array<std::uint8_t, 3> padding129{};
    };

    static_assert(sizeof(void *) == 4, "CODOL native ABI requires x86");
    static_assert(sizeof(SvNativePmove) == 0x12C);
    static_assert(offsetof(SvNativePmove, cmd) == 0x004);
    static_assert(offsetof(SvNativePmove, oldcmd) == 0x030);
    static_assert(offsetof(SvNativePmove, traceMask) == 0x05C);
    static_assert(offsetof(SvNativePmove, numTouch) == 0x060);
    static_assert(offsetof(SvNativePmove, touchEntities) == 0x064);
    static_assert(offsetof(SvNativePmove, bounds) == 0x0E4);
    static_assert(offsetof(SvNativePmove, xySpeed) == 0x0FC);
    static_assert(offsetof(SvNativePmove, proneChange) == 0x100);
    static_assert(offsetof(SvNativePmove, mantleStarted) == 0x104);
    static_assert(offsetof(SvNativePmove, mantleEndPosition) == 0x108);
    static_assert(offsetof(SvNativePmove, mantleDuration) == 0x114);
    static_assert(offsetof(SvNativePmove, viewChangeTime) == 0x118);
    static_assert(offsetof(SvNativePmove, viewChange) == 0x11C);
    static_assert(offsetof(SvNativePmove, torsoPitch) == 0x120);
    static_assert(offsetof(SvNativePmove, waistPitch) == 0x124);
    static_assert(offsetof(SvNativePmove, handler) == 0x128);

    enum class SvNativePmoveFailure : std::uint32_t
    {
        None,
        InvalidBinding,
        InvalidCommand,
        WrongThread,
        ReentrantCall,
        HandlerSlotBusy,
        AnimConditionInstallFailed,
        NonIncreasingCommandTime,
        SliceLimitExceeded,
        CommandTimeNotAdvanced,
        NativeException,
        HandlerRestoreFailed,
        TraceFailed,
        AnimConditionRestoreFailed,
        InvalidOutput,
    };

    struct SvNativePmoveOutput
    {
        // OLMOD(native-pmove-output): validated source-side projection of the
        // native pmove_t output tail, not an additional native structure.
        SvNativePmoveFailure failure{};
        std::uint32_t numTouch{};
        std::array<std::uint32_t, 32> touchEntities{};
        TraceBounds bounds;
        float xySpeed{};
        std::int32_t proneChange{};
        bool mantleStarted{};
        std::array<float, 3> mantleEndPosition{};
        std::int32_t mantleDuration{};
        std::int32_t viewChangeTime{};
        float viewChange{};
        float torsoPitch{};
        float waistPitch{};

        bool operator==(const SvNativePmoveOutput &) const = default;
    };

    [[nodiscard]] SvNativeUserCmd SV_ToNativeUserCmd(const UserCmd &command);
    [[nodiscard]] std::string_view SV_NativePmoveFailureName(
        SvNativePmoveFailure failure);
    [[nodiscard]] bool SV_IsNativePmoveOutputValid(
        const SvNativePmoveOutput &output);
    [[nodiscard]] std::optional<SvNativePmoveOutput>
    SV_ReadNativePmoveOutput(const SvNativePmove &pmove);
}
