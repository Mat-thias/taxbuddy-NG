import os
import datetime
import logging
import dotenv

import pypdf
from typing import Optional
from google import genai
from google.genai import types

from .constants import TAX_SYSTEM_PROMPT, RAG_FILES_DIR, READ_RAG_FILES

logging.basicConfig(level=logging.INFO, filename="log.log", filemode="w")

dotenv.load_dotenv(dotenv_path="app/secrets/.env")

# Initialize Client
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def load_knowledge_base(directory, read_rag_file: Optional[str] = None):
    knowledge_text = "=== NIGERIA TAX ACT 2025 REFERENCE DOCUMENTS ===\n"
    if not os.path.exists(directory):
        return ""
    
    # Simple caching of the text extraction to save time
    if read_rag_file and os.path.exists(os.path.join(directory, read_rag_file)):
        with open(os.path.join(directory, read_rag_file), "r") as f:
            return f.read()
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            if filename.endswith(".pdf"):
                reader = pypdf.PdfReader(filepath)
                text = "".join([page.extract_text() for page in reader.pages])
                knowledge_text += f"\nFILE: {filename}\n{text}\n"
            elif filename.endswith(".txt"):
                with open(filepath, "r") as f:
                    knowledge_text += f"\nFILE: {filename}\n{f.read()}\n"
        except Exception as e:
            logging.error(f"Error loading {filename}: {e}")

    if read_rag_file:
        with open(os.path.join(directory, read_rag_file), "w") as f:
            f.write(knowledge_text)

    return knowledge_text

def setup_context_cache():
    """
    Uses the new SDK client.caches to create or retrieve a cache.
    """
    cache_display_name = "nigeria-tax-act-2025-cache"
    
    # Reuse if exists
    for c in client.caches.list():
        if c.display_name == cache_display_name:
            return c

    knowledge = load_knowledge_base(RAG_FILES_DIR, READ_RAG_FILES)
    
    return client.caches.create(
        model="gemini-2.0-flash-001",
        config=types.CreateCachedContentConfig(
            display_name=cache_display_name,
            system_instruction=TAX_SYSTEM_PROMPT,
            # FIXED: Use types.Part(text=...)
            contents=[types.Content(parts=[types.Part(text=knowledge)])],
            ttl="86400s", 
        )
    )