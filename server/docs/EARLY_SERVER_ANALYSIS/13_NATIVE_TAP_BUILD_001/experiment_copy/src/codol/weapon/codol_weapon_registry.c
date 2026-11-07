#include "codol_weapon_registry.h"
#include <stdlib.h>
#include <string.h>
struct weapon_record { char *name,*ammo,*clip; int ammo_key,clip_key; unsigned char deduplicate,no_clip; };
struct codol_weapon_registry_s {
    struct weapon_record weapons[1024];
    unsigned ammo_owners[1024],clip_owners[1023];
    unsigned count,ammo_count,clip_count;
};
static char *copy_name(const char *name)
{
    size_t n=strlen(name)+1; char *out=malloc(n);
    if(out) memcpy(out,name,n);
    return out;
}
codol_weapon_registry_t *CODOL_CreateWeaponRegistry(void)
{ return calloc(1,sizeof(codol_weapon_registry_t)); }
void CODOL_DestroyWeaponRegistry(codol_weapon_registry_t *r)
{
    unsigned i; if(!r) return;
    for(i=0;i<r->count;++i) { free(r->weapons[i].name); free(r->weapons[i].ammo); free(r->weapons[i].clip); }
    free(r);
}
int CODOL_GetWeaponKeys(const codol_weapon_registry_t *r,unsigned wire,int *ammo,int *clip)
{
    if(!r || wire>=r->count || !ammo || !clip) return 0;
    *ammo=r->weapons[wire].ammo_key; *clip=r->weapons[wire].clip_key; return 1;
}
int CODOL_FindRegisteredWeapon(const codol_weapon_registry_t *r,const char *name)
{
    unsigned i; if(!r || !name || !*name) return -1;
    for(i=0;i<r->count;++i) if(!strcmp(r->weapons[i].name,name)) return (int)i;
    return -1;
}
int CODOL_RegisteredWeaponKeyNames(const codol_weapon_registry_t *r,unsigned wire,const char **ammo,const char **clip,
    unsigned *deduplicate,unsigned *no_clip)
{
    if(!r || wire>=r->count) return 0;
    if(ammo) *ammo=r->weapons[wire].ammo;
    if(clip) *clip=r->weapons[wire].clip;
    if(deduplicate) *deduplicate=r->weapons[wire].deduplicate;
    if(no_clip) *no_clip=r->weapons[wire].no_clip;
    return 1;
}
int CODOL_RegisteredWeaponName(const codol_weapon_registry_t *r,unsigned wire,const char **out)
{
    if(!r || !out || wire>=r->count || !r->weapons[wire].name) return 0;
    *out=r->weapons[wire].name; return 1;
}
int CODOL_RegisterWeaponKeys(codol_weapon_registry_t *r,unsigned wire,const char *name,
    const char *ammo,const char *clip,unsigned deduplicate,unsigned no_clip,int base)
{
    struct weapon_record next={0}; unsigned i; int a=-1,c=-1;
    if(!r || wire!=r->count || wire>=1024 || !name || !*name || deduplicate>1 || no_clip>1 ||
       base< -1 || (base>=0 && (unsigned)base>=r->count) || ((name[0]=='*')!=(base>=0))) return 0;
    for(i=0;i<r->count;++i) if(!strcmp(name,r->weapons[i].name)) return 0;
    /* The linked asset's strings are compared verbatim, empty included.
     * dog_bite (gate set, ammo/clip both the zone's shared "" string,
     * common_gametype_mp +0x564/+0x56c = 0x3002f501) de-duplicates on the
     * client onto the first ""-named pool entry, so it takes no index:
     * live C1 pools read 137 clips / 115 ammo against this registry's
     * 138 / 116 and every composed magazine after wire 98 was keyed one
     * high (2026-09-16). Substituting the internal name for "" was the
     * raw weapon-file parser rule, which never runs for zone assets. */
    if(!ammo) ammo="";
    if(!clip) clip="";
    /* C1 41f200: optional name search precedes the custom-base branch. */
    if(deduplicate) for(i=0;i<r->ammo_count;++i)
        if(!strcmp(ammo,r->weapons[r->ammo_owners[i]].ammo)) { a=(int)i; break; }
    if(a<0 && base>=0) a=r->weapons[base].ammo_key;
    if(a<0) a=(int)r->ammo_count;
    /* C1 41f3f0 has no custom-base inheritance for magazines. */
    if(!no_clip) {
        if(deduplicate) for(i=0;i<r->clip_count;++i)
            if(!strcmp(clip,r->weapons[r->clip_owners[i]].clip)) { c=(int)i; break; }
        if(c<0) c=(int)r->clip_count;
    }
    if(a>1023 || c>1022) return 0;
    next.name=copy_name(name); next.ammo=copy_name(ammo); next.clip=copy_name(clip);
    if(!next.name || !next.ammo || !next.clip) { free(next.name);free(next.ammo);free(next.clip);return 0; }
    next.ammo_key=a; next.clip_key=c; next.deduplicate=(unsigned char)deduplicate; next.no_clip=(unsigned char)no_clip;
    r->weapons[wire]=next;
    if(a==(int)r->ammo_count) r->ammo_owners[r->ammo_count++]=wire;
    if(!no_clip && c==(int)r->clip_count) r->clip_owners[r->clip_count++]=wire;
    ++r->count; return 1;
}
