import json
import subprocess
import time
from pathlib import Path
import logging
from datetime import datetime
from .Autoclicker import AutoClicker
from .File_collector import FileCollector
from .Portool import Portool
from .Randomize import Randomizer

class Overseer:
    def __init__(self, config_path: str = r"C:\Users\Victim\Desktop\analysis_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.desktop_path = Path(config_path).parent
        self.tools_path = self.desktop_path / "Tools"
        self.results_path = Path(self.config.get("results_path", self.desktop_path / "Analysis"))
        self.utils_path = Path(__file__).parent
        self.setup_logging()

    def _load_config(self):
        """Load and parse the configuration file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            if not config:
                raise ValueError("Failed to parse configuration file")
            return config
        except Exception as e:
            raise Exception(f"Failed to read or parse configuration file: {str(e)}")

    def setup_logging(self):
        """Setup logging configuration"""
        self.results_path.mkdir(exist_ok=True)
        log_file = self.results_path / "overseer.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def run_static_analysis(self):
        """Run static analysis tools"""
        if not self.config.get("static_tools"):
            return

        logging.info("Starting static analysis phase")
        
        if self.config["static_tools"].get("Capa", False):
            logging.info("Running Capa analysis")
            capa_path = self.tools_path / "Capa" / "capa.exe"
            if capa_path.exists():
                try:
                    output_file = self.results_path / "capa_results.txt"
                    with open(output_file, 'w') as f:
                        subprocess.run(
                            [str(capa_path), self.config["binary"]["vm_path"]], 
                            stdout=f, 
                            stderr=subprocess.PIPE,
                            text=True
                        )
                    logging.info("Capa analysis completed successfully")
                except Exception as e:
                    logging.error(f"Error running Capa: {str(e)}")
            else:
                logging.warning(f"Capa executable not found at {capa_path}")

        if self.config["static_tools"].get("Yara", False):
            logging.info("Running Yara analysis")
            yara_path = self.tools_path / "Yara" / "yara64.exe"
            yara_rules = self.tools_path / "Yara" / "yara_rules" / "*.yar"
            if yara_path.exists():
                try:
                    output_file = self.results_path / "yara_results.txt"
                    with open(output_file, 'w') as f:
                        subprocess.run(
                            [str(yara_path), "-r", str(yara_rules), self.config["binary"]["vm_path"]], 
                            stdout=f,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                    logging.info("Yara analysis completed successfully")
                except Exception as e:
                    logging.error(f"Error running Yara: {str(e)}")
            else:
                logging.warning(f"Yara executable not found at {yara_path}")

    def setup_dynamic_tools(self):
        """Initialize and start dynamic analysis tools"""
        if not self.config.get("dynamic_tools"):
            return

        # Start File Collector if enabled
        if self.config["dynamic_tools"].get("CaptureFiles", False):
            logging.info("Starting File Collector")
            watch_paths = [
                r"C:\Users\Victim\Desktop",
                r"C:\Users\Victim\Downloads",
                r"C:\Windows\Temp"
            ]
            collector = FileCollector(watch_paths, self.results_path / "Captured_Files")
            collector.start_monitoring(duration=None)  # Run until program ends

        # Start Network Monitor (Portool) if FakeNet is enabled
        if self.config["dynamic_tools"].get("Fakenet", False):
            logging.info("Starting Network Monitor")
            portool = Portool(self.results_path / "Network_Analysis")
            portool.monitor(duration=int(self.config["procmon_settings"].get("duration", 60)))

        # Setup Autoclicker if enabled
        if self.config["dynamic_tools"].get("Autoclicker", False):
            logging.info("Starting Auto Clicker")
            images_dir = self.utils_path / "popup_images"
            clicker = AutoClicker(images_dir, self.results_path / "Autoclicker")
            clicker.run(duration=int(self.config["procmon_settings"].get("duration", 60)))

        # Setup name randomization if enabled
        if self.config["dynamic_tools"].get("RandomizeNames", False):
            logging.info("Setting up file name randomization")
            randomizer = Randomizer(self.results_path / "Randomized_Names")
            binary_dir = Path(self.config["binary"]["vm_path"]).parent
            randomizer.randomize_directory(binary_dir)

    def start_dynamic_analysis(self):
        """Start dynamic analysis tools"""
        if not self.config.get("dynamic_tools"):
            return

        logging.info("Starting dynamic analysis phase")

        # Start Procmon if enabled
        if self.config["dynamic_tools"].get("Procmon", False):
            logging.info("Starting Process Monitor")
            procmon_path = self.tools_path / "Procmon" / "Procmon64.exe"
            if procmon_path.exists():
                try:
                    procmon_log = self.results_path / "procmon.pml"
                    subprocess.Popen([
                        str(procmon_path),
                        "/AcceptEula",
                        "/Quiet",
                        "/Minimized",
                        "/BackingFile",
                        str(procmon_log)
                    ])
                    logging.info("Process Monitor started successfully")
                except Exception as e:
                    logging.error(f"Error starting Procmon: {str(e)}")
            else:
                logging.warning(f"Procmon executable not found at {procmon_path}")

        # Start FakeNet if enabled
        if self.config["dynamic_tools"].get("Fakenet", False):
            logging.info("Starting FakeNet")
            fakenet_path = self.tools_path / "Fakenet" / "fakenet.exe"
            if fakenet_path.exists():
                try:
                    subprocess.Popen([str(fakenet_path)])
                    logging.info("FakeNet started successfully")
                except Exception as e:
                    logging.error(f"Error starting FakeNet: {str(e)}")
            else:
                logging.warning(f"FakeNet executable not found at {fakenet_path}")

        # Setup ProcDump if enabled
        if self.config["dynamic_tools"].get("ProcDump", False):
            logging.info("Setting up ProcDump")
            procdump_path = self.tools_path / "ProcDump" / "procdump64.exe"
            if procdump_path.exists():
                try:
                    binary_name = Path(self.config["binary"]["vm_path"]).stem
                    dump_path = self.results_path / "dump.dmp"
                    subprocess.Popen([
                        str(procdump_path),
                        "-ma",
                        "-e",
                        "-w",
                        binary_name,
                        str(dump_path)
                    ])
                    logging.info("ProcDump monitoring configured successfully")
                except Exception as e:
                    logging.error(f"Error configuring ProcDump: {str(e)}")
            else:
                logging.warning(f"ProcDump executable not found at {procdump_path}")

    def execute_binary(self):
        """Execute the binary for analysis"""
        if not self.config["binary"].get("run", False):
            return

        logging.info("Executing binary for analysis")
        binary_path = self.config["binary"]["vm_path"]

        if not Path(binary_path).exists():
            logging.error(f"Binary not found at {binary_path}")
            return

        try:
            if self.config["binary"].get("as_admin", False):
                subprocess.run(["runas", "/user:Administrator", binary_path])
            else:
                subprocess.Popen([binary_path])
            logging.info("Binary execution started successfully")

            # Handle Procmon timer if enabled
            if (self.config.get("procmon_settings", {}).get("enabled", False) and 
                not self.config["procmon_settings"].get("disable_timer", False)):
                duration = int(self.config["procmon_settings"].get("duration", 60))
                logging.info(f"Waiting {duration} seconds for analysis")
                time.sleep(duration)

                # Stop Procmon after duration
                if self.config["dynamic_tools"].get("Procmon", False):
                    logging.info("Stopping Process Monitor")
                    procmon_path = self.tools_path / "Procmon" / "Procmon64.exe"
                    subprocess.run([str(procmon_path), "/Terminate"])
                    logging.info("Process Monitor stopped")

        except Exception as e:
            logging.error(f"Error executing binary: {str(e)}")

    def run(self):
        """Main execution flow"""
        logging.info("Starting Overseer analysis process")
        logging.info(f"Using config file: {self.config_path}")
        logging.info(f"Tools path: {self.tools_path}")
        logging.info(f"Results path: {self.results_path}")

        # Create results subdirectories
        (self.results_path / "Captured_Files").mkdir(exist_ok=True)
        (self.results_path / "Network_Analysis").mkdir(exist_ok=True)
        (self.results_path / "Autoclicker").mkdir(exist_ok=True)
        (self.results_path / "Randomized_Names").mkdir(exist_ok=True)
        (self.results_path / "Static_Analysis").mkdir(exist_ok=True)

        self.run_static_analysis()
        self.setup_dynamic_tools()
        self.start_dynamic_analysis()  # Starts Procmon, etc.
        self.execute_binary()
        
        logging.info(f"Analysis complete. Results saved to {self.results_path}")


if __name__ == "__main__":
    overseer = Overseer()
    overseer.run()