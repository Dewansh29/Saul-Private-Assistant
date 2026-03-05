from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# 1. Load the exact same local embeddings we used for ingestion
local_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Connect to your newly created database
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=local_embeddings
)

# 3. Set up the Vector Retriever (Focuses on meaning)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 4. Set up the BM25 Keyword Retriever (Focuses on exact matches)
# We extract all the text you just ingested to build the keyword index
print("Building exact-match keyword index from ChromaDB...")
db_data = vectorstore.get()
all_texts = db_data['documents']
keyword_retriever = BM25Retriever.from_texts(all_texts)
keyword_retriever.k = 3

# 5. Combine them into the HYBRID RETRIEVER
# This gives 50% weight to meaning, and 50% weight to exact numbers/words
hybrid_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, keyword_retriever],
    weights=[0.5, 0.5] 
)

# --- LET'S TEST IT ---
print("\n--- Testing the Hybrid Search ---")
query = "What was the exact revenue or profit?" # You can change this question!

print(f"Query: {query}\n")
results = hybrid_retriever.invoke(query)

for i, doc in enumerate(results):
    print(f"Result {i+1} [Source: {doc.metadata.get('source')}, Page: {doc.metadata.get('page')}]:")
    # Print the first 250 characters of the chunk to see what it found
    print(doc.page_content[:250] + "...\n")