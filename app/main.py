import os
import json
import dotenv
import logging
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google.genai import types

from .utils import setup_context_cache, client

app = FastAPI(title="TaxBuddy-NG: 2026 Advisor")

# Instantiate Cache at startup
tax_cache = setup_context_cache()

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/api/chat")
async def chat_api(
    message: str = Form(...),
    history: str = Form(...), 
    file: Optional[UploadFile] = File(None)
):
    try:
        # 1. Correctly build the current message part
        # The new SDK uses types.Part(text=...) instead of .from_text()
        current_parts = [types.Part(text=message)]
        
        if file:
            file_bytes = await file.read()
            current_parts.append(
                types.Part(inline_data=types.Blob(data=file_bytes, mime_type=file.content_type))
            )

        # 2. Rebuild History using native types.Part(text=...)
        history_data = json.loads(history)
        contents = []
        for msg in history_data:
            contents.append(types.Content(
                role=msg["role"], 
                parts=[types.Part(text=msg["parts"])]
            ))
        
        # Add the latest user message
        contents.append(types.Content(role="user", parts=current_parts))

        # 3. Generate content using the cache name
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=contents,
            config=types.GenerateContentConfig(
                cached_content=tax_cache.name,
                temperature=0.0,  # Zero for expert precision
            )
        )
        
        return {"answer": response.text, "cached": True}

    except Exception as e:
        # This will now log the specific error in your console
        logging.error(f"CRITICAL ERROR: {str(e)}")
        return {"answer": "Strategic analysis interrupted. Please try again."}
    