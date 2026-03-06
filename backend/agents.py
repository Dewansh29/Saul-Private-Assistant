import fitz  # PyMuPDF
import os
from typing import Dict, Any, List
import pandas as pd
import json
from langgraph.graph import StateGraph, END
from rag_engine import retriever
# --- LOCAL LLM IMPORT ---
from langchain_ollama import OllamaLLM

# --- ENSURE THIS IMPORT IS CORRECT ---
from utils import extract_tables_from_pdf, extract_text_from_pdf, extract_data_from_excel, process_excel_data

# --- SETUP LOCAL MODELS ---
# We use a low temperature for strict data extraction, and a higher one for the debate.
llm_strict = OllamaLLM(model="llama3.2", temperature=0.0)
llm_creative = OllamaLLM(model="llama3.2", temperature=0.6)



# --- AGENT STATE ---
class AgentState(dict):
    raw_file_bytes: bytes
    filename: str
    company_name: str = "The Company"
    table_of_contents: str = ""
    key_pages: Dict = {}
    extracted_tables: Dict[int, List[pd.DataFrame]] = None
    extracted_text: str = ""
    structured_data: Dict[str, pd.DataFrame] = None
    financial_kpis: Dict = {}
    cleaned_data: str = ""
    debate: List[str] = []
    final_summary: str = ""
    deep_dive_analysis: Dict = {}
    user_query: str = ""
    scenario_response: str = ""
    analysis_context: str = ""
    benchmark_analysis: str = ""

# --- AGENT NODE DEFINITIONS ---

def ingestion_agent(state: AgentState) -> AgentState:
    print("---EXECUTING INGESTION AGENT---")
    file_bytes = state['raw_file_bytes']
    filename = state.get('filename', '')

    if filename.endswith('.pdf'):
        state['table_of_contents'] = extract_text_from_pdf(file_bytes, page_numbers=list(range(1, 10)))
    elif filename.endswith(('.xlsx', '.xls', '.csv')):
        state['structured_data'] = extract_data_from_excel(file_bytes, filename)
    else:
        state['cleaned_data'] = "Error: Unsupported file type."
    print("---INGESTION COMPLETE---")
    return state

def toc_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING FLEXIBLE TABLE OF CONTENTS AGENT---")
    prompt = f"""
    You are an expert at reading a Table of Contents from an annual report. From the text below, identify the starting page numbers for the following sections. Prioritize finding 'Financial Statements' or 'Standalone Financial Statements'. If not found, look for 'Board's Report' or 'Management Discussion'.
    Return ONLY a valid JSON object. No explanations. No extra text.
    Example: {{"financial_statements": 31, "boards_report": 8}}
    
    Table of Contents Text:
    ---
    {state['table_of_contents'][:6000]}
    ---
    """
    try:
        response = llm_strict.invoke(prompt)
        cleaned_response = response.strip().replace("```json", "").replace("```", "")
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            cleaned_response = cleaned_response[start_idx:end_idx]
            
        state['key_pages'] = json.loads(cleaned_response)
        print(f"---KEY PAGES IDENTIFIED: {state['key_pages']}---")
    except Exception as e:
        print(f"Error parsing ToC JSON: {e}. Using default page ranges.")
        state['key_pages'] = {}
    return state

def pdf_extraction_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING FULL PDF RAG INGESTION AGENT---")
    file_bytes = state['raw_file_bytes']
    company_name = state.get('company_name', 'The Company')

    print("Extracting full document text for Vector DB (CPU)...")
    pages_data = []
    full_text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            full_text += text + "\n"
            # Save the text WITH its specific page number
            pages_data.append({"page_num": page_num + 1, "text": text})
        doc.close()
        
        state['extracted_text'] = full_text
        
        # Feed the structured page data into ChromaDB
        retriever.ingest_pages(pages_data, company_name)
    except Exception as e:
        print(f"Error extracting full PDF: {e}")
        
    return state

def pdf_analysis_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING RAG-POWERED KPI EXTRACTION AGENT---")
    
    queries = [
        "What is the Revenue from operations and Total Income?",
        "What are the Total Expenses and Employee benefit expenses?",
        "What is the Profit before tax and Profit for the year (Net Profit)?",
        "What are the Total Assets, Total Liabilities, and Total Equity?",
        "What are the Cash and cash equivalents?"
    ]
    
    rag_context = ""
    print("Querying ChromaDB for financial metrics...")
    for q in queries:
        rag_context += retriever.hybrid_search(q, top_k=2) + "\n\n"
        
    safe_context = rag_context[:10000] 

    prompt = f"""
    You are a meticulous financial analyst. Your sole task is to extract key financial metrics from the provided RAG database context.

    CRITICAL DATA EXTRACTION RULES:
    1. UNIVERSAL UNIT STANDARDIZATION: Financial reports use varying scales (Absolute, Thousands, Millions, Billions). You must autonomously identify the scale from the surrounding text/headers. Mathematically convert ALL extracted numbers into standard ABSOLUTE values before outputting (e.g., if the text says 5.2 and the context implies 'in billions', you must output 5200000000).
    2. STRICT ANTI-HALLUCINATION: You are forbidden from guessing, estimating, or calculating values. Only extract numbers explicitly printed in the text.
    3. MISSING DATA: If a specific metric cannot be confidently found in the provided context, you MUST set its value to null. Do not force a fit.

    Metrics to extract (output as absolute numbers):
    - Revenue from operations
    - Total Income
    - Total Expenses
    - Profit before tax
    - Profit for the year (Net Profit)
    - Total Assets
    - Total Liabilities
    - Total Equity
    - Employee benefit expenses
    - Cash and cash equivalents

    Return ONLY a valid JSON object matching the exact keys above. Do not include any text, explanations, or markdown formatting outside the JSON.

    RAG DATABASE CONTEXT:
    ---
    {safe_context}
    ---
    """

    try:
        response = llm_strict.invoke(prompt)
        cleaned_response = response.strip().replace("```json", "").replace("```", "")
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            cleaned_response = cleaned_response[start_idx:end_idx]
            
        kpis = json.loads(cleaned_response)
        state['financial_kpis'] = kpis
        state['cleaned_data'] = json.dumps(kpis, indent=2)
        print("---RAG KPI EXTRACTION COMPLETE---")
        print(state['cleaned_data'])
    except Exception as e:
        print(f"Error extracting KPIs from RAG context: {e}")
        state['cleaned_data'] = "Error: Could not extract structured financial data."
        state['financial_kpis'] = {}
    return state

def company_identifier_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING COMPANY IDENTIFIER AGENT---")
    
    if state.get('extracted_text'):
        prompt = f"From the following text, identify and return ONLY the main company's name. Example: 'Capgemini Technology Services India Limited'.\n\nTEXT:\n{state['extracted_text'][:2000]}"
        try:
            response = llm_strict.invoke(prompt)
            identified_name = response.strip()
            if 3 < len(identified_name) < 100 and '\n' not in identified_name:
                state['company_name'] = identified_name
                print(f"---COMPANY IDENTIFIED FROM TEXT: {state['company_name']}---")
                return state
        except Exception:
            pass

    filename = state.get('filename', '')
    if filename.endswith(('.xlsx', '.xls', '.csv')):
        company_name = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
        state['company_name'] = company_name
        print(f"---COMPANY IDENTIFIED FROM FILENAME: {state['company_name']}---")
        return state

    pdf_bytes = state['raw_file_bytes']
    cover_pages_text = extract_text_from_pdf(pdf_bytes, page_numbers=[1, 2, 3])
    prompt = f"From the following text from a report's cover page, identify and return ONLY the main company's name.\n\nTEXT:\n{cover_pages_text}"
    try:
        response = llm_strict.invoke(prompt)
        identified_name = response.strip()
        if 3 < len(identified_name) < 100 and '\n' not in identified_name:
            state['company_name'] = identified_name
        else:
            state['company_name'] = "The Company"
        print(f"---COMPANY IDENTIFIED FROM COVER: {state['company_name']}---")
    except Exception as e:
        print(f"Could not identify company name, using default. Error: {e}")
        state['company_name'] = "The Company"
    return state

def structured_data_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING BULLETPROOF STRUCTURED DATA AGENT---")
    structured_data = state.get('structured_data')
    if not structured_data:
        state['cleaned_data'] = "Error: No structured data found."
        state['financial_kpis'] = {}
        return state

    relevant_text = process_excel_data(structured_data)[:10000]
    
    prompt = f"""
    You are a meticulous financial analyst. Your task is to extract key financial metrics from the text below.
    Return ONLY a valid JSON object. No explanations outside the JSON.

    Metrics to extract (all values should be in millions):
    - Revenue from operations
    - Total Income
    - Total Expenses
    - Profit before tax
    - Profit for the year (Net Profit)
    - Total Assets
    - Total Liabilities
    - Total Equity
    - Employee benefit expenses
    - Cash and cash equivalents

    PRE-PROCESSED DATA:
    ---
    {relevant_text}
    ---
    """
    try:
        response = llm_strict.invoke(prompt)
        cleaned_response = response.strip().replace("```json", "").replace("```", "")
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            cleaned_response = cleaned_response[start_idx:end_idx]
            
        kpis = json.loads(cleaned_response)
        state['financial_kpis'] = kpis
        state['cleaned_data'] = json.dumps(kpis, indent=2)
        print("---STRUCTURED DATA KPI EXTRACTION COMPLETE---")
    except Exception as e:
        print(f"Error extracting KPIs from Excel: {e}")
        state['cleaned_data'] = "Error: Could not extract structured financial data from the spreadsheet."
        state['financial_kpis'] = {}
    return state

def optimist_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING OPTIMIST AGENT (WITH STRATEGY RAG)---")
    company = state.get('company_name', 'The Company')
    kpis = state.get('cleaned_data', '{}')

    rag_query = "What are the key achievements, future growth strategies, new product launches, and positive management outlook?"
    rag_context = retriever.hybrid_search(rag_query, top_k=4)

    prompt = f"""
    You are the Optimistic CEO of {company}.
    Defend the financial results and highlight the company's strategic vision, growth, and achievements.
    Be highly detailed and comprehensive. Write at least 3 substantial paragraphs.

    MANDATORY CITATIONS: You MUST cite the specific page numbers for your claims. The RAG context includes tags like [SOURCE: Page X]. Always include the page number in your text, for example: "Our revenue grew 111% (Page 45)."

    HARD FINANCIAL DATA:
    {kpis}

    QUALITATIVE STRATEGY & ACHIEVEMENTS (From RAG Database):
    ---
    {rag_context}
    ---

    Focus on the narrative. Explain *how* the company achieved its numbers and what the exciting future holds based strictly on the provided qualitative text.
    """
    response = llm_strict.invoke(prompt)
    state['optimist_response'] = response.strip()
    
    # Ensure debate list exists and append response
    state.setdefault('debate', []).append(f"🤖 The Optimist (CEO): {response.strip()}")
    return state

def realist_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING REALIST AGENT (WITH OPERATIONS RAG)---")
    company = state.get('company_name', 'The Company')
    kpis = state.get('cleaned_data', '{}')

    rag_query = "What is the capital allocation, debt management strategy, cost efficiency, and auditor's remarks?"
    rag_context = retriever.hybrid_search(rag_query, top_k=4)

    prompt = f"""
    You are the pragmatic, data-driven CFO of {company}.
    Provide a grounded, highly detailed financial analysis. Write at least 3 substantial paragraphs.
    
    CRITICAL INSTRUCTION FOR MISSING DATA: 
    Review the HARD FINANCIAL DATA. If any metrics (like Revenue or Profit) are 'null' or missing, YOU MUST NOT complain, apologize, or state that the data is missing. A real CFO never makes excuses. Instead, seamlessly pivot your analysis to focus on the metrics that ARE present (e.g., Assets, Liabilities, Employee Costs, Cash) and rely heavily on the QUALITATIVE CONTEXT to assess operational efficiency and capital management.

    MANDATORY CITATIONS: You MUST cite the specific page numbers for your claims. The RAG context includes tags like [SOURCE: Page X]. Always include the page number in your text, for example: "Operating costs were optimized (Page 12)."
    
    HARD FINANCIAL DATA:
    {kpis}

    OPERATIONAL & FINANCIAL CONTEXT (From RAG Database):
    ---
    {rag_context}
    ---

    Synthesize the hard numbers with the operational realities and capital allocation strategies mentioned in the text. Be objective. Calculate ratios ONLY if the required numbers are explicitly provided.
    """
    response = llm_strict.invoke(prompt)
    state['realist_response'] = response.strip()
    
    # Ensure debate list exists and append response
    state.setdefault('debate', []).append(f"🧐 The Realist (CFO): {response.strip()}")
    return state

def skeptic_agent(state: AgentState) -> AgentState: # TYPO FIXED HERE!
    print("\n---EXECUTING SKEPTIC AGENT (WITH RISK RAG)---")
    company = state.get('company_name', 'The Company')
    kpis = state.get('cleaned_data', '{}')

    rag_query = "What are the key risk factors, pending litigations, supply chain disruptions, market threats, and material weaknesses?"
    rag_context = retriever.hybrid_search(rag_query, top_k=4)

    prompt = f"""
    You are a Skeptical, aggressive short-seller Investor analyzing {company}.
    Tear apart the narrative. Look for hidden risks, vulnerabilities, and high expenses.
    Write at least 3 substantial paragraphs detailing the systemic risks.

    MANDATORY CITATIONS: You MUST cite the specific page numbers for your attacks. The RAG context includes tags like [SOURCE: Page X]. Always include the page number in your text, for example: "The company faces major supply chain risks (Page 88)."

    HARD FINANCIAL DATA:
    {kpis}

    COMPANY RISKS & THREATS (From RAG Database):
    ---
    {rag_context}
    ---

    Focus on exposing the risks, debt issues, or market threats hidden in the report context. Point out specific risks mentioned in the text that threaten the company's future.
    """
    response = llm_strict.invoke(prompt)
    state['skeptic_response'] = response.strip()
    
    # Ensure debate list exists and append response
    state.setdefault('debate', []).append(f"🔥 The Skeptic (Investor): {response.strip()}")
    return state

def summary_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SUMMARY AGENT---")
    # Now this will successfully grab the debate from the 3 agents above!
    debate_text = "\n\n".join(state.get('debate', []))
    
    prompt = f"Summarize the following debate about {state['company_name']} into a final, actionable investment memo. Synthesize the optimistic, realistic, and skeptical viewpoints.\n\nDEBATE:\n{debate_text}"
    response = llm_strict.invoke(prompt)
    state['final_summary'] = response.strip()
    state['analysis_context'] = state['cleaned_data']
    return state

def comprehensive_analysis_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING COMPREHENSIVE ANALYSIS AGENT---")
    prompt = f"You are a senior analyst. From the report excerpts for {state['company_name']}, summarize:\n1. Key Growth Drivers.\n2. Stated Risks.\n3. Future Goals.\n\nSource Text:\n---\n{state['extracted_text'][:8000]}\n---"
    response = llm_strict.invoke(prompt)
    state['deep_dive_analysis'] = {"details": response.strip()}
    print("---COMPREHENSIVE ANALYSIS COMPLETE---")
    return state



def scenario_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SCENARIO AGENT (WITH RAG)---")
    user_query = state.get('user_query', "No query provided.")
    company_name = state.get('company_name', 'The Company')
    cleaned_data = state.get('cleaned_data', '{}')

    # Add RAG search to the What-If Simulator so it knows historical context!
    rag_context = retriever.hybrid_search(user_query, top_k=3)

    prompt = f"""
    You are a razor-sharp Financial Modeling Expert for {company_name}.
    The user is proposing a hypothetical "what-if" scenario. Your job is to calculate the potential financial impact.

    CRITICAL INSTRUCTIONS:
    1. Look at the HARD FINANCIAL DATA. Identify the current numbers relevant to the scenario. If a specific number is 'null' or missing, DO NOT crash or complain. Clearly state a reasonable assumption based on the HISTORICAL CONTEXT to fill the gap.
    2. Perform the step-by-step mathematical calculation. Show your work clearly.
    3. Provide a brutal, bottom-line conclusion on how this impacts the company's health or leverage.
    
    HARD FINANCIAL DATA:
    ---
    {cleaned_data}
    ---
    
    HISTORICAL CONTEXT (For reference & precedents):
    ---
    {rag_context}
    ---

    USER'S SCENARIO: "{user_query}"
    """
    response = llm_strict.invoke(prompt)
    state['scenario_response'] = response.strip()
    print("---SCENARIO ANALYSIS COMPLETE---")
    return state

def benchmark_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING BENCHMARK AGENT (MULTI-DOC RAG)---")
    company = state.get('company_name', 'The Company')
    kpis = state.get('cleaned_data', '{}')
    
    # We pass the competitor's name via the user_query variable
    competitor = state.get('user_query', 'Industry Competitors')

    # Query the RAG engine specifically for the competitor's data
    rag_query = f"What is the revenue, profit, market share, and strategic growth of {competitor}?"
    competitor_context = retriever.hybrid_search(rag_query, top_k=4)

    prompt = f"""
    You are an elite, ruthless Market Analyst benchmarking {company} against {competitor}.
    
    CRITICAL RULES - READ CAREFULLY:
    1. DO NOT APOLOGIZE. DO NOT say "Unfortunately," "I couldn't access," or "Based on available data."
    2. DO NOT mention if data is missing or incomplete. Never break character.
    3. If exact numbers for the competitor are missing from the text below, IGNORE the numbers and ruthlessly compare their STRATEGY and POSITIONING using whatever text IS available.
    4. Provide a bulleted list of competitive advantages and disadvantages for {company}.
    5. Cite [SOURCE: Page X] for the competitor data.
    
    Company KPIs ({company}):
    {kpis}
    
    Competitor Data ({competitor}):
    {competitor_context}
    """
    response = llm_strict.invoke(prompt)
    state['benchmark_analysis'] = response.strip()
    print("---BENCHMARK ANALYSIS COMPLETE---")
    return state

def compliance_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SEC/COMPLIANCE RISK AGENT---")
    company = state.get('company_name', 'The Company')
    
    # We deliberately query for the scariest terms in finance
    rag_query = "What are the auditor qualifications, material weaknesses, regulatory actions, pending litigations, or going concern warnings?"
    rag_context = retriever.hybrid_search(rag_query, top_k=4)

    prompt = f"""
    You are a strict SEC Compliance Officer and Risk Auditor analyzing {company}.
    Your job is to read the provided context and extract a high-priority alert list of legal threats, auditor remarks, and regulatory risks.
    
    CRITICAL INSTRUCTIONS:
    1. Output a clear, bulleted list of severe risks.
    2. MANDATORY CITATIONS: You MUST cite the [SOURCE: Page X] for every single bullet point.
    3. If no major risks are found, state "No material compliance risks found in the retrieved context."
    4. Do not include introductory or concluding fluff. Just give me the alerts.
    
    REPORT CONTEXT:
    ---
    {rag_context}
    ---
    """
    response = llm_strict.invoke(prompt)
    
    # We'll store this in analysis_context so we don't have to create a new state variable
    state['analysis_context'] = response.strip() 
    print("---COMPLIANCE CHECK COMPLETE---")
    return state

# --- Put this at the very bottom of agents.py with your other workflows ---
compliance_workflow = StateGraph(AgentState)
compliance_workflow.add_node("compliance_tracker", compliance_agent)
compliance_workflow.set_entry_point("compliance_tracker")
compliance_workflow.add_edge("compliance_tracker", END)
compliance_app = compliance_workflow.compile()

# --- WORKFLOW LOGIC ---
def route_file_type(state: AgentState) -> str:
    print("---ROUTING BY FILE TYPE---")
    if state.get('structured_data') is not None:
        return "structured_data_path"
    else:
        return "unstructured_data_path"

analysis_workflow = StateGraph(AgentState)
analysis_workflow.add_node("ingestion", ingestion_agent)
analysis_workflow.add_node("company_identifier", company_identifier_agent)
analysis_workflow.add_node("toc_analyzer", toc_agent)
analysis_workflow.add_node("pdf_extractor", pdf_extraction_agent)
analysis_workflow.add_node("pdf_analyzer", pdf_analysis_agent)
analysis_workflow.add_node("excel_analyzer", structured_data_agent)
analysis_workflow.add_node("optimist", optimist_agent)
analysis_workflow.add_node("realist", realist_agent)
analysis_workflow.add_node("skeptic", skeptic_agent)
analysis_workflow.add_node("summary", summary_agent)

analysis_workflow.set_entry_point("ingestion")
analysis_workflow.add_conditional_edges(
    "ingestion",
    route_file_type,
    {"structured_data_path": "excel_analyzer", "unstructured_data_path": "toc_analyzer"}
)
analysis_workflow.add_edge("toc_analyzer", "pdf_extractor")
analysis_workflow.add_edge("pdf_extractor", "pdf_analyzer")
analysis_workflow.add_edge("pdf_analyzer", "company_identifier")
analysis_workflow.add_edge("excel_analyzer", "company_identifier")
analysis_workflow.add_edge("company_identifier", "optimist")
analysis_workflow.add_edge("optimist", "realist")
analysis_workflow.add_edge("realist", "skeptic")
analysis_workflow.add_edge("skeptic", "summary")
analysis_workflow.add_edge("summary", END)
analysis_app = analysis_workflow.compile()

report_workflow = StateGraph(AgentState)
report_workflow.add_node("comprehensive_analysis", comprehensive_analysis_agent)
report_workflow.set_entry_point("comprehensive_analysis")
report_workflow.add_edge("comprehensive_analysis", END)
report_app = report_workflow.compile()

scenario_workflow = StateGraph(AgentState)
scenario_workflow.add_node("scenario_analyzer", scenario_agent)
scenario_workflow.set_entry_point("scenario_analyzer")
scenario_workflow.add_edge("scenario_analyzer", END)
scenario_app = scenario_workflow.compile()

benchmark_workflow = StateGraph(AgentState)
benchmark_workflow.add_node("benchmark_analyzer", benchmark_agent)
benchmark_workflow.set_entry_point("benchmark_analyzer")
benchmark_workflow.add_edge("benchmark_analyzer", END)
benchmark_app = benchmark_workflow.compile()