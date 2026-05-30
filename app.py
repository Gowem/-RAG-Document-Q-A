import os
import tempfile
import logging
import traceback

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
import chromadb
from chromadb.config import Settings

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
VECTORSTORE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "rag_vectorstore")
FASTEMBED_CACHE = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "fastembed_cache")
os.makedirs(VECTORSTORE_DIR, exist_ok=True)
os.makedirs(FASTEMBED_CACHE, exist_ok=True)
COLLECTION_NAME = "rag_docs"

PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based on the provided document context.
Use the context below to answer the question as thoroughly as possible.
If asked to summarise or explain the document, describe what you can see in the context.
Only say you don't have enough information if the context is truly empty or completely unrelated.

Context:
{context}

Question: {question}
Answer:"""

# ── Init once at startup ──────────────────────────────────────
log.info("Loading embedding model...")
_embeddings = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    cache_dir=FASTEMBED_CACHE,
)
_chroma_client = chromadb.PersistentClient(
    path=VECTORSTORE_DIR,
    settings=Settings(anonymized_telemetry=False),
)
log.info("Server ready at http://localhost:8181")

# ── FastAPI ───────────────────────────────────────────────────
api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_vectorstore() -> Chroma:
    """Always returns a valid Chroma instance, creating the collection if needed."""
    return Chroma(
        client=_chroma_client,
        embedding_function=_embeddings,
        collection_name=COLLECTION_NAME,
    )


def collection_exists() -> bool:
    """Check whether the Chroma collection currently exists."""
    try:
        _chroma_client.get_collection(COLLECTION_NAME)
        return True
    except Exception:
        return False


def load_and_chunk(file_path: str, filename: str):
    """Load a document and split into chunks."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        docs = PyMuPDFLoader(file_path).load()
    elif ext == ".docx":
        docs = Docx2txtLoader(file_path).load()
    elif ext == ".txt":
        try:
            docs = TextLoader(file_path, encoding="utf-8").load()
        except UnicodeDecodeError:
            docs = TextLoader(file_path, encoding="latin-1").load()
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Filter out pages/sections with no extractable text (e.g. image-only pages,
    # empty DOCX tables) — these cause a pydantic validation error downstream.
    docs = [d for d in docs if d.page_content and d.page_content.strip()]

    if not docs:
        raise ValueError(
            f"Document '{filename}' has no readable text. "
            "It may be image-based or password-protected."
        )

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    # Secondary safety filter — ensure every chunk has a string page_content
    chunks = [c for c in chunks if isinstance(c.page_content, str) and c.page_content.strip()]
    for chunk in chunks:
        chunk.metadata["source_file"] = filename
    return chunks


def clear_vectorstore():
    """Delete the Chroma collection (safe to call even if it doesn't exist)."""
    try:
        _chroma_client.delete_collection(COLLECTION_NAME)
        log.info("Vector store cleared.")
    except Exception:
        pass  # Already gone – that's fine


# ── Routes ────────────────────────────────────────────────────
@api.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@api.post("/upload")
def upload(file: UploadFile = File(...)):
    """
    Sync endpoint — FastAPI runs sync functions in a thread pool automatically.
    This avoids the ONNX/asyncio deadlock that occurs on Windows with async def.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(400, f"Unsupported type '{ext}'. Use PDF, DOCX or TXT.")

    contents = file.file.read()
    if not contents:
        raise HTTPException(400, "Uploaded file is empty.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        log.info("Chunking '%s' (%d bytes)...", file.filename, len(contents))
        chunks = load_and_chunk(tmp_path, file.filename)
        log.info("  → %d chunks produced", len(chunks))

        vs = get_vectorstore()

        # Remove old chunks for this file only if the collection is non-empty
        if collection_exists() and _chroma_client.get_collection(COLLECTION_NAME).count() > 0:
            try:
                vs.delete(where={"source_file": file.filename})
                log.info("  → old chunks for '%s' removed", file.filename)
            except Exception as ex:
                log.warning("  → could not delete old chunks (ignored): %s", ex)

        # Batch embedding to avoid memory crash on large documents (>50 chunks)
        BATCH_SIZE = 50
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i: i + BATCH_SIZE]
            vs.add_documents(batch)
            log.info("  → embedded batch %d/%d", min(i + BATCH_SIZE, len(chunks)), len(chunks))
        log.info("  → '%s' ingested successfully", file.filename)
        return {"message": f"'{file.filename}' ingested successfully", "chunks": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        log.error("Upload failed for '%s': %s", file.filename, traceback.format_exc())
        raise HTTPException(500, f"Ingestion error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


class QuestionRequest(BaseModel):
    question: str


@api.post("/ask")
def ask(req: QuestionRequest):
    """Sync endpoint — FastAPI runs this in a thread pool automatically."""
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty.")
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY not set in .env file.")
    if not collection_exists():
        raise HTTPException(400, "No documents have been ingested yet. Please upload a document first.")

    try:
        log.info("Question: %s", req.question)
        vs = get_vectorstore()

        # Check there are actually documents in the store
        col = _chroma_client.get_collection(COLLECTION_NAME)
        doc_count = col.count()
        if doc_count == 0:
            raise HTTPException(400, "The vector store is empty. Please upload a document first.")

        # Use similarity_search directly — this lets us filter out None page_content
        # which is a known bug in langchain-chroma 0.1.4 where _results_to_docs_and_scores
        # can return None for the document text, causing a pydantic ValidationError.
        k = min(6, doc_count)
        raw_docs = vs.similarity_search(req.question, k=k)
        # Guard: skip any doc whose page_content came back as None
        valid_docs = [d for d in raw_docs if isinstance(d.page_content, str) and d.page_content.strip()]

        if not valid_docs:
            return {"answer": "I don't have enough information in the uploaded documents.", "sources": []}

        context = "\n\n".join(d.page_content for d in valid_docs)
        sources = list({d.metadata.get("source_file", "?") for d in valid_docs})

        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=GROQ_API_KEY,
            temperature=0,
            timeout=30,
        )
        filled_prompt = PROMPT_TEMPLATE.replace("{context}", context).replace("{question}", req.question)
        answer = llm.invoke(filled_prompt).content
        log.info("Answer generated. Sources: %s", sources)
        return {"answer": answer, "sources": sources}

    except HTTPException:
        raise
    except Exception as e:
        log.error("Ask failed: %s", traceback.format_exc())
        raise HTTPException(500, f"Error: {e}")


@api.delete("/clear")
def clear():
    clear_vectorstore()
    return {"message": "Cleared"}
