import React from 'react';
import Header from '../Header/Header';
import styles from './About.module.css';

function About() {
  return (
    <>
      <Header activeTab="about" setActiveTab={() => {}} analysisDone={false} />
      <div className={styles.aboutContainer}>
        <h1>About Saul Goodman</h1>
        <section className={styles.section}>
          <h2>Proposed Solution: "Saul Goodman" - An AI-Powered CFO Assistant</h2>
          <p>
            Our project, "Saul Goodman," is an advanced AI-powered CFO assistant designed to deliver deep financial insights from annual reports and financial documents. Using a sophisticated multi-agent architecture built on LangGraph, our system ingests, analyzes, debates, and models financial data to provide comprehensive, actionable intelligence.
          </p>
        </section>
        <section className={styles.section}>
          <h2>How We Solve the Problem</h2>
          <h3>Data Ingestion & Parsing:</h3>
          <p>
            Our system handles both unstructured PDFs and structured Excel/CSV files.
          </p>
          <p>
            For PDFs, a smart "Table of Contents Agent" dynamically identifies the correct pages for key sections like "Financial Highlights" and "Management Discussion," making the analysis adaptable to any report format.
          </p>
          <p>
            This allows us to extract revenues, expenses, and other key performance metrics with high accuracy.
          </p>
          <h3>Financial Health Insights & Risk Awareness:</h3>
          <p>
            Instead of a single, flat summary, our core feature is a Multi-Agent "Boardroom" Debate.
          </p>
          <p>
            Three distinct AI personas—an Optimist (CEO), a Realist (CFO), and a Skeptic (Investor)—argue the strengths and weaknesses of the financial report, providing a balanced, 360-degree view.
          </p>
          <p>
            This approach naturally surfaces red flags, risks like discrepancies between adjusted and GAAP metrics, and hidden inefficiencies.
          </p>
          <h3>Explainability & Communication:</h3>
          <p>
            The debate format is a powerful form of Explainable AI, showing the user how a conclusion was reached by presenting conflicting viewpoints based on the data.
          </p>
          <p>
            All outputs are delivered in plain language, and a professionally formatted, downloadable Word Document provides a clear, auditable trail of the analysis.
          </p>
          <h3>Forecasting and Scenario Planning:</h3>
          <p>
            The "Scenario Simulator" tab transforms the tool from a static reporter into an interactive financial modeling assistant.
          </p>
          <p>
            Users can ask "what-if" questions in a natural language chat, and a specialized ScenarioAgent provides immediate, data-driven calculations on the potential impact of strategic decisions.
          </p>
        </section>
        <section className={styles.section}>
          <h2>What Makes Our Project Unique?</h2>
          <h3>Multi-Persona AI Debate (Beyond Summarization):</h3>
          <p>
            While other projects will summarize the data, ours brings it to life. The AI-driven debate between a CEO, CFO, and Investor provides a far deeper and more nuanced analysis, revealing insights that a simple summary would miss.
          </p>
          <h3>Interactive "What-If" Simulator (Dynamic, Not Static):</h3>
          <p>
            Our application is not just a one-time report generator; it's a conversational tool. The ability for users to engage with a financial modeling agent to test hypotheses and explore scenarios is a massive leap in functionality and user engagement.
          </p>
          <h3>Adaptive PDF Analysis (Robust and Flexible):</h3>
          <p>
            Our "Table of Contents Agent" makes our PDF analysis incredibly robust. Unlike hardcoded systems that will fail on new documents, our project can intelligently adapt to the structure of any annual report, making it a far more practical and professional tool.
          </p>
        </section>
        <section className={styles.section}>
          <h2>Team</h2>
          <ul className={styles.teamList}>
            {/* <li><a href="https://www.linkedin.com/in/jangraxmohit/" target="_blank" rel="noopener noreferrer">Mohit</a></li> */}
            <li><a href="https://www.linkedin.com/in/dewansh-jha-1a0917295/" target="_blank" rel="noopener noreferrer">Dewansh Jha</a></li>
            {/* <li><a href="https://www.linkedin.com/in/vineet-sood-82bb23297/" target="_blank" rel="noopener noreferrer">Vineet Sood</a></li>
            <li><a href="https://www.linkedin.com/in/ankush-chaudhary-758017277/" target="_blank" rel="noopener noreferrer">Ankush Chaudhary</a></li> */}
          </ul>
        </section>
      </div>
    </>
  );
}
export default About;