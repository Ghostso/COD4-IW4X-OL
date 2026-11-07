/* CoDOL sound assets converted into retained IW3 objects.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 * The 108-byte CoDOL alias carries five names, one extra scalar before its
 * flags word and two more before the falloff curve, so no record is copied
 * wholesale; every field is placed individually. Fields with a measured role
 * fill their retained counterpart, and the rest, including the CoDOL flag word
 * and its channel index, reach the engine through the appended CoDOL block
 * rather than being renamed into IW3 fields. Sample payloads, sixteen-knot
 * falloff curves and speaker levels are converted, but nothing here
 * initializes an audio device or plays anything. */
#include "codol_sound_native.h"
#include "codol_assets.h"
#include "xassets/weapondef.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(snd_alias_list_t)==12,"native alias list ABI");
_Static_assert(offsetof(struct snd_alias_t,soundFile)==16,"native alias sound file");
_Static_assert(offsetof(struct snd_alias_t,volumeFalloffCurve)==72,"native alias curve");
_Static_assert(offsetof(struct snd_alias_t,speakerMap)==88,"native alias speaker map");
/* The CoDOL block is appended, so the IW3 prefix keeps its offsets. */
_Static_assert(offsetof(struct snd_alias_t,codol)==92,"CoDOL alias block placement");
_Static_assert(SND_CURVE_KNOTS>=16,"CoDOL curves carry up to sixteen knots");
_Static_assert(sizeof(struct SndCurve)==8+8*SND_CURVE_KNOTS,"native curve ABI");
_Static_assert(sizeof(SpeakerMap_t)==408,"native speaker map ABI");
_Static_assert(sizeof(LoadedSound_t)==44,"native loaded sound ABI");
_Static_assert(sizeof(AILSOUNDINFO)==36,"mss32 sound info ABI");
typedef struct { uint8_t *data; size_t pos; } packing_t;
static uint32_t u32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
/* Last failure site in this module, for the engine error path. Pure: no output. */
static int snd_fail_line;
static int snd_fail(int line) { if(!snd_fail_line) snd_fail_line=line; return -1; }
static int snd_fail0(int line) { if(!snd_fail_line) snd_fail_line=line; return 0; }
int CODOL_NativeSoundFailureLine(void) { return snd_fail_line; }
static char snd_fail_name[64];
const char *CODOL_NativeSoundFailureName(void) { return snd_fail_name; }
static int finite_float(uint32_t bits,float *out)
{
    float value;
    memcpy(&value,&bits,4);
    if(!isfinite(value)) return snd_fail0(__LINE__);
    *out=value; return 1;
}
static int part(packing_t *p,const void *data,size_t size,unsigned alignment,void **out)
{
    size_t at=(p->pos+alignment-1)&~(size_t)(alignment-1);
    if(at>CODOL_ASSET_LIMIT || size>CODOL_ASSET_LIMIT-at) return snd_fail0(__LINE__);
    *out=p->data ? p->data+at : NULL;
    if(p->data && data && size) memcpy(*out,data,size);
    p->pos=at+size; return 1;
}
static int copy_string(packing_t *p,const char *text,void **out)
{
    if(!text) { *out=NULL; return 1; }
    return part(p,text,strlen(text)+1,1,out);
}
/* Serialized speaker maps use the retained ChannelMap_t layout: an entry count
 * and six SpeakerLevels_t records of a speaker index, a level count and two
 * levels. Values are converted and range checked rather than copied blind. */
static int convert_speakers(const codol_speaker_map_t *source,SpeakerMap_t *out)
{
    unsigned map,entry;
    if(!source->channel_maps) return snd_fail0(__LINE__);
    for(map=0;map<4;++map) {
        const uint8_t *record=source->channel_maps+100*(size_t)map;
        uint32_t entries=u32(record);
        if(entries>6) return snd_fail0(__LINE__);
        for(entry=0;entry<6;++entry) {
            const uint8_t *levels=record+4+16*(size_t)entry;
            uint32_t speaker=u32(levels),count=u32(levels+4);
            float value[2];
            if(!finite_float(u32(levels+8),value) || !finite_float(u32(levels+12),value+1)) return snd_fail0(__LINE__);
            if(entry<entries && (count>2 || speaker>5)) return snd_fail0(__LINE__);
            if(out) {
                SpeakerLevels_t *native=out->channelMaps[map/2][map%2].speakers+entry;
                native->speaker=(int)speaker; native->numLevels=(int)count;
                native->levels[0]=value[0]; native->levels[1]=value[1];
            }
        }
        if(out) out->channelMaps[map/2][map%2].entryCount=(int)entries;
    }
    return 1;
}
static int pack_alias(packing_t *p,const codol_sound_alias_t *source,struct snd_alias_t *out,
    codol_native_sound_t *stats)
{
    void *names[4],*file=NULL,*loaded=NULL,*curve=NULL,*speakers=NULL,*text=NULL;
    void *stream_dir=NULL,*stream_name=NULL,*mixer=NULL;
    unsigned i;
    if(!source->names[0] || !*source->names[0]) return snd_fail0(__LINE__);
    for(i=0;i<4;++i) if(!copy_string(p,source->names[i],names+i)) return snd_fail0(__LINE__);
    if(source->has_file) {
        if(!part(p,NULL,sizeof(SoundFile_t),8,&file)) return snd_fail0(__LINE__);
        if(source->file.has_loaded) {
            const codol_loaded_sound_t *sound=&source->file.loaded;
            if(!sound->name || !*sound->name) return snd_fail0(__LINE__);
            /* Shipped zones carry empty placeholder sounds (",null.wav" with a
             * zero length and no payload); they convert with a null buffer.
             * A nonzero length without recovered bytes is malformed. */
            if(sound->data_length && !sound->payload) return snd_fail0(__LINE__);
            if(!part(p,NULL,sizeof(LoadedSound_t),4,&loaded) ||
                !copy_string(p,sound->name,&text)) return snd_fail0(__LINE__);
            if(p->data) {
                LoadedSound_t *native=loaded;
                /* CoDOL keeps one more word than the retained sound info, so
                 * every field is placed by name instead of copied wholesale. */
                native->name=text;
                native->sounds.ailInfo.format=(int)sound->format;
                native->sounds.ailInfo.data_ptr=sound->payload;
                native->sounds.ailInfo.data_len=sound->data_length;
                native->sounds.ailInfo.rate=sound->rate;
                native->sounds.ailInfo.bits=(int)sound->bits;
                native->sounds.ailInfo.channels=(int)sound->channels;
                native->sounds.ailInfo.samples=sound->samples;
                native->sounds.ailInfo.block_size=sound->block_size;
                native->sounds.ailInfo.initial_ptr=sound->payload;
                native->sounds.data=(void *)(uintptr_t)sound->payload;
            }
            ++stats->loaded_sounds;
        } else {
            /* C1 0x7384e0 validates the name and tolerates an empty
             * directory, so only the name is required here. */
            if(!source->file.name || !*source->file.name) return snd_fail0(__LINE__);
            if(!copy_string(p,source->file.dir,&stream_dir) ||
                !copy_string(p,source->file.name,&stream_name)) return snd_fail0(__LINE__);
            ++stats->streams;
        }
        if(p->data) {
            SoundFile_t *native=file;
            native->type=source->file.type; native->exists=source->file.exists;
            if(source->file.has_loaded) native->sound.loadSnd=loaded;
            else {
                /* CoDOL carries no localization flag, stream index or length,
                 * so those retained fields stay zero instead of invented. */
                native->sound.streamSnd.filename.info.raw.dir=stream_dir;
                native->sound.streamSnd.filename.info.raw.name=stream_name;
            }
        }
    }
    if(source->has_curve) {
        if(source->curve.knot_count>SND_CURVE_KNOTS) return snd_fail0(__LINE__);
        if(!part(p,NULL,sizeof(struct SndCurve),4,&curve) ||
            !copy_string(p,source->curve.name,&text)) return snd_fail0(__LINE__);
        if(p->data) {
            struct SndCurve *native=curve;
            native->filename=text; native->knotCount=(int)source->curve.knot_count;
            memcpy(native->knots,source->curve.knots,sizeof(float)*2*source->curve.knot_count);
        }
        ++stats->curves;
    }
    if(source->has_speakers) {
        if(!part(p,NULL,sizeof(SpeakerMap_t),4,&speakers) ||
            !copy_string(p,source->speakers.name,&text)) return snd_fail0(__LINE__);
        if(!convert_speakers(&source->speakers,speakers)) return snd_fail0(__LINE__);
        if(p->data) {
            SpeakerMap_t *native=speakers;
            native->isDefault=source->speakers.is_default; native->name=text;
        }
        ++stats->speaker_maps;
    }
    if(!copy_string(p,source->names[4],&mixer)) return snd_fail0(__LINE__);
    if(out) {
        out->aliasName=names[0]; out->subtitle=names[1];
        out->secondaryAliasName=names[2]; out->chainAliasName=names[3];
        out->soundFile=file; out->sequence=source->sequence;
        out->volMin=source->volume[0]; out->volMax=source->volume[1];
        out->pitchMin=source->pitch[0]; out->pitchMax=source->pitch[1];
        out->distMin=source->distance[0]; out->distMax=source->distance[1];
        out->probability=source->probability; out->startDelay=source->start_delay;
        out->volumeFalloffCurve=curve; out->speakerMap=speakers;
        /* IW3's flags word has no measured bit assignment, so it stays zero
         * and the CoDOL flag word is carried verbatim next to it, with the
         * measured looping bit and channel index reachable through the
         * SND_Alias* accessors. Nothing here reinterprets the unmeasured
         * bits or renames the unmeasured scalars. */
        out->codol.mixerName=mixer;
        out->codol.flags=source->flags;
        out->codol.priority=source->priority;
        out->codol.scalar34=source->unmeasured[0];
        out->codol.scalar40=source->unmeasured[1];
        out->codol.scalar44=source->unmeasured[2];
        out->codol.scalar4c=source->unmeasured[3];
        out->codol.scalar50=source->unmeasured[4];
        out->codol.scalar5c=source->unmeasured[5];
        out->codol.scalar60=source->unmeasured[6];
        out->codol.scalar64=source->unmeasured[7];
        out->codol.loadedSentinel=source->has_file && source->file.has_loaded ?
            source->file.loaded.sentinel : 0;
    }
    ++stats->aliases; return 1;
}
static int pack(const codol_sound_alias_list_t *source,codol_native_sound_t *stats,packing_t *p)
{
    snd_alias_list_t *list=(snd_alias_list_t *)p->data;
    struct snd_alias_t *aliases; void *memory,*name; unsigned i;
    p->pos=sizeof(snd_alias_list_t);
    stats->aliases=stats->loaded_sounds=stats->streams=stats->curves=stats->speaker_maps=0;
    if(!copy_string(p,source->name,&name)) return snd_fail0(__LINE__);
    if(!part(p,NULL,(size_t)source->count*sizeof(struct snd_alias_t),4,&memory)) return snd_fail0(__LINE__);
    aliases=memory;
    for(i=0;i<source->count;++i)
        if(!pack_alias(p,source->aliases+i,aliases ? aliases+i : NULL,stats)) return snd_fail0(__LINE__);
    if(p->pos>INT32_MAX) return snd_fail0(__LINE__);
    if(list) { list->aliasName=name; list->head=aliases; list->count=(int)source->count; }
    return 1;
}
void CODOL_FreeNativeSound(codol_native_sound_t *out)
{ if(out) { free(out->storage); memset(out,0,sizeof(*out)); } }
int CODOL_BuildNativeSoundAliasList(const codol_sound_alias_list_t *source,codol_native_sound_t *out)
{
    packing_t p={0}; codol_native_sound_t result={0};
    if(!source || !out || !source->name || !*source->name || *source->name==',' ||
        !source->count || !source->aliases ||
        source->count>CODOL_ASSET_LIMIT/sizeof(struct snd_alias_t)) return snd_fail0(__LINE__);
    if(!pack(source,&result,&p)) return snd_fail0(__LINE__);
    result.size=p.pos;
    if(!(result.storage=calloc(1,result.size))) return snd_fail0(__LINE__);
    p.data=result.storage;
    if(!pack(source,&result,&p) || p.pos!=result.size) { free(result.storage); return snd_fail0(__LINE__); }
    result.list=result.storage;
    CODOL_FreeNativeSound(out); *out=result; return 1;
}
snd_alias_list_t *CODOL_FindEngineSoundAlias(const char *name)
{
    const snd_alias_list_t *list=NULL;
    if(!name || !*name) return NULL;
    /* Absent and malformed both yield null here: the engine's find-alias
     * contract has no way to report a broken definition. */
    return CODOL_LoadEngineNativeSound(name,&list)==1 ? (snd_alias_list_t *)list : NULL;
}
typedef struct weapon_sound_cache_s {
    char *name;
    codol_weapon_sound_bindings_t bindings;
    struct weapon_sound_cache_s *next;
} weapon_sound_cache_t;
static weapon_sound_cache_t *weapon_sounds;
static int bind_sound(const char *name,snd_alias_list_t **slot,codol_weapon_sound_bindings_t *out)
{
    const snd_alias_list_t *alias; int status;
    if(!name || !*name) return 1;
    ++out->requested;
    status=CODOL_LoadEngineNativeSound(name,&alias);
    if(status<0) { strncpy(snd_fail_name,name,sizeof(snd_fail_name)-1); return snd_fail0(__LINE__); }
    /* CoDOL keeps alias assets in sound zones a dedicated server need not
     * mount. An unknown name is not a malformed definition. */
    if(!status) { ++out->absent; return 1; }
    *slot=(snd_alias_list_t *)alias; ++out->resolved; return 1;
}
int CODOL_BuildNativeWeaponSoundBindings(const codol_weapon_sounds_t *sounds,
    const codol_weapon_tail_t *tail,codol_weapon_sound_bindings_t *out)
{
    codol_weapon_sound_bindings_t bindings={0};
    unsigned i,j;
    if(!sounds || !tail || !out || tail->count>64) return snd_fail(__LINE__);
    for(i=0;i<CODOL_WEAPON_SOUND_SLOTS;++i)
        if(!bind_sound(sounds->names[i],bindings.names+i,&bindings)) return snd_fail(__LINE__);
    for(i=0;i<2;++i) for(j=0;j<CODOL_WEAPON_SOUND_SURFACES;++j)
        if(!bind_sound(sounds->arrays[i][j],bindings.arrays[i]+j,&bindings)) return snd_fail(__LINE__);
    for(i=0;i<tail->count;++i) {
        if(tail->entries[i].kind!=CODOL_WEAPON_DEP_SOUND) continue;
        if(bindings.tail_count>=CODOL_WEAPON_SOUND_TAIL) return snd_fail(__LINE__);
        bindings.tail_offsets[bindings.tail_count]=tail->entries[i].offset;
        if(!bind_sound(tail->entries[i].name,bindings.tail+bindings.tail_count,&bindings)) return snd_fail(__LINE__);
        ++bindings.tail_count;
    }
    *out=bindings; return 1;
}
int CODOL_LoadEngineWeaponSounds(const char *weapon,const codol_weapon_sounds_t *sounds,
    const codol_weapon_tail_t *tail,const codol_weapon_sound_bindings_t **out)
{
    codol_weapon_sound_bindings_t bindings;
    weapon_sound_cache_t *cached;
    snd_fail_line=0; /* Report the innermost failure of this request. */
    snd_fail_name[0]=0;
    CODOL_ResetSoundSourceFailure();
    if(!weapon || !*weapon || !sounds || !tail || !out || tail->count>64) return snd_fail(__LINE__);
    for(cached=weapon_sounds;cached;cached=cached->next)
        if(!strcmp(cached->name,weapon)) { *out=&cached->bindings; return 1; }
    if(CODOL_BuildNativeWeaponSoundBindings(sounds,tail,&bindings)!=1) return snd_fail(__LINE__);
    if(!(cached=calloc(1,sizeof(*cached)))) return snd_fail(__LINE__);
    if(!(cached->name=malloc(strlen(weapon)+1))) { free(cached); return snd_fail(__LINE__); }
    memcpy(cached->name,weapon,strlen(weapon)+1);
    cached->bindings=bindings; cached->next=weapon_sounds; weapon_sounds=cached;
    *out=&cached->bindings; return 1;
}
int CODOL_ApplyNativeWeaponSounds(const codol_weapon_sound_bindings_t *bindings,struct WeaponDef *out)
{
    /* CoDOL's 53 slots are IW3's 45 fields in the same order with three extra
     * slots interleaved (9 the akimbo fire variant, 12/13 the fire-loop end
     * pair) and five appended. Roles are established by C1 consumers and by
     * which shipped weapons populate each slot; see the pass report. */
    static const struct { unsigned slot; size_t field; } mapping[]={
        {0,offsetof(struct WeaponDef,pickupSound)},
        {1,offsetof(struct WeaponDef,pickupSoundPlayer)},
        {2,offsetof(struct WeaponDef,ammoPickupSound)},
        {3,offsetof(struct WeaponDef,ammoPickupSoundPlayer)},
        {4,offsetof(struct WeaponDef,projectileSound)},
        {5,offsetof(struct WeaponDef,pullbackSound)},
        {6,offsetof(struct WeaponDef,pullbackSoundPlayer)},
        {7,offsetof(struct WeaponDef,fireSound)},
        {8,offsetof(struct WeaponDef,fireSoundPlayer)},
        {10,offsetof(struct WeaponDef,fireLoopSound)},
        {11,offsetof(struct WeaponDef,fireLoopSoundPlayer)},
        {14,offsetof(struct WeaponDef,fireStopSound)},
        {15,offsetof(struct WeaponDef,fireStopSoundPlayer)},
        {16,offsetof(struct WeaponDef,fireLastSound)},
        {17,offsetof(struct WeaponDef,fireLastSoundPlayer)},
        {18,offsetof(struct WeaponDef,emptyFireSound)},
        {19,offsetof(struct WeaponDef,emptyFireSoundPlayer)},
        {20,offsetof(struct WeaponDef,meleeSwipeSound)},
        {21,offsetof(struct WeaponDef,meleeSwipeSoundPlayer)},
        {22,offsetof(struct WeaponDef,meleeHitSound)},
        {23,offsetof(struct WeaponDef,meleeMissSound)},
        {24,offsetof(struct WeaponDef,rechamberSound)},
        {25,offsetof(struct WeaponDef,rechamberSoundPlayer)},
        {26,offsetof(struct WeaponDef,reloadSound)},
        {27,offsetof(struct WeaponDef,reloadSoundPlayer)},
        {28,offsetof(struct WeaponDef,reloadEmptySound)},
        {29,offsetof(struct WeaponDef,reloadEmptySoundPlayer)},
        {30,offsetof(struct WeaponDef,reloadStartSound)},
        {31,offsetof(struct WeaponDef,reloadStartSoundPlayer)},
        {32,offsetof(struct WeaponDef,reloadEndSound)},
        {33,offsetof(struct WeaponDef,reloadEndSoundPlayer)},
        {34,offsetof(struct WeaponDef,detonateSound)},
        {35,offsetof(struct WeaponDef,detonateSoundPlayer)},
        {36,offsetof(struct WeaponDef,nightVisionWearSound)},
        {37,offsetof(struct WeaponDef,nightVisionWearSoundPlayer)},
        {38,offsetof(struct WeaponDef,nightVisionRemoveSound)},
        {39,offsetof(struct WeaponDef,nightVisionRemoveSoundPlayer)},
        {40,offsetof(struct WeaponDef,altSwitchSound)},
        {41,offsetof(struct WeaponDef,altSwitchSoundPlayer)},
        {42,offsetof(struct WeaponDef,raiseSound)},
        {43,offsetof(struct WeaponDef,raiseSoundPlayer)},
        {44,offsetof(struct WeaponDef,firstRaiseSound)},
        {45,offsetof(struct WeaponDef,firstRaiseSoundPlayer)},
        {46,offsetof(struct WeaponDef,putawaySound)},
        {47,offsetof(struct WeaponDef,putawaySoundPlayer)}
    };
    unsigned i,bounce=0;
    if(!bindings || !out || bindings->tail_count>CODOL_WEAPON_SOUND_TAIL) return 0;
    for(i=0;i<sizeof(mapping)/sizeof(mapping[0]);++i)
        *(snd_alias_list_t **)((char *)out+mapping[i].field)=bindings->names[mapping[i].slot];
    for(i=0;i<bindings->tail_count;++i) switch(bindings->tail_offsets[i]) {
    case 0x7c0: out->projExplosionSound=bindings->tail[i]; break;
    case 0x7c4: out->projDudSound=bindings->tail[i]; break;
    case 0x8f0: out->projIgnitionSound=bindings->tail[i]; break;
    default: break;
    }
    /* Surface bounce sounds keep the source's 31 entries. The caller retains
     * these bindings at a stable address for the definition's lifetime. */
    for(i=0;i<CODOL_WEAPON_SOUND_SURFACES;++i) if(bindings->arrays[0][i]) ++bounce;
    out->bounceSound=bounce ? (struct snd_alias_list_t **)bindings->arrays[0] : NULL;
    return 1;
}
void CODOL_ResetNativeWeaponSounds(void)
{
    while(weapon_sounds) {
        weapon_sound_cache_t *entry=weapon_sounds;
        weapon_sounds=entry->next; free(entry->name); free(entry);
    }
}
