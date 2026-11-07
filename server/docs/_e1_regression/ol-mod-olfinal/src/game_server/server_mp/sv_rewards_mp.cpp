#include "sv_rewards_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <utility>

namespace CodolGameServer
{
    bool SV_GrantUavWeapon(SvPlayerState &state, const SvRewardWeapon &weapon)
    {
        if (!weapon.weaponAssetIndex || weapon.weaponAssetIndex > 2047 ||
            !weapon.ammoIndex || weapon.ammoIndex > 2047 ||
            !weapon.clipIndex || weapon.clipIndex > 2046 ||
            !weapon.clipCapacity || weapon.clipCapacity > 511)
            return false;
        auto next = state;
        auto held = std::ranges::find_if(next.heldWeapons, [&](const auto &slot) {
            return slot.weaponAssetIndex == weapon.weaponAssetIndex;
        });
        if (held == next.heldWeapons.end())
            held = std::ranges::find_if(next.heldWeapons, [](const auto &slot) {
                return !slot.weaponAssetIndex;
            });
        auto clip = std::ranges::find_if(next.ammoClips, [&](const auto &slot) {
            return slot.clipIndex == weapon.clipIndex;
        });
        if (clip == next.ammoClips.end())
            clip = std::ranges::find_if(next.ammoClips, [](const auto &slot) {
                return !slot.clipIndex;
            });
        auto pool = std::ranges::find_if(next.ammoPools, [&](const auto &slot) {
            return slot.ammoIndex == weapon.ammoIndex;
        });
        if (pool == next.ammoPools.end())
            pool = std::ranges::find_if(next.ammoPools, [](const auto &slot) {
                return !slot.ammoIndex;
            });
        if (held == next.heldWeapons.end() || clip == next.ammoClips.end() ||
            pool == next.ammoPools.end()) return false;
        // CODREF(1649370): retail DM 642900 (killcam viewpoint client2)
        // carries held slot4 weapon1188 with flags/tail zero, clip1188 right1,
        // pool1188 reserve0, and action slot1 type1/weapon1188. This proves
        // the inventory shape, NOT a reward earned at this snapshot's clock.
        *held = { .weaponAssetIndex = weapon.weaponAssetIndex };
        *clip = { .clipIndex = static_cast<std::int16_t>(weapon.clipIndex), .count = {1, 0} };
        *pool = { .ammoIndex = weapon.ammoIndex, .count = 0 };
        next.rewardActionType = 1;
        next.rewardActionWeapon = weapon.weaponAssetIndex;
        state = std::move(next);
        return true;
    }
}
