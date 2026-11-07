#include "sv_radius_damage_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    bool SV_IsRadiusDamageTraceRequestValid(const SvRadiusDamageTraceRequest &request)
    {
        const auto finite = [](const auto &point) {
            return std::ranges::all_of(point, [](float v) { return std::isfinite(v); });
        };
        return finite(request.start) && finite(request.end) && request.contentMask &&
            request.targetClientNum < MaximumGameClients &&
            (!request.inflictorEntityNum || *request.inflictorEntityNum < MaximumGameEntities);
    }

    std::optional<bool> SV_TestRadiusDamageVisibility(
        const SvRadiusDamageTraceRequest &request,
        const std::span<const SvCollisionEntity> entities,
        const SvRadiusDamageTracePassed &worldAndStaticModels,
        const SvRadiusDamageEntityTracePassed &entityTrace)
    {
        if (!SV_IsRadiusDamageTraceRequestValid(request) ||
            entities.size() > MaximumServerCollisionEntityNum + 1 || !worldAndStaticModels)
            return std::nullopt;
        std::array<bool, MaximumServerCollisionEntityNum + 1> seen{};
        for (const auto &entity : entities)
        {
            if (!SV_IsCollisionEntityValid(entity) || seen[entity.entityNum])
                return std::nullopt;
            seen[entity.entityNum] = true;
        }
        const auto worldClear = worldAndStaticModels(request);
        if (!worldClear || !*worldClear)
            return worldClear;
        for (const auto &entity : entities)
        {
            // CODREF(Ghosts SV_PointSightTraceToEntity 14020ADE0..14020AE0E):
            // test both entity IDs and both ownership exclusions. The existing
            // passOwnerEntityNum policy deliberately has different semantics.
            const auto excluded = [&](std::uint32_t number) {
                return number == request.targetClientNum ||
                    request.inflictorEntityNum == number;
            };
            if (!entity.linked || !(entity.contents & request.contentMask) ||
                excluded(entity.entityNum) ||
                (entity.ownerEntityNum && excluded(*entity.ownerEntityNum)) ||
                !SV_ShouldBroadphaseClipToEntity(
                    request.start, request.end, PointTraceBounds, entity))
                continue;
            if (!entityTrace)
                return std::nullopt;
            const auto clear = entityTrace(request, entity);
            if (!clear || !*clear)
                return clear;
        }
        return true;
    }
}
