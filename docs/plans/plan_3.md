  Diagnosis                                                                                                                                                            
                                                                                                                                                                       
  Bug 1: Tag filter uses wrong ChromaDB operator                                                                                                                       
                                                                                                                                                                       
  In cli.py:66, the tag filter builds:
  where["tags"] = {"$in": list(tag)}                                                                                                                                   
                                                                                                                                                                       
  But tags metadata is a list (e.g., ["Content", "Graph", "CC_3A_..."]). ChromaDB's $in only works on scalar values. For list-valued metadata, you must use $contains. 
                                                                                                                                                                       
  Proof:                                                                                                                                                               
  - {"tags": {"$in": ["Content"]}} → 0 results (broken)                                                                                                                
  - {"tags": {"$contains": "Content"}} → 5 results (correct)                                                                                                           
                                                                                                                                                                       
  Bug 2: Section filter references nonexistent metadata key                                                                                                            
                                                                                                                                                                       
  The CLI builds a filter checking Document Title, Primary Section, and Subsection. But looking at your actual data:                                                   
                                                                                                                                                                       
  ┌─────────────────┬───────────────────┐                                                                                                                              
  │  Metadata Key   │ Docs (out of 500) │                                                                                                                              
  ├─────────────────┼───────────────────┤                                                                                                                              
  │ Document Title  │ 452               │                                                                                                                              
  ├─────────────────┼───────────────────┤                                                                                                                              
  │ Primary Section │ 0                 │                                                                                                                              
  ├─────────────────┼───────────────────┤                                                                                                                              
  │ Subsection      │ 181               │                                                                                                                              
  └─────────────────┴───────────────────┘                                                                                                                              
                                                                                                                                                                       
  Primary Section never exists in your ingested documents. Your Obsidian notes use # and ### headers but rarely ##, so the MarkdownHeaderTextSplitter never populates  
  it. The filter silently returns no matches.                                                                                                                          
                                                                                                                                                                       
  Issue 3: RAG pipeline generalization is limited                                                                                                                      
                                                                                                                                                                       
  Several structural problems in the retrieval pipeline:                                                                                                               

  1. No distance metric specified — ChromaDB defaults to L2 (Euclidean) distance. Cosine similarity is far better for text embedding search.
  2. Small child chunks (400 chars) with narrow embeddings — a query about "mitochondria function" won't match a chunk using "oxidative phosphorylation" because the
  semantic overlap in a 400-char window is too narrow.
  3. No hybrid search — BM25 is configured but never implemented. Pure vector search misses exact keyword matches (critical for medical terminology like drug names,
  enzyme names, pathways).
  4. No reranking — After initial vector retrieval, results go straight to the LLM. A cross-encoder reranking step would significantly improve precision.
  5. Narrow search window — top_k * 3 = 30 child chunks searched to yield 10 parents. For 1145 chunks, this is only 2.6% of the collection.
  6. Silent exception swallowing — retriever.py:125 catches all exceptions during parent lookup and silently continues, hiding real errors.

  ---
  Proposed Plan

  Phase 1: Fix tag and section filters (immediate)

  cli.py — Replace $in with $contains for tag filters:
  # Single tag:  {"tags": {"$contains": "Content"}}
  # Multi-tag:   {"$or": [{"tags": {"$contains": "tag1"}}, ...]}

  cli.py — Fix section filter to only include metadata keys that actually exist, and use $contains for partial matching instead of exact $in:
  # Use $eq for exact, or consider substring matching

  Phase 2: Fix ChromaDB collection distance metric (requires re-ingest)

  chroma.py — When creating collections, specify cosine distance:
  self.client.create_collection(name=name, metadata={"hana:space": "cosine"})

  Phase 3: Increase retrieval quality

  config.py — Increase child_chunk_size from 400 to 800 and top_k_semantic from 25 to 50. Larger chunks capture more context per embedding.

  retriever.py — Increase the over-fetch multiplier from top_k * 3 to top_k * 5 for better parent coverage.

  Phase 4: Add BM25 hybrid search (major improvement)

  retriever.py — Implement the already-configured BM25 keyword search alongside vector search, then fuse results with Reciprocal Rank Fusion (RRF, parameter already in
   config at rrf_k: 80).

  Phase 5: Add cross-encoder reranking (optional, high impact)

  Use a lightweight cross-encoder (e.g., cross-encoder/ms-marco-MiniLM-L-6-v2) to rerank the top results before sending to the LLM.

  ---
  Phase 1 is the highest priority — it fixes actual broken functionality. Phases 2-3 are medium effort with large impact. Phases 4-5 are bigger lifts but would
  transform retrieval quality.

  Want me to start implementing Phase 1 (the filter fixes), or would you like to discuss/adjust the plan first?