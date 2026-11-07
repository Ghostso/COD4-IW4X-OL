#include "sv_main_mp.hpp"
#include "sv_zm_teleporters_mp.hpp"

#include "../../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <ranges>
#include <string>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::uint16_t FactoryTeleportCoreTrigger = 38;
        constexpr std::array<std::uint16_t, 3> FactoryTeleportPadTriggers{
            39, 41, 40,
        };
        constexpr std::uint32_t FactoryTeleporterLinkMilliseconds = FactoryLinkDuration;
        // RECONSTRUCTION: the capture proves a cooldown state but not this
        // duration.  Keep the value local and plainly named for replacement.
        constexpr std::uint32_t FactoryTeleporterCooldownMilliseconds = FactoryTeleportCooldown;
        // RECONSTRUCTION: the exact capture did not prove an economic debit.
        // The recorded prompt displays1.5 battery units, expressed in the current
        // Factory raw-battery numerator (1.2k per displayed battery unit).
        constexpr std::uint32_t FactoryTeleporterCostRaw = FactoryTeleportPrice;
        constexpr float FactoryCoreArrivalYaw = 270.0f;
        constexpr float FactoryArrivalOccupiedRadius = 64.0f;

        // Extracted zm_factory_sh origin_teleport_player_0/_1/_3/_2 records.
        // These are candidates, not a claimed retail player-index mapping.
        constexpr std::array<std::array<float, 3>, 4> FactoryCoreArrivals{{
            { -88.0f, 256.0f, 116.0f },
            { -24.0f, 256.0f, 116.0f },
            { -88.0f, 328.0f, 116.0f },
            { -24.0f, 328.0f, 116.0f },
        }};

        [[nodiscard]] std::optional<std::size_t> factoryPadIndex(
            const SvMapTrigger &trigger)
        {
            for (std::size_t pad = 0; pad < FactoryTeleportPadTriggers.size();
                 ++pad)
            {
                if (trigger.triggerIndex == FactoryTeleportPadTriggers[pad])
                    return pad;
            }
            return std::nullopt;
        }

        [[nodiscard]] bool isFactoryCore(const SvMapTrigger &trigger)
        {
            return trigger.triggerIndex == FactoryTeleportCoreTrigger;
        }

        [[nodiscard]] float squaredDistance(
            const std::array<float, 3> &first,
            const std::array<float, 3> &second)
        {
            const auto x = first[0] - second[0];
            const auto y = first[1] - second[1];
            const auto z = first[2] - second[2];
            return x * x + y * y + z * z;
        }

        [[nodiscard]] std::optional<SvEntityHandle> uniqueMapEntity(
            SvServerWorld &world, const std::string_view targetName)
        {
            const auto entities = world.findMapEntities(targetName, "targetname");
            return entities.size() == 1 ? std::optional{entities.front()} :
                std::nullopt;
        }
    }

    // OLMOD(factory-teleporters): generation-owned emitter with bounded lifetime.
    // These assets may loop; never leave unowned world particles after use.
    void ServerCore::emitFactoryTeleportFx(std::uint16_t effect,const std::array<float,3>&origin,const std::array<float,3>&angles) {
        if(!effect || !factoryTeleporterResources_.model || factoryTeleporterResources_.bone==255 ||
            factoryTeleportEffects_.size()>=16)return;
        const auto carrier=world_.spawnScriptModel(factoryTeleporterResources_.model,"tag_origin",origin,angles);
        if(!carrier)return;
        if(!world_.queueScriptModelFxEvent(*carrier,effect,factoryTeleporterResources_.bone)) {
            static_cast<void>(world_.freeEntity(*carrier));return;
        }
        factoryTeleportEffects_.emplace_back(*carrier,world_.snapshot().serverTime);
    }

    // CODREF(actor_grounded_adapter): Factory authored triggers38..41 and recorded
    // ZOMBIE_*TPAD/TELEPORT_TO_CORE hints. The client IDA6C8500/6C87A0 owns a
    // different UI channel, not this server controller. See September29 review.
    std::string ServerCore::factoryTeleportHint(
        const std::uint32_t clientNum,
        const SvMapTrigger &trigger) const
    {
        if (!factoryTeleportersEnabled_ ||
            !world_.factoryInteractablesEnabled() || matchGameType_ != "zm" ||
            matchMapName_ != "zm_factory_sh")
        {
            return {};
        }

        const auto player = world_.playerState(clientNum);
        if (!player || !player->health || player->pmType != 0)
            return {};

        if(!factoryPadIndex(trigger) && !isFactoryCore(trigger))return {};
        if(!zmPowerOn_)return "ZOMBIE_NEED_POWER";
        const auto now = world_.snapshot().serverTime;
        if (const auto pad = factoryPadIndex(trigger))
        {
            if (factoryTeleporters_.travel || now < factoryTeleporters_.cooldown)
                return "ZOMBIE_TELEPORT_COOLDOWN";
            if (factoryTeleporters_.links[*pad])
            {
                return std::string{"ZOMBIE_TELEPORT_TO_CORE"} +
                    HintArgumentLiteral + "1.5";
            }
            return factoryTeleporters_.pending(now) ? "ZOMBIE_LINK_ACTIVE" : "ZOMBIE_POWER_UP_TPAD";
        }

        if (!isFactoryCore(trigger))
            return {};
        if (factoryTeleporters_.pending(now))return "ZOMBIE_LINK_TPAD";
        return {};
    }

    // OLMOD(factory-teleporters): server-authoritative power/hull/life/funds transaction.
    // Team completion and30s deadline are reconstruction, not recovered script.
    bool ServerCore::processFactoryTeleportUse(
        const SvWorldClientInput &client,
        const SvMapTrigger &trigger)
    {
        if (!factoryTeleportersEnabled_ || !zmPowerOn_ ||
            !world_.factoryInteractablesEnabled() || matchGameType_ != "zm" ||
            matchMapName_ != "zm_factory_sh" ||
            client.gameplayState != ClientGameplayState::Playing)
        {
            return false;
        }
        const auto player = world_.playerState(client.clientNum);
        if (!player || !player->health || player->pmType != 0)
            return false;
        const auto now = world_.snapshot().serverTime;

        if (const auto pad = factoryPadIndex(trigger))
        {
            if (!factoryTeleporters_.links[*pad])
            {
                if(!factoryTeleporters_.begin(*pad,now,std::pair{client.clientNum,player->spawnGeneration}))return false;
                if(factoryTeleporterResources_.padStart)
                    emitFactoryTeleportFx(factoryTeleporterResources_.padStart,trigger.origin);
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM TELEPORT LINK START client=" +
                    std::to_string(client.clientNum) + " pad=" +
                    std::to_string(*pad));
                return true;
            }

            if (factoryTeleporters_.travel || now < factoryTeleporters_.cooldown || factoryTeleporters_.pending(now))
                return false;

            if(factoryBo1TravelEnabled_)
                return beginFactoryTravel(client.clientNum,player->spawnGeneration,*pad,trigger.origin);

            // Pick an extracted core origin only when no other active, living
            // client occupies its arrival bubble.  teleportFactoryPlayer then
            // performs the authoritative capsule/world collision validation.
            bool teleported{};
            for (const auto &candidate : FactoryCoreArrivals)
            {
                const auto occupied = std::ranges::any_of(
                    factoryTeleporters_.activeClients, [&](const std::uint32_t other) {
                        if (other == client.clientNum)
                        {
                            return false;
                        }
                        const auto state = world_.playerState(other);
                        return state && state->health &&
                            squaredDistance(state->origin, candidate) <
                                FactoryArrivalOccupiedRadius *
                                FactoryArrivalOccupiedRadius;
                    });
                if (!occupied)
                {
                    // The occupancy check cannot see map geometry.  Keep trying
                    // candidates until the world-owned capsule test accepts one.
                    teleported = world_.teleportFactoryPlayer(client.clientNum,
                        player->spawnGeneration, candidate,
                        FactoryCoreArrivalYaw, FactoryTeleporterCostRaw);
                    if (teleported) {
                        if(factoryTeleporterResources_.beam) {
                            emitFactoryTeleportFx(factoryTeleporterResources_.beam,trigger.origin);
                            emitFactoryTeleportFx(factoryTeleporterResources_.beam,candidate);
                        }
                        break;
                    }
                }
            }
            if (!teleported)
            {
                return false;
            }
            factoryTeleporters_.cooldown =
                now + FactoryTeleporterCooldownMilliseconds;
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM TELEPORT RETURN client=" +
                std::to_string(client.clientNum) + " pad=" +
                std::to_string(*pad) + " costRaw=" +
                std::to_string(FactoryTeleporterCostRaw));
            return true;
        }

        if (!isFactoryCore(trigger) || !factoryTeleporters_.pending(now))return false;
        const auto pad=static_cast<std::size_t>(factoryTeleporters_.pendingPad);
        if(!factoryTeleporters_.complete(now))return false;
        const auto effect=factoryTeleporters_.allPadsLinked() ?
            factoryTeleporterResources_.linkAll : factoryTeleporterResources_.linkSingle;
        emitFactoryTeleportFx(effect,trigger.origin);
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM TELEPORT LINK COMPLETE client=" +
            std::to_string(client.clientNum) + " pad=" + std::to_string(pad) +
            " allPadsLinked=" +
            std::to_string(factoryTeleporters_.allPadsLinked()));
        return true;
    }

    // CODREF(actor_grounded_adapter): recorded pack_door native ET6 endpoints;
    // unlocking after3links is reconstruction. Clip releases only after motion.
    void ServerCore::driveFactoryTeleporters(
        const std::span<const SvWorldClientInput> activeClients)
    {
        factoryTeleporters_.activeClients.clear();
        for (const auto &client : activeClients)
            if (client.gameplayState == ClientGameplayState::Playing)
                factoryTeleporters_.activeClients.push_back(client.clientNum);
        const auto now = world_.snapshot().serverTime;
        if(factoryBo1TravelEnabled_)driveFactoryTravel();
        std::erase_if(factoryTeleportEffects_,[&](const auto &entry) {
            if(now-entry.second<5000)return false;
            static_cast<void>(world_.freeEntity(entry.first));return true;
        });
        if(factoryTeleporters_.pendingPad>=0 && !factoryTeleporters_.pending(now)) {
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,"ZM TELEPORT LINK EXPIRED");
            factoryTeleporters_.clearPendingLink();
        }

        // CODREF(Factory173250/177150/180150): power precedes the machine's
        // hum, followed three seconds later by blue glow on bones7,5,6,4.
        // Resolve named tags on the resident ON model. The four-second initial
        // delay approximates this sample, not a recovered server script timer.
        if (zmPowerOn_ && !factoryTeleporters_.poweredAt)
            factoryTeleporters_.poweredAt=now;
        if (factoryTeleporters_.poweredAt && !factoryTeleporters_.packMachineStarted &&
            now-*factoryTeleporters_.poweredAt>=4000 && factoryTeleporterResources_.packModelOn)
        {
            const auto machine=uniqueMapEntity(world_,"pf745_auto2");
            if (machine && world_.setScriptModelIndex(*machine,
                    factoryTeleporterResources_.packModelOn,"zombie_vending_packapunch_on"))
            {
                factoryTeleporters_.packMachineStarted=true;
                factoryTeleporters_.packMachineStartedAt=now;
                factoryTeleporters_.packMachineHandle=std::pair{machine->entityNum,machine->generation};
                static_cast<void>(world_.queueScriptModelSoundEvent(*machine,factoryTeleporterResources_.packHum));
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,"ZM PAP POWERED model and hum");
            }
        }
        if (factoryTeleporters_.packMachineStarted && !factoryTeleporters_.packMachineGlowing &&
            now-factoryTeleporters_.packMachineStartedAt>=3000)
        {
            // One attempt: missing artwork never becomes a per-frame asset/event retry loop.
            factoryTeleporters_.packMachineGlowing=true;
            const auto saved=factoryTeleporters_.packMachineHandle;
            if (saved && factoryTeleporterResources_.packGlow &&
                std::ranges::none_of(factoryTeleporterResources_.packGlowBones,[](auto b){return b==255;}))
            {
                const SvEntityHandle machine{saved->first,saved->second};
                unsigned queued{};
                for (const auto bone:factoryTeleporterResources_.packGlowBones)
                    queued+=world_.queueScriptModelFxEvent(machine,factoryTeleporterResources_.packGlow,bone)?1u:0u;
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM PAP GLOW queued="+std::to_string(queued));
            }
        }

        if ((std::ranges::count(factoryTeleporters_.links,true) <= factoryTeleporters_.packDoorCompletedLinks && factoryTeleporters_.packDoorCompletedLinks<3) ||
            factoryTeleporters_.packAPunchUnlocked ||
            matchGameType_ != "zm" || matchMapName_ != "zm_factory_sh")
        {
            return;
        }

        if (factoryTeleporters_.packDoorCompletedLinks<3 && !factoryTeleporters_.packDoorOpening)
        {
            const auto door = uniqueMapEntity(world_, "pack_door");
            const auto clip = uniqueMapEntity(world_, "pack_door_clip");
            const auto current = door ? world_.entity(*door) : std::nullopt;
            if (!door || !clip || !current)
                return;
            factoryTeleporters_.packDoorOpening = true;
            factoryTeleporters_.packDoorOpenStarted = now;
            factoryTeleporters_.packDoorHandle =
                std::pair{door->entityNum, door->generation};
            factoryTeleporters_.packDoorClosedOrigin = current->currentOrigin;
            factoryTeleporters_.packDoorAngles = current->currentAngles;
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM PAP GATE OPEN START");
        }

        if(factoryTeleporters_.packDoorCompletedLinks<3) {
            if (!factoryTeleporters_.packDoorHandle)
                return;
            const SvEntityHandle door{
                .entityNum = factoryTeleporters_.packDoorHandle->first,
                .generation = factoryTeleporters_.packDoorHandle->second,
            };
            const auto elapsed = now - factoryTeleporters_.packDoorOpenStarted;
            const bool finalLink=factoryTeleporters_.packDoorCompletedLinks==2;
            const auto motion=SV_FactoryPackDoorStep(factoryTeleporters_.packDoorClosedOrigin,
                factoryTeleporters_.packDoorOpenStarted,now,finalLink);
            if (!world_.setFactoryPackDoorMotion(door,motion,static_cast<std::int32_t>(now)))
                return; // Fail closed; never restart from a partly moved pose.
            if(elapsed<SV_FactoryPackDoorDuration(finalLink))return;
            ++factoryTeleporters_.packDoorCompletedLinks;
            factoryTeleporters_.packDoorOpening=false;
            factoryTeleporters_.packDoorHandle.reset();
            if(factoryTeleporters_.packDoorCompletedLinks<3)return;

        }

        // Collision is released only after the visible door reached the
        // reconstructed fully lowered endpoint. Never hide the model as an opening
        // shortcut: its open/close motion is observed on retail entity 90.
        const auto clip = uniqueMapEntity(world_, "pack_door_clip");
        if (!clip || !world_.setBrushModelGameplayActive(*clip, false))
            return;
        factoryTeleporters_.packDoorOpening = false;
        factoryTeleporters_.packDoorHandle.reset();
        factoryTeleporters_.packAPunchUnlocked = true;
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "ZM PAP GATE OPEN COMPLETE");
    }
}
