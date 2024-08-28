from datetime import datetime
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
from .views_customer import update_subscription
from app.views_customer import get_application_status
from app.config.models import validate_phone
from app.config.helpers import format_date


hashing = Hashing(app)
app.secret_key = 'comp639groupAX'

@app.route('/')
@app.route('/home')
def home():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Products where CategoryID = 1 order by name ')
    fruitList = cursor.fetchall()
    cursor.execute('SELECT * FROM Products where CategoryID = 2 order by name ')
    vegList = cursor.fetchall()
   
    cursor.execute("""SELECT * FROM News WHERE NewsType = 'General' and LocationID is NULL ORDER BY DateCreated desc""")
    newslist = cursor.fetchall()
    current_url = '/'
    return render_template('home.html', fruitList=fruitList, vegList=vegList,format_nz_currency=format_nz_currency, current_url = current_url,newslist=newslist )

@app.route('/login/' , methods=['GET', 'POST'])
def login():
    msg=""
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = (request.form['username'])
        user_password = request.form['password']
        # Check if account exists using MySQL
        cursor = getCursor()
        cursor.execute('SELECT u.UserID, Email, Password, RoleID, FirstName, LastName, f.LocationID, l.Name FROM Users as u LEFT JOIN \
                        (select UserID, FirstName, LastName, LocationID from CustomerProfile as c \
                         union ( select UserID, FirstName, LastName, LocationID from StaffProfile)) AS f \
                        ON f.UserID = u.UserID \
                        inner join Locations l on l.LocationID = f.LocationID  \
                       WHERE Email = %s', (username.lower(),))
        # Fetch one record and return result/list-inquiry
        account = cursor.fetchone()
        # cursor.fetchall()
        if account is not None:
            password = account[2]
            if hashing.check_value(password, user_password, salt='comp'):
            # If account exists in accounts table 
            # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account[0]
                session['username'] = account[1]
                session['role'] = account[3]
                session['name'] = account[4]
                session['locationid'] = account[6]
                session['locationname'] = account[7]
                
                if session['role'] != 1:
                    cursor.execute('SELECT * FROM StaffProfile WHERE UserID = %s', (session['id'],))
                    sp = cursor.fetchone()
                    if sp[8] == 'Inactive':
                        flash("Your account has been disabled. Please contact admin", "danger")
                        session.pop('loggedin', None)
                        session.pop('id', None)
                        session.pop('username', None)
                        session.pop('role', None)
                        session.pop('name', None)
                        session.pop('locationid', None)
                        return render_template('login.html')

                # Retrieve application status from the database
                application_status = get_application_status(account[0])
                session['ApplicationStatus'] = application_status

                # Redirect to home page
                if session['role'] == 1:
                    return redirect('/customer')
                elif session['role'] == 2:
                     
                     return redirect('/staff')
                elif session['role'] == 3:
                     return redirect('/localmanager')
                else: 
                   return redirect('/nationalmanager')
            else:
                #password incorrect
                msg = 'Incorrect password.'
        else:
            # Account doesnt exist or username incorrect
            msg = 'Incorrect username.'
    # Show the login form with message (if any)

    return render_template('login.html', msg = msg)

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   session.pop('role', None)
   session.pop('name', None)
   session.pop('locationid', None)
   
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    connection = getDbConnection()
    if request.method == 'POST':
        username = request.form.get('username')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        password = request.form.get('password')
        locationid = request.form.get('location')
        address = request.form.get('address')
        phone = request.form.get('phonenumber')
  
        # Check if the email already exists in the database
        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE Email = %s", (username,))
        user = cursor.fetchone()
        if user:
            flash("Email already exists. Please choose a different email address.")
            return redirect('/register')
        else:
            cursor1 = getCursor()
            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            hashed = hashing.hash_value(password, salt='comp')
            cursor1.execute('INSERT INTO Users(Email, Password, RoleID) VALUES ( %s, %s, %s);', (username, hashed, 1,))
            cursor1.execute('SELECT UserID FROM Users WHERE Email = %s;', (username,))
            userID = cursor1.fetchone()[0]

            cursor1.execute('SELECT * FROM Locations WHERE LocationID = %s;', (locationid,)) 
            location_name = cursor1.fetchone()[1]          
            cursor1.execute('INSERT INTO CustomerProfile(UserID, FirstName, LastName, Location, LocationID, Address, Phone) VALUES( %s, %s, %s, %s, %s, %s, %s);', \
                            (userID, firstname, lastname,location_name, locationid, address, phone))
            connection.commit()
            cursor1.close()
            flash("Thanks! You have been registered.")
            return redirect('/login')

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT LocationID, Name FROM Locations")
    locations = cursor.fetchall()
    cursor.close()
    return render_template('register.html', locations=locations)
@app.route('/news/<int:id>', methods = ['GET'])
def viewNews(id):
    if request.method == 'GET':
        cursor = getCursor()
        cursor.execute('SELECT * FROM News WHERE NewsID = %s', (id,))
        news = cursor.fetchone()
        return render_template('all/news_details.html', news = news)

@app.route('/products')
def list_products():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Categories')
    categories = cursor.fetchall()

    query = "SELECT * FROM Products"
    params = []
    name = request.args.get('name')
    category_id = request.args.get('category')
    conditions = []

    if name:
        conditions.append("Name LIKE %s")
        params.append("%" + name + "%")
    if category_id and category_id.strip():  # Ensure category_id is not empty
        conditions.append("CategoryID = %s")
        params.append(category_id)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    products = cursor.fetchall()
    connection.close()

    return render_template('list_products.html', products=products, categories=categories, format_nz_currency=format_nz_currency)

@app.route('/customer')
@require_role(1)
def customer_dashboard():
    user_id = session.get('id')
    account_status = None
    points = {'CurrentPoints': 0}  # Default to 0 if no points found
    news = []

    if user_id:
        try:
            with getDbConnection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    # Fetch account holder application status
                    cursor.execute("SELECT ApplicationStatus FROM AccountHolders WHERE UserID = %s", (user_id,))
                    result = cursor.fetchone()
                    if result:
                        account_status = result['ApplicationStatus']
                    
                    # Ensure any remaining results are read
                    cursor.fetchall()

                    # Fetch the latest news
                    today = datetime.now().date()
                    cursor.execute("SELECT * FROM News WHERE ExpirationDate >= %s ORDER BY DateCreated DESC", (today,))
                    news = cursor.fetchall()

                    # Fetch current points
                    cursor.execute("SELECT CurrentPoints FROM Points WHERE UserID = %s", (user_id,))
                    points_result = cursor.fetchone()
                    if points_result:
                        points['CurrentPoints'] = points_result['CurrentPoints']
                    
                    # Ensure any remaining results are read
                    cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching application status or points: {e}", 'danger')

    return render_template('dashboard/customer_dashboard.html', account_status=account_status, news=news, points=points)


@app.route('/staff')
@require_role(2)
def staff_dashboard():
    update_subscription()
    cursor = getCursor()
    today = datetime.now().date()
    cursor.execute("SELECT * FROM News WHERE ExpirationDate >= %s and (LocationID = %s OR LocationID is NULL) ORDER BY DateCreated desc",(today, session.get('locationid')))
    news = cursor.fetchall()
    return render_template('dashboard/staff_dashboard.html', news=news)

@app.route('/localmanager')
@require_role(3)
def localmanager_dashboard():
    return render_template('dashboard/localmanager_dashboard.html')

@app.route('/nationalmanager')
@require_role(4)
def nationalmanager_dashboard():
    return render_template('dashboard/nationalmanager_dashboard.html')

### profile displayed 
@app.route('/profile')
def profile():
    # userID = session.get('userID')
    cur = getCursor()
    userID = session.get('id')
    # get profile
    cur.execute("select * FROM CustomerProfile where UserID = %s;",(userID,))
    profile_customer = cur.fetchone()
    if not profile_customer:
        cur.execute("select * FROM StaffProfile where UserID = %s;",(userID,))
        profile_staff = cur.fetchone()
    else:
        profile_staff = None
    return render_template('profile.html', profile_customer = profile_customer, profile_staff = profile_staff)

### update info
@app.route('/update_info/<int:userID>', methods=['GET', 'POST'])
def update_info(userID):
    cur = getCursor()
    role = session.get('role')
    session_userID = session.get('id')
## update customer's info
    if role == 1:
        cur.execute("select * FROM CustomerProfile where UserID = %s;",(userID,))
        profile = cur.fetchone()
        location = profile[3]
        if request.method == 'POST':
            first_name = request.form.get('firstname','')
            last_name = request.form.get('lastname','')
            address = request.form.get('address','')
            phone = request.form.get('phone','')
            location = request.form.get('location','')
            #validation
            pattern = re.compile("^[A-Za-z]+$")
            if pattern.match(first_name) and\
                pattern.match(last_name) and \
                validate_phone(phone):
                flash('Information Updated','success')
                ## update database
                cur.execute("UPDATE CustomerProfile SET FirstName = %s, LastName = %s, Location = %s, Address = %s, Phone = %s WHERE UserID = %s", (first_name, last_name, location, address, phone, userID))
                return redirect(url_for('profile'))
            else:
                flash('Please make sure your inputs for names are only letters and phone numbers between 9 to 11 digits','danger')
                return render_template('updateinfo.html', profile = profile, role = role, userID = userID, location = location)
        else:
            return render_template('updateinfo.html', profile = profile, role = role, userID = userID, location = location)
            

    elif role == 2:
        ## update staff's info
        cur.execute("select * FROM StaffProfile where UserID = %s;",(userID,))
        profile = cur.fetchone()
        location = profile[5]
        if request.method == 'POST':
            first_name = request.form.get('firstname','')
            last_name = request.form.get('lastname','')
            phone = request.form.get('phone','')
            pattern = re.compile("^[A-Za-z]+$")
            location = request.form.get('location','')
            if not location:
                location = profile[5]
            #validation
            if pattern.match(first_name) and \
                pattern.match(last_name) and \
                   validate_phone(phone):
                flash('Information Updated','success')
                ## update database
                cur.execute("UPDATE StaffProfile SET FirstName = %s, LastName = %s, Phone = %s WHERE UserID = %s", (first_name, last_name, phone, userID))
                return redirect(url_for('profile'))
            else:
                flash('Please make sure your inputs for names are only letters and phone numbers between 9 to 11 digits','danger')
                return render_template('updateinfo.html', profile = profile, role = role, userID = userID)

        else:
            return render_template('updateinfo.html', profile = profile, role = role, userID = userID)
        
    else:


        # updated by managers
        cur.execute("select * FROM StaffProfile where UserID = %s;",(userID,))
        profile = cur.fetchone()
        location = profile[5]
        if request.method == 'POST':
            first_name = request.form.get('firstname','')
            last_name = request.form.get('lastname','')
            phone = request.form.get('phone','')
            location = request.form.get('location','')
            if not location:
                location = profile[5]
            position = request.form.get('position','')
            if not position:
                position = profile[7]
            #validation
            pattern = re.compile("^[A-Za-z]+$")
            if pattern.match(first_name) and \
                pattern.match(last_name) and \
                validate_phone(phone):
                 
                flash('Information Updated','success')
                ## update database
                cur.execute("UPDATE StaffProfile SET FirstName = %s, LastName = %s, Phone = %s, Location = %s, Department = %s WHERE UserID = %s", (first_name, last_name, phone, location, position, userID))
                if userID == session_userID:
                    return redirect(url_for('profile'))
                elif role == 3:
                    return redirect(url_for('stafflist'))
                else:
                    return redirect(url_for('all_stafflist'))
            else:
                flash('Please make sure your inputs for names are only letters and phone numbers between 9 to 11 digits','danger')
                return render_template('updateinfo.html', profile = profile, role = role, userID = userID)

        else:
            return render_template('updateinfo.html', profile = profile, role = role, userID = userID)
        


## update pwd
@app.route('/update_pwd/<int:userID>', methods=['GET', 'POST'])
def update_pwd(userID):
    msg=""
    if request.method =='POST':
        
        current_pwd = request.form.get('currentpwd')
        new_pwd = request.form.get('newpwd')
        pwd_check = request.form.get('pwd_check')
        # using session to get username to check current pwd in sql
        userID = session.get('id')
        cur = getCursor()
        cur.execute("Select * FROM Users WHERE userID = %s;", (userID,))
        account = cur.fetchone()
     # check if the current pwd matches with the pwd in database
        hashed_password = hashing.hash_value(current_pwd, salt='comp')
        if hashed_password != account[2]:
            msg = "Please input the correct current password!"
            return render_template('updatepwd.html', msg=msg, userID=userID)
        #check if the user mistakely inputted
        else:
            if new_pwd ==pwd_check:
             hashed_newpwd = hashing.hash_value(new_pwd, salt='comp')
            #update into Users table   
             cur = getCursor()
             cur.execute("UPDATE Users SET Password = %s WHERE userID = %s", (hashed_newpwd, userID))
             msg="New Password Saved!"
             return render_template('updatepwd.html', msg=msg, userID=userID)
            else:
                msg="Passwords Inputted Don't Match"
                return render_template('updatepwd.html', msg=msg, userID=userID)
    else:
        return render_template('updatepwd.html',msg=msg, userID=userID) 


@app.route('/product_details/<int:product_id>')
def product_details(product_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT p.*, u.Name as UnitName FROM Products p JOIN Units u ON p.UnitID = u.UnitID WHERE p.ProductID = %s", (product_id,))
        product = cursor.fetchone()
        if not product:
            return "Product not found", 404

        return render_template('product_details.html', product=product)
    finally:
        cursor.close()
        connection.close()

        

@app.route('/boxes')
def list_boxes():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute('SELECT DISTINCT Type FROM Boxes')
    types = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT Size FROM Boxes')
    sizes = cursor.fetchall()
    
    query = "SELECT * FROM Boxes"
    params = []
    box_type = request.args.get('type')
    size = request.args.get('size')
    conditions = []

    if box_type:
        conditions.append("Type = %s")
        params.append(box_type)
    if size:
        conditions.append("Size = %s")
        params.append(size)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    cursor.execute(query, params)
    boxes = cursor.fetchall()
    connection.close()

    return render_template('list_boxes.html', boxes=boxes, types=types, sizes=sizes)

# Notification Start
@app.route('/view_notifications')
def view_notifications():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT n.*, 
               u.Email AS SenderEmail,
               COALESCE(cp.Email, sp.Email) AS RecipientEmail
        FROM Notifications n
        JOIN Users u ON n.UserID = u.UserID
        JOIN NotificationRecipients nr ON n.NotificationID = nr.NotificationID
        LEFT JOIN CustomerProfile cp ON nr.RecipientID = cp.UserID
        LEFT JOIN StaffProfile sp ON nr.RecipientID = sp.UserID
    """)
    notifications = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('all/notification.html', notifications=notifications, format_date=format_date)




@app.route('/create_notification', methods=['GET', 'POST'])
def create_notification():
    if request.method == 'POST':
        user_id = session.get('id')
        recipient_id = request.form.get('recipient_id')
        notification_type = request.form.get('type')
        title = request.form.get('title')
        message = request.form.get('message')
        link = request.form.get('link') or None
        expiration_date = request.form.get('expiration_date') or None

        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)

        # Insert the notification into the Notifications table
        cursor.execute(
            "INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated, ExpirationDate) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_id, notification_type, title, message, link, datetime.now(), expiration_date)
        )
        notification_id = cursor.lastrowid

        # Insert recipients into the NotificationRecipients table
        if recipient_id:
            # Specific recipient
            cursor.execute(
                "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                (recipient_id, notification_id)
            )
        else:
            # All customers or all staff
            if session.get('role') == 2:  # Staff
                cursor.execute("SELECT UserID FROM Users WHERE RoleID = 1")  # Customers only
            elif session.get('role') == 3:  # Location Manager
                cursor.execute("SELECT UserID FROM Users WHERE RoleID IN (1, 2)")  # Customers and Staff
            elif session.get('role') == 4:  # National Manager
                cursor.execute("SELECT UserID FROM Users WHERE RoleID IN (1, 2, 3, 4)")  # All users
            recipients = cursor.fetchall()
            for recipient in recipients:
                cursor.execute(
                    "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                    (recipient['UserID'], notification_id)
                )

        connection.commit()
        cursor.close()
        connection.close()
        flash('Notification created successfully.', "success")
        return redirect(url_for('view_notifications'))

    role = session.get('role')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    # Fetch customers and staff based on role
    if role == 2:  # Staff
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 1")  # Customers only
        customers = cursor.fetchall()
        staff = []
    elif role == 3:  # Location Manager
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 1")  # Customers
        customers = cursor.fetchall()
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 2")  # Staff
        staff = cursor.fetchall()
    elif role == 4:  # National Manager
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID IN (1, 2, 3, 4)")  # All users
        users = cursor.fetchall()
        customers = [user for user in users if user['RoleID'] == 1]
        staff = [user for user in users if user['RoleID'] in (2, 3, 4)]
    
    cursor.close()
    connection.close()
    return render_template('all/create_notification.html', customers=customers, staff=staff, role=role)

@app.route('/edit_notification/<int:notification_id>', methods=['GET', 'POST'])
def edit_notification(notification_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        notification_type = request.form.get('type')
        title = request.form.get('title')
        message = request.form.get('message')
        link = request.form.get('link') or None
        expiration_date = request.form.get('expiration_date') or None

        cursor.execute(
            "UPDATE Notifications SET Type = %s, Title = %s, Message = %s, Link = %s, ExpirationDate = %s WHERE NotificationID = %s",
            (notification_type, title, message, link, expiration_date, notification_id)
        )
        
        cursor.execute(
            "DELETE FROM NotificationRecipients WHERE NotificationID = %s",
            (notification_id,)
        )
        
        if recipient_id:
            cursor.execute(
                "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                (recipient_id, notification_id)
            )
        else:
            if session.get('role') == 2:  # Staff
                cursor.execute("SELECT UserID FROM Users WHERE RoleID = 1")  # Customers only
            elif session.get('role') == 3:  # Location Manager
                cursor.execute("SELECT UserID FROM Users WHERE RoleID IN (1, 2)")  # Customers and Staff
            elif session.get('role') == 4:  # National Manager
                cursor.execute("SELECT UserID FROM Users WHERE RoleID IN (1, 2, 3, 4)")  # All users
            recipients = cursor.fetchall()
            for recipient in recipients:
                cursor.execute(
                    "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                    (recipient['UserID'], notification_id)
                )

        connection.commit()
        cursor.close()
        connection.close()
        flash('Notification updated successfully.', "success")
        return redirect(url_for('view_notifications'))

    cursor.execute("SELECT * FROM Notifications WHERE NotificationID = %s", (notification_id,))
    notification = cursor.fetchone()

    role = session.get('role')
    if role == 2:  # Staff
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 1")  # Customers only
        customers = cursor.fetchall()
        staff = []
    elif role == 3:  # Location Manager
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 1")  # Customers
        customers = cursor.fetchall()
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID = 2")  # Staff
        staff = cursor.fetchall()
    elif role == 4:  # National Manager
        cursor.execute("SELECT UserID, Email, RoleID FROM Users WHERE RoleID IN (1, 2, 3, 4)")  # All users
        users = cursor.fetchall()
        customers = [user for user in users if user['RoleID'] == 1]
        staff = [user for user in users if user['RoleID'] in (2, 3, 4)]
    
    cursor.close()
    connection.close()
    return render_template('all/edit_notification.html', notification=notification, customers=customers, staff=staff, role=role)

@app.route('/delete_notification/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    connection = getDbConnection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM NotificationRecipients WHERE NotificationID = %s", (notification_id,))
    cursor.execute("DELETE FROM Notifications WHERE NotificationID = %s", (notification_id,))
    connection.commit()
    cursor.close()
    connection.close()
    flash('Notification deleted successfully.', "success")
    return redirect(url_for('view_notifications'))


@app.route('/read_notifications')
def read_notifications():
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT n.*, nr.HasBeenRead 
            FROM Notifications n
            JOIN NotificationRecipients nr ON n.NotificationID = nr.NotificationID
            WHERE nr.RecipientID = %s order by DateCreated desc
        """, (user_id,))
        notifications = cursor.fetchall()
    except Exception as e:
        flash('An error occurred while retrieving the notifications.')
        notifications = []
    finally:
        cursor.close()
        connection.close()

    return render_template('all/read_notifications.html', notifications=notifications, format_date = format_date)


@app.route('/notification/<int:notification_id>', methods=['GET'])
def read_notification_details(notification_id):
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT n.*, nr.HasBeenRead 
            FROM Notifications n
            JOIN NotificationRecipients nr ON n.NotificationID = nr.NotificationID
            WHERE n.NotificationID = %s AND nr.RecipientID = %s
        """, (notification_id, user_id))
        notification = cursor.fetchone()
        
        if not notification:
            flash('Notification not found or you do not have permission to view it.')
            return redirect(url_for('read_notifications'))

        if not notification['HasBeenRead']:
            cursor.execute("UPDATE NotificationRecipients SET HasBeenRead = TRUE WHERE NotificationID = %s AND RecipientID = %s", (notification_id, user_id))
            connection.commit()
    except Exception as e:
        flash('An error occurred while retrieving the notification details.')
        return redirect(url_for('read_notifications'))
    finally:
        cursor.close()
        connection.close()

    return render_template('all/read_notification_details.html', notification=notification, format_date = format_date)

# Notification End


# Inquiry
def getInquiryList():
    user_id = session.get('id') 
    location_id = session.get('locationid') 
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        if session['role'] == 2:
            cursor.execute("""
                select InquiryID,i.UserID,Subject,DateCreated,IfOpen from Inquiries i
                inner join Users u on u.UserID=i.UserID 
                inner join CustomerProfile c on c.UserID= u.UserID
                where c.LocationID = %s
                order by DateCreated desc""", (location_id,))

        elif session['role'] == 1:   
            cursor.execute("""
                select InquiryID,i.UserID,Subject,DateCreated,IfOpen from Inquiries i
                inner join CustomerProfile u on u.UserID=i.UserID               
                where u.UserID = %s
                order by DateCreated desc""", (user_id,))

        inquiries = cursor.fetchall()
        
            #return  render_template('customer/inquery_list.html',inqueries) 
    except Exception as e:
        flash('An error occurred while retrieving the inquiries.')
        return redirect(url_for('home'))
    finally:
        cursor.close()
        connection.close() 
    return inquiries  
# List inquiries by userID/locationID
@app.route('/list-inquiry', methods=['GET'])
def list_inquiry():
    inquiries =getInquiryList()
    return  render_template('customer/inquery_list.html',inquiries=inquiries, format_date = format_date)

# Add a new inquiry
@app.route('/add-inquiry', methods=['POST','GET'])
def add_inquiry():
    if request.method == 'GET':
        return  render_template('customer/inquery_form.html')
        
    elif request.method=='POST':
        try:
            user_id = session.get('id') 
            subject = request.form.get('subject')
            inqueryMessage = request.form.get('inqueryMessage')
            user_location_id = session.get('locationid')
            connection = getDbConnection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                insert into Inquiries (UserID, Subject, DateCreated, IfOpen) values 
            (%s,%s, %s,1)""", (user_id, subject,datetime.now()))
            addedInquiryID = cursor.lastrowid
            #cursor.execute("SELECT LAST_INSERT_ID() as InquiryID")
            #addedInquiryID = cursor.fetchone()['InquiryID']
            #Add msg with init inquiry 
         
            cursor.execute("""
            insert into InquiryMsg (InquiryID, UserID, Message, DateCreated, IfRead) values 
            (%s,%s,%s,%s,0)""", (addedInquiryID, user_id, inqueryMessage, datetime.now()))
            notiifcationTitle ='Inquiry - ' +subject
            notificationLink = "/list-message/"+ str(addedInquiryID)
            #Insert notification here
           
            # cursor.execute(
            #     "INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated) VALUES (%s, %s, %s, %s, %s,%s)",
            #     (user_id, 'General Alert', notiifcationTitle, 'You have a inquiry update.', notificationLink, datetime.now(),)
            # )

            cursor.execute("""
                select s.UserID from StaffProfile s 
                inner join Users u on s.UserID = u.UserID
                inner join Inquiries i on s.UserID = u.UserID
                where InquiryID =%s and u.RoleID = 2 and s.LocationID =%s
            """, (addedInquiryID ,user_location_id,))
            recipient_ids = cursor.fetchall()
            for recipient_id in recipient_ids:           
                cursor.execute(
                    "INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated ) VALUES (%s, %s, %s, %s, %s, %s )",
                        (recipient_id['UserID'], 'General Alert', notiifcationTitle, 'You have a inquiry update.', notificationLink,datetime.now())
                    )
                notification_id = cursor.lastrowid
                cursor.execute(
                        "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                        (recipient_id['UserID'], notification_id)
                )
            connection.commit()
           
            
            
            
        except Exception as e:
            flash('An error occurred while retrieving the notification details.')
            return redirect(url_for('read_notifications'))
        finally:
            cursor.close()
            connection.close() 
        return  redirect(url_for('list_inquiry'))


#View a inquiry/List messages with inquiry_id
@app.route('/list-message/<int:inquiry_id>', methods=['GET'])
def view_inquiry(inquiry_id):
    user_id = session.get('id') 
    subject = request.form.get('subject')

    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
           select im.*, u.RoleID, u.Email, i.Subject from InquiryMsg im 
           inner join Users u on u.UserID=im.UserID
           inner join Inquiries i on i.InquiryID=im.InquiryID
           where im.InquiryID= %s order by DateCreated """,(inquiry_id,))
        inqueryMsgs = cursor.fetchall()
           
    except Exception as e:
        flash('An error occurred while retrieving the notification details.')
        return redirect(url_for('read_notifications'))
    finally:
        cursor.close()
        connection.close() 
    return  render_template('customer/inquery_details.html',inqueryMsgs=inqueryMsgs, format_date = format_date)

# Add a new message within the inquiry
@app.route('/add-message', methods=['POST'])
def add_msg():
    inquiry_id =  int(request.form.get('inquiryID'))
    inquirySubject = request.form.get('inquirySubject')
    user_id = session.get('id') 
    user_role = session.get('role')
    user_location_id = session.get('locationid')
    message = request.form.get('newMsg')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        
        cursor.execute("""
            insert into InquiryMsg (InquiryID, UserID, Message, DateCreated, IfRead) values 
        (%s,%s,%s, %s,0)""", (inquiry_id, user_id, message, datetime.now()))
        #Inser notification here    
        notiifcationTitle ='Inquiry - ' +inquirySubject
        notificationLink = "/list-message/"+ str(inquiry_id)
        
        # Find out the userIDs who are going to receive Notifications
        if user_role==2:
            cursor.execute("""
                select i.UserID from Inquiries i 
                inner join Users u on i.UserID = u.UserID
                where InquiryID =%s and u.RoleID = 1
            """, (inquiry_id,))
            recipient_id = cursor.fetchone()
            cursor.execute(
                "INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated ) VALUES (%s, %s, %s, %s, %s, %s )",
                    (recipient_id['UserID'], 'General Alert', notiifcationTitle, 'You have a inquiry update.', notificationLink, datetime.now())
                )
            notification_id = cursor.lastrowid
            cursor.execute(
                    "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                    (recipient_id['UserID'], notification_id)
            )
        if user_role==1:
            cursor.execute("""
                select s.UserID from StaffProfile s 
                inner join Users u on s.UserID = u.UserID
                inner join Inquiries i on s.UserID = u.UserID
                where InquiryID =%s and u.RoleID = 2 and s.LocationID =%s
            """, (inquiry_id,user_location_id,))
            recipient_ids = cursor.fetchall()
            for recipient_id in recipient_ids:           
                cursor.execute(
                    "INSERT INTO Notifications (UserID, Type, Title, Message, Link, DateCreated ) VALUES (%s, %s, %s, %s, %s,%s )",
                        (recipient_id['UserID'], 'General Alert', notiifcationTitle, 'You have a inquiry update.', notificationLink,datetime.now())
                    )
                notification_id = cursor.lastrowid
                cursor.execute(
                        "INSERT INTO NotificationRecipients (RecipientID, NotificationID) VALUES (%s, %s)",
                        (recipient_id['UserID'], notification_id)
                )
        connection.commit()
    except Exception as e:
        flash('An error occurred while updating the inquiry message.')
        return redirect(url_for('list_inquiry'))
    finally:
        cursor.close()
        connection.close() 
    return  redirect(url_for('list_inquiry'))


