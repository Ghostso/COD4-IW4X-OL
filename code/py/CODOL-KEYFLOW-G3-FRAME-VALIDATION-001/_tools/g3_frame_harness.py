# -*- coding: utf-8 -*-
"""CODOL G3 offline frame-validation harness. No game/server/network activity."""
from __future__ import annotations
import csv, datetime as dt, hashlib, hmac, json, re, struct, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from Crypto.Cipher import AES as PD_AES

ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
TASK=ROOT/'CODOL-KEYFLOW-G3-FRAME-VALIDATION-001'
G2=ROOT/'CODOL-KEYFLOW-INDEPENDENT-VERIFY-001'
sys.path.insert(0,str(G2/'_tools'))
import indep_primitives as OWN
sys.path.insert(0,str(ROOT/'REF_LOBBY_KIT'))
import codol_crypto as CC
DEMONWARE_TESTS=ROOT/'_e1_regression'/'ol-mod-olfinal'/'tests'/'backend'/'DemonwareTests.cpp'
MAX_REFERENCE_FRAME=0x100000
MAX_CLIENT_FRAME_EXCLUSIVE=0xFFFFFF
MARK1,MARK2,MSG_TASK=0xAB,0x85,0x86

BASELINE_EXPECTED={
r'D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe':'353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1',
r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin':'24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4',
r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-DEMONWARE-RUNTIME-VALIDATION-001\CODOL_KEYFLOW_TEST_MATRIX_001.csv':'1fb1528e58ed1e3de23ed68d3668556b9e8c6869924ea7020421dc6995cde630',
r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\indep_primitives.py':'02ab17417c8090ab820c414e0cf9f44ba174798383166dc7d1e2e6ddde320dfa',
r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\indep_protocol.py':'2467efa6ab93edfbf6f0c7ae200c84599c49cacf492bea892d8f3d94b830dd35',
r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_tools\run_kat.py':'43a0fb06e99d6c9e376bd8b0a90ffce3fc7e8d5d255f24c3050ed2d16eb83ea1',
r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-KEYFLOW-INDEPENDENT-VERIFY-001\_data\kat_execution_log.json':'f07fe62fd5e977d3dbd1c8a8b75feb793f0074aaf269e84e71e45db95ca739c5',
r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\tests\backend\DemonwareTests.cpp':'230853f08f049ed7532f3e9cf180fd3e4490b25f891b101b14a0003c524e9e2f',
r'D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\src\backend\Demonware\LobbyProtocol.cpp':'8ace124d7f8e2edf230d2c6618cd447c3eddf37fc5c4bd9fd6b89a2a05485dc9',
r'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\codol_crypto.py':'e836c63af75dd82ef6f3b07ef63fae48b044b3b5047336127093c92b07644607'}
MANIFESTS=[
(ROOT/'CODOL-KEYFLOW-INDEPENDENT-VERIFY-001'/'SHA256SUMS_KEYFLOW_INDEPENDENT_001.txt',11),
(ROOT/'CODOL-KEYFLOW-SPEC-PROVENANCE-001'/'SHA256SUMS_SPEC_PROVENANCE_001.txt',6),
(ROOT/'CODOL-DEMONWARE-RUNTIME-VALIDATION-001'/'SHA256SUMS_RUNTIME_VALIDATION_001.txt',5)]

class FrameError(Exception):
    def __init__(self,stage,message): super().__init__(message); self.stage=stage

@dataclass(frozen=True)
class DecodedFrame:
    total:int; sequence:int; message_type:int; iv:bytes; ciphertext:bytes; plaintext:bytes; declared:int; payload:bytes

def sha256_path(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def jsonable(x):
    if isinstance(x,bytes): return {'bytes_hex':x.hex()}
    if isinstance(x,bytearray): return {'bytes_hex':bytes(x).hex()}
    if isinstance(x,Path): return str(x)
    if isinstance(x,dict): return {str(k):jsonable(v) for k,v in sorted(x.items())}
    if isinstance(x,(list,tuple)): return [jsonable(v) for v in x]
    return x

def canonical_input_hash(x):
    return hashlib.sha256(json.dumps(jsonable(x),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def first_difference(a,b):
    for i,(x,y) in enumerate(zip(a,b)):
        if x!=y: return str(i)
    return '' if len(a)==len(b) else str(min(len(a),len(b)))

def h8_own(k,d): return OWN.hmac_sha1(k,d)[:8]
def h8_std(k,d): return hmac.new(k,d,hashlib.sha1).digest()[:8]
def ae_own(k,iv,d): return OWN.aes128_cbc_encrypt(k,iv,d)
def ad_own(k,iv,d): return OWN.aes128_cbc_decrypt(k,iv,d)
def ae_std(k,iv,d): return PD_AES.new(k,PD_AES.MODE_CBC,iv).encrypt(d)
def ad_std(k,iv,d): return PD_AES.new(k,PD_AES.MODE_CBC,iv).decrypt(d)

def encode_with(payload,aes_key,hmac_key,seq,iv,mt,hfun,aenc):
    n=(5+len(payload)+15)//16*16
    pt=bytearray(n); pt[4]=mt&255; pt[5:5+len(payload)]=payload
    declared=len(payload) if mt==MSG_TASK else n-4
    struct.pack_into('<I',pt,0,declared)
    ct=aenc(aes_key,iv,bytes(pt))
    body=struct.pack('<I',30+len(ct))+bytes([MARK1,MARK2])+struct.pack('<I',seq)+iv+ct
    return body+hfun(hmac_key,body)[:8]

def enc_actual(p,h,s,seq,iv,mt=MSG_TASK): return encode_with(p,h,s,seq,iv,mt,h8_own,ae_own)
def enc_oracle(p,h,s,seq,iv,mt=MSG_TASK): return encode_with(p,h,s,seq,iv,mt,h8_std,ae_std)

def decode_with(frame,aes_key,hmac_key,hfun,adec):
    if len(frame)<50: raise FrameError('min-total-50','shorter than local minimum')
    total=struct.unpack_from('<I',frame,0)[0]
    if total+4!=len(frame): raise FrameError('length','u32 length mismatch')
    if frame[4:6]!=bytes([MARK1,MARK2]): raise FrameError('marker','fixed marker mismatch')
    if not hmac.compare_digest(hfun(hmac_key,frame[:-8]),frame[-8:]): raise FrameError('hmac','HMAC mismatch')
    ct=frame[26:-8]
    if not ct or len(ct)%16: raise FrameError('ct-align','ciphertext empty or misaligned')
    pt=adec(aes_key,frame[10:26],ct)
    if len(pt)<5: raise FrameError('plaintext','plaintext too short')
    declared=struct.unpack_from('<I',pt,0)[0]; mt=pt[4]
    if declared>len(pt)-4 or (mt!=MSG_TASK and declared==0): raise FrameError('declared','invalid declared length')
    psize=declared if mt==MSG_TASK else declared-1
    if psize>len(pt)-5: raise FrameError('payload-bounds','payload beyond plaintext')
    return DecodedFrame(total,struct.unpack_from('<I',frame,6)[0],mt,frame[10:26],ct,pt,declared,bytes(pt[5:5+psize]))

def dec_actual(f,k,h): return decode_with(f,k,h,h8_own,ad_own)
def dec_oracle(f,k,h): return decode_with(f,k,h,h8_std,ad_std)

def outcome(frame,k,h):
    try:
        d=dec_actual(frame,k,h); return {'accepted':True,'exception_type':'','reject_stage':'','sequence':d.sequence,'message_type':d.message_type,'payload_len':len(d.payload)}
    except Exception as e:
        return {'accepted':False,'exception_type':type(e).__name__,'reject_stage':getattr(e,'stage','other'),'sequence':None,'message_type':None,'payload_len':None}

def parse_frames(buf):
    out=[]; off=0
    while len(buf)-off>=4:
        ln=struct.unpack_from('<I',buf,off)[0]
        if ln==0: out.append((b'\0\0\0\0','keepalive')); off+=4; continue
        if ln>MAX_REFERENCE_FRAME: break
        end=off+4+ln
        if end>len(buf): break
        out.append((buf[off:end],'frame')); off=end
    return out,buf[off:]

def derive_pair(sk,tr,hfun,sfun):
    def exp(sec,label,size):
        out=b''; prev=b''; c=1
        while len(out)<size:
            prev=hfun(sec,prev+label+bytes([c&255])); c+=1; out+=prev
        return out[:size]
    th=sfun(tr); sec=hfun(th,sk); ch=exp(sec,b'CLIENTCHAL',16); d=exp(sec,b'BDDATA',72)
    return {'transcript_hash':th,'secret':sec,'challenge':ch,'response_id':ch[8:16],'request_hmac':d[:20],'response_hmac':d[20:40],'decrypt':d[40:56],'encrypt':d[56:72]}

def derive_keys(sk,tr):
    std_hmac=lambda k,d: hmac.new(k,d,hashlib.sha1).digest()
    std_sha=lambda d: hashlib.sha1(d).digest()
    return derive_pair(sk,tr,OWN.hmac_sha1,OWN.sha1),derive_pair(sk,tr,std_hmac,std_sha)

def extract_groups(source,anchor,end_anchor=None):
    start=source.index(anchor); scope=source[start:] if end_anchor is None else source[start:source.index(end_anchor,start)]
    groups=re.findall(r'fromHex\(\s*((?:"[0-9a-fA-F]+"\s*)+)\)',scope,re.S)
    return [bytes.fromhex(''.join(re.findall(r'"([0-9a-fA-F]+)"',g))) for g in groups]

def load_fixture():
    s=DEMONWARE_TESTS.read_text(encoding='utf-8'); hs=extract_groups(s,'const auto clientHeader = fromHex(','const auto requestFrame = fromHex(')
    req=extract_groups(s,'const auto requestFrame = fromHex(','const auto responseFrame = fromHex(')[0]
    resp=extract_groups(s,'const auto responseFrame = fromHex(','const ServiceResponse reconstructed{')[0]
    return {'client_header':hs[0],'server_header':hs[1],'client_auth':hs[2],'request_frame':req,'response_frame':resp}

def verify_manifests():
    ans=[]
    for m,n in MANIFESTS:
        ok=0; miss=[]; bad=[]
        for line in m.read_text(encoding='utf-8-sig').splitlines():
            z=re.match(r'^([0-9a-fA-F]{64})\s{2}(.+)$',line)
            if not z: continue
            exp,rel=z.group(1).lower(),z.group(2); p=m.parent/rel
            if not p.exists(): miss.append(rel); continue
            act=sha256_path(p)
            if act==exp: ok+=1
            else: bad.append({'path':rel,'expected':exp,'actual':act})
        ans.append({'manifest':str(m),'expected_count':n,'verified_count':ok,'missing':miss,'mismatches':bad,'ok':ok==n and not miss and not bad})
    return ans

def baseline_check():
    paths=[]
    for p,exp in BASELINE_EXPECTED.items():
        act=sha256_path(p) if Path(p).exists() else 'MISSING'
        paths.append({'path':p,'expected_sha256':exp,'actual_sha256':act,'ok':act.lower()==exp.lower()})
    ms=verify_manifests()
    return {'paths':paths,'all_path_hashes_ok':all(x['ok'] for x in paths),'manifests':ms,'all_manifests_ok':all(x['ok'] for x in ms),'ok':all(x['ok'] for x in paths) and all(x['ok'] for x in ms)}

class SeqGate:
    def __init__(self,expected): self.expected=expected; self.trace=[]
    def offer(self,s):
        before=self.expected; ok=s==self.expected
        if ok: self.expected=(self.expected+1)&0xffffffff
        consistent=(ok and self.expected==((before+1)&0xffffffff)) or ((not ok) and self.expected==before)
        self.trace.append({'sequence':s,'expected_before':before,'accepted':ok,'expected_after':self.expected,'state_consistent':consistent}); return ok
def main():
    root=TASK; tools=root/'_tools'; data_dir=root/'_data'; tools.mkdir(parents=True,exist_ok=True); data_dir.mkdir(parents=True,exist_ok=True)
    baseline=baseline_check(); fx=load_fixture(); req,resp=fx['request_frame'],fx['response_frame']
    sk=b'Tencentticket'+b'\0'*11; tr=fx['client_header'][8:]+fx['server_header']+fx['client_auth'][:-8]
    ko,ks=derive_keys(sk,tr)
    expcap={'response_id':bytes.fromhex('c90ed582eebb16ae'),'request_hmac':bytes.fromhex('44a8f0765d50efb49563ab593a7c6308cec719cf'),'response_hmac':bytes.fromhex('39aad030b8d22445063da2c914ae574939e2ab68')}
    proj_req=CC.decrypt_task_frame(req,ko['decrypt'],ko['request_hmac'])
    proj_resp=CC.decrypt_task_frame(resp,ko['encrypt'],ko['response_hmac'])
    proj_checks={
        'request_hmac_ok':bool(proj_req and proj_req.get('hmac_ok')),
        'request_seq':bool(proj_req and proj_req.get('seq')==1),
        'request_plaintext_equal':bool(proj_req and proj_req.get('plain')==dec_actual(req,ko['decrypt'],ko['request_hmac']).plaintext),
        'response_hmac_ok':bool(proj_resp and proj_resp.get('hmac_ok')),
        'response_seq':bool(proj_resp and proj_resp.get('seq')==0x16),
        'response_plaintext_equal':bool(proj_resp and proj_resp.get('plain')==dec_actual(resp,ko['encrypt'],ko['response_hmac']).plaintext),
    }
    if not all(proj_checks.values()): raise RuntimeError(f'project-reference capture check failed: {proj_checks}')
    rows=[]; raws=[]
    def sub(name,expected,actual,ok,**extra):
        d={'name':name,'expected':expected,'actual':actual,'ok':bool(ok),'exception_type':extra.get('exception_type',''),'reject_stage':extra.get('reject_stage',''),'out_of_bounds':bool(extra.get('out_of_bounds',False)),'state_consistent':extra.get('state_consistent',True)}
        for k,v in extra.items():
            if k not in d: d[k]=v
        return d
    def add(tid,inp,src,exp,subs,notes,status=None,byte_match=None,first_diff=''):
        if status is None: status='PASS' if all(s['ok'] for s in subs) else 'FAIL'
        if byte_match is None: byte_match='YES' if status=='PASS' else ('N/A' if status.startswith('BLOCKED') else 'NO')
        actual='; '.join(s['actual'] for s in subs)
        row={'test_id':tid,'input_hash':canonical_input_hash(inp),'expected_source':src,'expected_result':exp,'actual_result':actual,'byte_match':byte_match,'first_difference':first_diff,'status':status,'notes':notes}
        rows.append(row); raws.append({**row,'input_material':jsonable(inp),'subcases':subs})
    # TC-16 roundtrip and primitive cross-check
    subs=[]; inputs=[]; iv=bytes(range(16))
    for idx,n in enumerate([0,1,3,7,15,16,17,63,64,65,255]):
        p=bytes((i*17+idx)&255 for i in range(n)); seq=[0,1,2,17,0x01020304][idx%5]
        fa=enc_actual(p,ko['decrypt'],ko['request_hmac'],seq,iv); fo=enc_oracle(p,ks['decrypt'],ks['request_hmac'],seq,iv)
        d=dec_actual(fa,ko['decrypt'],ko['request_hmac']); ok=(d.sequence==seq and d.message_type==MSG_TASK and d.payload==p and fa==fo)
        subs.append(sub(f'payload_len_{n}','roundtrip fields preserved and independent codecs agree',f'seq={d.sequence} type=0x{d.message_type:02x} payload_len={len(d.payload)} actual_eq_oracle={fa==fo} frame_len={len(fa)}',ok,payload_hex=p.hex(),frame_hex=fa.hex(),oracle_hex=fo.hex()))
        inputs.append({'payload':p,'seq':seq,'iv':iv})
    add('TC-16',inputs,'INDEPENDENT-IMPLEMENTATION','decode(encode(x)) preserves fields for fixed vectors; own and standard primitive codecs agree',subs,'Property/primitive cross-check, not a protocol-spec oracle. Empty-payload 0x86 frame is the 50-byte minimum legal frame.')
    # TC-17 layout
    p17=bytes([0x50,0x03,0xCB,1,2,3,4]); seq17=0x11223344; iv17=bytes(range(16)); f17=enc_actual(p17,ko['decrypt'],ko['request_hmac'],seq17,iv17); fo17=enc_oracle(p17,ks['decrypt'],ks['request_hmac'],seq17,iv17)
    total17=struct.unpack_from('<I',f17,0)[0]; ct17=f17[26:-8]; tag17=h8_std(ks['request_hmac'],f17[:-8])
    subs=[sub('length_field','little-endian u32 equals total-4',f'0x{total17:08x} total={len(f17)}',total17==len(f17)-4),sub('fixed_marker','AB 85 at offsets 4..5',f17[4:6].hex(),f17[4:6]==b'\xab\x85'),sub('sequence_offset','seq at 6..9',f17[6:10].hex(),f17[6:10]==struct.pack('<I',seq17)),sub('iv_offset','IV at 10..25',f17[10:26].hex(),f17[10:26]==iv17),sub('ciphertext_bounds','CT at 26..-8, nonempty and aligned',f'len={len(ct17)} mod16={len(ct17)%16}',len(ct17)>0 and len(ct17)%16==0),sub('tag_offset','last 8 bytes equal HMAC(frame[:-8])[:8]',f17[-8:].hex(),hmac.compare_digest(f17[-8:],tag17)),sub('oracle_byte_equality','own primitive frame equals standard-primitive frame','equal' if f17==fo17 else 'different',f17==fo17)]
    add('TC-17',{'payload':p17,'seq':seq17,'iv':iv17,'frame':f17,'oracle_frame':fo17},'BINARY-DERIVED','all fixed offsets and little-endian length semantics match KF-16/KF-17/KF-18',subs,'Layout uses frozen-client write offsets and an independently implemented primitive encoder.')
    # TC-18 captured frames
    rd=dec_actual(req,ko['decrypt'],ko['request_hmac']); rr=enc_actual(rd.payload,ko['decrypt'],ko['request_hmac'],rd.sequence,rd.iv,rd.message_type)
    qd=dec_actual(resp,ko['encrypt'],ko['response_hmac']); qr=enc_actual(qd.payload,ko['encrypt'],ko['response_hmac'],qd.sequence,qd.iv,qd.message_type)
    subs=[sub('captured_request_decode','captured request authenticates and decodes',f'seq={rd.sequence} type=0x{rd.message_type:02x} payload_len={len(rd.payload)}',rd.sequence==1 and rd.message_type==MSG_TASK),sub('captured_request_reencode','re-encoded request is byte-identical','byte-identical' if rr==req else 'different',rr==req,first_difference=first_difference(req,rr)),sub('captured_response_decode','captured response authenticates and decodes',f'seq={qd.sequence} type=0x{qd.message_type:02x} payload_len={len(qd.payload)}',qd.sequence==0x16 and qd.message_type==1),sub('captured_response_reencode','re-encoded response is byte-identical','byte-identical' if qr==resp else 'different',qr==resp,first_difference=first_difference(resp,qr))]
    add('TC-18',{'request_frame':req,'response_frame':resp,'session_key':sk,'transcript':tr},'PROJECT-REFERENCE','decode then re-encode frozen captured frames byte-for-byte',subs,'Frames and KAT are from DemonwareTests.cpp:2480-2549 (same project lineage); regression evidence only.')    # TC-19 correct MAC
    base=enc_actual(b'\x50\x03\xcb\x01\x02\x03\x04',ko['decrypt'],ko['request_hmac'],17,bytes(range(16))); et=h8_std(ks['request_hmac'],base[:-8]); o=outcome(base,ko['decrypt'],ko['request_hmac'])
    subs=[sub('generated_frame_tag','tag equals independent HMAC[:8]',base[-8:].hex(),hmac.compare_digest(et,base[-8:])),sub('generated_frame_accept','local fixture accepts correct tag',f"accepted={o['accepted']}",o['accepted']),sub('captured_request_tag','captured request tag matches independent HMAC','match' if hmac.compare_digest(h8_std(ks['request_hmac'],req[:-8]),req[-8:]) else 'different',hmac.compare_digest(h8_std(ks['request_hmac'],req[:-8]),req[-8:])),sub('captured_response_tag','captured response tag matches independent HMAC','match' if hmac.compare_digest(h8_std(ks['response_hmac'],resp[:-8]),resp[-8:]) else 'different',hmac.compare_digest(h8_std(ks['response_hmac'],resp[:-8]),resp[-8:]))]
    add('TC-19',{'frame':base,'aes_key':ko['decrypt'],'hmac_key':ko['request_hmac'],'captured_request':req,'captured_response':resp},'BINARY-DERIVED','correct MAC passes; positive captured controls pass',subs,'Coverage and 8-byte truncation are binary-derived; arithmetic is cross-checked with hashlib/hmac.')
    # TC-20 wrong MAC and covered-byte tamper without recompute
    subs=[]; bad=bytearray(base); bad[-1]^=1; o=outcome(bytes(bad),ko['decrypt'],ko['request_hmac']); subs.append(sub('tag_flip','reject with HMAC mismatch',f"accepted={o['accepted']} stage={o['reject_stage']}",(not o['accepted']) and o['reject_stage']=='hmac',exception_type=o['exception_type'],reject_stage=o['reject_stage']))
    for name,off in [('header_AB',4),('header_85',5),('sequence_byte',6),('iv_byte',10),('ciphertext_byte',26)]:
        b=bytearray(base); b[off]^=1; o=outcome(bytes(b),ko['decrypt'],ko['request_hmac']); subs.append(sub(name,'reject changed covered byte without recomputing tag',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],exception_type=o['exception_type'],reject_stage=o['reject_stage']))
    add('TC-20',{'frame':base,'tamper_offsets':[4,5,6,10,26,len(base)-1]},'BINARY-DERIVED','tampered tag and covered bytes are rejected without OOB',subs,'Local fixture rejection. Original client disconnect/discard/idempotence remains unverified.')
    # TC-21 tag length and truncation
    subs=[]; o=outcome(base,ko['decrypt'],ko['request_hmac']); subs.append(sub('tag_len_8','8-byte tag accepted',f"accepted={o['accepted']}",o['accepted']))
    f9=bytearray(base+b'\0'); struct.pack_into('<I',f9,0,len(f9)-4); o=outcome(bytes(f9),ko['decrypt'],ko['request_hmac']); subs.append(sub('tag_len_9','9-byte tag rejected',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    signed=base[:-8]; full=hmac.new(ko['request_hmac'],signed,hashlib.sha1).digest(); f20=bytearray(signed+full); struct.pack_into('<I',f20,0,len(f20)-4); o=outcome(bytes(f20),ko['decrypt'],ko['request_hmac']); subs.append(sub('tag_len_20','20-byte full digest rejected as 8-byte tag field',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    for n in (0,1,4,7):
        short=bytes(base[:-8+n]); o=outcome(short,ko['decrypt'],ko['request_hmac']); subs.append(sub(f'tag_len_{n}','short tag rejected',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    add('TC-21',{'frame':base,'tested_tag_lengths':[0,1,4,7,8,9,20]},'BINARY-DERIVED','only first 8 bytes are accepted as tag; 9/20/short forms reject',subs,'9/20-byte variants alter the signed span and therefore fail HMAC, matching documented truncation behavior.')
    # TC-22 coverage boundary and recomputed MAC distinction
    subs=[]; covered=base[:-8]; t8=h8_std(ks['request_hmac'],covered); t9=h8_std(ks['request_hmac'],base[:-9]); tf=h8_std(ks['request_hmac'],base)
    subs += [sub('coverage_frame_minus_8','frame[:-8] matches wire tag','match' if hmac.compare_digest(t8,base[-8:]) else 'different',hmac.compare_digest(t8,base[-8:])),sub('coverage_frame_minus_9','frame[:-9] does not match wire tag','different' if not hmac.compare_digest(t9,base[-8:]) else 'match',not hmac.compare_digest(t9,base[-8:])),sub('coverage_full_frame','full frame including tag does not match wire tag','different' if not hmac.compare_digest(tf,base[-8:]) else 'match',not hmac.compare_digest(tf,base[-8:]))]
    for name,off in [('header_AB',4),('sequence',6),('iv',10),('ciphertext',26)]:
        b=bytearray(base); b[off]^=1; b[-8:]=h8_std(ks['request_hmac'],bytes(b[:-8])); o=outcome(bytes(b),ko['decrypt'],ko['request_hmac']); mac_ok=hmac.compare_digest(h8_std(ks['request_hmac'],bytes(b[:-8])),bytes(b[-8:])); subs.append(sub(name,'recomputed tag authenticates; structural validity reported separately',f'mac_pass={mac_ok} accepted={o["accepted"]} stage={o["reject_stage"]}',mac_ok,reject_stage=o['reject_stage'],accepted_full_frame=o['accepted']))
    add('TC-22',{'frame':base,'covered_offsets':[4,6,10,26]},'BINARY-DERIVED','MAC covers frame[:-8] and excludes the tag; MAC validity is distinct from full-frame acceptance',subs,'Header/IV/ciphertext may pass MAC after recomputation but still fail structural or decrypt validation.')
    # TC-23 short-frame rejection
    subs=[]
    for n in range(5,34):
        b=bytearray(b'\0'*n)
        struct.pack_into('<I',b,0,n-4)
        b[4]=MARK1
        if n>=6: b[5]=MARK2
        o=outcome(bytes(b),ko['decrypt'],ko['request_hmac'])
        subs.append(sub(f'total_len_{n}','reject without OOB',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    add('TC-23',{'tested_total_lengths':list(range(5,34))},'PROJECT-REFERENCE','short tag/frame inputs rejected by local fixture without OOB',subs,'Binary evidence proves a Bad frame/payload-size branch exists, not the original client disposition; row is local-fixture rejection only.')
    # TC-24..TC-27 sequence model
    def seq_add(tid,expected,offers,exp,src,notes,status=None):
        g=SeqGate(expected); subs=[]
        for i,s in enumerate(offers):
            a=g.offer(s); t=g.trace[-1]; subs.append(sub(f'offer_{i}_seq_0x{s:08x}',exp,f"accepted={a} expected_after=0x{t['expected_after']:08x}",t['state_consistent'],accepted=a,expected_before=t['expected_before'],expected_after=t['expected_after']))
        add(tid,{'expected_initial':expected,'offered_sequences':offers},src,exp,subs,notes,status=status)
    seq_add('TC-24',1,[1,2],'accept normally and advance expected counter','BINARY-DERIVED','Normal in-order sequence numbers accepted and expected increments exactly once.')
    seq_add('TC-25',2,[1],'reject duplicate/replay and leave expected unchanged','BINARY-DERIVED','Strict-equality model rejects replay. Existing server-side references do not implement this client receive-counter check; model-only evidence.')
    seq_add('TC-26',2,[3,4],'reject forward gap and leave expected unchanged','BINARY-DERIVED','Strict-equality model rejects gaps. Existing server-side references do not implement this client receive-counter check; model-only evidence.')
    g27=SeqGate(0xFFFFFFFF); a27=g27.offer(0); t27=g27.trace[-1]; s27=[sub('expected_ffffffff_then_zero','candidate A strict equality rejects; candidate B modulo wrap accepts and advances to 1',f'strict-model accepted={a27} expected_after=0x{t27["expected_after"]:08x}',True,candidate_semantics=['strict equality rejects 0','modulo wrap accepts 0 and advances to 1'])]
    add('TC-27',{'expected_initial':0xFFFFFFFF,'offered_sequence':0},'UNKNOWN','wrap behavior not closed by frozen evidence; record candidates without selecting one',s27,'BLOCKED-INSUFFICIENT-SPEC: strict equality is proven, but no explicit wrap branch or runtime sample selects the wrap policy.',status='BLOCKED-INSUFFICIENT-SPEC',byte_match='N/A')
    # TC-28 keepalive
    ka=b'\0\0\0\0'; fs,rest=parse_frames(ka); fs2,rest2=parse_frames(ka+base)
    subs=[sub('keepalive_alone','one keepalive consumed and empty remainder',f'frames={[(f.hex(),t) for f,t in fs]} rest={rest.hex()}',len(fs)==1 and fs[0][1]=='keepalive' and rest==b''),sub('keepalive_before_frame','keepalive then frame split correctly',f'frames={[(f.hex(),t) for f,t in fs2]} rest={rest2.hex()}',len(fs2)==2 and fs2[0][1]=='keepalive' and fs2[1]==(base,'frame') and rest2==b'')]
    add('TC-28',{'keepalive':ka,'following_frame':base},'PROJECT-REFERENCE','u32 zero is consumed as keepalive by local parse fixture',subs,'Local/reference behavior only; not attributed to original client without runtime sample.')
    # TC-29 over-limit length
    subs=[]
    for v in (0x100001,0xFFFFFF,0xFFFFFFFF):
        buf=struct.pack('<I',v)+b'X'*32; fs,rest=parse_frames(buf); cr=v>=MAX_CLIENT_FRAME_EXCLUSIVE; subs.append(sub(f'length_0x{v:08x}','no frame accepted; oversized input retained/rejected; 0x100001 records the reference/client cap divergence',f'frames={len(fs)} rest_len={len(rest)} client_limit_reject={cr}',len(fs)==0 and rest==buf and (cr or v==0x100001)))
    add('TC-29',{'declared_lengths':[0x100001,0xFFFFFF,0xFFFFFFFF]},'BINARY-DERIVED','length values outside the frozen-client upper bound are rejected',subs,'Client disassembly rejects >=0xFFFFFF; local parser caps at 0x100000. Difference is documented in the diff report.')
    # TC-30 inconsistent declared/actual lengths
    subs=[]
    for decl,actual in [(0x100,4),(0x100,16),(0x100,33),(5,5),(33,33)]:
        buf=struct.pack('<I',decl)+b'\xab\x85'+b'Z'*max(0,actual-4); fs,rest=parse_frames(buf); o=outcome(buf,ko['decrypt'],ko['request_hmac']); subs.append(sub(f'declared_{decl}_actual_{actual}','incomplete frame is not consumed; remainder retained; direct decode rejects',f'frames={len(fs)} rest_len={len(rest)} decode_accepted={o["accepted"]} stage={o["reject_stage"]}',len(fs)==0 and rest==buf and not o['accepted'],reject_stage=o['reject_stage']))
    for decl in (len(base)-5,4,5):
        buf=struct.pack('<I',decl)+base[4:]+b'EXTRA'; fs,rest=parse_frames(buf); o=outcome(fs[0][0],ko['decrypt'],ko['request_hmac']) if fs else {'accepted':False,'reject_stage':'parse'}; subs.append(sub(f'declared_smaller_{decl}','short candidate rejected by length check; remainder retained',f'frames={len(fs)} rest_len={len(rest)} decode_accepted={o["accepted"]} stage={o["reject_stage"]}',bool(fs) and not o['accepted'],reject_stage=o['reject_stage']))
    add('TC-30',{'larger_than_actual':[(0x100,4),(0x100,16),(0x100,33)],'smaller_than_actual':[len(base)-5,4,5]},'PROJECT-REFERENCE','declared/actual mismatches neither create a valid frame nor lose a valid remainder',subs,'Local parser behavior only; original client failure disposition remains unverified.')
    # TC-31 ciphertext alignment
    subs=[]
    for n in (0,1,15,17):
        body=struct.pack('<I',30+n)+b'\xab\x85'+struct.pack('<I',9)+bytes(range(16))+b'C'*n; frame=body+h8_std(ks['request_hmac'],body); o=outcome(frame,ko['decrypt'],ko['request_hmac']); subs.append(sub(f'ct_len_{n}','reject empty or non-16-byte ciphertext length',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    add('TC-31',{'ciphertext_lengths':[0,1,15,17]},'BINARY-DERIVED','ciphertext must be non-empty and 16-byte aligned',subs,'15-byte input is rejected at the minimum-total check before alignment; all forms reject.')
    # TC-32 empty/short frame boundaries
    subs=[]
    for n in list(range(0,4))+list(range(4,50)):
        if n<4: frame=bytes(n)
        else:
            b=bytearray(b'\0'*n)
            struct.pack_into('<I',b,0,max(0,n-4))
            if n>=5: b[4]=MARK1
            if n>=6: b[5]=MARK2
            frame=bytes(b)
        o=outcome(frame,ko['decrypt'],ko['request_hmac']); subs.append(sub(f'total_len_{n}','reject short/empty input without OOB',f"accepted={o['accepted']} stage={o['reject_stage']}",not o['accepted'],reject_stage=o['reject_stage']))
    minf=enc_actual(b'',ko['decrypt'],ko['request_hmac'],1,bytes(16)); mo=outcome(minf,ko['decrypt'],ko['request_hmac']); subs.append(sub('minimum_legal_0x86_50_bytes','50-byte frame accepted',f'len={len(minf)} accepted={mo["accepted"]}',len(minf)==50 and mo['accepted']))
    add('TC-32',{'tested_lengths':list(range(0,50)),'minimum_legal_frame':minf},'BINARY-DERIVED','empty/short ciphertext frames (<50 bytes) reject; 50-byte minimum legal frame accepts',subs,'The 4-byte keepalive is excluded from the 0x85 short-frame test and is handled separately in TC-28.')
    # key assertions before output
    checks={k:(ko[k]==v and ks[k]==v) for k,v in expcap.items()}
    if not all(checks.values()): raise RuntimeError(f'capture key assertion failed: {checks}')
    csv_path=root/'CODOL_G3_FRAME_TEST_RESULTS_001.csv'; cols=['test_id','input_hash','expected_source','expected_result','actual_result','byte_match','first_difference','status','notes']
    with csv_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for r in rows: w.writerow(r)
    summary={'total':len(rows),'pass':sum(r['status']=='PASS' for r in rows),'fail':sum(r['status']=='FAIL' for r in rows),'blocked_missing_oracle':sum(r['status']=='BLOCKED-MISSING-ORACLE' for r in rows),'blocked_insufficient_spec':sum(r['status']=='BLOCKED-INSUFFICIENT-SPEC' for r in rows),'not_executed':sum(r['status']=='NOT-EXECUTED' for r in rows)}
    raw={'task':'CODOL-KEYFLOW-G3-FRAME-VALIDATION-001','generated':dt.datetime.now().isoformat(timespec='seconds'),'scope':{'offline_only':True,'game_started':False,'server_started':False,'network_used':False,'binary_modified':False},'environment':{'python':sys.version,'crypto':'own indep_primitives + hashlib/hmac + pycryptodome 3.23.0'},'baseline':baseline,'fixture':{'source':str(DEMONWARE_TESTS),'source_sha256':sha256_path(DEMONWARE_TESTS),'session_key_hex':sk.hex(),'transcript_len':len(tr),'captured_request_len':len(req),'captured_response_len':len(resp),'derived_keys_own':{k:v.hex() for k,v in ko.items()},'derived_keys_std':{k:v.hex() for k,v in ks.items()},'expected_cpp_assertions':{k:v.hex() for k,v in expcap.items()},'key_checks':checks,'project_reference_check':proj_checks},'summary':summary,'results':raws}
    with (data_dir/'g3_execution_log.json').open('w',encoding='utf-8',newline='\n') as f: json.dump(raw,f,ensure_ascii=False,indent=2)
    print('baseline_ok=',baseline['ok']); print('summary=',summary); print('csv=',csv_path); print('json=',data_dir/'g3_execution_log.json')
    return 0 if baseline['ok'] and summary['fail']==0 and summary['not_executed']==0 else 2
if __name__=='__main__': raise SystemExit(main())
