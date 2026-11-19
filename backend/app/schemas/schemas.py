from pydantic import BaseModel, Field


class TextAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=60000, description="News article text, headline, or claim")
    title: str | None = Field(default=None, max_length=1024)
    save_history: bool = Field(default=True, description="Store analysis in history")


class UrlAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    save_history: bool = Field(default=True)


class UrlFetchResponse(BaseModel):
    url: str
    final_url: str
    title: str | None
    author: str | None
    publish_date: str | None
    site_name: str | None
    extractor: str
    text_preview: str
    text_length: int


class AnalysisResponse(BaseModel):
    id: str | None = None
    input_type: str = "text"
    source_url: str | None = None
    title: str | None = None
    prediction: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    explanation: dict | None = None
    linguistic_signals: dict | None = None
    metadata: dict | None = None
    model_name: str | None = None
    inference_ms: float | None = None
    status: str = "completed"
    error: str | None = None
    created_at: str | None = None


class AnalysisListItem(BaseModel):
    id: str
    input_type: str
    title: str | None
    prediction: str | None
    confidence: float | None
    source_url: str | None
    created_at: str
    status: str


class AnalysisListResponse(BaseModel):
    items: list[AnalysisListItem]
    total: int
    page: int
    page_size: int
    pages: int


class DashboardStatsResponse(BaseModel):
    total_analyses: int
    completed_analyses: int
    classification_distribution: dict[str, int]
    avg_confidence: float | None
    daily_trend: list[dict]
    confidence_histogram: list[dict]
    recent_activity: list[dict]
    avg_inference_ms: float | None
    data_source: str
    generated_at: str


class ModelInfoResponse(BaseModel):
    available: bool
    model_name: str
    labels: list[str]
    device: str
    error: str | None = None
    model_path: str | None = None
    hf_id: str | None = None
    locally_finetuned: bool = False
    metrics: dict | None = None
    metrics_source: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model_available: bool
    database: str
    timestamp: str
