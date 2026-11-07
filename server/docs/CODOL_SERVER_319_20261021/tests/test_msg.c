/* msg 位流层: 与 Python 参考位流逐字节对比 + 往返一致性 */
#include "codol_msg.h"
#include <stdio.h>
#include <string.h>

static int fails;
static uint8_t buf[256];

static void hexs(const uint8_t *d, size_t n, char *o)
{
    static const char *H = "0123456789abcdef"; size_t i;
    for (i = 0; i < n; i++) { o[i*2] = H[d[i]>>4]; o[i*2+1] = H[d[i]&15]; }
    o[n*2] = 0;
}

int main(void)
{
    codol_msg_t m;
    char hex[600], s[16];

    codol_msg_init(&m, buf, sizeof(buf));
    codol_msg_write_bits(&m, 0x5, 3);
    codol_msg_write_byte(&m, 0xAB);
    codol_msg_write_short(&m, 0x1234);
    codol_msg_write_long(&m, (int)0xDEADBEEF);
    codol_msg_write_string(&m, "hi");
    codol_msg_write_bits(&m, 0x7, 3);

    hexs(buf, (size_t)m.cursize, hex);
    if (strcmp(hex, "b562469bd5b7dded0d201c") != 0) {
        printf("FAIL 位流编码\n  got  %s\n  want b562469bd5b7dded0d201c\n", hex); fails++;
    } else printf("ok   位流编码   %s (%d B)\n", hex, m.cursize);

    /* 往返 */
    codol_msg_begin_reading(&m);
    if (codol_msg_read_bits(&m, 3) != 0x5) { printf("FAIL rt bits\n"); fails++; }
    if (codol_msg_read_byte(&m) != 0xAB) { printf("FAIL rt byte\n"); fails++; }
    if (codol_msg_read_short(&m) != 0x1234) { printf("FAIL rt short\n"); fails++; }
    if ((uint32_t)codol_msg_read_long(&m) != 0xDEADBEEFu) { printf("FAIL rt long\n"); fails++; }
    codol_msg_read_string(&m, s, sizeof(s));
    if (strcmp(s, "hi")) { printf("FAIL rt string (%s)\n", s); fails++; }
    if (codol_msg_read_bits(&m, 3) != 0x7) { printf("FAIL rt bits2\n"); fails++; }
    if (!fails) printf("ok   往返读取   全部字段一致\n");

    printf("\n%s (%d)\n", fails ? "FAILED" : "ALL PASSED", fails);
    return fails ? 1 : 0;
}
