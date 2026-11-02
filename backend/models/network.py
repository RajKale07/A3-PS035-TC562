"""
NEXUS — Adaptive Network Resilience Intelligence
SQLAlchemy ORM models for network topology persistence.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class NetworkTopology(Base):
    """Stores a named network topology snapshot."""

    __tablename__ = "network_topologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    nodes: Mapped[list["NetworkNode"]] = relationship(
        "NetworkNode", back_populates="topology", cascade="all, delete-orphan"
    )
    links: Mapped[list["NetworkLink"]] = relationship(
        "NetworkLink", back_populates="topology", cascade="all, delete-orphan"
    )
    simulations: Mapped[list["SimulationResult"]] = relationship(
        "SimulationResult", back_populates="topology", cascade="all, delete-orphan"
    )


class NetworkNode(Base):
    """A node (router/switch/host) in a network topology."""

    __tablename__ = "network_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topology_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_topologies.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="router"
    )  # router | switch | host | cloud
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # layout hint
    y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    topology: Mapped["NetworkTopology"] = relationship(
        "NetworkTopology", back_populates="nodes"
    )


class NetworkLink(Base):
    """A directed or undirected link between two nodes."""

    __tablename__ = "network_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topology_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_topologies.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    bandwidth_mbps: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    loss_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    topology: Mapped["NetworkTopology"] = relationship(
        "NetworkTopology", back_populates="links"
    )


class SimulationResult(Base):
    """Stores results from a NEXUS resilience simulation run."""

    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topology_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("network_topologies.id"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(128), nullable=False)
    resilience_score: Mapped[float] = mapped_column(Float, nullable=False)
    connectivity_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    avg_path_length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    failed_nodes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    optimizer_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    topology: Mapped["NetworkTopology"] = relationship(
        "NetworkTopology", back_populates="simulations"
    )

