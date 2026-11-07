/* Native script registry/lifetime checks without engine startup or game data. */
#include "codol_assets.h"
#include "codol_weapon_native.h"
#include "codol_collision.h"
#include "codol_dynents.h"
#include "codol_effects.h"
#include "codol_effects_native.h"
#include "codol_xmodel.h"
#include "codol_xmodel_native.h"
#include "codol_xanim_native.h"
#include "codol_material_native.h"
#include "codol_physics.h"
#include "codol_physics_native.h"
#include "codol_xsurface.h"
#include "codol_stream_model.h"
#include "codol_load_blocks.h"
#include "codol_asset_stream.h"
#include "qcommon.h"
#include "world.h"
#include "zlib/zlib.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* This standalone loader fixture has no engine string table or developer
 * console. Asset lifetime and parsing remain backed by their real sources. */
cvar_t *com_developer;
void QDECL Com_DPrintf(conChannel_t channel,const char *fmt,...)
{ (void)channel; (void)fmt; }
int CODOL_EngineStringHandleIs(unsigned handle,const char *name)
{ return handle==33 && name && !strcmp(name,"tag"); }
void CODOL_ReleaseEngineWeaponHideTags(codol_weapon_hide_tag_handles_t *owned)
{
    unsigned i;
    if(!owned) return;
    for(i=0;i<32;++i) assert(!owned->tags[i]);
    memset(owned,0,sizeof(*owned));
}

voidpf zcalloc(voidpf unused, unsigned n, unsigned size)
{
    (void)unused;
    return size && n > SIZE_MAX / size ? NULL : calloc(n, size);
}
void zcfree(voidpf unused, voidpf p) { (void)unused; free(p); }

static void put32(uint8_t *p, uint32_t v)
{
    unsigned i;
    for (i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8*i));
}

typedef struct { struct XModel model; unsigned calls; int fail; } effect_model_test_t;
static const struct XModel *test_effect_model(void *context,const char *name)
{
    effect_model_test_t *state=context; assert(!strcmp(name,"m")); ++state->calls;
    return state->fail ? NULL : &state->model;
}

static int default_weapon_build_calls,default_weapon_build_fail;
static int test_build_default_weapon(const char *name,codol_native_weapon_core_t *out)
{
    codol_mounted_weapon_t source;
    ++default_weapon_build_calls;
    assert(CODOL_LoadMountedWeapon(name,&source)==1);
    out->graphs.points[0]=malloc(2*sizeof(float)); assert(out->graphs.points[0]);
    if(default_weapon_build_fail) return -1;
    out->definition.szInternalName=source.strings[0];
    out->definition.damage=source.asset.data[0x588];
    out->inherits_perks=source.asset.data[0xbc2];
    out->lock_warning_gate=source.asset.data[0xbbd];
    return 1;
}
static void write_source_ex(const uint8_t *source, size_t length, int corrupt, char *path)
{
    static const char name[] = "maps/mp/native.gsc";
    uint8_t data[256] = {0};
    size_t blob = 16 + sizeof(name) + length + 1, size = 72 + blob;
    int fd = mkstemp(path);
    FILE *file;
    assert(fd >= 0 && size <= sizeof(data));
    put32(data, size - 40);
    put32(data+48, 1); put32(data+52, UINT32_MAX);
    put32(data+56, CODOL_ASSET_RAWFILE); put32(data+60, 32);
    put32(data+64, UINT32_MAX); put32(data+68, blob);
    put32(data+72, UINT32_MAX); put32(data+80, length + !!corrupt);
    put32(data+84, UINT32_MAX);
    memcpy(data+88, name, sizeof(name));
    memcpy(data+88+sizeof(name), source, length);
    file = fdopen(fd, "wb"); assert(file);
    assert(fwrite(data, 1, size, file) == size && !fclose(file));
}

static void mount_source_ex(const uint8_t *source, size_t length, int corrupt)
{
    char path[] = "/tmp/codol-registry-XXXXXX";
    write_source_ex(source, length, corrupt, path);
    assert(CODOL_MountArchive(path, NULL));
    assert(!unlink(path)); /* mounted image owns its data */
}

static void mount_source(const uint8_t *source, size_t length)
{
    mount_source_ex(source, length, 0);
}

static void mount_table(unsigned char value, int pooled)
{
    uint8_t data[128] = {0};
    char path[] = "/tmp/codol-table-XXXXXX";
    size_t blob_size = pooled ? 30 : 32, size = 72+blob_size;
    int fd = mkstemp(path);
    FILE *file;
    assert(fd >= 0);
    put32(data, size-40); put32(data+48, 1); put32(data+52, UINT32_MAX);
    put32(data+56, CODOL_ASSET_STRINGTABLE); put32(data+60, 32);
    put32(data+64, UINT32_MAX); put32(data+68, blob_size);
    put32(data+72, UINT32_MAX); put32(data+76, 1); put32(data+80, 1); put32(data+84, UINT32_MAX);
    memcpy(data+88, "t.csv", 6);
    put32(data+94, pooled ? 0x30000123 : UINT32_MAX); put32(data+98, value);
    if (!pooled) data[102] = value;
    file = fdopen(fd, "wb"); assert(file);
    assert(fwrite(data, 1, size, file) == size && !fclose(file));
    assert(CODOL_MountArchive(path, NULL)); assert(!unlink(path));
}

static const char *collision_name(void *context,uint32_t reference)
{
    assert(reference==0x30000123);
    return context;
}
static void *collision_model(void *context,uint32_t reference)
{
    assert(reference==0x30000123); return context;
}

typedef struct { unsigned calls,releases,live,fail_at,overflow; } bone_string_test_t;
static unsigned test_acquire_bone(void *context,const char *name)
{
    bone_string_test_t *s=context;
    assert(!strcmp(name,"tag")); ++s->calls;
    if (s->calls==s->fail_at && !s->overflow) return 0;
    ++s->live;
    return s->calls==s->fail_at ? 65536 : 33;
}
static void test_release_bone(void *context,unsigned handle)
{
    bone_string_test_t *s=context;
    assert((handle==33 || handle==65536) && s->live);
    --s->live; ++s->releases;
}
static unsigned test_acquire_weapon_tag(void *context,const char *name)
{
    assert(!strcmp(name,"tag") || !strcmp(name,"new"));
    return test_acquire_bone(context,"tag");
}
typedef struct { unsigned calls,mode; } stream_loader_test_t;
static int test_stream_loader(void *context,const char *name,codol_stream_model_t *out)
{
    stream_loader_test_t *state=context; codol_stream_model_t result={0};
    uint8_t *root;
    assert(!strcmp(name,"lod")); ++state->calls;
    if (!state->mode) return 0;
    root=calloc(1,220); assert(root);
    result.storage[0]=root; result.blocks[3]=(codol_model_block_t){root,220};
    put32(root,0x30000031); put32(root+4,0x30000035);
    root[8]=state->mode==2 ? 1 : 2;
    memcpy(root+48,state->mode==1 ? "bad" : "lod",4); root[52]=7;
    *out=result; return 1;
}
static int check_surface_corpus(int argc,char **argv)
{
    unsigned zones=0,assets=0,surfaces=0,failed=0,meshes=0,deferred_meshes=0;
    int path;
    for (path=1;path<argc;++path) {
        codol_zone_t zone={0};
        codol_load_blocks_t replay={0};
        codol_model_block_t blocks[8];
        unsigned i;
        if (!CODOL_OpenZoneFile(&zone,argv[path]) || !CODOL_ReplayZone(&zone,&replay,NULL)) {
            fprintf(stderr,"zone replay failed: %s\n",argv[path]);
            CODOL_FreeLoadBlocks(&replay); CODOL_CloseZone(&zone); return 1;
        }
        CODOL_LoadBlockViews(&replay,blocks); blocks[0]=(codol_model_block_t){0};
        for (i=0;i<zone.asset_count;++i) {
            codol_asset_t asset,candidates[4]={{0}};
            unsigned j,lod;
            assert(CODOL_ZoneAsset(&zone,i,&asset));
            if (asset.type==3) candidates[0]=asset;
            else if (asset.type==4) {
                if (!CODOL_XModelInlineSurfaceAssets(&asset,candidates)) {
                    fprintf(stderr,"model surface extraction failed: %s asset %u\n",argv[path],i); ++failed; continue;
                }
            } else continue;
            if (asset.type==4) {
                codol_xmodel_lods_t meta;
                codol_mounted_model_surfaces_t inputs[4]={{0}};
                const codol_mounted_model_surfaces_t *sources[4]={0};
                codol_native_model_mesh_t mesh={0}; int ready=1;
                assert(CODOL_ReadXModelLods(&asset,&meta));
                for(lod=0;lod<4;++lod) {
                    uint32_t ref=meta.lods[lod].surfaces_reference;
                    if(!candidates[lod].data && ref && ref<UINT32_MAX-1)
                        assert(CODOL_ResolveSurfaceAlias(&replay,ref,candidates+lod));
                }
                for(lod=meta.first;lod<meta.count;++lod) {
                    if(!meta.lods[lod].surface_count) continue;
                    if(!candidates[lod].data) { ready=0; break; }
                    assert(CODOL_ReadModelSurfaces(candidates+lod,&inputs[lod].source));
                    if(inputs[lod].source.count!=meta.lods[lod].surface_count) { ready=0; break; }
                    memcpy(inputs[lod].blocks,blocks,sizeof(blocks)); sources[lod]=inputs+lod;
                }
                if(ready) {
                    if(!CODOL_BuildNativeModelMesh(asset.data[6],&meta,sources,&mesh)) {
                        fprintf(stderr,"model mesh failed: %s asset %u\n",argv[path],i); ++failed;
                    } else {
                        assert(mesh.count==asset.data[6]);
                        for(j=0;j<mesh.count;++j) assert(mesh.material_indices[j]==j);
                        {
                            codol_native_model_core_t core={0}; int ids[256];
                            xMaterial_t *materials[256];
                            core.model.name="corpus";
                            for(j=0;j<asset.data[6];++j) materials[j]=ids+j;
                            assert(CODOL_BindNativeModelMesh(&core,&mesh,materials,asset.data[6]));
                            assert((unsigned char)core.model.numsurfs==mesh.count);
                            for(j=0;j<mesh.count;++j) assert(core.model.materialHandles[j]==ids+j);
                            assert(!memcmp(core.model.lodInfo,mesh.lods,sizeof(mesh.lods)));
                            CODOL_FreeNativeModelCore(&core);
                        }
                        ++meshes;
                    }
                } else ++deferred_meshes;
                CODOL_FreeNativeModelMesh(&mesh);
                for(lod=0;lod<4;++lod) CODOL_FreeModelSurfaces(&inputs[lod].source);
            }
            for (lod=0;lod<4;++lod) {
            codol_model_surfaces_t owned={0};
            if (!candidates[lod].data) continue;
            if (!CODOL_ReadModelSurfaces(candidates+lod,&owned)) {
                fprintf(stderr,"surface decode failed: %s asset %u\n",argv[path],i); ++failed; continue;
            }
            ++assets;
            {
                codol_native_lod_geometry_t native_lod={0};
                unsigned triangles=0,vertices=0,word;
                uint32_t mask[4]={0};
                assert(CODOL_BuildNativeLodGeometry(&owned,blocks,&native_lod));
                assert(native_lod.count==owned.count);
                for (j=0;j<native_lod.count;++j) {
                    assert(native_lod.surfaces[j].baseTriIndex==(uint16_t)triangles);
                    assert(native_lod.surfaces[j].baseVertIndex==(uint16_t)vertices);
                    triangles+=native_lod.surfaces[j].triCount;
                    vertices+=native_lod.surfaces[j].vertCount;
                    for (word=0;word<4;++word) {
                        uint32_t bits;
                        memcpy(&bits,owned.surfaces[j].header+52+word*4,4); mask[word]|=bits;
                    }
                    assert(!memcmp(native_lod.surfaces+j,&native_lod.owners[j].surface,sizeof(XSurface)));
                }
                assert(!memcmp(mask,native_lod.part_bits,sizeof(mask)));
                CODOL_FreeNativeLodGeometry(&native_lod);
            }
            for (j=0;j<owned.count;++j) {
                codol_native_surface_geometry_t native={0};
                if (!CODOL_BuildNativeSurfaceGeometry(owned.surfaces+j,blocks,&native)) {
                    codol_surface_arrays_t arrays={0}; codol_native_rigid_lists_t rigid={0};
                    int array_ok=CODOL_ResolveSurfaceArrays(owned.surfaces+j,blocks,&arrays);
                    int rigid_ok=CODOL_ResolveNativeRigidLists(owned.surfaces+j,blocks,&rigid);
                    fprintf(stderr,"surface construction failed: %s asset %u surface %u\n",argv[path],i,j); ++failed;
                    fprintf(stderr,"arrays=%d rigid=%d vertex count=%u triangle count=%u refs=%08x/%08x/%08x\n",
                        array_ok,rigid_ok,owned.surfaces[j].arrays[1].count,owned.surfaces[j].arrays[2].count,
                        owned.surfaces[j].arrays[0].reference,owned.surfaces[j].arrays[1].reference,owned.surfaces[j].arrays[2].reference);
                    CODOL_FreeSurfaceArrays(&arrays); CODOL_FreeNativeRigidLists(&rigid);
                } else {
                    assert(native.surface.vertCount==owned.surfaces[j].arrays[1].count);
                    assert(native.surface.triCount==owned.surfaces[j].arrays[2].count);
                    assert((uint8_t)native.surface.tileMode==owned.surfaces[j].header[0]);
                    assert(native.surface.deformed==owned.surfaces[j].header[1]);
                    assert(!memcmp(native.surface.partBits,owned.surfaces[j].header+52,16));
                    {
                        uint32_t mask[4]={0}; unsigned n,group,cursor=0;
                        for (n=0;n<native.rigid.count;++n) {
                            unsigned bone=native.rigid.lists[n].boneOffset>>6;
                            assert(bone<128); mask[bone>>5]|=UINT32_C(0x80000000)>>(bone&31);
                        }
                        for (group=0;group<4;++group) for (n=0;n<(unsigned)native.surface.vertInfo.vertCount[group];++n) {
                            unsigned field;
                            for (field=0;field<=group;++field) {
                                unsigned at=cursor+(field ? 2*field-1 : 0);
                                unsigned bone=native.surface.vertInfo.vertsBlend[at]>>6;
                                assert(bone<128); mask[bone>>5]|=UINT32_C(0x80000000)>>(bone&31);
                            }
                            cursor+=2*group+1;
                        }
                        assert(!memcmp(mask,native.surface.partBits,sizeof(mask)));
                    }
                    ++surfaces;
                }
                CODOL_FreeNativeSurfaceGeometry(&native);
            }
            CODOL_FreeModelSurfaces(&owned);
            }
        }
        CODOL_FreeLoadBlocks(&replay); CODOL_CloseZone(&zone); ++zones;
    }
    printf("Native surface corpus: %u zones, %u assets, %u constructed surfaces, %u failures\n",zones,assets,surfaces,failed);
    printf("Model mesh corpus: %u assembled, %u require external surface resolution\n",meshes,deferred_meshes);
    return failed ? 1 : 0;
}
static int check_stream_corpus(int argc,char **argv)
{
    unsigned files=0,surfaces=0; int i;
    for (i=2;i<argc;++i) {
        FILE *f=fopen(argv[i],"rb"); long length; uint8_t *data;
        codol_stream_model_t stream={0}; codol_model_surfaces_t source={0};
        codol_native_lod_geometry_t native={0}; unsigned j;
        assert(f && !fseek(f,0,SEEK_END)); length=ftell(f); assert(length>=0 && !fseek(f,0,SEEK_SET));
        data=malloc(length); assert(data && fread(data,1,length,f)==(size_t)length && !fclose(f));
        if (!CODOL_ReadStreamModel(data,length,&stream) ||
            !CODOL_ReadStreamModelSurfaces(&stream,&source) ||
            !CODOL_BuildNativeLodGeometry(&source,stream.blocks,&native)) {
            fprintf(stderr,"stream conversion failed: %s\n",argv[i]); return 1;
        }
        assert(native.count==source.count);
        surfaces+=native.count; ++files;
        CODOL_FreeModelSurfaces(&source); CODOL_FreeStreamModel(&stream); free(data);
        for(j=0;j<native.count;++j) {
            XSurface *s=native.surfaces+j;
            if(s->vertCount) assert(s->verts);
            if(s->triCount) assert(s->triIndices[0]<s->vertCount);
            if(s->vertListCount) assert(s->vertList);
        }
        CODOL_FreeNativeLodGeometry(&native);
    }
    printf("PASS: %u streamed files, %u owned native surfaces\n",files,surfaces); return 0;
}
/* Optional local corpus: extracted IWD entries retain archive prefixes. Search
 * numbered archives newest first, like the filesystem's archive precedence. */
static int corpus_stream_loader(void *context,const char *name,codol_stream_model_t *out)
{
    char path[2048]; int archive; FILE *file;
    if (!name || strchr(name,'/') || strchr(name,'\\') || strchr(name,':')) return -1;
    for (archive=5;archive>=0;--archive) {
        long length; uint8_t *bytes; int status;
        if (snprintf(path,sizeof(path),"%s/iw_model_%02d__%s",(const char *)context,archive,name)>=(int)sizeof(path)) return -1;
        file=fopen(path,"rb"); if (!file) continue;
        if (fseek(file,0,SEEK_END) || (length=ftell(file))<0 || length>CODOL_ASSET_LIMIT ||
            fseek(file,0,SEEK_SET)) { fclose(file); return -1; }
        bytes=malloc(length ? (size_t)length : 1); assert(bytes);
        status=fread(bytes,1,length,file)==(size_t)length && CODOL_ReadStreamModel(bytes,length,out);
        free(bytes); fclose(file); return status ? 1 : -1;
    }
    return 0;
}
static void *collision_named_model(void *context,const char *name)
{
    assert(!strcmp(name,"crate")); return context;
}
typedef struct { unsigned names,skeletons,geometry; } collision_model_counts_t;
static void *count_collision_model_name(void *context,const char *name)
{
    collision_model_counts_t *counts=context;
    const codol_mounted_model_skeleton_t *skeleton;
    const codol_mounted_model_geometry_t *geometry;
    assert(name && *name && *name!=','); ++counts->names;
    if (CODOL_LoadMountedXModelSkeleton(name,&skeleton)==1) {
        ++counts->skeletons;
        if (CODOL_LoadMountedXModelGeometry(name,&geometry)==1) ++counts->geometry;
    }
    return NULL; /* Corpus inspection does not fabricate a native XModel. */
}
typedef struct { unsigned acquired,released,live,models,failed; } native_collision_counts_t;
static unsigned native_collision_acquire(void *context,const char *name)
{
    native_collision_counts_t *state=context;
    assert(name && state->acquired<65535); /* SL also interns the empty string. */
    ++state->live; return ++state->acquired;
}
static void native_collision_release(void *context,unsigned handle)
{
    native_collision_counts_t *state=context;
    assert(handle && handle<=state->acquired && state->live);
    --state->live; ++state->released;
}
static void *native_collision_model(void *context,const char *name)
{
    native_collision_counts_t *state=context; const XModel *model;
    if(CODOL_LoadMountedCollisionXModel(name,native_collision_acquire,native_collision_release,state,&model)!=1) {
        if(state->failed++<8) fprintf(stderr,"Native collision model unresolved: %s\n",name);
        return NULL;
    }
    ++state->models; return (void *)model;
}
static int check_native_collision(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0}; int status;
    if(argc<5) return 2;
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    assert(CODOL_MountRuntimeArchives((const char *const *)(argv+4),argc-4,NULL,NULL,NULL));
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    printf("Native collision %s: status %d, %u/%u models bound, %u unresolved materials, %u owned bone strings\n",
        argv[3],status,state.models,map.static_models.count,map.materials.unresolved,state.live);
    status=status==1 && !map.static_models.unresolved && !map.materials.unresolved ? 0 : 1;
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    assert(!state.live && state.acquired==state.released);
    assert(CODOL_SetStreamModelLoader(NULL,NULL)); return status;
}
/* Offline audit of the contents/surfaceFlags actually present in a shipped map.
 *
 * Motivation. C1.exe's player trace mask is 0x2814011 (20 sites; the constant
 * 0x2810011 this server uses appears NOWHERE in the 33MB image). The two
 * differ by exactly one bit, 0x4000. C1's material infoParms table names no
 * material that can author contents 0x4000, 0x800000 or 0x2000000, so on paper
 * those three bits can only arrive at runtime on entities -- but "on paper" is
 * how three earlier hypotheses in this investigation died. This measures it.
 *
 * Pre-registered reading, fixed before running:
 *   - If 0x4000 occurs in ZERO brushes, ZERO leaf contents and ZERO materials,
 *     then swapping our mask for C1's cannot change any world-geometry trace
 *     result, and the mask difference is DEAD as an explanation for either the
 *     slab (extra solid) or the puddle (missing solid). It would remain a real
 *     parity defect for entity traces only.
 *   - If 0x4000 occurs anywhere in world data, the brush-selection counts
 *     under the two masks differ and the mask is a live candidate.
 *   - The same test is reported for 0x800000 and 0x2000000, the two bits the
 *     flags header records as unresolved.
 * Needs no server, no capture and no coordinates.
 *
 * argv: --contents <streamdir> <map> <C1.exe> <zone.ff>...  */
static void contents_names(int c,char *buf,size_t n)
{
    static const struct { int bit; const char *name; } tab[] = {
        {0x00000001,"solid"},{0x00000002,"foliage"},{0x00000004,"aiclipallowdeath"},
        {0x00000010,"glass"},{0x00000020,"water"},{0x00000040,"canshootclip"},
        {0x00000080,"clipmissile"},{0x00000200,"vehicleclip"},{0x00000400,"itemclip"},
        {0x00000800,"sky"},{0x00001000,"ai_nosight"},{0x00002000,"clipshot"},
        {0x00010000,"playerclip"},{0x00020000,"monsterclip"},{0x01000000,"mantle"},
        {0x08000000,"detail"},{0x10000000,"structural"},{0x80000000,"nodrop"}
    };
    size_t i,used=0; int residue=c;
    buf[0]=0;
    for(i=0;i<sizeof(tab)/sizeof(tab[0]);++i)
        if(c & tab[i].bit) {
            residue &= ~tab[i].bit;
            used+=(size_t)snprintf(buf+used,used<n?n-used:0,"%s%s",used?"|":"",tab[i].name);
            if(used>=n) return;
        }
    if(residue)
        snprintf(buf+used,used<n?n-used:0,"%sUNNAMED:0x%x",used?"|":"",(unsigned)residue);
}
static int check_contents(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    const int ours=0x2810011, c1=0x2814011;
    const int probe[3]={0x4000,0x00800000,0x02000000};
    unsigned i,j; int status;
    int brush_union=0, leaf_union=0, mat_union=0, sf_union=0;
    unsigned sel_ours=0, sel_c1=0, terr_mats=0;
    unsigned hit_brush[3]={0,0,0}, hit_leaf[3]={0,0,0}, hit_mat[3]={0,0,0};
    char nb[256];
    if(argc<6) return 2;
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),argc-5,argv[4],NULL,NULL)) {
        printf("Contents audit %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1) {
        printf("Contents audit %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    for(i=0;i<map.brushes.brush_count;++i) {
        int c=map.brushes.brushes[i].contents;
        brush_union|=c;
        if(c & ours) ++sel_ours;
        if(c & c1)   ++sel_c1;
        for(j=0;j<3;++j) if(c & probe[j]) ++hit_brush[j];
    }
    for(i=0;i<map.leaves.leaf_count;++i) {
        int c=map.leaves.leaves[i].brushContents | map.leaves.leaves[i].terrainContents;
        leaf_union|=c;
        for(j=0;j<3;++j) if(c & probe[j]) ++hit_leaf[j];
    }
    for(i=0;i<map.materials.count;++i) {
        int c=map.materials.materials[i].contentFlags;
        mat_union|=c; sf_union|=map.materials.materials[i].surfaceFlags;
        for(j=0;j<3;++j) if(c & probe[j]) ++hit_mat[j];
    }
    printf("Contents audit %s: brushes %u leaves %u materials %u terrain-tris %u aabbs %u\n",
        argv[3],map.brushes.brush_count,map.leaves.leaf_count,
        map.materials.count,map.terrain.triangle_count,map.terrain.aabb_count);
    contents_names(brush_union,nb,sizeof nb);
    printf("  union brush contents   0x%08x = %s\n",(unsigned)brush_union,nb);
    contents_names(leaf_union,nb,sizeof nb);
    printf("  union leaf contents    0x%08x = %s\n",(unsigned)leaf_union,nb);
    contents_names(mat_union,nb,sizeof nb);
    printf("  union material content 0x%08x = %s\n",(unsigned)mat_union,nb);
    printf("  union material sflags  0x%08x (surface types seen:",(unsigned)sf_union);
    for(i=0;i<32;++i) {
        unsigned seen=0;
        for(j=0;j<map.materials.count;++j)
            if((((unsigned)map.materials.materials[j].surfaceFlags)>>20&31u)==i) { seen=1; break; }
        if(seen) printf(" %u",i);
    }
    printf(")\n");
    for(j=0;j<3;++j)
        printf("  probe bit 0x%08x: brushes %u  leaves %u  materials %u\n",
            (unsigned)probe[j],hit_brush[j],hit_leaf[j],hit_mat[j]);
    printf("  brushes selected by ours 0x%08x: %u ; by C1 0x%08x: %u ; delta %d\n",
        (unsigned)ours,sel_ours,(unsigned)c1,sel_c1,(int)sel_c1-(int)sel_ours);
    /* Terrain is selected by its material, not by a brush contents word: list
     * every material an aabb references, because if none of them carries a bit
     * in the player mask the ground would not be hit at all. */
    {
        unsigned aabb_sel=0, aabb_unsel=0, aabb_bad=0;
        for(i=0;i<map.terrain.aabb_count;++i) {
            unsigned mi=map.terrain.aabbs[i].materialIndex, dup=0;
            if(mi>=map.materials.count) { ++aabb_bad; continue; }
            if(map.materials.materials[mi].contentFlags & ours) ++aabb_sel; else ++aabb_unsel;
            for(j=0;j<i;++j) if(map.terrain.aabbs[j].materialIndex==mi) { dup=1; break; }
            if(dup) continue;
            contents_names(map.materials.materials[mi].contentFlags,nb,sizeof nb);
            printf("  terrain material[%u] \"%s\" contents 0x%08x = %s  sflags 0x%08x type %u%s\n",
                mi,map.materials.materials[mi].material,
                (unsigned)map.materials.materials[mi].contentFlags,nb,
                (unsigned)map.materials.materials[mi].surfaceFlags,
                ((unsigned)map.materials.materials[mi].surfaceFlags>>20)&31u,
                (map.materials.materials[mi].contentFlags & ours)?"":"   <-- NOT in player mask");
            ++terr_mats;
        }
        printf("  terrain aabbs: %u player-solid material, %u NOT, %u out of range (%u distinct)\n",
            aabb_sel,aabb_unsel,aabb_bad,terr_mats);
    }
    /* Every material whose surface type is snow, for the slab cross-check:
     * the obstruction reported sflags 0x1300000, type 19. */
    for(i=0;i<map.materials.count;++i) {
        unsigned sf=(unsigned)map.materials.materials[i].surfaceFlags;
        if(((sf>>20)&31u)!=19u) continue;
        contents_names(map.materials.materials[i].contentFlags,nb,sizeof nb);
        printf("  SNOW material[%u] \"%s\" sflags 0x%08x contents 0x%08x = %s%s\n",
            i,map.materials.materials[i].material,sf,
            (unsigned)map.materials.materials[i].contentFlags,nb,
            (map.materials.materials[i].contentFlags & ours)?"":"   <-- NOT in player mask");
    }
    /* Duplicate material NAMES with conflicting player-solidity.
     *
     * The same shader legitimately appears several times with different
     * contents (a render copy, a clip copy, a bullet-only copy). Collision data
     * selects them BY INDEX, so duplicates are harmless only while every index
     * is right. If any index is off, or any name-keyed lookup collapses the
     * copies, a surface flips between solid and non-solid -- extra solid in one
     * place and missing solid in another, from ONE defect. This counts the
     * exposure: names where at least two copies disagree about whether the
     * player collides with them at all. */
    {
        unsigned names_conflict=0, shown=0;
        printf("  materials unresolved: %u of %u\n",map.materials.unresolved,map.materials.count);
        for(i=0;i<map.materials.count;++i) {
            unsigned first=1, sel=(map.materials.materials[i].contentFlags & ours)!=0, conflict=0;
            for(j=0;j<map.materials.count;++j) {
                if(j==i) continue;
                if(strcmp(map.materials.materials[j].material,map.materials.materials[i].material)) continue;
                if(j<i) { first=0; break; }
                if(((map.materials.materials[j].contentFlags & ours)!=0)!=sel) conflict=1;
            }
            if(!first || !conflict) continue;
            ++names_conflict;
            if(shown<12u) {
                printf("    CONFLICT \"%s\":",map.materials.materials[i].material);
                for(j=0;j<map.materials.count;++j)
                    if(!strcmp(map.materials.materials[j].material,map.materials.materials[i].material))
                        printf(" [%u]=0x%08x%s",j,(unsigned)map.materials.materials[j].contentFlags,
                            (map.materials.materials[j].contentFlags & ours)?"(solid)":"(pass)");
                printf("\n");
                ++shown;
            }
        }
        printf("  material names whose copies disagree on player-solidity: %u\n",names_conflict);
    }
    printf("  VERDICT: mask bit 0x4000 %s in world data -> C1 mask swap is %s for world geometry\n",
        (hit_brush[0]||hit_leaf[0]||hit_mat[0])?"PRESENT":"ABSENT",
        (hit_brush[0]||hit_leaf[0]||hit_mat[0])?"a LIVE candidate":"INERT");
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return 0;
}
/* Offline tree-descending collision query: names what a player hull actually
 * touches at a point, through the SAME structures and the SAME traversal the
 * engine uses, with the real player trace mask applied.
 *
 * The traversal is transcribed from the retained CM_TestInLeafBrushNode_r in
 * src/asmsource/_cm_trace.asm (lines 78-175), which is the exact function a
 * point/startsolid test such as stance_clear ends up in. That asm settles the
 * structure semantics that a C header alone leaves ambiguous:
 *   - node stride is 0x14 (20) bytes; axis@0, leafBrushCount@2, contents@4,
 *     and a union at @8 that is either {brushes ptr} or {dist, range,
 *     childOffset[2]} at @8/@c/@10/@12.
 *   - childOffset is RELATIVE, in node units: `ebx += childOffset[i] * 20`.
 *   - leafBrushCount > 0 is a brush list, == 0 is a pure split, and < 0 means
 *     recurse into the node immediately following (ebx+0x14) and THEN split.
 *   - a node whose own `contents` misses the trace mask is skipped entirely,
 *     subtree and all -- `test [ebx+4], edx; jz return`.
 *   - brush stride is 80 bytes, contents at +0xc, mins at +0, maxs at +0x10.
 *   - the split test compares the trace's absolute bounds against `dist`:
 *     absmin[axis] > dist takes child0 only, absmax[axis] < dist takes child1
 *     only, otherwise both.
 *
 * An earlier version of this query got all of that wrong in the permissive
 * direction: it ignored node contents, always visited both children, and
 * reached leaves by testing every leaf's bounding box instead of descending
 * the BSP. It reported two map-sized brushes at almost every probe point,
 * which cannot be what the engine sees -- players walk through that band.
 * That over-reach is the difference between "reachable in principle" and "the
 * engine actually visits it", and only the second is evidence.
 *
 * argv: --treequery <streamdir> <map> <C1.exe> <zone.ff>... -- <x> <y> <z> [height]
 * Default height 72 (standing); the hull is the stance hull, -15..15 in x/y. */
static int tri_box_overlap(const float c[3],const float h[3],
                           const float a[3],const float b[3],const float cc[3])
{
    float v0[3],v1[3],v2[3],e[3][3],n[3],d,r,p0,p1,p2,mn,mx; int i,j,k;
    for(i=0;i<3;++i){ v0[i]=a[i]-c[i]; v1[i]=b[i]-c[i]; v2[i]=cc[i]-c[i]; }
    for(i=0;i<3;++i){ e[0][i]=v1[i]-v0[i]; e[1][i]=v2[i]-v1[i]; e[2][i]=v0[i]-v2[i]; }
    for(j=0;j<3;++j) for(k=0;k<3;++k) {
        float ax[3]={0,0,0}; int u=(k+1)%3,w=(k+2)%3;
        ax[u]=-e[j][w]; ax[w]=e[j][u];
        p0=v0[0]*ax[0]+v0[1]*ax[1]+v0[2]*ax[2];
        p1=v1[0]*ax[0]+v1[1]*ax[1]+v1[2]*ax[2];
        p2=v2[0]*ax[0]+v2[1]*ax[1]+v2[2]*ax[2];
        mn=p0<p1?(p0<p2?p0:p2):(p1<p2?p1:p2);
        mx=p0>p1?(p0>p2?p0:p2):(p1>p2?p1:p2);
        r=h[0]*(ax[0]<0?-ax[0]:ax[0])+h[1]*(ax[1]<0?-ax[1]:ax[1])+h[2]*(ax[2]<0?-ax[2]:ax[2]);
        if(mn>r || mx<-r) return 0;
    }
    for(i=0;i<3;++i) {
        mn=v0[i]<v1[i]?(v0[i]<v2[i]?v0[i]:v2[i]):(v1[i]<v2[i]?v1[i]:v2[i]);
        mx=v0[i]>v1[i]?(v0[i]>v2[i]?v0[i]:v2[i]):(v1[i]>v2[i]?v1[i]:v2[i]);
        if(mn>h[i] || mx<-h[i]) return 0;
    }
    n[0]=e[0][1]*e[1][2]-e[0][2]*e[1][1];
    n[1]=e[0][2]*e[1][0]-e[0][0]*e[1][2];
    n[2]=e[0][0]*e[1][1]-e[0][1]*e[1][0];
    d=n[0]*v0[0]+n[1]*v0[1]+n[2]*v0[2];
    r=h[0]*(n[0]<0?-n[0]:n[0])+h[1]*(n[1]<0?-n[1]:n[1])+h[2]*(n[2]<0?-n[2]:n[2]);
    return (d<0?-d:d)<=r;
}
/* Query state, so the two recursive walks stay readable. */
typedef struct {
    const codol_collision_map_t *map;
    float ctr[3],half[3],amin[3],amax[3];
    int mask;
    unsigned leaves,brush_hits,terr_hits,terr_all,aabb_hits,world_brush_split;
    int quiet;
    float *top_terrain,*top_brush;
} tq_t;
/* CM_TestInLeafBrushNode_r, transcribed. */
static void tq_brush_node(tq_t *q,int node,int depth)
{
    const codol_collision_brush_node_t *bn;
    const codol_collision_map_t *map=q->map;
    char nb[256]; unsigned k; int axis; float dist;
    if(node<0 || (unsigned)node>=map->brush_tree.node_count || depth>128) return;
    bn=&map->brush_tree.nodes[node];
    if(!(bn->contents & q->mask)) return;          /* test [ebx+4], edx ; jz */
    if(bn->leafBrushCount>0) {
        for(k=0;k<(unsigned)bn->leafBrushCount;++k) {
            unsigned bi=bn->data.leaf.brushes[k];
            const codol_collision_brush_t *br;
            int inside=1; unsigned s;
            if(bi>=map->brushes.brush_count) continue;
            br=&map->brushes.brushes[bi];
            if(!(br->contents & q->mask)) continue;
            if(q->amin[0]>=br->maxs[0]||q->amin[1]>=br->maxs[1]||q->amin[2]>=br->maxs[2]||
               br->mins[0]>=q->amax[0]||br->mins[1]>=q->amax[1]||br->mins[2]>=q->amax[2]) continue;
            /* numsides==0 is a complete description: the brush IS its box, and
             * the six axial planes live in mins/maxs -- which is why the brush
             * record carries axialMaterialNum[2][3] separately from sides. */
            for(s=0;s<br->numsides && inside;++s) {
                const codol_collision_plane_t *pl=br->sides[s].plane;
                float sup=q->ctr[0]*pl->normal[0]+q->ctr[1]*pl->normal[1]+q->ctr[2]*pl->normal[2]
                        -(q->half[0]*(pl->normal[0]<0?-pl->normal[0]:pl->normal[0])
                         +q->half[1]*(pl->normal[1]<0?-pl->normal[1]:pl->normal[1])
                         +q->half[2]*(pl->normal[2]<0?-pl->normal[2]:pl->normal[2]));
                if(sup>pl->dist) inside=0;
            }
            if(!inside) continue;
            ++q->brush_hits;
            if(q->quiet) {
                if(q->top_brush && br->maxs[2]>*q->top_brush) *q->top_brush=br->maxs[2];
                continue;
            }
            contents_names(br->contents,nb,sizeof nb);
            printf("    BRUSH[%u] %s contents 0x%08x = %s sides %u box (%.1f %.1f %.1f)..(%.1f %.1f %.1f)\n",
                bi, bi>=q->world_brush_split?"TAIL/SUBMODEL-RANGE":"world-range",
                (unsigned)br->contents,nb,br->numsides,
                br->mins[0],br->mins[1],br->mins[2],br->maxs[0],br->maxs[1],br->maxs[2]);
        }
        return;
    }
    if(bn->leafBrushCount<0) tq_brush_node(q,node+1,depth+1);  /* lea edx,[ebx+0x14] */
    axis=bn->axis & 3; dist=bn->data.children.dist;
    if(axis>2) return;
    if(q->amin[axis]>dist) { tq_brush_node(q,node+bn->data.children.childOffset[0],depth+1); return; }
    if(q->amax[axis]<dist) { tq_brush_node(q,node+bn->data.children.childOffset[1],depth+1); return; }
    tq_brush_node(q,node+bn->data.children.childOffset[0],depth+1);
    tq_brush_node(q,node+bn->data.children.childOffset[1],depth+1);
}
/* The terrain aabb tree, transcribed from CM_PositionTestInAabbTree_r
 * (_cm_mesh.asm:615) and its caller CM_MeshTestInLeaf (_cm_mesh.asm:2786).
 *
 * The record is 32 bytes: origin[3]@0, halfSize[3]@0xc, materialIndex@0x18,
 * childCount@0x1a, index@0x1c. The crucial detail, and the one an earlier
 * version of this query got wrong: for an INTERIOR node (childCount != 0)
 * `index` is the ABSOLUTE index of the FIRST CHILD and the children are
 * `childCount` consecutive records -- `ebx = index<<5; ... ebx += 0x20` per
 * child. Only for a LEAF (childCount == 0) is `index` a partition index.
 * Skipping interior nodes, as the earlier version did, therefore hides every
 * triangle below the root. That is why it could not find the ground under a
 * standing player, and why its "no terrain here" was never a superset.
 *
 * CM_MeshTestInLeaf gates on the ROOT aabb's material contents before
 * descending (`test [esi+0x44], eax` where esi = cm.materials + matIndex*72,
 * contentFlags@0x44, surfaceFlags@0x40). We descend regardless and label each
 * triangle instead, reporting both counts: what the engine would collide with,
 * and what geometry is physically there. */
static void tq_aabb(tq_t *q,unsigned ai,unsigned root_mat,int depth)
{
    const codol_collision_map_t *map=q->map;
    const codol_collision_aabb_t *ab;
    char nb[256];
    if(depth>64 || ai>=map->terrain.aabb_count) return;
    ab=&map->terrain.aabbs[ai];
    /* CM_CullBox */
    if(ab->origin[0]-ab->halfSize[0]>q->amax[0]||ab->origin[0]+ab->halfSize[0]<q->amin[0]||
       ab->origin[1]-ab->halfSize[1]>q->amax[1]||ab->origin[1]+ab->halfSize[1]<q->amin[1]||
       ab->origin[2]-ab->halfSize[2]>q->amax[2]||ab->origin[2]+ab->halfSize[2]<q->amin[2]) return;
    ++q->aabb_hits;
    if(ab->childCount) {
        unsigned k;
        for(k=0;k<ab->childCount;++k) tq_aabb(q,(unsigned)ab->index+k,root_mat,depth+1);
        return;
    }
    if((unsigned)ab->index>=map->terrain.partition_count) return;
    {
        const codol_collision_partition_t *pa=&map->terrain.partitions[ab->index];
        /* Triangle indices are u16 and relative to this partition's vertex
         * BLOCK; C1 0x00583e30 resolves them against cm.verts+block*0x3000. */
        unsigned vb=(unsigned)pa->vertBlock*1024u;
        unsigned t, mi=ab->materialIndex<map->materials.count?ab->materialIndex:root_mat;
        int mc = mi<map->materials.count ? map->materials.materials[mi].contentFlags : 0;
        for(t=0;t<pa->triCount;++t) {
            unsigned ti=(unsigned)pa->firstTri+t;
            const uint16_t *idx;
            if(ti>=map->terrain.triangle_count) continue;
            idx=map->terrain.triangles[ti];
            if(!tri_box_overlap(q->ctr,q->half,map->terrain.vertices[vb+idx[0]],
                    map->terrain.vertices[vb+idx[1]],map->terrain.vertices[vb+idx[2]])) continue;
            ++q->terr_all;
            if(mc & q->mask) ++q->terr_hits;
            if(q->quiet) {
                if((mc & q->mask) && q->top_terrain) {
                    unsigned v; for(v=0;v<3;++v) {
                        float z=map->terrain.vertices[vb+idx[v]][2];
                        if(z>*q->top_terrain) *q->top_terrain=z;
                    }
                }
                continue;
            }
            contents_names(mc,nb,sizeof nb);
            printf("    TERRAIN tri %u aabb %u part %d mat[%u] \"%s\" contents 0x%08x = %s sf 0x%08x type %u %s z %.2f/%.2f/%.2f\n",
                ti,ai,ab->index,mi,
                mi<map->materials.count?map->materials.materials[mi].material:"?",
                (unsigned)mc,nb,
                mi<map->materials.count?(unsigned)map->materials.materials[mi].surfaceFlags:0u,
                mi<map->materials.count?(((unsigned)map->materials.materials[mi].surfaceFlags>>20)&31u):0u,
                (mc & q->mask)?"SOLID-to-player":"pass-through",
                map->terrain.vertices[vb+idx[0]][2],map->terrain.vertices[vb+idx[1]][2],
                map->terrain.vertices[vb+idx[2]][2]);
            {   /* A bank of snow and a floor of snow occupy the same z range
                 * but behave differently under a ground trace, which rejects
                 * anything below MIN_WALK_NORMAL. So print the normal. */
                const float *A=map->terrain.vertices[vb+idx[0]];
                const float *B=map->terrain.vertices[vb+idx[1]];
                const float *C=map->terrain.vertices[vb+idx[2]];
                float u0=B[0]-A[0],u1=B[1]-A[1],u2=B[2]-A[2];
                float v0=C[0]-A[0],v1=C[1]-A[1],v2=C[2]-A[2];
                float nx=u1*v2-u2*v1, ny=u2*v0-u0*v2, nz=u0*v1-u1*v0;
                float len=(float)sqrt((double)(nx*nx+ny*ny+nz*nz));
                float anz=len>0.0f?(nz<0.0f?-nz:nz)/len:0.0f;
                printf("        |nz| %.4f %s  v (%.1f %.1f %.1f) (%.1f %.1f %.1f) (%.1f %.1f %.1f)\n",
                    (double)anz, anz<0.7f?"<-- too steep to walk on":"walkable slope",
                    A[0],A[1],A[2],B[0],B[1],B[2],C[0],C[1],C[2]);
            }
        }
    }
}
static void tq_leaf_quiet(tq_t *q,const codol_collision_leaf_t *lf)
{
    unsigned k;
    tq_brush_node(q,lf->leafBrushNode,0);
    for(k=0;k<lf->collAabbCount;++k)
        tq_aabb(q,(unsigned)lf->firstCollAabbIndex+k,0,0);
}
static void tq_leaf(tq_t *q,unsigned li)
{
    const codol_collision_map_t *map=q->map;
    const codol_collision_leaf_t *lf;
    char nb[256]; unsigned k;
    if(li>=map->leaves.leaf_count) return;
    lf=&map->leaves.leaves[li];
    ++q->leaves;
    if(q->quiet) { tq_leaf_quiet(q,lf); return; }
    contents_names(lf->brushContents|lf->terrainContents,nb,sizeof nb);
    printf("  leaf[%u] brushContents 0x%08x terrainContents 0x%08x = %s aabbs %u..%u node %d\n",
        li,(unsigned)lf->brushContents,(unsigned)lf->terrainContents,nb,
        lf->firstCollAabbIndex,(unsigned)lf->firstCollAabbIndex+lf->collAabbCount,lf->leafBrushNode);
    tq_brush_node(q,lf->leafBrushNode,0);
    /* CM_MeshTestInLeaf: each of the leaf's aabbs is the ROOT of a tree. */
    for(k=0;k<lf->collAabbCount;++k)
        tq_aabb(q,(unsigned)lf->firstCollAabbIndex+k,
                (unsigned)map->terrain.aabbs[((unsigned)lf->firstCollAabbIndex+k)
                    <map->terrain.aabb_count?(unsigned)lf->firstCollAabbIndex+k:0].materialIndex,0);
}
/* BSP descent: children[i] < 0 encodes leaf index -1-child. */
static void tq_node(tq_t *q,int node,int depth)
{
    const codol_collision_map_t *map=q->map;
    const codol_collision_node_t *nd;
    const codol_collision_plane_t *pl;
    float d,r;
    if(depth>256) return;
    if(node<0) { tq_leaf(q,(unsigned)(-1-node)); return; }
    if((unsigned)node>=map->brushes.node_count) return;
    nd=&map->brushes.nodes[node];
    pl=nd->plane;
    if(!pl) return;
    d=q->ctr[0]*pl->normal[0]+q->ctr[1]*pl->normal[1]+q->ctr[2]*pl->normal[2]-pl->dist;
    r=q->half[0]*(pl->normal[0]<0?-pl->normal[0]:pl->normal[0])
     +q->half[1]*(pl->normal[1]<0?-pl->normal[1]:pl->normal[1])
     +q->half[2]*(pl->normal[2]<0?-pl->normal[2]:pl->normal[2]);
    if(d-r>0.0f) { tq_node(q,nd->children[0],depth+1); return; }
    if(d+r<0.0f) { tq_node(q,nd->children[1],depth+1); return; }
    tq_node(q,nd->children[0],depth+1);
    tq_node(q,nd->children[1],depth+1);
}
static int check_treequery(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    tq_t q; float pt[3],height=72.0f;
    unsigned i,zones=0; int status,sep=-1;
    for(i=5;i<(unsigned)argc;++i) if(!strcmp(argv[i],"--")) { sep=(int)i; break; }
    if(sep<0 || argc<sep+4) { printf("treequery: need -- <x> <y> <z> [height]\n"); return 2; }
    zones=(unsigned)sep-5u;
    pt[0]=(float)atof(argv[sep+1]); pt[1]=(float)atof(argv[sep+2]); pt[2]=(float)atof(argv[sep+3]);
    if(argc>sep+4) height=(float)atof(argv[sep+4]);
    memset(&q,0,sizeof q); q.mask=0x2810011;
    q.amin[0]=pt[0]-15.0f; q.amin[1]=pt[1]-15.0f; q.amin[2]=pt[2];
    q.amax[0]=pt[0]+15.0f; q.amax[1]=pt[1]+15.0f; q.amax[2]=pt[2]+height;
    for(i=0;i<3;++i){ q.ctr[i]=(q.amin[i]+q.amax[i])*0.5f; q.half[i]=(q.amax[i]-q.amin[i])*0.5f; }
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),(int)zones,argv[4],NULL,NULL)) {
        printf("Tree query %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1) {
        printf("Tree query %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    q.map=&map;
    /* Lowest brush index claimed by any inline submodel: everything at or above
     * it is brush-entity geometry in model-local coordinates. Submodel 0 is the
     * world, so it is excluded. This only labels the output; it changes no
     * traversal, so it cannot manufacture the answer it is here to check. */
    q.world_brush_split=map.brushes.brush_count;
    for(i=1;i<map.leaves.submodel_count;++i) {
        int bn=map.leaves.submodels[i].leaf.leafBrushNode;
        if(bn>=0 && (unsigned)bn<map.brush_tree.node_count) {
            const codol_collision_brush_node_t *n=&map.brush_tree.nodes[bn];
            if(n->leafBrushCount>0) {
                unsigned k;
                for(k=0;k<(unsigned)n->leafBrushCount;++k)
                    if(n->data.leaf.brushes[k]<q.world_brush_split)
                        q.world_brush_split=n->data.leaf.brushes[k];
            }
        }
    }
    printf("Tree query %s at (%.3f %.3f %.3f) hull z %.1f..%.1f mask 0x%08x\n",
        argv[3],pt[0],pt[1],pt[2],q.amin[2],q.amax[2],(unsigned)q.mask);
    printf("  brushes %u, bsp nodes %u, leaves %u, submodels %u, lowest submodel brush index %u\n",
        map.brushes.brush_count,map.brushes.node_count,map.leaves.leaf_count,
        map.leaves.submodel_count,q.world_brush_split);
    /* Descent self-validation, before any result from it is trusted.
     *
     * A descent that visits too few leaves fails silently: it reports "nothing
     * here", which reads exactly like a real absence of geometry. So: descend
     * with a degenerate point box and check the leaf we land in actually
     * contains the point, and compare against a brute-force scan of every leaf
     * whose bounds contain it. If the descent cannot find the leaf a linear
     * scan finds, every negative result below is void. */
    {
        tq_t pq=q; unsigned brute=0, k; int landed=-1;
        for(i=0;i<3;++i){ pq.amin[i]=pt[i]; pq.amax[i]=pt[i]; pq.ctr[i]=pt[i]; pq.half[i]=0.0f; }
        for(k=0;k<map.leaves.leaf_count;++k) {
            const codol_collision_leaf_t *lf=&map.leaves.leaves[k];
            if(pt[0]<lf->mins[0]||pt[0]>lf->maxs[0]||pt[1]<lf->mins[1]||pt[1]>lf->maxs[1]||
               pt[2]<lf->mins[2]||pt[2]>lf->maxs[2]) continue;
            ++brute; if(landed<0) landed=(int)k;
        }
        {   /* pure point descent, no printing: walk the BSP by hand */
            int node=0,depth=0,leaf=-1;
            while(depth++<256) {
                const codol_collision_node_t *nd;
                const codol_collision_plane_t *pl; float d;
                if(node<0) { leaf=-1-node; break; }
                if((unsigned)node>=map.brushes.node_count) { leaf=-2; break; }
                nd=&map.brushes.nodes[node]; pl=nd->plane;
                if(!pl) { leaf=-3; break; }
                d=pt[0]*pl->normal[0]+pt[1]*pl->normal[1]+pt[2]*pl->normal[2]-pl->dist;
                node=nd->children[d>0.0f?0:1];
            }
            printf("  VALIDATE: point descent -> leaf %d; brute-force leaves containing point: %u"
                   " (first %d)\n",leaf,brute,landed);
            if(leaf>=0 && (unsigned)leaf<map.leaves.leaf_count) {
                const codol_collision_leaf_t *lf=&map.leaves.leaves[leaf];
                int in = !(pt[0]<lf->mins[0]||pt[0]>lf->maxs[0]||pt[1]<lf->mins[1]||
                           pt[1]>lf->maxs[1]||pt[2]<lf->mins[2]||pt[2]>lf->maxs[2]);
                printf("  VALIDATE: leaf %d bounds (%.1f %.1f %.1f)..(%.1f %.1f %.1f) contains point: %s\n",
                    leaf,lf->mins[0],lf->mins[1],lf->mins[2],lf->maxs[0],lf->maxs[1],lf->maxs[2],
                    in?"YES":"NO -- DESCENT IS WRONG, ALL NEGATIVES BELOW ARE VOID");
            }
        }
        (void)pq;
    }
    tq_node(&q,0,0);
    printf("  leaves visited %u, aabb nodes visited %u, BRUSHES CONTAINING HULL %u,"
           " TERRAIN TRIANGLES INTERSECTING HULL %u (of which solid-to-player %u)\n",
        q.leaves,q.aabb_hits,q.brush_hits,q.terr_all,q.terr_hits);
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return 0;
}
/* Topmost-solid profile over an xy grid, using the validated descent.
 *
 * The stance refusal is XY-local: at (-549.0, 1015.2) triangles are overhead
 * and rising is refused; 78 units away at (-529.7, 937.1) every rise is
 * granted. Both report the player at z 100.1. So the question "what is the
 * floor around here" is not rhetorical -- if 100 is the general floor and the
 * snow is a mound on top of it, then 100.1 is a NORMAL standing height for
 * most of this area and only the mound is anomalous. If instead the snow is
 * the floor everywhere and 100 is always the buried clip lid, the player is
 * under the map across the whole region. Those are different bugs.
 *
 * For each sample this reports the highest terrain triangle surface and the
 * highest player-solid brush top, separately, so a mound sitting on a clip
 * lid is visible as two distinct numbers rather than one blended one.
 *
 * argv: --profile <streamdir> <map> <C1.exe> <zone.ff>... -- <x> <y> <half> <step> [zlo] [zhi] */
static int check_profile(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    tq_t q; float cx,cy,half,step,zlo=-64.0f,zhi=400.0f;
    unsigned i,zones=0; int status,sep=-1; float gx,gy;
    for(i=5;i<(unsigned)argc;++i) if(!strcmp(argv[i],"--")) { sep=(int)i; break; }
    if(sep<0 || argc<sep+5) { printf("profile: need -- <x> <y> <half> <step> [zlo] [zhi]\n"); return 2; }
    zones=(unsigned)sep-5u;
    cx=(float)atof(argv[sep+1]); cy=(float)atof(argv[sep+2]);
    half=(float)atof(argv[sep+3]); step=(float)atof(argv[sep+4]);
    if(argc>sep+5) zlo=(float)atof(argv[sep+5]);
    if(argc>sep+6) zhi=(float)atof(argv[sep+6]);
    if(step<=0.0f) return 2;
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),(int)zones,argv[4],NULL,NULL)) {
        printf("Profile %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1) {
        printf("Profile %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    printf("Profile %s around (%.1f %.1f) +-%.0f step %.0f, z %.0f..%.0f\n",
        argv[3],cx,cy,half,step,zlo,zhi);
    printf("  each cell: highest terrain surface / highest player-solid brush top"
           " ('.' = none found)\n");
    for(gy=cy+half; gy>=cy-half; gy-=step) {
        printf("  y %+8.1f :",gy);
        for(gx=cx-half; gx<=cx+half; gx+=step) {
            unsigned k; float bestT=-1e9f,bestB=-1e9f;
            memset(&q,0,sizeof q); q.map=&map; q.mask=0x2814011; q.quiet=1;
            q.amin[0]=gx-2.0f; q.amin[1]=gy-2.0f; q.amin[2]=zlo;
            q.amax[0]=gx+2.0f; q.amax[1]=gy+2.0f; q.amax[2]=zhi;
            for(k=0;k<3;++k){ q.ctr[k]=(q.amin[k]+q.amax[k])*0.5f;
                              q.half[k]=(q.amax[k]-q.amin[k])*0.5f; }
            q.top_terrain=&bestT; q.top_brush=&bestB;
            tq_node(&q,0,0);
            if(bestT>-1e8f) printf(" %6.1f",(double)bestT); else printf("      .");
            if(bestB>-1e8f) printf("/%-6.1f",(double)bestB); else printf("/.     ");
        }
        printf("\n");
    }
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return 0;
}
/* Reachability audit: can a trace reach every terrain triangle we loaded?
 *
 * Collision only ever sees a triangle through leaf -> collAabb root -> aabb
 * tree -> partition -> triangle. A triangle in a partition that no aabb leaf
 * references, or in an aabb subtree no leaf roots, is loaded and correct and
 * completely invisible to every trace -- the player walks onto it on the
 * client and falls through it on the server. That is the exact shape of the
 * reported symptom, and unlike a mask or a normal it is partial by nature:
 * some snow is found, some is not.
 *
 * This marks every partition reachable from every leaf, then reports what is
 * left. It is a pure data audit: no trace, no coordinates, no capture.
 *
 * Pre-registered: unreachable triangles == 0 means this is NOT the defect and
 * the swept path must be pursued in the engine instead. Any nonzero count is a
 * hole in the collision surface, and the triangles it names can be checked
 * against the coordinates the user falls through.
 *
 * argv: --reach <streamdir> <map> <C1.exe> <zone.ff>... */
static void reach_mark(const codol_collision_map_t *map,unsigned ai,
                       unsigned char *part_seen,unsigned char *aabb_seen,
                       unsigned *bad,int depth)
{
    const codol_collision_aabb_t *ab;
    if(depth>64) { ++*bad; return; }
    if(ai>=map->terrain.aabb_count) { ++*bad; return; }
    if(aabb_seen[ai]) return;
    aabb_seen[ai]=1;
    ab=&map->terrain.aabbs[ai];
    if(ab->childCount) {
        unsigned k;
        for(k=0;k<ab->childCount;++k)
            reach_mark(map,(unsigned)ab->index+k,part_seen,aabb_seen,bad,depth+1);
        return;
    }
    if((unsigned)ab->index>=map->terrain.partition_count) { ++*bad; return; }
    part_seen[ab->index]=1;
}
static int check_reach(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    unsigned char *part_seen=NULL,*aabb_seen=NULL,*tri_seen=NULL;
    unsigned i,zones=0,bad=0,lost_parts=0,lost_tris=0,seen_tris=0,shown=0;
    unsigned root_aabbs=0,orphan_aabbs=0;
    int status;
    if(argc<6) return 2;
    zones=(unsigned)argc-5u;
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),(int)zones,argv[4],NULL,NULL)) {
        printf("Reach audit %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1) {
        printf("Reach audit %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    part_seen=calloc(map.terrain.partition_count?map.terrain.partition_count:1,1);
    aabb_seen=calloc(map.terrain.aabb_count?map.terrain.aabb_count:1,1);
    tri_seen=calloc(map.terrain.triangle_count?map.terrain.triangle_count:1,1);
    if(!part_seen||!aabb_seen||!tri_seen) { printf("Reach audit: OOM\n"); goto done; }
    for(i=0;i<map.leaves.leaf_count;++i) {
        const codol_collision_leaf_t *lf=&map.leaves.leaves[i];
        unsigned k;
        for(k=0;k<lf->collAabbCount;++k) {
            ++root_aabbs;
            reach_mark(&map,(unsigned)lf->firstCollAabbIndex+k,part_seen,aabb_seen,&bad,0);
        }
    }
    /* Inline submodels root their own aabbs too. */
    for(i=0;i<map.leaves.submodel_count;++i) {
        const codol_collision_leaf_t *lf=&map.leaves.submodels[i].leaf;
        unsigned k;
        for(k=0;k<lf->collAabbCount;++k) {
            ++root_aabbs;
            reach_mark(&map,(unsigned)lf->firstCollAabbIndex+k,part_seen,aabb_seen,&bad,0);
        }
    }
    for(i=0;i<map.terrain.aabb_count;++i) if(!aabb_seen[i]) ++orphan_aabbs;
    for(i=0;i<map.terrain.partition_count;++i) {
        const codol_collision_partition_t *pa=&map.terrain.partitions[i];
        unsigned t;
        for(t=0;t<pa->triCount;++t) {
            unsigned ti=(unsigned)pa->firstTri+t;
            if(ti>=map.terrain.triangle_count) continue;
            if(part_seen[i]) { if(!tri_seen[ti]) { tri_seen[ti]=1; ++seen_tris; } }
        }
        if(!part_seen[i]) {
            ++lost_parts; lost_tris+=pa->triCount;
            if(shown<40u) {
                printf("  UNREACHABLE partition %u: %u triangles from %d, first tri at"
                       " (%.0f %.0f %.0f)\n",
                    i,(unsigned)pa->triCount,pa->firstTri,
                    (double)map.terrain.vertices[(unsigned)pa->vertBlock*1024u+map.terrain.triangles[pa->firstTri][0]][0],
                    (double)map.terrain.vertices[(unsigned)pa->vertBlock*1024u+map.terrain.triangles[pa->firstTri][0]][1],
                    (double)map.terrain.vertices[(unsigned)pa->vertBlock*1024u+map.terrain.triangles[pa->firstTri][0]][2]);
                ++shown;
            }
        }
    }
    printf("Reach audit %s: leaves %u submodels %u aabbs %u (roots referenced %u,"
           " never visited %u) partitions %u triangles %u\n",
        argv[3],map.leaves.leaf_count,map.leaves.submodel_count,
        map.terrain.aabb_count,root_aabbs,orphan_aabbs,
        map.terrain.partition_count,map.terrain.triangle_count);
    printf("  partitions reachable %u, UNREACHABLE %u; triangles in reachable"
           " partitions %u, in unreachable ones %u; bad references %u\n",
        map.terrain.partition_count-lost_parts,lost_parts,seen_tris,lost_tris,bad);
    /* Partition BORDERS are consumed only by the swept sphere/capsule path
     * (CM_TraceSphereThroughBorder, called from CM_TraceThroughAabbTree_r at
     * _cm_mesh.asm:1949 and :2161). The stationary path never touches them.
     * Since the player trace is a capsule and the reported failure is that a
     * moving player passes through terrain a stationary hull test stops, this
     * is the one input unique to the failing path -- and our reader infers its
     * layout rather than reading it from a spec. The consumer computes
     * z = t*border->zSlope + border->zBase, so zBase/zSlope at +0xc/+0x10 are
     * the fields that matter; distEq must be a usable plane equation. */
    {
        unsigned refs=0,b_nan=0,b_zero=0,b_wild=0,parts_with=0,k;
        for(k=0;k<map.terrain.partition_count;++k) {
            const codol_collision_partition_t *pa=&map.terrain.partitions[k];
            if(pa->borderCount) { ++parts_with; refs+=pa->borderCount; }
        }
        for(k=0;k<map.terrain.border_count;++k) {
            const codol_collision_border_t *bo=&map.terrain.borders[k];
            const float *f=&bo->distEq[0]; unsigned a; int nan=0,wild=0;
            for(a=0;a<7;++a) { float v=f[a]; if(v!=v) nan=1;
                               else if(v>1e9f||v<-1e9f) wild=1; }
            if(nan) ++b_nan; else if(wild) ++b_wild;
            if(bo->distEq[0]==0.0f&&bo->distEq[1]==0.0f&&bo->distEq[2]==0.0f) ++b_zero;
        }
        printf("  borders: %u loaded, %u referenced by %u partitions of %u;"
               " NaN %u, out-of-range %u, zero-plane %u\n",
            map.terrain.border_count,refs,parts_with,map.terrain.partition_count,
            b_nan,b_wild,b_zero);
        if(map.terrain.border_count)
            printf("  border[0]: distEq (%.4f %.4f %.4f) zBase %.3f zSlope %.4f"
                   " start %.3f length %.3f\n",
                map.terrain.borders[0].distEq[0],map.terrain.borders[0].distEq[1],
                map.terrain.borders[0].distEq[2],map.terrain.borders[0].zBase,
                map.terrain.borders[0].zSlope,map.terrain.borders[0].start,
                map.terrain.borders[0].length);
    }
    /* leaf->terrainContents is the gate on the whole terrain phase, in BOTH
     * paths: CM_TraceThroughTree tests `test [esi+0x8], eax` before calling
     * CM_TraceThroughAabbTree (_cm_trace.asm:2169), and CM_Trace does the same
     * before CM_MeshTestInLeaf (:2482). If a leaf's terrainContents is missing
     * a bit that its own terrain materials actually carry, every trace skips
     * that terrain while the geometry sits there looking perfectly valid --
     * and it would be partial, per-leaf, and invisible to every audit that
     * starts from the triangles. Derive the truth from the leaf's own aabb
     * materials and compare. */
    {
        unsigned bad_leaves=0,shown2=0,k;
        for(k=0;k<map.leaves.leaf_count;++k) {
            const codol_collision_leaf_t *lf=&map.leaves.leaves[k];
            int want=0; unsigned q;
            for(q=0;q<lf->collAabbCount;++q) {
                unsigned ai=(unsigned)lf->firstCollAabbIndex+q,mi;
                if(ai>=map.terrain.aabb_count) continue;
                mi=map.terrain.aabbs[ai].materialIndex;
                if(mi<map.materials.count) want|=map.materials.materials[mi].contentFlags;
            }
            if(!want) continue;
            if((want & ~lf->terrainContents)!=0) {
                ++bad_leaves;
                if(shown2<8u) {
                    printf("  LEAF %u terrainContents 0x%08x but its terrain materials"
                           " carry 0x%08x (missing 0x%08x) bounds (%.0f %.0f %.0f)..(%.0f %.0f %.0f)\n",
                        k,(unsigned)lf->terrainContents,(unsigned)want,
                        (unsigned)(want & ~lf->terrainContents),
                        lf->mins[0],lf->mins[1],lf->mins[2],lf->maxs[0],lf->maxs[1],lf->maxs[2]);
                    ++shown2;
                }
            }
        }
        printf("  leaves whose terrainContents omits bits their own terrain has: %u of %u\n",
            bad_leaves,map.leaves.leaf_count);
    }
    /* C1 0x00583e30 reads the partition byte at +0x02 -- which this loader
     * treats as padding -- as a VERTEX BLOCK selector:
     *     movzx esi, byte [ecx+2]
     *     imul  esi, esi, 0x3000        ; 0x3000 = 12288 = 1024 verts * 12
     *     add   esi, [0x24f02dc]        ; cm.verts
     * and uses that as the vertex base for this partition's triangles. If the
     * byte is ever nonzero, every triangle in that partition resolves against
     * the WRONG 1024-vertex block here, and the geometry lands somewhere else
     * entirely -- present, valid, and in the wrong place. */
    {
        unsigned hist[256]; unsigned k,nonzero=0,tris_nonzero=0,maxidx=0,mx=0;
        for(k=0;k<256;++k) hist[k]=0;
        for(k=0;k<map.terrain.partition_count;++k) {
            unsigned blk=map.terrain.partitions[k].borderCount; /* placeholder */
            (void)blk;
        }
        for(k=0;k<map.terrain.triangle_count;++k) {
            unsigned v;
            for(v=0;v<3;++v) if(map.terrain.triangles[k][v]>maxidx)
                maxidx=map.terrain.triangles[k][v];
        }
        mx=maxidx; nonzero=0; tris_nonzero=0;
        {   unsigned char *ref=calloc(map.terrain.vertex_count?map.terrain.vertex_count:1,1);
            unsigned used=0,high=0,v2;
            if(ref) {
                for(k=0;k<map.terrain.triangle_count;++k)
                    for(v2=0;v2<3;++v2) ref[map.terrain.triangles[k][v2]]=1;
                for(k=0;k<map.terrain.vertex_count;++k)
                    if(ref[k]) { ++used; if(k>=65536u) ++high; }
            }
            printf("  triangle vertex indices: max %u; vertices loaded %u;"
                   " referenced %u; referenced at or above 65536: %u\n",
                mx,map.terrain.vertex_count,used,high);
            printf("  UNADDRESSABLE by any u16 index: %u vertices (%.1f%%)%s\n",
                map.terrain.vertex_count>65536u?map.terrain.vertex_count-65536u:0u,
                map.terrain.vertex_count>65536u?
                    100.0*(double)(map.terrain.vertex_count-65536u)/(double)map.terrain.vertex_count:0.0,
                map.terrain.vertex_count>65536u?
                    "  <-- indices MUST be block-relative; C1 adds partition byte+2 * 1024":"");
            free(ref);
        }
    }
    {   /* The block byte itself, now that the loader keeps it. */
        unsigned nz=0,tris=0,maxb=0,k;
        for(k=0;k<map.terrain.partition_count;++k) {
            unsigned b=map.terrain.partitions[k].vertBlock;
            if(b) { ++nz; tris+=map.terrain.partitions[k].triCount; if(b>maxb) maxb=b; }
        }
        printf("  partition vertex-block byte: %u of %u partitions nonzero"
               " (max block %u, covering %u triangles)%s\n",
            nz,map.terrain.partition_count,maxb,tris,
            nz?"  <-- THIS TERRAIN IS RELOCATED IN OUR BUILD":"  (map fits one block)");
    }
    printf("  VERDICT: %s\n", (lost_tris||bad)?
        "HOLES -- terrain exists that no trace can reach":
        "every loaded triangle is reachable; the defect is not reachability");
done:
    free(part_seen); free(aabb_seen); free(tri_seen);
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return 0;
}
/* Do the terrain aabb nodes actually enclose what they contain?
 *
 * Both the position test and the swept test begin with CM_CullBox against
 * aabb->origin +- aabb->halfSize (_cm_mesh.asm:625 and :1643). An aabb that
 * is too SMALL for its triangles produces exactly the asymmetry this bug has
 * shown from the start:
 *
 *   - a position test taken while standing on the triangle is usually inside
 *     the undersized box anyway, so it finds the triangle;
 *   - a sweep approaching from outside can overlap the triangle while missing
 *     the undersized box, get culled, and pass straight through.
 *
 * That is direction-dependent and partial, which is what the evidence keeps
 * saying and what a mask, a normal, a walkable bit and a traversal bug all
 * failed to explain.
 *
 * Checks both relationships the tree depends on:
 *   leaf node      -> its partition's triangles must lie inside its box
 *   interior node  -> its children's boxes must lie inside its box
 *
 * Pre-registered: 0 undersized nodes means the aabb bounds are sound and the
 * swept path must be pursued elsewhere. Any nonzero count is a set of places
 * where geometry is invisible from some approach directions but not others,
 * and the worst offenders can be checked against the drift coordinates.
 *
 * argv: --aabbfit <streamdir> <map> <C1.exe> <zone.ff>... */
static int check_aabbfit(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    unsigned i,zones=0,leaf_bad=0,node_bad=0,leaves=0,nodes=0,shown=0;
    float worst=0.0f; unsigned worst_i=0;
    int status;
    unsigned char *world_reach=NULL;
    unsigned leaf_bad_world=0;
    if(argc<6) return 2;
    zones=(unsigned)argc-5u;
    { int z; for(z=5;z<argc;++z) if(!strcmp(argv[z],"--only")) { zones=(unsigned)z-5u; break; } }
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),(int)zones,argv[4],NULL,NULL)) {
        printf("Aabb fit %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1) {
        printf("Aabb fit %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    /* Which aabbs can a WORLD trace actually reach? Submodel terrain is in
     * model-local coordinates, exactly like the brush tail, so a box that does
     * not enclose globally-addressed triangles is expected there and means
     * nothing. Only world-reachable nodes can affect a player on the map. */
    {
        unsigned char *ps2=calloc(map.terrain.partition_count?map.terrain.partition_count:1,1);
        unsigned bad2=0,k2;
        world_reach=calloc(map.terrain.aabb_count?map.terrain.aabb_count:1,1);
        if(world_reach && ps2)
            for(k2=0;k2<map.leaves.leaf_count;++k2) {
                const codol_collision_leaf_t *lf=&map.leaves.leaves[k2];
                unsigned q2;
                for(q2=0;q2<lf->collAabbCount;++q2)
                    reach_mark(&map,(unsigned)lf->firstCollAabbIndex+q2,ps2,world_reach,&bad2,0);
            }
        free(ps2);
    }
    for(i=0;i<map.terrain.aabb_count;++i) {
        const codol_collision_aabb_t *ab=&map.terrain.aabbs[i];
        float bmin[3],bmax[3],over=0.0f; int have=0; unsigned k,a;
        for(a=0;a<3;++a){ bmin[a]=1e30f; bmax[a]=-1e30f; }
        if(ab->childCount) {
            ++nodes;
            for(k=0;k<ab->childCount;++k) {
                unsigned ci=(unsigned)ab->index+k;
                const codol_collision_aabb_t *cb;
                if(ci>=map.terrain.aabb_count) continue;
                cb=&map.terrain.aabbs[ci];
                for(a=0;a<3;++a) {
                    float lo=cb->origin[a]-cb->halfSize[a],hi=cb->origin[a]+cb->halfSize[a];
                    if(lo<bmin[a]) bmin[a]=lo;
                    if(hi>bmax[a]) bmax[a]=hi;
                }
                have=1;
            }
        } else {
            const codol_collision_partition_t *pa;
            ++leaves;
            if((unsigned)ab->index>=map.terrain.partition_count) continue;
            pa=&map.terrain.partitions[ab->index];
            for(k=0;k<pa->triCount;++k) {
                unsigned ti=(unsigned)pa->firstTri+k,v;
                const uint16_t *idx;
                if(ti>=map.terrain.triangle_count) continue;
                idx=map.terrain.triangles[ti];
                /* u16 indices are relative to the partition's vertex BLOCK
                 * (C1 0x00583e30: cm.verts + vertBlock*0x3000). */
                for(v=0;v<3;++v) for(a=0;a<3;++a) {
                    float z=map.terrain.vertices[(unsigned)pa->vertBlock*1024u+idx[v]][a];
                    if(z<bmin[a]) bmin[a]=z;
                    if(z>bmax[a]) bmax[a]=z;
                }
                have=1;
            }
        }
        if(!have) continue;
        for(a=0;a<3;++a) {
            float lo=ab->origin[a]-ab->halfSize[a],hi=ab->origin[a]+ab->halfSize[a];
            if(bmin[a]<lo && lo-bmin[a]>over) over=lo-bmin[a];
            if(bmax[a]>hi && bmax[a]-hi>over) over=bmax[a]-hi;
        }
        {
            /* Targeted: report these aabbs whether or not they are undersized. */
            int want=0,z;
            for(z=6;z<argc;++z) if((unsigned)atoi(argv[z])==i) want=1;
            if(want)
                printf("  aabb %u (%s): overhang %.3f; box (%.1f %.1f %.1f)+-(%.1f %.1f %.1f)"
                       " contents (%.1f %.1f %.1f)..(%.1f %.1f %.1f)\n",
                    i,ab->childCount?"interior":"leaf",(double)over,
                    ab->origin[0],ab->origin[1],ab->origin[2],
                    ab->halfSize[0],ab->halfSize[1],ab->halfSize[2],
                    bmin[0],bmin[1],bmin[2],bmax[0],bmax[1],bmax[2]);
        }
        if(over>0.001f) {
            if(ab->childCount) ++node_bad;
            else { ++leaf_bad; if(world_reach && world_reach[i]) ++leaf_bad_world; }
            if(over>worst) { worst=over; worst_i=i; }
            if(shown<12u) {
                printf("  UNDERSIZED aabb %u (%s): contents exceed box by %.3f;"
                       " box (%.1f %.1f %.1f)+-(%.1f %.1f %.1f) contents"
                       " (%.1f %.1f %.1f)..(%.1f %.1f %.1f)\n",
                    i,ab->childCount?"interior":"leaf",(double)over,
                    ab->origin[0],ab->origin[1],ab->origin[2],
                    ab->halfSize[0],ab->halfSize[1],ab->halfSize[2],
                    bmin[0],bmin[1],bmin[2],bmax[0],bmax[1],bmax[2]);
                ++shown;
            }
        }
    }
    printf("Aabb fit %s: %u aabbs (%u interior, %u leaf)\n",
        argv[3],map.terrain.aabb_count,nodes,leaves);
    printf("  undersized: %u leaf (%u WORLD-reachable), %u interior;"
           " worst overhang %.3f at aabb %u\n",
        leaf_bad,leaf_bad_world,node_bad,(double)worst,worst_i);
    free(world_reach);
    printf("  VERDICT: %s\n",(leaf_bad||node_bad)?
        "aabb bounds do NOT enclose their contents -- geometry is cullable from"
        " some approach directions":
        "every aabb encloses its contents; culling is not the asymmetry");
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return 0;
}
/* Offline audit of the terrain walkable bit lump.
 *
 * codol_collision_stream.c derives this lump's size as ceil(triCount*3/32)
 * 32-bit words from the TRIANGLE COUNT -- the stream header carries no count of
 * its own for it, only a reference marker -- so a different packing in CoDOL
 * (per-triangle byte, another edge order, a separate count) would leave the
 * array garbage past some point with nothing to catch it. Those bits set
 * trace->walkable on edge and vertex hits, and the ground gate reads it, so
 * wrong bits change which contacts are accepted at triangle seams.
 *
 * Pre-registered (docs/CODOL_UNEVEN_GROUND_FIX_SWEEP.md #3): a PASS is
 * ones-fraction >= 0.8 over the first triCount*3 bits AND no set bits beyond
 * them. A fail is a data bug worth fixing whatever it means for that thread.
 * Needs no server and no capture. */
static int check_walkable(int argc,char **argv)
{
    codol_collision_map_t map={0}; native_collision_counts_t state={0};
    uint64_t bits,words,i,ones=0,tail=0,trans=0,hist[4]={0,0,0,0}; int status,pass;
    /* argv: --walkable <streamdir> <map> <C1.exe> <zone.ff>...
     * The exe is the AES key source for the shipped zones; mounting without it
     * fails, which is why this takes it explicitly rather than passing NULL. */
    if(argc<6) return 2;
    assert(CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if(!CODOL_MountRuntimeArchives((const char *const *)(argv+5),argc-5,argv[4],NULL,NULL)) {
        printf("Walkable audit %s: MOUNT FAILED\n",argv[3]);
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[3],native_collision_model,&state,&map);
    if(status!=1 || !map.terrain.walkable) {
        printf("Walkable audit %s: LOAD FAILED status %d\n",argv[3],status);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
        CODOL_SetStreamModelLoader(NULL,NULL); return 1;
    }
    bits=(uint64_t)map.terrain.triangle_count*3u;
    words=map.terrain.walkable_words;
    for(i=0;i<bits;++i)
        if(map.terrain.walkable[i>>5] & (1u<<(i&31))) ++ones;
    for(i=bits;i<words*32u;++i)
        if(map.terrain.walkable[i>>5] & (1u<<(i&31))) ++tail;
    /* Structure, not just density. A correctly sized and packed array has
     * spatial correlation -- adjacent edges of a triangle usually share
     * walkability -- so the per-triangle edge counts pile up at 0 and 3 and the
     * bit-transition rate sits well under 0.5. Garbage is binomial
     * (1/8,3/8,3/8,1/8) with a transition rate of ~0.5. This is what decides
     * whether a ones-fraction below the pre-registered 0.8 means broken data or
     * simply that 0.8 was the wrong guess. */
    for(i=1;i<bits;++i) {
        unsigned a=(map.terrain.walkable[(i-1)>>5]>>((i-1)&31))&1u;
        unsigned b=(map.terrain.walkable[i>>5]>>(i&31))&1u;
        if(a!=b) ++trans;
    }
    for(i=0;i<map.terrain.triangle_count;++i) {
        unsigned k=0,e;
        for(e=0;e<3;++e) {
            uint64_t bit=(uint64_t)i*3u+e;
            if(map.terrain.walkable[bit>>5] & (1u<<(bit&31))) ++k;
        }
        ++hist[k];
    }
    pass = bits && (double)ones/(double)bits >= 0.8 && tail==0;
    printf("Walkable audit %s: tris %u edges %llu words %llu (derived %llu) "
           "ones %llu (%.4f) padbits-set %llu trans %.4f "
           "edges/tri 0:%llu 1:%llu 2:%llu 3:%llu -> %s\n",
        argv[3],map.terrain.triangle_count,(unsigned long long)bits,
        (unsigned long long)words,(unsigned long long)((bits+31)/32),
        (unsigned long long)ones,bits?(double)ones/(double)bits:0.0,
        (unsigned long long)tail, bits>1?(double)trans/(double)(bits-1):0.0,
        (unsigned long long)hist[0],(unsigned long long)hist[1],
        (unsigned long long)hist[2],(unsigned long long)hist[3],
        pass?"PASS":"FAIL");
    CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives();
    CODOL_SetStreamModelLoader(NULL,NULL);
    return pass?0:1;
}
static int check_mounted_model_corpus(int argc,char **argv)
{
    int path,set=!strcmp(argv[1],"--mounted-set"); unsigned models=0,meshes=0,failed=0,materials=0,physics[2]={0};
    assert(argc>3 && CODOL_SetStreamModelLoader(corpus_stream_loader,argv[2]));
    if (set) assert(CODOL_MountRuntimeArchives((const char *const *)(argv+3),argc-3,NULL,NULL,NULL));
    for (path=3;path<argc;++path) {
        codol_zone_t zone={0}; unsigned index;
        assert(CODOL_OpenZoneFile(&zone,argv[path]));
        if (!set) { const char *paths[]={argv[path]}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
        for (index=0;index<zone.asset_count;++index) {
            codol_asset_t asset; codol_xmodel_skeleton_t skeleton={0},source={0};
            codol_model_block_t views[8];
            codol_native_model_mesh_t mesh={0}; unsigned slot; int status;
            assert(CODOL_ZoneAsset(&zone,index,&asset)); if (asset.type!=4) continue;
            assert(CODOL_ReadXModelSkeleton(&asset,&source));
            assert(CODOL_MountedBlockViews(set ? argc-1-path : 0,views)); views[0]=(codol_model_block_t){0};
            assert(CODOL_RelocateXModelSkeleton(&source,views,&skeleton));
            CODOL_FreeXModelSkeleton(&source); ++models;
            status=CODOL_LoadNativeModelMesh(skeleton.name,&mesh);
            if (status!=1) {
                if (failed<30) fprintf(stderr,"mounted mesh failed: %s asset %u %s status %d\n",argv[path],index,skeleton.name,status);
                if (failed<2) {
                    codol_asset_t lod_assets[4]={{0}}; unsigned lod;
                    assert(CODOL_XModelInlineSurfaceAssets(&asset,lod_assets));
                    for (lod=0;lod<4;++lod) if (lod_assets[lod].data) {
                        codol_model_surfaces_t decoded={0};
                        assert(CODOL_ReadModelSurfaces(lod_assets+lod,&decoded));
                        fprintf(stderr,"  source LOD %u name %s ref %08x count %u\n",lod,
                            decoded.name ? decoded.name : "<pooled>",decoded.name_reference,decoded.count);
                        CODOL_FreeModelSurfaces(&decoded);
                    }
                }
                ++failed;
            } else ++meshes;
            for (slot=0;slot<2;++slot) {
                codol_mounted_model_physics_t dependency;
                int resolved=CODOL_LoadMountedModelPhysics(skeleton.name,slot,&dependency);
                if (resolved<0) fprintf(stderr,"physics failed: %s %s type %u\n",argv[path],skeleton.name,slot);
                assert(resolved>=0);
                if (resolved) {
                    assert(dependency.asset.type==slot && dependency.name && dependency.name[0]!=',');
                    assert(!dependency.blocks[0].data); ++physics[slot];
                    if (!slot) {
                        codol_native_physics_preset_t preset={0};
                        assert(CODOL_BuildNativePhysicsPreset(&dependency,&preset));
                        assert(!strcmp(preset.preset.name,dependency.name));
                        assert(!memcmp(preset.source.extended,dependency.asset.data+40,28));
                        assert(preset.preset.tempDefaultToCylinder==(dependency.asset.data[64]!=0));
                        CODOL_FreeNativePhysicsPreset(&preset);
                    } else {
                        codol_physics_map_t map={0};
                        const codol_physics_map_t *cached=NULL,*again=NULL;
                        assert(CODOL_ReadPhysicsMap(&dependency,&map));
                        assert(!strcmp(map.name,dependency.name));
                        assert(CODOL_LoadMountedPhysicsMap(dependency.name,&cached)==1);
                        assert(CODOL_LoadMountedPhysicsMap(dependency.name,&again)==1 && cached==again);
                        assert(cached->header==map.header && cached->count==map.count);
                        assert(!memcmp(cached->center_of_mass,map.center_of_mass,12));
                        CODOL_FreePhysicsMap(&map);
                    }
                }
            }
            { const codol_xmodel_materials_t *slots;
            codol_native_material_t *native;
            xMaterial_t **handles;
            assert(CODOL_LoadMountedModelMaterials(skeleton.name,&slots)==1);
            native=calloc(slots->count ? slots->count : 1,sizeof(*native));
            handles=calloc(slots->count ? slots->count : 1,sizeof(*handles)); assert(native && handles);
            for (slot=0;slot<slots->count;++slot) {
                codol_mounted_model_material_t material;
                const Material_t *engine,*again;
                status=CODOL_LoadMountedModelMaterialSource(skeleton.name,slot,&material);
                if (status!=1) fprintf(stderr,"material failed: %s asset %u %s slot %u status %d\n",argv[path],index,skeleton.name,slot,status);
                assert(status==1);
                assert(material.asset.type==5 && material.asset.size>=96);
                assert(material.name && *material.name && material.name[0]!=',');
                assert(!material.blocks[0].data && !material.blocks[0].size); ++materials;
                assert(CODOL_BuildNativeMaterial(&material,native+slot));
                assert(!strcmp(native[slot].material.info.name,material.name));
                assert(CODOL_LoadEngineMaterial(material.name,&engine)==1);
                assert(CODOL_LoadEngineMaterial(material.name,&again)==1 && again==engine);
                assert(!strcmp(engine->info.name,material.name));
                handles[slot]=(xMaterial_t *)engine;
            }
            if (status==1 && mesh.lod_count) {
                codol_native_model_core_t core={0}; core.model.name=skeleton.name;
                assert(CODOL_BindNativeModelMesh(&core,&mesh,handles,slots->count));
                for (slot=0;slot<mesh.count;++slot)
                    assert(core.model.materialHandles[slot]==handles[mesh.material_indices[slot]]);
                CODOL_FreeNativeModelCore(&core);
            }
            for (slot=0;slot<slots->count;++slot) CODOL_FreeNativeMaterial(native+slot);
            free(native); free(handles);
            }
            CODOL_FreeNativeModelMesh(&mesh); CODOL_FreeXModelSkeleton(&skeleton);
        }
        if (!set) CODOL_UnmountArchives(); CODOL_CloseZone(&zone);
    }
    if (set) CODOL_UnmountArchives();
    assert(CODOL_SetStreamModelLoader(NULL,NULL));
    printf("Mounted model corpus: %u models, %u meshes, %u materials, %u failures\n",models,meshes,materials,failed);
    printf("Mounted physics dependencies: %u presets, %u collision maps\n",physics[0],physics[1]);
    return failed ? 1 : 0;
}
static int check_mounted_collision(int argc,char **argv)
{
    codol_collision_map_t map={0}; size_t failed=0; unsigned asset=0;
    int status; collision_model_counts_t counts={0};
    if (argc<4) return 2;
    if (!CODOL_MountRuntimeArchives((const char *const *)(argv+3),argc-3,NULL,&failed,&asset)) {
        fprintf(stderr,"Collision mount failed: path %zu, asset %u\n",failed,asset); return 1;
    }
    status=CODOL_LoadMountedCollisionModels(argv[2],count_collision_model_name,&counts,&map);
    printf("Mounted collision %s: status %d, %u materials (%u unresolved), %u static models (%u unresolved), %u brushes, %u leaves\n",
        argv[2],status,map.materials.count,map.materials.unresolved,map.static_models.count,
        map.static_models.unresolved,map.brushes.brush_count,map.leaves.leaf_count);
    printf("Static-model aliases: %u names, %u skeletons, %u geometry sets / %u (native binding not performed)\n",
        counts.names,counts.skeletons,counts.geometry,map.static_models.count);
    if (counts.names!=map.static_models.count) {
        unsigned i;
        for (i=0;i<map.static_models.count && i<8;++i)
            printf("  static model %u reference 0x%08x\n",i,map.static_models.model_references[i]);
    }
    CODOL_UnmountArchives();
    /* Collision staging owns its data independently of archive lifetime. */
    if (status==1 && map.materials.count) assert(map.materials.materials[0].material[0]);
    status=status==1 && !map.materials.unresolved && counts.geometry==map.static_models.count ? 0 : 1;
    CODOL_FreeCollisionMap(&map); return status;
}
static int check_dynamic_corpus(int argc,char **argv)
{
    unsigned maps=0,totals[2]={0},types[3]={0}; int path;
    for(path=2;path<argc;++path) {
        codol_zone_t zone={0}; codol_load_blocks_t blocks={0}; unsigned i;
        if(!CODOL_OpenZoneFile(&zone,argv[path]) || !CODOL_ReplayZone(&zone,&blocks,NULL)) {
            fprintf(stderr,"dynamic replay failed: %s\n",argv[path]);
            CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone); return 1;
        }
        for(i=0;i<zone.asset_count;++i) {
            codol_asset_t asset; codol_dynamic_entities_t entities={0};
            assert(CODOL_ZoneAsset(&zone,i,&asset));
            if(asset.type!=14 && asset.type!=15) continue;
            if(!CODOL_ReadDynamicEntities(&asset,&blocks,&entities)) {
                fprintf(stderr,"dynamic decode failed: %s asset %u\n",argv[path],i);
                CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone); return 1;
            }
            printf("dynamic entities: %s asset %u: %u/%u\n",argv[path],i,entities.count[0],entities.count[1]);
            ++maps; totals[0]+=entities.count[0]; totals[1]+=entities.count[1];
            {
                unsigned category,index;
                for(category=0;category<2;++category) for(index=0;index<entities.count[category];++index) {
                    uint32_t type=entities.entities[category][index].type;
                    ++types[type==1 ? 0 : type==2 ? 1 : 2];
                }
            }
            CODOL_FreeDynamicEntities(&entities);
        }
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
    }
    printf("PASS: %u collision assets, %u/%u owned dynamic definitions\n",maps,totals[0],totals[1]);
    printf("dynamic types: %u clutter, %u destructible, %u unsupported\n",types[0],types[1],types[2]);
    return maps ? 0 : 1;
}
static int check_effect_sources(int argc,char **argv)
{
    unsigned effects=0,elements=0,stubs=0; int path;
    for(path=2;path<argc;++path) {
        codol_zone_t zone={0}; codol_load_blocks_t replay={0}; codol_model_block_t blocks[8]; unsigned i;
        assert(CODOL_OpenZoneFile(&zone,argv[path]) && CODOL_ReplayZone(&zone,&replay,NULL));
        CODOL_LoadBlockViews(&replay,blocks); blocks[0]=(codol_model_block_t){0};
        for(i=0;i<zone.asset_count;++i) {
            codol_asset_t asset; codol_effect_source_t source={0}; uint32_t ref; const char *name;
            assert(CODOL_ZoneAsset(&zone,i,&asset)); if(asset.type!=30) continue;
            assert(asset.size>=32); memcpy(&ref,asset.data,4);
            name=ref==UINT32_MAX ? (const char *)asset.data+32 : CODOL_LoadBlockString(&replay,ref);
            if(name && *name==',') { ++stubs; continue; }
            if(!CODOL_ReadEffectSource(&asset,blocks,&source)) {
                fprintf(stderr,"effect decode failed: %s asset %u (%s)\n",argv[path],i,name ? name : "unresolved name");
                CODOL_FreeLoadBlocks(&replay); CODOL_CloseZone(&zone); return 1;
            }
            ++effects; elements+=source.prefix.count; CODOL_FreeEffectSource(&source);
        }
        CODOL_FreeLoadBlocks(&replay); CODOL_CloseZone(&zone);
    }
    printf("PASS: %u complete effect sources, %u elements; %u name-only references\n",effects,elements,stubs);
    return effects ? 0 : 1;
}
static int check_dynamic_effects(int argc,char **argv)
{
    codol_dynamic_entities_t entities={0}; unsigned category,index,effects=0,models=0,materials=0;
    if(argc<4 || !CODOL_MountRuntimeArchives((const char *const *)argv+3,argc-3,NULL,NULL,NULL) ||
        CODOL_LoadMountedDynamicEntities(argv[2],&entities)!=1) { CODOL_UnmountArchives(); return 1; }
    for(category=0;category<2;++category) for(index=0;index<entities.count[category];++index) {
        codol_dynamic_dependency_t dependency; codol_effect_prefix_t prefix; const codol_effect_source_t *source; unsigned i;
        int status=CODOL_LoadMountedDynamicDependency(argv[2],category,index,30,&dependency);
        if(!status) continue;
        assert(status==1 && CODOL_LoadMountedEffectSource(dependency.name,&source)==1); prefix=source->prefix;
        printf("effect %u/%u %s: counts %u/%u/%u flags %08x; elements",category,index,prefix.name,
            prefix.counts[0],prefix.counts[1],prefix.counts[2],prefix.flags);
        for(i=0;i<prefix.count;++i) {
            const uint8_t *e=prefix.elements+260*i;
            unsigned j;
            printf(" %u(v%u,samples%u/%u,ext%u)",e[176],e[177],source->elements[i].velocity_count,
                source->elements[i].visual_sample_count,source->elements[i].extension_size);
            printf(" extra252=%02x%02x%02x%02x extraName=%s",e[255],e[254],e[253],e[252],
                source->elements[i].extra_name ? source->elements[i].extra_name : "<none>");
            for(j=0;j<3;++j) if(source->elements[i].effect_names[j])
                printf(" child%u=%s",j,source->elements[i].effect_names[j]);
            for(j=0;j<source->elements[i].visual_count;++j) {
                codol_effect_visual_source_t visual;
                int ready=CODOL_LoadMountedEffectVisual(dependency.name,i,j,&visual);
                if(ready<0) fprintf(stderr,"effect visual unresolved: %s element %u visual %u\n",dependency.name,i,j);
                assert(ready>=0);
                if(ready==1) { if(visual.asset.type==4) ++models; else { assert(visual.asset.type==5); ++materials; } }
            }
        }
        putchar('\n'); ++effects;
    }
    CODOL_FreeDynamicEntities(&entities); CODOL_UnmountArchives();
    printf("PASS: %u cached dynamic effect sources, %u model and %u material visuals resolved\n",effects,models,materials); return 0;
}
int main(int argc,char **argv)
{
    {
        uint8_t data[4096]={0}; size_t pos=72+0xbfc,point_at; unsigned i;
        char path[]="/tmp/codol-weapon-tail-XXXXXX"; const char *paths[]={path};
        codol_weapon_tail_t tail={0},saved; int fd; FILE *file;
        put32(data+8,8192); put32(data+20,8192); put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,28); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); memcpy(data+pos,"w",2); pos+=2;
        put32(data+72+0x9a0,UINT32_MAX); memcpy(data+pos,"g",2); pos+=2;
        data[72+0xbb0]=1; data[72+0xbb2]=1;
        put32(data+72+0x9a8,UINT32_MAX); point_at=pos; put32(data+pos,0x3f800000); put32(data+pos+4,0x40000000); pos+=8;
        put32(data+72+0x9a4,UINT32_MAX); memcpy(data+pos,"h",2); pos+=2;
        put32(data+72+0x9ac,UINT32_MAX); pos+=8;
        put32(data+72+0xaa8,UINT32_MAX); put32(data+pos,UINT32_MAX); pos+=112; memcpy(data+pos,"t",2); pos+=2;
        put32(data+72+0xac4,UINT32_MAX); put32(data+pos,UINT32_MAX); pos+=4; memcpy(data+pos,"s",2); pos+=2;
        put32(data+72+0xbb4,UINT32_MAX); put32(data+72+0xbb8,UINT32_MAX); pos+=16;
        put32(data,(uint32_t)pos-40); put32(data+68,(uint32_t)pos-72);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,pos,file)==pos && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponTail("w",&tail)==1 && tail.dependency_offset==pos-72);
        for(i=0;i<tail.count;++i) {
            const codol_weapon_dependency_t *entry=tail.entries+i;
            if(entry->offset==0xaa8) assert(entry->asset.type==40 && entry->asset.size==114 && !strcmp(entry->name,"t"));
            if(entry->offset==0xac4) assert(!strcmp(entry->name,"s"));
            if(entry->offset==0x9a8) assert(entry->point_count==1 && entry->points[3]==0x3f);
            if(entry->offset==0x9a0) assert(!strcmp(entry->name,"g"));
            if(entry->offset==0x9a4) assert(!strcmp(entry->name,"h"));
        }
        saved=tail;
        assert(CODOL_LoadMountedWeaponTail("missing",&tail)==0 && !memcmp(&tail,&saved,sizeof(tail)));
        put32(data+point_at,0x7fc00000); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,pos,file)==pos && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponTail("w",&tail)==-1 && !memcmp(&tail,&saved,sizeof(tail)));
        for(i=0;i<saved.count;++i) if(saved.entries[i].offset==0xaa8) assert(!strcmp(saved.entries[i].name,"t"));
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    if(argc>1 && !strcmp(argv[1],"--effect-sources")) return check_effect_sources(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--dynamic-effects")) return check_dynamic_effects(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--dynamic-entities")) return check_dynamic_corpus(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--native-collision")) return check_native_collision(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--walkable")) return check_walkable(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--contents")) return check_contents(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--treequery")) return check_treequery(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--profile")) return check_profile(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--reach")) return check_reach(argc,argv);
    if(argc>1 && !strcmp(argv[1],"--aabbfit")) return check_aabbfit(argc,argv);
    if (argc>1 && !strcmp(argv[1],"--mounted-collision")) return check_mounted_collision(argc,argv);
    if (argc>1 && (!strcmp(argv[1],"--mounted") || !strcmp(argv[1],"--mounted-set"))) return check_mounted_model_corpus(argc,argv);
    if (argc>1 && !strcmp(argv[1],"--stream")) return check_stream_corpus(argc,argv);
    if (argc>1) return check_surface_corpus(argc,argv);
    {
        uint8_t data[72+0xbfc+2+362+5]={0},patch[434]={0};
        char path[]="/tmp/codol-weapon-model-XXXXXX",update[]="/tmp/codol-weapon-model-patch-XXXXXX";
        const char *paths[]={path},*updates[]={update}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_weapon_model_t first={0},same={0},newer={0}; size_t i; uint32_t alias=0; int fd; FILE *file;
        codol_weapon_animations_t animations={0},saved_animations;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,28); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        put32(data+72+0x10,UINT32_MAX-1); put32(data+72+0x1c,0x40000001);
        memcpy(data+72+0xbfc,"w",2); put32(data+72+0xbfc+2,UINT32_MAX);
        data[72+0xbfc+2+0x12a]=255; memcpy(data+sizeof(data)-7,"m",2);
        put32(data+72+0x7c,UINT32_MAX); memcpy(data+sizeof(data)-5,"idle",5);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i<blocks.asset_alias_count;++i)
            if(blocks.asset_aliases[i].asset.type==4 && blocks.asset_aliases[i].reference) alias=blocks.asset_aliases[i].reference;
        assert(alias); CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        put32(data+72+0x14,alias);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponModel("w",0,&first)==1 && !strcmp(first.name,"m"));
        assert(CODOL_LoadMountedWeaponModel("W",1,&same)==1 && same.asset.data==first.asset.data);
        assert(CODOL_LoadMountedWeaponModel("w",2,&same)==0 && same.asset.data==first.asset.data);
        assert(CODOL_LoadMountedWeaponModel("w",3,&same)==-1 && same.asset.data==first.asset.data);
        assert(CODOL_LoadMountedWeaponModel("w",11,&same)==-1 && same.asset.data==first.asset.data);
        assert(CODOL_LoadMountedWeaponAnimations("w",&animations)==1 && !strcmp(animations.names[0],"idle"));
        assert(!animations.names[143] && animations.dependency_offset==sizeof(data)-72); saved_animations=animations;
        assert(CODOL_LoadMountedWeaponAnimations("absent",&animations)==0 && !memcmp(&animations,&saved_animations,sizeof(animations)));
        put32(patch,sizeof(patch)-40); put32(patch+8,8192); put32(patch+20,8192);
        put32(patch+48,1); put32(patch+52,UINT32_MAX); put32(patch+56,4); put32(patch+60,32);
        put32(patch+64,UINT32_MAX); put32(patch+68,362); put32(patch+72,UINT32_MAX);
        patch[72+0x12a]=255; put32(patch+72+0x13c,0x40000000); memcpy(patch+432,"m",2);
        fd=mkstemp(update); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(updates,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponModel("w",0,&newer)==1 && newer.asset.data!=first.asset.data);
        assert(CODOL_LoadMountedWeaponModel("w",1,&same)==1 && same.asset.data==newer.asset.data);
        assert(!strcmp(first.name,"m"));
        /* Bad final animation reference must not replace the previous view. */
        put32(data+72+0x7c+4*143,0x40000001); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponAnimations("w",&animations)==-1 && !memcmp(&animations,&saved_animations,sizeof(animations)));
        put32(data+72+0x7c+4*143,UINT32_MAX);
        /* Reuse the inline final string by moving it from the first slot. */
        put32(data+72+0x7c,0); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponAnimations("w",&animations)==1 && !animations.names[0] && !strcmp(animations.names[143],"idle"));
        assert(!strcmp(saved_animations.names[0],"idle"));
        assert(!unlink(path) && !unlink(update)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[72+0xbfc+2+34]={0},patch[106]={0};
        char path[]="/tmp/codol-weapon-fx-XXXXXX",update[]="/tmp/codol-weapon-fx-patch-XXXXXX";
        const char *paths[]={path},*updates[]={update}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_weapon_effects_t first={0},same={0},saved; size_t i; uint32_t alias=0; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,28); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        memcpy(data+72+0xbfc,"w",2); put32(data+72+0x35c,UINT32_MAX-1);
        put32(data+72+0xbfc+2,UINT32_MAX); memcpy(data+sizeof(data)-2,"f",2);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i<blocks.asset_alias_count;++i)
            if(blocks.asset_aliases[i].asset.type==30 && blocks.asset_aliases[i].reference) alias=blocks.asset_aliases[i].reference;
        assert(alias); CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone); put32(data+72+0x360,alias);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponEffects("w",&first)==1 && !strcmp(first.names[0],"f"));
        assert(first.assets[0].data==first.assets[1].data && first.dependency_offset==sizeof(data)-72);
        same=first; assert(CODOL_LoadMountedWeaponEffects("absent",&same)==0 && !memcmp(&same,&first,sizeof(first)));
        put32(patch,sizeof(patch)-40); put32(patch+8,8192); put32(patch+20,8192);
        put32(patch+48,1); put32(patch+52,UINT32_MAX); put32(patch+56,30); put32(patch+60,32);
        put32(patch+64,UINT32_MAX); put32(patch+68,34); put32(patch+72,UINT32_MAX);
        put32(patch+76,9); memcpy(patch+104,"f",2);
        fd=mkstemp(update); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(updates,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponEffects("W",&same)==1 && same.assets[0].data!=first.assets[0].data);
        assert(same.assets[0].data==same.assets[1].data && same.assets[0].data[4]==9);
        assert(same.dependency_offset==first.dependency_offset && !strcmp(first.names[0],"f")); saved=same;
        put32(data+72+0x360,0x40000001); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponEffects("w",&same)==-1 && !memcmp(&same,&saved,sizeof(same)));
        put32(data+72+0x360,0); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponEffects("w",&same)==1 && same.names[0] && !same.names[1]);
        assert(!same.assets[1].data && !strcmp(saved.names[1],"f"));
        assert(!unlink(path) && !unlink(update)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[72+0xbfc+2+4+6]={0};
        char path[]="/tmp/codol-weapon-sounds-XXXXXX"; const char *paths[]={path};
        codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_weapon_sounds_t sounds={0},saved; size_t i; uint32_t alias=0; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,28); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        memcpy(data+72+0xbfc,"w",2); put32(data+72+0x364,UINT32_MAX);
        put32(data+sizeof(data)-10,UINT32_MAX); memcpy(data+sizeof(data)-6,"sound",6);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=4;i+6<=blocks.written[3];++i)
            if(!memcmp(blocks.data[3]+i,"sound",6)) { alias=0x30000001u+(uint32_t)i-4; break; }
        assert(alias); CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        put32(data+72+0x434,alias);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponSounds("w",&sounds)==1 && !strcmp(sounds.names[0],"sound"));
        assert(!strcmp(sounds.names[52],"sound") && !sounds.names[1] && sounds.dependency_offset==sizeof(data)-72); saved=sounds;
        assert(CODOL_LoadMountedWeaponSounds("absent",&sounds)==0 && !memcmp(&sounds,&saved,sizeof(saved)));
        put32(data+72+0x434,0x40000001); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponSounds("w",&sounds)==-1 && !memcmp(&sounds,&saved,sizeof(saved)));
        put32(data+72+0x434,0); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponSounds("w",&sounds)==1 && !sounds.names[52]);
        assert(!strcmp(saved.names[52],"sound"));
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[72+0xbfc+2+124+13]={0};
        const size_t start=72+0xbfc+2;
        char path[]="/tmp/codol-weapon-sound-arrays-XXXXXX"; const char *paths[]={path};
        codol_zone_t zone={0}; codol_load_blocks_t blocks={0}; codol_weapon_sounds_t sounds={0},saved;
        uint32_t alias=0; size_t i; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,28); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        memcpy(data+72+0xbfc,"w",2); put32(data+72+0x438,UINT32_MAX);
        put32(data+start,UINT32_MAX); put32(data+start+120,UINT32_MAX);
        put32(data+start+124,UINT32_MAX); memcpy(data+start+128,"a",2);
        put32(data+start+130,UINT32_MAX); memcpy(data+start+134,"bb",3);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i+124<=blocks.written[3];i+=4)
            if(!memcmp(blocks.data[3]+i,data+start,124)) { alias=0x30000001u+(uint32_t)i; break; }
        assert(alias); CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        put32(data+72+0x43c,alias);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponSounds("w",&sounds)==1);
        for(i=0;i<2;++i) {
            assert(!strcmp(sounds.arrays[i][0],"a") && !strcmp(sounds.arrays[i][30],"bb"));
            assert(!sounds.arrays[i][1]);
        }
        assert(sounds.dependency_offset==sizeof(data)-72); saved=sounds;
        put32(data+72+0x43c,0x3ffffffd); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponSounds("w",&sounds)==-1 && !memcmp(&sounds,&saved,sizeof(saved)));
        assert(!strcmp(saved.arrays[1][30],"bb"));
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[72+0xbfc+2+34+98+14]={0}; const size_t fx=72+0xbfc+2,material=fx+34;
        char path[]="/tmp/codol-weapon-ammo-names-XXXXXX"; const char *paths[]={path};
        codol_zone_t zone={0}; codol_load_blocks_t blocks={0}; codol_weapon_ammo_names_t names={0},saved;
        codol_weapon_visuals_t visuals={0},old_visuals;
        uint32_t alias=0; size_t i; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,28); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        memcpy(data+72+0xbfc,"w",2); put32(data+72+0x440,UINT32_MAX);
        put32(data+fx,UINT32_MAX); memcpy(data+fx+32,"f",2);
        put32(data+72+0x450,UINT32_MAX-1); put32(data+material,UINT32_MAX); memcpy(data+material+96,"m",2);
        put32(data+72+0x564,UINT32_MAX); put32(data+72+0x56c,UINT32_MAX); put32(data+72+0x57c,UINT32_MAX);
        memcpy(data+sizeof(data)-14,"ammo\0clip\0cap",14);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i<blocks.asset_alias_count;++i)
            if(blocks.asset_aliases[i].asset.type==5 && blocks.asset_aliases[i].reference) alias=blocks.asset_aliases[i].reference;
        assert(alias); CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone); put32(data+72+0x454,alias);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponAmmoNames("w",&names)==1);
        assert(CODOL_LoadMountedWeaponVisuals("w",&visuals)==1);
        assert(visuals.entries[0].offset==0x440 && visuals.entries[0].asset.type==30 && !strcmp(visuals.entries[0].name,"f"));
        assert(!visuals.entries[1].asset.data && visuals.entries[1].offset==0x444);
        assert(visuals.entries[4].offset==0x450 && !strcmp(visuals.entries[4].name,"m"));
        assert(visuals.entries[4].asset.data==visuals.entries[5].asset.data);
        assert(visuals.entries[13].offset==0x550 && visuals.dependency_offset==sizeof(data)-72-14);
        old_visuals=visuals;
        assert(CODOL_LoadMountedWeaponVisuals("absent",&visuals)==0 && !memcmp(&visuals,&old_visuals,sizeof(visuals)));
        assert(!strcmp(names.ammo,"ammo") && !strcmp(names.clip,"clip") && !strcmp(names.shared_cap,"cap"));
        assert(names.dependency_offset==sizeof(data)-72); saved=names;
        assert(CODOL_LoadMountedWeaponAmmoNames("absent",&names)==0 && !memcmp(&names,&saved,sizeof(saved)));
        put32(data+72+0x57c,0x40000001);
        /* Remove the no-longer-inline shared-cap bytes so replay remains exact. */
        put32(data,sizeof(data)-44); put32(data+68,sizeof(data)-76);
        file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data)-4,file)==sizeof(data)-4 && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponAmmoNames("w",&names)==-1 && !memcmp(&names,&saved,sizeof(saved)));
        assert(!strcmp(saved.shared_cap,"cap"));
        assert(CODOL_LoadMountedWeaponVisuals("w",&visuals)==1); /* Independent of invalid later strings. */
        put32(data+72+0x454,0x40000001); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data)-4,file)==sizeof(data)-4 && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        visuals=old_visuals;
        assert(CODOL_LoadMountedWeaponVisuals("w",&visuals)==-1 && !memcmp(&visuals,&old_visuals,sizeof(visuals)));
        assert(!strcmp(old_visuals.entries[4].name,"m"));
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        codol_mounted_xanim_t first={0},current={0}; unsigned width;
        for(width=1;width<=2;++width) {
            uint8_t data[512]={0}; size_t pos=162,delta,quat,i; unsigned counts[]={4,6,8,32,10,12},sizes[]={1,2,4,2,1,4};
            char path[]="/tmp/codol-xanim-source-XXXXXX"; const char *paths[]={path}; int fd; FILE *file;
            put32(data+8,8192); put32(data+20,8192); put32(data+48,1); put32(data+52,UINT32_MAX);
            put32(data+56,2); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+72,UINT32_MAX);
            data[160]='a'; data[72+14]=width==1 ? 255 : 0; data[72+15]=width==2;
            data[72+27]=1; put32(data+72+80,UINT32_MAX); pos+=8;
            put32(data+72+84,UINT32_MAX); delta=pos; pos+=12;
            for(i=0;i<3;++i) put32(data+delta+4*i,UINT32_MAX);
            /* Constant translation, animated two-component rotation, constant
             * four-component rotation. The third track must remain present. */
            pos+=4; data[pos]=11; pos+=12;
            data[pos]=1; pos+=4; put32(data+pos,UINT32_MAX); pos+=4;
            data[pos+width]=1; pos+=2*width; quat=pos; memset(data+pos,33,8); pos+=8;
            pos+=4; memset(data+pos,77,8); pos+=8;
            for(i=0;i<6;++i) { put32(data+72+52+4*i,UINT32_MAX); data[72+counts[i]]=1; memset(data+pos,40+i,sizes[i]); pos+=sizes[i]; }
            put32(data+72+76,UINT32_MAX); put32(data+72+36,2); data[pos+width]=1; pos+=2*width;
            put32(data,pos-40); put32(data+68,pos-72);
            fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(data,1,pos,file)==pos && !fclose(file));
            assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
            assert(CODOL_LoadMountedXAnim("A",&current)==1 && !strcmp(current.name,"a"));
            assert(current.index_width==width && current.notify_count==1 && current.notifies);
            assert(current.tracks[0].frames[0]==11 && current.tracks[1].count==1);
            assert(current.tracks[1].frames==current.asset.data+quat-72 && current.tracks[1].indices[width]==1);
            assert(current.tracks[2].frames[0]==77 && current.tracks[2].frame_stride==8);
            for(i=0;i<6;++i) assert(current.stream_counts[i]==1 && current.streams[i][0]==40+i);
            assert(current.index_count==2 && current.indices[width]==1);
            if(width==1) first=current;
            else assert(first.asset.data!=current.asset.data && first.tracks[2].frames[0]==77);
            assert(!unlink(path));
        }
        first=current;
        assert(CODOL_LoadMountedXAnim("missing",&current)==0 && !memcmp(&first,&current,sizeof(first)));
        assert(CODOL_LoadMountedXAnim(NULL,&current)==-1 && !memcmp(&first,&current,sizeof(first)));
        CODOL_UnmountArchives();
    }
    {
        uint8_t data[188]={0}; char path[]="/tmp/codol-xanim-handles-XXXXXX"; const char *paths[]={path};
        bone_string_test_t state={0},other={0}; codol_xanim_handles_t sentinel={0};
        const struct XAnimParts *native=NULL,*native_first,*native_other=NULL;
        const codol_xanim_handles_t *handles=&sentinel,*first; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+40,2); put32(data+44,UINT32_MAX); put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,UINT32_MAX); put32(data+60,UINT32_MAX); memcpy(data+64,"tag\0tag",8);
        put32(data+72,2); put32(data+76,48); put32(data+80,UINT32_MAX); put32(data+84,100);
        put32(data+88,UINT32_MAX); data[88+26]=1; data[88+27]=1;
        put32(data+88+48,UINT32_MAX); put32(data+88+80,UINT32_MAX); data[176]='a'; data[180]=1;
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        state.fail_at=2;
        assert(CODOL_BindMountedXAnimHandles("a",test_acquire_bone,test_release_bone,&state,&handles)==-1);
        assert(handles==&sentinel && state.calls==2 && state.releases==1 && !state.live);
        state.calls=0; state.overflow=1;
        assert(CODOL_BindMountedXAnimHandles("a",test_acquire_bone,test_release_bone,&state,&handles)==-1);
        assert(handles==&sentinel && state.releases==3 && !state.live);
        state.fail_at=0;
        assert(CODOL_BindMountedXAnimHandles("a",test_acquire_bone,test_release_bone,&state,&handles)==1); first=handles;
        assert(handles->bone_count==1 && handles->notify_count==1 && handles->bones[0]==33 && handles->notifies[0]==33 && state.live==2);
        assert(CODOL_BindMountedXAnimHandles("A",test_acquire_bone,test_release_bone,&state,&handles)==1 && handles==first && state.calls==4);
        assert(CODOL_BindMountedXAnimHandles("a",test_acquire_bone,test_release_bone,&other,&handles)==1 && handles!=first && other.live==2);
        assert(CODOL_LoadMountedNativeXAnim("a",test_acquire_bone,test_release_bone,&state,&native)==1 && native);
        native_first=native;
        assert(CODOL_LoadMountedNativeXAnim("A",test_acquire_bone,test_release_bone,&state,&native)==1 && native==native_first && state.calls==4);
        assert(CODOL_LoadMountedNativeXAnim("a",test_acquire_bone,test_release_bone,&other,&native_other)==1 && native_other!=native_first && other.calls==2);
        assert(CODOL_LoadMountedNativeXAnim("missing",test_acquire_bone,test_release_bone,&state,&native)==0 && native==native_first);
        data[180]=2; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        handles=first;
        assert(CODOL_BindMountedXAnimHandles("a",test_acquire_bone,test_release_bone,&state,&handles)==-1 && handles==first && state.calls==4);
        assert(first->notifies[0]==33 && state.live==2);
        assert(CODOL_LoadMountedNativeXAnim("a",test_acquire_bone,test_release_bone,&state,&native)==-1 && native==native_first && state.calls==4);
        assert(((const unsigned char *)native_first)[27]==1); /* Retired native header remains alive. */
        data[180]=1; data[88+16]=1; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedNativeXAnim("a",test_acquire_bone,test_release_bone,&state,&native)==1 && native!=native_first);
        assert(((const unsigned char *)native)[16]==1 && ((const unsigned char *)native_first)[16]==0 && state.live==4);
        assert(!unlink(path)); CODOL_UnmountArchives();
        /* Unmount frees the native animation and archive. Its string handles
         * are retained because a later script-string generation may have
         * reused their numeric IDs; releasing one could free a new owner. */
        assert(state.live==4 && state.releases==3 && other.live==2 && other.releases==0);
    }
    {
        unsigned variant;
        for(variant=0;variant<2;++variant) {
        char name[17]={0}; strcpy(name,variant ? "m4_mp" : "defaultweapon_mp");
        uint8_t data[72+0xbfc+sizeof(name)]={0}; char path[]="/tmp/codol-default-weapon-XXXXXX";
        const char *paths[]={path}; const struct WeaponDef *first=NULL,*again=NULL;
        int fd; FILE *file; size_t size=72+0xbfc+strlen(name)+1;
        put32(data,size-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,28); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,size-72);
        put32(data+72,UINT32_MAX); data[72+0x588]=31;
        memcpy(data+72+0xbfc,name,sizeof(name));
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,size,file)==size && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        default_weapon_build_calls=0; default_weapon_build_fail=1;
        assert(CODOL_LoadMountedNativeWeapon(name,test_build_default_weapon,&first)==-1 && !first);
        default_weapon_build_fail=0;
        assert(CODOL_LoadMountedNativeWeapon(name,test_build_default_weapon,&first)==1 && first->damage==31);
        { int value=91; assert(CODOL_GetNativeWeaponInheritsPerks(first,&value) && value==0);
          assert(!CODOL_GetNativeWeaponInheritsPerks(NULL,&value) && value==0); }
        { int value=91; assert(CODOL_GetNativeWeaponLockWarningGate(first,&value) && value==0);
          assert(!CODOL_GetNativeWeaponLockWarningGate(NULL,&value) && value==0); }
        assert(default_weapon_build_calls==2);
        assert(CODOL_LoadMountedNativeWeapon(variant ? "M4_MP" : "DEFAULTWEAPON_MP",test_build_default_weapon,&again)==1 && again==first);
        assert(CODOL_LoadMountedDefaultWeapon("other",test_build_default_weapon,&again)==0 && again==first);
        assert(default_weapon_build_calls==2);
        data[72+0x588]=42; data[72+0xbc2]=1; data[72+0xbbd]=1; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,size,file)==size && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedNativeWeapon(name,test_build_default_weapon,&again)==1 && again!=first);
        assert(again->damage==42 && first->damage==31 && !strcmp(first->szInternalName,name));
        { int value=-1; assert(CODOL_GetNativeWeaponInheritsPerks(again,&value) && value==1);
          assert(CODOL_GetNativeWeaponInheritsPerks(first,&value) && value==0); }
        { int value=-1; assert(CODOL_GetNativeWeaponLockWarningGate(again,&value) && value==1);
          assert(CODOL_GetNativeWeaponLockWarningGate(first,&value) && value==0); }
        assert(default_weapon_build_calls==3);
        assert(!unlink(path)); CODOL_UnmountArchives();
        }
    }
    {
        static const char strings[]="none\0noweapon.accu\0noweapon.accu";
        uint8_t data[72+0xbfc+sizeof(strings)]={0}; char path[]="/tmp/codol-null-weapon-XXXXXX";
        const char *paths[]={path}; const struct WeaponDef *first=NULL,*again=NULL;
        int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,28); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72);
        put32(data+72,UINT32_MAX); put32(data+72+0x678,0x3fe00000);
        put32(data+72+0x9a0,UINT32_MAX); put32(data+72+0x9a4,UINT32_MAX);
        memcpy(data+72+0xbfc,strings,sizeof(strings));
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedNullWeapon("none",&first)==1 && first && !strcmp(first->szInternalName,"none"));
        assert(first->sprintDurationScale==1.75f && !*first->szAmmoName);
        assert(CODOL_LoadMountedNullWeapon("NONE",&again)==1 && again==first);
        assert(CODOL_LoadMountedNullWeapon("other",&again)==0 && again==first);
        data[72+0x588]=1; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedNullWeapon("none",&again)==-1 && again==first && !first->damage);
        data[72+0x588]=0; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedNullWeapon("none",&again)==1 && again!=first && first->sprintDurationScale==1.75f);
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[88+0xbfc+2]={0}; char path[]="/tmp/codol-weapon-hide-tags-XXXXXX";
        const char *paths[]={path}; codol_weapon_hide_tags_t first={0},same={0};
        codol_weapon_hide_tag_handles_t sentinel={{0}};
        const codol_weapon_hide_tag_handles_t *handles=&sentinel,*original;
        bone_string_test_t state={0},other={0}; unsigned failure,overflow;
        unsigned i; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+40,2); put32(data+44,UINT32_MAX); put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,UINT32_MAX); put32(data+60,UINT32_MAX); memcpy(data+64,"tag\0tag",8);
        put32(data+72,28); put32(data+76,48); put32(data+80,UINT32_MAX); put32(data+84,sizeof(data)-88);
        put32(data+88,UINT32_MAX); memcpy(data+88+0xbfc,"w",2);
        for(i=0;i<32;++i) data[88+0x3c+2*i]=1;
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeaponHideTags("w",&first)==1);
        for(i=0;i<32;++i) assert(first.names[i] && !strcmp(first.names[i],"tag"));
        for(overflow=0;overflow<2;++overflow) for(failure=1;failure<=32;++failure) {
            state=(bone_string_test_t){0}; state.fail_at=failure; state.overflow=overflow;
            assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&state,&handles)==-1);
            assert(handles==&sentinel && !state.live && state.calls==failure && state.releases==failure-1+overflow);
        }
        state=(bone_string_test_t){0};
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&state,&handles)==1);
        original=handles; assert(state.calls==32 && state.live==32);
        for(i=0;i<32;++i) assert(handles->tags[i]==33);
        assert(CODOL_BindMountedWeaponHideTags("W",test_acquire_weapon_tag,test_release_bone,&state,&handles)==1);
        assert(handles==original && state.calls==32);
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&other,&handles)==1);
        assert(handles!=original && other.live==32); handles=original;
        assert(CODOL_BindMountedWeaponHideTags("absent",test_acquire_weapon_tag,test_release_bone,&state,&handles)==0);
        assert(handles==original && state.calls==32);
        assert(CODOL_BindMountedWeaponHideTags("w",NULL,test_release_bone,&state,&handles)==-1);
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,NULL,&state,&handles)==-1);
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&state,NULL)==-1);
        same=first;
        assert(CODOL_LoadMountedWeaponHideTags("absent",&same)==0 && !memcmp(&same,&first,sizeof(first)));
        data[88+0x3c+62]=2; file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponHideTags("w",&same)==-1 && !memcmp(&same,&first,sizeof(first)));
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&state,&handles)==-1);
        assert(handles==original && state.calls==32 && state.live==32);
        data[88+0x3c+62]=1; data[88+0x3c+30]=0; memcpy(data+68,"new",4);
        file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeaponHideTags("w",&same)==1 && !same.names[15]);
        assert(!strcmp(same.names[31],"new") && !strcmp(first.names[31],"tag"));
        assert(CODOL_BindMountedWeaponHideTags("w",test_acquire_weapon_tag,test_release_bone,&state,&handles)==1);
        assert(handles!=original && state.calls==63 && state.live==63);
        for(i=0;i<32;++i) assert(handles->tags[i]==(i==15 ? 0 : 33) && original->tags[i]==33);
        assert(!unlink(path)); CODOL_UnmountArchives();
        /* Weapon tag handles share the same generation-safety policy as
         * animation strings: unmount drops the cache, not these references. */
        assert(state.live==63 && state.releases==0 && other.live==32 && other.releases==0);
    }
    {
        static const char names[]="w\0display\0overlay\0mode";
        uint8_t data[72+0xbfc+sizeof(names)]={0}; char path[]="/tmp/codol-weapon-source-XXXXXX";
        const char *paths[]={path}; codol_mounted_weapon_t first={0},same={0},newer={0},pooled={0};
        int fd; FILE *file; unsigned i;
        put32(data,sizeof(data)-40); put32(data+8,8192); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,28); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72);
        for(i=0;i<4;++i) put32(data+72+4*i,UINT32_MAX);
        memcpy(data+72+0xbfc,names,sizeof(names));
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedWeapon("w",&first)==1 && first.asset.type==28);
        assert(!strcmp(first.strings[1],"display") && !strcmp(first.strings[2],"overlay") && !strcmp(first.strings[3],"mode"));
        assert(CODOL_LoadMountedWeapon("W",&same)==1 && same.asset.data==first.asset.data);
        assert(CODOL_LoadMountedWeapon("missing",&same)==0 && same.asset.data==first.asset.data);
        put32(data+76,0x40000001); file=fopen(path,"wb"); assert(file);
        /* Remove the no-longer-inline display string from the serialized stream. */
        memmove(data+72+0xbfc+2,data+72+0xbfc+10,sizeof(names)-10);
        put32(data,sizeof(data)-48); put32(data+68,sizeof(data)-80);
        assert(fwrite(data,1,sizeof(data)-8,file)==sizeof(data)-8 && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeapon("w",&same)==-1 && same.asset.data==first.asset.data);
        {
            codol_zone_t zone={0}; codol_load_blocks_t blocks={0}; size_t offset;
            assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)-8) && CODOL_ReplayZone(&zone,&blocks,NULL));
            for(offset=0;offset+2<=blocks.written[3];++offset)
                if(!memcmp(blocks.data[3]+offset,"w",2)) break;
            assert(offset+2<=blocks.written[3]); put32(data+76,0x30000001+(uint32_t)offset);
            CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
            file=fopen(path,"wb"); assert(file);
            assert(fwrite(data,1,sizeof(data)-8,file)==sizeof(data)-8 && !fclose(file));
            assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
            assert(CODOL_LoadMountedWeapon("w",&pooled)==1);
            assert(!strcmp(pooled.strings[1],"w") && !strcmp(pooled.strings[2],"overlay"));
        }
        put32(data+76,UINT32_MAX); memcpy(data+72+0xbfc,names,sizeof(names)); data[72+0xbfc+2]='D';
        put32(data,sizeof(data)-40); put32(data+68,sizeof(data)-72);
        file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedWeapon("w",&newer)==1 && newer.asset.data!=first.asset.data);
        assert(!strcmp(newer.strings[1],"Display") && !strcmp(first.strings[1],"display"));
        assert(!strcmp(pooled.strings[1],"w")); /* Retired pooled block remains alive. */
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[230]={0}; char path[]="/tmp/codol-common-world-XXXXXX";
        const char *paths[]={path}; const struct ComWorld *first,*same=NULL,*replacement;
        int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,16); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,158);
        put32(data+72,UINT32_MAX); put32(data+76,1); put32(data+80,2); put32(data+84,UINT32_MAX);
        memcpy(data+88,"w",2); data[90]=2; data[91]=1; data[92]=7;
        put32(data+94,0x3f800000); put32(data+154,UINT32_MAX); memcpy(data+226,"sun",4);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadEngineCommonWorld("w",&first)==1);
        assert(first->isInUse==1 && first->primaryLightCount==2 && !strcmp(first->name,"w"));
        assert(first->primaryLights[0].type==2 && first->primaryLights[0].exponent==7);
        assert(first->primaryLights[0].color[0]==1 && !strcmp(first->primaryLights[0].defName,"sun"));
        assert(!first->primaryLights[1].defName);
        assert(CODOL_LoadEngineCommonWorld("W",&same)==1 && same==first);
        assert(CODOL_LoadEngineCommonWorld("missing",&same)==0 && same==first);
        put32(data+94,0x7fc00000); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadEngineCommonWorld("w",&same)==-1 && same==first);
        put32(data+94,0x40000000); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadEngineCommonWorld("w",&replacement)==1 && replacement!=first);
        assert(replacement->primaryLights[0].color[0]==2 && first->primaryLights[0].color[0]==1);
        assert(!strcmp(first->primaryLights[0].defName,"sun"));
        assert(!unlink(path)); CODOL_UnmountArchives(); CODOL_UnmountArchives();
    }
    {
        unsigned runner;
        for(runner=0;runner<3;++runner) {
        uint8_t data[680]={0}; const FxEffectDef *first=NULL,*current=NULL,*other=NULL; unsigned version,i;
#define FX_CHILD(fx) ((runner==1) ? (const FxEffectDef *)(fx)->elemDefs[0].visuals : (fx)->elemDefs[0].effectRefs[0])
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,2); put32(data+52,UINT32_MAX);
        for(i=0;i<2;++i) {
            unsigned start=88+296*i; put32(data+56+16*i,30); put32(data+60+16*i,start-40);
            put32(data+64+16*i,UINT32_MAX); put32(data+68+16*i,296);
            put32(data+start,UINT32_MAX); put32(data+start+20,1); put32(data+start+28,UINT32_MAX);
            data[start+32]='a'+i; put32(data+start+34+(runner==1 ? 188 : 216),UINT32_MAX); data[start+294]='b'-i;
            if(runner==1) { data[start+34+176]=14; data[start+34+177]=1; }
            if(runner==2) data[start+34+176]=1; /* Oriented sprite effect references. */
        }
        for(version=0;version<3;++version) {
            char path[]="/tmp/codol-native-effect-graph-XXXXXX"; const char *paths[]={path}; int fd; FILE *file;
            data[678]=version==1 ? 'z' : 'a'; if(version==2) data[382]='a';
            fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
            assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,41,NULL,NULL)); assert(!unlink(path));
            if(version==1) {
                assert(CODOL_LoadMountedNativeEffect("a",NULL,NULL,&current)==-1 && current==first);
                assert(CODOL_LoadMountedNativeEffect("a",NULL,NULL,&current)==-1 && current==first);
                assert(FX_CHILD(FX_CHILD(first))==first); continue;
            }
            assert(CODOL_LoadMountedNativeEffect("a",NULL,NULL,&current)==1);
            if(runner==2) assert(current->elemDefs[0].elemType==1);
            if(!version) {
                first=current; assert(!strcmp(FX_CHILD(first)->name,"b"));
                assert(FX_CHILD(FX_CHILD(first))==first);
                assert(CODOL_LoadMountedNativeEffect("b",NULL,NULL,&other)==1 && other==FX_CHILD(first));
                assert(CODOL_LoadMountedNativeEffect("a",NULL,NULL,&current)==1 && current==first);
            } else {
                assert(current!=first && FX_CHILD(current)==current);
                assert(FX_CHILD(first)==other);
            }
        }
        other=current;
        assert(CODOL_LoadMountedNativeEffect("missing",NULL,NULL,&current)==0 && current==other);
        CODOL_UnmountArchives();
#undef FX_CHILD
        }
    }
    {
        uint8_t data[376]={0}; char path[]="/tmp/codol-native-runner-array-XXXXXX"; const char *paths[]={path};
        const FxEffectDef *effect; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,30); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72); put32(data+72,UINT32_MAX);
        put32(data+92,1); put32(data+100,UINT32_MAX); data[104]='a';
        data[106+176]=14; data[106+177]=2; put32(data+106+188,UINT32_MAX);
        put32(data+366,UINT32_MAX); data[374]='a';
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedNativeEffect("a",NULL,NULL,&effect)==1);
        assert(effect->elemDefs[0].elemType==10 && effect->elemDefs[0].visualCount==2);
        assert(((const FxEffectDef **)effect->elemDefs[0].visuals)[0]==effect);
        assert(!((const FxEffectDef **)effect->elemDefs[0].visuals)[1]);
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t data[1094]={0}; char path[]="/tmp/codol-native-effect-bind-XXXXXX"; const char *paths[]={path};
        effect_model_test_t a={0},b={0}; FxEffectDef sentinel={0}; const FxEffectDef *first,*current=&sentinel;
        int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,30); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72);
        put32(data+72,UINT32_MAX); put32(data+92,2); put32(data+100,UINT32_MAX); memcpy(data+104,"f",2);
        data[106+176]=9; data[106+177]=1; put32(data+106+188,UINT32_MAX);
        data[366+176]=13; data[366+177]=1; put32(data+366+188,UINT32_MAX);
        put32(data+626,UINT32_MAX); memcpy(data+986,"m",2);
        put32(data+988,UINT32_MAX); /* First decal material inline; second is null. */
        put32(data+996,UINT32_MAX); memcpy(data+1092,"t",2);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); assert(!unlink(path));
        assert(CODOL_LoadMountedNativeEffect("f",NULL,NULL,&current)==-1 && current==&sentinel);
        a.fail=1; assert(CODOL_LoadMountedNativeEffect("f",test_effect_model,&a,&current)==-1 && current==&sentinel);
        a.fail=0; assert(CODOL_LoadMountedNativeEffect("f",test_effect_model,&a,&current)==1); first=current;
        assert(first->elemDefs[0].elemType==5 && first->elemDefs[0].visuals==&a.model);
        assert(first->elemDefs[1].elemType==9 && first->elemDefs[1].visualCount==1);
        assert(!strcmp(((Material_t **)first->elemDefs[1].visuals)[0]->info.name,"t"));
        assert(!((Material_t **)first->elemDefs[1].visuals)[1]);
        assert(CODOL_LoadMountedNativeEffect("f",test_effect_model,&a,&current)==1 && current==first && a.calls==2);
        assert(CODOL_LoadMountedNativeEffect("f",test_effect_model,&b,&current)==1 && current!=first && b.calls==1);
        assert(current->elemDefs[0].visuals==&b.model && first->elemDefs[0].visuals==&a.model);
        CODOL_UnmountArchives();
    }
    {
        uint8_t data[767]={0}; codol_asset_t asset={30,data,sizeof(data)};
        codol_model_block_t blocks[8]={{0}}; codol_effect_source_t source={0},saved; size_t n;
        put32(data,UINT32_MAX); put32(data+20,2); put32(data+28,UINT32_MAX); memcpy(data+32,"e",2);
        data[34+176]=5; data[34+177]=1;
        put32(data+34+180,UINT32_MAX); put32(data+34+184,UINT32_MAX); put32(data+34+188,0x30000001);
        put32(data+34+216,UINT32_MAX); put32(data+34+220,0x30000001);
        put32(data+34+244,UINT32_MAX); put32(data+34+256,UINT32_MAX);
        data[294+176]=12; data[294+177]=1; put32(data+294+188,UINT32_MAX); put32(data+294+244,UINT32_MAX);
        data[554]=1; data[650]=2; memcpy(data+698,"i",2);
        put32(data+720,1); put32(data+724,UINT32_MAX); put32(data+728,1); put32(data+732,UINT32_MAX);
        memcpy(data+758,"x",2); memcpy(data+760,"sound",6); data[766]=3;
        blocks[3]=(codol_model_block_t){(const uint8_t *)"pool",5};
        assert(CODOL_ReadEffectSource(&asset,blocks,&source)); saved=source;
        assert(source.elements[0].velocity_count==1 && source.elements[0].velocity_samples[0]==1);
        assert(source.elements[0].visual_sample_count==1 && source.elements[0].visual_samples[0]==2);
        assert(source.elements[0].extension_size==36 && source.elements[0].trail_vertex_count==1 && source.elements[0].trail_vertices==data+736);
        assert(source.elements[0].trail_index_count==1 && source.elements[0].trail_indices==data+756);
        assert(!strcmp(source.elements[0].effect_names[0],"i") && !strcmp(source.elements[0].effect_names[1],"pool"));
        assert(!strcmp(source.elements[0].extra_name,"x") && !strcmp(source.elements[1].visuals[0].string,"sound"));
        assert(source.elements[1].extension_size==1 && source.elements[1].extension[0]==3);
        for(n=0;n<sizeof(data);++n) {
            asset.size=n; assert(!CODOL_ReadEffectSource(&asset,blocks,&source) && !memcmp(&saved,&source,sizeof(source)));
        }
        asset.size=sizeof(data); assert(CODOL_ReadEffectSource(&asset,blocks,&source));
        CODOL_FreeEffectSource(&source); CODOL_FreeEffectSource(&source);
    }
    {
        uint8_t data[554]={0}; codol_asset_t asset={30,data,sizeof(data)};
        codol_model_block_t blocks[8]={{0}}; codol_effect_prefix_t prefix={0},saved;
        put32(data,UINT32_MAX); put32(data+4,123); put32(data+12,UINT32_MAX); put32(data+20,2);
        put32(data+28,UINT32_MAX); memcpy(data+32,"e",2);
        assert(CODOL_ReadEffectPrefix(&asset,NULL,&prefix)); saved=prefix;
        assert(prefix.count==2 && prefix.counts[1]==2 && prefix.flags==123 && prefix.looping_life==-1);
        assert(prefix.elements==data+34 && prefix.dependency_offset==554);
        --asset.size; assert(!CODOL_ReadEffectPrefix(&asset,NULL,&prefix) && !memcmp(&saved,&prefix,sizeof(prefix)));
        ++asset.size; put32(data+28,0); assert(!CODOL_ReadEffectPrefix(&asset,NULL,&prefix));
        put32(data+28,UINT32_MAX); put32(data+20,0x7fffffff); assert(!CODOL_ReadEffectPrefix(&asset,NULL,&prefix));
        put32(data+20,2); put32(data,0x30000001); blocks[3]=(codol_model_block_t){(const uint8_t *)"pool",5};
        assert(CODOL_ReadEffectPrefix(&asset,blocks,&prefix) && !strcmp(prefix.name,"pool") && prefix.elements==data+32);
        blocks[3].size=4; saved=prefix;
        assert(!CODOL_ReadEffectPrefix(&asset,blocks,&prefix) && !memcmp(&saved,&prefix,sizeof(prefix)));
    }
    {
        uint8_t data[1656]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t alias; unsigned i;
        const unsigned starts[5]={886,1256,1354,1460,1558};
        const uint32_t slots[5]={0x300000d1,0x30000325,0x30000329,0x30000331,0x30000335};
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,30); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72);
        put32(data+72,UINT32_MAX); put32(data+92,3); put32(data+100,UINT32_MAX); memcpy(data+104,"f",2);
        data[106+176]=9; data[106+177]=1; put32(data+106+188,UINT32_MAX);
        data[366+177]=2; put32(data+366+188,UINT32_MAX);
        data[626+176]=13; data[626+177]=1; put32(data+626+188,UINT32_MAX);
        put32(data+886,UINT32_MAX); memcpy(data+1246,"m",2);
        put32(data+1248,UINT32_MAX); put32(data+1252,UINT32_MAX);
        put32(data+1452,UINT32_MAX); put32(data+1456,UINT32_MAX);
        for(i=1;i<5;++i) { put32(data+starts[i],UINT32_MAX); data[starts[i]+96]='a'+i; }
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i<5;++i) {
            assert(i ? CODOL_ResolveMaterialAlias(&blocks,slots[i],&alias) : CODOL_ResolveModelAlias(&blocks,slots[i],&alias));
            assert(alias.data==zone.data+starts[i] && alias.size==(i ? 98 : 362));
        }
        {
            codol_asset_t effect; codol_effect_source_t source={0}; codol_model_block_t views[8];
            assert(CODOL_ZoneAsset(&zone,0,&effect)); CODOL_LoadBlockViews(&blocks,views);
            assert(CODOL_ReadEffectSource(&effect,views,&source));
            assert(source.elements[0].visuals[0].inline_asset.type==4 && source.elements[0].visuals[0].inline_asset.data==zone.data+886);
            assert(source.elements[1].visual_count==2 && source.elements[2].visual_count==2);
            assert(source.elements[1].visuals[1].inline_asset.data==zone.data+1354);
            assert(source.elements[2].visuals[1].inline_asset.type==5 && source.elements[2].visuals[1].inline_asset.data==zone.data+1558);
            CODOL_FreeEffectSource(&source);
        }
        {
            const codol_effect_source_t *first=NULL,*current=NULL,*second=NULL;
            codol_effect_visual_source_t original={0},resolved={0}; unsigned version;
            for(version=0;version<3;++version) {
                char path[]="/tmp/codol-effect-cache-XXXXXX"; const char *paths[]={path}; int fd; FILE *file;
                put32(data+76,version);
                if(version==2) put32(data+106+256,0x30000fff);
                fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
                assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
                assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,23,NULL,NULL)); assert(!unlink(path));
                if(version==2) {
                    assert(CODOL_LoadMountedEffectSource("f",&current)==-1 && current==second); continue;
                }
                assert(CODOL_LoadMountedEffectSource("f",&current)==1 && current->prefix.flags==version);
                if(!version) first=current; else { second=current; assert(second!=first && first->prefix.flags==0); }
                assert(CODOL_LoadMountedEffectSource("f",&current)==1 && current==(version ? second : first));
                assert(CODOL_LoadMountedEffectVisual("f",0,0,&resolved)==1 && resolved.asset.type==4 && !strcmp(resolved.name,"m"));
                assert(CODOL_LoadMountedEffectVisual("f",1,0,&resolved)==1 && resolved.asset.type==5 && !strcmp(resolved.name,"b"));
                original=resolved;
                assert(CODOL_LoadMountedEffectVisual("f",9,0,&resolved)==-1 && !memcmp(&original,&resolved,sizeof(resolved)));
                assert(CODOL_LoadMountedEffectVisual("f",1,9,&resolved)==-1 && !memcmp(&original,&resolved,sizeof(resolved)));
                if(!version) {
                    uint8_t patch[170]={0}; char override[]="/tmp/codol-fx-material-XXXXXX";
                    const char *patches[]={override};
                    memcpy(patch,data,72); put32(patch,sizeof(patch)-40); put32(patch+56,5); put32(patch+68,98);
                    put32(patch+72,UINT32_MAX); put32(patch+76,99); memcpy(patch+168,"b",2);
                    fd=mkstemp(override); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
                    assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
                    assert(CODOL_ReplaceRuntimeArchives(patches,1,NULL,24,NULL,NULL)); assert(!unlink(override));
                    assert(CODOL_LoadMountedEffectVisual("f",1,0,&resolved)==1 && resolved.asset.data!=original.asset.data);
                    assert(resolved.asset.data[4]==99 && original.asset.data[4]==0 && !resolved.blocks[0].data);
                    assert(CODOL_LoadMountedEffectSource("f",&current)==1 && current==first);
                }
            }
            assert(first->prefix.count==3 && second->prefix.count==3 && !strcmp(first->prefix.name,"f"));
            assert(CODOL_LoadMountedEffectSource("missing",&current)==0 && current==second);
            CODOL_UnmountArchives();
        }
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
    }
    {
        uint8_t data[146]={0}; const codol_physics_map_t *first=NULL,*second=NULL,*current=NULL;
        const PhysGeomList_t *native_first=NULL,*native_second=NULL,*native_current=NULL;
        unsigned version;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,1); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,74);
        put32(data+72,UINT32_MAX); memcpy(data+144,"p",2);
        for (version=0;version<3;++version) {
            char path[]="/tmp/codol-physics-map-cache-XXXXXX"; const char *paths[]={path};
            int fd=mkstemp(path); FILE *file; assert(fd>=0);
            put32(data+84,version==0 ? 0x3f800000 : version==1 ? 0x40000000 : 0x7fc00000);
            file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
            assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,42,NULL,NULL)); assert(!unlink(path));
            if (version<2) {
                assert(CODOL_LoadMountedPhysicsMap("p",&current)==1);
                assert(current->center_of_mass[0]==version+1 && !strcmp(current->name,"p"));
                if (!version) first=current; else { second=current; assert(second!=first); }
                assert(CODOL_LoadMountedPhysicsMap("p",&current)==1 && current==(version ? second : first));
                assert(CODOL_LoadEnginePhysicsMap("p",&native_current)==1);
                assert(native_current->mass.centerOfMass[0]==version+1);
                if (!version) native_first=native_current; else native_second=native_current;
                assert(CODOL_LoadEnginePhysicsMap("p",&native_current)==1 && native_current==(version ? native_second : native_first));
            } else assert(CODOL_LoadMountedPhysicsMap("p",&current)==-1 && current==second);
            if (version==2) assert(CODOL_LoadEnginePhysicsMap("p",&native_current)==-1 && native_current==native_second);
            assert(CODOL_LoadMountedPhysicsMap("missing",&current)==0);
            assert(CODOL_LoadMountedPhysicsMap(",p",&current)==-1);
            assert(current==(version ? second : first));
        }
        assert(first->center_of_mass[0]==1 && second->center_of_mass[0]==2);
        assert(native_first!=native_second && native_first->mass.centerOfMass[0]==1 && native_second->mass.centerOfMass[0]==2);
        assert(!strcmp(first->name,"p") && !strcmp(second->name,"p"));
        CODOL_UnmountArchives();
    }
    {
        uint8_t data[142]={0}; const struct PhysPreset *first=NULL,*second=NULL,*current=NULL;
        unsigned version;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,0); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,70);
        put32(data+72,UINT32_MAX); data[72+64]=2; memcpy(data+140,"p",2);
        for(version=0;version<3;++version) {
            char path[]="/tmp/codol-native-preset-XXXXXX"; const char *paths[]={path};
            int fd=mkstemp(path); FILE *file; assert(fd>=0);
            put32(data+80,version==0 ? 0x3f800000 : version==1 ? 0x40000000 : 0x7fc00000);
            file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
            assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,17,NULL,NULL)); assert(!unlink(path));
            if(version<2) {
                assert(CODOL_LoadEnginePhysicsPreset("p",&current)==1);
                assert(current->mass==version+1 && current->tempDefaultToCylinder && !strcmp(current->name,"p"));
                if(!version) first=current; else { second=current; assert(second!=first && first->mass==1); }
                assert(CODOL_LoadEnginePhysicsPreset("p",&current)==1 && current==(version ? second : first));
            } else assert(CODOL_LoadEnginePhysicsPreset("p",&current)==-1 && current==second);
            assert(CODOL_LoadEnginePhysicsPreset("missing",&current)==0);
            assert(CODOL_LoadEnginePhysicsPreset(",p",&current)==-1);
            assert(current==(version ? second : first));
        }
        assert(first->mass==1 && second->mass==2 && !strcmp(first->name,"p"));
        CODOL_UnmountArchives();
    }
    {
        uint8_t data[502]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t collision,effect,saved; codol_dynamic_records_t records;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,15); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,430);
        put32(data+72,123); put32(data+72+156,UINT32_MAX);
        put32(data+72+168,1); put32(data+72+172,UINT32_MAX);
        put32(data+328,123); put32(data+332,UINT32_MAX); put32(data+336,4); memcpy(data+372,"{}\n",4);
        put32(data+376+40,UINT32_MAX-1); put32(data+468,UINT32_MAX); memcpy(data+500,"e",2);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ZoneAsset(&zone,0,&collision) && CODOL_ResolveDynamicRecords(&blocks,&collision,0,&records));
        assert(CODOL_ResolveEffectAlias(&blocks,records.reference+40,&effect)); saved=effect;
        assert(effect.type==30 && effect.data==zone.data+468 && effect.size==34);
        assert(!CODOL_ResolveModelAlias(&blocks,records.reference+40,&effect) && !memcmp(&effect,&saved,sizeof(effect)));
        assert(CODOL_ResolveEffectAlias(&blocks,records.reference+92,&effect) && effect.data==saved.data);
        {
            uint8_t mounted[1154]={0},patch[106]={0};
            char path[]="/tmp/codol-dynamic-map-XXXXXX",override[]="/tmp/codol-dynamic-fx-XXXXXX";
            const char *paths[]={path}; codol_dynamic_dependency_t dependency={0},prior;
            int fd; FILE *file;
            memcpy(mounted,data,72); memcpy(mounted+88,data+72,430);
            put32(mounted,sizeof(mounted)-40); put32(mounted+48,2); put32(mounted+60,48);
            put32(mounted+72,21); put32(mounted+76,478); put32(mounted+80,UINT32_MAX); put32(mounted+84,636);
            put32(mounted+518,123); put32(mounted+522,UINT32_MAX); put32(mounted+518+0x38,UINT32_MAX);
            memcpy(mounted+1146,"mp_test",8);
            fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(mounted,1,sizeof(mounted),file)==sizeof(mounted) && !fclose(file));
            assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); assert(!unlink(path));
            assert(CODOL_LoadMountedDynamicDependency("mp_test",0,0,30,&dependency)==1);
            assert(!strcmp(dependency.name,"e") && dependency.asset.type==30 && !dependency.blocks[0].data);
            prior=dependency;
            assert(CODOL_LoadMountedDynamicDependency("mp_test",0,0,4,&dependency)==0);
            assert(CODOL_LoadMountedDynamicDependency("missing",0,0,30,&dependency)==0);
            assert(CODOL_LoadMountedDynamicDependency("mp_test",1,0,30,&dependency)==-1);
            assert(CODOL_LoadMountedDynamicDependency("mp_test",0,1,30,&dependency)==-1);
            assert(CODOL_LoadMountedDynamicDependency("mp_test",0,0,5,&dependency)==-1);
            assert(!memcmp(&dependency,&prior,sizeof(prior)));
            memcpy(patch,data,72); put32(patch,sizeof(patch)-40); put32(patch+56,30); put32(patch+68,34);
            put32(patch+72,UINT32_MAX); put32(patch+76,123); memcpy(patch+104,"e",2);
            fd=mkstemp(override); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
            paths[0]=override; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); assert(!unlink(override));
            assert(CODOL_LoadMountedDynamicDependency("mp_test",0,0,30,&dependency)==1);
            assert(dependency.asset.data!=prior.asset.data && dependency.asset.data[4]==123);
            assert(prior.asset.data[4]==0 && !strcmp(prior.name,"e"));
            CODOL_UnmountArchives();
        }
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
    }
    {
        uint8_t data[996]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t collision,model,preset,wrong; codol_dynamic_records_t records,saved_records;
        codol_dynamic_entities_t entities={0},saved;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,8192);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,15); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,924);
        put32(data+72,123); put32(data+72+156,UINT32_MAX);
        put32(data+72+168,0x10001); put32(data+72+172,UINT32_MAX); put32(data+72+176,UINT32_MAX);
        put32(data+328,123); put32(data+332,UINT32_MAX); put32(data+336,4); memcpy(data+372,"{}\n",4);
        put32(data+376,2); put32(data+392,0x3f800000); put32(data+396,0x40400000);
        put32(data+408,UINT32_MAX); put32(data+420,UINT32_MAX); put32(data+424,25);
        put32(data+428,0x3f800000); put32(data+464,0x80000001);
        put32(data+468,UINT32_MAX); memcpy(data+828,"dyn_m",6);
        put32(data+834,UINT32_MAX); memcpy(data+902,"p",2);
        put32(data+904+36,0x90007);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ZoneAsset(&zone,0,&collision));
        assert(CODOL_ResolveDynamicRecords(&blocks,&collision,0,&records)); saved_records=records;
        assert(records.count==1 && records.records==zone.data+376);
        assert(CODOL_ResolveModelAlias(&blocks,records.reference+32,&model) && model.data==zone.data+468 && model.size==366);
        assert(CODOL_ResolvePhysicsAlias(&blocks,0,records.reference+44,&preset) && preset.data==zone.data+834);
        wrong=collision; wrong.data=data+72;
        assert(!CODOL_ResolveDynamicRecords(&blocks,&wrong,0,&records) && !memcmp(&records,&saved_records,sizeof(records)));
        assert(CODOL_ReadDynamicEntities(&collision,&blocks,&entities)); saved=entities;
        assert(entities.count[0]==1 && entities.count[1]==1);
        assert(entities.entities[0][0].origin[0]==3 && entities.entities[0][0].quat[3]==1);
        assert(entities.entities[0][0].health==25 && entities.entities[0][0].contents==0x80000001);
        assert(entities.entities[0][0].model_slot==saved_records.reference+32);
        assert(entities.entities[1][0].brush_model==7 && entities.entities[1][0].physics_brush_model==9);
        put32(zone.data+904+52,0x7fc00000);
        assert(!CODOL_ReadDynamicEntities(&collision,&blocks,&entities) && !memcmp(&saved,&entities,sizeof(entities)));
        put32(zone.data+904+52,0); --collision.size;
        assert(!CODOL_ReadDynamicEntities(&collision,&blocks,&entities) && !memcmp(&saved,&entities,sizeof(entities)));
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        assert(entities.entities[0][0].mass[0]==1 && entities.entities[0][0].health==25);
        CODOL_FreeDynamicEntities(&entities); CODOL_FreeDynamicEntities(&entities);
    }
    {
        uint8_t data[578]={0}; char path[]="/tmp/codol-physics-xmodel-XXXXXX";
        const char *paths[]={path}; native_collision_counts_t strings={0},other={0};
        const XModel *base,*native,*same=NULL,*replacement; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,4); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,506);
        put32(data+72,UINT32_MAX); data[72+0x12a]=255;
        put32(data+72+0x160,UINT32_MAX); put32(data+72+0x164,UINT32_MAX);
        memcpy(data+432,"m",2);
        put32(data+434,UINT32_MAX); put32(data+442,0x3f800000); memcpy(data+502,"p",2);
        put32(data+504,UINT32_MAX); put32(data+516,0x40400000); memcpy(data+576,"q",2);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedCollisionXModel("m",native_collision_acquire,native_collision_release,&strings,&base)==1);
        assert(CODOL_LoadMountedPhysicsXModel("m",native_collision_acquire,native_collision_release,&strings,&native)==1);
        assert(native!=base && native->name==base->name && !base->physPreset && !base->physGeoms);
        assert(((const struct PhysPreset *)native->physPreset)->mass==1 && native->physGeoms->mass.centerOfMass[0]==3);
        assert(CODOL_LoadMountedPhysicsXModel("M",native_collision_acquire,native_collision_release,&strings,&same)==1 && same==native);
        assert(CODOL_LoadMountedPhysicsXModel("m",native_collision_acquire,native_collision_release,&other,&same)==-1 && same==native);
        assert(CODOL_LoadMountedPhysicsXModel("absent",native_collision_acquire,native_collision_release,&strings,&same)==0 && same==native);
        put32(data+516,0x7fc00000); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedPhysicsXModel("m",native_collision_acquire,native_collision_release,&strings,&same)==-1 && same==native);
        assert(native->physGeoms->mass.centerOfMass[0]==3);
        put32(data+516,0x40800000); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadMountedPhysicsXModel("m",native_collision_acquire,native_collision_release,&strings,&replacement)==1);
        assert(replacement!=native && replacement->physGeoms->mass.centerOfMass[0]==4 && native->physGeoms->mass.centerOfMass[0]==3);
        assert(!unlink(path)); CODOL_UnmountArchives(); assert(!strings.live);
    }
    {
        uint8_t data[1142]={0}; char path[]="/tmp/codol-world-model-XXXXXX";
        const char *paths[]={path}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t asset; const codol_mounted_model_skeleton_t *model,*again;
        const codol_mounted_model_geometry_t *geometry; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX);
        put32(data+56,21); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,1070);
        put32(data+72+456,1); put32(data+72+548,UINT32_MAX);
        put32(data+700+52,UINT32_MAX);
        put32(data+776,UINT32_MAX); data[776+0x12a]=255; memcpy(data+1136,"crate",6);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ResolveModelAlias(&blocks,0x30000045,&asset));
        assert(asset.size==366 && asset.type==4 && !strcmp((const char *)asset.data+360,"crate"));
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); assert(!unlink(path));
        assert(CODOL_LoadMountedXModelSkeleton("crate",&model)==1);
        assert(!strcmp(model->skeleton.name,"crate") && !model->skeleton.unresolved);
        assert(CODOL_LoadMountedXModelSkeleton("CRATE",&again)==1 && again==model);
        assert(CODOL_LoadMountedXModelGeometry("crate",&geometry)==1);
        {
            native_collision_counts_t strings={0},other={0}; const XModel *native,*same;
            assert(CODOL_LoadMountedCollisionXModel("crate",native_collision_acquire,native_collision_release,&strings,&native)==1);
            assert(!strcmp(native->name,"crate") && native->collLod==-1 && !native->numLods);
            assert(CODOL_LoadMountedCollisionXModel("CRATE",native_collision_acquire,native_collision_release,&strings,&same)==1 && same==native);
            assert(CODOL_LoadMountedCollisionXModel("crate",native_collision_acquire,native_collision_release,&other,&same)==-1 && same==native);
            assert(CODOL_LoadMountedCollisionXModel("missing",native_collision_acquire,native_collision_release,&strings,&same)==0 && same==native);
            {
                char replacement[]="/tmp/codol-native-model-group-XXXXXX";
                const char *paths[]={replacement}; const XModel *first,*second;
                fd=mkstemp(replacement); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
                put32(data+776+0x13c,0x3f800000);
                assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
                assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
                assert(CODOL_LoadMountedCollisionXModel("crate",native_collision_acquire,native_collision_release,&strings,&first)==1);
                assert(first!=native && first->radius==1 && native->radius==0);
                put32(data+776+0x13c,0x40000000); file=fopen(replacement,"wb"); assert(file);
                assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
                assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
                assert(CODOL_LoadMountedCollisionXModel("crate",native_collision_acquire,native_collision_release,&strings,&second)==1);
                assert(second!=first && second->radius==2 && first->radius==1 && native->radius==0);
                file=fopen(replacement,"wb"); assert(file);
                assert(fwrite(data,1,1,file)==1 && !fclose(file));
                assert(!CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
                assert(CODOL_LoadMountedCollisionXModel("crate",native_collision_acquire,native_collision_release,&strings,&same)==1 && same==second);
                assert(!unlink(replacement));
            }
            CODOL_UnmountArchives(); assert(!strings.live);
        }
        CODOL_UnmountArchives();
    }
    {
        uint8_t data[1487]={0}; char path[]="/tmp/codol-collision-model-XXXXXX";
        const char *paths[]={path}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t asset,saved; codol_collision_map_t map={0}; int handle=19;
        int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,3); put32(data+52,UINT32_MAX);
        put32(data+56,4); put32(data+60,64); put32(data+64,UINT32_MAX-1); put32(data+68,367);
        put32(data+72,15); put32(data+76,431); put32(data+80,UINT32_MAX); put32(data+84,380);
        put32(data+88,21); put32(data+92,811); put32(data+96,UINT32_MAX); put32(data+100,636);
        put32(data+104,UINT32_MAX); memcpy(data+464,",crate",7);
        put32(data+471,123); put32(data+471+16,1); put32(data+471+20,UINT32_MAX);
        put32(data+471+156,UINT32_MAX); put32(data+727,0x30000009);
        put32(data+803,123); put32(data+807,UINT32_MAX); put32(data+811,4); memcpy(data+847,"{}\n",4);
        put32(data+851,123); put32(data+855,UINT32_MAX); put32(data+851+56,UINT32_MAX);
        memcpy(data+1479,"mp_test",8);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ResolveModelAlias(&blocks,0x30000009,&asset)); saved=asset;
        assert(asset.type==4 && asset.size==367 && !strcmp((const char *)asset.data+360,",crate"));
        assert(CODOL_ResolveModelAlias(&blocks,0x30000031,&asset) && asset.data==saved.data);
        assert(!CODOL_ResolveModelAlias(&blocks,0x3000000a,&asset) && asset.data==saved.data);
        assert(!CODOL_ResolveMaterialAlias(&blocks,0x30000009,&asset) && asset.data==saved.data);
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); assert(!unlink(path));
        assert(CODOL_LoadMountedCollisionModels("mp_test",collision_named_model,&handle,&map)==1);
        assert(map.static_models.count==1 && !map.static_models.unresolved && map.static_models.models[0].xmodel==&handle);
        assert(CODOL_LoadMountedCollisionModels("mp_test",collision_named_model,NULL,&map)==1);
        assert(map.static_models.unresolved==1 && !map.static_models.models[0].xmodel);
        assert(map.static_models.model_references[0]==0x30000009);
        CODOL_FreeCollisionMap(&map); CODOL_UnmountArchives(); assert(handle==19);
    }
    {
        uint8_t bytes[16]="stone";
        codol_load_blocks_t blocks={0};
        blocks.data[3]=bytes; blocks.capacity[3]=sizeof(bytes); blocks.written[3]=6;
        assert(!strcmp(CODOL_LoadBlockString(&blocks,0x30000001),"stone"));
        assert(!CODOL_LoadBlockString(NULL,0x30000001));
        assert(!CODOL_LoadBlockString(&blocks,0));
        assert(!CODOL_LoadBlockString(&blocks,UINT32_MAX));
        assert(!CODOL_LoadBlockString(&blocks,UINT32_MAX-1));
        assert(!CODOL_LoadBlockString(&blocks,1));
        assert(!CODOL_LoadBlockString(&blocks,0x20000001));
        assert(!CODOL_LoadBlockString(&blocks,0x30000007));
        blocks.written[3]=5; /* allocator padding cannot terminate the string */
        assert(!CODOL_LoadBlockString(&blocks,0x30000001));
        blocks.written[3]=17;
        assert(!CODOL_LoadBlockString(&blocks,0x30000001));
    }
    {
        char a[]="/tmp/codol-group-a-XXXXXX",b[]="/tmp/codol-group-b-XXXXXX";
        const char *paths[]={a,b}; const codol_engine_rawfile_t *old,*current;
        FILE *file; size_t failed=99; unsigned asset=0;
        mount_source((const uint8_t *)"base",4);
        write_source_ex((const uint8_t *)"map_a",5,0,a);
        write_source_ex((const uint8_t *)"map_b",5,0,b);
        { unsigned i; uint8_t word[4];
          for(i=0;i<2;++i) {
            file=fopen(paths[i],"r+b"); assert(file);
            put32(word,512); assert(!fseek(file,8,SEEK_SET) && fwrite(word,1,4,file)==4);
            put32(word,1024); assert(!fseek(file,20,SEEK_SET) && fwrite(word,1,4,file)==4 && !fclose(file));
          }
        }
        file=fopen(b,"r+b"); assert(file && !fseek(file,88+8,SEEK_SET));
        assert(fputc('o',file)!=EOF && !fclose(file)); /* maps/mp/oative.gsc */
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,&failed,&asset));
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&old)==1 && !strcmp(old->buffer,"map_a"));
        assert(!CODOL_ReplaceRuntimeArchives(NULL,0,NULL,1,&failed,&asset) && failed==0);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&current)==1 && current==old);
        { char missing[128]; const char *bad_paths[]={b,missing};
          snprintf(missing,sizeof(missing),"%s/missing",a);
          assert(!CODOL_ReplaceRuntimeArchives(bad_paths,2,NULL,1,&failed,&asset) && failed==1);
          assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&current)==1 && current==old);
        }
        assert(CODOL_ReplaceRuntimeArchives(paths+1,1,NULL,1,&failed,&asset));
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&current)==1 && !strcmp(current->buffer,"base"));
        assert(!strcmp(old->buffer,"map_a")); /* retired borrowed cache stays alive */
        assert(CODOL_LoadEngineRawFile("maps/mp/oative.gsc",&current)==1 && !strcmp(current->buffer,"map_b"));
        assert(!CODOL_ReplaceRuntimeArchives(paths,1,NULL,0,&failed,&asset));
        CODOL_UnmountArchives(); unlink(a); unlink(b);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&current)==0);
    }
    {
        /* Two geometry records, one brush, inline and pooled side planes. */
        uint8_t bytes[319]={0},pool[40]={0}; unsigned i;
        codol_mounted_model_physics_t source={0}; codol_physics_map_t map={0},before;
        put32(bytes,UINT32_MAX); put32(bytes+4,2); put32(bytes+8,UINT32_MAX);
        for (i=0;i<9;++i) { float value=(float)(i+1); memcpy(bytes+12+4*i,&value,4); }
        memcpy(bytes+72,"p",2); put32(bytes+74,UINT32_MAX);
        bytes[210+24]=2; put32(bytes+210+28,UINT32_MAX);
        put32(bytes+210+32,UINT32_MAX); put32(bytes+210+60,5);
        put32(bytes+210+64,0x30000001);
        put32(bytes+278,UINT32_MAX); put32(bytes+286,0x30000015);
        source.asset=(codol_asset_t){1,bytes,sizeof(bytes)};
        source.blocks[3]=(codol_model_block_t){pool,sizeof(pool)};
        assert(CODOL_ReadPhysicsMap(&source,&map)); before=map;
        assert(map.count==2 && !strcmp(map.name,"p"));
        for (i=0;i<3;++i) {
            assert(map.center_of_mass[i]==(float)(i+1));
            assert(map.moments_of_inertia[i]==(float)(i+4));
            assert(map.products_of_inertia[i]==(float)(i+7));
        }
        assert(map.geometries[0].brush==bytes+210 && !map.geometries[1].brush);
        assert(map.geometries[0].side_count==2 && map.geometries[0].side_planes[0]==bytes+294);
        assert(map.geometries[0].side_planes[1]==pool+20 && map.geometries[0].planes==pool);
        assert(map.geometries[0].adjacency==bytes+314 && map.geometries[0].adjacency_size==5);
        for (i=0;i<sizeof(bytes);++i) {
            source.asset.size=i; assert(!CODOL_ReadPhysicsMap(&source,&map));
            assert(!memcmp(&map,&before,sizeof(map)));
        }
        source.asset.size=sizeof(bytes); source.blocks[3].size=39;
        assert(!CODOL_ReadPhysicsMap(&source,&map) && map.geometries==before.geometries);
        source.blocks[3].size=40; put32(bytes+286,0x20000001);
        assert(!CODOL_ReadPhysicsMap(&source,&map)); put32(bytes+286,0x30000015);
        for (i=0;i<9;++i) {
            uint8_t saved[4]; unsigned invalid;
            static const uint32_t invalid_bits[]={0x7fc00000,0x7f800000,0xff800000};
            memcpy(saved,bytes+12+4*i,4);
            for (invalid=0;invalid<3;++invalid) {
                put32(bytes+12+4*i,invalid_bits[invalid]);
                assert(!CODOL_ReadPhysicsMap(&source,&map));
                assert(!memcmp(&map,&before,sizeof(map)));
            }
            memcpy(bytes+12+4*i,saved,4);
        }
        assert(CODOL_ReadPhysicsMap(&source,&map));
        CODOL_FreePhysicsMap(&map); CODOL_FreePhysicsMap(&map);
        {
            uint8_t inline_planes[359]={0};
            memcpy(inline_planes,bytes,sizeof(bytes)); put32(inline_planes+210+64,UINT32_MAX);
            source.asset=(codol_asset_t){1,inline_planes,sizeof(inline_planes)};
            assert(CODOL_ReadPhysicsMap(&source,&map) && map.geometries[0].planes==inline_planes+319);
            CODOL_FreePhysicsMap(&map);
            source.asset=(codol_asset_t){1,bytes,sizeof(bytes)};
        }
        memset(bytes,0,sizeof(bytes)); put32(bytes,0x30000001);
        memcpy(pool,"empty",6); source.asset.size=72;
        assert(CODOL_ReadPhysicsMap(&source,&map) && !map.count && !strcmp(map.name,"empty"));
        put32(bytes+4,1); assert(!CODOL_ReadPhysicsMap(&source,&map));
        CODOL_FreePhysicsMap(&map);
    }
    {
        uint8_t header[72]={0},records[2][68]={{0}}; unsigned i;
        codol_physics_geometry_t geometries[2]={{0}};
        codol_physics_map_t source={0}; codol_native_physics_map_t native={0},saved;
        source.name="primitives"; source.header=header; source.count=2; source.geometries=geometries;
        source.center_of_mass[0]=3; source.moments_of_inertia[1]=4; source.products_of_inertia[2]=-5;
        for (i=0;i<2;++i) {
            geometries[i].record=records[i]; put32(records[i]+4,i ? 5 : 1);
            put32(records[i]+8,0x3f800000); put32(records[i]+24,0x3f800000); put32(records[i]+40,0x3f800000);
            put32(records[i]+44,0x40000000); put32(records[i]+56,0x40400000); put32(records[i]+60,0x40800000);
        }
        assert(CODOL_BuildNativePhysicsMap(&source,&native)); saved=native;
        assert(native.map.count==2 && native.map.geoms[0].type==1 && native.map.geoms[1].type==4);
        assert(native.map.geoms[1].offset[0]==2 && native.map.geoms[1].halfLengths[0]==3 && native.map.geoms[1].halfLengths[1]==4);
        assert(native.map.geoms[1].orientation[2][2]==1 && !native.map.geoms[1].brush);
        assert(native.map.mass.centerOfMass[0]==3 && native.map.mass.momentsOfInertia[1]==4 && native.map.mass.productsOfInertia[2]==-5);
        for (i=0;i<8;++i) if (i!=1 && i!=5) {
            put32(records[1]+4,i); assert(!CODOL_BuildNativePhysicsMap(&source,&native));
            assert(!memcmp(&native,&saved,sizeof(native)));
        }
        put32(records[1]+4,5); geometries[1].brush=header;
        assert(!CODOL_BuildNativePhysicsMap(&source,&native)); geometries[1].brush=NULL;
        put32(records[1]+8,0x7fc00000); assert(!CODOL_BuildNativePhysicsMap(&source,&native)); put32(records[1]+8,0x3f800000);
        put32(records[1]+56,0xbf800000); assert(!CODOL_BuildNativePhysicsMap(&source,&native)); put32(records[1]+56,0x40400000);
        assert(CODOL_BuildNativePhysicsMap(&source,&native));
        memset(records,0,sizeof(records)); memset(header,0,sizeof(header)); source.center_of_mass[0]=0;
        assert(native.map.geoms[1].type==4 && native.map.geoms[1].halfLengths[0]==3 && native.map.mass.centerOfMass[0]==3);
        assert(!strcmp(native.name,"primitives"));
        CODOL_FreeNativePhysicsMap(&native); CODOL_FreeNativePhysicsMap(&native);
    }
    {
        uint8_t bytes[74]={0}; unsigned i;
        codol_mounted_model_physics_t source={0};
        codol_native_physics_preset_t native={0},before;
        put32(bytes,UINT32_MAX); put32(bytes+28,UINT32_MAX);
        put32(bytes+8,0x41200000); put32(bytes+12,0x3f000000);
        put32(bytes+40,0x3f800001); /* Nonzero byte 40 must not select cylinder. */
        bytes[65]=255; memcpy(bytes+68,"box\0s",6);
        source.asset=(codol_asset_t){0,bytes,sizeof(bytes)};
        assert(CODOL_BuildNativePhysicsPreset(&source,&native)); before=native;
        assert(!native.preset.tempDefaultToCylinder && native.preset.mass==10 && native.preset.bounce==0.5f);
        assert(!memcmp(native.source.extended,bytes+40,28));
        for(i=0;i<sizeof(bytes);++i) {
            source.asset.size=i; assert(!CODOL_BuildNativePhysicsPreset(&source,&native));
            assert(!memcmp(&native,&before,sizeof(native)));
        }
        source.asset.size=sizeof(bytes);
        memset(bytes+68,0,6);
        assert(!strcmp(native.preset.name,"box") && !strcmp(native.preset.sndAliasPrefix,"s"));
        CODOL_FreeNativePhysicsPreset(&native); CODOL_FreeNativePhysicsPreset(&native);
        memcpy(bytes+68,"box\0s",6);
        for(i=1;i<=255;i+=254) {
            bytes[64]=i;
            assert(CODOL_BuildNativePhysicsPreset(&source,&native));
            assert(native.preset.tempDefaultToCylinder);
            CODOL_FreeNativePhysicsPreset(&native);
        }
    }
    {
        uint8_t bytes[74]={0},pool[6]={'b','o','x',0,'s',0};
        codol_mounted_model_physics_t source={0}; codol_physics_preset_t preset={0},before;
        unsigned i;
        put32(bytes,UINT32_MAX); put32(bytes+28,UINT32_MAX);
        put32(bytes+8,0x41200000); put32(bytes+12,0x3f000000); put32(bytes+40,0x3f800000);
        memcpy(bytes+68,pool,6); source.asset=(codol_asset_t){0,bytes,sizeof(bytes)};
        assert(CODOL_ReadPhysicsPreset(&source,&preset)); before=preset;
        assert(preset.mass==10 && preset.bounce==0.5f && !strcmp(preset.name,"box") && !strcmp(preset.sound_prefix,"s"));
        assert(!memcmp(preset.extended,bytes+40,28));
        for (i=0;i<sizeof(bytes);++i) {
            source.asset.size=i; assert(!CODOL_ReadPhysicsPreset(&source,&preset));
            assert(!memcmp(&preset,&before,sizeof(preset)));
        }
        source.asset.size=sizeof(bytes); put32(bytes+8,0x7fc00000);
        assert(!CODOL_ReadPhysicsPreset(&source,&preset)); put32(bytes+8,0x41200000);
        memset(bytes+68,0,6); assert(!strcmp(preset.name,"box") && !strcmp(preset.sound_prefix,"s"));
        CODOL_FreePhysicsPreset(&preset);
        put32(bytes,0x30000001); put32(bytes+28,0x30000005); source.asset.size=68;
        source.blocks[3]=(codol_model_block_t){pool,sizeof(pool)};
        assert(CODOL_ReadPhysicsPreset(&source,&preset)); before=preset;
        source.blocks[3].size=5;
        assert(!CODOL_ReadPhysicsPreset(&source,&preset) && !memcmp(&preset,&before,sizeof(preset)));
        memset(pool,0,sizeof(pool)); assert(!strcmp(preset.name,"box") && !strcmp(preset.sound_prefix,"s"));
        CODOL_FreePhysicsPreset(&preset);
    }
    {
        uint8_t data[610]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t asset={0},before; codol_mounted_model_physics_t physics,saved;
        char path[]="/tmp/codol-model-physics-XXXXXX"; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,512); put32(data+20,1024);
        put32(data+48,3); put32(data+52,UINT32_MAX);
        put32(data+60,64); put32(data+64,UINT32_MAX-1); put32(data+68,70);
        put32(data+72,1); put32(data+76,134); put32(data+80,UINT32_MAX); put32(data+84,74);
        put32(data+88,4); put32(data+92,208); put32(data+96,UINT32_MAX); put32(data+100,362);
        put32(data+104,UINT32_MAX); memcpy(data+172,"p",2);
        put32(data+174,UINT32_MAX); memcpy(data+246,"p",2);
        put32(data+248,UINT32_MAX); memcpy(data+608,"m",2);
        put32(data+600,0x30000009); put32(data+604,0x30000019);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ResolvePhysicsAlias(&blocks,0,0x30000031,&asset) && asset.type==0 && asset.size==70);
        before=asset;
        assert(!CODOL_ResolvePhysicsAlias(&blocks,1,0x30000009,&asset));
        assert(!CODOL_ResolvePhysicsAlias(&blocks,0,0x30000019,&asset));
        assert(!memcmp(&asset,&before,sizeof(asset)));
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        { const char *paths[]={path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
        assert(CODOL_LoadMountedModelPhysics("m",0,&physics)==1 && physics.asset.type==0);
        assert(!strcmp(physics.name,"p") && !physics.blocks[0].data);
        assert(CODOL_LoadMountedModelPhysics("m",1,&physics)==1 && physics.asset.type==1);
        saved=physics;
        assert(CODOL_LoadMountedModelPhysics("m",2,&physics)==-1 && !memcmp(&physics,&saved,sizeof(physics)));
        put32(data+604,0); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        { const char *paths[]={path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
        assert(CODOL_LoadMountedModelPhysics("m",1,&physics)==0 && !memcmp(&physics,&saved,sizeof(physics)));
        CODOL_UnmountArchives(); unlink(path);
    }
    {
        uint8_t bytes[100]={0}; char name[]="mat";
        codol_mounted_model_material_t source={0}; codol_native_material_t native={0},before;
        unsigned i;
        put32(bytes,UINT32_MAX); bytes[4]=129; bytes[5]=17; bytes[6]=4; bytes[7]=8;
        put32(bytes+16,0x81234567); memcpy(bytes+96,"mat",4);
        source.asset=(codol_asset_t){5,bytes,sizeof(bytes)}; source.name=name;
        assert(CODOL_BuildNativeMaterial(&source,&native)); before=native;
        assert((unsigned char)native.material.info.gameFlags==129 && native.material.info.sortKey==17);
        assert(native.material.info.textureAtlasRowCount==4 && native.material.info.textureAtlasColumnCount==8);
        assert((uint32_t)native.material.info.surfaceTypeBits==0x81234567);
        assert(!native.material.techniqueSet && !native.material.textureTable && !native.material.constantTable);
        assert(!native.material.textureCount && !native.material.constantCount && !native.material.stateBitsCount);
        for (i=0;i<sizeof(native.material.stateBitsEntry);++i) assert((unsigned char)native.material.stateBitsEntry[i]==255);
        for (i=0;i<sizeof(bytes);++i) {
            source.asset.size=i; assert(!CODOL_BuildNativeMaterial(&source,&native));
            assert(!memcmp(&native,&before,sizeof(native)));
        }
        source.asset.size=sizeof(bytes); source.name=",mat";
        assert(!CODOL_BuildNativeMaterial(&source,&native));
        memset(bytes,0,sizeof(bytes)); memset(name,0,sizeof(name));
        assert(!strcmp(native.material.info.name,"mat")); CODOL_FreeNativeMaterial(&native);
        assert(!native.owned_name && !native.material.info.name);
    }
    {
        uint8_t data[586]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        codol_asset_t asset={0},saved; const codol_mounted_model_surfaces_t *surfaces,*same;
        codol_native_model_mesh_t mesh={0};
        char path[]="/tmp/codol-surface-alias-XXXXXX"; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,512); put32(data+20,1024);
        put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+56,3); put32(data+60,48); put32(data+64,UINT32_MAX-1); put32(data+68,136);
        put32(data+72,4); put32(data+76,184); put32(data+80,UINT32_MAX); put32(data+84,362);
        put32(data+88,UINT32_MAX); put32(data+92,UINT32_MAX); data[96]=1;
        memcpy(data+136,"lod",4);
        put32(data+224,UINT32_MAX); data[230]=1; data[300]=1;
        put32(data+304,0x30000009); data[521]=1; memcpy(data+584,"m",2);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)));
        assert(CODOL_ReplayZone(&zone,&blocks,NULL));
        assert(CODOL_ResolveSurfaceAlias(&blocks,0x30000009,&asset)); saved=asset;
        assert(asset.type==3 && asset.size==136);
        assert(CODOL_ResolveSurfaceAlias(&blocks,0x30000021,&asset) && asset.data==saved.data);
        assert(!CODOL_ResolveMaterialAlias(&blocks,0x30000009,&asset));
        assert(!CODOL_ResolveSurfaceAlias(&blocks,0x3000000a,&asset));
        assert(!memcmp(&asset,&saved,sizeof(asset)));
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        { const char *paths[]={path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
        assert(CODOL_LoadMountedModelSurfaces("m",0,&surfaces)==1);
        assert(surfaces->source.count==1 && !strcmp(surfaces->source.name,"lod"));
        assert(CODOL_LoadMountedModelSurfaces("m",0,&same)==1 && same==surfaces);
        assert(CODOL_LoadNativeModelMesh("m",&mesh)==1 && mesh.count==1);
        {
            native_collision_counts_t strings={0}; const XModel *missing=NULL;
            /* This fixture intentionally has no material definition. Native
             * construction must unwind its mesh instead of publishing it. */
            assert(CODOL_LoadMountedCollisionXModel("m",native_collision_acquire,native_collision_release,&strings,&missing)==-1);
            assert(!missing && !strings.live && !strings.acquired);
        }
        {
            uint8_t patch[503]={0}; char patch_path[]="/tmp/codol-surface-stub-XXXXXX";
            codol_model_block_t base_views[8];
            put32(patch,sizeof(patch)-40); put32(patch+8,512); put32(patch+20,1024);
            put32(patch+48,2); put32(patch+52,UINT32_MAX);
            put32(patch+56,3); put32(patch+60,48); put32(patch+64,UINT32_MAX); put32(patch+68,53);
            put32(patch+72,4); put32(patch+76,101); put32(patch+80,UINT32_MAX); put32(patch+84,362);
            put32(patch+88,UINT32_MAX); memcpy(patch+136,",lod",5);
            put32(patch+141,UINT32_MAX); patch[147]=1; patch[217]=1;
            put32(patch+221,0x30000009); patch[438]=1; memcpy(patch+501,"m",2);
            fd=mkstemp(patch_path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
            { const char *paths[]={patch_path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
            assert(CODOL_LoadMountedModelSurfaces("m",0,&surfaces)==1 && surfaces!=same);
            assert(CODOL_MountedBlockViews(1,base_views));
            assert(surfaces->blocks[3].data==base_views[3].data);
            assert(surfaces->source.count==1 && !strcmp(surfaces->source.name,"lod"));
            same=surfaces;
            {
                uint8_t replacement[208]={0}; char replacement_path[]="/tmp/codol-surface-override-XXXXXX";
                const codol_mounted_model_surfaces_t *old=surfaces,*fresh;
                const char *paths[]={replacement_path};
                put32(replacement,sizeof(replacement)-40); put32(replacement+8,512); put32(replacement+20,1024);
                put32(replacement+48,1); put32(replacement+52,UINT32_MAX);
                put32(replacement+56,3); put32(replacement+60,32);
                put32(replacement+64,UINT32_MAX); put32(replacement+68,136);
                memcpy(replacement+72,data+88,136);
                replacement[124]=7; /* Surface header tile mode after root48 + name4. */
                fd=mkstemp(replacement_path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
                assert(fwrite(replacement,1,sizeof(replacement),file)==sizeof(replacement) && !fclose(file));
                assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
                assert(CODOL_LoadMountedModelSurfaces("m",0,&fresh)==1 && fresh!=old);
                assert(CODOL_MountedBlockViews(0,base_views));
                assert(fresh->blocks[3].data==base_views[3].data);
                assert(fresh->source.surfaces[0].header[0]==7 && old->source.surfaces[0].header[0]==0);
                assert(old->source.count==1 && !strcmp(old->source.name,"lod"));
                assert(CODOL_LoadMountedModelSurfaces("m",0,&surfaces)==1 && surfaces==fresh);
                file=fopen(replacement_path,"wb"); assert(file);
                assert(fwrite(replacement,1,1,file)==1 && !fclose(file));
                assert(!CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
                assert(CODOL_LoadMountedModelSurfaces("m",0,&surfaces)==1 && surfaces==fresh);
                same=surfaces; unlink(replacement_path);
            }
            /* An absent named dependency must not fall back to an older model. */
            memcpy(patch+136,",bad",5); file=fopen(patch_path,"wb"); assert(file);
            assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
            { const char *paths[]={patch_path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
            assert(CODOL_LoadMountedModelSurfaces("m",0,&surfaces)==-1 && surfaces==same);
            unlink(patch_path);
        }
        CODOL_UnmountArchives();
        assert(mesh.surfaces && mesh.surfaces[0].vertCount==0);
        CODOL_FreeNativeModelMesh(&mesh); unlink(path);
    }
    {
        uint8_t data[662]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0},saved;
        codol_asset_t material={0},unchanged; unsigned failed;
        char path[]="/tmp/codol-material-alias-XXXXXX"; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,512); put32(data+20,1024);
        put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+56,5); put32(data+60,48); put32(data+64,UINT32_MAX); put32(data+68,100);
        put32(data+72,4); put32(data+76,148); put32(data+80,UINT32_MAX); put32(data+84,474);
        put32(data+88,UINT32_MAX); memcpy(data+184,"mat",4);
        put32(data+188,UINT32_MAX); data[194]=3; put32(data+256,UINT32_MAX);
        memcpy(data+548,"m",2); put32(data+550,0x30000009);
        put32(data+554,UINT32_MAX); put32(data+558,0x3000002d);
        put32(data+562,UINT32_MAX); memcpy(data+658,"inl",4);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)));
        assert(CODOL_ReplayZone(&zone,&blocks,&failed));
        assert(blocks.asset_alias_count==6 && !blocks.collect_asset_aliases);
        assert(CODOL_ResolveMaterialAlias(&blocks,0x30000009,&material));
        assert(material.type==5 && material.size==100 && !memcmp(material.data+96,"mat",4));
        assert(CODOL_ResolveMaterialAlias(&blocks,0x3000002d,&material));
        assert(material.size==100 && !memcmp(material.data+96,"inl",4));
        unchanged=material;
        assert(!CODOL_ResolveMaterialAlias(&blocks,0x30000029,&material));
        assert(!CODOL_ResolveMaterialAlias(&blocks,0x3000002e,&material));
        assert(!CODOL_ResolveMaterialAlias(&blocks,1,&material));
        assert(!memcmp(&material,&unchanged,sizeof(material)));
        CODOL_FreeLoadBlocks(&blocks); saved=blocks;
        /* An explicit insertion slot is another alias for the same asset. */
        put32(zone.data+64,UINT32_MAX-1);
        assert(CODOL_ReplayZone(&zone,&blocks,&failed));
        assert(blocks.asset_alias_count==6);
        assert(CODOL_ResolveMaterialAlias(&blocks,0x30000021,&material));
        assert(!memcmp(material.data+96,"mat",4));
        CODOL_FreeLoadBlocks(&blocks); put32(zone.data+64,UINT32_MAX);
        /* Failure after an earlier asset was catalogued must not publish it. */
        --zone.size;
        assert(!CODOL_ReplayZone(&zone,&blocks,&failed) && failed==1);
        assert(!memcmp(&blocks,&saved,sizeof(blocks))); ++zone.size;
        CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        { const char *paths[]={path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
        assert(CODOL_LoadMountedModelMaterial("m",0,&material)==1);
        assert(!memcmp(material.data+96,"mat",4));
        assert(CODOL_LoadMountedModelMaterial("m",1,&material)==1);
        assert(!memcmp(material.data+96,"inl",4));
        unchanged=material;
        assert(CODOL_LoadMountedModelMaterial("m",2,&material)==1 && material.data==unchanged.data);
        assert(CODOL_LoadMountedModelMaterial("m",3,&material)==-1);
        assert(CODOL_LoadMountedModelMaterial("absent",0,&material)==0);
        assert(!memcmp(&material,&unchanged,sizeof(material)));
        {
            uint8_t patch[539]={0}; char patch_path[]="/tmp/codol-material-stub-XXXXXX";
            codol_mounted_model_material_t resolved,before;
            codol_model_block_t base_views[8];
            const Material_t *old_engine,*updated,*again;
            assert(CODOL_LoadEngineMaterial("mat",&old_engine)==1);
            assert(CODOL_LoadEngineMaterial("MAT",&again)==1 && again==old_engine);
            put32(patch,sizeof(patch)-40); put32(patch+8,512); put32(patch+20,1024);
            put32(patch+48,1); put32(patch+52,UINT32_MAX);
            put32(patch+56,4); put32(patch+60,32); put32(patch+64,UINT32_MAX); put32(patch+68,467);
            put32(patch+72,UINT32_MAX); patch[78]=1; put32(patch+140,UINT32_MAX);
            memcpy(patch+432,"m",2); put32(patch+434,UINT32_MAX);
            put32(patch+438,UINT32_MAX); memcpy(patch+534,",mat",5);
            fd=mkstemp(patch_path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            /* A real definition in another model overrides earlier references. */
            put32(patch,sizeof(patch)-41); put32(patch+68,466); patch[432]='n';
            patch[442]=66; memcpy(patch+534,"mat",4);
            assert(fwrite(patch,1,sizeof(patch)-1,file)==sizeof(patch)-1 && !fclose(file));
            { const char *paths[]={patch_path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
            assert(CODOL_LoadMountedModelMaterialSource("m",0,&resolved)==1);
            assert(resolved.asset.data[4]==66 && !strcmp(resolved.name,"mat"));
            assert(CODOL_LoadEngineMaterial("mat",&updated)==1 && updated!=old_engine);
            assert(updated->info.gameFlags==66 && old_engine->info.gameFlags==0);
            assert(!strcmp(old_engine->info.name,"mat"));
            assert(CODOL_LoadEngineMaterial(",mat",&again)==1 && again==updated);
            put32(patch,sizeof(patch)-40); put32(patch+68,467); patch[432]='m';
            memcpy(patch+534,",mat",5); file=fopen(patch_path,"wb"); assert(file);
            assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
            { const char *paths[]={patch_path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
            assert(CODOL_LoadMountedModelMaterialSource("m",0,&resolved)==1);
            assert(!strcmp(resolved.name,"mat") && resolved.asset.size==100);
            assert(CODOL_MountedBlockViews(1,base_views));
            assert(resolved.blocks[3].data==base_views[3].data && !resolved.blocks[0].data);
            before=resolved;
            memcpy(patch+534,",bad",5); file=fopen(patch_path,"wb"); assert(file);
            assert(fwrite(patch,1,sizeof(patch),file)==sizeof(patch) && !fclose(file));
            { const char *paths[]={patch_path}; assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL)); }
            assert(CODOL_LoadMountedModelMaterialSource("m",0,&resolved)==-1);
            assert(!memcmp(&resolved,&before,sizeof(resolved)));
            assert(CODOL_LoadEngineMaterial("bad",&again)==-1 && again==updated);
            assert(CODOL_LoadEngineMaterial("absent",&again)==0 && again==updated);
            unlink(patch_path);
        }
        CODOL_UnmountArchives(); unlink(path);
    }
    {
        uint8_t data[472]={0}; codol_asset_t asset={4,data,sizeof(data)};
        codol_xmodel_materials_t materials={0},saved; unsigned i;
        data[6]=3; put32(data+0x44,UINT32_MAX);
        put32(data+360,UINT32_MAX); put32(data+364,0x30000099);
        put32(data+372,UINT32_MAX); memcpy(data+468,"mat",4);
        assert(CODOL_ReadXModelMaterials(&asset,&materials)); saved=materials;
        assert(materials.count==3 && materials.array_reference==UINT32_MAX && materials.consumed==472);
        assert(materials.materials[0].reference==UINT32_MAX && materials.materials[0].inline_asset.type==5);
        assert(materials.materials[0].inline_asset.data==data+372 && materials.materials[0].inline_asset.size==100);
        assert(materials.materials[1].reference==0x30000099 && !materials.materials[1].inline_asset.data);
        assert(!materials.materials[2].reference && !materials.materials[2].inline_asset.data);
        for(i=0;i<sizeof(data);++i) {
            asset.size=i; assert(!CODOL_ReadXModelMaterials(&asset,&materials));
            assert(!memcmp(&materials,&saved,sizeof(materials)));
        }
        CODOL_FreeXModelMaterials(&materials); assert(!materials.materials && !materials.count);
    }
    {
        uint8_t data[140]={0}; codol_stream_model_t stream={0};
        codol_model_surfaces_t source={0},saved;
        stream.blocks[3]=(codol_model_block_t){data,sizeof(data)};
        put32(data,0x30000031); put32(data+4,0x30000035); data[8]=1;
        memcpy(data+48,"lod",4); data[52]=2;
        assert(CODOL_ReadStreamModelSurfaces(&stream,&source)); saved=source;
        assert(source.count==1 && !strcmp(source.name,"lod"));
        assert(source.surfaces[0].header[0]==2 && source.surfaces[0].relocated_tree_arrays);
        put32(data+4,0x30000081);
        assert(!CODOL_ReadStreamModelSurfaces(&stream,&source));
        assert(!memcmp(&source,&saved,sizeof(source)));
        put32(data+4,0x30000035); put32(data,0x30000089); memset(data+136,'x',4);
        assert(!CODOL_ReadStreamModelSurfaces(&stream,&source));
        assert(!memcmp(&source,&saved,sizeof(source)));
        memset(data,0,sizeof(data));
        assert(!strcmp(source.name,"lod") && source.surfaces[0].header[0]==2);
        CODOL_FreeModelSurfaces(&source);
    }
    {
        uint8_t data[96]={0}; codol_model_block_t blocks[8]={{0}};
        codol_surface_t source={0}; codol_native_rigid_lists_t result={0},saved;
        source.rigid_reference=0x30000001; source.rigid_count=1; source.relocated_tree_arrays=1;
        blocks[3]=(codol_model_block_t){data,sizeof(data)};
        put32(data+8,0x3000000d); /* tree follows list; arrays are elsewhere */
        put32(data+36,1); put32(data+40,0x30000051); /* node at 80 */
        put32(data+44,1); put32(data+48,0x30000049); /* leaf at 72, before node */
        data[72]=123; data[80]=45;
        assert(CODOL_ResolveNativeRigidLists(&source,blocks,&result)); saved=result;
        assert(((uint8_t *)result.lists[0].collisionTree->nodes)[0]==45);
        assert(((uint8_t *)result.lists[0].collisionTree->leafs)[0]==123);
        put32(data+48,0x30000061);
        assert(!CODOL_ResolveNativeRigidLists(&source,blocks,&result));
        assert(!memcmp(&result,&saved,sizeof(result)));
        memset(data,0,sizeof(data));
        assert(((uint8_t *)result.lists[0].collisionTree->leafs)[0]==123);
        CODOL_FreeNativeRigidLists(&result);
    }
    {
        uint8_t data[70]={0};
        codol_surface_t source={0};
        codol_native_rigid_lists_t result={0},saved;
        unsigned i;
        source.rigid_reference=UINT32_MAX; source.rigid_count=1;
        source.rigid_stream=data; source.rigid_stream_size=sizeof(data);
        data[0]=64; data[2]=2; data[4]=3; data[6]=1; put32(data+8,UINT32_MAX);
        put32(data+12,0x3f800000); put32(data+24,0x40000000);
        put32(data+36,1); put32(data+40,UINT32_MAX);
        put32(data+44,1); put32(data+48,UINT32_MAX);
        data[52]=7; data[64]=9; data[68]=11;
        assert(CODOL_BuildNativeRigidLists(&source,&result)); saved=result;
        assert(result.count==1 && result.lists[0].boneOffset==64 && result.lists[0].triOffset==3);
        assert(result.lists[0].collisionTree->trans[0]==1 && result.lists[0].collisionTree->scale[0]==2);
        assert(result.lists[0].collisionTree->nodes[0].aabb.mins[0]==7);
        assert(result.lists[0].collisionTree->nodes[0].childBeginIndex==9);
        assert(result.lists[0].collisionTree->leafs[0].triangleBeginIndex==11);
        {
            codol_native_rigid_lists_t flat={0}; uint32_t bits;
            put32(data+24,0x7f800000);
            assert(CODOL_BuildNativeRigidLists(&source,&flat));
            memcpy(&bits,&flat.lists[0].collisionTree->scale[0],4); assert(bits==0x7f800000);
            CODOL_FreeNativeRigidLists(&flat);
            put32(data+24,0xff800000); assert(!CODOL_BuildNativeRigidLists(&source,&flat));
            put32(data+24,0x7fc00000); assert(!CODOL_BuildNativeRigidLists(&source,&flat));
            put32(data+24,0x40000000);
        }
        {
            uint8_t asset_data[202]={0};
            uint32_t caps[8]={48,0,0,4096},reference;
            codol_load_blocks_t replay={0};
            codol_model_block_t blocks[8];
            codol_surface_t from_replay=source;
            codol_native_rigid_lists_t resolved={0};
            put32(asset_data+4,UINT32_MAX); asset_data[8]=1;
            put32(asset_data+48+40,1); put32(asset_data+48+44,UINT32_MAX);
            memcpy(asset_data+132,data,70);
            assert(CODOL_InitLoadBlocks(&replay,asset_data,sizeof(asset_data),caps,0));
            assert(CODOL_ReplayModelSurfaces(&replay,&reference));
            CODOL_LoadBlockViews(&replay,blocks);
            from_replay.rigid_reference=0x30000055; /* 84-byte surface precedes list */
            from_replay.rigid_stream=NULL;
            assert(CODOL_ResolveNativeRigidLists(&from_replay,blocks,&resolved));
            CODOL_FreeLoadBlocks(&replay);
            assert(resolved.lists[0].collisionTree->nodes[0].childBeginIndex==9);
            assert(resolved.lists[0].collisionTree->leafs[0].triangleBeginIndex==11);
            CODOL_FreeNativeRigidLists(&resolved);
        }
        {
            uint8_t block[82];
            codol_model_block_t blocks[8]={{0}};
            codol_surface_t pooled_source=source;
            codol_native_rigid_lists_t resolved={0},unchanged;
            memset(block,0xff,sizeof(block)); memcpy(block,data,52);
            memcpy(block+64,data+52,16); memcpy(block+80,data+68,2);
            blocks[3]=(codol_model_block_t){block,sizeof(block)};
            pooled_source.rigid_reference=0x30000001; pooled_source.rigid_stream=NULL;
            assert(CODOL_ResolveNativeRigidLists(&pooled_source,blocks,&resolved)); unchanged=resolved;
            assert(resolved.lists[0].collisionTree->nodes[0].aabb.mins[0]==7);
            assert(resolved.lists[0].collisionTree->leafs[0].triangleBeginIndex==11);
            for (i=0;i<sizeof(block);++i) {
                blocks[3].size=i;
                assert(!CODOL_ResolveNativeRigidLists(&pooled_source,blocks,&resolved));
                assert(!memcmp(&resolved,&unchanged,sizeof(resolved)));
            }
            CODOL_FreeNativeRigidLists(&resolved); blocks[3].size=sizeof(block);
            pooled_source=source; pooled_source.rigid_stream_size=12;
            put32(data+8,0x3000000d); /* inline list, pooled tree at block offset 12 */
            assert(CODOL_ResolveNativeRigidLists(&pooled_source,blocks,&resolved));
            memset(block,0,sizeof(block));
            assert(resolved.lists[0].collisionTree->leafs[0].triangleBeginIndex==11);
            CODOL_FreeNativeRigidLists(&resolved); put32(data+8,UINT32_MAX);
        }
        for (i=0;i<sizeof(data);++i) {
            source.rigid_stream_size=i;
            assert(!CODOL_BuildNativeRigidLists(&source,&result));
            assert(!memcmp(&result,&saved,sizeof(result)));
        }
        source.rigid_stream_size=sizeof(data); put32(data+8,0x30000001);
        assert(!CODOL_BuildNativeRigidLists(&source,&result)); put32(data+8,UINT32_MAX);
        put32(data+12,0x7fc00000); assert(!CODOL_BuildNativeRigidLists(&source,&result));
        memset(data,0,sizeof(data));
        assert(result.lists[0].collisionTree->leafs[0].triangleBeginIndex==11);
        CODOL_FreeNativeRigidLists(&result);
        assert(!result.count && !result.lists);
    }
    {
        uint8_t blend[2]={7,0},vertices[64]={0},triangles[6]={0,0,1,0,1,0};
        codol_surface_t source={0};
        codol_model_block_t blocks[8]={{0}};
        codol_surface_arrays_t result={0},saved;
        unsigned i;
        source.header[4]=2; source.header[6]=1; source.header[20]=1;
        source.arrays[0]=(codol_model_array_t){0x30000001,1,2,NULL};
        source.arrays[1]=(codol_model_array_t){0x60000001,2,32,NULL};
        source.arrays[2]=(codol_model_array_t){0x70000001,1,6,NULL};
        blocks[3]=(codol_model_block_t){blend,2}; blocks[6]=(codol_model_block_t){vertices,64};
        blocks[7]=(codol_model_block_t){triangles,6};
        {
            uint8_t rigid[12]={64,0,2,0,0,0,1,0};
            codol_native_surface_geometry_t native={0},saved_native;
            source.rigid_reference=UINT32_MAX; source.rigid_count=1;
            source.rigid_stream=rigid; source.rigid_stream_size=sizeof(rigid);
            source.header[0]=2; source.header[2]=32;
            put32(source.header+52,0x80000000); put32(source.header+64,1);
            assert(CODOL_BuildNativeSurfaceGeometry(&source,blocks,&native)); saved_native=native;
            assert(native.surface.vertCount==2 && native.surface.triCount==1);
            assert(native.surface.vertInfo.vertCount[0]==1 && native.surface.vertInfo.vertsBlend[0]==7);
            assert(native.surface.verts[1].xyz[0]==0 && native.surface.triIndices[2]==1);
            assert(native.surface.vertListCount==1 && native.surface.vertList[0].boneOffset==64);
            assert(native.surface.tileMode==2 && native.surface.deformed==0);
            assert((uint32_t)native.surface.partBits[0]==0x80000000 && native.surface.partBits[3]==1);
            source.header[68]=1;
            assert(!CODOL_BuildNativeSurfaceGeometry(&source,blocks,&native));
            assert(!memcmp(&native,&saved_native,sizeof(native))); source.header[68]=0;
            {
                codol_native_surface_geometry_t skinned={0};
                source.header[1]=1; source.rigid_count=0; source.rigid_reference=0;
                assert(CODOL_BuildNativeSurfaceGeometry(&source,blocks,&skinned));
                assert(skinned.surface.tileMode==2 && skinned.surface.deformed==1);
                CODOL_FreeNativeSurfaceGeometry(&skinned);
                source.header[1]=0; source.rigid_count=1; source.rigid_reference=UINT32_MAX;
            }
            assert(!memcmp(native.source_header,source.header,84));
            source.rigid_reference=0x70000001;
            assert(!CODOL_BuildNativeSurfaceGeometry(&source,blocks,&native));
            assert(!memcmp(&native,&saved_native,sizeof(native)));
            memset(rigid,0,sizeof(rigid));
            assert(native.surface.vertList[0].boneOffset==64);
            CODOL_FreeNativeSurfaceGeometry(&native);
            assert(!native.surface.verts && !native.surface.vertList);
            source.rigid_reference=0; source.rigid_count=0; source.rigid_stream=NULL; source.rigid_stream_size=0;
        }
        assert(CODOL_ResolveSurfaceArrays(&source,blocks,&result)); saved=result;
        {
            codol_surface_t inputs[2]={source,source};
            codol_model_surfaces_t group={0};
            codol_native_lod_geometry_t lod={0},saved_lod;
            inputs[1].header[0]=1; group.count=2; group.surfaces=inputs;
            put32(inputs[1].header+52,0x40000000);
            put32(inputs[1].header+60,0x80000000);
            assert(CODOL_BuildNativeLodGeometry(&group,blocks,&lod)); saved_lod=lod;
            assert(lod.count==2 && lod.surfaces[1].tileMode==1);
            assert((uint8_t *)(lod.surfaces+1)-(uint8_t *)lod.surfaces==56);
            assert(lod.surfaces[0].verts!=lod.surfaces[1].verts);
            assert(lod.surfaces[0].baseTriIndex==0 && lod.surfaces[0].baseVertIndex==0);
            assert(lod.surfaces[1].baseTriIndex==1 && lod.surfaces[1].baseVertIndex==2);
            assert(lod.part_bits[0]==0xc0000000 && lod.part_bits[1]==0 &&
                lod.part_bits[2]==0x80000000 && lod.part_bits[3]==1);
            inputs[1].header[68]=1;
            assert(!CODOL_BuildNativeLodGeometry(&group,blocks,&lod));
            assert(!memcmp(&lod,&saved_lod,sizeof(lod)) && lod.surfaces[1].triIndices[2]==1);
            CODOL_FreeNativeLodGeometry(&lod); assert(!lod.count && !lod.surfaces && !lod.owners);
            {
                codol_mounted_model_surfaces_t mounted={0},bad;
                const codol_mounted_model_surfaces_t *sources[4]={NULL,&mounted,&mounted,NULL};
                codol_xmodel_lods_t meta={0}; codol_native_model_mesh_t mesh={0},saved_mesh;
                codol_surface_t rejected[2];
                inputs[1].header[68]=0;
                mounted.source=group; memcpy(mounted.blocks,blocks,sizeof(blocks));
                meta.first=1; meta.count=3; meta.collision_lod=2;
                meta.lods[1].distance=100; meta.lods[1].surface_count=2; meta.lods[1].surface_index=3;
                meta.lods[2].distance=200; meta.lods[2].surface_count=2;
                assert(CODOL_BuildNativeModelMesh(5,&meta,sources,&mesh)); saved_mesh=mesh;
                assert(mesh.count==4 && mesh.lod_count==2 && mesh.collision_lod==1);
                assert(mesh.lods[0].dist==100 && mesh.lods[1].dist==200 && mesh.lods[1].surfIndex==2);
                assert(mesh.material_indices[0]==3 && mesh.material_indices[1]==4 &&
                    mesh.material_indices[2]==0 && mesh.material_indices[3]==1);
                assert(mesh.surfaces[2].baseTriIndex==0 && mesh.surfaces[3].baseTriIndex==1);
                assert((uint32_t)mesh.lods[1].partBits[0]==0xc0000000);
                assert(mesh.surfaces[0].verts!=mesh.surfaces[2].verts);
                {
                    codol_native_model_core_t core={0},before;
                    int ids[5]={0}; xMaterial_t *materials[5]; unsigned k;
                    char deformation[4];
                    core.model.name="mesh"; core.model.radius=17;
                    for(k=0;k<4;++k) { deformation[k]=mesh.surfaces[k].deformed; mesh.surfaces[k].deformed=0; }
                    for(k=0;k<5;++k) materials[k]=ids+k;
                    assert(CODOL_BindNativeModelMesh(&core,&mesh,materials,5)); before=core;
                    assert(core.model.surfs==mesh.surfaces && core.model.numLods==2 && core.model.collLod==1);
                    assert((unsigned char)core.model.numsurfs==4 && core.model.radius==17);
                    assert(core.model.lodRampType==XMODEL_LOD_RAMP_RIGID);
                    assert(core.model.materialHandles!=materials && core.model.materialHandles[0]==ids+3 &&
                        core.model.materialHandles[1]==ids+4 && core.model.materialHandles[2]==ids);
                    assert(core.model.lodInfo[1].surfIndex==2 && core.model.lodInfo[1].dist==200);
                    materials[3]=NULL;
                    mesh.surfaces[3].deformed=7; /* any nonzero byte, even in the last LOD */
                    assert(!CODOL_BindNativeModelMesh(&core,&mesh,materials,5));
                    assert(!memcmp(&core,&before,sizeof(core)) && core.model.materialHandles[0]==ids+3);
                    materials[3]=ids+3; mesh.lods[1].surfIndex=3;
                    assert(!CODOL_BindNativeModelMesh(&core,&mesh,materials,5));
                    mesh.lods[1].surfIndex=2;
                    assert(!CODOL_BindNativeModelMesh(&core,&mesh,materials,4));
                    assert(!memcmp(&core,&before,sizeof(core)));
                    assert(CODOL_BindNativeModelMesh(&core,&mesh,materials,5));
                    assert(core.model.lodRampType==XMODEL_LOD_RAMP_SKINNED);
                    mesh.surfaces[3].deformed=0;
                    assert(CODOL_BindNativeModelMesh(&core,&mesh,materials,5));
                    assert(core.model.lodRampType==XMODEL_LOD_RAMP_RIGID);
                    for(k=0;k<4;++k) mesh.surfaces[k].deformed=deformation[k];
                    CODOL_FreeNativeModelCore(&core);
                    assert(mesh.surfaces[1].triIndices[2]==1 && !core.model.materialHandles);
                }
                bad=mounted; memcpy(rejected,inputs,sizeof(rejected)); bad.source.surfaces=rejected;
                rejected[1].header[68]=1; sources[2]=&bad;
                assert(!CODOL_BuildNativeModelMesh(5,&meta,sources,&mesh));
                assert(!memcmp(&mesh,&saved_mesh,sizeof(mesh)));
                sources[2]=&mounted; meta.lods[1].surface_index=4;
                assert(!CODOL_BuildNativeModelMesh(5,&meta,sources,&mesh));
                meta.lods[1].surface_index=3; meta.collision_lod=0;
                assert(!CODOL_BuildNativeModelMesh(5,&meta,sources,&mesh));
                assert(!memcmp(&mesh,&saved_mesh,sizeof(mesh)));
                CODOL_FreeNativeModelMesh(&mesh); assert(!mesh.surfaces && !mesh.material_indices);
            }
        }
        for (i=0;i<3;++i) assert(!((uintptr_t)result.arrays[i].data&15));
        assert(result.arrays[0].data[0]==7 && result.arrays[2].data[2]==1);
        blocks[6].size=63; assert(!CODOL_ResolveSurfaceArrays(&source,blocks,&result)); blocks[6].size=64;
        triangles[2]=2; assert(!CODOL_ResolveSurfaceArrays(&source,blocks,&result)); triangles[2]=1;
        put32(vertices,0x7fc00000); assert(!CODOL_ResolveSurfaceArrays(&source,blocks,&result));
        assert(!memcmp(&result,&saved,sizeof(result)));
        memset(blend,0,sizeof(blend)); memset(triangles,0,sizeof(triangles));
        assert(result.arrays[0].data[0]==7 && result.arrays[2].data[2]==1);
        assert(result.arrays[2].reference==0x70000001);
        CODOL_FreeSurfaceArrays(&result);
    }
    {
        uint8_t data[176]={0};
        codol_asset_t asset={3,data,sizeof(data)};
        codol_model_surfaces_t result={0},saved;
        unsigned i;
        put32(data+4,UINT32_MAX); data[8]=1;
        data[48+4]=1; data[48+6]=1; data[48+20]=3;
        put32(data+48+28,UINT32_MAX); put32(data+48+32,UINT32_MAX); put32(data+48+16,UINT32_MAX);
        data[132]=7; data[138]=9; data[170]=11;
        assert(CODOL_ReadModelSurfaces(&asset,&result)); saved=result;
        assert(result.count==1 && !result.unresolved && result.consumed==176);
        assert(result.surfaces[0].arrays[0].count==3 && result.surfaces[0].arrays[0].data[0]==7);
        assert(result.surfaces[0].arrays[1].stride==32 && result.surfaces[0].arrays[1].data[0]==9);
        assert(result.surfaces[0].arrays[2].stride==6 && result.surfaces[0].arrays[2].data[0]==11);
        for (i=0;i<176;++i) {
            asset.size=i; assert(!CODOL_ReadModelSurfaces(&asset,&result));
            assert(!memcmp(&result,&saved,sizeof(result)));
        }
        memset(data,0,sizeof(data));
        assert(result.surfaces[0].arrays[1].data[0]==9);
        CODOL_FreeModelSurfaces(&result);
    }
    {
        uint8_t data[360]={0};
        codol_asset_t asset={4,data,sizeof(data)};
        codol_xmodel_lods_t result={0},saved;
        unsigned i;
        data[0x128]=1; data[0x129]=3;
        data[0x12a]=255;
        put32(data+0x48,0x7fc00000); /* inactive LOD is preserved, not interpreted */
        put32(data+0x48+56,0x42c80000);
        put32(data+0x48+112,0x43480000);
        put32(data+0x48+56+8,0x30000123);
        data[0x48+56+4]=7; data[0x48+56+6]=9;
        data[0x48+56+55]=0xa5;
        assert(CODOL_ReadXModelLods(&asset,&result)); saved=result;
        assert(result.first==1 && result.count==3 && result.lods[1].distance==100);
        assert(result.collision_lod==-1);
        assert(result.lods[1].surface_count==7 && result.lods[1].surface_index==9);
        assert(result.lods[1].surfaces_reference==0x30000123 && result.lods[1].remaining[39]==0xa5);
        for (i=0;i<360;++i) {
            asset.size=i; assert(!CODOL_ReadXModelLods(&asset,&result));
            assert(!memcmp(&result,&saved,sizeof(result)));
        }
        asset.size=360; data[0x129]=5;
        assert(!CODOL_ReadXModelLods(&asset,&result)); data[0x129]=3; data[0x128]=4;
        assert(!CODOL_ReadXModelLods(&asset,&result)); data[0x128]=1;
        put32(data+0x48+56,0x7f800000);
        assert(!CODOL_ReadXModelLods(&asset,&result));
        assert(!memcmp(&result,&saved,sizeof(result)));
    }
    {
        uint8_t data[1239]={0};
        char base[]="/tmp/codol-model-base-XXXXXX",patch[]="/tmp/codol-model-patch-XXXXXX";
        char invalid_geometry[]="/tmp/codol-model-geometry-XXXXXX";
        char missing_surfaces[]="/tmp/codol-model-surfaces-XXXXXX";
        const char *paths[4]={base,patch,invalid_geometry,missing_surfaces};
        const codol_mounted_model_skeleton_t *model,*again;
        const codol_mounted_model_geometry_t *geometry,*geometry_again;
        const codol_xmodel_materials_t *material_slots,*material_slots_again;
        const codol_mounted_model_surfaces_t *surface_asset,*surface_again;
        codol_native_surface_geometry_t native_surface={0};
        codol_native_lod_geometry_t native_lod={0},stream_lod={0};
        codol_native_model_mesh_t model_mesh={0};
        stream_loader_test_t stream_state={0};
        const uint16_t *handles=(const uint16_t *)(uintptr_t)1;
        unsigned handle_count=77;
        bone_string_test_t strings={0,0,0,2,0},other={0};
        static const uint32_t pooled[]={0x30000033,0x30000037,0x30000039,0x30000041,0x3000004d,0x30000051};
        unsigned i,j; int fd; FILE *f;
        assert(CODOL_SetStreamModelLoader(test_stream_loader,&stream_state));
        put32(data,sizeof(data)-40); put32(data+8,1024); put32(data+20,4096);
        put32(data+32,64); put32(data+36,64); /* vertex/index loader blocks */
        put32(data+40,2); put32(data+44,UINT32_MAX); put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+60,UINT32_MAX); memcpy(data+64,"tag",4);
        put32(data+68,4); put32(data+72,60); put32(data+76,UINT32_MAX); put32(data+80,456);
        put32(data+84,4); put32(data+88,516); put32(data+92,UINT32_MAX); put32(data+96,683);
        for (i=0;i<2;++i) {
            uint8_t *h=data+(i ? 556 : 100);
            put32(h,UINT32_MAX); h[4]=2; h[5]=1;
            put32(h+0x13c,0x40000000); /* radius 2 */
            put32(h+0x134,0x90000002); /* model contents differ from surface mask */
            h[0x12b]=0xa5; h[0x15d]=0x12; /* independent load-on-demand metadata */
            put32(h+0x140,0x3f800000); /* center x=1 */
            put32(h+0x14c,0x40000000); /* half-width x=2 */
            for (j=0;j<6;++j) put32(h+44+4*j,i ? pooled[j] : UINT32_MAX);
            memcpy(h+360,i ? "copy" : "base",5);
        }
        data[465]=1; data[467]=1; data[469]=1;
        put32(data+556+0x12c,UINT32_MAX); put32(data+556+0x130,1);
        put32(data+556+0x138,UINT32_MAX);
        data[556+0x129]=4;
        data[556+0x12a]=255;
        for (i=0;i<4;++i) put32(data+556+0x48+56*i,0x42c80000); /* distance 100 */
        put32(data+556+0x50,UINT32_MAX); /* inline LOD 0 surface asset */
        data[556+6]=1; data[556+0x4c]=1; /* one model material and LOD surface */
        put32(data+921+4,UINT32_MAX); data[921+8]=1;
        data[969+4]=1; data[969+6]=1;
        put32(data+969+32,UINT32_MAX); put32(data+969+16,UINT32_MAX);
        put32(data+1091,UINT32_MAX); put32(data+1095,1); /* one collision triangle */
        put32(data+1099,0x3f800000); put32(data+1111,0x40000000);
        put32(data+1123,1); put32(data+1127,0x80000001); put32(data+1131,7);
        put32(data+1135,0x40400000);
        put32(data+1183,0x3f800000); put32(data+1195,0x40000000);
        put32(data+1207,0x40800000);
        for (i=0;i<4;++i) {
            size_t written_size=sizeof(data);
            fd=mkstemp(i==3 ? missing_surfaces : i==2 ? invalid_geometry : i ? patch : base); assert(fd>=0); f=fdopen(fd,"wb"); assert(f);
            data[465]=i==1 ? 2 : 1; /* invalid zone-local bone index in first patch */
            if (i==2) put32(data+556+0x13c,0x7fc00000); /* valid skeleton, NaN radius */
            if (i==3) {
                put32(data+556+0x13c,0x40000000);
                data[556+6]=2; data[556+0x4c]=2; /* declared two, dependency is an empty placeholder */
                data[556+0x4c+56]=1; /* declared one, no dependency reference */
                put32(data+921+4,0); data[921+8]=0;
                memmove(data+969,data+1091,sizeof(data)-1091);
                written_size-=122; /* omit the surface header, vertices and triangles */
                put32(data+921,UINT32_MAX);
                memmove(data+973,data+969,written_size-969); memcpy(data+969,"lod",4); written_size+=4;
                put32(data,written_size-40); put32(data+96,683-122+4);
            }
            assert(fwrite(data,1,written_size,f)==written_size && !fclose(f));
        }
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedXModelSkeleton("COPY",&model)==1);
        assert(!model->skeleton.unresolved && model->skeleton.arrays[0].data[0]==1);
        for (i=0;i<CODOL_MODEL_SKELETON_ARRAYS;++i)
            assert(!((uintptr_t)model->skeleton.arrays[i].data&15));
        assert(model->bone_names.count==2 && !strcmp(model->bone_names.names[0].text,"tag"));
        assert(CODOL_LoadMountedXModelSkeleton("copy",&again)==1 && again==model);
        assert(CODOL_LoadMountedXModelGeometry("COPY",&geometry)==1);
        assert(CODOL_LoadMountedModelMaterials("COPY",&material_slots)==1);
        assert(material_slots->count==1 && !material_slots->array_reference && !material_slots->materials[0].reference);
        assert(CODOL_LoadMountedModelMaterials("copy",&material_slots_again)==1 && material_slots_again==material_slots);
        assert(geometry->collision.count==1 && geometry->collision.surfaces[0].boneIdx==1);
        assert(geometry->collision.surfaces[0].contents==(int)0x80000001 && geometry->collision.surfaces[0].surfFlags==7);
        assert(geometry->collision.surfaces[0].mins[0]==-1 && geometry->collision.surfaces[0].maxs[0]==3);
        assert(geometry->collision.surfaces[0].triangle_count==1 && geometry->collision.surfaces[0].triangles[0][0]==3);
        assert(geometry->bounds.radius==2 && geometry->bounds.mins[0]==-1 && geometry->bounds.maxs[0]==3);
        assert(geometry->bounds.contents==0x90000002);
        assert(geometry->bounds.flags==0xa5);
        assert(geometry->lods.first==0 && geometry->lods.count==4);
        assert(CODOL_LoadMountedModelSurfaces("COPY",0,&surface_asset)==1 && surface_asset->source.count==1);
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==1 && surface_again==surface_asset);
        assert(CODOL_LoadMountedModelSurfaces("copy",1,&surface_again)==0 && surface_again==surface_asset);
        assert(CODOL_LoadMountedModelSurfaces("copy",4,&surface_again)==-1 && surface_again==surface_asset);
        assert(CODOL_LoadNativeModelSurfaceGeometry("copy",0,0,&native_surface)==1);
        assert(CODOL_LoadNativeModelLodGeometry("copy",0,&native_lod)==1);
        assert(CODOL_LoadNativeModelMesh("copy",&model_mesh)==1);
        assert(model_mesh.count==1 && model_mesh.lod_count==4 && model_mesh.collision_lod==-1);
        assert(!stream_state.calls);
        assert(native_lod.count==1 && native_lod.surfaces[0].vertCount==1);
        assert(native_surface.surface.vertCount==1 && native_surface.surface.triCount==1);
        for (i=0;i<4;++i) assert(geometry->lods.lods[i].distance==100);
        assert(geometry->bounds.bone_count==2 && geometry->bounds.bones[0].radiusSquared==4);
        assert(geometry->bounds.bones[0].bounds[0][0]==-1 && geometry->bounds.bones[0].offset[0]==1);
        assert(CODOL_LoadMountedXModelGeometry("copy",&geometry_again)==1 && geometry_again==geometry);
        assert(CODOL_LoadMountedXModelGeometry("absent",&geometry_again)==0 && geometry_again==geometry);
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&strings,&handles,&handle_count)==-1);
        assert(handles==(const uint16_t *)(uintptr_t)1 && handle_count==77 && !strings.live && strings.releases==1);
        strings=(bone_string_test_t){0,0,0,2,1};
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&strings,&handles,&handle_count)==-1);
        assert(!strings.live && strings.releases==2 && handle_count==77);
        strings=(bone_string_test_t){0};
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&strings,&handles,&handle_count)==1);
        assert(handle_count==2 && handles[0]==33 && handles[1]==33 && strings.live==2);
        {
            codol_native_model_core_t core={0},unchanged;
            codol_mounted_model_geometry_t bad=*geometry;
            codol_xmodel_collision_surface_t surface=geometry->collision.surfaces[0];
            assert(CODOL_BuildNativeModelCore(model,geometry,handles,handle_count,&core));
            assert(core.model.numBones==2 && core.model.numRootBones==1);
            assert(core.model.collLod==-1);
            assert(core.model.boneNames==handles && core.model.boneNames[1]==33);
            assert(core.model.parentList[0]==1 && core.model.radius==2 && core.model.mins[0]==-1);
            assert((uint32_t)core.model.contents==0x90000002);
            assert((unsigned char)core.model.flags==0xa5);
            assert(core.model.baseMat==(DObjAnimMat *)model->skeleton.arrays[5].data);
            assert(core.model.boneInfo==(XBoneInfo_t *)geometry->bounds.bones);
            assert(core.model.numCollSurfs==1 && core.model.collSurfs[0].boneIdx==1);
            assert(core.model.collSurfs[0].contents==(int)0x80000001 && core.model.collSurfs[0].surfFlags==7);
            assert(core.model.collSurfs[0].maxs[0]==3);
            assert(core.model.collSurfs[0].collTris==surface.triangles);
            assert(core.model.collSurfs[0].numCollTris==(int)surface.triangle_count);
            unchanged=core; surface.boneIdx=2; bad.collision.surfaces=&surface;
            assert(!CODOL_BuildNativeModelCore(model,&bad,handles,handle_count,&core));
            assert(!memcmp(&core,&unchanged,sizeof(core)));
            assert(!CODOL_BuildNativeModelCore(model,geometry,handles,1,&core));
            assert(!memcmp(&core,&unchanged,sizeof(core)));
            bad=*geometry; bad.bounds.flags=256;
            assert(!CODOL_BuildNativeModelCore(model,&bad,handles,handle_count,&core));
            assert(!memcmp(&core,&unchanged,sizeof(core)));
            CODOL_FreeNativeModelCore(&core);
            assert(!core.model.collSurfs && !core.model.boneNames && strings.live==2);
            assert(geometry->collision.surfaces[0].triangles[0][0]==3);
        }
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&strings,&handles,&handle_count)==1 && strings.calls==2);
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&other,&handles,&handle_count)==-1 && !other.calls);
        assert(CODOL_LoadMountedXModelSkeleton("absent",&again)==0 && again==model);
        assert(CODOL_MountRuntimeArchives(paths+1,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedXModelSkeleton("copy",&again)==-1 && again==model);
        assert(CODOL_LoadMountedModelMaterials("copy",&material_slots_again)==-1 && material_slots_again==material_slots);
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==-1 && surface_again==surface_asset);
        assert(CODOL_LoadMountedXModelGeometry("copy",&geometry_again)==-1 && geometry_again==geometry);
        assert(CODOL_BindMountedModelBoneHandles("copy",test_acquire_bone,test_release_bone,&strings,&handles,&handle_count)==-1 && strings.live==2);
        assert(!CODOL_MountRuntimeArchives(paths+2,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedXModelSkeleton("copy",&again)==-1 && again==model);
        assert(CODOL_LoadMountedXModelGeometry("copy",&geometry_again)==-1 && geometry_again==geometry);
        assert(CODOL_LoadMountedXModelGeometry("copy",&geometry_again)==-1 && geometry_again==geometry);
        assert(CODOL_MountRuntimeArchives(paths+3,1,NULL,NULL,NULL));
        assert(CODOL_LoadMountedXModelSkeleton("copy",&again)==1 && again!=model);
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==-1 && surface_again==surface_asset);
        assert(CODOL_LoadMountedModelSurfaces("copy",1,&surface_again)==-1 && surface_again==surface_asset);
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==-1 && surface_again==surface_asset);
        {
            codol_native_lod_geometry_t unchanged=native_lod;
            assert(CODOL_LoadNativeModelLodGeometry("copy",0,&native_lod)==-1);
            assert(!memcmp(&native_lod,&unchanged,sizeof(native_lod)));
        }
        assert(!CODOL_SetStreamModelLoader(NULL,NULL));
        {
            codol_native_model_mesh_t saved=model_mesh;
            assert(CODOL_LoadNativeModelMesh("copy",&model_mesh)==-1);
            assert(!memcmp(&model_mesh,&saved,sizeof(model_mesh)));
        }
        stream_state.mode=1; /* valid container with the wrong surface name */
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==-1 && surface_again==surface_asset);
        stream_state.mode=2; /* correct name, wrong surface count */
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==-1 && surface_again==surface_asset);
        stream_state.mode=3;
        assert(CODOL_LoadMountedModelSurfaces("copy",0,&surface_again)==1 && surface_again!=surface_asset);
        assert(surface_again->source.count==2 && !strcmp(surface_again->source.name,"lod"));
        i=stream_state.calls;
        assert(CODOL_LoadNativeModelLodGeometry("copy",0,&stream_lod)==1 && stream_state.calls==i);
        assert(stream_lod.count==2 && stream_lod.surfaces[0].tileMode==7);
        assert(!unlink(base) && !unlink(patch) && !unlink(invalid_geometry) && !unlink(missing_surfaces));
        assert(model->skeleton.arrays[0].data[0]==1 && !strcmp(model->bone_names.names[1].text,"tag"));
        assert(geometry->bounds.radius==2 && geometry->bounds.maxs[0]==3);
        assert(geometry->collision.surfaces[0].triangles[0][0]==3 && geometry->bounds.bones[0].radiusSquared==4);
        CODOL_UnmountArchives();
        assert(CODOL_SetStreamModelLoader(NULL,NULL));
        assert(model_mesh.surfaces[0].triIndices[0]==0);
        CODOL_FreeNativeModelMesh(&model_mesh);
        assert(stream_lod.surfaces[0].tileMode==7);
        CODOL_FreeNativeLodGeometry(&stream_lod);
        assert(!strings.live && strings.releases==2);
        assert(native_surface.surface.verts[0].xyz[0]==0 && native_surface.surface.triIndices[2]==0);
        CODOL_FreeNativeSurfaceGeometry(&native_surface);
        assert(native_lod.surfaces[0].triIndices[2]==0);
        CODOL_FreeNativeLodGeometry(&native_lod);
    }
    {
        char good[]="/tmp/codol-prepared-good-XXXXXX",bad[]="/tmp/codol-prepared-bad-XXXXXX";
        const char *paths[2]={good,bad};
        uint8_t word[4],snapshot[64];
        codol_model_block_t views[8],after[8];
        const codol_engine_rawfile_t *raw;
        FILE *f;
        size_t failed=99;
        unsigned asset=99,i;
        write_source_ex((const uint8_t *)"prepared",8,0,good);
        write_source_ex((const uint8_t *)"rejected",8,0,bad);
        for (i=0;i<2;++i) {
            f=fopen(paths[i],"r+b"); assert(f);
            put32(word,64); assert(!fseek(f,8,SEEK_SET) && fwrite(word,1,4,f)==4);
            put32(word,4096); assert(!fseek(f,20,SEEK_SET) && fwrite(word,1,4,f)==4);
            if (i) { put32(word,23); assert(!fseek(f,56,SEEK_SET) && fwrite(word,1,4,f)==4); }
            assert(!fclose(f));
        }
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,&failed,&asset));
        assert(CODOL_MountedBlockViews(0,views) && views[3].size<=sizeof(snapshot));
        memcpy(snapshot,views[3].data,views[3].size);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc",&raw)==1 && raw->len==8);
        assert(!memcmp(raw->buffer,"prepared",8));
        assert(!CODOL_MountRuntimeArchives(paths,2,NULL,&failed,&asset) && failed==1 && asset==0);
        assert(CODOL_MountedBlockViews(0,after) && after[3].data==views[3].data);
        assert(!memcmp(snapshot,after[3].data,views[3].size));
        assert(!CODOL_MountedBlockViews(1,after));
        assert(!unlink(good) && !unlink(bad));
        assert(!memcmp(raw->buffer,"prepared",8)); /* source files no longer exist */
        CODOL_UnmountArchives();
        assert(!CODOL_MountedBlockViews(0,after));
    }
    {
        uint8_t data[1024]={0},empty[1024]={0};
        uint32_t capacities[8]={12,0,0,1024,0,0,0,0};
        codol_zone_t zone={data,0,56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        uint8_t *d,*members;
        size_t n=84,cut,required;
        put32(data+56,39); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); put32(data+76,2); put32(data+80,1); data[n++]='s'; ++n;
        d=data+n; n+=120;
        put32(d+8,1); put32(d+12,1); put32(d+16,1); put32(d+20,1);
        put32(d+24,1); put32(d+28,1); put32(d+32,1); put32(d+36,1);
        put32(d+52,2); put32(d+56,1); put32(d+60+52,1); put32(d+60+56,1);
        put32(data+n,2); put32(data+n+8,1); n+=12;
        put32(data+n,UINT32_MAX); put32(data+n+8,0x30000123); n+=16; data[n++]='a'; ++n;
        members=data+n; put32(members,2); put32(members+4,1); n+=20;
        put32(data+n,UINT32_MAX); put32(data+n+24,UINT32_MAX); n+=48;
        memcpy(data+n,"b\0c",4); n+=4;
        n+=16+16+8+4; data[n-1]=0x62;
        zone.size=n; put32(data+68,n-72);
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72;
        for (cut=72;cut<n;++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],1024));
        }
        zone.size=stream.source_size=n; put32(data+68,n-72);
        put32(members,UINT32_MAX); saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(members,2);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1); required=stream.position[3];
        assert(stream.source_position==n && stream.written[0]==12 && !stream.position[0] && !stream.depth);
        assert(stream.data[3][0]=='s' && stream.data[3][required-1]==0x62);
        CODOL_FreeLoadBlocks(&stream); capacities[3]=required-1;
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],required-1));
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[104]={0};
        uint32_t capacities[8]={16,0,0,32,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,2,0,{0}};
        codol_load_blocks_t stream={0},saved;
        put32(data+56,29); put32(data+60,48); put32(data+64,0x5dcd3c);
        put32(data+72,36); put32(data+76,48); put32(data+80,UINT32_MAX); put32(data+84,16);
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); stream.source_position=88; saved=stream;
        put32(data+68,1);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(data+68,0);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1 && !memcmp(&saved,&stream,sizeof(stream)));
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==1 && stream.source_position==104);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[72+400+65*12]={0},empty[65*12]={0};
        uint32_t capacities[8]={400,0,0,65*12,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        unsigned i;
        put32(data+56,26); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+68,sizeof(data)-72); put32(data+72+0xe0,1);
        for (i=0;i<64;++i) put32(data+472+12*i+8,1);
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); stream.source_position=72; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],sizeof(empty)));
        put32(data+472+63*12+8,0); zone.size=stream.source_size=sizeof(data)-12;
        put32(data+68,zone.size-72);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1 && stream.position[3]==64*12);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[8192]={0},empty[8192]={0};
        uint32_t capacities[8]={1024,0,0,8192,0,0,0,0};
        codol_zone_t zone={data,0,56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        static const unsigned event_offsets[]={0xd0,0xd8,0xd4,0xdc};
        static const unsigned types[]={6,12,13,4,20,21};
        uint8_t *h,*item;
        size_t n=84,cut,required;
        unsigned i;
        put32(data+56,25); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); put32(data+76,2); put32(data+80,1);
        data[n++]='l'; ++n; put32(data+n,0x30000123); put32(data+n+4,UINT32_MAX-1); n+=8;
        h=data+n; n+=400;
        put32(h,UINT32_MAX); data[n++]='m'; ++n;
        put32(h+44,UINT32_MAX); data[n++]='c'; ++n;
        put32(h+160,UINT32_MAX); put32(data+n,UINT32_MAX); n+=96; data[n++]='b'; ++n;
        put32(h+164,UINT32_MAX); data[n++]='f'; ++n;
        for (i=0;i<4;++i) {
            put32(h+event_offsets[i],1); put32(data+n,1); put32(data+n+4,1); n+=8;
            put32(data+n,1); n+=4; put32(data+n,UINT32_MAX); n+=8; data[n++]='0'+i; ++n;
        }
        put32(h+0xe0,1); put32(data+n,13); put32(data+n+4,1); put32(data+n+8,1); n+=12+8;
        put32(data+n,27); n+=12;
        put32(h+0xe4,UINT32_MAX); n+=20;
        put32(h+0xe8,UINT32_MAX); data[n++]='s'; ++n;
        put32(h+0xec,UINT32_MAX); data[n++]='t'; ++n;
        put32(h+0x118,UINT32_MAX); n+=20;
        put32(h+0xb0,7); put32(h+0x11c,1);
        for (i=0;i<6;++i) put32(data+n+4*i,1); n+=28; /* last item is null */
        for (i=0;i<6;++i) {
            item=data+n; n+=380; put32(item+0xb8,types[i]); put32(item+0x134,1);
            if (i==0) {
                put32(item,UINT32_MAX); data[n++]='i'; ++n;
                put32(item+0xe4,UINT32_MAX); data[n++]='x'; ++n;
                put32(item+0x10c,1); n+=8;
                put32(item+0x118,1); n+=12;
                put32(item+0x128,UINT32_MAX); put32(data+n,UINT32_MAX); n+=12; data[n++]='a'; ++n;
                put32(data+n+288,1); put32(data+n+320,UINT32_MAX); n+=324+8+96;
                put32(item+0x13c,1); put32(item+0x140,1); put32(data+n+4,UINT32_MAX); n+=8+20;
                put32(item+0x144,UINT32_MAX); put32(item+0x150,UINT32_MAX); n+=40;
            } else if (i==1) {
                put32(data+n,UINT32_MAX); put32(data+n+252,UINT32_MAX); n+=392;
                data[n++]='u'; ++n; data[n++]='v'; ++n;
            } else if (i==2) {
                put32(item+0x134,UINT32_MAX); data[n++]='d'; ++n;
            } else n+=i==3 ? 32 : i==4 ? 28 : 4;
        }
        data[n-1]=0x61; assert(n<=sizeof(data)); zone.size=n; put32(data+68,n-72);
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72;
        for (cut=72;cut<n;++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],1024) && !memcmp(empty,stream.data[3],8192));
        }
        zone.size=stream.source_size=n; put32(data+68,n-72);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1); required=stream.position[3];
        assert(stream.source_position==n && stream.written[0]==508 && !stream.position[0] && !stream.depth);
        assert(stream.data[3][0]=='l' && stream.data[3][16]=='m' && stream.data[3][required-1]==0x61);
        CODOL_FreeLoadBlocks(&stream); capacities[3]=required-1;
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],required-1));
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[512]={0},empty[512]={0};
        uint32_t capacities[8]={0,0,0,512,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n=44,cut;
        unsigned i;
        put32(data,9); put32(data+4,1);
        for (i=0;i<8;++i) put32(data+8+4*i,1);
        put32(data+n,UINT32_MAX); n+=8; data[n++]='a'; ++n;
        put32(data+n,1); data[n+4]=1; n+=8;
        put32(data+n,1); put32(data+n+4,UINT32_MAX); n+=8+20+8;
        put32(data+n,1); data[n+4]=2; n+=8+8;
        for (i=3;i<=6;++i) {
            put32(data+n,1); data[n+4]=i; n+=8;
            put32(data+n,UINT32_MAX); put32(data+n+4,UINT32_MAX); n+=8;
            data[n++]='0'+i; ++n; n+=20;
        }
        put32(data+n,UINT32_MAX); data[n+4]=7; n+=8;
        assert(n==274);
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3));
        for (cut=0;cut<n;++cut) {
            stream.source_size=cut; saved=stream;
            assert(!CODOL_ReplayMenuEvents(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],512));
        }
        stream.source_size=n; put32(data,UINT32_MAX); saved=stream;
        assert(!CODOL_ReplayMenuEvents(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        put32(data,9); stream.capacity[3]=283; saved=stream;
        assert(!CODOL_ReplayMenuEvents(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=284;
        assert(CODOL_ReplayMenuEvents(&stream,&ref) && ref==0x30000001);
        assert(stream.source_position==274 && stream.position[3]==284 && !stream.depth);
        assert(stream.data[3][52]=='a' && stream.data[3][132]=='3' && stream.data[3][252]=='6');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[64*20+8]={0},empty[sizeof(data)]={0};
        uint32_t capacities[8]={0,0,0,sizeof(data),0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        unsigned i;
        for (i=0;i<64;++i) {
            put32(data+20*i,1); put32(data+20*i+4,1); put32(data+20*i+8,1);
            put32(data+20*i+12,1); data[20*i+16]=2;
        }
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); saved=stream;
        assert(!CODOL_ReplayMenuEvents(&stream,&ref) && ref==123);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],sizeof(data)));
        data[63*20+16]=7; /* No nested payload for an unknown event type. */
        assert(CODOL_ReplayMenuEvents(&stream,&ref) && stream.source_position==64*20);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[168]={0},empty[74]={0};
        uint32_t capacities[8]={24,0,0,74,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        size_t cut;
        put32(data+56,38); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); put32(data+80,2); put32(data+92,1); data[96]='l';
        put32(data+98,UINT32_MAX); put32(data+114,UINT32_MAX);
        put32(data+130,0x30000123); put32(data+146,UINT32_MAX);
        memcpy(data+162,"a\0b\0c",6);
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); stream.source_position=72;
        for (cut=72;cut<sizeof(data);++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],74));
        }
        zone.size=stream.source_size=sizeof(data); put32(data+68,sizeof(data)-72);
        put32(data+80,UINT32_MAX); saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(data+80,2); stream.capacity[3]=73;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(empty,stream.data[3],74));
        stream.capacity[3]=74;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==sizeof(data) && stream.position[3]==74 && !stream.depth);
        assert(stream.data[3][68]=='a' && stream.data[3][70]=='b' && stream.data[3][72]=='c');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[92]={0},empty[94]={0};
        uint32_t capacities[8]={0,0,0,94,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t cut;
        put32(data,3); put32(data+4,1);
        put32(data+20,1); put32(data+24,2); put32(data+28,UINT32_MAX);
        put32(data+32,1); put32(data+36,3); put32(data+40,UINT32_MAX);
        put32(data+48,2); put32(data+52,UINT32_MAX); /* operator: no string */
        data[56]='a'; put32(data+58,1); put32(data+62,1);
        put32(data+78,1); put32(data+82,2); put32(data+86,UINT32_MAX); data[90]='b';
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
        for (cut=0;cut<sizeof(data);++cut) {
            stream.source_size=cut; saved=stream;
            assert(!CODOL_ReplayMenuExpression(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],94));
        }
        stream.source_size=sizeof(data); stream.capacity[3]=93; saved=stream;
        assert(!CODOL_ReplayMenuExpression(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=94;
        assert(CODOL_ReplayMenuExpression(&stream,&ref) && ref==0x30000001);
        assert(stream.source_position==92 && stream.position[3]==94 && !stream.depth);
        assert(stream.data[3][56]=='a' && stream.data[3][92]=='b');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[64*32+20]={0},empty[sizeof(data)]={0};
        uint32_t capacities[8]={0,0,0,sizeof(data),0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        unsigned i;
        for (i=0;i<64;++i) {
            put32(data+32*i,1); put32(data+32*i+4,1);
            put32(data+32*i+20,1); put32(data+32*i+24,3); put32(data+32*i+28,UINT32_MAX);
        }
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); saved=stream;
        assert(!CODOL_ReplayMenuExpression(&stream,&ref) && ref==123);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],sizeof(data)));
        /* A pooled final statement ends recursion without reading its record. */
        put32(data+63*32+28,0x30000123);
        assert(CODOL_ReplayMenuExpression(&stream,&ref) && stream.source_position==64*32);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        unsigned mode,i;
        for (mode=0;mode<2;++mode) {
            uint8_t data[256]={0},empty[128]={0};
            uint32_t capacities[8]={128,0,0,128,0,0,0,0};
            codol_zone_t zone={data,0,56,1,0,{0}};
            codol_load_blocks_t stream={0},saved;
            size_t n,cut,required;
            put32(data+56,mode ? 24 : 43); put32(data+60,32); put32(data+64,UINT32_MAX);
            put32(data+72,UINT32_MAX);
            if (!mode) {
                static const uint32_t types[]={15,16,38,39,40,UINT32_MAX,0};
                put32(data+76,7); put32(data+80,1); data[84]='a';
                for (i=0;i<7;++i) {
                    put32(data+86+12*i+4,types[i]);
                    put32(data+86+12*i+8,i==6 ? 0x30000123 : UINT32_MAX);
                }
                memcpy(data+170,"x\0y\0z",6); n=176; required=94;
            } else {
                put32(data+80,2); put32(data+84,UINT32_MAX-1); put32(data+88,0x30000123);
                put32(data+92,UINT32_MAX); data[96]='f';
                put32(data+98,UINT32_MAX); data[194]='m'; data[243]=0x69;
                n=244; required=60;
            }
            zone.size=n; put32(data+68,n-72);
            assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72;
            for (cut=72;cut<n;++cut) {
                zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
                assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],128) && !memcmp(empty,stream.data[3],128));
            }
            zone.size=stream.source_size=n; put32(data+68,n-72);
            put32(data+(mode ? 80 : 76),UINT32_MAX); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
            put32(data+(mode ? 80 : 76),mode ? 2 : 7);
            stream.capacity[3]=required-1; saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
            stream.capacity[3]=required;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
            assert(stream.source_position==n && stream.position[3]==required);
            assert(stream.written[0]==(mode ? 120 : 12) && !stream.position[0] && !stream.depth);
            if (mode) assert(stream.data[3][8]=='m' && stream.data[3][59]==0x69);
            else assert(stream.data[3][88]=='x' && stream.data[3][90]=='y' && stream.data[3][92]=='z');
            CODOL_FreeLoadBlocks(&stream);
        }
    }
    {
        uint8_t data[8192]={0},empty[8192]={0};
        uint32_t capacities[8]={8192,0,0,4096,0,0,0,0};
        codol_zone_t zone={data,0,56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        uint8_t *h=data+72;
        size_t n=72+0x314,cut,required;
        put32(data+56,41); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(h,UINT32_MAX); data[n++]='v'; ++n;
        put32(h+8,UINT32_MAX); data[n++]='u'; ++n;
        put32(h+0xac,UINT32_MAX); data[n++]='p'; ++n;
        put32(h+0xb0,UINT32_MAX-1); put32(data+n,UINT32_MAX); n+=68; data[n++]='f'; ++n;
        put32(h+0xb4,UINT32_MAX); data[n++]='a'; ++n;
        put32(h+0x190,UINT32_MAX); data[n++]='w'; ++n;
        put32(h+0x194,UINT32_MAX); put32(data+n,UINT32_MAX); n+=0xbfc; data[n++]='g'; ++n;
        put32(h+0x1ac,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='s'; ++n;
        put32(h+0x1b0,0x30000123); h[0x1c8]=7;
        put32(h+0x1d0,UINT32_MAX); put32(data+n,UINT32_MAX); n+=96; data[n++]='m'; ++n;
        put32(h+0x230,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='e'; ++n;
        put32(h+0x238,UINT32_MAX); data[n++]='l'; ++n;
        put32(h+0x23c+30*4,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='z'; ++n;
        assert(n<=sizeof(data)); zone.size=n; put32(data+68,n-72);
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72;
        for (cut=72;cut<n;++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],8192) && !memcmp(empty,stream.data[3],4096));
        }
        zone.size=stream.source_size=n; put32(data+68,n-72);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1); required=stream.position[3];
        assert(stream.source_position==n && stream.written[0]==0x314+0xbfc);
        assert(!stream.position[0] && stream.active==3 && !stream.depth);
        assert(stream.data[3][0]=='v' && stream.data[3][12]=='f' && stream.data[3][required-2]=='z');
        assert(h[0x1c8]==7); /* runtime script strings remain unbound */
        CODOL_FreeLoadBlocks(&stream); capacities[3]=required-1;
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],required-1));
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[173]={0},empty[68]={0};
        uint32_t capacities[8]={36,0,0,68,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        unsigned i; size_t cut;
        put32(data+56,42); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); put32(data+76,1); put32(data+80,3);
        for (i=0;i<3;++i) { put32(data+84+8*i,1); put32(data+88+8*i,1); }
        memcpy(data+108,"a\0{}",5); data[172]=0x71;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3)); stream.source_position=72;
        for (cut=72;cut<sizeof(data);++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],68));
        }
        zone.size=stream.source_size=sizeof(data); put32(data+68,sizeof(data)-72);
        stream.capacity[3]=67; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=68;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==sizeof(data) && stream.position[3]==68 && stream.written[0]==36);
        assert(stream.data[3][2]=='{' && stream.data[3][67]==0x71 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[8192]={0},empty[8192]={0};
        uint32_t capacities[8]={8192,0,0,4096,0,0,0,0};
        codol_zone_t zone={data,0,56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        uint8_t *h=data+72;
        size_t n=72+0xbfc,cut,required;
        put32(data+56,28); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(h,UINT32_MAX); data[n++]='w'; ++n;
        put32(h+0x10,UINT32_MAX-1); put32(data+n,UINT32_MAX); n+=360; data[n++]='m'; ++n;
        put32(h+0x7c,UINT32_MAX); data[n++]='a'; ++n;
        put32(h+0x2b8,UINT32_MAX); data[n++]='z'; ++n;
        put32(h+0x35c,UINT32_MAX); put32(data+n,UINT32_MAX); n+=32; data[n++]='f'; ++n;
        put32(h+0x364,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='s'; ++n;
        put32(h+0x434,UINT32_MAX); put32(data+n,0x30000123); n+=4;
        put32(h+0x438,UINT32_MAX); put32(data+n+120,UINT32_MAX); n+=124;
        put32(data+n,UINT32_MAX); n+=4; data[n++]='r'; ++n;
        put32(h+0x43c,0x30000123);
        put32(h+0x450,UINT32_MAX); put32(data+n,UINT32_MAX); n+=96; data[n++]='i'; ++n;
        put32(h+0x564,UINT32_MAX); data[n++]='d'; ++n;
        put32(h+0x758,UINT32_MAX); put32(data+n,UINT32_MAX); n+=72; data[n++]='p'; ++n;
        put32(h+0x7b0,0x30000123); put32(h+0x8ec,0x30000123);
        h[0xbb0]=2; h[0xbb2]=1;
        put32(h+0x9a0,UINT32_MAX); data[n++]='1'; ++n;
        put32(h+0x9a8,UINT32_MAX); n+=16;
        put32(h+0x9a4,UINT32_MAX); data[n++]='2'; ++n;
        put32(h+0x9ac,UINT32_MAX); n+=8;
        put32(h+0xaa8,UINT32_MAX-1); put32(data+n,UINT32_MAX); put32(data+n+4,UINT32_MAX);
        n+=112; data[n++]='t'; ++n;
        put32(data+n,UINT32_MAX); n+=96; data[n++]='v'; ++n;
        put32(h+0xadc,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='b'; ++n;
        put32(h+0xae0,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='c'; ++n;
        put32(h+0xafc,UINT32_MAX); put32(data+n,UINT32_MAX); n+=4; data[n++]='e'; ++n;
        put32(h+0xbb4,UINT32_MAX); n+=16;
        put32(h+0xbb8,UINT32_MAX); n+=8; data[n-1]=0x65;
        assert(n<=sizeof(data)); zone.size=n; put32(data+68,n-72);
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72;
        for (cut=72;cut<n;++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],8192) && !memcmp(empty,stream.data[3],4096));
        }
        zone.size=stream.source_size=n; put32(data+68,n-72);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        required=stream.position[3];
        assert(stream.source_position==n && stream.written[0]==0xbfc+360);
        assert(!stream.position[0] && stream.active==3 && !stream.depth);
        assert(stream.data[3][0]=='w' && stream.data[3][8]=='m' && stream.data[3][required-1]==0x65);
        assert(h[0x10]==0xfe && h[0x3c]==0); /* source references/indices are not patched */
        CODOL_FreeLoadBlocks(&stream);
        capacities[3]=required-1;
        assert(CODOL_InitLoadBlocks(&stream,data,n,capacities,3)); stream.source_position=72; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],required-1));
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[2356]={0},empty[2250]={0};
        uint32_t capacities[8]={40,0,0,2250,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        size_t cut;
        put32(data+56,31); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,sizeof(data)-72);
        put32(data+72,UINT32_MAX); put32(data+76,1);
        data[80]='i';
        /* The last of 560 references inserts a pointer and loads an effect. */
        put32(data+82,0x30000123);
        put32(data+82+559*4,UINT32_MAX-1);
        put32(data+2322,UINT32_MAX); data[2354]='e';
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
        stream.source_position=72;
        for (cut=72;cut<sizeof(data);++cut) {
            zone.size=stream.source_size=cut; put32(data+68,cut-72); saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],40) && !memcmp(empty,stream.data[3],2250));
        }
        zone.size=stream.source_size=sizeof(data); put32(data+68,sizeof(data)-72);
        stream.capacity[3]=2249; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(empty,stream.data[3],2250));
        stream.capacity[3]=2250;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==sizeof(data) && stream.position[3]==2250);
        assert(stream.written[0]==40 && stream.position[0]==0 && stream.active==3 && !stream.depth);
        assert(stream.data[3][0]=='i' && stream.data[3][2248]=='e');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[758]={0},empty[624]={0};
        uint32_t capacities[8]={300,0,128,624,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n=256,cut;
        unsigned i;
        put32(data+8,1); put32(data+12,UINT32_MAX);
        put32(data+32,1); put32(data+36,1); put32(data+40,1); put32(data+44,1);
        put32(data+64,1); put32(data+68,1); put32(data+96,1); put32(data+100,1); put32(data+104,1);
        put32(data+116,1); put32(data+120,1); put32(data+124,1); put32(data+128,1);
        data[140]=1; put32(data+144,1); put32(data+148,1); put32(data+152,1);
        put32(data+156,UINT32_MAX); data[160]=1; put32(data+164,1);
        data[168]=1; data[170]=1;
        for (i=172;i<=200;i+=4) put32(data+i,1);
        n+=20; put32(data+n,UINT32_MAX); n+=28; data[n++]=7;
        data[n+2]=1; put32(data+n+8,UINT32_MAX); n+=22;
        n+=6+4; put32(data+n+8,UINT32_MAX); n+=12+28+32;
        data[n]=1; put32(data+n+4,UINT32_MAX); put32(data+n+8,UINT32_MAX); data[n+30]=1;
        n+=36; put32(data+n,UINT32_MAX); n+=28; data[n++]=9;
        n+=24+4+28+44+184; assert(n==sizeof(data));
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (cut=0;cut<sizeof(data);++cut) {
            stream.source_size=cut; saved=stream;
            assert(!CODOL_ReplayCollision(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],300) && !memcmp(empty,stream.data[3],624));
            assert(!memcmp(empty,stream.data[2],128));
        }
        stream.source_size=sizeof(data); stream.capacity[2]=127; saved=stream;
        assert(!CODOL_ReplayCollision(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[2]=128;
        assert(CODOL_ReplayCollision(&stream,&ref) && ref==1);
        assert(stream.source_position==758 && stream.position[3]==624 && stream.position[2]==128);
        assert(stream.data[3][48]==7 && stream.data[3][320]==9);
        assert(stream.active==0 && !stream.depth && stream.position[0]==256);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[151]={0},empty[110]={0};
        uint32_t capacities[8]={44,0,0,110,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        unsigned i;
        put32(data,UINT32_MAX); put32(data+4,1); put32(data+8,3);
        for (i=12;i<=28;i+=8) { put32(data+i,1); put32(data+i+4,1); }
        put32(data+36,1); data[40]=2; data[44]='m'; memcpy(data+46,"{}",3);
        put32(data+109,UINT32_MAX); put32(data+129,0x30000123); data[149]='s';
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayMapEntities(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],44) && !memcmp(empty,stream.data[3],110));
        }
        stream.source_size=sizeof(data); stream.capacity[3]=109; saved=stream;
        assert(!CODOL_ReplayMapEntities(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=110;
        assert(CODOL_ReplayMapEntities(&stream,&ref) && ref==1);
        assert(stream.source_position==151 && stream.position[3]==110 && stream.data[3][108]=='s');
        assert(stream.active==0 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[482]={0},empty[332]={0},*h=data+72;
        uint32_t capacities[8]={84,0,0,332,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        size_t n;
        put32(data+56,18); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(h,UINT32_MAX); memset(h+4,0xa5,68);
        put32(h+72,UINT32_MAX); put32(h+76,1); put32(h+80,1); h[84]='w';
        put32(h+86,UINT32_MAX); h[130]='s';
        put32(h+90,1); put32(h+94,1); put32(h+98,1); put32(h+102,1);
        put32(h+132+52,1); put32(h+132+56,1);
        put32(h+204,UINT32_MAX); put32(h+208,UINT32_MAX); h[252]='c';
        put32(h+254,1); put32(h+258,1); put32(h+266,1); put32(h+270,1);
        put32(h+394,UINT32_MAX); h[400]=1; put32(h+402,1); h[406]='g'; h[408]=7;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
        stream.source_position=72;
        for (n=72;n<sizeof(data);++n) {
            put32(data+68,n-72); zone.size=n; stream.source_size=n; saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],84) && !memcmp(empty,stream.data[3],332));
        }
        put32(data+68,410); zone.size=sizeof(data); stream.source_size=sizeof(data);
        stream.capacity[3]=331; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=332;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==482 && stream.position[3]==332 && stream.position[0]==0);
        assert(!memcmp(empty,stream.data[0]+4,68) && h[4]==0xa5 && stream.data[3][330]==7);
        assert(stream.active==3 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[848]={0},empty[628]={0};
        uint32_t capacities[8]={628,0,432,220,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        uint8_t *p=data+456,*d=data+564;
        size_t n;
        unsigned i;
        put32(data+16,1); put32(p,1); put32(p+4,1); put32(p+8,1); put32(p+48,1);
        for (i=52;i<=100;i+=4) put32(p+i,1);
        put32(d,1); put32(d+4,2);
        for (i=16;i<=44;i+=4) put32(d+i,1);
        put32(data+616,1); put32(data+620,1);
        put32(data+684,0x30000123); put32(data+768,0x30000123); data[847]=9;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayWorld(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],628) && !memcmp(empty,stream.data[3],220));
            assert(!memcmp(empty,stream.data[2],432));
        }
        stream.source_size=sizeof(data); put32(p+4,UINT32_MAX); saved=stream;
        assert(!CODOL_ReplayWorld(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        put32(p+4,1); stream.capacity[2]=431; saved=stream;
        assert(!CODOL_ReplayWorld(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[2]=432;
        assert(CODOL_ReplayWorld(&stream,&ref) && ref==1);
        assert(stream.source_position==848 && stream.position[3]==220 && stream.position[2]==432);
        assert(stream.data[3][219]==9 && stream.active==0 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[840]={0},empty[32789]={0};
        uint32_t capacities[8]={628,0,32789,212,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        unsigned i;
        put32(data+32,2); put32(data+208,1); put32(data+212,1);
        put32(data+244,1); put32(data+248,1); put32(data+688,0x30000123);
        put32(data+572,1); put32(data+576,1);
        for (i=416;i<=452;i+=4) put32(data+i,1);
        data[696]=1; data[698]=1; put32(data+700,1); put32(data+704,1);
        data[720]=7; data[722]=9;
        put32(data+724,1); put32(data+728,1);
        put32(data+740+72,1); put32(data+740+76,1); data[839]=11;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayWorldScene(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],628) && !memcmp(empty,stream.data[3],212));
            assert(!memcmp(empty,stream.data[2],32789));
        }
        stream.source_size=sizeof(data); put32(data+28,2); saved=stream;
        assert(!CODOL_ReplayWorldScene(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        put32(data+28,0); stream.capacity[2]=32788; saved=stream;
        assert(!CODOL_ReplayWorldScene(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[2]=32789;
        assert(CODOL_ReplayWorldScene(&stream,&ref) && ref==1);
        assert(stream.source_position==840 && stream.position[3]==212 && stream.position[2]==32789);
        assert(stream.data[3][92]==7 && stream.data[3][94]==9 && stream.data[3][211]==11);
        assert(stream.active==3 && stream.depth==1);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[882]={0},empty[628]={0};
        uint32_t capacities[8]={628,0,12,256,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        uint8_t *d=data+80;
        size_t n;
        put32(d,1); put32(d+16,1); put32(d+40,1); put32(d+52,3); put32(d+64,3);
        put32(d+4,1); put32(d+8,1); put32(d+12,1); put32(d+20,1);
        put32(d+24,1); put32(d+28,1); put32(d+44,1); put32(d+56,1); put32(d+68,1);
        put32(data+628,0x30000123); put32(data+644,0x30000123); put32(data+648,0x30000123);
        data[696]=7; data[704]=9;
        put32(data+152+20,2); data[152+12]=1; data[152+18]=2;
        put32(data+152+28,1); put32(data+152+32,1); put32(data+152+36,1);
        put32(data+152+40,1); put32(data+152+44,1); put32(data+152+48,1); put32(data+152+52,1);
        data[881]=11;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayWorldDraw(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],628) && !memcmp(empty,stream.data[3],256));
            assert(!memcmp(empty,stream.data[2],12));
        }
        stream.source_size=sizeof(data); put32(data+152+20,3); saved=stream;
        assert(!CODOL_ReplayWorldDraw(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        put32(data+152+20,2); data[152+18]=0;
        assert(!CODOL_ReplayWorldDraw(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        data[152+18]=2; stream.capacity[3]=255; saved=stream;
        assert(!CODOL_ReplayWorldDraw(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=256;
        assert(CODOL_ReplayWorldDraw(&stream,&ref) && ref==1);
        assert(stream.source_position==882 && stream.position[3]==256 && stream.position[2]==12);
        assert(stream.data[3][255]==11);
        assert(stream.data[3][68]==7 && stream.data[3][77]==9);
        assert(stream.active==3 && stream.depth==1);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[841]={0},empty[2048]={0};
        uint32_t capacities[8]={628,0,2048,317,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        put32(data+8,1); put32(data+12,1); put32(data+52,1);
        put32(data+56,UINT32_MAX); put32(data+60,1); put32(data+64,1);
        put32(data+68,1); put32(data+72,1); put32(data+76,1);
        put32(data+650,1); put32(data+654,1); /* One tree and one node. */
        data[658+34]=1; put32(data+658+36,UINT32_MAX); data[702]=7;
        put32(data+704+24,1); put32(data+704+28,1);
        data[704+32]=1; put32(data+704+36,1);
        put32(data+744+28,1); data[744+34]=3; data[840]=9;
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayWorldVisibility(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],628) && !memcmp(empty,stream.data[3],317));
            assert(!memcmp(empty,stream.data[2],2048));
        }
        stream.source_size=sizeof(data); stream.capacity[3]=316; saved=stream;
        assert(!CODOL_ReplayWorldVisibility(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=317;
        assert(CODOL_ReplayWorldVisibility(&stream,&ref) && ref==1);
        assert(stream.source_position==841 && stream.position[3]==317 && stream.position[2]==2048);
        assert(stream.data[3][176]==7 && stream.data[3][316]==9);
        assert(stream.active==3 && stream.depth==1 && stream.position[0]==628);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[284]={0},empty[192]={0},runtime[192]={9};
        uint32_t capacities[8]={116,0,192,100,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        uint8_t *g=data+76;
        size_t n;
        unsigned i;
        put32(data+56,20); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); data[188]='w';
        put32(g+8,1); put32(g+12,1); put32(g+16,2); put32(g+20,1);
        put32(g+24,3); put32(g+36,1); put32(g+44,1);
        for (i=48;i<=96;i+=4) put32(g+i,1);
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
        stream.source_position=72; memcpy(stream.data[2],runtime,sizeof(runtime));
        for (n=72;n<sizeof(data);++n) {
            put32(data+68,n-72); zone.size=n; stream.source_size=n; saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],116) && !memcmp(empty,stream.data[3],100));
            assert(!memcmp(runtime,stream.data[2],192));
        }
        put32(data+68,212); zone.size=sizeof(data); stream.source_size=sizeof(data);
        stream.capacity[2]=191; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        assert(!memcmp(runtime,stream.data[2],192));
        stream.capacity[2]=192;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==284 && stream.position[3]==100 && stream.position[2]==192);
        assert(!memcmp(empty,stream.data[2],192) && stream.position[0]==0 && stream.active==3 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[228]={0},empty[144]={0};
        uint32_t capacities[8]={16,0,0,144,0,0,0,0};
        codol_zone_t zone={data,sizeof(data),56,1,0,{0}};
        codol_load_blocks_t stream={0},saved;
        size_t n;
        put32(data+56,16); put32(data+60,32); put32(data+64,UINT32_MAX);
        put32(data+72,UINT32_MAX); put32(data+80,2); put32(data+84,1);
        data[88]='w'; put32(data+90+64,UINT32_MAX);
        put32(data+90+68+64,0x30000123); data[226]='l';
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
        stream.source_position=72;
        for (n=72;n<sizeof(data);++n) {
            put32(data+68,n-72); zone.size=n; stream.source_size=n; saved=stream;
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],16) && !memcmp(empty,stream.data[3],144));
        }
        put32(data+68,156); zone.size=sizeof(data); stream.source_size=sizeof(data);
        stream.capacity[3]=141; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=144;
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==228 && stream.position[3]==142 && stream.position[0]==0);
        assert(stream.active==3 && !stream.depth && stream.data[3][140]=='l');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[745]={0},empty[564]={0};
        uint32_t capacities[8]={148,0,0,564,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        unsigned i;
        put32(data,UINT32_MAX); put32(data+4,UINT32_MAX); put32(data+8,1);
        data[12]='a';
        for (i=0;i<5;++i) { put32(data+14+4*i,UINT32_MAX); data[122+2*i]='b'+i; }
        put32(data+14+20,UINT32_MAX); put32(data+14+88,UINT32_MAX-1);
        put32(data+14+104,UINT32_MAX);
        data[132]=1; put32(data+136,UINT32_MAX); /* Inline loaded SoundFile. */
        put32(data+144,UINT32_MAX); put32(data+144+12,3);
        put32(data+144+44,UINT32_MAX-1); data[192]='s';
        memcpy(data+194,"pcm",3);
        put32(data+197,UINT32_MAX); data[333]='c';
        put32(data+335+4,UINT32_MAX); data[743]='m';
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplaySoundAsset(&stream,11,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],148) && !memcmp(empty,stream.data[3],564));
        }
        stream.source_size=sizeof(data); stream.capacity[3]=561; saved=stream;
        assert(!CODOL_ReplaySoundAsset(&stream,11,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=564;
        assert(CODOL_ReplaySoundAsset(&stream,11,&ref) && ref==1);
        assert(stream.source_position==745 && stream.position[3]==562);
        assert(stream.position[0]==12 && stream.written[0]==148 && stream.active==0 && !stream.depth);
        assert(stream.data[3][136]=='s' && stream.data[3][148]=='c' && stream.data[3][560]=='m');
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[368]={0},empty[340]={0};
        uint32_t capacities[8]={32,0,0,340,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        put32(data+16,1); put32(data+28,1);
        data[32+176]=5; /* Trail, with a pooled material reference. */
        put32(data+32+188,0x30000123);
        put32(data+32+216,UINT32_MAX); memcpy(data+292,"fx",3);
        put32(data+32+244,1); /* Trail header follows FX name. */
        put32(data+295+20,1); put32(data+295+24,1);
        put32(data+295+28,3); put32(data+295+32,1);
        put32(data+32+256,UINT32_MAX); memcpy(data+357,"trail_name",11);
        assert(CODOL_InitLoadBlocks(&stream,data,368,capacities,0));
        for (n=0;n<368;++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayEffect(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],32) && !memcmp(empty,stream.data[3],340));
        }
        stream.source_size=368; stream.capacity[3]=335; saved=stream;
        assert(!CODOL_ReplayEffect(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=340;
        assert(CODOL_ReplayEffect(&stream,&ref) && ref==1);
        assert(stream.source_position==368 && stream.position[3]==337 && stream.active==0 && !stream.depth);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t data[174]={0},empty[88]={0};
        uint32_t capacities[8]={88,0,0,88,0,0,0,0},ref=123;
        codol_load_blocks_t stream={0},saved;
        size_t n;
        data[15]=1; put32(data+84,1); /* 256 frames: two-byte frame indices. */
        put32(data+88,1); put32(data+92,1); put32(data+96,1);
        data[100]=1; data[102]=1; put32(data+128,1); /* packed translation */
        data[136]=7; data[142]=1; put32(data+146,1); /* quaternion2 frames */
        data[154]=9; data[166]=11; /* quaternion4 constant */
        assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
        for (n=0;n<sizeof(data);++n) {
            stream.source_size=n; saved=stream;
            assert(!CODOL_ReplayAnimation(&stream,&ref) && ref==123);
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],88) && !memcmp(empty,stream.data[3],88));
        }
        stream.source_size=sizeof(data); stream.capacity[3]=87; saved=stream;
        assert(!CODOL_ReplayAnimation(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
        stream.capacity[3]=88;
        assert(CODOL_ReplayAnimation(&stream,&ref) && ref==1);
        assert(stream.source_position==174 && stream.position[3]==88 && stream.active==0 && !stream.depth);
        assert(stream.data[3][48]==7 && stream.data[3][68]==9 && stream.data[3][80]==11);
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        unsigned kind;
        for (kind=6;kind<=9;++kind) {
            uint8_t data[174]={0};
            unsigned type=kind==9 ? 27 : kind;
            size_t header=type==27 ? 8 : type==8 ? 100 : 16;
            size_t extent=header+(type==27 ? 4 : type==8 ? 2 : 10);
            codol_zone_t zone={0};
            codol_load_blocks_t stream={0},saved;
            put32(data,72+extent-40); put32(data+8,100); put32(data+20,64);
            put32(data+48,1); put32(data+52,UINT32_MAX);
            put32(data+56,type); put32(data+60,32); put32(data+64,UINT32_MAX); put32(data+68,extent);
            put32(data+72,UINT32_MAX); data[72+header]='v';
            if (type==27) { put32(data+76,UINT32_MAX); data[82]='k'; }
            else if (type!=8) { put32(data+80,1); data[84]=2; memset(data+90,0x7f,8); }
            assert(CODOL_OpenZoneImage(&zone,data,72+extent) && CODOL_BeginZoneReplay(&zone,&stream));
            if (type==27) {
                saved=stream; zone.data[83]='x';
                assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1);
                assert(!memcmp(&saved,&stream,sizeof(stream))); zone.data[83]=0;
            }
            assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1 && stream.source_position==72+extent);
            assert(stream.position[0]==0 && stream.written[0]==header && stream.data[3][16]=='v');
            if (type==27) assert(stream.data[3][18]=='k' && stream.position[3]==20);
            if (type==6 || type==7) assert(stream.data[3][20]==0x7f && stream.position[3]==28);
            CODOL_FreeLoadBlocks(&stream); CODOL_CloseZone(&zone);
        }
    }
    {
        uint8_t data[137]={0},before[50];
        codol_zone_t zone={0};
        codol_load_blocks_t stream={0},saved;
        put32(data,97); put32(data+8,32); put32(data+20,64);
        put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+56,36); put32(data+60,48); put32(data+64,UINT32_MAX); put32(data+68,21);
        put32(data+72,37); put32(data+76,69); put32(data+80,UINT32_MAX); put32(data+84,28);
        put32(data+88,UINT32_MAX); put32(data+92,3); put32(data+96,100); put32(data+100,1);
        data[104]='a'; memcpy(data+106,"xyz",3); /* Compressed bytes require no trailing NUL. */
        put32(data+109,UINT32_MAX); put32(data+113,1); put32(data+117,1); put32(data+121,1);
        data[125]='t'; put32(data+127,UINT32_MAX); put32(data+131,'a'); data[135]='a';
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_BeginZoneReplay(&zone,&stream));
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1 && stream.source_position==109);
        assert(stream.position[3]==37 && !memcmp(stream.data[3]+34,"xyz",3));
        memcpy(before,stream.data[3],50); saved=stream;
        put32(zone.data+113,UINT32_MAX);
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(before,stream.data[3],50));
        put32(zone.data+113,1); stream.capacity[3]=49; saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==-1);
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(before,stream.data[3],50));
        stream.capacity[3]=4096;
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==1 && stream.source_position==137);
        assert(stream.position[3]==50 && stream.data[3][37]=='t' && stream.data[3][48]=='a');
        CODOL_FreeLoadBlocks(&stream); CODOL_CloseZone(&zone);
    }
    {
        uint8_t data[810]={0};
        codol_zone_t zone={0};
        codol_load_blocks_t stream={0},saved;
        codol_model_block_t views[8];
        codol_asset_t asset;
        codol_xmodel_skeleton_t source={0},resolved={0};
        put32(data,770); put32(data+8,360); put32(data+20,64);
        put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+56,4); put32(data+60,48); put32(data+64,UINT32_MAX); put32(data+68,362);
        put32(data+72,4); put32(data+76,410); put32(data+80,UINT32_MAX); put32(data+84,360);
        put32(data+88,UINT32_MAX); data[448]='a'; put32(data+450,0x30000021);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)));
        assert(CODOL_BeginZoneReplay(&zone,&stream));
        assert(stream.source_position==88 && stream.position[3]==32 && stream.depth==1);
        assert(stream.capacity[0]==4096 && stream.capacity[3]==4096);
        saved=stream;
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(zone.data+56,23); /* Known no-op family cannot skip a payload. */
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==-1 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(zone.data+56,44); /* Unknown family has no replay binding. */
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==0 && !memcmp(&saved,&stream,sizeof(stream)));
        put32(zone.data+56,4);
        assert(CODOL_ReplayZoneAsset(&zone,0,&stream)==1);
        assert(stream.source_position==450 && stream.position[0]==0 && stream.position[3]==34);
        assert(CODOL_ReplayZoneAsset(&zone,1,&stream)==1 && stream.source_position==810);
        assert(CODOL_ZoneAsset(&zone,1,&asset) && CODOL_ReadXModelSkeleton(&asset,&source));
        CODOL_LoadBlockViews(&stream,views);
        assert(CODOL_RelocateXModelSkeleton(&source,views,&resolved) && !strcmp(resolved.name,"a"));
        CODOL_FreeXModelSkeleton(&source); CODOL_FreeLoadBlocks(&stream); CODOL_CloseZone(&zone);
        assert(!strcmp(resolved.name,"a")); CODOL_FreeXModelSkeleton(&resolved);
    }
    {
        uint8_t input[813]={0},before[96],empty_header[360]={0};
        const uint32_t refs[6]={0x30000003,0x30000007,0x30000009,0x30000011,0x3000001d,0x30000021};
        uint32_t capacities[8]={360,0,0,96,0,0,0,0};
        codol_load_blocks_t stream={0},saved;
        codol_model_block_t views[8];
        codol_xmodel_skeleton_t first={0},second={0},resolved={0};
        unsigned i;
        input[4]=2; input[5]=1; put32(input,UINT32_MAX);
        for (i=0;i<6;++i) put32(input+44+4*i,UINT32_MAX);
        input[360]='m'; input[364]=1; input[366]=1;
        input[373]=255; input[374]=127; /* quaternion fourth component */
        input[453+4]=2; input[453+5]=1; put32(input+453,0x30000001);
        for (i=0;i<6;++i) put32(input+453+44+4*i,refs[i]);
        assert(CODOL_InitLoadBlocks(&stream,input,sizeof(input),capacities,3));
        assert(CODOL_PushLoadBlock(&stream,0)); saved=stream;
        stream.capacity[3]=95; saved=stream; memset(before,0,sizeof(before));
        assert(!CODOL_ReplayXModelSkeleton(&stream,&first));
        assert(!memcmp(&saved,&stream,sizeof(stream)) && !memcmp(before,stream.data[3],96));
        assert(!first.storage && !memcmp(empty_header,stream.data[0],360));
        stream.capacity[3]=96;
        assert(CODOL_ReplayXModelSkeleton(&stream,&first));
        assert(stream.active==3 && stream.source_position==453 && stream.position[3]==96);
        assert(first.name_reference==0x30000001);
        for (i=0;i<6;++i) assert(first.arrays[i].reference==refs[i]);
        CODOL_FreeXModelSkeleton(&first);
        assert(CODOL_PopLoadBlock(&stream) && CODOL_PopLoadBlock(&stream));
        assert(stream.position[0]==0 && CODOL_PushLoadBlock(&stream,0));
        assert(CODOL_ReplayXModelSkeleton(&stream,&second));
        assert(second.unresolved==7 && stream.source_position==813 && stream.position[3]==96);
        CODOL_LoadBlockViews(&stream,views);
        assert(CODOL_RelocateXModelSkeleton(&second,views,&resolved));
        CODOL_FreeXModelSkeleton(&second); CODOL_FreeLoadBlocks(&stream);
        assert(!resolved.unresolved && !strcmp(resolved.name,"m"));
        assert(resolved.arrays[0].data[2]==1 && resolved.arrays[1].data[0]==1);
        assert(resolved.arrays[2].data[6]==255 && resolved.arrays[2].data[7]==127);
        CODOL_FreeXModelSkeleton(&resolved);
    }
    {
        uint8_t input[16]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16};
        uint32_t capacities[8]={16,0,16,32,0,0,0,0},ref=99;
        codol_load_blocks_t stream={0},saved;
        codol_model_block_t views[8];
        unsigned i;
        assert(CODOL_InitLoadBlocks(&stream,input,sizeof(input),capacities,3));
        assert(CODOL_ReadLoadBlock(&stream,3,1,&ref) && ref==0x30000001);
        assert(CODOL_ReadLoadBlock(&stream,2,4,&ref) && ref==0x30000005);
        assert(stream.source_position==5 && stream.position[3]==6);
        assert(stream.data[3][3]==0 && stream.data[3][4]==4);
        assert(CODOL_InsertLoadPointer(&stream,&ref) && ref==0x30000009);
        assert(stream.source_position==5 && stream.position[3]==12);
        assert(CODOL_PushLoadBlock(&stream,0));
        assert(CODOL_ReadLoadBlock(&stream,2,1,&ref) && ref==1);
        assert(CODOL_PushLoadBlock(&stream,0));
        assert(CODOL_ReadLoadBlock(&stream,2,1,&ref) && ref==3);
        assert(CODOL_PopLoadBlock(&stream) && stream.position[0]==2);
        assert(CODOL_PushLoadBlock(&stream,2));
        assert(CODOL_ReadLoadBlock(&stream,16,1,&ref) && ref==0x20000001);
        assert(stream.source_position==9 && stream.data[2][0]==0);
        assert(CODOL_PopLoadBlock(&stream) && stream.active==0);
        assert(CODOL_PopLoadBlock(&stream) && stream.active==3 && stream.position[0]==0);
        CODOL_LoadBlockViews(&stream,views);
        assert(views[0].size==4 && views[3].size==12 && views[2].size==16);
        saved=stream; ref=99;
        assert(!CODOL_ReadLoadBlock(&stream,8,4,&ref)); /* Input exhausted first. */
        assert(ref==99 && !memcmp(&saved,&stream,sizeof(stream)));
        assert(!CODOL_ReadLoadBlock(&stream,1,3,&ref));
        assert(!CODOL_PopLoadBlock(&stream));
        assert(!CODOL_PushLoadBlock(&stream,8));
        assert(!memcmp(&saved,&stream,sizeof(stream)));
        for (i=0;i<CODOL_LOAD_STACK;++i) assert(CODOL_PushLoadBlock(&stream,3));
        assert(!CODOL_PushLoadBlock(&stream,3));
        for (i=0;i<CODOL_LOAD_STACK;++i) assert(CODOL_PopLoadBlock(&stream));
        assert(CODOL_PushLoadBlock(&stream,2)); saved=stream;
        assert(!CODOL_ReadLoadBlock(&stream,1,1,&ref)); /* Block exhausted. */
        assert(!memcmp(&saved,&stream,sizeof(stream)));
        CODOL_FreeLoadBlocks(&stream);
    }
    {
        uint8_t header[360]={0},block[91]={0};
        char name[]="test";
        const unsigned offsets[6]={0,4,5,13,25,27};
        codol_asset_t asset={4,header,sizeof(header)};
        codol_xmodel_skeleton_t source={0},result={0},saved;
        codol_model_block_t blocks[8]={{0}};
        unsigned i;
        header[4]=2; header[5]=1; put32(header,0x30000001);
        for (i=0;i<6;++i) put32(header+44+4*i,offsets[i]+1);
        block[2]=1; block[4]=1; block[11]=255; block[12]=127;
        blocks[0]=(codol_model_block_t){block,sizeof(block)};
        blocks[3]=(codol_model_block_t){(uint8_t *)name,sizeof(name)};
        assert(CODOL_ReadXModelSkeleton(&asset,&source) && source.unresolved==7);
        assert(CODOL_RelocateXModelSkeleton(&source,blocks,&result));
        assert(!result.unresolved && !strcmp(result.name,"test") && result.consumed==360);
        for (i=0;i<6;++i) {
            assert(result.arrays[i].reference==offsets[i]+1);
            assert(!memcmp(result.arrays[i].data,block+offsets[i],result.arrays[i].count*result.arrays[i].stride));
        }
        saved=result;
        for (i=0;i<sizeof(block);++i) {
            blocks[0].size=i;
            assert(!CODOL_RelocateXModelSkeleton(&source,blocks,&result));
            assert(!memcmp(&saved,&result,sizeof(result)));
        }
        blocks[0].size=sizeof(block); blocks[3].size=4;
        assert(!CODOL_RelocateXModelSkeleton(&source,blocks,&result));
        blocks[3].size=sizeof(name); source.arrays[0].reference=0x80000001;
        assert(!CODOL_RelocateXModelSkeleton(&source,blocks,&result));
        source.arrays[0].reference=1; block[4]=0;
        assert(!CODOL_RelocateXModelSkeleton(&source,blocks,&result));
        block[4]=1; put32(block+13,0x7fc00000);
        assert(!CODOL_RelocateXModelSkeleton(&source,blocks,&result));
        assert(!memcmp(&saved,&result,sizeof(result)));
        memset(block,0,sizeof(block)); name[0]='X'; CODOL_FreeXModelSkeleton(&source);
        assert(!strcmp(result.name,"test") && result.arrays[1].data[0]==1);
        assert(result.arrays[2].data[6]==255 && result.arrays[2].data[7]==127);
        CODOL_FreeXModelSkeleton(&result);
    }
    {
        uint8_t indices[6]={1,0,0,0,2,0};
        char text[]="tag_origin";
        codol_script_string_t pool[3]={{0,NULL},{UINT32_MAX,text},{0x30000123,NULL}};
        codol_xmodel_skeleton_t model={0};
        codol_xmodel_bone_names_t result={0},saved;
        model.bones=3; model.arrays[0]=(codol_model_array_t){UINT32_MAX,3,2,indices};
        assert(CODOL_ResolveXModelBoneNames(&model,pool,3,&result));
        assert(result.count==3 && result.unresolved==2);
        assert(!strcmp(result.names[0].text,"tag_origin") && result.names[0].index==1);
        assert(!result.names[1].text && !result.names[1].reference);
        assert(!result.names[2].text && result.names[2].reference==0x30000123);
        text[0]='X'; assert(!strcmp(result.names[0].text,"tag_origin"));
        saved=result; indices[0]=3;
        assert(!CODOL_ResolveXModelBoneNames(&model,pool,3,&result));
        assert(!memcmp(&saved,&result,sizeof(result)));
        indices[0]=1; model.arrays[0].data=NULL;
        assert(!CODOL_ResolveXModelBoneNames(&model,pool,3,&result));
        assert(!memcmp(&saved,&result,sizeof(result)));
        CODOL_FreeXModelBoneNames(&result);
    }
    {
        uint8_t preset[72]={0},map[263]={0},model[695]={0};
        codol_asset_t asset={4,model,sizeof(model)};
        size_t p=0,n;
        put32(preset,UINT32_MAX); put32(preset+28,UINT32_MAX);
        preset[68]='p'; preset[70]='s';
        assert(CODOL_AdvancePhysicsPresetStream(preset,sizeof(preset),&p) && p==72);
        for (n=0;n<sizeof(preset);++n) {
            p=0; assert(!CODOL_AdvancePhysicsPresetStream(preset,n,&p) && !p);
        }
        put32(map,UINT32_MAX); map[72]='m';
        put32(map+4,1); put32(map+8,1); put32(map+74,1);
        /* One brush, one side with an inline plane, five edge bytes,
         * and an inline plane array. Non-sentinel pointers load arrays. */
        map[142+24]=1; put32(map+142+28,1); put32(map+142+32,1);
        put32(map+142+60,5); put32(map+142+64,UINT32_MAX);
        put32(map+210,UINT32_MAX);
        p=0; assert(CODOL_AdvancePhysicsMapStream(map,sizeof(map),&p) && p==263);
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={72,0,0,196,0,0,0,0},ref=77;
            uint8_t empty[196]={0};
            assert(CODOL_InitLoadBlocks(&stream,map,sizeof(map),capacities,0));
            for (n=0;n<sizeof(map);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayPhysicsAsset(&stream,1,&ref) && ref==77);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],72) && !memcmp(empty,stream.data[3],196));
            }
            stream.source_size=sizeof(map); stream.capacity[3]=195; saved=stream;
            assert(!CODOL_ReplayPhysicsAsset(&stream,1,&ref));
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            stream.capacity[3]=196;
            assert(CODOL_ReplayPhysicsAsset(&stream,1,&ref) && ref==1);
            assert(stream.source_position==263 && stream.position[0]==72 && stream.position[3]==196);
            assert(stream.active==0 && !stream.depth && stream.data[3][0]=='m');
            assert(!memcmp(stream.data[3]+4,map+74,68));
            assert(!memcmp(stream.data[3]+72,map+142,68));
            CODOL_FreeLoadBlocks(&stream);
            assert(CODOL_InitLoadBlocks(&stream,preset,sizeof(preset),capacities,0));
            assert(CODOL_ReplayPhysicsAsset(&stream,0,&ref));
            assert(stream.source_position==72 && stream.position[0]==68 && stream.position[3]==4);
            assert(!memcmp(stream.data[3],"p\0s",4));
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(map);++n) {
            p=0; assert(!CODOL_AdvancePhysicsMapStream(map,n,&p) && !p);
        }
        put32(map+4,UINT32_MAX); p=0;
        assert(!CODOL_AdvancePhysicsMapStream(map,sizeof(map),&p) && !p);
        put32(map+4,1); put32(map+202,UINT32_MAX); p=0;
        assert(!CODOL_AdvancePhysicsMapStream(map,sizeof(map),&p) && !p);
        put32(map+202,5);
        put32(model+0x160,UINT32_MAX-1); put32(model+0x164,UINT32_MAX);
        memcpy(model+360,preset,sizeof(preset)); memcpy(model+432,map,sizeof(map));
        p=0; assert(CODOL_ReadXModelExtent(&asset,&p) && p==sizeof(model));
        {
            codol_asset_t views[2]={{0}},saved[2];
            assert(CODOL_XModelInlinePhysicsAssets(&asset,views));
            assert(views[0].type==0 && views[0].data==model+360 && views[0].size==72);
            assert(views[1].type==1 && views[1].data==model+432 && views[1].size==263);
            memcpy(saved,views,sizeof(views));
            for (n=0;n<sizeof(model);++n) {
                asset.size=n; assert(!CODOL_XModelInlinePhysicsAssets(&asset,views));
                assert(!memcmp(saved,views,sizeof(views)));
            }
            asset.size=sizeof(model);
        }
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={432,0,0,204,0,0,0,0},ref=123;
            uint8_t empty[432]={0};
            assert(CODOL_InitLoadBlocks(&stream,model,sizeof(model),capacities,0));
            for (n=0;n<sizeof(model);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayXModel(&stream,&ref) && ref==123);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],432) && !memcmp(empty,stream.data[3],204));
            }
            stream.source_size=sizeof(model); stream.capacity[3]=203; saved=stream;
            assert(!CODOL_ReplayXModel(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
            assert(!memcmp(empty,stream.data[0],432) && !memcmp(empty,stream.data[3],204));
            stream.capacity[3]=204;
            assert(CODOL_ReplayXModel(&stream,&ref) && ref==1);
            assert(stream.source_position==695 && stream.position[3]==204 && stream.position[0]==360);
            assert(!stream.depth && stream.active==0 && stream.written[0]==432);
            assert(stream.data[3][4]=='p' && stream.data[3][8]=='m');
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(model);++n) {
            asset.size=n; p=123;
            assert(!CODOL_ReadXModelExtent(&asset,&p) && p==123);
        }
    }
    {
        uint8_t data[388]={0};
        codol_asset_t asset={4,data,sizeof(data)};
        codol_xmodel_bounds_t result={0}, saved;
        size_t n;
        data[4]=data[5]=1;
        put32(data+0x138,1); /* Non-sentinel nonzero also means inline. */
        put32(data+0x13c,0x40800000); /* radius 4 */
        put32(data+0x140,0x40000000); put32(data+0x14c,0x3f800000);
        put32(data+360,0x40000000); put32(data+372,0x3f800000);
        put32(data+384,0x3f800000);
        put32(data+0x160,0x30000123); put32(data+0x164,UINT32_MAX);
        assert(CODOL_ReadXModelBounds(&asset,&result));
        assert(result.consumed==388 && result.bone_count==1 && result.bones);
        assert(result.mins[0]==1 && result.maxs[0]==3 && result.radius==4);
        assert(result.bones[0].bounds[0][0]==1 && result.bones[0].bounds[1][0]==3);
        assert(result.bones[0].offset[0]==2 && result.bones[0].radiusSquared==1);
        assert(result.physics_preset_reference==0x30000123 && result.physics_map_reference==UINT32_MAX);
        saved=result;
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadXModelBounds(&asset,&result));
            assert(!memcmp(&result,&saved,sizeof(result)));
        }
        asset.size=sizeof(data);
        put32(data+372,0xbf800000); /* negative half size */
        assert(!CODOL_ReadXModelBounds(&asset,&result));
        put32(data+372,0x3f800000); put32(data+384,0x7fc00000);
        assert(!CODOL_ReadXModelBounds(&asset,&result));
        put32(data+384,0x3f800000); put32(data+0x13c,0xbf800000);
        assert(!CODOL_ReadXModelBounds(&asset,&result));
        assert(!memcmp(&result,&saved,sizeof(result)));
        CODOL_FreeXModelBounds(&result);
        put32(data+0x13c,0); put32(data+0x138,0); asset.size=360;
        assert(CODOL_ReadXModelBounds(&asset,&result) && !result.bones && result.consumed==360);
        CODOL_FreeXModelBounds(&result);
    }
    {
        uint8_t data[410]={0};
        size_t p=0,n;
        put32(data,UINT32_MAX); put32(data+12,UINT32_MAX); data[204]='s';
        put32(data+206,UINT32_MAX); data[212]=1;
        put32(data+214,UINT32_MAX-1); put32(data+218,UINT32_MAX); put32(data+222,UINT32_MAX);
        data[226]=1; put32(data+230,UINT32_MAX);
        put32(data+234,UINT32_MAX); data[334]='d';
        put32(data+336,UINT32_MAX); put32(data+344,1); data[348]=2; data[352]='v';
        put32(data+362,UINT32_MAX); put32(data+370,1); data[374]=1; data[378]='p';
        data[384]=1; put32(data+388,UINT32_MAX); data[408]='t';
        assert(CODOL_AdvanceTechniqueSetStream(data,sizeof(data),&p) && p==sizeof(data));
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={304,0,0,82,0,0,0,0},ref=123;
            uint8_t empty[304]={0};
            assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
            for (n=0;n<sizeof(data);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayTechniqueSet(&stream,&ref) && ref==123);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],304) && !memcmp(empty,stream.data[3],82));
            }
            stream.source_size=sizeof(data); stream.capacity[3]=81; saved=stream;
            assert(!CODOL_ReplayTechniqueSet(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
            stream.capacity[3]=82;
            assert(CODOL_ReplayTechniqueSet(&stream,&ref) && ref==1);
            assert(stream.source_position==410 && stream.position[3]==82 && stream.position[0]==204);
            assert(!stream.depth && stream.active==0 && stream.written[0]==304);
            assert(stream.data[3][36]=='d' && stream.data[3][38]=='v' && stream.data[3][48]=='p');
            assert(stream.data[3][80]=='t');
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(data);++n) {
            p=0; assert(!CODOL_AdvanceTechniqueSetStream(data,n,&p) && !p);
        }
        data[212]=255; data[213]=255; p=0;
        assert(!CODOL_AdvanceTechniqueSetStream(data,sizeof(data),&p) && !p);
        data[212]=1; data[213]=0; data[348]=255; data[349]=255;
        assert(!CODOL_AdvanceTechniqueSetStream(data,sizeof(data),&p) && !p);
    }
    {
        uint8_t data[149]={0};
        size_t p=0,n;
        put32(data+4,1); put32(data+8,1); put32(data+12,1); put32(data+16,2);
        put32(data+64,UINT32_MAX-1);
        put32(data+92,UINT32_MAX); put32(data+124,UINT32_MAX);
        data[128]='w'; put32(data+142,3);
        assert(CODOL_AdvanceWaterStream(data,sizeof(data),&p) && p==sizeof(data));
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={40,0,0,119,0,0,0,0},ref=123;
            uint8_t empty[119]={0};
            assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,3));
            stream.position[0]=4;
            for (n=0;n<sizeof(data);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayWater(&stream,&ref) && ref==123);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],40) && !memcmp(empty,stream.data[3],119));
            }
            stream.source_size=sizeof(data); stream.capacity[3]=118; saved=stream;
            assert(!CODOL_ReplayWater(&stream,&ref) && !memcmp(&saved,&stream,sizeof(stream)));
            stream.capacity[3]=119;
            assert(CODOL_ReplayWater(&stream,&ref) && ref==0x30000001);
            assert(stream.source_position==149 && stream.position[3]==119);
            assert(stream.position[0]==4 && stream.written[0]==40 && stream.active==3 && !stream.depth);
            assert(!memcmp(stream.data[0]+4,data+92,36));
            assert(stream.data[3][96]=='w' && !memcmp(stream.data[3]+100,data+130,19));
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(data);++n) {
            p=0; assert(!CODOL_AdvanceWaterStream(data,n,&p) && !p);
        }
        put32(data+12,65536); put32(data+16,65536); p=0;
        assert(!CODOL_AdvanceWaterStream(data,sizeof(data),&p) && !p);
        put32(data+12,UINT32_MAX); put32(data+16,0);
        assert(!CODOL_AdvanceWaterStream(data,sizeof(data),&p) && !p);
    }
    {
        uint8_t data[244]={0};
        size_t p=0,n;
        put32(data,UINT32_MAX); put32(data+4,UINT32_MAX); data[8]=1; data[48]='s';
        data[54]=1; data[56]=1; /* vertex and triangle counts */
        put32(data+66,UINT32_MAX); data[70]=1; put32(data+78,UINT32_MAX);
        put32(data+82,UINT32_MAX); put32(data+90,1); put32(data+94,UINT32_MAX);
        put32(data+176,UINT32_MAX); /* rigid-list collision tree */
        put32(data+204,1); put32(data+208,1); put32(data+212,1); put32(data+216,1);
        assert(CODOL_AdvanceModelSurfacesStream(data,sizeof(data),&p) && p==sizeof(data));
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={48,0,0,162,0,0,48,22},ref=123;
            uint8_t empty[162]={0};
            assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
            stream.position[6]=stream.position[7]=1;
            for (n=0;n<sizeof(data);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayModelSurfaces(&stream,&ref) && ref==123);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],48) && !memcmp(empty,stream.data[3],162));
                assert(!memcmp(empty,stream.data[6],48) && !memcmp(empty,stream.data[7],22));
            }
            stream.source_size=sizeof(data); stream.capacity[7]=21; saved=stream;
            assert(!CODOL_ReplayModelSurfaces(&stream,&ref));
            assert(!memcmp(&saved,&stream,sizeof(stream)));
            stream.capacity[7]=22;
            assert(CODOL_ReplayModelSurfaces(&stream,&ref) && ref==1);
            assert(stream.source_position==244 && stream.position[3]==162);
            assert(stream.position[6]==48 && stream.position[7]==22 && stream.active==0 && !stream.depth);
            assert(!memcmp(stream.data[3]+4,data+50,84));
            assert(!memcmp(stream.data[3]+104,data+180,40));
            assert(!memcmp(stream.data[6]+16,data+136,32));
            assert(!memcmp(stream.data[7]+16,data+238,6));
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(data);++n) {
            p=0; assert(!CODOL_AdvanceModelSurfacesStream(data,n,&p) && !p);
        }
        put32(data+204,UINT32_MAX); p=0;
        assert(!CODOL_AdvanceModelSurfacesStream(data,sizeof(data),&p) && !p);
        put32(data+204,1); data[71]=0x80; /* negative signed blend count */
        assert(!CODOL_AdvanceModelSurfacesStream(data,sizeof(data),&p) && !p);
    }
    {
        uint8_t data[207]={0};
        size_t p=0,n;
        put32(data,UINT32_MAX); data[96]='m';
        data[0x48]=1; data[0x49]=1; data[0x4a]=1;
        put32(data+0x54,UINT32_MAX); put32(data+0x58,UINT32_MAX); put32(data+0x5c,UINT32_MAX);
        put32(data+106,UINT32_MAX-1); /* inline image in texture */
        put32(data+110,UINT32_MAX); put32(data+142,UINT32_MAX);
        data[146]='i'; put32(data+160,3); /* image loaddef payload */
        assert(CODOL_AdvanceMaterialStream(data,sizeof(data),&p) && p==sizeof(data));
        {
            codol_load_blocks_t stream={0},saved;
            uint32_t capacities[8]={132,0,0,88,0,0,0,0},ref=123;
            uint8_t empty[132]={0};
            assert(CODOL_InitLoadBlocks(&stream,data,sizeof(data),capacities,0));
            for (n=0;n<sizeof(data);++n) {
                stream.source_size=n; saved=stream;
                assert(!CODOL_ReplayMaterial(&stream,&ref) && ref==123);
                assert(!memcmp(&saved,&stream,sizeof(stream)));
                assert(!memcmp(empty,stream.data[0],132) && !memcmp(empty,stream.data[3],88));
            }
            stream.source_size=sizeof(data);
            assert(CODOL_ReplayMaterial(&stream,&ref) && ref==1);
            assert(stream.source_position==207 && stream.position[3]==88 && stream.position[0]==96);
            assert(!stream.depth && stream.active==0 && stream.written[0]==132);
            assert(stream.data[3][20]=='i' && !memcmp(stream.data[3]+48,data+167,32));
            CODOL_FreeLoadBlocks(&stream);
        }
        for (n=0;n<sizeof(data);++n) {
            p=0; assert(!CODOL_AdvanceMaterialStream(data,n,&p) && !p);
        }
        put32(data+160,UINT32_MAX); p=0;
        assert(!CODOL_AdvanceMaterialStream(data,sizeof(data),&p) && !p);
        put32(data+160,3); put32(data+0x50,UINT32_MAX-1);
        assert(!CODOL_AdvanceMaterialStream(data,sizeof(data),&p) && !p);
        put32(data+0x50,0); data[105]=11; put32(data+106,UINT32_MAX);
        assert(!CODOL_AdvanceMaterialStream(data,sizeof(data),&p) && !p);
    }
    {
        uint8_t data[452]={0};
        codol_asset_t asset={4,data,sizeof(data)};
        codol_xmodel_collision_t collision={0},saved;
        size_t n;
        put32(data,123); data[4]=1; data[5]=1;
        put32(data+0x12c,UINT32_MAX); put32(data+0x130,1);
        put32(data+360,UINT32_MAX); put32(data+364,1);
        put32(data+368,0x41200000); put32(data+380,0x40000000); put32(data+404,0x3f800000);
        assert(CODOL_ReadXModelCollision(&asset,&collision));
        assert(collision.count==1 && collision.consumed==sizeof(data));
        assert(collision.surfaces[0].mins[0]==8 && collision.surfaces[0].maxs[0]==12);
        assert(collision.surfaces[0].triangle_count==1 && collision.surfaces[0].triangles[0][0]==1);
        saved=collision;
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadXModelCollision(&asset,&collision));
            assert(!memcmp(&saved,&collision,sizeof(collision)));
        }
        asset.size=sizeof(data); put32(data+404,0x7fc00000);
        assert(!CODOL_ReadXModelCollision(&asset,&collision));
        assert(collision.surfaces[0].triangles[0][0]==1);
        put32(data+404,0); put32(data+392,1);
        assert(!CODOL_ReadXModelCollision(&asset,&collision));
        assert(!memcmp(&saved,&collision,sizeof(collision)));
        CODOL_FreeXModelCollision(&collision);
    }
    {
        uint8_t data[453]={0};
        codol_asset_t asset={4,data,sizeof(data)};
        codol_xmodel_skeleton_t model={0},saved;
        size_t i;
        put32(data,UINT32_MAX); data[4]=2; data[5]=1;
        for (i=0;i<6;++i) put32(data+0x2c+4*i,UINT32_MAX);
        data[360]='x'; data[366]=1; data[367]=0x12; data[373]=0x34;
        assert(CODOL_ReadXModelSkeleton(&asset,&model));
        assert(model.consumed==sizeof(data) && model.arrays[CODOL_MODEL_QUATS].stride==8);
        assert(model.arrays[CODOL_MODEL_QUATS].data[6]==0x34 && !strcmp(model.name,"x"));
        saved=model;
        for (i=0;i<sizeof(data);++i) {
            asset.size=i;
            assert(!CODOL_ReadXModelSkeleton(&asset,&model));
            assert(!memcmp(&saved,&model,sizeof(model)));
        }
        asset.size=sizeof(data); data[366]=0;
        assert(!CODOL_ReadXModelSkeleton(&asset,&model));
        data[366]=1; put32(data+375,0x7fc00000);
        assert(!CODOL_ReadXModelSkeleton(&asset,&model));
        assert(!memcmp(&saved,&model,sizeof(model)));
        CODOL_FreeXModelSkeleton(&model);
        put32(data+375,0); data[5]=3;
        assert(!CODOL_ReadXModelSkeleton(&asset,&model));
    }
    {
        uint8_t data[380]={0};
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_static_models_t models={0},saved;
        int model_handle=17;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+4*4,1); put32(data+5*4,UINT32_MAX);
        put32(data+256,0x30000123); put32(data+260,0x3f800000);
        put32(data+272,0x3f800000); put32(data+288,0x3f800000); put32(data+304,0x3f800000);
        put32(data+308,0x41200000); put32(data+320,0x40000000);
        put32(data+332,123); put32(data+336,UINT32_MAX); put32(data+340,4); memcpy(data+376,"{}\n",4);
        assert(CODOL_ReadCollisionStaticModels(&asset,NULL,NULL,&models));
        assert(models.count==1 && models.unresolved==1 && models.model_references[0]==0x30000123);
        assert(models.models[0].absmin[0]==8 && models.models[0].absmax[0]==12);
        CODOL_FreeCollisionStaticModels(&models);
        assert(CODOL_ReadCollisionStaticModels(&asset,collision_model,&model_handle,&models));
        assert(!models.unresolved && models.models[0].xmodel==&model_handle);
        saved=models; put32(data+272,0x7fc00000);
        assert(!CODOL_ReadCollisionStaticModels(&asset,collision_model,&model_handle,&models));
        assert(!memcmp(&models,&saved,sizeof(models)) && models.models[0].invScaledAxis[0][0]==1);
        CODOL_FreeCollisionStaticModels(&models); assert(model_handle==17);
    }
    {
        uint8_t data[1028]={0};
        codol_zone_t zone={0};
        codol_collision_map_t map={0},saved;
        char path[]="/tmp/codol-map-XXXXXX";
        int fd;
        FILE *file;
        put32(data,sizeof(data)-40); put32(data+48,2); put32(data+52,UINT32_MAX);
        put32(data+56,15); put32(data+60,48); put32(data+64,UINT32_MAX); put32(data+68,304);
        put32(data+72,21); put32(data+76,352); put32(data+80,UINT32_MAX); put32(data+84,636);
        put32(data+88,123); put32(data+88+39*4,UINT32_MAX);
        put32(data+344,123); put32(data+348,UINT32_MAX); put32(data+352,4); memcpy(data+388,"{}\n",4);
        put32(data+392,123); put32(data+396,UINT32_MAX); put32(data+392+0x38,UINT32_MAX);
        memcpy(data+1020,"mp_test",8);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)));
        assert(CODOL_LoadZoneCollision(&zone,"mp_test",NULL,NULL,&map)==1);
        saved=map;
        assert(CODOL_LoadZoneCollision(&zone,"missing",NULL,NULL,&map)==0);
        assert(!memcmp(&saved,&map,sizeof(map)));
        put32(zone.data+352,0); /* malformed final map component */
        assert(CODOL_LoadZoneCollision(&zone,"mp_test",NULL,NULL,&map)==-1);
        assert(!memcmp(&saved,&map,sizeof(map)));
        CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountArchive(path,NULL)); assert(!unlink(path));
        assert(CODOL_LoadMountedCollision("mp_test",&map)==1);
        {
            char patch[]="/tmp/codol-map-patch-XXXXXX";
            saved=map; put32(data+352,0);
            fd=mkstemp(patch); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
            assert(CODOL_MountArchive(patch,NULL)); assert(!unlink(patch));
            assert(CODOL_LoadMountedCollision("mp_test",&map)==-1);
            assert(!memcmp(&saved,&map,sizeof(map))); /* matching patch blocks fallback */
        }
        CODOL_UnmountArchives(); assert(!strcmp(map.entities.text,"{}\n"));
        CODOL_FreeCollisionMap(&map);
        {
            uint8_t pooled[1058]={0};
            char runtime[]="/tmp/codol-map-strings-XXXXXX";
            const char *paths[]={runtime}; size_t failed=0; unsigned failed_asset=0;
            put32(data+352,4);
            memcpy(pooled,data,344); memcpy(pooled+374,data+344,sizeof(data)-344);
            put32(pooled,sizeof(pooled)-40);
            put32(pooled+8,4096); put32(pooled+20,4096);
            put32(pooled+68,334); put32(pooled+76,382);
            put32(pooled+88+24,2); put32(pooled+88+28,UINT32_MAX);
            put32(pooled+344,UINT32_MAX); put32(pooled+348,7);
            /* 32 directory bytes + two 12-byte materials precede this string
             * in block 3. Its reference is not an offset in the zone file. */
            put32(pooled+356,0x30000039); memcpy(pooled+368,"stone",6);
            fd=mkstemp(runtime); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
            assert(fwrite(pooled,1,sizeof(pooled),file)==sizeof(pooled) && !fclose(file));
            assert(CODOL_MountRuntimeArchives(paths,1,NULL,&failed,&failed_asset));
            assert(!unlink(runtime));
            assert(CODOL_LoadMountedCollision("mp_test",&map)==1);
            assert(map.materials.count==2 && !map.materials.unresolved);
            assert(!strcmp(map.materials.materials[0].material,"stone"));
            assert(!strcmp(map.materials.materials[1].material,"stone"));
            CODOL_UnmountArchives();
            assert(!strcmp(map.materials.materials[1].material,"stone"));
            CODOL_FreeCollisionMap(&map);
        }
    }
    {
        uint8_t data[304]={0},world_data[628]={0};
        codol_asset_t asset={15,data,sizeof(data)},world={21,world_data,sizeof(world_data)};
        codol_collision_map_t map={0},saved;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+256,123); put32(data+260,UINT32_MAX); put32(data+264,4);
        memcpy(data+300,"{}\n",4);
        put32(world_data,123); put32(world_data+0x38,UINT32_MAX);
        assert(CODOL_ReadCollisionMap(&asset,&world,NULL,NULL,&map));
        assert(!strcmp(map.entities.text,"{}\n")); saved=map;
        put32(data+264,0);
        assert(!CODOL_ReadCollisionMap(&asset,&world,NULL,NULL,&map));
        assert(!memcmp(&saved,&map,sizeof(map)) && !strcmp(map.entities.text,"{}\n"));
        put32(data+264,4); memcpy(data+300,"{ }",4);
        assert(CODOL_ReadCollisionMap(&asset,&world,NULL,NULL,&map));
        assert(!strcmp(map.entities.text,"{ }"));
        CODOL_FreeCollisionMap(&map); CODOL_FreeCollisionMap(&map);
        assert(!map.entities.storage && !map.brushes.planes);
    }
    {
        uint8_t data[470]={0};
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_brush_tree_t tree={0},saved;
        size_t n;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+16*4,5); put32(data+17*4,UINT32_MAX);
        put32(data+18*4,2); put32(data+19*4,UINT32_MAX);
        put32(data+35*4,1); put32(data+36*4,UINT32_MAX);
        put32(data+37*4,UINT32_MAX); put32(data+38*4,UINT32_MAX);
        put32(data+280,0xffff0000); put32(data+296,0x00030002);
        put32(data+300,0x00010000); put32(data+308,UINT32_MAX);
        put32(data+320,0x00010000); put32(data+328,0x30000001);
        put32(data+340,0x00010000); put32(data+348,0x30000003);
        put32(data+426,123);
        assert(CODOL_ReadCollisionBrushTree(&asset,&tree));
        assert(tree.node_count==5 && tree.index_count==3 && tree.pooled_count==2);
        assert(tree.nodes[1].leafBrushCount==-1 && tree.nodes[1].data.children.childOffset[1]==3);
        assert(tree.nodes[2].data.leaf.brushes==tree.indices+2);
        assert(tree.nodes[3].data.leaf.brushes==tree.indices && tree.nodes[4].data.leaf.brushes==tree.indices+1);
        saved=tree;
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadCollisionBrushTree(&asset,&tree));
            assert(!memcmp(&saved,&tree,sizeof(tree)));
        }
        asset.size=sizeof(data); data[256]=1; /* missing brush */
        assert(!CODOL_ReadCollisionBrushTree(&asset,&tree));
        data[256]=0; put32(data+296,0x00030000); /* self edge */
        assert(!CODOL_ReadCollisionBrushTree(&asset,&tree));
        put32(data+296,0x00030002); put32(data+348,0x30000005); /* wrong slice */
        assert(!CODOL_ReadCollisionBrushTree(&asset,&tree));
        assert(!memcmp(&saved,&tree,sizeof(tree)));
        CODOL_FreeCollisionBrushTree(&tree); assert(!tree.nodes && !tree.indices);
    }
    {
        uint8_t data[312]={0}; size_t n;
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_leaves_t out={0},saved;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+80,3); put32(data+84,UINT32_MAX);
        put32(data+256,17); put32(data+260,0x80000000); put32(data+264,UINT32_MAX);
        put32(data+268,123);
        assert(CODOL_ReadCollisionLeaves(&asset,&out)); saved=out;
        assert(out.surface_count==3 && out.surfaces[0]==17 && out.surfaces[1]==0x80000000 && out.surfaces[2]==UINT32_MAX);
        for (n=0;n<sizeof(data);++n) {
            asset.size=n; assert(!CODOL_ReadCollisionLeaves(&asset,&out));
            assert(!memcmp(&out,&saved,sizeof(out)));
        }
        asset.size=sizeof(data); put32(data+256,19);
        assert(out.surfaces[0]==17);
        assert(CODOL_ReadCollisionLeaves(&asset,&out) && out.surfaces[0]==19);
        CODOL_FreeCollisionLeaves(&out); CODOL_FreeCollisionLeaves(&out);
    }
    {
        uint8_t data[408]={0};
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_leaves_t out={0},saved;
        size_t n;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+14*4,1); put32(data+15*4,UINT32_MAX);
        put32(data+33*4,1); put32(data+34*4,UINT32_MAX);
        put32(data+268,0x3f800000); put32(data+280,0x40000000);
        put32(data+296,0x41200000); put32(data+308,0x3f800000);
        put32(data+320,0x40a00000); put32(data+364,123);
        assert(CODOL_ReadCollisionLeaves(&asset,&out));
        assert(out.leaf_count==1 && out.submodel_count==1);
        assert(out.leaves[0].mins[0]==-1 && out.leaves[0].maxs[0]==3 && out.leaves[0].cluster==-1);
        assert(out.submodels[0].mins[0]==9 && out.submodels[0].maxs[0]==11 && out.submodels[0].radius==5);
        saved=out;
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadCollisionLeaves(&asset,&out));
            assert(!memcmp(&saved,&out,sizeof(out)));
        }
        asset.size=sizeof(data); put32(data+280,0xbf800000);
        assert(!CODOL_ReadCollisionLeaves(&asset,&out));
        assert(out.leaves[0].maxs[0]==3); /* independent source ownership */
        put32(data+280,0); put32(data+320,0x7f800000);
        assert(!CODOL_ReadCollisionLeaves(&asset,&out));
        put32(data+320,0); put32(data+292,1);
        assert(!CODOL_ReadCollisionLeaves(&asset,&out));
        assert(!memcmp(&saved,&out,sizeof(out)));
        CODOL_FreeCollisionLeaves(&out); assert(!out.leaves && !out.submodels);
    }
    {
        uint8_t data[356]={0}, planes[20]={0};
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_brushes_t out={0}, saved;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+2*4,1); put32(data+3*4,0x30001001);
        put32(data+12*4,2); put32(data+13*4,UINT32_MAX);
        put32(data+14*4,1); put32(data+15*4,UINT32_MAX);
        put32(data+256,0x30001001); put32(data+260,0xffff0001);
        put32(data+264,0x30001001); put32(data+268,0xffffffff);
        put32(data+312,123); put32(planes,0x3f800000);
        assert(CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&out));
        assert(out.node_count==2 && out.nodes[0].children[0]==1 && out.nodes[0].children[1]==-1);
        assert(out.nodes[1].plane==out.planes && out.nodes[1].children[0]==-1);
        saved=out; put32(data+268,0xffff0000); /* cycle back to root */
        assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&out));
        put32(data+268,0xfffffffe); /* missing leaf 1 */
        assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&out));
        put32(data+268,0xffffffff); put32(data+264,0x30001002); /* unaligned plane ref */
        assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&out));
        assert(!memcmp(&saved,&out,sizeof(out)));
        CODOL_FreeCollisionBrushes(&out); assert(!out.nodes && !out.node_count);
    }
    {
        uint8_t data[326]={0};
        char name[65]="pooled";
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_materials_t materials={0}, saved;
        size_t n;
        put32(data,123); put32(data+6*4,2); put32(data+7*4,UINT32_MAX);
        put32(data+39*4,UINT32_MAX);
        put32(data+256,UINT32_MAX); put32(data+260,0x80000001); put32(data+264,7);
        put32(data+268,0x30000123); data[280]='x'; put32(data+282,123);
        assert(CODOL_ReadCollisionMaterials(&asset,NULL,NULL,&materials));
        assert(materials.count==2 && materials.unresolved==1);
        assert(!strcmp(materials.materials[0].material,"x") && materials.materials[0].contentFlags==7);
        assert((uint32_t)materials.materials[0].surfaceFlags==0x80000001);
        assert(materials.name_references[1]==0x30000123 && !materials.materials[1].material[0]);
        CODOL_FreeCollisionMaterials(&materials);
        assert(CODOL_ReadCollisionMaterials(&asset,collision_name,name,&materials));
        assert(!materials.unresolved && !strcmp(materials.materials[1].material,"pooled"));
        saved=materials; name[0]='z';
        assert(!strcmp(materials.materials[1].material,"pooled"));
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadCollisionMaterials(&asset,collision_name,name,&materials));
            assert(!memcmp(&materials,&saved,sizeof(saved)));
        }
        asset.size=sizeof(data); memset(name,'a',64); name[64]=0;
        assert(!CODOL_ReadCollisionMaterials(&asset,collision_name,name,&materials));
        name[0]=0;
        assert(!CODOL_ReadCollisionMaterials(&asset,collision_name,name,&materials));
        assert(!memcmp(&materials,&saved,sizeof(saved)));
        CODOL_FreeCollisionMaterials(&materials);
    }
    {
        uint8_t data[725]={0};
        codol_asset_t world={21,data,sizeof(data)};
        codol_world_planes_t planes, saved;
        size_t n;
        put32(data,123); put32(data+8,1);
        put32(data+0x14,1); put32(data+0x18,UINT32_MAX);
        put32(data+0x38,UINT32_MAX);
        put32(data+628,1); put32(data+632,UINT32_MAX); put32(data+636,UINT32_MAX-1);
        put32(data+648,UINT32_MAX); put32(data+680,UINT32_MAX);
        data[684]='x'; put32(data+698,3); /* image name and loaddef payload */
        put32(data+705,0x3f800000);
        assert(CODOL_ReadWorldPlanes(&world,&planes));
        assert(planes.offset==705 && planes.count==1 && planes.name_reference==123 && !planes.name);
        saved=planes;
        for (n=0;n<sizeof(data);++n) {
            world.size=n;
            assert(!CODOL_ReadWorldPlanes(&world,&planes));
            assert(!memcmp(&saved,&planes,sizeof(saved)));
        }
        world.size=sizeof(data); put32(data+698,UINT32_MAX);
        assert(!CODOL_ReadWorldPlanes(&world,&planes));
        put32(data+698,3); put32(data+0x14,UINT32_MAX);
        assert(!CODOL_ReadWorldPlanes(&world,&planes));
        put32(data+0x14,1); put32(data+0x38,0x30001231);
        assert(!CODOL_ReadWorldPlanes(&world,&planes));
        assert(!memcmp(&saved,&planes,sizeof(saved)));
    }
    {
        uint8_t data[386]={0}, planes[20]={0};
        codol_asset_t asset={15,data,sizeof(data)};
        codol_collision_brushes_t brushes={0}, saved;
        size_t n;
        put32(data,123); put32(data+39*4,UINT32_MAX);
        put32(data+2*4,1); put32(data+3*4,0x30001001);
        put32(data+6*4,1); put32(data+7*4,UINT32_MAX);
        put32(data+8*4,1); put32(data+9*4,UINT32_MAX);
        put32(data+10*4,2); put32(data+11*4,UINT32_MAX);
        put32(data+35*4,1); put32(data+36*4,UINT32_MAX);
        put32(data+37*4,UINT32_MAX); put32(data+38*4,UINT32_MAX);
        put32(data+268,0x30001001); data[274]=1; data[275]=1;
        data[276]=4; data[277]=5;
        data[278]=1; put32(data+282,0x30002001); put32(data+286,0x30003001);
        data[308]=1; /* one axial edge plus one nonaxial edge */
        put32(data+314,0x41200000); put32(data+326,0x40000000);
        put32(data+338,0x80000001); put32(data+342,123);
        put32(planes,0x3f800000); put32(planes+12,0x40a00000);
        assert(CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&brushes));
        assert(!((uintptr_t)brushes.brushes&15));
        assert(brushes.brushes[0].sides==brushes.sides && brushes.sides[0].plane==brushes.planes);
        assert(brushes.brushes[0].baseAdjacentSide==brushes.edges && brushes.edges[1]==5);
        assert(brushes.brushes[0].mins[0]==8 && brushes.brushes[0].maxs[0]==12);
        assert(brushes.planes[0].type==0 && brushes.planes[0].dist==5);
        saved=brushes;
        for (n=0;n<sizeof(data);++n) {
            asset.size=n;
            assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&brushes));
            assert(!memcmp(&saved,&brushes,sizeof(saved)));
        }
        asset.size=sizeof(data); data[274]=255;
        assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&brushes));
        data[274]=1; put32(planes,0);
        assert(!CODOL_ReadCollisionBrushes(&asset,planes,sizeof(planes),&brushes));
        assert(brushes.planes[0].normal[0]==1); /* source lifetime independent */
        assert(!memcmp(&saved,&brushes,sizeof(saved)));
        CODOL_FreeCollisionBrushes(&brushes);
        assert(!brushes.planes && !brushes.brush_storage && !brushes.brush_count);
    }
    {
        uint8_t data[430]={0};
        codol_asset_t asset={15, data, sizeof(data)};
        codol_collision_terrain_t terrain={0}, saved;
        size_t n;
        put32(data, 123); put32(data+39*4, UINT32_MAX);
        put32(data+6*4, 1); put32(data+7*4, UINT32_MAX);
        put32(data+22*4, 3); put32(data+23*4, UINT32_MAX);
        put32(data+24*4, 1); put32(data+25*4, UINT32_MAX);
        put32(data+26*4, UINT32_MAX);
        put32(data+27*4, 1); put32(data+28*4, UINT32_MAX);
        put32(data+29*4, 1); put32(data+30*4, UINT32_MAX);
        put32(data+31*4, 1); put32(data+32*4, UINT32_MAX);
        put32(data+268, 0x3f800000); data[306]=1; data[308]=2;
        put32(data+310, 7); put32(data+314, 0x40000000);
        data[342]=1; data[343]=1; put32(data+350, 0x30001001);
        put32(data+354, 0x40400000); put32(data+370, 0x40800000);
        put32(data+386, 123);
        assert(CODOL_ReadCollisionTerrain(&asset, &terrain));
        assert(terrain.vertex_count==3 && terrain.vertices[0][0]==1);
        assert(terrain.triangles[0][2]==2 && terrain.walkable[0]==7);
        assert(terrain.partitions[0].borders==terrain.borders && terrain.borders[0].distEq[0]==2);
        assert(terrain.aabbs[0].origin[0]==3 && terrain.aabbs[0].halfSize[0]==4);
        saved=terrain;
        for (n=0; n<sizeof(data); ++n) {
            asset.size=n;
            assert(!CODOL_ReadCollisionTerrain(&asset, &terrain));
            assert(!memcmp(&saved, &terrain, sizeof(saved)));
        }
        asset.size=sizeof(data); put32(data+268, 0x7fc00000);
        assert(!CODOL_ReadCollisionTerrain(&asset, &terrain));
        assert(terrain.vertices[0][0]==1); /* owned independently of source */
        put32(data+268, 0); data[308]=3;
        assert(!CODOL_ReadCollisionTerrain(&asset, &terrain));
        data[308]=2; data[368]=1; /* self-referencing tree */
        assert(!CODOL_ReadCollisionTerrain(&asset, &terrain));
        assert(!memcmp(&saved, &terrain, sizeof(saved)));
        CODOL_FreeCollisionTerrain(&terrain);
        assert(!terrain.vertices && !terrain.partitions && !terrain.vertex_count);
    }
    {
        uint8_t data[396] = {0};
        codol_asset_t asset = {15, data, sizeof(data)};
        codol_map_entities_t entities = {0};
        size_t offset = 999, n;
        put32(data, 123); put32(data+39*4, UINT32_MAX);
        put32(data+18*4, 1); put32(data+19*4, UINT32_MAX); /* leafbrushes FIRST */
        put32(data+16*4, 1); put32(data+17*4, UINT32_MAX);
        put32(data+29*4, 1); put32(data+30*4, UINT32_MAX);
        put32(data+40*4, 1); put32(data+41*4, UINT32_MAX);
        data[258+2] = 1; put32(data+258+8, UINT32_MAX); /* inline leaf indices */
        put32(data+280+8, UINT32_MAX); /* one inline border despite count zero */
        put32(data+348, 123); put32(data+352, UINT32_MAX); put32(data+356, 4);
        memcpy(data+392, "{\n}", 4);
        assert(CODOL_LocateCollisionMapEntities(&asset, &offset) && offset == 348);
        {
            codol_collision_layout_t layout, saved;
            assert(CODOL_ReadCollisionLayout(&asset, &layout));
            assert(layout.map_entities == 348 && layout.name_reference == 123);
            assert(layout.sections[CODOL_COLL_LEAF_BRUSHES].offset == 256);
            assert(layout.sections[CODOL_COLL_LEAF_BRUSH_NODES].offset == 258);
            assert(layout.sections[CODOL_COLL_PARTITIONS].offset == 280);
            assert(layout.sections[CODOL_COLL_STATIC_NODES].offset == 320);
            assert(layout.sections[CODOL_COLL_PLANES].offset == SIZE_MAX);
            saved = layout; asset.size = 300;
            assert(!CODOL_ReadCollisionLayout(&asset, &layout) && !memcmp(&layout, &saved, sizeof(layout)));
            asset.size = sizeof(data);
        }
        assert(CODOL_ReadCollisionMapEntities(&asset, &entities) && !strcmp(entities.text, "{\n}"));
        CODOL_FreeMapEntities(&entities);
        for (n = 0; n < 392; ++n) {
            asset.size = n; offset = 999;
            assert(!CODOL_LocateCollisionMapEntities(&asset, &offset) && offset == 999);
        }
        asset.size = sizeof(data); put32(data+16*4, UINT32_MAX);
        assert(!CODOL_LocateCollisionMapEntities(&asset, &offset) && offset == 999);
        put32(data+16*4, 1); put32(data+39*4, 0x30000123);
        assert(!CODOL_ReadCollisionMapEntities(&asset, &entities) && !entities.storage);
    }
    {
        uint8_t data[130] = {0};
        codol_map_entities_t entities = {0}, invalid = {0};
        size_t n;
        put32(data, 123); put32(data+4, UINT32_MAX); put32(data+8, 4);
        for (n = 0; n < 3; ++n) { put32(data+12+8*n, 1); put32(data+16+8*n, UINT32_MAX); }
        put32(data+36, UINT32_MAX); data[40] = 1;
        memcpy(data+44, "{\n}", 4);
        put32(data+108, UINT32_MAX); put32(data+112, 0x3f800000);
        data[124] = 0; data[125] = 4; data[126] = 7;
        memcpy(data+128, "s", 2);
        assert(CODOL_ReadMapEntities(data, sizeof(data), &entities));
        assert(entities.consumed == 130 && entities.model_count == 1 && entities.hull_count == 1 && entities.slab_count == 1);
        assert(entities.models == entities.storage+4 && entities.hulls == entities.storage+12 && entities.slabs == entities.storage+44);
        assert(entities.stage_count == 1 && !strcmp(entities.stages[0].name, "s"));
        assert(entities.stages[0].origin[0] == 1 && entities.stages[0].trigger_index == 1024 && entities.stages[0].sun_index == 7);
        for (n = 48; n < sizeof(data); ++n)
            assert(!CODOL_ReadMapEntities(data, n, &invalid) && !invalid.storage);
        data[128] = 'x'; assert(!strcmp(entities.stages[0].name, "s"));
        CODOL_FreeMapEntities(&entities);
        data[52] = 2; /* model references two hulls, only one exists */
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid) && !invalid.storage);
        data[52] = 0; data[84] = 2; /* hull references absent slabs */
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid));
        data[84] = 0; put32(data+68, 0xbf800000); /* negative hull half-size */
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid));
        put32(data+68, 0); put32(data+88, 0x7f800000); /* infinite slab normal */
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid));
        put32(data+88, 0); data[124] = 2; data[125] = 0; /* invalid stage trigger */
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid));
        data[124] = 0; data[125] = 4;
        put32(data+24, 0x30000123);
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &invalid));
    }
    {
        uint8_t data[64] = {0};
        codol_map_entities_t entities = {0}, unchanged = {0};
        put32(data, 0x302a6784); put32(data+4, UINT32_MAX); put32(data+8, 4);
        memcpy(data+44, "{\n}", 4); memset(data+48, 0xa5, 16);
        assert(CODOL_ReadMapEntities(data, sizeof(data), &entities));
        assert(!entities.name && entities.name_reference == 0x302a6784);
        assert(entities.text_size == 4 && entities.consumed == 48 && !strcmp(entities.text, "{\n}"));
        data[44] = 'x'; assert(!strcmp(entities.text, "{\n}"));
        assert(!CODOL_ReadMapEntities(data, 47, &unchanged) && !unchanged.storage);
        data[45] = 0;
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &unchanged));
        CODOL_FreeMapEntities(&entities); CODOL_FreeMapEntities(&entities);
        put32(data, UINT32_MAX); memcpy(data+44, "map", 4); memcpy(data+48, "{\n}", 4);
        assert(CODOL_ReadMapEntities(data, sizeof(data), &entities));
        assert(!strcmp(entities.name, "map") && entities.consumed == 52);
        CODOL_FreeMapEntities(&entities);
        put32(data+4, 0x30000123);
        assert(!CODOL_ReadMapEntities(data, sizeof(data), &unchanged));
    }
    {
        char base[] = "/tmp/codol-base-XXXXXX", patch[] = "/tmp/codol-patch-XXXXXX";
        char bad[] = "/tmp/codol-bad-XXXXXX";
        const char *paths[2] = {base, NULL};
        const codol_engine_rawfile_t *old, *current;
        size_t failed = 99;
        mount_source((const uint8_t *)"old", 3);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &old) == 1);
        write_source_ex((const uint8_t *)"base", 4, 0, base);
        write_source_ex((const uint8_t *)"patch", 5, 0, patch);
        assert(!CODOL_MountArchives(paths, 2, NULL, &failed) && failed == 1);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &current) == 1 && current == old);
        assert(!strcmp(current->buffer, "old"));
        {
            int fd = mkstemp(bad);
            assert(fd >= 0 && write(fd, "bad", 3) == 3 && !close(fd));
            paths[1] = bad;
            assert(!CODOL_MountArchives(paths, 2, NULL, &failed) && failed == 1);
            assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &current) == 1 && current == old);
            assert(!unlink(bad));
        }
        paths[1] = patch; failed = 99;
        assert(CODOL_MountArchives(paths, 2, NULL, &failed) && failed == 99);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &current) == 1);
        assert(!strcmp(current->buffer, "patch") && !strcmp(old->buffer, "old"));
        assert(!CODOL_MountArchives(paths, 0, NULL, &failed) && failed == 0);
        assert(!unlink(base) && !unlink(patch));
        assert(!strcmp(current->buffer, "patch"));
        CODOL_UnmountArchives();
    }
    {
        const codol_engine_rawfile_t *first, *second, *sentinel = (void *)1;
        const uint8_t binary[] = {'x', 0, 'y'};
        assert(!CODOL_LoadEngineRawFile("maps/mp/native.gsc", &sentinel) && sentinel == (void *)1);
        mount_source(binary, sizeof(binary));
        assert(CODOL_LoadEngineRawFile("MAPS\\MP\\NATIVE.GSC", &first) == 1);
        assert(first->len == sizeof(binary) && !memcmp(first->buffer, binary, sizeof(binary)));
        assert(first->buffer[first->len] == 0);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &second) == 1 && first == second);
        mount_source((const uint8_t *)"replacement", 11);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &second) == 1 && first != second);
        assert(!strcmp(second->buffer, "replacement") && !memcmp(first->buffer, binary, sizeof(binary)));
        mount_source_ex((const uint8_t *)"broken", 6, 1);
        assert(CODOL_LoadEngineRawFile("maps/mp/native.gsc", &sentinel) == -1 && sentinel == (void *)1);
        CODOL_UnmountArchives();
        assert(!CODOL_LoadEngineRawFile("maps/mp/native.gsc", &sentinel) && sentinel == (void *)1);
    }
    {
        uint8_t data[79] = {0};
        codol_zone_t zone = {0};
        codol_script_string_t *strings, *sentinel = (void *)1;
        put32(data, sizeof(data)-40); put32(data+40, 4); put32(data+44, UINT32_MAX);
        put32(data+56, 0); put32(data+60, UINT32_MAX);
        put32(data+64, 0x30000123); put32(data+68, UINT32_MAX);
        memcpy(data+72, "tag_x", 6); /* final byte is an explicitly empty string */
        assert(CODOL_OpenZoneImage(&zone, data, sizeof(data)));
        memset(data, 0xcc, sizeof(data));
        assert(CODOL_ReadScriptStrings(&zone, &strings));
        assert(strings[0].reference == 0 && !strings[0].text);
        assert(strings[1].reference == UINT32_MAX && !strcmp(strings[1].text, "tag_x"));
        assert(strings[2].reference == 0x30000123 && !strings[2].text);
        assert(strings[3].text && !*strings[3].text);
        free(strings);
        zone.data[zone.table_offset-1] = 'x';
        assert(!CODOL_ReadScriptStrings(&zone, &sentinel) && sentinel == (void *)1);
        CODOL_CloseZone(&zone);
        assert(!CODOL_ReadScriptStrings(&zone, &sentinel) && sentinel == (void *)1);
        memset(data, 0, sizeof(data)); put32(data, 16);
        assert(CODOL_OpenZoneImage(&zone, data, 56));
        assert(CODOL_ReadScriptStrings(&zone, &sentinel) && !sentinel);
        CODOL_CloseZone(&zone);
    }
    {
        const codol_engine_table_t *first, *second, *sentinel = (void *)1;
        assert(!CODOL_LoadEngineStringTable("t.csv", &sentinel) && sentinel == (void *)1);
        mount_table('x', 0);
        assert(CODOL_LoadEngineStringTable("T.CSV", &first) == 1);
        assert(first->rowCount == 1 && first->columnCount == 1 && !strcmp(first->values[0], "x"));
        assert(CODOL_LoadEngineStringTable("t.csv", &second) == 1 && first == second);
        mount_table('y', 0);
        assert(CODOL_LoadEngineStringTable("t.csv", &second) == 1 && first != second);
        assert(!strcmp(first->values[0], "x") && !strcmp(second->values[0], "y"));
        mount_table('z', 1);
        assert(CODOL_LoadEngineStringTable("t.csv", &sentinel) == -1 && sentinel == (void *)1);
        CODOL_UnmountArchives();
        assert(!CODOL_LoadEngineStringTable("t.csv", &sentinel));
    }
    {
        uint8_t data[108]={0}; codol_zone_t zone={0}; codol_load_blocks_t blocks={0};
        const codol_engine_table_t *first,*same; size_t i,offset=SIZE_MAX;
        char path[]="/tmp/codol-pooled-table-XXXXXX"; const char *paths[]={path}; int fd; FILE *file;
        put32(data,sizeof(data)-40); put32(data+8,4096); put32(data+20,4096);
        put32(data+48,1); put32(data+52,UINT32_MAX); put32(data+56,37); put32(data+60,32);
        put32(data+64,UINT32_MAX); put32(data+68,36); put32(data+72,UINT32_MAX);
        put32(data+76,2); put32(data+80,1); put32(data+84,UINT32_MAX); memcpy(data+88,"t",2);
        put32(data+90,UINT32_MAX); put32(data+94,'x'); put32(data+102,'x'); memcpy(data+106,"x",2);
        assert(CODOL_OpenZoneImage(&zone,data,sizeof(data)) && CODOL_ReplayZone(&zone,&blocks,NULL));
        for(i=0;i+2<=blocks.written[3];++i) if(!memcmp(blocks.data[3]+i,"x",2)) offset=i;
        assert(offset!=SIZE_MAX); put32(data+98,0x30000001+(uint32_t)offset);
        CODOL_FreeLoadBlocks(&blocks); CODOL_CloseZone(&zone);
        fd=mkstemp(path); assert(fd>=0); file=fdopen(fd,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_MountRuntimeArchives(paths,1,NULL,NULL,NULL));
        assert(CODOL_LoadEngineStringTable("t",&first)==1 && first->columnCount==2);
        assert(!strcmp(first->values[0],"x") && !strcmp(first->values[1],"x"));
        same=first; assert(CODOL_LoadEngineStringTable("T",&same)==1 && same==first);
        put32(data+102,'y'); file=fopen(path,"wb"); assert(file);
        assert(fwrite(data,1,sizeof(data),file)==sizeof(data) && !fclose(file));
        assert(CODOL_ReplaceRuntimeArchives(paths,1,NULL,1,NULL,NULL));
        assert(CODOL_LoadEngineStringTable("t",&same)==-1 && same==first && !strcmp(first->values[1],"x"));
        assert(!unlink(path)); CODOL_UnmountArchives();
    }
    {
        uint8_t blob[44] = {0};
        codol_asset_t asset = {CODOL_ASSET_STRINGTABLE, blob, sizeof(blob)};
        codol_stringtable_t table = {0}, unchanged_table = {0};
        put32(blob, UINT32_MAX); put32(blob+4, 2); put32(blob+8, 1); put32(blob+12, UINT32_MAX);
        memcpy(blob+16, "t.csv", 6);
        put32(blob+22, UINT32_MAX); put32(blob+26, 92909918); /* hash("alpha") */
        put32(blob+30, 0x30000123); put32(blob+34, 123);
        memcpy(blob+38, "Alpha", 6);
        assert(CODOL_ReadStringTable(&asset, &table));
        assert(table.rows == 1 && table.columns == 2 && table.unresolved == 1);
        assert(!strcmp(table.name, "t.csv"));
        assert(!strcmp(CODOL_StringTableCell(&table, 0, 0)->text, "Alpha"));
        assert(!CODOL_StringTableCell(&table, 0, 1)->text);
        assert(CODOL_StringTableCell(&table, 0, 1)->reference == 0x30000123);
        assert(!CODOL_StringTableCell(&table, 1, 0));
        blob[38] = 'X';
        assert(!strcmp(CODOL_StringTableCell(&table, 0, 0)->text, "Alpha"));
        assert(!CODOL_ReadStringTable(&asset, &unchanged_table) && !unchanged_table.storage);
        blob[38] = 'A'; asset.size--;
        assert(!CODOL_ReadStringTable(&asset, &unchanged_table));
        CODOL_FreeStringTable(&table); CODOL_FreeStringTable(&table);
    }
    uint8_t *first, *second, *sentinel = (void *)1;
    size_t length, unchanged = 999;
    mount_source((const uint8_t *)"main() { wait 1; }", 18);
    assert(CODOL_LoadScriptAsset("MAPS\\MP\\NATIVE.GSC", &first, &length));
    assert(length == 18 && first[18] == 0);
    mount_source((const uint8_t *)"main() {}", 9);
    assert(CODOL_LoadScriptAsset("maps/mp/native.gsc", &second, &length));
    assert(length == 9 && !strcmp((char *)second, "main() {}"));
    assert(!memcmp(first, "main() { wait 1; }", 18));
    free(second);
    /* Matching corrupt patch must stop resolution before the older valid copy. */
    mount_source_ex((const uint8_t *)"main() {}", 9, 1);
    assert(CODOL_LoadScriptAssetStatus("maps/mp/native.gsc", &sentinel, &unchanged) == -1);
    assert(sentinel == (void *)1 && unchanged == 999);
    assert(!CODOL_LoadScriptAsset("maps/mp/native.gsc", &sentinel, &unchanged));
    /* Unsupported binary script must not silently fall back to an older mount. */
    mount_source((const uint8_t *)"a\0b", 3);
    assert(CODOL_LoadScriptAssetStatus("maps/mp/native.gsc", &sentinel, &unchanged) == -1);
    assert(!CODOL_LoadScriptAsset("maps/mp/native.gsc", &sentinel, &unchanged));
    assert(sentinel == (void *)1 && unchanged == 999);
    CODOL_UnmountArchives();
    assert(CODOL_LoadScriptAssetStatus("maps/mp/native.gsc", &sentinel, &unchanged) == 0);
    assert(!CODOL_LoadScriptAsset("maps/mp/native.gsc", &sentinel, &unchanged));
    assert(!memcmp(first, "main() { wait 1; }", 18)); free(first);
    CODOL_UnmountArchives();
    puts("PASS: native script mounts, ownership, overrides and binary rejection");
    {
        char path[]="/tmp/codol-reference-XXXXXX",csv[128];
        const codol_engine_table_t *table=NULL,*again=NULL;
        int fd=mkstemp(path);FILE *file;assert(fd>=0);
        file=fdopen(fd,"wb");assert(file);
        assert(fputs("item,rank\nghillie,4\n",file)>=0 && !fclose(file));
        snprintf(csv,sizeof(csv),"%s.csv",path);assert(!rename(path,csv));
        const char *name=strrchr(csv,'/')+1;
        assert(CODOL_LoadReferenceStringTable("/tmp",name,&table)==1);
        assert(table->columnCount==2 && table->rowCount==2 && !strcmp(table->values[3],"4"));
        file=fopen(csv,"wb");assert(file);assert(fputs("\"broken",file)>=0 && !fclose(file));
        assert(CODOL_LoadReferenceStringTable("/tmp",name,&again)==1 && again==table);
        assert(!strcmp(table->values[3],"4"));
        CODOL_UnmountArchives();again=(void *)1;
        assert(CODOL_LoadReferenceStringTable("/tmp",name,&again)==-1 && again==(void *)1);
        assert(CODOL_LoadReferenceStringTable("/tmp","../escape.csv",&again)==-1);
        assert(!remove(csv));CODOL_UnmountArchives();
        puts("PASS: reference table ownership, cache lifetime, malformed reload and path validation");
    }
    return 0;
}
