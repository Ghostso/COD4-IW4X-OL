#include "codol_map_custom.h"
#include <string.h>
typedef struct {const char *data;size_t size,pos;} reader_t;
static int equal(const char *a,const char *b)
{
    for(;;++a,++b) {
        unsigned x=(unsigned char)*a,y=(unsigned char)*b;
        if(x>='A' && x<='Z')x+=32;if(y>='A' && y<='Z')y+=32;
        if(x!=y)return 0;if(!x)return 1;
    }
}
/* Tokens retain braces separately even without surrounding whitespace.
 * Comments are ignored only outside quoted strings. */
static int token(reader_t *r,char *out,size_t cap)
{
    size_t n=0;int quoted;
    for(;;) {
        while(r->pos<r->size && (unsigned char)r->data[r->pos]<=32)++r->pos;
        if(r->pos==r->size)return 0;
        if(r->pos+1<r->size && r->data[r->pos]=='/' && r->data[r->pos+1]=='/') {
            r->pos+=2;while(r->pos<r->size && r->data[r->pos]!='\n')++r->pos;continue;
        }
        if(r->pos+1<r->size && r->data[r->pos]=='/' && r->data[r->pos+1]=='*') {
            r->pos+=2;
            while(r->pos+1<r->size && !(r->data[r->pos]=='*' && r->data[r->pos+1]=='/'))++r->pos;
            if(r->pos+1>=r->size)return -1;r->pos+=2;continue;
        }
        break;
    }
    if(r->data[r->pos]=='{' || r->data[r->pos]=='}'){out[0]=r->data[r->pos++];out[1]=0;return 1;}
    quoted=r->data[r->pos]=='"';if(quoted)++r->pos;
    while(r->pos<r->size) {
        char c=r->data[r->pos];
        if(quoted && c=='"'){++r->pos;out[n]=0;return 1;}
        if(!quoted && ((unsigned char)c<=32 || c=='{' || c=='}'))break;
        if(n+1>=cap)return -1;out[n++]=c;++r->pos;
    }
    if(quoted)return -1;out[n]=0;return 1;
}
int CODOL_MapCustom(const char *data,size_t size,const char *map,const char *key,char *out,size_t capacity)
{
    reader_t r={data,size,0};char k[1024],v[1024],map_name[1024],candidate[1024],result[1024];
    int status,found=0;
    if(!data || size>16*1024*1024 || memchr(data,0,size) || !map || !key || !out || !capacity)return -1;
    while((status=token(&r,k,sizeof(k)))==1) {
        int have=0;map_name[0]=0;
        if(strcmp(k,"{"))return -1;
        for(;;) {
            if(token(&r,k,sizeof(k))!=1)return -1;
            if(!strcmp(k,"}"))break;
            if(!strcmp(k,"{") || token(&r,v,sizeof(v))!=1 || !strcmp(v,"{") || !strcmp(v,"}"))return -1;
            if(equal(k,"map"))strcpy(map_name,v);
            if(equal(k,key)){strcpy(candidate,v);have=1;}
        }
        if(!found && equal(map_name,map) && have){strcpy(result,candidate);found=1;}
    }
    if(status<0)return -1;
    if(found){size_t n=strlen(result);if(n>=capacity)return -1;memcpy(out,result,n+1);}
    return found;
}
