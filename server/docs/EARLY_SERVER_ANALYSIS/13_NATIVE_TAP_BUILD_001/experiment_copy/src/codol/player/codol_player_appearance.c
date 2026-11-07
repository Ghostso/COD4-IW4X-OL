/* See codol_player_appearance.h for the ordering, availability and
 * first-person rules this file implements and where each was measured. */
#include "codol_player_appearance.h"
#include "codol_character_variant.h"
#include "codol_profile.h"
#include <stdlib.h>
#include <string.h>

/* The engine's own default-character column list, expressed in composition
 * slots: charFPA, charBOO, charFJA, charHAN, charVES, charHEA, charHEG,
 * charELP, charKNP (C1 .data:0xCCCAB4), then eyewear, which is a profile slot
 * and a model but has no column in the team-0 bot list. charPAT is a material
 * and is excluded here rather than dropped later, so slot 9 can never be
 * mistaken for a body part. */
static const unsigned char ordered_slots[]={0,1,2,3,5,4,6,7,8,13};
#define CODOL_COMPOSITION_MATERIAL_SLOT 9
#define CODOL_COMPOSITION_JACKET_SLOT 2
#define CODOL_COMPOSITION_GLOVE_SLOT 3

static int is_ordered(unsigned slot)
{
    unsigned i;
    for(i=0;i<sizeof(ordered_slots);++i)if(ordered_slots[i]==slot)return 1;
    return 0;
}

int CODOL_OrderCharacterParts(const codol_character_composition_t *source,
    codol_character_parts_t *out)
{
    codol_character_parts_t next={0};
    unsigned i;
    if(!source || !out)return 0;
    for(i=0;i<sizeof(ordered_slots);++i) {
        const char *model=source->models[ordered_slots[i]];
        if(!model || !*model)continue;
        if(next.count>=CODOL_CHARACTER_PARTS)return 0;
        next.model[next.count++]=model;
    }
    /* Slots outside the measured list still carry real items - the
     * weapon-class chest rig lands in slot 15 - and C1's own lobby compaction
     * (0x0060DAF0) walks all eighteen in ascending order and appends every one
     * that loads. Their position relative to the named parts is not measured
     * for the in-match path, so they follow it rather than displacing it. */
    for(i=0;i<CODOL_COMPOSITION_SLOTS;++i) {
        const char *model=source->models[i];
        if(i==CODOL_COMPOSITION_MATERIAL_SLOT || is_ordered(i))continue;
        if(!model || !*model)continue;
        if(next.count>=CODOL_CHARACTER_PARTS)return 0;
        next.model[next.count++]=model;
    }
    next.arms=source->viewmodels[CODOL_COMPOSITION_JACKET_SLOT];
    next.hands=source->viewmodels[CODOL_COMPOSITION_GLOVE_SLOT];
    if(next.arms && !*next.arms)next.arms=NULL;
    if(next.hands && !*next.hands)next.hands=NULL;
    /* The arm gates the pair; hands alone would be sent and then ignored. */
    if(!next.arms)next.hands=NULL;
    *out=next;return 1;
}

#ifdef CODOL_SERVER
#include "codol_xmodel.h"
#include "codol_assets.h"
#include "codol_script_profile_vm.h"
#include "codol_playerstate_ext.h"
#include "codol_clientstate_ext.h"
#include "codol_sv_state.h"
#include "codol_character_composition.h"
#include "codol_stats.h"
#include "scr_vm.h"
#include "cscr_stringlist.h"
#include "bg_public.h"
#include "codol_weapon_native.h"
#include "qcommon.h"
#include "server.h"
#include "g_shared.h"
#include "dobj.h"
#include "codol_pose_budget.h"

extern XModel *cached_models[CODOL_NATIVE_MODELS];
int CODOL_FindHighModel(unsigned handle);
int CODOL_AllocHighModel(const char *name);
XModel *__cdecl SV_XModelGet(const char *name);

typedef struct {
    int ready;
    unsigned count;
    unsigned model[CODOL_CHARACTER_PARTS];
    unsigned arms,hands;
} codol_character_pose_t;
static codol_character_pose_t characters[MAX_CLIENTS];
static codol_character_pose_t corpse_characters[MAX_GENTITIES];

/* A corpse owns the outfit captured at death, not a later respawn outfit.
 * Its native pose must use the same builder as the living source. */
void CODOL_CaptureCorpseCharacter(unsigned corpse,unsigned client)
{
    extern void CODOL_KnifeCorpseCreated(unsigned,unsigned);
    CODOL_KnifeCorpseCreated(corpse,client);
    if(corpse>=MAX_GENTITIES)return;
    memset(&corpse_characters[corpse],0,sizeof(corpse_characters[corpse]));
    if(client<MAX_CLIENTS)corpse_characters[corpse]=characters[client];
}

/* G_ModelIndex without its script error and without its precache-time
 * restriction. The retained builtin raises "model %s not precached" for any
 * name that is not already a configstring once the level is running, which a
 * profile-driven outfit can never satisfy: the names are only known when the
 * player spawns. C1 has the same operation on the same namespace and publishes
 * at runtime, and the CoDOL configstring bank is refreshed for every snapshot
 * (sv_snapshot.c), so a name registered here reaches the client with the frame
 * that first refers to it. Returns the native slot, or 0 when the bank is
 * full - never a slot the client has no name for. */
unsigned CODOL_RegisterRuntimeModel(const char *name)
{
    unsigned index,available=0;
    const char *p;
    if(!name || !*name || strlen(name)>=64)return 0;
    /* A published asset name is a reliable-command token; the per-frame
     * refresh (CODOL_RefreshAssetRange) rejects anything else with an
     * ERR_DROP of the whole map, so refuse it here instead. */
    for(p=name;*p;++p)
        if((unsigned char)*p<=32 || *p==127 || *p=='"' || *p==';' || *p=='\\')return 0;
    for(index=1;index<MAX_MODELS;++index) {
        unsigned handle=SV_GetConfigstringIndex(CS_MODELS+index);
        const char *existing;
        if(!handle || handle==sv.emptyConfigString) {
            if(!available)available=index;
            continue;
        }
        existing=SL_ConvertToString(handle);
        if(existing && !strcmp(existing,name))return index;
    }
    if(!available) {
        /* The 511 IW3 slots are full; C1 holds 2048 (G_ModelIndex 0x570400),
         * and so does the native bank above them (codol_sv_assets.c). */
        int high=CODOL_FindHighModel(SL_FindLowercaseString(name));
        if(high<=0)high=CODOL_AllocHighModel(name);
        return high>0 ? (unsigned)high : 0;
    }
    /* Both stores G_ModelIndex makes, in its order: the server-side cached
     * model first, so no reader can observe a published index whose cache
     * entry is still stale. */
    cached_models[available]=SV_XModelGet(name);
    if(!cached_models[available])return 0;
    SV_SetConfigstring(CS_MODELS+available,name);
    return available;
}

/* A name whose XModel the client cannot load does not merely go missing: the
 * client marks the clientInfo and replaces the entire body with its built-in
 * default character. The mounted CoDOL asset set is what these table rows name,
 * so a mounted skeleton is the availability answer this server can actually
 * give. It is not proof that the client has the streamed geometry. */
static int model_available(const char *name)
{
    const codol_mounted_model_skeleton_t *skeleton;
    return name && *name && CODOL_LoadMountedXModelSkeleton(name,&skeleton)==1;
}

/* The C1 first-person DObj attaches the gun to tag_weapon on its arm model.
 * Report the exact published pair when tracing is enabled; a model name alone
 * cannot distinguish a bad recipe from a native-to-wire model-bank mismatch. */
static void trace_viewmodel_part(unsigned client,const char *kind,const char *name,
    unsigned native_index)
{
    const codol_mounted_model_skeleton_t *skeleton=NULL;
    unsigned i,bones=0,roots=0;
    int status=0,has_tag=-1;
    if(name && *name)status=CODOL_LoadMountedXModelSkeleton(name,&skeleton);
    if(status==1 && skeleton) {
        bones=skeleton->skeleton.bones;
        roots=skeleton->skeleton.roots;
        has_tag=0;
        for(i=0;i<skeleton->bone_names.count;++i)
            if(skeleton->bone_names.names[i].text &&
               !strcmp(skeleton->bone_names.names[i].text,"tag_weapon")) {
                has_tag=1;
                break;
            }
        if(!has_tag && skeleton->bone_names.unresolved)has_tag=-1;
    }
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL viewmodel: client %u %s requested %s native %u wire %d skeleton %d bones %u roots %u tag_weapon %d\n",
        client,kind,name && *name ? name : "<none>",native_index,
        CODOL_ServerModelToWire(native_index),status,bones,roots,has_tag);
}

static int weapon_class_selector(const char *weapon,unsigned *selector)
{
    codol_mounted_weapon_t mounted;
    const uint8_t *p;
    uint32_t class_id;
    if(!weapon || !*weapon)return 0;
    /* C1 0x611ba0 loads the named weapon and reads its class at +0x344. */
    if(CODOL_LoadMountedWeapon(weapon,&mounted)!=1)return 0;
    if(mounted.asset.type!=28 || !mounted.asset.data || mounted.asset.size<0x348)return 0;
    p=mounted.asset.data+0x344;
    class_id=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
    return CODOL_ChestRigSelector(class_id,selector);
}

int CODOL_WeaponRigSelector(const char *weapon,unsigned *selector)
{
    char qualified[128];
    unsigned resolved=0;
    if(!selector)return 0;
    if(weapon_class_selector(weapon,&resolved)) { *selector=resolved; return 1; }
    /* The gametype script hands over a base name ("m4"), because that is what
     * getBaseWeaponName produces; the weapon asset is the multiplayer variant
     * ("m4_mp"). A composed custom name already carries its own suffix, so the
     * qualified form is only tried when the bare one is not an asset. */
    if(!weapon || !*weapon || strchr(weapon,'*') ||
       strlen(weapon)+4>=sizeof(qualified))return 0;
    if(strlen(weapon)>3 && !strcmp(weapon+strlen(weapon)-3,"_mp"))return 0;
    snprintf(qualified,sizeof(qualified),"%s_mp",weapon);
    if(!weapon_class_selector(qualified,&resolved))return 0;
    *selector=resolved;return 1;
}

/* C1 keeps three independent character selectors in one profile -
 * tfCharacterIndex, scCharacterIndex and zmCharacterIndex - and the zone the
 * client loaded decides which one is in play. Under zm there are no factions to
 * choose between: every player is a Cyborg, and mp/cyborgclasstable.csv's four
 * rows are the whole roster. The gametype scripts only know the MP team
 * (_teams.gsc playerModelForWeapon produces "tf" or "sc" and nothing else), so
 * the decision belongs here, beside the profile read, where the mounted zone is
 * already known. Without this a zm match composes tfCharacterIndex/
 * scCharacterIndex, i.e. the multiplayer soldier. */
static const char *zone_faction(const char *requested)
{
    const char *zone=CODOL_ServerZoneType();
    return (zone && !strcmp(zone,"zm")) ? "zm" : requested;
}

/* C1 registers the scoped-rifle breath sounds only when the server names the
 * player's voice. CG_SetClientDvarFromServer 0x00468A00 (case 's' of
 * CG_ServerCommand) sends "cg_vo_prefix" to 0x0046E060, which is the ONLY
 * writer of the three handles CG_UpdateHoldBreath 0x0047DAC0 plays:
 *   0x016D60EC weap_sniper_breathin   (flag ps+0x344 bit 4 rises)
 *   0x016D60F0 weap_sniper_breathout  (released before 4500 ms)
 *   0x016D60F4 weap_sniper_breathgasp (held past 4500 ms)
 * each with an "_f" suffix when prefix[3] == 'F' (0x0046E137). Outside zm the
 * same call registers "<prefix>mp_sprint" (0x0046E0C1) into 0x016D9AE0. Until
 * the command arrives all three handles are zero and the hold is silent.
 * The prefix is the faction voice (mp/factiontable.csv column 7 in C1's
 * code_post_gfx_mp: TF "UK_", SC "AB_") followed by gender and voice number,
 * the form the shipped aliases uk_m1_mp_sprint .. ab_f2_mp_sprint use. */
/* The prefix last sent to each client: the scripts build the same voice's
 * battle-chatter, quick-message, pain/death and hurt-breathing aliases from
 * it (codol_getVoicePrefix). Empty until the character is published. */
static char voice_prefixes[MAX_CLIENTS][8];
void CODOL_SendClientVoicePrefix(unsigned client,const char *faction,unsigned gender)
{
    const char *team;
    if(client>=(unsigned)MAX_CLIENTS || !faction)return;
    team=!strcmp(faction,"sc") ? "AB" : "UK";
    snprintf(voice_prefixes[client],sizeof(voice_prefixes[client]),"%s_%c1_",team,gender ? 'F' : 'M');
    SV_GameSendServerCommand((int)client,1,
        va("s cg_vo_prefix \"%s\"",voice_prefixes[client]));
    if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL voice: client %u cg_vo_prefix %s_%c1_ (%s)\n",
            client,team,gender ? 'F' : 'M',faction);
}

const char *CODOL_ClientVoicePrefix(unsigned client)
{
    if(client>=(unsigned)MAX_CLIENTS || !voice_prefixes[client][0])return NULL;
    return voice_prefixes[client];
}

int CODOL_SelectClientCharacter(unsigned client,const char *faction,unsigned gender,
    const char *camo,unsigned rig_selector)
{
    const codol_structured_schema_t *schema;
    const uint8_t *profile;
    codol_character_composition_t composition={0};
    codol_profile_character_t selected={0};
    unsigned roster_gender;
    if(client>=(unsigned)MAX_CLIENTS || !level.clients || !g_entities[client].r.inuse ||
       !g_entities[client].client || !faction || gender>1 || !camo || strlen(camo)!=3)return 0;
    faction=zone_faction(faction);
    schema=CODOL_ScriptProfileSchema(CODOL_PROFILE_PUBLIC);
    profile=CODOL_ScriptProfileBlob(client,CODOL_PROFILE_PUBLIC);
    if(!schema || !profile) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: client %u missing %s profile input (schema %d upload %d)\n",client,faction,schema!=NULL,profile!=NULL);
        return 0;
    }
    CODOL_ProfileCharacter(profile,CODOL_STATS_SIZE,schema,faction,&selected);
    /* hea_zmgirl ships only "*_zm_f_*" geometry, and the roster table is where
     * C1 keeps each Cyborg's sex; the caller's multiplayer gender says nothing
     * about it. An unresolved row keeps the caller's value rather than guess. */
    if(!strcmp(faction,"zm")) {
        int gender_status=CODOL_ZombieCharacterGender(profile,CODOL_STATS_SIZE,schema,&roster_gender);
        if(gender_status==1)gender=roster_gender;
        /* Exact 1.1.1.13 roster item 413 is hea_zmgirl. Her mounted body
         * rows are exclusively f zm sss. If the roster sex lookup fails,
         * retaining the multiplayer default m silently removes every part. */
        if(selected.items[4]==413 && gender!=1) {
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: female Zombies head 413 had roster gender status %d; selecting female model rows\n",gender_status);
            gender=1;
        }
    }
    if(CODOL_ComposeProfileCharacterAuto(profile,CODOL_STATS_SIZE,schema,faction,gender,camo,
        rig_selector,&composition,NULL) &&
       CODOL_PublishCharacterComposition(client,&composition,faction)) {
        CODOL_SendClientVoicePrefix(client,faction,gender);
        return 1;
    }
    if(!strcmp(faction,"zm")) {
        const codol_structured_definition_t *definition;
        const uint8_t *record;
        codol_structured_path_t selector={"zmCharacterIndex",0};
        codol_structured_field_t field;
        size_t capacity;
        uint8_t *copy=malloc(CODOL_STATS_SIZE);
        unsigned candidate;
        int roster_row;
        if(!copy)return 0;
        memcpy(copy,profile,CODOL_STATS_SIZE);
        if(CODOL_ProfileRecord(copy,CODOL_STATS_SIZE,schema,&definition,&record,&capacity) &&
           CODOL_ResolveStructuredField(definition,&selector,1,&field) && field.type.kind==9) {
            for(candidate=0;candidate<48;++candidate) {
                if(candidate==selected.character_index)continue;
                if(!CODOL_StructuredWriteScalar(&definition->layout,9,field.logical_index,
                    (uint8_t *)record,capacity,candidate))break;
                if(CODOL_ZombieCharacterRow(copy,CODOL_STATS_SIZE,schema,&roster_row,NULL)!=1)
                    continue;
                if(CODOL_ZombieCharacterGender(copy,CODOL_STATS_SIZE,schema,&roster_gender)==1)
                    gender=roster_gender;
                if(!CODOL_ComposeProfileCharacterAuto(copy,CODOL_STATS_SIZE,schema,"zm",gender,camo,
                    rig_selector,&composition,NULL))continue;
                if(CODOL_PublishCharacterComposition(client,&composition,"zm")) {
                    CODOL_SendClientVoicePrefix(client,"zm",gender);
                    Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: client %u selected unusable Zombies record; using roster record %u for this match\n",client,candidate);
                    free(copy);return 1;
                }
            }
        }
        free(copy);
    }
    return 0;
}

/* The roster key (mp/cyborgclasstable.csv column 0, zm1..zm4) of this client's
 * zombies character, from its uploaded profile. 1 with *key set, 0 when the
 * profile names no roster character or none was uploaded (a test client). */
int CODOL_ClientZombieCharacterKey(unsigned client,const char **key)
{
    const codol_structured_schema_t *schema;const uint8_t *profile;
    const codol_engine_table_t *roster;const void *table=NULL;int row;
    if(!key || client>=(unsigned)MAX_CLIENTS)return 0;
    schema=CODOL_ScriptProfileSchema(CODOL_PROFILE_PUBLIC);
    profile=CODOL_ScriptProfileBlob(client,CODOL_PROFILE_PUBLIC);
    if(!schema || !profile)return 0;
    if(CODOL_ZombieCharacterRow(profile,CODOL_STATS_SIZE,schema,&row,&table)!=1)return 0;
    roster=table;
    if(!roster->values[(size_t)row*roster->columnCount])return 0;
    *key=roster->values[(size_t)row*roster->columnCount];
    return 1;
}

int CODOL_PublishCharacterComposition(unsigned client,const codol_character_composition_t *composition,const char *faction)
{
    codol_character_parts_t parts;
    codol_client_appearance_t appearance={0};
    unsigned resolved[CODOL_CHARACTER_PARTS];
    unsigned count=0,i,arms=0,hands=0;
    if(!composition || !faction || client>=MAX_CLIENTS || !level.clients ||
       !g_entities[client].r.inuse || !g_entities[client].client)return 0;
    if(!CODOL_OrderCharacterParts(composition,&parts)) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: character %u part order failed\n",composition->character_index);return 0;
    }
    for(i=0;i<parts.count;++i) {
        unsigned index;
        if(!model_available(parts.model[i])) {
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: unavailable part %s for client %u\n",parts.model[i],client);
            continue;
        }
        index=CODOL_RegisterRuntimeModel(parts.model[i]);
        if(!index)continue;
        resolved[count++]=index;
    }
    if(!count) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: character %u has no available models (head item %u, body item %u, jacket item %u)\n",composition->character_index,composition->items[4],composition->items[0],composition->items[2]);return 0;
    }
    /* The arm model is the one the client's draw path dereferences directly, so
     * an unavailable arm removes the pair rather than leaving a dangling half. */
    if(parts.arms && model_available(parts.arms))arms=CODOL_RegisterRuntimeModel(parts.arms);
    if(arms && parts.hands && model_available(parts.hands))hands=CODOL_RegisterRuntimeModel(parts.hands);
    if(!arms)hands=0;
    if(!CODOL_RefreshServerAssetNames()) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: character %u asset-name refresh failed\n",composition->character_index);return 0;
    }
    for(i=0;i<count;++i) {
        int wire=CODOL_ServerModelToWire(resolved[i]);
        if(wire<=0) {
            Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: character %u native model %u has no wire index\n",composition->character_index,resolved[i]);return 0;
        }
        if(!i)appearance.model=(unsigned)wire;
        else appearance.attach_model[i-1]=(unsigned)wire;
    }
    if(!CODOL_PlayerStateSetViewmodels(&level.clients[client].ps,arms,hands) ||
       !CODOL_PublishClientAppearance(client,&appearance)) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL appearance: character %u viewmodel/client-info publication failed (arms %u hands %u)\n",composition->character_index,arms,hands);return 0;
    }
    characters[client].ready=1;
    characters[client].count=count;
    memcpy(characters[client].model,resolved,count*sizeof(*resolved));
    for(i=count;i<CODOL_CHARACTER_PARTS;++i)characters[client].model[i]=0;
    characters[client].arms=arms;
    characters[client].hands=hands;
    /* Client-info supplies the root/first six parts. The native DObj builder
     * appends the full outfit; snapshots capture all sixteen independently. */
    g_entities[client].model=(uint16_t)resolved[0];
    for(i=0;i<19;++i) {
        g_entities[client].attachModelNames[i]=(uint16_t)(i+1<count ? resolved[i+1] : 0);
        Scr_SetString(&g_entities[client].attachTagNames[i],0);
    }
    level_bgs.clientinfo[client].dobjDirty=1;
    if(CODOL_TRACE_ON()) {
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL profile appearance: client %u character %u faction %s parts %u arms %s hands %s\n",
            client,composition->character_index,faction,count,arms ? parts.arms : "<none>",hands ? parts.hands : "<none>");
        trace_viewmodel_part(client,"arms",parts.arms,arms);
        trace_viewmodel_part(client,"hands",parts.hands,hands);
    }
    return 1;
}

static int server_part_priority(const char *name)
{
    /* These parts carry the gameplay tags the dedicated server evaluates.
     * Keep their order stable so jacket arm bones exist before the gloves and
     * tag_eye arrives with the head.  The complete cosmetic list is published
     * independently in CODOL_PublishStoredClientCharacter. */
    if(!name)return 0;
    if(!strncmp(name,"fja_",4))return 1;
    if(!strncmp(name,"han_",4))return 2;
    if(!strncmp(name,"hea_",4))return 3;
    return 0;
}

static const char *pose_bone_name(unsigned handle)
{
    return SL_ConvertToString(handle);
}

/* Gameplay copies of priority parts (codol_pose_budget.c), built once per
 * source model. A DObj keeps pointing at its copy for as long as it lives, so
 * entries are never freed; a source whose identity changed gets a new entry. */
#define CODOL_POSE_VARIANTS 256
static struct {
    const XModel *source;
    const char *name;
    const xScriptString_t *names;
    unsigned char bones;
    XModel *pose;
} pose_variants[CODOL_POSE_VARIANTS];

static XModel *gameplay_pose_part(XModel *source)
{
    unsigned i,slot=CODOL_POSE_VARIANTS;
    for(i=0;i<CODOL_POSE_VARIANTS;++i) {
        if(!pose_variants[i].source) {
            if(slot==CODOL_POSE_VARIANTS)slot=i;
            continue;
        }
        if(pose_variants[i].source==source && pose_variants[i].name==source->name &&
           pose_variants[i].names==source->boneNames && pose_variants[i].bones==(unsigned char)source->numBones)
            return pose_variants[i].pose;
    }
    if(slot==CODOL_POSE_VARIANTS)return NULL;
    pose_variants[slot].source=source;
    pose_variants[slot].name=source->name;
    pose_variants[slot].names=source->boneNames;
    pose_variants[slot].bones=(unsigned char)source->numBones;
    pose_variants[slot].pose=CODOL_BuildGameplayPoseModel(source,pose_bone_name);
    if(pose_variants[slot].pose && CODOL_TRACE_ON())
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL server pose: %s reduced from %u to %u bones\n",source->name,
            (unsigned)(unsigned char)source->numBones,(unsigned)(unsigned char)pose_variants[slot].pose->numBones);
    return pose_variants[slot].pose;
}

/* Direct retained BG_UpdatePlayerDObj producer. The server DObj, like C1's,
 * takes DOBJ_MAX_BONES (253) bones with eight-word masks, and a stock CoDOL
 * outfit (168-191 bones) is posed whole, as the client draws it. The parts
 * gameplay reads come first - the root, then the jacket (torso and arm hit
 * boxes), the hands (weapon tags) and the head (head hit boxes, tag_eye) - so
 * that an outfit past 253 bones, which C1 itself cannot build, still keeps
 * them: a priority part that does not fit whole is posed from its gameplay
 * copy (codol_pose_budget.h) and only cosmetic parts are left out. The client
 * receives the complete appearance through its snapshot either way. */
unsigned CODOL_AppendCharacterDObjParts(const entityState_t *es,void *models,unsigned count,unsigned capacity)
{
    typedef struct {XModel *model;uint16_t tag;uint8_t ignoreCollision,pad;} part_t;
    part_t *out=(part_t *)models;
    unsigned i,pass,bones=0;
    const codol_character_pose_t *character;
    unsigned char used[CODOL_CHARACTER_PARTS]={0};
    _Static_assert(sizeof(part_t)==8,"retained DObj model stride");
    if(!es || es->number<0 || es->number>=MAX_GENTITIES)return 0;
    if(es->eType==ET_PLAYER && es->number<MAX_CLIENTS)character=&characters[es->number];
    else if(es->eType==ET_PLAYER_CORPSE)character=&corpse_characters[es->number];
    else return 0;
    if(!character->ready || !character->count)return 0;
    if(!models || !count || count>capacity || character->count-1>capacity-count)
        Com_Error(ERR_DROP,"CoDOL character exceeds native DObj model capacity");
    for(i=0;i<count;++i) {
        if(!out[i].model)Com_Error(ERR_DROP,"CoDOL character has a null native DObj model");
        bones+=(unsigned char)out[i].model->numBones;
    }
    if(bones>DOBJ_MAX_BONES)
        Com_Error(ERR_DROP,"CoDOL character root exceeds retained DObj bone capacity");
    for(pass=1;pass<=4;++pass) {
        for(i=1;i<character->count;++i) {
            unsigned model=character->model[i],priority;
            XModel *native=NULL;
            if(used[i])continue;
            if(model>=CODOL_NATIVE_MODELS || !(native=cached_models[model]))
                Com_Error(ERR_DROP,"CoDOL character part lost native model binding");
            priority=(unsigned)server_part_priority(native->name);
            if((pass<4 && priority!=pass) || (pass==4 && priority))continue;
            used[i]=1;
            if(bones+(unsigned char)native->numBones>DOBJ_MAX_BONES) {
                XModel *pose=priority ? gameplay_pose_part(native) : NULL;
                if(!pose || bones+(unsigned char)pose->numBones>DOBJ_MAX_BONES)continue;
                native=pose;
            }
            if(count>=capacity)Com_Error(ERR_DROP,"CoDOL character exceeds native DObj model capacity");
            out[count++]=(part_t){native,0,0,0};
            bones+=(unsigned char)native->numBones;
        }
    }
    return count;
}

int CODOL_SelectClientCharacterForWeapon(unsigned client,const char *faction,unsigned gender,
    const char *camo,const char *weapon)
{
    unsigned selector=0;
    /* An unresolved weapon leaves the selector at C1's own untouched value
     * rather than failing the whole character: the rig is one composition
     * slot, and rig 0 is a real selector, not a sentinel. */
    CODOL_WeaponRigSelector(weapon,&selector);
    return CODOL_SelectClientCharacter(client,faction,gender,camo,selector);
}

int CODOL_PublishStoredClientCharacter(unsigned client)
{
    codol_client_appearance_t appearance={0};
    unsigned i;
    if(client>=(unsigned)MAX_CLIENTS)return 0;
    if(!characters[client].ready || !characters[client].count)return 0;
    if(characters[client].count>CODOL_CLIENT_ATTACHMENTS+1)return -1;
    for(i=0;i<characters[client].count;++i) {
        /* Native slot -> CoDOL model bank slot. The bank is refreshed from the
         * native configstrings before a frame is built, so this must run after
         * that refresh; a name registered this frame has no wire ID yet and is
         * reported as a failure rather than published as slot zero. */
        int wire=CODOL_ServerModelToWire(characters[client].model[i]);
        if(wire<=0)return -1;
        if(!i)appearance.model=(unsigned)wire;
        else appearance.attach_model[i-1]=(unsigned)wire;
    }
    /* Every attachment tag stays zero. C1 bone-merges the character parts onto
     * the root's shared skeleton; there is no tag_* string for them. */
    return CODOL_PublishClientAppearance(client,&appearance) ? 1:-1;
}

int CODOL_ApplyStoredClientViewmodels(unsigned client,playerState_t *ps)
{
    if(client>=(unsigned)MAX_CLIENTS || !ps || ps->clientNum!=(int)client ||
       !characters[client].ready || !characters[client].arms)return 0;
    return CODOL_PlayerStateSetViewmodels(ps,characters[client].arms,
        characters[client].hands);
}

int CODOL_ClientCharacterModels(unsigned client,const unsigned **models,unsigned *count,
    unsigned *arms,unsigned *hands)
{
    if(client>=(unsigned)MAX_CLIENTS || !models || !count || !arms || !hands)return 0;
    if(!characters[client].ready)return 0;
    *models=characters[client].model;*count=characters[client].count;
    *arms=characters[client].arms;*hands=characters[client].hands;
    return 1;
}

void CODOL_ClearClientCharacter(unsigned client)
{
    if(client>=(unsigned)MAX_CLIENTS)return;
    memset(&characters[client],0,sizeof(characters[client]));
    voice_prefixes[client][0]=0;
    /* The playerState pair belongs to the extension, which clears it with the
     * rest of the client's per-connection state. */
    CODOL_PlayerStateExtClearClientViewhands(client);
}

void CODOL_ResetClientCharacters(void)
{
    unsigned i;
    memset(corpse_characters,0,sizeof(corpse_characters));
    for(i=0;i<(unsigned)MAX_CLIENTS;++i)memset(&characters[i],0,sizeof(characters[i]));
    memset(voice_prefixes,0,sizeof(voice_prefixes));
}
#endif
