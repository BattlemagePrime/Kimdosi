from abc import ABC, abstractmethod
import subprocess
from pathlib import Path
import os
from typing import List, Optional, Tuple
import time

def find_vmware_path() -> Optional[str]:
    """Check common VMware installation paths"""
    common_paths = [
        r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
        r"C:\Program Files\VMware\VMware Workstation\vmrun.exe",
        r"C:\Program Files (x86)\VMware\VMware Player\vmrun.exe",
        r"C:\Program Files\VMware\VMware Player\vmrun.exe"
    ]
    
    for path in common_paths:
        if Path(path).is_file():
            return path
    return None

def find_virtualbox_path() -> Optional[str]:
    """Check common VirtualBox installation paths"""
    common_paths = [
        r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
        r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe"
    ]
    
    for path in common_paths:
        if Path(path).is_file():
            return path
    return None

class VMManager(ABC):
    """Abstract base class for VM operations"""
    
    @abstractmethod
    def get_snapshots(self, vm_path: str) -> Tuple[List[str], Optional[str]]:
        """Get list of snapshots for the specified VM"""
        pass
        
    @abstractmethod
    def copy_to_guest(self, vm_path: str, host_path: str, guest_path: str, 
                      username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Copy file from host to guest VM"""
        pass
        
    @abstractmethod
    def start_vm(self, vm_path: str, snapshot: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Start VM and optionally restore to a snapshot"""
        pass

    @abstractmethod
    def check_vm_ready(self, vm_path: str) -> Tuple[bool, Optional[str]]:
        """Check if VM is running and tools are available"""
        pass

    @abstractmethod
    def run_program_in_guest(self, vm_path: str, program: str, args: str,
                             username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Execute a program in the guest VM"""
        pass

class VMwareManager(VMManager):
    def __init__(self, vmrun_path: Optional[str] = None):
        """Initialize VMware manager with optional custom vmrun path"""
        if vmrun_path:
            self.vmrun_path = vmrun_path
        else:
            default_path = find_vmware_path()
            if default_path:
                self.vmrun_path = default_path
            else:
                self.vmrun_path = "vmrun.exe"  # fallback for error handling
        
    def get_snapshots(self, vm_path: str) -> Tuple[List[str], Optional[str]]:
        try:
            if not Path(self.vmrun_path).is_file():
                return [], (
                    "VMware vmrun.exe not found. Please specify the correct path to vmrun.exe.\n"
                    "Common locations:\n"
                    "- C:\\Program Files (x86)\\VMware\\VMware Workstation\\vmrun.exe\n"
                    "- C:\\Program Files\\VMware\\VMware Workstation\\vmrun.exe\n"
                    "- C:\\Program Files (x86)\\VMware\\VMware Player\\vmrun.exe\n"
                    "- C:\\Program Files\\VMware\\VMware Player\\vmrun.exe"
                )
                
            if not Path(vm_path).is_file():
                return [], f"VM file not found at: {vm_path}"
                
            result = subprocess.run(
                [self.vmrun_path, "listSnapshots", vm_path],
                capture_output=True,
                text=True,
                check=True
            )
            # Skip the first line as it's usually a count of snapshots
            snapshots = result.stdout.splitlines()[1:]
            return [snap.strip() for snap in snapshots if snap.strip()], None
            
        except subprocess.CalledProcessError as e:
            return [], f"Error executing vmrun: {e.stderr or str(e)}"
        except FileNotFoundError as e:
            return [], f"File not found error: {str(e)}"
        except Exception as e:
            return [], f"Unexpected error: {str(e)}"

    def copy_to_guest(self, vm_path: str, host_path: str, guest_path: str,
                      username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Copy file from host to guest VM using VMware tools"""
        try:
            if not Path(self.vmrun_path).is_file():
                return False, "VMware vmrun.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            if not Path(host_path).exists():
                return False, f"Source file not found at: {host_path}"
                
            result = subprocess.run(
                [self.vmrun_path, "-gu", username, "-gp", password,
                 "copyFileFromHostToGuest", vm_path, host_path, guest_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Failed to copy file: {result.stderr}"
            return True, None
            
        except Exception as e:
            return False, f"Error copying file to VM: {str(e)}"

    def start_vm(self, vm_path: str, snapshot: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Start VMware VM and optionally restore to a snapshot"""
        try:
            if not Path(self.vmrun_path).is_file():
                return False, "VMware vmrun.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            # First revert to snapshot if specified
            if snapshot:
                result = subprocess.run(
                    [self.vmrun_path, "revertToSnapshot", vm_path, snapshot],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    return False, f"Failed to revert to snapshot: {result.stderr}"
            
            # Start the VM using Popen to avoid blocking
            process = subprocess.Popen(
                [self.vmrun_path, "start", vm_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a short time for immediate errors
            try:
                process.wait(timeout=2)
                if process.returncode != 0:
                    _, stderr = process.communicate()
                    return False, f"Failed to start VM: {stderr}"
            except subprocess.TimeoutExpired:
                # This is expected - the VM is starting in the background
                pass
            
            return True, None
            
        except Exception as e:
            return False, f"Error starting VM: {str(e)}"

    def check_vm_ready(self, vm_path: str) -> Tuple[bool, Optional[str]]:
        """Check if VMware VM is running and tools are available"""
        try:
            result = subprocess.run(
                [self.vmrun_path, "checkToolsState", vm_path],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and "running" in result.stdout.lower(), None
        except Exception as e:
            return False, str(e)

    def run_program_in_guest(self, vm_path: str, program: str, args: str,
                             username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Execute a program in the guest VM using VMware tools"""
        try:
            if not Path(self.vmrun_path).is_file():
                return False, "VMware vmrun.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            print(f"\n[DEBUG VMware] Running program in guest:")
            print(f"[DEBUG VMware] Program: {program}")
            print(f"[DEBUG VMware] Args: {args}")
            
            process = subprocess.Popen(
                [self.vmrun_path, "-gu", username, "-gp", password,
                 "runProgramInGuest", vm_path, program, args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print("[DEBUG VMware] Process started, waiting for initial response...")
            
            # Wait a short time for immediate errors
            try:
                process.wait(timeout=2)
                if process.returncode != 0:
                    stdout, stderr = process.communicate()
                    print(f"[DEBUG VMware] Process failed with return code {process.returncode}")
                    print(f"[DEBUG VMware] stdout: {stdout}")
                    print(f"[DEBUG VMware] stderr: {stderr}")
                    return False, f"Failed to run program: {stderr}"
                print("[DEBUG VMware] Process started successfully")
            except subprocess.TimeoutExpired:
                print("[DEBUG VMware] Process running in background (timeout expired as expected)")
                # This is expected - the program is running in the background
                pass
                
            return True, None
            
        except Exception as e:
            print(f"[DEBUG VMware] Unexpected error: {str(e)}")
            return False, f"Error running program in VM: {str(e)}"

class VirtualBoxManager(VMManager):
    def __init__(self, vboxmanage_path: Optional[str] = None):
        """Initialize VirtualBox manager with optional custom VBoxManage path"""
        if vboxmanage_path:
            self.vboxmanage_path = vboxmanage_path
        else:
            default_path = find_virtualbox_path()
            if default_path:
                self.vboxmanage_path = default_path
            else:
                self.vboxmanage_path = "VBoxManage.exe"  # fallback for error handling
        
    def get_snapshots(self, vm_path: str) -> Tuple[List[str], Optional[str]]:
        try:
            if not Path(self.vboxmanage_path).is_file():
                return [], (
                    "VirtualBox VBoxManage.exe not found. Please specify the correct path to VBoxManage.exe.\n"
                    "Common locations:\n"
                    "- C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe\n"
                    "- C:\\Program Files (x86)\\Oracle\\VirtualBox\\VBoxManage.exe"
                )
                
            if not Path(vm_path).is_file():
                return [], f"VM file not found at: {vm_path}"
                
            # Extract VM name from path (VirtualBox uses VM names rather than paths)
            vm_name = Path(vm_path).stem
            
            result = subprocess.run(
                [self.vboxmanage_path, "snapshot", vm_name, "list"],
                capture_output=True,
                text=True,
                check=True
            )
            # Parse VBoxManage output to extract snapshot names
            snapshots = []
            for line in result.stdout.splitlines():
                if "Name:" in line:
                    snap_name = line.split("Name:", 1)[1].strip()
                    if "UUID:" in snap_name:  # Remove UUID if present
                        snap_name = snap_name.split("UUID:", 1)[0].strip()
                    snapshots.append(snap_name)
            return snapshots, None
            
        except subprocess.CalledProcessError as e:
            return [], f"Error executing VBoxManage: {e.stderr or str(e)}"
        except FileNotFoundError as e:
            return [], f"File not found error: {str(e)}"
        except Exception as e:
            return [], f"Unexpected error: {str(e)}"

    def copy_to_guest(self, vm_path: str, host_path: str, guest_path: str,
                      username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Copy file from host to guest VM using VirtualBox tools"""
        try:
            if not Path(self.vboxmanage_path).is_file():
                return False, "VirtualBox VBoxManage.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            if not Path(host_path).exists():
                return False, f"Source file not found at: {host_path}"
                
            # Extract VM name from path (VirtualBox uses VM names rather than paths)
            vm_name = Path(vm_path).stem
            
            result = subprocess.run(
                [self.vboxmanage_path, "guestcontrol", vm_name,
                 "copyto", "--username", username, "--password", password,
                 host_path, guest_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Failed to copy file: {result.stderr}"
            return True, None
            
        except Exception as e:
            return False, f"Error copying file to VM: {str(e)}"

    def start_vm(self, vm_path: str, snapshot: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Start VirtualBox VM and optionally restore to a snapshot"""
        try:
            if not Path(self.vboxmanage_path).is_file():
                return False, "VirtualBox VBoxManage.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            # Extract VM name from path
            vm_name = Path(vm_path).stem
            
            # First revert to snapshot if specified
            if snapshot:
                result = subprocess.run(
                    [self.vboxmanage_path, "snapshot", vm_name, "restore", snapshot],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    return False, f"Failed to restore snapshot: {result.stderr}"
            
            # Start the VM using Popen to avoid blocking
            process = subprocess.Popen(
                [self.vboxmanage_path, "startvm", vm_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a short time for immediate errors
            try:
                process.wait(timeout=2)
                if process.returncode != 0:
                    _, stderr = process.communicate()
                    return False, f"Failed to start VM: {stderr}"
            except subprocess.TimeoutExpired:
                # This is expected - the VM is starting in the background
                pass
            
            return True, None
            
        except Exception as e:
            return False, f"Error starting VM: {str(e)}"

    def check_vm_ready(self, vm_path: str) -> Tuple[bool, Optional[str]]:
        """Check if VirtualBox VM is running and tools are available"""
        try:
            vm_name = Path(vm_path).stem
            result = subprocess.run(
                [self.vboxmanage_path, "guestproperty", "get", vm_name, "/VirtualBox/GuestAdd/Version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and "No value set!" not in result.stdout, None
        except Exception as e:
            return False, str(e)

    def run_program_in_guest(self, vm_path: str, program: str, args: str,
                             username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Execute a program in the guest VM using VirtualBox tools"""
        try:
            if not Path(self.vboxmanage_path).is_file():
                return False, "VirtualBox VBoxManage.exe not found"
                
            if not Path(vm_path).is_file():
                return False, f"VM file not found at: {vm_path}"
                
            # Extract VM name from path
            vm_name = Path(vm_path).stem
            
            print(f"\n[DEBUG VBox] Running program in guest:")
            print(f"[DEBUG VBox] VM Name: {vm_name}")
            print(f"[DEBUG VBox] Program: {program}")
            print(f"[DEBUG VBox] Args: {args}")
            
            process = subprocess.Popen(
                [self.vboxmanage_path, "guestcontrol", vm_name,
                 "start", "--username", username, "--password", password,
                 program, "--", args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print("[DEBUG VBox] Process started, waiting for initial response...")
            
            # Wait a short time for immediate errors
            try:
                process.wait(timeout=2)
                if process.returncode != 0:
                    stdout, stderr = process.communicate()
                    print(f"[DEBUG VBox] Process failed with return code {process.returncode}")
                    print(f"[DEBUG VBox] stdout: {stdout}")
                    print(f"[DEBUG VBox] stderr: {stderr}")
                    return False, f"Failed to run program: {stderr}"
                print("[DEBUG VBox] Process started successfully")
            except subprocess.TimeoutExpired:
                print("[DEBUG VBox] Process running in background (timeout expired as expected)")
                # This is expected - the program is running in the background
                pass
                
            return True, None
            
        except Exception as e:
            print(f"[DEBUG VBox] Unexpected error: {str(e)}")
            return False, f"Error running program in VM: {str(e)}"

def create_vm_manager(hypervisor: str, custom_path: Optional[str] = None) -> VMManager:
    """Factory function to create appropriate VM manager"""
    if hypervisor.lower() == "vmware":
        return VMwareManager(custom_path)
    elif hypervisor.lower() == "virtualbox":
        return VirtualBoxManager(custom_path)
    else:
        raise ValueError(f"Unsupported hypervisor: {hypervisor}")