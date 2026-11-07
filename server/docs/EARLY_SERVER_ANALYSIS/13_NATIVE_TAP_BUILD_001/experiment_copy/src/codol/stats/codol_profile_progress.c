/* Server-side persistence for the IW4-only playerdata roots.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_profile_progress.h"
#include "codol_script_profile_vm.h"
#include "codol_profile.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include "cvar.h"
#include "filesystem.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define PROGRESS_DIR "codol_progress"
#define PROGRESS_LINE 320

/* A key is a playerdata path with its components joined by '/', so it can
 * contain letters, digits, underscores, '#' and '/'. Anything else means the
 * file was not written by this server and is refused rather than guessed at. */
static int key_is_sane(const char *key)
{
    const char *p;
    if (!key || !*key) return 0;
    for (p = key; *p; ++p) {
        if ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
            (*p >= '0' && *p <= '9') || *p == '_' || *p == '/' || *p == '#' ||
            *p == '-' || *p == '.') continue;
        return 0;
    }
    return 1;
}

/* Text values are short and script-authored. Newlines and control characters
 * would break the line format, so they are refused on the way out; nothing in
 * the IW4 scripts writes one. */
static int text_is_sane(const char *text)
{
    const char *p;
    if (!text) return 0;
    for (p = text; *p; ++p)
        if ((unsigned char)*p < 0x20 || (unsigned char)*p == 0x7f) return 0;
    return 1;
}

static int progress_path(uint64_t uid, char *out, size_t size)
{
    const char *home = fs_homepath && fs_homepath->string ? fs_homepath->string : "";
    int n;
    if (!uid || !out || !size) return 0;
    n = snprintf(out, size, "%s/" PROGRESS_DIR "/%llu.txt", home, (unsigned long long)uid);
    if (n <= 0 || (size_t)n >= size) return 0;
    /* FS_CreatePath recognizes the platform separator, unlike fopen which
     * also accepts forward slashes on Windows. Normalize before either use. */
    FS_ReplaceSeparators(out);
    return 1;
}

int CODOL_LoadClientProgress(unsigned client, uint64_t uid)
{
    char path[MAX_OSPATH], line[PROGRESS_LINE];
    FILE *file;
    int restored = 0, bad = 0;
    if (!progress_path(uid, path, sizeof(path))) return -1;
    file = fopen(path, "rb");
    if (!file) return 0;
    while (fgets(line, sizeof(line), file)) {
        char *equals, *value;
        size_t length = strlen(line);
        while (length && (line[length - 1] == '\n' || line[length - 1] == '\r')) line[--length] = 0;
        if (!length || line[0] == '#') continue;
        equals = strchr(line, '=');
        if (!equals || equals == line) { bad = 1; break; }
        *equals = 0;
        value = equals + 1;
        if (!key_is_sane(line)) { bad = 1; break; }
        /* "i:" is an integer, "s:" a string. An unknown tag is a format
         * change, not something to interpret. */
        if (value[0] == 'i' && value[1] == ':') {
            if (!CODOL_ScriptProfileLegacySet(client, line, 0, atoi(value + 2), NULL)) { bad = 1; break; }
        } else if (value[0] == 's' && value[1] == ':') {
            if (!text_is_sane(value + 2) ||
                !CODOL_ScriptProfileLegacySet(client, line, 1, 0, value + 2)) { bad = 1; break; }
        } else { bad = 1; break; }
        ++restored;
    }
    fclose(file);
    if (bad) {
        Com_PrintWarning(CON_CHANNEL_SYSTEM,
            "CoDOL progress: %s is malformed; %d entries restored before stopping\n", path, restored);
        return -1;
    }
    if (restored)
        Com_Printf(CON_CHANNEL_SYSTEM, "CoDOL progress: restored %d entries for client %u\n",
                   restored, client);
    return restored;
}

int CODOL_SaveClientProgress(unsigned client, uint64_t uid)
{
    char path[MAX_OSPATH], directory[MAX_OSPATH];
    const char *home = fs_homepath && fs_homepath->string ? fs_homepath->string : "";
    FILE *file;
    unsigned count = CODOL_ScriptProfileLegacyCount(client), i;
    int written = 0, n;
    if (!count) return 0;
    if (!progress_path(uid, path, sizeof(path))) return -1;
    n = snprintf(directory, sizeof(directory), "%s/" PROGRESS_DIR, home);
    if (n <= 0 || (size_t)n >= sizeof(directory)) return -1;
    FS_CreatePath(path);
    file = fopen(path, "wb");
    if (!file) {
        Com_PrintWarning(CON_CHANNEL_SYSTEM, "CoDOL progress: cannot write %s\n", path);
        return -1;
    }
    fprintf(file, "# CoDOL server progression store for uid %llu\n", (unsigned long long)uid);
    fprintf(file, "# Written by the server, never uploaded and never read by the client.\n");
    for (i = 0; i < count; ++i) {
        const char *key = NULL, *text = NULL;
        int is_text = 0, value = 0;
        if (!CODOL_ScriptProfileLegacyEntry(client, i, &key, &is_text, &value, &text)) continue;
        if (!key_is_sane(key)) continue;
        if (is_text) {
            if (!text_is_sane(text)) continue;
            if (fprintf(file, "%s=s:%s\n", key, text) < 0) break;
        } else {
            if (fprintf(file, "%s=i:%d\n", key, value) < 0) break;
        }
        ++written;
    }
    if (fclose(file)) return -1;
    Com_DPrintf(CON_CHANNEL_SYSTEM, "CoDOL progress: saved %d entries for client %u (uid %llu)\n",
                written, client, (unsigned long long)uid);
    return written;
}

void CODOL_SaveClientProgressIfAttached(unsigned client)
{
    uint64_t uid = 0;
    if (!CODOL_ClientSecureProfile(client, &uid) || !uid) return;
    CODOL_SaveClientProgress(client, uid);
}
#endif
