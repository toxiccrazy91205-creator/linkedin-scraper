# LinkedIn Scraper Web App

A production-ready Flask web application for scraping LinkedIn profiles, job postings, company information, and searching for people — all through a polished, modern web interface.

**Free alternative** to Proxycurl ($50/mo), PhantomBuster ($69/mo), and Snov.io ($39/mo).

---

## Features

| Feature | Login Required | Description |
|---------|:--------------:|-------------|
| **Job Search** | No | Search job postings with filters — location, remote/onsite/hybrid, job type, experience level |
| **Company Lookup** | No | Get company data — industry, size, headquarters, website, specialties |
| **Profile Lookup** | Partial | Name, headline, location without login · Full profile with login |
| **People Search** | Yes | Search professionals by keywords, company, title, location |
| **Export** | No | Download results as JSON or CSV |

### UI Features

- 🌗 **Dark/Light theme** — toggle with persistence
- 📱 **Fully responsive** — works on desktop, tablet, and mobile
- ⚡ **Loading skeletons** — smooth loading experience
- 🔔 **Toast notifications** — real-time feedback for every action
- 📊 **Export buttons** — JSON and CSV download on all result panels
- 🎨 **Premium design** — glassmorphism, gradients, micro-animations

---

## Quick Start

### Prerequisites

- Python 3.11+ ([download](https://python.org))
- pip (comes with Python)

### 1. Clone & Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd linkedin-web

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your settings (optional — defaults work for local dev)
```

### 3. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## How It Works

### Authentication Flow

LinkedIn aggressively blocks automated scraping. This tool uses a **session-based approach**:

1. Click **"Launch LinkedIn Login"** in the Session tab
2. A **real browser window** opens on your machine
3. Log in to LinkedIn with your credentials manually
4. Close the browser — session cookies are saved to `.sessions/linkedin.json`
5. All subsequent scraping runs headlessly using those cookies
6. Session typically lasts **days to weeks** before re-login is needed

> **Your credentials are never stored** — only the session cookies, which are gitignored.

### What Works Without Login

| Feature | Without Login | With Login |
|---------|:------------:|:----------:|
| Job Search | ✅ Full | ✅ Full |
| Company Pages | ✅ Full | ✅ Full |
| Profiles | ⚠️ Partial | ✅ Full |
| People Search | ❌ No | ✅ Full |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web interface |
| `GET` | `/api/status` | Server health + session status |
| `POST` | `/api/login` | Trigger LinkedIn login flow |
| `POST` | `/api/profile` | Fetch a LinkedIn profile |
| `POST` | `/api/search/people` | Search for people |
| `POST` | `/api/search/jobs` | Search for jobs |
| `POST` | `/api/company` | Fetch company data |
| `POST` | `/api/export` | Export results as CSV/JSON |

### Example: Search Jobs

```bash
curl -X POST http://localhost:5000/api/search/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "python developer", "location": "San Francisco", "remote": "remote"}'
```

### Example: Get Profile

```bash
curl -X POST http://localhost:5000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"username": "johndoe"}'
```

### Example: Get Company

```bash
curl -X POST http://localhost:5000/api/company \
  -H "Content-Type: application/json" \
  -d '{"company_slug": "google"}'
```

---

## Deployment

### Render

1. Push your code to GitHub
2. Connect repo to [Render](https://render.com)
3. Render will auto-detect the `render.yaml` configuration
4. Deploy — Playwright + Chromium are installed during build

### Heroku

```bash
heroku create your-app-name
heroku buildpacks:add heroku/python
git push heroku main
```

### Railway

1. Push to GitHub
2. Create new project on [Railway](https://railway.app)
3. Connect your repo — Railway auto-detects `railway.toml`

### Docker

```bash
docker build -t linkedin-scraper .
docker run -p 5000:5000 linkedin-scraper
```

> **Note**: The interactive login flow (opening a headed browser) only works locally — not on cloud deployments. Log in locally first, then deploy with the saved session.

---

## Project Structure

```
linkedin-web/
├── app.py                  # Flask application + API routes
├── scraper.py              # LinkedIn scraper (Playwright-based)
├── models.py               # Profile, Job, Company, SearchResult dataclasses
├── stealth_browser.py      # Stealth browser manager with session persistence
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── Procfile                # Heroku deployment
├── render.yaml             # Render deployment
├── railway.toml            # Railway deployment
├── Dockerfile              # Docker container
├── static/
│   ├── css/style.css       # Complete design system (dark/light themes)
│   ├── js/app.js           # Frontend logic (tabs, API, rendering, export)
│   └── favicon.svg         # LinkedIn-themed favicon
└── templates/
    └── index.html          # Single-page application template
```

---

## Use Cases

- **Recruiting** — Search candidates by skills, location, company
- **Sales Prospecting** — Find decision-makers at target companies
- **Job Hunting** — Monitor job postings with specific filters
- **Competitive Intelligence** — Track competitor company pages
- **Market Research** — Analyze hiring trends and company growth

---

## Rate Limits

LinkedIn is aggressive with bot detection:
- ~50 pages/hour before soft blocks
- Hard blocks show CAPTCHA or "unusual activity" page
- Session cookies from manual login bypass most checks
- Random delays between requests are built-in

---

## License

MIT

---

## Credits

Based on the [BlackHole](https://github.com/dppalukuri/BlackHole) LinkedIn MCP server by [@dppalukuri](https://github.com/dppalukuri).
