#include "sv_client_impacts_mp.hpp"

#include <algorithm>
#include <array>

namespace CodolGameServer
{
    // CODREF(client_impacts): BO1 ClientImpacts 0x005F6810, Ghosts
    // ClientImpacts 0x1401149D0, and BO2 ClientImpacts/G_TouchEnts
    // 0x005B06E0/0x005B05E0 consume the bounded Pmove touch list in first-seen
    // order, notify both entities, then invoke both available touch handlers.
    // CODDIFF(client_impacts): CODOL has no retained server implementation;
    // this source plan resolves generation-safe ol-mod owners and leaves glass
    // touch plus concrete native handlers as TODO(CODOL).
    std::optional<SvClientImpactBatch> SV_BuildClientImpactBatch(
        const std::uint32_t sourceEntityNum,
        const std::span<const std::uint32_t> touchEntityNums,
        const std::span<const SvCollisionEntity> linkedEntities)
    {
        if (sourceEntityNum > MaximumServerCollisionEntityNum ||
            touchEntityNums.size() > 32)
        {
            return std::nullopt;
        }

        std::array<bool, MaximumServerCollisionEntityNum + 1> linkedEntityNums{};
        for (const auto &entity : linkedEntities)
        {
            if (!SV_IsCollisionEntityValid(entity) ||
                linkedEntityNums[entity.entityNum])
            {
                return std::nullopt;
            }
            linkedEntityNums[entity.entityNum] = true;
        }

        SvClientImpactBatch batch{
            .sourceEntityNum = sourceEntityNum,
            .inputTouchCount = static_cast<std::uint32_t>(
                touchEntityNums.size()),
        };
        for (std::size_t index = 0; index < touchEntityNums.size(); ++index)
        {
            const auto targetEntityNum = touchEntityNums[index];
            if (targetEntityNum > EntityNumNone)
                return std::nullopt;
            if (targetEntityNum == sourceEntityNum ||
                targetEntityNum > MaximumServerCollisionEntityNum)
            {
                continue;
            }
            if (std::find(
                    touchEntityNums.begin(),
                    touchEntityNums.begin() + index,
                    targetEntityNum) != touchEntityNums.begin() + index)
            {
                continue;
            }
            if (!linkedEntityNums[targetEntityNum])
            {
                ++batch.unresolvedEntityCount;
                continue;
            }
            batch.targetEntityNums[batch.impactCount++] = targetEntityNum;
        }
        return batch;
    }

    std::optional<SvClientImpactCallbackBatch>
        SV_BuildClientImpactCallbackBatch(
            const SvClientImpactBatch &impactBatch,
            const SvClientImpactCallbackOrder callbackOrder)
    {
        // CODREF(client_impacts): BO1/Ghosts invoke target then source with
        // contact=1; BO2 invokes source then target with the same contact.
        // CODDIFF(client_impacts): the caller must select between those two
        // reference orders because CODOL's removed server order is unknown.
        // OLMOD(client-impacts-callback-plan): validation keeps malformed
        // source candidates from reaching registered post-commit handlers.
        // TODO(CODOL): Bind the exact native entity handlers and collapse the
        // order policy after CODOL server evidence resolves both responsibilities.
        if (impactBatch.sourceEntityNum > MaximumServerCollisionEntityNum ||
            impactBatch.impactCount > impactBatch.targetEntityNums.size())
        {
            return std::nullopt;
        }

        std::array<bool, MaximumServerCollisionEntityNum + 1> seenTargets{};
        SvClientImpactCallbackBatch callbacks;
        for (std::uint32_t index = 0; index < impactBatch.impactCount; ++index)
        {
            const auto targetEntityNum = impactBatch.targetEntityNums[index];
            if (targetEntityNum > MaximumServerCollisionEntityNum ||
                targetEntityNum == impactBatch.sourceEntityNum ||
                seenTargets[targetEntityNum])
            {
                return std::nullopt;
            }
            seenTargets[targetEntityNum] = true;

            const SvClientImpactCallback sourceCallback{
                .receiverEntityNum = impactBatch.sourceEntityNum,
                .otherEntityNum = targetEntityNum,
                .contact = 1,
            };
            const SvClientImpactCallback targetCallback{
                .receiverEntityNum = targetEntityNum,
                .otherEntityNum = impactBatch.sourceEntityNum,
                .contact = 1,
            };
            switch (callbackOrder)
            {
            case SvClientImpactCallbackOrder::TargetThenSource:
                callbacks.callbacks[callbacks.callbackCount++] = targetCallback;
                callbacks.callbacks[callbacks.callbackCount++] = sourceCallback;
                break;
            case SvClientImpactCallbackOrder::SourceThenTarget:
                callbacks.callbacks[callbacks.callbackCount++] = sourceCallback;
                callbacks.callbacks[callbacks.callbackCount++] = targetCallback;
                break;
            default:
                return std::nullopt;
            }
        }
        return callbacks;
    }

    std::optional<SvClientImpactScriptNotificationBatch>
        SV_BuildClientImpactScriptNotificationBatch(
            const SvClientImpactBatch &impactBatch)
    {
        // CODREF(client_impacts): all three references notify source with
        // target and target with source once per first-seen touch entity.
        // OLMOD(client-impacts-script-plan): the source-then-target plan is a
        // bounded post-commit adapter for the current Lua runtime.
        // TODO(CODOL): Replace or narrow it when native script entity lifetime,
        // production gameplay source loading, and glass-touch notification are
        // recovered; this plan is not evidence of the removed CODOL script VM.
        if (impactBatch.sourceEntityNum > MaximumServerCollisionEntityNum ||
            impactBatch.impactCount > impactBatch.targetEntityNums.size())
        {
            return std::nullopt;
        }

        std::array<bool, MaximumServerCollisionEntityNum + 1> seenTargets{};
        SvClientImpactScriptNotificationBatch notifications;
        for (std::uint32_t index = 0; index < impactBatch.impactCount; ++index)
        {
            const auto targetEntityNum = impactBatch.targetEntityNums[index];
            if (targetEntityNum > MaximumServerCollisionEntityNum ||
                targetEntityNum == impactBatch.sourceEntityNum ||
                seenTargets[targetEntityNum])
            {
                return std::nullopt;
            }
            seenTargets[targetEntityNum] = true;
            notifications.notifications[notifications.notificationCount++] = {
                .receiverEntityNum = impactBatch.sourceEntityNum,
                .otherEntityNum = targetEntityNum,
            };
            notifications.notifications[notifications.notificationCount++] = {
                .receiverEntityNum = targetEntityNum,
                .otherEntityNum = impactBatch.sourceEntityNum,
            };
        }
        return notifications;
    }
}
