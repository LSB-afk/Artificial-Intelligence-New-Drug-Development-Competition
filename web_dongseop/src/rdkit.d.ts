declare module '@rdkit/rdkit' {
  export interface JSMol {
    delete(): void
    get_svg(width: number, height: number): string
  }

  export interface RDKitModule {
    get_mol(smiles: string): JSMol | null
    version(): string
  }

  export interface RDKitLoaderOptions {
    locateFile?: () => string
  }

  export default function initRDKitModule(options?: RDKitLoaderOptions): Promise<RDKitModule>
}

declare module '*?url' {
  const url: string
  export default url
}
