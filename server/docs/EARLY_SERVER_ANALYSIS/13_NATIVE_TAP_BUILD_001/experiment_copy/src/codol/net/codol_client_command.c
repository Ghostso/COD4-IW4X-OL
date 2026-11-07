/* C1 retains the id client-command payload shape, but its surrounding message
 * uses CoDOL's interleaved bit/byte stream. The retained MSG_ReadString stops
 * at the destination limit without proving that a NUL was consumed, and also
 * returns a partial command after end-of-message. Either behavior can execute
 * and acknowledge a command before the next 3-bit opcode is known to be
 * aligned. Keep the CoDOL reader transactional instead.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_client_command.h"
#include <string.h>

int CODOL_ReadClientCommand(codol_msg_t *message, uint32_t *sequence,
                            char *command, size_t capacity)
{
    codol_msg_t read;
    char staged[CODOL_CLIENT_COMMAND_MAX];
    uint32_t parsed_sequence;
    size_t length = 0;

    if(!message) return 0;
    if(!sequence || !command || !capacity || capacity > sizeof(staged)) {
        message->failed = 1;
        return 0;
    }

    read = *message;
    parsed_sequence = CODOL_ReadLong(&read);
    while(!read.failed) {
        uint32_t value = CODOL_ReadByte(&read);
        if(read.failed) break;
        if(!value) {
            staged[length] = 0;
            *sequence = parsed_sequence;
            memcpy(command, staged, length + 1);
            *message = read;
            return 1;
        }
        if(length + 1 >= capacity) {
            read.failed = 1;
            break;
        }
        /* Preserve the retained command tokenizer's format-string hardening. */
        staged[length++] = value == '%' ? '.' : (char)value;
    }

    message->failed = 1;
    return 0;
}
