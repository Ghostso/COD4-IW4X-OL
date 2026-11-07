#ifndef CODOL_BATTLE_SERVICE_H
#define CODOL_BATTLE_SERVICE_H
/* 战斗服接线层: UDP 收包 -> NAT/握手 -> 数据帧 -> OOB 分发 -> 回包。
 * 把 battle.c(外层) 与传输层连起来, 使真实客户端能完成握手并发命令。 */
#include "codol_types.h"
#include "codol_battle.h"
#include "codol_player.h"
#include "codol_frame_history.h"
#include "codol_equipment.h"

#ifdef __cplusplus
extern "C" {
#endif
/* ===================== 验证状态台账(不得把推断当结论) =====================
 * 【已在真实客户端上验证】
 *   · NAT/DTLS/密钥交换/stats/game state/netchan 全链路走通
 *   · usercmd 解析: [world] USERCMD 出现, time 递增, yaw/pitch 随转头变化, F/R 随按键变化;
 *     且与参照读取器在 16 条真实 body 字节上 16/16 一致
 *   · 出生点 (48,-572,-116) 已实测**错误** -> 改为不发自算位置/改镜像客户端预测态
 * 【未验证 / 待本轮结论】
 *   · 穿墙、速度异常、方向异常 —— 上一轮因出生点卡死**根本没测到**, 不算解决
 *   · 开镜/开火/换弹/弹药 —— 代码已补(照参照)并有单体测试, 但**未在客户端验证**
 *   · 小地图/角色外观/背包武器 —— 仍受固定模板影响, 未修
 * ==================================================================== */

typedef int (*codol_battle_sendto_fn)(void *ctx, const codol_netadr_t *to,
                                      const uint8_t *data, int len);

typedef struct {
    codol_battle_t       battle;
    void                *ctx;
    codol_battle_sendto_fn send;
    unsigned rx_nat, rx_init, rx_keyex, rx_data, rx_oob;
    unsigned tx_frames;
    /* game state / snapshot 调度 */
    uint64_t gamestate_due_ms;
    bool     gamestate_sent;
    bool     gamestate_loading;
    unsigned gamestate_attempts;
    uint32_t netchan_seq;
    uint64_t last_rx_ms;
    char     gamestate_path[512];
    /* stats 分块上传状态 */
    uint8_t *stats_buf;
    size_t   stats_total;
    uint32_t stats_chunks;
    /* 运动快照调度 */
    uint64_t snapshot_due_ms;
    uint64_t snapshot_epoch_ms;
    bool     snapshot_sent;
    /* World 层状态(手册 §5.1: 本层不知道 socket 细节) */
    codol_player_t          player;
    codol_world_t          *world;       /* optional authoritative world */
    int                     world_client;
    codol_frame_history_t   history;
    codol_usercmd_t         last_cmd;      /* 供 delta 基线(兼容保留) */
    bool                    have_last_cmd;
    /* ★ 按 ack 索引的输入基线表 —— 与参照 battle_server.py 的
     *   `assoc["input_baselines"][ack]` 语义一致: 客户端用"某条快照的 ack"
     *   作为 usercmd delta 的基线, 我们必须存下每条快照对应的基线,
     *   而不是只留最后一条命令(那样在 time 跳变/丢帧后必然失步)。 */
    struct {
        uint32_t          seq;
        codol_usercmd_t   cmd;
    }                       input_baselines[513];
    int                     input_baseline_count;
    unsigned rx_usercmd;
    /* 装备/开火/换弹状态机(照参照 _Equipment) + 输入去重时刻 */
    codol_equipment_t       equip;
    uint32_t                processed_input_time;
    unsigned                weapon_fires;
    /* 快照帧基线(◁ 本协议每字段写 to^from) */
    codol_snap_state_t      snap_from;
    codol_snap_state_t      snap_cur;
    /* 镜像客户端自己的预测态(nt10 --ps-probe 写出的 predicted.bin):
     *   有数据 -> 原样回发(位置+速度); 无数据 -> **连首帧也不发位置**,
     *   避免用错误出生点把人塞进房顶。 */
    char                    predicted_path[512];
    unsigned                mirror_hits;
    unsigned                mirror_miss;
    /* 实体段开关: 该文件存在 = 发 entityState 段; 不存在 = 不发(默认关)。
     * 仿照 gamestate_path / predicted_path: 路径在 init 里写死, 运行时可被决策覆盖。 */
    char                    entities_flag_path[512];
} codol_battle_service_t;

void codol_battle_service_init(codol_battle_service_t *svc, void *ctx,
                               codol_battle_sendto_fn send);
void codol_battle_service_bind_world(codol_battle_service_t *svc,
                                     codol_world_t *world, int client_num);
codol_result_t codol_battle_service_apply_usercmd(codol_battle_service_t *svc,
                                                  const codol_usercmd_t *cmd,
                                                  uint32_t elapsed_ms);

/* 处理一个收到的 UDP 包(来自 from)。内部完成全部应答。 */
/* 由主循环周期性调用(毫秒时钟), 负责下发 game state / 快照 */
void codol_battle_service_tick(codol_battle_service_t *svc, uint64_t now_ms);

/* 处理一个收到的 UDP 包(来自 from)。内部完成全部应答。 */
void codol_battle_service_on_packet(codol_battle_service_t *svc,
                                    const codol_netadr_t *from,
                                    const uint8_t *pkt, int len);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_BATTLE_SERVICE_H */
