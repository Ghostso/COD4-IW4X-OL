#ifdef CODOL_SERVER
#include "g_shared.h"
#include "bg_public.h"
#include "codol_weapon_lock.h"
#include <string.h>
/* Called by G_FireRocket after its default flight-mode initialization and
 * before linking/notifying. The caller assigns the returned entity through
 * EntHandle::setEnt, preserving the engine's handle bookkeeping. */
gentity_t *CODOL_ApplyRocketWeaponLock(gentity_t *owner,gentity_t *missile)
{
    const codol_weapon_lock_t *lock;gentity_t *target;
    if(!missile || missile->s.number<0 || missile->s.number>=ENTITYNUM_WORLD)return NULL;
    /* G_FireRocket has initialized the native trajectory mode before this
     * call. Capture even when there is no player owner or weapon lock. */
    missile->s.lerp.u.missile.flightMode=missile->missile.flightMode;
    CODOL_ResetMissilePosition((unsigned)missile->s.number);
    /* Owner identity for the client's compass. T5 G_FireRocket
     * (OpenBLOPS g_missile.cpp:5474..5493) sets missile.team from the parent
     * client's sess.cs.team and packs team | owner<<2 into es.faction, which
     * CG_CompassUpdateGuidedMissileInfo splits back into the icon's team and
     * owner (cg_compassfriendlies_mp.cpp:302..303). C1 keeps the two halves as
     * separate entityState fields present in every eType table: +0xa4, two
     * bits, the head-icon team its own setter 0x50e70a writes as allies 2 /
     * axis 1 / none 0, and +0x9c, six bits, the client number. Nothing set
     * either for a rocket, so every missile reached C1 as team 0 / owner 0
     * and a predator missile was drawn with client 0's colours for everyone.
     * The retained entityState has the same two members (entity.h:280/282),
     * unused on missiles, so the captured state carries them to every
     * snapshot and archive; CODOL_OverlayEngineMissile publishes them. A
     * non-client parent keeps T5's default owner 0 / team 0. */
    missile->s.clientNum=0;
    missile->s.iHeadIconTeam=TEAM_FREE;
    if(owner && owner->client && owner->s.number>=0 && owner->s.number<MAX_CLIENTS) {
        missile->s.clientNum=owner->s.number;
        if(owner->client->sess.cs.team==TEAM_RED || owner->client->sess.cs.team==TEAM_BLUE)
            missile->s.iHeadIconTeam=owner->client->sess.cs.team;
    }
    /* What C1 actually reads for the compass owner is neither of the above.
     * A live trace of C1 1.1.1.13 (docs/CODOL_C1_VIRTUALIZED_20260928.md,
     * 2026-09-28) shows the compass update CG_Missile calls (.tvm0 0x832ca85)
     * load es+0x80, test it against 0x7ff, and store it as the list entry's
     * owner (0x16c75b0 entry+0x18), whose clientinfo team the drawer 0x436030
     * compares with the local team. C1's own rocket spawn writes that field at
     * 0x5310ce..0x5310d9: es+0x80 = parent->s.number when the weapon's
     * guidedMissileType (+0x8e0) is 2, the predator's guidance; other rockets
     * keep the spawn default. The retained entityState's otherEntityNum is
     * unused on missiles and is what the C1 +0x80 field carries for movers
     * too (codol_equipment_support.c), so it carries the owner to
     * CODOL_OverlayEngineMissile. */
    missile->s.otherEntityNum=0;
    if(owner && owner->s.number>=0 && owner->s.number<ENTITYNUM_WORLD) {
        const struct WeaponDef *def=BG_GetWeaponDef(missile->s.weapon);
        if(def && def->guidedMissileType==MISSILE_GUIDANCE_HELLFIRE)
            missile->s.otherEntityNum=owner->s.number;
    }
    if(!owner || !missile || !owner->client || owner->s.number<0 || owner->s.number>=32)return NULL;
    /* The launch reads the lock of the owner's own live playerState, the way
     * IW4 0x4a4f2b/0x4a4f52 reads ps+0x408/client+0x3654 of the shooter. */
    lock=CODOL_PlayerStateWeaponLockRead(&owner->client->ps);
    if(!(lock->flags&2))return NULL;
    if(lock->flags&0x40) {
        /* C1 5749bc..5749d7 copies the absolute target, not the missile offset. */
        memcpy(codol_missile_positions[missile->s.number],lock->position,sizeof(lock->position));
        codol_missile_position_active[missile->s.number]=1;
        codol_missile_lock_active[missile->s.number]=1;
        memset(missile->missile.targetOffset,0,sizeof(missile->missile.targetOffset));
        missile->missile.flightMode=(lock->flags&4) ? MISSILEFLIGHTMODE_DIRECT:MISSILEFLIGHTMODE_TOP;
        missile->s.lerp.u.missile.flightMode=missile->missile.flightMode;
        return NULL;
    }
    if(lock->entity>=ENTITYNUM_WORLD)return NULL;
    target=&g_entities[lock->entity];
    if(!target->r.inuse)return NULL;
    codol_missile_lock_active[missile->s.number]=1;
    memcpy(missile->missile.targetOffset,lock->missile_offset,sizeof(lock->missile_offset));
    missile->missile.flightMode=(lock->flags&4) ? MISSILEFLIGHTMODE_DIRECT:MISSILEFLIGHTMODE_TOP;
    missile->s.lerp.u.missile.flightMode=missile->missile.flightMode;
    return target;
}
#endif
