# PublicGov-RAG — Legislação e Matérias Legislativas
### Sistema RAG de Apoio ao Cidadão e ao Servidor Público
**Câmara Municipal de Vereadores de Santana do Livramento — RS**

---

## 🏛️ 1. Visão Geral e Propósito

O **PublicGov-RAG** é um sistema de Inteligência Artificial baseado na arquitetura **RAG (*Retrieval-Augmented Generation*)**, desenvolvido para facilitar, democratizar e agilizar o acesso à informação pública legislativa da **Câmara Municipal de Vereadores de Santana do Livramento (RS)**.

O objetivo central é servir como uma ponte inteligente entre o acervo legislativo municipal e a sociedade, atendendo a dois públicos principais:

1. **Cidadãos Santanenses**: Compreender de forma clara, didática e direta as leis municipais, direitos, deveres, matérias em votação no plenário, moções e o posicionamento dos seus representantes eleitos.
2. **Servidores Públicos e Assessores Parlamentares**: Realizar consultas técnicas com precisão e celeridade, localizando precedentes regimentais, leis vigentes, redações de projetos de lei em tramitação e justificativas jurídicas, otimizando o trabalho legislativo e a instrução técnica de matérias.

---

## 🎯 2. Delimitação Estrita de Escopo

Para garantir a máxima confiabilidade, precisão e relevância das respostas, o sistema opera sob uma **fronteira de escopo bem definida**:

### ✅ O que ESTÁ no escopo (Legislação e Sessão Legislativa)
* **Atos Normativos e Leis Municipais**: Lei Orgânica do Município (LOM), Leis Ordinárias e Leis Complementares aprovadas e promulgadas/sancionadas.
* **Proposições Legislativas**: Projetos de Lei Ordinária (PLO), Projetos de Lei Complementar (PLC), Projetos de Decreto Legislativo (PDL) e Projetos de Resolução (PR).
* **Pautas e Ordens do Dia das Sessões**: Documentos oficiais que detalham o Expediente, matérias para deliberação, projetos em discussão e votação nas sessões plenárias (Ordinárias, Extraordinárias e Solenes).
* **Atas e Registros de Votação**: Atas das sessões com o registro de deliberações, votações nominais, pedidos de vista, baixas em diligência e aprovações/rejeições de matérias.
* **Instrumentos de Fiscalização e Manifestação Parlamentar**:
  * **Moções** (Moções de Apoio, Pesar, Repúdio, Aplauso e Reconhecimento);
  * **Requerimentos Oficiais** e **Pedidos de Providência / Informação** encaminhados ao Executivo ou órgãos públicos;
  * **Indicações Legislativas**.
* **Pareceres Técnicos das Comissões**: Análises de constitucionalidade, legalidade e mérito emitidas pelas comissões permanentes (ex.: Comissão de Constituição, Justiça e Redação; Comissão de Finanças e Orçamento).
* **Regramento Institucional do Processo Legislativo**: Regimento Interno da Câmara (ex.: Resolução nº 1.252/2016 e suas alterações).

### ❌ O que NÃO ESTÁ no escopo (Exclusões Deliberadas)
* **Rotinas e Gestão Administrativa Interna da Câmara**: Folha de pagamento, diárias de viagens, controle de ponto, férias de servidores, licitações de material de expediente e consumo interno (papel, toner, suprimentos), patrimônio mobiliário interno e portarias de recursos humanos.
* **Atos Administrativos do Poder Executivo (Prefeitura)**: Decretos regulamentares exclusivos do prefeito, processos de arrecadação tributária, autuações de trânsito, editais de concursos e licitações de obras da Prefeitura — *exceto* quando forem objeto direto de deliberação, audiência pública ou projeto de lei na Câmara.
* **Demandas Judiciais ou de Órgãos Externos**: Processos judiciais, decisões do Ministério Público ou de outras esferas fora do rito e competência do Poder Legislativo Municipal.

---

## 📄 3. Análise dos Tipos de Documentos Utilizados

Os documentos tramitados na Câmara de Santana do Livramento possuem formatos e características específicas que determinam como devem ser catalogados e processados:

| `doc_type` (Metadado) | Tipo de Documento | Conteúdo Típico e Estrutura | Importância para Cidadãos e Servidores |
| :--- | :--- | :--- | :--- |
| `Pauta_Sessao` | **Pauta das Sessões Plenárias** | Convocação, pauta da Ordem do Dia, lista de proposições a serem votadas, projetos em regime de urgência, leitura de expedientes. | Permite ao cidadão saber o que será votado na próxima sessão e ao servidor acompanhar a esteira de votação. |
| `Ata_Sessao` | **Ata de Sessão Plenária** | Registro de presenças/ausências, transcrição das discussões em tribuna, votações nominais e desfecho das matérias. | Garante transparência histórica sobre como votou cada vereador em cada projeto de lei. |
| `Projeto_de_Lei` | **Projetos de Lei (PLO / PLC)** | Ementa, texto articulado (artigos, parágrafos, incisos), justificativa formal do autor e impacto financeiro/social. | Essencial para entender a motivação de novas regras e preparar pareceres técnicos ou emendas. |
| `Lei_Municipal` | **Leis Promulgadas / Sancionadas** | Texto legal consolidado, data de vigência, revogações expressas de legislações anteriores. | Base de consulta para cidadãos conhecerem seus direitos e obrigações vigentes no município. |
| `Mocao` | **Moções Parlamentares** | Moções de Apoio (ex.: a projetos federais como alteração do MEI), Pesar, Repúdio ou Reconhecimento, fundamentadas regimentalmente. | Demonstra o posicionamento político e institucional da Câmara em temas locais, estaduais e nacionais. |
| `Parecer_Comissao` | **Pareceres de Comissões** | Análise de legalidade, constitucionalidade e adequação financeira da proposta antes de ir a plenário. | Peça fundamental para a segurança jurídica das votações e consulta prévia de servidores. |
| `Requerimento_Legislativo` | **Requerimentos e Pedidos de Informação** | Cobranças oficiais ao Poder Executivo sobre obras, saúde, educação, asfalto, iluminação e dados públicos. | Ferramenta primordial para fiscalização da gestão pública municipal. |
| `Regimento_e_LOM` | **Lei Orgânica e Regimento Interno** | Normas estruturantes do município e regras de tramitação, quóruns e funcionamento das sessões. | Guia mestre para a assessoria legislativa instruir os ritos processuais corretamente. |

### 🔍 Desafio Real: Tratamento de Documentos Digitalizados (OCR)
Na rotina de câmaras municipais, muitos documentos históricos ou expedientes protocolados fisicamente contêm apenas imagens escaneadas (sem texto nativo selecionável), como verificado nos arquivos de pautas do município.

O **PublicGov-RAG** implementa uma **pipeline híbrida e inteligente de extração**:
1. **Extração Nativa Rápida**: Avalia o PDF via `PyPDF`. Se houver camada textual com densidade suficiente (>30 caracteres válidos por página), o texto nativo é indexado diretamente em milissegundos.
2. **Fallback Automático com OCR**: Caso o arquivo seja composto por páginas escaneadas, o sistema aciona automaticamente o `pdf2image` (renderização via Poppler a 300 DPI) em conjunto com o `Tesseract OCR` configurado com pacote de idioma em português (`por`), garantindo que nenhum documento assinado ou escaneado seja ignorado.

---

## 🏗️ 4. Arquitetura da Solução

```mermaid
flowchart TD
    subgraph Ingestao ["1. Pipeline de Ingestão e Indexação"]
        A[Arquivos PDF / Pautas / Leis] --> B{Possui texto nativo?}
        B -- Sim --> C[PyPDFLoader]
        B -- Não / Escaneado --> D[Poppler + Tesseract OCR 'por']
        C --> E[Texto Extraído & Metadados doc_type]
        D --> E
        E --> F[RecursiveCharacterTextSplitter<br/>chunk_size: 1000 | overlap: 150]
        F --> G[Embedding Factory<br/>MiniLM-L12-v2 ou EmbeddingGemma 2]
        G --> H[(PostgreSQL + pgvector)]
        E --> I[(PostgreSQL DocumentModel)]
    end

    subgraph Consulta ["2. Agente LangGraph, Busca Híbrida & MCP"]
        J[Pergunta via REST /api/v1/query/ask ou MCP /mcp] --> K[Agente LangGraph - Roteador & Tool Calling]
        K --> L1[Busca Vetorial pgvector]
        K --> L2[Busca Lexical BM25]
        H -.-> L1
        H -.-> L2
        L1 --> M[Reciprocal Rank Fusion - RRF]
        L2 --> M
        M --> N[Cross-Encoder Reranker - FlashRank]
        N --> O[LLM gemini-2.5-flash]
        O --> P[Resposta Fundamentada + Fontes + tools_used]
        P --> Q[(PostgreSQL QueryLogModel - Auditoria)]
        K -. Callbacks .-> R[Langfuse Observability]
    end
```

### Principais Componentes:
* **API REST & Servidor MCP**: [FastAPI](https://fastapi.tiangolo.com/) com validação estrita via [Pydantic V2](https://docs.pydantic.dev/) e servidor **MCP (Model Context Protocol)** via [FastMCP](https://gofastmcp.com/) montado em `/mcp` (e executável via `stdio`).
* **Agente & Orquestração**: [LangGraph](https://www.langchain.com/langgraph) com *tool calling* para rotear entre consulta legislativa, pautas/moções, catálogo de documentos ou pedido de esclarecimento ao cidadão.
* **Busca Híbrida & Reranking**: Fusão de busca vetorial (`pgvector`) + busca lexical (`rank_bm25` com tokenização para termos legislativos exatos como `PLC nº 67/2025` e `Resolução nº 1.252/2016`) via **Reciprocal Rank Fusion (RRF)**, seguida de **Cross-Encoder Reranker** (`FlashRank`).
* **Modelo de Linguagem (LLM)**: `gemini-2.5-flash` via `langchain-google-genai` (configurável em `GEMINI_MODEL`) com temperatura baixa (`0.1`) para respostas factuais e estritamente aderentes aos documentos indexados.
* **Modelos de Embeddings (Configuráveis & Benchmarkáveis)**:
  * Padrão leve: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384d).
  * Opcional de alta precisão: `google/embeddinggemma-2` com *Task-Steered Prompts* (`SearchQuery` / `Document`) e truncamento **Matryoshka** (`128`, `256`, `512` ou `768` dimensões) em coleções isoladas no `pgvector`.
* **Banco Relacional & Vector Store Unificados**: **PostgreSQL 16 + `pgvector`** gerenciado via SQLAlchemy e `langchain-postgres` (`PGVector`), incluindo auditoria com telemetria (`latency_ms`, `prompt_tokens`, `completion_tokens` e `estimated_cost_usd`) em `QueryLogModel`.
* **Observabilidade & Evals**: Tracing nativo do LangChain via **Langfuse** (Cloud ou self-hosted via `docker compose --profile langfuse up -d`) e suíte automatizada em `evals/` com **Golden Dataset** (`evals/golden_dataset.json`), comparação de prompts (`v1` simples vs. `v2` restritivo) via **RAGAS** (*Faithfulness* e *Answer Relevancy*), precisão de citação de fontes, taxa de abstenção e benchmark de embeddings.

---

## 🚀 5. Instalação e Execução

### Opção A: Executando via Docker Compose (Recomendado)
O método com Docker já inclui o ambiente Linux com **Poppler** e **Tesseract OCR (Português)** pré-instalados:

1. Clone o repositório e navegue até a pasta:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd PublicGov-RAG
   ```

2. Crie e configure o arquivo `.env` a partir de `.env.example`:
   ```env
   GOOGLE_API_KEY=sua_chave_do_google_ai_studio_aqui
   GEMINI_MODEL=gemini-2.5-flash

   # Opcional: Langfuse Observability
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   LANGFUSE_HOST=https://cloud.langfuse.com

   # Opcional: EmbeddingGemma 2 (requer aceite de licença no HuggingFace)
   # EMBEDDING_MODEL=google/embeddinggemma-2
   # EMBEDDING_DIM=256
   # HF_TOKEN=hf_...
   ```

3. Suba os containers (PostgreSQL + `pgvector` e API):
   ```bash
   docker compose up -d --build
   ```

   *(Opcional)* Para subir também o **Langfuse self-hosted** em `http://localhost:3000`:
   ```bash
   docker compose --profile langfuse up -d --build
   ```
   Em seguida, crie o projeto no painel do Langfuse, copie as chaves `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` para o `.env` com `LANGFUSE_HOST=http://localhost:3000` e reinicie o serviço `api`.

A API estará acessível em `http://localhost:8000`.

---

### Opção B: Executando no Ambiente Local

#### 1. Pré-requisitos
* **Python 3.10+** (recomendado Python 3.11 ou 3.12).
* **Poppler Utilities**:
  * *Linux (Ubuntu/Debian)*: `sudo apt install poppler-utils tesseract-ocr tesseract-ocr-por`
  * *Windows*: Baixe o Poppler para Windows e adicione o diretório `bin/` às variáveis de ambiente (PATH), assim como o instalador do Tesseract OCR com o pacote `por.traineddata`.

#### 2. Instalação dos Pacotes Python
```bash
python -m venv venv

# No Windows:
.\venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

#### 3. Configuração do `.env`
Crie o arquivo `.env` na raiz do projeto:
```env
GOOGLE_API_KEY=AIzaSy...
```

#### 4. Inicialização do Servidor
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

A documentação interativa (Swagger UI) estará disponível em:
👉 **`http://localhost:8000/docs`**

---

## 📥 6. Como Indexar Documentos

### Indexação em Lote (Batch) nas 8 categorias `doc_type`
Para processar múltiplos documentos de uma vez:

1. Deposite os arquivos `.pdf` na pasta `pautas_camara/` (ou organize em subpastas nomeadas com cada uma das 8 categorias: `pautas_camara/Pauta_Sessao/`, `pautas_camara/Ata_Sessao/`, `pautas_camara/Projeto_de_Lei/`, `pautas_camara/Lei_Municipal/`, `pautas_camara/Mocao/`, `pautas_camara/Parecer_Comissao/`, `pautas_camara/Requerimento_Legislativo/`, `pautas_camara/Regimento_e_LOM/`).
2. Execute o script de envio automatizado:
   ```bash
   python batch_upload.py
   ```
O script enviará cada PDF para a API, que realizará a validação, extração (com OCR se necessário), chunking, inserção no banco vetorial e exibirá o resumo de cobertura por `doc_type`.

### Indexação Individual via API
Você pode enviar documentos individuais via `curl` ou pela documentação do Swagger:
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@pautas_camara/4429.pdf" \
  -F "doc_type=Mocao"
```

---

## 💬 7. Como Consultar o RAG

Envie uma requisição `POST` para o endpoint `/api/v1/query/ask`:

```bash
curl -X POST "http://localhost:8000/api/v1/query/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é a justificativa da Moção de Apoio referente ao teto do MEI?",
    "doc_type_filter": "Mocao"
  }'
```

### Exemplo de Resposta Retornada:
```json
{
  "question": "Qual é a justificativa da Moção de Apoio referente ao teto do MEI?",
  "answer": "A Moção de Apoio ao Projeto de Lei Complementar nº 67/2025 justifica que o número de Microempreendedores Individuais (MEIs) no Brasil dobrou entre 2018 e 2025. Contudo, o teto anual de faturamento de R$ 81 mil encontra-se defasado pela inflação desde 2018, podendo desestimular o crescimento e formalização da economia.",
  "sources": [
    "4429.pdf"
  ],
  "tools_used": [
    "consultar_pautas_e_votacoes"
  ]
}
```

---

## 📡 8. Endpoints da API e Servidor MCP

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/health` | Verifica saúde da API, modelo Gemini e configuração de embeddings/`pgvector`. |
| `GET` | `/api/v1/documents/` | Lista os documentos legislativos catalogados no PostgreSQL. |
| `POST` | `/api/v1/documents/upload` | Faz upload de um PDF, extrai texto (com OCR fallback), gera chunks e indexa no `pgvector`. |
| `POST` | `/api/v1/query/ask` | Executa o agente LangGraph com busca híbrida (BM25 + vetorial + RRF), reranking e telemetria. |
| `GET` | `/api/v1/query/history` | Retorna o histórico de auditoria das perguntas, ferramentas acionadas, latência, tokens, custo e respostas. |
| `GET` | `/api/v1/query/metrics` | Retorna o consolidado de telemetria (`total_queries`, `avg_latency_ms`, tokens e custo estimado). |
| `ALL` | `/mcp` | Endpoint HTTP/Streamable do servidor **MCP** (`FastMCP`). |
| `GET` | `/docs` | Interface gráfica interativa Swagger UI para teste de todos os endpoints. |

### Conectando via MCP (`stdio` para Claude Desktop / Cursor)
```bash
python -m app.mcp_server
```
Ferramentas expostas pelo MCP: `consultar_legislacao_municipal`, `consultar_pautas_e_votacoes`, `listar_documentos_camara` e `perguntar_oraculo_legislativo`.

---

## 🧪 9. Evals Automatizadas (Golden Dataset + RAGAS) e Benchmark de Embeddings

A pasta `evals/` contém o **Golden Dataset** ([`evals/golden_dataset.json`](evals/golden_dataset.json)) com **30 perguntas reais** (25 respondíveis + 5 sem resposta/fora de escopo para testar abstenção e bloqueio de alucinação):

```bash
# 1. Verificar cobertura atual de documentos indexados nas 8 categorias doc_type
python -m evals.run_eval --coverage-only

# 2. Suíte comparativa Prompt v1 (simples) vs. Prompt v2 (restritivo) com RAGAS
python -m evals.run_eval --prompts v1 v2

# 3. Apenas métricas de recuperação, citação de fontes e abstenção (sem juiz RAGAS)
python -m evals.run_eval --prompts v1 v2 --skip-ragas

# 4. Benchmark comparativo de retrieval (Vetorial vs Híbrido+RRF vs Reranker; MiniLM vs EmbeddingGemma 2)
python -m evals.benchmark_embeddings --models minilm --reindex
```

Os relatórios são salvos automaticamente em `evals/results/latest_report.json` e `evals/results/prompt_comparison.md`.

### Registro das Métricas Reais (após execução com `GOOGLE_API_KEY` e lote completo indexado)

| Métrica | Valor Obtido (`v2`) | Observação |
| :--- | :---: | :--- |
| **Documentos indexados** | _executar `--coverage-only` após upload_ | Contagem real em `DocumentModel` (`documents`) |
| **Fidelidade ao contexto (*Faithfulness*)** | _executar `evals.run_eval --prompts v1 v2`_ | Calculado pelo juiz RAGAS |
| **Precisão na citação de fontes** | _executar `evals.run_eval --prompts v1 v2`_ | Citação explícita de `source_file` + bloqueio de falsa citação |

---

## 📂 10. Estrutura do Repositório

```text
PublicGov-RAG/
├── app/
│   ├── api/
│   │   ├── deps.py                 # Injeção de dependências (Sessão PostgreSQL)
│   │   └── v1/
│   │       ├── documents.py        # Upload, indexação e listagem de PDFs
│   │       ├── query.py            # Consulta via agente e histórico de auditoria
│   │       └── router.py           # Agregador de rotas da API v1
│   ├── core/
│   │   ├── config.py               # Configurações via Pydantic Settings (.env)
│   │   ├── constants.py            # As 8 categorias oficiais de doc_type
│   │   ├── observability.py        # CallbackHandler e flush do Langfuse
│   │   └── telemetry.py            # Extração de tokens e estimativa de custo USD
│   ├── db/
│   │   ├── models.py               # Modelos relacionais + migração de telemetria
│   │   ├── session.py              # Engine e sessão SQLAlchemy (PostgreSQL)
│   │   └── vector_store.py         # PGVector no PostgreSQL + leitura para BM25
│   ├── schemas/
│   │   └── query.py                # Schemas Pydantic de requisição/resposta
│   ├── services/
│   │   ├── agent_service.py        # Agente LangGraph (prompts v1/v2, tool calling, telemetria)
│   │   ├── embedding_factory.py    # Singleton de embeddings (MiniLM e EmbeddingGemma 2)
│   │   ├── pdf_service.py          # Extração de PDFs, OCR (Tesseract) e chunking
│   │   ├── rag_service.py          # Orquestração da consulta e auditoria no banco
│   │   └── retrieval_service.py    # Busca híbrida (BM25 + pgvector + RRF) + FlashRank
│   ├── mcp_server.py               # Servidor MCP (FastMCP) HTTP e stdio
│   └── main.py                     # Ponto de entrada FastAPI + mount /mcp
├── evals/
│   ├── golden_dataset.json         # 30 perguntas reais (25 respondíveis + 5 abstenção)
│   ├── dataset.json                # Dataset inicial (18 perguntas)
│   ├── sample_corpus.json          # Chunks extraídos para benchmark reproduzível
│   ├── benchmark_embeddings.py     # Benchmark MiniLM vs EmbeddingGemma 2 (Matryoshka)
│   └── run_eval.py                 # Evals comparativas (v1 vs v2) com RAGAS e citação de fontes
├── pautas_camara/                  # Pasta para depósito de PDFs para indexação em lote
├── storage/uploads/                # PDFs enviados para a API
├── batch_upload.py                 # Script para automação de upload em lote
├── docker-compose.yml              # Orquestração API + PostgreSQL/pgvector
├── .dockerfile                     # Container Python 3.12 com Poppler e Tesseract OCR
├── .env.example                    # Modelo de variáveis de ambiente
├── requirements.txt                # Dependências Python do projeto
└── README.md                       # Documentação completa do projeto
```

---

## 🔒 11. Governança e Melhores Práticas

1. **Rastreabilidade e Fontes Citadas**: Toda resposta gerada pelo sistema devolve obrigatoriamente a lista de arquivos fonte utilizados (`sources`), permitindo que servidores e cidadãos verifiquem o documento original para fins formais.
2. **Minimização de Alucinações**: O prompt do sistema orienta expressamente o modelo a informar quando uma matéria não for localizada no contexto documental indexado, evitando suposições fora da legislação formal.
3. **Padronização de Nomenclatura**: Ao indexar novos arquivos, recomenda-se nomeá-los com prefixos claros (ex.: `PLO_12_2025.pdf`, `PAUTA_SO_08_2025.pdf`, `MOCAO_02_2025.pdf`), facilitando a identificação imediata na lista de fontes.

---

<p align="center">
  <b>PublicGov-RAG</b> — Transparência e eficiência a serviço da democracia e do cidadão de Santana do Livramento.
</p>
