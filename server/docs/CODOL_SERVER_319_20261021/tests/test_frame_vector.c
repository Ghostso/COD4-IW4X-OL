/* 固定输入的帧向量: 与参照实现逐字节对比 */
#include "codol_battle.h"
#include <stdio.h>
#include <string.h>

int main(void)
{
    codol_battle_assoc_t a;
    uint8_t out[512];
    uint8_t plain[24];
    int n, i;

    memset(&a, 0, sizeof(a));
    a.in_use = true;
    a.key_ready = true;
    for (i = 0; i < 24; i++) a.transport_key[i] = (uint8_t)(0x10 + i);
    a.cookie[2] = 0x11; a.cookie[3] = 0x22;    /* client_tag */
    a.cookie[14] = 0xB8; a.cookie[15] = 0xBA; /* server_tag */
    a.send_seq = 0;

    plain[0] = 0xFF; plain[1] = 0xFF; plain[2] = 0xFF; plain[3] = 0xFF;
    memcpy(plain + 4, "challengeResponse 1", 19);
    plain[23] = 0;

    n = codol_battle_send_data(&a, plain, 24, out, sizeof(out));
    printf("len=%d\n", n);
    for (i = 0; i < n; i++) printf("%02X", out[i]);
    printf("\n");
    return 0;
}
