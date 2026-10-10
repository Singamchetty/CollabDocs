# Testing CollabDocs

Three ways to check the project, from fastest to most hands-on, plus a fresh-checkout check at the end:

1. **Automated tests** (`manage.py test`): models, constraints, transactions, signal, middleware, serializers and every endpoint.
2. **Postman collection run** (`newman` or the Postman app): all 17 endpoints against a live server.
3. **Manual checks**: the behaviours the brief asks you to demonstrate (middleware logs, audit log, rollback).

Do the [setup in the README](README.md#setup) first: `.env` copied, Postgres running, virtual environment active.

## 1. Automated tests

```bash
python manage.py test
```

This ends with `OK` when everything passes. Django creates a separate `test_<POSTGRES_DB>` database for the run and deletes it afterwards, so your real data is never touched. The `POSTGRES_USER` in `.env` must be allowed to create databases (the Docker Compose user is).

Request-log lines such as `POST /api/users/ 201 12.3ms` are printed while the tests run. That is the logging middleware working, not an error.

### Running part of the suite

```bash
python manage.py test users                      # one app
python manage.py test documents.test_model_relationships   # one file
python manage.py test documents.tests.DocumentWriteApiTests   # one class
python manage.py test documents.tests.DocumentWriteApiTests.test_put_saves_a_new_version_and_logs_update   # one test
python manage.py test -v 2                       # list every test as it runs
python manage.py test --failfast                 # stop at the first failure
```

### What each part covers

| Where | Covers |
|---|---|
| `documents/test_model_relationships.py` | All 8 models: UUID primary keys, `TextChoices`, unique constraints, self-referential comment parent, tag many-to-many, cascade vs `SET_NULL` on delete, and that no model change is missing a migration |
| `users/tests.py` | `POST /api/users/`, `GET /api/users/{id}/`: validation, duplicates, 404 |
| `workspaces/tests.py` | Workspace create (owner becomes admin, rollback on failure), members (404 unknown user, 409 duplicate, fixed query count), summary aggregates, member unique constraint |
| `documents/tests.py` | Document create/update with versions, atomic rollback of document + version + audit log, row lock on update, list filters (`workspace`, `status`, `tag`, `search`), versions, stats, tags, the `post_save` signal, the exception handler, the request-logging middleware, and that bad query parameters return errors in the same shape as serializer errors |
| `comments/tests.py` | Comments and replies, cross-document parent check, threaded listing with a fixed query count |
| `tags/tests.py` | Tag creation, name normalisation, 409 on duplicates |
| `audit_log/tests.py` | Actor and date-range filters, whole-day `date_to`, read-only behaviour |

## 2. Postman collection (all 17 endpoints)

`CollabDocs.postman_collection.json` in the repository root has one request per endpoint, grouped into Users, Workspaces, Documents, Comments, Tags and Audit Logs. Each request saves the ids that the next ones need (user, workspace, document and so on), so it runs top to bottom without editing.

**Important:** the collection creates real records. Point it at a throwaway database rather than the one you use day to day.

### Step 1: create a throwaway database and start the API on it

Use the `POSTGRES_USER` from your `.env` (`collabdocs` in `.env.example`).

macOS/Linux:

```bash
docker compose exec -T db createdb -U collabdocs collabdocs_e2e
POSTGRES_DB=collabdocs_e2e python manage.py migrate
POSTGRES_DB=collabdocs_e2e python manage.py runserver
```

Windows (PowerShell):

```powershell
docker compose exec -T db createdb -U collabdocs collabdocs_e2e
$env:POSTGRES_DB = "collabdocs_e2e"
python manage.py migrate
python manage.py runserver
```

An environment variable takes priority over `.env`, which is why this does not touch your normal database.

### Step 2: run the collection

**In the Postman app:** import the file, open the collection, and use *Run collection* (or send the requests one by one from the top). `base_url` defaults to `http://localhost:8000`.

**From the command line** (needs Node.js), in a second terminal:

```bash
npx newman run CollabDocs.postman_collection.json
```

Expected result: newman reports `18` requests (the 17 endpoints plus one helper request that the *Add Member* pre-request script sends to create its second user), `26` assertions, and `0` in the `failed` column.

### Step 3: clean up

Stop the server (Ctrl+C), then:

```bash
docker compose exec -T db dropdb -U collabdocs collabdocs_e2e
```

On Windows PowerShell also run `Remove-Item Env:POSTGRES_DB` (or close the terminal) so later commands use your normal database again.

### Trying the error cases by hand

The collection runs the happy path. To see the error handling, edit a request in Postman and resend it. Note that *Create User* and *Create Tag* put `{{$timestamp}}` in their bodies, so every send is unique until you replace it with a fixed value.

| Request | Change | Expected |
|---|---|---|
| Add Member | Send it twice | 409 (already a member) |
| Add Member | Set `user_id` to `00000000-0000-4000-8000-000000000000` | 404 (valid format, no such user) |
| Create User | Replace `{{$timestamp}}` in the email and phone with fixed values, then send it twice | second send is 400 (email and phone already used) |
| Create Tag | Replace `{{$timestamp}}` in the name with a fixed word, then send it twice | second send is 409 |
| Add Comment | Create a second document with *Create Document*, then set this request's `document` to the new document's id while keeping `parent` | 400 (reply must stay on the parent's document) |
| List Comments | Untick the `document` query param | 400 |
| List Documents | Set `status=bogus` | 400 |
| Get User | Use a uuid that does not exist | 404 |

## 3. Manual checks for the demo

**Middleware logs.** With `runserver` running, every request prints a line like `PUT /api/documents/<id>/ 200 41.20ms` (method, path, status, milliseconds) in the server console.

**Audit log from the signal.** Create a document, update it with `PUT`, then call `GET /api/audit-logs/?actor=<user id>`. You should see one `created` and one `updated` entry for that document. The actor is the document's `created_by`, even if a different user saved the update.

**Atomic transactions and rollback.** Creating a document is two steps in one transaction: save the document (which also writes an audit-log row through the signal), then save version 1. To show a rollback live, make the database reject the second step, send the request from Postman, and show that the first step was undone too. No code changes are needed.

1. In your database client, run this against the database the server uses. It makes every insert into the versions table fail:

   ```sql
   CREATE FUNCTION demo_fail_version_insert() RETURNS trigger AS $$
   BEGIN
     RAISE EXCEPTION 'demo: version insert blocked';
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER demo_block_versions
   BEFORE INSERT ON documents_documentversion
   FOR EACH ROW EXECUTE FUNCTION demo_fail_version_insert();
   ```

2. In Postman, send *Create Document*. It returns **500**, because the version insert failed.
3. Show that nothing was kept. In the client run `select count(*) from documents_document;` and `select count(*) from audit_log_auditlog;` (both unchanged), or call `GET /api/documents/` and `GET /api/audit-logs/`. The document row and its audit-log row had already been inserted when the failure happened, and were undone with it.
4. Remove the trigger and send the same request again. It now returns **201** and creates the document, version 1 and the audit-log entry together:

   ```sql
   DROP TRIGGER demo_block_versions ON documents_documentversion;
   DROP FUNCTION demo_fail_version_insert();
   ```

Do this on a throwaway database (section 2) if you can, and always run the `DROP` statements afterwards, or every later document create will fail.

**Rollback without touching the database.** The test suite also covers this. Run these with `-v 2` and show the output:

```bash
python manage.py test -v 2 \
  documents.tests.DocumentWriteApiTests.test_create_rolls_back_document_and_audit_log_if_version_fails \
  documents.tests.DocumentWriteApiTests.test_put_rolls_back_content_change_if_version_fails \
  workspaces.tests.WorkspaceApiTests.test_create_workspace_rolls_back_if_member_creation_fails
```

The backslashes are macOS/Linux line continuations; on Windows put the whole command on one line.

Each one simulates the failure by patching the second step of a two-step save to raise an error, then checks that the first step (the document or workspace, and the audit-log row) was undone too. Say that the failure is simulated if you show this in the demo.

**Looking at the data.** Connect any database client (or `docker compose exec db psql -U collabdocs -d collabdocs`) to host `localhost`, port `5432`, with the values from `.env`.

## 4. Checking a fresh checkout

To confirm the repository works from nothing, clone it to a new folder and run the README setup, but point it at an **empty** database. If you reuse a database that is already migrated, `migrate` will say "No migrations to apply" and prove nothing about migrating from scratch.

macOS/Linux:

```bash
docker compose exec -T db createdb -U collabdocs collabdocs_clean
export POSTGRES_DB=collabdocs_clean
python manage.py check
python manage.py makemigrations --check --dry-run   # must print "No changes detected"
python manage.py migrate                            # must apply every migration
python manage.py test
```

On Windows PowerShell use `$env:POSTGRES_DB = "collabdocs_clean"` instead of `export`. Afterwards drop it with `docker compose exec -T db dropdb -U collabdocs collabdocs_clean`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Cannot connect to the Docker daemon` | Docker is not running. Start Docker Desktop, Rancher Desktop or Colima, then `docker compose up -d`. |
| `Connection refused` on port 5432 | Postgres is not running. Run `docker compose up -d`. |
| `password authentication failed` | The `POSTGRES_*` values in `.env` no longer match the database. Postgres only applies them the first time its volume is created, so editing `.env` later does not change the existing user. Put the old values back, or run `docker compose down -v` to delete the volume (this deletes the data in it) and start again. |
| `ImproperlyConfigured: Set the DJANGO_SECRET_KEY environment variable` (or another variable name) | No `.env` file, or it lacks that variable. Run `cp .env.example .env` (Windows: `Copy-Item .env.example .env`). |
| `permission denied to create database` | The `.env` database user cannot create the test database. Use the Docker Compose user. |
| `database "test_..." already exists` | A previous run was interrupted. Answer `yes` to delete it, or run with `--noinput`. |
| `Error: That port is already in use.` | Stop the other server, or run `python manage.py runserver 8001` and set the Postman `base_url` to match. |
| `npx: command not found` | Node.js is not installed. Install it, or use the Postman app instead of `newman`. |
