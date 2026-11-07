/* Native syscall conditionals. Preserve source offsets by blanking excluded
 * text, rather than wrapping it in comments that its own comments can close.
 * The condition vocabulary is the retained Scr_ScriptPreCompile vocabulary;
 * this does not introduce a C preprocessor or evaluate arbitrary GSC. */
#ifdef CODOL_SERVER
#include "q_shared.h"
#include "qcommon.h"
#include "cmd.h"
#include "scr_vm.h"
#include "codol_script_precompile.h"
#include <string.h>

typedef struct {
    int parent_active, condition, saw_else;
    unsigned line;
} codol_conditional_t;

static int directive(const char *p, const char *word)
{
    size_t n = strlen(word);
    return !strncmp(p, word, n) &&
        (!p[n] || p[n]==' ' || p[n]=='\t' || p[n]=='\r' || p[n]=='\n');
}

static void blank_line(char *start, char *end)
{
    for(; start<end; ++start)
        if(*start!='\r') *start=' ';
}

/* Remove comments before recognizing directives, preserving offsets and CRLF.
 * This also handles a comment that begins on a directive line: erasing that
 * line must not leave its continuation exposed as script on the next line.
 * Strings (including escaped quotes and comment-like text) remain untouched. */
static void blank_comments(char *p, char *end, unsigned *block, unsigned line)
{
    int quoted=0;
    while(p<end) {
        if(*block) {
            if(*p=='*' && p+1<end && p[1]=='/') {
                *block=0; *p++=' '; *p++=' ';
            } else { if(*p!='\r') *p=' '; ++p; }
        } else if(quoted) {
            if(*p=='\\' && p+1<end) p+=2;
            else { if(*p=='"') quoted=0; ++p; }
        } else if(*p=='/' && p+1<end && p[1]=='/') {
            blank_line(p,end); return;
        } else if(*p=='/' && p+1<end && p[1]=='*') {
            *block=line; *p++=' '; *p++=' ';
        }
        else { if(*p=='"') quoted=1; ++p; }
    }
}

void CODOL_PrecompileScript(char *source, const char *filename)
{
    codol_conditional_t stack[128];
    unsigned line=1, depth=0, block=0;
    int active=1;
    char *start=source;
    if(!source) return;
    while(*start) {
        char *end=strchr(start,'\n'), *p=start;
        int kind=0;
        if(!end) end=start+strlen(start);
        blank_comments(start,end,&block,line);
        while(p<end && (*p==' ' || *p=='\t' || *p=='\r')) ++p;
        if(p<end) {
            if(directive(p,"#if")) kind=1;
            else if(directive(p,"#else")) kind=2;
            else if(directive(p,"#endif")) kind=3;
        }
        if(kind) {
            const char *error=NULL;
            char saved=*end;
            *end=0;
            Cmd_TokenizeString(p);
            if(kind==1) {
                const char *func=Cmd_Argv(1);
                int negate=(*func=='!'), condition=0;
                if(negate) ++func;
                if(Cmd_Argc()!=3 || !*Cmd_Argv(2) ||
                   Q_stricmp(func,"isSyscallDefined"))
                    error="expected #if [!]isSyscallDefined <name>";
                else if(depth==sizeof(stack)/sizeof(stack[0]))
                    error="conditional nesting limit exceeded";
                else {
                    if(active) condition=!!Scr_IsSyscallDefined(Cmd_Argv(2)) != negate;
                    stack[depth].parent_active=active;
                    stack[depth].condition=condition;
                    stack[depth].saw_else=0;
                    stack[depth].line=line;
                    ++depth;
                    active=active && condition;
                }
            } else if(Cmd_Argc()!=1) error="unexpected conditional arguments";
            else if(!depth) error="conditional directive without #if";
            else if(kind==2) {
                if(stack[depth-1].saw_else) error="duplicate #else";
                else {
                    stack[depth-1].saw_else=1;
                    active=stack[depth-1].parent_active && !stack[depth-1].condition;
                }
            } else active=stack[--depth].parent_active;
            Cmd_EndTokenizedString();
            *end=saved;
            if(error) {
                Com_Error(ERR_SCRIPT,"Script precompile error: %s, line %u: %s",
                          filename,line,error);
                return;
            }
            blank_line(start,end);
        } else {
            if(!active) blank_line(start,end);
        }
        if(!*end) break;
        start=end+1; ++line;
    }
    if(block)
        Com_Error(ERR_SCRIPT,"Script precompile error: %s, line %u: unterminated comment",
                  filename,block);
    else if(depth)
        Com_Error(ERR_SCRIPT,"Script precompile error: %s, line %u: missing #endif",
                  filename,stack[depth-1].line);
}
#endif
