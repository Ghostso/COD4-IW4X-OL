#include "sv_radius_damage_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    namespace
    {
        using Vector = std::array<float, 3>;

        bool finiteVector(const Vector &value)
        {
            return std::ranges::all_of(value, [](float v) {
                return std::isfinite(v);
            });
        }

        float squaredLength(const Vector &value)
        {
            return value[0] * value[0] + value[1] * value[1] +
                value[2] * value[2];
        }

        bool normalize(Vector &value)
        {
            const auto length = std::sqrt(squaredLength(value));
            if (!std::isfinite(length))
                return false;
            // CODREF(Vec3Normalize): coincident points remain the zero vector.
            const auto inverse = length > 0.0f ? 1.0f / length : 1.0f;
            for (auto &component : value)
                component *= inverse;
            return finiteVector(value);
        }
    }

    std::optional<std::vector<SvPlayerRadiusDamageResult>>
    SV_ComputePlayerRadiusDamage(
        const SvPlayerRadiusDamageRequest &request,
        const std::span<const SvPlayerRadiusDamageTarget> targets,
        const SvRadiusDamageTracePassed &tracePassed)
    {
        constexpr float Int32UpperExclusive = 2147483648.0f;
        if (!finiteVector(request.origin) || !std::isfinite(request.radius) ||
            !std::isfinite(request.innerDamage) || request.innerDamage < 0.0f ||
            request.innerDamage >= Int32UpperExclusive ||
            !std::isfinite(request.outerDamage) || request.outerDamage < 0.0f ||
            request.outerDamage >= Int32UpperExclusive || !request.contentMask ||
            targets.size() > MaximumGameClients ||
            (request.inflictorEntityNum &&
                *request.inflictorEntityNum >= MaximumGameEntities) ||
            (request.ignoreClientNum &&
                *request.ignoreClientNum >= MaximumGameClients))
            return std::nullopt;
        if (request.cone)
        {
            const auto &cone = *request.cone;
            if (!std::isfinite(cone.angleCos) || cone.angleCos < -1.0f ||
                cone.angleCos > 1.0f || !finiteVector(cone.direction) ||
                (cone.angleCos != -1.0f &&
                    std::abs(squaredLength(cone.direction) - 1.0f) > 0.0001f))
                return std::nullopt;
        }
        std::array<bool, MaximumGameClients> seen{};
        for (const auto &target : targets)
        {
            if (target.clientNum >= MaximumGameClients || seen[target.clientNum] ||
                !finiteVector(target.origin) || !finiteVector(target.eyePosition) ||
                !finiteVector(target.absoluteBounds.midpoint) ||
                !finiteVector(target.absoluteBounds.halfSize) ||
                std::ranges::any_of(target.absoluteBounds.halfSize,
                    [](float v) { return v < 0.0f; }) ||
                !std::isfinite(target.shieldProtection) ||
                target.shieldProtection < 0.0f || target.shieldProtection > 1.0f)
                return std::nullopt;
            seen[target.clientNum] = true;
        }

        // CODREF(G_RadiusDamage): clamp radius to one, measure from the blast
        // to the closest point of r.absBox, and exclude the exact outer edge.
        const auto radius = std::max(1.0f, request.radius);
        const auto radiusSquared = radius * radius;
        if (!std::isfinite(radiusSquared))
            return std::nullopt;
        std::vector<SvPlayerRadiusDamageResult> result;
        result.reserve(targets.size());
        for (const auto &target : targets)
        {
            if (request.ignoreClientNum == target.clientNum)
                continue;
            Vector separation{};
            for (std::size_t axis = 0; axis < 3; ++axis)
                separation[axis] = std::max(0.0f,
                    std::abs(request.origin[axis] -
                        target.absoluteBounds.midpoint[axis]) -
                    target.absoluteBounds.halfSize[axis]);
            const auto distanceSquared = squaredLength(separation);
            if (!std::isfinite(distanceSquared))
                return std::nullopt;
            if (distanceSquared >= radiusSquared)
                continue;

            const auto distance = std::sqrt(distanceSquared);
            const auto damage = (request.innerDamage - request.outerDamage) *
                (1.0f - distance / radius) + request.outerDamage;
            Vector horizontal{ request.origin[0] - target.origin[0],
                request.origin[1] - target.origin[1], 0.0f };
            if (!normalize(horizontal))
                return std::nullopt;
            Vector midpoint{};
            for (std::size_t axis = 0; axis < 3; ++axis)
                midpoint[axis] = (target.origin[axis] + target.eyePosition[axis]) * 0.5f;
            const auto halfHeight = (target.eyePosition[2] - target.origin[2]) * 0.5f;
            // CODREF(CanDamage): center, lateral+ eye/feet, lateral- eye/feet.
            // The lateral vector is horizontal and 15 units wide; do not use
            // the collision half-width or a standing-height constant instead.
            const Vector lateral{ -horizontal[1] * 15.0f,
                horizontal[0] * 15.0f, 0.0f };
            std::array<Vector, 5> points{ midpoint, midpoint, midpoint, midpoint, midpoint };
            for (std::size_t index = 1; index < points.size(); ++index)
            {
                const auto sign = index < 3 ? 1.0f : -1.0f;
                for (std::size_t axis = 0; axis < 3; ++axis)
                    points[index][axis] += sign * lateral[axis];
                points[index][2] += index % 2 ? halfHeight : -halfHeight;
            }
            unsigned visible = 0;
            for (const auto &point : points)
            {
                if (!finiteVector(point))
                    return std::nullopt;
                if (request.cone && request.cone->angleCos != -1.0f)
                {
                    Vector direction{};
                    for (std::size_t axis = 0; axis < 3; ++axis)
                        direction[axis] = point[axis] - request.origin[axis];
                    if (!normalize(direction))
                        return std::nullopt;
                    float dot = 0.0f;
                    for (std::size_t axis = 0; axis < 3; ++axis)
                        dot += direction[axis] * request.cone->direction[axis];
                    if (dot < request.cone->angleCos)
                        continue;
                }
                if (!tracePassed)
                    return std::nullopt;
                const auto passed = tracePassed({ request.origin, point,
                    target.clientNum, request.inflictorEntityNum, request.contentMask });
                if (!passed)
                    return std::nullopt;
                visible += *passed ? 1u : 0u;
            }
            // CODREF(CanDamage): three visible points already give full
            // exposure. G_RadiusDamage truncates AFTER shield and cover scaling.
            const auto exposure = std::min(1.0f, static_cast<float>(visible) / 3.0f);
            const auto scaled = damage * (exposure * (1.0f - target.shieldProtection));
            if (!std::isfinite(scaled) || scaled < 0.0f || scaled >= Int32UpperExclusive)
                return std::nullopt;
            Vector direction{};
            for (std::size_t axis = 0; axis < 3; ++axis)
                direction[axis] = target.origin[axis] - request.origin[axis];
            direction[2] += 24.0f;
            if (!finiteVector(direction))
                return std::nullopt;
            result.push_back({ target.clientNum, target.spawnGeneration,
                distance, damage, exposure, target.shieldProtection,
                static_cast<std::int32_t>(scaled), direction });
        }
        return result;
    }
}
