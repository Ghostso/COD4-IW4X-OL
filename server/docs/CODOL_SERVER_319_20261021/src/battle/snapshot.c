#include "codol_snapshot.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

/* ---- _BitWriter: 照抄参照实现 ----
 * ★ bytes_() 直接追加到 Data 末尾, 位指针不动;
 *   bits() 在字节对齐时把位指针**跳到 Data 末尾**(越过刚追加的原始字节);
 *   bits() 内是 **LSB-first** 写位。 */
typedef struct {
    uint8_t *data;
    int      cap;
    int      len;
    int      bit;          /* 绝对位位置 */
    bool     overflow;
} bw_t;

static void bw_init(bw_t *w, uint8_t *buf, int cap)
{
    memset(w, 0, sizeof(*w));
    w->data = buf; w->cap = cap;
}

static void bw_bytes(bw_t *w, const void *p, int n)
{
    if (w->len + n > w->cap) { w->overflow = true; return; }
    memcpy(w->data + w->len, p, (size_t)n);
    w->len += n;
}

static void bw_bits(bw_t *w, uint32_t v, int n)
{
    int i;
    for (i = 0; i < n; i++) {
        if ((w->bit & 7) == 0) {
            w->bit = w->len * 8;
            if (w->len >= w->cap) { w->overflow = true; return; }
            w->data[w->len++] = 0;
        }
        w->data[w->bit >> 3] |= (uint8_t)(((v >> i) & 1) << (w->bit & 7));
        w->bit++;
    }
}

/* 索引游程编码 —— ★★ 2026-10-25 修正回 4 位一组/步长 15 的写法。
 *
 * 依据 docs/BITORDER_6701D0_20261022.md 第 5 节"与本项目 snapshot.c 的对照":
 *   "历史实现错误: 这是把 indexBits 硬编码成 4 位、把 varint 写成 4 位一组。
 *    2026-10-23 已修正为按表宽编码(7 位)…"
 *
 * ★ 但**实测结论相反**: 10-23 的"修正"(7 位)让客户端拒收快照、进不了图;
 *   编回 4 位一组后(配合下面那四个字段)首帧快照与 10-22 那份能进图的二进制一致。
 *   所以对这个客户端, 4 位一组才是对的形式 —— 以实测为准, 不以文档结论为准。
 *
 * 语义(按 0x670CB0 反汇编): skip = index - prev - 1;
 *   skip == 0 -> 单个 1 位; 否则 0 位 + 每个 15 用 4 位表示, 末段用 4 位。 */
static void bw_index(bw_t *w, int index, int *prev, int index_bits)
{
    int skip;
    (void)index_bits;                  /* 该客户端要的是 4 位一组, 不按表宽 */
    skip = index - *prev - 1;
    *prev = index;
    if (skip == 0) { bw_bits(w, 1, 1); return; }
    bw_bits(w, 0, 1);
    while (skip >= 15) { bw_bits(w, 15, 4); skip -= 15; }
    bw_bits(w, (uint32_t)skip, 4);
}

static void bw_scalar(bw_t *w, uint32_t value, int width)
{
    int i;
    bw_bits(w, value == 0 ? 0 : 1, 1);
    if (value == 0) return;
    bw_bits(w, value & ((1u << (width & 7)) - 1u), width & 7);
    for (i = width & 7; i < width; i += 8) {
        uint8_t b = (uint8_t)((value >> i) & 0xFF);
        bw_bytes(w, &b, 1);
    }
}

static void put_f32(bw_t *w, float f)
{
    uint32_t u; memcpy(&u, &f, 4); bw_bytes(w, &u, 4);
}
static void put_u32(bw_t *w, uint32_t u) { bw_bytes(w, &u, 4); }
static void put_u16(bw_t *w, uint16_t u) { bw_bytes(w, &u, 2); }
static void put_u8(bw_t *w, uint8_t u)   { bw_bytes(w, &u, 1); }

void codol_snap_state_zero(codol_snap_state_t *st) { if (st) memset(st, 0, sizeof(*st)); }

/* ★ 2026-10-24: 原来的"基线异或"编码器(put_u32_xor / put_f32_xor / bw_scalar_xor)
 *   已删除 —— 字段载荷改为**裸值**(约束说明见 codol_snapshot_build 里那段)。
 *   删除原因: `to ^ 上一帧` 在"玩家一帧没动"的帧上退化成 0, 而头部基线位恒写 0
 *   (客户端被告知没有旧基线), 于是客户端按绝对量读到的就是 0 —— 等于每帧发
 *   position=(0,0,0)。详见 docs/SNAPSHOT_FIELD_DIFF_20261024.md §5。 */

void codol_snap_equip_default(codol_snap_equip_t *eq)
{
    memset(eq, 0, sizeof(*eq));
    eq->slot_count = 1;
    /* _Slot(1156, 585, 30, 71, 4): weapon, ammo, capacity, fire_ms, ads
     *                                   ^ 第三个是 capacity(=30)
     *   clip = capacity = 30 ; reserve = capacity*3 = 90 */
    eq->slots[0].weapon = 1156;
    eq->slots[0].ammo_key = 585;
    eq->slots[0].capacity = 30;
    eq->slots[0].clip = 30;
    eq->slots[0].reserve = 90;
}

/* ===================== entityState 段 =====================
 * ⚠️⚠️ 格式出处**未经本 build 验证**（2026-10-25 用户指出）：
 *   下面这些常数是从 **ol-mod 的 `sv_snapshot_mp.cpp`** 抄来的，而 ol-mod 服务的
 *   是 **3.3.3.3**，不是我们的 3.19 —— 它自己的注释里就写着
 *   "3.3.3.3 ends a server message with 6; **OLfinal** ends it with 5"，
 *   即它明确把我们的目标当作**另一个 build**。
 *
 *   与 **CoD4x(IW3)** 的实现**不一致**：
 *     CoD4x `MSG_WriteDeltaEntity()` 选出字段表后调用
 *       `MSG_WriteEntityDelta(snapInfo, msg, time, from, to, force,
 *                             fieldtype->numFields, **10**, fieldtype->field)`
 *     —— 实体 delta 的**索引位宽是 10**，而且**字段表按 eType 选**
 *        （`index = (eType <= 17) ? eType : 17; fieldtype = &netFieldList[index]`）。
 *   本实现用的是 6 位 lastChangedField + 3 位跳号 + **一张固定字段表**。
 *
 *   ⇒ 因此：**默认关闭（开关 `snapshot_entities.on`），并且在按 3.19 客户端自己的
 *     读取器（MSG_ReadDeltaEntity 等价物）核对出真实位宽之前，不要打开它。**
 *     权威做法是从 **本 build 客户端二进制**里读出那个读取器，而不是再找一个
 *     别的服务端实现来抄。
 *
 * 原始出处（供核对，不作为结论）：sv_snapshot_mp.cpp（ol-mod，3.3.3.3）
 *   · writeEntityNumber(5706): 号 == last+1 -> 单 1 位; 否则 1 位 0 + 1 位 1 + 11 位号。
 *   · 逐实体头(6221-6225): removed(1) | changed(1, 0=不变) |
 *       若 changed: newEntity(1, 1=无基线) | lastChangedField(6 位)。
 *   · 之后逐字段: writeSkippedFieldIndex(field, lastIdx, 3) + 字段值。
 *   · 字段 switch(6239-6253): case 0 -> eType(8 位原始字节); case 2/3/4 -> writeEntityOrigin。
 *   · 结尾(8811): writeEntityNumber(MaxEntityNumber=2047, ...)。
 * 本段只处理**新实体**(无基线): 基线取全零。 */
#define CODOL_ES_LAST_CHANGED_BITS 6
#define CODOL_ES_FIELD_SKIP_BITS   3
#define CODOL_ES_MAX_ENTITY_NUMBER 2047

/* writeEntityNumber(5706) */
static void bw_entity_number(bw_t *w, uint32_t number, int32_t *last)
{
    if (number == (uint32_t)(*last + 1)) {
        bw_bits(w, 1, 1);
    } else {
        bw_bits(w, 0, 1);
        bw_bits(w, 1, 1);
        bw_bits(w, number, 11);
    }
    *last = (int32_t)number;
}

/* writeSkippedFieldIndex(5231): 步长 1 用 1 位; 否则 0 位 + 每 (2^skipBits-1)=7 的 3 位游程 + 余数 3 位 */
static void bw_skipped_field(bw_t *w, uint32_t field, int32_t *last, int skip_bits)
{
    int32_t delta = (int32_t)field - *last;
    if (delta == 1) {
        bw_bits(w, 1, 1);
    } else {
        uint32_t chunk = (1u << skip_bits) - 1u;
        uint32_t remaining = (uint32_t)(delta - 1);
        bw_bits(w, 0, 1);
        while (remaining >= chunk) { bw_bits(w, chunk, skip_bits); remaining -= chunk; }
        bw_bits(w, remaining, skip_bits);
    }
    *last = (int32_t)field;
}

/* writeEntityOrigin(6016): floor(v+0.5) 取整; 相对 mapCenter 居中到 16 位;
 *   |delta|<=63 -> 1 位 0 + 7 位 (delta+64); 否则 1 位 1 + 16 位 (centeredValue^centeredBaseline)。
 * ★ mapCenter 本阶段按 0 处理(入参未提供, 见 build() 注释) —— 与参照默认值 {} 一致。 */
static bool bw_entity_origin(bw_t *w, float value, float baseline, float center)
{
    int32_t rv, rb, rc;
    int64_t cv, cb, delta;
    if (!(value == value) || !(baseline == baseline) || !(center == center))
        return false;                                   /* NaN */
    rv = (int32_t)floorf(value + 0.5f);
    rb = (int32_t)floorf(baseline + 0.5f);
    rc = (int32_t)floorf(center + 0.5f);
    cv = (int64_t)rv - rc + 0x8000;
    cb = (int64_t)rb - rc + 0x8000;
    if (cv < 0 || cv > 0xFFFF || cb < 0 || cb > 0xFFFF) return false;
    delta = (int64_t)rv - rb;
    if (delta >= -64 && delta <= 63) {
        bw_bits(w, 0, 1);
        bw_bits(w, (uint32_t)(delta + 64), 7);
    } else {
        bw_bits(w, 1, 1);
        bw_bits(w, (uint32_t)(cv ^ cb), 16);
    }
    return true;
}

/* ================= eType -> origin 字段 index 表 =================
 * ★★ 2026-10-25 修正: 字段表**按 eType 选**, 不是一张固定表。
 *   依据: 本 build 客户端自己的读取器(0x671170, 已反汇编确认):
 *     ecx = eType ; if (ecx > 0x17) ecx = 0x17 ;      // 索引 0..23
 *     fieldTable = [0xda9330 + ecx*8] ;               // 字段数组指针
 *     numFields  = [0xda9334 + ecx*8] ;               // 恒为 63
 *   记录 = 12 字节 { int offset; int bits; int changeHints; }, 每表 63 条, 无名字指针。
 *
 *   origin = trBase[0..2] = 实体结构里**绝对偏移 24/28/32** 的三个字段
 *     (entityState_s{ int number(0); int eType(4); LerpEntityState lerp(8); … };
 *      LerpEntityState{ … trajectory_t pos(→12) … }; trajectory_t 36 字节
 *      ⇒ pos.trBase[0..2] 落在实体偏移 24/28/32)。
 *   下表把每个 eType 的表里 offset==24/28/32 的**字段 index** 抽出来。x→24, y→28, z→32。
 *   ⚠️ eType 0/5/11/16/17/18/20 共用同一张表(ptr=0xDA4608), 其 origin = index 2/3/4,
 *      与修正前写死的完全一致 ⇒ 这些类型的产出逐字节不变。
 *
 *   数据来源(只读可复跑): fixtures/entity_field_tables_20261025.json
 *   (24 张表已抽好; 每张都齐备 {24,28,32} 三个偏移, 故 ok 全为 1)。 */
typedef struct { uint8_t idx[3]; uint8_t ok; } codol_origin_map_t;
static const codol_origin_map_t CODOL_ORIGIN_MAP[24] = {
    { {  2,  3,  4 }, 1 },   /*  0  0xDA4608 */
    { {  2,  1,  6 }, 1 },   /*  1  0xDA4BF8 */
    { {  2,  3,  6 }, 1 },   /*  2  0xDA4EF0 */
    { {  6,  5,  4 }, 1 },   /*  3  0xDA6508 */
    { {  2,  1,  8 }, 1 },   /*  4  0xDA7A20 */
    { {  2,  3,  4 }, 1 },   /*  5  0xDA4608 */
    { {  1,  2,  4 }, 1 },   /*  6  0xDA6808 */
    { {  5,  6, 10 }, 1 },   /*  7  0xDA6E08  ACTOR */
    { {  3,  4,  6 }, 1 },   /*  8  0xDA7108 */
    { {  2,  3,  7 }, 1 },   /*  9  0xDA7408 */
    { {  8,  9, 10 }, 1 },   /* 10  0xDA7728 */
    { {  2,  3,  4 }, 1 },   /* 11  0xDA4608 */
    { { 16, 17, 18 }, 1 },   /* 12  0xDA5AF0 */
    { {  1,  5,  7 }, 1 },   /* 13  0xDA54E0 */
    { {  1,  2,  3 }, 1 },   /* 14  0xDA57D8 */
    { {  1,  2,  8 }, 1 },   /* 15  0xDA51E8 */
    { {  2,  3,  4 }, 1 },   /* 16  0xDA4608 */
    { {  2,  3,  4 }, 1 },   /* 17  0xDA4608 */
    { {  2,  3,  4 }, 1 },   /* 18  0xDA4608 */
    { {  2,  3,  4 }, 1 },   /* 19  0xDA5DE8 */
    { {  2,  3,  4 }, 1 },   /* 20  0xDA4608 */
    { { 20, 21, 11 }, 1 },   /* 21  0xDA60E8 */
    { {  3,  4,  5 }, 1 },   /* 22  0xDA6B08 */
    { {  2,  3,  4 }, 1 },   /* 23  0xDA4900 */
};

/* 写实体列表: 逐实体 writeEntityNumber + 头 + 字段, 结尾 writeEntityNumber(2047)。
 * ents[].number 必须**升序**(参照要求, 否则游程编码错位)。返回 0 成功, -1 编码失败。
 * ★ 字段按 eType 选表取 origin 的字段 index (见上表), 并按**字段 index 升序**写出。 */
static int bw_write_entities(bw_t *w, const codol_snap_entity_t *ents, int ent_count)
{
    int32_t last_entity = -1;
    int i;
    for (i = 0; i < ent_count; i++) {
        const codol_snap_entity_t *e = &ents[i];
        uint32_t fx, fy, fz;
        bool ch0, chx, chy, chz;
        int32_t last_field = -1;
        int32_t last_changed;
        int et = e->type;
        const codol_origin_map_t *om;
        struct { int idx; int kind; } fld[4];   /* kind: 0=eType, 1=x, 2=y, 3=z */
        int nf = 0, j, k;

        /* ecx = eType ; if (ecx > 0x17) ecx = 0x17 (照 0x671170 的表选择) */
        if (et > 0x17) et = 0x17;
        om = &CODOL_ORIGIN_MAP[et];

        bw_entity_number(w, (uint32_t)e->number, &last_entity);

        memcpy(&fx, &e->x, 4);
        memcpy(&fy, &e->y, 4);
        memcpy(&fz, &e->z, 4);
        /* 新实体: 基线全零 -> changed = 新值位模式 != 0(照参照 bit_cast 比较) */
        ch0 = ((uint32_t)e->type != 0u);
        chx = (fx != 0u);
        chy = (fy != 0u);
        chz = (fz != 0u);

        /* 收集要写的 (字段 index, 种类); origin 找不齐(ok==0)时只留 eType(字段 0)。 */
        if (ch0)                { fld[nf].idx = 0;          fld[nf].kind = 0; nf++; }
        if (om->ok) {
            if (chx)            { fld[nf].idx = om->idx[0]; fld[nf].kind = 1; nf++; }
            if (chy)            { fld[nf].idx = om->idx[1]; fld[nf].kind = 2; nf++; }
            if (chz)            { fld[nf].idx = om->idx[2]; fld[nf].kind = 3; nf++; }
        } else if (chx || chy || chz) {
            /* 找不齐 {24,28,32}: **跳过该实体的 origin**, 只写 eType, 记一次。 */
            static bool warned = false;
            if (!warned) {
                fprintf(stderr,
                    "[snapshot] eType %d 的字段表找不到完整 origin{off 24/28/32} -> 只写 eType\n",
                    et);
                warned = true;
            }
        }

        /* 按字段 index 升序排序(nf <= 4), 游程编码要求升序。 */
        for (j = 0; j < nf; j++)
            for (k = j + 1; k < nf; k++)
                if (fld[k].idx < fld[j].idx) {
                    int ti = fld[j].idx, tk = fld[j].kind;
                    fld[j].idx = fld[k].idx; fld[j].kind = fld[k].kind;
                    fld[k].idx = ti;         fld[k].kind = tk;
                }

        last_changed = (nf > 0) ? (int32_t)fld[nf - 1].idx : -1;

        bw_bits(w, 0, 1);                               /* removed = 0 */
        if (last_changed < 0) {                         /* 无字段变化 -> 不变(照参照) */
            bw_bits(w, 0, 1);
            continue;
        }
        bw_bits(w, 1, 1);                               /* changed = 1 */
        bw_bits(w, 1, 1);                               /* newEntity = 1(无基线) */
        bw_bits(w, (uint32_t)last_changed, CODOL_ES_LAST_CHANGED_BITS);

        for (j = 0; j < nf; j++) {
            bw_skipped_field(w, (uint32_t)fld[j].idx, &last_field, CODOL_ES_FIELD_SKIP_BITS);
            switch (fld[j].kind) {
            case 0: put_u8(w, (uint8_t)(e->type & 0xFF));   /* case 0: MSG_WriteByte(eType) */
                    break;
            case 1: if (!bw_entity_origin(w, e->x, 0.0f, 0.0f)) return -1; break;
            case 2: if (!bw_entity_origin(w, e->y, 0.0f, 0.0f)) return -1; break;
            default:if (!bw_entity_origin(w, e->z, 0.0f, 0.0f)) return -1; break;
            }
        }
    }
    bw_entity_number(w, CODOL_ES_MAX_ENTITY_NUMBER, &last_entity);   /* 列表终止符 */
    return 0;
}

int codol_snapshot_build(uint8_t *out, int out_cap,
                         uint32_t ack, uint32_t server_time, uint32_t command_time,
                         bool first,
                         float x, float y, float z,
                         int16_t pitch, int16_t yaw, int16_t roll,
                         float vx, float vy, float aim_fraction, bool aiming,
                         bool omit_motion,
                         bool on_ground,
                         uint16_t living_weapon_entity,
                         const codol_snap_state_t *from,
                         codol_snap_state_t *cur,
                         const codol_snap_equip_t *eq,
                         const codol_snap_entity_t *ents, int ent_count)
{
    static const codol_snap_state_t ZERO;
    bw_t w;
    int prev = -1;
    if (!from) from = &ZERO;
    (void)from;   /* 字段载荷已改为裸值, 基线不再参与编码; 形参保留以不动调用方签名 */
    if (cur) codol_snap_state_zero(cur);
    const codol_snap_slot_t *sel = &eq->slots[0];
    int guns, i;

    bw_init(&w, out, out_cap);

    put_u32(&w, ack);
    put_u8(&w, 0);
    put_u32(&w, server_time);
    put_u8(&w, first ? 0 : 1);
    put_u8(&w, first ? 8 : 4);

    bw_bits(&w, 0, 1);
    bw_bits(&w, 1, 1);
    bw_bits(&w, 220, 8);

    bw_index(&w, 0, &prev, 7);  bw_bits(&w, 1, 1); put_u32(&w, command_time);
    bw_index(&w, 1, &prev, 7);  bw_bits(&w, 0, 1); put_u8(&w, (uint8_t)(eq->event_sequence & 0xFF));
    bw_index(&w, 3, &prev, 7);  bw_scalar(&w, (uint32_t)eq->weapon_time, 16);

    /* ★★ 字段载荷一律写**裸值**, 不是 `to ^ 上一帧`。
     *   约束: 头部(第 0x0D 字节)的基线位这里恒写 0 = "没有旧基线快照", 客户端据此把
     *   每个字段按绝对量读; 三份参照实现(Python `battle_server.py::_build_motion_snapshot`、
     *   `CodolMotionSnapshot.cs` 的 `BuildVerifiedMotionSnapshot` 与 `BuildCore`)对这批
     *   字段也全部写裸值。
     *   历史实现写 `to ^ from`: 首帧基线全零时 `to ^ 0 == to`, 与裸值等价 —— 所以首帧
     *   一直是对的, 问题被掩盖了; 但从第 2 帧起, 玩家一帧没动的字段会被写成 0,
     *   等于每帧告诉客户端 position=(0,0,0)。详见 docs/SNAPSHOT_FIELD_DIFF_20261024.md §5。 */
    /* omit_motion: 非首帧**省略**位置/速度(字段 8/10/11/13/14) ——
     *   不写的字段客户端保持原值, 位置交给客户端自己的预测/碰撞决定。 */
    if (!omit_motion) {
        bw_index(&w, 8,  &prev, 7); put_f32(&w, x);
        bw_index(&w, 10, &prev, 7); put_f32(&w, z);
        bw_index(&w, 11, &prev, 7); put_f32(&w, y);
        bw_index(&w, 13, &prev, 7); put_f32(&w, vy);
        bw_index(&w, 14, &prev, 7); put_f32(&w, vx);
    }

    bw_index(&w, 17, &prev, 7); bw_scalar(&w, (uint32_t)eq->weapon_state, 6);
    /* ★ 视角字段: 与 Python 版 omit_viewangles.on 对齐 —— 首帧后省略 idx 18/19/29,
     *   不写 = 客户端保持自己的视角, 消除服务端回传造成的转头阻尼/方向错乱。 */
    if (first) {
        bw_index(&w, 18, &prev, 7); put_u16(&w, (uint16_t)yaw);
        bw_index(&w, 19, &prev, 7); put_u16(&w, (uint16_t)pitch);
    }
    bw_index(&w, 20, &prev, 7); bw_scalar(&w, aiming ? 0x10u : 0u, 32);

    for (i = 0; i < 4; i++) {
        bw_index(&w, 21 + i, &prev, 7);
        bw_bits(&w, 1, 1);
        put_u8(&w, (uint8_t)(eq->events[i] & 0xFF));
        if (eq->events[i] != 0x19 && eq->events[i] != 0x1A) {
            bw_bits(&w, 1, 1);
            bw_bits(&w, (uint32_t)(eq->event_weapons[i] & 0x7FF), 11);
        }
    }

    if (first) {
        bw_index(&w, 29, &prev, 7); put_u16(&w, (uint16_t)roll);
    }
    /* ★★ index 34 = ViewHeight,权威实现直接 Bytes(60f)。
     *   之前写 put_f32_xor(60,60) -> 60^60=0，客户端读到 ViewHeight=0
     *   -> 相机高度 0 -> 视角在脚底/穿地。同理 index38。 */
    bw_index(&w, 34, &prev, 7); put_f32(&w, 60.0f);
    bw_index(&w, 38, &prev, 7); bw_scalar(&w, 60, 8);
    /* ★ index 39 = 当前手持武器。参照 battle_server.py:1183 写的是 `sel.weapon`
     *   (当前选中槽), 不是 slots[0] —— 硬编码 slots[0] 会让客户端看到
     *   "手持武器永远是主武器", 副武器切不出来。 */
    bw_index(&w, 39, &prev, 7);
    bw_scalar(&w, (uint32_t)eq->slots[eq->selected_slot < 0 ? 0 : eq->selected_slot].weapon, 11);
    bw_index(&w, 41, &prev, 7); put_f32(&w, aim_fraction);
    bw_index(&w, 44, &prev, 7); bw_scalar(&w, (uint32_t)eq->weapon_delay, 16);

    bw_index(&w, 54, &prev, 7); bw_bits(&w, 1, 1); bw_bits(&w, 0x1000, 31);
    bw_index(&w, 56, &prev, 7); bw_scalar(&w, 139, 10);
    bw_index(&w, 60, &prev, 7); bw_scalar(&w, 190, 16);
    /* ★★ index 61 = groundEntityNum: 2046 = "站在某个世界实体上", 2047 = 空中(ENTITYNUM_NONE)。
     *   **首帧写 2047**, 之后省略, 交给客户端自己的 ClipMap。
     *
     *   ⚠️ 2026-10-26 回退记录: 曾把这里改成 2046, 实机结果 =
     *      **开镜失效(瞄准镜消失) + 人物在房顶**。这与 2026-10-24 的既有结论一致:
     *        SNAPSHOT_RAWFIX_20261024_1357: 恒发 2046 -> 客户端进"飞行模式"且开镜失效
     *      原因: 2046 表示"正站在某个世界实体上", 但服务端并没有在快照实体段里
     *      下发任何实体(ents=0), 客户端找不到那个 groundEntity ⇒ 状态不一致。
     *      2047(ENTITYNUM_NONE) 是诚实的"我不知道你踩着什么", 客户端据此自己跑物理。
     *   ⇒ 在实体段能真正下发模型/实体之前, 这一格必须保持 2047。 */
    if (first) {
        bw_index(&w, 61, &prev, 7); bw_scalar(&w, 2047u, 16);
    }
    bw_index(&w, 62, &prev, 7); bw_scalar(&w, 0, 6);
    bw_index(&w, 63, &prev, 7); bw_scalar(&w, 800, 16);
    bw_index(&w, 68, &prev, 7); bw_scalar(&w, 2047, 11);
    bw_index(&w, 83, &prev, 7); bw_scalar(&w, 0, 1);
    bw_index(&w, 107, &prev, 7); bw_scalar(&w, 0, 16);
    bw_index(&w, 162, &prev, 7); bw_scalar(&w, 0, 16);
    /* ★ 62/83/107/162 这四个字段与 idx 219 都**不在参照里**(参照还额外说明 idx219
     *   在真实序列里不存在、playerState 表也确实只有 87 项), 但**它们当前是能用的写法**:
     *   2026-10-25 按参照逐字节重写后客户端直接卡"等待玩家数据", 而这份写法能进图。
     *   ⇒ 以实测为准。*/
    bw_index(&w, 219, &prev, 7); bw_bits(&w, 1, 1); bw_bits(&w, 1, 1);
    put_f32(&w, 1.0f); bw_bits(&w, 0, 8);
    bw_bits(&w, 1, 1); bw_bits(&w, 5, 17);
    put_u16(&w, 100); put_u16(&w, 100);

    /* ★★ 注意: 这一段**故意不按参照**(参照在 68 之后写 idx 84 段)。2026-10-25 实测:
     *   把编码器改成与参照逐字节一致(141B/119B)之后, 客户端反而**卡"等待玩家数据"**
     *   (`REFENC_OMIT1_20261024_1153` 首帧 119B、`REFENCODER_20261024_1150` 首帧 141B,
     *    两次都只走到 head≈0x62~0x8C)。而**当前这种写法能让客户端进图**(§8.1 有完整证据)。
     *   ⇒ 以实测为准: 参照的 10-07 改写版**在真机上不被这个客户端接受**。 */
    guns = eq->slot_count - ((eq->slots[eq->slot_count - 1].capacity == 0) ? 1 : 0);
    bw_bits(&w, guns > 0 ? 1 : 0, 1);
    for (i = 0; i < guns; i++) {
        const codol_snap_slot_t *s = &eq->slots[i];
        bw_bits(&w, (uint32_t)i, 4);
        bw_bits(&w, (uint32_t)s->weapon, 11);
        bw_bits(&w, 1, 1);
        bw_bits(&w, (uint32_t)s->clip, 9);
        bw_bits(&w, 0, 1);
        bw_bits(&w, (i + 1 < guns) ? 1 : 0, 1);
    }
    bw_bits(&w, 1, 1);                       /* 15 个已拥有槽位 */
    for (i = 0; i < 15; i++) {
        int occupied = (i < eq->slot_count);
        bw_bits(&w, occupied ? 1 : 0, 1);
        if (occupied) {
            bw_bits(&w, 1, 1);
            bw_bits(&w, (uint32_t)eq->slots[i].weapon, 11);
            bw_bits(&w, 0, 5);
            bw_bits(&w, 0, 12);
        }
    }
    bw_bits(&w, guns > 0 ? 1 : 0, 1);        /* 备弹 */
    for (i = 0; i < guns; i++) {
        const codol_snap_slot_t *s = &eq->slots[i];
        bw_bits(&w, (uint32_t)i, 4);
        bw_bits(&w, (uint32_t)s->ammo_key, 11);
        bw_bits(&w, (uint32_t)(s->reserve & 0xFFF), 12);
        bw_bits(&w, (i + 1 < guns) ? 1 : 0, 1);
    }
    bw_bits(&w, 0, 13);
    bw_bits(&w, 0, 1); bw_bits(&w, 0, 1); bw_bits(&w, 0, 1);
    bw_bits(&w, 1, 1); bw_bits(&w, 2047, 11);
    bw_bits(&w, 0, 1); bw_bits(&w, 0, 1);

    /* ★★ entityState 段 —— **插在消息终止符 0x05 之前**。
     *   开关关闭时 ents==NULL/ent_count==0, 本段一位不写 -> 产出与改动前逐字节相同。
     *   ★ mapCenter 本阶段按 0 处理: 参照的 mapCenter 来自 configstr(地图中心),
     *     本服未提供该 configstr, 故入参默认 {}; 对 |origin|<=64 的实体会走 delta 分支
     *     (与 mapCenter 无关), 大坐标走绝对分支时按 mapCenter=0 居中。 */
    if (ents && ent_count > 0) {
        if (bw_write_entities(&w, ents, ent_count) < 0) return -1;
    }

    { uint8_t tail = 0x05; bw_bytes(&w, &tail, 1); }

    /* ★★ clientInfo 段(手持武器子实体引用)。
     *   依据(2026-10-22 已在本客户端二进制上验证):
     *     out.exe 0x00DA8078 netfield 表首项 = {offset 0x140, width 11}
     *     out.exe 0x0054BD7A: mov ecx,[ebx+0x140]; mov [edi+0x398],ecx
     *   即 clientState 字段 0 = 11bit ET6 武器子实体号, 0 = 无枪。
     *   之前我们从不发 clientInfo 段 -> 客户端基线为零 -> 没枪。
     *   段格式(照 sv_snapshot_mp.cpp writeClientInfos):
     *     循环{ writeClientNumber; 1bit removed; 1bit hasDelta; [delta] }
     *     结束 1bit 0
     *   本次只发一条记录、只发字段 0，作为最小验证。 */
    #if 0  /* ★ 实测(2026-10-22): 这个 clientInfo 段使客户端卡在
       *   "等待玩家数据"。FIRST3 那轮(能进游戏)没有这个段。
       *   在完整弄清楚 clientInfo 的前置条件之前不发。 */
    bw_bits(&w, 1, 1);                 /* 还有下一条记录 */
    bw_bits(&w, 0, 1);                 /* clientNum != last+1 */
    bw_bits(&w, 0, 5);                 /* clientNum = 0 */
    bw_bits(&w, 0, 1);                 /* 未删除 */
    bw_bits(&w, 1, 1);                 /* 有 delta */
    bw_bits(&w, 1, 1);                 /* 字段索引 0 */
    bw_bits(&w, 1, 1);                 /* 值非零 */
    bw_bits(&w, living_weapon_entity & 0x7FFu, 11);
    bw_bits(&w, 0, 1);                 /* 段结束 */
#endif

    if (w.overflow) return -1;

    /* ★ 回填本帧值 -> 下一帧的基线 */
    if (cur) {
        cur->command_time  = command_time;
        cur->pm_flags      = aiming ? 0x10 : 0;
        cur->x = x; cur->y = y; cur->z = z;
        cur->vx = vx; cur->vy = vy;
        cur->pitch = (uint16_t)pitch; cur->yaw = (uint16_t)yaw; cur->roll = (uint16_t)roll;
        cur->aim_fraction  = aim_fraction;
        cur->weapon_state  = eq->weapon_state;
        cur->weapon_time   = eq->weapon_time;
        cur->weapon_delay  = eq->weapon_delay;
        cur->current_weapon = eq->slots[eq->selected_slot < 0 ? 0 : eq->selected_slot].weapon;
    }
    return w.len;
}

