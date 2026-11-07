/* RC-XD wheel spin producer. See codol_vehicle_wheel_anim.h for the C1
 * evidence (why the wheels only turn under server animation commands).
 *
 * Clip facts, MEASURED from common_mp.zone (the xanim records themselves):
 *   rccar_front_driving_forward   58 frames @30, loop; front wheel bones
 *   rccar_back_driving_forward    58 frames @30, loop; back wheel bones
 *     left/right_wheel_0N_jnt: 31 full-quat keys about +Y, +61 deg per key,
 *     1800 deg over the clip = 5 wheel revolutions per cycle.
 *   rccar_front_driving_backward  59 frames @30, loop
 *   rccar_back_driving_backward   59 frames @30, loop
 *     the same bones, -48 deg per key, 1440 deg = 4 revolutions per cycle.
 * The front clips animate only left/right_wheel_01_jnt (plus static tags), the
 * back clips only _02_jnt, so all four sit under the tree root at once and
 * the forward and backward pairs swap weights on a direction change.
 * Playback rate 1 therefore rolls the car at 2*pi*r*revs/cycle_seconds; the
 * producer divides the body's forward speed by that to get the rate.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_vehicle_wheel_anim.h"
#include "codol_actor_anim_journal.h"
#include "codol_model_animation.h"
#include "codol_entitystate_ext.h"
#include "codol_engine_state.h"
#include "scr_vm_functions.h"
#include "xassets/xanims.h"
#include "dobj.h"
#include "qcommon_io.h"

#include <math.h>
#include <string.h>

extern XAnim_s *Scr_GetAnims(unsigned int index);
extern void G_DObjUpdate(gentity_t *entity);
extern int XAnimSetGoalWeight(DObj *obj, unsigned int anim, float goalWeight,
                              float goalTime, float rate, unsigned int notifyName,
                              unsigned int notifyType, int bRestart);
extern int XAnimSetCompleteGoalWeight(DObj *obj, unsigned int anim, float goalWeight,
                                      float goalTime, float rate, unsigned int notifyName,
                                      unsigned int notifyType, int bRestart);
extern void XAnimClearTree(struct XAnimTree_s *tree);

#define WHEEL_OWNERS 8
enum { FRONT_FORWARD, BACK_FORWARD, FRONT_BACKWARD, BACK_BACKWARD, CLIP_COUNT };
static const char *const clip_names[CLIP_COUNT] = {
    "rccar_front_driving_forward", "rccar_back_driving_forward",
    "rccar_front_driving_backward", "rccar_back_driving_backward"
};
/* Wheel revolutions in one cycle of the forward and the backward clips. */
static const float clip_revolutions[2] = { 5.0f, 4.0f };
/* Below this body speed (in/s) the wheels hold their angle. */
#define WHEEL_DEADBAND 2.0f
/* The clip pair only swaps past this speed, so contact jitter and bounces
 * off a wall do not flap forward/backward (four commands per flap). */
#define WHEEL_REVERSE_SPEED 10.0f
/* The journal validator and the wire codec both stop at rate 5. */
#define WHEEL_MAX_RATE 5.0f
/* A rate change smaller than this waits for WHEEL_REFRESH_MS, so steady
 * acceleration does not publish two commands on every server frame. */
#define WHEEL_RATE_STEP 0.25f
#define WHEEL_REFRESH_MS 500
#define WHEEL_BLEND 0.15f

typedef struct {
    int used;
    unsigned entity;
    int useCount;
    struct XAnimTree_s tree;
    unsigned refs[CLIP_COUNT];
    /* in/s of body speed at playback rate 1, forward and backward. */
    float unit_speed[2];
    int direction; /* 0 = nothing published yet, 1 forward, -1 backward */
    float rate;
    int publish_time;
    unsigned client_tree;
    int warned;
} wheel_owner_t;

static wheel_owner_t owners[WHEEL_OWNERS];

static int same_name(const char *a, const char *b)
{
    if(!a || !b) return 0;
    while(*a == '\\' || *a == '/') a++;
    while(*b == '\\' || *b == '/') b++;
    for(; *a && *b; a++, b++) {
        char x = *a, y = *b;
        if(x >= 'A' && x <= 'Z') x = (char)(x - 'A' + 'a');
        if(y >= 'A' && y <= 'Z') y = (char)(y - 'A' + 'a');
        if(x != y) return 0;
    }
    return *a == *b;
}

static wheel_owner_t *owner_for(const gentity_t *e)
{
    unsigned i;
    if(!e) return NULL;
    for(i = 0; i < WHEEL_OWNERS; i++)
        if(owners[i].used && owners[i].entity == (unsigned)e->s.number &&
           owners[i].useCount == e->useCount) return &owners[i];
    return NULL;
}

/* The exact value C1 will decode (codol_animcmd.c playback_rate): 1 is sent
 * exactly, otherwise 31 steps over 0..2 and 31 over 2..5. The server tree
 * gets the same value so a bootstrap from its captured pose matches. */
static float wire_rate(float v)
{
    float n;
    if(!(v > 0.0f)) return 0.0f;
    if(v > WHEEL_MAX_RATE) v = WHEEL_MAX_RATE;
    if(fabsf(v - 1.0f) < 1e-6f) return 1.0f;
    if(v > 2.0f) {
        n = rintf((v - 2.0f) / 3.0f * 31.0f);
        return 2.0f + n * 3.0f / 31.0f;
    }
    n = rintf(v / 2.0f * 31.0f);
    return n * 2.0f / 31.0f;
}

struct XAnimTree_s *CODOL_VehicleWheelAnimTree(const gentity_t *e)
{
    wheel_owner_t *o = owner_for(e);
    return o && o->tree.anims ? &o->tree : NULL;
}

int CODOL_VehicleWheelAnimAttach(gentity_t *e, float wheel_radius)
{
    unsigned tree, count, i, identity = 0, client_tree = 0;
    XAnim_s *anims;
    wheel_owner_t *o = NULL;
    float frequency[2];
    DObj *obj;
    if(!e || !e->r.inuse || owner_for(e)) return 0;
    if(!(wheel_radius > 0.0f)) {
        Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL rc wheels: ent %d has no wheel radius; wheels will not spin\n",
                         e->s.number);
        return 0;
    }
    count = CODOL_ServerAnimTreeCount();
    for(tree = 1; tree <= count; tree++)
        if(same_name(CODOL_ServerAnimTreeName(tree), "vehicles")) break;
    if(tree > count || !(anims = Scr_GetAnims(tree))) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL rc wheels: no server animtree \"vehicles\" (a loaded script must declare "
            "#using_animtree(\"vehicles\"), maps/mp/killstreaks/_rcbomb.gsc does); wheels will not spin\n");
        return 0;
    }
    for(i = 0; i < WHEEL_OWNERS; i++) if(!owners[i].used) { o = &owners[i]; break; }
    if(!o) return 0;
    memset(o, 0, sizeof(*o));
    for(i = 0; i < CLIP_COUNT; i++) {
        const XAnimEntry *entry;
        if(!CODOL_FindAnimInServerTree(tree, clip_names[i], &o->refs[i]) ||
           o->refs[i] >= anims->size) {
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL rc wheels: \"%s\" is not in the server vehicles tree (%u entries); wheels will not spin\n",
                clip_names[i], anims->size);
            return 0;
        }
        entry = &anims->entries[o->refs[i]];
        if(entry->numAnims || !entry->u.parts || !(entry->u.parts->frequency > 0.0f)) {
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL rc wheels: \"%s\" (entry %u) has no loaded clip; wheels will not spin\n",
                clip_names[i], o->refs[i]);
            return 0;
        }
    }
    if(!CODOL_ClientAnimTreeForServerTree(tree, &client_tree) || !client_tree || client_tree > 15) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL rc wheels: the client animlists give \"vehicles\" no 4-bit tree id; wheels will not spin\n");
        return 0;
    }
    if(!CODOL_EntityStateVehicleIdentity(&e->s, &identity) || !(identity >> 4) || (identity >> 4) >= 32) {
        Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL rc wheels: ent %d has no captured vehicle identity\n",
                         e->s.number);
        return 0;
    }
    frequency[0] = anims->entries[o->refs[FRONT_FORWARD]].u.parts->frequency;
    frequency[1] = anims->entries[o->refs[FRONT_BACKWARD]].u.parts->frequency;
    for(i = 0; i < 2; i++)
        o->unit_speed[i] = 2.0f * 3.14159265f * wheel_radius * clip_revolutions[i] * frequency[i];
    o->entity = (unsigned)e->s.number;
    o->useCount = e->useCount;
    o->tree.anims = anims;
    o->tree.children = 0;
    o->tree.pad = 0;
    o->client_tree = client_tree;
    o->used = 1;
    /* The retained G_DObjUpdate asks CODOL_ActorOwnedTree, which answers this
     * tree for a bound vehicle, so the rebuilt server DObj carries it. */
    G_DObjUpdate(e);
    obj = Com_GetServerDObj(e->s.number);
    if(!obj || DObjGetTree(obj) != &o->tree) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL rc wheels: ent %d server DObj %s the vehicles tree; wheels will not spin\n",
            e->s.number, obj ? "does not use" : "was not rebuilt with");
        memset(o, 0, sizeof(*o));
        G_DObjUpdate(e);
        return 0;
    }
    /* Wire +094 of every snapshot of this definition names the client tree
     * (codol_engine_state.c CODOL_OverlayEngineVehiclePose). */
    CODOL_SetVehicleDefinitionAnimTree(identity >> 4, client_tree);
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL rc wheels: ent %d bound server tree %u (%u entries) / client tree %u (definition %u), clips %u %u %u %u, "
        "rate-1 speed %.1f fwd / %.1f back in/s (radius %.1f)\n",
        e->s.number, tree, anims->size, client_tree, identity >> 4, o->refs[0], o->refs[1], o->refs[2], o->refs[3],
        o->unit_speed[0], o->unit_speed[1], wheel_radius);
    return 1;
}

static int apply(wheel_owner_t *o, DObj *obj, codol_actor_anim_event_t *event, unsigned ref,
                 float weight, float rate, int complete)
{
    const unsigned notifyType = weight > 0.001f ? 2u : 0u;
    int error = complete
        ? XAnimSetCompleteGoalWeight(obj, ref, weight, WHEEL_BLEND, rate, 0, notifyType, 0)
        : XAnimSetGoalWeight(obj, ref, weight, WHEEL_BLEND, rate, 0, notifyType, 0);
    if(error) return 0;
    memset(event, 0, sizeof(*event));
    event->generation = CODOL_ACTOR_INCARNATION(o->useCount);
    event->command.entity = (uint16_t)o->entity;
    event->command.time = (uint32_t)(level.time ? level.time : 50);
    /* C1 0x443e90 type 3 is the plain setanim family; arg2 bit 0 selects the
     * complete entry point (0x63c730), which raises the root's goal weight. */
    event->command.type = 3;
    event->command.ref = (uint16_t)ref;
    event->command.arg2 = (uint8_t)(complete ? 1 : 0);
    event->command.goal_weight = weight;
    event->command.blend = WHEEL_BLEND;
    event->command.playback_rate = rate;
    return 1;
}

void CODOL_VehicleWheelAnimFrame(gentity_t *e, float forward_speed, int now)
{
    wheel_owner_t *o = owner_for(e);
    codol_actor_anim_event_t events[CLIP_COUNT];
    unsigned count = 0, on, off;
    int direction;
    float speed, rate;
    DObj *obj;
    if(!o || !isfinite(forward_speed)) return;
    obj = Com_GetServerDObj(e->s.number);
    if(!obj || DObjGetTree(obj) != &o->tree) {
        if(!o->warned) {
            o->warned = 1;
            Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL rc wheels: ent %d lost its vehicles tree DObj\n",
                             e->s.number);
        }
        return;
    }
    direction = o->direction ? o->direction : 1;
    if(forward_speed > WHEEL_REVERSE_SPEED) direction = 1;
    else if(forward_speed < -WHEEL_REVERSE_SPEED) direction = -1;
    /* Speed along the playing direction; a slow roll the other way holds. */
    speed = direction > 0 ? forward_speed : -forward_speed;
    rate = speed > WHEEL_DEADBAND ? wire_rate(speed / o->unit_speed[direction < 0]) : 0.0f;
    if(direction == o->direction) {
        if(rate == o->rate) return;
        if(fabsf(rate - o->rate) < WHEEL_RATE_STEP && (rate == 0.0f) == (o->rate == 0.0f) &&
           now - o->publish_time < WHEEL_REFRESH_MS && now >= o->publish_time) return;
    }
    on = direction > 0 ? FRONT_FORWARD : FRONT_BACKWARD;
    off = direction > 0 ? FRONT_BACKWARD : FRONT_FORWARD;
    if(!apply(o, obj, &events[count++], o->refs[on], 1.0f, rate, 1) ||
       !apply(o, obj, &events[count++], o->refs[on + 1], 1.0f, rate, 1)) goto refused;
    if(o->direction && direction != o->direction) {
        if(!apply(o, obj, &events[count++], o->refs[off], 0.0f, o->rate, 0) ||
           !apply(o, obj, &events[count++], o->refs[off + 1], 0.0f, o->rate, 0)) goto refused;
    }
    if(!CODOL_ActorAnimJournalAppend(events, count)) {
        static int lastComplaint;
        if(!lastComplaint || now - lastComplaint >= 1000 || now < lastComplaint) {
            lastComplaint = now;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL rc wheels: ent %d animation journal refused %u commands at %d\n",
                e->s.number, count, level.time);
        }
    }
    if(o->direction != direction)
        Com_Printf(CON_CHANNEL_SERVER, "CoDOL rc wheels: ent %d %s rate %.3f (speed %.0f in/s) t %d\n",
                   e->s.number, direction > 0 ? "forward" : "backward", rate, forward_speed, now);
    o->direction = direction;
    o->rate = rate;
    o->publish_time = now;
    return;
refused:
    if(!o->warned) {
        o->warned = 1;
        Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL rc wheels: ent %d XAnim refused a wheel clip\n",
                         e->s.number);
    }
}

unsigned CODOL_VehicleWheelAnimCaptureSources(codol_dog_anim_capture_source_t *out, unsigned capacity)
{
    unsigned i, n = 0;
    for(i = 0; i < WHEEL_OWNERS && n < capacity; i++) {
        const wheel_owner_t *o = &owners[i];
        const gentity_t *e;
        DObj *obj;
        if(!o->used || o->entity >= MAX_GENTITIES) continue;
        e = &g_entities[o->entity];
        if(!e->r.inuse || e->useCount != o->useCount) continue;
        obj = Com_GetServerDObj((int)o->entity);
        if(!obj || obj->entnum != o->entity + 1 || DObjGetTree(obj) != &o->tree) continue;
        out[n].entity = o->entity;
        out[n].generation = CODOL_ACTOR_INCARNATION(o->useCount);
        out[n].tree = &o->tree;
        n++;
    }
    return n;
}

void CODOL_VehicleWheelAnimEntityFreed(const gentity_t *e)
{
    wheel_owner_t *o = owner_for(e);
    if(!o) return;
    /* G_FreeEntity clears the DObj's tree right after this hook; release the
     * info records here so that later clear finds an empty tree. */
    XAnimClearTree(&o->tree);
    o->tree.children = 0;
    o->used = 0;
}

void CODOL_VehicleWheelAnimReset(void)
{
    memset(owners, 0, sizeof(owners));
    CODOL_SetVehicleDefinitionAnimTree(0, 0);
}
#endif
