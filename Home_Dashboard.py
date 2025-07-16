# 🏠_Home_Dashboard.py

import streamlit as st
import time
from hardware_controller import MockController, RaspberryPiController
import platform
import os

# --- Page Setup ---
st.set_page_config(page_title="Smart Home Dashboard", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")


# --- Hardware Initialization ---
# This is the core logic: Check if we are running on a Raspberry Pi.
# If so, use the RaspberryPiController; otherwise, use the MockController.
def get_controller():
    # A simple way to check if we're on a Pi is to check the platform.
    is_pi = platform.machine().startswith("arm") or platform.machine().startswith("aarch64")

    # For testing: you can force a controller like this:
    # return MockController()

    if is_pi:
        try:
            # This import will only succeed on a Pi with the RPi.GPIO library installed.
            return RaspberryPiController()
        except (ImportError, RuntimeError):
            st.warning("Could not initialize Raspberry Pi hardware. Falling back to Mock Controller.")
            return MockController()
    else:
        return MockController()


# Initialize the controller and store it in the session state to prevent
# re-initialization on every interaction.
if "hw_controller" not in st.session_state:
    st.session_state.hw_controller = get_controller()
    st.session_state.hw_controller.setup()

# Create a short alias for the controller
hw = st.session_state.hw_controller


# --- Helper Functions ---
def hex_to_rgb(hex_color):
    """Converts a hex color string to an (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


# --- UI Layout ---

# Header
st.title("🏠 Smart Home Dashboard")
st.markdown("Control and monitor your connected home devices.")

# --- Device Control ---
col1, col2 = st.columns(2)

# --- Column 1: Lighting Controls ---
with col1:
    st.header("💡 Lighting")

    with st.container(border=True):
        st.subheader("Bedroom Light")
        brightness = st.slider("Brightness", min_value=0, max_value=100, value=100, step=1, key="dimmable_light_slider")
        hw.set_dimmable_light(brightness)
        if isinstance(hw, MockController):
            st.info("This demonstrates controlling LED brightness using PWM (Pulse Width Modulation).")

    # Mood Lamp (Represented by an RGB LED)
    with st.container(border=True):
        st.subheader("RGB Mood Lamp")
        color = st.color_picker("Choose a color", "#FFFFFF", key="mood_lamp_picker")
        r, g, b = hex_to_rgb(color)
        hw.set_mood_lamp_color(r, g, b)
        if isinstance(hw, MockController):
            st.info("This controls each channel (Red, Green, Blue) of an RGB LED with three PWM signals.")


# --- Column 2: Sensors & Security ---
with col2:
    st.header("🔬 Sensors & Security")

    # Doorbell (Represented by a Push Button)
    with st.container(border=True):
        st.subheader("Doorbell")
        if isinstance(hw, MockController):
            st.info("In Mock Mode, you can press the button below to simulate the doorbell.")
            if st.button("Simulate Doorbell Press"):
                # Directly toggle the internal state of the MockController
                hw._doorbell_pressed = not hw._doorbell_pressed
                st.rerun()  # Refresh the screen to update status

        if hw.read_doorbell():
            st.success("🔔 **Ding-dong!** Someone is at the door!")
        else:
            st.write("No one at the door.")

    # Presence Sensor (Represented by an Ultrasonic Sensor)
    with st.container(border=True):
        st.subheader("Garage Proximity Sensor")
        distance = hw.get_distance()

        # Define a threshold for object detection
        detection_threshold = 20.0  # in cm

        if distance <= detection_threshold:
            st.warning(f"**Object Detected!** Distance: **{distance:.1f} cm**")
        else:
            st.info(f"All clear. Distance: **{distance:.1f} cm**")

        # Normalize the value to a 0.0-1.0 range for the progress bar
        progress_value = max(0, 100 - (distance / 3)) / 100.0
        st.progress(progress_value)  # Visual progress bar
        if isinstance(hw, MockController):
            st.info("This uses an ultrasonic sensor to measure distance.")

    # Security Camera (Represented by a Pi Camera)
    with st.container(border=True):
        st.subheader("Security Camera")

        if st.button("Take Snapshot 📸"):
            with st.spinner("Capturing image..."):
                # Define the image path
                image_path = "snapshot.jpg"

                # Use the controller to capture the image
                captured_path = hw.capture_image(image_path)

                if captured_path and os.path.exists(captured_path):
                    st.image(captured_path, caption="Live Snapshot", use_column_width=True)
                else:
                    st.error("Failed to capture image.")
        if isinstance(hw, MockController):
            st.info("This uses the Pi Camera module to capture a live image.")

# --- Footer / Cleanup ---
st.sidebar.info("Attempting to clean up GPIO resources on app exit.")
