#ifdef CODOL_SERVER
#include "codol_knife_pickup.h"
#include "codol_weapon_native.h"
#include "entity.h"
#include "bg_public.h"
#include "codol_weapon_bits.h"
#include "codol_weapon_slots.h"

extern int Add_Ammo(gentity_t *,unsigned int,unsigned char,int,int);
extern unsigned char BG_PlayerHasCompatibleWeapon(const playerState_t *,unsigned);
extern int BG_GetMaxPickupableAmmo(const playerState_t *,unsigned);

int CODOL_IsKnifeDefinition(const struct WeaponDef *definition)
{
    unsigned source_class;
    return CODOL_GetNativeWeaponClass(definition,&source_class) && source_class==9;
}

int CODOL_IsKnifeEntity(const gentity_t *entity)
{
    unsigned weapon;
    if(!entity || !entity->r.inuse || entity->s.eType!=ET_MISSILE)return 0;
    /* Same captured packed item identity consumed by Touch_Item. */
    weapon=CODOL_ItemIndexWeapon(entity->s.index);
    return weapon!=0 && weapon<(unsigned)BG_GetNumWeapons() &&
        CODOL_IsKnifeDefinition(BG_GetWeaponDef((int)weapon));
}

int CODOL_RecoverKnifeAmmo(gentity_t *player,const struct WeaponDef *definition,
    unsigned weapon,unsigned variant)
{
    if(!CODOL_IsKnifeDefinition(definition))return -1;
    if(!player || !player->r.inuse || !player->client || player->health<=0)return 0;
    /* C1 528292..5282a5: class9 gets AddAmmo(weapon,1,fillClip=1).
     * Native Add_Ammo checks ownership/compatible inventory and clips both
     * stock and clip to their capacity. Confirm actual transfer before removal
     * even if the upstream item eligibility gate was reached by another path. */
    return Add_Ammo(player,weapon,(unsigned char)variant,1,1)>0;
}

int CODOL_KnifeCanBeGrabbed(const playerState_t *ps,unsigned weapon)
{
    if(!weapon || weapon>=(unsigned)BG_GetNumWeapons() ||
       !CODOL_IsKnifeDefinition(BG_GetWeaponDef((int)weapon)))return -1;
    if(!ps || weapon>=CODOL_WEAPON_SLOTS)return 0;
    /* Match Add_Ammo's ownership/compatible-ammo contract without mutation.
     * An owned knife is ammunition recovery, not replacement of an item. */
    if(!CODOL_WeaponBitsOwned(ps,weapon) &&
       !BG_PlayerHasCompatibleWeapon(ps,weapon))return 0;
    return BG_GetMaxPickupableAmmo(ps,weapon)>0;
}
#endif
