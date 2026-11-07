#pragma once

#include <windows.h>

#include <vector>

#include "Launcher.h"

namespace codol {

class BootstrapMonitor {
 public:
  void Attach(DWORD pid);
  void Detach();
  bool IsAttached() const { return process_ != nullptr; }

  // Returns a snapshot of modules the game has loaded. Depth is inferred
  // from confirmed module load evidence only.
  bool SnapshotModules();
  const std::vector<ModuleSnapshot>& Modules() const { return modules_; }
  BootDepth ComputeDepth() const;
  bool HasModule(const std::wstring& name) const;

 private:
  HANDLE process_ = nullptr;
  DWORD pid_ = 0;
  std::vector<ModuleSnapshot> modules_;
};

}  // namespace codol
