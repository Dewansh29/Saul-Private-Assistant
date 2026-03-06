import React, { useState } from 'react';
import styles from './Benchmark.module.css';

function Benchmark({ analysisResult, setError }) {
  const [competitorName, setCompetitorName] = useState('');
  const [benchmarkResult, setBenchmarkResult] = useState('');
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  const handleBenchmarkClick = async (e) => {
    e.preventDefault();
    if (!analysisResult || !competitorName) return;
    
    setIsBenchmarking(true);
    setError('');
    setBenchmarkResult('');

    try {
      const response = await fetch('http://127.0.0.1:8000/benchmark', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: analysisResult.company_name,
          cleaned_data: analysisResult.cleaned_data,
          competitor_name: competitorName // Passing the competitor!
        }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const result = await response.json();
      setBenchmarkResult(result.response);
    } catch (e) {
      setError('An error occurred during benchmark analysis. Check the backend console.');
      console.error(e);
    } finally {
      setIsBenchmarking(false);
    }
  };

  return (
    <div className={styles.container}>
      <h2>Market Benchmarking</h2>
      <p>Compare {analysisResult.company_name} against a direct competitor.</p>
      
      <form onSubmit={handleBenchmarkClick} style={{display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem'}}>
        <input 
          type="text" 
          placeholder="Enter Competitor Name (e.g., Swiggy)" 
          value={competitorName}
          onChange={(e) => setCompetitorName(e.target.value)}
          style={{padding: '0.75rem', borderRadius: '8px', border: '1px solid #30363d', background: '#161b22', color: '#e1e4e8', width: '300px'}}
        />
        <button type="submit" disabled={isBenchmarking || !competitorName} style={{padding: '0.75rem 1.5rem', background: '#ff9900', color: '#24292e', borderRadius: '8px', fontWeight: 'bold', border: 'none', cursor: 'pointer'}}>
          {isBenchmarking ? 'Analyzing...' : 'Run Benchmark'}
        </button>
      </form>

      {isBenchmarking && <p className={styles.loadingMessage}>Running ruthless competitor analysis...</p>}

      {benchmarkResult && (
        <div className={styles.resultContainer}>
          <pre className={styles.preTag}>{benchmarkResult}</pre>
        </div>
      )}
    </div>
  );
}

export default Benchmark;