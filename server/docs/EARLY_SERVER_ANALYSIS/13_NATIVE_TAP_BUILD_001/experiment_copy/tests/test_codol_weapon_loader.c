#include "codol_weapon_native.h"
#include "codol_xmodel_native.h"
#include "codol_xanim_native.h"
#include "codol_effects_native.h"
#include "codol_sound_native.h"
#include "qcommon_io.h"
typedef struct XAnimParts XAnimParts;
#include "xassets/xanims.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned calls,fail_at;
static uint8_t header[0xbfc];
static XModel native_model;
static XModel native_projectile;
static int projectile_status=1,projectile_metadata;
static struct XAnimParts native_animation;
static int animation_status=1,empty_animations;
static codol_weapon_hide_tag_handles_t tags;
static FxEffectDef flashes[2];
static int effect_status=1,effect_metadata;
static int shell_metadata;
static FxEffectDef shells[4];
static snd_alias_list_t fire_alias,bounce_alias,explosion_alias;
static snd_alias_list_t reload_alias,putaway_alias,akimbo_alias;
static unsigned warning_calls;
/* This fixture exercises mounted weapon composition. Image/attachment engine
 * adapters belong to separate tests; fail loudly if they become reachable. */
int CODOL_LoadMountedWeaponAttachment(const char *name,codol_mounted_weapon_attachment_t *out)
{ (void)name; (void)out; assert(0); return -1; }
void CODOL_FreeMountedWeaponAttachment(codol_mounted_weapon_attachment_t *out)
{ (void)out; assert(0); }
int CODOL_LoadMountedWeaponHideTags(const char *name,codol_weapon_hide_tags_t *out)
{ (void)name; (void)out; assert(0); return -1; }
int CODOL_AcquireEngineWeaponHideTags(const codol_weapon_hide_tags_t *source,codol_weapon_hide_tag_handles_t *out)
{ (void)source; (void)out; assert(0); return -1; }
void CODOL_ReleaseEngineWeaponHideTags(codol_weapon_hide_tag_handles_t *out)
{ (void)out; assert(0); }
int CODOL_GetNativeWeaponMissileStickiness(const struct WeaponDef *definition,codol_missile_stickiness_t *out)
{ (void)definition; (void)out; assert(0); return 0; }
const char *CODOL_NativeEffectFailureDetail(void) { return "fixture effect unavailable"; }
void QDECL Com_PrintWarning(conChannel_t channel,const char *fmt,...)
{ (void)channel; (void)fmt; ++warning_calls; }
static int next(void);
int CODOL_LoadMountedWeaponVisuals(const char *name,codol_weapon_visuals_t *out)
{
    unsigned i; (void)name; if(!next()) return -1;
    memset(out,0,sizeof(*out));
    for(i=0;i<4;++i) {
        out->entries[i].offset=0x440+4*i; out->entries[i].kind=CODOL_WEAPON_DEP_ASSET;
        if(header[0x440+4*i]) {
            static const char *names[]={"shell0","shell1","shell2","shell3"};
            out->entries[i].name=names[i]; out->entries[i].asset=(codol_asset_t){30,header,1};
        }
    }
    if(shell_metadata==1) out->entries[0].offset=0;
    if(shell_metadata==2) out->entries[4]=out->entries[0];
    if(shell_metadata==3) out->entries[0].kind=CODOL_WEAPON_DEP_STRING;
    if(shell_metadata==4) out->entries[0].asset.type=5;
    if(shell_metadata==5) out->entries[0].name=NULL;
    return 1;
}
static int next(void) { return ++calls!=fail_at; }
int CODOL_LoadMountedWeapon(const char *name,codol_mounted_weapon_t *out)
{
    if(!strcmp(name,"missing")) return 0;
    if(!next()) return -1;
    memset(out,0,sizeof(*out)); out->asset=(codol_asset_t){28,header,sizeof(header)};
    out->strings[0]="weapon"; return 1;
}
int CODOL_LoadMountedWeaponAnimations(const char *name,codol_weapon_animations_t *out)
{
    (void)name; if(!next()) return -1; memset(out,0,sizeof(*out));
    out->names[3]="";
    if(!empty_animations) out->names[1]=out->names[143]="anim";
    return 1;
}
int CODOL_LoadEngineNativeXAnim(const char *name,const struct XAnimParts **out)
{
    assert(!strcmp(name,"anim")); if(!next()) return -1;
    if(animation_status==2) { *out=NULL; return 1; }
    if(animation_status!=1) return animation_status;
    *out=&native_animation; return 1;
}
/* Sound names resolve through the native alias provider; "last" is absent,
 * which must leave its slot null instead of failing the weapon. */
int CODOL_LoadMountedWeaponSounds(const char *name,codol_weapon_sounds_t *out)
{
    (void)name; memset(out,0,sizeof(*out));
    out->names[7]="fire"; out->names[16]="last"; out->arrays[0][3]="bounce";
    out->names[26]="reload"; out->names[46]="putaway"; out->names[9]="akimbo"; return 1;
}
int CODOL_LoadEngineNativeSound(const char *name,const snd_alias_list_t **out)
{
    if(!strcmp(name,"last")) return 0;
    if(!strcmp(name,"fire")) *out=&fire_alias;
    else if(!strcmp(name,"reload")) *out=&reload_alias;
    else if(!strcmp(name,"putaway")) *out=&putaway_alias;
    else if(!strcmp(name,"akimbo")) *out=&akimbo_alias;
    else if(!strcmp(name,"bounce")) *out=&bounce_alias;
    else { assert(!strcmp(name,"explode")); *out=&explosion_alias; }
    return 1;
}
int CODOL_LoadMountedWeaponAmmoNames(const char *name,codol_weapon_ammo_names_t *out)
{ (void)name; if(!next()) return -1; memset(out,0,sizeof(*out)); return 1; }
int CODOL_LoadMountedWeaponTail(const char *name,codol_weapon_tail_t *out)
{
    const unsigned offsets[]={0x9a0,0x9a4,0x9a8,0x9ac,0xbb4,0xbb8}; unsigned i;
    (void)name; if(!next()) return -1; memset(out,0,sizeof(*out)); out->count=6;
    for(i=0;i<6;++i) { out->entries[i].offset=offsets[i]; out->entries[i].kind=i<2 ? CODOL_WEAPON_DEP_STRING : CODOL_WEAPON_DEP_POINTS; }
    out->count=10;
    out->entries[6].offset=0xb78; out->entries[6].kind=CODOL_WEAPON_DEP_STRING; out->entries[6].name="gl_m4_mp";
    out->entries[7].offset=0xb88; out->entries[7].kind=CODOL_WEAPON_DEP_STRING;
    out->entries[8].offset=0x9fc; out->entries[8].kind=CODOL_WEAPON_DEP_STRING; out->entries[8].name="HINT_USE";
    out->entries[9].offset=0xa00; out->entries[9].kind=CODOL_WEAPON_DEP_STRING;
    out->count=11; out->entries[10].offset=0x7b0; out->entries[10].kind=CODOL_WEAPON_DEP_ASSET;
    if(header[0x7b0]) {
        out->entries[10].name="projectile";
        out->entries[10].asset=(codol_asset_t){4,header,1};
    }
    if(projectile_metadata==1) out->count=10;
    if(projectile_metadata==2) { out->entries[11]=out->entries[10]; out->count=12; }
    if(projectile_metadata==3) out->entries[10].kind=CODOL_WEAPON_DEP_STRING;
    if(projectile_metadata==4) out->entries[10].asset.type=5;
    if(projectile_metadata==5) out->entries[10].name=NULL;
    out->entries[out->count].offset=0xa24;
    out->entries[out->count].kind=CODOL_WEAPON_DEP_STRING;
    out->entries[out->count++].name="mods";
    out->entries[out->count].offset=0x7c0;
    out->entries[out->count].kind=CODOL_WEAPON_DEP_SOUND;
    out->entries[out->count++].name="explode";
    return 1;
}
int CODOL_LoadMountedWeaponModel(const char *name,unsigned slot,codol_weapon_model_t *out)
{
    (void)name; if(!next()) return -1;
    if(slot) return 0;
    memset(out,0,sizeof(*out)); out->name="model"; return 1;
}
int CODOL_LoadEnginePhysicsXModel(const char *name,const XModel **out)
{
    if(!next()) return -1;
    if(!strcmp(name,"projectile")) {
        *out=projectile_status==2 ? NULL : &native_projectile;
        return projectile_status==2 ? 1 : projectile_status;
    }
    assert(!strcmp(name,"model")); *out=&native_model; return 1;
}
int CODOL_LoadEngineWeaponHideTags(const char *name,const codol_weapon_hide_tag_handles_t **out)
{ (void)name; if(!next()) return -1; *out=&tags; return 1; }
int CODOL_LoadMountedWeaponEffects(const char *name,codol_weapon_effects_t *out)
{
    (void)name; if(!next()) return -1; memset(out,0,sizeof(*out));
    if(header[0x35c]) out->names[0]="view";
    if(header[0x360]) out->names[1]="world";
    if(effect_metadata==1) out->names[0]=NULL;
    if(effect_metadata==2) out->names[0]="";
    if(effect_metadata==3) out->names[0]="view";
    return 1;
}
int CODOL_LoadEngineNativeEffect(const char *name,const FxEffectDef **out)
{
    if(!next()) return -1;
    if(!strncmp(name,"shell",5)) {
        assert(name[5]>='0' && name[5]<='3');
        *out=effect_status==2 ? NULL : &shells[name[5]-'0'];
        return effect_status==2 ? 1 : effect_status;
    }
    assert(!strcmp(name,"view") || !strcmp(name,"world"));
    *out=effect_status==2 ? NULL : &flashes[!strcmp(name,"world")];
    return effect_status==2 ? 1 : effect_status;
}
int main(void)
{
    codol_native_weapon_core_t core={0},saved; unsigned total,i;
    header[0x10]=1;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
    assert(core.definition.handXModel==&native_model && !strcmp(core.definition.szAmmoName,"weapon"));
    assert(!strcmp(core.definition.szAltWeaponName,"gl_m4_mp") && !*core.partner_weapon_name);
    assert(!strcmp(core.script_mods,"mods"));
    assert(!strcmp(core.definition.szUseHintString,"HINT_USE") && !*core.definition.dropHintString);
    assert(core.source_models[0]==&native_model);
    assert(core.animation_parts[1]==&native_animation && core.animation_parts[143]==&native_animation);
    for(i=0;i<144;++i) if(i!=1 && i!=143) assert(!core.animation_parts[i]);
    assert(core.definition.fireSound==&fire_alias && !core.definition.fireSoundPlayer);
    assert(!core.definition.fireLastSound && !core.definition.pickupSound);
    assert(core.definition.bounceSound && core.definition.bounceSound[3]==&bounce_alias);
    assert(!core.definition.bounceSound[0] && core.definition.projExplosionSound==&explosion_alias);
    assert(!core.definition.projDudSound && !core.definition.projIgnitionSound);
    /* Slots 26 and 46 sit after the three interleaved CoDOL-only slots. */
    assert(core.definition.reloadSound==&reload_alias && !core.definition.reloadSoundPlayer);
    assert(core.definition.putawaySound==&putaway_alias && !core.definition.putawaySoundPlayer);
    assert(!core.definition.fireLoopSound && !core.definition.emptyFireSound);
    /* The CoDOL-only akimbo slot must not leak into a neighbouring field. */
    assert(core.definition.fireSoundPlayer!=&akimbo_alias && core.definition.fireLoopSound!=&akimbo_alias);
    total=calls; assert(total==21); saved=core;
    for(i=1;i<=total;++i) {
        calls=0; fail_at=i;
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1);
        assert(calls==i && !memcmp(&core,&saved,sizeof(core)));
    }
    calls=0; fail_at=0;
    assert(CODOL_LoadEngineWeaponCore("missing",&core)==0 && !calls && !memcmp(&core,&saved,sizeof(core)));
    assert(CODOL_LoadEngineWeaponCore(NULL,&core)==-1 && !calls);
    assert(CODOL_LoadEngineWeaponCore("",&core)==-1 && !calls);
    assert(CODOL_LoadEngineWeaponCore("weapon",NULL)==-1 && !calls);
    header[0x350]=6;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && calls==total);
    assert(core.definition.fireType==(weapFireType_t)6);
    saved=core; calls=0; header[0x350]=7;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && calls==total && !memcmp(&core,&saved,sizeof(core)));
    header[0x350]=0; calls=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && calls==total);
    saved=core;
    for(animation_status=0;animation_status<=2;animation_status+=2) {
        calls=0;
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && calls==17 && !memcmp(&core,&saved,sizeof(core)));
    }
    animation_status=1; empty_animations=1; calls=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && calls==19);
    for(i=0;i<144;++i) assert(!core.animation_parts[i]);
    header[0x7b0]=1; calls=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && calls==20);
    assert(core.definition.projectileModel==&native_projectile); saved=core;
    for(projectile_status=-1;projectile_status<=2;++projectile_status) {
        if(projectile_status==1) continue;
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    }
    projectile_status=1;
    for(projectile_metadata=1;projectile_metadata<=5;++projectile_metadata)
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    projectile_metadata=0; header[0x7b0]=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && !core.definition.projectileModel);
    header[0x35c]=header[0x360]=1;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
    assert(core.definition.viewFlashEffect==&flashes[0] && core.definition.worldFlashEffect==&flashes[1]);
    saved=core;
    calls=0; fail_at=20; /* World effect fails after the view has resolved. */
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1 && calls==21);
    assert(core.definition.viewFlashEffect==&flashes[0] && !core.definition.worldFlashEffect);
    assert(warning_calls==1);
    fail_at=0;
    for(effect_status=-1;effect_status<=2;++effect_status) if(effect_status!=1) {
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
        assert(!core.definition.viewFlashEffect && !core.definition.worldFlashEffect);
    }
    effect_status=1;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
    assert(core.definition.viewFlashEffect==&flashes[0] && core.definition.worldFlashEffect==&flashes[1]);
    saved=core;
    for(effect_metadata=1;effect_metadata<=2;++effect_metadata)
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    header[0x35c]=0; effect_metadata=3;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    effect_metadata=0; header[0x360]=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
    assert(!core.definition.viewFlashEffect && !core.definition.worldFlashEffect);
    for(i=0;i<4;++i) header[0x440+4*i]=1;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1); saved=core;
    assert(core.definition.viewShellEjectEffect==&shells[0] && core.definition.worldShellEjectEffect==&shells[1]);
    assert(core.definition.viewLastShotEjectEffect==&shells[2] && core.definition.worldLastShotEjectEffect==&shells[3]);
    for(shell_metadata=1;shell_metadata<=5;++shell_metadata)
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    shell_metadata=0;
    for(effect_status=-1;effect_status<=2;++effect_status) if(effect_status!=1)
        assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && !memcmp(&core,&saved,sizeof(core)));
    effect_status=1; calls=0; fail_at=23;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==-1 && calls==23 && !memcmp(&core,&saved,sizeof(core)));
    fail_at=0;
    for(i=0;i<4;++i) header[0x440+4*i]=0;
    assert(CODOL_LoadEngineWeaponCore("weapon",&core)==1);
    assert(!core.definition.viewShellEjectEffect && !core.definition.worldShellEjectEffect);
    assert(!core.definition.viewLastShotEjectEffect && !core.definition.worldLastShotEjectEffect);
    CODOL_FreeNativeWeaponCore(&core);
    {
        codol_weapon_registry_t *registry=CODOL_CreateWeaponRegistry(); int ammo,clip;
        assert(registry); calls=0; fail_at=2;
        assert(!CODOL_RegisterMountedWeaponKeys(registry,0,"weapon"));
        fail_at=0; header[0xbbc]=2;
        assert(!CODOL_RegisterMountedWeaponKeys(registry,0,"weapon"));
        header[0xbbc]=1; header[0x560]=1;
        assert(!CODOL_RegisterMountedWeaponKeys(registry,0,"mismatched_name"));
        assert(CODOL_RegisterMountedWeaponKeys(registry,0,"weapon"));
        assert(CODOL_GetWeaponKeys(registry,0,&ammo,&clip) && ammo==0 && clip==-1);
        CODOL_DestroyWeaponRegistry(registry);
    }
    puts("PASS: mounted weapon core orchestration, dependency failures and atomic replacement");
    return 0;
}
