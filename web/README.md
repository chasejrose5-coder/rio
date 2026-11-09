# RIO web

The Next.js app. Streamlit is still the live site. This folder does not replace it.

## Run it with the API

From the repository root:

```bash
bash scripts/dev-local.sh
```

The API listens on `http://127.0.0.1:8000`. This app listens on `http://127.0.0.1:3000`. The script uses the local account file and does not read production Supabase settings. See `docs/migration/step3-plan.md`.

`NEXT_PUBLIC_RIO_API_URL` is the API origin. It defaults to `http://localhost:8000`. The cookie is the API's `rio_hosted` cookie. Requests send it with `credentials: "include"`.

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
