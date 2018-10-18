import sqlite3
import json


def get_tables(src='collection.anki2', dst='sample.json'):
    conn = sqlite3.connect(src)
    conn.row_factory = sqlite3.Row

    d = dict()
    c = conn.execute('''SELECT tbl_name FROM sqlite_master WHERE type="table"''')
    for r in c:
        try:
            c1 = conn.execute(f'''
                SELECT * FROM "{r[0]}" 
                WHERE id >= (abs(random()) % (SELECT max(id) FROM "{r[0]}")) 
                LIMIT 1''')
            r1 = c1.fetchone()
            if r1:
                d[r[0]] = dict(r1)
        except sqlite3.OperationalError:
            pass

    with open(dst, 'w') as f:
        d0 = dict()
        d0['tables'] = d
        json.dump(d0, f, indent=2, ensure_ascii=False)


def get_miscellaneous(src='collection.anki2', dst='sample.json'):
    conn = sqlite3.connect(src)
    conn.row_factory = sqlite3.Row

    with open(dst) as f:
        d0 = json.load(f)

    c = conn.execute('''SELECT * FROM col''')
    for k, v in dict(c.fetchone()).items():
        if isinstance(v, str):
            d0.setdefault('col', dict())[k] = json.loads(v)
            d0['tables']['col'][k] = 'See below'

    with open(dst, 'w') as f:
        json.dump(d0, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    get_tables()
    get_miscellaneous()
