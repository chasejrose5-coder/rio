-- Expired hosted sessions. Safe to run more than once.
-- The API used to delete expired rows on every signed-in request. That
-- delete filters on expires_at. The primary key is sid_hash, so the delete
-- scanned the table. Cleanup is now occasional; this index is for that scan.
-- Run this in the Supabase SQL editor. The app does not apply it.
-- Do not run it against a database you have not backed up. Production was
-- not changed by the commit that added this file.

create index if not exists app_sessions_expires_at
  on public.app_sessions (expires_at);
