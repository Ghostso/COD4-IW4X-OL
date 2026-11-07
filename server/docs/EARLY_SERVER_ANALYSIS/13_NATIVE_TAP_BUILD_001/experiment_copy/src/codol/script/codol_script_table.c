#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "codol_assets.h"

/* Retained cdecl routines consume the engine table layout published by the
 * native asset loader, including its mounted-table/reference-CSV policy. */
extern void StringTable_GetAsset(const char *name, const codol_engine_table_t **table);
extern const char *StringTable_GetColumnValueForRow(const codol_engine_table_t *table,
                                                  int row, int column);

/* IW4 5f4720 is shared by tablelookupbyrow and tablelookupistringbyrow.
 * Both return an ordinary script string in that resolver table. T5 654590
 * (tablelookupcolumnforrow) reads the same filename, row, column arguments. */
void CODOL_Scr_TableLookupByRow(void)
{
    const codol_engine_table_t *table = NULL;
    const char *name;
    int row, column;
    if (Scr_GetNumParam() < 3) {
        Scr_Error("TableLookupByRow requires a table name, row and column"); return;
    }
    name = Scr_GetString(0);
    row = Scr_GetInt(1);
    column = Scr_GetInt(2);
    StringTable_GetAsset(name, &table);
    if (!table) { Scr_Error("string table is unavailable"); return; }
    if (com_developer && com_developer->integer > 1)
        Com_DPrintf(CON_CHANNEL_SCRIPT, "tableLookupByRow %s row %d column %d -> '%s'\n", name, row, column, StringTable_GetColumnValueForRow(table, row, column));
    Scr_AddString(StringTable_GetColumnValueForRow(table, row, column));
}

/* IW4 5f46c0 -> 4ac180 searches backward, comparing case-insensitively,
 * so a later duplicate row overrides an earlier one. Missing values yield -1. */
void CODOL_Scr_TableLookupRowNum(void)
{
    const codol_engine_table_t *table = NULL;
    const char *name, *value;
    int column, row;
    if (Scr_GetNumParam() < 3) {
        Scr_Error("TableLookupRowNum requires a table name, column and value"); return;
    }
    name = Scr_GetString(0);
    column = Scr_GetInt(1);
    value = Scr_GetString(2);
    StringTable_GetAsset(name, &table);
    if (!table) { Scr_Error("string table is unavailable"); return; }
    if (!table->columnCount) { Scr_AddInt(-1); return; }
    if (column < 0 || column >= table->columnCount) {
        Scr_ParamError(1, "string table column out of range"); return;
    }
    for (row = table->rowCount - 1; row >= 0; --row) {
        const char *cell = table->values[(size_t)row * table->columnCount + column];
        if (cell && !Q_stricmp(value, cell)) { Scr_AddInt(row); return; }
    }
    Scr_AddInt(-1);
}
#endif

/* tableLookup( <table>, <searchColumn>, <searchValue>, <returnColumn> ): the
 * retained Scr_TableLookup contract (four parameters, StringTable_GetAsset,
 * StringTable_Lookup, empty string when nothing matches) with a developer
 * trace of misses, so a script that searches a CoDOL table with an IW4 key is
 * visible in the console instead of failing later on the empty result. */
extern const char *StringTable_Lookup(const codol_engine_table_t *table, int searchColumn, const char *searchValue, int returnColumn);
/* Empty authored cells are successful lookups too. Only used for developer
 * diagnostics; preserve the retained lookup's result and duplicate ordering. */
static int table_has_key(const codol_engine_table_t *table, int column, const char *value)
{
    int row;
    if (column < 0 || column >= table->columnCount || !table->values) return 0;
    for (row = table->rowCount - 1; row >= 0; --row) {
        const char *cell = table->values[(size_t)row * table->columnCount + column];
        if (cell && !Q_stricmp(value, cell)) return 1;
    }
    return 0;
}
void CODOL_Scr_TableLookup(void)
{
    const codol_engine_table_t *table = NULL;
    const char *name, *value, *result;
    int searchColumn, returnColumn;
    if (Scr_GetNumParam() != 4) {
        Scr_Error("Usage: tableLookup( <table name>, <search column>, <search value>, <return column> )");
        return;
    }
    name = Scr_GetString(0);
    StringTable_GetAsset(name, &table);
    searchColumn = Scr_GetInt(1);
    value = Scr_GetString(2);
    returnColumn = Scr_GetInt(3);
    if (!table) { Scr_AddString(""); return; }
    result = StringTable_Lookup(table, searchColumn, value, returnColumn);
    if ((!result || !*result) && com_developer && com_developer->integer &&
        (returnColumn < 0 || returnColumn >= table->columnCount ||
         !table_has_key(table, searchColumn, value)))
        Com_DPrintf(CON_CHANNEL_SCRIPT, "tableLookup miss: %s column %d value '%s' return column %d (%dx%d)\n",
                    name, searchColumn, value, returnColumn, table->rowCount, table->columnCount);
    Scr_AddString(result ? result : "");
}
