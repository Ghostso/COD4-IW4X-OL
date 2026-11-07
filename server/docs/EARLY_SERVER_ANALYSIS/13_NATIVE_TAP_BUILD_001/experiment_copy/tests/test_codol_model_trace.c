/* Exercise converted collision records through the retained assembly tracer. */
#include "codol_xmodel_native.h"
#include "cm_public.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

extern int XModelTraceLine(const XModel *,trace_t *,const float *,const float *,int);

static trace_t trace(const XModel *model,const float start[3],const float end[3],int mask,int expected)
{
    trace_t result={0}; result.fraction=1;
    assert(XModelTraceLine(model,&result,start,end,mask)==expected);
    return result;
}
int main(void)
{
    static const unsigned strides[6]={2,1,8,12,1,32};
    unsigned char arrays[6][64] __attribute__((aligned(16)))={{0}};
    uint16_t handle=1;
    float triangle[2][12]={
        {0,0,-1,0, 1,0,0,0, 0,1,0,0},
        {0,0,1,0, 1,0,0,0, 0,1,0,0}
    };
    float start[3]={.25f,.25f,1},end[3]={.25f,.25f,-1};
    codol_mounted_model_skeleton_t source={0};
    codol_mounted_model_geometry_t geometry={0};
    codol_xmodel_collision_surface_t surfaces[2]={{0}};
    codol_native_model_core_t core={0},saved;
    trace_t result; unsigned i;
    source.skeleton.name="native_triangle";
    source.skeleton.bones=source.skeleton.roots=1;
    for(i=0;i<6;++i) {
        source.skeleton.arrays[i].count=i>=1 && i<=3 ? 0 : 1;
        source.skeleton.arrays[i].stride=strides[i];
        source.skeleton.arrays[i].data=arrays[i];
    }
    geometry.bounds.bone_count=1; geometry.collision.count=2; geometry.collision.surfaces=surfaces;
    for(i=0;i<2;++i) {
        surfaces[i].mins[2]=-.1f;
        surfaces[i].maxs[0]=surfaces[i].maxs[1]=1; surfaces[i].maxs[2]=.1f;
        surfaces[i].contents=i ? 1 : 2; surfaces[i].surfFlags=i ? 7 : 5;
        surfaces[i].triangle_count=2; surfaces[i].triangles=triangle;
    }
    assert(CODOL_BuildNativeModelCore(&source,&geometry,&handle,1,&core));
    assert(sizeof(core.model.collSurfs[0])==44);
    /* The second descriptor's second triangle proves both assembly strides. */
    result=trace(&core.model,start,end,1,0);
    assert(fabsf(result.fraction-.4375f)<.00001f && result.normal[2]==1);
    assert(result.cflags==1 && result.sflags==7 && !result.startsolid && !result.allsolid);
    result=trace(&core.model,start,end,2,0);
    assert(result.cflags==2 && result.sflags==5);
    result=trace(&core.model,start,end,4,-1); assert(result.fraction==1);
    core.model.collSurfs[1].collTris=triangle+1; core.model.collSurfs[1].numCollTris=1;
    result=trace(&core.model,end,start,1,-1); assert(result.fraction==1); /* back face */
    start[0]=end[0]=start[1]=end[1]=.75f;
    result=trace(&core.model,start,end,1,-1); assert(result.fraction==1); /* outside triangle, inside bounds */
    core.model.collLod=-1;
    start[0]=end[0]=start[1]=end[1]=.25f;
    result=trace(&core.model,start,end,1,-1); assert(result.fraction==1);
    saved=core; surfaces[1].triangles=NULL;
    assert(!CODOL_BuildNativeModelCore(&source,&geometry,&handle,1,&core));
    assert(!memcmp(&saved,&core,sizeof(core)));
    surfaces[1].triangles=triangle; surfaces[1].triangle_count=UINT32_MAX;
    assert(!CODOL_BuildNativeModelCore(&source,&geometry,&handle,1,&core));
    assert(!memcmp(&saved,&core,sizeof(core)));
    CODOL_FreeNativeModelCore(&core);
    assert(triangle[1][2]==1); /* triangle storage remains geometry-owned */
    puts("PASS: converted model collision records through retained assembly tracing");
    return 0;
}
