#include "g_shared.h"
#include "scr_vm.h"
#include "cscr_stringlist.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

gentity_t g_entities[MAX_GENTITIES];
extern int CODOL_NotifyMissileStationary(gentity_t *entity);

static unsigned events[2], event_count, argument_count;
static gentity_t *argument;
static int delete_missile, convert_missile, delete_target, reuse_target;

unsigned int SL_GetString(const char *name, int type)
{
    assert(type == 0);
    if(!strcmp(name,"stationary")) return 1;
    assert(!strcmp(name,"missile_stuck"));
    return 2;
}
void SL_RemoveRefToString(unsigned int name) { assert(name == 1 || name == 2); }
void Scr_AddEntity(gentity_t *entity) { assert(!argument_count++); argument = entity; }
void Scr_AddUndefined(void) { assert(!argument_count++); argument = NULL; }
void Scr_Notify(gentity_t *entity, unsigned short name, unsigned int count)
{
    assert(entity == &g_entities[3]);
    assert(event_count < 2 && name == event_count + 1);
    assert(count == (name == 2));
    if(name == 2) {
        assert(argument_count == 1);
        argument_count = 0;
    } else {
        assert(argument_count == 0);
        if(delete_missile) entity->r.inuse = 0;
        if(convert_missile) entity->s.eType = ET_GENERAL;
        if(delete_target) g_entities[5].r.inuse = 0;
        if(reuse_target) ++g_entities[5].useCount;
    }
    events[event_count++] = name;
}

static void reset(void)
{
    memset(g_entities,0,sizeof(g_entities));
    events[0] = events[1] = event_count = argument_count = 0;
    argument = NULL;
    delete_missile = convert_missile = delete_target = reuse_target = 0;
    g_entities[3].r.inuse = 1;
    g_entities[3].s.eType = ET_MISSILE;
    g_entities[3].useCount = 7;
    g_entities[5].r.inuse = 1;
    g_entities[5].useCount = 11;
}

int main(void)
{
    reset();
    g_entities[3].s.groundEntityNum = 5;
    assert(CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 2 && events[0] == 1 && events[1] == 2);
    assert(argument == &g_entities[5]);

    reset();
    g_entities[3].s.groundEntityNum = ENTITYNUM_WORLD;
    assert(CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 2 && argument == NULL);

    reset();
    g_entities[3].s.groundEntityNum = ENTITYNUM_NONE;
    assert(CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 2 && argument == NULL);

    reset();
    g_entities[3].s.groundEntityNum = 5;
    delete_target = 1;
    assert(CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 2 && argument == NULL);

    reset();
    g_entities[3].s.groundEntityNum = 5;
    reuse_target = 1;
    assert(CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 2 && argument == NULL);

    reset();
    g_entities[3].s.groundEntityNum = 5;
    delete_missile = 1;
    assert(!CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 1 && argument_count == 0);

    reset();
    g_entities[3].s.groundEntityNum = 5;
    convert_missile = 1;
    assert(!CODOL_NotifyMissileStationary(&g_entities[3]));
    assert(event_count == 1 && argument_count == 0);

    puts("PASS: missile_stuck follows stationary with a live impact entity and stops after receiver deletion");
    return 0;
}
