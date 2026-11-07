#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include <stdint.h>
#include <math.h>
#include <string.h>

/* C1 53c070 sets this entity-only flag. The -98 wire codec has 30 bits,
 * so this marker must remain server-side. */
#define CODOL_ENTITY_STATIC UINT32_C(0x80000000)
static gentity_t *script_entity(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return NULL;
    }
    return &g_entities[ref.entnum];
}
void CODOL_Scr_WillNeverChange(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity) entity->s.lerp.eFlags=(int)((uint32_t)entity->s.lerp.eFlags|CODOL_ENTITY_STATIC);
}
static int mutable_entity(scr_entref_t ref,const char *message)
{
    gentity_t *entity=script_entity(ref); if(!entity) return 0;
    if((uint32_t)entity->s.lerp.eFlags&CODOL_ENTITY_STATIC) { Scr_Error(message); return 0; }
    return 1;
}
void CODOL_Scr_Delete(scr_entref_t ref)
{
    if(mutable_entity(ref,"Cannot delete a 'willNeverChange' entity")) ScrCmd_Delete(ref);
}
void CODOL_Scr_Show(scr_entref_t ref)
{
    if(mutable_entity(ref,"Cannot change a 'willNeverChange' entity")) ScrCmd_Show(ref);
}
void CODOL_Scr_Hide(scr_entref_t ref)
{
    if(mutable_entity(ref,"Cannot change a 'willNeverChange' entity")) ScrCmd_Hide(ref);
}
void CODOL_Scr_ShowToPlayer(scr_entref_t ref)
{
    if(mutable_entity(ref,"Cannot change a 'willNeverChange' entity")) ScrCmd_ShowToPlayer(ref);
}
static void add_angle(scr_entref_t ref,unsigned axis)
{
    gentity_t *entity=script_entity(ref); float angles[3],delta;
    if(!entity) return;
    if(!mutable_entity(ref,"Cannot change a 'willNeverChange' entity")) return;
    delta=Scr_GetFloat(0);
    memcpy(angles,entity->r.currentAngles,sizeof(angles));
    angles[axis]+=delta;
    if(!isfinite(delta) || !isfinite(angles[0]) || !isfinite(angles[1]) || !isfinite(angles[2])) {
        Scr_Error("AddAngle requires finite angles"); return;
    }
    /* The source reference adds one Euler component. Use the same setter as
     * the retained script 'angles' field, including trajectory reset. */
    G_SetAngle(entity,angles);
}
void CODOL_Scr_AddPitch(scr_entref_t ref) { add_angle(ref,0); }
void CODOL_Scr_AddYaw(scr_entref_t ref) { add_angle(ref,1); }
void CODOL_Scr_AddRoll(scr_entref_t ref) { add_angle(ref,2); }
/* IW4 5f5a40 -> 470d30: rotate midpoint + half-size * coefficients,
 * then translate by entity origin. Coefficients are not clamped. */
void CODOL_Scr_GetPointInBounds(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);float coefficient[3],local[3],axis[3][3],point[3];
    unsigned i;
    if(!entity)return;
    /* IW45f5a6f..5f5a8c reads all three floats with no finite/range guard. */
    for(i=0;i<3;++i) coefficient[i]=Scr_GetFloat(i);
    for(i=0;i<3;++i) {
        local[i]=(entity->r.mins[i]+entity->r.maxs[i])*0.5f+
                 (entity->r.maxs[i]-entity->r.mins[i])*0.5f*coefficient[i];
    }
    AnglesToAxis(entity->r.currentAngles,axis);
    for(i=0;i<3;++i) {
        /* IW4 helper470d30 stores the rotated vector before adding origin
         * at470e08..470e28. Do not round the origin into each partial sum. */
        volatile float rotated=(long double)local[0]*axis[0][i]+
            (long double)local[1]*axis[1][i]+(long double)local[2]*axis[2][i];
        point[i]=(long double)rotated+entity->r.currentOrigin[i];
    }
    Scr_AddVector(point);
}
/* IW4 5da240: player-only query of current view height. */
void CODOL_Scr_GetPlayerViewHeight(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("GetPlayerViewHeight requires a player");return;}
    Scr_AddFloat(entity->client->ps.viewHeightCurrent);
}
/* IW4 5edf30 queries the missile's owner handle, not its guidance target. */
void CODOL_Scr_GetMissileOwner(void)
{
    gentity_t *missile=Scr_GetEntity(0);unsigned number;
    if(!missile)return;
    if(missile->s.eType!=ET_MISSILE){Scr_Error("GetMissileOwner requires a missile");return;}
    number=missile->r.ownerNum.number;
    if(!number){Scr_AddUndefined();return;}
    if(number>MAX_GENTITIES){Scr_Error("GetMissileOwner has an invalid owner handle");return;}
    Scr_AddEntity(&g_entities[number-1]);
}
/* T5 6469d0..646ad0 expose the current transform and stored local/world
 * collision bounds. Absolute bounds are the linked broadphase bounds,
 * not a fresh origin + mins/maxs calculation. */
void CODOL_Scr_GetAngles(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddVector(entity->r.currentAngles);
}
void CODOL_Scr_GetMins(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddVector(entity->r.mins);
}
void CODOL_Scr_GetMaxs(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddVector(entity->r.maxs);
}
void CODOL_Scr_GetAbsMins(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddVector(entity->r.absmin);
}
void CODOL_Scr_GetAbsMaxs(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddVector(entity->r.absmax);
}
/* T5 655a60 returns the receiver reference number directly. */
void CODOL_Scr_GetEntNum(scr_entref_t ref) { Scr_AddInt(ref.entnum); }
/* IW4 5ef2f0 -> 49c060 checks the actual tag-link parent. */
void CODOL_Scr_IsLinked(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(entity)Scr_AddBool(entity->tagInfo && entity->tagInfo->parent);
}
/* T5 645f40 -> 691d30 compares the immediate parent, not ancestors. */
void CODOL_Scr_IsLinkedTo(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref),*parent;
    if(!entity)return;
    parent=Scr_GetEntity(0);
    if(parent)Scr_AddBool(entity->tagInfo && entity->tagInfo->parent==parent);
}
/* IW4 5da2b0 reads the current user command's signed forward/right bytes
 * and divides each by 127. Diagonal input is not length-normalized. */
void CODOL_Scr_GetNormalizedMovement(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    float movement[3];
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("GetNormalizedMovement requires a player");return;}
    movement[0]=(signed char)entity->client->sess.cmd.forwardmove/127.0f;
    movement[1]=(signed char)entity->client->sess.cmd.rightmove/127.0f;
    movement[2]=0.0f;
    Scr_AddVector(movement);
}
/* IW4 5dec20 requires zero arguments and an actual spectator session;
 * spectatorClient alone may retain a previous follow target. */
void CODOL_Scr_GetSpectatingPlayer(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    int target;
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("GetSpectatingPlayer requires a player");return;}
    if(Scr_GetNumParam()){Scr_Error("Usage: self GetSpectatingPlayer()");return;}
    target=entity->client->spectatorClient;
    if(entity->client->sess.sessionState!=SESS_STATE_SPECTATOR || target<0) {
        Scr_AddUndefined(); return;
    }
    if(target>=MAX_GENTITIES){Scr_Error("Invalid spectator target");return;}
    Scr_AddEntity(&g_entities[target]);
}
/* T5 645070 reads the session multiplier written by 644fd0, not the
 * effective player-state multiplier after gameplay modifiers. The retained
 * ScrCmd_SetMoveSpeedScale writes sess.moveSpeedScaleMultiplier (+2ffc). */
void CODOL_Scr_GetMoveSpeedScale(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("GetMoveSpeedScale requires a player");return;}
    Scr_AddFloat(entity->client->sess.moveSpeedScaleMultiplier);
}

/* T5 6095b0/609750 test the occupied-vehicle state and, for the latter,
 * resolve the player's owner handle. Native G_VehEntHandler_Use sets
 * pm_flags 0x100000 and r.ownerNum; G_VehUnlinkPlayer clears both. */
void CODOL_Scr_IsInVehicle(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("IsInVehicle requires a player");return;}
    Scr_AddBool((entity->client->ps.pm_flags&0x100000)!=0);
}

void CODOL_Scr_GetVehicleOccupied(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    unsigned number;
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("GetVehicleOccupied requires a player");return;}
    if(!(entity->client->ps.pm_flags&0x100000)){Scr_AddUndefined();return;}
    number=entity->r.ownerNum.number;
    if(!number){Scr_Error("Player is in a vehicle but has no vehicle owner handle");return;}
    if(number>MAX_GENTITIES){Scr_Error("Invalid occupied vehicle handle");return;}
    Scr_AddEntity(&g_entities[number-1]);
}
/* IW4 5da750 tests its turret stance bits 0xc00. Retained turret_use
 * sets the native player turret eFlags pair. */
void CODOL_Scr_IsUsingTurret(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->client){Scr_ObjectError("IsUsingTurret requires a player");return;}
    Scr_AddBool((entity->client->ps.eFlags&PLAYER_EFLAG_TURRET_MASK)!=0);
}
/* IW4 5ecef0 checks turret state, then active, then the owner EntHandle.
 * An active turret with an empty handle returns ENTITYNUM_NONE, not world.
 * Native turret_use maintains both active and r.ownerNum directly. */
void CODOL_Scr_GetTurretOwner(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    unsigned number;
    if(!entity)return;
    if(!entity->pTurretInfo){Scr_Error("GetTurretOwner requires a turret");return;}
    if(!entity->active){Scr_AddUndefined();return;}
    number=entity->r.ownerNum.number;
    if(number>MAX_GENTITIES){Scr_Error("Invalid turret owner handle");return;}
    Scr_AddEntity(&g_entities[number ? number-1:ENTITYNUM_NONE]);
}
/* IW4 0x5ed300 stores the supplied float directly in turret playerSpread.
 * Retained turret_think_client reads that field at +38 into Bullet_Fire's
 * spread argument. This changes the active turret, not its shared WeaponDef. */
void CODOL_Scr_SetPlayerSpread(scr_entref_t ref)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->pTurretInfo) {
        Scr_Error("SetPlayerSpread requires a turret");return;
    }
    entity->pTurretInfo->playerSpread=Scr_GetFloat(0);
}
static void set_turret_fire_disabled(scr_entref_t ref,int disabled)
{
    gentity_t *entity=script_entity(ref);
    if(!entity)return;
    if(!entity->pTurretInfo) {
        Scr_Error("Turret fire control requires a turret");return;
    }
    if(disabled)entity->pTurretInfo->flags|=CODOL_TURRET_FIRE_DISABLED;
    else entity->pTurretInfo->flags&=~CODOL_TURRET_FIRE_DISABLED;
}
/* IW4 0x5ed9d0/0x5eda40 toggle flag 2. Native flag 2 is stance state,
 * so use a dedicated flag consumed by turret_think_client's firing gate. */
void CODOL_Scr_TurretFireDisable(scr_entref_t ref)
{ set_turret_fire_disabled(ref,1); }
void CODOL_Scr_TurretFireEnable(scr_entref_t ref)
{ set_turret_fire_disabled(ref,0); }
/* IW4 0x5ed8f0 -> 0x4be660: exactly one argument, stored without
 * normalization or clamping. Native turret_think reads dropPitch at +1c
 * as its idle pitch target on each frame. */
void CODOL_Scr_SetDefaultDropPitch(scr_entref_t ref)
{
    gentity_t *entity;
    if(Scr_GetNumParam()!=1) {
        Scr_Error("SetDefaultDropPitch requires one parameter");return;
    }
    entity=script_entity(ref);
    if(!entity)return;
    if(!entity->pTurretInfo) {
        Scr_Error("SetDefaultDropPitch requires a turret");return;
    }
    entity->pTurretInfo->dropPitch=Scr_GetFloat(0);
}
void CODOL_RecomputeTurretDropPitchNative(gentity_t *,int,int);
void CODOL_Scr_RestoreDefaultDropPitch(scr_entref_t ref)
{
    gentity_t *entity;
    if(Scr_GetNumParam()!=0) {
        Scr_Error("RestoreDefaultDropPitch requires no parameters");return;
    }
    entity=script_entity(ref);
    if(!entity)return;
    if(!entity->pTurretInfo) {
        Scr_Error("RestoreDefaultDropPitch requires a turret");return;
    }
    /* C1 0x57be01 uses the same mask as IW4; mounted brush contents are
     * preserved by the native collision loader. Include current gun pitch
     * on a hit, leaving the old value intact if tags/geometry are absent. */
    CODOL_RecomputeTurretDropPitchNative(entity,0x800811,1);
}
/* IW4 5f2f40's flags at 79a15c use the names initialized at 472950..
 * 472a43. IW4 inserts EXPLOSIVE_BULLET and omits IW3's TELEFRAG entry;
 * importing those table indices would incorrectly classify melee. */
void CODOL_Scr_IsExplosiveDamageMod(void)
{
    static const char *const explosive[]={
        "MOD_EXPLOSIVE_BULLET", "MOD_GRENADE", "MOD_GRENADE_SPLASH",
        "MOD_PROJECTILE", "MOD_PROJECTILE_SPLASH", "MOD_EXPLOSIVE"
    };
    const char *name=Scr_GetString(0);
    unsigned i;
    for(i=0;i<sizeof(explosive)/sizeof(explosive[0]);++i)
        if(!strcmp(name,explosive[i])){Scr_AddBool(1);return;}
    Scr_AddBool(0);
}
#endif
