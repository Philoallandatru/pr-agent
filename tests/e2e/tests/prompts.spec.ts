import { test, expect } from '@playwright/test';
import { AuthHelper, PromptHelper, WaitHelper } from '../helpers';

test.describe('Prompt Management', () => {
  let authHelper: AuthHelper;
  let promptHelper: PromptHelper;
  let waitHelper: WaitHelper;

  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page);
    promptHelper = new PromptHelper(page);
    waitHelper = new WaitHelper(page);

    await authHelper.login('admin', 'admin123');
  });

  test('should display prompts page', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await expect(page.locator('h1')).toContainText('Prompts');
    await expect(page.locator('[data-testid="prompt-list"]')).toBeVisible();
  });

  test('should list all available prompts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    // Should show default prompts
    await expect(page.locator('text=pr_reviewer')).toBeVisible();
    await expect(page.locator('text=code_suggestions')).toBeVisible();
    await expect(page.locator('text=describe')).toBeVisible();
  });

  test('should edit prompt content', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    const originalContent = await page.locator('[data-testid="prompt-pr_reviewer"]').textContent();

    await promptHelper.editPrompt('pr_reviewer', 'Updated prompt content for testing');

    await waitHelper.waitForToast('Saved successfully');

    const newContent = await page.locator('[data-testid="prompt-pr_reviewer"]').textContent();
    expect(newContent).not.toBe(originalContent);
  });

  test('should validate prompt content', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="edit-prompt-pr_reviewer"]');
    await page.fill('textarea[name="content"]', '');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Prompt content cannot be empty')).toBeVisible();
  });

  test('should reset prompt to default', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    // Edit prompt first
    await promptHelper.editPrompt('pr_reviewer', 'Custom content');

    // Reset to default
    await promptHelper.resetPrompt('pr_reviewer');

    await waitHelper.waitForToast('Reset successfully');

    // Should show default content
    const content = await page.locator('[data-testid="prompt-pr_reviewer"]').textContent();
    expect(content).toContain('Review the following pull request');
  });

  test('should preview prompt with variables', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="edit-prompt-pr_reviewer"]');

    // Add variables to prompt
    await page.fill('textarea[name="content"]', 'Review PR #{pr_number} in {repository}');

    await page.click('[data-testid="preview-button"]');

    // Fill preview variables
    await page.fill('input[name="pr_number"]', '123');
    await page.fill('input[name="repository"]', 'test-repo');

    await page.click('[data-testid="generate-preview"]');

    await expect(page.locator('[data-testid="preview-content"]')).toContainText('Review PR #123 in test-repo');
  });

  test('should search prompts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.fill('input[placeholder*="Search"]', 'reviewer');

    await expect(page.locator('text=pr_reviewer')).toBeVisible();
    await expect(page.locator('text=describe')).not.toBeVisible();
  });

  test('should display prompt metadata', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="prompt-pr_reviewer"]');

    await expect(page.locator('[data-testid="last-modified"]')).toBeVisible();
    await expect(page.locator('[data-testid="character-count"]')).toBeVisible();
    await expect(page.locator('[data-testid="token-estimate"]')).toBeVisible();
  });

  test('should handle concurrent edits', async ({ page, context }) => {
    await promptHelper.navigateToPrompts();

    // Open prompt in first tab
    await page.click('[data-testid="edit-prompt-pr_reviewer"]');

    // Open same prompt in second tab
    const page2 = await context.newPage();
    await new AuthHelper(page2).login('admin', 'admin123');
    await new PromptHelper(page2).navigateToPrompts();
    await page2.click('[data-testid="edit-prompt-pr_reviewer"]');

    // Edit in first tab
    await page.fill('textarea[name="content"]', 'First edit');
    await page.click('button[type="submit"]');

    // Try to edit in second tab
    await page2.fill('textarea[name="content"]', 'Second edit');
    await page2.click('button[type="submit"]');

    // Should show conflict warning
    await expect(page2.locator('text=Prompt was modified by another user')).toBeVisible();
  });

  test('should export prompts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="export-button"]');

    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');

    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('prompts');
    expect(download.suggestedFilename()).toContain('.json');
  });

  test('should import prompts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="import-button"]');

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'prompts.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({
        pr_reviewer: 'Imported prompt content'
      }))
    });

    await page.click('[data-testid="confirm-import"]');

    await waitHelper.waitForToast('Prompts imported successfully');

    const content = await page.locator('[data-testid="prompt-pr_reviewer"]').textContent();
    expect(content).toContain('Imported prompt content');
  });

  test('should validate imported file format', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="import-button"]');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'invalid.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('invalid content')
    });

    await page.click('[data-testid="confirm-import"]');

    await expect(page.locator('text=Invalid file format')).toBeVisible();
  });

  test('should create custom prompt', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="create-prompt-button"]');

    await page.fill('input[name="name"]', 'custom_prompt');
    await page.fill('textarea[name="content"]', 'This is a custom prompt');
    await page.click('button[type="submit"]');

    await waitHelper.waitForToast('Prompt created successfully');

    await expect(page.locator('text=custom_prompt')).toBeVisible();
  });

  test('should delete custom prompt', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    // Create custom prompt first
    await page.click('[data-testid="create-prompt-button"]');
    await page.fill('input[name="name"]', 'to_delete');
    await page.fill('textarea[name="content"]', 'Temporary prompt');
    await page.click('button[type="submit"]');

    // Delete it
    await page.click('[data-testid="delete-prompt-to_delete"]');
    await page.click('[data-testid="confirm-delete"]');

    await waitHelper.waitForToast('Prompt deleted successfully');

    await expect(page.locator('text=to_delete')).not.toBeVisible();
  });

  test('should not delete system prompts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    const deleteButton = page.locator('[data-testid="delete-prompt-pr_reviewer"]');

    // System prompts should not have delete button
    await expect(deleteButton).not.toBeVisible();
  });

  test('should syntax highlight prompt content', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="edit-prompt-pr_reviewer"]');

    const editor = page.locator('[data-testid="prompt-editor"]');

    // Should have syntax highlighting classes
    await expect(editor.locator('.syntax-variable')).toHaveCount({ min: 1 });
  });

  test('should auto-save prompt drafts', async ({ page }) => {
    await promptHelper.navigateToPrompts();

    await page.click('[data-testid="edit-prompt-pr_reviewer"]');

    await page.fill('textarea[name="content"]', 'Draft content');

    // Wait for auto-save
    await page.waitForTimeout(2000);

    await expect(page.locator('text=Draft saved')).toBeVisible();

    // Reload page
    await page.reload();

    await page.click('[data-testid="edit-prompt-pr_reviewer"]');

    // Should restore draft
    const content = await page.locator('textarea[name="content"]').inputValue();
    expect(content).toBe('Draft content');
  });
});
