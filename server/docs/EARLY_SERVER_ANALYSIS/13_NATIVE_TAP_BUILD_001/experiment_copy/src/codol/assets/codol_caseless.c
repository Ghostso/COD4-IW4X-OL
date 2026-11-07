/* Case-insensitive loose-file open for POSIX hosts. SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_caseless.h"
#include <errno.h>
#include <string.h>
#ifndef _WIN32
#include <dirent.h>
#include <strings.h>
#include <sys/stat.h>
#endif

FILE *CODOL_FOpenReadCaseless(const char *path)
{
#ifdef _WIN32
    return path ? fopen(path, "rb") : NULL;
#else
    char resolved[4096], component[256];
    const char *p;
    size_t used;
    FILE *file;
    if (!path || !*path) { errno = ENOENT; return NULL; }
    if ((file = fopen(path, "rb")) || errno != ENOENT) return file;
    /* Walk the path one component at a time, keeping every component that
     * exists as spelled and otherwise taking the directory entry that matches
     * it ignoring case. The first spelling found wins, as on a Windows host. */
    used = 0;
    p = path;
    if (*p == '/') { resolved[used++] = '/'; while (*p == '/') ++p; }
    resolved[used] = 0;
    while (*p) {
        const char *end = strchr(p, '/');
        size_t length = end ? (size_t)(end - p) : strlen(p);
        struct stat st;
        DIR *dir;
        struct dirent *entry;
        int found = 0;
        if (!length || length >= sizeof(component)) { errno = ENOENT; return NULL; }
        memcpy(component, p, length); component[length] = 0;
        if (used + length + 2 >= sizeof(resolved)) { errno = ENAMETOOLONG; return NULL; }
        memcpy(resolved + used, component, length + 1);
        if (stat(resolved, &st) == 0) found = 1;
        else {
            resolved[used] = 0;
            dir = opendir(used ? resolved : ".");
            if (dir) {
                while ((entry = readdir(dir)))
                    if (!strcasecmp(entry->d_name, component)) {
                        memcpy(resolved + used, entry->d_name, length + 1);
                        found = 1;
                        break;
                    }
                closedir(dir);
            }
        }
        if (!found) { errno = ENOENT; return NULL; }
        used += length;
        p += length;
        while (*p == '/') ++p;
        if (*p) resolved[used++] = '/';
        resolved[used] = 0;
    }
    return fopen(resolved, "rb");
#endif
}
