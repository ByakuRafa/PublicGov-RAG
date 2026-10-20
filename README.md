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
        F --> G[HuggingFace Embeddings<br/>paraphrase-multilingual-MiniLM-L12-v2]
        G --> H[(ChromaDB Vector Store)]
        E --> I[(SQLite DocumentModel)]
    end

    subgraph Consulta ["2. Pipeline de Consulta RAG"]
        J[Pergunta do Cidadão / Servidor] --> K[Filtro opcional por doc_type]
        K --> L[Retriever Semântico ChromaDB k=4]
        H -. Busca Vetorial .-> L
        L --> M[Formatação do Contexto Restrito]
        M --> N[Prompt Especializado do Oráculo]
        J --> N
        N --> O[LLM Google Gemini Flash]
        O --> P[Resposta Fundamentada + Fontes Citadas]
        P --> Q[(SQLite QueryLogModel - Auditoria)]
    end
```

### Principais Componentes:
* **API REST**: [FastAPI](https://fastapi.tiangolo.com/) com validação estrita via [Pydantic V2](https://docs.pydantic.dev/).
* **Orquestração RAG**: [LangChain](https://www.langchain.com/) gerenciando chains, templates de prompt e integração com retrievers.
* **Modelo de Linguagem (LLM)**: `gemini-3.6-flash` via `langchain-google-genai` com temperatura baixa (`0.1`) para respostas factuais e estritamente aderentes aos documentos indexados.
* **Modelo de Embeddings**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` executado localmente, otimizado para a língua portuguesa.
* **Vector Store**: [ChromaDB](https://www.trychroma.com/) com persistência local em `./storage/chroma_db`.
* **Banco Relacional & Auditoria**: SQLite (`./storage/publicgov.db`) gerenciado via [SQLAlchemy](https://www.sqlalchemy.org/) para log de consultas e catálogo de documentos.

---

## 🚀 5. Instalação e Execução

### Opção A: Executando via Docker Compose (Recomendado)
O método com Docker já inclui o ambiente Linux com **Poppler** e **Tesseract OCR (Português)** pré-instalados:

1. Clone o repositório e navegue até a pasta:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd PublicGov-RAG
   ```

2. Crie e configure o arquivo `.env`:
   ```env
   GOOGLE_API_KEY=sua_chave_do_google_ai_studio_aqui
   ```

3. Suba o container:
   ```bash
   docker compose up -d --build
   ```

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

### Indexação em Lote (Batch)
Para processar múltiplos documentos de uma vez (como pautas e moções):

1. Deposite os arquivos `.pdf` na pasta `pautas_camara/`.
2. Execute o script de envio automatizado:
   ```bash
   python batch_upload.py
   ```
O script enviará cada PDF para a API, que realizará a validação, extração (com OCR se necessário), chunking e inserção no banco vetorial.

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
  "answer": "A Moção de Apoio ao Projeto de Lei Complementar nº 67/2025 justifica que o número de Microempreendedores Individuais (MEIs) no Brasil dobrou entre 2018 e 2025. Contudo, o teto anual de faturamento de R$ 81 mil encontra-se defasado pela inflação desde 2018, podendo desestimular o crescimento e formalização da economia. A proposta propõe elevar o limite para R$ 150 mil anuais com reajuste automático pelo IPCA.",
  "sources": [
    "4429.pdf"
  ]
}
```

---

## 📡 8. Endpoints da API

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/health` | Verifica a saúde operacional da API. |
| `POST` | `/api/v1/documents/upload` | Faz upload de um documento PDF, extrai texto (com OCR fallback), gera chunks e indexa no ChromaDB. |
| `POST` | `/api/v1/query/ask` | Realiza a consulta em linguagem natural utilizando o contexto dos documentos legislativos recuperados. |
| `GET` | `/api/v1/query/history` | Retorna o histórico de auditoria das perguntas e respostas processadas pelo sistema. |
| `GET` | `/docs` | Interface gráfica interativa Swagger UI para teste de todos os endpoints. |

---

## 📂 9. Estrutura do Repositório

```text
PublicGov-RAG/
├── app/
│   ├── api/
│   │   ├── deps.py                 # Injeção de dependências (Sessão de Banco de Dados)
│   │   └── v1/
│   │       ├── documents.py        # Endpoint de upload e indexação de PDFs
│   │       ├── query.py            # Endpoints de consulta RAG e histórico
│   │       └── router.py           # Agregador de rotas da API v1
│   ├── core/
│   │   └── config.py               # Configurações do sistema via Pydantic Settings
│   ├── db/
│   │   ├── models.py               # Modelos relacionais (DocumentModel, QueryLogModel)
│   │   ├── session.py              # Sessão SQLAlchemy do SQLite
│   │   └── vector_store.py         # Configuração do ChromaDB e embeddings HuggingFace
│   ├── schemas/
│   │   └── query.py                # Modelos de validação de requisição/resposta (Pydantic)
│   ├── services/
│   │   ├── pdf_service.py          # Lógica de extração de PDFs, OCR (Tesseract) e chunking
│   │   └── rag_service.py          # Lógica do RAG, prompt do Oráculo e integração com Gemini
│   └── main.py                     # Ponto de entrada FastAPI e ciclo de vida da aplicação
├── pautas_camara/                  # Pasta para depósito de PDFs para indexação em lote
├── storage/                        # Diretório persistido de uploads, ChromaDB e SQLite
│   ├── chroma_db/
│   ├── uploads/
│   └── publicgov.db
├── batch_upload.py                 # Script para automação de upload em lote
├── docker-compose.yml              # Orquestração do container Docker
├── .dockerfile                     # Receita do container com Poppler e Tesseract OCR
├── requirements.txt                # Dependências Python do projeto
└── README.md                       # Documentação completa do projeto
```

---

## 🔒 10. Governança e Melhores Práticas

1. **Rastreabilidade e Fontes Citadas**: Toda resposta gerada pelo sistema devolve obrigatoriamente a lista de arquivos fonte utilizados (`sources`), permitindo que servidores e cidadãos verifiquem o documento original para fins formais.
2. **Minimização de Alucinações**: O prompt do sistema orienta expressamente o modelo a informar quando uma matéria não for localizada no contexto documental indexado, evitando suposições fora da legislação formal.
3. **Padronização de Nomenclatura**: Ao indexar novos arquivos, recomenda-se nomeá-los com prefixos claros (ex.: `PLO_12_2025.pdf`, `PAUTA_SO_08_2025.pdf`, `MOCAO_02_2025.pdf`), facilitando a identificação imediata na lista de fontes.

---

<p align="center">
  <b>PublicGov-RAG</b> — Transparência e eficiência a serviço da democracia e do cidadão de Santana do Livramento.
</p>
