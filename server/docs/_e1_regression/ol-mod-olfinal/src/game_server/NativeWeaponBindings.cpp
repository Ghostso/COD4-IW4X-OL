#define NOMINMAX
#include <Windows.h>

#include "EngineBindings.hpp"
#include "server_mp/sv_snapshot_mp.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(fire_weapon): CODOL playerState_s producers/consumers confirm
        // these offsets; BO1/Ghosts names constrain semantics but do not supply
        // x86 layout. Unknown neighboring bytes remain opaque.
        // CODDIFF(1649370): THE SAME UNPORTED BLOCK AS NativeWeaponMovementBindings.cpp
        // -- a THIRD file holding playerState_s offsets, and byte-identical to the
        // 3.3.3.3 tree's copy of this file. Same struct, three files, one of them ported.
        // Values and evidence are stated once, in NativeWeaponMovementBindings.cpp.
        constexpr std::size_t EFlagsOffset = 0x104;
        constexpr std::size_t ViewAnglesOffset = 0x160;
        constexpr std::size_t LinkEntityOffset = 0x248;
        constexpr std::size_t CurrentWeaponOffset = 0x3F8;
        constexpr std::size_t WeaponPositionFractionOffset = 0x404;
        constexpr std::int32_t UnlinkedEntityNum = 2047;
        constexpr std::uint32_t TurretViewFlags = 0x0C00;

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

        bool invokePlayerEyePosition(
            const EngineBindings::BGGetPlayerEyePosition function,
            const SvNativePlayerState &playerState,
            const std::int32_t time,
            float *const origin)
        {
            // OLMOD(native-weapon-call-guard): retained client primitives can
            // fault when reconstructed server globals or inputs are incomplete.
            // SEH contains the source transaction but cannot roll native state
            // back after a mutating call.
            bool completed{};
            __try
            {
                function(-1, playerState.bytes.data(), origin, time);
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }

        // CODDIFF(1649370): THIS WAS THE WRONG FUNCTION, AND ITS ARGUMENTS WERE
        // BACKWARDS. `AnglesToQuaternionRva` 0x3853E0 is sub_7853E0, which reads its
        // angles through ESI and writes FOUR floats through EDX - an
        // angles-to-QUATERNION, not 3.3.3.3's nine-float AnglesToAxis 0x0062C1A0,
        // which does not exist on this build at all. With the registers the
        // other way round this read a zeroed axis buffer AS the angles and
        // stamped a quaternion over the caller's `fireAngles`, so every basis it
        // produced was three zero vectors and SV_IsWeaponFireBasisValid refused
        // it. Section 73f.
        //
        // What 1649370 has is AngleVectors, sub_767890: four STACK arguments,
        // __cdecl, three separate destinations. Quake-derived engines define
        // AnglesToAxis as AngleVectors with the SECOND row inverted, so this
        // returns the same (forward, LEFT, up) the callers below already expect.
        bool invokeAngleVectors(
            void *const function,
            const std::array<float, 3> &angles,
            std::array<float, 9> &axis)
        {
            // OLMOD(native-weapon-call-guard): AngleVectors is non-mutating on
            // its angle argument; this boundary converts a native exception into
            // candidate failure.
            const auto *const anglesData = angles.data();
            auto *const forwardData = axis.data();
            auto *const rightData = axis.data() + 3;
            auto *const upData = axis.data() + 6;
            bool completed{};
            __try
            {
                __asm
                {
                    push upData
                    push rightData
                    push forwardData
                    push anglesData
                    mov eax, function
                    call eax
                    add esp, 10h
                }
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            if (completed)
            {
                for (std::size_t component{ 3 }; component != 6; ++component)
                    axis[component] = -axis[component];
            }
            return completed;
        }

        void callBulletEndpos(
            void *const function,
            const float *const muzzleTrace,
            float *const end,
            std::uint32_t *const randomSeed,
            const float spread,
            float *const direction,
            const float *const forward,
            const float *const right,
            const float *const up,
            const float maxRange)
        {
            // CODREF(fire_weapon): 3.3.3.3's Bullet_Endpos 0x0055AEB0 uses the
            // custom ABI EDI=muzzleTrace, ESI=end, followed by seed, spread,
            // dir, forward, right, up and maxRange on the stack -- SEVEN.
            //
            // CODDIFF(1649370): sub_592230 READS TEN, and the three new ones are
            // all floats INSERTED into the middle. Section 75.
            //
            //   [ebp+08] uint32*  randomSeed     unchanged
            //   [ebp+0C] float    spread         unchanged slot
            //   [ebp+10] float    spread         <- NEW, a SECOND cone radius
            //   [ebp+14] float*   direction      was [ebp+10]
            //   [ebp+18] float    randomMinimum  <- NEW
            //   [ebp+1C] float    randomMaximum  <- NEW
            //   [ebp+20] float*   forward        was [ebp+14]
            //   [ebp+24] float*   right          was [ebp+18]
            //   [ebp+28] float*   up             was [ebp+1C]
            //   [ebp+2C] float    maxRange       was [ebp+20]
            //
            // EDI and ESI are unchanged -- sub_592230 still does `fld [edi]`
            // into `fstp [esi]`. Carrying the seven-argument form left the
            // callee reading forward, right, up and maxRange out of the
            // caller's own frame, and three uninitialised dwords as floats.
            //
            // Recovered from sub_592230 and its ordinary CG_FireWeapon call at
            // 0x595DF0: [0x0C,0x10] are radial angle bounds and [0x18,0x1C]
            // are azimuth bounds. The plain-bullet call passes [0,spread] and
            // [0,360]. The helper consumes them as lo+(hi-lo)*random. Both
            // DEG2RAD (0x00DE7FA0) and LCG scale 1/32768 (0x00DE7BD8) are
            // bit-identical to 3.3.3.3's.
            //
            // CODREF(weapon_firing_path): CG_FireWeapon 0x595DF0 passes
            // radiusAngleMinDeg=0 and radiusAngleMaxDeg=spread for an ordinary
            // bullet. sub_592230 linearly samples between those radii. Passing
            // spread for both values collapses the disc to its outer rim and
            // makes hip fire avoid the crosshair centre.
            const float spreadMinimum = 0.0f;
            const float randomMinimum = 0.0f;
            // flt_E57A74 at the same call site is 360.0f. A 90-degree maximum
            // confines every authoritative shot to one quadrant.
            const float randomMaximum = 360.0f;
            __asm
            {
                push edi
                push esi
                push maxRange
                push up
                push right
                push forward
                push randomMaximum
                push randomMinimum
                push direction
                push spread
                push spreadMinimum
                push randomSeed
                mov edi, muzzleTrace
                mov esi, end
                call function
                add esp, 40
                pop esi
                pop edi
            }
        }

        bool invokeBulletEndpos(
            void *const function,
            const SvBulletEndposRequest &request,
            SvBulletEndposResult &result)
        {
            // OLMOD(native-weapon-call-guard): operate on a copied seed/result
            // so a fault cannot publish a partial source end position.
            bool completed{};
            __try
            {
                result.randomSeed = request.randomSeed;
                callBulletEndpos(
                    function,
                    request.basis.muzzleTrace.data(),
                    result.end.data(),
                    &result.randomSeed,
                    request.spread,
                    result.direction.data(),
                    request.basis.forward.data(),
                    request.basis.right.data(),
                    request.basis.up.data(),
                    request.maxRange);
                completed = true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                completed = false;
            }
            return completed;
        }
    }

    std::optional<std::array<float, 3>> EngineBindings::getPlayerEyePosition(
        const SvNativePlayerState &playerState,
        const std::int32_t time) const
    {
        // CODREF(fire_weapon): CODOL BG_GetPlayerEyePosition 0x00414150 owns
        // origin, view height, bob, lean and minimum-height clamping. Its -1
        // linkedEntityContext is valid only for the unlinked player path.
        if (!valid() ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return std::nullopt;
        }

        const auto eFlags = readNativeValue<std::uint32_t>(
            playerState, EFlagsOffset);
        const auto linkEntity = readNativeValue<std::int32_t>(
            playerState, LinkEntityOffset);
        // TODO(CODOL): Add server-owned tag/link entity resolution before
        // accepting viewlocked or linked player states.
        if ((eFlags & TurretViewFlags) != 0 ||
            linkEntity != UnlinkedEntityNum)
            return std::nullopt;

        std::array<float, 3> origin{};
        if (!invokePlayerEyePosition(
                bgGetPlayerEyePosition_, playerState, time, origin.data()) ||
            !std::ranges::all_of(origin, [](const float value) {
                return std::isfinite(value);
            }))
        {
            return std::nullopt;
        }
        return origin;
    }

    std::optional<SvWeaponFireBasis>
        EngineBindings::buildServerWeaponFireBasis(
            const SvNativePlayerState &playerState,
            const SvWeaponAimState &aimState,
            const SvResolvedWeapon &weapon,
            const std::int32_t time) const
    {
        return buildServerFireBasis(playerState, aimState,
            weapon.weaponAssetIndex, weapon.weaponType, false, time);
    }

    std::optional<SvWeaponFireBasis> EngineBindings::buildServerOffhandFireBasis(
        const SvNativePlayerState &playerState,
        const SvWeaponAimState &aimState,
        const SvOffhandWeapon &weapon,
        const std::int32_t time) const
    {
        if (!weapon.offhandClass)
            return std::nullopt;
        // CODREF(1649370): offhand admission 429E10 requires WeaponDef type1.
        // A grenade is selected at +3E4 while +3F8 still names the held gun.
        return buildServerFireBasis(playerState, aimState,
            weapon.weaponAssetIndex, 1, true, time);
    }

    std::optional<SvWeaponFireBasis> EngineBindings::buildServerFireBasis(
        const SvNativePlayerState &playerState,
        const SvWeaponAimState &aimState,
        const std::uint16_t weaponAssetIndex,
        const std::uint8_t weaponType,
        const bool offhand,
        const std::int32_t time) const
    {
        // CODREF(fire_weapon): BO1 FireWeapon/G_CalcMuzzlePoints
        // 0x006978F0/0x00697760 and Ghosts FireWeapon/CalcMuzzlePoints
        // 0x140169280/0x1401690D0 establish eye position plus server-owned gun
        // pitch/yaw as the weaponParms basis. CODOL offsets and native helpers
        // below settle the actual x86 projection.
        if (!std::isfinite(aimState.gunPitch) ||
            !std::isfinite(aimState.gunYaw) ||
            !weaponAssetIndex ||
            weaponAssetIndex > EngineBindings::MaximumWeaponAssetIndex)
        {
            return std::nullopt;
        }

        const auto currentWeapon = readNativeValue<std::uint32_t>(
            playerState, offhand ? 0x3E4 : CurrentWeaponOffset);
        const auto weaponPositionFraction = readNativeValue<float>(
            playerState, WeaponPositionFractionOffset);
        const auto viewAngles = readNativeValue<std::array<float, 3>>(
            playerState, ViewAnglesOffset);
        const auto muzzleTrace = getPlayerEyePosition(playerState, time);
        if (currentWeapon != weaponAssetIndex || !muzzleTrace ||
            !std::isfinite(viewAngles[2]) ||
            !std::isfinite(weaponPositionFraction) ||
            weaponPositionFraction < 0.0f || weaponPositionFraction > 1.0f)
        {
            return std::nullopt;
        }

        const std::array fireAngles{
            aimState.gunPitch,
            aimState.gunYaw,
            viewAngles[2],
        };
        std::array<float, 9> axis{};
        if (!invokeAngleVectors(angleVectors_, fireAngles, axis))
            return std::nullopt;

        SvWeaponFireBasis basis{
            .weaponAssetIndex = weaponAssetIndex,
            .weaponType = weaponType,
            .weaponPositionFraction = weaponPositionFraction,
            .muzzleTrace = *muzzleTrace,
            .forward = { axis[0], axis[1], axis[2] },
            // CODDIFF(fire_weapon): CODOL AnglesToAxis 0x0062C1A0 stores the
            // left axis in row one, while weaponParms/Bullet_Endpos owns right.
            .right = { -axis[3], -axis[4], -axis[5] },
            .up = { axis[6], axis[7], axis[8] },
        };
        return SV_IsWeaponFireBasisValid(basis)
            ? std::optional{ basis }
            : std::nullopt;
    }

    std::optional<SvBulletEndposResult>
        EngineBindings::calculateBulletEndpos(
            const SvBulletEndposRequest &request) const
    {
        // CODREF(fire_weapon): validation and thread ownership surround the
        // retained CODOL Bullet_Endpos primitive rather than reimplementing its
        // trigonometry or random direction calculation in source.
        if (!valid() || !SV_IsBulletEndposRequestValid(request) ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return std::nullopt;
        }

        SvBulletEndposResult result{};
        if (!invokeBulletEndpos(bulletEndpos_, request, result) ||
            !finiteVector(result.end) || !finiteVector(result.direction))
        {
            return std::nullopt;
        }
        return result;
    }

    std::optional<float> EngineBindings::surfacePenetrationDepth(
        const std::uint16_t weaponAssetIndex,
        const std::uint8_t surfaceType) const
    {
        // CODREF(weapon_firing_path): out.exe sub_42EC00 is
        // BG_GetSurfacePenetrationDepth. It selects CODOL's loaded table using
        // the completed modular WeaponDef, including the special mode-9 table.
        constexpr std::size_t functionRva = 0x02EC00;
        if (!valid() || !weaponAssetIndex ||
            weaponAssetIndex > MaximumWeaponAssetIndex ||
            !surfaceType || surfaceType >= BulletSurfaceTypeCount ||
            gameThreadId_.load(std::memory_order_acquire) != GetCurrentThreadId())
        {
            return std::nullopt;
        }

        float depth = std::numeric_limits<float>::quiet_NaN();
        bool completed{};
        __try
        {
            const auto *const slot =
                reinterpret_cast<const std::uint8_t *const *>(
                    module_ + WeaponDefinitionsRva) + weaponAssetIndex;
            const auto *const definition = *slot;
            if (definition)
            {
                const auto surfaceFactor = reinterpret_cast<double(__cdecl *)(
                    const void *, std::int32_t)>(module_ + functionRva)(
                        definition, surfaceType);
                // OLFinal sub_5923C0 multiplies the material table by
                // WeaponDef+0xE78, then scales thickness loss by +0xE7C
                // (zero means 1.0). Return the equivalent effective depth so
                // the source loop can retain damage -= thickness / depth.
                const auto penetrationScale =
                    *reinterpret_cast<const float *>(definition + 3704);
                auto lossScale =
                    *reinterpret_cast<const float *>(definition + 3708);
                if (lossScale == 0.0f)
                    lossScale = 1.0f;
                depth = static_cast<float>(surfaceFactor) *
                    penetrationScale / lossScale;
                completed = true;
            }
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            completed = false;
        }
        return completed && std::isfinite(depth) && depth >= 0.0f &&
                depth <= MaximumWeaponDamageRange
            ? std::optional{ depth }
            : std::nullopt;
    }
}
