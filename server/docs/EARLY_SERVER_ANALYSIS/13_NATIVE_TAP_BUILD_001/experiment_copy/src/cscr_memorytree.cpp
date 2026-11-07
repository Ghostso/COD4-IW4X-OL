#include "q_shared.h"
#include "qcommon_io.h"
#include "sys_thread.h"
#include "misc.h"
#include "cscr_stringlist.h"
#include "sys_main.h"

#define MEMORY_NODE_BITS 16
#define MEMORY_NODE_COUNT (1 << MEMORY_NODE_BITS)
#define MEMORY_NODE_SIZE 16

const char *mt_type_names[ ] =
{
  "empty",
  "thread",
  "vector",
  "notetrack",
  "anim tree",
  "small anim tree",
  "external",
  "temp",
  "surface",
  "anim part",
  "model part",
  "model part map",
  "duplicate parts",
  "model list",
  "script parse",
  "script string",
  "class",
  "tag info",
  "animscripted",
  "config string",
  "debugger string",
  "vehicle",
  "generic"
  };

class MemoryTree
{
public:
  byte *MT_Alloc(int numBytes, int type);
  void MT_FreeIndex(unsigned int nodeNum, int numBytes);
  void MT_Free(void *p, int numBytes);
  unsigned int MT_AllocIndex(int numBytes, int type);
  void MT_DumpTree( );
  void MT_Init( );
  bool MT_Realloc(int oldNumBytes, int newNumbytes);
  byte* MT_GetRefByIndex(int index);
  int MT_GetIndexByRef(byte* p);

private:
  const char *MT_NodeInfoString(unsigned int nodeNum);
  int MT_GetSubTreeSize(int nodeNum);
  void MT_RebuildFreeTree(const char *why);
  bool MT_FreeTreeLooksSane(int size, int node);
  void MT_Error(const char *funcName, int numBytes);
  int MT_GetSize(int numBytes);
  int MT_GetScore(int num);
  bool MT_RemoveHeadMemoryNode(int size);
  bool MT_AddMemoryNode(int newNode, int size);
  bool MT_RemoveMemoryNode(int oldNode, int size);
  void MT_InitBits( );
public:
  bool MT_IsAllocatedIndex(unsigned int nodeNum);
private:
  int Scr_GetStringUsage( );

  struct MemoryNode
  {
    uint16_t prev;
    uint16_t next;
    byte padding[MEMORY_NODE_SIZE - 4];
  };

  struct __align(128) scrMemTreeGlob_t
  {
    MemoryNode nodes[MEMORY_NODE_COUNT];
    char leftBits[256];
    char numBits[256];
    char logBits[256];
    uint16_t head[MEMORY_NODE_BITS +1];
    int totalAlloc;
    int totalAllocBuckets;
    int avgAlloc;
    int avgAllocBytes;
  };

  struct scrMemTreeDebugGlob_t
  {
    char mt_usage[MEMORY_NODE_COUNT];
    char mt_usage_size[MEMORY_NODE_COUNT];
  };

  scrMemTreeGlob_t gScrMemTreeGlob;
  scrMemTreeDebugGlob_t gScrMemTreeDebugGlob;


};



const char* MemoryTree::MT_NodeInfoString(unsigned int nodeNum)
{
  int type;
  char string[920];

  type = gScrMemTreeDebugGlob.mt_usage[nodeNum];
  if ( gScrMemTreeDebugGlob.mt_usage[nodeNum] )
  {
    Q_strncpyz(string, SL_ConvertToString(nodeNum), sizeof(string));
    return va("%s: '%s' (%d)", mt_type_names[type], string, gScrMemTreeDebugGlob.mt_usage_size[nodeNum]);
  }
  return "<FREE>";
}


int MemoryTree::MT_GetSubTreeSize(int nodeNum)
{
  int s;

  if ( nodeNum )
  {
    s = MT_GetSubTreeSize(gScrMemTreeGlob.nodes[nodeNum].prev);
    return s + MT_GetSubTreeSize(gScrMemTreeGlob.nodes[nodeNum].next) + 1;
  }
  return 0;
}


void MemoryTree::MT_DumpTree( )
{
  int subTreeSize;
  unsigned int nodeNum;
  int size;
  int totalAllocBuckets;
  int totalAlloc;
  int mt_type_usage[ARRAY_COUNT(mt_type_names)];
  unsigned int type;
  int totalBuckets;

  memset(&mt_type_usage, 0, sizeof(mt_type_usage));
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "********************************\n");
  totalAlloc = 0;
  totalAllocBuckets = 0;
  for ( nodeNum = 0; nodeNum < MEMORY_NODE_COUNT; ++nodeNum )
  {
    type = gScrMemTreeDebugGlob.mt_usage[nodeNum];
    if ( type )
    {
      Com_Printf(CON_CHANNEL_PARSERSCRIPT, "%s\n", MT_NodeInfoString(nodeNum));
      ++totalAlloc;
      totalAllocBuckets += 1 << gScrMemTreeDebugGlob.mt_usage_size[nodeNum];
      mt_type_usage[type] += 1 << gScrMemTreeDebugGlob.mt_usage_size[nodeNum];
    }
  }

  assert(gScrMemTreeGlob.totalAlloc == totalAlloc);
  assert(gScrMemTreeGlob.totalAllocBuckets == totalAllocBuckets);

  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "********************************\n");
  totalBuckets = gScrMemTreeGlob.totalAllocBuckets;
  for ( size = 0; size <= MEMORY_NODE_BITS; ++size )
  {
    subTreeSize = MT_GetSubTreeSize(gScrMemTreeGlob.head[size]);
    totalBuckets += subTreeSize * (1 << size);
    Com_Printf(CON_CHANNEL_PARSERSCRIPT, "%d subtree has %d * %d = %d free buckets\n", size, subTreeSize, 1 << size, subTreeSize * (1 << size));
  }
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "********************************\n");
  for ( type = 1; type < ARRAY_COUNT(mt_type_names); ++type )
  {
    Com_Printf(CON_CHANNEL_PARSERSCRIPT, "'%s' allocated: %d\n", mt_type_names[type], mt_type_usage[type]);
  }
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "********************************\n");
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "total memory alloc buckets: %d (%d instances)\n", gScrMemTreeGlob.totalAllocBuckets, gScrMemTreeGlob.totalAlloc);
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "total memory free buckets: %d\n", MEMORY_NODE_COUNT -1 - gScrMemTreeGlob.totalAllocBuckets);
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "********************************\n");
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "avg alloc: %f\n", (float)gScrMemTreeGlob.avgAllocBytes / (float)gScrMemTreeGlob.avgAlloc);

  assert(totalBuckets == MEMORY_NODE_COUNT - 1);
}


void MemoryTree::MT_Error(const char *funcName, int numBytes)
{
  MT_DumpTree();
  Com_Printf(CON_CHANNEL_PARSERSCRIPT, "%s: failed memory allocation of %d bytes for script usage\n", funcName, numBytes);
  /*if ( Sys_IsServerThread() )
  {
    Scr_TerminalError("failed memory allocation for script usage");
  }
  else*/
  {
    Com_Error(ERR_DROP, "%s: failed allocation of %d bytes for script usage", funcName, numBytes);
  }
}

int MemoryTree::MT_GetSize(int numBytes)
{
  int numBuckets;

  assert (numBytes > 0);
  if ( numBytes >= MEMORY_NODE_COUNT )
  {
    MT_Error("MT_GetSize: max allocation exceeded", numBytes);
    return 0;
  }
  numBuckets = (numBytes + MEMORY_NODE_SIZE -1) / MEMORY_NODE_SIZE -1;
  if ( numBuckets > 255 )
  {
      return gScrMemTreeGlob.logBits[numBuckets >> 8] + 8;
  }
  return gScrMemTreeGlob.logBits[numBuckets];
}


int MemoryTree::MT_GetScore(int num)
{
  char bits;

  assert(num != 0);

  union MTnum_t
  {
    int i;
    uint8_t b[4];
  };

  MTnum_t mtnum;

  mtnum.i = MEMORY_NODE_COUNT - num;
  assert(mtnum.i != 0);

  bits = gScrMemTreeGlob.leftBits[mtnum.b[0]];
  if ( !mtnum.b[0] )
  {
    bits += gScrMemTreeGlob.leftBits[mtnum.b[1]];
  }
  return mtnum.i - (gScrMemTreeGlob.numBits[mtnum.b[1]] + gScrMemTreeGlob.numBits[mtnum.b[0]]) + (1 << bits);
}



/* The free tree is a binary trie over the 16-bit node number, so a walk from
 * a head to a leaf visits at most MEMORY_NODE_BITS + 1 nodes. Anything longer
 * is a cycle in damaged links: stop and let the caller rebuild the tree instead
 * of spinning forever (VPS 2026-09-27, zm_prototype_sh load: the main thread
 * sat at 100% CPU in this function under SV_SetConfigstring). */
#define MT_MAX_TREE_WALK (2 * MEMORY_NODE_BITS + 4)

bool MemoryTree::MT_RemoveHeadMemoryNode(int size)
{
  MemoryNode tempNodeValue;
  int oldNode;
  MemoryNode oldNodeValue;
  uint16_t *parentNode;
  int prevScore;
  int nextScore;
  int currentNode;
  int steps = 0;

  assert(size >= 0 && size <= MEMORY_NODE_BITS);

  parentNode = &gScrMemTreeGlob.head[size];
  currentNode = *parentNode;
  oldNodeValue = gScrMemTreeGlob.nodes[*parentNode];

  while ( 1 )
  {
    if ( ++steps > MT_MAX_TREE_WALK )
    {
      return false;
    }
    /* A damaged free-tree link used to spin the server forever here.  This
     * was observed during a live CoDOL class spawn: node 0x4800 had its next
     * link set to itself and the main thread never returned to networking.
     * A free node cannot validly be its own child.  Cut only that impossible
     * edge; the node being removed remains owned by this allocation. */
    if ( oldNodeValue.prev == currentNode )
      oldNodeValue.prev = 0;
    if ( oldNodeValue.next == currentNode )
      oldNodeValue.next = 0;
    if(!oldNodeValue.prev)
    {
        oldNode = oldNodeValue.next;
        *parentNode = oldNodeValue.next;
        if ( !oldNode )
        {
            break;
        }
        parentNode = &gScrMemTreeGlob.nodes[oldNode].next;
    }else{
        if ( oldNodeValue.next )
        {
            prevScore = MT_GetScore(oldNodeValue.prev);
            nextScore = MT_GetScore(oldNodeValue.next);

            assert(prevScore != nextScore);

            if ( prevScore >= nextScore )
            {
                oldNode = oldNodeValue.prev;
                *parentNode = oldNode;
                parentNode = &gScrMemTreeGlob.nodes[oldNode].prev;
            }
            else
            {
                oldNode = oldNodeValue.next;
                *parentNode = oldNode;
                parentNode = &gScrMemTreeGlob.nodes[oldNode].next;
            }
        }
        else
        {
            oldNode = oldNodeValue.prev;
            *parentNode = oldNode;
            parentNode = &gScrMemTreeGlob.nodes[oldNode].prev;
        }
    }
    assert(oldNode != 0);

    tempNodeValue = oldNodeValue;
    oldNodeValue = gScrMemTreeGlob.nodes[oldNode];
    gScrMemTreeGlob.nodes[oldNode] = tempNodeValue;
    currentNode = oldNode;
  }
  return true;
}


bool MemoryTree::MT_AddMemoryNode(int newNode, int size)
{
  int node;
  int nodeNum;
  int newScore;
  uint16_t *parentNode;
  int level;
  int score;
  int steps = 0;

  assert(size >= 0 && size <= MEMORY_NODE_BITS);

  parentNode = &gScrMemTreeGlob.head[size];
  node = gScrMemTreeGlob.head[size];
  if ( gScrMemTreeGlob.head[size] )
  {
    newScore = MT_GetScore(newNode);
    nodeNum = 0;
    level = MEMORY_NODE_COUNT;
    do
    {
        assert(newNode != node);
        score = MT_GetScore(node);

        assert(score != newScore);

        if ( score < newScore )
        {
            while ( 1 )
            {
                if ( ++steps > MT_MAX_TREE_WALK )
                {
                    return false;
                }
                assert(node == *parentNode);
                assert(node != newNode);

                *parentNode = newNode;
                gScrMemTreeGlob.nodes[newNode] = gScrMemTreeGlob.nodes[node];
                if ( !node )
                {
                    break;
                }
                level >>= 1;

                assert(node != nodeNum);

                if ( node >= nodeNum )
                {
                    parentNode = &gScrMemTreeGlob.nodes[newNode].next;
                    nodeNum += level;
                }
                else
                {
                    parentNode = &gScrMemTreeGlob.nodes[newNode].prev;
                    nodeNum -= level;
                }
                newNode = node;
                node = *parentNode;
            }
            return true;
        }
        if ( ++steps > MT_MAX_TREE_WALK )
        {
            return false;
        }
        level >>= 1;

        assert(newNode != nodeNum);

        if ( newNode >= nodeNum )
        {
            parentNode = &gScrMemTreeGlob.nodes[node].next;
            nodeNum += level;
        }
        else
        {
            parentNode = &gScrMemTreeGlob.nodes[node].prev;
            nodeNum -= level;
        }
        node = *parentNode;
    }while(node);
  }
  *parentNode = newNode;
  gScrMemTreeGlob.nodes[newNode].prev = 0;
  gScrMemTreeGlob.nodes[newNode].next = 0;
  return true;
}



bool MemoryTree::MT_RemoveMemoryNode(int oldNode, int size)
{
  MemoryNode tempNodeValue;
  int node;
  MemoryNode oldNodeValue;
  int nodeNum;
  uint16_t *parentNode;
  int prevScore;
  int nextScore;
  int level;

  assert(size >= 0 && size <= MEMORY_NODE_BITS);

  int steps = 0;

  nodeNum = 0;
  level = MEMORY_NODE_COUNT;
  parentNode = &gScrMemTreeGlob.head[size];
  for ( node = *parentNode; node; node = *parentNode )
  {
    if ( ++steps > MT_MAX_TREE_WALK )
    {
      /* Damaged links: report "not found" so the caller stops merging; the
       * next allocation checks the tree and rebuilds it. */
      return false;
    }
    if ( oldNode == node )
    {
      oldNodeValue = gScrMemTreeGlob.nodes[oldNode];

      while ( 1 )
      {
        if ( ++steps > 2 * MT_MAX_TREE_WALK )
        {
          return true;
        }
        if ( oldNodeValue.prev )
        {
          if ( oldNodeValue.next )
          {
            prevScore = MT_GetScore(oldNodeValue.prev);
            nextScore = MT_GetScore(oldNodeValue.next);
            
            assert(prevScore != nextScore);

            if ( prevScore >= nextScore )
            {
              oldNode = oldNodeValue.prev;
              *parentNode = oldNodeValue.prev;
              parentNode = &gScrMemTreeGlob.nodes[oldNodeValue.prev].prev;
            }
            else
            {
              oldNode = oldNodeValue.next;
              *parentNode = oldNodeValue.next;
              parentNode = &gScrMemTreeGlob.nodes[oldNodeValue.next].next;
            }
          }
          else
          {
            oldNode = oldNodeValue.prev;
            *parentNode = oldNodeValue.prev;
            parentNode = &gScrMemTreeGlob.nodes[oldNodeValue.prev].prev;
          }
        }
        else
        {
          oldNode = oldNodeValue.next;
          *parentNode = oldNodeValue.next;
          if ( !oldNodeValue.next )
          {
            return true;
          }
          parentNode = &gScrMemTreeGlob.nodes[oldNodeValue.next].next;
        }

        assert(oldNode != 0);

        tempNodeValue = oldNodeValue;
        oldNodeValue = gScrMemTreeGlob.nodes[oldNode];
        gScrMemTreeGlob.nodes[oldNode] = tempNodeValue;
      }
    }
    if ( oldNode == nodeNum )
    {
      return false;
    }
    level >>= 1;
    if ( oldNode >= nodeNum )
    {
      parentNode = &gScrMemTreeGlob.nodes[node].next;
      nodeNum += level;
    }
    else
    {
      parentNode = &gScrMemTreeGlob.nodes[node].prev;
      nodeNum -= level;
    }
  }
  return false;
}


unsigned int MemoryTree::MT_AllocIndex(int numBytes, int type)
{
  int nodeNum;
  int size;
  signed int newSize;

  int attempts = 0;

  size = MT_GetSize(numBytes);
  assert(size >= 0 && size <= MEMORY_NODE_BITS);

  Sys_EnterCriticalSection(CRITSECT_MEMORY_TREE);
retry:
  for ( newSize = size; ; ++newSize )
  {
    if ( newSize > MEMORY_NODE_BITS )
    {
      Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);
      MT_Error("MT_AllocIndex", numBytes);
      return 0;
    }
    nodeNum = gScrMemTreeGlob.head[newSize];
    if ( gScrMemTreeGlob.head[newSize] )
    {
      break;
    }
  }
  /* A head that is not a free, correctly aligned block, or a walk that does
   * not terminate, means the free links were overwritten -- a script string
   * released after it was freed decrements its refCount, which is the free
   * node's prev link. The allocated blocks are intact and fully described by
   * mt_usage/mt_usage_size, so rebuild the free tree from them and retry. */
  if ( !MT_FreeTreeLooksSane(newSize, nodeNum) || !MT_RemoveHeadMemoryNode(newSize) )
  {
    if ( ++attempts > 2 )
    {
      Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);
      Com_Error(ERR_FATAL, "MT_AllocIndex: the script memory free tree is damaged beyond repair");
      return 0;
    }
    MT_RebuildFreeTree("MT_AllocIndex");
    goto retry;
  }
  while ( newSize != size )
  {
    --newSize;
    if ( !MT_AddMemoryNode(nodeNum + (1 << newSize), newSize) )
    {
      MT_RebuildFreeTree("MT_AllocIndex split");
    }
  }
  assert(nodeNum >= 0 && nodeNum < MEMORY_NODE_COUNT);

  ++gScrMemTreeGlob.totalAlloc;
  ++gScrMemTreeGlob.avgAlloc;
  gScrMemTreeGlob.avgAllocBytes += numBytes;
  gScrMemTreeGlob.totalAllocBuckets += 1 << size;

  assert(type != 0);
  assertx( !gScrMemTreeDebugGlob.mt_usage[nodeNum], "MT_NodeInfoString( nodeNum ) = %s", MT_NodeInfoString(nodeNum));
  assertx( !gScrMemTreeDebugGlob.mt_usage_size[nodeNum], "MT_NodeInfoString( nodeNum ) = %s", MT_NodeInfoString(nodeNum));

  gScrMemTreeDebugGlob.mt_usage[nodeNum] = type;
  gScrMemTreeDebugGlob.mt_usage_size[nodeNum] = size;
  Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);

  return nodeNum;
}




void MemoryTree::MT_InitBits( )
{
  char bits;
  int temp;
  int i;

  for ( i = 0; i < 256; ++i )
  {
    bits = 0;
    for ( temp = i; temp; temp >>= 1 )
    {
      if ( temp & 1 )
      {
        ++bits;
      }
    }
    gScrMemTreeGlob.numBits[i] = bits;
    for ( bits = 8; i & ((1 << bits) - 1); --bits )
    {
      ;
    }
    gScrMemTreeGlob.leftBits[i] = bits;
    bits = 0;
    for ( temp = i; temp; temp >>= 1 )
    {
      ++bits;
    }
    gScrMemTreeGlob.logBits[i] = bits;
  }
}

void MemoryTree::MT_Init( )
{
  int i;

  Sys_EnterCriticalSection(CRITSECT_MEMORY_TREE);
  MT_InitBits();
  for ( i = 0; i <= MEMORY_NODE_BITS; ++i )
  {
    gScrMemTreeGlob.head[i] = 0;
  }
  gScrMemTreeGlob.nodes[0].prev = 0;
  gScrMemTreeGlob.nodes[0].next = 0;
  for ( i = 0; i < MEMORY_NODE_BITS; ++i )
  {
    MT_AddMemoryNode(1 << i, i);
  }
  gScrMemTreeGlob.totalAlloc = 0;
  gScrMemTreeGlob.totalAllocBuckets = 0;
  memset(gScrMemTreeDebugGlob.mt_usage, 0, MEMORY_NODE_COUNT);
  memset(gScrMemTreeDebugGlob.mt_usage_size, 0, MEMORY_NODE_COUNT);
  Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);
}


int MemoryTree::Scr_GetStringUsage( )
{
  return gScrMemTreeGlob.totalAllocBuckets;
}


void MemoryTree::MT_FreeIndex(unsigned int nodeNum, int numBytes)
{
  int size;
  int lowBit;

  size = MT_GetSize(numBytes);

  assert(size >= 0 && size <= MEMORY_NODE_BITS);
  assert(nodeNum > 0 && nodeNum < MEMORY_NODE_COUNT);

  Sys_EnterCriticalSection(CRITSECT_MEMORY_TREE);
  if ( !gScrMemTreeDebugGlob.mt_usage[nodeNum] || gScrMemTreeDebugGlob.mt_usage_size[nodeNum] != size )
  {
    /* Freeing a block that is not allocated (or with the wrong size) would
     * link it into the free tree twice. Refuse and say who asked. */
    static int reports;
    int usage = gScrMemTreeDebugGlob.mt_usage[nodeNum];
    int usageSize = gScrMemTreeDebugGlob.mt_usage_size[nodeNum];
    Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);
    if ( reports < 16 )
    {
      ++reports;
      Com_PrintError(CON_CHANNEL_PARSERSCRIPT, "MT_FreeIndex: node %u (%d bytes, size %d) is %s (usage %d, size %d); ignoring this free\n",
                     nodeNum, numBytes, size, usage ? "allocated with another size" : "already free", usage, usageSize);
      Sys_PrintBacktrace();
    }
    return;
  }
  --gScrMemTreeGlob.totalAlloc;
  gScrMemTreeGlob.totalAllocBuckets -= 1 << size;

  assert(gScrMemTreeDebugGlob.mt_usage[nodeNum]);
  assertx(gScrMemTreeDebugGlob.mt_usage_size[nodeNum] == size, "(MT_NodeInfoString( nodeNum )) = %s", MT_NodeInfoString(nodeNum));

  gScrMemTreeDebugGlob.mt_usage[nodeNum] = 0;
  gScrMemTreeDebugGlob.mt_usage_size[nodeNum] = 0;
  while ( 1 )
  {
    assert(size <= MEMORY_NODE_BITS);

    lowBit = 1 << size;

    assert(nodeNum == (nodeNum & ~(lowBit - 1)));

    if ( size == MEMORY_NODE_BITS || !MT_RemoveMemoryNode(lowBit ^ nodeNum, size) )
    {
      break;
    }
    nodeNum &= ~lowBit;
    ++size;
  }
  if ( !MT_AddMemoryNode(nodeNum, size) )
  {
    MT_RebuildFreeTree("MT_FreeIndex");
  }
  Sys_LeaveCriticalSection(CRITSECT_MEMORY_TREE);
}

bool MemoryTree::MT_IsAllocatedIndex(unsigned int nodeNum)
{
  return nodeNum > 0 && nodeNum < MEMORY_NODE_COUNT && gScrMemTreeDebugGlob.mt_usage[nodeNum] != 0;
}

/* A head node must be free (not in mt_usage) and aligned to its block size. */
bool MemoryTree::MT_FreeTreeLooksSane(int size, int node)
{
  if ( node <= 0 || node >= MEMORY_NODE_COUNT )
  {
    return false;
  }
  if ( node & ((1 << size) - 1) )
  {
    return false;
  }
  return gScrMemTreeDebugGlob.mt_usage[node] == 0;
}

/* Rebuild every free list from the allocation map. Allocated blocks are
 * [n, n + 2^mt_usage_size[n]) for each n with mt_usage[n] != 0; node 0 is
 * never handed out. Each free run is split into the largest aligned
 * power-of-two blocks, which is the buddy-merged state MT_FreeIndex
 * maintains. Called with CRITSECT_MEMORY_TREE held. */
void MemoryTree::MT_RebuildFreeTree(const char *why)
{
  static byte used[MEMORY_NODE_COUNT];
  static int rebuilds;
  int node, size, end, blocks = 0, freeBuckets = 0;

  memset(used, 0, sizeof(used));
  used[0] = 1;
  for ( node = 1; node < MEMORY_NODE_COUNT; ++node )
  {
    if ( gScrMemTreeDebugGlob.mt_usage[node] )
    {
      end = node + (1 << gScrMemTreeDebugGlob.mt_usage_size[node]);
      if ( end > MEMORY_NODE_COUNT )
      {
        end = MEMORY_NODE_COUNT;
      }
      memset(&used[node], 1, end - node);
    }
  }
  for ( size = 0; size <= MEMORY_NODE_BITS; ++size )
  {
    gScrMemTreeGlob.head[size] = 0;
  }
  gScrMemTreeGlob.nodes[0].prev = 0;
  gScrMemTreeGlob.nodes[0].next = 0;
  node = 1;
  while ( node < MEMORY_NODE_COUNT )
  {
    if ( used[node] )
    {
      ++node;
      continue;
    }
    for ( size = MEMORY_NODE_BITS - 1; size > 0; --size )
    {
      int span = 1 << size;
      if ( (node & (span - 1)) == 0 && node + span <= MEMORY_NODE_COUNT &&
           !memchr(&used[node], 1, span) )
      {
        break;
      }
    }
    gScrMemTreeGlob.nodes[node].prev = 0;
    gScrMemTreeGlob.nodes[node].next = 0;
    MT_AddMemoryNode(node, size);
    freeBuckets += 1 << size;
    ++blocks;
    node += 1 << size;
  }
  if ( rebuilds < 16 )
  {
    ++rebuilds;
    Com_PrintError(CON_CHANNEL_PARSERSCRIPT, "%s: the script memory free tree was damaged (a script string or object used after it was freed); "
                   "rebuilt it from the allocation map: %d free blocks, %d free buckets, %d allocated buckets\n",
                   why, blocks, freeBuckets, gScrMemTreeGlob.totalAllocBuckets);
    Sys_PrintBacktrace();
  }
}

byte* MemoryTree::MT_Alloc(int numBytes, int type)
{
  return (byte*)&gScrMemTreeGlob.nodes[MT_AllocIndex(numBytes, type)];
}


bool MemoryTree::MT_Realloc(int oldNumBytes, int newNumbytes)
{
  return MT_GetSize(oldNumBytes) >= MT_GetSize(newNumbytes);
}

void MemoryTree::MT_Free(void *p, int numBytes)
{
  assertx((MemoryNode *) p - gScrMemTreeGlob.nodes >= 0 && (MemoryNode *) p - gScrMemTreeGlob.nodes < MEMORY_NODE_COUNT, 
            "(MemoryNode *) p - gScrMemTreeGlob.nodes = %i", (MemoryNode *) p - gScrMemTreeGlob.nodes);

  MT_FreeIndex((MemoryNode *) p - gScrMemTreeGlob.nodes, numBytes);
}

byte* MemoryTree::MT_GetRefByIndex(int index)
{
    if(index > MEMORY_NODE_COUNT)
    {
        MT_Error("MT_GetRefByIndex: out of bounds index", index);
        return NULL;
    }
    return (byte*)&gScrMemTreeGlob.nodes[index];
}

int MemoryTree::MT_GetIndexByRef(byte* p)
{
    int index = (MemoryNode *) p - gScrMemTreeGlob.nodes;
    if(index < 0 || index >= MEMORY_NODE_COUNT)
    {
        MT_Error("MT_GetIndexByRef: out of bounds ref", index);
        return 0;
    }
    return index;
}


static class MemoryTree mt;

extern "C"{

void __cdecl MT_DumpTree( )
{
    mt.MT_DumpTree();
}

void MT_Init()
{
    mt.MT_Init();
}

bool MT_Realloc(int oldNumBytes, int newNumbytes)
{
    return mt.MT_Realloc(oldNumBytes, newNumbytes);
}

byte *__cdecl MT_Alloc(int numBytes, int type)
{
  return mt.MT_Alloc(numBytes, type);
}

void __cdecl MT_Free(void *p, int numBytes)
{
  mt.MT_Free(p, numBytes);
}

};



byte* MT_GetRefByIndex(int index)
{
    return mt.MT_GetRefByIndex(index);
}

int MT_GetIndexByRef(byte* p)
{
    return mt.MT_GetIndexByRef(p);
}

void __cdecl MT_FreeIndex(unsigned int nodeNum, int numBytes)
{
  mt.MT_FreeIndex(nodeNum, numBytes);
}

unsigned int __cdecl MT_AllocIndex(int numBytes, int type)
{
	return mt.MT_AllocIndex(numBytes, type);
}

extern "C" int MT_IsAllocatedIndex(unsigned int nodeNum)
{
	return mt.MT_IsAllocatedIndex(nodeNum) ? 1 : 0;
}
