#ifndef CODOL_ACTOR_DELIVERY_H
#define CODOL_ACTOR_DELIVERY_H
#include "codol_actor_anim_journal.h"
#include "codol_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_ActorDeliveryReset(void);
void CODOL_ActorDeliveryClear(unsigned client);
int CODOL_ActorDeliveryArchive(int frame,unsigned time);
int CODOL_ActorDeliveryCapture(unsigned client,unsigned sequence,int frame,unsigned time);
int CODOL_ActorDeliveryPrepare(unsigned client,unsigned sequence,unsigned acknowledged,
 const codol_entity_state_t *entities,unsigned count,codol_animcmd_t *out,unsigned capacity,unsigned *written);
#ifdef __cplusplus
}
#endif
#endif
