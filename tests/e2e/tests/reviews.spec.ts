import { test, expect } from '@playwright/test';
import { AuthHelper, ReviewHelper, WaitHelper } from '../helpers';

test.describe('Review History', () => {
  let authHelper: AuthHelper;
  let reviewHelper: ReviewHelper;
  let waitHelper: WaitHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    reviewHelper = new ReviewHelper(page);
    waitHelper = new WaitHelper(page);

    await authHelper.login('admin', 'admin123');
  });

  test('should display reviews page', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await expect(page.locator('h1')).toContainText('Reviews');
    await expect(page.locator('[data-testid="status-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="repository-filter"]')).toBeVisible();
  });

  test('should filter reviews by status', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await reviewHelper.filterByStatus('success');

    await waitHelper.waitForNoLoadingSpinner();

    // All visible reviews should have success status
    const statusBadges = page.locator('[data-testid="status-badge"]');
    const count = await statusBadges.count();

    for (let i = 0; i < count; i++) {
      await expect(statusBadges.nth(i)).toContainText('Success');
    }
  });

  test('should filter reviews by repository', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await reviewHelper.filterByRepository('test-repo');

    await waitHelper.waitForNoLoadingSpinner();

    // All visible reviews should be from test-repo
    const repoNames = page.locator('[data-testid="repository-name"]');
    const count = await repoNames.count();

    for (let i = 0; i < count; i++) {
      await expect(repoNames.nth(i)).toContainText('test-repo');
    }
  });

  test('should view review details', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    const firstReview = page.locator('tbody tr').first();
    await firstReview.click();

    await expect(page.locator('[data-testid="review-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="pr-number"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-content"]')).toBeVisible();
  });

  test('should display review metadata', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.locator('tbody tr').first().click();

    await expect(page.locator('[data-testid="created-at"]')).toBeVisible();
    await expect(page.locator('[data-testid="duration"]')).toBeVisible();
    await expect(page.locator('[data-testid="token-count"]')).toBeVisible();
  });

  test('should search reviews', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.fill('input[placeholder*="Search"]', 'PR-123');

    await waitHelper.waitForNoLoadingSpinner();

    await expect(page.locator('text=PR-123')).toBeVisible();
  });

  test('should paginate through reviews', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    const pagination = page.locator('[data-testid="pagination"]');
    await expect(pagination).toBeVisible();

    const nextButton = page.locator('[data-testid="next-page"]');
    await nextButton.click();

    await waitHelper.waitForNoLoadingSpinner();

    // URL should update with page parameter
    await expect(page).toHaveURL(/page=2/);
  });

  test('should sort reviews by date', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.click('th:has-text("Date")');

    await waitHelper.waitForNoLoadingSpinner();

    // Should sort in descending order (newest first)
    const dates = await page.locator('[data-testid="review-date"]').allTextContents();
    const timestamps = dates.map(d => new Date(d).getTime());

    for (let i = 1; i < timestamps.length; i++) {
      expect(timestamps[i]).toBeLessThanOrEqual(timestamps[i - 1]);
    }
  });

  test('should export reviews', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.click('[data-testid="export-button"]');
    await page.click('[data-value="csv"]');

    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.csv');
  });

  test('should display review statistics', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await expect(page.locator('[data-testid="total-reviews"]')).toBeVisible();
    await expect(page.locator('[data-testid="success-rate"]')).toBeVisible();
    await expect(page.locator('[data-testid="average-duration"]')).toBeVisible();
  });

  test('should handle empty state', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    // Filter by non-existent repository
    await reviewHelper.filterByRepository('non-existent-repo');

    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
    await expect(page.locator('text=No reviews found')).toBeVisible();
  });

  test('should refresh review list', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    const refreshButton = page.locator('[data-testid="refresh-button"]');
    await refreshButton.click();

    await waitHelper.waitForNoLoadingSpinner();

    await expect(page.locator('tbody')).toBeVisible();
  });

  test('should display review errors', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await reviewHelper.filterByStatus('failed');

    const firstFailedReview = page.locator('tbody tr').first();
    await firstFailedReview.click();

    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });

  test('should copy review content', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.locator('tbody tr').first().click();

    await page.click('[data-testid="copy-button"]');

    await waitHelper.waitForToast('Copied to clipboard');
  });

  test('should filter by date range', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.click('[data-testid="date-range-filter"]');
    await page.fill('input[name="start"]', '2026-04-01');
    await page.fill('input[name="end"]', '2026-04-22');
    await page.click('[data-testid="apply-filter"]');

    await waitHelper.waitForNoLoadingSpinner();

    // All reviews should be within date range
    const dates = await page.locator('[data-testid="review-date"]').allTextContents();
    dates.forEach(dateStr => {
      const date = new Date(dateStr);
      expect(date.getTime()).toBeGreaterThanOrEqual(new Date('2026-04-01').getTime());
      expect(date.getTime()).toBeLessThanOrEqual(new Date('2026-04-22').getTime());
    });
  });

  test('should display review diff', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    await page.locator('tbody tr').first().click();

    await page.click('[data-testid="view-diff-button"]');

    await expect(page.locator('[data-testid="diff-viewer"]')).toBeVisible();
    await expect(page.locator('.diff-line')).toHaveCount({ min: 1 });
  });

  test('should handle keyboard navigation', async ({ page }) => {
    await reviewHelper.navigateToReviews();

    const firstRow = page.locator('tbody tr').first();
    await firstRow.focus();

    // Press Enter to open details
    await page.keyboard.press('Enter');

    await expect(page.locator('[data-testid="review-details"]')).toBeVisible();

    // Press Escape to close
    await page.keyboard.press('Escape');

    await expect(page.locator('[data-testid="review-details"]')).not.toBeVisible();
  });
});
