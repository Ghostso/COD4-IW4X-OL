#ifndef __BG_PUBLIC_H__
#define __BG_PUBLIC_H__

#include "entity.h"
#include "cm_public.h"
#include "xassets/weapondef.h"

void __cdecl BG_EvaluateTrajectory(trajectory_t *tr, int atTime, float *result);
void __cdecl BG_ShutdownWeaponDefFiles();
const char *__cdecl BG_WeaponName(int weapon);

#ifdef __cplusplus
extern "C"{
#endif

struct WeaponDef *__cdecl BG_GetWeaponDef(int weapon);

#ifdef __cplusplus
};
#endif


struct DObjModel_s;

struct pmove_t
{
  struct playerState_s *ps;
  usercmd_t cmd;
  usercmd_t oldcmd;
  int tracemask;
  int numtouch;
  int touchents[32];
  vec3_t mins;
  vec3_t maxs;
  float xyspeed;
  int proneChange;
  float maxSprintTimeMultiplier;
  byte mantleStarted;
  char pad1[3];
  vec3_t mantleEndPos;
  int mantleDuration;
  int viewChangeTime;
  float viewChange;
  char handler;
  char pad2[3];
};

struct pml_t
{
  vec3_t forward;
  vec3_t right;
  vec3_t up;
  float frametime;
  int msec;
  int walking;
  int groundPlane;
  int almostGroundPlane;
  trace_t groundTrace;
  float impactSpeed;
  vec3_t previous_origin;
  vec3_t previous_velocity;
};

/*
#pragma pack(push, 8)
struct animation_s
{
  char name[64];
  int initialLerp;
  float moveSpeed;
  int duration;
  int nameHash;
  int flags;
  int pad1;
  int64_t movetype;
  int noteType;
  int pad2;
};
#pragma pack(pop)

#pragma pack(push, 8)
struct animScriptData_t
{
  animation_s animations[512];
  unsigned int numAnimations;
  animScript_t scriptAnims[1][43];
  animScript_t scriptCannedAnims[1][43];
  animScript_t scriptStateChange[1][1];
  animScript_t scriptEvents[21];
  animScriptItem_t scriptItems[2048];
  int numScriptItems;
  scr_animtree_t animTree;
  unsigned __int16 torsoAnim;
  unsigned __int16 legsAnim;
  unsigned __int16 turningAnim;
  snd_alias_list_t *(__cdecl *soundAlias)(const char *);
  int (__cdecl *playSoundAlias)(int, snd_alias_list_t *);
};
#pragma pack(pop)



#pragma pack(push, 1)
struct __align(8) bgs_s
{
  animScriptData_t animScriptData;
  bodyAnim_t generic_human;
  int time;
  int latestSnapshotTime;
  int frametime;
  int anim_user;
  XModel *(__cdecl *GetXModel)(const char *);
  void (__cdecl *CreateDObj)(DObjModel_s *, unsigned int int16_t, XAnimTree_s *, int, int, clientInfo_t *);
  uint16_t (__cdecl *AttachWeapon)(DObjModel_s *, uint16_t, clientInfo_t *);
  DObj_s *(__cdecl *GetDObj)(int, int);
  void (__cdecl *SafeDObjFree)(int, int);
  void *(__cdecl *AllocXAnim)(int);
  clientInfo_t clientinfo[64];
};
#pragma pack(pop)
*/

struct __align(8) bgs_s
{
  /* 0x999cc, NOT IW3's 0x9a9d0. This array exists only to place the fields
   * after it, and it was 0x1004 too long, so every clientinfo access through
   * this header hit the wrong address. MEASURED four ways that clientinfo[0]
   * sits at bgs+0x99a04 with stride 0x4cc:
   *   _g_misc_mp.asm:1495  lea edx,[ecx+edx*4+0x99a00] then lea eax,[edx+4]
   *   codol_animation_tables.c:121  clientConditions at bgs+0x99e5c = +0x458
   *   _bg_animation_mp.asm:320      legs at ci+0x37c
   *   _g_main_mp.asm:1848  level_bgs: resb 0xacd20 = 0x99a04 + 64*0x4cc exactly
   * Measured consequences of the old value: codol_player_appearance.c wrote
   * dobjDirty to 0x9adfc instead of 0x99df8, so it was never set and the store
   * landed in an unrelated clientinfo slot; and codol_pmove_c1_ground.c put
   * clientNum 63 past the end of level_bgs -- a .bss overwrite.
   *
   * level_bgs is allocated in asm (resb), so the C sizeof is not load-bearing;
   * only the field offsets are.
   *
   * Do NOT also shrink clientControllers_s or clientInfo_t. They are already
   * correct: verified with the compiler that clientConditions is at ci+0x458,
   * pXAnimTree at ci+0x4a8, sizeof(clientInfo_t) 0x4cc and legs at ci+0x37c.
   * A proposed patch that shrank them by 4 alongside this would have broken a
   * layout that already matched the assembly. */
  byte animScriptData[0x999cc];
  byte generic_human[0x10];
  int time;
  int latestSnapshotTime;
  int frametime;
  int anim_user;
  struct XModel *(__cdecl *GetXModel)(const char *);
  void (__cdecl *CreateDObj)(struct DObjModel_s *, uint16_t, struct XAnimTree_s *, int, int, struct clientInfo_t *);
  uint16_t (__cdecl *AttachWeapon)(struct DObjModel_s *, uint16_t, struct clientInfo_t *);
  struct DObj_s *(__cdecl *GetDObj)(int, int);
  void (__cdecl *SafeDObjFree)(int, int);
  void *(__cdecl *AllocXAnim)(int);
  struct clientInfo_t clientinfo[64];
};

extern struct bgs_s level_bgs;
extern struct bgs_s *bgs;
#endif


