#ifndef CODOL_SCRIPT_PROFILE_VM_H
#define CODOL_SCRIPT_PROFILE_VM_H
#include "codol_structured_schema.h"
/* C1 keeps two script-visible profile buffers and one accessor for each:
 * GetPlayerData (0x551e20) reads mp/playerdata.def, the client's uploaded
 * mpdata, and GetSecurePlayerData (0x551ef0) reads mp/playersecuredata.def,
 * the server-attached mpdata_s. Both are 32768-byte blobs whose first four
 * bytes hold crc32(blob+4) and whose structured record starts at blob+4.
 *
 * The blobs themselves, their session edits and their lifetime belong to the
 * profile core (codol_stats.c and codol_profile_clients.c). This module only
 * adapts them to the VM and caches the two mounted definition sets. */
typedef enum {
    CODOL_PROFILE_PUBLIC = 0,
    CODOL_PROFILE_SECURE = 1
} codol_profile_buffer_t;
/* Mounted definition set for one buffer, cached until the assets it borrows
 * strings and offset maps from are dropped. NULL when the def is not mounted
 * or fails to parse. */
const codol_structured_schema_t *CODOL_ScriptProfileSchema(codol_profile_buffer_t);
/* The one view every profile reader shares: the session copy once a script has
 * written to it, otherwise the completed upload or the attached secure
 * profile. NULL when neither exists. */
const uint8_t *CODOL_ScriptProfileBlob(unsigned client,codol_profile_buffer_t);
/* Schema-selected definition plus the readable record of that blob. Returns 1
 * and borrowed pointers, or 0 with every output preserved. */
int CODOL_ScriptProfileView(unsigned client,codol_profile_buffer_t,
    const codol_structured_definition_t **definition,const uint8_t **record,size_t *capacity);
/* Drops the cached definition sets. Required whenever the mounted assets they
 * borrow from are released; per-client profile lifetime is not handled here. */
void CODOL_ResetScriptProfiles(void);
#ifdef CODOL_SERVER
#include "scr_vm.h"
void CODOL_Scr_GetPlayerData(scr_entref_t);
void CODOL_Scr_GetSecurePlayerData(scr_entref_t);
void CODOL_Scr_SetPlayerData(scr_entref_t);
/* Drops the per-client session store of IW4-only members (see the module
 * source). Called wherever the client's profile attachments are dropped. */
void CODOL_ScriptProfileForgetLegacy(unsigned client);
/* The IW4-only root store, exposed so a session can be carried across a
 * disconnect. Keys are path components joined with '/'; a value is either an
 * int or a short string. Enumeration order is insertion order. */
unsigned CODOL_ScriptProfileLegacyCount(unsigned client);
int CODOL_ScriptProfileLegacyEntry(unsigned client,unsigned index,const char **key,
    int *is_text,int *value,const char **text);
int CODOL_ScriptProfileLegacySet(unsigned client,const char *key,int is_text,int value,
    const char *text);
int CODOL_ScriptProfileLegacyGetInt(unsigned client,const char *key,int *value);
#endif
#endif
