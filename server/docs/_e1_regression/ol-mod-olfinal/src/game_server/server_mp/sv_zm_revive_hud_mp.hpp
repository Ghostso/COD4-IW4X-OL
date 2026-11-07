#pragma once
#include "sv_zm_ammo_mp.hpp"

namespace CodolGameServer
{
    // CODREF(factory-revive-hud): Factory 60150/70850 and Sumpf547000/551300.
    // The marker changes material at treatment start; dimensions, tint, target
    // attachment and flags are recorded native fields, not a replacement image.
    inline SvHudElem SV_BuildZombieReviveMarker(std::uint16_t client,
        bool treating, const std::array<std::uint16_t, 2> &materials)
    {
        const auto material = materials[treating ? 1 : 0];
        if (!material) return {};
        return { .type=SvHudElemType::Waypoint, .targetEntNum=client,
            .materialIndex=material, .width=16, .height=16,
            .color=0xC833FFFFu, .value=1.0f, .flags=0x408 };
    }

    inline std::array<SvHudElem, 3> SV_BuildZombieTreatmentHud(
        const SvZombieDownedState &down, std::uint32_t now, std::uint32_t recipient,
        const std::array<std::uint16_t, 2> &materials)
    {
        std::array<SvHudElem, 3> result{};
        // OLMOD(revive-hud-recipient): treatment progress belongs to the helper.
        // The victim retains the downed overlay, not a second treatment bar.
        if (!down.reviver || *down.reviver!=recipient || down.bledOut ||
            now-down.lastSeen>500 || !down.duration ||
            !materials[0] || !materials[1]) return result;
        const auto bar=SV_BuildFactoryAmmoHud(SvFactoryAmmoHold{
            .startedAt=down.startedAt, .lastSeen=down.lastSeen, .active=true},now,materials);
        result[0]=bar[0]; result[1]=bar[1];
        result[0].setIconSizeAnimation(3,9,down.startedAt,
            static_cast<std::uint16_t>(down.duration));
        // Native NCS localized band:59 MPUI_REVIVING.
        // Centered caption above the white bar matches the reference capture;
        // the layout borrows retail's measured interaction-bar coordinates.
        result[2]={.type=SvHudElemType::Text,.origin={0,80,0},
            .targetEntNum=EntityNumNone,.color=0xFFFFFFFFu,.flags=1,
            .alignOrg=5,.alignScreen=0x99,.fontScale=0.9f,
            .label=59,.sort=-1};
        return result;
    }

    // Original successful zombie outros set the completion flag at+1500ms and
    // leave at+7500..7700ms. Applying that schedule to all-down defeat is an
    // explicit reconstruction; it must never select FFA podium/winner assets.
    inline constexpr std::uint32_t SvZombieResultsMilliseconds=1500;
    inline constexpr std::uint32_t SvZombieMatchEndedMilliseconds=7600;
    inline SvHudElem SV_BuildZombieGameOverHud()
    {
        // NCS localized952+462 = ZOMBIE_GAME_OVER on CODOL1649370.
        return {.type=SvHudElemType::Text,.origin={0,-60,0},
            .targetEntNum=EntityNumNone,.color=0xFFFFFFFFu,.flags=1,
            .alignOrg=5,.alignScreen=0x22,.fontScale=2.0f,.font=11,.label=462};
    }
}
