/* IW4 script profiler markers. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_script_profiler.h"
#include "scr_vm_functions.h"

/* IW4 emits OP_prof_begin/OP_prof_end for these calls and its retail VM
 * executes them as no-ops (the profiler is compiled out); the compiler still
 * requires exactly one string argument. The retained IW3 compiler has neither
 * the token nor the opcode, so the same contract is enforced here as a
 * builtin: one string, no return value, no other effect. */
static void profiler_marker(const char *which)
{
    if(Scr_GetNumParam() != 1) {
        Scr_Error(va("%s takes exactly one parameter", which));
        return;
    }
    if(Scr_GetType(0) != VAR_STRING && Scr_GetType(0) != VAR_ISTRING) {
        Scr_ParamError(0, va("%s expects a profile name string", which));
        return;
    }
}
void CODOL_Scr_ProfBegin(void) { profiler_marker("prof_begin"); }
void CODOL_Scr_ProfEnd(void) { profiler_marker("prof_end"); }
#endif
