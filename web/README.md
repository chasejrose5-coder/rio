# RIO web

The Next.js app. The live site is `https://www.riorunning.com`. Streamlit stays up at `https://riotraining.streamlit.app` and links here. `rio-one-mocha.vercel.app` and `rio-rio-44fa.vercel.app` serve this same build and show a note with that link. They are not redirected.

## Run it with the API

From the repository root:

```bash
bash scripts/dev-local.sh
```

The API listens on `http://127.0.0.1:8000`. This app listens on `http://127.0.0.1:3000`. The script uses the local account file and does not read production Supabase settings. See `docs/migration/step3-plan.md`.

`NEXT_PUBLIC_RIO_API_URL` is the API origin. It defaults to `http://localhost:8000`. The cookie is the API's `rio_hosted` cookie. Requests send it with `credentials: "include"`.

The test site sets that variable to `/api` and sets `RIO_API_ORIGIN` to the Render origin. Next rewrites `/api/*` onto that origin, so the browser stays on the Vercel host. A laptop leaves `RIO_API_ORIGIN` unset and this rewrite stays off. The checklist is `docs/migration/deploy-test.md`.

Fonts and photos are not committed under `web/public`. `ui/static/fonts` and `ui/static/photos` are the source of truth, and Streamlit serves those files. `npm run dev` and `npm run build` copy them into `web/public/fonts` and `web/public/photos` as ordinary files before Next starts. Those two folders are gitignored. The URLs stay `/fonts/*` and `/photos/*`.

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
