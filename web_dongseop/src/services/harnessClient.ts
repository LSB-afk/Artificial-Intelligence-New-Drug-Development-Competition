import type { HarnessClient } from '../domain/contracts'
import { HttpHarnessClient } from './httpHarness'
import { MockHarnessClient } from './mockHarness'

// 실제 하네스가 앞에 서고, 닿지 않으면 고정 픽스처가 콘솔을 계속 띄웁니다.
const httpClient = new HttpHarnessClient(new MockHarnessClient())

export const harnessClient: HarnessClient = httpClient
export const isHarnessConnected = () => httpClient.isConnected
