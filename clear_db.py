import sqlite3
conn = sqlite3.connect('runs.db')
conn.execute('DELETE FROM runs;')
conn.commit()
conn.close()
print('Done')