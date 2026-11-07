#include "codol_script_lower.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <string>
#include <algorithm>
#include <cstdio>
static std::string transform(const char *s)
{
    char *out=NULL; size_t n=0;
    assert(CODOL_LowerScriptSyntax(s,strlen(s),&out,&n)==1 && n==strlen(out));
    std::string result(out); free(out); return result;
}
int main()
{
    char *out=(char *)1; size_t n=99;
    const char *plain="main(){ s=\"foreach (x in fake)\"; /* foreach */ // foreach\n return; }";
    assert(CODOL_LowerScriptSyntax(plain,strlen(plain),&out,&n)==0 && out==(char *)1 && n==99);
    const char *nested="main(){ __CODOL_FOREACH_0A=1; foreach (key, value in makeArray())\n if(value) foreach (x in value) { continue; } else break; }";
    std::string result=transform(nested);
    assert(result.find("__codol_foreach_0a_=(makeArray())")!=std::string::npos);
    assert(result.find("key=__codol_foreach_0k[")!=std::string::npos);
    assert(result.find("makeArray()",result.find("makeArray()")+1)==std::string::npos);
    assert(std::count(result.begin(),result.end(),'\n')==1);
    assert(result.find(" else break; } }")!=std::string::npos);
    result=transform("main(){ foreach ( v\n in\n getArray(1, (2,3,4))\n )\n do { break; } while(0); }");
    assert(std::count(result.begin(),result.end(),'\n')==4);
    assert(result.find("while(0); } }")!=std::string::npos);
    result=transform("main(){ self call [[level.func[func]]](); call [[callback]](); }");
    assert(result=="main(){ self      [[level.func[func]]]();      [[callback]](); }");
    result=transform("main(){ foreach(v in call [[getItems]]()) self call [[useItem]](v); }");
    assert(result.find("call")==std::string::npos);
    const char *bad[]={"foreach(x in a)","foreach(x a) {}","foreach(x in a) {", "foreach(,x in a);"};
    for(const char *s:bad) assert(CODOL_LowerScriptSyntax(s,strlen(s),&out,&n)==-1 && out==(char *)1 && n==99);
    result=transform("TABLE = \"mp/test.csv\";\nmain(){ x=table; y=self.table; z=\"TABLE\"; /* TABLE */ if(TABLE==x) return TABLE; }");
    assert(result.find("x=\"mp/test.csv\"")!=std::string::npos);
    assert(result.find("y=self.table; z=\"TABLE\"; /* TABLE */")!=std::string::npos);
    assert(result.find("if(\"mp/test.csv\"==x)")!=std::string::npos);
    assert(std::count(result.begin(),result.end(),'\n')==1);
    result=transform("A=\"a\"; main(){ if(x==A && y || A==z) return A; }");
    assert(result.find("x==\"a\" && y || \"a\"==z")!=std::string::npos);
    result=transform("PATH=\"abc\"; main(){ foreach(x in get(PATH)) call [[fn]](PATH); }");
    assert(result.find("get(\"abc\")")!=std::string::npos && result.find("[[fn]](\"abc\")")!=std::string::npos);
    result=transform("N=3; F=-1.5; main(){ return N+F; }");
    assert(result.find("return 3+(-1.5);")!=std::string::npos);
    result=transform("A=3-1; B=-.5; main(){ return A+B; }");
    assert(result.find("return (3 - 1)+(-.5);")!=std::string::npos);
    const char *non_constant="A=lookup();main(){}";
    assert(CODOL_LowerScriptSyntax(non_constant,strlen(non_constant),&out,&n)==0 &&
           out==(char *)1 && n==99);
    result=transform("A=1+2;main(){return A;}");
    assert(result.find("return (1 + 2);")!=std::string::npos);
    const char *bad_constants[]={"A=\"a\";A=\"b\";",
        "A=\"a\";main(){A=\"b\";}","A=\"a\";main(){A++;}"};
    for(const char *s:bad_constants)
        assert(CODOL_LowerScriptSyntax(s,strlen(s),&out,&n)==-1 && out==(char *)1 && n==99);
    puts("PASS: native foreach lowering, nesting, statement bounds, comments, names and line preservation");
}
