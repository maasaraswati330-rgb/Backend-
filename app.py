import sqlite3
import hashlib
import uuid
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()
DB_FILE = "earnsry.db"
SERVE_URL = "https://backend-f6zj.onrender.com"
NETLIFY_URL = "https://captchae.site"

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UrlShorten(BaseModel):
    url: str
    user_uid: str

class Link(BaseModel):
    slug: str
    original_url: str
    views: int
    created_at: int

class UserStats(BaseModel):
    total_views: int
    total_earnings: float
    cpm_rate: float = 4.00
    referrals: int = 0
    links: List[Link]

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", NETLIFY_URL, SERVE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database functions
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            user_uid TEXT NOT NULL,
            views INTEGER DEFAULT 0,
            created_at INTEGER,
            FOREIGN KEY (user_uid) REFERENCES users (uid)
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    create_database()

def hash_password(password: str):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_slug():
    return uuid.uuid4().hex[:7]

# API Endpoints
@app.post("/register_user_data")
async def register_user_data(user: UserRegister):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (user.username, user.email))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            if existing_user['username'] == user.username:
                return JSONResponse(content={"success": False, "message": "Username already taken."})
            if existing_user['email'] == user.email:
                return JSONResponse(content={"success": False, "message": "Email already in use."})
        uid = str(uuid.uuid4())
        password_hash = hash_password(user.password)
        created_at = int(time.time())
        cursor.execute("INSERT INTO users (uid, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                       (uid, user.username, user.email, password_hash, created_at))
        conn.commit()
        conn.close()
        return JSONResponse(content={"success": True, "message": "Registration successful!"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": "An unexpected error occurred."})

@app.post("/login_user_data")
async def login_user_data(user: UserLogin):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
        found_user = cursor.fetchone()
        conn.close()
        if not found_user or found_user['password_hash'] != hash_password(user.password):
            return JSONResponse(content={"success": False, "message": "Invalid username or password."})
        return JSONResponse(content={
            "success": True,
            "message": "Login successful!",
            "username": found_user['username'],
            "uid": found_user['uid']
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": "An unexpected error occurred."})

@app.post("/shorten_url")
async def shorten_url(link: UrlShorten):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT slug FROM urls WHERE original_url = ? AND user_uid = ?", (link.url, link.user_uid))
        existing_slug = cursor.fetchone()
        if existing_slug:
            conn.close()
            return JSONResponse(content={"success": True, "slug": existing_slug['slug'], "message": "URL already shortened."})
        slug = generate_slug()
        cursor.execute("INSERT INTO urls (slug, original_url, user_uid, views, created_at) VALUES (?, ?, ?, 0, ?)",
                       (slug, link.url, link.user_uid, int(time.time())))
        conn.commit()
        conn.close()
        return JSONResponse(content={"success": True, "slug": slug})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": "URL shortening failed."})

# URL Flow Handlers - FIXED VERSION
@app.get("/{slug}")
async def serve_ad_page_1(slug: str, request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_url FROM urls WHERE slug = ?", (slug,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="Slug not found.")

    conn.close()

    base_url = str(request.base_url).rstrip('/')

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Please wait...</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            margin: 0;
            overflow-x: hidden;
        }}
        #ad-frame {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            z-index: 1000;
        }}
    </style>
</head>
<body class="bg-gray-50 flex items-center justify-center min-h-screen">
    <div class="bg-white p-8 rounded-lg shadow-xl text-center max-w-sm">
        <h1 class="text-2xl font-bold mb-4">Your link is almost ready!</h1>
        <p class="text-gray-600 mb-6">Please wait for <span id="countdown" class="font-bold text-red-500">5</span> seconds.</p>

        <div class="bg-gray-200 p-4 rounded-md mb-6">
            <p class="text-gray-500">This is a placeholder for your ads.</p>
        </div>

        <button id="get-link-btn" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg opacity-50 cursor-not-allowed" disabled>
            Get Link
        </button>
    </div>

    <script>
        let countdown = 5;
        const countdownEl = document.getElementById('countdown');
        const getLinkBtn = document.getElementById('get-link-btn');
        const baseUrl = "{base_url}";

        // Add message listener for iframe communication
        window.addEventListener('message', function(event) {{
            if (event.data.action === 'redirect') {{
                window.location.href = `${{baseUrl}}/go_to_original/${{event.data.slug}}`;
            }}
        }});

        const timer = setInterval(() => {{
            countdown--;
            countdownEl.textContent = countdown;
            if (countdown <= 0) {{
                clearInterval(timer);
                getLinkBtn.disabled = false;
                getLinkBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                getLinkBtn.classList.add('hover:bg-blue-700');
                getLinkBtn.textContent = 'Get Link';
            }}
        }}, 1000);

        getLinkBtn.addEventListener('click', () => {{
            // Create fullscreen iframe to load second ad page
            const iframe = document.createElement('iframe');
            iframe.id = 'ad-frame';
            iframe.src = `${{baseUrl}}/ad_page2_content/{slug}`;
            document.body.innerHTML = '';
            document.body.appendChild(iframe);
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

@app.get("/ad_page2_content/{slug}")
async def serve_ad_page_2_content(slug: str):
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Final Step!</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 flex items-center justify-center min-h-screen">
    <div class="bg-white p-8 rounded-lg shadow-xl text-center max-w-sm">
        <h1 class="text-2xl font-bold mb-4">You are almost there!</h1>
        <p class="text-gray-600 mb-6">Please wait another <span id="countdown_2" class="font-bold text-red-500">5</span> seconds.</p>

        <div class="bg-gray-200 p-4 rounded-md mb-6">
            <p class="text-gray-500">This is a placeholder for your second ad.</p>
        </div>

        <button id="get-final-link-btn" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg opacity-50 cursor-not-allowed" disabled>
            Get Final Link
        </button>
    </div>

    <script>
        const slug = "{slug}";
        let countdown_2 = 5;
        const countdownEl_2 = document.getElementById('countdown_2');
        const getFinalLinkBtn = document.getElementById('get-final-link-btn');

        const timer_2 = setInterval(() => {{
            countdown_2--;
            countdownEl_2.textContent = countdown_2;
            if (countdown_2 <= 0) {{
                clearInterval(timer_2);
                getFinalLinkBtn.disabled = false;
                getFinalLinkBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                getFinalLinkBtn.classList.add('hover:bg-blue-700');
                getFinalLinkBtn.textContent = 'Get Final Link';
            }}
        }}, 1000);

        getFinalLinkBtn.addEventListener('click', () => {{
            // Tell parent window to redirect to final URL
            window.parent.postMessage({{
                action: 'redirect',
                slug: "{slug}"
            }}, '*');
        }});
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

@app.get("/go_to_original/{slug}")
async def get_final_link(slug: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_url FROM urls WHERE slug = ?", (slug,))
    result = cursor.fetchone()

    if result:
        original_url = result['original_url']
        cursor.execute("UPDATE urls SET views = views + 1 WHERE slug = ?", (slug,))
        conn.commit()
        conn.close()
        return RedirectResponse(url=original_url, status_code=302)
    else:
        conn.close()
        raise HTTPException(status_code=404, detail="Original URL not found.")

# User stats endpoint
@app.get("/api/user_stats")
async def get_user_stats(user_uid: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT SUM(views) AS total_views FROM urls WHERE user_uid = ?", (user_uid,))
        total_views = cursor.fetchone()['total_views'] or 0

        cpm = 4.00
        total_earnings = (total_views / 1000) * cpm

        cursor.execute("SELECT slug, original_url, views, created_at FROM urls WHERE user_uid = ? ORDER BY created_at DESC", (user_uid,))
        links = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return UserStats(
            total_views=total_views,
            total_earnings=round(total_earnings, 2),
            cpm_rate=cpm,
            referrals=0,
            links=links
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching user stats.")
