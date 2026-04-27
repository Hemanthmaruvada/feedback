# 📋 FeedbackHub — Online Feedback Collection System
### Built with Python Flask | Beginner-Friendly

---

## 🚀 How to Run (Step by Step)

### Step 1 — Make sure Python is installed
```bash
python --version   # should say Python 3.x
```

### Step 2 — Install Flask
```bash
pip install flask
```

### Step 3 — Run the app
```bash
cd feedback_app
python app.py
```

### Step 4 — Open your browser
Go to: **http://127.0.0.1:5000**

---

## 🔐 Admin Login
- **Username:** `admin`
- **Password:** `admin123`

> Change these in `app.py` or via the database after running.

---

## 📁 Project Structure
```
feedback_app/
├── app.py               ← Main Flask application
├── requirements.txt     ← Dependencies
├── feedback.db          ← SQLite database (auto-created on first run)
└── templates/
    ├── base.html        ← Shared layout with sidebar
    ├── login.html       ← Admin login page
    ├── dashboard.html   ← Admin dashboard
    ├── new_form.html    ← Create a new form
    ├── edit_form.html   ← Add/remove questions
    ├── respond.html     ← Public form (shared with respondents)
    ├── analytics.html   ← Charts and response data
    ├── thank_you.html   ← Shown after submitting
    └── error.html       ← Error page
```

---

## 🛠️ Features
- ✅ Admin login/logout
- ✅ Create, edit, delete feedback forms
- ✅ 4 question types: Open Text, Multiple Choice, Checkbox, Rating (1–5)
- ✅ Unique shareable link for each form
- ✅ Anonymous & identified response modes
- ✅ Bar and Pie chart visualizations (Chart.js)
- ✅ Export all responses to CSV
- ✅ SQLite database (no setup required)

---

## 💡 How It Works
1. Admin logs in → creates a form → adds questions
2. Admin copies the share link and sends it to respondents
3. Respondents fill the form (no login needed)
4. Admin views charts and analytics in the dashboard
5. Admin can export all responses as a CSV file

---

## 🔧 Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask |
| Database | SQLite (via sqlite3) |
| Frontend | Bootstrap 5 + Chart.js |
| Icons | Font Awesome 6 |

---

## 📝 For Beginners: Key Concepts Used
- **Flask Routes** — `@app.route(...)` maps URLs to functions
- **Jinja2 Templates** — HTML files with `{{ variable }}` and `{% for %}` loops
- **SQLite** — A simple file-based database, no server needed
- **Sessions** — How Flask remembers who is logged in
- **POST/GET** — How HTML forms send data to the server
