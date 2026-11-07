#include "codol_msg.h"
#include <string.h>

void codol_msg_init(codol_msg_t *m, uint8_t *data, int length)
{
    memset(m, 0, sizeof(*m));
    m->data = data;
    m->maxsize = length;
    m->readonly = false;
}

void codol_msg_init_readonly(codol_msg_t *m, uint8_t *data, int length)
{
    memset(m, 0, sizeof(*m));
    m->data = data;
    m->maxsize = length;
    m->cursize = length;    /* ★ 只读模式必须预置已用长度, 否则一读即判溢出 */
    m->readonly = true;
}

void codol_msg_begin_reading(codol_msg_t *m) { m->readcount = 0; m->bit = 0; }
void codol_msg_clear(codol_msg_t *m) { m->overflowed = false; m->cursize = 0; m->bit = 0; m->readcount = 0; }

void codol_msg_write_bits(codol_msg_t *m, uint32_t value, int bits)
{
    int i;
    if (bits <= 0 || bits > 32 || m->readonly) return;
    if (m->bit == 0) {
        if (m->cursize >= m->maxsize) { m->overflowed = true; return; }
        m->data[m->cursize++] = 0;
    }
    for (i = bits - 1; i >= 0; i--) {
        if (value & (1u << i)) m->data[m->cursize - 1] |= (uint8_t)(1u << (7 - m->bit));   /* 字节内 MSB-first */
        m->bit = (m->bit + 1) & 7;
        if (m->bit == 0 && i != 0) {
            if (m->cursize >= m->maxsize) { m->overflowed = true; return; }
            m->data[m->cursize++] = 0;
        }
    }
}

uint32_t codol_msg_read_bits(codol_msg_t *m, int bits)
{
    uint32_t v = 0;
    int i;
    if (bits <= 0 || bits > 32) return 0;
    for (i = 0; i < bits; i++) {
        if (m->readcount >= m->cursize) { m->overflowed = true; return v; }
        v = (v << 1) | ((m->data[m->readcount] >> (7 - m->bit)) & 1);
        m->bit = (m->bit + 1) & 7;
        if (m->bit == 0) m->readcount++;
    }
    return v;
}

void codol_msg_write_byte(codol_msg_t *m, int c) { codol_msg_write_bits(m, (uint32_t)(c & 0xFF), 8); }
int  codol_msg_read_byte(codol_msg_t *m) { return (int)(codol_msg_read_bits(m, 8) & 0xFF); }
void codol_msg_write_short(codol_msg_t *m, int c) { codol_msg_write_bits(m, (uint32_t)(c & 0xFFFF), 16); }
int  codol_msg_read_short(codol_msg_t *m) { return (int)(codol_msg_read_bits(m, 16) & 0xFFFF); }
void codol_msg_write_long(codol_msg_t *m, int c) { codol_msg_write_bits(m, (uint32_t)c, 32); }
int  codol_msg_read_long(codol_msg_t *m) { return (int)codol_msg_read_bits(m, 32); }

void codol_msg_write_data(codol_msg_t *m, const void *data, int len)
{
    const uint8_t *p = (const uint8_t *)data;
    int i;
    for (i = 0; i < len; i++) codol_msg_write_byte(m, p[i]);
}

int codol_msg_read_data(codol_msg_t *m, void *data, int len)
{
    uint8_t *p = (uint8_t *)data;
    int i;
    for (i = 0; i < len; i++) p[i] = (uint8_t)codol_msg_read_byte(m);
    return len;
}

void codol_msg_write_string(codol_msg_t *m, const char *s)
{
    int i;
    if (!s) { codol_msg_write_byte(m, 0); return; }
    for (i = 0; s[i]; i++) codol_msg_write_byte(m, (uint8_t)s[i]);
    codol_msg_write_byte(m, 0);
}

int codol_msg_read_string(codol_msg_t *m, char *buf, int buflen)
{
    int i = 0, c;
    if (buflen <= 0) return 0;
    do {
        c = codol_msg_read_byte(m);
        if (i < buflen - 1) buf[i++] = (char)c;
    } while (c && i < buflen - 1);
    buf[i] = 0;
    return i;
}

void codol_msg_align(codol_msg_t *m)
{
    if (m->bit) { m->bit = 0; if (!m->readonly) { /* 已分配新字节则 cursize 已推进 */ } }
}
