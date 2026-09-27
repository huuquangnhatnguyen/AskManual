# AskManual

Photograph or describe a fault on an industrial drive and get a structured, cited answer
drawn from the manufacturer's own manuals, with every claim expanding to the cropped page
region it came from.

Stack: Python · FastAPI · Qdrant · BM25 · Postgres · Claude · server-rendered phone-width UI.
Plan and status: [MILESTONES.md](MILESTONES.md). Code map and open tasks: [DEVELOPING.md](DEVELOPING.md).

---

## Run locally

### 1. Install

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash). macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # then fill in the values below
```

Minimum `.env` for local work:

```ini
POSTGRES_PASSWORD=pick-anything
DATABASE_URL=postgresql://askmanual:pick-anything@localhost:5432/askmanual
QDRANT_URL=http://localhost:6333
```

### 2. Start the services

Start Docker Desktop first, then:

```bash
docker compose up -d qdrant postgres
```

### 3a. Run with fixtures (works today, no data needed)

```bash
uvicorn api.main:app --reload
```

Open http://localhost:8000. `/ask` returns the fixture answer, `/?fixture=refusal` shows the
refusal screen, and `/?delay=3` shows the loading state. `/health` should report
`"status": "ok"` once both services are up. `/docs` has the interactive API schema.

### 3b. Run the real pipeline

This needs AS2.3, AS3.1, AS4.1 and AS4.2 done (see DEVELOPING.md), plus the data:

```bash
python -m ingest.run corpus/          # -> chunks.jsonl + pages/   (corpus/ is not in git)
python -m retrieval.index             # -> Qdrant collection, index/bm25.pkl, Postgres fault_codes
```

Add to `.env`:

```ini
PIPELINE=real
ANTHROPIC_API_KEY=sk-ant-...
REFUSAL_THRESHOLD=<value from: python -m eval.calibrate --retriever fused>
```

Then run `uvicorn api.main:app` as above.

### 3c. Everything in Docker

```bash
docker compose up --build             # app + Qdrant + Postgres, http://localhost:8000
```

This runs in fixture mode, because the default image doesn't contain `chunks.jsonl` or `pages/`.

---

## Deploy (Railway)

Railway is the host in the plan: the app, Postgres and Qdrant live in one project, and HTTPS
comes built in. Render and Fly.io work the same way with their own CLIs. The Dockerfile already
reads the `PORT` the host injects.

There are two stages. **Stage 1** puts the fixture app on a public URL now (AS0.7). **Stage 2**
switches that same URL to the real pipeline once M2–M4 land (AS4.3).

### Stage 1: fixture app on a public URL

**One-time setup**

```bash
npm i -g @railway/cli
railway login                         # opens a browser
railway init                          # creates the project, name it "askmanual"
```

**Deploy the app** from the repo root. This uploads the directory and builds `Dockerfile`:

```bash
railway up
```

If it asks for a service, create one called `app`. Every command below that takes
`--service app` refers to it.

**Add Postgres**

```bash
railway add --database postgres
railway variables --service app --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}'
```

The `${{...}}` is a Railway reference, resolved on Railway's side. Keep the single quotes so
your shell doesn't expand it.

**Add Qdrant.** The CLI can't set every option here, so use the dashboard. In the project,
choose **+ New → Docker Image**, enter `qdrant/qdrant:v1.19.1`, and name the service `qdrant`. Then:

- **Settings → Volumes:** add a volume mounted at `/qdrant/storage`. Without it the index is
  wiped on every restart.
- **Variables:** add `QDRANT__SERVICE__HOST=::`. Railway's private network can be IPv6-only,
  and Qdrant listens on IPv4 unless told otherwise.

Point the app at it over the private network:

```bash
railway variables --service app --set 'QDRANT_URL=http://${{qdrant.RAILWAY_PRIVATE_DOMAIN}}:6333'
```

**Get the public URL**

```bash
railway domain --service app          # prints https://<something>.up.railway.app
```

**Check it (AS0.7 done-when)**

```bash
curl https://<your-domain>/health     # want "status": "ok": both probes run from Railway, not your laptop
```

Then do **AS0.8**. Open the URL on a real phone over cellular, not wifi. Tap the photo input
(it must open the camera), upload a photo, and ask a question. Write down anything that breaks.

**Redeploy** is one step: `railway up`. For push-to-deploy instead, push the repo to GitHub
and connect it under the `app` service's **Settings → Source**. The repo has no remote yet.

### Stage 2: switch the live URL to the real pipeline (AS4.3)

The real app needs three things the fixture app doesn't:

1. **Indexes built in the deployed services.** Run the builder from your laptop against them:
   - **Postgres:** copy `DATABASE_PUBLIC_URL` from the Postgres service's **Variables** tab.
   - **Qdrant:** a private Railway service can't be reached from your laptop. Either expose it
     for the build (**qdrant → Settings → Networking → TCP Proxy** on port 6333, and remove it
     afterwards), or use **Qdrant Cloud's free tier** instead: create a cluster, set
     `QDRANT_URL` and `QDRANT_API_KEY` on the app, and delete the Railway qdrant service.

   ```bash
   DATABASE_URL='<public postgres url>' QDRANT_URL='<reachable qdrant url>' QDRANT_API_KEY='<if cloud>' \
     python -m retrieval.index            # must end with three "ok" lines
   ```

2. **`chunks.jsonl`, `pages/` (414 MB) and `index/bm25.pkl` inside the image.** These aren't in
   git, and `.dockerignore` excludes them, so build with `Dockerfile.real`, which includes them.
   Build locally and push to a registry, then point the Railway service at that image:

   ```bash
   docker build -f Dockerfile.real -t ghcr.io/<you>/askmanual:real .
   docker login ghcr.io                  # GitHub username + a token with write:packages
   docker push ghcr.io/<you>/askmanual:real
   ```

   In the dashboard, open **app → Settings → Source → Connect Image** and enter
   `ghcr.io/<you>/askmanual:real`. Make the package public, or add registry credentials.
   From now on, a redeploy means: rebuild, push, then **Redeploy** in the dashboard.

3. **Generation settings on the app:**

   ```bash
   railway variables --service app --set 'ANTHROPIC_API_KEY=sk-ant-...' --set 'REFUSAL_THRESHOLD=<calibrated>'
   ```

   `Dockerfile.real` already sets `PIPELINE=real`.

**Check it (AS4.3 done-when):** on the live URL, ask gold question G01 ("ACS580 is showing
fault 2330…") and get real citations. Ask an out-of-corpus question (a Siemens S7 reset) and
get a refusal. `/evidence/not_a_chunk` should return 404.

### Where each setting lives

| Variable | Stage | Set on | Value |
|---|---|---|---|
| `DATABASE_URL` | 1 | app | `${{Postgres.DATABASE_URL}}` |
| `QDRANT_URL` | 1 | app | `http://${{qdrant.RAILWAY_PRIVATE_DOMAIN}}:6333`, or the Qdrant Cloud URL |
| `QDRANT_API_KEY` | 1 | app | Qdrant Cloud only |
| `QDRANT__SERVICE__HOST` | 1 | qdrant | `::` |
| `ANTHROPIC_API_KEY` | 2 | app | your key. Never commit it |
| `REFUSAL_THRESHOLD` | 2 | app | from `python -m eval.calibrate` |
| `PIPELINE` | 2 | image | `real`, set by `Dockerfile.real` |

`PORT` is injected by Railway; don't set it. Every key the app reads is listed in
[.env.example](.env.example).

### Troubleshooting

- **`/health` says `qdrant: ConnectError`:** check `QDRANT__SERVICE__HOST=::` on the qdrant
  service, and that `QDRANT_URL` uses the private domain and port 6333.
- **`/health` says `postgres: OperationalError`:** `DATABASE_URL` on the app isn't the
  reference above, or Postgres is still starting.
- **The build fails with `COPY pages` not found:** you built `Dockerfile.real` in a checkout
  without the ingest artifacts. Run step 3b first.
- **`/ask` returns 502 or 504:** `ANTHROPIC_API_KEY` is missing or invalid, or generation is
  slow. Raise `GENERATION_TIMEOUT` (default 45 seconds).
