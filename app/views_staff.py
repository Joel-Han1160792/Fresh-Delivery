from flask import request
from flask import render_template, flash
from app import app
from flask import redirect
from flask import url_for
from flask import session
import re
from flask import flash
from app.config.database import getCursor, getDbConnection
from app.config.helpers import format_nz_currency, require_role
from flask_hashing import Hashing
from flask import request
import mysql.connector
from mysql.connector import FieldType
from app.config.models import all_orders
from app.config.models import all_status
from app.config.models import all_products
from app.config.models import all_product_cats
from app.config.models import all_units
from app.config.models import all_units_from_unitsTable
import os
from datetime import datetime
dir_path = os.path.dirname(os.path.realpath(__file__))

@app.route('/manage-orders')
@require_role(2)
def list_orders():
    role = session.get('role')
    locationID = session.get('locationid') if role != 4 else None
    orders = all_orders(locationID)
    status = all_status()
    return render_template('staff/list_orders.html', orders=orders, status=status, format_nz_currency=format_nz_currency)

@app.route('/manage-products')
@require_role(2)
def list_all_products():
    products = all_products()
    cats = all_product_cats()
    return render_template('staff/list_products.html', products=products, cats=cats, format_nz_currency=format_nz_currency )

@app.route('/add-product', methods=['POST', 'GET'])
@require_role(2)
def add_product():
    cats = all_product_cats()
    units = all_units_from_unitsTable()
    if request.method =='GET':
        return  render_template('staff/add_product.html',cats=cats, units=units)
    if request.method =='POST':
        if session.get('loggedin') != True or session.get('role') < 1:
            flash('Please log in to add items to your cart.')
            return redirect(url_for('login'))
        
        userId = session.get('id')
        if 'photo' not in request.files:
            msg = 'No file part in the request'
            return render_template('staff/add_product.html', msg=msg) 
        file = request.files['photo']
        if file.filename == '':
            msg = 'No selected file'
            return render_template('staff/add_product.html', msg=msg) 
        if file:
            # Save the uploaded file
            global dir_path
            img_folder = dir_path + "/static/img/"
            file.save(os.path.join(img_folder, file.filename))
            msg = 'File uploaded successfully'
        name = request.form.get('name')
        description  = request.form.get('description')
        quantity = int(request.form.get('quantity', 1))
        price =float(request.form.get('price', 2))
        categoryID = int(request.form.get('categroy', 1))
        unit = request.form.get('unit')
        imageURL = file.filename
        cursor = getCursor()
        cursor.execute("INSERT INTO Products (Name, Description, Price,  AvailableQuantity, ImageURL, CategoryID, UnitID) values(%s,%s,%s,%s,%s,%s,%s)",(name,description,quantity,price,imageURL,categoryID,unit))
        msg="Product Added"
        msgLevel = 's'
        return redirect(url_for('list_all_products'))
        # return render_template('staff/add_product.html', msg=msg,cats=cats) 
    
@app.route('/delete-product/<int:product_id>', methods=['POST','GET'])  
def delete_product (product_id):  
    if session.get('loggedin') != True or session.get('role') < 1:
            flash('Please log in to add items to your cart.')
            return redirect(url_for('login'))
    else:
        userId = session.get('id')   
        cursor = getCursor()
        cursor.execute("Update Products set Available = 0 where ProductID = %s",( product_id,))
       #cursor.execute("delete from Products where ProductID = %s",( product_id,))
        msg="Product Deleted"
        msgLevel = 's'
        return redirect(url_for('list_all_products'))

@app.route('/update-product/<int:product_id>', methods=['POST', 'GET'])
def update_product(product_id):
    cats = all_product_cats()
    if request.method =='POST':
        if session.get('loggedin') != True or session.get('role') < 1:
            flash('Please log in to add items to your cart.')
            return redirect(url_for('login'))
        imageURL=request.form.get('oPhoto')
        userId = session.get('id')
        if 'photo' not in request.files:
            msg = 'No file part in the request'
            msgLevel = 'w'
            return redirect(url_for('update_product', product_id=product_id)) 
        file = request.files['photo']
        if file.filename == '':
            msg = 'No selected file'
            msgLevel = 'w'
           # return redirect(url_for('update_product', product_id=product_id)) 
        elif file.filename != '':
            # Save the uploaded file
            global dir_path
            img_folder = dir_path + "/static/img/"
            file.save(os.path.join(img_folder, file.filename))
            imageURL = file.filename
            msg = 'File uploaded successfully'
            msgLevel = 's'
        name = request.form.get('name')
        description  = request.form.get('description')
        quantity = int(request.form.get('quantity', 1))
        price =float(request.form.get('price', 2))
        unit = request.form.get('unit')
        categroyID = int(request.form.get('categroy'))
        available = int(request.form.get('available'))
        cursor = getCursor()
        cursor.execute("UPDATE Products SET name = %s, description= %s, availableQuantity = %s, price = %s, imageURL=%s, categoryID=%s, unitID=%s, available=%s where productId = %s",(name, description,quantity,price,imageURL, categroyID, unit, available, product_id))
        # cursor.execute("SELECT ProductID, p.Name, Description, Price, Unit, c.CategoryID, AvailableQuantity, ImageURL, c.Name, unit FROM Products p inner join Categories c on c.CategoryID = p.CategoryID WHERE ProductID = %s", (product_id,))
        # product = cursor.fetchone()
        msg="Product updated"
        msgLevel = 's'
        return redirect(url_for('list_all_products'))
        # return redirect(url_for('update_product', product_id=product_id, cats=cats))
    
    if request.method == 'GET':
        connection = getDbConnection()
        cursor = getCursor()
        try:
            cursor.execute("SELECT ProductID, p.Name, Description, Price, UnitID, c.CategoryID, AvailableQuantity, ImageURL, c.Name, p.Available FROM Products p inner join Categories c on c.CategoryID = p.CategoryID WHERE ProductID = %s", (product_id,))
            product = cursor.fetchone()
            units = all_units_from_unitsTable()
            if not product:
                return "Product not found", 404       
            return render_template('staff/product_details.html', product=product, cats=cats, units=units)
        
        except Exception as e:
            print("Error fetching product details:", e)
            return "An error occurred", 500
        finally:
            cursor.close()
            connection.close()

@app.route('/update-order/<int:order_id>', methods=['POST', 'GET'])
def update_order(order_id):
   
    if request.method =='POST':
        if session.get('loggedin') != True or session.get('role') < 1:
            flash('Please log in to add items to your cart.')
            return redirect(url_for('login'))
      
        statusID = int(request.form.get('statusInputDropdown'))
       
        msg="Order updated"
        msgLevel = 's'

        connection = getDbConnection()
        cursor = getCursor()
        try:
            cursor.execute("update Orders set StatusID=%s, DateUpdated=%s WHERE OrderID = %s", (statusID, datetime.now(),order_id,))
            # Insert a notification here to a user base on userID

            cursor.execute(""" Select UserID, os.statusName, os.StatusID from Orders o 
                           inner join OrderStatus os on o.StatusID = os.StatusID
                           where o.OrderID = %s order by DateUpdated desc LIMIT 1
            """,(order_id,))
            currentOrder = cursor.fetchone()
            cursor.execute("""Insert Notifications (UserID, Title, Message, DateCreated, type )
                             values ( %s, 'Status Update', CONCAT('Your order is ', %s),  %s, 'Order Update')""",(currentOrder[0],currentOrder[1],datetime.now(),))
            # Get the Notification ID
            cursor.execute("""Select max(NotificationID) from Notifications where userID = %s""",(currentOrder[0],))
            newNotice = cursor.fetchone()
            # Insert to NotificationRecipient
            cursor.execute("""Insert NotificationRecipients values(%s,%s,0)""",(currentOrder[0],newNotice[0]))
            
           
            return redirect(url_for('list_orders'))
        
        except Exception as e:
            print("Error fetching product details:", e)
            return "An error occurred", 500
        finally:
            cursor.close()
            connection.close()
            
