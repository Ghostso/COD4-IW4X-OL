#ifndef CODOL_SCRIPT_PERSIST_H
#define CODOL_SCRIPT_PERSIST_H

#ifdef __cplusplus
extern "C" {
#endif

/* The clients' pers[] objects, the per-client roots the round-restart struct
 * sweep (Scr_FreeObjects) must spare; game[] is the VM's own root. */
unsigned CODOL_ScriptPersistRoots(unsigned *roots, unsigned max);

#ifdef __cplusplus
}
#endif

#endif
