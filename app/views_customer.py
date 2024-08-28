from datetime import datetime
from datetime import date, timedelta
from flask import redirect, render_template, request, session, url_for, flash
from app import app
from app.config.database import getDbConnection
from app.config.database import getCursor
from app.config.helpers import require_role
from app.config.helpers import format_date
from app.config.helpers import format_nz_currency
import secrets
import string



def get_cart_item_count(user_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT SUM(Quantity) AS item_count FROM CartItems WHERE CartID IN (SELECT CartID FROM Cart WHERE UserID = %s)", (user_id,))
        result = cursor.fetchone()
        return result['item_count'] if result and result['item_count'] else 0
    except Exception as e:
        print("Error getting cart item count:", e)
        return 0
    finally:
        cursor.close()
        connection.close()
    
def load_notification_counts(user_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT COUNT(*) AS count FROM NotificationRecipients WHERE RecipientID = %s AND HasBeenRead = FALSE", 
            (user_id,)
        )
        result = cursor.fetchone()
        return result['count'] if result and result['count'] else 0
    except Exception as e:
        print("Error getting cart item count:", e)
        return 0
    finally:
        cursor.close()
        connection.close()
    
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if session.get('loggedin') != True or session.get('role') < 1:
        flash('Please log in to add items to your cart.', "danger")
        return redirect(url_for('login'))

    userId = session.get('id')
    quantity = int(request.form.get('quantity', 1))
    unit = request.form.get('unit')

    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM Products WHERE ProductID = %s", (product_id,))
        product = cursor.fetchone()
        
        if product and quantity > 0 and unit and product['AvailableQuantity']>=quantity:
            cursor.execute("SELECT * FROM Cart WHERE UserID = %s", (userId,))
            cart = cursor.fetchone()
            if not cart:
                cursor.execute("INSERT INTO Cart (UserID) VALUES (%s)", (userId,))
                connection.commit()
                cursor.execute("SELECT * FROM Cart WHERE UserID = %s", (userId,))
                cart = cursor.fetchone()

            cursor.execute("SELECT * FROM CartItems WHERE CartID = %s AND ProductID = %s AND Unit = %s", 
                           (cart['CartID'], product_id, unit))
            cart_item = cursor.fetchone()
            if cart_item:
                cursor.execute("UPDATE CartItems SET Quantity = Quantity + %s WHERE CartID = %s AND ProductID = %s AND Unit = %s", 
                               (quantity, cart['CartID'], product_id, unit))
            else:
                cursor.execute("INSERT INTO CartItems (CartID, ProductID, Quantity, UnitPrice, Unit) VALUES (%s, %s, %s, %s, %s)", 
                               (cart['CartID'], product_id, quantity, product['Price'], unit))

            connection.commit()
            flash('Item added to cart.', "success")
        else:
            flash('Invalid product or quantity.', "danger")
    except Exception as e:
        print(e)
        flash('An error occurred while adding to the cart.', "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('list_products'))


@app.route('/cart')
def cart():
    userId = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    discount = 0
    cart_items = []
    total = 0
    shipping_price = 0
    applied_gift_card = session.get('applied_gift_card', None)
    account_holder_status = 'no'
    
    try:
        cursor.execute("SELECT * FROM Cart WHERE UserID = %s", (userId,))
        cart = cursor.fetchone()

        if cart:
            cursor.execute("""
                SELECT ci.*, p.Name, r.RecipeID, r.RecipeName
                FROM CartItems ci
                JOIN Products p ON ci.ProductID = p.ProductID
                LEFT JOIN Recipes r ON p.ProductID = r.ProductID
                WHERE ci.CartID = %s
            """, (cart['CartID'],))
            cart_items = cursor.fetchall()

            gift_card_number = cart.get('GiftCard')
            if gift_card_number:
                cursor.execute('SELECT Balance FROM GiftCards WHERE CardNumber = %s', (gift_card_number,))
                gift_card = cursor.fetchone()
                if gift_card:
                    discount = gift_card['Balance']

            total = sum(item['Quantity'] * item['UnitPrice'] for item in cart_items) - discount
            if total < 0:
                total = 0
                
            # Check account holder status 
            cursor.execute("""
                SELECT ah.ApplicationStatus
                FROM AccountHolders ah
                WHERE ah.UserID = %s AND ah.ApplicationStatus = 'Approved'
            """, (userId,))
            account_holder = cursor.fetchone()
            if account_holder:
                account_holder_status = account_holder['ApplicationStatus']

            # Get the user's location
            location_id = session.get('locationid') 

            # Fetch the shipping price based on the location
            cursor.execute("SELECT ShippingPrice FROM Locations WHERE LocationID = %s", (location_id,))
            location = cursor.fetchone()
            if location:
                shipping_price = location['ShippingPrice']
                total += shipping_price

    except Exception as e:
        flash('An error occurred while retrieving the cart.', 'warning')
        print("Error occurred:", e)
        total = 0
    finally:
        cursor.close()
        connection.close()

    return render_template('customer/cart.html', cart_items=cart_items, total=total, shipping_price=shipping_price, applied_gift_card=applied_gift_card, account_holder_status=account_holder_status)


@app.route('/place_order', methods=['POST'])
def place_order():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    user_id = session.get('id')
    
    try:
        # Fetch cart
        cursor.execute("SELECT * FROM Cart WHERE UserID = %s", (user_id,))
        cart = cursor.fetchone()
        
        if not cart:
            flash('Your cart is empty.')
            return redirect(url_for('cart'))

        # Check account holder status and remaining credit
        cursor.execute("""
            SELECT ah.RemainingCredit
            FROM AccountHolders ah
            WHERE ah.UserID = %s AND ah.ApplicationStatus = 'Approved'
        """, (user_id,))
        account_holder = cursor.fetchone()
        
        remaining_credit = account_holder['RemainingCredit'] if account_holder else None
        
        # Calculate cart total
        cursor.execute("SELECT SUM(UnitPrice * Quantity) AS CartTotal FROM CartItems WHERE CartID = %s", (cart['CartID'],))
        cart_total = cursor.fetchone()['CartTotal']
        
        if account_holder and cart_total > remaining_credit:
            flash('Exceeds credit limit, please increase limit before placing an order.')
            return redirect(url_for('cart'))

        # Fetch shipping price based on location
        cursor.execute("SELECT ShippingPrice FROM Locations WHERE LocationID = %s", (session.get('locationid'),))
        shipping_price = cursor.fetchone()['ShippingPrice']

        # Create a new order
        cursor.execute("""
            INSERT INTO Orders (UserID, DateOrdered, StatusID, TotalPrice, LocationID, ShippingPrice) 
            VALUES (%s, %s, %s, 0, %s, %s)
        """, (user_id, datetime.now(), 1, session.get('locationid'), shipping_price))
        connection.commit()

        cursor.execute("SELECT LAST_INSERT_ID() AS OrderID")
        order_id = cursor.fetchone()['OrderID']

        # Check gift card balance
        gift_card_balance = 0
        if 'GiftCard' in cart:
            cursor.execute('SELECT Balance FROM GiftCards WHERE CardNumber = %s', (cart['GiftCard'],))
            gift_card = cursor.fetchone()
            if gift_card:
                gift_card_balance = gift_card['Balance']

        # Transfer cart items to order items and update total price
        cursor.execute("SELECT * FROM CartItems WHERE CartID = %s", (cart['CartID'],))
        cart_items = cursor.fetchall()
        
        total_price = 0
        for item in cart_items:
            cursor.execute("""
                INSERT INTO OrderItems (OrderID, ProductID, Quantity, UnitPrice) 
                VALUES (%s, %s, %s, %s)
            """, (order_id, item['ProductID'], item['Quantity'], item['UnitPrice']))
            total_price += item['Quantity'] * item['UnitPrice']

        # Calculate points earned
        points_earned = int(total_price * 10)
        cursor.execute("""
            INSERT INTO Points (UserID, CurrentPoints)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE CurrentPoints = CurrentPoints + %s
        """, (user_id, points_earned, points_earned))
        
        cursor.execute("""
            INSERT INTO PointsTransactions (UserID, OrderID, PointsEarned)
            VALUES (%s, %s, %s)
        """, (user_id, order_id, points_earned))
        
        # Update inventory
        for item in cart_items:
            cursor.execute("""
                UPDATE Products 
                SET AvailableQuantity = AvailableQuantity - %s 
                WHERE ProductID = %s
            """, (item['Quantity'], item['ProductID']))

        # Adjust final price with gift card balance and include shipping price
        final_price = total_price + shipping_price - gift_card_balance
        new_gift_card_balance = gift_card_balance - (total_price + shipping_price) if final_price <= 0 else 0
        if final_price < 0:
            final_price = 0

        cursor.execute("UPDATE Orders SET TotalPrice = %s WHERE OrderID = %s", (final_price, order_id))

        # Update gift card balance
        if 'GiftCard' in cart:
            cursor.execute("UPDATE GiftCards SET Balance = %s WHERE CardNumber = %s", (new_gift_card_balance, cart['GiftCard']))

        # Update remaining credit for account holders
        if account_holder:
            new_remaining_credit = remaining_credit - final_price
            cursor.execute("UPDATE AccountHolders SET RemainingCredit = %s WHERE UserID = %s", (new_remaining_credit, user_id))

        # Clear the cart
        cursor.execute("DELETE FROM CartItems WHERE CartID = %s", (cart['CartID'],))
        cursor.execute("DELETE FROM Cart WHERE CartID = %s", (cart['CartID'],))
        connection.commit()
        
        session.pop('applied_gift_card', None)
        flash('Order placed successfully.', "success")
        if not account_holder:
            # Process payment
            process_payment(user_id, order_id, 'Order', request.form['card_number'], request.form['cardholder_name'])
            
    except Exception as e:
        connection.rollback()
        print("Error occurred:", e)
        flash('An error occurred while placing the order.', 'danger')
    
    finally:
        cursor.close()
        connection.close()
    

    
    return redirect(url_for('list_products'))

@app.route('/update_cart_item/<int:cart_item_id>', methods=['POST'])
def update_cart_item(cart_item_id):

    quantity = int(request.form.get('quantity', 1))
    unit = request.form.get('unit')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    try:
        if quantity > 0 and unit:
            cursor.execute("UPDATE CartItems SET Quantity = %s, Unit = %s WHERE CartItemID = %s", 
                           (quantity, unit, cart_item_id))
            connection.commit()
            flash('Cart item updated.', "success")
        else:
            flash('Invalid quantity or unit.', "danger")
    except Exception as e:
        print(e)
        flash('An error occurred while updating the cart item.', "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('cart'))

@app.route('/remove_cart_item/<int:cart_item_id>', methods=['POST'])
def remove_cart_item(cart_item_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM CartItems WHERE CartItemID = %s", (cart_item_id,))
        connection.commit()
        flash('Cart item removed.', "success")
    except Exception as e:
        print(e)
        flash('An error occurred while removing the cart item.', "danger")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('cart'))



@app.route('/apply_account_holder', methods=['GET', 'POST'])
def apply_account_holder():
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    if request.method == 'POST':
        business_name = request.form.get('business_name')
        business_address = request.form.get('business_address')
        contact_number = request.form.get('contact_number')
        
        cursor.execute("""
            SELECT * FROM AccountHolders WHERE UserID = %s
        """, (user_id,))
        existing_application = cursor.fetchone()
        
        if existing_application:
            cursor.fetchall()
            cursor.execute("""
                UPDATE AccountHolders
                SET BusinessName = %s, BusinessAddress = %s, BusinessContactNumber = %s, ApplicationStatus = 'Pending'
                WHERE UserID = %s
            """, (business_name, business_address, contact_number, user_id))
        else:
            cursor.execute("""
                INSERT INTO AccountHolders (UserID, BusinessName, BusinessAddress, BusinessContactNumber, ApplicationStatus)
                VALUES (%s, %s, %s, %s, 'Pending')
            """, (user_id, business_name, business_address, contact_number))
        
        connection.commit()
        cursor.close()
        connection.close()
        flash('Your application has been submitted and is pending review.', 'info')
        return redirect(url_for('apply_account_holder'))
    
    cursor.execute("""
        SELECT ApplicationStatus, CreditLimit, RemainingCredit
        FROM AccountHolders
        WHERE UserID = %s
    """, (user_id,))
    application = cursor.fetchone()
    cursor.fetchall()
    cursor.close()
    connection.close()
    
    return render_template('customer/apply_account_holder.html', application=application)




################ view receipts#########################
@app.route('/receipt', methods = ['POST','GET'])
def receipt():
    userid = session.get('id')
    cursor = getCursor()
    sql ="""
            SELECT o.OrderID, o.DateOrdered, o.TotalPrice, p.PaymentID
            FROM Orders AS o
            JOIN Payments AS p ON o.OrderID = p.OrderID
            WHERE o.UserID = %s
            """

    cursor.execute(sql,(userid,))
    receipts = cursor.fetchall()
    print(receipts)

   
    sql = """
        SELECT p.BoxOrderID, p.CreatedAt, p.Type, bo.TotalPrice, p.PaymentID
        FROM Payments AS p
        JOIN BoxOrders AS bo ON p.BoxOrderID = bo.BoxOrderID
        WHERE bo.UserID = %s;
        """
    cursor.execute(sql,(userid,))
    subscriptions = cursor.fetchall()
    return render_template('/customer/receipt.html',receipts = receipts, subscriptions = subscriptions, format_date = format_date, format_nz_currency=format_nz_currency)
        
def get_application_status(user_id):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT ApplicationStatus FROM AccountHolders WHERE UserID = %s', (user_id,))
        result = cursor.fetchone()
        return result['ApplicationStatus'] if result else 'Not Applied'
    finally:
        cursor.close()
        connection.close()

######## receipt details
@app.route('/receipt_details/<int:receiptID>')
def receipt_details(receiptID):
    
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    sql = "SELECT * FROM Payments WHERE PaymentID = %s"
    cursor.execute(sql, (receiptID,))
    result = cursor.fetchone()
    orderid = result['OrderID']
    box_orders = None
    orders = None
    if not orderid:
        box_orderid = result['BoxOrderID']
    invoiceid = result['InvoiceID']
    created_date = result['CreatedAt']
    if orderid:
        sql = """
               SELECT o.OrderID, p.Name, oi.UnitPrice, oi.Quantity FROM Orders AS o
               JOIN OrderItems AS oi ON  o.OrderID = oi.OrderID
               JOIN Products AS p ON oi.ProductID = p.ProductID
               WHERE o.OrderID = %s;

            """
        cursor.execute(sql, (orderid,) )
        orders = cursor.fetchall()
        print(orders)
    else:
        sql = """
               SELECT bo.BoxOrderID, b.Name, b.Price, b.Size, bo.Quantity, bo.TotalPrice FROM BoxOrders AS bo
               JOIN Boxes AS b ON bo.BoxID = b.BoxID
               WHERE BoxOrderID = %s;

               """
        cursor.execute(sql,(box_orderid,))
        box_orders = cursor.fetchall()

    sql = " SELECT * FROM Invoices WHERE InvoiceID = %s"
    cursor.execute(sql, (invoiceid,))
    invoice = cursor.fetchone()
    remaining = cursor.fetchall()
    print(invoice)
    #getting the customer's name and address
    userid = session.get('id')
    sql = "SELECT FirstName, LastName, Address FROM CustomerProfile WHERE UserID = %s "
    cursor.execute(sql,(userid,))
    customer = cursor.fetchone()
    return render_template('customer/receipt_details.html', invoiceid = invoiceid, created_date = created_date, orders = orders, box_orders = box_orders, invoice = invoice, customer = customer, format_date = format_date)



@app.route('/box_details/<int:BoxID>')
def box_details(BoxID):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Boxes WHERE BoxID = %s", (BoxID,))
    box = cursor.fetchone()
    cursor.execute("""
        SELECT bc.BoxContentID, p.Name, u.Name AS UnitName, bc.Quantity
        FROM BoxContents bc
        JOIN Products p ON bc.ProductID = p.ProductID
        JOIN Units u ON p.UnitID = u.UnitID
        WHERE bc.BoxID = %s
    """, (BoxID,))
    box_contents = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('box_details.html', box=box, box_contents=box_contents)



# update_subscription
def update_subscription():
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    sql = """SELECT * FROM Subscriptions
             WHERE CAST(EndDate AS date)= CURDATE()
             AND Status = 'Active' 
             AND Frequency !='One-time'; """
            
    print('it has been updated')

    cursor.execute(sql)
    updates = cursor.fetchall()
    for update in updates:
        if update:
            subid = update['SubID']
            boxid = update['BoxID']
            userid = update['UserID']
            quantity = update['Quantity']
            frequency = update['Frequency']
            total_price = float(update['TotalPrice'])
            gst = total_price/1.15*0.15
            gst = format(gst, ".2f")
            total_price = format(total_price, ".2f")
            start_date = update['EndDate']
            created_date = update['DateCreated']
            if frequency == 'Weekly':
                end_date = start_date + timedelta(weeks=1)
            elif frequency == 'Fortnightly':
                end_date = start_date + timedelta(weeks=2)
            else:
                end_date = start_date + timedelta(weeks=4)\
                
            start_date = start_date.strftime('%Y/%m/%d %H:%M:%S')
            end_date = end_date.strftime('%Y/%m/%d %H:%M:%S')
            
        #update database for subcriptions

            sql = """
                    UPDATE Subscriptions 
                    SET StartDate = %s, 
                        EndDate = %s 
                    WHERE SubID = %s;
                """
            params = (start_date, end_date, subid)

            cursor.execute(sql, params)
            connection.commit()

        ### insert into database for boxorder
            Status_id = 1
            sql = " INSERT INTO BoxOrders (BoxID, UserID, StatusID, Quantity, TotalPrice, DateCreated) VALUES (%s, %s, %s, %s, %s, %s)"
            params = (boxid, userid, Status_id, quantity, total_price, created_date)
            cursor.execute(sql, params)
            box_orderid = cursor.lastrowid
            connection.commit()
        
        ### insert into database for invoice
            sql = """
                INSERT INTO Invoices (UserID, InvoiceDate, DueDate, TotalAmount, GSTAmount, Status) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (userid, start_date, start_date, total_price, gst,  "paid")
       
            cursor.execute(sql, params)
            invoiceid= cursor.lastrowid
            connection.commit()

        ### insert into database for Payment
            type = "subscription"
            sql = """
                INSERT INTO Payments (BoxOrderID, InvoiceID,  Type, CreatedAt) 
                VALUES (%s, %s, %s, %s)
            """
        params = (box_orderid, invoiceid, type, created_date)
        
        cursor.execute(sql, params)
        connection.commit()



# Add subscription
@app.route('/add_subscription', methods= ['POST'])
def add_sub():
    boxid = request.form.get('BoxID')
    frequency = request.form.get('frequency')
    quantity = request.form.get('quantity')
    price = request.form.get('price')
    total_price = float(price) * int(quantity)
    userid = session.get('id')
    type = request.form.get('type')
    created_date = datetime.now()
    start_date = datetime.now()
    location_id = session.get('locationid') 
    
   
    if frequency =='One-time':
        end_date = start_date
    elif frequency == 'Weekly':
        end_date = start_date + timedelta(weeks=1)
    elif frequency == 'Fortnightly':
        end_date = start_date + timedelta(weeks=2)
    else:
        end_date = start_date + timedelta(weeks=4)
   
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)



### insert into database for boxorder
    Status_id = 1
    sql = " INSERT INTO BoxOrders (BoxID, UserID, StatusID, Quantity, TotalPrice, DateCreated) VALUES (%s, %s, %s, %s, %s, %s)"
    params = (boxid, userid, Status_id, quantity, total_price, created_date)
    cursor.execute(sql, params)
    id = cursor.lastrowid
    connection.commit()
    


### insert into database for subscriptions
    sql = "INSERT INTO Subscriptions (BoxID, UserID, Frequency, Quantity, StartDate, EndDate, DateCreated, TotalPrice) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    params = (boxid, userid, frequency, quantity, start_date, end_date, created_date, total_price)

    cursor.execute(sql, params)
    
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('input_payment_info', id = id, type = type ))

# ####################customer make payment###############################
@app.route('/input_payment_info/<int:id>/<string:type>', methods = ['GET','POST'])
def input_payment_info(id, type):
    if request.method == 'POST':
        cardnumber = request.form.get('card_number')
        cardholder = request.form.get('cardholder_name')
        created_date = datetime.now()
        userid = session.get('id')

        connection = getDbConnection()
        cursor = connection.cursor(dictionary=True)
        if type =="Subscription":
        #### getting totalprice from BoxOrders
            sql = """
                SELECT * FROM BoxOrders WHERE BoxOrderID = %s
            """
        else:
            sql ="""
                SELECT * FROM Orders WHERE OrderID = %s
                """ 
        cursor.execute(sql,(id,))
        box_order = cursor.fetchone()
        total_price = float(box_order['TotalPrice'])
        gst = total_price/1.15*0.15
        gst = format(gst, ".2f")
        total_price = format(total_price, ".2f")

        # insert into Invoices
        sql = """
                INSERT INTO Invoices (UserID, InvoiceDate, DueDate, TotalAmount, GSTAmount, Status) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
        params = (userid, created_date, created_date, total_price, gst,  "paid")
   
       
        cursor.execute(sql, params)
        invoiceid= cursor.lastrowid
        connection.commit()


        # insert into payments
        # subscriptions
    
        sql = """
            INSERT INTO Payments (BoxOrderID, InvoiceID, CardNumber, CardHolder, Type, CreatedAt) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        params = (id, invoiceid, cardnumber, cardholder, type, created_date)
    

        cursor.execute(sql, params)
        connection.commit()

        cursor.close()
        connection.close()
        flash('You have made your payment successfully.', 'success')
        return redirect(url_for('customer_dashboard'))
        
    else:
       
        return render_template('customer/payment.html', id = id, type=type)

@app.route('/order')
def order():
    cur = getCursor()
    cur.execute("SELECT Orders.OrderID, DateOrdered, TotalPrice, StatusName FROM Orders \
                LEFT JOIN OrderStatus ON Orders.StatusID = OrderStatus.StatusID \
                WHERE UserID =  %s ORDER BY DateOrdered DESC", (session['id'],))
    orderlist = cur.fetchall()
    return render_template('customer/order.html', orderlist = orderlist, format_date = format_date)

@app.route('/orderdetail/<int:orderID>')
def orderdetail(orderID):
    connection = getDbConnection()
    cur = connection.cursor(dictionary=True)
    cur.execute("""
        SELECT Orders.OrderID, DateOrdered, TotalPrice, StatusName, ShippingPrice, 
               Name, OrderItems.Unit, OrderItems.UnitPrice, OrderItems.Quantity
        FROM Orders
        LEFT JOIN OrderItems ON Orders.OrderID = OrderItems.OrderID
        LEFT JOIN Products ON OrderItems.ProductID = Products.ProductID
        LEFT JOIN OrderStatus ON Orders.StatusID = OrderStatus.StatusID
        WHERE Orders.OrderID = %s 
    """, (orderID,))
    detail = cur.fetchall()
    cur.close()
    connection.close()
    return render_template('customer/orderdetail.html', detail=detail, format_date = format_date)


@app.route('/order_again/<int:orderID>')
def order_again(orderID):
    user_id = session.get('id')
    if not user_id:
        flash('You need to be logged in to reorder.', 'danger')
        return redirect(url_for('login'))

    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Retrieve the items from the order
        cursor.execute("SELECT ProductID, Quantity, UnitPrice, Unit FROM OrderItems WHERE OrderID = %s", (orderID,))
        items = cursor.fetchall()

        # Get the user's cart or create a new one if it doesn't exist
        cursor.execute("SELECT CartID FROM Cart WHERE UserID = %s", (user_id,))
        cart = cursor.fetchone()
        if not cart:
            cursor.execute("INSERT INTO Cart (UserID) VALUES (%s)", (user_id,))
            connection.commit()
            cursor.execute("SELECT LAST_INSERT_ID() AS CartID")
            cart_id = cursor.fetchone()['CartID']
        else:
            cart_id = cart['CartID']

        # Add the items to the cart
        for item in items:
            cursor.execute(
                "INSERT INTO CartItems (CartID, ProductID, Quantity, UnitPrice, Unit) VALUES (%s, %s, %s, %s, %s) \
                ON DUPLICATE KEY UPDATE Quantity = Quantity + VALUES(Quantity)",
                (cart_id, item['ProductID'], item['Quantity'], item['UnitPrice'], item['Unit'])
            )
        connection.commit()
        flash('Items have been added to your cart.', 'success')
    except Exception as e:
        print(e)
        flash('An error occurred while reordering.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('cart'))


@app.route('/view_credit')
def view_credit():
    user_id = session.get('id')
    
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT CreditLimit, RemainingCredit, InvoiceDueDate 
        FROM AccountHolders 
        WHERE UserID = %s
    """, (user_id,))
    
    credit_info = cursor.fetchone()
    
    cursor.close()
    connection.close()
    
    return render_template('customer/view_credit.html', credit_info=credit_info)

@app.route('/request_credit_increase', methods=['GET', 'POST'])
def request_credit_increase():
    user_id = session.get('id')
    
    if request.method == 'POST':
        requested_amount = request.form.get('requested_amount')
        reason = request.form.get('reason')
        
        connection = getDbConnection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO CreditIncreaseRequests (UserID, RequestedAmount, Reason, Status) 
            VALUES (%s, %s, %s, 'Pending')
        """, (user_id, requested_amount, reason))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Your request for a credit limit increase has been submitted.', 'success')
        return redirect(url_for('view_credit'))
    
    return render_template('customer/request_credit_increase.html')


@app.route('/my_invoices')
@require_role(1)
def my_invoices():
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT InvoiceID, InvoiceDate, DueDate, TotalAmount, GSTAmount, Status
        FROM Invoices
        WHERE UserID = %s
        ORDER BY InvoiceDate DESC
    """, (user_id,))
    invoices = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return render_template('customer/my_invoices.html', invoices=invoices)

@app.route('/invoice_details/<int:invoice_id>')
@require_role(1)
def invoice_details(invoice_id):
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT i.InvoiceID, i.InvoiceDate, i.DueDate, i.TotalAmount, i.GSTAmount, i.ShippingPrice, i.Status,
               ii.Description, ii.Quantity, ii.UnitPrice, ii.TotalPrice,
               u.Email
        FROM Invoices i
        LEFT JOIN InvoiceItems ii ON i.InvoiceID = ii.InvoiceID
        LEFT JOIN Users u ON i.UserID = u.UserID
        WHERE i.InvoiceID = %s AND i.UserID = %s
    """, (invoice_id, user_id))
    invoice = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    if not invoice:
        flash('Invoice not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('my_invoices'))
    
    return render_template('customer/invoice_details.html', invoice=invoice)


@app.route('/pay_invoice/<int:invoice_id>', methods=['POST'])
@require_role(1)
def pay_invoice(invoice_id):
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check if the invoice belongs to the user and is not already paid
        cursor.execute("""
            SELECT * FROM Invoices 
            WHERE InvoiceID = %s AND UserID = %s AND Status != 'Paid'
        """, (invoice_id, user_id))
        invoice = cursor.fetchone()

        if not invoice:
            flash('Invoice not found or already paid.', 'danger')
            return redirect(url_for('my_invoices'))

        # Process payment (assume payment details are collected via a form)
        card_number = request.form.get('card_number')
        card_holder = request.form.get('card_holder')

        # Create a new payment record
        cursor.execute("""
            INSERT INTO Payments (InvoiceID, CardNumber, CardHolder, Type, CreatedAt) 
            VALUES (%s, %s, %s, 'Invoice', %s)
        """, (invoice_id, card_number, card_holder, datetime.now()))

        # Update the invoice status to 'Paid'
        cursor.execute("""
            UPDATE Invoices 
            SET Status = 'Paid' 
            WHERE InvoiceID = %s
        """, (invoice_id,))
        
        connection.commit()
        flash('Invoice paid successfully.', 'success')
    except Exception as e:
        connection.rollback()
        print("Error occurred:", e)
        flash('An error occurred while processing the payment.', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('invoice_details', invoice_id=invoice_id))

# showing customer's subs
@app.route('/subscriptions')
@require_role(1)
def subscriptions():
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    sql = """
            SELECT s.* , b.Name ,b.Size FROM Subscriptions AS s
            JOIN Boxes AS b ON b.BoxID = s.BoxID
            WHERE Status = 'Active'
            AND UserID = %s;
         """
    cursor.execute(sql,(user_id,))
    subs = cursor.fetchall()
    return render_template('customer/subs.html', subs = subs, format_date = format_date, format_nz_currency =format_nz_currency)

# stop subs
@app.route('/stop_subscription/<int:subid>', methods = ['POST'])
@require_role(1)
def stop_subscription(subid):
    user_id = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    sql = """
            UPDATE Subscriptions
            SET Status = 'Inactive'
            WHERE SubID = %s
        """
    cursor.execute(sql, (subid,))
    connection.commit()
    flash('You will not be charged and receive orders at next term','success')
    return redirect(url_for('subscriptions'))

@app.route('/News/<newstype>')
def news(newstype):
    cursor = getCursor()
    cursor.execute('SELECT * FROM News WHERE NewsType = %s ORDER BY ExpirationDate desc, DateCreated desc', (newstype,))
    newslist = cursor.fetchall()
    today = datetime.now().date()
    if session['role'] == 4:
        filtered_newslist = newslist
    else:   
        filtered_newslist = [news for news in newslist if news[6] == session['locationid']]
    print(filtered_newslist)
    return render_template('all/specialoffers.html', newslist=filtered_newslist, newstype = newstype, today=today, format_date=format_date)

@app.route('/buygiftcard/<int:id>', methods=["GET", 'POST'])
@require_role(1)  # Assuming role 1 is for customers
def buygiftcard(id):
    if request.method == 'GET':
        try:
            with getDbConnection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute('SELECT * FROM GiftCardOption WHERE GiftCardOptionID = %s', (id,))
                    gc = cursor.fetchone()
            return render_template('customer/buygiftcard.html', gc=gc)
        except Exception as e:
            flash(f"Error fetching gift card options: {e}", 'danger')
            return redirect(url_for('giftcard'))

    else:
        try:
            characters = string.ascii_letters + string.digits
            giftcardcode = ''.join(secrets.choice(characters) for _ in range(10))
            gcid = request.form['gcid']
            amount = request.form['amount']
            name = request.form['name']
            address = request.form['address']
            dateCreated = datetime.now().date()
            user_id = session.get('id')

            with getDbConnection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute('SELECT * FROM GiftCardOption WHERE GiftCardOptionID = %s', (gcid,))
                    gc = cursor.fetchone()
                    if not gc:
                        flash("Gift card option not found.", 'danger')
                        return redirect(url_for('giftcard'))

                    # Insert into GiftCards table
                    cursor.execute('''
                        INSERT INTO GiftCards (CardNumber, Balance, Type, Name, Address, dateCreated) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (giftcardcode, amount, gcid, name, address, dateCreated))

                    # Get the inserted GiftCardID
                    cursor.execute("SELECT LAST_INSERT_ID() AS GiftCardID")
                    gift_card_id = cursor.fetchone()['GiftCardID']

                    # Insert into UserGiftCards table
                    cursor.execute('''
                        INSERT INTO UserGiftCards (UserID, GiftCardID) 
                        VALUES (%s, %s)
                    ''', (user_id, gift_card_id))

                    connection.commit()

            return render_template('customer/mygiftcard.html', giftcardcode=giftcardcode, gc=gc, amount=amount)
        except Exception as e:
            flash(f"Error occurred: {e}", 'danger')
            return redirect(url_for('giftcard'))


@app.route('/applypromo', methods=['POST'])
def applypromo():
    code = request.form['promocode']
    cursor = getCursor()
    cursor.execute('SELECT CardNumber FROM GiftCards')
    allcards = cursor.fetchall()

    # Extract card numbers from tuples
    allcard_numbers = [card[0] for card in allcards]
    
    if code in allcard_numbers:
        userId = session.get('id')
        cursor.execute('UPDATE CART SET GiftCard = %s WHERE UserID = %s', (code, userId,))
        flash('The gift card has been applied', 'success')
        session['applied_gift_card'] = code
    else:
        flash('The gift card number is not valid.', 'warning')
    
    return redirect('/cart')


@app.route('/remove_gift_card', methods=['POST'])
def remove_gift_card():
    userId = session.get('id')
    connection = getDbConnection()
    cursor = connection.cursor()

    try:
        cursor.execute('UPDATE Cart SET GiftCard = NULL WHERE UserID = %s', (userId,))
        connection.commit()
        session.pop('applied_gift_card', None)
        flash('The gift card has been removed.', 'success')
    except Exception as e:
        flash('An error occurred while removing the gift card.', 'warning')
    finally:
        cursor.close()
        connection.close()

    return redirect('/cart')

@app.route('/recipes')
def recipes():
    search_query = request.args.get('search', '').strip()
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    recipes = []

    try:
        if search_query:
            cursor.execute("""
                SELECT r.RecipeID, r.RecipeName, r.Ingredients, r.Instructions, r.ImageURL, p.Name AS ProductName
                FROM Recipes r
                JOIN Products p ON r.ProductID = p.ProductID
                WHERE p.Name LIKE %s
            """, ('%' + search_query + '%',))
        else:
            cursor.execute("""
                SELECT r.RecipeID, r.RecipeName, r.Ingredients, r.Instructions, r.ImageURL, p.Name AS ProductName
                FROM Recipes r
                JOIN Products p ON r.ProductID = p.ProductID
            """)
        recipes = cursor.fetchall()
    except Exception as e:
        flash('An error occurred while retrieving the recipes.', 'warning')
    finally:
        cursor.close()
        connection.close()

    return render_template('customer/recipes.html', recipes=recipes, search_query=search_query)

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    connection = getDbConnection()
    cursor = connection.cursor()
    cursor.execute('SELECT r.RecipeID, r.RecipeName, r.Ingredients, r.Instructions, r.ImageURL, p.Name AS ProductName '
                   'FROM Recipes r JOIN Products p ON r.ProductID = p.ProductID WHERE r.RecipeID = %s', (recipe_id,))
    recipe = cursor.fetchone()
    cursor.close()
    
    if recipe:
        recipe = {
            'RecipeID': recipe[0],
            'RecipeName': recipe[1],
            'Ingredients': recipe[2],
            'Instructions': recipe[3],
            'ImageURL': recipe[4],
            'ProductName': recipe[5]
        }
    
    return render_template('customer/recipe_detail.html', recipe=recipe)

@app.route('/view_gift_cards')
@require_role(1)
def view_gift_cards():
    user_id = session.get('id')
    try:
        with getDbConnection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT ugc.DatePurchased, gc.CardNumber, gc.Balance, gco.GiftCardName, gco.Value, gco.Image
                    FROM UserGiftCards ugc
                    JOIN GiftCards gc ON ugc.GiftCardID = gc.GiftCardID
                    JOIN GiftCardOption gco ON gc.Type = gco.GiftCardOptionID
                    WHERE ugc.UserID = %s
                """, (user_id,))
                gift_cards = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching gift cards: {e}", 'danger')
        gift_cards = []

    return render_template('customer/view_gift_cards.html', gift_cards=gift_cards, format_date=format_date)

def process_payment(user_id, order_id, type, card_number, card_holder):
    connection = getDbConnection()
    cursor = connection.cursor(dictionary=True)
    created_date = datetime.now()

    if type == "Subscription":
        # getting total price from BoxOrders
        sql = "SELECT * FROM BoxOrders WHERE BoxOrderID = %s"
    else:
        sql = "SELECT * FROM Orders WHERE OrderID = %s"
    
    cursor.execute(sql, (order_id,))
    order = cursor.fetchone()
    total_price = float(order['TotalPrice'])
    gst = total_price / 1.15 * 0.15
    gst = format(gst, ".2f")
    total_price = format(total_price, ".2f")

    # insert into Invoices
    sql = """
        INSERT INTO Invoices (UserID, InvoiceDate, DueDate, TotalAmount, GSTAmount, Status) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (user_id, created_date, created_date, total_price, gst, "paid")
    cursor.execute(sql, params)
    invoice_id = cursor.lastrowid
    connection.commit()

    # insert into Payments
    if type == "Subscription":
        sql = """
            INSERT INTO Payments (BoxOrderID, InvoiceID, CardNumber, CardHolder, Type, CreatedAt) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
    else:
        sql = """
            INSERT INTO Payments (OrderID, InvoiceID, CardNumber, CardHolder, Type, CreatedAt) 
            VALUES (%s, %s, %s, %s, %s, %s) 
        """
    
    params = (order_id, invoice_id, card_number, card_holder, type, created_date)
    cursor.execute(sql, params)
    connection.commit()

    cursor.close()
    connection.close()
    flash('You have made your payment successfully.', 'success')