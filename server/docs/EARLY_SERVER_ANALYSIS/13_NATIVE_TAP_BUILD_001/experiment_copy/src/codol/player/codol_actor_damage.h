#ifndef CODOL_ACTOR_DAMAGE_H
#define CODOL_ACTOR_DAMAGE_H
#include "g_shared.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_ActorPain(gentity_s *,gentity_s *,int,const float *,int,const float *,hitLocation_t,int);
void CODOL_ActorDie(gentity_s *,gentity_s *,gentity_s *,int,int,int,const float *,hitLocation_t,int);
#ifdef __cplusplus
}
#endif
#endif
