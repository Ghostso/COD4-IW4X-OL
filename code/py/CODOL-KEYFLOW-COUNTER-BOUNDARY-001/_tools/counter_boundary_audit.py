# -*- coding: utf-8 -*-
"""Static-only audit for CODOL-KEYFLOW-COUNTER-BOUNDARY-001."""
from __future__ import annotations
import csv, hashlib, json, struct, sys
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
TASK=ROOT/'CODOL-KEYFLOW-COUNTER-BOUNDARY-001'
PACKED=Path(r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe')
RECOVERED=Path(r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin')
G3=ROOT/'CODOL-KEYFLOW-G3-FRAME-VALIDATION-001'

INPUTS=[
 ('packed-client',PACKED,'353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1'),
 ('recovered-image',RECOVERED,'24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4'),
 ('g3-results',G3/'CODOL_G3_FRAME_TEST_RESULTS_001.csv','6a9ea44e67adca4c07848f6a7c757203a750dd2e38b31b864470e3866c872ea9'),
 ('g3-diff',G3/'CODOL_G3_FRAME_DIFF_REPORT_001.md','d56fab6efc01691c61437e8d09c73d12a933e8a36b8a7fde07bb7b12829165d1'),
 ('g3-boundary',G3/'CODOL_G3_BOUNDARY_BEHAVIOR_001.md','6b18c6e02050df1a95abfd98dfe3a25e679f3d48b7686c0b0b400e59a78f010d'),
 ('g3-decision',G3/'CODOL_G3_DECISION_001.md','76d924fcf78f80186babc433c2bb720c29d9f2f557acfafbd8f3c1316b0a799a'),
 ('g3-manifest',G3/'SHA256SUMS_G3_FRAME_VALIDATION_001.txt','c09b3b6194adb0a7615532022e15863c17f269c99f2e34455f852f5ea893dc87'),
 ('g3-harness',G3/'_tools/g3_frame_harness.py','ea3a997a480dd99cce0ab34241aa78402e7a370f5e6ff8bb9ac4f9c244023010'),
 ('g3-log',G3/'_data/g3_execution_log.json','f26ffdb1108de434ac8a9483a1edf475814e0ec1eede783286544f1cacd3782c'),
 ('evidence-trace',ROOT/'CODOL-DEMONWARE-RUNTIME-VALIDATION-001/CODOL_KEYFLOW_EVIDENCE_TRACE_001.csv','dd541bbb98f73414586f96e5a7b2696bd707056ccc3bc1a8f4b3acd3e6721e2b'),
 ('source-crosswalk',ROOT/'CODOL-KEYFLOW-SPEC-PROVENANCE-001/CODOL_KEYFLOW_SPEC_CROSSWALK_001.csv','f4297fe60d989dd451b7676745def5b170a39b4c12f0e541eea5025d7b2f59dd'),
 ('recv-evidence',ROOT/'CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/_data/recv_parser_core.txt','6522d17acd911287bd3e64088952fb436106c4aef8f475550972bd50c42944b7'),
 ('frame-evidence',ROOT/'CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/_data/frame_85_region.txt','4fe00d2d4224b4fa88c8aecc8b94d710d54fb5c5f753f0ca15e19bdba797375b'),
 ('ref-parser',ROOT/'REF_LOBBY_KIT/codol_crypto.py','e836c63af75dd82ef6f3b07ef63fae48b044b3b5047336127093c92b07644607'),
]

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def load_text(path):
    return Path(path).read_text(encoding='utf-8-sig')

def verify_inputs():
    out=[]
    for name,path,expected in INPUTS:
        actual=sha256(path) if Path(path).exists() else 'MISSING'
        out.append({'name':name,'path':str(path),'expected_sha256':expected,'actual_sha256':actual,'ok':actual==expected})
    return out

def decoder_for(image_path,start,end):
    pe=pefile.PE(str(image_path)); ib=pe.OPTIONAL_HEADER.ImageBase
    off=pe.get_offset_from_rva(start-ib); data=Path(image_path).read_bytes()[off:off+(end-start)]
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    return list(md.disasm(data,start)),ib

def inst_by_addr(insns):
    return {i.address:i for i in insns}

def ins_record(i):
    return {'address':f'0x{i.address:08X}','bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'op_str':i.op_str}

def count_refs(insns,disp):
    out=[]
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    for i in insns:
        # Re-decode a one-instruction view with detail so operands are available.
        for x in md.disasm(i.bytes,i.address):
            for op in x.operands:
                try:
                    if op.type==3 and op.mem.disp==disp:  # X86_OP_MEM
                        out.append(ins_record(i)); break
                except Exception:
                    pass
            break
    return out

def seq_step(expected,sequence):
    old=expected; new=(old+1)&0xFFFFFFFF; accepted=(sequence==old)
    return {'expected_before':old,'incoming':sequence,'expected_after':new,'accepted':accepted,'equality_operand':old}

def q(x): return x & 0xFFFFFFFF

def main():
    inputs=verify_inputs()
    if not all(x['ok'] for x in inputs): raise SystemExit('input hash mismatch')

    recv_start,recv_end=0xAAAE70,0xAAB25A
    send_start,send_end=0xAAAA10,0xAAAE70
    auth_start,auth_end=0xAAB260,0xAAB310
    recv,ib=decoder_for(RECOVERED,recv_start,recv_end)
    send,_=decoder_for(RECOVERED,send_start,send_end)
    auth,_=decoder_for(RECOVERED,auth_start,auth_end)
    ri,si,ai=inst_by_addr(recv),inst_by_addr(send),inst_by_addr(auth)

    key_addrs=[0xAAAB4C,0xAAADA2,0xAAAFA4,0xAAAFAA,0xAAAFAD,0xAAAFB3,0xAAAFB9,0xAAAFFD,0xAAAF7B,0xAAAF80,0xAAAF86,0xAAA770,0xAAA791,0xAAB2D4,0xAAB2DF,0xAAB2E5,0xAAC0EA,0xAAC1D6,0xAAC2F0]
    selected={}
    allins={**ri,**si,**ai}
    for a in key_addrs:
        if a in allins: selected[f'0x{a:08X}']=ins_record(allins[a])
        else:
            # Some dispatcher addresses are outside the three function ranges.
            d,_=decoder_for(RECOVERED,a,a+16)
            selected[f'0x{a:08X}']=ins_record(d[0]) if d else {'missing':True}

    refs={'receive_0x5d0':count_refs(recv,0x5D0),'receive_0x5d4':count_refs(recv,0x5D4),
          'send_0x5d0':count_refs(send,0x5D0),'send_0x5d4':count_refs(send,0x5D4),
          'auth_done_0x5d0':count_refs(auth,0x5D0),'auth_done_0x5d4':count_refs(auth,0x5D4)}

    model={
      'normal':[seq_step(1,1),seq_step(2,2)],
      'duplicate_before_fix':[seq_step(2,1)],
      'gap':[seq_step(2,3)],
      'gap_then_same_if_connection_continued':[seq_step(2,3),seq_step(3,3)],
      'wrap_ffffffff_then_zero':[seq_step(0xFFFFFFFF,0)],
      'send_counter_examples':[{'counter_before':0,'sequence_in_frame':0,'counter_after':1},
                               {'counter_before':0xFFFFFFFF,'sequence_in_frame':0xFFFFFFFF,'counter_after':0}],
    }

    client_ct_limit_exclusive=0xFFFFFF
    client_max_aligned_ct=(client_ct_limit_exclusive-1)//16*16
    client_equiv_len_max=client_max_aligned_ct+30
    local_len_limit_inclusive=0x100000
    gap_low=local_len_limit_inclusive+1
    gap_high=client_equiv_len_max

    csv_rows=[
      ['L-01','length field width','u32 (4-byte dword stores/loads)', 'u32 struct <I','OUTBOUND 0xAAAA9D..0xAAAAA8; A87830 copies 4 bytes; inbound tag arithmetic uses 4-byte field','codol_crypto.py struct.unpack_from("<I")','same width','CONFIRMED-STATIC','no direct impact','x86 little-endian storage is confirmed by captured 01 00 00 00 for seq=1; length examples use 9e 00 00 00.'],
      ['L-02','length field semantic','len = total_frame_bytes - 4', 'ln = bytes following the 4-byte prefix','KF-17; captured 0x9e/158 and 0x3e/62','codol_crypto.py parse_frames uses off+4+ln','same public semantic for complete frames','CONFIRMED-STATIC','no direct impact','Both layers treat the dword as the count of following bytes.'],
      ['L-03','local parser upper bound','not the client static check','reject/retain when ln > 0x100000','REF_LOBBY_KIT parser, line with ln > 0x100000','CONFIRMED / PROJECT-REFERENCE','different layer','MODEL-ONLY','does not invalidate small-vector G3 results','Do not promote this parser cap to a protocol cap.'],
      ['L-04','client ciphertext upper bound','ct_len < 0xFFFFFF; aligned','no equivalent exact check','0xAAAF7B test low nibble; 0xAAAF80 cmp ecx,0xffffff; 0xAAAF86 jge','local parser checks outer ln first','different layer and strictness','CONFIRMED-STATIC','large-frame compatibility gap','ecx is computed as tag_address - ciphertext_start, so this is ciphertext length, not outer length.'],
      ['L-05','client-equivalent outer-len maximum','max aligned ct=0xFFFFF0; max len=0x100000E; max total=0x1000012','local parser max accepted ln=0x100000','arithmetic from L-04 plus len=ct+30 / total=ct+34','REF_LOBBY_KIT parser boundary','client threshold is about 16 MiB-equivalent; local is 1 MiB','CONFIRMED-STATIC','large-frame gap','Use the converted value, never compare 0x100000 directly with 0xFFFFFF.'],
      ['L-06','gap interval','client-equivalent ln 0x100001..0x100000E may pass the located ct check','local parser rejects/retains >0x100000','L-04/L-05','L-03','real implementation difference','CONFIRMED-STATIC','separate residual compatibility gap','No full valid large frame was executed; this is static threshold and layer evidence.'],
      ['L-07','check order','ct alignment/limit before seq check, HMAC and decrypt','outer length check before decode; decode later checks exact length/alignment','0xAAAF73..0xAAAF98 before 0xAAAFA4; HMAC at 0xAAB074','g3 parser then decode','different order and layer','CONFIRMED-STATIC','changes what the local parser can reject first','Do not infer client allocation behavior from this order.'],
      ['L-08','allocation/read constraint','passed buffer and tag-pointer arithmetic observed; no allocation in 0xAAAE70','parser does not allocate; later frame code allocates/copies','0xAAAE70 uses esi/ebx buffer arguments; no malloc call in range','codol_crypto.py parse_frames slices bytes','insufficient evidence for allocation policy','UNRESOLVED','no immediate G3 effect','Large allocation behavior remains unverified.'],
      ['L-09','current matrix coverage','TC-29 distinct tests only 0x100001/0xFFFFFF/0xFFFFFFFF field values','TC-29 does not build a valid large frame','G3 CSV TC-29','G3 CSV TC-29','gap interval not covered by a valid-frame test','CONFIRMED-STATIC','G3 length conclusion remains narrow','Add a future safe static/model test or runtime fixture before changing parser.'],
      ['L-10','impact on existing G3','small fixed vectors unaffected','TC-16..TC-28 and TC-30..TC-32 use small frames','G3 results/log','G3 results/log','no regression to fixed-vector conclusions','CONFIRMED-STATIC','does not by itself revoke G3 core pass','Treat length limit mismatch as an independent compatibility gap.'],
    ]

    evidence={
      'task':'CODOL-KEYFLOW-COUNTER-BOUNDARY-001',
      'scope':{'offline_static':True,'game_started':False,'server_started':False,'network_used':False,'binary_modified':False},
      'inputs':inputs,
      'image_base':f'0x{ib:08X}',
      'functions':{'send':'0x00AAAA10..0x00AAAE60','receive':'0x00AAAE70..0x00AAB25A','auth_done':'0x00AAB260..0x00AAB303','dispatcher':'0x00AAC0C0..0x00AAC3C8','cleanup':'0x00AAA770..0x00AAA7A6'},
      'selected_instructions':selected,
      'counter_reference_scan':refs,
      'sequence_model':model,
      'length_values':{'local_outer_len_max_accepted':q(local_len_limit_inclusive),'client_ct_limit_exclusive':q(client_ct_limit_exclusive),'client_max_aligned_ct':q(client_max_aligned_ct),'client_equivalent_outer_len_max':q(client_equiv_len_max),'client_equivalent_total_max':q(client_equiv_len_max+4),'gap_low':q(gap_low),'gap_high':q(gap_high)},
      'classification':{'tc27':'CONFIRMED-STATIC','length_layer':'CONFIRMED-STATIC','length_practical_impact':'UNRESOLVED','original_g3_sequence_model':'CONFLICTING-EVIDENCE'}
    }
    (TASK/'_data').mkdir(parents=True,exist_ok=True)
    (TASK/'_data'/'counter_boundary_static_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    with (TASK/'CODOL_FRAME_LENGTH_BOUNDARY_AUDIT_001.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['boundary_id','category','frozen_client_value','local_parser_value','client_evidence','local_evidence','comparison','status','impact_on_g3','notes']); w.writerows(csv_rows)
    print('inputs_ok=',all(x['ok'] for x in inputs))
    print('client_equiv_outer_len_max=',hex(client_equiv_len_max))
    print('counter_refs=',{k:len(v) for k,v in refs.items()})
    print('evidence=',TASK/'_data'/'counter_boundary_static_evidence.json')
    print('csv=',TASK/'CODOL_FRAME_LENGTH_BOUNDARY_AUDIT_001.csv')

if __name__=='__main__': main()