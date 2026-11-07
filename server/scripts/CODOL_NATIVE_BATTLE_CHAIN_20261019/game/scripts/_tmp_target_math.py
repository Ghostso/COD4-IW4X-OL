import csv,collections,math
rows=list(csv.DictReader(open(r"scripts/_out/ca8000_boundary_audit.csv",newline="")))
vals=[]
for r in rows:
 if r["region"]=="TEMPLATE_475" and r["value_class"]=="IN_IMAGE_VA":
  vals.append(int(r["raw_value_hex"],16)-0x400000)
print("template ptr count",len(vals),"unique",len(set(vals)))
print("pages_256",collections.Counter(x>>8 for x in vals))
print("pages_1024",collections.Counter(x>>10 for x in vals))
aligned4=sum(x%4==0 for x in vals); aligned2=sum(x%2==0 for x in vals)
print("align4",aligned4,"align2",aligned2,"mod4",collections.Counter(x%4 for x in vals))
# entropy of ideal random payload vs actual target lack of backing
print("nearest_byte_span",hex(min(vals)),hex(max(vals)),"span",max(vals)-min(vals))
# slot refs counts and target refs
refs=[int(r["ff_refs"]) for r in rows if r["region"]=="TEMPLATE_475"]
print("slot refs total",sum(refs),"nonzero",sum(x>0 for x in refs),"max",max(refs))
# caller RVA clustering: exact values not multiset because CSV unique refs; count entries by slot
cnt=collections.Counter()
for r in rows:
 for x in filter(None,r["caller_rvas"].split()): cnt[int(x,16)]+=1
print("callers",len(cnt),"refs",sum(cnt.values()))
# count callers that point to any template target? no, caller means FF site, not call graph.
print("low2",collections.Counter(v%4 for v in vals))
