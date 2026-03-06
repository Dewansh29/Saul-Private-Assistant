from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import traceback
import io
import requests
import json

from agents import analysis_app, report_app, scenario_app, benchmark_app, compliance_app, AgentState
from utils import create_word_report
from rag_engine import retriever

app = FastAPI(
    title="Saul Goodman: Financial Strategy API",
    description="API for the AI Financial Analyst Agent"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# --- TEST ROUTES ---
# ==========================================

@app.get("/test-rag")
def test_rag_pipeline():
    """Tests the new local embedding and vector database setup."""
    
    # We now format the dummy text as a page dictionary so the engine can track page numbers
    sample_pages = [
        {
            "page_num": 1, 
            "text": "In Q3 2023, The Company saw a massive surge in revenue, hitting $450 million. However, employee benefit expenses also rose sharply to $120 million due to aggressive hiring in the APAC region. The board is concerned about the debt-to-equity ratio standing at 1.5, suggesting high leverage."
        }
    ]
    
    # 1. Ingest the text using the NEW page-based method
    retriever.ingest_pages(sample_pages, "TestCorp")
    
    # 2. Perform a Hybrid Search
    answer_context = retriever.hybrid_search("What were the employee benefit expenses?")
    
    return {"retrieved_context": answer_context}

@app.get("/")
def health_check():
    return {"status": "Backend Online. Ready to process."}

@app.get("/ping-ollama")
def ping_ollama():
    """Tests the connection to your local Llama 3.2."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2", 
                "prompt": "You are Saul Goodman. Give me a one-sentence piece of aggressive financial advice.",
                "stream": False
            }
        )
        if response.status_code == 200:
            return {
                "status": "Success", 
                "saul_says": response.json().get("response")
            }
        return {"status": "Failed", "details": response.text}
    except Exception as e:
        return {"error": f"Could not connect to Ollama. Details: {str(e)}"}

# ==========================================
# --- CORE API ROUTES ---
# ==========================================

@app.post("/analyze-stream")
async def analyze_stream(file: UploadFile = File(...)):
    """Streams the LangGraph execution node-by-node to the frontend via Server-Sent Events."""
    file_bytes = await file.read()
    
    async def event_stream():
        # Initialize the state for LangGraph
        initial_state = AgentState(
            raw_file_bytes=file_bytes, 
            filename=file.filename,
            company_name="The Company",
            debate=[]
        )
        
        try:
            # LangGraph's .stream() yields data every time a node finishes its task!
            for output in analysis_app.stream(initial_state):
                node_name = list(output.keys())[0]
                state_update = output[node_name]
                
                # Create a clean package to send to the React frontend
                payload = {
                    "node": node_name,
                    "company_name": state_update.get("company_name"),
                    "latest_debate": state_update.get("debate", [])[-1] if state_update.get("debate") else None,
                    "kpis": state_update.get("cleaned_data") if node_name in ["pdf_analyzer", "excel_analyzer"] else None,
                    "summary": state_update.get("final_summary") if node_name == "summary" else None
                }
                
                # Yield the package in SSE format (data: {...}\n\n)
                yield f"data: {json.dumps(payload, default=str)}\n\n"
                
        except Exception as e:
            print(f"Streaming Error: {e}")
            error_payload = {"node": "error", "message": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/analyze")
async def analyze_report_for_display(file: UploadFile = File(...)):
    """Legacy route: Waits for the entire process to finish before returning."""
    try:
        file_bytes = await file.read()
        initial_state = AgentState(raw_file_bytes=file_bytes, debate=[], filename=file.filename)
        print("--- Invoking Analysis Workflow for Display ---")
        final_state = analysis_app.invoke(initial_state)
        return JSONResponse(content={
            "company_name": final_state.get('company_name'),
            "debate": final_state.get('debate'),
            "final_summary": final_state.get('final_summary'),
            "extracted_text": final_state.get('extracted_text'),
            "analysis_context": final_state.get('final_summary'),
            "cleaned_data": final_state.get('cleaned_data')
        })
    except Exception as e:
        print(f"ERROR in /analyze: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class ReportRequest(BaseModel):
    company_name: str
    debate: List[str]
    final_summary: str
    cleaned_data: str

class ScenarioRequest(BaseModel):
    analysis_context: str
    user_query: str
    company_name: str
    cleaned_data: str

class BenchmarkRequest(BaseModel):
    company_name: str
    cleaned_data: str
    competitor_name: str

@app.post("/download_report")
async def download_detailed_report(request: ReportRequest):
    try:
        print("--- Generating Word Report ---")
        
        full_report_data = {
            "debate": request.debate,
            "final_summary": request.final_summary,
            "cleaned_data": request.cleaned_data
        }
        
        report_stream = create_word_report(full_report_data, request.company_name)
        
        docx_media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        download_filename = f"Saul_Goodman_Analysis_{request.company_name}.docx"
        
        return StreamingResponse(
            report_stream,
            media_type=docx_media_type,
            headers={"Content-Disposition": f"attachment; filename=\"{download_filename}\""}
        )
    except Exception as e:
        print(f"ERROR in /download_report: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    user_query: str

@app.post("/chat")
async def deep_dive_chat(request: ChatRequest):
    """The Interrogation Room: Directly ask questions about the ingested report."""
    try:
        print(f"--- Interrogation Room Query: {request.user_query} ---")
        
        # 1. Hit the RAG Engine for the specific user question
        rag_context = retriever.hybrid_search(request.user_query, top_k=3)
        
        # 2. Prompt Saul Goodman (using the creative LLM from agents.py)
        # Note: We import llm_creative from agents at the top of main.py if not already there, 
        # or just instantiate it here. For safety, let's use the OllamaLLM directly here.
        from langchain_ollama import OllamaLLM
        chat_llm = OllamaLLM(model="llama3.2", temperature=0.6)
        
        prompt = f"""
        You are Saul Goodman, the slick, fast-talking, legally-flexible criminal lawyer from Albuquerque. 
        You are currently acting as a slightly shady but brilliant financial advisor for the user.
        
        CRITICAL RULES FOR YOUR PERSONA:
        1. Talk EXACTLY like Saul Goodman. Use his catchphrases ("Did you know you have rights?", "My guy", "Let me tell ya", "S'all good, man").
        2. Use sleazy but clever metaphors (e.g., laser tag arcades, burner phones, slip-and-falls, nail salons, money laundering, dodging the IRS).
        3. Be highly charismatic, slightly unhinged, but ultimately give mathematically sound and brutal financial advice based STRICTLY on the provided report context.
        4. If the answer isn't in the context, pitch them on a completely unrelated, slightly shady tax loophole instead, and tell them to call your burner phone.
        
        MANDATORY CITATIONS: You must cite the [SOURCE: Page X] in your response so the SEC doesn't come after us.
        
        REPORT CONTEXT:
        ---
        {rag_context}
        ---
        
        USER QUESTION: "{request.user_query}"
        """
        
        response = chat_llm.invoke(prompt)
        
        return {"response": response.strip(), "sources_used": rag_context}
        
    except Exception as e:
        print(f"ERROR in /chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scenario")
async def analyze_scenario(request: ScenarioRequest):
    try:
        initial_state = AgentState(
            analysis_context=request.analysis_context,
            user_query=request.user_query,
            company_name=request.company_name,
            cleaned_data=request.cleaned_data
        )
        print("--- Invoking Scenario Agent ---")
        final_state = scenario_app.invoke(initial_state)
        return {"response": final_state.get('scenario_response', 'Could not process scenario.')}
    except Exception as e:
        print(f"ERROR in /scenario: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/benchmark")
async def analyze_benchmark(request: BenchmarkRequest):
    """Feature 5: Cross-Company Benchmarking."""
    try:
        initial_state = AgentState(
            company_name=request.company_name,
            cleaned_data=request.cleaned_data,
            user_query=request.competitor_name  # Pass the competitor name to the agent
        )
        print(f"--- Invoking Benchmark Agent for {request.company_name} vs {request.competitor_name} ---")
        final_state = benchmark_app.invoke(initial_state)
        
        return {"response": final_state.get('benchmark_analysis', 'Could not process benchmark analysis.')}
    except Exception as e:
        print(f"ERROR in /benchmark: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
class ComplianceRequest(BaseModel):
    company_name: str

@app.post("/compliance")
async def run_compliance_check(request: ComplianceRequest):
    """Feature 4: Automated SEC/Compliance Risk Flagging."""
    try:
        initial_state = AgentState(company_name=request.company_name)
        print("--- Invoking Compliance Agent ---")
        
        # This triggers the standalone SEC agent workflow
        final_state = compliance_app.invoke(initial_state)
        
        return {"compliance_alerts": final_state.get('analysis_context', 'No compliance data extracted.')}
    except Exception as e:
        print(f"ERROR in /compliance: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))