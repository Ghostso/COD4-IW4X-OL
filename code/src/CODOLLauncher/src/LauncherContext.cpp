#include "LauncherContext.h"

namespace codol {

void LauncherContext::ClearHandles() {
  // Only null the bookkeeping fields. Ownership of native handles stays in
  // the callers (GameProcess/TCLSCompatibility).
  sharedMemory = nullptr;
  mutex = nullptr;
  event = nullptr;
}

}  // namespace codol
