import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

CHROMA_DIR = "./chroma_policy_db"
PDF_PATH = "policy.pdf"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def ingest():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Could not find {PDF_PATH}. Place it in the project root.")

    print(f"Loading {PDF_PATH}...")
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()
    print(f"Loaded {len(docs)} page(s)")

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunk(s)")

    print(f"Loading embedding model ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("Embedding chunks and writing to Chroma...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )

    print(f"Done. Vectorstore saved to {CHROMA_DIR}")


if __name__ == "__main__":
    ingest()