import { expect, test } from '@playwright/test'

test('login locale persists and password reset flow is reachable', async ({ page }) => {
  await page.goto('/login')
  await page.locator('.language-select .el-select__wrapper').click()
  await page.getByText('English', { exact: true }).last().click()

  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  await expect(page.getByText('Remember me', { exact: true })).toBeVisible()
  await page.getByText('Remember me', { exact: true }).click()
  await expect(page.locator('.el-checkbox')).toHaveClass(/is-checked/)

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => localStorage.getItem('app_locale'))).toBe('en')

  await page.goto('/reset-password?uid=test-user&token=test-token')
  await expect(page.getByRole('heading', { name: 'Reset Password' })).toBeVisible()
  await expect(page.getByPlaceholder('New password', { exact: true })).toBeVisible()
  await expect(page.getByPlaceholder('Confirm new password', { exact: true })).toBeVisible()
  await expect(page.locator('body')).not.toHaveCSS('overflow-x', 'scroll')
})
