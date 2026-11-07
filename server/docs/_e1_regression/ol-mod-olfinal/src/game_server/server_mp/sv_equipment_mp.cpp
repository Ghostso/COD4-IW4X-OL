#include "sv_equipment_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <utility>

namespace CodolGameServer
{
    // OLMOD(factory_offhand_reward): atomic replacement around the native PM
    // inventory layout; CODOL grant policy is not recovered (see research note).
    bool SV_ReplaceOffhandReward(SvPlayerState &playerState,
        SvResolvedEquipment &equipment, const std::size_t slot,
        const SvOffhandWeapon &replacement)
    {
        if (slot >= equipment.weapons.size() || !replacement.weaponAssetIndex ||
            !SV_IsEquipmentValid(equipment)) return false;
        auto nextEquipment = equipment;
        const auto old = equipment.weapons[slot];
        if (old.weaponAssetIndex == replacement.weaponAssetIndex) return false;
        nextEquipment.weapons[slot] = replacement;
        if (!SV_IsEquipmentValid(nextEquipment)) return false;
        auto next = playerState;
        // Reject aliases of unrelated inventory/ammo. This transaction cannot
        // consume another item's slot just because a definition shares indexes.
        if (std::ranges::any_of(next.heldWeapons, [&](const auto &entry) {
                return entry.weaponAssetIndex == replacement.weaponAssetIndex;
            }) || std::ranges::any_of(next.ammoClips, [&](const auto &entry) {
                return entry.clipIndex == replacement.clipIndex &&
                    entry.clipIndex != old.clipIndex;
            }) || std::ranges::any_of(next.ammoPools, [&](const auto &entry) {
                return entry.ammoIndex == replacement.ammoIndex &&
                    entry.ammoIndex != old.ammoIndex;
            })) return false;
        if (old.weaponAssetIndex)
        {
            const auto held = std::ranges::find(next.heldWeapons,
                old.weaponAssetIndex, &SvHeldWeaponState::weaponAssetIndex);
            const auto clip = std::ranges::find(next.ammoClips,
                old.clipIndex, &SvAmmoClipState::clipIndex);
            const auto pool = std::ranges::find(next.ammoPools,
                old.ammoIndex, &SvAmmoPoolState::ammoIndex);
            if (held == next.heldWeapons.end() || clip == next.ammoClips.end() ||
                pool == next.ammoPools.end()) return false;
            *held = {}; *clip = {}; *pool = {};
        }
        // Equip just the changed slot: re-equipping the complete equipment
        // loadout would silently refill the unchanged throwable.
        SvResolvedEquipment grant{};
        grant.weapons[slot] = replacement;
        if (!SV_EquipOffhandLoadout(next, grant)) return false;
        next.offhandWeaponSlotA = nextEquipment.weapons[0].weaponAssetIndex;
        next.offhandWeaponSlotB = playerState.offhandWeaponSlotB;
        next.offhandWeaponSlotC = nextEquipment.weapons[1].weaponAssetIndex;
        next.offhandWeaponAssetIndex = playerState.offhandWeaponAssetIndex == old.weaponAssetIndex
            ? replacement.weaponAssetIndex : playerState.offhandWeaponAssetIndex;
        if (!next.offhandWeaponAssetIndex)
            next.offhandWeaponAssetIndex = replacement.weaponAssetIndex;
        playerState = std::move(next);
        equipment = std::move(nextEquipment);
        return true;
    }

    bool SV_IsEquipmentValid(const SvResolvedEquipment &equipment)
    {
        for (const auto &weapon : equipment.weapons)
        {
            if (!weapon.weaponAssetIndex)
            {
                if (weapon != SvOffhandWeapon{}) return false;
                continue;
            }
            // CODREF(1649370): 429E10 indexes WeaponDef from each slot;
            // 42C510/421A70 consume the clip/ammo indexes. Wire domains are
            // 11-bit weapon/ammo, 11-bit clip with 2047 reserved, 9-bit count.
            if (weapon.weaponAssetIndex > 0x7FF || !weapon.ammoIndex ||
                weapon.ammoIndex > 0x7FF || !weapon.clipIndex ||
                weapon.clipIndex > 0x7FE || !weapon.clipCapacity ||
                weapon.clipCapacity > 0x1FF || !weapon.offhandClass ||
                !weapon.spawnCount || weapon.spawnCount > weapon.clipCapacity ||
                weapon.weaponName.empty()) return false;
        }
        const auto &a = equipment.weapons[0];
        const auto &b = equipment.weapons[1];
        return !a.weaponAssetIndex || !b.weaponAssetIndex ||
            (a.weaponAssetIndex != b.weaponAssetIndex && a.ammoIndex != b.ammoIndex &&
                a.clipIndex != b.clipIndex);
    }

    const SvOffhandWeapon *SV_FindOffhandWeapon(
        const SvResolvedEquipment &equipment, const std::uint16_t weaponAssetIndex)
    {
        if (!weaponAssetIndex) return nullptr;
        for (const auto &weapon : equipment.weapons)
            if (weapon.weaponAssetIndex == weaponAssetIndex) return &weapon;
        return nullptr;
    }

    bool SV_EquipOffhandLoadout(
        SvPlayerState &playerState, const SvResolvedEquipment &equipment)
    {
        if (!SV_IsEquipmentValid(equipment)) return false;
        auto next = playerState;
        for (const auto &weapon : equipment.weapons)
        {
            if (!weapon.weaponAssetIndex) continue;
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
            // Retail dm at commandTime45600: held slot2=906, flags=0,
            // ammo pool906 stock=0, clip906 right=1 left=0. BO1 699510 and
            // Ghosts14016A9E0 likewise add offhands to the held inventory.
            *held = { .weaponAssetIndex = weapon.weaponAssetIndex };
            *clip = { .clipIndex = static_cast<std::int16_t>(weapon.clipIndex),
                .count = {weapon.spawnCount, 0} };
            *pool = { .ammoIndex = weapon.ammoIndex, .count = 0 };
        }
        // CODREF(1649370): 429E10 /59E5A0 select slots A/B/C for
        // +frag/+smoke/+tact (0x4000/0x8000/0x10000). The profile's tactical
        // belongs to +tact; the older smoke slot is a separate input.
        next.offhandWeaponSlotA = equipment.weapons[0].weaponAssetIndex;
        next.offhandWeaponSlotB = 0;
        next.offhandWeaponSlotC = equipment.weapons[1].weaponAssetIndex;
        next.offhandWeaponAssetIndex = next.offhandWeaponSlotA
            ? next.offhandWeaponSlotA : next.offhandWeaponSlotC;
        playerState = std::move(next);
        return true;
    }
}
