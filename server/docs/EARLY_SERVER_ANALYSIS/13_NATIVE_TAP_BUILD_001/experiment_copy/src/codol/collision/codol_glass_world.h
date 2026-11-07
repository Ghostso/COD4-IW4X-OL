/* Authoritative glass state, separate from client shard simulation. */
#ifndef CODOL_GLASS_WORLD_H
#define CODOL_GLASS_WORLD_H
#include "codol_glass_map.h"
#include "codol_glass_snapshot.h"
/* One-based brush/trace IDs versus zero-based script/wire IDs are explicit. */
int CODOL_GlassWorldInstall(const codol_glass_map_source_t *);
int CODOL_GlassWorldEnsureMap(void);
void CODOL_GlassWorldReset(void);
unsigned CODOL_GlassWorldCount(void);
int CODOL_GlassWorldDamage(unsigned piece, unsigned damage, const float *position,
    const float *direction, int time);
void CODOL_GlassWorldRadiusDamage(const float *origin,float radius,
    float maximum,float minimum,const float *cone,float cone_cos,int time);
int CODOL_GlassWorldRemove(unsigned piece,int time);
int CODOL_GlassWorldShatter(unsigned piece,const float *direction,int time);
float CODOL_GlassMissileShatterVelocity(void);
int CODOL_GlassWorldShatterAt(unsigned piece,const float *position,
    const float *direction,int time);
int CODOL_GlassWorldOrigin(unsigned piece,float *out);
int CODOL_GlassWorldState(unsigned piece);
int CODOL_GlassWorldCollides(unsigned one_based_id);
int CODOL_GlassWorldCapture(codol_glass_wire_piece_t *,size_t capacity,unsigned *count);
struct trace_s;
void CODOL_GlassBulletDamage(const struct trace_s *,int damage,const float *position,
    const float *direction);
void CODOL_GlassMeleeDamage(const struct trace_s *,const float *position,const float *direction);
void CODOL_GlassExplosionDamage(const float *origin,float maximum,float minimum,
    float radius,float cone_cos,const float *cone);
/* Collision leaf routines read this byte array using one_based_id-1. It is
 * zeroed on reset, so an uninitialized map never silently loses collision. */
extern unsigned char codol_glass_collision_state[CODOL_GLASS_MAX_PIECES];
#endif
