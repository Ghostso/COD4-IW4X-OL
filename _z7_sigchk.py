from cryptography import x509
for p in [r"CODOLServer\lobby_server\lobby_server.pem",
          r"CODOLServer\lobby_server\lobby_server.pem.bak_20261002_223811"]:
    try:
        c = x509.load_pem_x509_certificate(open(p,"rb").read())
        print("  %-58s sig=%s" % (p.split("\\")[-1], c.signature_algorithm_oid._name))
    except Exception as e:
        print("  ", p, "ERR", e)
