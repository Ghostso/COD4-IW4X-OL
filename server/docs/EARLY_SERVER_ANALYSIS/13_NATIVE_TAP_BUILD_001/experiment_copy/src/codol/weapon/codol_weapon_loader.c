/* Native mounted weapon composition; no serialized pointers reach the engine. */
#include "codol_weapon_native.h"
#include "codol_xmodel_native.h"
#include "codol_xanim_native.h"
#include "codol_effects_native.h"
#include "codol_sound_native.h"
#include <string.h>
/* Resolve an adjusted asset name through its native provider. The old source
 * bytes may be absent after a rename, so the name and slot type are authoritative. */
static int load_image_effect(const char *name,const FxEffectDef **out)
{
    if(!name) { *out=NULL; return 1; }
    return *name && CODOL_LoadEngineNativeEffect(name,out)==1 && *out;
}
/* C1 WeaponDef +7b8 is the projectile explosion effect. The retained
 * G_ExplodeMissile keeps a persistent smoke entity only when kind 5 has one
 * (C1 52ef3b..52ef4f makes the same test), so leaving it null silently drops
 * smoke grenade persistence. Tabun is kind 5 with no effect, as in C1. A
 * missing effect degrades to null, like the muzzle flashes: it is cosmetic. */
static const FxEffectDef *load_explosion_effect(const char *weapon,const codol_weapon_tail_t *tail)
{
    const FxEffectDef *effect=NULL; unsigned i;
    for(i=0;i<tail->count;++i) {
        const codol_weapon_dependency_t *entry=tail->entries+i;
        if(entry->offset!=0x7b8 || entry->kind!=CODOL_WEAPON_DEP_ASSET || !entry->name || !*entry->name) continue;
        if(CODOL_LoadEngineNativeEffect(entry->name,&effect)!=1 || !effect) {
            Com_PrintWarning(CON_CHANNEL_SYSTEM,
                "CoDOL weapon %s: explosion effect '%s' did not resolve in any mounted zone (%s)\n",
                weapon ? weapon : "?",entry->name,CODOL_NativeEffectFailureDetail());
            effect=NULL;
        }
        break;
    }
    return effect;
}
int CODOL_LoadEngineWeaponCoreFromImage(const codol_weapon_source_image_t *image,
    codol_weapon_hide_tag_handles_t *owned_tags,codol_weapon_sound_bindings_t *owned_sounds,
    codol_native_weapon_core_t *out)
{
    codol_weapon_animations_t animations; codol_weapon_effects_t effects;
    codol_weapon_visuals_t visuals; codol_weapon_tail_t tail;
    codol_weapon_sounds_t sound_names; codol_weapon_hide_tags_t tag_names;
    codol_weapon_sound_bindings_t sounds; codol_weapon_hide_tag_handles_t tags={{0}};
    codol_native_weapon_core_t result={0};
    const XModel *models[11]={0},*projectile=NULL;
    const struct XAnimParts *parts[144]={0};
    const FxEffectDef *flashes[2]={0},*ejection[4]={0};
    unsigned i,j,projectile_slots=0;
    if(!image || !owned_tags || !owned_sounds || !out ||
       CODOL_WeaponSourceAnimations(image,&animations)!=1 ||
       CODOL_WeaponSourceEffects(image,&effects)!=1 ||
       CODOL_WeaponSourceVisuals(image,&visuals)!=1 ||
       CODOL_WeaponSourceTail(image,&tail)!=1 ||
       CODOL_WeaponSourceSounds(image,&sound_names)!=1 ||
       CODOL_WeaponSourceHideTags(image,&tag_names)!=1) return -1;
    for(i=0;i<11;++i) {
        codol_weapon_model_t model; int status=CODOL_WeaponSourceModel(image,i,&model);
        if(status<0 || (status==1 &&
           (CODOL_LoadEnginePhysicsXModel(model.name,models+i)!=1 || !models[i]))) return -1;
    }
    for(i=0;i<144;++i) if(animations.names[i] && *animations.names[i])
        if(CODOL_LoadEngineNativeXAnim(animations.names[i],parts+i)!=1 || !parts[i]) return -1;
    for(i=0;i<2;++i) if(!load_image_effect(effects.names[i],flashes+i)) return -1;
    for(i=0;i<tail.count;++i) if(tail.entries[i].offset==0x7b0) {
        const codol_weapon_dependency_t *entry=tail.entries+i;
        if(++projectile_slots!=1 || entry->kind!=CODOL_WEAPON_DEP_ASSET || entry->asset.type!=4) return -1;
        if(entry->name && (!*entry->name ||
           CODOL_LoadEnginePhysicsXModel(entry->name,&projectile)!=1 || !projectile)) return -1;
    }
    if(projectile_slots!=1) return -1;
    for(i=0;i<4;++i) {
        const codol_weapon_dependency_t *entry=NULL;
        for(j=0;j<14;++j) if(visuals.entries[j].offset==0x440+4*i) {
            if(entry) return -1;
            entry=visuals.entries+j;
        }
        if(!entry || entry->kind!=CODOL_WEAPON_DEP_ASSET || entry->asset.type!=30 ||
           !load_image_effect(entry->name,ejection+i)) return -1;
    }
    if(CODOL_BuildNativeWeaponSoundBindings(&sound_names,&tail,&sounds)!=1 ||
       CODOL_AcquireEngineWeaponHideTags(&tag_names,&tags)!=1) return -1;
    if(!CODOL_BuildNativeWeaponCoreFromImage(image,models,&tags,&result) ||
       !CODOL_ApplyNativeWeaponSounds(&sounds,&result.definition)) {
        CODOL_FreeNativeWeaponCore(&result);
        CODOL_ReleaseEngineWeaponHideTags(&tags); return -1;
    }
    result.definition.projectileModel=(XModel *)projectile;
    result.definition.projExplosionEffect=(struct FxEffectDef *)load_explosion_effect(NULL,&tail);
    result.definition.viewFlashEffect=(FxEffectDef *)flashes[0];
    result.definition.worldFlashEffect=(FxEffectDef *)flashes[1];
    result.definition.viewShellEjectEffect=(FxEffectDef *)ejection[0];
    result.definition.worldShellEjectEffect=(FxEffectDef *)ejection[1];
    result.definition.viewLastShotEjectEffect=(FxEffectDef *)ejection[2];
    result.definition.worldLastShotEjectEffect=(FxEffectDef *)ejection[3];
    memcpy(result.animation_parts,parts,sizeof(parts));
    /* No pointer into the temporary bindings may escape. */
    if(result.definition.bounceSound) result.definition.bounceSound=owned_sounds->arrays[0];
    CODOL_FreeNativeWeaponCore(out);
    CODOL_ReleaseEngineWeaponHideTags(owned_tags);
    *owned_tags=tags; *owned_sounds=sounds; *out=result; return 1;
}
int CODOL_RegisterMountedWeaponKeys(codol_weapon_registry_t *registry,unsigned wire,const char *name)
{
    codol_mounted_weapon_t source; codol_weapon_ammo_names_t names;
    if(!registry || !name || !*name || name[0]=='*' ||
       CODOL_LoadMountedWeapon(name,&source)!=1 || !source.asset.data || source.asset.size<0xbfc ||
       !source.strings[0] || strcmp(name,source.strings[0]) ||
       CODOL_LoadMountedWeaponAmmoNames(name,&names)!=1) return 0;
    return CODOL_RegisterWeaponKeys(registry,wire,name,names.ammo,names.clip,
        source.asset.data[0xbbc],source.asset.data[0x560],-1);
}

static int load_projectile_model(const codol_mounted_weapon_t *source,
    const codol_weapon_tail_t *tail,const XModel **out)
{
    const codol_weapon_dependency_t *entry=NULL;
    const uint8_t *p; unsigned i; int present;
    if(!source->asset.data || source->asset.size<0xbfc || tail->count>64) return 0;
    for(i=0;i<tail->count;++i) if(tail->entries[i].offset==0x7b0) {
        if(entry) return 0;
        entry=tail->entries+i;
    }
    if(!entry || entry->kind!=CODOL_WEAPON_DEP_ASSET) return 0;
    p=source->asset.data+0x7b0; present=!!(p[0]|p[1]|p[2]|p[3]);
    if(!present) return !entry->name && !entry->asset.data && !entry->asset.size;
    if(!entry->name || !*entry->name || entry->asset.type!=4 ||
       !entry->asset.data || !entry->asset.size) return 0;
    /* alpha0022/docs/projectiles_fix.md: C1 missile renderer 443c0f
     * reads def+7b0. Retained G_RegisterWeapon uses projectileModel +584. */
    return CODOL_LoadEnginePhysicsXModel(entry->name,out)==1 && *out;
}

/* Last failure site of CODOL_LoadEngineWeaponCore, for the engine error path.
 * A pure module: no console output, only a retrievable reason. */
static int core_fail_line;
static int core_fail(int line) { core_fail_line=line; return -1; }
int CODOL_EngineWeaponCoreFailureLine(void) { return core_fail_line; }
int CODOL_LoadEngineWeaponCore(const char *name,codol_native_weapon_core_t *out)
{
    CODOL_ResetNativeWeaponCoreFailure();
    codol_mounted_weapon_t source;
    codol_weapon_animations_t animations;
    codol_weapon_ammo_names_t ammo;
    codol_weapon_tail_t tail;
    const codol_weapon_hide_tag_handles_t *tags=NULL;
    const XModel *models[11]={0}; unsigned i; int status;
    const XModel *projectile=NULL;
    codol_weapon_effects_t effects;
    const FxEffectDef *flashes[2]={0};
    codol_weapon_visuals_t visuals;
    const FxEffectDef *ejection[4]={0};
    codol_weapon_sounds_t sound_names;
    const codol_weapon_sound_bindings_t *sounds=NULL;
    const struct XAnimParts *parts[144]={0};
    if(!name || !*name || !out) return core_fail(__LINE__);
    status=CODOL_LoadMountedWeapon(name,&source); if(status!=1) return status<0 ? core_fail(__LINE__) : status;
    if(CODOL_LoadMountedWeaponAnimations(name,&animations)!=1 ||
       CODOL_LoadMountedWeaponAmmoNames(name,&ammo)!=1 ||
       CODOL_LoadMountedWeaponTail(name,&tail)!=1) return core_fail(__LINE__);
    for(i=0;i<11;++i) {
        codol_weapon_model_t model;
        status=CODOL_LoadMountedWeaponModel(name,i,&model);
        if(status<0) return core_fail(__LINE__);
        if(status==1 && CODOL_LoadEnginePhysicsXModel(model.name,&models[i])!=1) return core_fail(__LINE__);
    }
    for(i=0;i<144;++i) if(animations.names[i] && *animations.names[i]) {
        if(CODOL_LoadEngineNativeXAnim(animations.names[i],&parts[i])!=1 || !parts[i]) return core_fail(__LINE__);
    }
    /* Animation-name slot 7 is the melee (knife) viewmodel xanim, slot 8 the
     * melee charge. docs/CODOL_MELEE_ANIM_20260920.md proves the slot from the
     * shipped weaponattach records -- three of them write a literally *_melee
     * name to def+0x098. C1's name getter 0x45c500 returns def[0x7c+4*index]
     * raw and substitutes nothing, so an empty slot plays no animation, while
     * def+0x590 still lets the weapon melee and deal damage.
     *
     * MEASURED 2026-09-20: 22 of the 40 weapons the zm roster hands out ship
     * with that slot empty, among them coltanaconda_zm (".44 Magnum") and
     * m14ebr_zm -- the reported bug. It is a gap in the shipped definitions,
     * and the server has no channel to close it: no zone a zm match mounts
     * carries a weaponattach asset, so C1's composed-name override path is
     * unavailable. Name it once per weapon rather than leaving it to be
     * rediscovered from a player report, for the same reason d6b75caa names
     * the unresolvable muzzle flash below. */
    if(source.asset.size>=0xbfc) {
        const uint8_t *melee=source.asset.data+0x590;
        unsigned damage=(unsigned)melee[0]|(unsigned)melee[1]<<8|
                        (unsigned)melee[2]<<16|(unsigned)melee[3]<<24;
        if(damage && damage<=0x7fffffffu && (!animations.names[7] || !*animations.names[7]))
            Com_PrintWarning(CON_CHANNEL_SYSTEM,
                "CoDOL weapon %s: melee damage %u but animation slot 7 is empty; "
                "C1 plays no melee animation for it (shipped definition gap)\n",
                name,damage);
    }
    if(CODOL_LoadEngineWeaponHideTags(name,&tags)!=1) return core_fail(__LINE__);
    if(!load_projectile_model(&source,&tail,&projectile)) return core_fail(__LINE__);
    if(CODOL_LoadMountedWeaponEffects(name,&effects)!=1) return core_fail(__LINE__);
    for(i=0;i<2;++i) {
        const uint8_t *p=source.asset.data+0x35c+4*i;
        int present=!!(p[0]|p[1]|p[2]|p[3]);
        if(present!=!!effects.names[i] || (effects.names[i] && !*effects.names[i])) return core_fail(__LINE__);
        /* An unresolvable muzzle flash DEGRADES; it does not kill the server.
         * MEASURED 2026-09-20: the first zm boot to publish a full 131-slot
         * weapon window died here on m1911_zm -- "invalid or unsupported
         * data", with a line number and nothing else to go on.
         *
         * NULL is already a legal value for both of these fields: it is what
         * they hold when the definition declares no flash at all (the
         * `present` test above), and they are assigned straight into
         * definition.viewFlashEffect / worldFlashEffect. It also matches how
         * the rest of this server treats a missing dependency -- an absent
         * xmodel becomes 'void', an absent xanim becomes the null animation,
         * both with a warning -- and it matches C1, which does not refuse to
         * start a map over a cosmetic effect.
         *
         * The warning NAMES the weapon and the effect, because the bare line
         * number cost a boot cycle to interpret. If the named effect turns
         * out to ship in a mounted zone after all, that is a resolver bug
         * rather than missing content, and this is what will reveal it. */
        if(present && (CODOL_LoadEngineNativeEffect(effects.names[i],&flashes[i])!=1 || !flashes[i])) {
            Com_PrintWarning(CON_CHANNEL_SYSTEM,
                "CoDOL weapon %s: %s muzzle flash '%s' did not resolve in any mounted zone (%s); "
                "loading the weapon without it\n",
                name, i ? "world" : "view", effects.names[i],CODOL_NativeEffectFailureDetail());
            flashes[i]=NULL;
        }
    }
    if(CODOL_LoadMountedWeaponVisuals(name,&visuals)!=1) return core_fail(__LINE__);
    for(i=0;i<4;++i) {
        const codol_weapon_dependency_t *entry=NULL; unsigned j;
        const uint8_t *p=source.asset.data+0x440+4*i;
        int present=!!(p[0]|p[1]|p[2]|p[3]);
        for(j=0;j<14;++j) if(visuals.entries[j].offset==0x440+4*i) {
            if(entry) return core_fail(__LINE__);
            entry=visuals.entries+j;
        }
        if(!entry || entry->kind!=CODOL_WEAPON_DEP_ASSET) return core_fail(__LINE__);
        if(!present) {
            if(entry->name || entry->asset.data || entry->asset.size) return core_fail(__LINE__);
        } else if(!entry->name || !*entry->name || entry->asset.type!=30 ||
            !entry->asset.data || !entry->asset.size ||
            CODOL_LoadEngineNativeEffect(entry->name,&ejection[i])!=1 || !ejection[i]) return core_fail(__LINE__);
    }
    /* Every sound name the definition carries becomes a native alias list
     * before the core is replaced. Names no mounted archive defines stay null;
     * a malformed alias, curve or loaded sound fails the whole weapon. */
    if(CODOL_LoadMountedWeaponSounds(name,&sound_names)!=1) return core_fail(__LINE__);
    if(CODOL_LoadEngineWeaponSounds(name,&sound_names,&tail,&sounds)!=1 || !sounds) return core_fail(__LINE__);
    if(!CODOL_BuildNativeWeaponCore(&source,models,&animations,&ammo,&tail,tags,out)) return core_fail(__LINE__);
    out->definition.projectileModel=(XModel *)projectile;
    out->definition.projExplosionEffect=(struct FxEffectDef *)load_explosion_effect(name,&tail);
    /* C1 leading dependency slots +35c/+360 are view/world muzzle flashes.
     * All dependency loads finish before replacing the caller's core. */
    out->definition.viewFlashEffect=(FxEffectDef *)flashes[0];
    out->definition.worldFlashEffect=(FxEffectDef *)flashes[1];
    /* C1 brass selection 4819d0..481a08: last-shot pair then ordinary pair,
     * each selected by the local-view predicate, matching IW3 brass code. */
    out->definition.viewShellEjectEffect=(FxEffectDef *)ejection[0];
    out->definition.worldShellEjectEffect=(FxEffectDef *)ejection[1];
    out->definition.viewLastShotEjectEffect=(FxEffectDef *)ejection[2];
    out->definition.worldLastShotEjectEffect=(FxEffectDef *)ejection[3];
    /* Established slot roles only; the bindings keep the CoDOL-only akimbo,
     * loop-end and rolling-surface sounds for later gameplay work. */
    if(!CODOL_ApplyNativeWeaponSounds(sounds,&out->definition)) {
        CODOL_FreeNativeWeaponCore(out); return core_fail(__LINE__);
    }
    memcpy(out->animation_parts,parts,sizeof(parts)); return 1;
}
