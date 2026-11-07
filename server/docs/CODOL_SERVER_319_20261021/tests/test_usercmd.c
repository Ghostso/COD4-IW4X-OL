/* test_usercmd: C 侧 usercmd 解析器 与 Python 参照读取器 的差分对账.
 *
 * 用法: test_usercmd [cases.txt]
 *   cases.txt 每行: <key_hex8> <body_hex> <expected_canonical>
 * 输出每行:        <key_hex8> <body_hex> <actual_canonical>
 * 由 tools/gen_cases.py 生成 (生成前每条都先过参照读取器自校验).
 */
#include "codol_usercmd.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hexval(int ch)
{
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
    return -1;
}

static int hexdecode(const char *s, unsigned char *out, int cap)
{
    int n = 0;
    while (s[0] && s[1]) {
        int hi = hexval((unsigned char)s[0]), lo = hexval((unsigned char)s[1]);
        if (hi < 0 || lo < 0) break;
        if (n >= cap) break;
        out[n++] = (unsigned char)((hi << 4) | lo);
        s += 2;
    }
    return n;
}

static void canonical(const codol_usercmd_list_t *l, char *out, int cap)
{
    int i, off = 0;
    out[0] = 0;
    if (l->count <= 0) { snprintf(out, cap, "REJECT"); return; }
    for (i = 0; i < l->count; i++) {
        const codol_usercmd_t *c = &l->cmds[i];
        off += snprintf(out + off, cap - off, "%sT%u,B%u,P%u,Y%u,R%u,W%u,A%u,H%u,X%u,K%u,F%d,S%d,B32%u,E%d,%d,%d,%d,%d",
                        i ? ";" : "",
                        (unsigned)c->time, (unsigned)c->buttons,
                        (unsigned)c->pitch, (unsigned)c->yaw, (unsigned)c->roll,
                        (unsigned)c->weapon, (unsigned)c->word22, (unsigned)c->word24,
                        (unsigned)c->word34, (unsigned)c->packed_angle,
                        (int)c->forwardmove, (int)c->rightmove, (unsigned)c->byte32,
                        c->extra[0], c->extra[1], c->extra[2], c->extra[3], c->extra[4]);
        if (off >= cap - 64) break;
    }
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "cases.txt";
    char line[8192];
    FILE *fp = fopen(path, "r");
    int total = 0, mismatch = 0;

    if (!fp) { printf("no file %s\n", path); return 1; }
    while (fgets(line, sizeof(line), fp)) {
        unsigned key;
        char bodyhex[8192], exp[4096];
        unsigned char body[2048];
        int blen;
        codol_usercmd_list_t list;
        char act[4096];
        char *p;

        if (line[0] == '\n' || line[0] == '\r' || line[0] == 0) continue;
        if (sscanf(line, "%x %8191s %4095s", &key, bodyhex, exp) != 3) continue;
        blen = hexdecode(bodyhex, body, (int)sizeof(body));
        memset(&list, 0, sizeof(list));
        if (!codol_usercmd_parse(body, blen, key, NULL, &list))
            snprintf(act, sizeof(act), "REJECT");
        else
            canonical(&list, act, sizeof(act));

        total++;
        if (strcmp(act, exp) != 0) {
            mismatch++;
            if (mismatch <= 5) {
                printf("MISMATCH key=%08X blen=%d\n", key, blen);
                printf("  exp=%s\n", exp);
                printf("  act=%s\n", act);
            }
        }
        if (argc > 2) {   /* 详细模式: 逐行打印 */
            printf("%08X %s %s\n", key, bodyhex, act);
        }
    }
    fclose(fp);
    printf("test_usercmd: %d cases, %d mismatch\n", total, mismatch);
    return mismatch ? 1 : 0;
}
