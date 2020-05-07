import pymysql
from dbhelper import dbhelper
import json

class Database:
    
    def __init__(self):
        print(dbhelper.get_info())
        dbinfo = json.loads(dbhelper.get_info())
        db = "testdb"
        self.con = pymysql.connect(
            host=dbinfo['host'], 
            user=dbinfo['username'], 
            password=dbinfo['password'], 
            db=db, 
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cur = self.con.cursor()
        
    def list_products(self):
        self.cur.execute("SELECT productName, price FROM Products")
        result = self.cur.fetchall()
        return result
        