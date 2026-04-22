import { test, expect } from '@playwright/test';
import { AuthHelper } from '../helpers';

test.describe('Authentication', () => {
  let authHelper: AuthHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
  });

  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    await expect(page.locator('h1')).toContainText('Login');
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await authHelper.login('admin', 'admin123');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/');

    // Should show user menu
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="username"]', 'invalid');
    await page.fill('input[name="password"]', 'wrong');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('[role="alert"]')).toContainText('Invalid credentials');

    // Should stay on login page
    await expect(page).toHaveURL('/login');
  });

  test('should logout successfully', async ({ page }) => {
    await authHelper.login('admin', 'admin123');
    await authHelper.logout();

    // Should redirect to login page
    await expect(page).toHaveURL('/login');

    // Should not show user menu
    await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    await page.goto('/repositories');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should remember user after page reload', async ({ page }) => {
    await authHelper.login('admin', 'admin123');

    // Reload page
    await page.reload();

    // Should still be logged in
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    await expect(page).toHaveURL('/');
  });

  test('should handle session expiration', async ({ page }) => {
    await authHelper.login('admin', 'admin123');

    // Clear local storage to simulate expired session
    await page.evaluate(() => localStorage.clear());

    // Try to access protected route
    await page.goto('/repositories');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/login');

    // Try to submit without filling fields
    await page.click('button[type="submit"]');

    // Should show validation errors
    await expect(page.locator('text=Username is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should toggle password visibility', async ({ page }) => {
    await page.goto('/login');

    const passwordInput = page.locator('input[name="password"]');
    const toggleButton = page.locator('[data-testid="toggle-password"]');

    // Initially should be password type
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle
    await toggleButton.click();

    // Should change to text type
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Click toggle again
    await toggleButton.click();

    // Should change back to password type
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('should handle keyboard navigation', async ({ page }) => {
    await page.goto('/login');

    // Tab through fields
    await page.keyboard.press('Tab');
    await expect(page.locator('input[name="username"]')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.locator('input[name="password"]')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.locator('button[type="submit"]')).toBeFocused();
  });

  test('should submit form with Enter key', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');

    // Press Enter in password field
    await page.locator('input[name="password"]').press('Enter');

    // Should login successfully
    await expect(page).toHaveURL('/');
  });
});
