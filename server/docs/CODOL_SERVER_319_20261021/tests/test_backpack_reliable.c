/* test_backpack_reliable.c -- backpack selection must come from the reliable
 * command stream ("mr 1 1 custom1/custom2"), because usercmd.weapon is 0 in
 * CODOL 3.19 live captures. Previously the reliable text was parsed and thrown
 * away, so the server always served the init weapon (1156).
 */
#include "codol_usercmd.h"
#include "codol_equipment.h"
#include <stdio.h>
#include <string.h>

static int fails;
#define CK(c, ...) do { if (!(c)) { printf("FAIL " __VA_ARGS__); printf("\n"); fails++; } } while (0)

/* Minimal encoder: opcode=2 reliable block(s) + opcode=0 + one idle cmd. */
static int build_body(unsigned char *out, const char *const *cmds, int n)
{
    /* bit writer mirroring ref_reader: LSB-first, bytes_ appends raw */
    int len = 0, bit = 0;
    unsigned char *d = out;
    memset(out, 0, 256);
    #define PUTBITS(v, nbits) do { \
        for (int _i = 0; _i < (nbits); _i++) { \
            if ((bit & 7) == 0) { bit = len * 8; d[len++] = 0; } \
            d[bit >> 3] |= (unsigned char)((((v) >> _i) & 1) << (bit & 7)); \
            bit++; \
        } } while (0)
    #define PUTBYTES(p, nbytes) do { \
        memcpy(d + len, (p), (nbytes)); len += (nbytes); } while (0)

    for (int i = 0; i < n; i++) {
        PUTBITS(2, 3);
        unsigned int seq = 100 + i;
        PUTBYTES(&seq, 4);
        PUTBYTES(cmds[i], (int)strlen(cmds[i]) + 1);
    }
    PUTBITS(0, 3);
    unsigned char one = 1;
    PUTBYTES(&one, 1);
    /* one idle cmd: time byte, then idle marker (1^key&1)==0 path -> bits(1)=0, bits(3)=7 */
    unsigned char t = 10;
    PUTBITS(0, 1);           /* time: not delta-1 */
    PUTBYTES(&t, 4);         /* absolute time (4 bytes) */
    PUTBITS(0, 1);           /* (bit ^ key&1)==0 with key=0 */
    PUTBITS(7, 3);           /* idle terminator */
    return len;
    #undef PUTBITS
    #undef PUTBYTES
}

int main(void)
{
    unsigned char body[256];
    codol_usercmd_list_t list;
    codol_equipment_t e;

    /* case 1: custom2 must switch to the 3-slot backpack */
    {
        const char *cmds[] = { "mr 1 1 custom2" };
        int n = build_body(body, cmds, 1);
        CK(codol_usercmd_parse(body, n, 0, NULL, &list), "parse failed");
        CK(list.reliable_count == 1, "reliable_count=%d (expect 1)", list.reliable_count);
        CK(strcmp(list.reliable[0], "mr 1 1 custom2") == 0,
           "reliable text=%s", list.reliable[0]);

        codol_equipment_init(&e);
        CK(e.slot_count == 2 && e.current_weapon == 309, "init state wrong");
        CK(codol_equipment_select_backpack(&e, list.reliable[0]), "select custom2 rejected");
        CK(e.slot_count == 3, "slot_count=%d (expect 3)", e.slot_count);
        CK(e.current_weapon == 1157, "current_weapon=%d (expect 1157)", e.current_weapon);
        printf("ok   custom2    slots=%d current=%d\n", e.slot_count, e.current_weapon);
    }

    /* case 2: custom1 must return to the single-slot backpack */
    {
        const char *cmds[] = { "mr 1 1 custom1" };
        int n = build_body(body, cmds, 1);
        CK(codol_usercmd_parse(body, n, 0, NULL, &list), "parse failed");
        codol_equipment_init(&e);
        codol_equipment_select_backpack(&e, "mr 1 1 custom2");
        CK(codol_equipment_select_backpack(&e, list.reliable[0]), "select custom1 rejected");
        CK(e.slot_count == 2 && e.current_weapon == 309, "custom1 -> slots=%d current=%d",
           e.slot_count, e.current_weapon);
        printf("ok   custom1    slots=%d current=%d\n", e.slot_count, e.current_weapon);
    }

    /* case 3: malformed command must be ignored, not crash */
    {
        codol_equipment_init(&e);
        CK(!codol_equipment_select_backpack(&e, "mr 2 0 custom3"), "bad command accepted");
        CK(e.slot_count == 2 && e.current_weapon == 309, "bad command mutated state");
        printf("ok   malformed  ignored, slots=%d current=%d\n", e.slot_count, e.current_weapon);
    }

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
