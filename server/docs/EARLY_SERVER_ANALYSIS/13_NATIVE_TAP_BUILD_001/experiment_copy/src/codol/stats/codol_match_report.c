/* See codol_match_report.h for the lobby contract this file implements.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_match_report.h"
#include "codol_profile.h"
#include "codol_script_profile_vm.h"
#include "codol_stats.h"
#include "codol_matchdata_server.h"
#include "codol_assets.h"
#include "codol_weapon_compose.h"
#include "scr_vm.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include "cvar.h"
#include "filesystem.h"
#include "server.h"
#include "g_shared.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <limits.h>
#include <math.h>

#define CODOL_MATCH_REPORT_NAME "match_report.json"

/* The lifetime counters the client's career page reads out of its secure
 * profile. Every one is resolved BY NAME through the mounted
 * mp/playersecuredata.def, never by offset: a name this DDL does not declare is
 * skipped and named once in the console, so the list can be wrong without being
 * dangerous. The scripts are what maintain them - _persistence::statAdd /
 * statSet from _damage.gsc, _gamescore.gsc and _gamelogic.gsc write straight
 * into the session secure blob through setPlayerData - so this file only has to
 * measure, exactly as it already does for experience: value now minus value at
 * profile attach. Nothing here re-counts a kill.
 *
 * The names are this client's, taken from the decoded
 * mp/playersecuredata.def (v11, checksum 158043991, 6665 bytes, 1680 leaves,
 * from the PATCH zone - the base zone ships a different def, checksum
 * 1491960907). IW4 names CODOL does not declare - misses, timePlayedAllies,
 * timePlayedOpfor, timePlayedOther, restXPGoal and the round subtree - are deliberately NOT
 * in this list: setPlayerData routes them to the legacy session store that is
 * discarded at disconnect, so measuring them would always report nothing.
 *
 * Ratios are deliberately absent. `accuracy` is stored x10000 and `winRatio`
 * x10, the scripts recompute them with updatePersRatio, and the delta of a
 * ratio is meaningless; the lobby recomputes both from the lifetime totals.
 * `kdRatio` is not even read by the career page - CareerController divides
 * kills by deaths in ActionScript - so nothing needs to maintain it. */
static const char *const codol_match_report_stats[] = {
    "timePlayedTotal", "timePlayed", "timePlayedOverAll",
    "score", "kills", "deaths", "assists", "headshots", "suicides",
    "totalShots", "hits",
    "wins", "losses", "ties", "escapes",
    "winStreak", "killStreak",
    "objectives", "bombPlants", "bombDefuses", "confirmed", "denied"
};
#define CODOL_MATCH_REPORT_STATS     (sizeof(codol_match_report_stats)/sizeof(codol_match_report_stats[0]))
#define CODOL_MATCH_REPORT_DEPARTED 32
/* Challenges one player advanced in one match. CoDOL ships 611 of them, but a
 * single match moves a handful; 64 is far above anything observed and keeps
 * the row small enough to stay static on a 32-bit server. Overflow is
 * reported, never silently dropped. */
#define CODOL_MATCH_REPORT_CHALLENGES 64
/* mp/playersecuredata.def declares challenges[1000]; the id is column 4 of
 * mp/allChallengesTable.csv and doubles as the storage address. */
#define CODOL_MATCH_REPORT_CHALLENGE_IDS 1000
#define CODOL_MATCH_REPORT_NAME_CHARS 36
/* Distinct weapons one player killed with in one match. Overflow is reported,
 * never silently dropped. Names are base weapon names (ak47_mp), which fit. */
#define CODOL_MATCH_REPORT_WEAPONS 24
#define CODOL_MATCH_REPORT_WEAPON_CHARS 40
/* 64 live slots plus 32 frozen rows at roughly 230 bytes each, plus up to
 * ~1 KB of weapon XP per human. Static rather than automatic: the game loop is
 * single threaded and this is not a size to put on a 32-bit server stack. */
#define CODOL_MATCH_REPORT_BYTES 65536

typedef struct {
    unsigned char used;
    unsigned char bot;
    unsigned char baseline_valid;
    unsigned char slot;          /* the client number this row played in */
    uint64_t uid;
    char name[CODOL_MATCH_REPORT_NAME_CHARS];
    int team;
    int baseline_xp;
    /* What this row already owns independently of the engine slot: earlier
     * stays in this match, minus whatever a previous report already carried.
     * Counters may go negative here; the sum with the engine never does. */
    int carry_xp, carry_kills, carry_deaths, carry_assists, carry_score;
    /* Departed rows only: the settled counters, engine plus carry, taken at
     * the moment the slot stopped being this player's. */
    int kills, deaths, assists, score;
    /* Career counters, measured the same way as experience: the value at
     * profile attach, plus whatever an earlier stay in this match already
     * settled. stat_valid says the DDL actually declares that member. */
    int stat_base[CODOL_MATCH_REPORT_STATS];
    int stat_carry[CODOL_MATCH_REPORT_STATS];
    unsigned char stat_valid[CODOL_MATCH_REPORT_STATS];
    /* Challenge progress this row earned, id -> delta, carried across a
     * reconnect exactly as stat_carry is. Only earlier stays live here; the
     * current stay is diffed at emit against challenge_base, which a written
     * report advances, so a second report in one match cannot re-count it. */
    unsigned short challenge_id[CODOL_MATCH_REPORT_CHALLENGES];
    int challenge_carry[CODOL_MATCH_REPORT_CHALLENGES];
    unsigned char challenges;
    unsigned char challenge_overflow;
    /* Weapon XP this row earned, base weapon name -> amount. Nothing in the
     * secure profile holds it - C1 reads a weapon's level only from the
     * lobby's inventory record (alpha0022 career/weapon_leveling.py) - so it is
     * accumulated here as _damage.gsc credits each kill, carried across a
     * reconnect, and zeroed once a report has carried it. */
    char weapon_name[CODOL_MATCH_REPORT_WEAPONS][CODOL_MATCH_REPORT_WEAPON_CHARS];
    int weapon_xp[CODOL_MATCH_REPORT_WEAPONS];
    unsigned char weapons;
    unsigned char weapon_overflow;
} codol_match_row_t;

static codol_match_row_t live[MAX_CLIENTS];
static codol_match_row_t departed[CODOL_MATCH_REPORT_DEPARTED];
/* Challenge progress a written report already carried, per live slot. Until the
 * first report of a stay this is unset and the attached profile is the
 * baseline; once a report is written, the session values it measured become
 * the baseline, so the next report (a map change after gameended, or a player
 * leaving afterwards) holds only what accrued since. The lobby folds every
 * spooled report, so re-reporting a stay would credit it twice. A negative
 * entry is an id that could not be read then and is skipped. */
static float challenge_base[MAX_CLIENTS][CODOL_MATCH_REPORT_CHALLENGE_IDS];
static unsigned char challenge_base_valid[MAX_CLIENTS];

static const char *report_directory(void)
{
    cvar_t *directory = Cvar_FindVar("codol_profilePath");
    return (directory && directory->string && *directory->string) ? directory->string : NULL;
}

/* The XP the client's progression currently stands at, read back through the
 * same recovered C1 conversion _rank.gsc's getRankExperience uses, so a value
 * this file compares was produced by the identical rule that produced the one
 * the script saw. The blob is the session view: setRankExperience edits that,
 * never the attached bytes. */
static int client_total_xp(unsigned client, int *out)
{
    const codol_structured_schema_t *schema;
    const codol_engine_table_t *table;
    const uint8_t *blob;
    int rank, total;
    schema = CODOL_ScriptProfileSchema(CODOL_PROFILE_SECURE);
    blob = CODOL_ScriptProfileBlob(client, CODOL_PROFILE_SECURE);
    if (!schema || !blob || CODOL_LoadEngineStringTable("mp/rankTable.csv", &table) != 1) return 0;
    if (!CODOL_ProfileExperience(blob, CODOL_STATS_SIZE, schema, table, &rank, &total)) return 0;
    *out = total;
    return 1;
}

/* NA_BOT is zero, and so is NA_BAD (sys_net.h:53-54), so an un-set-up netchan
 * reads as a bot. SV_DirectConnect does not call Netchan_Setup until
 * sv_client.c:569, well after it attaches the secure profile at :505, which
 * makes this answer worthless during a connect and correct only once the
 * client is really connected. Never latch it; ask when the netchan is real. */
/* One named counter out of the client's session secure profile, normalised to
 * an integer. Kinds 0/1/2/9 are int32/byte/bool/short and are the value itself.
 *
 * Kind 8 is float32, and it is NOT an exotic case to refuse: this DDL stores
 * `kills` and `wins` - the two headline numbers on the career page - as floats,
 * exactly as the GSC field for sess.kills is F_FLOAT. CODOL_StructuredReadScalar
 * hands back the raw bits, so they are reinterpreted and rounded here. A
 * nonfinite or out-of-range float is refused rather than truncated into
 * nonsense. A string or aggregate member is not a counter and is refused. */
static int read_secure_stat(unsigned client, const char *name, int *out)
{
    const codol_structured_definition_t *def;
    const uint8_t *record;
    size_t capacity;
    codol_structured_path_t path;
    codol_structured_field_t field;
    uint32_t bits = 0;
    path.name = name; path.index = 0;
    if (!CODOL_ScriptProfileView(client, CODOL_PROFILE_SECURE, &def, &record, &capacity)) return 0;
    if (!CODOL_ResolveStructuredField(def, &path, 1, &field)) return 0;
    if (field.type.kind != 0 && field.type.kind != 1 && field.type.kind != 2 &&
        field.type.kind != 8 && field.type.kind != 9) return 0;
    if (!CODOL_StructuredReadScalar(&def->layout, field.type.kind, field.logical_index,
                                    record, capacity, &bits)) return 0;
    if (field.type.kind == 8) {
        float value;
        memcpy(&value, &bits, sizeof(value));
        if (!(value >= 0.0f) || !(value <= 2147483000.0f)) return 0;  /* rejects NaN too */
        *out = (int)(value + 0.5f);
        return 1;
    }
    if (bits > (uint32_t)INT_MAX) return 0;
    *out = (int)bits;
    return 1;
}

/* CHALLENGE EGRESS.
 *
 * CoDOL keeps challenge progress as one cumulative float per challenge in the
 * secure profile's challenges[1000], indexed by the numeric id in column 4 of
 * mp/allChallengesTable.csv. The GSC accessors in _missions.gsc write exactly
 * that member, so a tier earned in this match is the difference between the
 * session blob the scripts edited and the pristine bytes the lobby attached.
 *
 * Diffing those two is the whole mechanism: the attached copy is immutable for
 * the life of the attachment (codol_profile_clients.c keeps `data` and
 * `session` apart precisely so every reader sees edits without altering the
 * attached bytes), so no baseline of our own is needed and the measurement is
 * idempotent. Nothing here writes a profile - the lobby owns persistence, and
 * this file only reports.
 *
 * ROUNDING: the member is a float and the lobby accumulates integers, so a
 * fractional delta is reported only once it reaches a whole unit. Progress is
 * authored in whole events, so this is a guard, not a policy. */
static int challenge_view(const uint8_t *blob, const codol_structured_definition_t **def,
                          const uint8_t **record, size_t *capacity)
{
    const codol_structured_schema_t *schema = CODOL_ScriptProfileSchema(CODOL_PROFILE_SECURE);
    if (!schema || !blob) return 0;
    return CODOL_ProfileRecord(blob, CODOL_STATS_SIZE, schema, def, record, capacity);
}

static int challenge_value(const codol_structured_definition_t *def, const uint8_t *record,
                           size_t capacity, unsigned id, double *out)
{
    /* Two path steps, as getPlayerData( "challenges", id ) builds them: the
     * member, then the index into it. A single step naming "challenges"
     * resolves to the array itself (the resolver never reads a named step's
     * index), so every id failed here and no report ever carried a challenge. */
    codol_structured_path_t path[2];
    codol_structured_field_t field;
    uint32_t bits = 0;
    float value;
    path[0].name = "challenges";
    path[0].index = 0;
    path[1].name = NULL;
    path[1].index = (int)id;
    if (!CODOL_ResolveStructuredField(def, path, 2, &field)) return 0;
    if (field.type.kind != 8) return 0;
    if (!CODOL_StructuredReadScalar(&def->layout, field.type.kind, field.logical_index,
                                    record, capacity, &bits)) return 0;
    memcpy(&value, &bits, sizeof(value));
    if (!(value >= 0.0f) || !(value <= 2147483000.0f)) return 0;   /* rejects NaN too */
    *out = (double)value;
    return 1;
}

/* Merge one id's delta into a row, adding to an id already present. */
static void challenge_merge(codol_match_row_t *row, unsigned id, int delta)
{
    unsigned i;
    if (delta <= 0) return;
    for (i = 0; i < row->challenges; ++i) {
        if (row->challenge_id[i] == (unsigned short)id) {
            row->challenge_carry[i] += delta;
            return;
        }
    }
    if (row->challenges >= CODOL_MATCH_REPORT_CHALLENGES) { row->challenge_overflow = 1; return; }
    row->challenge_id[row->challenges] = (unsigned short)id;
    row->challenge_carry[row->challenges] = delta;
    ++row->challenges;
}

/* This stay's deltas, session minus attached (or minus what the last written
 * report measured, see challenge_base). `sink` receives each one. Returns the
 * number reported, or -1 when the client has no attached profile (a bot, or a
 * slot whose profile never bound) - not the same as zero. */
static int challenge_stay_deltas(unsigned client, void *context,
                                 void (*sink)(void *, unsigned, int))
{
    const codol_structured_definition_t *now_def, *was_def;
    const uint8_t *now_rec, *was_rec, *now_blob, *was_blob;
    size_t now_cap, was_cap;
    unsigned id;
    int found = 0;
    if (client >= MAX_CLIENTS) return -1;
    now_blob = CODOL_ClientSecureProfile(client, NULL);
    was_blob = CODOL_ClientSecureProfileAttached(client, NULL);
    if (!now_blob || !was_blob) return -1;
    if (now_blob == was_blob) return 0;      /* no script ever edited this profile */
    if (!challenge_view(now_blob, &now_def, &now_rec, &now_cap)) return -1;
    if (!challenge_view(was_blob, &was_def, &was_rec, &was_cap)) return -1;
    for (id = 0; id < CODOL_MATCH_REPORT_CHALLENGE_IDS; ++id) {
        double now_value = 0.0, was_value = 0.0;
        int delta;
        if (!challenge_value(now_def, now_rec, now_cap, id, &now_value)) continue;
        if (challenge_base_valid[client]) {
            if (challenge_base[client][id] < 0.0f) continue;
            was_value = (double)challenge_base[client][id];
        } else if (!challenge_value(was_def, was_rec, was_cap, id, &was_value)) continue;
        if (now_value <= was_value) continue;
        delta = (int)(now_value - was_value);
        if (delta <= 0) continue;
        sink(context, id, delta);
        ++found;
    }
    return found;
}

static void challenge_into_row(void *context, unsigned id, int delta)
{
    challenge_merge((codol_match_row_t *)context, id, delta);
}

static void challenge_count(void *context, unsigned id, int delta)
{
    (void)id;
    *(int *)context += delta;
}

/* Make the client's current challenge values the baseline of its next report. */
static void challenge_rebase(unsigned client)
{
    const codol_structured_definition_t *def;
    const uint8_t *record, *blob;
    size_t capacity;
    unsigned id;
    if (client >= MAX_CLIENTS) return;
    blob = CODOL_ClientSecureProfile(client, NULL);
    if (!blob || !challenge_view(blob, &def, &record, &capacity)) return;
    for (id = 0; id < CODOL_MATCH_REPORT_CHALLENGE_IDS; ++id) {
        double value = 0.0;
        challenge_base[client][id] =
            challenge_value(def, record, capacity, id, &value) ? (float)value : -1.0f;
    }
    challenge_base_valid[client] = 1;
}

/* Names the DDL does not declare, once per server run, so a wrong entry in the
 * list above is visible instead of silently reporting nothing. */
static void report_missing_stat(unsigned index)
{
    static unsigned char announced[CODOL_MATCH_REPORT_STATS];
    if (index >= CODOL_MATCH_REPORT_STATS || announced[index]) return;
    announced[index] = 1;
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL match report: mp/playersecuredata.def declares no scalar '%s'; "
        "that career counter will not be reported\n", codol_match_report_stats[index]);
}

static int client_is_bot(unsigned client)
{
    return svs.clients[client].netchan.remoteAddress.type == NA_BOT;
}

static int client_connected(unsigned client)
{
    if (!sv_maxclients || client >= (unsigned)sv_maxclients->integer) return 0;
    return svs.clients[client].state >= CS_CONNECTED;
}

/* The engine's own per-match counters. sess.kills is a float on this build
 * (the C1 script field is F_FLOAT); the report is an integer scoreboard, so it
 * is truncated exactly once, here. */
static void client_counters(unsigned client, int *kills, int *deaths, int *assists, int *score, int *team)
{
    const clientSession_t *sess;
    *kills = *deaths = *assists = *score = 0;
    *team = TEAM_FREE;
    if (!level.clients) return;
    sess = &level.clients[client].sess;
    *kills = (int)sess->kills;
    *deaths = sess->deaths;
    *assists = sess->assists;
    *score = sess->score;
    *team = sess->cs.team;
}

static codol_match_row_t *find_departed(uint64_t uid)
{
    unsigned i;
    if (!uid) return NULL;
    for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i)
        if (departed[i].used && departed[i].uid == uid) return &departed[i];
    return NULL;
}

void CODOL_MatchReportClientAttached(unsigned client, uint64_t uid)
{
    codol_match_row_t row;
    codol_match_row_t *earlier;
    int total = 0;
    unsigned index;
    if (client >= MAX_CLIENTS) return;
    memset(&row, 0, sizeof(row));
    row.used = 1;
    row.slot = (unsigned char)client;
    row.uid = uid;
    /* A row exists only because a secure profile attached for a real account:
     * CODOL_AutoBindClientSecureProfile refuses a zero uid and bots have none.
     * So every stored row is a human. Asking client_is_bot() here is the bug
     * that made a connecting player report as a bot and lose its whole match. */
    row.baseline_valid = (unsigned char)(client_total_xp(client, &total) ? 1 : 0);
    row.baseline_xp = row.baseline_valid ? total : 0;
    for (index = 0; index < CODOL_MATCH_REPORT_STATS; ++index) {
        int value = 0;
        if (read_secure_stat(client, codol_match_report_stats[index], &value)) {
            row.stat_base[index] = value;
            row.stat_valid[index] = 1;
        } else report_missing_stat(index);
    }
    /* A reconnect inside one match is the same player, not a second row. Adopt
     * what the earlier stay accumulated and retire that departed entry. */
    earlier = find_departed(uid);
    if (earlier) {
        row.carry_xp = earlier->carry_xp;
        row.carry_kills = earlier->kills;
        row.carry_deaths = earlier->deaths;
        row.carry_assists = earlier->assists;
        row.carry_score = earlier->score;
        for (index = 0; index < CODOL_MATCH_REPORT_STATS; ++index)
            row.stat_carry[index] = earlier->stat_carry[index];
        for (index = 0; index < earlier->challenges; ++index) {
            row.challenge_id[index] = earlier->challenge_id[index];
            row.challenge_carry[index] = earlier->challenge_carry[index];
        }
        row.challenges = earlier->challenges;
        row.challenge_overflow = earlier->challenge_overflow;
        memcpy(row.weapon_name, earlier->weapon_name, sizeof(row.weapon_name));
        memcpy(row.weapon_xp, earlier->weapon_xp, sizeof(row.weapon_xp));
        row.weapons = earlier->weapons;
        row.weapon_overflow = earlier->weapon_overflow;
        memset(earlier, 0, sizeof(*earlier));
    }
    live[client] = row;
    /* A new attachment is measured from its own bytes again. */
    challenge_base_valid[client] = 0;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL match report: client %u uid %llu baseline %d XP%s\n",
        client, (unsigned long long)uid, row.baseline_xp,
        row.baseline_valid ? "" : " (UNREADABLE - this player's XP cannot be reported)");
}

static int settle(int engine, int *carry)
{
    /* The carry is negative for everything an earlier report already took, so
     * the settled figure is what this row still owes the lobby. */
    int value = engine + *carry;
    *carry = 0;
    return value > 0 ? value : 0;
}

static void freeze(unsigned client, codol_match_row_t *out)
{
    codol_match_row_t row = live[client];
    int total = 0, team = 0;
    unsigned index;
    client_counters(client, &row.kills, &row.deaths, &row.assists, &row.score, &team);
    row.team = team;
    row.slot = (unsigned char)client;
    if (svs.clients[client].name[0])
        Q_strncpyz(row.name, svs.clients[client].name, sizeof(row.name));
    /* Fold the carry in now: once the slot is released the engine counters are
     * gone, and a frozen row that ignored the carry would re-report counters a
     * previous report already took. */
    row.kills = settle(row.kills, &row.carry_kills);
    row.deaths = settle(row.deaths, &row.carry_deaths);
    row.assists = settle(row.assists, &row.carry_assists);
    row.score = settle(row.score, &row.carry_score);
    if (row.baseline_valid && client_total_xp(client, &total) && total > row.baseline_xp)
        row.carry_xp += total - row.baseline_xp;
    for (index = 0; index < CODOL_MATCH_REPORT_STATS; ++index) {
        int value = 0;
        if (!row.stat_valid[index]) continue;
        if (read_secure_stat(client, codol_match_report_stats[index], &value) &&
            value > row.stat_base[index])
            row.stat_carry[index] += value - row.stat_base[index];
        row.stat_valid[index] = 0;   /* the slot's profile is about to go */
    }
    /* Settle the challenge deltas the same way: once the slot is released the
     * session blob is freed and the difference is unrecoverable. */
    challenge_stay_deltas(client, &row, challenge_into_row);
    row.baseline_valid = 0;
    *out = row;
}

void CODOL_MatchReportClientDropped(unsigned client)
{
    codol_match_row_t row;
    unsigned i;
    if (client >= MAX_CLIENTS || !live[client].used) return;
    freeze(client, &row);
    memset(&live[client], 0, sizeof(live[client]));
    challenge_base_valid[client] = 0;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL match report: client %u uid %llu left with %d XP, k%d d%d a%d s%d\n",
        client, (unsigned long long)row.uid, row.carry_xp, row.kills, row.deaths,
        row.assists, row.score);
    for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i) {
        if (departed[i].used) continue;
        departed[i] = row;
        return;
    }
    Com_PrintWarning(CON_CHANNEL_SERVER,
        "CoDOL match report: more than %u players left this match; %s is not in the report\n",
        (unsigned)CODOL_MATCH_REPORT_DEPARTED, row.name[0] ? row.name : "a departed player");
}

int CODOL_MatchReportHumansConnected(void)
{
    unsigned i;
    if (!sv_maxclients) return 0;
    for (i = 0; i < (unsigned)sv_maxclients->integer && i < MAX_CLIENTS; ++i) {
        if (!client_connected(i)) continue;
        /* An attached account is a human whatever its netchan currently says;
         * the netchan test only has to decide the slots that own no row. */
        if (live[i].used || !client_is_bot(i)) return 1;
    }
    return 0;
}

/* The weapon a kill is credited to, keyed the way the lobby keys weapon XP:
 * the base weapon name. A C1 loadout gun is a composed name
 * ("*a 32 5 14 4 ...", see codol_weapon_compose.h) whose base index names the
 * gun the level belongs to; attachments and camo do not level separately.
 * Anything else - a grenade, a killstreak - is already its own name and is
 * passed through; the lobby ignores the ones its weapon table does not list.
 * 1 resolved, 0 nothing to credit. */
static int weapon_credit_key(const char *weapon, char *out, size_t size)
{
    codol_composed_weapon_t composed;
    const char *base = NULL;
    size_t n;
    if (!weapon || !*weapon || !Q_stricmp(weapon, "none")) return 0;
    switch (CODOL_ParseComposedWeaponName(weapon, &composed)) {
    case 1:
        if (CODOL_ComposedWeaponBaseName(composed.base, &base) != 1 || !base || !*base)
            return 0;
        weapon = base;
        break;
    case 0:
        break;
    default:
        return 0;
    }
    Q_strncpyz(out, weapon, (int)size);
    for (n = 0; out[n]; ++n)
        if (out[n] >= 'A' && out[n] <= 'Z') out[n] = (char)(out[n] - 'A' + 'a');
    return 1;
}

int CODOL_MatchReportCreditWeaponXP(unsigned client, const char *weapon, int amount)
{
    codol_match_row_t *row;
    char key[CODOL_MATCH_REPORT_WEAPON_CHARS];
    unsigned i;
    if (client >= MAX_CLIENTS || amount <= 0) return 0;
    row = &live[client];
    /* Only an attached account owns a row; bots and unauthenticated slots
     * have nowhere for weapon XP to go. */
    if (!row->used) return 0;
    if (!weapon_credit_key(weapon, key, sizeof(key))) return 0;
    for (i = 0; i < row->weapons; ++i) {
        if (strcmp(row->weapon_name[i], key)) continue;
        row->weapon_xp[i] = row->weapon_xp[i] > INT_MAX - amount ? INT_MAX
                                                                : row->weapon_xp[i] + amount;
        return 1;
    }
    if (row->weapons >= CODOL_MATCH_REPORT_WEAPONS) {
        if (!row->weapon_overflow)
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL match report: client %u killed with more than %u weapons; %s earns no "
                "weapon XP this match\n", client, (unsigned)CODOL_MATCH_REPORT_WEAPONS, key);
        row->weapon_overflow = 1;
        return 0;
    }
    Q_strncpyz(row->weapon_name[row->weapons], key, sizeof(row->weapon_name[0]));
    row->weapon_xp[row->weapons] = amount;
    ++row->weapons;
    return 1;
}

/* self codol_creditWeaponXP(<weapon name>, <amount>)
 *
 * _damage.gsc handleNormalDeath calls this once per enemy kill with the
 * killing weapon and the gametype's flat "kill" score value - deliberately not
 * the giveRankXP amount, which also carries headshot, last-stand, streak and
 * xpScaler bonuses. Returns 1 when the XP was recorded for the lobby. */
void CODOL_Scr_CreditWeaponXP(scr_entref_t ref)
{
    if (ref.classnum || ref.entnum >= MAX_CLIENTS || !g_entities[ref.entnum].client ||
        !g_entities[ref.entnum].r.inuse) {
        Scr_Error("codol_creditWeaponXP: entity must be a player entity");
        return;
    }
    if (Scr_GetNumParam() != 2) {
        Scr_Error("codol_creditWeaponXP requires a weapon name and an amount");
        return;
    }
    Scr_AddInt(CODOL_MatchReportCreditWeaponXP((unsigned)ref.entnum, Scr_GetString(0),
                                               Scr_GetInt(1)));
}

/* ------------------------------------------------------------------------- */
/* JSON writing                                                              */
/* ------------------------------------------------------------------------- */

typedef struct { char *data; size_t size, used; int overflow; } buffer_t;

static void append(buffer_t *b, const char *text, size_t length)
{
    if (b->overflow || b->used + length >= b->size) { b->overflow = 1; return; }
    memcpy(b->data + b->used, text, length);
    b->used += length;
    b->data[b->used] = 0;
}

static void append_text(buffer_t *b, const char *text) { append(b, text, strlen(text)); }

static void append_int(buffer_t *b, int value)
{
    char text[16];
    int n = snprintf(text, sizeof(text), "%d", value);
    if (n <= 0 || (size_t)n >= sizeof(text)) { b->overflow = 1; return; }
    append(b, text, (size_t)n);
}

/* A player name is arbitrary client text, including C1 colour escapes and
 * whatever bytes survived the name filter. Emit it as a JSON string the lobby's
 * json.loads accepts: quote/backslash escaped, every control byte as \u00XX,
 * and every byte above 0x7f as \u00XX too, which is the latin-1 reading the
 * lobby already uses for names elsewhere. */
static void append_string(buffer_t *b, const char *text)
{
    const unsigned char *p;
    append_text(b, "\"");
    for (p = (const unsigned char *)(text ? text : ""); *p; ++p) {
        char escape[8];
        if (*p == '"' || *p == '\\') { escape[0] = '\\'; escape[1] = (char)*p; append(b, escape, 2); }
        else if (*p >= 0x20 && *p < 0x7f) append(b, (const char *)p, 1);
        else { snprintf(escape, sizeof(escape), "\\u%04x", (unsigned)*p); append(b, escape, 6); }
    }
    append_text(b, "\"");
}

static void append_uid(buffer_t *b, uint64_t uid)
{
    char text[24];
    int n = snprintf(text, sizeof(text), "%llu", (unsigned long long)uid);
    if (n <= 0 || (size_t)n >= sizeof(text)) { b->overflow = 1; return; }
    append_text(b, "\"");
    append(b, text, (size_t)n);
    append_text(b, "\"");
}

static const char *outcome_for(int team, const int scores[2])
{
    /* The team a row played for against the other one. TEAM_RED is bank 1 and
     * TEAM_BLUE bank 2, the same pairing CODOL_PublishTeamScores uses. */
    int mine, theirs;
    if (team == TEAM_RED) { mine = scores[0]; theirs = scores[1]; }
    else if (team == TEAM_BLUE) { mine = scores[1]; theirs = scores[0]; }
    else return "tie";
    if (mine > theirs) return "win";
    if (mine < theirs) return "loss";
    return "tie";
}

/* `client` is the engine slot this row is still playing in, or -1 for a
 * departed row or a bot. A live row's challenge deltas are diffed here, from
 * the baseline the previous report left (challenge_base), rather than stored. */
static void append_row(buffer_t *b, int slot, const codol_match_row_t *row,
                       int kills, int deaths, int assists, int score, int earned,
                       const int *stats, const int scores[2], int first, int client)
{
    codol_match_row_t merged;
    if (client >= 0) {
        merged = *row;
        challenge_stay_deltas((unsigned)client, &merged, challenge_into_row);
        row = &merged;
    }
    if (!first) append_text(b, ",\n  ");
    append_text(b, "{\"slot\": ");
    append_int(b, slot);
    append_text(b, ", \"name\": ");
    append_string(b, row->name[0] ? row->name : "player");
    append_text(b, ", \"bot\": ");
    append_text(b, row->bot ? "true" : "false");
    if (!row->bot && row->uid) { append_text(b, ", \"uid\": "); append_uid(b, row->uid); }
    append_text(b, ", \"team\": ");
    append_int(b, row->team);
    append_text(b, ", \"kills\": ");
    append_int(b, kills);
    append_text(b, ", \"deaths\": ");
    append_int(b, deaths);
    append_text(b, ", \"assists\": ");
    append_int(b, assists);
    append_text(b, ", \"score\": ");
    append_int(b, score);
    append_text(b, ", \"outcome\": ");
    append_string(b, outcome_for(row->team, scores));
    if (!row->bot && stats) {
        /* The career counters this match added, measured out of the secure
         * profile the scripts maintain. Absent members are simply absent from
         * the object; the lobby credits what it is given. */
        unsigned n; int first = 1;
        append_text(b, ", \"lifetime\": {");
        for (n = 0; n < CODOL_MATCH_REPORT_STATS; ++n) {
            if (stats[n] <= 0) continue;
            if (!first) append_text(b, ", ");
            first = 0;
            append_string(b, codol_match_report_stats[n]);
            append_text(b, ": ");
            append_int(b, stats[n]);
        }
        append_text(b, "}");
    }
    if (!row->bot) {
        /* kill_xp/match_bonus are the retired Python writer's split of the same
         * total. This server has no separate end-of-match bonus stage: the
         * vendor scripts award it through giveRankXP like any other event, so
         * it is already inside the measured delta and is not re-derived here.
         * applied_live stays 0 - nothing was persisted outside this report. */
        append_text(b, ", \"xp\": {\"kill_xp\": ");
        append_int(b, earned);
        append_text(b, ", \"match_bonus\": 0, \"total\": ");
        append_int(b, earned);
        append_text(b, ", \"applied_live\": 0}");
        /* The lobby folds this into players/<uid>.json and re-renders the
         * secure blob from it; see alpha0022 rank_writeback._merge_progression
         * and progression.credit(). Keys are the numeric challenge ids, the
         * same addresses these deltas were measured at. Absent when nothing
         * moved, so an ordinary match adds nothing to the file. */
        /* "weapons" is the base weapon name -> weapon XP this match, which the
         * lobby adds to the profile and serves as the inventory record's xp
         * field, the only thing C1 derives a weapon level from. */
        if (row->challenges || row->weapons) {
            unsigned c;
            append_text(b, ", \"progression\": {");
            if (row->challenges) {
                append_text(b, "\"challenges\": {");
                for (c = 0; c < row->challenges; ++c) {
                    if (c) append_text(b, ", ");
                    append_text(b, "\"");
                    append_int(b, (int)row->challenge_id[c]);
                    append_text(b, "\": ");
                    append_int(b, row->challenge_carry[c]);
                }
                append_text(b, "}");
            }
            if (row->weapons) {
                if (row->challenges) append_text(b, ", ");
                append_text(b, "\"weapons\": {");
                for (c = 0; c < row->weapons; ++c) {
                    if (c) append_text(b, ", ");
                    append_string(b, row->weapon_name[c]);
                    append_text(b, ": ");
                    append_int(b, row->weapon_xp[c]);
                }
                append_text(b, "}");
            }
            append_text(b, "}");
        }
        if (row->challenge_overflow)
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL match report: %s advanced more than %u challenges; the rest "
                "are not in the report\n", row->name[0] ? row->name : "a player",
                (unsigned)CODOL_MATCH_REPORT_CHALLENGES);
    }
    append_text(b, "}");
}

static int write_file(const char *directory, const char *name, const char *text, size_t length)
{
    char path[MAX_OSPATH], temporary[MAX_OSPATH];
    FILE *file;
    int n;
    n = snprintf(path, sizeof(path), "%s/%s", directory, name);
    if (n <= 0 || (size_t)n >= sizeof(path)) return 0;
    n = snprintf(temporary, sizeof(temporary), "%s/%s.tmp", directory, name);
    if (n <= 0 || (size_t)n >= sizeof(temporary)) return 0;
    FS_ReplaceSeparators(path);
    FS_ReplaceSeparators(temporary);
    file = fopen(temporary, "wb");
    if (!file) return 0;
    if (fwrite(text, 1, length, file) != length) { fclose(file); remove(temporary); return 0; }
    if (fclose(file)) { remove(temporary); return 0; }
    /* POSIX rename replaces in one step. Windows refuses a rename onto an
     * existing name, so the old report is removed first; a reader can then see
     * the complete old file, the complete new file, or no file, but never a
     * half-written one - which is all the lobby's consume-by-rename needs. */
    if (rename(temporary, path)) {
        remove(path);
        if (rename(temporary, path)) { remove(temporary); return 0; }
    }
    return 1;
}

/* Where this report goes.
 *
 * match_report.json is ONE slot and the lobby empties it only when a client
 * asks it for mpdata_s or its marketplace record - that is, when a player is
 * back in the front end. With a map rotation (codol_exitToLobby 0) nobody goes
 * back between matches, so every gameended report replaced the unconsumed one
 * before it: on 2026-09-27 the lobby ledger holds only the last report of each
 * rotation run and 16700 + 10940 XP of earlier matches never arrived. A second
 * match server sharing the resources directory (sh1x-rollout.sh) races for the
 * same name as well.
 *
 * So, by default, every report gets its own name that sorts in write order:
 * match_report.q.<epoch>.<port>.<seq>.json. The lobby folds them oldest
 * first. codol_matchReportSpool 0 restores the single legacy file for a lobby
 * that does not read the spool yet. */
static int report_file_name(char *out, size_t size)
{
    static cvar_t *spool;
    static unsigned sequence;
    cvar_t *port;
    int n;
    if (!spool)
        spool = Cvar_RegisterBool("codol_matchReportSpool", qtrue, CVAR_ARCHIVE,
            "Write every match report under its own name for the lobby to fold in order");
    if (!spool->boolean) {
        Q_strncpyz(out, CODOL_MATCH_REPORT_NAME, (int)size);
        return 1;
    }
    port = Cvar_FindVar("net_port");
    n = snprintf(out, size, "match_report.q.%010lu.%05d.%06u.json",
                 (unsigned long)Com_GetRealtime(), port ? port->integer : 0,
                 ++sequence % 1000000u);
    return n > 0 && (size_t)n < size;
}

int CODOL_WriteMatchReport(const char *reason)
{
    static char storage[CODOL_MATCH_REPORT_BYTES];
    buffer_t b;
    const char *directory = report_directory();
    int scores[2], slot, rows = 0, humans = 0, activity = 0, earned_total = 0;
    int live_earned[MAX_CLIENTS], live_kills[MAX_CLIENTS], live_deaths[MAX_CLIENTS];
    int live_assists[MAX_CLIENTS], live_score[MAX_CLIENTS], live_total[MAX_CLIENTS];
    static int live_stats[MAX_CLIENTS][CODOL_MATCH_REPORT_STATS];
    static int departed_stats[CODOL_MATCH_REPORT_DEPARTED][CODOL_MATCH_REPORT_STATS];
    char file_name[96];
    unsigned i, n;
    file_name[0] = 0;
    if (!directory) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL match report: codol_profilePath is empty; the match result cannot reach the lobby\n");
        return 0;
    }
    if (!level.clients || !sv_maxclients) return 0;
    scores[0] = level.teamScores[TEAM_RED];
    scores[1] = level.teamScores[TEAM_BLUE];
    memset(live_total, 0, sizeof(live_total));

    for (i = 0; i < MAX_CLIENTS; ++i) {
        int team = 0, total = 0;
        live_earned[i] = live_kills[i] = live_deaths[i] = live_assists[i] = live_score[i] = 0;
        if (!live[i].used || !client_connected(i)) continue;
        client_counters(i, &live_kills[i], &live_deaths[i], &live_assists[i], &live_score[i], &team);
        live[i].team = team;
        if (svs.clients[i].name[0]) Q_strncpyz(live[i].name, svs.clients[i].name, sizeof(live[i].name));
        live_kills[i] = live_kills[i] + live[i].carry_kills > 0 ? live_kills[i] + live[i].carry_kills : 0;
        live_deaths[i] = live_deaths[i] + live[i].carry_deaths > 0 ? live_deaths[i] + live[i].carry_deaths : 0;
        live_assists[i] = live_assists[i] + live[i].carry_assists > 0 ? live_assists[i] + live[i].carry_assists : 0;
        live_score[i] = live_score[i] + live[i].carry_score > 0 ? live_score[i] + live[i].carry_score : 0;
        live_earned[i] = live[i].carry_xp;
        for (n = 0; n < CODOL_MATCH_REPORT_STATS; ++n) {
            int value = 0;
            live_stats[i][n] = live[i].stat_carry[n];
            if (live[i].stat_valid[n] &&
                read_secure_stat(i, codol_match_report_stats[n], &value) &&
                value > live[i].stat_base[n])
                live_stats[i][n] += value - live[i].stat_base[n];
            if (live_stats[i][n] < 0) live_stats[i][n] = 0;
        }
        if (live[i].baseline_valid && client_total_xp(i, &total)) {
            live_total[i] = total;
            if (total > live[i].baseline_xp) live_earned[i] += total - live[i].baseline_xp;
        }
        ++rows;
        ++humans;
        earned_total += live_earned[i];
        activity += live_kills[i] + live_deaths[i] + live_assists[i] + live_score[i];
        /* The lobby credits challenge progress too, so it is activity. */
        for (n = 0; n < live[i].challenges; ++n)
            if (live[i].challenge_carry[n] > 0) activity += live[i].challenge_carry[n];
        challenge_stay_deltas(i, &activity, challenge_count);
    }
    for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i) {
        if (!departed[i].used) continue;
        for (n = 0; n < CODOL_MATCH_REPORT_STATS; ++n)
            departed_stats[i][n] = departed[i].stat_carry[n] > 0 ? departed[i].stat_carry[n] : 0;
        ++rows;
        ++humans;
        earned_total += departed[i].carry_xp;
        activity += departed[i].kills + departed[i].deaths + departed[i].assists +
                    departed[i].score;
        for (n = 0; n < departed[i].challenges; ++n)
            if (departed[i].challenge_carry[n] > 0) activity += departed[i].challenge_carry[n];
    }
    /* "Activity" is deliberately what the lobby can be credited for - XP, and
     * the kills/deaths/assists/score that become lifetime counters - and
     * deliberately NOT time played. A report carrying nothing but a duration
     * would still replace a report the lobby has not consumed yet, which is
     * how a real match's XP would get thrown away by an idle reconnect.
     * Say the outcome out loud either way: "no report" and "a report with
     * nothing in it" look identical from the console otherwise, and the usual
     * cause is upstream (the scripts never called setRankExperience). */
    if (!rows || !humans || (earned_total <= 0 && activity <= 0)) {
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL match report: nothing owed (reason %s): %d row(s), %d human, %d XP, activity %d - not written\n",
            reason && *reason ? reason : "ended", rows, humans, earned_total, activity);
        for (i = 0; i < MAX_CLIENTS; ++i) {
            if (!live[i].used || !client_connected(i)) continue;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL match report:   client %u uid %llu xp %d (base %d, now %d, valid %d) k%d d%d a%d s%d\n",
                i, (unsigned long long)live[i].uid, live_earned[i], live[i].baseline_xp,
                live_total[i], (int)live[i].baseline_valid,
                live_kills[i], live_deaths[i], live_assists[i], live_score[i]);
        }
        for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i) {
            if (!departed[i].used) continue;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL match report:   left slot %u uid %llu xp %d k%d d%d a%d s%d\n",
                (unsigned)departed[i].slot, (unsigned long long)departed[i].uid,
                departed[i].carry_xp, departed[i].kills, departed[i].deaths,
                departed[i].assists, departed[i].score);
        }
        return 0;
    }

    b.data = storage; b.size = sizeof(storage); b.used = 0; b.overflow = 0;
    storage[0] = 0;
    append_text(&b, "{\n \"format\": 1,\n \"created\": ");
    append_int(&b, (int)(long)Com_GetRealtime());
    append_text(&b, ",\n \"reason\": ");
    append_string(&b, reason && *reason ? reason : "ended");
    append_text(&b, ",\n \"server_time_ms\": ");
    append_int(&b, level.time);
    append_text(&b, ",\n \"duration_s\": ");
    append_int(&b, level.time > level.startTime ? (level.time - level.startTime) / 1000 : 0);
    append_text(&b, ",\n \"team_scores\": [");
    append_int(&b, scores[0]);
    append_text(&b, ", ");
    append_int(&b, scores[1]);
    append_text(&b, "],\n \"players\": [\n  ");
    slot = 0;
    for (i = 0; i < MAX_CLIENTS; ++i) {
        if (!live[i].used || !client_connected(i)) continue;
        append_row(&b, live[i].slot, &live[i], live_kills[i], live_deaths[i], live_assists[i],
                   live_score[i], live_earned[i], live_stats[i], scores, !slot++, (int)i);
    }
    for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i) {
        if (!departed[i].used) continue;
        append_row(&b, departed[i].slot, &departed[i], departed[i].kills, departed[i].deaths,
                   departed[i].assists, departed[i].score, departed[i].carry_xp,
                   departed_stats[i], scores, !slot++, -1);
    }
    /* The bots, for the scoreboard context the lobby's format carries. They own
     * no stored row - nothing attaches a profile for them - so they are built
     * here, where the netchan is real and the NA_BOT test actually answers. */
    for (i = 0; i < MAX_CLIENTS; ++i) {
        codol_match_row_t bot;
        int team = 0, kills, deaths, assists, score;
        if (live[i].used || !client_connected(i) || !client_is_bot(i)) continue;
        memset(&bot, 0, sizeof(bot));
        bot.bot = 1;
        bot.slot = (unsigned char)i;
        client_counters(i, &kills, &deaths, &assists, &score, &team);
        bot.team = team;
        if (svs.clients[i].name[0]) Q_strncpyz(bot.name, svs.clients[i].name, sizeof(bot.name));
        append_row(&b, bot.slot, &bot, kills, deaths, assists, score, 0, NULL, scores, !slot++, -1);
    }
    append_text(&b, "\n ]\n}\n");
    if (b.overflow) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL match report: %d rows do not fit in %u bytes; the match result is NOT reported\n",
            rows, (unsigned)sizeof(storage));
        return -1;
    }
    if (!report_file_name(file_name, sizeof(file_name)) ||
        !write_file(directory, file_name, b.data, b.used)) {
        Com_PrintWarning(CON_CHANNEL_SERVER,
            "CoDOL match report: cannot write %s/%s; the match result is LOST to the lobby\n",
            directory, file_name[0] ? file_name : CODOL_MATCH_REPORT_NAME);
        return -1;
    }
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL match report: wrote %d rows (%d human, %d XP, reason %s) to %s/%s\n",
        rows, humans, earned_total, reason && *reason ? reason : "ended", directory, file_name);
    /* One line per human row, so a report the lobby never folds can still be
     * credited by hand from the console log alone. */
    for (i = 0; i < MAX_CLIENTS; ++i) {
        if (!live[i].used || !client_connected(i)) continue;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL match report:   %s uid %llu xp %d (base %d, now %d) k%d d%d a%d s%d\n",
            file_name, (unsigned long long)live[i].uid, live_earned[i], live[i].baseline_xp,
            live_total[i], live_kills[i], live_deaths[i], live_assists[i], live_score[i]);
    }
    for (i = 0; i < CODOL_MATCH_REPORT_DEPARTED; ++i) {
        if (!departed[i].used) continue;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL match report:   %s uid %llu xp %d (left) k%d d%d a%d s%d\n",
            file_name, (unsigned long long)departed[i].uid, departed[i].carry_xp,
            departed[i].kills, departed[i].deaths, departed[i].assists, departed[i].score);
    }
    /* Consecutive reports must partition the match, never repeat it: everything
     * just reported becomes the new baseline, and the frozen rows are done. */
    for (i = 0; i < MAX_CLIENTS; ++i) {
        if (!live[i].used) continue;
        live[i].carry_xp = 0;
        /* live_* already included the old carry, so subtracting it leaves the
         * negative of what the engine counters read at this instant: the next
         * report's row is then only what accrued after this one. */
        live[i].carry_kills -= live_kills[i];
        live[i].carry_deaths -= live_deaths[i];
        live[i].carry_assists -= live_assists[i];
        live[i].carry_score -= live_score[i];
        if (live[i].baseline_valid && live_total[i] > live[i].baseline_xp)
            live[i].baseline_xp = live_total[i];
        /* Challenges are measured against a baseline: this report took the
         * earlier stays' carry and everything up to the values it just read. */
        memset(live[i].challenge_id, 0, sizeof(live[i].challenge_id));
        memset(live[i].challenge_carry, 0, sizeof(live[i].challenge_carry));
        live[i].challenges = 0;
        live[i].challenge_overflow = 0;
        if (client_connected(i)) challenge_rebase(i);
        /* Weapon XP is accumulated, not measured, so the report owns it now. */
        memset(live[i].weapon_name, 0, sizeof(live[i].weapon_name));
        memset(live[i].weapon_xp, 0, sizeof(live[i].weapon_xp));
        live[i].weapons = 0;
        live[i].weapon_overflow = 0;
        for (n = 0; n < CODOL_MATCH_REPORT_STATS; ++n) {
            int value = 0;
            live[i].stat_carry[n] = 0;
            if (live[i].stat_valid[n] && read_secure_stat(i, codol_match_report_stats[n], &value))
                live[i].stat_base[n] = value;
        }
    }
    memset(departed, 0, sizeof(departed));
    return 1;
}

/* ------------------------------------------------------------------------- */
/* Server match record delivery (setMatchDataDef/setMatchData/sendMatchData)  */
/* ------------------------------------------------------------------------- */

/* C1 hands the prepared {record, definition size} pair to its Live upload queue
 * (0x551d80 -> 0x5cf180 -> 0x58eba0). This server has no Demonware backend of
 * its own: the lobby is the backend, and the boundary between the two processes
 * is the same resources directory the rank report crosses. So deliver the
 * record there, beside match_report.json, under the definition's own name.
 * Nothing in the lobby consumes it yet - this closes the "retained, no delivery
 * sink" path and gives the end-game record a real destination, it is not a
 * claim that the lobby reads it. */
static int matchdata_sink(void *context, const codol_server_matchdata_submission_t *submission)
{
    const char *directory = report_directory();
    (void)context;
    if (!submission || !submission->record || !submission->size) return 0;
    if (!directory) return 0;
    if (!write_file(directory, "match_data.mdr", (const char *)submission->record, submission->size))
        return 0;
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL match data: delivered %u bytes of %s to %s/match_data.mdr\n",
        (unsigned)submission->size, submission->name ? submission->name : "?", directory);
    return 1;
}

void CODOL_InstallMatchDataSink(void)
{
    CODOL_SetServerMatchDataSink(matchdata_sink, NULL);
}

void CODOL_ResetMatchReport(void)
{
    unsigned i;
    for (i = 0; i < MAX_CLIENTS; ++i) {
        if (!live[i].used) continue;
        CODOL_MatchReportClientDropped(i);
    }
    /* Only writes when something is still owed. After an ordinary game-over
     * report every row has settled to nothing, so a map change cannot overwrite
     * a report the lobby has not consumed yet with an empty one. */
    CODOL_WriteMatchReport("mapchange");
    memset(live, 0, sizeof(live));
    memset(departed, 0, sizeof(departed));
    memset(challenge_base_valid, 0, sizeof(challenge_base_valid));
}
#endif
