#include "codol_collision.h"
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
void CODOL_FreeCollisionMaterials(codol_collision_materials_t *m)
{
    if (!m) return;
    free(m->materials); free(m->name_references); memset(m,0,sizeof(*m));
}
int CODOL_ReadCollisionMaterials(const codol_asset_t *asset,codol_collision_name_resolver_t resolver,
                                 void *context,codol_collision_materials_t *out)
{
    codol_collision_layout_t layout;
    codol_collision_materials_t m={0};
    const codol_collision_span_t *s;
    size_t p;
    uint32_t i;
    if (!out || !CODOL_ReadCollisionLayout(asset,&layout)) return 0;
    s=layout.sections+CODOL_COLL_MATERIALS; m.count=s->count;
    p=s->offset+(size_t)m.count*12;
    if (m.count) {
        m.materials=calloc(m.count,sizeof(*m.materials));
        m.name_references=calloc(m.count,sizeof(*m.name_references));
        if (!m.materials || !m.name_references) goto fail;
    }
    for (i=0;i<m.count;++i) {
        const uint8_t *record=asset->data+s->offset+12*i;
        uint32_t ref=u32(record),flags=u32(record+4),contents=u32(record+8);
        const char *name=NULL;
        size_t length=0;
        memcpy(&m.materials[i].surfaceFlags,&flags,4);
        memcpy(&m.materials[i].contentFlags,&contents,4);
        if (ref==UINT32_MAX) {
            const uint8_t *end=memchr(asset->data+p,0,asset->size-p);
            if (!end) goto fail;
            name=(const char *)(asset->data+p); p=(size_t)(end-asset->data)+1;
        } else {
            if (!ref || ref==UINT32_MAX-1) goto fail;
            if (resolver) name=resolver(context,ref);
            if (!name) { m.name_references[i]=ref; ++m.unresolved; continue; }
        }
        while (length<sizeof(m.materials[i].material) && name[length]) ++length;
        if (!length || length==sizeof(m.materials[i].material)) goto fail;
        memcpy(m.materials[i].material,name,length+1);
    }
    *out=m; return 1;
fail:
    CODOL_FreeCollisionMaterials(&m); return 0;
}
