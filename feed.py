import requests
from bs4 import BeautifulSoup
import icalendar
import uuid
from datetime import datetime, timedelta
import pytz
import os
import time
import schedule
from flask import Flask, send_file

# URL for the lunch menu
MENU_URL = "https://myschoolmenus.com/organizations/1543/sites/11029/menus/74432"
# Path to store the generated ICS file
ICS_PATH = "lunch_menu.ics"
# Timezone - adjust to your local timezone
TIMEZONE = pytz.timezone('America/New_York')

app = Flask(__name__)

def fetch_and_parse_menu():
    """Fetch menu data from the school menu website and parse it."""
    try:
        # Fetch the menu webpage
        response = requests.get(MENU_URL)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is where you'll need to customize the parsing logic based on the actual HTML structure
        # The following is a placeholder implementation
        menu_by_date = {}
        
        # Example: Find menu items by date
        # Adjust the selectors based on the actual HTML structure of the page
        menu_days = soup.select('.menu-day')  # This selector will likely need adjustment
        
        for day in menu_days:
            # Extract date
            date_element = day.select_one('.date')  # Adjust selector
            if not date_element:
                continue
                
            date_str = date_element.text.strip()
            try:
                # Adjust the date parsing based on how dates are formatted on the site
                date_obj = datetime.strptime(date_str, '%B %d, %Y').date()
            except ValueError:
                continue
            
            # Extract menu items
            menu_items = []
            items_elements = day.select('.menu-item')  # Adjust selector
            for item in items_elements:
                menu_items.append(item.text.strip())
            
            if menu_items:
                menu_by_date[date_obj] = menu_items
        
        return menu_by_date
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching menu data: {e}")
        return {}
    except Exception as e:
        print(f"Error parsing menu data: {e}")
        return {}

def create_ical_feed(menu_by_date):
    """Create an iCalendar feed from the menu data."""
    # Create a calendar
    cal = icalendar.Calendar()
    cal.add('prodid', '-//School Lunch Menu Calendar//example.com//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', 'School Lunch Menu')
    cal.add('X-WR-CALDESC', 'Daily school lunch menu items')
    
    # Add events for each day's menu
    for date, menu_items in menu_by_date.items():
        event = icalendar.Event()
        
        # Create a unique ID for the event
        event.add('uid', f"lunch-{date}-{uuid.uuid4()}@example.com")
        
        # Set event title
        event.add('summary', 'School Lunch Menu')
        
        # Format the menu items into a description
        description = "Lunch Menu:\n" + "\n".join(menu_items)
        event.add('description', description)
        
        # Set the event date (all day event)
        event_date = datetime.combine(date, datetime.min.time())
        event_date = TIMEZONE.localize(event_date)
        event.add('dtstart', event_date.date())
        event.add('dtend', (event_date + timedelta(days=1)).date())
        
        # Don't block time on the calendar
        event.add('transp', 'TRANSPARENT')
        
        # Add the event to the calendar
        cal.add_component(event)
    
    # Write the calendar to a file
    with open(ICS_PATH, 'wb') as f:
        f.write(cal.to_ical())
    
    print(f"Calendar updated with {len(menu_by_date)} days of lunch menus")

def update_calendar_feed():
    """Fetch menu data and update the calendar feed."""
    menu_by_date = fetch_and_parse_menu()
    if menu_by_date:
        create_ical_feed(menu_by_date)
        print("Calendar feed updated successfully!")
    else:
        print("Failed to update calendar feed: No menu data available.")

# Flask route to serve the ICS file
@app.route('/lunch_calendar.ics')
def serve_calendar():
    return send_file(ICS_PATH, mimetype='text/calendar')

@app.route('/')
def home():
    return """
    <html>
    <head><title>School Lunch Calendar</title></head>
    <body>
        <h1>School Lunch Calendar</h1>
        <p>Subscribe to this calendar feed in your calendar application using this URL:</p>
        <code>https://your-domain.com/lunch_calendar.ics</code>
        <p>Last updated: {}</p>
    </body>
    </html>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    # Update the calendar feed initially
    update_calendar_feed()
    
    # Schedule the update to run daily
    schedule.every().day.at("06:00").do(update_calendar_feed)
    
    # Run the Flask app in a separate thread
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False)).start()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)
