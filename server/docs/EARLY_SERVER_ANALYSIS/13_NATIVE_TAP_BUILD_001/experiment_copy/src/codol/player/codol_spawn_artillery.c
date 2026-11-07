/* Original T5 _spawning::create_artillery_influencers and OpenBLOPS
 * SpawnSystem_ComputeCylinderInfluence/InfluenceWeight. No cross-engine
 * structure offsets. These are static, all-team artillery cylinders only. */
#ifdef CODOL_SERVER
#include "codol_spawn_artillery.h"
#include "scr_vm.h"
#include <math.h>
#include <limits.h>
#include <string.h>

#define CODOL_ARTILLERY_INFLUENCERS 328
typedef struct {
    unsigned id;
    float center[3], radius, score;
    int curve;
} codol_artillery_influencer_t;
static codol_artillery_influencer_t influencers[CODOL_ARTILLERY_INFLUENCERS];
static unsigned next_id = 1;
static unsigned active_count;

void CODOL_ResetArtilleryInfluencers(void)
{
    memset(influencers, 0, sizeof(influencers));
    active_count = 0;
    /* IDs survive resets so a prior level's handle cannot remove a new one. */
}

void CODOL_Scr_AddArtilleryInfluencer(void)
{
    float origin[3], radius, score;
    unsigned i;
    int curve;
    if (Scr_GetNumParam() != 4) {
        Scr_Error("codol_addArtilleryInfluencer(target, radius, score, curve)");
        return;
    }
    Scr_GetVector(0, origin);
    radius = Scr_GetFloat(1);
    score = Scr_GetFloat(2);
    curve = Scr_GetInt(3);
    if (!isfinite(origin[0]) || !isfinite(origin[1]) || !isfinite(origin[2])) {
        Scr_ParamError(0, "artillery target must be finite"); return;
    }
    if (!isfinite(radius) || radius <= 0.0f || !isfinite(radius * radius)) {
        Scr_ParamError(1, "artillery radius must be positive and finite"); return;
    }
    if (!isfinite(score)) { Scr_ParamError(2, "artillery score must be finite"); return; }
    if ((unsigned)curve > 4u) { Scr_ParamError(3, "artillery curve must be 0..4"); return; }
    for (i = 0; i < CODOL_ARTILLERY_INFLUENCERS && influencers[i].id; ++i) {}
    if (i == CODOL_ARTILLERY_INFLUENCERS || next_id > INT_MAX) {
        Scr_Error("artillery spawn influencer storage exhausted"); return;
    }
    /* T5 cylinder base targetZ-2000, height5000 => midpoint targetZ+500. */
    influencers[i].center[0] = origin[0];
    influencers[i].center[1] = origin[1];
    influencers[i].center[2] = origin[2] + 500.0f;
    influencers[i].radius = radius;
    influencers[i].score = score;
    influencers[i].curve = curve;
    influencers[i].id = next_id++;
    ++active_count;
    Scr_AddInt(influencers[i].id);
}

void CODOL_Scr_RemoveArtilleryInfluencer(void)
{
    unsigned i, id;
    if (Scr_GetNumParam() != 1) {
        Scr_Error("codol_removeArtilleryInfluencer(id)"); return;
    }
    id = (unsigned)Scr_GetInt(0);
    for (i = 0; id && i < CODOL_ARTILLERY_INFLUENCERS; ++i) {
        if (influencers[i].id == id) {
            memset(&influencers[i], 0, sizeof(influencers[i]));
            --active_count;
            return;
        }
    }
    Scr_Error("Trying to remove artillery influencer that does not exist");
}

void CODOL_Scr_ArtillerySpawnWeight(void)
{
    float origin[3], total = 0.0f;
    unsigned i, remaining;
    if (Scr_GetNumParam() != 1) {
        Scr_Error("codol_artillerySpawnWeight(origin)"); return;
    }
    Scr_GetVector(0, origin);
    if (!isfinite(origin[0]) || !isfinite(origin[1]) || !isfinite(origin[2])) {
        Scr_ParamError(0, "spawn origin must be finite"); return;
    }
    remaining = active_count;
    for (i = 0; remaining && i < CODOL_ARTILLERY_INFLUENCERS; ++i) {
        const codol_artillery_influencer_t *influence = &influencers[i];
        float dx, dy, distance_sq, radial, weight;
        if (!influence->id) continue;
        --remaining;
        if (fabsf(origin[2] - influence->center[2]) >= 2500.0f) continue;
        dx = origin[0] - influence->center[0];
        dy = origin[1] - influence->center[1];
        distance_sq = dx * dx + dy * dy;
        if (distance_sq >= influence->radius * influence->radius) continue;
        radial = sqrtf(distance_sq / (influence->radius * influence->radius));
        switch (influence->curve) {
        case 1: weight = 1.0f - radial; break;
        case 2: weight = (1.0f - radial) * (1.0f - radial); break;
        case 3: weight = radial; break;
        case 4: weight = 2.0f * radial - 1.0f; break;
        default: weight = 1.0f; break;
        }
        total += weight * influence->score;
    }
    if (!isfinite(total)) { Scr_Error("artillery spawn influence overflow"); return; }
    Scr_AddFloat(total);
}
#endif
