#ifndef CODOL_MSG_H
#define CODOL_MSG_H
/* 位流消息缓冲 —— 结构照 CoD4x 的 msg_t / MSG_* (同源直系)。
 * 位序: MSB-first; 与 CoD/Quake 家族一致。 */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool     overflowed;
    bool     readonly;
    uint8_t *data;
    uint8_t *split_data;
    int      maxsize;
    int      cursize;
    int      split_size;
    int      readcount;
    int      bit;
    int      last_ref_entity;
    int      length_offset;
} codol_msg_t;

void     codol_msg_init(codol_msg_t *m, uint8_t *data, int length);
void     codol_msg_init_readonly(codol_msg_t *m, uint8_t *data, int length);
void     codol_msg_begin_reading(codol_msg_t *m);
void     codol_msg_clear(codol_msg_t *m);

void     codol_msg_write_bits(codol_msg_t *m, uint32_t value, int bits);
uint32_t codol_msg_read_bits(codol_msg_t *m, int bits);

void     codol_msg_write_byte(codol_msg_t *m, int c);
int      codol_msg_read_byte(codol_msg_t *m);
void     codol_msg_write_short(codol_msg_t *m, int c);
int      codol_msg_read_short(codol_msg_t *m);
void     codol_msg_write_long(codol_msg_t *m, int c);
int      codol_msg_read_long(codol_msg_t *m);

void     codol_msg_write_data(codol_msg_t *m, const void *data, int len);
int      codol_msg_read_data(codol_msg_t *m, void *data, int len);
void     codol_msg_write_string(codol_msg_t *m, const char *s);
int      codol_msg_read_string(codol_msg_t *m, char *buf, int buflen);

/* 对齐: 把 bit 指针推到字节边界 */
void     codol_msg_align(codol_msg_t *m);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_MSG_H */
