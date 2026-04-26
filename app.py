# version 1.0 — MongoDB Atlas backend, Railway-ready
import os
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production-use-env-var")

# =========================
# MONGODB CONNECTION
# =========================
# Set these in Railway → your service → Variables:
#
#   MONGO_URI  = mongodb+srv://etadmin:<password>@<cluster>.mongodb.net/expenses_db?retryWrites=true&w=majority
#   SECRET_KEY = <random 32-char string>
#
# Copy your exact URI from: MongoDB Atlas → Connect → Drivers → Python

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/expenses_db")

client       = MongoClient(MONGO_URI)
db           = client["expenses_db"]
users_col    = db["users"]
income_col   = db["income"]
expenses_col = db["expenses"]


# =========================
# DB INIT — indexes
# =========================
def init_db():
    users_col.create_index("username", unique=True)
    income_col.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    expenses_col.create_index([("user_id", ASCENDING), ("date", DESCENDING)])


# =========================
# HELPERS
# =========================
def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d")


def month_range(year, month):
    """Return (start_datetime, end_datetime) for a given year/month."""
    start = datetime(int(year), int(month), 1)
    if int(month) == 12:
        end = datetime(int(year) + 1, 1, 1)
    else:
        end = datetime(int(year), int(month) + 1, 1)
    return start, end


def fmt_income(doc):
    return {
        "id":     str(doc["_id"]),
        "amount": doc["amount"],
        "date":   doc["date"].strftime("%Y-%m-%d"),
        "note":   doc.get("note", ""),
    }


def fmt_expense(doc):
    return {
        "id":       str(doc["_id"]),
        "amount":   doc["amount"],
        "category": doc.get("category", "other"),
        "date":     doc["date"].strftime("%Y-%m-%d"),
        "note":     doc.get("note", ""),
    }


# =========================
# AUTH DECORATOR
# =========================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return decorated


# =========================
# SERVE FRONTEND
# =========================
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# =========================
# AUTH ROUTES
# =========================
@app.route("/api/register", methods=["POST"])
def register():
    data            = request.json
    username        = data.get("username", "").strip()
    password        = data.get("password", "").strip()
    dob             = data.get("dob", "")
    note            = data.get("note", "")
    opening_balance = data.get("opening_balance", 0)
    start_date      = data.get("start_date", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    try:
        opening_balance = float(opening_balance)
        parse_date(dob)
        start_dt = parse_date(start_date)
    except Exception:
        return jsonify({"error": "Invalid data format"}), 400

    hashed = generate_password_hash(password)

    try:
        result = users_col.insert_one({
            "username": username,
            "password": hashed,
            "dob":      dob,
            "note":     note,
        })
        income_col.insert_one({
            "user_id": result.inserted_id,
            "amount":  opening_balance,
            "date":    start_dt,
            "note":    "OPENING BALANCE",
        })
        return jsonify({"message": "User created successfully"})

    except DuplicateKeyError:
        return jsonify({"error": "Username already exists"}), 409


@app.route("/api/login", methods=["POST"])
def login():
    data     = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    user = users_col.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        session["user_id"]  = str(user["_id"])
        session["username"] = username
        return jsonify({"message": "Logged in", "username": username})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
def me():
    if "user_id" in session:
        return jsonify({"logged_in": True, "username": session["username"]})
    return jsonify({"logged_in": False})


# =========================
# INCOME
# =========================
@app.route("/api/income", methods=["POST"])
@login_required
def add_income():
    data = request.json
    try:
        amt = float(data["amount"])
        if amt <= 0:
            raise ValueError
        dt = parse_date(data["date"])
    except Exception:
        return jsonify({"error": "Invalid data"}), 400

    income_col.insert_one({
        "user_id": ObjectId(session["user_id"]),
        "amount":  amt,
        "date":    dt,
        "note":    data.get("note", ""),
    })
    return jsonify({"message": "Income added"})


@app.route("/api/income")
@login_required
def get_income():
    year  = request.args.get("year")
    month = request.args.get("month")
    uid   = ObjectId(session["user_id"])
    query = {"user_id": uid}

    if year and month:
        start, end = month_range(year, month)
        query["date"] = {"$gte": start, "$lt": end}

    docs = income_col.find(query).sort("date", DESCENDING)
    return jsonify([fmt_income(d) for d in docs])


# =========================
# EXPENSES
# =========================
@app.route("/api/expenses", methods=["POST"])
@login_required
def add_expense():
    data = request.json
    try:
        amt = float(data["amount"])
        if amt <= 0:
            raise ValueError
        dt = parse_date(data["date"])
    except Exception:
        return jsonify({"error": "Invalid data"}), 400

    expenses_col.insert_one({
        "user_id":  ObjectId(session["user_id"]),
        "amount":   amt,
        "category": data.get("category", "other").lower(),
        "date":     dt,
        "note":     data.get("note", ""),
    })
    return jsonify({"message": "Expense added"})


@app.route("/api/expenses")
@login_required
def get_expenses():
    year  = request.args.get("year")
    month = request.args.get("month")
    uid   = ObjectId(session["user_id"])
    query = {"user_id": uid}

    if year and month:
        start, end = month_range(year, month)
        query["date"] = {"$gte": start, "$lt": end}

    sort_dir = ASCENDING if (year and month) else DESCENDING
    docs = expenses_col.find(query).sort("date", sort_dir)
    return jsonify([fmt_expense(d) for d in docs])


@app.route("/api/expenses/<eid>", methods=["DELETE"])
@login_required
def delete_expense(eid):
    expenses_col.delete_one({
        "_id":     ObjectId(eid),
        "user_id": ObjectId(session["user_id"]),
    })
    return jsonify({"message": "Deleted"})


@app.route("/api/income/<iid>", methods=["DELETE"])
@login_required
def delete_income(iid):
    income_col.delete_one({
        "_id":     ObjectId(iid),
        "user_id": ObjectId(session["user_id"]),
        "note":    {"$ne": "OPENING BALANCE"},
    })
    return jsonify({"message": "Deleted"})


# =========================
# SUMMARY
# =========================
@app.route("/api/summary")
@login_required
def summary():
    year  = int(request.args.get("year",  datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))
    uid   = ObjectId(session["user_id"])

    start_of_month, end_of_month = month_range(year, month)

    # Cumulative income up to end of selected month
    res = list(income_col.aggregate([
        {"$match": {"user_id": uid, "date": {"$lt": end_of_month}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_income = res[0]["total"] if res else 0.0

    # Cumulative expenses up to end of selected month
    res = list(expenses_col.aggregate([
        {"$match": {"user_id": uid, "date": {"$lt": end_of_month}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]))
    total_expense = res[0]["total"] if res else 0.0

    # Category breakdown for the selected month only
    categories = [
        {"category": r["_id"], "amount": round(r["amount"], 2)}
        for r in expenses_col.aggregate([
            {"$match": {"user_id": uid, "date": {"$gte": start_of_month, "$lt": end_of_month}}},
            {"$group": {"_id": "$category", "amount": {"$sum": "$amount"}}},
            {"$sort": {"amount": -1}},
        ])
    ]

    # Monthly expense trend — last 6 months, chronological
    trend = [
        {
            "month":   f"{r['_id']['year']}-{r['_id']['month']:02d}",
            "expense": round(r["expense"], 2),
        }
        for r in expenses_col.aggregate([
            {"$match": {"user_id": uid}},
            {"$group": {
                "_id": {"year": {"$year": "$date"}, "month": {"$month": "$date"}},
                "expense": {"$sum": "$amount"},
            }},
            {"$sort": {"_id.year": -1, "_id.month": -1}},
            {"$limit": 6},
        ])
    ]
    trend = trend[::-1]

    return jsonify({
        "total_income":  round(total_income,  2),
        "total_expense": round(total_expense, 2),
        "balance":       round(total_income - total_expense, 2),
        "categories":    categories,
        "trend":         trend,
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
