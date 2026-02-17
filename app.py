import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ---------------- FITNESS LOGIC ----------------

def calculate_bmi(weight, height):
    return round(weight / ((height / 100) ** 2), 2)

def calorie_target(weight, height, age, activity_level):
    bmr = 10 * weight + 6.25 * height - 5 * age + 5
    activity_multipliers = {
        "low": 1.2,
        "medium": 1.55,
        "high": 1.9
    }
    return int(bmr * activity_multipliers.get(activity_level, 1.2))

# ---------------- UI ----------------

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>FitTrack Pro</title>
<style>
body{
margin:0;
font-family:Arial;
background:linear-gradient(135deg,#667eea,#764ba2);
display:flex;
justify-content:center;
align-items:center;
height:100vh;
}
.card{
background:white;
padding:30px;
width:380px;
border-radius:15px;
box-shadow:0 15px 40px rgba(0,0,0,0.3);
}
h2{text-align:center;}
input,select{
width:100%;
padding:10px;
margin:6px 0;
border-radius:8px;
border:1px solid #ddd;
}
button{
width:100%;
padding:10px;
border:none;
border-radius:8px;
background:#667eea;
color:white;
font-weight:bold;
cursor:pointer;
}
button:hover{background:#5a67d8;}
hr{margin:15px 0;}
.small{text-align:center;font-size:12px;color:#777;}
</style>
</head>
<body>
<div class="card">
<h2>FitTrack Pro</h2>

<h4>Create Account</h4>
<input id="name" placeholder="Name">
<input id="email" placeholder="Email">
<input id="password" type="password" placeholder="Password">
<input id="age" placeholder="Age">
<input id="height" placeholder="Height (cm)">
<input id="weight" placeholder="Weight (kg)">
<select id="activity">
<option value="low">Low Activity</option>
<option value="medium">Medium Activity</option>
<option value="high">High Activity</option>
</select>
<button onclick="register()">Register</button>

<hr>

<h4>Login</h4>
<input id="login_email" placeholder="Email">
<input id="login_password" type="password" placeholder="Password">
<button onclick="login()">Login</button>

<div class="small">Track. Improve. Transform.</div>
</div>

<script>
function register(){
fetch("/register",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
name:name.value,
email:email.value,
password:password.value,
age:age.value,
height:height.value,
weight:weight.value,
activity:activity.value
})
}).then(r=>r.json()).then(d=>alert(d.message));
}

function login(){
fetch("/login",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
email:login_email.value,
password:login_password.value
})
}).then(r=>r.json()).then(d=>{
localStorage.setItem("token",d.token);
window.location="/dashboard";
});
}
</script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{
margin:0;
font-family:Arial;
background:#f4f6f9;
padding:30px;
}
.container{
max-width:700px;
margin:auto;
background:white;
padding:30px;
border-radius:15px;
box-shadow:0 10px 30px rgba(0,0,0,0.1);
}
h2{text-align:center;}
.stat{
background:#667eea;
color:white;
padding:15px;
border-radius:10px;
margin:10px 0;
}
input{
width:100%;
padding:10px;
margin:10px 0;
border-radius:8px;
border:1px solid #ddd;
}
button{
width:100%;
padding:10px;
border:none;
border-radius:8px;
background:#28a745;
color:white;
font-weight:bold;
cursor:pointer;
margin-top:5px;
}
button:hover{background:#218838;}
.logout{
background:#dc3545;
}
.logout:hover{background:#c82333;}
canvas{margin-top:20px;}
</style>
</head>
<body>
<div class="container">
<h2>Your Dashboard</h2>
<div id="profile"></div>

<h4>Log New Weight</h4>
<input id="new_weight" placeholder="Enter new weight">
<button onclick="logWeight()">Save Weight</button>

<canvas id="chart"></canvas>

<button class="logout" onclick="logout()">Logout</button>
</div>

<script>
let chart;

function loadProfile(){
fetch("/profile",{
headers:{"Authorization":"Bearer "+localStorage.getItem("token")}
}).then(r=>r.json()).then(d=>{
profile.innerHTML=
"<div class='stat'>Name: "+d.name+"</div>"+
"<div class='stat'>BMI: "+d.bmi+"</div>"+
"<div class='stat'>Daily Calories: "+d.calories+"</div>";
});
}

function logWeight(){
fetch("/log-weight",{
method:"POST",
headers:{
"Content-Type":"application/json",
"Authorization":"Bearer "+localStorage.getItem("token")
},
body:JSON.stringify({weight:new_weight.value})
}).then(()=>loadProgress());
}

function loadProgress(){
fetch("/progress",{
headers:{"Authorization":"Bearer "+localStorage.getItem("token")}
}).then(r=>r.json()).then(d=>{
const labels=d.map(x=>new Date(x.date).toLocaleDateString());
const weights=d.map(x=>x.weight);

if(chart){chart.destroy();}
const ctx=document.getElementById("chart").getContext("2d");
chart=new Chart(ctx,{
type:"line",
data:{
labels:labels,
datasets:[{
label:"Weight Progress",
data:weights,
borderColor:"#667eea",
fill:false,
tension:0.3
}]
}
});
});
}

function logout(){
localStorage.removeItem("token");
window.location="/";
}

loadProfile();
loadProgress();
</script>
</body>
</html>
"""

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template_string(INDEX_HTML)

@app.route("/dashboard")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (name,email,password,age,height,weight,activity_level)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """,(data["name"],data["email"],hashed_pw,data["age"],
         data["height"],data["weight"],data["activity"]))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message":"Account created"})

@app.route("/login", methods=["POST"])
def login():
    data=request.json
    conn=get_db()
    cur=conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s",(data["email"],))
    user=cur.fetchone()
    cur.close()
    conn.close()
    if user and bcrypt.check_password_hash(user["password"],data["password"]):
        token=create_access_token(identity=user["id"],expires_delta=timedelta(days=1))
        return jsonify({"token":token})
    return jsonify({"error":"Invalid credentials"}),401

@app.route("/profile")
@jwt_required()
def profile():
    user_id=get_jwt_identity()
    conn=get_db()
    cur=conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s",(user_id,))
    user=cur.fetchone()
    cur.close()
    conn.close()
    bmi=calculate_bmi(user["weight"],user["height"])
    calories=calorie_target(user["weight"],user["height"],
                            user["age"],user["activity_level"])
    return jsonify({
        "name":user["name"],
        "bmi":bmi,
        "calories":calories
    })

@app.route("/log-weight",methods=["POST"])
@jwt_required()
def log_weight():
    user_id=get_jwt_identity()
    data=request.json
    conn=get_db()
    cur=conn.cursor()
    cur.execute("""
        INSERT INTO weight_logs (user_id,weight,date)
        VALUES (%s,%s,%s)
    """,(user_id,data["weight"],datetime.now()))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message":"Logged"})

@app.route("/progress")
@jwt_required()
def progress():
    user_id=get_jwt_identity()
    conn=get_db()
    cur=conn.cursor()
    cur.execute("""
        SELECT weight,date FROM weight_logs
        WHERE user_id=%s
        ORDER BY date ASC
    """,(user_id,))
    logs=cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(logs)

if __name__=="__main__":
    app.run()
