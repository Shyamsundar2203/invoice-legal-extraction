#!/usr/bin/env bash
# Quick end-to-end smoke test: starts the backend and runs extraction on the
# bundled sample invoice so you can see the pipeline work in under a minute.
set -e

cd "$(dirname "$0")/.."

echo "==> Installing backend dependencies (if needed)"
pip install --quiet -r backend/requirements.txt

echo "==> Starting API server on :8000"
export DATA_DIR="$(pwd)/data"
(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &)
sleep 3

echo "==> Sending sample invoice to /extract"
curl -s -X POST "http://localhost:8000/extract?doc_type=invoice" \
  -F "file=@data/sample/sample_invoice.png" | python3 -m json.tool

echo ""
echo "==> Done. Open frontend/index.html in a browser to use the UI,"
echo "    or visit http://localhost:8000/docs for the interactive API docs."
