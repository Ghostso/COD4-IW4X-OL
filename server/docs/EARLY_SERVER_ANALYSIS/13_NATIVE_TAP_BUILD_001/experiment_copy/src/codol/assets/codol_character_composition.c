#include "codol_character_composition.h"
#include "codol_character_variant.h"
#include <stdio.h>
#include <string.h>
/* Early alpha0022 seeds used the ascending string-address order as profile
 * slots. C1 694818/694850 copies slots unchanged and reads head slot4, so
 * those eye-first records are legacy data, not another engine layout.
 * Recognize the complete old convention before repairing a local copy. */
static int normalize_legacy_character(codol_profile_character_t *selected)
{
    static const unsigned destinations[]={13,9,8,7,6,1,3,5,0,2,4};
    const codol_engine_table_t *market;
    uint16_t items[20]={0};
    unsigned i;
    if(!selected->items[10] || selected->items[10]>=32768)return 1;
    for(i=11;i<20;++i)if(selected->items[i])return 1;
    if(CODOL_LoadEngineStringTable("mp/coMarketplaceItems.csv",&market)!=1)return 0;
    for(i=0;i<11;++i) {
        codol_character_item_t item;
        unsigned id=selected->items[i];
        int status;
        if(!id)continue;
        if(id>=32768)return 1;
        status=CODOL_CharacterItem(market,(uint16_t)id,&item);
        if(status<0)return 0;
        if(status!=1 || strcmp(item.type,"cha") ||
           CODOL_CharacterSlotForGroup(item.group)!=(int)destinations[i])return 1;
        items[destinations[i]]=(uint16_t)id;
    }
    memcpy(selected->items,items,sizeof(items));
    return 1;
}
/* mp/cyborgclasstable.csv is the Zombies roster: column 0 is the mode's own
 * slot key (zm1..zm4), column 2 the character's sex and column 3 its head
 * identity. The four shipped rows are the only characters Zombies offers, and
 * one of them is female: hea_zmgirl exists solely as "*_zm_f_*" geometry, so
 * composing it with the male variant selects another character's row or no row
 * at all. C1 keeps the sex with the roster rather than in the profile, so the
 * server has to ask the same table.
 * 1 resolved, 0 the profile's zombies head is not a roster character (output
 * preserved), -1 the table or profile is unusable. */
/* The roster row of the profile's zombies character: the row whose head
 * identity (column 3) is the profile's selected zombies head. 1 with *row and
 * *roster_out set, 0 when the profile names no roster character, -1 when the
 * table or profile is unusable. */
int CODOL_ZombieCharacterRow(const uint8_t *profile,size_t size,
    const codol_structured_schema_t *schema,int *row,const void **roster_out)
{
    codol_profile_character_t selected;const codol_engine_table_t *market,*roster;
    codol_character_item_t head;int status,r;
    if(!row)return -1;
    if(!CODOL_ProfileCharacter(profile,size,schema,"zm",&selected) ||
       !normalize_legacy_character(&selected))return -1;
    if(!selected.items[4] || selected.items[4]>=32768)return 0;
    if(CODOL_LoadEngineStringTable("mp/coMarketplaceItems.csv",&market)!=1 ||
       CODOL_LoadEngineStringTable("mp/cyborgclasstable.csv",&roster)!=1)return -1;
    status=CODOL_CharacterItem(market,selected.items[4],&head);
    if(status<0)return -1;
    if(status!=1 || !head.name || !*head.name)return 0;
    if(roster->rowCount<0 || roster->columnCount<4 || (roster->rowCount && !roster->values))return -1;
    /* C1's own table order; the last matching row wins, as every other
     * marketplace/character table lookup in this file does. */
    for(r=roster->rowCount-1;r>=0;--r) {
        const char *const *cells=roster->values+(size_t)r*roster->columnCount;
        if(!cells[3] || strcmp(cells[3],head.name))continue;
        *row=r;
        if(roster_out)*roster_out=roster;
        return 1;
    }
    return 0;
}
int CODOL_ZombieCharacterGender(const uint8_t *profile,size_t size,
    const codol_structured_schema_t *schema,unsigned *gender)
{
    const codol_engine_table_t *roster=NULL;const char *const *cells;int row,status;
    const void *table=NULL;
    if(!gender)return -1;
    status=CODOL_ZombieCharacterRow(profile,size,schema,&row,&table);
    roster=table;
    if(status!=1)return status;
    cells=roster->values+(size_t)row*roster->columnCount;
    if(!cells[2])return 0;
    /* The shipped cell carries stray padding (" \t\tf", " \t\tm"): compare the
     * one token, as the GSC roster reader does. Matching the raw cell left
     * every row unresolved and hid the female row behind the item-413 guard. */
    {
        const char *sex=cells[2];size_t n;
        while(*sex==' ' || *sex=='\t')++sex;
        for(n=0;sex[n] && sex[n]!=' ' && sex[n]!='\t' && sex[n]!='\r' && sex[n]!='\n';++n);
        if(n==1 && sex[0]=='f'){*gender=1;return 1;}
        if(n==1 && sex[0]=='m'){*gender=0;return 1;}
    }
    return -1;
}
int CODOL_ComposeProfileCharacter(const uint8_t *profile,size_t size,const codol_structured_schema_t *schema,
    const char *faction,unsigned gender,const char *camo,const char *skin,unsigned rig_selector,
    codol_character_composition_t *out)
{
    codol_profile_character_t selected;codol_character_composition_t next={0};
    const codol_engine_table_t *market,*defaults,*rigs;unsigned f,i;
    if(!out || !faction || gender>1 || !camo || strlen(camo)!=3 || !skin)return 0;
    if(!strcmp(faction,"tf"))f=0;else if(!strcmp(faction,"sc"))f=1;
    else if(!strcmp(faction,"zm"))f=2;else return 0;
    if(!CODOL_ProfileCharacter(profile,size,schema,faction,&selected)) {
        fprintf(stderr,"CoDOL appearance: profile character read failed for %s\n",faction);return 0;
    }
    if(!normalize_legacy_character(&selected)) {
        fprintf(stderr,"CoDOL appearance: legacy character normalization failed for %s\n",faction);return 0;
    }
    if(CODOL_LoadEngineStringTable("mp/coMarketplaceItems.csv",&market)!=1 ||
       CODOL_LoadEngineStringTable("mp/coCharacterDefTable.csv",&defaults)!=1 ||
       CODOL_LoadEngineStringTable("mp/coChestRigs.csv",&rigs)!=1) {
        fprintf(stderr,"CoDOL appearance: character tables unavailable for %s\n",faction);return 0;
    }
    next.character_index=selected.character_index;
    memcpy(next.items,selected.items,sizeof(next.items));
    /* C1 sign-extends the profile shorts, but it composes into a ZEROED array:
     * 0060b074 memsets the eighteen-slot composition to 0 (push 0x4c, push 0,
     * call 0xae04c0) and only then does 0060d2c0 - and the per-record variant
     * 0060d3a0 called from 0060b0fd behind the same memset - copy the stored
     * slots, skipping every value that is exactly -1 (cmp edx,0xffffffff / je
     * past the store). A -1 selection therefore reaches 0060d020 as a zero and
     * takes that character's coCharacterDefTable default. -1 means "nothing
     * chosen for this slot", not "this slot stays empty": a TF character saved
     * without gloves (hea_sean, profile slot 3 == -1) still receives its
     * charHAN default han_basic, which is what draws its viewmodel hands.
     * Other negative values are not special-cased by C1 and stay unresolvable
     * below, so the positive-ID guards remain. */
    for(i=0;i<CODOL_COMPOSITION_SLOTS;++i)if(next.items[i]==0xFFFFu)next.items[i]=0;
    if((next.items[4]<32768 && !CODOL_ApplyCharacterDefaults(market,defaults,next.items[4],next.items)) ||
       !CODOL_ApplyCharacterChestRig(market,rigs,rig_selector,next.items)) {
        fprintf(stderr,"CoDOL appearance: defaults or rig failed for %s character %u head %u rig %u\n",faction,selected.character_index,next.items[4],rig_selector);return 0;
    }
    if(next.items[2] && next.items[2]<32768 && next.items[7]) {
        const codol_engine_table_t *parts;codol_character_item_t item;int allowed;
        if(CODOL_LoadCharacterItemParts(next.items[2],&item,&parts)!=1 ||
           !CODOL_CharacterSlot7Allowed(parts,item.name,&allowed))return 0;
        if(!allowed)next.items[7]=0;
    }
    for(i=0;i<CODOL_COMPOSITION_SLOTS;++i) {
        int status;
        if(!next.items[i] || next.items[i]>=32768)continue;
        status=CODOL_LoadCharacterItemModels(next.items[i],gender,f,camo,skin,
            &next.models[i],&next.viewmodels[i]);
        if(status<0) {
            fprintf(stderr,"CoDOL appearance: item model failed for %s character %u slot %u item %u\n",faction,selected.character_index,i,next.items[i]);return 0;
        }
        if(status!=1)next.viewmodels[i]=NULL;
    }
    *out=next;return 1;
}
int CODOL_ComposeProfileCharacterAuto(const uint8_t *profile,size_t size,
    const codol_structured_schema_t *schema,const char *faction,unsigned gender,
    const char *camo,unsigned rig_selector,codol_character_composition_t *out,char skin[4])
{
    codol_profile_character_t selected;char tone[4];
    if(!out)return 0;
    /* C1 0060d354 reads the head slot before any default merge, precisely
     * because the merge is keyed by it, and derives the tone from that item. */
    if(!CODOL_ProfileCharacter(profile,size,schema,faction,&selected) ||
       !normalize_legacy_character(&selected)) {
        fprintf(stderr,"CoDOL appearance: automatic character selection failed for %s\n",faction);return 0;
    }
    CODOL_CharacterSkinTone(selected.items[4]<32768 ? selected.items[4] : 0,tone);
    if(!CODOL_ComposeProfileCharacter(profile,size,schema,faction,gender,camo,tone,
        rig_selector,out))return 0;
    if(skin)memcpy(skin,tone,4);
    return 1;
}
