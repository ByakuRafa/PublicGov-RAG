# Relatório Comparativo de Evals — PublicGov-RAG

- **Dataset:** `evals/golden_dataset.json` (30 perguntas)
- **Modelo LLM:** `gemini-3.5-flash-lite` | **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Documentos indexados no PostgreSQL:** **308** (6/9 categorias `doc_type`)

| Versão Prompt | Faithfulness (RAGAS) | Answer Relevancy | Source Recall@4 | Precisão Citação de Fontes | Abstenção (Sem Resposta) | Latência Média (ms) | Tokens (In/Out) | Custo Total (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `v1` | 66.97% | 62.71% | 96.00% | 36.67% | 80.00% | 9820.0 | 170758/6863 | $0.019822 |
| `v2` | 65.00% | 53.65% | 92.00% | 72.50% | 80.00% | 8221.8 | 176865/5717 | $0.019973 |

> **Categorias `doc_type` ainda sem PDFs indexados no banco:** `Ata_Sessao`, `Lei_Municipal`, `Materia_Legislativa`
