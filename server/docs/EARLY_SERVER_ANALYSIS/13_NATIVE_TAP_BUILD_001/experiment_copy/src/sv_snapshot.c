#include <math.h>
#include <stdio.h>
/*
===========================================================================
    Copyright (C) 2010-2013  Ninja and TheKelm
    Copyright (C) 1999-2005 Id Software, Inc.

    This file is part of IW4OL source code, a fork of CoD4x.

    IW4OL source code is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    IW4OL source code is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
===========================================================================
*/


#include "q_shared.h"
#include "bg_public.h"
#include "bg.h"
#include "qcommon_io.h"
#include "net_game_conf.h"
#include "server.h"
#include "huffman.h"
#include "msg.h"
#include "sys_main.h"
#include "g_sv_shared.h"
#include "cm_public.h"
#include "g_shared.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"

#ifdef CODOL_SERVER
#include "codol_sv_frame.h"
#include "codol_sv_state.h"
#include "codol_frame_builder.h"
extern char codol_entity_seed_failure[160];
#include "codol_sv_weapons.h"
#include "codol_actor_state.h"
#include "codol_actor_delivery.h"
#include "codol_clientstate_ext.h"
#include "codol_player_appearance.h"
extern void SV_CodolTraceAckPublication(client_t *cl, const char *kind, int packet,
                                         int wireAck, qboolean transmitted, qboolean recovered);
/* Readiness describes a completed native snapshot, live or archived. The
 * gameplay converter validates the sequence-matched captured channels. */
static unsigned char codol_snapshot_ready[MAX_CLIENTS];
static uint32_t codol_snapshot_sequence[MAX_CLIENTS];
#define SV_WIRE_SERVERCOMMAND 1
#define SV_WIRE_EOF 5
#else
#define SV_SEND_HUFFMAN
#define SV_WIRE_SERVERCOMMAND svc_serverCommand
#define SV_WIRE_EOF svc_EOF
#endif
/*
=============================================================================

Delta encode a client frame onto the network channel

A normal server packet will look like:

4	sequence number (high bit set if an oversize fragment)
<optional reliable commands>
1	svc_snapshot
4	last client reliable command
4	serverTime
1	lastframe for delta compression
1	snapFlags
1	areaBytes
<areabytes>
<playerstate>
<packetentities>

=============================================================================
*/

/*
==================
SV_UpdateServerCommandsToClient

(re)send all server commands the client hasn't acknowledged yet
==================
*/
__cdecl void SV_UpdateServerCommandsToClient( client_t *client, msg_t *msg ) {
	int i;
//	extclient_t* extcl = &svs.extclients[ client - svs.clients ];

	// write any unacknowledged serverCommands
	for ( i = client->reliableAcknowledge + 1 ; i <= client->reliableSequence ; i++ ) {
		MSG_WriteByte( msg, SV_WIRE_SERVERCOMMAND );
		MSG_WriteLong( msg, i );
		//MSG_WriteString( msg, extcl->reliableCommands[ i & ( MAX_RELIABLE_COMMANDS - 1 ) ].command );
		MSG_WriteString( msg, client->reliableCommands[ i & ( MAX_RELIABLE_COMMANDS - 1 ) ].command );
	}

	client->reliableSent = client->reliableSequence;

}

void SV_UpdateServerCommandsToClientRecover( client_t *client, msg_t *msg )
{
	int i;
	int cmdlen;

	for(i = client->reliableAcknowledge + 1; i <= client->reliableSequence; i++)
	{

		cmdlen = strlen(client->reliableCommands[i & ( MAX_RELIABLE_COMMANDS - 1 )].command);

		if ( cmdlen + msg->cursize + 6 >= msg->maxsize )
			break;

		MSG_WriteByte(msg, SV_WIRE_SERVERCOMMAND);
		MSG_WriteLong(msg, i);
		MSG_WriteString(msg, client->reliableCommands[i & ( MAX_RELIABLE_COMMANDS - 1 )].command);

	}
	if ( i - 1 > client->reliableSent )
	client->reliableSent = i - 1;
}


#ifdef CODOL_SERVER
void CODOL_ResetClientOriginPolicy(unsigned slot)
{
    (void)slot;
}
/* C1 MSG_WriteDeltaPlayerstate 0x5a619b..0x5a6238 suppresses the origin only
 * when the reported prediction has the exact outgoing commandTime and is
 * within 0.1 units of the authoritative result.  A missing delta base cannot
 * safely suppress it: C1's refill falls back to that base on a prediction-ring
 * miss, which is how a single missed spawn seed persisted as (0,0,0). */
/* 2026-09-16 sniper-sway investigation: every frame this returns 1 republishes
 * the whole hint-3 group -- origin, velocity, viewangles AND bobCycle -- with a
 * zero delta base, i.e. it overrides the client's own prediction. C1 draws the
 * scoped weapon's sway from ps->bobCycle (0x00424d90, gated on WeaponDef+0x694,
 * so scoped weapons only), so a forced hint-3 frame lands directly on a
 * sniper's scope. The counters name which gate fires; the sum is printed once
 * per second per client so a live session says whether the cause is the
 * commandTime handshake or a genuine pmove divergence. */
/* src/codol/player/codol_pmove_trace.c -- the per-command decomposition of the
 * very disagreement this gate acts on.  It is driven from here, and only from
 * here, so that its divergence count is by construction the `toofar` count. */
void CODOL_PmoveTraceReport(unsigned client, const float *serverOrigin,
                            const float *predictedOrigin, int predictedTime);
/* src/codol/snapshot/codol_snapshot_pacing.c -- measures how evenly this
 * server consumes usercmds, in the only units the client can see: the
 * per-snapshot advance of the published ps.commandTime. */
void CODOL_PacingSnapshot(unsigned client, int psCommandTime, int serverTime,
                          int rateDelayed);

typedef struct {
    unsigned total, sent, no_base, not_active, follow, viewlock, intermission;
    unsigned no_pred_time, time_mismatch, too_far;
    float worst_dist, last_dist;
    int last_pred_time, last_cmd_time;
} codol_rov_stats_t;
static codol_rov_stats_t codol_rov_stats[MAX_CLIENTS];
static int CODOL_ReadOriginVelocityFlag(unsigned slot,const client_t *client,
                                        const clientSnapshot_t *frame,int has_base)
{
    const playerState_t *ps=&frame->ps;
    codol_rov_stats_t *st;
    float dx,dy,dz,d2;
    if(slot>=MAX_CLIENTS) return 1;
    st=&codol_rov_stats[slot];
    ++st->total;
    st->last_pred_time=client->predictedOriginServerTime;
    st->last_cmd_time=ps->commandTime;
    if(!has_base) { ++st->no_base; ++st->sent; return 1; }
    if(client->state!=CS_ACTIVE) { ++st->not_active; ++st->sent; return 1; }
    if(ps->otherFlags&POF_FOLLOW) { ++st->follow; ++st->sent; return 1; }
    if(ps->viewlocked_entNum!=ENTITYNUM_NONE) { ++st->viewlock; ++st->sent; return 1; }
    if(ps->pm_type==6) { ++st->intermission; ++st->sent; return 1; }
    if(client->predictedOriginServerTime<=0) { ++st->no_pred_time; ++st->sent; return 1; }
    if(client->predictedOriginServerTime!=ps->commandTime) {
        ++st->time_mismatch; ++st->sent; return 1;
    }
    dx=ps->origin[0]-client->predictedOrigin[0];
    dy=ps->origin[1]-client->predictedOrigin[1];
    dz=ps->origin[2]-client->predictedOrigin[2];
    d2=dx*dx+dy*dy+dz*dz;
    st->last_dist=d2>0.0f ? (float)sqrt((double)d2) : 0.0f;
    if(st->last_dist>st->worst_dist) st->worst_dist=st->last_dist;
    if(CODOL_TRACE_ON())
        CODOL_PmoveTraceReport(slot,ps->origin,client->predictedOrigin,
                               ps->commandTime);
    if(d2>0.01f) { ++st->too_far; ++st->sent; return 1; }
    return 0;
}
static void CODOL_ReportOriginVelocityFlag(unsigned slot)
{
    static int last[MAX_CLIENTS];
    codol_rov_stats_t *st;
    if(slot>=MAX_CLIENTS) return;
    st=&codol_rov_stats[slot];
    if(!st->total) return;
    if(!CODOL_TRACE_ON()) return;
    if(svs.time-last[slot]<1000 && svs.time>=last[slot]) return;
    last[slot]=svs.time;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL rov: client %u sent %u/%u (nobase %u inactive %u follow %u viewlock %u "
        "interm %u nopredtime %u timemismatch %u toofar %u) dist %.3f worst %.3f "
        "predTime %d cmdTime %d\n",
        slot,st->sent,st->total,st->no_base,st->not_active,st->follow,st->viewlock,
        st->intermission,st->no_pred_time,st->time_mismatch,st->too_far,
        (double)st->last_dist,(double)st->worst_dist,st->last_pred_time,st->last_cmd_time);
    memset(st,0,sizeof(*st));
}
#endif
__cdecl void SV_WriteSnapshotToClient(client_t* client, msg_t* msg){
#ifdef CODOL_SERVER
    /* Both the direct sender and batched sender reach this function. A zombie
     * retains reliable disconnect commands but has no gameplay frame. */
    if(client->state==CS_ZOMBIE) return;
    unsigned slot=(unsigned)(client-svsHeader.clients);
    uint32_t sequence=(uint32_t)client->netchan.outgoingSequence;
    const codol_native_frame_t *native=CODOL_ClientNativeFrame(slot,sequence);
    const codol_animcmd_t *commands;
    size_t command_count;
    unsigned flags=(unsigned)svsHeader.snapFlagServerBit;
    uint32_t acknowledged;
    int rov;
    codol_delta_context_t context={svsHeader.time,{0,0,0},0,0};
    clientSnapshot_t *frame=&client->frames[sequence&PACKET_MASK];
    frame->var_03=svsHeader.time;
    if(CODOL_TRACE_ON())
        CODOL_PacingSnapshot(slot,frame->ps.commandTime,svs.time,
                             (int)client->rateDelayed);
    if(client->rateDelayed) flags|=1;
    if(client->state==CS_ACTIVE) client->unksnapshotvar=1;
    else if(client->state!=CS_ZOMBIE) client->unksnapshotvar=0;
    if(!client->unksnapshotvar) flags|=2;
    if(!native) {
        static char why[200];
        snprintf(why,sizeof(why),"no native frame for sequence %u (ready %u, ready sequence %u, builder: %s)",
            sequence,(unsigned)codol_snapshot_ready[slot],codol_snapshot_sequence[slot],
            codol_frame_failure ? codol_frame_failure : "none");
        codol_snapshot_failure=why; msg->overflowed=qtrue; return;
    }
    commands=CODOL_NativeFrameCommands(native,&command_count);
    acknowledged=client->state==CS_ACTIVE && client->deltaMessage>0 ?
        (uint32_t)client->deltaMessage : 0;
    rov=CODOL_ReadOriginVelocityFlag(slot,client,frame,
        CODOL_ClientSnapshotHasBase(slot,acknowledged,sequence,flags));
    CODOL_ReportOriginVelocityFlag(slot);
    CODOL_PrepareClientSnapshot(slot,msg,CODOL_NativeFrameState(native),
        acknowledged,
        CODOL_NativeFrameUpdates(native),commands,command_count,flags,
        rov,&context);
    if(CODOL_TRACE_ON() && com_developer && com_developer->integer) {
        static int last_report[MAX_CLIENTS];
        if(slot<MAX_CLIENTS && svs.time-last_report[slot]>=1000) {
            const codol_snapshot_state_t *debug_state=CODOL_NativeFrameState(native);
            int debug_ent0=-1; size_t debug_i;
            for(debug_i=0;debug_state && debug_i<debug_state->entity_count;++debug_i)
                if(debug_state->entities[debug_i].number==0) {
                    debug_ent0=(int)debug_state->entities[debug_i].type; break;
                }
            last_report[slot]=svs.time;
            Com_DPrintf(CON_CHANNEL_SERVER,
                "CoDOL snapshot clock: client %u seq %u ack %d delta %d gap %d server %d command %d lastcmd %d age %d rov %d flags 0x%x stance %d vh %.1f/%d lerp %d/%d/%d ent0 %d pof 0x%x\n",
                slot,sequence,client->messageAcknowledge,client->deltaMessage,
                (int)sequence-client->deltaMessage,svsHeader.time,frame->ps.commandTime,
                client->lastUsercmd.serverTime,svsHeader.time-frame->ps.commandTime,rov,flags,
                frame->ps.pm_flags&3,frame->ps.viewHeightCurrent,frame->ps.viewHeightTarget,
                frame->ps.viewHeightLerpTime,frame->ps.viewHeightLerpTarget,
                frame->ps.viewHeightLerpDown,debug_ent0,(unsigned)frame->ps.otherFlags);
        }
    }
#else

    snapshotInfo_t snapInfo;
    int lastframe;
    int from_num_entities;
    int newindex, oldindex, newnum, oldnum;
    clientState_t *newcs, *oldcs;
    entityState_t *newent, *oldent;
    clientSnapshot_t *frame, *oldframe;
    int i;
    int snapFlags;
    int var_x, from_first_entity, from_num_clients, from_first_client;

    snapInfo.clnum = client - svsHeader.clients;
    snapInfo.client = (void*)client;
	snapInfo.snapshotDeltaTime = 0;
    snapInfo.fromBaseline = 0;
    snapInfo.archived = 0;

    frame = &client->frames[client->netchan.outgoingSequence & PACKET_MASK];
    frame->var_03 = svsHeader.time;

    if(client->deltaMessage <= 0 ||  client->state != CS_ACTIVE) {
        oldframe = NULL;
        lastframe = 0;
        var_x = 0;

    } else if(client->netchan.outgoingSequence - client->deltaMessage >= PACKET_BACKUP - 3) {
        Com_DPrintf(CON_CHANNEL_SERVER,"%s: Delta request from out of date packet.\n", client->name);
        oldframe = NULL;
        lastframe = 0;
        var_x = 0;

    } else if(client->demoDeltaFrameCount <= 0 && client->demorecording){

        oldframe = NULL;
        lastframe = 0;
        var_x = 0;
        client->demowaiting = qfalse;
        Com_DPrintf(CON_CHANNEL_SERVER,"Force a nondelta frame for %s for demo recording\n", client->name);

        if(client->demoMaxDeltaFrames < 1024)
        {
            client->demoMaxDeltaFrames <<= 1;
        }
        client->demoDeltaFrameCount = client->demoMaxDeltaFrames;


    } else {
        oldframe = &client->frames[client->deltaMessage & PACKET_MASK];
        lastframe = client->netchan.outgoingSequence - client->deltaMessage;
        var_x = oldframe->var_03;
        client->demoDeltaFrameCount--;

        if(oldframe->first_entity <  svsHeader.nextSnapshotEntities - svsHeader.numSnapshotEntities) {
            Com_DPrintWarning(CON_CHANNEL_SERVER,"%s: Delta request from out of date entities - delta against entity %i, oldest is %i, current is %i.  Their old snapshot had %i entities in it\n",
                            client->name, oldframe->first_entity, svs.nextSnapshotEntities - svs.numSnapshotEntities, svs.nextSnapshotEntities, oldframe->num_entities );
            oldframe = NULL;
            lastframe = 0;
            var_x = 0;

        } else if(oldframe->first_client <  svsHeader.nextSnapshotClients - svsHeader.numSnapshotClients) {

            Com_DPrintWarning(CON_CHANNEL_SERVER,"%s: Delta request from out of date clients - delta against client %i, oldest is %i, current is %i.  Their old snapshot had %i clients in it\n",
                            client->name, oldframe->first_client, svs.nextSnapshotClients - svs.numSnapshotClients, svs.nextSnapshotClients, oldframe->num_clients);
            oldframe = NULL;
            lastframe = 0;
            var_x = 0;
        }
    }


    MSG_WriteByte(msg, svc_snapshot);
    MSG_WriteLong(msg, svsHeader.time);
    MSG_WriteByte(msg, lastframe);
    snapInfo.snapshotDeltaTime = var_x;

    snapFlags = svsHeader.snapFlagServerBit;

    if(client->rateDelayed){
	snapFlags |= 1;
    }

    if(client->state == CS_ACTIVE) {

	client->unksnapshotvar = 1;

    } else {
		if(client->state != CS_ZOMBIE){
			client->unksnapshotvar = 0;
		}
    }

    if(!client->unksnapshotvar){
		snapFlags |= 2;
    }

    MSG_WriteByte(msg, snapFlags);

    if(oldframe) {
		MSG_WriteDeltaPlayerstate( &snapInfo, msg, svsHeader.time, &oldframe->ps, &frame->ps);
		from_num_entities = oldframe->num_entities;
		from_first_entity = oldframe->first_entity;
		from_num_clients = oldframe->num_clients;
		from_first_client = oldframe->first_client;
    } else {
	        MSG_WriteDeltaPlayerstate( &snapInfo, msg, svsHeader.time, 0, &frame->ps);
		from_num_entities = 0;
		from_first_entity = 0;
		from_num_clients = 0;
		from_first_client = 0;
    }

    MSG_ClearLastReferencedEntity(msg);


    newindex = 0;
    oldindex = 0;

//    Com_Printf(CON_CHANNEL_SERVER,"Delta client: %i:\n", snapInfo.clnum);


    while ( newindex < frame->num_entities || oldindex < from_num_entities)
	{
		if ( newindex >= frame->num_entities ) {
			newnum = 9999;
			newent = NULL;
		} else {
			newent = &svsHeader.snapshotEntities[( frame->first_entity + newindex ) % svsHeader.numSnapshotEntities];
			newnum = newent->number;
		}

		if ( oldindex >= from_num_entities ) {
			oldnum = 9999;
			oldent = NULL;
		} else {
			oldent = &svsHeader.snapshotEntities[( from_first_entity + oldindex ) % svsHeader.numSnapshotEntities];
			oldnum = oldent->number;
		}

		if ( newnum == oldnum ) {
			// delta update from old position
			// because the force parm is qfalse, this will not result
			// in any bytes being emited if the entity has not changed at all
	//		Com_Printf(CON_CHANNEL_SERVER,"^2Delta Update Entity - New delta: %i Old delta: %i\n", newent->number, oldent->number);
			MSG_WriteDeltaEntity( &snapInfo, msg, svsHeader.time, oldent, newent, qfalse );
			oldindex++;
			newindex++;
			continue;
		}

		if ( newnum < oldnum ) {
			// this is a new entity, send it from the baseline
			snapInfo.fromBaseline = 1;
	//		Com_Printf(CON_CHANNEL_SERVER,"Delta Add Entity: %i\n", newent->number);
			MSG_WriteDeltaEntity( &snapInfo, msg, svsHeader.time, &svsHeader.svEntities[newnum].baseline.s, newent, qtrue );
			snapInfo.fromBaseline = 0;
			newindex++;
			continue;
		}

		if ( newnum > oldnum ) {
			// the old entity isn't present in the new message
	//		Com_Printf(CON_CHANNEL_SERVER,"Delta Remove Entity: %i\n", oldent->number);
			MSG_WriteDeltaEntity( &snapInfo, msg, svsHeader.time, oldent, NULL, qtrue );
			oldindex++;
			continue;
		}
    }


    MSG_WriteEntityIndex(&snapInfo, msg, ( MAX_GENTITIES - 1 ), GENTITYNUM_BITS);
    MSG_ClearLastReferencedEntity(msg);

    newindex = 0;
    oldindex = 0;

    while(newindex < frame->num_clients || oldindex < from_num_clients)
	{
		if(newindex >= frame->num_clients){
			newnum = 9999;
			newcs = NULL;
		}else{

			newcs = &svsHeader.snapshotClients[(frame->first_client + newindex) % svsHeader.numSnapshotClients];
			newnum = newcs->clientIndex;
		}

		if(oldindex >= from_num_clients){
			oldnum = 9999;
			oldcs = NULL;
		}else{

			oldcs = &svsHeader.snapshotClients[(from_first_client + oldindex) % svsHeader.numSnapshotClients];
			oldnum = oldcs->clientIndex;
		}

		if ( newnum == oldnum ) {
			// delta update from old position
			// because the force parm is qfalse, this will not result
			// in any bytes being emited if the entity has not changed at all
			MSG_WriteDeltaClient( &snapInfo, msg, svsHeader.time, oldcs, newcs, qfalse );
			oldindex++;
			newindex++;
			continue;
		}

		if ( newnum < oldnum ) {
			MSG_WriteDeltaClient( &snapInfo, msg, svsHeader.time, NULL, newcs, qtrue );
			newindex++;
			continue;
		}

		if ( newnum > oldnum ) {
			MSG_WriteDeltaClient( &snapInfo, msg, svsHeader.time, oldcs, NULL, qtrue );
			oldindex++;
			continue;
		}
	}

	MSG_WriteBit0(msg);

	if(sv_padPackets->integer){
		for( i=0 ; i < sv_padPackets->integer ; i++){
			MSG_WriteByte( msg, 0); //svc_nop
		}
    }
#endif
}


void SV_WriteClientConfigInfo( msg_t* msg, client_t* cl, int messageNum )
{
	//cl: client about which we write updates
	MSG_WriteByte( msg, svc_configclient );
	if(messageNum != -1) //Only in gamestate this will be -1
	{
		MSG_WriteLong(msg, messageNum);
	}
	MSG_WriteByte( msg, cl - svs.clients );
	MSG_WriteString( msg, cl->name );
	MSG_WriteString( msg, cl->clantag );
}


void SV_UpdateConfigData(client_t* cl, msg_t* msg)
{
#ifdef CODOL_SERVER
	/* CoDOL acknowledges reliable commands, not IW4OL's config-data stream.
	 * Player identity belongs in its clientState section. Sending the legacy
	 * envelope here also eventually drops clients on an ACK they cannot send. */
	(void)cl; (void)msg;
#else
	int i;
	unsigned int index;

	if(cl->gamestateSent < 2)
	{
		return; //reset sent, need to wait till client has gamestate acknowledged
	}

	//cl: client to whom we write updates
	if(svs.configDataSequence - MAX_CONFIGDATACACHE >= cl->configDataAcknowledge)
	{
		cl->delayDropMsg = "svs.configDataSequence - MAX_CONFIGDATACACHE >= cl->configDataAcknowledge";
		return;
	}

	if(svs.configDataSequence < cl->configDataAcknowledge)
	{
		cl->delayDropMsg = "svs.configDataSequence < cl->configDataAcknowledge";
		return;
	}
	for(i = cl->configDataAcknowledge +1; i <= svs.configDataSequence; ++i)
	{
	//	Com_Printf(CON_CHANNEL_SERVER,"Write Data: %d, Sequence %d\n", i, svs.configDataSequence);
		index = svs.changedConfigData[i % MAX_CONFIGDATACACHE];

		if(index < 64)
		{
			SV_WriteClientConfigInfo( msg, &svs.clients[index], i );
		}
	}

#endif
}



/*
====================
SV_RateMsec

Return the number of msec a given size message is supposed
to take to clear, based on the current rate
TTimo - use sv_maxRate or sv_dl_maxRate depending on regular or downloading client
====================
*/
#define HEADER_RATE_BYTES   48      // include our header, IP header, and some overhead

static int SV_RateMsec( client_t *client, int messageSize ) {
	int rate;
	int rateMsec;
	int maxRate;

#ifdef CODOL_SERVER
	/* CODOL_NetchanSubmit sends every fragment of a message in the same
	 * frame, so charge all of it plus each fragment's header: a 4.3 KB full
	 * frame used to be charged as 1.5 KB and went out as four back-to-back
	 * packets at the full snapshot rate. */
	messageSize += HEADER_RATE_BYTES * ( ( messageSize - 1 ) / 1162 );
#else
	// individual messages will never be larger than fragment size
	if ( messageSize > 1500 ) {
		messageSize = 1500;
	}
#endif
	// low watermark for sv_maxRate, never 0 < sv_maxRate < 1000 (0 is no limitation)
	if ( sv_maxRate->integer && sv_maxRate->integer < 1000 ) {
		Cvar_SetInt( sv_maxRate, 1000 );
	}
	rate = client->rate;
	maxRate = sv_maxRate->integer;

	if ( maxRate ) {
		if ( maxRate < rate ) {
			rate = maxRate;
		}
	}
	rateMsec = ( messageSize + HEADER_RATE_BYTES ) * 1000 / rate;

	return rateMsec;
}


void SV_TrackHuffmanCompression(int compsize, int uncompsize)
{
    static int totaluncompbytes = 0;
    static int totalcompbytes = 0;
    static int nextnotifybytes = 0;

    totaluncompbytes += uncompsize;
    totalcompbytes += compsize;

    if(totalcompbytes > nextnotifybytes)
    {
	Com_Printf(CON_CHANNEL_SERVER,"Huffman compressionrate: %.2f\n", (float)totaluncompbytes / (float)totalcompbytes);
	nextnotifybytes += 1024*16;
    }
}

/*
=======================
SV_SendMessageToClient

Called by SV_SendClientSnapshot and SV_SendClientGameState
=======================
*/
__cdecl qboolean SV_SendMessageToClient( msg_t *msg, client_t *client ) {
	int rateMsec;
#ifdef CODOL_SERVER
    clientSnapshot_t *attemptedFrame = &client->frames[client->netchan.outgoingSequence & PACKET_MASK];
    int oldSize = attemptedFrame->messageSize;
    unsigned oldSent = attemptedFrame->messageSent, oldAcked = attemptedFrame->messageAcked;
    if (msg->overflowed) return qfalse;
#endif

#ifdef SV_SEND_HUFFMAN
	byte svCompressBuf[4*65536];
	int len;
	*(int32_t*)svCompressBuf = *(int32_t*)msg->data;
	len = MSG_WriteBitsCompress( msg->data + 4 ,(byte*)svCompressBuf + 4, msg->cursize - 4);
//	SV_TrackHuffmanCompression(len, msg->cursize - 4);
	len += 4;
#endif
	if(client->delayDropMsg){
		SV_DropClient(client, client->delayDropMsg);
#ifdef CODOL_SERVER
        return qfalse;
#endif
	}

	if(client->demorecording && !client->demowaiting && client->demofile.handleFiles.file.o)
	{
#ifdef SV_SEND_HUFFMAN
		SV_WriteDemoMessageForClient(svCompressBuf, len, client);
#else
		SV_WriteDemoMessageForClient(msg->data, msg->cursize, client);
#endif
	}

	// record information about the message
#ifdef SV_SEND_HUFFMAN
	client->frames[client->netchan.outgoingSequence & PACKET_MASK].messageSize = len;
#else
	client->frames[client->netchan.outgoingSequence & PACKET_MASK].messageSize = msg->cursize;
#endif
	client->frames[client->netchan.outgoingSequence & PACKET_MASK].messageSent = Sys_Milliseconds();
	client->frames[client->netchan.outgoingSequence & PACKET_MASK].messageAcked = 0xFFFFFFFF;

	// send the datagram
#ifdef SV_SEND_HUFFMAN
	SV_Netchan_Transmit( client, svCompressBuf, len );
#else
    if (!SV_Netchan_Transmit(client, msg->data, msg->cursize)) {
#ifdef CODOL_SERVER
        attemptedFrame->messageSize = oldSize;
        attemptedFrame->messageSent = oldSent;
        attemptedFrame->messageAcked = oldAcked;
        client->nextSnapshotTime = svs.time + client->snapshotMsec;
#endif
        return qfalse;
    }
#endif
	// set nextSnapshotTime based on rate and requested number of updates

	// local clients get snapshots every frame
	// TTimo - show_bug.cgi?id=491
	// added sv_lanForceRate check

#ifdef CODOL_SERVER
	/* IW3's 28 messages were 1.4 s at 20 Hz; at 60 Hz they are under half a
	 * second, so an ordinary internet hiccup froze snapshots for 3 s. Keep
	 * the 1.4 s meaning. */
	{
		int lagLimit = client->snapshotMsec > 0 ? 1400 / client->snapshotMsec : 28;
		if ( lagLimit < 28 ) lagLimit = 28;
		if(client->state == CS_ACTIVE && client->deltaMessage >= 0 && client->netchan.outgoingSequence - client->deltaMessage > lagLimit){
			client->nextSnapshotTime = svs.time + 3000 + client->snapshotMsec;
		}
	}
#else
	if(client->state == CS_ACTIVE && client->deltaMessage >= 0 && client->netchan.outgoingSequence - client->deltaMessage > 28){
		client->nextSnapshotTime = svs.time + 3000 + client->snapshotMsec;
	}
#endif

	if ( client->netchan.remoteAddress.type == NA_LOOPBACK || Sys_IsLANAddress( &client->netchan.remoteAddress )) {
		client->nextSnapshotTime = svs.time - 1;
		return qtrue;
	}

	// normal rate / snapshotMsec calculation
	rateMsec = SV_RateMsec( client, msg->cursize );

	// TTimo - during a download, ignore the snapshotMsec
	// the update server on steroids, with this disabled and sv_fps 60, the download can reach 30 kb/s
	// on a regular server, we will still top at 20 kb/s because of sv_fps 20
	if ( !*client->downloadName && rateMsec < client->snapshotMsec ) {
		// never send more packets than this, no matter what the rate is at
		rateMsec = client->snapshotMsec;
		client->rateDelayed = qfalse;
	} else {
		client->rateDelayed = qtrue;
	}

	client->nextSnapshotTime = svs.time + rateMsec;

	// don't pile up empty snapshots while connecting
	if ( client->state != CS_ACTIVE && !*client->downloadName) {
		// a gigantic connection message may have already put the nextSnapshotTime
		// more than a second away, so don't shorten it
		// do shorten if client is downloading
		if (  client->nextSnapshotTime < svs.time + 1000 ) {
			client->nextSnapshotTime = svs.time + 1000;
		}
	}
#ifdef SV_SEND_HUFFMAN
	sv.bpsTotalBytes += len;
#else
	sv.bpsTotalBytes += msg->cursize;
#endif
    return qtrue;
}

void SV_SendClientSnapshot(client_t *cl){

	msg_t msg;

	SV_SetServerStaticHeader();

	SV_BeginClientSnapshot(cl, &msg);

	SV_WriteSnapshotToClient(cl, &msg);

	SV_EndClientSnapshot(cl, &msg);

	SV_GetServerStaticHeader();
}

void SV_BeginClientSnapshot(client_t *client, msg_t *msg)
{
	static byte tempSnapshotMsgBuf[NETCHAN_UNSENTBUFFER_SIZE];


	MSG_Init( msg, tempSnapshotMsgBuf, sizeof(tempSnapshotMsgBuf) );
#ifdef CODOL_SERVER
    CODOL_DiscardClientSnapshot((unsigned)(client - svsHeader.clients));
	if (!CODOL_RefreshServerAssetNames() || !CODOL_RefreshServerPlayerNames() ||
        !CODOL_RefreshServerWeaponMappings()) { msg->overflowed = qtrue; return; }
    {
        unsigned slot=(unsigned)(client-svsHeader.clients);
        uint32_t sequence=(uint32_t)client->netchan.outgoingSequence;
        if(slot<MAX_CLIENTS && client->state==CS_ACTIVE && codol_snapshot_ready[slot] &&
           codol_snapshot_sequence[slot]==sequence) {
            static const char *reported_failure[MAX_CLIENTS];
            static int reported_time[MAX_CLIENTS];
            int built=CODOL_BuildGameplayFrame(slot,sequence,&client->frames[sequence&PACKET_MASK]);
            /* Printed for real (was developer-only), once per failure kind and
             * again every 10 s while it persists: a silent rejection hid a
             * 14 s snapshot blackout on the VPS. */
            if(!built && codol_frame_failure &&
               (reported_failure[slot]!=codol_frame_failure || svsHeader.time-reported_time[slot]>=10000 ||
                svsHeader.time<reported_time[slot])) {
                reported_time[slot]=svsHeader.time;
                if(!strcmp(codol_frame_failure,"entity conversion"))
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL frame rejected for client %u: %s (entity %d type %d, %s: %s)\n",
                        slot,codol_frame_failure,codol_entity_failure_number,codol_entity_failure_type,
                        codol_entity_failure_stage ? codol_entity_failure_stage : "none",codol_entity_seed_failure);
                else if(!strcmp(codol_frame_failure,"player or HUD conversion"))
                    Com_Printf(CON_CHANNEL_SERVER,"CoDOL frame rejected for client %u: %s (%s)\n",slot,
                        codol_frame_failure,codol_player_failure ? codol_player_failure : "unknown step");
                else Com_Printf(CON_CHANNEL_SERVER,"CoDOL frame rejected for client %u: %s\n",slot,codol_frame_failure);
            }
            reported_failure[slot]=built ? NULL : codol_frame_failure;
        }
    }
#endif
	MSG_ClearLastReferencedEntity( msg );

	MSG_WriteLong( msg, client->lastClientCommand );

	if ( client->state >= CS_CONNECTED || client->state == CS_ZOMBIE )
	{
		SV_UpdateServerCommandsToClient( client, msg );
	}
	if ( client->state >= CS_CONNECTED && client->gamestateSent)
	{
		SV_UpdateConfigData(client, msg);
	}

}

void SV_EndClientSnapshot(client_t *client, msg_t *msg)
{
#ifdef CODOL_SERVER
    unsigned slot = (unsigned)(client - svsHeader.clients);
    uint32_t sequence = client->netchan.outgoingSequence;
    qboolean recovered = qfalse;
#endif

	if ( client->state != CS_ZOMBIE )
		SV_WriteDownloadToClient( client );

#ifdef CODOL_SERVER
    /* A delta's relative base was encoded for sequence. If another message
     * consumed it, recover reliable commands rather than send that delta under
     * a different packet number or commit it to the wrong history slot. */
        if (CODOL_ClientSnapshotPending(slot) &&
        (sequence != (uint32_t)client->netchan.outgoingSequence ||
         !CODOL_ClientSnapshotPrepared(slot, msg, sequence))) {
        codol_snapshot_failure="pending snapshot sequence/preparation mismatch at end"; msg->overflowed = qtrue;
    }
    if (!CODOL_ClientSnapshotPrepared(slot, msg, sequence))
#endif
	    MSG_WriteByte(msg, SV_WIRE_EOF);

	if ( msg->overflowed == qtrue)
	{
#ifdef CODOL_SERVER
        CODOL_DiscardClientSnapshot(slot);
        recovered = qtrue;
#endif
		int codolReport = 1;
#ifdef CODOL_SERVER
		/* Report once per distinct FAILURE SHAPE per client, digits masked
		 * out of the comparison. MEASURED 2026-09-20: a zm match logged
		 * 1,274 copies of one fault -- each differing only in an element
		 * index and a sequence number -- plus 1,274 unacknowledged-command
		 * dumps behind them, together burying every other line in the log.
		 * The recovery below is unchanged and still runs every frame; only
		 * the diagnostics are deduplicated.
		 *
		 * "overflowed" is also a misnomer on the CoDOL path: the flag is set
		 * when snapshot PREPARATION refuses, so it can fire with cursize far
		 * below maxsize (420 of 131072 in that match). Say which case it is
		 * instead of implying a size problem. */
		{
			static char codolReportedShape[MAX_CLIENTS][256];
			static int codolReportedTime[MAX_CLIENTS], codolSilenced[MAX_CLIENTS];
			const char *codolWhy = codol_snapshot_failure ? codol_snapshot_failure : "engine writer";
			unsigned codolSlot = slot;
			char codolShape[256]; unsigned csi = 0, cwi = 0;
			while (codolWhy[cwi] && csi + 1 < sizeof(codolShape)) {
				if (codolWhy[cwi] >= '0' && codolWhy[cwi] <= '9') {
					codolShape[csi++] = '#';
					while (codolWhy[cwi] >= '0' && codolWhy[cwi] <= '9') ++cwi;
				} else codolShape[csi++] = codolWhy[cwi++];
			}
			codolShape[csi] = 0;
			if (codolSlot < MAX_CLIENTS) {
				/* A new shape reports at once; a repeating one again every
				 * 10 s with how many frames it cost meanwhile. Silencing it
				 * for the life of the process hid a 14 s blackout. */
				codolReport = strncmp(codolReportedShape[codolSlot], codolShape, sizeof(codolShape) - 1) != 0 ||
				              svsHeader.time - codolReportedTime[codolSlot] >= 10000 ||
				              svsHeader.time < codolReportedTime[codolSlot];
				if (codolReport) {
					if (codolSilenced[codolSlot])
						Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL: %d more unprepared snapshot(s) for %s since the last report\n",
							codolSilenced[codolSlot], client->name);
					codolSilenced[codolSlot] = 0;
					codolReportedTime[codolSlot] = svsHeader.time;
					Q_strncpyz(codolReportedShape[codolSlot], codolShape, sizeof(codolReportedShape[codolSlot]));
				} else ++codolSilenced[codolSlot];
			}
		}
#endif
		if (codolReport)
			Com_PrintWarning(CON_CHANNEL_SERVER, "WARNING: snapshot %s for %s, trying to recover (%s; cursize %d of %d) (repeats are counted and reported every 10 s)\n",
				msg->cursize >= msg->maxsize ? "overflowed" : "could not be prepared", client->name,
				codol_snapshot_failure ? codol_snapshot_failure : "engine writer", msg->cursize, msg->maxsize);

		if ( client->state == CS_ACTIVE || client->state == CS_ZOMBIE )
		{
			if (codolReport) SV_ShowClientUnAckCommands(client);

			MSG_Clear( msg );
			MSG_WriteLong(msg, client->lastClientCommand);

			SV_UpdateServerCommandsToClientRecover( client, msg );

			MSG_WriteByte(msg, SV_WIRE_EOF);

		}
		if ( msg->overflowed == qtrue)
		{
			Com_PrintWarning(CON_CHANNEL_SERVER,"WARNING: client disconnected for msg overflow: %s\n", client->name);
			NET_OutOfBandPrint(NS_SERVER, &client->netchan.remoteAddress, "disconnect");
			SV_DropClient(client, "EXE_SERVERMESSAGEOVERFLOW");
		}
	}

#ifdef CODOL_SERVER
    {
        int packet = client->netchan.outgoingSequence;
        int wireAck = msg->cursize >= 4 ?
            (int)((uint32_t)msg->data[0] | ((uint32_t)msg->data[1] << 8) |
                  ((uint32_t)msg->data[2] << 16) | ((uint32_t)msg->data[3] << 24)) : -1;
        qboolean accepted = SV_SendMessageToClient(msg, client);
        SV_CodolTraceAckPublication(client, "snapshot", packet, wireAck, accepted, recovered);
        CODOL_FinishClientSnapshot(slot, msg, sequence, accepted);
    }
#else
    SV_SendMessageToClient(msg, client);
#endif
}


//#if 0

/*
===============
SV_AddEntToSnapshot
===============
*/
static void SV_AddEntToSnapshot(  int number, snapshotEntityNumbers_t *eNums )
{

	// if we are full, silently discard entities
	if ( eNums->numSnapshotEntities == MAX_SNAPSHOT_ENTITIES ) {
		return;
	}

	eNums->snapshotEntities[ eNums->numSnapshotEntities ] = number;
	eNums->numSnapshotEntities++;
}


/*
===============
SV_AddEntitiesVisibleFromPoint
===============
*/
static void SV_AddCachedEntitiesVisibleFromPoint(int from_num_entities, int from_first_entity, float *origin, signed int clientNum, snapshotEntityNumbers_t *eNums)
{
	int e, i, l;
	int clientcluster;
	int leafnum, boxleafnums;
	byte    *clientpvs;
	byte    *bitvector;
	float fogOpaqueDistSqrd;
	uint16_t clusternums[128];
	int lastLeaf;
	archivedEntity_t *aent;


	leafnum = CM_PointLeafnum( origin );
	clientcluster = CM_LeafCluster( leafnum );

	if(clientcluster < 0)
	{
		return;
	}

	clientpvs = CM_ClusterPVS( clientcluster );

	fogOpaqueDistSqrd = G_GetFogOpaqueDistSqrd();

	if ( fogOpaqueDistSqrd == 3.4028235e38 )
	{
      fogOpaqueDistSqrd = 0.0;
	}

	int maxCachedSnapshotEntities = sizeof(svs.cachedSnapshotEntities) / sizeof(svs.cachedSnapshotEntities[0]);

	for ( e = 0 ; e < from_num_entities ; e++ ) {

	    aent = &svs.cachedSnapshotEntities[(e + from_first_entity) % maxCachedSnapshotEntities];
        if ( (1 << (clientNum & 31)) & aent->r.clientMask[clientNum >> 5] || aent->s.number == clientNum )
		{
			continue;
		}

        if ( aent->r.svFlags & 0x18 )
		{
            SV_AddEntToSnapshot( e, eNums );
			continue;
		}

		boxleafnums = CM_BoxLeafnums(aent->r.absmin, aent->r.absmax, clusternums, sizeof(clusternums) / sizeof(clusternums[0]), &lastLeaf);
        if ( !boxleafnums )
		{
			continue;
		}

		bitvector = clientpvs;

		for ( i = 0 ; i < boxleafnums ; i++ )
		{
			l = CM_LeafCluster(clusternums[i]);
			if ( bitvector[l >> 3] & ( 1 << ( l & 7 ) ) && l != -1)
			{
				break;
			}
		}

		if ( i == boxleafnums)
		{
			continue;
		}

		if(!(fogOpaqueDistSqrd == 0.0 || BoxDistSqrdExceeds(aent->r.absmin, aent->r.absmax, origin, fogOpaqueDistSqrd) == qfalse) )
		{
			continue;
		}
		// add it
		SV_AddEntToSnapshot( e, eNums );
	}
}



/*
===============
SV_AddEntitiesVisibleFromPoint
===============
*/
static void SV_AddEntitiesVisibleFromPoint( float *origin, int clientNum, snapshotEntityNumbers_t *eNums )
{
	int e, i;
	gentity_t *ent;
	svEntity_t  *svEnt;
	int l;
	int clientcluster;
	int leafnum;
	byte    *clientpvs;
	byte    *bitvector;
	float fogOpaqueDistSqrd;


	leafnum = CM_PointLeafnum( origin );
	clientcluster = CM_LeafCluster( leafnum );

	if(clientcluster < 0)
	{
		return;
	}

	clientpvs = CM_ClusterPVS( clientcluster );

	fogOpaqueDistSqrd = G_GetFogOpaqueDistSqrd();

	if ( fogOpaqueDistSqrd == 3.4028235e38 )
	{
      fogOpaqueDistSqrd = 0.0;
	}

	for ( e = 0 ; e < sv.num_entities ; e++ ) {
		ent = SV_GentityNum( e );

		// never send entities that aren't linked in.
		// never send client's own entity, because it can
		// be regenerated from the playerstate
		if ( !ent->r.linked || e == clientNum)
		{
			continue;
		}


		if ( !ent->r.broadcastTime )
		{
		  if ( ent->r.svFlags & 1 || (1 << (clientNum & 31)) & ent->r.clientMask[clientNum >> 5] )
		  {
		    continue;
		  }

		}else{
			if(ent->r.broadcastTime < 0 || ent->r.broadcastTime >= svs.time)
			{
				SV_AddEntToSnapshot( e, eNums );
				continue;
			}
			ent->r.broadcastTime = 0;
		}


        if ( ent->r.svFlags & 0x18 )
        {
			SV_AddEntToSnapshot( e, eNums );
			continue;
		}

		svEnt = SV_SvEntityForGentity( ent );

		bitvector = clientpvs;

		// check individual leafs
		if ( !svEnt->numClusters ) {
			//goto notVisible; Different in CoD
			SV_AddEntToSnapshot( e, eNums );
			continue;
		}

		l = 0;
		for ( i = 0 ; i < svEnt->numClusters ; i++ )
		{
			l = svEnt->clusternums[i];
			if ( bitvector[l >> 3] & ( 1 << ( l & 7 ) ) )
			{
				break;
			}
		}

		// if we haven't found it to be visible,
		// check overflow clusters that coudln't be stored
		if ( i == svEnt->numClusters )
		{
			if ( svEnt->lastCluster )
			{
				for ( ; l <= svEnt->lastCluster ; l++ )
				{
					if ( bitvector[l >> 3] & ( 1 << ( l & 7 ) ) )
					{
						break;
					}
				}
				if ( l == svEnt->lastCluster ) {
					continue;    // not visible
				}
			} else {
				continue;
			}
		}

		if ( fogOpaqueDistSqrd != 0.0)
		{
			if(BoxDistSqrdExceeds(ent->r.absmin, ent->r.absmax, origin, fogOpaqueDistSqrd))
			{
				continue;
			}
		}
		// add it
		SV_AddEntToSnapshot( e, eNums );
	}
}

#ifdef CODOL_SERVER
/*
===============
CoDOL link parents

The visibility passes above cull every entity on its own, so a linked child
(a script model on linkTo; the published link lives in the entity-state
extension, wire +0xe8, low word = parent number + 1) could be sent while its
parent was culled by PVS or fog. C1 then prints "Entity #%i of type %i: parent
ent #%i not in snapshot." (0x4419a0) every frame and cannot place the child.
After the pass, every included child's parent is added too - regardless of
PVS, but only if it passes the filters that hide an entity from this client
outright (unlinked, SVF_NOCLIENT, clientMask/hide(), the client's own entity,
which C1 resolves from the predicted player). Parents of added parents follow.
The list is rebuilt in ascending entity order, without duplicates, as the
writer requires. A parent that still cannot be sent is handled per recipient
in the collector (CODOL_CollectServerEntitiesForClient), which publishes the
child unlinked for that frame.
===============
*/
static int SV_CodolLinkParent( const entityState_t *es )
{
	unsigned info;
	float origin[3], angles[3];

	if ( !CODOL_EntityStateLink( es, &info, origin, angles ) || !( info & 65535u ) )
	{
		return -1;
	}
	return (int)( info & 65535u ) - 1;
}

static qboolean SV_CodolParentSendable( gentity_t *parent, int clientNum )
{
	if ( !parent->r.inuse || !parent->r.linked )
	{
		return qfalse;
	}
	if ( parent->r.broadcastTime && ( parent->r.broadcastTime < 0 || parent->r.broadcastTime >= svs.time ) )
	{
		return qtrue;
	}
	if ( parent->r.svFlags & SVF_NOCLIENT || (1 << (clientNum & 31)) & parent->r.clientMask[clientNum >> 5] )
	{
		return qfalse;
	}
	return qtrue;
}

static void SV_CodolAddLinkParents( int clientNum, snapshotEntityNumbers_t *eNums )
{
	static byte present[MAX_GENTITIES];
	int i, e, parent, added = 0;

	Com_Memset( present, 0, sizeof( present ) );
	for ( i = 0; i < eNums->numSnapshotEntities; i++ )
	{
		present[eNums->snapshotEntities[i]] = 1;
	}
	// the list grows while it is walked, so an added parent's own parent is visited too
	for ( i = 0; i < eNums->numSnapshotEntities; i++ )
	{
		parent = SV_CodolLinkParent( &SV_GentityNum( eNums->snapshotEntities[i] )->s );
		if ( parent < 0 || parent >= sv.num_entities || parent == clientNum || present[parent] )
		{
			continue;
		}
		if ( !SV_CodolParentSendable( SV_GentityNum( parent ), clientNum ) )
		{
			continue;
		}
		if ( eNums->numSnapshotEntities == MAX_SNAPSHOT_ENTITIES )
		{
			break;
		}
		present[parent] = 1;
		eNums->snapshotEntities[eNums->numSnapshotEntities++] = parent;
		added = 1;
	}
	if ( !added )
	{
		return;
	}
	eNums->numSnapshotEntities = 0;
	for ( e = 0; e < MAX_GENTITIES; e++ )
	{
		if ( present[e] )
		{
			eNums->snapshotEntities[eNums->numSnapshotEntities++] = e;
		}
	}
}

/* The archived (killcam / delayed) world: eNums holds indices into the cached
 * snapshot, whose entities are stored in ascending entity order. */
static void SV_CodolAddCachedLinkParents( int from_num_entities, int from_first_entity, int clientNum, snapshotEntityNumbers_t *eNums )
{
	static short cacheIndex[MAX_GENTITIES];
	static byte present[MAX_GENTITIES];
	int maxCachedSnapshotEntities = sizeof(svs.cachedSnapshotEntities) / sizeof(svs.cachedSnapshotEntities[0]);
	archivedEntity_t *aent;
	int i, e, number, parent, added = 0;

	for ( e = 0; e < MAX_GENTITIES; e++ )
	{
		cacheIndex[e] = -1;
	}
	Com_Memset( present, 0, sizeof( present ) );
	for ( e = 0; e < from_num_entities; e++ )
	{
		number = svs.cachedSnapshotEntities[(e + from_first_entity) % maxCachedSnapshotEntities].s.number;
		if ( number >= 0 && number < MAX_GENTITIES && cacheIndex[number] < 0 )
		{
			cacheIndex[number] = (short)e;
		}
	}
	for ( i = 0; i < eNums->numSnapshotEntities; i++ )
	{
		present[eNums->snapshotEntities[i]] = 1;
	}
	for ( i = 0; i < eNums->numSnapshotEntities; i++ )
	{
		aent = &svs.cachedSnapshotEntities[(eNums->snapshotEntities[i] + from_first_entity) % maxCachedSnapshotEntities];
		parent = SV_CodolLinkParent( &aent->s );
		if ( parent < 0 || parent >= MAX_GENTITIES || parent == clientNum || cacheIndex[parent] < 0 )
		{
			continue;
		}
		e = cacheIndex[parent];
		if ( present[e] )
		{
			continue;
		}
		aent = &svs.cachedSnapshotEntities[(e + from_first_entity) % maxCachedSnapshotEntities];
		if ( aent->r.svFlags & SVF_NOCLIENT || (1 << (clientNum & 31)) & aent->r.clientMask[clientNum >> 5] )
		{
			continue;
		}
		if ( eNums->numSnapshotEntities == MAX_SNAPSHOT_ENTITIES )
		{
			break;
		}
		present[e] = 1;
		eNums->snapshotEntities[eNums->numSnapshotEntities++] = e;
		added = 1;
	}
	if ( !added )
	{
		return;
	}
	eNums->numSnapshotEntities = 0;
	for ( e = 0; e < from_num_entities && e < MAX_GENTITIES; e++ )
	{
		if ( present[e] )
		{
			eNums->snapshotEntities[eNums->numSnapshotEntities++] = e;
		}
	}
}
#endif

static cachedSnapshot_t *SV_GetCachedSnapshot(int *pArchiveTime)
{
  int frame;
  int archivedFrame;
  cachedSnapshot_t *cachedSnap;

  if ( *pArchiveTime <= 0 )
  {
	return 0;
  }

  frame = ((uint64_t)*pArchiveTime * (uint64_t)sv_fps->integer) / (uint64_t)1000;
  archivedFrame = svs.nextArchivedSnapshotFrames - frame;

  if ( archivedFrame < svs.nextArchivedSnapshotFrames - NUM_ARCHIVED_FRAMES )
  {
    archivedFrame = svs.nextArchivedSnapshotFrames - NUM_ARCHIVED_FRAMES;
    *pArchiveTime = ((uint64_t)1000 * (uint64_t)(svs.nextArchivedSnapshotFrames - (svs.nextArchivedSnapshotFrames - NUM_ARCHIVED_FRAMES))) / (uint64_t)sv_fps->integer;
  }

  if ( archivedFrame < 0 )
  {
    archivedFrame = 0;
    *pArchiveTime = ((uint64_t)1000 * (uint64_t)svs.nextArchivedSnapshotFrames) / (uint64_t)sv_fps->integer;
  }

  for( ; archivedFrame < svs.nextArchivedSnapshotFrames; ++archivedFrame)
  {
    cachedSnap = SV_GetCachedSnapshotInternal(archivedFrame, 0, 1);

    if ( cachedSnap )
    {
      return cachedSnap;
    }
  }
  *pArchiveTime = 0;
  return NULL;
}

/*
=============
SV_BuildClientSnapshot

Decides which entities are going to be visible to the client, and
copies off the playerstate and areabits.

This properly handles multiple recursive portals, but the render
currently doesn't.

For viewing through other player's eyes, clent can be something other than client->gentity
=============
*/
static void SV_BuildClientSnapshot( client_t *client ) {

	vec3_t org;
	clientSnapshot_t            *frame;
	snapshotEntityNumbers_t entityNumbers;
	int i;
	archivedEntity_t			*aent;
	gentity_t              		*ent;
	entityState_t               *entState;
	cachedClient_t				*cachedClient;
	clientState_t               *clientStateSource;
	clientState_t               *clientState;
	gentity_t					*clent;
	int clientNum;
	playerState_t               *ps;
	int							archiveTime;
	cachedSnapshot_t			*cachedSnap;
	client_t					*snapClient;

	// this is the frame we are creating
	frame = &client->frames[ client->netchan.outgoingSequence & PACKET_MASK ];
#ifdef CODOL_SERVER
    CODOL_InvalidateClientSnapshotHud((unsigned)(client-svs.clients));
    CODOL_ClearClientNativeFrame((unsigned)(client-svs.clients));
    /* The actor capture belongs to the snapshot being built, so it is dropped
     * with the frame it would have described. */
    CODOL_InvalidateClientSnapshotActors((unsigned)(client-svs.clients));
    codol_snapshot_ready[client-svs.clients]=0;
#endif

	// clear everything in this snapshot
	entityNumbers.numSnapshotEntities = 0;

	// show_bug.cgi?id=62
	frame->num_entities = 0;
	frame->num_clients = 0;

	clent = client->gentity;
	if ( !clent || client->state == CS_ZOMBIE || sv.state < SS_GAME ) {
		return;
	}

	frame->first_entity = svs.nextSnapshotEntities;
    frame->first_client = svs.nextSnapshotClients;

	clientNum = client - svs.clients;


	archiveTime = G_GetClientArchiveTime(clientNum);

	cachedSnap = SV_GetCachedSnapshot(&archiveTime);

	G_SetClientArchiveTime(clientNum, archiveTime);


	// grab the current playerState_t
	ps = SV_GameClientNum( clientNum );

	frame->ps = *ps;
#ifdef CODOL_SERVER
    /* The serialized copy carries the extension of the state it was copied
     * from, which for a following spectator is the archived state the
     * retained spectator path already applied to this client. */
    CODOL_PlayerStateExtCopy(&frame->ps, ps);
    /* Character viewmodels belong to the captured snapshot. Applying them to
     * the live state first made this path depend on pointer identity and let a
     * later live-state writer replace the pair before capture. The frame slot
     * and its extension are tracked storage, so apply the stored native arm /
     * hand pair after copying both halves. A spectator following another
     * player keeps the followed state exactly as the retained path supplied it. */
    CODOL_ApplyStoredClientViewmodels((unsigned)clientNum,&frame->ps);
    /* Resolve HUD while ps still identifies the live captured client copy.
     * The CoDOL writer must require the sequence-matched capture; failure
     * leaves it invalid instead of reusing another frame's HUD. */
    CODOL_CaptureClientSnapshotHud((unsigned)(client-svs.clients),
        (uint32_t)client->netchan.outgoingSequence,&ps->hud);
#endif

	//Update client num from other source here
	clientNum = frame->ps.clientNum;


	if ( clientNum < 0 || clientNum >= MAX_GENTITIES ) {
		Com_Error( ERR_DROP, "SV_BuildClientSnapshot(): bad gEnt" );
	}

	// find the client's viewpoint
	VectorCopy( ps->origin, org );
	org[2] += ps->viewHeightCurrent;

//----(SA)	added for 'lean'
	// need to account for lean, so areaportal doors draw properly
	AddLeanToPosition(org, ps->viewangles[1], ps->leanf, 16.0, 20.0);
//----(SA)	end

	if(cachedSnap)
	{
		int snapTime = svs.time - cachedSnap->time;

		int maxCachedSnapshotEntities = sizeof(svs.cachedSnapshotEntities) / sizeof(svs.cachedSnapshotEntities[0]);

		SV_AddCachedEntitiesVisibleFromPoint(cachedSnap->num_entities, cachedSnap->first_entity, org, clientNum, &entityNumbers);
#ifdef CODOL_SERVER
		SV_CodolAddCachedLinkParents(cachedSnap->num_entities, cachedSnap->first_entity, clientNum, &entityNumbers);
#endif

        for ( i = 0 ;i < entityNumbers.numSnapshotEntities; ++i )
        {
            entState = &svs.snapshotEntities[svs.nextSnapshotEntities % svs.numSnapshotEntities];
            aent = &svs.cachedSnapshotEntities[(cachedSnap->first_entity + entityNumbers.snapshotEntities[i]) % maxCachedSnapshotEntities];

			*entState = aent->s;
#ifdef CODOL_SERVER
            /* The serialized ring slot carries the epoch of the archived
             * entity state it was copied from. */
            CODOL_EntityStateExtCopy(entState, &aent->s);
#endif

            if ( entState->lerp.pos.trTime )
			{
              entState->lerp.pos.trTime += snapTime;
			}
			if ( entState->lerp.apos.trTime )
			{
              entState->lerp.apos.trTime += snapTime;
			}
#ifdef CODOL_SERVER
            if ( entState->eType == ET_MG42 )
            {
              /* The captured turret's time2 word holds status bytes, not a
               * timestamp. Rebase the two interpolation stamps instead so
               * delayed playback preserves elapsed heat/spin time. */
              entState->lerp.u.turret.lastBarrelRotChangeTime = (int)(
                (uint32_t)entState->lerp.u.turret.lastBarrelRotChangeTime + (uint32_t)snapTime);
              entState->lerp.u.turret.lastHeatChangeTime = (int)(
                (uint32_t)entState->lerp.u.turret.lastHeatChangeTime + (uint32_t)snapTime);
            }
            else
#endif
            if ( entState->time2 )
			{
              entState->time2 += snapTime;
			}

            if ( entState->eType == ET_MISSILE || entState->eType == ET_GENERAL || entState->eType == ET_EVENTS + EV_CUSTOM_EXPLODE )
			{
              entState->lerp.u.anonymous.data[0] += snapTime;
			}
			svs.nextSnapshotEntities++;
			// this should never hit, map should always be restarted first in SV_Frame
			if ( svs.nextSnapshotEntities >= 0x7FFFFFFE ) {
				Com_Error( ERR_FATAL, "svs.nextSnapshotEntities wrapped" );
			}

			frame->num_entities++;
        }


		int maxCachedClients = sizeof(svs.cachedSnapshotClients) / sizeof(svs.cachedSnapshotClients[0]);

		for ( i = 0; i < cachedSnap->num_clients; ++i )
        {
			cachedClient = &svs.cachedSnapshotClients[(i + cachedSnap->first_client) % maxCachedClients];
			clientState = &svs.snapshotClients[svs.nextSnapshotClients % svs.numSnapshotClients];
			*clientState = cachedClient->cs;
#ifdef CODOL_SERVER
            if (!CODOL_CaptureArchivedClientAbilities(svs.nextSnapshotClients, &cachedClient->cs))
                Com_Error(ERR_DROP, "CoDOL archived client ability capture failed");
#endif
			svs.nextSnapshotClients++;

			// this should never hit, map should always be restarted first in SV_Frame
			if ( svs.nextSnapshotClients >= 0x7FFFFFFE ) {
				Com_Error( ERR_FATAL, "svs.nextSnapshotClients wrapped" );
			}
			frame->num_clients++;
        }
#ifdef CODOL_SERVER
        /* This recipient is being served an archived world: its actors are the
         * table archived with the same archived frame, never the live one. */
        CODOL_CaptureClientSnapshotActors((unsigned)(client-svs.clients),
            (uint32_t)client->netchan.outgoingSequence,
            cachedSnap->archivedFrame, cachedSnap->time);
        /* The actor animation poses archived with that same frame, so a killcam
         * or late-joining recipient is bootstrapped from the captured pose. */
        CODOL_ActorDeliveryCapture((unsigned)(client-svs.clients),
            (uint32_t)client->netchan.outgoingSequence,
            cachedSnap->archivedFrame, cachedSnap->time);
        /* The archived entity/client ring and player extension are captured
         * above. Submit them to the same converter as a live snapshot; its
         * HUD/actor sequence checks still reject missing captures. */
        codol_snapshot_ready[client-svs.clients]=1;
        codol_snapshot_sequence[client-svs.clients]=(uint32_t)client->netchan.outgoingSequence;
#endif
		return;
	}



	// add all the entities directly visible to the eye, which
	// may include portal entities that merge other viewpoints
	SV_AddEntitiesVisibleFromPoint( org, clientNum, &entityNumbers );
#ifdef CODOL_SERVER
	SV_CodolAddLinkParents( clientNum, &entityNumbers );
#endif

	// copy the entity states out
	for ( i = 0 ; i < entityNumbers.numSnapshotEntities ; i++ ) {
		ent = SV_GentityNum( entityNumbers.snapshotEntities[i] );
		entState = &svs.snapshotEntities[svs.nextSnapshotEntities % svs.numSnapshotEntities];
		*entState = ent->s;
#ifdef CODOL_SERVER
		CODOL_EntityStateExtCopy(entState, &ent->s);
#endif
		svs.nextSnapshotEntities++;
		// this should never hit, map should always be restarted first in SV_Frame
		if ( svs.nextSnapshotEntities >= 0x7FFFFFFE ) {
			Com_Error( ERR_FATAL, "svs.nextSnapshotEntities wrapped" );
		}
		frame->num_entities++;
	}


	// copy the client states out
	for ( snapClient = svs.clients, i = 0 ; i < sv_maxclients->integer ; i++, snapClient++ )
	{
		if(snapClient->state < CS_PRIMED || (!snapClient->gamestateSent && snapClient->netchan.remoteAddress.type != NA_BOT))
		{
			continue;
		}

		clientStateSource = G_GetClientState( i );

		if(snapClient->undercover && i != clientNum)
		{
			continue; // skip send gamestate for undercover players
		}

		clientState = &svs.snapshotClients[svs.nextSnapshotClients % svs.numSnapshotClients];
		*clientState = *clientStateSource;
#ifdef CODOL_SERVER
        if (!CODOL_CapturePublishedClientAbilities(svs.nextSnapshotClients, (unsigned)i))
            Com_Error(ERR_DROP, "CoDOL client ability capture failed");
#endif

		svs.nextSnapshotClients++;
		// this should never hit, map should always be restarted first in SV_Frame
		if ( svs.nextSnapshotClients >= 0x7FFFFFFE ) {
			Com_Error( ERR_FATAL, "svs.nextSnapshotClients wrapped" );
		}
		frame->num_clients++;
	}

#ifdef CODOL_SERVER
    /* Live world: produce the actor table now, while this snapshot's entity
     * states are the live ones it was built from. */
    CODOL_CaptureClientSnapshotActors((unsigned)(client-svs.clients),
        (uint32_t)client->netchan.outgoingSequence,-1,0);
    /* svs.time, not svsHeader.time: SV_SendClientMessages builds every
     * client's snapshot BEFORE it calls SV_SetServerStaticHeader, so here
     * svsHeader.time is still the previous frame's time. The actor animation
     * journal was cut one frame behind the events G_RunFrame had just
     * appended at svs.time, the cut was refused ("older than the last
     * appended event"), and every snapshot to a recipient who could see a
     * dog was rejected as "actor animation delivery" until the match ended. */
    CODOL_ActorDeliveryCapture((unsigned)(client-svs.clients),
        (uint32_t)client->netchan.outgoingSequence,-1,(unsigned)svs.time);
    codol_snapshot_ready[client-svs.clients]=1;
    codol_snapshot_sequence[client-svs.clients]=(uint32_t)client->netchan.outgoingSequence;
#endif
}
//#endif



/*
 =======================
 SV_SendClientMessages
 =======================
 */

void SV_SendClientMessages( void ) {
	int i, freeBytes, index;
	msg_t msg;
	byte buf[0x20000];
	client_t *c;
	byte snapClients[MAX_CLIENTS];
	int numclients = 0; // NERVE - SMF - net debugging
	/*
	SV_SendClientMessagesA( );
	return;
	 */
	sv.bpsTotalBytes = 0; // NERVE - SMF - net debugging
	sv.ubpsTotalBytes = 0; // NERVE - SMF - net debugging

	// send a message to each connected client
	for ( i = 0, c = svs.clients ; i < sv_maxclients->integer ; i++, c++ ) {
		if ( !c->state || c->netchan.remoteAddress.type == NA_BOT)
		{
			snapClients[i] = 0;
			continue; // not connected
		}

#ifndef CODOL_SERVER
		ReliableMessagesFrame(c->reliablemsg.netstate, svs.time);

		SV_ReceiveReliableMessages(c);
#endif
		if ( svs.time < c->nextSnapshotTime ) {
			snapClients[i] = 0;
			continue; // not time yet
		}

		numclients++; // NERVE - SMF - net debugging

		// send additional message fragments if the last message
		// was too large to send at once
		if ( c->netchan.unsentFragments ) {
			c->nextSnapshotTime = svs.time + SV_RateMsec( c, c->netchan.unsentLength - c->netchan.unsentFragmentStart );
			SV_Netchan_TransmitNextFragment( c );
			snapClients[i] = 0;
			continue;
		}

		// generate a new message
		snapClients[i] = 1;

#ifdef CODOL_SERVER
		/* Configstring updates held while the client loaded the map. Until
		 * they are all queued the client gets reliable commands only: a
		 * snapshot must not name a weapon or model it has not registered. */
		if ( c->state == CS_ACTIVE ) {
			CODOL_PumpDeferredConfigstrings( c );
			if ( CODOL_DeferredConfigstringsHoldSnapshot( c ) ) {
				snapClients[i] = 2;
				continue;
			}
		}
#endif
		if ( c->state == CS_ACTIVE || c->state == CS_ZOMBIE )
            SV_BuildClientSnapshot( c );

	}

	SV_SetServerStaticHeader();

	for (i = 0, c = svs.clients; i < sv_maxclients->integer; i++, c++) {

		if(snapClients[i] == 0)
			continue;

		SV_BeginClientSnapshot( c, &msg );

		if((c->state == CS_ACTIVE || c->state == CS_ZOMBIE) && snapClients[i] != 2)
			SV_WriteSnapshotToClient( c, &msg );

		SV_EndClientSnapshot(c, &msg);
		SV_SendClientVoiceData( c );
	}

	// NERVE - SMF - net debugging
	if ( sv_showAverageBPS->integer && numclients > 0 ) {
		float ave = 0, uave = 0;

		for ( i = 0; i < MAX_BPS_WINDOW - 1; i++ ) {
			sv.bpsWindow[i] = sv.bpsWindow[i + 1];
			ave += sv.bpsWindow[i];

			sv.ubpsWindow[i] = sv.ubpsWindow[i + 1];
			uave += sv.ubpsWindow[i];
		}

		sv.bpsWindow[MAX_BPS_WINDOW - 1] = sv.bpsTotalBytes;
		ave += sv.bpsTotalBytes;

		sv.ubpsWindow[MAX_BPS_WINDOW - 1] = sv.ubpsTotalBytes;
		uave += sv.ubpsTotalBytes;

		if ( sv.bpsTotalBytes >= sv.bpsMaxBytes ) {
			sv.bpsMaxBytes = sv.bpsTotalBytes;
		}

		if ( sv.ubpsTotalBytes >= sv.ubpsMaxBytes ) {
			sv.ubpsMaxBytes = sv.ubpsTotalBytes;
		}

		sv.bpsWindowSteps++;

		if ( sv.bpsWindowSteps >= MAX_BPS_WINDOW ) {
			float comp_ratio;

			sv.bpsWindowSteps = 0;

			ave = ( ave / (float)MAX_BPS_WINDOW );
			uave = ( uave / (float)MAX_BPS_WINDOW );

			comp_ratio = ( 1 - ave / uave ) * 100.f;
			sv.ucompAve += comp_ratio;
			sv.ucompNum++;

			Com_DPrintf(CON_CHANNEL_SERVER, "bpspc(%2.0f) bps(%2.0f) pk(%i) ubps(%2.0f) upk(%i) cr(%2.2f) acr(%2.2f)\n",
						ave / (float)numclients, ave, sv.bpsMaxBytes, uave, sv.ubpsMaxBytes, comp_ratio, sv.ucompAve / sv.ucompNum );
		}
	}
	// -NERVE - SMF

	if ( sv.state != SS_GAME )
	{
		SV_GetServerStaticHeader();
		return;
	}

	MSG_Init(&msg, buf, sizeof(buf));
	SV_ArchiveSnapshot(&msg);

	SV_GetServerStaticHeader();

	if ( msg.overflowed == qtrue )
	{
		Com_DPrintf(CON_CHANNEL_SERVER,"SV_ArchiveSnapshot: ignoring snapshot because it overflowed.\n");
		return;
	}

	int maxArchivedSnapshotFrames = sizeof(svs.archivedSnapshotFrames) / sizeof(svs.archivedSnapshotFrames[0]);

	svs.archivedSnapshotFrames[svs.nextArchivedSnapshotFrames % maxArchivedSnapshotFrames].start = svs.nextArchivedSnapshotBuffer;
	svs.archivedSnapshotFrames[svs.nextArchivedSnapshotFrames % maxArchivedSnapshotFrames].size = msg.cursize;

	index = svs.nextArchivedSnapshotBuffer % ARCHIVEDSSBUF_SIZE;

	svs.nextArchivedSnapshotBuffer += msg.cursize;

	if ( svs.nextArchivedSnapshotBuffer >= (signed int)0x7FFFFFFE )
	{
		Com_Error(0, "svs.nextArchivedSnapshotBuffer wrapped");
		return;
	}
	freeBytes = ARCHIVEDSSBUF_SIZE - index;

	if ( msg.cursize > freeBytes )
	{
		memcpy(&svs.archivedSnapshotBuffer[index], msg.data, freeBytes);
		memcpy(svs.archivedSnapshotBuffer, &msg.data[freeBytes], msg.cursize - freeBytes);

	}
	else
	{
		memcpy(&svs.archivedSnapshotBuffer[index], msg.data, msg.cursize);
	}

	svs.nextArchivedSnapshotFrames++;

	if (  svs.nextArchivedSnapshotFrames >= (signed int)0x7FFFFFFE  ){
		Com_Error(0, "svs.nextArchivedSnapshotFrames wrapped");
	}

}


void __cdecl SV_GetClientPositionsFromCachedSnap(cachedSnapshot_t *cachedFrame, vec3_t *pos, vec3_t *angles, bool *success)
{
  struct archivedEntity_s *cachedEnt;
  unsigned int i;
  int clientNum;

  for ( i = 0; i < cachedFrame->num_entities; ++i )
  {
    assertx(cachedFrame->first_entity >= 0, "cachedFrame->first_entity = %i", cachedFrame->first_entity);

    cachedEnt = &svs.cachedSnapshotEntities[(i + cachedFrame->first_entity) % svs.numCachedSnapshotEntities];
    clientNum = cachedEnt->s.number;
    if ( cachedEnt->s.number >= MAX_CLIENTS )
    {
      break;
    }
#ifdef CODOL_SERVER
    /* C1 corpses19..26 are inside IW3's old client-number reservation.
     * Rewind positions describe players, not every low-numbered entity. */
    if(clientNum < 0 || cachedEnt->s.eType != ET_PLAYER) continue;
#endif
    success[clientNum] = true;
    BG_EvaluateTrajectory(&cachedEnt->s.lerp.pos, cachedFrame->time, pos[clientNum]);
    angles[clientNum][0] = 0.0;
    angles[clientNum][1] = cachedEnt->s.lerp.apos.trBase[1];
    angles[clientNum][2] = 0.0;
  }
}


bool __cdecl SV_GetClientPositionsAtTime(int gametime, vec3_t *pos, vec3_t *angles, bool *success)
{
  vec3_t endPos[MAX_CLIENTS];
  int startOffset;
  int rewindDeltaTime;
  vec3_t startAngles[MAX_CLIENTS];
  bool foundStart;
  int endOffset;
  float progress;
  vec3_t startPos[MAX_CLIENTS];
  bool startSuccess[MAX_CLIENTS];
  bool endSuccess[MAX_CLIENTS];
  cachedSnapshot_t *frameStart;
  vec3_t endAngles[MAX_CLIENTS];
  bool foundEnd;
  int clientNum;
  cachedSnapshot_t *frameEnd;
  int snapOffset;


  rewindDeltaTime = svs.time - gametime;
  int frametime = 1000000 / sv_fps->integer; //in usec for accuracy
  int frameHistCount = (1000*rewindDeltaTime) / frametime;
  startOffset = (frametime * (frameHistCount + 2)) / 1000;
  endOffset = (frametime * (frameHistCount + 1)) / 1000;
  frameStart = SV_GetCachedSnapshot(&startOffset);
  frameEnd = SV_GetCachedSnapshot(&endOffset);
  if ( frameStart || frameEnd )
  {
    snapOffset = 1;
    while ( frameEnd && frameEnd->time < gametime )
    {
      frameStart = frameEnd;
      endOffset = (frametime * (--snapOffset + frameHistCount)) / 1000;
      frameEnd = SV_GetCachedSnapshot(&endOffset);
    }
    if ( frameEnd && snapOffset != 1 )
    {
      Com_Printf(CON_CHANNEL_SERVER, "Adjusted frameEnd by %i snaps - Requested time=%d Got time=%d\n", 1 - snapOffset, gametime, frameEnd->time);
    }
    snapOffset = 2;
    while ( frameStart && frameStart->time > gametime )
    {
      frameStart = frameEnd;
      startOffset = (frametime * (++snapOffset + frameHistCount)) / 1000;
      frameStart = SV_GetCachedSnapshot(&startOffset);
    }
    if ( frameStart && snapOffset != 2 )
    {
      if(CODOL_TRACE_VERBOSE())
      Com_Printf(CON_CHANNEL_SERVER, "Adjusted frameStart by %i snaps\n", snapOffset - 2);
    }
    foundStart = frameStart != 0;
    foundEnd = frameEnd != 0;

    memset(startSuccess, 0, sizeof(startSuccess));
    memset(endSuccess, 0, sizeof(endSuccess));

    if ( frameStart )
    {
      assertx(frameStart->time <= gametime, "frameStart->time is %i for gametime %i", frameStart->time, gametime);

      SV_GetClientPositionsFromCachedSnap(frameStart, startPos, startAngles, startSuccess);
    }
    if ( foundEnd )
    {
      assertx(frameEnd->time >= gametime, "frameEnd->time is %i for gametime %i", frameEnd->time, gametime);

      SV_GetClientPositionsFromCachedSnap(frameEnd, endPos, endAngles, endSuccess);
    }
    if ( foundStart && foundEnd )
    {
      if ( startOffset == endOffset )
      {
        progress = 0.0;
      }
      else
      {
        progress = (float)(gametime - frameStart->time) / (float)(frameEnd->time - frameStart->time);
      }
      assert(progress >= 0);
      assert(progress <= 1);
    }
    else
    {
      progress = 0.0;
    }
    for ( clientNum = 0; clientNum < MAX_CLIENTS; ++clientNum )
    {
      if ( startSuccess[clientNum] && endSuccess[clientNum] )
      {
	assertx(frameStart->time <= gametime, "%i > %i", frameStart->time, gametime);
	assertx(frameEnd->time >= gametime, "%i < %i", frameEnd->time, gametime);

        success[clientNum] = true;
        Vec3Lerp(startPos[clientNum], endPos[clientNum], progress, pos[clientNum]);
        Vec3Lerp(startAngles[clientNum], endAngles[clientNum], progress, angles[clientNum]);

	assert(!IS_NAN( pos[clientNum][0] ));
	assert(!IS_NAN( pos[clientNum][1] ));
	assert(!IS_NAN( pos[clientNum][2] ));

	assert(!IS_NAN( angles[clientNum][0] ));
	assert(!IS_NAN( angles[clientNum][1] ));
	assert(!IS_NAN( angles[clientNum][2] ));
      }
      else if ( startSuccess[clientNum] )
      {
        success[clientNum] = true;
        VectorCopy(startPos[clientNum], pos[clientNum]);
        VectorCopy(startAngles[clientNum], angles[clientNum]);

        assert(!IS_NAN( pos[clientNum][0]));
        assert(!IS_NAN( pos[clientNum][1]));
        assert(!IS_NAN( pos[clientNum][2]));

        assert(!IS_NAN( angles[clientNum][0]));
        assert(!IS_NAN( angles[clientNum][1]));
        assert(!IS_NAN( angles[clientNum][2]));

      }
      else if ( endSuccess[clientNum] )
      {
        success[clientNum] = true;

        VectorCopy(endPos[clientNum], pos[clientNum]);
        VectorCopy(endAngles[clientNum], angles[clientNum]);

        assert(!IS_NAN( pos[clientNum][0]));
        assert(!IS_NAN( pos[clientNum][1]));
        assert(!IS_NAN( pos[clientNum][2]));

        assert(!IS_NAN( angles[clientNum][0]));
        assert(!IS_NAN( angles[clientNum][1]));
        assert(!IS_NAN( angles[clientNum][2]));
      }
    }
    return true;
  }
  Com_Printf(CON_CHANNEL_SERVER, "Failed to get a cached snapshot for antilag - offset is %i\n", rewindDeltaTime);
  return false;
}





clientState_t * G_GetClientStateLocal(int clientNum)
{
  //assert(svsHeaderValid);

  return (clientState_t *)((byte*)svsHeader.firstClientState + clientNum * svsHeader.clientSize);
}

int GetFollowPlayerStateLocal(int clientNum, playerState_t *ps)
{
  unsigned int index;

  assert(svsHeaderValid);

  if ( *(int *)((byte *)&svsHeader.firstPlayerState->otherFlags + clientNum * svsHeader.clientSize) & POF_PLAYER )
  {
    memcpy(ps, (byte*)svsHeader.firstPlayerState + clientNum * svsHeader.clientSize, sizeof(*ps));
    for ( index = 0; index < 0x1F && ps->hud.current[index].type; ++index )
    {
      memset(&ps->hud.current[index], 0, sizeof(ps->hud.current[0]));
      assert(ps->hud.current[index].type == HE_TYPE_FREE);
    }
/*
    while ( index < 0x1F )
    {
      assert(!memcmp( &ps->hud.current[index], &g_dummyHudCurrent, sizeof( g_dummyHudCurrent ) ));
      ++index;
    }
*/
    return 1;
  }
  memset(ps, 0, sizeof(*ps));
  return 0;
}

gentity_t *__cdecl SV_GentityNumLocal(int num)
{
    assert(svsHeaderValid);
    return (gentity_t *)((char *)svsHeader.gentities + num * svsHeader.gentitySize);
}

void MSG_TestDeltaAE(snapshotInfo_t* snapInfo, int time, archivedEntity_t* baseline, archivedEntity_t *to, int refent);
void MSG_TestDeltaPS(snapshotInfo_t* snapInfo, int time, playerState_t* baseline, playerState_t *to);
void MSG_TestDeltaCS(snapshotInfo_t* snapInfo, int time, clientState_t* baseline, clientState_t *to);


void SV_ArchiveSnapshot(msg_t *msg)
{
#ifdef CODOL_SERVER
  /* An epoch record follows every entity. Emit the entity header even when
   * its native fields match baseline, so the reader has a record to pair it
   * with (and can observe an epoch change after an 8-bit counter wrap). */
  const enum DeltaFlags entityArchiveFlags = DELTA_FLAGS_FORCE;
#else
  const enum DeltaFlags entityArchiveFlags = 0;
#endif
//  struct MatchState *matchState; 
  clientState_t *cs2;
  clientState_t *cs3; 
  clientState_t *lcs;
  cachedClient_t *cachedClient2;
  int e;
  client_t *client;
  int clientNum;
  snapshotInfo_t snapInfo = { 0 };
  archivedEntity_t *archEnt;
  int j;
  int x;
  cachedSnapshot_t *cachedSnap;
  gentity_t *gent;
  int n;
#ifndef NDEBUG
  int lastEntityNum;
#endif
  archivedEntity_t to;
  int i;
  playerState_t ps;
//  struct MatchState *from;
  archivedEntity_t *baseline;
  cachedSnapshot_t *cachedFrame;
  cachedClient_t *cachedCl;

//  assert(svsHeaderValid);
  assert(svsHeader.cachedSnapshotEntities);
  assert(svsHeader.cachedSnapshotClients);
  assert(svsHeader.archivedSnapshotBuffer);
  assert(svsHeader.cachedSnapshotFrames);

//  assert(Sys_IsServerThread() || !sv.smp);

  snapInfo.archived = true;

  n = svsHeader.nextCachedSnapshotFrames - 512;
  if ( svsHeader.nextCachedSnapshotFrames - 512 < 0 )
  {
    n = 0;
  }
#ifndef NDEBUG
  MSG_WriteLong(msg, 0xdeadbeef);
#endif
  svsHeader.archivedEntityCount = 0;
  for ( i = svsHeader.nextCachedSnapshotFrames - 1; i >= n; --i )
  {
    cachedFrame = &svsHeader.cachedSnapshotFrames[i % 512];
    if ( cachedFrame->archivedFrame >= svsHeader.nextArchivedSnapshotFrames - svsHeader.fps && !cachedFrame->usesDelta )
    {
      if ( cachedFrame->first_entity >= svsHeader.nextCachedSnapshotEntities - svsHeader.numCachedSnapshotEntities
        && cachedFrame->first_client >= svsHeader.nextCachedSnapshotClients - svsHeader.numCachedSnapshotClients )
      {
        MSG_WriteBit0(msg);

#ifndef NDEBUG
        MSG_WriteLong(msg, 0xdeadbee0);
#endif

        MSG_WriteLong(msg, cachedFrame->archivedFrame);
        MSG_WriteLong(msg, svsHeader.time);
//        MSG_WriteLong(msg, svsHeader.physicsTime);
        MSG_ClearLastReferencedEntity(msg);
/*
        from = &svsHeader.cachedSnapshotMatchStates[cachedFrame->matchState % svsHeader.numCachedSnapshotMatchStates];
        matchState = G_GetMatchStateLocal();
        MSG_WriteDeltaMatchState(&snapInfo, msg, svsHeader.time, from, matchState);
	MSG_ClearLastReferencedEntity(msg);
	*/
        cachedCl = 0;
        clientNum = 0;
        j = 0;
        //PIXBeginNamedEvent(3158271, "clients");
        while ( clientNum < svsHeader.maxclients || j < cachedFrame->num_clients )
        {
          if ( clientNum >= svsHeader.maxclients || svsHeader.clients[clientNum].state >= CS_PRIMED )
          {
            if ( j < cachedFrame->num_clients )
            {
              cachedClient2 = &svsHeader.cachedSnapshotClients[(j + cachedFrame->first_client)
                                                             % svsHeader.numCachedSnapshotClients];
              x = cachedClient2->cs.clientIndex;
            }
            else
            {
              cachedClient2 = 0;
              x = 9999;
            }
            snapInfo.clnum = clientNum;
            if ( clientNum == x )
            {
	      assert(cachedClient2);

              cs2 = G_GetClientStateLocal(clientNum);
              MSG_TestDeltaCS(&snapInfo, svsHeader.time, &cachedClient2->cs, cs2);

              MSG_WriteDeltaClient(&snapInfo, msg, svsHeader.time, &cachedClient2->cs, cs2, 1);
#ifdef CODOL_SERVER
              CODOL_WriteArchivedClientAbilities(msg, clientNum, NULL);
#endif
              if ( GetFollowPlayerStateLocal(clientNum, &ps) )
              {
                MSG_WriteBit1(msg);
                if ( cachedClient2->playerStateExists )
                {

		    MSG_TestDeltaPS(&snapInfo, svsHeader.time, &cachedClient2->ps, &ps);

                  MSG_WriteDeltaPlayerstate(&snapInfo, msg, svsHeader.time, &cachedClient2->ps, &ps);
#ifdef CODOL_SERVER
                  /* The serialized state is this client's live one; its
                   * extension record uses the same baseline the playerState
                   * was delta'd against, so the reader restores the two
                   * halves together. */
                  CODOL_PlayerStateExtWriteClient(msg, clientNum, &cachedClient2->ps);
#endif
                }
                else
                {
		    MSG_TestDeltaPS(&snapInfo, svsHeader.time, NULL, &ps);

                  MSG_WriteDeltaPlayerstate(&snapInfo, msg, svsHeader.time, NULL, &ps);
#ifdef CODOL_SERVER
                  CODOL_PlayerStateExtWriteClient(msg, clientNum, NULL);
#endif
                }
              }
              else
              {
                MSG_WriteBit0(msg);
              }
              ++j;
              ++clientNum;
            }
            else if ( clientNum >= x )
            {
              if ( clientNum > x )
              {
                ++j;
              }
            }
            else
            {
              cs3 = G_GetClientStateLocal(clientNum);

              MSG_TestDeltaCS(&snapInfo, svsHeader.time, NULL, cs3);

              MSG_WriteDeltaClient(&snapInfo, msg, svsHeader.time, NULL, cs3, 1);
#ifdef CODOL_SERVER
              CODOL_WriteArchivedClientAbilities(msg, clientNum, NULL);
#endif
              if ( GetFollowPlayerStateLocal(clientNum, &ps) )
              {
                MSG_WriteBit1(msg);

		MSG_TestDeltaPS(&snapInfo, svsHeader.time, NULL, &ps);

                MSG_WriteDeltaPlayerstate(&snapInfo, msg, svsHeader.time, NULL, &ps);
#ifdef CODOL_SERVER
                CODOL_PlayerStateExtWriteClient(msg, clientNum, NULL);
#endif
              }
              else
              {
                MSG_WriteBit0(msg);
              }
              ++clientNum;
            }
          }
          else
          {
            ++clientNum;
          }
        }
/*
        if ( GetCurrentThreadId() == (_DWORD)g_DXDeviceThread && 0 == dword_A8402BC )
        {
          D3DPERF_EndEvent();
        }
*/
	MSG_WriteBit0(msg);
        MSG_ClearLastReferencedEntity(msg);

#ifndef NDEBUG
	    MSG_WriteLong(msg, 0xdeadbee9);
        lastEntityNum = -1;
#endif

        //PIXBeginNamedEvent(3158271, "entities");
        for ( e = 0; e < svsHeader.num_entities; ++e )
        {
          gent = SV_GentityNumLocal(e);
          if ( gent->r.linked )
          {
            assertx ( gent->s.number == e, "entnum: %d vs %d, eType: %d, origin: %f %f %f", gent->s.number, e, gent->s.eType, gent->r.currentOrigin[0], gent->r.currentOrigin[1], gent->r.currentOrigin[2]);

	    if ( gent->r.broadcastTime /*|| gent->s.clientLinkInfo.flags & 1*/
		 || ( !(gent->r.svFlags & 1) &&
	    (gent->r.svFlags & 0x18 || svsHeader.svEntities[gent->s.number].numClusters))
	    /* && !(gent->r.svFlags & 0x80)*/
	    )
            {
              baseline = &svsHeader.svEntities[gent->s.number].baseline;
              assert( baseline );
              memcpy(&to.s, &gent->s, sizeof(entityState_t));
              to.r.svFlags = gent->r.svFlags;
              if ( gent->r.broadcastTime )
              {
                to.r.svFlags |= 8u;
              }
	      to.r.clientMask[0] = gent->r.clientMask[0];
	      to.r.clientMask[1] = gent->r.clientMask[1];
	      VectorCopy(gent->r.absmin, to.r.absmin);
	      VectorCopy(gent->r.absmax, to.r.absmax);
          snapInfo.fromBaseline = 1;

#ifndef NDEBUG
	      assertx(lastEntityNum != gent->s.number, "lastEntityNum is %i, cur entnum is %i", lastEntityNum, gent->s.number);
	      MSG_WriteLong(msg, 0xdeadbee7);
#endif

	      MSG_TestDeltaAE(&snapInfo, svsHeader.time, baseline, &to, msg->lastRefEntity);

              if ( MSG_WriteDeltaArchivedEntity(&snapInfo, msg, svsHeader.time, baseline, &to, entityArchiveFlags) )
              {
                ++svsHeader.archivedEntityCount;
              }
#ifdef CODOL_SERVER
              /* The serialized state is the live entity; its epoch is written
               * beside it, absolute against the entity baseline. */
              CODOL_EntityStateExtWriteEntity(msg, (unsigned)gent->s.number, NULL);
#endif
              snapInfo.fromBaseline = 0;
#ifndef NDEBUG
              lastEntityNum = gent->s.number;
#endif
            }
          }
	}
	/*
        if ( GetCurrentThreadId() == (_DWORD)g_DXDeviceThread && 0 == dword_A8402BC )
        {
          D3DPERF_EndEvent();
	}
	*/
        goto skipDelta;
      }
      break;
    }
  }


  //PIXBeginNamedEvent(3158271, "write delta");
  MSG_WriteBit1(msg);
#ifndef NDEBUG
  MSG_WriteLong(msg, 0xdeadbee1);
#endif
  MSG_WriteLong(msg, svsHeader.time);
//  MSG_WriteLong(msg, svsHeader.physicsTime);
  MSG_ClearLastReferencedEntity(msg);
  cachedSnap = &svsHeader.cachedSnapshotFrames[svsHeader.nextCachedSnapshotFrames % 512];
  svsHeader.cachedSnapshotFrames[svsHeader.nextCachedSnapshotFrames % 512].archivedFrame = svsHeader.nextArchivedSnapshotFrames;
//  cachedSnap->matchState = svsHeader.nextCachedSnapshotMatchStates;
  cachedSnap->num_entities = 0;
  cachedSnap->first_entity = svsHeader.nextCachedSnapshotEntities;
  cachedSnap->num_clients = 0;
  cachedSnap->first_client = svsHeader.nextCachedSnapshotClients;
  cachedSnap->usesDelta = 0;
  cachedSnap->time = svsHeader.time;
  //cachedSnap->physicsTime = svsHeader.physicsTime;
  MSG_ClearLastReferencedEntity(msg);
/*
  matchState = &svsHeader.cachedSnapshotMatchStates[svsHeader.nextCachedSnapshotMatchStates
                                                  % svsHeader.numCachedSnapshotMatchStates];
  memcpy(matchState, G_GetMatchStateLocal(), sizeof(MatchState));
  MSG_WriteDeltaMatchState(v1, &snapInfo, msg, svsHeader.time, 0, matchState);
  if ( ++svsHeader.nextCachedSnapshotMatchStates >= 0x7FFFFFFE )
  {
    Com_Error(ERR_FATAL, "svsHeader.nextCachedSnapshotMatchStates wrapped");
  }
  MSG_ClearLastReferencedEntity(msg);
*/


  for ( i = 0, client = svsHeader.clients; i < svsHeader.maxclients; ++i, ++client)
  {
    if ( client->state >= CS_PRIMED )
    {
      cachedCl = &svsHeader.cachedSnapshotClients[svsHeader.nextCachedSnapshotClients
                                                % svsHeader.numCachedSnapshotClients];
      lcs = G_GetClientStateLocal(i);

      memcpy(&cachedCl->cs, lcs, sizeof(cachedCl->cs));

      MSG_TestDeltaCS(&snapInfo, svsHeader.time, NULL, &cachedCl->cs);

      MSG_WriteDeltaClient(&snapInfo, msg, svsHeader.time, 0, &cachedCl->cs, 1);
#ifdef CODOL_SERVER
      CODOL_WriteArchivedClientAbilities(msg, i, &cachedCl->cs);
#endif
      cachedCl->playerStateExists = GetFollowPlayerStateLocal(i, &cachedCl->ps);
#ifdef CODOL_SERVER
      /* The archive slot takes the magnitude armed on that client right now;
       * the weapFlags half already rode the playerState copy. */
      if ( cachedCl->playerStateExists ) CODOL_PlayerStateExtCopyFromClient(&cachedCl->ps, i);
      else CODOL_PlayerStateExtClear(&cachedCl->ps);
#endif
      if ( cachedCl->playerStateExists )
      {
        MSG_WriteBit1(msg);

	MSG_TestDeltaPS(&snapInfo, svsHeader.time, NULL, &cachedCl->ps);

        MSG_WriteDeltaPlayerstate(&snapInfo, msg, svsHeader.time, NULL, &cachedCl->ps);
#ifdef CODOL_SERVER
        CODOL_PlayerStateExtWriteState(msg, &cachedCl->ps, NULL);
#endif
      }
      else
      {
        MSG_WriteBit0(msg);
      }
      if ( ++svsHeader.nextCachedSnapshotClients >= 0x7FFFFFFE )
      {
        Com_Error(ERR_FATAL, "svsHeader.nextCachedSnapshotClients wrapped");
      }
      ++cachedSnap->num_clients;
    }
  }


  MSG_WriteBit0(msg);

#ifndef NDEBUG
	      MSG_WriteLong(msg, 0xdeadbee9);
#endif

  MSG_ClearLastReferencedEntity(msg);
  for ( e = 0; e < svsHeader.num_entities; ++e )
  {
    gent = SV_GentityNumLocal(e);
    if ( gent->r.linked )
    {
      assertx ( gent->s.number == e, "entnum: %d vs %d, eType: %d, origin: %f %f %f", gent->s.number, e, gent->s.eType, gent->r.currentOrigin[0], gent->r.currentOrigin[1], gent->r.currentOrigin[2] );

      if ( gent->r.broadcastTime
	/* || gent->s.clientLinkInfo.flags & 1*/
	|| (!(gent->r.svFlags & 1)
        && (gent->r.svFlags & 0x18 || svsHeader.svEntities[gent->s.number].numClusters))
        /*&& !(gent->r.svFlags & 0x80)*/ )
      {
	baseline = &svsHeader.svEntities[gent->s.number].baseline;
	
	assert(baseline);

        archEnt = &svsHeader.cachedSnapshotEntities[svsHeader.nextCachedSnapshotEntities % svsHeader.numCachedSnapshotEntities];
        memcpy(archEnt, gent, sizeof(svsHeader.cachedSnapshotEntities[0]));
#ifdef CODOL_SERVER
        CODOL_EntityStateExtCopy(&archEnt->s, &gent->s);
#endif
        archEnt->r.svFlags = gent->r.svFlags;
        if ( gent->r.broadcastTime )
        {
          archEnt->r.svFlags |= 8u;
        }
        archEnt->r.clientMask[0] = gent->r.clientMask[0];
        archEnt->r.clientMask[1] = gent->r.clientMask[1];

	VectorCopy(gent->r.absmax, archEnt->r.absmax);
	VectorCopy(gent->r.absmin, archEnt->r.absmin);
	
        snapInfo.fromBaseline = 1;

#ifndef NDEBUG
        MSG_WriteLong(msg, 0xdeadbee7);
#endif
	MSG_TestDeltaAE(&snapInfo, svsHeader.time, baseline, archEnt, msg->lastRefEntity);

        MSG_WriteDeltaArchivedEntity(&snapInfo, msg, svsHeader.time, baseline, archEnt, entityArchiveFlags);
#ifdef CODOL_SERVER
        /* One record per archived entity, against the same baseline the
         * entity delta used - the entity baseline, which carries no epoch. */
        CODOL_EntityStateExtWrite(msg, &archEnt->s, NULL);
#endif
        ++svsHeader.archivedEntityCount;
        snapInfo.fromBaseline = 0;
        if ( ++svsHeader.nextCachedSnapshotEntities >= 0x7FFFFFFE )
        {
          Com_Error(ERR_FATAL, "svsHeader.nextCachedSnapshotEntities wrapped");
        }
        ++cachedSnap->num_entities;
      }
    }
  }

  if ( ++svsHeader.nextCachedSnapshotFrames >= 0x7FFFFFFE )
  {
    Com_Error(ERR_FATAL, "svsHeader.nextCachedSnapshotFrames wrapped");
  }
/*
  if ( GetCurrentThreadId() == (_DWORD)g_DXDeviceThread && 0 == dword_A8402BC )
  {
    D3DPERF_EndEvent();
  }
*/
skipDelta:
#ifdef CODOL_SERVER
  /* Both full and delta archives reach this point. Capture under the frame
   * being written, not only when a new full cached snapshot was allocated. */
  CODOL_ArchiveSnapshotActors(svsHeader.nextArchivedSnapshotFrames, svsHeader.time);
  CODOL_ActorDeliveryArchive(svsHeader.nextArchivedSnapshotFrames, svsHeader.time);
#endif
#ifndef NDEBUG
        MSG_WriteLong(msg, 0xdeadbee7);
#endif

  MSG_WriteEntityIndex(&snapInfo, msg, ENTITYNUM_NONE, GENTITYNUM_BITS);
}

bool SV_FrameIsStillInArchivedSnapshotBuffer(const int frameStart)
{
  int bufferStart;

  assert(frameStart >= 0);
  bufferStart = svs.nextArchivedSnapshotBuffer - ARCHIVEDSSBUF_SIZE;
  if ( svs.nextArchivedSnapshotBuffer - ARCHIVEDSSBUF_SIZE >= 0 )
  {
    return frameStart >= bufferStart && frameStart < svs.nextArchivedSnapshotBuffer;
  }
  if ( frameStart >= svs.nextArchivedSnapshotBuffer )
  {
    return frameStart >= bufferStart + 0x28000000;
  }
  return true;
}


cachedSnapshot_t* SV_GetCachedSnapshotInternal(int archivedFrame, int depth, bool expectedToSucceed)
{
  int startIndex;
  archivedSnapshot_t *frame;
  signed int oldArchivedFrame;
  int newnum;
  int oldindex;
  signed int oldnum;
  msg_t msg;
  cachedSnapshot_t *cachedFrame;
  cachedClient_t *oldCachedClient;
  int partSize;
  int firstCachedSnapshotFrame;
  int i;
  cachedSnapshot_t *oldCachedFrame;
  cachedClient_t *cachedClient;

  frame = &svs.archivedSnapshotFrames[archivedFrame % NUM_ARCHIVED_FRAMES];
  assertx(frame->size, "(archivedFrame) = %i", archivedFrame);

  if ( !SV_FrameIsStillInArchivedSnapshotBuffer(frame->start) )
  {
    if ( expectedToSucceed && svs.nextArchivedSnapshotErrorTime < svs.time)
    {
      Com_Printf(CON_CHANNEL_SERVER, "Failed to get archived snapshot for archived frame %i - frame->start is too old - %i < %i - %i\n",
        archivedFrame, frame->start, svs.nextArchivedSnapshotBuffer, ARCHIVEDSSBUF_SIZE);
      svs.nextArchivedSnapshotErrorTime = svs.time + 1000;
    }
    return 0;
  }
  firstCachedSnapshotFrame = svs.nextCachedSnapshotFrames - 512;
  if ( svs.nextCachedSnapshotFrames - 512 < 0 )
  {
    firstCachedSnapshotFrame = 0;
  }
  for ( i = svs.nextCachedSnapshotFrames - 1; i >= firstCachedSnapshotFrame; --i )
  {
    cachedFrame = &svs.cachedSnapshotFrames[i % 512];
    if ( cachedFrame->archivedFrame == archivedFrame )
    {
      assertx(cachedFrame->first_entity >= 0, "(cachedFrame->first_entity) = %i", cachedFrame->first_entity);

      if (/* cachedFrame->matchState > depth + svs.nextCachedSnapshotMatchStates - svs.numCachedSnapshotMatchStates
	&& */
	cachedFrame->first_entity > 160 * depth + svs.nextCachedSnapshotEntities - svs.numCachedSnapshotEntities
        && cachedFrame->first_client > 32 * depth + svs.nextCachedSnapshotClients - svs.numCachedSnapshotClients )
      {
        return cachedFrame;
      }
      break;
    }
  }
  startIndex = frame->start % ARCHIVEDSSBUF_SIZE;
  partSize = ARCHIVEDSSBUF_SIZE - startIndex;
  if ( frame->size > partSize )
  {
    MSG_InitReadOnlySplit( &msg, &svs.archivedSnapshotBuffer[startIndex], partSize, &svs.archivedSnapshotBuffer[0], frame->size - partSize);
  }
  else
  {
    MSG_InitReadOnly(&msg, &svs.archivedSnapshotBuffer[startIndex], frame->size);
  }
  MSG_BeginReading(&msg);

  assert(MSG_ReadLong(&msg) == 0xdeadbeef);

  if ( MSG_ReadBit(&msg) )
  {
    assert ( !msg.overflowed );
    assert(MSG_ReadLong(&msg) == 0xdeadbee1);

    cachedFrame = &svs.cachedSnapshotFrames[svs.nextCachedSnapshotFrames % 512];
    cachedFrame->archivedFrame = archivedFrame;
 //   cachedFrame->matchState = svs.nextCachedSnapshotMatchStates;
    cachedFrame->num_entities = 0;
    cachedFrame->first_entity = svs.nextCachedSnapshotEntities;
    cachedFrame->num_clients = 0;
    cachedFrame->first_client = svs.nextCachedSnapshotClients;
    cachedFrame->usesDelta = 0;
    cachedFrame->time = MSG_ReadLong(&msg);
//    cachedFrame->physicsTime = MSG_ReadLong(&msg);
    
    MSG_ClearLastReferencedEntity(&msg);
/*
    MSG_ReadDeltaMatchState(&msg, cachedFrame->time, 0, &svs.cachedSnapshotMatchStates[svs.nextCachedSnapshotMatchStates % svs.numCachedSnapshotMatchStates]);
    
    ++svs.nextCachedSnapshotMatchStates;
    
    MSG_ClearLastReferencedEntity(&msg);
*/
    while ( MSG_ReadBit(&msg) )
    {
      newnum = MSG_ReadEntityIndex(&msg, 6);
      if ( msg.overflowed )
      {
        Com_Error(ERR_DROP, "SV_GetCachedSnapshot: end of message");
      }

      cachedClient = &svs.cachedSnapshotClients[svs.nextCachedSnapshotClients % svs.numCachedSnapshotClients];
      MSG_ReadDeltaClient(&msg, cachedFrame->time, 0, &svs.cachedSnapshotClients[svs.nextCachedSnapshotClients % svs.numCachedSnapshotClients].cs, newnum);
#ifdef CODOL_SERVER
      CODOL_ReadArchivedClientAbilities(&msg, &cachedClient->cs);
#endif
      cachedClient->playerStateExists = MSG_ReadBit(&msg);
      if ( cachedClient->playerStateExists )
      {
        MSG_ReadDeltaPlayerstate(0, &msg, cachedFrame->time, 0, &cachedClient->ps, 0);
#ifdef CODOL_SERVER
        /* Rebuilt from the archive stream, including the extension record
         * that was written next to this playerState. */
        CODOL_PlayerStateExtReadState(&msg, &cachedClient->ps, NULL);
#endif
      }
#ifdef CODOL_SERVER
      else
      {
        CODOL_PlayerStateExtClear(&cachedClient->ps);
      }
#endif

      assert ( !svsHeaderValid );

      if ( ++svs.nextCachedSnapshotClients >= 0x7FFFFFFE )
      {
        Com_Error(ERR_FATAL, "svs.nextCachedSnapshotClients wrapped");
      }
      ++cachedFrame->num_clients;
    }

    assert(MSG_ReadLong(&msg) == 0xdeadbee9);

    MSG_ClearLastReferencedEntity(&msg);

    while ( 1 )
    {
      assert(MSG_ReadLong(&msg) == 0xdeadbee7);

      newnum = MSG_ReadEntityIndex(&msg, GENTITYNUM_BITS);
      if ( newnum == ENTITYNUM_NONE )
      {
        break;
      }
      if ( msg.overflowed )
      {
        Com_Error(ERR_DROP, "SV_GetCachedSnapshot: end of message");
      }

      MSG_ReadDeltaArchivedEntity( &msg, cachedFrame->time, &sv.svEntities[newnum].baseline,
	&svs.cachedSnapshotEntities[svs.nextCachedSnapshotEntities % svs.numCachedSnapshotEntities], newnum);
#ifdef CODOL_SERVER
      CODOL_EntityStateExtRead(&msg,
        &svs.cachedSnapshotEntities[svs.nextCachedSnapshotEntities % svs.numCachedSnapshotEntities].s, NULL);
#endif

      if ( ++svs.nextCachedSnapshotEntities >= 0x7FFFFFFE )
      {
        Com_Error(ERR_FATAL, "svs.nextCachedSnapshotEntities wrapped");
      }
      ++cachedFrame->num_entities;
    }
    if ( ++svs.nextCachedSnapshotFrames >= 0x7FFFFFFE )
    {
      Com_Error(ERR_FATAL, "svs.nextCachedSnapshotFrames wrapped");
    }
  }
  else
  {
    assert ( !msg.overflowed );
    assert(MSG_ReadLong(&msg) == 0xdeadbee0);

    oldArchivedFrame = MSG_ReadLong(&msg);
    if ( oldArchivedFrame < svs.nextArchivedSnapshotFrames - NUM_ARCHIVED_FRAMES )
    {
      if ( expectedToSucceed && svs.nextArchivedSnapshotErrorTime < svs.time )
      {
        Com_Printf(CON_CHANNEL_SERVER, "getting archive snapshot failed for time %i - oldArchiveFrame(%i) < svs.nextArchivedSnapshotFrames(%i) - NUM_ARCHIVED_FRAMES(%i)\n",
          archivedFrame, oldArchivedFrame, svs.nextArchivedSnapshotFrames, NUM_ARCHIVED_FRAMES);
        svs.nextArchivedSnapshotErrorTime = svs.time + 1000;
      }
      return 0;
    }
    frame = &svs.archivedSnapshotFrames[oldArchivedFrame % NUM_ARCHIVED_FRAMES];
    if ( !SV_FrameIsStillInArchivedSnapshotBuffer(frame->start) )
    {
      if ( expectedToSucceed && svs.nextArchivedSnapshotErrorTime < svs.time )
      {
	Com_Printf(CON_CHANNEL_SERVER, "getting archive snapshot failed for time %i - frame->start(%i) < svs.nextArchivedSnapshotBuffer(%i) - ARCHIVEDSSBUF_SIZE(%i)\n",
	  archivedFrame, frame->start, svs.nextArchivedSnapshotBuffer, ARCHIVEDSSBUF_SIZE);
        svs.nextArchivedSnapshotErrorTime = svs.time + 1000;
      }
      return 0;
    }
    oldCachedFrame = SV_GetCachedSnapshotInternal(oldArchivedFrame, depth + 1, expectedToSucceed);
    if ( !oldCachedFrame )
    {
      if ( expectedToSucceed && svs.nextArchivedSnapshotErrorTime < svs.time )
      {
        Com_Printf(CON_CHANNEL_SERVER, "failed to get snapshot for time %i - it was delta'd off time %i, and we couldn't get that snapshot\n",
          archivedFrame, oldArchivedFrame);
        svs.nextArchivedSnapshotErrorTime = svs.time + 1000;
      }
      return 0;
    }

    assert(!oldCachedFrame->usesDelta);

    cachedFrame = &svs.cachedSnapshotFrames[svs.nextCachedSnapshotFrames % 512];
    cachedFrame->archivedFrame = archivedFrame;
//    cachedFrame->matchState = svs.nextCachedSnapshotMatchStates;
    cachedFrame->num_entities = 0;
    cachedFrame->first_entity = svs.nextCachedSnapshotEntities;
    cachedFrame->num_clients = 0;
    cachedFrame->first_client = svs.nextCachedSnapshotClients;
    cachedFrame->usesDelta = 1;
    cachedFrame->time = MSG_ReadLong(&msg);
//    cachedFrame->physicsTime = MSG_ReadLong(&msg);
    MSG_ClearLastReferencedEntity(&msg);
/*	
    MSG_ReadDeltaMatchState( &msg, cachedFrame->time, 
      &svs.cachedSnapshotMatchStates[oldCachedFrame->matchState % svs.numCachedSnapshotMatchStates],
      &svs.cachedSnapshotMatchStates[svs.nextCachedSnapshotMatchStates % svs.numCachedSnapshotMatchStates]);

    ++svs.nextCachedSnapshotMatchStates;
*/
    MSG_ClearLastReferencedEntity(&msg);
    oldindex = 0;
    oldCachedClient = 0;
    if ( oldCachedFrame->num_clients > 0 )
    {
      oldCachedClient = &svs.cachedSnapshotClients[oldCachedFrame->first_client % svs.numCachedSnapshotClients];
      oldnum = oldCachedClient->cs.clientIndex;
    }
    else
    {
      oldnum = 99999;
    }
    while ( MSG_ReadBit(&msg) )
    {
      newnum = MSG_ReadEntityIndex(&msg, 6);

      assert(newnum >= 0);

      if ( msg.overflowed )
      {
        Com_Error(ERR_DROP, "SV_GetCachedSnapshot: end of message");
      }
      while ( oldnum < newnum )
      {
        if ( ++oldindex < oldCachedFrame->num_clients )
        {
          oldCachedClient = &svs.cachedSnapshotClients[(oldindex + oldCachedFrame->first_client)
                                                     % svs.numCachedSnapshotClients];
          oldnum = oldCachedClient->cs.clientIndex;
        }
        else
        {
          oldnum = 99999;
        }
      }
      if ( oldnum == newnum )
      {
        cachedClient = &svs.cachedSnapshotClients[svs.nextCachedSnapshotClients % svs.numCachedSnapshotClients];
	assert(cachedClient != oldCachedClient);		


        MSG_ReadDeltaClient(&msg, cachedFrame->time, &oldCachedClient->cs, &cachedClient->cs, newnum);
#ifdef CODOL_SERVER
        CODOL_ReadArchivedClientAbilities(&msg, &cachedClient->cs);
#endif
        cachedClient->playerStateExists = MSG_ReadBit(&msg);
        if ( cachedClient->playerStateExists )
        {
          if ( oldCachedClient->playerStateExists )
          {
            MSG_ReadDeltaPlayerstate(0, &msg, cachedFrame->time, &oldCachedClient->ps, &cachedClient->ps, 0);
#ifdef CODOL_SERVER
            /* Same baseline for both halves of the state. */
            CODOL_PlayerStateExtReadState(&msg, &cachedClient->ps, &oldCachedClient->ps);
#endif
          }
          else
          {
            MSG_ReadDeltaPlayerstate(0, &msg, cachedFrame->time, 0, &cachedClient->ps, 0);
#ifdef CODOL_SERVER
            CODOL_PlayerStateExtReadState(&msg, &cachedClient->ps, NULL);
#endif
          }
        }
#ifdef CODOL_SERVER
        else
        {
          CODOL_PlayerStateExtClear(&cachedClient->ps);
        }
#endif
	assert(!svsHeaderValid);
        if ( ++svs.nextCachedSnapshotClients >= 0x7FFFFFFE )
        {
          Com_Error(ERR_FATAL, "svs.nextCachedSnapshotClients wrapped");
        }
        ++cachedFrame->num_clients;
        if ( ++oldindex < oldCachedFrame->num_clients )
        {
          oldCachedClient = &svs.cachedSnapshotClients[(oldindex + oldCachedFrame->first_client) % svs.numCachedSnapshotClients];
          oldnum = oldCachedClient->cs.clientIndex;
        }
        else
        {
          oldnum = 99999;
        }
      }
      else
      {
	assert(oldnum > newnum);
        cachedClient = &svs.cachedSnapshotClients[svs.nextCachedSnapshotClients % svs.numCachedSnapshotClients];

        MSG_ReadDeltaClient(&msg, cachedFrame->time, 0, &svs.cachedSnapshotClients[svs.nextCachedSnapshotClients % svs.numCachedSnapshotClients].cs, newnum);
#ifdef CODOL_SERVER
        CODOL_ReadArchivedClientAbilities(&msg, &cachedClient->cs);
#endif
        cachedClient->playerStateExists = MSG_ReadBit(&msg);
        if ( cachedClient->playerStateExists )
        {
          MSG_ReadDeltaPlayerstate(0, &msg, cachedFrame->time, 0, &cachedClient->ps, 0);
#ifdef CODOL_SERVER
          CODOL_PlayerStateExtReadState(&msg, &cachedClient->ps, NULL);
#endif
        }
#ifdef CODOL_SERVER
        else
        {
          CODOL_PlayerStateExtClear(&cachedClient->ps);
        }
#endif

	assert( !svsHeaderValid );

	if ( ++svs.nextCachedSnapshotClients >= 0x7FFFFFFE )
        {
          Com_Error(ERR_FATAL, "svs.nextCachedSnapshotClients wrapped");
        }
        ++cachedFrame->num_clients;
      }
    }

    assert(MSG_ReadLong(&msg) == 0xdeadbee9);

    MSG_ClearLastReferencedEntity(&msg);

    while ( 1 )
    {
      assert(MSG_ReadLong(&msg) == 0xdeadbee7);

      newnum = MSG_ReadEntityIndex(&msg, GENTITYNUM_BITS);
      if ( newnum == ENTITYNUM_NONE )
      {
        break;
      }
      if ( msg.overflowed )
      {
        Com_Error(ERR_DROP, "SV_GetCachedSnapshot: end of message");
      }

      MSG_ReadDeltaArchivedEntity(
        &msg, cachedFrame->time, &sv.svEntities[newnum].baseline,
        &svs.cachedSnapshotEntities[svs.nextCachedSnapshotEntities % svs.numCachedSnapshotEntities], newnum);
#ifdef CODOL_SERVER
      CODOL_EntityStateExtRead(&msg,
        &svs.cachedSnapshotEntities[svs.nextCachedSnapshotEntities % svs.numCachedSnapshotEntities].s, NULL);
#endif
      if ( ++svs.nextCachedSnapshotEntities >= 0x7FFFFFFE )
      {
        Com_Error(ERR_FATAL, "svs.nextCachedSnapshotEntities wrapped");
      }
      ++cachedFrame->num_entities;
    }
    if ( ++svs.nextCachedSnapshotFrames >= 0x7FFFFFFE )
    {
      Com_Error(ERR_FATAL, "svs.nextCachedSnapshotFrames wrapped");
    }

  }
  assertx(cachedFrame->num_entities < svs.numCachedSnapshotEntities, "(cachedFrame->num_entities) = %i", cachedFrame->num_entities);
  assertx(cachedFrame->num_clients < svs.numCachedSnapshotClients, "(cachedFrame->num_clients) = %i", cachedFrame->num_clients);
//  assert(cachedFrame->matchState >= svs.nextCachedSnapshotMatchStates - svs.numCachedSnapshotMatchStates);
  assert(cachedFrame->first_entity >= svs.nextCachedSnapshotEntities - svs.numCachedSnapshotEntities);
  assert(cachedFrame->first_client >= svs.nextCachedSnapshotClients - svs.numCachedSnapshotClients);
  return cachedFrame;
}



int SV_GetCurrentClientInfo(int clientNum, playerState_t *ps, clientState_t *cs)
{
    assert(clientNum < sv_maxclients->integer);

  if ( svs.clients[clientNum].state == CS_ACTIVE )
  {
    if ( GetFollowPlayerState(clientNum, ps) )
    {
      memcpy(cs, G_GetClientState(clientNum), sizeof(clientState_t));
      return 1;
    }
  }
  return 0;
}




/* ext is the caller's half of the playerState bundle: it receives the CoDOL
 * extension belonging to the playerState this call delivers - the archived
 * one in the cached-snapshot arm, the live one in the current-info arm - so a
 * caller that copies the state onward can carry both halves explicitly.
 * Callers that only inspect the result pass NULL. */
int SV_GetArchivedClientInfo(int clientNum, int *pArchiveTime, playerState_t *ps, clientState_t *cs, float *origin, int *health, int *otherFlags, codol_ps_ext_t *ext)
{
  cachedSnapshot_t *cachedSnapshot;
  unsigned int i;
  int offsettime;
  cachedClient_t *cachedClient;
    playerState_t backupPs;

    assert(health);
    assert(otherFlags);

  cachedSnapshot = SV_GetCachedSnapshot(pArchiveTime);
#ifdef CODOL_SERVER
  /* No state delivered means no magnitude; every early return below keeps
   * this value. */
  CODOL_PlayerStateExtFetch(ext, NULL);
#endif
  if ( cachedSnapshot )
  {
	assert(*pArchiveTime > 0);
    offsettime = svs.time - cachedSnapshot->time;
    cachedClient = 0;
    for ( i = 0; ; ++i )
    {
      if ( i >= cachedSnapshot->num_clients )
      {
        return 0;
      }
      cachedClient = &svs.cachedSnapshotClients[(i + cachedSnapshot->first_client) % svs.numCachedSnapshotClients];
      if ( cachedClient->cs.clientIndex == clientNum )
      {
        break;
      }
    }
    if ( !cachedClient->playerStateExists )
    {
      return 0;
    }

	assert(cachedClient);
	assert(cachedClient->ps.otherFlags & POF_PLAYER);

    if ( origin )
    {
	    VectorCopy(cachedClient->ps.origin, origin);
    }
    if ( cs )
    {
      Com_Memcpy(cs, &cachedClient->cs, sizeof(clientState_t));
    }
    *health = cachedClient->ps.stats[0];
    *otherFlags = cachedClient->ps.otherFlags;
    if ( ps )
    {
      Com_Memcpy(ps, &cachedClient->ps, sizeof(playerState_t));
#ifdef CODOL_SERVER
      /* The archived magnitude that belongs to this archived playerState. */
      CODOL_PlayerStateExtFetch(ext, &cachedClient->ps);
#endif
      if ( ps->commandTime )
      {
        ps->commandTime += offsettime;
      }
#ifndef CODOL_SERVER
      if ( ps->pm_time )
      {
        ps->pm_time += offsettime;
      }
#else
      /* pm_time is a remaining duration, unlike commandTime/jumpTime.
       * Jump_ApplySlowdown seeds 1200 or JUMP_LAND_SLOWDOWN_TIME and
       * Jump_GetLandFactor consumes that duration. Preserve the archived
       * value; adding the playback delay extends the movement restriction. */
#endif
      if ( ps->foliageSoundTime )
      {
        ps->foliageSoundTime += offsettime;
      }
      if ( ps->jumpTime )
      {
        ps->jumpTime += offsettime;
      }
      if ( ps->viewHeightLerpTime )
      {
        ps->viewHeightLerpTime += offsettime;
      }
      if ( ps->shellshockTime )
      {
        ps->shellshockTime += offsettime;
      }
#ifdef CODOL_SERVER
      /* C1 PM_GetSprintLeft40f5c3..40f5e5 compares the captured sprint
       * start/end and subtracts the current command time. Move these clocks
       * with commandTime; leave the max-length duration and zero (never
       * sprinted) sentinel intact. Use wrapping arithmetic for time words. */
      if ( ps->sprintState.lastSprintStart )
      {
        ps->sprintState.lastSprintStart = (int)((uint32_t)ps->sprintState.lastSprintStart +
                                               (uint32_t)offsettime);
      }
      if ( ps->sprintState.lastSprintEnd )
      {
        ps->sprintState.lastSprintEnd = (int)((uint32_t)ps->sprintState.lastSprintEnd +
                                             (uint32_t)offsettime);
      }
#endif
      for ( i = 0; i < 0x1F && ps->hud.archival[i].type; ++i )
      {
        if ( ps->hud.archival[i].time )
        {
          ps->hud.archival[i].time += offsettime;
        }
        if ( ps->hud.archival[i].fadeStartTime )
        {
		    ps->hud.archival[i].fadeStartTime += offsettime;
		    assertx(ps->hud.archival[i].fadeStartTime <= svs.time, "%i, %i", ps->hud.archival[i].fadeStartTime, svs.time);
        }
        if ( ps->hud.archival[i].scaleStartTime )
        {
          ps->hud.archival[i].scaleStartTime += offsettime;
        }
        if ( ps->hud.archival[i].moveStartTime )
        {
          ps->hud.archival[i].moveStartTime += offsettime;
        }
      }
      ps->deltaTime += offsettime;
    }
    return 1;
  }
  if ( !ps )
  {
      ps = &backupPs;
  }
  if ( *pArchiveTime <= 0 && SV_GetCurrentClientInfo(clientNum, ps, cs) )
  {
#ifdef CODOL_SERVER
      /* Live follow: the state came straight from that client, so does the
       * magnitude. */
      CODOL_PlayerStateExtFetchFromClient(ext, clientNum);
#endif
      *health = ps->stats[0];
      *otherFlags = ps->otherFlags;
      if ( origin )
      {
		VectorCopy(ps->origin, origin);
      }
      return 1;
  }
  return 0;
}
