#ifdef CODOL_SERVER
#include "codol_script_model_animation.h"
#include "codol_model_animation.h"
#include "codol_entitystate_ext.h"
#include "server.h"
#include "scr_vm.h"

#include "cscr_stringlist.h"

#include <stdint.h>
#include <string.h>

/* The willNeverChange marker this tree uses. codol_script_entity.c owns the
 * definition (C1 0x53c070 sets the same entity-only flag); it is repeated here
 * rather than published, because that file belongs to another owner. The
 * reference handler tests IW4's own flag bit 0x2000000 at gentity+8, which is
 * the same field, s.lerp.eFlags. */
#define CODOL_ENTITY_STATIC UINT32_C(0x80000000)

/* IW4's family has no variant argument, and C1's 0x800 bit only selects
 * 0x63bbe0 over 0x63c520 for reasons that were not established, so the plain
 * arm is used. See codol_model_animation.h. */
#define CODOL_SCRIPT_MODEL_ANIM_VARIANT 0

/* Receiver resolution, in the reference handler's order: a non-entity receiver
 * first, then the script-model requirement.
 *
 * IW4 (0x4d9a00) tests the entity's script class word against the four classes
 * script_brushmodel/script_model/script_origin/light, then requires
 * s.eType == ET_SCRIPTMOVER *and* the script_model class specifically. This
 * native gentity_t does carry classname; use it rather than inferring a script
 * class from collision contents. */
static gentity_t *script_model(scr_entref_t ref, const char *method)
{
    gentity_t *entity;
    if(ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity");
        return NULL;
    }
    entity = &g_entities[ref.entnum];
    if(entity->s.eType != ET_SCRIPTMOVER || entity->classname != scr_const.script_model) {
        Scr_Error(va("%s() valid only for script models", method));
        return NULL;
    }
    return entity;
}

void CODOL_Scr_PrecacheMpAnim(void)
{
    const char *name;
    int slot;
    if(!level.initializing) {
        Scr_Error("PrecacheMpAnim() must be called before any wait statements "
                  "in the gametype or level script");
        return;
    }
    name = Scr_GetString(0);
    if(!name || !*name) {
        Scr_Error("PrecacheMpAnim() requires an animation name");
        return;
    }
    slot = CODOL_RegisterMpAnimName(name);
    if(slot <= 0) {
        /* The reference reports the full bank as
         * "G_FindConfigstringIndex: overflow mp anim: <name>". */
        Scr_Error(va("PrecacheMpAnim: overflow mp anim: %s", name));
        return;
    }
    /* The reference precache registers a name and loads nothing, so this one
     * does not resolve a tree either: the animtree a play needs may not be
     * loaded yet, and the entity that will carry the animation - and with it
     * the tree the play resolves in - is not known here. */
    /* No script return value. */
}

/* A missing or unresolvable animation must never end a match. The reference
 * raises here, but every caller in this tree is an animated prop: IW4 and C1
 * both ship maps whose animation registrations name an xanim their own zone
 * does not carry, and the only correct answer is to leave the prop in its bind
 * pose. Report once per (model, animation) so the missing registration stays
 * visible. maps/mp/_animatedmodels.gsc reports the unregistered-model half. */
static void report_static_prop(const gentity_t *entity,const char *name,const char *why)
{
    static char reported[64][96]; static unsigned reported_count; unsigned i;
    const char *model = entity->model ? SL_ConvertToString(entity->model) : "(no model)";
    char key[96];
    Com_sprintf(key,sizeof(key),"%s/%s",model,name?name:"");
    for(i=0;i<reported_count;++i) if(!strcmp(reported[i],key)) return;
    if(reported_count<64){ Q_strncpyz(reported[reported_count],key,sizeof(reported[0])); ++reported_count; }
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL animated model: model '%s' cannot play animation '%s' (%s); prop left static (reported once)\n",
        model,name?name:"(none)",why);
}
void CODOL_ScrCmd_ScriptModelPlayAnim(scr_entref_t ref)
{
    gentity_t *entity = script_model(ref, "ScriptModelPlayAnim");
    const char *name;
    int slot;
    codol_model_anim_t captured;
    uint32_t entry, tree;
    if(!entity) return;
    /* Initialization-time play is allowed on a willNeverChange entity; after
     * that it is refused, which is the reference order (0x4d9a83..0x4d9a9e). */
    if(!level.initializing &&
       ((uint32_t)entity->s.lerp.eFlags & CODOL_ENTITY_STATIC)) {
        Scr_Error("Cannot change a 'willNeverChange' entity");
        return;
    }
    name = Scr_GetString(0);
    if(!name) return;
    slot = CODOL_FindMpAnimName(name);
    if(slot <= 0) {
        report_static_prop(entity,name,"it was never PrecacheMpAnim'd");
        return;
    }
    /* The store resolves the name inside the entity's animtree, or inside the
     * one declared tree that carries it. A refusal means the animation could
     * not be started - no declared animtree carries the name, or several do
     * and the entity does not say which - and is reported rather than stored,
     * because the client selects the animation by its index inside one
     * specific tree. */
    if(!CODOL_PrepareModelAnimation((unsigned)entity->s.number, (unsigned)slot,
                                level.time, CODOL_SCRIPT_MODEL_ANIM_VARIANT,&captured)) {
        if(!CODOL_ClientAnimTreeBindingCount()) {
            report_static_prop(entity,name,
                "no client animtree correspondence is declared");
            return;
        }
        report_static_prop(entity,name,
            "it is not in exactly one declared animtree");
        return;
    }
    if(!CODOL_ModelAnimationEncode(&captured,&entry,&tree) ||
       !CODOL_EntityStateModelAnimCaptured(&entity->s,entry,tree)) {
        report_static_prop(entity,name,"the animation snapshot capture failed");
        return;
    }
    CODOL_CommitModelAnimation((unsigned)entity->s.number,&captured);
    /* No script return value. */
}

void CODOL_ScrCmd_ScriptModelClearAnim(scr_entref_t ref)
{
    gentity_t *entity = script_model(ref, "ScriptModelClearAnim");
    if(!entity) return;
    /* The reference clear has no willNeverChange guard: stopping an animation
     * is allowed on an entity that may never change again. Clearing an entity
     * that carries none succeeds, as the reference's unconditional store of
     * (0, 0) does. */
    if(!CODOL_EntityStateModelAnimCaptured(&entity->s,0,0)) {
        Scr_Error("ScriptModelClearAnim: animation snapshot capture failed");
        return;
    }
    CODOL_ClearModelAnimation((unsigned)entity->s.number);
    /* No script return value. */
}

#endif /* CODOL_SERVER */
