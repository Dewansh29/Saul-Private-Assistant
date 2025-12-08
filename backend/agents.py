import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any, List
import pandas as pd
import json
from langgraph.graph import StateGraph, END
# --- ENSURE THIS IMPORT IS CORRECT ---
from utils import extract_tables_from_pdf, extract_text_from_pdf, extract_data_from_excel, process_excel_data

# --- SETUP & MARKET DATA ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash-lite')
MARKET_DATA = {
    "APAC Food Delivery Sector Growth (YoY)": {"value": "27%", "source": "Q3 2024 Food Delivery Market Report"},
    "Global Quick Commerce Growth (YoY)": {"value": "85%", "source": "Global Commerce Analytics, FY24 Review"},
}


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
    Return the result as a clean JSON object with the keys "financial_statements" and "boards_report". If a section is not found, its value should be null. Example: {{"financial_statements": 31, "boards_report": 8}}
    Table of Contents Text:
    ---
    {state['table_of_contents']}
    ---
    """
    response = model.generate_content(prompt)
    try:
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        state['key_pages'] = json.loads(cleaned_response)
        print(f"---KEY PAGES IDENTIFIED: {state['key_pages']}---")
    except Exception as e:
        print(f"Error parsing ToC JSON: {e}. Using default page ranges.")
        state['key_pages'] = {}
    return state


def pdf_extraction_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING ROBUST PDF EXTRACTION AGENT---")
    file_bytes = state['raw_file_bytes']
    key_pages = state.get('key_pages', {})

    start_page = min(p for p in key_pages.values() if p is not None) if any(key_pages.values()) else 8
    page_range = list(range(int(start_page), int(start_page) + 50))
    print(f"---Scanning PDF pages {min(page_range)} to {max(page_range)} for tables and text.---")

    state['extracted_tables'] = extract_tables_from_pdf(file_bytes, page_numbers=page_range)
    state['extracted_text'] = extract_text_from_pdf(file_bytes, page_numbers=page_range)
    return state

def pdf_analysis_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING ENHANCED PDF KPI EXTRACTION AGENT---")
    tables_text = ""
    if state.get('extracted_tables'):
        print(f"---Found {len(state['extracted_tables'])} pages with tables.---")
        for page, tables in state['extracted_tables'].items():
            for i, table in enumerate(tables):
                tables_text += f"--- Parsed Table {i+1} from Page {page} ---\n{table.to_markdown(index=False)}\n\n"
    else:
        print("---No structured tables automatically parsed. Relying on raw text analysis.---")
        tables_text = "No structured tables were extracted."

    full_context = f"PARSED TABLE DATA:\n{tables_text}\n\nRAW TEXT FROM REPORT:\n{state['extracted_text']}"

    prompt = f"""
    You are a meticulous financial analyst. Your task is to extract key financial metrics from the provided data from a company's annual report.
    The data contains both structured tables (if any were parsed) and raw text. *You must find the financial data, even if it is only in the raw text.*
    Focus on the *Standalone Financial Performance* for the most recent year (e.g., 2023-24).

    Metrics to extract (all values should be in millions, e.g., 272,524):
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

    Return the result as a clean JSON object. If a value cannot be found, set its value to null.
    
    Example Output:
    {{
        "Revenue from operations": 272524,
        "Total Income": 281613,
        "Total Expenses": 239855,
        "Profit before tax": 41758,
        "Profit for the year (Net Profit)": 31632,
        "Total Assets": 253919,
        "Total Liabilities": 42013,
        "Total Equity": 211906,
        "Employee benefit expenses": 200175,
        "Cash and cash equivalents": 9095
    }}

    FULL CONTEXT DATA:
    ---
    {full_context}
    ---
    """

    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        kpis = json.loads(cleaned_response)
        state['financial_kpis'] = kpis
        state['cleaned_data'] = json.dumps(kpis, indent=2)
        print("---PDF KPI EXTRACTION COMPLETE---")
        print(state['cleaned_data'])
    except Exception as e:
        print(f"Error extracting KPIs from PDF: {e}")
        state['cleaned_data'] = "Error: Could not extract structured financial data from the PDF."
        state['financial_kpis'] = {}
    return state


def company_identifier_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING COMPANY IDENTIFIER AGENT---")
    if state.get('extracted_text'):
        prompt = f"From the following text from an annual report, identify and return ONLY the main company's name. Example: 'Capgemini Technology Services India Limited'.\n\nTEXT:\n{state['extracted_text'][:2000]}"
        try:
            response = model.generate_content(prompt)
            identified_name = response.text.strip()
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
        response = model.generate_content(prompt)
        identified_name = response.text.strip()
        if 3 < len(identified_name) < 100 and '\n' not in identified_name:
            state['company_name'] = identified_name
        else:
            state['company_name'] = "The Company"
        print(f"---COMPANY IDENTIFIED FROM COVER: {state['company_name']}---")
    except Exception as e:
        print(f"Could not identify company name, using default. Error: {e}")
        state['company_name'] = "The Company"
    return state


# --- CHANGE: This agent now uses the new, more robust processing function ---
def structured_data_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING BULLETPROOF STRUCTURED DATA AGENT---")
    structured_data = state.get('structured_data')
    if not structured_data:
        state['cleaned_data'] = "Error: No structured data found."
        state['financial_kpis'] = {}
        return state

    # Use the new helper function to pre-process the data
    relevant_text = process_excel_data(structured_data)
    print("----------- PRE-PROCESSED EXCEL DATA FED TO LLM -----------")
    print(relevant_text)
    print("---------------------------------------------------------")
    
    prompt = f"""
    You are a meticulous financial analyst. Your task is to extract key financial metrics from the pre-processed, highly relevant text below, which was extracted from an Excel file.

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

    Return the result as a clean JSON object. If a value cannot be found for a metric based on the text, set its value to null.
    Do not add any commentary or explanation outside of the JSON object.

    PRE-PROCESSED DATA:
    ---
    {relevant_text}
    ---
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        kpis = json.loads(cleaned_response)
        state['financial_kpis'] = kpis
        state['cleaned_data'] = json.dumps(kpis, indent=2)
        print("---STRUCTURED DATA KPI EXTRACTION COMPLETE---")
        print(state['cleaned_data'])
    except Exception as e:
        print(f"Error extracting KPIs from Excel: {e}")
        state['cleaned_data'] = "Error: Could not extract structured financial data from the spreadsheet."
        state['financial_kpis'] = {}
    return state


def optimist_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING OPTIMIST AGENT---")
    prompt = f"""
    You are an optimistic CEO of {state['company_name']}.
    Based on the financial KPIs below, provide a positive and encouraging takeaway for the board.
    You MUST cite specific numbers from the KPIs to support your argument. If any KPIs are 'null' or missing, acknowledge the data gap as a temporary hiccup but focus on the positive available numbers and the company's strong reputation.

    Financial KPIs:
    {state['cleaned_data']}
    """
    response = model.generate_content(prompt)
    state['debate'].append(f"🤖 The Optimist (CEO): {response.text.strip()}")
    return state


def realist_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING REALIST AGENT---")
    prompt = f"""
    You are a pragmatic and realistic CFO of {state['company_name']}.
    Based on the financial KPIs below, provide a balanced, data-driven analysis.

    Your analysis MUST:
    1.  Start by acknowledging any missing data (KPIs with 'null' values) and state what analysis is not possible as a result.
    2.  Highlight the company's strengths using the available numbers.
    3.  Identify areas that need careful monitoring.
    4.  **Calculate and cite at least two relevant financial ratios or percentages.** For example, calculate the Net Profit Margin (Net Profit / Revenue from operations) or what percentage of Total Expenses is Employee Benefit Expenses.
    5.  You MUST cite the original numbers from the KPIs to support all your claims.

    Financial KPIs:
    {state['cleaned_data']}
    """
    response = model.generate_content(prompt)
    state['debate'].append(f"🧐 The Realist (CFO): {response.text.strip()}")
    return state

def skeptic_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SKEPTIC AGENT---")
    prompt = f"""
    You are a skeptical investor analyzing {state['company_name']}.
    Your job is to find potential weaknesses or red flags in the financial data.

    Your analysis MUST:
    1.  If any data is missing (KPIs with 'null' values), treat the lack of transparency itself as a major red flag and explain the risks.
    2.  Use the available numbers to find concerning trends or metrics.
    3.  **Calculate and cite at least two key financial ratios or percentages** to expose a potential weakness. For example, calculate the company's debt-to-equity ratio (Total Liabilities / Total Equity) or its profit margin.
    4.  You MUST cite the original numbers from the KPIs to support your skeptical viewpoint.

    Financial KPIs:
    {state['cleaned_data']}
    """
    response = model.generate_content(prompt)
    state['debate'].append(f"🔥 The Skeptic (Investor): {response.text.strip()}")
    return state


def summary_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SUMMARY AGENT---")
    debate_text = "\n".join(state['debate'])
    prompt = f"Summarize the following debate about {state['company_name']} into a final, actionable investment memo. Synthesize the optimistic, realistic, and skeptical viewpoints into a balanced conclusion.\n\nDEBATE:\n{debate_text}"
    response = model.generate_content(prompt)
    state['final_summary'] = response.text
    state['analysis_context'] = state['cleaned_data']
    return state


def comprehensive_analysis_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING COMPREHENSIVE ANALYSIS AGENT---")
    prompt = f"You are a senior analyst. From the report excerpts for {state['company_name']}, summarize:\n1. Key Growth Drivers.\n2. Stated Risks.\n3. Future Goals.\n\nSource Text:\n---\n{state['extracted_text']}\n---"
    response = model.generate_content(prompt)
    state['deep_dive_analysis'] = {"details": response.text}
    print("---COMPREHENSIVE ANALYSIS COMPLETE---")
    return state


def scenario_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING SCENARIO AGENT---")
    user_query = state.get('user_query', "No query provided.")
    company_name = state.get('company_name', 'The Company')
    cleaned_data = state.get('cleaned_data', '{}')

    prompt = f"""
    You are a financial modeling expert for {company_name}.
    Given a JSON object of key financial data and a "what-if" question, calculate the potential impact.
    Show your step-by-step calculation and provide a clear, concise conclusion.
    If the provided data is insufficient to answer the question, state exactly what information is missing.

    KEY FINANCIAL DATA:
    ---
    {cleaned_data}
    ---

    USER'S SCENARIO:
    "{user_query}"
    """
    response = model.generate_content(prompt)
    state['scenario_response'] = response.text
    print("---SCENARIO ANALYSIS COMPLETE---")
    return state


def benchmark_agent(state: AgentState) -> AgentState:
    print("\n---EXECUTING BENCHMARK AGENT---")
    prompt = f"""
    You are a market analyst. Compare {state['company_name']}'s financial data with the provided market benchmarks.
    Provide a bulleted list of insights, citing the source for each benchmark.
    Ground your comparison in the company's specific numbers.

    Company KPIs:
    ---
    {state['cleaned_data']}
    ---

    Market Benchmarks:
    ---
    {str(MARKET_DATA)}
    ---
    """
    response = model.generate_content(prompt)
    state['benchmark_analysis'] = response.text
    print("---BENCHMARK ANALYSIS COMPLETE---")
    return state


# --- WORKFLOW LOGIC ---
def route_file_type(state: AgentState) -> str:
    print("---ROUTING BY FILE TYPE---")
    if state.get('structured_data'):
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