/* test_collision.c -- ground and clip-box sweep tests for the firingrange collision set. */
#include "codol_collision.h"
#include <stdio.h>
#include <math.h>

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(void)
{
    const float mins[3] = {-15.0f, -15.0f, 0.0f};
    const float maxs[3] = { 15.0f,  15.0f, 70.0f};
    codol_collision_trace_t tr;

    /* 1. fall onto ground from spawn height */
    {
        float start[3] = {48.0f, -572.0f, -100.0f};
        float end[3]   = {48.0f, -572.0f, -140.0f};
        codol_collision_box_trace(&tr, start, end, mins, maxs, CODOL_CONTENTS_SOLID);
        CHECK(tr.fraction > 0.0f && tr.fraction < 1.0f, "ground hit should stop the fall");
        CHECK(fabsf(tr.end_pos[2] - codol_ground_z) < 0.01f, "should land exactly on ground plane");
        CHECK(tr.normal[2] > 0.9f, "ground normal should point up");
    }

    /* 2. unobstructed horizontal move near spawn */
    {
        float start[3] = {48.0f, -572.0f, -116.0f};
        float end[3]   = {58.0f, -572.0f, -116.0f};
        codol_collision_box_trace(&tr, start, end, mins, maxs,
                                  CODOL_CONTENTS_PLAYERCLIP | CODOL_CONTENTS_SOLID);
        CHECK(tr.fraction == 1.0f, "open ground move must not be blocked");
    }

    /* 3. blocked by the clip box at (-75,-434) */
    {
        float start[3] = {-75.0f, -500.0f, -116.0f};
        float end[3]   = {-75.0f, -380.0f, -116.0f};
        codol_collision_box_trace(&tr, start, end, mins, maxs, CODOL_CONTENTS_PLAYERCLIP);
        CHECK(tr.fraction < 1.0f, "clip box must block movement");
        CHECK(tr.end_pos[1] < -434.0f - 32.0f + 16.0f + 0.5f, "must stop before the box");
    }

    /* 4. point-solid checks */
    CHECK(codol_collision_point_solid((float[]){0,0,-200}, CODOL_CONTENTS_SOLID), "below ground is solid");
    CHECK(!codol_collision_point_solid((float[]){48,-572,-116}, CODOL_CONTENTS_SOLID), "spawn point is free");
    CHECK(codol_collision_point_solid((float[]){-75,-434,-64}, CODOL_CONTENTS_PLAYERCLIP), "clip origin is solid");

    /* 5. exact ClipMap bounds, not the old 64x64x64 approximation. */
    CHECK(codol_collision_point_solid((float[]){-824,-96,-57}, CODOL_CONTENTS_PLAYERCLIP),
          "brush *71 centre is solid");
    CHECK(!codol_collision_point_solid((float[]){-840,-96,-57}, CODOL_CONTENTS_PLAYERCLIP),
          "brush *71 x half-extent is 8, not 32");
    CHECK(!codol_collision_point_solid((float[]){-75,-460,-64}, CODOL_CONTENTS_PLAYERCLIP),
          "brush *79 y half-extent is 4, not 32");

    /* 6. box count sanity */
    CHECK(codol_static_box_count == 29, "29 script_brushmodel clip volumes");

    if (failures == 0) printf("test_collision: all checks passed\n");
    return failures ? 1 : 0;
}
