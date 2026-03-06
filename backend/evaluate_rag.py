import re
from rag_engine import retriever

print("\n" + "="*50)
print("🚀 INIT: SAUL GOODMAN RAG EVALUATION SUITE")
print("="*50)

# 1. Create a mini "Ground Truth" dataset
test_pages = [
    {"page_num": 1, "text": "In Q3 2023, TestCorp saw a massive surge in revenue, hitting $450 million. Profit margins remained stable."},
    {"page_num": 2, "text": "Employee benefit expenses rose sharply to $120 million due to aggressive hiring in the APAC region."},
    {"page_num": 3, "text": "The board is concerned about pending litigation regarding environmental regulations and a debt-to-equity ratio of 1.5."},
    {"page_num": 4, "text": "Strategic growth will focus on AI integration and launching the new 'Glitch Bazaar' platform next year."}
]

# 2. Define test questions and the exact page we EXPECT the engine to find
eval_queries = [
    {"query": "How much was the revenue in Q3?", "expected_page": 1},
    {"query": "Why did employee expenses increase?", "expected_page": 2},
    {"query": "Are there any pending lawsuits or litigation?", "expected_page": 3},
    {"query": "What is the strategic growth plan?", "expected_page": 4}
]

print("\n[1/3] Ingesting ground truth data into local ChromaDB...")
retriever.ingest_pages(test_pages, "EvalCorp")

total_precision = 0
total_recall = 0
total_mrr = 0
k = 3 # We are testing the top 3 results

print("\n[2/3] Running queries and calculating metrics...\n")

for i, test in enumerate(eval_queries):
    query = test["query"]
    expected_page = test["expected_page"]
    
    # Run the hybrid search
    results_str = retriever.hybrid_search(query, top_k=k)
    
    # Extract the page numbers from the output string using regex (e.g., finding "Page 2" in "[SOURCE: Page 2]")
    retrieved_pages = [int(p) for p in re.findall(r'\[SOURCE: Page (\d+)\]', results_str)]
    
    # Calculate Metrics
    is_relevant = expected_page in retrieved_pages
    
    # Precision@k: (Relevant chunks retrieved) / (Total chunks retrieved)
    # Since there's only 1 right page per question here, precision is 1/len(retrieved_pages) if found
    precision = (1 / len(retrieved_pages)) if is_relevant and len(retrieved_pages) > 0 else 0.0
    
    # Recall@k: (Relevant chunks retrieved) / (Total relevant chunks in document)
    # There is only 1 relevant chunk total, so recall is 1.0 if found, 0.0 if missed
    recall = 1.0 if is_relevant else 0.0
    
    # MRR: 1 / (Rank of the correct answer)
    mrr = 0.0
    if is_relevant:
        rank = retrieved_pages.index(expected_page) + 1
        mrr = 1.0 / rank

    total_precision += precision
    total_recall += recall
    total_mrr += mrr
    
    print(f"Query {i+1}: '{query}'")
    print(f"  -> Expected Page: {expected_page} | Retrieved Pages: {retrieved_pages}")
    print(f"  -> Precision@{k}: {precision:.2f} | Recall@{k}: {recall:.2f} | MRR: {mrr:.2f}\n")

# 3. Calculate Final Averages
num_queries = len(eval_queries)
avg_precision = total_precision / num_queries
avg_recall = total_recall / num_queries
avg_mrr = total_mrr / num_queries

print("="*50)
print("📊 FINAL RAG ENGINE METRICS (HYBRID ENSEMBLE)")
print("="*50)
print(f"Mean Precision@{k} : {avg_precision:.3f}  (Relevance of returned chunks)")
print(f"Mean Recall@{k}    : {avg_recall:.3f}  (Ability to find the target chunk)")
print(f"Mean Reciprocal Rank : {avg_mrr:.3f}  (How high the correct answer ranked)")
print("="*50)
print("Evaluation Complete. Ready for submission.")