import requests
from bs4 import BeautifulSoup
import icalendar
import uuid
from datetime import datetime, timedelta
import pytz
import os
import json
import re

# URL for the lunch menu
MENU_URL = "https://myschoolmenus.com/organizations/1543/sites/11029/menus/74432"
# Path to store the generated ICS file
ICS_PATH = "lunch_calendar.ics"
# Timezone - adjust to your local timezone
TIMEZONE = pytz.timezone('America/New_York')
# Debug info file
DEBUG_FILE = "debug_info.txt"

def save_debug_info(content, title="Debug Information"):
    """Save debug information to a file."""
    with open(DEBUG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"\n\n{'='*50}\n{title}\n{'='*50}\n")
        f.write(content)

def debug_page_structure(url):
    """Extract and save information about the page structure for debugging."""
    try:
        print(f"Fetching {url} for debugging...")
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save the whole HTML for inspection
        save_debug_info(soup.prettify(), "Full HTML")
        
        # Find potential data in script tags (often contains JSON data)
        script_data = []
        for script in soup.find_all('script'):
            script_content = script.string
            if script_content and ('menu' in script_content.lower() or 'food' in script_content.lower()):
                script_data.append(script_content)
        
        if script_data:
            save_debug_info("\n".join(script_data), "Potential Data in Scripts")
        
        # Look for elements that might contain menu information
        debug_output = []
        
        # Elements with day, date, menu, or food in class name
        for keyword in ['day', 'date', 'menu', 'food', 'lunch']:
            elements = soup.select(f'[class*="{keyword}"]')
            if elements:
                debug_output.append(f"\nElements with '{keyword}' in class ({len(elements)}):")
                for i, elem in enumerate(elements[:10]):  # Limit to first 10
                    class_str = ' '.join(elem.get('class', []))
                    text = elem.get_text(strip=True)[:50]
                    debug_output.append(f"{i+1}. Tag: {elem.name}, Class: {class_str}, Text: {text}")
                if len(elements) > 10:
                    debug_output.append(f"...and {len(elements) - 10} more")
        
        # Look for date patterns in the text
        date_pattern = re.compile(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b', re.IGNORECASE)
        
        date_elements = []
        for elem in soup.find_all(text=date_pattern):
            parent = elem.parent
            date_elements.append((parent.name, parent.get('class', []), elem))
        
        if date_elements:
            debug_output.append("\nElements containing date patterns:")
            for i, (tag, classes, text) in enumerate(date_elements[:20]):
                class_str = ' '.join(classes)
                debug_output.append(f"{i+1}. Tag: {tag}, Class: {class_str}, Text: {text.strip()[:50]}")
        
        # Save the debug output
        save_debug_info("\n".join(debug_output), "Page Structure Analysis")
        
        # Check for network requests (API endpoints)
        # This is more difficult without a browser, but we can look for clues in the HTML
        api_hints = re.findall(r'(api|json|data).*?["\']([^"\']+)["\']', str(soup))
        if api_hints:
            save_debug_info("\n".join([f"{i+1}. {hint[1]}" for i, hint in enumerate(api_hints[:30])]), "Potential API Endpoints")
        
        print("Debug information saved to", DEBUG_FILE)
        
    except Exception as e:
        print(f"Error in debug_page_structure: {e}")
        save_debug_info(f"Error: {str(e)}", "Debug Error")

def try_multiple_parsing_strategies(soup):
    """Try multiple parsing strategies to extract menu data."""
    menu_by_date = {}
    
    strategies = [
        try_calendar_parsing,
        try_list_parsing,
        try_table_parsing,
        try_json_extraction
    ]
    
    for strategy in strategies:
        print(f"Trying {strategy.__name__}...")
        result = strategy(soup)
        if result:
            print(f"Success with {strategy.__name__}!")
            menu_by_date.update(result)
    
    return menu_by_date

def try_calendar_parsing(soup):
    """Try parsing calendar-style menu layout."""
    menu_by_date = {}
    
    # Try different selectors for day elements
    for day_selector in ['.calendar-day', '.menu-day', '.day', '[class*="day"]']:
        days = soup.select(day_selector)
        if not days:
            continue
            
        print(f"Found {len(days)} potential day elements with selector: {day_selector}")
        
        for day in days:
            # Try to extract date
            date_obj = None
            
            # Try different methods to find date
            for date_selector in ['.date', '.day-date', 'h3', 'h4', '.header']:
                date_elem = day.select_one(date_selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Try different date formats
                    for date_format in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            date_obj = datetime.strptime(date_text, date_format).date()
                            break
                        except ValueError:
                            continue
                    
                    if date_obj:
                        break
            
            if not date_obj:
                continue
                
            # Extract menu items
            menu_items = []
            
            # Try different selectors for menu items
            for item_selector in ['.menu-item', '.food-item', 'li', '[class*="item"]']:
                items = day.select(item_selector)
                if items:
                    for item in items:
                        item_text = item.get_text(strip=True)
                        if item_text:
                            menu_items.append(item_text)
                    break
            
            if menu_items:
                menu_by_date[date_obj] = menu_items
    
    return menu_by_date

def try_list_parsing(soup):
    """Try parsing list-style menu layout."""
    menu_by_date = {}
    
    # Look for date headers followed by lists
    headers = soup.select('h2, h3, h4, h5')
    
    for header in headers:
        date_text = header.get_text(strip=True)
        date_obj = None
        
        # Try to parse date from header
        for date_format in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
            try:
                date_obj = datetime.strptime(date_text, date_format).date()
                break
            except ValueError:
                continue
        
        if not date_obj:
            continue
            
        # Look for lists following this header
        next_elem = header.find_next_sibling()
        if next_elem and next_elem.name in ['ul', 'ol']:
            menu_items = [item.get_text(strip=True) for item in next_elem.find_all('li')]
            if menu_items:
                menu_by_date[date_obj] = menu_items
    
    return menu_by_date

def try_table_parsing(soup):
    """Try parsing table-style menu layout."""
    menu_by_date = {}
    
    tables = soup.select('table')
    for table in tables:
        # Look for date in table header or caption
        date_obj = None
        caption = table.find('caption')
        if caption:
            date_text = caption.get_text(strip=True)
            for date_format in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                try:
                    date_obj = datetime.strptime(date_text, date_format).date()
                    break
                except ValueError:
                    continue
        
        if not date_obj:
            # Try to find date in table header
            headers = table.select('th')
            for header in headers:
                date_text = header.get_text(strip=True)
                for date_format in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                    try:
                        date_obj = datetime.strptime(date_text, date_format).date()
                        break
                    except ValueError:
                        continue
                if date_obj:
                    break
        
        if date_obj:
            # Extract menu items from table cells
            menu_items = []
            cells = table.select('td')
            for cell in cells:
                item_text = cell.get_text(strip=True)
                if item_text:
                    menu_items.append(item_text)
            
            if menu_items:
                menu_by_date[date_obj] = menu_items
    
    return menu_by_date

def try_json_extraction(soup):
    """Try to extract menu data from embedded JSON."""
    menu_by_date = {}
    
    # Look for script tags that might contain JSON data
    scripts = soup.find_all('script')
    
    for script in scripts:
        if not script.string:
            continue
            
        # Look for JSON-like patterns
        json_pattern = re.compile(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}')
        matches = json_pattern.findall(script.string)
        
        for match in matches:
            if 'menu' in match.lower() or 'food' in match.lower() or 'lunch' in match.lower():
                try:
                    data = json.loads(match)
                    # Process extracted JSON data
                    # This would need custom handling based on the JSON structure
                    save_debug_info(json.dumps(data, indent=2), "Extracted JSON")
                except json.JSONDecodeError:
                    continue
    
    return menu_by_date

def fetch_and_parse_menu():
    """Fetch menu data from the school menu website and parse it."""
    try:
        # Fetch the menu webpage
        print(f"Fetching menu from {MENU_URL}...")
        response = requests.get(MENU_URL)
        response.raise_for_status()
        
        # Save debug information first
        with open(DEBUG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"Debug information for {MENU_URL}\nGenerated on {datetime.now()}\n")
        
        # Save debug information about the page structure
        debug_page_structure(MENU_URL)
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try multiple parsing strategies
        menu_by_date = try_multiple_parsing_strategies(soup)
        
        print(f"Found menu items for {len(menu_by_date)} days")
        return menu_by_date
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching menu data: {e}")
        save_debug_info(f"Error fetching menu data: {e}", "Fetch Error")
        return {}
    except Exception as e:
        print(f"Error parsing menu data: {e}")
        save_debug_info(f"Error parsing menu data: {e}", "Parse Error")
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
    print("Starting menu scraper...")
    menu_by_date = fetch_and_parse_menu()
    if menu_by_date:
        success = create_ical_feed(menu_by_date)
        if success:
            print("Calendar feed updated successfully!")
        else:
            print("Failed to update calendar feed: No menu events created.")
    else:
        print("Failed to update calendar feed: No menu data available.")
        # Create a minimal calendar with a debug note
        cal = icalendar.Calendar()
        cal.add('prodid', '-//School Lunch Menu Calendar//example.com//')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', 'School Lunch Menu')
        cal.add('X-WR-CALDESC', 'Daily school lunch menu items')
        
        # Add a single event explaining the issue
        event = icalendar.Event()
        event.add('uid', f"debug-{datetime.now().date()}-{uuid.uuid4()}@example.com")
        event.add('summary', 'Menu Fetch Failed')
        event.add('description', 'The script was unable to fetch menu data. Please check the debug_info.txt file in the repository.')
        today = datetime.now().date()
        event.add('dtstart', today)
        event.add('dtend', today + timedelta(days=1))
        event.add('transp', 'TRANSPARENT')
        cal.add_component(event)
        
        with open(ICS_PATH, 'wb') as f:
            f.write(cal.to_ical())
        print("Created minimal calendar with debug information.")

if __name__ == "__main__":
    main()
