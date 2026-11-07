#ifndef CODOL_WEAPON_LOCK_H
#define CODOL_WEAPON_LOCK_H
#include <stdint.h>
#include "codol_playerstate.h"
#include "codol_playerstate_ext.h"
/* IW4 lock state, kept outside the retained IW3 playerState ABI but inside
 * the CoDOL playerState extension, because IW4 and C1 keep it in the
 * playerState itself: PlayerCmd_WeaponLockFinalize (iw4x 0x5dd500) writes
 * ps+0x404 flags, ps+0x408 entity and ps+0x40c position, and C1 transmits
 * those three through the measured netfields 0x48c/0x490/0x494..0x49c. The
 * state therefore travels with every playerState copy - snapshot frame,
 * archive slot, archive stream and spectator bundle - instead of being a
 * per-client global that a delayed spectator would read as "now".
 * Entity target and position remain stored when switching target modes.
 * Missile offset is server-side and is not the position target: IW4 keeps it
 * at client+0x3654 and only the missile launch (0x4a4f52) reads it. */
typedef codol_ps_lock_t codol_weapon_lock_t;
void CODOL_ResetWeaponLock(codol_weapon_lock_t *);
/* position != NULL selects a position target, otherwise entity (0..2046).
 * finalize adds locked and fire-mode flags; start clears those flags.
 * Invalid arguments preserve all state. */
int CODOL_SetWeaponLock(codol_weapon_lock_t *,unsigned entity,const float *position,
    int finalize,const float *missile_offset,int direct_fire);
void CODOL_FreeWeaponLock(codol_weapon_lock_t *);
int CODOL_SetWeaponLockWarning(codol_weapon_lock_t *,unsigned mask,int enabled);
/* C1 fields 48c/490/494/498/49c; missile offset is deliberately server-only. */
int CODOL_OverlayWeaponLock(codol_player_fields_t *,const codol_weapon_lock_t *);
/* The lock of one playerState storage. The read accessor never returns NULL:
 * an untracked state reads as unlocked. The mutable accessor returns NULL for
 * an untracked state and records the reset lock on first use. */
codol_weapon_lock_t *CODOL_PlayerStateWeaponLock(const playerState_t *ps);
const codol_weapon_lock_t *CODOL_PlayerStateWeaponLockRead(const playerState_t *ps);
/* The live state of a connected client, for callers holding an index. */
codol_weapon_lock_t *CODOL_ClientWeaponLock(unsigned client);
/* Live half only, and only the lock: the recoil magnitude sharing the block
 * is another subsystem's, and captured snapshots and archived history keep
 * the lock they were taken with. The all-clients form is the map/game reset
 * and does clear every storage. */
void CODOL_ResetClientWeaponLock(unsigned client);
void CODOL_ResetClientWeaponLocks(void);
/* Source-visible position targets for retained missile guidance. */
extern unsigned char codol_missile_position_active[ENTITYNUM_WORLD];
/* Persistent target state, separate from a handle that may be dissociated. */
extern unsigned char codol_missile_lock_active[ENTITYNUM_WORLD];
void CODOL_SetMissileEntityTarget(unsigned entity,int locked);
extern float codol_missile_positions[ENTITYNUM_WORLD][3];
void CODOL_ResetMissilePosition(unsigned entity);
void CODOL_ResetMissilePositions(void);
#endif
