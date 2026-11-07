#include "sv_zm_navgraph_mp.hpp"

#include <algorithm>
#include <bit>
#include <charconv>
#include <cmath>
#include <functional>
#include <limits>
#include <queue>
#include <set>
#include <system_error>
#include <utility>

namespace CodolGameServer
{
    std::array<float, 3> SvZmNegotiationMotion::position(const std::uint32_t elapsed) const
    {
        if (samples.empty()) return {};
        if (elapsed >= duration()) return samples.back();
        const auto first = elapsed < firstInterval;
        const auto index = first ? 0u : 1u+(elapsed-firstInterval)/100u;
        const auto fraction = first ? static_cast<float>(elapsed)/firstInterval
            : static_cast<float>((elapsed-firstInterval)%100u)/100.0f;
        auto result = samples[index];
        for (std::size_t axis = 0; axis < 3; ++axis)
            result[axis] += (samples[index+1u][axis]-result[axis])*fraction;
        return result;
    }

    namespace
    {
        // Factory demo C-2021-7-31[15-32-16]zm, humanoid710,command69100..73550.
        // Type2 starts69100 (first snapshot69150); walk-fast at72850. Third
        // Factory demo actor711 independently confirms3750ms,45800->49550.
        // Do not substitute dog824's traverse_up_40 or extend to other edges.
        constexpr std::array<std::array<float,3>,46> FactoryClimb948947{{
            {87,221,-3}, // command-time pose; next sample is50ms later
            {87,221,-3},{87,221,-3},{87,221,5},{86,220,16},
            {85,219,22},{83,218,29},{83,217,40},{84,216,46},
            {84,216,50},{83,216,52},{83,216,53},{82,215,54},
            {81,215,53},{81,215,53},{80,215,53},{80,216,54},
            {80,216,56},{80,216,57},{80,217,59},{80,218,60},
            {80,218,62},{80,218,65},{80,217,68},{79,215,73},
            {78,212,78},{77,210,82},{77,209,85},{78,210,88},
            {79,210,90},{79,211,92},{80,212,93},{79,212,95},
            {77,212,96},{74,212,96},{70,212,96},{67,212,96},
            {63,213,96},{62,213,96},
            // Walk-fast begins before its body clears the authored ledge clip.
            // Retain the measured exit, not a straight line to the node centre.
            {62,213,96},{59,212,95},{54,208,95},{48,205,95},
            {43,201,95},{37,198,95},{31,195,93}
        }};
        // Same actor, next directed negotiation977->976. Command74500, first
        // position sample74550, walk75650. Start interpolated between74450/74550;
        // retain the 50ms first interval instead of shifting the animation clock.
        constexpr std::array<std::array<float,3>,13> FactoryDrop977976{{
            {37.5f,253,93},{38,253,93},{42,253,93},{46,253,93},
            {52,253,93},{58,253,85},{65,253,70},{73,253,51},
            {83,253,25},{93,253,-2},{93,253,-2},{93,253,-2},{93,253,-2}
        }};
        // West platform exit: same demo actor709,66350->67500 command handoff.
        // Last sample67550 includes50ms of walking away from the landing.
        constexpr std::array<std::array<float,3>,13> FactoryDrop975974{{
            {-151,157,93},{-155,157,93},{-159,157,93},{-164,157,93},
            {-170,157,89},{-176,157,78},{-184,157,61},{-193,157,39},
            {-203,157,12},{-208,157,-2},{-208,157,-2},{-208,157,-2},
            {-213,157,-3}
        }};
        // The four node classnames a zm map carries. Kept in step with the list
        // sv_mapents_mp.cpp uses to decide which entities consume an entity number --
        // both walk the SAME entities, and the graph's indices are that walk's order.
        [[nodiscard]] bool isNavNodeClass(const std::string_view className)
        {
            return className.starts_with("node_");
        }

        [[nodiscard]] std::optional<std::array<float, 3>> parseOrigin(
            const std::string_view text)
        {
            std::array<float, 3> out{};
            auto cursor = text.data();
            const auto end = text.data() + text.size();
            for (auto &value : out)
            {
                while (cursor < end && *cursor == ' ')
                    ++cursor;
                if (cursor == end)
                    return std::nullopt;
                const auto parsed = std::from_chars(cursor, end, value);
                if (parsed.ec != std::errc{} || parsed.ptr == cursor)
                    return std::nullopt;
                cursor = parsed.ptr;
            }
            return out;
        }

        [[nodiscard]] float planarDistance(
            const std::array<float, 3> &a, const std::array<float, 3> &b)
        {
            const auto dx = a[0] - b[0];
            const auto dy = a[1] - b[1];
            return std::sqrt(dx * dx + dy * dy);
        }
    }

    SvZmNavGraph SV_BuildZmNavGraph(
        const std::span<const SvMapEntity> entities,
        const std::string_view mapName,
        const SvZmNavAnimResolver &resolveAnim,
        const SvZmNavGroundResolver &resolveGround,
        const SvZmNavSource source,
        const SvZmNavWalkValidator &validateReferenceWalk)
    {
        const auto *const table = resolveGround
            ? SV_ZmNavGroundedTable(mapName) : SV_ZmNavTable(mapName);
        if (table == nullptr)
            return {};
        const auto *const reference = source == SvZmNavSource::Bo1Hybrid
            ? SV_ZmBo1ReferenceTable(mapName) : nullptr;
        // A requested donor overlay must never degrade silently to the normal
        // graph. It is meaningful only on the exact Factory map, with live floor
        // and corridor validation supplied by the running server.
        if (source == SvZmNavSource::Bo1Hybrid &&
            (reference == nullptr || !resolveGround || !validateReferenceWalk))
            return {};

        // The map's own nodes, in entity-string order. This ordering IS the contract
        // with the table's edge indices.
        std::vector<std::array<float, 3>> nodes;
        std::vector<const SvMapEntity *> nodeEntities;
        for (const auto &entity : entities)
        {
            const auto className = entity.value("classname");
            if (!className || !isNavNodeClass(*className))
                continue;
            const auto originText = entity.value("origin");
            if (!originText)
                return {};                      // a node without a position breaks the order
            const auto origin = parseOrigin(*originText);
            if (!origin)
                return {};
            nodes.push_back(*origin);
            nodeEntities.push_back(&entity);
        }

        // FAIL CLOSED. Count first, then every position.
        if (nodes.size() * 3u != table->nodeOriginBits.size())
            return {};
        for (std::size_t i = 0; i < nodes.size(); ++i)
        {
            for (std::size_t axis = 0; axis < 3; ++axis)
            {
                const auto expected =
                    std::bit_cast<float>(table->nodeOriginBits[i * 3u + axis]);
                if (std::abs(nodes[i][axis] - expected) > SvZmNavPositionTolerance)
                    return {};
            }
        }

        SvZmNavGraph graph;
        graph.nodes = std::move(nodes);
        if (reference)
        {
            if (reference->shadowNodeOriginBits.size() % 3u != 0u)
                return {};
            graph.referenceNodes = reference->shadowNodeOriginBits.size() / 3u;
            graph.nodes.reserve(graph.nodes.size() + graph.referenceNodes);
            for (std::size_t i = 0; i < graph.referenceNodes; ++i)
            {
                graph.nodes.push_back({
                    std::bit_cast<float>(reference->shadowNodeOriginBits[i * 3u]),
                    std::bit_cast<float>(reference->shadowNodeOriginBits[i * 3u + 1u]),
                    std::bit_cast<float>(reference->shadowNodeOriginBits[i * 3u + 2u])});
            }
        }
        // MapEnt begin.target -> end.targetname owns traversal direction, even
        // without a board group. Reversing a jump-up does not create a drop.
        // The previous symmetric graph sent live actors958->945, parking them
        // above the ground-floor climb start with no legal descent motion.
        for (std::size_t from=0;from<nodeEntities.size();++from)
        {
            if (nodeEntities[from]->value("classname") != "node_negotiation_begin")
                continue;
            const auto target=nodeEntities[from]->value("target");
            if (!target || target->empty()) continue;
            std::optional<std::uint16_t> to;
            bool ambiguous=false;
            for (std::size_t i=0;i<nodeEntities.size();++i)
            {
                if (nodeEntities[i]->value("classname") != "node_negotiation_end" ||
                    nodeEntities[i]->value("targetname") != target) continue;
                if (to) { ambiguous=true; break; }
                to=static_cast<std::uint16_t>(i);
            }
            if (!to || ambiguous) continue;
            const auto begin=static_cast<std::uint16_t>(from);
            if (std::ranges::any_of(table->edges,[&](const SvZmNavEdge &edge) {
                return edge.via != SvZmNavVia::Walk &&
                    std::min(edge.a,edge.b)==std::min(begin,*to) &&
                    std::max(edge.a,edge.b)==std::max(begin,*to);
            }))
                graph.reverseNegotiationEdges.emplace_back(*to,begin);
        }
        // Use authored identity positions before grounding. Barrier begin/end
        // ownership, not sorted edge order, defines the permitted entrance.
        for (const auto &barrier : SV_SelectZmBarriers(entities))
        {
            if (!barrier.hasVault)
                continue;
            const auto findIdentity = [&graph](const std::array<float, 3> &position)
                -> std::optional<std::uint16_t> {
                for (std::size_t i = 0; i < graph.nodes.size(); ++i)
                {
                    const auto &node = graph.nodes[i];
                    if (std::abs(node[0] - position[0]) <= SvZmNavPositionTolerance &&
                        std::abs(node[1] - position[1]) <= SvZmNavPositionTolerance &&
                        std::abs(node[2] - position[2]) <= SvZmNavPositionTolerance)
                        return static_cast<std::uint16_t>(i);
                }
                return std::nullopt;
            };
            const auto outside = findIdentity(barrier.outside);
            const auto inside = findIdentity(barrier.inside);
            if (outside && inside && *outside != *inside)
            {
                graph.reverseBarrierEdges.emplace_back(*inside, *outside);
                // Factory demo15-32-16 actors723/670/713 start at auto414 and
                // descend to pf683 (y~157,z~6), never pf682 (y30,z69).
                // Distance-only matching chose the neighbouring west-zone window.
                if (mapName == "zm_factory_sh" && barrier.name == "pf683_auto1")
                {
                    for (const auto &entity : entities)
                    {
                        if (entity.value("targetname") != "auto414")
                            continue;
                        const auto origin = entity.value("origin");
                        const auto goal = origin ? parseOrigin(*origin) : std::nullopt;
                        if (goal)
                            graph.spawnBarrierByGoal.emplace(*goal,
                                std::pair{std::min(*outside,*inside),std::max(*outside,*inside)});
                    }
                }
            }
        }
        std::vector<bool> grounded(graph.nodes.size(), true);
        if (resolveGround)
        {
            for (std::size_t i = 0; i < graph.nodes.size(); ++i)
            {
                const auto authored = graph.nodes[i];
                const auto z = resolveGround(i, authored);
                grounded[i] = z && std::isfinite(*z) &&
                    *z <= authored[2] + 1.0f && *z >= authored[2] - 256.0f;
                if (grounded[i])
                    graph.nodes[i][2] = *z;
            }
        }

        // A DEMO VORONOI TRANSITION IS NOT AUTOMATICALLY A WALKABLE EDGE.
        //
        // The frozen reconstruction assigned each demo sample to the nearest map
        // node in X/Y.  Factory has several storeys above the same plan position,
        // so that procedure admitted ordinary walk links between different floors.
        // The live failure was node 833 (Z=24) -> node 651 (Z=120): a ground-level
        // actor aimed at the upper walkway and the collision solver quite correctly
        // made it hug the intervening wall forever.
        //
        // Preserve every map-declared negotiation.  Those are the authored vault,
        // mantle and drop links whose vertical displacement is intentional.  Only
        // a plain inferred Walk is rejected when it exceeds the same 72-unit floor
        // tolerance used by nearest-node selection.
        const auto usableEdge = [&graph, &grounded, mapName,
                                 &resolveGround](const SvZmNavEdge &edge) {
            // The absolute-demo Voronoi reconstruction still inferred one straight
            // chord through Factory's centre machinery. Three independent live
            // actors (704/707/708) hit the same world brush on 617->840 at
            // (-3.375,-14.860,29.886), fraction 0.032061, normalZ 0. This is a
            // shared graph defect, not actor-local congestion: reject it once while
            // constructing the graph instead of making every zombie wall-follow for
            // 1500 ms and rediscover the identical obstruction.
            const auto factoryCentreFalseEdge = resolveGround &&
                mapName == "zm_factory_sh" &&
                std::min(edge.a, edge.b) == 617u &&
                std::max(edge.a, edge.b) == 840u;
            return grounded[edge.a] && grounded[edge.b] &&
                !factoryCentreFalseEdge &&
                (edge.via != SvZmNavVia::Walk ||
                std::abs(
                    graph.nodes[edge.a][2] - graph.nodes[edge.b][2]) <=
                    SvZmNavHeightTolerance);
        };

        // Keep the accepted CODOL topology verbatim, then admit only BO1 ordinary
        // walks that are not already present and whose grounded corridor the live
        // CODOL world independently proves. Donor negotiation links are omitted:
        // CODOL's directed animation ownership remains solely with its own table.
        // OLMOD(factory-reference-admission): donor data never replaces CODOL
        // traversal ownership; see navigation-increment-20260920.md.
        std::vector<SvZmNavEdge> acceptedEdges;
        acceptedEdges.reserve(table->edges.size() +
            (reference ? reference->edges.size() : 0u));
        std::set<std::pair<std::uint16_t, std::uint16_t>> knownPairs;
        const auto nodeCount = graph.nodes.size();
        for (const auto &edge : table->edges)
        {
            if (edge.a >= nodeCount || edge.b >= nodeCount || edge.a == edge.b)
                return {};
            if (!usableEdge(edge))
                continue;
            acceptedEdges.push_back(edge);
            knownPairs.emplace(std::min(edge.a, edge.b), std::max(edge.a, edge.b));
        }
        if (reference)
        {
            graph.referenceEdgesConsidered = reference->edges.size();
            for (const auto &edge : reference->edges)
            {
                if (edge.a >= nodeCount || edge.b >= nodeCount || edge.a == edge.b)
                    return {};
                if (edge.via != SvZmNavVia::Walk || !usableEdge(edge))
                    continue;
                const auto pair = std::pair{
                    std::min(edge.a, edge.b), std::max(edge.a, edge.b)};
                if (knownPairs.contains(pair))
                    continue;
                if (!validateReferenceWalk(
                        graph.nodes[edge.a], graph.nodes[edge.b]))
                    continue;
                knownPairs.insert(pair);
                acceptedEdges.push_back(edge);
                ++graph.referenceEdgesAccepted;
            }
        }

        // CSR build: count degrees, prefix-sum, fill. Every edge is undirected, so it
        // contributes to both endpoints.
        std::vector<std::uint32_t> degree(nodeCount + 1u, 0u);
        for (const auto &edge : acceptedEdges)
        {
            ++degree[edge.a];
            ++degree[edge.b];
        }
        graph.adjacencyStart.assign(nodeCount + 1u, 0u);
        for (std::size_t i = 0; i < nodeCount; ++i)
            graph.adjacencyStart[i + 1u] = graph.adjacencyStart[i] + degree[i];
        graph.adjacency.assign(graph.adjacencyStart.back(), 0u);
        auto cursor = graph.adjacencyStart;
        for (const auto &edge : acceptedEdges)
        {
            graph.adjacency[cursor[edge.a]++] = edge.b;
            graph.adjacency[cursor[edge.b]++] = edge.a;
        }

        // THE VAULT ANIMATIONS, resolved against the engine that is actually running.
        //
        // An index is never carried in the table: the client rebuilds its animation band
        // at map load, so the only correct source is this engine's own band (12.47, and
        // `codol-client-reresolves-asset-indices`). An edge whose xanim is empty, or whose
        // xanim this engine does not hold, simply gets no entry -- the actor crosses it
        // with no animation change, which is what happened before any of this existed.
        if (resolveAnim)
        {
            if (mapName == "zm_factory_sh")
            {
                graph.windowTraverseAnimations = {
                    resolveAnim("ai_zombie_traverse_v6").value_or(0),
                    resolveAnim("ai_zombie_traverse_v7").value_or(0)};
            }
            // Resolving is a band walk per name, so do it once per distinct xanim rather
            // than once per edge: 53 edges share 6 names.
            std::map<std::string_view, std::optional<std::uint16_t>> byName;
            for (const auto &edge : table->edges)
            {
                if (edge.xanim.empty() || !usableEdge(edge))
                    continue;
                const auto known = byName.find(edge.xanim);
                const auto index = known != byName.end()
                    ? known->second
                    : byName.emplace(edge.xanim, resolveAnim(edge.xanim)).first->second;
                if (index && *index)
                {
                    graph.vaultAnim.emplace(
                        std::pair{ std::min(edge.a, edge.b), std::max(edge.a, edge.b) },
                        *index);
                }
            }
        }
        // Enable only with the measured ground and exact resident animation. The
        // authored node Z is not the foot Z and cannot anchor this motion.
        if (mapName == "zm_factory_sh" && resolveGround && resolveAnim &&
            grounded.size() > 948 && grounded[947] && grounded[948] &&
            std::abs(graph.nodes[948][2] + 3.0f) < 1.0f &&
            std::abs(graph.nodes[947][2] - 93.0f) < 1.0f)
        {
            const auto animation = graph.vaultAnimFor(948,947);
            if (animation)
                graph.negotiationMotion.emplace(std::pair{std::uint16_t{948},std::uint16_t{947}},
                    SvZmNegotiationMotion{animation,FactoryClimb948947,3750,50,180.0f});
        }
        if (mapName == "zm_factory_sh" && resolveGround && resolveAnim &&
            grounded.size()>977 && grounded[977] && grounded[976] &&
            std::abs(graph.nodes[977][2]-93.0f)<1.0f &&
            std::abs(graph.nodes[976][2]+3.0f)<1.0f)
        {
            const auto animation=graph.vaultAnimFor(977,976);
            if (animation)
                graph.negotiationMotion.emplace(std::pair{std::uint16_t{977},std::uint16_t{976}},
                    SvZmNegotiationMotion{animation,FactoryDrop977976,1150,50,0.0f});
        }
        if (mapName == "zm_factory_sh" && resolveGround && resolveAnim &&
            grounded.size()>975 && grounded[975] && grounded[974] &&
            std::abs(graph.nodes[975][2]-93.0f)<1.0f &&
            std::abs(graph.nodes[974][2]+3.0f)<1.0f)
        {
            const auto animation=graph.vaultAnimFor(975,974);
            if (animation)
                graph.negotiationMotion.emplace(std::pair{std::uint16_t{975},std::uint16_t{974}},
                    SvZmNegotiationMotion{animation,FactoryDrop975974,1150,100,180.0f});
        }
        return graph;
    }

    std::optional<std::uint16_t> SV_ZmNavNearestNode(
        const SvZmNavGraph &graph,
        const std::span<const float, 3> origin,
        const float maxDistance,
        const float maxHeightDelta)
    {
        std::optional<std::uint16_t> best;
        auto bestDistance = maxDistance;
        const std::array<float, 3> point{ origin[0], origin[1], origin[2] };
        for (std::size_t i = 0; i < graph.nodes.size(); ++i)
        {
            // Retain authored node identities, but never choose an isolated node
            // as a route entry/goal. Factory live actor 707 selected node 867
            // after collision steering and then obtained empty routes forever.
            if (graph.neighbours(static_cast<std::uint16_t>(i)).empty())
                continue;
            // THE FLOOR TEST FIRST. Nearest in plan view is meaningless on a map with
            // storeys: the node directly overhead is 15 units away and 212 units up.
            if (std::abs(graph.nodes[i][2] - point[2]) > maxHeightDelta)
                continue;
            const auto distance = planarDistance(graph.nodes[i], point);
            if (distance > bestDistance)
                continue;
            bestDistance = distance;
            best = static_cast<std::uint16_t>(i);
        }
        return best;
    }

    namespace
    {
        bool navEdgeAllowed(
            const SvZmNavGraph &graph,
            const std::uint16_t node,
            const std::uint16_t next,
            const std::span<const std::pair<std::uint16_t, std::uint16_t>>
                forbiddenEdges)
        {
            if (std::ranges::find(graph.reverseBarrierEdges,
                    std::pair{ node, next }) != graph.reverseBarrierEdges.end())
                return false;
            if (std::ranges::find(graph.reverseNegotiationEdges,
                    std::pair{ node, next }) != graph.reverseNegotiationEdges.end())
                return false;

            // A LARGE VERTICAL LEG IS NOT A WALK. The captured graph retains a
            // handful of proximity links whose endpoints overlap in XY but sit on
            // different floors. Only measured directed negotiation motion or the
            // outside-to-inside side of a window may cross one.
            const auto verticalDistance = std::abs(
                graph.nodes[node][2] - graph.nodes[next][2]);
            if (verticalDistance > 72.0f &&
                !graph.negotiationMotion.contains({ node, next }) &&
                std::ranges::find(graph.reverseBarrierEdges,
                    std::pair{ next, node }) == graph.reverseBarrierEdges.end())
            {
                return false;
            }

            const auto candidate =
                std::pair{ std::min(node, next), std::max(node, next) };
            return !std::ranges::any_of(
                forbiddenEdges,
                [candidate](const auto edge) {
                    return candidate == std::pair{
                        std::min(edge.first, edge.second),
                        std::max(edge.first, edge.second) };
                });
        }

        std::vector<std::uint16_t> rebuildRoute(
            const std::uint16_t from,
            const std::uint16_t to,
            const std::vector<std::uint16_t> &parent)
        {
            std::vector<std::uint16_t> route;
            for (auto node = to;; node = parent[node])
            {
                route.push_back(node);
                if (node == from)
                    break;
            }
            std::reverse(route.begin(), route.end());
            return route;
        }

        std::vector<std::uint16_t> navRoute(
            const SvZmNavGraph &graph,
            const std::uint16_t from,
            const std::uint16_t to,
            const std::span<const std::pair<std::uint16_t, std::uint16_t>>
                forbiddenEdges)
        {
        const auto nodeCount = graph.nodes.size();
        if (from >= nodeCount || to >= nodeCount)
            return {};
        if (from == to)
            return { from };

        constexpr auto Infinity = std::numeric_limits<float>::infinity();
        std::vector<float> cost(nodeCount, Infinity);
        std::vector<std::uint16_t> parent(nodeCount, 0u);
        std::vector<bool> closed(nodeCount, false);

        // A* with a straight-line heuristic, which is admissible here because an edge's
        // cost is its own straight-line length.
        const auto heuristic = [&](const std::uint16_t node) {
            return planarDistance(graph.nodes[node], graph.nodes[to]);
        };
        using Entry = std::pair<float, std::uint16_t>;
        std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
        cost[from] = 0.0f;
        parent[from] = from;
        open.emplace(heuristic(from), from);

        while (!open.empty())
        {
            const auto [estimate, node] = open.top();
            open.pop();
            static_cast<void>(estimate);
            if (closed[node])
                continue;
            closed[node] = true;
            if (node == to)
                break;
            for (const auto next : graph.neighbours(node))
            {
                if (!navEdgeAllowed(graph, node, next, forbiddenEdges))
                    continue;
                if (closed[next])
                    continue;
                const auto stepCost =
                    cost[node] + planarDistance(graph.nodes[node], graph.nodes[next]);
                if (stepCost >= cost[next])
                    continue;
                cost[next] = stepCost;
                parent[next] = node;
                open.emplace(stepCost + heuristic(next), next);
            }
        }

        if (!closed[to])
            return {};                          // a different component: no route exists
        return rebuildRoute(from, to, parent);
        }
    }

    std::vector<std::uint16_t> SV_ZmNavRoute(
        const SvZmNavGraph &graph, const std::uint16_t from, const std::uint16_t to)
    {
        return navRoute(graph, from, to, {});
    }

    std::vector<std::uint16_t> SV_ZmNavRouteAvoidingEdge(
        const SvZmNavGraph &graph,
        const std::uint16_t from,
        const std::uint16_t to,
        const std::pair<std::uint16_t, std::uint16_t> forbiddenEdge)
    {
        return navRoute(graph, from, to, std::span{ &forbiddenEdge, 1u });
    }

    std::vector<std::uint16_t> SV_ZmNavRouteAvoidingEdges(
        const SvZmNavGraph &graph,
        const std::uint16_t from,
        const std::uint16_t to,
        const std::span<const std::pair<std::uint16_t, std::uint16_t>>
            forbiddenEdges)
    {
        return navRoute(graph, from, to, forbiddenEdges);
    }

    std::vector<std::uint16_t> SV_ZmNavRouteToClosestReachableNode(
        const SvZmNavGraph &graph,
        const std::uint16_t from,
        const std::span<const float, 3> goal,
        const float maxGoalDistance,
        const float maxGoalHeightDelta,
        const std::span<const std::pair<std::uint16_t, std::uint16_t>>
            forbiddenEdges)
    {
        const auto nodeCount = graph.nodes.size();
        if (from >= nodeCount)
            return {};

        constexpr auto Infinity = std::numeric_limits<float>::infinity();
        std::vector<float> cost(nodeCount, Infinity);
        std::vector<std::uint16_t> parent(nodeCount, 0u);
        std::vector<bool> closed(nodeCount, false);
        using Entry = std::pair<float, std::uint16_t>;
        std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
        cost[from] = 0.0f;
        parent[from] = from;
        open.emplace(0.0f, from);

        std::optional<std::uint16_t> closest;
        auto closestDistance = maxGoalDistance;
        auto closestRouteCost = Infinity;
        const std::array<float, 3> goalPoint{goal[0], goal[1], goal[2]};

        while (!open.empty())
        {
            const auto [queuedCost, node] = open.top();
            open.pop();
            if (closed[node])
                continue;
            closed[node] = true;

            if (!graph.neighbours(node).empty() &&
                std::abs(graph.nodes[node][2] - goalPoint[2]) <= maxGoalHeightDelta)
            {
                const auto distance = planarDistance(graph.nodes[node], goalPoint);
                if (distance < closestDistance ||
                    (distance == closestDistance && queuedCost < closestRouteCost))
                {
                    closest = node;
                    closestDistance = distance;
                    closestRouteCost = queuedCost;
                }
            }

            for (const auto next : graph.neighbours(node))
            {
                if (closed[next] || !navEdgeAllowed(graph, node, next, forbiddenEdges))
                    continue;
                const auto nextCost =
                    cost[node] + planarDistance(graph.nodes[node], graph.nodes[next]);
                if (nextCost >= cost[next])
                    continue;
                cost[next] = nextCost;
                parent[next] = node;
                open.emplace(nextCost, next);
            }
        }

        return closest ? rebuildRoute(from, *closest, parent)
                       : std::vector<std::uint16_t>{};
    }
}
