#pragma once

#include <array>
#include <cstdint>
#include <cmath>
#include <optional>

namespace CodolGameServer
{
    struct SvPlayerState;
    // IW4 _killstreaks.gsc: lastEarnedStreak guards each life; the owned
    // list persists across death. Inventory publication is a separate retry.
    struct SvUavEarningState
    {
        std::uint32_t owned{};
        std::optional<std::uint8_t> life;
        std::optional<std::uint8_t> grantedLife;
        bool earnedThisLife{};
        void observe(std::uint8_t generation, bool alive, bool eligible,
            std::uint32_t streak, std::uint8_t threshold)
        {
            if (!alive) { life.reset(); grantedLife.reset(); earnedThisLife = false; return; }
            if (life != generation) { life = generation; grantedLife.reset(); earnedThisLife = false; }
            if (eligible && !earnedThisLife && streak >= threshold && owned != UINT32_MAX)
            {
                ++owned;
                earnedThisLife = true;
            }
        }
    };
    struct SvRewardWeapon
    {
        std::uint16_t weaponAssetIndex{};
        std::uint16_t ammoIndex{};
        std::uint16_t clipIndex{};
        std::uint16_t clipCapacity{};
        bool aimDownSight{};
        bool hasOverlayReticle{};
        bool operator==(const SvRewardWeapon &) const = default;
    };
    // Explicit one-charge grant. The earning owner must prevent repeated grants.
    // Publishes held weapon, clip, reserve and key4 action as one source change.
    [[nodiscard]] bool SV_GrantUavWeapon(SvPlayerState &state, const SvRewardWeapon &weapon);

    struct SvRewardDefinition
    {
        std::uint32_t runtimeId{};
        std::uint32_t normalCost{};
        std::uint32_t persistentCost{};
        bool operator==(const SvRewardDefinition &) const = default;
    };

    struct SvResolvedRewards
    {
        std::array<std::uint32_t, 3> profileItems{};
        std::array<SvRewardDefinition, 3> definitions{};
        bool persistentCosts{};
        bool operator==(const SvResolvedRewards &) const = default;
    };

    struct SvRewardSlot
    {
        std::uint8_t id{};
        std::uint8_t target{};
        bool operator==(const SvRewardSlot &) const = default;
    };

    inline std::optional<std::array<SvRewardSlot, 3>> SV_EquippedRewardTargets(
        const SvResolvedRewards &rewards, float shift)
    {
        if (!std::isfinite(shift) || std::floor(shift) != shift || shift < -100 || shift > 100)
            return std::nullopt;
        std::array<SvRewardSlot, 3> result{};
        for (std::size_t i = 0; i < result.size(); ++i)
        {
            const auto &definition = rewards.definitions[i];
            if (!definition.runtimeId) continue;
            const auto cost = rewards.persistentCosts ? definition.persistentCost : definition.normalCost;
            const auto target = static_cast<double>(cost) + shift;
            if (definition.runtimeId > 255 || target < 0 || target > 31)
                return std::nullopt;
            result[i] = {static_cast<std::uint8_t>(definition.runtimeId),
                static_cast<std::uint8_t>(target)};
        }
        return result;
    }

    // Resolve selection only. Character/perk modifiers and grant/spend state
    // are separate from these two measured native table cost columns.
    template <typename Lookup>
    std::optional<SvResolvedRewards> SV_ResolveProfileRewards(
        const std::array<std::uint32_t, 3> &items, Lookup lookup)
    {
        SvResolvedRewards result{ .profileItems = items };
        for (std::size_t slot = 0; slot < items.size(); ++slot)
        {
            if (items[slot] <= 1) continue;
            if (items[slot] > 65535) return std::nullopt;
            const auto reward = lookup(items[slot] - 1);
            // Runtime fields have 8-bit IDs and 5-bit targets. A failed lookup
            // must not become a valid zero-cost reward through atoi("").
            if (!reward || !reward->runtimeId || reward->runtimeId > 255 ||
                reward->normalCost > 31 || reward->persistentCost > 31)
                return std::nullopt;
            result.definitions[slot] = *reward;
        }
        return result;
    }
}
