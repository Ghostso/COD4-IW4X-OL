#pragma once

#include "sv_native_entitystate_mp.hpp"

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>

namespace CodolGameServer
{
    // OLMOD(native-characterinfo-view): confirmed CODOL offsets required by
    // the native DObj/animation bridge. The remainder stays opaque and this
    // does not claim to reconstruct the complete characterInfo_t layout.
    // CODDIFF(1649370): 0x3B8 on 3.3.3.3, 0x450 here -- 152 bytes larger. Both builds state
    // their own size outright, as the stride of the per-client characterInfo array: 3.3.3.3
    // multiplies by it at 0x518136 ("imul edi, edi, 0x3B8") a few instructions before the
    // animation projection, and this build at 0x53DE19 and 0x53DE34 ("imul ecx, ecx, 0x450")
    // in the same place. The multiply appears 342 times on 3.3.3.3 and 496 times here, so it
    // is the struct's real size and not a local constant.
    //
    // This drives ol-mod's own per-entity storage stride AND the buffer it hands
    // BG_UpdatePlayerDObj and BG_PlayerAnimation, both of which write through it -- so at 0x3B8
    // this server was handing the engine a buffer 152 bytes short of what it believes it owns.
    // Section 34b's playerState shortfall was the same defect in a different struct.
    constexpr std::size_t SvNativeCharacterInfoSize = 0x450;
    // CODDIFF(1649370): 0x160 AND 0x1A0 ARE 3.3.3.3's, AND SECTION 35j's THREE ROUTES ALL
    // MISSED IT. BG_PlayerAnimation is sub_40A960, ol-mod already calls it, and it takes the
    // characterInfo in EDI -- which this file's own thunk sets. It then names both frames
    // outright, twice each:
    //
    //     40A981  lea esi, [edi+17Ch]                 -> sub_408E70   clear
    //     40A992  lea esi, [edi+1BCh]                 -> sub_408E70   clear
    //     40A9D7  lea esi, [edi+17Ch]  ecx=[edi+258h] -> sub_408A70   run, LEGS
    //     40A9F8  lea esi, [edi+1BCh]  ecx=[edi+25Ch] -> sub_408A70   run, TORSO
    //
    // Both moved by the same +0x1C and they stay exactly SvNativeLerpFrameSize apart, which
    // is what makes it a relocation rather than two guesses. sub_408E70 confirms the frame's
    // own shape from the other side: it reads the animation number at frame+0x10 masked
    // `& 0x3FF`, and resets +0x10, +0x14 and +0x18 = 150.
    //
    // WHY NOTHING CAUGHT THIS. ol-mod installs the obfuscated accessor pair at
    // characterInfo + THIS offset, and SV_AreNativeLerpFrameAccessorsValid then decodes what
    // ol-mod itself wrote at the same place -- so a wrong offset is perfectly self-consistent
    // and the guard passes. The engine meanwhile runs its lerp frames 0x1C bytes further on,
    // where no accessor was ever installed. Section 35j predicted exactly this failure mode
    // and could not find the value; the answer was in a function this server already calls.
    constexpr std::size_t SvNativeCharacterInfoLegsLerpFrameOffset = 0x17C;
    constexpr std::size_t SvNativeCharacterInfoTorsoLerpFrameOffset = 0x1BC;
    constexpr std::size_t SvNativeLerpFrameSize = 0x40;
    // CONFIRMED ON out.exe, all three, out of sub_408A70 -- the same "run" function the
    // block above already names as the consumer of both frames. It decodes the pair twice
    // and in both directions, which pins the offsets, the CROSS-KEYING and the two cookies
    // in one read:
    //
    //     408deb  (dword_E60B3C ^ *(frame + 28) ^ (frame + 32))(source, frame + 36)
    //     408b9a  (dword_E60B40 ^ (frame + 28) ^ *(frame + 32))(frame + 36, dest)
    //     408c1c  (dword_E60B3C ^ (frame + 32) ^ *(frame + 28))  -- the SET again, hoisted
    //
    // 28 is 0x1C and 32 is 0x20, so the SET pointer is STORED at +0x1C and keyed on the
    // ADDRESS of +0x20 while the GET is stored at +0x20 and keyed on the address of +0x1C
    // -- exactly the cross that SV_DecodeNativeLerpFrameAccessors performs, and exactly
    // sec 43e's rule. The two cookies are dword_E60B3C and dword_E60B40, which are
    // NativeLerpFrameSetKeyRva and NativeLerpFrameGetKeyRva unchanged.
    //
    // AND THE THIRD OFFSET FALLS OUT OF THE SAME LINES: both accessors are handed
    // `frame + 36` as the buffer they read or write, so the protected value is at +0x24.
    // Nothing had to be assumed about its width or its role.
    //
    // The same function confirms the rest of the frame's head from the other side:
    // +0x10 is the animation number (compared against a5 and masked `& 0x3FF`), +0x14 is
    // the anim-def pointer whose +0x50 is a flag word and +0x44 a duration, +0x34 is the
    // lerp rate this function clamps to 0.1..4.0, and +0x38 is the timestamp it compares
    // against the global frame time. That accounts for the frame up to +0x3C and leaves
    // SvNativeLerpFrameSize = 0x40 with nothing unexplained.
    constexpr std::size_t SvNativeLerpFrameSetAccessorOffset = 0x1C;
    constexpr std::size_t SvNativeLerpFrameGetAccessorOffset = 0x20;
    constexpr std::size_t SvNativeLerpFrameProtectedValueOffset = 0x24;

    // The accessor initializer opens `cmp ebx, 0x20; ja <bail>`, so the selector it accepts is
    // 0..32 -- THIRTY-THREE, on both builds. ol-mod carried a 34th accessor pair that the
    // initializer cannot reach and then picked selectors modulo 34, so roughly one spawn in
    // seventeen asked for a selector the engine rejects outright. Everything that bounds a
    // selector reads this.
    constexpr std::uint32_t SvNativeLerpFrameSelectorCount = 33;

    // THE ANIM-SCRIPT BLOCK, AS BG_AnimScriptEvent READS IT.  These are here
    // and not buried in a .cpp because the death event's only failure signal is
    // a bare -1 and nothing in this project has ever been able to read the table
    // that produced it -- `grep -rn 25F80 src/` returned nothing before this.
    //
    // out.exe sub_407E10 (VA 0x00407E10) is BG_AnimScriptEvent, and it states
    // the whole addressing in five instructions:
    //
    //     407e14  mov  edx, dword_827F734          ; the anim-script block
    //     407e1c  imul ecx, 204h                   ; event * sizeof(animScript_t)
    //     407e2a  lea  eax, [ecx+edx+25F80h]       ; &scriptEvents[event]
    //     407e37  mov  edx, dword_827F730          ; the anim-condition block
    //     407e43  lea  ecx, [ecx+edx+0AF350h]      ; &characterInfo[clientNum]
    //
    // NOTE THE TWO DIFFERENT GLOBALS.  0x0827F734 carries the script table and
    // 0x0827F730 carries the characterInfo; this project installs only the
    // second (installServerAnimConditionStorage) and lets the first keep
    // whatever the last sub_407530 in the process left there.  They are the
    // same pointer in the engine's own flow -- CL_ParseGamestate sub_453760
    // writes 0x0827F730 at 0x00454BCF and hands the same value to
    // BG_AnimParseAnimScript at 0x00454CDF, which stores it into 0x0827F734 at
    // 0x00407551 -- but nothing enforces that here after initialisation.
    //
    // sub_407790, the set walker BG_AnimScriptEvent calls, opens
    // `mov eax,[eax]` / `test eax,eax` / `jle` on the first dword of the
    // animScript_t, so THE FIRST DWORD IS numItems and a value <= 0 makes the
    // walker return without writing its out-parameter -- which is the -1 the
    // caller pre-seeded at 0x00407E4B.  That is the reading no instrument in
    // this project has ever taken.
    constexpr std::size_t SvNativeAnimScriptStride = 0x204;
    constexpr std::size_t SvNativeAnimScriptEventTableOffset = 0x25F80;
    // BG_AnimParseAnimScript sub_407530 clears exactly ONE animScript_t at
    // block + 155004 = 0x25D7C (0x004075E6, `memset(a2 + 155004, 0, 0x204)`)
    // and that scrap script sits immediately before the event table:
    // 0x25D7C + 0x204 == 0x25F80.  Two unrelated instructions in two functions
    // agreeing on the boundary is what makes the event-table offset a
    // measurement rather than a guess, so the relationship is asserted rather
    // than merely commented.
    constexpr std::size_t SvNativeAnimScriptScrapScriptOffset = 0x25D7C;
    static_assert(
        SvNativeAnimScriptScrapScriptOffset + SvNativeAnimScriptStride ==
            SvNativeAnimScriptEventTableOffset,
        "the event table starts one animScript_t after the scrap script "
        "BG_AnimParseAnimScript clears at 0x25D7C");
    // out.exe's event NAME table at VA 0x00E60410 holds forty
    // {const char *, 0xFFFFFFFF} entries -- 0 PAIN, 1 DEATH, 2 FIREWEAPON,
    // 7 RAISEWEAPON ... 39 ADSTURRET_UNDEPLOY -- and terminates with
    // {0, 0xFFFFFFFF} at index 40.  Counted off the terminator, not assumed
    // from 3.3.3.3.
    constexpr std::size_t SvNativeAnimScriptEventCount = 40;
    // CODDIFF(1649370): THIS PROJECT CARRIED 38 AND THE BUILD SAYS 19.  The
    // condition NAME table at VA 0x00E60828 is nineteen
    // {const char *, 0xFFFFFFFF} entries -- 0 PLAYERANIMTYPE, 1 WEAPONCLASS,
    // 2 MOUNTED, 3 MOVETYPE, 4 MOVING_FORWARD, 5 CROUCHING, 6 FIRING,
    // 7 WEAPON_POSITION, 8 STRAFING, 9 PERK, 10 DAMAGETYPE, 11 HITLOCATION,
    // 12 HITDIRECTION, 13 AKIMBO, 14 RIOTSHIELDNEXT, 15 PLAYERANIMTYPEPRIMARY,
    // 16 FASTMANTLE, 17 SPECIES, 18 ATTACKNUM -- and terminates with
    // {0, 0xFFFFFFFF} at index 19 (VA 0x00E608C0).  The parallel condition-TYPE
    // table begins at VA 0x00E608C8, one entry later, and holds nineteen
    // entries too; sub_407790 indexes it as dword_E608C8[2 * conditionIndex].
    //
    // Counting 38 made the conditions diagnostic read nineteen real condition
    // slots plus nineteen slots of unrelated characterInfo (0x384..0x41C), so
    // its `nonzero=N/38` mixed the measurement with its own neighbours.  A
    // count that reads past its own table cannot say whether a condition is
    // missing.
    constexpr std::size_t SvNativeAnimConditionCount = 19;
    // sub_407790 reads `*(DWORD *)(characterInfo + 8 * conditionIndex + 748)`
    // and its partner at +752, so the array base is 748 = 0x2EC with an 8-byte
    // stride.
    constexpr std::size_t SvNativeAnimConditionBaseOffset = 0x2EC;
    constexpr std::size_t SvNativeAnimConditionStride = 8;

    // The byte offset of scriptEvents[event] inside the anim-script block, or
    // no value when `event` is not one of this build's forty events. Returning
    // an optional rather than clamping is deliberate: an out-of-range event is
    // a porting mistake and must not silently read a neighbouring script.
    [[nodiscard]] constexpr std::optional<std::size_t>
        SV_NativeAnimScriptEventOffset(const std::int32_t event) noexcept
    {
        if (event < 0 ||
            static_cast<std::size_t>(event) >= SvNativeAnimScriptEventCount)
        {
            return std::nullopt;
        }
        return SvNativeAnimScriptEventTableOffset +
            static_cast<std::size_t>(event) * SvNativeAnimScriptStride;
    }

    struct SvNativeLerpFrameAccessorTargets
    {
        std::uint32_t set{};
        std::uint32_t get{};
    };

    [[nodiscard]] bool SV_DecodeNativeLerpFrameAccessors(
        std::span<const std::byte> characterInfo,
        std::size_t frameOffset,
        std::uint32_t characterInfoAddress,
        std::uint32_t setKey,
        std::uint32_t getKey,
        SvNativeLerpFrameAccessorTargets &targets);

    [[nodiscard]] bool SV_AreNativeLerpFrameAccessorsValid(
        std::span<const std::byte> characterInfo,
        std::uint32_t characterInfoAddress,
        std::uint32_t moduleAddress,
        std::uint32_t setKey,
        std::uint32_t getKey);

    // CODOL's BG_PlayerAnimation reads its animation numbers from
    // characterInfo_t, unlike BO1's direct entityState_s input. The native
    // client callers project these fields immediately before each call.
    [[nodiscard]] bool SV_ProjectNativePlayerAnimationToCharacterInfo(
        const SvNativeEntityState &entityState,
        std::span<std::byte> characterInfo);
}
