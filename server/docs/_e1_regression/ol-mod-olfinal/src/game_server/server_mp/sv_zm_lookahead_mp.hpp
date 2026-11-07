#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <optional>
#include <span>

namespace CodolGameServer
{
    // CODREF(actor_path_lookahead): BO1 Path_Begin 0x906400,
    // Path_CalcLookahead 0x90A120 / Path_GetDistToPathSegment 0x9035F0,
    // and Ghosts Path_CalcLookahead 0x1400FF410 integrate perpendicular
    // offset * segment length, NOT a fixed forward distance. CODOL's original
    // server owner is absent; use the existing demo/map graph and out.exe
    // 0x46EA60 -> 0x668220 collision boundary. No foreign path_t layout is used.
    struct SvZmAreaLookahead
    {
        static constexpr float InitialArea = 21845.334f; // BO1 Path_Begin
        float area{InitialArea};
        bool previousTraceClear{};

        // CODREF(actor_path_lookahead): BO1 0x90B050 / 0x90B100 and Ghosts
        // 0x140101680 / 0x140102450 agree on clear growth. Ghosts/BO2 add a
        // flag/dodge-dependent .8 reduction; this adapter uses the BO1 policy:
        // its non-zombie ai_useBetterLookahead momentum branch is excluded.
        void observe(bool clear, float consumedArea, bool completed) noexcept
        {
            const auto maximum = completed ? consumedArea : area;
            if (clear)
                area = std::min(area * 1.1764705f + 6.4f, 65536.0f);
            else
                area = std::max(maximum * (previousTraceClear ? 0.75f : 0.5625f), 0.001f);
            if (completed)
                area = std::min(area, std::max(consumedArea, InitialArea));
            previousTraceClear = clear;
        }
    };

    struct SvZmAreaLookaheadTarget
    {
        std::array<float, 3> position{};
        std::size_t lastNode{};
        float consumedArea{};
        bool completed{};
    };

    // CODREF(actor_path_lookahead): area/in-segment interpolation from the two
    // Path_CalcLookahead references above. OLMOD(bounded-lookahead-adapter):
    // the measured CODOL graph is forward ordered and lacks native pathpoint
    // ownership. Keep its existing non-walk/elevation boundaries, at most 32
    // nodes and 192 units per selection; the caller still prediction-traces.
    // TODO(CODOL): replace these adapter bounds after original path owner and
    // prediction-trace ground policy are recovered, not from reference ABI.
    template<class Position, class OrdinaryEdge>
    std::optional<SvZmAreaLookaheadTarget> SV_ZmAreaLookaheadTargetForRoute(
        const std::array<float, 3>& origin,
        std::span<const std::uint16_t> nodes, std::size_t cursor,
        float budget, Position position, OrdinaryEdge ordinary)
    {
        if (cursor >= nodes.size() || !std::isfinite(budget) || budget <= 0.0f)
            return std::nullopt;
        for (auto value : origin)
            if (!std::isfinite(value)) return std::nullopt;
        auto from = origin;
        auto remainingDistance = 192.0f;
        SvZmAreaLookaheadTarget result{origin, cursor, 0.0f, false};
        const auto limit = cursor + std::min<std::size_t>(32, nodes.size() - cursor);
        for (auto index = cursor; index < limit; ++index)
        {
            const auto point = position(nodes[index]);
            for (auto value : point)
                if (!std::isfinite(value)) return std::nullopt;
            if (std::abs(point[2] - origin[2]) > 8.0f)
                break;
            const auto dx = point[0] - from[0], dy = point[1] - from[1];
            const auto length = std::hypot(dx, dy);
            if (length > 0.001f)
            {
                const auto height = std::abs(dx * (point[1] - origin[1]) -
                    dy * (point[0] - origin[0])) / length;
                auto travel = std::min(length, remainingDistance);
                if (height > 0.001f)
                    travel = std::min(travel, std::max(0.0f,
                        (budget - result.consumedArea) / height));
                const auto fraction = travel / length;
                for (std::size_t axis = 0; axis < 3; ++axis)
                    result.position[axis] = from[axis] + (point[axis] - from[axis]) * fraction;
                result.lastNode = index;
                result.consumedArea += height * travel;
                remainingDistance -= travel;
                if (travel < length || remainingDistance <= 0.001f)
                    return result;
            }
            else
            {
                result.position = point;
                result.lastNode = index;
            }
            if (index + 1 == nodes.size() || !ordinary(nodes[index], nodes[index + 1]))
            {
                result.completed = true;
                return result;
            }
            from = point;
        }
        return result;
    }

    // CODREF(actor_path_lookahead): BO1 Path_TrimCompletedPath 0x908820
    // trims using the saved lookahead direction, not the incoming edge's plane.
    // OLMOD(bounded-lookahead-adapter): only a still-owned, accepted prediction
    // chord may use this test; the caller bounds its node range and floor.
    inline bool SV_ZmPassedLookaheadPlane(const std::array<float, 3>& actor,
        const std::array<float, 3>& waypoint,
        const std::array<float, 3>& direction) noexcept
    {
        const auto lengthSquared = direction[0] * direction[0] + direction[1] * direction[1];
        const auto forward = (waypoint[0] - actor[0]) * direction[0] +
            (waypoint[1] - actor[1]) * direction[1];
        return std::isfinite(lengthSquared) && lengthSquared > 0.001f &&
            std::isfinite(forward) && forward <= 0.0f &&
            std::abs(waypoint[2] - actor[2]) <= 8.0f;
    }
}
