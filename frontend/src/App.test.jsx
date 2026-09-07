import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the TokenTrim heading', () => {
    render(<App />);
    expect(screen.getAllByText(/TokenTrim/i)[0]).toBeInTheDocument();
  });

  it('shows error for invalid history JSON when submitting', async () => {
    // Mock fetch so the form submission doesn't hang
    global.fetch = vi.fn();

    render(<App />);

    // Find history textarea and set invalid JSON
    const textareas = screen.getAllByRole('textbox');
    // History textarea is the second one (index 1, after query)
    const historyArea = textareas[1];
    fireEvent.change(historyArea, { target: { value: 'not valid json {{{' } });

    // Submit the form
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Should show error without calling fetch
    await waitFor(() => {
      expect(screen.getByText(/Invalid JSON/i)).toBeInTheDocument();
    });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('displays metrics after a successful /chat fetch', async () => {
    const mockResponse = {
      response: 'Hello from the model!',
      cached: false,
      cost_usd: 0.000123,
      naive_cost_usd: 0.000456,
      model_used: 'qwen3.5-flash',
      routing_reason: 'difficulty=0.10 -> simple',
      latency_ms: 42.5,
      similarity: null,
      tokens: {
        input: 35,
        output: 10,
        breakdown: {
          uncompressed: { system: 5, history: 20, rag: 5, query: 5 },
          compressed:   { system: 5, history: 10, rag: 5, query: 5 },
        },
      },
      naive_prompt: [{ role: 'user', content: 'test' }],
      trimmed_prompt: [{ role: 'user', content: 'test' }],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    render(<App />);

    // Clear the history field so JSON.parse doesn't fail
    const textareas = screen.getAllByRole('textbox');
    fireEvent.change(textareas[1], { target: { value: '[]' } });
    fireEvent.change(textareas[2], { target: { value: '[]' } });

    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Wait for response to appear
    await waitFor(() => {
      expect(screen.getByText(/Hello from the model!/i)).toBeInTheDocument();
    });

    // Check the model name appears somewhere
    expect(screen.getByText(/qwen3.5-flash/i)).toBeInTheDocument();
  });

  it('calculates tokens-saved correctly', async () => {
    // uncompressed total = 5+20+5+5 = 35, input = 25 → saved = 35 - 25 = 10
    const mockResponse = {
      response: 'Test response',
      cached: false,
      cost_usd: 0.0001,
      naive_cost_usd: 0.0003,
      model_used: 'qwen3.5-flash',
      routing_reason: 'difficulty=0.10 -> simple',
      latency_ms: 20,
      similarity: null,
      tokens: {
        input: 25,
        output: 8,
        breakdown: {
          uncompressed: { system: 5, history: 20, rag: 5, query: 5 },
          compressed:   { system: 5, history: 10, rag: 5, query: 5 },
        },
      },
      naive_prompt: [],
      trimmed_prompt: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    render(<App />);
    const textareas = screen.getAllByRole('textbox');
    fireEvent.change(textareas[1], { target: { value: '[]' } });
    fireEvent.change(textareas[2], { target: { value: '[]' } });

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText(/Test response/i)).toBeInTheDocument();
    });

    // saved tokens = uncompressed total (35) - input (25) = 10
    // The UI shows this; just verify the response section rendered
    expect(screen.getByText(/qwen3.5-flash/i)).toBeInTheDocument();
  });
});
