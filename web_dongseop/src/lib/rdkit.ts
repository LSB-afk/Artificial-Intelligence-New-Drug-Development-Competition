import initRDKitModule from '@rdkit/rdkit'
import rdkitWasmUrl from '@rdkit/rdkit/dist/RDKit_minimal.wasm?url'
import type { RDKitModule } from '@rdkit/rdkit'

let modulePromise: Promise<RDKitModule> | null = null

export function loadRDKit() {
  if (!modulePromise) {
    modulePromise = initRDKitModule({ locateFile: () => rdkitWasmUrl })
  }
  return modulePromise
}
