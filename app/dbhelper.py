import boto3
import os
import mysql.connector as mysql
import json

class dbhelper:
    @staticmethod
    def get_info():
        secret_name = os.getenv('secretname')
        region_name = os.getenv('region')
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        return client.get_secret_value(SecretId=secret_name)['SecretString']
        
    @staticmethod
    def initDB():
        dbinfo = json.loads(dbhelper.get_info())
        db = mysql.connect(
            host = dbinfo['host'],
            user = dbinfo['username'],
            passwd = dbinfo['password']
        )
        cursor = db.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS testdb")
        cursor.execute("CREATE TABLE IF NOT EXISTS testdb.Products (id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,productName VARCHAR(250) NOT NULL,price FLOAT NOT NULL)")
        
        db = mysql.connect(
            host = dbinfo['host'],
            user = dbinfo['username'],
            passwd = dbinfo['password'],
            database='testdb'
        )
        cursor = db.cursor()
        
        cursor.execute("INSERT INTO Products (productName, price) SELECT * FROM (SELECT 'Shampoo', 3.2) AS tmp WHERE NOT EXISTS (SELECT productName FROM Products WHERE productName = 'Shampoo') LIMIT 1")
        cursor.execute("INSERT INTO Products (productName, price) SELECT * FROM (SELECT 'Conditioner', 5.9) AS tmp WHERE NOT EXISTS (SELECT productName FROM Products WHERE productName = 'Conditioner') LIMIT 1")
        db.commit()