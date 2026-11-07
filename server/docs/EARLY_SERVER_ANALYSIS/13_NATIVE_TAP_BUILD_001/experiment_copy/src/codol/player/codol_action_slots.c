/* SPDX-License-Identifier: AGPL-3.0-or-later
 * C1 action-slot state. Native identity is captured with each playerState. */
#ifdef CODOL_SERVER
#include "codol_weapon_slots.h"
#include "codol_action_slots.h"
#include "codol_playerstate_ext.h"
#include "codol_usercmd.h"
#include "scr_vm_functions.h"
#include "bg.h"
#include "g_shared.h"
#include <string.h>
extern int BG_FindWeaponIndexForName(const char *name);

void CODOL_ResetClientActionSlotState(unsigned client)
{
    codol_ps_ext_t *ext;
    if(client>=MAX_CLIENTS || !level.clients)return;
    ext=CODOL_PlayerStateExt(&level.clients[client].ps);
    if(ext)memset(&ext->action_slots,0,sizeof(ext->action_slots));
}

void CODOL_Scr_SetActionSlot(scr_entref_t ref)
{
    gentity_t *ent;
    codol_ps_ext_t *ext;
    const char *kind;
    int slot,type,weapon=0,count=Scr_GetNumParam();
    if(ref.classnum || ref.entnum>=MAX_CLIENTS ||
       !(ent=&g_entities[ref.entnum])->client) {
        Scr_ObjectError("setactionslot: entity must be a player");return;
    }
    if(count<2 || count>3) {
        Scr_Error("setactionslot requires slot, type, and a weapon for type weapon");return;
    }
    if(Scr_GetType(0)!=VAR_INTEGER) {
        Scr_ParamError(0,"setactionslot: slot must be an integer");return;
    }
    slot=Scr_GetInt(0);
    if(slot<1 || slot>CODOL_ACTION_SLOT_COUNT) {
        Scr_ParamError(0,"setactionslot: slot must be between 1 and 5");return;
    }
    if(Scr_GetType(1)!=VAR_STRING) {
        Scr_ParamError(1,"setactionslot: type must be a string");return;
    }
    kind=Scr_GetString(1);
    if(!Q_stricmp(kind,"weapon"))type=1;
    else if(!Q_stricmp(kind,"altmode"))type=2;
    else if(!Q_stricmp(kind,"nightvision"))type=3;
    else if(!*kind)type=0;
    else {Scr_ParamError(1,"setactionslot: invalid action type");return;}
    if(type==1) {
        if(count!=3 || Scr_GetType(2)!=VAR_STRING) {
            Scr_ParamError(2,"setactionslot: weapon type requires a weapon name");return;
        }
        /* C1 51680a finds an already registered definition; setting an action
         * slot is not a weapon precache or inventory grant. */
        const char *name=Scr_GetString(2);
        weapon=BG_FindWeaponIndexForName(name);
        if(weapon<=0 || weapon>=(int)CODOL_WEAPON_SLOTS) {
            /* IW4 raises here, and on IW4 that is right: a script asking for an
             * unprecached weapon wrote the wrong name. On this server it is a
             * CAPACITY condition instead. The native weapon registry is finite
             * and shared with composed weapons, so a correctly named, really
             * precached weapon can still land at or past index 128 and have no
             * publishable index - that is exactly how rcbomb_mp reached
             * "engine 128 wire -1 owned 0" and then ended the match here. A
             * reward whose weapon did not fit must stay unusable, not take
             * everyone's game down. Report once per weapon, leave the slot as
             * it was, and let the caller decide. */
            static unsigned reported[16]; static unsigned reported_count;
            unsigned hash=0,i; int seen=0;
            for(i=0;name[i];++i) hash=hash*31u+(unsigned char)name[i];
            for(i=0;i<reported_count;++i) if(reported[i]==hash){seen=1;break;}
            if(!seen && reported_count<16) {
                reported[reported_count++]=hash;
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "setactionslot: weapon '%s' has no publishable index"
                    " (native %d); action slot %d left unchanged."
                    " The native weapon registry is out of publishable room.\n",
                    name,weapon,slot);
            }
            return;
        }
    }
    ext=CODOL_PlayerStateExt(&ent->client->ps);
    if(!ext){Scr_Error("setactionslot: player state is unavailable");return;}
    --slot;
    ext->action_slots.type[slot]=(uint8_t)type;
    /* C1 only changes the parameter for weapon actions. Inactive slots retain
     * the last parameter; consumers gate it by type. */
    if(type==1)ext->action_slots.weapon[slot]=(uint16_t)weapon;
}

int CODOL_OverlayActionSlots(codol_player_fields_t *wire,const playerState_t *ps)
{
    const codol_ps_ext_t *ext;
    codol_player_fields_t next;
    unsigned slot,i;
    if(!wire || !ps || !(ext=CODOL_PlayerStateExtConst(ps)))return 0;
    next=*wire;
    for(slot=0;slot<CODOL_ACTION_SLOT_COUNT;++slot) {
        int mapped=ext->action_slots.weapon[slot] ?
            CODOL_WeaponToWire(ext->action_slots.weapon[slot]):0;
        unsigned found=0;
        if(ext->action_slots.type[slot]>3 || mapped<0 || mapped>2047)return 0;
        for(i=0;i<CODOL_PLAYER_FIELDS;++i) {
            const codol_player_field_t *field=CODOL_PlayerField(i);
            if(!field)return 0;
            if(field->offset==0x544+4*slot) {
                next.field[i]=ext->action_slots.type[slot];found|=1;
            }
            if(field->offset==0x558+4*slot) {
                next.field[i]=(unsigned)mapped;found|=2;
            }
        }
        if(found!=3)return 0;
    }
    *wire=next;return 1;
}
#endif
