# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_REGION` | Your B2 region segment, e.g. `us-west-004` |
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_PUBLIC_URL_BASE` | Optional public bucket URL base |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

### B2 environment migration

Older deployments may still have the pre-standard B2 names below. For a rolling
deploy, add the new variable while keeping the old one, deploy this version, then
remove the old variable in a later release. When both key ID variables are set,
`B2_APPLICATION_KEY_ID` wins.

| Old variable | New variable | Notes |
|--------------|--------------|-------|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` | Same application key ID value |
| `B2_ENDPOINT` | `B2_REGION` | Use only the region segment, e.g. `us-west-004`, not the full endpoint URL |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` | Optional; leave blank to use presigned URLs |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
