# -*- coding: utf-8 -*-
"""Offline arithmetic audit for CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
TASK=ROOT/'CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001'
G3=ROOT/'CODOL-KEYFLOW-G3-FRAME-VALIDATION-001'
CB=ROOT/'CODOL-KEYFLOW-COUNTER-BOUNDARY-001'
PACKED=Path(r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe')
RECOVERED=Path(r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin')

INPUTS=[
 ('packed-client',PACKED,'353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1'),
 ('recovered-image',RECOVERED,'24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4'),
 ('g3-harness',G3/'_tools/g3_frame_harness.py','ea3a997a480dd99cce0ab34241aa78402e7a370f5e6ff8bb9ac4f9c244023010'),
 ('g3-results',G3/'CODOL_G3_FRAME_TEST_RESULTS_001.csv','6a9ea44e67adca4c07848f6a7c757203a750dd2e38b31b864470e3866c872ea9'),
 ('g3-log',G3/'_data/g3_execution_log.json','f26ffdb1108de434ac8a9483a1edf475814e0ec1eede783286544f1cacd3782c'),
 ('g3-manifest',G3/'SHA256SUMS_G3_FRAME_VALIDATION_001.txt','c09b3b6194adb0a7615532022e15863c17f269c99f2e34455f852f5ea893dc87'),
 ('counter-audit',CB/'CODOL_COUNTER_WRAP_STATIC_AUDIT_001.md','4a934db18b613c7fadc8dcde0f478d6afb0d2248967db371afd096f211fa946c'),
 ('counter-evidence',CB/'_data/counter_boundary_static_evidence.json','55b775bf7a2640c5c276049b049582e7634c526f256e5e1b62595a6047d8992c'),
 ('counter-tc27',CB/'CODOL_G3_TC27_REASSESSMENT_001.md','63cec359eacf50677bd88d4932a86d857a1878f65747712749f205617dbf924c'),
 ('counter-residual',CB/'CODOL_G3_RESIDUAL_RISK_UPDATE_001.md','4f15c3ceb702b9522e8f17b827fe91b6fc1f183815dac2d006df1f48e584dfd1'),
]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def input_check():
    out=[]
    for name,path,expected in INPUTS:
        actual=sha(path) if Path(path).exists() else 'MISSING'
        out.append({'name':name,'path':str(path),'expected_sha256':expected,'actual_sha256':actual,'ok':actual==expected})
    return out

def hx(n): return f'0x{n:X}'

def frame_from_outer(ln):
    ct=ln-30
    total=ln+4
    aligned=(ct>0 and ct%16==0)
    return {'outer_len':ln,'ciphertext_len':ct,'total_len':total,'iv_len':16,'tag_len':8,'ct_aligned':aligned}

def payload_0x86(ct):
    if not (ct>0 and ct%16==0): return None
    return {'min':ct-20,'max':ct-5,'padding_zero_added_max':(ct-5-(ct-20))%16}

def local_parser_model(ln, complete=True):
    if ln==0: return {'accepted':True,'reason':'keepalive'}
    if ln>0x100000: return {'accepted':False,'reason':'ln > 0x100000; parser retains remainder'}
    if not complete: return {'accepted':False,'reason':'incomplete buffer; parser waits'}
    return {'accepted':True,'reason':'ln <= 0x100000; complete frame sliced'}

def client_ct_static(ct):
    nonzero=ct>0
    aligned=(ct%16==0)
    below_limit=(ct<0xFFFFFF)
    return {'ct_nonzero':nonzero,'ct_aligned':aligned,'ct_below_0xFFFFFF':below_limit,'length_valid':nonzero and aligned and below_limit}

def classification(local_ok, client_ok, ct_aligned):
    if local_ok and client_ok: return 'LOCAL-PARSER-ACCEPT / CLIENT-STATIC-LENGTH-OK / E2E-UNKNOWN'
    if local_ok and not client_ok: return 'LOCAL-PARSER-ACCEPT / CLIENT-STATIC-LENGTH-INVALID / E2E-UNKNOWN'
    if (not local_ok) and client_ok: return 'LOCAL-PARSER-REJECT / CLIENT-STATIC-LENGTH-OK / E2E-UNKNOWN'
    return 'LOCAL-PARSER-REJECT / CLIENT-STATIC-LENGTH-INVALID / E2E-UNKNOWN'

def main():
    checks=input_check()
    if not all(x['ok'] for x in checks): raise SystemExit('input hash mismatch')
    vals=[0xFFFFE,0xFFFFF,0x100000,0x100001,0x10000E,0xFFFFFF,0x100000E,0x100000F,0x1000010,0x100001E]
    rows=[]
    for idx,ln in enumerate(vals,1):
        f=frame_from_outer(ln); lp=local_parser_model(ln,complete=True); cl=client_ct_static(f['ciphertext_len']); p=payload_0x86(f['ciphertext_len'])
        payload_text='N/A' if p is None else f"{hx(p['min'])}..{hx(p['max'])}"
        rows.append({
            'case_id':f'LC-{idx:02d}',
            'outer_len_hex':hx(ln),
            'outer_len_dec':ln,
            'ciphertext_len_hex':hx(f['ciphertext_len']),
            'ciphertext_len_dec':f['ciphertext_len'],
            'total_len_hex':hx(f['total_len']),
            'iv_bytes':16,
            'tag_bytes':8,
            'ciphertext_aligned':str(f['ct_aligned']).lower(),
            'max_payload_0x86_range':payload_text,
            'local_parser_numeric_accept':str(lp['accepted']).lower(),
            'local_parser_reason':lp['reason'],
            'formula_evidence':'KF-17; outbound 0xAAAA84-0xAAAA9D; ct_len=ceil((5+payload_len)/16)*16',
            'local_parser_evidence':'REF_LOBBY_KIT/codol_crypto.py parse_frames: ln > 0x100000',
            'client_static_evidence':'0xAAAF7B test cl,0xF; 0xAAAF80 cmp ecx,0xFFFFFF; 0xAAAF86 jge',
            'client_ct_nonzero':str(cl['ct_nonzero']).lower(),
            'client_ct_aligned':str(cl['ct_aligned']).lower(),
            'client_ct_below_0xFFFFFF':str(cl['ct_below_0xFFFFFF']).lower(),
            'client_static_length_valid':str(cl['length_valid']).lower(),
            'compatibility_classification':classification(lp['accepted'],cl['length_valid'],f['ct_aligned']),
            'evidence_level':'BINARY-STATIC + PROJECT-REFERENCE + ARITHMETIC-MODEL',
            'end_to_end_status':'NOT-OBSERVED',
            'notes':'' if f['ct_aligned'] else 'Outer length is parser-numeric only; decrypted ciphertext length is not 16B aligned.'
        })
    with (TASK/'CODOL_LENGTH_BOUNDARY_CASES_001.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    local_max_aligned_ct=((0x100000-30)//16)*16
    local_max_aligned_outer=local_max_aligned_ct+30
    first_gap_aligned_outer=0xFFFF0+30
    client_max_aligned_ct=((0xFFFFFF-1)//16)*16
    client_equiv_outer=client_max_aligned_ct+30
    evidence={
      'task':'CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001',
      'scope':{'offline_static':True,'large_allocation':False,'game_started':False,'server_started':False,'network_used':False,'binary_modified':False},
      'inputs':checks,
      'formulas':{
        'plaintext_pad_0x86':'ct_len = ceil((5 + payload_len)/16)*16',
        'outer_len':'outer_len = ct_len + 30',
        'total_len':'total_len = outer_len + 4 = ct_len + 34',
        'layout':'len_u32 | AB | 85 | seq_u32 | IV16 | ciphertext | tag8',
      },
      'local_parser':{'implementation':'REF_LOBBY_KIT/codol_crypto.py parse_frames','condition':'reject/retain when outer_len > 0x100000','max_numeric_accept':0x100000,'max_aligned_outer_under_cap':local_max_aligned_outer,'first_aligned_outer_above_cap':first_gap_aligned_outer},
      'client_static':{'ct_limit_condition':'ct_len < 0xFFFFFF','ct_limit_inclusive_max_multiple_of_16':client_max_aligned_ct,'max_equivalent_outer_len':client_equiv_outer,'max_equivalent_total_len':client_equiv_outer+4},
      'cases':rows,
      'tc27':{'source':str(CB/'CODOL_G3_TC27_REASSESSMENT_001.md'),'status':'CONFIRMED-STATIC','runtime_status':'NOT-OBSERVED','g3_original_status':'BLOCKED-INSUFFICIENT-SPEC'}
    }
    (TASK/'_data').mkdir(parents=True,exist_ok=True)
    (TASK/'_data'/'length_compatibility_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print('inputs_ok=',all(x['ok'] for x in checks))
    print('local_max_aligned_outer=',hex(local_max_aligned_outer))
    print('first_gap_aligned_outer=',hex(first_gap_aligned_outer))
    print('client_max_aligned_ct=',hex(client_max_aligned_ct))
    print('client_equiv_outer=',hex(client_equiv_outer))
    print('cases=',TASK/'CODOL_LENGTH_BOUNDARY_CASES_001.csv')
    print('evidence=',TASK/'_data'/'length_compatibility_evidence.json')

if __name__=='__main__': main()