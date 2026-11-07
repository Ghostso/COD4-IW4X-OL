/* gs_adapt.h -- gamestate 动态房间适配(header-only)
 *
 * 与 reference/dynamic_gamestate.py 的 _Writer/_Reader 逐行等价:
 *   索引位写在一个 bit 游标上, 字符串走 append-only 的字节游标, 两者交错。
 *   fixture 上 decode -> encode 已核对逐字节一致(283B)。
 *
 * 适配范围(两者必须一起改, 否则首部与 cs0 自相矛盾):
 *   header(mapName / gameType)
 *   configstring[0] 里的 \mapname\<m>\ 与 \g_gametype\<gt>\
 * field4(configStringChecksum) 不在这里动 -- 由调用方回填客户端自报值。
 *
 * 日志: 调用方在 include 前定义 GS_LOG_WARN(...), 否则退化为空。
 */
#ifndef CODOL_GS_ADAPT_H
#define CODOL_GS_ADAPT_H

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifndef GS_LOG_WARN
#define GS_LOG_WARN(...) ((void)0)
#endif

static bool _json_get_str(const char *json, const char *key, char *out, size_t out_sz)
{
    char pat[64];
    const char *p, *q;
    size_t n;
    if (!json || !key || !out || out_sz == 0) return false;
    snprintf(pat, sizeof(pat), "\"%s\"", key);
    p = strstr(json, pat);
    if (!p) return false;
    p += strlen(pat);
    while (*p && *p != ':') p++;
    if (*p != ':') return false;
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    if (*p != '"') return false;
    p++;
    q = strchr(p, '"');
    if (!q) return false;
    n = (size_t)(q - p);
    if (n == 0 || n >= out_sz) return false;
    memcpy(out, p, n);
    out[n] = 0;
    return true;
}

/* 从 configstring 值里把 \key\old 替换成 \key\new (长度可不同)。
 * ★ 2026-11-07: 原实现把 replacement 写回 buf[0] (assume 命中在开头), 于是
 *   cs0 这种"\2482\2\...\mapname\X\"的长前缀会被整段吞掉 —— 该函数此前是死代码,
 *   从没跑过, 由 tests/test_gs_adapt 对拍发现。现在按命中位置原地替换。
 * 返回新长度; 缓冲区不足或未找到返回 -1。 */
static int _cs_replace_kv(char *buf, int buf_sz, const char *key,
                          const char *new_val)
{
    char pattern[96], replacement[160];
    const char *hit;
    int rep_len, tail_len, new_len;
    size_t hit_off, old_end;
    snprintf(pattern, sizeof(pattern), "\\%s\\", key);
    hit = strstr(buf, pattern);
    if (!hit) return -1;
    hit_off = (size_t)(hit - buf);
    {
        const char *val_end = strchr(buf + hit_off + strlen(pattern), '\\');
        if (!val_end) return -1;
        old_end = (size_t)(val_end - buf);
    }
    snprintf(replacement, sizeof(replacement), "\\%s\\%s", key, new_val);
    rep_len = (int)strlen(replacement);
    tail_len = (int)strlen(buf + old_end);
    new_len = (int)(hit_off + (size_t)rep_len + (size_t)tail_len);
    if (new_len >= buf_sz - 1) return -1;
    memmove(buf + hit_off + (size_t)rep_len, buf + old_end, (size_t)tail_len + 1);
    memcpy(buf + hit_off, replacement, (size_t)rep_len);
    return new_len;
}

typedef struct {
    uint8_t d[1200];
    size_t len;
    size_t bit;
} _gs_w;

static void _w_byte(_gs_w *w, unsigned v)
{
    if (w->len < sizeof(w->d)) w->d[w->len++] = (uint8_t)v;
}

static void _w_short(_gs_w *w, unsigned v)
{
    _w_byte(w, v & 0xFF);
    _w_byte(w, (v >> 8) & 0xFF);
}

static void _w_raw(_gs_w *w, const void *p, size_t n)
{
    const uint8_t *s = (const uint8_t *)p;
    size_t i;
    for (i = 0; i < n; i++) _w_byte(w, s[i]);
}

static void _w_cstr(_gs_w *w, const char *s, size_t n)
{
    _w_raw(w, s, n);
    _w_byte(w, 0);
}

static void _w_bits(_gs_w *w, unsigned v, int width)
{
    int i;
    for (i = 0; i < width; i++) {
        if ((w->bit & 7) == 0) {
            w->bit = w->len * 8;
            _w_byte(w, 0);
        }
        if ((w->bit >> 3) < w->len)
            w->d[w->bit >> 3] |= (uint8_t)(((v >> i) & 1u) << (w->bit & 7));
        w->bit++;
    }
}

static void _w_index(_gs_w *w, unsigned index, unsigned prev)
{
    if (index == prev + 1) {
        _w_bits(w, 1, 1);
    } else {
        _w_bits(w, 0, 1);
        _w_bits(w, index, 14);
    }
}

static int _r_bits(const uint8_t *d, size_t n, size_t *bit, size_t *end,
                   int width, unsigned *out)
{
    unsigned v = 0;
    int i;
    for (i = 0; i < width; i++) {
        if ((*bit & 7) == 0) {
            if (*end >= n) return -1;
            *bit = *end * 8;
            (*end)++;
        }
        v |= (unsigned)((d[*bit >> 3] >> (*bit & 7)) & 1u) << i;
        (*bit)++;
    }
    *out = v;
    return 0;
}

static int _r_cstr(const uint8_t *d, size_t n, size_t *end, char *out, size_t out_sz)
{
    size_t k = 0;
    while (*end < n && d[*end]) {
        if (k + 1 >= out_sz) return -1;      /* 截断就报错, 不要静默写坏 */
        out[k++] = (char)d[*end];
        (*end)++;
    }
    if (*end >= n) return -1;
    out[k] = 0;
    (*end)++;
    return 0;
}

static int _gs_adapt_dynamic(uint8_t *state, size_t cap, size_t *len_io,
                             const char *room_json_path)
{
    FILE *fp;
    char json[1024];
    char room_map[128] = {0}, room_gt[64] = {0};
    size_t json_n, n, pos, block_start, tail_start, tail_len, out_len, i;
    static uint8_t out[1200];
    uint8_t hdr_cmd, cfg_cmd;
    uint32_t hdr_ver, hdr_field4;
    unsigned count, idx, prev, seq;
    size_t bit, end;
    _gs_w blk;
    _gs_w blk0;                              /* 未改写版本, 只用来量原始块长 */
    char val[512];

    if (!state || !len_io || *len_io < 16) return -1;
    if (!room_json_path || !room_json_path[0]) return -1;
    fp = fopen(room_json_path, "rb");
    if (fp) {
        json_n = fread(json, 1, sizeof(json) - 1, fp);
        fclose(fp);
        json[json_n] = 0;
        if (!_json_get_str(json, "map", room_map, sizeof(room_map))) room_map[0] = 0;
        if (!_json_get_str(json, "game_type", room_gt, sizeof(room_gt))) room_gt[0] = 0;
    } else {
        json[0] = 0;
    }

    /* ★ 兜底输入：没有 active_room.json(或它没写 map) 时读同目录的 coop_map.txt。
     *   一行地图名；game_type 按前缀推断(coop_* -> coop，其余 tdm)。
     *   这条让"选图"在只放一个文件的情况下也能生效，不必依赖大厅那条链。
     *   文件也不存在时返回 -1，调用方沿用 fixture(地图就是 fixture 里的那张)。 */
    if (!room_map[0]) {
        char side[600];
        const char *slash = strrchr(room_json_path, '/');
        const char *bslash = strrchr(room_json_path, '\\');
        if (bslash && (!slash || bslash > slash)) slash = bslash;
        size_t dl = slash ? (size_t)(slash - room_json_path) : 0;
        if (dl > 0 && dl < sizeof(side) - 32) {
            memcpy(side, room_json_path, dl);
            side[dl] = 0;
            strncat(side, "/coop_map.txt", sizeof(side) - strlen(side) - 1);
            fp = fopen(side, "rb");
            if (fp) {
                size_t k = 0;
                int ch;
                while (k + 1 < sizeof(room_map) && (ch = fgetc(fp)) != EOF &&
                       ch != '\n' && ch != '\r' && ch != ' ' && ch != '\t')
                    room_map[k++] = (char)ch;
                room_map[k] = 0;
                fclose(fp);
                if (room_map[0]) {
                    GS_LOG_WARN("[battle] 地图来自 %s: %s", side, room_map);
                }
            }
        }
    }
    if (!room_map[0]) return -1;
    if (!room_gt[0])
        strncpy(room_gt, strncmp(room_map, "coop_", 5) == 0 ? "coop" : "tdm",
                sizeof(room_gt) - 1);

    /* header: [4B 0][u8 cmd=3][u32 ver][map\0][gt\0][u32 field4][u8 4][u16 count] */
    n = *len_io;
    pos = 4;
    if (pos + 1 > n) return -1;
    hdr_cmd = state[pos]; pos += 1;
    if (hdr_cmd != 3) return -1;
    if (pos + 4 > n) return -1;
    memcpy(&hdr_ver, state + pos, 4); pos += 4;
    while (pos < n && state[pos]) pos++;
    if (pos >= n) return -1;
    pos++;                                  /* map 结束 */
    while (pos < n && state[pos]) pos++;
    if (pos >= n) return -1;
    pos++;                                  /* game_type 结束 */
    if (pos + 4 > n) return -1;
    memcpy(&hdr_field4, state + pos, 4); pos += 4;

    block_start = pos;
    if (pos + 3 > n) return -1;
    cfg_cmd = state[pos]; pos += 1;
    if (cfg_cmd != 4) return -1;
    count = (unsigned)state[pos] | ((unsigned)state[pos + 1] << 8);
    pos += 2;
    if (count > 4096) return -1;             /* 合理上限, 防越界 */

    /* 双游标: bit 从 pos*8 起, 字节游标也从 pos 起 */
    bit = pos * 8;
    end = pos;
    memset(&blk, 0, sizeof(blk));
    _w_byte(&blk, 4);
    _w_short(&blk, count);
    memset(&blk0, 0, sizeof(blk0));
    _w_byte(&blk0, 4);
    _w_short(&blk0, count);

    prev = 0xFFFFFFFFu;                      /* == python 的 -1 */
    for (i = 0; i < count; i++) {
        if (_r_bits(state, n, &bit, &end, 1, &seq) < 0) return -1;
        if (seq) {
            idx = prev + 1;
        } else {
            if (_r_bits(state, n, &bit, &end, 14, &idx) < 0) return -1;
        }
        if (_r_cstr(state, n, &end, val, sizeof(val)) < 0) return -1;
        /* ★ 尾部起点必须按"原始块长"算: 先用未改写的字符串编一份 blk0 量长度,
         *   改写后的 blk 只用于输出。用改写后的长度去切源缓冲会整体错位。 */
        _w_index(&blk0, idx, prev);
        if (blk0.len + strlen(val) + 16 > sizeof(blk0.d)) return -1;
        _w_cstr(&blk0, val, strlen(val));
        if (idx == 0) {
            /* cs0 = CS_SERVERINFO, 客户端从这里读 mapname / g_gametype */
            if (_cs_replace_kv(val, (int)sizeof(val), "mapname", room_map) < 0)
                GS_LOG_WARN("[battle] cs0 里没有 \\mapname\\ -- 地图只改了首部");
            if (_cs_replace_kv(val, (int)sizeof(val), "g_gametype", room_gt) < 0)
                GS_LOG_WARN("[battle] cs0 里没有 \\g_gametype\\ -- 模式只改了首部");
        }
        _w_index(&blk, idx, prev);
        if (blk.len + strlen(val) + 16 > sizeof(blk.d)) return -1;
        _w_cstr(&blk, val, strlen(val));
        prev = idx;
    }

    tail_start = block_start + blk0.len;
    if (tail_start > n) return -1;
    tail_len = n - tail_start;

    out_len = 4 + 1 + 4 + strlen(room_map) + 1 + strlen(room_gt) + 1 + 4
              + blk.len + tail_len;
    if (out_len > cap || out_len > sizeof(out)) return -1;

    memset(out, 0, 4);
    pos = 4;
    out[pos++] = 3;
    memcpy(out + pos, &hdr_ver, 4); pos += 4;
    memcpy(out + pos, room_map, strlen(room_map)); pos += strlen(room_map);
    out[pos++] = 0;
    memcpy(out + pos, room_gt, strlen(room_gt)); pos += strlen(room_gt);
    out[pos++] = 0;
    memcpy(out + pos, &hdr_field4, 4); pos += 4;
    memcpy(out + pos, blk.d, blk.len); pos += blk.len;
    memcpy(out + pos, state + tail_start, tail_len); pos += tail_len;

    memcpy(state, out, out_len);
    *len_io = out_len;
    return 0;
}

#endif /* CODOL_GS_ADAPT_H */
