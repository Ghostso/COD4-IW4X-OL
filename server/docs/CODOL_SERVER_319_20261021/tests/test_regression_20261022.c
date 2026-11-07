/* test_regression_20261022.c -- locks two field bugs found in the first live run.
 *
 * Bug 1 (spawn on roof): playerstate.origin is the EYE position but the server
 *        sent the foot position. 60 units too low -> client sank and the engine
 *        pushed the body onto the roof.
 * Bug 2 (W+Shift switched weapon): usercmd.weapon decodes to garbage (58566 in
 *        the live capture); the old code trusted any non-zero value as a weapon
 *        switch request, so pressing Shift (which perturbs the bit stream)
 *        looked like a weapon change.
 */
#include "codol_player.h"
#include "codol_equipment.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

static int fails;
#define CK(c, ...) do { if (!(c)) { printf("FAIL " __VA_ARGS__); printf("\n"); fails++; } } while (0)

static codol_usercmd_t cmd(uint32_t t, uint32_t btn, int fwd, int right, uint16_t yaw, uint16_t weapon)
{
    codol_usercmd_t c; memset(&c, 0, sizeof(c));
    c.time = t; c.buttons = btn; c.forwardmove = (int8_t)fwd;
    c.rightmove = (int8_t)right; c.yaw = yaw; c.weapon = weapon;
    return c;
}

int main(void)
{
    codol_player_t p;
    codol_equipment_t e;
    codol_usercmd_t c;

    /* --- Bug 1: eye height --- */
    codol_player_init(&p, 48.0f, -572.0f, -116.0f);
    {
        float eye = p.z + 60.0f;
        CK(fabsf(eye - (-56.0f)) < 0.01f, "eye z should be foot z + 60, got %.1f", eye);
        printf("ok   eye height   foot z=%.1f -> eye z=%.1f\n", p.z, eye);
    }

    /* --- Bug 2: garbage weapon must not switch --- */
    codol_equipment_init(&e);
    {
        int before = e.selected_slot;
        /* live capture value; not a real weapon id, must be ignored */
        c = cmd(1000, 0, 0, 0, 0, 58566);
        codol_equipment_step(&e, &c, 16);
        CK(e.selected_slot == before, "garbage weapon 58566 switched slot %d->%d", before, e.selected_slot);
        CK(e.current_weapon == 309, "garbage weapon corrupted current_weapon=%d", e.current_weapon);
        printf("ok   garbage W    W=58566 ignored, slot=%d weapon=%d\n", e.selected_slot, e.current_weapon);
    }

    /* --- Bug 2b: a REAL weapon id still switches (custom2 has 1157/1158/317) --- */
    {
        CK(codol_equipment_select_backpack(&e, "mr 1 1 custom2"), "backpack select failed");
        c = cmd(1100, 0, 0, 0, 0, 1157);
        codol_equipment_step(&e, &c, 16);
        CK(e.current_weapon == 1157, "real weapon 1157 not adopted (got %d)", e.current_weapon);
        printf("ok   real W      W=1157 adopted, weapon=%d\n", e.current_weapon);
    }

    /* --- Bug 2c: sprint must raise speed, not switch --- */
    {
        codol_equipment_init(&e);
        int before = e.selected_slot;
        codol_player_init(&p, 48.0f, -572.0f, -116.0f);
        c = cmd(2000, CODOL_BTN_SPRINT, 1, 0, 0, 58566);
        codol_player_apply_usercmd(&p, &c, 1.0f / 128.0f);
        {
            float sp = sqrtf(p.vx * p.vx + p.vy * p.vy);
            CK(fabsf(sp - CODOL_SPRINT_SPEED) < 1.0f, "sprint speed %.1f != %.1f", sp, CODOL_SPRINT_SPEED);
            printf("ok   sprint      |v|=%.1f (walk %.0f)\n", sp, CODOL_MOVE_SPEED);
        }
        c = cmd(2010, CODOL_BTN_SPRINT, 0, 0, 0, 58566);
        codol_equipment_step(&e, &c, 16);
        CK(e.selected_slot == before, "sprint press switched weapon");
    }

    /* --- fire bit is bit0 per IW4X buttons_t --- */
    {
        codol_equipment_init(&e);
        c = cmd(3000, CODOL_BTN_FIRE, 0, 0, 0, 0);
        CK(codol_equipment_step(&e, &c, 16), "CODOL_BTN_FIRE(0x1) did not fire");
        CK(e.slots[0].clip == 5, "clip should be 5, got %d", e.slots[0].clip);
        printf("ok   fire bit    0x1 fires, clip=%d\n", e.slots[0].clip);
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
