import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import paho.mqtt.client as mqtt
import json


class MQTTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote panel manager")
        self.client = None
        self.connected = False

        # Connection Frame
        connection_frame = ttk.LabelFrame(root, text="Connection Settings")
        connection_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # Broker Address
        ttk.Label(connection_frame, text="Broker:").grid(row=0, column=0, sticky="w")
        self.broker_entry = ttk.Entry(connection_frame)
        self.broker_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.broker_entry.insert(0, "panel.ekoncept.pl")

        # Port
        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, sticky="w")
        self.port_entry = ttk.Entry(connection_frame, width=6)
        self.port_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.port_entry.insert(0, "443")

        # WebSocket Path
        ttk.Label(connection_frame, text="WS Path:").grid(row=1, column=0, sticky="w")
        self.ws_path_entry = ttk.Entry(connection_frame)
        self.ws_path_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.ws_path_entry.insert(0, "/mqtt")

        # Username
        ttk.Label(connection_frame, text="Username:").grid(row=2, column=0, sticky="w")
        self.username_entry = ttk.Entry(connection_frame)
        self.username_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Password
        ttk.Label(connection_frame, text="Password:").grid(row=2, column=2, sticky="w")
        self.password_entry = ttk.Entry(connection_frame, show="*")
        self.password_entry.grid(row=2, column=3, sticky="ew", padx=5, pady=2)

        # Access Code Frame
        code_frame = ttk.LabelFrame(root, text="Access Code (6 characters case insensitive)")
        code_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.code_entry = ttk.Entry(code_frame)
        self.code_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        # Add input validation
        self.code_entry.configure(validate="key")
        self.code_entry['validatecommand'] = (
            self.code_entry.register(self.validate_code), '%P')

        # Command Buttons Frame
        command_frame = ttk.LabelFrame(root, text="Commands")
        command_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        ttk.Button(command_frame, text="Update Config",
                   command=self.send_update_config).grid(row=0, column=0, padx=5, pady=2)

        ttk.Button(command_frame, text="Update Password",
                   command=self.send_update_password).grid(row=0, column=1, padx=5, pady=2)

        # New "Send Message" button
        ttk.Button(command_frame, text="Send Message",
                   command=self.send_message).grid(row=0, column=2, padx=5, pady=2)

        # Status Frame
        status_frame = ttk.Frame(root)
        status_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.connect_button = ttk.Button(status_frame, text="Connect", command=self.connect)
        self.connect_button.pack(side="left", padx=5)

        self.disconnect_button = ttk.Button(status_frame, text="Disconnect",
                                            command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.pack(side="left", padx=5)

        # Configure grid weights
        root.grid_columnconfigure(0, weight=1)
        connection_frame.grid_columnconfigure(1, weight=1)
        code_frame.grid_columnconfigure(0, weight=1)
        command_frame.grid_columnconfigure((0, 1, 2), weight=1)

    def validate_code(self, new_value):
        """Validate access code input (max 6 characters)"""
        return len(new_value) <= 6

    def connect(self):
        broker = self.broker_entry.get()
        port = self.port_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        ws_path = self.ws_path_entry.get().strip()

        if not broker:
            messagebox.showerror("Error", "Broker address is required")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return

        try:
            self.client = mqtt.Client(transport="websockets")
            self.client.ws_set_options(path=ws_path)
            self.client.tls_set()

            if username or password:
                self.client.username_pw_set(username, password)

            self.client.connect(broker, port, 60)
            self.client.loop_start()
            self.connected = True
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def disconnect(self):
        if self.client and self.connected:
            self.client.disconnect()
            self.client.loop_stop()
            self.connected = False
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)

    def send_update_config(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to broker")
            return

        code = self.code_entry.get()
        if len(code) != 6:
            messagebox.showerror("Error", "Access code must contain 6 characters")
            return

        domain = simpledialog.askstring("Update Config", "Enter domain:")
        if not domain:
            return

        topic_prefix = simpledialog.askstring("Update Config", "Enter topic prefix:")
        if not topic_prefix:
            return

        payload = {
            "command": "update_config",
            "domain": domain,
            "topic_prefix": topic_prefix
        }
        self.publish_command(payload)

    def send_update_password(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to broker")
            return

        code = self.code_entry.get()
        if len(code) != 6:
            messagebox.showerror("Error", "Access code must contain 6 characters")
            return

        new_password = simpledialog.askstring("Update Password", "Enter new password:")
        if not new_password:
            return

        payload = {
            "command": "update_password",
            "new_password": new_password
        }
        self.publish_command(payload)

    def send_message(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to broker")
            return

        code = self.code_entry.get()
        if len(code) != 6:
            messagebox.showerror("Error", "Access code must contain 6 characters")
            return

        user_message = simpledialog.askstring("Send Message", "Enter your message:")
        if not user_message:
            return

        payload = {
            "command": "show_message",
            "message": user_message
        }
        self.publish_command(payload)

    def publish_command(self, payload):
        try:
            code = self.code_entry.get()
            code = code.upper()
            topic = f"service/{code}/configuration"
            json_payload = json.dumps(payload, indent=2)
            self.client.publish(topic, json_payload)
            messagebox.showinfo("Success", f"Published to {topic}:\n{json_payload}")
        except Exception as e:
            messagebox.showerror("Publish Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTApp(root)
    root.mainloop()
