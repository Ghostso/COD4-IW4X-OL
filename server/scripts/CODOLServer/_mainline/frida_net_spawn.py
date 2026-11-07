#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
frida_net_spawn.py -- spawn CODOL suspended, inject Frida before ACE arms,
then log all ws2_32 network calls.

Run elevated. Observation only by default; --redirect replaces selected
hostnames with 127.0.0.1 inside getaddrinfo.
"""

import argparse
import json
import os
import sys
import time

import frida

JS = r"""
'use strict';
var redirect = %REDIRECT%;
var targets = ["ied-tqos.qq.com","tqos.gamesafe.qq.com",
               "cod4master.activision.com","stun.us.demonware.net",
               "stun.eu.demonware.net","stun.jp.demonware.net",
               "stun.au.demonware.net"];
function s(x){ try { return x.readAnsiString(); } catch(e) { return null; } }
function emit(o){ send(o); }
function hook(name, cb){
  var p = Module.findExportByName('ws2_32.dll', name);
  if (!p) { emit({type:'missing',api:name}); return; }
  Interceptor.attach(p, cb);
  emit({type:'hooked',api:name,address:p.toString()});
}
hook('getaddrinfo', {
  onEnter: function(args){
    var host=s(args[0]);
    emit({type:'getaddrinfo',host:host});
    if (redirect && host){
      for (var i=0;i<targets.length;i++){
        if (host===targets[i]) {
          args[0] = Memory.allocUtf8String('127.0.0.1');
          emit({type:'redirect',from:host,to:'127.0.0.1'});
          break;
        }
      }
    }
  }
});
hook('gethostbyname', {
  onEnter: function(args){ emit({type:'gethostbyname',host:s(args[0])}); }
});
function sockaddr(ptr, len){
  try {
    var fam = ptr.readU16();
    if (fam === 2) {
      var port = (ptr.add(2).readU8()<<8) | ptr.add(3).readU8();
      var ip = ptr.add(4).readU8()+'.'+ptr.add(5).readU8()+'.'+
               ptr.add(6).readU8()+'.'+ptr.add(7).readU8();
      return {family:fam, ip:ip, port:port};
    }
    return {family:fam, raw:ptr.readByteArray(len>64?64:len)};
  } catch(e) { return {error:String(e)}; }
}
hook('connect', {
  onEnter: function(args){
    emit({type:'connect',socket:args[0].toInt32(),addr:sockaddr(args[1],16)});
  },
  onLeave: function(ret){ emit({type:'connect_ret',ret:ret.toInt32()}); }
});
hook('WSAConnect', {
  onEnter: function(args){
    emit({type:'WSAConnect',socket:args[0].toInt32(),addr:sockaddr(args[1],16)});
  }
});
hook('send', {
  onEnter: function(args){
    var n=args[2].toInt32();
    var data=null;
    try { data=args[1].readByteArray(n>512?512:n); } catch(e){}
    emit({type:'send',socket:args[0].toInt32(),len:n,data:data});
  },
  onLeave: function(ret){ emit({type:'send_ret',ret:ret.toInt32()}); }
});
hook('sendto', {
  onEnter: function(args){
    var n=args[2].toInt32();
    var data=null;
    try { data=args[1].readByteArray(n>512?512:n); } catch(e){}
    emit({type:'sendto',socket:args[0].toInt32(),len:n,
          to:sockaddr(args[4],16),data:data});
  }
});
hook('recv', {
  onEnter: function(args){ this.sock=args[0].toInt32(); this.buf=args[1]; this.len=args[2].toInt32(); },
  onLeave: function(ret){
    var n=ret.toInt32(); var data=null;
    if(n>0){ try{ data=this.buf.readByteArray(n>512?512:n); }catch(e){} }
    emit({type:'recv',socket:this.sock,len:n,data:data});
  }
});
hook('recvfrom', {
  onEnter: function(args){ this.sock=args[0].toInt32(); this.buf=args[1]; },
  onLeave: function(ret){
    var n=ret.toInt32(); var data=null;
    if(n>0){ try{ data=this.buf.readByteArray(n>512?512:n); }catch(e){} }
    emit({type:'recvfrom',socket:this.sock,len:n,data:data});
  }
});
emit({type:'ready'});
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=120.0)
    ap.add_argument('--redirect', action='store_true')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    trace_path = os.path.join(args.out, 'frida_net.jsonl')
    log_path = os.path.join(args.out, 'frida_net.log')
    trace = open(trace_path, 'w', encoding='utf-8')
    log = open(log_path, 'w', encoding='utf-8')

    def emit(obj):
        trace.write(json.dumps(obj, ensure_ascii=False) + '\n')
        trace.flush()
        if obj.get('type') not in ('send', 'recv', 'sendto', 'recvfrom'):
            log.write(json.dumps(obj, ensure_ascii=False) + '\n')
            log.flush()
            print(json.dumps(obj, ensure_ascii=False), flush=True)

    js = JS.replace('%REDIRECT%', 'true' if args.redirect else 'false')
    device = frida.get_local_device()
    argv = [args.exe, '-q', '--disable-gpu', '--disable-gpu-compositing']
    print('spawning', argv, flush=True)
    pid = device.spawn(argv, cwd=args.cwd)
    print('pid', pid, flush=True)
    try:
        session = device.attach(pid, persist_timeout=0)
    except Exception as exc:
        print('attach failed: %r; resuming so the game is not left suspended'
              % (exc,), flush=True)
        device.resume(pid)
        return 1
    print('attached', flush=True)
    script = session.create_script(js)

    def on_message(message, data):
        if message.get('type') == 'send':
            obj = message.get('payload')
            if isinstance(obj, dict) and 'data' in obj and data:
                obj['data_hex'] = data.hex()
                obj.pop('data', None)
            emit(obj)
        else:
            emit({'type': 'frida_message', 'message': message})

    script.on('message', on_message)
    print('loading script...', flush=True)
    script.load()
    print('script loaded; resuming', flush=True)
    device.resume(pid)

    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(0.5)
    try:
        session.detach()
    except Exception:
        pass
    trace.close()
    log.close()
    print('done pid', pid, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
