/* C1 PM_UpdateVariableZoom 0x418480 port: codol_variable_zoom.c.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_variable_zoom.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static int failures;
#define CHECK(cond) do { if(!(cond)) { ++failures; \
    fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__, #cond); } } while(0)

static const float vzoom[3] = {10.0f, 5.0f, 2.5f};   /* three levels */
static const float twozoom[3] = {10.0f, 5.0f, 0.0f}; /* two levels */
static const float fixed[3] = {10.0f, 0.0f, 0.0f};   /* ordinary scope */

int main(void)
{
    codol_variable_zoom_t z;
    int t;

    /* Ordinary fixed scope: never changes, never latches. */
    memset(&z, 0, sizeof z);
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, fixed, 1000, 4));
    CHECK(z.level == 0 && z.latch == 0 && z.time == 0);

    /* No overlay, or not raised: returns before touching state. */
    CHECK(!CODOL_VariableZoomStep(&z, 0, 1.0f, vzoom, 1000, 4));
    CHECK(!CODOL_VariableZoomStep(&z, 1, 0.0f, vzoom, 1000, 4));
    CHECK(!CODOL_VariableZoomStep(&z, 1, NAN, vzoom, 1000, 4));
    CHECK(z.level == 0 && z.latch == 0 && z.time == 0);

    /* Press on a raised variable scope: level 1, latch, one event. */
    CHECK(CODOL_VariableZoomStep(&z, 1, 0.5f, vzoom, 1000, 4));
    CHECK(z.level == 1 && z.latch == 1 && z.time == 1000);
    /* Holding the key does not step again. */
    for(t = 1016; t < 1500; t += 16) CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, t, 4));
    CHECK(z.level == 1 && z.latch == 1 && z.time == 1000);
    /* Release: latch drops once 40 ms have passed since the last change. */
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 1500, 0));
    CHECK(z.latch == 0 && z.time == 1500);
    /* A press within 40 ms of that is debounced ... */
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 1530, 4));
    CHECK(z.level == 1 && z.latch == 0);
    /* ... and taken on the first command past it. */
    CHECK(CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 1541, 4));
    CHECK(z.level == 2 && z.latch == 1 && z.time == 1541);
    /* Cycle wraps 2 -> 0 on a three-level scope. */
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 1600, 0));
    CHECK(CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 1700, 4));
    CHECK(z.level == 0);

    /* Two-level scope: fov[2] == 0 sends 1 -> 0. */
    memset(&z, 0, sizeof z);
    CHECK(CODOL_VariableZoomStep(&z, 1, 1.0f, twozoom, 100, 4));
    CHECK(z.level == 1);
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, twozoom, 200, 0));
    CHECK(CODOL_VariableZoomStep(&z, 1, 1.0f, twozoom, 300, 4));
    CHECK(z.level == 0);

    /* Level left at 1 on a weapon whose next FOV is zero: still steps back to
     * 0 (C1 only returns early when level and next are both 0). */
    memset(&z, 0, sizeof z); z.level = 1;
    CHECK(CODOL_VariableZoomStep(&z, 1, 1.0f, fixed, 500, 4));
    CHECK(z.level == 0 && z.latch == 1);

    /* Idle commands refresh the time every 40 ms (0x418568). */
    memset(&z, 0, sizeof z);
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 41, 0));
    CHECK(z.time == 41);
    CHECK(!CODOL_VariableZoomStep(&z, 1, 1.0f, vzoom, 60, 0));
    CHECK(z.time == 41);

    /* Per-client table and wire view. */
    {
        uint32_t level = 9, latch = 9;
        codol_variable_zoom_t *c = CODOL_VariableZoomClient(3);
        CHECK(c != NULL);
        CHECK(CODOL_VariableZoomClient(64) == NULL);
        c->level = 2; c->latch = 1;
        CODOL_VariableZoomWire(3, &level, &latch);
        CHECK(level == 2 && latch == 1);
        CODOL_VariableZoomWire(-1, &level, &latch);
        CHECK(level == 0 && latch == 0);
        CODOL_VariableZoomResetClient(3);
        CODOL_VariableZoomWire(3, &level, &latch);
        CHECK(level == 0 && latch == 0);
    }

    if(failures) { fprintf(stderr, "test_codol_variable_zoom: %d failure(s)\n", failures); return 1; }
    puts("test_codol_variable_zoom: ok");
    return 0;
}
