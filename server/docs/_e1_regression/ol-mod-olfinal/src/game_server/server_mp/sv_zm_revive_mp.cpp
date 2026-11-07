#include "sv_snapshot_mp.hpp"
#include "sv_perks_mp.hpp"
#include "../../shared/RuntimeLog.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    // CODREF(original Factory60150/514050): hide ordinary weapons, independent
    // full pistol clip and90 reserve; restore pre-down ammo at72750/521150.
    // Pistol preference beyond the two observed loadouts remains reconstruction.
    bool SvServerWorld::prepareZombieDownedInventory(SvGameClient &client,
        ZombieDownedInventory &saved) const
    {
        if (!client.resolvedLoadout) return false;
        auto loadout=*client.resolvedLoadout;
        std::optional<SvResolvedWeapon> pistol;
        for (const auto &weapon:{loadout.secondary,loadout.primary})
            if (!pistol && weapon.weaponClass==5 && weapon.clipSize && weapon.ammoIndex)
                pistol=weapon;
        if (!pistol && zombieFallbackPistol_ && weaponDefinitionResolver_)
        {
            SvResolvedWeapon fallback;
            if (weaponDefinitionResolver_(zombieFallbackPistol_,fallback) &&
                fallback.weaponClass==5 && fallback.clipSize && fallback.ammoIndex)
                pistol=fallback;
        }
        if (!pistol) return false; // Asset failure: do not invent a weapon identity.
        if (loadout.primary.weaponAssetIndex!=pistol->weaponAssetIndex)
            loadout.secondary=*pistol;
        else loadout.primary=*pistol;
        if (!SV_IsResolvedLoadoutValid(loadout)) return false;
        auto &ps=client.playerState;
        saved={.generation=ps.spawnGeneration,.weapon=ps.currentWeaponAssetIndex,
            .offhand=ps.offhandWeaponAssetIndex,.reward=ps.rewardActionWeapon,
            .offhandSlots=ps.offhandWeaponSlots(),.held=ps.heldWeapons,
            .clips=ps.ammoClips,.pools=ps.ammoPools,.loadout=client.resolvedLoadout};
        if (ps.clientNum<weaponGrants_.size() && weaponGrants_[ps.clientNum].active)
            saved.grantedWeapon=weaponGrants_[ps.clientNum].weapon;
        client.resolvedLoadout=std::move(loadout);
        ps.heldWeapons={}; ps.ammoClips={}; ps.ammoPools={};
        ps.heldWeapons[0].weaponAssetIndex=pistol->weaponAssetIndex;
        ps.heldWeapons[0].heldBefore=true;
        ps.ammoClips[0].clipIndex=pistol->clipIndex;
        ps.ammoClips[0].count[0]=pistol->clipSize;
        ps.ammoPools[0].ammoIndex=pistol->ammoIndex; ps.ammoPools[0].count=90;
        ps.currentWeaponAssetIndex=pistol->weaponAssetIndex;
        ps.offhandWeaponAssetIndex=ps.offhandWeaponSlotA=ps.offhandWeaponSlotB=ps.offhandWeaponSlotC=0;
        ps.rewardActionWeapon=0; ps.grenadeTimeLeft=0;
        ps.weaponState={}; ps.weaponTime={}; ps.weaponDelay={}; ps.weaponHandFlags={};
        for (auto &anim:ps.weaponAnim) anim=static_cast<std::uint16_t>((~anim)&0x400);
        return true;
    }

    void SvServerWorld::restoreZombieDownedInventory(SvGameClient &client,
        const ZombieDownedInventory &saved)
    {
        auto &ps=client.playerState;
        if (ps.spawnGeneration!=saved.generation) return;
        ps.heldWeapons=saved.held; ps.ammoClips=saved.clips; ps.ammoPools=saved.pools;
        ps.currentWeaponAssetIndex=saved.weapon; ps.offhandWeaponAssetIndex=saved.offhand;
        ps.offhandWeaponSlotA=saved.offhandSlots[0]; ps.offhandWeaponSlotB=saved.offhandSlots[1];
        ps.offhandWeaponSlotC=saved.offhandSlots[2]; ps.rewardActionWeapon=saved.reward;
        ps.weaponState={}; ps.weaponTime={}; ps.weaponDelay={}; ps.weaponHandFlags={};
        ps.grenadeTimeLeft=0; client.resolvedLoadout=saved.loadout;
        if (ps.clientNum<weaponGrants_.size())
            weaponGrants_[ps.clientNum]=saved.grantedWeapon
                ? SvWeaponGrant{.weapon=*saved.grantedWeapon,.active=true} : SvWeaponGrant{};
        for (auto &anim:ps.weaponAnim) anim=static_cast<std::uint16_t>((~anim)&0x400);
    }

    void SvServerWorld::sendZombieDownedPresentation(std::uint32_t client,
        bool downed,std::uint16_t weapon)
    {
        if (!reliableCommandSender_) return;
        // CODREF(613A40): 'i' ->611920 parses duration,blur,flags,priority;
        // '3' ->46CEF0 type5. Exact original Factory down/revive command pair.
        reliableCommandSender_(client,downed?"i 1000 2.000000 0 1":"i 100 0.000000 0 1");
        if (downed) reliableCommandSender_(client,"3 \"grayscale\" 1000");
        else reliableCommandSender_(client,"3 \"zm_factory_sh\" 0");
        if (weapon) reliableCommandSender_(client,"a "+std::to_string(weapon));
        if (const auto owner=clientStates_.find(client);owner!=clientStates_.end())
            reliableCommandSender_(client,"y "+std::to_string(owner->second.client.playerState.offhandWeaponAssetIndex));
    }

    std::optional<SvPlayerState> SV_PlayerSnapshotView(
        const SvSnapshotFrame &frame, const std::uint32_t recipient)
    {
        auto subject = recipient;
        const auto follow = frame.zombieSpectatorTargets.find(recipient);
        if (follow != frame.zombieSpectatorTargets.end()) subject = follow->second;
        const auto state = std::ranges::find(frame.playerStates, subject, &SvPlayerState::clientNum);
        if (state == frame.playerStates.end()) return std::nullopt;
        auto view = *state;
        if (follow != frame.zombieSpectatorTargets.end())
        {
            // CODREF(1649370): CGAME_FOLLOWING consumer45CE10 tests ps+10
            // bit800. Original zm20-21-43,20-34-14,21-43-53 carry field54
            // 0x2800 and field59=the watched client, retaining its pm_type.
            // Keep transient subject flags, replace only ownership bits.
            view.otherFlags = (view.otherFlags & ~0x1000u) | 0x2800u;
        }
        if (const auto held=frame.zombieReviverGenerations.find(subject);
            held!=frame.zombieReviverGenerations.end() && held->second==view.spawnGeneration)
        {
            view.pmFlags |= SvPmFlagsMatchEndFrozen;
            view.velocity={};
        }
        if(const auto held=frame.factoryTravelerGenerations.find(subject);
            held!=frame.factoryTravelerGenerations.end() && held->second==view.spawnGeneration) {
            // CODREF(factory-arrival-lock): CODOL41CB40 movement/input gate.
            // CODOL53C650/53C6AA and the existing pre-class path consume NoDraw.
            // Recipient-only projection: never alter inventory or locked-entity flags.
            view.pmFlags |= SvPmFlagsMatchEndFrozen;
            view.eFlags |= SvEFlagsNoDraw;
            view.velocity={};
        }
        return view;
    }

    bool SvServerWorld::consumeZombieDown(const std::uint32_t clientNum)
    {
        if (!zombieDownedState(clientNum)) return false;
        auto &down=zombieDowned_.at(clientNum);
        if (down.scoreRecorded) return false;
        down.scoreRecorded=true;
        return true;
    }

    bool SvServerWorld::zombieDowned(const std::uint32_t clientNum) const
    {
        const auto down = zombieDownedState(clientNum);
        return down && !down->bledOut;
    }

    std::optional<SvZombieDownedState> SvServerWorld::zombieDownedState(
        const std::uint32_t clientNum) const
    {
        const auto down = zombieDowned_.find(clientNum);
        const auto player = clientStates_.find(clientNum);
        if (down == zombieDowned_.end() || player == clientStates_.end() ||
            player->second.client.gameplayState != ClientGameplayState::Playing ||
            down->second.generation != player->second.client.playerState.spawnGeneration)
            return std::nullopt;
        return down->second;
    }

    std::optional<std::uint32_t> SvServerWorld::zombieReviveTarget(
        const std::uint32_t reviver) const
    {
        if (!zombieRevivalActive_ || zombieTeamWiped_ || matchCompleted_)
            return std::nullopt;
        const auto player = clientStates_.find(reviver);
        if (player == clientStates_.end() ||
            player->second.client.gameplayState != ClientGameplayState::Playing ||
            !player->second.client.playerState.health || zombieDowned(reviver))
            return std::nullopt;
        const auto &ps = player->second.client.playerState;
        std::optional<std::uint32_t> target;
        auto closest = SvZombieReviveRadius * SvZombieReviveRadius;
        for (const auto &[clientNum, state] : zombieDowned_)
        {
            if (clientNum == reviver || !zombieDowned(clientNum)) continue;
            const auto &victim = clientStates_.at(clientNum).client.playerState;
            const auto x = victim.origin[0] - ps.origin[0];
            const auto y = victim.origin[1] - ps.origin[1];
            const auto z = victim.origin[2] - ps.origin[2];
            const auto distance = x*x + y*y + z*z;
            if (distance > closest || (distance == closest && target && clientNum > *target)) continue;
            auto start = ps.origin, end = victim.origin;
            start[2] += ps.viewHeightCurrent; end[2] += 18.0f;
            // Fail closed without native collision. A nearby player through a
            // closed door/floor is not a reachable revive target.
            const auto hit = traceCapsule(start, end, {},
                PlayerCollisionContentMask & ~PlayerCollisionContents,
                SvTraceEntityFilter{.passEntityNum = reviver});
            if (!hit || hit->allSolid || hit->startSolid || hit->fraction < 1.0f) continue;
            target = clientNum; closest = distance;
        }
        return target;
    }

    // OLMOD(revive-treatment-hold): project owner, native movement/view consumers.
    bool SvServerWorld::zombieReviveHeld(const std::uint32_t reviver) const
    {
        const auto helper=playerState(reviver);
        if (!helper || !helper->health || helper->pmType!=SvPmTypeNormal ||
            !zombieRevivalActive_ || zombieTeamWiped_ || matchCompleted_) return false;
        for (const auto &[victim,down]:zombieDowned_)
            if (!down.bledOut && down.reviver==reviver &&
                down.reviverGeneration==helper->spawnGeneration &&
                snapshot_.serverTime-down.lastSeen<=500 &&
                zombieReviveTarget(reviver)==victim) return true;
        return false;
    }

    bool SvServerWorld::processZombieReviveUse(
        const std::uint32_t reviver, const bool held)
    {
        const auto target = held ? zombieReviveTarget(reviver) : std::nullopt;
        for (auto &[clientNum, down] : zombieDowned_)
            if (down.reviver == reviver && target != clientNum)
            {
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM REVIVE cancelled helper=" + std::to_string(reviver) +
                    " target=" + std::to_string(clientNum));
                down.cancel();
            }
        if (!target) return false;
        auto &down = zombieDowned_.at(*target);
        auto &helper = clientStates_.at(reviver).client;
        const auto now = snapshot_.serverTime;
        // One claimant. A disconnected/stale holder cannot reserve a victim.
        if (down.reviver && now - down.lastSeen > 500) down.cancel();
        if (down.reviver && down.reviver != reviver) return false;
        if (!down.reviver || down.reviverGeneration != helper.playerState.spawnGeneration)
        {
            down.cancel();
            down.reviver = reviver;
            down.reviverGeneration = helper.playerState.spawnGeneration;
            down.startedAt = now;
            const auto abilities = effectivePlayerAbilities(reviver, down.reviverGeneration);
            const auto rate = abilities ? SV_AbilityValue(*abilities, SvAbilityReviveRate, 1.0f) : 1.0f;
            down.duration = static_cast<std::uint32_t>(SvZombieReviveMilliseconds /
                (std::isfinite(rate) ? std::clamp(rate, 1.0f, 3.0f) : 1.0f));
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM REVIVE started helper=" + std::to_string(reviver) +
                " target=" + std::to_string(*target) + " treatmentHudOwner=" +
                std::to_string(reviver) + " duration=" + std::to_string(down.duration));
        }
        down.lastSeen = now;
        if (now - down.startedAt < down.duration) return false;
        auto &victim = clientStates_.at(*target).client;
        if (const auto saved=zombieDownedInventories_.find(*target);
            saved!=zombieDownedInventories_.end())
        {
            restoreZombieDownedInventory(victim,saved->second);
            zombieDownedInventories_.erase(saved);
        }
        victim.playerState.health = victim.playerState.maxHealth;
        victim.playerState.pmType = SvPmTypeNormal;
        victim.playerState.pmFlags &= ~3u;
        victim.damageFeedbackState = {};
        SV_OverlayPlayerStateToNative(victim.playerState, victim.nativePlayerState);
        sendZombieDownedPresentation(*target,false,victim.playerState.currentWeaponAssetIndex);
        healthRegen_.erase(*target);
        zombieDowned_.erase(*target);
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM REVIVE complete helper=" + std::to_string(reviver) +
            " target=" + std::to_string(*target));
        return true;
    }

    // OLMOD(factory-cooperative-revive): generation-owned reconstruction policy.
    // CODREF: CODOL 1649370 PM_CheckDuck 0x417D10 (0x417FFB) forces prone for
    // pm_type 7. BO1 PlayerCmd_Revive 0x605E90 restores health/stance; its type
    // value is different. TODO(CODOL): recover original timers and loss flow;
    // see .agents/research/factory-cooperative-revive-20260928.md.
    void SvServerWorld::stepZombieRevives()
    {
        if (!zombieRevivalEnabled_) return;
        std::erase_if(zombieDowned_, [this](const auto &entry) {
            const auto player = clientStates_.find(entry.first);
            return player == clientStates_.end() ||
                player->second.client.gameplayState != ClientGameplayState::Playing ||
                player->second.client.playerState.spawnGeneration != entry.second.generation;
        });
        std::erase_if(zombieDownedInventories_,[this](const auto &entry) {
            return !zombieDownedState(entry.first) ||
                zombieDowned_.at(entry.first).generation!=entry.second.generation;
        });
        std::size_t participants{}, standing{};
        for (const auto &[clientNum, state] : clientStates_)
        {
            if (state.client.gameplayState != ClientGameplayState::Playing ||
                !state.client.appliedSpawnSequence) continue;
            ++participants;
            if (state.client.playerState.health && !zombieDowned(clientNum)) ++standing;
        }
        if (!zombieRevivalActive_ && participants >= 2)
        {
            zombieRevivalActive_ = true;
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM REVIVE armed: cooperative damage enabled");
        }
        if (!zombieRevivalActive_ || zombieTeamWiped_) return;
        if (participants && !standing && !zombieDowned_.empty())
        {
            zombieTeamWiped_ = true;
            setMatchCompleted(true);
            for (auto &[clientNum, down] : zombieDowned_) down.cancel();
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM REVIVE team wiped: zombie results requested");
            return;
        }
        const auto now = snapshot_.serverTime;
        for (auto &[clientNum, down] : zombieDowned_)
        {
            if (down.bledOut)
            {
                if (zmPresentationRound_ > down.round)
                    clientStates_.at(clientNum).client.respawnTime = now + 1;
                continue;
            }
            if (down.reviver && (now - down.lastSeen > 500 ||
                    zombieReviveTarget(*down.reviver) != clientNum)) down.cancel();
            // A held revive pauses bleedout. It cannot be held without fresh
            // committed commands, range and a surviving claimant.
            if (down.reviver) continue;
            if (now - down.downedAt < SvZombieBleedoutMilliseconds) continue;
            const auto result = finishPlayerDamage(SvPlayerDamagePayload{
                .targetClientNum = clientNum, .damage = 1,
                .methodOfDeath = SvMethodOfDeathSuicide});
            if (result == FinishPlayerDamageResult::Applied)
            {
                down.bledOut = true; down.cancel();
                sendZombieDownedPresentation(clientNum,false,0);
                clientStates_.at(clientNum).client.respawnTime.reset();
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM REVIVE bleedout client=" + std::to_string(clientNum));
            }
        }
    }
}
