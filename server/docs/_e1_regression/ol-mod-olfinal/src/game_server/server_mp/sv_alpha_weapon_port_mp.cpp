#include "sv_alpha_weapon_port_mp.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::array<float, HitLocationCount> StandardHitLocations{
            1.0f, 1.4f, 1.4f, 1.0f, 1.0f, 1.0f, 1.0f,
            1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f,
            1.0f, 1.0f, 1.0f, 1.0f, 0.0f, 0.0f, 1.0f,
        };

        // CODREF(alpha_weapondef): each source value below is decoded from the
        // direct 0xC28 record in 0.0.2.2 ui_viewer_mp.zone. The field witnesses
        // and original offsets live in CODOL checkpoint 95 and
        // Tools/codol_alpha_weapon_stats.py.
        constexpr SvAlphaWeaponTuning FalTuning{
            0, 0, 2, 0, 1,
            60, 120, 1, 55, 35, 135,
            0, 600, 949, 0,
            { 5.0f, 4.5f, 4.0f, 9.0f, 8.0f, 7.0f },
            1000.0f, 1500.0f,
            StandardHitLocations,
            20, 79, true,
        };

        constexpr SvAlphaWeaponTuning ColtAnacondaTuning{
            0, 5, 2, 0, 1,
            18, 36, 1, 50, 35, 135,
            0, 449, 550, 0,
            { 2.0f, 1.5f, 1.0f, 4.0f, 3.0f, 2.0f },
            500.0f, 1250.0f,
            StandardHitLocations,
            6, 79, true,
        };

        constexpr SvAlphaWeaponTuning BarrettTuning{
            0, 1, 3, 0, 1,
            20, 30, 1, 70, 70, 135,
            0, 699, 1000, 1,
            { 10.0f, 9.5f, 9.0f, 15.0f, 14.0f, 13.0f },
            4000.0f, 5000.0f,
            { 1.0f, 1.5f, 1.5f, 1.5f, 1.5f, 1.5f, 1.45f,
              1.45f, 1.45f, 1.45f, 1.45f, 1.45f, 1.45f, 1.45f,
              1.45f, 1.45f, 1.45f, 1.45f, 0.0f, 0.0f, 5.0f },
            10, 50, true,
        };

        constexpr SvAlphaWeaponTuning TavorTuning{
            0, 0, 2, 0, 0,
            90, 180, 1, 40, 30, 135,
            0, 550, 829, 0,
            { 3.0f, 2.5f, 2.0f, 7.0f, 6.0f, 5.0f },
            1500.0f, 2000.0f, StandardHitLocations,
            30, 79, true,
        };

        constexpr SvAlphaWeaponTuning MasadaTuning{
            0, 0, 2, 0, 0,
            90, 180, 1, 30, 20, 135,
            0, 449, 750, 0,
            { 3.0f, 2.5f, 2.0f, 7.0f, 6.0f, 5.0f },
            1800.0f, 2300.0f, StandardHitLocations,
            30, 76, true,
        };

        constexpr SvAlphaWeaponTuning UziTuning{
            0, 3, 1, 0, 0,
            96, 192, 1, 30, 20, 135,
            0, 419, 800, 0,
            { 2.0f, 1.75f, 1.5f, 5.0f, 4.5f, 4.0f },
            750.0f, 1000.0f, StandardHitLocations,
            32, 63, true,
        };

        constexpr SvAlphaWeaponTuning M21Tuning{
            0, 1, 3, 0, 1,
            30, 60, 1, 70, 70, 135,
            0, 600, 949, 1,
            { 10.0f, 9.5f, 9.0f, 15.0f, 14.0f, 13.0f },
            4000.0f, 5000.0f,
            { 1.0f, 1.5f, 1.5f, 1.1f, 1.1f, 1.0f, 1.0f,
              1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f,
              1.0f, 1.0f, 1.0f, 1.0f, 0.0f, 0.0f, 1.0f },
            10, 50, true,
        };

        constexpr SvAlphaWeaponTuning GlockTuning{
            0, 3, 1, 0, 0,
            99, 198, 1, 30, 20, 135,
            0, 500, 550, 0,
            { 2.0f, 1.75f, 1.5f, 5.0f, 4.5f, 4.0f },
            300.0f, 500.0f, StandardHitLocations,
            33, 54, true,
        };

        constexpr SvAlphaWeaponTuning Beretta393Tuning{
            0, 5, 1, 0, 3,
            60, 120, 1, 40, 30, 135,
            0, 449, 550, 0,
            { 3.0f, 2.5f, 2.0f, 6.0f, 5.0f, 4.0f },
            500.0f, 750.0f, StandardHitLocations,
            20, 64, true,
        };

        constexpr SvAlphaWeaponTuning BerettaTuning{
            0, 5, 1, 0, 1,
            45, 90, 1, 40, 25, 135,
            0, 449, 550, 0,
            { 3.0f, 2.5f, 2.0f, 6.0f, 5.0f, 4.0f },
            550.0f, 800.0f, StandardHitLocations,
            15, 79, true,
        };

        constexpr SvAlphaWeaponTuning DesertEagleGoldTuning{
            0, 5, 2, 0, 1,
            21, 42, 1, 50, 30, 135,
            0, 449, 550, 0,
            { 2.0f, 1.5f, 1.0f, 4.0f, 3.0f, 2.0f },
            350.0f, 1200.0f, StandardHitLocations,
            7, 79, true,
        };

        // FAL and Colt Anaconda have measured OLfinal descendants. Eight
        // additional MW2-era names have explicit compatibility aliases in the
        // final registry; that is weaker lineage evidence, kept distinct here.
        // Barrett's presentation family is converted from the alpha metadata
        // and loose overlay. Its exact viewmodel_barrett_* animations and
        // complete viewmodel_barrett/weapon_m82 pair are patched onto a retained
        // CheyTac WeaponDef whose remaining pointer-bearing dependencies have
        // OLfinal ownership. The requested 0.0.2.2 presentation also publishes
        // its exact four-row Barrett base-body coWeapModels table.
        constexpr std::array Ports{
            SvAlphaWeaponPort{
                "fal_mp", "ff58_mp",
                SvAlphaWeaponLineage::MeasuredDescendant, FalTuning },
            SvAlphaWeaponPort{
                "coltanaconda_mp", "magnumncm_mp",
                SvAlphaWeaponLineage::MeasuredDescendant,
                ColtAnacondaTuning },
            SvAlphaWeaponPort{
                "tavor_mp", "tar21_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, TavorTuning },
            SvAlphaWeaponPort{
                "masada_mp", "acr_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, MasadaTuning },
            SvAlphaWeaponPort{
                "uzi_mp", "miniuzi_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, UziTuning },
            SvAlphaWeaponPort{
                "m21_mp", "m21ebr_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, M21Tuning },
            SvAlphaWeaponPort{
                "glock_mp", "g18_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, GlockTuning },
            SvAlphaWeaponPort{
                "beretta393_mp", "m93_mp",
                SvAlphaWeaponLineage::CompatibilityAlias,
                Beretta393Tuning },
            SvAlphaWeaponPort{
                "beretta_mp", "m9_mp",
                SvAlphaWeaponLineage::CompatibilityAlias, BerettaTuning },
            SvAlphaWeaponPort{
                "deserteaglegold_mp", "degold_mp",
                SvAlphaWeaponLineage::CompatibilityAlias,
                DesertEagleGoldTuning },
            SvAlphaWeaponPort{
                "barrett_heartbeat_mp", "cheytac_mp",
                SvAlphaWeaponLineage::ConvertedPresentation, BarrettTuning },
        };

        // CODREF(alpha_weapondef): OLfinal offsets, each independently named by
        // out.exe consumers in EngineBindings.cpp. Start ammo is the +0x7E0
        // member immediately before the two name pointers and the runtime ammo
        // index at +0x7EC, preserving the alpha +1476/+1480/+1484/+1488 order.
        constexpr std::size_t NameOffset = 0;
        constexpr std::size_t WeaponTypeOffset = 1416;
        constexpr std::size_t WeaponClassOffset = 1420;
        constexpr std::size_t WeaponPenetrateTypeOffset = 1424;
        constexpr std::size_t WeaponImpactTypeOffset = 1428;
        constexpr std::size_t WeaponFireTypeOffset = 1432;
        constexpr std::size_t WeaponStartAmmoOffset = 2016;
        constexpr std::size_t WeaponMaxAmmoOffset = 2040;
        constexpr std::size_t WeaponShotCountOffset = 2044;
        // CODREF(alpha_weapondef): C1 0x4D1830 reads alpha +0x5F8 as
        // melee damage; its retained OLfinal counterpart 0x4BC1D0 reads the
        // same field at +0x818 and passes it to the melee trace helper.
        constexpr std::size_t WeaponMeleeDamageOffset = 2072;
        constexpr std::size_t WeaponFireDelayOffset = 2088;
        constexpr std::size_t WeaponDropTimeOffset = 2188;
        constexpr std::size_t WeaponRaiseTimeOffset = 2192;
        constexpr std::size_t WeaponOverlayReticleOffset = 2348;
        constexpr std::size_t WeaponHipSpreadOffset = 2384;
        constexpr std::size_t WeaponDamageOffset = 3344;
        constexpr std::size_t WeaponDamageRangeOffset = 3368;
        constexpr std::size_t WeaponHitLocationMultipliersOffset = 3404;
        constexpr std::size_t WeaponClipSizeOffset = 3688;
        constexpr std::size_t WeaponFireTimeOffset = 3696;
        constexpr std::size_t WeaponAimDownSightOffset = 3806;
        constexpr std::size_t WeaponAmmoCountClipRelativeOffset = 3865;

        template <typename T>
        void write(std::span<std::byte> output, const std::size_t offset,
            const T &value) noexcept
        {
            std::memcpy(output.data() + offset, &value, sizeof(value));
        }

        bool valid(const SvAlphaWeaponTuning &tuning) noexcept
        {
            return tuning.weaponType >= 0 && tuning.weaponClass >= 0 &&
                tuning.penetrateType >= 0 && tuning.impactType >= 0 &&
                tuning.fireType >= 0 && tuning.startAmmo > 0 &&
                tuning.maxAmmo >= tuning.clipSize && tuning.shotCount > 0 &&
                tuning.damage >= 0 && tuning.minDamage >= 0 &&
                tuning.meleeDamage > 0 &&
                tuning.minDamage < std::numeric_limits<std::int32_t>::max() &&
                tuning.fireDelayMilliseconds >= 0 &&
                tuning.dropTimeMilliseconds >= 0 &&
                tuning.raiseTimeMilliseconds >= 0 && tuning.clipSize > 0 &&
                tuning.fireTimeMilliseconds > 0 &&
                std::isfinite(tuning.maxDamageRange) &&
                std::isfinite(tuning.minDamageRange) &&
                tuning.maxDamageRange > 0.0f &&
                tuning.minDamageRange > tuning.maxDamageRange &&
                tuning.minDamageRange <= StandardBulletRange &&
                std::ranges::all_of(tuning.hipSpread, [](const float value) {
                    return std::isfinite(value) && value >= 0.0f;
                }) &&
                std::ranges::all_of(
                    tuning.hitLocationMultipliers, [](const float value) {
                        return std::isfinite(value) && value >= 0.0f &&
                            value <= 20.0f;
                    });
        }
    }

    std::span<const SvAlphaWeaponPort> SV_AlphaWeaponPorts() noexcept
    {
        return Ports;
    }

    std::optional<std::uint16_t> SV_AlphaWeaponNetworkAssetIndex(
        const std::string_view name) noexcept
    {
        const auto port = std::ranges::find_if(
            Ports, [name](const SvAlphaWeaponPort &candidate) {
                return candidate.alphaName && candidate.alphaName == name;
            });
        if (port == Ports.end())
            return std::nullopt;
        return static_cast<std::uint16_t>(
            AlphaWeaponNetworkBaseIndex + std::distance(Ports.begin(), port));
    }

    std::uint32_t SV_StringTableHash(const std::string_view value) noexcept
    {
        std::uint32_t result{};
        for (const auto character : value)
        {
            const auto byte = static_cast<std::uint8_t>(character);
            const auto lower = byte >= 'A' && byte <= 'Z'
                ? static_cast<std::uint8_t>(byte - 'A' + 'a')
                : byte;
            result = result * 31u + lower;
        }
        return result;
    }

    bool SV_PatchAlphaWeaponDefinition(
        const std::span<std::byte> definition,
        const std::uint32_t persistentNameAddress,
        const SvAlphaWeaponTuning &tuning) noexcept
    {
        if (definition.size() != OlfinalWeaponDefSize ||
            !persistentNameAddress || !valid(tuning))
        {
            return false;
        }

        write(definition, NameOffset, persistentNameAddress);
        write(definition, WeaponTypeOffset, tuning.weaponType);
        write(definition, WeaponClassOffset, tuning.weaponClass);
        write(definition, WeaponPenetrateTypeOffset, tuning.penetrateType);
        write(definition, WeaponImpactTypeOffset, tuning.impactType);
        write(definition, WeaponFireTypeOffset, tuning.fireType);
        write(definition, WeaponStartAmmoOffset, tuning.startAmmo);
        write(definition, WeaponMaxAmmoOffset, tuning.maxAmmo);
        write(definition, WeaponShotCountOffset, tuning.shotCount);
        write(definition, WeaponMeleeDamageOffset, tuning.meleeDamage);
        write(definition, WeaponFireDelayOffset,
            tuning.fireDelayMilliseconds);
        write(definition, WeaponDropTimeOffset, tuning.dropTimeMilliseconds);
        write(definition, WeaponRaiseTimeOffset, tuning.raiseTimeMilliseconds);
        write(definition, WeaponOverlayReticleOffset, tuning.overlayReticle);
        std::memcpy(
            definition.data() + WeaponHipSpreadOffset,
            tuning.hipSpread.data(),
            sizeof(tuning.hipSpread));

        // CODREF(alpha_weapondef): alpha stores the classic two-endpoint
        // linear falloff. OLfinal consumes six points. Points 0 and 1 preserve
        // that exact line and inactive middle ranges remain zero. Two equal
        // floating-point endpoints can evaluate a few ulps below minDamage
        // and lose one point when the native routine truncates to int. The
        // guard endpoint therefore sits one unit beyond CODOL's maximum
        // ordinary bullet trace and is minDamage+1: every reachable distance
        // after minDamageRange remains in [minDamage,minDamage+1) and truncates
        // to the exact alpha value. Keeping the guard beyond the reachable
        // domain also avoids the retained routine's exact-final-range fallback
        // to damage[0].
        const std::array<std::int32_t, 6> damage{
            tuning.damage, tuning.minDamage, tuning.minDamage,
            tuning.minDamage, tuning.minDamage, tuning.minDamage + 1,
        };
        const std::array<float, 6> ranges{
            tuning.maxDamageRange, tuning.minDamageRange,
            0.0f, 0.0f, 0.0f, StandardBulletRange + 1.0f,
        };
        std::memcpy(definition.data() + WeaponDamageOffset,
            damage.data(), sizeof(damage));
        std::memcpy(definition.data() + WeaponDamageRangeOffset,
            ranges.data(), sizeof(ranges));
        std::memcpy(
            definition.data() + WeaponHitLocationMultipliersOffset,
            tuning.hitLocationMultipliers.data(),
            sizeof(tuning.hitLocationMultipliers));
        write(definition, WeaponClipSizeOffset, tuning.clipSize);
        write(definition, WeaponFireTimeOffset, tuning.fireTimeMilliseconds);
        definition[WeaponAimDownSightOffset] =
            tuning.aimDownSight ? std::byte{ 1 } : std::byte{};

        // Alpha maxAmmo is already an absolute round count. Keeping a source
        // descendant's clip-relative flag would multiply it by clipSize in
        // both the retained game and EngineBindings' validated projection.
        definition[WeaponAmmoCountClipRelativeOffset] = std::byte{};
        return true;
    }
}
