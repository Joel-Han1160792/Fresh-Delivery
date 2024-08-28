import mysql.connector
from mysql.connector import FieldType
import connect


dbconn = None
connection = None

def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser,
    password=connect.dbpass, host=connect.dbhost, auth_plugin='mysql_native_password',
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn

def getDbConnection():
    return mysql.connector.connect(user=connect.dbuser, password=connect.dbpass, host=connect.dbhost, database=connect.dbname, auth_plugin='mysql_native_password')
