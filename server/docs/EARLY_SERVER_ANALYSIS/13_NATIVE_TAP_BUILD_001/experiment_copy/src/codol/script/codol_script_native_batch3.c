/*
 * Missing GSC natives, batch 3. Spawn sight trace is source-registered;
 * ishost remains an unregistered draft.
 * Parent replaced the worker's guessed spawn geometry using IW4 bounds and
 * projection evidence and reviewed the world-trace wrapper. Host identity
 * remains open; no runtime parity is claimed for either function.
 *
 * spawnsighttrace - the line-of-sight term of MP spawn-point selection.
 * ishost          - the host-client predicate the MP dev commands gate on.
 *
 * Selection: both names are called by the alpha MP script corpus, neither is
 * registered anywhere in src/ and neither has an implementation in the tree
 * under any symbol name. Absence was established against source, not against
 * the published manifest: the registry snapshot in
 * obj/claude-workers/gsc-native-batch3-registered.txt is every
 * Scr_AddFunction/Scr_AddMethod name literal in src/ (739 names), which is a
 * strict superset of the batch2 snapshot, and the candidate list is restricted
 * to the script set an MP server loads (alpha0022/gsc_overlay plus vendor/iw4
 * maps/mp, common_scripts, mptype and character - 641 files). Names any script
 * in that corpus defines, and names ever reached through "::", were dropped:
 * script helpers are not natives. Evidence, rejected candidates and the
 * shared-file registration this worker does not own are in
 * obj/claude-workers/gsc-native-batch3-checkpoint.md and -report.md.
 */
#ifdef CODOL_SERVER

#include "q_shared.h"
#include "bg.h"
#include "g_shared.h"
#include "entity.h"
#include "server.h"
#include "scr_vm.h"
#include "sys_net.h"
#include "codol_script_native_batch3.h"
#include "cm_local.h"

#include <math.h>

/* Native counterpart of IW4 48e080. CM sight hits encode brush+1, then
 * numBrushes+aabb+1 (retained CM_SightTraceThroughLeaf_60). IW4 stores
 * brush Bounds separately; IW3 stores mins/maxs in each cbrush_t. */
int CODOL_SpawnSightHitBounds(int hit, vec3_t midpoint, vec3_t halfsize)
{
    unsigned index, axis;
    if(hit<=0 || !midpoint || !halfsize) return 0;
    index=(unsigned)hit-1;
    if(index<cm.numBrushes) {
        const cbrush_t *brush;
        if(!cm.brushes) return 0;
        brush=&cm.brushes[index];
        for(axis=0;axis<3;++axis) {
            midpoint[axis]=(brush->mins[axis]+brush->maxs[axis])*0.5f;
            halfsize[axis]=(brush->maxs[axis]-brush->mins[axis])*0.5f;
        }
    } else {
        const CollisionAabbTree_t *tree;
        index-=cm.numBrushes;
        if(!cm.aabbTrees || cm.aabbTreeCount<=0 || index>=(unsigned)cm.aabbTreeCount) return 0;
        tree=&cm.aabbTrees[index];
        for(axis=0;axis<3;++axis) {
            midpoint[axis]=tree->origin[axis];
            halfsize[axis]=tree->halfSize[axis];
        }
    }
    return 1;
}

/* IW4 5f75a0: choose the extrema of the expanded obstruction rectangle
 * projected onto the horizontal normal. Keep its corner order for equal
 * projections, enforce 64 units of clearance, and project height along the
 * original direction. Distances describe the detour, not endpoint distance. */
static void spawn_sight_routes(const vec3_t from, const vec3_t to,
                              const vec3_t mid, const vec3_t half,
                              vec3_t routes[2], float distances[2])
{
    vec3_t dir, normal;
    float corners[4][2], projection[2], horizontal, expanded[2];
    unsigned i, side;
    for(i=0;i<3;++i) dir[i]=to[i]-from[i];
    horizontal=(float)sqrt((double)(dir[0]*dir[0]+dir[1]*dir[1]));
    if(horizontal==0.0f) horizontal=1.0f;
    for(i=0;i<3;++i) dir[i]/=horizontal;
    normal[0]=dir[1]; normal[1]=-dir[0]; normal[2]=0.0f;
    expanded[0]=half[0]+30.0f; expanded[1]=half[1]+30.0f;
    corners[0][0]=mid[0]+expanded[0];
    corners[0][1]=mid[1]+expanded[1];
    corners[1][0]=mid[0]-expanded[0];
    corners[1][1]=mid[1]-expanded[1];
    corners[2][0]=corners[0][0]; corners[2][1]=corners[1][1];
    corners[3][0]=corners[1][0]; corners[3][1]=corners[0][1];
    for(side=0;side<2;++side) {
        routes[side][0]=corners[0][0]; routes[side][1]=corners[0][1];
        routes[side][2]=from[2];
        projection[side]=(corners[0][0]-from[0])*normal[0]+
                         (corners[0][1]-from[1])*normal[1];
    }
    for(i=1;i<4;++i) {
        float d=(corners[i][0]-from[0])*normal[0]+
                (corners[i][1]-from[1])*normal[1];
        for(side=0;side<2;++side) {
            if((!side && d<projection[side]) || (side && d>projection[side])) {
                projection[side]=d;
                routes[side][0]=corners[i][0]; routes[side][1]=corners[i][1];
            }
        }
    }
    for(side=0;side<2;++side) {
        float limit=side ? 64.0f : -64.0f;
        if((!side && projection[side]>limit) || (side && projection[side]<limit)) {
            float shift=limit-projection[side];
            routes[side][0]+=shift*normal[0];
            routes[side][1]+=shift*normal[1];
            projection[side]=limit;
        }
        routes[side][2]=from[2]+dir[2]*((routes[side][0]-from[0])*dir[0]+
                                      (routes[side][1]-from[1])*dir[1]);
        distances[side]=side ? projection[side] : -projection[side];
    }
}

/* The reference world sight wrapper 4e2760 uses mask0x801, zero Bounds,
 * world model0, and preserves the first hit as a cache hint on later traces.
 * 50238e..5023d9 checks the old brush then traverses the world tree, matching
 * native CM_BoxSightTrace. CoDOL collision import retains brush/material
 * content words unchanged (codol_collision_native.c). */
static int spawn_sight_hit(int previous, const vec3_t from, const vec3_t to)
{
    const vec3_t zero={0,0,0};
    return CM_BoxSightTrace(previous,from,to,zero,zero,0,0x801);
}

void CODOL_Scr_SpawnSightTrace(void)
{
    vec3_t from,to,mid,half,routes[2];
    float distances[2];
    int hit;
    unsigned side;
    /* Complete IW4 handler5f7960..5f7cb9 never queries parameter0 or argc. */
    Scr_GetVector(1,from);
    Scr_GetVector(2,to);
    hit=spawn_sight_hit(0,from,to);
    if(!hit) { Scr_AddFloat(1.0f); return; }
    if(!CODOL_SpawnSightHitBounds(hit,mid,half)) {
        Scr_Error("spawnsighttrace: invalid world collision hit"); return;
    }
    spawn_sight_routes(from,to,mid,half,routes,distances);
    for(side=0;side<2;++side) {
        /* 5f7a69/5f7b8d skip distances >200, including unordered values.
         * Both segments must clear before publishing the detour weight. */
        if(!(distances[side]<=200.0f)) continue;
        if(!spawn_sight_hit(hit,from,routes[side]) &&
           !spawn_sight_hit(hit,routes[side],to)) {
            Scr_AddFloat(1.0f-(distances[side]-64.0f)/136.0f); return;
        }
    }
    Scr_AddFloat(0.0f);
}

/*
 * <player> ishost() -> bool
 *
 * IW4 0x005deb80, decoded:
 *
 *   005deb86  reject a non-entity receiver (0x0072c7f0)
 *   005deb9d  reject an entity without a client pointer (gentity+0x158),
 *             error text built from 0x0072d454 - the usual "not a player
 *             entity" object error
 *   005debcb  reject any parameter (Scr_GetNumParam must be 0, 0x00718d98)
 *   005debe1  read the client identity word at client+0x31d8 and compare it
 *             against the session host identity global 0x066b7008
 *   005dec00  publish the comparison as a bool
 *
 * Translation to this tree. IW4's identity comparison is an online-party
 * notion: the host is the client whose XUID matches the party host's. This
 * fork is a dedicated server and has no party host identity, so the identity
 * comparison has no counterpart and must not be faked with a constant. The
 * engine state that carries the same meaning here is the connection itself:
 * the host of a server is the client connected over this machine's local
 * address, which is exactly the connection the alpha's own C1 client makes
 * when it runs on the server machine. sv_client.c:863 already uses
 * NET_IsLocalAddress() on client_t::netchan.remoteAddress for host detection,
 * so this is the established local-host test in this tree and not a new one.
 *
 * Remote clients therefore get false and a locally connected client gets true,
 * both from live connection state. What is deliberately NOT claimed: this is
 * not IW4's party-host identity, so on a server whose operator plays from
 * another machine no client is the host, which is the correct answer for a
 * dedicated server and the answer the callers - the host-only dev commands in
 * maps/mp/gametypes/_dev.gsc:376 and :396 - want.
 */
void CODOL_Scr_IsHost(scr_entref_t entref)
{
    gentity_t *entity;
    client_t *client;
    int num;

    if(Scr_GetNumParam() != 0)
    {
        Scr_Error("ishost() takes no parameters");
        return;
    }

    entity = VM_GetGEntityForNum(entref);
    if(entity == NULL)
        return;
    if(entity->client == NULL)
    {
        Scr_ObjectError("not a player entity");
        return;
    }

    num = entity->s.number;
    if(num < 0 || num >= sv_maxclients->integer || svs.clients == NULL)
    {
        Scr_AddBool(qfalse);
        return;
    }

    client = &svs.clients[num];
    if(client->state < CS_CONNECTED)
    {
        Scr_AddBool(qfalse);
        return;
    }

    Scr_AddBool(NET_IsLocalAddress(client->netchan.remoteAddress) ? qtrue
                                                                  : qfalse);
}

#endif /* CODOL_SERVER */
