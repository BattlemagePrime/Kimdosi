import psutil
import socket
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict

class Portool:
    def __init__(self, results_path: Path):
        self.results_path = results_path
        self.connections: Dict[str, Set[tuple]] = defaultdict(set)
        self.dns_queries: Dict[str, List[str]] = defaultdict(list)
        self.setup_logging()

    def setup_logging(self):
        """Setup logging configuration"""
        self.results_path.mkdir(exist_ok=True)
        log_file = self.results_path / "portool.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID"""
        try:
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Unknown"

    def capture_connections(self):
        """Capture current network connections"""
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED':
                process_name = self._get_process_name(conn.pid)
                if conn.raddr:  # Remote address exists
                    connection_info = (
                        conn.laddr.ip,
                        conn.laddr.port,
                        conn.raddr.ip,
                        conn.raddr.port
                    )
                    self.connections[process_name].add(connection_info)
                    logging.info(f"Connection: {process_name} - {connection_info}")

    def _resolve_ip(self, ip: str) -> Optional[str]:
        """Attempt to resolve IP address to hostname"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            self.dns_queries[ip].append(hostname)
            return hostname
        except socket.herror:
            return None

    def analyze_connections(self):
        """Analyze captured connections and generate report"""
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.results_path / f"network_analysis_{report_time}.json"
        
        analysis = {
            "timestamp": report_time,
            "processes": {}
        }

        for process_name, connections in self.connections.items():
            process_data = {
                "connection_count": len(connections),
                "connections": []
            }

            for conn in connections:
                local_ip, local_port, remote_ip, remote_port = conn
                remote_hostname = self._resolve_ip(remote_ip)
                
                connection_data = {
                    "local": f"{local_ip}:{local_port}",
                    "remote": f"{remote_ip}:{remote_port}",
                    "remote_hostname": remote_hostname
                }
                process_data["connections"].append(connection_data)

            analysis["processes"][process_name] = process_data

        with open(report_file, 'w') as f:
            json.dump(analysis, f, indent=4)
        
        logging.info(f"Network analysis report saved to: {report_file}")

    def monitor(self, duration: int = 60):
        """Monitor network activity for specified duration"""
        logging.info(f"Starting network monitoring for {duration} seconds")
        start_time = datetime.now()
        
        try:
            while (datetime.now() - start_time).seconds < duration:
                self.capture_connections()
                
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        finally:
            self.analyze_connections()
            logging.info("Network monitoring complete")