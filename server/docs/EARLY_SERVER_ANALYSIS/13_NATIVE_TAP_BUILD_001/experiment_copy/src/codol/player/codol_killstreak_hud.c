/* SPDX-License-Identifier: AGPL-3.0-or-later
 * C1 script-owned killstreak progress and five reward previews. */
#ifdef CODOL_SERVER
#include "codol_killstreak_hud.h"
#include "codol_playerstate_ext.h"
#include "scr_vm_functions.h"
#include "g_shared.h"
#include <string.h>

/* C1 setters: count 516fb0, IDs 517110, targets 5172f0.
 * Getter counterparts: 517070, 517230, 5173d0. */
static codol_killstreak_hud_t *state(scr_entref_t ref,int count)
{
    codol_ps_ext_t *ext;
    int i;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client) {
        Scr_ObjectError("killstreak HUD method requires a player");return NULL;
    }
    if(Scr_GetNumParam()!=count) {
        Scr_Error("killstreak HUD method: incorrect argument count");return NULL;
    }
    for(i=0;i<count;++i)if(Scr_GetType(i)!=VAR_INTEGER) {
        Scr_ParamError(i,"killstreak HUD arguments must be integers");return NULL;
    }
    ext=CODOL_PlayerStateExt(&g_entities[ref.entnum].client->ps);
    if(!ext){Scr_Error("killstreak HUD state unavailable");return NULL;}
    return &ext->killstreak_hud;
}
static int clamp(int value,int maximum)
{return value<0?0:value>maximum?maximum:value;}
void CODOL_Scr_SetKillstreak(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,1);
    if(s)s->count=(uint16_t)clamp(Scr_GetInt(0),256);
}
void CODOL_Scr_GetKillstreak(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,0);
    if(s)Scr_AddInt(s->count);
}
void CODOL_Scr_SetKillstreakID(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,2);
    int id,slot;
    if(!s)return;
    id=Scr_GetInt(0);slot=clamp(Scr_GetInt(1),4);
    if(id>128){Scr_Error("SetKillstreakID exceeds maximum of 128");return;}
    s->id[slot]=(uint8_t)clamp(id,128);
}
void CODOL_Scr_GetKillstreakID(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,1);
    int slot;
    if(!s)return;
    slot=Scr_GetInt(0);Scr_AddInt((unsigned)slot<5?s->id[slot]:0);
}
void CODOL_Scr_SetKillstreakTarget(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,2);
    if(s)s->target[clamp(Scr_GetInt(1),4)]=(uint8_t)clamp(Scr_GetInt(0),25);
}
void CODOL_Scr_GetKillstreakTarget(scr_entref_t ref)
{
    codol_killstreak_hud_t *s=state(ref,1);
    int slot;
    if(!s)return;
    slot=Scr_GetInt(0);Scr_AddInt((unsigned)slot<5?s->target[slot]:0);
}
void CODOL_ResetClientKillstreakHud(unsigned client)
{
    codol_ps_ext_t *ext;
    if(client>=MAX_CLIENTS || !level.clients)return;
    ext=CODOL_PlayerStateExt(&level.clients[client].ps);
    if(ext)memset(&ext->killstreak_hud,0,sizeof(ext->killstreak_hud));
}
int CODOL_OverlayKillstreakHud(codol_player_fields_t *wire,const playerState_t *ps)
{
    const codol_ps_ext_t *ext;
    const codol_killstreak_hud_t *s;
    codol_player_fields_t next;
    unsigned i,found=0,slot;
    if(!wire || !ps || !(ext=CODOL_PlayerStateExtConst(ps)))return 0;
    s=&ext->killstreak_hud;next=*wire;
    if(s->count>256)return 0;
    for(slot=0;slot<5;++slot)if(s->id[slot]>128 || s->target[slot]>25)return 0;
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) {
        const codol_player_field_t *f=CODOL_PlayerField(i);
        if(!f)return 0;
        /* C1 count setter retains 256; this field has only eight wire bits.
         * Preserve full script/archive state independently of wire width. */
        if(f->offset==0x64){next.field[i]=s->count&255u;++found;}
        if(f->offset>=0x68 && f->offset<=0x78 && !(f->offset&3)) {
            next.field[i]=s->id[(f->offset-0x68)/4];++found;
        }
        if(f->offset>=0x7c && f->offset<=0x8c && !(f->offset&3)) {
            next.field[i]=s->target[(f->offset-0x7c)/4];++found;
        }
    }
    if(found!=11)return 0;
    *wire=next;return 1;
}
#endif
