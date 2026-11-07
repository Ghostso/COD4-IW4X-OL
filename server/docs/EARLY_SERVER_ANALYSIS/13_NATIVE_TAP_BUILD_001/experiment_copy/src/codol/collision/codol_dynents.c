#include "codol_dynents.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static unsigned u16(const uint8_t *p) { return p[0]|(unsigned)p[1]<<8; }
static int floats(float *out,const uint8_t *p,unsigned count)
{
    unsigned i;
    for(i=0;i<count;++i) {
        uint32_t bits=u32(p+4*i); memcpy(out+i,&bits,4);
        if(!isfinite(out[i])) return 0;
    }
    return 1;
}
void CODOL_FreeDynamicEntities(codol_dynamic_entities_t *out)
{
    if(!out) return;
    free(out->entities[0]); free(out->entities[1]); memset(out,0,sizeof(*out));
}
int CODOL_ReadDynamicEntities(const codol_asset_t *collision,const codol_load_blocks_t *blocks,
    codol_dynamic_entities_t *out)
{
    codol_dynamic_entities_t result={0}; unsigned category,i;
    if(!collision || !blocks || !out || !collision->data || collision->size<256 ||
        (collision->type!=14 && collision->type!=15)) return 0;
    for(category=0;category<2;++category) {
        codol_dynamic_records_t records;
        result.count[category]=u16(collision->data+168+2*category);
        if(!result.count[category]) continue;
        if(!CODOL_ResolveDynamicRecords(blocks,collision,category,&records) ||
            records.count!=result.count[category] || !records.reference ||
            ((records.reference-1)>>28)!=3 ||
            (uint64_t)records.reference+(uint64_t)records.count*92>0x40000000u) goto fail;
        result.entities[category]=calloc(records.count,sizeof(*result.entities[category]));
        if(!result.entities[category]) goto fail;
        for(i=0;i<records.count;++i) {
            const uint8_t *p=records.records+92*i; uint32_t health=u32(p+48);
            codol_dynamic_entity_t *e=result.entities[category]+i;
            e->type=u32(p); e->model_reference=u32(p+32);
            e->brush_model=u16(p+36); e->physics_brush_model=u16(p+38);
            e->effect_reference=u32(p+40); e->preset_reference=u32(p+44);
            memcpy(&e->health,&health,4); e->contents=u32(p+88);
            if(!floats(e->quat,p+4,4) || !floats(e->origin,p+20,3) || !floats(e->mass,p+52,9)) goto fail;
            e->model_slot=records.reference+92*i+32;
            e->effect_slot=records.reference+92*i+40;
            e->preset_slot=records.reference+92*i+44;
        }
    }
    CODOL_FreeDynamicEntities(out); *out=result; return 1;
fail:
    CODOL_FreeDynamicEntities(&result); return 0;
}
