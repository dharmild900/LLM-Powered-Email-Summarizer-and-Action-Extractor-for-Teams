import { useState } from 'react';
import axios from 'axios';

export default function App() {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const summarize = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post('/api/summarize', { subject, body });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: 'Arial, sans-serif' }}>
      <h1>Enterprise Email Summarizer</h1>
      <div style={{ marginBottom: 12 }}>
        <input value={subject} onChange={e => setSubject(e.target.value)} placeholder="Subject" style={{ width: 800, padding: 8 }} />
      </div>
      <div>
        <textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Email body" style={{ width: 800, height: 200, padding: 8 }} />
      </div>
      <div style={{ marginTop: 12 }}>
        <button onClick={summarize} disabled={loading} style={{ padding: '8px 16px' }}>{loading ? 'Working...' : 'Summarize'}</button>
      </div>
      {error && <div style={{ color: 'red', marginTop: 12 }}>{error}</div>}
      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>Summary</h3>
          <p>{result.summary}</p>
          <h4>Actions</h4>
          <ul>{result.actions?.map((a,i) => <li key={i}>{a}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
