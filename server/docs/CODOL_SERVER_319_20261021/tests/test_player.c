/* test_player: \u79fb\u52a8\u6a21\u578b\u2014\u2014\u9010\u884c\u5bf9\u7167 CODOL-Combat-Server-v0.1
 * GameWorld.ComputeMoveVelocity + \u5b9e\u6d4b\u6807\u5b9a\u914d\u7f6e firingrange_live.cfg:
 *   dir_bias = 0 -2 / flip_move_y = 1 / flip_strafe_x = 1 / vertical_sim = 0 */
#include "codol_player.h"
#include <stdio.h>
#include <math.h>
#include <string.h>

static int fails;
static codol_usercmd_t cmd(uint32_t t, uint32_t btn, int fwd, int right, uint16_t yaw)
{
    codol_usercmd_t c; memset(&c, 0, sizeof(c));
    c.time = t; c.buttons = btn; c.forwardmove = (int8_t)fwd;
    c.rightmove = (int8_t)right; c.yaw = yaw; return c;
}

#define NEAR(a,b) (fabsf((a)-(b)) < 1e-2f)
#define CK(c, ...) do { if (!(c)) { printf("FAIL " __VA_ARGS__); printf("\n"); fails++; } } while (0)

int main(void)
{
    codol_player_t p;
    codol_usercmd_t c;
    float x0, y0, z0;

    codol_player_init(&p, 48.0f, -572.0f, -116.0f);

    /* \u2460 \u51fa\u751f\u70b9\u5fc5\u987b\u662f\u5b9e\u6d4b\u5730\u9762 z=-127.018 (\u975e -116) */
    CK(NEAR(p.z, -116.0f), "\u51fa\u751f z=%.3f (\u5e94 -116)", p.z);
    printf("ok   \u51fa\u751f\u70b9     (%.1f, %.1f, %.3f)\n", p.x, p.y, p.z);

    /* \u2461 \u5782\u76f4: \u91cd\u529b\u843d\u5730 -> z \u6536\u655b\u5230 -116 */
    {
        int i;
        for (i = 0; i < 400; i++) {
            c = cmd((uint32_t)(i * 16), 0u, 1, 0, 0);
            codol_player_apply_usercmd(&p, &c, 1.0f / 32.0f);
        }
        CK(NEAR(p.z, -116.0f), "\u672a\u843d\u5230\u5730\u9762: z=%.3f (\u5e94 -116)", p.z);
        CK(p.on_ground, "\u843d\u5730\u540e on_ground \u5e94\u4e3a true");
        printf("ok   \u5782\u76f4        \u843d\u5730\u5230 z=%.1f, on_ground=%d\n", p.z, (int)p.on_ground);
    }

    /* \u2462 \u524d\u8fdb: yaw=0 -> +X ; dir_bias=-2 \u6240\u4ee5 yaw=16384(\u5ba2\u6237\u7aef 90\u00b0) -> -X */
    {
        p.vx = p.vy = 0; x0 = p.x; y0 = p.y;
        c = cmd(1, 0, 1, 0, 0);
        codol_player_apply_usercmd(&p, &c, 1.0f / 32.0f);
        CK(p.x > x0 && NEAR(p.y, y0), "yaw=0 \u524d\u8fdb dx=%.3f dy=%.3f (\u5e94 +x)", p.x - x0, p.y - y0);
        printf("ok   \u524d\u8fdb yaw=0    dx=%+.3f dy=%+.3f (\u6cbf +x)\n", p.x - x0, p.y - y0);

        p.vx = p.vy = 0; x0 = p.x;
        c = cmd(2, 0, 1, 0, 16384);
        codol_player_apply_usercmd(&p, &c, 1.0f / 32.0f);
        CK(p.x < x0, "yaw=16384 \u524d\u8fdb dx=%.3f (\u5e94 -x, dir_bias \u7b26\u53f7\u76f8\u53cd)", p.x - x0);
        printf("ok   \u524d\u8fdb yaw=90   dx=%+.3f (\u6cbf -x, dir_bias=-2 \u7b26\u53f7\u76f8\u53cd)\n", p.x - x0);
    }

    /* \u2463 \u53f3\u79fb: flip_strafe_x + flip_move_y -> yaw=0 \u53f3\u79fb\u8d70 -Y */
    {
        p.vx = p.vy = 0; x0 = p.x; y0 = p.y;
        c = cmd(3, 0, 0, 1, 0);
        codol_player_apply_usercmd(&p, &c, 1.0f / 32.0f);
        CK(p.y < y0 && NEAR(p.x, x0), "\u53f3\u79fb dx=%.3f dy=%.3f (\u5e94 -y)", p.x - x0, p.y - y0);
        printf("ok   \u53f3\u79fb yaw=0    dx=%+.3f dy=%+.3f (\u6cbf -y)\n", p.x - x0, p.y - y0);
    }

    /* \u2464 \u659c\u5411\u5f52\u4e00: |v| \u5e94\u6052\u4e3a WalkSpeed */
    {
        p.vx = p.vy = 0;
        c = cmd(4, 0, 1, 1, 0);
        codol_player_apply_usercmd(&p, &c, 1.0f / 32.0f);
        {
            float sp = sqrtf(p.vx * p.vx + p.vy * p.vy);
            CK(NEAR(sp, CODOL_MOVE_SPEED), "\u659c\u5411\u901f\u5ea6=%.2f (\u5e94 %.1f)", sp, CODOL_MOVE_SPEED);
            printf("ok   \u659c\u5411\u5f52\u4e00   |v|=%.2f (= WalkSpeed %.0f)\n", sp, CODOL_MOVE_SPEED);
        }
    }

    /* \u2465 \u5f00\u955c: buttons & 0x800 -> aim_fraction 0->1->0 */
    {
        p.aiming = false; p.aim_fraction = 0.0f;
        c = cmd(100, CODOL_BTN_ADS, 0, 0, 0);
        codol_player_apply_usercmd(&p, &c, 1.0f / 60.0f);
        CK(p.aiming && p.aim_fraction > 0.0f, "\u5f00\u955c\u672a\u751f\u6548");
        { int i; for (i = 0; i < 60; i++) { c.time += 16; codol_player_apply_usercmd(&p, &c, 1.0f / 60.0f); } }
        CK(p.aim_fraction > 0.999f, "\u5f00\u955c\u672a\u6ee1 frac=%.3f", p.aim_fraction);
        c.buttons = 0;
        { int i; for (i = 0; i < 60; i++) { c.time += 16; codol_player_apply_usercmd(&p, &c, 1.0f / 60.0f); } }
        CK(p.aim_fraction < 0.001f && !p.aiming, "\u6536\u955c\u672a\u56de\u96f6 frac=%.3f", p.aim_fraction);
        printf("ok   \u5f00\u955c/\u6536\u955c 0->1->0, ads_per_sec=%.0f\n", CODOL_ADS_PER_SEC);
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
