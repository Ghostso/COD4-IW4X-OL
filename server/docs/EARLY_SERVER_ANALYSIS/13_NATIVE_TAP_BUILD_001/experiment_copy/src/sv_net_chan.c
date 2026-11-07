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
#include "netchan.h"
#include "server.h"

#include <string.h>
#include <stdlib.h>
#ifdef CODOL_SERVER
#include "codol_wire.h"
#endif


/*
==============
SV_Netchan_Decode

	// first 12 bytes of the data are always:
	long serverId;
	long messageAcknowledge;
	long reliableAcknowledge;

==============
*/
void SV_Netchan_Decode( client_t *client, byte *data, int remaining ) {
#ifdef CODOL_SERVER
    if (remaining > 0)
        CODOL_Xor(data, remaining,
            client->challenge ^ (byte)client->serverId ^ client->messageAcknowledge,
            (const byte *)client->reliableCommands[
                client->reliableAcknowledge & (MAX_RELIABLE_COMMANDS - 1)].command,
            MAX_STRING_CHARS);
    return;
#endif

	int i, index;
	byte key, *string;
//	extclient_t *extcl = &svs.extclients[ client - svs.clients ];
	
//	string = (byte *)extcl->reliableCommands[ client->reliableAcknowledge & ( MAX_RELIABLE_COMMANDS - 1 ) ].command;
	string = (byte *)client->reliableCommands[ client->reliableAcknowledge & ( MAX_RELIABLE_COMMANDS - 1 ) ].command;

	if(!remaining) return;
	key = client->challenge ^ (byte)client->serverId ^ client->messageAcknowledge;

	for ( i=0, index=0; i < remaining; i++ ) {

		if ( !string[index] ) {
			index = 0;
		}

		// modify the key with the last sent and acknowledged server command
		key ^= string[index] << ( i & 1 );
		data[i] ^= key;

		index++;
	}

}

/*
==============
SV_Netchan_Encode

	// first four bytes of the data are always:
	long reliableAcknowledge;

==============
*/

void SV_Netchan_Encode( client_t *client, byte *data, int cursize ) {
#ifdef CODOL_SERVER
    if (cursize > 4)
        CODOL_Xor(data + 4, cursize - 4,
            client->challenge ^ client->netchan.outgoingSequence,
            (const byte *)client->lastClientCommandString,
            sizeof(client->lastClientCommandString));
    return;
#endif

	int i, index;
	byte key, *string;

	string = (byte *)client->lastClientCommandString;
	key = client->challenge ^ client->netchan.outgoingSequence;

	for ( i = 0, index = 0; i < cursize - 4; i++ ) {

		if ( !string[index] ) {
			index = 0;
		}

		// modify the key with the last sent and acknowledged server command
		key ^= string[index] << ( i & 1 );
		data[i+4] ^= key;

		index++;
	}

}


/*
===============
SV_Netchan_Transmit

TTimo
show_bug.cgi?id=462
if there are some unsent fragments (which may happen if the snapshots
and the gamestate are fragmenting, and collide on send for instance)
then buffer them and make sure they get sent in correct order
================
*/
qboolean SV_Netchan_Transmit( client_t *client, byte *data, int cursize) {   //int length, const byte *data ) {
	qboolean nt_ret;
	int i;
#ifdef CODOL_SERVER
    byte *encoded;
    if (!data || cursize < 4 || cursize > NETCHAN_UNSENTBUFFER_SIZE) return qfalse;
    encoded = malloc((size_t)cursize);
    if (!encoded) return qfalse;
    memcpy(encoded, data, (size_t)cursize);
    SV_Netchan_Encode(client, encoded, cursize);
    nt_ret = CODOL_NetchanSubmit(&client->netchan, cursize, encoded);
    /* Submit sends synchronously or owns a fragment copy. Keep the caller's
     * plaintext intact for snapshot-history validation and rejected retries. */
    free(encoded);
    if (!nt_ret) return qfalse;
#else

//	SV_DumpCommands(client, (byte*)data, cursize, qfalse);

	if(cursize - 4){
		SV_Netchan_Encode(client, data, cursize);
	}
	nt_ret = Netchan_Transmit( &client->netchan, cursize, data );
#endif
	if(client->netchan.unsentFragments){
		return nt_ret;
	}

	i = client->netchan.outgoingSequence & 31;

	Com_Memset(&client->frames[i], 0, sizeof(clientSnapshot_t));

	client->frames[i].first_entity = svs.nextSnapshotEntities;
	client->frames[i].first_client = svs.nextSnapshotClients;

	return nt_ret;
}


/*
===============
SV_Netchan_TransmitNextFragment

TTimo
show_bug.cgi?id=462
if there are some unsent fragments (which may happen if the snapshots
and the gamestate are fragmenting, and collide on send for instance)
then buffer them and make sure they get sent in correct order
================
*/
__cdecl qboolean SV_Netchan_TransmitNextFragment( client_t *client ) {   //int length, const byte *data ) {
	int i;

	Netchan_TransmitNextFragment( &client->netchan );

	if(client->netchan.unsentFragments)
		return qtrue; //Return true if we have still unsent fragments
	
	i = client->netchan.outgoingSequence & 31;

	Com_Memset(&client->frames[i], 0, sizeof(clientSnapshot_t));

	client->frames[i].first_entity = svs.nextSnapshotEntities;
	client->frames[i].first_client = svs.nextSnapshotClients;

	return qfalse; //No more unsent fragments, this was the last fragment
}
