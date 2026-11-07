/* gamestate 载荷向量: u32 seq + state, [8:] ^= (seq^1)&0xFF */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

int main(void)
{
    FILE *fp = fopen("firingrange-gamestate.bin", "rb");
    uint8_t state[1200], payload[1208];
    size_t n; uint32_t seq = 1; uint8_t mask; int i, total;

    if (!fp) { printf("no file\n"); return 1; }
    n = fread(state, 1, sizeof(state), fp);
    fclose(fp);

    total = 4 + (int)n;
    payload[0]=(uint8_t)seq; payload[1]=(uint8_t)(seq>>8);
    payload[2]=(uint8_t)(seq>>16); payload[3]=(uint8_t)(seq>>24);
    memcpy(payload + 4, state, n);
    mask = (uint8_t)((seq ^ 1) & 0xFF);
    for (i = 8; i < total; i++) payload[i] ^= mask;

    printf("len=%d\n", total);
    for (i = 0; i < total && i < 40; i++) printf("%02X", payload[i]);
    printf("\n");
    return 0;
}
