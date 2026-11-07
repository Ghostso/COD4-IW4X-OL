#include "sv_native_characterinfo_mp.hpp"

#include <array>
#include <cstdint>
#include <cstring>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(bg_update_player_dobj): CODOL sub_518050/sub_518740 project
        // these entityState words into the 0x3B8 characterInfo immediately
        // before BG_PlayerAnimation 0x0040B5D0. BO1 BG_PlayerAnimation
        // 0x0040D9D0 and Ghosts 0x14006CEF0 confirm the shared animation/DObj
        // responsibility, but neither reference layout is reused here.
        // CODDIFF(1649370): all four moved with entityState_s, and this file kept
        // 3.3.3.3's copies even after sv_native_entitystate_mp.cpp was ported --
        // the same constant living in two places, corrected in one.
        // 0xD4/0xD8 are legsAnim/torsoAnim, which BG_PlayerStateToEntityState
        // settles independently: es 0xD4 -> 0xDC and 0xD8 -> 0xE0. The other two
        // follow the ET_PLAYER netfield alignment through the same +4 shift.
        constexpr std::size_t EntityAnimationState68Offset = 0x6C;
        constexpr std::size_t EntityAnimationState6COffset = 0x70;
        constexpr std::size_t EntityAnimationD4Offset = 0xDC;
        constexpr std::size_t EntityAnimationD8Offset = 0xE0;

        // CODDIFF(1649370): all six moved by +0x64, READ OFF THIS BUILD rather
        // than aligned or inferred -- they sit outside every netfield table, so
        // nothing but the code can answer.
        //
        // 3.3.3.3's projection is twelve instructions at 0x518166:
        //     mov ecx,[edx+0xD4] -> mov [edi+0x1F4],ecx
        //     mov eax,[edx+0xD8] -> mov [edi+0x1F8],eax
        //     fld [edx+0x6C]     -> fstp [edi+0x1FC]
        //     fld [edx+0x68]     -> fstp [edi+0x200]
        //     xor eax,eax           mov [edi+0x204],eax ; mov [edi+0x208],eax
        // Searching this build for that SHAPE -- anchored on the entityState
        // offsets section 34 already settled, since the destination is the
        // unknown -- finds exactly two sites, the same count 3.3.3.3 has, and
        // the clean one is 0x53DE4E:
        //     mov eax,[ebx+0xDC] -> mov [edi+0x258],eax
        //     mov ecx,[ebx+0xE0] -> mov [edi+0x25C],ecx
        //     fld [ebx+0x70]     -> fstp [edi+0x260]
        //     fld [ebx+0x6C]     -> fstp [edi+0x264]
        //     xor eax,eax           mov [edi+0x268],eax ; mov [edi+0x26C],eax
        //     call 0x40A960
        // That last instruction is BGPlayerAnimationRva, so edi is characterInfo
        // and there is nothing left to assume. The finder was calibrated on the
        // 3.3.3.3 image first, where it returned 0x1F4..0x208 at both of the two
        // call sites this file's own comment names.
        //
        // It also re-derives section 34's entityState port from the other side:
        // 0xD4->0xDC, 0xD8->0xE0, 0x6C->0x70 and 0x68->0x6C are exactly what the
        // netfield alignment predicted, arrived at independently.
        constexpr std::size_t CharacterAnimationD4Offset = 0x258;
        constexpr std::size_t CharacterAnimationD8Offset = 0x25C;
        constexpr std::size_t CharacterAnimationState6COffset = 0x260;
        constexpr std::size_t CharacterAnimationState68Offset = 0x264;
        constexpr std::size_t CharacterAnimationScratch0Offset = 0x268;
        constexpr std::size_t CharacterAnimationScratch1Offset = 0x26C;

        // CODDIFF(1649370): READ OUT OF THE BUILD'S OWN INITIALIZER, not shifted by a
        // delta. sub_403C70 is `cmp ebx, 0x20; ja bail; jmp [ebx*4 + 0x404004]`, and every
        // case XORs its SET and GET accessor addresses in as literals -- so the pairs are in
        // the code, in selector order, on whichever image you point at. That matters here:
        // the first 23 pairs moved by +0x10 between the builds and the last 10 did not move
        // at all, so a blanket delta would have been wrong for ten of thirty-three.
        //
        // The extractor was calibrated by re-deriving ol-mod's EXISTING 3.3.3.3 arrays off
        // the 3.3.3.3 image first: all 33 pairs came back exact, and the 34th entry ol-mod
        // carried turned out to be unreachable through the initializer on either build.
        //
        // These are the addresses SV_AreNativeLerpFrameAccessorsValid compares the decoded
        // pointers against, so 3.3.3.3's values did not merely mismatch -- they failed the
        // whole DObj/animation gate at stage lerp_frame_accessor_validation.
        constexpr std::array<std::uint32_t, 33> NativeLerpFrameSetAccessorRvas{
            0x001720, 0x001840, 0x001940, 0x001A40, 0x001B60, 0x001C80,
            0x001D80, 0x001EA0, 0x001FB0, 0x0020D0, 0x0021F0, 0x002310,
            0x002430, 0x002550, 0x002670, 0x002780, 0x0028A0, 0x0029C0,
            0x002AD0, 0x002BE0, 0x002CF0, 0x002E10, 0x002F30, 0x003050,
            0x003170, 0x003290, 0x0033A0, 0x0034A0, 0x0035C0, 0x0036E0,
            0x003800, 0x003910, 0x003A30,
        };
        constexpr std::array<std::uint32_t, 33> NativeLerpFrameGetAccessorRvas{
            0x0017C0, 0x0018D0, 0x0019D0, 0x001AE0, 0x001C00, 0x001D10,
            0x001E20, 0x001F40, 0x002050, 0x002170, 0x002290, 0x0023B0,
            0x0024D0, 0x0025F0, 0x002710, 0x002820, 0x002940, 0x002A60,
            0x002B70, 0x002C80, 0x002D90, 0x002EB0, 0x002FD0, 0x0030F0,
            0x003210, 0x003330, 0x003430, 0x003540, 0x003660, 0x003780,
            0x0038A0, 0x0039B0, 0x003AD0,
        };

        std::uint32_t readValue(
            const SvNativeEntityState &state,
            const std::size_t offset)
        {
            std::uint32_t value{};
            std::memcpy(&value, state.bytes.data() + offset, sizeof(value));
            return value;
        }

        void writeValue(
            const std::span<std::byte> destination,
            const std::size_t offset,
            const std::uint32_t value)
        {
            std::memcpy(destination.data() + offset, &value, sizeof(value));
        }
    }

    bool SV_DecodeNativeLerpFrameAccessors(
        const std::span<const std::byte> characterInfo,
        const std::size_t frameOffset,
        const std::uint32_t characterInfoAddress,
        const std::uint32_t setKey,
        const std::uint32_t getKey,
        SvNativeLerpFrameAccessorTargets &targets)
    {
        // CODDIFF(bg_update_player_dobj): CODOL protects the two lerp-frame
        // accessor pointers with frame-address-dependent XOR. This decoder is
        // a validation boundary for the retained native initializer, not a
        // portable BO1/Ghosts characterInfo implementation.
        if (frameOffset > characterInfo.size() ||
            characterInfo.size() - frameOffset < SvNativeLerpFrameSize)
        {
            return false;
        }

        std::uint32_t encodedSet{};
        std::uint32_t encodedGet{};
        std::memcpy(
            &encodedSet,
            characterInfo.data() + frameOffset +
                SvNativeLerpFrameSetAccessorOffset,
            sizeof(encodedSet));
        std::memcpy(
            &encodedGet,
            characterInfo.data() + frameOffset +
                SvNativeLerpFrameGetAccessorOffset,
            sizeof(encodedGet));
        const auto frameAddress = characterInfoAddress +
            static_cast<std::uint32_t>(frameOffset);
        targets.set = encodedSet ^ setKey ^
            (frameAddress + SvNativeLerpFrameGetAccessorOffset);
        targets.get = encodedGet ^ getKey ^
            (frameAddress + SvNativeLerpFrameSetAccessorOffset);
        return true;
    }

    bool SV_AreNativeLerpFrameAccessorsValid(
        const std::span<const std::byte> characterInfo,
        const std::uint32_t characterInfoAddress,
        const std::uint32_t moduleAddress,
        const std::uint32_t setKey,
        const std::uint32_t getKey)
    {
        for (const auto frameOffset : {
                 SvNativeCharacterInfoLegsLerpFrameOffset,
                 SvNativeCharacterInfoTorsoLerpFrameOffset })
        {
            SvNativeLerpFrameAccessorTargets targets{};
            if (!SV_DecodeNativeLerpFrameAccessors(
                    characterInfo,
                    frameOffset,
                    characterInfoAddress,
                    setKey,
                    getKey,
                    targets))
            {
                return false;
            }
            bool matched{};
            for (std::size_t index = 0;
                 index < NativeLerpFrameSetAccessorRvas.size();
                 ++index)
            {
                if (targets.set ==
                        moduleAddress + NativeLerpFrameSetAccessorRvas[index] &&
                    targets.get ==
                        moduleAddress + NativeLerpFrameGetAccessorRvas[index])
                {
                    matched = true;
                    break;
                }
            }
            if (!matched)
                return false;
        }
        return true;
    }

    bool SV_ProjectNativePlayerAnimationToCharacterInfo(
        const SvNativeEntityState &entityState,
        const std::span<std::byte> characterInfo)
    {
        if (characterInfo.size() < SvNativeCharacterInfoSize ||
            !SV_ReadNativeEntityState(entityState))
        {
            return false;
        }

        // Both CODOL callers, sub_518050 and sub_518740, perform this exact
        // projection before BG_PlayerAnimation. The +0x68/+0x6C semantics are
        // still opaque, so preserve their native words without speculative
        // naming. The final two fields are caller-owned scratch and reset each
        // frame before optional client-only animation shadowing.
        writeValue(
            characterInfo,
            CharacterAnimationD4Offset,
            readValue(entityState, EntityAnimationD4Offset));
        writeValue(
            characterInfo,
            CharacterAnimationD8Offset,
            readValue(entityState, EntityAnimationD8Offset));
        writeValue(
            characterInfo,
            CharacterAnimationState6COffset,
            readValue(entityState, EntityAnimationState6COffset));
        writeValue(
            characterInfo,
            CharacterAnimationState68Offset,
            readValue(entityState, EntityAnimationState68Offset));
        writeValue(characterInfo, CharacterAnimationScratch0Offset, 0);
        writeValue(characterInfo, CharacterAnimationScratch1Offset, 0);
        return true;
    }
}
