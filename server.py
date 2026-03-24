from flask import Flask, request, redirect
import sqlite3
import hashlib
import secrets

app = Flask(__name__)

DB = "pagebook.db"

# ---------- DB ----------
def get_db():
    return sqlite3.connect(DB, timeout=10, check_same_thread=False)


def init_db():
    with get_db() as db:
        c = db.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            password TEXT,
            approved INTEGER DEFAULT 0,
            activation_key TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id INTEGER,
            author TEXT,
            message TEXT
        )
        """)


# ---------- UTIL ----------
def sanitize(text):
    return text.replace("<", "").replace(">", "")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_key():
    return secrets.token_hex(16)


# ---------- USERS ----------
def create_user(url, password):
    key = generate_key()

    with get_db() as db:
        c = db.cursor()
        c.execute(
            "INSERT INTO users (url, password, approved, activation_key) VALUES (?, ?, 0, ?)",
            (url, hash_password(password), key)
        )
        user_id = c.lastrowid

    link = f"http://127.0.0.1:5000/activate/{user_id}/{key}"

    with open("approve.txt", "a") as f:
        f.write(f"{url}|||{link}\n")


def check_user(url, password):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT password, approved FROM users WHERE url=?", (url,))
        row = c.fetchone()

    if row:
        if row[0] != hash_password(password):
            return "wrong_pass"
        if row[1] == 0:
            return "not_approved"
        return "ok"

    return "not_exist"


def get_user_by_url(url):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT id FROM users WHERE url=?", (url,))
        row = c.fetchone()
        return row[0] if row else None


def get_all_users():
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT id, url FROM users WHERE approved=1")
        return c.fetchall()


# ---------- POSTS ----------
def save_post(page_id, author, message):
    with get_db() as db:
        c = db.cursor()
        c.execute(
            "INSERT INTO posts (page_id, author, message) VALUES (?, ?, ?)",
            (page_id, author, message)
        )


def load_posts(page_id, page, per_page=5):
    offset = (page - 1) * per_page

    with get_db() as db:
        c = db.cursor()
        c.execute(
            "SELECT author, message FROM posts WHERE page_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (page_id, per_page, offset)
        )
        return c.fetchall()


def count_posts(page_id):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM posts WHERE page_id=?", (page_id,))
        return c.fetchone()[0]


# ---------- ROUTES ----------

# 🏠 HOME (lista utilizadores)
@app.route("/")
def home():
    users = get_all_users()

    html = """
    <body style="background:black;color:white;font-family:Arial;">
    <h1>PageBook</h1>
    <a href="/register">➕ Registar</a>
    <h2>Utilizadores</h2>
    """

    for uid, url in users:
        html += f'<a href="/user/{uid}">{url}</a><br>'

    html += "</body>"
    return html


# 📝 REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""

    if request.method == "POST":
        url = sanitize(request.form.get("url", ""))
        password = request.form.get("password", "")

        if url and password:
            try:
                create_user(url, password)
                msg = "Registado! Aguarda aprovação."
            except:
                msg = "Já existe"

    return f"""
    <body style="background:black;color:white;">
    <a href="/">⬅</a>
    <h2>Registar</h2>
    <form method="POST">
        <input name="url"><br>
        <input type="password" name="password"><br>
        <button>Registar</button>
    </form>
    <p>{msg}</p>
    </body>
    """


# 🔗 ACTIVATE
@app.route("/activate/<int:user_id>/<key>")
def activate(user_id, key):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT activation_key FROM users WHERE id=?", (user_id,))
        row = c.fetchone()

        if row and row[0] == key:
            c.execute("UPDATE users SET approved=1 WHERE id=?", (user_id,))
            db.commit()
            return "Conta ativada!"

    return "Link inválido"


# 👤 USER PAGE
@app.route("/user/<int:page_id>", methods=["GET", "POST"])
def user_page(page_id):
    page = request.args.get("page", 1, type=int)
    error = ""

    if request.method == "POST":
        url = sanitize(request.form.get("url", ""))
        msg = sanitize(request.form.get("message", ""))
        password = request.form.get("password", "")

        if url and msg and password:
            res = check_user(url, password)

            if res == "ok":
                save_post(page_id, url, msg)
                return redirect(f"/user/{page_id}?page={page}")
            elif res == "wrong_pass":
                error = "Password errada"
            elif res == "not_approved":
                error = "Conta não ativada"
            else:
                error = "User não existe"

    posts = load_posts(page_id, page)
    total = count_posts(page_id)
    total_pages = (total + 4) // 5 if total else 1

    html = f"""
    <body style="background:black;color:white;">
    <a href="/">⬅ Voltar</a>

    <h2>Página do utilizador #{page_id}</h2>

    <form method="POST">
        <input name="url" placeholder="Teu URL"><br>
        <input type="password" name="password"><br>
        <textarea name="message"></textarea><br>
        <button>Postar</button>
    </form>

    <p>{error}</p>
    <hr>
    """

    for author, msg in posts:
        html += f"<b>{author}</b><br><p>{msg}</p><hr>"

    html += f"Página {page}/{total_pages}<br>"

    if page > 1:
        html += f'<a href="/user/{page_id}?page={page-1}">⬅</a> '
    if page < total_pages:
        html += f'<a href="/user/{page_id}?page={page+1}">➡</a>'

    html += "</body>"
    return html


# ---------- START ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)
