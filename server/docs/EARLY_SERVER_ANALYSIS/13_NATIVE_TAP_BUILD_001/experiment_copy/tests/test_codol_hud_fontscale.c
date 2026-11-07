#include "scr_vm_functions.h"
#include "g_hud.h"
#include "codol_hud_fontscale.h"
#include "codol_engine_state.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
qboolean Assert_MyHandler(const char *e,const char *f,int l,const char *fn,const char *fmt,...)
{ fprintf(stderr,"%s:%d: %s\n",f,l,e); abort(); }
game_hudelem_t g_hudelems[1024];
gentity_t g_entities[MAX_GENTITIES];
level_locals_t level;
static gclient_t player;
static float seconds;
static unsigned errors;
float Scr_GetFloat(unsigned i) { assert(!i); return seconds; }
void Scr_ObjectError(const char *s) { assert(s); ++errors; }
void Scr_ParamError(int i,const char *s) { assert(!i && s); ++errors; }
void Scr_Error(const char *s) { assert(s); ++errors; }
void CODOL_HudSetFontScale(game_hudelem_t *,int);
void HudElem_UpdateClient(gclient_t *,int,enum hudelem_update_t);
static uint32_t field(const codol_hud_element_t *wire,unsigned offset)
{
    unsigned i; for(i=0;i<CODOL_HUD_FIELDS;++i) if(CODOL_HudFieldOffset(i)==offset) return wire->field[i];
    assert(0); return 0;
}
int main(void)
{
    scr_entref_t ref={0}; codol_hud_fontscale_t scale,before;
    codol_hud_element_t wire; codol_hud_bindings_t bindings={0}; hudElemState_t detached;
    ref.classnum=1; ref.entnum=4;
    HudElem_SetDefaults(&g_hudelems[4]); g_hudelems[4].clientNum=ENTITYNUM_NONE;
    level.time=1000; seconds=2; CODOL_Scr_ChangeFontScaleOverTime(ref);
    assert(CODOL_GetHudFontScale(&g_hudelems[4].elem,&scale));
    assert(scale.from==1 && scale.start==1000 && scale.duration==2000);
    g_hudelems[4].elem.fontScale=3; level.time=2000; seconds=1;
    CODOL_Scr_ChangeFontScaleOverTime(ref);
    assert(CODOL_GetHudFontScale(&g_hudelems[4].elem,&scale));
    assert(scale.from==2 && scale.start==2000 && scale.duration==1000);
    g_hudelems[4].elem.fontScale=4;
    level.maxclients=1; level.gentities=g_entities; g_entities[0].r.inuse=1;
    HudElem_UpdateClient(&player,0,3);
    assert(CODOL_GetHudFontScale(&player.ps.hud.archival[0],&before));
    assert(!memcmp(&before,&scale,sizeof(scale)));
    bindings.font_scale_from=before.from; bindings.font_scale_start=before.start; bindings.font_scale_duration=before.duration;
    assert(CODOL_BuildEngineHudElement(&wire,&player.ps.hud.archival[0],&bindings));
    { float f; uint32_t bits=field(&wire,0x18); memcpy(&f,&bits,4); assert(f==2); }
    assert(field(&wire,0x1c)==2000 && field(&wire,0x20)==1000);
    detached=player.ps.hud; assert(!CODOL_GetHudFontScale(&detached.archival[0],&scale));
    /* Captured client metadata must survive modification/reuse of its source. */
    HudElem_SetDefaults(&g_hudelems[4]);
    assert(CODOL_GetHudFontScale(&g_hudelems[4].elem,&scale) && !scale.duration);
    assert(CODOL_GetHudFontScale(&player.ps.hud.archival[0],&scale) && scale.duration==1000);
    seconds=0; CODOL_Scr_ChangeFontScaleOverTime(ref);
    seconds=NAN; CODOL_Scr_ChangeFontScaleOverTime(ref);
    seconds=61; CODOL_Scr_ChangeFontScaleOverTime(ref); assert(errors==3);
    ref.classnum=0; CODOL_Scr_ChangeFontScaleOverTime(ref); assert(errors==4);
    CODOL_ResetHudFontScales();
    assert(!CODOL_GetHudFontScale(&player.ps.hud.archival[0],&scale));
    seconds=0.8f; CODOL_HudSetFontScale(&g_hudelems[4],0); assert(g_hudelems[4].elem.fontScale==0.8f);
    seconds=0; CODOL_HudSetFontScale(&g_hudelems[4],0);
    seconds=NAN; CODOL_HudSetFontScale(&g_hudelems[4],0);
    assert(errors==6 && g_hudelems[4].elem.fontScale==0.8f);
    puts("PASS: HUD font interpolation interruption, native client capture, CoDOL fields, identity and reset");
}
