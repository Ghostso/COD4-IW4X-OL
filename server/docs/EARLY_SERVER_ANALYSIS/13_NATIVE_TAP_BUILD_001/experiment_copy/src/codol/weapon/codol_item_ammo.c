/* Native dropped-weapon magazines. SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_weapon_state.h"
#include "g_shared.h"
#include "bg.h"
#include "xassets/weapondef.h"
#include "codol_usercmd.h"
#include "qcommon.h"
#include "codol_item_ammo.h"
#include "codol_weapon_slots.h"
#include <stddef.h>
#include <string.h>

_Static_assert(sizeof(gentity_t)==0x274,"retained entity stride");
_Static_assert(offsetof(gentity_t,codolItem.slots)==offsetof(gentity_t,item),"item prefix");

/* Script selection and offhand commands carry the same C1 weapon identity
 * as inventory snapshots, even before the first client-side weapon switch.
 *
 * Called from the retained G_SelectWeaponIndex and G_SetEquippedOffHand
 * (_g_weapon.asm:1144/1177), which both build a reliable server command out of
 * the returned index. This used to Com_Error(ERR_DROP) when a weapon had no
 * published C1 index, which ends the match for every player because one
 * weapon could not be named on the wire - the same shape of defect as the
 * AC-130 reload-metadata crash, and reachable by any killstreak-held or
 * composed weapon that is not in the published bank.
 *
 * Both call sites are straight-line assembly that always sends the command, so
 * the helper cannot suppress the send. Zero is the established "no weapon"
 * value in this mapping (CODOL_WeaponToWire returns 0 for native 0), so an
 * unpublishable weapon now reports itself once and selects none. The player
 * sees no weapon selected instead of the wrong weapon or a dropped server. */
static unsigned char wire_index_reported[128];
static unsigned char wire_index_reported_high;
void CODOL_ResetWeaponWireIndexReports(void)
{
    memset(wire_index_reported,0,sizeof(wire_index_reported));
    wire_index_reported_high=0;
}
int CODOL_RequireWeaponWireIndex(unsigned native)
{
    int wire=CODOL_WeaponToWire(native);
    if(wire>=0) return wire;
    /* Report once per native index. This runs on every weapon selection, so
     * reporting per call would flood; reporting per index keeps a second
     * unpublished weapon visible. Indices at or above the internal registry
     * size share one flag because they cannot be tabulated. */
    if(native<sizeof(wire_index_reported)) {
        if(!wire_index_reported[native]) {
            wire_index_reported[native]=1;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL selection weapon %u has no published C1 index;"
                " selecting none for this command\n",native);
        }
    } else if(!wire_index_reported_high) {
        wire_index_reported_high=1;
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL selection weapon %u is outside the internal weapon registry;"
            " selecting none for this command\n",native);
    }
    return 0;
}

void CODOL_Scr_ItemWeaponSetAmmo(scr_entref_t ref)
{
    gentity_t *ent;
    struct WeaponDef *def;
    int count=Scr_GetNumParam(),right,stock,left,slot=0,weapon;
    if(ref.classnum || ref.entnum>=MAX_GENTITIES || !g_entities[ref.entnum].r.inuse) {
        Scr_ObjectError("itemweaponsetammo requires an item entity");return;
    }
    ent=&g_entities[ref.entnum];
    if(ent->s.eType!=ET_ITEM) {Scr_Error("entity is not an item");return;}
    if(count<2 || count>4) {Scr_Error("itemweaponsetammo: clip, reserve [, left clip [, alternate slot]]");return;}
    /* IW4 5f25a3..5f2607: left clip defaults to right; the optional
     * alternate slot is argument FOUR, not the retained IW3 third. */
    right=Scr_GetInt(0);stock=Scr_GetInt(1);left=count>2?Scr_GetInt(2):right;
    if(right<0){Scr_ParamError(0,"ammo count must be nonnegative");return;}
    if(stock<0){Scr_ParamError(1,"ammo count must be nonnegative");return;}
    if(left<0){Scr_ParamError(2,"ammo count must be nonnegative");return;}
    if(count>3)slot=Scr_GetInt(3);
    if(slot<0 || slot>1){Scr_ParamError(3,"alternate slot must be 0 or 1");return;}
    weapon=(int)CODOL_ItemIndexWeapon(ent->item[slot].index);
    if(weapon<=0 || weapon>=BG_GetNumWeapons())return;
    def=BG_GetWeaponDef(weapon);
    /* IW4 5f2622..5f266d caps each magazine, leaving reserve unchanged. */
    ent->item[slot].ammoCount=stock;
    ent->item[slot].clipAmmoCount=right>def->iClipSize?def->iClipSize:right;
    if(CODOL_WeaponIsDualWield((unsigned)weapon)) {
        ent->codolItem.leftClip[slot]=left>def->iClipSize?def->iClipSize:left;
        ent->codolItem.leftKnown|=1u<<slot;
    }
}

/* Called by the retained pickup producer after ownership/right ammo transfer.
 * These bytes belong to the entity union and are cleared by G_FreeEntity. */
void CODOL_ItemPickupLeftAmmo(gentity_t *item,gentity_t *player,unsigned slot)
{
    unsigned weapon;
    if(!item || !player || !player->client || slot>1 ||
       !(item->codolItem.leftKnown&(1u<<slot)))return;
    weapon=CODOL_ItemIndexWeapon(item->item[slot].index);
    if(CODOL_WeaponIsDualWield(weapon))
        CODOL_WeaponStateSetLeftClip(&player->client->ps,weapon,item->codolItem.leftClip[slot]);
}
#endif
