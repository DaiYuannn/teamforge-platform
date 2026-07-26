import { expect, test, type Page } from '@playwright/test'
import { stat } from 'node:fs/promises'

async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login')
  await page.getByPlaceholder('邮箱地址').fill(email)
  await page.getByPlaceholder('密码').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/)
}

async function primaryColor(page: Page): Promise<string> {
  return page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim().toLowerCase()
  )
}

test('账户偏好随登录账号切换', async ({ page }) => {
  await login(page, 'admin@demo.com', 'admin123456')
  await expect.poll(() => primaryColor(page)).toBe('#176b73')

  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  await login(page, 'teacher1@demo.com', 'teacher123456')
  await expect(page).toHaveURL(/\/projects(?:\?|$)/)
  await expect.poll(() => primaryColor(page)).toBe('#6f5a86')
})

test('核心工作台入口可用且使用中文业务标签', async ({ page }) => {
  await login(page, 'admin@demo.com', 'admin123456')

  await page.goto('/competitions')
  await expect(page.getByRole('heading', { name: '比赛管理' })).toBeVisible()
  await expect(page.getByText(/共\s*\d+\s*场比赛/)).toBeVisible()

  await page.goto('/finance')
  await expect(page.getByRole('button', { name: /票据 OCR/ })).toBeVisible()
  await page.getByRole('button', { name: /票据 OCR/ }).click()
  const ocrDialog = page.getByRole('dialog', { name: '票据 OCR 识别' })
  await expect(ocrDialog).toBeVisible()
  await ocrDialog.getByRole('button', { name: '取消', exact: true }).click()

  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: '定时报表' })).toBeVisible()

  await page.goto('/notifications')
  await expect(page.getByRole('heading', { name: '通知中心' })).toBeVisible()
  const notificationList = page.locator('.content-panel:visible, .mobile-list:visible')
  await expect(notificationList.getByText('定时报表已生成', { exact: true })).toBeVisible()
})

test('项目时间线不回退显示英文事件代码', async ({ page }) => {
  await login(page, 'admin@demo.com', 'admin123456')
  await page.goto('/projects')
  const firstProject = page.locator('button.project-name, button.mobile-project-title').first()
  await expect(firstProject).toBeVisible()
  await firstProject.click()
  await page.getByRole('button', { name: '时间线', exact: true }).click()
  await expect(page.getByRole('heading', { name: '项目时间线' })).toBeVisible()

  const timeline = page.locator('.project-timeline')
  await expect(timeline).toBeVisible()
  await expect(timeline).not.toContainText(
    /competition_result|competition_defense|task_completed|file_uploaded/
  )
  await expect(timeline.locator('.event-tag').first()).toBeVisible()
})

test('管理员可进入演示备份管理并下载有效数据包', async ({ page }, testInfo) => {
  await login(page, 'admin@demo.com', 'admin123456')
  await page.goto('/admin/backups')
  await expect(page.getByRole('heading', { name: /演示数据备份/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '生成备份包', exact: true })).toBeVisible()

  const downloadButton = page.locator('.backup-panel .el-table__body-wrapper tbody tr')
    .first()
    .getByRole('button', { name: '下载', exact: true })
  await expect(downloadButton).toBeEnabled()
  const downloadPromise = page.waitForEvent('download')
  await downloadButton.click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/\.zip$/i)
  const savedPath = testInfo.outputPath(download.suggestedFilename())
  await download.saveAs(savedPath)
  expect((await stat(savedPath)).size).toBeGreaterThan(0)
})
