#include "sv_main_mp.hpp"
#include "../../shared/RuntimeLog.hpp"
#include <algorithm>
#include <cmath>
#include <numbers>
#include <ranges>

namespace CodolGameServer {
namespace {
// CODREF(actor_grounded_adapter): July31 Factory opens at165550 and selects
// at169950. Ten-second unattended offer is reconstruction. Both resident lid
// clips have120frames at60fps; wait the full2s close before another purchase.
// only the observed open-to-select interval is taken from that recording.
constexpr std::uint32_t BoxRollMs=4400,BoxOfferMs=10000,BoxCloseMs=2000,BoxCost=1200;
bool elapsed(std::uint32_t now,std::uint32_t start,std::uint32_t duration) {
    return now-start>=duration;
}
// Authored rubble is visible only at inactive sites. Preserve the source/native
// collision transaction and roll back all pieces if a later mirror rejects it.
bool showSite(SvServerWorld &world,const SvFactoryBoxSite &site,bool active) {
    std::vector<std::pair<SvEntityHandle,SvGameEntity>> changed;
    for(const auto h:{site.base,site.lid,site.rubble})if(h) {
        const auto e=world.entity(*h);if(!e)return false;
        changed.emplace_back(*h,*e);
    }
    for(const auto &[h,e]:changed) {
        const bool visible=site.rubble && h==*site.rubble?!active:active;
        if(!world.setScriptModelTransformAndActive(h,e.currentOrigin,e.currentAngles,visible)) {
            for(const auto &[prior,old]:changed)
                static_cast<void>(world.setScriptModelTransformAndActive(prior,old.currentOrigin,old.currentAngles,old.gameplayActive));
            return false;
        }
    }
    return true;
}
void freePresentation(SvServerWorld &world,std::optional<SvEntityHandle> &handle) {
    if(handle)static_cast<void>(world.freeEntity(*handle));handle.reset();
}
void boxPoof(SvServerWorld &world,SvFactoryBoxRuntime &box,const SvFactoryBoxResources &res,
             const SvFactoryBoxSite &site,std::uint32_t now) {
    freePresentation(world,box.poof);
    if(!res.effectModel || !res.relocationEffect || res.effectBone==255)return;
    box.poof=world.spawnScriptModel(res.effectModel,"tag_origin",site.origin,{});
    if(box.poof && !world.queueScriptModelFxEvent(*box.poof,res.relocationEffect,res.effectBone))
        freePresentation(world,box.poof);
    box.poofStarted=now;
}
}

bool SV_FactoryBoxBearRoll(std::uint32_t paidPull,std::uint32_t moves,std::uint32_t random) {
    // OLMOD(factory_box_relocation): BO1 _zombiemode_weapons.gsc reference,
    // not recovered CODOL probability. No bear on1..3;15% on4..7; first
    // location guaranteed at8; later sites30% on8..12 and50% thereafter.
    if(paidPull<4)return false;
    if(!moves && paidPull>=8)return true;
    return random%100 < (paidPull<8?15u:paidPull<13?30u:50u);
}
std::size_t SV_FactoryBoxNextSite(std::size_t active,std::size_t count,std::uint32_t random) {
    // OLMOD(factory_box_relocation): uniform OTHER authored location. CODOL's
    // original shuffle/order is unknown; do not infer it from map numbering.
    if(count<2 || active>=count)return active;
    const auto choice=static_cast<std::size_t>(random)%(count-1);
    return choice>=active?choice+1:choice;
}

std::array<float,3> SV_FactoryBoxDisplayOrigin(
    const SvFactoryBoxResources &resources,std::uint16_t asset,const SvFactoryBoxSite &site) {
    auto origin=site.origin;
    const auto weapon=std::ranges::find(resources.weapons,asset,&SvFactoryBoxWeapon::asset);
    if(weapon==resources.weapons.end())return origin;
    // OLMOD(factory_box_horizontal_center): the marker is centred on the box,
    // but the modular M9 horizontal midpoint is (-7.88635,.019425).
    // Root mesh origins are not visual centres. Compensate in the box's rotated
    // horizontal plane; keep the measured rise height and FX anchor unchanged.
    // This is presentation reconstruction, not a recovered retail script.
    const float yaw=site.angles[1]*std::numbers::pi_v<float>/180.0f;
    const auto &center=weapon->bodyCenter;
    if(!std::isfinite(yaw) || !std::isfinite(center[0]) || !std::isfinite(center[1]))return origin;
    origin[0]-=std::cos(yaw)*center[0]-std::sin(yaw)*center[1];
    origin[1]-=std::sin(yaw)*center[0]+std::cos(yaw)*center[1];
    return origin;
}

SvNativeTrajectory SV_FactoryBoxRise(
    const std::array<float,3> &origin,std::uint32_t started,std::uint32_t now) {
    // CODREF(actor_grounded_adapter): original Factory165550/entity781 and Sumpf870800/entity774
    // agree on a40unit rise, native types7(2000ms),3(100ms),8(899ms), then0.
    // out.exe410BD0 owns acceleration/deceleration; send its trajectory rather
    // than stepping a model upward or resetting its clock at each reward swap.
    constexpr float speed=25.80645179748535f;
    SvNativeTrajectory result{.type=7,.time=static_cast<std::int32_t>(started),
        .duration=2000,.base=origin,.delta={0,0,speed}};
    const auto age=now-started;
    if(age>=3000) {
        result.type=0;result.time=static_cast<std::int32_t>(started+3000);
        result.duration=0;result.delta={};result.base[2]+=40;
    } else if(age>=2100) {
        result.type=8;result.time=static_cast<std::int32_t>(started+2100);
        result.duration=899;result.base[2]+=speed*1.1f;
    } else if(age>=2000) {
        result.type=3;result.time=static_cast<std::int32_t>(started+2000);
        result.duration=100;result.base[2]+=speed;
    }
    return result;
}

void SV_StopFactoryBoxFx(SvServerWorld &world,SvFactoryBoxFxCarriers &carriers) {
    // OLMOD(factory_box_fx_lifetime): generation-owned removal; never stop
    // unrelated FX or repeatedly emit the looping definitions on every tick.
    for(auto &carrier:carriers) {
        if(carrier)static_cast<void>(world.freeEntity(*carrier));
        carrier.reset();
    }
}

SvFactoryBoxFxCarriers SV_StartFactoryBoxFx(
    SvServerWorld &world,const SvFactoryBoxResources &resources,const SvFactoryBoxSite &site) {
    SvFactoryBoxFxCarriers carriers{};
    if(!resources.effectModel || resources.effectBone==255 ||
        !resources.effects[0] || !resources.effects[1])return carriers;
    // CODREF(actor_grounded_adapter): original Factory165550 and Sumpf870850
    // emit113 on two root-bone script models, FX127/253. Exact out.exe452970
    // decodes low9 effect/high8 bone;452D10->5319B0 attaches to the carrier.
    // Both recordings put ray at weapon marker, glow5units above, with local
    // rotations (90,lidYaw+90,0) and(-90,lidYaw-90,-90). Both disappear at close.
    // Resolve names, not captured indices; native assets own color/particles.
    for(std::size_t i=0;i<carriers.size();++i) {
        auto origin=site.origin;if(i==1)origin[2]+=5;
        const std::array<float,3> angles=i==0
            ? std::array<float,3>{90,site.angles[1]+90,0}
            : std::array<float,3>{-90,site.angles[1]-90,-90};
        carriers[i]=world.spawnScriptModel(resources.effectModel,"tag_origin",origin,angles);
        if(!carriers[i] || !world.queueScriptModelFxEvent(
                *carriers[i],resources.effects[i],resources.effectBone)) {
            SV_StopFactoryBoxFx(world,carriers);return {};
        }
    }
    return carriers;
}

void ServerCore::setFactoryBoxResources(SvFactoryBoxResources resources) {
    const std::lock_guard lock(mutex_);
    factoryBoxResources_=std::move(resources);
}

std::optional<std::uint16_t> SV_FactorySoundAliasSlot(
    const std::map<std::uint16_t,std::string> &slots,std::string_view name) {
    if(name.empty() || name.size()>=128 || name.find('\0')!=std::string_view::npos)return {};
    // Original Factory recordings publish dynamic sound aliases in this band.
    // Allocation order is reconstructed; preserve every occupied source slot.
    for(std::uint16_t i=50;i<=90;++i)
        if(const auto s=slots.find(i);s!=slots.end() && s->second==name)return i;
    for(std::uint16_t i=50;i<=90;++i)
        if(const auto s=slots.find(i);s==slots.end() || s->second.empty())return i;
    return {};
}

void ServerCore::announceFactorySoundAliases() {
    if(!factoryInteractablesEnabled_ || !world_.factoryInteractablesEnabled() ||
       !factoryBox_.initialized || factoryBox_.soundsRegistered)return;
    const auto &clients=clients_.clients();
    if(std::ranges::none_of(clients,[](const auto &c){return c.state!=ClientState::Free;}) ||
       std::ranges::any_of(clients,[](const auto &c){return c.state!=ClientState::Free && c.state!=ClientState::Active;}))return;
    // Same all-active boundary as ordinary sound registration: never update a
    // loading client's CCS table. The stored gamestate also serves late joins.
    std::map<std::uint16_t,std::string> slots;
    for(std::uint16_t i=50;i<=90;++i)
        if(const auto value=clients_.configString(SoundAliasConfigStringBase+i))slots[i]=*value;
    for(const auto name:{"zmb_box_open","zmb_music_box","zmb_box_cycle","zmb_box_select",
        "zmb_box_close","zmb_box_move","zmb_box_poof","zmb_box_poof_land","zmb_box_raise",
        "zmb_couch_slam","zmb_vox_ann_magicbox","zmb_monkey_song"}) {
        auto &alias=factorySounds_[name];
        if(!alias)if(const auto slot=SV_FactorySoundAliasSlot(slots,name)) {
            static_cast<void>(clients_.SV_SetConfigString(SoundAliasConfigStringBase+*slot,name));
            if(clients_.configString(SoundAliasConfigStringBase+*slot)==name) {
                slots[*slot]=name;alias=*slot;
            }
        }
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "Factory sound registered name="+std::string(name)+" alias="+std::to_string(alias));
    }
    if(factoryBoxResources_.reconstructedPool)world_.setFactoryMonkeySong(factorySounds_["zmb_monkey_song"]);
    // CODREF(sv_build_client_snapshot): CODOL5328D0 consumes cs4536+(parm>>1).
    // Original July31 Factory registers 183/184/186 + tag_brass at4537/39/40.
    // Allocate existing native protocol slots without overwriting other scripts.
    for(std::size_t i=0;i<factoryBoxResources_.teslaViewEffects.size();++i) {
        const auto fx=factoryBoxResources_.teslaViewEffects[i];
        if(!factoryBoxResources_.reconstructedPool || !fx || fx>=400)continue;
        const auto digits=std::to_string(1000+fx).substr(1)+"tag_brass";
        std::uint16_t chosen{};
        for(std::uint16_t s=1;s<32;++s)
            if(clients_.configString(4536+s)==digits){chosen=s;break;}
        if(!chosen)for(std::uint16_t s=1;s<32;++s) {
            const auto current=clients_.configString(4536+s);
            if(!current || current->empty()) {
                static_cast<void>(clients_.SV_SetConfigString(4536+s,digits));
                if(clients_.configString(4536+s)==digits)chosen=s;
                break;
            }
        }
        factoryBox_.teslaViewSlots[i]=chosen;
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "Factory Tesla view FX effect="+std::to_string(fx)+" slot="+std::to_string(chosen));
    }
    factoryBox_.soundsRegistered=true;
}

void ServerCore::factoryInteractionSound(std::uint32_t client,std::string_view name) {
    const auto i=factorySounds_.find(name);
    if(i==factorySounds_.end() || !i->second)return;
    // These are map-owned sounds, including after the buyer disconnects.
    // Reuse the positional event path so every relevant client hears the box.
    if(factoryBox_.initialized && factoryBox_.active<factoryBox_.sites.size())
        static_cast<void>(world_.spawnSoundAliasEvent(i->second,
            factoryBox_.sites[factoryBox_.active].origin));
    else static_cast<void>(clients_.queueLocalSound(client,i->second));
}

std::string ServerCore::factoryBoxHint(std::uint32_t client,const SvMapTrigger &trigger) const {
    if(!factoryInteractablesEnabled_ || !world_.factoryInteractablesEnabled() ||
        trigger.targetname!="treasure_chest_use" || !factoryBox_.initialized ||
        factoryBox_.sites.empty() || factoryBoxResources_.weapons.empty() ||
        factoryBox_.sites[factoryBox_.active].trigger!=trigger.triggerIndex)return {};
    if(factoryBox_.phase==SvFactoryBoxPhase::Closed)return "ZOMBIE_RANDOM_WEAPON_1000";
    if(factoryBox_.phase==SvFactoryBoxPhase::Offer && factoryBox_.owner==client) {
        const auto state=world_.playerState(client);
        if(state && state->health && state->spawnGeneration==factoryBox_.life)
            return factoryBox_.rewardKind==SvFactoryBoxRewardKind::Ammo
                ? "ZOMBIE_CHEST_MAXAMMO" : "ZOMBIE_RANDOM_WEAPON_1000";
    }
    return {};
}

void ServerCore::closeFactoryBox(std::uint32_t now) {
    SV_StopFactoryBoxFx(world_,factoryBox_.effectCarriers);
    if(factoryBox_.display) {
        static_cast<void>(world_.freeEntity(*factoryBox_.display));
        factoryBox_.display.reset();
    }
    if(!factoryBox_.sites.empty()) {
        const auto &site=factoryBox_.sites[factoryBox_.active];
        if(site.lid && factoryBoxResources_.closeAnimation)
            static_cast<void>(world_.setScriptModelAnimation(*site.lid,
                factoryBoxResources_.closeAnimation,now,3));
    }
    factoryInteractionSound(factoryBox_.owner,"zmb_box_close");
    factoryBox_.phase=SvFactoryBoxPhase::Closing;factoryBox_.started=now;
    cursorHintTrigger_.erase(factoryBox_.owner);
}

bool ServerCore::processFactoryBoxUse(const SvWorldClientInput &client,const SvMapTrigger &trigger) {
    if(factoryBoxHint(client.clientNum,trigger).empty())return false;
    const auto state=world_.playerState(client.clientNum);
    if(!state || !state->health || client.gameplayState!=ClientGameplayState::Playing)return false;
    const auto now=world_.snapshot().serverTime;
    if(factoryBox_.phase==SvFactoryBoxPhase::Offer) {
        if(!clients_.canQueueReliableCommands(client.clientNum))return false;
        std::string_view refusal;
        const bool ammoReward=factoryBox_.rewardKind==SvFactoryBoxRewardKind::Ammo;
        const auto equipment=factoryBoxResources_.equipment.find(factoryBox_.offer);
        const bool equipmentReward=!ammoReward && equipment!=factoryBoxResources_.equipment.end();
        const bool granted=ammoReward ? world_.refillFactoryAmmo(client.clientNum,0,true) :
            equipmentReward ? world_.replaceFactoryEquipment(client.clientNum,
                equipment->second.weaponName=="zombie_cymbal_monkey"?1:0,equipment->second) :
            world_.replaceFactoryWeapon(client.clientNum,state->currentWeaponAssetIndex,factoryBox_.offer,0,&refusal);
        if(!granted) {
            if(ammoReward)refusal="ammo_full_or_unavailable";
            if(equipmentReward)refusal="equipment_exchange_rejected";
            // A malformed/stale offer must never strand the paid roll.  This
            // owner can refund only the same living buyer, then closes so a
            // repeated use cannot mint further refunds.
            const bool refunded=world_.changeFactoryBattery(client.clientNum,
                static_cast<std::int32_t>(BoxCost),factoryBox_.life);
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM BOX CLAIM_REJECT client="+std::to_string(client.clientNum)+
                " current="+std::to_string(state->currentWeaponAssetIndex)+
                " offer="+std::to_string(factoryBox_.offer)+" reason="+std::string(refusal)+
                " site="+std::to_string(factoryBox_.active)+" refunded="+std::to_string(refunded));
            closeFactoryBox(now);
            return false;
        }
        // Caller already owns ServerCore::mutex_; the public selection method
        // would acquire it again. Authoritative ownership has committed above.
        if(!ammoReward && !equipmentReward)static_cast<void>(clients_.queueReliableCommand(client.clientNum,"a "+std::to_string(factoryBox_.offer)));
        if(equipmentReward)static_cast<void>(clients_.queueReliableCommand(client.clientNum,
            "y "+std::to_string(world_.playerState(client.clientNum)->offhandWeaponAssetIndex)));
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM BOX CLAIM client="+std::to_string(client.clientNum)+" weapon="+std::to_string(factoryBox_.offer)+
            " kind="+(ammoReward?"ammo":"weapon"));
        closeFactoryBox(now);return true;
    }
    if(factoryBox_.phase!=SvFactoryBoxPhase::Closed)return false;
    struct Choice { SvFactoryBoxRewardKind kind; std::uint16_t asset; std::uint16_t weight; };
    std::vector<Choice> choices;
    for(const auto &w:factoryBoxResources_.weapons) {
        if(!w.asset || w.asset>=WeaponConfigStringCount ||
            std::ranges::find(choices,w.asset,&Choice::asset)!=choices.end())continue;
        const auto baseFor=[&](std::uint16_t asset) {
            const auto i=factoryBoxResources_.weaponBases.find(asset);
            return i==factoryBoxResources_.weaponBases.end()?asset:i->second;
        };
        const bool owned=std::ranges::any_of(state->heldWeapons,[&](const auto &slot){
            return slot.weaponAssetIndex && baseFor(slot.weaponAssetIndex)==baseFor(w.asset);
        });
        // BO1 ownership exclusion is reused; CODOL rarity remains unknown.
        if(!owned && w.weight)choices.push_back({SvFactoryBoxRewardKind::Weapon,w.asset,w.weight});
    }
    // Original Prototype591550 proves the ammo reward. Eligibility and
    // weights remain explicit reconstruction; never charge a full-ammo player
    // for an unusable refill, nor replace a firearm to grant ammunition.
    if(factoryBoxResources_.ammoModel && world_.canRefillFactoryAmmo(client.clientNum,0,true))
        choices.push_back({SvFactoryBoxRewardKind::Ammo,0,static_cast<std::uint16_t>(factoryBoxResources_.reconstructedPool?15:1)});
    if(choices.empty())return false;
    // OLMOD(factory_box): temporary weighted reconstruction. The optional
    // class pool retains weight1; neither is a recovered retail drop table.
    auto seed=factoryBox_.seed ^ now ^ (client.clientNum+1)*0x85ebca6bu;
    seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;
    std::vector<std::uint16_t> weights;weights.reserve(choices.size());
    for(const auto &choice:choices)weights.push_back(choice.weight);
    const auto selected=SV_SelectFactorySpecialReward(weights,seed);
    if(!selected)return false;
    const auto chosen=choices[*selected];
    const auto offer=chosen.asset;
    const auto firstDisplay=chosen.kind==SvFactoryBoxRewardKind::Weapon ? offer : factoryBoxResources_.weapons.front().asset;
    const auto &site=factoryBox_.sites[factoryBox_.active];
    const auto displayOrigin=SV_FactoryBoxDisplayOrigin(factoryBoxResources_,firstDisplay,site);
    const auto display=world_.spawnFactoryWeaponDisplay(firstDisplay,displayOrigin,site.angles);
    if(!display)return false;
    if(!world_.setFactoryWeaponDisplayMotion(*display,firstDisplay,
            SV_FactoryBoxRise(displayOrigin,now,now),site.angles)) {
        static_cast<void>(world_.freeEntity(*display));return false;
    }
    if(!world_.changeFactoryBattery(client.clientNum,-static_cast<std::int32_t>(BoxCost),state->spawnGeneration)) {
        static_cast<void>(world_.freeEntity(*display));return false;
    }
    ++factoryBox_.pulls;
    factoryBox_.bearRoll=factoryBox_.sites.size()>1 && factoryBoxResources_.bearModel &&
        SV_FactoryBoxBearRoll(factoryBox_.pulls,factoryBox_.moves,seed>>8);
    factoryBox_.owner=client.clientNum;factoryBox_.life=state->spawnGeneration;
    factoryBox_.seed=seed;factoryBox_.previewSeed=seed?seed:1;factoryBox_.offer=offer;factoryBox_.display=display;
    factoryBox_.rewardKind=chosen.kind;
    factoryBox_.phase=SvFactoryBoxPhase::Rolling;factoryBox_.started=now;factoryBox_.lastCycle=now;
    factoryBox_.effectCarriers=SV_StartFactoryBoxFx(world_,factoryBoxResources_,site);
    const bool lidQueued=site.lid && factoryBoxResources_.openAnimation &&
        // CODREF(cl_parse_packet_anims): type1 flags3 retains ancestor weights
        // and restarts an existing leaf via789E90->789B60 on repeated purchases.
        world_.setScriptModelAnimation(*site.lid,factoryBoxResources_.openAnimation,now,3);
    factoryInteractionSound(client.clientNum,"zmb_box_open");
    factoryInteractionSound(client.clientNum,"zmb_music_box");
    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
        "ZM BOX ROLL client="+std::to_string(client.clientNum)+" weapon="+std::to_string(offer)+
        " kind="+(chosen.kind==SvFactoryBoxRewardKind::Ammo?"ammo":"weapon")+
        " costRaw=1200 reconstructedPool=1 lidQueued="+std::to_string(lidQueued)+
        " nativeFxPair="+std::to_string(factoryBox_.effectCarriers[0].has_value() && factoryBox_.effectCarriers[1].has_value())+
        " display="+std::to_string(display->entityNum));
    return true;
}

void ServerCore::driveFactoryBox(std::span<const SvWorldClientInput> activeClients) {
    if(!factoryInteractablesEnabled_ || !world_.factoryInteractablesEnabled() || !mapTriggers_)return;
    const auto now=world_.snapshot().serverTime;
    if(!factoryBox_.initialized) {
        // The map trigger table can arrive before its script-model handles.
        // Stage a complete usable start site first; otherwise leave the owner
        // uninitialized so the next frame retries instead of permanently
        // recording an empty box map.
        std::vector<SvFactoryBoxSite> stagedSites;
        std::optional<std::size_t> stagedActive;
        for(const auto &t:mapTriggers_->triggers) {
            if(t.targetname!="treasure_chest_use")continue;
            const auto lids=world_.findMapEntities(t.target,"targetname");
            if(lids.empty())continue;
            const auto lid=world_.entity(lids.front());if(!lid)continue;
            auto baseName=std::string(t.target);const auto pos=baseName.find("lid");
            if(pos==std::string::npos)continue;baseName.replace(pos,3,"base");
            const auto bases=world_.findMapEntities(baseName,"targetname");
            if(bases.empty())continue;
            SvFactoryBoxSite site{t.triggerIndex,bases.front(),lids.front(),lid->currentOrigin,lid->currentAngles};
            site.rewardAngles=site.angles;
            site.rewardAngles[1]+=90;
            // CODREF(actor_grounded_adapter): authored Factory mapents link each
            // magic_box_lid_N to magic_box_weapon_spawn_N. The marker supplies
            // the display position. OLMOD(factory_box_display_axes): our native
            // weapon-selector renderer uses the firearm's longitudinal axis;
            // keep lid yaw (long edge), not the marker's perpendicular yaw.
            // The marker is also the original rise trajectory's base.
            auto markerName=std::string(t.target);markerName.replace(pos,3,"weapon_spawn");
            const auto markers=world_.findMapEntities(markerName,"targetname");
            if(markers.size()==1)if(const auto marker=world_.entity(markers.front())) {
                site.origin=marker->currentOrigin;
                site.rewardAngles=marker->currentAngles;
            }
            const auto rubble=world_.findMapEntities(std::string(t.noteworthy)+"_rubble","script_noteworthy");
            if(rubble.size()==1)site.rubble=rubble.front();
            if(t.noteworthy=="start_chest")stagedActive=stagedSites.size();
            stagedSites.push_back(site);
        }
        if(stagedSites.empty() || !stagedActive || !factoryBoxResources_.animationTree)return;
        factoryBox_.sites=std::move(stagedSites);
        factoryBox_.active=*stagedActive;
        for(std::size_t i=0;i<factoryBox_.sites.size();++i) {
            const auto &s=factoryBox_.sites[i];
            if(!showSite(world_,s,i==factoryBox_.active))return;
        }
        // Bind well before a purchase so client model creation already owns
        // the matching tree when the open command arrives.
        if(!world_.bindScriptModelAnimationTree(*factoryBox_.sites[factoryBox_.active].lid,
                factoryBoxResources_.animationTree))return;
        for(const auto name:{"zmb_box_open","zmb_music_box","zmb_box_cycle","zmb_box_select","zmb_box_close","zmb_box_move","zmb_box_poof","zmb_box_poof_land","zmb_box_raise","zmb_couch_slam","zmb_vox_ann_magicbox",
            "mus_perks_packa_sting","zmb_perks_packa_upgrade","zmb_perks_packa_ready","zmb_perks_packa_ticktock","zmb_packapunch_pickup"})
            if(factorySoundResolver_)factorySounds_[name]=factorySoundResolver_(name).value_or(0);
        factoryBox_.initialized=true;
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM BOX initialized sites="+std::to_string(factoryBox_.sites.size())+" weapons="+std::to_string(factoryBoxResources_.weapons.size()));
    }
    if(factoryBox_.poof && elapsed(now,factoryBox_.poofStarted,5000))freePresentation(world_,factoryBox_.poof);
    if(factoryBox_.phase==SvFactoryBoxPhase::Closed)return;
    if(factoryBox_.phase==SvFactoryBoxPhase::Closing) {
        if(elapsed(now,factoryBox_.started,BoxCloseMs))factoryBox_.phase=SvFactoryBoxPhase::Closed;
        return;
    }
    // Once a bear has refunded its owner the move belongs to the map, not that
    // player's life. Disconnect/death must not cancel it or refund a new life.
    if(factoryBox_.phase==SvFactoryBoxPhase::Bear) {
        const auto age=now-factoryBox_.started;
        const auto &site=factoryBox_.sites[factoryBox_.active];
        if(age>=2500 && factoryBox_.display) {
            if(!factoryBox_.lastCycle) {factoryInteractionSound(factoryBox_.owner,"zmb_box_raise");factoryBox_.lastCycle=1;}
            auto origin=site.origin;origin[2]+=40;
            SvNativeTrajectory motion{.type=7,.time=static_cast<std::int32_t>(factoryBox_.started+2500),
                .duration=3000,.base=origin,.delta={0,0,200}};
            if(age>=5500) {motion.type=3;motion.time+=3000;motion.duration=1000;motion.base[2]+=300;}
            static_cast<void>(world_.setFactoryBoxModelMotion(*factoryBox_.display,motion));
        }
        if(age<6500)return;
        freePresentation(world_,factoryBox_.display);
        SV_StopFactoryBoxFx(world_,factoryBox_.effectCarriers);
        // BO1 uses temporary non-solid pieces so map collision stays at home.
        // Native CODOL ET6 trajectories render the lift; no server-frame pose scans.
        std::size_t piece{};bool ready=true;
        for(const auto h:{site.base,site.lid}) {
            const auto e=h?world_.entity(*h):std::nullopt;
            if(!e) {ready=false;break;}
            auto &clone=factoryBox_.movingPieces[piece++];
            clone=world_.spawnScriptModel(e->networkState.modelIndex,e->scriptModelName,e->currentOrigin,e->currentAngles);
            if(!clone || !world_.setFactoryBoxModelMotion(*clone,
                SvNativeTrajectory{.type=3,.time=static_cast<std::int32_t>(now),.duration=5000,
                    .base=e->currentOrigin,.delta={0,0,10}})) {ready=false;break;}
        }
        if(!ready || !showSite(world_,site,false)) {
            for(auto &h:factoryBox_.movingPieces)freePresentation(world_,h);
            closeFactoryBox(now);return;
        }
        // Rubble appears after disappearance, not through the ascending box.
        if(site.rubble)if(const auto e=world_.entity(*site.rubble))
            static_cast<void>(world_.setScriptModelTransformAndActive(*site.rubble,e->currentOrigin,e->currentAngles,false));
        factoryInteractionSound(factoryBox_.owner,"zmb_box_move");
        // BO1 departure choreography; alias is resident in CODOL localized ZM.
        factoryInteractionSound(factoryBox_.owner,"zmb_vox_ann_magicbox");
        factoryBox_.phase=SvFactoryBoxPhase::Departing;factoryBox_.started=now;return;
    }
    if(factoryBox_.phase==SvFactoryBoxPhase::Departing) {
        // Preserve the native client-evaluated rise. Per-tick stationary
        // teleports made the reconstructed lateral shake visibly stutter.
        // Exact CODOL shake choreography remains unrecovered.
        if(!elapsed(now,factoryBox_.started,5000))return;
        const auto &site=factoryBox_.sites[factoryBox_.active];
        for(auto &h:factoryBox_.movingPieces)freePresentation(world_,h);
        static_cast<void>(showSite(world_,site,false));
        boxPoof(world_,factoryBox_,factoryBoxResources_,site,now);
        factoryInteractionSound(factoryBox_.owner,"zmb_box_poof");
        factoryBox_.phase=SvFactoryBoxPhase::Relocating;factoryBox_.started=now;return;
    }
    if(factoryBox_.phase==SvFactoryBoxPhase::Relocating) {
        if(!elapsed(now,factoryBox_.started,12000))return;
        auto seed=factoryBox_.seed;seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;
        const auto next=SV_FactoryBoxNextSite(factoryBox_.active,factoryBox_.sites.size(),seed);
        const auto &site=factoryBox_.sites[next];
        if(!showSite(world_,site,true) || !site.lid ||
            !world_.bindScriptModelAnimationTree(*site.lid,factoryBoxResources_.animationTree)) {
            static_cast<void>(showSite(world_,site,false));
            static_cast<void>(showSite(world_,factoryBox_.sites[factoryBox_.active],true));
            closeFactoryBox(now);
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM BOX relocation rejected; restoring previous site without retry loop");
            return;
        }
        factoryBox_.active=next;factoryBox_.seed=seed;factoryBox_.pulls=0;++factoryBox_.moves;
        if(factoryBoxResources_.closeAnimation)static_cast<void>(world_.setScriptModelAnimation(
            *site.lid,factoryBoxResources_.closeAnimation,now,3));
        boxPoof(world_,factoryBox_,factoryBoxResources_,site,now);
        factoryInteractionSound(factoryBox_.owner,"zmb_box_poof_land");
        factoryInteractionSound(factoryBox_.owner,"zmb_couch_slam");
        factoryBox_.phase=SvFactoryBoxPhase::Closing;factoryBox_.started=now;
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM BOX RELOCATED site="+std::to_string(next)+" moves="+std::to_string(factoryBox_.moves)+" reconstructedOrder=1");
        return;
    }
    const auto owner=world_.playerState(factoryBox_.owner);
    const bool connected=std::ranges::any_of(activeClients,[&](const auto &c){return c.clientNum==factoryBox_.owner && c.gameplayState==ClientGameplayState::Playing;});
    if(!connected || !owner || !owner->health || owner->spawnGeneration!=factoryBox_.life) {closeFactoryBox(now);return;}
    const auto &site=factoryBox_.sites[factoryBox_.active];
    if(factoryBox_.phase==SvFactoryBoxPhase::Rolling && factoryBox_.display) {
        // Publish phase changes on the simulation tick, independently of the
        //150ms cosmetic selector cadence (the native middle phase is100ms).
        if(const auto display=world_.entity(*factoryBox_.display))
            static_cast<void>(world_.setFactoryWeaponDisplayMotion(*factoryBox_.display,
                display->networkState.weaponAssetIndex,
                SV_FactoryBoxRise(SV_FactoryBoxDisplayOrigin(factoryBoxResources_,
                    display->networkState.weaponAssetIndex,site),factoryBox_.started,now),site.angles));
    }
    if(factoryBox_.phase==SvFactoryBoxPhase::Rolling && elapsed(now,factoryBox_.started,BoxRollMs)) {
        if(factoryBox_.bearRoll) {
            freePresentation(world_,factoryBox_.display);
            auto origin=site.origin;origin[2]+=40;
            factoryBox_.display=world_.spawnScriptModel(factoryBoxResources_.bearModel,"zombie_teddybear",origin,site.rewardAngles);
            static_cast<void>(world_.changeFactoryBattery(factoryBox_.owner,BoxCost,factoryBox_.life));
            cursorHintTrigger_.erase(factoryBox_.owner);
            if(!factoryBox_.display) {closeFactoryBox(now);return;}
            factoryBox_.phase=SvFactoryBoxPhase::Bear;factoryBox_.started=now;
            factoryInteractionSound(factoryBox_.owner,"zmb_box_select");
            factoryBox_.lastCycle=0;
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM BOX BEAR pulls="+std::to_string(factoryBox_.pulls)+" refundRaw=1200 bo1Policy=1");
            return;
        }
        factoryBox_.phase=SvFactoryBoxPhase::Offer;factoryBox_.started=now;
        auto origin=SV_FactoryBoxDisplayOrigin(factoryBoxResources_,factoryBox_.offer,site);origin[2]+=40;
        if(factoryBox_.rewardKind==SvFactoryBoxRewardKind::Ammo) {
            // CODREF(actor_grounded_adapter): Prototype590750 ammo entity537
            // yaw135 matches its authored lid yaw315+180, not marker yaw45.
            // This model has a different authored forward axis from the bear.
            auto ammoAngles=site.angles;
            ammoAngles[1]=std::remainder(ammoAngles[1]+180.0f,360.0f);
            const auto ammo=world_.spawnScriptModel(factoryBoxResources_.ammoModel,"zombie_ammocan",origin,ammoAngles);
            if(!ammo) {
                static_cast<void>(world_.changeFactoryBattery(factoryBox_.owner,BoxCost,factoryBox_.life));
                closeFactoryBox(now);return;
            }
            freePresentation(world_,factoryBox_.display);factoryBox_.display=ammo;
        } else if(factoryBox_.display)static_cast<void>(world_.setFactoryWeaponDisplay(*factoryBox_.display,factoryBox_.offer,origin,site.angles));
        // Unattended offers descend during their reconstructed ten-second
        // claim window, keeping the reward-specific centering and orientation.
        const SvNativeTrajectory descending{3,static_cast<std::int32_t>(now),
            static_cast<std::int32_t>(BoxOfferMs),origin,{0,0,-40.f/(BoxOfferMs*.001f)}};
        const bool moving=factoryBox_.display &&
            (factoryBox_.rewardKind==SvFactoryBoxRewardKind::Ammo
                ? world_.setFactoryBoxModelMotion(*factoryBox_.display,descending)
                : world_.setFactoryWeaponDisplayMotion(*factoryBox_.display,factoryBox_.offer,descending,site.angles));
        if(!moving) {closeFactoryBox(now);return;}
        // zmb_box_select is box_bear_select.wav; ordinary offers must not
        // play the teddy selection cue.
        cursorHintTrigger_.erase(factoryBox_.owner);
    } else if(factoryBox_.phase==SvFactoryBoxPhase::Rolling && elapsed(now,factoryBox_.lastCycle,150)) {
        factoryBox_.lastCycle=now;
        // OLMOD(factory_box_preview): advance a private visual RNG, never the
        // already-selected reward. Suppress consecutive repeats where possible.
        auto visual=factoryBox_.previewSeed;
        visual^=visual<<13;visual^=visual>>17;visual^=visual<<5;
        factoryBox_.previewSeed=visual;
        std::vector<std::uint16_t> weights;
        const auto previous=factoryBox_.display?world_.entity(*factoryBox_.display):std::nullopt;
        for(const auto &entry:factoryBoxResources_.weapons)
            weights.push_back(factoryBoxResources_.weapons.size()>1 && previous &&
                previous->networkState.weaponAssetIndex==entry.asset ? 0 : SV_FactoryPreviewWeight(entry.name));
        const auto index=SV_SelectFactorySpecialReward(weights,visual);
        if(!index)return;
        const auto &w=factoryBoxResources_.weapons[*index];
        if(factoryBox_.display)static_cast<void>(world_.setFactoryWeaponDisplayMotion(*factoryBox_.display,w.asset,
            SV_FactoryBoxRise(SV_FactoryBoxDisplayOrigin(factoryBoxResources_,w.asset,site),
                factoryBox_.started,now),site.angles));
    } else if(factoryBox_.phase==SvFactoryBoxPhase::Offer && elapsed(now,factoryBox_.started,BoxOfferMs))closeFactoryBox(now);
}
}
