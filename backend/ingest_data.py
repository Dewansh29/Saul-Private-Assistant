from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Load the PDF
pdf_path = "Zomato_Annual_Report_2023-24.pdf"
loader = PyPDFLoader(pdf_path)
pages = loader.load()

# 2. Configure the Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200
)

# 3. Split the documents
chunks = text_splitter.split_documents(pages)

# Add custom metadata for later benchmarking
for chunk in chunks:
    chunk.metadata["company_id"] = "Zomato"

# 4. Initialize the LOCAL offline embedding model
# all-MiniLM-L6-v2 is a lightweight, blazing-fast model perfect for testing
local_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 5. Ingest into ChromaDB entirely on your machine
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=local_embeddings, 
    persist_directory="./chroma_db"
)

print(f"Successfully ingested {len(chunks)} chunks into ChromaDB with 100% local privacy.")