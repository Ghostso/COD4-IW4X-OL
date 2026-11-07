#pragma once

#include "sv_collision_mp.hpp"
#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    // CODREF(actor_grounded_adapter): exact CODOL trace boundaries 0x46EA60
    // and 0x668220 retain native collision. BO1 Actor_Physics_1 0x912E40
    // separates walking/air/nogravity/noclip; Ghosts G_StepSlideMove
    // 0x140164B70 and BO2 AIPhys_StepSlideMove 0x899FA0 qualify steps with
    // traces. Reference layouts and physics are not imported. This adapter
    // still lacks the original CODOL falling/negotiation owner.

    // Window ownership follows the current directed leg, including cursor zero
    // after replanning. A pre-replan cached flag cannot establish this ownership.
    inline bool SV_ZmWindowOwnsGroundTransition(unsigned from, unsigned to,
        unsigned outside, unsigned inside, bool passed)
    {
        return !passed && from == outside && to == inside;
    }

    // OLMOD(zm-grounded-transition): an authored traversal requires its own
    // movement owner; ordinary waypoint arrival tolerance is not a drop limit.
    inline bool SV_ZmUnsupportedGroundTransition(bool assignedWindow,
        bool hasMotion, bool authoredNegotiation, float heightDelta,
        float arrivalHeight)
    {
        return !assignedWindow && !hasMotion &&
            (authoredNegotiation || std::abs(heightDelta) > arrivalHeight);
    }

    // OLMOD(zm-grounded-step): source-controller position admission, not a
    // recovered Actor_Physics implementation. The caller owns the native world
    // trace, bounds/mask and ordinary movement; active negotiation exits earlier.
    // TODO(CODOL): recover CODOL actor falling ownership and validate its state
    // transitions before replacing this grounded-walking boundary. IDA reference
    // comparison is recorded in .agents/research/actor-traversal-20260917.md.
    inline std::array<float, 3> SV_ZmResolveGroundedStep(
        const std::array<float, 3> &previous,
        std::array<float, 3> proposed,
        float traceStartZ, float traceEndZ,
        const std::optional<TraceResult> &ground)
    {
        if (ground && !ground->allSolid && !ground->startSolid &&
            ground->fraction < 1.0f)
        {
            proposed[2] = traceStartZ + (traceEndZ - traceStartZ) *
                std::clamp(ground->fraction, 0.0f, 1.0f);
            return proposed;
        }
        // Ordinary walking has no airborne/gravity owner here. A failed ground
        // query therefore cannot authorize a new position over empty space.
        // Preserve the previous position; the caller publishes zero velocity.
        return previous;
    }

    // OLMOD(zm-supported-step-retry): a source-owned retry for the mismatch
    // between the raised-bottom steering hull and the feet-aligned support hull.
    // A clear steering sweep can still place the feet inside an ascending surface.
    // Do not ignore that startSolid or lift the destination through a ceiling:
    // qualify up/across/down from the previous supported position instead.
    // BO1-guided donor groundStep uses this order and partial ceiling clearance;
    // this is not a recovered CODOL Actor_Physics implementation.
    template <typename Query>
    inline std::optional<std::array<float, 3>> SV_ZmRetrySupportedStep(
        const std::array<float, 3> &previous,
        const std::array<float, 3> &proposed,
        Query &&query)
    {
        constexpr float Skin = 0.25f;
        constexpr float StepHeight = 18.0f;
        constexpr float GroundDepth = 72.0f; // Retain this controller's existing reach.
        const auto valid = [](const std::optional<TraceResult> &t) {
            return t && std::isfinite(t->fraction) && t->fraction >= 0.0f &&
                t->fraction <= 1.0f && !t->startSolid && !t->allSolid;
        };
        const auto clear = [&](const auto &t) {
            return valid(t) && t->fraction >= 1.0f;
        };
        if (std::hypot(proposed[0]-previous[0], proposed[1]-previous[1]) < 0.001f)
            return std::nullopt;
        auto upStart = previous;
        upStart[2] += Skin;
        auto upEnd = previous;
        upEnd[2] += StepHeight;
        const auto up = query(upStart, upEnd);
        if (!valid(up)) return std::nullopt;
        auto rise = Skin + (StepHeight-Skin)*up->fraction;
        if (up->fraction < 1.0f) rise -= Skin;
        if (rise <= Skin) return std::nullopt;
        auto raised = previous;
        raised[2] += rise;
        auto across = proposed;
        across[2] = raised[2];
        if (!clear(query(raised, across))) return std::nullopt;
        auto below = across;
        below[2] = previous[2]-GroundDepth;
        const auto floor = query(across, below);
        if (!valid(floor) || floor->fraction >= 1.0f ||
            !std::isfinite(floor->normal[2]) || floor->normal[2] < 0.7f)
            return std::nullopt;
        auto landing = across;
        landing[2] += (below[2]-across[2])*floor->fraction + Skin;
        if (!std::isfinite(landing[2]) || landing[2] > previous[2]+StepHeight ||
            landing[2] < previous[2]-GroundDepth)
            return std::nullopt;
        if (!clear(query(landing, landing))) return std::nullopt;
        return landing;
    }
}
