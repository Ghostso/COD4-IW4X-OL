/* Native engine ownership for converted model bone strings. */
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "cscr_stringlist.h"
#include "codol_xmodel.h"
#include "codol_xmodel_native.h"
#include "codol_xanim_native.h"
#include "codol_stream_model.h"
#include "codol_collision.h"
#include "codol_effects_native.h"
#include "codol_collision_native.h"
#include "codol_physics_native.h"
#include "filesystem.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static codol_native_clip_map_t installed_clip;
static codol_collision_map_t installed_source;
int CODOL_TriggerClipHandle(unsigned index)
{
    return index<installed_clip.trigger_model_count ? (int)(installed_clip.trigger_model_base+index) : -1;
}

void CODOL_ShutdownEngineClipMap(void)
{
    CODOL_FreeNativeClipMap(&installed_clip);
    CODOL_FreeCollisionMap(&installed_source);
}

static int load_stream_model(void *context,const char *name,codol_stream_model_t *out)
{
    char path[MAX_QPATH]; void *data=NULL; int length,status;
    (void)context;
    /* Streamed surface assets are basenames under models/, as in C1 0x4c9f20. */
    if (!name || !*name || strchr(name,'/') || strchr(name,'\\') || strchr(name,':') ||
        !strcmp(name,".") || !strcmp(name,"..") || strlen(name)+8>sizeof(path)) return -1;
    snprintf(path,sizeof(path),"models/%s",name);
    length=FS_ReadFile(path,&data);
    if (length<0) return 0;
    status=CODOL_ReadStreamModel(data,(size_t)length,out) ? 1 : -1;
    if (data) FS_FreeFile(data);
    return status;
}
void CODOL_InitEngineStreamModels(void)
{
    CODOL_SetStreamModelLoader(load_stream_model,NULL);
}

static unsigned acquire_bone_string(void *context,const char *name)
{
    (void)context;
    return SL_GetString(name,0);
}
static void release_bone_string(void *context,unsigned handle)
{
    (void)context;
    SL_RemoveRefToString(handle);
}
int CODOL_EngineStringHandleIs(unsigned handle,const char *name)
{
    const char *text;
    if(!handle || handle>UINT16_MAX || !name) return 0;
    text=SL_ConvertToString(handle);
    return text && !strcmp(text,name);
}
int CODOL_LoadEngineModelBoneHandles(const char *name,const uint16_t **handles,unsigned *count)
{
    return CODOL_BindMountedModelBoneHandles(name,acquire_bone_string,release_bone_string,NULL,handles,count);
}
int CODOL_LoadEngineXAnimHandles(const char *name,const codol_xanim_handles_t **out)
{
    return CODOL_BindMountedXAnimHandles(name,acquire_bone_string,release_bone_string,NULL,out);
}
int CODOL_LoadEngineWeaponHideTags(const char *name,const codol_weapon_hide_tag_handles_t **out)
{
    return CODOL_BindMountedWeaponHideTags(name,acquire_bone_string,release_bone_string,NULL,out);
}
void CODOL_ReleaseEngineWeaponHideTags(codol_weapon_hide_tag_handles_t *owned)
{
    unsigned i;
    if(!owned) return;
    for(i=0;i<32;++i) if(owned->tags[i])
        release_bone_string(NULL,owned->tags[i]);
    memset(owned,0,sizeof(*owned));
}
int CODOL_AcquireEngineWeaponHideTags(const codol_weapon_hide_tags_t *source,
    codol_weapon_hide_tag_handles_t *out)
{
    codol_weapon_hide_tag_handles_t result={{0}}; unsigned i,handle;
    if(!source || !out) return -1;
    for(i=0;i<32;++i) if(source->names[i] && !*source->names[i]) return -1;
    for(i=0;i<32;++i) {
        if(!source->names[i]) continue;
        handle=acquire_bone_string(NULL,source->names[i]);
        if(!handle || handle>UINT16_MAX) {
            if(handle) release_bone_string(NULL,handle);
            CODOL_ReleaseEngineWeaponHideTags(&result); return -1;
        }
        result.tags[i]=(uint16_t)handle;
    }
    CODOL_ReleaseEngineWeaponHideTags(out);
    *out=result; return 1;
}
int CODOL_LoadEngineNativeXAnim(const char *name,const struct XAnimParts **out)
{
    return CODOL_LoadMountedNativeXAnim(name,acquire_bone_string,release_bone_string,NULL,out);
}
int CODOL_LoadNativeModelCore(const char *name,codol_native_model_core_t *out)
{
    const codol_mounted_model_skeleton_t *skeleton;
    const codol_mounted_model_geometry_t *geometry;
    const uint16_t *handles;
    unsigned count;
    int status;
    if (!out) return -1;
    status=CODOL_LoadMountedXModelSkeleton(name,&skeleton);
    if (status!=1) return status;
    status=CODOL_LoadMountedXModelGeometry(name,&geometry);
    if (status!=1) return status;
    status=CODOL_LoadEngineModelBoneHandles(name,&handles,&count);
    if (status!=1) return status;
    return CODOL_BuildNativeModelCore(skeleton,geometry,handles,count,out) ? 1 : -1;
}
int CODOL_LoadEngineCollisionXModel(const char *name,const XModel **out)
{
    return CODOL_LoadMountedCollisionXModel(name,acquire_bone_string,release_bone_string,NULL,out);
}
int CODOL_LoadEnginePhysicsXModel(const char *name,const XModel **out)
{
    return CODOL_LoadMountedPhysicsXModel(name,acquire_bone_string,release_bone_string,NULL,out);
}
static const XModel *load_effect_model(void *context,const char *name)
{
    const XModel *model;
    (void)context;
    return CODOL_LoadEnginePhysicsXModel(name,&model)==1 ? model : NULL;
}
int CODOL_LoadEngineNativeEffect(const char *name,const FxEffectDef **out)
{
    return CODOL_LoadMountedNativeEffect(name,load_effect_model,NULL,out);
}
static void *load_collision_model(void *context,const char *name)
{
    const XModel *model;
    int status;
    (void)context;
    status=CODOL_LoadEngineCollisionXModel(name,&model);
    if(status!=1) Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision model %s failed: %d\n",name,status);
    return status==1 ? (void *)model : NULL;
}
int CODOL_LoadEngineCollisionMap(const char *name,codol_collision_map_t *out)
{
    return CODOL_LoadMountedCollisionModels(name,load_collision_model,NULL,out);
}
int CODOL_BuildEngineClipMap(const char *name,const codol_collision_map_t *source,codol_native_clip_map_t *out)
{
    codol_dynamic_entities_t dynamic={0}; codol_dynamic_binding_t *bindings[2]={0};
    const codol_dynamic_binding_t *views[2]; unsigned category,i; int status,result=-1;
    if (!name || !source || !out) return -1;
    status=CODOL_LoadMountedDynamicEntities(name,&dynamic);
    if (status!=1) {
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: dynamic decode failed (%d)\n",name,status);
        return status;
    }
    for (category=0;category<2;++category) {
        if (dynamic.count[category]) {
            bindings[category]=calloc(dynamic.count[category],sizeof(*bindings[category]));
            if (!bindings[category]) goto done;
        }
        for (i=0;i<dynamic.count[category];++i) {
            const codol_dynamic_entity_t *entity=dynamic.entities[category]+i;
            codol_dynamic_binding_t *binding=bindings[category]+i;
            codol_dynamic_dependency_t dependency;
            memset(&dependency,0,sizeof(dependency));
            if (entity->model_reference) {
                const XModel *model;
                if (CODOL_LoadMountedDynamicDependency(name,category,i,4,&dependency)!=1 ||
                    CODOL_LoadEnginePhysicsXModel(dependency.name,&model)!=1) {
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: dynamic %u/%u model %s failed\n",name,category,i,dependency.name); goto done;
                }
                binding->model=(XModel *)model;
            }
            if (entity->effect_reference) {
                const FxEffectDef *effect=NULL;
                /* The destroy effect is cosmetic on a dedicated server: clients
                 * play it from their own zone, and the server keeps only the
                 * entity's collision. An effect the native decoder cannot build
                 * (MEASURED 2026-09-26: props/sack_coffee on mp_underpass) must
                 * not stop the whole map from loading -- degrade to no effect,
                 * as weapon muzzle flashes do, and say which. The dependency
                 * reference itself is still required to be well formed. */
                if (CODOL_LoadMountedDynamicDependency(name,category,i,30,&dependency)!=1) {
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: dynamic %u/%u effect reference unreadable\n",name,category,i); goto done;
                }
                if (CODOL_LoadEngineNativeEffect(dependency.name,&effect)!=1 || !effect) {
                    Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL collision %s: dynamic %u/%u destroy effect %s could not be built; "
                        "keeping the entity without it\n",name,category,i,dependency.name);
                    effect=NULL;
                }
                binding->effect=(FxEffectDef *)effect;
            }
            if (entity->preset_reference) {
                const struct PhysPreset *preset;
                if (CODOL_LoadMountedDynamicDependency(name,category,i,0,&dependency)!=1 ||
                    CODOL_LoadEnginePhysicsPreset(dependency.name,&preset)!=1) {
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: dynamic %u/%u preset %s failed\n",name,category,i,dependency.name); goto done;
                }
                binding->preset=(struct PhysPreset *)preset;
            }
        }
    }
    views[0]=bindings[0]; views[1]=bindings[1];
    result=CODOL_BuildUnculledNativeClipMap(source,&dynamic,views,name,out) ? 1 : -1;
    if(result!=1) Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: resolved clipmap conversion failed\n",name);
done:
    free(bindings[0]); free(bindings[1]); CODOL_FreeDynamicEntities(&dynamic); return result;
}
int CODOL_InstallEngineClipMap(const char *path)
{
    static const char prefix[]="maps/mp/",suffix[]=".d3dbsp";
    char name[MAX_QPATH],*owned_name; size_t length,base_length;
    codol_collision_map_t source={0}; codol_native_clip_map_t native={0};
    if (!path) return -1;
    length=strlen(path);
    if (length<=sizeof(prefix)-1+sizeof(suffix)-1 ||
        strncmp(path,prefix,sizeof(prefix)-1) || strcmp(path+length-(sizeof(suffix)-1),suffix)) return -1;
    base_length=length-(sizeof(prefix)-1)-(sizeof(suffix)-1);
    if (base_length>=sizeof(name)) return -1;
    memcpy(name,path+sizeof(prefix)-1,base_length); name[base_length]=0;
    if (strchr(name,'/') || strchr(name,'\\') || strchr(name,':')) return -1;
    {
        int status=CODOL_LoadEngineCollisionMap(name,&source);
        if(status!=1) {
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: source decode failed (%d)\n",name,status);
            goto fail;
        }
        /* A coop match has two spellings: `name` is the base mp_* level zone
         * that carries the world, and the session/playlist spelling names the
         * coop zone, whose ONLY asset is an addon_map_ents carrying the Spec
         * Ops entities (MEASURED, docs/CODOL_ADDON_MAP_ENTS_20260920.md).
         * Overlay it before the clipmap is assembled, so the merged trigger
         * arrays reach CODOL_AppendNativeTriggers as one contiguous range. */
        const char *session=CODOL_SessionMapName();
        if(session && *session && strcmp(session,name)) {
            codol_map_entities_t addon={0},merged={0};
            status=CODOL_LoadMountedAddonMapEntities(session,&addon);
            if(status<0) {
                Com_PrintError(CON_CHANNEL_SERVER,
                    "CoDOL collision %s: addon entities maps/mp/%s.mapents are present but unreadable\n",name,session);
                goto fail;
            }
            if(status==0) {
                Com_PrintWarning(CON_CHANNEL_SERVER,
                    "CoDOL collision %s: no addon_map_ents maps/mp/%s.mapents in any mounted zone; "
                    "this match will only see the base multiplayer entities\n",name,session);
            } else {
                unsigned base_models=source.entities.model_count;
                size_t base_text=source.entities.text_size;
                if(!CODOL_MergeMapEntities(&source.entities,&addon,&merged)) {
                    CODOL_FreeMapEntities(&addon);
                    Com_PrintError(CON_CHANNEL_SERVER,
                        "CoDOL collision %s: addon entities maps/mp/%s.mapents could not be composed\n",name,session);
                    goto fail;
                }
                Com_Printf(CON_CHANNEL_SERVER,
                    "CoDOL collision %s: addon %s overlaid, entity text %u -> %u bytes, trigger models %u + %u = %u\n",
                    name,session,(unsigned)base_text,(unsigned)merged.text_size,
                    base_models,addon.model_count,merged.model_count);
                CODOL_FreeMapEntities(&addon);
                CODOL_FreeMapEntities(&source.entities);
                source.entities=merged;
            }
        }
        status=CODOL_BuildEngineClipMap(name,&source,&native);
        if(status!=1) {
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL collision %s: native assembly failed (%d)\n",name,status);
            goto fail;
        }
    }
    owned_name=malloc(length+1); if (!owned_name) goto fail;
    memcpy(owned_name,path,length+1); free((void *)native.map.name);
    native.map.name=owned_name; native.map.mapEnts->name=owned_name;
    CODOL_ShutdownEngineClipMap(); installed_source=source; installed_clip=native;
    cm=installed_clip.map;
    /* CM_LoadMap initializes trace-thread data and marks cm in use next. */
    return 1;
fail:
    CODOL_FreeNativeClipMap(&native); CODOL_FreeCollisionMap(&source); return -1;
}
#endif
