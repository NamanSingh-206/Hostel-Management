# run_once.py  ← run from terminal, then delete this file
from werkzeug.security import generate_password_hash
import MySQLdb

conn = MySQLdb.connect(host='localhost', user='root', passwd='Himysql@123', db='hostel_db')
cur = conn.cursor()
hashed = generate_password_hash('admin123')
cur.execute("UPDATE wardens SET password = %s WHERE username = 'admin'", (hashed,))
conn.commit()
cur.close()
conn.close()
print("Password updated successfully!")