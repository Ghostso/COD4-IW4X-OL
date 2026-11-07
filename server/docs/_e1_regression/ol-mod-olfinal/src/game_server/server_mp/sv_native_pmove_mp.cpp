#include "sv_native_pmove_mp.hpp"

#include <algorithm>
#include <cstdlib>
#include <cmath>
#include <ranges>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(pmove): CODOL Pmove 0x0041E860 consumes the exact 0x12C
        // pmove_t and 0x2C usercmd_s layouts declared in the header. BO1
        // 0x004385F0 and Ghosts 0x140082BE0 confirm the shared movement
        // ownership and bounded touch-list responsibility without supplying
        // CODOL offsets.
        template <std::size_t Size>
        [[nodiscard]] bool finiteVector(const std::array<float, Size> &values)
        {
            return std::ranges::all_of(values, [](const float value) {
                return std::isfinite(value);
            });
        }
    }

    SvNativeUserCmd SV_ToNativeUserCmd(const UserCmd &command)
    {
        return {
            .commandTime = command.commandTime,
            .buttons = command.buttons,
            .angles = {
                command.angles[0],
                command.angles[1],
                command.angles[2],
            },
            .weapon = command.weapon,
            .offHandIndex = command.offHandIndex,
            .lastWeaponAltModeSwitch = command.lastWeaponAltModeSwitch,
            .forwardMove = command.forwardMove,
            .rightMove = command.rightMove,
            .conditionalAngle = command.conditionalAngle,
            .conditionalByte = command.conditionalByte,
            .conditionalElevenBits = command.conditionalElevenBits,
            .selectedLocation = command.selectedLocation,
            .selectedDirection = command.selectedDirection,
        };
    }

    std::string_view SV_NativePmoveFailureName(
        const SvNativePmoveFailure failure)
    {
        switch (failure)
        {
        case SvNativePmoveFailure::None: return "none";
        case SvNativePmoveFailure::InvalidBinding: return "invalid_binding";
        case SvNativePmoveFailure::InvalidCommand: return "invalid_command";
        case SvNativePmoveFailure::WrongThread: return "wrong_thread";
        case SvNativePmoveFailure::ReentrantCall: return "reentrant_call";
        case SvNativePmoveFailure::HandlerSlotBusy: return "handler_slot_busy";
        case SvNativePmoveFailure::AnimConditionInstallFailed:
            return "anim_condition_install_failed";
        case SvNativePmoveFailure::NonIncreasingCommandTime:
            return "non_increasing_native_command_time";
        case SvNativePmoveFailure::SliceLimitExceeded:
            return "slice_limit_exceeded";
        case SvNativePmoveFailure::CommandTimeNotAdvanced:
            return "native_command_time_not_advanced";
        case SvNativePmoveFailure::NativeException: return "native_exception";
        case SvNativePmoveFailure::HandlerRestoreFailed:
            return "handler_restore_failed";
        case SvNativePmoveFailure::TraceFailed: return "trace_failed";
        case SvNativePmoveFailure::AnimConditionRestoreFailed:
            return "anim_condition_restore_failed";
        case SvNativePmoveFailure::InvalidOutput: return "invalid_output";
        }
        return "unknown";
    }

    std::optional<SvNativePmoveOutput> SV_ReadNativePmoveOutput(
        const SvNativePmove &pmove)
    {
        // OLMOD(native-pmove-output-validation): native Pmove mutates this
        // caller-owned tail. Validate every field whose domain is proven
        // before the source player/entity transaction can observe it.
        // TODO(CODOL): prove proneChange, mantleDuration and viewChangeTime
        // sentinel/range semantics from CODOL write and consumer sites. Exit
        // when current i64 field xrefs or disassembly plus BO1/Ghosts control
        // flow establish their exact domains and fixed regressions cover them.
        if (pmove.numTouch < 0 || pmove.numTouch > 32 || pmove.handler != 0 ||
            pmove.mantleStarted > 1)
        {
            return std::nullopt;
        }

        SvNativePmoveOutput output{
            .numTouch = static_cast<std::uint32_t>(pmove.numTouch),
            .bounds = pmove.bounds,
            .xySpeed = pmove.xySpeed,
            .proneChange = pmove.proneChange,
            .mantleStarted = pmove.mantleStarted != 0,
            .mantleEndPosition = pmove.mantleEndPosition,
            .mantleDuration = pmove.mantleDuration,
            .viewChangeTime = pmove.viewChangeTime,
            .viewChange = pmove.viewChange,
            .torsoPitch = pmove.torsoPitch,
            .waistPitch = pmove.waistPitch,
        };
        for (std::size_t index = 0; index < output.numTouch; ++index)
        {
            const auto entityNum = pmove.touchEntities[index];
            if (entityNum < 0 || entityNum > 2047)
                return std::nullopt;
            output.touchEntities[index] = static_cast<std::uint32_t>(entityNum);
        }
        if (!SV_IsNativePmoveOutputValid(output))
            return std::nullopt;
        return output;
    }

    bool SV_IsNativePmoveOutputValid(const SvNativePmoveOutput &output)
    {
        if (output.numTouch > output.touchEntities.size() ||
            !finiteVector(output.bounds.midpoint) ||
            !finiteVector(output.bounds.halfSize) ||
            std::ranges::any_of(
                output.bounds.halfSize,
                [](const float value) { return value < 0.0f; }) ||
            !std::isfinite(output.xySpeed) || output.xySpeed < 0.0f ||
            !finiteVector(output.mantleEndPosition) ||
            !std::isfinite(output.viewChange) ||
            !std::isfinite(output.torsoPitch) ||
            !std::isfinite(output.waistPitch))
        {
            return false;
        }
        return std::ranges::all_of(
            output.touchEntities.begin(),
            output.touchEntities.begin() + output.numTouch,
            [](const std::uint32_t entityNum) { return entityNum <= 2047; });
    }

}
