"""Create Supabase Storage policies for SalikChat."""

import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

POLICIES = [
    # issue-media: authenticated can insert
    """CREATE POLICY "Allow authenticated uploads to issue-media"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'issue-media')""",

    # issue-media: public can read
    """CREATE POLICY "Allow public read on issue-media"
ON storage.objects FOR SELECT TO public
USING (bucket_id = 'issue-media')""",

    # issue-media: owner can delete
    """CREATE POLICY "Allow owners to delete from issue-media"
ON storage.objects FOR DELETE TO authenticated
USING (bucket_id = 'issue-media')""",

    # issue-media: owner can update
    """CREATE POLICY "Allow owners to update issue-media"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'issue-media')
WITH CHECK (bucket_id = 'issue-media')""",

    # chat-media: authenticated can insert
    """CREATE POLICY "Allow authenticated uploads to chat-media"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'chat-media')""",

    # chat-media: authenticated can read
    """CREATE POLICY "Allow authenticated read on chat-media"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'chat-media')""",

    # avatars: authenticated can insert
    """CREATE POLICY "Allow authenticated uploads to avatars"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'avatars')""",

    # avatars: public can read
    """CREATE POLICY "Allow public read on avatars"
ON storage.objects FOR SELECT TO public
USING (bucket_id = 'avatars')""",

    # avatars: owner can update
    """CREATE POLICY "Allow users to update own avatars"
ON storage.objects FOR UPDATE TO authenticated
USING (bucket_id = 'avatars')
WITH CHECK (bucket_id = 'avatars')""",

    # mechanic-docs: authenticated can insert
    """CREATE POLICY "Allow authenticated uploads to mechanic-docs"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'mechanic-docs')""",

    # mechanic-docs: authenticated can read
    """CREATE POLICY "Allow authenticated read on mechanic-docs"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'mechanic-docs')""",
]


def run_sql(sql):
    """Execute SQL via Supabase REST SQL endpoint."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/"
    # Actually, we'll use the management API query endpoint
    # Supabase provides a /pg/ endpoint or we can use the postgrest rpc
    # The simplest way: use supabase-py to call rpc
    pass


def main():
    # Use httpx/urllib to call the Supabase SQL endpoint
    endpoint = f"{SUPABASE_URL}/rest/v1/rpc/"

    # Actually, Supabase doesn't expose raw SQL via REST.
    # We need to use the management API or the SQL Editor.
    # Let's use the pg-meta API instead:
    # POST /pg/query with {"query": "..."}
    # This requires the service role key.

    for i, sql in enumerate(POLICIES):
        policy_name = sql.split('"')[1]
        data = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/pg/query",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SERVICE_KEY}",
                "apikey": SERVICE_KEY,
            },
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req)
            print(f"  OK  [{i+1}/{len(POLICIES)}] {policy_name}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if "already exists" in body.lower() or "duplicate" in body.lower():
                print(f"  OK  [{i+1}/{len(POLICIES)}] {policy_name} (already exists)")
            else:
                print(f"  FAIL [{i+1}/{len(POLICIES)}] {policy_name}: {e.code} {body[:200]}")


if __name__ == "__main__":
    main()
