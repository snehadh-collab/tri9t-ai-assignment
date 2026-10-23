import os
import json
import uuid
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, DocumentVersion, DocumentNode, Selection, SelectionItem
from app.parser import parse_pdf_to_nodes

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

JSON_STORE_PATH = "./generations_store.json"
if not os.path.exists(JSON_STORE_PATH):
    with open(JSON_STORE_PATH, "w") as f:
        json.dump([], f)

app = FastAPI(title="Tri9T AI Backend - CardioTrack CT-200")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class IngestRequest(BaseModel):
    file_path: str
    version_label: str

class SelectionCreate(BaseModel):
    name: str
    version_id: int
    node_ids: List[str]

class GenerationRequest(BaseModel):
    selection_id: str

@app.post("/api/v1/documents/ingest")
def ingest_document(req: IngestRequest, db: Session = Depends(get_db)):
    doc_ver = DocumentVersion(version_label=req.version_label)
    db.add(doc_ver)
    db.commit()
    db.refresh(doc_ver)

    parsed_nodes = parse_pdf_to_nodes(req.file_path, doc_ver.id)
    for n in parsed_nodes:
        db_node = DocumentNode(**n)
        db.add(db_node)
    db.commit()

    return {"message": "Document ingested successfully", "version_id": doc_ver.id, "node_count": len(parsed_nodes)}

@app.get("/api/v1/nodes/tree")
def get_tree(version_id: Optional[int] = None, db: Session = Depends(get_db)):
    if not version_id:
        latest = db.query(DocumentVersion).order_by(DocumentVersion.id.desc()).first()
        version_id = latest.id if latest else 1
    nodes = db.query(DocumentNode).filter(DocumentNode.version_id == version_id).all()
    return nodes

@app.get("/api/v1/nodes/{node_id}")
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = db.query(DocumentNode).filter(DocumentNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    children = db.query(DocumentNode).filter(DocumentNode.parent_id == node_id).all()
    return {"node": node, "children": children}

@app.get("/api/v1/nodes/{node_id}/diff")
def node_diff(node_id: str, target_version: int, db: Session = Depends(get_db)):
    source_node = db.query(DocumentNode).filter(DocumentNode.id == node_id).first()
    target_node = db.query(DocumentNode).filter(
        DocumentNode.version_id == target_version,
        DocumentNode.node_path == source_node.node_path
    ).first()
    
    if not target_node:
        return {"status": "REMOVED_IN_TARGET_VERSION"}
        
    changed = source_node.content_hash != target_node.content_hash
    return {
        "changed": changed,
        "source_hash": source_node.content_hash,
        "target_hash": target_node.content_hash,
        "source_text": source_node.body_text,
        "target_text": target_node.body_text
    }

@app.post("/api/v1/selections")
def create_selection(req: SelectionCreate, db: Session = Depends(get_db)):
    sel = Selection(id=f"sel_{uuid.uuid4().hex[:8]}", name=req.name, version_id=req.version_id)
    db.add(sel)
    db.commit()

    for nid in req.node_ids:
        node = db.query(DocumentNode).filter(DocumentNode.id == nid).first()
        if node:
            item = SelectionItem(selection_id=sel.id, node_id=nid, pinned_content_hash=node.content_hash)
            db.add(item)
    db.commit()
    return {"selection_id": sel.id, "status": "CREATED_AND_PINNED"}

@app.post("/api/v1/generations/generate")
def generate_test_cases(req: GenerationRequest, db: Session = Depends(get_db)):
    sel = db.query(Selection).filter(Selection.id == req.selection_id).first()
    if not sel:
        raise HTTPException(status_code=404, detail="Selection not found")

    items = db.query(SelectionItem).filter(SelectionItem.selection_id == req.selection_id).all()
    context_text = ""
    for item in items:
        node = db.query(DocumentNode).filter(DocumentNode.id == item.node_id).first()
        if node:
            context_text += f"\nSection {node.heading}:\n{node.body_text}\n"

    generated_output = {
        "generation_id": f"gen_{uuid.uuid4().hex[:8]}",
        "selection_id": sel.id,
        "target_version_id": sel.version_id,
        "test_cases": [
            {
                "test_case_id": "TC-CT200-01",
                "title": "Cuff Overpressure Emergency Deflate",
                "steps": ["Simulate cuff pressure > 299 mmHg"],
                "expected": "Emergency deflation triggers within 2 seconds"
            },
            {
                "test_case_id": "TC-CT200-02",
                "title": "Low Battery Warning Threshold",
                "steps": ["Drain AA battery below threshold"],
                "expected": "Displays low-battery icon on screen"
            }
        ]
    }

    with open(JSON_STORE_PATH, "r+") as f:
        data = json.load(f)
        data.append(generated_output)
        f.seek(0)
        json.dump(data, f, indent=2)

    return generated_output

@app.get("/api/v1/retrieval/{selection_id}")
def retrieve_and_check_staleness(selection_id: str, compare_version_id: int, db: Session = Depends(get_db)):
    sel_items = db.query(SelectionItem).filter(SelectionItem.selection_id == selection_id).all()
    
    staleness_report = []
    is_overall_stale = False

    for item in sel_items:
        orig_node = db.query(DocumentNode).filter(DocumentNode.id == item.node_id).first()
        target_node = db.query(DocumentNode).filter(
            DocumentNode.version_id == compare_version_id,
            DocumentNode.node_path == orig_node.node_path
        ).first()

        if not target_node:
            status = "STALE_NODE_DELETED"
            is_overall_stale = True
        elif target_node.content_hash != item.pinned_content_hash:
            status = "STALE_TEXT_CHANGED"
            is_overall_stale = True
        else:
            status = "STABLE"

        staleness_report.append({
            "node_path": orig_node.node_path,
            "heading": orig_node.heading,
            "status": status,
            "original_hash": item.pinned_content_hash,
            "compare_version_hash": target_node.content_hash if target_node else None
        })

    with open(JSON_STORE_PATH, "r") as f:
        all_generations = json.load(f)
        
    gens = [g for g in all_generations if g["selection_id"] == selection_id]

    return {
        "selection_id": selection_id,
        "is_overall_stale": is_overall_stale,
        "staleness_details": staleness_report,
        "generations": gens
    }
    