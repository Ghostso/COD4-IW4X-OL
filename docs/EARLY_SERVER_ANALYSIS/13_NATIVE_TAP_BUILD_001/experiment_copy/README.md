# sh1x server

**Call of Duty Online Closed Alpha Server**

This server is a fork of CoD4x, adapted for **CoDOL 1.1.1.13**, using the existing alpha0022
research and implementation. Changes are compiled into the server source;
no client hooks, injection, or Python game-server proxy are used.

**This is an incomplete port, not a playable CoDOL server.** Native netchan
fragmentation, user-command decoding, and the engine input bridge are integrated.
The bdDTLS DATA codec and native encrypted fastfile/rawfile reader are tested;
mounted rawfiles feed the script source compiler. The handshake, session manager,
CoDOL snapshots, configstrings, runtime asset translation, and gameplay extensions
still need porting. See [port status, evidence, and build instructions](docs/CODOL_PORT.md).

`make` builds `bin/codol_dedrun` (or `.exe` on Windows).
`make GAME=iw4ol` builds the upstream wire profile. Use `--codol-info` to inspect
the CoDOL executable without loading game assets or opening sockets.

## Origin

This server is a fork of CoD4x. It is licensed under the AGPL3 license; see
[License.md](License.md), [copying.md](copying.md) and [Copyright.md](Copyright.md).

## Compiling on Linux

Prerequisites: NASM, gcc and make (32-bit toolchain).

RHEL/CentOS/Rocky Linux 32-bit:
```
sudo yum install -y glibc-devel glibc-devel.i686 libgcc.i686 libstdc++-devel.i686 nasm
```

Debian/Ubuntu 64-bit:
```
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install nasm:i386 make gcc-multilib g++-multilib git
```

Arch Linux 64-bit:
```
sudo pacman -S nasm gcc lib32-gcc-libs make
```

Then run `make`. The binary is placed in `bin/`.

## Compiling on Windows

Use msys2 (mingw32 toolchain, NASM and make) and run `tools/BUILD-CODOL.ps1`,
or see the build instructions in [docs/CODOL_PORT.md](docs/CODOL_PORT.md).
