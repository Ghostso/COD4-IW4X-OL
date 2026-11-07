/*
 * Missing GSC natives, batch 3: MP spawn-selection line of sight and the
 * host-client predicate. Both names are called by the alpha MP script corpus
 * and this tree has no binding and no implementation for either.
 *
 * Reference handlers (IW4 iw4x.exe, the primary reference):
 *   spawnsighttrace  builtin table 0x0079ae7c  name 0x00705970  handler 0x005f7960
 *   ishost           method  table 0x0073cac0  name 0x006d9dac  handler 0x005deb80
 * Both table entries carry developer word 0, so neither is developer-only.
 *
 * The decoded contracts, the fork-local translation and the parts of the IW4
 * behaviour that are reproduced only partially are documented at each function
 * in src/codol_script_native_batch3.c. Candidate selection, the rejected
 * candidates and the registry integration this worker does not own are in
 * obj/claude-workers/gsc-native-batch3-checkpoint.md and -report.md.
 */
#ifndef __CODOL_SCRIPT_NATIVE_BATCH3_H__
#define __CODOL_SCRIPT_NATIVE_BATCH3_H__

#ifdef CODOL_SERVER

#include "q_shared.h"
#include "bg.h"
#include "scr_vm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* spawnsighttrace( <spawnpoint>, <from>, <to> ) -> float 0..1
 *
 * Global function, not a method: the spawn point is parameter 0. Returns how
 * much line of sight exists from <from> to <to>; 1 when the direct sight
 * trace is clear, 0 when nothing gets through, and a value in between when
 * only a laterally offset line gets through. maps/mp/gametypes/_spawnlogic
 * feeds the result to adjustSightValue(), which asserts the 0..1 range and
 * turns anything above 0 into a spawn-point weight penalty. */
void CODOL_Scr_SpawnSightTrace(void);
/* Resolve a positive native world-sight hit into midpoint/halfsize. Caller
 * must check success; spawn geometry consumes these bounds. */
int CODOL_SpawnSightHitBounds(int hit, vec3_t midpoint, vec3_t halfsize);

/* <player> ishost() -> bool
 *
 * True when the receiving player's connection is this machine's local
 * connection. Errors like every other player method when the receiver is not
 * a player entity. */
void CODOL_Scr_IsHost(scr_entref_t entref);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif
