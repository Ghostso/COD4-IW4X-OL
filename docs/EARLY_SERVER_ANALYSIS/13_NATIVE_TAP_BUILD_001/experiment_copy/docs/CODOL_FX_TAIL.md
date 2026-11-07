# CoDOL tail-element conversion

Oriented sprites are also supported: C1 dispatch table `0x00c3cb54[1]`
points to `0x004e5db0`. After culling, that handler passes the element's own
three axes (draw state +20/+2c/+38) to sprite generation at `0x004e51b0`.
The named IW3 `FX_DrawElem_OrientedSprite` in `_fx_draw.asm` (line 161)
uses its corresponding axes (+1c/+28/+34), and `s_drawElemHandler` assigns
it index 1. CoDOL type 1 therefore maps to native type 1, retaining the
existing material binding, sample ownership and effect-graph transaction.
The fixtures cover preserved samples/materials and oriented-sprite cyclic
dependencies, missing children, retries and archive replacement.
The oriented-sprite change passes full Linux regressions, Linux/Windows
server builds, the Linux sanitizer fixture and the native Windows FX fixture.

CoDOL element type 3 maps to IW3 type 2. This is a rendering-handler comparison,
not an inference from material-reference serialization or the XAsset type ID.

For C1 SHA256 `d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`:

- `0x004e683a` reads the element type byte at +176. `0x004e6841` indexes
  the handler table at `0x00c3cb54`; index 3 points to `0x004e6020`.
- The handler calls velocity evaluation at `0x005043c0`, then normalizes
  the resulting direction through `0x004090e0`.
- At `0x004e606f..0x004e6098`, it shifts the sprite center backward along
  that direction by the visual length.
- It constructs the camera-to-center vector and cross products with the
  velocity direction, normalizes the perpendicular axis, and calls the same
  sprite generator (`0x004e51b0`) used by billboard/oriented elements.

The retained, symbol-named implementation in
`tools/cod4_dasm/src/_fx_draw.asm`, `FX_DrawElem_Tail` (line 216), follows this
same sequence: `FX_GetVelocityAtTime`, normalization, tail culling, backward
center shift, camera/direction cross products, and sprite generation.
Its `s_drawElemHandler` table (line 4813) assigns the tail routine index 2.
The temporary draw-state offsets differ by four bytes; those states are not
copied by the asset converter. The measured source/native element records both
place type and sample fields at +176/+180/+184.

The converter now translates type 3 to type 2, binds native materials, owns
copied velocity/visual samples, and keeps the existing dependency transaction.
Trail definitions and unconverted extension fields still reject conversion.
The archive graph's type gate also accepts type 3.

Validation: the focused 32-bit ASan/UBSan fixture checks type translation,
material binding, sample preservation, dependent effects and atomic failure.
The full Linux regression/build passes. A native Linux startup against the
original archives reports both `muzzleflashes/pistolflash_view` and
`muzzleflashes/pistolflash` at native status 1 (previously the latter was -1).
This verifies conversion of the world flash's three tail-containing children;
it does not establish complete weapon registration or client match entry.

The final full Windows build and native Windows startup diagnostic also pass:
both leading effect slots report native status 1. Diagnostic runs use an
isolated home directory and port, then quit; the existing lobby and C1 client
are left running.
