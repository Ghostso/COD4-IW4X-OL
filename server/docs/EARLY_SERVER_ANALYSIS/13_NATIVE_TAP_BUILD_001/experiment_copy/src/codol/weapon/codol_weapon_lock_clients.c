/* Weapon-lock storage. The lock is not a per-client global: IW4 keeps its
 * flags, target entity and target position inside the playerState
 * (PlayerCmd_WeaponLockFinalize iw4x 0x5dd500 writes ps+0x404/0x408/0x40c) and
 * C1 transmits the same three through the measured playerState netfields
 * 0x48c/0x490/0x494..0x49c, so a spectator watching a delayed playerState must
 * see the lock that state carried, not the one the followed player has now.
 * The lock therefore lives in the CoDOL playerState extension, which travels
 * with every playerState copy, through the archive stream and into the
 * spectator bundle. See codol_playerstate_ext.h. */
#include "codol_weapon_lock.h"
#include "codol_playerstate_ext.h"
#include <stddef.h>

/* CoDOL carries 32 players; the C1 client wire and every lock field are sized
 * for that, and the retained per-client lock array used the same bound. */
#define CODOL_MAX_LOCK_CLIENTS 32u

codol_weapon_lock_t *CODOL_PlayerStateWeaponLock(const playerState_t *ps)
{
    return CODOL_PlayerStateLockMutable(ps);
}

const codol_weapon_lock_t *CODOL_PlayerStateWeaponLockRead(const playerState_t *ps)
{
    return CODOL_PlayerStateLockRead(ps);
}

/* The live state of a connected client, for callers that hold a client index
 * rather than a playerState. This is the *live* slot only - the same block the
 * resolver returns for level.clients[client].ps - and a snapshot or archived
 * state is reached through its own playerState instead. The bound is CoDOL's
 * player limit, which is what the C1 wire and the lock fields carry. */
codol_weapon_lock_t *CODOL_ClientWeaponLock(unsigned client)
{
    if (client >= CODOL_MAX_LOCK_CLIENTS) return NULL;
    return CODOL_PlayerStateExtClientLock(client);
}

void CODOL_ResetClientWeaponLock(unsigned client)
{
    /* Live half only, and only the lock: the recoil magnitude in the same
     * block belongs to another subsystem, and captured snapshots and archived
     * history keep the lock they were taken with. */
    CODOL_PlayerStateExtClearClientLock(client);
}

void CODOL_ResetClientWeaponLocks(void)
{
    /* The map/game reset discards every state, live, captured and archived. */
    CODOL_PlayerStateExtClearAll();
}
