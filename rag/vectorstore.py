from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

CHROMA_DIR = "./chroma_policy_db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings():
    """Returns the embedding function. Must match what ingest.py used,
    otherwise query vectors won't line up with stored vectors."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def load_vectorstore():
    """Loads the existing Chroma collection built by ingest.py.
    Does NOT create or embed anything — just opens the persisted DB."""
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings()
    )