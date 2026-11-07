#include "codol_usercmd.h"
#include <string.h>

/* ---- MixedReader ---- */
typedef struct {
    const uint8_t *data;
    int  len;
    int  cursor;
    int  bit;
    bool truncated;
} mr_t;

static void mr_init(mr_t *r, const uint8_t *d, int n)
{
    memset(r, 0, sizeof(*r)); r->data = d; r->len = n;
}

static uint32_t mr_bits(mr_t *r, int n)
{
    uint32_t v = 0; int i;
    for (i = 0; i < n; i++) {
        if ((r->bit & 7) == 0) {
            if (r->cursor >= r->len) { r->truncated = true; return v; }
            r->bit = r->cursor * 8;
            r->cursor++;
        }
        v |= (uint32_t)(((r->data[r->bit >> 3] >> (r->bit & 7)) & 1) << i);
        r->bit++;
    }
    return v;
}

static uint32_t mr_bytes(mr_t *r, int n)
{
    uint32_t v = 0; int i;
    if (r->cursor + n > r->len) { r->truncated = true; return v; }
    for (i = 0; i < n; i++) { v |= (uint32_t)r->data[r->cursor] << (8 * i); r->cursor++; }
    return v;
}

static bool mr_text(mr_t *r, char *out, int cap)
{
    int i = 0, c;
    for (;;) {
        c = (int)mr_bytes(r, 1);
        if (r->truncated) return false;
        if (c == 0) { out[i] = 0; return true; }
        if (c < 32 || c > 126) return false;
        if (i < cap - 1) out[i++] = (char)c;
        else return false;
    }
}

#define MR_MASK(w) ((w) >= 32 ? 0xFFFFFFFFu : ((1u << (w)) - 1u))

static uint32_t mr_delta(mr_t *r, uint32_t old, uint32_t key, int width, bool aligned)
{
    uint32_t v;
    if (mr_bits(r, 1) == 0) return old;
    v = aligned ? mr_bytes(r, width / 8) : mr_bits(r, width);
    return (v ^ key) & MR_MASK(width);
}

bool codol_usercmd_parse(const uint8_t *data, int len, uint32_t key,
                         const codol_usercmd_t *baseline,
                         codol_usercmd_list_t *out)
{
    mr_t r;
    uint32_t opcode;
    int count, i;
    codol_usercmd_t old;

    if (!data || len <= 0 || !out) return false;
    memset(out, 0, sizeof(*out));
    mr_init(&r, data, len);

    opcode = mr_bits(&r, 3);
    {
        bool have_rseq = false;
        uint32_t prev_rseq = 0;
        while (opcode == 2) {                   /* 可靠命令段: 收集文本交给上层 */
            char tmp[1024];
            uint32_t rseq = mr_bytes(&r, 4);
            /* ★ 参照 read_input 的可靠命令序列校验(此前缺失):
             *   if seq == 0 or seq > 1000000 or (reliable and seq != prev+1): raise
             *   缺少这一步时, 一旦可靠段的 seq/文本边界读偏, 解析会带着错误游标
             *   继续走完整个包, 产出垃圾 usercmd(实测 yaw=59064/ weapon=142)。 */
            if (rseq == 0 || rseq > 1000000u) return false;
            if (have_rseq && rseq != prev_rseq + 1u) return false;
            if (!mr_text(&r, tmp, sizeof(tmp))) return false;
            if (r.truncated) return false;
            have_rseq = true;
            prev_rseq = rseq;
            if (out->reliable_count < CODOL_MAX_RELIABLE_TEXT) {
                strncpy(out->reliable[out->reliable_count], tmp,
                        CODOL_RELIABLE_TEXT_LEN - 1);
                out->reliable[out->reliable_count][CODOL_RELIABLE_TEXT_LEN - 1] = 0;
                out->reliable_count++;
            }
            opcode = mr_bits(&r, 3);
        }
    }
    if (opcode != 0 && opcode != 1) return false;

    count = (int)mr_bytes(&r, 1);
    if (count < 1 || count > CODOL_MAX_USERCMDS) return false;

    if (baseline) old = *baseline;
    else memset(&old, 0, sizeof(old));

    for (i = 0; i < count; i++) {
        codol_usercmd_t c = old;
        if (mr_bits(&r, 1) != 0) c.time = (old.time + mr_bytes(&r, 1)) & 0xFFFFFFFFu;
        else                     c.time = mr_bytes(&r, 4);

        if ((mr_bits(&r, 1) ^ (key & 1)) == 0) {
            if (mr_bits(&r, 3) != 7) return false;      /* idle terminator */
        } else {
            bool full = ((mr_bits(&r, 1) ^ (key & 1)) != 0);
            uint32_t first_key = full ? key : (key ^ c.time);
            c.buttons = (old.buttons & ~1u) | (mr_bits(&r, 1) ^ (first_key & 1));
            c.pitch = (uint16_t)(mr_delta(&r, old.pitch, first_key, 16, true) & 0xFFFF);
            c.yaw   = (uint16_t)(mr_delta(&r, old.yaw,   first_key, 16, true) & 0xFFFF);
            /* move: CODOL 线格式是**单个 4bit 非对齐 delta 位域**，与参照 read_input
             *   逐行一致。该布局已在真实客户端字节上验证：参照同次运行解出 910 条
             *   可靠命令 + 120 次开火，而开火事件必需 inputs 非空。
             *   语义: bit0=前 bit1=后 bit2=右 bit3=左。
             *   ★ 切勿用 IW4X 的 unpack_move: 那是 IW4X **私有内存结构**的 2×int8,
             *     搬到这里会让 4bit↔16bit 错位，位流立刻失步，终结符校验必然失败。 */
            {
                uint32_t oldmove = (uint32_t)((old.forwardmove > 0 ? 1u : 0u) |
                                              (old.forwardmove < 0 ? 2u : 0u) |
                                              (old.rightmove   > 0 ? 4u : 0u) |
                                              (old.rightmove   < 0 ? 8u : 0u));
                uint32_t mv = mr_delta(&r, oldmove, first_key, 4, false) & 0xFu;
                c.forwardmove = (int8_t)((mv & 1u ? 1 : 0) - (mv & 2u ? 1 : 0));
                c.rightmove   = (int8_t)((mv & 4u ? 1 : 0) - (mv & 8u ? 1 : 0));
            }
            if (full) {
                uint32_t timed = (key ^ c.time);
                c.roll = (uint16_t)(mr_delta(&r, old.roll, timed, 16, true) & 0xFFFF);
                c.buttons = ((c.buttons & 1u) |
                             ((mr_delta(&r, old.buttons >> 1, timed, 29, false) << 1) & 0xFFFFFFFFu));
                c.weapon = (uint16_t)(mr_delta(&r, old.weapon, timed, 11, false) & 0xFFFF);
                c.word24 = (uint16_t)(mr_delta(&r, old.word24, timed, 11, false) & 0xFFFF);
                c.word22 = (uint16_t)(mr_delta(&r, old.word22, timed, 11, false) & 0xFFFF);
                if (c.buttons & 0x20000u)
                    for (int j = 0; j < 3; j++)
                        c.extra[j] = (uint8_t)(mr_delta(&r, old.extra[j], timed, 8, true) & 0xFF);
                if (c.buttons & 0x200000u)
                    for (int j = 3; j < 5; j++)
                        c.extra[j] = (uint8_t)(mr_delta(&r, old.extra[j], timed, 8, true) & 0xFF);
                if (c.buttons & 4u) {
                    c.packed_angle = (uint16_t)(mr_delta(&r, old.packed_angle, timed, 16, true) & 0xFFFF);
                    c.byte32 = (uint8_t)(mr_delta(&r, old.byte32, timed, 8, false) & 0xFF);
                    c.word34 = (uint16_t)(mr_delta(&r, old.word34, timed, 11, false) & 0xFFFF);
                }
            }
            if (mr_bits(&r, 3) != (full ? 5 : 2)) return false;   /* input terminator */
        }
        if (r.truncated) return false;
        out->cmds[out->count++] = c;
        old = c;
    }
    return true;
}
