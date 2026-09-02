import { useState } from 'react'

function StackedBar({ data, label }) {
  if (!data) return null;
  const total = data.system + data.history + data.rag + data.query;
  if (total === 0) return null;

  const sysP = (data.system / total) * 100;
  const histP = (data.history / total) * 100;
  const ragP = (data.rag / total) * 100;
  const queryP = (data.query / total) * 100;

  return (
    <div className="bar-row">
      <div className="bar-label">{label} ({total} tks)</div>
      <div className="bar-track">
        {sysP > 0 && <div className="bar-segment segment-system" style={{ width: `${sysP}%` }}>{sysP > 10 ? 'SYS' : ''}</div>}
        {histP > 0 && <div className="bar-segment segment-history" style={{ width: `${histP}%` }}>{histP > 10 ? 'HIST' : ''}</div>}
        {ragP > 0 && <div className="bar-segment segment-rag" style={{ width: `${ragP}%` }}>{ragP > 10 ? 'RAG' : ''}</div>}
        {queryP > 0 && <div className="bar-segment segment-query" style={{ width: `${queryP}%` }}>{queryP > 10 ? 'QRY' : ''}</div>}
      </div>
    </div>
  );
}

function PromptView({ title, promptArray }) {
  return (
    <div className="prompt-view">
      <div className="prompt-header">{title}</div>
      <div className="prompt-body">
        {promptArray && promptArray.map((msg, idx) => (
          <div key={idx} className="message-block">
            <span className="role">{msg.role.toUpperCase()}</span>
            {msg.content}
          </div>
        ))}
        {(!promptArray || promptArray.length === 0) && (
          <div style={{ color: 'var(--text-muted)' }}>No data to display.</div>
        )}
      </div>
    </div>
  );
}

function App() {
  const [query, setQuery] = useState("How does this optimization work?");
  const [history, setHistory] = useState("[\n  {\"role\": \"user\", \"content\": \"Hello, can you explain TokenTrim?\"},\n  {\"role\": \"assistant\", \"content\": \"Sure, it compresses context to save money.\"}\n]");
  const [rag, setRag] = useState("[\n  \"TokenTrim is a middleware that intercepts calls to Alibaba Cloud models.\",\n  \"It uses Semantic Caching and Context Compression to reduce prompt sizes.\"\n]");
  
  const [skipCache, setSkipCache] = useState(true);
  const [skipCompression, setSkipCompression] = useState(false);
  const [forceTier, setForceTier] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    let parsedHistory = [];
    let parsedRag = [];
    
    try {
      if (history.trim()) parsedHistory = JSON.parse(history);
      if (rag.trim()) parsedRag = JSON.parse(rag);
    } catch (e) {
      setError("Invalid JSON in History or RAG fields.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          history: parsedHistory,
          rag_chunks: parsedRag,
          skip_cache: skipCache,
          skip_compression: skipCompression,
          forced_tier: forceTier || null
        })
      });
      
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const tokens = result?.tokens;
  const breakdown = tokens?.breakdown;
  const saved = tokens ? Math.max(0, tokens.breakdown.uncompressed.system + tokens.breakdown.uncompressed.history + tokens.breakdown.uncompressed.rag + tokens.breakdown.uncompressed.query - tokens.input) : 0;

  return (
    <div className="app-container">
      <header>
        <h1>TokenTrim visualizer</h1>
        <div>Optimizer UI</div>
      </header>
      
      <div className="main-content">
        <div className="panel" style={{ flex: '0 0 350px' }}>
          <div className="panel-header">Request Controls</div>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>User Query</label>
              <textarea 
                rows={3} 
                value={query} 
                onChange={e => setQuery(e.target.value)}
                placeholder="Ask a question..."
              />
            </div>
            
            <div className="form-group">
              <label>History (JSON array of role/content)</label>
              <textarea 
                rows={5} 
                value={history} 
                onChange={e => setHistory(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
              />
            </div>
            
            <div className="form-group">
              <label>RAG Chunks (JSON array of strings)</label>
              <textarea 
                rows={5} 
                value={rag} 
                onChange={e => setRag(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
              />
            </div>

            <div className="panel-header" style={{ marginTop: '2rem', fontSize: '1rem' }}>Interventions</div>
            
            <div className="checkbox-group">
              <input type="checkbox" id="skipCache" checked={skipCache} onChange={e => setSkipCache(e.target.checked)} />
              <label htmlFor="skipCache">Bypass Semantic Cache</label>
            </div>
            
            <div className="checkbox-group">
              <input type="checkbox" id="skipComp" checked={skipCompression} onChange={e => setSkipCompression(e.target.checked)} />
              <label htmlFor="skipComp">Bypass Context Compression</label>
            </div>
            
            <div className="form-group">
              <label>Force Model Tier</label>
              <input type="text" value={forceTier} onChange={e => setForceTier(e.target.value)} placeholder="e.g. qwen-max" />
            </div>
            
            {error && <div style={{ color: 'var(--accent-red)', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
            
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Sending...' : 'Send Request'}
            </button>
          </form>
        </div>
        
        <div className="panel" style={{ background: 'rgba(15, 23, 42, 0.4)' }}>
          {result ? (
            <>
              <div className="analytics-card">
                <div className="panel-header" style={{ marginBottom: '1rem' }}>Optimization Analytics</div>
                
                <div className="metrics-grid">
                  <div className="metric-box">
                    <div className="metric-label">Tokens Sent</div>
                    <div className="metric-value">{tokens?.input}</div>
                  </div>
                  <div className="metric-box">
                    <div className="metric-label">Tokens Saved</div>
                    <div className="metric-value positive">{saved}</div>
                  </div>
                  <div className="metric-box">
                    <div className="metric-label">Model Used</div>
                    <div className="metric-value" style={{ fontSize: '1.1rem', color: 'var(--accent-blue)', marginTop: '0.4rem' }}>
                      {result.model_used}
                    </div>
                  </div>
                </div>

                {breakdown && (
                  <div className="bar-chart-container">
                    <StackedBar data={breakdown.uncompressed} label="Naive Payload" />
                    <StackedBar data={breakdown.compressed} label="Trimmed Payload" />
                    
                    <div className="legend">
                      <div className="legend-item"><div className="legend-color segment-system"></div> System</div>
                      <div className="legend-item"><div className="legend-color segment-history"></div> History</div>
                      <div className="legend-item"><div className="legend-color segment-rag"></div> RAG</div>
                      <div className="legend-item"><div className="legend-color segment-query"></div> Query</div>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="diff-container">
                <PromptView title="Naive Prompt (Uncompressed)" promptArray={result.naive_prompt} />
                <PromptView title="TokenTrim Prompt (Sent to API)" promptArray={result.trimmed_prompt} />
              </div>
              
              <div className="prompt-view" style={{ flex: 'none', minHeight: '150px' }}>
                <div className="prompt-header">Assistant Response</div>
                <div className="prompt-body" style={{ color: '#e2e8f0', fontFamily: 'inherit', fontSize: '0.95rem' }}>
                  {result.response}
                </div>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
              Submit a request to see the visual diff and optimization analytics.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
