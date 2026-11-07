/* Shipped C1 bot class CSV -> native recipes, with no playerdata dependency. */
#ifdef CODOL_SERVER
#include "codol_bot_loadout.h"
#include "codol_script_profile_loadout.h"
#include "codol_player_appearance.h"
#include "codol_character_variant.h"
#include "codol_sv_weapons.h"
#include "codol_weapon_compose.h"
#include "codol_xmodel.h"
#include "codol_weapon_budget.h"
#include "server.h"
#include "filesystem.h"
#include <ctype.h>
#include "scr_vm.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#define BOT_TABLE "mp/botclasstable.csv"
static void *csvBuffer;
static char *csvRows[128][10];
static unsigned csvRowCount;
static int csvStatus;
static unsigned missingDefaultWarnings;
static unsigned unbuildablePartWarnings;
static unsigned loadoutFallbackWarnings;
static unsigned substituteHeadWarnings;
static unsigned characterFallbackWarnings;
static uint32_t droppedPartWarnings[9][2];
void CODOL_ResetBotLoadout(void)
{
    if(csvBuffer)FS_FreeFile(csvBuffer);
    csvBuffer=NULL;csvStatus=0;csvRowCount=0;
    missingDefaultWarnings=0;
    unbuildablePartWarnings=0;
    loadoutFallbackWarnings=0;
    substituteHeadWarnings=0;
    characterFallbackWarnings=0;
    memset(droppedPartWarnings,0,sizeof(droppedPartWarnings));
    memset(csvRows,0,sizeof(csvRows));
}
/* Ten declared columns, RFC-style doubled quotes, no silent dropped fields. */
static int load_csv(void)
{
    char *read,*write,*cell;int size,quoted,closed,delimiter;unsigned column;
    if(csvStatus)return csvStatus==1;
    csvStatus=-1;size=FS_ReadFile(BOT_TABLE,&csvBuffer);
    if(size<=0 || size>256*1024)goto invalid;
    read=csvBuffer;
    while(*read){
        if(csvRowCount==128)goto invalid;
        for(column=0;column<10;++column){
            cell=write=read;quoted=(*read=='"');closed=!quoted;if(quoted)++read;
            while(*read){
                if(quoted && *read=='"'){
                    if(read[1]=='"'){*write++='"';read+=2;continue;}
                    ++read;closed=1;break;
                }
                if(!quoted && (*read==','||*read=='\r'||*read=='\n'))break;
                if(*read=='\r'||*read=='\n')goto invalid;
                *write++=*read++;
            }
            if(!closed)goto invalid;
            if(quoted)while(*read==' '||*read=='\t')++read;
            delimiter=(unsigned char)*read;if(delimiter)++read;
            *write=0;csvRows[csvRowCount][column]=cell;
            if(column<9){if(delimiter!=',')goto invalid;}
            else {
                if(delimiter==',')goto invalid;
                if(delimiter=='\r'&&*read=='\n')++read;
                else if(delimiter!='\r'&&delimiter!='\n'&&delimiter!=0)goto invalid;
            }
        }
        ++csvRowCount;
    }
    if(csvRowCount<2 || strcmp(csvRows[0][0],"uniqueName"))goto invalid;
    for(column=1;column<10;++column){char label[20];snprintf(label,sizeof(label),"botclass%u",column-1);if(strcmp(csvRows[0][column],label))goto invalid;}
    csvStatus=1;return 1;
invalid:
    if(csvBuffer)FS_FreeFile(csvBuffer);csvBuffer=NULL;csvRowCount=0;
    return 0;
}
static int bot_class(scr_entref_t ref,unsigned params,unsigned *classIndex)
{
    int index;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client || svs.clients[ref.entnum].netchan.remoteAddress.type!=NA_BOT){Scr_ObjectError("bot loadout requires a bot player");return 0;}
    if(Scr_GetNumParam()!=params || Scr_GetType(0)!=VAR_INTEGER){Scr_Error("bot loadout requires integer class index and member");return 0;}
    index=Scr_GetInt(0);if(index<0||index>8){Scr_ParamError(0,"bot class index must be 0..8");return 0;}*classIndex=index;return 1;
}
static const char *value(unsigned index,const char *key)
{
    unsigned row;
    if(index>8 || !key || !load_csv())return NULL;
    for(row=1;row<csvRowCount;++row)if(!Q_stricmp(csvRows[row][0],key))
        return *csvRows[row][index+1]?csvRows[row][index+1]:"none";
    return NULL;
}
/* botclasstable.csv names the difficulties each class may use. Keep class
 * selection tied to that authored row instead of assuming all nine classes
 * are suitable for Recruit. */
static void class_allows_difficulty(void)
{
    int cls;const char *tier,*allowed,*start,*end;size_t length;
    if(Scr_GetNumParam()!=2 || Scr_GetType(0)!=VAR_INTEGER || Scr_GetType(1)!=VAR_STRING){
        Scr_Error("codol_botclassallowsdifficulty requires class index and difficulty name");return;
    }
    cls=Scr_GetInt(0);tier=Scr_GetString(1);
    if(cls<0 || cls>8){Scr_ParamError(0,"bot class index must be 0..8");return;}
    allowed=value((unsigned)cls,"botDifficulties");
    if(!allowed || !tier){Scr_AddBool(0);return;}
    length=strlen(tier);start=allowed;
    while(*start){
        end=strchr(start,'|');if(!end)end=start+strlen(start);
        if((size_t)(end-start)==length && !strncmp(start,tier,length)){Scr_AddBool(1);return;}
        start=*end?end+1:end;
    }
    Scr_AddBool(0);
}
static int market_id(const char *name,const char *type)
{
    const codol_engine_table_t *t;int row,id=0;char *end;long n;
    if(CODOL_LoadEngineStringTable("mp/comarketplaceitems.csv",&t)!=1 || !t || t->columnCount<3 || !t->values)return 0;
    for(row=0;row<t->rowCount;++row){const char *const *v=t->values+(size_t)row*t->columnCount;
        if(!v[0]||!v[1]||!v[2]||Q_stricmp(v[1],name)||Q_stricmp(v[2],type))continue;
        n=strtol(v[0],&end,10);if(end==v[0]||*end||n<=0||n>32767)return 0;id=(int)n;
    }
    return id;
}
/* Every builtin here answers a spawning bot. A missing table row is a data
 * defect worth a warning, never a script exception: an exception here unwinds
 * giveLoadout, drops the gametype thread and ends the human's match. */
static void get_item(scr_entref_t ref)
{
    unsigned cls;const char *key,*text;if(!bot_class(ref,2,&cls))return;key=Scr_GetString(1);text=value(cls,key);
    if(!text){
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u: %s has no member %s; answering none\n",cls,BOT_TABLE,key?key:"<null>");
        Scr_AddString("none");return;
    }
    Scr_AddString(text);
}
/* A declaration is not an available C1 pair. WA2000 declares gri_default,
 * but its attachment/model tables provide no grip at all. Do not invent one
 * or reject the otherwise complete legal weapon. Missing constructible parts
 * remain errors, as do every explicit CSV choice and descriptor overflow.
 *
 * The rule itself now lives with the recipe, in
 * CODOL_LoadoutMissingDefaultsUnconstructible, because the human profile
 * bridge has to apply exactly the same test: while it did not, a player's
 * WA2000 degraded to its stock IW4 body under a bot carrying the identical
 * composed name. */
static int missing_defaults_unconstructible(const codol_loadout_recipe_t *recipe)
{
    return CODOL_LoadoutMissingDefaultsUnconstructible(recipe);
}
/* A pair can be legal for the weapon and still have no shipped geometry.
 * mp/coWeaponAttachmentTable.csv lists (fal_mp, red_swat1) and
 * mp/coweapitems/sco.csv gives that pair the models red_swat1_s_blk and
 * red_swat1_s_blk_vmgun, but no mounted zone carries either XModel - the name
 * occurs in the shipped fastfiles only inside that stringtable. C1 then
 * substitutes its own default asset for the part, which is what the flat,
 * unlit red plane on the bot FAL is. Legality is not availability: check the
 * mounted asset set before a chosen part reaches a published recipe.
 * 1 the part's models exist (or it merges none), 0 one is absent. */
static int part_models_mounted(const codol_loadout_recipe_t *recipe,
    const codol_loadout_part_t *part,const char **missing)
{
    const codol_mounted_model_skeleton_t *skeleton;
    const char *world=NULL,*view=NULL;
    if(!recipe || !part || !part->name || !part->group)return 1;
    /* No row means the item contributes no mesh at all (every cam_*, sco_none,
     * hbs_normal, gps_default), which is not an absence. */
    if(CODOL_ComposedItemModelRow(recipe->base_name,part->name,part->group,recipe->flag,
        &world,&view,NULL)!=1)return 1;
    if(world && *world && CODOL_LoadMountedXModelSkeleton(world,&skeleton)!=1) {
        if(missing)*missing=world;
        return 0;
    }
    if(view && *view && CODOL_LoadMountedXModelSkeleton(view,&skeleton)!=1) {
        if(missing)*missing=view;
        return 0;
    }
    return 1;
}
/* `append_weapon_set` refuses any publish whose final BG_GetNumWeapons()
 * exceeds the native definition ceiling - but only *after*
 * BG_GetWeaponIndexForName has already appended the definition, which leaves a
 * native weapon with no wire slot and no configstring.
 *
 * A full combat-training lobby can reach that ceiling: every distinct bot class
 * composes its own primary and secondary definition on top of the ~52 stock
 * weapons and the partner definitions each of those registers. When there is
 * no room the bot has to take a weapon that is already registered, which costs
 * no slot and is what IW4 hands a bot whose loadout cannot be built. Check
 * before composing so the doomed registration never happens.
 *
 * The budget itself - the ceiling, the headroom, "is this name already live" -
 * is shared with the human profile bridge in codol_weapon_budget.h, so both
 * producers gate on one implementation and one copy of the ceiling. */
/* A bot whose loadout cannot be built must never end the human's match: every
 * data, asset and capacity failure degrades with one warning. Only
 * script-contract violations (wrong receiver, wrong argument type) still
 * raise, because those are programming errors in the caller. */
static void weapon_fallback(unsigned cls,int side,const char *baseName,const char *why)
{
    unsigned bit=1u<<(cls*2+(unsigned)(side?1:0));
    /* Handing back a name that still has to be registered would re-create the
     * exact overflow this fallback exists to avoid. */
    const char *answer=CODOL_SafeStockWeapon(baseName);
    if(!(loadoutFallbackWarnings&bit)) {
        loadoutFallbackWarnings|=bit;
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u %s weapon: %s; falling back to %s\n",
            cls,side?"secondary":"primary",why,answer);
    }
    Scr_AddString(answer);
}
static void get_weapon(scr_entref_t ref)
{
    unsigned cls,slot,i,count=0,dropped;int side,base,ids[CODOL_LOADOUT_ATTACHMENTS];char key[64],baseName[128];
    const char *idNames[CODOL_LOADOUT_ATTACHMENTS];
    const char *prefix,*name,*item;const struct WeaponDef *definition;codol_loadout_recipe_t recipe;
    if(!bot_class(ref,2,&cls))return;side=Scr_GetInt(1);if(side<0||side>1){Scr_ParamError(1,"bot weapon slot must be 0 or 1");return;}
    prefix=side?"loadoutSecondary":"loadoutPrimary";name=value(cls,prefix);
    if(!name || !strcmp(name,"none")){Scr_AddString("none");return;}
    if(snprintf(baseName,sizeof(baseName),"%s%s",name,strstr(name,"_mp")?"":"_mp")>=(int)sizeof(baseName)){
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u: weapon name %s is too long\n",cls,name);
        Scr_AddString("none");return;
    }
    base=market_id(baseName,"wea");
    if(!base){weapon_fallback(cls,side,"none",va("%s is not a C1 marketplace weapon",baseName));return;}
    for(i=1;i<= (side?4u:8u);++i){
        if(i==1)snprintf(key,sizeof(key),"%sAttachment",prefix);else snprintf(key,sizeof(key),"%sAttachment%u",prefix,i);
        item=value(cls,key);if(!item || !strcmp(item,"none"))continue;
        ids[count]=market_id(item,"wat");
        if(!ids[count]){weapon_fallback(cls,side,baseName,va("attachment %s is not in the C1 marketplace",item));return;}
        idNames[count]=item;++count;
    }
    snprintf(key,sizeof(key),"%sCamo",prefix);item=value(cls,key);
    if(item && strcmp(item,"none")){
        ids[count]=market_id(item,"wat");
        if(!ids[count]){weapon_fallback(cls,side,baseName,va("camo item %s is not in the C1 marketplace",item));return;}
        idNames[count]=item;++count;
    }
    if(!CODOL_NativeWeaponRoom()){weapon_fallback(cls,side,baseName,"the native weapon definition table is full");return;}
    if(CODOL_ComposeLoadoutWeaponRecipe(base,ids,count,&recipe)!=1 || recipe.skipped_full ||
       (recipe.missing_defaults && !missing_defaults_unconstructible(&recipe))){
        weapon_fallback(cls,side,baseName,"the recipe does not compose");return;
    }
    /* Drop only the class's own unbuildable choices, then rebuild once: a
     * declared default the composer supplied is already covered above, and an
     * iron-sight rifle is a correct gun where a placeholder mesh is not. The
     * original recipe stands if the reduced one will not compose. */
    for(i=0,dropped=0;i<recipe.count;++i) {
        const codol_loadout_part_t *part=&recipe.parts[i];
        const char *absent=NULL;unsigned j;
        if(part->origin!=CODOL_LOADOUT_PART_EQUIPPED)continue;
        if(part_models_mounted(&recipe,part,&absent))continue;
        for(j=0;j<count;++j)if(idNames[j] && !Q_stricmp(idNames[j],part->name))break;
        if(j==count)continue;
        if(!(unbuildablePartWarnings&(1u<<(cls*2+side)))) {
            unbuildablePartWarnings|=1u<<(cls*2+side);
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot %s: attachment %s needs xmodel %s, which is in no mounted zone; dropping it rather than publishing C1's placeholder mesh\n",
                baseName,part->name,absent?absent:"<unnamed>");
        }
        idNames[j]=NULL;++dropped;
    }
    if(dropped) {
        codol_loadout_recipe_t reduced;int reducedIds[CODOL_LOADOUT_ATTACHMENTS];unsigned n=0;
        for(i=0;i<count;++i)if(idNames[i])reducedIds[n++]=ids[i];
        if(CODOL_ComposeLoadoutWeaponRecipe(base,reducedIds,n,&reduced)==1 && !reduced.skipped_full &&
           (!reduced.missing_defaults || missing_defaults_unconstructible(&reduced)))recipe=reduced;
        else Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot %s: reduced recipe does not compose; keeping the original\n",baseName);
    }
    if(recipe.missing_defaults && !(missingDefaultWarnings&(1u<<(cls*2+side)))){
        missingDefaultWarnings|=1u<<(cls*2+side);
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot %s: %u declared default(s) have no legal C1 attachment/model pair; retaining complete legal recipe\n",baseName,recipe.missing_defaults);
    }
    if(!recipe.base_world_model||!*recipe.base_world_model||!recipe.base_view_model||!*recipe.base_view_model){Scr_AddString(baseName);return;}
    if(CODOL_LoadComposedWeapon(recipe.name,&definition)!=1){
        weapon_fallback(cls,side,baseName,va("%s has no buildable definition",recipe.name));return;
    }
    if(CODOL_PublishComposedWeapon(recipe.name,baseName,&slot)!=1){
        weapon_fallback(cls,side,baseName,va("%s could not be published (%s)",recipe.name,CODOL_ServerWeaponRegistryError()));return;
    }
    Scr_AddString(recipe.name);
}
/* C1 729090 only accepts a coCharItems row whose column-2 key names this
 * faction exactly or the shared "ss", and its running best starts at -1, so an
 * ineligible item selects nothing at all; 44e8b0 then simply does not append
 * that part. mp/coCharItems/hea.csv gives hea_socomc exactly one row, keyed
 * "m sc sss", while both the shipped and the loose mp/botClassTable.csv put
 * hea_socomc in the *team-force* charHEA column for classes 3 and 8. Those two
 * bots therefore compose every other part and no head.
 *
 * The repair has to stay in the data: do not relax the faction rule (that
 * would dress every faction in the other one's geometry) and do not hardcode a
 * head. mp/coCharacterDefTable.csv column 1 is each character's own faction
 * tag, so the table already names the heads this faction is built from - take
 * the first one that actually resolves. */
static int head_resolves(uint16_t id,unsigned gender,unsigned faction)
{
    const char *model=NULL,*viewmodel=NULL;
    char skin[4];
    if(!id || id>=32768)return 0;
    CODOL_CharacterSkinTone(id,skin);
    return CODOL_LoadCharacterItemModels(id,gender,faction,"urb",skin,&model,&viewmodel)==1 &&
        model && *model;
}
static uint16_t faction_character_head(const codol_engine_table_t *characters,
    unsigned gender,unsigned faction)
{
    const char *tag=faction ? "SC":"TF";
    int r;
    if(!characters || characters->columnCount<2 || characters->rowCount<0 ||
       (characters->rowCount && !characters->values))return 0;
    for(r=0;r<characters->rowCount;++r) {
        const char *const *cells=characters->values+(size_t)r*characters->columnCount;
        int id;
        if(!cells[0] || !cells[1] || Q_stricmp(cells[1],tag))continue;
        id=market_id(cells[0],"cha");
        if(id>0 && head_resolves((uint16_t)id,gender,faction))return (uint16_t)id;
    }
    return 0;
}
/* Same rule as the weapon builtins: a bot appearance that cannot be composed
 * leaves the bot with whatever appearance it already had and logs once. It
 * must not unwind the spawn thread. */
static void character_fallback(unsigned cls,const char *faction,const char *why)
{
    unsigned bit=1u<<(cls*2+(faction && !strcmp(faction,"sc") ? 1u:0u));
    if(characterFallbackWarnings&bit)return;
    characterFallbackWarnings|=bit;
    Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u (%s) character: %s; keeping appearance\n",
        cls,faction?faction:"?",why);
}
static void character(scr_entref_t ref)
{
    static const char *const keys[]={"charFPA","charBOO","charFJA","charHAN","charHEA","charVES","charHEG","charELP","charKNP","charPAT","charEYE"};
    unsigned cls,f,i,selector=0,gender=0;int id,slot,status;char key[48],skin[4];const char *faction,*weapon,*name;
    const codol_engine_table_t *market,*defaults,*rigs,*parts;codol_character_item_t item;
    codol_character_composition_t composition={0};
    if(!bot_class(ref,3,&cls))return;faction=Scr_GetString(1);weapon=Scr_GetString(2);
    if(!strcmp(faction,"tf"))f=0;else if(!strcmp(faction,"sc"))f=1;else{Scr_ParamError(1,"bot faction must be tf or sc");return;}
    if(CODOL_LoadEngineStringTable("mp/comarketplaceitems.csv",&market)!=1 || CODOL_LoadEngineStringTable("mp/cocharacterdeftable.csv",&defaults)!=1 || CODOL_LoadEngineStringTable("mp/cochestrigs.csv",&rigs)!=1){character_fallback(cls,faction,"character tables unavailable");return;}
    snprintf(key,sizeof(key),"charGender%s",f?"_sc":"");name=value(cls,key);if(name&&!strcmp(name,"f"))gender=1;
    composition.character_index=cls;
    for(i=0;i<sizeof(keys)/sizeof(*keys);++i){
        snprintf(key,sizeof(key),"%s%s",keys[i],f?"_sc":"");name=value(cls,key);
        if(!name || !strcmp(name,"none"))continue;
        id=market_id(name,"cha");if(!id || CODOL_CharacterItem(market,(uint16_t)id,&item)!=1 || (slot=CODOL_CharacterSlotForGroup(item.group))<0 || slot>=CODOL_COMPOSITION_SLOTS){character_fallback(cls,faction,va("item %s cannot resolve",name));return;}
        /* Actual item group wins: shipped charELP contains eye_aviators in
         * several classes; it remains eyewear rather than an elbow model. */
        composition.items[slot]=(uint16_t)id;
    }
    /* Before the tone and the defaults, both of which C1 keys on this item. */
    if(composition.items[4] && !head_resolves(composition.items[4],gender,f)) {
        uint16_t replacement=faction_character_head(defaults,gender,f);
        codol_character_item_t before,after;
        if(!replacement){character_fallback(cls,faction,"no usable head");return;}
        if(!(substituteHeadWarnings&(1u<<(cls*2+f)))) {
            substituteHeadWarnings|=1u<<(cls*2+f);
            if(CODOL_CharacterItem(market,composition.items[4],&before)==1 &&
               CODOL_CharacterItem(market,replacement,&after)==1)
                Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u (%s): %s has no %s head variant; using the character table's %s instead\n",
                    cls,faction,before.name,faction,after.name);
        }
        composition.items[4]=replacement;
    }
    CODOL_CharacterSkinTone(composition.items[4],skin);CODOL_WeaponRigSelector(weapon,&selector);
    if(!CODOL_ApplyCharacterDefaults(market,defaults,composition.items[4],composition.items)||!CODOL_ApplyCharacterChestRig(market,rigs,selector,composition.items)){character_fallback(cls,faction,"defaults/vest resolution failed");return;}
    if(composition.items[2] && composition.items[7]){int allowed;if(CODOL_LoadCharacterItemParts(composition.items[2],&item,&parts)!=1 || !CODOL_CharacterSlot7Allowed(parts,item.name,&allowed)){character_fallback(cls,faction,"jacket metadata unavailable");return;}if(!allowed)composition.items[7]=0;}
    for(i=0;i<CODOL_COMPOSITION_SLOTS;++i)if(composition.items[i]){
        status=CODOL_LoadCharacterItemModels(composition.items[i],gender,f,"urb",skin,&composition.models[i],&composition.viewmodels[i]);
        if(status<0){character_fallback(cls,faction,"model resolution failed");return;}
        /* Absence is legal for the selector and silent for the publisher, so
         * this is the only place a dropped body part is ever visible. */
        if(status!=1 && !(droppedPartWarnings[cls][f]&(1u<<i))) {
            codol_character_item_t missing;
            droppedPartWarnings[cls][f]|=1u<<i;
            if(CODOL_CharacterItem(market,composition.items[i],&missing)==1)
                Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL bot class %u (%s): slot %u item %s has no %s variant; part omitted\n",
                    cls,faction,i,missing.name,faction);
        }
    }
    if(!CODOL_PublishCharacterComposition(ref.entnum,&composition,faction))character_fallback(cls,faction,"publication failed");
    else CODOL_SendClientVoicePrefix(ref.entnum,faction,gender);
}
void CODOL_RegisterBotLoadoutMethods(void)
{
    Scr_AddFunction("codol_botclassallowsdifficulty",class_allows_difficulty,0);
    Scr_AddMethod("codol_getbotloadoutitem",get_item,0);
    Scr_AddMethod("codol_getbotloadoutweapon",get_weapon,0);
    Scr_AddMethod("codol_applybotcharacter",character,0);
}
#endif
