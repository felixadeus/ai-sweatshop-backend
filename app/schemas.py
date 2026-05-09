"""
Space Dungeon Sweatshop - Pydantic Schemas
Request/response models for all API endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════
# Agent Schemas
# ═══════════════════════════════════════════════════════════


class AgentBase(BaseModel):
    """Base agent fields shared across schemas."""

    name: str
    role: str


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""

    status: str = "idle"
    efficiency_pct: float = 100.0
    tasks_completed: int = 0
    current_task: Optional[str] = None


class AgentUpdate(BaseModel):
    """Schema for updating an agent's properties."""

    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    efficiency_pct: Optional[float] = None
    current_task: Optional[str] = None


class AgentResponse(AgentBase):
    """Schema for agent data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    efficiency_pct: float
    tasks_completed: int
    current_task: Optional[str] = None
    created_at: datetime


class AgentStatusResponse(BaseModel):
    """Schema for agent status + current task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    current_task: Optional[str] = None
    efficiency_pct: float
    updated_at: Optional[datetime] = None


class AgentCommandRequest(BaseModel):
    """Schema for sending a command to an agent."""

    command: str
    params: dict[str, Any] = Field(default_factory=dict)


class AgentCommandResponse(BaseModel):
    """Schema for command execution response."""

    success: bool
    message: str
    agent_id: int
    command: str
    executed_at: datetime


class EfficiencyReport(BaseModel):
    """Schema for agent efficiency report."""

    agent_id: int
    agent_name: str
    efficiency_pct: float
    tasks_completed: int
    tasks_failed: int
    avg_task_duration_seconds: Optional[float] = None
    report_generated_at: datetime


# ═══════════════════════════════════════════════════════════
# Task Schemas
# ═══════════════════════════════════════════════════════════


class TaskBase(BaseModel):
    """Base task fields shared across schemas."""

    agent_id: str
    type: str  # design / research / order / other
    payload: Optional[dict[str, Any]] = None
    priority: int = Field(default=3, ge=1, le=5)


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    status: str = "pending"


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    status: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class TaskResponse(TaskBase):
    """Schema for task data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    result: Optional[dict[str, Any]] = None
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class TaskFilterParams(BaseModel):
    """Query parameters for filtering tasks."""

    status: Optional[str] = None
    agent: Optional[str] = None
    type: Optional[str] = None


class TaskCancelResponse(BaseModel):
    """Schema for task cancellation response."""

    success: bool
    task_id: int
    message: str


class TaskRetryResponse(BaseModel):
    """Schema for task retry response."""

    success: bool
    task_id: int
    new_task_id: Optional[int] = None
    message: str


# ═══════════════════════════════════════════════════════════
# Design Schemas
# ═══════════════════════════════════════════════════════════


class DesignBase(BaseModel):
    """Base design fields shared across schemas."""

    prompt: str
    product_type: str  # tshirt / mug / poster / candle / supplement


class DesignCreate(DesignBase):
    """Schema for creating a new design."""

    task_id: Optional[int] = None
    image_url: Optional[str] = None


class DesignGenerateRequest(BaseModel):
    """Schema for generating a new design via AI."""

    prompt: str
    product_type: str
    style: Optional[str] = "modern"


class DesignUpdate(BaseModel):
    """Schema for updating a design."""

    status: Optional[str] = None
    image_url: Optional[str] = None
    printify_product_id: Optional[str] = None
    etsy_listing_id: Optional[str] = None


class DesignResponse(DesignBase):
    """Schema for design data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: Optional[int] = None
    image_url: Optional[str] = None
    status: str
    printify_product_id: Optional[str] = None
    etsy_listing_id: Optional[str] = None
    created_at: datetime


class DesignFilterParams(BaseModel):
    """Query parameters for filtering designs."""

    status: Optional[str] = None
    product_type: Optional[str] = None


class DesignApprovalResponse(BaseModel):
    """Schema for design approval/rejection response."""

    success: bool
    design_id: int
    status: str
    message: str


# ═══════════════════════════════════════════════════════════
# Product Schemas
# ═══════════════════════════════════════════════════════════


class ProductBase(BaseModel):
    """Base product fields shared across schemas."""

    title: str
    store: str  # etsy-pod / etsy-candles / supplements
    price: float


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    design_id: Optional[int] = None
    description: Optional[str] = None
    cost: float = 0.0
    printify_product_id: Optional[str] = None
    etsy_listing_id: Optional[str] = None
    supplifull_sku: Optional[str] = None


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    cost: Optional[float] = None


class ProductResponse(ProductBase):
    """Schema for product data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    design_id: Optional[int] = None
    description: Optional[str] = None
    cost: float
    printify_product_id: Optional[str] = None
    etsy_listing_id: Optional[str] = None
    supplifull_sku: Optional[str] = None
    status: str
    sales_count: int
    revenue: float
    created_at: datetime


class ProductFilterParams(BaseModel):
    """Query parameters for filtering products."""

    store: Optional[str] = None
    status: Optional[str] = None


class ProductPublishResponse(BaseModel):
    """Schema for product publish response."""

    success: bool
    product_id: int
    etsy_listing_id: Optional[str] = None
    message: str
    published_at: datetime


# ═══════════════════════════════════════════════════════════
# Sales Schemas
# ═══════════════════════════════════════════════════════════


class SaleBase(BaseModel):
    """Base sale fields shared across schemas."""

    product_id: int
    platform: str  # etsy / supplifull
    amount: float


class SaleCreate(SaleBase):
    """Schema for creating a new sale record."""

    platform_fee: float = 0.0
    net: float = 0.0


class SaleResponse(SaleBase):
    """Schema for sale data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    platform_fee: float
    net: float
    order_date: datetime


class SaleFilterParams(BaseModel):
    """Query parameters for filtering sales."""

    platform: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class RevenueSummary(BaseModel):
    """Schema for revenue summary response."""

    total_revenue: float
    total_sales: int
    total_platform_fees: float
    total_net: float
    by_store: dict[str, dict[str, float]]
    by_period: dict[str, float]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class OrderSyncResponse(BaseModel):
    """Schema for order sync response."""

    success: bool
    orders_synced: int
    new_orders: int
    message: str
    synced_at: datetime


# ═══════════════════════════════════════════════════════════
# Research Schemas
# ═══════════════════════════════════════════════════════════


class ResearchFindingBase(BaseModel):
    """Base research finding fields shared across schemas."""

    competitor_store: str
    product_category: str
    trend_score: float = 0.0
    estimated_sales: int = 0


class ResearchFindingCreate(ResearchFindingBase):
    """Schema for creating a research finding."""

    concept_extracted: Optional[str] = None


class ResearchFindingResponse(ResearchFindingBase):
    """Schema for research finding data in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_extracted: Optional[str] = None
    sent_to_forge: bool
    forge_design_id: Optional[int] = None
    created_at: datetime


class ScrapeRequest(BaseModel):
    """Schema for requesting a competitor store scrape."""

    store_url: str


class ScrapeResponse(BaseModel):
    """Schema for scrape operation response."""

    success: bool
    store_url: str
    products_found: int
    message: str
    scraped_at: datetime


class ConceptToForgeRequest(BaseModel):
    """Schema for sending a concept to Forge for design."""

    concept: str
    product_type: str = "tshirt"
    priority: int = Field(default=2, ge=1, le=5)


class ConceptToForgeResponse(BaseModel):
    """Schema for concept-to-forge response."""

    success: bool
    concept: str
    task_id: int
    message: str
    sent_at: datetime


# ═══════════════════════════════════════════════════════════
# Store Schemas
# ═══════════════════════════════════════════════════════════


class StoreMetrics(BaseModel):
    """Schema for store metrics in responses."""

    store: str
    total_products: int
    active_products: int
    total_revenue: float
    total_sales: int
    avg_order_value: float
    health_score: float


class StoreResponse(BaseModel):
    """Schema for store details response."""

    id: str
    name: str
    platform: str
    status: str
    metrics: StoreMetrics
    created_at: Optional[datetime] = None


class StoreHealthMetrics(BaseModel):
    """Schema for store health check response."""

    store: str
    health_score: float
    status: str  # healthy / warning / critical
    last_sync: Optional[datetime] = None
    issues: list[str]
    recommendations: list[str]


# ═══════════════════════════════════════════════════════════
# WebSocket Message Schema
# ═══════════════════════════════════════════════════════════


class WebSocketMessage(BaseModel):
    """Standard WebSocket message format."""

    type: str
    agent_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str  # ISO format


# ═══════════════════════════════════════════════════════════
# Health Check Schema
# ═══════════════════════════════════════════════════════════


class HealthCheckResponse(BaseModel):
    """Schema for health check endpoint."""

    status: str
    version: str
    uptime_seconds: float
    agents_online: int
    tasks_pending: int
    timestamp: datetime


# ═══════════════════════════════════════════════════════════
# System Schemas
# ═══════════════════════════════════════════════════════════


class SystemStats(BaseModel):
    """Schema for overall system statistics."""

    total_agents: int
    agents_working: int
    agents_idle: int
    agents_alert: int
    total_tasks: int
    tasks_pending: int
    tasks_running: int
    tasks_completed: int
    tasks_failed: int
    total_products: int
    products_active: int
    total_sales: int
    total_revenue: float
    total_designs: int
    designs_draft: int
    designs_approved: int
    research_findings: int
    timestamp: datetime
