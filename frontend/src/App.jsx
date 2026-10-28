import { useCallback, useEffect, useId, useMemo, useState } from 'react'

const SAMPLE_CODES = {
  calculate_total: {
    name: 'Sum of Items',
    code: `def calculate_total(items):
    total = 0
    for item in items:
        total += item
    return total`,
  },
  binary_search: {
    name: 'Binary Search',
    code: `def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1`,
  },
  is_palindrome: {
    name: 'Palindrome Check',
    code: `def is_palindrome(text: str) -> bool:
    cleaned = ''.join(c.lower() for c in text if c.isalnum())
    return cleaned == cleaned[::-1]`,
  },
  calculate_fibonacci: {
    name: 'Fibonacci Sequence',
    code: `def fibonacci(n: int) -> int:
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b`,
  },
}

const OUTPUT_OPTIONS = ['Both', 'Generate Docstring', 'Explain Code']

const OUTPUT_MODE_MAP = {
  Both: 'both',
  'Generate Docstring': 'docstring',
  'Explain Code': 'explain',
}

const initialResult = {
  docstring: '',
  explanation: '',
  generation_time_ms: null,
  model_name: '',
  device: '',
  mode: '',
  status: '',
}

// Support both relative Vite proxy (/api) and direct backend fallback
const API_BASE_URLS = ['', 'http://127.0.0.1:8000', 'http://localhost:8000']

async function requestApi(path, options = {}) {
  let lastError = null
  for (const base of API_BASE_URLS) {
    const url = `${base}${path}`
    try {
      const response = await fetch(url, options)
      if (response.ok) {
        return await response.json()
      }
      // If server returned structured error
      const errorJson = await response.json().catch(() => null)
      if (errorJson && errorJson.detail) {
        throw new Error(errorJson.detail)
      }
      throw new Error(`Server returned HTTP ${response.status}`)
    } catch (err) {
      lastError = err
      // If network error (cannot reach origin), try next URL candidate
      if (err.name === 'TypeError' || err.message.includes('Failed to fetch')) {
        continue
      }
      throw err
    }
  }
  throw lastError || new Error(`Could not connect to ${path}`)
}

function App() {
  const [theme, setTheme] = useState('dark')
  const [language, setLanguage] = useState('Python')
  const [outputMode, setOutputMode] = useState('Both')
  const [selectedSampleKey, setSelectedSampleKey] = useState('calculate_total')
  const [code, setCode] = useState(SAMPLE_CODES.calculate_total.code)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(initialResult)
  const [copyFeedback, setCopyFeedback] = useState('')
  const [backendStatus, setBackendStatus] = useState({
    connected: false,
    modelLoaded: false,
    checking: true,
    message: 'Checking CodeT5 model status...',
    device: 'cpu',
    mode: 'unknown',
  })

  const languageSelectId = useId()
  const outputModeSelectId = useId()
  const sampleSelectId = useId()

  const appClassName = useMemo(() => `app-shell ${theme}`, [theme])

  // Check backend model status on mount and poll
  const checkStatus = useCallback(async () => {
    try {
      const data = await requestApi('/api/model-status')
      setBackendStatus({
        connected: true,
        modelLoaded: Boolean(data.model_loaded),
        checking: false,
        message: data.message || 'Connected to CodeT5-50K',
        device: data.device || 'cpu',
        mode: data.mode || 'real-model',
      })
    } catch {
      setBackendStatus({
        connected: false,
        modelLoaded: false,
        checking: false,
        message: 'Backend server offline (run backend on port 8000)',
        device: 'unknown',
        mode: 'disconnected',
      })
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    const runAsyncCheck = async () => {
      try {
        const data = await requestApi('/api/model-status')
        if (!isCancelled) {
          setBackendStatus({
            connected: true,
            modelLoaded: Boolean(data.model_loaded),
            checking: false,
            message: data.message || 'Connected to CodeT5-50K',
            device: data.device || 'cpu',
            mode: data.mode || 'real-model',
          })
        }
      } catch {
        if (!isCancelled) {
          setBackendStatus({
            connected: false,
            modelLoaded: false,
            checking: false,
            message: 'Backend server offline (run backend on port 8000)',
            device: 'unknown',
            mode: 'disconnected',
          })
        }
      }
    }

    runAsyncCheck()
    const interval = setInterval(runAsyncCheck, 15000)

    return () => {
      isCancelled = true
      clearInterval(interval)
    }
  }, [])

  const handleSelectSample = (key) => {
    setSelectedSampleKey(key)
    if (SAMPLE_CODES[key]) {
      setCode(SAMPLE_CODES[key].code)
      setError('')
    }
  }

  const handleClear = () => {
    setCode('')
    setError('')
    setResult(initialResult)
  }

  const handleGenerate = async () => {
    const trimmed = code.trim()
    if (!trimmed) {
      setError('Please enter Python code before generating output.')
      return
    }

    setError('')
    setIsLoading(true)

    const apiMode = OUTPUT_MODE_MAP[outputMode] || 'both'

    try {
      const data = await requestApi('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: trimmed,
          output_mode: apiMode,
          language,
        }),
      })

      setResult({
        docstring: data.docstring || '',
        explanation: data.explanation || '',
        generation_time_ms: data.generation_time_ms ?? null,
        model_name: data.model_name || 'CodeT5-50K',
        device: data.device || 'cpu',
        mode: data.mode || 'real-model',
        status: data.status || 'Success',
      })

      // If backend responded, update connection status
      setBackendStatus((prev) => ({
        ...prev,
        connected: true,
        modelLoaded: Boolean(data.model_loaded),
        checking: false,
      }))
    } catch (requestError) {
      console.error('Generation error:', requestError)
      // If backend is unreachable, offer a helpful message
      if (!backendStatus.connected) {
        setError(
          'Cannot reach backend server. Please start the backend server with: python -m uvicorn backend.app.main:app --port 8000'
        )
      } else {
        setError(requestError.message || 'Something went wrong while generating the response.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = async (value, label) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopyFeedback(`${label} copied to clipboard!`)
      setTimeout(() => setCopyFeedback(''), 2500)
    } catch {
      window.alert(`Unable to copy ${label.toLowerCase()}.`)
    }
  }

  // Insert generated docstring directly into user code editor
  const handleInsertDocstring = () => {
    if (!result.docstring || !code) return

    // Find function signature line to insert docstring right after def line
    const lines = code.split('\n')
    const defIndex = lines.findIndex((line) => line.trim().startsWith('def '))

    if (defIndex !== -1) {
      // Find indentation of function body
      const defLine = lines[defIndex]
      const indentMatch = defLine.match(/^(\s*)/)
      const baseIndent = (indentMatch ? indentMatch[1] : '') + '    '

      // Indent docstring lines
      const docLines = result.docstring
        .split('\n')
        .map((l) => (l.trim() ? baseIndent + l : l))
        .join('\n')

      const updated = [
        ...lines.slice(0, defIndex + 1),
        docLines,
        ...lines.slice(defIndex + 1),
      ].join('\n')

      setCode(updated)
      setCopyFeedback('Docstring inserted into code!')
      setTimeout(() => setCopyFeedback(''), 2500)
    } else {
      // Prepend docstring to code
      setCode(`${result.docstring}\n\n${code}`)
      setCopyFeedback('Docstring prepended to code!')
      setTimeout(() => setCopyFeedback(''), 2500)
    }
  }

  // Handle Ctrl+Enter shortcut in textarea
  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleGenerate()
    }
  }

  // Determine status pill badge
  const statusBadge = useMemo(() => {
    if (backendStatus.checking) {
      return {
        className: 'status-pill status-checking',
        text: '🟡 Checking CodeT5 Model...',
      }
    }
    if (backendStatus.connected && backendStatus.modelLoaded) {
      return {
        className: 'status-pill status-ready',
        text: `🟢 CodeT5-50K Active (${backendStatus.device.toUpperCase()})`,
      }
    }
    if (backendStatus.connected && !backendStatus.modelLoaded) {
      return {
        className: 'status-pill status-fallback',
        text: '🟠 Model Initializing...',
      }
    }
    return {
      className: 'status-pill status-offline',
      text: '🔴 Backend Offline',
    }
  }, [backendStatus])

  return (
    <div className={appClassName}>
      <header className="topbar">
        <div className="brand-wrap">
          <div className="brand-mark" aria-hidden="true">C</div>
          <div>
            <div className="brand-title">CodeScribe AI</div>
            <div className="brand-subtitle">
              Intelligent docstrings & code explanations powered by <strong>CodeT5-50K</strong>
            </div>
          </div>
        </div>

        <div className="topbar-actions">
          <button
            type="button"
            className={statusBadge.className}
            onClick={checkStatus}
            title={`${backendStatus.message}. Click to re-check connection.`}
          >
            {statusBadge.text}
          </button>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
            aria-label="Toggle light and dark theme"
          >
            {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>
      </header>

      {/* Copy Toast feedback */}
      {copyFeedback && (
        <div className="toast-notification" role="status">
          ✓ {copyFeedback}
        </div>
      )}

      <main className="workspace">
        {/* Left Panel: Code Input */}
        <section className="panel control-panel">
          <div className="panel-header">
            <h2>Python Code Input</h2>
            <div className="inline-controls">
              <label htmlFor={sampleSelectId}>
                <span>Sample Code</span>
                <select
                  id={sampleSelectId}
                  value={selectedSampleKey}
                  onChange={(e) => handleSelectSample(e.target.value)}
                >
                  {Object.entries(SAMPLE_CODES).map(([key, item]) => (
                    <option key={key} value={key}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>

              <label htmlFor={languageSelectId}>
                <span>Language</span>
                <select
                  id={languageSelectId}
                  value={language}
                  onChange={(event) => setLanguage(event.target.value)}
                >
                  <option value="Python">Python</option>
                </select>
              </label>

              <label htmlFor={outputModeSelectId}>
                <span>Output Type</span>
                <select
                  id={outputModeSelectId}
                  value={outputMode}
                  onChange={(event) => setOutputMode(event.target.value)}
                >
                  {OUTPUT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="editor-wrapper">
            <textarea
              value={code}
              onChange={(event) => setCode(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Paste your Python function here... (e.g., def add(a, b): return a + b)"
              aria-label="Python code editor"
              spellCheck="false"
            />
            <div className="editor-footer">
              <span className="code-metrics">
                {code ? `${code.split('\n').length} lines • ${code.length} chars` : 'Empty editor'}
              </span>
              <span className="shortcut-hint">Tip: Press Ctrl + Enter to generate</span>
            </div>
          </div>

          <div className="button-row">
            <button
              type="button"
              className="secondary"
              onClick={() => handleSelectSample('calculate_total')}
            >
              Load Sample
            </button>
            <button type="button" className="secondary" onClick={handleClear}>
              Clear
            </button>
            <button
              type="button"
              className="primary"
              onClick={handleGenerate}
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="loading-label">
                  <span className="spinner" /> Generating with CodeT5...
                </span>
              ) : (
                'Generate Output'
              )}
            </button>
          </div>

          {error ? (
            <div className="error-message" role="alert">
              <strong>Error:</strong> {error}
              {!backendStatus.connected && (
                <div className="error-hint">
                  Make sure your FastAPI server is running with: <code>backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000</code>
                </div>
              )}
            </div>
          ) : null}
        </section>

        {/* Right Panel: Output Results */}
        <section className="panel output-panel">
          <div className="panel-header">
            <h2>Generated Results</h2>
            {result.generation_time_ms !== null && (
              <div className="metrics-badge" title="Model inference latency">
                ⚡ {result.generation_time_ms} ms &bull; {result.model_name}
              </div>
            )}
          </div>

          {isLoading ? (
            <div className="loading-state">
              <div className="pulse-loader" />
              <p>Analyzing code with fine-tuned <strong>CodeT5-50K</strong> model...</p>
              <span className="loading-subtext">Executing seq2seq generation with beam search</span>
            </div>
          ) : !result.docstring && !result.explanation ? (
            <div className="empty-state">
              <div className="empty-icon">✨</div>
              <p>
                Your AI-generated docstring or code explanation will render here in real-time.
              </p>
              <span className="empty-hint">
                Select a sample snippet or paste your own Python code, then click <strong>Generate Output</strong>.
              </span>
            </div>
          ) : (
            <div className="results-stack">
              {result.docstring ? (
                <div className="output-card">
                  <div className="output-card-header">
                    <div className="card-title-group">
                      <h3>Docstring Output</h3>
                      <span className="card-pill">CodeT5 Generated</span>
                    </div>
                    <div className="card-actions">
                      <button
                        type="button"
                        className="insert-btn"
                        onClick={handleInsertDocstring}
                        title="Insert docstring directly into your code in the editor"
                      >
                        Insert into Code
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCopy(result.docstring, 'Docstring')}
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                  <pre className="code-output">{result.docstring}</pre>
                </div>
              ) : null}

              {result.explanation ? (
                <div className="output-card">
                  <div className="output-card-header">
                    <div className="card-title-group">
                      <h3>Code Explanation</h3>
                      <span className="card-pill">Natural Language</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopy(result.explanation, 'Explanation')}
                    >
                      Copy
                    </button>
                  </div>
                  <div className="explanation-body">
                    {result.explanation.split('\n').map((line, idx) => {
                      if (line.startsWith('**') && line.endsWith('**')) {
                        return (
                          <h4 key={idx} className="expl-heading">
                            {line.replace(/\*\*/g, '')}
                          </h4>
                        )
                      }
                      if (line.startsWith('- ')) {
                        return (
                          <div key={idx} className="expl-list-item">
                            <span className="bullet">&bull;</span>
                            <span>{line.substring(2)}</span>
                          </div>
                        )
                      }
                      return line.trim() ? (
                        <p key={idx} className="expl-para">
                          {line}
                        </p>
                      ) : null
                    })}
                  </div>
                </div>
              ) : null}

              {result.status && (
                <div className="result-footer-status">
                  <span className="dot" />
                  <span>{result.status}</span>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
