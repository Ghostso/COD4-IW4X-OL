#ifndef CODOL_MATCHDATA_H
#define CODOL_MATCHDATA_H
#include "codol_structured_schema.h"
#include "codol_msg.h"
#pragma pack(push, 8)
#define CODOL_CLIENT_MATCHDATA_CAPACITY 1024
typedef struct {
    char name[64];
    codol_structured_schema_t schema;
    uint8_t record[CODOL_CLIENT_MATCHDATA_CAPACITY];
} codol_client_matchdata_t;
/* Native per-server record; reset at SV_ClearServer before another map starts.
 * Schema arrays are owned; strings/maps borrow mounted archive lifetimes. */
void CODOL_ResetClientMatchData(void);
/* Idempotent for the same ASCII-case-insensitive name. Different selections
 * require server reset. Failed loads preserve all state. */
int CODOL_SelectClientMatchData(const char *name);
codol_client_matchdata_t *CODOL_ClientMatchData(void);
void CODOL_RequestClientMatchData(unsigned client);
void CODOL_AcknowledgeClientMatchData(unsigned client);
int CODOL_ClientMatchDataDue(unsigned client,uint32_t time);
void CODOL_ClientMatchDataSent(unsigned client,uint32_t time);
/* Append opcode 4/name/NUL/full record before the enclosing message EOF.
 * Whole-byte fields preserve any pending bit pool. Invalid input/capacity
 * sets message.failed without changing size, bit cursor or payload bytes. */
int CODOL_WriteClientMatchDataSection(codol_msg_t *,const char *name,
    const uint8_t *record,size_t record_size);
#pragma pack(pop)
#endif
