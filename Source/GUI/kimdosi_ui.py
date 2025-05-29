from PyQt6.QtWidgets import (
    QWidget, QLabel, QComboBox, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QCheckBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox, QSizePolicy, QRadioButton,
    QFrame, QSpacerItem
)
from PyQt6.QtGui import QIcon, QPalette, QBrush, QPixmap
from PyQt6.QtCore import Qt
from pathlib import Path
import json
from Core.vm_manager import create_vm_manager
from Core.transfer import TransferManager

CONFIG_PATH = Path(__file__).parent.parent / "Configs" / "kimdosi_ui_config.json"

class KimdosiUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_preferences()

    def closeEvent(self, event):
        """Save preferences when window is closed"""
        self.save_preferences()
        event.accept()

    def init_ui(self):
        self.setWindowTitle("Kimdosi")
        self.setMinimumSize(750, 500)
        
        # Set window icon using absolute path
        icon_path = Path(__file__).parent.parent / "Images" / "kimdosi_icon.ico"
        if not icon_path.exists():
            icon_path = icon_path.with_name("Kimdosi_icon.png")  # Try PNG as fallback
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        
        # Left panel
        left_layout = QVBoxLayout()
        
        # Add sections with dynamic spacing
        hypervisor_section = self.create_hypervisor_section()
        network_section = self.create_network_section()
        vm_section = self.create_vm_section()
        binary_section = self.create_binary_section()
        
        # Set size policies for all sections
        for section in [hypervisor_section, network_section, vm_section, binary_section]:
            section.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        
        # Add sections with dynamic spacers
        left_layout.addWidget(hypervisor_section)
        left_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        left_layout.addWidget(network_section)
        left_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        left_layout.addWidget(vm_section)
        left_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        left_layout.addWidget(binary_section)
        
        # Right panel with tools section
        right_widget = self.create_tools_section()
        right_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Add both panels to main layout with proper stretch factors
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(right_widget, 1)

        # Bottom buttons
        bottom_layout = self.create_bottom_buttons()

        # Final layout
        final_layout = QVBoxLayout()
        final_layout.addLayout(main_layout)
        final_layout.addLayout(bottom_layout)

        self.setLayout(final_layout)

    def connect_save_triggers(self):
        """This method is no longer needed as we save on exit"""
        pass

    def create_hypervisor_section(self):
        group = QGroupBox("Hypervisor")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5)

        # Radio buttons in horizontal layout
        radio_widget = QWidget()
        radio_layout = QHBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        
        self.vmware_radio = QRadioButton("VMware")
        self.virtualbox_radio = QRadioButton("VirtualBox")
        self.vmware_radio.setChecked(True)  # Default to VMware
        
        radio_layout.addWidget(self.vmware_radio)
        radio_layout.addWidget(self.virtualbox_radio)
        radio_layout.addStretch()
        
        # Hypervisor path
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(4)
        
        self.hypervisor_path = QLineEdit()
        self.hypervisor_path.setPlaceholderText("Custom Installation Path (Optional)")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_hypervisor_path)
        
        path_layout.addWidget(self.hypervisor_path)
        path_layout.addWidget(browse_btn)
        
        # Add to main layout
        layout.addWidget(radio_widget)
        layout.addWidget(path_widget)
        
        group.setLayout(layout)
        return group

    def create_network_section(self):
        group = QGroupBox("Network Configuration")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5)

        # Radio buttons in horizontal layout
        radio_widget = QWidget()
        radio_layout = QHBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        
        self.hostonly_radio = QRadioButton("Host-Only")
        self.nat_radio = QRadioButton("NAT")
        self.bridged_radio = QRadioButton("Bridged")
        
        # Set Host-Only as default
        self.hostonly_radio.setChecked(True)
        
        radio_layout.addWidget(self.hostonly_radio)
        radio_layout.addWidget(self.nat_radio)
        radio_layout.addWidget(self.bridged_radio)
        radio_layout.addStretch()
        
        # Add to main layout
        layout.addWidget(radio_widget)
        
        group.setLayout(layout)
        return group

    def create_vm_section(self):
        group = QGroupBox("VM Configuration")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5)

        # VM Path
        layout.addWidget(QLabel("Select Virtual Machine Image:"))
        vm_widget = QWidget()
        vm_layout = QHBoxLayout(vm_widget)
        vm_layout.setContentsMargins(0, 0, 0, 0)
        vm_layout.setSpacing(4)
        self.vm_path = QLineEdit()
        self.vm_path.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_vmx_file)
        vm_layout.addWidget(self.vm_path)
        vm_layout.addWidget(browse_btn)
        layout.addWidget(vm_widget)

        # Snapshot
        layout.addWidget(QLabel("Select Snapshot:"))
        self.snapshot_combo = QComboBox()
        self.snapshot_combo.addItems([""])
        layout.addWidget(self.snapshot_combo)
        
        # Username/Password
        self.username = QLineEdit()
        self.username.setPlaceholderText("VM Username")
        self.password = QLineEdit() 
        self.password.setPlaceholderText("VM Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        
        group.setLayout(layout)
        return group

    def create_binary_section(self):
        group = QGroupBox("Binary/Zip")
        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(5, 5, 5, 5)

        # File selection row
        binary_widget = QWidget()
        binary_layout = QHBoxLayout(binary_widget)
        binary_layout.setContentsMargins(0, 0, 0, 0)
        self.binary_path = QLineEdit()
        self.binary_path.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_malware)
        binary_layout.addWidget(self.binary_path)
        binary_layout.addWidget(browse_btn)

        # Password field
        self.zip_password = QLineEdit()
        self.zip_password.setPlaceholderText("Zip Password (if any)")

        # Run and Admin checkboxes in a horizontal layout
        run_admin_widget = QWidget()
        run_admin_layout = QHBoxLayout(run_admin_widget)
        run_admin_layout.setContentsMargins(0, 0, 0, 0)
        self.run_check = QCheckBox("Run")
        self.admin_check = QCheckBox("As Admin")
        run_admin_layout.addWidget(self.run_check)
        run_admin_layout.addWidget(self.admin_check)
        run_admin_layout.addStretch()

        form.addRow("File:", binary_widget)
        form.addRow("Password:", self.zip_password)
        form.addRow(run_admin_widget)

        group.setLayout(form)
        return group

    def create_tools_section(self):
        group = QGroupBox("Tools")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5)

        # Static Tools frame without transparency
        static_frame = QFrame()
        static_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        static_frame.setLineWidth(1)
        static_layout = QVBoxLayout(static_frame)
        static_layout.setSpacing(6)
        static_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create title widget with checkbox
        static_title = QWidget()
        static_title_layout = QHBoxLayout(static_title)
        static_title_layout.setContentsMargins(0, 0, 0, 0)
        static_title_layout.addWidget(QLabel("Static Analysis"))
        self.static_all = QCheckBox("Select All")
        static_title_layout.addStretch()
        static_title_layout.addWidget(self.static_all)
        
        # Add custom title widget and tools to layout
        static_layout.addWidget(static_title)
        
        self.static_all.stateChanged.connect(lambda state: self.toggle_all_tools(state, self.static_tools))
        self.static_tools = {
            "Capa": QCheckBox("Capa"),
            "Yara": QCheckBox("Yara"), 
            "Exiftool": QCheckBox("Exiftool"),
            "Detect-it-Easy": QCheckBox("Detect It Easy"),
            "Floss": QCheckBox("FLOSS"),
            "ResourceExtract": QCheckBox("Resource Extract")
        }
        
        for tool in self.static_tools.values():
            static_layout.addWidget(tool)

        layout.addWidget(static_frame, 1)  # 1 stretch factor
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        
        # Dynamic Tools frame without transparency
        dynamic_frame = QFrame()
        dynamic_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        dynamic_frame.setLineWidth(1)
        dynamic_layout = QVBoxLayout(dynamic_frame)
        dynamic_layout.setSpacing(6)
        dynamic_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create title widget with checkbox
        dynamic_title = QWidget()
        dynamic_title_layout = QHBoxLayout(dynamic_title)
        dynamic_title_layout.setContentsMargins(0, 0, 0, 0)
        dynamic_title_layout.addWidget(QLabel("Dynamic Analysis"))
        self.dynamic_all = QCheckBox("Select All")
        dynamic_title_layout.addStretch()
        dynamic_title_layout.addWidget(self.dynamic_all)
        
        # Add custom title widget to layout
        dynamic_layout.addWidget(dynamic_title)
        
        self.dynamic_all.stateChanged.connect(lambda state: self.toggle_all_tools(state, self.dynamic_tools))
        
        # Create a dict without Procmon as it will be handled separately
        self.dynamic_tools = {
            "Fakenet": QCheckBox("FakeNet-NG"),
            "ProcDump": QCheckBox("ProcDump"),
            "Autoclicker": QCheckBox("Auto Clicker"),
            "CaptureFiles": QCheckBox("Capture Dropped Files"),
            "Screenshots": QCheckBox("Take Screenshots"),
            "RandomizeNames": QCheckBox("Randomize File Names")
        }
        
        # Procmon with inline settings
        procmon_widget = QWidget()
        procmon_layout = QHBoxLayout(procmon_widget)
        procmon_layout.setContentsMargins(0, 0, 0, 0)
        procmon_layout.setSpacing(10)
        
        self.dynamic_tools["Procmon"] = QCheckBox("Process Monitor")
        procmon_layout.addWidget(self.dynamic_tools["Procmon"])
        
        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(4)
        
        duration_layout.addWidget(QLabel("Duration:"))
        self.procmon_duration = QLineEdit()
        self.procmon_duration.setFixedWidth(60)
        self.procmon_duration.setText("60")
        duration_layout.addWidget(self.procmon_duration)
        
        self.procmon_disable_timer = QCheckBox("Disable Timer")
        self.procmon_disable_timer.stateChanged.connect(
            lambda: self.procmon_duration.setDisabled(self.procmon_disable_timer.isChecked())
        )
        
        procmon_layout.addWidget(duration_widget)
        procmon_layout.addWidget(self.procmon_disable_timer)
        procmon_layout.addStretch()
        
        dynamic_layout.addWidget(procmon_widget)
        
        # Add remaining dynamic tools
        for tool in self.dynamic_tools.values():
            if tool != self.dynamic_tools["Procmon"]:  # Skip Procmon as it's already added
                dynamic_layout.addWidget(tool)

        layout.addWidget(dynamic_frame, 1)  # 1 stretch factor
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        
        # Download Tools button without transparency
        self.download_btn = QPushButton("Download Tools")
        self.download_btn.clicked.connect(self.download_tools)
        layout.addWidget(self.download_btn)

        group.setLayout(layout)
        return group

    def create_bottom_buttons(self):
        layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Analysis")
        self.start_btn.clicked.connect(self.start_analysis)
        self.stop_btn = QPushButton("Stop Analysis")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.results_btn = QPushButton("Open Results")
        self.results_btn.clicked.connect(self.open_results)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.results_btn)

        return layout
        
    def toggle_all_tools(self, state, tool_dict):
        for tool in tool_dict.values():
            tool.setChecked(state == 2)  # 2 represents Qt.Checked

    def browse_vmx_file(self):
        if self.vmware_radio.isChecked():
            file_filter = "VMware Image (*.vmx)"
        else:
            file_filter = "VirtualBox Image (*.vdi)"
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Virtual Machine", "", file_filter
        )
        if file_path:
            self.vm_path.setText(file_path)
            self.update_snapshot_list()  # Update snapshots when VM is selected

    def browse_malware(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Binary/Zip File", "", "All Files (*.*)"
        )
        if file_path:
            # Convert to Path object before setting
            self.binary_path.setText(str(Path(file_path)))

    def browse_hypervisor_path(self):
        if self.vmware_radio.isChecked():
            file_filter = "VMware (vmrun.exe)"
            title = "Select VMware Installation Path"
        else:
            file_filter = "VirtualBox (VBoxManage.exe)"
            title = "Select VirtualBox Installation Path"
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", file_filter
        )
        if file_path:
            self.hypervisor_path.setText(file_path)

    def show_message(self, title, message, icon=QMessageBox.Icon.Information):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        # Make text selectable
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        # Set a minimum width to better handle long messages
        msg.setMinimumWidth(400)
        return msg.exec()

    def update_snapshot_list(self):
        """Update the snapshot combobox with available snapshots from the selected VM"""
        if not self.vm_path.text():
            return
            
        try:
            # Create VM manager based on selected hypervisor
            hypervisor = "vmware" if self.vmware_radio.isChecked() else "virtualbox"
            vm_manager = create_vm_manager(hypervisor, self.hypervisor_path.text() or None)
            
            # Get snapshots
            snapshots, error = vm_manager.get_snapshots(self.vm_path.text())
            
            # Handle error if present
            if error:
                self.show_message("Snapshot Error", error, QMessageBox.Icon.Warning)
                self.snapshot_combo.clear()
                self.snapshot_combo.addItems([""])
                return
                
            # Update combobox
            self.snapshot_combo.clear()
            if not snapshots:
                self.show_message("No Snapshots", "No snapshots found for the selected VM.", QMessageBox.Icon.Information)
                self.snapshot_combo.addItems([""])
            else:
                self.snapshot_combo.addItems([""] + snapshots)  # Add empty option first
            
        except Exception as e:
            self.show_message("Error", f"Failed to get snapshots: {str(e)}", QMessageBox.Icon.Critical)
            self.snapshot_combo.clear()
            self.snapshot_combo.addItems([""])

    def download_tools(self):
        # TODO: Implement tools download
        pass

    def start_analysis(self):
        """Start the analysis process by preparing tools and binary"""
        if not self.binary_path.text():
            self.show_message("Error", "Please select a binary/zip file to analyze", QMessageBox.Icon.Warning)
            return
            
        try:
            # Create configuration for the analysis
            analysis_config = {
                "static_tools": {name: cb.isChecked() 
                               for name, cb in self.static_tools.items()},
                "dynamic_tools": {name: cb.isChecked() 
                                for name, cb in self.dynamic_tools.items()},
                "procmon_settings": {
                    "enabled": self.dynamic_tools["Procmon"].isChecked(),
                    "duration": self.procmon_duration.text() if not self.procmon_disable_timer.isChecked() else "0",
                    "disable_timer": self.procmon_disable_timer.isChecked()
                },
                "binary": {
                    "path": self.binary_path.text(),
                    "run": self.run_check.isChecked(),
                    "as_admin": self.admin_check.isChecked()
                }
            }

            # Add VM configuration if VM is selected
            if self.vm_path.text():
                analysis_config["vm"] = {
                    "type": "vmware" if self.vmware_radio.isChecked() else "virtualbox",
                    "path": self.vm_path.text(),
                    "username": self.username.text(),
                    "password": self.password.text(),
                    "binary_password": self.zip_password.text(),  # Add binary password here
                    "hypervisor_path": self.hypervisor_path.text() or None,
                    "snapshot": self.snapshot_combo.currentText() or None
                }
            
            # Use TransferManager to prepare the analysis
            transfer_manager = TransferManager()
            transfer_manager.prepare_analysis(analysis_config)
            
            self.show_message("Success", "Analysis preparation complete", QMessageBox.Icon.Information)
            
        except Exception as e:
            self.show_message("Error", f"Failed to prepare analysis: {str(e)}", QMessageBox.Icon.Critical)

    def stop_analysis(self):
        # TODO: Implement analysis stop
        pass

    def open_results(self):
        # TODO: Implement results viewing
        pass

    def save_preferences(self):
        """Save UI preferences to config file"""
        config = {
            "vmx_path": self.vm_path.text(),
            "username": self.username.text(),
            "password": self.password.text(),
            "zip_password": self.zip_password.text(),
            "binary_path": self.binary_path.text(),
            "snapshot": self.snapshot_combo.currentText(),
            "randomize_names": self.dynamic_tools["RandomizeNames"].isChecked(),
            "run": self.run_check.isChecked(),
            "as_admin": self.admin_check.isChecked(),
            "procmon_enabled": self.dynamic_tools["Procmon"].isChecked(),
            "procmon_disable_timer": self.procmon_disable_timer.isChecked(),
            "procmon_duration": self.procmon_duration.text(),
            "tool_Capa": self.static_tools["Capa"].isChecked(),
            "tool_FakeNet": self.dynamic_tools["Fakenet"].isChecked(),
            "tool_Floss": self.static_tools["Floss"].isChecked(),
            "tool_Yara": self.static_tools["Yara"].isChecked(),
            "tool_ProcDump": self.dynamic_tools["ProcDump"].isChecked(),
            "tool_Detect-It-Easy": self.static_tools["Detect-it-Easy"].isChecked(),
            "tool_ResourceExtract": self.static_tools["ResourceExtract"].isChecked(),
            "tool_Autoclicker": self.dynamic_tools["Autoclicker"].isChecked(),
            "tool_Exiftool": self.static_tools["Exiftool"].isChecked(),
            "tool_Capture_Dropped_Files": self.dynamic_tools["CaptureFiles"].isChecked(),
            "tool_Screenshots": self.dynamic_tools["Screenshots"].isChecked()
        }
        
        try:
            # Ensure config directory exists
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            # Save config
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.show_message("Error", f"Failed to save preferences: {str(e)}", QMessageBox.Icon.Warning)

    def load_preferences(self):
        """Load UI preferences from config file"""
        if not CONFIG_PATH.exists():
            return
            
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                
            # Load VM settings
            self.vm_path.setText(config.get("vmx_path", ""))
            self.username.setText(config.get("username", ""))
            self.password.setText(config.get("password", ""))
            self.zip_password.setText(config.get("zip_password", ""))
            self.binary_path.setText(config.get("binary_path", ""))  # Add loading binary path
            
            # Load snapshot if VM path exists
            saved_snapshot = config.get("snapshot", "")
            if saved_snapshot and self.vm_path.text():
                self.update_snapshot_list()
                index = self.snapshot_combo.findText(saved_snapshot)
                if index >= 0:
                    self.snapshot_combo.setCurrentIndex(index)
            
            # Load run settings
            self.run_check.setChecked(config.get("run", False))
            self.admin_check.setChecked(config.get("as_admin", False))
            
            # Load Procmon settings
            self.dynamic_tools["Procmon"].setChecked(config.get("procmon_enabled", False))
            self.procmon_disable_timer.setChecked(config.get("procmon_disable_timer", False))
            self.procmon_duration.setText(config.get("procmon_duration", "60"))
            
            # Load static tools
            self.static_tools["Capa"].setChecked(config.get("tool_Capa", False))
            self.static_tools["Floss"].setChecked(config.get("tool_Floss", False))
            self.static_tools["Yara"].setChecked(config.get("tool_Yara", False))
            self.static_tools["Detect-it-Easy"].setChecked(config.get("tool_Detect-It-Easy", False))
            self.static_tools["ResourceExtract"].setChecked(config.get("tool_ResourceExtract", False))
            self.static_tools["Exiftool"].setChecked(config.get("tool_Exiftool", False))
            
            # Load dynamic tools
            self.dynamic_tools["Fakenet"].setChecked(config.get("tool_FakeNet", False))
            self.dynamic_tools["ProcDump"].setChecked(config.get("tool_ProcDump", False))
            self.dynamic_tools["Autoclicker"].setChecked(config.get("tool_Autoclicker", False))
            self.dynamic_tools["CaptureFiles"].setChecked(config.get("tool_Capture_Dropped_Files", False))
            self.dynamic_tools["RandomizeNames"].setChecked(config.get("randomize_names", False))
            self.dynamic_tools["Screenshots"].setChecked(config.get("tool_Screenshots", False))
            
        except Exception as e:
            self.show_message("Error", f"Failed to load preferences: {str(e)}", QMessageBox.Icon.Warning)