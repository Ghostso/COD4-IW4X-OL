/* Bit-level regression for native 0x670CB0 run coding. */
#include "codol_snapshot.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int read_bit(const uint8_t *p, int bit)
{
    return (p[bit >> 3] >> (bit & 7)) & 1;
}

static int read_bits(const uint8_t *p, int bit, int n)
{
    int i, v = 0;
    for (i = 0; i < n; ++i) v |= read_bit(p, bit + i) << i;
    return v;
}

/* Independent mirror of native 0x670CB0 for an 87-field playerState. */
static int decode_run_7bit(const uint8_t *p, int *bit)
{
    int run = 1, v;
    if (read_bit(p, *bit) == 1) { (*bit)++; return 1; }
    (*bit)++;
    do {
        v = read_bits(p, *bit, 7);
        *bit += 7;
        run += v;
    } while (v == 127);
    return run;
}

int main(void)
{
    codol_snap_equip_t eq;
    codol_snap_state_t from;
    uint8_t out[512];
    int n, bit = 8 * 11 + 10;
    codol_snap_equip_default(&eq);
    memset(&from, 0, sizeof(from));
    from.x = 1.0f;
    from.z = 2.0f;
    from.y = 3.0f;
    n = codol_snapshot_build(out, sizeof(out), 0, 1000, 1000, true,
                             48.0f, -572.0f, -116.0f, 0, 0, 0,
                             0.0f, 0.0f, 0.0f, false, false, true,
                             0, &from, NULL, &eq, NULL, 0);
    if (n <= 0 || bit + 16 > n * 8) {
        printf("snapshot build failed n=%d\n", n);
        return 1;
    }
    if (decode_run_7bit(out, &bit) != 1) {
        printf("field0 run must decode as 1 with seven-bit chunks\n");
        return 1;
    }
    puts("test_snapshot_run: all checks passed");
    return 0;
}
