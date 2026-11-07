#pragma once

#include "sv_alpha_weapon_port_mp.hpp"

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace CodolGameServer
{
    // OLMOD(forge-publish): registers a CodolForge-emitted XAnimParts with the
    // running client through the retained DB_LinkXAssetEntry, the same door
    // `sv_alpha_weapon_port_mp` already uses for WeaponDef and StringTable.
    //
    // The work splits in two, and the split is deliberate because only one half
    // can be proved without a client:
    //
    //   RELOCATION  pure, deterministic, unit-tested. A staged blob stores its
    //               pointer fields as 0 (NULL) or 0xFFFFFFFF (payload follows
    //               inline), exactly as a zone stream does. Relocating copies the
    //               blob into owned memory and rewrites those placeholders into
    //               real addresses, walking the arrays in the loader's own order
    //               and requiring them to tile the blob EXACTLY.
    //
    //   PUBLICATION one call into the engine. It cannot be tested offline, so it
    //               is kept as thin as possible, guarded, and fails closed.
    //
    // CODREF(xanim): Load_XAnimParts out.exe 0x485B40 reads 88 bytes and visits
    // its arrays in this order - name string, names, notify, deltaPart, dataByte,
    // dataShort, dataInt, randomDataShort, randomDataByte, randomDataInt,
    // indices. The stream is PACKED: the loader aligns its destination cursor,
    // not the source, so there is no padding between arrays.

    enum class SvForgeXAnimStatus : std::uint32_t
    {
        Disabled,
        InvalidBlob,        // the blob's arrays do not tile it
        UnresolvedString,   // a bone or notify name did not intern
        MissingBinding,     // an engine function was not supplied
        WrongThread,
        LinkFailed,         // DB_LinkXAssetEntry faulted or refused
        Ready,
    };

    [[nodiscard]] const char *SV_ForgeXAnimStatusName(SvForgeXAnimStatus status) noexcept;

    // A relocated asset. The engine COPIES the 88-byte header but keeps every
    // pointer inside it, so this storage must outlive the client - it is never
    // freed, and it must never be moved or reallocated after relocation.
    struct SvForgeXAnimAsset
    {
        std::vector<std::byte> storage;
        std::string name;
        std::uint8_t boneCount = 0;
        std::uint8_t notifyCount = 0;
        std::vector<std::uint16_t> boneStrings;    // resolved, parallel to boneNames
        std::vector<std::uint16_t> notifyStrings;

        [[nodiscard]] void *header() noexcept
        {
            return storage.empty() ? nullptr : storage.data();
        }
    };

    // Resolves one name to a script-string index. Returns 0 for failure - index 0
    // is the null string, so it is never a valid answer for a bone name.
    using SvForgeStringResolver = std::function<std::uint16_t(const std::string &)>;

    // Pure. Makes no engine call. Fails rather than guessing on ANY inconsistency:
    // an unexpected pointer placeholder, arrays that do not tile the blob exactly,
    // a bone-name list that disagrees with the header's count, or a name that does
    // not resolve.
    [[nodiscard]] std::optional<SvForgeXAnimAsset> SV_RelocateForgeXAnim(
        std::span<const std::byte> blob,
        const std::vector<std::string> &boneNames,
        const std::vector<std::string> &notifyNames,
        const SvForgeStringResolver &resolve,
        std::string &error);

    struct SvForgeXAnimBindings
    {
        // out.exe 0x49DA10, __cdecl (XAssetType, XAssetHeader **).
        void *dbLinkXAssetEntry = nullptr;
        // out.exe 0x74BD10, __cdecl (const char *, int kind, unsigned len) -> index.
        // The zone loader passes kind 4 for its own string list.
        void *scriptStringGet = nullptr;
        std::int32_t scriptStringKind = 4;
    };

    // Builds a resolver over `bindings.scriptStringGet`. Returns an empty function
    // when the binding is absent, so a caller can tell "not bound" from "resolved
    // to nothing".
    //
    // PREFER SV_ForgeStringTableResolver. This one calls into the engine, which
    // means a critical section and a calling convention that has never been
    // exercised; the table walk needs neither.
    [[nodiscard]] SvForgeStringResolver SV_ForgeStringResolver(
        const SvForgeXAnimBindings &bindings) noexcept;

    // out.exe 0x789C524 holds the script-string table base. Entries are 20 bytes:
    //   +0 u16 refcount   +2 u8 kind   +3 u8 length (INCLUDING the NUL)
    //   +4.. the name, inline
    //
    // MEASURED against a running client on 2026-09-09: the pointer read back
    // 0x789c700, bone names were present with kind 4 - the kind the zone loader
    // passes - and `length` was strlen+1 as the intern call site implies.
    inline constexpr std::size_t ScriptStringTablePtrRva = 0x749C524;  // 0x0789C524
    inline constexpr std::size_t ScriptStringStride = 20;
    inline constexpr std::size_t ScriptStringMaxIndex = 0xFFFF;

    // Resolves by WALKING that table instead of calling the intern function.
    // Read-only: no critical section, no allocation, and no calling convention to
    // get wrong - a wrong one would take the client down.
    //
    // It cannot intern a name the client does not already have. A port never needs
    // that: of the 67 bone names the PPSh animations bind, 66 are already OLfinal
    // script strings, and the one that is not is the gun model's own.
    //
    // The index it returns is PER PROCESS. Two clients on one machine give the
    // same bone different indices, which is why an emitted asset cannot carry them.
    [[nodiscard]] SvForgeStringResolver SV_ForgeStringTableResolver(
        std::uintptr_t moduleBase) noexcept;

    // The engine call. NOT covered by tests - nothing here has been executed
    // against a client, and a caller must treat a Ready result as "the call
    // returned", not as "the animation plays".
    //
    // XAnimParts is asset type 2.
    [[nodiscard]] SvForgeXAnimStatus SV_PublishForgeXAnim(
        SvForgeXAnimAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept;

    inline constexpr std::uint32_t OlfinalXAnimAssetType = 2;

    // RVAs against the 3.19.26.13 image base 0x400000, so nothing here assumes the
    // module loaded where it prefers.
    inline constexpr std::size_t DBLinkXAssetEntryRva = 0x09DA10;   // 0x0049DA10
    inline constexpr std::size_t ScriptStringGetRva = 0x34BD10;     // 0x0074BD10

    // The slice of a bundle animation this path needs, so it does not have to
    // include the bundle header.
    struct SvForgeAnimationRef
    {
        std::string name;
        std::string asset;
        std::vector<std::string> bones;
        std::vector<std::string> notifies;
    };

    struct SvForgeXAnimPublishReport
    {
        bool ran = false;                  // false when the gate was closed
        std::size_t attempted = 0;
        std::size_t published = 0;
        std::vector<std::pair<std::string, std::string>> failures;  // name, why
    };

    // The whole path, in one call: resolve the two engine functions from
    // `moduleBase`, read each animation's blob from `<bundleRoot>/<asset>`,
    // relocate it, and publish it as asset type 2.
    //
    // GATED. Does nothing at all unless `enable` is true, because publishing an
    // asset into a live client is not something to do as a side effect of loading
    // a bundle. Nothing in this repository calls it with `enable` set.
    //
    // Relocated assets are kept alive for the life of the process: the engine
    // copies the 88-byte header but keeps the pointers inside it, so the storage
    // can never be released.
    //
    // NOT VERIFIED AGAINST A RUNNING CLIENT. A `published` count means the engine
    // call returned an entry, not that the animation plays.
    [[nodiscard]] SvForgeXAnimPublishReport SV_PublishForgeBundleXAnims(
        const std::vector<SvForgeAnimationRef> &animations,
        const std::filesystem::path &bundleRoot,
        std::uintptr_t moduleBase,
        bool enable) noexcept;

    // -----------------------------------------------------------------------
    // XModel (asset type 4)
    //
    // Unlike an animation, an XModel is NOT a self-contained blob: CodolForge
    // emits a 360-byte header with its scalars set and every pointer slot zero,
    // and ships the skeleton arrays separately. So there is nothing to relocate -
    // the layout is BUILT here, from the bundle's own pieces.
    //
    // CODREF(xmodel): Load_XModel out.exe 0x489B20, with every count read off its
    // own register loads rather than transferred from IW4 notes:
    //
    //   +44 boneNames          u16   x numBones          (sub_484F80(bones, 1))
    //   +48 parentList         u8    x nonRoot           (sub_484D00, esi=bones-roots)
    //   +52 quats              i16   x 4 * nonRoot       (sub_484E80)
    //   +56 trans              float x 3 * nonRoot       (sub_484D80, 4*eax bytes)
    //   +60 partClassification u8    x numBones          (sub_484D00, esi=bones)
    //   +64 baseMat            32    x numBones          (sub_485FF0, eax<<5)
    //   +68 materials          ptr   x numsurfs          (sub_488490, edi*4)
    //   +72 XModelLodInfo[4], 56 bytes each, INLINE in the struct
    //   +300 collSurfs (count +304)  +312 boneInfo
    //   +352 physPreset  +356 physCollmap
    //
    // nonRoot = numBones - numRootBones. `sub_489B20` reads bones at +4 and roots
    // at +5 and subtracts them at 0x489C1F / 0x489CCF, which is what fixes those
    // four array lengths.
    //
    // lodInfo[0].modelSurfs carries the streamed sentinel 0xFFFFFFFE and
    // lodInfo[0].name is the LOOSE resource name - `models/%s` is one of the three
    // channels out.exe still honours, so the surfaces arrive from the overlay
    // rather than from the zone.

    // Resolves a material name to the engine's `Material *`. Returns nullptr for
    // failure, which is always fatal: a surface with no material is not drawable.
    using SvForgeMaterialResolver = std::function<void *(const std::string &)>;

    struct SvForgeModelRef
    {
        std::string name;
        std::vector<std::byte> header;              // exactly 360 bytes
        std::vector<std::string> boneNames;
        std::vector<std::byte> parentList;
        std::vector<std::byte> quaternions;
        std::vector<std::byte> translations;
        std::vector<std::byte> partClassification;
        std::vector<std::byte> baseMatrices;
        std::string resource;                       // lodInfo[0].name
        std::vector<std::string> materials;
    };

    struct SvForgeXModelAsset
    {
        std::vector<std::byte> storage;             // header, then everything it points at
        std::string name;
        std::uint8_t numBones = 0;
        std::uint8_t numRootBones = 0;
        std::uint8_t numsurfs = 0;
        std::vector<std::uint16_t> boneStrings;

        [[nodiscard]] void *header() noexcept
        {
            return storage.empty() ? nullptr : storage.data();
        }
    };

    // Pure apart from the two resolvers. Refuses on any disagreement between the
    // header's scalars and the arrays it was given, because a published XModel
    // whose bone count lies is a crash rather than a visual glitch.
    [[nodiscard]] std::optional<SvForgeXModelAsset> SV_BuildForgeXModel(
        const SvForgeModelRef &model,
        const SvForgeStringResolver &resolveString,
        const SvForgeMaterialResolver &resolveMaterial,
        std::string &error);

    // XModel is asset type 4; Material is 5.
    inline constexpr std::uint32_t OlfinalXModelAssetType = 4;
    inline constexpr std::uint32_t OlfinalMaterialAssetType = 5;

    // out.exe 0x49CF30 - DB_FindXAssetHeader(u32 type, const char *name,
    // int allowDefault), __cdecl, confirmed from its own disassembly.
    //
    // CORRECTION: this was first written as 0x09D3B0, taken from
    // `ClientAnimtreeHook.cpp`'s FindAssetRva without checking it named the same
    // function. It does not - 0x49D3B0 falls INSIDE another routine, and calling
    // it with three arguments would have run arbitrary code. `EngineBindings`
    // already had the right value (DBFindXAssetHeaderRva 0x09CF30) and its comment
    // says outright that the binary carries both a two- and a three-argument form.
    //
    // NOTE: this function can BLOCK - it waits on a streaming event and takes
    // different paths depending on the calling thread - so it is not safe to call
    // from an arbitrary thread.
    inline constexpr std::size_t DBFindXAssetHeaderRva = 0x09CF30;   // 0x0049CF30

    // -----------------------------------------------------------------------
    // The XAsset hash table, walked read-only.
    //
    // PREFER THESE over SV_ForgeMaterialResolver / SV_ForgeImageResolver, for the
    // same reason SV_ForgeStringTableResolver is preferred over the intern call:
    // no critical section, no allocation, no calling convention to get wrong, and
    // nothing that can block.
    //
    // `DB_FindXAssetHeader` (0x49CF30) is the wrong door for anything driven from
    // outside the engine's own threads. It takes a critical section, waits on a
    // streaming event, and branches on `GetCurrentThreadId` against three
    // different thread ids - and on a live client it did exactly that.
    //
    // But ALL of that is its wrapper. The lookup itself is `sub_49CA70`, and it is
    // pure:
    //
    //     bucket = sub_49C870(type, name)
    //     for (i = heads[bucket]; i; i = entries[i].next)
    //         if (entries[i].type == type && iequals(name, nameOf(entries[i])))
    //             return &entries[i]
    //
    //     entries  dword_239B120   28-byte stride
    //                +0 u32 type   +8 header   +20 u32 next
    //     heads    dword_1E2D338   one u32 per bucket, 0 terminates a chain
    //     buckets  0x1D4C0 = 120,000
    //
    // and `sub_49C870` is seeded with the ASSET TYPE - `mov eax, edi` at 0x49DA60,
    // where edi holds it:
    //
    //     h = type
    //     for each char:  c = tolower(ch);  h = 31 * h + (c == '\\' ? '/' : c)
    //     return h % 120000
    //
    // Note the asymmetry, which is the engine's and is mirrored exactly: the HASH
    // folds a backslash to a forward slash, and the COMPARE does not. Two names
    // differing only in slash direction share a bucket and still compare unequal.
    //
    // MEASURED against a live client on 2026-09-09: walking all 120,000 buckets
    // and recomputing each entry's hash from its own name reproduced the bucket it
    // was found in for **81,128 of 81,128** assets whose type has a name accessor,
    // with zero mismatches. The remaining 18,882 entries are type 27, whose
    // accessor is none of the three below and which is therefore refused rather
    // than read at a guessed offset. The longest chain in the whole table is 7,
    // and `mc/mtl_t6_wpn_pda` resolves in ONE step - against the 200,000-entry
    // linear scan the runtime probes used before this was decoded.

    inline constexpr std::size_t XAssetEntriesRva = 0x1F9B120;       // 0x0239B120
    inline constexpr std::size_t XAssetHashHeadsRva = 0x1A2D338;     // 0x01E2D338
    inline constexpr std::size_t XAssetNameThunksRva = 0xA5C8C0;     // 0x00E5C8C0
    inline constexpr std::size_t XAssetEntryStride = 28;
    inline constexpr std::size_t XAssetEntryTypeOffset = 0;
    inline constexpr std::size_t XAssetEntryHeaderOffset = 8;
    inline constexpr std::size_t XAssetEntryNextOffset = 20;
    inline constexpr std::uint32_t XAssetHashBuckets = 0x1D4C0;      // 120,000
    // The measured longest chain is 7. This cap only has to stop a corrupt `next`
    // from spinning; it is not a size the table is expected to approach.
    inline constexpr std::uint32_t XAssetMaxChainSteps = 4096;
    // A name longer than this is treated as no match rather than read further.
    inline constexpr std::size_t XAssetMaxNameLength = 1024;

    // `funcs_49CACE` at 0x00E5C8C0 is the engine's own per-type name accessor.
    // Three distinct thunks cover every type this port touches, and each one IS
    // the offset, read from the engine rather than inferred from samples:
    //
    //     0x483390   **(DWORD **)p         name at header +0   (XAnimParts, XModel)
    //     0x4833A0   *(DWORD *)(*p + 16)   Material at +16
    //     0x4833C0   *(DWORD *)(*p + 48)   GfxImage at +48
    inline constexpr std::uint32_t XAssetNameThunkAt0Rva = 0x83390;    // 0x00483390
    inline constexpr std::uint32_t XAssetNameThunkAt16Rva = 0x833A0;   // 0x004833A0
    inline constexpr std::uint32_t XAssetNameThunkAt48Rva = 0x833C0;   // 0x004833C0
    inline constexpr std::size_t XAssetNameOffsetUnknown =
        static_cast<std::size_t>(-1);

    // Pure. sub_49C870, reproduced.
    [[nodiscard]] std::uint32_t SV_ForgeXAssetHash(
        std::uint32_t type, const std::string &name) noexcept;

    // Pure. Maps one of the three accessor thunks to the offset it reads.
    // XAssetNameOffsetUnknown for anything else, which always refuses.
    [[nodiscard]] std::size_t SV_ForgeXAssetNameOffsetForThunk(
        std::uint32_t thunkRva) noexcept;

    // Pure. sub_49CA70's comparison: byte for byte, lowering only A-Z.
    [[nodiscard]] bool SV_ForgeXAssetNamesEqual(
        const char *stored, const std::string &wanted) noexcept;

    // A view over the three arrays. Held as raw pointers so a test can point it at
    // synthetic memory and exercise the walk without a client.
    struct SvForgeXAssetTable
    {
        const std::uint32_t *hashHeads = nullptr;
        const std::uint8_t *entries = nullptr;
        const std::uintptr_t *nameThunks = nullptr;   // absolute addresses
        std::uintptr_t moduleBase = 0;                // to turn one into an RVA
        std::uint32_t buckets = XAssetHashBuckets;

        [[nodiscard]] bool valid() const noexcept
        {
            return hashHeads && entries && nameThunks && buckets;
        }
    };

    [[nodiscard]] SvForgeXAssetTable SV_ForgeXAssetTableFor(
        std::uintptr_t moduleBase) noexcept;

    // The lookup. Returns the asset's header, or nullptr - and nullptr always
    // means "not present", never "the default one", because this walk cannot
    // create a default the way DB_FindXAssetHeader can.
    [[nodiscard]] void *SV_ForgeFindXAsset(
        const SvForgeXAssetTable &table,
        std::uint32_t type,
        const std::string &name) noexcept;

    // The two resolvers the builders actually want.
    [[nodiscard]] SvForgeMaterialResolver SV_ForgeMaterialTableResolver(
        std::uintptr_t moduleBase) noexcept;
    // SV_ForgeImageTableResolver is declared with the image resolver below, where
    // SvForgeImageResolver itself is first named.

    // Builds a material resolver over DB_FindXAssetHeader. Empty when unbound.
    //
    // PREFER SV_ForgeMaterialTableResolver. This one is kept only because the
    // engine call is the reference the walk above was derived FROM; a live client
    // has already shown it blocks.
    [[nodiscard]] SvForgeMaterialResolver SV_ForgeMaterialResolver(
        std::uintptr_t moduleBase) noexcept;

    // The engine call for a model. Same caveat as the animation one: a Ready
    // result means the call returned, not that the model draws.
    [[nodiscard]] SvForgeXAnimStatus SV_PublishForgeXModel(
        SvForgeXModelAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept;

    // -----------------------------------------------------------------------
    // WeaponDef (asset type 28)
    //
    // Nothing new is published here: `sv_alpha_weapon_port_mp` ALREADY clones a
    // shipped WeaponDef, patches it through SV_PatchAlphaWeaponDefinition and
    // links it as type 28. What was missing is the bridge - turning the CoD4
    // weaponfile's strings and seconds into the tuning that patch consumes.
    //
    // The mapping is pure and fully testable, which is the whole reason it lives
    // here rather than inside the engine call.
    [[nodiscard]] std::optional<SvAlphaWeaponTuning> SV_ForgeWeaponTuning(
        const std::map<std::string, std::string> &keys,
        std::string &error);

    // -----------------------------------------------------------------------
    // Material (asset type 5)
    //
    // A Material is CLONED, never authored. `MaterialTextureDef.nameHash` is
    // produced by the asset pipeline and appears nowhere in the client, so it
    // cannot be recomputed - but it does not have to be. The hash covers the
    // SAMPLER NAME, so the same slot carries the same hash in every material that
    // has it, which makes it a usable key for matching a clone's slots to a port's.
    //
    // Measured across 2,849 shipped materials (nameStart/nameEnd are literally the
    // first and last characters of the sampler name):
    //
    //   colorMap     'c'..'p'   0xa0ab1041   semantic 2   2920 uses
    //   normalMap    'n'..'p'   0x59d30d0f   semantic 5   2575
    //   specularMap  's'..'p'   0x34ecccb3   semantic 8   2251
    //   detailMap    'd'..'p'   0xeb529b4d   semantic 5     92
    //
    // CODREF(material): Load_Material out.exe 0x488250 reads 104 bytes.
    //   +16 name   +81 textureCount   +82 constantCount   +83 stateBitsCount
    //   +88 techniqueSet   +92 textureTable (12 bytes per entry)
    //   +96 constantTable (16-byte aligned)   +100 stateBitsTable
    //
    // Only the texture table and the name are replaced. techniqueSet, constants
    // and state bits keep pointing at the CLONE's engine-owned memory - that is
    // what cloning is for, and it is the same shallow strategy the WeaponDef port
    // already relies on.
    struct SvForgeMaterialSlot
    {
        std::string semantic;   // colorMap, normalMap, specularMap, detailMap
        std::string image;
    };

    struct SvForgeMaterialAsset
    {
        std::vector<std::byte> storage;   // 104-byte header, name, texture table
        std::string name;
        std::uint8_t textureCount = 0;

        [[nodiscard]] void *header() noexcept
        {
            return storage.empty() ? nullptr : storage.data();
        }
    };

    using SvForgeImageResolver = std::function<void *(const std::string &)>;

    // Pure apart from the image resolver. `cloneHeader` is the 104 bytes of a
    // shipped Material and `cloneTable` its textureCount x 12 texture table, both
    // read out of the running client. Refuses if a requested slot is not one the
    // clone actually has, because writing an image into the wrong slot draws a
    // normal map as diffuse rather than failing.
    [[nodiscard]] std::optional<SvForgeMaterialAsset> SV_BuildForgeMaterial(
        const std::string &name,
        std::span<const std::byte> cloneHeader,
        std::span<const std::byte> cloneTable,
        const std::vector<SvForgeMaterialSlot> &slots,
        const SvForgeImageResolver &resolveImage,
        std::string &error);

    // The nameHash a sampler slot carries, or 0 for a name with no measurement.
    [[nodiscard]] std::uint32_t SV_ForgeSamplerHash(const std::string &semantic) noexcept;

    // -----------------------------------------------------------------------
    // The CoD4 material file, which says which image goes in which slot.
    //
    // SV_BuildForgeMaterial takes slots as {semantic, image} pairs, and something
    // has to produce them. Taking them from the `_c` / `_n` / `_s` suffix would be
    // a convention, and a convention is exactly the kind of thing that produces a
    // plausible wrong answer - a normal map in the diffuse slot draws, it just
    // draws wrong.
    //
    // It does not have to be guessed. A CoD4 material carries its sampler names as
    // literal strings beside its own texture table:
    //
    //     +0   u32 offset of the material's name
    //     +48  u8  textureCount        +50 u8 constantCount
    //     +52  u32 offset of the technique-set name
    //     +56  u32 offset of the texture table
    //     +60  u32 offset of the constant table
    //
    //     texture table entry, 12 bytes:
    //       +0  u32 offset of the SAMPLER name ("colorMap", "normalMap", ...)
    //       +4  u8  sampleState        +5 u8 semantic
    //       +8  u32 offset of the IMAGE name
    //
    // Every pointer field in the file is a FILE OFFSET - the package was dumped
    // with its pointers rebased - so the whole thing is self-contained.
    //
    // MEASURED against the PPSh's two materials (299 bytes each):
    //
    //     mtl_t4_ppsh41_base   colorMap    semantic 2  t4_ppsh41_base_c
    //                          normalMap   semantic 5  t4_ppsh41_base_n
    //                          specularMap semantic 8  ~t4_ppsh41_base_s-rgb&...
    //
    // and those semantics are the same 2 / 5 / 8 measured across 2,849 shipped
    // OLfinal materials, which is what makes the sampler name a usable key across
    // the two engines.
    struct SvForgeCod4Material
    {
        std::string name;
        std::vector<SvForgeMaterialSlot> slots;   // semantic name, image name
        std::vector<std::uint8_t> semantics;      // parallel, as the file states them
        std::string techniqueSet;
    };

    // Pure. Refuses on any offset that leaves the file, any string without a
    // terminator inside it, and any sampler whose nameHash this tree has not
    // measured - because a slot that cannot be matched by hash cannot be bound at
    // all, and binding it by position is the failure this refuses to make.
    [[nodiscard]] std::optional<SvForgeCod4Material> SV_ParseForgeCod4Material(
        std::span<const std::byte> file,
        std::string &error);

    inline constexpr std::size_t OffCod4MtlName = 0;
    inline constexpr std::size_t OffCod4MtlTextureCount = 48;
    inline constexpr std::size_t OffCod4MtlConstantCount = 50;
    inline constexpr std::size_t OffCod4MtlTechniqueSet = 52;
    inline constexpr std::size_t OffCod4MtlTextureTable = 56;
    inline constexpr std::size_t Cod4MtlHeaderSize = 64;
    inline constexpr std::size_t Cod4TextureDefStride = 12;


    inline constexpr std::uint32_t OlfinalGfxImageAssetType = 10;

    // Builds an image resolver over DB_FindXAssetHeader. Empty when unbound.
    //
    // PREFER SV_ForgeImageTableResolver, for the reason given above it.
    [[nodiscard]] SvForgeImageResolver SV_ForgeImageResolver(
        std::uintptr_t moduleBase) noexcept;

    // The read-only walk, for images. See *The XAsset hash table* above.
    [[nodiscard]] SvForgeImageResolver SV_ForgeImageTableResolver(
        std::uintptr_t moduleBase) noexcept;

    [[nodiscard]] SvForgeXAnimStatus SV_PublishForgeMaterial(
        SvForgeMaterialAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept;
}
