# 043 self-verification — re-derived from raw bytes (read-only)

CHECK	RESULT	DETAIL
sha_dll	PASS	ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20
sha_exe	PASS	36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
sha_img	PASS	17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045
conv_gamestate	PASS	b'gamestateupdate %'
conv_connectResponse	PASS	b'connectResponse'
conv_cgservercommand	PASS	b'CG_ServerCommand:'
conv_netbuffer_str	PASS	3b206e65742d627566666572204e4f5420656e6f756768
exe_img_same_ep	PASS	0xe5dc690
exe_img_same_ts	PASS	0x6096930a
img_len	PASS	0xa65000
iat_out_of_image	PASS	0xCA84E8 beyond
encoder_tag_0C	PASS	c603
encoder_threshold_0x80	PASS	81ff80000000
encoder_threshold_0x100	PASS	81ff00010000
encoder_threshold_0x10000	PASS	81ff00000100
helper_744b20_true	PASS	b801000000c3
deser_ebx8_count_2	PASS	2
deser2_reads_buf	PASS	8b33
deser1_caller	PASS	['0x85d49d']
deser2_callers	PASS	['0x85d3db', '0x85d418', '0x85d9b5', '0x85d9f7']
encoder_caller	PASS	['0x879ce3']
ref_netbuf_real_len	PASS	['0x87cddb']
ref_unit_size	PASS	['0x87c80a', '0x87decc']
ref_wstring_fmt	PASS	['0x87e306']
tqos_cspkg_ref	PASS	['0x85d2f6']
tqos_udp_ref	PASS	['0x85d7cb', '0x85d89a']
tqos_create_err_ref	PASS	['0x85ebd0']
dispatcher_typeread	PASS	0fb74424
dispatcher_sub2	PASS	83e802
deser_entries_independent	PASS	b8f4170000/b80c180000

OVERALL: PASS
