#ifdef CODOL_SERVER
#include "codol_animation_tables.h"
#include "qcommon.h"
#include "codol_weapon_state.h"
#include "player.h"
#include "xassets/weapondef.h"
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
_Static_assert(sizeof(codol_anim_script_slot_t)==0x204,"native animation script slot ABI");
_Static_assert(offsetof(codol_anim_script_slot_t,items)==4,"native script item array ABI");
static void *script_owner;
_Alignas(16) unsigned char CODOL_AnimationRecords[CODOL_ANIM_RECORD_COUNT*0x60];
unsigned CODOL_AnimationCount;
void CODOL_BeginAnimationRecords(unsigned count)
{
    if(!count || count>CODOL_ANIM_RECORD_COUNT) {
        Com_Error(ERR_DROP,"Invalid CoDOL animation tree size: %u (maximum %u)",count,CODOL_ANIM_RECORD_COUNT);
        return;
    }
    memset(CODOL_AnimationRecords,0,sizeof(CODOL_AnimationRecords));
    CODOL_AnimationCount=count;
}
typedef struct { unsigned char *data; uint32_t count,capacity; } command_list_t;
static command_list_t command_lists[2048];
static codol_anim_script_slot_t extra[2][CODOL_ANIM_MOVE_COUNT-CODOL_ANIM_LEGACY_MOVE_COUNT];
static codol_anim_script_slot_t extra_events[CODOL_ANIM_EVENT_COUNT-CODOL_ANIM_LEGACY_EVENT_COUNT];
extern struct bgs_s *bgs;
static uint32_t conditions[64][9][2];
static uint16_t known_conditions[64];
/* Ten unchanged IW3 indices, then nine CoDOL names in measured order. */
static const unsigned char condition_kind[19]={0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1};

void CODOL_ResetAnimMoveScripts(void *owner)
{
    for(unsigned i=0;i<2048;++i) free(command_lists[i].data);
    memset(command_lists,0,sizeof(command_lists));
    memset(extra,0,sizeof(extra));
    memset(extra_events,0,sizeof(extra_events));
    memset(conditions,0,sizeof(conditions));
    memset(known_conditions,0,sizeof(known_conditions));
    script_owner=owner;
    if(!owner) {
        memset(CODOL_AnimationRecords,0,sizeof(CODOL_AnimationRecords));
        CODOL_AnimationCount=0;
    }
}
static command_list_t *command_list(void *item)
{
    uintptr_t base=(uintptr_t)script_owner+0x199b4, address=(uintptr_t)item;
    if(!script_owner || address<base || (address-base)%0x100 || (address-base)/0x100>=2048) {
        Com_Error(ERR_DROP,"Invalid native animation command item"); return NULL;
    }
    command_list_t *list=&command_lists[(address-base)/0x100];
    if(*(uint32_t *)((unsigned char *)item+0x7c)!=list->count) {
        Com_Error(ERR_DROP,"Native animation command count mismatch"); return NULL;
    }
    return list;
}
void *CODOL_AppendAnimCommand(void *item)
{
    command_list_t *list=command_list(item);
    if(!list) return NULL;
    if(list->count==list->capacity) {
        /* Keep native signed command counts and allocation multiplication valid. */
        if(list->capacity>INT_MAX/32) {
            Com_Error(ERR_DROP,"Native animation command allocation overflow"); return NULL;
        }
        uint32_t capacity=list->capacity ? list->capacity*2 : 8;
        unsigned char *data=realloc(list->data,(size_t)capacity*16);
        if(!data) { Com_Error(ERR_DROP,"Out of memory for native animation commands"); return NULL; }
        list->data=data; list->capacity=capacity;
    }
    void *out=list->data+(size_t)list->count*16;
    memset(out,0,16);
    ++list->count;
    *(uint32_t *)((unsigned char *)item+0x7c)=list->count;
    return out;
}
void *CODOL_AnimCommands(void *item)
{
    command_list_t *list=command_list(item);
    return list ? list->data : NULL;
}
codol_anim_script_slot_t *CODOL_AnimMoveScript(void *owner,int state,int movement,int canned)
{
    if(!owner || owner!=script_owner || state!=0 || movement<0 || movement>=CODOL_ANIM_MOVE_COUNT ||
        (canned!=0 && canned!=1)) return NULL;
    if(movement<CODOL_ANIM_LEGACY_MOVE_COUNT)
        return (codol_anim_script_slot_t *)((unsigned char *)owner+
            (canned ? 0x116b0 : 0xc004)+(size_t)movement*sizeof(codol_anim_script_slot_t));
    return &extra[canned][movement-CODOL_ANIM_LEGACY_MOVE_COUNT];
}
codol_anim_script_slot_t *CODOL_RequireAnimMoveScript(void *owner,int state,int movement,int canned)
{
    codol_anim_script_slot_t *slot=CODOL_AnimMoveScript(owner,state,movement,canned);
    if(!slot) Com_Error(ERR_DROP,"Invalid native CoDOL animation movement lookup: state %d, movement %d, canned %d",
        state,movement,canned);
    return slot;
}
codol_anim_script_slot_t *CODOL_AnimEventScript(void *owner,int event)
{
    if(!owner || owner!=script_owner || event<0 || event>=CODOL_ANIM_EVENT_COUNT) return NULL;
    if(event<CODOL_ANIM_LEGACY_EVENT_COUNT)
        return (codol_anim_script_slot_t *)((unsigned char *)owner+0x16f60+
            (size_t)event*sizeof(codol_anim_script_slot_t));
    return &extra_events[event-CODOL_ANIM_LEGACY_EVENT_COUNT];
}
codol_anim_script_slot_t *CODOL_RequireAnimEventScript(void *owner,int event)
{
    codol_anim_script_slot_t *slot=CODOL_AnimEventScript(owner,event);
    if(!slot) Com_Error(ERR_DROP,"Invalid native CoDOL animation event lookup: event %d",event);
    return slot;
}
static uint32_t *condition_value(int client,int condition,int write)
{
    if(!script_owner || script_owner!=(void *)bgs || client<0 || client>=64 ||
        condition<0 || condition>=CODOL_ANIM_CONDITION_COUNT) return NULL;
    if(condition<CODOL_ANIM_LEGACY_CONDITION_COUNT)
        return (uint32_t *)((unsigned char *)script_owner+0x99e5c+(size_t)client*0x4cc+condition*8);
    condition-=CODOL_ANIM_LEGACY_CONDITION_COUNT;
    if(write) known_conditions[client]|=(uint16_t)(1u<<condition);
    if(!(known_conditions[client]&(1u<<condition))) {
        /* A CoDOL condition no native producer has written yet reads as its
         * zero value (false / "none" / string index 0) rather than ending
         * the level: the animation scripts test akimbo, fastmantle,
         * riotshieldnext, divedirection and scripted on ordinary moves such
         * as mantling. Reported once per condition in developer mode. */
        static uint32_t zero[2]; static uint16_t reported;
        if(!(reported&(1u<<condition))) {
            reported|=(uint16_t)(1u<<condition);
            Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL animation condition %d read before any native producer set it; reading as zero\n",
                condition+CODOL_ANIM_LEGACY_CONDITION_COUNT);
        }
        zero[0]=zero[1]=0; return zero;
    }
    return conditions[client][condition];
}
void CODOL_SetAnimConditionValue(int client,int condition,uint64_t value)
{
    uint32_t *out=condition_value(client,condition,1);
    if(!out) { Com_Error(ERR_DROP,"Invalid native animation condition setter: client %d, condition %d",client,condition); return; }
    out[0]=(uint32_t)value; out[1]=(uint32_t)(value>>32);
}
void CODOL_SetAnimConditionBit(int client,int condition,int bit)
{
    if(bit<0 || bit>=64) { Com_Error(ERR_DROP,"Invalid animation condition bit: %d",bit); return; }
    CODOL_SetAnimConditionValue(client,condition,UINT64_C(1)<<bit);
}
/* Per-frame producer for the CoDOL conditions the playerState decides.
 * Called from ClientEndFrame beside the other native publishers.
 *   13 akimbo                 - the hand extension's dual-wield flag.
 *   16 playeranimtypeprimary  - held weapon's type, independently of an active
 *                               offhand selected by condition 0.
 * fastmantle, riotshieldnext, divedirection and scripted stay at their zero
 * value: no native producer measures them yet. */
void CODOL_UpdateAnimConditionsFromPlayerState(int client,const struct playerState_s *ps)
{
    const struct WeaponDef *held;
    if(!script_owner || script_owner!=(void *)bgs || client<0 || client>=64 || !ps) return;
    CODOL_SetAnimConditionValue(client,13,CODOL_WeaponStateIsDualWielding(ps) ? 1u : 0u);
    /* C1 405f78..405fc9 uses ps+33c (held weapon), while 405f0d..405f25
     * may select the offhand for condition0. Native ps.weapon owns that held
     * identity; no weapon-class coercion or loadout-slot assumption applies. */
    held=BG_GetWeaponDef(ps->weapon);
    if(!held || held->playerAnimType<0 || held->playerAnimType>=64) {
        Com_Error(ERR_DROP,"Invalid held weapon animation type for client %d",client);
        return;
    }
    CODOL_SetAnimConditionBit(client,16,held->playerAnimType);
}
int CODOL_AnimConditionMatches(const void *client_info,const codol_anim_condition_t *condition)
{
    uintptr_t base=(uintptr_t)script_owner+0x99a04, address=(uintptr_t)client_info;
    uint32_t *value; int client;
    if(!script_owner || !condition || address<base || (address-base)%0x4cc ||
        (address-base)/0x4cc>=64) {
        Com_Error(ERR_DROP,"Invalid animation condition client"); return 0;
    }
    client=(int)((address-base)/0x4cc);
    value=condition_value(client,condition->index,0);
    if(!value) {
        Com_Error(ERR_DROP,"Animation condition has no native state: client %d, condition %d",client,condition->index); return 0;
    }
    if(condition_kind[condition->index]) return value[0]==condition->low;
    return !!((value[0]&condition->low)|(value[1]&condition->high));
}
#endif
