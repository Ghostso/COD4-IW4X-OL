import re
b=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
# 找 STUN 配置块完整内容
def ctx(va, back, fwd):
    off=va-0x714000; seg=b[off-back:off+fwd]; base=va-back
    print("=== around VA 0x%08X ==="%va)
    i=0
    while i<len(seg):
        j=i
        while j<len(seg) and 32<=seg[j]<127: j+=1
        if j-i>=3:
            print("  VA 0x%08X  %r"%(base+i, seg[i:j].decode("latin1")[:130])); i=j
        else: i+=1
ctx(0x00DE0028, 0x60, 0x200)
print()
print("=== 搜 STUN / TQoS / qos 配置项 ===")
for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{3,40}", b):
    s=m.group().decode("latin1")
    if re.match(r"^(STUN|TQoS|tqos|Qos|qos|QOS|stun)", s):
        print("  VA 0x%08X  %s" % (0x714000+m.start(), s))
