# NEXUS — Local Development

Run the Flask backend and open the admin UI to manage site content.

Prereqs
- Python 3.8+

Setup (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\app.py
```

Visit:
- http://localhost:5000/ (site)
- http://localhost:5000/admin (admin UI)

Notes
- Uploaded images are saved to `uploads/` and served at `/uploads/<filename>`.
- Data is persisted to `data/data.json` and messages to `data/messages.json`.
- This is a simple dev setup. For production, add authentication, HTTPS, and a proper database.
