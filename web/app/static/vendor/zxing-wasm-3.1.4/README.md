# zxing-wasm 3.1.4 (reader build)

Unmodified files from the npm package `zxing-wasm@3.1.4`
(<https://github.com/Sec-ant/zxing-wasm>, MIT, see `LICENSE`):

- `zxing-reader.iife.js` = `dist/iife/reader/index.js`
- `zxing_reader.wasm` = `dist/reader/zxing_reader.wasm`

Used by the nutrition barcode scanner (`ts/nutrition/modals/barcode.ts`) only
in browsers without a native `BarcodeDetector`. Loaded from this folder on
demand; camera frames are decoded locally and never uploaded. The WASM URL is
overridden (`locateFile`) so the library never fetches from a CDN.

To update: `npm pack zxing-wasm@<version>`, copy the two files, update the
folder name and `BARCODE_VENDOR` in `barcode.ts`, and check the hashes:

```
sha256sum zxing-reader.iife.js zxing_reader.wasm
```
