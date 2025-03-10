import requests
from bs4 import BeautifulSoup
import icalendar
import uuid
from datetime import datetime, timedelta
import pytz
import os

# URL for the lunch menu
MENU_URL = "https://myschoolmenus.com/organizations/1543/sites/11029/menus/74432"
# Path to store the generated ICS file
ICS_PATH = "lunch_calendar.ics"
# Timezone - adjust to your local timezone
TIMEZONE = pytz.timezone('America/New_York')

def fetch_and_parse_menu():
    """Fetch menu data from the school menu website and parse it."""
    try:
        # Fetch the menu webpage
        response = requests.get(MENU_URL)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is where you'll need to customize the parsing logic based on the actual HTML structure
        menu_by_date = {}
        
        # Example: Find menu items by date
        # The following selectors will need to be adjusted based on the actual page structure
        # Use browser developer tools to inspect the HTML and find the right selectors
        
        # Look for calendar days with menu items
        days = soup.select('.calendar-day')  # Adjust this selector
        
        for day in days:
            # Extract date information
            date_element = day.select_one('.sr-only')  # Adjust this selector
            if not date_element:
                continue
                
            # Parse the date (adjust format as needed)
            date_str = date_element.text.strip()
            try:
                date_obj = datetime.strptime(date_str, '%B %d, %Y').date()
            except ValueError:
                # Try alternative format
                try:
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
                except ValueError:
                    continue
            
            # Extract menu items
            menu_items = []
            items_elements = day.select('.item recipe-name')  # Adjust this selector
            for item in items_elements:
                menu_items.append(item.text.strip())
            
            if menu_items:
                menu_by_date[date_obj] = menu_items
        
        # If the above parsing doesn't work, you might need a different approach
        # The site might load data via JavaScript, which might require a different technique
        
        print(f"Found menu items for {len(menu_by_date)} days")
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
    return len(menu_by_date) > 0

def main():
    """Main function to update the calendar feed."""
    menu_by_date = fetch_and_parse_menu()
    if menu_by_date:
        success = create_ical_feed(menu_by_date)
        if success:
            print("Calendar feed updated successfully!")
        else:
            print("Failed to update calendar feed: No menu events created.")
    else:
        print("Failed to update calendar feed: No menu data available.")

if __name__ == "__main__":
    main()
