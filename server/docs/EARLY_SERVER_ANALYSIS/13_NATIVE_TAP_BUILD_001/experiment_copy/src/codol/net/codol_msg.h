/* CoDOL's interleaved byte/bit message stream. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_MSG_H
#define CODOL_MSG_H
#include <stddef.h>
#include <stdint.h>

/* Semantic state must not inherit engine-header packing. */
#pragma pack(push, 8)
typedef struct {
    uint8_t *data;
    size_t size, capacity, cursor, bit;
    int failed;
} codol_msg_t;

void CODOL_MsgReadInit(codol_msg_t *m, const void *data, size_t size);
void CODOL_MsgWriteInit(codol_msg_t *m, void *data, size_t capacity);
uint32_t CODOL_ReadBits(codol_msg_t *m, unsigned bits);
uint32_t CODOL_ReadByte(codol_msg_t *m);
uint32_t CODOL_ReadShort(codol_msg_t *m);
uint32_t CODOL_ReadLong(codol_msg_t *m);
int CODOL_ReadData(codol_msg_t *m, void *out, size_t size);
void CODOL_WriteBits(codol_msg_t *m, uint32_t value, unsigned bits);
void CODOL_WriteByte(codol_msg_t *m, uint32_t value);
void CODOL_WriteShort(codol_msg_t *m, uint32_t value);
void CODOL_WriteLong(codol_msg_t *m, uint32_t value);
void CODOL_WriteData(codol_msg_t *m, const void *data, size_t size);
void CODOL_WriteString(codol_msg_t *m, const char *text);
#pragma pack(pop)
#endif
