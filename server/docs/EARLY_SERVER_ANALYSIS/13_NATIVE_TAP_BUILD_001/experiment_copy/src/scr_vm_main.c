#ifdef CODOL_SERVER
#include "codol_actor_scripts.h"
#include "codol_script_objectives.h"
#endif
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

#include "q_shared.h"
#ifdef CODOL_SERVER
#include "codol_remote_vehicle_script.h"
#include "codol_rc_lifecycle.h"
#include "codol_obituary.h"
#include "codol_script_anim.h"
#endif
#ifdef CODOL_SERVER
#include "codol_script_radar.h"
#include "codol_action_slots.h"
#include "codol_killstreak_hud.h"
#include "codol_radar_types.h"
#include "codol_equipment_support.h"
#include "codol_script_appearance.h"
#include "codol_script_model_scale.h"
#include "codol_script_precompile.h"
#include "codol_sv_state.h"
#include "codol_script_native_batch2.h"
#include "codol_script_native_batch3.h"
#include "codol_script_light.h"
#include "codol_script_minimap.h"
#include "codol_script_sound.h"
#include "codol_spectate_defaults.h"
#include "codol_script_startup_extra.h"
#include "codol_script_model_animation.h"
#include "codol_model_animation.h"
#include "codol_script_profiler.h"
#include "codol_script_rank_experience.h"
#include "codol_script_precache.h"
#include "codol_script_combat_builtins.h"
#include "codol_script_client_material.h"
#include "codol_script_contents.h"
#include "codol_script_vehicle_builtins.h"
/* codol_actor_lifecycle.cpp: resolves CodeCallback_ActorDamage/ActorKilled. */
void CODOL_ActorDamage_LoadCallbacks(void);
#include "codol_script_player_builtins.h"
#include "codol_script_missing_next.h"
#include "codol_script_turret_target.h"
#include "codol_script_turret_placement.h"
#include "codol_script_thermal_material.h"
#include "codol_profile_skill.h"
#include "codol_script_glass.h"
#include "codol_script_magicbullet.h"
#include "codol_location_selection.h"
#include "codol_spawn_artillery.h"
#include "codol_rc_placement_trace.h"
#include "codol_rc_spawn_influence.h"
#include "codol_bomb.h"
#include "codol_script_slowmotion.h"
#include "codol_script_entity_fx.h"
#include "codol_script_offhand_primary.h"
#include "codol_vehicle_spawner.h"
#endif
#include "scr_vm.h"
#ifdef CODOL_SERVER
#include "codol_map_shadow.h"
#endif
#include "codol_script_childthread.h"
#include "scr_vm_functions.h"
#include "qcommon_io.h"
#include "cvar.h"
#include "cmd.h"
#include "misc.h"
#include "sys_main.h"
#include "sv_bots.h"
#ifdef CODOL_SERVER
#include "codol_bot.h"
#endif
//#include "scr_vm_classfunc.h"
#include "stringed_interface.h"
#include "cscr_stringlist.h"
#include "cscr_variable.h"
#include "cscr_animtree.h"
#include "cscr_parser.h"

#include <stdarg.h>
#include <ctype.h>

typedef struct
{
    char *name;
    xfunction_t offset;
    qboolean developer;
} v_function_t;


void __cdecl GScr_AddFieldsForEntity();


void Scr_AddStockFunctions()
{
	Scr_AddFunction("createprintchannel", GScr_CreatePrintChannel, 1 );
	Scr_AddFunction("setprintchannel", GScr_printChannelSet, 1 );
	Scr_AddFunction("print", print, 0 );
	Scr_AddFunction("println", println, 1 );
	/* println is DEVELOPER-only: with developer 0 the compiler discards the
	 * whole statement (EmitCall, _scr_compiler.asm), so none of the script
	 * tree's println diagnostics exist in a production build, and
	 * RuntimeError is silent there too.  codolprintln is the always-on
	 * counterpart for stage reporting that must survive a production boot. */
	Scr_AddFunction("codolprintln", GScr_CoDOLPrintLn, 0 );
	Scr_AddFunction("iprintln", iprintln, 0 );
	Scr_AddFunction("iprintlnbold", iprintlnbold, 0 );
	Scr_AddFunction("print3d", GScr_Print3D, 1 );
	Scr_AddFunction("printstar", GScr_PrintDebugStar, 1 );
	Scr_AddFunction("line", GScr_line, 1 );
	Scr_AddFunction("getent", Scr_GetEnt, 0 );
	Scr_AddFunction("getentarray", Scr_GetEntArray, 0 );
	Scr_AddFunction("spawnplane", GScr_SpawnPlane, 0 );
	Scr_AddFunction("spawnturret", GScr_SpawnTurret, 0 );
	Scr_AddFunction("precacheturret", GScr_PrecacheTurret, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("canspawnturret", CODOL_Scr_CanSpawnTurret, 0 );
	Scr_AddFunction("setthermalbodymaterial", CODOL_Scr_SetThermalBodyMaterial, 0 );
	Scr_AddFunction("updateskill", CODOL_Scr_UpdateSkill, 0 );
	Scr_AddFunction("getglass", CODOL_Scr_GetGlass, 0 );
	Scr_AddFunction("getglassarray", CODOL_Scr_GetGlassArray, 0 );
    Scr_AddFunction("getglassorigin", CODOL_Scr_GetGlassOrigin, 0);
    Scr_AddFunction("isglassdestroyed", CODOL_Scr_IsGlassDestroyed, 0);
    Scr_AddFunction("destroyglass", CODOL_Scr_DestroyGlass, 0);
    Scr_AddFunction("deleteglass", CODOL_Scr_DeleteGlass, 0);
#endif
	Scr_AddFunction("spawnstruct", Scr_AddStruct, 0 );
	Scr_AddFunction("assert", assertCmd, 1 );
	Scr_AddFunction("assertex", assertexCmd, 1 );
	Scr_AddFunction("assertmsg", assertmsgCmd, 1 );
	Scr_AddFunction("isdefined", GScr_IsDefined, 0 );
	Scr_AddFunction("isstring", GScr_IsString, 0 );
	Scr_AddFunction("isalive", GScr_IsAlive, 0 );
	Scr_AddFunction("gettime", GScr_GetTime, 0 );
	Scr_AddFunction("getentbynum", Scr_GetEntByNum, 0 );
	Scr_AddFunction("getweaponmodel", Scr_GetWeaponModel, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("getweaponhidetags", CODOL_Scr_GetWeaponHideTags, 0);
    Scr_AddFunction("getweaponflashtagname", CODOL_Scr_GetWeaponFlashTagName, 0);
    Scr_AddFunction("getweaponscriptmods", CODOL_Scr_GetWeaponScriptMods, 0);
    Scr_AddFunction("weaponhasthermalscope", CODOL_Scr_WeaponHasThermalScope, 0);
    Scr_AddFunction("codol_weaponhasgps", CODOL_Scr_WeaponHasGPS, 0);
    Scr_AddFunction("codol_weaponhasidlock", CODOL_Scr_WeaponHasIDLock, 0);
    Scr_AddFunction("codol_weaponhashpbt", CODOL_Scr_WeaponHasHPBT, 0);
#endif
	Scr_AddFunction("getanimlength", GScr_GetAnimLength, 0 );
	Scr_AddFunction("animhasnotetrack", GScr_AnimHasNotetrack, 0 );
	Scr_AddFunction("getnotetracktimes", GScr_GetNotetrackTimes, 0 );
	Scr_AddFunction("getbrushmodelcenter", GScr_GetBrushModelCenter, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_add", CODOL_Scr_Objective_Add, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_add", Scr_Objective_Add, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_delete", CODOL_Scr_Objective_Delete, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_delete", Scr_Objective_Delete, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_state", CODOL_Scr_Objective_State, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_state", Scr_Objective_State, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_icon", CODOL_Scr_Objective_Icon, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_icon", Scr_Objective_Icon, 0 );
#endif
	Scr_AddFunction("float", GScr_Float, 0); // like int(...) but to convert to floating point number.
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_position", CODOL_Scr_Objective_Position, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_position", Scr_Objective_Position, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_onentity", CODOL_Scr_Objective_OnEntity, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_onentity", Scr_Objective_OnEntity, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_current", CODOL_Scr_Objective_Current, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_current", Scr_Objective_Current, 0 );
#endif
	Scr_AddFunction("missile_createattractorent", Scr_MissileCreateAttractorEnt, 0 );
	Scr_AddFunction("missile_createattractororigin", Scr_MissileCreateAttractorOrigin, 0 );
	Scr_AddFunction("missile_createrepulsorent", Scr_MissileCreateRepulsorEnt, 0 );
	Scr_AddFunction("missile_createrepulsororigin", Scr_MissileCreateRepulsorOrigin, 0 );
	Scr_AddFunction("missile_deleteattractor", Scr_MissileDeleteAttractor, 0 );
	Scr_AddFunction("bullettrace", Scr_BulletTrace, 0 );
	Scr_AddFunction("bullettracepassed", Scr_BulletTracePassed, 0 );
	Scr_AddFunction("sighttracepassed", Scr_SightTracePassed, 0 );
	Scr_AddFunction("physicstrace", Scr_PhysicsTrace, 0 );
	Scr_AddFunction("playerphysicstrace", Scr_PlayerPhysicsTrace, 0 );
	Scr_AddFunction("getmovedelta", GScr_GetMoveDelta, 0 );
	Scr_AddFunction("getangledelta", GScr_GetAngleDelta, 0 );
	Scr_AddFunction("getnorthyaw", GScr_GetNorthYaw, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("setnorthyaw", CODOL_Scr_SetNorthYaw, 0);
#endif
	Scr_AddFunction("randomint", Scr_RandomInt, 0 );
	Scr_AddFunction("randomfloat", Scr_RandomFloat, 0 );
	Scr_AddFunction("randomintrange", Scr_RandomIntRange, 0 );
	Scr_AddFunction("randomfloatrange", Scr_RandomFloatRange, 0 );
	Scr_AddFunction("sin", GScr_sin, 0 );
	Scr_AddFunction("cos", GScr_cos, 0 );
	Scr_AddFunction("tan", GScr_tan, 0 );
	Scr_AddFunction("asin", GScr_asin, 0 );
	Scr_AddFunction("acos", GScr_acos, 0 );
	Scr_AddFunction("atan", GScr_atan, 0 );
	Scr_AddFunction("int", GScr_CastInt, 0 );
	Scr_AddFunction("abs", GScr_abs, 0 );
	Scr_AddFunction("min", GScr_min, 0 );
	Scr_AddFunction("max", GScr_max, 0 );
	Scr_AddFunction("floor", GScr_floor, 0 );
	Scr_AddFunction("ceil", GScr_ceil, 0 );
	Scr_AddFunction("sqrt", GScr_sqrt, 0 );
	Scr_AddFunction("vectorfromlinetopoint", GScr_VectorFromLineToPoint, 0 );
	Scr_AddFunction("pointonsegmentnearesttopoint", GScr_PointOnSegmentNearestToPoint, 0 );
	Scr_AddFunction("isweapondetonationtimed",GScr_IsWeaponDetonationTimed, 0);
	Scr_AddFunction("distance", Scr_Distance, 0 );
	Scr_AddFunction("distance2d", Scr_Distance2D, 0 );
	Scr_AddFunction("distancesquared", Scr_DistanceSquared, 0 );
	Scr_AddFunction("length", Scr_Length, 0 );
	Scr_AddFunction("lengthsquared", Scr_LengthSquared, 0 );
	Scr_AddFunction("closer", Scr_Closer, 0 );
	Scr_AddFunction("vectordot", Scr_VectorDot, 0 );
	Scr_AddFunction("vectornormalize", Scr_VectorNormalize, 0 );
	Scr_AddFunction("vectortoangles", Scr_VectorToAngles, 0 );
	Scr_AddFunction("vectorlerp", Scr_VectorLerp, 0 );
	Scr_AddFunction("anglestoup", Scr_AnglesToUp, 0 );
	Scr_AddFunction("anglestoright", Scr_AnglesToRight, 0 );
	Scr_AddFunction("anglestoforward", Scr_AnglesToForward, 0 );
	Scr_AddFunction("combineangles", Scr_CombineAngles, 0 );
	Scr_AddFunction("issubstr", Scr_IsSubStr, 0 );
	Scr_AddFunction("getsubstr", Scr_GetSubStr, 0 );
	Scr_AddFunction("tolower", Scr_ToLower, 0 );
	Scr_AddFunction("strtok", Scr_StrTok, 0 );
	Scr_AddFunction("musicplay", Scr_MusicPlay, 0 );
	Scr_AddFunction("musicstop", Scr_MusicStop, 0 );
	Scr_AddFunction("soundfade", Scr_SoundFade, 0 );
	Scr_AddFunction("ambientplay", Scr_AmbientPlay, 0 );
	Scr_AddFunction("ambientstop", Scr_AmbientStop, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("setac130ambience", CODOL_Scr_SetAC130Ambience, 0);
#endif
	Scr_AddFunction("precachemodel", Scr_PrecacheModel, 0 );
	Scr_AddFunction("precacheshellshock", Scr_PrecacheShellShock, 0 );
	Scr_AddFunction("precacheitem", CODOL_Scr_PrecacheItem, 0 );
	Scr_AddFunction("precacheshader", Scr_PrecacheShader, 0 );
	//Scr_AddFunction("precachestring", Scr_PrecacheString, 0 );
	Scr_AddFunction("precacherumble", Scr_PrecacheRumble, 0 );
	Scr_AddFunction("loadfx", Scr_LoadFX, 0 );
	Scr_AddFunction("playfx", Scr_PlayFX, 0 );
	Scr_AddFunction("playfxontag", Scr_PlayFXOnTag, 0 );
	Scr_AddFunction("playloopedfx", Scr_PlayLoopedFX, 0 );
	Scr_AddFunction("spawnfx", Scr_SpawnFX, 0 );
	Scr_AddFunction("triggerfx", Scr_TriggerFX, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("physicsexplosionsphere", CODOL_Scr_PhysicsExplosionSphere, 0 );
#else
	Scr_AddFunction("physicsexplosionsphere", Scr_PhysicsExplosionSphere, 0 );
#endif
	Scr_AddFunction("physicsexplosioncylinder", Scr_PhysicsExplosionCylinder, 0 );
	Scr_AddFunction("physicsjolt", Scr_PhysicsRadiusJolt, 0 );
	Scr_AddFunction("physicsjitter", Scr_PhysicsRadiusJitter, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("precachevehicle", CODOL_Scr_PrecacheVehicle, 0 );
	Scr_AddFunction("setexpfog", CODOL_Scr_SetExponentialFog, 0 );
#else
	Scr_AddFunction("setexpfog", Scr_SetExponentialFog, 0 );
#endif
	Scr_AddFunction("grenadeexplosioneffect", Scr_GrenadeExplosionEffect, 0 );
	Scr_AddFunction("radiusdamage", GScr_RadiusDamage, 0 );
	Scr_AddFunction("setplayerignoreradiusdamage", GScr_SetPlayerIgnoreRadiusDamage, 0 );
	Scr_AddFunction("getnumparts", GScr_GetNumParts, 0 );
	Scr_AddFunction("getpartname", GScr_GetPartName, 0 );
	Scr_AddFunction("earthquake", GScr_Earthquake, 0 );
	Scr_AddFunction("newteamhudelem", GScr_NewTeamHudElem, 0 );
	Scr_AddFunction("resettimeout", Scr_ResetTimeout, 0 );
	Scr_AddFunction("weaponfiretime", GScr_WeaponFireTime, 0 );
	Scr_AddFunction("isweaponcliponly", GScr_IsWeaponClipOnly, 0 );
	Scr_AddFunction("weaponclipsize", GScr_WeaponClipSize, 0 );
	Scr_AddFunction("weaponissemiauto", GScr_WeaponIsSemiAuto, 0 );
	Scr_AddFunction("weaponisboltaction", GScr_WeaponIsBoltAction, 0 );
	Scr_AddFunction("weapontype", GScr_WeaponType, 0 );
	Scr_AddFunction("weaponclass", GScr_WeaponClass, 0 );
	Scr_AddFunction("weaponinventorytype", GScr_WeaponInventoryType, 0 );
	Scr_AddFunction("weaponstartammo", GScr_WeaponStartAmmo, 0 );
	Scr_AddFunction("weaponmaxammo", GScr_WeaponMaxAmmo, 0 );
	Scr_AddFunction("weaponaltweaponname", GScr_WeaponAltWeaponName, 0 );
	Scr_AddFunction("isplayer", GScr_IsPlayer, 0 );
	Scr_AddFunction("isplayernumber", GScr_IsPlayerNumber, 0 );
	Scr_AddFunction("setwinningplayer", GScr_SetWinningPlayer, 0 );
	Scr_AddFunction("setwinningteam", GScr_SetWinningTeam, 0 );
	Scr_AddFunction("announcement", GScr_Announcement, 0 );
	Scr_AddFunction("clientannouncement", GScr_ClientAnnouncement, 0 );
	Scr_AddFunction("getteamscore", GScr_GetTeamScore, 0 );
	Scr_AddFunction("setteamscore", GScr_SetTeamScore, 0 );
	Scr_AddFunction("setclientnamemode", GScr_SetClientNameMode, 0 );
	Scr_AddFunction("updateclientnames", GScr_UpdateClientNames, 0 );
	Scr_AddFunction("getteamplayersalive", GScr_GetTeamPlayersAlive, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("objective_team", CODOL_Scr_Objective_Team, 0 ); /* 32 slots, C1 */
#else
	Scr_AddFunction("objective_team", GScr_Objective_Team, 0 );
#endif
	Scr_AddFunction("logprint", GScr_LogPrint, 0 );
	Scr_AddFunction("worldentnumber", GScr_WorldEntNumber, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("obituary", CODOL_GScr_Obituary, 0 );
#else
	Scr_AddFunction("obituary", GScr_Obituary, 0 );
#endif
	Scr_AddFunction("positionwouldtelefrag", GScr_positionWouldTelefrag, 0 );
	Scr_AddFunction("getstarttime", GScr_getStartTime, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("precachemenu", CODOL_Scr_PrecacheMenu, 0);
#else
	Scr_AddFunction("precachemenu", GScr_PrecacheMenu, 0 );
#endif
	Scr_AddFunction("precachestatusicon", GScr_PrecacheStatusIcon, 0 );
	Scr_AddFunction("precacheheadicon", GScr_PrecacheHeadIcon, 0 );
	Scr_AddFunction("precachelocationselector", GScr_PrecacheLocationSelector, 0 );
	Scr_AddFunction("map_restart", GScr_MapRestart, 0 );
	Scr_AddFunction("exitlevel", CODOL_Scr_ExitLevel, 0 );
	Scr_AddFunction("setarchive", GScr_SetArchive, 0 );
	Scr_AddFunction("allclientsprint", GScr_AllClientsPrint, 0 );
	Scr_AddFunction("clientprint", GScr_ClientPrint, 0 );
	Scr_AddFunction("mapexists", GScr_MapExists, 0 );
	Scr_AddFunction("isvalidgametype", GScr_IsValidGameType, 0 );
	Scr_AddFunction("matchend", GScr_MatchEnd, 0 );
	Scr_AddFunction("setplayerteamrank", GScr_SetPlayerTeamRank, 0 );
	Scr_AddFunction("sendranks", GScr_SendXboxLiveRanks, 0 );
	Scr_AddFunction("endparty", GScr_EndXboxLiveLobby, 0 );
	Scr_AddFunction("setteamradar", GScr_SetTeamRadar, 0 );
	Scr_AddFunction("getteamradar", GScr_GetTeamRadar, 0 );
#ifdef CODOL_SERVER
	Scr_AddFunction("setteamspyplane", CODOL_Scr_SetTeamSpyplane, 0);
	Scr_AddFunction("getteamspyplane", CODOL_Scr_GetTeamSpyplane, 0);
	Scr_AddFunction("setteamsatellite", CODOL_Scr_SetTeamSatellite, 0);
	Scr_AddFunction("getteamsatellite", CODOL_Scr_GetTeamSatellite, 0);
	Scr_AddFunction("blockteamradar", CODOL_Scr_BlockTeamRadar, 0);
	Scr_AddFunction("unblockteamradar", CODOL_Scr_UnblockTeamRadar, 0);
	Scr_AddFunction("isteamradarblocked", CODOL_Scr_IsTeamRadarBlocked, 0);
#endif
	Scr_AddFunction("getassignedteam", GScr_GetAssignedTeam, 0 );
	Scr_AddFunction("setvotestring", GScr_SetVoteString, 0 );
	Scr_AddFunction("setvotetime", GScr_SetVoteTime, 0 );
	Scr_AddFunction("setvoteyescount", GScr_SetVoteYesCount, 0 );
	Scr_AddFunction("setvotenocount", GScr_SetVoteNoCount, 0 );
	Scr_AddFunction("fprintfields", GScr_FPrintFields, 1 );
	Scr_AddFunction("fgetarg", GScr_FGetArg, 1 );
	//Scr_AddFunction("kick", GScr_KickPlayer, 0 );
	//Scr_AddFunction("ban", GScr_BanPlayer, 0 );
	Scr_AddFunction("map", GScr_LoadMap, 0 );
	Scr_AddFunction("playrumbleonposition", Scr_PlayRumbleOnPosition, 0 );
	Scr_AddFunction("playrumblelooponposition", Scr_PlayRumbleLoopOnPosition, 0 );
	Scr_AddFunction("stopallrumbles", Scr_StopAllRumbles, 0 );
	Scr_AddFunction("soundexists", ScrCmd_SoundExists, 0 );
	Scr_AddFunction("issplitscreen", Scr_IsSplitscreen, 0 );
	Scr_AddFunction("setminimap", GScr_SetMiniMap, 0 );
	Scr_AddFunction("setmapcenter", GScr_SetMapCenter, 0 );
	Scr_AddFunction("setgameendtime", GScr_SetGameEndTime, 0 );
	Scr_AddFunction("getarraykeys", GScr_GetArrayKeys, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("sortbydistance", CODOL_Scr_SortByDistance, 0);
    Scr_AddFunction("getgroundposition", CODOL_Scr_GetGroundPosition, 0);
    Scr_AddFunction("exp", CODOL_Scr_Exp, 0);
    Scr_AddFunction("log", CODOL_Scr_Log, 0);
    Scr_AddFunction("squared", CODOL_Scr_Squared, 0);
    Scr_AddFunction("clamp", CODOL_Scr_Clamp, 0);
    Scr_AddFunction("angleclamp", CODOL_Scr_AngleClamp, 0);
    Scr_AddFunction("vectortoyaw", CODOL_Scr_VectorToYaw, 0);
    Scr_AddFunction("transformmove", CODOL_Scr_TransformMove, 0);
    Scr_AddFunction("getfirstarraykey", CODOL_Scr_GetFirstArrayKey, 0);
    Scr_AddFunction("getnextarraykey", CODOL_Scr_GetNextArrayKey, 0);
    Scr_AddFunction("matrix4x4transformpoints", CODOL_Scr_Matrix4x4TransformPoints, 0);
    Scr_AddFunction("rotatepoint", CODOL_Scr_RotatePoint, 0);
    Scr_AddFunction("isvec", CODOL_Scr_IsVec, 0);
    Scr_AddFunction("lerpfloat", CODOL_Scr_LerpFloat, 0);
    Scr_AddFunction("lerpvector", CODOL_Scr_LerpVector, 0);
    Scr_AddFunction("vectorcross", CODOL_Scr_VectorCross, 0);
    Scr_AddFunction("absangleclamp180", CODOL_Scr_AbsAngleClamp180, 0);
    Scr_AddFunction("getmissileowner", CODOL_Scr_GetMissileOwner, 0);
    Scr_AddFunction("isexplosivedamagemod", CODOL_Scr_IsExplosiveDamageMod, 0);
#endif
	Scr_AddFunction("searchforonlinegames", GScr_SearchForOnlineGames, 0 );
	Scr_AddFunction("quitlobby", GScr_QuitLobby, 0 );
	Scr_AddFunction("quitparty", GScr_QuitParty, 0 );
	Scr_AddFunction("startparty", GScr_StartParty, 0 );
	Scr_AddFunction("startprivatematch", GScr_StartPrivateMatch, 0 );
#ifdef CODOL_SERVER
    /* The assembly wrappers publish IW3 configstrings 824/825, which are not
     * the vision sets a C1 client reads. The native producer publishes the
     * C1 range and adds the three types IW3 never had. */
    Scr_AddFunction("visionsetnaked", CODOL_Scr_VisionSetNaked, 0);
    Scr_AddFunction("visionsetnight", CODOL_Scr_VisionSetNight, 0);
    Scr_AddFunction("visionsetmissilecam", CODOL_Scr_VisionSetMissileCam, 0);
    Scr_AddFunction("visionsetthermal", CODOL_Scr_VisionSetThermal, 0);
    Scr_AddFunction("visionsetpain", CODOL_Scr_VisionSetPain, 0);
#else
	Scr_AddFunction("visionsetnaked", Scr_VisionSetNaked, 0 );
	Scr_AddFunction("visionsetnight", Scr_VisionSetNight, 0 );
#endif
	Scr_AddFunction("tablelookup", CODOL_Scr_TableLookup, 0 );
	Scr_AddFunction("tablelookupistring", Scr_TableLookupIString, 0 );
#ifdef CODOL_SERVER
    Scr_AddFunction("tablelookupbyrow", CODOL_Scr_TableLookupByRow, 0);
    Scr_AddFunction("tablelookupistringbyrow", CODOL_Scr_TableLookupByRow, 0);
    Scr_AddFunction("tablelookupcolumnforrow", CODOL_Scr_TableLookupByRow, 0);
    Scr_AddFunction("tablelookuprownum", CODOL_Scr_TableLookupRowNum, 0);
#endif
	Scr_AddFunction("endlobby", GScr_EndLobby, 0 );
	Scr_AddFunction("logstring", Scr_LogString, 0);

    //User edited functions
    Scr_AddFunction("spawn", GScr_Spawn, 0);
#ifdef CODOL_SERVER
    /* The legacy IW4OL GScr_SpawnVehicle body is commented out in
     * scr_vm_functions.c and used the old <origin>,<spawnflags>,<type>,<model>
     * argument order. CODOL_Scr_SpawnVehicle implements the actual IW4/C1
     * contract (model, targetname, vehicle definition, origin, angles),
     * selects the helicopter initializer for definition type 5 and the
     * retained SpawnVehicle otherwise, and installs the per-spawn
     * script_vehicle_collmap brush. It is the producer the RC-XD reward and
     * every other script-spawned vehicle need. */
    Scr_AddFunction("spawnvehicle", CODOL_Scr_SpawnVehicle, 0);
#endif
    Scr_AddFunction("spawnhelicopter", GScr_SpawnHelicopter, 0);
    Scr_AddFunction("getdvar", GScr_GetCvar, 0);
    Scr_AddFunction("getdvarint", GScr_GetCvarInt, 0);
    Scr_AddFunction("getdvarfloat", GScr_GetCvarFloat, 0);
    Scr_AddFunction("setdvar", GScr_SetCvar, 0);
#ifdef CODOL_SERVER
    Scr_AddFunction("setdevdvar", GScr_SetCvar, 0);
    Scr_AddFunction("angleclamp180", CODOL_Scr_AngleClamp180, 0);
    Scr_AddFunction("averagepoint", CODOL_Scr_AveragePoint, 0);
    Scr_AddFunction("averagenormal", CODOL_Scr_AverageNormal, 0);
    Scr_AddFunction("getplayers", CODOL_Scr_GetPlayers, 0);
    Scr_AddFunction("getclassperk", CODOL_Scr_GetClassPerk, 0);
    Scr_AddFunction("getmapcustom", CODOL_Scr_GetMapCustom, 0);
    Scr_AddFunction("precachefxteamthermal", CODOL_Scr_PrecacheFxTeamThermal, 0);
    Scr_AddFunction("getclassindex", CODOL_Scr_GetClassIndex, 0);
    Scr_AddFunction("setclientmatchdatadef", CODOL_Scr_SetClientMatchDataDef, 0);
    Scr_AddFunction("getclientmatchdatadef", CODOL_Scr_GetClientMatchDataDef, 0);
    Scr_AddFunction("setclientmatchdata", CODOL_Scr_SetClientMatchData, 0);
    Scr_AddFunction("getclientmatchdata", CODOL_Scr_GetClientMatchData, 0);
    Scr_AddFunction("sendclientmatchdata", CODOL_Scr_SendClientMatchData, 0);
    Scr_AddFunction("setmatchdatadef", CODOL_Scr_SetMatchDataDef, 0);
    Scr_AddFunction("setmatchdata", CODOL_Scr_SetMatchData, 0);
    Scr_AddFunction("getmatchdata", CODOL_Scr_GetMatchData, 0);
    Scr_AddFunction("clearmatchdata", CODOL_Scr_ClearMatchData, 0);
    Scr_AddFunction("weaponinheritsperks", CODOL_Scr_WeaponInheritsPerks, 0);
    Scr_AddFunction("getweaponmindamagerange", CODOL_Scr_GetWeaponMinDamageRange, 0);
    Scr_AddFunction("getweaponmaxdamagerange", CODOL_Scr_GetWeaponMaxDamageRange, 0);
    Scr_AddFunction("getweaponmindamage", CODOL_Scr_GetWeaponMinDamage, 0);
    Scr_AddFunction("getweaponmaxdamage", CODOL_Scr_GetWeaponMaxDamage, 0);
    Scr_AddFunction("weaponreloadtime", CODOL_Scr_WeaponReloadTime, 0);
    Scr_AddFunction("getweaponfusetime", CODOL_Scr_GetWeaponFuseTime, 0);
    Scr_AddFunction("codol_ispointinwater", CODOL_Scr_IsPointInWater, 0);
    Scr_AddFunction("weaponburstcount", CODOL_Scr_WeaponBurstCount, 0);
    Scr_AddFunction("weaponisauto", CODOL_Scr_WeaponIsAuto, 0);
    Scr_AddFunction("isweaponprimary", CODOL_Scr_IsWeaponPrimary, 0);
    Scr_AddFunction("getweaponindexfromname", CODOL_Scr_GetWeaponIndexFromName, 0);
    Scr_AddFunction("codol_weaponinventorytype", CODOL_Scr_WeaponInventoryTypeSafe, 0);
    Scr_AddFunction("codol_isweaponpublished", CODOL_Scr_IsWeaponPublished, 0);
    /* Find-only: unlike getweaponindexfromname this never registers a
     * definition, so a roster can ask whether a name is mounted without
     * burning a weapon slot on a defaultweapon_mp clone. */
    Scr_AddFunction("codol_isweaponmounted", CODOL_Scr_IsWeaponMounted, 0);
    Scr_AddFunction("codol_getweaponclass", CODOL_Scr_GetWeaponClassSafe, 0);
    Scr_AddFunction("magicbullet", CODOL_Scr_MagicBullet, 0);
    Scr_AddFunction("setslowmotion", CODOL_Scr_SetSlowMotion, 0);
    Scr_AddFunction("playfxontagforclients", CODOL_Scr_PlayFXOnTagForClients, 0);
    Scr_AddFunction("isspawner", CODOL_Scr_IsSpawner, 0);
    Scr_AddFunction("vehicle_getspawnerarray", CODOL_Scr_VehicleGetSpawnerArray, 0);
    Scr_AddFunction("getweaponarray", CODOL_Scr_GetWeaponArray, 0);
    Scr_AddFunction("getdroppedweapons", CODOL_Scr_GetWeaponArray, 0);
    Scr_AddFunction("getweaponfiresound", CODOL_Scr_GetWeaponFireSound, 0);
    Scr_AddFunction("getweaponfiresoundplayer", CODOL_Scr_GetWeaponFireSoundPlayer, 0);
    Scr_AddFunction("getweaponpickupsound", CODOL_Scr_GetWeaponPickupSound, 0);
    Scr_AddFunction("getweaponpickupsoundplayer", CODOL_Scr_GetWeaponPickupSoundPlayer, 0);
    Scr_AddFunction("getweaponprojexplosionsound", CODOL_Scr_GetWeaponProjExplosionSound, 0);
    Scr_AddFunction("isvehicle", CODOL_Scr_IsVehicle, 0);
    Scr_AddFunction("getnumvehicles", CODOL_Scr_GetNumVehicles, 0);
    Scr_AddFunction("getmaxvehicles", CODOL_Scr_GetMaxVehicles, 0);
    Scr_AddFunction("vehicle_getarray", CODOL_Scr_VehicleGetArray, 0);
    Scr_AddFunction("collisiontestpointsinsphere", CODOL_Scr_CollisionTestPointsInSphere, 0);
    Scr_AddFunction("collisiontestpointsincylinder", CODOL_Scr_CollisionTestPointsInCylinder, 0);
    Scr_AddFunction("collisiontestpointsinpill", CODOL_Scr_CollisionTestPointsInPill, 0);
    Scr_AddFunction("collisiontestpointsincone", CODOL_Scr_CollisionTestPointsInCone, 0);
    Scr_AddFunction("collisiontestpointsinbox", CODOL_Scr_CollisionTestPointsInBox, 0);
    Scr_AddFunction("qsortscoredspawnpointsascending", CODOL_Scr_QSortScoredSpawnPointsAscending, 0);
    Scr_AddFunction("canspawn", CODOL_Scr_CanSpawn, 0);
    Scr_AddFunction("spawnsighttrace", CODOL_Scr_SpawnSightTrace, 0);
    Scr_AddFunction("stopfxontag", CODOL_Scr_StopFxOnTag, 0);
    Scr_AddFunction("getsystemtime", CODOL_Scr_GetSystemTime, 0);
    Scr_AddFunction("getbuildnumber", CODOL_Scr_GetBuildNumber, 0);
    Scr_AddFunction("getbuildversion", CODOL_Scr_GetBuildVersion, 0);
    Scr_AddFunction("getvehiclenode", CODOL_Scr_GetVehicleNode, 0);
    Scr_AddFunction("getnode", CODOL_Scr_GetNode, 0);
    Scr_AddFunction("getnodearray", CODOL_Scr_GetNodeArray, 0);
    Scr_AddFunction("getallnodes", CODOL_Scr_GetAllPathNodes, 0);
    Scr_AddFunction("getvehiclenodearray", CODOL_Scr_GetVehicleNodeArray, 0);
    Scr_AddFunction("getallvehiclenodes", CODOL_Scr_GetAllVehicleNodes, 0);
    Scr_AddFunction("setdevdvarifuninitialized", CODOL_Scr_SetDevDvarIfUninitialized, 1);
    Scr_AddFunction("getdvarvector", CODOL_Scr_GetDvarVector, 0);
    Scr_AddFunction("getdvarcolorred", CODOL_Scr_GetDvarColorRed, 0);
    Scr_AddFunction("getdvarcolorgreen", CODOL_Scr_GetDvarColorGreen, 0);
    Scr_AddFunction("getdvarcolorblue", CODOL_Scr_GetDvarColorBlue, 0);
    Scr_AddFunction("setdvarifuninitialized", CODOL_Scr_SetDvarIfUninitialized, 0);
    Scr_AddFunction("codol_setmapsunsamplesize", CODOL_Scr_SetMapSunSampleSize, 0);
#endif
    Scr_AddFunction("vectoradd", GScr_VectorAdd, 0);
    Scr_AddFunction("precachestring", Scr_PrecacheString_f, 0);
    Scr_AddFunction("newhudelem", GScr_NewHudElem, 0);
    Scr_AddFunction("newclienthudelem", GScr_NewClientHudElem, 0);
    Scr_AddFunction("addtestclient", GScr_SpawnBot, 0);
    Scr_AddFunction("removetestclient", GScr_RemoveBot, 0);
    Scr_AddFunction("removealltestclients", GScr_RemoveAllBots, 0);
    Scr_AddFunction("makedvarserverinfo", GScr_MakeCvarServerInfo, 0);
    Scr_AddFunction("openfile", GScr_FS_FOpen, 0);
    Scr_AddFunction("closefile", GScr_FS_FClose, 0);
    Scr_AddFunction("fprintln", GScr_FS_WriteLine, 0);
    Scr_AddFunction("freadln", GScr_FS_ReadLine, 0);
    Scr_AddFunction("kick", GScr_KickClient, 0);
    Scr_AddFunction("ban", GScr_BanClient, 0);
    Scr_AddFunction("fs_fopen", GScr_FS_FOpen, 0);
    Scr_AddFunction("fs_fclose", GScr_FS_FClose, 0);
    Scr_AddFunction("fs_fcloseall", GScr_FS_FCloseAll, 0);
    Scr_AddFunction("fs_testfile", GScr_FS_TestFile, 0);
    Scr_AddFunction("fs_readline", GScr_FS_ReadLine, 0);
    Scr_AddFunction("fs_writeline", GScr_FS_WriteLine, 0);
    Scr_AddFunction("fs_remove", GScr_FS_Remove, 0);
    Scr_AddFunction("getrealtime", GScr_GetRealTime, 0);
    Scr_AddFunction("timetostring", GScr_TimeToString, 0);
    Scr_AddFunction("strtokbypixlen", GScr_StrTokByPixLen, 0);
    Scr_AddFunction("strpixlen", GScr_StrPixLen, 0);
    Scr_AddFunction("strcolorstrip", GScr_StrColorStrip, 0);
    Scr_AddFunction("strrepl", GScr_StrRepl, 0);
    Scr_AddFunction("strtokbylen", GScr_StrTokByLen, 0);
    Scr_AddFunction("exec", GScr_CbufAddText, 0);
    Scr_AddFunction("execex", GScr_CbufAddTextEx, 0);
    Scr_AddFunction("sha256", GScr_SHA256, 0);
    Scr_AddFunction("addscriptcommand", GScr_AddScriptCommand, 0);
    Scr_AddFunction("isarray", Scr_IsArray_f, qfalse); // http://zeroy.com/script/variables/isarray.htm
    Scr_AddFunction("iscvardefined", GScr_IsCvarDefined, 0);
    Scr_AddFunction("arraytest", GScr_ArrayTest, 1);

    Scr_AddFunction("base64encode", GScr_Base64Encode, 0);
    Scr_AddFunction("base64decode", GScr_Base64Decode, 0);
    Scr_AddFunction("isentity", GScr_IsEntity, 0);
    Scr_AddFunction("isvector", GScr_IsVector, 0);
    Scr_AddFunction("isfloat", GScr_IsFloat, 0);
    Scr_AddFunction("isint", GScr_IsInt, 0);
    Scr_AddFunction("pow", GScr_Pow, 0);
	Scr_AddFunction("strctrlstrip", GScr_StrCtrlStrip, 0 );
	Scr_AddFunction("toupper", GScr_ToUpper, 0 );
	Scr_AddFunction("strreplace", GScr_StrReplace, 0 );
    Scr_AddFunction("usercall", Scr_Usercall, 0);
}

void Scr_AddStockMethods()
{


    //PlayerCmd

    Scr_AddMethod("usercall", PlayerCmd_Usercall, 0);
	Scr_AddMethod("giveweapon", PlayerCmd_giveWeapon, 0 );
	Scr_AddMethod("takeweapon", PlayerCmd_takeWeapon, 0 );
	Scr_AddMethod("takeallweapons", PlayerCmd_takeAllWeapons, 0 );
	Scr_AddMethod("getcurrentweapon", PlayerCmd_getCurrentWeapon, 0 );
	Scr_AddMethod("getcurrentoffhand", PlayerCmd_getCurrentOffhand, 0 );
	Scr_AddMethod("getcurrentprimaryweapon", CODOL_Scr_GetCurrentPrimaryWeapon, 0 );
	Scr_AddMethod("getcurrentweaponclipammo", CODOL_Scr_GetCurrentWeaponClipAmmo, 0 );
	Scr_AddMethod("isswitchingweapon", CODOL_Scr_IsSwitchingWeapon, 0 );
	Scr_AddMethod("isreloading", CODOL_Scr_IsReloading, 0 );
	Scr_AddMethod("isdualwielding", CODOL_Scr_IsDualWielding, 0 );
	Scr_AddMethod("hasweapon", PlayerCmd_hasWeapon, 0 );
	Scr_AddMethod("switchtoweapon", PlayerCmd_switchToWeapon, 0 );
	Scr_AddMethod("switchtooffhand", PlayerCmd_switchToOffhand, 0 );
	Scr_AddMethod("givestartammo", PlayerCmd_giveStartAmmo, 0 );
	Scr_AddMethod("givemaxammo", PlayerCmd_giveMaxAmmo, 0 );
	Scr_AddMethod("getfractionstartammo", PlayerCmd_getFractionStartAmmo, 0 );
	Scr_AddMethod("getfractionmaxammo", PlayerCmd_getFractionMaxAmmo, 0 );
	Scr_AddMethod("setorigin", PlayerCmd_setOrigin, 0 );
	Scr_AddMethod("getvelocity", PlayerCmd_GetVelocity, 0 );
	Scr_AddMethod("setplayerangles", PlayerCmd_setAngles, 0 );
	Scr_AddMethod("getplayerangles", PlayerCmd_getAngles, 0 );
	Scr_AddMethod("usebuttonpressed", PlayerCmd_useButtonPressed, 0 );
	Scr_AddMethod("attackbuttonpressed", PlayerCmd_attackButtonPressed, 0 );
	Scr_AddMethod("meleebuttonpressed", PlayerCmd_meleeButtonPressed, 0 );
	Scr_AddMethod("fragbuttonpressed", PlayerCmd_fragButtonPressed, 0 );
	Scr_AddMethod("secondaryoffhandbuttonpressed", PlayerCmd_secondaryOffhandButtonPressed, 0 );
	Scr_AddMethod("playerads", PlayerCmd_playerADS, 0 );
	Scr_AddMethod("isonground", PlayerCmd_isOnGround, 0 );
	Scr_AddMethod("pingplayer", PlayerCmd_pingPlayer, 0 );
	Scr_AddMethod("setviewmodel", PlayerCmd_SetViewmodel, 0 );
	Scr_AddMethod("getviewmodel", PlayerCmd_GetViewmodel, 0 );
#ifdef CODOL_SERVER
	Scr_AddMethod("setoffhandsecondaryclass", CODOL_Scr_SetOffhandSecondaryClass, 0);
	Scr_AddMethod("getoffhandsecondaryclass", CODOL_Scr_GetOffhandSecondaryClass, 0);
#else
	Scr_AddMethod("setoffhandsecondaryclass", PlayerCmd_setOffhandSecondaryClass, 0 );
	Scr_AddMethod("getoffhandsecondaryclass", PlayerCmd_getOffhandSecondaryClass, 0 );
#endif
	Scr_AddMethod("beginlocationselection", CODOL_BeginLocationSelection, 0 );
	Scr_AddMethod("endlocationselection", CODOL_EndLocationSelection, 0 );
	Scr_AddMethod("codol_launchmortarbomb", CODOL_Scr_LaunchMortarBomb, 0 );
	Scr_AddMethod("launchbomb", CODOL_Scr_LaunchBomb, 0 );
    Scr_AddFunction("codol_getprojectilegravity", CODOL_Scr_GetProjectileGravity, 0);
	Scr_AddMethod("beginlocationmortarselection", CODOL_BeginLocationMortarSelection, 0 );
	Scr_AddMethod("buttonpressed", PlayerCmd_buttonPressedDEVONLY, 0 );
	Scr_AddMethod("sayall", PlayerCmd_SayAll, 0 );
	Scr_AddMethod("sayteam", PlayerCmd_SayTeam, 0 );
	Scr_AddMethod("showscoreboard", PlayerCmd_showScoreboard, 0 );
	Scr_AddMethod("setspawnweapon", PlayerCmd_setSpawnWeapon, 0 );
	Scr_AddMethod("dropitem", PlayerCmd_dropItem, 0 );
	Scr_AddMethod("finishplayerdamage", PlayerCmd_finishPlayerDamage, 0 );
	Scr_AddMethod("suicide", PlayerCmd_Suicide, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("openmenu", CODOL_Scr_OpenMenu, 0);
    Scr_AddMethod("openmenunomouse", CODOL_Scr_OpenMenuNoMouse, 0);
    Scr_AddMethod("closemenu", CODOL_Scr_CloseMenu, 0);
    Scr_AddMethod("closeingamemenu", CODOL_Scr_CloseInGameMenu, 0);
    Scr_AddMethod("openpopupmenu", CODOL_Scr_OpenPopupMenu, 0);
    Scr_AddMethod("isitemunlocked", CODOL_Scr_IsItemUnlocked, 0);
    Scr_AddMethod("codol_tryisitemunlocked", CODOL_Scr_TryIsItemUnlocked, 0);
    Scr_AddMethod("codol_trychallengestate", CODOL_Scr_TryChallengeState, 0);
    Scr_AddMethod("getplayerdata", CODOL_Scr_GetPlayerData, 0);
    Scr_AddMethod("getrankexperience", CODOL_Scr_GetRankExperience, 0);
    Scr_AddMethod("setrankexperience", CODOL_Scr_SetRankExperience, 0);
    Scr_AddMethod("getsecureplayerdata", CODOL_Scr_GetSecurePlayerData, 0);
    Scr_AddMethod("setplayerdata", CODOL_Scr_SetPlayerData, 0);
    /* Weapon XP for the lobby's match report; see codol_match_report.c. */
    Scr_AddMethod("codol_creditweaponxp", CODOL_Scr_CreditWeaponXP, 0);
    Scr_AddMethod("codol_getloadoutitem", CODOL_Scr_GetLoadoutItem, 0);
    Scr_AddMethod("setoffhandequipment", CODOL_Scr_SetOffhandEquipment, 0);
    /* The sentient "do not target" byte (C1 +0x18), which actor acquisition
     * already honours at codol_actor_lifecycle.cpp:331 and :649. The two
     * implementations have existed in codol_sentient.cpp since it was
     * written -- and even name themselves "setdonttarget" in their own
     * Scr_Error text -- but were never registered, so they were dead from
     * script. zm last stand needs them: self.ignoreme is a plain script
     * variable no native field reads, so without this a downed player is
     * still mobbed. T5 gets the same effect via is_player_valid(p, true)
     * inside find_flesh. */
    /* Declared locally: codol_sentient.h puts these in its extern "C"
     * arm, which is compiled only for C++ consumers, so this C file
     * cannot see them through the header. */
    { extern void CODOL_Scr_SetDontTarget(scr_entref_t);
      extern void CODOL_Scr_GetDontTarget(scr_entref_t);
      Scr_AddMethod("setdonttarget", CODOL_Scr_SetDontTarget, 0);
      Scr_AddMethod("getdonttarget", CODOL_Scr_GetDontTarget, 0); }
    Scr_AddMethod("setabilitymodifier", CODOL_Scr_SetAbilityModifier, 0);
    Scr_AddMethod("unsetabilitymodifier", CODOL_Scr_UnsetAbilityModifier, 0);
    Scr_AddMethod("hasabilitymodifier", CODOL_Scr_HasAbilityModifier, 0);
    Scr_AddMethod("clearabilitymodifiers", CODOL_Scr_ClearAbilityModifiers, 0);
    Scr_AddMethod("setabilitymodifiervalue", CODOL_Scr_SetAbilityModifierValue, 0);
    Scr_AddMethod("getselectedperkmodifiervalue", CODOL_Scr_GetSelectedPerkModifierValue, 0);
    Scr_AddMethod("getoffhandequipment", CODOL_Scr_GetOffhandEquipment, 0);
    Scr_AddMethod("codol_getloadoutperk", CODOL_Scr_GetLoadoutPerk, 0);
    Scr_AddMethod("codol_getloadoutkillstreak", CODOL_Scr_GetLoadoutKillstreak, 0);
    Scr_AddMethod("codol_getloadoutattachment", CODOL_Scr_GetLoadoutAttachment, 0);
    Scr_AddMethod("codol_getloadoutattachments", CODOL_Scr_GetLoadoutAttachments, 0);
    Scr_AddMethod("codol_getloadoutcamo", CODOL_Scr_GetLoadoutCamo, 0);
    Scr_AddMethod("codol_getloadoutweapon", CODOL_Scr_GetLoadoutWeapon, 0);
    Scr_AddMethod("codol_applyprofilecharacter", CODOL_Scr_ApplyProfileCharacter, 0);
    Scr_AddMethod("codol_getzombiecharacter", CODOL_Scr_GetZombieCharacter, 0);
    Scr_AddMethod("codol_getvoiceprefix", CODOL_Scr_GetVoicePrefix, 0);
    Scr_AddMethod("codol_getloadoutitemtype", CODOL_Scr_GetLoadoutItemType, 0);
    Scr_AddFunction("codol_getweaponbasename", CODOL_Scr_GetWeaponBaseName, 0);
    Scr_AddFunction("codol_getweaponattachmentnames", CODOL_Scr_GetWeaponAttachmentNames, 0);
    Scr_AddMethod("closepopupmenu", CODOL_Scr_ClosePopupMenu, 0);
#else
	Scr_AddMethod("openmenu", PlayerCmd_OpenMenu, 0 );
	Scr_AddMethod("openmenunomouse", PlayerCmd_OpenMenuNoMouse, 0 );
	Scr_AddMethod("closemenu", PlayerCmd_CloseMenu, 0 );
	Scr_AddMethod("closeingamemenu", PlayerCmd_CloseInGameMenu, 0 );
#endif
	Scr_AddMethod("freezecontrols", PlayerCmd_FreezeControls, 0 );
	Scr_AddMethod("disableweapons", PlayerCmd_DisableWeapons, 0 );
	Scr_AddMethod("enableweapons", PlayerCmd_EnableWeapons, 0 );
	Scr_AddMethod("setreverb", PlayerCmd_SetReverb, 0 );
	Scr_AddMethod("deactivatereverb", PlayerCmd_DeactivateReverb, 0 );
	Scr_AddMethod("setchannelvolumes", PlayerCmd_SetChannelVolumes, 0 );
	Scr_AddMethod("deactivatechannelvolumes", PlayerCmd_DeactivateChannelVolumes, 0 );
	Scr_AddMethod("setweaponammoclip", PlayerCmd_SetWeaponAmmoClip, 0 );
	Scr_AddMethod("setweaponammostock", PlayerCmd_SetWeaponAmmoStock, 0 );
	Scr_AddMethod("getweaponammoclip", PlayerCmd_GetWeaponAmmoClip, 0 );
	Scr_AddMethod("getweaponammostock", PlayerCmd_GetWeaponAmmoStock, 0 );
	Scr_AddMethod("anyammoforweaponmodes", PlayerCmd_AnyAmmoForWeaponModes, 0 );
	Scr_AddMethod("iprintln", iclientprintln, 0 );
	Scr_AddMethod("iprintlnbold", iclientprintlnbold, 0 );
	Scr_AddMethod("setentertime", PlayerCmd_setEnterTime, 0 );
	Scr_AddMethod("cloneplayer", PlayerCmd_ClonePlayer, 0 );
	Scr_AddMethod("setclientdvar", PlayerCmd_SetClientDvar, 0 );
	Scr_AddMethod("setclientdvars", PlayerCmd_SetClientDvars, 0 );
	Scr_AddMethod("playlocalsound", ScrCmd_PlayLocalSound, 0 );
	Scr_AddMethod("stoplocalsound", ScrCmd_StopLocalSound, 0 );
	Scr_AddMethod("istalking", PlayerCmd_IsTalking, 0 );
	Scr_AddMethod("allowspectateteam", PlayerCmd_AllowSpectateTeam, 0 );
	Scr_AddMethod("allowads", PlayerCmd_AllowADS, 0 );
	Scr_AddMethod("allowjump", PlayerCmd_AllowJump, 0 );
	Scr_AddMethod("allowsprint", PlayerCmd_AllowSprint, 0 );
	Scr_AddMethod("setspreadoverride", PlayerCmd_SetSpreadOverride, 0 );
	Scr_AddMethod("resetspreadoverride", PlayerCmd_ResetSpreadOverride, 0 );
#ifdef CODOL_SERVER
	Scr_AddMethod("setactionslot", CODOL_Scr_SetActionSlot, 0 );
	Scr_AddMethod("setkillstreak", CODOL_Scr_SetKillstreak, 0 );
	Scr_AddMethod("getkillstreak", CODOL_Scr_GetKillstreak, 0 );
	Scr_AddMethod("setkillstreakid", CODOL_Scr_SetKillstreakID, 0 );
	Scr_AddMethod("getkillstreakid", CODOL_Scr_GetKillstreakID, 0 );
	Scr_AddMethod("setkillstreaktarget", CODOL_Scr_SetKillstreakTarget, 0 );
	Scr_AddMethod("getkillstreaktarget", CODOL_Scr_GetKillstreakTarget, 0 );

#else
	Scr_AddMethod("setactionslot", PlayerCmd_SetActionSlot, 0 );
#endif
	Scr_AddMethod("getweaponslist", PlayerCmd_GetWeaponsList, 0 );
	Scr_AddMethod("getweaponslistprimaries", PlayerCmd_GetWeaponsListPrimaries, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("setperk", CODOL_Scr_SetPerk, 0);
    Scr_AddMethod("hasperk", CODOL_Scr_HasPerk, 0);
    Scr_AddMethod("clearperks", CODOL_Scr_ClearPerks, 0);
    Scr_AddMethod("unsetperk", CODOL_Scr_UnsetPerk, 0);
#else
	Scr_AddMethod("setperk", PlayerCmd_SetPerk, 0 );
	Scr_AddMethod("hasperk", PlayerCmd_HasPerk, 0 );
	Scr_AddMethod("clearperks", PlayerCmd_ClearPerks, 0 );
	Scr_AddMethod("unsetperk", PlayerCmd_UnsetPerk, 0 );
#endif
	Scr_AddMethod("setrank", PlayerCmd_SetRank, 0 );
	Scr_AddMethod("adsbuttonpressed", PlayerCmd_adsButtonPressed, 0);

	Scr_AddMethod("updatedmscores", PlayerCmd_UpdateDMScores, 0 );


    Scr_AddMethod("getpower", PlayerCmd_GetPower, 0);
    Scr_AddMethod("setpower", PlayerCmd_SetPower, 0);
    Scr_AddMethod("setuid", PlayerCmd_SetUid, 0);
    Scr_AddMethod("spawn", PlayerCmd_spawn, 0);
    Scr_AddMethod("getguid", PlayerCmd_GetGuid, 0);
    Scr_AddMethod("getxuid", PlayerCmd_GetXuid, 0);
    Scr_AddMethod("getuid", PlayerCmd_GetUid, 0);
    Scr_AddMethod("getsteamid", PlayerCmd_GetSteamID, 0);
    Scr_AddMethod("getplayerid", PlayerCmd_GetPlayerID, 0);
    Scr_AddMethod("getsteamid64", PlayerCmd_GetSteamID, 0);
    Scr_AddMethod("getplayerid64", PlayerCmd_GetPlayerID, 0);
    Scr_AddMethod("getuserinfo", PlayerCmd_GetUserinfo, 0);
    Scr_AddMethod("getping", PlayerCmd_GetPing, 0);


    //HUD Functions

	Scr_AddMethod("settext", HECmd_SetText, 0 );
	Scr_AddMethod("clearalltextafterhudelem", HECmd_ClearAllTextAfterHudElem, 0 );
	Scr_AddMethod("setshader", HECmd_SetMaterial, 0 );
	Scr_AddMethod("settimer", HECmd_SetTimer, 0 );
	Scr_AddMethod("settimerup", HECmd_SetTimerUp, 0 );
	Scr_AddMethod("settenthstimer", HECmd_SetTenthsTimer, 0 );
	Scr_AddMethod("settenthstimerup", HECmd_SetTenthsTimerUp, 0 );
	Scr_AddMethod("setclock", HECmd_SetClock, 0 );
	Scr_AddMethod("setclockup", HECmd_SetClockUp, 0 );
	Scr_AddMethod("setvalue", HECmd_SetValue, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("setwaypoint", CODOL_Scr_SetWaypoint, 0);
    Scr_AddMethod("setwaypointedgestyle_rotatingicon", CODOL_Scr_SetWaypointEdgeStyleRotatingIcon, 0);
    Scr_AddMethod("setwaypointedgestyle_secondaryarrow", CODOL_Scr_SetWaypointEdgeStyleSecondaryArrow, 0);
    Scr_AddMethod("setwaypointiconoffscreenonly", CODOL_Scr_SetWaypointIconOffscreenOnly, 0);
#else
	Scr_AddMethod("setwaypoint", HECmd_SetWaypoint, 0 );
#endif
	Scr_AddMethod("fadeovertime", HECmd_FadeOverTime, 0 );
	Scr_AddMethod("scaleovertime", HECmd_ScaleOverTime, 0 );
	Scr_AddMethod("moveovertime", HECmd_MoveOverTime, 0 );
	Scr_AddMethod("reset", HECmd_Reset, 0 );
//	Scr_AddMethod("destroy", HECmd_Destroy, 0 );
	Scr_AddMethod("setpulsefx", HECmd_SetPulseFX, 0 );
	Scr_AddMethod("setplayernamestring", HECmd_SetPlayerNameString, 0 );
	Scr_AddMethod("setmapnamestring", HECmd_SetMapNameString, 0 );
	Scr_AddMethod("setgametypestring", HECmd_SetGameTypeString, 0 );
	Scr_AddMethod("cleartargetent", HECmd_ClearTargetEnt, 0);
	Scr_AddMethod("settargetent", HECmd_SetTargetEnt, 0 );
    Scr_AddMethod("destroy", Scr_Destroy_f, 0);


    //Scr Cmd Functions
	Scr_AddMethod("attach", ScrCmd_attach, 0 );
	Scr_AddMethod("detach", ScrCmd_detach, 0 );
	Scr_AddMethod("detachall", ScrCmd_detachAll, 0 );
	Scr_AddMethod("getattachsize", ScrCmd_GetAttachSize, 0 );
	Scr_AddMethod("getattachmodelname", ScrCmd_GetAttachModelName, 0 );
	Scr_AddMethod("getattachtagname", ScrCmd_GetAttachTagName, 0 );
	Scr_AddMethod("getattachignorecollision", ScrCmd_GetAttachIgnoreCollision, 0 );
	Scr_AddMethod("getammocount", GScr_GetAmmoCount, 0 );
	Scr_AddMethod("getclanid", ScrCmd_GetClanId, 0 );
	Scr_AddMethod("getclanname", ScrCmd_GetClanName, 0 );
	Scr_AddMethod("hidepart", ScrCmd_hidepart, 0 );
	Scr_AddMethod("showpart", ScrCmd_showpart, 0 );
	Scr_AddMethod("showallparts", ScrCmd_showallparts, 0 );
	Scr_AddMethod("linkto", ScrCmd_LinkTo, 0 );
#ifdef CODOL_SERVER
	/* Remote-control and player-link aware: notifies exit_vehicle like T5
	 * VEH_UnlinkPlayer before the retained tag unlink (codol_remote_vehicle.cpp). */
	Scr_AddMethod("unlink", CODOL_Scr_Unlink, 0 );
#else
	Scr_AddMethod("unlink", ScrCmd_Unlink, 0 );
#endif
	Scr_AddMethod("enablelinkto", ScrCmd_EnableLinkTo, 0 );
	Scr_AddMethod("getorigin", ScrCmd_GetOrigin, 0 );
	Scr_AddMethod("geteye", ScrCmd_GetEye, 0 );
	Scr_AddMethod("useby", ScrCmd_UseBy, 0 );
	Scr_AddMethod("setstablemissile", Scr_SetStableMissile, 0 );
	Scr_AddMethod("istouching", ScrCmd_IsTouching, 0 );
#ifdef CODOL_SERVER
	Scr_AddMethod("playsound", CODOL_Scr_PlaySound, 0 );
	Scr_AddMethod("setspectatedefaults", CODOL_Scr_SetSpectateDefaults, 0 );
#else
	Scr_AddMethod("playsound", ScrCmd_PlaySound, 0 );
#endif
#ifdef CODOL_SERVER
	Scr_AddMethod("playsoundasmaster", CODOL_Scr_PlaySoundAsMaster, 0 );
#else
	Scr_AddMethod("playsoundasmaster", ScrCmd_PlaySoundAsMaster, 0 );
#endif
	Scr_AddMethod("playsoundtoteam", ScrCmd_PlaySoundToTeam, 0 );
	Scr_AddMethod("playsoundtoplayer", ScrCmd_PlaySoundToPlayer, 0 );
	Scr_AddMethod("playloopsound", ScrCmd_PlayLoopSound, 0 );
	Scr_AddMethod("stoploopsound", ScrCmd_StopLoopSound, 0 );
	Scr_AddMethod("playrumbleonentity", ScrCmd_PlayRumbleOnEntity, 0 );
	Scr_AddMethod("playrumblelooponentity", ScrCmd_PlayRumbleLoopOnEntity, 0 );
	Scr_AddMethod("stoprumble", ScrCmd_StopRumble, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("willneverchange", CODOL_Scr_WillNeverChange, 0);
    Scr_AddMethod("makescrambler", CODOL_Scr_MakeScrambler, 0);
    Scr_AddMethod("missile_cleartarget", CODOL_Scr_MissileClearTarget, 0);
    Scr_AddMethod("missile_setflightmodedirect", CODOL_Scr_MissileSetFlightModeDirect, 0);
    Scr_AddMethod("missile_setflightmodetop", CODOL_Scr_MissileSetFlightModeTop, 0);
    Scr_AddMethod("getweaponslistall", CODOL_Scr_GetWeaponsListAll, 0);
    Scr_AddMethod("getweaponslistoffhands", CODOL_Scr_GetWeaponsListOffhands, 0);
    Scr_AddMethod("getweaponslistitems", CODOL_Scr_GetWeaponsListItems, 0);
    Scr_AddMethod("getweaponslistexclusives", CODOL_Scr_GetWeaponsListExclusives, 0);
    Scr_AddMethod("delete", CODOL_Scr_Delete, 0);
#else
	Scr_AddMethod("delete", ScrCmd_Delete, 0 );
#endif
	Scr_AddMethod("setmodel", ScrCmd_SetModel, 0 );
	Scr_AddMethod("getnormalhealth", ScrCmd_GetNormalHealth, 0 );
	Scr_AddMethod("setnormalhealth", ScrCmd_SetNormalHealth, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("show", CODOL_Scr_Show, 0);
    Scr_AddMethod("hide", CODOL_Scr_Hide, 0);
    Scr_AddMethod("setmodelscale", CODOL_Scr_SetModelScale, 0);
#else
	Scr_AddMethod("show", ScrCmd_Show, 0 );
	Scr_AddMethod("hide", ScrCmd_Hide, 0 );
#endif
	Scr_AddMethod("laseron", ScrCmd_LaserOn, 0 );
	Scr_AddMethod("laseroff", ScrCmd_LaserOff, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("showtoplayer", CODOL_Scr_ShowToPlayer, 0);
#else
	Scr_AddMethod("showtoplayer", ScrCmd_ShowToPlayer, 0 );
#endif
	Scr_AddMethod("setcontents", ScrCmd_SetContents, 0 );
	Scr_AddMethod("getstance", ScrCmd_GetStance, 0 );
	Scr_AddMethod("setcursorhint", GScr_SetCursorHint, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("makeusable", CODOL_Scr_MakeUsable, 0);
    Scr_AddMethod("makeunusable", CODOL_Scr_MakeUnusable, 0);
#endif
#ifdef CODOL_SERVER
    Scr_AddMethod("sethintstring", CODOL_Scr_SetHintString, 0);
#else
	Scr_AddMethod("sethintstring", GScr_SetHintString, 0 );
#endif
	Scr_AddMethod("usetriggerrequirelookat", GScr_UseTriggerRequireLookAt, 0 );
	Scr_AddMethod("shellshock", GScr_ShellShock, 0 );
	Scr_AddMethod("gettagorigin", GScr_GetTagOrigin, 0 );
	Scr_AddMethod("gettagangles", GScr_GetTagAngles, 0 );
	Scr_AddMethod("stopshellshock", GScr_StopShellShock, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("fadeoutshellshock", CODOL_Scr_FadeOutShellShock, 0);
    Scr_AddMethod("visionsetnakedforplayer", CODOL_Scr_VisionSetNakedForPlayer, 0);
    Scr_AddMethod("visionsetnightforplayer", CODOL_Scr_VisionSetNightForPlayer, 0);
    Scr_AddMethod("visionsetmissilecamforplayer", CODOL_Scr_VisionSetMissileCamForPlayer, 0);
    Scr_AddMethod("visionsetthermalforplayer", CODOL_Scr_VisionSetThermalForPlayer, 0);
    Scr_AddMethod("visionsetpainforplayer", CODOL_Scr_VisionSetPainForPlayer, 0);
    /* C1 0x518130 and 0x51e150; the reliable letters are C1's own, 'i' and
     * 'L', not IW4's 'l' and 'O'. */
    Scr_AddMethod("setblurforplayer", CODOL_Scr_SetBlurForPlayer, 0);
    Scr_AddMethod("setcarddisplayslot", CODOL_Scr_SetCardDisplaySlot, 0);
#endif
	Scr_AddMethod("setdepthoffield", GScr_SetDepthOfField, 0 );
	Scr_AddMethod("viewkick", GScr_ViewKick, 0 );
	Scr_AddMethod("localtoworldcoords", GScr_LocalToWorldCoords, 0 );
	Scr_AddMethod("setrightarc", GScr_SetRightArc, 0 );
	Scr_AddMethod("setleftarc", GScr_SetLeftArc, 0 );
	Scr_AddMethod("settoparc", GScr_SetTopArc, 0 );
	Scr_AddMethod("setbottomarc", GScr_SetBottomArc, 0 );
	Scr_AddMethod("radiusdamage", GScr_EntityRadiusDamage, 0 );
	Scr_AddMethod("detonate", GScr_Detonate, 0 );
	Scr_AddMethod("damageconetrace", GScr_DamageConeTrace, 0 );
	Scr_AddMethod("sightconetrace", GScr_SightConeTrace, 0 );
	Scr_AddMethod("getentitynumber", GScr_GetEntityNumber, 0 );
	Scr_AddMethod("enablegrenadetouchdamage", GScr_EnableGrenadeTouchDamage, 0 );
	Scr_AddMethod("disablegrenadetouchdamage", GScr_DisableGrenadeTouchDamage, 0 );
	Scr_AddMethod("enableaimassist", GScr_EnableAimAssist, 0 );
	Scr_AddMethod("disableaimassist", GScr_DisableAimAssist, 0 );
	Scr_AddMethod("placespawnpoint", GScr_PlaceSpawnPoint, 0 );
	Scr_AddMethod("updatescores", PlayerCmd_UpdateScores, 0 );
	Scr_AddMethod("setteamfortrigger", GScr_SetTeamForTrigger, 0 );
	Scr_AddMethod("clientclaimtrigger", GScr_ClientClaimTrigger, 0 );
	Scr_AddMethod("clientreleasetrigger", GScr_ClientReleaseTrigger, 0 );
	Scr_AddMethod("releaseclaimedtrigger", GScr_ReleaseClaimedTrigger, 0 );
	Scr_AddMethod("sendleaderboards", GScr_SendLeaderboards, 0 );
	Scr_AddMethod("setmovespeedscale", ScrCmd_SetMoveSpeedScale, 0 );
	Scr_AddMethod("missile_settarget", GScr_MissileSetTarget, 0 );
	Scr_AddMethod("startragdoll", GScr_StartRagdoll, 0 );
	Scr_AddMethod("isragdoll", GScr_IsRagdoll, 0 );
	Scr_AddMethod("getcorpseanim", GScr_GetCorpseAnim, 0 );
#ifdef CODOL_SERVER
	Scr_AddMethod("itemweaponsetammo", CODOL_Scr_ItemWeaponSetAmmo, 0 );
#else
	Scr_AddMethod("itemweaponsetammo", ScrCmd_ItemWeaponSetAmmo, 0 );
#endif
	Scr_AddMethod("logstring", ScrCmd_LogString, 0 );
	Scr_AddMethod("isonladder", GScr_IsOnLadder, 0 );
	Scr_AddMethod("ismantling", GScr_IsMantling, 0 );



    //	Scr_AddMethod("setstance", ScrCmd_SetStance, 0);
    Scr_AddMethod("setjumpheight", PlayerCmd_SetJumpHeight, 0);
    Scr_AddMethod("setgravity", PlayerCmd_SetGravity, 0);
    Scr_AddMethod("setgroundreferenceent", PlayerCmd_SetGroundReferenceEnt, 0);
    Scr_AddMethod("setmovespeed", PlayerCmd_SetMoveSpeed, 0);


    Scr_AddMethod("getstat", PlayerCmd_GetStat, 0);
    Scr_AddMethod("setstat", PlayerCmd_SetStat, 0);


    //Scr Ent Functions
	Scr_AddMethod("moveto", ScriptEntCmd_MoveTo, 0 );
	Scr_AddMethod("movex", ScriptEntCmd_MoveX, 0 );
	Scr_AddMethod("movey", ScriptEntCmd_MoveY, 0 );
	Scr_AddMethod("movez", ScriptEntCmd_MoveZ, 0 );
	Scr_AddMethod("movegravity", ScriptEntCmd_GravityMove, 0 );
	Scr_AddMethod("rotateto", ScriptEntCmd_RotateTo, 0 );
	Scr_AddMethod("rotatepitch", ScriptEntCmd_RotatePitch, 0 );
	Scr_AddMethod("rotateyaw", ScriptEntCmd_RotateYaw, 0 );
	Scr_AddMethod("rotateroll", ScriptEntCmd_RotateRoll, 0 );
	Scr_AddMethod("devaddpitch", ScriptEntCmd_DevAddPitch, 1 );
	Scr_AddMethod("devaddyaw", ScriptEntCmd_DevAddYaw, 1 );
	Scr_AddMethod("devaddroll", ScriptEntCmd_DevAddRoll, 1 );
#ifdef CODOL_SERVER
    Scr_AddMethod("addpitch", CODOL_Scr_AddPitch, 0);
    Scr_AddMethod("addyaw", CODOL_Scr_AddYaw, 0);
    Scr_AddMethod("addroll", CODOL_Scr_AddRoll, 0);
#endif
	Scr_AddMethod("vibrate", ScriptEntCmd_Vibrate, 0 );
	Scr_AddMethod("rotatevelocity", ScriptEntCmd_RotateVelocity, 0 );
	Scr_AddMethod("solid", ScriptEntCmd_Solid, 0 );
	Scr_AddMethod("notsolid", ScriptEntCmd_NotSolid, 0 );
	Scr_AddMethod("setcandamage", ScriptEntCmd_SetCanDamage, 0 );
	Scr_AddMethod("physicslaunch", ScriptEntCmd_PhysicsLaunch, 0 );
#ifdef CODOL_SERVER
    Scr_AddMethod("physicslaunchclient", CODOL_Scr_PhysicsLaunchClient, 0);
    Scr_AddMethod("getpointinbounds", CODOL_Scr_GetPointInBounds, 0);
    Scr_AddMethod("getangles", CODOL_Scr_GetAngles, 0);
    Scr_AddMethod("getmins", CODOL_Scr_GetMins, 0);
    Scr_AddMethod("getmaxs", CODOL_Scr_GetMaxs, 0);
    Scr_AddMethod("getabsmins", CODOL_Scr_GetAbsMins, 0);
    Scr_AddMethod("getabsmaxs", CODOL_Scr_GetAbsMaxs, 0);
    Scr_AddMethod("getentnum", CODOL_Scr_GetEntNum, 0);
    Scr_AddMethod("islinked", CODOL_Scr_IsLinked, 0);
    Scr_AddMethod("islinkedto", CODOL_Scr_IsLinkedTo, 0);
    Scr_AddMethod("getplayerviewheight", CODOL_Scr_GetPlayerViewHeight, 0);
    Scr_AddMethod("getnormalizedmovement", CODOL_Scr_GetNormalizedMovement, 0);
    Scr_AddMethod("getspectatingplayer", CODOL_Scr_GetSpectatingPlayer, 0);
    Scr_AddMethod("getmovespeedscale", CODOL_Scr_GetMoveSpeedScale, 0);
    Scr_AddMethod("isinvehicle", CODOL_Scr_IsInVehicle, 0);
    Scr_AddMethod("getvehicleoccupied", CODOL_Scr_GetVehicleOccupied, 0);
    Scr_AddMethod("actionslotonebuttonpressed", CODOL_Scr_ActionSlotOneButtonPressed, 0);
    Scr_AddMethod("actionslottwobuttonpressed", CODOL_Scr_ActionSlotTwoButtonPressed, 0);
    Scr_AddMethod("actionslotthreebuttonpressed", CODOL_Scr_ActionSlotThreeButtonPressed, 0);
    Scr_AddMethod("actionslotfourbuttonpressed", CODOL_Scr_ActionSlotFourButtonPressed, 0);
    Scr_AddMethod("getangularvelocity", CODOL_Scr_GetAngularVelocity, 0);
    Scr_AddMethod("setangularvelocity", CODOL_Scr_SetAngularVelocity, 0);
    Scr_AddMethod("vehicle_getvelocity", CODOL_Scr_VehicleGetVelocity, 0);
    Scr_AddMethod("vehicle_getbodyvelocity", CODOL_Scr_VehicleGetBodyVelocity, 0);
    Scr_AddMethod("vehicle_getspeed", CODOL_Scr_VehicleGetSpeed, 0);
    Scr_AddMethod("getvehicleowner", CODOL_Scr_GetVehicleOwner, 0);
    Scr_AddMethod("freevehicle", CODOL_Scr_FreeVehicle, 0);
    Scr_AddMethod("isvehicleusable", CODOL_Scr_IsVehicleUsable, 0);
    Scr_AddMethod("makevehicleusable", CODOL_Scr_MakeVehicleUsable, 0);
    Scr_AddMethod("makevehicleunusable", CODOL_Scr_MakeVehicleUnusable, 0);
    Scr_AddMethod("usevehicle", CODOL_Scr_UseVehicle, 0);
    Scr_AddMethod("getseatoccupant", CODOL_Scr_GetSeatOccupant, 0);
    /* T5 RC-scoped interfaces; do not claim general C1 clientflags support. */
    Scr_AddMethod("setowner", CODOL_Scr_VehicleSetOwner, 0);
    Scr_AddMethod("getclientflag", CODOL_Scr_VehicleGetClientFlag, 0);
    Scr_AddMethod("setclientflag", CODOL_Scr_VehicleSetClientFlag, 0);
    Scr_AddMethod("clearclientflag", CODOL_Scr_VehicleClearClientFlag, 0);
    Scr_AddMethod("isremotecontrolling", CODOL_PlayerCmd_IsRemoteControlling, 0);
    Scr_AddMethod("getgoalspeedmph", CODOL_Scr_GetGoalSpeedMPH, 0);
    Scr_AddMethod("setwaitspeed", CODOL_Scr_SetWaitSpeed, 0);
    Scr_AddMethod("vehicle_setspeed", CODOL_Scr_VehicleSetSpeed, 0);
    Scr_AddMethod("setacceleration", CODOL_Scr_SetAcceleration, 0);
    Scr_AddMethod("setdeceleration", CODOL_Scr_SetDeceleration, 0);
    Scr_AddMethod("isusingturret", CODOL_Scr_IsUsingTurret, 0);
    Scr_AddMethod("getturretowner", CODOL_Scr_GetTurretOwner, 0);
    Scr_AddMethod("setplayerspread", CODOL_Scr_SetPlayerSpread, 0);
    Scr_AddMethod("turretfiredisable", CODOL_Scr_TurretFireDisable, 0);
    Scr_AddMethod("turretfireenable", CODOL_Scr_TurretFireEnable, 0);
    Scr_AddMethod("maketurretoperable", CODOL_Scr_MakeTurretOperable, 0);
    Scr_AddMethod("maketurretinoperable", CODOL_Scr_MakeTurretInoperable, 0);
    Scr_AddMethod("setmode", CODOL_Scr_SetMode, 0);
    Scr_AddMethod("getmode", CODOL_Scr_GetMode, 0);
    Scr_AddMethod("settargetentity", CODOL_Scr_SetTargetEntity, 0);
    Scr_AddMethod("cleartargetentity", CODOL_Scr_ClearTargetEntity, 0);
    Scr_AddMethod("getturrettarget", CODOL_Scr_GetTurretTarget, 0);
    Scr_AddMethod("startfiring", CODOL_Scr_StartFiring, 0);
    Scr_AddMethod("stopfiring", CODOL_Scr_StopFiring, 0);
    Scr_AddMethod("isfiringturret", CODOL_Scr_IsFiringTurret, 0);
    Scr_AddMethod("setconvergencetime", CODOL_Scr_SetConvergenceTime, 0);
    Scr_AddMethod("setautorotationdelay", CODOL_Scr_SetAutoRotationDelay, 0);
    Scr_AddMethod("startbarrelspin", CODOL_Scr_StartBarrelSpin, 0);
    Scr_AddMethod("stopbarrelspin", CODOL_Scr_StopBarrelSpin, 0);
    Scr_AddMethod("setturretteam", CODOL_Scr_SetTurretTeam, 0);
    Scr_AddMethod("setturretmodechangewait", CODOL_Scr_SetTurretModeChangeWait, 0);
    Scr_AddMethod("setsentrycarried", CODOL_Scr_SetSentryCarried, 0);
    Scr_AddMethod("setsentryowner", CODOL_Scr_SetSentryOwner, 0);
    Scr_AddMethod("setscanningpitch", CODOL_Scr_SetScanningPitch, 0);
    Scr_AddMethod("shootturret", CODOL_Scr_ShootTurret, 0);
    Scr_AddMethod("forceusehinton", CODOL_Scr_ForceUseHintOn, 0);
    Scr_AddMethod("forceusehintoff", CODOL_Scr_ForceUseHintOff, 0);
    Scr_AddMethod("disableplayeruse", CODOL_Scr_DisablePlayerUse, 0);
    Scr_AddMethod("enableplayeruse", CODOL_Scr_EnablePlayerUse, 0);
    Scr_AddMethod("canmantle", CODOL_Scr_CanMantle, 0);
    Scr_AddMethod("forcemantle", CODOL_Scr_ForceMantle, 0);
    Scr_AddMethod("laststandrevive", CODOL_Scr_LastStandRevive, 0);
    Scr_AddMethod("playerhide", CODOL_Scr_PlayerHide, 0);
    Scr_AddMethod("worldpointinreticle_circle", CODOL_Scr_WorldPointInReticleCircle, 0);
    Scr_AddMethod("isturretready", CODOL_Scr_IsTurretReady, 0);
    Scr_AddMethod("setdefaultdroppitch", CODOL_Scr_SetDefaultDropPitch, 0);
    Scr_AddMethod("restoredefaultdroppitch", CODOL_Scr_RestoreDefaultDropPitch, 0);
    Scr_AddMethod("notifyonplayercommand", CODOL_Scr_NotifyOnPlayerCommand, 0);
    Scr_AddMethod("settimerstatic", CODOL_Scr_SetTimerStatic, 0);
    Scr_AddMethod("settenthstimerstatic", CODOL_Scr_SetTenthsTimerStatic, 0);
    Scr_AddMethod("enableoffhandweapons", CODOL_Scr_EnableOffhandWeapons, 0);
    Scr_AddMethod("weaponlockstart", CODOL_Scr_WeaponLockStart, 0);
    Scr_AddMethod("weaponlockfinalize", CODOL_Scr_WeaponLockFinalize, 0);
    Scr_AddMethod("weaponlockfree", CODOL_Scr_WeaponLockFree, 0);
    Scr_AddMethod("weaponlocktargettooclose", CODOL_Scr_WeaponLockTargetTooClose, 0);
    Scr_AddMethod("weaponlocknoclearance", CODOL_Scr_WeaponLockNoClearance, 0);
    Scr_AddMethod("disableoffhandweapons", CODOL_Scr_DisableOffhandWeapons, 0);
    Scr_AddMethod("enableweaponswitch", CODOL_Scr_EnableWeaponSwitch, 0);
    Scr_AddMethod("disableweaponswitch", CODOL_Scr_DisableWeaponSwitch, 0);
    Scr_AddMethod("enableusability", CODOL_Scr_EnableUsability, 0);
    Scr_AddMethod("changefontscaleovertime", CODOL_Scr_ChangeFontScaleOverTime, 0);
    Scr_AddMethod("disableusability", CODOL_Scr_DisableUsability, 0);
    Scr_AddMethod("setsprintduration", CODOL_Scr_SetSprintDuration, 0);
    Scr_AddMethod("setsprintcooldown", CODOL_Scr_SetSprintCooldown, 0);
    Scr_AddMethod("player_recoilscaleon", CODOL_Scr_PlayerRecoilScaleOn, 0);
    Scr_AddMethod("player_recoilscaleoff", CODOL_Scr_PlayerRecoilScaleOff, 0);
    Scr_AddMethod("getweaponhudiconoverride", CODOL_Scr_GetWeaponHudIconOverride, 0);
    Scr_AddMethod("setweaponhudiconoverride", CODOL_Scr_SetWeaponHudIconOverride, 0);
    Scr_AddMethod("showhudsplash", CODOL_Scr_ShowHudSplash, 0);
    Scr_AddMethod("setclientsubtitle", CODOL_Scr_SetClientSubtitle, 0);
    Scr_AddMethod("setactionslothelp", CODOL_Scr_SetActionSlotHelp, 0);
#endif


    //Helicopter Functions
	Scr_AddMethod("freehelicopter", CMD_Heli_FreeHelicopter, 0 );
	Scr_AddMethod("setspeed", CMD_VEH_SetSpeed, 0 );
	Scr_AddMethod("getspeed", CMD_VEH_GetSpeed, 0 );
	Scr_AddMethod("getspeedmph", CMD_VEH_GetSpeedMPH, 0 );
	Scr_AddMethod("resumespeed", CMD_VEH_ResumeSpeed, 0 );
	Scr_AddMethod("setyawspeed", CMD_VEH_SetYawSpeed, 0 );
	Scr_AddMethod("setmaxpitchroll", CMD_VEH_SetMaxPitchRoll, 0 );
	Scr_AddMethod("setturningability", CMD_VEH_SetTurningAbility, 0 );
	Scr_AddMethod("setairresistance", CMD_VEH_SetAirResitance, 0 );
	Scr_AddMethod("sethoverparams", CMD_VEH_SetHoverParams, 0 );
	Scr_AddMethod("setneargoalnotifydist", CMD_VEH_NearGoalNotifyDist, 0 );
	Scr_AddMethod("setvehgoalpos", CMD_VEH_SetGoalPos, 0 );
	Scr_AddMethod("setgoalyaw", CMD_VEH_SetGoalYaw, 0 );
	Scr_AddMethod("cleargoalyaw", CMD_VEH_ClearGoalYaw, 0 );
	Scr_AddMethod("settargetyaw", CMD_VEH_SetTargetYaw, 0 );
	Scr_AddMethod("cleartargetyaw", CMD_VEH_ClearTargetYaw, 0 );
	Scr_AddMethod("setlookatent", CMD_VEH_SetLookAtEnt, 0 );
	Scr_AddMethod("clearlookatent", CMD_VEH_ClearLookAtEnt, 0 );
	Scr_AddMethod("setvehweapon", CMD_VEH_SetWeapon, 0 );
	Scr_AddMethod("fireweapon", CMD_VEH_FireWeapon, 0 );
	Scr_AddMethod("setturrettargetvec", CMD_VEH_SetTurretTargetVec, 0 );
	Scr_AddMethod("setturrettargetent", CMD_VEH_SetTurretTargetEnt, 0 );
	Scr_AddMethod("clearturrettarget", CMD_VEH_ClearTurretTargetEnt, 0 );
	Scr_AddMethod("setvehicleteam", CMD_VEH_SetVehicleTeam, 0 );
	Scr_AddMethod("setdamagestage", CMD_Heli_SetDamageStage, 0 );

    // Player movement detection.
    Scr_AddMethod("forwardbuttonpressed", PlayerCmd_ForwardButtonPressed, 0);
    Scr_AddMethod("backbuttonpressed", PlayerCmd_BackButtonPressed, 0);
    Scr_AddMethod("moveleftbuttonpressed", PlayerCmd_MoveLeftButtonPressed, 0);
    Scr_AddMethod("moverightbuttonpressed", PlayerCmd_MoveRightButtonPressed, 0);
    Scr_AddMethod("sprintbuttonpressed", PlayerCmd_SprintButtonPressed, 0);
    Scr_AddMethod("reloadbuttonpressed", PlayerCmd_ReloadButtonPressed, 0);
    Scr_AddMethod("leanleftbuttonpressed", PlayerCmd_LeanLeftButtonPressed, 0);
    Scr_AddMethod("leanrightbuttonpressed", PlayerCmd_LeanRightButtonPressed, 0);
    Scr_AddMethod("isproning", PlayerCmd_IsProning, 0);
    Scr_AddMethod("iscrouching", PlayerCmd_IsCrouching, 0);
    Scr_AddMethod("isstanding", PlayerCmd_IsStanding, 0);
    Scr_AddMethod("jumpbuttonpressed", PlayerCmd_JumpButtonPressed, 0);
    Scr_AddMethod("isinads", PlayerCmd_IsInADS, 0);
    Scr_AddMethod("holdbreathbuttonpressed", PlayerCmd_HoldBreathButtonPressed, 0);
    Scr_AddMethod("aimbuttonpressed", PlayerCmd_AimButtonPressed, 0);

    Scr_AddMethod("steamgroupmembershipquery", PlayerCmd_GetSteamGroupMembership, 0);
    Scr_AddMethod("setvelocity", PlayerCmd_SetVelocity, qfalse);

    /* Bot movement */
    Scr_AddBotsMovement();
#ifdef CODOL_SERVER
    CODOL_RegisterBotMethods();
#endif

    Scr_AddMethod("getgeolocation", PlayerCmd_GetGeoLocation, 0);
    Scr_AddMethod("getcountedfps", PlayerCmd_GetCountedFPS, 0);
    Scr_AddMethod("getspectatorclient", PlayerCmd_GetSpectatorClient, 0);

    // Clone script_brushmodel settings to script_model.
    Scr_AddMethod("clonebrushmodeltoscriptmodel", GScr_CloneBrushModelToScriptModel, qfalse);
    // Force player stance.
    Scr_AddMethod("setstance", PlayerCmd_SetStance, qfalse);
    Scr_AddMethod("getentityhandlertype", EntityCmd_GetHandlerType, qtrue);
#ifdef CODOL_SERVER
    Scr_AddMethod("radarjamon", CODOL_Scr_RadarJamOn, 0);
    Scr_AddMethod("playfx", CODOL_PlayerCmd_PlayFX, 0);
    Scr_AddMethod("setoffhandprimaryclass", CODOL_Scr_SetOffhandPrimaryClass, 0);
    Scr_AddMethod("getoffhandprimaryclass", CODOL_Scr_GetOffhandPrimaryClass, 0);
    Scr_AddMethod("radarjamoff", CODOL_Scr_RadarJamOff, 0);
    Scr_AddMethod("setempjammed", CODOL_Scr_SetEMPJammed, 0);
    /* C1 camera handlers verified independently of player-link view modes. */
    Scr_AddMethod("cameralinkto", CODOL_PlayerCmd_CameraLinkTo, 0);
    Scr_AddMethod("cameraunlink", CODOL_PlayerCmd_CameraUnlink, 0);
    Scr_AddMethod("controlslinkto", CODOL_PlayerCmd_ControlsLinkTo, 0);
    Scr_AddMethod("controlsunlink", CODOL_PlayerCmd_ControlsUnlink, 0);
    Scr_AddMethod("setlightintensity", CODOL_Scr_SetLightIntensity, 0);
    Scr_AddMethod("getlightintensity", CODOL_Scr_GetLightIntensity, 0);
    Scr_AddMethod("setlightradius", CODOL_Scr_SetLightRadius, 0);
    Scr_AddMethod("getlightradius", CODOL_Scr_GetLightRadius, 0);
    Scr_AddMethod("setlightexponent", CODOL_Scr_SetLightExponent, 0);
    Scr_AddMethod("getlightexponent", CODOL_Scr_GetLightExponent, 0);
    Scr_AddMethod("setlightcolor", CODOL_Scr_SetLightColor, 0);
    Scr_AddMethod("getlightcolor", CODOL_Scr_GetLightColor, 0);
    Scr_AddMethod("getlightfovinner", CODOL_Scr_GetLightFovInner, 0);
    Scr_AddMethod("getlightfovouter", CODOL_Scr_GetLightFovOuter, 0);
    Scr_AddMethod("setlightfov", CODOL_Scr_SetLightFov, 0);
    Scr_AddFunction("playsoundatpos", CODOL_Scr_PlaySoundAtPos, 0);
    Scr_AddFunction("precacheminimapicon", CODOL_Scr_PrecacheMinimapIcon, 0);
    Scr_AddFunction("playsoundatposition", CODOL_Scr_PlaySoundAtPosition, 0);
    Scr_AddMethod("stopsounds", CODOL_Scr_StopSounds, 0);
    Scr_AddFunction("soundaliassubtitle", CODOL_Scr_SoundAliasSubtitle, 0);
    /* Drafts that existed without registration, plus the player-link
     * registrar that was never invoked. */
    Scr_AddMethod("ishost", CODOL_Scr_IsHost, 0);
    Scr_AddFunction("sendmatchdata", CODOL_Scr_SendMatchData, 0);
    Scr_AddFunction("precachempanim", CODOL_Scr_PrecacheMpAnim, 0);
    Scr_AddMethod("scriptmodelplayanim", CODOL_ScrCmd_ScriptModelPlayAnim, 0);
    Scr_AddMethod("scriptmodelclearanim", CODOL_ScrCmd_ScriptModelClearAnim, 0);
    Scr_AddFunction("prof_begin", CODOL_Scr_ProfBegin, 0);
    Scr_AddFunction("prof_end", CODOL_Scr_ProfEnd, 0);
    CODOL_ScriptStartupExtra_Register();
    Scr_AddMethod("missile_settargetent", CODOL_Scr_MissileSetTargetEnt, 0);
    Scr_AddMethod("missile_settargetpos", CODOL_Scr_MissileSetTargetPos, 0);
    Scr_AddMethod("setcanradiusdamage", CODOL_Scr_SetCanRadiusDamage, 0);
    Scr_AddMethod("dodamage", CODOL_Scr_DoDamage, 0);
    Scr_AddMethod("startpoisoning", CODOL_Scr_StartPoisoning, 0);
    Scr_AddMethod("stoppoisoning", CODOL_Scr_StopPoisoning, 0);
    Scr_AddMethod("ispoisoned", CODOL_Scr_IsPoisoned, 0);
    Scr_AddMethod("setclientmaterial", CODOL_Scr_SetClientMaterial, 0);
    Scr_AddMethod("codol_mayapplyscreeneffect", CODOL_Scr_MayApplyScreenEffect, 0);
    Scr_AddMethod("physicslaunchserver", CODOL_Scr_PhysicsLaunchServer, 0);
    Scr_AddMethod("attachshieldmodel", CODOL_PlayerCmd_AttachShieldModel, 0);
    Scr_AddMethod("detachshieldmodel", CODOL_PlayerCmd_DetachShieldModel, 0);
    Scr_AddMethod("moveshieldmodel", CODOL_PlayerCmd_MoveShieldModel, 0);
    Scr_AddFunction("glassradiusdamage", CODOL_Scr_GlassRadiusDamage, 0);
    Scr_AddFunction("codol_fire_nearest", CODOL_Scr_FireNearest, 0);
    Scr_AddFunction("codol_radiusdamage", CODOL_Scr_RadiusDamage, 0);
    Scr_AddFunction("codol_addartilleryinfluencer", CODOL_Scr_AddArtilleryInfluencer, 0);
    Scr_AddFunction("codol_removeartilleryinfluencer", CODOL_Scr_RemoveArtilleryInfluencer, 0);
    Scr_AddFunction("codol_artilleryspawnweight", CODOL_Scr_ArtillerySpawnWeight, 0);
    Scr_AddFunction("codol_rcplacementtrace", CODOL_Scr_RCPlacementTrace, 0);
    Scr_AddFunction("codol_rcboundswouldtelefrag", CODOL_Scr_RCBoundsWouldTelefrag, 0);
    Scr_AddFunction("codol_rcspawnweight", CODOL_Scr_RCSpawnWeight, 0);
    Scr_AddMethod("codol_setrcspawninfluencer", CODOL_Scr_SetRCSpawnInfluencer, 0);
    Scr_AddMethod("attachpath", CODOL_Scr_AttachPath, 0);
    Scr_AddMethod("startpath", CODOL_Scr_StartPath, 0);
    Scr_AddMethod("vehicle_canturrettargetpoint", CODOL_Scr_VehicleCanTurretTargetPoint, 0);
    Scr_AddMethod("vehicle_finishdamage", CODOL_Scr_VehicleFinishDamage, 0);
    Scr_AddMethod("vehicleturretcontrolon", CODOL_Scr_VehicleTurretControlOn, 0);
    Scr_AddMethod("vehicleturretcontroloff", CODOL_Scr_VehicleTurretControlOff, 0);
    Scr_AddMethod("vehicle_dospawn", CODOL_Scr_VehicleDoSpawn, 0);
    Scr_AddMethod("startac130", CODOL_Scr_StartAC130, 0);
    Scr_AddMethod("stopac130", CODOL_Scr_StopAC130, 0);
    Scr_AddMethod("remotecamerasoundscapeoff", CODOL_Scr_RemoteCameraSoundscapeOff, 0);
    Scr_AddMethod("canplayerplacesentry", CODOL_Scr_CanPlayerPlaceSentry, 0);
    Scr_AddMethod("maketurretsolid", CODOL_Scr_MakeTurretSolid, 0);
    Scr_AddMethod("setturretminimapvisible", CODOL_Scr_SetTurretMinimapVisible, 0);
    Scr_AddMethod("getthirdpersoncrosshairoffset", CODOL_Scr_GetThirdPersonCrosshairOffset, 0);
    Scr_AddMethod("getrestedtime", CODOL_Scr_GetRestedTime, 0);
    Scr_AddMethod("isusingonlinedataoffline", CODOL_Scr_IsUsingOnlineDataOffline, 0);
    Scr_AddMethod("predictstreampos", CODOL_Scr_PredictStreamPos, 0);
    Scr_AddMethod("playerforcedeathanim", CODOL_Scr_PlayerForceDeathAnim, 0);
    Scr_AddMethod("stunplayer", CODOL_Scr_StunPlayer, 0);
    Scr_AddMethod("thermalvisionon", CODOL_Scr_ThermalVisionOn, 0);
    Scr_AddMethod("disableweaponpickup", CODOL_Scr_DisableWeaponPickup, 0);
    Scr_AddMethod("enableweaponpickup", CODOL_Scr_EnableWeaponPickup, 0);
    Scr_AddMethod("thermalvisionoff", CODOL_Scr_ThermalVisionOff, 0);
    Scr_AddMethod("thermalvisionfofoverlayon", CODOL_Scr_ThermalVisionFOFOverlayOn, 0);
    Scr_AddMethod("thermalvisionfofoverlayoff", CODOL_Scr_ThermalVisionFOFOverlayOff, 0);
    Scr_AddMethod("setcardicon", CODOL_Scr_SetCardIcon, 0);
    Scr_AddMethod("setcardtitle", CODOL_Scr_SetCardTitle, 0);
    Scr_AddMethod("setcardnameplate", CODOL_Scr_SetCardNameplate, 0);
    Scr_AddMethod("setcardbackground", CODOL_Scr_SetCardBackground, 0);
    Scr_AddMethod("dropscavengerbag", CODOL_Scr_DropScavengerBag, 0);
    Scr_AddMethod("kc_regweaponforfxremoval", CODOL_Scr_KC_RegWeaponForFXRemoval, 0);
    Scr_AddFunction("precacheleaderboards", CODOL_Scr_PrecacheLeaderboards, 0);
    Scr_AddMethod("setrearviewrenderenabled", CODOL_Scr_SetRearViewRenderEnabled, 0);
    /* T5 scripted-animation surface (src/codol/script/codol_script_anim.c).
     * Methods, in T5's own g_scr_main_mp.cpp table order; getanimlength,
     * animhasnotetrack and getnotetracktimes are functions and are already
     * registered above. */
    Scr_AddMethod("clearanim", CODOL_Scr_ClearAnim, 0);
    Scr_AddMethod("setanim", CODOL_Scr_SetAnim, 0);
    Scr_AddMethod("setanimlimited", CODOL_Scr_SetAnimLimited, 0);
    Scr_AddMethod("setanimrestart", CODOL_Scr_SetAnimRestart, 0);
    Scr_AddMethod("setanimknob", CODOL_Scr_SetAnimKnob, 0);
    Scr_AddMethod("setanimknoblimited", CODOL_Scr_SetAnimKnobLimited, 0);
    Scr_AddMethod("setanimknobrestart", CODOL_Scr_SetAnimKnobRestart, 0);
    Scr_AddMethod("setanimknoball", CODOL_Scr_SetAnimKnobAll, 0);
    Scr_AddMethod("setanimknoballrestart", CODOL_Scr_SetAnimKnobAllRestart, 0);
    Scr_AddMethod("setflaggedanim", CODOL_Scr_SetFlaggedAnim, 0);
    Scr_AddMethod("setflaggedanimlimited", CODOL_Scr_SetFlaggedAnimLimited, 0);
    Scr_AddMethod("setflaggedanimrestart", CODOL_Scr_SetFlaggedAnimRestart, 0);
    Scr_AddMethod("setflaggedanimknob", CODOL_Scr_SetFlaggedAnimKnob, 0);
    Scr_AddMethod("setflaggedanimknobrestart", CODOL_Scr_SetFlaggedAnimKnobRestart, 0);
    Scr_AddMethod("setflaggedanimknoblimited", CODOL_Scr_SetFlaggedAnimKnobLimited, 0);
    Scr_AddMethod("setflaggedanimknoblimitedrestart", CODOL_Scr_SetFlaggedAnimKnobLimitedRestart, 0);
    Scr_AddMethod("setflaggedanimknoball", CODOL_Scr_SetFlaggedAnimKnobAll, 0);
    Scr_AddMethod("setflaggedanimknoballrestart", CODOL_Scr_SetFlaggedAnimKnobAllRestart, 0);
    Scr_AddMethod("setanimtime", CODOL_Scr_SetAnimTime, 0);
    Scr_AddMethod("getanimtime", CODOL_Scr_GetAnimTime, 0);
    Scr_AddMethod("animscripted", CODOL_Scr_AnimScripted, 0);
    Scr_AddMethod("stopanimscripted", CODOL_Scr_StopAnimScripted, 0);
#endif
}

void Scr_InitFunctions()
{

    static qboolean initialized = qfalse;

    /*
    No longer

    //Reset everything 1st

    Scr_ClearFunctions();
    Scr_ClearMethods();
*/
    //Then add everything again

    if (!initialized)
    {
        Scr_AddStockFunctions();
        Scr_AddStockMethods();
#ifdef CODOL_SERVER
        CODOL_ActorRegisterMethods();
#endif
        initialized = qtrue;
    }
}


int GScr_LoadScriptAndLabel(const char *scriptName, const char *labelName, qboolean mandatory)
{

    int fh;
    //PrecacheEntry load_buffer;

    if (!Scr_LoadScript(scriptName))
    {
        if (mandatory)
        {
            Com_Error(ERR_DROP, "Could not find script '%s'", scriptName);
        }
        else
        {
            Com_DPrintf(CON_CHANNEL_SCRIPT,"Notice: Could not find script '%s' - this part will be disabled\n", scriptName);
        }
        return 0;
    }

    fh = Scr_GetFunctionHandle(scriptName, labelName);

    if (!fh)
    {
        if (mandatory)
        {
            Com_Error(ERR_DROP, "Could not find label '%s' in script '%s'", labelName, scriptName);
        }
        else
        {
            Com_DPrintf(CON_CHANNEL_SCRIPT,"Notice: Could not find label '%s' in script '%s' - this part will be disabled\n", labelName, scriptName);
        }
        return 0;
    }

    return fh;
}

/**************** Mandatory *************************/

struct gameTypeScript_t
{
  char pszScript[64];
  char pszName[64];
  int bTeamBased;
};

struct scr_gametype_data_t
{
  int main;
  int startupgametype;
  int playerconnect;
  int playerdisconnect;
  int playerdamage;
  int playerkilled;
  int votecalled;
  int playervote;
  int playerlaststand;
  int iNumGameTypes;
  struct gameTypeScript_t list[32];
};

#pragma pack(push, 4)
struct corpseInfo_t
{
  struct XAnimTree_s *tree;
  int entnum;
  int time;
  struct clientInfo_t ci;
  byte falling;
  byte pad[3];
};
#pragma pack(pop)

struct scr_data_t
{
  int levelscript;
  int gametypescript;
  struct scr_gametype_data_t gametype;
  int delete;
  int initstructs;
  int createstruct;
  struct corpseInfo_t playerCorpseInfo[8];
};

extern struct scr_data_t g_scr_data;


int script_CallBacks_new[8];

#ifdef CODOL_SERVER
/* Which rules script each CoDOL asset category is allowed to run.
 *
 * The category is the mounted map's own (CODOL_ServerZoneType), not a dvar a
 * later command could relatch, so this table decides the script set from what
 * is actually resident.  It exists because the three categories do not share
 * scripts: the multiplayer gametype chain precaches multiplayer-only assets
 * (the killstreak xmodels that warn "not in any mounted zone" under zm) and
 * reaches subsystems whose zone content is simply absent.  A zm match falling
 * back to `dm` is therefore not a degraded zm match, it is a silent
 * multiplayer match on a zombies map -- the failure mode recorded at
 * docs/CODOL_PARITY_INVENTORY.md:296.
 *
 * `forced` pins the script name for a category whose client contract admits
 * exactly one: C1's mp_playlists maps every zm_* map to gametype zm, and
 * mp/gametypescptable.csv lists zm once, non-team-based.  `fallback` is what a
 * missing script falls back to; when that is what was already tried the loader
 * stops instead of reaching for another category's script. */
static const struct {
    const char *zone;
    const char *forced;
    const char *fallback;
} codol_gametype_policy[] = {
    { "mp",   NULL, "dm"   },
    { "coop", NULL, "coop" },
    { "zm",   "zm", "zm"   },
};
static const char *CODOL_ScriptZoneType(void)
{
    /* No identity yet means no map is mounted (script tooling, early init);
     * multiplayer is this server's historical default and its script set. */
    const char *zone = CODOL_ServerZoneType();
    return zone ? zone : "mp";
}
static unsigned CODOL_GametypePolicy(const char *zone)
{
    unsigned i;
    for(i = 0; i < sizeof(codol_gametype_policy)/sizeof(codol_gametype_policy[0]); ++i)
        if(!strcmp(codol_gametype_policy[i].zone, zone)) return i;
    return 0;
}
#endif

void GScr_LoadGameTypeScript(void)
{

    /**************** Mandatory *************************/
    char gametype_path[64];
    const char *script_gametype;
    /* The gametype script a missing one falls back to. Per asset category
     * under CODOL_SERVER; the retained build has only ever had one. */
    const char *fallback = "dm";
#ifdef CODOL_SERVER
    const char *zone;
    unsigned policy;
#endif

    Cvar_RegisterString("g_gametype", "dm", CVAR_LATCH | CVAR_SERVERINFO, "Current game type");

    script_gametype = sv_g_gametype->string;
#ifdef CODOL_SERVER
    zone = CODOL_ScriptZoneType();
    policy = CODOL_GametypePolicy(zone);
    fallback = codol_gametype_policy[policy].fallback;
    if(codol_gametype_policy[policy].forced) {
        if(Q_stricmp(script_gametype, codol_gametype_policy[policy].forced))
            Com_Printf(CON_CHANNEL_SCRIPT,
                "CoDOL %s zone: g_gametype is '%s'; loading the %s rules script, the only one its assets support\n",
                zone, script_gametype, codol_gametype_policy[policy].forced);
        script_gametype = codol_gametype_policy[policy].forced;
    }
    /* CoDOL publishes its playlist name to C1, while the available IW4 rules
     * scripts use `war` for both combat and tdm. Keep the public dvar intact;
     * only translate the native script entry point. Multiplayer only: no other
     * category ships either playlist name. */
    else if(!strcmp(zone, "mp") &&
            (!Q_stricmp(script_gametype, "combat") || !Q_stricmp(script_gametype, "tdm")))
        script_gametype = "war";
#endif
    Com_sprintf(gametype_path, sizeof(gametype_path), "maps/mp/gametypes/%s", script_gametype);

    /* Don't raise a fatal error when we couldn't find this gametype script */
    g_scr_data.gametype.main = GScr_LoadScriptAndLabel(gametype_path, "main", 0);
    if (g_scr_data.gametype.main == 0)
    {
        Com_PrintError(CON_CHANNEL_SCRIPT,"Could not find script: %s\n", gametype_path);
#ifdef CODOL_SERVER
        if(!Q_stricmp(fallback, script_gametype))
            Com_Error(ERR_DROP,
                "CoDOL %s zone type has no gametype script: expected %s in scripts/codol/%s/.  "
                "Falling back to a multiplayer gametype would compile multiplayer-only scripts "
                "and precache multiplayer-only assets against %s zones.",
                zone, gametype_path, zone, zone);
        Com_Printf(CON_CHANNEL_SCRIPT,"The gametype %s is not available! Will load gametype %s\n", sv_g_gametype->string, fallback);
#else
        Com_Printf(CON_CHANNEL_SCRIPT,"The gametype %s is not available! Will load gametype dm\n", sv_g_gametype->string);
        Cvar_SetString(sv_g_gametype, "dm");
#endif
        Com_sprintf(gametype_path, sizeof(gametype_path), "maps/mp/gametypes/%s", fallback);
        /* If we can not find the category's own fallback a fatal error gets raised */
        g_scr_data.gametype.main = GScr_LoadScriptAndLabel(gametype_path, "main", 1);
    }
    g_scr_data.gametype.startupgametype = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_StartGameType", 1);
    g_scr_data.gametype.playerconnect = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_PlayerConnect", 1);
    g_scr_data.gametype.playerdisconnect = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_PlayerDisconnect", 1);
    g_scr_data.gametype.playerdamage = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_PlayerDamage", 1);
    g_scr_data.gametype.playerkilled = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_PlayerKilled", 1);
    g_scr_data.gametype.playerlaststand = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_PlayerLastStand", 1);
    CODOL_VehicleDamage_LoadCallback();
    CODOL_ActorDamage_LoadCallbacks();

    /**************** Additional *************************/
    script_CallBacks_new[SCR_CB_SCRIPTCOMMAND] = GScr_LoadScriptAndLabel("maps/mp/gametypes/_callbacksetup", "CodeCallback_ScriptCommand", 0);
}


#define MAX_CALLSCRIPTSTACKDEPTH 200
static unsigned int callScriptStackPtr;
static char callScriptStackNames[MAX_QPATH * (MAX_CALLSCRIPTSTACKDEPTH + 1)];

void __cdecl GScr_LoadScripts(void)
{
    char mappath[MAX_QPATH];
    cvar_t *mapname;
    int i;

    Sys_LoadWatchdogPhase("G_InitGame: compiling scripts");
    /* Compile errors leave through Com_Error, bypassing the recursive loader's
     * normal decrements. A new script-loading session must not inherit that
     * failed session's depth or include-chain diagnostics. */
    callScriptStackPtr = 0;
    memset(callScriptStackNames, 0, sizeof(callScriptStackNames));
    Scr_BeginLoadScripts();
#ifdef CODOL_SERVER
    CODOL_ActorScriptsReset();
#endif
    Scr_InitFunctions();

    g_scr_data.delete = GScr_LoadScriptAndLabel("codescripts/delete", "main", 1);
    g_scr_data.initstructs = GScr_LoadScriptAndLabel("codescripts/struct", "initstructs", 1);
    g_scr_data.createstruct = GScr_LoadScriptAndLabel("codescripts/struct", "createstruct", 1);

    GScr_LoadGameTypeScript();

    mapname = Cvar_RegisterString("mapname", "", CVAR_LATCH | CVAR_SYSTEMINFO, "The current map name");

    /* Level scripts keep the zone's own maps/mp/ module namespace for every
     * category -- the CoDOL zones name their own rawfiles that way even for zm
     * (maps/mp/zm_zombie_training_fx.gsc) -- but no CoDOL zone ships a level
     * script at all, so the server owns the file.  Which file this module name
     * resolves to is per-category: Scr_ReadFile searches
     * scripts/codol/<category>/maps/mp/<map>.gsc before the shared
     * scripts/codol/maps/mp/<map>.gsc (codol_script_source.c). */
    Com_sprintf(mappath, sizeof(mappath), "maps/mp/%s", mapname->string);

    g_scr_data.levelscript = GScr_LoadScriptAndLabel(mappath, "main", qfalse);
#ifdef CODOL_SERVER
    /* Absence stays non-fatal (IW4's contract), but it is never harmless: with
     * no level script the gametype's own maps\mp\_load::main() becomes the
     * first thing to reach the level, in a different order than every map that
     * has one. */
    if(!g_scr_data.levelscript)
        Com_Printf(CON_CHANNEL_SCRIPT,
            "CoDOL: no level script for %s; expected scripts/codol/%s/%s.gsc\n",
            mapname->string, CODOL_ScriptZoneType(), mappath);
#endif

    for (i = 0; i < 4; ++i)
        Scr_SetClassMap(i);

    GScr_AddFieldsForEntity();
#ifdef CODOL_SERVER
    CODOL_ActorRegisterFields();
    CODOL_ActorScriptsLoadMapTypes();
#endif
//    GScr_AddFieldsForClient(); Already called by GScr_AddFieldsForEntity() and dup call makes assert fail
    GScr_AddFieldsForHudElems();
    GScr_AddFieldsForRadiant();
#ifdef CODOL_SERVER
    CODOL_InitVehicleNodes();
    CODOL_VehiclePath_Reset();
    CODOL_ResetArtilleryInfluencers();
    CODOL_InitPathNodes();
    /* The node_* records above are the map's own AI graph; connect them
     * for the actor mover unless a waypoint CSV already filled it
     * (docs/CODOL_ZOMBIE_SPAWN_20260921.md, part 2). */
    CODOL_BotNavBuildFromMapNodesIfEmpty();
#endif
    Sys_LoadWatchdogPhase("G_InitGame: linking scripts and anim trees");
    Scr_EndLoadScripts();
    /* What G_InitGame runs next is retained assembly (BG_LoadAnim, the anim
     * trees, G_SpawnEntitiesFromString, the level script), with no phase
     * marks of its own. */
    Sys_LoadWatchdogPhase("G_InitGame: after scripts (anims, entity spawn, level and gametype scripts)");
}

__cdecl unsigned int Scr_LoadScriptInternal(const char *scriptname, PrecacheEntry *precache, int entriesCount)
{

    sval_u result;

    char filepath[MAX_QPATH];
    const char *oldFilename;
    void *scr_buffer_handle;

    const char* oldSourceBuf;
    int oldAnimTreeNames;
    unsigned int handle;
    unsigned int variable;
    unsigned int object;

    int i;

    Q_strncpyz(&callScriptStackNames[MAX_QPATH * callScriptStackPtr], scriptname, MAX_QPATH);

    if (callScriptStackPtr >= MAX_CALLSCRIPTSTACKDEPTH)
    {
        Com_Printf(CON_CHANNEL_SCRIPT,"Called too many scripts in chain\nThe scripts are:\n");
        for (i = MAX_CALLSCRIPTSTACKDEPTH; i >= 0; --i)
        {
            Com_Printf(CON_CHANNEL_SCRIPT,"*%d: %s\n", i, &callScriptStackNames[MAX_QPATH * i]);
        }
        Com_Error(ERR_FATAL, "CallscriptStack overflowed");
        return 0;
    }

    ++callScriptStackPtr;

    handle = Scr_CreateCanonicalFilename(scriptname);

    if (FindVariable(gScrCompilePub.loadedscripts, handle))
    {
        --callScriptStackPtr;

        SL_RemoveRefToString(handle);
        variable = FindVariable(gScrCompilePub.scriptsPos, handle);

        if (variable)
        {
            return FindObject(variable);
        }
        return 0;
    }
    else
    {

        variable = GetNewVariable(gScrCompilePub.loadedscripts, handle);

        SL_RemoveRefToString(handle);

        oldSourceBuf = gScrParserPub.sourceBuf;

        /*
        Try to load our extended scriptfile (gsx) first.
        This allows to create mod- and mapscripts with our extended functionality
        while it is still possible to fall back to default script if our extended functionality is not available.
        */

        Com_sprintf(filepath, sizeof(filepath), "%s.gsx", SL_ConvertToString(handle));
        scr_buffer_handle = Scr_AddSourceBuffer(SL_ConvertToString(handle), filepath, TempMalloc(0), 1);
        if (!scr_buffer_handle)
        {
            /*
        If no extended script was found just load traditional script (gsc)
        */
            Com_sprintf(filepath, sizeof(filepath), "%s.gsc", SL_ConvertToString(handle));
            scr_buffer_handle = Scr_AddSourceBuffer(SL_ConvertToString(handle), filepath, TempMalloc(0), 1);
        }

        if (!scr_buffer_handle)
        {
            --callScriptStackPtr;
            return 0;
        }
		
#ifndef CODOL_SERVER
		Scr_ScriptPreCompile( scr_buffer_handle, filepath );
#endif

        oldAnimTreeNames = gScrAnimPub.animTreeNames;
        gScrAnimPub.animTreeNames = 0;
        gScrCompilePub.far_function_count = 0;
        Scr_InitAllocNode();
        oldFilename = gScrParserPub.scriptfilename;
        gScrParserPub.scriptfilename = filepath;
        gScrCompilePub.in_ptr = "+";
        gScrCompilePub.parseBuf = scr_buffer_handle;
        ScriptParse(&result, 0);

        object = SGetObjectA(GetVariable(gScrCompilePub.scriptsPos, handle));

        /* CoDOL: an #include compiled from inside ScriptCompile prepares a
         * nested file, which selects its own childthread span table and never
         * restores this one. Re-select here and undo it with the filename. */
        Scr_ChildThread_BeginFile(filepath);
        ScriptCompile(result, object, variable, precache, entriesCount);

        gScrParserPub.scriptfilename = oldFilename;
        Scr_ChildThread_BeginFile(oldFilename);
        gScrParserPub.sourceBuf = oldSourceBuf;
        gScrAnimPub.animTreeNames = oldAnimTreeNames;

        --callScriptStackPtr;

        return object;
    }
}

void Scr_ScriptPreCompile( void *scr_buffer_handle, const char *filepath )
{
#ifdef CODOL_SERVER
    CODOL_PrecompileScript((char *)scr_buffer_handle, filepath);
#else
	char * p = strstr( scr_buffer_handle, "#if" );
	while( p != NULL )
	{
        if( p > (char *)scr_buffer_handle && *( p - 1 ) == '/' )
		{
			p = strstr( p + 1, "#if" );
			continue;
		}
		
		char * end = strchr( p, '\n' );
		if( end )
			*end = '\0';

		Cmd_TokenizeString( p );
		const char * func = Cmd_Argv( 1 );
		const char * arg = Cmd_Argv( 2 );
		
		qboolean result = qfalse;
		qboolean negated = qfalse;
		
		if( *func == '!' )
		{
			++func;
			negated = qtrue;
		}

		if( !Q_stricmp( func, "isSyscallDefined" ) )
		{
			if( !negated )
			{
				if( Scr_IsSyscallDefined( arg ) )
				{
					memcpy( p, "//#", 3 );
					result = qtrue;
				}
				else
				{
					memcpy( p, "/*#", 3 );
				}
			}
			else
			{
				if( Scr_IsSyscallDefined( arg ) )
				{
					memcpy( p, "/*#", 3 );
				}
				else
				{
					memcpy( p, "//#", 3 );
					result = qtrue;
				}
			}
		}
		else
		{
			Com_Error( ERR_SCRIPT, "****** Script Pre-Compile Error ******\nUnknown macro function: %s \n%s", func, filepath );
		}
			
		Cmd_EndTokenizedString();

		if( end )
			*end = '\n';

		char * el = strstr( p, "#else" );
		p = strstr( p, "#endif" );
			
		if( p == NULL )
		{
			Com_Error( ERR_SCRIPT, "****** Script Pre-Compile Error ******\nExpected #endif, none found\n%s", filepath );
		}
			
		int pos1, pos2;
		pos1 = pos2 = 0;
		if( el != NULL )
		{
			pos1 = p - (char *)scr_buffer_handle;
			pos2 = el - (char *)scr_buffer_handle;
			if( pos2 < pos1 )
			{
				if( result )
				{
					memcpy( el, "/*#el", 5 );
				}
				else
				{
					memcpy( el, "#el*/", 5 );
				}
			}
		}
			
		if( el == NULL || pos2 > pos1 )
		{
			if( result )
			{
				memcpy( p, "//#eif", 6 );
			}
			else
			{
				memcpy( p, "#eif*/", 6 );
			}
		}
		else
		{
			if( result )
			{
				memcpy( p, "#eif*/", 6 );
			}
			else
			{
				memcpy( p, "//#eif", 6 );
			}
		}

		p = strstr( p, "#if" );
	}
#endif
}

unsigned int Scr_LoadScript(const char* scriptname)
{
    PrecacheEntry precache;

    return Scr_LoadScriptInternal(scriptname, &precache, 0);

}


void Scr_Sys_Error_Wrapper(const char *fmt, ...)
{
    va_list argptr;
    char com_errorMessage[4096];

    va_start(argptr, fmt);
    Q_vsnprintf(com_errorMessage, sizeof(com_errorMessage), fmt, argptr);
    va_end(argptr);

    Com_Error(ERR_SCRIPT, "%s", com_errorMessage);
}

/*
int GetArraySize(int aHandle)
{
    int size = gScrVarGlob.variables[aHandle].value.typeSize.size;
    return size;
}*/

/* only for debug */
/*
__regparm3 void VM_Notify_Hook(int entid, int constString, VariableValue *arguments)
{
    Com_Printf(CON_CHANNEL_SCRIPT,"^2Notify Entitynum: %d, EventString: %s\n", entid, SL_ConvertToString(constString));
    VM_Notify(entid, constString, arguments);
}*/



void RuntimeError_Debug(char *msg, char *pos, int a4)
{
    int i;

    Com_Printf(CON_CHANNEL_SCRIPT,"\n^1******* script runtime error *******\n%s: ", msg);
    Scr_PrintPrevCodePos(0, pos, a4);
    if (gScrVmPub.function_count)
    {
        for (i = gScrVmPub.function_count - 1; i > 0; --i)
        {
            Com_Printf(CON_CHANNEL_SCRIPT,"^1called from:\n");
            Scr_PrintPrevCodePos(0, gScrVmPub.function_frame_start[i].fs.pos, gScrVmPub.function_frame_start[i].fs.localId == 0);
        }
        Com_Printf(CON_CHANNEL_SCRIPT,"^1started from:\n");
        Scr_PrintPrevCodePos(0, gScrVmPub.function_frame_start[0].fs.pos, 1);
    }
    Com_Printf(CON_CHANNEL_SCRIPT,"^1************************************\n");
}

void RuntimeError(char *pos, int arg4, char *message, char *a4)
{
    int errtype;

    /* An ordinary script error must not become terminal just because it hit
     * the Scr_SetLoading window. The retained IW3 error path inlined into
     * _scr_vm.asm does "if (gScrVarPub.developer && gScrVmGlob.loading)
     * terminal_error = 1" before jumping out, and gScrVarPub.developer is
     * com_developer || com_logfile (Com_SetScriptSettings), so a production
     * server (developer 0, logfile on) promoted every bad cast or bad builtin
     * argument raised between G_InitGame and the end of the first SV_Frame --
     * i.e. while the players respawn after an S&D round's map_restart -- into
     * Com_Error(ERR_SCRIPT) and Sys_Error. T5 dropped that promotion
     * (OpenBLOPS cscr_vm.cpp Scr_ErrorInternal). Keep it only when errors are
     * meant to abort (abort_on_error = com_developer); Scr_TerminalError
     * (variable/memory exhaustion) and anything else that is terminal stays
     * fatal. */
    if (gScrVmPub.terminal_error && !gScrVmPub.abort_on_error && !Scr_IsExplicitTerminalError())
    {
        gScrVmPub.terminal_error = 0;
    }

    if (!gScrVarPub.developer && !gScrVmPub.terminal_error)
    {
        /* Production runs developer 0, and this early return used to make
         * every script runtime error invisible there (a zm actor thread that
         * died on its first frame left no trace in 40 logs).  Print the
         * message -- Scr_PrintPrevCodePos asserts developer, so only the
         * message -- with a per-process cap so a per-frame error cannot flood
         * the log.  Behaviour is otherwise unchanged: no abort, no Com_Error. */
        static int shown;
        if (shown < 64) {
            ++shown;
            Com_Printf(CON_CHANNEL_SCRIPT, "^1script runtime error (%d/64 shown at developer 0): %s%s%s\n",
                shown, message, a4 ? " -- " : "", a4 ? a4 : "");
            if (shown == 64)
                Com_Printf(CON_CHANNEL_SCRIPT, "^1script runtime errors: cap reached; further ones are silent until restart\n");
        }
        return;
    }

    if (gScrVmPub.debugCode)
    {
        Com_Printf(CON_CHANNEL_SCRIPT,"%s\n", message);
        if (!gScrVmPub.terminal_error)
        {
            return;
        }
    }
    else
    {
        RuntimeError_Debug(message, pos, arg4);
        if (!gScrVmPub.abort_on_error && !gScrVmPub.terminal_error)
        {
            return;
        }
    }

    if (gScrVmPub.terminal_error)
    {
        errtype = 5;
    }
    else
    {
        errtype = 4;
    }

    if (a4)
    {
        Com_Error(errtype, "script runtime error\n(see console for details)\n%s\n%s", message, a4);
    }
    else
    {
        Com_Error(errtype, "script runtime error\n(see console for details)\n%s", message);
    }
}



gentity_t *VM_GetGEntityForNum(scr_entref_t num)
{
    if (num.classnum)
    {
        Scr_Error("Not an entity");
        return NULL;
    }

    return &g_entities[num.entnum];
}

gclient_t *VM_GetGClientForEntity(gentity_t *ent)
{
    return ent->client;
}

gclient_t *VM_GetGClientForEntityNumber(scr_entref_t num)
{
    return VM_GetGClientForEntity(VM_GetGEntityForNum(num));
}

client_t *VM_GetClientForEntRef(scr_entref_t ref) //Very bad, this must go
{
    return &svs.clients[ref.entnum];
}

gentity_t *VM_GetGEntityForEntRef(scr_entref_t num)
{
    if (num.classnum)
    {
        Scr_Error("Not an entity");
        return NULL;
    }

    return &g_entities[num.entnum];
}

gclient_t *VM_GetGClientForEntRef(scr_entref_t ref)
{
    return VM_GetGClientForEntity(VM_GetGEntityForEntRef(ref));
}



void Scr_YYACError(const char* fmt, ...)
{
    va_list argptr;
    char com_errorMessage[4096];

    va_start(argptr, fmt);
    Q_vsnprintf(com_errorMessage, sizeof(com_errorMessage), fmt, argptr);
    va_end(argptr);

    Com_Error(ERR_SCRIPT, "%s", com_errorMessage);
}
