from datetime import datetime, time

def is_in_range(current_time, start_str, end_str):
    """
    Check if a given time (datetime.time) is within a time range.
    """
    # Convert start and end strings to time objects
    start = datetime.strptime(start_str, "%H:%M").time()
    end = datetime.strptime(end_str, "%H:%M").time()

    # Handle time range properly (e.g., even if crosses midnight)
    if start <= end:
        return start <= current_time <= end
    else:
        return current_time >= start or current_time <= end
