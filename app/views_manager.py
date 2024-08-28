from datetime import datetime, timedelta
from decimal import Decimal
import io
from flask import request
from flask import render_template, flash
# import matplotlib
# matplotlib.use('Agg')  # Use a non-interactive backend
# import matplotlib.pyplot as plt
import pandas as pd
import base64
from app import app
from flask import redirect
from flask import url_for
from flask import session
import re
from flask import flash
from app.config.database import getCursor, getDbConnection
from app.config.helpers import format_nz_currency, require_role, format_date
from flask_hashing import Hashing
from flask import request
import mysql.connector
from mysql.connector import FieldType
import os
from mysql.connector.errors import IntegrityError
dir_path = os.path.dirname(os.path.realpath(__file__))

### local manager's staff page 
@app.route("/local_stafflist", methods=['GET', 'POST'])
@require_role(3)
def stafflist():
    cursor = getCursor()
    manager_location = session.get('locationid')
    
    if not manager_location:
        flash('Location ID not found in session.', 'danger')
        return redirect(url_for('dashboard'))  # Adjust this redirect as needed
    
    # Base SQL query to get staff by location
    sql = """
        SELECT * FROM StaffProfile 
        WHERE LocationID = %s 
        ORDER BY CASE Status
            WHEN 'Active' THEN 1
            WHEN 'Inactive' THEN 2
            ELSE 3
        END 
    """
    cursor.execute(sql, (manager_location,))
    local_staff = cursor.fetchall()
    
    # If the request method is POST, apply the search filter
    if request.method == 'POST':
        query = request.form.get('name')
        sql = """
            SELECT * FROM StaffProfile 
            WHERE LocationID = %s 
            AND (FirstName LIKE %s OR LastName LIKE %s)
            ORDER BY CASE Status
                WHEN 'Active' THEN 1
                WHEN 'Inactive' THEN 2
                ELSE 3
            END
        """
        params = (manager_location, "%" + query + "%", "%" + query + "%")
        cursor.execute(sql, params)
        local_staff = cursor.fetchall()
    
    cursor.close()
    
    return render_template('manager/local_staff_list.html', local_staff=local_staff)

### update staff status
@app.route('/update_status', methods = ['POST'])
def update_status():
   
    cursor = getCursor()
    connection = getDbConnection()
    sql = """
           UPDATE StaffProfile 
           SET Status = %s
           WHERE UserID = %s

        """
    userID = request.form.get('userID')
    status = request.form.get('status')
    cursor.execute(sql, (status, userID))
    connection.commit()
    flash('You have set this staff inactive!', 'success')
    if session['role'] == 3:
        return redirect(url_for('stafflist'))
    if session['role'] == 4:
        return redirect(url_for('all_stafflist'))
        

### national manager's staff page 
@app.route("/national_stafflist", methods=['get','post'])
def all_stafflist():
        
        location = request.form.get('location') if request.method == 'POST' else None
        if location == "None":
             location = None

        cursor = getCursor()
        params = []
        sql = """
                SELECT * FROM StaffProfile 
                """
    
        if location:
            sql += """
                    WHERE Location = %s
                    """
            params.append(location)

        name = request.form.get('name') if request.method == 'POST' else None
        if name:
            name_condition = """
                             (FirstName LIKE %s OR LastName LIKE %s)
                        """
            if location:
                 sql += "AND" + name_condition
            else:
                 sql += "WHERE" + name_condition
             
            params.extend(['%' + name + '%', '%' + name + '%' ])

        sql += """
                ORDER BY CASE status
                        WHEN 'Active' THEN 1
                        WHEN 'Inactive' THEN 2
                        ELSE 3
                END 

        
                """
   
        cursor.execute(sql, tuple(params))

        national_staff = cursor.fetchall()

        return render_template('manager/national_staff_list.html', national_staff = national_staff, location = location)


# update staff info as manager
@app.route('/view_applications')
@require_role(3)
def view_applications():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    locationId = session['locationid']
    roleId  = session['role']
    if roleId == 4:
        query = """
            SELECT a.AccountHolderID, a.UserID, u.Email, a.BusinessName, a.BusinessAddress, a.BusinessContactNumber, a.ApplicationStatus, a.ApplicationTime
            FROM AccountHolders a
            JOIN Users u ON a.UserID = u.UserID
            WHERE a.ApplicationStatus = 'Pending'
        """
        params = ()
    else:  # Role is 3
        query = """
            SELECT a.AccountHolderID, a.UserID, u.Email, a.BusinessName, a.BusinessAddress, a.BusinessContactNumber, a.ApplicationStatus, a.ApplicationTime
            FROM AccountHolders a
            JOIN Users u ON a.UserID = u.UserID
            JOIN CustomerProfile s ON u.UserID = s.UserID
            WHERE a.ApplicationStatus = 'Pending' AND s.LocationID = %s
        """
        params = (locationId,)
        
    cursor.execute(query, params)
    applications = cursor.fetchall()

    cursor = getCursor()
    cursor.execute("SELECT * FROM AccountHolders a LEFT JOIN CustomerProfile c on c.UserID = a.UserID")
    ah = cursor.fetchall()


    cursor.close()
    connection.close()
    
    return render_template('staff/view_applications.html', applications=applications, ah = ah)



@app.route('/approve_application/<int:account_holder_id>', methods=['POST'])
def approve_application(account_holder_id):
    connection = getDbConnection()
    cursor = connection.cursor()
    
    cursor.execute("""
        UPDATE AccountHolders
        SET ApplicationStatus = 'Approved', CreditLimit = %s, RemainingCredit = %s
        WHERE AccountHolderID = %s
    """, (1000.00, 1000.00, account_holder_id))  # Default credit limit and remaining credit

    connection.commit()
    cursor.close()
    connection.close()
    
    flash('Application approved successfully.', 'success')
    return redirect(url_for('view_applications'))

@app.route('/reject_application/<int:account_holder_id>', methods=['POST'])
def reject_application(account_holder_id):
    connection = getDbConnection()
    cursor = connection.cursor()
    
    cursor.execute("""
        UPDATE AccountHolders
        SET ApplicationStatus = 'Rejected'
        WHERE AccountHolderID = %s
    """, (account_holder_id,))

    connection.commit()
    cursor.close()
    connection.close()
    
    flash('Application rejected successfully.', 'success')
    return redirect(url_for('view_applications'))


@app.route('/locations')
@require_role(4)
def view_locations():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Locations")
    locations = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('manager/locations/view_locations.html', locations=locations)

@app.route('/add_location', methods=['GET', 'POST'])
@require_role(4)
def add_location():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        shipping = request.form['shippingprice']
        connection = getDbConnection()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO Locations (Name, Address, ShippingPrice) VALUES (%s, %s, %s)", (name, address,shipping,))
            connection.commit()
            flash('Location added successfully.', 'success')
            return redirect(url_for('view_locations'))
        except Exception as e:
            print(e)
            flash('An error occurred while adding the location.', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('manager/locations/add_location.html')

@app.route('/edit_location/<int:location_id>', methods=['GET', 'POST'])
@require_role(4) 
def edit_location(location_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        shipping = request.form['shippingprice']
        try:
            cursor.execute("UPDATE Locations SET Name = %s, Address = %s, ShippingPrice = %s WHERE LocationID = %s", (name, address,shipping, location_id))
            connection.commit()
            flash('Location updated successfully.', 'success')
            return redirect(url_for('view_locations'))
        except Exception as e:
            print(e)
            flash('An error occurred while updating the location.', 'danger')
        finally:
            cursor.close()
            connection.close()
    else:
        cursor.execute("SELECT * FROM Locations WHERE LocationID = %s", (location_id,))
        location = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('manager/locations/edit_location.html', location=location)


@app.route('/delete_location/<int:location_id>', methods=['POST'])
@require_role(4)
def delete_location(location_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Check if there are any staff profiles associated with this location
        cursor.execute("SELECT * FROM StaffProfile WHERE LocationID = %s", (location_id,))
        staff_profiles = cursor.fetchall()
        if staff_profiles:
            flash('There are still staff members associated with this location. Please remove them before deleting the location.', 'danger')
            return redirect(url_for('view_locations'))

        # If no staff profiles are found, delete the location
        cursor.execute("DELETE FROM Locations WHERE LocationID = %s", (location_id,))
        connection.commit()
        flash('Location deleted successfully.', 'success')
    except Exception as e:
        print(e)
        flash('An error occurred while deleting the location.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('view_locations'))

@app.route('/view_credit_requests')
@require_role(3)
def view_credit_requests():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    locationId = session['locationid']
    roleId  = session['role']
    if roleId == 4:
        query = """
            SELECT c.RequestID, c.UserID, u.Email, cp.FirstName, cp.LastName, 
                c.RequestedAmount, c.Reason, c.Status, c.RequestTime
            FROM CreditIncreaseRequests c
            JOIN Users u ON c.UserID = u.UserID
            JOIN CustomerProfile cp ON c.UserID = cp.UserID
            WHERE c.Status = 'Pending'
        """
        params = ()
    else:  # Role is 3
        query = """
            SELECT c.RequestID, c.UserID, u.Email, cp.FirstName, cp.LastName, 
                c.RequestedAmount, c.Reason, c.Status, c.RequestTime
            FROM CreditIncreaseRequests c
            JOIN Users u ON c.UserID = u.UserID
            JOIN CustomerProfile cp ON c.UserID = cp.UserID
            WHERE c.Status = 'Pending' AND cp.LocationID = %s
        """
        params = (locationId,)
        
    cursor.execute(query, params)

    credit_requests = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return render_template('manager/view_credit_requests.html', credit_requests=credit_requests)

@app.route('/approve_credit_request/<int:request_id>', methods=['POST'])
@require_role(3)
def approve_credit_request(request_id):
    
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    # Fetch the request details to update the AccountHolders table
    cursor.execute("SELECT UserID, RequestedAmount FROM CreditIncreaseRequests WHERE RequestID = %s", (request_id,))
    request = cursor.fetchone()
    if not request:
        flash('Request not found.', 'danger')
        return redirect(url_for('view_credit_requests'))
    
    user_id = request['UserID']
    requested_amount = request['RequestedAmount']
    
    cursor.execute("""
        UPDATE AccountHolders
        SET CreditLimit = CreditLimit + %s, RemainingCredit = RemainingCredit + %s
        WHERE UserID = %s
    """, (requested_amount, requested_amount, user_id))
    
    cursor.execute("""
        UPDATE CreditIncreaseRequests
        SET Status = 'Approved'
        WHERE RequestID = %s
    """, (request_id,))
    
    connection.commit()
    cursor.close()
    connection.close()
    flash('Credit limit increase request approved.', 'success')
    return redirect(url_for('view_credit_requests'))

@app.route('/reject_credit_request/<int:request_id>', methods=['POST'])
@require_role(3)
def reject_credit_request(request_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        UPDATE CreditIncreaseRequests
        SET Status = 'Rejected'
        WHERE RequestID = %s
    """, (request_id,))
    
    connection.commit()
    cursor.close()
    connection.close()
    flash('Credit limit increase request rejected.', 'info')
    return redirect(url_for('view_credit_requests'))

@app.route('/manage_credit_limits')
@require_role(3)
def manage_credit_limits():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT ah.UserID, ah.BusinessName, ah.CreditLimit, ah.RemainingCredit, cp.FirstName, cp.LastName, u.Email
        FROM AccountHolders ah
        JOIN CustomerProfile cp ON ah.UserID = cp.UserID
        JOIN Users u ON ah.UserID = u.UserID
        WHERE ah.ApplicationStatus = 'Approved'
    """)
    account_holders = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('manager/manage_credit_limits.html', account_holders=account_holders)

@app.route('/edit_credit_limit/<int:user_id>', methods=['GET', 'POST'])
@require_role(4)
def edit_credit_limit(user_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        new_credit_limit = request.form.get('credit_limit')
        new_remaining_credit = request.form.get('remaining_credit')

        cursor.execute("""
            UPDATE AccountHolders
            SET CreditLimit = %s, RemainingCredit = %s
            WHERE UserID = %s
        """, (new_credit_limit, new_remaining_credit, user_id))
        connection.commit()
        flash('Credit limit updated successfully.', 'success')
        return redirect(url_for('manage_credit_limits'))

    cursor.execute("""
        SELECT ah.UserID, ah.BusinessName, ah.CreditLimit, ah.RemainingCredit, cp.FirstName, cp.LastName, u.Email
        FROM AccountHolders ah
        JOIN CustomerProfile cp ON ah.UserID = cp.UserID
        JOIN Users u ON ah.UserID = u.UserID
        WHERE ah.UserID = %s
    """, (user_id,))
    account_holder = cursor.fetchone()
    cursor.close()
    connection.close()

    return render_template('manager/edit_credit_limit.html', account_holder=account_holder)


def generate_invoices_function():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    today = datetime.today()
    first_day_of_month = today.replace(day=1)
    
    try:
        # Get all account holders
        cursor.execute("SELECT UserID FROM AccountHolders WHERE ApplicationStatus = 'Approved'")
        account_holders = cursor.fetchall()
        
        if not account_holders:
            return False, 'No account holders found.'

        for account_holder in account_holders:
            user_id = account_holder['UserID']
            
            # Calculate total amount and GST for the current month, including shipping price
            cursor.execute("""
                SELECT SUM(TotalPrice) AS TotalAmount, SUM(ShippingPrice) AS ShippingPrice
                FROM Orders
                WHERE UserID = %s AND DateOrdered BETWEEN %s AND %s
            """, (user_id, first_day_of_month, today))
            total_amount_result = cursor.fetchone()
            total_amount = total_amount_result['TotalAmount'] or Decimal('0.00')
            shipping_price = total_amount_result['ShippingPrice'] or Decimal('0.00')
            
            gst_rate = Decimal('0.15')
            gst_amount = total_amount * gst_rate  # Assuming 15% GST
            
            total_amount_with_gst = total_amount + gst_amount
            due_date = today + timedelta(days=30)  # Payment due in 30 days
            
            # Insert invoice
            cursor.execute("""
                INSERT INTO Invoices (UserID, InvoiceDate, DueDate, TotalAmount, GSTAmount, ShippingPrice, Status)
                VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
            """, (user_id, today, due_date, total_amount_with_gst, gst_amount, shipping_price))
            connection.commit()
            invoice_id = cursor.lastrowid
            
            # Get order details for the invoice items
            cursor.execute("""
                SELECT p.Name, oi.Quantity, oi.UnitPrice, (oi.Quantity * oi.UnitPrice) AS TotalPrice
                FROM OrderItems oi
                JOIN Products p ON oi.ProductID = p.ProductID
                WHERE oi.OrderID IN (
                    SELECT OrderID
                    FROM Orders
                    WHERE UserID = %s AND DateOrdered BETWEEN %s AND %s
                )
            """, (user_id, first_day_of_month, today))
            order_items = cursor.fetchall()
            
            # Insert invoice items
            for item in order_items:
                cursor.execute("""
                    INSERT INTO InvoiceItems (InvoiceID, Description, Quantity, UnitPrice, TotalPrice)
                    VALUES (%s, %s, %s, %s, %s)
                """, (invoice_id, item['Name'], item['Quantity'], item['UnitPrice'], item['TotalPrice']))
            
            connection.commit()
        
        return True, 'Invoices generated successfully.'
    except Exception as e:
        connection.rollback()
        print("Error occurred:", e)
        return False, 'An error occurred while generating invoices.'
    finally:
        cursor.close()
        connection.close()
 
@app.route('/generate_invoices', methods=['POST'])
@require_role(4)
def generate_invoices_route():
    success, message = generate_invoices_function()
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('all_invoices'))

@app.route('/all_invoices', methods=['GET', 'POST'])
@require_role(4)
def all_invoices():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    # Get search parameters from request
    email_search = request.form.get('email_search')
    status_search = request.form.get('status_search')

    # Build the base query
    query = """
        SELECT i.InvoiceID, i.InvoiceDate, i.DueDate, i.TotalAmount, i.GSTAmount, i.Status, u.Email
        FROM Invoices i
        JOIN Users u ON i.UserID = u.UserID
        WHERE 1=1
    """

    # Add conditions based on search parameters
    params = []
    if email_search:
        query += " AND u.Email LIKE %s"
        params.append(f"%{email_search}%")
    if status_search:
        query += " AND i.Status = %s"
        params.append(status_search)
    
    query += " ORDER BY i.InvoiceDate DESC"

    cursor.execute(query, params)
    invoices = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('manager/all_invoices.html', invoices=invoices, email_search=email_search, status_search=status_search)



@app.route('/invoice_details_manager/<int:invoice_id>')
@require_role(3)
def invoice_details_manager(invoice_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT i.InvoiceID, i.InvoiceDate, i.DueDate, i.TotalAmount, i.GSTAmount, i.ShippingPrice, i.Status,
               ii.Description, ii.Quantity, ii.UnitPrice, ii.TotalPrice, u.Email
        FROM Invoices i
        LEFT JOIN InvoiceItems ii ON i.InvoiceID = ii.InvoiceID
        JOIN Users u ON i.UserID = u.UserID
        WHERE i.InvoiceID = %s
    """, (invoice_id,))
    invoice = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    if not invoice:
        flash('Invoice not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('all_invoices'))
    
    return render_template('manager/invoice_details_manager.html', invoice=invoice, format_nz_currency = format_nz_currency)

@app.route('/categories')
@require_role(4)
def view_categories():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Categories")
    categories = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('manager/view_categories.html', categories=categories)

@app.route('/add_category', methods=['GET', 'POST'])
@require_role(4)
def add_category():
    if request.method == 'POST':
        name = request.form['name']

        connection = getDbConnection()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO Categories (Name) VALUES (%s)", (name,))
            connection.commit()
            flash('Category added successfully.', 'success')
            return redirect(url_for('view_categories'))
        except Exception as e:
            print(e)
            flash('An error occurred while adding the category.', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('manager/add_category.html')

@app.route('/edit_category/<int:category_id>', methods=['GET', 'POST'])
@require_role(4)
def edit_category(category_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        try:
            cursor.execute("UPDATE Categories SET Name = %s WHERE CategoryID = %s", (name, category_id))
            connection.commit()
            flash('Category updated successfully.', 'success')
            return redirect(url_for('view_categories'))
        except Exception as e:
            print(e)
            flash('An error occurred while updating the category.', 'danger')
        finally:
            cursor.close()
            connection.close()
    else:
        cursor.execute("SELECT * FROM Categories WHERE CategoryID = %s", (category_id,))
        category = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('manager/edit_category.html', category=category)

@app.route('/delete_category/<int:category_id>', methods=['POST'])
@require_role(4)
def delete_category(category_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM Categories WHERE CategoryID = %s", (category_id,))
        connection.commit()
        flash('Category deleted successfully.', 'success')
    except Exception as e:
        print(e)
        flash('You cannot delete this category unless you remove all the products from this category first', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('view_categories'))

@app.route('/units')
@require_role(4)
def view_units():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Units")
    units = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('manager/view_units.html', units=units)

@app.route('/add_unit', methods=['GET', 'POST'])
@require_role(4)
def add_unit():
    if request.method == 'POST':
        name = request.form['name']

        connection = getDbConnection()
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO Units (Name) VALUES (%s)", (name,))
            connection.commit()
            flash('Unit added successfully.', 'success')
            return redirect(url_for('view_units'))
        except Exception as e:
            print(e)
            flash('An error occurred while adding the unit.', 'danger')
        finally:
            cursor.close()
            connection.close()

    return render_template('manager/add_unit.html')

@app.route('/edit_unit/<int:unit_id>', methods=['GET', 'POST'])
@require_role(4)
def edit_unit(unit_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        try:
            cursor.execute("UPDATE Units SET Name = %s WHERE UnitID = %s", (name, unit_id))
            connection.commit()
            flash('Unit updated successfully.', 'success')
            return redirect(url_for('view_units'))
        except Exception as e:
            print(e)
            flash('An error occurred while updating the unit.', 'danger')
        finally:
            cursor.close()
            connection.close()
    else:
        cursor.execute("SELECT * FROM Units WHERE UnitID = %s", (unit_id,))
        unit = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('manager/edit_unit.html', unit=unit)

@app.route('/delete_unit/<int:unit_id>', methods=['POST'])
@require_role(4)
def delete_unit(unit_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Check if there are any products associated with this unit
        cursor.execute("SELECT * FROM Products WHERE UnitID = %s", (unit_id,))
        products = cursor.fetchall()
        if products:
            flash('There are still products associated with this unit. Please remove them before deleting the unit.', 'danger')
            return redirect(url_for('view_units'))

        # If no products are found, delete the unit
        cursor.execute("DELETE FROM Units WHERE UnitID = %s", (unit_id,))
        connection.commit()
        flash('Unit deleted successfully.', 'success')
    except Exception as e:
        print(e)
        flash('An error occurred while deleting the unit.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('view_units'))

@app.route('/editnews/<int:id>', methods = ['GET','POST'])
def editnews(id):
    if request.method == 'GET':
        cursor = getCursor()
        cursor.execute('SELECT * FROM News WHERE NewsID = %s', (id,))
        news = cursor.fetchone()
        cursor.fetchall()
        cursor.execute('SELECT * FROM Locations')
        locations = cursor.fetchall()
        return render_template('manager/editnews.html', news = news, locations=locations)
    else:
        newstype = request.form['newstype']
        title = request.form['title']
        message = request.form['message']
        date = datetime.now()
        ExpirationDate = request.form['date']
        if session['role'] == 3:
            LocationID = session['locationid']
        else:
            LocationID = request.form['location']
            if LocationID == "NULL":
                LocationID = None

        cursor = getCursor()
        cursor.execute('UPDATE News SET NewsType = %s, Title = %s, Message = %s, DateCreated = %s, ExpirationDate = %s, LocationID = %s WHERE NewsID = %s', \
                       (newstype,title,message,date,ExpirationDate,LocationID,id,))
        return redirect(url_for('news', newstype = newstype))

@app.route('/deletenews/<newstype>/<int:id>')
def deletenews(newstype,id):
    cursor = getCursor()
    cursor.execute('DELETE FROM News WHERE NewsID = %s', (id,))
    return redirect(url_for('news', newstype = newstype))

@app.route('/addnews/<newstype>', methods = ['GET','POST'])
def addnews(newstype):
    if request.method == 'GET':

        if session['role'] == 4:
            cursor = getCursor()
            cursor.execute('SELECT * FROM Locations')
            locations = cursor.fetchall()
            return render_template('manager/addnews.html', newstype = newstype, locations = locations)
        else:
            return render_template('manager/addnews.html', newstype = newstype)
    else:
        newstype = request.form['newstype']
        title = request.form['title']
        message = request.form['message']
        date = request.form['date']
        if session['role'] == 3:
            locationId = session['locationid']
        else:

            locationId = request.form['location']
            if locationId == "NULL":
                locationId = None
        cursor = getCursor()
        cursor.execute('INSERT INTO News (NewsType, Title, Message, ExpirationDate, LocationID) VALUES ( %s, %s, %s, %s, %s)', \
                       (newstype,title,message,date,locationId,))
        return redirect(url_for('news', newstype = newstype))    
    
@app.route('/giftcard')
def giftcard():
    balance = request.args.get('balance', None)
    code = request.args.get('code', None)
    cursor = getCursor()
    cursor.execute('SELECT * FROM GiftCardOption')
    giftcard = cursor.fetchall()
    return render_template('manager/view_giftcard.html',giftcard=giftcard, balance = balance, code = code)

@app.route('/addgiftcard', methods = ['GET','POST'])
def addgiftcard():
    if request.method == 'GET':
        return render_template('manager/addgiftcard.html')
    else:
         # Save the uploaded file
        file = request.files['photo']
        global dir_path
        img_folder = dir_path + "/static/Images/"
        file.save(os.path.join(img_folder, file.filename))
        name = request.form.get('name')
        value =float(request.form.get('value', 2)) 
        imageURL = file.filename
        cursor = getCursor()
        cursor.execute("INSERT INTO GiftCardOption(GiftCardName, Value, Image) VALUES (%s,%s,%s)",(name,value,imageURL))
        flash('Gift card has been added',"success")
        return redirect('/giftcard')

@app.route('/deletegiftcard/<int:giftcardoptionid>')
def deletegiftcard(giftcardoptionid):
    cursor = getCursor()
    cursor.execute('SELECT * FROM GiftCardOption WHERE GiftCardOptionID = %s',(giftcardoptionid,))
    gc = cursor.fetchone()
    cursor1 = getCursor()
    cursor1.execute('DELETE FROM GiftCardOption WHERE GiftCardOptionID = %s',(giftcardoptionid,))
    img_folder = dir_path + "/static/Images/"
    image_path = os.path.join(img_folder, gc[3])
    os.remove(image_path)
    flash('Gift card has been deleted',"success")
    return redirect('/giftcard')    

@app.route('/editgiftcard/<int:giftcardoptionid>', methods = ['GET','POST'])
def editgiftcard(giftcardoptionid):
    cursor = getCursor()
    cursor.execute('SELECT * FROM GiftCardOption WHERE GiftCardOptionID = %s', (giftcardoptionid,) )
    gc = cursor.fetchone()
    if request.method == 'GET':
        return render_template('manager/editgiftcard.html', gc=gc)
    else:
         # Save the uploaded file
        file = request.files['photo']
        if file:              
            img_folder = dir_path + "/static/Images/"
            file.save(os.path.join(img_folder, file.filename))
            imageURL = file.filename
        else:
            imageURL = gc[3]

        name = request.form.get('name')
        value =float(request.form.get('value', 2)) 
        cursor = getCursor()
        cursor.execute("UPDATE GiftCardOption SET GiftCardName = %s, Value = %s, Image = %s WHERE GiftCardOptionID = %s",(name,value,imageURL,giftcardoptionid, ))
        flash('Gift card has been updated',"success")
        return redirect('/giftcard')
    


@app.route('/checkgcbalance', methods=['POST'])
def checkgcbalance():
    gc = request.form['gccode']
    cursor = getCursor()
    cursor.execute('SELECT Balance FROM GiftCards WHERE CardNumber = %s', (gc,))
    detail = cursor.fetchone()
    cursor.close()
    if detail:
        balance = detail[0]
        return redirect(url_for('giftcard', code = gc, balance = balance))
    else:
        flash('Invalid Gift Card Number', 'warning')
        return redirect('/giftcard')

@app.route('/manage_boxes')
@require_role(3)
def manage_boxes():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Boxes")
    boxes = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('manager/manage_boxes.html', boxes=boxes, format_nz_currency=format_nz_currency)

@app.route('/add_box', methods=['POST'])
@require_role(3)
def add_box():
    name = request.form['name']
    type = request.form['type']
    size = request.form['size']
    price = request.form['price']
    contentsDescription = request.form['contentsDescription']
    if type == "Vegetable":
        image = "box-1.jpg"
    elif type == "Fruit":
        image = "box-2.jpg"
    else:
        image = "box-3.jpg"
    connection = getDbConnection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO Boxes (Name, Type, Size, Price, ContentsDescription, ImageURL)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, type, size, price, contentsDescription,image))
    connection.commit()
    cursor.close()
    connection.close()
    flash('New box added successfully.', "success")
    return redirect(url_for('manage_boxes'))

@app.route('/delete_box', methods=['POST'])
@require_role(3)
def delete_box():
    box_id = request.form['box_id']
    
    connection = getDbConnection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("DELETE FROM Boxes WHERE BoxID = %s", (box_id,))
        connection.commit()
        flash('Box deleted successfully.',"success")
    except IntegrityError as e:
        if e.errno == 1451:  # Foreign key constraint error
            flash('You cannot delete this box because it still has contents inside.', "danger")
        else:
            flash('An error occurred while trying to delete the box.',"danger")
    finally:
        cursor.close()
        connection.close()
    
    return redirect(url_for('manage_boxes'))

@app.route('/box/<int:box_id>/contents')
@require_role(3)
def view_box_contents(box_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT bc.BoxContentID, p.Name, p.UnitID, u.Name as UnitName, bc.Quantity
        FROM BoxContents bc
        JOIN Products p ON bc.ProductID = p.ProductID
        JOIN Units u ON p.UnitID = u.UnitID
        WHERE bc.BoxID = %s
    """, (box_id,))
    box_contents = cursor.fetchall()
    cursor.execute("SELECT * FROM Boxes WHERE BoxID = %s", (box_id,))
    box = cursor.fetchone()
    cursor.close()
    connection.close()
    return render_template('manager/view_box_contents.html', box=box, box_contents=box_contents)

@app.route('/box/<int:box_id>/add_product', methods=['GET', 'POST'])
@require_role(3)
def add_product_to_box(box_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        cursor.execute("INSERT INTO BoxContents (BoxID, ProductID, Quantity) VALUES (%s, %s, %s)", (box_id, product_id, quantity))
        connection.commit()
        flash('Product added to box successfully.',"success")
        return redirect(url_for('view_box_contents', box_id=box_id))
    cursor.execute("""
        SELECT p.ProductID, p.Name, u.Name as UnitName
        FROM Products p
        JOIN Units u ON p.UnitID = u.UnitID
    """)
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('manager/add_product_to_box.html', box_id=box_id, products=products)

@app.route('/box/<int:box_id>/remove_product/<int:box_content_id>', methods=['POST'])
@require_role(3)
def remove_product_from_box(box_id, box_content_id):
    connection = getDbConnection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM BoxContents WHERE BoxContentID = %s", (box_content_id,))
    connection.commit()
    cursor.close()
    connection.close()
    flash('Product removed from box successfully.',"success")
    return redirect(url_for('view_box_contents', box_id=box_id))

@app.route('/box/<int:box_id>/edit_product/<int:box_content_id>', methods=['GET', 'POST'])
@require_role(3)
def edit_product_in_box(box_id, box_content_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    if request.method == 'POST':
        quantity = request.form['quantity']
        cursor.execute("UPDATE BoxContents SET Quantity = %s WHERE BoxContentID = %s", (quantity, box_content_id))
        connection.commit()
        flash('Product quantity updated successfully.', "success")
        return redirect(url_for('view_box_contents', box_id=box_id))
    cursor.execute("SELECT * FROM BoxContents WHERE BoxContentID = %s", (box_content_id,))
    box_content = cursor.fetchone()
    cursor.execute("""
        SELECT p.ProductID, p.Name, u.Name as UnitName
        FROM Products p
        JOIN Units u ON p.UnitID = u.UnitID
        WHERE p.ProductID = %s
    """, (box_content['ProductID'],))
    product = cursor.fetchone()
    cursor.close()
    connection.close()
    return render_template('manager/edit_product_in_box.html', box_content=box_content, product=product)

# Reports
@app.route('/management_reports', methods=['GET', 'POST'])
@require_role(4)
def management_reports():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        print(start_date)
        print(end_date)
        # Fetch sales trends data
        cursor.execute("""
            SELECT DATE(DateOrdered) as OrderDate, SUM(TotalPrice) as TotalSales
            FROM Orders
            WHERE DateOrdered BETWEEN %s AND %s
            GROUP BY DATE(DateOrdered)
            ORDER BY OrderDate
        """, (start_date, end_date))
        sales_trends = cursor.fetchall()

        # Fetch popular products data
        cursor.execute("""
            SELECT Products.Name, SUM(OrderItems.Quantity) as TotalSold
            FROM OrderItems
            JOIN Products ON OrderItems.ProductID = Products.ProductID
            JOIN Orders ON OrderItems.OrderID = Orders.OrderID
            WHERE Orders.DateOrdered BETWEEN %s AND %s
            GROUP BY Products.Name
            ORDER BY TotalSold DESC
        """, (start_date, end_date))

        popular_products = cursor.fetchall()


        # Fetch location orders data
        cursor.execute("""
            SELECT Locations.Name AS LocationName, COUNT(Orders.OrderID) as OrderCount
            FROM Orders
            LEFT JOIN Locations ON Orders.LocationID = Locations.LocationID
            WHERE Orders.DateOrdered BETWEEN %s AND %s
            GROUP BY Locations.Name
            ORDER BY OrderCount DESC
        """, (start_date, end_date))
        location_orders = cursor.fetchall()

        print(popular_products)
        cursor.close()
        connection.close()

        return render_template('manager/management_reports.html',
                               sales_trends=sales_trends,
                               popular_products=popular_products,
                               location_orders=location_orders,
                               start_date=start_date,
                               end_date=end_date)

    return render_template('manager/management_reports.html')


@app.route('/viewallgc')
def viewallgc():
    cursor = getCursor()
    cursor.execute('SELECT GiftCardID,CardNumber, Balance,GiftCardName, Name, Address, dateCreated FROM GiftCards LEFT JOIN GiftCardOption ON Type = GiftCardOptionID  ')
    allgc = cursor.fetchall()
    return render_template('manager/view_allgiftcards.html', allgc = allgc)

@app.route('/points_transactions')
@require_role(3)  # Assuming role 3 or higher can view points transactions
def points_transactions():
    email = request.args.get('email')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT pt.TransactionID, u.Email, pt.OrderID, pt.PointsEarned, pt.TransactionDate
        FROM PointsTransactions pt
        JOIN Users u ON pt.UserID = u.UserID
    """
    params = []
    
    if email:
        query += " WHERE u.Email LIKE %s"
        params.append(f"%{email}%")
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('manager/points_transactions.html', transactions=transactions, format_date = format_date)

@app.route('/EditAccountHolder/<int:id>', methods = ["GET","POST"])
@require_role(4)
def EditAccountHolder(id):
    if request.method == "GET":
        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM AccountHolders a LEFT JOIN CustomerProfile c on c.UserID = a.UserID WHERE a.AccountHolderID = %s', (id,))
        account_holder = cursor.fetchone()
        return render_template('manager/edit_accountholder.html', id = id, account_holder = account_holder)
    
    if request.method == "POST":
        name = request.form['BusinessName']
        address = request.form['BusinessAddress']
        contact_number = request.form['BusinessContactNumber']
        invoice_due_date = request.form['InvoiceDueDate']
        application_status = request.form['ApplicationStatus']

        cursor = getCursor()
        cursor.execute("UPDATE AccountHolders SET BusinessName = %s, BusinessAddress = %s, BusinessContactNumber = %s,\
                InvoiceDueDate = %s, ApplicationStatus = %s \
            WHERE AccountHolderID = %s ", (name, address, contact_number, invoice_due_date, application_status, id))
        flash("Account Holder Information has been updated", "success")
        return redirect("/view_applications")


@app.route('/DeleteAccountHolder/<int:id>', methods = ["POST"])
@require_role(4)
def DeleteAccountHolder(id):
    if request.method == "POST":
        cursor = getCursor()
        cursor.execute('DELETE FROM AccountHolders WHERE AccountHolderID = %s', (id,))
        return redirect("/view_applications")

@app.route('/editboxinfo/<int:id>', methods = ["GET", "POST"])
@require_role(3)
def editboxinfo(id):
    if request.method == "GET":
        cursor = getCursor()
        cursor.execute("SELECT * FROM Boxes WHERE BoxID = %s", (id,))
        box = cursor.fetchone()
        return render_template('manager/edit_box.html', box = box)
    else:
        name = request.form['name']
        type = request.form['type']
        size = request.form['size']
        price = request.form['price']
        contentsDescription = request.form['contentsDescription']
        cursor = getCursor()
        cursor.execute('UPDATE Boxes SET Name = %s, Type = %s, Size = %s, Price = %s, ContentsDescription = %s WHERE BoxID = %s', \
                       (name, type, size,price,contentsDescription, id,))
        flash("Box information has been updated", "success")
        return redirect("/manage_boxes")