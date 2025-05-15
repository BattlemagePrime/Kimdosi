from pathlib import Path
import json
import shutil
import zipfile
from typing import Dict, Any
from datetime import datetime
import time
from .vm_manager import create_vm_manager, VMManager

class TransferManager:
    def __init__(self, workspace_root: Path = None):
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent.parent
        self.workspace_root = workspace_root
        self.tool_transfer_path = workspace_root / "Tool_Transfer"
        self.binary_transfer_path = workspace_root / "Binary_Transfer"
        self.tools_root = workspace_root / "Tools"

    def prepare_analysis(self, analysis_config: Dict[str, Any]) -> None:
        """
        Prepare the analysis by setting up transfer folders and copying required files
        
        Args:
            analysis_config: Dictionary containing analysis configuration including tools and binary settings
        
        Raises:
            FileNotFoundError: If tools or binary paths don't exist
            PermissionError: If unable to create/modify transfer directories
            Exception: For other unexpected errors
        """
        try:
            # Prepare Tool_Transfer directory
            self._prepare_directory(self.tool_transfer_path)
            
            # Save analysis configuration
            config_path = self.tool_transfer_path / "analysis_config.json"
            with open(config_path, "w") as f:
                json.dump(analysis_config, f, indent=4)
            
            # Copy selected static tools
            self._copy_selected_tools(analysis_config["static_tools"])
            
            # Copy selected dynamic tools
            self._copy_selected_tools(analysis_config["dynamic_tools"])
            
            # Copy binary to Binary_Transfer
            self._prepare_directory(self.binary_transfer_path)
            binary_source = Path(analysis_config["binary"]["path"])
            if not binary_source.exists():
                raise FileNotFoundError(f"Binary file not found: {binary_source}")
            shutil.copy2(binary_source, self.binary_transfer_path / binary_source.name)
            
            # Create zip file of Tool_Transfer contents
            tools_zip = self._create_tools_zip()
            
            # Send files to VM
            if "vm" in analysis_config:
                self._send_to_vm(
                    tools_zip,
                    self.binary_transfer_path / binary_source.name,
                    analysis_config["vm"]
                )
            
        except Exception as e:
            # Clean up transfer directories in case of error
            self._cleanup_transfer_directories()
            raise e

    def _prepare_directory(self, directory: Path) -> None:
        """Create empty directory, removing existing content if necessary"""
        directory.mkdir(exist_ok=True)
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def _copy_selected_tools(self, tool_config: Dict[str, bool]) -> None:
        """Copy selected tools to the Tool_Transfer directory"""
        for tool_name, enabled in tool_config.items():
            if enabled:
                tool_path = self.tools_root / tool_name
                if not tool_path.exists():
                    raise FileNotFoundError(f"Tool not found: {tool_name}")
                dest_path = self.tool_transfer_path / tool_name
                if tool_path.is_dir():
                    shutil.copytree(tool_path, dest_path)
                else:
                    shutil.copy2(tool_path, dest_path)

    def _cleanup_transfer_directories(self) -> None:
        """Clean up transfer directories in case of error"""
        try:
            if self.tool_transfer_path.exists():
                shutil.rmtree(self.tool_transfer_path)
            if self.binary_transfer_path.exists():
                shutil.rmtree(self.binary_transfer_path)
        except Exception:
            pass  # Ignore cleanup errors

    def _create_tools_zip(self) -> Path:
        """Create a zip file containing all files in the Tool_Transfer directory
        
        Returns:
            Path to the created zip file
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        zip_path = self.tool_transfer_path / f"tools_{timestamp}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add each file and directory to the zip
            for item in self.tool_transfer_path.iterdir():
                if item.name != zip_path.name:  # Skip the zip file itself
                    if item.is_file():
                        zipf.write(item, item.name)
                    elif item.is_dir():
                        for file_path in item.rglob("*"):
                            if file_path.is_file():
                                # Get relative path from Tool_Transfer directory
                                rel_path = file_path.relative_to(self.tool_transfer_path)
                                zipf.write(file_path, rel_path)
        return zip_path

    def _send_to_vm(self, tools_zip: Path, binary_path: Path, vm_config: Dict[str, Any]) -> None:
        """Send tools and binary to the virtual machine"""
        # Ensure transfer directories exist
        self.tool_transfer_path.mkdir(exist_ok=True)
        self.binary_transfer_path.mkdir(exist_ok=True)

        # Create VM manager
        vm_manager = create_vm_manager(vm_config["type"], vm_config.get("hypervisor_path"))
        
        # Start VM and optionally restore snapshot
        success, error = vm_manager.start_vm(vm_config["path"], vm_config.get("snapshot"))
        if not success:
            raise Exception(f"Failed to start VM: {error}")
            
        # Poll for VM readiness with timeout
        timeout = time.time() + 30  # 30 second timeout
        while time.time() < timeout:
            ready, error = vm_manager.check_vm_ready(vm_config["path"])
            if ready:
                break
            time.sleep(1)  # Wait 1 second before checking again
        else:
            raise Exception("Timed out waiting for VM to become ready")
            
        # Get desktop path based on username
        desktop_path = fr"C:\Users\{vm_config['username']}\Desktop"
        
        # First transfer both files to ensure they're available before unzipping
        
        # Transfer tools.zip
        tools_dest = fr"{desktop_path}\tools.zip"
        success, error = vm_manager.copy_to_guest(
            vm_config["path"],
            str(tools_zip),
            tools_dest,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to copy tools to VM: {error}")
            
        # Transfer binary
        binary_dest = fr"{desktop_path}\binary{binary_path.suffix}"
        success, error = vm_manager.copy_to_guest(
            vm_config["path"],
            str(binary_path), 
            binary_dest,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to copy binary to VM: {error}")

        # Now that both files are transferred, attempt to unzip tools
        self._unzip_tools_in_vm(vm_manager, vm_config, tools_dest, fr"{desktop_path}\tools")

    def _unzip_tools_in_vm(self, vm_manager: VMManager, vm_config: Dict[str, Any], tools_zip_path: str, desktop_path: str) -> None:
        """Unzip tools and malware archives in VM after confirming successful transfer"""
        base_desktop = fr"C:\Users\{vm_config['username']}\Desktop"
        
        # First create Analysis_Results directory
        success, error = vm_manager.run_program_in_guest(
            vm_config["path"],
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            f'-command "New-Item -ItemType Directory -Path \'{base_desktop}\Analysis_Results\' -Force"',
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to create Analysis_Results directory: {error}")

        print("[DEBUG] Created Analysis_Results directory")

        # Now unzip the tools
        success, error = vm_manager.run_program_in_guest(
            vm_config["path"],
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            f'-command "Expand-Archive -Path \'{tools_zip_path}\' -DestinationPath \'{base_desktop}\' -Force"',
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to unzip tools in VM: {error}")

        print("[DEBUG] Unzipped tools successfully")

        # Update config with correct VM paths
        config_path = self.tool_transfer_path / "analysis_config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        # Handle malware unzipping if it's a zip file
        binary_vm_path = fr"{base_desktop}\binary{Path(config['binary']['path']).suffix}"
        if binary_vm_path.lower().endswith('.zip'):
            # Create malware extraction directory
            malware_dir = fr"{base_desktop}\Binaries"
            success, error = vm_manager.run_program_in_guest(
                vm_config["path"],
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                f'-command "New-Item -ItemType Directory -Path \'{malware_dir}\' -Force"',
                vm_config["username"],
                vm_config["password"]
            )
            if not success:
                raise Exception(f"Failed to create malware directory: {error}")

            # Unzip malware with password if provided
            unzip_command = f'-command "'
            if config['binary'].get('password'):
                # Use 7-Zip if password is needed
                unzip_command += fr'& "C:\Program Files\7-Zip\7z.exe" x -p{config["binary"]["password"]} -o"{malware_dir}" "{binary_vm_path}"'
            else:
                # Use PowerShell Expand-Archive if no password needed
                unzip_command += f'Expand-Archive -Path \'{binary_vm_path}\' -DestinationPath \'{malware_dir}\' -Force'
            unzip_command += '"'

            success, error = vm_manager.run_program_in_guest(
                vm_config["path"],
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                unzip_command,
                vm_config["username"],
                vm_config["password"]
            )
            if not success:
                raise Exception(f"Failed to unzip malware in VM: {error}")

            print("[DEBUG] Unzipped malware successfully")

            # Update the binary path to point to the first file in the malware directory
            success, error = vm_manager.run_program_in_guest(
                vm_config["path"],
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                f'-command "$file = Get-ChildItem \'{malware_dir}\' -File | Select-Object -First 1; Write-Output $file.FullName"',
                vm_config["username"],
                vm_config["password"]
            )
            if not success:
                raise Exception(f"Failed to get extracted malware path: {error}")

            # Update binary path to point to extracted file
            config["binary"]["vm_path"] = fr"{malware_dir}\{Path(config['binary']['path']).stem}"
        else:
            # Not a zip file, use the original binary path
            config["binary"]["vm_path"] = binary_vm_path

        # Add results path
        config["results_path"] = fr"{base_desktop}\Analysis_Results"
        
        # Write updated config back
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)