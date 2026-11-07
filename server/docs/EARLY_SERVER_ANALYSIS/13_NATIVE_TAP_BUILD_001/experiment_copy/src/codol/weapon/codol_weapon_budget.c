/* See codol_weapon_budget.h for why "fall back to the stock weapon" is not
 * free and what it used to cost. */
#ifdef CODOL_SERVER
#include "codol_weapon_budget.h"
#include "codol_sv_weapons.h"
#include "codol_usercmd.h"
#include <string.h>
/* One composed name can append its own definition and a retained alternate. */
#define CODOL_NATIVE_WEAPON_HEADROOM 2u
extern int BG_GetNumWeapons(void);
extern int BG_FindWeaponIndexForName(const char *name);
int CODOL_NativeWeaponRoom(void)
{
    int count=BG_GetNumWeapons();
    return count>0 &&
        (unsigned)count+CODOL_NATIVE_WEAPON_HEADROOM<=CODOL_WEAPON_SLOTS;
}
int CODOL_WeaponAlreadyLive(const char *name)
{
    int engine;
    if(!name || !*name || !strcmp(name,"none")) return 0;
    engine=BG_FindWeaponIndexForName(name);
    return engine>0 && engine<BG_GetNumWeapons() && CODOL_WeaponToWire((unsigned)engine)>0;
}
const char *CODOL_SafeStockWeapon(const char *name)
{
    if(!name || !*name || !strcmp(name,"none")) return "none";
    if(CODOL_WeaponAlreadyLive(name)) return name;
    return CODOL_NativeWeaponRoom() ? name:"none";
}
#endif
