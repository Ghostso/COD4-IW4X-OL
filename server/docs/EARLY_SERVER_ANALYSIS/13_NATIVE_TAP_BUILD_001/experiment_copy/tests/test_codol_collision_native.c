#include "codol_collision_native.h"
#include "codol_dynents_native.h"
#include "qcommon_io.h"
#include <assert.h>
#include <float.h>
#include <stdio.h>
#include <string.h>

static TraceThreadInfo thread_info;
void *Sys_GetValue(int key) { assert(key==3); return &thread_info; }
void Com_PrintError(conChannel_t channel,const char *format,...) { (void)channel; (void)format; assert(0); }
void Com_Printf(conChannel_t channel,const char *format,...) { (void)channel; (void)format; }
static void test_clipmap(void)
{
    codol_collision_map_t source={0}; codol_native_clip_map_t native={0},saved;
    codol_collision_plane_t plane={{1,0,0},0,0,0,{0}};
    codol_collision_node_t node={&plane,{-1,-2}};
    codol_collision_leaf_t leaves[2]={{0}}; codol_collision_submodel_t model={0};
    codol_collision_material_t material={{"stone"},5,7};
    codol_collision_static_model_t placement={0}; codol_collision_brush_node_t tree={0};
    codol_dynamic_entity_t entity={0}; codol_dynamic_entities_t dynamic={{1,0},{&entity,NULL}};
    codol_dynamic_binding_t binding={0}; const codol_dynamic_binding_t *bindings[2]={&binding,NULL};
    int borrowed; uint8_t pvs[2]={1,2}; int16_t clusters[2]={0,1}; char text[]="{}",name[]="maps/test";
    codol_clip_map_metadata_t metadata={name,2,1,1,pvs,2,clusters,2};
    vec3_t front={1,0,0},back={-1,0,0};
    source.brushes.plane_count=1; source.brushes.planes=&plane;
    source.brushes.node_count=1; source.brushes.nodes=&node;
    source.brush_tree.node_count=1; source.brush_tree.nodes=&tree;
    source.leaves.leaf_count=2; source.leaves.leaves=leaves;
    source.leaves.submodel_count=1; source.leaves.submodels=&model;
    source.materials.count=1; source.materials.materials=&material;
    source.static_model_count=source.static_models.count=1; source.static_models.models=&placement;
    source.entities.text=text; source.entities.text_size=sizeof(text);
    source.checksum=0x87654321;
    placement.xmodel=&borrowed; entity.type=1; entity.model_reference=123;
    entity.quat[3]=1; binding.model=(struct XModel *)&borrowed;
    assert(CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native)); saved=native;
    assert(native.map.planes==native.brushes.planes && native.map.nodes[0].plane==native.map.planes);
    assert(native.map.leafs==native.leaves.leaves && native.map.materials==native.assets.materials);
    assert(native.map.staticModelList[0].xmodel==(void *)&borrowed && native.map.checksum==0x87654321);
    assert(native.map.dynEntDefList[0]==native.dynamics.definitions[0] && native.map.dynEntPoseList[0]);
    assert(native.map.box_brush==native.brushes.brushes && native.map.box_model.leaf.leafBrushNode==1);
    assert(native.map.mapEnts->name==native.map.name && native.map.mapEnts->numEntityChars==3 && !native.map.isInUse);
    cm=native.map;
    assert(CM_PointLeafnum(front)==0 && CM_PointLeafnum(back)==1);
    assert(CM_LeafCluster(0)==0 && CM_LeafCluster(1)==1);
    assert(*CM_ClusterPVS(0)==1 && *CM_ClusterPVS(1)==2 && CM_NumInlineModels()==1);
    assert(!strcmp(CM_EntityString(),"{}")); memset(&cm,0,sizeof(cm));
    metadata.visibility_size=1; assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native));
    metadata.visibility_size=2; clusters[1]=2;
    assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native)); clusters[1]=1;
    node.children[1]=-3; assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native)); node.children[1]=-2;
    node.children[0]=0; assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native)); node.children[0]=-1;
    binding.model=NULL; assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native));
    binding.model=(struct XModel *)&borrowed; text[2]='x';
    assert(!CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native)); text[2]=0;
    assert(!memcmp(&native,&saved,sizeof(native)));
    metadata.vised=0; metadata.visibility_size=1;
    assert(CODOL_BuildNativeClipMap(&source,&dynamic,bindings,&metadata,&native));
    assert(CODOL_BuildUnculledNativeClipMap(&source,&dynamic,bindings,name,&native));
    assert(native.map.numClusters==1 && native.map.clusterBytes==8 && !native.map.vised);
    assert(native.map.leafs[0].cluster==0 && native.map.leafs[1].cluster==0);
    assert(native.map.visibility[0]==255 && native.map.visibility[7]==255);
    saved=native; binding.model=NULL;
    assert(!CODOL_BuildUnculledNativeClipMap(&source,&dynamic,bindings,name,&native));
    assert(!memcmp(&native,&saved,sizeof(native))); binding.model=(struct XModel *)&borrowed;
    {
        uint8_t tm[8]={1,0,0,0,1,0,0,0},th[32]={0},ts[20]={0};
        float half=2,one=1;
        for(unsigned a=0;a<3;++a) memcpy(th+12+4*a,&half,4);
        th[24]=1; th[28]=1;
        memcpy(ts,&one,4); memcpy(ts+4,&one,4); memcpy(ts+16,&one,4);
        source.entities.model_count=1; source.entities.models=tm;
        source.entities.hull_count=1; source.entities.hulls=th;
        source.entities.slab_count=1; source.entities.slabs=ts;
        assert(CODOL_BuildUnculledNativeClipMap(&source,&dynamic,bindings,name,&native));
        assert(native.trigger_model_base==1 && native.trigger_model_count==1);
        cm=native.map;
        vec3_t inside={0,0,0},corner={1,1,0};
        assert(cm.numSubModels==2 && CM_PointContents(inside,1)==1 && CM_PointContents(corner,1)==0);
        assert(cm.nodes[0].plane==cm.planes && CM_PointLeafnum(back)==1);
        assert(cm.box_brush==cm.brushes+cm.numBrushes);
        cLeafBrushNode_t *box=cm.leafbrushNodes+cm.box_model.leaf.leafBrushNode;
        assert(box->leafBrushCount==1 && box->data.leaf.brushes[0]==cm.numBrushes);
        saved=native; th[28]=2;
        assert(!CODOL_BuildUnculledNativeClipMap(&source,&dynamic,bindings,name,&native));
        assert(!memcmp(&native,&saved,sizeof(native)));
        source.entities.model_count=source.entities.hull_count=source.entities.slab_count=0;
        source.entities.models=source.entities.hulls=source.entities.slabs=NULL;
    }
    memset(text,0,sizeof(text)); memset(name,0,sizeof(name)); memset(pvs,0,sizeof(pvs));
    memset(leaves,0,sizeof(leaves)); memset(&plane,0,sizeof(plane)); memset(&entity,0,sizeof(entity));
    cm=native.map;
    assert(!strcmp(cm.name,"maps/test") && !strcmp(CM_EntityString(),"{}"));
    assert(CM_PointLeafnum(back)==1 && CM_LeafCluster(1)==0 && *CM_ClusterPVS(0)==255);
    assert(cm.dynEntDefList[0][0].type==1 && cm.dynEntDefList[0][0].xModel==(void *)&borrowed);
    memset(&cm,0,sizeof(cm)); CODOL_FreeNativeClipMap(&native); CODOL_FreeNativeClipMap(&native);
}
static void test_assets(void)
{
    codol_collision_material_t rows[2]={{{0}}};
    codol_collision_static_model_t placements[2]={{0}};
    uint32_t refs[2]={0}; int borrowed[2]={0}; unsigned i;
    codol_collision_materials_t materials={2,0,rows,refs};
    codol_collision_static_models_t models={2,0,placements,refs};
    codol_native_collision_assets_t native={0},saved;
    strcpy(rows[0].material,"stone"); strcpy(rows[1].material,"metal");
    rows[1].surfaceFlags=17; rows[1].contentFlags=42;
    for (i=0;i<2;++i) {
        placements[i].xmodel=borrowed+i; placements[i].writable=7+i;
        placements[i].origin[0]=i+2; placements[i].absmin[0]=-3; placements[i].absmax[0]=4;
        placements[i].invScaledAxis[1][2]=0.5f;
    }
    assert(CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); saved=native;
    assert(native.material_count==2 && native.model_count==2);
    assert(native.materials[1].surfaceFlags==17 && native.materials[1].contentFlags==42);
    assert(native.models[1].xmodel==(void *)(borrowed+1) && native.models[1].origin[0]==3);
    assert(native.models[1].writable==8 && native.models[1].invScaledAxis[1][2]==0.5f);
    refs[1]=123; assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); refs[1]=0;
    models.unresolved=1; assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); models.unresolved=0;
    materials.unresolved=1; assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); materials.unresolved=0;
    placements[1].xmodel=NULL; assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native));
    placements[1].xmodel=borrowed+1; placements[1].absmin[0]=5;
    assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); placements[1].absmin[0]=-3;
    placements[1].invScaledAxis[0][0]=__builtin_nanf("");
    assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native)); placements[1].invScaledAxis[0][0]=0;
    memset(rows[1].material,'x',64); assert(!CODOL_BuildNativeCollisionAssets(&materials,&models,&native));
    assert(!memcmp(&native,&saved,sizeof(native)) && !strcmp(native.materials[1].material,"metal"));
    memset(rows,0,sizeof(rows)); memset(placements,0,sizeof(placements));
    assert(!strcmp(native.materials[0].material,"stone") && native.models[1].origin[0]==3);
    materials.count=models.count=0;
    assert(CODOL_BuildNativeCollisionAssets(&materials,&models,&native) && !native.model_count);
    CODOL_FreeNativeCollisionAssets(&native); CODOL_FreeNativeCollisionAssets(&native);
}

static void test_terrain(void)
{
    float vertices[3][3]={{0,0,0},{1,0,0},{0,1,0}};
    uint16_t triangles[2][3]={{0,1,2},{2,1,0}}; uint32_t walkable=0x2d;
    codol_collision_border_t borders[2]={{0}};
    codol_collision_partition_t partitions[2]={{0}};
    codol_collision_aabb_t aabbs[3]={{0}};
    codol_collision_terrain_t source={3,2,1,2,2,3,vertices,triangles,&walkable,borders,partitions,aabbs};
    codol_native_terrain_t native={0},saved;
    borders[1].length=7;
    partitions[0].triCount=partitions[1].triCount=1;
    partitions[0].borderCount=partitions[1].borderCount=1;
    partitions[0].borders=borders; partitions[1].borders=borders+1; partitions[1].firstTri=1;
    aabbs[0].childCount=2; aabbs[0].index=1; aabbs[2].index=1; aabbs[2].materialIndex=5;
    assert(CODOL_BuildNativeCollisionTerrain(&source,&native)); saved=native;
    assert(native.partitions[1].borders==native.borders+1 && native.partitions[1].borders->length==7);
    assert(native.aabbs[0].childCount==2 && native.aabbs[0].u.firstChildIndex==1);
    assert(native.aabbs[2].u.partitionIndex==1 && native.aabbs[2].materialIndex==5);
    assert(native.triangles[1][0]==2 && native.walkable[0]==0x2d);
    partitions[1].borders=borders+2;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    partitions[1].borders=(codol_collision_border_t *)((char *)borders+1);
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    partitions[1].borders=borders+1; partitions[1].firstTri=2;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    partitions[1].firstTri=1; triangles[1][0]=3;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    triangles[1][0]=2; aabbs[0].index=0;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    aabbs[0].index=2;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    aabbs[0].index=1; source.walkable_words=0;
    assert(!CODOL_BuildNativeCollisionTerrain(&source,&native) && !memcmp(&saved,&native,sizeof(native)));
    source.walkable_words=1;
    assert(CODOL_BuildNativeCollisionTerrain(&source,&native));
    memset(vertices,0,sizeof(vertices)); memset(borders,0,sizeof(borders)); walkable=0;
    assert(native.vertices[1][0]==1 && native.borders[1].length==7 && native.walkable[0]==0x2d);
    CODOL_FreeNativeCollisionTerrain(&native); CODOL_FreeNativeCollisionTerrain(&native);
    assert(!native.vertices && !native.partitions && !native.aabbs);
}
static void test_leaves(void)
{
    codol_collision_leaf_t leaf={0}; codol_collision_submodel_t model={0};
    codol_collision_leaves_t source={1,1,&leaf,&model};
    codol_native_leaves_t native={0},saved;
    uint32_t surfaces[3]={17,0x80000000,UINT32_MAX};
    source.surface_count=3; source.surfaces=surfaces;
    leaf.firstCollAabbIndex=1; leaf.collAabbCount=2; leaf.leafBrushNode=2;
    leaf.cluster=-1; leaf.brushContents=19; leaf.terrainContents=7; leaf.mins[0]=-3;
    model.leaf=leaf; model.radius=8; model.maxs[0]=6;
    assert(CODOL_BuildNativeCollisionLeaves(&source,3,3,&native)); saved=native;
    assert(native.surface_count==3 && !memcmp(native.surfaces,surfaces,sizeof(surfaces)));
    source.surfaces=NULL;
    assert(!CODOL_BuildNativeCollisionLeaves(&source,3,3,&native) && !memcmp(&saved,&native,sizeof(native)));
    source.surfaces=surfaces;
    assert(native.leaves[0].cluster==-1 && native.leaves[0].brushContents==19);
    assert(native.models[0].leaf.leafBrushNode==2 && native.models[0].radius==8);
    assert(native.models[0].maxs[0]==6 && native.models[0].leaf.terrainContents==7);
    assert(!CODOL_BuildNativeCollisionLeaves(&source,2,3,&native) && !memcmp(&saved,&native,sizeof(native)));
    assert(!CODOL_BuildNativeCollisionLeaves(&source,3,2,&native) && !memcmp(&saved,&native,sizeof(native)));
    model.leaf.cluster=-2;
    assert(!CODOL_BuildNativeCollisionLeaves(&source,3,3,&native) && !memcmp(&saved,&native,sizeof(native)));
    model.leaf.cluster=-1; source.submodel_count=CAPSULE_MODEL_HANDLE+1;
    assert(!CODOL_BuildNativeCollisionLeaves(&source,3,3,&native) && !memcmp(&saved,&native,sizeof(native)));
    source.submodel_count=1;
    assert(CODOL_BuildNativeCollisionLeaves(&source,3,3,&native));
    memset(&leaf,0,sizeof(leaf)); memset(&model,0,sizeof(model));
    memset(surfaces,0,sizeof(surfaces));
    assert(native.surfaces[0]==17 && native.surfaces[1]==0x80000000 && native.surfaces[2]==UINT32_MAX);
    assert(native.leaves[0].mins[0]==-3 && native.models[0].radius==8);
    /* Exercise retained engine model counting against the native array. */
    cm.numSubModels=native.model_count; cm.cmodels=native.models;
    assert(CM_NumInlineModels()==1);
    memset(&cm,0,sizeof(cm));
    CODOL_FreeNativeCollisionLeaves(&native); CODOL_FreeNativeCollisionLeaves(&native);
    assert(!native.models && !native.leaves);
}
static void test_dynamic_definitions(void)
{
    codol_dynamic_entity_t rows[2]={{0}};
    codol_dynamic_entities_t source={{1,1},{rows,rows+1}};
    int model,effect,preset;
    codol_dynamic_binding_t bound[2]={{(struct XModel *)&model,(struct FxEffectDef *)&effect,(struct PhysPreset *)&preset},{0}};
    const codol_dynamic_binding_t *bindings[2]={bound,bound+1};
    codol_native_dynamic_entities_t native={0},saved;
    rows[0].type=2; rows[0].quat[3]=1; rows[0].origin[1]=7;
    rows[0].model_reference=rows[0].effect_reference=rows[0].preset_reference=UINT32_MAX;
    rows[0].health=50; rows[0].mass[8]=3; rows[0].contents=0x80000001;
    rows[1].type=1; rows[1].brush_model=4; rows[1].physics_brush_model=6;
    assert(CODOL_BuildNativeDynamicEntities(&source,bindings,&native)); saved=native;
    assert(native.count[0]==1 && native.count[1]==1);
    {
        unsigned category; uint8_t zeros[32]={0};
        for(category=0;category<2;++category) {
            assert(native.poses[category] && !memcmp(native.poses[category],zeros,32));
            assert(native.clients[category] && !memcmp(native.clients[category],zeros,12));
            assert(native.collisions[category] && !memcmp(native.collisions[category],zeros,20));
            ((uint8_t *)native.poses[category])[31]=1;
            ((uint8_t *)native.clients[category])[11]=2;
            ((uint8_t *)native.collisions[category])[19]=3;
        }
        assert(native.poses[0]!=native.poses[1] && native.clients[0]!=native.clients[1] && native.collisions[0]!=native.collisions[1]);
    }
    assert(native.definitions[0]->xModel==bound[0].model && native.definitions[0]->destroyFx==bound[0].effect);
    assert(native.definitions[0]->physPreset==bound[0].preset && !native.definitions[0]->destroyPieces);
    assert(native.definitions[0]->health==50 && native.definitions[0]->mass[8]==3);
    assert((uint32_t)native.definitions[0]->contents==0x80000001 && native.definitions[0]->origin[1]==7);
    assert(native.definitions[1]->brushModel==4 && native.definitions[1]->physicsBrushModel==6);
    bound[0].effect=NULL;
    /* A referenced effect may be absent from the server's cosmetic decoder. */
    assert(CODOL_BuildNativeDynamicEntities(&source,bindings,&native));
    assert(!native.definitions[0]->destroyFx); saved=native;
    bound[0].effect=(struct FxEffectDef *)&effect; rows[1].type=3;
    assert(!CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && !memcmp(&native,&saved,sizeof(saved)));
    rows[1].type=1; source.count[1]=65536;
    assert(!CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && !memcmp(&native,&saved,sizeof(saved)));
    source.count[1]=1; bound[1].preset=(struct PhysPreset *)&preset;
    assert(!CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && !memcmp(&native,&saved,sizeof(saved)));
    bound[1].preset=NULL;
    {
        uint32_t nan_bits=0x7fc00000;
        memcpy(&rows[1].mass[0],&nan_bits,4);
        assert(!CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && !memcmp(&native,&saved,sizeof(saved)));
        rows[1].mass[0]=0;
    }
    rows[0].mass[8]=9;
    assert(native.definitions[0]->mass[8]==3);
    assert(CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && native.definitions[0]->mass[8]==9);
    assert(!((uint8_t *)native.poses[0])[31] && !((uint8_t *)native.clients[1])[11] && !((uint8_t *)native.collisions[1])[19]);
    source.count[0]=0; source.count[1]=2; source.entities[1]=rows; bindings[1]=bound;
    assert(CODOL_BuildNativeDynamicEntities(&source,bindings,&native));
    assert(native.count[1]==2 && native.definitions[1][1].type==1 && !native.poses[0]);
    ((uint8_t *)native.poses[1])[63]=4;
    ((uint8_t *)native.clients[1])[23]=5;
    ((uint8_t *)native.collisions[1])[39]=6;
    source.count[0]=source.count[1]=0;
    assert(CODOL_BuildNativeDynamicEntities(&source,bindings,&native) && !native.definitions[0] && !native.definitions[1]);
    assert(!native.poses[0] && !native.poses[1] && !native.clients[0] && !native.clients[1] && !native.collisions[0] && !native.collisions[1]);
    CODOL_FreeNativeDynamicEntities(&native); CODOL_FreeNativeDynamicEntities(&native);
}
int main(void)
{
    codol_collision_plane_t planes[2]={{0}};
    codol_collision_side_t sides[1]={{0}};
    uint8_t edges[3]={7,8,9};
    codol_collision_brush_t brushes[2]={{0}};
    codol_collision_node_t nodes[1]={{0}};
    codol_collision_brush_node_t tree_nodes[2]={{0}};
    uint16_t indices[2]={0,1};
    codol_collision_brushes_t source={0}; codol_collision_brush_tree_t tree={0};
    codol_native_brushes_t native={0},saved; uint32_t i;
    planes[1].normal[0]=1; planes[1].dist=17;
    sides[0].plane=planes+1; sides[0].materialNum=3; sides[0].edgeCount=1;
    brushes[0].numsides=1; brushes[0].sides=sides; brushes[0].contents=19;
    brushes[0].baseAdjacentSide=edges; brushes[0].edgeCount[0][0]=1;
    brushes[1].baseAdjacentSide=edges+2; brushes[1].edgeCount[1][2]=1;
    nodes[0].plane=planes+1; nodes[0].children[0]=-1; nodes[0].children[1]=-2;
    tree_nodes[1].leafBrushCount=2; tree_nodes[1].data.leaf.brushes=indices;
    source.plane_count=2; source.planes=planes; source.side_count=1; source.sides=sides;
    source.edge_count=3; source.edges=edges; source.brush_count=2; source.brushes=brushes;
    source.node_count=1; source.nodes=nodes;
    tree.node_count=2; tree.nodes=tree_nodes; tree.index_count=2; tree.indices=indices;
    assert(CODOL_BuildNativeCollisionBrushes(&source,&tree,&native)); saved=native;
    assert(!((uintptr_t)native.brushes&15));
    assert(native.sides[0].plane==native.planes+1 && native.planes[1].dist==17);
    assert(native.nodes[0].plane==native.planes+1 && native.nodes[0].children[1]==-2);
    assert(native.brushes[0].sides==native.sides && native.brushes[1].baseAdjacentSide==native.edges+2);
    assert(native.brush_nodes[1].data.leaf.brushes==native.indices);
    assert(native.brush_node_count==3 && native.index_count==3);
    assert(native.box_model.leaf.leafBrushNode==2 && native.box_model.leaf.brushContents==-1);
    assert(!native.box_model.leaf.terrainContents && !native.brushes[2].numsides && !native.brushes[2].sides);
    assert(native.brush_nodes[2].leafBrushCount==1 && native.brush_nodes[2].data.leaf.brushes==native.indices+2);
    assert(native.indices[2]==2 && native.brushes[2].contents==-1);
    for(i=0;i<3;++i) {
        assert(native.box_model.leaf.mins[i]==FLT_MAX && native.box_model.leaf.maxs[i]==-FLT_MAX);
        assert(native.brushes[2].axialMaterialNum[0][i]==-1 && native.brushes[2].axialMaterialNum[1][i]==-1);
    }
    {
        vec3_t mins={-10,-20,-30},maxs={10,20,30};
        thread_info.box_model=&native.box_model;
        thread_info.box_brush=native.brushes+native.brush_count;
        assert(CM_TempBoxModel(mins,maxs)==CAPSULE_MODEL_HANDLE);
        assert(!memcmp(native.box_model.mins,mins,sizeof(mins)));
        assert(!memcmp(thread_info.box_brush->maxs,maxs,sizeof(maxs)));
        assert(native.box_model.leaf.leafBrushNode==2);
        saved=native;
    }
    sides[0].plane=(codol_collision_plane_t *)((char *)planes+1);
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    sides[0].plane=planes+2;
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    sides[0].plane=planes+1; brushes[0].numsides=2;
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    brushes[0].numsides=1; brushes[1].baseAdjacentSide=edges+3;
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    brushes[1].baseAdjacentSide=edges+2; tree_nodes[1].data.leaf.brushes=indices+1;
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    tree_nodes[1].data.leaf.brushes=indices; indices[1]=2;
    assert(!CODOL_BuildNativeCollisionBrushes(&source,&tree,&native) && !memcmp(&native,&saved,sizeof(native)));
    indices[1]=1;
    assert(CODOL_BuildNativeCollisionBrushes(&source,&tree,&native));
    memset(planes,0,sizeof(planes)); memset(edges,0,sizeof(edges)); memset(indices,0,sizeof(indices));
    assert(native.planes[1].dist==17 && native.edges[2]==9 && native.indices[1]==1);
    CODOL_FreeNativeCollisionBrushes(&native); CODOL_FreeNativeCollisionBrushes(&native);
    assert(!native.brushes && !native.brush_nodes && !native.indices);
    test_terrain(); test_dynamic_definitions(); test_assets();
    test_leaves(); test_clipmap();
    puts("PASS: owned native brushes/terrain/leaves/dynamic definitions, relocation and temporary box hull");
    return 0;
}
