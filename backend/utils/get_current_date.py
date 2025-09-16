from datetime import datetime

# Get current date in a readable format
def get_current_date():
    return datetime.now().strftime("%B %d, %Y")

def get_current_hour():
    """Returns the current hour in HH:MM format (24-hour clock)."""
    now = datetime.now()
    return now.strftime("%H:%M")