#pragma once
#include "sv_snapshot_mp.hpp"

namespace CodolGameServer {
inline constexpr std::uint32_t FactoryAmmoHoldMilliseconds = 2000;

// OLMOD(factory_ammo): reconstructed server owner; original Sumpf records a
// two-second native size animation and a one-battery purchase on completion.
struct SvFactoryAmmoHold {
    std::uint32_t trigger{}, generation{}, startedAt{}, lastSeen{};
    bool active{}, completed{};

    bool update(bool held, bool eligible, std::uint32_t target,
                std::uint32_t life, std::uint32_t now) {
        if (!held) { *this = {}; return false; }
        if (generation != life) *this = {};
        if (completed) return false;
        if (!eligible) { active = false; return false; }
        if (!active || trigger != target || now - lastSeen > 500) {
            trigger = target; generation = life; startedAt = now; active = true;
        }
        lastSeen = now;
        if (now - startedAt < FactoryAmmoHoldMilliseconds) return false;
        active = false; completed = true;
        return true;
    }
};

inline std::array<SvHudElem, 2> SV_BuildFactoryAmmoHud(
    const SvFactoryAmmoHold &hold, std::uint32_t now,
    const std::array<std::uint16_t, 2> &materials) {
    std::array<SvHudElem, 2> result{};
    if (!hold.active || now - hold.lastSeen > 500 || !materials[0] || !materials[1])
        return result;
    // CODREF(actor_grounded_adapter): original Sumpf337750..339750; exact HUD
    // descriptors23..26 feed IDA538510/5385C0 width/height interpolation.
    auto &fill = result[0];
    fill.type = SvHudElemType::Icon; fill.origin = {-60,94,0};
    fill.targetEntNum = 2047; fill.materialIndex = materials[0];
    fill.width = 120; fill.height = 9; fill.color = 0xFFFFFFFF;
    fill.alignOrg = 1; fill.alignScreen = 0x99; fill.sort = -2;
    fill.setIconSizeAnimation(3,9,hold.startedAt,FactoryAmmoHoldMilliseconds);
    auto &background = result[1];
    background.type = SvHudElemType::Icon; background.origin = {0,94,0};
    background.targetEntNum = 2047; background.materialIndex = materials[1];
    background.width = 120; background.height = 9; background.color = 0xFFFFFFFF;
    background.alignOrg = 5; background.alignScreen = 0x99; background.sort = -3;
    return result;
}
}
