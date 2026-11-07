/* Native setblurforplayer and setcarddisplayslot.
 *
 * Argument order, error text, numeric conversion, wire format and command
 * letters are all read from the reference binaries: IW4 for the builtin names
 * and the explicit parameter indices it passes to Scr_ParamError, C1 1.1.1.13
 * for the wire, the bounds and the receivers. Where the two disagree - the
 * command letters and the card slot bound - C1 wins, because C1 is what reads
 * these commands. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "codol_script_player_presentation.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* C1 0x518221: fld <seconds>; fmul qword [0xc842b0] (1000.0); call 0xae0410.
 * 0xae0410 is MSVC's _ftol2: the SSE2 path is cvttsd2si and the x87 path is the
 * matching truncating fixup, so the conversion truncates toward zero rather
 * than rounding, and an input that is not finite or does not fit a signed
 * 32-bit integer produces the integer indefinite 0x80000000. That is a
 * different conversion from the one the vision builtins use, so it is
 * reproduced separately rather than shared.
 *
 * The double arithmetic is exact here for every value that can reach an int: a
 * single times 1000.0 needs at most 31 significant bits, so the product is
 * exact in double and equals what the x87 computes in extended precision.
 * Casting the double directly would be undefined outside int range, so the
 * range test comes first. */
int CODOL_BlurMilliseconds(float seconds)
{
    double scaled, truncated;

    scaled = (double)seconds * 1000.0;
    if(scaled != scaled) return INT_MIN;
    truncated = trunc(scaled);
    if(!(truncated >= -2147483648.0) || !(truncated <= 2147483647.0)) return INT_MIN;
    return (int)truncated;
}

/* C1 0x51827b..0x5182ca formats va("%c %i %f %i %i", 'i', ms, blur, 0, 1) and
 * sends it reliably to one client. The blur value reaches the format as a
 * double promoted from the script single (fld dword; fstp qword), which is what
 * passing a float through varargs does here as well. The receiver 0x468830
 * reads argv[1] with atoi, argv[2] with atof and argv[3]/argv[4] with atoi. */
int CODOL_SendPlayerBlur(unsigned client, float blur, int milliseconds)
{
    char command[128];

    if(client >= MAX_CLIENTS) return 0;
    snprintf(command, sizeof(command), "%c %i %f %i %i",
             CODOL_BLUR_COMMAND_LETTER, milliseconds, (double)blur,
             CODOL_BLUR_COMMAND_SELECTOR, CODOL_BLUR_COMMAND_PRIORITY);
    SV_GameSendServerCommand((int)client, 1, command);
    return 1;
}

/* C1 0x51e2d1..0x51e31a formats _snprintf(buf, 0x40, "%c %i %i", 'L',
 * cardPlayer->s.number, slot) and sends it reliably to the calling player. The
 * receiver 0x469af1 takes argv[1] as the client number whose card is shown and
 * argv[2] as the slot. */
int CODOL_SendCardDisplaySlot(unsigned viewer, int card_client, int slot)
{
    char command[64];

    if(viewer >= MAX_CLIENTS) return 0;
    snprintf(command, sizeof(command), "%c %i %i",
             CODOL_CARD_SLOT_COMMAND_LETTER, card_client, slot);
    SV_GameSendServerCommand((int)viewer, 1, command);
    return 1;
}

/* Shared by both methods: the self reference must be a plain entity that owns a
 * client (C1 blur 0x518143..0x51816e, card 0x51e175..0x51e19a; the card handler
 * tests entnum*0x2cc + 0x220d12c, which is gentity + 0x17c, the client
 * pointer). The messages are the engines' own. */
static int presentation_player(scr_entref_t ref)
{
    if(ref.classnum) { Scr_ObjectError("not an entity"); return 0; }
    if(ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return 0;
    }
    return 1;
}

/* C1 0x518130 / IW4 0x5dc9a0.
 *
 * Parameter 0 is the blur value and parameter 1 is the time in seconds; the
 * engines read them in that order (C1 0x5181b7 and 0x5181c2) and neither gates
 * on Scr_GetNumParam - a missing parameter is reported by the parameter fetch
 * itself, which IW4OL's Scr_GetFloat does the same way.
 *
 * Both checks are "0 > value", so zero is accepted, which the MP scripts rely
 * on (`self setblurforplayer( 0, 0.3 )`). IW4 passes the parameter indices to
 * Scr_ParamError explicitly - 1 for the time (0x5dca18) and 0 for the blur
 * (0x5dca45) - so those indices are used here rather than C1's internal
 * one-based encoding of the same thing.
 *
 * The recipient: C1 takes it from a gentity field (0x518296 reads gentity+0x9c;
 * IW4 reads gentity+0x94 at 0x5dca6a) while IW4's card builtin sends to the
 * script entity number directly, so for a player entity the two are the same
 * value. The validated player's client number is used; the exact name of that
 * gentity field was not resolved and is not relied on. */
void CODOL_Scr_SetBlurForPlayer(scr_entref_t ref)
{
    float blur, seconds;
    int milliseconds;

    if(!presentation_player(ref)) return;

    blur = Scr_GetFloat(0);
    seconds = Scr_GetFloat(1);

    if(0 > seconds) { Scr_ParamError(1, "Time must be positive"); return; }
    milliseconds = CODOL_BlurMilliseconds(seconds);
    if(0 > blur) { Scr_ParamError(0, "Blur value must be greater than 0"); return; }

    CODOL_SendPlayerBlur(ref.entnum, blur, milliseconds);
}

/* C1 0x51e150 / IW4 0x5df250.
 *
 * Parameter 0 is the player whose card is displayed and parameter 1 is the
 * slot. The parameter entity must own a client - "Player provided is not a
 * client." (C1 0xc53800, IW4 0x6f2380) - and the slot must satisfy
 * 0 <= slot < 0x13 in C1 (0x51e28c), which is one more slot than IW4's 0x12
 * (0x5df2cd). C1's bound is used because C1's receiver 0x469af1 is the one
 * indexing the table, and its stride confirms 0x13 records per local client.
 * The message keeps the engine's own wording, including passing the bound
 * itself as the second value. */
void CODOL_Scr_SetCardDisplaySlot(scr_entref_t ref)
{
    gentity_t *card_player;
    int slot;

    if(!presentation_player(ref)) return;

    card_player = Scr_GetEntity(0);
    if(!card_player || !card_player->client) {
        Scr_Error("Player provided is not a client.");
        return;
    }

    slot = Scr_GetInt(1);
    if(slot < 0 || slot >= CODOL_CARD_DISPLAY_SLOTS) {
        Scr_Error(va("Invalid slot number %i, must be between 0 and %i.",
                     slot, CODOL_CARD_DISPLAY_SLOTS));
        return;
    }

    CODOL_SendCardDisplaySlot(ref.entnum, card_player->s.number, slot);
}

#endif
