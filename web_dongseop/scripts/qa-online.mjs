/**
 * 하네스를 켠 상태의 QA 게이트.
 *
 * `qa.mjs`는 하네스를 끄고 돌면서 오프라인 폴백을 검증합니다. 그 게이트는 설계상
 * `/api/*`가 전부 실패하는 경로만 지나므로, 콘솔이 하네스에 실제로 연결됐을 때의
 * 코드 — 프리셋 목록, `POST /api/workspace/runs`, sandbox 실행의 출처 표기, 연결
 * 재확인 — 는 한 줄도 실행하지 않습니다. 데모의 핵심 증거가 회귀 감시 밖에 있던
 * 셈이라, 이 파일이 그 절반을 맡습니다.
 *
 * 하네스 수명은 이 스크립트가 직접 관리합니다. 켜고 끄는 순서 자체가 검증 대상이기
 * 때문입니다(사용자가 콘솔을 열어 둔 채 서버를 켜는 경우).
 *
 *     npm run qa:online
 */
import { spawn } from 'node:child_process'
import { mkdir, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const baseUrl = process.env.QA_URL ?? 'http://127.0.0.1:4173/'
// 러너마다 크롬 위치가 다릅니다. 기본값은 로컬 macOS 설치 경로입니다.
const chromePath = process.env.QA_CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const repoRoot = fileURLToPath(new URL('../../', import.meta.url))
const artifactDir = new URL('../artifacts/', import.meta.url)
const artifactPath = (name) => fileURLToPath(new URL(name, artifactDir))

const HARNESS_PORT = Number(process.env.QA_HARNESS_PORT ?? 8765)
const HARNESS_ORIGIN = `http://127.0.0.1:${HARNESS_PORT}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function harnessReachable() {
  try {
    const response = await fetch(`${HARNESS_ORIGIN}/api/health`)
    return response.ok
  } catch {
    return false
  }
}

/** 하네스를 띄우고 실제로 응답할 때까지 기다립니다. */
async function startHarness() {
  const child = spawn('python3', ['-m', 'h2l.server', '--port', String(HARNESS_PORT)], {
    cwd: repoRoot,
    env: { ...process.env, PYTHONPATH: 'src' },
    stdio: 'ignore',
    detached: true,
  })
  // python3가 없으면 'error'가 나고, 리스너가 없으면 uncaught로 튀어 정리 코드를 건너뜁니다.
  let spawnError = null
  child.on('error', (error) => { spawnError = error })
  child.unref()
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (spawnError) throw new Error(`하네스를 띄우지 못했습니다: ${spawnError.message}`)
    if (await harnessReachable()) return child
    await wait(250)
  }
  await stopHarness(child).catch(() => {})
  throw new Error(`하네스가 ${HARNESS_ORIGIN}에서 응답하지 않습니다.`)
}

async function stopHarness(child) {
  if (!child) return
  for (const signal of ['SIGTERM', 'SIGKILL']) {
    try { process.kill(-child.pid, signal) } catch { /* 이미 죽었으면 그만 */ }
    for (let attempt = 0; attempt < 20; attempt += 1) {
      if (!(await harnessReachable())) return
      await wait(250)
    }
  }
  // 여기까지 오면 포트를 잡고 있는 무언가가 남습니다. `npm run qa`는 :8765가 비어
  // 있어야 도니까, 조용히 넘기지 않고 사람이 치우도록 알립니다.
  throw new Error(`하네스가 멈추지 않았습니다. :${HARNESS_PORT}를 직접 확인해 주세요.`)
}

/** 모달을 열고 지금 무엇을 제시하는지 읽은 뒤 닫습니다. */
async function readStartDialog(page) {
  await page.getByRole('button', { name: '새 실행', exact: true }).first().click()
  await page.locator('.start-modal').waitFor()
  // 모달을 열면 연결을 다시 재므로 그 왕복을 기다립니다.
  await wait(600)
  const state = await page.evaluate(() => {
    const modes = [...document.querySelectorAll('.mode-fieldset button')].map((button) => ({
      label: button.querySelector('strong')?.textContent?.trim() ?? '',
      selected: button.classList.contains('is-selected'),
      disabled: button.disabled,
    }))
    return {
      scenarios: [...document.querySelectorAll('.scenario-fieldset button strong')]
        .map((node) => node.textContent.replace('권장', '').trim()),
      modes,
      scopeText: document.querySelector('.modal-scope p')?.textContent?.trim() ?? '',
    }
  })
  await page.keyboard.press('Escape')
  await page.locator('.start-modal').waitFor({ state: 'detached' })
  return state
}

await mkdir(artifactDir, { recursive: true })

assert(
  !(await harnessReachable()),
  `이 게이트는 하네스를 직접 켜고 끕니다. :${HARNESS_PORT}에 이미 떠 있는 서버를 먼저 내려 주세요.`,
)

const browser = await chromium.launch({ headless: true, executablePath: chromePath })

// 하네스는 자기 프로세스 그룹에 있으므로 터미널 SIGINT가 닿지 않습니다. 여기서
// 거두지 않으면 Ctrl-C 한 번에 :8765를 점유한 고아가 남고, 그 뒤로 이 게이트도
// `npm run qa`도 전제가 깨져 못 돕니다.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => {
    void stopHarness(harness)
      .catch(() => {})
      .finally(() => browser.close().catch(() => {}).finally(() => process.exit(130)))
  })
}
const errors = []
const checks = []
const probes = []
/** 6번이 하네스를 내려 둔 구간. 이 밖의 `/api/*` 실패는 전부 진짜 오류입니다. */
const offlineWindow = { open: false }
let harness = null

try {
  harness = await startHarness()

  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 })
  // 6번 검사만 하네스를 일부러 내립니다. 그 **구간 안의** `/api/*` 실패는 고장이
  // 아니라 검증 대상이므로 따로 모읍니다.
  //
  // 이 판별을 URL만 보고 하면 게이트가 스스로를 속입니다. 연결 구간의 진짜 API
  // 실패까지 같은 통에 들어가서, 오프라인 창을 통째로 지워도 `probes.length > 0`이
  // 만족되고 오류는 하나도 안 잡힙니다. 그래서 시간 구간으로 좁힙니다.
  const isHarnessProbe = (url) => url.startsWith(new URL('/api/', baseUrl).href)
  const expected = (url) => offlineWindow.open && isHarnessProbe(url)
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    // 리소스 적재 실패는 응답 리스너가 이미 분류합니다. 중복 계상하지 않습니다.
    if (isHarnessProbe(message.location()?.url ?? '')) return
    errors.push(`console: ${message.text()}`)
  })
  page.on('response', (response) => {
    if (response.status() < 400) return
    const entry = `${response.status()} ${new URL(response.url()).pathname}`
    if (expected(response.url())) probes.push(entry)
    else errors.push(`http ${entry} (${response.url()})`)
  })

  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  // `networkidle`은 요청이 멎었다는 뜻이지 React가 렌더를 끝냈다는 뜻이 아닙니다.
  // 아직 `.app-loading`일 때 셀렉터를 읽으면 전부 빈 값이라 단정이 헛돕니다.
  await page.locator('.app-loading').waitFor({ state: 'detached' }).catch(() => {})
  await page.locator('.prototype-note strong').waitFor()

  // ---- 1. 연결됨을 콘솔이 스스로 말하는가 --------------------------------
  const connected = await page.evaluate(() => ({
    chip: document.querySelector('.adapter-state')?.textContent?.trim() ?? '',
    isConnected: document.querySelectorAll('.adapter-state.is-connected').length,
    footer: document.querySelector('.prototype-note strong')?.textContent?.trim() ?? '',
    runCount: document.querySelectorAll('.recent-runs button').length,
  }))
  assert(connected.isConnected === 1, `하네스가 켜져 있는데 연결됨 표시가 없습니다: ${connected.chip}`)
  assert(connected.footer === '파이썬 하네스 연결', `연결 표기가 틀렸습니다: ${connected.footer}`)
  // 계산된 실행 2건 + 픽스처 2건. 하나라도 사라지면 폴백이나 병합이 깨진 것입니다.
  assert(connected.runCount === 4, `실행 수가 계산 2 + 픽스처 2가 아닙니다: ${connected.runCount}`)
  checks.push(`harness connected ${JSON.stringify(connected)}`)

  // ---- 2. 시나리오는 하네스가 내려준 것인가 -------------------------------
  const online = await readStartDialog(page)
  const harnessPresets = await fetch(`${HARNESS_ORIGIN}/api/scenarios`).then((r) => r.json())
  const presetLabels = harnessPresets.scenarios.map((preset) => preset.label)
  // 아래 단정들은 `.every()`라서 프리셋이 0개면 공허하게 참이 됩니다. 바닥을 박습니다.
  assert(presetLabels.length >= 4, `하네스가 프리셋을 충분히 내려주지 않았습니다: ${presetLabels.length}개`)
  assert(
    presetLabels.every((label) => online.scenarios.includes(label)),
    `하네스 프리셋이 모달에 없습니다. 서버=${presetLabels} 화면=${online.scenarios}`,
  )
  assert(
    online.scenarios.length === presetLabels.length,
    `모달이 하네스 프리셋 외의 시나리오를 섞어 보여 줍니다: ${online.scenarios}`,
  )
  const liveMode = online.modes.find((mode) => mode.label === '실제 하네스 API')
  assert(liveMode && !liveMode.disabled, '하네스가 켜져 있는데 "실제 하네스 API"를 고를 수 없습니다.')
  assert(liveMode.selected, '하네스가 켜져 있으면 실제 하네스 API가 기본 선택이어야 합니다.')
  checks.push(`harness presets in dialog ${JSON.stringify(online)}`)

  // ---- 3. 프리셋을 실행하면 규칙이 실제로 도는가 --------------------------
  await page.getByRole('button', { name: '새 실행', exact: true }).first().click()
  await page.locator('.start-modal').waitFor()
  await wait(600)
  const dialog = page.getByRole('dialog', { name: '새 실행 시작' })
  await dialog.getByRole('button', { name: /실패 임상/ }).click()
  await dialog.getByRole('button', { name: /실행 시작/ }).click()
  await page.locator('.start-modal').waitFor({ state: 'detached' })
  await wait(700)

  const run = await page.evaluate(() => ({
    classification: document.querySelector('.run-metrics > div:last-child strong')?.textContent?.trim() ?? '',
    heading: document.querySelector('h1')?.textContent?.trim() ?? '',
    notices: [...document.querySelectorAll('.context-banner strong, .safety-notice strong')]
      .map((node) => node.textContent.trim()),
  }))
  assert(run.heading.includes('DEMO-TARGET-B'), `실패 임상 프리셋의 타깃이 아닙니다: ${run.heading}`)
  assert(run.classification === '계산 결과', `계산 결과로 분류되지 않았습니다: ${run.classification}`)
  checks.push(`preset run computed ${JSON.stringify(run)}`)

  // 기각 판정이면 분자 단계가 열리면 안 됩니다. 이 게이트가 지키는 과학 불변식입니다.
  //
  // 패널 id와 게이트 전용 문장에 못 박습니다. `.content-area`에 "미실행"·"차단"으로
  // 느슨하게 물으면 개요 패널의 단계 배지가 그 정규식을 만족시켜서, 분자 탭을 아예
  // 열지 않아도 통과합니다.
  await page.getByRole('tab', { name: /분자/ }).click()
  await page.locator('#panel-molecules').waitFor()
  const moleculeText = await page.locator('#panel-molecules').innerText()
  assert(
    moleculeText.includes('진행 거절 판정이라 분자 단계를 열지 않았습니다.'),
    `기각 실행인데 분자 화면이 게이트 차단을 말하지 않습니다: ${moleculeText.slice(0, 160)}`,
  )
  assert(!/후보|candidate/i.test(moleculeText.split('\n')[0] ?? ''), '기각 실행에 분자 후보가 표시됩니다.')

  // 보고서 본문은 화면에 그리지 않고 내려받기로만 나갑니다. 그러니 화면 텍스트가
  // 아니라 실제로 저장되는 바이트를 봐야 합니다 — 콘솔의 sandbox 표시는 이 파일을
  // 따라나가지 않으므로, 파일이 스스로 출처를 말해야 합니다.
  await page.getByRole('tab', { name: /보고서/ }).click()
  await wait(400)
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /TXT 다운로드/ }).first().click(),
  ])
  const reportPath = artifactPath('online-decision-report.txt')
  await download.saveAs(reportPath)
  const report = await readFile(reportPath, 'utf8')
  assert(report.includes('Provenance: SANDBOX'), `내려받은 보고서에 SANDBOX 출처 표기가 없습니다:\n${report}`)
  assert(/Run: SANDBOX-/.test(report), `보고서의 실행 id에 SANDBOX 표시가 없습니다:\n${report}`)
  assert(/Molecule eligible: false/.test(report), `승인 없는 실행인데 분자 단계가 열렸습니다:\n${report}`)
  await page.screenshot({ path: artifactPath('online-preset-run.png'), fullPage: true })
  checks.push(`sandbox provenance survives into the exported report (${download.suggestedFilename()})`)

  // ---- 4. 과학 plane은 여전히 읽기 전용인가 -------------------------------
  const listAfter = await fetch(`${HARNESS_ORIGIN}/api/workspace/runs`).then((r) => r.text())
  const registryAfter = await fetch(`${HARNESS_ORIGIN}/api/registry`).then((r) => r.text())
  assert(JSON.parse(listAfter).runs.length === 2, '실행 생성이 하네스 목록을 바꿨습니다.')
  assert(!listAfter.includes('SANDBOX-'), 'sandbox 실행이 하네스 목록에 저장됐습니다.')
  // "SANDBOX가 없다"는 500 오류 본문에서도 참이므로, 응답이 진짜인지 먼저 봅니다.
  assert(JSON.parse(registryAfter).groups.length > 0, '레지스트리 응답이 비어 있어 오염 여부를 확인할 수 없습니다.')
  assert(!registryAfter.includes('SANDBOX'), 'sandbox 실행이 레지스트리에 들어갔습니다.')
  checks.push('scientific plane unchanged by a console run')

  // ---- 5. UI 토큰이 살아 있는가(연결 경로에서도) --------------------------
  await page.getByRole('tab', { name: /개요/ }).click()
  const tokens = await page.evaluate(() => ({
    sidebar: getComputedStyle(document.querySelector('.sidebar')).backgroundColor,
    primary: getComputedStyle(document.querySelector('.primary-button')).backgroundColor,
    body: Number.parseFloat(getComputedStyle(document.body).fontSize),
  }))
  assert(tokens.sidebar === 'rgb(248, 251, 252)', `사이드바 색이 바뀌었습니다: ${tokens.sidebar}`)
  assert(tokens.primary === 'rgb(47, 111, 228)', `기본 버튼 색이 바뀌었습니다: ${tokens.primary}`)
  assert(tokens.body >= 15, `기본 글자 크기가 너무 작습니다: ${tokens.body}px`)
  checks.push(`style tokens hold on the connected path ${JSON.stringify(tokens)}`)

  // ---- 6. 연결 상태를 다시 재는가 ----------------------------------------
  // 콘솔을 열어 둔 채 하네스를 껐다 켜는 것은 데모 중에 실제로 일어나는 일이고,
  // 마운트 때 한 번만 재던 시절에는 새로고침 전까지 계속 "닿지 않습니다"였습니다.
  offlineWindow.open = true
  await stopHarness(harness)
  harness = null
  const offline = await readStartDialog(page)
  const offlineLive = offline.modes.find((mode) => mode.label === '실제 하네스 API')
  assert(offlineLive?.disabled, '하네스를 내렸는데 실제 하네스 API가 아직 선택 가능합니다.')
  assert(
    !offline.scenarios.some((label) => presetLabels.includes(label)),
    `하네스가 꺼졌는데 프리셋이 남아 있습니다: ${offline.scenarios}`,
  )

  // 창을 닫기 전에, 그 안에서 실제로 연결 실패가 관측됐는지 확인합니다. 여기가
  // 비어 있으면 하네스가 안 내려갔거나 콘솔이 재조회를 안 한 것이고, 두 경우 모두
  // 아래 재연결 단정은 아무것도 증명하지 못합니다.
  assert(probes.length > 0, '하네스를 내린 구간에서 연결 실패 흔적이 없습니다. 재연결 검사가 헛돌았습니다.')
  const offlineProbeCount = probes.length

  harness = await startHarness()
  await wait(300)
  offlineWindow.open = false
  const back = await readStartDialog(page)
  const backLive = back.modes.find((mode) => mode.label === '실제 하네스 API')
  assert(backLive && !backLive.disabled, '하네스를 다시 켰는데 새로고침 없이는 고를 수 없습니다.')
  assert(
    presetLabels.every((label) => back.scenarios.includes(label)),
    `재연결 후 프리셋이 돌아오지 않았습니다: ${back.scenarios}`,
  )
  checks.push('connection state is re-measured, not cached from mount')

  await wait(300)
  assert(errors.length === 0, `브라우저 오류가 있습니다:\n${errors.join('\n')}`)
  assert(
    probes.length === offlineProbeCount,
    `하네스를 다시 켠 뒤에도 연결 실패가 이어졌습니다: ${probes.slice(offlineProbeCount).join(', ')}`,
  )

  process.stdout.write(`${JSON.stringify({ ok: true, checks, errors, offlineProbes: [...new Set(probes)] }, null, 2)}\n`)
} finally {
  await stopHarness(harness).catch(() => {})
  await browser.close()
}
