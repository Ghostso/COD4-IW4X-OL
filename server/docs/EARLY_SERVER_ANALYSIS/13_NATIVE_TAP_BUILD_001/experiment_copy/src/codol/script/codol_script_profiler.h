/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCRIPT_PROFILER_H
#define CODOL_SCRIPT_PROFILER_H
#ifdef __cplusplus
extern "C" {
#endif
/* IW4 script profiler markers prof_begin(name) / prof_end(name). The retained
 * IW3 grammar has no token for them and this VM has no OP_prof_* handler, so
 * they are ordinary builtins here. Retail IW4 compiles the profiler out and
 * both markers only validate their argument; that is the behavior kept. */
void CODOL_Scr_ProfBegin(void);
void CODOL_Scr_ProfEnd(void);
#ifdef __cplusplus
}
#endif
#endif
