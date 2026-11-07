#include "Launcher.h"

#include <shellapi.h>
#include <shlwapi.h>

#include <fstream>
#include <iomanip>
#include <sstream>
#include <ctime>

#include "BootstrapMonitor.h"
#include "GameProcess.h"
#include "LauncherContext.h"
#include "TCLSCompatibility.h"
#include "Version.h"

namespace codol {

std::wstring NowIso() {
  SYSTEMTIME st = {};
  GetLocalTime(&st);
  wchar_t buf[64] = {};
  swprintf_s(buf, L"%04d-%02d-%02dT%02d:%02d:%02d.%03d", st.wYear, st.wMonth,
             st.wDay, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
  return buf;
}

std::wstring GetLastErrorText(DWORD code) {
  wchar_t* buffer = nullptr;
  DWORD flags = FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
                 FORMAT_MESSAGE_IGNORE_INSERTS;
  DWORD written = FormatMessageW(flags, nullptr, code, 0,
                                 reinterpret_cast<wchar_t*>(&buffer), 0, nullptr);
  std::wstring text;
  if (written && buffer) {
    text = buffer;
    LocalFree(buffer);
  } else {
    wchar_t fallback[64] = {};
    swprintf_s(fallback, L"Win32 error %lu", code);
    text = fallback;
  }
  while (!text.empty() && (text.back() == L'\r' || text.back() == L'\n')) {
    text.pop_back();
  }
  return text;
}

std::string Narrow(const std::wstring& value) {
  if (value.empty()) {
    return "";
  }
  int len = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
                                nullptr, 0, nullptr, nullptr);
  std::string out(static_cast<size_t>(len), '\0');
  WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
                      &out[0], len, nullptr, nullptr);
  return out;
}

std::wstring Widen(const std::string& value) {
  if (value.empty()) {
    return L"";
  }
  int len = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
                                nullptr, 0);
  std::wstring out(static_cast<size_t>(len), L'\0');
  MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()),
                      &out[0], len);
  return out;
}

std::wstring ModuleName(const std::wstring& path) {
  size_t slash = path.find_last_of(L"\\/");
  return slash == std::wstring::npos ? path : path.substr(slash + 1);
}

bool FileExists(const std::wstring& path) {
  DWORD attr = GetFileAttributesW(path.c_str());
  return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

std::wstring Utf8PathFromArg(const wchar_t* value) {
  return value ? std::wstring(value) : L"";
}

Launcher::Launcher(const std::wstring& configPath) : configPath_(configPath) {}

int Launcher::PrintUsage() const {
  std::wcout << kLauncherVersion << L"\n"
             << L"Usage:\n"
             << L"  CODOLLauncher.exe [--diagnostic] [--verbose] [--wait] "
                L"[--no-monitor]\n\n"
             << L"Flags:\n"
             << L"  --diagnostic  Print machine-readable launch state\n"
             << L"  --verbose     Write detailed module/state log lines\n"
             << L"  --wait        Wait for game process exit before exiting\n"
             << L"  --no-monitor  Disable module monitoring\n";
  return 0;
}

bool Launcher::LoadConfig() {
  if (configPath_.empty() || !FileExists(configPath_)) {
    return false;
  }

  wchar_t full[MAX_PATH] = {};
  GetFullPathNameW(configPath_.c_str(), MAX_PATH, full, nullptr);
  std::wstring dir = full;
  size_t slash = dir.find_last_of(L"\\/");
  dir = slash == std::wstring::npos ? L"." : dir.substr(0, slash);

  wchar_t value[2048] = {};
  std::wstring path;
  std::wstring wd;
  std::wstring args;

  if (GetPrivateProfileStringW(L"Game", L"Path", L"", value, 2048, configPath_.c_str())) {
    path = ExpandPath(value);
  }
  if (GetPrivateProfileStringW(L"Game", L"WorkingDirectory", L"", value, 2048,
                               configPath_.c_str())) {
    wd = ExpandPath(value);
  }
  if (GetPrivateProfileStringW(L"Launch", L"Arguments", L"", value, 2048,
                               configPath_.c_str())) {
    args = value;
  }
  if (GetPrivateProfileStringW(L"Monitor", L"Enabled", L"true", value, 32,
                               configPath_.c_str())) {
    monitor_ = (_wcsicmp(value, L"false") != 0) && (_wcsicmp(value, L"0") != 0);
  }
  if (GetPrivateProfileStringW(L"TCLS", L"Enabled", L"false", value, 32,
                               configPath_.c_str())) {
    tclsEnabled_ = (_wcsicmp(value, L"true") == 0) || (_wcsicmp(value, L"1") == 0);
  }

  gamePath_ = path;
  workingDirectory_ = wd;
  arguments_ = args;

  if (gamePath_.empty()) {
    gamePath_ = L"codoMP_client_shipRetail.exe";
  }
  if (!PathIsAbsoluteW(gamePath_.c_str())) {
    gamePath_ = dir + L"\\" + gamePath_;
  }
  if (workingDirectory_.empty()) {
    workingDirectory_ = dir;
  }
  return FileExists(gamePath_);
}

std::wstring Launcher::ExpandPath(const std::wstring& value) const {
  if (value.empty()) {
    return value;
  }
  if (value == L".") {
    wchar_t cwd[MAX_PATH] = {};
    GetCurrentDirectoryW(MAX_PATH, cwd);
    return cwd;
  }
  DWORD len = ExpandEnvironmentStringsW(value.c_str(), nullptr, 0);
  if (len > 0 && len < 32768) {
    std::wstring out(len, L'\0');
    ExpandEnvironmentStringsW(value.c_str(), &out[0], len);
    out.resize(len - 1);
    return out;
  }
  return value;
}

void Launcher::LogResult(const LaunchResult& result) const {
  std::wstring logName = L"CODOLLauncher\\logs\\CODOLLauncher_" + NowIso() + L".log";
  // Replace forbidden filename chars that NowIso may include.
  for (auto& ch : logName) {
    if (ch == L':' || ch == L'/') {
      ch = L'-';
    }
  }
  std::ofstream out(Narrow(logName), std::ios::out | std::ios::trunc);
  if (!out) {
    return;
  }
  auto line = [&](const std::wstring& text) {
    out << Narrow(NowIso()) << " " << Narrow(text) << "\n";
  };
  line(L"[Launcher] PID=" + std::to_wstring(result.launcherPid));
  line(L"[Launcher] BOOT_DEPTH=" + std::to_wstring(static_cast<int>(result.depth)));
  line(L"[Game] PID=" + std::to_wstring(result.gamePid));
  line(L"[Game] TID=" + std::to_wstring(result.mainThreadId));
  line(L"[Game] EXIT_CODE=" + std::to_wstring(result.exitCode));
  line(L"[Game] LAST_ERROR=" + std::to_wstring(result.lastError));
  line(L"[Modules] count=" + std::to_wstring(result.modules.size()));
  for (const auto& mod : result.modules) {
    std::wostringstream ss;
    ss << L"[Module] " << mod.path << L" base=0x" << std::hex << mod.base
       << L" size=0x" << mod.size;
    line(ss.str());
  }
  line(L"[KNOWN] TCLS_SHAREDMEMEMORY+GamePID mapping is created before resume "
       L"(enabled=" + (tclsEnabled_ ? L"true" : L"false") + L")");
  out.flush();
}

void Launcher::PrintDiagnostic(const LaunchResult& result) const {
  std::wcout << L"[Launcher]\n";
  std::wcout << L"PID=" << result.launcherPid << L"\n\n";

  std::wcout << L"[Game]\n";
  std::wcout << L"PID=" << result.gamePid << L"\n";
  std::wcout << L"TID=" << result.mainThreadId << L"\n\n";

  std::wcout << L"[Context]\n";
  std::wcout << L"TCLS=" << (tclsEnabled_ ? L"enabled" : L"disabled") << L"\n";
  if (tclsEnabled_) {
    std::wcout << L"Mapping=TCLS_SHAREDMEMEMORY+" << result.gamePid << L"\n";
  } else {
    std::wcout << L"Mapping=NONE\n";
  }
  std::wcout << L"WorkingDirectory=" << workingDirectory_ << L"\n\n";

  std::wcout << L"[Bootstrap]\n";
  bool exe = false;
  bool base = false;
  bool tenproxy = false;
  for (const auto& mod : result.modules) {
    std::wstring name = ModuleName(mod.path);
    if (_wcsicmp(name.c_str(), L"codoMP_client_shipRetail.exe") == 0) {
      exe = true;
    } else if (_wcsicmp(name.c_str(), L"codoMP_client_shipRetailBase.dll") == 0) {
      base = true;
    } else if (_wcsicmp(name.c_str(), L"TenProxy.dll") == 0) {
      tenproxy = true;
    } else if (_wcsicmp(name.c_str(), L"libcef.dll") == 0) {
      std::wcout << L"libcef=YES\n";
    }
  }
  std::wcout << L"EXE Entry=" << (exe ? L"YES" : L"NO") << L"\n";
  std::wcout << L"Base ordinal1=" << (base ? L"YES" : L"NO") << L"\n";
  std::wcout << L"VM boundary=UNKNOWN (no debugger instrumentation)\n";
  std::wcout << L"BOOT_DEPTH=" << static_cast<int>(result.depth) << L"\n\n";

  std::wcout << L"[Modules]\n";
  std::wcout << L"Base.dll=" << (base ? L"YES" : L"NO") << L"\n";
  std::wcout << L"TenProxy.dll=" << (tenproxy ? L"YES" : L"NO") << L"\n";
  for (const auto& mod : result.modules) {
    std::wcout << L"Module=" << mod.path << L" 0x" << std::hex << mod.base
               << L" 0x" << mod.size << L"\n";
  }

  std::wcout << L"\n[Result]\n";
  std::wcout << L"BOOT_DEPTH=" << static_cast<int>(result.depth) << L"\n";
  std::wcout << L"EXIT_CODE=" << result.exitCode << L"\n";
  std::wcout << L"LAST_ERROR=" << result.lastError << L"\n";
}

int Launcher::Run(int argc, wchar_t** argv) {
  for (int i = 1; i < argc; ++i) {
    std::wstring arg = argv[i];
    if (arg == L"--diagnostic") {
      diagnostic_ = true;
    } else if (arg == L"--verbose") {
      verbose_ = true;
    } else if (arg == L"--wait") {
      wait_ = true;
    } else if (arg == L"--no-monitor") {
      monitor_ = false;
    } else if (arg == L"--help" || arg == L"-h" || arg == L"/?") {
      return PrintUsage();
    } else {
      std::wcerr << L"Unknown argument: " << arg << L"\n";
      return PrintUsage();
    }
  }

  if (!LoadConfig()) {
    std::wcerr << L"Configuration or game not found. Expected resources:\n"
               << L"  CODOLLauncher.ini\n"
               << L"  codoMP_client_shipRetail.exe\n";
    return 2;
  }

  LaunchResult result;
  result.launcherPid = GetCurrentProcessId();
  TCLSCompatibility tcls;
  BootstrapMonitor monitor;
  LauncherContext ctx;

  if (tclsEnabled_) {
    tcls.SetEnabled(true);
  }

  // Stage 0-3: validate path and working directory.
  if (!SetCurrentDirectoryW(workingDirectory_.c_str())) {
    result.lastError = GetLastError();
    std::wcerr << L"SetCurrentDirectory failed: " << GetLastErrorText(result.lastError) << L"\n";
    return 3;
  }

  GameProcess game(gamePath_, workingDirectory_, arguments_, CREATE_SUSPENDED);
  if (!game.Create()) {
    result.lastError = game.LastError();
    std::wcerr << L"CreateProcessW failed: " << GetLastErrorText(result.lastError) << L"\n";
    return 4;
  }

  result.gamePid = game.Pid();
  result.mainThreadId = game.ThreadId();
  result.process = game.ProcessHandle();
  result.thread = game.ThreadHandle();

  ctx.launcherPid = result.launcherPid;
  ctx.gamePid = result.gamePid;
  ctx.gamePath = gamePath_;
  ctx.workingDirectory = workingDirectory_;
  ctx.commandLine = gamePath_;
  if (!arguments_.empty()) {
    ctx.commandLine += L" ";
    ctx.commandLine += arguments_;
  }

  // Stage S6: create the only launcher IPC that historical evidence confirms.
  if (tclsEnabled_) {
    if (tcls.Prepare(result.gamePid)) {
      ctx.tclsMappingCreated = true;
      ctx.mappingName = tcls.MappingName();
      ctx.sharedMemory = tcls.MappingHandle();
    } else {
      result.lastError = GetLastError();
    }
  }

  // Stage S8: resume the game primary thread.
  if (!game.Resume()) {
    result.lastError = game.LastError();
    std::wcerr << L"ResumeThread failed: " << GetLastErrorText(result.lastError) << L"\n";
    if (result.process) {
      TerminateProcess(result.process, 0);
    }
    return 5;
  }

  if (monitor_) {
    monitor.Attach(result.gamePid);
  }

  // Poll module load for a short window; if --wait is set, wait for exit.
  DWORD ticks = 0;
  DWORD exit = 0;
  bool exited = true;
  for (;;) {
    if (monitor_) {
      monitor.SnapshotModules();
    }
    if (WaitForSingleObject(game.ProcessHandle(), 250) == WAIT_OBJECT_0) {
      GetExitCodeProcess(game.ProcessHandle(), &exit);
      result.exitCode = exit;
      break;
    }
    ticks += 250;
    if (!wait_ && ticks > 6000) {
      exited = false;
      break;
    }
  }

  if (monitor_) {
    monitor.SnapshotModules();
    result.modules = monitor.Modules();
    result.depth = monitor.ComputeDepth();
  } else {
    result.modules.clear();
    result.depth = BootDepth::ProcessNotCreated;
  }

  LogResult(result);

  if (diagnostic_) {
    PrintDiagnostic(result);
  } else {
    std::wcout << L"BOOT_DEPTH = " << static_cast<int>(result.depth) << L"\n";
    std::wcout << L"GamePID = " << result.gamePid << L"\n";
    if (exited) {
      std::wcout << L"GameExited = " << result.exitCode << L"\n";
    }
  }

  if (monitor_) {
    monitor.Detach();
  }
  return tclsEnabled_ && !ctx.tclsMappingCreated ? 6 : 0;
}

}  // namespace codol
