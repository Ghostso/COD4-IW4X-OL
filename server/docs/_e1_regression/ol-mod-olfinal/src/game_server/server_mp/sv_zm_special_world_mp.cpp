#include "sv_snapshot_mp.hpp"
#include "sv_zm_special_mp.hpp"
#include "../../shared/RuntimeLog.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer {
// OLMOD(factory_special_world): opt-in reconstructed combat owner. See
// factory-special-rewards-20260926.md for native evidence and missing behavior.
// CODREF(sv_build_client_snapshot): original July31 Factory215050 onward
// emits eType140 / event117 every100ms. IDA532910,5328D0 and452A00 resolve
// cs4536+(parm>>1), its three-digit FX index and the following tag string.
// OLMOD(factory_view_fx): bounded per-owner temporary events; no shared native
// layouts, collision entities or recurring script/animation allocations.
bool SvServerWorld::spawnFactoryViewFx(std::uint32_t clientNum,std::uint16_t slot) {
    const auto player=playerState(clientNum);
    if(!factoryInteractablesEnabled_ || !entityPool_ || !slot || slot>=32 ||
        !player || player->health<=0 || clientNum>=MaximumGameClients)return false;
    const auto handle=spawnEntity();if(!handle)return false;
    auto &event=entities_.at(handle->entityNum);
    event.networkState.eType=EntityTypeEventBase+117;
    event.networkState.eventParm=static_cast<std::uint32_t>(slot)<<1u;
    event.networkState.origin=player->origin;event.currentOrigin=player->origin;
    event.clientNum=EntityNumNone;event.gameplayActive=true;event.collisionLinked=false;
    if(!entityPool_->markFreeAfterEvent(*handle,snapshot_.serverTime,EntityNumWorld)) {
        static_cast<void>(freeEntity(*handle));return false;
    }
    factoryViewFxRecipients_[handle->entityNum]={*handle,clientNum};
    return true;
}
void SvServerWorld::stepFactoryWeaponLights(const std::array<std::uint16_t,3> &slots) {
    if(!factoryInteractablesEnabled_)return;
    const auto now=snapshot_.serverTime;
    for(const auto &[number,state]:clientStates_) {
        const auto &c=state.client;const auto &ps=c.playerState;
        if(c.gameplayState!=ClientGameplayState::Playing || ps.health<=0 || c.deathState ||
            factorySpecialWeapon(ps.currentWeaponAssetIndex)!=SvFactorySpecialKind::Tesla ||
            !c.resolvedLoadout){factoryViewFxNext_.erase(number);continue;}
        const auto &l=*c.resolvedLoadout;
        const auto *gun=l.primary.weaponAssetIndex==ps.currentWeaponAssetIndex?&l.primary:
            l.secondary.weaponAssetIndex==ps.currentWeaponAssetIndex?&l.secondary:nullptr;
        if(!gun)continue;
        const auto clip=std::ranges::find(ps.ammoClips,gun->clipIndex,&SvAmmoClipState::clipIndex);
        if(clip==ps.ammoClips.end() || !clip->count[0])continue;
        // Retail: 3 rounds -> tube_view; 2 -> tube_view2; 1 -> tube_view3.
        // Reconstructed boundary: upgraded six-round weapon is not enabled here.
        const auto index=3u-std::min<unsigned>(3,clip->count[0]);
        auto &next=factoryViewFxNext_[number];
        if(now>=next && slots[index] && spawnFactoryViewFx(number,slots[index]))next=now+100;
    }
}
void SvServerWorld::setFactorySpecialWeapons(std::map<std::uint16_t,SvFactorySpecialKind> weapons,
    std::map<std::uint16_t,SvFactorySpecialCombat> combat, SvFactoryTrapFx fx) {
    for(const auto &[number,presentation]:factoryTrapPresentation_)
        if(presentation.emitter)static_cast<void>(freeEntity(*presentation.emitter));
    factoryTrapPresentation_.clear();factoryTrapFx_=fx;
    factorySpecialWeapons_.clear();factorySpecialStatuses_.clear();
    factorySpecialCombat_=std::move(combat);
    // Resource registration may precede map activation. Lookup remains gated
    // to Factory; retaining this table cannot enable specials in multiplayer.
    for(const auto &[asset,kind]:weapons)
        if(asset && asset<WeaponConfigStringCount && kind<SvFactorySpecialKind::Count && kind!=SvFactorySpecialKind::Ammo)
            factorySpecialWeapons_.emplace(asset,kind);
}
std::optional<SvFactorySpecialKind> SvServerWorld::factorySpecialWeapon(std::uint16_t asset) const {
    if(!factoryInteractablesEnabled_)return std::nullopt;
    const auto it=factorySpecialWeapons_.find(asset);
    return it==factorySpecialWeapons_.end()?std::nullopt:std::optional{it->second};
}
bool SvServerWorld::replaceFactoryEquipment(std::uint32_t clientNum,
    std::size_t slot,const SvOffhandWeapon &replacement,std::uint32_t costRaw) {
    if(!factorySpecialWeapon(replacement.weaponAssetIndex) || slot>=2 ||
        clientNum>=zombieBattery_.size() || zombieBattery_[clientNum]<costRaw)return false;
    const auto found=clientStates_.find(clientNum);
    if(found==clientStates_.end())return false;
    auto &owner=found->second.client;
    if(owner.gameplayState!=ClientGameplayState::Playing || owner.deathState ||
        owner.playerState.health<=0 || !owner.resolvedLoadout)return false;
    auto equipment=playerEquipment(clientNum,owner.playerState.spawnGeneration)
        ? *playerEquipment(clientNum,owner.playerState.spawnGeneration):SvResolvedEquipment{};
    // Existing equipment must not alias firearm ammo; retire only private slots.
    const auto &old=equipment.weapons[slot];
    for(const auto *gun:{&owner.resolvedLoadout->primary,&owner.resolvedLoadout->secondary})
        if((old.weaponAssetIndex && (gun->ammoIndex==old.ammoIndex || gun->clipIndex==old.clipIndex)) ||
            gun->ammoIndex==replacement.ammoIndex || gun->clipIndex==replacement.clipIndex)return false;
    auto candidate=owner.playerState;
    if(!SV_ReplaceOffhandReward(candidate,equipment,slot,replacement))return false;
    auto native=owner.nativePlayerState;
    SV_OverlayPlayerStateToNative(candidate,native);
    auto roundTrip=candidate;
    if(!SV_OverlayNativePlayerStateToPlayerState(native,roundTrip) || roundTrip!=candidate)return false;
    playerEquipment_[clientNum]={candidate.spawnGeneration,equipment};
    owner.playerState=std::move(candidate);owner.nativePlayerState=std::move(native);
    zombieBattery_[clientNum]-=costRaw;
    return true;
}
SvMissileFrameResult SvServerWorld::stepFactorySpecialMissile(SvFactorySpecialKind kind,
    const SvServerMissile &missile,const std::array<float,3> &origin,std::uint32_t now) const {
    const auto owner=clientStates_.find(missile.network.owner);
    if(owner==clientStates_.end() || owner->second.client.playerState.spawnGeneration!=missile.ownerSpawnGeneration ||
        owner->second.client.gameplayState!=ClientGameplayState::Playing ||
        owner->second.client.playerState.health<=0)return SvMissileRetirement{};
    return SV_StepFactorySpecial(kind,missile,origin,now,zmBoardTrajectoryEvaluator_,
        [this](const SvServerMissile &m,const auto &start,const auto &end)->std::optional<TraceResult> {
            if(!pointTraceRunner_)return std::nullopt;
            // OLMOD(factory_special_collision): use the existing bounded model
            // trace, including static models and actor DObjs. CollisionOnly
            // skips actor models. passOwnerEntityNum excludes siblings, NOT
            // the owner itself; passing the shooter also excludes its missile.
            // Per-projectile native CODOL masks remain unrecovered.
            // The native mirror is published from bulletCollisionEntities_.
            // The navigation/capsule view deliberately omits actors and cannot
            // satisfy the model trace's complete-mirror validation.
            return pointTraceRunner_({.start=start,.end=end,.contentMask=BulletLocationalContentMask,
                .filter={m.network.owner,std::nullopt},.mode=SvPointTraceMode::BulletLocational},glassState_,bulletCollisionEntities_);
        },factorySpecialCombat_.contains(missile.network.weapon)
            ? factorySpecialCombat_.at(missile.network.weapon).sticky : false);
}
std::optional<std::array<float,3>> SvServerWorld::factoryMonkeyTarget(const std::array<float,3> &from) const {
    if(!factoryInteractablesEnabled_ || !pointTraceRunner_)return std::nullopt;
    float best=600.f*600.f;
    std::optional<std::array<float,3>> target;
    // Bounded by the explicit special missile cap; expired/airborne monkeys do
    // not divert actors. Normal graph/window constraints still own movement.
    for(const auto &[number,m]:missiles_) {
        if(factorySpecialWeapon(m.network.weapon)!=SvFactorySpecialKind::Monkey ||
            m.network.position.type!=0 || snapshot_.serverTime>=m.fuseDeadline)continue;
        const auto &p=m.network.position.base;
        float distance{};for(std::size_t i=0;i<3;++i)distance+=(p[i]-from[i])*(p[i]-from[i]);
        if(distance>=best)continue;
        auto start=from,end=p;start[2]+=32;end[2]+=8;
        const auto clear=pointTraceRunner_({.start=start,.end=end,.contentMask=BulletLocationalContentMask,
            .filter={number,std::nullopt},.mode=SvPointTraceMode::BulletLocational,.worldOnly=true},glassState_,bulletCollisionEntities_);
        if(!clear || clear->startSolid || clear->allSolid || clear->fraction<1.f)continue;
        best=distance;target=p;
    }
    return target;
}
void SvServerWorld::stepFactorySpecialPresentation() {
    if(!factoryInteractablesEnabled_ || !entityPool_)return;
    const auto now=snapshot_.serverTime;
    // Original actor wire+54 falls by .1 per100ms to .5. Keep the source
    // status lifetime reconstructed; expiry restores the actor field as well.
    for(auto it=factorySpecialStatuses_.begin();it!=factorySpecialStatuses_.end();) {
        const auto &status=it->second;
        const auto e=entities_.find(it->first);
        const bool live=entityPool_->resolve(status.handle) && e!=entities_.end();
        if(!live || now>=status.until) {
            if(live && status.shrunk)e->second.networkState.actorField0054=status.originalScale;
            it=factorySpecialStatuses_.erase(it);continue;
        }
        if(status.shrunk && e->second.networkState.eType==EntityTypeActor) {
            e->second.networkState.actorField0054=status.originalScale*
                (1.f-std::min(.5f,(now-status.shrinkStarted)*.001f));
            // Reconstructed contact kill: authoritative moving-player touch,
            // bounded to a live fully shrunken actor. This is reconstructed
            // contact policy, not a claim of recovered original stomp logic.
            const auto health=entityDamageStates_.find(it->first);
            if(now-status.shrinkStarted>=500 && health!=entityDamageStates_.end() &&
               health->second.canTakeDamage && !health->second.cannotDie && health->second.health>0) {
                for(const auto &[clientNum,state]:clientStates_) {
                    const auto &ps=state.client.playerState;
                    if(state.client.gameplayState!=ClientGameplayState::Playing || ps.health<=0 ||
                       state.entity.lastThinkServerTime!=now ||
                       ps.velocity[0]*ps.velocity[0]+ps.velocity[1]*ps.velocity[1]<=1.f)continue;
                    // Fresh authoritative collision touch avoids through-wall
                    // kills, stale contacts and credit to a stationary player.
                    const auto count=std::min<std::size_t>(state.entity.numTouch,state.entity.touchEntities.size());
                    if(std::find(state.entity.touchEntities.begin(),state.entity.touchEntities.begin()+count,
                        it->first)==state.entity.touchEntities.begin()+count)continue;
                    const auto before=health->second.health;health->second.health=0;
                    SvEntityDamagePayload cause{.targetEntityNum=it->first,.targetGeneration=status.handle.generation,
                        .attackerEntityNum=clientNum,.damage=before,.methodOfDeath=SvMethodOfDeathMelee,
                        .point=e->second.currentOrigin};
                    appendEntityDamageEvent({cause,0,before},"shrink_stomp");
                    break;
                }
            }
        }
        ++it;
    }
    // A generation-owned carrier per grounded trap, bounded by the32 missile
    // admission cap. No per-frame event replay or retries for missing assets.
    for(auto it=factoryTrapPresentation_.begin();it!=factoryTrapPresentation_.end();) {
        if(!missiles_.contains(it->first) || !entityPool_->resolve(it->second.missile)) {
            if(it->second.emitter && !freeEntity(*it->second.emitter) && entityPool_->resolve(*it->second.emitter)) {++it;continue;}
            it=factoryTrapPresentation_.erase(it);
        } else ++it;
    }
    for(const auto &[number,missile]:missiles_) {
        const auto kind=factorySpecialWeapon(missile.network.weapon);
        if(!kind || *kind<SvFactorySpecialKind::FireTrap || *kind>SvFactorySpecialKind::Monkey ||
           missile.network.position.type!=0 || factoryTrapPresentation_.contains(number) ||
           factoryTrapPresentation_.size()>=32)continue;
        const auto *life=entityPool_->resolve(number);if(!life)continue;
        auto &presentation=factoryTrapPresentation_[number];
        presentation.missile={number,life->generation};
        if(*kind==SvFactorySpecialKind::Monkey) {
            // BO1's original script separates the simulation grenade and the
            // animated model. Use CODOL's resident o_monkey_bomb/tree, and the
            // existing gameplayActive publication gate, not a guessed eFlag.
            const auto origin=missile.network.position.base;
            if(factoryTrapFx_.monkeyModel && factoryTrapFx_.monkeyAnimation && factoryTrapFx_.monkeyTree) {
                presentation.emitter=spawnScriptModel(factoryTrapFx_.monkeyModel,
                    "weapon_zombie_monkey_bomb",origin,missile.network.angles.base);
                if(presentation.emitter &&
                    bindScriptModelAnimationTree(*presentation.emitter,factoryTrapFx_.monkeyTree) &&
                    setScriptModelAnimation(*presentation.emitter,factoryTrapFx_.monkeyAnimation,now)) {
                    entities_.at(number).gameplayActive=false;
                } else if(presentation.emitter && freeEntity(*presentation.emitter))presentation.emitter.reset();
            }
            if(factoryTrapFx_.monkeySong)
                static_cast<void>(spawnSoundAliasEvent(factoryTrapFx_.monkeySong,origin));
            continue;
        }
        const auto index=static_cast<unsigned>(*kind)-static_cast<unsigned>(SvFactorySpecialKind::FireTrap);
        const auto effect=factoryTrapFx_.effects[index];
        if(!factoryTrapFx_.model || factoryTrapFx_.bone==255 || !effect)continue;
        auto origin=missile.network.position.base;
        // Original Factory: fire entity534 +14Z, freeze471 +5Z,
        // shock483 +20Z. Sumpf shrink859 is at device origin.
        if(*kind==SvFactorySpecialKind::FireTrap)origin[2]+=14.f;
        else if(*kind==SvFactorySpecialKind::FreezeTrap)origin[2]+=5.f;
        else if(*kind==SvFactorySpecialKind::ShockTrap)origin[2]+=20.f;
        presentation.emitter=spawnScriptModel(factoryTrapFx_.model,"tag_origin",origin,{-90,0,0});
        if(presentation.emitter && !queueScriptModelFxEvent(*presentation.emitter,effect,factoryTrapFx_.bone)) {
            if(freeEntity(*presentation.emitter))presentation.emitter.reset();
        }
    }
}
void SvServerWorld::applyFactorySpecialImpact(const SvFactorySpecialImpact &impact) {
    // OLMOD(factory_special_impact): bounded post-publication damage/status
    // dispatch; no claim of recovered CODOL radius, chain or trap policy.
    if(!factoryInteractablesEnabled_ || !entityPool_ || !pointTraceRunner_ ||
        factorySpecialWeapon(impact.weapon)!=impact.kind)return;
    const auto owner=clientStates_.find(impact.owner);
    if(owner==clientStates_.end() || owner->second.client.playerState.spawnGeneration!=impact.ownerLife ||
       owner->second.client.playerState.health<=0 ||
       owner->second.client.gameplayState!=ClientGameplayState::Playing)return;
    const auto policy=std::ranges::find(FactoryReconstructedBoxPool,impact.kind,&SvFactorySpecialEntry::kind);
    const auto settings=factorySpecialCombat_.find(impact.weapon);
    if(impact.kind==SvFactorySpecialKind::Smoke)return; // effect carrier only; AI smoke occlusion not recovered
    const float baseRadius=settings!=factorySpecialCombat_.end()?settings->second.radius:
        impact.kind==SvFactorySpecialKind::Ray?160.f:250.f;
    // Reconstructed fire/electric tuning: one third of the base radius.
    const float radius=(impact.kind==SvFactorySpecialKind::FireTrap ||
        impact.kind==SvFactorySpecialKind::ShockTrap)?baseRadius/3.f+12.f:baseRadius;
    if(!std::isfinite(radius) || radius<=0 || radius>4096)return;
    std::vector<std::pair<float,std::uint32_t>> targets;
    for(const auto &[number,e]:entities_) {
        const auto health=entityDamageStates_.find(number);
        if(e.networkState.eType!=EntityTypeActor || health==entityDamageStates_.end() ||
            !health->second.canTakeDamage || health->second.health<=0)continue;
        auto center=e.currentOrigin;center[2]+=32;
        float d2{};for(std::size_t i=0;i<3;++i)d2+=(center[i]-impact.origin[i])*(center[i]-impact.origin[i]);
        if(d2<=radius*radius || impact.directHit==number || impact.kind==SvFactorySpecialKind::Tesla)
            targets.emplace_back(impact.directHit==number?0.f:d2,number);
    }
    std::ranges::sort(targets); // stable distance/entity ordering, bounded target budget
    unsigned applied{},totalDamage{};
    auto damageOrigin=impact.origin;
    std::optional<std::uint16_t> chainSource;
    while(!targets.empty() && applied<10) {
        if(impact.kind==SvFactorySpecialKind::Tesla && applied) {
            for(auto &[distance,number]:targets) {
                auto center=entities_.at(number).currentOrigin;center[2]+=32;distance=0;
                for(std::size_t i=0;i<3;++i)distance+=(center[i]-damageOrigin[i])*(center[i]-damageOrigin[i]);
            }
            std::ranges::sort(targets);
        }
        const auto [d2,number]=targets.front();targets.erase(targets.begin());
        if(d2>radius*radius && impact.directHit!=number)break;
        const auto *life=entityPool_->resolve(number);if(!life)continue;
        auto &e=entities_.at(number);auto center=e.currentOrigin;center[2]+=32;
        if(impact.directHit!=number) {
            auto start=damageOrigin;start[2]+=2;
            const auto visible=pointTraceRunner_({.start=start,.end=center,.contentMask=BulletLocationalContentMask,
                .filter={chainSource.value_or(impact.owner),impact.owner}},glassState_,collisionEntities_);
            if(!visible || visible->allSolid || visible->startSolid ||
                (visible->fraction<1.f && visible->hitId!=number))continue;
        }
        ++applied;
        if(impact.kind==SvFactorySpecialKind::FreezeTrap || impact.kind==SvFactorySpecialKind::ShrinkTrap || impact.kind==SvFactorySpecialKind::Flash) {
            auto [it,inserted]=factorySpecialStatuses_.try_emplace(number);
            auto &status=it->second;
            if(inserted || status.handle.generation!=life->generation)
                status={SvEntityHandle{number,life->generation},0,false,false,e.networkState.actorField0054};
            status.until=snapshot_.serverTime+2000;
            if(impact.kind==SvFactorySpecialKind::FreezeTrap || impact.kind==SvFactorySpecialKind::Flash)status.frozen=true;
            else if(!status.shrunk) {status.shrunk=true;status.shrinkStarted=snapshot_.serverTime;}
            continue;
        }
        auto &health=entityDamageStates_.at(number);
        const auto before=health.health;
        std::int32_t damage=100; // explicit trap reconstruction per 500ms pulse
        if(impact.kind==SvFactorySpecialKind::Tesla || impact.kind==SvFactorySpecialKind::Monkey)damage=before;
        if(impact.kind==SvFactorySpecialKind::Ray) {
            SvResolvedWeapon weapon;
            if(!weaponDefinitionResolver_ || !weaponDefinitionResolver_(impact.weapon,weapon))continue;
            damage=std::max(1,weapon.damageCurve.damage[0]);
            if(impact.directHit!=number)damage=std::max(1,static_cast<int>(damage*(1.f-std::sqrt(d2)/radius)));
        }
        if(impact.kind==SvFactorySpecialKind::Grenade) {
            if(settings==factorySpecialCombat_.end())continue;
            const auto &p=settings->second;
            damage=std::max(0,static_cast<int>(p.innerDamage+
                (p.outerDamage-p.innerDamage)*std::clamp(std::sqrt(d2)/radius,0.f,1.f)));
        }
        damage=std::min(damage,health.cannotDie?before-1:before);
        if(damage<=0)continue;
        health.health-=damage;
        totalDamage+=static_cast<unsigned>(damage);
        SvEntityDamagePayload cause{.targetEntityNum=number,.targetGeneration=life->generation,
            .attackerEntityNum=impact.owner,.damage=damage,.methodOfDeath=SvMethodOfDeathUnknown,
            .weaponAssetIndex=impact.weapon,.point=center};
        appendEntityDamageEvent({cause,health.health,before},policy!=FactoryReconstructedBoxPool.end()
            ? policy->weapon : "factory_grenade");
        if(impact.kind==SvFactorySpecialKind::Tesla) {
            damageOrigin=center;
            chainSource=static_cast<std::uint16_t>(number);
        }
    }
    // One record per committed shot/detonation, never per frame or trap pulse.
    // This distinguishes contact without a target from the old rejected-frame
    // loop without adding an unbounded diagnostic queue.
    if(impact.kind==SvFactorySpecialKind::Ray || impact.kind==SvFactorySpecialKind::Tesla ||
       impact.kind==SvFactorySpecialKind::Grenade || impact.kind==SvFactorySpecialKind::Flash ||
       impact.kind==SvFactorySpecialKind::Monkey)
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM SPECIAL IMPACT weapon="+std::to_string(impact.weapon)+" kind="+
            std::to_string(static_cast<unsigned>(impact.kind))+" direct="+
            std::to_string(impact.directHit.value_or(EntityNumNone))+" targets="+
            std::to_string(applied)+" damage="+std::to_string(totalDamage));
}
}
