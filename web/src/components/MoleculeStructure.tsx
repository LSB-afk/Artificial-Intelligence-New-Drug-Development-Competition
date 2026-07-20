import { AlertTriangle, LoaderCircle } from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { loadRDKit } from '../lib/rdkit'

interface MoleculeStructureProps {
  smiles: string
  compact?: boolean
  label?: string
}

type RenderState =
  | { status: 'loading' }
  | { status: 'ready'; svg: string; version: string }
  | { status: 'invalid'; message: string }

const svgCache = new Map<string, { svg: string; version: string }>()
const maxCachedStructures = 80

function readCachedStructure(key: string) {
  const cached = svgCache.get(key)
  if (!cached) return undefined
  svgCache.delete(key)
  svgCache.set(key, cached)
  return cached
}

function cacheStructure(key: string, value: { svg: string; version: string }) {
  if (svgCache.has(key)) svgCache.delete(key)
  svgCache.set(key, value)
  if (svgCache.size > maxCachedStructures) {
    const oldestKey = svgCache.keys().next().value
    if (oldestKey) svgCache.delete(oldestKey)
  }
}

export default function MoleculeStructure({ smiles, compact = false, label = '분자 구조' }: MoleculeStructureProps) {
  const titleId = useId()
  const cacheKey = `${compact ? '104x72' : '320x220'}:${smiles}`
  const cached = readCachedStructure(cacheKey)
  const [state, setState] = useState<RenderState>(cached ? { status: 'ready', ...cached } : { status: 'loading' })

  useEffect(() => {
    let cancelled = false
    const render = async () => {
      const cachedSvg = readCachedStructure(cacheKey)
      if (cachedSvg) {
        setState({ status: 'ready', ...cachedSvg })
        return
      }

      setState({ status: 'loading' })
      try {
        const rdkit = await loadRDKit()
        const molecule = rdkit.get_mol(smiles)
        if (!molecule) {
          if (!cancelled) setState({ status: 'invalid', message: 'RDKit이 이 SMILES를 해석하지 못했습니다.' })
          return
        }

        try {
          const size = compact ? 104 : 320
          const rendered = { svg: molecule.get_svg(size, compact ? 72 : 220), version: rdkit.version() }
          cacheStructure(cacheKey, rendered)
          if (!cancelled) setState({ status: 'ready', ...rendered })
        } finally {
          molecule.delete()
        }
      } catch {
        if (!cancelled) setState({ status: 'invalid', message: 'RDKit WebAssembly를 불러오지 못했습니다.' })
      }
    }
    void render()
    return () => { cancelled = true }
  }, [cacheKey, compact, smiles])

  if (state.status === 'loading') {
    return <div className={`molecule-render is-loading${compact ? ' is-compact' : ''}`} aria-label="분자 구조 로딩 중"><LoaderCircle className="spin" size={compact ? 16 : 22} /></div>
  }

  if (state.status === 'invalid') {
    return <div className={`molecule-render is-invalid${compact ? ' is-compact' : ''}`} title={state.message}><AlertTriangle size={compact ? 16 : 22} /><span>{compact ? '해석 실패' : state.message}</span></div>
  }

  return (
    <figure className={`molecule-render${compact ? ' is-compact' : ''}`} aria-labelledby={titleId}>
      <figcaption id={titleId} className="sr-only">{label}, RDKit {state.version} 렌더링</figcaption>
      <div aria-hidden="true" dangerouslySetInnerHTML={{ __html: state.svg }} />
    </figure>
  )
}
