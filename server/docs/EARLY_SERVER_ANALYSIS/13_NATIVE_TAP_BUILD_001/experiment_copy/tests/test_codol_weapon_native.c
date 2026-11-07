#include "codol_weapon_native.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void weapon_core_test(void)
{
    uint8_t header[0xbfc]={0},points[8]={0,0,128,63,0,0,0,64};
    codol_mounted_weapon_t source={{28,header,sizeof(header)},{"w","source4","display","source12"},0};
    codol_weapon_animations_t animations={0}; codol_weapon_ammo_names_t ammo={0};
    codol_weapon_tail_t tail={0}; codol_weapon_hide_tag_handles_t tags={{0}};
    codol_native_weapon_core_t core={0},saved; XModel model={0};
    const XModel *models[11]={&model}; unsigned i;
    const unsigned offsets[]={0x9a0,0x9a4,0x9a8,0x9ac,0xbb4,0xbb8};
    header[0x10]=1; header[0x3c+62]=1; tags.tags[31]=7;
    header[0x588]=67; header[0x5e8]=18; animations.names[143]="variant"; animations.names[18]="drop";
    header[0x584]=93; header[0xbcd]=1; header[0xbd7]=1; header[0xbc2]=1;
    header[0xbbd]=1;
    { float head=1.5f,shield=2.5f; memcpy(header+0xa54,&head,4); memcpy(header+0xa98,&shield,4); }
    tail.count=6;
    for(i=0;i<6;++i) {
        tail.entries[i].offset=offsets[i]; tail.entries[i].kind=i<2 ? CODOL_WEAPON_DEP_STRING : CODOL_WEAPON_DEP_POINTS;
        if(i>=2) { tail.entries[i].point_count=1; tail.entries[i].points=points; }
    }
    tail.count=11;
    tail.entries[6].offset=0xb78; tail.entries[6].kind=CODOL_WEAPON_DEP_STRING; tail.entries[6].name="gl_m4_mp";
    tail.entries[7].offset=0xb88; tail.entries[7].kind=CODOL_WEAPON_DEP_STRING; tail.entries[7].name="heiap_barrett_post_penetrate";
    tail.entries[8].offset=0x9fc; tail.entries[8].kind=CODOL_WEAPON_DEP_STRING; tail.entries[8].name="HINT_USE";
    tail.entries[9].offset=0xa00; tail.entries[9].kind=CODOL_WEAPON_DEP_STRING; tail.entries[9].name="HINT_DROP";
    tail.entries[10].offset=0xa24; tail.entries[10].kind=CODOL_WEAPON_DEP_STRING; tail.entries[10].name="script_mods";
    memset(header+0xa04,255,8);
    header[0x38]=1; models[10]=&model;
    memset(header+0xb7c,255,4); memset(header+0xb8c,255,4);
    assert(CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core));
    assert(core.definition.szAltWeaponName==tail.entries[6].name && core.partner_weapon_name==tail.entries[7].name);
    assert(!core.definition.altWeaponIndex);
    assert(core.inherits_perks==1);
    assert(core.lock_warning_gate==1);
    saved=core;header[0xbbd]=2;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core));
    assert(!memcmp(&saved,&core,sizeof(core)));header[0xbbd]=1;
    assert(core.script_mods==tail.entries[10].name && !core.definition.szScript);
    assert(core.definition.szUseHintString==tail.entries[8].name && core.definition.dropHintString==tail.entries[9].name);
    assert(!core.definition.iUseHintStringIndex && !core.definition.dropHintStringIndex);
    assert(core.source_models[10]==&model && !core.definition.worldModel[7]);
    assert(core.definition.handXModel==&model && core.definition.damage==67 && core.timings.reload_empty_add_variant==18);
    assert(!strcmp(core.definition.szInternalName,"w") && !strcmp(core.definition.szDisplayName,"display"));
    assert(!core.definition.szOverlayName && !core.definition.szModeName);
    for(i=0;i<4;++i) assert(core.source_strings[i]==source.strings[i]);
    assert(core.definition.szAmmoName==source.strings[0] && core.definition.szClipName==source.strings[0]);
    assert(core.animations.names[143]==animations.names[143] && core.definition.szXAnims[15]==animations.names[18]);
    assert(core.hide_tags.tags[31]==7);
    assert(core.definition.iSharedAmmoCap==93 && core.definition.bClipOnly==1);
    assert(core.definition.bNoPartialReload==1);
    assert(core.definition.locationDamageMultipliers[2]==1.5f && core.shield_damage_multiplier==2.5f);
    for(i=0;i<8;++i) assert(!core.definition.hideTags[i]);
    for(i=0;i<4;++i) assert(core.graphs.points[i] && core.graphs.points[i][0][0]==1 && core.graphs.points[i][0][1]==2);
    assert(core.definition.accuracyGraphKnots[0]==core.graphs.points[0]); saved=core;
    for(i=6;i<11;++i) {
        tail.count=i;
        assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
        tail.count=11; tail.entries[i].kind=CODOL_WEAPON_DEP_ASSET;
        assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
        tail.entries[i].kind=CODOL_WEAPON_DEP_STRING;
        tail.entries[11]=tail.entries[i]; tail.count=12;
        assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
        tail.count=11;
    }
    memset(header+0xa98,255,4);
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    { float shield=2.5f; memcpy(header+0xa98,&shield,4); }
    header[0x340]=5;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x340]=0; header[0x34c]=6;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x34c]=0;
    header[0x344]=12;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x344]=255;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x344]=0;
    header[0x348]=4;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x348]=0; header[0x354]=6;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x354]=0;
    tags.tags[31]=0;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    tags.tags[31]=7; models[0]=NULL;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    models[0]=&model; header[0x350]=7;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    header[0x350]=0; tail.entries[5].points=NULL;
    assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && !memcmp(&core,&saved,sizeof(core)));
    assert(core.graphs.points[0][0][1]==2); tail.entries[5].points=points;
    for(i=0;i<8;++i) {
        header[0x588]=(uint8_t)i;
        assert(CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core) && core.definition.damage==(int)i);
    }
    saved=core;
    for(i=2;i<256;++i) {
        header[0xbc2]=(uint8_t)i;
        assert(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core));
        assert(!memcmp(&core,&saved,sizeof(core)));
    }
    header[0xbc2]=0;
    tail.entries[6].name=NULL; tail.entries[7].name="";
    tail.entries[8].name=""; tail.entries[9].name=NULL; tail.entries[10].name=NULL;
    assert(CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,&tags,&core));
    assert(core.definition.szAltWeaponName && !*core.definition.szAltWeaponName);
    assert(core.partner_weapon_name && !*core.partner_weapon_name);
    assert(core.script_mods && !*core.script_mods);
    assert(core.inherits_perks==0);
    assert(core.definition.szUseHintString && !*core.definition.szUseHintString);
    assert(core.definition.dropHintString && !*core.definition.dropHintString);
    CODOL_FreeNativeWeaponCore(&core); CODOL_FreeNativeWeaponCore(&core);
    memset(&saved,0,sizeof(saved)); assert(!memcmp(&core,&saved,sizeof(core)));
}
static void weapon_type_test(void)
{
    uint8_t header[0xbfc]={0}; codol_mounted_weapon_t source={{28,header,sizeof(header)},{0},0};
    struct WeaponDef native={0},saved; unsigned type,inventory,i,j;
    const weapType_t expected_types[]={WEAPTYPE_BULLET,WEAPTYPE_GRENADE,WEAPTYPE_PROJECTILE,
        WEAPTYPE_BINOCULARS,WEAPTYPE_GRENADE};
    const uint32_t invalid_types[]={5,6,255,UINT32_MAX};
    const uint32_t invalid_inventories[]={6,7,255,UINT32_MAX};
    native.damage=91; native.weapClass=WEAPCLASS_MG;
    for(type=0;type<5;++type) for(inventory=0;inventory<6;++inventory) {
        header[0x340]=(uint8_t)type; header[0x34c]=(uint8_t)inventory;
        assert(CODOL_ApplyNativeWeaponType(&source,&native));
        assert(native.weapType==expected_types[type] && (unsigned)native.inventoryType==inventory);
        assert(native.damage==91 && native.weapClass==WEAPCLASS_MG);
    }
    saved=native;
    for(i=0;i<2;++i) for(j=0;j<sizeof(invalid_types)/sizeof(*invalid_types);++j) {
        const uint32_t *invalid=i ? invalid_inventories : invalid_types;
        uint32_t value=invalid[j]; unsigned offset=i ? 0x34c : 0x340,k;
        memset(header,0,sizeof(header));
        for(k=0;k<4;++k) header[offset+k]=(uint8_t)(value>>(8*k));
        assert(!CODOL_ApplyNativeWeaponType(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    }
    memset(header,0,sizeof(header)); source.asset.size=0xbfb;
    assert(!CODOL_ApplyNativeWeaponType(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    source.asset.size=sizeof(header); source.asset.type=4;
    assert(!CODOL_ApplyNativeWeaponType(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    assert(!CODOL_ApplyNativeWeaponType(NULL,&native) && !CODOL_ApplyNativeWeaponType(&source,NULL));
}
static void weapon_class_test(void)
{
    uint8_t header[0xbfc]={0}; codol_mounted_weapon_t source={{28,header,sizeof(header)},{0},0};
    struct WeaponDef native={0},saved; unsigned i,k;
    const unsigned ids[]={0,1,2,3,4,5,6,7,8,9,10,11};
    const weapClass_t expected[]={WEAPCLASS_RIFLE,WEAPCLASS_RIFLE,WEAPCLASS_MG,WEAPCLASS_SMG,WEAPCLASS_SPREAD,
        WEAPCLASS_PISTOL,WEAPCLASS_GRENADE,WEAPCLASS_ROCKETLAUNCHER,WEAPCLASS_TURRET,WEAPCLASS_GRENADE,
        WEAPCLASS_NON_PLAYER,WEAPCLASS_ITEM};
    const uint32_t invalid[]={12,255,256,UINT32_MAX};
    native.damage=91; native.weapType=WEAPTYPE_PROJECTILE; native.inventoryType=WEAPINVENTORY_OFFHAND;
    for(i=0;i<sizeof(ids)/sizeof(*ids);++i) {
        header[0x344]=(uint8_t)ids[i];
        assert(CODOL_ApplyNativeWeaponClass(&source,&native) && native.weapClass==expected[i]);
        assert(native.damage==91 && native.weapType==WEAPTYPE_PROJECTILE && native.inventoryType==WEAPINVENTORY_OFFHAND);
    }
    saved=native;
    for(i=0;i<sizeof(invalid)/sizeof(*invalid);++i) {
        for(k=0;k<4;++k) header[0x344+k]=(uint8_t)(invalid[i]>>(8*k));
        assert(!CODOL_ApplyNativeWeaponClass(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    }
    memset(header,0,sizeof(header)); source.asset.size=0xbfb;
    assert(!CODOL_ApplyNativeWeaponClass(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    source.asset.size=sizeof(header); source.asset.type=4;
    assert(!CODOL_ApplyNativeWeaponClass(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    source.asset.type=28; source.asset.data=NULL;
    assert(!CODOL_ApplyNativeWeaponClass(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
    assert(!CODOL_ApplyNativeWeaponClass(NULL,&native) && !CODOL_ApplyNativeWeaponClass(&source,NULL));
}
int main(void)
{
    {
        uint8_t data[0xbfc]={0}; codol_mounted_weapon_t source={{28,data,sizeof(data)},{0},0};
        struct WeaponDef native={0},saved; unsigned mode,i,j;
        const uint32_t invalid[]={0x7f800000,0xff800000,0x7fc00000};
        native.damage=91; native.fAdsViewKickCenterSpeed=37; native.fHipViewScatterMax=41;
        for(mode=0;mode<2;++mode) {
            unsigned base=mode ? 0x958 : 0x900; data[base]=(uint8_t)(7+mode);
            for(i=0;i<13;++i) {
                float value=100*mode+i+0.25f;
                if((i>=1 && i<=4) || i>=9) value=-value;
                memcpy(data+base+4+4*i,&value,4);
            }
        }
        assert(CODOL_ApplyNativeWeaponRecoil(&source,&native));
        assert(native.adsGunKickReducedKickBullets==7 && native.hipGunKickReducedKickBullets==8);
        assert(native.adsGunKickReducedKickPercent==0.25f && native.hipGunKickReducedKickPercent==100.25f);
        assert(native.fAdsGunKickPitchMin==-1.25f && native.fAdsGunKickPitchMax==-2.25f);
        assert(native.fHipGunKickPitchMin==-101.25f && native.fHipGunKickPitchMax==-102.25f);
        assert(native.fAdsGunKickYawMin==-3.25f && native.fAdsGunKickYawMax==-4.25f);
        assert(native.fHipGunKickYawMin==-103.25f && native.fHipGunKickYawMax==-104.25f);
        assert(native.fAdsGunKickAccel==5.25f && native.fAdsGunKickSpeedMax==6.25f && native.fAdsGunKickSpeedDecay==7.25f && native.fAdsGunKickStaticDecay==8.25f);
        assert(native.fHipGunKickAccel==105.25f && native.fHipGunKickSpeedMax==106.25f && native.fHipGunKickSpeedDecay==107.25f && native.fHipGunKickStaticDecay==108.25f);
        assert(native.fAdsViewKickPitchMin==-9.25f && native.fAdsViewKickPitchMax==-10.25f && native.fAdsViewKickYawMin==-11.25f && native.fAdsViewKickYawMax==-12.25f);
        assert(native.fHipViewKickPitchMin==-109.25f && native.fHipViewKickPitchMax==-110.25f && native.fHipViewKickYawMin==-111.25f && native.fHipViewKickYawMax==-112.25f);
        assert(native.damage==91 && native.fAdsViewKickCenterSpeed==37 && native.fHipViewScatterMax==41); saved=native;
        for(mode=0;mode<2;++mode) for(i=0;i<13;++i) {
            unsigned offset=(mode ? 0x958 : 0x900)+4+4*i; uint8_t restore[4]; memcpy(restore,data+offset,4);
            for(j=0;j<3;++j) {
                memcpy(data+offset,invalid+j,4);
                assert(!CODOL_ApplyNativeWeaponRecoil(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            }
            if(i==0 || (i>=5 && i<=8)) {
                float negative=-1; memcpy(data+offset,&negative,4);
                assert(!CODOL_ApplyNativeWeaponRecoil(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            }
            memcpy(data+offset,restore,4);
        }
        for(mode=0;mode<2;++mode) {
            unsigned base=mode ? 0x958 : 0x900; memset(data+base,255,4);
            assert(!CODOL_ApplyNativeWeaponRecoil(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            memset(data+base,0,4); data[base]=(uint8_t)(7+mode);
        }
        source.asset.size=0xbfb;
        assert(!CODOL_ApplyNativeWeaponRecoil(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.size=sizeof(data); source.asset.type=4;
        assert(!CODOL_ApplyNativeWeaponRecoil(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        assert(!CODOL_ApplyNativeWeaponRecoil(NULL,&native) && !CODOL_ApplyNativeWeaponRecoil(&source,NULL));
        source.asset.type=28; memset(data,0,sizeof(data));
        assert(CODOL_ApplyNativeWeaponRecoil(&source,&native) && !native.adsGunKickReducedKickBullets && !native.fHipViewKickYawMax);
    }
    {
        uint8_t data[0xbfc]={0}; codol_mounted_weapon_t source={{28,data,sizeof(data)},{0},0};
        struct WeaponDef native={0},saved; codol_weapon_timing_extensions_t extra={0},old_extra;
        const uint32_t values[]={0,1,100,3000,INT32_MAX}; unsigned i,k;
        for(i=0;i<sizeof(values)/sizeof(*values);++i) {
            for(k=0;k<4;++k) data[0x55c+k]=data[0xba0+k]=(uint8_t)(values[i]>>(8*k));
            assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
            assert(CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
            assert(native.iStartAmmo==(int)values[i] && native.iFirstRaiseTime==(int)values[i]);
            assert(native.iMaxAmmo==0 && native.iClipSize==0); /* No clamping to capacity. */
        }
        saved=native; old_extra=extra;
        memset(data+0x55c,255,4);
        assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        memset(data+0xba0,255,4);
        assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra) && !memcmp(&native,&saved,sizeof(native)) && !memcmp(&extra,&old_extra,sizeof(extra)));
    }
    {
        uint8_t data[0xbfc]={0}; codol_mounted_weapon_t source={{28,data,sizeof(data)},{0},0};
        struct WeaponDef native={0},saved; float shield=77,old_shield; unsigned i,j;
        const uint32_t invalid[]={0xbf800000,0x7f800000,0xff800000,0x7fc00000};
        native.damage=91;
        for(i=0;i<20;++i) { float value=i+0.25f; memcpy(data+0xa4c+4*i,&value,4); }
        memset(data+0xa9c,255,4); /* Neighbor is not a hit-location multiplier. */
        assert(CODOL_ApplyNativeWeaponLocationDamage(&source,&native,&shield));
        for(i=0;i<19;++i) assert(native.locationDamageMultipliers[i]==i+0.25f);
        assert(shield==19.25f && native.damage==91); saved=native; old_shield=shield;
        for(i=0;i<20;++i) for(j=0;j<sizeof(invalid)/sizeof(*invalid);++j) {
            float restore=i+0.25f;
            memcpy(data+0xa4c+4*i,invalid+j,4);
            assert(!CODOL_ApplyNativeWeaponLocationDamage(&source,&native,&shield));
            assert(!memcmp(&native,&saved,sizeof(native)) && shield==old_shield);
            memcpy(data+0xa4c+4*i,&restore,4);
        }
        source.asset.size=0xbfb;
        assert(!CODOL_ApplyNativeWeaponLocationDamage(&source,&native,&shield) && !memcmp(&native,&saved,sizeof(native)) && shield==old_shield);
        source.asset.size=sizeof(data); source.asset.type=4;
        assert(!CODOL_ApplyNativeWeaponLocationDamage(&source,&native,&shield) && shield==old_shield);
        source.asset.type=28;
        assert(!CODOL_ApplyNativeWeaponLocationDamage(NULL,&native,&shield));
        assert(!CODOL_ApplyNativeWeaponLocationDamage(&source,NULL,&shield));
        assert(!CODOL_ApplyNativeWeaponLocationDamage(&source,&native,NULL));
        memset(data+0xa4c,0,80);
        assert(CODOL_ApplyNativeWeaponLocationDamage(&source,&native,&shield) && shield==0);
        for(i=0;i<19;++i) assert(native.locationDamageMultipliers[i]==0);
    }
    {
        uint8_t data[0xbfc]={0}; codol_mounted_weapon_t source={{28,data,sizeof(data)},{"none",NULL,NULL,NULL},0};
        codol_weapon_animations_t animations={0}; codol_weapon_ammo_names_t ammo={0}; codol_weapon_tail_t tail={0};
        codol_native_weapon_core_t native={0},saved; unsigned i;
        const unsigned offsets[]={0x9a0,0x9a4,0x9a8,0x9ac,0xbb4,0xbb8};
        const unsigned forbidden[]={0x10,0x3c,0x340,0x35c,0x588,0x670,0xbc8,0xbf8};
        memset(data,255,4); data[0x67a]=0xe0; data[0x67b]=0x3f;
        tail.count=6;
        for(i=0;i<6;++i) {
            tail.entries[i].offset=offsets[i]; tail.entries[i].kind=i<2 ? CODOL_WEAPON_DEP_STRING : CODOL_WEAPON_DEP_POINTS;
            if(i<2) tail.entries[i].name="noweapon.accu";
        }
        tail.count=11;
        tail.entries[6].offset=0xb78; tail.entries[6].kind=CODOL_WEAPON_DEP_STRING;
        tail.entries[7].offset=0xb88; tail.entries[7].kind=CODOL_WEAPON_DEP_STRING;
        tail.entries[8].offset=0x9fc; tail.entries[8].kind=CODOL_WEAPON_DEP_STRING;
        tail.entries[9].offset=0xa00; tail.entries[9].kind=CODOL_WEAPON_DEP_STRING;
        tail.entries[10].offset=0xa24; tail.entries[10].kind=CODOL_WEAPON_DEP_STRING;
        assert(CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native));
        assert(!strcmp(native.definition.szInternalName,"none") && native.definition.sprintDurationScale==1.75f);
        assert(!*native.definition.szAmmoName && !*native.definition.szClipName && !*native.definition.szAltWeaponName);
        assert(!*native.definition.szUseHintString && !*native.definition.dropHintString && !*native.definition.szScript);
        assert(!*native.definition.fireRumble && !*native.definition.meleeImpactRumble && !native.definition.damage);
        for(i=0;i<33;++i) assert(native.definition.szXAnims[i] && !*native.definition.szXAnims[i]);
        saved=native;
        for(i=0;i<sizeof(forbidden)/sizeof(*forbidden);++i) {
            data[forbidden[i]]=1;
            assert(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native) && !memcmp(&native,&saved,sizeof(native)));
            data[forbidden[i]]=0;
        }
        animations.names[143]="unexpected";
        assert(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native) && !memcmp(&native,&saved,sizeof(native)));
        animations.names[143]=NULL; ammo.ammo="unexpected";
        assert(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native) && !memcmp(&native,&saved,sizeof(native)));
        ammo.ammo=NULL; tail.entries[0].name="wrong.accu";
        assert(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native) && !memcmp(&native,&saved,sizeof(native)));
        tail.entries[0].name="noweapon.accu"; data[0x9b0]=1;
        assert(!CODOL_BuildNativeNullWeapon(&source,&animations,&ammo,&tail,&native) && !memcmp(&native,&saved,sizeof(native)));
        CODOL_FreeNativeWeaponCore(&native);
    }
    {
        uint8_t data[0xbfc]={0}; codol_mounted_weapon_t source={{28,data,sizeof(data)},{0},0};
        struct WeaponDef native={0},saved; unsigned p,o,i,k;
        const uint32_t invalid_penetration[]={4,5,255,256,UINT32_MAX};
        const uint32_t invalid_offhand[]={6,7,255,256,UINT32_MAX};
        const PenetrateType penetration[]={PENETRATE_TYPE_NONE,PENETRATE_TYPE_SMALL,PENETRATE_TYPE_MEDIUM,PENETRATE_TYPE_LARGE};
        const OffhandClass offhand[]={OFFHAND_CLASS_NONE,OFFHAND_CLASS_FRAG_GRENADE,OFFHAND_CLASS_SMOKE_GRENADE,OFFHAND_CLASS_FLASH_GRENADE,OFFHAND_CLASS_CODOL_FRAG_ALT,OFFHAND_CLASS_CODOL_EQUIPMENT};
        native.damage=89; native.stance=WEAPSTANCE_PRONE;
        for(p=0;p<4;++p) for(o=0;o<6;++o) {
            data[0x348]=(uint8_t)p; data[0x354]=(uint8_t)o;
            data[0xbc4]=(uint8_t)(p&1);
            assert(CODOL_ApplyNativeWeaponCombatClasses(&source,&native));
            assert(native.penetrateType==penetration[p] && native.offhandClass==offhand[o]);
            assert(native.bRifleBullet==(int)(p&1));
            assert(native.damage==89 && native.stance==WEAPSTANCE_PRONE);
        }
        saved=native;
        data[0xbc4]=2;
        assert(!CODOL_ApplyNativeWeaponCombatClasses(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        data[0xbc4]=0;
        for(o=0;o<2;++o) for(i=0;i<sizeof(invalid_penetration)/sizeof(*invalid_penetration);++i) {
            const uint32_t *invalid=o ? invalid_offhand : invalid_penetration;
            memset(data,0,sizeof(data));
            for(k=0;k<4;++k) data[(o ? 0x354 : 0x348)+k]=(uint8_t)(invalid[i]>>(8*k));
            assert(!CODOL_ApplyNativeWeaponCombatClasses(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        }
        memset(data,0,sizeof(data)); source.asset.size=0xbfb;
        assert(!CODOL_ApplyNativeWeaponCombatClasses(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.size=sizeof(data); source.asset.type=4;
        assert(!CODOL_ApplyNativeWeaponCombatClasses(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.type=28; source.asset.data=NULL;
        assert(!CODOL_ApplyNativeWeaponCombatClasses(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        assert(!CODOL_ApplyNativeWeaponCombatClasses(NULL,&native) && !CODOL_ApplyNativeWeaponCombatClasses(&source,NULL));
    }
    weapon_class_test();
    weapon_type_test();
    weapon_core_test();
    uint8_t header[0xbfc]={0}; struct WeaponDef native={0},saved;
    codol_mounted_weapon_t source={{28,header,sizeof(header)},{0}};
    codol_weapon_timing_extensions_t extra={0},old_extra;
    unsigned offset;
    {
        const float values[]={0.95f,0.4f,1.25f};
        const uint32_t invalid[]={0xbf800000,0x7f800000,0xff800000,0x7fc00001}; unsigned i,j;
        memcpy(header+0x670,values,sizeof(values)); native.damage=77; native.aimDownSight=1;
        assert(CODOL_ApplyNativeWeaponMovement(&source,&native));
        assert(native.moveSpeedScale==values[0] && native.adsMoveSpeedScale==values[1] && native.sprintDurationScale==values[2]);
        assert(native.damage==77 && native.aimDownSight==1); saved=native;
        for(i=0;i<3;++i) for(j=0;j<4;++j) {
            memcpy(header+0x670+4*i,invalid+j,4);
            assert(!CODOL_ApplyNativeWeaponMovement(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            memcpy(header+0x670+4*i,values+i,4);
        }
        source.asset.size=0x67b;
        assert(!CODOL_ApplyNativeWeaponMovement(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.size=sizeof(header); source.asset.type=0;
        assert(!CODOL_ApplyNativeWeaponMovement(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.type=28; memset(header,0,sizeof(header));
        assert(CODOL_ApplyNativeWeaponMovement(&source,&native) && !native.moveSpeedScale && !native.adsMoveSpeedScale && !native.sprintDurationScale);
    }
    {
        const uint32_t rates[]={0x3b83126f,0x3b449ba6};
        const uint32_t invalid[]={0xbf800000,0x7f800000,0xff800000,0x7fc00001}; unsigned i,j;
        memcpy(header+0xa28,rates,sizeof(rates)); header[0xbc8]=1; header[0xbc9]=1;
        native.iAdsTransInTime=137; native.iAdsTransOutTime=251; native.damage=77;
        assert(CODOL_ApplyNativeWeaponAds(&source,&native));
        assert(!memcmp(native.fOOPosAnimLength,rates,sizeof(rates)) && native.aimDownSight==1 && native.bRechamberWhileAds==1);
        assert(native.iAdsTransInTime==137 && native.iAdsTransOutTime==251 && native.damage==77);
        saved=native;
        for(i=0;i<2;++i) for(j=0;j<4;++j) {
            memcpy(header+0xa28+4*i,invalid+j,4);
            assert(!CODOL_ApplyNativeWeaponAds(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            memcpy(header+0xa28+4*i,rates+i,4);
        }
        for(i=0;i<2;++i) {
            header[0xbc8+i]=2;
            assert(!CODOL_ApplyNativeWeaponAds(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            header[0xbc8+i]=1;
        }
        source.asset.size=0xbc9;
        assert(!CODOL_ApplyNativeWeaponAds(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        source.asset.size=sizeof(header);
        memset(header,0,sizeof(header));
        assert(CODOL_ApplyNativeWeaponAds(&source,&native) && !native.aimDownSight && !native.bRechamberWhileAds &&
            !native.fOOPosAnimLength[0] && !native.fOOPosAnimLength[1]);
    }
    {
        const weapFireType_t modes[]={WEAPON_FIRETYPE_FULLAUTO,WEAPON_FIRETYPE_SINGLESHOT,
            WEAPON_FIRETYPE_BURSTFIRE2,WEAPON_FIRETYPE_BURSTFIRE3,WEAPON_FIRETYPE_BURSTFIRE4,
            (weapFireType_t)5,(weapFireType_t)6};
        unsigned i,j; uint32_t mode;
        native.damage=137; native.iRechamberTime=467;
        for(i=0;i<7;++i) for(j=0;j<2;++j) {
            mode=i; memcpy(header+0x350,&mode,4); header[0xbc6]=j;
            assert(CODOL_ApplyNativeWeaponFireMode(&source,&native));
            assert(native.fireType==modes[i] && native.bBoltAction==(int)j);
            assert(native.damage==137 && native.iRechamberTime==467);
        }
        saved=native;
        for(i=7;i<9;++i) {
            mode=i; memcpy(header+0x350,&mode,4);
            assert(!CODOL_ApplyNativeWeaponFireMode(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        }
        memset(header+0x350,255,4);
        assert(!CODOL_ApplyNativeWeaponFireMode(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        memset(header+0x350,0,4); header[0xbc6]=2;
        assert(!CODOL_ApplyNativeWeaponFireMode(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        header[0xbc6]=0; source.asset.size=0xbc6;
        assert(!CODOL_ApplyNativeWeaponFireMode(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.size=sizeof(header); source.asset.type=0;
        assert(!CODOL_ApplyNativeWeaponFireMode(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.type=28;
        assert(!CODOL_ApplyNativeWeaponFireMode(NULL,&native) && !CODOL_ApplyNativeWeaponFireMode(&source,NULL));
        assert(CODOL_ApplyNativeWeaponFireMode(&source,&native) && native.fireType==WEAPON_FIRETYPE_FULLAUTO && !native.bBoltAction);
    }
    {
        const unsigned offsets[]={0x588,0x58c,0xa30,0xa34,0xa38,0xa3c};
        const uint32_t values[]={35,40,20,25,0x447a0000,0x44bb8000}; /* 1000,1500 */
        const uint32_t bad_ranges[]={0xbf800000,0x7f800000,0xff800000,0x7fc00001};
        unsigned i,j;
        for(i=0;i<6;++i) memcpy(header+offsets[i],values+i,4);
        native.iMeleeDamage=135; native.iFireTime=137;
        assert(CODOL_ApplyNativeWeaponDamage(&source,&native));
        assert(native.damage==35 && native.playerDamage==40 && native.minDamage==20 && native.minPlayerDamage==25);
        assert(native.fMaxDamageRange==1000 && native.fMinDamageRange==1500);
        assert(native.iMeleeDamage==135 && native.iFireTime==137);
        saved=native;
        for(i=0;i<4;++i) {
            memset(header+offsets[i],255,4);
            assert(!CODOL_ApplyNativeWeaponDamage(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
            memcpy(header+offsets[i],values+i,4);
        }
        for(i=4;i<6;++i) for(j=0;j<4;++j) {
            memcpy(header+offsets[i],bad_ranges+j,4);
            assert(!CODOL_ApplyNativeWeaponDamage(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
            memcpy(header+offsets[i],values+i,4);
        }
        source.asset.size=0xa3f;
        assert(!CODOL_ApplyNativeWeaponDamage(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.size=sizeof(header); source.asset.type=2;
        assert(!CODOL_ApplyNativeWeaponDamage(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.type=28;
        assert(!CODOL_ApplyNativeWeaponDamage(NULL,&native) && !CODOL_ApplyNativeWeaponDamage(&source,NULL));
        memcpy(header+0xa3c,values+4,4); /* Equal endpoints are meaningful. */
        assert(CODOL_ApplyNativeWeaponDamage(&source,&native) && native.fMinDamageRange==1000);
        memcpy(header+0xa38,values+5,4); /* Preserve reversed endpoints too. */
        assert(CODOL_ApplyNativeWeaponDamage(&source,&native) && native.fMaxDamageRange==1500 && native.fMinDamageRange==1000);
        memset(header,0,sizeof(header));
        assert(CODOL_ApplyNativeWeaponDamage(&source,&native) && !native.damage && !native.playerDamage &&
            !native.minDamage && !native.minPlayerDamage && !native.fMaxDamageRange && !native.fMinDamageRange);
    }
    {
        codol_weapon_tail_t tail={0}; codol_native_weapon_graphs_t owner={0},old_owner;
        const unsigned offsets[]={0x9a0,0x9a4,0x9a8,0x9ac,0xbb4,0xbb8};
        uint8_t bytes[4][17]={{0}}; unsigned i,j; float value;
        tail.count=6;
        for(i=0;i<6;++i) {
            tail.entries[i].offset=offsets[i];
            tail.entries[i].kind=i<2 ? CODOL_WEAPON_DEP_STRING : CODOL_WEAPON_DEP_POINTS;
            if(i<2) { tail.entries[i].name=i ? "players" : "actors"; continue; }
            tail.entries[i].points=bytes[i-2]+1; tail.entries[i].point_count=2;
            for(j=0;j<4;++j) { value=(i-2)*10+j+0.5f; memcpy(bytes[i-2]+1+4*j,&value,4); }
        }
        native.damage=77;
        assert(CODOL_BindNativeWeaponGraphs(&tail,&native,&owner));
        assert(!strcmp(native.accuracyGraphName[0],"actors") && !strcmp(native.accuracyGraphName[1],"players"));
        assert(native.accuracyGraphKnots[0][1][1]==3.5f && native.accuracyGraphKnots[1][0][0]==10.5f);
        assert(native.originalAccuracyGraphKnots[0][1][1]==23.5f && native.originalAccuracyGraphKnots[1][0][0]==30.5f);
        for(i=0;i<2;++i) assert(native.accuracyGraphKnotCount[i]==2 && native.originalAccuracyGraphKnotCount[i]==2);
        native.accuracyGraphKnots[0][0][0]=99;
        assert(native.originalAccuracyGraphKnots[0][0][0]==20.5f && native.damage==77);
        saved=native; old_owner=owner;
        memset(bytes[3]+1,255,4);
        assert(!CODOL_BindNativeWeaponGraphs(&tail,&native,&owner));
        assert(!memcmp(&saved,&native,sizeof(native)) && !memcmp(&old_owner,&owner,sizeof(owner)));
        assert(owner.points[0][0][0]==99); /* Failed replacement retains owned payload. */
        tail.entries[5].point_count=0;
        tail.entries[0].offset=0x9a4;
        assert(!CODOL_BindNativeWeaponGraphs(&tail,&native,&owner));
        tail.entries[0].offset=0x9a0;
        for(i=2;i<6;++i) { tail.entries[i].point_count=0; tail.entries[i].points=NULL; }
        assert(CODOL_BindNativeWeaponGraphs(&tail,&native,&owner));
        for(i=0;i<4;++i) assert(!owner.points[i]);
        assert(!native.accuracyGraphKnots[0] && !native.originalAccuracyGraphKnots[1] && !native.originalAccuracyGraphKnotCount[1]);
        CODOL_FreeNativeWeaponGraphs(&owner); CODOL_FreeNativeWeaponGraphs(&owner);
    }
    {
        const unsigned offsets[]={0x590,0x5a0,0x5a4,0x5c0,0x5c4};
        const uint32_t values[]={135,79,100,800,1159}; unsigned i;
        for(i=0;i<5;++i) memcpy(header+offsets[i],values+i,4);
        native.damage=77; native.iFireTime=137;
        assert(CODOL_ApplyNativeWeaponMelee(&source,&native));
        assert(native.iMeleeDamage==135 && native.iMeleeDelay==79 && native.meleeChargeDelay==100);
        assert(native.iMeleeTime==800 && native.meleeChargeTime==1159 && native.damage==77 && native.iFireTime==137);
        saved=native;
        for(i=0;i<5;++i) {
            memset(header+offsets[i],255,4);
            assert(!CODOL_ApplyNativeWeaponMelee(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
            memcpy(header+offsets[i],values+i,4);
        }
        source.asset.size=0x5c4;
        assert(!CODOL_ApplyNativeWeaponMelee(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.size=sizeof(header); source.asset.type=2;
        assert(!CODOL_ApplyNativeWeaponMelee(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
        source.asset.type=28; memset(header,0,sizeof(header));
        assert(CODOL_ApplyNativeWeaponMelee(&source,&native) && !native.iMeleeDamage && !native.iMeleeDelay &&
            !native.meleeChargeDelay && !native.iMeleeTime && !native.meleeChargeTime);
    }
    for (offset=0x59c;offset<=0x638;offset+=4) { uint32_t value=offset; memcpy(header+offset,&value,4); }
    { uint32_t in=300,out=400; memcpy(header+0x950,&in,4); memcpy(header+0x954,&out,4); }
    { uint32_t fire=137; memcpy(header+0xb68,&fire,4); }
    native.damage=77; native.szInternalName="unchanged";
    assert(CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
    assert(native.iRechamberTime==0x5ac && native.iRechamberBoltTime==0x5b4);
    assert(native.iFireTime==137);
    assert(native.iFireDelay==0x59c && native.iHoldFireTime==0x5b8);
    assert(native.iDetonateDelay==0x5a8 && native.iDetonateTime==0x5bc);
    assert(native.iAdsTransInTime==300 && native.iAdsTransOutTime==400);
    {
        const unsigned offsets[]={0x59c,0x5a8,0x5b8,0x5bc,0x950,0x954};
        const uint32_t invalid[]={0x80000000u,UINT32_MAX}; unsigned i,j;
        saved=native; old_extra=extra;
        for(i=0;i<6;++i) {
            uint32_t original; memcpy(&original,header+offsets[i],4);
            for(j=0;j<2;++j) {
                memcpy(header+offsets[i],invalid+j,4);
                assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
                assert(!memcmp(&native,&saved,sizeof(native)) && !memcmp(&extra,&old_extra,sizeof(extra)));
            }
            memcpy(header+offsets[i],&original,4);
        }
    }
    assert(native.iReloadTime==0x5c8 && native.iReloadEmptyTime==0x5d4 && native.iReloadEndTime==0x5f4);
    assert(native.iReloadAddTime==0x5dc && native.iReloadStartTime==0x5ec && native.iReloadStartAddTime==0x5f0);
    assert(native.iDropTime==0x5f8 && native.iRaiseTime==0x5fc && native.iAltDropTime==0x600);
    assert(native.quickDropTime==0x604 && native.quickRaiseTime==0x608);
    assert(native.iEmptyRaiseTime==0x610 && native.iEmptyDropTime==0x614);
    assert(native.sprintInTime==0x618 && native.sprintOutTime==0x620);
    assert(extra.dive_in==0x630 && extra.dive_out==0x638);
    {
        const unsigned locomotion[]={0x618,0x620,0x630,0x638}; unsigned i;
        native.sprintLoopTime=91; native.nightVisionWearTime=92; native.nightVisionRemoveTime=93;
        saved=native; old_extra=extra;
        for(i=0;i<4;++i) {
            uint32_t value=locomotion[i]; memset(header+value,255,4);
            assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
            assert(!memcmp(&native,&saved,sizeof(native)) && !memcmp(&extra,&old_extra,sizeof(extra)));
            memcpy(header+value,&value,4);
        }
        assert(CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
        assert(native.sprintLoopTime==91 && native.nightVisionWearTime==92 && native.nightVisionRemoveTime==93);
    }
    assert(extra.rechamber_variant==0x5b0 && extra.reload_variant==0x5cc && extra.reload_empty_variant==0x5d8);
    assert(extra.reload_add_variant==0x5e0 && extra.reload_empty_add==0x5e4 && extra.reload_empty_add_variant==0x5e8);
    assert(native.damage==77 && !strcmp(native.szInternalName,"unchanged")); saved=native; old_extra=extra;
    for(offset=0x5dc;offset<=0x5f0;offset+=4) {
        uint32_t value=offset;
        memset(header+offset,255,4);
        assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
        assert(!memcmp(&native,&saved,sizeof(native)) && !memcmp(&extra,&old_extra,sizeof(extra)));
        memcpy(header+offset,&value,4);
    }
    memset(header+0x5d8,255,4);
    assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
    assert(!memcmp(&native,&saved,sizeof(native)) && !memcmp(&extra,&old_extra,sizeof(extra)));
    source.asset.size=0x614;
    assert(!CODOL_ApplyNativeWeaponTimings(&source,&native,&extra));
    source.asset.size=sizeof(header); memset(header,0,sizeof(header));
    assert(CODOL_ApplyNativeWeaponTimings(&source,&native,&extra) && !native.iRaiseTime && !extra.reload_variant);
    assert(!native.sprintInTime && !native.sprintOutTime && !extra.dive_in && !extra.dive_out);
    assert(!native.iFireDelay && !native.iHoldFireTime && !native.iDetonateDelay && !native.iDetonateTime);
    assert(!native.iAdsTransInTime && !native.iAdsTransOutTime);
    {
        uint32_t maximum=120,capacity=30,shots=8;
        memcpy(header+0x574,&maximum,4); memcpy(header+0xb60,&capacity,4); memcpy(header+0x578,&shots,4);
        native.iAmmoIndex=17; native.iClipIndex=23; native.iSharedAmmoCapIndex=29; native.iFireTime=137;
        memset(header+0x568,255,4); memset(header+0x570,255,4); memset(header+0x580,255,4);
        assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
        assert(native.iMaxAmmo==120 && native.iClipSize==30 && native.shotCount==8);
        {
            const uint32_t caps[]={0,1,29,30,31,120,121,0x7fffffff}; unsigned i,flag;
            for(i=0;i<sizeof(caps)/sizeof(*caps);++i) for(flag=0;flag<2;++flag) {
                memcpy(header+0x584,caps+i,4); header[0xbcd]=(uint8_t)flag;
                assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
                assert(native.iSharedAmmoCap==(int)caps[i] && native.bClipOnly==(int)flag);
                assert(native.iAmmoIndex==17 && native.iClipIndex==23 && native.iSharedAmmoCapIndex==29);
                assert(native.iMaxAmmo==120 && native.iClipSize==30 && native.shotCount==8);
            }
            saved=native;
            for(i=2;i<256;++i) {
                header[0xbcd]=(uint8_t)i;
                assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            }
            header[0xbcd]=1;
            { const uint32_t invalid[]={0x80000000,0xffffffff};
                for(i=0;i<2;++i) {
                    memcpy(header+0x584,invalid+i,4);
                    assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
                }
            }
            memset(header+0x584,0,4); header[0xbcd]=0;
        }
        {
            unsigned partial,segmented,invalid;
            for(partial=0;partial<2;++partial) for(segmented=0;segmented<2;++segmented) {
                header[0xbd7]=(uint8_t)partial; header[0xbd8]=(uint8_t)segmented;
                assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
                assert(native.bNoPartialReload==(int)partial && native.bSegmentedReload==(int)segmented);
                assert(native.iClipSize==30 && native.iAmmoIndex==17 && native.iClipIndex==23);
            }
            saved=native;
            for(invalid=2;invalid<256;++invalid) {
                header[0xbd7]=(uint8_t)invalid;
                assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            }
            header[0xbd7]=0;
            assert(CODOL_ApplyNativeWeaponAmmo(&source,&native) && !native.bNoPartialReload);
        }
        header[0xbd8]=1;
        assert(CODOL_ApplyNativeWeaponAmmo(&source,&native) && native.bSegmentedReload==1);
        saved=native; header[0xbd8]=2;
        assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        header[0xbd8]=0;
        assert(CODOL_ApplyNativeWeaponAmmo(&source,&native) && !native.bSegmentedReload);
        {
            const uint32_t caps[]={0,1,29,30,31,0x7fffffff}; unsigned i,j;
            for(i=0;i<6;++i) for(j=0;j<6;++j) {
                memcpy(header+0x764,caps+i,4); memcpy(header+0x768,caps+j,4);
                assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
                assert(native.iReloadAmmoAdd==(int)caps[i] && native.iReloadStartAdd==(int)caps[j]);
                assert(native.iClipSize==30 && native.iMaxAmmo==120 && native.shotCount==8);
            }
            saved=native;
            memset(header+0x764,255,4);
            assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            memcpy(header+0x764,caps+5,4); memset(header+0x768,255,4);
            assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
            memcpy(header+0x768,caps+5,4);
        }
        assert(native.iAmmoIndex==17 && native.iClipIndex==23 && native.iFireTime==137 && native.damage==77);
        saved=native; memset(header+0x578,255,4);
        assert(!CODOL_ApplyNativeWeaponAmmo(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        memset(header,0,sizeof(header)); assert(CODOL_ApplyNativeWeaponAmmo(&source,&native));
        assert(!native.iMaxAmmo && !native.iClipSize && !native.shotCount && native.iAmmoIndex==17 &&
            !native.iReloadAmmoAdd && !native.iReloadStartAdd && !native.iSharedAmmoCap &&
            !native.bClipOnly && native.iSharedAmmoCapIndex==29);
    }
    {
        XModel models[11]={{0}}; const XModel *bindings[11]; unsigned i;
        for(i=0;i<11;++i) { uint32_t ref=i+1; memcpy(header+0x10+4*i,&ref,4); bindings[i]=models+i; }
        native.gunXModel[15]=models; native.worldModel[15]=models;
        assert(CODOL_BindNativeWeaponModels(&source,bindings,&native));
        assert(native.handXModel==models && native.gunXModel[0]==models+1 && native.gunXModel[1]==models+2);
        for(i=0;i<2;++i) assert(native.worldModel[i]==models+3+i);
        assert(native.worldClipModel==models+5 && native.knifeModel==models+7 && native.worldKnifeModel==models+8);
        for(i=2;i<16;++i) assert(!native.gunXModel[i]);
        for(i=2;i<16;++i) assert(!native.worldModel[i]);
        assert(native.damage==77 && native.iAmmoIndex==17); saved=native;
        bindings[10]=NULL;
        assert(!CODOL_BindNativeWeaponModels(&source,bindings,&native) && !memcmp(&native,&saved,sizeof(native)));
        memset(header+0x10+4*10,0,4);
        assert(CODOL_BindNativeWeaponModels(&source,bindings,&native) && !native.worldModel[7]);
        memset(header+0x10,0,44); memset(bindings,0,sizeof(bindings));
        assert(CODOL_BindNativeWeaponModels(&source,bindings,&native) && !native.handXModel && !native.gunXModel[0]);
        assert(!native.worldClipModel && !native.knifeModel && !native.worldKnifeModel);
    }
    {
        codol_native_weapon_core_t core={0},before;
        XModel world={0},view={0}; unsigned i;
        core.definition.damage=91;
        core.definition.handXModel=&world;
        core.source_models[1]=&view;
        before=core;
        assert(!CODOL_BindNativeComposedWeaponModels(NULL,&view,&core));
        assert(!memcmp(&before,&core,sizeof(core)));
        assert(!CODOL_BindNativeComposedWeaponModels(&world,NULL,&core));
        assert(!memcmp(&before,&core,sizeof(core)));
        assert(CODOL_BindNativeComposedWeaponModels(&world,&view,&core));
        for(i=0;i<16;++i) {
            assert(core.definition.gunXModel[i]==&view);
            assert(core.definition.worldModel[i]==&world);
        }
        assert(core.definition.damage==91 && core.definition.handXModel==&world);
        assert(core.source_models[1]==&view);
    }
    {
        unsigned i; float value;
        for(i=0;i<13;++i) { value=i+0.25f; memcpy(header+(i<12 ? 0x6b8+4*i : 0x940),&value,4); }
        assert(CODOL_ApplyNativeWeaponSpread(&source,&native));
        assert(native.fHipSpreadStandMin==0.25f && native.fHipSpreadDuckedMin==1.25f && native.fHipSpreadProneMin==2.25f);
        assert(native.hipSpreadStandMax==3.25f && native.hipSpreadDuckedMax==4.25f && native.hipSpreadProneMax==5.25f);
        assert(native.fHipSpreadDecayRate==6.25f && native.fHipSpreadFireAdd==7.25f && native.fHipSpreadTurnAdd==8.25f);
        assert(native.fHipSpreadMoveAdd==9.25f && native.fHipSpreadDuckedDecay==10.25f && native.fHipSpreadProneDecay==11.25f);
        assert(native.fAdsSpread==12.25f && native.damage==77); saved=native;
        memset(header+0x940,255,4);
        assert(!CODOL_ApplyNativeWeaponSpread(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        value=-1; memcpy(header+0x940,&value,4);
        assert(!CODOL_ApplyNativeWeaponSpread(&source,&native) && !memcmp(&native,&saved,sizeof(native)));
        memset(header,0,sizeof(header)); assert(CODOL_ApplyNativeWeaponSpread(&source,&native) && !native.fAdsSpread);
    }
    {
        codol_weapon_animations_t animations={0}; char names[144][8]; unsigned i;
        for(i=0;i<144;++i) { snprintf(names[i],sizeof(names[i]),"slot%u",i); animations.names[i]=names[i]; }
        for(i=0;i<33;++i) native.szXAnims[i]="unmapped";
        assert(CODOL_ApplyNativeWeaponAnimationNames(&animations,&native));
        assert(!strcmp(native.szXAnims[15],"slot18") && !strcmp(native.szXAnims[13],"slot15"));
        assert(!strcmp(native.szXAnims[19],"slot22") && !strcmp(native.szXAnims[18],"slot21"));
        assert(!strcmp(native.szXAnims[21],"slot24") && !strcmp(native.szXAnims[20],"slot23"));
        assert(!strcmp(native.szXAnims[9],"slot9") && !strcmp(native.szXAnims[10],"slot11"));
        assert(!strcmp(native.szXAnims[12],"slot14") && !strcmp(native.szXAnims[17],"slot20"));
        assert(!strcmp(native.szXAnims[6],"slot6") && !strcmp(native.szXAnims[30],"slot36"));
        assert(!strcmp(native.szXAnims[7],"slot7") && !strcmp(native.szXAnims[8],"slot8"));
        assert(!strcmp(native.szXAnims[1],"slot1") && !strcmp(native.szXAnims[2],"slot2"));
        for(i=0;i<3;++i) assert(native.szXAnims[22+i]==animations.names[25+i]);
        for(i=3;i<=5;++i) assert(native.szXAnims[i]==animations.names[i]);
        assert(native.szXAnims[28]==animations.names[34] && native.szXAnims[29]==animations.names[35]);
        assert(native.szXAnims[11]==animations.names[13] && native.szXAnims[14]==animations.names[16]);
        assert(native.szXAnims[16]==animations.names[19] && native.szXAnims[25]==animations.names[31]);
        assert(!strcmp(native.szXAnims[0],"unmapped") && !strcmp(native.szXAnims[26],"unmapped"));
        assert(!strcmp(native.szXAnims[27],"unmapped") && !strcmp(native.szXAnims[31],"unmapped"));
        assert(!strcmp(native.szXAnims[32],"unmapped"));
        assert(!strcmp(animations.names[143],"slot143") && native.damage==77);
        saved=native;
        assert(!CODOL_ApplyNativeWeaponAnimationNames(NULL,&native) && !memcmp(&native,&saved,sizeof(native)));
        memset(&animations,0,sizeof(animations)); animations.names[18]="";
        assert(CODOL_ApplyNativeWeaponAnimationNames(&animations,&native));
        assert(native.szXAnims[15] && !*native.szXAnims[15] && !native.szXAnims[13]);
        for(i=3;i<=5;++i) assert(!native.szXAnims[i]);
        assert(!native.szXAnims[28] && !native.szXAnims[29] && !native.szXAnims[11]);
        assert(!native.szXAnims[14] && !native.szXAnims[16] && !native.szXAnims[25]);
    }
    {
        codol_weapon_ammo_names_t names={"reserve","magazine","shared",0};
        native.iAmmoIndex=17; native.iClipIndex=23; native.iSharedAmmoCapIndex=5;
        assert(CODOL_ApplyNativeWeaponAmmoNames(&names,"weapon",&native));
        assert(!strcmp(native.szAmmoName,"reserve") && !strcmp(native.szClipName,"magazine"));
        assert(!strcmp(native.szSharedAmmoCapName,"shared")); saved=native;
        assert(!CODOL_ApplyNativeWeaponAmmoNames(&names,"",&native) && !memcmp(&native,&saved,sizeof(native)));
        names.ammo=""; names.clip=NULL; names.shared_cap=NULL;
        assert(CODOL_ApplyNativeWeaponAmmoNames(&names,"weapon",&native));
        assert(!strcmp(native.szAmmoName,"weapon") && !strcmp(native.szClipName,"weapon") && !*native.szSharedAmmoCapName);
        assert(native.iAmmoIndex==17 && native.iClipIndex==23 && native.iSharedAmmoCapIndex==5 && native.damage==77);
    }
    puts("PASS: native weapon scalar/model/animation mapping, retained variants and atomic failures"); return 0;
}
