# TransitMate — AI-Assisted Transportation Recommendation System

This is a minimal Django + DRF scaffold for the Final Term Project (Transportation + Recommendation System + Python).

Quick setup (Windows PowerShell):

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and start server
python manage.py migrate
python manage.py runserver

# Run tests
python manage.py test
```

What I added:
- Minimal Django project `transitmate`
- App `recommend` with models, serializers, views and tests
- `ai_prompts/initial_prompts.md` with example AI prompts (for assignment proof)

Frontend decision: React (Vite) scaffold added in `frontend/`.

Frontend quick start (requires Node.js and npm/yarn):

```powershell
# from project root
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port `5173` by default and will call the Django API at `http://127.0.0.1:8000/api/...`. Django is configured for development CORS to allow requests from the frontend dev server.

Next steps (recommendations):
- Choose frontend option (Django templates or React + DRF). Say "Django" or "React".
- I can extend recommendation logic to use a simple ML model or persisted user profiles.
