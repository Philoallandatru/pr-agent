import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Repositories from '../pages/Repositories';
import { AuthProvider } from '../contexts/AuthContext';

// Mock API client
vi.mock('../api/client', () => ({
  getRepositories: vi.fn(),
  createRepository: vi.fn(),
  updateRepository: vi.fn(),
  deleteRepository: vi.fn(),
}));

describe('Repositories Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders repositories list', async () => {
    const { getRepositories } = require('../api/client');

    getRepositories.mockResolvedValue([
      { id: 1, name: 'Test Repo 1', project_key: 'TEST', repo_slug: 'repo1', enabled: true },
      { id: 2, name: 'Test Repo 2', project_key: 'TEST', repo_slug: 'repo2', enabled: false },
    ]);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Repositories />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Repo 1')).toBeInTheDocument();
      expect(screen.getByText('Test Repo 2')).toBeInTheDocument();
    });
  });

  it('opens add repository dialog', async () => {
    const user = userEvent.setup();
    const { getRepositories } = require('../api/client');

    getRepositories.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <AuthProvider>
          <Repositories />
        </AuthProvider>
      </BrowserRouter>
    );

    const addButton = screen.getByRole('button', { name: /add/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/add repository/i)).toBeInTheDocument();
    });
  });

  it('creates new repository', async () => {
    const user = userEvent.setup();
    const { getRepositories, createRepository } = require('../api/client');

    getRepositories.mockResolvedValue([]);
    createRepository.mockResolvedValue({
      id: 3,
      name: 'New Repo',
      project_key: 'NEW',
      repo_slug: 'new-repo',
      enabled: true,
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <Repositories />
        </AuthProvider>
      </BrowserRouter>
    );

    // Open dialog
    const addButton = screen.getByRole('button', { name: /add/i });
    await user.click(addButton);

    // Fill form
    await waitFor(() => {
      const nameInput = screen.getByLabelText(/name/i);
      const projectInput = screen.getByLabelText(/project/i);
      const slugInput = screen.getByLabelText(/slug/i);

      user.type(nameInput, 'New Repo');
      user.type(projectInput, 'NEW');
      user.type(slugInput, 'new-repo');
    });

    // Submit
    const submitButton = screen.getByRole('button', { name: /save/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(createRepository).toHaveBeenCalled();
    });
  });

  it('deletes repository with confirmation', async () => {
    const user = userEvent.setup();
    const { getRepositories, deleteRepository } = require('../api/client');

    getRepositories.mockResolvedValue([
      { id: 1, name: 'Test Repo', project_key: 'TEST', repo_slug: 'repo', enabled: true },
    ]);
    deleteRepository.mockResolvedValue({});

    render(
      <BrowserRouter>
        <AuthProvider>
          <Repositories />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Repo')).toBeInTheDocument();
    });

    // Click delete button
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    await user.click(deleteButton);

    // Confirm deletion
    await waitFor(() => {
      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      user.click(confirmButton);
    });

    await waitFor(() => {
      expect(deleteRepository).toHaveBeenCalledWith(1);
    });
  });
});
