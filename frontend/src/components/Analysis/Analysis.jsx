import React, { useState } from 'react';
import styles from './Analysis.module.css';
import heroBanner from '../../assets/wallpaper2.jpg';

function Analysis({ file, setFile, analysisResult, setAnalysisResult, setError, setActiveTab }) {
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [currentNode, setCurrentNode] = useState('');
  
  // SEC Audit State
  const [secAlerts, setSecAlerts] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setAnalysisResult(null);
    setSecAlerts('');
    setError('');
    setCurrentNode('');
  };

  const handleAnalyzeStream = async () => {
    if (!file) { setError('Please select a case file first.'); return; }
    setIsLoading(true);
    setError('');
    setSecAlerts('');
    
    // Initialize empty state to hold the incoming stream
    setAnalysisResult({ debate: [], final_summary: '', cleaned_data: '', company_name: '' });
    setCurrentNode('Initializing secure connection...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      // We use fetch and read the stream manually because EventSource doesn't support POST with files
      const response = await fetch('http://127.0.0.1:8000/analyze-stream', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let partialData = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = (partialData + chunk).split('\n\n');
          partialData = lines.pop(); // Keep the last incomplete chunk

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (!dataStr) continue;
              
              try {
                const data = JSON.parse(dataStr);

                if (data.node === 'error') {
                  setError(`Error: ${data.message}`);
                  setIsLoading(false);
                  return;
                }

                // Update what the AI is currently thinking about
                const formattedNodeName = data.node.replace('_', ' ').toUpperCase();
                setCurrentNode(`Agent Active: ${formattedNodeName}`);

                // Update the UI state progressively
                setAnalysisResult(prev => {
                  const updated = { ...prev };
                  if (data.company_name) updated.company_name = data.company_name;
                  if (data.kpis) updated.cleaned_data = data.kpis;
                  if (data.summary) updated.final_summary = data.summary;
                  
                  // Only add new debate entries to the array
                  if (data.latest_debate && !updated.debate.includes(data.latest_debate)) {
                     updated.debate = [...updated.debate, data.latest_debate];
                  }
                  return updated;
                });

              } catch (err) {
                console.error("Stream parse error:", err, dataStr);
              }
            }
          }
        }
      }
      setCurrentNode('Analysis Complete.');
      setIsLoading(false);
    } catch (e) {
      setError('Connection lost. The feds might have tapped the line.');
      console.error(e);
      setIsLoading(false);
    }
  };

  const handleSecAudit = async () => {
    if (!analysisResult?.company_name) return;
    setIsAuditing(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: analysisResult.company_name }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const result = await response.json();
      setSecAlerts(result.compliance_alerts);
    } catch (e) {
      setError('Failed to run SEC Audit.');
    } finally {
      setIsAuditing(false);
    }
  };

  const handleDownload = async () => {
    if (!analysisResult) return;
    setIsDownloading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/download_report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...analysisResult, filename: file.name }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `Saul_Goodman_Dossier_${analysisResult.company_name || 'Report'}.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      setError('Document shredder jammed. Could not download.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className={styles.container}>
      <img src={heroBanner} alt="Saul Goodman banner" className={styles.heroBanner} />

      <div className={styles.uploaderSection}>
        <h2>The War Room</h2>
        <p>Upload a target's financial filings. Let the boys tear it apart.</p>
        
        <label htmlFor="file-upload" className={styles.fileInputLabel}>
          {file ? `📄 ${file.name}` : '📁 Drop Case File Here'}
        </label>
        <input id="file-upload" type="file" onChange={handleFileChange} accept=".pdf,.xlsx,.csv" className={styles.fileInput} />
        
        <div className={styles.buttonContainer}>
          <button onClick={handleAnalyzeStream} disabled={isLoading || isDownloading || !file} className={styles.actionButton}>
            {isLoading ? 'Executing RAG Pipeline...' : 'Commence Analysis'}
          </button>
        </div>
        
        {/* Live LangGraph Node Tracker */}
        {isLoading && (
          <div className={styles.statusTracker}>
            <div className={styles.spinner}></div>
            <span>{currentNode}</span>
          </div>
        )}
      </div>
      
      {analysisResult && analysisResult.debate.length > 0 && (
        <div className={styles.resultsContainer}>
          
          <div className={styles.toolbar}>
             <button onClick={() => setActiveTab('simulator')} className={styles.navButton}>
               Go to Simulator →
             </button>
             <button onClick={() => setActiveTab('benchmark')} className={styles.navButton}>
               Market Benchmark →
             </button>
             <button onClick={handleSecAudit} disabled={isAuditing} className={styles.auditButton}>
               {isAuditing ? 'Auditing...' : '🚨 Run SEC Compliance Audit'}
             </button>
             <button onClick={handleDownload} disabled={isDownloading} className={styles.downloadButton}>
               {isDownloading ? 'Printing...' : '📄 Export Word Dossier'}
             </button>
          </div>

          {secAlerts && (
            <div className={styles.secBox}>
              <h3>🚨 SEC / Compliance Alerts</h3>
              <pre className={styles.preTag}>{secAlerts}</pre>
            </div>
          )}

          <h3>Boardroom Transcript: {analysisResult.company_name || 'Identifying...'}</h3>
          <div className={styles.chatContainer}>
            {analysisResult.debate.map((msg, index) => (
              <div key={index} className={styles.chatBubble}>
                {/* Simple logic to bold the speaker's name */}
                {msg.split(':').map((part, i) => 
                  i === 0 ? <strong key={i} style={{color: 'var(--primary-orange)'}}>{part}:</strong> : part
                )}
              </div>
            ))}
            {isLoading && <div className={styles.typingIndicator}>An agent is typing...</div>}
          </div>

          {analysisResult.final_summary && (
            <div className={styles.summary}>
              <h3>Final Verdict</h3>
              <pre className={styles.preTag}>{analysisResult.final_summary}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Analysis;