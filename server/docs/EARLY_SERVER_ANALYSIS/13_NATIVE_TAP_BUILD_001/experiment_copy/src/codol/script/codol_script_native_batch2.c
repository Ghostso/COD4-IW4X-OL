/*
 * Missing GSC natives, batch 2.
 *
 * canspawn      - spawn-point validation used by the MP spawn logic.
 * stopfxontag   - the shutdown half of the tagged-effect pair whose start
 *                 half (playfxontag) is already bound in this tree.
 *
 * Selection: both names are called by the alpha MP script corpus, neither is
 * registered anywhere in src/ (fresh Scr_AddFunction/Scr_AddMethod snapshot in
 * obj/claude-workers/gsc-native-batch2-registered.txt, 735 names) and neither
 * has an implementation in the tree under any symbol name. The published
 * manifest is stale in both directions, so absence was established against
 * source, not against docs/CODOL_BUILTIN_INVENTORY.json.
 */
#ifdef CODOL_SERVER

#include "q_shared.h"
#include "bg.h"
#include "g_shared.h"
#include "server.h"
#include "scr_vm.h"
#include "cscr_stringlist.h"
#include "cm_public.h"
#include "codol_script_native_batch2.h"

#include <string.h>

/* Retained helpers that have no prototype in a shared header yet. The
 * signatures come from their retained assembly call sites, which is how the
 * other CoDOL script modules in this tree declare them too. */
void __cdecl G_AddEvent(gentity_t *ent, int event, int eventParm);
unsigned int __cdecl Scr_GetConstLowercaseString(unsigned int index);
/* _g_utils_mp.asm:128. Scr_PlayFXOnTag passes (name, start, max, create,
 * diagnosticLabel) in this order at _g_scr_main_mp.asm:4598..4606. */
int __cdecl G_FindConfigstringIndex(const char *name, int start, int max,
                                    int create, const char *diagnosticLabel);
int __cdecl SV_DObjGetBoneIndex(struct gentity_s *ent, unsigned int boneName);
void __cdecl SV_DObjDumpInfo(struct gentity_s *ent);

/*
 * canspawn( <origin> ) -> bool
 *
 * IW4 0x005f7290, decoded instruction by instruction:
 *
 *   005f7293  lea eax,[esp]      ; local vec3
 *   005f7299  call Scr_GetVector(0, &origin)
 *   005f729e  push 0x810011      ; content mask
 *   005f72a3  push 0x7ff         ; IW4's ENTITYNUM_NONE
 *   005f72a8  push 0x739b78      ; Bounds{ mid (0,0,35), halfSize (15,15,35) }
 *   005f72ad  push &origin       ; end
 *   005f72b4  push &origin       ; start - the volume is traced against itself
 *   005f72b9  push &trace
 *   005f72ba  call 0x0042ce50
 *   005f72c2  cmp byte [trace+0x28],0 ; trace_t.allsolid
 *   005f72c7  jne -> Scr_Add*(0) ; blocked
 *             fallthrough        -> Scr_Add*(1)
 *
 * Notes on the translation to this tree:
 *  - the reference takes no parameter count check and errors on nothing; per
 *    the parent review of the previous batch, reading only parameter 0 does
 *    not establish a strict one-argument contract, so no extra-parameter
 *    rejection is added here.
 *  - IW4 passes a Bounds (midpoint + half size). The equivalent absolute box
 *    is mins = mid - half = (-15,-15,0), maxs = mid + half = (15,15,70).
 *  - G_TraceCapsule in this fork is a plain box trace: sv_world.cpp:320 only
 *    builds IgnoreEntParams and forwards mins/maxs to SV_Trace, so it is the
 *    exact shape of the reference call and not a capsule approximation.
 *  - the pass-entity number is this engine's ENTITYNUM_NONE (2047 with GENTITYNUM_BITS 11, numerically IW4's
 *    0x7ff). Sentinels are named, never equated across forks by assumption; ENTITYNUM_NONE is what
 *    this tree's own G_TraceCapsule callers use (g_cmds.c:836, which also uses
 *    the same 0x810011 mask).
 *  - the reference returns through 0x0041d7d0 with a literal 1 or 0. Scr_AddInt
 *    publishes the same VAR_INTEGER 1/0 that GSC tests with if()/!.
 */
void CODOL_Scr_CanSpawn(void)
{
    /* IW4's Bounds at 0x00739b78, expanded to absolute box extents. */
    static const vec3_t canspawn_mins = { -15.0f, -15.0f, 0.0f };
    static const vec3_t canspawn_maxs = { 15.0f, 15.0f, 70.0f };
    trace_t trace;
    vec3_t origin;

    Scr_GetVector(0, origin);
    memset(&trace, 0, sizeof(trace));
    G_TraceCapsule(&trace, origin, canspawn_mins, canspawn_maxs, origin,
                   ENTITYNUM_NONE, 0x810011);
    Scr_AddInt(trace.allsolid ? 0 : 1);
}

/* stopfxontag(effect, entity, tag): C1 5440f0 requires exactly three
 * arguments and effect1..319; model/tag/bone validation follows. It publishes
 * a three-digit effect/tag compound in bank3971 and queues event90 to either
 * the player scripted queue or the entity queue (544436/544466).
 * Native registration uses an explicit marker for its wider representation;
 * the bridge still reads old two-digit compounds without guessing tag digits.
 * Appended native event numbering preserves all retained assembly constants.
 * Source-integrated only; no runtime parity is claimed.
 */
void CODOL_Scr_StopFxOnTag(void)
{
    gentity_t *ent;
    unsigned int tag;
    const char *tagName;
    int effectId;
    int bone;
    int configstring;

    if (Scr_GetNumParam() != 3)
    {
        /* Same message and same position as the retained twin. */
        Scr_Error("Incorrect number of parameters");
        return;
    }

    effectId = Scr_GetInt(0);
    if (effectId <= 0 || effectId >= 320)
    {
        Scr_ParamError(0, va("effect id %i is invalid", effectId));
        return;
    }

    ent = Scr_GetEntity(1);
    if (ent == NULL)
        return;
    if (ent->model == 0)
    {
        /* IW4 0x00718528: "cannot stop-fx-on-tag on entity with no model". */
        Scr_ParamError(1, "cannot stop-fx-on-tag on entity with no model");
        return;
    }

    tag = Scr_GetConstLowercaseString(2);
    tagName = SL_ConvertToString(tag);
    if (tagName == NULL)
        return;
    if (strchr(tagName, '\"') != NULL)
    {
        Scr_ParamError(2, "cannot use \" char");
        return;
    }

    bone = SV_DObjGetBoneIndex(ent, tag);
    if (bone < 0)
    {
        /* The retained twin dumps the DObj before reporting, so the tag list
         * of the offending model reaches the log the same way. */
        SV_DObjDumpInfo(ent);
        Scr_ParamError(2, va("tag %s does not exist on model %s", tagName,
                             SL_ConvertToString(G_ModelName(ent->model))));
        return;
    }

    /* CS 0x6a2 / 0x100 entries / create / no overflow error: the retained
     * Scr_PlayFXOnTag argument list at _g_scr_main_mp.asm:4598..4606. */
    configstring = CODOL_RegisterNativeTaggedEffect((unsigned)effectId,tagName);
    if (configstring <= 0)
    {
        Scr_ParamError(0, va("could not register effect %i on tag %s",
                             effectId, tagName));
        return;
    }

    G_AddEvent(ent, CODOL_EV_STOP_FX_ON_TAG, configstring);
}

#endif /* CODOL_SERVER */
