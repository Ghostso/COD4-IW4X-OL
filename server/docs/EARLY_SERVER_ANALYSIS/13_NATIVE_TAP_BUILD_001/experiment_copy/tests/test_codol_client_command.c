#include "codol_client_command.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void valid_command(void)
{
    uint8_t data[64];
    codol_msg_t writer, reader;
    uint32_t sequence = 0;
    char command[16] = "unchanged";

    CODOL_MsgWriteInit(&writer, data, sizeof(data));
    CODOL_WriteBits(&writer, 2, 3); /* already-read clc_clientCommand pool */
    CODOL_WriteLong(&writer, 17);
    CODOL_WriteString(&writer, "mr % 23");
    CODOL_WriteBits(&writer, 3, 3);
    assert(!writer.failed);

    CODOL_MsgReadInit(&reader, data, writer.size);
    assert(CODOL_ReadBits(&reader, 3) == 2);
    assert(CODOL_ReadClientCommand(&reader, &sequence, command, sizeof(command)));
    assert(sequence == 17);
    assert(!strcmp(command, "mr . 23"));
    assert(CODOL_ReadBits(&reader, 3) == 3);
    assert(!reader.failed);
}

static void rejected_atomically(const uint8_t *data, size_t size, size_t capacity)
{
    codol_msg_t reader, before;
    uint32_t sequence = UINT32_C(0xa5a5a5a5);
    char command[16], saved[16];

    memset(command, 0x5a, sizeof(command));
    memcpy(saved, command, sizeof(saved));
    CODOL_MsgReadInit(&reader, data, size);
    before = reader;
    assert(!CODOL_ReadClientCommand(&reader, &sequence, command, capacity));
    assert(reader.failed);
    assert(reader.cursor == before.cursor && reader.bit == before.bit);
    assert(sequence == UINT32_C(0xa5a5a5a5));
    assert(!memcmp(command, saved, sizeof(command)));
}

int main(void)
{
    static const uint8_t unterminated[] = {1,0,0,0,'n',' ','1'};
    static const uint8_t overlong[] = {2,0,0,0,'a','b','c','d',0};
    codol_msg_t message;
    uint32_t sequence = 0;
    char command[4] = {0};

    valid_command();
    rejected_atomically(unterminated, sizeof(unterminated), 16);
    rejected_atomically(overlong, sizeof(overlong), 4);

    CODOL_MsgReadInit(&message, overlong, sizeof(overlong));
    assert(!CODOL_ReadClientCommand(&message, NULL, command, sizeof(command)));
    CODOL_MsgReadInit(&message, overlong, sizeof(overlong));
    assert(!CODOL_ReadClientCommand(&message, &sequence, command, 0));
    puts("PASS: client reliable commands require an in-bounds NUL and publish atomically");
    return 0;
}
