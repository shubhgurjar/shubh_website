from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import re

from database import get_db
from auth import require_auth
from models import DomainCreate, DomainUpdate, DomainResponse

router = APIRouter(prefix="/api/domains", tags=["Domains"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.get("", response_model=List[DomainResponse])
def get_domains():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.id, d.name, d.slug, d.description, d.icon, d.color, d.order_index, d.created_at, d.updated_at,
                COUNT(DISTINCT t.id) AS topic_count,
                COUNT(DISTINCT r.id) AS resource_count
            FROM domains d
            LEFT JOIN topics t ON d.id = t.domain_id
            LEFT JOIN resources r ON t.id = r.topic_id
            GROUP BY d.id
            ORDER BY d.order_index ASC, d.id ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@router.get("/{domain_id}")
def get_domain_detail(domain_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE id = ?", (domain_id,))
        domain = cursor.fetchone()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")

        # Fetch topics for this domain
        cursor.execute("""
            SELECT 
                t.*,
                COUNT(r.id) as resource_count
            FROM topics t
            LEFT JOIN resources r ON t.id = r.topic_id
            WHERE t.domain_id = ?
            GROUP BY t.id
            ORDER BY t.order_index ASC, t.id ASC
        """, (domain_id,))
        topics = [dict(t) for t in cursor.fetchall()]

        result = dict(domain)
        result["topics"] = topics
        return result


@router.post("", response_model=DomainResponse)
def create_domain(data: DomainCreate, user=Depends(require_auth)):
    slug = data.slug or slugify(data.name)
    with get_db() as conn:
        cursor = conn.cursor()
        # Ensure unique slug
        cursor.execute("SELECT id FROM domains WHERE slug = ?", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{cursor.lastrowid or 1}"

        cursor.execute("""
            INSERT INTO domains (name, slug, description, icon, color, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data.name, slug, data.description, data.icon or 'folder', data.color or 'indigo', data.order_index or 0))
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM domains WHERE id = ?", (new_id,))
        new_domain = dict(cursor.fetchone())
        new_domain["topic_count"] = 0
        new_domain["resource_count"] = 0
        return new_domain


@router.put("/{domain_id}", response_model=DomainResponse)
def update_domain(domain_id: int, data: DomainUpdate, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM domains WHERE id = ?", (domain_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Domain not found")

        updates = []
        params = []
        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.slug is not None:
            updates.append("slug = ?")
            params.append(data.slug)
        if data.description is not None:
            updates.append("description = ?")
            params.append(data.description)
        if data.icon is not None:
            updates.append("icon = ?")
            params.append(data.icon)
        if data.color is not None:
            updates.append("color = ?")
            params.append(data.color)
        if data.order_index is not None:
            updates.append("order_index = ?")
            params.append(data.order_index)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(domain_id)
            cursor.execute(f"UPDATE domains SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()

        cursor.execute("""
            SELECT 
                d.*,
                COUNT(DISTINCT t.id) AS topic_count,
                COUNT(DISTINCT r.id) AS resource_count
            FROM domains d
            LEFT JOIN topics t ON d.id = t.domain_id
            LEFT JOIN resources r ON t.id = r.topic_id
            WHERE d.id = ?
            GROUP BY d.id
        """, (domain_id,))
        return dict(cursor.fetchone())


@router.delete("/{domain_id}")
def delete_domain(domain_id: int, user=Depends(require_auth)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM domains WHERE id = ?", (domain_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Domain not found")
        cursor.execute("DELETE FROM domains WHERE id = ?", (domain_id,))
        conn.commit()
    return {"status": "deleted", "id": domain_id}
