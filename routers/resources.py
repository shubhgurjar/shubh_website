from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Tuple
import json
import re
from urllib.parse import urlparse

from database import get_db
from auth import require_auth
from models import ResourceCreate, ResourceUpdate, ResourceResponse, BulkResourceCreate

router = APIRouter(prefix="/api/resources", tags=["Resources"])


def format_resource_row(row) -> dict:
    d = dict(row)
    try:
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    except Exception:
        d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()] if d["tags"] else []
    d["is_favorite"] = bool(d["is_favorite"])
    return d


@router.get("", response_model=List[ResourceResponse])
def get_resources(
    topic_id: Optional[int] = None,
    type: Optional[str] = None,
    favorite_only: Optional[bool] = False,
    tag: Optional[str] = None,
    q: Optional[str] = None
):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                r.*,
                t.title AS topic_title,
                d.name AS domain_name,
                d.color AS domain_color
            FROM resources r
            JOIN topics t ON r.topic_id = t.id
            JOIN domains d ON t.domain_id = d.id
        """
        filters = []
        params = []

        if topic_id:
            filters.append("r.topic_id = ?")
            params.append(topic_id)
        if type:
            filters.append("r.type = ?")
            params.append(type)
        if favorite_only:
            filters.append("r.is_favorite = 1")
        if q:
            filters.append("(r.title LIKE ? OR r.notes LIKE ? OR r.tags LIKE ?)")
            term = f"%{q}%"
            params.extend([term, term, term])
        if tag:
            filters.append("r.tags LIKE ?")
            params.append(f"%{tag}%")

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY r.is_favorite DESC, r.order_index ASC, r.id DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [format_resource_row(row) for row in rows]


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                r.*,
                t.title AS topic_title,
                d.name AS domain_name,
                d.color AS domain_color
            FROM resources r
            JOIN topics t ON r.topic_id = t.id
            JOIN domains d ON t.domain_id = d.id
            WHERE r.id = ?
        """, (resource_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resource not found")
        return format_resource_row(row)


@router.post("", response_model=ResourceResponse)
def create_resource(data: ResourceCreate, user=Depends(require_auth)):
    tags_json = json.dumps(data.tags or [])
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM topics WHERE id = ?", (data.topic_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Invalid topic_id")

        cursor.execute("""
            INSERT INTO resources (topic_id, type, title, url, file_path, notes, tags, is_favorite, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.topic_id,
            data.type,
            data.title,
            data.url or "",
            data.file_path or "",
            data.notes or "",
            tags_json,
            1 if data.is_favorite else 0,
            data.order_index or 0,
        ))
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("""
            SELECT 
                r.*,
                t.title AS topic_title,
                d.name AS domain_name,
                d.color AS domain_color
            FROM resources r
            JOIN topics t ON r.topic_id = t.id
            JOIN domains d ON t.domain_id = d.id
            WHERE r.id = ?
        """, (new_id,))
        return format_resource_row(cursor.fetchone())


def parse_link_line(line: str, default_type: str) -> Tuple[str, str, str]:
    """Returns (cleaned_url, title, detected_type)"""
    line = line.strip()
    if not line:
        return "", "", default_type

    url = line
    title = ""

    # Check for separator '|' or ' - '
    if "|" in line:
        parts = line.split("|", 1)
        if parts[0].strip().startswith("http"):
            url = parts[0].strip()
            title = parts[1].strip()
        else:
            title = parts[0].strip()
            url = parts[1].strip()
    elif " - " in line and line.strip().startswith("http"):
        parts = line.split(" - ", 1)
        url = parts[0].strip()
        title = parts[1].strip()

    # Detect resource type
    detected_type = default_type
    low = url.lower()
    if "youtube.com" in low or "youtu.be" in low:
        detected_type = "youtube"
    elif low.endswith(".pdf") or "/pdf/" in low or "arxiv.org/abs/" in low:
        detected_type = "pdf"
    elif "drive.google.com" in low:
        detected_type = "drive_folder" if "folder" in low else "drive_file"
    elif "github.com" in low:
        detected_type = "github"

    # If title wasn't explicitly given:
    if not title:
        if detected_type == "youtube":
            m = re.search(r'(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})', url)
            if m:
                video_id = m.group(1)
                title = f"YouTube Video ({video_id})"
            else:
                title = "YouTube Video"
        elif "drive.google.com" in low:
            title = "Google Drive Folder" if "folder" in low else "Google Drive File"
        elif "github.com" in low:
            m = re.search(r'github\.com\/([^\/\?#]+\/[^\/\?#]+)', url)
            title = f"GitHub: {m.group(1)}" if m else "GitHub Repository"
        else:
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if path:
                last_segment = path.split("/")[-1]
                last_segment = re.sub(r'\.(pdf|html|htm|md)$', '', last_segment, flags=re.IGNORECASE)
                last_segment = last_segment.replace("-", " ").replace("_", " ").title()
                title = last_segment if len(last_segment) > 1 else (parsed.netloc or "Resource")
            else:
                title = parsed.netloc or "Resource"

    return url, title, detected_type


@router.post("/bulk")
def create_resources_bulk(data: BulkResourceCreate, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify domain exists
        cursor.execute("SELECT id, name FROM domains WHERE id = ?", (data.domain_id,))
        domain = cursor.fetchone()
        if not domain:
            raise HTTPException(status_code=400, detail="Invalid domain_id")

        # Determine topic_id
        topic_id = data.topic_id
        if topic_id:
            cursor.execute("SELECT id FROM topics WHERE id = ? AND domain_id = ?", (topic_id, data.domain_id))
            if not cursor.fetchone():
                topic_id = None

        if not topic_id:
            # Check for an existing topic or create default 'Curated Resources' topic
            cursor.execute("SELECT id FROM topics WHERE domain_id = ? ORDER BY order_index ASC, id ASC LIMIT 1", (data.domain_id,))
            first_topic = cursor.fetchone()
            if first_topic:
                topic_id = first_topic["id"]
            else:
                # Auto-create topic
                cursor.execute("""
                    INSERT INTO topics (domain_id, title, slug, summary, status, importance, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data.domain_id, f"{domain['name']} Resources", "curated-resources", "Curated learning links and videos.", "in_progress", "core", 0))
                topic_id = cursor.lastrowid

        # Collect lines
        raw_lines = []
        if data.links_text:
            raw_lines.extend(data.links_text.splitlines())
        if data.links:
            raw_lines.extend(data.links)

        created_resources = []
        for line in raw_lines:
            url, title, res_type = parse_link_line(line, data.type)
            if not url:
                continue

            cursor.execute("""
                INSERT INTO resources (topic_id, type, title, url, file_path, notes, tags, is_favorite, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                topic_id,
                res_type,
                title,
                url,
                "",
                "",
                "[]",
                0,
                0,
            ))
            new_id = cursor.lastrowid
            created_resources.append({
                "id": new_id,
                "topic_id": topic_id,
                "type": res_type,
                "title": title,
                "url": url,
            })

        conn.commit()

        return {
            "status": "success",
            "count": len(created_resources),
            "topic_id": topic_id,
            "domain_id": data.domain_id,
            "resources": created_resources,
        }


@router.put("/{resource_id}", response_model=ResourceResponse)
def update_resource(resource_id: int, data: ResourceUpdate, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Resource not found")

        updates = []
        params = []
        update_dict = data.dict(exclude_unset=True)

        if "tags" in update_dict:
            update_dict["tags"] = json.dumps(update_dict["tags"] or [])
        if "is_favorite" in update_dict:
            update_dict["is_favorite"] = 1 if update_dict["is_favorite"] else 0

        for field, val in update_dict.items():
            updates.append(f"{field} = ?")
            params.append(val)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(resource_id)
            cursor.execute(f"UPDATE resources SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        cursor.execute("""
            SELECT 
                r.*,
                t.title AS topic_title,
                d.name AS domain_name,
                d.color AS domain_color
            FROM resources r
            JOIN topics t ON r.topic_id = t.id
            JOIN domains d ON t.domain_id = d.id
            WHERE r.id = ?
        """, (resource_id,))
        return format_resource_row(cursor.fetchone())


@router.delete("/{resource_id}")
def delete_resource(resource_id: int, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM resources WHERE id = ?", (resource_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Resource not found")
        cursor.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        conn.commit()
    return {"status": "deleted", "id": resource_id}


@router.post("/{resource_id}/toggle-favorite")
def toggle_favorite(resource_id: int, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_favorite FROM resources WHERE id = ?", (resource_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resource not found")
        
        new_fav = 0 if row["is_favorite"] else 1
        cursor.execute("UPDATE resources SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_fav, resource_id))
        conn.commit()
        return {"id": resource_id, "is_favorite": bool(new_fav)}
