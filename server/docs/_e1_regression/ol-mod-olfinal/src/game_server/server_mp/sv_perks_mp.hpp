#pragma once

#include <array>
#include <cstdint>

namespace CodolGameServer
{
    inline constexpr std::uint32_t SvAbilityModifierCount = 192;
    inline constexpr std::uint32_t SvAbilityScavenger = 2;
    inline constexpr std::uint32_t SvAbilityBulletSpreadScale = 6;
    inline constexpr std::uint32_t SvAbilityNoRadar = 18;
    inline constexpr std::uint32_t SvAbilityNoSentryGuns = 20;
    inline constexpr std::uint32_t SvAbilityRadarArrow = 24;
    inline constexpr std::uint32_t SvAbilityDetectExplosive = 30;
    inline constexpr std::uint32_t SvAbilityInvalidCounterUav = 35;
    inline constexpr std::uint32_t SvAbilityExplosivePaint = 37;
    inline constexpr std::uint32_t SvAbilityBulletPaint = 38;
    inline constexpr std::uint32_t SvAbilityDelayTriggeredExplosive = 43;
    inline constexpr std::uint32_t SvAbilityScramblerImmune = 56;
    inline constexpr std::uint32_t SvAbilitySideRolling = 80;
    inline constexpr std::uint32_t SvAbilityDelayClaymoreTime = 90;
    inline constexpr std::uint32_t SvAbilityArmorExplosiveDamageScale = 96;
    inline constexpr std::uint32_t SvAbilityGasMask = 99;
    inline constexpr std::uint32_t SvAbilityStunProtectionScale = 100;
    inline constexpr std::uint32_t SvAbilityFlashProtectionScale = 101;
    inline constexpr std::uint32_t SvAbilityReviveRate = 105;
    inline constexpr std::uint32_t SvAbilityDetectCrateTraps = 114;
    inline constexpr std::uint32_t SvAbilityAntiPaint = 128;
    inline constexpr std::uint32_t SvAbilityVictimNoDeadIcon = 131;
    inline constexpr std::uint32_t SvAbilityKillstreakShift = 140;
    inline constexpr std::uint32_t SvAbilityArmorRevive = 143;
    inline constexpr std::uint32_t SvAbilityEmpProtectionScale = 144;
    inline constexpr std::uint32_t SvAbilityCrateReroll = 145;
    inline constexpr std::uint32_t SvAbilityNoHelicopter = 150;
    inline constexpr std::uint32_t SvAbilityNoAirplane = 151;
    inline constexpr std::uint32_t SvAbilityNoHintWhenAiming = 182;
    inline constexpr std::uint32_t SvAbilitySideRollingExpert = 187;
    inline constexpr std::uint32_t SvAbilityRadarArrowFloatSlot = 13;
    inline constexpr float SvAbilityRadarArrowValue = 8.0f;
    inline constexpr std::uint32_t SvAbilityRadarArrowDurationMilliseconds = 10'000;

    struct SvAbilityModifiers
    {
        // CODREF(1649370): clientState+0x98/+0xB0 -> ps+0x590/+0x5A8
        // at 0x54C230..0x54C284. Ability bits are MSB first, unlike perks.
        std::array<std::uint32_t, 6> mask{};
        std::array<float, 36> values{};
        // The table has server-owned modifiers without a client float slot.
        // Keep their resolved default+delta values beside the network block;
        // only mask/values above are serialized or copied to native ps.
        std::array<float, SvAbilityModifierCount> resolvedValues{};
        float moveSpeedScale{ 1.0f };
        float fallDamageScale{ 1.0f };
        // Script-owned modifier 140 has no native network float slot.
        float killstreakShift{};

        bool operator==(const SvAbilityModifiers &) const = default;
    };

    [[nodiscard]] constexpr bool SV_HasAbility(
        const SvAbilityModifiers &abilities, const std::uint32_t modifierId)
    {
        return modifierId < SvAbilityModifierCount &&
            (abilities.mask[modifierId >> 5] &
                (0x80000000u >> (modifierId & 31))) != 0;
    }

    [[nodiscard]] constexpr float SV_AbilityValue(
        const SvAbilityModifiers &abilities,
        const std::uint32_t modifierId,
        const float fallback)
    {
        return SV_HasAbility(abilities, modifierId)
            ? abilities.resolvedValues[modifierId]
            : fallback;
    }

    constexpr void SV_ApplyRadarArrow(SvAbilityModifiers &abilities)
    {
        abilities.mask[SvAbilityRadarArrow >> 5] |=
            0x80000000u >> (SvAbilityRadarArrow & 31);
        abilities.values[SvAbilityRadarArrowFloatSlot] =
            SvAbilityRadarArrowValue;
        abilities.resolvedValues[SvAbilityRadarArrow] =
            SvAbilityRadarArrowValue;
    }

    constexpr void SV_ApplySideRollingExpert(SvAbilityModifiers &abilities)
    {
        if (!SV_HasAbility(abilities, SvAbilitySideRollingExpert))
            return;
        // CODREF(out.exe 0x41FF20): native pmove gates side rolling on
        // modSideRolling (80), while the selectable perk row carries only the
        // server-owned modSideRollingExpert (187). Retail's class description
        // says the expert item makes side roll occupy one perk slot. Preserve
        // 187 for the clientState row and grant the no-slot native capability
        // here, where a retail server script would translate the equipped row.
        abilities.mask[SvAbilitySideRolling >> 5] |=
            0x80000000u >> (SvAbilitySideRolling & 31);
    }

    // Kept outside SvResolvedLoadout: that struct is embedded in the persistent,
    // address-sensitive native player-state allocation (handoff section 184h).
    struct SvResolvedPerks
    {
        // Preserve the profile's catalog-ID-plus-one representation for UI dvars.
        std::array<std::uint32_t, 6> itemIds{};
        std::array<std::uint32_t, 3> bits{};
        SvAbilityModifiers abilities;

        bool operator==(const SvResolvedPerks &) const = default;
    };

    template <typename LookupPerkIndex>
    SvResolvedPerks SV_ResolveProfilePerks(
        const std::array<std::uint32_t, 6> &profileItems,
        LookupPerkIndex lookup)
    {
        SvResolvedPerks result{ .itemIds = profileItems };
        for (auto &item : result.itemIds)
        {
            if (item <= 1)
                continue;
            // CODREF(1649370): UI profile getter 0x50FD05 returns value - 1.
            // The input is the decoded profile integer, not a catalog item ID.
            const auto index = lookup(item - 1);
            if (!index || *index >= 96)
            {
                item = 1;
                continue;
            }
            result.bits[*index >> 5] |= 1u << (*index & 31);
        }
        return result;
    }
}
