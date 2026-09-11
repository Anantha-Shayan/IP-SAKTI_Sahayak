"""FastAPI application for IP-SAKTI Sahayak."""

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.retrieval.query import SearchQuery, SearchResult
from backend.rag.generation import RAGPipeline

router = APIRouter()

# Global instances to be initialized by the app
retriever = None
rag_pipeline = None

class RAGQuery(BaseModel):
    query: str
    top_k_retrieve: int = 20
    top_k_rerank: int = 5
    filters: Optional[Dict[str, Any]] = None

class RAGResponse(BaseModel):
    answer: str
    context: str
    sources: List[Dict[str, Any]]

@router.post("/search", response_model=List[SearchResult])
def search_endpoint(query: SearchQuery):
    if not retriever:
        raise HTTPException(status_code=500, detail="Retriever not initialized")
    
    if hasattr(retriever, "search") and "filters" in retriever.search.__code__.co_varnames:
        results = retriever.search(query.query, top_k=query.top_k, filters=query.filters)
    else:
        results = retriever.search(query.query, top_k=query.top_k)
        
    return results

@router.post("/rag", response_model=RAGResponse)
def rag_endpoint(query: RAGQuery):
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RAG pipeline not initialized")
        
    response = rag_pipeline.answer(
        query=query.query,
        top_k_retrieve=query.top_k_retrieve,
        top_k_rerank=query.top_k_rerank,
        filters=query.filters
    )
    return RAGResponse(**response)

def create_app() -> FastAPI:
    app = FastAPI(title="IP-SAKTI Sahayak API")
    app.include_router(router)
    return app
