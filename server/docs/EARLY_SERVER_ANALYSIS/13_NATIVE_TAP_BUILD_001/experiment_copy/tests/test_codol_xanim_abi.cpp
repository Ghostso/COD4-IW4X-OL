#include "q_shared.h"
#include "xassets/xanims.h"
#include <cstddef>
#include <cstdio>

/* Offsets consumed by retained IW3 assembly, independently of CoDOL's source
 * header. XAnimFillInSyncNodes_r reads loop at 0x10; XAnimCalcDeltaTree reads
 * delta at 0x11; XAnimCalc reads the first bone count at 0x12; DB_Load and
 * XAnimResetAnimMap_r read the total bone count at 0x1b. */
static_assert(sizeof(XAnimParts)==88,"IW3 animation header size");
static_assert(offsetof(XAnimParts,bLoop)==0x10,"loop flag");
static_assert(offsetof(XAnimParts,bDelta)==0x11,"delta flag");
static_assert(offsetof(XAnimParts,boneCount)==0x12,"first bone count");
static_assert(offsetof(XAnimParts,boneCount)+sizeof(((XAnimParts *)0)->boneCount)-1==0x1b,"total bone count");
static_assert(offsetof(XAnimParts,notifyCount)==0x1c,"notify count");
static_assert(offsetof(XAnimParts,assetType)==0x1d,"asset type");
static_assert(offsetof(XAnimParts,randomDataShortCount)==0x20,"random short count");
static_assert(offsetof(XAnimParts,names)==0x30,"bone handles");
static_assert(offsetof(XAnimParts,notify)==0x50,"notifies");
static_assert(offsetof(XAnimParts,deltaPart)==0x54,"delta parts");
static_assert(sizeof(XAnimDeltaPart)==8,"IW3 has two delta tracks");
static_assert(sizeof(XAnimNotifyInfo)==8,"notify record stride");
int main() { std::puts("PASS: native XAnim ABI matches retained IW3 consumers"); }
