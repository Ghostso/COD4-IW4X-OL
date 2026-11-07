#include "codol_script_childthread.h"
#include "q_shared.h"
#include "scr_vm.h"
#include "cscr_parser.h"
#include "cscr_main.h"
#include "cscr_variable.h"
#include "xassets/rawfile.h"
#include "xassets.h"
#include "qcommon_mem.h"
#ifdef CODOL_SERVER
#include "codol_assets.h"
#include "codol_script_source.h"
/* codol_sv_state.h pulls the snapshot/message headers and carries no C++
 * linkage guard; this one accessor is all the parser needs. */
extern "C" const char *CODOL_ServerZoneType(void);
#include "codol_script_lower.h"
static int CODOL_ScriptBuiltinKind(const char *name);
#include "cvar.h"
#include <stdlib.h>
#endif

struct SaveSourceBufferInfo
{
  char *sourceBuf;
  int len;
};


struct SourceLookup
{
  unsigned int sourcePos;
  int type;
};


struct OpcodeLookup
{
  const char *codePos;
  unsigned int sourcePosIndex;
  unsigned int sourcePosCount;
  int profileTime;
  int profileBuiltInTime;
  int profileUsage;
};

struct scrParserGlob_t
{
  struct OpcodeLookup *opcodeLookup;
  unsigned int opcodeLookupMaxLen;
  unsigned int opcodeLookupLen;
  struct SourceLookup *sourcePosLookup;
  unsigned int sourcePosLookupMaxLen;
  unsigned int sourcePosLookupLen;
  unsigned int sourceBufferLookupMaxLen;
  const char *currentCodePos;
  unsigned int currentSourcePosCount;
  struct SaveSourceBufferInfo *saveSourceBufferLookup;
  unsigned int saveSourceBufferLookupLen;
  int delayedSourceIndex;
  int threadStartSourceIndex;
};

scrParserGlob_t gScrParserGlob;
scrParserPub_t gScrParserPub;


extern "C" void __regparm3 Scr_AddSourceBufferInternal(const char *extFilename, const char *codePos, char *sourceBuf, int len, bool doEolFixup, bool archive);


unsigned int Scr_GetFunctionLineNumInternal(const char *buf, unsigned int sourcePos, const char **startLine)
{
  unsigned int lineNum;
  unsigned int functionLine;
  const char *functionStartLine;

  assert(buf != NULL);

  *startLine = buf;
  lineNum = 0;
  functionLine = 0;
  functionStartLine = buf;
  while ( sourcePos )
  {
    if ( !*buf )
    {
      if ( buf[1] == '{' )
      {
        functionLine = lineNum;
        functionStartLine = *startLine;
      }
      *startLine = buf + 1;
      ++lineNum;
    }
    ++buf;
    --sourcePos;
  }
  *startLine = functionStartLine;
  return functionLine;
}


void Scr_PrintSourcePosSummary(conChannel_t channel, const char *filename)
{
  const char *s;

  assert(filename);

  if ( gScrParserGlob.saveSourceBufferLookup )
  {
    s = "(savegame)";
  }
  else
  {
    s = "";
  }
  Com_Printf(channel, "%s%s\t\n", filename, s);
}

void Scr_CopyFormattedLine(char *line, const char *rawLine)
{
  int len;
  int i;

  len = strlen(rawLine);
  if ( len >= 1024 )
  {
    len = 1023;
  }
  for ( i = 0; i < len; ++i )
  {
    if ( rawLine[i] == '\t' )
    {
      line[i] = ' ';
    }
    else
    {
      line[i] = rawLine[i];
    }
  }
  if ( len > 0 && line[len - 1] == '\r' )
  {
    line[len - 1] = 0;
  }
  line[len] = 0;
}

unsigned int Scr_GetFunctionInfo(const char *buf, unsigned int sourcePos, char *line)
{
  const char *startLine;
  unsigned int lineNum;

  lineNum = Scr_GetFunctionLineNumInternal(buf, sourcePos, &startLine);
  Scr_CopyFormattedLine(line, startLine);
  return lineNum;
}

void Scr_PrintFunctionPosSpreadSheet(conChannel_t channel, const char *filename, const char *buf, unsigned int sourcePos)
{
  const char *s;
  unsigned int lineNum;
  char line[1024];
  
  assert(filename);

  lineNum = Scr_GetFunctionInfo(buf, sourcePos, line);
  if ( gScrParserGlob.saveSourceBufferLookup )
  {
    s = "(savegame)";
  }
  else
  {
    s = "";
  }
  Com_Printf(channel, "%s%s\t%d\t%s\n", filename, s, lineNum + 1, line);
}

const char *Scr_PrevCodePosFileName(const char *codePos)
{
  assert(gScrVarPub.developer);
  if ( !codePos )
  {
    return "<frozen thread>";
  }
  if ( codePos == &g_EndPos )
  {
    return "<removed thread>";
  }
  if ( gScrVarPub.programBuffer && Scr_IsInOpcodeMemory(codePos) )
  {
    return gScrParserPub.sourceBufferLookup[Scr_GetSourceBuffer(codePos - 1)].buf;
  }
  return codePos;
}

bool Scr_PrevCodePosFileNameMatches(const char *codePos, const char *fileName)
{
  const char *codePosFileName;

    assert(fileName);
    assert(gScrVarPub.developer);

  codePosFileName = Scr_PrevCodePosFileName(codePos);
  if ( codePosFileName )
  {
    if(Q_stristr(codePosFileName, fileName) != NULL)
    {
        return true;
    }
  }
  return false;
}

OpcodeLookup * Scr_GetPrevSourcePosOpcodeLookup(const char *codePos)
{
  unsigned int low;
  unsigned int middle;
  unsigned int high;

    assert(Scr_IsInOpcodeMemory( codePos ));
    assert(gScrParserGlob.opcodeLookup);
  low = 0;
  high = gScrParserGlob.opcodeLookupLen - 1;
  while ( low <= high )
  {
    middle = (high + low) / 2;
    if ( codePos < gScrParserGlob.opcodeLookup[middle].codePos )
    {
      high = middle - 1;
    }
    else
    {
      low = middle + 1;
      if ( middle + 1 == gScrParserGlob.opcodeLookupLen || codePos < gScrParserGlob.opcodeLookup[low].codePos )
      {
        return &gScrParserGlob.opcodeLookup[middle];
      }
    }
  }
  assert(UNREACHABLE_CODE);
  return 0;
}

unsigned int Scr_GetPrevSourcePos(const char *codePos, unsigned int index)
{
  return gScrParserGlob.sourcePosLookup[index + Scr_GetPrevSourcePosOpcodeLookup(codePos)->sourcePosIndex].sourcePos;
}

const char * Scr_PrevCodePosFunctionName(const char *codePos)
{
  unsigned int bufferIndex;
  const char *startLine;

  assert(gScrVarPub.developer);

  if ( !codePos )
  {
    return "<frozen thread>";
  }
  if ( codePos == &g_EndPos )
  {
    return "<removed thread>";
  }
  if ( !gScrVarPub.programBuffer || !Scr_IsInOpcodeMemory(codePos) )
  {
    return "<unknown>";
  }
  bufferIndex = Scr_GetSourceBuffer(codePos - 1);
  Scr_GetFunctionLineNumInternal(gScrParserPub.sourceBufferLookup[bufferIndex].sourceBuf, Scr_GetPrevSourcePos(codePos - 1, 0), &startLine);
  return startLine;
}

unsigned int Scr_GetLineNumInternal(const char *buf, unsigned int sourcePos, const char **startLine, int *col)
{
  unsigned int lineNum;

  assert(buf != NULL);

  *startLine = buf;
  lineNum = 0;
  while ( sourcePos )
  {
    if ( !*buf )
    {
      *startLine = buf + 1;
      ++lineNum;
    }
    ++buf;
    --sourcePos;
  }
  *col = buf - *startLine;
  return lineNum;
}

unsigned int Scr_GetLineInfo(const char *buf, unsigned int sourcePos, int *col, char *line)
{
  const char *startLine;
  unsigned int lineNum;

  if ( buf )
  {
    lineNum = Scr_GetLineNumInternal(buf, sourcePos, &startLine, col);
  }
  else
  {
    lineNum = 0;
    startLine = "";
    *col = 0;
  }
  Scr_CopyFormattedLine(line, startLine);
  return lineNum;
}

void Scr_PrintSourcePosSpreadSheet(conChannel_t channel, const char *filename, const char *buf, unsigned int sourcePos)
{
  const char *s;
  unsigned int lineNum;
  char line[1024];
  int col;

  assert(filename);

  lineNum = Scr_GetLineInfo(buf, sourcePos, &col, line);
  if ( gScrParserGlob.saveSourceBufferLookup )
  {
    s = "(savegame)";
  }
  else
  {
    s = "";
  }
  Com_Printf(channel, "%s%s\t%d\t%s\t%d\n", filename, s, lineNum + 1, line, col, 0);
}

void Scr_PrintPrevCodePosSpreadSheet(conChannel_t channel, const char *codePos, bool summary, bool functionSummary)
{
  unsigned int bufferIndex;

  assert(gScrVarPub.developer);

  if ( codePos )
  {
    if ( codePos == &g_EndPos )
    {
      Com_Printf(channel, "<removed thread>\n");
    }
    else if ( gScrVarPub.programBuffer && Scr_IsInOpcodeMemory(codePos) )
    {
      bufferIndex = Scr_GetSourceBuffer(codePos - 1);
      if ( summary )
      {
        Scr_PrintSourcePosSummary(channel, gScrParserPub.sourceBufferLookup[bufferIndex].buf);
      }
      else if ( functionSummary )
      {
        Scr_PrintFunctionPosSpreadSheet(channel, gScrParserPub.sourceBufferLookup[bufferIndex].buf, gScrParserPub.sourceBufferLookup[bufferIndex].sourceBuf, Scr_GetPrevSourcePos(codePos - 1, 0));
      }
      else
      {
        Scr_PrintSourcePosSpreadSheet(channel, gScrParserPub.sourceBufferLookup[bufferIndex].buf, gScrParserPub.sourceBufferLookup[bufferIndex].sourceBuf, Scr_GetPrevSourcePos(codePos - 1, 0));
      }
    }
    else
    {
      Com_Printf(channel, "%s\n", codePos);
    }
  }
  else
  {
    Com_Printf(channel, "<frozen thread>\n");
  }
}

#ifdef CODOL_SERVER
/* Keep childthread keywords in the archived/debug copy. Only the parser's
 * separate copy is rewritten, at identical byte offsets. Restored source
 * already passed the general syntax/precompiler stages and uses this helper
 * directly, reconstructing its spans without transforming that text twice. */
static char *Scr_PrepareChildThreadSource(const char *name,const char *codePos,
                                         char *source,int length,bool archive)
{
  char *parserSource=source;
  Scr_ChildThread_ClearFile(name);
  if(source && length>=0 && Scr_ChildThread_SourceHasKeyword(source,length)) {
    parserSource=(char *)Hunk_AllocateTempMemoryHigh(length+1);
    memcpy(parserSource,source,length); parserSource[length]=0;
    const char *error=NULL; int position=0;
    if(!Scr_ChildThread_LowerSource(name,parserSource,length,&error,&position)) {
      Com_Error(ERR_DROP,"CoDOL script %s, offset %d: %s",name,position,
                error?error:"invalid childthread call");
      return NULL;
    }
  }
  Scr_ChildThread_BeginFile(name);
  Scr_AddSourceBufferInternal(name,codePos,source,length,1,archive);
  return parserSource;
}
#endif

static char *Scr_PrepareSource(const char *name,const char *codePos,char *source,int length,bool archive)
{
#ifdef CODOL_SERVER
  if(!source || length<0 || memchr(source,0,(size_t)length)) {
    Com_Error(ERR_DROP,"CoDOL script %s is not complete text source",name);
    return NULL;
  }
  /* Select syscall-conditional branches before interpreting extended GSC.
   * Inactive code must not contribute file constants, foreach rewrites or
   * unsupported-keyword errors. All CoDOL readers supply writable copies.
   * The prepared text is what source lookup/save buffers retain, so restored
   * source follows the same path without applying the precompiler twice. */
  CODOL_HeapCheck("script prepare entry");
  Scr_ScriptPreCompile(source,name);
  CODOL_SetScriptBuiltinResolver(CODOL_ScriptBuiltinKind);
  char *lowered=NULL; size_t loweredLength=0;
  /* Name every script on the way into the lowering pass. A fault inside the
   * pass leaves no other trace of which source was being rewritten, and the
   * corpus is large enough that narrowing it by hand is impractical. */
  if(com_developer && com_developer->integer)
    Com_DPrintf(CON_CHANNEL_SCRIPT,"CoDOL lowering: %s (%d bytes)\n",name,length);
  int status=CODOL_LowerScriptSyntax(source,length,&lowered,&loweredLength);
  if(status<0) {
    unsigned line=0;
    const char *construct=CODOL_LowerScriptDiagnostic(&line);
    if(construct)
      Com_Error(ERR_DROP,"CoDOL script %s, line %u: unsupported GSC construct '%s'",name,line,construct);
    else
      Com_Error(ERR_DROP,"CoDOL script %s has invalid extended syntax",name);
    return NULL;
  }
  if(status==1) {
    source=(char *)Hunk_AllocateTempMemoryHigh(loweredLength+1);
    memcpy(source,lowered,loweredLength+1); free(lowered); length=(int)loweredLength;
  }
  return Scr_PrepareChildThreadSource(name,codePos,source,length,archive);
#endif
  Scr_AddSourceBufferInternal(name,codePos,source,length,1,archive);
  return source;
}

char *__cdecl Scr_ReadFile_FastFile(const char *filename, const char *extFilename, const char *codePos, bool archive)
{
#ifdef CODOL_SERVER
  uint8_t *payload;
  size_t length;
  int codol_status = CODOL_LoadScriptAssetStatus(extFilename, &payload, &length);
  if (codol_status < 0)
  {
    Com_Error(ERR_DROP, "CoDOL script %s has invalid or unsupported asset data", extFilename);
    return NULL;
  }
  if (codol_status > 0)
  {
    char *source = (char *)Hunk_AllocateTempMemoryHigh(length + 1);
    memcpy(source, payload, length + 1);
    free(payload);
    return Scr_PrepareSource(extFilename,codePos,source,length,archive);
  }
#endif
  RawFile *rawfile;
  int len;
  const char *sourceBuf;

  if ( useFastFile->boolean )
  {
    rawfile = DB_FindXAssetHeader(ASSET_TYPE_RAWFILE, extFilename, true, 100).rawfile;
    if ( rawfile )
    {
      sourceBuf = rawfile->buffer;
#ifdef CODOL_SERVER
      /* Load_RawFile reads len+1 bytes; len excludes the terminating NUL.
       * Use that length so an embedded NUL reaches the shared text validator
       * instead of silently compiling a prefix through strlen. */
      len = rawfile->len;
      if(!sourceBuf || len<0 || len>16*1024*1024 || sourceBuf[len]!=0) {
        Com_Error(ERR_DROP,"CoDOL script %s has invalid rawfile source",extFilename);
        return NULL;
      }
      /* Source preparation rewrites #if directives in place. Keep mounted
       * rawfile bytes immutable, including when
       * syntax lowering returns the original input unchanged. Each compile
       * session must see the original directives and current syscall registry. */
      char *source = (char *)Hunk_AllocateTempMemoryHigh(len + 1);
      memcpy(source, sourceBuf, len + 1);
      return Scr_PrepareSource(extFilename,codePos,source,len,archive);
#else
      len = strlen(sourceBuf);
      return Scr_PrepareSource(extFilename,codePos,(char *)sourceBuf,len,archive);
#endif
    }
  }
  Scr_AddSourceBufferInternal(extFilename, codePos, 0, -1, 1, archive);
  return NULL;
}


char *__cdecl Scr_ReadFile_LoadObj(const char *filename, const char *extFilename, const char *codePos, bool archive)
{
  int len;
  int f;
  char *sourceBuf;

  len = FS_FOpenFileByMode(extFilename, &f, FS_READ);
  if ( len >= 0 )
  {
/*
    if ( !fs_gameDirVar && fs_gameDirVar->string[0] )
    {
      g_loadedImpureScript = 1;
    }
*/
 #ifdef CODOL_SERVER
    /* Match the external-source reader's bound before len+1/allocation. */
    if(len>16*1024*1024) {
      FS_FCloseFile(f);
      Com_Error(ERR_DROP,"CoDOL script %s exceeds the source size limit",extFilename);
      return NULL;
    }
 #endif
    sourceBuf = (char*)Hunk_AllocateTempMemoryHigh(len + 1);
 #ifdef CODOL_SERVER
    int received=0;
    while(received<len) {
      int amount=FS_Read(sourceBuf+received,len-received,f);
      if(amount<=0 || amount>len-received) {
        FS_FCloseFile(f);
        Com_Error(ERR_DROP,"CoDOL script %s could not be read completely",extFilename);
        return NULL;
      }
      received+=amount;
    }
 #else
    FS_Read(sourceBuf, len, f);
 #endif
    sourceBuf[len] = 0;
    FS_FCloseFile(f);
    return Scr_PrepareSource(extFilename,codePos,sourceBuf,len,archive);
  }
  Scr_AddSourceBufferInternal(extFilename, codePos, 0, -1, 1, archive);
  return NULL;
}



/* Builtin lookup for the syntax lowering pass: registered functions, then
 * methods, by the same case-insensitive tables the compiler resolves calls in. */
static int CODOL_ScriptBuiltinKind(const char *name)
{
  const char *lookup=name; qboolean developer=qfalse;
  if(Scr_GetFunction(&lookup,&developer)) return 1;
  lookup=name;
  if(Scr_GetMethod(&lookup,&developer)) return 2;
  return 0;
}

char *__cdecl Scr_ReadFile(const char *filename, const char *extFilename, const char *codePos, bool archive)
{
#ifdef CODOL_SERVER
  cvar_t *base = Cvar_RegisterString("codol_scriptPath", "", 0, "Native server GSC source root (mp subdirectory before common files)");
  cvar_t *overlay = Cvar_RegisterString("codol_scriptOverlay", "", 0, "Native server GSC source overrides");
  cvar_t *nativeOverlay = Cvar_RegisterString("codol_scriptNativeOverlay", "scripts/codol", 0, "sh1x script adaptations, above the user overlay");
  char *payload = NULL; size_t length = 0;
  int status;
  /* Animation trees belong to the mounted CoDOL archives: C1 ships its own
   * animtrees/*.atr as rawfiles and mp/playeranim.script names animations
   * (dive-to-prone and others) that the vendor IW4 tree does not carry. The
   * script roots only stand in when no mounted archive defines the tree. */
  if (!strncmp(extFilename, "animtrees/", 10)) {
    const codol_engine_rawfile_t *raw = NULL;
    if (CODOL_LoadEngineRawFile(extFilename, &raw) == 1 && raw && raw->buffer && raw->len >= 0) {
      char *source = (char *)Hunk_AllocateTempMemoryHigh(raw->len + 1);
      memcpy(source, raw->buffer, raw->len); source[raw->len] = 0;
      if (com_developer && com_developer->integer)
        FS_SV_HomeWriteFile(va("codol_animtrees/%s", extFilename + 10), source, raw->len);
      Com_DPrintf(CON_CHANNEL_SYSTEM, "CoDOL mounted animtree: %s\n", extFilename);
      return Scr_PrepareSource(extFilename, codePos, source, raw->len, archive);
    }
  }
  /* The mounted map's asset category selects the script set: a zm or coop
   * match resolves maps/mp/gametypes/_callbacksetup, its gametype script and
   * its level script out of <nativeOverlay>/<category>/ and never compiles the
   * multiplayer ones. NULL before a map identity is latched (script tools,
   * unit fixtures), which leaves the multiplayer order untouched. */
  status = CODOL_ReadScriptSourceWithNativeOverlayForZone(base->string, overlay->string,
    nativeOverlay->string, CODOL_ServerZoneType(), extFilename, &payload, &length);
  if (status < 0) {
    Com_Error(ERR_DROP, "CoDOL external script %s is unreadable or invalid source", extFilename);
    return NULL;
  }
  if (status == 1) {
    char *source = (char *)Hunk_AllocateTempMemoryHigh(length + 1);
    memcpy(source, payload, length + 1); free(payload);
    return Scr_PrepareSource(extFilename,codePos,source,length,archive);
  }
#endif
    int file;

//  if ( fs_gameDirVar && fs_gameDirVar->string[0])
  {
    if ( FS_FOpenFileRead(extFilename, &file) < 0 )
    {
      return Scr_ReadFile_FastFile(filename, extFilename, codePos, archive);
    }
    FS_FCloseFile(file);
    return Scr_ReadFile_LoadObj(filename, extFilename, codePos, archive);
  }
/* 
Impure script locked mode here:
  if ( useFastFile->boolean )
  {
    return Scr_ReadFile_FastFile(filename, extFilename, codePos, archive);
  }
  return Scr_ReadFile_LoadObj(filename, extFilename, codePos, archive);
*/    
}


extern "C"{


void Scr_PrintSourcePos(conChannel_t channel, const char *filename, const char *buf, unsigned int sourcePos)
{
  const char *s; 
  unsigned int lineNum;
  char line[1024];
  int i;
  int col;

  lineNum = Scr_GetLineInfo(buf, sourcePos, &col, line);
  if ( gScrParserGlob.saveSourceBufferLookup )
  {
    s = " (savegame)";
  }
  else
  {
    s = "";
  }
  Com_Printf(channel, "(file '%s'%s, line %d)\n", filename, s, lineNum + 1);
  Com_Printf(channel, "%s\n", line, 0);
  for ( i = 0; i < col; ++i )
  {
    Com_Printf(channel, " ");
  }
  Com_Printf(channel, "*\n");
}


unsigned int __cdecl Scr_GetSourceBuffer(const char *codePos)
{
  unsigned int bufferIndex;
  
    assert(Scr_IsInOpcodeMemory(codePos ));
    assert(gScrParserPub.sourceBufferLookupLen > 0);

  for ( bufferIndex = gScrParserPub.sourceBufferLookupLen - 1;
        bufferIndex && (!gScrParserPub.sourceBufferLookup[bufferIndex].codePos || gScrParserPub.sourceBufferLookup[bufferIndex].codePos > codePos);
        --bufferIndex );
  return bufferIndex;
}

void __cdecl Scr_PrintPrevCodePos(conChannel_t channel, const char *codePos, unsigned int index)
{
  unsigned int bufferIndex;


  if ( !codePos )
  {
    Com_Printf(channel, "<frozen thread>\n");
    return;
  }
  if ( codePos == &g_EndPos )
  {
    Com_Printf(channel, "<removed thread>\n");
  }
  else
  {
    if ( gScrVarPub.developer )
    {
      if ( gScrVarPub.programBuffer && Scr_IsInOpcodeMemory(codePos) )
      {
        bufferIndex = Scr_GetSourceBuffer(codePos - 1);
        Scr_PrintSourcePos(channel, gScrParserPub.sourceBufferLookup[bufferIndex].buf, gScrParserPub.sourceBufferLookup[bufferIndex].sourceBuf, Scr_GetPrevSourcePos(codePos - 1, index));
        return;
      }
    }
    else if ( Scr_IsInOpcodeMemory(codePos - 1) )
    {
      Com_Printf(channel, "@ %d\n", codePos - gScrVarPub.programBuffer);
      return;
    }
    Com_Printf(channel, "%s\n\n", codePos);
  }
}


char *__cdecl Scr_AddSourceBuffer( const char *filename, const char *extFilename, const char *codePos, bool archive)
{
  const char *source;
  char c;
  SaveSourceBufferInfo *saveSourceBuffer;
  signed int len;
  char *dest;
  int i;
  char *sourceBuf;

  if ( !archive || !gScrParserGlob.saveSourceBufferLookup )
  {
    return Scr_ReadFile(filename, extFilename, codePos, archive);
  }
  assert(gScrParserGlob.saveSourceBufferLookupLen > 0);
  --gScrParserGlob.saveSourceBufferLookupLen;
  saveSourceBuffer = &gScrParserGlob.saveSourceBufferLookup[gScrParserGlob.saveSourceBufferLookupLen];
  len = saveSourceBuffer->len;

  assert(len >= -1);
  if ( len >= 0 )
  {
    sourceBuf = (char*)Hunk_AllocateTempMemoryHigh(len + 1);
    source = saveSourceBuffer->sourceBuf;
    dest = sourceBuf;
    for ( i = 0; i < len; ++i )
    {
      c = *source++;
      if ( c )
      {
        *dest++ = c;
      }
      else
      {
        *dest++ = '\n';
      }
    }
    *dest = 0;
    if ( saveSourceBuffer->sourceBuf )
    {
      Hunk_FreeDebugMem(gScrParserGlob.saveSourceBufferLookup[gScrParserGlob.saveSourceBufferLookupLen].sourceBuf);
    }
  }
  else
  {
    sourceBuf = 0;
  }
#ifdef CODOL_SERVER
  return Scr_PrepareChildThreadSource(extFilename,codePos,sourceBuf,len,archive);
#else
  Scr_AddSourceBufferInternal(extFilename, codePos, sourceBuf, len, 1, archive);
  return sourceBuf;
#endif
}


};

void __cdecl Scr_GetTextSourcePos(const char *buf, const char *codePos, char *line)
{
  unsigned int bufferIndex;
  int col;

  if ( gScrVarPub.developer && codePos && codePos != &g_EndPos && gScrVarPub.programBuffer && Scr_IsInOpcodeMemory(codePos) )
  {
    bufferIndex = Scr_GetSourceBuffer(codePos - 1);
    Scr_GetLineInfo(gScrParserPub.sourceBufferLookup[bufferIndex].sourceBuf, Scr_GetPrevSourcePos(codePos - 1, 0), &col, line);
  }
  else
  {
    *line = 0;
  }
}

void CompileError2(const char *codePos, const char *msg, ...)
{
  char line[1024];
  char text[1024];
  va_list va;

  va_start(va, msg);
  assert(!gScrVarPub.evaluate);

  assert(Scr_IsInOpcodeMemory( codePos ));

//  Monkey_GrabComPrints(1);
//  Scr_IgnoreLeaks( );
  Com_PrintError(CON_CHANNEL_PARSERSCRIPT, "\n");
  Com_PrintError(CON_CHANNEL_PARSERSCRIPT, "******* %s script compile error *******\n", "Server");
  
  vsnprintf(text, sizeof(text), msg, va);
  Com_PrintError(CON_CHANNEL_PARSERSCRIPT, "%s: ", text);
  Scr_PrintPrevCodePos(CON_CHANNEL_PARSERSCRIPT, codePos, 0);
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "************************************\n");
//  Monkey_Error(0);
  Scr_GetTextSourcePos(gScrParserPub.sourceBuf, codePos, line);
  Com_Error(ERR_DROP, "%s script compile error\n%s\n%s\n(see console for details)\n", "Server", text, line);
}



