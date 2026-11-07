/* Native steering for a remote-controlled missile.
 *
 * `controlslinkto` on its own publishes state and latches an owner; nothing in
 * this server consumed it, so a linked missile flew as if nobody were holding
 * it. This file is the consumer C1 1.1.1.13 runs once per accepted command.
 *
 * The whole path was read out of C1, not inferred from IW4, because C1 steers
 * from two dedicated wire bytes rather than from the player's view angles:
 *
 *   C1 0x50cae4  ClientThink_real, at 0x50cfea, immediately before returning:
 *                  if ((ps->otherFlags & 2) && ps->cameraEntNum != 0x7ff)
 *                      RemoteControlUpdate(ent, msec, cmd);
 *                msec is that function's own ClientThink delta, computed at
 *                0x50c90a..0x50c96e: cmd->serverTime clamped into
 *                [level.time - 1000, level.time + 200], minus ps->commandTime,
 *                abandoned below 1 and capped at 200.
 *
 *   C1 0x50c870  RemoteControlUpdate (eax = player, edx = msec, stack = cmd):
 *                  ent = &g_entities[ps->cameraEntNum];        // ps + 0x54
 *                  if (!*(uint16 *)(ent + 0x248)) return;      // controls handle
 *                  if (ent->s.eType != 4) return;              // missile only
 *                  RemoteControlAngles(&ent->s.apos.trBase, cmd, msec);
 *                  ent->r.currentAngles = ent->s.apos.trBase;  // +0x158
 *                It tests no button bit at all, and never reads the +0x204
 *                flag that controlsLinkTo latches.
 *
 *   C1 0x40ec50  RemoteControlAngles (eax = cmd, esi = angles in+out,
 *                stack = msec):
 *                  pitch = (int8_t)cmd[0x24];   // 40ec5c movsx: SIGNED
 *                  yaw   = (int8_t)cmd[0x25];   // 40ec6f movsx: SIGNED
 *                  s     = msec * 0.001;                  // double 0xc84410
 *                  d[0]  = rate216 * s * (pitch / -127.0); // double 0xc84da0
 *                  d[1]  = rate217 * s * (yaw   / -127.0);
 *                  d[2]  = 0;
 *                  AnglesToAxis(d, m); AnglesToAxis(angles, cur);
 *                  out = transpose(m) * cur;              // 0x619fa0
 *                  AxisToAngles(out, angles);             // 0x61b8e0
 *
 * Two details are easy to get wrong and are therefore spelled out. The wire
 * bytes are signed and the divisor is negative: C1 loads -127.0, so a positive
 * byte turns the missile the negative way on its axis. And the delta matrix is
 * transposed before the multiply; the retained IW3 analogue for weapon-view
 * deltas (_g_active_mp.asm:1804..1821) composes without a transpose, so the
 * transpose here is C1's and is reproduced literally. The multiply order was
 * read out of C1 0x619fa0's body -- edx is the output, eax the right-hand
 * matrix and the stack argument the left-hand one -- not assumed from a name.
 *
 * The angle bytes arrive through the accepted-input record rather than through
 * CODOL_LastUsercmd, so a bot, a synthetic spawn think or a native-only client
 * simply produces no steering instead of steering with a stale word.
 * CODOL_ReadUsercmd (src/codol_usercmd.c:62) only re-reads the two bytes when
 * the wire buttons carry 0x200000 and otherwise carries the previous pair
 * forward, which is exactly the value C1 0x50c870 reads unconditionally; this
 * file therefore does not gate on that button either.
 *
 * Parent review: the worker's linear-disassembly search did not locate C1's
 * speed consumer. That does not prove absence (indirect references and other
 * executable sections remain possible). The speed helper below implements
 * the measured IW4 calculation and is connected to native MissileTrajectory,
 * with missile-owned state and mapped boost events. C1 runtime parity remains
 * unverified.
 *
 * IW4 registers those same four dvars in the same order with the same defaults
 * and flags (0x4671f5..0x4672a2: missileRemoteSpeedTargetRange (3000, 6000),
 * missileRemoteSpeedUp 2000, missileRemoteSpeedDown 500,
 * missileExplosionLiftDistance 32), which is what identifies C1's numeric
 * names, and IW4 does have the consumer. So the model implemented here is
 * IW4 0x5e8990 -> 0x5e8790. The helper accepts speed settings from its caller,
 * which registers C1's measured speed dvars:
 *
 *   IW4 0x5e8990  MissileTrajectory (ecx = missile, eax = out): after the three
 *                 gates -- level.time > launchTime, pos.trType != 2,
 *                 handler == 9 -- `if (ent->flags & 0x80) { remote(); return; }`
 *                 at 0x5e89d1, ahead of the guided/homing path.
 *
 *   IW4 0x5e8790  remote (esi = missile, edi = out):
 *                   buttons = controls owner's client buttons, 0 when there is
 *                             no owner or the remote-control bit is clear;
 *                   AngleVectors(s.apos.trBase, forward, 0, 0);
 *                   speed = DotProduct(s.pos.trDelta, forward);
 *                   if (armed && !boosted && (buttons & fire)) {
 *                       target = range[1];
 *                       if (target - speed > 500.0) { boosted = 1; event; }
 *                       speed = target;
 *                   } else {
 *                       if (remote held && !fire) armed = 1;
 *                       target = range[0];
 *                       speed moves toward target by up/down * 0.05 with the
 *                       reference +0.001 comparisons, clamped at target;
 *                   }
 *                   s.pos.trDelta = forward * speed;
 *                   s.pos.trBase += s.pos.trDelta * 0.05;
 *                   *out = s.pos.trBase;
 *                 Constants read out of the image: 0.05 (0x7170a8), 500.0
 *                 (0x702938), 0.001 (0x721b54).
 *
 * The two button bits are CoDOL's own, not IW4's: the remote-control bit is
 * 0x200000, the bit C1's delta-usercmd decoder gates the remote-angle bytes on
 * (src/codol_usercmd.c:62), and fire is bit 0, which C1 encodes on its own in
 * both usercmd branches (src/codol_usercmd.c:37,52). CODOL_FilterUsercmd keeps
 * that fire bit out of the pmove command while 0x200000 is set, so reading it
 * here cannot double as a shot.
 *
 * Integration evidence: IW4 clears ent+0x18c bit0x800 on entry. The same
 * field feeds the trace mask at5e8e35..5e8e82, through476b70 ->406440
 * ->423280, whose world trace receives it as argument6. The retained
 * G_RunMissile uses native gentity.clipmask at190 in the corresponding trace
 * argument. This is the collision mask, not the entity flags word.
 * IW4 also emits G_AddEvent(ent,0x61,0); native EV_MISSILE_REMOTE_BOOST
 * now maps to C1 event105 with zero parameter. The native trajectory consumer
 * performs the mask clear and emission and uses missile-owned speed state.
 * C1's shipped remote projectile has zero acceleration and speed10, so its
 * initial trajectory is linear. Explicit remote mode is dispatched before
 * the retained linear fallback, while preserving launch-time/rocket-handler
 * gates. This is native server integration of the IW4 flight calculation;
 * it is not a claim that C1's missing speed consumer has been recovered.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
#ifdef CODOL_SERVER

#include "q_shared.h"
#include "q_math.h"
#include "qcommon_io.h"
#include "entity.h"
#include "player.h"
#include "g_shared.h"
#include "cvar.h"
#include "codol_remote_missile.h"
#include "bg.h"
#include "codol_script_startup_extra.h"
#include "codol_weapon_input.h"

#include <float.h>
#include <string.h>

typedef struct {
    unsigned char enabled;
    codol_remote_speed_state_t speed;
} codol_remote_missile_state_t;
static codol_remote_missile_state_t s_remoteMissiles[MAX_GENTITIES];

void CODOL_SetMissileRemoteMode(unsigned entity, int enabled)
{
    if(entity<MAX_GENTITIES) s_remoteMissiles[entity].enabled=enabled!=0;
}
int CODOL_MissileRemoteMode(unsigned entity)
{
    return entity<MAX_GENTITIES && s_remoteMissiles[entity].enabled;
}
void CODOL_ResetMissileRemoteState(unsigned entity)
{
    if(entity<MAX_GENTITIES)
        memset(&s_remoteMissiles[entity],0,sizeof(s_remoteMissiles[entity]));
}
void CODOL_ResetMissileRemoteStates(void)
{
    memset(s_remoteMissiles,0,sizeof(s_remoteMissiles));
}

/* IW4 5e8790..5e8975, arithmetic separated from event/lifecycle publication.
 * IW4 hardcodes 0.05 (0x7170a8) because its server frame is always 50ms: the
 * step is "one server frame". This server runs sv_fps 60 (16.7ms frames,
 * bin/START-CODOL-SERVER.cmd), and MissileTrajectory runs once per frame, so
 * the literal 0.05 advanced the missile 3x its speed and accelerated it 3x
 * too fast. The caller passes the real frame length instead; at 20fps it is
 * exactly IW4's 0.05. Command-driven steering keeps its own ClientThink delta. */
int CODOL_RemoteMissileSpeedStep(codol_remote_speed_state_t *state,
    unsigned buttons, const vec3_t angles, vec3_t velocity, vec3_t position,
    float normal_speed, float boost_speed, float acceleration, float deceleration,
    float frame_seconds)
{
    vec3_t forward;
    float speed, difference;
    unsigned axis;
    int event=0;
    AngleVectors(angles,forward,NULL,NULL);
    speed=velocity[0]*forward[0]+velocity[1]*forward[1]+velocity[2]*forward[2];
    if(!(buttons&0x200000)) buttons=0;
    if(state->armed && !state->boosted && (buttons&1)) {
        if(boost_speed-speed>500.0f) { state->boosted=1; event=1; }
        speed=boost_speed;
    } else {
        if((buttons&0x200000) && !(buttons&1)) state->armed=1;
        difference=normal_speed-speed;
        if(difference>0.001f) {
            speed=(float)(speed+(double)acceleration*frame_seconds);
            if(speed>normal_speed) speed=normal_speed;
        } else if(difference<0.001f) {
            /* 5e88f9 compares the same positive epsilon, not -epsilon. */
            speed=(float)(speed-(double)deceleration*frame_seconds);
            if(speed<normal_speed) speed=normal_speed;
        }
    }
    for(axis=0;axis<3;++axis) {
        velocity[axis]=forward[axis]*speed;
        position[axis]=(float)(position[axis]+(double)velocity[axis]*frame_seconds);
    }
    return event;
}

/* q_math.c:742 defines this but no header declares it; the retained assembly
 * reaches it as a plain cdecl global (_g_active_mp.asm:70). */
void AxisToAngles(vec3_t axis[3], vec3_t angles);

/* C1 renames its dvars to numeric ids, so these two names are the measured
 * ones: pitch is the global at 0x1509d08 registered at 0x40c471, yaw the global
 * at 0x1509d64 registered at 0x40c4a9. Both are registered with default 35.0
 * (0xc846a8), minimum 0 and maximum FLT_MAX (0xc842f0). C1's flag word is 0xc4;
 * the meaning of its 0x4 bit was not established, so it is not reproduced and
 * these stay out of the serverinfo string. */
#define CODOL_REMOTE_PITCH_RATE_DVAR "216"
#define CODOL_REMOTE_YAW_RATE_DVAR   "217"
#define CODOL_REMOTE_RATE_DEFAULT    35.0f

/* ClientThink_real supplies its saved, capped delta after activation. */
#define CODOL_REMOTE_MSEC_MAX      200

/* 0xc84410 and 0xc84da0, the two doubles C1 0x40ec50 divides by. */
#define CODOL_REMOTE_MSEC_TO_SECONDS 0.001f
#define CODOL_REMOTE_BYTE_SCALE   (-127.0f)

static cvar_t *s_pitchRate;
static cvar_t *s_yawRate;
static cvar_t *s_speedRange, *s_speedUp, *s_speedDown;

static unsigned s_remoteTraceCount;
static int s_remoteTraceTime=-1,s_remoteTraceEntity=-1;
static unsigned char s_remoteTraceStep;

void CODOL_RemoteMissileTraceDispatch(struct gentity_s *missile)
{
    s_remoteTraceStep=0;
    if(!missile || missile->s.eType!=ET_MISSILE ||
       !CODOL_MissileRemoteMode((unsigned)missile->s.number) || s_remoteTraceCount>=32)return;
    if(s_remoteTraceEntity==missile->s.number && s_remoteTraceTime>=0 &&
       level.time>=s_remoteTraceTime && level.time-s_remoteTraceTime<1000)return;
    s_remoteTraceTime=level.time;s_remoteTraceEntity=missile->s.number;
    ++s_remoteTraceCount;s_remoteTraceStep=1;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL remote missile dispatch: entity %d owner %d weapon %d time %d launch %d think %d handler %u trType %d origin (%.1f %.1f %.1f) base (%.1f %.1f %.1f) velocity (%.1f %.1f %.1f)\n",
        missile->s.number,CODOL_EntityControllingPlayer(missile->s.number),missile->s.weapon,
        level.time,missile->s.lerp.u.missile.launchTime,missile->nextthink,(unsigned char)missile->handler,
        missile->s.lerp.pos.trType,missile->r.currentOrigin[0],missile->r.currentOrigin[1],missile->r.currentOrigin[2],
        missile->s.lerp.pos.trBase[0],missile->s.lerp.pos.trBase[1],missile->s.lerp.pos.trBase[2],
        missile->s.lerp.pos.trDelta[0],missile->s.lerp.pos.trDelta[1],missile->s.lerp.pos.trDelta[2]);
}

void __cdecl G_AddEvent(gentity_t *ent, int event, int parameter);

/* C1 registrations52e380/52e3b8/52e3f0; numeric names1188/1189/1190,
 * range3000,6000, acceleration2000, deceleration500. Use the same established
 * native flag policy as the two remote angle dvars below. */
static void remote_register_speed_dvars(void)
{
    if(!s_speedRange)
        s_speedRange=Cvar_RegisterVec2("1188",3000.0f,6000.0f,0.0f,FLT_MAX,
            CVAR_ROM|CVAR_CHEAT,"Remote missile normal and boost speeds.");
    if(!s_speedUp)
        s_speedUp=Cvar_RegisterFloat("1189",2000.0f,0.0f,FLT_MAX,
            CVAR_ROM|CVAR_CHEAT,"Remote missile acceleration.");
    if(!s_speedDown)
        s_speedDown=Cvar_RegisterFloat("1190",500.0f,0.0f,FLT_MAX,
            CVAR_ROM|CVAR_CHEAT,"Remote missile deceleration.");
}

/* The server frame MissileTrajectory is advancing, level.time minus
 * level.previousTime (g_shared.h:126). A frame outside (0, 200ms] - the first
 * frame of a map, or a hitch - falls back to IW4's fixed 50ms step. */
static float remote_frame_seconds(void)
{
    int msec=level.time-level.previousTime;
    if(msec<1 || msec>200) return 0.05f;
    return (float)msec*0.001f;
}

int CODOL_RemoteMissileTrajectory(struct gentity_s *missile, vec3_t out)
{
    codol_weapon_input_t input;
    unsigned buttons=0, number;
    int owner;
    if(!missile || !out || missile->s.eType!=ET_MISSILE) return 0;
    number=(unsigned)missile->s.number;
    if(!CODOL_MissileRemoteMode(number)) return 0;
    remote_register_speed_dvars();
    owner=CODOL_EntityControllingPlayer((int)number);
    if(owner>=0 && owner<MAX_CLIENTS && g_entities[owner].r.inuse &&
       g_entities[owner].client && CODOL_ExecutedWeaponInput((unsigned)owner,&input) &&
       input.kind==CODOL_INPUT_NETWORK)
        buttons=input.raw_buttons;
    /* IW4 remote entry5e8797 clears the collision-mask bit before movement. */
    missile->clipmask&=~0x800;
    /* Linear flight may already have advanced before controlsLinkTo. Seed
     * from the traced position, not its older trajectory anchor. */
    if(missile->s.lerp.pos.trType == TR_LINEAR)
        VectorCopy(missile->r.currentOrigin, missile->s.lerp.pos.trBase);
    if(CODOL_RemoteMissileSpeedStep(&s_remoteMissiles[number].speed,buttons,
        missile->s.lerp.apos.trBase,missile->s.lerp.pos.trDelta,
        missile->s.lerp.pos.trBase,s_speedRange->vec2[0],s_speedRange->vec2[1],
        s_speedUp->value,s_speedDown->value,remote_frame_seconds()))
        G_AddEvent(missile,EV_MISSILE_REMOTE_BOOST,0);
    VectorCopy(missile->s.lerp.pos.trBase,out);
    /* A stepped linear base describes this frame. Leaving the launch stamp
     * would make C1 add all elapsed flight time to that already advanced base.
     * It also gives controlsUnlink a continuous free-flight trajectory. */
    if(missile->s.lerp.pos.trType == TR_LINEAR)
        missile->s.lerp.pos.trTime = level.time;
    if(s_remoteTraceStep && s_remoteTraceEntity==missile->s.number) {
        s_remoteTraceStep=0;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL remote missile step: entity %d buttons 0x%x speeds %.1f/%.1f accel %.1f decel %.1f angles (%.1f %.1f %.1f) output (%.1f %.1f %.1f) velocity (%.1f %.1f %.1f)\n",
            missile->s.number,buttons,s_speedRange->vec2[0],s_speedRange->vec2[1],s_speedUp->value,s_speedDown->value,
            missile->s.lerp.apos.trBase[0],missile->s.lerp.apos.trBase[1],missile->s.lerp.apos.trBase[2],
            out[0],out[1],out[2],missile->s.lerp.pos.trDelta[0],missile->s.lerp.pos.trDelta[1],missile->s.lerp.pos.trDelta[2]);
    }
    return 1;
}

static void remote_register_dvars(void)
{
    if(s_pitchRate && s_yawRate) return;
    s_pitchRate = Cvar_RegisterFloat(CODOL_REMOTE_PITCH_RATE_DVAR,
                                     CODOL_REMOTE_RATE_DEFAULT, 0.0f, FLT_MAX,
                                     CVAR_ROM | CVAR_CHEAT,
                                     "Remote-controlled missile pitch rate.");
    s_yawRate = Cvar_RegisterFloat(CODOL_REMOTE_YAW_RATE_DVAR,
                                   CODOL_REMOTE_RATE_DEFAULT, 0.0f, FLT_MAX,
                                   CVAR_ROM | CVAR_CHEAT,
                                   "Remote-controlled missile yaw rate.");
}

/* C1 0x40ec50. `angles` is read and written in place, the way C1 uses it both
 * here and on its client view path at 0x476509. */
static void remote_control_angles(vec3_t angles, const unsigned char bytes[2],
                                  int msec)
{
    float seconds, pitchRate, yawRate;
    vec3_t delta;
    float m[3][3], cur[3][3], transposed[3][3], composed[3][3];
    int row, col;

    remote_register_dvars();
    pitchRate = s_pitchRate ? s_pitchRate->value : CODOL_REMOTE_RATE_DEFAULT;
    yawRate = s_yawRate ? s_yawRate->value : CODOL_REMOTE_RATE_DEFAULT;

    seconds = (float)msec * CODOL_REMOTE_MSEC_TO_SECONDS;
    /* The wire bytes are signed: C1 sign-extends both at 0x40ec5c/0x40ec6f. */
    delta[0] = (pitchRate * seconds) *
               ((float)(signed char)bytes[0] / CODOL_REMOTE_BYTE_SCALE);
    delta[1] = (yawRate * seconds) *
               ((float)(signed char)bytes[1] / CODOL_REMOTE_BYTE_SCALE);
    delta[2] = 0.0f;

    AnglesToAxis(delta, (vec3_t *)m);
    AnglesToAxis(angles, (vec3_t *)cur);
    for(row = 0; row < 3; ++row)
        for(col = 0; col < 3; ++col) transposed[row][col] = m[col][row];
    MatrixMultiply(transposed, cur, composed);
    AxisToAngles((vec3_t *)composed, angles);
}

/* C1 0x50c870's resolution, in the order C1 performs it: the camera-linked
 * entity first, then the controls handle, then the entity type. The camera link
 * is the one C1 reads (ps + 0x54, set by cameraLinkTo at 0x548259); the controls
 * link contributes the owner handle C1 stores on the entity at +0x248, which
 * this server keeps as the controls map in codol_script_startup_extra.c. */
struct gentity_s *CODOL_RemoteMissileControlledEntity(int clientNum)
{
    gentity_t *ent;

    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return NULL;
    ent = CODOL_PlayerCameraLinkedEntity(clientNum, NULL);
    if(!ent) return NULL;
    /* C1 tests only that the handle is set, not whose it is. */
    if(CODOL_EntityControllingPlayer(ent->s.number) < 0) return NULL;
    if(ent->s.eType != ET_MISSILE) return NULL;
    return ent;
}

void CODOL_RemoteMissileClientThink(struct gentity_s *ent,
                                    int msec)
{
    codol_weapon_input_t input;
    gentity_t *missile;
    int clientNum;

    if(!ent || !ent->r.inuse || !ent->client || msec<1 || msec>CODOL_REMOTE_MSEC_MAX) return;
    clientNum = ent->s.number;
    if(clientNum < 0 || clientNum >= MAX_CLIENTS) return;

    /* Only a real CoDOL command carries the two bytes. A bot command, a
     * synthetic spawn think and a native client all report no raw angles, and
     * steering one missile with another client's word is exactly the mistake
     * the accepted-input binding exists to prevent. */
    if(!CODOL_ExecutedWeaponInput((unsigned)clientNum, &input)) return;
    if(input.kind != CODOL_INPUT_NETWORK) return;
    if(!input.remote_angles_valid) return;

    missile = CODOL_RemoteMissileControlledEntity(clientNum);
    if(!missile) return;


    remote_control_angles(missile->s.lerp.apos.trBase, input.remote_angles, msec);
    VectorCopy(missile->s.lerp.apos.trBase, missile->r.currentAngles);
}

#endif /* CODOL_SERVER */
