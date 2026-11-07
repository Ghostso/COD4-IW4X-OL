import hashlib, pathlib, sys
F = pathlib.Path(r'F:\桌面\ol\ol-mod-olfinal')
EV = pathlib.Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_t1_fix_evidence')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
cpp_now = (F / 'src/game_server/server_mp/sv_network_mp.cpp').read_text(encoding='utf-8')
hpp_now = (F / 'src/game_server/server_mp/sv_network_mp.hpp').read_text(encoding='utf-8')
cpp_old = cpp_now.replace('''        const std::lock_guard lock(mutex_);
        if (socket_.open())
        {
            // lastSocketError contract: every path below that returns true
            // CLEARS the sticky error, and every path that returns false leaves
            // it carrying the reason. A caller can therefore read a true result
            // as "no outstanding socket failure". See sv_network_mp.hpp.
            //
            // A live binding is never torn down just because start() was called
            // again. Port 0 means "any port", so an existing binding already
            // satisfies it; the requested address is not applied.
            if (port == 0)
            {
                status_.lastSocketError = 0;
                return true;
            }''', '''        const std::lock_guard lock(mutex_);
        if (socket_.open())
        {
            // A live binding is never torn down just because start() was called
            // again. Port 0 means "any port", so an existing binding already
            // satisfies it; the requested address is not applied.
            if (port == 0)
                return true;''')
cpp_old = cpp_old.replace('''                return false;
            }
            status_.lastSocketError = 0;
            return true;
        }''', '''                return false;
            }
            return true;
        }''')
hpp_old = hpp_now.replace('''        // lastSocketError contract: every path that returns true CLEARS it to 0,
        // and every path that returns false leaves it carrying the reason. A true
        // result therefore means "no outstanding socket failure", on the fresh
        // bind path and on both idempotent early returns alike.
        //
        // Idempotent while a socket is already open:
        //   port == 0                        -> the live binding already
        //                                       satisfies an ephemeral request;
        //                                       return true with the binding
        //                                       untouched, and the requested
        //                                       address is not applied
        //   same port, same bound address    -> return true with the binding
        //                                       untouched''', '''        // Idempotent while a socket is already open:
        //   port == 0                        -> the live binding already
        //                                       satisfies an ephemeral request;
        //                                       return true, unchanged, and the
        //                                       requested address is not applied
        //   same port, same bound address    -> return true, unchanged''')
(EV / 'pre_ff2_sv_network_mp.cpp').write_text(cpp_old, encoding='utf-8', newline='')
(EV / 'pre_ff2_sv_network_mp.hpp').write_text(hpp_old, encoding='utf-8', newline='')
print('reconstructed cpp sha256 =', sha(EV / 'pre_ff2_sv_network_mp.cpp'))
print('baseline     cpp sha256 = AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6')
print('match cpp =', sha(EV / 'pre_ff2_sv_network_mp.cpp') == 'AF93F7C8EEDE4E4C4417835F73D943544D906A7E1F3C5FBA9892CB82EEC58AA6')
print('reconstructed hpp sha256 =', sha(EV / 'pre_ff2_sv_network_mp.hpp'))
print('baseline     hpp sha256 = A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915')
print('match hpp =', sha(EV / 'pre_ff2_sv_network_mp.hpp') == 'A5BBE54734A1F7DBB675F73CF1BAE4BC420C38B6E39A1D48B64EC67047F40915')