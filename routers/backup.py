from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import JSONResponse
from datetime import datetime
import json

from database import get_db
from auth import require_auth

router = APIRouter(prefix="/api", tags=["Backup & Search"])


@router.get("/backup/export")
def export_backup(user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Fetch all domains
        cursor.execute("SELECT * FROM domains ORDER BY order_index ASC, id ASC")
        domain_rows = cursor.fetchall()
        
        result_domains = []
        for d in domain_rows:
            d_dict = dict(d)
            domain_id = d_dict["id"]
            
            # Fetch topics for domain
            cursor.execute("SELECT * FROM topics WHERE domain_id = ? ORDER BY order_index ASC, id ASC", (domain_id,))
            topic_rows = cursor.fetchall()
            
            topics_list = []
            for t in topic_rows:
                t_dict = dict(t)
                topic_id = t_dict["id"]
                
                # Fetch resources for topic
                cursor.execute("SELECT * FROM resources WHERE topic_id = ? ORDER BY order_index ASC, id ASC", (topic_id,))
                res_rows = cursor.fetchall()
                resources_list = []
                for r in res_rows:
                    r_dict = dict(r)
                    try:
                        r_dict["tags"] = json.loads(r_dict["tags"]) if r_dict["tags"] else []
                    except Exception:
                        r_dict["tags"] = [tag.strip() for tag in r_dict["tags"].split(",") if tag.strip()] if r_dict["tags"] else []
                    r_dict["is_favorite"] = bool(r_dict["is_favorite"])
                    resources_list.append(r_dict)
                
                t_dict["resources"] = resources_list
                topics_list.append(t_dict)
                
            d_dict["topics"] = topics_list
            result_domains.append(d_dict)

    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "domains": result_domains,
    }

    filename = f"career_hub_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return JSONResponse(content=export_data, headers=headers)


@router.post("/backup/import")
def import_backup(payload: dict = Body(...), user=Depends(require_auth)):
    mode = payload.get("mode", "replace")  # "replace" or "merge"
    domains = payload.get("domains", [])
    
    if not isinstance(domains, list):
        raise HTTPException(status_code=400, detail="Invalid backup format: 'domains' must be a list")

    with get_db() as conn:
        cursor = conn.cursor()
        
        if mode == "replace":
            # Clear existing data (cascades automatically)
            cursor.execute("DELETE FROM domains")

        for d_idx, d in enumerate(domains):
            cursor.execute("""
                INSERT INTO domains (name, slug, description, icon, color, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                d.get("name"),
                d.get("slug") or f"domain-{d_idx}",
                d.get("description", ""),
                d.get("icon", "folder"),
                d.get("color", "indigo"),
                d.get("order_index", d_idx),
            ))
            domain_id = cursor.lastrowid

            for t_idx, t in enumerate(d.get("topics", [])):
                cursor.execute("""
                    INSERT INTO topics (domain_id, title, slug, summary, status, importance, drive_folder_url, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain_id,
                    t.get("title"),
                    t.get("slug") or f"topic-{t_idx}",
                    t.get("summary", ""),
                    t.get("status", "in_progress"),
                    t.get("importance", "high"),
                    t.get("drive_folder_url", ""),
                    t.get("order_index", t_idx),
                ))
                topic_id = cursor.lastrowid

                for r_idx, r in enumerate(t.get("resources", [])):
                    tags = json.dumps(r.get("tags", [])) if isinstance(r.get("tags"), list) else (r.get("tags") or "[]")
                    cursor.execute("""
                        INSERT INTO resources (topic_id, type, title, url, file_path, notes, tags, is_favorite, order_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        topic_id,
                        r.get("type", "note"),
                        r.get("title"),
                        r.get("url", ""),
                        r.get("file_path", ""),
                        r.get("notes", ""),
                        tags,
                        1 if r.get("is_favorite") else 0,
                        r.get("order_index", r_idx),
                    ))

        conn.commit()

    return {"status": "imported", "domains_count": len(domains)}


@router.get("/search")
def global_search(q: str):
    term = q.strip()
    if not term:
        return {"domains": [], "topics": [], "resources": []}

    pattern = f"%{term}%"
    with get_db() as conn:
        cursor = conn.cursor()

        # Search domains
        cursor.execute("SELECT id, name, slug, description, icon, color FROM domains WHERE name LIKE ? OR description LIKE ?", (pattern, pattern))
        domains = [dict(r) for r in cursor.fetchall()]

        # Search topics
        cursor.execute("""
            SELECT t.id, t.domain_id, t.title, t.slug, t.summary, t.status, t.importance, d.name as domain_name, d.color as domain_color
            FROM topics t
            JOIN domains d ON t.domain_id = d.id
            WHERE t.title LIKE ? OR t.summary LIKE ?
        """, (pattern, pattern))
        topics = [dict(r) for r in cursor.fetchall()]

        # Search resources
        cursor.execute("""
            SELECT r.*, t.title as topic_title, d.name as domain_name, d.color as domain_color
            FROM resources r
            JOIN topics t ON r.topic_id = t.id
            JOIN domains d ON t.domain_id = d.id
            WHERE r.title LIKE ? OR r.notes LIKE ? OR r.tags LIKE ? OR r.url LIKE ?
        """, (pattern, pattern, pattern, pattern))
        resource_rows = cursor.fetchall()
        resources = []
        for r in resource_rows:
            r_dict = dict(r)
            try:
                r_dict["tags"] = json.loads(r_dict["tags"]) if r_dict["tags"] else []
            except Exception:
                r_dict["tags"] = [tag.strip() for tag in r_dict["tags"].split(",") if tag.strip()] if r_dict["tags"] else []
            r_dict["is_favorite"] = bool(r_dict["is_favorite"])
            resources.append(r_dict)

        return {
            "query": term,
            "domains": domains,
            "topics": topics,
            "resources": resources,
            "total_matches": len(domains) + len(topics) + len(resources),
        }
