from flask import Flask, render_template, url_for
from database import Database
from dbhelper import dbhelper

app = Flask(__name__)

@app.route('/')
def index():
    dbhelper.initDB()
    def db_query():
        db = Database()
        prods = db.list_products()
        return prods
    res = db_query()
    return render_template('index.html', result=res, content_type='application/json')
    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')