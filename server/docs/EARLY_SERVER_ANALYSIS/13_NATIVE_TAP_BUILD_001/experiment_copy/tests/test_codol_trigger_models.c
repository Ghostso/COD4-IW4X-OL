#include "codol_assets.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static void u16(unsigned char *p,unsigned v) { p[0]=v; p[1]=v>>8; }
static void f32(unsigned char *p,float v) { memcpy(p,&v,4); }
static int contains(const codol_trigger_hull_t *h,const float p[3])
{
    for(unsigned i=0;i<h->plane_count;++i) {
        const codol_trigger_plane_t *plane=h->planes+i;
        float dot=0; for(unsigned a=0;a<3;++a) dot+=plane->normal[a]*p[a];
        if(dot>plane->distance+0.00001f) return 0;
    }
    return 1;
}
int main(void)
{
    unsigned char models[16]={0},hulls[96]={0},slabs[40]={0};
    codol_map_entities_t source={0}; codol_trigger_model_t model={0};
    source.models=models; source.model_count=2; source.hulls=hulls; source.hull_count=3;
    source.slabs=slabs; source.slab_count=2;
    /* Nonzero first indices distinguish first/count order. Two hull union,
     * with an oblique slab cutting the corner off the first box. */
    models[8]=8; u16(models+12,2); u16(models+14,1);
    for(unsigned i=1;i<3;++i) for(unsigned a=0;a<3;++a) f32(hulls+i*32+12+a*4,2);
    f32(hulls+64,10); u16(hulls+32+28,1); u16(hulls+32+30,1);
    hulls[32+24]=8; hulls[64+24]=16;
    f32(slabs+20,2); f32(slabs+24,2); f32(slabs+36,2);
    assert(CODOL_ReadTriggerModel(&source,1,&model));
    assert(model.contents==8 && model.hull_count==2 && model.mins[0]==-2 && model.maxs[0]==12);
    assert(model.hulls[0].plane_count==8 && model.hulls[1].plane_count==6);
    float inside[3]={0,0,0},cut[3]={1,1,0},boundary[3]={0.5f,0.5f,0},other[3]={10,0,0};
    assert(contains(&model.hulls[0],inside) && contains(&model.hulls[0],boundary));
    assert(!contains(&model.hulls[0],cut) && contains(&model.hulls[1],other));
    assert(fabsf(model.hulls[0].planes[7].normal[0]-0.70710678f)<0.00001f);
    codol_trigger_hull_t *saved=model.hulls;
    f32(slabs+20,0); f32(slabs+24,0);
    assert(!CODOL_ReadTriggerModel(&source,1,&model) && model.hulls==saved);
    f32(slabs+20,1); f32(slabs+36,-1);
    assert(!CODOL_ReadTriggerModel(&source,1,&model) && model.hulls==saved);
    f32(slabs+36,1); u16(hulls+32+30,2);
    assert(!CODOL_ReadTriggerModel(&source,1,&model) && model.hulls==saved);
    assert(!CODOL_ReadTriggerModel(&source,2,&model));
    memset(hulls,0,sizeof(hulls)); memset(slabs,0,sizeof(slabs));
    assert(contains(&model.hulls[0],boundary)); /* owns decoded geometry */
    CODOL_FreeTriggerModel(&model); CODOL_FreeTriggerModel(&model);
    puts("PASS: trigger model ranges, hull union bounds, oblique slab planes, ownership and atomic rejection");
}
