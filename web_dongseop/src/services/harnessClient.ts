import type { HarnessClient } from '../domain/contracts'
import { MockHarnessClient } from './mockHarness'

// 실제 하네스가 준비되면 이 한 줄을 HTTP/SSE 어댑터로 교체합니다.
export const harnessClient: HarnessClient = new MockHarnessClient()
