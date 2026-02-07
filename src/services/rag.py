"""
RAG (Retrieval-Augmented Generation) Service

Knowledge base management and suggested response generation
using vector similarity search.
"""

import json
import os
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

from openai import AsyncOpenAI
from loguru import logger

from src.config import settings


class KnowledgeBase:
    """
    Vector-based knowledge base for suggested responses.
    
    Features:
    - ChromaDB for vector storage
    - OpenAI embeddings
    - Semantic similarity search
    - Response generation
    - Template matching
    """
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        """
        Initialize knowledge base.
        
        Args:
            collection_name: ChromaDB collection name
            persist_directory: Directory for persistent storage
        """
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        self._chroma_client = None
        self._collection = None
        self._initialized = False
        
        logger.info(f"KnowledgeBase initialized with collection: {self.collection_name}")
    
    async def initialize(self) -> None:
        """Initialize ChromaDB and create collection."""
        
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # Create persist directory if needed
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize ChromaDB client
            self._chroma_client = chromadb.Client(ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))
            
            # Get or create collection
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Support ticket knowledge base"}
            )
            
            self._initialized = True
            logger.info(f"ChromaDB collection '{self.collection_name}' ready")
            
        except ImportError:
            logger.warning("ChromaDB not available, using in-memory fallback")
            self._collection = InMemoryCollection()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._collection = InMemoryCollection()
            self._initialized = True
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI."""
        
        try:
            response = await self.client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text[:8000]  # Limit length
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536
    
    async def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a document to the knowledge base.
        
        Args:
            doc_id: Unique document identifier
            content: Document content
            metadata: Additional metadata (category, tags, etc.)
            
        Returns:
            bool: Success status
        """
        
        await self.initialize()
        
        try:
            # Generate embedding
            embedding = await self._get_embedding(content)
            
            # Add to collection
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata or {}]
            )
            
            logger.info(f"Added document {doc_id} to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    async def add_resolved_ticket(
        self,
        ticket_id: str,
        question: str,
        response: str,
        category: str,
        rating: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a resolved ticket to knowledge base for future reference.
        
        Args:
            ticket_id: Original ticket ID
            question: Customer's question/issue
            response: Agent's response
            category: Ticket category
            rating: Customer satisfaction rating
            metadata: Additional context
            
        Returns:
            bool: Success status
        """
        
        # Only add well-rated responses
        if rating is not None and rating < 3:
            logger.debug(f"Skipping low-rated ticket {ticket_id}")
            return False
        
        # Combine question and response for better matching
        content = f"Question: {question}\n\nResponse: {response}"
        
        doc_metadata = {
            "type": "resolved_ticket",
            "ticket_id": ticket_id,
            "category": category,
            "rating": rating,
            "added_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        return await self.add_document(
            doc_id=f"ticket_{ticket_id}",
            content=content,
            metadata=doc_metadata
        )
    
    async def add_faq(
        self,
        faq_id: str,
        question: str,
        answer: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Add FAQ entry to knowledge base.
        
        Args:
            faq_id: Unique FAQ identifier
            question: FAQ question
            answer: FAQ answer
            category: Related category
            tags: Search tags
            
        Returns:
            bool: Success status
        """
        
        content = f"FAQ: {question}\n\nAnswer: {answer}"
        
        metadata = {
            "type": "faq",
            "question": question,
            "category": category,
            "tags": tags or [],
            "added_at": datetime.utcnow().isoformat()
        }
        
        return await self.add_document(
            doc_id=f"faq_{faq_id}",
            content=content,
            metadata=metadata
        )
    
    async def find_similar(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find similar documents in knowledge base.
        
        Args:
            query: Search query
            category: Filter by category
            limit: Maximum results
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of similar documents with scores
        """
        
        await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            
            # Build where filter
            where_filter = None
            if category:
                where_filter = {"category": category}
            
            # Query collection
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )
            
            # Process results
            documents = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    # Calculate similarity score (1 - distance for cosine)
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    score = max(0, 1 - distance)
                    
                    if score >= min_score:
                        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                        doc_id = results["ids"][0][i] if results.get("ids") else f"doc_{i}"
                        
                        documents.append({
                            "id": doc_id,
                            "content": doc,
                            "score": round(score, 3),
                            "metadata": metadata
                        })
            
            logger.info(f"Found {len(documents)} similar documents for query")
            return documents
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    async def generate_suggested_responses(
        self,
        ticket_content: str,
        category: Optional[str] = None,
        language: str = "tr",
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate suggested responses for a ticket.
        
        Combines RAG with AI generation for best results.
        
        Args:
            ticket_content: Ticket content
            category: Ticket category
            language: Response language
            limit: Number of suggestions
            
        Returns:
            List of suggested responses
        """
        
        
        suggestions = []
        
        # 1. Find similar documents
        similar_docs = await self.find_similar(
            query=ticket_content,
            category=category,
            limit=5
        )
        
        # Extract responses from similar documents
        for doc in similar_docs[:limit]:
            content = doc["content"]
            
            # Try to extract just the response part
            if "Response:" in content:
                response = content.split("Response:")[-1].strip()
            elif "Answer:" in content:
                response = content.split("Answer:")[-1].strip()
            else:
                response = content
            
            suggestions.append({
                "content": response,
                "source": "rag",
                "source_id": doc["id"],
                "relevance_score": doc["score"],
                "metadata": doc["metadata"]
            })
        
        # 2. Generate AI response (always try, even without similar docs)
        if len(suggestions) < limit:
            try:
                ai_response = await self._generate_ai_response(
                    ticket_content=ticket_content,
                    similar_docs=similar_docs[:3] if similar_docs else [],
                    category=category,
                    language=language
                )
                
                if ai_response:
                    suggestions.append({
                        "content": ai_response,
                        "source": "ai_generated",
                        "source_id": None,
                        "relevance_score": 0.9,
                        "metadata": {"based_on": [d["id"] for d in similar_docs[:3]] if similar_docs else []}
                    })
            except Exception as e:
                logger.warning(f"AI response generation failed: {e}")
        
        return suggestions[:limit]
    
    async def _generate_ai_response(
        self,
        ticket_content: str,
        similar_docs: List[Dict],
        category: Optional[str],
        language: str = "tr"
    ) -> Optional[str]:
        """Generate AI response based on similar documents or directly from GPT."""
        
        # Build context from similar docs (if any)
        context_parts = []
        for doc in similar_docs:
            context_parts.append(f"Reference:\n{doc['content']}\n")
        
        context = "\n---\n".join(context_parts) if context_parts else ""
        
        # Determine language instruction
        lang_instruction = "Respond in Turkish." if language == "tr" else f"Respond in {language}."
        
        if context:
            # RAG-based response with references
            system_prompt = f"""You are a professional customer support expert. Generate a concise and helpful response based on the provided reference responses.

Rules:
1. Don't copy references directly, adapt them to the specific question
2. Be professional and direct. Avoid unnecessary pleasantries.
3. Keep it very concise. Do not write long paragraphs.
4. Use bullet points for steps if suitable.
5. Limit response to 3-4 sentences if possible.
6. {lang_instruction}"""
            
            user_prompt = f"""Customer message:
{ticket_content}

Reference responses:
{context}

Write an appropriate response for this customer:"""
        else:
            # Direct GPT response (no KB references)
            category_context = f"This is a {category} inquiry." if category else ""
            system_prompt = f"""You are a professional customer support expert for a technology company. Provide concise, accurate, and helpful responses.

Rules:
1. Be professional but brief.
2. Provide clear and actionable information immediately.
3. Avoid filler words and long-winded explanations.
4. If you don't know specific details, ask clarifying questions directly.
5. Limit response to 3-4 sentences if possible.
6. {lang_instruction}"""
            
            user_prompt = f"""Customer message:
{ticket_content}

{category_context}

Write a professional and helpful response for this customer:"""
        
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from knowledge base."""
        
        await self.initialize()
        
        try:
            self._collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        
        await self.initialize()
        
        try:
            count = self._collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


class InMemoryCollection:
    """Simple in-memory fallback when ChromaDB is not available."""
    
    def __init__(self):
        self.documents = {}
        self.embeddings = {}
        self.metadatas = {}
    
    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict]
    ):
        for i, doc_id in enumerate(ids):
            self.documents[doc_id] = documents[i]
            self.embeddings[doc_id] = embeddings[i]
            self.metadatas[doc_id] = metadatas[i]
    
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        # Simple cosine similarity
        import math
        
        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0
        
        query_emb = query_embeddings[0]
        results = []
        
        for doc_id, emb in self.embeddings.items():
            # Apply filter
            if where:
                meta = self.metadatas.get(doc_id, {})
                if not all(meta.get(k) == v for k, v in where.items()):
                    continue
            
            score = cosine_sim(query_emb, emb)
            results.append((doc_id, score))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:n_results]
        
        return {
            "ids": [[r[0] for r in results]],
            "documents": [[self.documents[r[0]] for r in results]],
            "distances": [[1 - r[1] for r in results]],
            "metadatas": [[self.metadatas.get(r[0], {}) for r in results]]
        }
    
    def delete(self, ids: List[str]):
        for doc_id in ids:
            self.documents.pop(doc_id, None)
            self.embeddings.pop(doc_id, None)
            self.metadatas.pop(doc_id, None)
    
    def count(self) -> int:
        return len(self.documents)


# Singleton instance
knowledge_base = KnowledgeBase()
