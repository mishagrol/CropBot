import sqlite3

db = sqlite3.connect("../db/agrobot.db")
# print('Hello from SQL', flush=True)
cursor = db.cursor()
cursor.executescript(open("../db/schema.sql").read())
# try:
    
# except:
#     print("DB ALREADY EXISTS!!!!")
