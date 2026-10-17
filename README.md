# 🚀 Shubh's Software Engineering Career Knowledge Hub

A personal, private, and high-performance web application to organize, track, and master everything related to your software engineering career.

Built with **FastAPI (Python)**, **SQLite**, and **Vue.js 3** + **Tailwind CSS**, designed for zero-config local operation, in-browser rich media previews, and one-click JSON sync for GitHub version control.

---

## 🌟 Key Features

- ⚡ **Zero-Friction Quick Bulk Paste**: Paste multiple YouTube, PDF, or Google Drive links at once (one per line). Just pick the domain and type—titles, thumbnails, and embeddings are generated automatically with no descriptions required.
- 🧠 **Bird's-Eye View Dashboard**: Domain summary cards with progress statistics, concept counts, and quick filter chips.
- 🌳 **Hierarchical Knowledge Architecture**: Structured into Domains (*AI & ML, System Design, Backend, etc.*) $\rightarrow$ Topics & Concepts (*LLMs, Caching, RAG, etc.*) $\rightarrow$ Attached Resources.
- 📺 **YouTube Video Study Mode**: Direct YouTube link integration with auto-extracted thumbnails, embedded player, and timestamped study notes.
- 📁 **Google Drive Integration**: Direct one-click launch buttons linked to your Google Drive folders and documents for every topic.
- 📄 **In-Browser PDF Viewer & Uploads**: Upload PDF papers, cheatsheets, and architectural guides directly from your machine with instant in-browser reading.
- 📝 **Markdown Notes & Code Highlighting**: Write formatted personal notes, code snippets, and study takeaways with live Markdown rendering.
- 🔍 **Real-Time Global Search**: Instant search across all domains, topics, titles, tags, and notes.
- 💾 **SQLite + 1-Click JSON Backup**: Fast querying backed by SQLite (`data/career_hub.db`), paired with instant JSON Export & Import so you can commit human-readable backups to GitHub anytime.
- 🔒 **Private Access Control**: Master password protection with secure PBKDF2 hashing and persistent JWT session cookies.

---

## ⚡ Quick Start

### 1. Launch with Single Command

Simply run the startup script:

```bash
./run.sh
```

The script will automatically:
1. Verify Python 3
2. Create the virtual environment (`venv/`) if not already present
3. Install required dependencies
4. Initialize the SQLite database and seed initial Software Engineering domains
5. Launch the application server at [http://localhost:8000](http://localhost:8000)

### 2. Manual Launch (Alternative)

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Open your browser at **`http://localhost:8000`**.

---

## 🔐 Authentication & Security

- **Default Master Password**: `admin123`
- You can change the master password directly inside the app by clicking the **Settings (⚙️)** icon in the header.
- To customize via environment variable, set:
  ```bash
  export CAREER_HUB_PASSWORD="your-secure-password"
  ```
- All editing, uploading, and backups require authentication, keeping your personal career hub private if deployed to the web.

---

## 🗂️ Project Structure

```
shubh_website/
├── run.sh                  # Single-command executable runner
├── app.py                  # FastAPI application entrypoint
├── config.py               # Paths, security secrets, and environment settings
├── database.py             # SQLite database initialization & schema
├── models.py               # Pydantic data schemas
├── auth.py                 # PBKDF2 password hashing & JWT auth handlers
├── requirements.txt        # Backend dependencies
├── data/
│   ├── career_hub.db       # Primary SQLite database
│   └── seed_data.json      # Starter SWE domains and topics
├── routers/
│   ├── auth.py             # Login, logout, status & password update endpoints
│   ├── domains.py          # Domain CRUD and statistics
│   ├── topics.py           # Topics CRUD and filtering
│   ├── resources.py        # Resources (YouTube, PDFs, Drive, Notes) & favorites
│   ├── uploads.py          # File/PDF upload streaming
│   └── backup.py           # 1-click JSON Export/Import & Global Search
└── static/
    ├── index.html          # Vue 3 SPA frontend (Tailwind CSS, modals, embeds)
    ├── js/
    │   └── app.js          # Vue 3 application state and API client
    ├── css/
    │   └── custom.css      # Typography, scrollbars, and markdown styling
    └── uploads/            # Local directory for uploaded PDFs and documents
```

---

## 🔄 GitHub Sync & Backup

To back up your data to GitHub:
1. In the app header or footer, click **JSON Backup & Sync (💾)**.
2. Click **Download JSON** to get an export file (e.g. `career_hub_backup_2026.json`).
3. Commit this JSON file to your GitHub repository:
   ```bash
   git add data/ .gitignore
   git commit -m "chore: backup career knowledge hub"
   git push origin main
   ```
4. On any new device, you can import this JSON file with one click using the **Restore / Import from JSON** modal!

---

## ☁️ Publishing to the Web (Optional)

When you're ready to host this online:
1. Deploy to any Python host like **Render**, **Railway**, **Fly.io**, or an **AWS / DigitalOcean VPS**.
2. Set the `CAREER_HUB_PASSWORD` environment variable.
3. The site will automatically lock behind your master password so only you have access!
