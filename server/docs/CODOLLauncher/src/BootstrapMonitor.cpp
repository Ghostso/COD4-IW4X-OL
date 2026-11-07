#include "BootstrapMonitor.h"
#include "Launcher.h"

#include <psapi.h>

#include <algorithm>
#include <set>

namespace codol {

void BootstrapMonitor::Attach(DWORD pid) {
  Detach();
  pid_ = pid;
  process_ = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
  SnapshotModules();
}

void BootstrapMonitor::Detach() {
  if (process_) {
    CloseHandle(process_);
    process_ = nullptr;
  }
  pid_ = 0;
  modules_.clear();
}

bool BootstrapMonitor::SnapshotModules() {
  modules_.clear();
  if (!process_) {
    return false;
  }

  HMODULE handles[1024];
  DWORD needed = 0;
  if (!EnumProcessModulesEx(process_, handles, sizeof(handles), &needed,
                            LIST_MODULES_ALL)) {
    return false;
  }
  size_t count = needed / sizeof(HMODULE);
  count = std::min<size_t>(count, _countof(handles));

  std::set<std::wstring> seen;
  for (size_t i = 0; i < count; ++i) {
    wchar_t path[MAX_PATH] = {};
    if (!GetModuleFileNameExW(process_, handles[i], path, MAX_PATH)) {
      continue;
    }
    if (!seen.insert(path).second) {
      continue;
    }

    MODULEINFO info = {};
    if (GetModuleInformation(process_, handles[i], &info, sizeof(info))) {
      ModuleSnapshot snap;
      snap.path = path;
      snap.base = reinterpret_cast<uintptr_t>(info.lpBaseOfDll);
      snap.size = info.SizeOfImage;
      modules_.push_back(snap);
    }
  }
  return !modules_.empty();
}

bool BootstrapMonitor::HasModule(const std::wstring& name) const {
  std::wstring lower = name;
  std::transform(lower.begin(), lower.end(), lower.begin(), ::towlower);
  for (const auto& mod : modules_) {
    std::wstring current = ModuleName(mod.path);
    std::transform(current.begin(), current.end(), current.begin(), ::towlower);
    if (current == lower) {
      return true;
    }
  }
  return false;
}

BootDepth BootstrapMonitor::ComputeDepth() const {
  if (!HasModule(L"codoMP_client_shipRetail.exe")) {
    return BootDepth::ProcessNotCreated;
  }

  if (!HasModule(L"codoMP_client_shipRetailBase.dll")) {
    return BootDepth::ExeEntry;
  }

  if (HasModule(L"TenProxy.dll") || HasModule(L"TenRpcs.dll") ||
      HasModule(L"GameRpcs.dll") || HasModule(L"TCJ.dll")) {
    return BootDepth::TenProxyProjectDll;
  }

  if (HasModule(L"libcef.dll") || HasModule(L"BugTrace.dll") ||
      HasModule(L"GbSpy.dll")) {
    return BootDepth::NewBaseExeBootstrap;
  }

  return BootDepth::BaseOrdinal1;
}

}  // namespace codol
