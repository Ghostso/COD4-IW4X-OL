#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "cscr_variable.h"
#include "codol_stats.h"
#include "codol_assets.h"
#include "codol_script_profile_vm.h"
#include "codol_script_profile_loadout.h"
#include <stdio.h>
#include <string.h>

/* Exported by the retained VM; this is its current stack, not the saved
 * caller frame. Native builtin dispatch keeps localId at gFs+4. */
extern struct function_stack_t gFs;

static int class_space(unsigned char c)
{ return c==' ' || (c>='\t' && c<='\r'); }
void CODOL_Scr_GetClassIndex(void)
{
    const char *text=Scr_GetString(0),*end,*digits=NULL;
    const char *prefixes[]={"custom","class"}; unsigned p,i,value=0;
    while(class_space((unsigned char)*text)) ++text;
    end=text+strlen(text);
    while(end>text && class_space((unsigned char)end[-1])) --end;
    for(p=0;p<2;++p) {
        const char *prefix=prefixes[p]; size_t n=strlen(prefix);
        if((size_t)(end-text)<=n) continue;
        for(i=0;i<n;++i) {
            unsigned char c=text[i]; if(c>='A' && c<='Z') c+='a'-'A';
            if(c!=(unsigned char)prefix[i]) break;
        }
        if(i==n) { digits=text+n; break; }
    }
    if(!digits) { Scr_AddInt(-1); return; }
    for(;digits<end;++digits) {
        unsigned digit=(unsigned char)*digits-'0';
        /* Python integers are unbounded; native GSC results must fit signed
         * 32 bits. Permit N=2147483648 because the returned index is N-1. */
        if(digit>9 || value>(UINT32_C(2147483648)-digit)/10) { Scr_AddInt(-1); return; }
        value=value*10+digit;
    }
    Scr_AddInt(value ? (int)(value-1) : -1);
}

void CODOL_Scr_GetClassPerk(void)
{
    unsigned self; scr_entref_t ref; int item,status,ci=Scr_GetInt(0),slot=Scr_GetInt(1);
    const char *name=NULL,*type=NULL;
    if(ci<0 || ci>=8 || slot<1 || slot>5) {
        Scr_Error("getClassPerk: class must be 0..7 and slot 1..5"); return;
    }
    if(!gFs.localId) { Scr_Error("getClassPerk requires a player script thread"); return; }
    self=Scr_GetSelf(gFs.localId);
    if(!self || Scr_GetObjectType(self)!=VAR_ENTITY) {
        Scr_Error("getClassPerk requires a player script self"); return;
    }
    ref=Scr_GetEntityIdRef(self);
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client ||
       !g_entities[ref.entnum].r.inuse) {
        Scr_Error("getClassPerk requires a player entity"); return;
    }
    {
        const codol_structured_definition_t *definition;
        const uint8_t *record; size_t capacity; uint32_t raw;
        codol_structured_field_t field;
        codol_structured_path_t path[]={
            {"weaponClasses",0},{NULL,ci},{"perks",0},{NULL,slot-1}
        };
        /* Resolve against the uploaded profile's mounted definition, rather
         * than embedding one export's class stride and absolute byte offset.
         * The shared view also observes accepted GSC session writes. */
        if(!CODOL_ScriptProfileView(ref.entnum,CODOL_PROFILE_PUBLIC,
                &definition,&record,&capacity) ||
           !CODOL_ResolveStructuredField(definition,path,4,&field) ||
           field.type.kind!=9 ||
           !CODOL_StructuredReadScalar(&definition->layout,field.type.kind,
                field.logical_index,record,capacity,&raw)) {
            Scr_Error("getClassPerk: missing profile or invalid mounted perk field"); return;
        }
        raw &= 0xffffu;
        item=raw>=0x8000u ? (int)raw-0x10000 : (int)raw;
    }
    if(item<=0) { Scr_AddString(""); return; }
    /* Share the marketplace's last-ID-row resolution with the loadout bridge.
     * Reject a winning non-perk row rather than selecting an older perk row. */
    status=CODOL_LoadoutItemName(item,&name,&type,NULL);
    if(status<0) {
        Scr_Error("getClassPerk: marketplace item table is unavailable"); return;
    }
    if(status!=1) { Scr_Error("getClassPerk: profile perk item is absent from marketplace"); return; }
    if(!type || strcmp(type,"per")) { Scr_Error("getClassPerk: profile item is not a perk"); return; }
    Scr_AddString(name);
}
#endif
