#include "codol_weapon_registry.h"
#include "codol_engine_state.h"
#include "codol_usercmd.h"
#include "codol_weapon_bits.h"
#include "xassets/weapondef.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static const struct { const char *name; int ammo,clip; } stock[]={
#include "fixtures/codol_stock_ammo_keys.inc"
};
/* This fixture uses a standalone playerState rather than the server's tracked
 * extension storage. Keep the owned-weapon seam local to the ammo binding test. */
int CODOL_WeaponBitsOwned(const playerState_t *ps, unsigned weapon)
{
    return ps && weapon < sizeof(ps->weapons) * 8u &&
        (ps->weapons[weapon >> 5] & (1u << (weapon & 31u))) != 0;
}
int main(void)
{
    codol_weapon_registry_t *r=CODOL_CreateWeaponRegistry();
    unsigned i; int a,c;
    assert(r);
    for(i=0;i<54;++i) {
        const char *ammo=stock[i].name,*clip=stock[i].name;
        unsigned gate=i==36 || i==42 || i==43;
        if(i==36) { ammo="mp5sd_ammo"; clip="mp5sd_clip"; }
        if(i==42 || i==43) { ammo="5.56 x 45 mm nato"; clip="scar_mp"; }
        assert(CODOL_RegisterWeaponKeys(r,i,stock[i].name,ammo,clip,gate,0,-1));
        assert(CODOL_GetWeaponKeys(r,i,&a,&c) && a==stock[i].ammo && c==stock[i].clip);
    }
    /* Ungated custom: inherit reserve, append clip. Gated SCAR: reuse both. */
    assert(CODOL_RegisterWeaponKeys(r,54,"*a 2 0","reserve2","clip2",0,0,2));
    assert(CODOL_GetWeaponKeys(r,54,&a,&c) && a==2 && c==53);
    assert(CODOL_RegisterWeaponKeys(r,55,"*a 42 0","5.56 x 45 mm nato","scar_mp",1,0,42));
    assert(CODOL_GetWeaponKeys(r,55,&a,&c) && a==42 && c==42);
    assert(!CODOL_RegisterWeaponKeys(r,57,"gap","a","c",0,0,-1));
    assert(!CODOL_RegisterWeaponKeys(r,56,"bad","a","c",2,0,-1));
    assert(!CODOL_RegisterWeaponKeys(r,56,"*bad","a","c",0,0,56));
    assert(!CODOL_RegisterWeaponKeys(r,56,"none","a","c",0,0,-1));
    assert(CODOL_RegisterWeaponKeys(r,56,"no_clip",NULL,NULL,0,1,-1));
    assert(CODOL_GetWeaponKeys(r,56,&a,&c) && a==53 && c==-1);
    assert(CODOL_RegisterWeaponKeys(r,57,"*a 2 override","5.56 x 45 mm nato","scar_mp",1,0,2));
    assert(CODOL_GetWeaponKeys(r,57,&a,&c) && a==42 && c==42); /* Name search precedes base. */
    assert(CODOL_RegisterWeaponKeys(r,58,"next",NULL,NULL,0,0,-1));
    assert(CODOL_GetWeaponKeys(r,58,&a,&c) && a==54 && c==54); /* No-clip did not append a clip. */
    {
        playerState_t ps={0}; struct WeaponDef d1={0},d2={0};
        struct WeaponDef *defs[CODOL_WEAPON_SLOTS]={0};
        codol_engine_player_bindings_t bindings={0},saved;
        codol_player_array_updates_t arrays={0};
        defs[7]=&d1; defs[8]=&d2;
        d1.iAmmoIndex=d2.iAmmoIndex=17; d1.iClipIndex=d2.iClipIndex=23;
        CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(42,7) && CODOL_MapWeapon(55,8));
        ps.weapons[0]=(1u<<7)|(1u<<8); ps.ammo[17]=120; ps.ammoclip[23]=30;
        bindings.alt_weapon=99;
        assert(CODOL_BuildEngineAmmoBindings(&bindings,&ps,r,defs));
        assert(bindings.alt_weapon==99 && bindings.clips[0].wire_key==42 && bindings.reserves[0].wire_key==42);
        assert(bindings.clips[1].engine_index==-1 && bindings.reserves[1].engine_index==-1);
        assert(CODOL_OverlayEngineAmmo(&arrays,&ps,bindings.clip_mask,bindings.clips,bindings.reserve_mask,bindings.reserves));
        assert(arrays.clip_index[0]==42 && arrays.clip_ammo[0][0]==30 && arrays.reserve_ammo[0]==120);
        saved=bindings; d2.iClipIndex=24;
        assert(!CODOL_BuildEngineAmmoBindings(&bindings,&ps,r,defs) && !memcmp(&bindings,&saved,sizeof(bindings)));
        ps.weapons[0]=0;
        assert(CODOL_BuildEngineAmmoBindings(&bindings,&ps,r,defs));
        assert(CODOL_OverlayEngineAmmo(&arrays,&ps,bindings.clip_mask,bindings.clips,bindings.reserve_mask,bindings.reserves));
        for(i=0;i<15;++i) assert(arrays.clip_index[i]==-1 && !arrays.clip_ammo[i][0] && !arrays.reserve_ammo[i]);
    }
    {
        /* An unlimited-ammo weapon (registry no_clip, C1 clip index -1) still
         * publishes its magazine, as the record keyed -1, in a bound slot
         * ahead of the unbound -1 slots. */
        playerState_t ps={0}; struct WeaponDef d1={0},d3={0};
        struct WeaponDef *defs[CODOL_WEAPON_SLOTS]={0};
        codol_engine_player_bindings_t bindings={0};
        codol_player_array_updates_t arrays={0};
        defs[7]=&d1; defs[9]=&d3;
        d1.iAmmoIndex=17; d1.iClipIndex=23; d3.iAmmoIndex=40; d3.iClipIndex=41;
        CODOL_ResetWeaponMap(); assert(CODOL_MapWeapon(42,7) && CODOL_MapWeapon(56,9));
        ps.weapons[0]=(1u<<7)|(1u<<9); ps.ammo[17]=120; ps.ammoclip[23]=30; ps.ammoclip[41]=400;
        assert(CODOL_BuildEngineAmmoBindings(&bindings,&ps,r,defs));
        assert(bindings.clips[0].wire_key==42 && bindings.clips[0].engine_index==23);
        assert(bindings.clips[1].wire_key==-1 && bindings.clips[1].engine_index==41);
        assert(bindings.clips[2].wire_key==-1 && bindings.clips[2].engine_index==-1);
        assert(CODOL_OverlayEngineAmmo(&arrays,&ps,bindings.clip_mask,bindings.clips,bindings.reserve_mask,bindings.reserves));
        assert(arrays.clip_index[1]==-1 && arrays.clip_ammo[1][0]==400);
        assert(arrays.clip_index[2]==-1 && !arrays.clip_ammo[2][0]);
    }
    CODOL_DestroyWeaponRegistry(r);
    puts("PASS: 108 measured stock ammo keys, custom registration and native inventory ammo bindings");
    return 0;
}
