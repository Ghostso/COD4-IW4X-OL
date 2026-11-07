#include "sv_use_object_mp.hpp"

#include <algorithm>
#include <unordered_set>

namespace CodolGameServer
{
    namespace
    {
        bool validDefinition(const SvUseObjectDefinition &definition)
        {
            if (!definition.objectId)
                return false;
            if (definition.allowedRelation == SvUseTeamRelation::Any)
                return true;
            return definition.ownerTeam == SvTeam::Tf ||
                definition.ownerTeam == SvTeam::Sc;
        }

        bool teamAllowed(
            const SvUseObjectDefinition &definition,
            const SvTeam team)
        {
            switch (definition.allowedRelation)
            {
            case SvUseTeamRelation::Any:
                return team == SvTeam::Tf || team == SvTeam::Sc;
            case SvUseTeamRelation::Friendly:
                return team == definition.ownerTeam;
            case SvUseTeamRelation::Enemy:
                return (team == SvTeam::Tf || team == SvTeam::Sc) &&
                    team != definition.ownerTeam;
            }
            return false;
        }
    }

    void SvUseObjectSystem::reset()
    {
        definitions_.clear();
        clientProgress_.clear();
        objectClaimants_.clear();
        lastCommandTimes_.clear();
    }

    bool SvUseObjectSystem::configure(
        const std::span<const SvUseObjectDefinition> definitions)
    {
        std::unordered_set<std::uint32_t> objectIds;
        if (definitions.empty() ||
            std::ranges::any_of(definitions, [&](const auto &definition) {
                return !validDefinition(definition) ||
                    !objectIds.insert(definition.objectId).second;
            }))
        {
            return false;
        }
        reset();
        definitions_.assign(definitions.begin(), definitions.end());
        return true;
    }

    const SvUseObjectDefinition *SvUseObjectSystem::eligibleDefinition(
        const SvUseObjectClientCommand &command) const
    {
        if (!command.playing || !command.alive ||
            !(command.buttons & UserCmdButtonActivate))
        {
            return nullptr;
        }

        // The caller owns native trigger ranking. Preserving candidate order
        // prevents this generic progress owner from inventing spatial policy.
        for (const auto &candidate : command.candidates)
        {
            if (!candidate.insideTrigger)
                continue;
            const auto definition = std::ranges::find(
                definitions_, candidate.objectId,
                &SvUseObjectDefinition::objectId);
            if (definition == definitions_.end() ||
                !teamAllowed(*definition, command.team) ||
                (definition->requiresKeyObject && !candidate.hasKeyObject))
            {
                continue;
            }
            return &*definition;
        }
        return nullptr;
    }

    std::optional<SvUseObjectEvent> SvUseObjectSystem::cancelProgress(
        const std::uint32_t clientNum,
        const std::uint32_t commandTime)
    {
        const auto progress = clientProgress_.find(clientNum);
        if (progress == clientProgress_.end())
            return std::nullopt;
        const SvUseObjectEvent event{
            .type = SvUseObjectEventType::Cancel,
            .objectId = progress->second.objectId,
            .clientNum = clientNum,
            .commandTime = commandTime,
            .elapsedMilliseconds =
                progress->second.lastCommandTime -
                    progress->second.startCommandTime,
        };
        objectClaimants_.erase(progress->second.objectId);
        clientProgress_.erase(progress);
        return event;
    }

    std::optional<SvUseObjectEvent> SvUseObjectSystem::cancelClient(
        const std::uint32_t clientNum,
        const std::uint32_t commandTime)
    {
        const auto previousCommandTime = lastCommandTimes_.find(clientNum);
        if (previousCommandTime != lastCommandTimes_.end() &&
            commandTime < previousCommandTime->second)
        {
            return std::nullopt;
        }
        if (previousCommandTime == lastCommandTimes_.end() ||
            commandTime > previousCommandTime->second)
        {
            lastCommandTimes_[clientNum] = commandTime;
        }
        return cancelProgress(clientNum, commandTime);
    }

    std::vector<SvUseObjectEvent> SvUseObjectSystem::processCommittedCommand(
        const SvUseObjectClientCommand &command)
    {
        std::vector<SvUseObjectEvent> events;
        const auto previousCommandTime = lastCommandTimes_.find(command.clientNum);
        if (previousCommandTime != lastCommandTimes_.end() &&
            command.commandTime <= previousCommandTime->second)
        {
            return events;
        }
        lastCommandTimes_[command.clientNum] = command.commandTime;

        const auto *definition = eligibleDefinition(command);
        const auto progress = clientProgress_.find(command.clientNum);
        if (!definition ||
            (progress != clientProgress_.end() &&
                progress->second.objectId != definition->objectId))
        {
            if (const auto cancelled =
                    cancelProgress(command.clientNum, command.commandTime))
            {
                events.push_back(*cancelled);
            }
            if (!definition)
                return events;
        }

        auto active = clientProgress_.find(command.clientNum);
        if (active == clientProgress_.end())
        {
            const auto claimant = objectClaimants_.find(definition->objectId);
            if (claimant != objectClaimants_.end() &&
                claimant->second != command.clientNum)
            {
                return events;
            }
            objectClaimants_[definition->objectId] = command.clientNum;
            active = clientProgress_.emplace(command.clientNum, SvUseObjectProgress{
                .objectId = definition->objectId,
                .clientNum = command.clientNum,
                .startCommandTime = command.commandTime,
                .lastCommandTime = command.commandTime,
            }).first;
            events.push_back({
                .type = SvUseObjectEventType::Begin,
                .objectId = definition->objectId,
                .clientNum = command.clientNum,
                .commandTime = command.commandTime,
            });
        }
        else
        {
            active->second.lastCommandTime = command.commandTime;
        }

        const auto elapsed = command.commandTime - active->second.startCommandTime;
        if (elapsed < definition->useDurationMilliseconds)
            return events;
        events.push_back({
            .type = SvUseObjectEventType::Complete,
            .objectId = definition->objectId,
            .clientNum = command.clientNum,
            .commandTime = command.commandTime,
            .elapsedMilliseconds = elapsed,
        });
        objectClaimants_.erase(definition->objectId);
        clientProgress_.erase(active);
        return events;
    }

    std::optional<SvUseObjectProgress> SvUseObjectSystem::progressForClient(
        const std::uint32_t clientNum) const
    {
        const auto progress = clientProgress_.find(clientNum);
        return progress == clientProgress_.end()
            ? std::nullopt
            : std::optional{ progress->second };
    }

    std::optional<std::uint32_t> SvUseObjectSystem::claimantForObject(
        const std::uint32_t objectId) const
    {
        const auto claimant = objectClaimants_.find(objectId);
        return claimant == objectClaimants_.end()
            ? std::nullopt
            : std::optional{ claimant->second };
    }
}
