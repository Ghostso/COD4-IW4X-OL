#include "sv_main_mp.hpp"
#include "../../shared/RuntimeLog.hpp"
#include <algorithm>
#include <cmath>
#include <ranges>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::array<std::array<float,3>,4> CoreArrivals{{
            {-88,256,116},{-24,256,116},{-88,328,116},{-24,328,116}}};
        void travelLog(const std::string &message)
        {
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM BO1 TRAVEL " + message);
        }
        bool nearPad(const SvPlayerState &player,const std::array<float,3> &pad)
        {
            const auto x=player.origin[0]-pad[0],y=player.origin[1]-pad[1];
            // BO1 uses a 176-unit horizontal test. The height guard is a
            // reconstruction safety boundary for Factory's stacked floors.
            return player.health && player.pmType==SvPmTypeNormal &&
                x*x+y*y<=176.0f*176.0f && std::abs(player.origin[2]-pad[2])<100;
        }
    }

    // OLMOD(factory-bo1-travel): BO1-derived script schedule, not a native primitive.
    // Patched Der Riese player_teleporting / teleport_players use 2s charge,
    // individual black rooms for 2s and 5s cooldown. CODOL paid travel is not
    // captured. Keep this behind OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1.
    bool ServerCore::beginFactoryTravel(std::uint32_t client,std::uint8_t generation,
        std::size_t pad,const std::array<float,3> &origin)
    {
        auto &state=factoryTeleporters_;
        const auto now=world_.snapshot().serverTime;
        if(!factoryBo1TravelEnabled_ || state.travel || pad>=state.links.size() ||
            !state.links[pad] || state.pending(now) || now<state.cooldown || matchStatus_.completed)
            return false;
        const auto player=world_.playerState(client);
        if(!player || player->spawnGeneration!=generation || !nearPad(*player,origin) ||
            world_.factoryTravelHeld(client,generation))return false;
        const auto &fx=factoryTeleporterResources_;
        if(!state.roomFxReady || !fx.roomFlash || !fx.model || fx.bone==255)return false;
        // Preflight both endpoints before charging. Actual entry/return repeats
        // the authoritative hull query; a trace is not a reservation.
        const SvTraceEntityFilter filter{.passEntityNum=client};
        const auto clear=[&](const auto &point) {
            const auto trace=world_.traceCapsule(point,point,StandingPlayerTraceBounds,
                PlayerCollisionContentMask,filter);
            return trace && !trace->startSolid && !trace->allSolid;
        };
        if(!clear(std::array<float,3>{2048,-320,56}) ||
            !std::ranges::any_of(CoreArrivals,clear))return false;
        if(!world_.changeFactoryBattery(client,-static_cast<std::int64_t>(FactoryTeleportPrice),generation))
            return false;
        state.travel=SvFactoryTravel{.started=now,.payer=client,.payerGeneration=generation,
            .pad=pad,.padOrigin=origin};
        emitFactoryTeleportFx(fx.padStart,origin,{270,0,0});
        emitFactoryTeleportFx(fx.coreChargeBeam,{-56.7883f,296.402f,104},{270,0,0});
        emitFactoryTeleportFx(fx.coreChargeFlat,{-56.8396f,296.767f,104},{270,0,0});
        travelLog("CHARGE payer="+std::to_string(client)+" pad="+std::to_string(pad));
        return true;
    }

    // OLMOD(factory-bo1-travel): BO1-derived per-match effect ownership and
    // per-life travel ownership. No respawn, loadout replacement or ABI edits.
    void ServerCore::driveFactoryTravel()
    {
        auto &state=factoryTeleporters_;
        const auto &fx=factoryTeleporterResources_;
        const auto now=world_.snapshot().serverTime;
        if(!state.roomFxAttempted && fx.model && fx.bone!=255 && fx.roomFlash)
        {
            state.roomFxAttempted=true;state.roomFxReady=true;
            for(std::size_t room=0;room<state.roomFx.size();++room)
            {
                const std::array<float,3> pos{2047.92f+320.0f*room,-279.977f,115.73f};
                state.roomFx[room]=world_.spawnScriptModel(fx.model,"tag_origin",pos,{0,270,0});
                if(!state.roomFx[room] || !world_.queueScriptModelFxEvent(*state.roomFx[room],fx.roomFlash,fx.bone))
                    state.roomFxReady=false;
            }
            if(!state.roomFxReady)for(auto &carrier:state.roomFx) {
                if(carrier)static_cast<void>(world_.freeEntity(*carrier));carrier.reset();
            }
            travelLog("ROOM FX ready="+std::to_string(state.roomFxReady));
        }
        if(!state.travel)return;
        auto &trip=*state.travel;
        const auto sameLife=[&](std::uint32_t client,std::uint8_t generation) {
            const auto ps=world_.playerState(client);
            return ps && ps->spawnGeneration==generation &&
                std::ranges::find(state.activeClients,client)!=state.activeClients.end();
        };
        const auto fade=[&](std::uint32_t client,std::uint8_t generation) {
            if(sameLife(client,generation))static_cast<void>(clients_.queueReliableCommand(client,"5 0"));
        };
        if(!trip.inRooms)
        {
            std::map<std::uint32_t,std::uint8_t> nearby;
            if(!matchStatus_.completed)for(const auto client:state.activeClients) {
                const auto ps=world_.playerState(client);
                if(ps && nearPad(*ps,trip.padOrigin))nearby.emplace(client,ps->spawnGeneration);
            }
            for(const auto &[client,generation]:trip.overlays)
                if(!nearby.contains(client) || nearby.at(client)!=generation)fade(client,generation);
            const auto age=now-trip.started;
            if(trip.chargeRemaining(now) && !matchStatus_.completed)
            {
                for(const auto &[client,generation]:nearby)
                    if(!trip.overlays.contains(client) || trip.overlays.at(client)!=generation)
                        static_cast<void>(clients_.queueReliableCommand(client,
                            "5 "+std::to_string(trip.chargeRemaining(now))));
                trip.overlays=std::move(nearby);
                if(age>=1700 && !trip.soundPlayed) {
                    trip.soundPlayed=true;
                    if(fx.travelSound)for(const auto &[client,generation]:trip.overlays)
                        static_cast<void>(clients_.queueLocalSound(client,fx.travelSound));
                }
                return;
            }
            for(const auto &[client,generation]:trip.overlays)fade(client,generation);
            trip.overlays.clear();
            std::uint8_t room{};
            for(const auto &[client,generation]:nearby)
            {
                if(room>=4)break;
                const auto ps=world_.playerState(client);
                if(!ps)continue;
                const auto height=std::clamp(60.0f-ps->viewHeightCurrent,0.0f,49.0f);
                const std::array<float,3> roomOrigin{2048.0f+320.0f*room,-320,56+height};
                if(!world_.teleportFactoryPlayer(client,generation,roomOrigin,90,0,0.0f))continue;
                if(!world_.setFactoryTravelHold(client,generation,true)) {
                    static_cast<void>(world_.teleportFactoryPlayer(client,generation,ps->origin,ps->viewAngles[1],0));
                    continue;
                }
                trip.travelers.push_back({client,generation,ps->origin,ps->viewAngles[1],room++});
                static_cast<void>(clients_.queueReliableCommand(client,"N \"default\" 0"));
                travelLog("ROOM client="+std::to_string(client)+" room="+std::to_string(room-1));
            }
            if(trip.travelers.empty()) {
                // RECONSTRUCTION: an empty/canceled trip is refunded to its
                // original life only; never credit a replacement player.
                static_cast<void>(world_.changeFactoryBattery(trip.payer,FactoryTeleportPrice,trip.payerGeneration));
                state.travel.reset();state.cooldown=now+1000;travelLog("CANCEL no travelers");return;
            }
            trip.enterRooms(now);
            emitFactoryTeleportFx(fx.beam,trip.padOrigin,{270,0,0});
            return; // Do not collapse room/arrival after a late server frame.
        }
        if(!trip.roomReady(now) && !matchStatus_.completed)return;
        if(now<trip.nextReturnAttempt)return;
        trip.nextReturnAttempt=now+250; // bounded collision work if all exits are obstructed
        std::erase_if(trip.travelers,[&](const SvFactoryTraveler &traveler) {
            const auto ps=world_.playerState(traveler.client);
            const bool valid=sameLife(traveler.client,traveler.generation);
            if(!valid || !ps || !ps->health || ps->pmType!=SvPmTypeNormal) {
                static_cast<void>(world_.setFactoryTravelHold(traveler.client,traveler.generation,false));
                // Do not overwrite a new life or a downed player's grayscale.
                fade(traveler.client,traveler.generation);
                if(valid)static_cast<void>(clients_.queueReliableCommand(traveler.client,"N \"zm_factory_sh\" 0"));
                return true;
            }
            bool returned{};
            for(std::size_t index=0;index<CoreArrivals.size();++index) {
                const auto &dest=CoreArrivals[(traveler.room+index)%CoreArrivals.size()];
                const bool occupied=std::ranges::any_of(state.activeClients,[&](auto other) {
                    const auto p=world_.playerState(other);
                    if(other==traveler.client || !p || !p->health)return false;
                    const auto x=p->origin[0]-dest[0],y=p->origin[1]-dest[1];
                    return x*x+y*y<36*36 && std::abs(p->origin[2]-dest[2])<72;
                });
                if(!occupied && world_.teleportFactoryPlayer(traveler.client,traveler.generation,dest,270,0,0.0f)) {
                    returned=true;break;
                }
            }
            // RECONSTRUCTION: if the mainframe is occupied, return to the
            // validated departure instead. Keep collision validation intact.
            if(!returned)returned=world_.teleportFactoryPlayer(traveler.client,traveler.generation,
                traveler.departure,traveler.yaw,0);
            if(!returned && now-trip.roomStarted>=FactoryTravelRoomMs+1000) {
                // Bounded recovery around the departure, still using the normal
                // authoritative hull test. Never bypass collision to escape a room.
                constexpr std::array<std::array<float,2>,8> offsets{{
                    {48,0},{-48,0},{0,48},{0,-48},{48,48},{-48,48},{48,-48},{-48,-48}}};
                for(const auto &offset:offsets) {
                    auto dest=traveler.departure;dest[0]+=offset[0];dest[1]+=offset[1];
                    if(world_.teleportFactoryPlayer(traveler.client,traveler.generation,dest,traveler.yaw,0)) {
                        returned=true;break;
                    }
                }
            }
            if(!returned) {
                if(trip.returnRetries++%20==0)travelLog("RETURN BLOCKED client="+std::to_string(traveler.client));
                return false; // fail closed and retry, never place inside geometry
            }
            static_cast<void>(world_.setFactoryTravelHold(traveler.client,traveler.generation,false));
            static_cast<void>(clients_.queueReliableCommand(traveler.client,"N \"zm_factory_sh\" 0"));
            fade(traveler.client,traveler.generation);
            travelLog("RETURN client="+std::to_string(traveler.client));return true;
        });
        if(trip.travelers.empty()) {
            emitFactoryTeleportFx(fx.coreBeam,{-59.2913f,295.86f,105},{270,0,0});
            emitFactoryTeleportFx(fx.coreFlat,{-57.8089f,297.147f,104},{270,180,180});
            state.travel.reset();state.cooldown=now+FactoryTeleportCooldown;
        }
    }

    // OLMOD(factory-bo1-travel): per-life owner around the retained native
    // ClientThink/Pmove freeze consumer; no new pm_type or persistent weapon flag.
    bool SvServerWorld::setFactoryTravelHold(std::uint32_t client,std::uint8_t generation,bool enabled)
    {
        if(!enabled) {
            const auto hold=factoryTravelHolds_.find(client);
            if(hold!=factoryTravelHolds_.end() && hold->second.first==generation)factoryTravelHolds_.erase(hold);
            return true;
        }
        const auto ps=playerState(client);
        if(!factoryInteractablesEnabled() || !ps || ps->spawnGeneration!=generation ||
            !ps->health || ps->pmType!=SvPmTypeNormal)return false;
        factoryTravelHolds_[client]={generation,ps->origin};return true;
    }
    bool SvServerWorld::factoryTravelHeld(std::uint32_t client,std::uint8_t generation) const
    {
        const auto hold=factoryTravelHolds_.find(client);
        const auto ps=playerState(client);
        return hold!=factoryTravelHolds_.end() && hold->second.first==generation && ps &&
            ps->spawnGeneration==generation && ps->health && ps->pmType==SvPmTypeNormal;
    }
}
