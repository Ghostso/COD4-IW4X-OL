# 042 self-verification — re-derived from raw image bytes (read-only)

CHECK	RESULT	DETAIL
image_sha256	PASS	17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045
image_base	PASS	0x400000
s_netbuf_notenough	PASS	b'; net-buffer NOT enough: real_len<%d> si'
s_string_len_err	PASS	
s_wstring_len_err	PASS	
s_unit_notenough	PASS	
s_str_format_err	PASS	
ref_netbuf_notenough	PASS	['0x87cddb']
ref_unit_notenough	PASS	['0x87c80a', '0x87decc']
sizeinfo_entry	PASS	558bec51
sizeinfo_width2	PASS	81ff80000000
sizeinfo_width3	PASS	81ff00010000
sizeinfo_width4	PASS	81ff00000100
deser1_entry	PASS	b8f4170000
deser2_entry	PASS	b80c180000
dispatcher_entry	PASS	b87c9d0000
dispatcher_typeread	PASS	0fb74424
dispatcher_sub2	PASS	83e802
dispatcher_je	PASS	744c
dispatcher_sub2b	PASS	83e802
tqos_cspkg	PASS	b'QOSCSPkg'
tqos_udp	PASS	b'udp://%s:%d'
tqos_helper	PASS	
deser1_caller	PASS	['0x85d49d']
oob_getchallenge_ref	PASS	['0x1c071f']
oob_connectresponse_ref	PASS	['0x1c17b5']
image_size	PASS	0xa65000
recv_slot_unavailable	PASS	0xCA84E8 beyond image
code_section_present	PASS	code section fully present

OVERALL: PASS
