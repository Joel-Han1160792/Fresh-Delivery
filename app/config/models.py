from app.config.database import getDbConnection
from app.config.database import getCursor
from flask import request
import mysql.connector
from mysql.connector import FieldType

# get_all functions 

def all_product_cats():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Categories')
    categories = cursor.fetchall()
    connection.close()
    return  categories

def all_units():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
    SELECT 
        SUBSTRING(COLUMN_TYPE, 6, LENGTH(COLUMN_TYPE) - 6) AS enum_values 
    FROM 
        information_schema.COLUMNS 
    WHERE 
        TABLE_NAME = 'Products' 
        AND COLUMN_NAME = 'Unit';
    """)

    result = cursor.fetchone()
    value_type = type(result['enum_values'])
    if(value_type == bytes):
        units = result['enum_values'].decode('utf-8').strip("'").split("','")
    else:
        units= result['enum_values'].strip("'").split("','")
    # Extract and split the values
    connection.close()
    return  units

def all_units_from_unitsTable():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
    SELECT UnitID, Name FROM Units
    """)

    units = cursor.fetchall()
    connection.close()
    return  units

def all_products():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM Products"
    params = []
    name = request.args.get('name')
    category_id = request.args.get('category')
    available = (request.args.get('available'))
 
    conditions = []
   
    if name:
        conditions.append("Name LIKE %s")
        params.append("%" + name + "%")
    if category_id and category_id.strip():  # Ensure category_id is not empty
        conditions.append("CategoryID = %s")
        params.append(category_id)
    if available and 0==available:
        conditions.append("available= %s")
        params.append(available)
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    products = cursor.fetchall()
    connection.close()

    return  products

def all_orders(locationID):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    query = """SELECT u.Email, o.StatusID, os.StatusName, TotalPrice, l.Name as Location, l.Address, DateOrdered, OrderID, o.UserID, DateUpdated 
               FROM Orders o 
               INNER JOIN Users u ON o.UserID= u.UserID
               INNER JOIN OrderStatus os ON o.StatusID=os.StatusID
               INNER JOIN Locations l ON l.LocationID = o.LocationID
            """
    params = []
    username = request.args.get('username')
    statusID = request.args.get('statusID')
    date = request.args.get('date')
    
    conditions = []
    if locationID:
        conditions.append("o.LocationID = %s")
        params.append(locationID)
    if username:
        conditions.append("u.Email LIKE %s")
        params.append("%" + username + "%")
    if statusID and statusID.strip():
        conditions.append("o.StatusID = %s")
        params.append(statusID)
    if date:
        conditions.append("o.DateOrdered LIKE %s")
        params.append("%" + date + "%")
        
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    orders = cursor.fetchall()
    connection.close()
   
    return orders

def all_status():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""select statusID, statusName from OrderStatus
            """)
    status = cursor.fetchall()
    connection.close()
    return  status

#### Validations
#phone number
def validate_phone(phone):
    return phone.isdigit() and len(phone) in [10, 11]

