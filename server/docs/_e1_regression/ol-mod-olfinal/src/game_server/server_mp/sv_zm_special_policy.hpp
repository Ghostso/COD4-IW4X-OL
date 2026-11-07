#pragma once
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace CodolGameServer {
// OLMOD(factory_special_reconstruction): explicit source policy, not recovered
// CODOL server scripts or native probabilities. Names/models are native assets.
enum class SvFactorySpecialKind : std::uint8_t {
    Ray, Tesla, FireTrap, FreezeTrap, ShockTrap, ShrinkTrap, Monkey, Ammo, Grenade, Flash, Smoke, Count
};
struct SvFactorySpecialEntry {
    SvFactorySpecialKind kind;
    std::string_view weapon, model;
    std::uint16_t weight;
    bool equipment;
};
// Native ordinary-grenade blast fields, kept outside all native/wire layouts.
struct SvFactorySpecialCombat {
    float radius{250};
    int innerDamage{100},outerDamage{};
    bool sticky{};
};
// Source-owned presentation resources, resolved by name once per map.
struct SvFactoryTrapFx {
    std::uint16_t model{};
    std::uint8_t bone{255};
    std::array<std::uint16_t,4> effects{}; // fire, freeze, shock, shrink
    std::uint16_t monkeyModel{},monkeyAnimation{},monkeySong{};
    std::uint8_t monkeyTree{};
};
struct SvFactorySpecialImpact {
    SvFactorySpecialKind kind{};
    std::array<float,3> origin{};
    std::uint16_t weapon{}, owner{};
    std::uint8_t ownerLife{};
    std::optional<std::uint16_t> directHit;
};
inline constexpr std::array<SvFactorySpecialEntry,8> FactoryReconstructedBoxPool{{
    {SvFactorySpecialKind::Ray,"ray_gun_zm","weapon_usa_ray_gun",10,false},
    {SvFactorySpecialKind::Tesla,"tesla_gun_zm","weapon_usa_tesla",10,false},
    {SvFactorySpecialKind::FireTrap,"trap_fire_zm","t5_tf_bomb_sh",15,true},
    {SvFactorySpecialKind::FreezeTrap,"trap_freeze_zm","t5_tz_bomb_sh",15,true},
    {SvFactorySpecialKind::ShockTrap,"trap_shock_zm","t5_ts_bomb_sh",15,true},
    {SvFactorySpecialKind::ShrinkTrap,"trap_shrink_zm","t5_tk_bomb_sh",15,true},
    // Monkey eligibility is reconstruction; native models/definitions exist,
    // but none of our five original recordings proves a final monkey offer.
    {SvFactorySpecialKind::Monkey,"zombie_cymbal_monkey","weapon_zombie_monkey_bomb",5,true},
    {SvFactorySpecialKind::Ammo,"","zombie_ammocan",15,false},
}};
// Visual preview weights are independent of award weights. The Tesla preview
// is deliberately rarer at the user's request; this is presentation policy.
[[nodiscard]] std::uint16_t SV_FactoryPreviewWeight(std::string_view name);
[[nodiscard]] const SvFactorySpecialEntry *SV_FactorySpecialEntry(std::string_view name);
// Selection accepts only capabilities whose complete gameplay owner is enabled.
// Weights renormalize after ownership/capability filtering; no silent substitutes.
[[nodiscard]] std::optional<std::size_t> SV_SelectFactorySpecialReward(
    std::span<const std::uint16_t> eligibleWeights, std::uint32_t random);
}
