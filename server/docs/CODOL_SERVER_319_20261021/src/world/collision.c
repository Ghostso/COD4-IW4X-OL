/* codol_collision.c -- AABB sweep against the verified 3.19 script_brushmodel AABBs.
 *
 * The box set is generated from coop_train_zone.bin by
 * tools/export_clipmap_zone.py. The trace itself follows the axis-aligned
 * slab semantics used by the engine for an AABB sweep.
 */
#include "codol_collision.h"
#include <math.h>
#include <string.h>

const float codol_ground_z = -116.0f;

/* Exact script_brushmodel AABBs recovered from the 3.19 ClipMap.
 * The compact clipmap has 30 cbrush_t records; entities *71..*99 map to
 * records 1..29 and are translated by each entity's map origin.
 *
 * ★ 对照实验开关(2026-10-25): 定义 CODOL_PLACEHOLDER_WORLD 时退回 Phase 7
 *   之前那个"placeholder 世界"形态(单个占位盒), 用来验证客户端进不了图
 *   是不是 10-23 的 ClipMap 改动造成的。 */
#ifdef CODOL_PLACEHOLDER_WORLD
const codol_collision_box_t codol_static_boxes[] = {
    { { -4096.0f, -4096.0f, -128.0f }, { 4096.0f, 4096.0f, -124.0f }, 0x00000001, -1 }
};
#else
const codol_collision_box_t codol_static_boxes[] = {
#include "codol_clipmap_coop_train.inc"
};
#endif
const int codol_static_box_count = (int)(sizeof(codol_static_boxes) / sizeof(codol_static_boxes[0]));

/* Sweep one axis-aligned box against one expanded AABB.
 * Returns fraction (0..1) or 1.0 when no hit; writes normal. */
static float sweep_box_vs_aabb(const float start[3], const float delta[3],
                               const float emins[3], const float emaxs[3],
                               float out_normal[3])
{
    float t_enter = 0.0f, t_exit = 1.0f;
    int   enter_axis = -1, enter_sign = 0;
    int i;

    for (i = 0; i < 3; i++) {
        if (fabsf(delta[i]) < 1e-8f) {
            if (start[i] < emins[i] || start[i] > emaxs[i]) return 1.0f;
            continue;
        }
        float inv = 1.0f / delta[i];
        float t1 = (emins[i] - start[i]) * inv;
        float t2 = (emaxs[i] - start[i]) * inv;
        float sign = -1.0f;
        if (t1 > t2) { float tmp = t1; t1 = t2; t2 = tmp; sign = 1.0f; }
        if (t1 > t_enter) { t_enter = t1; enter_axis = i; enter_sign = (int)sign; }
        if (t2 < t_exit)  { t_exit = t2; }
        if (t_enter > t_exit) return 1.0f;
    }
    if (t_enter < 0.0f || t_enter > 1.0f) return 1.0f;
    if (enter_axis >= 0) {
        out_normal[0] = out_normal[1] = out_normal[2] = 0.0f;
        out_normal[enter_axis] = (float)enter_sign;
    }
    return t_enter;
}

void codol_collision_box_trace(codol_collision_trace_t *trace,
                               const float start[3], const float end[3],
                               const float mins[3], const float maxs[3],
                               int content_mask)
{
    float delta[3], best = 1.0f, best_normal[3] = {0.0f, 0.0f, 0.0f};
    int i, b;

    memset(trace, 0, sizeof(*trace));
    trace->fraction = 1.0f;
    trace->normal[1] = 1.0f;
    trace->entity_num = -1;
    for (i = 0; i < 3; i++) delta[i] = end[i] - start[i];

    for (b = 0; b < codol_static_box_count; b++) {
        const codol_collision_box_t *box = &codol_static_boxes[b];
        float emins[3], emaxs[3], n[3] = {0.0f, 0.0f, 0.0f}, f;
        if (!(box->contents & content_mask)) continue;
        for (i = 0; i < 3; i++) {
            emins[i] = box->mins[i] - maxs[i];
            emaxs[i] = box->maxs[i] - mins[i];
        }
        f = sweep_box_vs_aabb(start, delta, emins, emaxs, n);
        if (f < best) { best = f; best_normal[0] = n[0]; best_normal[1] = n[1]; best_normal[2] = n[2]; }
    }

    /* ground plane: solid at/below codol_ground_z.
     * NOTE: the spawn point sits exactly on the plane, so the test must be
     * inclusive (>=). Otherwise a player standing on the floor falls through
     * on the very first frame and never comes back. */
    if ((content_mask & CODOL_CONTENTS_SOLID) && delta[2] < 0.0f) {
        float floor = codol_ground_z - mins[2];
        if (end[2] <= floor) {
            float f;
            if (start[2] <= floor) {
                f = 0.0f;                    /* already touching/inside */
            } else {
                f = (start[2] - floor) / (start[2] - end[2]);
            }
            if (f < best) { best = f; best_normal[0] = best_normal[1] = 0.0f; best_normal[2] = 1.0f; }
        }
    }

    trace->fraction = best;
    for (i = 0; i < 3; i++) {
        trace->normal[i] = best_normal[i];
        trace->end_pos[i] = start[i] + delta[i] * best;
    }
    trace->startsolid = (best == 0.0f);
    trace->allsolid = false;
}

bool codol_collision_point_solid(const float p[3], int content_mask)
{
    int b;
    if ((content_mask & CODOL_CONTENTS_SOLID) && p[2] < codol_ground_z) return true;
    for (b = 0; b < codol_static_box_count; b++) {
        const codol_collision_box_t *box = &codol_static_boxes[b];
        if (!(box->contents & content_mask)) continue;
        if (p[0] >= box->mins[0] && p[0] <= box->maxs[0] &&
            p[1] >= box->mins[1] && p[1] <= box->maxs[1] &&
            p[2] >= box->mins[2] && p[2] <= box->maxs[2]) return true;
    }
    return false;
}

void codol_collision_box_trace_ex(codol_collision_trace_t *trace,
                                  const float start[3], const float end[3],
                                  const float mins[3], const float maxs[3],
                                  int content_mask,
                                  int skip_entity,
                                  const codol_collision_box_t *dynamic_boxes,
                                  int dynamic_count)
{
    float delta[3];
    int i;
    (void)skip_entity;
    if (!trace || !start || !end || !mins || !maxs) return;
    codol_collision_box_trace(trace, start, end, mins, maxs, content_mask);
    if (!dynamic_boxes || dynamic_count <= 0) return;
    for (i = 0; i < 3; i++) delta[i] = end[i] - start[i];
    for (i = 0; i < dynamic_count; ++i) {
        const codol_collision_box_t *box = &dynamic_boxes[i];
        float n[3] = {0.0f, 0.0f, 0.0f}, f;
        if (!(box->contents & content_mask)) continue;
        f = sweep_box_vs_aabb(start, delta, box->mins, box->maxs, n);
        if (f < trace->fraction) {
            trace->fraction = f;
            trace->normal[0] = n[0];
            trace->normal[1] = n[1];
            trace->normal[2] = n[2];
            trace->entity_num = box->entity_num;
        }
    }
    for (i = 0; i < 3; ++i)
        trace->end_pos[i] = start[i] + delta[i] * trace->fraction;
    trace->startsolid = trace->fraction == 0.0f;
}
