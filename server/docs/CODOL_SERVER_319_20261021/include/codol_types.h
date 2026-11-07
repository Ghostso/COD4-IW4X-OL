#ifndef CODOL_TYPES_H
#define CODOL_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef int32_t  codol_result_t;
#define CODOL_OK               0
#define CODOL_ERR_GENERIC     -1
#define CODOL_ERR_INVALID_ARG -2
#define CODOL_ERR_NO_MEMORY   -3
#define CODOL_ERR_NO_EVIDENCE -4
#define CODOL_ERR_WIRE_REJECT -5
#define CODOL_ERR_STATE       -6
#define CODOL_ERR_IO          -7

#define CODOL_TARGET_VERSION      "3.19"
#define CODOL_TARGET_BUILD        "1649370"
#define CODOL_CLIENT_SHA256_PREFIX "36997674"

#define CODOL_MAX_PACKET_SIZE     1400
#define CODOL_MAX_CLIENTS         18
#define CODOL_MAX_ENTITIES        1024
#define CODOL_MAX_CONFIGSTRINGS   2442
#define CODOL_MAX_RELIABLE_CMDS   64
#define CODOL_SNAPSHOT_HISTORY    32
#define CODOL_SERVER_TICK_HZ      128
#define CODOL_SNAPSHOT_RATE_HZ    128

typedef struct codol_netadr {
    int      type;
    uint8_t  ip[16];
    uint16_t port;
    uint32_t scope_id;
} codol_netadr_t;



typedef struct codol_trajectory {
    float origin[3];
    float angles[3];
    float velocity[3];
} codol_trajectory_t;

typedef struct codol_entity_state {
    int                 number;
    int                 type;
    bool                in_use;
    codol_trajectory_t  pos;
    codol_trajectory_t  apos;
    int                 owner;
    int                 model_index;
    int                 weapon;
    int                 health;
    uint32_t            flags;
    float               mins[3];
    float               maxs[3];
} codol_entity_state_t;

typedef struct codol_player_state {
    int     client_num;
    int     command_time;
    int     pm_type;
    int     pm_flags;
    float   origin[3];
    float   velocity[3];
    int     weapon_state;
    int     view_angles[3];
    int     health;
    int     max_health;
    int     score;
    int     deaths;
    int     team;
    char    name[32];
} codol_player_state_t;

typedef struct codol_snapshot {
    codol_entity_state_t entities[CODOL_MAX_ENTITIES];
    codol_player_state_t players[CODOL_MAX_CLIENTS];
    uint32_t            frame_number;
    uint64_t            server_time;
    uint32_t            snap_flags;
} codol_snapshot_t;

typedef struct codol_snapshot_history {
    codol_snapshot_t snapshots[CODOL_SNAPSHOT_HISTORY];
    int              head;
    int              count;
} codol_snapshot_history_t;


typedef struct codol_message_header {
    uint16_t opcode;
    uint32_t sequence;
    uint32_t ack;
    const uint8_t *payload;
    size_t   payload_len;
} codol_message_header_t;

typedef struct codol_frame {
    uint32_t frame_number;
    uint64_t server_time;
    int      num_entities;
    int      first_entity;
} codol_frame_t;

typedef struct codol_message {
    codol_message_header_t header;
    uint8_t                decoded[4096];
    size_t                 decoded_len;
} codol_message_t;

/* netchan —— 结构照 IW4 引擎(经 IW4X Game/Structs.hpp:7119 确认);
 * 行为照 CoD4x src/netchan.c。★ IW4 用单个 int qport, 无 CoD4x 的 upperqport。 */
#define CODOL_NETCHAN_MAX_PACKETLEN 1400
#define CODOL_NETCHAN_FRAGMENT_SIZE (CODOL_NETCHAN_MAX_PACKETLEN - 100)
#define CODOL_NETCHAN_FRAGMENT_BIT  0x80000000u

/* ---- CODOL 3.19 客户端分片(FAT)布局 --------------------------------------
 * 与 CoD4x(IW3) 的 "qport + fragmentStart(4) + fragmentLength(2)" 老布局
 * **不同**。真实布局由 ol-mod 的 net_chan_mp.cpp 给出(其 CODREF 指向
 * CODOL Netchan_Process 0x005A5960):
 *
 *   head u32 LE : 序号(29 位, mask 0x1FFFFFFF) | 标志
 *                 0x80000000 = 分片
 *                 0x40000000 = 分片且要求分片确认
 *                 0x20000000 = 分片确认包(服务端->客户端的应答)
 *   [4]  u8     : fragmentIndex
 *   [5]  u8     : lastFragmentIndex
 *   [6]  u16 LE : fragmentStride   (恒 = 1154)
 *   [8]  u16 LE : fragmentLength   (本片负载字节数)
 *   [10] ...    : 负载
 *
 * 分片只切 "序号之后的整条消息", 并且**不含 serverId**(它落在负载里)。
 * 重组 = u32(序号) ‖ 各片负载按 index*stride 拼接, 之后按普通帧那套
 * 13 字节头(serverId(1)+messageAck(4)+reliableAck(4))解析。
 *
 * 交叉验算(基线 run 的 _c_battle_out.txt, 普通帧 seq 0x426 = 1153B 不分片,
 * 下一帧 seq 0x427 变 FAT):
 *   大包 bytes=1164 -> fragmentLength = 1164-10 = 1154 = stride, index=0
 *   同 seq 小包 bytes=20 -> fragmentLength = 10, lastFragmentIndex = 1
 *   消息 = 4 + 1154 + 10 = 1168B  (post-seq 1164 >= 1154 => 触发分片, 自洽)
 * 另: 旧代码把 [5..8] 当 messageAck 读并 &0x1FFFFFFF, 恰好只剩 fragmentLength
 * 的低 5 位 —— 这就是之前观察到 "(bytes-10) mod 32" 规律的原因。 */
#define CODOL_FAT_BIT            0x80000000u  /* 分片消息 */
#define CODOL_FAT_RELIABLE_BIT   0x40000000u  /* 分片且要求分片确认 */
#define CODOL_FAT_ACK_BIT        0x20000000u  /* 分片确认包 */
#define CODOL_FAT_SEQ_MASK       0x1FFFFFFFu
#define CODOL_FAT_STRIDE         1154         /* 固定分片步长 */
#define CODOL_FAT_HDR            10           /* 分片头字节数 */
#define CODOL_FAT_MAX_FRAGMENTS  128
#define CODOL_FAT_MAX_MESSAGE    32768        /* 单条重组消息上限(实测 ~2.2KB) */

typedef struct codol_fat_reassembler {
    uint32_t sequence;          /* 正在重组的消息序号; 0 = 空闲 */
    uint16_t stride;
    uint8_t  last_index;
    uint8_t  in_use;
    uint32_t received_bits[4];  /* 128 位: 第 i 片是否已收 */
    uint32_t received_bytes;    /* 已收负载字节数(去重后) */
    /* buffer[0..4) = u32 序号; 第 i 片负载落在 buffer[4 + i*stride)。
     * 收全后 buffer[0 .. 4+received_bytes) 就是重组好的整条消息。 */
    uint8_t  buffer[4 + CODOL_FAT_MAX_MESSAGE];
} codol_fat_reassembler_t;

typedef struct codol_netchan {
    int             outgoing_sequence;
    int             sock;               /* 0=client, 1=server */
    int             dropped;
    int             incoming_sequence;
    codol_netadr_t  remote_address;
    int             qport;
    int             fragment_sequence;
    int             fragment_length;
    uint8_t        *fragment_buffer;
    int             fragment_buffer_size;
    int             unsent_fragments;
    int             unsent_fragment_start;
    int             unsent_length;
    uint8_t        *unsent_buffer;
    int             unsent_buffer_size;
    codol_fat_reassembler_t fat;        /* 接收侧分片重组状态(C-3.19 布局) */
} codol_netchan_t;
typedef struct codol_session {
    int                 slot;
    int                 state;
    codol_netadr_t      remote;
    uint32_t            challenge;
    uint32_t            cookie;
    codol_netchan_t     netchan;
    uint64_t            connect_time_us;
    uint64_t            last_packet_time_us;
    uint32_t            session_token;
    uint8_t             client_guid[16];
    char                player_name[32];
    uint32_t            reliable_sequence;
    uint32_t            reliable_ack;
    uint8_t            *recv_buf;
    size_t              recv_buf_len;
    size_t              recv_buf_cap;
} codol_session_t;

typedef struct codol_world {
    int                 state;
    char                map_name[64];
    codol_entity_state_t entities[CODOL_MAX_ENTITIES];
    codol_player_state_t players[CODOL_MAX_CLIENTS];
    codol_snapshot_history_t snapshot_history;
    uint32_t            frame_number;
    uint64_t            start_time_us;
    float               gravity;
    void               *clipmap;
    void               *map_ents;
    void               *comworld;
    void               *physics;
    void               *gamemode;
} codol_world_t;

typedef struct codol_config {
    uint16_t battle_port;
    uint16_t control_port;
    uint32_t tick_rate_hz;
    uint32_t snapshot_rate_hz;
    uint32_t max_clients;
    bool     release_mode;
    char     run_dir[512];
    char     evidence_ledger_path[512];
    char     bind_address[64];
} codol_config_t;

typedef struct codol_evidence_registry {
    const char **known_ids;
    size_t       known_count;
    bool         release_mode;
} codol_evidence_registry_t;

typedef struct codol_server {
    codol_config_t           config;
    codol_world_t            world;
    codol_session_t          sessions[CODOL_MAX_CLIENTS];
    int                      num_sessions;
    codol_evidence_registry_t evidence_registry;
    const void              *wire_table;
    size_t                   wire_table_count;
    bool                     running;
    uint64_t                 tick_count;
    uint64_t                 last_tick_time_us;
    void                    *transport_ctx;
    char                     lock_file_path[600];
    bool                     lock_held;
} codol_server_t;

typedef struct codol_trace {
    float   end_pos[3];
    float   normal[3];
    float   fraction;
    int     contents;
    int     entity_num;
    bool    startsolid;
    bool    allsolid;
} codol_trace_t;

typedef struct codol_pmove_constants {
    float   mins[3];
    float   maxs[3];
    float   eye_offset[3];
    float   gravity;
    float   step_size;
    float   friction;
    float   accelerate;
    float   air_accelerate;
    float   max_speed;
    float   jump_velocity;
} codol_pmove_constants_t;

typedef struct codol_usercmd {
    uint32_t time;
    uint32_t buttons;
    uint16_t pitch, yaw, roll;
    uint16_t weapon;
    uint16_t word22, word24, word34;
    uint16_t packed_angle;
    int8_t   forwardmove;    /* IW4X: char forwardmove */
    int8_t   rightmove;      /* IW4X: char rightmove   */
    uint8_t  byte32;
    uint8_t  extra[5];
} codol_usercmd_t;

typedef struct codol_pmove {
    codol_player_state_t   *ps;
    codol_usercmd_t         cmd;
    codol_pmove_constants_t constants;
    codol_trace_t           ground_trace;
    int                     ground_entity;
    bool                    walking;
} codol_pmove_t;

typedef struct codol_bitstream {
    const uint8_t *data;
    size_t         len;
    size_t         pos;
    uint32_t       bit_pos;
} codol_bitstream_t;

typedef struct codol_packet {
    codol_netadr_t  remote;
    const uint8_t  *data;
    size_t          len;
    uint64_t        recv_time_us;
} codol_packet_t;

#ifdef __cplusplus
}
#endif

#endif /* CODOL_TYPES_H */

