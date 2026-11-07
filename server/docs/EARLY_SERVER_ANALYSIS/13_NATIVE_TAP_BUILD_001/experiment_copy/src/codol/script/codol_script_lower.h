#ifndef CODOL_SCRIPT_LOWER_H
#define CODOL_SCRIPT_LOWER_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Adapts the extended GSC source constructs used by the CoDOL script corpus to
 * the grammar the retained native scanner/parser accepts: file scope constant
 * declarations (literals, localized strings, vectors and constant expressions
 * over earlier constants of the same file), foreach/foreach key,value, and the
 * explicit call [[func]]() pointer-call marker. Constants stay file scoped and
 * never rewrite function names. childthread is left for codol_script_childthread.
 * 1: owned transformed source; 0: unchanged; -1: invalid/unsupported syntax.
 * Outputs are unchanged unless successful. Caller frees transformed source. */
int CODOL_LowerScriptSyntax(const char *,size_t,char **,size_t *);
/* Verifies that the C++ containers this pass relies on have the layout the
 * linked standard library expects. Returns 3 when correct. A wrong answer
 * means a translation unit built its container templates under a different
 * #pragma pack and the linker chose those copies; see stringed_ingame.cpp. */
int CODOL_ScriptLowerSelfTest(void);
/* Names the construct that made the most recent call fail and its 1-based line,
 * or returns NULL when the failure was not a recognised construct. The returned
 * string is static; the value is only meaningful after a -1 result. */
const char *CODOL_LowerScriptDiagnostic(unsigned *);
/* Installs the builtin lookup used to redirect ::name pointers to registered
 * builtins (0 unknown, 1 function, 2 method); NULL disables the rewrite. */
void CODOL_SetScriptBuiltinResolver(int (*)(const char *));
#ifdef __cplusplus
}
#endif
#endif
