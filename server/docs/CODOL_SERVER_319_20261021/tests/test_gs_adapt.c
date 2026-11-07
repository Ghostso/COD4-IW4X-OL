/* test_gs_adapt: 用 active_room.json 适配 gamestate fixture, 产物落盘供与
 * reference/dynamic_gamestate.py 逐字节对拍。
 *
 * 用法: test_gs_adapt <fixture.bin> <room.json> <out.bin>
 *       test_gs_adapt <fixture.bin> -          <out.bin>   # 不做适配, 原样拷贝(对照)
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#define GS_LOG_WARN(...) do { printf("WARN: "); printf(__VA_ARGS__); printf("\n"); } while (0)
#include "../src/battle/gs_adapt.h"

int main(int argc, char **argv)
{
    static uint8_t state[1200];
    FILE *fp;
    size_t n;
    int rc;

    if (argc < 4) {
        printf("usage: %s <fixture.bin> <room.json|-> <out.bin>\n", argv[0]);
        return 2;
    }
    fp = fopen(argv[1], "rb");
    if (!fp) { printf("open fixture failed: %s (errno=%d)\n", argv[1], errno); return 1; }
    n = fread(state, 1, sizeof(state), fp);
    fclose(fp);

    fp = fopen(argv[3], "wb");
    if (!fp) { printf("open out failed: %s (errno=%d)\n", argv[3], errno); return 1; }

    if (strcmp(argv[2], "-") == 0) {
        rc = 0;
    } else {
        rc = _gs_adapt_dynamic(state, sizeof(state), &n, argv[2]);
    }
    printf("adapt rc=%d len=%zu\n", rc, n);

    fwrite(state, 1, n, fp);
    fclose(fp);
    return rc == 0 ? 0 : 3;
}
