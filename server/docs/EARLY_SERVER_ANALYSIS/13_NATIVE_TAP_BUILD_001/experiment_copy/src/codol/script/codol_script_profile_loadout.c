#include "codol_script_profile_loadout.h"
#include "codol_script_profile_vm.h"
#include "codol_character_variant.h"
#ifdef CODOL_SERVER
#include "codol_sv_weapons.h"
#include "codol_weapon_compose.h"
#include "codol_weapon_budget.h"
#include "codol_loadout_fastmag.h"
#include "qcommon.h"
#endif
#include <stdio.h>
#include <string.h>
#define MARKETPLACE_TABLE "mp/coMarketplaceItems.csv"
#define ATTACHMENT_TABLE "mp/coWeaponAttachmentTable.csv"
/* An empty CoDOL slot is the stored -1; zero is an id no marketplace row uses. */
static int slot_empty(int item){ return item<=0; }
static int read_short(const codol_structured_definition_t *d,const uint8_t *record,size_t capacity,
    const codol_structured_path_t *path,size_t count,int *out)
{
    codol_structured_field_t field;uint32_t value;
    if(!CODOL_ResolveStructuredField(d,path,count,&field) || field.type.kind!=9)return 0;
    if(!CODOL_StructuredReadScalar(&d->layout,field.type.kind,field.logical_index,
           record,capacity,&value))return 0;
    *out=(int)(int16_t)(uint16_t)value;return 1;
}
int CODOL_ReadProfileLoadout(unsigned client,unsigned class_index,codol_profile_loadout_t *out)
{
    static const char *const bases[CODOL_LOADOUT_WEAPONS]={"primaryBase","secondaryBase"};
    static const char *const attach[CODOL_LOADOUT_WEAPONS]={"primaryAttach","secondaryAttach"};
    const codol_structured_definition_t *d;const uint8_t *record;size_t capacity;
    codol_structured_path_t path[4];codol_profile_loadout_t next;unsigned w,i;
    struct {const char *name;int *field;} singles[5];
    if(!out || class_index>=CODOL_LOADOUT_CLASSES)return -1;
    if(!CODOL_ScriptProfileView(client,CODOL_PROFILE_PUBLIC,&d,&record,&capacity))return 0;
    memset(&next,0,sizeof(next));
    path[0]=(codol_structured_path_t){"weaponClasses",0};
    path[1]=(codol_structured_path_t){NULL,(int32_t)class_index};
    singles[0].name="deathstreak";singles[0].field=&next.deathstreak;
    singles[1].name="lethal";singles[1].field=&next.lethal;
    singles[2].name="tactical";singles[2].field=&next.tactical;
    singles[3].name="special";singles[3].field=&next.special;
    singles[4].name="meleeWpn";singles[4].field=&next.melee;
    for(i=0;i<5;++i) {
        path[2]=(codol_structured_path_t){singles[i].name,0};
        if(!read_short(d,record,capacity,path,3,singles[i].field))return -1;
        /* C1 equipment UI uses actual marketplace ID + 1 in playerdata.
         * Setter 590ae0 increments at 590b56; getter 590bc0 decrements at
         * 590c8a after the signed-short reader 5906e2. Member table cd234c
         * contains lethal, special, tactical, meleeWpn. Decode only these
         * proven leaves: stored0 is empty(-1), stored1227 is item1226.
         * Deathstreak UI 6be71f uses the same getter. Keep raw profile
         * storage unchanged; decode only this loadout view. */
        --*singles[i].field;
    }
    for(w=0;w<CODOL_LOADOUT_WEAPONS;++w) {
        path[2]=(codol_structured_path_t){bases[w],0};
        if(!read_short(d,record,capacity,path,3,&next.base[w]))return -1;
        path[2]=(codol_structured_path_t){attach[w],0};
        for(i=0;i<CODOL_LOADOUT_ATTACHMENTS;++i) {
            path[3]=(codol_structured_path_t){NULL,(int32_t)i};
            if(!read_short(d,record,capacity,path,4,&next.attachments[w][i]))return -1;
        }
    }
    path[2]=(codol_structured_path_t){"perks",0};
    for(i=0;i<CODOL_LOADOUT_PERKS;++i) {
        path[3]=(codol_structured_path_t){NULL,(int32_t)i};
        if(!read_short(d,record,capacity,path,4,&next.perks[i]))return -1;
        /* C1 getter 591488 / setter 59173a use the same ID+1 codec. */
        --next.perks[i];
    }
    path[2]=(codol_structured_path_t){"killstreaks",0};
    for(i=0;i<CODOL_LOADOUT_KILLSTREAKS;++i) {
        path[3]=(codol_structured_path_t){NULL,(int32_t)i};
        if(!read_short(d,record,capacity,path,4,&next.killstreaks[i]))return -1;
        /* C1 getter 5914ba / setter 591764 use the same ID+1 codec. */
        --next.killstreaks[i];
    }
    *out=next;return 1;
}
int CODOL_LoadoutItemName(int item,const char **name,const char **type,const char **group)
{
    const codol_engine_table_t *market=NULL;codol_character_item_t entry;int status;
    if(slot_empty(item) || item>0xffff)return 0;
    status=CODOL_LoadEngineStringTable(MARKETPLACE_TABLE,&market);
    if(status!=1)return -1;
    status=CODOL_CharacterItem(market,(uint16_t)item,&entry);
    if(status<0)return -1;
    if(status!=1 || !entry.name || !*entry.name)return 0;
    if(name)*name=entry.name;
    if(type)*type=entry.type;
    if(group)*group=entry.group;
    return 1;
}
int CODOL_LoadoutAttachmentItemIndex(int item,unsigned *index)
{
    const codol_engine_table_t *market=NULL;char key[8];int r,found=-1;
    unsigned ordinal=0,resolved=0;
    if(!index || slot_empty(item) || item>0xffff)return 0;
    if(CODOL_LoadEngineStringTable(MARKETPLACE_TABLE,&market)!=1)return -1;
    if(!market || market->rowCount<0 || market->columnCount<3 ||
       (market->rowCount && !market->values))return -1;
    snprintf(key,sizeof(key),"%d",item);
    /* C1's id lookup takes the last matching row, and its attachment numbering
     * counts the "wat" rows in table order starting at one. Walk once and keep
     * the ordinal belonging to the last row that carries this id. */
    for(r=0;r<market->rowCount;++r) {
        const char *const *cells=market->values+(size_t)r*market->columnCount;
        if(!cells[0] || !cells[2]) return -1;
        if(!strcmp(cells[2],"wat")) ++ordinal;
        /* Select the last ID row across all item types, then classify it.
         * An older wat row cannot win over a later non-attachment row. */
        if(!strcmp(cells[0],key)) {
            found=r; resolved=!strcmp(cells[2],"wat") ? ordinal : 0;
        }
    }
    if(found<0 || !resolved)return 0;
    *index=resolved;return 1;
}
int CODOL_LoadoutWeaponIndex(const char *name,unsigned *index)
{
    const codol_engine_table_t *table=NULL;int r,q,published=-1;unsigned next=2;
    if(!index || !name || !*name)return 0;
    /* The slot the server actually published wins: the client resolves a base
     * index against the weapons it holds, and CS_WEAPONS slot i carries index
     * i. CODOL_InitializeServerWeaponConfigstrings builds that list from the
     * same table in the same order, so the fallback below agrees with it when
     * the registry is not up yet. */
#ifdef CODOL_SERVER
    {
        const codol_weapon_registry_t *registry=CODOL_ServerWeaponRegistry();
        if(registry) {
            published=CODOL_FindRegisteredWeapon(registry,name);
            if(published<0) return 0;
        }
    }
#endif
    if(published>=0){*index=(unsigned)published;return 1;}
    if(!strcmp(name,"none")){*index=0;return 1;}
    if(!strcmp(name,"defaultweapon_mp")){*index=1;return 1;}
    if(CODOL_LoadEngineStringTable(ATTACHMENT_TABLE,&table)!=1)return -1;
    if(!table || table->rowCount<0 || table->columnCount<1 ||
       (table->rowCount && !table->values))return -1;
    /* C1 registers a weapon when the row's name differs from the previous row
     * (0x41fbed..0x41fc0c) and BG_GetWeaponIndexForName returns the existing
     * index for a name it already holds, so the numbering is first appearance
     * in row order. The table is grouped by weapon, which is why the previous
     * name is checked before the scan. */
    for(r=0;r<table->rowCount;++r) {
        const char *const *cells=table->values+(size_t)r*table->columnCount;
        const char *previous=NULL;
        int seen=0;
        if(!cells[0] || !*cells[0])continue;
        if(r) {
            const char *const *before=table->values+(size_t)(r-1)*table->columnCount;
            previous=before[0];
        }
        if(previous && *previous && !strcmp(previous,cells[0]))continue;
        for(q=0;q<r-1 && !seen;++q) {
            const char *const *earlier=table->values+(size_t)q*table->columnCount;
            seen=earlier[0] && *earlier[0] && !strcmp(earlier[0],cells[0]);
        }
        if(seen)continue;
        if(!strcmp(cells[0],name)){*index=next;return 1;}
        ++next;
    }
    return 0;
}
typedef struct {
    codol_loadout_recipe_t *recipe;
    char pairs[CODOL_COMPOSED_NAME_SIZE];
    size_t length;  /* rendered length of pairs */
    size_t reserve; /* longest header this base index can render */
} compose_state_t;
/* One model per bone tag: DObjCreateSkelForBones binds a bone by name and
 * takes the first match, and nothing on the client side dedupes, so two parts
 * naming one tag are merged into the same place. The rule is only ever applied
 * to the parts this module adds itself. A class's own equipped choice is never
 * held back for it: the tag collision has no measured connection to the build
 * failures it was once blamed for, and the one composed spec measured to
 * render contains one (rai_default and for_default, both TAG_FOREGRIP). */
static int tag_taken(const codol_loadout_recipe_t *recipe,const char *tag)
{
    unsigned i;
    if(!tag || !*tag)return 0;
    for(i=0;i<recipe->count;++i)
        if(recipe->parts[i].tag && !strcmp(recipe->parts[i].tag,tag))return 1;
    return 0;
}
static int group_present(const codol_loadout_recipe_t *recipe,const char *group)
{
    unsigned i;
    if(!group || !*group)return 0;
    for(i=0;i<recipe->count;++i)
        if(recipe->parts[i].group && !strcmp(recipe->parts[i].group,group))return 1;
    return 0;
}
static int item_present(const codol_loadout_recipe_t *recipe,unsigned item)
{
    unsigned i;
    for(i=0;i<recipe->count;++i)if(recipe->parts[i].item==item)return 1;
    return 0;
}
/* Append one pair. required marks the class's own choice, which is an error to
 * lose rather than something to count and move on from. 1 emitted, 0 held
 * back, -1 a required pair did not fit. */
static int append_part(compose_state_t *state,unsigned item,unsigned variant,
    const char *name,const char *group,const char *tag,
    codol_loadout_part_origin_t origin,int required)
{
    codol_loadout_recipe_t *recipe=state->recipe;
    codol_loadout_part_t *part;int written;
    if(recipe->count>=CODOL_COMPOSED_ATTACHMENTS) {
        if(required)return -1;
        ++recipe->skipped_full;return 0;
    }
    written=snprintf(state->pairs+state->length,sizeof(state->pairs)-state->length,
        " %u %u",item,variant);
    if(written<0 || (size_t)written>=sizeof(state->pairs)-state->length ||
       state->reserve+state->length+(size_t)written+1u>sizeof(recipe->name)) {
        state->pairs[state->length]=0;
        if(required)return -1;
        ++recipe->skipped_full;return 0;
    }
    state->length+=(size_t)written;
    part=&recipe->parts[recipe->count++];
    part->item=item;part->variant=variant;part->name=name;part->group=group;
    part->tag=tag && *tag ? tag : NULL;part->origin=origin;
    return 1;
}
/* Resolve a part named rather than stored: its attachment index, its group and
 * its variant on this weapon. 1 usable, 0 not legal here, -1 table failure. */
static int resolve_named_part(const char *base_name,const char *item_name,
    unsigned *item,unsigned *variant,const char **group)
{
    int status=CODOL_ComposedAttachmentItemIndex(item_name,item,group);
    if(status!=1)return status;
    return CODOL_ComposedAttachmentVariant(base_name,item_name,variant);
}
int CODOL_ComposeLoadoutWeaponRecipe(int base_item,const int *attachments,unsigned count,
    codol_loadout_recipe_t *out)
{
    codol_weapon_default_slot_t defaults[CODOL_COMPOSED_ATTACHMENTS];
    codol_loadout_recipe_t recipe;compose_state_t state;
    const char *name,*type;unsigned base_index,declared=0,i,j;int status,written;
    char header[32];
    if(!out || count>CODOL_LOADOUT_ATTACHMENTS || (count && !attachments))return -1;
    status=CODOL_LoadoutItemName(base_item,&name,&type,NULL);
    if(status!=1)return status;
    if(!type || strcmp(type,"wea"))return 0;
    status=CODOL_LoadoutWeaponIndex(name,&base_index);
    if(status!=1)return status;
    if(!base_index)return 0;
    memset(&recipe,0,sizeof(recipe));
    recipe.base_name=name;recipe.base_index=base_index;
    recipe.composition_base_name=name;recipe.composition_base_index=base_index;
    memset(&state,0,sizeof(state));
    state.recipe=&recipe;
    /* Reserve the longest header this base can render, because the flag is not
     * known until the last camo lift has happened. */
    written=snprintf(header,sizeof(header),"*a %u 255",base_index);
    if(written<0 || (size_t)written>=sizeof(header))return -1;
    state.reserve=(size_t)written;
    /* --- the class's own choices, in the order the profile stores them ---- */
    for(i=0;i<count;++i) {
        const char *item_name=NULL,*group=NULL,*tag=NULL;
        unsigned item,variant;
        /* An empty slot is genuinely empty and is skipped. A stored id that
         * does not resolve is a failure: dropping it would hand the player a
         * weapon missing an attachment they own, with nothing reported. */
        if(slot_empty(attachments[i]))continue;
        if(CODOL_LoadoutItemName(attachments[i],&item_name,&type,&group)!=1)return -1;
        if(!type || strcmp(type,"wat"))return -1;
        if(CODOL_LoadoutAttachmentItemIndex(attachments[i],&item)!=1)return -1;
        /* The profile keys slots by group label, and a label can disagree with
         * the item it holds, so the same item can appear twice. Emitting it
         * twice would resolve it twice on the client. */
        if(item_present(&recipe,item)){++recipe.skipped_duplicate;continue;}
        /* Legality is the presence of the (weapon, item) row, and the same row
         * carries the pair's variant. An item this weapon has no row for
         * resolves to nothing in bg_attachIdx, so emitting it would only take
         * up one of the fifteen pair slots. */
        status=CODOL_ComposedAttachmentVariant(name,item_name,&variant);
        if(status<0)return -1;
        if(status!=1)return -1;
        if(CODOL_ComposedAttachmentTag(name,item_name,group,&tag)<0)return -1;
        if(tag_taken(&recipe,tag))++recipe.collisions;
        if(group && !strcmp(group,"cam")) {
            /* THE CAMO LIFT. The id is the one mp/coweapitems/cam.csv gives
             * this item on this weapon, which is the row space of
             * mp/coweapmodels/<weapon>.csv. The pair's own variant is a
             * different byte and is zero for every premium camo, so lifting it
             * would draw the plain base gun for every one of them. The pair is
             * still emitted: it carries the stat overrides too, and it merges
             * no model, so it can never take a bone from anything. */
            if(CODOL_ComposedCamoId(name,item_name,(int)variant,
                   &recipe.flag,&recipe.camo_source)<0)return -1;
            recipe.camo_item=item_name;
        }
        if(append_part(&state,item,variant,item_name,group,tag,
               CODOL_LOADOUT_PART_EQUIPPED,1)<0)return -1;
    }
    /* --- the weapon's own declared defaults, for the groups still empty --- */
    status=CODOL_WeaponDeclaredDefaults(name,defaults,
        sizeof(defaults)/sizeof(*defaults),&declared);
    if(status<0)return -1;
    if(status!=1)declared=0;
    for(i=0;i<declared;++i) {
        const char *group=NULL,*tag=NULL,*part_name=defaults[i].item;unsigned item,variant;
        /* The player's own choice always wins its slot: a class that equips
         * mag_extusp has filled the mag group and must not also be handed
         * mag_default. Both the item's marketplace group and the record's own
         * slot label are checked, because a record can label a group with the
         * slot name rather than the item's group. */
        if(group_present(&recipe,defaults[i].slot))continue;
        status=resolve_named_part(name,part_name,&item,&variant,&group);
        if(status<0)return -1;
        if(status!=1) {
            /* Some shipped declarations name a generic visual that has no
             * legal pair for this weapon. Example: m9_mp declares
             * iro_default, while its own attachment/model tables offer
             * iro_glowm9. Resolve a neutral model-producing item from the
             * same declared group instead of building a DObj with a missing
             * core bone or aborting the match. */
            group=defaults[i].slot;
            status=CODOL_ComposedLegalDefaultReplacement(name,group,
                &part_name,&item,&variant);
            if(status<0)return -1;
            if(status!=1)continue;
        }
        if(group_present(&recipe,group))continue;
        if(item_present(&recipe,item))continue;
        if(CODOL_ComposedAttachmentTag(name,part_name,group,&tag)<0)return -1;
        if(append_part(&state,item,variant,part_name,group,tag,
               CODOL_LOADOUT_PART_DECLARED,1)!=1)return -1;
        /* A weapon whose own record declares a camo (cartevent -> cam_gold,
         * m4a1techevent -> cam_tiger) wears it when the class chose none, so
         * the flag agrees with the pair that was just emitted instead of
         * leaving an event gun on its plain base row. Only a declared default
         * lifts; the filler camo above never does. */
        if(!recipe.camo_item && !strncmp(part_name,"cam_",4)) {
            if(CODOL_ComposedCamoId(name,part_name,(int)variant,
                   &recipe.flag,&recipe.camo_source)<0)return -1;
            recipe.camo_item=part_name;
        }
    }
    /* --- what the build still leaves uncovered, for the caller to report -- */
    for(i=0;i<declared;++i) {
        const char *group=NULL;unsigned item;
        if(group_present(&recipe,defaults[i].slot))continue;
        if(CODOL_ComposedAttachmentItemIndex(defaults[i].item,&item,&group)==1) {
            if(group_present(&recipe,group) || item_present(&recipe,item))continue;
        }
        for(j=0;j<recipe.count;++j)
            if(recipe.parts[j].name && !strcmp(recipe.parts[j].name,defaults[i].item))break;
        if(j==recipe.count)++recipe.missing_defaults;
    }
#ifdef CODOL_SERVER
    status=CODOL_EventFastMagCompositionBase(&recipe,&recipe.composition_base_index);
    if(status<0)Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL fastmag: equivalent composition could not be verified for %s; preserving selected recipe\n",
        recipe.base_name);
    if(status==1)recipe.composition_base_name="m4a1tech_mp";
#endif
    /* The single spelling this server emits: one space before every number.
     * C1's parser (0x421590) accepts other spacings; 0x420580 turned out to be
     * the alt-mode name builder rather than a canonicaliser, so no re-emission
     * rule is claimed from it. codol_weapon_compose keys its definitions by
     * this same rendering. */
    written=snprintf(recipe.name,sizeof(recipe.name),"*a %u %u%s",
        recipe.composition_base_index,recipe.flag,state.pairs);
    if(written<0 || (size_t)written>=sizeof(recipe.name))return -1;
    /* The art the flag actually selects, so a caller can tell a composed gun
     * that resolves CoDOL runtime art from one that resolves nothing. */
    CODOL_ComposedBaseModelRow(name,recipe.flag,
        &recipe.base_world_model,&recipe.base_view_model);
    *out=recipe;return 1;
}
int CODOL_ComposeLoadoutWeapon(int base_item,const int *attachments,unsigned count,
    char *out,size_t size)
{
    codol_loadout_recipe_t recipe;int status;size_t n;
    if(!out || !size)return -1;
    status=CODOL_ComposeLoadoutWeaponRecipe(base_item,attachments,count,&recipe);
    if(status!=1)return status;
    n=strlen(recipe.name)+1;
    if(n>size)return -1;
    memcpy(out,recipe.name,n);return 1;
}
/* A shipped declaration is not the same thing as an available C1 pair.
 * wa2000_mp declares gri_default in mp/coweapitemswea.csv, but neither
 * mp/coWeaponAttachmentTable.csv nor mp/coweapitems/gri.csv gives this weapon
 * any grip at all, so that group can never be covered and no legal replacement
 * exists in it either. C1 composes the gun regardless; rejecting the recipe
 * publishes the plain stock base instead, whose gunXModel[0] is the shipped
 * IW4-style body - the wrong-model failure docs/CODOL_NATIVE_WEAPON_MAPPING.md
 * describes as "publishing only a stock base index can select the shipped
 * IW4-style fallback mesh".
 *
 * 1 only when every uncovered declared group is that case. A group whose own
 * pair IS legal for this weapon, or which has a legal replacement in it, means
 * the composer dropped something it could have emitted; that stays an error.
 *
 * Both loadout producers gate on this one implementation - the bot table
 * bridge (codol_bot_loadout.c) and the human profile bridge below - so a
 * weapon cannot compose for a bot and degrade to its stock body for the player
 * holding the identical recipe. */
int CODOL_LoadoutMissingDefaultsUnconstructible(const codol_loadout_recipe_t *recipe)
{
    codol_weapon_default_slot_t defaults[CODOL_COMPOSED_ATTACHMENTS];
    unsigned count=0,i,j,unconstructible=0;
    if(!recipe || !recipe->base_name || !*recipe->base_name)return 0;
    if(CODOL_WeaponDeclaredDefaults(recipe->base_name,defaults,
        CODOL_COMPOSED_ATTACHMENTS,&count)!=1)return 0;
    for(i=0;i<count;++i){
        const char *group=NULL,*replacement=NULL;unsigned item=0,variant=0;int found=0,status;
        status=CODOL_ComposedAttachmentItemIndex(defaults[i].item,&item,&group);
        if(status<0)return 0;
        for(j=0;j<recipe->count;++j){
            const codol_loadout_part_t *part=&recipe->parts[j];
            if((part->group && !strcmp(part->group,defaults[i].slot)) ||
               (group && part->group && !strcmp(part->group,group)) ||
               (status==1 && part->item==item) ||
               (part->name && !strcmp(part->name,defaults[i].item))){found=1;break;}
        }
        if(found)continue;
        /* A legal pair missing from output would be a composer defect. */
        if(CODOL_ComposedAttachmentVariant(recipe->base_name,defaults[i].item,&variant)!=0)return 0;
        status=CODOL_ComposedLegalDefaultReplacement(recipe->base_name,defaults[i].slot,
            &replacement,&item,&variant);
        if(status!=0)return 0;
        ++unconstructible;
    }
    return unconstructible==recipe->missing_defaults;
}
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
/* Empty and unresolvable slots answer with the name IW4's own class table uses
 * for an absent choice. That is a representation of "this slot holds nothing",
 * not a substituted item: no default weapon, perk or attachment is invented. */
static const char loadout_none[]="none";
/* codol_getLoadoutWeapon runs on the human's own spawn/class-change path
 * (maps/mp/gametypes/_class.gsc -> _menus.gsc menuresponse -> spawnClient), so
 * a script exception there unwinds spawnClient and ends the match for
 * everybody. Every optional-data and capacity failure in that getter therefore
 * degrades to a weapon that is safe to hand back and warns once per slot; only
 * script-contract violations (wrong receiver, wrong argument type or range)
 * still raise.
 *
 * "Safe" is not the same as "stock": a stock name the native table does not
 * already hold still costs a definition slot, because giveWeapon resolves it
 * through BG_GetWeaponIndexForName, which registers. On a full table that is
 * precisely what overflows the engine->wire map and drops the server.
 * CODOL_SafeStockWeapon answers the name only when there is room for it or it
 * is already live, and "none" otherwise. */
static unsigned loadout_weapon_warned;
/* Separate latch: the unconstructible-default notice is a data observation
 * about the weapon, not a degradation, so it must not silence a later real
 * fallback warning for the same slot. */
static unsigned loadout_default_warned;
static void loadout_weapon_fallback(const char *method,unsigned weapon,
    const char *base,const char *why)
{
    const char *answer=CODOL_SafeStockWeapon(base);
    unsigned bit=1u<<(weapon&31u);
    if(!(loadout_weapon_warned&bit)) {
        loadout_weapon_warned|=bit;
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL loadout: %s slot %u: %s; using %s\n",
            method,weapon,why,answer);
    }
    Scr_AddString(answer);
}
static int loadout_entity(scr_entref_t ref,const char *method,unsigned *client)
{
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].client ||
       !g_entities[ref.entnum].r.inuse) {
        Scr_Error(va("%s: entity must be a player entity",method));return 0;
    }
    *client=ref.entnum;return 1;
}
static int loadout_for(scr_entref_t ref,const char *method,unsigned parameters,
    codol_profile_loadout_t *out)
{
    unsigned client;int class_index,status;
    if(!loadout_entity(ref,method,&client))return 0;
    if((unsigned)Scr_GetNumParam()!=parameters) {
        Scr_Error(va("%s requires %u parameters",method,parameters));return 0;
    }
    if(Scr_GetType(0)!=VAR_INTEGER) {
        Scr_ParamError(0,va("%s: class index must be an integer",method));return 0;
    }
    class_index=Scr_GetInt(0);
    if(class_index<0 || (unsigned)class_index>=CODOL_LOADOUT_CLASSES) {
        Scr_ParamError(0,va("%s: class index must be 0..%u",method,CODOL_LOADOUT_CLASSES-1));
        return 0;
    }
    status=CODOL_ReadProfileLoadout(client,(unsigned)class_index,out);
    if(status==1)return 1;
    if(!status)Scr_Error(va("%s: this player has no complete profile upload, or "
        "mp/playerdata.def is not mounted",method));
    else Scr_Error(va("%s: mp/playerdata.def does not describe weaponClasses[%d] "
        "as this build reads it",method,class_index));
    return 0;
}
/* loadout_for raises on an unusable profile, which is right for the query
 * getters a script calls defensively but fatal for the weapon getter: that one
 * runs inside spawnClient, so its exception ends the match. This is the same
 * validation with the profile read *reported* instead of thrown.
 * 1 ok, 0 the caller has already raised a script-contract violation,
 * -1 the profile is unusable and the caller must degrade. */
static int loadout_for_optional(scr_entref_t ref,const char *method,unsigned parameters,
    codol_profile_loadout_t *out)
{
    unsigned client;int class_index;
    if(!loadout_entity(ref,method,&client))return 0;
    if((unsigned)Scr_GetNumParam()!=parameters) {
        Scr_Error(va("%s requires %u parameters",method,parameters));return 0;
    }
    if(Scr_GetType(0)!=VAR_INTEGER) {
        Scr_ParamError(0,va("%s: class index must be an integer",method));return 0;
    }
    class_index=Scr_GetInt(0);
    if(class_index<0 || (unsigned)class_index>=CODOL_LOADOUT_CLASSES) {
        Scr_ParamError(0,va("%s: class index must be 0..%u",method,CODOL_LOADOUT_CLASSES-1));
        return 0;
    }
    return CODOL_ReadProfileLoadout(client,(unsigned)class_index,out)==1 ? 1:-1;
}
static int loadout_index(const char *method,unsigned parameter,unsigned limit,unsigned *out)
{
    int value;
    if(Scr_GetType(parameter)!=VAR_INTEGER) {
        Scr_ParamError((int)parameter,va("%s: index must be an integer",method));return 0;
    }
    value=Scr_GetInt(parameter);
    if(value<0 || (unsigned)value>=limit) {
        Scr_ParamError((int)parameter,va("%s: index must be 0..%u",method,limit-1));return 0;
    }
    *out=(unsigned)value;return 1;
}
/* A stale/unknown optional item must not abort the whole spawn thread. C1 can
 * receive profiles newer than the mounted marketplace table; class scripts
 * already validate "none" / specialty_null and select their stock fallback. */
static void push_typed_item(const char *method,int item,const char *expected_type)
{
    const char *name=NULL,*type=NULL;
    const char *fallback=expected_type &&
        (!strcmp(expected_type,"per") || !strcmp(expected_type,"des")) ?
        "specialty_null" : loadout_none;
    int status;
    if(slot_empty(item)){Scr_AddString(fallback);return;}
    status=CODOL_LoadoutItemName(item,&name,&type,NULL);
    if(status<0) {
        Scr_Error(va("%s: " MARKETPLACE_TABLE " is not mounted or is malformed",method));return;
    }
    if(status!=1) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "%s: stored item %d has no marketplace row; using %s\n",
            method,item,fallback);
        Scr_AddString(fallback);return;
    }
    if(expected_type && (!type || strcmp(type,expected_type))) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "%s: stored item %d is not type %s; using %s\n",
            method,item,expected_type,fallback);
        Scr_AddString(fallback);return;
    }
    Scr_AddString(name);
}
static void push_item(const char *method,int item)
{ push_typed_item(method,item,NULL); }
/* <player> codol_getLoadoutItem( <class>, <member> ) */
void CODOL_Scr_GetLoadoutItem(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutItem";
    codol_profile_loadout_t loadout;const char *member;unsigned i;
    static const char *const names[]={"primaryBase","secondaryBase","lethal","tactical",
        "special","meleeWpn","deathstreak"};
    const int *values[7];
    if(!loadout_for(ref,method,2,&loadout))return;
    if(Scr_GetType(1)!=VAR_STRING && Scr_GetType(1)!=VAR_ISTRING) {
        Scr_ParamError(1,va("%s: member must be a name",method));return;
    }
    member=Scr_GetString(1);
    values[0]=&loadout.base[0];values[1]=&loadout.base[1];values[2]=&loadout.lethal;
    values[3]=&loadout.tactical;values[4]=&loadout.special;values[5]=&loadout.melee;
    values[6]=&loadout.deathstreak;
    for(i=0;i<sizeof(names)/sizeof(*names);++i)
        if(member && !strcmp(member,names[i])) {
            if(i>=2 && i<=4)
                Com_DPrintf(CON_CHANNEL_SERVER,
                    "CoDOL profile equipment: client %u class %d member %s item %d\n",
                    (unsigned)ref.entnum,Scr_GetInt(0),names[i],*values[i]);
            /* An empty deathstreak is a null perk, not a weapon named none.
             * Keep the perk sentinel used by the spawn/deathstreak lifecycle. */
            if(i==6) push_typed_item(method,*values[i],"des");
            else push_item(method,*values[i]);
            return;
        }
    Scr_ParamError(1,va("%s: weaponClasses has no scalar member \"%s\" this bridge exposes",
        method,member ? member : ""));
}
/* <player> codol_getLoadoutPerk( <class>, <0..4> ) */
void CODOL_Scr_GetLoadoutPerk(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutPerk";
    codol_profile_loadout_t loadout;unsigned index;
    if(!loadout_for(ref,method,2,&loadout))return;
    if(!loadout_index(method,1,CODOL_LOADOUT_PERKS,&index))return;
    if(index<3 && !slot_empty(loadout.perks[index])) {
        static const char *const groups[]={"pk1","pk2","pk3"};
        const char *group=NULL;
        int status=CODOL_LoadoutItemName(loadout.perks[index],NULL,NULL,&group);
        if(status==1 && (!group || strcmp(group,groups[index]))) {
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "%s: stored item %d is not in group %s; using specialty_null\n",
                method,loadout.perks[index],groups[index]);
            Scr_AddString("specialty_null");return;
        }
    }
    push_typed_item(method,loadout.perks[index],"per");
}
/* <player> codol_getLoadoutKillstreak( <class>, <0..3> ) */
void CODOL_Scr_GetLoadoutKillstreak(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutKillstreak";
    codol_profile_loadout_t loadout;unsigned index;
    if(!loadout_for(ref,method,2,&loadout))return;
    if(!loadout_index(method,1,CODOL_LOADOUT_KILLSTREAKS,&index))return;
    {
        const char *name=NULL,*type=NULL;
        int status=CODOL_LoadoutItemName(loadout.killstreaks[index],&name,&type,NULL);
        Com_DPrintf(CON_CHANNEL_SERVER,
            "CoDOL selected killstreak: client %u class %d slot %u item %d name %s type %s\n",
            (unsigned)ref.entnum,Scr_GetInt(0),index,loadout.killstreaks[index],
            status==1 && name ? name : "none",status==1 && type ? type : "none");
    }
    push_typed_item(method,loadout.killstreaks[index],"kis");
}
/* <player> codol_getLoadoutAttachment( <class>, <weapon 0..1>, <slot 0..14> ) */
void CODOL_Scr_GetLoadoutAttachment(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutAttachment";
    codol_profile_loadout_t loadout;unsigned weapon,slot;
    if(!loadout_for(ref,method,3,&loadout))return;
    if(!loadout_index(method,1,CODOL_LOADOUT_WEAPONS,&weapon))return;
    if(!loadout_index(method,2,CODOL_LOADOUT_ATTACHMENTS,&slot))return;
    push_typed_item(method,loadout.attachments[weapon][slot],"wat");
}
/* <player> codol_getLoadoutAttachments( <class>, <weapon 0..1> )
 * All fifteen slots in definition order, so slot positions survive the call. */
void CODOL_Scr_GetLoadoutAttachments(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutAttachments";
    codol_profile_loadout_t loadout;unsigned weapon,slot;
    const char *names[CODOL_LOADOUT_ATTACHMENTS];
    if(!loadout_for(ref,method,2,&loadout))return;
    if(!loadout_index(method,1,CODOL_LOADOUT_WEAPONS,&weapon))return;
    for(slot=0;slot<CODOL_LOADOUT_ATTACHMENTS;++slot) {
        const char *name=NULL,*type=NULL;int status;
        if(slot_empty(loadout.attachments[weapon][slot])){names[slot]=loadout_none;continue;}
        status=CODOL_LoadoutItemName(loadout.attachments[weapon][slot],&name,&type,NULL);
        if(status<0) {
            Scr_Error(va("%s: " MARKETPLACE_TABLE " is not mounted or is malformed",method));return;
        }
        if(status!=1) {
            Scr_Error(va("%s: stored attachment %d in slot %u has no row in " MARKETPLACE_TABLE,
                method,loadout.attachments[weapon][slot],slot));
            return;
        }
        if(!type || strcmp(type,"wat")) {
            Scr_Error(va("%s: stored item %d in slot %u is not an attachment",method,
                loadout.attachments[weapon][slot],slot));return;
        }
        names[slot]=name;
    }
    Scr_MakeArray();
    for(slot=0;slot<CODOL_LOADOUT_ATTACHMENTS;++slot) {
        Scr_AddString(names[slot]);
        Scr_AddArray();
    }
}
/* <player> codol_getLoadoutCamo( <class>, <weapon 0..1> )
 * Camo is an attachment item like any other; it is identified by its own
 * marketplace group rather than by a fixed slot number. */
void CODOL_Scr_GetLoadoutCamo(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutCamo";
    codol_profile_loadout_t loadout;unsigned weapon,slot;
    if(!loadout_for(ref,method,2,&loadout))return;
    if(!loadout_index(method,1,CODOL_LOADOUT_WEAPONS,&weapon))return;
    for(slot=0;slot<CODOL_LOADOUT_ATTACHMENTS;++slot) {
        const char *name=NULL,*group=NULL;
        int status;
        if(slot_empty(loadout.attachments[weapon][slot])) continue;
        status=CODOL_LoadoutItemName(loadout.attachments[weapon][slot],&name,NULL,&group);
        if(status<0) {
            Scr_Error(va("%s: " MARKETPLACE_TABLE " is not mounted or is malformed",method));return;
        }
        if(status!=1) {
            Scr_Error(va("%s: stored attachment %d has no marketplace row",method,
                loadout.attachments[weapon][slot]));return;
        }
        if(status==1 && group && !strcmp(group,"cam")){Scr_AddString(name);return;}
    }
    Scr_AddString(loadout_none);
}
/* <player> codol_getLoadoutItemType( <class>, <member> )
 * The marketplace type column of a stored slot: "wea", "wat", and the
 * equipment/perk/killstreak codes the table carries. Scripts use it to decide
 * whether a slot holds something they can give, instead of guessing from the
 * name. An empty slot answers "none". */
void CODOL_Scr_GetLoadoutItemType(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutItemType";
    codol_profile_loadout_t loadout;const char *member,*type=NULL;unsigned i;int item;
    static const char *const names[]={"primaryBase","secondaryBase","lethal","tactical",
        "special","meleeWpn","deathstreak"};
    const int *values[7];int status;
    if(!loadout_for(ref,method,2,&loadout))return;
    if(Scr_GetType(1)!=VAR_STRING && Scr_GetType(1)!=VAR_ISTRING) {
        Scr_ParamError(1,va("%s: member must be a name",method));return;
    }
    member=Scr_GetString(1);
    values[0]=&loadout.base[0];values[1]=&loadout.base[1];values[2]=&loadout.lethal;
    values[3]=&loadout.tactical;values[4]=&loadout.special;values[5]=&loadout.melee;
    values[6]=&loadout.deathstreak;
    for(i=0;i<sizeof(names)/sizeof(*names);++i)
        if(member && !strcmp(member,names[i])) {
            item=*values[i];
            if(slot_empty(item)){Scr_AddString(loadout_none);return;}
            status=CODOL_LoadoutItemName(item,NULL,&type,NULL);
            if(status<0) {
                Scr_Error(va("%s: " MARKETPLACE_TABLE " is not mounted or is malformed",method));return;
            }
            if(status!=1 || !type) {
                Scr_Error(va("%s: stored item %d has no row in " MARKETPLACE_TABLE,method,item));return;
            }
            Scr_AddString(type);return;
        }
    Scr_ParamError(1,va("%s: weaponClasses has no scalar member \"%s\" this bridge exposes",
        method,member ? member : ""));
}
/* codol_getWeaponBaseName( <weapon> )
 * IW4's getBaseWeaponName splits on underscores, which a composed name has
 * none of. This answers the base weapon of a composed name and returns any
 * other name unchanged, so callers stop deriving nonsense from "*a 25 0 ...". */
void CODOL_Scr_GetWeaponBaseName(void)
{
    static const char method[]="codol_getWeaponBaseName";
    codol_composed_weapon_t record;const char *name,*base=NULL;int status;
    if(Scr_GetNumParam()!=1){Scr_Error(va("%s requires one weapon name",method));return;}
    name=Scr_GetString(0);
    if(!name){Scr_ParamError(0,va("%s requires one weapon name",method));return;}
    status=CODOL_ParseComposedWeaponName(name,&record);
    if(status==0){Scr_AddString(name);return;}
    if(status<0){Scr_ParamError(0,va("%s: malformed composed weapon name",method));return;}
    if(CODOL_ComposedWeaponBaseName(record.base,&base)!=1 || !base) {
        Scr_Error(va("%s: composed base index %u is not a published weapon",method,record.base));return;
    }
    Scr_AddString(base);
}
/* codol_getWeaponAttachmentNames( <weapon> )
 * The attachment item names a composed name carries, in the order it carries
 * them. A non-composed name answers an empty array rather than the result of
 * splitting it on underscores. */
void CODOL_Scr_GetWeaponAttachmentNames(void)
{
    static const char method[]="codol_getWeaponAttachmentNames";
    codol_composed_weapon_t record;const char *name;
    const char *items[CODOL_COMPOSED_ATTACHMENTS];unsigned i;int status;
    if(Scr_GetNumParam()!=1){Scr_Error(va("%s requires one weapon name",method));return;}
    name=Scr_GetString(0);
    if(!name){Scr_ParamError(0,va("%s requires one weapon name",method));return;}
    status=CODOL_ParseComposedWeaponName(name,&record);
    if(status<0){Scr_ParamError(0,va("%s: malformed composed weapon name",method));return;}
    if(status==0){Scr_MakeArray();return;}
    for(i=0;i<record.count;++i) {
        const char *item=NULL;
        int found=CODOL_ComposedAttachmentItemName(record.items[i],&item);
        if(found<0) {
            Scr_Error(va("%s: " MARKETPLACE_TABLE " is not mounted or is malformed",method));return;
        }
        if(found!=1) {
            Scr_Error(va("%s: attachment item index %u has no row in " MARKETPLACE_TABLE,
                method,record.items[i]));
            return;
        }
        items[i]=item;
    }
    Scr_MakeArray();
    for(i=0;i<record.count;++i) {
        Scr_AddString(items[i]);
        Scr_AddArray();
    }
}
/* <player> codol_getLoadoutWeapon( <class>, <weapon 0..1> )
 * The composed custom weapon name carrying the base and every populated
 * attachment slot, which is what lets the loadout survive without being cut
 * down to two attachments.
 *
 * A composed name can only be given once it occupies a weapon slot the server
 * has published, because that slot is what the client resolves the name from.
 * This getter builds and publishes the composed definition before returning
 * its name. Weapons without composable CoDOL art keep their stock base, as C1
 * does; a bad optional recipe must not terminate the match. */
void CODOL_Scr_GetLoadoutWeapon(scr_entref_t ref)
{
    static const char method[]="codol_getLoadoutWeapon";
    codol_profile_loadout_t loadout;unsigned weapon,slot;
    codol_loadout_recipe_t recipe;const char *name;
    const char *base=NULL;const struct WeaponDef *composed=NULL;int status;
    status=loadout_for_optional(ref,method,2,&loadout);
    if(!status)return;
    if(status<0) {
        /* The parameter count is already validated, so the slot is readable. */
        if(!loadout_index(method,1,CODOL_LOADOUT_WEAPONS,&weapon))return;
        loadout_weapon_fallback(method,weapon,NULL,
            "this player has no complete profile upload, or mp/playerdata.def "
            "does not describe weaponClasses as this build reads it");
        return;
    }
    if(!loadout_index(method,1,CODOL_LOADOUT_WEAPONS,&weapon))return;
    status=CODOL_ComposeLoadoutWeaponRecipe(loadout.base[weapon],loadout.attachments[weapon],
        CODOL_LOADOUT_ATTACHMENTS,&recipe);
    name=recipe.name;
    if(status<0) {
        loadout_weapon_fallback(method,weapon,NULL,MARKETPLACE_TABLE " or " ATTACHMENT_TABLE
            " is not mounted, or the composed name does not fit");
        return;
    }
    if(status!=1) {
        /* No base weapon stored in this slot at all. */
        if(slot_empty(loadout.base[weapon])){Scr_AddString(loadout_none);return;}
        loadout_weapon_fallback(method,weapon,NULL,va("stored base weapon %d is not a \"wea\" row in "
            MARKETPLACE_TABLE ", or " ATTACHMENT_TABLE " does not list it",loadout.base[weapon]));
        return;
    }
    if(CODOL_LoadoutItemName(loadout.base[weapon],&base,NULL,NULL)!=1 || !base) {
        loadout_weapon_fallback(method,weapon,NULL,MARKETPLACE_TABLE " is not mounted or is malformed");
        return;
    }
    /* Seven shipped weapons, including beretta_mp, have a stock definition but
     * no mp/coweapmodels body. The reference composer deliberately leaves them
     * at their base index: composing them would create attachments without a
     * gun body. */
    if(!recipe.base_world_model || !*recipe.base_world_model ||
       !recipe.base_view_model || !*recipe.base_view_model) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL loadout: %s has no complete composed art; using stock base\n",base);
        Scr_AddString(CODOL_SafeStockWeapon(base));return;
    }
    /* A build that still leaves one of the weapon's own declared groups empty
     * has never been seen to render: the client ends the match with
     * "178 0 <spec> right" on the next fresh connect. Say so here rather than
     * hand back a name that does that, and do not quietly answer with the bare
     * base weapon either, which would discard every attachment the player
     * chose.
     *
     * Unless the weapon's own data cannot cover the group at all - wa2000_mp
     * declares a grip its tables never offer. That recipe is complete and
     * legal, and the bot bridge has always kept it; rejecting it here is what
     * put the player's WA2000 back on its stock IW4 body while a bot holding
     * the identical "*a 53 0 ..." name carried the CoDOL one. */
    if(recipe.missing_defaults && !CODOL_LoadoutMissingDefaultsUnconstructible(&recipe)) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL loadout: %s leaves %u declared group(s) empty; using stock %s\n",
            name,recipe.missing_defaults,base);
        Scr_AddString(CODOL_SafeStockWeapon(base));return;
    }
    if(recipe.missing_defaults && !(loadout_default_warned&(1u<<(weapon&31u)))) {
        loadout_default_warned|=1u<<(weapon&31u);
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL loadout: %s: %u declared default(s) have no legal C1 attachment/model "
            "pair; retaining complete legal recipe\n",base,recipe.missing_defaults);
    }
    if(recipe.skipped_full) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL loadout: %s overflowed by %u part(s); using stock %s\n",
            name,recipe.skipped_full,base);
        Scr_AddString(CODOL_SafeStockWeapon(base));return;
    }
    /* Composing costs a native definition slot, and append_weapon_set only
     * refuses the publish *after* BG_GetWeaponIndexForName has appended it.
     * Ask first, so a full table never produces a definition with no wire
     * index - that is what made the retained SaveRegisteredWeapons refresh
     * fail and drop the server. */
    if(!CODOL_NativeWeaponRoom()) {
        loadout_weapon_fallback(method,weapon,base,
            "the native weapon definition table is full");
        return;
    }
    /* Prove the composed name before handing it to the script: this builds the
     * distinct native definition behind it, so a name that cannot be built is
     * caught here instead of as a failed give later. */
    if(CODOL_LoadComposedWeapon(name,&composed)!=1) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL loadout: cannot build %s (%s); using stock %s\n",
            name,CODOL_ComposedWeaponError(),base);
        Scr_AddString(CODOL_SafeStockWeapon(base));return;
    }
    /* Publishing puts the name in a weapon slot the client resolves it from.
     * Without that slot the name is not sendable. Losing the player's
     * attachments is bad; ending everyone's match is worse, so this degrades
     * to a weapon that is safe to hand back rather than raising. */
    if(CODOL_PublishComposedWeapon(name,base,&slot)!=1) {
        loadout_weapon_fallback(method,weapon,base,
            va("%s could not be published into a weapon slot (%s)",name,
               CODOL_ServerWeaponRegistryError()));
        return;
    }
    Scr_AddString(name);
}
#endif
