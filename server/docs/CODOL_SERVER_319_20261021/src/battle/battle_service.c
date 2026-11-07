#include "codol_battle_service.h"
#include "codol_platform.h"
#include "codol_snapshot.h"
#include "codol_world.h"
#include "codol_movement.h"
#include "codol_entity.h"
#include "codol_combat.h"
#include "codol_weapondefs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* 眼睛高度: playerstate.origin 是眼位, 脚底 + 60 = 眼位 (快照 index 38 同值) */
#define CODOL_EYE_HEIGHT 60.0f

/* ★ 2026-11-07: 下行帧的 serverId。
 *   netchan 明文布局(实机 RX_BODY 证实)是
 *     [0..3] 序号 | [4] serverId | [5..8] messageAck | [9..12] reliableAck | [13..] body
 *   掩码 = (messageAck ^ 1 ^ serverId) & 0xFF, 从偏移 13 起。
 *   客户端会在自己的上行帧 [4] 里带它的 serverId, 这里抄回来原样回填,
 *   避免客户端因 serverId 不一致而整条丢弃。 */
static uint8_t g_peer_serverid = 0;

/* gamestate 里 mapName/gameType 之后那个 u32 = configStringChecksum
 *   (PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023 §2; 与 _LEARN_TESTOL_DELIVERY2 §470 十四一致)。
 *
 * 2026-11-07 实机两连测(都是同一台客户端、同一份 fixture)：
 *   run 170243  原样转发 fixture 值 0x62F0CDCD  -> 客户端报 gamestateupdate 1，
 *               随后才因别的原因断开（弹「关卡文件与服务器的不同」）
 *   run 181405  回填 connect 里的 \checksum\(0xD6965188) -> 客户端连进度都不报，
 *               clientState 7→0 直接断开（界面错误码 1107）
 * ⇒ **不能回填客户端值**：这一格由客户端对收到的 configstring 自行校验，
 *   只要不改 configstring，fixture 里的值就是对的。
 * 保留下面的解析只为留证据/复现（默认不回填，CODOL_ECHO_CHECKSUM=1 才开）。 */
static uint32_t g_peer_checksum = 0;
static int g_peer_checksum_valid = 0;

#ifdef _WIN32
#include <windows.h>
static uint64_t mono_ms(void) { return (uint64_t)GetTickCount64(); }
#else
#include <time.h>
static uint64_t mono_ms(void)
{
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000 + (uint64_t)ts.tv_nsec / 1000000;
}
#endif

void codol_battle_service_bind_world(codol_battle_service_t *svc,
                                     codol_world_t *world, int client_num)
{
    if (!svc) return;
    svc->world = world;
    svc->world_client = client_num;
    if (world && client_num >= 0 && client_num < CODOL_MAX_CLIENTS) {
        if (codol_world_spawn_player(world, client_num) == CODOL_OK) {
            const codol_player_state_t *ps = codol_player_get(world, client_num);
            if (ps) {
                svc->player.x = ps->origin[0];
                svc->player.y = ps->origin[1];
                svc->player.z = ps->origin[2];
                svc->player.vx = ps->velocity[0];
                svc->player.vy = ps->velocity[1];
                svc->player.vz = ps->velocity[2];
            }
        }
    }
}

/* Deterministic test target for the isolated firing-range harness.
 * The target is stationary, has a real health pool, and is never sent as a
 * client entity; it exists only to exercise the damage/death path. */
static int ensure_damage_target(codol_battle_service_t *svc)
{
    int i;
    if (!svc || !svc->world) return -1;
    for (i = 0; i < CODOL_MAX_ENTITIES; ++i) {
        codol_entity_state_t *e = &svc->world->entities[i];
        if (e->in_use && e->type == CODOL_ET_ACTOR && e->owner == 1001)
            return e->number;
    }
    if (codol_entity_spawn_actor(svc->world, 0, 0.0f, 0.0f, -116.0f, 100, 0) != CODOL_OK)
        return -1;
    for (i = 0; i < CODOL_MAX_ENTITIES; ++i) {
        codol_entity_state_t *e = &svc->world->entities[i];
        if (e->in_use && e->type == CODOL_ET_ACTOR) {
            e->owner = 1001;
            e->mins[0] = -15.0f; e->mins[1] = -15.0f; e->mins[2] = 0.0f;
            e->maxs[0] = 15.0f; e->maxs[1] = 15.0f; e->maxs[2] = 70.0f;
            return e->number;
        }
    }
    return -1;
}

static void apply_test_hit(codol_battle_service_t *svc, int target_num)
{
    const codol_weapondef_t *weapon;
    codol_damage_policy_t policy;
    codol_damage_result_t result;
    float distance = 0.0f;
    if (!svc || !svc->world || target_num < 0) return;
    weapon = codol_weapondef_find("m4a1tech_mp");
    if (!weapon) return;
    if (svc->world_client >= 0 && svc->world_client < CODOL_MAX_CLIENTS) {
        const codol_player_state_t *ps = codol_player_get(svc->world, svc->world_client);
        codol_entity_state_t *target = codol_entity_get(svc->world, target_num);
        if (ps && target) {
            float dx = target->pos.origin[0] - ps->origin[0];
            float dy = target->pos.origin[1] - ps->origin[1];
            float dz = target->pos.origin[2] - ps->origin[2];
            distance = sqrtf(dx * dx + dy * dy + dz * dz);
        }
    }
    codol_damage_policy_default(&policy);
    if (codol_damage_apply(svc->world, target_num, weapon, distance,
                           CODOL_HITLOC_TORSO_UPPER, &policy, &result) == CODOL_OK) {
        CODOL_LOG_INFO("[world] HIT target=%d damage=%d health=%d killed=%d distance=%.1f",
                       target_num, result.damage, result.target_health_after,
                       (int)result.killed, distance);
    }
}

codol_result_t codol_battle_service_apply_usercmd(codol_battle_service_t *svc,
                                                  const codol_usercmd_t *cmd,
                                                  uint32_t elapsed_ms)
{
    if (!svc || !cmd) return CODOL_ERR_INVALID_ARG;
    /* ★ 视角与开镜状态必须无条件写入 svc->player。
     *   此前只有无 world 的分支(codol_player_move_in_world)会写 pitch/yaw/roll/aim_*,
     *   而服务端实际走的是 world 分支 —— 它只回填 origin/velocity, 于是
     *   svc->player.yaw 永远是 init 的 0: 快照下发的视角恒为 0、input_baselines
     *   记录的基线也是 0(客户端拿它做 delta 基线必然解出垃圾)。 */
    svc->player.pitch = cmd->pitch;
    svc->player.yaw = cmd->yaw;
    svc->player.roll = cmd->roll;
    svc->player.buttons = cmd->buttons;
    svc->player.aiming = ((cmd->buttons & CODOL_BTN_ADS) != 0);
    {
        float step = (svc->player.aiming ? 1.0f : -1.0f) * CODOL_ADS_PER_SEC
                     * (float)elapsed_ms * 0.001f;
        svc->player.aim_fraction += step;
        if (svc->player.aim_fraction > 1.0f) svc->player.aim_fraction = 1.0f;
        if (svc->player.aim_fraction < 0.0f) svc->player.aim_fraction = 0.0f;
    }
    if (svc->world && svc->world_client >= 0 &&
        svc->world_client < CODOL_MAX_CLIENTS) {
        const codol_player_state_t *ps;
        /* ★ 用**真实命令间隔**积分: 固定 1/128 会让位移偏小上千倍,
         *   服务端坐标因此不可信(实测每帧发位置时客户端被推着飘出地图)。 */
        codol_result_t rc = codol_movement_process_usercmd_dt(
            svc->world, svc->world_client, cmd,
            (float)elapsed_ms * 0.001f);
        if (rc != CODOL_OK) return rc;
        ps = codol_player_get(svc->world, svc->world_client);
        if (ps) {
            svc->player.x = ps->origin[0];
            svc->player.y = ps->origin[1];
            svc->player.z = ps->origin[2];
            svc->player.vx = ps->velocity[0];
            svc->player.vy = ps->velocity[1];
            svc->player.vz = ps->velocity[2];
        }
    } else {
        codol_player_move_in_world(&svc->player, cmd,
                                   (float)elapsed_ms * 0.001f, NULL, -1);
    }
    svc->last_cmd = *cmd;
    svc->have_last_cmd = true;
    return CODOL_OK;
}

void codol_battle_service_init(codol_battle_service_t *svc, void *ctx,
                               codol_battle_sendto_fn send)
{
    memset(svc, 0, sizeof(*svc));
    svc->ctx = ctx;
    svc->send = send;
    codol_battle_init(&svc->battle);
    /* 出生点: 取自参照实现已验证的 mp_firingrange 出生坐标
     *   (battle_server.py: "pos_x": 48.0, "pos_y": -572.0, "pos_z": -116.0).
     *   ★ 现状: (48,-572,-116) 已实测错误(客户端报告"卡在房顶/天上") -> 改成不发自算位置。
     *   ★ 注意: 曾把"空气墙"归因于此, 那是**推断**——当时 usercmd 解析恒失败、
     *     位置从不更新, 两个因素混在一起, 并未单独验证。 */
    /* ★★ 出生点 = 地图自己的 info_player_start_so。
     *   来源: 解出的 zone (coop_train_mp_firingrange) 实体串实测数据:
     *     info_player_start_so  origin = 48 -572 -116   (这张图唯一的设计出生点)
     *   之前照某份 C# 配置改成 -127.018, 比地图出生点低 11 单位 ->
     *   人陷进地板/卡住。 */
    codol_player_init(&svc->player, 48.0f, -572.0f, -116.0f);
    codol_equipment_init(&svc->equip);
    codol_snap_state_zero(&svc->snap_from);
    codol_snap_state_zero(&svc->snap_cur);
    svc->processed_input_time = 0;
    strncpy(svc->gamestate_path, "firingrange-gamestate.bin",
            sizeof(svc->gamestate_path) - 1);
    /* 实体段开关: 默认关(文件不存在)。放一个空文件 snapshot_entities.on 即打开。 */
    strncpy(svc->entities_flag_path, "snapshot_entities.on",
            sizeof(svc->entities_flag_path) - 1);
    /* mirror_predicted = 0 (实测配置): 关闭镜像。实测结论是客户端必须服务
     * 端权威地每帧接收位置; 镜像（以及省略位置）都会让它无碰撞无限飘。 */
    svc->predicted_path[0] = 0;
    svc->netchan_seq = 1;
    svc->last_rx_ms = mono_ms();
}

/* 读 nt10 探针写出的 predicted.bin: <6f I> = x,y,z,vx,vy,vz,seq (28B, LE).
 * 返回 true 当且仅当:文件存在、大小正确、数值有效、**且 mtime 新鲜**(避免用陈旧值把人拽回)。 */
static bool read_predicted(const char *path, float out[6], int max_age_ms, uint32_t *seq_out)
{
    FILE *fp;
    unsigned char buf[28];
    int i;

    if (!path || !path[0]) return false;
    fp = fopen(path, "rb");
    if (!fp) return false;
    if (fread(buf, 1, sizeof(buf), fp) != sizeof(buf)) { fclose(fp); return false; }
    fclose(fp);

    for (i = 0; i < 6; i++) {
        float v;
        memcpy(&v, buf + i * 4, 4);
        if (!(v == v)) return false;                       /* NaN */
        if (v > 100000.0f || v < -100000.0f) return false; /* 越界 */
        out[i] = v;
    }
    if (out[0] == 0.0f && out[1] == 0.0f && out[2] == 0.0f) return false;
    if (seq_out) memcpy(seq_out, buf + 24, 4);

#ifdef _WIN32
    /* 新鲜度: predicted.bin 必须是刚写的。两者同为 FILETIME(100ns since 1601)
     * 基准, 可直接相减。 */
    {
        WIN32_FILE_ATTRIBUTE_DATA fad;
        FILETIME now_ft;
        uint64_t now100, mt100;
        if (!GetFileAttributesExA(path, GetFileExInfoStandard, &fad)) return false;
        GetSystemTimeAsFileTime(&now_ft);
        now100 = ((uint64_t)now_ft.dwHighDateTime << 32) | now_ft.dwLowDateTime;
        mt100 = ((uint64_t)fad.ftLastWriteTime.dwHighDateTime << 32) | fad.ftLastWriteTime.dwLowDateTime;
        if (now100 > mt100 && (now100 - mt100) > (uint64_t)max_age_ms * 10000ull) return false;
    }
#else
    (void)max_age_ms;
#endif
    return true;
}

/* 简单文件开关: 文件存在 = true(默认关)。 */
static bool flag_file_exists(const char *path)
{
    FILE *fp;
    if (!path || !path[0]) return false;
    fp = fopen(path, "rb");
    if (!fp) return false;
    fclose(fp);
    return true;
}

/* game state 下发 —— 照参照实现 SendPendingGameStates:
 * payload = u32 seq + state(259B); [8:] 按 (seq^1)&0xFF 掩码 */
#define GS_LOG_WARN(...) CODOL_LOG_WARN(__VA_ARGS__)
#include "gs_adapt.h"
static int send_gamestate(codol_battle_service_t *svc, codol_battle_assoc_t *a)
{
    uint8_t state[1200];
    uint8_t payload[1216];
    uint32_t seq;
    uint8_t mask;
    FILE *fp;
    size_t n;
    int i, total;
    char room_path[600];

    fp = fopen(svc->gamestate_path, "rb");
    if (!fp) { CODOL_LOG_WARN("[battle] 打不开 %s", svc->gamestate_path); return -1; }
    n = fread(state, 1, sizeof(state), fp);
    fclose(fp);
    if (n < 16 || n > 1100) { CODOL_LOG_WARN("[battle] gamestate 尺寸异常 %zu", n); return -1; }

    snprintf(room_path, sizeof(room_path), "%s/active_room.json", ".");
    /* ★ 2026-11-07 A/B 开关：kit 里放 `no_map_adapt.flag` 时完全跳过地图适配，
     *   行为与"加地图选择之前"逐字节一致(直接发 fixture)。
     *   用文件而不是环境变量：run_all 是由提权 agent 拉起的，环境变量传不进去。 */
    {
        static int no_adapt = -1;
        if (no_adapt < 0) {
            FILE *nf = fopen("./no_map_adapt.flag", "rb");
            no_adapt = nf ? 1 : 0;
            if (nf) fclose(nf);
            if (no_adapt) CODOL_LOG_WARN("[battle] no_map_adapt.flag 存在 -> 跳过地图适配");
        }
        if (no_adapt) {
            CODOL_LOG_INFO("[battle] gamestate 原样发送(适配已禁用, state=%zuB)", n);
            goto send_now;
        }
    }
    if (_gs_adapt_dynamic(state, sizeof(state), &n, room_path) == 0) {
        /* ★ 把这一局选中的地图打出来 —— 动态地图选择器的唯一可观测出口 */
        char gm[128] = {0}, gt[64] = {0};
        size_t sp = 9, k = 0;
        while (sp < n && state[sp] && k + 1 < sizeof(gm)) gm[k++] = (char)state[sp++];
        sp++; k = 0;
        while (sp < n && state[sp] && k + 1 < sizeof(gt)) gt[k++] = (char)state[sp++];
        CODOL_LOG_INFO("[battle] gamestate 地图选择: map=%s gametype=%s (state=%zuB)",
                       gm, gt, n);
    } else {
        CODOL_LOG_WARN("[battle] gamestate 动态适配未生效 (%s 与 coop_map.txt 都不可用) —— 地图沿用 fixture",
                       room_path);
    }

    /* ★★ 2026-11-07 实机(run ONCE_20261107_181405)定案：**不能**回填客户端值。
     *
     *   填 fixture 原值 0x62F0CDCD 时, 客户端解析完 gamestate 会报 gamestateupdate 1,
     *   之后才因为别的原因断开(上一刀看到的"关卡文件不同")；
     *   回填 connect 里的 \checksum\(0xD6965188) 后, 客户端 **连进度都不报**,
     *   clientState 7→0 直接断开(界面报错误码 1107)。
     *
     *   ⇒ 这一格是**服务端对 configstring 块的校验值**, 由客户端自己重算比对;
     *     只要我们不改 configstring, fixture 里的值就是对的。回填客户端自报值必错。
     *   ⇒ 默认关闭；需要复现这条实验时设 CODOL_ECHO_CHECKSUM=1。
     *   ⚠ 将来若真的换图(cs0 被改写), 这个值**必须重算**——见 §470
     *     "如果你改这个字符串, 你必须在同一个提交里重新生成 fixture"。 */
    {
        static int echo_cksum = -1;
        if (echo_cksum < 0) {
            const char *e = getenv("CODOL_ECHO_CHECKSUM");
            echo_cksum = (e && e[0] == '1') ? 1 : 0;
        }
        if (echo_cksum && g_peer_checksum_valid && n > 16 && state[4] == 3) {
            size_t p = 4 + 1 + 4;
            size_t m = p;
            while (m < n && state[m]) m++;          /* map */
            m++;
            while (m < n && state[m]) m++;          /* gametype */
            m++;
            if (m + 4 <= n) {
                uint32_t old;
                memcpy(&old, state + m, 4);
                memcpy(state + m, &g_peer_checksum, 4);
                CODOL_LOG_INFO("[battle] gamestate configStringChecksum 0x%08X -> 0x%08X (off=%zu)",
                               (unsigned)old, (unsigned)g_peer_checksum, m);
            }
        }
    }

send_now:
    seq = svc->netchan_seq++;
    /* ★★ 2026-11-07: 同 send_snapshot —— 补齐 13 字节 netchan 头, 掩码从 13 起。 */
    total = 13 + (int)n;
    payload[0] = (uint8_t)seq; payload[1] = (uint8_t)(seq >> 8);
    payload[2] = (uint8_t)(seq >> 16); payload[3] = (uint8_t)(seq >> 24);
    payload[4] = g_peer_serverid;
    payload[5] = payload[6] = payload[7] = payload[8] = 0;
    payload[9] = payload[10] = payload[11] = payload[12] = 0;
    memcpy(payload + 13, state, n);
    mask = (uint8_t)((0u ^ 1u ^ (unsigned)g_peer_serverid) & 0xFF);
    for (i = 13; i < total; i++) payload[i] ^= mask;

    svc->gamestate_attempts++;
    if (send_frame(svc, a, payload, total) < 0) return -1;

    CODOL_LOG_INFO("[battle] TX_GAMESTATE seq=%u state=%zuB (attempt %u)",
                   (unsigned)seq, n, svc->gamestate_attempts);
    return 0;
}

/* 运动快照 —— "等待玩家数据"等的就是它: gamestateupdate 6 后 0.5s 起, 每 25ms 一帧 */
#define CODOL_SNAP_DT_MS 7    /* snap_hz = 128 (实测配置: 128Hz 是参考实现采样率) */

/* 出生点: 本版**不指定**。参照实现(HANDOFF §13.35)说"首帧必须发一个已知可站的坐标",
 * 但我们试过两次(355 1371 0 / 48 -572 -116)都报"在房顶", 按用户决定撤回。
 * 迭代用的候选表已存档: HANDOFF_20261025_BINARY_BISECT.md §11。 */

/* ★ 位置/出生点实验已完成, 结论见 send_snapshot() 里的注释; 需要重做时用 §11.2 的候选坐标。
 *   (2026-10-25 试过的坐标: 355 1371 0 / 48 -572 -116 / -44 -387 -83) */

static int send_snapshot(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                         uint64_t now_ms)
{
    codol_snap_equip_t eq;
    uint8_t snap[512], payload[528];
    uint32_t seq, server_time;
    uint8_t mask;
    int n, i, total;
    float px, py, pz, pvx, pvy;
    bool omit;
    codol_snap_entity_t ents[8];
    int ent_count = 0;

    codol_equipment_to_snapshot(&svc->equip, &eq);
    if (!svc->snapshot_epoch_ms) svc->snapshot_epoch_ms = now_ms;
    server_time = 1000 + (uint32_t)(now_ms - svc->snapshot_epoch_ms);

    /* ★★ 镜像客户端自己的预测态 (参照 "B 路线" / _MIRROR_PRED)。
     *   predicted.bin 由 nt10 --ps-probe 从客户端内存定点写出(20ms 一次),
     *   里面是客户端**自己**带重力/碰撞的位置与速度。
     *   回发它"应该"与客户端自己一致 -> 不拉扯 —— **推断, 本轮待验证**。
     *   拿不到镜像 -> **连首帧也不发位置**, 让客户端用地图自带出生点
     *   ((之前发的 48,-572,-116 会把人塞进房顶。) */
    {
        float pred[6];
        uint32_t sq = 0;
        if (read_predicted(svc->predicted_path, pred, 500, &sq)) {
            float lead = 0.05f;                    /* PRED_LEAD 默认 50ms */
            float lx = pred[3] * lead, ly = pred[4] * lead, lz = pred[5] * lead;
            float d2 = lx * lx + ly * ly + lz * lz;
            if (d2 > 120.0f * 120.0f) {            /* 外推限幅 120 单位 */
                float k = 120.0f / sqrtf(d2);
                lx *= k; ly *= k; lz *= k;
            }
            px = pred[0] + lx; py = pred[1] + ly; pz = pred[2] + lz;
            pvx = pred[3]; pvy = pred[4];
            omit = false;
            svc->mirror_hits++;
        } else {
            /* ★★ 位置策略(2026-10-26 单变量实验): **只发首帧, 之后完全放手**。
             *
             * 为什么停掉每帧下发:
             *   本轮实机(ONCE_20261026_215943)确认 —— 18404 帧快照里 **z 恒为 -116**,
             *   一次没变过。那个 -116 是 `collision.c` 里写死的无限大地面平面常数,
             *   不是算出来的: 地图 29 个碰撞盒最低只到 z=-169, **没有一块真实地板**。
             *   于是服务端每帧都在对客户端说"你在 (x, y, -116)", 而客户端靠自己跑
             *   物理得到的是另一个位置 ⇒ 两边互相拉扯 ⇒
             *     · 人物悬空(客户端被灌的 z 与它自己的落地判定冲突)
             *     · 穿墙(服务端的 x/y 也没有真实碰撞约束)
             *     · 走到某些位置卡住(分歧点被夹住)
             *     · 准星不出现(状态机被位置分歧搞乱)
             *
             * 为什么现在只发首帧是安全的(此前那次不是):
             *   上一轮"只发首帧"失败是因为**首帧同时把这些一起改坏了**:
             *     idx61 写成了 2046(导致开镜失效), movement 的 dt 仍是错值。
             *   这一轮 idx61 已回到 2047、dt 已用真实间隔, 位置是唯一的变量。
             *   首帧给出的 (48,-572,-116) 是地图 info_player_start_so 的官方出生点,
             *   之后客户端用自己完整的 ClipMap 跑物理 —— 那才是权威。
             *
             * ⚠️ 这是单变量实验: 只改这一个点。若客户端仍卡在屋顶, 说明它还依赖
             *    服务端的位置流来完成初始化, 那就得走"补全 clipmap 地板"那条路。 */
            px = svc->player.x;
            py = svc->player.y;
            pz = svc->player.z;
            pvx = svc->player.vx; pvy = svc->player.vy;
            omit = svc->snapshot_sent;   /* 首帧 false(发一次出生点), 之后 true(不发) */
            svc->mirror_miss++;
        }
    }

    /* ★★ 实体段(默认关): 只有开关文件 snapshot_entities.on 存在才发。
     *   从 world->entities[] 取 in_use && type != 0 的实体, 按槽号升序
     *   (数组本就是槽序, number == 槽号, 满足参照对升序的要求)。
     *   上限 8 条: 单条实体段最坏约 12 字节(号 13 位 + 头 9 位 +
     *   字段0 的 12 位 + 三轴各 21 位 ≈ 97 位), 8 条约 100 字节; 运动段
     *   最长 ~125 字节, 合计仍在 snap[512] 内留足余量, 不会撑爆 payload[520]。 */
    if (svc->world && flag_file_exists(svc->entities_flag_path)) {
        int wc;
        for (wc = 0; wc < CODOL_MAX_ENTITIES && ent_count < 8; wc++) {
            const codol_entity_state_t *e = &svc->world->entities[wc];
            if (e->in_use && e->type != 0) {
                ents[ent_count].number = e->number;
                ents[ent_count].type   = e->type;
                ents[ent_count].x      = e->pos.origin[0];
                ents[ent_count].y      = e->pos.origin[1];
                ents[ent_count].z      = e->pos.origin[2];
                ent_count++;
            }
        }
    }

    n = codol_snapshot_build(snap, sizeof(snap),
                             0,                 /* ack */
                             server_time,
                             svc->processed_input_time,   /* ★ command_time = 客户端 usercmd 的确认时刻。
                                                          * 之前写死 1000 -> 客户端认为命令永远没被消费,
                                                          * 不断重发 -> **客户端指令溢出** + 一跳漂移。 */
                             !svc->snapshot_sent,
                             px, py, pz,
                             (int16_t)svc->player.pitch, (int16_t)svc->player.yaw, (int16_t)svc->player.roll,
                             pvx, pvy,
                             svc->player.aim_fraction, svc->player.aiming,
                             omit,
                             /* ★★ index61 = groundEntityNum: 2046=在地面 / 2047=空中。
                              *   ★ 2026-10-24 实机回退: 参照按"服务端所见的接地状态"动态写,
                              *   但**我们服务端这份是退化的**(碰撞地面是写死的 -116 常数,
                              *   玩家恒不离地 ⇒ 恒发 2046)。实测 SNAPSHOT_RAWFIX_20261024_1357:
                              *   恒发 2046 → 客户端进"飞行模式"+开镜失效; 恒发 2047 → 客户端
                              *   自己跑物理。所以在真实 clipmap 碰撞落地之前, 这里仍传 false。
                              *   等碰撞是真的, 再改成传 svc->player.on_ground。
                              *   见 docs/SNAPSHOT_FIELD_DIFF_20261024.md §12。 */
                             false,
                             /* ★ ET6 武器子实体号。本轮还没有实体池 -> 0(无枪)。
                              *   下一步需要真正生成 ET6 并把它的 entityNum 传这里。 */
                             (uint16_t)0,
                             &svc->snap_from,   /* 上一帧基线 */
                             &svc->snap_cur,    /* 本帧值 */
                             &eq,
                             ent_count > 0 ? ents : NULL, ent_count);   /* 实体段(默认不发) */
    if (n <= 0) return -1;
    svc->snap_from = svc->snap_cur;   /* 本帧成为下一帧基线 */

    seq = svc->netchan_seq++;
    /* ★★ 2026-11-07: 下行帧补齐 13 字节 netchan 头, 掩码改从偏移 13 起。
     * 依据(实机 RX_BODY, 14B 明文 = 13 头 + 1 体):
     *   [0..3] u32 序号(29 位)|标志  [4] u8 serverId
     *   [5..8] u32 messageAck&0x1FFFFFFF  [9..12] u32 reliableAck
     *   [13..] body, 每字节 ^= mask, mask = (messageAck ^ 1 ^ serverId) & 0xFF
     * 旧实现只有 4 字节头、掩码从 8 起、掩码用 seq ⇒ 客户端每帧丢弃、ack 恒 0。 */
    total = 13 + n;
    payload[0] = (uint8_t)seq; payload[1] = (uint8_t)(seq >> 8);
    payload[2] = (uint8_t)(seq >> 16); payload[3] = (uint8_t)(seq >> 24);
    payload[4] = g_peer_serverid;
    payload[5] = payload[6] = payload[7] = payload[8] = 0;   /* messageAck */
    payload[9] = payload[10] = payload[11] = payload[12] = 0; /* reliableAck */
    memcpy(payload + 13, snap, (size_t)n);
    mask = (uint8_t)((0u ^ 1u ^ (unsigned)g_peer_serverid) & 0xFF);
    for (i = 13; i < total; i++) payload[i] ^= mask;

    /* ★ 对照实验(2026-10-25): 把前 3 帧快照的**完整线上字节**落盘。
     *   用途: 若客户端仍拒收, 可与离线探针(probe_snapshot_size)的输出逐字节对账,
     *   确认线上内容到底和"能用的那份"差在哪。 */
    {
        static int dbg_snap = 0, dbg_snap_ent = 0;
        /* 普通帧和"带实体段"的帧各记 3 帧: 后者本轮才第一次出现, 它的线上字节
         * 是判断客户端为何收/拒的直接物证。 */
        if ((ent_count > 0) ? (dbg_snap_ent < 3) : (dbg_snap < 3)) {
            char hx[1600];
            int j, dn = total < 400 ? total : 400;
            for (j = 0; j < dn; j++) sprintf(hx + j * 2, "%02X", payload[j]);
            hx[dn * 2] = 0;
            CODOL_LOG_INFO("[battle] TX_SNAP_HEX seq=%u total=%d ents=%d %s",
                           (unsigned)seq, total, ent_count, hx);
            if (ent_count > 0) dbg_snap_ent++; else dbg_snap++;
        }
    }

    if (send_frame(svc, a, payload, total) < 0) return -1;
    svc->snapshot_sent = true;
    { codol_snap_frame_t f; memset(&f, 0, sizeof(f)); f.seq = seq; f.server_time = server_time; f.player = svc->player; f.valid = true; codol_frame_history_commit(&svc->history, &f); }
    /* ★ 记录本帧快照的 ack -> 输入基线, 与参照 `input_baselines[seq]` 一致。
     *   客户端下一批 usercmd 会以这个 ack 为 delta 基线, 必须能精确还原。 */
    {
        int slot = (int)(seq % 513u);
        svc->input_baselines[slot].seq = seq;
        memset(&svc->input_baselines[slot].cmd, 0, sizeof(svc->input_baselines[slot].cmd));
        svc->input_baselines[slot].cmd.pitch = (uint16_t)svc->player.pitch;
        svc->input_baselines[slot].cmd.yaw = (uint16_t)svc->player.yaw;
        svc->input_baselines[slot].cmd.weapon = (uint16_t)svc->equip.slots[svc->equip.selected_slot].weapon;
        svc->input_baselines[slot].cmd.buttons = svc->equip.selected_slot >= 0 ? 0u : 0u;
        if (svc->player.aim_fraction > 0.0f) svc->input_baselines[slot].cmd.buttons |= CODOL_BTN_ADS;
        svc->input_baselines[slot].cmd.word34 = 2047;
        if (svc->input_baseline_count < 513) svc->input_baseline_count++;
    }
    CODOL_LOG_INFO("[battle] TX_SNAPSHOT seq=%u bytes=%d omit=%d ents=%d ong=%d mirror=%u/%u pos=%.1f,%.1f,%.1f",
                   (unsigned)seq, n, (int)omit, ent_count, (int)svc->player.on_ground,
                   svc->mirror_hits, svc->mirror_miss,
                   px, py, pz);
    return 0;
}

void codol_battle_service_tick(codol_battle_service_t *svc, uint64_t now_ms)
{
    int i;
    (void)now_ms;
    /* ★ 统一时钟: 调用方传进来的可能是 QPC 派生的毫秒, 与 gamestate_due_ms
     *   (GetTickCount64) 不同纪元 -> 比较永远不成立。这里一律用 mono_ms()。 */
    now_ms = mono_ms();
    if (!svc) return;
    for (i = 0; i < CODOL_BATTLE_MAX_PEERS; i++) {
        codol_battle_assoc_t *a = &svc->battle.peers[i];
        if (!a->in_use || !a->key_ready) continue;
        /* 运动快照: gamestateupdate 6 之后 0.5s 起, 每 25ms 一帧 */
        if (svc->snapshot_due_ms && now_ms >= svc->snapshot_due_ms) {
            send_snapshot(svc, a, now_ms);
            svc->snapshot_due_ms = now_ms + CODOL_SNAP_DT_MS;
        }
        if (svc->gamestate_loading) continue;        /* 客户端已回报进度 -> 停发 */
        if (svc->gamestate_due_ms && !svc->gamestate_sent &&
            now_ms >= svc->gamestate_due_ms && svc->gamestate_attempts < 5) {
            if (send_gamestate(svc, a) == 0) {
                svc->gamestate_sent = true;
                /* ★ 2026-11-07 (实机 run ONCE_20261107_162350): 不再等
                 *   `gamestateupdate 6` 才起快照。该 run 里客户端到「设置游戏」
                 *   后 RX_GAMESTATE_PROGRESS=0、TX_SNAPSHOT=0、每条 usercmd 的
                 *   ack 恒为 0 —— 两边互等。改为 gamestate 发出 0.5s 后即开始推
                 *   快照；原 stage==6 分支保留(同样被 !snapshot_due_ms 守卫)。 */
                if (!svc->snapshot_due_ms)
                    svc->snapshot_due_ms = mono_ms() + 500;
                CODOL_LOG_INFO("[battle] gamestate 已发 -> 0.5s 后开始推快照"
                               "(不等 gamestateupdate 6)");
            }
            svc->gamestate_due_ms = now_ms + 2000;   /* 未获进度则 2s 后重试 */
        }
    }
}

static int send_frame(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                      const uint8_t *plain, int len)
{
    uint8_t frame[2048];
    int n = codol_battle_send_data(a, plain, len, frame, sizeof(frame));
    if (n <= 0) return -1;
    svc->tx_frames++;
    {
        int rc = svc->send(svc->ctx, &a->peer, frame, n);
        CODOL_LOG_INFO("[battle] TX_DATA seq=%u plain=%dB frame=%dB rc=%d",
                       (unsigned)(a->send_seq - 1), len, n, rc);
        if (svc->tx_frames <= 3) {
            char hx[256]; int i;
            for (i = 0; i < n && i < 40; i++) sprintf(hx + i*2, "%02X", frame[i]);
            hx[(n < 40 ? n : 40) * 2] = 0;
            CODOL_LOG_INFO("[battle]  key=%02X%02X%02X%02X.. tag=%02X%02X frame_hex=%s",
                           a->transport_key[0], a->transport_key[1],
                           a->transport_key[2], a->transport_key[3],
                           a->cookie[14], a->cookie[15], hx);
        }
        return rc;
    }
}

/* OOB 应答统一封装: FF FF FF FF + text + 00, 放进加密数据帧 */
static void send_oob_text(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                          const char *text)
{
    uint8_t buf[512];
    size_t tl = strlen(text);
    buf[0] = 0xFF; buf[1] = 0xFF; buf[2] = 0xFF; buf[3] = 0xFF;
    memcpy(buf + 4, text, tl);
    buf[4 + tl] = 0;
    send_frame(svc, a, buf, (int)(5 + tl));
}

/* getchallenge 回包 —— 2026-11-07 改为回显客户端 challenge。
 *
 * 客户端出站字面量(本地逆向): "getchallenge 0 \"%s\"" @ 0x00DBF704
 *     => arg1 = 常量 0 ；arg2 = 客户端 challenge 字符串（带引号）
 * 参照 CoD4X sv_client.c:124:
 *     NET_OutOfBandPrint(..., "challengeResponse %d %d 0 xproto 18",
 *                        challenge, clientChallenge);
 * 旧实现: send_oob_text(svc, a, "challengeResponse 1")
 *     —— 常量值、不回显、无尾字段。
 *
 * A/B 开关: 环境变量 CODOL_CHALLENGE_LEGACY=1 时退回旧回包，
 * 便于在同一个 run 目录内对照，无需改代码。
 * ------------------------------------------------------------------------- */
static void handle_getchallenge(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                                const char *cmd)
{
    char arg1[32];
    char cli[112];
    char resp[192];
    uint32_t srv;
    const char *p;
    const char *env;
    size_t n;

    p = cmd + 13;                               /* 跳过 "getchallenge " */
    while (*p == ' ') p++;
    n = 0;
    while (*p && *p != ' ' && n < sizeof(arg1) - 1) arg1[n++] = *p++;
    arg1[n] = 0;

    while (*p == ' ') p++;
    if (*p == '"') p++;                         /* 去掉引号 */
    n = 0;
    while (*p && *p != '"' && *p != ' ' && n < sizeof(cli) - 1) cli[n++] = *p++;
    cli[n] = 0;

    env = getenv("CODOL_CHALLENGE_LEGACY");
    if (env && env[0] == '1') {
        CODOL_LOG_INFO("[battle] RX_GETCHALLENGE arg1=\"%s\" echo=\"%s\" "
                       "-> LEGACY \"challengeResponse 1\"", arg1, cli);
        send_oob_text(svc, a, "challengeResponse 1");
        return;
    }

    srv = (uint32_t)(mono_ms() & 0x7FFFFFFFu);
    if (srv == 0) srv = 1;

    if (cli[0]) {
        sprintf(resp, "challengeResponse %u %s 0 xproto 18", (unsigned)srv, cli);
    } else {
        /* 没有可回显的 challenge: 仍按单值形态回，避免退化成空参数 */
        sprintf(resp, "challengeResponse %u", (unsigned)srv);
    }
    CODOL_LOG_INFO("[battle] RX_GETCHALLENGE arg1=\"%s\" echo=\"%s\" srv=%u "
                   "-> \"%s\"", arg1, cli, (unsigned)srv, resp);
    send_oob_text(svc, a, resp);
}

static void handle_stats(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                         const uint8_t *plain, int len)
{
    /* 真实包形: FF FF FF FF | "stats\0" | index@10 | total(u16 LE)@11 | <chunk>@13
     * 块大小 1238B; count = ceil(total/1238)
     * 应答 "statResponse <missing 位掩码>"(bit i = 第 i 块仍缺) —— 必须逐块推进,
     * 否则客户端每毫秒重发、永不推进 -> 卡在"同步游戏设置"。 */
    uint8_t index;
    uint16_t total;
    int count, avail, n, remain, i;
    uint32_t missing = 0;
    char resp[64];

    if (len < 13) { CODOL_LOG_WARN("[battle] stats 包过短 %d", len); return; }
    index = plain[10];
    total = (uint16_t)(plain[11] | (plain[12] << 8));
    if (total < 1 || total > 32768) {
        CODOL_LOG_WARN("[battle] RX_STATS 参数非法 index=%u total=%u len=%d",
                       (unsigned)index, (unsigned)total, len);
        return;
    }
    count = (total + 1237) / 1238;
    if (index >= count) {
        CODOL_LOG_WARN("[battle] RX_STATS index 越界 %u/%d", (unsigned)index, count);
        return;
    }
    if (svc->stats_total != (size_t)total) {
        if (svc->stats_buf) free(svc->stats_buf);
        svc->stats_buf = (uint8_t *)calloc(1, (size_t)total);
        svc->stats_total = (size_t)total;
        svc->stats_chunks = 0;
    }
    avail = len - 13;
    n = avail < 1238 ? avail : 1238;
    remain = total - index * 1238;
    if (n > remain) n = remain;
    if (n > 0 && svc->stats_buf)
        memcpy(svc->stats_buf + index * 1238, plain + 13, (size_t)n);
    svc->stats_chunks |= (1u << index);

    for (i = 0; i < count; i++)
        if (!(svc->stats_chunks & (1u << i))) missing |= (1u << i);

    CODOL_LOG_INFO("[battle] RX_STATS index=%u total=%u count=%d len=%d(期望 %d) 已收块=0x%X",
                   (unsigned)index, (unsigned)total, count, len, 13 + remain,
                   (unsigned)svc->stats_chunks);

    sprintf(resp, "statResponse %u", (unsigned)missing);
    send_oob_text(svc, a, resp);
    if (missing == 0) CODOL_LOG_INFO("[battle] STATS_COMPLETE total=%u", (unsigned)total);
}
/* 普通 netchan 帧的解析路径(13 字节头 + XOR 掩码 + usercmd)。
 * FAT 分片重组完成后走的是**同一个函数** —— 重组出来的整条消息与普通帧
 * 布局完全一致(u32 序号 | u8 serverId | u32 messageAck | u32 reliableAck | 体)。 */
static void handle_netchan_frame(codol_battle_service_t *svc,
                                 const uint8_t *plain, int len)
{
    uint32_t head = (uint32_t)plain[0] | ((uint32_t)plain[1] << 8) |
                    ((uint32_t)plain[2] << 16) | ((uint32_t)plain[3] << 24);
    uint32_t ack = ((uint32_t)plain[5] | ((uint32_t)plain[6] << 8) |
                    ((uint32_t)plain[7] << 16) | ((uint32_t)plain[8] << 24)) & 0x1FFFFFFFu;
    uint8_t body[8192];
    uint8_t m = (uint8_t)((ack ^ 1 ^ plain[4]) & 0xFF);
    g_peer_serverid = plain[4];      /* ★ 抄回客户端 serverId, 下行帧原样回填 */
    int blen = len - 13, i;
    codol_usercmd_list_t list;

    CODOL_LOG_INFO("[battle] RX_CLIENT_GAME_HEADER messageAck=%u bytes=%d head=0x%08X",
                   ack, len, head);
    svc->last_rx_ms = mono_ms();

    if (blen <= 0) return;
    if (blen > (int)sizeof(body)) {
        CODOL_LOG_INFO("[battle] RX_BODY_TOO_LARGE blen=%d (上限 %d) head=0x%08X",
                       blen, (int)sizeof(body), head);
        return;
    }
    for (i = 0; i < blen; i++) body[i] = (uint8_t)(plain[13 + i] ^ m);
    {   /* 诊断: 原始 body 全量落盘(FAT 重组后的大包正是形态切换/配装类长命令
         *   最可能出现的地方, 不截断才能离线复现)。 */
        static int dbg_body = 0;
        if (dbg_body < 3000) {
            static char hx[8192 * 2 + 2];
            int j;
            if (blen > 8192) blen = 8192;
            for (j = 0; j < blen; j++) sprintf(hx + j*2, "%02X", body[j]);
            hx[blen*2] = 0;
            CODOL_LOG_INFO("[world] RX_BODY blen=%d head=0x%08X ack=%u hex=%s", blen, head, ack, hx);
            dbg_body++;
        }
    }
    {
        /* ★ 基线语义必须与参照 battle_server.py 完全一致:
         *     baseline = assoc["input_baselines"].get(ack)
         *     if baseline is None and snapshot_sent and ack > 0: raise  (拒绝, 不回退)
         *   回退到 last_cmd 会用**错误基线**硬解, 位流不报错却产垃圾
         *   (实测 yaw=59064 / weapon=142 / pitch=3725)。宁可拒绝。 */
        const codol_usercmd_t *base = NULL;
        if (ack > 0 && svc->input_baselines[ack % 513u].seq == ack)
            base = &svc->input_baselines[ack % 513u].cmd;
        else if (svc->snapshot_sent && ack > 0) {
            static int rej = 0;
            if (++rej <= 5 || rej % 100 == 0)
                CODOL_LOG_INFO("[world] REJECT_USERCMD ack=%u (无匹配基线, 共 %d 次)",
                               ack, rej);
            return;
        }
        if (!codol_usercmd_parse(body, blen, ack, base, &list))
            return;
    }

    /* ★ 先消费可靠命令(背包选择等)。
     *   CODOL 把 "mr 1 1 custom1/custom2" 放在 opcode==2 段;
     *   之前这些文本被直接丢弃 -> 服务端不知道背包选择。 */
    if (list.reliable_count > 0) {
        int r;
        for (r = 0; r < list.reliable_count; r++) {
            const char *cmd = list.reliable[r];
            bool changed = codol_equipment_select_backpack(&svc->equip, cmd);
            CODOL_LOG_INFO("[world] RELIABLE cmd=\"%s\" backpack_changed=%d slot_count=%d current=%d",
                           cmd, (int)changed, svc->equip.slot_count,
                           svc->equip.current_weapon);
        }
    }
    if (list.count > 0) {
        int k, applied = 0;
        for (k = 0; k < list.count; k++) {
            codol_usercmd_t *cm = &list.cmds[k];
            uint32_t elapsed;
            /* 照参照实现: 首帧前全处理; 之后只处理比
             * processed_input_time 更新的命令(netchan 会重发,
             * 不去重会把开火/换弹/移动重复计数)。 */
            if (svc->snapshot_sent && cm->time <= svc->processed_input_time) continue;
            elapsed = (cm->time - svc->processed_input_time) & 0xFFFFFFFFu;
            if (elapsed > 200u) elapsed = 200u;
            svc->processed_input_time = cm->time;
            if (codol_equipment_step(&svc->equip, cm, (int)elapsed)) {
                svc->weapon_fires++;
                if (svc->weapon_fires <= 5 || svc->weapon_fires % 20 == 0)
                    CODOL_LOG_INFO("[world] FIRE #%u weapon=%d clip=%d reserve=%d t=%u",
                                   svc->weapon_fires, svc->equip.slots[svc->equip.selected_slot].weapon,
                                   svc->equip.slots[svc->equip.selected_slot].clip,
                                   svc->equip.slots[svc->equip.selected_slot].reserve,
                                   cm->time);
                apply_test_hit(svc, ensure_damage_target(svc));
            }
            /* ★ 按键标定(2026-10-22): 每条 usercmd 原始值写 CSV。
             *   用于反推 CODOL 3.19 的 buttons 位定义。 */
            {
                static FILE *km = NULL;
                static int km_init = 0;
                if (!km_init) {
                    km = fopen("keymap_cal.csv", "w");
                    km_init = 1;
                    if (km) fprintf(km, "time,buttons,weapon,fwd,right,yaw,pitch,roll\n");
                }
                if (km) {
                    fprintf(km, "%u,0x%08X,%u,%d,%d,%u,%u,%u\n",
                            cm->time, cm->buttons, cm->weapon,
                            (int)cm->forwardmove, (int)cm->rightmove,
                            cm->yaw, cm->pitch, cm->roll);
                    fflush(km);
                }
            }
            codol_battle_service_apply_usercmd(svc, cm, elapsed);
            applied++;
        }
        if (applied > 0) {
            svc->rx_usercmd += applied;
            if (svc->rx_usercmd <= 5 || svc->rx_usercmd % 100 == 0)
                CODOL_LOG_INFO("[world] USERCMD n=%d time=%u yaw=%d pitch=%d F=%d R=%d btn=0x%X W=%d pos=%.1f,%.1f,%.1f",
                               list.count, list.cmds[list.count-1].time,
                               (int)list.cmds[list.count-1].yaw,
                               (int)list.cmds[list.count-1].pitch,
                               (int)list.cmds[list.count-1].forwardmove,
                               (int)list.cmds[list.count-1].rightmove,
                               (unsigned)list.cmds[list.count-1].buttons,
                               (int)list.cmds[list.count-1].weapon,
                               svc->player.x, svc->player.y, svc->player.z);
        }
    }
    if (list.count > 0) {
        svc->last_cmd = list.cmds[list.count - 1];
        svc->have_last_cmd = true;
    }
    codol_frame_history_ack(&svc->history, ack);
}

static void handle_plain(codol_battle_service_t *svc, codol_battle_assoc_t *a,
                         const uint8_t *plain, int len)
{
    char cmd[256];
    int i;

    if (len >= 4 && plain[0] == 0xFF && plain[1] == 0xFF &&
        plain[2] == 0xFF && plain[3] == 0xFF) {
        svc->rx_oob++;
        for (i = 0; i < (int)sizeof(cmd) - 1 && 4 + i < len && plain[4 + i]; i++)
            cmd[i] = (char)plain[4 + i];
        cmd[i] = 0;
        CODOL_LOG_INFO("[battle] RX_OOB cmd='%s'", cmd);

        if (strncmp(cmd, "stats", 5) == 0) { handle_stats(svc, a, plain, len); return; }
        if (strncmp(cmd, "getchallenge ", 13) == 0) { handle_getchallenge(svc, a, cmd); return; }
        if (strncmp(cmd, "connect ", 8) == 0) {
            /* ★ 取客户端自报的关卡校验值: userinfo 里 `\checksum\-694791800\` */
            {
                const char *k = strstr(cmd, "\\checksum\\");
                if (k) {
                    long v = strtol(k + 10, NULL, 10);
                    g_peer_checksum = (uint32_t)v;
                    g_peer_checksum_valid = 1;
                    CODOL_LOG_INFO("[battle] connect userinfo checksum=%ld (0x%08X) -> 回填 gamestate",
                                   v, (unsigned)g_peer_checksum);
                } else {
                    CODOL_LOG_WARN("[battle] connect userinfo 里没有 \\checksum\\, gamestate 校验字段保持原值");
                }
            }
            send_oob_text(svc, a, "connectResponse");
            return;                       /* 调度交给 netchan 帧触发 */
        }
        if (strcmp(cmd, "heartbeat") == 0)          { send_oob_text(svc, a, "heartbeatresponse"); return; }
        if (strncmp(cmd, "gamestateupdate ", 16) == 0) {
            CODOL_LOG_INFO("[battle] RX_GAMESTATE_PROGRESS stage=%s", cmd + 16);
            svc->gamestate_loading = true;       /* 收到进度 => 停止重发 */
            {
                int stage = atoi(cmd + 16);
                if (stage == 6 && !svc->snapshot_due_ms) {
                    svc->snapshot_due_ms = mono_ms() + 500;   /* 0.5s 后开始推快照 */
                    CODOL_LOG_INFO("[battle] 准备推送运动快照(stage 6)");
                }
            }
            return;                              /* 无应答 */
        }
        if (strncmp(cmd, "cancelConnect", 13) == 0) {
            CODOL_LOG_INFO("[battle] RX_CANCEL_CONNECT");
            return;
        }
        return;
    }

    /* 客户端 netchan 帧 */
    if (len >= 14) {
        uint32_t head = (uint32_t)plain[0] | ((uint32_t)plain[1] << 8) |
                        ((uint32_t)plain[2] << 16) | ((uint32_t)plain[3] << 24);
        uint32_t ack = ((uint32_t)plain[5] | ((uint32_t)plain[6] << 8) |
                        ((uint32_t)plain[7] << 16) | ((uint32_t)plain[8] << 24)) & 0x1FFFFFFFu;
        CODOL_LOG_INFO("[battle] RX_CLIENT_GAME_HEADER messageAck=%u bytes=%d head=0x%08X",
                       ack, len, head);
        svc->last_rx_ms = mono_ms();

        /* ★ CODOL 3.19 分片(FAT)帧。旧代码在这里直接跳过 -> FAT 之后零 usercmd,
         *   这就是交接文档里的阻断点。现在按 index/last/stride/length 重组,
         *   收全后走**与普通帧完全相同**的解析路径(handle_netchan_frame)。
         *   布局依据见 codol_types.h 的 CODOL_FAT_* 常量块。 */
        if (head & CODOL_FAT_BIT) {
            uint8_t ctl[64];
            int ctl_len = 0;
            int fn = codol_fat_receive(&a->fat, plain, len, ctl, sizeof(ctl), &ctl_len);
            a->fat_frames++;
            svc->last_rx_ms = mono_ms();
            if (fn < 0) {
                a->fat_invalid++;
                if (a->fat_invalid <= 5 || a->fat_invalid % 200 == 0)
                    CODOL_LOG_INFO("[battle] RX_FAT_INVALID head=0x%08X bytes=%d (累计 %u)",
                                   head, len, a->fat_invalid);
            } else {
                if (ctl_len > 0) svc->send(svc->ctx, &a->peer, ctl, ctl_len);
                if (a->fat_frames <= 8 || a->fat_frames % 500 == 0)
                    CODOL_LOG_INFO("[battle] RX_FAT_FRAGMENT head=0x%08X seq=%u idx=%u last=%u stride=%u frag_len=%u bytes=%d %s",
                                   head, head & CODOL_FAT_SEQ_MASK, plain[4], plain[5],
                                   (unsigned)(plain[6] | (plain[7] << 8)),
                                   (unsigned)(plain[8] | (plain[9] << 8)), len,
                                   fn > 0 ? "收全" : "待续");
                if (fn > 0) {
                    a->fat_reassembled++;
                    CODOL_LOG_INFO("[battle] RX_FAT_REASSEMBLED seq=%u total=%d (累计 %u)",
                                   head & CODOL_FAT_SEQ_MASK, fn, a->fat_reassembled);
                    handle_netchan_frame(svc, a->fat.buffer, fn);
                }
            }
        } else {

        /* ---- 普通帧: World 层解析 usercmd 并推进玩家(内部移动模型) ---- */
            uint8_t body[2048];
            uint8_t m = (uint8_t)((ack ^ 1 ^ plain[4]) & 0xFF);
    g_peer_serverid = plain[4];      /* ★ 抄回客户端 serverId, 下行帧原样回填 */
            int blen = len - 13, i;
            codol_usercmd_list_t list;
            if (blen > 0 && blen <= (int)sizeof(body)) {
                for (i = 0; i < blen; i++) body[i] = (uint8_t)(plain[13 + i] ^ m);
                {   /* 诊断: 原始 body 全量落盘(不截断, 见 handle_netchan_frame 同名注释) */
                    static int dbg_body = 0;
                    if (dbg_body < 3000) {
                        static char hx[4096 * 2 + 2];
                        int j;
                        for (j = 0; j < blen; j++) sprintf(hx + j*2, "%02X", body[j]);
                        hx[blen*2] = 0;
                        CODOL_LOG_INFO("[world] RX_BODY blen=%d head=0x%08X ack=%u hex=%s", blen, head, ack, hx);
                        dbg_body++;
                    }
                }
                {
                    /* 基线语义与参照一致: 精确 ack 匹配, 缺失即拒绝(不回退 last_cmd) */
                    const codol_usercmd_t *base = NULL;
                    bool ok;
                    if (ack > 0 && svc->input_baselines[ack % 513u].seq == ack)
                        base = &svc->input_baselines[ack % 513u].cmd;
                    else if (svc->snapshot_sent && ack > 0) {
                        static int rej = 0;
                        if (++rej <= 5 || rej % 100 == 0)
                            CODOL_LOG_INFO("[world] REJECT_USERCMD ack=%u (无匹配基线, 共 %d 次)",
                                           ack, rej);
                        return;
                    }
                    ok = codol_usercmd_parse(body, blen, ack, base, &list);
                    if (!ok && ack == 0 && blen == 1) ok = true;  /* 首帧空包 */
                    if (!ok) return;
                }
                if (list.count + list.reliable_count > 0) {
                    /* ★ 先消费可靠命令(背包选择等)。
                     *   CODOL 把 "mr 1 1 custom1/custom2" 放在 opcode==2 段;
                     *   之前这些文本被直接丢弃 -> 服务端不知道背包选择。 */
                    if (list.reliable_count > 0) {
                        int r;
                        for (r = 0; r < list.reliable_count; r++) {
                            const char *cmd = list.reliable[r];
                            bool changed = codol_equipment_select_backpack(&svc->equip, cmd);
                            CODOL_LOG_INFO("[world] RELIABLE cmd=\"%s\" backpack_changed=%d slot_count=%d current=%d",
                                           cmd, (int)changed, svc->equip.slot_count,
                                           svc->equip.current_weapon);
                        }
                    }
                    if (list.count > 0) {
                        int k, applied = 0;
                        for (k = 0; k < list.count; k++) {
                            codol_usercmd_t *cm = &list.cmds[k];
                            uint32_t elapsed;
                            /* 照参照实现: 首帧前全处理; 之后只处理比
                             * processed_input_time 更新的命令(netchan 会重发,
                             * 不去重会把开火/换弹/移动重复计数)。 */
                            if (svc->snapshot_sent && cm->time <= svc->processed_input_time) continue;
                            elapsed = (cm->time - svc->processed_input_time) & 0xFFFFFFFFu;
                            if (elapsed > 200u) elapsed = 200u;
                            svc->processed_input_time = cm->time;
                            if (codol_equipment_step(&svc->equip, cm, (int)elapsed)) {
                                svc->weapon_fires++;
                                if (svc->weapon_fires <= 5 || svc->weapon_fires % 20 == 0)
                                    CODOL_LOG_INFO("[world] FIRE #%u weapon=%d clip=%d reserve=%d t=%u",
                                                   svc->weapon_fires, svc->equip.slots[svc->equip.selected_slot].weapon,
                                                   svc->equip.slots[svc->equip.selected_slot].clip,
                                                   svc->equip.slots[svc->equip.selected_slot].reserve,
                                                   cm->time);
                                apply_test_hit(svc, ensure_damage_target(svc));
                            }
                            /* ★ 按键标定(2026-10-22): 每条 usercmd 原始值写 CSV。
                             *   用于反推 CODOL 3.19 的 buttons 位定义。 */
                            {
                                static FILE *km = NULL;
                                static int km_init = 0;
                                if (!km_init) {
                                    km = fopen("keymap_cal.csv", "w");
                                    km_init = 1;
                                    if (km) fprintf(km, "time,buttons,weapon,fwd,right,yaw,pitch,roll\\n");
                                }
                                if (km) {
                                    fprintf(km, "%u,0x%08X,%u,%d,%d,%u,%u,%u\n",
                                            cm->time, cm->buttons, cm->weapon,
                                            (int)cm->forwardmove, (int)cm->rightmove,
                                            cm->yaw, cm->pitch, cm->roll);
                                    fflush(km);
                                }
                                /* ★ 形态切换抓包: 只要 weapon / word22 / word24 变化就单独记一行。
                                 *   自由荣耀的"变形"若走 usercmd 字段, 必然在这里留下痕迹。 */
                                {
                                    static uint16_t pw = 0xFFFF, p22 = 0xFFFF, p24 = 0xFFFF;
                                    if (pw == 0xFFFF) { pw = cm->weapon; p22 = cm->word22; p24 = cm->word24; }
                                    if (cm->weapon != pw || cm->word22 != p22 || cm->word24 != p24) {
                                        CODOL_LOG_INFO("[world] CMD_FIELD_CHANGE t=%u weapon=%u->%u "
                                                       "word22=%u->%u word24=%u->%u btn=0x%X",
                                                       cm->time, pw, cm->weapon, p22, cm->word22,
                                                       p24, cm->word24, cm->buttons);
                                        pw = cm->weapon; p22 = cm->word22; p24 = cm->word24;
                                    }
                                }
                            }
                            codol_battle_service_apply_usercmd(svc, cm, elapsed);
                            applied++;
                        }
                        if (applied > 0) {
                            svc->rx_usercmd += applied;
                            if (svc->rx_usercmd <= 5 || svc->rx_usercmd % 100 == 0)
                                CODOL_LOG_INFO("[world] USERCMD n=%d time=%u yaw=%d pitch=%d F=%d R=%d btn=0x%X W=%d pos=%.1f,%.1f,%.1f",
                                               list.count, list.cmds[list.count-1].time,
                                               (int)list.cmds[list.count-1].yaw,
                                               (int)list.cmds[list.count-1].pitch,
                                               (int)list.cmds[list.count-1].forwardmove,
                                               (int)list.cmds[list.count-1].rightmove,
                                               (unsigned)list.cmds[list.count-1].buttons,
                                               (int)list.cmds[list.count-1].weapon,
                                               svc->player.x, svc->player.y, svc->player.z);
                        }
                    }
                    /* ★ 解析成功后立即把本批最后一条命令记为 last_cmd。
                     *   参照 `read_input` 的 old=c 在循环内推进, 下一批的 baseline
                     *   就是上一批的最后一条 —— 与是否 applied 无关。之前只在
                     *   apply_usercmd 内更新, 被 continue 跳过的命令不更新,
                     *   time 跳变后基线便与客户端脱节, 整批解码失步。 */
                    if (list.count > 0) {
                        svc->last_cmd = list.cmds[list.count - 1];
                        svc->have_last_cmd = true;
                    }
                    codol_frame_history_ack(&svc->history, ack);
                }
            }
        }
        /* ★ 照参照实现: 收到 netchan 帧 => 客户端已就绪, 调度 game state */
        if (!svc->gamestate_sent && !svc->gamestate_due_ms && !svc->gamestate_loading)
            svc->gamestate_due_ms = mono_ms() + 200;
    }
}

/* RX 取证的日志预算 —— 只管握手期, 进图后每秒几十帧不再刷日志 */
static int rx_log_budget = 1200;

void codol_battle_service_on_packet(codol_battle_service_t *svc,
                                    const codol_netadr_t *from,
                                    const uint8_t *pkt, int len)
{
    uint8_t reply[2048];
    uint8_t plain[2048];
    int n;
    codol_battle_assoc_t *a;

    if (!svc || !from || !pkt || len <= 0) return;

    /* ★ RX 全量取证(2026-11-05): 客户端卡"等待连接"时必须看到它到底发了什么。
     *   握手类报文(≤256B: 29B NAT / 16B init / 219B 密钥交换)**整条**打成 hex ——
     *   这样抓一轮就能把真机报文固化成**离线回放测试**(见 tests/test_battle.c),
     *   之后改战斗服不必再开游戏。
     *   ★ 预算上限: 握手期够看就行, 否则进图后每秒几十帧会把日志刷爆。 */
    if (rx_log_budget > 0) {
        char rhx[1024];
        int rj, rn = len <= 256 ? len : 48;
        rx_log_budget--;
        if (len <= 256) {
            for (rj = 0; rj < rn; rj++) sprintf(rhx + rj * 2, "%02X", pkt[rj]);
            rhx[rn * 2] = 0;
            /* ★ 带上来源地址: 客户端进程的 UDP socket 实测绑在 0.0.0.0:22011,
             *   这里要确认握手包的**来源 IP:端口**与我们回包的目的一致。 */
            CODOL_LOG_INFO("[battle] RX %dB FULL %s  from=%u.%u.%u.%u:%u", len, rhx,
                           (unsigned)from->ip[0], (unsigned)from->ip[1],
                           (unsigned)from->ip[2], (unsigned)from->ip[3],
                           (unsigned)from->port);
        } else {
            for (rj = 0; rj < rn; rj++) sprintf(rhx + rj * 2, "%02X", pkt[rj]);
            rhx[rn * 2] = 0;
            CODOL_LOG_INFO("[battle] RX %dB head48 %s ...", len, rhx);
        }
    }

    /* ① NAT 遍历 */
    n = codol_battle_try_nat_reply(&svc->battle, from, pkt, len, reply, sizeof(reply));
    if (n > 0) {
        svc->rx_nat++;
        svc->send(svc->ctx, from, reply, n);
        CODOL_LOG_INFO("[battle] TX_NAT_REPLY %dB", n);
        return;
    }

    /* ② DTLS init */
    n = codol_battle_try_init_ack(&svc->battle, from, pkt, len, reply, sizeof(reply));
    if (n > 0) {
        svc->rx_init++;
        svc->send(svc->ctx, from, reply, n);
        CODOL_LOG_INFO("[battle] TX_DTLS_INIT_ACK %dB", n);
        return;
    }

    /* ③ 密钥交换 */
    n = codol_battle_try_key_exchange_ack(&svc->battle, from, pkt, len, reply, sizeof(reply));
    if (n == 0 && len == 219 && pkt[0] == 3 && pkt[1] == 2) {
        /* ★ 219B 形状正确却被判据拒掉 —— 把关键字段打出来, 一轮就能定位是哪一条不符 */
        codol_battle_assoc_t *ka = codol_battle_find(&svc->battle, from);
        unsigned long long ksid = 0;
        int i;
        for (i = 7; i >= 0; i--) ksid = (ksid << 8) | pkt[111 + i];
        CODOL_LOG_WARN("[battle] KX_REJECT 219B: tag got=%02X%02X want=%02X%02X "
                       "sid got=%016llX want=%016llX assoc=%s",
                       pkt[2], pkt[3],
                       ka ? ka->cookie[14] : 0, ka ? ka->cookie[15] : 0,
                       ksid, ka ? (unsigned long long)ka->session_id : 0ULL,
                       ka ? "有" : "无");
    }
    if (n > 0) {
        svc->rx_keyex++;
        svc->send(svc->ctx, from, reply, n);
        CODOL_LOG_INFO("[battle] KEY_EXCHANGE_OK -> TX_DTLS_KEY_EXCHANGE_ACK %dB", n);
        /* ★★ 每连接重置 game-state 调度状态。
         *   这些字段放在服务结构里是**全局**的: 第一次连接成功后 gamestate_sent=true,
         *   客户端一重连(新会话)就再也拿不到 game state -> 卡在"设置游戏"。
         *   密钥交换每连接只成功一次, 在这里重置最稳。 */
        svc->gamestate_sent = false;
        svc->gamestate_loading = false;
        svc->gamestate_attempts = 0;
        svc->gamestate_due_ms = 0;
        svc->netchan_seq = 1;
        /* ★★ 2026-10-24 补漏: 这里原先**没有**重置快照状态, 导致"第二轮再进卡等待玩家数据"。
         *   症状链(SPAWNAUTH_20261024_1420 实测):
         *     第二次连接 seq 从 1 重新开始(上面那行), 但 `snapshot_sent` 仍是 true
         *     ⇒ `first = !svc->snapshot_sent` 恒为 false ⇒ **新会话的第一帧不是首帧**;
         *     而 §15 的位序要求: 首帧的头部是 `first=1 / flags=0x08`, 且 §13.5 的首帧契约
         *     (baseline bit / 各段) 也依赖 `first`。新会话收到一帧"非首帧"就建不起基线
         *     ⇒ 卡在"等待玩家数据"。
         *   另两个也必须重置:
         *     · `snapshot_epoch_ms` —— 否则 serverTime 从上一会话延续(实测第二会话
         *       seq=1 的 serverTime 已是 30 秒量级), 客户端按"刚开局"对时间会错位;
         *     · `snapshot_due_ms` —— 否则沿用旧调度。 */
        svc->snapshot_sent = false;
        svc->snapshot_epoch_ms = 0;
        svc->snapshot_due_ms = 0;
        /* 输入侧同理: 新会话客户端从 time=0 重新开始发 usercmd, 旧的高水位会把它们全吃掉。 */
        svc->processed_input_time = 0;
        svc->have_last_cmd = false;
        /* 分片重组状态也按连接重置: 重连后客户端序号回到 1,
         * 残留的半条消息会挡住新会话的第一条分片。 */
        {
            codol_battle_assoc_t *ka = codol_battle_find(&svc->battle, from);
            if (ka) { codol_fat_reset(&ka->fat); ka->fat_frames = ka->fat_reassembled = ka->fat_invalid = 0; }
        }
        /* 另: 这里**不**调度 game state —— 参照实现是等客户端发来 netchan 帧
         * 之后才 ready, 再等 0.2s 下发; 提前发客户端会丢弃。 */
        return;
    }

    /* ④ 保活帧(type 7): 客户端状态泵 0xBBEA80 在握手完成后按 [+0x5d8] 周期发送,
     *    接收处理器 0xBB4593 什么都不做 ⇒ 服务端静默忽略, 只推进收帧序号。
     *    (若不单独处理, 会被当成"数据帧解不开"计入 RX_DROP, 污染日志。) */
    if (len >= 6 && pkt[0] == 7 && pkt[1] == 2) {
        codol_battle_assoc_t *ka = codol_battle_find(&svc->battle, from);
        if (ka && ka->key_ready) codol_battle_note_keepalive(ka, pkt, len);
        return;
    }

    /* ⑤ 数据帧 */
    a = codol_battle_find(&svc->battle, from);
    if (!a || !a->key_ready) {
        if (rx_log_budget > 0) {
            rx_log_budget--;
            /* ★ 2026-11-07 诊断(run ONCE_20261107_163342): gamestate 发完之后,
             *   同一 from 的来帧突然 find 不到关联。in_use 全库只在 battle.c:118
             *   置 true、从不清零, codol_battle_init 也只在启动调一次 ⇒ 表没被重置,
             *   所以要看清到底是 type 不匹配, 还是 from 本身换了来源。 */
            {
                int _k, _live = 0;
                static int _dbg_dump = 0;
                for (_k = 0; _k < CODOL_BATTLE_MAX_PEERS; _k++)
                    if (svc->battle.peers[_k].in_use) _live++;
                CODOL_LOG_INFO("[battle] RX_DROP 未握手(assoc=%s key_ready=%d) %dB "
                               "incoming{type=%d port=%u} live_peers=%d",
                               a ? "有" : "无", a ? (int)a->key_ready : 0, len,
                               (int)from->type, (unsigned)from->port, _live);
                if (_dbg_dump < 4) {
                    _dbg_dump++;
                    for (_k = 0; _k < CODOL_BATTLE_MAX_PEERS; _k++) {
                        if (!svc->battle.peers[_k].in_use) continue;
                        CODOL_LOG_INFO("[battle]   peer[%d] type=%d port=%u key_ready=%d "
                                       "ip=%u.%u.%u.%u (ip[4..7]=%02X %02X %02X %02X)",
                                       _k,
                                       (int)svc->battle.peers[_k].peer.type,
                                       (unsigned)svc->battle.peers[_k].peer.port,
                                       (int)svc->battle.peers[_k].key_ready,
                                       (unsigned)svc->battle.peers[_k].peer.ip[0],
                                       (unsigned)svc->battle.peers[_k].peer.ip[1],
                                       (unsigned)svc->battle.peers[_k].peer.ip[2],
                                       (unsigned)svc->battle.peers[_k].peer.ip[3],
                                       (unsigned)svc->battle.peers[_k].peer.ip[4],
                                       (unsigned)svc->battle.peers[_k].peer.ip[5],
                                       (unsigned)svc->battle.peers[_k].peer.ip[6],
                                       (unsigned)svc->battle.peers[_k].peer.ip[7]);
                    }
                }
            }
        }
        return;
    }
    n = codol_battle_read_data(a, pkt, len, plain, sizeof(plain));
    if (n < 0) {
        if (rx_log_budget > 0) {
            rx_log_budget--;
            CODOL_LOG_INFO("[battle] RX_DROP 数据帧解不开 %dB", len);
        }
        return;
    }
    svc->rx_data++;
    handle_plain(svc, a, plain, n);
}
