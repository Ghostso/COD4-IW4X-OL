/* C1 ADS sway phase: the server-side producer of playerState +0x4a0.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * C1 draws a scoped weapon's idle sway from an integer phase accumulator at
 * cg+0xBF980, as sin(phase*0.001) for yaw and sin(phase*0.0007) for pitch,
 * scaled by stanceRamp * maxAngle * fWeaponPosFrac * holdBreathScale
 * (BG_AddIdleSway 0x00424C10). Measured live out of C1 (4169 rendered frames,
 * docs/captures/sway_live3.jsonl), that accumulator is
 *
 *     phase = 3.00 x (predicted ps.commandTime - snapshot ps.commandTime)
 *
 * with a seed of EXACTLY ZERO, rebuilt on every rendered frame. It is not a
 * free-running accumulator: it is re-seeded from the wire and then replayed
 * forward through CG_PredictPlayerState's usercmd loop. The seed is
 * playerState +0x4a0 - netfield index 4, encoding -70, changeHint 3 - which
 * this server has never produced, so the client seeds 0 every snapshot and the
 * drawn sway saw-tooths at the snapshot rate. That is the jitter.
 * Full analysis: docs/CODOL_SWAY_CAUSE_SWEEP_20260916.md.
 *
 * WHY +0x4a0 IS THE PHASE AND NOT A TIMESTAMP
 * -------------------------------------------
 * Encoding -70 shares its wire format with -97 (serverTime - value in 1+8 bits
 * when the difference is 0..255, else a full long; codol_delta.c:136), and -97
 * is what commandTime and eight other timestamps use. That looks like a time
 * codec, which would argue the field carries an epoch rather than a fast
 * accumulator. The live measurement settles it the other way: the client's
 * phase equals the wire value PLUS the replayed span, i.e. the wire value is
 * assigned straight into the accumulator. An epoch would have to be
 * differenced, and a zero epoch would then have produced phase ~ 3*commandTime
 * (six figures), not the measured 3*span.
 *   The codec is reconciled by seeding the accumulator FROM commandTime rather
 * than from zero: the value then starts within 255 of serverTime, takes the
 * cheap 9-bit arm at the start of every aim-down-sights, and falls through to
 * the 33-bit arm as it drifts ahead at (2*speed - 1) units per ms. That is
 * also why -70 exists as a separate code from -97 at all: it is the only
 * field carrying it, which is what lets C1's send predicate hang the
 * "force-send whenever fWeaponPosFrac != 0" rule on exactly this field
 * (codol_playerstate.c:50, ported from C1 0x5a44b0).
 *   The absolute value is cosmetically irrelevant - only sin() of it is drawn -
 * so seeding from commandTime costs nothing and buys the cheap arm.
 *
 * THE RATE, AND ITS DELIBERATE ASYMMETRY
 * --------------------------------------
 * C1 advances the phase TWICE per replayed usercmd, in 0x0045E830:
 *
 *   0x0045E849  if (cg[0xBF984] == 0) return;
 *   0x0045E852  def = (ps.weapFlags & 2) ? ps[0x328] : ps[0x33c];
 *   0x0045E86B  if (!def) return;
 *   0x0045E87B  call BG_AdvanceSwayPhase 0x00424B90
 *                  -> gated on def[0x694] != 0 AND ps.fWeaponPosFrac != 0.0f
 *                  -> phase += (int)(holdBreathScale * dt * 1000 * speed)
 *   0x0045E88C  call BG_GetSwayParams 0x00422FE0
 *   0x0045E8A5  phase += (int)(dt * 1000 * speed)   <-- SECOND ADD
 *
 * The second add is NOT scaled by holdBreathScale and NOT gated on
 * def[0x694] or fWeaponPosFrac. So the effective rate is
 *
 *     scoped, holdBreathScale 1 : speed * (1 + 1)   = 3.0 /ms at speed 1.5
 *     scoped, holding breath    : speed * (1 + ~0)  = 1.5 /ms  (halves, not stops)
 *     hip fire (posFrac == 0)   : speed * 1         = 5.0 /ms at hip speed
 *
 * The 3.000/ms measured live is this, not a bug. This producer reproduces the
 * asymmetry exactly rather than the tidy version: a server that advanced at a
 * plain 1 x speed would leave a half-amplitude saw-tooth behind.
 *
 * BG_GetSwayParams 0x00422FE0 speed selection:
 *   def[0xBC8] != 0        -> def[0x6F8] + (def[0x6F4] - def[0x6F8]) * posFrac
 *   else def[0x6F0] != 0.0 -> def[0x6F8]
 *   else                   -> 1.0            (with maxAngle 80.0)
 *
 * KNOWN APPROXIMATION
 * -------------------
 * C1 truncates each add per usercmd; this integrates over the whole
 * commandTime step in one go, because usercmds are drained in a burst on
 * socket arrival and this producer runs at snapshot-build time. During steady
 * scoped idle - the case the jitter is reported in - fWeaponPosFrac and
 * holdBreathScale are both pinned, so the only difference is truncation:
 * at most ~4 units per snapshot, i.e. under 0.002 degrees of drawn angle,
 * against a measured median jump of 0.017. Documented rather than hidden.
 */
#ifdef CODOL_SERVER
#include "codol_sway_phase.h"
#include "codol_assets.h"
#include "codol_weapon_compose.h"
#include "bg.h"
#include "bg_public.h"
#include "player.h"
#include "qcommon_io.h"
#include "xassets/weapondef.h"
#include <math.h>
#include <string.h>

/* This translation unit is pulled in by codol_engine_state.c, which several
 * narrow test targets link on their own. Weak references keep those targets
 * linking without dragging in the asset and weapon-composition subsystems: an
 * unresolved weak symbol is a null address, which the guards below treat as
 * "no definition data available" and fall back to BG_GetSwayParams' third
 * branch (speed 1.0). In the real server every one of them resolves. */
extern int CODOL_LoadMountedWeapon(const char *, codol_mounted_weapon_t *)
    __attribute__((weak));
extern int CODOL_LoadMountedWeaponAttachment(const char *,
    codol_mounted_weapon_attachment_t *) __attribute__((weak));
extern void CODOL_FreeMountedWeaponAttachment(codol_mounted_weapon_attachment_t *)
    __attribute__((weak));
extern int CODOL_ComposedWeaponBaseDefinition(const struct WeaponDef *,
    const struct WeaponDef **) __attribute__((weak));
extern int CODOL_ComposedWeaponRecord(const struct WeaponDef *,
    const codol_composed_weapon_t **) __attribute__((weak));
extern int CODOL_ComposedAttachmentAssetName(const char *, unsigned, const char **)
    __attribute__((weak));
extern struct WeaponDef *BG_GetWeaponDef(int) __attribute__((weak));

#define CODOL_SWAY_CLIENTS      64u
#define CODOL_SWAY_DEF_CACHE    1024u

/* C1 runtime WeaponDef offsets, as BG_GetSwayParams 0x00422FE0 and
 * BG_AdvanceSwayPhase 0x00424B90 read them. These are offsets into the
 * serialized type-28 blob, which IS the runtime definition; the retained IW3
 * WeaponDef has no converted counterpart for them. See the harvest note in
 * memory "Offline WeaponDef harvest" and codol_pmove_c1_breath.c. */
#define C1_DEF_OVERLAY_RETICLE  0x694u  /* def[0x694], gates the first add    */
#define C1_DEF_HIP_SWAY_MAX     0x6f0u  /* def[0x6F0], selects the 2nd branch */
#define C1_DEF_ADS_SWAY_SPEED   0x6f4u  /* def[0x6F4]                         */
#define C1_DEF_HIP_SWAY_SPEED   0x6f8u  /* def[0x6F8]                         */
#define C1_DEF_ADS_ALLOWED      0xbc8u  /* def[0xBC8], selects the 1st branch */

typedef struct {
    int      valid;
    int      last_command_time;
    int      phase;
    int      log_time;          /* commandTime of the last diagnostic line */
    int      log_phase;         /* phase at that line, to print a real rate */
} codol_sway_client_t;

typedef struct {
    const struct WeaponDef *def;
    float    hip_sway_max;      /* +0x6f0 */
    float    ads_sway_speed;    /* +0x6f4 */
    float    hip_sway_speed;    /* +0x6f8 */
    unsigned overlay_reticle;   /* +0x694 */
    unsigned ads_allowed;       /* +0xbc8 */
    int      resolved;
} codol_sway_def_t;

static codol_sway_client_t codol_sway_clients[CODOL_SWAY_CLIENTS];
static codol_sway_def_t    codol_sway_defs[CODOL_SWAY_DEF_CACHE];

/* Truncation toward zero, matching the ftol at C1 0x00AE0410 that both adds
 * pass through. C's float->int conversion already truncates toward zero, so
 * this only guards the non-finite and out-of-range cases. */
static int codol_sway_ftol(double v)
{
    if (!isfinite(v)) return 0;
    if (v >= 2147483647.0) return 2147483647;
    if (v <= -2147483648.0) return -2147483647 - 1;
    return (int)v;
}

/* Reads the five sway fields out of the composed definition's serialized base
 * image, then replays every type-43 attachment override that touches one of
 * them, exactly as C1 BG_BuildCustomWeaponDef 0x00421590 does before the sway
 * code reads the definition. Skipping the replay is the "composed weapon index
 * trap": a scope attachment on a base whose own image carries zero at +0x694
 * makes the server compute a rate the client does not. */
static void codol_sway_resolve_def(unsigned weapon, const struct WeaponDef *def,
                                   codol_sway_def_t *out)
{
    const struct WeaponDef *base = NULL;
    codol_mounted_weapon_t mounted;
    const codol_composed_weapon_t *record = NULL;

    memset(out, 0, sizeof *out);
    out->def = def;
    out->hip_sway_speed = 1.0f;   /* BG_GetSwayParams third branch */
    out->ads_sway_speed = 1.0f;
    if (!def) { out->resolved = 1; return; }
    if (!CODOL_ComposedWeaponBaseDefinition ||
        CODOL_ComposedWeaponBaseDefinition(def, &base) != 1 || !base) base = def;
    if (CODOL_LoadMountedWeapon &&
        base->szInternalName && base->szInternalName[0] &&
        CODOL_LoadMountedWeapon(base->szInternalName, &mounted) == 1 &&
        mounted.asset.data && mounted.asset.size >= C1_DEF_ADS_ALLOWED + 1u) {
        uint32_t word;
        memcpy(&word, mounted.asset.data + C1_DEF_OVERLAY_RETICLE, 4);
        out->overlay_reticle = word;
        if (mounted.asset.size >= C1_DEF_HIP_SWAY_SPEED + 4u) {
            memcpy(&out->hip_sway_max,   mounted.asset.data + C1_DEF_HIP_SWAY_MAX,   4);
            memcpy(&out->ads_sway_speed, mounted.asset.data + C1_DEF_ADS_SWAY_SPEED, 4);
            memcpy(&out->hip_sway_speed, mounted.asset.data + C1_DEF_HIP_SWAY_SPEED, 4);
        }
        out->ads_allowed = mounted.asset.data[C1_DEF_ADS_ALLOWED];
    }
    if (CODOL_ComposedWeaponRecord && CODOL_ComposedAttachmentAssetName &&
        CODOL_LoadMountedWeaponAttachment && CODOL_FreeMountedWeaponAttachment &&
        CODOL_ComposedWeaponRecord(def, &record) == 1 && record &&
        base->szInternalName && base->szInternalName[0]) {
        unsigned a;
        for (a = 0; a < record->count && a < CODOL_COMPOSED_ATTACHMENTS; ++a) {
            const char *asset = NULL;
            codol_mounted_weapon_attachment_t att;
            unsigned e;
            if (CODOL_ComposedAttachmentAssetName(base->szInternalName,
                                                  record->items[a], &asset) != 1 || !asset)
                continue;
            if (CODOL_LoadMountedWeaponAttachment(asset, &att) != 1) continue;
            for (e = 0; e < att.count; ++e) {
                uint32_t off, val;
                memcpy(&off, att.entries + 12u * e, 4);
                memcpy(&val, att.entries + 12u * e + 8u, 4);
                switch (off) {
                case C1_DEF_OVERLAY_RETICLE: out->overlay_reticle = val; break;
                case C1_DEF_ADS_ALLOWED:     out->ads_allowed = val & 0xffu; break;
                case C1_DEF_HIP_SWAY_MAX:    memcpy(&out->hip_sway_max, &val, 4); break;
                case C1_DEF_ADS_SWAY_SPEED:  memcpy(&out->ads_sway_speed, &val, 4); break;
                case C1_DEF_HIP_SWAY_SPEED:  memcpy(&out->hip_sway_speed, &val, 4); break;
                default: break;
                }
            }
            CODOL_FreeMountedWeaponAttachment(&att);
        }
    }
    if (!isfinite(out->hip_sway_max))   out->hip_sway_max = 0.0f;
    if (!isfinite(out->ads_sway_speed)) out->ads_sway_speed = 1.0f;
    if (!isfinite(out->hip_sway_speed)) out->hip_sway_speed = 1.0f;
    out->resolved = 1;
}

static const codol_sway_def_t *codol_sway_def(unsigned weapon, const struct WeaponDef *def)
{
    static codol_sway_def_t scratch;
    codol_sway_def_t *slot;
    if (weapon >= CODOL_SWAY_DEF_CACHE) {
        codol_sway_resolve_def(weapon, def, &scratch);
        return &scratch;
    }
    slot = &codol_sway_defs[weapon];
    if (!slot->resolved || slot->def != def) codol_sway_resolve_def(weapon, def, slot);
    return slot;
}

/* BG_GetSwayParams 0x00422FE0, speed output only. The maxAngle output is drawn
 * client-side and never reaches the wire, so it is not computed here. */
static float codol_sway_speed(const codol_sway_def_t *d, float pos_frac)
{
    if (!d) return 1.0f;
    if (d->ads_allowed != 0u)
        return d->hip_sway_speed + (d->ads_sway_speed - d->hip_sway_speed) * pos_frac;
    if (d->hip_sway_max != 0.0f) return d->hip_sway_speed;
    return 1.0f;
}

void CODOL_SwayPhaseReset(int clientNum)
{
    if (clientNum < 0 || (unsigned)clientNum >= CODOL_SWAY_CLIENTS) return;
    codol_sway_clients[clientNum].valid = 0;
}

/* codol_sway_defs is keyed by a raw `const WeaponDef *`, so it stays correct
 * only for as long as those definitions live. The asset-category teardown
 * frees the composed weapon cores that back them, and the allocator can hand
 * the same address back for a different weapon in the next category -- a
 * recycled pointer would then false-match and this cache would answer with the
 * previous category's sway curve. The cached values are copied scalars, so the
 * consequence is a wrong rate rather than a dereference: exactly the kind of
 * bug that survives a whole session unnoticed. Drop the table instead. */
void CODOL_SwayPhaseResetDefs(void)
{
    memset(codol_sway_defs, 0, sizeof codol_sway_defs);
}

int CODOL_SwayPhase(const playerState_t *ps)
{
    codol_sway_client_t *c;
    const codol_sway_def_t *d;
    const struct WeaponDef *def;
    unsigned weapon;
    float pos_frac, breath, speed;
    int dt;

    if (!ps) return 0;
    if (ps->clientNum < 0 || (unsigned)ps->clientNum >= CODOL_SWAY_CLIENTS) return 0;
    c = &codol_sway_clients[ps->clientNum];

    /* Seed from commandTime, not from zero: see the codec note in the header
     * comment. A backwards commandTime re-seeds rather than winding the phase
     * backwards - g_client_mp.cpp publishes level.time - 100 on every spawn,
     * which would otherwise hand the client a negative advance. */
    if (!c->valid || ps->commandTime < c->last_command_time) {
        c->valid = 1;
        c->last_command_time = ps->commandTime;
        c->phase = ps->commandTime;
        c->log_time = ps->commandTime;
        c->log_phase = c->phase;
        return c->phase;
    }
    dt = ps->commandTime - c->last_command_time;
    if (dt <= 0) return c->phase;          /* idempotent: ~half of all snapshots */
    if (dt > 1000) dt = 1000;              /* a hitch must not fling the phase */

    /* C1 0x0045E852: the offhand definition wins while weapFlags bit 1 is up. */
    weapon = ((unsigned)ps->weapFlags & 2u) ? (unsigned)ps->offHandIndex
                                            : (unsigned)ps->weapon;
    def = BG_GetWeaponDef ? BG_GetWeaponDef((int)weapon) : NULL;
    d = codol_sway_def(weapon, def);

    pos_frac = ps->fWeaponPosFrac;
    breath = ps->holdBreathScale;
    if (!isfinite(pos_frac)) pos_frac = 0.0f;
    if (!isfinite(breath)) breath = 0.0f;
    speed = codol_sway_speed(d, pos_frac);
    if (!isfinite(speed)) speed = 1.0f;

    /* First add, BG_AdvanceSwayPhase 0x00424B90: gated on def[0x694] != 0 and
     * fWeaponPosFrac != 0.0f EXACTLY (fucompp against fldz at 0x00424BC7), and
     * scaled by holdBreathScale. */
    if (def && d->overlay_reticle != 0u && pos_frac != 0.0f)
        c->phase += codol_sway_ftol((double)breath * (double)dt * (double)speed);
    /* Second add, C1 0x0045E891..0x0045E8A5: ungated and unscaled. It runs for
     * any weapon with a definition, hip or scoped, breath held or not. */
    if (def)
        c->phase += codol_sway_ftol((double)dt * (double)speed);

    c->last_command_time = ps->commandTime;

    /* One diagnostic line per client per second of command time, only while
     * scoped, so a scoped playtest produces a readable trace and a normal match
     * produces nothing. `rate` is what the client's replay must reproduce and
     * `svdelta` is the -70 codec's cheap-arm margin (0..255 takes 9 bits).
     * Grep: "CoDOL sway phase:". */
    if (CODOL_TRACE_VERBOSE() && pos_frac != 0.0f && c->phase - c->log_phase > 0 &&
        ps->commandTime - c->log_time >= 1000) {
        int steps = ps->commandTime - c->log_time;
        c->log_time = ps->commandTime;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL sway phase: c%d cmd %d dt %d frac %.4f breath %.4f speed %.3f "
            "rate %.3f/ms phase %d svdelta %d\n",
            ps->clientNum, ps->commandTime, dt, pos_frac, breath, speed,
            steps ? (double)(c->phase - c->log_phase) / (double)steps : 0.0,
            c->phase, ps->commandTime - c->phase);
        c->log_phase = c->phase;
    }
    return c->phase;
}

#endif /* CODOL_SERVER */
