/* Native vision sets: five global builtins and five player methods.
 *
 * Contracts are taken from C1 1.1.1.13, with IW4 used only to recover the type
 * names its builtin table still carries. C1's own letters and configstrings are
 * used; IW4's differ and are never sent to a C1 client. */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "codol_sv_state.h"
#include "codol_script_vision.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

/* C1 0x517e91 copies 0x3f bytes into a 0x40-byte gclient slot and terminates
 * it. The command it sends still carries the script's own string. */
#define CODOL_VISION_NAME_CHARS 64
/* Bounds the reliable command and the configstring value. C1 formats through a
 * 1024-byte va buffer; this is a native input bound, not retail truncation. */
#define CODOL_VISION_NAME_LIMIT 1000

/* Command letters read from the receiving side, not from IW4: C1's client
 * command dispatcher 0x469320 maps 'N','O','P','Q','R' (and the unused sixth
 * '3') through the table at 0x46a118 onto the handlers 0x469b94, 0x469c3a,
 * 0x469c8a, 0x469cda, 0x469d2a, which call CG_SetVisionSetTransition
 * (0x47a1e0) with the type index 0..4. The sender's table is 0xc52f58.
 *
 * Note for the reliable channel as a whole: SV_SetClientStat in sv_client.c
 * also sends 'N' ("%c %i %i"), which a C1 client parses as this naked vision
 * command. That collision is a separate protocol gap, recorded rather than
 * papered over here; no substitute letter is guessed. */
static const char codol_vision_letters[CODOL_VISION_TYPES] = { 'N', 'O', 'P', 'Q', 'R' };

/* Mirrors the gclient storage C1 writes at client+0x38a0 (duration) and
 * client+0x38b8 (name), which is why it is cleared wherever the gclient is. */
static struct {
    char name[CODOL_VISION_NAME_CHARS];
    int duration;
} codol_player_vision[MAX_CLIENTS][CODOL_VISION_TYPES];

void CODOL_ResetPlayerVisionSets(unsigned client)
{
    if(client >= MAX_CLIENTS) return;
    memset(codol_player_vision[client], 0, sizeof(codol_player_vision[client]));
}

void CODOL_ResetAllPlayerVisionSets(void)
{
    memset(codol_player_vision, 0, sizeof(codol_player_vision));
}

const char *CODOL_PlayerVisionSetName(unsigned client, unsigned type)
{
    if(client >= MAX_CLIENTS || type >= CODOL_VISION_TYPES) return NULL;
    return codol_player_vision[client][type].name;
}

int CODOL_PlayerVisionSetDuration(unsigned client, unsigned type)
{
    if(client >= MAX_CLIENTS || type >= CODOL_VISION_TYPES) return 0;
    return codol_player_vision[client][type].duration;
}

/* C1 0x517e42..0x517e6b and 0x550417..0x550441 are the same sequence: the
 * script float is multiplied by 1000.0, the product is rounded back to a single
 * (fstp dword), 2^-30 is added, and fistp converts the sum with the default x87
 * control word - round to nearest, ties to even - not with truncation and not
 * with floor. A conversion that is not finite or does not fit in a signed 32-bit
 * integer produces the x87 integer indefinite, 0x80000000.
 *
 * Parent PE inspection: c842b0 holds 1000.0; c84590 holds bytes
 * 000000000000103e, or 2^-30, not the customary 0.5. The bias is exactly
 * representable in double at all single-precision halfway-integer values.
 * At larger magnitudes the single is already integral and losing the bias
 * cannot change round-to-nearest. rint follows the current rounding mode,
 * as fistp does. Runtime floating-point environment remains unvalidated. */
static int vision_milliseconds(float seconds)
{
    double scaled, rounded;

    scaled = (double)seconds * 1000.0;
    /* Well beyond the int range even after the single-precision store.
     * Check before narrowing so huge finite script floats need not overflow
     * a C double-to-float conversion. */
    if(!(scaled >= -4294967296.0) || !(scaled <= 4294967296.0)) return INT_MIN;
    scaled = (double)(float)scaled;
    if(scaled != scaled) return INT_MIN;
    rounded = rint(scaled + 0x1p-30);
    if(!(rounded >= -2147483648.0) || !(rounded <= 2147483647.0)) return INT_MIN;
    return (int)rounded;
}

/* Both C1 paths take the transition before the name and accept only one or two
 * parameters: one means 1000 ms (0x517dfb, 0x550480), two convert the second
 * (0x517e3d, 0x5504c5). Negative and indefinite results are passed through, as
 * they are by the engine. */
static int vision_transition(int *duration, const char *usage)
{
    int count = Scr_GetNumParam();
    if(count == 1) { *duration = 1000; return 1; }
    if(count == 2) { *duration = vision_milliseconds(Scr_GetFloat(1)); return 1; }
    Scr_Error(usage);
    return 0;
}

/* C1 validates nothing here and hands the script's string straight to va, so
 * the length bound and the refused characters below are a native input policy
 * for the reliable channel, not retail parity: they are exactly the bytes that
 * would otherwise change how the client re-tokenizes the command or the
 * configstring value back into its 0x40-byte slot. */
static const char *vision_name(void)
{
    const char *name = Scr_GetString(0);
    unsigned i;

    if(!name) { Scr_Error("Invalid parameters."); return NULL; }
    for(i = 0; name[i]; ++i) {
        if(i >= CODOL_VISION_NAME_LIMIT) {
            Scr_Error("Visionset name is too long");
            return NULL;
        }
        if((unsigned char)name[i] < 32 || name[i] == 127 || name[i] == '"' ||
           name[i] == '\\' || name[i] == ';') {
            Scr_Error(va("Invalid visionset name '%s'", name));
            return NULL;
        }
    }
    return name;
}

/* C1 0x517d70: the reference must be a plain entity that owns a client. The
 * gclient copy is truncated to 0x3f bytes (0x517e9a) but the command formatted
 * right after it at 0x517eb2 pushes the original script string, so the wire
 * carries the untruncated name and the receiving client applies its own
 * 0x40-byte limit (0x469bed). The command is quoted, carries milliseconds
 * (0xc52f60), and is sent reliably to that one client only. */
static void vision_set_for_player(scr_entref_t ref, unsigned type)
{
    char command[CODOL_VISION_NAME_LIMIT + 32];
    const char *name;
    int duration;

    if(ref.classnum) { Scr_ObjectError("not an entity"); return; }
    if(ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients ||
       !g_entities[ref.entnum].client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return;
    }
    if(!vision_transition(&duration,
        "USAGE: <player> VisionSet*ForPlayer( <visionset name>, <transition time> )")) return;
    if(!(name = vision_name())) return;

    Q_strncpyz(codol_player_vision[ref.entnum][type].name, name,
               sizeof(codol_player_vision[ref.entnum][type].name));
    codol_player_vision[ref.entnum][type].duration = duration;

    snprintf(command, sizeof(command), "%c \"%s\" %i",
             codol_vision_letters[type], name, duration);
    SV_GameSendServerCommand((int)ref.entnum, 1, command);
}

/* The global sets are gamestate. C1 publishes them with SV_SetConfigstring, but
 * the retained IW3 configstring array is not what a CoDOL client reads, so the
 * value goes into the CoDOL bank that builds the gamestate and is pushed to the
 * clients that already hold theirs. */
static void vision_publish(unsigned index, const char *value)
{
    codol_configstrings_t *bank = CODOL_ServerConfigstrings();
    const char *old = CODOL_GetConfigstring(bank, index);
    int i;

    if(old && !strcmp(old, value)) return;
    if(!CODOL_SetConfigstring(bank, index, value)) {
        Scr_Error("Could not set visionset");
        return;
    }
    if(!svs.clients || !sv_maxclients) return;
    for(i = 0; i < sv_maxclients->integer; ++i)
        if(svs.clients[i].state >= CS_PRIMED && svs.clients[i].gamestateSent)
            SV_SendServerCommandNoLoss(&svs.clients[i], "d %u %s", index, value);
}

/* C1's five global builtins - 0x550470 (naked, configstring 0x519), 0x550520
 * and the shared body 0x550380 (night and missilecam, 0x51a and 0x51b),
 * 0x550540 (thermal, 0x51c), 0x5505f0 (pain, 0x51d), plus 0x5506ee for the
 * sixth slot no script names - all format the value as the quoted name followed
 * by the transition (0xc59314) and report any other parameter count as
 * "Invalid parameters." (0xc5931c). They store nothing per player. C1's applier
 * 0x466b80 tokenizes that value back into the global slot and atoi's the second
 * token, which is why the name is not truncated on the way out. */
static void vision_set(unsigned type)
{
    char value[CODOL_VISION_NAME_LIMIT + 32];
    const char *name;
    int duration;

    if(!vision_transition(&duration, "Invalid parameters.")) return;
    if(!(name = vision_name())) return;

    snprintf(value, sizeof(value), "\"%s\" %i", name, duration);
    vision_publish(CODOL_CS_VISIONSET + type, value);
}

void CODOL_Scr_VisionSetNaked(void) { vision_set(CODOL_VISION_NAKED); }
void CODOL_Scr_VisionSetNight(void) { vision_set(CODOL_VISION_NIGHT); }
void CODOL_Scr_VisionSetMissileCam(void) { vision_set(CODOL_VISION_MISSILECAM); }
void CODOL_Scr_VisionSetThermal(void) { vision_set(CODOL_VISION_THERMAL); }
void CODOL_Scr_VisionSetPain(void) { vision_set(CODOL_VISION_PAIN); }

void CODOL_Scr_VisionSetNakedForPlayer(scr_entref_t ref)
{ vision_set_for_player(ref, CODOL_VISION_NAKED); }
void CODOL_Scr_VisionSetNightForPlayer(scr_entref_t ref)
{ vision_set_for_player(ref, CODOL_VISION_NIGHT); }
void CODOL_Scr_VisionSetMissileCamForPlayer(scr_entref_t ref)
{ vision_set_for_player(ref, CODOL_VISION_MISSILECAM); }
void CODOL_Scr_VisionSetThermalForPlayer(scr_entref_t ref)
{ vision_set_for_player(ref, CODOL_VISION_THERMAL); }
void CODOL_Scr_VisionSetPainForPlayer(scr_entref_t ref)
{ vision_set_for_player(ref, CODOL_VISION_PAIN); }

#endif
