# Evidence: the COD OL client statically links OpenSSL 1.1.1.
# 239 crypto\*.c source-file paths were recovered from a live memory dump
# (region around VA 0x3d58f000..0x3d5c9000) during a run that reached
# DW_LOBBY_CONNECTED.  Key files proving the primitives actually used:
#   crypto\rsa\rsa_pk1.c, rsa_oaep.c, rsa_ossl.c, rsa_sign.c
#   crypto\evp\e_aes.c, evp_enc.c, digest.c
#   crypto\bn\bn_exp.c, bn_mont.c (modexp - the RSA core)
#   crypto\kdf\hkdf.c
# The "aes 1.1.4" / "sha256" identifier strings sit in the client's own
# string pool next to the fastfile magics IWffs100/IWff0100/IWffu100.
#
# Consequence: the .ff layer-1 chain (RSA PKCS#1 v1.5 via the embedded
# ZoneKey, then AES-CTR) is a *standard* OpenSSL construction - which is why
# a hand-rolled RSA (pure-python pow) and pycryptodome AES-CTR reproduce it
# byte-exactly (see FF_LAYER1_DECRYPT_20260930.md).
