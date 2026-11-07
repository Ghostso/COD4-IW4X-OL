#include "codol_physics_native.h"
#include "cm_local.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void u32(uint8_t *p,uint32_t v) { unsigned i; for(i=0;i<4;++i)p[i]=v>>(8*i); }
static void f32(uint8_t *p,float f) { uint32_t v; memcpy(&v,&f,4); u32(p,v); }
int main(void)
{
    uint8_t header[72]={0},record[68]={0},raw[68]={0},edges[28]={0};
    uint8_t sides[8]={0},planes[20]={0},other[20]={0};
    const uint8_t *side_planes[]={other};
    codol_physics_geometry_t geometry={0}; codol_physics_map_t source={0};
    codol_native_physics_map_t native={0},saved; BrushWrapper_t *b; unsigned i;
    source.name="brush"; source.header=header; source.count=1; source.geometries=&geometry;
    geometry.record=record; geometry.brush=raw; geometry.adjacency=edges; geometry.adjacency_size=24;
    u32(record,UINT32_MAX-1); u32(raw+60,24);
    for(i=0;i<3;++i) { f32(raw+4*i,10+i); f32(raw+12+4*i,2+i); f32(record+8+16*i,1); }
    for(i=0;i<6;++i) { raw[48+i]=4*i; raw[54+i]=4; raw[36+2*i]=i; }
    for(i=0;i<24;++i) edges[i]=i%6;
    assert(CODOL_BuildNativePhysicsMap(&source,&native)); b=native.map.geoms[0].brush;
    assert(b && !((uintptr_t)b&15) && !b->numsides && b->totalEdgeCount==24);
    assert(b->mins[0]==8 && b->maxs[2]==16 && b->firstAdjacentSideOffsets[1][2]==20);
    assert(!memcmp(b->baseAdjacentSide,edges,24)); saved=native;
    raw[48]=23; assert(!CODOL_BuildNativePhysicsMap(&source,&native));
    assert(!memcmp(&saved,&native,sizeof(native))); raw[48]=0;
    f32(raw+12,-1); assert(!CODOL_BuildNativePhysicsMap(&source,&native)); f32(raw+12,2);
    /* Nonaxial side: the per-side plane may be a separate resolved object. */
    raw[24]=1; geometry.side_count=1; geometry.sides=sides;
    geometry.planes=planes; geometry.side_planes=side_planes;
    geometry.adjacency_size=28; u32(raw+60,28);
    sides[4]=9; sides[6]=24; sides[7]=4;
    f32(planes,0.6f); f32(planes+4,0.8f); f32(planes+12,3);
    f32(other,-0.6f); f32(other+4,0.8f); f32(other+12,4);
    assert(CODOL_BuildNativePhysicsMap(&source,&native)); b=native.map.geoms[0].brush;
    assert(b->numsides==1 && b->sides[0].materialNum==9 && b->sides[0].firstAdjacentSideOffset==24);
    assert(b->sides[0].plane->signbits==1 && b->sides[0].plane->type==3 && b->sides[0].plane->dist==4);
    assert(b->planes[0].dist==3 && b->sides[0].plane!=b->planes);
    saved=native; f32(other,0); assert(!CODOL_BuildNativePhysicsMap(&source,&native));
    assert(!memcmp(&saved,&native,sizeof(native)));
    memset(raw,0,sizeof(raw)); memset(planes,0,sizeof(planes)); memset(other,0,sizeof(other));
    memset(edges,0,sizeof(edges));
    assert(b->mins[0]==8 && b->planes[0].dist==3 && b->sides[0].plane->dist==4);
    assert(b->baseAdjacentSide[1]==1);
    CODOL_FreeNativePhysicsMap(&native); CODOL_FreeNativePhysicsMap(&native);
    puts("CoDOL native physics brush tests passed"); return 0;
}
