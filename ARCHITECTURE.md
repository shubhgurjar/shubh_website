# High-Level Architecture

```mermaid
flowchart LR
    User["User"]
    Browser["Web browser"]
    CDN["External CDNs<br/>Vue 3, Tailwind CSS, Marked.js"]
    Media["External resources<br/>YouTube, Google Drive"]

    subgraph App["Career Knowledge Hub"]
        UI["Vue 3 single-page app<br/>static/index.html, static/js/app.js"]
        API["FastAPI application<br/>app.py"]

        subgraph Routes["API routers"]
            AuthRoutes["Authentication and settings<br/>/api/auth"]
            DomainRoutes["Domains<br/>/api/domains"]
            TopicRoutes["Topics<br/>/api/topics"]
            ResourceRoutes["Resources<br/>/api/resources"]
            UploadRoutes["File uploads<br/>/api/uploads"]
            BackupRoutes["Backup and search<br/>/api/backup, /api/search"]
        end

        Auth["Auth dependency<br/>PBKDF2 password hashes<br/>JWT cookie or Bearer token"]
        DBAccess["SQLite access and startup seeding<br/>database.py"]
        SQLite[("SQLite database<br/>data/career_hub.db<br/>settings, domains, topics, resources")]
        Uploads[("Local uploaded files<br/>static/uploads/")]
        Seed["Initial data<br/>data/seed_data.json"]
    end

    User --> Browser
    Browser -->|"HTTP: page and API requests"| UI
    UI -->|"Same-origin JSON and multipart requests<br/>credentials: same-origin"| API
    UI -.->|"Loads frontend libraries"| CDN
    UI -.->|"Opens or embeds linked content"| Media

    API --> AuthRoutes
    API --> DomainRoutes
    API --> TopicRoutes
    API --> ResourceRoutes
    API --> UploadRoutes
    API --> BackupRoutes

    AuthRoutes --> Auth
    DomainRoutes -->|"Writes require authentication"| Auth
    TopicRoutes -->|"Writes require authentication"| Auth
    ResourceRoutes -->|"Writes require authentication"| Auth
    UploadRoutes -->|"Requires authentication"| Auth
    BackupRoutes -->|"Import/export require authentication"| Auth

    AuthRoutes --> DBAccess
    DomainRoutes --> DBAccess
    TopicRoutes --> DBAccess
    ResourceRoutes --> DBAccess
    BackupRoutes --> DBAccess
    UploadRoutes -->|"Save uploaded files"| Uploads
    API -->|"Serve static assets and uploaded files"| Browser

    DBAccess --> SQLite
    DBAccess -.->|"Seed when domains are empty"| Seed
    BackupRoutes -.->|"JSON export / import"| Browser
```

## Diagram notes

- On startup, the FastAPI lifespan initializes the SQLite schema and seeds default data when the domains table is empty.
- Domain, topic, resource, and settings changes are persisted in SQLite. Uploaded files are stored under `static/uploads/` and served as static files.
- Authentication is enforced by the API routes that use the `require_auth` dependency. The auth status and login endpoints are used by the frontend to manage the session.
- The browser loads Vue, Tailwind CSS, and Marked.js from external CDNs. YouTube and Google Drive are linked or embedded content, not backend services.
- Backup export and import exchange JSON through the browser; GitHub backup/restore is a user-driven workflow.

## Import into diagrams.net (draw.io)

Create a new diagram, choose **Arrange → Insert → Advanced → Mermaid**, then paste the Mermaid source from the code block above. The Markdown file is the editable source for the diagram.
