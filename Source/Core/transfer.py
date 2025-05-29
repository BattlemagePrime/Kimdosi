from pathlib import Path
import json
import shutil
import zipfile
from typing import Dict, Any
from datetime import datetime
import time
from .vm_manager import create_vm_manager, VMManager
from Utils.zip_handler import ZipHandler

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
        # First, always copy 7z as it's required
        seven_zip_path = self.tools_root / "7z"
        if not seven_zip_path.exists():
            raise FileNotFoundError("7-Zip tool not found in Tools/7z directory")
        dest_path = self.tool_transfer_path / "7z"
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(seven_zip_path, dest_path)
        
        # Then copy other selected tools
        for tool_name, enabled in tool_config.items():
            if enabled and tool_name != "7z":  # Skip 7z as we already copied it
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
        zip_path = self.tool_transfer_path / "tools.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add each file and directory to the zip
            for item in self.tool_transfer_path.iterdir():
                if item.name != zip_path.name:  # Skip the zip file itself
                    if item.is_file():
                        zipf.write(str(item), item.name)
                    elif item.is_dir():
                        for file_path in item.rglob("*"):
                            if file_path.is_file():
                                # Get relative path from Tool_Transfer directory
                                rel_path = file_path.relative_to(self.tool_transfer_path)
                                zipf.write(str(file_path), str(rel_path))
        return zip_path
        
    def _send_to_vm(self, tools_zip: Path, binary_path: Path, vm_config: Dict[str, Any]) -> None:
        """Send tools and binary to the virtual machine and set up the environment"""
        # Create VM manager and start VM
        print("\n=== Starting VM ===")
        vm_manager = create_vm_manager(vm_config["type"], vm_config.get("hypervisor_path"))
        success, error = vm_manager.start_vm(vm_config["path"], vm_config.get("snapshot"))
        if not success:
            raise Exception(f"Failed to start VM: {error}")
            
        # Poll for VM readiness
        self._wait_for_vm(vm_manager, vm_config)
            
        # Get desktop path and create Analysis directory
        base_desktop = fr"C:\Users\{vm_config['username']}\Desktop"
        print(f"\n=== Setting up VM directories ===\nBase desktop path: {base_desktop}")
        self._create_vm_directories(vm_manager, vm_config, base_desktop)
        
        # Transfer tools.zip and extract to Tools folder
        print("\n=== Transferring tools.zip ===")
        tools_dest = fr"{base_desktop}\tools.zip"
        success, error = vm_manager.copy_to_guest(
            vm_config["path"],
            str(tools_zip),
            tools_dest,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to copy tools to VM: {error}")

        # Create Tools directory and extract
        print("\n=== Extracting tools.zip ===")
        tools_dir = fr"{base_desktop}\Tools"
        extract_cmd = f'powershell -Command "New-Item -Path \'{tools_dir}\' -ItemType Directory -Force; Expand-Archive -Path \'{tools_dest}\' -DestinationPath \'{tools_dir}\' -Force"'
        print(f"Tools extraction command: {extract_cmd}")
        success, error = vm_manager.execute_command(
            vm_config["path"],
            extract_cmd,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to extract tools in VM: {error}")

        # Remove the tools zip file after extraction
        print("\n=== Cleaning up tools.zip ===")
        delete_cmd = f'powershell -Command "Remove-Item -Path \'{tools_dest}\' -Force"'
        print(f"Delete tools.zip command: {delete_cmd}")
        vm_manager.execute_command(
            vm_config["path"],
            delete_cmd,
            vm_config["username"],
            vm_config["password"]
        )

        # Transfer binary file to VM
        print("\n=== Transferring binary file ===")
        binary_dest = fr"{base_desktop}\{binary_path.name}"
        print(f"Binary destination: {binary_dest}")
        success, error = vm_manager.copy_to_guest(
            vm_config["path"],
            str(binary_path),
            binary_dest,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to copy binary to VM: {error}")

        # Create binary output directory
        print("\n=== Creating binary output directory ===")
        binary_output_dir = fr"{base_desktop}\Binary"
        create_dir_cmd = f'cmd /c mkdir "{binary_output_dir}" 2>nul'
        print(f"Create directory command: {create_dir_cmd}")
        success, error = vm_manager.execute_command(
            vm_config["path"],
            create_dir_cmd,
            vm_config["username"],
            vm_config["password"]
        )

        # Extract binary using 7z with simpler direct command
        print("\n=== Extracting binary file ===")
        binary_password = vm_config.get("binary_password", "")
        password_arg = f'-p{binary_password}' if binary_password else ""
        
        # Direct 7z.exe command
        extract_cmd = f'"{base_desktop}\\Tools\\7z\\7z.exe" e "{binary_dest}" {password_arg} -o"{binary_output_dir}" -y'
        print(f"Binary extraction command: {extract_cmd}")
        success, error = vm_manager.execute_command(
            vm_config["path"],
            extract_cmd,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            print(f"Binary extraction error: {error}")
            raise Exception(f"Failed to extract binary in VM: {error}")

        # Remove the binary zip file
        print("\n=== Cleaning up binary file ===")
        delete_cmd = f'del "{binary_dest}"'
        vm_manager.execute_command(
            vm_config["path"],
            delete_cmd,
            vm_config["username"],
            vm_config["password"]
        )
        print("\n=== Transfer and extraction complete ===\n")

    def _create_vm_directories(self, vm_manager: VMManager, vm_config: Dict[str, Any], base_desktop: str) -> None:
        """Create required directories in the VM"""
        # Only create Analysis directory
        analysis_dir = fr"{base_desktop}\Analysis"
        create_dir_cmd = f'powershell -Command "New-Item -Path \'{analysis_dir}\' -ItemType Directory -Force"'
        success, error = vm_manager.execute_command(
            vm_config["path"],
            create_dir_cmd,
            vm_config["username"],
            vm_config["password"]
        )
        if not success:
            raise Exception(f"Failed to create Analysis directory in VM: {error}")

    def _wait_for_vm(self, vm_manager: VMManager, vm_config: Dict[str, Any], timeout: int = 300) -> None:
        """Wait for VM to be ready, checking by trying to execute a simple command
        
        Args:
            vm_manager: The VM manager instance
            vm_config: VM configuration dictionary
            timeout: Maximum time to wait in seconds (default: 300)
        
        Raises:
            Exception: If VM is not ready within timeout period
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            success, _ = vm_manager.execute_command(
                vm_config["path"],
                "powershell -Command \"echo 'VM Ready'\"",
                vm_config["username"],
                vm_config["password"]
            )
            if success:
                return
            time.sleep(10)
        raise Exception(f"VM not ready after {timeout} seconds")