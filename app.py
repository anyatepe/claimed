"""
FastAPI application with summarization and classification endpoints.
"""
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, ConfigDict

app = FastAPI(
    title="Summarization and Classification API",
    description="API endpoints for text summarization and classification",
    version="1.0.0",
)

# Request/Response Models for /v1/summarize
class RetrievalConfig(BaseModel):
    """Retrieval configuration for summarization."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "k": 5
            }
        }
    )
    k: int = Field(..., description="Number of retrieval results", gt=0, examples=[5])

class SummarizeRequest(BaseModel):
    """Request model for summarization endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input": "Artificial intelligence is transforming the way we work and live. Machine learning algorithms can now process vast amounts of data to identify patterns and make predictions. Deep learning, a subset of machine learning, uses neural networks to solve complex problems.",
                "retrieval": {
                    "k": 5
                },
                "max_tokens": 100,
                "style": "bullet"
            }
        }
    )
    input: str = Field(..., description="Input text to summarize", min_length=1)
    retrieval: Optional[RetrievalConfig] = Field(None, description="Optional retrieval configuration")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens in summary", gt=0)
    style: Literal["bullet", "abstract"] = Field("abstract", description="Summary style")

class SummarizeResponse(BaseModel):
    """Response model for summarization endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "AI is transforming work and life through machine learning and deep learning."
            }
        }
    )
    summary: str = Field(..., description="Generated summary")

# Request/Response Models for /v1/classify
class ClassifyRequest(BaseModel):
    """Request model for classification endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input": "I love this product! It's amazing and works perfectly.",
                "labels": ["positive", "negative", "neutral"],
                "multi_label": False
            }
        }
    )
    input: str = Field(..., description="Input text to classify", min_length=1)
    labels: list[str] = Field(..., description="List of possible labels", min_length=1)
    multi_label: bool = Field(False, description="Whether to allow multiple labels")

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[str]) -> list[str]:
        """Validate that labels list is not empty and contains unique strings."""
        if not v:
            raise ValueError("labels list cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("labels must be unique")
        return v


class ClassifyResponse(BaseModel):
    """Response model for classification endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "labels": ["positive"],
                "confidence": {
                    "positive": 0.95,
                    "negative": 0.03,
                    "neutral": 0.02
                }
            }
        }
    )
    labels: list[str] = Field(..., description="Predicted labels")
    confidence: dict[str, float] = Field(..., description="Confidence scores for each label")

@app.post("/v1/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """
    Summarize input text.
    
    This endpoint accepts text input and returns a summary based on the specified style
    (bullet points or abstract). Optional retrieval and max_tokens parameters can be
    provided to control the summarization process.
    """
    # Placeholder logic: echo the input as summary
    # In a real implementation, this would call a summarization model
    summary_text = request.input
    
    return SummarizeResponse(summary=summary_text)

@app.post("/v1/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest) -> ClassifyResponse:
    """
    Classify input text into one or more labels.
    
    This endpoint accepts text input and a list of possible labels, then returns
    the predicted label(s) along with confidence scores. If multi_label is True,
    multiple labels can be returned.
    """
    # Placeholder logic: echo the first label with dummy confidence scores
    # In a real implementation, this would call a classification model
    predicted_labels = [request.labels[0]] if not request.multi_label else request.labels[:1]
    
    # Generate dummy confidence scores
    confidence_scores = {}
    for label in request.labels:
        if label == predicted_labels[0]:
            confidence_scores[label] = 0.9
        else:
            confidence_scores[label] = 0.1 / (len(request.labels) - 1) if len(request.labels) > 1 else 0.0
    
    return ClassifyResponse(labels=predicted_labels, confidence=confidence_scores)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
