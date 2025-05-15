import os
import random
import string
import logging
from pathlib import Path
from typing import Dict

class Randomizer:
    def __init__(self, results_path: Path):
        self.results_path = results_path
        self.name_map: Dict[str, str] = {}
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        self.results_path.mkdir(exist_ok=True)
        log_file = self.results_path / "randomizer.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def _generate_random_name(self, extension: str = "") -> str:
        """Generate a random filename with optional extension"""
        length = random.randint(8, 12)
        chars = string.ascii_letters + string.digits
        random_name = ''.join(random.choice(chars) for _ in range(length))
        return random_name + extension

    def randomize_file(self, file_path: Path) -> Path:
        """Randomize a single file name and return the new path"""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        original_name = file_path.name
        if original_name in self.name_map:
            return Path(self.name_map[original_name])

        extension = file_path.suffix
        new_name = self._generate_random_name(extension)
        while (file_path.parent / new_name).exists():
            new_name = self._generate_random_name(extension)

        new_path = file_path.parent / new_name
        try:
            file_path.rename(new_path)
            self.name_map[original_name] = str(new_path)
            logging.info(f"Renamed: {original_name} -> {new_name}")
            return new_path
        except Exception as e:
            logging.error(f"Error renaming {original_name}: {str(e)}")
            raise

    def randomize_directory(self, directory: Path, recursive: bool = True) -> None:
        """Randomize all file names in a directory"""
        if not directory.exists():
            raise NotADirectoryError(f"Directory not found: {directory}")

        try:
            # First randomize files in current directory
            for item in directory.iterdir():
                if item.is_file():
                    self.randomize_file(item)
                elif item.is_dir() and recursive:
                    self.randomize_directory(item, recursive)

            # Save the name mapping
            map_file = self.results_path / "name_mapping.txt"
            with open(map_file, 'w') as f:
                for original, renamed in self.name_map.items():
                    f.write(f"{original} -> {renamed}\n")

            logging.info(f"Name mapping saved to: {map_file}")

        except Exception as e:
            logging.error(f"Error during directory randomization: {str(e)}")
            raise

    def restore_names(self) -> None:
        """Restore original file names using the saved mapping"""
        for original_name, current_path in self.name_map.items():
            try:
                current = Path(current_path)
                if current.exists():
                    new_path = current.parent / original_name
                    current.rename(new_path)
                    logging.info(f"Restored: {current.name} -> {original_name}")
            except Exception as e:
                logging.error(f"Error restoring {current_path}: {str(e)}")

    def get_original_name(self, randomized_name: str) -> str:
        """Look up original name for a randomized file"""
        for original, renamed in self.name_map.items():
            if Path(renamed).name == randomized_name:
                return original
        return randomized_name  # Return the input if not found