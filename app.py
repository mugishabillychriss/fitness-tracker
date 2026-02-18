import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from psycopg2.extras import RealDictCursor
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# ------------------ Register ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        age = request.form.get("age")
        height = request.form.get("height")
        weight = request.form.get("weight")
        activity_level = request.form.get("activity_level")

        conn = get_db()
        if not conn:
            flash("Database connection failed!", "danger")
            return redirect(url_for("register"))

        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO users (name,email,password,age,height,weight,activity_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (name,email,password,age,height,weight,activity_level))
            conn.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            print("Register error:", e)
            flash("Email exists or invalid data!", "danger")
            conn.rollback()
        finally:
            cur.close()
            conn.close()
    return render_template("register.html")

# ------------------ Login ------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        if not conn:
            flash("Database connection failed!", "danger")
            return redirect(url_for("login"))

        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"],password):
            session["user_id"] = user["id"]
            flash(f"Welcome {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

# ------------------ Dashboard ------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM weight_logs WHERE user_id=%s ORDER BY date ASC", (session["user_id"],))
    weights = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("dashboard.html", weights=weights)

# ------------------ Logout ------------------
@app.route("/logout")
def logout():
    session.pop("user_id",None)
    flash("Logged out successfully","success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
