#ifndef CODOL_PLAYER_H
#define CODOL_PLAYER_H
/* 玩家运动状态 —— World 层。照手册 §5.1: 本层**不知道 socket 细节**。
 *
 * pmove 依据: CoD4x src/bg_jump.cpp(IW3, 同族)
 *   Jump_CalcHeight: 跳跃初速 = 2 * jumpHeight * gravity
 *                    且当 PMF_JUMPING 且 pm_time <= 落地减速窗口时除以
 *                    newdiv = pm_time*1.5*0.00058823527 + 1.0(>1699 时 2.5)
 *   Jump_GetLandFactor: 落地因子 = 同式(封顶 2.5)
 * ★ 这些常量是**内部移动模型**(手册 §4.2: 3.19 官方 usercmd/pmove 线格式未闭合),
 *   不作为最终协议断言。 */
#include <stdint.h>
#include <stdbool.h>
#include "codol_usercmd.h"
#include "codol_world.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CODOL_PMF_JUMPING              0x00000200u   /* 内部模型常量, 待证据绑定 */
#define CODOL_JUMP_LAND_SLOWDOWN_TIME  1700
#define CODOL_JUMP_HEIGHT              39.0f
#define CODOL_GRAVITY                  800.0f
#define CODOL_JUMP_SLOWDOWN_ENABLE     true
/* 水平移动模型: 速度 + 斜向归一化, 取自参照实现(已在真实客户端上让玩家能正常移动).
 * ★ 服务端发的位置必须贴近客户端自己的预测, 否则每帧被拽回 -> 空气墙/橡皮筋。 */
#define CODOL_MOVE_SPEED               190.0f
/* dir_bias = 0 -2 (实测): 真实朝向 = yaw度 * -2 + 0 */
#define CODOL_DIR_BIAS_SCALE           (-2.0)
#define CODOL_DIR_BIAS_DEG             0.0
#define CODOL_HALF_DIAG                0.70710678f
/* 开镜: 照参照实现 _Slot(..., ads=4) -> ads_per_sec = 4.0 */
/* ★ IW4X buttons_t 实际位定义(Structs.hpp:2036-2052):
 *   ATTACK=1<<0(0x1) SPRINT=1<<1(0x2) MELEE=1<<2(0x4) ACTIVATE=1<<3(0x8)
 *   RELOAD=1<<4(0x10) ... ADS=1<<11(0x800)
 *   之前没有 SPRINT -> Shift 被错当切枪(实测 2026-10-22)。 */
#define CODOL_BTN_SPRINT               0x2u
#define CODOL_SPRINT_SPEED             320.0f   /* 冲刺速度(参照 CoD4x pmove 默认) */
#define CODOL_ADS_PER_SEC              4.0f
#define CODOL_BTN_ADS                  0x800u   /* usercmd buttons 里的开镜键 */

typedef enum {
    CODOL_STANCE_STAND = 0,
    CODOL_STANCE_CROUCH = 1,
    CODOL_STANCE_PRONE = 2
} codol_stance_t;

typedef struct {
    float   x, y, z;
    float   vx, vy, vz;
    uint16_t pitch, yaw, roll;
    uint32_t pm_flags;
    int      pm_time;            /* 距跳跃/落地的毫秒, 落地下滑用 */
    float    gravity;
    bool     on_ground;
    codol_stance_t stance;
    uint32_t buttons;
    uint16_t weapon;
    int      last_cmd_time;
    float    jump_origin_z;   /* IW4 playerState: jumpOriginZ */
    /* 开镜状态 -> 快照 index 20(aiming) 与 index 41(aim_fraction) */
    bool     aiming;
    float    aim_fraction;
    float    movement_dir;    /* IW4 playerState: movementDir  */
} codol_player_t;

void codol_player_init(codol_player_t *p, float x, float y, float z);

/* CoD4x Jump_CalcHeight 的结构(跳跃是 gravity/pm_flags/pm_time 的函数, 不是常量) */
float codol_player_jump_velocity(const codol_player_t *p);
float codol_player_land_factor(const codol_player_t *p);

/* World-aware movement applies static clipmap and dynamic entity hulls.
 * The legacy helper remains for isolated unit tests that do not own a world. */
void codol_player_move_in_world(codol_player_t *p, const codol_usercmd_t *c, float dt,
                                const codol_world_t *world, int skip_entity);
void codol_player_apply_usercmd(codol_player_t *p, const codol_usercmd_t *c, float dt);

/* 用一批 usercmd 推进 */
void codol_player_apply_list(codol_player_t *p, const codol_usercmd_list_t *l, float dt);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_PLAYER_H */
