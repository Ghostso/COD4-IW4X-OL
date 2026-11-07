#pragma once
#include "sv_snapshot_mp.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <map>
#include <utility>
#include <vector>

namespace CodolGameServer {
// OLMOD(factory-teleporters): match-owned reconstruction, never a native ABI.
// Three authored pads share one mainframe link. Any living teammate may finish
// it; a second pad cannot steal the active timer. Timers are explicit policy.
inline constexpr std::uint32_t FactoryLinkDuration=30000;
inline constexpr std::uint32_t FactoryTeleportCooldown=5000;
inline constexpr std::uint32_t FactoryTeleportPrice=1800; // recorded hint1.5 *1200
// BO1-DERIVED: patched Der Riese charge/black-room/cooldown timings.
// CODOL did not record paid travel; this owner requires a separate opt-in.
inline constexpr std::uint32_t FactoryTravelChargeMs=2000,FactoryTravelRoomMs=2000;
struct SvFactoryTraveler {
    std::uint32_t client{}; std::uint8_t generation{};
    std::array<float,3> departure{};
    float yaw{}; std::uint8_t room{};
};
struct SvFactoryTravel {
    std::uint32_t started{},roomStarted{};
    std::uint32_t payer{}; std::uint8_t payerGeneration{};
    std::size_t pad{}; std::array<float,3> padOrigin{};
    bool inRooms{},soundPlayed{};
    std::map<std::uint32_t,std::uint8_t> overlays;
    std::vector<SvFactoryTraveler> travelers;
    std::uint32_t nextReturnAttempt{},returnRetries{};
    [[nodiscard]] std::uint32_t chargeRemaining(std::uint32_t now) const {
        const auto elapsed=now-started;
        return elapsed<FactoryTravelChargeMs ? FactoryTravelChargeMs-elapsed : 0;
    }
    void enterRooms(std::uint32_t now){inRooms=true;roomStarted=now;}
    [[nodiscard]] bool roomReady(std::uint32_t now) const {
        return inRooms && now-roomStarted>=FactoryTravelRoomMs;
    }
};
struct SvFactoryTeleporterState {
    std::array<bool,3> links{};
    std::int8_t pendingPad{-1};
    std::uint32_t linkExpiry{},cooldown{};
    // Reconstructed recipient policy: only the initiating player/life sees the
    // stopwatch. Another living teammate can still complete the shared link.
    std::optional<std::pair<std::uint32_t,std::uint32_t>> linkClockOwner;
    bool packAPunchUnlocked{},packDoorOpening{};
    std::optional<std::uint32_t> poweredAt;
    bool packMachineStarted{},packMachineGlowing{};
    std::uint32_t packMachineStartedAt{};
    std::optional<std::pair<std::uint32_t,std::uint32_t>> packMachineHandle;
    std::uint32_t packDoorOpenStarted{};
    std::uint8_t packDoorCompletedLinks{};
    std::optional<std::pair<std::uint32_t,std::uint32_t>> packDoorHandle;
    std::array<float,3> packDoorClosedOrigin{},packDoorAngles{};
    std::vector<std::uint32_t> activeClients;
    std::optional<SvFactoryTravel> travel;
    bool roomFxAttempted{},roomFxReady{};
    std::array<std::optional<SvEntityHandle>,4> roomFx;
    [[nodiscard]] bool allPadsLinked() const {return links[0]&&links[1]&&links[2];}
    [[nodiscard]] bool pending(std::uint32_t now) const {return pendingPad>=0&&now<linkExpiry;}
    bool begin(std::size_t pad,std::uint32_t now,
        std::optional<std::pair<std::uint32_t,std::uint32_t>> owner=std::nullopt) {
        if(travel||pad>=links.size()||links[pad]||pending(now)||now<cooldown)return false;
        pendingPad=static_cast<std::int8_t>(pad);linkExpiry=now+FactoryLinkDuration;
        linkClockOwner=owner;return true;
    }
    bool complete(std::uint32_t now) {
        if(!pending(now))return false;
        links[static_cast<std::size_t>(pendingPad)]=true;clearPendingLink();return true;
    }
    bool showsClock(std::uint32_t client,std::uint32_t generation,std::uint32_t now) const {
        return pending(now) && linkClockOwner==std::optional{std::pair{client,generation}};
    }
    void clearPendingLink(){pendingPad=-1;linkExpiry=0;linkClockOwner.reset();}
};
struct SvFactoryTeleporterResources {
    // Resident asset names are native; their server-side schedule is reconstructed.
    std::uint16_t padStart{},beam{},linkSingle{},linkAll{},model{};
    std::uint8_t bone{255};
    std::uint16_t roomFlash{},coreChargeBeam{},coreChargeFlat{},coreBeam{},coreFlat{},travelSound{};
    std::uint16_t clockFace{},clockGlass{};
    std::uint16_t packModelOn{},packGlow{},packHum{};
    std::array<std::uint8_t,4> packGlowBones{255,255,255,255};
};
// CODREF(Factory344250/345250/345750; out.exe410BD0): gate accelerates
// downward for1s then travels at-35u/s for0.5s. Demo coordinates quantize;
// continuous17.5+17.5 displacement avoids introducing a rounding snap.
// Repeating this recorded step per linked pad is reconstructed scheduling.
// RECONSTRUCTION: final link continues at the same speed for another2s.
// Three35-unit steps leave the native model's top at165.58 above the114.5
// floor. Total175 lowering puts it at95.58, fully beneath the entrance.
// The available Factory demos do not capture this final open endpoint.
inline constexpr std::uint32_t SV_FactoryPackDoorDuration(bool finalLink) {
    return finalLink ? 3500 : 1500;
}
inline SvNativeTrajectory SV_FactoryPackDoorStep(const std::array<float,3> &closed,
    std::uint32_t began,std::uint32_t now,bool finalLink=false) {
    const auto duration=SV_FactoryPackDoorDuration(finalLink);
    auto base=closed;
    if(now-began<1000)return {7,static_cast<std::int32_t>(began),1000,base,{0,0,-35}};
    base[2]-=17.5f;
    if(now-began<duration)return {3,static_cast<std::int32_t>(began+1000),
        static_cast<std::int32_t>(duration-1000),base,{0,0,-35}};
    base[2]-=35.0f*(static_cast<float>(duration-1000)/1000.0f);
    return {0,static_cast<std::int32_t>(began+duration),0,base,{}};
}
// CODREF(factory-link-clock): original Factory317150 and1150350, native563043.
// The native client rotates the needle; the separate glass overlays it.
// OLMOD(factory-link-clock): recorded native face/glass and clock descriptors.
inline std::array<SvHudElem,2> SV_BuildFactoryLinkClock(std::uint32_t deadline,
    const SvFactoryTeleporterResources &resources) {
    if(!resources.clockFace || !resources.clockGlass)return {};
    std::array<SvHudElem,2> result{};
    result[0]={.type=SvHudElemType::ClockDown,.origin={10,20,0},
        .targetEntNum=EntityNumNone,.materialIndex=resources.clockFace,
        .width=96,.height=96,.color=0xFFFFFFFFu,.alignScreen=0x11,.sort=2};
    result[0].setClock(deadline,60000);
    result[1]={.type=SvHudElemType::Icon,.origin={10,20,0},
        .targetEntNum=EntityNumNone,.materialIndex=resources.clockGlass,
        .width=96,.height=96,.color=0xFFFFFFFFu,.alignScreen=0x11,.sort=3};
    return result;
}
}
