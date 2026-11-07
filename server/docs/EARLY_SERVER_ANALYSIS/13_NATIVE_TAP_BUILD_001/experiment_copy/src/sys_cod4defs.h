/*
===========================================================================
    Copyright (C) 2010-2013  Ninja and TheKelm

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



#ifndef __SYS_COD4DEFS_H__
#define __SYS_COD4DEFS_H__


#ifdef CODOL_SERVER
#define EXECUTABLE_NAME "codol_dedrun"
#define PRODUCT_NAME "Call of Duty Online Closed Alpha Server"
#define CLIENT_WINDOW_TITLE "sh1x server - Call of Duty Online Closed Alpha Server"
#define CLIENT_WINDOW_MIN_TITLE "sh1x server"
#else
#define EXECUTABLE_NAME "iw4ol_dedrun"

#define PRODUCT_NAME				"Call of Duty 4 - Modern Warfare Dedicated Server"
#define CLIENT_WINDOW_TITLE     	"Call of Duty 4 - Modern Warfare Dedicated Server"
#define CLIENT_WINDOW_MIN_TITLE 	"CoD4 MW"
#endif
#define BASEGAME "main"

#define PORT_MASTER 20810
#define MASTER_SERVER_NAME "cod4master.activision.com"

#define HEARTBEAT_GAME "COD-4"
#define HEARTBEAT_DEAD "flatline"

#define PRODUCT_VERSION "1.0"

#define Q3_VERSION "-"

#ifdef CODOL_SERVER
#define GAME_STRING "sh1x server - Call of Duty Online Closed Alpha Server"
#else
#define GAME_STRING "CoD4 X"
#endif

#include "version/version.h"

#define MAX_CLIENTS 64
//#define MAX_CONFIGSTRINGS 2*2442
#define MAX_CONFIGSTRINGS 4883
// Configstrings limits.
#define MAX_LOCATIONSELECTORS  3
#define MAX_STATUSICONS        8
#define MAX_HEADICONS          15
#define MAX_SHOCKS             16
#define MAX_TAGS               32
#define MAX_MENUS              32
#define MAX_FX                 100
#define MAX_SOUNDS             256
#define MAX_FXONTAGS           256
#define MAX_MATERIALS          256
#define MAX_LOCALIZEDSTRINGS   512
#define MAX_MODELS             512
#ifdef CODOL_SERVER
/* Native model slots. C1's G_ModelIndex (0x570400) allows 2048 (cmp esi,0x800
 * at 0x570431/0x570456, CS 1315+i). Slots 1..511 stay in the IW3
 * configstrings at CS_MODELS (the ranges after it are laid out from
 * MAX_MODELS, so MAX_MODELS itself cannot grow); 512..2047 are held by
 * codol_sv_assets.c. cached_models is sized for all of them. */
#define CODOL_NATIVE_MODELS    2048
#endif

// Configstrings types offsets.
#define CS_LOCALIZEDSTRINGS   309
#define CS_LOCATIONSELECTORS  827
#define CS_MODELS             (CS_LOCATIONSELECTORS + MAX_LOCATIONSELECTORS)
#define CS_SOUNDS             (CS_MODELS + MAX_MODELS)
#define CS_FX                 (CS_SOUNDS + MAX_SOUNDS)
#define CS_FXONTAGS           (CS_FX + MAX_FX)
#define CS_SHOCKS             (CS_FXONTAGS + MAX_FXONTAGS)
#define CS_MENUS              (CS_SHOCKS + MAX_SHOCKS)
#define CS_MATERIALS          (CS_MENUS + MAX_MENUS)
#define CS_STATUSICONS        2259
#define CS_HEADICONS          (CS_STATUSICONS + MAX_STATUSICONS)
#define CS_TAGS               (CS_HEADICONS + MAX_HEADICONS)

#endif
