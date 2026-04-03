# code-test

`PulseDesk` is now a real local web app instead of a static demo.

## Features

- Local Python web server
- Persistent SQLite storage in `app.db`
- Task creation, status updates, filtering, and deletion
- Lead pipeline tracking with stage updates
- Server-side activity log
- Dashboard summary cards
- JSON export of app data
- Responsive UI with motion and layered visual styling

## Files

- `server.py`: API server and static file host
- `app.db`: SQLite database created automatically on first run
- `static/index.html`: dashboard layout
- `static/styles.css`: visual system and animations
- `static/app.js`: client-side state and API calls

## Run

```bash
cd /mnt/c/Users/abhig/code-test
python3 server.py
```

Open:

```text
http://127.0.0.1:8000
```

## API

- `GET /api/status`: full dashboard snapshot
- `POST /api/tasks`: create a task
- `PATCH /api/tasks/<id>`: update a task
- `DELETE /api/tasks/<id>`: delete a task
- `POST /api/leads`: create a lead
- `PATCH /api/leads/<id>`: update a lead
- `DELETE /api/leads/<id>`: delete a lead
- `GET /api/export`: export all current data as JSON

## GitHub

Changes appear in your GitHub repository only after you commit and push them:

```bash
git add .
git commit -m "Build PulseDesk app"
git push origin main
```
