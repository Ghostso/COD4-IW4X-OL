/* Native match-report fixture.
 *
 * Checks the two things the lobby actually depends on: the XP a row reports is
 * exactly the growth of that client's secure progression since its profile was
 * attached, and the JSON is the format-1 document rank_writeback.py accepts,
 * with a per-row uid. The engine side is a fixture: svs/level are defined here,
 * and the secure profile is stubbed down to one integer per client so the
 * arithmetic under test is the report's, not the rank table's.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "server.h"
#include "g_shared.h"
#include "codol_match_report.h"
#include "codol_structured_schema.h"
#include "codol_assets.h"
#include "codol_matchdata_server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ---- engine fixture ----------------------------------------------------- */
serverStatic_t svs;
level_locals_t level;
cvar_t *sv_maxclients;
static cvar_t maxclients_var, profile_path_var;
static gclient_t clients[MAX_CLIENTS];
static char profile_directory[512];

/* One "secure profile" per client: the total XP the rank conversion would
 * report. The report never inspects the bytes, only the converted total. */
static int profile_total[MAX_CLIENTS];
static int profile_attached[MAX_CLIENTS];
static codol_structured_schema_t fixture_schema;
static codol_engine_table_t fixture_table;

cvar_t *Cvar_FindVar(const char *name)
{
    if (!strcmp(name, "codol_profilePath")) return &profile_path_var;
    return NULL;
}
const codol_structured_schema_t *CODOL_ScriptProfileSchema(int buffer)
{ (void)buffer; return &fixture_schema; }
const uint8_t *CODOL_ScriptProfileBlob(unsigned client, int buffer)
{
    (void)buffer;
    if (client >= MAX_CLIENTS || !profile_attached[client]) return NULL;
    return (const uint8_t *)&profile_total[client];
}
int CODOL_LoadEngineStringTable(const char *name, const codol_engine_table_t **out)
{ (void)name; *out = &fixture_table; return 1; }
int CODOL_ProfileExperience(const uint8_t *profile, size_t size, const codol_structured_schema_t *schema,
                            const codol_engine_table_t *table, int *rank, int *experience)
{
    (void)size; (void)schema; (void)table;
    if (!profile) return 0;
    *rank = 0;
    *experience = *(const int *)profile;
    return 1;
}
void CODOL_SetServerMatchDataSink(codol_server_matchdata_sink_t handler, void *context)
{ (void)handler; (void)context; }

/* A stand-in secure DDL. Members are resolved BY NAME exactly as the mounted
 * mp/playersecuredata.def resolves them, so the fixture can also prove what
 * happens to a name the real DDL would not declare: "misses" is deliberately
 * absent here. logical_index is the slot in profile_stats[client][]. */
static const char *const fixture_stats[] = {
    "timePlayedTotal", "score", "kills", "deaths", "assists", "headshots",
    "totalShots", "hits", "wins", "losses", "ties", "winStreak", "killStreak",
    "escapes", "suicides", "objectives"
};
/* This client's DDL stores `kills` and `wins` as float32 - the two headline
 * numbers on the career page - so the fixture must too, or a reader that only
 * handles integers would pass here and report nothing live. */
static int fixture_stat_is_float(const char *name)
{ return !strcmp(name, "kills") || !strcmp(name, "wins"); }
#define FIXTURE_STATS (sizeof(fixture_stats)/sizeof(fixture_stats[0]))
static uint32_t profile_stats[MAX_CLIENTS][FIXTURE_STATS];
static codol_structured_definition_t fixture_def;

static int fixture_stat_index(const char *name)
{
    unsigned i;
    for (i = 0; i < FIXTURE_STATS; ++i)
        if (!strcmp(name, fixture_stats[i])) return (int)i;
    return -1;
}
static void set_stat(unsigned client, const char *name, uint32_t value)
{
    int index = fixture_stat_index(name);
    if (index < 0) return;
    if (fixture_stat_is_float(name)) {
        float f = (float)value;
        memcpy(&profile_stats[client][index], &f, sizeof(f));
    } else profile_stats[client][index] = value;
}
int CODOL_ScriptProfileView(unsigned client, int buffer,
                            const codol_structured_definition_t **definition,
                            const uint8_t **record, size_t *capacity)
{
    (void)buffer;
    if (client >= MAX_CLIENTS || !profile_attached[client]) return 0;
    *definition = &fixture_def;
    *record = (const uint8_t *)profile_stats[client];
    *capacity = sizeof(profile_stats[client]);
    return 1;
}
int CODOL_ResolveStructuredField(const codol_structured_definition_t *definition,
                                 const codol_structured_path_t *path, size_t count,
                                 codol_structured_field_t *out)
{
    int index;
    (void)definition; (void)count;
    if (!path || !path->name) return 0;
    index = fixture_stat_index(path->name);
    if (index < 0) return 0;
    out->type.kind = fixture_stat_is_float(path->name) ? 8 : 0;
    out->type.index = 0;
    out->logical_index = (uint32_t)index; out->mapped_address = 0;
    return 1;
}
int CODOL_StructuredReadScalar(const codol_structured_layout_t *layout, unsigned type,
                               unsigned property, const uint8_t *record, size_t capacity,
                               uint32_t *out)
{
    (void)layout; (void)type;
    if ((size_t)(property + 1) * sizeof(uint32_t) > capacity) return 0;
    *out = ((const uint32_t *)record)[property];
    return 1;
}
time_t Com_GetRealtime(void) { return 1789500000; }
void QDECL Com_Printf(conChannel_t channel, const char *fmt, ...) { (void)channel; (void)fmt; }
void QDECL Com_PrintWarning(conChannel_t channel, const char *fmt, ...) { (void)channel; (void)fmt; }
void FS_ReplaceSeparators(char *path) { (void)path; }
void Q_strncpyz(char *dest, const char *src, int size)
{
    if (size <= 0) return;
    strncpy(dest, src, (size_t)size - 1);
    dest[size - 1] = 0;
}

/* ---- harness ------------------------------------------------------------ */
static int failures;
static void check(int condition, const char *what, const char *detail)
{
    if (condition) { printf("  ok   %s\n", what); return; }
    printf("  FAIL %s %s\n", what, detail ? detail : "");
    ++failures;
}

static char report_text[65536];
static size_t read_report(void)
{
    char path[640];
    FILE *file;
    size_t n;
    snprintf(path, sizeof(path), "%s/match_report.json", profile_directory);
    file = fopen(path, "rb");
    if (!file) return 0;
    n = fread(report_text, 1, sizeof(report_text) - 1, file);
    fclose(file);
    report_text[n] = 0;
    return n;
}
static void remove_report(void)
{
    char path[640];
    snprintf(path, sizeof(path), "%s/match_report.json", profile_directory);
    remove(path);
}
static int has(const char *needle) { return strstr(report_text, needle) != NULL; }
/* Search only inside one named row's "lifetime" object: the row itself
 * already carries this-match "kills"/"deaths"/"score" keys with the same
 * names, and every other row has a lifetime object of its own. */
static int lifetime_has(const char *who, const char *needle)
{
    char key[64];
    const char *row, *start, *end;
    char window[4096];
    size_t n;
    snprintf(key, sizeof(key), "\"name\": \"%s\"", who);
    row = strstr(report_text, key);
    if (!row) return 0;
    start = strstr(row, "\"lifetime\": {");
    if (!start) return 0;
    end = strchr(start, '}');
    if (!end) return 0;
    n = (size_t)(end - start);
    if (n >= sizeof(window)) n = sizeof(window) - 1;
    memcpy(window, start, n);
    window[n] = 0;
    return strstr(window, needle) != NULL;
}

static void connect_client(unsigned slot, const char *name, uint64_t uid, int bot,
                           int total, int team)
{
    svs.clients[slot].state = CS_ACTIVE;
    svs.clients[slot].netchan.remoteAddress.type = bot ? NA_BOT : NA_IP;
    Q_strncpyz(svs.clients[slot].name, name, sizeof(svs.clients[slot].name));
    clients[slot].sess.cs.team = team;
    clients[slot].sess.kills = 0;
    clients[slot].sess.deaths = 0;
    clients[slot].sess.assists = 0;
    clients[slot].sess.score = 0;
    profile_total[slot] = total;
    profile_attached[slot] = !bot;
    /* Only an account attaches a profile. A bot never reaches
     * CODOL_AutoBindClientSecureProfile (it has no uid), so the report has to
     * synthesise its row from the connected slot at write time - which is also
     * the only moment the NA_BOT test can be trusted, because NA_BOT is zero
     * and SV_DirectConnect does not set the netchan up until after the attach. */
    if (!bot)
        CODOL_MatchReportClientAttached(slot, uid);
}

int main(int argc, char **argv)
{
    const char *directory = argc > 1 ? argv[1] : ".";
    int written;

    snprintf(profile_directory, sizeof(profile_directory), "%s", directory);
    profile_path_var.string = profile_directory;
    maxclients_var.integer = MAX_CLIENTS;
    sv_maxclients = &maxclients_var;
    level.clients = clients;
    level.time = 620000;
    level.startTime = 20000;
    level.teamScores[TEAM_RED] = 750;
    level.teamScores[TEAM_BLUE] = 1000;
    remove_report();

    printf("match report: two humans and a bot\n");
    connect_client(0, "Alpha", 11354582479263516619ULL, 0, 484072, TEAM_BLUE);
    connect_client(1, "Bra^1vo\"\\", 2758876527760990337ULL, 0, 1000, TEAM_RED);
    connect_client(2, "bot0", 0, 1, 0, TEAM_RED);

    check(CODOL_WriteMatchReport("gameended") == 0,
          "an idle match with no XP and no activity writes nothing", NULL);

    /* A match happens. _rank.gsc commits through setRankExperience, which is
     * what moves these totals. */
    clients[0].sess.kills = 9; clients[0].sess.deaths = 3;
    clients[0].sess.assists = 2; clients[0].sess.score = 1000;
    clients[1].sess.kills = 4; clients[1].sess.deaths = 7;
    clients[1].sess.assists = 1; clients[1].sess.score = 450;
    clients[2].sess.kills = 2; clients[2].sess.deaths = 10; clients[2].sess.score = 200;
    profile_total[0] = 484072 + 1500;
    profile_total[1] = 1000 + 620;

    written = CODOL_WriteMatchReport("gameended");
    check(written == 1, "a match with XP is reported", NULL);
    check(read_report() > 0, "the report file exists", NULL);
    check(has("\"format\": 1"), "format 1", report_text);
    check(has("\"reason\": \"gameended\""), "the reason is carried", NULL);
    check(has("\"team_scores\": [750, 1000]"), "team scores", NULL);
    check(has("\"uid\": \"11354582479263516619\""), "row 0 names its own account", NULL);
    check(has("\"uid\": \"2758876527760990337\""), "row 1 names its own account", NULL);
    check(has("\"total\": 1500"), "row 0 reports exactly the XP it gained", report_text);
    check(has("\"total\": 620"), "row 1 reports exactly the XP it gained", report_text);
    check(has("\"applied_live\": 0"),
          "nothing was persisted behind the lobby's back", NULL);
    check(has("\"kills\": 9") && has("\"deaths\": 3") && has("\"assists\": 2"),
          "row 0 carries its own counters", NULL);
    check(has("\"kills\": 4") && has("\"deaths\": 7"),
          "row 1 carries its own counters", NULL);
    check(has("\"name\": \"Bra^1vo\\\"\\\\\""),
          "a name with a quote and a backslash is escaped", report_text);
    check(has("\"outcome\": \"win\""), "the blue row won", NULL);
    check(has("\"outcome\": \"loss\""), "the red rows lost", NULL);
    check(has("\"bot\": true"), "the bot is present", NULL);
    check(strstr(report_text, "\"bot\": true, \"team\"") != NULL,
          "and carries no uid key", report_text);
    check(has("\"name\": \"bot0\", \"bot\": true"),
          "the bot row is synthesised from the connected slot, not from an attach",
          report_text);
    {   /* the bot row must have no xp object: count them */
        const char *p = report_text; int xp = 0;
        while ((p = strstr(p, "\"xp\":")) != NULL) { ++xp; ++p; }
        check(xp == 2, "exactly the two human rows carry xp", NULL);
    }

    printf("match report: consecutive reports partition the match\n");
    check(CODOL_WriteMatchReport("timelimit") == 0,
          "an immediate second report has nothing to add", NULL);
    profile_total[0] += 250;
    clients[0].sess.kills = 11;
    check(CODOL_WriteMatchReport("timelimit") == 1, "more XP reports again", NULL);
    read_report();
    check(has("\"total\": 250"), "and reports only the new XP, never the first 1500",
          report_text);
    check(has("\"kills\": 2"), "and only the kills since the last report", report_text);

    printf("match report: a departed player is still reported\n");
    profile_total[1] += 80;
    CODOL_MatchReportClientDropped(1);
    svs.clients[1].state = CS_FREE;
    profile_attached[1] = 0;
    check(CODOL_MatchReportHumansConnected() == 1, "one human is still in", NULL);
    check(CODOL_WriteMatchReport("disconnect") == 1, "the leaver is reported", NULL);
    read_report();
    check(has("\"uid\": \"2758876527760990337\""), "with its own uid", report_text);
    check(has("\"total\": 80"), "and the XP it earned after the last report", report_text);

    printf("match report: a reconnect is one row, not two\n");
    connect_client(1, "Bravo", 2758876527760990337ULL, 0, 1700, TEAM_RED);
    profile_total[1] = 1700 + 90;
    clients[1].sess.kills = 1;
    check(CODOL_WriteMatchReport("gameended") == 1, "the rejoined player is reported", NULL);
    read_report();
    {
        const char *first = strstr(report_text, "\"uid\": \"2758876527760990337\"");
        check(first && !strstr(first + 1, "\"uid\": \"2758876527760990337\""),
              "exactly one row for that account", report_text);
    }
    check(has("\"total\": 90"), "carrying only the new XP", report_text);

    printf("match report: career counters are measured, not re-counted\n");
    {
        /* The scripts maintain the secure profile through setPlayerData; this
         * module only measures it, the same way it measures experience. */
        unsigned slot = 5;
        svs.clients[slot].state = CS_ACTIVE;
        svs.clients[slot].netchan.remoteAddress.type = NA_IP;
        Q_strncpyz(svs.clients[slot].name, "Career", sizeof(svs.clients[slot].name));
        clients[slot].sess.cs.team = TEAM_BLUE;
        clients[slot].sess.kills = 0; clients[slot].sess.deaths = 0;
        clients[slot].sess.assists = 0; clients[slot].sess.score = 0;
        profile_total[slot] = 100000;
        profile_attached[slot] = 1;
        set_stat(slot, "timePlayedTotal", 3600);
        set_stat(slot, "kills", 400);
        set_stat(slot, "score", 90000);
        set_stat(slot, "hits", 2000);
        set_stat(slot, "totalShots", 8000);
        set_stat(slot, "killStreak", 7);
        set_stat(slot, "wins", 40);   /* float32 in this DDL, like kills */
        CODOL_MatchReportClientAttached(slot, 1122334455667788990ULL);

        /* A match happens: the scripts move the profile. */
        set_stat(slot, "timePlayedTotal", 3600 + 540);
        set_stat(slot, "kills", 400 + 9);
        set_stat(slot, "score", 90000 + 1250);
        set_stat(slot, "hits", 2000 + 31);
        set_stat(slot, "totalShots", 8000 + 120);
        set_stat(slot, "killStreak", 11);
        set_stat(slot, "wins", 41);
        clients[slot].sess.kills = 9; clients[slot].sess.score = 1250;
        profile_total[slot] = 100000 + 900;

        check(CODOL_WriteMatchReport("gameended") == 1, "the career match is reported", NULL);
        read_report();
        check(has("\"lifetime\": {"), "the row carries a lifetime object", report_text);
        check(has("\"timePlayedTotal\": 540"), "time played is the delta, not the total",
              report_text);
        check(has("\"kills\": 9") && has("\"score\": 1250"),
              "kills and score are deltas", report_text);
        check(has("\"hits\": 31") && has("\"totalShots\": 120"),
              "accuracy inputs are deltas", report_text);
        check(has("\"killStreak\": 4"),
              "a best-streak member reports its rise this match", report_text);
        check(lifetime_has("Career", "\"wins\": 1") &&
              lifetime_has("Career", "\"kills\": 9"),
              "float32 members (kills, wins) are read, not refused as non-integers",
              report_text);
        check(!has("\"bombPlants\""),
              "a member this DDL does not declare is simply absent", report_text);
        check(!lifetime_has("Career", "\"deaths\""),
              "and an unchanged counter is omitted rather than sent as zero", report_text);

        /* Partitioning applies to the counters too. */
        check(CODOL_WriteMatchReport("timelimit") == 0,
              "an immediate second report owes nothing", NULL);
        set_stat(slot, "kills", 400 + 12);
        clients[slot].sess.kills = 12;
        check(CODOL_WriteMatchReport("timelimit") == 1, "more kills report again", NULL);
        read_report();
        check(lifetime_has("Career", "\"kills\": 3"),
              "carrying only the three since the last report", report_text);
        CODOL_MatchReportClientDropped(slot);
        svs.clients[slot].state = CS_FREE;
        profile_attached[slot] = 0;
    }

    printf("match report: an attach before Netchan_Setup is still a human\n");
    {
        /* THE 18:55 LIVE BUG. NA_BOT is zero and so is NA_BAD, and
         * SV_DirectConnect attaches the secure profile at sv_client.c:505 but
         * does not call Netchan_Setup until :569, so a connecting human reads
         * as a bot for the whole of the attach. The server logged
         * "nothing owed ... 1 row(s), 0 human" and never wrote a report. */
        unsigned slot = 4;
        svs.clients[slot].state = CS_ACTIVE;
        svs.clients[slot].netchan.remoteAddress.type = NA_BOT;   /* not set up yet */
        Q_strncpyz(svs.clients[slot].name, "Late", sizeof(svs.clients[slot].name));
        clients[slot].sess.cs.team = TEAM_BLUE;
        clients[slot].sess.kills = 0; clients[slot].sess.deaths = 0;
        clients[slot].sess.assists = 0; clients[slot].sess.score = 0;
        profile_total[slot] = 5000;
        profile_attached[slot] = 1;
        CODOL_MatchReportClientAttached(slot, 8765909783858705198ULL);
        check(CODOL_MatchReportHumansConnected() == 1,
              "an attached account counts as human even with a bot-looking netchan", NULL);
        svs.clients[slot].netchan.remoteAddress.type = NA_IP;    /* Netchan_Setup ran */
        clients[slot].sess.kills = 3; clients[slot].sess.score = 300;
        profile_total[slot] = 5000 + 410;
        check(CODOL_WriteMatchReport("gameended") == 1,
              "and its match is reported, not discarded as a bot", NULL);
        read_report();
        check(has("\"uid\": \"8765909783858705198\"") &&
              has("\"total\": 410"),
              "with its own uid and its own XP", report_text);
        CODOL_MatchReportClientDropped(slot);
        svs.clients[slot].state = CS_FREE;
        profile_attached[slot] = 0;
    }

    printf("match report: a map change cannot clobber an unconsumed report\n");
    {
        /* The lobby has not fetched the last report yet. SV_ClearServer resets
         * the store on the way into the next map; nothing is owed, so the
         * document on disk must survive untouched. */
        static char before[sizeof(report_text)];
        check(read_report() > 0, "a report is waiting", NULL);
        memcpy(before, report_text, sizeof(before));
        CODOL_ResetMatchReport();
        read_report();
        check(!strcmp(before, report_text),
              "the waiting report is byte-identical after the reset", report_text);
    }
    connect_client(0, "Alpha", 11354582479263516619ULL, 0, 700000, TEAM_BLUE);

    printf("match report: no profile path means no report\n");
    profile_path_var.string = (char *)"";
    check(CODOL_WriteMatchReport("gameended") == 0,
          "an unset codol_profilePath writes nothing", NULL);
    profile_path_var.string = profile_directory;

    /* Leave the last document on disk: the companion Python check feeds it to
     * the lobby's own rank_writeback.py so both ends agree on the schema. */
    CODOL_ResetMatchReport();
    if (failures) { printf("\nFAILED: %d check(s)\n", failures); return 1; }
    printf("\nPASS: match report XP deltas, per-row uid, escaping, departure, reconnect and reset\n");
    return 0;
}
