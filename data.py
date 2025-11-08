
import win32gui
import time
import csv
import datetime

FILE_NAME = "activity_log01.csv"
INTERVAL_SECONDS = 5  # Log active window every 5 seconds

def get_active_window_title():
    """Retrieves the title of the currently focused window on Windows."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return "ERROR: Could not get title"

def logger():
    """Logs the timestamp and active window title to a CSV file."""
    print(f"--- Starting activity monitor. Logging to {FILE_NAME} every {INTERVAL_SECONDS} seconds. ---")
    
    # Check if file exists to determine if we need to write headers
    try:
        with open(FILE_NAME, 'r') as f:
            file_is_empty = (len(f.readlines()) == 0)
    except FileNotFoundError:
        file_is_empty = True

    with open(FILE_NAME, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        if file_is_empty:
            writer.writerow(['Timestamp', 'Window_Title'])
            print("Wrote CSV header.")

        try:
            while True:
                title = get_active_window_title()
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([now, title])
                file.flush()
                print(f"Logged: {now} | {title[:60]}...")
                time.sleep(INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            print("\n--- Monitoring stopped by user. ---")
        except Exception as e:
            print(f"\n--- An error occurred: {e} ---")

if __name__ == "__main__":
    logger()