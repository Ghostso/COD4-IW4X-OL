/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SHOCK_RAWFILE_H
#define CODOL_SHOCK_RAWFILE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Rewrites a C1 shock/<name>.shock text whose dvars are named by registration
 * number (66..92) into the retained bg_shock_* names; other lines are copied.
 * 1 with an owned, NUL-terminated buffer; 0 on failure (outputs unchanged). */
int CODOL_TranslateShockText(const char *text, size_t length, char **out, size_t *out_length);
#ifdef __cplusplus
}
#endif
#endif
