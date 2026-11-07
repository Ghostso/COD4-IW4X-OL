/* Native directed waypoint graph for CoDOL combat training.
 * CSV data: alpha0022/resources/waypoints. No navmesh offsets imported. */
#ifdef CODOL_SERVER
#include "codol_bot_nav.h"
#include "filesystem.h"
#include "q_shared.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <ctype.h>
#define LINKS 48   /* CSV cap; T5 has no per-node cap, the map graph counts overflow as "link cap" */
/* blocker[i] is the entity number + 1 of the entity whose DisconnectPaths cut
 * links[i] (0 = open); record / negotiationEnd are the map-graph fields
 * declared in the header (-1 on CSV graphs). */
typedef struct { float point[3]; unsigned short links[LINKS]; unsigned short blocker[LINKS]; unsigned char count,stance; short component; short record,negotiationEnd; codol_bot_annotation_t annotation; } node_t;
static node_t nodes[CODOL_BOT_NODES];
static int count;
static codol_bot_route_stats_t route_stats;
static float distance(const float *a,const float *b)
{float x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return sqrtf(x*x+y*y+z*z);}
static char *line(char **text)
{
    char *start=*text,*p=start;
    if(!p || !*p)return NULL;
    while(*p && *p!='\n' && *p!='\r')++p;
    if(*p){*p++=0;while(*p=='\n'||*p=='\r')++p;}
    *text=p;return start;
}
static char *field(char **text)
{char *start=*text,*p=start;if(!p)return NULL;while(*p&&*p!=',')++p;if(*p){*p++=0;*text=p;}else *text=NULL;return start;}
static int integer(char **p,long *value)
{char *end;while(isspace((unsigned char)**p))++*p;*value=strtol(*p,&end,10);if(end==*p)return 0;*p=end;return 1;}
static int vector(char *part,float out[3])
{
    int i;char *end;
    if(!part||!*part)return 0;
    for(i=0;i<3;++i){out[i]=strtof(part,&end);if(end==part||!isfinite(out[i]))return -1;part=end;}
    while(isspace((unsigned char)*part))++part;
    return *part?-1:1;
}
/* Undirected component labels over the loaded links (union-find), so a
 * failed route can say whether its two ends were ever connected. */
static int nav_find(short *parent,int i){while(parent[i]!=i)i=parent[i]=parent[parent[i]];return i;}
static void nav_label_components(void)
{
    static short parent[CODOL_BOT_NODES],label[CODOL_BOT_NODES];int i,j,next=0;
    for(i=0;i<count;++i){parent[i]=(short)i;label[i]=-1;}
    for(i=0;i<count;++i)for(j=0;j<nodes[i].count;++j)parent[nav_find(parent,i)]=nav_find(parent,nodes[i].links[j]);
    for(i=0;i<count;++i){int root=nav_find(parent,i);if(label[root]<0)label[root]=(short)next++;nodes[i].component=label[root];}
}
int CODOL_BotNavLoad(const char *path)
{
    void *buffer=NULL;char *cursor,*row,*part,*columns,*end;long total,v;int size,i,j;
    node_t *pending;
    count=0; /* Missing/invalid map must never reuse the previous map's graph. */
    if(!path || strstr(path,"..") || strchr(path,':') || *path=='/' || *path=='\\')return 0;
    size=FS_ReadFile(path,&buffer);
    if(size<=0 || size>4*1024*1024){if(buffer)FS_FreeFile(buffer);return 0;}
    pending=calloc(CODOL_BOT_NODES,sizeof(*pending));
    if(!pending){FS_FreeFile(buffer);return 0;}
    cursor=buffer;row=line(&cursor);end=row;
    if(!row || !integer(&end,&total)||total<1||total>CODOL_BOT_NODES)goto bad;
    while(isspace((unsigned char)*end))++end;if(*end)goto bad;
    for(i=0;i<total;++i){
        pending[i].record=pending[i].negotiationEnd=-1;
        row=line(&cursor);if(!row)goto bad;columns=row;part=field(&columns);
        for(j=0;j<3;++j){pending[i].point[j]=strtof(part,&end);if(end==part||!isfinite(pending[i].point[j]))goto bad;part=end;}
        while(isspace((unsigned char)*part))++part;if(*part)goto bad;
        part=field(&columns);if(!part)goto bad;
        while(*part){while(isspace((unsigned char)*part))++part;if(!*part)break;
            if(!integer(&part,&v)||v<0||v>=total||pending[i].count==LINKS)goto bad;
            pending[i].links[pending[i].count++]=(unsigned short)v;
        }
        part=field(&columns);if(!part)goto bad;
        if(!strcmp(part,"stand")||!strcmp(part,"claymore")||!strcmp(part,"grenade")||!strcmp(part,"javelin"))pending[i].stance=CODOL_BOT_STAND;
        else if(!strcmp(part,"crouch"))pending[i].stance=CODOL_BOT_CROUCH;
        else if(!strcmp(part,"prone"))pending[i].stance=CODOL_BOT_PRONE;
        else if(!strcmp(part,"climb"))pending[i].stance=CODOL_BOT_CLIMB;
        else goto bad;
        if(!strcmp(part,"claymore"))pending[i].annotation.tactic=CODOL_BOT_TACTIC_CLAYMORE;
        else if(!strcmp(part,"grenade"))pending[i].annotation.tactic=CODOL_BOT_TACTIC_GRENADE;
        else if(!strcmp(part,"javelin"))pending[i].annotation.tactic=CODOL_BOT_TACTIC_JAVELIN;
        j=vector(field(&columns),pending[i].annotation.angles);if(j<0)goto bad;pending[i].annotation.hasAngles=(j==1);
        j=vector(field(&columns),pending[i].annotation.target);if(j<0)goto bad;pending[i].annotation.hasTarget=(j==1);
        /* Empty trailing fields are allowed; unknown nonempty data is not
         * silently discarded or misread as a graph link. */
        while((part=field(&columns))!=NULL){while(isspace((unsigned char)*part))++part;if(*part)goto bad;}
    }
    while((row=line(&cursor))!=NULL){while(isspace((unsigned char)*row))++row;if(*row)goto bad;}
    memcpy(nodes,pending,(size_t)total*sizeof(*nodes));count=(int)total;
    nav_label_components();
    free(pending);FS_FreeFile(buffer);return count;
bad:free(pending);FS_FreeFile(buffer);return 0;
}
/* The waypoint graph is per-map native state, so the map lifecycle loads it.
 *
 * MEASURED 2026-09-21: the only caller of CODOL_BotNavLoad -- the sole writer
 * of `count` -- was the `loadbotwaypoints` builtin, called from
 * maps/mp/gametypes/_codol_bots::init(), which only maps/mp/gametypes/_gamelogic
 * threads (:1508).  The zm gametype never runs _gamelogic on purpose
 * (zm/maps/mp/gametypes/zm.gsc calls _callbacksetup + _zombiemode::init and
 * nothing else), so on a zm map nothing ever wrote `count` and this
 * file-static kept the PREVIOUS map's nodes.  bin/home/main/qconsole.log,
 * 2026-09-21 00:00: zm_prototype_sh zombies planned "route node 170 -> 48:
 * 9 nodes" over mp_rust's 192-node graph, walked at coordinates that mean
 * nothing in that map, wedged ("stuck ... -> repath", "no clear nav node
 * within 256 to snap to") and never reached the player.  It also suppressed
 * the actor mover's straight-line fallback, which only engages when
 * CODOL_BotNavCount() is 0.
 *
 * Loading here gives every category the graph its own map ships and an empty
 * one where there is none (no zm/coop map has a waypoint CSV, and CoDOL ships
 * no pathdata asset class at all -- docs/zone_assets).  Returning 0 is a
 * normal outcome, not a failure. */
int CODOL_BotNavLoadForMap(const char *mapname)
{
    char path[MAX_QPATH];
    if(!mapname || !*mapname){count=0;return 0;}
    Com_sprintf(path,sizeof(path),"waypoints/%s_wp.csv",mapname);
    return CODOL_BotNavLoad(path);
}
int CODOL_BotNavCount(void){return count;}

/* ---------------------------------------------------------------------------
 * The map's own AI graph.
 *
 * MEASURED 2026-09-21 (obj/zm-mapents/zm_prototype_sh-mapents.txt, parsed out
 * of the col_map_mp entity lump): zm_prototype_sh carries 691 node_pathnode
 * plus 12 node_negotiation_begin / 12 node_negotiation_end entities -- the IW
 * AI node set -- and mp_killhouse_sh carries 660 + node_guard/node_cover_*.
 * The compiled link table is NOT in the zone: replay_game_world_mp
 * (codol_load_blocks.c) zeroes GameWorldMp bytes 4..71 (the PathData slot)
 * without consuming any stream bytes, which is only possible because every
 * CoDOL map ships it empty.  That matches the engine: C1.exe carries the
 * runtime connector's strings ("PATH_MAX_NODES (%i) exceeded.  Nodecount: %d",
 * "Pathnode (%s) at (%g %g %g) has no connections leaving it"), i.e. CoDOL
 * connects its nodes at map load exactly like T5 Path_ConnectPaths
 * (OpenBLOPS Game/Server/game/pathnode_load_obj.cpp:1517), which links every
 * ordered pair that Path_CanLinkNodes accepts (:1380):
 *   - |dz| <= 128 and horizontal distance <= 256,
 *   - an actor capsule (+-15.5 xy, actorMins/Maxs z) walked from A toward B
 *     in 4-unit wishes under gravity, failing on any hit, on a ground drop
 *     of more than 32, or on more than 96 steps,
 *   - and |z_end - z_B| <= 18 on arrival;
 *   - a negotiation begin node links only to its own end node (dist 15).
 * The walk below is that rule on this server's capsule trace: 8-unit steps
 * (half the iteration budget), an 18-unit step-up before each step and a
 * 32-unit drop test after it.  Dynamic blocking entities are irrelevant here
 * because it runs from GScr_LoadScripts, before any entity is spawned --
 * T5 zeroes their contents for the duration for the same reason.
 *
 * This is the "fix maps, don't pin" answer for zm/coop: the map is the
 * authority for its own navigation.  The hand-authored CSV still wins on the
 * mp maps that have one (the bots were tuned on it), so this only runs when
 * the CSV load left the graph empty.
 * ------------------------------------------------------------------------ */
#include "server.h"
#include "entity.h"
#include "qcommon_io.h"
#include "g_shared.h"
#include "g_public.h"
#include "sys_main.h"
unsigned CODOL_PathNodeCount(void);
const char *CODOL_PathNodeValue(unsigned index, const char *key);
int CODOL_PathNodeOrigin(unsigned index, float *origin);
/* T5 actor hull (OpenBLOPS actor.h:452): actorMins {-15,-15,0}, actorMaxs
 * {15,15,48}.  Path_CanLinkNodes widens xy by 0.5.  The 72-unit PLAYER
 * height this port first used is 24 taller than any zombie the graph is
 * for, and clipped door lintels and stair ceilings for nothing. */
#define MAP_LINK_MAX_XY 256.0f         /* T5: fDistSqrd <= 65536 */
#define MAP_LINK_MAX_DZ 128.0f
#define MAP_LINK_STEP 8.0f
#define MAP_LINK_STEP_UP 18.0f
#define MAP_LINK_MAX_DROP 32.0f
#define MAP_LINK_ARRIVE 4.0f           /* T5: fDistSqrd <= 16 */
#define MAP_LINK_ARRIVE_DZ 18.0f       /* T5: |z_end - z_to| <= 18 */
#define MAP_LINK_FLAT 4.0f             /* fast path: floor within +-4 of a.z along the line */
#define MAP_LINK_WALKABLE_NORMAL 0.7f /* same ground threshold as actor physics */
#define MAP_LINK_TRACE_MASK 0x2820011  /* T5 Path_CanLinkNodes phys.iTraceMask */
#define MAP_DROP_TRACE_MASK 0x820011   /* T5 node_droptofloor */
#define MAP_DROP_DEPTH 256.0f
#define MAP_GRID 256.0f
#define MAP_GRID_HASH 4096
#define MAP_BAD_PRINT 6
static const float map_actor_mins[3] = {-15.5f, -15.5f, 0.0f};
static const float map_actor_maxs[3] = {15.5f, 15.5f, 48.0f};
/* Rejection census, one counter per exit of the link test, printed at the end
 * of the build so ONE boot says why a pair did not link.  The forward-hit
 * counters split by what the capsule hit: world solid (CONTENTS_SOLID),
 * monsterclip (0x20000 without solid), anything else (glass, the runtime
 * bits). */
enum {
    MAP_R_DZ, MAP_R_XY, MAP_R_COINCIDENT, MAP_R_FWD_STARTSOLID, MAP_R_FWD_HIT_SOLID,
    MAP_R_FWD_HIT_MONSTERCLIP, MAP_R_FWD_HIT_OTHER, MAP_R_NO_FLOOR, MAP_R_DOWN_STARTSOLID,
    MAP_R_STEP_BUDGET, MAP_R_ARRIVE_DZ, MAP_R_LINK_CAP, MAP_R_LINK, MAP_R_COUNT
};
static const char *const map_reason_names[MAP_R_COUNT] = {
    "dz>128", "xy>256", "coincident", "fwd startsolid", "fwd hit solid", "fwd hit monsterclip",
    "fwd hit other", "no walkable floor within drop", "down startsolid", "step budget", "arrival dz>18",
    "link cap", "link"
};
static unsigned map_hist[MAP_R_COUNT];
static unsigned map_fast_path;
static int map_hit_reason(const trace_t *tr)
{
    if (tr->cflags & 0x1) return MAP_R_FWD_HIT_SOLID;
    if (tr->cflags & 0x20000) return MAP_R_FWD_HIT_MONSTERCLIP;
    return MAP_R_FWD_HIT_OTHER;
}
/* Floor z under (x,y) for the actor hull, searching from z+up down to z-down.
 * Returns 0 when nothing is found (or the start is in solid: *solid=1). */
static int map_floor_at(float x, float y, float z, float up, float down, float *floor, int *solid)
{
    float start[3], end[3];
    trace_t tr;
    start[0] = end[0] = x; start[1] = end[1] = y; start[2] = z + up; end[2] = z - down;
    G_TraceCapsule(&tr, start, map_actor_mins, map_actor_maxs, end, ENTITYNUM_NONE, MAP_LINK_TRACE_MASK);
    *solid = tr.startsolid || tr.allsolid;
    if (*solid || tr.fraction >= 1.0f || tr.normal[2] < MAP_LINK_WALKABLE_NORMAL) return 0;
    *floor = start[2] + (end[2] - start[2]) * tr.fraction;
    return 1;
}
/* The T5 rule on this server's capsule trace: 8-unit steps, an 18-unit
 * step-up before each step and a 32-unit drop test after it, arrive within
 * 18 in z.  Before the step walk, a flat-ground fast path: when the floor
 * sampled every 32 units along the line stays within +-4 of a.z and b is at
 * that height, the step walk's capsule is the same constant-height capsule
 * every step, so ONE full-length sweep decides it (6 traces instead of ~64).
 * Returns a MAP_R_* reason. */
static int map_link_walk(const float *from, const float *to)
{
    float pos[3], dir[2], len, start[3], end[3], down[3], floor, t;
    trace_t tr;
    int steps, solid, flat = fabsf(to[2] - from[2]) <= MAP_LINK_FLAT;
    dir[0] = to[0] - from[0]; dir[1] = to[1] - from[1];
    len = sqrtf(dir[0]*dir[0] + dir[1]*dir[1]);
    if (len < 1.0f) return MAP_R_COINCIDENT;
    dir[0] /= len; dir[1] /= len;
    for (t = 32.0f; flat && t < len; t += 32.0f) {
        if (!map_floor_at(from[0] + dir[0]*t, from[1] + dir[1]*t, from[2], MAP_LINK_STEP_UP, MAP_LINK_MAX_DROP, &floor, &solid)
            || fabsf(floor - from[2]) > MAP_LINK_FLAT) flat = 0;
    }
    if (flat) {
        start[0] = from[0]; start[1] = from[1]; start[2] = from[2] + MAP_LINK_STEP_UP;
        end[0] = to[0]; end[1] = to[1]; end[2] = start[2];
        G_TraceCapsule(&tr, start, map_actor_mins, map_actor_maxs, end, ENTITYNUM_NONE, MAP_LINK_TRACE_MASK);
        if (tr.startsolid || tr.allsolid) return MAP_R_FWD_STARTSOLID;
        if (tr.fraction < 1.0f) return map_hit_reason(&tr);
        ++map_fast_path;
        return MAP_R_LINK;
    }
    pos[0] = from[0]; pos[1] = from[1]; pos[2] = from[2];
    for (steps = 0; steps < 96; ++steps) {
        float dx = to[0] - pos[0], dy = to[1] - pos[1], remain = sqrtf(dx*dx + dy*dy), adv;
        if (remain <= MAP_LINK_ARRIVE) break;
        adv = remain < MAP_LINK_STEP ? remain : MAP_LINK_STEP;
        start[0] = pos[0]; start[1] = pos[1]; start[2] = pos[2] + MAP_LINK_STEP_UP;
        end[0] = start[0] + dir[0]*adv; end[1] = start[1] + dir[1]*adv; end[2] = start[2];
        G_TraceCapsule(&tr, start, map_actor_mins, map_actor_maxs, end, ENTITYNUM_NONE, MAP_LINK_TRACE_MASK);
        if (tr.startsolid || tr.allsolid) return MAP_R_FWD_STARTSOLID;
        if (tr.fraction < 1.0f) return map_hit_reason(&tr);
        down[0] = end[0]; down[1] = end[1]; down[2] = end[2] - MAP_LINK_STEP_UP - MAP_LINK_MAX_DROP;
        G_TraceCapsule(&tr, end, map_actor_mins, map_actor_maxs, down, ENTITYNUM_NONE, MAP_LINK_TRACE_MASK);
        if (tr.startsolid || tr.allsolid) return MAP_R_DOWN_STARTSOLID;
        /* A near-vertical face can be the first hit of this downward sweep.
         * Actor physics refuses it as ground, so it cannot support a nav
         * edge even when the trace returned a fraction below one. */
        if (tr.fraction >= 1.0f || tr.normal[2] < MAP_LINK_WALKABLE_NORMAL)
            return MAP_R_NO_FLOOR;
        pos[0] = end[0]; pos[1] = end[1];
        pos[2] = end[2] + (down[2] - end[2]) * tr.fraction;
    }
    if (steps >= 96) return MAP_R_STEP_BUDGET;
    return fabsf(pos[2] - to[2]) <= MAP_LINK_ARRIVE_DZ ? MAP_R_LINK : MAP_R_ARRIVE_DZ;
}
/* T5 node_droptofloor (OpenBLOPS pathnode.cpp:327), run for every node
 * before linking (G_SpawnPathnodes, :513): from origin+1 down 256 with the
 * actor hull cut to 30 tall, mask 0x820011; in solid or floating -> the
 * node becomes NODE_BADNODE and is never linked; otherwise the origin moves
 * to the landing and a stationary full-height probe must be clear.
 *
 * MEASURED 2026-09-21 (tools/codol_path_link_census.py, point trace): the
 * authored node origins float 7..78 units above their floor on
 * zm_prototype_sh (mode 28), 2..80+ on zm_asylum_sh, 18..46 on
 * zm_zombie_training -- not one node within 7 of its floor.  C1.exe carries
 * this pass too ("is floating" 0x8794fc, "has no connections leaving it"
 * 0x8794dc).  Without it the walk started 28 above the floor, the drop
 * test failed for every node more than 32 up, and the arrival test failed
 * for the rest because the walker's z had snapped to the floor while the
 * target's had not: 620 of 715 nodes isolated. */
static int map_drop_to_floor(float *origin, int *reason)
{
    static const float drop_mins[3] = {-15.0f, -15.0f, 0.0f};
    static const float drop_maxs[3] = {15.0f, 15.0f, 30.0f};
    static const float probe_mins[3] = {-15.0f, -15.0f, 0.0f};
    static const float probe_maxs[3] = {15.0f, 15.0f, 48.0f};
    float start[3], end[3];
    trace_t tr;
    start[0] = end[0] = origin[0]; start[1] = end[1] = origin[1];
    start[2] = origin[2] + 1.0f; end[2] = origin[2] - (MAP_DROP_DEPTH - 1.0f);
    G_TraceCapsule(&tr, start, drop_mins, drop_maxs, end, ENTITYNUM_NONE, MAP_DROP_TRACE_MASK);
    if (tr.startsolid || tr.allsolid) { *reason = 0; return 0; }
    if (tr.fraction >= 1.0f) { *reason = 1; return 0; }
    end[2] = start[2] + (end[2] - start[2]) * tr.fraction;
    G_TraceCapsule(&tr, end, probe_mins, probe_maxs, end, ENTITYNUM_NONE, MAP_DROP_TRACE_MASK);
    if (tr.startsolid || tr.allsolid) { *reason = 2; return 0; }
    origin[2] = end[2];
    return 1;
}
/* Union-find over the links, treated as undirected, for the load-time
 * reachability census. */
static int map_find(int *parent, int i) { while (parent[i] != i) i = parent[i] = parent[parent[i]]; return i; }
static int map_grid_cell(float v) { return (int)floorf(v / MAP_GRID); }
static unsigned map_grid_hash(int cx, int cy) { return ((unsigned)cx * 73856093u ^ (unsigned)cy * 19349663u) & (MAP_GRID_HASH - 1); }
static const char *map_spawn_value(const SpawnVar *record, const char *key)
{
    int i;
    for (i = 0; i < record->numSpawnVars; ++i)
        if (!Q_stricmp(record->spawnVars[i].key, key)) return record->spawnVars[i].value;
    return NULL;
}
void CODOL_BotNavBuildFromMapNodesIfEmpty(void)
{
    unsigned total = CODOL_PathNodeCount(), i, j, used = 0, links = 0, negotiation = 0, isolated = 0, sinks = 0;
    unsigned bad[3] = {0, 0, 0}, printed = 0, components = 0, main_component = 0, main_size = 0, off_main = 0;
    int *index, *head, *next, *cx, *cy, *parent, *entering;
    int start_ms = Sys_Milliseconds();
    if (count > 0 || !total) return;   /* a CSV graph is loaded, or the map has no nodes */
    index = calloc(total, sizeof(*index));
    head = malloc(MAP_GRID_HASH * sizeof(*head));
    next = calloc(total, sizeof(*next));
    cx = calloc(total, sizeof(*cx));
    cy = calloc(total, sizeof(*cy));
    parent = calloc(total, sizeof(*parent));
    entering = calloc(total, sizeof(*entering));
    if (!index || !head || !next || !cx || !cy || !parent || !entering) {
        free(index); free(head); free(next); free(cx); free(cy); free(parent); free(entering);
        return;
    }
    memset(nodes, 0, sizeof(nodes));
    memset(map_hist, 0, sizeof(map_hist));
    map_fast_path = 0;
    for (i = 0; i < MAP_GRID_HASH; ++i) head[i] = -1;
    for (i = 0; i < total; ++i) {
        const char *cls = CODOL_PathNodeValue(i, "classname"), *flags = CODOL_PathNodeValue(i, "spawnflags");
        int reason;
        index[i] = -1;
        if (!cls || strncmp(cls, "node_", 5)) continue;
        if (flags && (strtol(flags, NULL, 10) & 1)) continue;         /* T5: DONT_LINK */
        if (used >= CODOL_BOT_NODES) break;
        if (!CODOL_PathNodeOrigin(i, nodes[used].point)) continue;
        if (!map_drop_to_floor(nodes[used].point, &reason)) {
            static const char *const why[3] = {"is in solid", "is floating", "lands in solid"};
            ++bad[reason];
            if (printed++ < MAP_BAD_PRINT)
                Com_PrintError(CON_CHANNEL_SERVER, "ERROR: Pathnode (%s) at (%g %g %g) %s\n", cls,
                    nodes[used].point[0], nodes[used].point[1], nodes[used].point[2], why[reason]);
            continue;
        }
        nodes[used].stance = strcmp(cls, "node_cover_crouch") == 0 || strcmp(cls, "node_cover_prone") == 0
            ? CODOL_BOT_CROUCH : CODOL_BOT_STAND;
        nodes[used].record = (short)i;
        nodes[used].negotiationEnd = -1;
        cx[used] = map_grid_cell(nodes[used].point[0]);
        cy[used] = map_grid_cell(nodes[used].point[1]);
        j = map_grid_hash(cx[used], cy[used]);
        next[used] = head[j]; head[j] = (int)used;
        parent[used] = (int)used;
        index[i] = (int)used++;
    }
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL waypoint graph: %u map nodes dropped to the floor (%u in solid, %u floating, %u landing in solid skipped); connecting (T5 Path_ConnectPaths rule)...\n",
        used, bad[0], bad[1], bad[2]);
    for (i = 0; i < total; ++i) {
        const char *cls, *target;
        int a = index[i], dcx, dcy;
        if (a < 0) continue;
        cls = CODOL_PathNodeValue(i, "classname");
        if (cls && !strcmp(cls, "node_negotiation_begin")) {
            /* T5 Path_IsNegotiationLink: begin -> its targeted end, unconditionally
             * (dist 15).  Geometric links are still attempted below, as T5 does. */
            target = CODOL_PathNodeValue(i, "target");
            for (j = 0; target && j < total; ++j) {
                const char *tn = index[j] >= 0 ? CODOL_PathNodeValue(j, "targetname") : NULL;
                if (tn && !strcmp(tn, target) && nodes[a].count < LINKS) {
                    nodes[a].links[nodes[a].count++] = (unsigned short)index[j];
                    nodes[a].negotiationEnd = (short)index[j];
                    nodes[a].stance = nodes[index[j]].stance = CODOL_BOT_NEGOTIATE;   /* T5 traversal link: every actor may take it */
                    ++entering[index[j]];
                    parent[map_find(parent, a)] = map_find(parent, index[j]);
                    ++links; ++negotiation;
                }
            }
        }
        /* Every other node in the 3x3 grid neighbourhood is a candidate; the
         * T5 dz/xy gates then the walk decide.  Nodes outside the
         * neighbourhood are more than 256 apart on some axis and fail xy. */
        for (dcy = -1; dcy <= 1; ++dcy) for (dcx = -1; dcx <= 1; ++dcx) {
            int b;
            for (b = head[map_grid_hash(cx[a] + dcx, cy[a] + dcy)]; b >= 0; b = next[b]) {
                float dx, dy, dz;
                int r, k, dup = 0;
                if (cx[b] != cx[a] + dcx || cy[b] != cy[a] + dcy || b == a) continue;
                dx = nodes[b].point[0] - nodes[a].point[0];
                dy = nodes[b].point[1] - nodes[a].point[1];
                dz = nodes[b].point[2] - nodes[a].point[2];
                if (dz < -MAP_LINK_MAX_DZ || dz > MAP_LINK_MAX_DZ) { ++map_hist[MAP_R_DZ]; continue; }
                if (dx*dx + dy*dy > MAP_LINK_MAX_XY*MAP_LINK_MAX_XY) { ++map_hist[MAP_R_XY]; continue; }
                for (k = 0; k < nodes[a].count; ++k) if (nodes[a].links[k] == b) dup = 1;
                if (dup) continue;                                   /* the negotiation link above */
                r = map_link_walk(nodes[a].point, nodes[b].point);
                if (r == MAP_R_LINK && nodes[a].count >= LINKS) r = MAP_R_LINK_CAP;
                ++map_hist[r];
                if (r != MAP_R_LINK) continue;
                nodes[a].links[nodes[a].count++] = (unsigned short)b;
                ++entering[b];
                parent[map_find(parent, a)] = map_find(parent, b);
                ++links;
            }
        }
        if (!nodes[a].count) {
            ++isolated;
            if (isolated <= MAP_BAD_PRINT)
                Com_PrintError(CON_CHANNEL_SERVER, "ERROR: Pathnode (%s) at (%g %g %g) has no connections leaving it\n",
                    cls ? cls : "?", nodes[a].point[0], nodes[a].point[1], nodes[a].point[2]);
        }
    }
    count = (int)used;
    nav_label_components();
    /* Component census: the largest component is "main"; every spawner and
     * exterior goal must reach it or the zombies it feeds can never arrive. */
    for (i = 0; i < used; ++i) {
        if (!entering[i]) ++sinks;
        if (map_find(parent, (int)i) == (int)i) ++components;
    }
    for (i = 0; i < used; ++i) {
        unsigned size = 0;
        if (map_find(parent, (int)i) != (int)i) continue;
        for (j = 0; j < used; ++j) if (map_find(parent, (int)j) == (int)i) ++size;
        if (size > main_size) { main_size = size; main_component = i; }
    }
    off_main = used - main_size;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL waypoint graph: built from the map in %d ms: %u nodes, %u links (%u negotiation, %u flat fast-path), %u nodes with no link leaving them, %u with none entering, %u components (main %u nodes, %u off it)\n",
        Sys_Milliseconds() - start_ms, used, links, negotiation, map_fast_path, isolated, sinks, components, main_size, off_main);
    Com_Printf(CON_CHANNEL_SERVER, "CoDOL waypoint graph: link test census:");
    for (i = 0; i < MAP_R_COUNT; ++i)
        if (map_hist[i]) Com_Printf(CON_CHANNEL_SERVER, " %s=%u", map_reason_names[i], map_hist[i]);
    Com_Printf(CON_CHANNEL_SERVER, "\n");
    if (used) {
        /* zombie_spawner structs name their node by target; exterior_goal
         * structs sit outside the window, so the nearest node stands in. */
        SpawnVar parsed;
        unsigned spawners = 0, goals = 0, spawners_off = 0, goals_off = 0;
        G_ResetEntityParsePoint();
        while (G_ParseSpawnVars(&parsed)) {
            const char *cls = map_spawn_value(&parsed, "classname"), *note, *tn, *target, *origin;
            float point[3];
            int node = -1, is_spawner, is_goal;
            if (!cls || strcmp(cls, "script_struct")) continue;
            note = map_spawn_value(&parsed, "script_noteworthy"); tn = map_spawn_value(&parsed, "targetname");
            is_spawner = note && !strcmp(note, "zombie_spawner");
            is_goal = tn && !strcmp(tn, "exterior_goal");
            if (!is_spawner && !is_goal) continue;
            target = map_spawn_value(&parsed, "target");
            for (j = 0; target && j < total && node < 0; ++j) {
                const char *ntn = index[j] >= 0 ? CODOL_PathNodeValue(j, "targetname") : NULL;
                if (ntn && !strcmp(ntn, target)) node = index[j];
            }
            origin = map_spawn_value(&parsed, "origin");
            if (node < 0 && origin && sscanf(origin, "%f %f %f", &point[0], &point[1], &point[2]) == 3)
                node = CODOL_BotNavNearest(point);
            if (is_spawner) ++spawners; else ++goals;
            if (node < 0 || map_find(parent, node) != map_find(parent, (int)main_component)) {
                if (is_spawner) ++spawners_off; else ++goals_off;
                if (spawners_off + goals_off <= MAP_BAD_PRINT)
                    Com_PrintError(CON_CHANNEL_SERVER, "CoDOL waypoint graph: %s at (%s) -> node %d is off the main component\n",
                        is_spawner ? "zombie_spawner" : "exterior_goal", origin ? origin : "?", node);
            }
        }
        G_ResetEntityParsePoint();
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL waypoint graph: %u zombie_spawner (%u off the main component), %u exterior_goal (%u off)\n",
            spawners, spawners_off, goals, goals_off);
    }
    free(index); free(head); free(next); free(cx); free(cy); free(parent); free(entering);
}
const float *CODOL_BotNavPoint(int node){return node>=0&&node<count?nodes[node].point:NULL;}
int CODOL_BotNavStance(int node){return node>=0&&node<count?nodes[node].stance:CODOL_BOT_STAND;}
int CODOL_BotNavComponent(int node){return node>=0&&node<count?nodes[node].component:-1;}
const codol_bot_route_stats_t *CODOL_BotNavLastRouteStats(void){return &route_stats;}
int CODOL_BotNavNearest(const float *point)
{int i,best=-1;float d,minimum=FLT_MAX;for(i=0;i<count;++i){d=distance(point,nodes[i].point);if(d<minimum){minimum=d;best=i;}}return best;}
const codol_bot_annotation_t *CODOL_BotNavAnnotation(int node)
{return node>=0&&node<count?&nodes[node].annotation:NULL;}
int CODOL_BotNavRouteFiltered(int from,int to,unsigned short *path,int capacity,codol_bot_edge_filter_t allow,void *context)
{
    float cost[CODOL_BOT_NODES],score[CODOL_BOT_NODES],best;
    short parent[CODOL_BOT_NODES];unsigned char closed[CODOL_BOT_NODES]={0};
    unsigned short reverse[CODOL_BOT_NODES];int i,j,current,next,length=0;
    memset(&route_stats,0,sizeof(route_stats));
    if(from<0||to<0||from>=count||to>=count||!path||capacity<1){route_stats.stop=2;return 0;}
    for(i=0;i<count;++i){cost[i]=score[i]=FLT_MAX;parent[i]=-1;}
    cost[from]=0;score[from]=distance(nodes[from].point,nodes[to].point);
    for(i=0;i<count;++i){
        current=-1;best=FLT_MAX;for(j=0;j<count;++j)if(!closed[j]&&score[j]<best){best=score[j];current=j;}
        if(current<0){route_stats.stop=1;return 0;}
        if(current==to){for(j=to;j!=-1;j=parent[j]){if(length>=capacity){route_stats.stop=3;return 0;}reverse[length++]=(unsigned short)j;}for(j=0;j<length;++j)path[j]=reverse[length-j-1];return length;}
        closed[current]=1;++route_stats.expanded;
        for(j=0;j<nodes[current].count;++j){float candidate;next=nodes[current].links[j];if(closed[next])continue;
            if(nodes[current].blocker[j])continue;   /* cut by DisconnectPaths (a barrier clip, a door) */
            if(allow && !allow(current,next,context)){++route_stats.filtered;continue;}
            candidate=cost[current]+distance(nodes[current].point,nodes[next].point);
            if(candidate<cost[next]){parent[next]=(short)current;cost[next]=candidate;score[next]=candidate+distance(nodes[next].point,nodes[to].point);}
        }
    }
    route_stats.stop=1;
    return 0;
}
int CODOL_BotNavRoute(int from,int to,unsigned short *path,int capacity)
{return CODOL_BotNavRouteFiltered(from,to,path,capacity,NULL,NULL);}
int CODOL_BotNavNegotiationEnd(int node){return node>=0&&node<count?nodes[node].negotiationEnd:-1;}
int CODOL_BotNavRecord(int node){return node>=0&&node<count?nodes[node].record:-1;}
int CODOL_BotNavLinkBlocked(int from,int to)
{
    int j;
    if(from<0||from>=count)return 0;
    for(j=0;j<nodes[from].count;++j)if(nodes[from].links[j]==to)return nodes[from].blocker[j];
    return 0;
}
/* Segment a->b, swept as the actor hull (T5 actorMins/Maxs {-15,-15,0}..
 * {15,15,48}, the hull the links were walked with), against the box:
 * slab test on the box grown by the hull.  Node points sit on the floor,
 * so the hull's height is what lets a floor-level link meet a clip brush
 * whose bottom is above the floor (the zm window clips start ~25 up). */
static int nav_segment_crosses_box(const float *a,const float *b,const float *mins,const float *maxs)
{
    float lo[3],hi[3],t0=0,t1=1;int i;
    for(i=0;i<3;++i){lo[i]=mins[i]-(i==2?48.0f:15.0f);hi[i]=maxs[i]+(i==2?0.0f:15.0f);}
    for(i=0;i<3;++i){
        float d=b[i]-a[i];
        if(fabsf(d)<0.0001f){if(a[i]<lo[i]||a[i]>hi[i])return 0;continue;}
        {float ta=(lo[i]-a[i])/d,tb=(hi[i]-a[i])/d;if(ta>tb){float x=ta;ta=tb;tb=x;}
         if(ta>t0)t0=ta;if(tb<t1)t1=tb;if(t0>t1)return 0;}
    }
    return 1;
}
/* T5 Path_DisconnectPathsForEntity (OpenBLOPS pathnode.cpp:3182): a link
 * near the entity is cut only when the capsule {-15,-15,18}..{15,15,48}
 * swept along it hits the ENTITY'S OWN brushes (SV_SightTraceCapsuleToEntity,
 * mask 0x2820011), not its bounding box.  The box test alone cut every link
 * through a diagonal window's AABB: zm_zombie_training's window at
 * (565 1335 272) faces 225 degrees, its clip's box (497 1266)-(567 1336)
 * swallowed all 37 links into the negotiation begin node from the yard, and
 * every zombie from that yard found no path to its own window. */
static int nav_link_hits_entity(int entnum,const float *a,const float *b)
{
    static const float cmins[3]={-15.0f,-15.0f,18.0f},cmaxs[3]={15.0f,15.0f,48.0f};
    gentity_t *ent=&g_entities[entnum];
    trace_t tr;
    /* An entity with none of the traced contents (a script_model chunk) is
     * judged by its box, as before. */
    if(!(ent->r.contents&0x2820011))return 1;
    /* CM_TransformedBoxTrace only lowers the fraction it is given (the
     * retained SV_ClipMoveToEntity passes its running trace); SV_ClipToEntity
     * zeroes it first and so reports a hit for every trace. */
    memset(&tr,0,sizeof(tr));
    tr.fraction=1.0f;
    CM_TransformedBoxTrace(&tr,a,b,cmins,cmaxs,SV_ClipHandleForEntity(ent),0x2820011,ent->r.currentOrigin,
        ent->r.bmodel?ent->r.currentAngles:vec3_origin);
    return tr.startsolid||tr.allsolid||tr.fraction<1.0f;
}
int CODOL_BotNavDisconnectPaths(int entnum,const float *mins,const float *maxs)
{
    int i,j,changed=0;unsigned short tag;
    if(entnum<0||entnum>=65534||!mins||!maxs)return 0;
    tag=(unsigned short)(entnum+1);
    for(i=0;i<count;++i)for(j=0;j<nodes[i].count;++j){
        if(nodes[i].blocker[j])continue;   /* already cut (by this or another entity): first cutter owns it */
        if(!nav_segment_crosses_box(nodes[i].point,nodes[nodes[i].links[j]].point,mins,maxs))continue;
        if(entnum<ENTITYNUM_WORLD&&!nav_link_hits_entity(entnum,nodes[i].point,nodes[nodes[i].links[j]].point))continue;
        nodes[i].blocker[j]=tag;++changed;
    }
    return changed;
}
int CODOL_BotNavConnectPaths(int entnum)
{
    int i,j,changed=0;unsigned short tag;
    if(entnum<0||entnum>=65534)return 0;
    tag=(unsigned short)(entnum+1);
    for(i=0;i<count;++i)for(j=0;j<nodes[i].count;++j)
        if(nodes[i].blocker[j]==tag){nodes[i].blocker[j]=0;++changed;}
    return changed;
}
#endif
