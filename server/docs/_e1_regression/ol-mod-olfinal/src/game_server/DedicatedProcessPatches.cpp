#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "DedicatedProcessPatches.hpp"
#include "EngineBindings.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <charconv>
#include <cstring>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::size_t SingleInstanceGuardRva = 0x37EE5A;
        constexpr std::size_t SingleInstanceNameRva = 0x9DBA14;
        constexpr std::size_t RelocatedAddressOffset = 2;
        constexpr std::size_t RelocatedAddressSize = 4;
        constexpr std::size_t BranchOpcodeOffset = 23;
        constexpr std::uint8_t ConditionalJumpOpcode = 0x75;
        constexpr std::uint8_t UnconditionalJumpOpcode = 0xEB;
        constexpr std::uint8_t NoOperationOpcode = 0x90;
        constexpr std::array<std::uint8_t, 25> SingleInstanceGuard{
            0x81, 0x3D, 0xC0, 0x80, 0x1F, 0x0E, 0xB7, 0x00,
            0x00, 0x00, 0x8B, 0x45, 0x08, 0x53, 0x56, 0x57,
            0x8B, 0x7D, 0x10, 0x89, 0x44, 0x24, 0x10, 0x75,
            0x2D,
        };
        constexpr auto ClientSingleInstanceName = std::to_array(
            "Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB30}}");
        constexpr auto DedicatedSingleInstanceName = std::to_array(
            "Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}");
        static_assert(
            ClientSingleInstanceName.size() == DedicatedSingleInstanceName.size());

        auto clientInstanceSingleInstanceName(const std::uint32_t instance)
        {
            auto result = ClientSingleInstanceName;
            result[result.size() - 4] = static_cast<char>('0' + instance);
            return result;
        }
        struct ClientFrameCall
        {
            std::size_t rva;
            std::array<std::uint8_t, 5> bytes;
        };
        constexpr std::array ClientFrameCalls{
            ClientFrameCall{
                0xFE650,
                { 0xE8, 0x6B, 0x43, 0x0C, 0x00 },
            },
            ClientFrameCall{
                0xFE695,
                { 0xE8, 0xE6, 0x43, 0x0C, 0x00 },
            },
            ClientFrameCall{
                0xFE6A9,
                { 0xE8, 0xD2, 0xF9, 0xFF, 0xFF },
            },
            ClientFrameCall{
                0xFE6B4,
                { 0xE8, 0x17, 0x72, 0xF7, 0xFF },
            },
        };
        constexpr std::size_t ClientFramePatchStartRva =
            ClientFrameCalls.front().rva;
        constexpr std::size_t ClientFramePatchEndRva =
            ClientFrameCalls.back().rva + ClientFrameCalls.back().bytes.size();
        constexpr std::size_t AudioDriverStartupCallRva = 0x0FD694;
        constexpr std::array<std::uint8_t, 5> AudioDriverStartupCall{
            0xE8, 0x77, 0x2F, 0x32, 0x00,
        };
        constexpr std::size_t FrontendStartupCallRva = 0x37F8B8;
        constexpr std::array<std::uint8_t, 5> FrontendStartupCall{
            0xE8, 0xC3, 0x81, 0xCB, 0xFF,
        };
        constexpr std::size_t FocusStartupSequenceRva = 0x37F8D8;
        constexpr std::array<std::uint8_t, 7> FocusStartupSequence{
            0x52, 0xFF, 0x15, 0x18, 0x38, 0x9D, 0x0E,
        };
        constexpr std::size_t FocusRelocatedAddressOffset = 3;
        constexpr std::size_t FocusRelocatedAddressSize = 4;
        struct AccessibilityStartupBranch
        {
            std::size_t rva;
            std::uint8_t displacement;
        };
        constexpr std::array AccessibilityStartupBranches{
            AccessibilityStartupBranch{ 0x37F816, 0x12 },
            AccessibilityStartupBranch{ 0x37F82F, 0x10 },
            AccessibilityStartupBranch{ 0x37F846, 0x11 },
        };
        constexpr std::size_t AccessibilityStartupPatchStartRva =
            AccessibilityStartupBranches.front().rva;
        constexpr std::size_t AccessibilityStartupPatchEndRva =
            AccessibilityStartupBranches.back().rva + 2;
        constexpr std::size_t CursorVisibilityCallRva = 0x7E01C4;
        constexpr std::array<std::uint8_t, 5> CursorVisibilityCall{
            0xE8, 0x67, 0xAC, 0xB9, 0xFF,
        };
        constexpr std::size_t InputFrameStartupCallRva = 0x0FD99C;
        constexpr std::array<std::uint8_t, 5> InputFrameStartupCall{
            0xE8, 0x9F, 0xD5, 0x27, 0x00,
        };

        enum class SingleInstanceGuardState
        {
            Original,
            Patched,
            LegacyBypass,
            Unexpected,
        };

        enum class ClientFramePatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class FrontendStartupPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class AudioStartupPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class FocusStartupPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class AccessibilityStartupPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class CursorVisibilityPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        enum class InputFrameStartupPatchState
        {
            Original,
            Patched,
            Unexpected,
        };

        struct WritableRegion
        {
            std::uint8_t *address;
            std::size_t size;
            bool enabled;
            DWORD oldProtection{};
        };

        SingleInstanceGuardState inspectSingleInstanceGuard(
            const std::span<const std::uint8_t> image)
        {
            if (SingleInstanceGuardRva > image.size() ||
                SingleInstanceGuard.size() > image.size() - SingleInstanceGuardRva)
            {
                return SingleInstanceGuardState::Unexpected;
            }

            const auto guard = image.subspan(
                SingleInstanceGuardRva, SingleInstanceGuard.size());
            for (std::size_t index = 0; index != SingleInstanceGuard.size(); ++index)
            {
                if (index == BranchOpcodeOffset ||
                    (index >= RelocatedAddressOffset &&
                        index < RelocatedAddressOffset + RelocatedAddressSize))
                {
                    continue;
                }
                if (guard[index] != SingleInstanceGuard[index])
                    return SingleInstanceGuardState::Unexpected;
            }
            if (SingleInstanceNameRva > image.size() ||
                ClientSingleInstanceName.size() >
                    image.size() - SingleInstanceNameRva)
            {
                return SingleInstanceGuardState::Unexpected;
            }
            const auto name = image.subspan(
                SingleInstanceNameRva, ClientSingleInstanceName.size());
            const auto hasClientName = std::memcmp(
                name.data(),
                ClientSingleInstanceName.data(),
                ClientSingleInstanceName.size()) == 0;
            const auto hasDedicatedName = std::memcmp(
                name.data(),
                DedicatedSingleInstanceName.data(),
                DedicatedSingleInstanceName.size()) == 0;
            if (!hasClientName && !hasDedicatedName)
                return SingleInstanceGuardState::Unexpected;
            if (guard[BranchOpcodeOffset] == UnconditionalJumpOpcode)
                return SingleInstanceGuardState::LegacyBypass;
            if (guard[BranchOpcodeOffset] != ConditionalJumpOpcode)
                return SingleInstanceGuardState::Unexpected;
            if (hasDedicatedName)
                return SingleInstanceGuardState::Patched;
            if (hasClientName)
                return SingleInstanceGuardState::Original;
            return SingleInstanceGuardState::Unexpected;
        }

        ClientFramePatchState inspectClientFrameCalls(
            const std::span<const std::uint8_t> image)
        {
            bool hasOriginal{};
            for (const auto &call : ClientFrameCalls)
            {
                if (call.rva > image.size() ||
                    call.bytes.size() > image.size() - call.rva)
                {
                    return ClientFramePatchState::Unexpected;
                }
                const auto actual = image.subspan(call.rva, call.bytes.size());
                if (std::ranges::equal(actual, call.bytes))
                {
                    hasOriginal = true;
                    continue;
                }
                if (!std::ranges::all_of(actual, [](const std::uint8_t byte) {
                        return byte == NoOperationOpcode;
                    }))
                {
                    return ClientFramePatchState::Unexpected;
                }
            }
            return hasOriginal
                ? ClientFramePatchState::Original
                : ClientFramePatchState::Patched;
        }

        FrontendStartupPatchState inspectFrontendStartupCall(
            const std::span<const std::uint8_t> image)
        {
            if (FrontendStartupCallRva > image.size() ||
                FrontendStartupCall.size() >
                    image.size() - FrontendStartupCallRva)
            {
                return FrontendStartupPatchState::Unexpected;
            }
            const auto actual = image.subspan(
                FrontendStartupCallRva, FrontendStartupCall.size());
            if (std::ranges::equal(actual, FrontendStartupCall))
                return FrontendStartupPatchState::Original;
            if (std::ranges::all_of(actual, [](const std::uint8_t byte) {
                    return byte == NoOperationOpcode;
                }))
            {
                return FrontendStartupPatchState::Patched;
            }
            return FrontendStartupPatchState::Unexpected;
        }

        AudioStartupPatchState inspectAudioDriverStartupCall(
            const std::span<const std::uint8_t> image)
        {
            if (AudioDriverStartupCallRva > image.size() ||
                AudioDriverStartupCall.size() >
                    image.size() - AudioDriverStartupCallRva)
            {
                return AudioStartupPatchState::Unexpected;
            }
            const auto actual = image.subspan(
                AudioDriverStartupCallRva, AudioDriverStartupCall.size());
            if (std::ranges::equal(actual, AudioDriverStartupCall))
                return AudioStartupPatchState::Original;
            if (std::ranges::all_of(actual, [](const std::uint8_t byte) {
                    return byte == NoOperationOpcode;
                }))
            {
                return AudioStartupPatchState::Patched;
            }
            return AudioStartupPatchState::Unexpected;
        }

        FocusStartupPatchState inspectFocusStartupSequence(
            const std::span<const std::uint8_t> image)
        {
            if (FocusStartupSequenceRva > image.size() ||
                FocusStartupSequence.size() >
                    image.size() - FocusStartupSequenceRva)
            {
                return FocusStartupPatchState::Unexpected;
            }
            const auto actual = image.subspan(
                FocusStartupSequenceRva, FocusStartupSequence.size());
            bool original = true;
            for (std::size_t index = 0;
                 index != FocusStartupSequence.size();
                 ++index)
            {
                if (index >= FocusRelocatedAddressOffset &&
                    index < FocusRelocatedAddressOffset +
                        FocusRelocatedAddressSize)
                {
                    continue;
                }
                if (actual[index] != FocusStartupSequence[index])
                {
                    original = false;
                    break;
                }
            }
            if (original)
                return FocusStartupPatchState::Original;
            if (std::ranges::all_of(actual, [](const std::uint8_t byte) {
                    return byte == NoOperationOpcode;
                }))
            {
                return FocusStartupPatchState::Patched;
            }
            return FocusStartupPatchState::Unexpected;
        }

        AccessibilityStartupPatchState inspectAccessibilityStartupBranches(
            const std::span<const std::uint8_t> image)
        {
            bool hasOriginal{};
            for (const auto &branch : AccessibilityStartupBranches)
            {
                if (branch.rva > image.size() || 2 > image.size() - branch.rva)
                    return AccessibilityStartupPatchState::Unexpected;
                if (image[branch.rva + 1] != branch.displacement)
                    return AccessibilityStartupPatchState::Unexpected;
                if (image[branch.rva] == ConditionalJumpOpcode)
                {
                    hasOriginal = true;
                    continue;
                }
                if (image[branch.rva] != UnconditionalJumpOpcode)
                    return AccessibilityStartupPatchState::Unexpected;
            }
            return hasOriginal
                ? AccessibilityStartupPatchState::Original
                : AccessibilityStartupPatchState::Patched;
        }

        CursorVisibilityPatchState inspectCursorVisibilityCall(
            const std::span<const std::uint8_t> image)
        {
            if (CursorVisibilityCallRva > image.size() ||
                CursorVisibilityCall.size() >
                    image.size() - CursorVisibilityCallRva)
            {
                return CursorVisibilityPatchState::Unexpected;
            }
            const auto actual = image.subspan(
                CursorVisibilityCallRva, CursorVisibilityCall.size());
            if (std::ranges::equal(actual, CursorVisibilityCall))
                return CursorVisibilityPatchState::Original;
            if (std::ranges::all_of(actual, [](const std::uint8_t byte) {
                    return byte == NoOperationOpcode;
                }))
            {
                return CursorVisibilityPatchState::Patched;
            }
            return CursorVisibilityPatchState::Unexpected;
        }

        InputFrameStartupPatchState inspectInputFrameStartupCall(
            const std::span<const std::uint8_t> image)
        {
            if (InputFrameStartupCallRva > image.size() ||
                InputFrameStartupCall.size() >
                    image.size() - InputFrameStartupCallRva)
            {
                return InputFrameStartupPatchState::Unexpected;
            }
            const auto actual = image.subspan(
                InputFrameStartupCallRva, InputFrameStartupCall.size());
            if (std::ranges::equal(actual, InputFrameStartupCall))
                return InputFrameStartupPatchState::Original;
            if (std::ranges::all_of(actual, [](const std::uint8_t byte) {
                    return byte == NoOperationOpcode;
                }))
            {
                return InputFrameStartupPatchState::Patched;
            }
            return InputFrameStartupPatchState::Unexpected;
        }
    }

    bool patchDedicatedSingleInstanceBuffer(const std::span<std::uint8_t> image)
    {
        const auto state = inspectSingleInstanceGuard(image);
        if (state == SingleInstanceGuardState::Patched)
            return true;
        if (state != SingleInstanceGuardState::Original &&
            state != SingleInstanceGuardState::LegacyBypass)
            return false;
        std::memcpy(
            image.data() + SingleInstanceNameRva,
            DedicatedSingleInstanceName.data(),
            DedicatedSingleInstanceName.size());
        image[SingleInstanceGuardRva + BranchOpcodeOffset] =
            ConditionalJumpOpcode;
        return true;
    }

    bool patchClientInstanceSingleInstanceBuffer(
        const std::span<std::uint8_t> image,
        const std::uint32_t instance)
    {
        if (instance < 2 || instance > 9 ||
            SingleInstanceNameRva > image.size() ||
            ClientSingleInstanceName.size() >
                image.size() - SingleInstanceNameRva)
            return false;
        const auto instanceName = clientInstanceSingleInstanceName(instance);
        const auto currentName = image.subspan(
            SingleInstanceNameRva, instanceName.size());
        if (std::ranges::equal(currentName, instanceName))
            return true;
        if (inspectSingleInstanceGuard(image) !=
            SingleInstanceGuardState::Original)
            return false;
        std::memcpy(
            image.data() + SingleInstanceNameRva,
            instanceName.data(),
            instanceName.size());
        return true;
    }

    bool installClientInstanceSingleInstancePatch(const std::uint32_t instance)
    {
        if (instance < 2 || instance > 9)
            return false;
        auto *module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return false;
        const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return false;
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(
            module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->FileHeader.Machine != IMAGE_FILE_MACHINE_I386 ||
            nt->FileHeader.TimeDateStamp != EngineBindings::ExpectedTimestamp ||
            nt->OptionalHeader.SizeOfImage != EngineBindings::ExpectedImageSize)
        {
            return false;
        }
        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto instanceName = clientInstanceSingleInstanceName(instance);
        const auto currentName = image.subspan(
            SingleInstanceNameRva, instanceName.size());
        if (std::ranges::equal(currentName, instanceName))
            return true;
        if (inspectSingleInstanceGuard(image) !=
            SingleInstanceGuardState::Original)
            return false;
        DWORD oldProtection{};
        auto *name = module + SingleInstanceNameRva;
        if (!VirtualProtect(
                name,
                ClientSingleInstanceName.size(),
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            return false;
        }
        const auto patched =
            patchClientInstanceSingleInstanceBuffer(image, instance);
        if (patched)
            FlushInstructionCache(
                GetCurrentProcess(), name, ClientSingleInstanceName.size());
        DWORD ignored{};
        VirtualProtect(
            name, ClientSingleInstanceName.size(), oldProtection, &ignored);
        return patched;
    }

    std::optional<std::uint32_t> configuredClientInstance()
    {
        std::array<char, 8> value{};
        const auto size = GetEnvironmentVariableA(
            "OLMOD_CLIENT_INSTANCE", value.data(), value.size());
        if (!size)
            return 1;
        if (size >= value.size())
            return std::nullopt;
        std::uint32_t instance{};
        const auto parsed = std::from_chars(
            value.data(), value.data() + size, instance);
        if (parsed.ec != std::errc{} || parsed.ptr != value.data() + size ||
            instance < 1 || instance > 9)
        {
            return std::nullopt;
        }
        return instance;
    }

    bool patchDedicatedClientFrameBuffer(const std::span<std::uint8_t> image)
    {
        const auto state = inspectClientFrameCalls(image);
        if (state == ClientFramePatchState::Patched)
            return true;
        if (state != ClientFramePatchState::Original)
            return false;
        for (const auto &call : ClientFrameCalls)
        {
            std::fill_n(
                image.begin() + call.rva,
                call.bytes.size(),
                NoOperationOpcode);
        }
        return true;
    }

    bool patchDedicatedFrontendStartupBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectFrontendStartupCall(image);
        if (state == FrontendStartupPatchState::Patched)
            return true;
        if (state != FrontendStartupPatchState::Original)
            return false;
        std::fill_n(
            image.begin() + FrontendStartupCallRva,
            FrontendStartupCall.size(),
            NoOperationOpcode);
        return true;
    }

    bool patchDedicatedAudioStartupBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectAudioDriverStartupCall(image);
        if (state == AudioStartupPatchState::Patched)
            return true;
        if (state != AudioStartupPatchState::Original)
            return false;
        std::fill_n(
            image.begin() + AudioDriverStartupCallRva,
            AudioDriverStartupCall.size(),
            NoOperationOpcode);
        return true;
    }

    bool patchDedicatedFocusStartupBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectFocusStartupSequence(image);
        if (state == FocusStartupPatchState::Patched)
            return true;
        if (state != FocusStartupPatchState::Original)
            return false;
        std::fill_n(
            image.begin() + FocusStartupSequenceRva,
            FocusStartupSequence.size(),
            NoOperationOpcode);
        return true;
    }

    bool patchDedicatedAccessibilityStartupBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectAccessibilityStartupBranches(image);
        if (state == AccessibilityStartupPatchState::Patched)
            return true;
        if (state != AccessibilityStartupPatchState::Original)
            return false;
        for (const auto &branch : AccessibilityStartupBranches)
            image[branch.rva] = UnconditionalJumpOpcode;
        return true;
    }

    bool patchDedicatedCursorVisibilityBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectCursorVisibilityCall(image);
        if (state == CursorVisibilityPatchState::Patched)
            return true;
        if (state != CursorVisibilityPatchState::Original)
            return false;
        std::fill_n(
            image.begin() + CursorVisibilityCallRva,
            CursorVisibilityCall.size(),
            NoOperationOpcode);
        return true;
    }

    bool patchDedicatedInputFrameStartupBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto state = inspectInputFrameStartupCall(image);
        if (state == InputFrameStartupPatchState::Patched)
            return true;
        if (state != InputFrameStartupPatchState::Original)
            return false;
        std::fill_n(
            image.begin() + InputFrameStartupCallRva,
            InputFrameStartupCall.size(),
            NoOperationOpcode);
        return true;
    }

    DedicatedProcessPatchResult patchDedicatedProcessBuffer(
        const std::span<std::uint8_t> image)
    {
        const auto guardState = inspectSingleInstanceGuard(image);
        const auto clientFrameState = inspectClientFrameCalls(image);
        const auto frontendStartupState = inspectFrontendStartupCall(image);
        const auto focusStartupState = inspectFocusStartupSequence(image);
        const auto accessibilityStartupState =
            inspectAccessibilityStartupBranches(image);
        const auto cursorVisibilityState = inspectCursorVisibilityCall(image);
        const auto inputFrameStartupState = inspectInputFrameStartupCall(image);
        const auto audioStartupState = inspectAudioDriverStartupCall(image);
        if (guardState == SingleInstanceGuardState::Unexpected ||
            clientFrameState == ClientFramePatchState::Unexpected ||
            frontendStartupState == FrontendStartupPatchState::Unexpected ||
            focusStartupState == FocusStartupPatchState::Unexpected ||
            accessibilityStartupState ==
                AccessibilityStartupPatchState::Unexpected ||
            cursorVisibilityState == CursorVisibilityPatchState::Unexpected ||
            inputFrameStartupState == InputFrameStartupPatchState::Unexpected ||
            audioStartupState == AudioStartupPatchState::Unexpected)
        {
            return DedicatedProcessPatchResult::UnexpectedBytes;
        }
        if (guardState == SingleInstanceGuardState::Patched &&
            clientFrameState == ClientFramePatchState::Patched &&
            frontendStartupState == FrontendStartupPatchState::Patched &&
            focusStartupState == FocusStartupPatchState::Patched &&
            accessibilityStartupState ==
                AccessibilityStartupPatchState::Patched &&
            cursorVisibilityState == CursorVisibilityPatchState::Patched &&
            inputFrameStartupState == InputFrameStartupPatchState::Patched &&
            audioStartupState == AudioStartupPatchState::Patched)
        {
            return DedicatedProcessPatchResult::AlreadyPatched;
        }

        patchDedicatedSingleInstanceBuffer(image);
        patchDedicatedClientFrameBuffer(image);
        patchDedicatedFrontendStartupBuffer(image);
        patchDedicatedFocusStartupBuffer(image);
        patchDedicatedAccessibilityStartupBuffer(image);
        patchDedicatedCursorVisibilityBuffer(image);
        patchDedicatedInputFrameStartupBuffer(image);
        patchDedicatedAudioStartupBuffer(image);
        return DedicatedProcessPatchResult::Patched;
    }

    DedicatedProcessPatchResult installDedicatedProcessPatches()
    {
        auto *module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return DedicatedProcessPatchResult::UnsupportedHost;
        const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return DedicatedProcessPatchResult::UnsupportedHost;
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(
            module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->FileHeader.Machine != IMAGE_FILE_MACHINE_I386 ||
            nt->FileHeader.TimeDateStamp != EngineBindings::ExpectedTimestamp ||
            nt->OptionalHeader.SizeOfImage != EngineBindings::ExpectedImageSize)
        {
            return DedicatedProcessPatchResult::UnsupportedHost;
        }

        const std::span<std::uint8_t> image(
            module, nt->OptionalHeader.SizeOfImage);
        const auto guardState = inspectSingleInstanceGuard(image);
        const auto clientFrameState = inspectClientFrameCalls(image);
        const auto frontendStartupState = inspectFrontendStartupCall(image);
        const auto focusStartupState = inspectFocusStartupSequence(image);
        const auto accessibilityStartupState =
            inspectAccessibilityStartupBranches(image);
        const auto cursorVisibilityState = inspectCursorVisibilityCall(image);
        const auto inputFrameStartupState = inspectInputFrameStartupCall(image);
        const auto audioStartupState = inspectAudioDriverStartupCall(image);
        if (guardState == SingleInstanceGuardState::Patched &&
            clientFrameState == ClientFramePatchState::Patched &&
            frontendStartupState == FrontendStartupPatchState::Patched &&
            focusStartupState == FocusStartupPatchState::Patched &&
            accessibilityStartupState ==
                AccessibilityStartupPatchState::Patched &&
            cursorVisibilityState == CursorVisibilityPatchState::Patched &&
            inputFrameStartupState == InputFrameStartupPatchState::Patched &&
            audioStartupState == AudioStartupPatchState::Patched)
        {
            return DedicatedProcessPatchResult::AlreadyPatched;
        }
        if (guardState == SingleInstanceGuardState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedSingleInstanceBytes;
        if (clientFrameState == ClientFramePatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedClientFrameBytes;
        if (frontendStartupState == FrontendStartupPatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedFrontendStartupBytes;
        if (focusStartupState == FocusStartupPatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedFocusStartupBytes;
        if (accessibilityStartupState ==
            AccessibilityStartupPatchState::Unexpected)
        {
            return DedicatedProcessPatchResult::UnexpectedAccessibilityStartupBytes;
        }
        if (cursorVisibilityState == CursorVisibilityPatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedCursorVisibilityBytes;
        if (inputFrameStartupState == InputFrameStartupPatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedInputFrameStartupBytes;
        if (audioStartupState == AudioStartupPatchState::Unexpected)
            return DedicatedProcessPatchResult::UnexpectedAudioStartupBytes;

        constexpr auto clientFrameSize =
            ClientFramePatchEndRva - ClientFramePatchStartRva;
        constexpr auto accessibilityStartupSize =
            AccessibilityStartupPatchEndRva - AccessibilityStartupPatchStartRva;
        const auto patchGuard = guardState != SingleInstanceGuardState::Patched;
        const auto patchClientFrame =
            clientFrameState == ClientFramePatchState::Original;
        const auto patchFrontendStartup =
            frontendStartupState == FrontendStartupPatchState::Original;
        const auto patchFocusStartup =
            focusStartupState == FocusStartupPatchState::Original;
        const auto patchAccessibilityStartup = accessibilityStartupState ==
            AccessibilityStartupPatchState::Original;
        const auto patchCursorVisibility =
            cursorVisibilityState == CursorVisibilityPatchState::Original;
        const auto patchInputFrameStartup =
            inputFrameStartupState == InputFrameStartupPatchState::Original;
        const auto patchAudioStartup =
            audioStartupState == AudioStartupPatchState::Original;

        std::array regions{
            WritableRegion{ module + SingleInstanceGuardRva + BranchOpcodeOffset,
                1, patchGuard },
            WritableRegion{ module + SingleInstanceNameRva,
                DedicatedSingleInstanceName.size(), patchGuard },
            WritableRegion{ module + ClientFramePatchStartRva,
                clientFrameSize, patchClientFrame },
            WritableRegion{ module + AudioDriverStartupCallRva,
                AudioDriverStartupCall.size(), patchAudioStartup },
            WritableRegion{ module + FrontendStartupCallRva,
                FrontendStartupCall.size(), patchFrontendStartup },
            WritableRegion{ module + FocusStartupSequenceRva,
                FocusStartupSequence.size(), patchFocusStartup },
            WritableRegion{ module + AccessibilityStartupPatchStartRva,
                accessibilityStartupSize, patchAccessibilityStartup },
            WritableRegion{ module + CursorVisibilityCallRva,
                CursorVisibilityCall.size(), patchCursorVisibility },
            WritableRegion{ module + InputFrameStartupCallRva,
                InputFrameStartupCall.size(), patchInputFrameStartup },
        };
        std::size_t protectedRegionCount{};
        for (; protectedRegionCount != regions.size(); ++protectedRegionCount)
        {
            auto &region = regions[protectedRegionCount];
            if (!region.enabled)
                continue;
            if (!VirtualProtect(
                    region.address,
                    region.size,
                    PAGE_EXECUTE_READWRITE,
                    &region.oldProtection))
            {
                for (auto index = protectedRegionCount; index-- != 0;)
                {
                    auto &protectedRegion = regions[index];
                    if (!protectedRegion.enabled)
                        continue;
                    DWORD ignored{};
                    VirtualProtect(
                        protectedRegion.address,
                        protectedRegion.size,
                        protectedRegion.oldProtection,
                        &ignored);
                }
                return DedicatedProcessPatchResult::ProtectionFailed;
            }
        }

        auto *opcode = module + SingleInstanceGuardRva + BranchOpcodeOffset;
        auto *singleInstanceName = module + SingleInstanceNameRva;
        auto *audioStartup = module + AudioDriverStartupCallRva;
        auto *frontendStartup = module + FrontendStartupCallRva;
        auto *focusStartup = module + FocusStartupSequenceRva;
        auto *cursorVisibility = module + CursorVisibilityCallRva;
        auto *inputFrameStartup = module + InputFrameStartupCallRva;

        if (patchGuard)
        {
            std::memcpy(
                singleInstanceName,
                DedicatedSingleInstanceName.data(),
                DedicatedSingleInstanceName.size());
            *opcode = ConditionalJumpOpcode;
        }
        if (patchClientFrame)
        {
            for (const auto &call : ClientFrameCalls)
            {
                std::fill_n(
                    module + call.rva,
                    call.bytes.size(),
                    NoOperationOpcode);
            }
        }
        if (patchFrontendStartup)
        {
            std::fill_n(
                frontendStartup,
                FrontendStartupCall.size(),
                NoOperationOpcode);
        }
        if (patchAudioStartup)
        {
            std::fill_n(
                audioStartup,
                AudioDriverStartupCall.size(),
                NoOperationOpcode);
        }
        if (patchFocusStartup)
        {
            std::fill_n(
                focusStartup,
                FocusStartupSequence.size(),
                NoOperationOpcode);
        }
        if (patchAccessibilityStartup)
        {
            for (const auto &branch : AccessibilityStartupBranches)
                module[branch.rva] = UnconditionalJumpOpcode;
        }
        if (patchCursorVisibility)
        {
            std::fill_n(
                cursorVisibility,
                CursorVisibilityCall.size(),
                NoOperationOpcode);
        }
        if (patchInputFrameStartup)
        {
            std::fill_n(
                inputFrameStartup,
                InputFrameStartupCall.size(),
                NoOperationOpcode);
        }

        for (auto &region : regions)
        {
            if (region.enabled)
            {
                FlushInstructionCache(
                    GetCurrentProcess(), region.address, region.size);
            }
        }
        for (auto index = regions.size(); index-- != 0;)
        {
            auto &region = regions[index];
            if (!region.enabled)
                continue;
            DWORD ignored{};
            VirtualProtect(
                region.address, region.size, region.oldProtection, &ignored);
        }
        return DedicatedProcessPatchResult::Patched;
    }

    const char *dedicatedProcessPatchResultName(
        const DedicatedProcessPatchResult result)
    {
        switch (result)
        {
        case DedicatedProcessPatchResult::Patched:
            return "patched";
        case DedicatedProcessPatchResult::AlreadyPatched:
            return "already_patched";
        case DedicatedProcessPatchResult::UnsupportedHost:
            return "unsupported_host";
        case DedicatedProcessPatchResult::UnexpectedBytes:
            return "unexpected_bytes";
        case DedicatedProcessPatchResult::UnexpectedSingleInstanceBytes:
            return "unexpected_single_instance_bytes";
        case DedicatedProcessPatchResult::UnexpectedClientFrameBytes:
            return "unexpected_client_frame_bytes";
        case DedicatedProcessPatchResult::UnexpectedFrontendStartupBytes:
            return "unexpected_frontend_startup_bytes";
        case DedicatedProcessPatchResult::UnexpectedFocusStartupBytes:
            return "unexpected_focus_startup_bytes";
        case DedicatedProcessPatchResult::UnexpectedAccessibilityStartupBytes:
            return "unexpected_accessibility_startup_bytes";
        case DedicatedProcessPatchResult::UnexpectedCursorVisibilityBytes:
            return "unexpected_cursor_visibility_bytes";
        case DedicatedProcessPatchResult::UnexpectedInputFrameStartupBytes:
            return "unexpected_input_frame_startup_bytes";
        case DedicatedProcessPatchResult::UnexpectedAudioStartupBytes:
            return "unexpected_audio_startup_bytes";
        case DedicatedProcessPatchResult::ProtectionFailed:
            return "protection_failed";
        }
        return "unknown";
    }
}
