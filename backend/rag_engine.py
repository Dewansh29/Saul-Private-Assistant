import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi
import numpy as np
from langchain_core.documents import Document

class HybridRetriever:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        print("--- Loading Embedding Model (CPU Only) ---")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'} 
        )
        self.vector_store = None
        self.bm25 = None
        self.chunks = []
        self.documents = []

    def ingest_pages(self, pages_data: list, company_name: str):
        """
        Takes a list of dictionaries: [{'page_num': 1, 'text': '...'}, ...]
        This ensures every chunk knows exactly what page it came from.
        """
        print(f"\n--- Chunking Document for {company_name} ---")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        
        self.documents = []
        # Process page by page so metadata is preserved
        for page in pages_data:
            if not page['text'].strip():
                continue
            chunks = text_splitter.split_text(page['text'])
            for chunk in chunks:
                doc = Document(
                    page_content=chunk, 
                    metadata={"company": company_name, "page": page['page_num']}
                )
                self.documents.append(doc)
                
        self.chunks = [doc.page_content for doc in self.documents]

        print(f"Created {len(self.chunks)} chunks. Building Vector DB...")
        self.vector_store = Chroma.from_documents(
            documents=self.documents,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        
        print("Building BM25 Keyword Index...")
        tokenized_chunks = [chunk.split(" ") for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_chunks)
        print("--- RAG Ingestion Complete ---")

    def hybrid_search(self, query: str, top_k: int = 4) -> str:
        if not self.vector_store or not self.bm25:
            return "Error: Document not ingested yet."
            
        print(f"\n--- Executing Hybrid Search for: '{query[:30]}...' ---")
        
        # 1. Vector Search
        vector_results = self.vector_store.similarity_search(query, k=top_k)
        
        # 2. Keyword Search
        tokenized_query = query.split(" ")
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:top_k]
        
        # Combine results and format them to explicitly state the Page Number
        combined_texts = []
        seen_content = set()
        
        # Process Vector Results
        for doc in vector_results:
            if doc.page_content not in seen_content:
                page_num = doc.metadata.get('page', 'Unknown')
                combined_texts.append(f"[SOURCE: Page {page_num}]\n{doc.page_content}")
                seen_content.add(doc.page_content)
                
        # Process BM25 Results
        for idx in top_bm25_indices:
            content = self.chunks[idx]
            if content not in seen_content:
                # Find the matching document to get its metadata
                matching_doc = next((d for d in self.documents if d.page_content == content), None)
                page_num = matching_doc.metadata.get('page', 'Unknown') if matching_doc else 'Unknown'
                combined_texts.append(f"[SOURCE: Page {page_num}]\n{content}")
                seen_content.add(content)

        return "\n\n---\n\n".join(combined_texts[:top_k])

retriever = HybridRetriever()