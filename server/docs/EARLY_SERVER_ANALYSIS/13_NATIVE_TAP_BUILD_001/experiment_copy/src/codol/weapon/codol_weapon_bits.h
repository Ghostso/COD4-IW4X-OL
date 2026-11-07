/* The four per-weapon playerState arrays, at the full 700-slot native width.
 *
 * Why they are not in playerState_t: the retained IW3 struct gives them 48
 * bytes at 0x55c (weapons, weaponold, weaponrechamber - 128 bits each) and 128
 * bytes at 0x81c (weaponmodels), and sizeof(playerState_t) cannot change
 * because 521 retained-assembly sites address gclient_t members at or past
 * 0x2f64. C1 registers 700 definitions, so all four moved into the playerState
 * extension (codol_playerstate_ext.h), which is keyed by the storage the state
 * lives in - live client, snapshot ring slot, or archive slot - and therefore
 * travels with the state through a snapshot, an archive rebuild and a
 * spectator's follow. Keying them by ps->clientNum would have been wrong for
 * the reason that header states: a spectator's own playerState carries the
 * followed player's clientNum.
 *
 * Retained assembly reaches these through src/asmsource/codol_weapon_bits.inc.
 * The four bit and model entry points below are the cdecl callees those macros
 * use and take a site tag so a misidentified playerState register names itself
 * in the log instead of corrupting memory.
 */
#ifndef CODOL_WEAPON_BITS_H
#define CODOL_WEAPON_BITS_H

#include <stdint.h>
#include "player.h"
#include "codol_weapon_slots.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    CODOL_WB_ARRAY_OWNED = 0,
    CODOL_WB_ARRAY_OLD = 1,
    CODOL_WB_ARRAY_RECHAMBER = 2,
    CODOL_WB_ARRAY_COUNT = 3
};

/* Where the assembly macros leave a 32-bit result across their popad. The
 * server is single threaded and the value is consumed by the instruction that
 * follows the macro, so one slot is enough. */
extern uint32_t codol_weapbits_result;

/* cdecl, called from retained assembly. word is the index the site had already
 * computed (weapon >> 5); a negative or out-of-range word reads as zero and is
 * ignored on write. */
uint32_t CODOL_WeaponBitsRead(const playerState_t *ps, int array, int word, uint32_t site);
void CODOL_WeaponBitsOr(const playerState_t *ps, int array, int word, uint32_t bits, uint32_t site);
void CODOL_WeaponBitsAnd(const playerState_t *ps, int array, int word, uint32_t mask, uint32_t site);
uint32_t CODOL_WeaponModelRead(const playerState_t *ps, int weapon, uint32_t site);
void CODOL_WeaponModelWrite(const playerState_t *ps, int weapon, uint32_t model, uint32_t site);

/* The same state for C callers, by weapon index rather than by word. */
int CODOL_WeaponBitsOwned(const playerState_t *ps, unsigned weapon);
int CODOL_WeaponBitsOldTest(const playerState_t *ps, unsigned weapon);
int CODOL_WeaponBitsRechamberTest(const playerState_t *ps, unsigned weapon);
void CODOL_WeaponBitsOwnedSet(const playerState_t *ps, unsigned weapon, int owned);
void CODOL_WeaponBitsOldSet(const playerState_t *ps, unsigned weapon, int old);
void CODOL_WeaponBitsRechamberSet(const playerState_t *ps, unsigned weapon, int rechamber);
unsigned CODOL_WeaponBitsModelGet(const playerState_t *ps, unsigned weapon);
void CODOL_WeaponBitsModelSet(const playerState_t *ps, unsigned weapon, unsigned model);
/* Whole-inventory word access, for the writers that walk all 22 words. */
uint32_t CODOL_WeaponBitsOwnedWord(const playerState_t *ps, unsigned word);
/* Drop everything this state owns. Used where the retained engine zeroed the
 * three bitsets and the model bytes as part of a larger memset. */
void CODOL_WeaponBitsInventoryClear(const playerState_t *ps);

/* Diagnostics: how many calls found no storage for their playerState, i.e. how
 * many times a site named the wrong register. Zero is the only correct value
 * and a test asserts it after a match. */
unsigned CODOL_WeaponBitsMisses(void);
void CODOL_WeaponBitsResetMisses(void);

#ifdef __cplusplus
}
#endif
#endif
