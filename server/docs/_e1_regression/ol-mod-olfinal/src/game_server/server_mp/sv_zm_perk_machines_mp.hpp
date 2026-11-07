#pragma once
#include "sv_perks_mp.hpp"
#include "sv_map_triggers_mp.hpp"
#include <algorithm>
#include <bit>

namespace CodolGameServer {
inline constexpr std::uint32_t FactoryPerkArmor=1u<<22, FactoryPerkRevive=1u<<23,
    FactoryPerkReload=1u<<24, FactoryPerkRof=1u<<25;
inline constexpr std::uint32_t FactoryMachinePerks=
    FactoryPerkArmor|FactoryPerkRevive|FactoryPerkReload|FactoryPerkRof;

// OLMOD(factory_perk_machines): use reach is distinct from physical overlap.
// Factory cabinet collision keeps the observed approaches 6..11 units outside
// the authored volumes. Reconstructed 12-unit XY margin; keep original Z and
// hull/slab checks, restrict to the four machine identities, never enlarge doors.
inline const SvMapTrigger *SV_FactoryPerkTriggerAt(
    const SvMapTriggerTable *table,const std::array<float,3> &origin,
    const std::array<float,3> &midpoint,const std::array<float,3> &halfSize) {
    if(!table || table->mapName!="zm_factory_sh")return nullptr;
    auto reach=halfSize;reach[0]+=12;reach[1]+=12;
    const SvMapTrigger *best=nullptr;float bestDistance=0;
    for(const auto &t:table->triggers) {
        if(t.targetname!="zombie_vending" ||
            (t.noteworthy!="specialty_fastreload" && t.noteworthy!="specialty_quickrevive" &&
             t.noteworthy!="specialty_armorvest" && t.noteworthy!="specialty_rof"))continue;
        if(!SV_MapTriggerTouches(*table,t,origin,midpoint,reach))continue;
        const float x=origin[0]-t.origin[0],y=origin[1]-t.origin[1];
        const float distance=x*x+y*y;
        if(!best || distance<bestDistance){best=&t;bestDistance=distance;}
    }
    return best;
}

// OLMOD(factory_perk_machines): original Factory purchases cost 2/3/4 batteries
// with 0/1/2 machine perks. Sumpf's first Double Tap costs 2, second Quick Revive
// costs 3. Count ownership, not rounds or unrelated class perks. Fourth price 5
// extrapolates this observed progression; no recovered server script is claimed.
inline constexpr std::uint32_t SV_FactoryPerkPriceUnits(std::uint32_t perks) {
    return 2u + std::popcount(perks & FactoryMachinePerks);
}

// CODREF(actor_grounded_adapter): exact CODOL coPerkStatsTable IDs22..25 and
// coAbilityModifiersTable IDs1/23/104/105. Original snapshots corroborate reload
// slot1=2 and rate-of-fire slot12=2. Native404100 resolves the client slot;
// 54C230..54C284 projects abilities to playerstate. Server-owned modifiers have
// no float slot. Native weapon prediction consumes the replicated values.
inline void SV_ApplyFactoryPurchasedPerks(SvAbilityModifiers &a,std::uint32_t mask) {
    const auto add=[&](unsigned id,int slot,float initial,float delta) {
        const float base=SV_HasAbility(a,id)?a.resolvedValues[id]:initial;
        const float value=std::max(0.0f,base+delta);
        a.mask[id>>5]|=0x80000000u>>(id&31);
        a.resolvedValues[id]=value;
        if(slot>=0)a.values[slot]=value;
    };
    if(mask&FactoryPerkReload)add(1,1,1,1);
    if(mask&FactoryPerkRof)add(23,12,1,1);
    if(mask&FactoryPerkArmor)add(104,-1,100,150);
    // TODO(CODOL): native reviveRate is stored, but the cooperative downed-player
    // interaction owner is not recovered. Do not claim a working solo self-revive.
    if(mask&FactoryPerkRevive)add(105,-1,1,2);
}
}
