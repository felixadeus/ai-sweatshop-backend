"""
Space Dungeon Sweatshop - SQLAlchemy Models
All database models for the AI agent command center.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Agent(Base):
    """
    AI Agent model — represents a worker in the sweatshop.
    Each agent has a role, status, efficiency metrics, and task tracking.
    """

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="idle"
    )  # working / idle / alert
    efficiency_pct: Mapped[float] = mapped_column(Float, default=100.0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    current_task: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Task(Base):
    """
    Task model — represents a unit of work assigned to an agent.
    Tracks the full lifecycle from pending to completion or failure.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # design / research / order / other
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending / running / completed / failed
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1 (highest) - 5 (lowest)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Design(Base):
    """
    Design model — represents an AI-generated design.
    Linked to a task, with product type and publishing status.
    """

    __tablename__ = "designs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    product_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # tshirt / mug / poster / candle / supplement
    status: Mapped[str] = mapped_column(
        String, default="draft"
    )  # draft / approved / uploaded
    printify_product_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    etsy_listing_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Product(Base):
    """
    Product model — represents a sellable product.
    Derived from a design, listed on a store platform.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    design_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    store: Mapped[str] = mapped_column(
        String, nullable=False
    )  # etsy-pod / etsy-candles / supplements
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    printify_product_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    etsy_listing_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    supplifull_sku: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, default="draft"
    )  # draft / active / paused
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Sale(Base):
    """
    Sale model — represents a completed order/transaction.
    Tracks revenue, platform fees, and net earnings.
    """

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    platform: Mapped[str] = mapped_column(
        String, nullable=False
    )  # etsy / supplifull
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)
    net: Mapped[float] = mapped_column(Float, nullable=False)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ResearchFinding(Base):
    """
    Research Finding model — represents scraped competitor data.
    Used by Nova to identify trends and send concepts to Forge.
    """

    __tablename__ = "research_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_store: Mapped[str] = mapped_column(String, nullable=False)
    product_category: Mapped[str] = mapped_column(String, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_sales: Mapped[int] = mapped_column(Integer, default=0)
    concept_extracted: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sent_to_forge: Mapped[bool] = mapped_column(Boolean, default=False)
    forge_design_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
