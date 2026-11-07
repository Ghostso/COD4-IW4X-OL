# 041 self-verification — re-derived from raw DLL bytes (read-only)

CHECK	RESULT	DETAIL
dll_sha256	PASS	ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20
recv_call_bytes	PASS	ff15482ab010
recvfrom_slot_ordinal17	PASS	0x80000011
wsasocketw_unique	PASS	['0x235d6d']
wsasocketw_args	PASS	6a006a006a006a016a036a02
icmp_type8	PASS	c60708
icmp_id_write	PASS	894f04
icmp_seq_write	PASS	66895f08
icmp_ts_write	PASS	89570c
checksum_loop6	PASS	c745fc06000000
checksum_not	PASS	f7d0
sendto_call	PASS	ff154c2ab010
sendto_len30	PASS	6a30
buf_ref_count_3	PASS	[('0x235f08', 'mov'), ('0x235f76', 'lea'), ('0x235f94', 'mov')]
no_rep_movs	PASS	no movs/movsb
ihl_and0f	PASS	8a8df4feffff80
ihl_shl2	PASS	6603d26603d2
type0_check	PASS	803900
out_rtt_write	PASS	2b410c8bb5e0fe
out_seq_write	PASS	66891e
out_ttl_write	PASS	894e0c
ttl_read_buf8	PASS	0fb68dfcfeffff
plen_minus10	PASS	83ef
return_zero	PASS	33c0
caller_call	PASS	e8164d0000
caller_out_ptr	PASS	8d442414
caller_push_out	PASS	50
createthread_call	PASS	ff152c23b010
lpstart_addr	PASS	6850102310
threadproc_ref	PASS	dword refs=1
cluster_recv_sites	PASS	['0x235f7e', '0x42d97f', '0x670daf']
launcher_upstream_sec	PASS	[('0x3512437', '.tvm0')]
frame_out_base_rel0	PASS	[0]
frame_thisD_rel16	PASS	[16]
frame_reader171_out04	PASS	[4]
frame_reader175_out0C	PASS	[12]
frame_D_socket_rel16	PASS	[16]
frame_D_event_rel20	PASS	[20]
frame_job4_from_out04	PASS	8b4c24
frame_job8_from_out0C	PASS	8b5424

OVERALL: PASS
