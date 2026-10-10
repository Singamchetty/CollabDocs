# CollabDocs

Backend API for CollabDocs — a platform where users can create workspaces, invite
collaborators, write and version documents, leave comments, and control access with
role-based permissions. Think of it as a simplified Notion or Google Docs, API-only.
Postman is the client; there is no frontend in this repository.

## Stack

- Python 3.14, Django 6.1, Django REST Framework
- PostgreSQL 16 (via Docker Compose)
- [uv](https://docs.astral.sh/uv/) for dependency management

## Project layout

Domain logic is split into one Django app per area, mirroring the model groups in the brief:

- `users` — `User`
- `workspaces` — `Workspace`, `WorkspaceMember`
- `documents` — `Document`, `DocumentVersion`
- `comments` — `Comment`
- `tags` — `Tag`
- `audit_log` — `AuditLog`

Each app owns its models, serializers, views, tests and `urls.py`. `config/urls.py` only includes the
apps' URL files, so working inside an app never means editing `config/`.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/):
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Docker (any daemon works — Docker Desktop, Rancher Desktop, Colima, etc.) for Postgres via `docker compose`

## Setup

1. Copy the environment template and adjust if needed:

   macOS/Linux:

   ```bash
   cp .env.example .env
   ```

   Windows (PowerShell):

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d
   ```

3. Create a virtual environment and install dependencies with `uv`:

   macOS/Linux:

   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

   Windows (PowerShell):

   ```powershell
   uv venv
   .venv\Scripts\Activate.ps1
   uv pip install -r requirements.txt
   ```

   Windows (cmd.exe):

   ```bat
   uv venv
   .venv\Scripts\activate.bat
   uv pip install -r requirements.txt
   ```

4. Apply migrations:

   ```bash
   python manage.py migrate
   ```

5. Run the server:

   ```bash
   python manage.py runserver
   ```

   Commands in steps 4–5 are the same on every OS once the virtual environment is activated.

The API is served at `http://localhost:8000/api/`. Import `CollabDocs.postman_collection.json`
(repository root) into Postman and run its folders top to bottom, or use the Collection Runner:
each request saves the ids the next ones need as collection variables.

You can also connect a database client (DBeaver, JDBC, `psql`, etc.) directly to
Postgres using the `POSTGRES_*` values from `.env` — host `localhost`, port `5432`.

## API endpoints

The table lists all 17 endpoints. Conventions and a full request and response example for each
one follow it. Every request is also logged to the server console with method, path, status and
time taken.

| Method | Endpoint | Body / query | Notes |
|---|---|---|---|
| POST | `/api/users/` | `first_name`, `last_name`, `email`, `phone` | Email is lowercased and validated; email/phone must be unique |
| GET | `/api/users/{id}/` | | |
| POST | `/api/workspaces/` | `name`, `owner` (user id) | Owner is added as an `admin` member in the same transaction |
| GET | `/api/workspaces/{id}/` | | Includes `member_count` |
| POST | `/api/workspaces/{id}/members/` | `user_id`, `role` (`admin`/`editor`/`viewer`) | 404 unknown user, 409 already a member |
| GET | `/api/workspaces/{id}/members/` | | Members with nested user data |
| GET | `/api/workspaces/{id}/summary/` | | Document, member and total comment counts |
| POST | `/api/documents/` | `title`, `content`, `workspace`, `created_by`, `status` | Creates the document and version 1 atomically |
| PUT | `/api/documents/{id}/` | same as create, optional `saved_by` | Saves a new version atomically; `created_by` is ignored |
| GET | `/api/documents/` | `workspace`, `status` (comma-separated), `tag`, `search` | `search` matches title or content; paginated |
| GET | `/api/documents/{id}/versions/` | | Versions in order |
| GET | `/api/documents/{id}/stats/` | | Version, comment and distinct contributor counts |
| POST | `/api/documents/{id}/tags/` | `tags`: list of names | Creates missing tags; names are lowercased; idempotent |
| POST | `/api/comments/` | `document`, `author`, `content`, optional `parent` | Top-level comment or reply; a reply's parent must be on the same document |
| GET | `/api/comments/?document={id}` | `document` (required) | Threaded: replies nested under their parent; 400 without `document`, 404 if unknown |
| POST | `/api/tags/` | `name` | Trimmed and lowercased; 409 if the tag already exists |
| GET | `/api/audit-logs/` | `actor` (user id), `date_from`, `date_to` | Entries written by the Document `post_save` signal, newest first; dates are ISO dates or datetimes and a bare `date_to` includes that whole day |

### Conventions

- **Base URL:** `http://localhost:8000`. Send and receive JSON (`Content-Type: application/json`).
- **Ids and dates:** ids are UUIDs and timestamps are ISO 8601 in UTC.
- **No authentication:** the brief does not ask for any, so a request names the user it is about by id (`owner`, `created_by`, `saved_by`, `author`, `user_id`).
- **Pagination:** the document list and audit-log list return `{"count", "next", "previous", "results"}` with 20 items per page (`?page=2`). Members, versions and comment threads return a plain array.
- **Errors:**
  - `400 Bad Request`: `{"field": ["message", ...]}`. Problems that involve several fields use the key `non_field_errors`.
  - `404 Not Found` and `409 Conflict`: `{"detail": "message"}`. A malformed id in the URL is also a 404.
  - `405 Method Not Allowed` for any method an endpoint does not support.
- **About the examples:** they are real responses captured from the running API. Ids and timestamps were replaced with sample values so the examples read consistently.

### Users

#### Create a user

`POST /api/users/`

Creates a user. All four fields are required.

- `email` is trimmed, lowercased and validated, and must be unique.
- `phone` must be 7-15 digits with an optional leading `+`, and must be unique.

Request body:

```json
{
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@example.com",
  "phone": "+14155550101"
}
```

Response **201 Created**

```json
{
  "id": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@example.com",
  "phone": "+14155550101",
  "created_at": "2026-01-15T10:00:30.482915Z"
}
```

Error: an invalid email and phone gives **400 Bad Request**

```json
{
  "email": [
    "Enter a valid email address."
  ],
  "phone": [
    "Phone must be 7-15 digits, optionally starting with '+'."
  ]
}
```

Error: an email that already exists gives **400 Bad Request**

```json
{
  "email": [
    "user with this email already exists."
  ]
}
```

#### Get a user

`GET /api/users/{id}/`

Returns one user.

Response **200 OK**

```json
{
  "id": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@example.com",
  "phone": "+14155550101",
  "created_at": "2026-01-15T10:00:30.482915Z"
}
```

Error: an id that does not exist gives **404 Not Found**

```json
{
  "detail": "No User matches the given query."
}
```

### Workspaces

#### Create a workspace

`POST /api/workspaces/`

Creates a workspace and, in the same transaction, adds `owner` as a member with the `admin` role.

- `owner` is a user id; there is no authentication, so it is sent explicitly.

Request body:

```json
{
  "name": "Engineering",
  "owner": "e3e70682-c209-4cac-a29f-6fbed82c07cd"
}
```

Response **201 Created**

```json
{
  "id": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "name": "Engineering",
  "owner": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "is_active": true,
  "created_at": "2026-01-15T10:00:44.482915Z",
  "member_count": 1
}
```

Error: an owner that does not exist gives **400 Bad Request**

```json
{
  "owner": [
    "Invalid pk \"d95bafc8-f2a4-427b-9cf4-bb99f4bea973\" - object does not exist."
  ]
}
```

#### Get a workspace

`GET /api/workspaces/{id}/`

Returns the workspace with its member count.

Response **200 OK**

```json
{
  "id": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "name": "Engineering",
  "owner": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "is_active": true,
  "created_at": "2026-01-15T10:00:44.482915Z",
  "member_count": 2
}
```

#### Add a member

`POST /api/workspaces/{id}/members/`

Adds a user to the workspace with a role.

- `role` is one of `admin`, `editor`, `viewer`.
- A user can only be a member of a workspace once.

Request body:

```json
{
  "user_id": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
  "role": "editor"
}
```

Response **201 Created**

```json
{
  "id": "b8a1abcd-1a69-46c7-8da4-f9fc3c6da5d7",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "user": {
    "id": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
    "first_name": "Grace",
    "last_name": "Hopper",
    "email": "grace@example.com",
    "phone": "+14155550102",
    "created_at": "2026-01-15T10:00:37.482915Z"
  },
  "role": "editor",
  "joined_at": "2026-01-15T10:00:58.482915Z"
}
```

Error: a user who is already a member gives **409 Conflict**

```json
{
  "detail": "User is already a member of this workspace."
}
```

Error: a user id that does not exist gives **404 Not Found**

```json
{
  "detail": "User not found."
}
```

Error: an invalid role gives **400 Bad Request**

```json
{
  "role": [
    "\"owner\" is not a valid choice."
  ]
}
```

#### List members

`GET /api/workspaces/{id}/members/`

Returns every member with their role and nested user details (not paginated).

Response **200 OK**

```json
[
  {
    "id": "5bc8fbbc-bde5-4099-8164-d8399f767c45",
    "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
    "user": {
      "id": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
      "first_name": "Ada",
      "last_name": "Lovelace",
      "email": "ada@example.com",
      "phone": "+14155550101",
      "created_at": "2026-01-15T10:00:30.482915Z"
    },
    "role": "admin",
    "joined_at": "2026-01-15T10:00:51.482915Z"
  },
  {
    "id": "b8a1abcd-1a69-46c7-8da4-f9fc3c6da5d7",
    "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
    "user": {
      "id": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
      "first_name": "Grace",
      "last_name": "Hopper",
      "email": "grace@example.com",
      "phone": "+14155550102",
      "created_at": "2026-01-15T10:00:37.482915Z"
    },
    "role": "editor",
    "joined_at": "2026-01-15T10:00:58.482915Z"
  }
]
```

#### Workspace summary

`GET /api/workspaces/{id}/summary/`

Returns the number of documents, members and comments (across all the workspace's documents).

Response **200 OK**

```json
{
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "document_count": 1,
  "member_count": 2,
  "comment_count": 2
}
```

### Documents

#### Create a document

`POST /api/documents/`

Creates the document and its first version in one transaction. The audit log entry is written in the same transaction.

- `status` is one of `draft`, `published`, `archived` (default `draft`).
- `created_by` is optional; when sent it is also recorded as the author of version 1.

Request body:

```json
{
  "title": "Q4 launch plan",
  "content": "Draft v1: outline the launch milestones.",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "status": "draft"
}
```

Response **201 Created**

```json
{
  "id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "title": "Q4 launch plan",
  "content": "Draft v1: outline the launch milestones.",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "status": "draft",
  "updated_at": "2026-01-15T10:01:05.482915Z",
  "tag_names": [],
  "latest_version_number": 1
}
```

Error: a blank title and an invalid status gives **400 Bad Request**

```json
{
  "title": [
    "This field may not be blank."
  ],
  "status": [
    "\"frozen\" is not a valid choice."
  ]
}
```

#### Update a document

`PUT /api/documents/{id}/`

Replaces the document's fields and saves the new content as the next version, in one transaction.

- Send the full document, as with any `PUT`.
- `saved_by` is optional and records who saved this version (it defaults to the document creator).
- `created_by` is ignored on update, so authorship cannot be changed.

Request body:

```json
{
  "title": "Q4 launch plan",
  "content": "Draft v2: added owners and dates.",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "status": "draft",
  "saved_by": "21636369-8b52-4b4a-97b7-50923ceb3ffd"
}
```

Response **200 OK**

```json
{
  "id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "title": "Q4 launch plan",
  "content": "Draft v2: added owners and dates.",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "status": "draft",
  "updated_at": "2026-01-15T10:01:26.482915Z",
  "tag_names": [],
  "latest_version_number": 2
}
```

#### List documents

`GET /api/documents/`

Returns a paginated list, newest update first. All filters are optional and can be combined.

- `workspace`: workspace id.
- `status`: one status, or several separated by commas (`draft,published`).
- `tag`: tag name, case-insensitive.
- `search`: case-insensitive text found in the title or the content.
- `page`: page number (20 documents per page).

Example: `/api/documents/?workspace=cd613e30-d8f1-4adf-91b7-584a2265b1f5&status=draft,published&tag=python&search=launch`

Response **200 OK**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
      "title": "Q4 launch plan",
      "content": "Draft v2: added owners and dates.",
      "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
      "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
      "status": "draft",
      "updated_at": "2026-01-15T10:01:26.482915Z",
      "tag_names": [
        "django",
        "python"
      ],
      "latest_version_number": 2
    }
  ]
}
```

Error: an invalid status gives **400 Bad Request**

```json
{
  "status": [
    "Invalid status ['frozen']. Choose from ['draft', 'published', 'archived']."
  ]
}
```

#### List a document's versions

`GET /api/documents/{id}/versions/`

Returns every saved version in order, oldest first (not paginated).

Response **200 OK**

```json
[
  {
    "id": "6513270e-269e-4d37-b2a7-4de452e6b438",
    "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
    "content": "Draft v1: outline the launch milestones.",
    "version_number": 1,
    "saved_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
    "saved_at": "2026-01-15T10:01:19.482915Z"
  },
  {
    "id": "6018366c-f658-47a7-9ed3-4fe53a096533",
    "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
    "content": "Draft v2: added owners and dates.",
    "version_number": 2,
    "saved_by": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
    "saved_at": "2026-01-15T10:01:40.482915Z"
  }
]
```

#### Document stats

`GET /api/documents/{id}/stats/`

Returns the number of versions, the number of comments, and the number of distinct people who saved a version.

Response **200 OK**

```json
{
  "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "version_count": 2,
  "comment_count": 2,
  "contributor_count": 2
}
```

#### Add tags to a document

`POST /api/documents/{id}/tags/`

Attaches one or more tags by name. Tags that do not exist yet are created.

- Names are trimmed and lowercased, and duplicates in the list are ignored.
- Sending a tag the document already has is harmless.
- Returns the updated document.

Request body:

```json
{
  "tags": [
    "Python",
    "django"
  ]
}
```

Response **200 OK**

```json
{
  "id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "title": "Q4 launch plan",
  "content": "Draft v2: added owners and dates.",
  "workspace": "cd613e30-d8f1-4adf-91b7-584a2265b1f5",
  "created_by": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "status": "draft",
  "updated_at": "2026-01-15T10:01:26.482915Z",
  "tag_names": [
    "django",
    "python"
  ],
  "latest_version_number": 2
}
```

Error: an empty list gives **400 Bad Request**

```json
{
  "tags": [
    "This list may not be empty."
  ]
}
```

### Comments

#### Add a comment or reply

`POST /api/comments/`

Adds a top-level comment, or a reply when `parent` is set. `document`, `author` and `content` are required.

- A reply's `parent` must be a comment on the same document.

Request body:

```json
{
  "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "author": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "content": "Looks good - can we add a rollout date?"
}
```

Response **201 Created**

```json
{
  "id": "4462ebfc-5f91-4ef0-9cfb-ac6e7687a66e",
  "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "author": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
  "content": "Looks good - can we add a rollout date?",
  "parent": null,
  "created_at": "2026-01-15T10:01:47.482915Z",
  "reply_count": 0
}
```

Reply to that comment by also sending `parent`:

```json
{
  "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "author": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
  "content": "Added: ships on the 15th.",
  "parent": "4462ebfc-5f91-4ef0-9cfb-ac6e7687a66e"
}
```

Response **201 Created**

```json
{
  "id": "7b89296c-6dcb-4c50-8857-7eb1924770d3",
  "document": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
  "author": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
  "content": "Added: ships on the 15th.",
  "parent": "4462ebfc-5f91-4ef0-9cfb-ac6e7687a66e",
  "created_at": "2026-01-15T10:01:54.482915Z",
  "reply_count": 0
}
```

Error: a `parent` that belongs to a different document gives **400 Bad Request**

```json
{
  "non_field_errors": [
    "A reply must belong to the same document as its parent comment."
  ]
}
```

#### List a document's comments (threaded)

`GET /api/comments/?document={id}`

Returns the document's top-level comments, oldest first, each with its replies nested under `replies` (any depth). Not paginated.

- `document` is required.

Example: `/api/comments/?document=14a03569-d26b-4496-92e5-dfe8cb1855fe`

Response **200 OK**

```json
[
  {
    "id": "4462ebfc-5f91-4ef0-9cfb-ac6e7687a66e",
    "author": {
      "id": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
      "first_name": "Ada",
      "last_name": "Lovelace"
    },
    "content": "Looks good - can we add a rollout date?",
    "parent": null,
    "created_at": "2026-01-15T10:01:47.482915Z",
    "replies": [
      {
        "id": "7b89296c-6dcb-4c50-8857-7eb1924770d3",
        "author": {
          "id": "21636369-8b52-4b4a-97b7-50923ceb3ffd",
          "first_name": "Grace",
          "last_name": "Hopper"
        },
        "content": "Added: ships on the 15th.",
        "parent": "4462ebfc-5f91-4ef0-9cfb-ac6e7687a66e",
        "created_at": "2026-01-15T10:01:54.482915Z",
        "replies": []
      }
    ]
  }
]
```

Error: a missing `document` parameter gives **400 Bad Request**

```json
{
  "document": [
    "This query parameter is required."
  ]
}
```

### Tags

#### Create a tag

`POST /api/tags/`

Creates a tag. The name is trimmed and lowercased.

Request body:

```json
{
  "name": "Roadmap"
}
```

Response **201 Created**

```json
{
  "id": "db5b5fab-8f4d-4e27-9da1-494c73cf256d",
  "name": "roadmap",
  "document_count": 0
}
```

Error: a name that already exists (any capitalisation) gives **409 Conflict**

```json
{
  "detail": "Tag 'roadmap' already exists."
}
```

### Audit logs

#### List audit logs

`GET /api/audit-logs/`

Returns a paginated list of audit entries, newest first. Entries are written automatically whenever a document is created or updated; they cannot be created or changed through the API.

- `actor`: user id of the person who made the change.
- `date_from` / `date_to`: inclusive bounds as an ISO date (`2026-01-31`) or datetime (`2026-01-31T09:00:00Z`). A bare `date_to` includes that whole day.

Example: `/api/audit-logs/?actor=e3e70682-c209-4cac-a29f-6fbed82c07cd&date_from=2020-01-01&date_to=2099-12-31`

Response **200 OK**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "87751d4c-a850-4e2c-84dc-da6a797d76de",
      "actor": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
      "action": "updated",
      "model_name": "Document",
      "object_id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
      "timestamp": "2026-01-15T10:01:33.482915Z"
    },
    {
      "id": "e8d79f49-af6d-414c-8a6f-188a424e617b",
      "actor": "e3e70682-c209-4cac-a29f-6fbed82c07cd",
      "action": "created",
      "model_name": "Document",
      "object_id": "14a03569-d26b-4496-92e5-dfe8cb1855fe",
      "timestamp": "2026-01-15T10:01:12.482915Z"
    }
  ]
}
```

Error: an unparseable date gives **400 Bad Request**

```json
{
  "date_from": [
    "Use an ISO date (YYYY-MM-DD) or datetime."
  ]
}
```

## Running tests

```bash
python manage.py test
```

See [TESTING.md](TESTING.md) for running part of the suite, running the Postman collection with
`newman`, trying the error cases by hand, and the checks to show in the demo.

## Demo

_Link to the demo video will be added before final submission._
