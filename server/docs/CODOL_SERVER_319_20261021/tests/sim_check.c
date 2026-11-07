/* sim_check.c -- drive the real movement model and report trajectory sanity. */
#include "codol_player.h"
#include "codol_collision.h"
#include <stdio.h>
#include <math.h>
#include <string.h>

int main(void)
{
    codol_player_t p;
    codol_usercmd_t c;
    int i, landed = -1, blocked = -1;
    float prevx, prevy;

    codol_player_init(&p, 48.0f, -572.0f, -100.0f);   /* start 16u above ground */

    /* phase 1: free fall, no input */
    for (i = 0; i < 200; i++) {
        memset(&c, 0, sizeof(c));
        c.time = (uint32_t)(i * 8);
        codol_player_apply_usercmd(&p, &c, 1.0f / 128.0f);
        if (landed < 0 && p.on_ground) landed = i;
    }
    printf("phase1 fall: landed at frame %d, z=%.2f on_ground=%d\n", landed, p.z, (int)p.on_ground);

    /* phase 2: walk forward (+x) 300 frames */
    prevx = p.x;
    for (i = 0; i < 300; i++) {
        memset(&c, 0, sizeof(c));
        c.time = (uint32_t)(1000 + i * 8);
        c.forwardmove = 127; c.yaw = 0;
        codol_player_apply_usercmd(&p, &c, 1.0f / 128.0f);
        if (blocked < 0 && fabsf(p.x - prevx) < 0.001f) blocked = i;
        prevx = p.x;
    }
    printf("phase2 walk: x=%.1f y=%.1f z=%.1f (moved %.1f units)\n", p.x, p.y, p.z, p.x - 48.0f);

    /* phase 3: walk into the clip box at (-75,-434): face -x/-y */
    codol_player_init(&p, -75.0f, -500.0f, -116.0f);
    for (i = 0; i < 400; i++) {
        memset(&c, 0, sizeof(c));
        c.time = (uint32_t)(5000 + i * 8);
        c.forwardmove = 127; c.yaw = 0;    /* yaw 0 -> +x per earlier calibration */
        c.rightmove = 127;                  /* also try +y */
        codol_player_apply_usercmd(&p, &c, 1.0f / 128.0f);
    }
    printf("phase3 into clip: x=%.1f y=%.1f z=%.1f\n", p.x, p.y, p.z);

    printf("\nSUMMARY: ground=%d, free-walk=%d\n",
           landed >= 0, p.z > -200.0f);
    return 0;
}
