from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import re
import json

from database import get_db
from auth import require_auth
from models import TopicCreate, TopicUpdate, TopicResponse

router = APIRouter(prefix="/api/topics", tags=["Topics"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.get("", response_model=List[TopicResponse])
def get_topics(
    domain_id: Optional[int] = None,
    status: Optional[str] = None,
    importance: Optional[str] = None
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                t.*,
                d.name AS domain_name,
                d.color AS domain_color,
                COUNT(r.id) AS resource_count
            FROM topics t
            JOIN domains d ON t.domain_id = d.id
            LEFT JOIN resources r ON t.id = r.topic_id
        """
        filters = []
        params = []
        if domain_id:
            filters.append("t.domain_id = ?")
            params.append(domain_id)
        if status:
            filters.append("t.status = ?")
            params.append(status)
        if importance:
            filters.append("t.importance = ?")
            params.append(importance)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " GROUP BY t.id ORDER BY t.order_index ASC, t.id ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/{topic_id}")
def get_topic_detail(topic_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.*,
                d.name AS domain_name,
                d.color AS domain_color
            FROM topics t
            JOIN domains d ON t.domain_id = d.id
            WHERE t.id = ?
        """, (topic_id,))
        topic = cursor.fetchone()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Fetch resources
        cursor.execute("""
            SELECT * FROM resources
            WHERE topic_id = ?
            ORDER BY is_favorite DESC, order_index ASC, id ASC
        """, (topic_id,))
        resource_rows = cursor.fetchall()
        resources = []
        for r in resource_rows:
            r_dict = dict(r)
            try:
                r_dict["tags"] = json.loads(r_dict["tags"]) if r_dict["tags"] else []
            except Exception:
                r_dict["tags"] = [t.strip() for t in r_dict["tags"].split(",") if t.strip()] if r_dict["tags"] else []
            r_dict["is_favorite"] = bool(r_dict["is_favorite"])
            resources.append(r_dict)

        result = dict(topic)
        result["resources"] = resources
        return result


@router.post("", response_model=TopicResponse)
def create_topic(data: TopicCreate, user=Depends(require_auth)):
    slug = data.slug or slugify(data.title)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM domains WHERE id = ?", (data.domain_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Invalid domain_id")

        cursor.execute("""
            INSERT INTO topics (domain_id, parent_id, title, slug, summary, status, importance, drive_folder_url, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.domain_id,
            data.parent_id,
            data.title,
            slug,
            data.summary or "",
            data.status or "in_progress",
            data.importance or "high",
            data.drive_folder_url or "",
            data.order_index or 0,
        ))
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("""
            SELECT 
                t.*,
                d.name AS domain_name,
                d.color AS domain_color,
                0 AS resource_count
            FROM topics t
            JOIN domains d ON t.domain_id = d.id
            WHERE t.id = ?
        """, (new_id,))
        return dict(cursor.fetchone())


@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(topic_id: int, data: TopicUpdate, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Topic not found")

        updates = []
        params = []
        for field, val in data.dict(exclude_unset=True).items():
            updates.append(f"{field} = ?")
            params.append(val)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(topic_id)
            cursor.execute(f"UPDATE topics SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        cursor.execute("""
            SELECT 
                t.*,
                d.name AS domain_name,
                d.color AS domain_color,
                COUNT(r.id) AS resource_count
            FROM topics t
            JOIN domains d ON t.domain_id = d.id
            LEFT JOIN resources r ON t.id = r.topic_id
            WHERE t.id = ?
            GROUP BY t.id
        """, (topic_id,))
        return dict(cursor.fetchone())


@router.delete("/{topic_id}")
def delete_topic(topic_id: int, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM topics WHERE id = ?", (topic_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found")
        cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        conn.commit()
    return {"status": "deleted", "id": topic_id}
