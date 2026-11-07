#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace CodolGameServer
{
    // OLMOD(weapon-fire-source-schema): these are typed source transaction
    // views, not binary declarations of CODOL weaponParms, WeaponDef, gentity,
    // or playerState. Native addresses and layouts stay inside EngineBindings.
    enum class SvPlayerHand : std::uint8_t
    {
        Right,
        Left,
    };

    constexpr std::uint8_t WeaponTypeBullet = 0;
    constexpr std::uint8_t WeaponClassSpread = 4;
    // CODREF(fire_weapon): CODOL retained fire uses 0x46000000 (8192.0f) for
    // the ordinary non-spread Bullet_Endpos range.
    constexpr float StandardBulletRange = 8192.0f;
    constexpr float MaximumWeaponDamageRange = 1000000.0f;
    constexpr std::size_t WeaponDamageCurvePointCount = 6;

    struct SvWeaponDamageCurve
    {
        std::array<std::int32_t, WeaponDamageCurvePointCount> damage{};
        std::array<float, WeaponDamageCurvePointCount> ranges{};

        bool operator==(const SvWeaponDamageCurve &) const = default;
    };

    struct SvBulletDamageInput
    {
        SvWeaponDamageCurve curve{};
        float distance{};
        float damageMultiplier{ 1.0f };
        float damageRangeScale{ 1.0f };

        bool operator==(const SvBulletDamageInput &) const = default;
    };

    struct SvWeaponAimState
    {
        float gunPitch{};
        float gunYaw{};

        bool operator==(const SvWeaponAimState &) const = default;
    };

    // Ordinary-player FireWeapon input available before spread,
    // bullet/projectile, and damage ownership have been recovered.
    struct SvWeaponFireBasis
    {
        std::uint16_t weaponAssetIndex{};
        std::uint8_t weaponType{};
        float weaponPositionFraction{};
        std::array<float, 3> muzzleTrace{};
        std::array<float, 3> forward{};
        std::array<float, 3> right{};
        std::array<float, 3> up{};

        bool operator==(const SvWeaponFireBasis &) const = default;
    };

    struct SvWeaponSpreadInput
    {
        float viewHeightCurrent{};
        float playerSizeScale{};
        float weaponPositionFraction{};
        float normalizedAimSpreadScale{};
        std::int32_t spreadOverride{};
        std::int32_t spreadOverrideState{};
        float hipSpreadStandMin{};
        float hipSpreadCrouchMin{};
        float hipSpreadProneMin{};
        float hipSpreadStandMax{};
        float hipSpreadCrouchMax{};
        float hipSpreadProneMax{};
        float adsSpread{};
        float perkSpreadScale{1.0f};

        bool operator==(const SvWeaponSpreadInput &) const = default;
    };

    struct SvWeaponSpreadResult
    {
        float minimum{};
        float maximum{};
        float firing{};

        bool operator==(const SvWeaponSpreadResult &) const = default;
    };

    struct SvBulletEndposRequest
    {
        std::uint32_t randomSeed{};
        float spread{};
        float maxRange{};
        SvWeaponFireBasis basis{};

        bool operator==(const SvBulletEndposRequest &) const = default;
    };

    struct SvBulletEndposResult
    {
        std::uint32_t randomSeed{};
        std::array<float, 3> end{};
        std::array<float, 3> direction{};

        bool operator==(const SvBulletEndposResult &) const = default;
    };

    struct SvBulletFirePlanInput
    {
        std::uint32_t commandTime{};
        SvPlayerHand hand{};
        std::uint8_t weaponType{};
        std::uint8_t weaponClass{};
        std::uint8_t penetrateType{};
        std::uint8_t shotCount{};
        SvWeaponDamageCurve damageCurve{};
        bool rifleBullet{};
        bool bulletExplosiveDamage{};

        bool operator==(const SvBulletFirePlanInput &) const = default;
    };

    struct SvBulletFirePlan
    {
        std::uint32_t randomSeed{};
        std::uint8_t shotCount{};
        std::uint8_t methodOfDeath{};
        float maxRange{};
        bool penetrate{};

        bool operator==(const SvBulletFirePlan &) const = default;
    };

    [[nodiscard]] bool SV_IsWeaponFireBasisValid(
        const SvWeaponFireBasis &basis);
    [[nodiscard]] bool SV_IsBulletEndposRequestValid(
        const SvBulletEndposRequest &request);
    [[nodiscard]] std::uint32_t SV_SeedBulletRandom(
        std::uint32_t commandTime,
        SvPlayerHand hand) noexcept;
    [[nodiscard]] bool SV_IsWeaponDamageCurveValid(
        const SvWeaponDamageCurve &curve);
    [[nodiscard]] std::optional<std::int32_t> SV_CalculateBulletDamage(
        const SvBulletDamageInput &input);
    [[nodiscard]] std::optional<SvBulletFirePlan> SV_BuildBulletFirePlan(
        const SvBulletFirePlanInput &input);
    [[nodiscard]] std::optional<SvWeaponSpreadResult> SV_CalculateWeaponSpread(
        const SvWeaponSpreadInput &input);
}
