# Copyright (c) farm-ng, inc. Amiga Development Kit License, Version 0.1
import argparse
import asyncio
import json
import os
import subprocess
from typing import List

from utils.gnss_client import GnssMonitor

# import internal libs

# Must come before kivy imports
os.environ["KIVY_NO_ARGS"] = "1"

# gui configs must go before any other kivy import
from kivy.config import Config  # noreorder # noqa: E402

Config.set("graphics", "resizable", False)
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "800")
Config.set("graphics", "fullscreen", "false")
Config.set("input", "mouse", "mouse,disable_on_activity")
Config.set("kivy", "keyboard_mode", "systemanddock")

# kivy imports
from kivy.app import App  # noqa: E402
from kivy.lang.builder import Builder  # noqa: E402
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label


class BaseStationApp(App):
    """Base class for the main Kivy app."""

    def __init__(self) -> None:
        super().__init__()
        self.async_tasks: List[asyncio.Task] = []
        self.gnss_monitor = GnssMonitor()
        self.selected_location = None
        self.current_mode = "survey-in"  # Default mode
        self.load_known_locations()
        # Load initial config
        self.initial_config = None
        try:
            with open("/mnt/service_config/basestation.json", "r") as f:
                self.initial_config = json.load(f)
        except Exception as e:
            print(f"Error loading base station configuration: {e}")

    def build(self):
        """Build the Kivy application."""
        root = Builder.load_file("res/main.kv")

        # Now we can safely update the UI
        if self.initial_config:
            Clock.schedule_once(
                lambda dt: self.apply_initial_config(self.initial_config), 0
            )

        return root

    def apply_initial_config(self, config):
        """Apply initial configuration after UI is built."""
        # Set initial mode
        self.current_mode = "fixed" if config["USE_FIXED_MODE"] else "survey-in"

        # Update UI based on mode
        if config["USE_FIXED_MODE"]:
            coords = config["COORDINATES"]
            self.root.ids.current_coordinates_column.opacity = 0.5
            self.root.ids.fixed_coordinates_column.opacity = 1
            self.root.ids.switch_to_fixed_mode.disabled = True
            self.root.ids.switch_to_survey_mode.disabled = False

            # Check if these coordinates match any known location
            for loc in self.location_data:
                if (
                    abs(loc["latitude"] - coords["LATITUDE"]) < 1e-6
                    and abs(loc["longitude"] - coords["LONGITUDE"]) < 1e-6
                    and abs(loc["altitude"] - coords["ALTITUDE"]) < 0.1
                ):
                    self.selected_location = loc
                    break

            # Update UI with coordinates
            self.update_ui_with_config(coords)
        else:
            self.root.ids.current_coordinates_column.opacity = 1
            self.root.ids.fixed_coordinates_column.opacity = 0.5
            self.root.ids.switch_to_fixed_mode.disabled = False
            self.root.ids.switch_to_survey_mode.disabled = True

    def update_ui_with_config(self, coords):
        """Update UI with loaded configuration."""

        # Update right column with coordinates
        self.root.ids.selected_latitude_label.text = (
            f"Latitude: {coords['LATITUDE']:.8f}"
        )
        self.root.ids.selected_longitude_label.text = (
            f"Longitude: {coords['LONGITUDE']:.8f}"
        )
        self.root.ids.selected_altitude_label.text = (
            f"Altitude: {coords['ALTITUDE']:.2f}"
        )

        # If we found a matching known location, update the name
        if self.selected_location:
            self.root.ids.selected_name_label.text = (
                f"Name: {self.selected_location['name']}"
            )
            self.root.ids.select_location_button.text = self.selected_location["name"]

    def load_known_locations(self):
        """Load known locations from JSON file."""
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, "utils", "known-locations.json")

            with open(json_path, "r") as f:
                data = json.load(f)
                self.known_locations = [loc["name"] for loc in data["locations"]]
                # Store all location data for later use
                self.location_data = data["locations"]
        except Exception as e:
            print(f"Error loading known locations: {e}")
            print(f"Tried to load from: {json_path}")
            self.known_locations = []
            self.location_data = []

    def switch_to_survey_mode(self):
        """Switch to fixed mode."""
        self.current_mode = "survey-in"

        # Update button states
        self.root.ids.switch_to_fixed_mode.disabled = False
        self.root.ids.switch_to_survey_mode.disabled = True
        self.root.ids.current_coordinates_column.opacity = 1
        self.root.ids.fixed_coordinates_column.opacity = 0.5

    def switch_to_fixed_mode(self):
        """Switch to fixed mode."""
        self.current_mode = "fixed"
        # Enable location selection
        self.root.ids.select_location_button.disabled = False
        # Update button states
        self.root.ids.switch_to_fixed_mode.disabled = True
        self.root.ids.switch_to_survey_mode.disabled = False
        self.root.ids.current_coordinates_column.opacity = 0.5
        self.root.ids.fixed_coordinates_column.opacity = 1

    def on_mode_toggle(self, state):
        """Handle mode toggle state change."""
        self.current_mode = "fixed" if state == "down" else "survey-in"

    def show_location_selection(self):
        """Show popup with location selection buttons."""
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        scroll = ScrollView(size_hint=(1, 0.9))
        button_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        button_layout.bind(minimum_height=button_layout.setter("height"))

        for loc_name in self.known_locations:
            # Create horizontal layout for each location
            loc_box = BoxLayout(
                orientation="horizontal", size_hint_y=None, height="48dp", spacing=5
            )

            # Location selection button
            select_btn = Button(text=loc_name, size_hint_x=0.9)
            select_btn.bind(
                on_release=lambda x, ln=loc_name: self.on_location_selected(ln, popup)
            )

            # Delete button
            delete_btn = Button(
                text="✕",  # Unicode X symbol
                size_hint_x=0.1,
                background_color=(1, 0.3, 0.3, 1),  # Red color
            )
            delete_btn.bind(
                on_release=lambda x, ln=loc_name: self.confirm_delete_location(ln)
            )

            # Add buttons to horizontal layout
            loc_box.add_widget(select_btn)
            loc_box.add_widget(delete_btn)

            # Add the horizontal layout to the scrolling layout
            button_layout.add_widget(loc_box)

            # btn = Button(
            #     text=loc_name,
            #     size_hint_y=None,
            #     height='48dp'
            # )
            # btn.bind(on_release=lambda x, ln=loc_name: self.on_location_selected(ln, popup))
            # button_layout.add_widget(btn)

        scroll.add_widget(button_layout)
        content.add_widget(scroll)

        close_button = Button(text="Close", size_hint_y=0.1)
        content.add_widget(close_button)

        popup = Popup(
            title="Select Location",
            content=content,
            size_hint=(0.8, 0.8),
            auto_dismiss=True,
        )
        close_button.bind(on_release=popup.dismiss)
        popup.open()

    def on_location_selected(self, location_name, popup):
        """Handle location selection."""
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, "utils", "known-locations.json")

            with open(json_path, "r") as f:
                data = json.load(f)
                for loc in data["locations"]:
                    if loc["name"] == location_name:
                        self.selected_location = loc
                        # Update selected location labels
                        self.root.ids.selected_name_label.text = (
                            f"Selected Location: {loc['name']}"
                        )
                        self.root.ids.selected_latitude_label.text = (
                            f"Latitude: {loc['latitude']:.10f}"
                        )
                        self.root.ids.selected_longitude_label.text = (
                            f"Longitude: {loc['longitude']:.10f}"
                        )
                        self.root.ids.selected_altitude_label.text = (
                            f"Altitude: {loc['altitude']:.2f} m"
                        )
                        break
        except Exception as e:
            print(f"Error loading location data: {e}")

        popup.dismiss()

    def on_save_new_location(self):
        """Save current location as a new known location."""
        # Create popup for name input
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Add name input field
        from kivy.uix.textinput import TextInput

        name_input = TextInput(multiline=False, size_hint_y=None, height="48dp")

        # Add buttons
        button_box = BoxLayout(
            orientation="horizontal", size_hint_y=None, height="48dp", spacing=10
        )
        save_button = Button(text="Save")
        cancel_button = Button(text="Cancel")

        # Add all widgets to content
        content.add_widget(Label(text="Enter location name:"))
        content.add_widget(name_input)
        button_box.add_widget(save_button)
        button_box.add_widget(cancel_button)
        content.add_widget(button_box)

        popup = Popup(
            title="Save New Location",
            content=content,
            size_hint=(0.8, 0.8),
            auto_dismiss=False,
        )

        def save_location(instance):
            name = name_input.text.strip()
            if not name:
                return

            try:
                # Get current coordinates from labels
                lat = float(self.root.ids.latitude_label.text.split(": ")[1])
                lon = float(self.root.ids.longitude_label.text.split(": ")[1])
                alt = float(
                    self.root.ids.altitude_label.text.split(": ")[1].split(" ")[0]
                )

                # Create new location entry
                new_location = {
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": alt,
                }

                # Get the directory where the script is located
                script_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(script_dir, "utils", "known-locations.json")

                # Read existing data
                with open(json_path, "r") as f:
                    data = json.load(f)

                # Append new location
                data["locations"].append(new_location)

                # Write back to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=4)

                # Update the app's location data
                self.load_known_locations()

                popup.dismiss()

            except Exception as e:
                error_popup = Popup(
                    title="Error",
                    content=Label(text=f"Failed to save location: {str(e)}"),
                    size_hint=(0.6, 0.4),
                )
                error_popup.open()

        save_button.bind(on_release=save_location)
        cancel_button.bind(on_release=popup.dismiss)

        popup.open()

        def on_apply_location(self):
            """Apply selected location to basestation configuration."""
            if not self.selected_location:
                return

            config = {
                "USE_FIXED_MODE": True,
                "COORDINATES": {
                    "LATITUDE": self.selected_location["latitude"],
                    "LONGITUDE": self.selected_location["longitude"],
                    "ALTITUDE": self.selected_location["altitude"],
                },
            }
            with open("/mnt/service_config/basestation.json", "w") as f:
                json.dump(config, f, indent=4)

    def on_apply_location(self):
        """Apply current configuration to basestation and restart GNSS service."""
        try:
            # Prepare configuration based on current mode
            if self.current_mode == "fixed":
                if not self.selected_location:
                    error_popup = Popup(
                        title="Error",
                        content=Label(text="Please select a location first"),
                        size_hint=(0.6, 0.4),
                    )
                    error_popup.open()
                    return

                config = {
                    "USE_FIXED_MODE": True,
                    "COORDINATES": {
                        "LATITUDE": self.selected_location["latitude"],
                        "LONGITUDE": self.selected_location["longitude"],
                        "ALTITUDE": self.selected_location["altitude"],
                    },
                }
            else:  # survey-in mode
                config = {
                    "USE_FIXED_MODE": False,
                    "COORDINATES": {"LATITUDE": 0.0, "LONGITUDE": 0.0, "ALTITUDE": 0.0},
                }

            # Write configuration with sudo
            config_str = json.dumps(config, indent=4)
            subprocess.run(
                [
                    "sudo",
                    "bash",
                    "-c",
                    f"echo '{config_str}' > /mnt/service_config/basestation.json",
                ],
                check=True,
            )

            # Restart GNSS service with sudo
            uid_cmd = subprocess.run(
                ["id", "-u", "adminfarmng"], capture_output=True, text=True, check=True
            )
            uid = uid_cmd.stdout.strip()

            # Restart GNSS service with the correct command
            subprocess.run(
                [
                    "sudo",
                    "-u",
                    "adminfarmng",
                    f"XDG_RUNTIME_DIR=/run/user/{uid}",
                    "systemctl",
                    "--user",
                    "restart",
                    "farmng-gps.service",
                ],
                check=True,
            )

            # Show success popup
            success_popup = Popup(
                title="Success",
                content=Label(text="Configuration applied and GNSS service restarted"),
                size_hint=(0.6, 0.4),
            )
            success_popup.open()
            Clock.schedule_once(
                lambda dt: success_popup.dismiss(), 2
            )  # Auto-dismiss after 2 seconds

        except subprocess.CalledProcessError as e:
            error_popup = Popup(
                title="Error",
                content=Label(text=f"Failed to apply configuration: {str(e)}"),
                size_hint=(0.6, 0.4),
            )
            error_popup.open()

    def on_exit_btn(self) -> None:
        """Kills the running kivy application."""
        App.get_running_app().stop()

    def confirm_delete_location(self, location_name):
        """Show confirmation popup before deleting location."""
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)

        # Warning message
        content.add_widget(
            Label(
                text=f'Are you sure you want to delete\n"{location_name}"?',
                halign="center",
            )
        )

        # Buttons
        button_box = BoxLayout(
            orientation="horizontal", size_hint_y=None, height="48dp", spacing=10
        )

        confirm_btn = Button(text="Delete", background_color=(1, 0.3, 0.3, 1))  # Red
        cancel_btn = Button(text="Cancel")

        button_box.add_widget(confirm_btn)
        button_box.add_widget(cancel_btn)
        content.add_widget(button_box)

        confirm_popup = Popup(
            title="Confirm Delete",
            content=content,
            size_hint=(0.6, 0.3),
            auto_dismiss=False,
        )

        def do_delete(instance):
            try:
                # Get the directory where the script is located
                script_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(script_dir, "utils", "known-locations.json")

                # Read current data
                with open(json_path, "r") as f:
                    data = json.load(f)

                # Remove location
                data["locations"] = [
                    loc for loc in data["locations"] if loc["name"] != location_name
                ]

                # Write back to file
                with open(json_path, "w") as f:
                    json.dump(data, f, indent=4)

                # Reload locations
                self.load_known_locations()

                # Close both popups
                confirm_popup.dismiss()

                # Show success message
                success_popup = Popup(
                    title="Success",
                    content=Label(text=f'Location "{location_name}" deleted'),
                    size_hint=(0.6, 0.2),
                )
                success_popup.open()
                Clock.schedule_once(lambda dt: success_popup.dismiss(), 1.5)

            except Exception as e:
                error_popup = Popup(
                    title="Error",
                    content=Label(text=f"Failed to delete location: {str(e)}"),
                    size_hint=(0.6, 0.3),
                )
                error_popup.open()

        confirm_btn.bind(on_release=do_delete)
        cancel_btn.bind(on_release=confirm_popup.dismiss)

        confirm_popup.open()

    async def app_func(self):
        async def run_wrapper() -> None:
            await self.async_run(async_lib="asyncio")
            for task in self.async_tasks:
                task.cancel()

        # Add GNSS monitoring task
        self.async_tasks.append(asyncio.ensure_future(self.update_gnss_status()))

        return await asyncio.gather(run_wrapper(), *self.async_tasks)

    async def update_gnss_status(self) -> None:
        """Monitor GNSS status updates."""
        while self.root is None:
            await asyncio.sleep(1.0)

        while True:
            status = await self.gnss_monitor.update_status()
            if status:
                print(
                    f"Position: {status.latitude:.10f}, {status.longitude:.10f}, {status.altitude:.5f}"
                )
                # Update Kivy UI with the new GNSS status
                self.root.ids.latitude_label.text = f"Latitude: {status.latitude:.10f}"
                self.root.ids.longitude_label.text = (
                    f"Longitude: {status.longitude:.10f}"
                )
                self.root.ids.altitude_label.text = f"Altitude: {status.altitude:.5f} m"
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="base-station-app")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(BaseStationApp().app_func())
    except asyncio.CancelledError:
        pass
    loop.close()
