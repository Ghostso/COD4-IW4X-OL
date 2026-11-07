/* CoDOL per-entity model scale.
 *
 * C1's entityState carries a model scale at +0x54, which the client reads at
 * 0x441532 when it draws the entity (alpha0022/entity_codec.py). The retained
 * IW3 entityState has no such member, so the snapshot overlay
 * (src/codol/snapshot/codol_engine_state.c) used to publish 1.0 for every
 * entity. This table is the server's side of that field.
 *
 *   <entity> setModelScale(<scale>)
 *       draws the entity at <scale> times its size. 1.0 is normal size. The
 *       value is cleared when the entity is freed.
 *
 * Only drawing changes: bounds, hit locations and collision are untouched.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_script_model_scale.h"
#include "scr_vm_functions.h"
#include "server.h"
#include <string.h>

/* 0 means "never set", so a zero-initialised table is all normal size. */
static float s_modelScale[MAX_GENTITIES];

float CODOL_EntityModelScale(int num)
{
    if (num < 0 || num >= MAX_GENTITIES || s_modelScale[num] <= 0.0f) return 1.0f;
    return s_modelScale[num];
}

void CODOL_EntityModelScaleFreed(int num)
{
    if (num >= 0 && num < MAX_GENTITIES) s_modelScale[num] = 0.0f;
}

void CODOL_Scr_SetModelScale(scr_entref_t ref)
{
    float scale;
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity");
        return;
    }
    scale = Scr_GetFloat(0);
    if (!(scale >= 0.01f && scale <= 100.0f)) {
        Scr_ParamError(0, va("setModelScale: scale %g outside 0.01..100", scale));
        return;
    }
    s_modelScale[ref.entnum] = scale == 1.0f ? 0.0f : scale;
}
