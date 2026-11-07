import io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
base=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data"
def ld(n):
    return [l.rstrip("\n") for l in open(base+"\\"+n,encoding="utf-8",errors="replace")]
new=ld("strings_NEW_80816711.txt"); old=ld("strings_OLD_28366ae9.txt"); c13=ld("strings_1113_a96c5dfb.txt")
sn,so,sc=set(new),set(old),set(c13)
print("NEW strings",len(sn),"OLD",len(so),"1113",len(sc))
print("NEW-only vs OLD",len(sn-so))
print("OLD-only vs NEW",len(so-sn))
print("NEW-only vs 1113",len(sn-sc))
print("common NEW&OLD",len(sn&so))
for tag,s in [("NEW",sn),("OLD",so),("1113",sc)]:
    print(tag,"mbedtls count",sum(1 for x in s if "mbedtls" in x))
