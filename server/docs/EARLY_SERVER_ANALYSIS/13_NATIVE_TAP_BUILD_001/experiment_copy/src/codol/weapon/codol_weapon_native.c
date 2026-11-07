#include "codol_weapon_native.h"
#include "codol_weapon_attachment.h"
#include <stddef.h>
/* Retained loader writes ADS reciprocals at7f8/7fc; Bullet_Fire reads
 * damage ranges808/80c. Arrays of pointers to accuracy-graph pairs contain
 * two pointers each, not four floats; preserve that distinction in ABI work. */
_Static_assert(offsetof(struct WeaponDef,fOOPosAnimLength)==0x7f8,"native ADS rate offsets");
_Static_assert(offsetof(struct WeaponDef,fMaxDamageRange)==0x808,"native maximum damage range offset");
_Static_assert(offsetof(struct WeaponDef,fMinDamageRange)==0x80c,"native minimum damage range offset");
_Static_assert(offsetof(struct WeaponDef,playerAnimType)==0x128,"native body animation type offset");
#include <string.h>
#include <limits.h>
#include <math.h>
#include <stdlib.h>
static uint32_t null_weapon_word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int CODOL_BuildNativeNullWeapon(const codol_mounted_weapon_t *source,const codol_weapon_animations_t *animations,
    const codol_weapon_ammo_names_t *ammo,const codol_weapon_tail_t *tail,codol_native_weapon_core_t *out)
{
    static const unsigned allowed[]={0,4,8,12,0x564,0x56c,0x57c,0x678,0x9a0,0x9a4,0x9a8,0x9ac,0x9b0,
        0x9fc,0xa00,0xa20,0xa24,0xaa0,0xaa4,0xacc,0xb78,0xb84,0xb88,0xbb0,0xbb4,0xbb8};
    const XModel *models[11]={0}; codol_weapon_hide_tag_handles_t tags={{0}}; unsigned o,i;
    if(!source || !animations || !ammo || !tail || !out || source->asset.type!=28 ||
       !source->asset.data || source->asset.size<0xbfc || !source->strings[0] || strcmp(source->strings[0],"none")) return 0;
    for(i=1;i<4;++i) if(source->strings[i] && *source->strings[i]) return 0;
    for(i=0;i<144;++i) if(animations->names[i] && *animations->names[i]) return 0;
    if((ammo->ammo && *ammo->ammo) || (ammo->clip && *ammo->clip) || (ammo->shared_cap && *ammo->shared_cap)) return 0;
    if(!null_weapon_word(source->asset.data) || null_weapon_word(source->asset.data+0x678)!=0x3fe00000 ||
       null_weapon_word(source->asset.data+0x9b0)!=null_weapon_word(source->asset.data+0xbb0) || tail->count>64) return 0;
    /* All remaining source fields must be zero. Pointers permitted here are
     * resolved and validated below, never copied into the native definition. */
    for(o=0;o<0xbfc;o+=4) {
        if(o>=0x7c && o<0x2bc) continue;
        for(i=0;i<sizeof(allowed)/sizeof(*allowed);++i) if(o==allowed[i]) break;
        if(i==sizeof(allowed)/sizeof(*allowed) && null_weapon_word(source->asset.data+o)) return 0;
    }
    for(i=0;i<tail->count;++i) {
        const codol_weapon_dependency_t *e=tail->entries+i;
        if(e->kind==CODOL_WEAPON_DEP_POINTS) {
            unsigned shift=(e->offset==0x9ac || e->offset==0xbb8) ? 16 : 0;
            if(e->offset!=0x9a8 && e->offset!=0x9ac && e->offset!=0xbb4 && e->offset!=0xbb8) return 0;
            if(e->point_count!=((null_weapon_word(source->asset.data+0xbb0)>>shift)&65535)) return 0;
        } else if(e->offset==0x9a0 || e->offset==0x9a4) {
            if(e->kind!=CODOL_WEAPON_DEP_STRING || !e->name || strcmp(e->name,"noweapon.accu")) return 0;
        } else if((e->name && *e->name) || e->asset.data || e->points || e->point_count) return 0;
    }
    if(!CODOL_BuildNativeWeaponCore(source,models,animations,ammo,tail,&tags,out)) return 0;
    /* Retained BG_LoadDefaultWeaponDef_LoadObj initializes every string field
     * to empty, then sets name, accuracy graphs and sprint scale (1.75). */
    for(i=0;i<33;++i) out->definition.szXAnims[i]="";
    out->definition.szDisplayName=out->definition.szOverlayName=out->definition.szModeName="";
    out->definition.szAmmoName=out->definition.szClipName=out->definition.szSharedAmmoCapName="";
    out->definition.szAltWeaponName=out->definition.szUseHintString=out->definition.dropHintString="";
    out->definition.szScript=out->definition.fireRumble=out->definition.meleeImpactRumble="";
    return 1;
}
void CODOL_FreeNativeWeaponCore(codol_native_weapon_core_t *out)
{
    if(!out) return;
    CODOL_FreeNativeWeaponGraphs(&out->graphs);
    memset(out,0,sizeof(*out));
}
/* First failure site of the current core build; reset by the engine loader. */
static int wn_fail_line;
static int wn_fail(int line) { if(!wn_fail_line) wn_fail_line=line; return 0; }
int CODOL_NativeWeaponCoreFailureLine(void) { return wn_fail_line; }
void CODOL_ResetNativeWeaponCoreFailure(void) { wn_fail_line=0; }
static int bind_weapon_registration_strings(const codol_weapon_tail_t *tail,codol_native_weapon_core_t *out)
{
    static const unsigned offsets[]={0xb78,0xb88,0x9fc,0xa00,0xa24};
    const codol_weapon_dependency_t *entries[5]={0}; const char *names[5]; unsigned i,j;
    if(tail->count>64) return wn_fail(__LINE__);
    /* alpha0022/alt_weapons.py: C1 registrar 0x41f4b0 resolves +b78;
     * 0x41f510 separately resolves +b88. Serialized indices +b7c/+b8c
     * belong to the client registry and must never become native indices. */
    for(i=0;i<tail->count;++i) {
        const codol_weapon_dependency_t *entry=tail->entries+i;
        for(j=0;j<5;++j) if(entry->offset==offsets[j]) {
            if(entries[j]) return wn_fail(__LINE__);
            entries[j]=entry;
        }
    }
    for(i=0;i<5;++i) {
        if(!entries[i] || entries[i]->kind!=CODOL_WEAPON_DEP_STRING) return wn_fail(__LINE__);
        names[i]=entries[i]->name ? entries[i]->name : "";
    }
    /* Retained BG_GetWeaponIndexForName dereferences szAltWeaponName[0].
     * A resolved null string denotes no companion, so provide an empty string. */
    out->definition.szAltWeaponName=names[0]; out->partner_weapon_name=names[1];
    /* C1 G_RegisterWeapon 0x529abf/0x529aee reads +9fc/+a00, then
     * registers hints into +a04/+a08. Native G_RegisterWeapon has the same
     * string dereferences at +7dc/+7e0. Hint indices are runtime-owned. */
    out->definition.szUseHintString=names[2]; out->definition.dropHintString=names[3];
    /* C1 535c10 identifies itself through the GetWeaponScriptMods error at
     * c55b80. Its successful path reads +a24 at 535c88 and calls Scr_AddString.
     * Preserve this CoDOL extension separately from the native script field. */
    out->script_mods=names[4];
    return 1;
}
/* C1 G_SpawnTurret gets its WeaponDef from the weapon-index table at
 * 57e9aa..57e9bf and retains it in [esp+c]. The fallback reads establish
 * these fields directly, without assuming equal IW3/C1 structure offsets:
 * right 57ec0a (+9bc), left 57ec78 (+9b8), top 57ed79 (+9c0),
 * bottom 57ede6 (+9c4), yaw 57ee76 (+9e8), pitch 57eeef (+9e4),
 * range 57efd6 (+9f0). Spawn applies signs/clamps and squares the range;
 * the definition must keep the original values so map overrides still work.
 * C1 57b8e0 resolves the same weapon table (57b935); 57b95a/57b979 clamp
 * pitch rate by max+9dc then min+9d4, and 57b99a/57b9b9 clamp yaw by
 * max+9e0 then min+9d8. Spawn reads aiSpread+9cc at57f03f and
 * playerSpread+9d0 at57f11c. suppressionTime's named spawn fallback reads
 * +9ec at57ef61, then converts seconds to milliseconds for the turret.
 * Keep definition times in seconds and preserve rate bounds even if inverted;
 * the measured convergence consumer applies max then min in that order. */
static int apply_weapon_turret_spawn_values(const codol_mounted_weapon_t *source,
    struct WeaponDef *out)
{
    static const unsigned offsets[]={0x9b8,0x9bc,0x9c0,0x9c4,0x9e4,0x9e8,0x9f0,
        0x9cc,0x9d0,0x9d4,0x9d8,0x9dc,0x9e0,0x9ec};
    float values[sizeof(offsets)/sizeof(*offsets)]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data ||
       source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<sizeof(offsets)/sizeof(*offsets);++i) {
        uint32_t bits=null_weapon_word(source->asset.data+offsets[i]);
        memcpy(values+i,&bits,sizeof(bits));
        if(!isfinite(values[i])) return wn_fail(__LINE__);
    }
    out->leftArc=values[0]; out->rightArc=values[1];
    out->topArc=values[2]; out->bottomArc=values[3];
    out->pitchConvergenceTime=values[4]; out->yawConvergenceTime=values[5];
    out->maxRange=values[6];
    out->aiSpread=values[7]; out->playerSpread=values[8];
    out->minTurnSpeed[0]=values[9]; out->minTurnSpeed[1]=values[10];
    out->maxTurnSpeed[0]=values[11]; out->maxTurnSpeed[1]=values[12];
    out->suppressTime=values[13];
    return 1;
}

static int apply_weapon_turret_heat_values(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 57b1f0 reads rates/penalty; 41dd80 reads spin durations;
     * 57b050 reads enable. All offsets use the resolved WeaponDef base. */
    static const unsigned offsets[]={0xab8,0xabc,0xac0,0xad4,0xad8};
    float values[5]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<5;++i) {
        uint32_t bits=null_weapon_word(source->asset.data+offsets[i]);
        memcpy(values+i,&bits,sizeof(bits));
        if(!isfinite(values[i])) return wn_fail(__LINE__);
    }
    if(source->asset.data[0xbe8]>1) return wn_fail(__LINE__);
    out->turretOverheatUpRate=values[0];
    out->turretOverheatDownRate=values[1];
    out->turretOverheatPenalty=values[2];
    out->turretBarrelSpinUpTime=values[3];
    out->turretBarrelSpinDownTime=values[4];
    out->turretBarrelSpinEnabled=source->asset.data[0xbe8];
    return 1;
}
static int apply_weapon_turret_sweep_values(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 57b639/57b73a read the peak rate, 57b6d0/57b59d the acceleration and
     * 57b583 the per-leg delay, all from the resolved WeaponDef base. The
     * delay is an integer millisecond count added to level.time, so it is not
     * read as a float. */
    static const unsigned offsets[]={0xa14,0xa18};
    float values[2]; uint32_t delay; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<2;++i) {
        uint32_t bits=null_weapon_word(source->asset.data+offsets[i]);
        memcpy(values+i,&bits,sizeof(bits));
        if(!isfinite(values[i]) || values[i]<0.0f) return wn_fail(__LINE__);
    }
    delay=null_weapon_word(source->asset.data+0xa1c);
    out->turretSweepRate=values[0];
    out->turretSweepAccel=values[1];
    /* The producer adds this signed word directly; no 60-second cap was
     * measured. Preserve its bits rather than rejecting valid definitions. */
    memcpy(&out->turretSweepDelay,&delay,sizeof(delay));
    return 1;
}
static void bind_resolved_weapon_models(const XModel *const models[11],struct WeaponDef *out);
static int build_weapon_core(const codol_mounted_weapon_t *source,const XModel *const models[11],
    const codol_weapon_animations_t *animations,const codol_weapon_ammo_names_t *ammo,
    const codol_weapon_tail_t *tail,const codol_weapon_hide_tag_handles_t *tags,
    int serialized_presence,codol_native_weapon_core_t *out)
{
    codol_native_weapon_core_t result={0}; struct WeaponDef *d=&result.definition; unsigned i;
    if(!source || !models || !animations || !ammo || !tail || !tags || !out ||
       source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc ||
       !source->strings[0] || !*source->strings[0] || source->asset.data[0xbc2]>1) return wn_fail(__LINE__);
    result.inherits_perks=source->asset.data[0xbc2];
    /* C1 405f25..405f32 selects the view/offhand WeaponDef and reads +33c
     * into the playerAnimType condition. 405f78..405fc9 repeats that lookup
     * for the held weapon's primary condition. These are indices in mounted
     * mp/playeranimtypes.txt, not the weapon-class enum. The parser condition
     * is a 64-bit set; do not permit a definition to index past that storage.
     * Preserve the index so newly authored named types remain representable. */
    {
        uint32_t animation_type=null_weapon_word(source->asset.data+0x33c);
        if(animation_type>=64)return wn_fail(__LINE__);
        d->playerAnimType=(int)animation_type;
    }
    result.source_weapon_class=(unsigned)source->asset.data[0x344] |
        (unsigned)source->asset.data[0x345]<<8 |
        (unsigned)source->asset.data[0x346]<<16 |
        (unsigned)source->asset.data[0x347]<<24;
    if(result.source_weapon_class>=12)return wn_fail(__LINE__);
    result.bomb.type=null_weapon_word(source->asset.data+0x340);
    result.bomb.guidance=null_weapon_word(source->asset.data+0x8e0);
    memcpy(&result.bomb.lifetime,source->asset.data+0x7a4,4);
    memcpy(&result.bomb.acceleration,source->asset.data+0x7a8,4);
    memcpy(&result.bomb.curvature,source->asset.data+0x7ac,4);
    memcpy(&result.bomb.destabilization,source->asset.data+0xa40,4);
    memcpy(&result.bomb.destabilization_distance,source->asset.data+0xa48,4);
    if(result.bomb.type>4 || result.bomb.guidance>4 || !isfinite(result.bomb.lifetime) ||
       !isfinite(result.bomb.acceleration) || !isfinite(result.bomb.curvature) ||
       !isfinite(result.bomb.destabilization))return wn_fail(__LINE__);
    if(source->asset.data[0xbbd]>1)return wn_fail(__LINE__);
    result.lock_warning_gate=source->asset.data[0xbbd];
    /* C1 0x419d51 tests this byte before enabling the second weapon hand. */
    if(source->asset.data[0xbd5]>1)return wn_fail(__LINE__);
    result.dual_wield=source->asset.data[0xbd5];
    result.riot_shield=(result.bomb.type==3);
    if(source->asset.data[0xbca]>1)return wn_fail(__LINE__);
    result.ads_reload=source->asset.data[0xbca];
    if(source->asset.data[0xbc7]>1)return wn_fail(__LINE__);
    result.dual_mag=source->asset.data[0xbc7];
    /* C1 reads these two beside the weapon type, at 0x41b207 and 0x41ae09. */
    if(source->asset.data[0xbe0]>1 || source->asset.data[0xbe4]>1)return wn_fail(__LINE__);
    result.detonate_trigger=source->asset.data[0xbe0];
    result.hold_pin=source->asset.data[0xbe4];
    result.requires_ground=source->asset.data[0xbe5];
    result.offhand_cancel=source->asset.data[0xbec]!=0;
    result.unlimited_ammo=source->asset.data[0x560]!=0;
    result.silenced=source->asset.data[0xbda];
    /* Script-only flags (see the core definition). Stored as booleans: the
     * C1 queries push the raw byte, and every shipped asset writes 0 or 1. */
    result.thermal_scope=source->asset.data[0xbe6]!=0;
    result.hpbt=source->asset.data[0xbf3]!=0;
    result.gps=source->asset.data[0xbf4]!=0;
    result.id_lock=source->asset.data[0xbf5]!=0;
    /* Raw bits, like C1's own fld: a zero FOV ends the zoom cycle there. */
    memcpy(result.zoom_fov,source->asset.data+0x944,sizeof result.zoom_fov);
    for(i=0;serialized_presence && i<32;++i) {
        const uint8_t *p=source->asset.data+0x3c+2*i;
        if(!!(p[0]|p[1])!=!!tags->tags[i]) return wn_fail(__LINE__);
    }
    /* alpha0022/docs/weapon_fix.md identifies displayName at +8, not +4.
     * The default weapon's +8 contains WEAPON_DEFAULTWEAPON. Preserve the
     * remaining source strings without assuming IW3 overlay/mode roles. */
    d->szInternalName=source->strings[0]; d->szDisplayName=source->strings[2];
    if(!bind_weapon_registration_strings(tail,&result) ||
       (serialized_presence && !CODOL_BindNativeWeaponModels(source,models,d)) ||
       !CODOL_ApplyNativeWeaponAnimationNames(animations,d) ||
       !CODOL_ApplyNativeWeaponAmmoNames(ammo,source->strings[0],d) ||
       !CODOL_ApplyNativeWeaponTimings(source,d,&result.timings) ||
       !CODOL_ApplyNativeWeaponAmmo(source,d) || !CODOL_ApplyNativeWeaponMelee(source,d) ||
       !CODOL_ApplyNativeWeaponFuse(source,d) ||
       !CODOL_ApplyNativeWeaponProjectile(source,d) ||
       !CODOL_ReadMissileStickiness(source,&result.missile_stickiness) ||
       !CODOL_ReadNativeWeaponBounce(source,&result.bounce) ||
       !CODOL_ApplyNativeWeaponDamage(source,d) || !CODOL_ApplyNativeWeaponLocationDamage(source,d,&result.shield_damage_multiplier) ||
       !CODOL_ApplyNativeWeaponFireMode(source,d) || !CODOL_ApplyNativeWeaponLockRequirement(source,d) || !CODOL_ApplyNativeWeaponRecoil(source,d) ||
       !CODOL_ApplyNativeWeaponAds(source,d) || !CODOL_ApplyNativeWeaponMovement(source,d) ||
       !CODOL_ApplyNativeWeaponSpread(source,d) || !CODOL_ApplyNativeWeaponType(source,d) ||
       !CODOL_ApplyNativeWeaponClass(source,d) || !CODOL_ApplyNativeWeaponCombatClasses(source,d) ||
       !apply_weapon_turret_spawn_values(source,d) ||
       !apply_weapon_turret_heat_values(source,d) ||
       !apply_weapon_turret_sweep_values(source,d) ||
       !CODOL_BindNativeWeaponGraphs(tail,d,&result.graphs)) {
        CODOL_FreeNativeWeaponCore(&result); return wn_fail(__LINE__);
    }
    if(!serialized_presence) bind_resolved_weapon_models(models,d);
    result.animations=*animations; result.hide_tags=*tags;
    memcpy(result.source_models,models,sizeof(result.source_models));
    memcpy(result.source_strings,source->strings,sizeof(result.source_strings));
    CODOL_FreeNativeWeaponCore(out); *out=result; return 1;
}
int CODOL_BuildNativeWeaponCore(const codol_mounted_weapon_t *source,const XModel *const models[11],
    const codol_weapon_animations_t *animations,const codol_weapon_ammo_names_t *ammo,
    const codol_weapon_tail_t *tail,const codol_weapon_hide_tag_handles_t *tags,codol_native_weapon_core_t *out)
{
    return build_weapon_core(source,models,animations,ammo,tail,tags,1,out);
}
int CODOL_BuildNativeWeaponCoreFromImage(const codol_weapon_source_image_t *image,
    const XModel *const models[11],const codol_weapon_hide_tag_handles_t *tags,
    codol_native_weapon_core_t *out)
{
    codol_mounted_weapon_t source; codol_weapon_animations_t animations;
    codol_weapon_ammo_names_t ammo; codol_weapon_tail_t tail;
    codol_weapon_hide_tags_t names; unsigned i;
    if(!image || !models || !tags || !out ||
       CODOL_WeaponSourceView(image,&source)!=1 ||
       CODOL_WeaponSourceAnimations(image,&animations)!=1 ||
       CODOL_WeaponSourceAmmoNames(image,&ammo)!=1 ||
       CODOL_WeaponSourceTail(image,&tail)!=1 ||
       CODOL_WeaponSourceHideTags(image,&names)!=1) return wn_fail(__LINE__);
    /* Attachment names and appended tags do not rewrite zone-local pointer
     * words/indices. Validate presence against their resolved image slots. */
    for(i=0;i<11;++i) {
        codol_weapon_model_t model; int status=CODOL_WeaponSourceModel(image,i,&model);
        if(status<0 || (status==1)!=!!models[i]) return wn_fail(__LINE__);
    }
    for(i=0;i<32;++i) if(!!names.names[i]!=!!tags->tags[i]) return wn_fail(__LINE__);
    return build_weapon_core(&source,models,&animations,&ammo,&tail,tags,0,out);
}
void CODOL_FreeNativeWeaponGraphs(codol_native_weapon_graphs_t *owner)
{
    unsigned i;
    if(!owner) return;
    for(i=0;i<4;++i) free(owner->points[i]);
    memset(owner,0,sizeof(*owner));
}
int CODOL_ApplyNativeWeaponLockRequirement(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    unsigned value;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc)return wn_fail(__LINE__);
    value=source->asset.data[0xbbe];if(value>1)return wn_fail(__LINE__);
    out->requireLockonToFire=(int)value;return 1;
}
int CODOL_ApplyNativeWeaponType(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 type table at 0xcd727c: bullet, grenade, projectile, riotshield,
     * bomb. IW4 reused IW3's value 3 (binoculars, the retained non-firing
     * weapon type) for the riot shield, so that slot is the native
     * equivalent. "bomb" has no IW3 type; the placed/thrown explosive path
     * (grenade) is the nearest native behaviour and is not a measured
     * equivalent. */
    static const weapType_t types[]={WEAPTYPE_BULLET,WEAPTYPE_GRENADE,WEAPTYPE_PROJECTILE,
        WEAPTYPE_BINOCULARS,WEAPTYPE_GRENADE};
    static const weapInventoryType_t inventories[]={WEAPINVENTORY_PRIMARY,WEAPINVENTORY_OFFHAND,
        WEAPINVENTORY_ITEM,WEAPINVENTORY_ALTMODE
#ifdef CODOL_SERVER
        ,WEAPINVENTORY_EXCLUSIVE,WEAPINVENTORY_SCAVENGER
#endif
    };
    unsigned i; uint32_t values[2]; const unsigned offsets[]={0x340,0x34c};
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 script readers 0x541b43/0x541c33 index the semantic string tables
     * at 0xcd727c/0xcd7f58. CoDOL adds exclusive/scavenger inventory
     * categories; preserve them rather than coercing either to primary. */
    for(i=0;i<2;++i) {
        const uint8_t *p=source->asset.data+offsets[i];
        values[i]=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    }
    if(values[0]>=sizeof(types)/sizeof(*types) || values[1]>=sizeof(inventories)/sizeof(*inventories)) return wn_fail(__LINE__);
    out->weapType=types[values[0]]; out->inventoryType=inventories[values[1]]; return 1;
}
int CODOL_ApplyNativeWeaponClass(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 0x541ba3 reads +344; 0x541ba9 indexes the class-name table at
     * 0xcd7f28. Sniper and throwingknife have no corresponding IW3 class. */
    /* The C1 class table is rifle, sniper, mg, smg, spread, pistol, grenade,
     * rocketlauncher, turret, throwingknife, non_player, item. The retained
     * IW3 class set has no sniper or throwingknife: IW3 sniper rifles are
     * WEAPCLASS_RIFLE (bolt/ADS behaviour comes from the definition fields)
     * and the thrown knife is an offhand throwable, which IW3 drives through
     * WEAPCLASS_GRENADE. Those two are the nearest native classes, not
     * measured C1 equivalents; scripts keying on the class name see
     * "rifle"/"grenade" for them. */
    static const int classes[]={WEAPCLASS_RIFLE,WEAPCLASS_RIFLE,WEAPCLASS_MG,WEAPCLASS_SMG,
        WEAPCLASS_SPREAD,WEAPCLASS_PISTOL,WEAPCLASS_GRENADE,WEAPCLASS_ROCKETLAUNCHER,
        WEAPCLASS_TURRET,WEAPCLASS_GRENADE,WEAPCLASS_NON_PLAYER,WEAPCLASS_ITEM};
    const uint8_t *p; uint32_t value;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    p=source->asset.data+0x344;
    value=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    if(value>=sizeof(classes)/sizeof(*classes) || classes[value]<0) return wn_fail(__LINE__);
    out->weapClass=(weapClass_t)classes[value]; return 1;
}
int CODOL_ApplyNativeWeaponCombatClasses(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    static const PenetrateType penetration[]={PENETRATE_TYPE_NONE,PENETRATE_TYPE_SMALL,PENETRATE_TYPE_MEDIUM,PENETRATE_TYPE_LARGE};
    static const OffhandClass offhand[]={OFFHAND_CLASS_NONE,OFFHAND_CLASS_FRAG_GRENADE,
        OFFHAND_CLASS_SMOKE_GRENADE,OFFHAND_CLASS_FLASH_GRENADE,
        OFFHAND_CLASS_CODOL_FRAG_ALT,OFFHAND_CLASS_CODOL_EQUIPMENT};
    const unsigned offsets[]={0x348,0x354}; uint32_t values[2]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1's weapon byte +0xbc4 is bRifleBullet (verified against its named
     * weapon definitions). The retained Bullet_Fire reads this at native
     * WeaponDef +0x4e0 to select rifle versus pistol hit/kill MOD. Leaving
     * the field zero classified every native rifle and SMG hit as pistol. */
    if(source->asset.data[0xbc4]>1) return wn_fail(__LINE__);
    /* C1 penetration reader 0x507cf7 and name table 0xcd7f8c. Offhand
     * selection compares +354 at 0x421dca/0x421e20; class script-string
     * pointers at 0xcd49cc order none/frag/smoke/flash before extra roles. */
    for(i=0;i<2;++i) {
        const uint8_t *p=source->asset.data+offsets[i];
        values[i]=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        /* Penetration still has four values; the offhand class has six, and
         * rejecting the two new ones rejected the whole definition -- which
         * meant no weapon could ever occupy the third selected-offhand slot. */
        if(values[i]>=(i ? sizeof(offhand)/sizeof(*offhand)
                        : sizeof(penetration)/sizeof(*penetration))) return wn_fail(__LINE__);
    }
    out->penetrateType=penetration[values[0]];
    out->offhandClass=offhand[values[1]];
    out->bRifleBullet=source->asset.data[0xbc4];
    return 1;
}
int CODOL_BindNativeWeaponGraphs(const codol_weapon_tail_t *source,struct WeaponDef *out,codol_native_weapon_graphs_t *owner)
{
    static const unsigned offsets[]={0x9a0,0x9a4,0x9a8,0x9ac,0xbb4,0xbb8};
    const codol_weapon_dependency_t *entries[6]={0};
    codol_native_weapon_graphs_t result={0}; unsigned i,j,k;
    if(!source || !out || !owner || source->count>64) return wn_fail(__LINE__);
    for(i=0;i<source->count;++i) for(j=0;j<6;++j) if(source->entries[i].offset==offsets[j]) {
        if(entries[j]) return wn_fail(__LINE__);
        entries[j]=source->entries+i;
    }
    for(i=0;i<6;++i) if(!entries[i] || entries[i]->kind!=(i<2 ? CODOL_WEAPON_DEP_STRING : CODOL_WEAPON_DEP_POINTS)) return wn_fail(__LINE__);
    for(i=0;i<4;++i) {
        const codol_weapon_dependency_t *entry=entries[i+2];
        if(entry->point_count>65535 || (entry->point_count && !entry->points)) goto fail;
        if(!entry->point_count) continue;
        result.points[i]=malloc((size_t)entry->point_count*sizeof(*result.points[i]));
        if(!result.points[i]) goto fail;
        for(j=0;j<entry->point_count;++j) for(k=0;k<2;++k) {
            const uint8_t *p=entry->points+8*j+4*k;
            uint32_t bits=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
            float value; memcpy(&value,&bits,4); if(!isfinite(value)) goto fail;
            result.points[i][j][k]=value;
        }
    }
    for(i=0;i<2;++i) {
        out->accuracyGraphName[i]=entries[i]->name;
        out->accuracyGraphKnots[i]=result.points[i];
        out->originalAccuracyGraphKnots[i]=result.points[i+2];
        out->accuracyGraphKnotCount[i]=(int)entries[i+2]->point_count;
        out->originalAccuracyGraphKnotCount[i]=(int)entries[i+4]->point_count;
    }
    CODOL_FreeNativeWeaponGraphs(owner); *owner=result; return 1;
fail:
    CODOL_FreeNativeWeaponGraphs(&result); return wn_fail(__LINE__);
}
int CODOL_ApplyNativeWeaponMovement(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    float values[3]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 PM_CmdScale 0x41023f/0x410266 consumes +670/+674; max sprint
     * 0x40e9e6 consumes +678. Retained movement/footstep code uses native
     * +418/+41c, while BG_GetMaxSprintTime uses sprintDurationScale. */
    for(i=0;i<3;++i) {
        const uint8_t *p=source->asset.data+0x670+4*i;
        uint32_t word=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        memcpy(values+i,&word,4);
        if(!isfinite(values[i]) || values[i]<0) return wn_fail(__LINE__);
    }
    out->moveSpeedScale=values[0]; out->adsMoveSpeedScale=values[1]; out->sprintDurationScale=values[2];
    return 1;
}
int CODOL_ApplyNativeWeaponAds(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    float rates[2]; unsigned i,enabled,rechamber,fire_only;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 0x418798/0x4187af consume +a28/+a2c per millisecond. Retained
     * PM_UpdateAimDownSightLerp multiplies by +7f8/+7fc (fOOPosAnimLength).
     * C1 0x418655 gates ADS on +bc8; 0x4186e1 gates rechamber ADS on +bc9.
     * Do not round reciprocals into integer durations and recompute rates. */
    for(i=0;i<2;++i) {
        const uint8_t *p=source->asset.data+0xa28+4*i;
        uint32_t word=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        memcpy(rates+i,&word,4);
        if(!isfinite(rates[i]) || rates[i]<0) return wn_fail(__LINE__);
    }
    enabled=source->asset.data[0xbc8]; rechamber=source->asset.data[0xbc9];
    fire_only=source->asset.data[0xbcf];
    if(enabled>1 || rechamber>1 || fire_only>1) return wn_fail(__LINE__);
    memcpy(out->fOOPosAnimLength,rates,sizeof(rates));
    out->aimDownSight=(int)enabled; out->bRechamberWhileAds=(int)rechamber;
    /* C1 0x4186fb and 0x41b4c0 force ADS before an ADS-only shot. */
    out->adsFireOnly=(int)fire_only;
    return 1;
}
int CODOL_ApplyNativeWeaponFireMode(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    static const weapFireType_t modes[]={WEAPON_FIRETYPE_FULLAUTO,WEAPON_FIRETYPE_SINGLESHOT,
        WEAPON_FIRETYPE_BURSTFIRE2,WEAPON_FIRETYPE_BURSTFIRE3,WEAPON_FIRETYPE_BURSTFIRE4,
        (weapFireType_t)5,(weapFireType_t)6};
    const uint8_t *p; uint32_t mode; unsigned rechamber;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 quota dispatcher 0x41a9d0 / table 0x41aa4c: shared modes 0..4,
     * double-barrel 5 and spin-up 6. C1 0x418f89 gates rechamber on +bc6;
     * retained PM_Weapon tests native +4e8 (bBoltAction) for this role. */
    p=source->asset.data+0x350;
    mode=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    rechamber=source->asset.data[0xbc6];
    if(mode>=sizeof(modes)/sizeof(modes[0]) || rechamber>1) return wn_fail(__LINE__);
    out->fireType=modes[mode]; out->bBoltAction=(int)rechamber;
    return 1;
}
int CODOL_ApplyNativeWeaponRecoil(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    static const size_t fields[2][13]={
        {offsetof(struct WeaponDef,adsGunKickReducedKickPercent),offsetof(struct WeaponDef,fAdsGunKickPitchMin),
         offsetof(struct WeaponDef,fAdsGunKickPitchMax),offsetof(struct WeaponDef,fAdsGunKickYawMin),offsetof(struct WeaponDef,fAdsGunKickYawMax),
         offsetof(struct WeaponDef,fAdsGunKickAccel),offsetof(struct WeaponDef,fAdsGunKickSpeedMax),offsetof(struct WeaponDef,fAdsGunKickSpeedDecay),
         offsetof(struct WeaponDef,fAdsGunKickStaticDecay),offsetof(struct WeaponDef,fAdsViewKickPitchMin),offsetof(struct WeaponDef,fAdsViewKickPitchMax),
         offsetof(struct WeaponDef,fAdsViewKickYawMin),offsetof(struct WeaponDef,fAdsViewKickYawMax)},
        {offsetof(struct WeaponDef,hipGunKickReducedKickPercent),offsetof(struct WeaponDef,fHipGunKickPitchMin),
         offsetof(struct WeaponDef,fHipGunKickPitchMax),offsetof(struct WeaponDef,fHipGunKickYawMin),offsetof(struct WeaponDef,fHipGunKickYawMax),
         offsetof(struct WeaponDef,fHipGunKickAccel),offsetof(struct WeaponDef,fHipGunKickSpeedMax),offsetof(struct WeaponDef,fHipGunKickSpeedDecay),
         offsetof(struct WeaponDef,fHipGunKickStaticDecay),offsetof(struct WeaponDef,fHipViewKickPitchMin),offsetof(struct WeaponDef,fHipViewKickPitchMax),
         offsetof(struct WeaponDef,fHipViewKickYawMin),offsetof(struct WeaponDef,fHipViewKickYawMax)}
    };
    float values[2][13]; int counts[2]; unsigned mode,i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 counts 0x41b56d/0x41b588; percentages 0x4221ac/0x4221b4;
     * random angular ranges 0x422200..0x422403; interpolated gun dynamics
     * 0x4242f9..0x424355. Each mode starts with a count, then 13 floats. */
    for(mode=0;mode<2;++mode) {
        unsigned base=mode ? 0x958 : 0x900;
        uint32_t count=null_weapon_word(source->asset.data+base); if(count>INT_MAX) return wn_fail(__LINE__);
        counts[mode]=(int)count;
        for(i=0;i<13;++i) {
            uint32_t bits=null_weapon_word(source->asset.data+base+4+4*i);
            memcpy(&values[mode][i],&bits,4);
            if(!isfinite(values[mode][i]) || ((i==0 || (i>=5 && i<=8)) && values[mode][i]<0)) return wn_fail(__LINE__);
        }
    }
    out->adsGunKickReducedKickBullets=counts[0]; out->hipGunKickReducedKickBullets=counts[1];
    for(mode=0;mode<2;++mode) for(i=0;i<13;++i) memcpy((uint8_t *)out+fields[mode][i],&values[mode][i],4);
    return 1;
}
int CODOL_ApplyNativeWeaponLocationDamage(const codol_mounted_weapon_t *source,struct WeaponDef *out,float *shield_multiplier)
{
    float values[20]; unsigned i;
    if(!source || !out || !shield_multiplier || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 0x521035 reads def+a4c+4*hitLoc before the global multiplier.
     * hitLocName[20] at 0xcce0d0 is in the same interleaved limb order as
     * IW3 HITLOC_*, with shield appended at 19. Source +a9c is not part of it. */
    for(i=0;i<20;++i) {
        uint32_t bits=null_weapon_word(source->asset.data+0xa4c+4*i);
        memcpy(values+i,&bits,4);
        if(!isfinite(values[i]) || values[i]<0) return wn_fail(__LINE__);
    }
    memcpy(out->locationDamageMultipliers,values,sizeof(out->locationDamageMultipliers));
    *shield_multiplier=values[19]; return 1;
}
int CODOL_ApplyNativeWeaponDamage(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 0x505c40: +588/+a30 are the ordinary damage endpoints;
     * 0x505c91 selects +58c/+a34 for player damage. 0x505cfd..0x505d4c
     * compares distance with +a38/+a3c and interpolates between endpoints.
     * Equal/reversed ranges remain intact: the reader branches before its
     * division. Do not invent damage, clamp endpoints or reorder distances. */
    static const struct { unsigned source; size_t target; } fields[]={
        {0x588,offsetof(struct WeaponDef,damage)},
        {0x58c,offsetof(struct WeaponDef,playerDamage)},
        {0xa30,offsetof(struct WeaponDef,minDamage)},
        {0xa34,offsetof(struct WeaponDef,minPlayerDamage)},
        {0xa38,offsetof(struct WeaponDef,fMaxDamageRange)},
        {0xa3c,offsetof(struct WeaponDef,fMinDamageRange)}
    };
    uint32_t values[6]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<6;++i) {
        const uint8_t *p=source->asset.data+fields[i].source;
        values[i]=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if(i<4) { if(values[i]>INT_MAX) return wn_fail(__LINE__); }
        else { float value; memcpy(&value,values+i,4); if(!isfinite(value) || value<0) return wn_fail(__LINE__); }
    }
    for(i=0;i<6;++i) memcpy((uint8_t *)out+fields[i].target,values+i,4);
    return 1;
}
int CODOL_ApplyNativeWeaponMelee(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 PM_Weapon_CheckForMelee 0x41c0f7 gates on +0x590.
     * PM_Weapon_MeleeInit 0x41bdb1..0x41bdd5 reads the charge and normal
     * duration/delay pairs. The attachment override branch is not flattened. */
    static const struct { unsigned source; size_t target; } fields[]={
        {0x590,offsetof(struct WeaponDef,iMeleeDamage)},
        {0x5a0,offsetof(struct WeaponDef,iMeleeDelay)},
        {0x5a4,offsetof(struct WeaponDef,meleeChargeDelay)},
        {0x5c0,offsetof(struct WeaponDef,iMeleeTime)},
        {0x5c4,offsetof(struct WeaponDef,meleeChargeTime)}
    };
    int values[5]; unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<5;++i) {
        const uint8_t *p=source->asset.data+fields[i].source;
        uint32_t value=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if(value>INT_MAX) return wn_fail(__LINE__);
        values[i]=(int)value;
    }
    for(i=0;i<5;++i) memcpy((uint8_t *)out+fields[i].target,values+i,sizeof(int));
    return 1;
}
int CODOL_ApplyNativeWeaponProjectile(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 573f10..573fb6 scales forward by +794, adds +798 vertically,
     * and +79c along normalized horizontal forward. Explosion caller
     * 52f13c..52f15b passes +778/+780/+784 to radial damage522950. */
    static const struct { unsigned source; size_t target; } fields[]={
        {0x794,offsetof(struct WeaponDef,iProjectileSpeed)},
        {0x798,offsetof(struct WeaponDef,iProjectileSpeedUp)},
        {0x79c,offsetof(struct WeaponDef,iProjectileSpeedForward)},
        {0x778,offsetof(struct WeaponDef,iExplosionRadius)},
        {0x780,offsetof(struct WeaponDef,iExplosionInnerDamage)},
        {0x784,offsetof(struct WeaponDef,iExplosionOuterDamage)}
    };
    uint32_t values[6],cone_bits,explosion_kind,radius_min; unsigned i; float cone,lifetime,acceleration_time;
    if(!source || !out || source->asset.type!=28 || !source->asset.data ||
       source->asset.size<0xbfc) return wn_fail(__LINE__);
    for(i=0;i<6;++i) values[i]=null_weapon_word(source->asset.data+fields[i].source);
    /* C1 52efea..52f030 reads degrees, then passes the cosine to radius
     * damage. Leaving this zero narrows an omnidirectional explosion. */
    cone_bits=null_weapon_word(source->asset.data+0x788);
    memcpy(&cone,&cone_bits,sizeof(cone));
    memcpy(&lifetime,source->asset.data+0x7a4,sizeof(lifetime));
    memcpy(&acceleration_time,source->asset.data+0x7a8,sizeof(acceleration_time));
    if(!isfinite(cone) || !isfinite(lifetime) || !isfinite(acceleration_time))
        return wn_fail(__LINE__);
    /* C1 52eeae..52eebc: byte bdc selects C5511c=(0,0,1) instead
     * of the impact trace normal. Retained explosion reads this named field. */
    if(source->asset.data[0xbdc]>1 || source->asset.data[0xbdd]>1)
        return wn_fail(__LINE__);
    /* C1 G_ExplodeMissile 52eed4 switches on +7b4 with the retained enum:
     * 0/6 grenade event73, 1 rocket76, 2 flashbang78 (then 52f169 calls
     * the flash blast 522870 with +778/+77c), anything else custom79; 52ef3b
     * keeps a persistent smoke entity for 5 when +7b8 is set. Measured
     * common_gametype_mp: flash 2, smoke/tabun 5, concussion/emp 3, frag/
     * semtex/white phosphorus 0. Left zero, every offhand exploded as a frag.
     * C1 adds kind 7 (zombies crossbow/sniper explosive); no C1 reader tests
     * for it, so it takes the custom-event arm there and in every retained
     * equality test here. Store it unchanged rather than folding it into 3. */
    explosion_kind=null_weapon_word(source->asset.data+0x7b4);
    radius_min=null_weapon_word(source->asset.data+0x77c);
    if(explosion_kind>WEAPPROJEXP_NUM || radius_min>INT_MAX) return wn_fail(__LINE__);
    for(i=0;i<6;++i) memcpy((uint8_t *)out+fields[i].target,values+i,4);
    /* C1 rocket launch53169b multiplies +7a4 seconds by -1000 and
     * subtracts the result from level.time, then caps nextthink at +60000.
     * Retained G_FireRocket uses projLifetime for the same deadline. Leaving
     * it zero makes the missile expire before a remote camera can render.
     * C1 531749 also selects accelerated launch from +7a8, corresponding
     * to the retained timeToAccelerate branch; preserve its native value. */
    out->projLifetime=lifetime;
    out->timeToAccelerate=acceleration_time;
    out->damageConeAngle=cone;
    out->projExplosionEffectForceNormalUp=source->asset.data[0xbdc];
    out->projExplosion=(weapProjExposion_t)explosion_kind;
    out->iExplosionRadiusMin=(int)radius_min;
    /* The C1 packed tail has verified rolling/force-normal/stick-to-player
     * anchors at bdb/bdc/bde. The intervening impact-explode boolean follows
     * the named IW4 schema, independently checked against loaded C1 assets:
     * remote missile/RPG/M79=1, frag/semtex/throwing knife=0. This is a schema
     * binding, not a claim to have recovered C1's impact instruction. Native
     * MissileImpact requires this field before applying radial damage. */
    out->bProjImpactExplode=source->asset.data[0xbdd];
    /* C1 rocket spawn 530e9d reads the guidance kind at +0x8e0 (the javelin
     * branch there tests 3). It was never converted, so every C1 launcher
     * reached the retained MissileTrajectory with guidance NONE and no
     * missile could home, whatever its lock or Missile_SetTargetEnt said.
     * Measured values (codol_checkweapon, 2026-09-24) match the IW4 enum the
     * retained code uses: rpg_mp 0, stinger_mp/at4_mp/tow_turret_mp 1
     * (sidewinder), javelin_mp 3. A kind the retained enum has no branch for
     * stays NONE rather than entering a guidance path it cannot run. */
    {
        uint32_t guided;
        memcpy(&guided,source->asset.data+0x8e0,sizeof(guided));
        out->guidedMissileType=guided<MISSILE_GUIDANCE_COUNT ?
            (guidedMissileType_t)guided : MISSILE_GUIDANCE_NONE;
    }
    return 1;
}
int CODOL_ReadNativeWeaponBounce(const codol_mounted_weapon_t *source,codol_weapon_bounce_t *out)
{
    codol_weapon_bounce_t result;
    unsigned i;
    if(!source || !out || source->asset.type!=28 || !source->asset.data ||
       source->asset.size<0xbfc) return wn_fail(__LINE__);
    if(source->asset.data[0xbdb]>1) return wn_fail(__LINE__);
    result.rolling=source->asset.data[0xbdb];
    /* C1 52e942..52e967 interpolates +7d4 (parallel) and +850
     * (perpendicular). The 0x7c-byte interval is 31 floats; keep surface IDs
     * intact, including 29/30, rather than indexing retained 29-entry data. */
    for(i=0;i<CODOL_WEAPON_BOUNCE_SURFACES;++i) {
        uint32_t p=null_weapon_word(source->asset.data+0x7d4+4*i);
        uint32_t q=null_weapon_word(source->asset.data+0x850+4*i);
        memcpy(result.parallel+i,&p,4);
        memcpy(result.perpendicular+i,&q,4);
        if(!isfinite(result.parallel[i]) || !isfinite(result.perpendicular[i]))
            return wn_fail(__LINE__);
    }
    *out=result;
    return 1;
}
int CODOL_ApplyNativeWeaponFuse(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    uint32_t value;
    unsigned timed,cook;
    if(!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 offhand hold entry 0x41c520 seeds the grenade timer: 0x41c55b reads
     * def+0x654 and 0x41c561 writes ps+0x34; 0x41cca0 counts it down for
     * cook-off weapons. Shipped milliseconds: frag 3500, flash 1500, smoke
     * 1000, matching the reference's measured fuse table. */
    value=null_weapon_word(source->asset.data+0x654);
    /* C1 stores these as bytes, unlike the retained int fields. Validate
     * both before changing any output so malformed assets remain atomic. */
    timed=source->asset.data[0xbe2];
    cook=source->asset.data[0xbcc];
    if(value>INT_MAX || timed>1 || cook>1) return wn_fail(__LINE__);
    /* 53094b..53098c selects held ps+34 versus supplied fuse from +be2.
     * Retained G_FireGrenade/BounceMissile consume timedDetonation for that
     * same fuse ownership and persistence. 41ccff..41cd0e decrements held
     * ps+34 only for +bcc, the cookOffHold behavior. */
    out->fuseTime=(int)value;
    out->timedDetonation=(int)timed;
    out->bCookOffHold=(int)cook;
    return 1;
}
int CODOL_ApplyNativeWeaponSoundNames(const codol_weapon_sounds_t *sounds,
    const codol_weapon_tail_t *tail,codol_native_weapon_sounds_t *out)
{
    /* Slot roles measured in the shipped definitions: slot 0 pickup
     * ("weap_pickup"/"grenade_pickup"), slot 2 ammo pickup, slot 4 projectile,
     * slot 5 pull-back, slots 7/8 the fire pair consumed by C1 0x481d60.
     * C1 script readers 0x558d90/0x558df0 read +364/+368 respectively,
     * dereference the string records and return their names. Together with
     * the shipped pickup strings and paired slot layout this identifies
     * slot 1 as the player pickup variant; playback is not asserted here.
     * Tail +0x7c0 carries the explosion sound ("flashbang_explode_default"),
     * with +0x7c4 the dud sound and +0x8f0 the ignition sound. */
    const codol_weapon_dependency_t *entry=NULL;
    codol_native_weapon_sounds_t result={0}; unsigned i;
    if(!sounds || !tail || !out || tail->count>64) return wn_fail(__LINE__);
    for(i=0;i<tail->count;++i) if(tail->entries[i].offset==0x7c0) {
        if(entry) return wn_fail(__LINE__);
        entry=tail->entries+i;
    }
    if(!entry || entry->kind!=CODOL_WEAPON_DEP_SOUND) return wn_fail(__LINE__);
    result.pickup=sounds->names[0] && *sounds->names[0] ? sounds->names[0] : NULL;
    result.pickup_player=sounds->names[1] && *sounds->names[1] ? sounds->names[1] : NULL;
    result.proj_explosion=entry->name && *entry->name ? entry->name : NULL;
    *out=result; return 1;
}
int CODOL_ApplyNativeWeaponAnimationNames(const codol_weapon_animations_t *source,struct WeaponDef *out)
{
    /* C1 dispatcher 0x47be58 maps animation IDs to NAME slots based at +0x7c.
     * Roles follow the measured state transitions in alpha0022 weapon_fsm.py.
     * Native slots come from IW3 weaponDefFields, szXAnims at +0x50.
     * CoDOL alternate/dual/dive names remain in the complete source view. */
    static const unsigned char slots[][2]={
        {1,1},{2,2},             /* idle, empty idle */
        {3,3},{4,4},{5,5},       /* fire, hold fire, last shot */
        {34,28},{35,29},         /* ADS fire and ADS last shot */
        {6,6},{36,30},           /* hip and ADS rechamber */
        {7,7},{8,8},             /* melee and melee charge; C1 0x47b9dd/0x47b9f0 */
        {9,9},{11,10},{14,12},   /* reload, empty reload, reload end */
        {13,11},{16,14},{19,16}, /* reload start, first raise, alternate raise */
        {31,25},                /* detonate: anim 32 -> slot 31 at 0x47bc1a */
        {18,15},{15,13},{20,17}, /* drop, raise, alternate drop */
        {22,19},{21,18},         /* quick drop, quick raise */
        {24,21},{23,20},         /* empty drop, empty raise */
        {25,22},{26,23},{27,24}  /* sprint in, loop, out */
    };
    unsigned i;
    if (!source || !out) return wn_fail(__LINE__);
    for (i=0;i<sizeof(slots)/sizeof(slots[0]);++i)
        out->szXAnims[slots[i][1]]=source->names[slots[i][0]];
    return 1;
}
int CODOL_ApplyNativeWeaponSpread(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    static const size_t targets[]={
        offsetof(struct WeaponDef,fHipSpreadStandMin),offsetof(struct WeaponDef,fHipSpreadDuckedMin),
        offsetof(struct WeaponDef,fHipSpreadProneMin),offsetof(struct WeaponDef,hipSpreadStandMax),
        offsetof(struct WeaponDef,hipSpreadDuckedMax),offsetof(struct WeaponDef,hipSpreadProneMax),
        offsetof(struct WeaponDef,fHipSpreadDecayRate),offsetof(struct WeaponDef,fHipSpreadFireAdd),
        offsetof(struct WeaponDef,fHipSpreadTurnAdd),offsetof(struct WeaponDef,fHipSpreadMoveAdd),
        offsetof(struct WeaponDef,fHipSpreadDuckedDecay),offsetof(struct WeaponDef,fHipSpreadProneDecay),
        offsetof(struct WeaponDef,fAdsSpread)
    };
    float values[13]; unsigned i;
    if (!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    /* C1 BG_CalcSpread 0x422660 and spread integration 0x418b90; the
     * reference docs/ballistics.md records the individual consumer offsets. */
    for (i=0;i<13;++i) {
        const uint8_t *p=source->asset.data+(i<12 ? 0x6b8+4*i : 0x940);
        uint32_t bits=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        memcpy(values+i,&bits,4);
        if (!isfinite(values[i]) || values[i]<0) return wn_fail(__LINE__);
    }
    for (i=0;i<13;++i) memcpy((uint8_t *)out+targets[i],values+i,4);
    return 1;
}
int CODOL_BindNativeWeaponModels(const codol_mounted_weapon_t *source,const XModel *const models[11],struct WeaponDef *out)
{
    unsigned i;
    if (!source || !models || !out || source->asset.type!=28 ||
        !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for (i=0;i<11;++i) {
        const uint8_t *p=source->asset.data+0x10+4*i;
        uint32_t ref=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if (!!ref!=!!models[i]) return wn_fail(__LINE__);
    }
    bind_resolved_weapon_models(models,out); return 1;
}
int CODOL_BindNativeComposedWeaponModels(const XModel *world,const XModel *view,
    codol_native_weapon_core_t *out)
{
    unsigned i;
    if(!world || !view || !out)return wn_fail(__LINE__);
    /* The composed name's flag selected these models before this call. The
     * retained IW3 giver still indexes a 16-entry array with its variant
     * argument, while C1 has already baked that choice into the definition.
     * Publish the selected pair in every representable legacy slot. */
    for(i=0;i<16;++i) {
        out->definition.gunXModel[i]=(XModel *)view;
        out->definition.worldModel[i]=(XModel *)world;
    }
    return 1;
}
static void bind_resolved_weapon_models(const XModel *const models[11],struct WeaponDef *out)
{
    unsigned i;
    /* C1 hand fallback 0x47d268; indexed view read 0x47c994; indexed world
     * reads 0x45c90b/0x5357db. G_RegisterWeapon 0x529b1d..0x529b78
     * iterates TWO world models; +24/+30/+38 are registered separately.
     * Replay's eleven consecutive pointers are not one world-model array. */
    out->handXModel=(XModel *)models[0];
    memset(out->gunXModel,0,sizeof(out->gunXModel));
    memset(out->worldModel,0,sizeof(out->worldModel));
    for (i=0;i<2;++i) out->gunXModel[i]=(XModel *)models[1+i];
    for (i=0;i<2;++i) out->worldModel[i]=(XModel *)models[3+i];
    /* alpha0022/docs/weapon_fix.md's measured model roles: +24 magazine,
     * +2c view knife, +30 world knife. Additional references stay in core. */
    out->worldClipModel=(XModel *)models[5];
    out->knifeModel=(XModel *)models[7];
    out->worldKnifeModel=(XModel *)models[8];
}
int CODOL_ApplyNativeWeaponAmmoNames(const codol_weapon_ammo_names_t *source,const char *internal_name,struct WeaponDef *out)
{
    if(!source || !internal_name || !*internal_name || !out) return wn_fail(__LINE__);
    out->szAmmoName=source->ammo && *source->ammo ? source->ammo : internal_name;
    out->szClipName=source->clip && *source->clip ? source->clip : internal_name;
    /* C1 0x41f310 compares +0x57c, leaving the shared-cap index -1 for an
     * empty name. Registration itself remains the engine's responsibility. */
    out->szSharedAmmoCapName=source->shared_cap ? source->shared_cap : "";
    return 1;
}
int CODOL_ApplyNativeWeaponAmmo(const codol_mounted_weapon_t *source,struct WeaponDef *out)
{
    /* C1 max-ammo consumer 0x41e017, reload capacity 0x41e55f and shot
     * loop 0x47f32e. All 127 definitions matched to the reference's measured
     * weapon_ammo_table agree with these three offsets. */
    /* C1 PM_ReloadClip 0x41e4f0 selects +764 for ordinary reloads and
     * +768 for start phases. IW3 PM_ReloadClip uses +534/+538 respectively.
     * Zero and caps >= clip size have distinct engine handling; preserve them. */
    /* Starting ammo is read at C1 0x50ffb3/0x5100d7 and exposed to scripts
     * at 0x541cc3. It is a definition value, not maxAmmo minus clip size. */
    /* C1 BG_GetMaxAmmo 0x41dfb0/0x41e040 reads the shared pool's +584.
     * +580 is a runtime index assigned by 0x41f310, never an asset value to
     * import. Its +bcd clip-only branch (0x41dfbc/0x41e085) matches the
     * retained BG_GetMaxPickupableAmmo native bClipOnly branch at +500. */
    static const unsigned offsets[]={0x55c,0x574,0xb60,0x578,0x764,0x768,0x584};
    int values[7]; unsigned i,segmented,clip_only,no_partial;
    if (!source || !out || source->asset.type!=28 || !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for (i=0;i<7;++i) {
        const uint8_t *p=source->asset.data+offsets[i];
        uint32_t value=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if (value>INT_MAX) return wn_fail(__LINE__);
        values[i]=(int)value;
    }
    /* C1 0x4195de tests +bd8 before selecting reload-start duration/state. */
    segmented=source->asset.data[0xbd8];
    clip_only=source->asset.data[0xbcd];
    /* C1 0x41a17d: +bd7 gates partial reloads. +764 limits the transfer;
     * zero/whole-clip caps require an empty clip, smaller caps require room
     * for that transfer. Retained PM_Weapon_CheckForReload_90 uses +52c
     * (bNoPartialReload) with native +534 (iReloadAmmoAdd) identically. */
    no_partial=source->asset.data[0xbd7];
    if(segmented>1 || clip_only>1 || no_partial>1) return wn_fail(__LINE__);
    out->iStartAmmo=values[0]; out->iMaxAmmo=values[1]; out->iClipSize=values[2]; out->shotCount=values[3];
    out->iReloadAmmoAdd=values[4]; out->iReloadStartAdd=values[5];
    out->iSharedAmmoCap=values[6]; out->bClipOnly=(int)clip_only;
    out->bSegmentedReload=(int)segmented;
    out->bNoPartialReload=(int)no_partial;
    return 1;
}
int CODOL_ApplyNativeWeaponTimings(const codol_mounted_weapon_t *source,struct WeaponDef *out,
    codol_weapon_timing_extensions_t *extensions)
{
    /* C1 0x4190af/ba/c9 (rechamber), 0x419361/3a3/3ee/42a (reload),
     * and the change/end phases documented in alpha0022 weapon_fsm.py. */
    static const struct { unsigned source; size_t target; } fields[]={
        {0xb68,offsetof(struct WeaponDef,iFireTime)}, /* C1 fire phase, 0x41b573. */
        /* alpha0022 harvest_firetime.py records these consumers directly. */
        {0x59c,offsetof(struct WeaponDef,iFireDelay)}, /* 0x41b4c0, also offhand 0x41c683. */
        {0x5a8,offsetof(struct WeaponDef,iDetonateDelay)}, /* 0x41c44f. */
        {0x5b8,offsetof(struct WeaponDef,iHoldFireTime)}, /* 0x41b41e. */
        {0x5bc,offsetof(struct WeaponDef,iDetonateTime)}, /* 0x41c43d. */
        /* docs/ads_simulation.md: source durations for the rate producer at
         * 0x41ea90. Keep serialized rates independently; do not invert them. */
        {0x950,offsetof(struct WeaponDef,iAdsTransInTime)},
        {0x954,offsetof(struct WeaponDef,iAdsTransOutTime)},
        /* C1 PM_UpdateAimDownSightLerp 0x41869c/0x4186d1 subtracts this
         * transition tail from weaponTime while deciding whether reload may
         * retain ADS. */
        {0x9b4,offsetof(struct WeaponDef,iPositionReloadTransTime)},
        {0x5ac,offsetof(struct WeaponDef,iRechamberTime)},
        {0x5b4,offsetof(struct WeaponDef,iRechamberBoltTime)},
        {0x5c8,offsetof(struct WeaponDef,iReloadTime)},
        {0x5d4,offsetof(struct WeaponDef,iReloadEmptyTime)},
        {0x5dc,offsetof(struct WeaponDef,iReloadAddTime)}, /* C1 0x419242 */
        {0x5ec,offsetof(struct WeaponDef,iReloadStartTime)}, /* C1 0x4195f9 */
        {0x5f0,offsetof(struct WeaponDef,iReloadStartAddTime)}, /* C1 0x41925c */
        {0x5f4,offsetof(struct WeaponDef,iReloadEndTime)},
        {0x5f8,offsetof(struct WeaponDef,iDropTime)},
        {0x5fc,offsetof(struct WeaponDef,iRaiseTime)},
        {0x600,offsetof(struct WeaponDef,iAltDropTime)},
        /* C1 PM_FinishWeaponChange alternate raise, 0x419e09: the new weapon's
         * +b80 (after altWeaponIndex +b7c, as in IW4's WeaponCompleteDef).
         * Shipped gl_*_mp defs carry 699 ms (gl_ak47_mp 300); unmapped, the
         * retained PM_Weapon_1140 raise read 0 and cut the alternate raise. */
        {0xb80,offsetof(struct WeaponDef,iAltRaiseTime)},
        {0x604,offsetof(struct WeaponDef,quickDropTime)},
        {0x608,offsetof(struct WeaponDef,quickRaiseTime)},
        /* C1 419e9f uses ba0 for ordinary first raise. 60c is the
         * flag80000/attachment17 override, not the ordinary duration:
         * m9_mp stores 250 here versus 3000 at60c. */
        {0xba0,offsetof(struct WeaponDef,iFirstRaiseTime)},
        {0x610,offsetof(struct WeaponDef,iEmptyRaiseTime)},
        {0x614,offsetof(struct WeaponDef,iEmptyDropTime)},
        {0x618,offsetof(struct WeaponDef,sprintInTime)}, /* C1 0x41d0aa. */
        {0x620,offsetof(struct WeaponDef,sprintOutTime)} /* C1 0x41d162/0x41d1ad. */
    };
    /* C1's sprint loop writes a zero timer at 0x41d106; do not infer +61c.
     * Dive entry/exit use +630/+638 (0x41d22a/0x41d2da), not IW3 night vision. */
    static const unsigned extra_offsets[]={0x5b0,0x5cc,0x5d8,0x5e0,0x5e4,0x5e8,0x630,0x638,
        0xb3c,0xb40}; /* Spin-up charge and decay durations; see the header. */
    int values[sizeof(fields)/sizeof(fields[0])],extras[sizeof(extra_offsets)/sizeof(extra_offsets[0])]; unsigned i;
    if (!source || !out || !extensions || source->asset.type!=28 ||
        !source->asset.data || source->asset.size<0xbfc) return wn_fail(__LINE__);
    for (i=0;i<sizeof(fields)/sizeof(fields[0])+sizeof(extra_offsets)/sizeof(extra_offsets[0]);++i) {
        unsigned offset=i<sizeof(fields)/sizeof(fields[0]) ? fields[i].source : extra_offsets[i-sizeof(fields)/sizeof(fields[0])];
        const uint8_t *p=source->asset.data+offset;
        uint32_t value=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
        if (value>INT_MAX) return wn_fail(__LINE__);
        if (i<sizeof(fields)/sizeof(fields[0])) values[i]=(int)value;
        else extras[i-sizeof(fields)/sizeof(fields[0])]=(int)value;
    }
    for (i=0;i<sizeof(fields)/sizeof(fields[0]);++i)
        memcpy((uint8_t *)out+fields[i].target,values+i,sizeof(int));
    *extensions=(codol_weapon_timing_extensions_t){extras[0],extras[1],extras[2],extras[3],
        extras[4],extras[5],extras[6],extras[7],extras[8],extras[9]};
    return 1;
}
