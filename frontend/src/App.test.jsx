import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('CodeScribe AI app', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url) => {
        if (url.includes('/api/model-status')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                model_loaded: true,
                mode: 'real-model',
                mock_mode: false,
                trained_model_connected: true,
                message: 'CodeT5-50K model is active and running on CPU.',
                model_dir: 'D:/CodeScribe-Ai/CodeT5_50K_Final',
                device: 'cpu',
              }),
          })
        }
        if (url.includes('/api/generate')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                mode: 'real-model',
                mock_mode: false,
                model_loaded: true,
                output_mode: 'both',
                docstring: '"""Calculate the total of all items in a list.\n"""',
                explanation: '**Purpose:** Calculate the total of all items in a list.',
                status: 'Real CodeT5-50K inference completed successfully.',
                generation_time_ms: 124.5,
                model_name: 'CodeT5-50K (Fine-Tuned)',
                device: 'cpu',
              }),
          })
        }
        return Promise.reject(new Error(`Unhandled URL: ${url}`))
      })
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the product header and live CodeT5 status badge', async () => {
    render(<App />)

    expect(screen.getByText('CodeScribe AI')).toBeInTheDocument()
    expect(
      screen.getByText(/Intelligent docstrings & code explanations powered by/i)
    ).toBeInTheDocument()
    expect(await screen.findByText(/CodeT5-50K Active/i)).toBeInTheDocument()
  })

  it('shows validation when trying to generate empty code', async () => {
    const user = userEvent.setup()
    render(<App />)

    const clearButton = screen.getByRole('button', { name: 'Clear' })
    await user.click(clearButton)

    const generateButton = screen.getByRole('button', { name: 'Generate Output' })
    await user.click(generateButton)

    expect(
      screen.getByText('Please enter Python code before generating output.')
    ).toBeInTheDocument()
  })

  it('loads the sample Python function into the editor', async () => {
    const user = userEvent.setup()
    render(<App />)

    const sampleButton = screen.getByRole('button', { name: 'Load Sample' })
    await user.click(sampleButton)

    const editor = screen.getByLabelText('Python code editor')
    expect(editor.value).toContain('def calculate_total(items):')
  })

  it('generates real CodeT5 output and renders docstring & explanation cards', async () => {
    const user = userEvent.setup()
    render(<App />)

    const generateButton = screen.getByRole('button', { name: 'Generate Output' })
    await user.click(generateButton)

    expect(await screen.findByText('Docstring Output')).toBeInTheDocument()
    expect(await screen.findByText('Code Explanation')).toBeInTheDocument()
    expect(
      screen.getAllByText(/Calculate the total of all items/i).length
    ).toBeGreaterThanOrEqual(1)
  })
})
