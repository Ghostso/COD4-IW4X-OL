#include "codol_collision_native.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <limits.h>
int CODOL_AppendNativeTriggers(const codol_map_entities_t *source,codol_native_clip_map_t *out)
{
    codol_trigger_model_t *models=NULL;
    codol_native_brushes_t *old,b;
    cmodel_t *submodels=NULL; cNode_t *nodes=NULL;
    unsigned hulls=0,planes=0,hi=0,pi=0;
    if(!source || !out || out->trigger_model_count) return 0;
    old=&out->brushes; b=*old;
    if(!source->model_count) return 1;
    if(source->model_count>=1023 || out->leaves.model_count>1023-source->model_count ||
       !old->brush_node_count || !old->index_count) return 0;
    models=calloc(source->model_count,sizeof(*models)); if(!models) return 0;
    b.planes=NULL; b.sides=NULL; b.brush_storage=NULL; b.brush_nodes=NULL; b.indices=NULL;
    for(unsigned i=0;i<source->model_count;++i) {
        if(!CODOL_ReadTriggerModel(source,i,models+i) || models[i].hull_count>SHRT_MAX) goto fail;
        hulls+=models[i].hull_count;
        if(hulls>65535-old->brush_count) goto fail;
        for(unsigned j=0;j<models[i].hull_count;++j) {
            unsigned n=models[i].hulls[j].plane_count;
            if(n>1000000-planes) goto fail;
            planes+=n;
        }
    }
    b.plane_count+=planes; b.side_count+=planes; b.brush_count+=hulls;
    b.brush_node_count+=source->model_count; b.index_count+=hulls;
    b.planes=calloc(b.plane_count,sizeof(*b.planes)); b.sides=calloc(b.side_count,sizeof(*b.sides));
    b.brush_storage=calloc(1,(size_t)(b.brush_count+1)*sizeof(*b.brushes)+15);
    b.brush_nodes=calloc(b.brush_node_count,sizeof(*b.brush_nodes)); b.indices=calloc(b.index_count,sizeof(*b.indices));
    nodes=calloc(old->node_count ? old->node_count : 1,sizeof(*nodes));
    submodels=calloc(out->leaves.model_count+source->model_count,sizeof(*submodels));
    if(!b.planes || !b.sides || !b.brush_storage || !b.brush_nodes || !b.indices || !nodes || !submodels) goto fail;
    b.brushes=(cbrush_t *)(((uintptr_t)b.brush_storage+15)&~(uintptr_t)15);
    memcpy(b.planes,old->planes,old->plane_count*sizeof(*b.planes));
    memcpy(b.sides,old->sides,old->side_count*sizeof(*b.sides));
    memcpy(b.brushes,old->brushes,old->brush_count*sizeof(*b.brushes));
    memcpy(b.brush_nodes,old->brush_nodes,old->brush_node_count*sizeof(*b.brush_nodes));
    memcpy(b.indices,old->indices,old->index_count*sizeof(*b.indices));
    memcpy(nodes,old->nodes,old->node_count*sizeof(*nodes));
    memcpy(submodels,out->leaves.models,out->leaves.model_count*sizeof(*submodels));
    for(unsigned i=0;i<old->node_count;++i) nodes[i].plane=b.planes+(old->nodes[i].plane-old->planes);
    for(unsigned i=0;i<old->side_count;++i) b.sides[i].plane=b.planes+(old->sides[i].plane-old->planes);
    for(unsigned i=0;i<old->brush_count;++i) if(old->brushes[i].numsides)
        b.brushes[i].sides=b.sides+(old->brushes[i].sides-old->sides);
    for(unsigned i=0;i<old->brush_node_count;++i) if(old->brush_nodes[i].leafBrushCount>0)
        b.brush_nodes[i].data.leaf.brushes=b.indices+(old->brush_nodes[i].data.leaf.brushes-old->indices);
    /* Move the reserved box brush; its original node/index retain their IDs. */
    b.brushes[b.brush_count]=old->brushes[old->brush_count];
    b.indices[old->index_count-1]=(uint16_t)b.brush_count;
    for(unsigned i=0;i<source->model_count;++i) {
        codol_trigger_model_t *m=models+i; cmodel_t *dst=submodels+out->leaves.model_count+i;
        cLeafBrushNode_t *node=b.brush_nodes+old->brush_node_count+i;
        memcpy(dst->mins,m->mins,12); memcpy(dst->maxs,m->maxs,12);
        memcpy(dst->leaf.mins,m->mins,12); memcpy(dst->leaf.maxs,m->maxs,12);
        double radius=0; for(unsigned a=0;a<3;++a) { double v=fmax(fabs(m->mins[a]),fabs(m->maxs[a])); radius+=v*v; }
        dst->radius=(float)sqrt(radius); if(!isfinite(dst->radius)) goto fail;
        dst->leaf.brushContents=m->contents; dst->leaf.cluster=-1;
        dst->leaf.leafBrushNode=old->brush_node_count+i;
        node->contents=m->contents; node->leafBrushCount=m->hull_count;
        node->data.leaf.brushes=b.indices+old->index_count+hi;
        for(unsigned j=0;j<m->hull_count;++j,++hi) {
            codol_trigger_hull_t *h=m->hulls+j; cbrush_t *brush=b.brushes+old->brush_count+hi;
            memcpy(brush->mins,h->mins,12); memcpy(brush->maxs,h->maxs,12);
            brush->contents=h->contents; brush->numsides=h->plane_count;
            brush->sides=b.sides+old->side_count+pi;
            b.indices[old->index_count+hi]=old->brush_count+hi;
            for(unsigned k=0;k<h->plane_count;++k,++pi) {
                cplane_t *p=b.planes+old->plane_count+pi;
                memcpy(p->normal,h->planes[k].normal,12); p->dist=h->planes[k].distance; p->type=3;
                for(unsigned a=0;a<3;++a) { if(p->normal[a]<0) p->signbits|=1u<<a; if(p->normal[a]==1) p->type=a; }
                b.sides[old->side_count+pi].plane=p;
            }
        }
    }
    free(old->planes); free(old->sides); free(old->brush_storage); free(old->brush_nodes); free(old->indices); free(old->nodes);
    free(out->leaves.models); b.nodes=nodes; *old=b; out->leaves.models=submodels;
    out->trigger_model_base=out->leaves.model_count; out->trigger_model_count=source->model_count;
    out->leaves.model_count+=source->model_count;
    for(unsigned i=0;i<source->model_count;++i) CODOL_FreeTriggerModel(models+i);
    free(models); return 1;
fail:
    free(b.planes); free(b.sides); free(b.brush_storage); free(b.brush_nodes); free(b.indices); free(nodes); free(submodels);
    for(unsigned i=0;i<source->model_count;++i) CODOL_FreeTriggerModel(models+i);
    free(models); return 0;
}
