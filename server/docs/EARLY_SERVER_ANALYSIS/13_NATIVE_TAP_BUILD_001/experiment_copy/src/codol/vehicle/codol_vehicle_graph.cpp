/* C1 673d67..673dab: physics vehicles load vehicle/<VehicleDef+b4>.
 * 59db70 verifies GRAPH_FLOAT_FILE and passes remaining text to59d910.
 * 59d910 reads a declared pair count, then float pairs (32 maximum), and
 * requires the actual count to match. 673d87 supplies80.0f (C323B0) as graph
 * maximum acceleration; this is independent of VEHICLEFILE's accel setting.
 * No native controller activation and no synthesized fallback curve.
 */
#ifdef CODOL_SERVER
#include "codol_vehicle_graph.h"
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct graph_reader { const char *p,*end; };
static int token(graph_reader *r,char out[96])
{
    for(;;) {
        while(r->p<r->end && isspace((unsigned char)*r->p))++r->p;
        if(r->p==r->end)return 0;
        if(r->end-r->p>=2 && r->p[0]=='/' && r->p[1]=='/') {
            while(r->p<r->end && *r->p!='\n')++r->p;
        } else if(r->end-r->p>=2 && r->p[0]=='/' && r->p[1]=='*') {
            r->p+=2;
            while(r->end-r->p>=2 && !(r->p[0]=='*' && r->p[1]=='/'))++r->p;
            if(r->end-r->p<2)return -1;
            r->p+=2;
        } else break;
    }
    if(*r->p=='}'){out[0]=*r->p++;out[1]=0;return 1;}
    unsigned n=0;
    while(r->p<r->end && !isspace((unsigned char)*r->p) && *r->p!='}') {
        unsigned char c=(unsigned char)*r->p++;
        if(c<33 || c=='"' || c==';' || n==95)return -1;
        out[n++]=(char)c;
    }
    out[n]=0;return n ? 1 : -1;
}
static int scalar(graph_reader *r,float *out)
{
    char value[96],*end;
    if(token(r,value)!=1)return 0;
    errno=0;float x=strtof(value,&end);
    if(errno || end==value || *end || !isfinite(x))return 0;
    *out=x;return 1;
}
int CODOL_ParseVehicleAccelerationGraph(const char *bytes,size_t size,
                                       codol_vehicle_acceleration_t *out)
{
    static const char magic[]="GRAPH_FLOAT_FILE";
    if(!bytes || !out || size<sizeof(magic)-1 || size>8192)return -1;
    if(size && !bytes[size-1])--size;
    if(memchr(bytes,0,size) || memcmp(bytes,magic,sizeof(magic)-1))return -1;
    graph_reader r={bytes+sizeof(magic)-1,bytes+size};char text[96],*end;
    if(token(&r,text)!=1)return -1;
    errno=0;long count=strtol(text,&end,10);
    if(errno || end==text || *end || count<2 || count>CODOL_VEHICLE_ACCEL_KNOTS)return -1;
    codol_vehicle_acceleration_t result={};result.count=(unsigned)count;
    result.maximum_acceleration=80.0f;
    for(unsigned i=0;i<result.count;++i) {
        codol_vehicle_accel_knot_t *k=&result.knots[i];
        if(!scalar(&r,&k->speed_fraction) || !scalar(&r,&k->acceleration_fraction) ||
           k->speed_fraction<0 || k->speed_fraction>1 || k->acceleration_fraction<0 ||
           (i && k->speed_fraction<=result.knots[i-1].speed_fraction))return -1;
    }
    int more=token(&r,text);
    if(more<0 || (more && (strcmp(text,"}") || token(&r,text)!=0)))return -1;
    if(result.knots[0].speed_fraction!=0 || result.knots[result.count-1].speed_fraction!=1)return -1;
    *out=result;return 1;
}
int CODOL_LoadVehicleAccelerationGraph(const codol_vehicle_raw_t *definition,
                                      codol_vehicle_acceleration_t *out)
{
    if(!definition || !out)return -1;
    const char *name=definition->common.physics_profile;
    if(!*name || strchr(name,'/') || strchr(name,'\\') || strstr(name,".."))return -1;
    char path[128];
    if(snprintf(path,sizeof(path),"vehicle/%s",name)>=(int)sizeof(path))return -1;
    const codol_engine_rawfile_t *raw=NULL;
    int status=CODOL_LoadEngineRawFile(path,&raw);
    if(status!=1)return status;
    if(!raw || !raw->buffer || raw->len<0)return -1;
    return CODOL_ParseVehicleAccelerationGraph(raw->buffer,(size_t)raw->len,out);
}
#endif
