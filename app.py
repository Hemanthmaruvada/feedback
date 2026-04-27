from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
import json
import csv
import io
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

DB_PATH = 'feedback.db'

# ─── Database Setup ────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users (admin only for now)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'admin'
    )''')

    # Forms
    c.execute('''CREATE TABLE IF NOT EXISTS forms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        share_token TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        allow_anonymous INTEGER DEFAULT 1
    )''')

    # Questions
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL,
        options TEXT,
        order_num INTEGER DEFAULT 0,
        FOREIGN KEY (form_id) REFERENCES forms(id)
    )''')

    # Responses
    c.execute('''CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_id INTEGER NOT NULL,
        respondent_name TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (form_id) REFERENCES forms(id)
    )''')

    # Answers
    c.execute('''CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        response_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        answer_text TEXT,
        FOREIGN KEY (response_id) REFERENCES responses(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )''')

    # Create default admin if not exists
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', 'admin123', 'admin'))

    conn.commit()
    conn.close()

# ─── Auth Helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_token():
    import random, string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

# ─── Auth Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
                            (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    forms = conn.execute('''
        SELECT f.*, COUNT(r.id) as response_count
        FROM forms f
        LEFT JOIN responses r ON f.id = r.form_id
        GROUP BY f.id
        ORDER BY f.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('dashboard.html', forms=forms)

# ─── Form Builder ──────────────────────────────────────────────────────────────

@app.route('/forms/new', methods=['GET', 'POST'])
@login_required
def new_form():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        allow_anon = 1 if request.form.get('allow_anonymous') else 0
        token = generate_token()
        conn = get_db()
        cur = conn.execute(
            'INSERT INTO forms (title, description, share_token, allow_anonymous) VALUES (?,?,?,?)',
            (title, description, token, allow_anon)
        )
        form_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash('Form created! Now add your questions.', 'success')
        return redirect(url_for('edit_form', form_id=form_id))
    return render_template('new_form.html')

@app.route('/forms/<int:form_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_form(form_id):
    conn = get_db()
    form = conn.execute('SELECT * FROM forms WHERE id=?', (form_id,)).fetchone()
    questions = conn.execute(
        'SELECT * FROM questions WHERE form_id=? ORDER BY order_num', (form_id,)).fetchall()
    conn.close()
    if not form:
        flash('Form not found!', 'error')
        return redirect(url_for('dashboard'))
    return render_template('edit_form.html', form=form, questions=questions)

@app.route('/forms/<int:form_id>/add_question', methods=['POST'])
@login_required
def add_question(form_id):
    qtext = request.form['question_text']
    qtype = request.form['question_type']
    options_raw = request.form.get('options', '')
    options = json.dumps([o.strip() for o in options_raw.split(',') if o.strip()]) if options_raw else None
    conn = get_db()
    order = conn.execute('SELECT COUNT(*) FROM questions WHERE form_id=?', (form_id,)).fetchone()[0]
    conn.execute(
        'INSERT INTO questions (form_id, question_text, question_type, options, order_num) VALUES (?,?,?,?,?)',
        (form_id, qtext, qtype, options, order)
    )
    conn.commit()
    conn.close()
    flash('Question added!', 'success')
    return redirect(url_for('edit_form', form_id=form_id))

@app.route('/forms/<int:form_id>/delete_question/<int:q_id>', methods=['POST'])
@login_required
def delete_question(form_id, q_id):
    conn = get_db()
    conn.execute('DELETE FROM questions WHERE id=? AND form_id=?', (q_id, form_id))
    conn.commit()
    conn.close()
    flash('Question deleted.', 'success')
    return redirect(url_for('edit_form', form_id=form_id))

@app.route('/forms/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    conn = get_db()
    conn.execute('DELETE FROM answers WHERE response_id IN (SELECT id FROM responses WHERE form_id=?)', (form_id,))
    conn.execute('DELETE FROM responses WHERE form_id=?', (form_id,))
    conn.execute('DELETE FROM questions WHERE form_id=?', (form_id,))
    conn.execute('DELETE FROM forms WHERE id=?', (form_id,))
    conn.commit()
    conn.close()
    flash('Form deleted.', 'success')
    return redirect(url_for('dashboard'))

# ─── Response Collection ───────────────────────────────────────────────────────

@app.route('/respond/<token>', methods=['GET', 'POST'])
def respond(token):
    conn = get_db()
    form = conn.execute('SELECT * FROM forms WHERE share_token=?', (token,)).fetchone()
    if not form:
        conn.close()
        return render_template('error.html', message='Form not found or link is invalid.')

    questions = conn.execute(
        'SELECT * FROM questions WHERE form_id=? ORDER BY order_num', (form['id'],)).fetchall()

    if request.method == 'POST':
        respondent_name = request.form.get('respondent_name', 'Anonymous') or 'Anonymous'
        cur = conn.execute(
            'INSERT INTO responses (form_id, respondent_name) VALUES (?,?)',
            (form['id'], respondent_name)
        )
        response_id = cur.lastrowid
        for q in questions:
            answer = request.form.get(f'q_{q["id"]}', '')
            conn.execute(
                'INSERT INTO answers (response_id, question_id, answer_text) VALUES (?,?,?)',
                (response_id, q['id'], answer)
            )
        conn.commit()
        conn.close()
        return render_template('thank_you.html', form=form)

    conn.close()
    return render_template('respond.html', form=form, questions=questions)

# ─── Analytics ─────────────────────────────────────────────────────────────────

@app.route('/forms/<int:form_id>/analytics')
@login_required
def analytics(form_id):
    conn = get_db()
    form = conn.execute('SELECT * FROM forms WHERE id=?', (form_id,)).fetchone()
    questions = conn.execute(
        'SELECT * FROM questions WHERE form_id=? ORDER BY order_num', (form_id,)).fetchall()
    responses = conn.execute(
        'SELECT * FROM responses WHERE form_id=? ORDER BY submitted_at DESC', (form_id,)).fetchall()

    analytics_data = []
    for q in questions:
        answers = conn.execute(
            'SELECT answer_text FROM answers WHERE question_id=?', (q['id'],)).fetchall()
        answer_list = [a['answer_text'] for a in answers if a['answer_text']]

        if q['question_type'] in ('multiple_choice', 'checkbox', 'rating'):
            from collections import Counter
            counts = Counter(answer_list)
            analytics_data.append({
                'question': q['question_text'],
                'type': q['question_type'],
                'labels': list(counts.keys()),
                'values': list(counts.values()),
                'total': len(answer_list)
            })
        else:
            analytics_data.append({
                'question': q['question_text'],
                'type': q['question_type'],
                'answers': answer_list,
                'total': len(answer_list)
            })

    conn.close()
    return render_template('analytics.html', form=form, analytics_data=analytics_data,
                           responses=responses, response_count=len(responses))

@app.route('/forms/<int:form_id>/export_csv')
@login_required
def export_csv(form_id):
    conn = get_db()
    form = conn.execute('SELECT * FROM forms WHERE id=?', (form_id,)).fetchone()
    questions = conn.execute(
        'SELECT * FROM questions WHERE form_id=? ORDER BY order_num', (form_id,)).fetchall()
    responses = conn.execute(
        'SELECT * FROM responses WHERE form_id=?', (form_id,)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    header = ['Response ID', 'Respondent', 'Submitted At'] + [q['question_text'] for q in questions]
    writer.writerow(header)

    for resp in responses:
        row = [resp['id'], resp['respondent_name'], resp['submitted_at']]
        for q in questions:
            ans = conn.execute(
                'SELECT answer_text FROM answers WHERE response_id=? AND question_id=?',
                (resp['id'], q['id'])).fetchone()
            row.append(ans['answer_text'] if ans else '')
        writer.writerow(row)

    conn.close()
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=form_{form_id}_responses.csv'}
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
