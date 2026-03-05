from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import traceback
import io
import requests
import json

from agents import analysis_app, report_app, scenario_app, benchmark_app, AgentState
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
    sample_financial_text = """
    In Q3 2023, The Company saw a massive surge in revenue, hitting $450 million. 
    However, employee benefit expenses also rose sharply to $120 million due to aggressive hiring in the APAC region.
    The board is concerned about the debt-to-equity ratio standing at 1.5, suggesting high leverage.
    """
    
    # 1. Ingest the text (CPU Embeddings + ChromaDB + BM25)
    retriever.ingest_text(sample_financial_text, "TestCorp")
    
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
    try:
        initial_state = AgentState(
            company_name=request.company_name,
            cleaned_data=request.cleaned_data
        )
        print("--- Invoking Benchmark Agent ---")
        final_state = benchmark_app.invoke(initial_state)
        return {"response": final_state.get('benchmark_analysis', 'Could not process benchmark analysis.')}
    except Exception as e:
        print(f"ERROR in /benchmark: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))