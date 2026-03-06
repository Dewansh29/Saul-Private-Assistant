import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document

class HybridRetriever:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        print("--- Loading Embedding Model (CPU Only) ---")
        # Explicitly forces embeddings to the CPU to save VRAM
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'} 
        )
        self.vector_store = None
        self.ensemble_retriever = None

    def ingest_pages(self, pages_data: list, company_name: str):
        print(f"\n--- Chunking Document for {company_name} ---")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        documents = []
        for page in pages_data:
            if not page['text'].strip():
                continue
            chunks = text_splitter.split_text(page['text'])
            for chunk in chunks:
                doc = Document(
                    page_content=chunk, 
                    metadata={"company": company_name, "page": page['page_num']}
                )
                documents.append(doc)

        print(f"Created {len(documents)} chunks. Building Vector DB...")
        
        # 1. Vector Store (Semantic Search)
        self.vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        vector_retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
        
        # 2. BM25 Index (Exact Keyword Match)
        print("Building BM25 Keyword Index...")
        keyword_retriever = BM25Retriever.from_documents(documents)
        keyword_retriever.k = 4
        
        # 3. Hybrid Ensemble Retriever (50/50 weight)
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, keyword_retriever],
            weights=[0.5, 0.5]
        )
        print("--- RAG Ingestion Complete ---")

    def hybrid_search(self, query: str, top_k: int = 4) -> str:
        if not self.ensemble_retriever:
            return "Error: Document not ingested yet."
            
        print(f"\n--- Executing Hybrid Search for: '{query[:30]}...' ---")
        
        results = self.ensemble_retriever.invoke(query)
        
        combined_texts = []
        seen_content = set()
        
        for doc in results:
            if doc.page_content not in seen_content:
                page_num = doc.metadata.get('page', 'Unknown')
                # Strict formatting so the LLM agents can cite their sources
                combined_texts.append(f"[SOURCE: Page {page_num}]\n{doc.page_content}")
                seen_content.add(doc.page_content)
                
        return "\n\n---\n\n".join(combined_texts[:top_k])

retriever = HybridRetriever()