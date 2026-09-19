# CollabDocs — 10-Day Development Plan

## Project goal

Build the Django REST Framework backend for CollabDocs, an API-only collaborative document platform with users, workspaces, members, documents, versions, comments, tags, audit logs, transactions, middleware, and role-based access control.

## Team responsibilities

| Member | Ownership | Main deliverables |
|---|---|---|
| Member 1 — Core/Data Lead | Setup, models, migrations, transactions, middleware, signals | Eight models, PostgreSQL setup, atomic workflows, request logging, AuditLog signal |
| Member 2 — Workspace/API Lead | Users and workspaces | User endpoints, workspace endpoints, member management, permissions, summaries |
| Member 3 — Documents/API Lead | Documents, versions, comments, tags, audit APIs | Document/version endpoints, threaded comments, tags, audit-log filtering |

All members review one another's pull requests and participate in integration testing.

## AI-agent workflow

Use AI agents in five roles:

1. **Planning agent** — converts requirements into small tasks and API contracts.
2. **Coding agent** — implements one feature at a time using the agreed conventions.
3. **Review agent** — checks correctness, security, query optimization, and rubric coverage.
4. **Testing agent** — creates unit/API tests and Postman requests.
5. **Documentation agent** — prepares the README, endpoint examples, and demo script.

For every task:

```text
Requirement → API contract → AI implementation → Human review → Tests → Pull request
```

AI agents must not change shared models or migrations without review from Member 1.

## Ten-day schedule

### Day 1 — Architecture and setup

- Read the complete brief and marking rubric.
- Agree on app structure, URL conventions, response format, error format, and branch strategy.
- Set up the Django project, DRF, PostgreSQL, `.env`, and pinned dependencies.
- Define the API contract for all 17 endpoints.
- Create the initial Postman collection structure.

**Deliverable:** The project runs locally and the API contracts are agreed upon.

### Day 2 — Models and migrations

Member 1 implements and documents:

- `User`
- `Workspace`
- `WorkspaceMember`
- `Document`
- `DocumentVersion`
- `Comment`
- `Tag`
- `AuditLog`

Requirements include UUID primary keys, `TextChoices`, the unique workspace/member constraint, threaded comments, document/tag many-to-many relations, and correct `on_delete` behavior.

Members 2 and 3 review relationships and prepare seed data and fixtures.

**Deliverable:** Migrations apply cleanly from an empty database.

### Day 3 — Infrastructure and serializers

Member 1 implements:

- Request logging middleware
- Document `post_save` signal
- Signal registration in `AppConfig.ready()`
- Common error handling conventions

Members 2 and 3 implement the initial serializers, custom validation, nested representations, and at least two `SerializerMethodField` usages.

**Deliverable:** Middleware logs method, path, status, and duration; serializers validate correctly.

### Day 4 — Users and workspaces

Member 2 implements:

- `POST /api/users/`
- `GET /api/users/{id}/`
- `POST /api/workspaces/`
- `GET /api/workspaces/{id}/`
- `POST /api/workspaces/{id}/members/`
- `GET /api/workspaces/{id}/members/`
- `GET /api/workspaces/{id}/summary/`

Use `ModelViewSet`, `@action`, `transaction.atomic()`, `select_related()`, `annotate()`, and `Count()`.

The workspace owner must automatically become an admin member. Duplicate members must return HTTP 409.

**Deliverable:** User and workspace flows work end-to-end.

### Day 5 — Documents and versions

Member 3 implements:

- `POST /api/documents/`
- `PUT /api/documents/{id}/`
- `GET /api/documents/`
- `GET /api/documents/{id}/versions/`
- `GET /api/documents/{id}/stats/`
- `POST /api/documents/{id}/tags/`

Every document save must create a new version inside the same atomic transaction. Implement workspace/status/tag filtering, title search with `Q` objects, `select_related()`, `prefetch_related()`, and aggregation queries.

**Deliverable:** Document creation, updates, version history, filtering, tags, and statistics work.

### Day 6 — Comments, tags, and audit logs

Member 3 implements:

- `POST /api/comments/`
- `GET /api/comments/?document={id}`
- `POST /api/tags/`
- `GET /api/audit-logs/`

Support top-level comments and replies, validate parent-document consistency, handle duplicate tags, and filter audit logs by actor and date range.

Members 1 and 2 review signal output and role-based access rules.

**Deliverable:** Comments, threaded replies, tags, and audit-log filtering work.

### Day 7 — Integration and optimization

All members merge the feature branches and resolve conflicts.

Review the project for:

- `ModelViewSet` for standard CRUD
- `@action` for summaries, stats, tags, and versions
- `DefaultRouter`
- `select_related()` and `prefetch_related()` for nested data
- Query-parameter filtering and `Q` searches
- `Count()` or `aggregate()` in at least three endpoints
- `values_list()` where only IDs are required
- Correct 400, 404, and 409 responses
- Complete transaction and rollback handling

**Deliverable:** One integrated branch with all endpoints reachable.

### Day 8 — Automated tests and Postman

- Test models, constraints, transactions, rollback behavior, signals, and middleware.
- Test all user, workspace, document, comment, tag, and audit-log endpoints.
- Test validation failures, missing objects, duplicate records, and permission failures.
- Complete the Postman collection with all 17 endpoints.

**Deliverable:** Automated tests pass and Postman covers every required endpoint.

### Day 9 — Clean-environment validation

Run the project from a clean environment:

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

Verify `.env.example`, pinned `requirements.txt`, clean migrations, README setup instructions, Postman requests, and absence of committed secrets.

**Deliverable:** A reproducible project that works from a fresh clone.

### Day 10 — Demo and submission

Record a 5–10 minute demo showing:

1. User creation
2. Workspace creation and automatic owner membership
3. Adding members with roles
4. Document creation and update
5. Version history
6. Tags and threaded comments
7. Statistics or summary aggregation
8. Middleware logs in the console
9. AuditLog creation after a document update
10. Transaction rollback after a failed operation

Commit the final Postman collection and add the demo link to `README.md`.

## Git workflow

Suggested branches:

```text
main
develop
feature/core-models
feature/users-workspaces
feature/documents-comments
feature/tests
feature/documentation
```

Use small pull requests. Every pull request should include tests and receive at least one teammate review before merging.

## Definition of done

- All eight required models are implemented correctly.
- All 17 endpoints work with meaningful responses and status codes.
- Transactions protect workspace and document workflows.
- Middleware and signals are registered and working.
- Query optimization and aggregation requirements are demonstrated.
- Tests pass from a clean database.
- README, `.env.example`, requirements, migrations, and Postman collection are committed.
- Demo video covers the required behaviors.

## Reusable AI prompts

### Coding agent

```text
Implement this Django REST Framework requirement: [requirement]

Use the existing project conventions. Use ModelViewSet for standard CRUD and
@action for custom endpoints. Include validation, correct HTTP status codes,
tests, and only modify files necessary for this task.
```

### Review agent

```text
Review this code against the CollabDocs rubric. Check UUID primary keys,
TextChoices, transactions, permissions, query optimization, signals,
validation, error handling, and HTTP status codes. List issues by severity.
```

### Testing agent

```text
Create Django REST Framework tests for this endpoint, including success cases,
validation errors, missing objects, duplicate records, transaction rollback,
and permission failures.
```
