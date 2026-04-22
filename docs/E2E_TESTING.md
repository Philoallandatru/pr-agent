# End-to-End Testing Guide

This guide explains how to run and write E2E tests for PR Agent using Playwright.

## Overview

The E2E test suite covers:
- **Authentication**: Login, logout, session management
- **Repository Management**: CRUD operations, search, filtering
- **Review History**: Viewing, filtering, exporting reviews
- **Prompt Management**: Editing, resetting, importing/exporting prompts
- **Dashboard**: Analytics and metrics visualization

## Prerequisites

Install dependencies:

```bash
cd tests/e2e
npm install
npx playwright install
```

## Running Tests

### Run all tests

```bash
npm test
```

### Run tests in headed mode (see browser)

```bash
npm run test:headed
```

### Run tests in UI mode (interactive)

```bash
npm run test:ui
```

### Run specific test file

```bash
npx playwright test tests/auth.spec.ts
```

### Run tests in specific browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Debug tests

```bash
npm run test:debug
```

### View test report

```bash
npm run test:report
```

## Test Structure

### Test Files

```
tests/e2e/
├── helpers/
│   └── index.ts           # Helper classes for common actions
├── tests/
│   ├── auth.spec.ts       # Authentication tests
│   ├── repositories.spec.ts # Repository management tests
│   ├── reviews.spec.ts    # Review history tests
│   └── prompts.spec.ts    # Prompt management tests
├── playwright.config.ts   # Playwright configuration
└── package.json
```

### Helper Classes

The test suite includes helper classes for common operations:

**AuthHelper**:
```typescript
const authHelper = new AuthHelper(page);
await authHelper.login('admin', 'admin123');
await authHelper.logout();
```

**RepositoryHelper**:
```typescript
const repoHelper = new RepositoryHelper(page);
await repoHelper.addRepository('test-repo', 'https://github.com/test/repo.git');
await repoHelper.deleteRepository('test-repo');
```

**ReviewHelper**:
```typescript
const reviewHelper = new ReviewHelper(page);
await reviewHelper.filterByStatus('success');
await reviewHelper.viewReviewDetails(123);
```

**PromptHelper**:
```typescript
const promptHelper = new PromptHelper(page);
await promptHelper.editPrompt('pr_reviewer', 'New content');
await promptHelper.resetPrompt('pr_reviewer');
```

**WaitHelper**:
```typescript
const waitHelper = new WaitHelper(page);
await waitHelper.waitForToast('Success message');
await waitHelper.waitForNoLoadingSpinner();
```

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { AuthHelper } from '../helpers';

test.describe('Feature Name', () => {
  let authHelper: AuthHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    await authHelper.login('admin', 'admin123');
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await page.goto('/some-page');

    // Act
    await page.click('button');

    // Assert
    await expect(page.locator('text=Success')).toBeVisible();
  });
});
```

### Best Practices

1. **Use data-testid attributes**:
```typescript
// Good
await page.click('[data-testid="submit-button"]');

// Avoid
await page.click('button.btn-primary');
```

2. **Wait for network idle**:
```typescript
await page.goto('/page');
await page.waitForLoadState('networkidle');
```

3. **Use explicit waits**:
```typescript
await expect(page.locator('text=Success')).toBeVisible();
```

4. **Clean up after tests**:
```typescript
test.afterEach(async ({ page }) => {
  // Clean up test data
  await deleteTestData();
});
```

5. **Use fixtures for common setup**:
```typescript
test.use({
  storageState: 'auth.json' // Reuse authentication
});
```

## Test Data Management

### Using Test Fixtures

Create reusable test data:

```typescript
// fixtures/test-data.ts
export const testRepositories = [
  { name: 'repo-1', url: 'https://github.com/test/repo-1.git' },
  { name: 'repo-2', url: 'https://github.com/test/repo-2.git' }
];
```

### Cleaning Up Test Data

```typescript
test.afterEach(async ({ page }) => {
  // Delete test repositories
  await page.goto('/repositories');
  const testRepos = page.locator('tr:has-text("test-")');
  const count = await testRepos.count();
  
  for (let i = 0; i < count; i++) {
    await testRepos.first().locator('[data-testid="delete-button"]').click();
    await page.click('[data-testid="confirm-delete"]');
  }
});
```

## Authentication State

### Save Authentication State

```typescript
// auth.setup.ts
import { test as setup } from '@playwright/test';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="username"]', 'admin');
  await page.fill('input[name="password"]', 'admin123');
  await page.click('button[type="submit"]');
  
  await page.context().storageState({ path: 'auth.json' });
});
```

### Use Saved Authentication

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: 'auth.json'
      },
      dependencies: ['setup']
    }
  ]
});
```

## Visual Testing

### Take Screenshots

```typescript
test('visual regression', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveScreenshot('dashboard.png');
});
```

### Compare Screenshots

Playwright automatically compares screenshots and fails if they differ.

Update baseline screenshots:
```bash
npx playwright test --update-snapshots
```

## Accessibility Testing

### Check Accessibility

```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('should not have accessibility violations', async ({ page }) => {
  await page.goto('/');
  
  const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
  
  expect(accessibilityScanResults.violations).toEqual([]);
});
```

## Performance Testing

### Measure Page Load Time

```typescript
test('page load performance', async ({ page }) => {
  const startTime = Date.now();
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  const loadTime = Date.now() - startTime;
  
  expect(loadTime).toBeLessThan(3000); // 3 seconds
});
```

## CI/CD Integration

### GitHub Actions

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd tests/e2e
        npm ci
        npx playwright install --with-deps
    
    - name: Start application
      run: |
        docker-compose up -d
        sleep 10
    
    - name: Run tests
      run: |
        cd tests/e2e
        npm test
    
    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: playwright-report
        path: tests/e2e/playwright-report/
```

## Debugging

### Debug Mode

```bash
npm run test:debug
```

This opens the Playwright Inspector where you can:
- Step through tests
- Inspect elements
- View console logs
- Record new tests

### Trace Viewer

View traces for failed tests:

```bash
npx playwright show-trace trace.zip
```

### Console Logs

Capture console logs:

```typescript
page.on('console', msg => console.log(msg.text()));
```

### Network Logs

Monitor network requests:

```typescript
page.on('request', request => {
  console.log('>>', request.method(), request.url());
});

page.on('response', response => {
  console.log('<<', response.status(), response.url());
});
```

## Troubleshooting

### Tests Timing Out

Increase timeout:

```typescript
test('slow test', async ({ page }) => {
  test.setTimeout(60000); // 60 seconds
  // ...
});
```

### Flaky Tests

Use retry:

```typescript
// playwright.config.ts
export default defineConfig({
  retries: 2
});
```

### Element Not Found

Use explicit waits:

```typescript
await page.waitForSelector('[data-testid="element"]', {
  state: 'visible',
  timeout: 10000
});
```

### Authentication Issues

Clear storage state:

```typescript
await page.context().clearCookies();
await page.context().clearPermissions();
```

## Best Practices

1. **Independent Tests**: Each test should be independent and not rely on other tests
2. **Descriptive Names**: Use clear, descriptive test names
3. **Page Objects**: Use helper classes to encapsulate page interactions
4. **Wait Strategies**: Use explicit waits instead of arbitrary timeouts
5. **Test Data**: Use unique test data to avoid conflicts
6. **Clean Up**: Always clean up test data after tests
7. **Assertions**: Use meaningful assertions with clear error messages
8. **Parallelization**: Run tests in parallel when possible
9. **Screenshots**: Take screenshots on failure for debugging
10. **Documentation**: Document complex test scenarios

## See Also

- [Playwright Documentation](https://playwright.dev/)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
- [API Testing Guide](./API_TESTING.md)
- [Performance Testing Guide](./PERFORMANCE_TESTING.md)
