/* Missing MP-startup player builtins. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * playerhide: the reachable MP closure calls it from
 * maps/mp/gametypes/_playerlogic.gsc:920 (intermission spawn, after
 * self spawn(...) and playerLinkTo) and maps/mp/gametypes/_damage.gsc:685
 * (faux death, after victim.body = victim clonePlayer(...)). Both scripts are
 * compiled by every MP gametype, so the unresolved name is a compile blocker.
 *
 * Measured reference behaviour, C1 0x54de50:
 *   ent = script entity (0x534a10)
 *   if (!ent->client)            Scr_Error("Must be called on a player.")
 *   ent->client->ps.flags |= 0x10        (C1 playerState +0xec, wire bit 0x10)
 *   ent->r.contents = 0                  (C1 entityShared +0x130)
 * IW4 0x5f6de0 is the same function in its own layout: client +0x158,
 * ps.eFlags +0xb0 bit 0x20, contents +0x11c. Neither build tests the
 * willNeverChange marker that C1 hide/show check at 0x54d9b8/0x54da26,
 * neither enforces an argument count, neither relinks the entity, and neither
 * touches the clientMask words that C1 hide/show write (+0x10c/+0x110).
 *
 * Native producers/consumers in this tree:
 *   - playerState eFlags is +0xb0 here as in IW4. Retained
 *     BG_PlayerStateToEntityState (src/asmsource/_bg_misc.asm:2163) copies the
 *     whole word into entityState eFlags (+0x8) every frame, adding 0x20000
 *     for pm_type > 6 and 0x40000 for ADS, so the marker reaches the player's
 *     entity state without this method writing it.
 *   - This fork stores C1 bit 0x10 directly in the authoritative playerState.
 *     Generic retained entity hiding remains a separate entityState concern.
 *   - r.contents is read live: G_SetClientContents
 *     (src/asmsource/_g_active_mp.asm:2462) stores the player's contents and
 *     returns without relinking, and its only caller is ClientSpawn
 *     (src/g_client_mp.cpp:85). Nothing recomputes player contents per frame,
 *     so the cleared contents stays cleared, exactly as in the reference.
 *   - Lifecycle: ClientSpawn keeps only `ps.eFlags & 0x100002` across a spawn
 *     (src/g_client_mp.cpp, iFlags) and calls G_SetClientContents, so a
 *     respawn clears the hidden marker and restores collision contents. No
 *     extra teardown is needed for the faux-death and intermission call sites.
 *   - The direct C1 snapshot path publishes the marker unchanged.
 */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_script_startup_missing.h"
#include "codol_script_startup_extra.h"
#include <math.h>

int __cdecl G_DObjGetWorldTagPos(gentity_t *, unsigned int, float *);

/* C1 resolves the receiver with the shared script-entity helper before the
 * client check, so a non-entity reference raises an object error and only a
 * real entity without a client reaches the player message. */
static gentity_t *script_player(scr_entref_t ref)
{
    gentity_t *entity;
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return NULL;
    }
    entity=&g_entities[ref.entnum];
    if(!entity->client) {
        /* C1 0x54de78 raises this exact string (0xc58f78); IW4 0x6fa28c is the
         * same text. It is a script error, not an object error: the same
         * emitter C1 uses for the willNeverChange messages. */
        Scr_Error("Must be called on a player."); return NULL;
    }
    return entity;
}

void CODOL_Scr_PlayerHide(scr_entref_t entref)
{
    gentity_t *entity=script_player(entref);
    if(!entity) return;
    /* Both reference builds set the flag first, then clear contents. No
     * argument count is enforced and no value is returned. */
    entity->client->ps.eFlags|=CODOL_PS_EF_HIDDEN;
    entity->r.contents=0;
}

int CODOL_PlayerStateHidden(const struct playerState_s *ps)
{
    return ps && (ps->eFlags&CODOL_PS_EF_HIDDEN)!=0;
}

/* self WorldPointInReticle_Circle( <point>, <fov degrees>, <radius> )
 *
 * Decoded from IW4 0x005f5910 (method table 0x0073d75c) and its projection
 * helper 0x00502dc0, not from the alpha0022 Python, which models the two
 * floats as horizontal/vertical half-angles and tests an angular ellipse.
 * The measured contract is different:
 *
 *   entref.classnum != 0                -> object error (IW4 0x72c7f0)
 *   ent->client == NULL                 -> object error
 *                                          va("entity %i is not a player")
 *   arg0 vector (Scr_GetVector), arg1 and arg2 floats, no argument count check
 *   origin = view origin, axis = angle vectors of the playerState view angles
 *   0x00409f00(delta, axis, out): out[i] = dot(delta, axis[i])
 *   forward = out[0]; the helper returns false unless forward > 0 strictly
 *   tangent = tan(arg1 * 0.01745329238474369 * 0.5)   (arg1 is a full FOV)
 *   x = -320.0 * (out[1] / forward) / tangent
 *   y = -240.0 * (out[2] / forward) / (0.75 * tangent)
 *   result = x*x + y*y < arg2*arg2                    (strict; equality is 0)
 *
 * So the projection is into 640x480 virtual screen pixels around the screen
 * centre (constants -320.0 at IW4 0x72d790, -240.0 at 0x714f20, the 0.75
 * aspect at 0x6e2a80, 0.5 at 0x70fe50, deg2rad at 0x6e6360, the 0.0 the
 * caller compares the helper's boolean against at 0x78644c), and arg2 is a
 * radius in those pixels. The javelin/stinger calls `( targetPos, 65, 40 )`
 * are therefore a 65 degree FOV and a 40 pixel circle. The signs of the two
 * scale constants and whether the second axis row is left or right cannot
 * change the result because both components are squared.
 *
 * Native mapping: the retained G_GetPlayerViewOrigin (declared in g_shared.h,
 * implemented in src/asmsource/_g_client_mp.asm:1027) is the counterpart of
 * IW4 0x434cc0, including its mounted-view tag lookup, and AnglesToAxis is
 * the counterpart of the angle-vector helper 0x4e2620.
 *
 * IW4 wrapper4b6d00 selects tag_player on the view-link parent when link
 * flags+14 contain4. PlayerLinkWeaponViewToDelta sets that bit at5ef53c and
 * stores the parent entity number+18c at5ef574. The native equivalent is
 * CODOL_PLAYERLINK_WEAPONVIEW/linkEntNum, already maintained by link methods.
 */
static int reticle_origin(gentity_t *entity, float *origin)
{
    const codolPlayerLink_t *link=CODOL_PlayerLinkState(entity->s.number);
    if(link && link->mode==CODOL_PLAYERLINK_WEAPONVIEW) {
        int parent=link->linkEntNum;
        if(parent<0 || parent>=ENTITYNUM_NONE || !g_entities[parent].r.inuse ||
           !G_DObjGetWorldTagPos(&g_entities[parent],scr_const.tag_player,origin)) {
            Com_Error(ERR_DROP,"G_GetPlayerViewOrigin(): Couldn't find \"tag_player\" on player's view-link parent.");
            return 0;
        }
    } else {
        G_GetPlayerViewOrigin(&entity->client->ps,origin);
    }
    return 1;
}

void CODOL_Scr_WorldPointInReticleCircle(scr_entref_t entref)
{
    gentity_t *entity; playerState_t *ps;
    float point[3],origin[3],axis[3][3],delta[3];
    float fov,radius,x,y;
    volatile float forward,side,up,radians,tangent,vertical_tangent,ratio,distance;
    unsigned i;
    if(entref.classnum || entref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return;
    }
    entity=&g_entities[entref.entnum];
    if(!entity->client) {
        Scr_ObjectError(va("entity %i is not a player",entref.entnum)); return;
    }
    Scr_GetVector(0,point);
    fov=Scr_GetFloat(1);
    radius=Scr_GetFloat(2);
    ps=&entity->client->ps;
    if(!reticle_origin(entity,origin)) return;
    AnglesToAxis(ps->viewangles,axis);
    for(i=0;i<3;++i) delta[i]=point[i]-origin[i];
    forward=(long double)delta[0]*axis[0][0]+(long double)delta[1]*axis[0][1]+(long double)delta[2]*axis[0][2];
    if(!(forward>0.0f)) { Scr_AddBool(0); return; }
    side=(long double)delta[0]*axis[1][0]+(long double)delta[1]*axis[1][1]+(long double)delta[2]*axis[1][2];
    up=(long double)delta[0]*axis[2][0]+(long double)delta[1]*axis[2][1]+(long double)delta[2]*axis[2][2];
    /* Preserve the measured float stores in502e20/2d/4a/6c/82 and5f5a00.
     * No extra FOV/radius restrictions: reference arithmetic decides the bool. */
    radians=(long double)fov*0.01745329238474369*0.5;
    tangent=(float)tan((double)radians);
    ratio=(long double)side/forward;
    x=(float)(-320.0L*ratio/tangent);
    ratio=(long double)up/forward;
    vertical_tangent=(long double)tangent*0.75;
    y=(float)(-240.0L*ratio/vertical_tangent);
    distance=(long double)x*x+(long double)y*y;
    Scr_AddBool((long double)distance<(long double)radius*radius);
}

#endif
