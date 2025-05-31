#!/usr/bin/env python3
import can
import time
import threading
import random
import argparse
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QSlider, QLabel, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

# CAN Message IDs
TEMP_MSG_ID = 0x123    # ID for temperature messages
FAN_MSG_ID = 0x3       # ID for fan speed messages

class CANBusInterface:
    """Interface for CAN bus communication"""
    def __init__(self, channel="vcan0", bustype="socketcan"):
        self.channel = channel
        self.bustype = bustype
        self.bus = can.interface.Bus(channel=self.channel, bustype=self.bustype)
        self.running = True
        self.last_fan_level = 0  # Changed to fan level (0-3)
        self.last_temp = 0
        
    def send_temperature(self, temp):
        """Send a temperature value over CAN bus"""
        # Ensure temperature is within valid range and convert to bytes
        temp = max(0, min(120, temp))
        temp_bytes = temp.to_bytes(1, byteorder='big')
        
        # Create and send CAN message
        msg = can.Message(arbitration_id=TEMP_MSG_ID, data=temp_bytes, is_extended_id=False)
        try:
            self.bus.send(msg)
            self.last_temp = temp
            return True
        except can.CanError as e:
            print(f"Error sending temperature: {e}")
            return False
            
    def start_listening(self, callback):
        """Start listening for CAN messages in a separate thread"""
        self.listener_thread = threading.Thread(target=self._listen_for_messages, args=(callback,))
        self.listener_thread.daemon = True
        self.listener_thread.start()
        
    def _listen_for_messages(self, callback):
        """Listen for CAN messages and call the callback for fan speed messages"""
        while self.running:
            message = self.bus.recv(timeout=1.0)
            if message and message.arbitration_id == FAN_MSG_ID:
                # Extract the raw byte value as the fan level (0-3)
                if len(message.data) > 0:
                    fan_level = message.data[0]  # Just use the first byte directly
                    self.last_fan_level = fan_level
                    if callback:
                        callback(fan_level)
    
    def stop(self):
        """Stop the CAN listener thread"""
        self.running = False
        if hasattr(self, 'listener_thread') and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1.0)


class EngineTempSimulator(QObject):
    """Simulates engine temperature behavior"""
    temp_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.current_temp = 20  # Start at ambient temp
        self.target_temp = 85   # Normal operating temp
        self.is_running = False
        self.cooling_active = False
        self.heating_rate = 0.5  # °C per second when heating
        self.cooling_rates = [0.0, 0.2, 0.4, 0.6]  # Cooling rates for fan levels 0-3
        self.ambient_cooling_rate = 0.1  # Natural cooling rate
        self.manual_control = False  # Flag for manual temperature control
        
    def start(self):
        """Start the engine simulation"""
        self.is_running = True
        if not self.manual_control:
            self.target_temp = 85  # Normal operating temp
        
    def stop(self):
        """Stop the engine simulation"""
        self.is_running = False
        self.manual_control = False
        self.target_temp = 20  # Cool down to ambient
        
    def set_target_temp(self, temp):
        """Manually set a target temperature"""
        self.target_temp = max(20, min(120, temp))
        self.manual_control = True  # Enable manual control mode
        
    def update(self, fan_level=0):
        """Update the engine temperature based on conditions"""
        # Ensure fan_level is within valid range (0-3)
        fan_level = min(3, max(0, fan_level))
        
        if not self.is_running:
            # Engine off - cool down toward ambient
            if self.current_temp > 20:
                self.current_temp -= self.ambient_cooling_rate
                if self.current_temp < 20:
                    self.current_temp = 20
            return
        
        # Calculate temperature change based on conditions
        if self.manual_control:
            # In manual mode, force temperature toward target with faster rate
            if abs(self.current_temp - self.target_temp) < 1.0:
                self.current_temp = self.target_temp
            elif self.current_temp < self.target_temp:
                self.current_temp += max(0.8, self.heating_rate)  # Faster heating in manual mode
            else:
                self.current_temp -= max(0.8, self.ambient_cooling_rate)  # Faster cooling in manual mode
        else:
            # Normal simulation mode
            if self.current_temp < self.target_temp:
                # Heating up - simulate increasing temperature with occasional fluctuations
                heat_rate = self.heating_rate * (1.0 + random.uniform(-0.1, 0.3))
                self.current_temp += heat_rate
                
                # Allow temperature to exceed target slightly to simulate real engine behavior
                if not self.manual_control and self.current_temp > self.target_temp * 1.05:
                    self.current_temp = self.target_temp * 1.05
            else:
                # Natural cooling with small random variations
                cool_rate = self.ambient_cooling_rate * (1.0 + random.uniform(-0.1, 0.2))
                self.current_temp -= cool_rate
            
        # Apply fan cooling effect based on fan level
        fan_cooling = self.cooling_rates[fan_level]
        
        # Fan is more effective at higher temperatures
        if self.current_temp > 90:
            fan_cooling *= 1.5
        
        self.current_temp -= fan_cooling
        
        # Ensure temperature stays in valid range
        self.current_temp = max(20, min(120, self.current_temp))
        self.temp_changed.emit(int(self.current_temp))


class EngineSimulatorGUI(QMainWindow):
    """GUI for engine temperature simulator"""
    def __init__(self, can_interface):
        super().__init__()
        self.can_interface = can_interface
        self.simulator = EngineTempSimulator()
        self.simulator.temp_changed.connect(self.on_temp_changed)
        self.slider_being_dragged = False
        
        # Set up GUI
        self.setWindowTitle("Engine Temperature Simulator")
        self.setGeometry(100, 100, 600, 400)
        self.setup_ui()
        
        # Start listeners and timers
        self.can_interface.start_listening(self.on_fan_level_update)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(100)  # Update 10 times per second
        
    def setup_ui(self):
        """Set up the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Temperature display
        temp_group = QGroupBox("Engine Temperature")
        temp_layout = QVBoxLayout(temp_group)
        
        self.temp_value_label = QLabel("Current: 20°C")
        self.temp_value_label.setStyleSheet("font-size: 20pt; font-weight: bold;")
        temp_layout.addWidget(self.temp_value_label)
        
        # Target temperature display
        self.target_temp_label = QLabel("Target: 85°C")
        self.target_temp_label.setStyleSheet("font-size: 14pt;")
        temp_layout.addWidget(self.target_temp_label)
        
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(20, 120)
        self.temp_slider.setValue(85)
        self.temp_slider.setTracking(True)
        self.temp_slider.valueChanged.connect(self.on_manual_temp_change)
        self.temp_slider.sliderPressed.connect(self.on_slider_pressed)
        self.temp_slider.sliderReleased.connect(self.on_slider_released)
        temp_layout.addWidget(self.temp_slider)
        
        # Slider labels
        slider_labels = QHBoxLayout()
        slider_labels.addWidget(QLabel("20°C"))
        slider_labels.addStretch()
        slider_labels.addWidget(QLabel("70°C"))
        slider_labels.addStretch()
        slider_labels.addWidget(QLabel("120°C"))
        temp_layout.addLayout(slider_labels)
        
        main_layout.addWidget(temp_group)
        
        # Fan speed display
        fan_group = QGroupBox("Fan Control")
        fan_layout = QVBoxLayout(fan_group)
        
        self.fan_value_label = QLabel("Fan Level: 0 (Off)")
        self.fan_value_label.setStyleSheet("font-size: 16pt;")
        fan_layout.addWidget(self.fan_value_label)
        
        # Fan level indicators (4 levels: 0-3)
        fan_indicator_layout = QHBoxLayout()
        for i in range(4):
            indicator = QLabel()
            indicator.setFixedSize(40, 40)
            indicator.setStyleSheet("background-color: grey; border-radius: 20px;")
            if i == 0:
                indicator.setText("Off")
            else:
                indicator.setText(f"L{i}")
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fan_indicator_layout.addWidget(indicator)
            setattr(self, f"fan_indicator_{i}", indicator)
        
        fan_layout.addLayout(fan_indicator_layout)
        main_layout.addWidget(fan_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Engine")
        self.start_button.clicked.connect(self.start_engine)
        controls_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Engine")
        self.stop_button.clicked.connect(self.stop_engine)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        self.force_temp_button = QPushButton("Force Temperature")
        self.force_temp_button.clicked.connect(self.force_temperature)
        controls_layout.addWidget(self.force_temp_button)
        
        # Temperature stress test buttons
        self.high_temp_button = QPushButton("High Temp Test")
        self.high_temp_button.clicked.connect(self.high_temp_test)
        controls_layout.addWidget(self.high_temp_button)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        controls_layout.addWidget(self.quit_button)
        
        main_layout.addLayout(controls_layout)
        
        # Status message
        self.status_label = QLabel("Engine Off")
        self.status_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        # Debug info
        self.debug_label = QLabel("CAN debug: waiting for fan messages...")
        main_layout.addWidget(self.debug_label)
    
    def start_engine(self):
        """Start the engine simulation"""
        current_target = self.temp_slider.value()
        self.simulator.start()
        if self.simulator.manual_control:
            self.simulator.set_target_temp(current_target)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Engine Running")
    
    def stop_engine(self):
        """Stop the engine simulation"""
        self.simulator.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Engine Off - Cooling Down")
    
    def force_temperature(self):
        """Force the current slider temperature"""
        temp = self.temp_slider.value()
        self.simulator.set_target_temp(temp)
        self.target_temp_label.setText(f"Target: {temp}°C")
        self.status_label.setText(f"Setting target temperature: {temp}°C")
    
    def high_temp_test(self):
        """Run a high temperature test sequence"""
        self.simulator.set_target_temp(110)
        self.temp_slider.setValue(110)
        self.target_temp_label.setText("Target: 110°C")
        self.status_label.setText("High Temperature Test Running")
    
    def on_slider_pressed(self):
        """Handle slider being pressed"""
        self.slider_being_dragged = True
    
    def on_slider_released(self):
        """Handle slider being released"""
        self.slider_being_dragged = False
        # Automatically apply target temp when slider is released
        self.force_temperature()
    
    def on_manual_temp_change(self, value):
        """Handle manual temperature slider changes"""
        self.target_temp_label.setText(f"Target: {value}°C")
    
    def on_temp_changed(self, temp):
        """Handle temperature updates from the simulator"""
        self.temp_value_label.setText(f"Current: {int(temp)}°C")
        # Send the updated temperature to the CAN bus
        self.can_interface.send_temperature(int(temp))
        
        # Update slider position to match (if not being dragged)
        if not self.slider_being_dragged:
            self.temp_slider.setValue(int(temp))
            
        # Update temperature display color based on value
        if temp < 60:
            color = "blue" 
        elif temp < 90:
            color = "green"
        elif temp < 100:
            color = "orange"
        else:
            color = "red"
            
        self.temp_value_label.setStyleSheet(f"font-size: 20pt; font-weight: bold; color: {color}")
    
    def on_fan_level_update(self, level):
        """Update GUI based on fan level received from CAN bus"""
        # Display the fan level and update the debug label
        level_names = ["Off", "Low", "Medium", "High"]
        level_label = level_names[min(level, 3)]
        self.fan_value_label.setText(f"Fan Level: {level} ({level_label})")
        
        # Log the raw CAN message for debugging
        self.debug_label.setText(f"CAN debug: Received fan level: {level} (0x{level:02X})")
        
        # Update fan indicators
        for i in range(4):
            indicator = getattr(self, f"fan_indicator_{i}")
            if i == level:
                indicator.setStyleSheet("background-color: #00AA00; border-radius: 20px; color: white; font-weight: bold;")
            else:
                indicator.setStyleSheet("background-color: grey; border-radius: 20px; color: white;")
    
    def update_simulation(self):
        """Regular timer update for simulation"""
        # Update the simulator with the latest fan level
        self.simulator.update(self.can_interface.last_fan_level)
    
    def closeEvent(self, event):
        """Clean up when closing the window"""
        self.can_interface.stop()
        event.accept()


def run_console_mode(can_interface):
    """Run the simulator in console mode (no GUI)"""
    print("Engine Temperature Simulator (Console Mode)")
    print("-------------------------------------------")
    print("Commands: start, stop, temp [value], hightemp, status, quit")
    
    simulator = EngineTempSimulator()
    
    def on_fan_level_update(level):
        level_names = ["Off", "Low", "Medium", "High"]
        level_label = level_names[min(level, 3)]
        print(f"[CAN] Received fan level: {level} ({level_label}) [0x{level:02X}]")
    
    can_interface.start_listening(on_fan_level_update)
    
    running = True
    last_update = time.time()
    last_status_time = 0
    
    while running:
        # Update simulation at regular intervals
        current_time = time.time()
        if current_time - last_update >= 0.1:  # 10 updates per second
            simulator.update(can_interface.last_fan_level)
            temp = int(simulator.current_temp)
            can_interface.send_temperature(temp)
            last_update = current_time
            
            # Print status every 2 seconds if anything changes
            if current_time - last_status_time >= 2.0:
                last_status_time = current_time
                level_names = ["Off", "Low", "Medium", "High"]
                level = min(can_interface.last_fan_level, 3)
                print(f"Temperature: {temp}°C | Fan: Level {level} ({level_names[level]}) | Target: {simulator.target_temp}°C")
        
        # Check for user input (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            cmd = sys.stdin.readline().strip().lower()
            
            if cmd == "quit":
                running = False
            elif cmd == "start":
                simulator.start()
                print("Engine started")
            elif cmd == "stop":
                simulator.stop()
                print("Engine stopped")
            elif cmd == "hightemp":
                simulator.set_target_temp(110)
                print("High temperature test started - target 110°C")
            elif cmd == "status":
                status = "running" if simulator.is_running else "stopped"
                print(f"Engine is {status}")
                print(f"Temperature: {int(simulator.current_temp)}°C")
                print(f"Target temperature: {simulator.target_temp}°C")
                level = min(can_interface.last_fan_level, 3)
                level_names = ["Off", "Low", "Medium", "High"]
                print(f"Fan level: {level} ({level_names[level]})")
                print(f"Manual control: {'Yes' if simulator.manual_control else 'No'}")
            elif cmd.startswith("temp "):
                try:
                    value = int(cmd.split()[1])
                    simulator.set_target_temp(value)
                    print(f"Target temperature set to {value}°C")
                except (IndexError, ValueError):
                    print("Usage: temp [value]")
            else:
                print("Unknown command")
        
        time.sleep(0.01)  # Small sleep to prevent CPU hogging
    
    can_interface.stop()
    print("Simulation ended")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Engine Temperature Simulator")
    parser.add_argument("--console", action="store_true", help="Run in console mode (no GUI)")
    parser.add_argument("--channel", default="vcan0", help="CAN bus channel")
    args = parser.parse_args()
    
    # Initialize CAN interface
    can_interface = CANBusInterface(channel=args.channel)
    
    if args.console:
        import select  # For non-blocking input in console mode
        run_console_mode(can_interface)
    else:
        # GUI mode
        app = QApplication(sys.argv)
        window = EngineSimulatorGUI(can_interface)
        window.show()
        sys.exit(app.exec())