/* Compass objectives at C1's 32 slots.
 *
 * C1's MSG_ReadDeltaPlayerstate reads a hard-coded 32 objective slots of
 * stride 0x24 (0x5a1f9c / 0x5a1fd6; codol_player_arrays.h), and the IW4
 * scripts it runs allocate ids up to 31 (_gameobjects.gsc getNextObjID caps
 * at 31; every useObject/carryObject, airdrop crate and tank takes ids). The
 * retained IW3 builtins (_g_scr_main_mp.asm Scr_Objective_*) rejected any
 * index above 15 with a script error, which killed the calling thread: an
 * emergency airdrop in dom (6 flag ids + 8 crate ids) pushed the next crate
 * past 15 and left it half set up with no compass icon.
 *
 * level.objectives[16] (level+0x24, stride 0x1c) cannot grow in place, and
 * G_RunFrame copies exactly those 16 into ps->objective with the per-client
 * team filter. Slots 0..15 therefore stay in level.objectives, unchanged for
 * the retained copy; slots 16..31 live here and are filtered by the same rule
 * at snapshot time (CODOL_FillHighObjectives). The builtins below are the
 * retained ones re-implemented over both halves with IW3's exact semantics
 * (state names, broadcast flag handling, integral positions, icon checks).
 */
#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "g_shared.h"
#include "cscr_stringlist.h"
#include "codol_script_objectives.h"
#include <string.h>

int G_MaterialIndex(const char *name);

static objective_t codol_high_objectives[CODOL_OBJECTIVE_TOTAL - CODOL_OBJECTIVE_RETAINED];

void CODOL_ResetObjectives(void)
{
    unsigned i;
    memset(codol_high_objectives, 0, sizeof(codol_high_objectives));
    for (i = 0; i < CODOL_OBJECTIVE_TOTAL - CODOL_OBJECTIVE_RETAINED; ++i)
        codol_high_objectives[i].entNum = CODOL_OBJECTIVE_NO_ENTITY;
}

static objective_t *objective_slot(unsigned index)
{
    return index < CODOL_OBJECTIVE_RETAINED ? &level.objectives[index]
                                            : &codol_high_objectives[index - CODOL_OBJECTIVE_RETAINED];
}

/* Reads parameter 0; a script error for an index C1 cannot carry. */
static objective_t *objective_argument(unsigned param)
{
    int index = Scr_GetInt(param);
    if ((unsigned)index >= CODOL_OBJECTIVE_TOTAL) {
        Scr_ParamError(param, va("index %i is an illegal objective index. Valid indexes are 0 to %i\n",
                                 index, CODOL_OBJECTIVE_TOTAL - 1));
        return NULL;
    }
    return objective_slot((unsigned)index);
}

/* An objective bound to an entity made it broadcast (svFlags 0x10); drop
 * that when the binding goes away, as every retained builtin does. */
static void release_entity(objective_t *objective)
{
    int entnum = objective->entNum;
    if (entnum != CODOL_OBJECTIVE_NO_ENTITY) {
        if (entnum >= 0 && entnum < MAX_GENTITIES && g_entities[entnum].r.inuse)
            g_entities[entnum].r.svFlags &= ~0x10;
        objective->entNum = CODOL_OBJECTIVE_NO_ENTITY;
    }
}

/* "empty" 0, "active" 1, "invisible" 2, "current" 4; -1 after the error. */
static int objective_state(unsigned param, int use_name)
{
    unsigned short name = (unsigned short)Scr_GetConstString(param);
    if (name == scr_const.empty) return OBJST_EMPTY;
    if (name == scr_const.invisible) return OBJST_INVISIBLE;
    if (name == scr_const.current) return OBJST_CURRENT;
    if (name == scr_const.active) return OBJST_ACTIVE;
    Scr_ParamError(param, va("Illegal objective state \"%s\". Valid states are \"empty\", \"invisible\", \"current\", \"active\"\n",
                             use_name ? Scr_GetString(param) : SL_ConvertToString(name)));
    return OBJST_EMPTY;
}

static void objective_position(objective_t *objective, unsigned param)
{
    unsigned axis;
    Scr_GetVector(param, objective->origin);
    for (axis = 0; axis < 3; ++axis) objective->origin[axis] = (float)(int)objective->origin[axis];
}

static void objective_icon(objective_t *objective, unsigned param)
{
    const char *name = Scr_GetString(param);
    unsigned i;
    for (i = 0; name[i]; ++i)
        if ((unsigned char)(name[i] - 0x20) > 0x5e)
            Scr_ParamError(param, va("Illegal character '%c'(ascii %i) in objective icon name: %s\n",
                                     name[i], (unsigned char)name[i], name));
    if (i > 0x3f)
        Scr_ParamError(param, va("Objective icon name is too long (> %i): %s\n", 0x3f, name));
    objective->icon = G_MaterialIndex(name);
}

void CODOL_Scr_Objective_Add(void)
{
    int count = Scr_GetNumParam();
    objective_t *objective;
    if (count < 2)
        Scr_Error("objective_add needs at least the first two parameters out of its parameter list of: index state [string] [position]\n");
    objective = objective_argument(0);
    if (!objective) return;
    release_entity(objective);
    objective->state = objective_state(1, 0);
    if (count > 2) {
        objective_position(objective, 2);
        objective->entNum = CODOL_OBJECTIVE_NO_ENTITY;
        if (count > 3) objective_icon(objective, 3);
    }
    objective->teamNum = TEAM_FREE;
}

void CODOL_Scr_Objective_Delete(void)
{
    objective_t *objective = objective_argument(0);
    if (!objective) return;
    release_entity(objective);
    memset(objective, 0, sizeof(*objective));
    objective->entNum = CODOL_OBJECTIVE_NO_ENTITY;
}

void CODOL_Scr_Objective_State(void)
{
    objective_t *objective = objective_argument(0);
    if (!objective) return;
    objective->state = objective_state(1, 1);
    if (objective->state == OBJST_EMPTY || objective->state == OBJST_INVISIBLE)
        release_entity(objective);
}

void CODOL_Scr_Objective_Icon(void)
{
    objective_t *objective = objective_argument(0);
    if (objective) objective_icon(objective, 1);
}

void CODOL_Scr_Objective_Position(void)
{
    objective_t *objective = objective_argument(0);
    if (!objective) return;
    release_entity(objective);
    objective_position(objective, 1);
}

void CODOL_Scr_Objective_OnEntity(void)
{
    objective_t *objective = objective_argument(0);
    gentity_t *entity;
    if (!objective) return;
    release_entity(objective);
    entity = Scr_GetEntity(1);
    entity->r.svFlags |= 0x10;
    objective->entNum = entity->s.number;
}

void CODOL_Scr_Objective_Current(void)
{
    unsigned char current[CODOL_OBJECTIVE_TOTAL];
    int count = Scr_GetNumParam(), i;
    memset(current, 0, sizeof(current));
    for (i = 0; i < count; ++i) {
        int index = Scr_GetInt(i);
        if ((unsigned)index >= CODOL_OBJECTIVE_TOTAL) {
            Scr_ParamError(i, va("index %i is an illegal objective index. Valid indexes are 0 to %i\n",
                                 index, CODOL_OBJECTIVE_TOTAL - 1));
            continue;
        }
        current[index] = 1;
    }
    for (i = 0; i < CODOL_OBJECTIVE_TOTAL; ++i) {
        objective_t *objective = objective_slot((unsigned)i);
        if (current[i]) objective->state = OBJST_CURRENT;
        else if (objective->state == OBJST_CURRENT) objective->state = OBJST_ACTIVE;
    }
}

void CODOL_Scr_Objective_Team(void)
{
    objective_t *objective = objective_argument(0);
    unsigned short team;
    if (!objective) return;
    team = (unsigned short)Scr_GetConstString(1);
    if (team == scr_const.allies) objective->teamNum = TEAM_BLUE; /* allies 2 */
    else if (team == scr_const.axis) objective->teamNum = TEAM_RED; /* axis 1 */
    else if (team == scr_const.none) objective->teamNum = TEAM_FREE;
    else Scr_ParamError(1, va("Illegal team string '%s'. Must be allies, axis, or none.", SL_ConvertToString(team)));
}

/* Used objective slots and the highest id in use, for codol_limits. */
int CODOL_ObjectivesInUse(unsigned *highest)
{
    unsigned i;
    int used = 0;
    if (highest) *highest = 0;
    for (i = 0; i < CODOL_OBJECTIVE_TOTAL; ++i)
        if (objective_slot(i)->state != OBJST_EMPTY) {
            ++used;
            if (highest) *highest = i;
        }
    return used;
}

/* The G_RunFrame rule (_g_main_mp.asm G_RunFrame_280..290) for the slots it
 * does not copy: a used objective reaches a client whose team matches, or
 * every client when it has no team; anything else arrives with state 0. The
 * team is the one of the client the state belongs to (ps->clientNum), which
 * for a spectator following someone is the followed player's. */
void CODOL_FillHighObjectives(int client, objective_t *out)
{
    int team = -1;
    unsigned i;
    if (client >= 0 && client < MAX_CLIENTS && g_entities[client].client)
        team = g_entities[client].client->sess.cs.team;
    for (i = 0; i < CODOL_OBJECTIVE_TOTAL - CODOL_OBJECTIVE_RETAINED; ++i) {
        const objective_t *objective = &codol_high_objectives[i];
        out[i] = *objective;
        if (objective->state != OBJST_EMPTY && objective->teamNum && objective->teamNum != team)
            out[i].state = OBJST_EMPTY;
    }
}
#endif
