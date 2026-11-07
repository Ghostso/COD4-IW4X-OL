/* Native recovery of deployed equipment; class1 keeps C1 live throwback. */
#ifdef CODOL_SERVER
#include "codol_missile_pickup.h"
#include "codol_knife_pickup.h"
#include "codol_weapon_native.h"
#include "g_shared.h"
#include "bg_public.h"
#include "codol_weapon_bits.h"
#include "codol_weapon_slots.h"
#include <stdio.h>
#include "scr_vm.h"
extern void G_AddPredictableEvent(gentity_t *,int,int);
extern void G_AddEvent(gentity_t *,int,int);
extern int Add_Ammo(gentity_t *,unsigned int,unsigned char,int,int);
extern int BG_GetMaxPickupableAmmo(const playerState_t *,unsigned);
extern qboolean G_GetHintStringIndex(int *,const char *);

static int special_definition(const struct WeaponDef *def)
{
    unsigned source_class;
    if(!def || !CODOL_GetNativeWeaponClass(def,&source_class) || source_class==9)
        return 0;
    /* +be2 timedDetonation and +354 offhandClass are independently loaded
     * from the C1 header. Untimed C4/Betty/scrambler keep their device paths. */
    return def->timedDetonation && (def->offhandClass==2 ||
        def->offhandClass==3 || def->offhandClass==5);
}
static unsigned missile_weapon(const gentity_t *ent)
{
    unsigned weapon;
    if(!ent || !ent->r.inuse || ent->s.eType!=ET_MISSILE)return 0;
    weapon=CODOL_ItemIndexWeapon(ent->s.index);
    return weapon && weapon<(unsigned)BG_GetNumWeapons()?weapon:0;
}
int CODOL_IsInventoryMissile(const gentity_t *ent)
{
    unsigned weapon=missile_weapon(ent);
    return weapon && (CODOL_IsKnifeDefinition(BG_GetWeaponDef(weapon)) ||
        special_definition(BG_GetWeaponDef(weapon)));
}
int CODOL_InventoryMissileCanBeGrabbed(const playerState_t *ps,unsigned weapon)
{
    int knife=CODOL_KnifeCanBeGrabbed(ps,weapon);
    if(knife!=-1)return knife;
    if(!weapon || weapon>=(unsigned)BG_GetNumWeapons() ||
       !special_definition(BG_GetWeaponDef(weapon)))return -1;
    /* Exact current inventory identity, never grant a different class item
     * merely because it shares an ammo pool. */
    if(!ps || weapon>=CODOL_WEAPON_SLOTS ||
       !CODOL_WeaponBitsOwned(ps,weapon))return 0;
    return BG_GetMaxPickupableAmmo(ps,weapon)>0;
}
int CODOL_InventoryMissileUseAllowed(const gentity_t *player,const gentity_t *ent)
{
    unsigned weapon=missile_weapon(ent);
    if(!weapon || !special_definition(BG_GetWeaponDef(weapon)))return 1;
    return player && player->r.inuse && player->client && player->health>0 &&
        ent->r.ownerNum.number==(unsigned)player->s.number+1 &&
        ent->nextthink>level.time &&
        CODOL_InventoryMissileCanBeGrabbed(&player->client->ps,weapon)==1;
}
int CODOL_RecoverMissileAmmo(gentity_t *player,const struct WeaponDef *def,
    unsigned weapon,unsigned variant,gentity_t *missile)
{
    int knife=CODOL_IsKnifeDefinition(def);
    if(!knife && !special_definition(def))return -1;
    if(missile_weapon(missile)!=weapon || !player || !player->r.inuse ||
       !player->client || player->health<=0 ||
       !CODOL_InventoryMissileUseAllowed(player,missile))return 0;
    {
        int generation=missile->useCount;
        unsigned item_index=missile->s.index;
        if(knife) {
            if(CODOL_RecoverKnifeAmmo(player,def,weapon,variant)<=0)return 0;
        } else if(Add_Ammo(player,weapon,(unsigned char)variant,1,1)<=0)return 0;
        /* Cancel the fuse before script notification. Waiters may delete,
         * reuse, or convert this slot; only the same pickup missile may get
         * the death notification and final free below. */
        missile->nextthink=0;
        if(player->client->sess.predictItemPickup)
            G_AddPredictableEvent(player,10,(int)weapon);
        else if(knife)
            G_AddEvent(player,10,(int)weapon);
        Scr_AddUndefined();
        Scr_AddEntity(player);
        Scr_Notify(missile,scr_const.trigger,2);
        if(!missile->r.inuse || missile->useCount!=generation ||
           missile->s.eType!=ET_MISSILE || missile->s.index!=item_index)return 2;
        Scr_Notify(missile,scr_const.death,0);
        if(missile->r.inuse && missile->useCount==generation &&
           missile->s.eType==ET_MISSILE && missile->s.index==item_index)
            G_FreeEntity(missile);
        return 2; /* World lifecycle completed; Touch_Item must return now. */
    }
}
int CODOL_InventoryMissileHint(const gentity_t *ent)
{
    unsigned weapon=missile_weapon(ent);
    const struct WeaponDef *def;
    char text[1024];
    int index,n;
    if(!weapon || !special_definition(def=BG_GetWeaponDef(weapon)))return -1;
    if(!def->szDisplayName || !def->szDisplayName[0])return -2;
    /* Shipped localized_code_post_gfx_mp asset2564: localized pickup with
     * &&1 substitution. 0x14 separates localized message arguments. */
    n=snprintf(text,sizeof(text),"WEAPON_PICKUP_GENERIC%c%s",20,def->szDisplayName);
    if(n<0 || n>=(int)sizeof(text) || !G_GetHintStringIndex(&index,text))return -2;
    return index;
}
#endif
