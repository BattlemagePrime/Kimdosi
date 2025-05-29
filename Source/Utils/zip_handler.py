import subprocess
from pathlib import Path


class ZipHandler:
    def __init__(self):
        self.seven_zip_path = Path(__file__).parent.parent.parent / "Tools" / "7z" / "7z.exe"
        if not self.seven_zip_path.exists():
            raise FileNotFoundError(f"7-Zip executable not found at {self.seven_zip_path}")

    def extract_file(self, zip_path: str, output_dir: str, password: str = None) -> bool:
        """
        Extract a zip file using 7-Zip
        
        Args:
            zip_path: Path to the zip file
            output_dir: Directory to extract to
            password: Optional password for encrypted archives
            
        Returns:
            bool: True if extraction was successful, False otherwise
        """
        try:            # Build command
            cmd = [str(self.seven_zip_path), "x", zip_path, f"-o{output_dir}", "-y"]
            if password:
                cmd.append(f"-p{password}")

            # Run 7-Zip
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return "Everything is Ok" in result.stdout

        except subprocess.CalledProcessError as e:
            if "Wrong password" in e.stderr:
                raise ValueError("Incorrect password for zip file")
            elif "Cannot open the file as archive" in e.stderr:
                raise ValueError("File is not a valid archive")
            else:
                raise RuntimeError(f"Error extracting zip file: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during extraction: {str(e)}")

    def is_encrypted(self, zip_path: str) -> bool:
        """
        Check if a zip file is password protected
        
        Args:
            zip_path: Path to the zip file
            
        Returns:
            bool: True if the archive is encrypted, False otherwise
        """
        try:
            cmd = [str(self.seven_zip_path), "l", "-slt", zip_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return "Encrypted = +" in result.stdout

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error checking zip encryption: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error checking encryption: {str(e)}")
