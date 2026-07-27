import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page, type TestInfo } from '@playwright/test'

async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByPlaceholder('邮箱地址').fill('admin@demo.com')
  await page.getByPlaceholder('密码').fill('admin123456')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/)
}

async function assertAccessible(page: Page, testInfo: TestInfo, label: string): Promise<void> {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  const blocking = result.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious',
  )
  await testInfo.attach(`axe-${label}.json`, {
    body: JSON.stringify(result.violations, null, 2),
    contentType: 'application/json',
  })
  expect(blocking, `${label} 存在严重 WCAG 违规`).toEqual([])
}

test('公共门户通过 WCAG 2.1 A/AA 严重项扫描', async ({ page }, testInfo) => {
  await page.goto('/public')
  await expect(page.locator('main, [role="main"]').first()).toBeVisible()
  await assertAccessible(page, testInfo, 'public')
})

test('核心认证工作台通过 WCAG 2.1 A/AA 严重项扫描', async ({ page }, testInfo) => {
  await loginAsAdmin(page)
  const routes = [
    ['/dashboard', 'dashboard'],
    ['/projects', 'projects'],
    ['/tasks', 'tasks'],
    ['/files', 'files'],
    ['/finance', 'finance'],
    ['/reports', 'reports'],
    ['/analytics-studio', 'analytics-studio'],
    ['/admin/platform-capabilities', 'platform-capabilities'],
    ['/admin/engineering', 'engineering-console'],
    ['/admin/users', 'admin-users'],
  ] as const

  for (const [route, label] of routes) {
    await page.goto(route)
    await expect(page.locator('main, .main-content, .mobile-content').first()).toBeVisible()
    await assertAccessible(page, testInfo, label)
  }
})
