/* CoDOL publication of retained engine asset names. */
#ifdef CODOL_SERVER
#include "codol_script_player_builtins.h"
#include "server.h"
#include "g_shared.h"
#include "scr_vm.h"
#include "codol_sv_state.h"
#include "codol_engine_state.h"
#include "codol_sv_weapons.h"
#include "codol_clientstate_ext.h"
#include "codol_weapon_state.h"
#include "codol_weapon_flags.h"
#include "codol_remote_vehicle.h"
#include "cscr_stringlist.h"
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
/* codol_script_hud_notifications.c: the ACTION_SLOT_HELP store. */
unsigned CODOL_ClientActionSlotHelp(unsigned client);
int CODOL_PublishServerId(int32_t server_id)
{
    char value[16]; int i;
    const char *old = CODOL_GetConfigstring(CODOL_ServerConfigstrings(), CODOL_CS_SERVER_ID);
    snprintf(value, sizeof(value), "%d", (int)server_id);
    if(old && !strcmp(old, value)) return 1;
    if(!CODOL_SetServerId(server_id)) return 0;
    if(!svs.clients || !sv_maxclients) return 1;
    for(i = 0; i < sv_maxclients->integer; ++i)
        if(svs.clients[i].state >= CS_PRIMED && svs.clients[i].gamestateSent)
            SV_SendServerCommandNoLoss(&svs.clients[i], "d %u %s", CODOL_CS_SERVER_ID, value);
    return 1;
}
_Static_assert(MAX_SOUNDS<=CODOL_SOUND_SLOTS,"native sound IDs fit the CoDOL sound bank");

void CODOL_BroadcastWeaponConfigstrings(unsigned first,unsigned count)
{
    unsigned i; int recipient;
    if(first>=CODOL_WEAPON_SLOTS || count>CODOL_WEAPON_SLOTS-first) return;
    for(i=first;i<first+count;++i) {
        const char *name=CODOL_GetConfigstring(CODOL_ServerConfigstrings(),CODOL_CS_WEAPONS+i);
        if(!name || !*name) continue;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_WEAPONS+i,name);
        }
    }
    /* This reliable command must follow every newly appended definition:
     * the C1 registration loop dereferences all slots below the new count. */
    if(count) {
        const char *total=CODOL_GetConfigstring(CODOL_ServerConfigstrings(),CODOL_CS_WEAPON_COUNT);
        if(total && *total) for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_WEAPON_COUNT,total);
        }
    }

}

static unsigned codol_model_strings[MAX_MODELS], codol_tag_strings[MAX_TAGS];
static int codol_model_slots[CODOL_NATIVE_MODELS], codol_tag_slots[MAX_TAGS];
/* Native model slots MAX_MODELS..CODOL_NATIVE_MODELS-1: referenced script
 * strings, the IW3 configstring's role for the lower slots. */
static unsigned codol_high_model_names[CODOL_NATIVE_MODELS-MAX_MODELS];
static unsigned codol_material_strings[MAX_MATERIALS],codol_localized_strings[MAX_LOCALIZEDSTRINGS];
static int codol_material_slots[MAX_MATERIALS],codol_localized_slots[MAX_LOCALIZEDSTRINGS];
/* Retained G_EffectIndex uses base0x63e and100 slots; C1 has320 slots. */
static unsigned codol_effect_strings[100];
static int codol_effect_slots[CODOL_EFFECT_SLOTS];
static int codol_byte_effect_slots[CODOL_EFFECT_SLOTS];
/* Extra native slots cannot live at CS_FX+index: slot100 overlaps the
 * retained tagged-effect range. Their names belong to this map's registry. */
static char codol_extra_effect_names[CODOL_EFFECT_SLOTS-100][64];
static int codol_tagged_effect_slots[256];
static struct { unsigned tagged_slot; uint32_t audience; } codol_masked_tagged_effects[256];
static int codol_weapon_map_warned;
/* Hint string slots 32..95 (see CODOL_G_GetHintStringIndex). */
static char codol_high_hints[CODOL_HINTSTRING_SLOTS-CODOL_HINTSTRING_RETAINED][MAX_STRING_CHARS];
extern struct XModel *cached_models[CODOL_NATIVE_MODELS];
struct XModel *__cdecl SV_XModelGet(const char *name);
unsigned int __cdecl SV_GetConfigstringConst(int index);
void CODOL_ResetServerAssetNames(void)
{
    unsigned model;
    for(model=0;model<CODOL_NATIVE_MODELS-MAX_MODELS;++model) {
        if(codol_high_model_names[model]) SL_RemoveRefToString(codol_high_model_names[model]);
        codol_high_model_names[model]=0;
        cached_models[MAX_MODELS+model]=NULL;
    }
    memset(codol_high_hints, 0, sizeof(codol_high_hints));
    codol_weapon_map_warned = 0;
    memset(codol_model_strings, 0, sizeof(codol_model_strings));
    memset(codol_tag_strings, 0, sizeof(codol_tag_strings));
    memset(codol_model_slots, 0, sizeof(codol_model_slots));
    memset(codol_tag_slots, 0, sizeof(codol_tag_slots));
    memset(codol_material_strings,0,sizeof(codol_material_strings));
    memset(codol_localized_strings,0,sizeof(codol_localized_strings));
    memset(codol_material_slots,0,sizeof(codol_material_slots));
    memset(codol_localized_slots,0,sizeof(codol_localized_slots));
    memset(codol_effect_strings,0,sizeof(codol_effect_strings));
    memset(codol_extra_effect_names,0,sizeof(codol_extra_effect_names));
    memset(codol_effect_slots,0,sizeof(codol_effect_slots));
    memset(codol_byte_effect_slots,0,sizeof(codol_byte_effect_slots));
    memset(codol_tagged_effect_slots,0,sizeof(codol_tagged_effect_slots));
    memset(codol_masked_tagged_effects,0,sizeof(codol_masked_tagged_effects));
}
int CODOL_ServerModelToWire(unsigned index)
{ return index < CODOL_NATIVE_MODELS && (!index || codol_model_slots[index]) ? codol_model_slots[index] : -1; }
/* G_ModelName for every native slot: the IW3 configstring below MAX_MODELS,
 * the CoDOL table above it, the empty string for a free slot. */
unsigned CODOL_G_ModelName(int index)
{
    if(index>=0 && index<MAX_MODELS) return SV_GetConfigstringConst(CS_MODELS+index);
    if(index>=MAX_MODELS && index<CODOL_NATIVE_MODELS && codol_high_model_names[index-MAX_MODELS])
        return codol_high_model_names[index-MAX_MODELS];
    return sv.emptyConfigString;
}
/* The native slot >= MAX_MODELS already holding this lowercase script
 * string, or 0. */
int CODOL_FindHighModel(unsigned handle)
{
    unsigned index;
    if(!handle || handle==sv.emptyConfigString) return 0;
    for(index=0;index<CODOL_NATIVE_MODELS-MAX_MODELS;++index)
        if(codol_high_model_names[index]==handle) return (int)(MAX_MODELS+index);
    return 0;
}
/* Allocate a native slot >= MAX_MODELS once the IW3 slots are full, with
 * G_ModelIndex's stores (cached XModel first, then the name) and the wire
 * registration CODOL_RefreshAssetRange performs for the lower slots. 0 when
 * C1's 2048 are exhausted or the name cannot be published; nothing is left
 * half registered. */
int CODOL_AllocHighModel(const char *name)
{
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    unsigned index,handle;
    const char *p;
    int slot,recipient;
    struct XModel *model;
    if(!name || !*name || strlen(name)>=64 || !bank || !inherited) return 0;
    handle=SL_FindLowercaseString(name);
    if((slot=CODOL_FindHighModel(handle))>0) return slot;
    for(p=name;*p;++p)
        if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') return 0;
    for(index=0;index<CODOL_NATIVE_MODELS-MAX_MODELS;++index)
        if(!codol_high_model_names[index]) break;
    if(index>=CODOL_NATIVE_MODELS-MAX_MODELS) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL models: all %d native model slots are in use; '%s' refused\n",
            CODOL_NATIVE_MODELS-1,name);
        return 0;
    }
    model=SV_XModelGet(name);
    if(!model) return 0;
    slot=CODOL_RegisterInheritedModelName(bank,inherited,name);
    if(slot<1) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL models: C1 model bank cannot take '%s'\n",name);
        return 0;
    }
    cached_models[MAX_MODELS+index]=model;
    codol_high_model_names[index]=SL_GetLowercaseString(name,0);
    codol_model_slots[MAX_MODELS+index]=slot;
    if(svs.clients && sv_maxclients)
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_MODELS+(unsigned)slot,name);
        }
    return (int)(MAX_MODELS+index);
}
int CODOL_ServerTagToWire(unsigned index)
{ return index < MAX_TAGS && (!index || codol_tag_slots[index]) ? codol_tag_slots[index] : -1; }
int CODOL_ServerMaterialToWire(unsigned index)
{ return index<MAX_MATERIALS && (!index || codol_material_slots[index]) ? codol_material_slots[index] : -1; }
int CODOL_ServerLocalizedToWire(unsigned index)
{ return index<MAX_LOCALIZEDSTRINGS && (!index || codol_localized_slots[index]) ? codol_localized_slots[index] : -1; }
int CODOL_ServerEffectToWire(unsigned index)
{ return index<CODOL_EFFECT_SLOTS && (!index || codol_effect_slots[index]) ? codol_effect_slots[index] : -1; }
int CODOL_ServerByteEffectToWire(unsigned index)
{ return index<CODOL_EFFECT_SLOTS && (!index || codol_byte_effect_slots[index]>0) ? codol_byte_effect_slots[index] : -1; }
int CODOL_ServerTaggedEffectToWire(unsigned index)
{ return index<256 && (!index || codol_tagged_effect_slots[index]) ? codol_tagged_effect_slots[index] : -1; }
static void CODOL_RefreshByteEffects(void)
{
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    unsigned index;
    /* Run during name publication, before snapshot construction. Never allocate
     * from a per-recipient serializer or overwrite an inherited asset. The
     * wider mapping remains valid even when the low bank is exhausted. */
    for(index=1;index<CODOL_EFFECT_SLOTS;++index) {
        int wide=codol_effect_slots[index],slot=codol_byte_effect_slots[index],recipient;
        const char *name,*old;
        if(wide<=0 || !inherited) { codol_byte_effect_slots[index]=0; continue; }
        name=CODOL_GetConfigstring(bank,CODOL_CS_EFFECTS+(unsigned)wide);
        if(!name) name=CODOL_GetConfigstring(inherited,CODOL_CS_EFFECTS+(unsigned)wide);
        if(!name || !*name) { codol_byte_effect_slots[index]=0; continue; }
        if(slot>0) {
            old=CODOL_GetConfigstring(bank,CODOL_CS_EFFECTS+(unsigned)slot);
            if(!old) old=CODOL_GetConfigstring(inherited,CODOL_CS_EFFECTS+(unsigned)slot);
            if(old && !strcmp(old,name)) continue;
        }
        slot=CODOL_RegisterByteEffectName(bank,inherited,name);
        codol_byte_effect_slots[index]=slot;
        if(slot<=0 || !bank->values[CODOL_CS_EFFECTS+(unsigned)slot]) continue;
        if(!svs.clients || !sv_maxclients) continue;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_EFFECTS+(unsigned)slot,name);
        }
    }
}
/* Native overflow effect slots, separate from legacy configstring addresses.
 * Called by the full-width effect producer once its consumers are connected.
 * Return0 for a missing late lookup, -1 for invalid/exhausted registration. */
int CODOL_RegisterExtraServerEffect(const char *name,int create)
{
    char canonical[64];
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    unsigned index,free_slot=0;
    int slot,recipient;
    if(!name || !*name || strlen(name)>=64 || strchr(name,'\n') ||
       strchr(name,'\r')) return -1;
    /* Retained G_FindConfigstringIndex uses lowercase string identities for
     * effect names (base63e >334). Match that identity in the extra pool. */
    for(index=0;name[index];++index)
        canonical[index]=name[index]>='A' && name[index]<='Z' ? name[index]+32 : name[index];
    canonical[index]=0;
    name=canonical;
    for(index=100;index<CODOL_EFFECT_SLOTS;++index) {
        const char *current=codol_extra_effect_names[index-100];
        if(*current && !strcmp(current,name)) return (int)index;
        if(!*current && !free_slot) free_slot=index;
    }
    if(!create) return 0;
    if(!free_slot || !bank || !inherited) return -1;
    slot=CODOL_RegisterEffectName(bank,inherited,name);
    if(slot<=0) return -1;
    strcpy(codol_extra_effect_names[free_slot-100],name);
    codol_effect_slots[free_slot]=slot;
    if(bank->values[CODOL_CS_EFFECTS+(unsigned)slot] && svs.clients && sv_maxclients)
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_EFFECTS+(unsigned)slot,name);
        }
    CODOL_RefreshByteEffects();
    return (int)free_slot;
}
/* Preserve retained low-slot/constant-configstring allocation, then spill into
 * map-owned slots. The last retained helper argument is a diagnostic label,
 * not an overflow boolean. */
int G_FindConfigstringIndex(const char *,int,int,int,const char *);
int CODOL_RegisterNativeTaggedEffect(unsigned effect,const char *tag)
{
    /* Mark the wider native representation explicitly: legacy two-digit
     * compounds may contain tags beginning with digits and cannot be guessed.
     * Only the translated wire bank contains C1's unmarked three digits. */
    if(!effect || effect>=CODOL_EFFECT_SLOTS || !tag || !*tag ||
       strlen(tag)>MAX_STRING_CHARS-40 || strchr(tag,'\n') || strchr(tag,'\r')) return 0;
    return G_FindConfigstringIndex(va("@%03u%s",effect,tag),0x6a2,256,1,NULL);
}
int CODOL_RegisterMaskedTaggedEffect(unsigned effect,const char *tag,uint32_t audience)
{
    unsigned i,freeSlot=0;
    int tagged=CODOL_RegisterNativeTaggedEffect(effect,tag);
    if(tagged<=0) return 0;
    /* Match IW4's bounded compound bank, with the audience kept native.
     * Never recycle an identity: old snapshot queues still name it. */
    for(i=1;i<256;++i) {
        if(codol_masked_tagged_effects[i].tagged_slot==(unsigned)tagged &&
           codol_masked_tagged_effects[i].audience==audience) return (int)i;
        if(!codol_masked_tagged_effects[i].tagged_slot && !freeSlot) freeSlot=i;
    }
    if(!freeSlot) return 0;
    codol_masked_tagged_effects[freeSlot].tagged_slot=(unsigned)tagged;
    codol_masked_tagged_effects[freeSlot].audience=audience;
    return (int)freeSlot;
}
int CODOL_ReadMaskedTaggedEffect(unsigned index,unsigned *taggedSlot,uint32_t *audience)
{
    if(!index || index>=256 || !taggedSlot || !audience ||
       !codol_masked_tagged_effects[index].tagged_slot) return 0;
    *taggedSlot=codol_masked_tagged_effects[index].tagged_slot;
    *audience=codol_masked_tagged_effects[index].audience;
    return 1;
}
int CODOL_NativeEffectIndex(const char *name)
{
    unsigned index;
    int found,create=level.initializing;
    if(!name || !*name) return 0;
    found=G_FindConfigstringIndex(name,0x63e,100,0,NULL);
    if(found>0) return found;
    found=CODOL_RegisterExtraServerEffect(name,0);
    if(found>0) return found;
    if(found<0) { Scr_Error("invalid effect name"); return 0; }
    if(!create) { Scr_Error(va("effect '%s' not precached",name)); return 0; }
    for(index=1;index<100;++index) {
        unsigned handle=SV_GetConfigstringIndex(0x63e + index);
        if(!handle || handle==sv.emptyConfigString)
            return G_FindConfigstringIndex(name,0x63e,100,1,"effect");
    }
    found=CODOL_RegisterExtraServerEffect(name,1);
    if(found<0) { Scr_Error("effect registry exhausted or unavailable"); return 0; }
    return found;
}
void CODOL_GetNativeEffectName(unsigned index,char *out,int capacity)
{
    const char *name="";
    if(!out || capacity<=0) return;
    if(index>0 && index<100) {
        SV_GetConfigstring(0x63e + index,out,capacity);
        return;
    }
    if(index>=100 && index<CODOL_EFFECT_SLOTS) name=codol_extra_effect_names[index-100];
    Q_strncpyz(out,name,capacity);
}
static int CODOL_RefreshInheritedRange(int localized)
{
    unsigned first=localized==2 ? 0x63e : localized ? CS_LOCALIZEDSTRINGS : CS_MATERIALS;
    unsigned count=localized==2 ? 100 : localized ? MAX_LOCALIZEDSTRINGS : MAX_MATERIALS;
    unsigned base=localized==2 ? CODOL_CS_EFFECTS : localized ? CODOL_CS_LOCALIZEDSTRINGS : CODOL_CS_MATERIALS;
    unsigned *handles=localized==2 ? codol_effect_strings : localized ? codol_localized_strings : codol_material_strings;
    int *slots=localized==2 ? codol_effect_slots : localized ? codol_localized_slots : codol_material_slots;
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings(); unsigned index;
    for(index=1;index<count;++index) {
        unsigned handle=SV_GetConfigstringIndex(first+index);
        const char *name,*old; int slot,recipient;
        if(!handle || handle==sv.emptyConfigString) { handles[index]=handle; slots[index]=0; continue; }
        name=SL_ConvertToString(handle);
        if(!inherited || !name || !*name || strlen(name)>MAX_STRING_CHARS-32 || strchr(name,'\n') || strchr(name,'\r')) return 0;
        if(handle==handles[index] && slots[index]>0) {
            old=bank->values[base+slots[index]];
            if(!old) old=inherited->values[base+slots[index]];
            if(old && !strcmp(old,name)) continue;
        }
        slot=localized==2 ? CODOL_RegisterEffectName(bank,inherited,name) : localized ? CODOL_RegisterLocalizedString(bank,inherited,name) : CODOL_RegisterHudMaterial(bank,inherited,name);
        if(slot<1) return 0;
        handles[index]=handle; slots[index]=slot;
        /* Pure inherited matches need no command. An explicit override may
         * have been allocated before this binding, so publish it here too. */
        if(!bank->values[base+(unsigned)slot]) continue;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",base+(unsigned)slot,name);
        }
    }
    if(localized==2) CODOL_RefreshByteEffects();
    return 1;
}
static int CODOL_RefreshTaggedEffects(void)
{
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    unsigned index;
    if(!CODOL_RefreshInheritedRange(2)) return 0;
    for(index=1;index<256;++index) {
        unsigned handle=SV_GetConfigstringIndex(0x6a2+index);
        const char *native,*value; int effect,slot,previous,recipient;
        unsigned prefix=0,digits=2,native_effect=0,j;
        if(!handle || handle==sv.emptyConfigString) { codol_tagged_effect_slots[index]=0; continue; }
        native=SL_ConvertToString(handle);
        if(!native) return 0;
        if(native[0]=='@') { prefix=1; digits=3; }
        if(strlen(native)<=prefix+digits || strlen(native)>MAX_STRING_CHARS-33) return 0;
        for(j=prefix;j<prefix+digits;++j) {
            if(native[j]<'0' || native[j]>'9') return 0;
            native_effect=native_effect*10+(unsigned)(native[j]-'0');
        }
        effect=CODOL_ServerEffectToWire(native_effect);
        if(effect<=0) return 0;
        slot=CODOL_RegisterTaggedEffect(bank,inherited,(unsigned)effect,native+prefix+digits);
        if(slot<1) return 0;
        previous=codol_tagged_effect_slots[index];
        codol_tagged_effect_slots[index]=slot;
        value=CODOL_GetConfigstring(bank,CODOL_CS_TAGGED_EFFECTS+(unsigned)slot);
        if(previous==slot || !value) continue;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_TAGGED_EFFECTS+(unsigned)slot,value);
        }
    }
    return 1;
}
#include "codol_hud_fontscale.h"
static int CODOL_ResolveServerHud(void *context,const hudelem_t *source,codol_hud_bindings_t *out)
{
    int label,text,material; unsigned flags; (void)context;
    if(source->soundID || !CODOL_TranslateEngineHudFlags((unsigned)source->flags,&flags)) return 0;
    label=CODOL_ServerLocalizedToWire((unsigned)source->label);
    text=CODOL_ServerLocalizedToWire((unsigned)source->text);
    material=CODOL_ServerMaterialToWire((unsigned)source->materialIndex);
    if(label<0 || text<0 || material<0) return 0;
    codol_hud_fontscale_t scale;
    if(!CODOL_GetHudFontScale(source,&scale)) return 0;
    *out=(codol_hud_bindings_t){(unsigned)label,(unsigned)text,(unsigned)material,0,flags,
        scale.from,scale.start,scale.duration}; return 1;
}
int CODOL_CollectServerHud(codol_hud_state_t *out,const hudElemState_t *source)
{
    if(!out || !source || !CODOL_RefreshInheritedRange(0) || !CODOL_RefreshInheritedRange(1)) return 0;
    return CODOL_CollectEngineHud(out,source,CODOL_ResolveServerHud,NULL);
}
static int CODOL_RefreshAssetRange(unsigned first, unsigned count, unsigned *handles,
                                 int *slots, int model)
{
    unsigned index;
    codol_configstrings_t *bank = CODOL_ServerConfigstrings();
    const codol_configstrings_t *inherited = CODOL_ServerInheritedConfigstrings();
    for (index = 1; index < count; ++index) {
        unsigned handle = SV_GetConfigstringIndex(first + index);
        const char *name, *p;
        unsigned config_index;
        int slot, recipient;
        if (!handle || handle == sv.emptyConfigString) {
            handles[index] = handle; slots[index] = 0; continue;
        }
        name = SL_ConvertToString(handle);
        if (!name || !*name) return 0;
        if (handle == handles[index] && slots[index] > 0) {
            const char *registered = CODOL_GetConfigstring(bank,
                (model ? CODOL_CS_MODELS : CODOL_CS_TAGS) + slots[index]);
            if(!registered) registered = CODOL_GetConfigstring(inherited,
                (model ? CODOL_CS_MODELS : CODOL_CS_TAGS) + slots[index]);
            if (registered && !strcmp(registered, name)) continue;
        }
        /* Asset names are reliable-command tokens. Never silently alter a name
         * to make it parseable: that would identify a different client asset. */
        for (p = name; *p; ++p)
            if ((unsigned char)*p <= 32 || *p == 127 || *p == '"' || *p == ';' || *p == '\\') return 0;
        slot = model ? CODOL_RegisterInheritedModelName(bank, inherited, name) :
                       CODOL_RegisterInheritedTagName(bank, inherited, name);
        if (slot < 1) return 0;
        handles[index] = handle; slots[index] = slot;
        config_index = (model ? CODOL_CS_MODELS : CODOL_CS_TAGS) + slot;
        for (recipient = 0; recipient < sv_maxclients->integer; ++recipient) {
            client_t *target = &svs.clients[recipient];
            if (target->state >= CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target, "d %u %s", config_index, name);
        }
    }
    return 1;
}
static int CODOL_RefreshIndexedNames(unsigned native_base,unsigned wire_base,unsigned count,unsigned first)
{
    unsigned index; codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    for(index=first;index<count;++index) {
        unsigned handle=SV_GetConfigstringIndex(native_base+index);
        const char *name=(handle && handle!=sv.emptyConfigString) ? SL_ConvertToString(handle) : "";
        const char *old=CODOL_GetConfigstring(bank,wire_base+index),*p;
        int recipient;
        if(!name) return 0;
        if((!old && !*name) || (old && !strcmp(old,name))) continue;
        for(p=name;*p;++p)
            if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\') return 0;
        if(!CODOL_SetConfigstring(bank,wire_base+index,name)) return 0;
        /* These namespaces preserve native indices, including explicit clears. */
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",wire_base+index,name);
        }
    }
    return 1;
}
static int CODOL_RefreshSoundNames(void)
{
    /* C1 LocalSound 468765 reads CS[3395+index]. */
    return CODOL_RefreshIndexedNames(CS_SOUNDS,CODOL_CS_SOUNDS,MAX_SOUNDS,1);
}
static int CODOL_RefreshShellshockNames(void)
{
    /* Retained GScr_ShellShock searches 0x7a2+1..15; C1 4674ff..46752a
     * loads shock/<name>.shock for CS4227+index into settings[index]. */
    return CODOL_RefreshIndexedNames(0x7a2,CODOL_CS_SHELLSHOCKS,CODOL_SHELLSHOCK_SLOTS,1);
}
int CODOL_RefreshServerDvars(void)
{
    const codol_configstrings_t *inherited=CODOL_ServerInheritedConfigstrings();
    codol_configstrings_t *bank=CODOL_ServerConfigstrings(),*staged;
    char *pending[CODOL_MAX_REPLICATED_DVARS]={0};
    size_t old_pool_bytes[CODOL_MAX_REPLICATED_DVARS]={0};
    unsigned i,pass,changed=0;
    if(!inherited) return 1; /* No map constants installed yet. */
    /* Borrow unchanged pointers only for the final-pool view. Never clear this
     * shallow copy: pending[] alone owns the new allocations until commit. */
    staged=malloc(sizeof(*staged));
    if(!staged) return 0;
    memcpy(staged,bank,sizeof(*staged));
    for(i=0;i<CODOL_MAX_REPLICATED_DVARS;++i) {
        unsigned index=CODOL_CS_DVAR_NAMES+i,value_index=CODOL_CS_DVAR_VALUES+i;
        const char *name=CODOL_GetConfigstring(bank,index),*old,*value;
        cvar_t *var; size_t length;
        if(!name) name=CODOL_GetConfigstring(inherited,index);
        if(!name || !*name) break; /* C1 replicated-dvar applier 0x466020. */
        var=Cvar_FindVar(name);
        if(!var || !(var->flags&CVAR_SYSTEMINFO)) continue;
        value=Cvar_DisplayableValue(var);
        if(!value || strlen(value)>CODOL_CONFIGSTRING_VALUE_CHARS ||
           strchr(value,'\n') || strchr(value,'\r')) goto fail;
        old=CODOL_GetConfigstring(bank,value_index);
        if(!old) old=CODOL_GetConfigstring(inherited,value_index);
        if(old && !strcmp(old,value)) continue;
        length=strlen(value);
        pending[i]=malloc(length+1);
        if(!pending[i]) goto fail;
        memcpy(pending[i],value,length+1);
        staged->values[value_index]=pending[i];
        old_pool_bytes[i]=(old && *old) ? strlen(old)+1 : 0;
        ++changed;
    }
    if(!changed) { free(staged); return 1; }
    if(!CODOL_ConfigstringPoolSize(staged,inherited,NULL)) goto fail;
    /* C1 rebuilds the pool after every d command. Decreases first make every
     * intermediate pool no larger than max(old pool, validated final pool).
     * These are value-only updates: the inherited name ordering is unchanged. */
    for(pass=0;pass<2;++pass) {
        for(i=0;i<CODOL_MAX_REPLICATED_DVARS;++i) {
            unsigned value_index=CODOL_CS_DVAR_VALUES+i;
            size_t length,new_pool_bytes;
            int recipient;
            if(!pending[i]) continue;
            length=strlen(pending[i]);
            new_pool_bytes=length ? length+1 : 0;
            if((new_pool_bytes>old_pool_bytes[i]) != (pass==1)) continue;
            if(bank->values[value_index])
                bank->bytes-=strlen(bank->values[value_index])+1;
            else ++bank->count;
            free(bank->values[value_index]);
            bank->values[value_index]=pending[i];
            bank->bytes+=length+1;
            pending[i]=NULL; /* ownership transferred; no fallible allocation */
            for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
                client_t *target=&svs.clients[recipient];
                if(target->state>=CS_PRIMED && target->gamestateSent)
                    SV_SendServerCommandNoLoss(target,"d %u %s",value_index,
                        bank->values[value_index]);
            }
        }
    }
    free(staged);
    return 1;
fail:
    for(i=0;i<CODOL_MAX_REPLICATED_DVARS;++i) free(pending[i]);
    free(staged);
    return 0;
}
/* Registration-time C1 tag slot allocation. The wire slot for a native tag
 * was only allocated from the gamestate/snapshot path, so a link captured in
 * G_RunFrame before the first snapshot of a map (the three SV_SpawnServer
 * warm-up frames and every frame until a client is primed) had a native
 * index and no slot, and was dropped for that frame. IW4 has no such gap:
 * G_TagIndex publishes CS_TAGS+i at once and that index is the wire index.
 * Idempotent and cheap (32 entries); safe from G_RunFrame. */
int CODOL_RefreshServerTagNames(void)
{
    if(!sv_maxclients) return 0;
    return CODOL_RefreshAssetRange(CS_TAGS, MAX_TAGS, codol_tag_strings, codol_tag_slots, 0);
}
int CODOL_RefreshServerAssetNames(void)
{
    return CODOL_RefreshAssetRange(CS_MODELS, MAX_MODELS, codol_model_strings, codol_model_slots, 1) &&
           CODOL_RefreshAssetRange(CS_TAGS, MAX_TAGS, codol_tag_strings, codol_tag_slots, 0) &&
           CODOL_RefreshSoundNames() && CODOL_RefreshInheritedRange(0) && CODOL_RefreshInheritedRange(1) &&
           CODOL_RefreshIndexedNames(CS_STATUSICONS,CODOL_CS_STATUS_ICONS,MAX_STATUSICONS,0) &&
           CODOL_RefreshIndexedNames(CS_HEADICONS,CODOL_CS_HEAD_ICONS,MAX_HEADICONS,0) &&
           CODOL_RefreshIndexedNames(827,1312,3,0) &&
           CODOL_RefreshTaggedEffects() && CODOL_RefreshShellshockNames() && CODOL_RefreshServerDvars();
}

int CODOL_OverlayServerClient(codol_client_state_t *wire, const clientState_t *engine)
{
    codol_client_assets_t assets = {0};
    int model, tag;
    unsigned i;
    if (!wire || !engine || (model = CODOL_ServerModelToWire(engine->modelindex)) < 0) return 0;
    assets.model = model;
    for (i = 0; i < 6; ++i) {
        model = CODOL_ServerModelToWire(engine->attachModelIndex[i]);
        tag = CODOL_ServerTagToWire(engine->attachTagIndex[i]);
        if (model < 0 || tag < 0) return 0;
        assets.attach_model[i] = model; assets.attach_tag[i] = tag;
    }
    /* C1 G_UpdateClientState 0x50d0f0 fills the animation-condition words
     * from the client's playerState. The archived clientState carries none of
     * them, so they come from the live client like rank does. */
    if(engine->clientIndex>=0 && engine->clientIndex<level.maxclients &&
       g_entities[engine->clientIndex].r.inuse && g_entities[engine->clientIndex].client) {
        const gentity_t *player=&g_entities[engine->clientIndex];
        const playerState_t *ps=&player->client->ps;
        assets.dual_wield=CODOL_WeaponStateIsDualWielding(ps) ? 1u : 0u;
        assets.riot_shield_next=(ps->weapFlags & CODOL_WEAP_RIOTSHIELD_NEXT) ? 1u : 0u;
        /* 0x50d16a..0x50d18e; ps+0x3334 has no writer in C1, so the value
         * is 1 while the 0x400000 window is open. */
        assets.dive_state=((ps->pm_flags & 0x400000u) && !(ps->pm_flags & 0x800u) && ps->pm_time==0) ? 1u : 0u;
        /* 0x12c: the vehicle an ET_PLAYER is drawn from (0x44c15f). A remote
         * driver owns its vehicle through ownerNum (codol_remote_vehicle.cpp
         * validates ownerNum == vehicle+1); a seated rider is tag-linked to
         * an ET_VEHICLE parent. */
        assets.vehicle_entity=0;
        if(CODOL_RemoteVehicleType((unsigned)engine->clientIndex)>=0 && player->r.ownerNum.number>0 &&
           player->r.ownerNum.number-1<ENTITYNUM_MAX_NORMAL)
            assets.vehicle_entity=(unsigned)player->r.ownerNum.number-1;
        else if(player->tagInfo && player->tagInfo->parent && player->tagInfo->parent->r.inuse &&
                player->tagInfo->parent->s.eType==ET_VEHICLE)
            assets.vehicle_entity=(unsigned)player->tagInfo->parent->s.number;
        /* 0x134: no producer identified in C1's server module yet; 0 is the
         * default colour (0x460452 -> 1,1,1). */
        assets.colour_index=0;
        /* 0x010: the action slot [{ACTION_SLOT_HELP}] names, set by script
         * (setActionSlotHelp) before a killstreak splash; wire is slot - 1. */
        assets.action_slot_help=CODOL_ClientActionSlotHelp((unsigned)engine->clientIndex);
        if(assets.action_slot_help) --assets.action_slot_help;
    }
    return CODOL_OverlayEngineClient(wire, engine, &assets);
}
int CODOL_OverlayServerModelEntity(codol_entity_state_t *wire,const gentity_t *engine)
{
    int model;
    if(!wire || !engine || engine->r.bmodel ||
       (model=CODOL_ServerModelToWire(engine->s.index))<0) return 0;
    return CODOL_OverlayEngineModelEntity(wire,&engine->s,(unsigned)model,0);
}
static int CODOL_RefreshHintStrings(void)
{
    unsigned slot;
    codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    /* Native G_GetHintStringIndex starts at0x115, with no reserved zero slot.
     * C1 456270 reads CS[584+ps.cursorHintString] as localized message text. */
    for(slot=0;slot<CODOL_HINTSTRING_RETAINED;++slot) {
        unsigned handle=SV_GetConfigstringIndex(0x115+slot);
        unsigned wire_index=CODOL_CS_HINTSTRINGS+slot;
        const char *value=(handle && handle!=sv.emptyConfigString) ? SL_ConvertToString(handle) : "";
        const char *old=CODOL_GetConfigstring(bank,wire_index);
        int recipient;
        if(!value || strlen(value)>MAX_STRING_CHARS-32 || strchr(value,'\n') || strchr(value,'\r')) return 0;
        if((!old && !*value) || (old && !strcmp(old,value))) continue;
        if(!CODOL_SetConfigstring(bank,wire_index,value)) return 0;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",wire_index,value);
        }
    }
    return 1;
}
/* G_GetHintStringIndex(int *index, const char *text) for all 96 C1 slots.
 *
 * The retained allocator (and its inline copies in GScr_SetHintString and
 * trigger_use_shared) scanned the 32 configstrings at 0x115 and failed at 32
 * ("Too many different hintstring values"): the block cannot grow because
 * 0x115+32 is CS_LOCALIZEDSTRINGS. C1 allows 96 (0x53c4d0 cmp esi,0x60).
 * Slots 0..31 keep the retained storage so CODOL_RefreshHintStrings still
 * publishes them; 32..95 are kept here and published straight to
 * CS 584+slot. Both halves allocate in order and never free within a map,
 * like the original. Returns 1 with *index set, or 0 with *index = -1. */
int CODOL_G_GetHintStringIndex(int *index, const char *text)
{
    char current[MAX_STRING_CHARS];
    unsigned slot;
    codol_configstrings_t *bank;
    int recipient;
    if(!index) return 0;
    *index=-1;
    if(!text) return 0;
    for(slot=0;slot<CODOL_HINTSTRING_RETAINED;++slot) {
        SV_GetConfigstring(0x115+slot,current,sizeof(current));
        if(!current[0]) {
            SV_SetConfigstring(0x115+slot,text);
            *index=(int)slot;
            return 1;
        }
        if(!strcmp(current,text)) { *index=(int)slot; return 1; }
    }
    for(slot=CODOL_HINTSTRING_RETAINED;slot<CODOL_HINTSTRING_SLOTS;++slot) {
        char *stored=codol_high_hints[slot-CODOL_HINTSTRING_RETAINED];
        if(stored[0]) {
            if(!strcmp(stored,text)) { *index=(int)slot; return 1; }
            continue;
        }
        bank=CODOL_ServerConfigstrings();
        if(!bank || strlen(text)>MAX_STRING_CHARS-32 || strchr(text,'\n') || strchr(text,'\r') ||
           !CODOL_SetConfigstring(bank,CODOL_CS_HINTSTRINGS+slot,text)) {
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL hint strings: cannot publish slot %u\n",slot);
            return 0;
        }
        Q_strncpyz(stored,text,MAX_STRING_CHARS);
        if(svs.clients && sv_maxclients)
            for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
                client_t *target=&svs.clients[recipient];
                if(target->state>=CS_PRIMED && target->gamestateSent)
                    SV_SendServerCommandNoLoss(target,"d %u %s",CODOL_CS_HINTSTRINGS+slot,text);
            }
        *index=(int)slot;
        return 1;
    }
    return 0;
}
/* C1 keeps the two team scores in cg+0xBEB20 and cg+0xBEB24. Two routes reach
 * them: the reliable commands C and D (4699d5 / 469a12), which the retained
 * setteamscore and updatescores builtins now send, and configstrings 5 and 6,
 * which the client also reads for its win/lose banner (550960) and which a
 * late joiner needs in its gamestate. The retained engine never writes those
 * two configstrings - CS_SCORES1/2 are inside a commented-out block in
 * g_shared.h - so publish them here whenever level.teamScores changes.
 * The bank itself is the previous-value record, so a new map republishes. */
void CODOL_PublishTeamScores(void)
{
    static const unsigned index[2] = { CODOL_CS_TEAM_SCORE1, CODOL_CS_TEAM_SCORE2 };
    int score[2];
    unsigned i;
    codol_configstrings_t *bank;
    if (!level.clients || !svs.clients || !sv_maxclients) return;
    score[0] = level.teamScores[TEAM_RED];
    score[1] = level.teamScores[TEAM_BLUE];
    bank = CODOL_ServerConfigstrings();
    for (i = 0; i < 2; ++i) {
        char value[16];
        const char *old;
        int recipient, length;
        length = snprintf(value, sizeof(value), "%i", score[i]);
        if (length < 0 || (size_t)length >= sizeof(value)) continue;
        old = CODOL_GetConfigstring(bank, index[i]);
        if (old && !strcmp(old, value)) continue;
        if (!CODOL_SetConfigstring(bank, index[i], value)) return;
        for (recipient = 0; recipient < sv_maxclients->integer; ++recipient) {
            client_t *target = &svs.clients[recipient];
            if (target->state >= CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target, "d %u %s", index[i], value);
        }
    }
}
/* Tell the client to rebuild its weapon HUD when the weapon or the offhand
 * changes. C1's F command (469a8f) reads one element index, bounds it with
 * "cmp eax,7 / ja" and dispatches through the eight-entry table at 0x4682f4
 * inside 0x468140: 0 health, 1 compass, 2 stance, 3 sprint meter,
 * 4 weapon info, 5 offhand info, 6 objective info, 7 RC bomb hints.
 *
 * A retail server sends it after a weapon change; this server never did, which
 * leaves the ammo and offhand panels showing whatever they were built with.
 * Driving it from here rather than from the retained weapon assembly catches
 * every path that can change the weapon - give, switch, pickup, class change,
 * spawn - with no extra send site. */
void CODOL_RefreshWeaponHud(void)
{
    static int last_weapon[MAX_CLIENTS];
    static int last_offhand[MAX_CLIENTS];
    static unsigned char primed[MAX_CLIENTS];
    int i, limit;
    if (!level.clients || !svs.clients || !sv_maxclients) return;
    limit = sv_maxclients->integer;
    if (limit > level.maxclients) limit = level.maxclients;
    if (limit > MAX_CLIENTS) limit = MAX_CLIENTS;
    for (i = 0; i < limit; ++i) {
        client_t *client = &svs.clients[i];
        const playerState_t *ps;
        if (client->state != CS_ACTIVE || !client->gamestateSent) { primed[i] = 0; continue; }
        ps = &level.clients[i].ps;
        if (!primed[i]) {
            /* The first frame after a client goes active is its own refresh. */
            primed[i] = 1;
            last_weapon[i] = ps->weapon;
            last_offhand[i] = ps->offHandIndex;
            continue;
        }
        if (ps->weapon != last_weapon[i]) {
            last_weapon[i] = ps->weapon;
            SV_SendServerCommandNoLoss(client, "F 4");
        }
        if (ps->offHandIndex != last_offhand[i]) {
            last_offhand[i] = ps->offHandIndex;
            SV_SendServerCommandNoLoss(client, "F 5");
        }
    }
}
int CODOL_PublishAssetConfigstring(unsigned index)
{
    /* Retained SaveRegisteredWeapons writes its space-delimited native list
     * to CS 0x8d2.  A CoDOL client has no such list; it registers definitions
     * from CS_WEAPONS (5362+) and CS_WEAPON_COUNT (6517).  Refresh that real
     * registry here and consume the native update.  Publishing the retained
     * list both targets an unrelated C1 slot and exceeds C1's 1015-byte
     * single-configstring limit once the IW4 weapon set is registered. */
    if(index==0x8d2) {
        if(CODOL_RefreshServerWeaponMappings()) return 1;
        /* The refresh fails once the retained table has outgrown the 128-entry
         * engine->wire map, which happens as soon as anything registers a
         * weapon after that map is full (append_weapon_set's native_count>128
         * guard in codol_sv_weapons.c). Keeping the previous map leaves only
         * the unmapped definitions unreachable - CODOL_WeaponToWire answers -1
         * for them and every consumer already handles that - whereas returning
         * -1 here ERR_DROPs the server and ends the match for everyone. Warn
         * once per level so the capacity problem stays visible. */
        if(!codol_weapon_map_warned) {
            codol_weapon_map_warned = 1;
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL weapon map refresh failed (%s); keeping the previous map. Definitions past the retained 128-slot table have no wire index\n",
                CODOL_ServerWeaponRegistryError());
        }
        return 1;
    }
    /* Retained SaveRegisteredItems similarly writes its compact ownership
     * mask to 0x90a.  CoDOL receives owned/equipped weapons in playerState's
     * inventory section and does not consume this native configstring. */
    if(index==0x90a) return 1;
    /* These are retained server vote bookkeeping, not CoDOL wire slots.
     * C1's aligned dispatcher467350 sends13 to fog4667e0,15 to match
     * time466780 and16 to map center49e190. Raw fallback publication would
     * corrupt those fields after every vote. Keep native values for vote
     * logic; CoDOL voting presentation needs its own verified producer. */
    if(index>=CS_VOTE_TIME && index<=CS_VOTE_NO) return 1;
    /* Retained precache handlers allocate every slot, including offset zero.
     * C1's icon banks are separate from its general material namespace. */
    if(index>=CS_STATUSICONS && index<CS_STATUSICONS+MAX_STATUSICONS)
        return CODOL_RefreshIndexedNames(CS_STATUSICONS,CODOL_CS_STATUS_ICONS,MAX_STATUSICONS,0) ? 1 : -1;
    if(index>=CS_HEADICONS && index<CS_HEADICONS+MAX_HEADICONS)
        return CODOL_RefreshIndexedNames(CS_HEADICONS,CODOL_CS_HEAD_ICONS,MAX_HEADICONS,0) ? 1 : -1;
    /* C1 selector lookup541130: config bank27d3cba +2*1312. */
    if(index>=827 && index<830)
        return CODOL_RefreshIndexedNames(827,1312,3,0) ? 1 : -1;
    if(index>=0x115 && index<0x115+CODOL_HINTSTRING_RETAINED)
        return CODOL_RefreshHintStrings() ? 1 : -1;
    if(index>=0x63e && index<0x63e + 100) return CODOL_RefreshTaggedEffects() ? 1 : -1;
    if(index>=0x6a2 && index<0x7a2) return CODOL_RefreshTaggedEffects() ? 1 : -1;
    if(index>=0x7a2 && index<0x7a2+CODOL_SHELLSHOCK_SLOTS)
        return CODOL_RefreshShellshockNames() ? 1 : -1;
    if(index>=CS_MATERIALS && index<CS_MATERIALS+MAX_MATERIALS) return CODOL_RefreshInheritedRange(0) ? 1 : -1;
    if(index>=CS_LOCALIZEDSTRINGS && index<CS_LOCALIZEDSTRINGS+MAX_LOCALIZEDSTRINGS) return CODOL_RefreshInheritedRange(1) ? 1 : -1;
    if(index==9 || index==11 || index==12 || index==821 || index==822 || index==823)
        return CODOL_RefreshServerMapConfigstrings() ? 1 : -1;
    if(index>=CS_SOUNDS && index<CS_SOUNDS+MAX_SOUNDS)
        return CODOL_RefreshSoundNames() ? 1 : -1;
    if(index>=CS_MODELS && index<CS_MODELS+MAX_MODELS)
        return CODOL_RefreshAssetRange(CS_MODELS,MAX_MODELS,codol_model_strings,codol_model_slots,1) ? 1 : -1;
    if(index>=CS_TAGS && index<CS_TAGS+MAX_TAGS)
        return CODOL_RefreshAssetRange(CS_TAGS,MAX_TAGS,codol_tag_strings,codol_tag_slots,0) ? 1 : -1;
    return 0;
}
/* Retained setexpfog produces start,density,r,g,b,milliseconds. C1's
 * non-sun fog producer545fd0 uses start,density,r,g,b,opacity,milliseconds,0
 * (format c57acc). Preserve the original tokens, adding full opacity and
 * disabling the optional sun extension. G_InitGame's single "0" clears fog.
 * This translates the existing six-argument method, not C1's richer API. */
static int CODOL_TranslateRetainedFog(const char *value,char output[512])
{
    char part[18][64];
    const char *cursor,*start;
    int count=0,length;
    if(!value) return 0;
    if(!*value || !strcmp(value,"0")) {
        strcpy(output,value);
        return 1;
    }
    cursor=value;
    while(*cursor) {
        size_t bytes;
        while(isspace((unsigned char)*cursor)) ++cursor;
        if(!*cursor) break;
        start=cursor;
        while(*cursor && !isspace((unsigned char)*cursor)) ++cursor;
        bytes=(size_t)(cursor-start);
        if(count==18 || bytes>=sizeof(part[0])) return 0;
        memcpy(part[count],start,bytes); part[count++][bytes]=0;
    }
    /* The native CoDOL GSC producer already writes the full client format. */
    if((count==8 && !strcmp(part[7],"0")) ||
       (count==17 && !strcmp(part[7],"1"))) {
        if(strlen(value)>=512) return 0;
        strcpy(output,value);
        return 1;
    }
    if(count!=6) return 0;
    length=snprintf(output,512,"%s %s %s %s %s 1 %s 0",
        part[0],part[1],part[2],part[3],part[4],part[5]);
    return length>=0 && length<512;
}
int CODOL_RefreshServerMapConfigstrings(void)
{
    static const unsigned mapping[][2]={{822,CODOL_CS_NORTHYAW},{823,CODOL_CS_MINIMAP},
        {11,CODOL_CS_MATCH_END_TIME},{12,CODOL_CS_MAP_CENTER},
        {821,CODOL_CS_AMBIENT},{9,CODOL_CS_FOG}};
    unsigned i; codol_configstrings_t *bank=CODOL_ServerConfigstrings();
    if(!CODOL_RefreshHintStrings()) return 0;
    for(i=0;i<sizeof(mapping)/sizeof(mapping[0]);++i) {
        unsigned handle=SV_GetConfigstringIndex(mapping[i][0]), wire_index=mapping[i][1];
        const char *value=(handle && handle!=sv.emptyConfigString) ? SL_ConvertToString(handle) : "";
        const char *old=CODOL_GetConfigstring(bank,wire_index);
        char fog_value[512];
        int recipient;
        /* SV_SetGameEndTime/MapCenter use IW3 11/12. C1 466780 reads
         * end time from 15; 467020 parses center from 16 into 6c450c8.
         * Unset initial values inherit the empty client defaults. */
        if(i>=2 && !old && value && !*value) continue;
        if(wire_index==CODOL_CS_FOG) {
            if(!CODOL_TranslateRetainedFog(value,fog_value)) return 0;
            value=fog_value;
        }
        /* Preserve each field's payload, including ambience's n/t info keys.
         * C1 ambientStop5427d0 uses1300; dispatcher4676b6 feeds44f2e0,
         * which reads name n and deadline t, just like the retained producer.
         * Bound the complete reliable command. */
        if(!value || strlen(value)>MAX_STRING_CHARS-32 || strchr(value,'\n') || strchr(value,'\r')) return 0;
        if(old && !strcmp(old,value)) continue;
        if(!CODOL_SetConfigstring(bank,wire_index,value)) return 0;
        for(recipient=0;recipient<sv_maxclients->integer;++recipient) {
            client_t *target=&svs.clients[recipient];
            if(target->state>=CS_PRIMED && target->gamestateSent)
                SV_SendServerCommandNoLoss(target,"d %u %s",wire_index,value);
        }
    }
    return 1;
}
static int collect_clients(int first, int count, codol_client_state_t *out, size_t capacity,
    codol_snapshot_client_resolver_t resolve,void *context)
{
    codol_client_state_t clients[32] = {{0}};
    int i, ring_count = svsHeader.numSnapshotClients, next = svsHeader.nextSnapshotClients;
    if (count < 0 || count > 32 || (size_t)count > capacity || (count && !out) ||
        first < 0 || next < 0 || first > next || (int64_t)first + count > next) return 0;
    if (!count) return 1;
    if (!svsHeader.snapshotClients || ring_count <= 0 || ring_count > 0x20000 ||
        count > ring_count || first < (int64_t)next - ring_count) return 0;
    for (i = 0; i < count; ++i) {
        const clientState_t *source = &svsHeader.snapshotClients[((int64_t)first+i) % ring_count];
        if(resolve && !resolve(context,source,&clients[i])) return 0;
        if (!CODOL_OverlayServerClient(&clients[i], source) ||
            !CODOL_OverlayCapturedClientAbilities(first+i, &clients[i]) ||
            !CODOL_OverlayClientCards(&clients[i]) ||
            (i && clients[i].number <= clients[i-1].number)) return 0;
    }
    if (count) memcpy(out, clients, (size_t)count*sizeof(*out));
    return 1;
}
int CODOL_CollectServerClients(int first,int count,codol_client_state_t *out,size_t capacity)
{ return collect_clients(first,count,out,capacity,NULL,NULL); }
int CODOL_CollectServerClientsResolved(int first,int count,codol_client_state_t *out,size_t capacity,
    codol_snapshot_client_resolver_t resolve,void *context)
{
    if(count && !resolve) return 0;
    return collect_clients(first,count,out,capacity,resolve,context);
}
#endif
