import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import numpy as np
import joblib
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score


# --- Email notification function ---
EMAIL_ADDRESS = "batterydetect.org@gmail.com"  # <-- Replace with your Gmail address
EMAIL_PASSWORD = "adjw jgsw egae wtne"    # <-- Replace with your Gmail app password

def send_email(to_email, subject, message):
    try:
        html_content = f'''
<html>
<head>
<style>
/* Mobile responsive */
@media only screen and (max-width: 600px) {{
    .container {{
        width: 100% !important;
        padding: 10px !important;
    }}
    .btn {{
        width: 100% !important;
    }}
}}
</style>
</head>

<body style="margin:0; padding:0; font-family: 'Segoe UI', Arial, sans-serif; background-color:#f4f6f9;">

<div class="container" style="max-width:600px; margin:30px auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 15px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background: linear-gradient(135deg, #2d7be5, #00c6ff); padding:25px; text-align:center; color:white;">
        <h1 style="margin:0; font-size:24px;">🔋 Battery Fault Detection</h1>
        <p style="margin:5px 0 0; font-size:14px;">AI Powered Monitoring System</p>
    </div>

    <!-- Body -->
    <div style="padding:25px;">
        <p style="font-size:16px;">Dear user,</p>

        <p style="font-size:16px; line-height:1.6; color:#444;">
            {message}
        </p>

        <!-- Highlight Box -->
        <div style="background:#f1f7ff; border-left:4px solid #2d7be5; padding:15px; margin:20px 0; border-radius:6px;">
            <b>🚀 Upgrade Your Monitoring Experience!</b><br>
            Get real-time alerts, predictive insights, and enhanced system safety.
        </div>

        <!-- CTA Button -->
        <div style="text-align:center; margin:25px 0;">
            <a href="#" class="btn"
               style="background: linear-gradient(135deg, #2d7be5, #00c6ff);
                      color:white;
                      padding:12px 25px;
                      text-decoration:none;
                      border-radius:25px;
                      font-size:15px;
                      display:inline-block;
                      transition:0.3s;">
                View Dashboard
            </a>
        </div>

        <hr style="border:none; border-top:1px solid #eee; margin:25px 0;">

        <!-- Footer -->
        <p style="font-size:13px; color:#666; text-align:center;">
            Empowering safe and reliable battery systems with AI-driven insights.
        </p>

        <!-- Social / Contact -->
        <div style="text-align:center; margin-top:15px;">
            <p style="font-size:13px; color:#888;">
                📧 batterydetect.org@gmail.com <br>
                📞 +91-XXXXXXXXXX
            </p>
        </div>

    </div>

    <!-- Bottom Strip -->
    <div style="background:#f1f1f1; text-align:center; padding:12px; font-size:12px; color:#777;">
        © 2026 Battery System Fault Detection | All Rights Reserved
    </div>

</div>

</body>
</html>
        '''
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print('Email error:', e)
        return False
    


# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = r"C:\Users\Saipriya\Downloads\Battery system fault detection a data driven aggregation and augmentation strategy\battery_fault_binary_30000_rows.csv"

DB_PATH = os.path.join(BASE_DIR, "users.db")

MODELS_DIR = os.path.join(BASE_DIR, "models")

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Create folders if they don't exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "secret_climate_key"

ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "Admin"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT, phone TEXT)"
    )
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

X_train = X_test = y_train = y_test = None
model_accuracies = {}
best_model_name = None

# ---------------- DECORATORS ----------------
from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*a, **k)
    return wrap

def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrap

# ---------------- HOME ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- ADMIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_home"))

    return render_template("admin_login.html")

@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/admin_home")
@admin_required
def admin_home():
    return render_template("admin_home.html")

# ---------------- DATASET UPLOAD ----------------

import os

UPLOAD_FOLDER = "uploads"
MODELS_DIR = "models"

# 👉 ADD IT HERE
DATA_PATH = os.path.join(UPLOAD_FOLDER, "dataset.csv")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/upload_dataset", methods=["GET", "POST"])
@admin_required
def upload_dataset():

    message = None
    table = None

    if request.method == "POST":

        file = request.files.get("dataset")

        if file and file.filename.endswith(".csv"):

            save_path = DATA_PATH
            file.save(save_path)

            message = "Dataset uploaded successfully!"

            df = pd.read_csv(save_path)
            table = df.head().to_html(
                classes="table table-striped table-bordered", index=False
            )

        else:
            message = "Please upload a valid CSV file."

    return render_template("upload_dataset.html", message=message, table=table)

# ---------------- PREPROCESS ----------------
@app.route("/preprocess")
@admin_required
def preprocess():

    if not os.path.exists(DATA_PATH):
        return redirect(url_for("upload_dataset"))

    df = pd.read_csv(DATA_PATH)

    total_rows_before = len(df)
    missing_before = df.isnull().sum().sum()
    duplicates_before = df.duplicated().sum()

    df = df.fillna(df.median(numeric_only=True))
    df = df.drop_duplicates()

    total_rows_after = len(df)
    missing_after = df.isnull().sum().sum()
    duplicates_after = df.duplicated().sum()

    # -------- FEATURES & TARGET --------
    X = df.drop(["fault"], axis=1)
    y = df["fault"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler.pkl"))
    joblib.dump((X_scaled, y.values), os.path.join(MODELS_DIR, "preprocessed.pkl"))

    return render_template(
        "preprocess.html",
        total_rows_before=total_rows_before,
        missing_before=missing_before,
        duplicates_before=duplicates_before,
        total_rows_after=total_rows_after,
        missing_after=missing_after,
        duplicates_after=duplicates_after,
        message="Battery dataset preprocessing completed successfully",
    )

# ---------------- SPLIT DATASET ----------------
@app.route("/split_dataset")
@admin_required
def split_dataset():

    pp = os.path.join(MODELS_DIR, "preprocessed.pkl")

    if not os.path.exists(pp):
        return redirect(url_for("preprocess"))

    Xs, y = joblib.load(pp)

    total_rows = len(Xs)

    Xtr, Xte, ytr, yte = train_test_split(
        Xs, y, test_size=0.2, random_state=42, shuffle=True
    )

    joblib.dump((Xtr, Xte, ytr, yte), os.path.join(MODELS_DIR, "split.pkl"))

    return render_template(
        "split_dataset.html",
        total_rows=total_rows,
        train_rows=len(Xtr),
        test_rows=len(Xte),
        split_ratio="80% Train / 20% Test",
        message="Dataset split successfully",
    )

# ---------------- TRAIN MODELS ----------------
@app.route("/train_models")
@admin_required
def train_models():

    global model_accuracies, best_model_name

    split_path = os.path.join(MODELS_DIR, "split.pkl")

    if not os.path.exists(split_path):
        return redirect(url_for("split_dataset"))

    Xtr, Xte, ytr, yte = joblib.load(split_path)

    models = {
        "Logistic Regression": LogisticRegression(),
        "Random Forest": RandomForestClassifier(),
        "Gradient Boosting": GradientBoostingClassifier(),
        "SVM": SVC(),
        "KNN": KNeighborsClassifier(),
    }

    model_accuracies = {}

    for name, model in models.items():

        model.fit(Xtr, ytr)

        preds = model.predict(Xte)

        acc = accuracy_score(yte, preds) * 100

        model_accuracies[name] = round(acc, 2)

    best_model_name = max(model_accuracies, key=model_accuracies.get)

    best_model = models[best_model_name]

    joblib.dump(best_model, os.path.join(MODELS_DIR, "best_model.pkl"))

    # -------- PLOTS --------
    names = list(model_accuracies.keys())
    scores = list(model_accuracies.values())

    plt.figure(figsize=(7, 4))
    plt.bar(names, scores)
    plt.ylabel("Accuracy (%)")
    plt.xticks(rotation=30)
    plt.title("Model Performance Comparison")
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "accuracy_comparison.png"))
    plt.close()

    plt.figure(figsize=(6, 6))
    plt.pie(scores, labels=names, autopct="%1.1f%%", startangle=140)
    plt.title("Accuracy Distribution")
    plt.savefig(os.path.join(STATIC_DIR, "pie_accuracy.png"))
    plt.close()

    plt.figure(figsize=(7, 4))
    plt.plot(names, scores, marker="o")
    plt.ylabel("Accuracy (%)")
    plt.xticks(rotation=30)
    plt.grid(True)
    plt.title("Model Performance Trend")
    plt.tight_layout()
    plt.savefig(os.path.join(STATIC_DIR, "line_accuracy.png"))
    plt.close()

    return render_template(
        "train_models.html", accuracies=model_accuracies, best_model=best_model_name
    )

# ---------------- COMPARE MODELS ----------------
@app.route("/compare_models")
@admin_required
def compare_models():

    if not model_accuracies:
        return redirect(url_for("train_models"))

    return render_template(
        "compare_models.html",
        accuracies=model_accuracies,
        acc_image="accuracy_comparison.png",
        pie_image="pie_accuracy.png",
        line_image="line_accuracy.png",
    )


@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        n=request.form.get("name")
        e=request.form.get("email")
        p=request.form.get("password")
        phone=request.form.get("phone")
        conn=get_db()
        try:
            conn.execute("INSERT INTO users(name,email,password,phone) VALUES(?,?,?,?)",(n,e,p,phone))
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        e=request.form.get("email");p=request.form.get("password")
        conn=get_db()
        u=conn.execute("SELECT * FROM users WHERE email=? AND password=?",(e,p)).fetchone()
        conn.close()
        if u:
            session["user_id"]=u["id"];session["user_name"]=u["name"];session["email"]=u["email"]
            return redirect(url_for("user_home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear();return redirect(url_for("index"))

# --------- user pages ----------
@app.route("/user_home")
@login_required
def user_home():
    return render_template("user_home.html",name=session.get("user_name"))

@app.route("/profile")
@login_required
def profile():
    uid=session.get("user_id")
    conn=get_db();u=conn.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone();conn.close()
    return render_template("profile.html",user=u)

@app.route("/delete_account",methods=["POST"])
@login_required
def delete_account():
    uid=session.get("user_id")
    conn=get_db();conn.execute("DELETE FROM users WHERE id=?",(uid,));conn.commit();conn.close()
    session.clear()
    return redirect(url_for("index"))


# ---------------- MANAGE USERS ----------------
@app.route("/manage_users")
@admin_required
def manage_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("manage_users.html", users=rows)


# ---------------- DELETE USER ----------------
@app.route("/delete_user/<int:uid>")
@admin_required
def delete_user(uid):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return redirect(url_for("manage_users"))


# ---------------- PREDICTION ----------------
@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():

    scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
    model_path = os.path.join(MODELS_DIR, "best_model.pkl")

    prediction = None
    explanation = None

    if os.path.exists(scaler_path) and os.path.exists(model_path):
        scaler = joblib.load(scaler_path)
        model = joblib.load(model_path)

        if request.method == "POST":
            try:
                values = [
                    float(request.form.get("voltage_V")),
                    float(request.form.get("current_A")),
                    float(request.form.get("temperature_C")),
                    float(request.form.get("soc_percent")),
                    float(request.form.get("soh_percent")),
                    float(request.form.get("internal_resistance_mOhm")),
                    float(request.form.get("charge_cycles")),
                    float(request.form.get("ambient_temp_C"))
                ]
                X = np.array([values])
                X_scaled = scaler.transform(X)
                result = model.predict(X_scaled)[0]

                if result == 1:
                    prediction = "Battery Fault Detected"
                    explanation = "Please check the battery immediately!"
                else:
                    prediction = "Battery Status Normal"
                    explanation = "The battery is functioning within normal parameters."

                # --- Email Notification (replaces SMS/WhatsApp) ---
                uid = session.get("user_id")
                conn = get_db()
                user = conn.execute("SELECT email FROM users WHERE id=?", (uid,)).fetchone()
                conn.close()
                if user and user["email"]:
                    email_subject = "Battery System Fault Detection - Prediction Result"
                    email_message = f"<b>Prediction:</b> {prediction}<br><b>Details:</b> {explanation}"
                    send_email(user["email"], email_subject, email_message)
            except Exception as ex:
                prediction = "Invalid input values"

    return render_template(
        "predict.html",
        prediction=prediction,
        explanation=explanation
    )

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)