import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_label: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    nodes: Mapped[List["DocumentNode"]] = relationship("DocumentNode", back_populates="doc_version")

class DocumentNode(Base):
    __tablename__ = "document_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("document_nodes.id"), nullable=True)
    
    heading: Mapped[str] = mapped_column(String(512), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, default="")
    node_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    doc_version: Mapped["DocumentVersion"] = relationship("DocumentVersion", back_populates="nodes")

class Selection(Base):
    __tablename__ = "selections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[List["SelectionItem"]] = relationship("SelectionItem", back_populates="selection")

class SelectionItem(Base):
    __tablename__ = "selection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    selection_id: Mapped[str] = mapped_column(ForeignKey("selections.id"), nullable=False)
    node_id: Mapped[str] = mapped_column(ForeignKey("document_nodes.id"), nullable=False)
    pinned_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    selection: Mapped["Selection"] = relationship("Selection", back_populates="items")
    