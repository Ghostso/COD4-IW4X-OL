# -*- coding: utf-8 -*-
"""044: build 02_DECODER_TYPE_DOMAIN.tsv, 04_INDIRECT_CALL_SCAN.tsv,
05_FUNCTION_POINTER_CANDIDATES.tsv, 06_BLOCKER_REASSESSMENT.tsv. READ-ONLY."""
import _common as c, os, struct, json

T = c.ROOT

def wr(name, lines):
    c.w(os.path.join(T, name), "\n".join(lines) + "\n")

# ---------------- 02 DECODER TYPE DOMAIN ----------------
hdr = ["decoder","func_entry_rva","probe_site_rva","instruction_bytes","instruction",
       "field","access_width_bits","condition","target_rva","reachable_type_values",
       "branch_semantics","unit","target_buffer","evidence_class","image_sha256_prefix"]
IMG = "17cef6e0"
rows = [
 # D1 entry / guards
 ["D1","0087c110","0087c15a","3beb","cmp ebp,ebx","arg0","32","== 0","0087d55a","n/a","null-context guard -> 0x82010468 error","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087c162","395d10","cmp dword[ebp+0x10],ebx","arg0+0x10","32","== 0","0087d55a","n/a","field-validity guard","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087c18c","0f8699130000","jbe 0x87d52b","arg1+4","32","<= 0","0087d52b","n/a","input buffer length==0 guard","byte","arg1 {data,len}","CONFIRMED",IMG],
 # D1 type-field reads
 ["D1","0087c110","0087c767","837b0801","cmp dword[ebx+8],1","descriptor+8","32","<=1 vs >1","0087c77b/0087c774","{0,1} vs {>1}","pointer-base selection","-","source ptr","CONFIRMED",IMG],
 ["D1","0087c110","0087c794","8b4308","mov eax,dword[ebx+8]","descriptor+8","32","(load)","-","(all)","type/kind value load","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087c797","83f801","cmp eax,1","descriptor+8","32","<=1","0087ceb1","{0,1}","type 0/1 -> dedicated handling","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087c7a0","83e815","sub eax,0x15","descriptor+8","32","==0 after sub -> 21","0087cbc8","{21}","type 21 -> string-from-netbuffer path","byte","char*","CONFIRMED",IMG],
 ["D1","0087c110","0087c7a9","48","dec eax","descriptor+8","32","==0 after dec -> 22","0087c994","{22}","type 22 -> wstring-from-netbuffer path","word","wchar*","CONFIRMED",IMG],
 ["D1","0087c110","0087c7b0","8b4b18","mov ecx,dword[ebx+0x18]","descriptor+0x18","32","(default)","0087c7b0","{2..20, 23..2^32-1}","default: element array, size-class from [ebx+0x1c]","byte","typed array","CONFIRMED",IMG],
 # D1 size class cascade
 ["D1","0087c110","0087c813","4b","dec ebx","descriptor+0x1c","32","==0 -> size 1","0087c954","{1}","1-byte element copy loop","byte","dst","CONFIRMED",IMG],
 ["D1","0087c110","0087c81a","4b","dec ebx","descriptor+0x1c","32","==0 -> size 2","0087c930","{2}","2-byte big-endian swap copy","16-bit","dst","CONFIRMED",IMG],
 ["D1","0087c110","0087c821","83eb02","sub ebx,2","descriptor+0x1c","32","==0 -> size 4","0087c8eb","{4}","4-byte endian swap copy","32-bit","dst","CONFIRMED",IMG],
 ["D1","0087c110","0087c82a","89442420","mov [esp+0x20],eax","count","32","default -> size 8","0087c830","{8}","8-byte shld/shrd element copy loop","64-bit","dst","CONFIRMED",IMG],
 ["D1","0087c110","0087c954","83f840","cmp eax,0x40","count","32",">0x40 -> memcpy","0087c978","{>64}","bulk copy via 0x8427f0(memcpy)","byte","dst","CONFIRMED",IMG],
 # D1 bounds checks
 ["D1","0087c110","0087c7be","3b542434","cmp edx,dword[esp+0x34]","src_end",'32',"above -> overflow","0087c7c4","n/a","src bound check (imul size*count)","byte","src","CONFIRMED",IMG],
 ["D1","0087c110","0087c7fb","3b4c2430","cmp ecx,dword[esp+0x30]","dst_end","32","above -> overflow","0087c801","n/a","dst bound -> net-buffer NOT enough (0xd9efb8)","byte","dst","CONFIRMED",IMG],
 # D1 returns
 ["D1","0087c110","0087d524","b801040182","mov eax,0x82010401","retval","32","status","0087d577","n/a","return status 0x82010401","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087d553","b868040182","mov eax,0x82010468","retval","32","status","0087d57a","n/a","return status 0x82010468","-","-","CONFIRMED",IMG],
 ["D1","0087c110","0087d524","b801040182","mov eax,0x82010401","retval","32","status","-","n/a","status family 0x820104xx","-","-","CONFIRMED",IMG],
 # D2
 ["D2","0087d5a0","0087d5f4","837d1000","cmp dword[ebp+0x10],0","arg1+0x10","32","==0","0087ed21","n/a","context validity guard","-","-","CONFIRMED",IMG],
 ["D2","0087d5a0","0087d60f","8b33","mov esi,dword[ebx]","descriptor B","32","(load)","-","(all)","buffer B data pointer","byte","buffer B","CONFIRMED",IMG],
 ["D2","0087d5a0","0087d619","8b4304","mov eax,dword[ebx+4]","descriptor B+4","32","(load)","-","n/a","buffer B length","byte","buffer B","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dca3","0fb74544","movzx eax,word[ebp+0x44]","descriptor+0x44","16","test al,4","0087dcb7","flag","flag bit2 selects indexed base","-","-","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dcb7","837d0801","cmp dword[ebp+8],1","descriptor+8","32","<=1 vs >1","0087dcca","{0,1} vs {>1}","pointer-base selection (same shape as D1)","-","source ptr","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dd3e","83f815","cmp eax,0x15","descriptor+8","32","==0x15 (21)","0087dd4d","{21}","group A member (21)","byte","-","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dd43","83f816","cmp eax,0x16","descriptor+8","32","==0x16 (22)","0087dd4d","{22}","group B member (22)","byte","-","CONFIRMED",IMG],
 ["D2","0087d5a0","0087de58","83f801","cmp eax,1","descriptor+8","32","<=1","0087e65f","{0,1}","type 0/1 -> dedicated handling","-","-","CONFIRMED",IMG],
 ["D2","0087d5a0","0087de61","83e815","sub eax,0x15","descriptor+8","32","==0 -> 21","0087e30f","{21}","type 21 -> string path","byte","char*","CONFIRMED",IMG],
 ["D2","0087d5a0","0087de6a","48","dec eax","descriptor+8","32","==0 -> 22","0087e07a","{22}","type 22 -> wstring path","word","wchar*","CONFIRMED",IMG],
 ["D2","0087d5a0","0087de71","8b4d18","mov ecx,dword[ebp+0x18]","descriptor+0x18","32","(default)","0087de71","{2..20, 23..2^32-1}","default: element array","byte","typed array","CONFIRMED",IMG],
 ["D2","0087d5a0","0087deed","49","dec ecx","size-class (=[ebp+0x1c])","32","{1,2,4,8} cascade","0087e03f/0087e017/0087dfce","{1,2,4,8,other}","size-class dispatch same shape as D1","byte","dst","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dea0","83f840","cmp eax,0x40","count","32",">0x40","0087e05e","{>64}","bulk copy via 0x8427f0","byte","dst","CONFIRMED(shared shape)",IMG],
 ["D2","0087d5a0","0087de83","762a","jbe 0x87deaf","src_end","32","above -> overflow","0087debf","n/a","src bound check","byte","src","CONFIRMED",IMG],
 ["D2","0087d5a0","0087dee0","c744243402040182","mov [esp+0x34],0x82010402","retval","32","status","0087e5da","n/a","return status 0x82010402","-","-","CONFIRMED",IMG],
 # shared helpers
 ["CORE-A","0087ed70","0087ed70","833de8c7960100","cmp dword[0x196c7e8],0","global 0x196c7e8","32","==0 -> static buffer","0087ed91","n/a","if uninit use static 0x196c7f0","-","1KB scratch (0x400)",42,IMG],
 ["CORE-A","0087ed70","0087ed85","ff153083ca00","call dword[0xca8330]","IAT slot 0xca8330","32","-","-","n/a","pool acquire (slot OUT-OF-IMAGE)","-","scratch","CONFIRMED(call) / BLOCKED(slot value)",IMG],
 ["CORE-A","0087ed70","0087ed91","80beff03000000","cmp byte[esi+0x3ff],0","scratch+0x3ff","8","!=0 -> clear","0087ed9c","n/a","clear last byte of 0x400 buffer","byte","scratch","CONFIRMED",IMG],
 ["CORE-B","0087edb0","0087edb0","8b542408","mov edx,[esp+8]","arg1 (max count)","32","==0 -> ret 0","0087edce","n/a","bounded length count","-","-","CONFIRMED",IMG],
 ["CORE-B","0087edb0","0087edc0","66833900","cmp word[ecx],0","arg0[i]","16","==0 -> stop","0087edce","n/a","UTF-16 wcslen with bound","16-bit","input","CONFIRMED",IMG],
 ["CORE-MID","0087ed60","0087ed60","8b442404","mov eax,[esp+4]","arg0","32","-","0087ed69","n/a","setter: global 0x196c780 = arg0 (MISSED BY 043)","-","-",42,IMG],
]
wr("02_DECODER_TYPE_DOMAIN.tsv", ["\t".join(hdr)] + ["\t".join(str(x) for x in r) for r in rows])

# ---------------- 04 INDIRECT CALL SCAN ----------------
src = open(os.path.join(c.EV, "c01_indirect_union.tsv"), encoding="utf-8").read().splitlines()
out = ["site_rva\tsite_va\tmnemonic\toperand\tsite_form\tbytes\tsource\tcoverage\timage_sha256_prefix"]
for l in src[1:]:
    out.append(l + "\tpresent .tp3#1 (file_off==RVA)\t17cef6e0")
wr("04_INDIRECT_CALL_SCAN.tsv", out)

# ---------------- 05 FUNCTION POINTER CANDIDATES ----------------
r = json.load(open(os.path.join(c.EV, "c01_indirect_scan.json"), encoding="utf-8"))
f = json.load(open(os.path.join(c.EV, "c02_focus.json"), encoding="utf-8"))
h5 = ["candidate_id","kind","site_rva","site_va","table_base_rva","elem_width_bytes","elem_count",
      "min_target_rva","max_target_rva","targets_all_in_text","classification","reason","image_sha256_prefix"]
r5 = []
# netbuffer-region indexed forms -> all proven to be in-instruction displacements (false positives)
for i, b in enumerate(f["nb_jumptables"]):
    d0 = c.idword(b)
    r5.append(["NBT-%02d" % (i+1), "indexed_jmp_operand", "0087%04x" % 0, "n/a", "%08x" % b, 4, "1 (probed)",
               "n/a", "n/a", "NO", "FALSE_POSITIVE_IN_INSTRUCTION_DISP",
               "indexing displacement inside the instruction itself; dword at base decodes to code (0x%08x)" % (d0 or 0), "17cef6e0"])
# contiguous runs
for i, run in enumerate(r["contiguous_runs"][:40]):
    r5.append(["RUN-%03d" % (i+1), "contiguous_in_text_dwords", "n/a", "n/a", run["off"], 4, run["n"],
               run["min"], run["max"], "YES", "DATA_TABLE_OR_JUMPTABLE",
               ">=8 consecutive 4-byte values inside .text; not referenced by any indexed [reg*4+disp] operating on it",
               "17cef6e0"])
# focus dword hits
for name, hits in r["focus_dword_hits"].items():
    r5.append(["FOCUS-" + name, "absolute_dword_ref_to_audited_entry", "n/a", "n/a", "n/a", 4, len(hits),
               "n/a", "n/a", "n/a", "NONE_FOUND" if not hits else "FOUND",
               "search for the exact VA of %s across ALL present bytes" % name, "17cef6e0"])
wr("05_FUNCTION_POINTER_CANDIDATES.tsv", ["\t".join(h5)] + ["\t".join(str(x) for x in x) for x in r5])

# ---------------- 06 BLOCKER REASSESSMENT ----------------
h6 = ["edge_id","original_blocker_043","044_new_evidence","new_direct_evidence_found",
      "missing_range_narrowed","alternative_verifiable_path","still_needs_extra_evidence",
      "impact_on_class_A_server_admission","044_status"]
IMG = "17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045"
r6 = [
 ["BE-01","socket/recv -> read primitive 0x87BE00; 043: IAT slot 0xCA84E8 value unknown, image not covering .tp3 #3/#5",
  "0x87BE00 = ReadFile-like primitive calling [0xCA84E8] then fallback [0xCA84E4], error via [0xCA853C], timeouts compared to 0x2714/0x2733; part of the async file/overlapped family, invoked by TQOS dispatcher 0x85E6F0 via thunk 0x87BA50. IAT slots are beyond EOF (file 0xA65000 < RVA 0xCA84E8).",
  "NO (slot value not resolvable)","NO",
  "Only at API-name level: the overload-guarded two-stage call shape is shared between ReadFile/RecvFile and WSARecv; 044 finds no byte in the present image that distinguishes them, and the string evidence in this image belongs to libcurl ('recv','select'), i.e. a different module.",
  "YES (IAT slot value, or PE import directory with sizes, or an API-name-bearing capture)","A - still blocks socket/recv attribution","UNKNOWN/BLOCKED"],
 ["BE-02","read primitive 0x87BE00 -> decoder 0x87C110; 043: no direct edge; full .text E8/imm32 scan = 0 hits",
  "043's E8 count independently reproduced: 0x87BE00 has 0 E8 callers in all present text; it is only reached through thunk 0x87BA50 (E9). Full-image indexed-indirect scan finds 2 such sites in the decoder region (0x87ED85 IAT call, 0x87EDD0 IAT jmp) and none touching the decoders.",
  "NO","NO","None in the present image; 0x87BE00/0x87BA50 remain reachable only via 0x85D5A0 and 0x85E6F0.",
  "YES (complete image / IAT region)","B","UNKNOWN (unchanged)"],
 ["BE-03","business layer -> decoders 0x87C110/0x87D5A0; 043: only TQOS callers visible",
  "Re-confirmed E8 callers: 0x87C110 <- {0x85D49D}; 0x87D5A0 <- {0x85D3DB,0x85D418,0x85D9B5,0x85D9F7}; plus 0x87EDB0 <- {0x87C9B7} only. Zero absolute (dword) references to either decoder entry anywhere in present bytes, and zero indexed/near-fed indirect calls targeting them.",
  "NO (no new caller)","PARTIAL (all negative evidence re-verified exhaustively over the present image)",
  "None static; indirect/register dispatch could still reach them from un-recovered regions, which cannot be disproved.",
  "YES","A - business path unresolved","UNKNOWN (unchanged; negative evidence strengthened)"],
 ["BE-04","read primitive -> decoder 0x87D5A0; 043: no direct edge",
  "Same as BE-02 for 0x87D5A0: 0 E8 callers from the primitive; callers remain the TQOS cluster only.",
  "NO","NO","None","YES","B","UNKNOWN (unchanged)"],
 ["BE-05","application message type table -> dispatcher branch; 043: in-match type table not located",
  "TQOS dispatcher 0x85E6F0 branch structure recovered: reads [ebx] via thunk 0x87BA50 into a 0x4ebc stack buffer, then 0x85D3A0 decodes, then switches on word[esp+6]-2 (values 0 / 2 after sub): 2 -> 0x85E7B0 (0x85E4F0 handler), else 0 -> 0x85E769 (0x85E5C0 handler). This is the TQOS envelope type, NOT the in-match opcode table.",
  "NO (business opcode table still absent)","NO","None","YES","A","UNKNOWN (unchanged)"],
 ["BE-06",".tvm0 protocol logic; 043: protected",
  "Not rescanned (out of 044 scope, unchanged). 044 confirms the analysed image region is .tp3 #1 only, and 0x0E5D3000 (old .tvm0) in this image is *.tp3*-named non-linear bytes.",
  "NO","NO","None","YES (separate authorisation)","C","BLOCKED (unchanged)"],
 ["BE-07","producer (buffer allocation) -> net_start/net_end; 043: allocation point not covered",
  "0x87C110 and 0x87D5A0 both accept explicit {data,len} pairs (arg1 {data,len}; D2 also arg2/arg3 buffer pairs) and base all bounds arithmetic on them ([esp+0x30],[esp+0x34], [ebx+4],[edi+4]); no allocation of the input buffer occurs inside them. The scratch buffer they DO obtain is only the 0x400 diagnostic buffer from 0x87ED70.",
  "NO (producer still outside image)","PARTIAL (proved the decoders are pure consumers, not producers)",
  "None","YES","B","UNKNOWN (narrowed)"],
]
wr("06_BLOCKER_REASSESSMENT.tsv", ["\t".join(h6)] + ["\t".join(str(x) for x in x) for x in r6])
print("wrote 02 / 04 / 05 / 06")