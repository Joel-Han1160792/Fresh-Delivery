from flask import Flask, g, session

from app.config.helpers import format_date, format_nz_currency, format_time


app = Flask(__name__)

from app import views_all
from app import views_manager
from app import views_customer
from app import views_staff


app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_time'] = format_time
app.jinja_env.filters['format_nz_currency'] = format_nz_currency

@app.before_request
def before_request():
    user_id = session.get('id')
    if user_id:
        g.cart_item_count = views_customer.get_cart_item_count(user_id)
        g.unread_notification_count = views_customer.load_notification_counts(user_id)
        g.application_status = views_customer.get_application_status(user_id)

    else:
        g.cart_item_count = 0
        g.unread_notification_count = 0
        g.application_status =  None
    
    # inquiries =views_all.getInquiryList()
