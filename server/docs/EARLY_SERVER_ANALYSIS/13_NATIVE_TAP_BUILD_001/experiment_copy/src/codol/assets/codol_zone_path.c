#include "codol_zone_path.h"
#include <stdio.h>
#include <string.h>
static int token(const char *s)
{
    if(!s || !*s) return 0;
    for(;*s;++s) if(!((*s>='a' && *s<='z') || (*s>='A' && *s<='Z') ||
        (*s>='0' && *s<='9') || *s=='_' || *s=='-')) return 0;
    return 1;
}
int CODOL_ZoneFilePath(const char *base,const char *language,const char *directory,
                       const char *name,char *out,size_t capacity)
{
    char path[1024]; int n;
    if(!out || !token(name)) return 0;
    if(directory && *directory) n=snprintf(path,sizeof(path),"%s/%s.ff",directory,name);
    else {
        if(!base || !*base || !token(language)) return 0;
        n=snprintf(path,sizeof(path),"%s/client_shipRetail/%s/%s.ff",base,language,name);
    }
    if(n<0 || (size_t)n>=sizeof(path) || (size_t)n>=capacity) return 0;
    memcpy(out,path,(size_t)n+1); return 1;
}
