import { test, expect } from '@playwright/test';
import { AuthHelper, RepositoryHelper, WaitHelper } from '../helpers';

test.describe('Repository Management', () => {
  let authHelper: AuthHelper;
  let repoHelper: RepositoryHelper;
  let waitHelper: WaitHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    repoHelper = new RepositoryHelper(page);
    waitHelper = new WaitHelper(page);

    // Login before each test
    await authHelper.login('admin', 'admin123');
  });

  test('should display repositories page', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await expect(page.locator('h1')).toContainText('Repositories');
    await expect(page.locator('[data-testid="add-repository-button"]')).toBeVisible();
  });

  test('should add new repository', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    const initialCount = await repoHelper.getRepositoryCount();

    await repoHelper.addRepository('test-repo', 'https://github.com/test/repo.git');

    await waitHelper.waitForToast('Repository added successfully');

    const newCount = await repoHelper.getRepositoryCount();
    expect(newCount).toBe(initialCount + 1);

    await expect(page.locator('text=test-repo')).toBeVisible();
  });

  test('should validate repository URL', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await page.click('[data-testid="add-repository-button"]');
    await page.fill('input[name="name"]', 'invalid-repo');
    await page.fill('input[name="url"]', 'not-a-valid-url');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Invalid repository URL')).toBeVisible();
  });

  test('should search repositories', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    // Add test repositories
    await repoHelper.addRepository('frontend-app', 'https://github.com/test/frontend.git');
    await repoHelper.addRepository('backend-api', 'https://github.com/test/backend.git');

    // Search for "frontend"
    await repoHelper.searchRepository('frontend');

    await expect(page.locator('text=frontend-app')).toBeVisible();
    await expect(page.locator('text=backend-api')).not.toBeVisible();
  });

  test('should delete repository', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('to-delete', 'https://github.com/test/delete.git');

    const initialCount = await repoHelper.getRepositoryCount();

    await repoHelper.deleteRepository('to-delete');

    await waitHelper.waitForToast('Repository deleted successfully');

    const newCount = await repoHelper.getRepositoryCount();
    expect(newCount).toBe(initialCount - 1);

    await expect(page.locator('text=to-delete')).not.toBeVisible();
  });

  test('should display repository details', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('detail-test', 'https://github.com/test/detail.git');

    await page.click('text=detail-test');

    await expect(page.locator('[data-testid="repository-details"]')).toBeVisible();
    await expect(page.locator('text=https://github.com/test/detail.git')).toBeVisible();
  });

  test('should edit repository settings', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('edit-test', 'https://github.com/test/edit.git');

    const row = page.locator('tr:has-text("edit-test")');
    await row.locator('[data-testid="edit-button"]').click();

    await page.fill('input[name="name"]', 'edited-repo');
    await page.click('button[type="submit"]');

    await waitHelper.waitForToast('Repository updated successfully');

    await expect(page.locator('text=edited-repo')).toBeVisible();
    await expect(page.locator('text=edit-test')).not.toBeVisible();
  });

  test('should enable/disable repository monitoring', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('monitor-test', 'https://github.com/test/monitor.git');

    const row = page.locator('tr:has-text("monitor-test")');
    const toggleSwitch = row.locator('[data-testid="monitoring-toggle"]');

    // Initially should be enabled
    await expect(toggleSwitch).toBeChecked();

    // Disable monitoring
    await toggleSwitch.click();
    await waitHelper.waitForToast('Monitoring disabled');

    await expect(toggleSwitch).not.toBeChecked();

    // Enable monitoring
    await toggleSwitch.click();
    await waitHelper.waitForToast('Monitoring enabled');

    await expect(toggleSwitch).toBeChecked();
  });

  test('should display repository statistics', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('stats-test', 'https://github.com/test/stats.git');

    await page.click('text=stats-test');

    await expect(page.locator('[data-testid="total-prs"]')).toBeVisible();
    await expect(page.locator('[data-testid="reviewed-prs"]')).toBeVisible();
    await expect(page.locator('[data-testid="pending-prs"]')).toBeVisible();
  });

  test('should handle pagination', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    // Add multiple repositories
    for (let i = 1; i <= 15; i++) {
      await repoHelper.addRepository(`repo-${i}`, `https://github.com/test/repo-${i}.git`);
    }

    // Should show pagination controls
    await expect(page.locator('[data-testid="pagination"]')).toBeVisible();

    // Go to next page
    await page.click('[data-testid="next-page"]');

    // Should show different repositories
    await expect(page.locator('text=repo-11')).toBeVisible();
  });

  test('should sort repositories', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('zebra-repo', 'https://github.com/test/zebra.git');
    await repoHelper.addRepository('alpha-repo', 'https://github.com/test/alpha.git');

    // Click name column header to sort
    await page.click('th:has-text("Name")');

    // First row should be alpha-repo
    const firstRow = page.locator('tbody tr').first();
    await expect(firstRow).toContainText('alpha-repo');

    // Click again to reverse sort
    await page.click('th:has-text("Name")');

    // First row should be zebra-repo
    await expect(firstRow).toContainText('zebra-repo');
  });

  test('should handle duplicate repository names', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    await repoHelper.addRepository('duplicate', 'https://github.com/test/dup1.git');

    await page.click('[data-testid="add-repository-button"]');
    await page.fill('input[name="name"]', 'duplicate');
    await page.fill('input[name="url"]', 'https://github.com/test/dup2.git');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Repository name already exists')).toBeVisible();
  });

  test('should refresh repository list', async ({ page }) => {
    await repoHelper.navigateToRepositories();

    const refreshButton = page.locator('[data-testid="refresh-button"]');
    await refreshButton.click();

    await waitHelper.waitForNoLoadingSpinner();

    // Should show updated data
    await expect(page.locator('tbody')).toBeVisible();
  });
});
