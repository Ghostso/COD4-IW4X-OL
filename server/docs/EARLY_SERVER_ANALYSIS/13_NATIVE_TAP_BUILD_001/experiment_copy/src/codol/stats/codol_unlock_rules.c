#include "codol_unlock_rules.h"
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
static int space(unsigned char c){return c==' ' || (c>='\t' && c<='\r');}
int CODOL_EvaluateUnlockRule(const char *item,const char *category,const char *rank,
    const char *requirements,codol_unlock_read_t read,void *context,int *unlocked)
{
    int value,override_unknown=0;const char *p;
    if(!item || !category || !rank || !requirements || !read || !unlocked)return 0;
    if(!strcmp(category,"title") || !strcmp(category,"icon")) {
        if(!read(context,!strcmp(category,"title") ? "titleUnlocked" : "iconUnlocked",item,&value))override_unknown=1;
        else if(value){*unlocked=1;return 1;}
    }
    if(*rank) {
        long threshold;
        errno=0;threshold=strtol(rank,NULL,10);
        if(errno==ERANGE || threshold<INT_MIN || threshold>INT_MAX)return 0;
        if(!read(context,"experienceRank","",&value))return 0;
        if(value<threshold){if(override_unknown)return 0;*unlocked=0;return 1;}
    }
    p=requirements;
    while(*p) {
        const char *start;size_t n;char name[64];int stage=1;
        while(*p==';' || space((unsigned char)*p))++p;
        start=p;
        while(*p && *p!=';' && !space((unsigned char)*p))++p;
        n=(size_t)(p-start);if(!n)break;
        /* IW4 0x40d762 bounds the token copy to 64 bytes including NUL. */
        if(n>63)n=63;
        memcpy(name,start,n);name[n]=0;
        if(n>2 && name[n-2]=='_' && name[n-1]>='0' && name[n-1]<='9') {
            stage=name[n-1]-'0';name[n-2]=0;
        }
        if(!read(context,"challengeState",name,&value))return 0;
        if(value<=stage){if(override_unknown)return 0;*unlocked=0;return 1;}
    }
    *unlocked=1;return 1;
}
