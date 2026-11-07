def compute(a1,a2,a3,count1bits):
    b=8+count1bits
    last=-1
    for i,s in a1:
        b += 1 if i==last+1 else 14; last=i; b += 8+len(s)*8
    b+=10; last=-1
    for i,v in a2:
        b += 1 if i==last+1 else 14; last=i; b+=10
    b+=10; last=-1
    for i,fa,fb,ex in a3:
        b += 1 if i==last+1 else 14; last=i; b+=10+7+4+len(ex)*12
    return b
cases=[
 ("empty A1/A2/A3", [], [], []),
 ("A1=[(0,'')], rest empty", [(0,'')], [], []),
 ("A1=[(0,\"a\")], rest empty", [(0,'a')], [], []),
 ("A1=[(0,\"a\")], A2=[(0,1)]", [(0,'a')], [(0,1)], []),
 ("full: A1=[(0,'a')] A2=[(0,1),(1,2)] A3=[(0,1023,127,[4095,1])]", [(0,'a')], [(0,1),(1,2)], [(0,1023,127,[4095,1])]),
 ("A1=[(0,'a'),(5,'bb')]", [(0,'a'),(5,'bb')], [], []),
]
print("=== 0x06 bit offset (offset counted from the FIRST bit of 0x04) ===")
print("%-62s %-10s %-10s" % ("case","count1=16","count1=8"))
for name,a1,a2,a3 in cases:
    b16=compute(a1,a2,a3,16); b8=compute(a1,a2,a3,8)
    print("%-62s %-10s %-10s" % (name,"%d%s"%(b16,"*" if b16%8 else ""),"%d%s"%(b8,"*" if b8%8 else "")))
print()
print("* = NOT byte-aligned")
print()
print("NOTE: 0x04 itself is 8 bits, count1 16 bits -> the body after the count starts at bit 24 (3 bytes, aligned).")
print("      Since every A1 string is written as whole bytes and every index-delta for consecutive indices is 1 bit,")
print("      misalignment appears whenever an index-delta is the 14-bit form (1+13).")