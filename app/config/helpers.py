import functools
from flask import Flask, flash, redirect, session, url_for

def format_date(value, format='%d/%m/%Y'):
    """Format a datetime object as a date string."""
    if value is None:
        return ""
    return value.strftime(format)

def format_time(delta):
    # Convert timedelta to total seconds
    total_seconds = int(delta.total_seconds())
    # Calculate hours and minutes
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    # Format and return time string
    return '{:02d}:{:02d}'.format(hours, minutes)

def require_role(role):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('loggedin') != True or session.get('role') < role:
                flash("You have no access!", "danger")
                return redirect(url_for('logout'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def format_nz_currency(value):
    if value is None:
        return ""
    return f"NZ${value:,.2f}"
