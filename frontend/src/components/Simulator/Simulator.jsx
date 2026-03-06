import React, { useState } from 'react';
import styles from './Simulator.module.css';

function Simulator({ analysisResult, setError }) {
  const [chatQuery, setChatQuery] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [scenarioQuery, setScenarioQuery] = useState('');
  const [scenarioResponse, setScenarioResponse] = useState('');
  const [isScenarioLoading, setIsScenarioLoading] = useState(false);

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatQuery) return;
    setIsChatLoading(true);
    setChatResponse('');
    
    try {
      const response = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_query: chatQuery }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const result = await response.json();
      setChatResponse(result.response);
    } catch (e) {
      setError('Chat Error: Saul hung up the burner phone. Backend unreachable.');
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleScenarioSubmit = async (e) => {
    e.preventDefault();
    if (!scenarioQuery) return;
    setIsScenarioLoading(true);
    setScenarioResponse('');

    try {
      const response = await fetch('http://127.0.0.1:8000/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_context: analysisResult.final_summary,
          user_query: scenarioQuery,
          company_name: analysisResult.company_name,
          cleaned_data: analysisResult.cleaned_data
        }),
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const result = await response.json();
      setScenarioResponse(result.response);
    } catch (e) {
      setError('Scenario Error: Could not crunch the numbers.');
    } finally {
      setIsScenarioLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBox}>
        <h2>Step into Saul's Office</h2>
        <p>Run hypothetical financial scenarios, or interrogate your attorney directly.</p>
      </div>

      <div className={styles.grid}>
        {/* INTERROGATION ROOM */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.icon}>⚖️</span>
            <h3>The Interrogation Room</h3>
          </div>
          <p className={styles.subtitle}>Ask specific questions about the case file.</p>
          
          <form onSubmit={handleChatSubmit} className={styles.form}>
            <div className={styles.inputWrapper}>
              <input 
                type="text" 
                placeholder="e.g., Why did employee expenses spike?" 
                value={chatQuery} 
                onChange={(e) => setChatQuery(e.target.value)}
                className={styles.inputField}
              />
              <button type="submit" disabled={isChatLoading || !chatQuery} className={styles.actionButton}>
                {isChatLoading ? 'Dialing...' : 'Ask Saul'}
              </button>
            </div>
          </form>

          {chatResponse && (
            <div className={styles.responseBox}>
              <span className={styles.saulLabel}>Saul Goodman Says:</span>
              <p>{chatResponse}</p>
            </div>
          )}
        </div>

        {/* SCENARIO SIMULATOR */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <span className={styles.icon}>📈</span>
            <h3>"What-If" Simulator</h3>
          </div>
          <p className={styles.subtitle}>Test financial hypotheticals and predict impacts.</p>
          
          <form onSubmit={handleScenarioSubmit} className={styles.form}>
            <div className={styles.inputWrapper}>
              <input 
                type="text" 
                placeholder="e.g., What if revenue drops by 15% next year?" 
                value={scenarioQuery} 
                onChange={(e) => setScenarioQuery(e.target.value)}
                className={styles.inputField}
              />
              <button type="submit" disabled={isScenarioLoading || !scenarioQuery} className={styles.actionButton}>
                {isScenarioLoading ? 'Crunching...' : 'Run Model'}
              </button>
            </div>
          </form>

          {scenarioResponse && (
            <div className={styles.responseBox}>
              <span className={styles.modelLabel}>Financial Model Output:</span>
              <pre className={styles.preTag}>{scenarioResponse}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Simulator;