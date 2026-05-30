# RAG Document Q&A System

A production-ready Retrieval-Augmented Generation (RAG) system that lets you upload documents (PDF, DOCX, TXT) and ask questions about them using GPT-4o and ChromaDB.

## Architecture

```
User uploads PDF/DOCX/TXT
        ↓
Text Extraction (PyMuPDF / Docx2txt / TextLoader)
        ↓
Chunking (RecursiveCharacterTextSplitter, ~500 tokens)
        ↓
Embedding (OpenAI text-embedding-3-small)
        ↓
Store vectors in ChromaDB (local)
        ↓
User asks a question
        ↓
Question → Embedding → Similarity Search in ChromaDB
        ↓
Top-4 relevant chunks retrieved
        ↓
Chunks + Question → GPT-4o (custom prompt)
        ↓
Answer + source filenames returned to user
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend API | FastAPI |
| LLM | OpenAI GPT-4o |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (local) |
| Orchestration | LangChain |
| Document Parsing | PyMuPDF, Docx2txt |
| Testing | pytest |
| CI/CD | GitHub Actions |

## Project Structure

```
rag-document-qa/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── ingest.py        # Document loading + chunking + embedding
│   ├── retriever.py     # Vector search logic
│   ├── qa_chain.py      # LangChain RAG chain with custom prompt
│   └── utils.py         # Helper functions
├── frontend/
│   └── streamlit_app.py # Streamlit UI
├── data/uploads/        # Uploaded docs (gitignored)
├── vectorstore/         # ChromaDB storage (gitignored)
├── tests/
│   └── test_ingest.py   # Unit tests
├── .github/workflows/
│   └── ci.yml           # GitHub Actions CI
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
└── README.md
```

## Setup

### Prerequisites
- Python 3.11+
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/rag-document-qa.git
cd rag-document-qa

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Running the App

**Terminal 1 — Start the FastAPI backend:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Start the Streamlit frontend:**
```bash
streamlit run frontend/streamlit_app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health status |
| POST | `/upload` | Upload & ingest a document |
| POST | `/ask` | Ask a question |
| DELETE | `/vectorstore` | Clear all indexed documents |

**Example — upload a document:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@my_document.pdf"
```

**Example — ask a question:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```

## Running with Docker

```bash
docker build -t rag-doc-qa .
docker run -p 8000:8000 --env-file .env rag-doc-qa
```

## Running Tests

```bash
pytest tests/ -v
```

## Use Cases

- **HR Policy Bot** — Upload your employee handbook and let staff ask questions
- **Legal Document Reader** — Instantly query contracts, agreements, and regulations
- **Research Assistant** — Upload papers and ask about findings, methodology, or conclusions
- **Customer Support** — Index product documentation for automated Q&A

## Future Improvements

- [ ] Multi-document cross-referencing with metadata filtering
- [ ] Streaming responses for real-time answer display
- [ ] User authentication and per-user document namespaces
- [ ] Support for scanned PDFs via OCR (Tesseract)
- [ ] Pinecone / Weaviate as a production vector DB option
- [ ] Conversation memory for follow-up questions
- [ ] Evaluation framework (RAGAS) for answer quality scoring
