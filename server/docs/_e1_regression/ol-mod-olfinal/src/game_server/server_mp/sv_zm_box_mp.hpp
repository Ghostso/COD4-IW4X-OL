#pragma once
#include "sv_snapshot_mp.hpp"
#include <map>
#include <string>
#include <vector>

namespace CodolGameServer {
// OLMOD(factory_interactables): source-only, reset with the match. Resident
// definitions and models are resolved at map load, never in the actor tick.
struct SvFactoryBoxWeapon {
    std::uint16_t asset{};
    std::string name;
    std::array<float,3> bodyCenter{};
    std::uint16_t weight{1};
};
struct SvFactoryBoxSite {
    std::uint16_t trigger{};
    std::optional<SvEntityHandle> base,lid;
    std::array<float,3> origin{},angles{};
    std::optional<SvEntityHandle> rubble;
    // Authored weapon_spawn marker axes for the bear reward.
    // Modular firearm bodies use the lid's longitudinal axes above.
    std::array<float,3> rewardAngles{};
};
enum class SvFactoryBoxPhase { Closed, Rolling, Offer, Closing, Bear, Departing, Relocating };
enum class SvFactoryBoxRewardKind { Weapon, Ammo };
struct SvFactoryBoxRuntime {
    std::vector<SvFactoryBoxSite> sites;
    std::size_t active{};
    SvFactoryBoxPhase phase{SvFactoryBoxPhase::Closed};
    std::uint32_t owner{},started{},lastCycle{},seed{0x9e3779b9u};
    std::uint32_t previewSeed{1};
    std::uint8_t life{};
    std::uint16_t offer{};
    SvFactoryBoxRewardKind rewardKind{SvFactoryBoxRewardKind::Weapon};
    std::optional<SvEntityHandle> display;
    std::array<std::optional<SvEntityHandle>,2> effectCarriers{};
    bool initialized{};
    bool soundsRegistered{};
    std::array<std::uint16_t,3> teslaViewSlots{};
    std::uint32_t pulls{},moves{};
    bool bearRoll{};
    std::array<std::optional<SvEntityHandle>,2> movingPieces{};
    std::optional<SvEntityHandle> poof;
    std::uint32_t poofStarted{};
};
struct SvFactoryBoxResources {
    std::vector<SvFactoryBoxWeapon> weapons;
    // All published aliases, including duplicates omitted from the offer pool.
    std::map<std::uint16_t,std::uint16_t> weaponBases;
    std::uint16_t openAnimation{},closeAnimation{};
    std::uint8_t animationTree{};
    std::uint16_t effectModel{};
    std::array<std::uint16_t,2> effects{};
    std::uint8_t effectBone{255};
    std::uint16_t bearModel{},relocationEffect{};
    std::uint16_t ammoModel{};
    bool reconstructedPool{};
    std::array<std::uint16_t,3> teslaViewEffects{};
    std::map<std::uint16_t,SvOffhandWeapon> equipment;
};
// Explicit BO1 reference policy; not recovered CODOL drop probabilities.
[[nodiscard]] bool SV_FactoryBoxBearRoll(std::uint32_t paidPull,std::uint32_t moves,std::uint32_t random);
[[nodiscard]] std::size_t SV_FactoryBoxNextSite(std::size_t active,std::size_t count,std::uint32_t random);
using SvFactoryBoxFxCarriers=std::array<std::optional<SvEntityHandle>,2>;
[[nodiscard]] std::array<float,3> SV_FactoryBoxDisplayOrigin(
    const SvFactoryBoxResources &resources,std::uint16_t asset,const SvFactoryBoxSite &site);
[[nodiscard]] SvNativeTrajectory SV_FactoryBoxRise(
    const std::array<float,3> &origin,std::uint32_t started,std::uint32_t now);
[[nodiscard]] SvFactoryBoxFxCarriers SV_StartFactoryBoxFx(
    SvServerWorld &world,const SvFactoryBoxResources &resources,const SvFactoryBoxSite &site);
void SV_StopFactoryBoxFx(SvServerWorld &world,SvFactoryBoxFxCarriers &carriers);
[[nodiscard]] std::optional<std::uint16_t> SV_FactorySoundAliasSlot(
    const std::map<std::uint16_t,std::string> &slots,std::string_view name);
}
