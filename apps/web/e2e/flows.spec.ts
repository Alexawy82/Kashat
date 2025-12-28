// Placeholder E2E smoke test (non-executing in CI unless configured)
import { test, expect } from '@playwright/test'

test.describe('End-to-End Flows', () => {
  test('Recurring: suggest → approve → confirmed shows', async ({ page, request }) => {
    await page.goto('/recurring')
    // Try to trigger suggestions via API as a fallback to speed up
    await request.post('/api/recurring/suggest')
    await page.reload()
    // Approve first pending if present
    const approve = page.locator('text=Approve').first()
    if (await approve.count()) {
      await approve.click()
      await expect(page.locator('text=Series approved')).toBeVisible()
    }
  })

  test('Transfers: suggest → approve → toggle include', async ({ page, request }) => {
    await page.goto('/transfers')
    await request.post('/api/transfers/suggest_v2')
    await page.reload()
    const approve = page.locator('text=Approve').first()
    if (await approve.count()) {
      await approve.click()
      await expect(page.locator('text=Transfer approved')).toBeVisible()
    }
    // Toggle include if a checkbox exists
    const toggles = page.locator('input[type="checkbox"]').filter({ hasText: '' })
    if (await toggles.count()) {
      await toggles.first().check({ force: true })
      await expect(page.locator('text=Included in analytics')).toBeVisible()
    }
  })

  test('Data Management: upload → list → summary → delete', async ({ page }) => {
    await page.goto('/settings/data-management')
    // Upload two small CSV sample files
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles(['data/fixtures/sample_bank.csv', 'data/fixtures/sample_bank2.csv'])
    await page.getByText('Upload').click()
    // Wait for toast
    await expect(page.locator('text=Files uploaded')).toBeVisible()
    // Select first run in list
    const runItem = page.locator('div[style*="cursor:"] >> nth=0')
    if (await runItem.count()) {
      await runItem.click()
      await expect(page.getByText('Files')).toBeVisible()
      await expect(page.getByText('Story by Month')).toBeVisible()
      // Delete with confirm
      page.on('dialog', async (dialog) => {
        await dialog.accept()
      })
      await page.getByText('Delete').click()
      await expect(page.locator('text=Run deleted')).toBeVisible()
    }
  })
})
