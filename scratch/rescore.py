import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from config import calculate_relevance_score, DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('SELECT id, company, title, location, notes FROM leads')
rows = cursor.fetchall()
updated = 0
for r in rows:
    lid, comp, title, loc, notes = r
    score = calculate_relevance_score(title, f"{comp} {notes or ''}", loc)
    cursor.execute('UPDATE leads SET relevance_score = ? WHERE id = ?', (score, lid))
    updated += 1
conn.commit()
conn.close()
print(f'Successfully re-scored {updated} leads!')
