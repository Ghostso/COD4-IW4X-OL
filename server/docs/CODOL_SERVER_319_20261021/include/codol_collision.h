/* codol_collision.h -- static world collision for coop_train_mp_firingrange.
 *
 * Data provenance (all offsets re-derived from coop_train_zone.bin):
 *   - ground height  : info_player_start_so origin z = -116 (map's only design spawn)
 *   - clip volumes   : 29 script_brushmodel entities, origins from the entity string
 *   - trigger hulls  : 32 TriggerHull records parsed from MapEnts (Bounds + contents + slab refs)
 *
 * The 29 script_brushmodel volumes are exact AABBs from the 3.19 ClipMap
 * (tools/export_clipmap_zone.py); the eight plane-backed world brushes are
 * retained in the JSON evidence but are not used by this movement trace yet.
 */
#ifndef CODOL_COLLISION_H
#define CODOL_COLLISION_H

#include <stdbool.h>

#define CODOL_CONTENTS_SOLID      0x00000001
#define CODOL_CONTENTS_PLAYERCLIP 0x00010000
#define CODOL_CONTENTS_MASK_ALL   0xFFFFFFFF

typedef struct {
    float mins[3];
    float maxs[3];
    int   contents;
    int   entity_num;   /* -1 for static world geometry */
} codol_collision_box_t;

typedef struct {
    float fraction;      /* 0..1 along start->end */
    float normal[3];     /* surface normal at impact */
    float end_pos[3];    /* start + fraction * (end - start) */
    bool  startsolid;
    bool  allsolid;
    int   entity_num;   /* dynamic hit entity, or -1 for world geometry */
} codol_collision_trace_t;

extern const float codol_ground_z;
extern const codol_collision_box_t codol_static_boxes[];
extern const int codol_static_box_count;

/* Sweep an AABB (mins/maxs relative to origin) from start to end.
 * Returns fraction 1.0 when unobstructed. */
void codol_collision_box_trace(codol_collision_trace_t *trace,
                               const float start[3], const float end[3],
                               const float mins[3], const float maxs[3],
                               int content_mask);

/* True when the point lies inside any solid volume or below ground. */
bool codol_collision_point_solid(const float p[3], int content_mask);
void codol_collision_box_trace_ex(codol_collision_trace_t *trace,
                                  const float start[3], const float end[3],
                                  const float mins[3], const float maxs[3],
                                  int content_mask,
                                  int skip_entity,
                                  const codol_collision_box_t *dynamic_boxes,
                                  int dynamic_count);

#endif /* CODOL_COLLISION_H */

