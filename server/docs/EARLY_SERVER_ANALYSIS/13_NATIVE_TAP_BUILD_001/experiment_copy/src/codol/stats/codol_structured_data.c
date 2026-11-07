#include "codol_structured_data.h"
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static int locate(const codol_structured_layout_t *layout,unsigned type,unsigned property,
                  size_t capacity,size_t *offset,unsigned *bit)
{
    uint32_t address; size_t width;
    if(!layout || !layout->offset_map || layout->offset_map_size%4 ||
       property>=layout->offset_map_size/4 || capacity<layout->record_size ||
       (type>2 && type!=8 && type!=9)) return 0;
    address=word(layout->offset_map+(size_t)property*4);
    *bit=type==2 ? address&7 : 0;
    *offset=type==2 ? address>>3 : address;
    width=type==0 || type==8 ? 4 : type==9 ? 2 : 1;
    return *offset<=layout->record_size && width<=layout->record_size-*offset;
}
int CODOL_StructuredReadScalar(const codol_structured_layout_t *layout,unsigned type,
    unsigned property,const uint8_t *record,size_t capacity,uint32_t *out)
{
    size_t offset; unsigned bit; uint32_t value;
    if(!record || !out || !locate(layout,type,property,capacity,&offset,&bit)) return 0;
    value=type==0 || type==8 ? word(record+offset) :
        type==9 ? (uint32_t)record[offset]|(uint32_t)record[offset+1]<<8 :
        type==1 ? record[offset] : (record[offset]>>bit)&1;
    *out=value; return 1;
}
int CODOL_StructuredWriteScalar(const codol_structured_layout_t *layout,unsigned type,
    unsigned property,uint8_t *record,size_t capacity,uint32_t value)
{
    size_t offset; unsigned bit,i;
    if(!record || (type==1 && value>255) || (type==2 && value>1) ||
       !locate(layout,type,property,capacity,&offset,&bit)) return 0;
    if(type==0 || type==8 || type==9)
        for(i=0;i<(type==9 ? 2u : 4u);++i) record[offset+i]=(uint8_t)(value>>(i*8));
    else if(type==1) record[offset]=(uint8_t)value;
    else record[offset]=(uint8_t)((record[offset]&~(1u<<bit))|(value<<bit));
    return 1;
}
