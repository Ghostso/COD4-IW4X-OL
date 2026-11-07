/* Lobby -> game server admission roster. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_admission.h"
#include "codol_crypto.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "cvar.h"
#include "qcommon_io.h"
#endif

#define ROSTER_MAX 256
#define ROSTER_BYTES (64 * 1024)

static codol_admission_entry_t roster[ROSTER_MAX];
static size_t roster_count;
static char roster_path[1024];
static long long roster_mtime = -1, roster_size = -1, roster_mtime_ns = -1, roster_inode = -1;
#ifdef CODOL_SERVER
static cvar_t *admission_path, *admission_required;
#endif

static void erase(void *ptr, size_t n)
{ volatile uint8_t *p = ptr; while (n--) *p++ = 0; }

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static const char *field(const char *p, char *out, size_t cap)
{
    size_t n = 0;
    while (*p == ' ' || *p == '\t') ++p;
    while (*p && *p != ' ' && *p != '\t' && *p != '\r' && *p != '\n') {
        if (n + 1 >= cap) return NULL;
        out[n++] = *p++;
    }
    out[n] = 0;
    return n ? p : NULL;
}

int CODOL_AdmissionParseLine(const char *line, codol_admission_entry_t *out)
{
    char ip[16], key[33], uid[17], expires[24], tag[33];
    codol_admission_entry_t e;
    unsigned a, b, c, d;
    size_t i;
    char *end;
    const char *p = line;
    if (!line || !out) return 0;
    while (*p == ' ' || *p == '\t') ++p;
    if (!*p || *p == '#' || *p == '\r' || *p == '\n') return 0;
    memset(&e, 0, sizeof(e));
    if (!(p = field(p, ip, sizeof(ip))) || !(p = field(p, key, sizeof(key))) ||
        !(p = field(p, uid, sizeof(uid))) || !(p = field(p, expires, sizeof(expires))) ||
        !(p = field(p, tag, sizeof(tag)))) return 0;
    if (sscanf(ip, "%u.%u.%u.%u", &a, &b, &c, &d) != 4 || a > 255 || b > 255 || c > 255 || d > 255)
        return 0;
    e.ip[0] = (uint8_t)a; e.ip[1] = (uint8_t)b; e.ip[2] = (uint8_t)c; e.ip[3] = (uint8_t)d;
    if (strlen(key) != 32) return 0;
    for (i = 0; i < 16; ++i) {
        int hi = hexval(key[2 * i]), lo = hexval(key[2 * i + 1]);
        if (hi < 0 || lo < 0) return 0;
        e.key[i] = (uint8_t)(hi << 4 | lo);
    }
    if (strcmp(uid, "0")) {
        if (strlen(uid) != 16) return 0;
        for (i = 0; i < 16; ++i) {
            int v = hexval(uid[i]);
            if (v < 0) return 0;
            e.uid = e.uid << 4 | (uint64_t)v;
        }
    }
    e.expires = strtoll(expires, &end, 10);
    if (*end || e.expires <= 0) return 0;
    /* A gamertag is a website username: printable, no info-string separators. */
    for (i = 0; tag[i]; ++i)
        if ((unsigned char)tag[i] <= 32 || (unsigned char)tag[i] >= 127 || tag[i] == '\\' ||
            tag[i] == '"' || tag[i] == ';' || tag[i] == '%') return 0;
    /* "-" is the lobby's placeholder for a seat whose gamertag is unknown. */
    if (strcmp(tag, "-")) memcpy(e.gamertag, tag, i + 1);
    *out = e;
    erase(&e, sizeof(e));
    return 1;
}

static const char *configured_path(void)
{
#ifdef CODOL_SERVER
    /* Empty: the lobby writes the roster beside securitykey.bin, so derive it
     * from codol_securityKeyPath and existing launchers need no new setting. */
    static char derived[1024];
    cvar_t *key;
    const char *slash;
    size_t dir;
    if (admission_path && admission_path->string[0]) return admission_path->string;
    key = Cvar_FindVar("codol_securityKeyPath");
    if (!key || !key->string[0]) return "";
    slash = strrchr(key->string, '/');
    if (!slash || (strrchr(key->string, '\\') && strrchr(key->string, '\\') > slash))
        slash = strrchr(key->string, '\\');
    dir = slash ? (size_t)(slash - key->string) + 1 : 0;
    if (dir + sizeof("game_admissions.txt") > sizeof(derived)) return "";
    memcpy(derived, key->string, dir);
    memcpy(derived + dir, "game_admissions.txt", sizeof("game_admissions.txt"));
    return derived;
#else
    return getenv("CODOL_ADMISSION_PATH") ? getenv("CODOL_ADMISSION_PATH") : "";
#endif
}

/* Nanoseconds of the modification time where the platform keeps them. */
static long long mtime_ns(const struct stat *st)
{
#if defined(__linux__) && defined(_STATBUF_ST_NSEC)
    return (long long)st->st_mtim.tv_nsec;
#else
    (void)st; return 0;
#endif
}

/* Re-read the roster when its path, inode, size or modification time changed.
 * The lobby replaces the file (temp + os.replace), so every write is a new
 * inode; seconds and size alone missed a second write in the same second with
 * the same size -- which the lobby does on every createSession (the uid-latch
 * refresh republishes the old key, then the new key replaces it), leaving the
 * new key off the roster until some later write. A missing or unreadable file
 * is an empty roster. */
static void reload(void)
{
    const char *path = configured_path();
    struct stat st;
    FILE *file;
    char *text, *line, *next;
    size_t n;
    if (!path || !*path || strlen(path) >= sizeof(roster_path)) {
        erase(roster, sizeof(roster)); roster_count = 0; roster_path[0] = 0; return;
    }
    if (stat(path, &st) != 0) {
        erase(roster, sizeof(roster)); roster_count = 0;
        roster_mtime = roster_size = roster_mtime_ns = roster_inode = -1;
        strcpy(roster_path, path); return;
    }
    /* Windows CRT stat can expose only second-resolution modification time
     * and no useful replacement identity. The lobby can publish two same-size
     * rosters in that interval. Admission is consulted at handshake/connect,
     * so re-reading this bounded file is preferable to retaining an old key. */
#if !defined(_WIN32) && !defined(CODOL_TEST_COARSE_STAT)
    if (!strcmp(roster_path, path) && roster_mtime == (long long)st.st_mtime &&
        roster_mtime_ns == mtime_ns(&st) && roster_inode == (long long)st.st_ino &&
        roster_size == (long long)st.st_size) return;
#endif
    strcpy(roster_path, path);
    roster_mtime = (long long)st.st_mtime; roster_size = (long long)st.st_size;
    roster_mtime_ns = mtime_ns(&st); roster_inode = (long long)st.st_ino;
    erase(roster, sizeof(roster)); roster_count = 0;
    if (st.st_size <= 0 || st.st_size > ROSTER_BYTES || !(file = fopen(path, "rb"))) return;
    text = malloc((size_t)st.st_size + 1);
    if (!text) { fclose(file); return; }
    n = fread(text, 1, (size_t)st.st_size, file);
    fclose(file);
    text[n] = 0;
    for (line = text; line && *line && roster_count < ROSTER_MAX; line = next) {
        next = strchr(line, '\n');
        if (next) *next++ = 0;
        if (CODOL_AdmissionParseLine(line, &roster[roster_count])) ++roster_count;
    }
    erase(text, n);
    free(text);
}

static int live(const codol_admission_entry_t *e)
{ return e->expires > (long long)time(NULL); }

size_t CODOL_AdmissionCandidates(const uint8_t ip[4], uint8_t keys[][16], size_t max)
{
    size_t i, count = 0;
    int pass;
    if (!keys || !max) return 0;
    reload();
    for (pass = 0; pass < 2; ++pass)
        for (i = 0; i < roster_count && count < max; ++i) {
            int same = ip && !memcmp(roster[i].ip, ip, 4);
            if (!live(&roster[i]) || same != !pass) continue;
            memcpy(keys[count++], roster[i].key, 16);
        }
    return count;
}

int CODOL_AdmissionIdentify(const uint8_t ip[4], const uint8_t shared_x[28],
                            const uint8_t data_key[24], codol_admission_entry_t *out)
{
    uint8_t derived[24];
    size_t i;
    int pass;
    if (!shared_x || !data_key || !out) return 0;
    reload();
    for (pass = 0; pass < 2; ++pass)
        for (i = 0; i < roster_count; ++i) {
            int same = ip && !memcmp(roster[i].ip, ip, 4);
            if (!live(&roster[i]) || same != !pass) continue;
            if (CODOL_DeriveKey(derived, shared_x, roster[i].key) && !memcmp(derived, data_key, 24)) {
                *out = roster[i];
                erase(derived, sizeof(derived));
                return 1;
            }
        }
    erase(derived, sizeof(derived));
    return 0;
}

int CODOL_AdmissionMember(const uint8_t ip[4], uint64_t uid, codol_admission_entry_t *out)
{
    size_t i;
    if (!ip || !uid || !out) return 0;
    reload();
    for (i = 0; i < roster_count; ++i)
        if (live(&roster[i]) && roster[i].uid == uid && !memcmp(roster[i].ip, ip, 4)) {
            *out = roster[i];
            return 1;
        }
    return 0;
}

#ifdef CODOL_SERVER
void CODOL_AdmissionInit(void)
{
    admission_path = Cvar_RegisterString("codol_admissionPath", "", 0,
        "Lobby admission roster; empty = game_admissions.txt beside codol_securityKeyPath");
    admission_required = Cvar_RegisterBool("codol_admissionRequired", qfalse, 0,
        "Refuse clients the lobby has not admitted (needs codol_admissionPath)");
}
int CODOL_AdmissionRequired(void)
{ return admission_required && admission_required->boolean; }
#else
void CODOL_AdmissionInit(void) {}
int CODOL_AdmissionRequired(void) { return getenv("CODOL_ADMISSION_REQUIRED") != NULL; }
#endif
