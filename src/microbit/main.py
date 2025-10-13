# type: ignore
# main.py for micro:bit (v1 and v2 compatible)
from microbit import *
import music
import sys

# Detect micro:bit version for optimized serial handling
try:
    # Check if uart.any() exists (v1 specific)
    uart.any()
    MICROBIT_VERSION = 1
except AttributeError:
    MICROBIT_VERSION = 2

def send_status_event(message):
    """Send status event"""
    timestamp = running_time()
    # Format: STATUS|message|timestamp
    event_str = "STATUS|" + message + "|" + str(timestamp)
    print(event_str)

def process_command(cmd):
    """Process commands from MCP server"""
    global waiting_for_button, wait_button_type, wait_start_time, wait_timeout
    
    if cmd.startswith("MESSAGE:"):
        message = cmd[8:]
        display.scroll(message)
        send_status_event("displayed:" + message)
    if cmd.startswith("IMAGE:"):
        image = cmd[6:]
        display.show(Image(image))
        send_status_event("displayed:" + image)
    if cmd.startswith("TEMP:"):
        temp_celsius = temperature()
        timestamp = running_time()
        # Format: TEMP|temperature|timestamp
        temp_response = "TEMP|" + str(temp_celsius) + "|" + str(timestamp)
        print(temp_response)
    if cmd.startswith("WAIT_BUTTON:"):
        # Parse: WAIT_BUTTON:button:timeout
        parts = cmd.split(":")
        if len(parts) >= 3:
            wait_button_type = parts[1]  # "a", "b", or "any"
            wait_timeout = float(parts[2])
            waiting_for_button = True
            wait_start_time = running_time()
            send_status_event("waiting_for_button:" + wait_button_type)
    if cmd.startswith("MUSIC:"):
        # Parse: MUSIC:note1,note2,note3...
        notes_str = cmd[6:]  # Remove "MUSIC:" prefix
        if notes_str:
            notes = notes_str.split(",")
            try:
                music.play(notes)  # This blocks until music finishes
                send_status_event("music_played:" + str(len(notes)) + "_notes")
            except Exception as e:
                send_status_event("music_error:" + str(e))
        else:
            send_status_event("music_error:no_notes_provided")

def send_button_event(button, action):
    """Send button event"""
    timestamp = running_time()
    # Format: BUTTON|button|action|timestamp
    event_str = "BUTTON|" + button + "|" + action + "|" + str(timestamp)
    print(event_str)

def send_button_timeout():
    """Send button timeout event"""
    # Format: BUTTON_TIMEOUT|waited_for|timeout_duration
    event_str = "BUTTON_TIMEOUT|" + wait_button_type + "|" + str(wait_timeout)
    print(event_str)

def read_serial_input():
    """Read input from serial - compatible with both v1 and v2"""
    if MICROBIT_VERSION == 1:
        # v1 uses uart interface
        if uart.any():
            return uart.read(1).decode('utf-8', 'ignore')
    else:
        # v2 uses sys.stdin - non-blocking read
        try:
            import select
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1)
        except ImportError:
            # Fallback if select is not available
            try:
                # This may block briefly on v2
                return sys.stdin.read(1) if sys.stdin.readable() else None
            except:
                return None
    return None

# Global variables for button waiting
waiting_for_button = False
wait_button_type = ""
wait_start_time = 0
wait_timeout = 0

# Button state tracking
button_a_was_pressed = False
button_b_was_pressed = False

# Startup
display.show(Image.HAPPY)
sleep(1000)
display.clear()
send_status_event("ready:v" + str(MICROBIT_VERSION))

# Main loop
input_buffer = ""

while True:
    # Handle commands - version-specific input handling
    try:
        if MICROBIT_VERSION == 1:
            # v1 implementation using uart
            if uart.any():
                char = uart.read(1)
                if char:
                    if char == b'\n':
                        if input_buffer:
                            process_command(input_buffer.strip())
                            input_buffer = ""
                    else:
                        input_buffer += char.decode('utf-8', 'ignore')
        else:
            # v2 implementation using sys.stdin
            # Try line-based reading for better reliability
            try:
                # Check if input is available without blocking
                import select
                if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                    line = sys.stdin.readline().strip()
                    if line:
                        process_command(line)
            except ImportError:
                # Fallback for systems without select
                try:
                    # This approach may block briefly
                    if sys.stdin.readable():
                        line = sys.stdin.readline().strip()
                        if line:
                            process_command(line)
                except:
                    pass  # Skip if stdin not available
    except Exception as e:
        send_status_event("input_error:" + str(e))
    
    # Button monitoring when waiting for button press
    if waiting_for_button:
        # Check for timeout
        current_time = running_time()
        if (current_time - wait_start_time) >= (wait_timeout * 1000):  # Convert to milliseconds
            waiting_for_button = False
            send_button_timeout()
        else:
            # Check button states
            button_a_pressed = button_a.is_pressed()
            button_b_pressed = button_b.is_pressed()
            
            # Detect button A press (edge detection)
            if button_a_pressed and not button_a_was_pressed:
                if wait_button_type == "a" or wait_button_type == "any":
                    waiting_for_button = False
                    send_button_event("a", "pressed")
            
            # Detect button B press (edge detection)
            if button_b_pressed and not button_b_was_pressed:
                if wait_button_type == "b" or wait_button_type == "any":
                    waiting_for_button = False
                    send_button_event("b", "pressed")
            
            # Update button state tracking
            button_a_was_pressed = button_a_pressed
            button_b_was_pressed = button_b_pressed
    else:
        # Reset button state tracking when not waiting
        button_a_was_pressed = button_a.is_pressed()
        button_b_was_pressed = button_b.is_pressed()
    
    sleep(50)
