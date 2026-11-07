#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

#include "sv_mapents_mp.hpp"

namespace CodolGameServer
{
    // OLMOD(window-route-owner): project handoff, supported by forward-edge traces.
    // Reconstructed handoff policy: identify only a forward, map-owned window
    // actually present in the planned route. Never infer an entrance by distance.
    inline std::optional<std::pair<std::uint16_t, std::uint16_t>>
    SV_ZmFirstRouteWindow(std::span<const std::uint16_t> path,
        std::span<const std::pair<std::uint16_t, std::uint16_t>> reverseWindows)
    {
        for (std::size_t i = 1; i < path.size(); ++i)
        {
            const auto reverse = std::pair{path[i], path[i - 1]};
            if (std::ranges::find(reverseWindows, reverse) != reverseWindows.end())
                return std::pair{std::min(path[i - 1], path[i]),
                    std::max(path[i - 1], path[i])};
        }
        return std::nullopt;
    }

    // Window spacing owns only the outside approach, never post-window routing.
    constexpr bool SV_ZmWindowQueueApplies(
        bool hasBarrier, bool barrierPassed, bool finalLeg) noexcept
    {
        return hasBarrier && !barrierPassed && !finalLeg;
    }

    // Pursuit yielding is safe only when the actor owns a traced pursuit
    // corridor. A graph leg remains on its measured centreline. Pursuit also
    // keeps its exact player bearing: neighbours may slow a follower but never
    // invent a left/right destination that was absent from the demo route.
    constexpr bool SV_ZmPursuitYieldApplies(bool pursuitLeg,
        bool barrierPassed, bool fullNavigationBounds,
        bool elevationLeg, float distance) noexcept
    {
        return pursuitLeg && barrierPassed && fullNavigationBounds &&
            !elevationLeg && distance > 0.001f;
    }

    // OpenBLOPS Actor_TeamMoveBlocked does not push a follower sideways off its
    // authored path.  It waits behind an actor occupying the same forward
    // corridor, then resumes when that actor clears.  Graph legs need that
    // longitudinal arbitration even though lateral crowd steering is deliberately
    // pursuit-only (a lateral graph offset can select the wrong Factory stair).
    constexpr bool SV_ZmGraphYieldApplies(bool pursuitLeg,
        bool barrierPassed, bool fullNavigationBounds,
        bool elevationLeg, float distance) noexcept
    {
        return !pursuitLeg && barrierPassed && fullNavigationBounds &&
            !elevationLeg && distance > 0.001f;
    }

    inline float SV_ZmGraphYieldScale(float ahead, float side,
        float separation) noexcept
    {
        constexpr float BodyDiameter = 30.0f;
        constexpr float NoticeRadius = 42.0f;
        constexpr float CorridorHalfWidth = 20.0f;
        if (ahead < -4.0f || std::abs(side) > CorridorHalfWidth ||
            separation >= NoticeRadius)
        {
            return 1.0f;
        }
        if (separation <= BodyDiameter)
            return 0.0f;
        return std::clamp((separation - BodyDiameter) /
            (NoticeRadius - BodyDiameter), 0.0f, 1.0f);
    }

    // OpenBLOPS Path_UpdateLookahead aims along the route rather than snapping the
    // wish direction at every pathnode.  Build that forward point over ordinary,
    // same-floor edges only.  The caller prediction-traces the resulting chord;
    // barriers and negotiation/elevation edges therefore remain hard boundaries.
    template<class Position, class OrdinaryEdge>
    std::optional<std::array<float,3>> SV_ZmRouteLookaheadTarget(
        const std::array<float,3>& origin,
        std::span<const std::uint16_t> nodes, std::size_t cursor,
        float distance, Position position, OrdinaryEdge ordinary)
    {
        if (cursor>=nodes.size() || !std::isfinite(distance) || distance<=0.0f)
            return std::nullopt;
        auto from=origin;
        auto target=position(nodes[cursor]);
        auto remaining=distance;
        for (auto index=cursor; index<nodes.size(); ++index)
        {
            const auto point=position(nodes[index]);
            // Do not smooth a sequence of small risers into an untraced diagonal
            // climb.  Grounded stair movement continues to target its raw node.
            if (std::abs(point[2]-origin[2])>8.0f)
                break;
            const auto dx=point[0]-from[0];
            const auto dy=point[1]-from[1];
            const auto length=std::hypot(dx,dy);
            if (length>=remaining && length>0.001f)
            {
                const auto fraction=remaining/length;
                for (std::size_t axis=0;axis<3;++axis)
                    target[axis]=from[axis]+(point[axis]-from[axis])*fraction;
                return target;
            }
            target=point;
            remaining-=length;
            if (index+1u>=nodes.size() ||
                !ordinary(nodes[index],nodes[index+1u]))
                break;
            from=point;
        }
        return target;
    }

    // OLMOD(lookahead-progress): a shortcut must reach the incoming waypoint's
    // forward plane. A polyline that doubles back can otherwise produce a
    // short chord behind that plane, moving the actor without ever allowing
    // the route cursor to advance. This is a conservative adapter admission
    // rule, not a recovered native Path_UpdateLookahead implementation.
    inline bool SV_ZmLookaheadAdvances(const std::array<float,3>& origin,
        const std::array<float,3>& waypoint,const std::array<float,3>& target)
    {
        const auto x=waypoint[0]-origin[0],y=waypoint[1]-origin[1];
        const auto forward=(target[0]-origin[0])*x+(target[1]-origin[1])*y;
        return std::isfinite(forward) && forward+.01f>=x*x+y*y;
    }

    // OpenBLOPS Path_TrimCompletedPath advances a point after the actor crosses
    // the completed segment's forward plane.  That plane belongs to the INCOMING
    // leg.  Using waypoint->next here consumed a right-angle corner as soon as a
    // smoothed approach gained any component in the outgoing direction -- up to
    // corridorHalfWidth before actually reaching it.  The next lookahead then
    // started one node too far ahead and visibly corrected left/right.  Retain a
    // narrow corridor bound so an actor displaced onto an unrelated parallel route
    // cannot consume nodes.
    inline bool SV_ZmWaypointPassed(const std::array<float,3>& actor,
        const std::array<float,3>& previous,
        const std::array<float,3>& waypoint,
        float corridorHalfWidth=32.0f) noexcept
    {
        const auto edgeX=waypoint[0]-previous[0];
        const auto edgeY=waypoint[1]-previous[1];
        const auto edgeLength=std::hypot(edgeX,edgeY);
        if (!std::isfinite(edgeLength) || edgeLength<=0.001f)
            return false;
        const auto actorX=actor[0]-waypoint[0];
        const auto actorY=actor[1]-waypoint[1];
        const auto forward=actorX*edgeX+actorY*edgeY;
        const auto lateral=std::abs(actorX*edgeY-actorY*edgeX)/edgeLength;
        return forward>=0.0f && lateral<=corridorHalfWidth;
    }

    constexpr bool SV_ZmRouteNeedsReplan(bool planned, bool completedPlayerRoute,
        bool destinationChanged, bool timerExpired, bool exhausted) noexcept
    {
        // A healthy route already owns the actor's current incoming leg and its
        // remaining suffix. Re-running A* merely because one second elapsed can
        // select that incoming edge in reverse at the next junction. The following
        // tick then plans from the other endpoint and selects it back again, making
        // an actor oscillate even though player and destination have not moved.
        // The timer remains for exhausted/incomplete prefixes that need a retry.
        return !planned || destinationChanged ||
            (!completedPlayerRoute && exhausted && timerExpired);
    }

    // Project-side final-approach geometry, not a recovered native navigator.
    // Choose the nearest point at the requested stand-off, never a compass
    // slot that makes an actor orbit the target or cross through the player.
    inline std::array<float,3> SV_ZmPursuitStandOffTarget(
        const std::array<float,3> &actor, const std::array<float,3> &player,
        float radius)
    {
        auto target=player;
        const auto dx=actor[0]-player[0], dy=actor[1]-player[1];
        const auto distance=std::hypot(dx,dy);
        if (distance<=radius || distance<=0.001f)
        {
            target[0]=actor[0];
            target[1]=actor[1];
        }
        else
        {
            target[0]+=dx*radius/distance;
            target[1]+=dy*radius/distance;
        }
        return target;
    }

    constexpr bool SV_ZmPursuitProbeDue(std::uint32_t now,
        std::uint32_t checkedAt, const std::array<float,3>& checkedPlayer,
        const std::array<float,3>& player) noexcept
    {
        const auto dx=player[0]-checkedPlayer[0];
        const auto dy=player[1]-checkedPlayer[1];
        return checkedAt==0u || now-checkedAt>=200u || dx*dx+dy*dy>=64.0f;
    }

    // A retained wall tangent prevents left/right oscillation at a corner, but a
    // pursuit target can move to the other side of that wall while the key remains
    // the synthetic "player" waypoint. Probe the other tangent only in that case
    // (or when the retained side is blocked), keeping the common clear case cheap.
    constexpr bool SV_ZmWallFollowNeedsOppositeProbe(std::int8_t retainedSign,
        float desiredAlongBasis, float retainedFraction) noexcept
    {
        const auto desiredSign=desiredAlongBasis>=0.0f ? 1 : -1;
        return retainedSign==0 || retainedSign!=desiredSign || retainedFraction<0.10f;
    }

    // Five percent hysteresis retains a materially clearer existing corridor while
    // allowing pursuit to reverse promptly when both sides are comparably open.
    constexpr std::int8_t SV_ZmSelectWallFollowSign(std::int8_t retainedSign,
        float desiredAlongBasis, float retainedFraction,
        float oppositeFraction) noexcept
    {
        const auto desiredSign=static_cast<std::int8_t>(
            desiredAlongBasis>=0.0f ? 1 : -1);
        if (retainedSign==0) return desiredSign;
        if (retainedSign!=desiredSign)
            return oppositeFraction+0.05f>=retainedFraction
                ? desiredSign : retainedSign;
        return retainedFraction<0.10f &&
            oppositeFraction>retainedFraction+0.05f
                ? static_cast<std::int8_t>(-retainedSign) : retainedSign;
    }

    // Bounded forward-only selection; never skip an owned negotiation edge.
    template<class OrdinaryEdge, class Supported>
    std::size_t SV_ZmShortcutCursor(std::span<const std::uint16_t> nodes,
        std::size_t cursor, std::optional<std::uint16_t> previous,
        OrdinaryEdge ordinary, Supported supported)
    {
        if (cursor>=nodes.size() || nodes.size()-cursor<2u) return cursor;
        const auto incoming=cursor ? std::optional{nodes[cursor-1u]} : previous;
        if (!incoming || !ordinary(*incoming,nodes[cursor])) return cursor;
        const auto limit=cursor+std::min<std::size_t>(2u,nodes.size()-cursor-1u);
        auto selected=cursor;
        for (auto candidate=cursor+1u; candidate<=limit; ++candidate)
        {
            if (!ordinary(nodes[candidate-1u],nodes[candidate])) break;
            if (supported(nodes[candidate])) selected=candidate;
        }
        return selected;
    }

    // Project-side bounded corridor validation, not recovered retail pathfinding.
    // A body sweep alone cannot prove that a walk has floor support over a gap.
    template<class Ground, class Clear>
    bool SV_ZmSupportedWalk(const std::array<float,3>& from,
        const std::array<float,3>& to, Ground ground, Clear clear,
        float maximumLength=192.0f)
    {
        for (std::size_t axis=0; axis<3; ++axis)
            if (!std::isfinite(from[axis]) || !std::isfinite(to[axis])) return false;
        const float length=std::hypot(to[0]-from[0],to[1]-from[1]);
        if (length>maximumLength || std::abs(to[2]-from[2])>8.0f) return false;
        const auto count=std::max(1,static_cast<int>(std::ceil(length/16.0f)));
        auto previous=from;
        for (int sample=1; sample<=count; ++sample)
        {
            const float fraction=static_cast<float>(sample)/count;
            std::array<float,3> point{};
            for (std::size_t axis=0; axis<3; ++axis)
                point[axis]=from[axis]+(to[axis]-from[axis])*fraction;
            const auto floor=ground(point);
            if (!floor || !std::isfinite(*floor) || std::abs(*floor-point[2])>4.0f)
                return false;
            point[2]=*floor;
            if (!clear(previous,point)) return false;
            previous=point;
        }
        return true;
    }

    // Donor-edge admission for an ordinary staircase. Retail's path prediction
    // records `lookaheadHitsStairs`; a stair is still an ordinary path link, not a
    // negotiation. The flat-corridor predicate above intentionally rejects it and
    // remains the rule for runtime shortcuts. This bounded variant is used only
    // while admitting an opt-in donor edge at map load.
    //
    // Every eight planar units must retain floor support, each tread transition
    // must fit the actor stepper's existing 18-unit standing step, elevation must
    // progress toward the destination, and a full actor body must clear either the
    // direct segment or the same segment with its feet raised by one legal step.
    // It therefore cannot turn a gap, wall, lift, or drop into a walk link.
    template<class Ground, class Clear>
    bool SV_ZmSupportedStairWalk(const std::array<float,3>& from,
        const std::array<float,3>& to, Ground ground, Clear clear,
        float maximumLength=260.0f, float maximumTotalRise=112.0f,
        float maximumStep=18.0f)
    {
        for (std::size_t axis=0; axis<3; ++axis)
            if (!std::isfinite(from[axis]) || !std::isfinite(to[axis])) return false;
        const float length=std::hypot(to[0]-from[0],to[1]-from[1]);
        const float totalRise=to[2]-from[2];
        if (length>maximumLength || std::abs(totalRise)>maximumTotalRise) return false;
        const auto count=std::max(1,static_cast<int>(std::ceil(length/8.0f)));
        auto previous=from;
        for (int sample=1; sample<=count; ++sample)
        {
            const float fraction=static_cast<float>(sample)/count;
            std::array<float,3> point{};
            for (std::size_t axis=0; axis<3; ++axis)
                point[axis]=from[axis]+(to[axis]-from[axis])*fraction;
            const auto floor=ground(point);
            if (!floor || !std::isfinite(*floor)) return false;
            point[2]=*floor;
            const auto step=point[2]-previous[2];
            if (std::abs(step)>maximumStep+0.01f) return false;
            if ((totalRise>4.0f && step<-4.0f) ||
                (totalRise<-4.0f && step>4.0f)) return false;
            if (!clear(previous,point))
            {
                auto raisedPrevious=previous;
                auto raisedPoint=point;
                raisedPrevious[2]+=maximumStep;
                raisedPoint[2]+=maximumStep;
                if (!clear(raisedPrevious,raisedPoint)) return false;
            }
            previous=point;
        }
        return std::abs(previous[2]-to[2])<=4.0f;
    }

    // THE ZOMBIE NAVIGATION GRAPH, AND WHERE IT COMES FROM.
    //
    // A zm map ships 1100 `node_*` entities in MapEnts -- 994 `node_pathnode` plus 53
    // `node_negotiation_begin`/`_end` pairs -- and they carry ONLY a position. The links
    // between them belong to the `aipaths` asset, and `aipaths` is EMPTY in every zone
    // measured: its XAsset record holds a resolved header pointer instead of the write
    // placeholder, with zero bytes, on both zm_factory_sh and zm_asylum_sh. The client
    // never needed it; the AI ran on Tencent's server. See 20-zm-actor-lifecycle.md 12.57.
    //
    // So the edges were MEASURED, off 1063 retail zombie walks reconstructed from the zm
    // demos (12.58), plus the map's own 53 negotiation pairs, which are the barrier
    // vaults and are map data rather than observation. `Tools/demo-re/zmtracks.py`
    // produces them; `Tools/gen-zm-navgraph.py` turns that into the generated table.
    //
    // WHAT THIS IS NOT: retail's graph. It is a floor -- every edge in it is somewhere a
    // real zombie demonstrably went, but three captures did not walk everywhere, and 5 of
    // factory's 30 spawner goal nodes have no edge at all. An actor whose goal is
    // unreachable STAYS ON ITS SPAWNER. That is not a fallback to be softened later: a
    // route invented for an unrouted goal is exactly the through-walls behaviour 12.55
    // removed.

    enum class SvZmNavVia : std::uint8_t
    {
        // A crossing observed in the demo trajectories.
        Walk = 0,
        // A `node_negotiation_begin`/`_end` pair -- the map's own declared traversal.
        // Crossing one plays `animScript`; 45 of the 53 were ALSO walked, because
        // retail streams position through the vault animation.
        Negotiation = 1,
        WalkAndNegotiation = 2,
    };

    struct SvZmNavEdge
    {
        std::uint16_t a{};
        std::uint16_t b{};
        SvZmNavVia via{};
        // The MapEnts `animscript` -- a SCRIPT name, not an animation. Retail's server
        // ran `mp/animscripts/...` and that GSC picked the xanim; this server has no
        // such layer. Kept for provenance; `xanim` is what is actually playable.
        std::string_view animScript;
        // The XANIM the client holds for that animscript, measured by walking the
        // client's own animation band by name (12.61) and correlating the remaining
        // script name with live Factory demo assertions.  In particular,
        // `zombie_mantle_over_40` publishes `ai_zombie_traverse_v6` for slow actors;
        // its runtime name is not a mechanical `ai_` spelling of the animscript.
        //
        // A NAME, NOT AN INDEX, on purpose: the client rebuilds its own band at map load,
        // so an index recorded here would name a different animation elsewhere (12.47).
        std::string_view xanim;
    };

    struct SvZmNavTable
    {
        std::string_view mapName;
        // Raw float bits, THREE PER NODE, in the order `node_*` entities appear in the
        // map entity string. Present so the runtime can prove the loaded map is the map
        // the edges were measured on -- not as a source of positions, which MapEnts
        // already supplies.
        std::span<const std::uint32_t> nodeOriginBits;
        std::span<const SvZmNavEdge> edges;
    };

    // Optional reference topology layered on top of the identity-checked CODOL
    // table.  Its first indices address the CODOL nodes; any remaining indices
    // address the appended reference-only positions.  This is deliberately a
    // separate type so a donor graph can never replace the recovered CODOL
    // topology by accident.
    struct SvZmNavReferenceTable
    {
        std::string_view mapName;
        std::span<const std::uint32_t> shadowNodeOriginBits;
        std::span<const SvZmNavEdge> edges;
    };

    enum class SvZmNavSource : std::uint8_t
    {
        CodolRecovered,
        Bo1Hybrid
    };

    // Null when this build ships no measured graph for the map, which is the normal case
    // for every zm map but factory. Callers must park their actors, not improvise.
    [[nodiscard]] const SvZmNavTable *SV_ZmNavTable(std::string_view mapName);
    [[nodiscard]] const SvZmNavTable *SV_ZmNavGroundedTable(std::string_view mapName);
    [[nodiscard]] const SvZmNavReferenceTable *SV_ZmBo1ReferenceTable(
        std::string_view mapName);

    // Bounded demo-derived negotiation, not a general native root-motion solver.
    // Samples are absolute positions on the identity-validated map at 100ms intervals.
    struct SvZmNegotiationMotion
    {
        std::uint16_t animation{};
        std::span<const std::array<float, 3>> samples;
        // Animation may hand off before the actor has cleared the ledge volume.
        std::uint32_t walkingHandoff{};
        std::uint32_t firstInterval{100};
        float facingYaw{180.0f};
        [[nodiscard]] std::uint32_t duration() const
        { return samples.size()<2 ? 0u : firstInterval + static_cast<std::uint32_t>(samples.size()-2u)*100u; }
        [[nodiscard]] std::array<float, 3> position(std::uint32_t elapsed) const;
    };

    // The graph as the server uses it: positions from the map that is actually loaded,
    // adjacency in CSR form.
    struct SvZmNavGraph
    {
        std::vector<std::array<float, 3>> nodes;
        // CSR adjacency. Neighbours of node i are
        // `adjacency[adjacencyStart[i] .. adjacencyStart[i + 1])`.
        std::vector<std::uint32_t> adjacencyStart;
        std::vector<std::uint16_t> adjacency;
        // Physical topology stays symmetric for coarse component membership.
        // A* must reject these directed inside->outside barrier crossings.
        std::vector<std::pair<std::uint16_t, std::uint16_t>> reverseBarrierEdges;
        std::vector<std::pair<std::uint16_t, std::uint16_t>> reverseNegotiationEdges;
        // Explicit demo-confirmed spawn-goal -> entrance mappings, keyed by
        // authored goal coordinates (before ground projection).
        std::map<std::array<float, 3>, std::pair<std::uint16_t, std::uint16_t>> spawnBarrierByGoal;
        // THE VAULT ANIMATION FOR ONE EDGE, keyed by the ordered node pair, and present
        // only where the xanim was BOTH measured for that animscript AND resolved by the
        // engine this server is running against. A missing entry means the actor crosses
        // the edge with no animation change.
        std::map<std::pair<std::uint16_t, std::uint16_t>, std::uint16_t> vaultAnim;
        // Resident, name-resolved Factory window variants v6/v7; no copied CCS IDs.
        std::array<std::uint16_t,2> windowTraverseAnimations{};
        // Directed: reversing a climb is not a valid descent animation or motion.
        std::map<std::pair<std::uint16_t, std::uint16_t>, SvZmNegotiationMotion> negotiationMotion;
        // Admission telemetry for an opt-in donor overlay.  These counters are
        // zero for the normal CODOL graph and let a Factory test prove that the
        // requested hybrid was actually used rather than silently falling back.
        std::size_t referenceNodes{};
        std::size_t referenceEdgesConsidered{};
        std::size_t referenceEdgesAccepted{};

        [[nodiscard]] std::uint16_t vaultAnimFor(
            const std::uint16_t from, const std::uint16_t to) const
        {
            const auto found = vaultAnim.find(
                { std::min(from, to), std::max(from, to) });
            return found == vaultAnim.end() ? std::uint16_t{} : found->second;
        }

        [[nodiscard]] bool empty() const { return nodes.empty(); }
        [[nodiscard]] std::span<const std::uint16_t> neighbours(std::uint16_t node) const
        {
            if (node + 1u >= adjacencyStart.size())
                return {};
            return { adjacency.data() + adjacencyStart[node],
                     adjacencyStart[node + 1u] - adjacencyStart[node] };
        }
    };

    inline constexpr float SvZmNavHeightTolerance = 72.0f;

    // Retail does not attach an actor to the geometrically nearest pathnode
    // blindly. OpenBLOPS Path_NearestNodeNotCrossPlanes sorts nearby nodes and
    // accepts the first one reached by SV_SightTraceCapsule; only its zombie-mode
    // fallback ignores that visibility test. Keep the policy testable here while
    // the live caller supplies the native capsule trace and any required component.
    template<class Accept>
    [[nodiscard]] std::optional<std::uint16_t> SV_ZmNavNearestNodeIf(
        const SvZmNavGraph &graph, std::span<const float,3> origin,
        float maxDistance, Accept accept,
        float maxHeightDelta = SvZmNavHeightTolerance)
    {
        std::vector<std::pair<float,std::uint16_t>> candidates;
        candidates.reserve(graph.nodes.size());
        for (std::size_t index{}; index < graph.nodes.size(); ++index)
        {
            const auto nodeIndex = static_cast<std::uint16_t>(index);
            if (graph.neighbours(nodeIndex).empty() ||
                std::abs(graph.nodes[index][2] - origin[2]) > maxHeightDelta)
            {
                continue;
            }
            const auto dx = graph.nodes[index][0] - origin[0];
            const auto dy = graph.nodes[index][1] - origin[1];
            const auto distance = std::hypot(dx,dy);
            if (distance > maxDistance)
                continue;
            candidates.emplace_back(distance,nodeIndex);
        }
        std::ranges::sort(candidates, [](const auto &left, const auto &right) {
            return left.first < right.first;
        });
        for (const auto &[distance,nodeIndex] : candidates)
        {
            static_cast<void>(distance);
            if (accept(nodeIndex))
                return nodeIndex;
        }
        return std::nullopt;
    }

    // Resolve an XANIM NAME to the index this engine will send. Supplied by the caller
    // because only the dedicated's EngineBindings can ask the running engine, and it
    // must return nullopt for a name the engine does not hold rather than a guess.
    using SvZmNavAnimResolver =
        std::function<std::optional<std::uint16_t>(std::string_view)>;
    // Ground only after authored map identity validation. Missing/invalid results
    // isolate that node rather than treating its authored marker as a floor.
    using SvZmNavGroundResolver = std::function<std::optional<float>(
        std::size_t, const std::array<float, 3> &)>;
    // A donor walk is admitted only when the running map independently proves
    // floor support and actor-sized world clearance for its grounded endpoints.
    using SvZmNavWalkValidator = std::function<bool(
        const std::array<float, 3> &, const std::array<float, 3> &)>;

    // Build the graph for `mapName` from the map's own entities, or an EMPTY graph.
    //
    // IT FAILS CLOSED, AND IT IS SUPPOSED TO. The table's edges are indices into the
    // map's `node_*` list in entity-string order, so the two have to be the same list.
    // This checks that they are -- same count, every node within `PositionTolerance` --
    // and returns nothing at all if they are not. A graph half-agreeing with the loaded
    // map would route zombies along another map's corridors, which is worse than no
    // routing at all.
    //
    // `resolveAnim` is optional. Without it the graph carries no vault animations and
    // actors cross negotiation edges exactly as they did before -- which is also what
    // happens for any edge whose xanim the engine does not hold.
    [[nodiscard]] SvZmNavGraph SV_BuildZmNavGraph(
        std::span<const SvMapEntity> entities,
        std::string_view mapName,
        const SvZmNavAnimResolver &resolveAnim = {},
        const SvZmNavGroundResolver &resolveGround = {},
        SvZmNavSource source = SvZmNavSource::CodolRecovered,
        const SvZmNavWalkValidator &validateReferenceWalk = {});

    // How far above or below a node a position may be and still resolve to it.
    //
    // PLANAR NEAREST-NODE WAS A BUG ON A MULTI-STOREY MAP, and factory is one. 12.59
    // made the search ignore Z because spawn point 4 sits 48 units BELOW its own goal
    // node (12.55b) and a 3D search answered a node on another floor for a zombie
    // standing correctly on its spawner. Ignoring Z entirely does the same thing far
    // worse: measured in game, an actor at Z -122 resolved to a node 15 units away in
    // plan view whose Z is +90 -- 212 units and a whole storey up -- then routed along
    // THAT floor's edges while its own height interpolated toward them, which is a
    // zombie walking through a ceiling.
    //
    // 72 units splits the two cases: comfortably above the 48-unit spawn offset that
    // motivated the planar search, and comfortably below a storey. The map's own jump
    // vocabulary agrees -- `ai_zombie_jump_down_*` runs 72, 96, 120, 127, 184, 190, so
    // anything past 72 is a drop the map expects an animation for, not a step.
    // The node nearest `origin` in the plane, within `maxDistance`, and within
    // `maxHeightDelta` ABOVE OR BELOW it. Nullopt when nothing qualifies -- which is a
    // real answer and means the caller should park rather than route from a guess.
    [[nodiscard]] std::optional<std::uint16_t> SV_ZmNavNearestNode(
        const SvZmNavGraph &graph,
        std::span<const float, 3> origin,
        float maxDistance,
        float maxHeightDelta = SvZmNavHeightTolerance);

    // A* from `from` to `to`, inclusive of both, or EMPTY when no route exists.
    //
    // An empty result is a normal answer, not an error: factory's graph is 939 nodes in
    // one component plus five two-node islands, and five spawner goal nodes have no edge
    // at all. The caller parks the actor.
    [[nodiscard]] std::vector<std::uint16_t> SV_ZmNavRoute(
        const SvZmNavGraph &graph,
        std::uint16_t from,
        std::uint16_t to);

    // A* while treating one physical graph edge as closed in both directions.
    // Zombie window negotiations are directional in MapEnts even though the
    // measured navigation graph is undirected; once an actor has entered through
    // its assigned window, this prevents a shortest-path replan from immediately
    // sending it back out through that same opening.
    [[nodiscard]] std::vector<std::uint16_t> SV_ZmNavRouteAvoidingEdge(
        const SvZmNavGraph &graph,
        std::uint16_t from,
        std::uint16_t to,
        std::pair<std::uint16_t, std::uint16_t> forbiddenEdge);

    [[nodiscard]] std::vector<std::uint16_t> SV_ZmNavRouteAvoidingEdges(
        const SvZmNavGraph &graph,
        std::uint16_t from,
        std::uint16_t to,
        std::span<const std::pair<std::uint16_t, std::uint16_t>> forbiddenEdges);

    // OpenBLOPS Path_FindCloseNode equivalent for a measured graph with incomplete
    // coverage. Search only edges that ordinary routing may traverse, then return
    // the route to the reachable node geometrically closest to `goal`. This is a
    // fallback after an exact goal-node route fails; it never invents an edge or
    // relaxes window direction, negotiation, height, or actor-known block rules.
    [[nodiscard]] std::vector<std::uint16_t> SV_ZmNavRouteToClosestReachableNode(
        const SvZmNavGraph &graph,
        std::uint16_t from,
        std::span<const float, 3> goal,
        float maxGoalDistance,
        float maxGoalHeightDelta,
        std::span<const std::pair<std::uint16_t, std::uint16_t>> forbiddenEdges = {});

    // How far a node may sit from the position the map declares before the graph is
    // rejected. An identity check, not a value check -- node spacing is 58 units at the
    // median, so nothing but the right map comes close.
    inline constexpr float SvZmNavPositionTolerance = 0.05f;
}
