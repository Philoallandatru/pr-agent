import { Page } from '@playwright/test';

/**
 * Helper class for authentication-related actions
 */
export class AuthHelper {
  constructor(private page: Page) {}

  async login(username: string, password: string) {
    await this.page.goto('/login');
    await this.page.fill('input[name="username"]', username);
    await this.page.fill('input[name="password"]', password);
    await this.page.click('button[type="submit"]');
    await this.page.waitForURL('/');
  }

  async logout() {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
    await this.page.waitForURL('/login');
  }

  async isLoggedIn(): Promise<boolean> {
    try {
      await this.page.waitForSelector('[data-testid="user-menu"]', { timeout: 2000 });
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * Helper class for repository-related actions
 */
export class RepositoryHelper {
  constructor(private page: Page) {}

  async navigateToRepositories() {
    await this.page.goto('/repositories');
    await this.page.waitForLoadState('networkidle');
  }

  async addRepository(name: string, url: string) {
    await this.page.click('[data-testid="add-repository-button"]');
    await this.page.fill('input[name="name"]', name);
    await this.page.fill('input[name="url"]', url);
    await this.page.click('button[type="submit"]');
    await this.page.waitForSelector(`text=${name}`);
  }

  async deleteRepository(name: string) {
    const row = this.page.locator(`tr:has-text("${name}")`);
    await row.locator('[data-testid="delete-button"]').click();
    await this.page.click('[data-testid="confirm-delete"]');
    await this.page.waitForSelector(`text=${name}`, { state: 'detached' });
  }

  async searchRepository(query: string) {
    await this.page.fill('input[placeholder*="Search"]', query);
    await this.page.waitForTimeout(500); // Debounce
  }

  async getRepositoryCount(): Promise<number> {
    const rows = await this.page.locator('tbody tr').count();
    return rows;
  }
}

/**
 * Helper class for review-related actions
 */
export class ReviewHelper {
  constructor(private page: Page) {}

  async navigateToReviews() {
    await this.page.goto('/reviews');
    await this.page.waitForLoadState('networkidle');
  }

  async filterByStatus(status: string) {
    await this.page.click('[data-testid="status-filter"]');
    await this.page.click(`[data-value="${status}"]`);
    await this.page.waitForLoadState('networkidle');
  }

  async filterByRepository(repository: string) {
    await this.page.click('[data-testid="repository-filter"]');
    await this.page.click(`text=${repository}`);
    await this.page.waitForLoadState('networkidle');
  }

  async viewReviewDetails(prNumber: number) {
    await this.page.click(`[data-testid="review-${prNumber}"]`);
    await this.page.waitForSelector('[data-testid="review-details"]');
  }

  async getReviewCount(): Promise<number> {
    const rows = await this.page.locator('tbody tr').count();
    return rows;
  }
}

/**
 * Helper class for prompt-related actions
 */
export class PromptHelper {
  constructor(private page: Page) {}

  async navigateToPrompts() {
    await this.page.goto('/prompts');
    await this.page.waitForLoadState('networkidle');
  }

  async editPrompt(name: string, content: string) {
    await this.page.click(`[data-testid="edit-prompt-${name}"]`);
    await this.page.fill('textarea[name="content"]', content);
    await this.page.click('button[type="submit"]');
    await this.page.waitForSelector('text=Saved successfully');
  }

  async resetPrompt(name: string) {
    await this.page.click(`[data-testid="reset-prompt-${name}"]`);
    await this.page.click('[data-testid="confirm-reset"]');
    await this.page.waitForSelector('text=Reset successfully');
  }
}

/**
 * Helper class for analytics-related actions
 */
export class AnalyticsHelper {
  constructor(private page: Page) {}

  async navigateToDashboard() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async selectDateRange(start: string, end: string) {
    await this.page.click('[data-testid="date-range-picker"]');
    await this.page.fill('input[name="start"]', start);
    await this.page.fill('input[name="end"]', end);
    await this.page.click('[data-testid="apply-date-range"]');
    await this.page.waitForLoadState('networkidle');
  }

  async exportReport(format: 'pdf' | 'csv' | 'json') {
    await this.page.click('[data-testid="export-button"]');
    await this.page.click(`[data-value="${format}"]`);
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.click('[data-testid="confirm-export"]');
    const download = await downloadPromise;
    return download;
  }

  async getMetricValue(metric: string): Promise<string> {
    const element = await this.page.locator(`[data-testid="metric-${metric}"]`);
    return await element.textContent() || '';
  }
}

/**
 * Helper class for API interactions
 */
export class ApiHelper {
  constructor(private page: Page) {}

  async createAuthToken(): Promise<string> {
    const response = await this.page.request.post('/api/auth/token', {
      data: {
        username: 'admin',
        password: 'admin123'
      }
    });
    const data = await response.json();
    return data.access_token;
  }

  async makeAuthenticatedRequest(
    method: string,
    endpoint: string,
    token: string,
    data?: any
  ) {
    return await this.page.request.fetch(endpoint, {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data
    });
  }
}

/**
 * Wait for specific conditions
 */
export class WaitHelper {
  constructor(private page: Page) {}

  async waitForApiResponse(urlPattern: string | RegExp) {
    return await this.page.waitForResponse(urlPattern);
  }

  async waitForNoLoadingSpinner() {
    await this.page.waitForSelector('[data-testid="loading-spinner"]', {
      state: 'detached',
      timeout: 10000
    });
  }

  async waitForToast(message?: string) {
    if (message) {
      await this.page.waitForSelector(`[role="alert"]:has-text("${message}")`);
    } else {
      await this.page.waitForSelector('[role="alert"]');
    }
  }
}
