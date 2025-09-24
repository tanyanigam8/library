from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, datetime
from functools import wraps

DB = 'data.db'
app = Flask(__name__)
app.secret_key = 'devkey'

# ---------- helpers ----------
def db():
    return sqlite3.connect(DB)

def today():
    return datetime.date.today()

def to_date(s: str):
    return datetime.date.fromisoformat(s)

def admin_only(fn):
    @wraps(fn)
    def wrap(*a, **k):
        if session.get('role') != 'admin':
            flash('admin only')
            return redirect(url_for('login'))
        return fn(*a, **k)
    return wrap

# ---------- home ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- unified login (new / existing) ----------
# Give aliases so old template links keep working.
@app.route('/login', methods=['GET','POST'], endpoint='login')
@app.route('/login/admin', methods=['GET','POST'], endpoint='login_admin')
@app.route('/login/member', methods=['GET','POST'], endpoint='login_member')
def login_unified():
    """
    One page handles both:
    - mode='new' (default): create user (name, username, password, role)
    - mode='existing': login with username/password
    """
    if request.method == 'POST':
        mode = request.form.get('mode', 'new')
        u = (request.form.get('user') or '').strip()
        p = (request.form.get('pw') or '').strip()

        if mode == 'new':
            n = (request.form.get('name') or '').strip()
            r = (request.form.get('role') or 'user').strip()
            if not (n and u and p):
                flash('enter name, username and password')
                return render_template('login.html', mode=mode)
            with db() as d:
                c = d.cursor()
                c.execute("SELECT 1 FROM users WHERE uname=?", (u,))
                if c.fetchone():
                    flash('username already exists')
                    return render_template('login.html', mode=mode)
                c.execute("INSERT INTO users(name,uname,pwd,role) VALUES(?,?,?,?)",
                          (n, u, p, 'admin' if r=='admin' else 'user'))
                uid = c.lastrowid
                d.commit()
            session['uid'] = uid
            session['role'] = 'admin' if r=='admin' else 'user'
            return redirect(url_for('maintenance') if session['role']=='admin' else url_for('reports'))

        else:  # existing
            if not (u and p):
                flash('enter username and password')
                return render_template('login.html', mode=mode)
            with db() as d:
                c = d.cursor()
                c.execute("SELECT id, role FROM users WHERE uname=? AND pwd=?", (u,p))
                r = c.fetchone()
            if not r:
                flash('invalid credentials')
                return render_template('login.html', mode=mode)
            session['uid'], session['role'] = r[0], (r[1] or 'user')
            return redirect(url_for('maintenance') if session['role']=='admin' else url_for('reports'))

    # GET
    return render_template('login.html', mode='new')  # default to "new" per your spec

@app.route('/logout')
def logout():
    session.clear()
    return render_template('logged_out.html')

# ---------- BOOKS (typ='book' or 'movie') ----------
@app.route('/books')
def books():
    d = db(); c = d.cursor()
    c.execute('SELECT id,title,author,avail FROM books WHERE typ="book"')
    rows = c.fetchall(); d.close()
    return render_template('books.html', rows=rows)

@app.route('/book/add', methods=['GET','POST'])
@admin_only
def book_add():
    if request.method == 'POST':
        typ = (request.form.get('typ') or 'book').strip() or 'book'
        t = (request.form.get('title') or '').strip()
        a = (request.form.get('author') or '').strip()
        p = (request.form.get('pub') or '').strip()
        if not (t and a and p):
            flash('enter all fields'); return render_template('book_form.html', action='Add', row=None)
        d = db(); c = d.cursor()
        c.execute("INSERT INTO books(title,author,pub,typ,avail) VALUES(?,?,?,?,1)", (t,a,p,typ))
        d.commit(); d.close()
        flash('saved'); return redirect(url_for('books') if typ=='book' else url_for('master_movies'))
    return render_template('book_form.html', action='Add', row=None)

@app.route('/book/edit/<int:id>', methods=['GET','POST'])
@admin_only
def book_edit(id):
    d = db(); c = d.cursor()
    if request.method == 'POST':
        typ = (request.form.get('typ') or 'book').strip() or 'book'
        t = (request.form.get('title') or '').strip()
        a = (request.form.get('author') or '').strip()
        p = (request.form.get('pub') or '').strip()
        if not (t and a and p):
            flash('enter all fields')
            c.execute("SELECT id,title,author,pub,typ FROM books WHERE id=?", (id,))
            r = c.fetchone(); d.close()
            return render_template('book_form.html', action='Edit', row=r)
        c.execute("UPDATE books SET title=?, author=?, pub=?, typ=? WHERE id=?", (t,a,p,typ,id))
        d.commit(); d.close()
        flash('updated'); return redirect(url_for('books') if typ=='book' else url_for('master_movies'))
    c.execute("SELECT id,title,author,pub,typ FROM books WHERE id=?", (id,))
    r = c.fetchone(); d.close()
    return render_template('book_form.html', action='Edit', row=r)

@app.route('/book/del/<int:id>')
@admin_only
def book_del(id):
    d = db(); c = d.cursor()
    c.execute("DELETE FROM books WHERE id=?", (id,))
    d.commit(); d.close()
    flash('deleted'); return redirect(url_for('books'))

# Available Books (must fill title or pick author)
@app.route('/books/available', methods=['GET','POST'])
def book_available():
    d = db(); c = d.cursor()
    c.execute("SELECT DISTINCT author FROM books WHERE typ='book' ORDER BY author")
    authors = [r[0] for r in c.fetchall()]
    rows = []; msg = ''
    if request.method == 'POST':
        q = (request.form.get('q') or '').strip()
        a = (request.form.get('author') or '').strip()
        if not q and not a:
            msg = 'enter title or pick author'
        else:
            if q and a:
                c.execute("""SELECT id,title,author FROM books
                             WHERE avail=1 AND typ='book' AND title LIKE ? AND author=?""",(f'%{q}%',a))
            elif q:
                c.execute("""SELECT id,title,author FROM books
                             WHERE avail=1 AND typ='book' AND title LIKE ?""",(f'%{q}%',))
            else:
                c.execute("""SELECT id,title,author FROM books
                             WHERE avail=1 AND typ='book' AND author=?""",(a,))
            rows = c.fetchall()
    d.close()
    return render_template('book_available.html', authors=authors, rows=rows, msg=msg)

# Search Results (radio last column)
@app.route('/books/search', methods=['GET','POST'])
def book_search():
    rows = []
    if request.method == 'POST':
        q = (request.form.get('q') or '').strip()
        d = db(); c = d.cursor()
        c.execute("SELECT id,title,author FROM books WHERE title LIKE ? OR author LIKE ?", (f'%{q}%', f'%{q}%'))
        rows = c.fetchall(); d.close()
    return render_template('search_results.html', rows=rows)

# ---------- MEMBERS ----------
@app.route('/members')
def members():
    d = db(); c = d.cursor()
    c.execute('SELECT id,name,phone,email,member_till FROM members')
    rows = c.fetchall(); d.close()
    return render_template('members.html', rows=rows)

@app.route('/member/add', methods=['GET','POST'])
@admin_only
def member_add():
    if request.method == 'POST':
        n = (request.form.get('name') or '').strip()
        p = (request.form.get('phone') or '').strip()
        e = (request.form.get('email') or '').strip()
        plan = (request.form.get('plan') or '6m')
        if not (n and p and e):
            flash('enter all fields'); return render_template('member_form.html', action='Add', row=None)
        add_days = 182 if plan=='6m' else 365 if plan=='1y' else 730
        mt = (today() + datetime.timedelta(days=add_days)).isoformat()
        d = db(); c = d.cursor()
        c.execute("INSERT INTO members(name,phone,email,member_till) VALUES(?,?,?,?)", (n,p,e,mt))
        d.commit(); d.close()
        flash('saved'); return redirect(url_for('members'))
    return render_template('member_form.html', action='Add', row=None)

@app.route('/member/edit/<int:id>', methods=['GET','POST'])
@admin_only
def member_edit(id):
    d = db(); c = d.cursor()
    if request.method == 'POST':
        ext = request.form.get('extend','6m')
        cancel = request.form.get('cancel') == 'on'
        c.execute("SELECT member_till FROM members WHERE id=?", (id,))
        r = c.fetchone()
        if not r:
            d.close(); flash('not found'); return redirect(url_for('members'))
        if cancel:
            mt = today().isoformat()
        else:
            cur = to_date(r[0]) if r[0] else today()
            add_days = 182 if ext=='6m' else 365 if ext=='1y' else 730
            mt = (cur + datetime.timedelta(days=add_days)).isoformat()
        c.execute("UPDATE members SET member_till=? WHERE id=?", (mt,id))
        d.commit(); d.close()
        flash('updated'); return redirect(url_for('members'))
    c.execute("SELECT id,name,phone,email,member_till FROM members WHERE id=?", (id,))
    row = c.fetchone(); d.close()
    return render_template('member_form.html', action='Edit', row=row)

@app.route('/member/del/<int:id>')
@admin_only
def member_del(id):
    d = db(); c = d.cursor()
    c.execute("DELETE FROM members WHERE id=?", (id,))
    d.commit(); d.close()
    flash('deleted'); return redirect(url_for('members'))

# ---------- ISSUES (transactions) ----------
@app.route('/issues')
def issues():
    d = db(); c = d.cursor()
    c.execute("""SELECT i.id, b.title, m.name, i.issue_dt, i.due_dt, i.ret_dt
                 FROM issues i
                 JOIN books b ON i.book_id=b.id
                 JOIN members m ON i.member_id=m.id""")
    rows = c.fetchall(); d.close()
    return render_template('issues.html', rows=rows, today=today().isoformat())

@app.route('/issue/add', methods=['GET','POST'])
def issue_add():
    d = db(); c = d.cursor()
    if request.method == 'POST':
        bid = (request.form.get('book') or '').strip()
        mid = (request.form.get('member') or '').strip()
        idt_s = request.form.get('issue_dt', today().isoformat())
        due_s = request.form.get('due_dt', (today()+datetime.timedelta(days=15)).isoformat())
        if not (bid and mid):
            flash('select book and member')
        else:
            idt = to_date(idt_s); due = to_date(due_s)
            if idt < today():
                flash('issue date cannot be before today')
            elif due > (idt + datetime.timedelta(days=15)):
                flash('return date cannot be beyond 15 days from issue date')
            else:
                c.execute("INSERT INTO issues(book_id,member_id,issue_dt,due_dt,ret_dt) VALUES(?,?,?,?,NULL)",
                          (bid,mid,idt_s,due_s))
                c.execute("UPDATE books SET avail=0 WHERE id=?", (bid,))
                d.commit(); d.close()
                flash('issued'); return redirect(url_for('issues'))
    c.execute("SELECT id,title,author FROM books WHERE avail=1")
    bs = c.fetchall()
    c.execute("SELECT id,name FROM members")
    ms = c.fetchall(); d.close()
    tdy = today().isoformat()
    due_def = (today()+datetime.timedelta(days=15)).isoformat()
    return render_template('issue_form.html', books=bs, members=ms, tdy=tdy, due_def=due_def)

@app.route('/issues/active')
def issues_active():
    d = db(); c = d.cursor()
    c.execute("""SELECT i.id, b.title, m.name, i.issue_dt, i.due_dt
                 FROM issues i
                 JOIN books b ON i.book_id=b.id
                 JOIN members m ON i.member_id=m.id
                 WHERE i.ret_dt IS NULL""")
    rows = c.fetchall(); d.close()
    return render_template('active_issues.html', rows=rows)

@app.route('/issues/overdue')
def issues_overdue():
    tdy = today().isoformat()
    d = db(); c = d.cursor()
    c.execute("""SELECT i.id, b.title, m.name, i.issue_dt, i.due_dt
                 FROM issues i
                 JOIN books b ON i.book_id=b.id
                 JOIN members m ON i.member_id=m.id
                 WHERE i.ret_dt IS NULL AND i.due_dt < ?""", (tdy,))
    rows = c.fetchall(); d.close()
    return render_template('overdue.html', rows=rows, today=tdy)

@app.route('/issue/ret/<int:id>', methods=['GET','POST'])
def issue_ret(id):
    d = db(); c = d.cursor()
    c.execute("""SELECT i.id, b.id, b.title, b.author, i.issue_dt, i.due_dt
                 FROM issues i JOIN books b ON i.book_id=b.id WHERE i.id=?""", (id,))
    r = c.fetchone(); d.close()
    if not r:
        flash('not found'); return redirect(url_for('issues'))
    if request.method == 'POST':
        ret_dt = request.form.get('ret_dt', today().isoformat())
        return redirect(url_for('fine_pay', id=id, ret_dt=ret_dt))
    return render_template('return_form.html', row=r, ret_def=today().isoformat())

@app.route('/fine/<int:id>', methods=['GET','POST'])
def fine_pay(id):
    d = db(); c = d.cursor()
    c.execute("""SELECT i.id, i.book_id, b.title, b.author, i.issue_dt, i.due_dt
                 FROM issues i JOIN books b ON i.book_id=b.id WHERE i.id=?""", (id,))
    r = c.fetchone()
    if not r:
        d.close(); flash('not found'); return redirect(url_for('issues'))
    ret_s = request.args.get('ret_dt') if request.method == 'GET' else request.form.get('ret_dt')
    ret_s = ret_s or today().isoformat()
    late_days = max(0, (to_date(ret_s) - to_date(r[5])).days)
    if request.method == 'POST':
        paid = request.form.get('paid') == 'on'
        if late_days > 0 and not paid:
            flash('fine pending - check Paid to continue')
            d.close()
            return render_template('fine.html', row=r, ret_dt=ret_s, late=late_days)
        c.execute("UPDATE issues SET ret_dt=? WHERE id=?", (ret_s, id))
        c.execute("UPDATE books SET avail=1 WHERE id=?", (r[1],))
        d.commit(); d.close()
        return redirect(url_for('confirm', msg='return done'))
    d.close()
    return render_template('fine.html', row=r, ret_dt=ret_s, late=late_days)

# ---------- menus (flowchart) ----------
@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/transactions')
def transactions():
    return render_template('transactions.html')

@app.route('/maintenance')
@admin_only
def maintenance():
    return render_template('maint_menu.html')

# ---------- master lists (user + admin) ----------
@app.route('/master')
def master_index():
    return render_template('master_index.html')

@app.route('/master/books')
def master_books():
    d = db(); c = d.cursor()
    c.execute("SELECT id,title,author,typ,avail FROM books WHERE typ='book'")
    rows = c.fetchall(); d.close()
    return render_template('master_books.html', rows=rows)

@app.route('/master/movies')
def master_movies():
    d = db(); c = d.cursor()
    c.execute("SELECT id,title,author,pub,avail FROM books WHERE typ='movie'")
    rows = c.fetchall(); d.close()
    return render_template('master_movies.html', rows=rows)

@app.route('/master/memberships')
def master_memberships():
    d = db(); c = d.cursor()
    c.execute("SELECT id,name,phone,email,member_till FROM members")
    rows = c.fetchall(); d.close()
    return render_template('master_memberships.html', rows=rows)

# ---------- requests ----------
@app.route('/requests', endpoint='requests')
def req_list():
    d = db(); c = d.cursor()
    c.execute("""SELECT r.id, m.name, r.book_title, r.dt, r.status
                 FROM requests r LEFT JOIN members m ON r.member_id=m.id
                 ORDER BY r.id DESC""")
    rows = c.fetchall(); d.close()
    return render_template('requests.html', rows=rows)

@app.route('/request/add', methods=['GET','POST'])
def req_add():
    if request.method == 'POST':
        mid = (request.form.get('member') or '').strip() or None
        bt  = (request.form.get('book_title') or '').strip()
        if not bt:
            flash('enter book title')
        else:
            d = db(); c = d.cursor()
            c.execute("INSERT INTO requests(member_id,book_title,dt,status) VALUES(?,?,?,?)",
                      (mid, bt, today().isoformat(), 'pending'))
            d.commit(); d.close()
            return redirect(url_for('confirm', msg='request saved'))
    d = db(); c = d.cursor()
    c.execute("SELECT id,name FROM members")
    ms = c.fetchall(); d.close()
    return render_template('request_form.html', members=ms)

# ---------- Maintenance notes (admin only) ----------
@app.route('/maint', endpoint='maint')                # keeps url_for('maint')
@app.route('/maint/list', endpoint='maint_list')      # also allows url_for('maint_list')
@admin_only
def maint_list():
    d = db(); c = d.cursor()
    c.execute("SELECT id,title,dt,details FROM maint ORDER BY id DESC")
    rows = c.fetchall(); d.close()
    return render_template('maint.html', rows=rows)


@app.route('/maint/add', methods=['GET','POST'])
@admin_only
def maint_add():
    if request.method == 'POST':
        t = (request.form.get('title') or '').strip()
        ds = (request.form.get('details') or '').strip()
        if not t:
            flash('enter title'); return render_template('maint_form.html')
        d = db(); c = d.cursor()
        c.execute("INSERT INTO maint(title,dt,details) VALUES(?,?,?)", (t, today().isoformat(), ds))
        d.commit(); d.close()
        return redirect(url_for('confirm', msg='maintenance saved'))
    return render_template('maint_form.html')

# ---------- misc ----------
@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

@app.route('/confirm')
def confirm():
    return render_template('confirm.html', msg=request.args.get('msg','saved'))

if __name__ == '__main__':
    app.run(debug=True)
