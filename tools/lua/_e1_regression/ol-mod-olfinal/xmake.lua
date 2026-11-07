set_project("ol-mod")
set_version("0.1.0")
set_xmakever("3.0.9")

set_allowedplats("windows")
set_allowedarchs("windows|x86")
set_defaultplat("windows")
set_defaultarchs("windows|x86")
set_defaultmode("release")
set_toolchains("msvc")

add_rules("mode.debug", "mode.release")
set_languages("c++latest")
set_encodings("utf-8")
set_warnings("all", "extra")
set_policy("build.warning", true)

if is_mode("debug") then
    set_runtimes("MTd")
    set_symbols("debug")
else
    set_runtimes("MT")
    set_optimize("fastest")
    set_policy("build.optimization.lto", true)
end

add_cxxflags("/Zc:__cplusplus", "/permissive-", "/arch:SSE2", {tools = "cl"})
add_ldflags("/INCREMENTAL:NO", {tools = "link"})

-- BUILD ENVIRONMENT, NOT BEHAVIOUR. This tree linked user32/advapi32/crypt32 by
-- accident for its whole life: older MSVC CRTs name them in their own /DEFAULTLIB
-- directives, so nothing had to ask. xmake now resolves "Microsoft Visual Studio
-- (x86) version ... 2026" here and that default set is trimmed, so a build that
-- linked cleanly at 14:11 stopped linking at 14:39 with 34 unresolved externals
-- and NO source change -- confirmed by rebuilding the previous commit, which
-- fails identically.
--
-- Every one of the 34 is named by a library that already declares what it needs:
--   user32    ClientProcessPatches' raw-input hook and RuntimeLog's console window
--             (RegisterRawInputDevices, GetRawInputData, CallWindowProcA,
--              SetWindowLongA, IsWindow, ShowWindow, IsWindowVisible)
--   advapi32  libcrypto's rand_win/e_capi (CryptGenRandom, CryptAcquireContextW,
--             the event-log calls)
--   crypt32   libcrypto's certificate store (CertOpenStore, CertCloseStore, ...)
-- and vcpkg's own libcrypto.pc states the same list outright:
--   Libs: "-L${libdir}" -llibcrypto -lcrypt32 -lws2_32 -ladvapi32 -luser32
-- so this declares a real dependency that was always there rather than papering
-- over a missing symbol.
add_syslinks("user32", "advapi32", "crypt32")

set_targetdir("build/bin/$(mode)")
set_objectdir("build/obj/$(mode)/$(target)")
set_dependir("build/deps/$(mode)/$(target)")

-- Reuse the already installed static x86 OpenSSL package through vcpkg.
-- nlohmann_json is header-only and is resolved through xmake-repo.
local vcpkg_baseline = "aa2d37682e3318d93aef87efa7b0e88e81cd3d59"
add_requires("vcpkg::openssl", {
    alias = "openssl",
    configs = {baseline = vcpkg_baseline}
})
add_requires("vcpkg::mhook", {
    alias = "mhook",
    configs = {baseline = vcpkg_baseline}
})
add_requires("nlohmann_json 3.12.0")
add_requires("lua 5.4.8", {configs = {shared = false}})

local backend_core = {
    "src/backend/Demonware/*.cpp",
    "src/backend/DedicatedBookingDispatcher.cpp",
    "src/backend/SharedRoomClient.cpp",
    "src/backend/SharedRoomControl.cpp",
    "src/backend/SharedRoomSessionOwner.cpp",
    "src/backend/Servers.cpp",
    "src/shared/DedicatedControl.cpp",
    "src/shared/CodolPlaylist.cpp",
    "src/shared/DedicatedSession.cpp",
    "src/shared/RuntimeLog.cpp"
}

local backend_headers = {
    "src/backend/**.hpp",
    "src/shared/DedicatedControl.hpp",
    "src/shared/CodolPlaylist.hpp",
    "src/shared/DedicatedSession.hpp",
    "src/shared/LocalnetServer.hpp",
    "src/shared/ProcessRole.hpp",
    "src/shared/RuntimeLog.hpp"
}

local game_server_core = {
    "src/client_bridge/ClientSessionBridge.cpp",
    "src/game_server/ClientProcessPatches.cpp",
    "src/game_server/ClientAnimtreeHook.cpp",
    "src/game_server/ClientRenderFrameHook.cpp",
    "src/game_server/DedicatedProcessPatches.cpp",
    "src/game_server/DisconnectWitness.cpp",
    "src/game_server/PlayerDataDef.cpp",
    "src/game_server/qcommon/*.cpp",
    "src/game_server/server_mp/*.cpp",
    "src/game_server/win32/*.cpp",
    "src/shared/DedicatedControl.cpp",
    "src/shared/CodolPlaylist.cpp",
    "src/shared/DedicatedSession.cpp",
    "src/shared/RuntimeLog.cpp"
}

local game_server_headers = {
    "src/client_bridge/ClientSessionBridge.hpp",
    "src/game_server/**.hpp",
    "src/shared/DedicatedControl.hpp",
    "src/shared/CodolPlaylist.hpp",
    "src/shared/DedicatedSession.hpp",
    "src/shared/ProcessRole.hpp",
    "src/shared/RuntimeLog.hpp"
}

local localnetworking_core = {
    "src/localnetworking/Localnetworking.cpp",
    "src/localnetworking/RuntimePaths.cpp",
    "src/localnetworking/WinsockHooks.cpp"
}

local localnetworking_headers = {
    "src/localnetworking/*.hpp",
    "src/shared/LocalnetServer.hpp"
}

local platformwrapper_core = {
    "src/platformwrapper/PlatformConfig.cpp",
    "src/platformwrapper/Tencent.cpp",
    "src/platformwrapper/Hooks.cpp"
}

local platformwrapper_headers = {
    "src/platformwrapper/*.hpp"
}

target("ol_localnetworking")
    set_kind("shared")
    set_group("plugins")
    set_filename("LocalnetworkingRe.Ayria32")
    add_files(table.unpack(localnetworking_core))
    add_headerfiles(table.unpack(localnetworking_headers))
    add_files("src/localnetworking/Appmain.cpp")
    add_includedirs("src")
    add_packages("mhook")
    add_links("ws2_32")

target("ol_platformwrapper")
    set_kind("shared")
    set_group("plugins")
    set_filename("PlatformwrapperRe.Ayria32")
    add_files(table.unpack(platformwrapper_core))
    add_headerfiles(table.unpack(platformwrapper_headers))
    add_files("src/platformwrapper/Appmain.cpp")
    add_includedirs("src")
    add_packages("mhook", "nlohmann_json")
    add_links("user32")

target("ol_backend")
    set_kind("shared")
    set_group("plugins")
    set_filename("AlwaysofflineRe.Localnet32")
    add_files(table.unpack(backend_core))
    add_headerfiles(table.unpack(backend_headers))
    add_files("src/backend/Appmain.cpp")
    add_includedirs("src", "src/backend")
    add_packages("openssl", "nlohmann_json")
    add_links("bcrypt", "ws2_32")

target("ol_room_owner")
    set_kind("binary")
    set_group("servers")
    set_default(false)
    add_files(
        "src/backend/SharedRoomHost.cpp",
        "src/backend/SharedRoomControl.cpp",
        "src/backend/SharedRoomSessionOwner.cpp",
        "src/shared/DedicatedControl.cpp"
    )
    add_headerfiles(
        "src/backend/SharedRoomControl.hpp",
        "src/backend/SharedRoomSessionOwner.hpp",
        "src/shared/DedicatedControl.hpp"
    )
    add_includedirs("src")
    add_links("ws2_32")

target("ol_game_server")
    set_kind("shared")
    set_group("plugins")
    set_filename("CodolGameServer.Localnet32")
    -- Resolve sampled release-build stall addresses without changing optimization.
    add_shflags("/MAP", {tools = "link", force = true})
    add_files(table.unpack(game_server_core))
    add_headerfiles(table.unpack(game_server_headers))
    add_files(
        "src/game_server/Appmain.cpp",
        "src/game_server/ClientNoclipHotkey.cpp",
        "src/game_server/EngineBindings.cpp",
        "src/game_server/ClientCommandTrace.cpp",
        "src/game_server/FrameHook.cpp",
        "src/game_server/NativeEntityStateBindings.cpp",
        "src/game_server/NativeWeaponBindings.cpp",
        "src/game_server/NativeWeaponMovementBindings.cpp",
        "src/game_server/NativePmoveBindings.cpp"
    )
    add_includedirs("src/game_server")
    add_packages("openssl", "lua", "nlohmann_json")
    add_links("ws2_32")

target("ol_deploy")
    set_kind("phony")
    set_group("distribution")
    set_default(true)
    add_deps("ol_localnetworking", "ol_platformwrapper", "ol_backend", "ol_game_server", "ol_room_owner")
    after_build(function (target)
        local build_mode = get_config("mode") or "release"
        local config_file = path.join(os.projectdir(), "config", "codol-game-dir.txt")
        local game_directory = ""
        if os.isfile(config_file) then
            game_directory = io.readfile(config_file) or ""
            game_directory = game_directory:gsub("^\239\187\191", "")
            game_directory = game_directory:match("^%s*(.-)%s*$") or ""
        end

        if #game_directory == 0 then
            cprint("${yellow}CODOL deployment skipped: config/codol-game-dir.txt is empty.")
            return
        end

        local installer = path.join(os.projectdir(), "tools", "distribution", "InstallCodolRuntime.ps1")
        os.vrunv("powershell.exe", {
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", installer,
            "-GameDirectory", game_directory,
            "-Mode", build_mode,
            "-SkipBuild"
        })
    end)

target("ol_backend_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(table.unpack(backend_core))
    add_headerfiles(table.unpack(backend_headers))
    add_files("tests/backend/DemonwareTests.cpp", "tests/backend/ServerTests.cpp")
    add_includedirs("src", "src/backend")
    add_packages("openssl", "nlohmann_json")
    add_links("bcrypt", "ws2_32")
    add_tests("default", {rundir = os.projectdir()})

target("ol_game_server_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_ldflags("/STACK:8388608", {force = true})
    add_files(table.unpack(game_server_core))
    add_headerfiles(table.unpack(game_server_headers))
    add_files("tests/game_server/ServerCoreTests.cpp")
    add_includedirs("src/game_server")
    add_packages("openssl", "lua", "nlohmann_json")
    add_links("ws2_32")
    add_tests("default", {rundir = os.projectdir()})

target("ol_playerdata_def_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    -- The def walker needs nothing from the engine: no sockets, no game state, no
    -- packages. Its own target so it stays a second to build and a second to run.
    add_files("src/game_server/PlayerDataDef.cpp")
    add_headerfiles("src/game_server/PlayerDataDef.hpp")
    add_files("tests/game_server/PlayerDataDefTests.cpp")
    add_includedirs("src/game_server")
    add_tests("default", {rundir = os.projectdir()})

target("ol_dedicated_control_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(
        "src/client_bridge/ClientSessionBridge.cpp",
        "src/shared/CodolPlaylist.cpp",
        "src/shared/DedicatedControl.cpp",
        "src/shared/DedicatedSession.cpp"
    )
    add_headerfiles(
        "src/shared/CodolPlaylist.hpp",
        "src/shared/DedicatedControl.hpp",
        "src/shared/DedicatedSession.hpp",
        "src/shared/ProcessRole.hpp"
    )
    add_files(
        "tests/shared/DedicatedControlTests.cpp",
        "tests/shared/DedicatedSessionTests.cpp",
        "tests/shared/ClientSessionBridgeTests.cpp"
    )
    add_includedirs("src")
    add_links("ws2_32")
    add_tests("default", {rundir = os.projectdir()})

target("ol_lua_runtime_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(table.unpack(game_server_core))
    add_headerfiles(table.unpack(game_server_headers))
    add_files("tests/game_server/LuaRuntimeTests.cpp")
    add_includedirs("src/game_server")
    add_packages("openssl", "lua", "nlohmann_json")
    add_links("ws2_32")
    add_tests("default", {rundir = os.projectdir()})

-- Real-socket transport lifecycle: loopback binding, start() idempotency,
-- stop() state cleanup and rebinding. Offline; no game process or injection.
target("ol_transport_lifecycle_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(table.unpack(game_server_core))
    add_headerfiles(table.unpack(game_server_headers))
    add_files("tests/game_server/TransportLifecycleTests.cpp")
    add_includedirs("src/game_server")
    add_packages("openssl", "lua", "nlohmann_json")
    add_links("ws2_32")
    add_tests("default", {rundir = os.projectdir()})

target("ol_localnetworking_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(
        "src/localnetworking/Localnetworking.cpp",
        "src/localnetworking/RuntimePaths.cpp",
        "src/localnetworking/WinsockHooks.cpp",
        "tests/localnetworking/RuntimeTests.cpp"
    )
    add_headerfiles(table.unpack(localnetworking_headers))
    add_includedirs("src")
    add_packages("mhook")
    add_links("ws2_32")
    add_deps("ol_localnetworking", "ol_localnetworking_fixture")
    add_tests("default", {rundir = os.projectdir()})

target("ol_localnetworking_fixture")
    set_kind("shared")
    set_group("tests")
    set_default(false)
    set_filename("Fixture.Localnet32")
    set_targetdir("build/bin/$(mode)/localnetworking_fixture/Plugins")
    add_files("tests/localnetworking/FixturePlugin.cpp")
    add_headerfiles("src/shared/LocalnetServer.hpp")
    add_includedirs("src")

target("ol_platformwrapper_tests")
    set_kind("binary")
    set_group("tests")
    set_default(false)
    set_rundir(os.projectdir())
    add_files(
        "src/platformwrapper/PlatformConfig.cpp",
        "src/platformwrapper/Tencent.cpp",
        "tests/platformwrapper/RuntimeTests.cpp"
    )
    add_headerfiles(table.unpack(platformwrapper_headers))
    add_includedirs("src")
    add_packages("nlohmann_json")
    add_links("user32")
    add_deps("ol_platformwrapper")
    add_tests("default", {rundir = os.projectdir()})

target("ol_archived_tls_probe")
    set_kind("binary")
    set_group("probes")
    set_default(false)
    add_files(
        "src/backend/Demonware/ByteBuffer.cpp",
        "src/backend/Demonware/Crypto.cpp",
        "src/backend/Demonware/LobbyProtocol.cpp",
        "src/backend/Demonware/ServiceRegistry.cpp",
        "tests/backend/ArchivedTlsProbe.cpp"
    )
    add_headerfiles(
        "src/backend/IServer.hpp",
        "src/backend/Demonware/ByteBuffer.hpp",
        "src/backend/Demonware/Crypto.hpp",
        "src/backend/Demonware/LobbyProtocol.hpp",
        "src/backend/Demonware/ServiceRegistry.hpp",
        "src/shared/LocalnetServer.hpp"
    )
    add_includedirs("src/backend")
    add_packages("openssl")
    add_links("bcrypt", "ws2_32")
