#include "codol_script_lower.h"
#include <string>
#include <vector>
#include <set>
#include <map>
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <stdexcept>

/* Source-to-source adaptation of the extended (IW4 era) GSC constructs used by
 * the CoDOL script corpus into the grammar the retained native scanner/parser
 * actually accepts. The accepted grammar was read out of the retained flex/bison
 * tables in src/asmsource/_scr_yacc.asm, not assumed:
 *
 *   - foreach/in/do are not keywords; there is no ternary and no do/while.
 *   - There is no general unary minus: -5 is a negative literal, but -b, -f(),
 *     -self.x and -( ... ) are all rejected. A substituted value must therefore
 *     never land directly after a prefix + or -.
 *   - << >> <<= >>= are supported natively and need no adaptation.
 *   - .size is a single token, so nothing may be spliced between . and size.
 *   - ' is a bad token, not a string delimiter.
 *   - call [[f]]() parses only because call lexes as an identifier, which makes
 *     it the self receiver of the pointer call. The marker must be removed.
 */

namespace {
struct Token { size_t begin,end; std::string text; bool id; };
struct Edit { size_t begin,end; std::string text; };
struct Unsupported { const char *construct; size_t offset; };
bool alpha(char c) { return (c>='a' && c<='z') || (c>='A' && c<='Z') || c=='_'; }
bool digit(char c) { return c>='0' && c<='9'; }
bool space(char c) { return c==' ' || c=='\t' || c=='\r' || c=='\n'; }
std::string lower(std::string s) { for(char &c:s) if(c>='A' && c<='Z') c+=32; return s; }

/* Identifiers that cannot end a value, so a following + or - is a prefix sign. */
const char *const kNonValueWords[]={
    "return","wait","thread","if","else","while","for","foreach","switch",
    "case","default","break","continue","endon","notify","waittill",
    "waittillmatch","waittillframeend","breakpoint","prof_begin","prof_end",
    "breakon","in","childthread"
};

/* Engine-supplied builtin lookup: 0 unknown, 1 function, 2 method. Null (the
 * standalone fixture) leaves ::name pointers untouched. */
int (*g_builtinResolver)(const char *)=0;

struct Lowerer {
    std::string source;
    std::vector<Token> tokens;
    std::set<std::string> ids;
    void require(bool ok) { if(!ok) throw std::runtime_error("extended syntax"); }
    void reject(const char *construct,size_t offset) {
        Unsupported failure={construct,offset}; throw failure;
    }
    explicit Lowerer(const char *s,size_t n):source(s,n) {
        for(size_t p=0;p<n;) {
            size_t begin=p; char c=s[p];
            if(space(c)) { ++p; continue; }
            if(c=='/' && p+1<n && s[p+1]=='/') { while(p<n && s[p]!='\n') ++p; continue; }
            if(c=='/' && p+1<n && s[p+1]=='*') {
                p+=2; while(p+1<n && !(s[p]=='*' && s[p+1]=='/')) ++p;
                require(p+1<n); p+=2; continue;
            }
            bool id=alpha(c);
            /* Only " opens a string. The retained scanner rejects ' as a bad
             * token, so treating it as a delimiter here would let this pass
             * swallow real code between two unrelated apostrophes. */
            if(c=='"') {
                ++p; bool closed=false;
                while(p<n) { if(s[p]=='\\') { require(p+1<n); p+=2; }
                    else if(s[p]=='\n') break;
                    else if(s[p++]=='"') { closed=true; break; } }
                require(closed);
            } else if(id) { ++p; while(p<n && (alpha(s[p]) || digit(s[p]))) ++p; }
            else ++p;
            std::string text=source.substr(begin,p-begin); if(id) { text=lower(text); ids.insert(text); }
            tokens.push_back({begin,p,text,id});
        }
        tokens.push_back({n,n,"",false});
    }
    bool at(size_t p,const char *s) { return p<tokens.size() && tokens[p].text==s; }
    size_t group(size_t p,unsigned depth=0) {
        require(depth<256);
        std::string end;
        if(at(p,"(")) end=")"; else if(at(p,"[")) end="]"; else if(at(p,"{")) end="}"; else require(false);
        for(++p;p<tokens.size()-1;++p) {
            if(tokens[p].text==end) return p+1;
            if(at(p,"(") || at(p,"[") || at(p,"{")) p=group(p,depth+1)-1;
            else require(!at(p,")") && !at(p,"]") && !at(p,"}"));
        }
        require(false); return 0;
    }
    size_t statement(size_t p,unsigned depth=0) {
        require(depth<256 && p<tokens.size()-1);
        if(at(p,"{")) return group(p);
        if(at(p,"if") || at(p,"while") || at(p,"for") || at(p,"foreach") || at(p,"switch")) {
            bool condition=at(p,"if"); require(at(p+1,"("));
            size_t end=statement(group(p+1),depth+1);
            if(condition && at(end,"else")) end=statement(end+1,depth+1);
            return end;
        }
        if(at(p,"do")) {
            p=statement(p+1,depth+1); require(at(p,"while") && at(p+1,"("));
            p=group(p+1); require(at(p,";")); return p+1;
        }
        while(p<tokens.size()-1) {
            if(at(p,";")) return p+1;
            require(!at(p,"}"));
            if(at(p,"(") || at(p,"[") || at(p,"{")) p=group(p); else ++p;
        }
        require(false); return 0;
    }
    std::string temporary(unsigned serial,const char *suffix) {
        std::string name="__codol_foreach_"+std::to_string(serial)+suffix;
        while(ids.count(name)) name+="_";
        ids.insert(name); return name;
    }
    std::string apply(std::vector<Edit> &edits) {
        std::stable_sort(edits.begin(),edits.end(),[](const Edit &a,const Edit &b) {
            return a.begin<b.begin || (a.begin==b.begin && a.end<b.end);
        });
        std::string result; size_t offset=0;
        for(const Edit &e:edits) {
            require(e.begin>=offset);
            result.append(source,offset,e.begin-offset); result+=e.text; offset=e.end;
            require(result.size()<=32*1024*1024);
        }
        result.append(source,offset,source.size()-offset); return result;
    }

    /* IW4 statement keyword. The retained scanner lexes it as an identifier,
     * so "self childthread f()" is a syntax error and "childthread f()" would
     * silently compile as a call whose self is the undefined variable
     * "childthread". Recognition, the compiler opcode tagging and the VM
     * opcodes now live in codol_script_childthread.cpp; this pass only has to
     * leave the keyword alone, and keeps it in kNonValueWords so the sign
     * disambiguation stays correct. */
    void checkUnsupported() {
        /* childthread is recognised and compiled natively by
         * codol_script_childthread.cpp, which runs on the buffer this
         * pass produces, so it must not be rejected or rewritten here. */
    }

    /* --- file scope constants ------------------------------------------- */
    static bool nonValueWord(const std::string &s) {
        for(const char *w:kNonValueWords) if(s==w) return true;
        return false;
    }
    /* True when token p can end a value, making a following +/- binary. */
    bool valueEnd(size_t p) {
        if(p>=tokens.size()) return false;
        const Token &t=tokens[p];
        if(t.text==")" || t.text=="]") return true;
        if(t.id) return !nonValueWord(t.text);
        return !t.text.empty() && (digit(t.text[0]) || t.text[0]=='"');
    }
    /* Validates a declaration value as a constant expression and produces its
     * substitution text. Accepts numbers, strings, &"localized", true/false/
     * undefined, earlier constants of this file, + - * / % ! ~, balanced
     * parentheses and commas inside them. Returns false for anything else, in
     * which case the statement is not a constant declaration at all. */
    bool constantValue(size_t first,size_t last,
                       const std::map<std::string,std::string> &values,
                       const std::map<std::string,bool> &literals,
                       std::string &out,bool &single) {
        const std::string &s=source;
        size_t p=tokens[first].begin,n=tokens[last].end,depth=0,count=0;
        std::string body; std::string only; bool onlyLiteral=false;
        bool previousEndsValue=false,joinSignedNumber=false;
        while(p<n) {
            if(space(s[p])) { ++p; continue; }
            /* Comments are whitespace to the native scanner. This parser reads
             * the source span between tokens, so it must skip them too. */
            if(s[p]=='/' && p+1<n && s[p+1]=='/') {
                p+=2; while(p<n && s[p]!='\n') ++p;
                continue;
            }
            if(s[p]=='/' && p+1<n && s[p+1]=='*') {
                p+=2;
                while(p+1<n && !(s[p]=='*' && s[p+1]=='/')) ++p;
                if(p+1>=n) return false;
                p+=2; continue;
            }
            std::string item; bool literal=false;
            if(s[p]=='&' && p+1<n && s[p+1]=='"') { item="&"; ++p; }
            if(!item.empty() || s[p]=='"') {
                size_t begin=p; ++p; bool closed=false;
                while(p<n) { if(s[p]=='\\') { if(p+1>=n) return false; p+=2; }
                    else if(s[p]=='\n') return false;
                    else if(s[p++]=='"') { closed=true; break; } }
                if(!closed) return false;
                item+=s.substr(begin,p-begin); literal=true;
            } else if(digit(s[p]) || (s[p]=='.' && p+1<n && digit(s[p+1]))) {
                size_t begin=p; while(p<n && digit(s[p])) ++p;
                if(p<n && s[p]=='.') {
                    ++p; if(p>=n || !digit(s[p])) return false;
                    while(p<n && digit(s[p])) ++p;
                }
                /* The retained scanner has no exponent or hexadecimal literal. */
                if(p<n && (alpha(s[p]) || s[p]=='.')) return false;
                item=s.substr(begin,p-begin); literal=true;
            } else if(alpha(s[p])) {
                size_t begin=p; while(p<n && (alpha(s[p]) || digit(s[p]))) ++p;
                std::string name=lower(s.substr(begin,p-begin));
                if(name=="true" || name=="false" || name=="undefined") { item=name; literal=true; }
                else {
                    auto found=values.find(name); if(found==values.end()) return false;
                    item=found->second;
                    /* An alias of a single literal remains a single literal.
                     * Otherwise A=5; B=A; return -B would be rejected as a
                     * signed compound constant even though B expands to 5. */
                    auto kind=literals.find(name);
                    literal=kind!=literals.end() && kind->second;
                }
            } else if(std::strchr("+-*/%!~(),",s[p])) {
                if(s[p]=='(') ++depth;
                else if(s[p]==')') { if(!depth) return false; --depth; }
                else if(s[p]==',' && !depth) return false;
                item.assign(1,s[p]); ++p;
            } else return false;
            if(!count) { only=item; onlyLiteral=literal; }
            /* The retained scanner accepts a signed numeric literal, but not
             * general unary minus. Keep its sign adjacent when reconstructing
             * a file-scope constant; binary operators still need separation. */
            bool number=literal && !item.empty() &&
                (digit(item[0]) || (item[0]=='.' && item.size()>1 && digit(item[1])));
            if(count && !(joinSignedNumber && number)) body+=' ';
            body+=item; ++count;
            joinSignedNumber=(item=="-" || item=="+") && !previousEndsValue;
            previousEndsValue=literal || item==")";
        }
        if(depth || !count) return false;
        if(count==1 && onlyLiteral) { out=only; single=true; return true; }
        out="("+body+")"; single=false; return true;
    }
    std::string constants() {
        std::map<std::string,std::string> values;
        std::map<std::string,bool> literals;
        std::set<size_t> declarations;
        std::vector<Edit> edits;
        for(size_t i=0;i+1<tokens.size();++i) {
            if(at(i,"{")) { i=group(i)-1; continue; }
            if(!tokens[i].id || !at(i+1,"=") || at(i+2,"=")) continue;
            size_t semicolon=i+2;
            while(semicolon<tokens.size()-1 && !at(semicolon,";") && !at(semicolon,"{")) ++semicolon;
            /* Not a declaration. Step back onto a { so the brace-skipping
             * branch still keeps this scan at file scope. */
            if(!at(semicolon,";")) { i=at(semicolon,"{") ? semicolon-1 : semicolon; continue; }
            if(semicolon<=i+2) { i=semicolon; continue; }
            std::string value; bool single=false;
            if(!constantValue(i+2,semicolon-1,values,literals,value,single)) { i=semicolon; continue; }
            if(values.count(tokens[i].text)) reject("duplicate file constant",tokens[i].begin);
            values.emplace(tokens[i].text,value);
            literals.emplace(tokens[i].text,single);
            size_t begin=tokens[i].begin,end=tokens[semicolon].end;
            std::string blank=source.substr(begin,end-begin);
            for(char &c:blank) if(c!='\n' && c!='\r') c=' ';
            edits.push_back({begin,end,blank});
            for(size_t j=i;j<=semicolon;++j) declarations.insert(j);
            i=semicolon;
        }
        if(values.empty()) return {};
        for(size_t i=0;i+1<tokens.size();++i) {
            if(!tokens[i].id || declarations.count(i)) continue;
            auto value=values.find(tokens[i].text); if(value==values.end()) continue;
            // Qualified members, animation references and script paths are
            // separate namespaces, and so are function names.
            if(i && (at(i-1,".") || at(i-1,":") || at(i-1,"\\") || at(i-1,"#"))) continue;
            /* %name is an animation reference only in prefix position.
             * In value % CONSTANT it is the remainder operator: leaving the
             * constant untouched would refer to a declaration erased above. */
            if(i && at(i-1,"%") && !(i>=2 && valueEnd(i-2))) continue;
            /* A case label is a value, unlike the module in module::func. */
            if((at(i+1,":") && !(i && at(i-1,"case"))) || at(i+1,"\\")) continue;
            if(at(i+1,"(")) continue;
            if(at(i+1,"=") && !at(i+2,"=")) reject("assignment to a file constant",tokens[i].begin);
            if((at(i+1,"+") || at(i+1,"-") || at(i+1,"*") || at(i+1,"/") ||
                at(i+1,"%") || at(i+1,"&") || at(i+1,"|") || at(i+1,"^")) &&
               (at(i+2,"=") || ((at(i+1,"+") || at(i+1,"-")) &&
                tokens[i+1].text==tokens[i+2].text)))
                reject("assignment to a file constant",tokens[i].begin);
            if(((at(i+1,"<") && at(i+2,"<")) ||
                (at(i+1,">") && at(i+2,">"))) && at(i+3,"="))
                reject("assignment to a file constant",tokens[i].begin);
            /* The retained grammar has no unary minus over a parenthesized
             * expression, so a compound value may not follow a prefix sign. */
            if(!literals[tokens[i].text] && i && (at(i-1,"-") || at(i-1,"+")) &&
               !(i>=2 && valueEnd(i-2)))
                reject("signed file constant",tokens[i].begin);
            edits.push_back({tokens[i].begin,tokens[i].end,value->second});
        }
        return apply(edits);
    }
    std::string run() {
        std::vector<Edit> edits; unsigned serial=0;
        for(size_t i=0;i+1<tokens.size();++i) if(at(i,"foreach")) {
            require(at(i+1,"(")); size_t close=group(i+1)-1,p=i+2;
            require(tokens[p].id); std::string value=tokens[p++].text,key;
            if(at(p,",")) { key=value; ++p; require(tokens[p].id); value=tokens[p++].text; }
            require(at(p,"in") && p+1<close); ++p;
            size_t body=close+1,end=statement(body);
            std::string expression=source.substr(tokens[p].begin,tokens[close].begin-tokens[p].begin);
            for(size_t j=p;j+2<close;++j) if(at(j,"call") && at(j+1,"[") && at(j+2,"["))
                expression.replace(tokens[j].begin-tokens[p].begin,4,"    ");
            std::string array=temporary(serial,"a"),keys=temporary(serial,"k"),index=temporary(serial++,"i");
            std::string replacement="{ "+array+"=("+expression+"); "+keys+"=getarraykeys("+array+"); for ("+index+"=0; "+index+"<"+keys+".size; "+index+"++) { ";
            if(!key.empty()) replacement+=key+"="+keys+"["+index+"]; ";
            replacement+=value+"="+array+"["+keys+"["+index+"]]; ";
            size_t begin=tokens[i].begin,finish=tokens[close].end;
            size_t original_lines=std::count(source.begin()+begin,source.begin()+finish,'\n');
            size_t generated_lines=std::count(replacement.begin(),replacement.end(),'\n');
            replacement.append(original_lines-generated_lines,'\n');
            edits.push_back({begin,finish,replacement});
            edits.push_back({tokens[end-1].end,tokens[end-1].end," } }"});
        }
        // IW4 explicit pointer-call marker; IW3 spells this [[func]]().
        for(size_t i=0;i+2<tokens.size();++i) if(at(i,"call") && at(i+1,"[") && at(i+2,"[")) {
            bool covered=false;
            for(const Edit &e:edits) if(tokens[i].begin>=e.begin && tokens[i].begin<e.end) covered=true;
            if(!covered) edits.push_back({tokens[i].begin,tokens[i].end,"    "});
        }
        builtinPointers(edits);
        if(edits.empty()) return {};
        return apply(edits);
    }

    /* IW4 lets a script take a pointer to a builtin (level.f = ::laserOff;
     * level.func["precacheMpAnim"] = ::precacheMpAnim;) and call it through
     * [[ ]] like any script function; IW4 compiles OP_GetBuiltinFunction /
     * OP_GetBuiltinMethod for that. The retained IW3 compiler resolves ::name
     * only against the functions of the file (EmitFunction in
     * _scr_compiler.asm) and its VM has one pointer type, the script code
     * position. A ::name that names no function of this file but a registered
     * builtin is therefore redirected to a forwarding script function appended
     * to the file, which calls the builtin with the arguments it received
     * (builtins take at most six, and an undefined argument ends the list the
     * way an omitted one does). A method builtin is forwarded on self, so a
     * pointer call without a receiver fails the same way IW4's does. A ::name
     * that is neither stays untouched and keeps its compile error. Nothing is
     * appended unless a pointer is actually rewritten. */
    void builtinPointers(std::vector<Edit> &edits) {
        if(!g_builtinResolver) return;
        std::set<std::string> defined;
        for(size_t i=0;i+1<tokens.size();++i) {
            if(at(i,"{")) { i=group(i)-1; continue; }
            if(tokens[i].id && at(i+1,"(")) {
                size_t end=group(i+1);
                if(at(end,"{")) defined.insert(tokens[i].text);
            }
        }
        std::map<std::string,std::pair<std::string,int> > wrappers;
        for(size_t i=0;i+2<tokens.size();++i) {
            if(!at(i,":") || !at(i+1,":") || !tokens[i+2].id) continue;
            if(i && (tokens[i-1].id || at(i-1,")") || at(i-1,"]"))) continue; /* module::name, case labels */
            const std::string &name=tokens[i+2].text;
            if(defined.count(name)) continue;
            int kind=g_builtinResolver(name.c_str());
            if(kind!=1 && kind!=2) continue;
            auto found=wrappers.find(name);
            if(found==wrappers.end()) {
                std::string wrapper="__codol_builtin_"+name;
                while(ids.count(wrapper)) wrapper+="_";
                ids.insert(wrapper);
                found=wrappers.emplace(name,std::make_pair(wrapper,kind)).first;
            }
            edits.push_back({tokens[i+2].begin,tokens[i+2].end,found->second.first});
        }
        if(wrappers.empty()) return;
        std::string tail="\n";
        for(const auto &w:wrappers) {
            const std::string &name=w.first,&wrapper=w.second.first;
            const std::string receiver=w.second.second==2 ? "self " : "";
            tail+=wrapper+"(a0,a1,a2,a3,a4,a5)\n{\n";
            std::string args;
            for(unsigned n=0;n<6;++n) {
                tail+="\tif(!isdefined(a"+std::to_string(n)+")) return "+receiver+name+"("+args+");\n";
                if(n) args+=",";
                args+="a"+std::to_string(n);
            }
            tail+="\treturn "+receiver+name+"("+args+");\n}\n";
        }
        edits.push_back({source.size(),source.size(),tail});
    }
};

const char *g_diagnostic=0;
unsigned g_diagnosticLine=0;

void recordDiagnostic(const char *construct,const char *source,size_t offset)
{
    unsigned line=1;
    for(size_t i=0;i<offset;++i) if(source[i]=='\n') ++line;
    g_diagnostic=construct; g_diagnosticLine=line;
}
}

/* Optional stage trace. The server installs a printer so a fault inside the
 * pass can be located; the standalone fixtures leave it null. */
/* Standalone check that the C++ containers this pass relies on behave in the
 * binary they are linked into. Returns the observed set size; 3 is correct. */
extern "C" int CODOL_ScriptLowerSelfTest(void)
{
    std::set<std::string> probe;
    probe.insert("alpha"); probe.insert("beta"); probe.insert("gamma"); probe.insert("alpha");
    return (int)probe.size();
}
int CODOL_LowerScriptSyntax(const char *source,size_t length,char **out,size_t *out_length)
{
    g_diagnostic=0; g_diagnosticLine=0;
    if(!source || !out || !out_length || length>16*1024*1024 || std::memchr(source,0,length)) return -1;
    try {
        Lowerer lowerer(source,length);
        lowerer.checkUnsupported();
        std::string constants=lowerer.constants();
        std::string result;
        if(constants.empty()) result=lowerer.run();
        else {
            Lowerer expanded(constants.data(),constants.size()); result=expanded.run();
            if(result.empty()) result=constants;
        }
        if(result.empty()) return 0;
        if(result.size()>32*1024*1024) return -1;
        char *data=static_cast<char *>(std::malloc(result.size()+1)); if(!data) return -1;
        std::memcpy(data,result.c_str(),result.size()+1); *out=data; *out_length=result.size(); return 1;
    }
    catch(const Unsupported &failure) {
        recordDiagnostic(failure.construct,source,failure.offset); return -1;
    }
    catch(...) { return -1; }
}

const char *CODOL_LowerScriptDiagnostic(unsigned *line)
{
    if(line) *line=g_diagnosticLine;
    return g_diagnostic;
}

void CODOL_SetScriptBuiltinResolver(int (*resolver)(const char *))
{
    g_builtinResolver=resolver;
}
