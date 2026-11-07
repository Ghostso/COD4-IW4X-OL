/* CoDOL client reliable-command framing.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_CLIENT_COMMAND_H
#define CODOL_CLIENT_COMMAND_H

#include "codol_msg.h"

#define CODOL_CLIENT_COMMAND_MAX 1024u

/* Reads the payload following clc_clientCommand: a little-endian sequence and
 * a NUL-terminated command string. Output and the source cursor are atomic;
 * malformed or overlong input only marks the source failed. */
int CODOL_ReadClientCommand(codol_msg_t *message, uint32_t *sequence,
                            char *command, size_t capacity);

#endif
