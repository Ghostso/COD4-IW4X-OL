#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_game.h"

/* T5 6067f0..606ac0 OR held buttons with accumulated rising edges.
 * C1 action IDs are translated when received, never copied as T5 bit IDs. */
static void action_slot_pressed(scr_entref_t ref,unsigned slot)
{
    gentity_t *entity;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS) {
        Scr_ObjectError("Action slot query requires a player");return;
    }
    entity=&g_entities[ref.entnum];
    if(!entity->client){Scr_ObjectError("Action slot query requires a player");return;}
    /* Native ClientThink suppresses non-selection buttons in this mode. */
    Scr_AddInt(!entity->client->ps.locationSelectionInfo &&
               (CODOL_ActionSlotButtons(ref.entnum)&(1u<<slot))!=0);
}
void CODOL_Scr_ActionSlotOneButtonPressed(scr_entref_t ref){action_slot_pressed(ref,0);}
void CODOL_Scr_ActionSlotTwoButtonPressed(scr_entref_t ref){action_slot_pressed(ref,1);}
void CODOL_Scr_ActionSlotThreeButtonPressed(scr_entref_t ref){action_slot_pressed(ref,2);}
void CODOL_Scr_ActionSlotFourButtonPressed(scr_entref_t ref){action_slot_pressed(ref,3);}
#endif
