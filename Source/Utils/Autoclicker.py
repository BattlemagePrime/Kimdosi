import cv2
import numpy as np
import pyautogui
import time
import logging
from pathlib import Path
from typing import List, Optional, Tuple


class AutoClicker:
    def __init__(self, images_dir: Path, results_path: Path, confidence: float = 0.85):
        """
        Initialize AutoClicker with directory containing button/popup images to match
        
        Args:
            images_dir: Directory containing reference images to match
            results_path: Directory to store logs and screenshots
            confidence: Confidence threshold for image matching (0-1)
        """
        self.images_dir = images_dir
        self.results_path = results_path
        self.confidence = confidence
        self.reference_images = []
        self.setup_logging()
        self.load_images()
        
        # Safety settings for pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def setup_logging(self):
        """Setup logging configuration"""
        self.results_path.mkdir(exist_ok=True)
        log_file = self.results_path / "autoclicker.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def load_images(self):
        """Load all reference images from the images directory"""
        for img_path in self.images_dir.glob("*.png"):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.reference_images.append((img_path.stem, img))
                logging.info(f"Loaded reference image: {img_path.name}")
            else:
                logging.warning(f"Failed to load image: {img_path}")

    def find_match(self, screen: np.ndarray) -> Optional[Tuple[str, Tuple[int, int]]]:
        """
        Find matching reference image in screenshot
        
        Returns:
            Tuple of (image_name, (x, y)) if match found, None otherwise
        """
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        
        best_match = None
        best_val = 0
        best_name = None
        
        for name, template in self.reference_images:
            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > self.confidence and max_val > best_val:
                best_val = max_val
                best_match = max_loc
                best_name = name
        
        if best_match:
            return best_name, best_match
        return None

    def click_match(self, match_info: Tuple[str, Tuple[int, int]], screenshot: np.ndarray):
        """Click on matched location with offset to hit center of button"""
        name, (x, y) = match_info
        template = [t[1] for t in self.reference_images if t[0] == name][0]
        h, w = template.shape
        
        center_x = x + w // 2
        center_y = y + h // 2
        
        try:
            pyautogui.click(center_x, center_y)
            logging.info(f"Clicked {name} at ({center_x}, {center_y})")
            
            # Save screenshot with click location marked
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            marked_img = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            cv2.rectangle(marked_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(marked_img, (center_x, center_y), 5, (0, 0, 255), -1)
            
            screenshot_path = self.results_path / f"click_{name}_{timestamp}.png"
            cv2.imwrite(str(screenshot_path), marked_img)
            
        except Exception as e:
            logging.error(f"Failed to click {name}: {str(e)}")

    def run(self, duration: int = 60):
        """
        Run autoclicker for specified duration
        
        Args:
            duration: How long to run in seconds
        """
        if not self.reference_images:
            logging.error("No reference images loaded")
            return
            
        logging.info(f"Starting autoclicker for {duration} seconds")
        end_time = time.time() + duration
        
        try:
            while time.time() < end_time:
                # Capture screen
                screen = np.array(pyautogui.screenshot())
                
                # Look for matches
                match = self.find_match(screen)
                if match:
                    self.click_match(match, screen)
                
                # Short sleep to prevent excessive CPU usage
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logging.info("Autoclicker stopped by user")
        except Exception as e:
            logging.error(f"Autoclicker error: {str(e)}")
        finally:
            logging.info("Autoclicker finished")