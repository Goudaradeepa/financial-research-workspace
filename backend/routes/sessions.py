import uuid
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status

from database import get_db_connection, STORAGE_DIR
from models import ResearchSessionCreate, ResearchSessionUpdate, ResearchSessionResponse

router = APIRouter(prefix="/api/sessions", tags=["Research Sessions"])

@router.post("", response_model=ResearchSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: ResearchSessionCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    tags_json = json.dumps(payload.tags or [])

    cursor.execute("""
    INSERT INTO research_sessions (id, name, description, created_at, updated_at, ticker, tags)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        payload.name.strip(),
        payload.description.strip() if payload.description else None,
        now,
        now,
        payload.ticker.strip().upper() if payload.ticker else None,
        tags_json
    ))
    conn.commit()

    session_storage = STORAGE_DIR / "sessions" / session_id
    session_storage.mkdir(parents=True, exist_ok=True)

    cursor.execute("SELECT * FROM research_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    return ResearchSessionResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ticker=row["ticker"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        document_count=0,
        total_size_bytes=0
    )

@router.get("", response_model=List[ResearchSessionResponse])
def list_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        s.id, s.name, s.description, s.created_at, s.updated_at, s.ticker, s.tags,
        COUNT(d.id) as doc_count,
        COALESCE(SUM(d.file_size_bytes), 0) as total_size
    FROM research_sessions s
    LEFT JOIN financial_documents d ON s.id = d.session_id
    GROUP BY s.id
    ORDER BY s.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for row in rows:
        sessions.append(ResearchSessionResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            ticker=row["ticker"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            document_count=row["doc_count"],
            total_size_bytes=row["total_size"]
        ))
    return sessions

@router.get("/{session_id}", response_model=ResearchSessionResponse)
def get_session(session_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        s.id, s.name, s.description, s.created_at, s.updated_at, s.ticker, s.tags,
        COUNT(d.id) as doc_count,
        COALESCE(SUM(d.file_size_bytes), 0) as total_size
    FROM research_sessions s
    LEFT JOIN financial_documents d ON s.id = d.session_id
    WHERE s.id = ?
    GROUP BY s.id
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Research session not found")

    return ResearchSessionResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ticker=row["ticker"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        document_count=row["doc_count"],
        total_size_bytes=row["total_size"]
    )

@router.put("/{session_id}", response_model=ResearchSessionResponse)
def update_session(session_id: str, payload: ResearchSessionUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM research_sessions WHERE id = ?", (session_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")

    new_name = payload.name.strip() if payload.name is not None else existing["name"]
    new_desc = payload.description.strip() if payload.description is not None else existing["description"]
    new_ticker = payload.ticker.strip().upper() if payload.ticker is not None else existing["ticker"]
    new_tags = json.dumps(payload.tags) if payload.tags is not None else existing["tags"]
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    UPDATE research_sessions
    SET name = ?, description = ?, ticker = ?, tags = ?, updated_at = ?
    WHERE id = ?
    """, (new_name, new_desc, new_ticker, new_tags, now, session_id))
    conn.commit()

    cursor.execute("""
    SELECT 
        s.id, s.name, s.description, s.created_at, s.updated_at, s.ticker, s.tags,
        COUNT(d.id) as doc_count,
        COALESCE(SUM(d.file_size_bytes), 0) as total_size
    FROM research_sessions s
    LEFT JOIN financial_documents d ON s.id = d.session_id
    WHERE s.id = ?
    GROUP BY s.id
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()

    return ResearchSessionResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        ticker=row["ticker"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        document_count=row["doc_count"],
        total_size_bytes=row["total_size"]
    )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM research_sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Research session not found")

    cursor.execute("DELETE FROM research_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

    session_storage = STORAGE_DIR / "sessions" / session_id
    if session_storage.exists():
        shutil.rmtree(session_storage, ignore_errors=True)

    return None
