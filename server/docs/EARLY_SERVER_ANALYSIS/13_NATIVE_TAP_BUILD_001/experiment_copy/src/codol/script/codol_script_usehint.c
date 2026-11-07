#ifdef CODOL_SERVER
#include "codol_script_usehint.h"
#include "scr_vm_functions.h"
#include <string.h>

typedef struct
{
    qboolean active;
    int hintStringIndex;
} codol_force_use_hint_t;
static codol_force_use_hint_t forced_hints[MAX_CLIENTS];

/* Retained _g_scr_main_mp.asm: cdecl(out index, text), 32-slot pool. */
extern qboolean G_GetHintStringIndex(int *outIndex, const char *text);

/* IW5 equipment sets hints on script_origin and script_model receivers,
 * before makeUsable. Use the native hint pool and cursor-hint field without
 * the retained trigger_use-only classname restriction. */
void CODOL_Scr_SetHintString(scr_entref_t ref)
{
    gentity_t *entity;
    char text[1024];
    int index;
    if(ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return;
    }
    entity = &g_entities[ref.entnum];
    if(!entity->r.inuse) {
        Scr_ObjectError("Entity is not in use"); return;
    }
    if(!Scr_GetNumParam()) {
        Scr_Error("setHintString requires a hint message"); return;
    }
    if(Scr_GetType(0) == 2 && !Q_stricmp(Scr_GetString(0), "")) {
        entity->s.un1.hintStringIndex = 255;
        return;
    }
    Scr_ConstructMessageString(0, (int)Scr_GetNumParam()-1,
                              "Hint String", text, sizeof(text));
    if(!G_GetHintStringIndex(&index, text)) {
        Scr_Error("Too many hint strings (maximum 32)"); return;
    }
    entity->s.un1.hintStringIndex = index;
}

static int hint_client_slot(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_CLIENTS) {
        Scr_ObjectError("Not a player"); return -1;
    }
    if(!g_entities[ref.entnum].client) {
        Scr_ObjectError("Not a player"); return -1;
    }
    return ref.entnum;
}

/* IW4 5f6110 -> 5f6000 builds all message arguments before interning.
 * The receiver's entity slot remains stable while ps.clientNum follows
 * another player during spectating. */
void CODOL_Scr_ForceUseHintOn(scr_entref_t ref)
{
    int slot=hint_client_slot(ref),index;
    char text[1024];
    if(slot<0)return;
    Scr_ConstructMessageString(0,(int)Scr_GetNumParam()-1,"Hint String",text,sizeof(text));
    if(!G_GetHintStringIndex(&index,text)) {
        Scr_Error("Too many hint strings (maximum 32)"); return;
    }
    forced_hints[slot].active=qtrue;
    forced_hints[slot].hintStringIndex=index;
}

/* IW4 5f01b0 clears the override without changing its stored string. */
void CODOL_Scr_ForceUseHintOff(scr_entref_t ref)
{
    int slot=hint_client_slot(ref);
    if(slot>=0)forced_hints[slot].active=qfalse;
}

/* IW4 49437d: generic-use hint, interned string, and no target entity.
 * Called after retained use restrictions and before the ordinary search. */
qboolean CODOL_ForceUseHint_Apply(struct gentity_s *entity)
{
    int slot;
    if(!entity || !entity->client)return qfalse;
    slot=entity->s.number;
    if(slot<0 || slot>=MAX_CLIENTS || !forced_hints[slot].active)return qfalse;
    entity->client->ps.cursorHint=1;
    entity->client->ps.cursorHintString=forced_hints[slot].hintStringIndex;
    entity->client->ps.cursorHintEntIndex=ENTITYNUM_NONE;
    return qtrue;
}

void CODOL_ForceUseHint_ResetClient(int slot)
{
    if(slot>=0 && slot<MAX_CLIENTS)memset(&forced_hints[slot],0,sizeof(forced_hints[slot]));
}
void CODOL_ForceUseHint_ResetAll(void)
{
    memset(forced_hints,0,sizeof(forced_hints));
}
#endif
