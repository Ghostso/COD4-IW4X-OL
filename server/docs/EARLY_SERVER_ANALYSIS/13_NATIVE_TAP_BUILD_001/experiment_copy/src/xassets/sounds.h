#ifndef __SOUNDS_H__
#define __SOUNDS_H__

#include <stdint.h>

typedef enum 
{
  SAT_UNKNOWN = 0x0,
  SAT_LOADED = 0x1,
  SAT_STREAMED = 0x2,
  SAT_PRIMED = 0x3,
  SAT_COUNT = 0x4,
}snd_alias_type_t;


/* CoDOL curves carry up to sixteen knots (record +4 is a 16-bit count, C1
 * evaluator 0x7375b0, interpolation 0x618d80 with an 8-byte stride), so the
 * knot array is sized for the CoDOL source rather than IW3's eight. */
#define SND_CURVE_KNOTS 16

struct SndCurve
{
  const char *filename;
  int knotCount;
  float knots[SND_CURVE_KNOTS][2];
};


typedef struct SpeakerLevels_s
{
  int speaker;
  int numLevels;
  float levels[2];
}SpeakerLevels_t;
 
typedef struct ChannelMap_s
{
  int entryCount;	// how many entries are used
  SpeakerLevels_t speakers[6];
}ChannelMap_t;
 
typedef struct SpeakerMap_s
{
  byte isDefault;
  byte pad[3];
  const char *name;
  ChannelMap_t channelMaps[2][2];
}SpeakerMap_t;



typedef struct _AILSOUNDINFO
{
  signed int format;
  const void *data_ptr;
  unsigned int data_len;
  unsigned int rate;
  signed int bits;
  signed int channels;
  unsigned int samples;
  unsigned int block_size;
  const void *initial_ptr;
}AILSOUNDINFO;

typedef struct MssSound_s
{
  AILSOUNDINFO ailInfo;
  void *data;
}MssSound_t;

typedef struct LoadedSound_s
{
  const char *name;
  MssSound_t sounds;
}LoadedSound_t;


struct SoundFileInfo
{
  const char *sndfilename;
  MssSound_t ailsoundinfo;
};


typedef struct StreamFileNamePacked_s
{
  uint64_t offset;
  uint64_t length;
}StreamFileNamePacked_t;
 
typedef struct StreamFileNameRaw_s
{
  const char *dir;
  const char *name;
}StreamFileNameRaw_t;
 
typedef union StreamFileInfo_s
{
  StreamFileNameRaw_t raw;
  StreamFileNamePacked_t packed;
}StreamFileInfo_t;
 
typedef struct StreamFileName_s
{
  StreamFileInfo_t info;
  uint16_t isLocalized;
  uint16_t fileIndex;
}StreamFileName_t;
 
typedef struct StreamedSound_s
{
  StreamFileName_t filename;
  unsigned int totalMsec;
}StreamedSound_t;
 


typedef union SoundFileRef_s
{
    LoadedSound_t *loadSnd;
    StreamedSound_t streamSnd;
}SoundFileRef_t;


typedef struct SoundFile_s
{
    byte type;
    byte pad2[3];
    SoundFileRef_t sound;
    byte exists;
    byte pad[3];
}SoundFile_t;



/* CoDOL alias data with no IW3 field. Members are named for the CoDOL record
 * word they are read from unless a C1 consumer establishes the role, so no
 * IW3 meaning is implied for the unmeasured scalars. */
typedef struct SndAliasCodol_s
{
  const char *mixerName;      /* record +0x10, no measured consumer */
  unsigned int flags;         /* record +0x38, raw CoDOL flag word */
  unsigned char priority;     /* record +0x3c, compared with a global threshold */
  unsigned char pad[3];
  float scalar34;             /* record +0x34 */
  float scalar40, scalar44;   /* record +0x40, +0x44; +0x44 scales a mix level */
  float scalar4c, scalar50;   /* record +0x4c, +0x50 */
  float scalar5c, scalar60, scalar64; /* record +0x5c..+0x64 */
  unsigned int loadedSentinel; /* loaded sound record +0x1c, constant in shipped data */
} SndAliasCodol_t;

/* Measured CoDOL flag semantics. Bit 0 is the looping flag (C1 0x738665 and
 * 0x738330); bits 9..14 hold the mixer channel index (C1 0x738547). Bits
 * 3, 4, 5, 6, 7 and 8 are used by C1 but their roles are not established. */
#define SND_ALIAS_CODOL_LOOPING 0x1u
#define SND_ALIAS_CODOL_CHANNEL_SHIFT 9
#define SND_ALIAS_CODOL_CHANNEL_MASK 0x3fu
#define SND_AliasChannel(alias) (((alias)->codol.flags >> SND_ALIAS_CODOL_CHANNEL_SHIFT) & SND_ALIAS_CODOL_CHANNEL_MASK)
#define SND_AliasLooping(alias) (((alias)->codol.flags & SND_ALIAS_CODOL_LOOPING) != 0)

struct snd_alias_t
{
  const char *aliasName;
  const char *subtitle;
  const char *secondaryAliasName;
  const char *chainAliasName;
  SoundFile_t *soundFile;
  int sequence;
  float volMin;
  float volMax;
  float pitchMin;
  float pitchMax;
  float distMin;
  float distMax;
  int flags;                  /* IW3 bit assignment unmeasured; see codol.flags */
  float slavePercentage;
  float probability;
  float lfePercentage;
  float centerPercentage;
  int startDelay;
  struct SndCurve *volumeFalloffCurve;
  float envelopMin;
  float envelopMax;
  float envelopPercentage;
  SpeakerMap_t *speakerMap;
  SndAliasCodol_t codol;
};



typedef struct snd_alias_list_t
{
  const char *aliasName;
  struct snd_alias_t *head; //Can be multiple
  int count;
} snd_alias_list_t;

typedef union 
{
  int handle;
}SndEntHandle_t;


typedef struct
{
  struct snd_alias_t *alias0;
  struct snd_alias_t *alias1;
  float lerp;
  SndEntHandle_t sndEnt;
  float org[3];
  float volume;
  float pitch;
  int timeshift;
  float fraction;
  int startDelay;
  byte master;
  byte timescale;
  byte pad[2];
  snd_alias_system_t system;
}SndStartAliasInfo_t;

#ifdef __cplusplus
extern "C"{
#endif


struct snd_alias_t *__cdecl _Com_PickSoundAliasFromList(struct snd_alias_list_t *sndaliaslist);
void SND_PlayAmbientAlias(struct snd_alias_t *alias, int localClientNum, int fadetime);




typedef struct snd_alias_list_t *snd_alias_list_name;

void __cdecl Com_UnloadSoundAliases(snd_alias_system_t type);
#ifdef __cplusplus
}
#endif

#endif
