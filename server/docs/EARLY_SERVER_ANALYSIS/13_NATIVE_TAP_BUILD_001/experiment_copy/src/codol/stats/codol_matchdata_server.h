#ifndef CODOL_MATCHDATA_SERVER_H
#define CODOL_MATCHDATA_SERVER_H
#include "codol_structured_schema.h"
#pragma pack(push, 8)
/* Server match record. C1 keeps it in a 0xf800-byte buffer behind a 64-byte
 * definition name (Scr_SetMatchDataDef 0x553bf0, Scr_SetMatchData 0x553600,
 * Scr_GetMatchData 0x551cd0, Scr_ClearMatchData 0x551e00). It is separate from
 * the 0x400-byte client match record and is never cleared by the map change. */
#define CODOL_SERVER_MATCHDATA_CAPACITY 0xf800u
#define CODOL_SERVER_MATCHDATA_NAME 64u
typedef enum {
    CODOL_MATCHDATA_DEF_LOADED=0,
    CODOL_MATCHDATA_DEF_UNCHANGED,      /* same name: C1 returns without reload */
    CODOL_MATCHDATA_DEF_ALREADY_SET,
    CODOL_MATCHDATA_DEF_NAME_TOO_LONG,  /* >= 64 bytes */
    CODOL_MATCHDATA_DEF_UNAVAILABLE,    /* missing/invalid definition asset */
    CODOL_MATCHDATA_DEF_TOO_LARGE       /* record size above the buffer */
} codol_matchdata_def_status_t;
typedef struct {
    char name[CODOL_SERVER_MATCHDATA_NAME];
    codol_structured_schema_t schema;
    uint8_t record[CODOL_SERVER_MATCHDATA_CAPACITY];
} codol_server_matchdata_t;
/* Idempotent for an identical name; a different name requires a clear first.
 * Success writes the definition's LE version/checksum into the first eight
 * record bytes and leaves the remaining bytes untouched, as C1 does.
 * Failure preserves the whole state. */
codol_matchdata_def_status_t CODOL_SelectServerMatchData(const char *name);
/* NULL until a definition is selected and its schema is available. The schema
 * is reloaded on demand after the archives it borrows from were released. */
codol_server_matchdata_t *CODOL_ServerMatchData(void);
const char *CODOL_ServerMatchDataDef(void);
void CODOL_ClearServerMatchData(void);   /* C1 0x551e00: whole record and name */
/* Drop only the borrowed schema (names/offset map live in mounted archives).
 * The selected name and record survive; the next access reloads and checks the
 * stored version/checksum header. */
void CODOL_ReleaseServerMatchDataSchema(void);
void CODOL_ResetServerMatchData(void);
typedef struct {
    const char *name;
    const uint8_t *record;
    uint32_t version,checksum,id;
    size_t size;
} codol_server_matchdata_submission_t;
/* C1's queued sender (0x551d80 -> 0x5cf180) re-resolves the definition and
 * hands {record, definition size} to the upload path. Returns 1 with the
 * payload, 0 when no definition is selected, -1 when the definition is
 * unusable (C1 warns "Unknown def file %s" and submits a zero length). */
int CODOL_PrepareServerMatchDataSubmission(codol_server_matchdata_submission_t *out);
const codol_server_matchdata_submission_t *CODOL_LastServerMatchDataSubmission(void);
/* Outbound delivery seam. C1 hands the same {record,size} pair to its Live
 * upload queue (0x5cf22a -> 0x58eba0 -> 0x707470); the native server has no
 * equivalent backend yet. A registered sink owns the actual delivery and must
 * copy anything it keeps: the payload points at the live record. */
typedef int (*codol_server_matchdata_sink_t)(void *context,
    const codol_server_matchdata_submission_t *);
void CODOL_SetServerMatchDataSink(codol_server_matchdata_sink_t,void *context);
/* 1 delivered, 0 no sink registered, -1 the sink rejected the record. */
int CODOL_DeliverServerMatchData(const codol_server_matchdata_submission_t *);
/* C1's readable dump of the same record (0x6205d0, root name "Root", depth 1).
 * Two spaces of indentation per level capped at 15, scalars as
 * "<indent><name>\t= <value>\n", aggregates as "<indent><name>\n".
 * Returns 0 without emitting anything when no record is available. */
typedef void (*codol_matchdata_text_sink_t)(void *context,const char *text,size_t length);
int CODOL_WriteServerMatchDataReport(codol_matchdata_text_sink_t,void *context);
#pragma pack(pop)
#endif
