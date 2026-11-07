#ifndef CODOL_SCRIPT_SOURCE_H
#define CODOL_SCRIPT_SOURCE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Source-only roots: overlay, base/mp, then base, followed by the exact
 * alpha0022 US Army LMG/SMG-B export-filename corrections. No match returns 0;
 * Two exact damaged reference head-alias bodies receive whitespace repairs.
 * Overlay contents never receive these repairs.
 * malformed/unreadable source returns -1 without falling through. Success
 * returns 1 and an owned NUL-terminated buffer; caller frees it. */
int CODOL_ReadScriptSource(const char *base,const char *overlay,const char *name,
    char **out,size_t *length);
/* Same validation/ownership, with server-owned adaptations between the
 * user overlay and reference roots. Empty native_overlay omits this layer. */
int CODOL_ReadScriptSourceWithNativeOverlay(const char *base,const char *overlay,
    const char *native_overlay,const char *name,char **out,size_t *length);
/* Same, with the mounted map's CoDOL asset category ("mp", "coop", "zm")
 * selecting <native_overlay>/<zone_type>/<name> ahead of <native_overlay>/<name>,
 * so a category's gametype, callback and level scripts replace the shared
 * multiplayer ones under their own module names instead of being copied.
 * A NULL, empty or non-lowercase zone_type omits the layer, leaving the
 * multiplayer resolution order unchanged. */
int CODOL_ReadScriptSourceWithNativeOverlayForZone(const char *base,const char *overlay,
    const char *native_overlay,const char *zone_type,const char *name,char **out,size_t *length);
/* Any root may be "fs:<dir>": its files are read through this host reader
 * instead of the OS filesystem (the server passes its search-path reader, so a
 * script tree can ship inside an .iwd). The reader returns 1 with a malloc'd
 * buffer of at least length+1 bytes, 0 when the file does not exist, -1 on error. */
typedef int (*codol_script_fs_reader_t)(const char *path,char **out,size_t *length);
void CODOL_SetScriptFsReader(codol_script_fs_reader_t reader);
#ifdef __cplusplus
}
#endif
#endif
