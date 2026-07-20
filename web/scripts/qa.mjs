import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const baseUrl = process.env.QA_URL ?? 'http://127.0.0.1:4173/'
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const artifactDir = new URL('../artifacts/', import.meta.url)

const artifactPath = (name) => fileURLToPath(new URL(name, artifactDir))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function observePage(page, errors) {
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('response', (response) => {
    if (response.status() >= 400) errors.push(`http ${response.status()}: ${response.url()}`)
  })
}

await mkdir(artifactDir, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: chromePath })
const errors = []
const checks = []

try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 })
  await observePage(desktop, errors)
  await desktop.goto(baseUrl, { waitUntil: 'networkidle' })

  await desktop.getByRole('heading', { name: 'IBD 타깃 근거 검토' }).waitFor()
  await desktop.getByText('TYK2는 이 IBD 실행의 분자 최적화 대상으로 진행하지 않습니다.').waitFor()
  await desktop.screenshot({ path: artifactPath('desktop-evidence.png'), fullPage: true })
  checks.push('desktop evidence decision')

  await desktop.getByRole('tab', { name: /분자/ }).click()
  await desktop.getByRole('heading', { name: '타깃 기각으로 분자 단계가 실행되지 않았습니다.' }).waitFor()
  checks.push('molecule stage empty state')

  await desktop.getByRole('button', { name: /분자 비교 UI fixture 열기/ }).click()
  await desktop.getByRole('heading', { name: '분자 비교 화면 점검' }).waitFor()
  await desktop.locator('.molecule-render svg').first().waitFor({ timeout: 20000 })
  const renderedStructures = await desktop.locator('.molecule-render svg').count()
  assert(renderedStructures >= 2, `RDKit SVG가 충분히 렌더링되지 않았습니다: ${renderedStructures}`)
  await desktop.screenshot({ path: artifactPath('desktop-molecules.png'), fullPage: true })
  checks.push(`RDKit structures ${renderedStructures}`)

  await desktop.getByRole('tab', { name: /보고서/ }).click()
  await desktop.getByText('SYNTHETIC', { exact: true }).waitFor()
  await desktop.getByText('과학적 결론이 아닌 UI 렌더링 확인 결과입니다.').count()
  checks.push('synthetic report disclosure')

  await desktop.getByRole('button', { name: '새 실행', exact: true }).first().click()
  const dialog = desktop.getByRole('dialog', { name: '새 실행 시작' })
  await dialog.getByRole('button', { name: /IBD 근거 검토/ }).click()
  await dialog.getByRole('button', { name: /실행 시작/ }).click()
  await desktop.getByText('실행 중', { exact: true }).first().waitFor({ timeout: 3000 })
  assert(await desktop.getByText('TYK2는 이 IBD 실행의 분자 최적화 대상으로 진행하지 않습니다.').count() === 0, '실행 초기에 최종 TYK2 판단이 노출됩니다.')
  await desktop.getByText('검토 대기', { exact: true }).first().waitFor({ timeout: 10000 })
  const skippedStages = await desktop.locator('.stage-marker.stage-skipped').count()
  assert(skippedStages === 5, `미실행 단계가 5개가 아닙니다: ${skippedStages}`)
  await desktop.getByRole('button', { name: /검토 완료 처리/ }).click()
  await desktop.getByRole('button', { name: /검토 완료/ }).waitFor()
  checks.push('run lifecycle, delayed output, and human review')

  await desktop.getByRole('button', { name: '새 실행', exact: true }).first().click()
  const fixtureDialog = desktop.getByRole('dialog', { name: '새 실행 시작' })
  await fixtureDialog.getByRole('button', { name: /분자 비교 UI 점검/ }).click()
  await fixtureDialog.getByRole('button', { name: /실행 시작/ }).click()
  await desktop.getByRole('heading', { name: '합성 fixture 레코드를 생성하는 중입니다.' }).waitFor({ timeout: 3000 })
  assert(await desktop.getByText('FIX-042', { exact: true }).count() === 0, '후보 생성 전에 합성 분자 레코드가 노출됩니다.')
  await desktop.getByRole('heading', { name: '분자 비교 화면 점검' }).waitFor({ timeout: 7000 })
  await desktop.getByRole('button', { name: /실행 취소/ }).click()
  await desktop.getByText('취소', { exact: true }).first().waitFor()
  checks.push('synthetic output gate and cancellation')

  await desktop.getByRole('button', { name: '새 실행', exact: true }).first().click()
  await desktop.keyboard.press('Escape')
  assert(await desktop.getByRole('dialog').count() === 0, 'Escape 키로 모달이 닫히지 않았습니다.')
  checks.push('dialog escape')

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 })
  await observePage(mobile, errors)
  await mobile.goto(baseUrl, { waitUntil: 'networkidle' })
  await mobile.getByRole('heading', { name: 'IBD 타깃 근거 검토' }).waitFor()
  const decisionBox = await mobile.locator('.decision-panel').boundingBox()
  const stageBox = await mobile.locator('.stage-panel').boundingBox()
  assert(decisionBox && stageBox && decisionBox.y < stageBox.y, '모바일에서 결정 패널이 파이프라인보다 먼저 배치되지 않았습니다.')
  const horizontalOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  assert(horizontalOverflow <= 1, `모바일 가로 넘침이 있습니다: ${horizontalOverflow}px`)
  await mobile.screenshot({ path: artifactPath('mobile-evidence.png'), fullPage: true })
  checks.push('mobile decision order and overflow')

  await mobile.getByRole('tab', { name: /개요/ }).focus()
  await mobile.keyboard.press('ArrowRight')
  assert(await mobile.getByRole('tab', { name: /타깃/ }).getAttribute('aria-selected') === 'true', '탭 화살표 키 이동이 동작하지 않습니다.')
  checks.push('keyboard tab navigation')

  await new Promise((resolve) => setTimeout(resolve, 500))
  assert(errors.length === 0, `브라우저 오류가 있습니다:\n${errors.join('\n')}`)

  process.stdout.write(`${JSON.stringify({ ok: true, checks, errors }, null, 2)}\n`)
} finally {
  await browser.close()
}
