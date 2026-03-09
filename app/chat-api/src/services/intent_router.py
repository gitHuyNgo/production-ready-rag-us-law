import os
import logging
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from llama_index.llms.openai import OpenAI
from llama_index.core import PromptTemplate

logger = logging.getLogger(__name__)

class QueryIntent(str, Enum):
    DIRECT_ID = "direct_id_lookup"
    SEMANTIC = "semantic_search"
    HYBRID = "hybrid_rag"
    GREETING = "greeting_or_smalltalk"

class IntentAnalysis(BaseModel):
    intent: QueryIntent = Field(description="The primary intent of the user query")
    detected_ids: List[str] = Field(default=[], description="List of US Code identifiers like /us/usc/t1/s1")
    keywords: List[str] = Field(default=[], description="Key legal terms extracted for keyword search")
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")

class LegalIntentRouter:
    def __init__(self):
        self.llm = OpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        
        self.intent_template = PromptTemplate(
            "You are a legal expert assistant analyzing US Code queries.\n"
            "USER QUERY: \"{query}\"\n\n"
            "TASK:\n"
            "1. Intent: Is it a 'direct_id_lookup' (specific section), 'semantic_search' (concepts), or 'hybrid_rag'?\n"
            "2. Identifiers: Extract any US Code IDs (e.g., /us/usc/t1/s1).\n"
            "3. Keywords: Extract 2-3 CORE legal terms (e.g., 'person', 'maritime', 'vessel') for keyword-based graph lookup.\n"
            "Return analysis in structured JSON."
        )

    def route_query(self, query: str) -> IntentAnalysis:
        logger.info(f"Analyzing intent for: {query[:50]}...")
        
        try:
            response = self.llm.structured_predict(
                IntentAnalysis, 
                self.intent_template, 
                query=query
            )
            return response
        except Exception as e:
            logger.error(f"Intent routing failed: {str(e)}")
            return IntentAnalysis(
                intent=QueryIntent.HYBRID,
                reasoning=f"Fallback due to error: {str(e)}"
            )

intent_router = LegalIntentRouter()