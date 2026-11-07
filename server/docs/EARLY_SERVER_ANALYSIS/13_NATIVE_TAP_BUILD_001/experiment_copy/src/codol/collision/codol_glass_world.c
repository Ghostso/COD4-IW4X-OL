/* Native C1 glass state, damage and snapshot capture.
 * Damage 523d80, impact packing 523b10/523a80, radius damage 523e20.
 * Client shard simulation remains C1's FxGlassSystem, driven by its section. */
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "q_math.h"
#include "cvar.h"
#include "server.h"
#include "g_shared.h"
#include "cm_public.h"
#include "cm_local.h"
#include "qcommon.h"
#include "codol_glass_world.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
extern byte __cdecl DirToByte(const vec3_t);

typedef struct {
    float origin[3],axis[3][3];
    unsigned damage;
    int change_time;
    codol_glass_wire_piece_t wire;
} piece_t;
static piece_t pieces[CODOL_GLASS_MAX_PIECES];
static unsigned piece_count;
static int map_ready;
unsigned char codol_glass_collision_state[CODOL_GLASS_MAX_PIECES];
static cvar_t *weaken,*destroy,*radius_multiplier,*melee_damage,*missile_shatter;

static void register_dvars(void)
{
    if (weaken) return;
    /* C1 5238d0: defaults25/100, minimum1, maximum65535.
     * Radius multiplier52392c..523960: default4, minFLT_MIN,maxFLT_MAX. */
    weaken=Cvar_RegisterInt("glass_damageToWeaken",25,1,65535,0,
        "Damage required to weaken a glass piece");
    destroy=Cvar_RegisterInt("glass_damageToDestroy",100,1,65535,0,
        "Damage required to destroy a glass piece");
    melee_damage=Cvar_RegisterInt("glass_meleeDamage",1000,1,65535,0,
        "Melee damage to a glass piece");
    radius_multiplier=Cvar_RegisterFloat("glass_radiusDamageMultiplier",4.0f,
        1.1754943508222875e-38f,3.4028234663852886e38f,0,
        "Explosion damage multiplier for glass");
    /* IW4 missileGlassShatterVel (466de6); C1 52df20: default 600, minimum 0,
     * maximum FLT_MAX, flags 0x84 (cheat). */
    missile_shatter=Cvar_RegisterFloat("missileGlassShatterVel",600.0f,0.0f,
        3.4028234663852886e38f,CVAR_CHEAT,
        "Minimum missile speed to shatter glass and fly through it");
}
float CODOL_GlassMissileShatterVelocity(void)
{
    register_dvars();
    return missile_shatter->value;
}
static unsigned u16(const unsigned char *p) { return p[0]|(unsigned)p[1]<<8; }
static float f32(const unsigned char *p) { float f;memcpy(&f,p,4);return f; }
static unsigned state(unsigned damage)
{
    if (damage==65535) return 3;
    if (damage>=(unsigned)destroy->integer) return 2;
    return damage>=(unsigned)weaken->integer;
}
void CODOL_GlassWorldReset(void)
{
    memset(pieces,0,sizeof(pieces));
    memset(codol_glass_collision_state,0,sizeof(codol_glass_collision_state));
    piece_count=0;
    map_ready=0;
}
int CODOL_GlassWorldEnsureMap(void)
{
    codol_glass_map_source_t source;
    char name[MAX_QPATH];
    int result;
    unsigned i;
    if (map_ready) return map_ready>0;
    if (!sv_mapname || !sv_mapname->string || !*sv_mapname->string) return 0;
    Com_GetBspFilename(name,sizeof(name),sv_mapname->string);
    result=CODOL_LoadMountedGlassMap(name,&source);
    if (result==1) {
        for (i=0;i<cm.numBrushes;++i) if (cm.brushes[i].glassPieceIndex>source.count) {
            result=-1;break;
        }
    }
    if (result!=1 || !CODOL_GlassWorldInstall(&source)) {
        map_ready=-1;
        Com_PrintWarning(CON_CHANNEL_SERVER,"CoDOL glass: cannot load complete map data for %s (%d)\n",name,result);
        return 0;
    }
    map_ready=1;
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL glass: installed %u pieces for %s\n",piece_count,name);
    return 1;
}
int CODOL_GlassWorldInstall(const codol_glass_map_source_t *source)
{
    piece_t *copy;
    unsigned i,j;
    if (!source || source->count>CODOL_GLASS_MAX_PIECES ||
        (source->count && (!source->initial_pieces || !source->server_pieces))) return 0;
    copy=source->count?calloc(source->count,sizeof(*copy)):NULL;
    if (source->count && !copy) return 0;
    register_dvars();
    for (i=0;i<source->count;++i) {
        const unsigned char *p=source->initial_pieces+52*i;
        const unsigned char *s=source->server_pieces+12*i;
        float quaternion[4],length=0;
        for (j=0;j<4;++j) {
            quaternion[j]=f32(p+4*j);
            if (!isfinite(quaternion[j])) goto fail;
            length+=quaternion[j]*quaternion[j];
        }
        if (!isfinite(length) || length<=0) goto fail;
        QuatToAxis(quaternion,copy[i].axis);
        for (j=0;j<3;++j) {
            copy[i].origin[j]=f32(p+16+4*j);
            if (!isfinite(copy[i].origin[j])) goto fail;
        }
        copy[i].damage=u16(s);
        copy[i].wire=(codol_glass_wire_piece_t){state(copy[i].damage),s[8],s[9],s[10]};
        if (copy[i].wire.state==2 && copy[i].wire.direction!=255 &&
            (copy[i].wire.impact_x>63 || copy[i].wire.impact_y>63)) goto fail;
    }
    CODOL_GlassWorldReset();
    if (source->count) memcpy(pieces,copy,source->count*sizeof(*copy));
    piece_count=source->count;
    for (i=0;i<piece_count;++i) codol_glass_collision_state[i]=pieces[i].wire.state;
    free(copy);return 1;
fail:
    free(copy);return 0;
}
unsigned CODOL_GlassWorldCount(void) { return piece_count; }
static unsigned coordinate(float value)
{
    /* C1 quantizes dot(hit-origin, axis) with floor(value*63/512+32). */
    float packed=floorf(value*0.123046875f+32.0f);
    if (packed<=0) return 0;
    if (packed>=63) return 63;
    return (unsigned)packed;
}
static int change_damage(unsigned index,unsigned damage,const float *position,
    const float *direction,int time)
{
    piece_t *p;
    unsigned next,j;
    float length=0,delta[3];
    if (index>=piece_count) return -1;
    p=pieces+index;
    p->damage=damage;
    next=state(p->damage);
    if (next==p->wire.state) return next;
    p->wire.state=next;p->change_time=time;
    codol_glass_collision_state[index]=(unsigned char)next;
    if (next!=2) return next;
    p->wire.direction=255;p->wire.impact_x=p->wire.impact_y=0;
    if (!position || !direction) return next;
    for (j=0;j<3;++j) {
        if (!isfinite(position[j]) || !isfinite(direction[j])) return next;
        length+=direction[j]*direction[j];
        delta[j]=position[j]-p->origin[j];
    }
    if (!isfinite(length) || length<=0) return next;
    p->wire.direction=DirToByte(direction);
    p->wire.impact_x=coordinate(DotProduct(delta,p->axis[0]));
    p->wire.impact_y=coordinate(DotProduct(delta,p->axis[1]));
    return next;
}
int CODOL_GlassWorldDamage(unsigned index,unsigned damage,const float *position,
    const float *direction,int time)
{
    unsigned total;
    if (index>=piece_count) return -1;
    if (!damage || pieces[index].wire.state>=2) return pieces[index].wire.state;
    total=damage>=65534-pieces[index].damage?65534:pieces[index].damage+damage;
    return change_damage(index,total,position,direction,time);
}
int CODOL_GlassWorldShatter(unsigned index,const float *direction,int time)
{
    if (index>=piece_count) return 0;
    if (pieces[index].wire.state<2)
        change_damage(index,(unsigned)destroy->integer,pieces[index].origin,direction,time);
    return 1;
}
/* IW4 412fc0 / C1 54a3a9..54a3f5: destroy an intact or weakened piece at a
 * measured impact. An already destroyed or removed piece is left unchanged. */
int CODOL_GlassWorldShatterAt(unsigned index,const float *position,
    const float *direction,int time)
{
    if (index>=piece_count) return 0;
    register_dvars();
    if (pieces[index].wire.state<2)
        change_damage(index,(unsigned)destroy->integer,position,direction,time);
    return 1;
}
int CODOL_GlassWorldOrigin(unsigned index,float *out)
{
    if (index>=piece_count || !out) return 0;
    VectorCopy(pieces[index].origin,out);return 1;
}
int CODOL_GlassWorldState(unsigned index)
{ return index<piece_count?pieces[index].wire.state:-1; }
int CODOL_GlassWorldRemove(unsigned index,int time)
{
    if (index>=piece_count) return 0;
    pieces[index].damage=65535;pieces[index].wire.state=3;
    pieces[index].change_time=time;codol_glass_collision_state[index]=3;
    return 1;
}
int CODOL_GlassWorldCollides(unsigned id)
{
    return !id || id>piece_count || codol_glass_collision_state[id-1]<2;
}
int CODOL_GlassWorldCapture(codol_glass_wire_piece_t *out,size_t capacity,unsigned *count)
{
    unsigned i;
    if (!count || capacity<piece_count || (piece_count && !out)) return 0;
    for (i=0;i<piece_count;++i) out[i]=pieces[i].wire;
    *count=piece_count;return 1;
}
void CODOL_GlassWorldRadiusDamage(const float *origin,float radius,float maximum,
    float minimum,const float *cone,float cone_cos,int time)
{
    unsigned i,j;
    if (!origin || !isfinite(radius) || radius<=0 || !isfinite(maximum) ||
        !isfinite(minimum) || minimum<0 || maximum<minimum) return;
    for (j=0;j<3;++j) if (!isfinite(origin[j])) return;
    /* 523e23..523e3e caps, rather than floors, radius at256 (C323AC).
     * The x87 CF comparison takes the store when256 < requested radius. */
    if (radius>256.0f) radius=256.0f;
    register_dvars();
    for (i=0;i<piece_count;++i) {
        float delta[3],distance,damage;
        if (pieces[i].wire.state>=2) continue;
        VectorSubtract(pieces[i].origin,origin,delta);
        distance=sqrtf(DotProduct(delta,delta));
        if (distance>radius) continue;
        if (distance>0) for (j=0;j<3;++j) delta[j]/=distance;
        if (cone && DotProduct(cone,delta)<cone_cos) continue;
        damage=(maximum+(minimum-maximum)*(distance/radius))*radius_multiplier->value;
        if (!isfinite(damage) || damage<=0) continue;
        CODOL_GlassWorldDamage(i,damage>=65534?65534:(unsigned)damage,
            pieces[i].origin,delta,time);
    }
}
void CODOL_GlassBulletDamage(const struct trace_s *trace,int damage,
    const float *position,const float *direction)
{
    if (!trace || trace->hitType!=TRACE_HITTYPE_GLASS || !trace->hitId ||
        damage<=0 || !CODOL_GlassWorldEnsureMap()) return;
    CODOL_GlassWorldDamage((unsigned)trace->hitId-1,(unsigned)damage,position,direction,level.time);
}
void CODOL_GlassExplosionDamage(const float *origin,float maximum,float minimum,
    float radius,float cone_cos,const float *cone)
{
    if (!CODOL_GlassWorldEnsureMap()) return;
    CODOL_GlassWorldRadiusDamage(origin,radius,maximum,minimum,cone,cone_cos,level.time);
}
void CODOL_GlassMeleeDamage(const struct trace_s *trace,const float *position,const float *direction)
{
    if (!trace || trace->hitType!=TRACE_HITTYPE_GLASS || !trace->hitId ||
        !CODOL_GlassWorldEnsureMap()) return;
    CODOL_GlassBulletDamage(trace,melee_damage->integer,position,direction);
}
#endif
