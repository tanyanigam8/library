import sqlite3
DB='data.db'
def c(s):
    return s
def init():
    db = sqlite3.connect(DB)
    cur = db.cursor()
    # users
    cur.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, uname TEXT UNIQUE, pwd TEXT, role TEXT
    )''')
    # members
    cur.execute('''CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, email TEXT, member_till TEXT
    )''')
    # books (also movies - use type field)
    cur.execute('''CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, author TEXT, pub TEXT, typ TEXT, avail INTEGER
    )''')
    # issues
    cur.execute('''CREATE TABLE IF NOT EXISTS issues(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER, member_id INTEGER, issue_dt TEXT, due_dt TEXT, ret_dt TEXT
    )''')
    # requests
    cur.execute('''CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, book_title TEXT, dt TEXT, status TEXT
    )''')
    # maintenance notes
    cur.execute('''CREATE TABLE IF NOT EXISTS maint(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, dt TEXT, details TEXT
    )''')
    # sample seed
    cur.execute("INSERT OR IGNORE INTO users(id,name,uname,pwd,role) VALUES(1,'Admin','admin','admin','admin')")
    cur.execute("INSERT INTO books(title,author,pub,typ,avail) VALUES('Little Python','Tanya','Pub1','book',1)")
    cur.execute("INSERT INTO members(name,phone,email,member_till) VALUES('Rahul','9999999999','r@mail','2026-03-01')")
    db.commit()
    db.close()
    print('db init done')
if __name__=='__main__':
    init()
