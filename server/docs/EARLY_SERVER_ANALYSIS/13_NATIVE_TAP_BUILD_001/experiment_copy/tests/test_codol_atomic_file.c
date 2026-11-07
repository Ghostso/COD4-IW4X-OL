/* Real same-directory state replacement on a temporary filesystem path.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_atomic_file.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void contents(const char *path, const char *expected)
{
    char actual[32];
    FILE *file = fopen(path, "rb");
    size_t n;
    assert(file);
    n = fread(actual, 1, sizeof(actual), file);
    assert(!ferror(file) && fclose(file) == 0);
    assert(n == strlen(expected) && !memcmp(actual, expected, n));
}

int main(void)
{
    char root[256], path[300], temporary[304], directory[300], missing[340];
    const char *base = getenv("TMPDIR") ? getenv("TMPDIR") : "/tmp";
    struct stat st;
    FILE *file;
    assert(snprintf(root, sizeof(root), "%s/codol-atomic-XXXXXX", base) > 0);
    assert(mkdtemp(root));
    assert(snprintf(path, sizeof(path), "%s/codol_sessions.txt", root) > 0);
    assert(snprintf(temporary, sizeof(temporary), "%s.tmp", path) > 0);
    assert(snprintf(directory, sizeof(directory), "%s/existing-directory", root) > 0);
    assert(snprintf(missing, sizeof(missing), "%s/missing/state", root) > 0);
    file = fopen(path, "wb");
    assert(file && fwrite("old", 1, 3, file) == 3 && fclose(file) == 0);
    assert(CODOL_AtomicWriteFile(path, "new state", 9));
    contents(path, "new state");
    assert(stat(path, &st) == 0 && (st.st_mode & 0777) == 0600);
    assert(access(temporary, F_OK) != 0);
    assert(CODOL_AtomicWriteFile(path, NULL, 0));
    contents(path, "");
    assert(mkdir(directory, 0700) == 0);
    assert(!CODOL_AtomicWriteFile(directory, "bad", 3));
    assert(stat(directory, &st) == 0 && S_ISDIR(st.st_mode));
    assert(!CODOL_AtomicWriteFile(missing, "bad", 3));
    assert(unlink(path) == 0 && rmdir(directory) == 0 && rmdir(root) == 0);
    puts("CoDOL atomic session-file replacement and failure preservation passed");
    return 0;
}
