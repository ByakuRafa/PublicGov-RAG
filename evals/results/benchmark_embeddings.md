# Benchmark de Embeddings e Estratégias de Retrieval — PublicGov-RAG

| Embedding | Modo de Busca | Recall@4 | MRR@4 | Latência Média (ms) | Indexação (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| MiniLM-L12-v2 (384d) | `vector_only` | 80.00% | 0.7056 | 40.0 | 5.26 |
| MiniLM-L12-v2 (384d) | `hybrid_rrf` | 93.33% | 0.8667 | 50.5 | 5.26 |
| MiniLM-L12-v2 (384d) | `hybrid_rrf_rerank` | 93.33% | 0.7889 | 2510.2 | 5.26 |
