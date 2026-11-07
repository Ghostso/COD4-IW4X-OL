#pragma once
#include "sv_zm_navgraph_mp.hpp"
#include "sv_zm_factory_room_data.hpp"
#include <set>
#include <string>

namespace CodolGameServer {
// OLMOD(factory-room-import): authored room topology. Existing native trace-backed
// validators own admission; this does not recover or change the AI controller.
inline std::string SV_ApplyFactoryRoomDraft(SvZmNavGraph &current,
    const SvZmNavGroundResolver &ground, const SvZmNavWalkValidator &clear,
    const SvZmNavWalkValidator &landingClear = {})
{
    if(current.nodes.size()!=1206 || !ground || !clear)
        return "rejected: base size or live validators unavailable";
    auto graph=current;
    const auto first=static_cast<std::uint16_t>(graph.nodes.size());
    std::vector<bool> good;
    for(const auto &p:FactoryRoomDraft::Points) {
        auto q=p;const auto z=ground(graph.nodes.size(),p);
        const bool ok=z && std::isfinite(*z) && std::abs(*z-(p[2]-32.0f))<=8.0f;
        q[2]=ok?*z:p[2]-32.0f;graph.nodes.push_back(q);good.push_back(ok);
    }
    std::set<std::uint16_t> replaced(std::begin(FactoryRoomDraft::Replaced),std::end(FactoryRoomDraft::Replaced));
    // Never remove any original negotiation owner, including ones not visible
    // in the editor's donor ordinary-walk layer.
    for(const auto &[edge,anim]:graph.vaultAnim){replaced.erase(edge.first);replaced.erase(edge.second);}
    for(const auto &edge:graph.reverseBarrierEdges){replaced.erase(edge.first);replaced.erase(edge.second);}
    for(const auto &edge:graph.reverseNegotiationEdges){replaced.erase(edge.first);replaced.erase(edge.second);}
    std::set<std::pair<std::uint16_t,std::uint16_t>> edges;
    auto insert=[&](std::uint16_t a,std::uint16_t b){if(a!=b)edges.emplace(std::min(a,b),std::max(a,b));};
    std::size_t accepted=0,rejected=0,boundary=0;
    std::string failures;
    for(const auto &e:FactoryRoomDraft::Links) {
        const auto a=static_cast<std::uint16_t>(first+e[0]),b=static_cast<std::uint16_t>(first+e[1]);
        if(good[e[0]]&&good[e[1]]&&clear(graph.nodes[a],graph.nodes[b])&&clear(graph.nodes[b],graph.nodes[a])){insert(a,b);++accepted;}else {++rejected; if (failures.size()<2048) failures += " " + std::to_string(e[0]) + "->" + std::to_string(e[1]);}
    }
    for(const auto &e:FactoryRoomDraft::Ports) {
        const auto b=static_cast<std::uint16_t>(first+e[1]);
        const bool windowLanding=(e[0]==675 || e[0]==680) && landingClear &&
            std::hypot(graph.nodes[e[0]][0]-graph.nodes[b][0],graph.nodes[e[0]][1]-graph.nodes[b][1])<=32.0f;
        const auto &admit=windowLanding?landingClear:clear;
        if(!good[e[1]]||!admit(graph.nodes[e[0]],graph.nodes[b])||!admit(graph.nodes[b],graph.nodes[e[0]]))
            return "rejected: required port "+std::to_string(e[0])+" failed live clearance; customAccepted="+std::to_string(accepted)+" rejected="+std::to_string(rejected)+" blockedLinks="+failures;
        insert(e[0],b);
    }
    for(std::uint16_t a=0;a<first;++a)for(const auto b:current.neighbours(a)) {
        if(a>=b)continue;
        const bool ra=replaced.contains(a),rb=replaced.contains(b);
        if(!ra&&!rb){insert(a,b);continue;}
        if(ra&&rb)continue;
        const auto outside=ra?b:a,inside=ra?a:b;
        // Only redirect an existing boundary crossing, to a nearby same-floor
        // manual point. Never create proximity links between unrelated rooms.
        std::optional<std::uint16_t> chosen;float best=96.0f;
        for(std::size_t i=0;i<good.size();++i) {
            if(!good[i])continue;const auto n=static_cast<std::uint16_t>(first+i);
            const auto &p=graph.nodes[n],&old=graph.nodes[inside];
            const auto d=std::hypot(p[0]-old[0],p[1]-old[1]);
            if(d>=best||std::abs(p[2]-old[2])>24.0f)continue;
            if(clear(graph.nodes[outside],p)&&clear(p,graph.nodes[outside])){chosen=n;best=d;}
        }
        if(chosen){insert(outside,*chosen);++boundary;}
    }
    // OLMOD(factory-room-import): omit only isolated, non-port proposals after
    // live clearance. Never bridge rejected corridors or discard an entire
    // disconnected room section. All required ports remain mandatory.
    std::set<std::uint16_t> seen{static_cast<std::uint16_t>(first+FactoryRoomDraft::Ports[2][1])};
    bool changed=true;while(changed){changed=false;for(const auto &[a,b]:edges){if(seen.contains(a)&&!seen.contains(b)){seen.insert(b);changed=true;}if(seen.contains(b)&&!seen.contains(a)){seen.insert(a);changed=true;}}}
    std::set<std::uint16_t> omitted;
    std::string omittedIds;
    for(std::size_t i=0;i<good.size();++i)if(!good[i]||!seen.contains(static_cast<std::uint16_t>(first+i))) {
        const auto n=static_cast<std::uint16_t>(first+i);
        const bool port=std::ranges::any_of(FactoryRoomDraft::Ports,[&](const auto &p){return p[1]==i;});
        const bool linked=std::ranges::any_of(edges,[&](const auto &e){return e.first==n||e.second==n;});
        if(port||linked)
            return "rejected: disconnected required point or section offset="+std::to_string(i)+" blockedLinks="+failures;
        omitted.insert(n);
        omittedIds += " "+std::to_string(FactoryRoomDraft::LocalIds[i]);
    }
    // Compact only appended IDs; all native node and negotiation IDs stay fixed.
    std::vector<std::uint16_t> remap(graph.nodes.size());
    auto compact=std::vector<std::array<float,3>>{};
    compact.reserve(graph.nodes.size()-omitted.size());
    for(std::size_t i=0;i<graph.nodes.size();++i) {
        if(omitted.contains(static_cast<std::uint16_t>(i)))continue;
        remap[i]=static_cast<std::uint16_t>(compact.size());compact.push_back(graph.nodes[i]);
    }
    std::set<std::pair<std::uint16_t,std::uint16_t>> compactEdges;
    for(const auto &[a,b]:edges)compactEdges.emplace(remap[a],remap[b]);
    graph.nodes=std::move(compact);edges=std::move(compactEdges);
    graph.adjacencyStart.assign(graph.nodes.size()+1,0);
    for(const auto &[a,b]:edges){++graph.adjacencyStart[a+1];++graph.adjacencyStart[b+1];}
    for(std::size_t i=1;i<graph.adjacencyStart.size();++i)graph.adjacencyStart[i]+=graph.adjacencyStart[i-1];
    graph.adjacency.assign(graph.adjacencyStart.back(),0);auto cursor=graph.adjacencyStart;
    for(const auto &[a,b]:edges){graph.adjacency[cursor[a]++]=b;graph.adjacency[cursor[b]++]=a;}
    current=std::move(graph);
    return "applied sha="+std::string(FactoryRoomDraft::SourceSha)+" nodes="+std::to_string(good.size()-omitted.size())+" customAccepted="+std::to_string(accepted)+" rejected="+std::to_string(rejected)+" boundary="+std::to_string(boundary)+" omittedLocalIds="+omittedIds+" blockedLinks="+failures;
}
}
