/* Same-directory replacement for native server state. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_ATOMIC_FILE_H
#define CODOL_ATOMIC_FILE_H
#include <stddef.h>
int CODOL_AtomicWriteFile(const char *path, const void *data, size_t length);
int CODOL_AtomicWriteHomeFile(const char *qpath, const void *data, size_t length);
#endif
