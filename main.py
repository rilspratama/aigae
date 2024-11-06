from dotenv import load_dotenv
import os
import requests
import uuid
import time
import json
import threading
import logging
from typing import List, Dict, Optional
from queue import Queue

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProxyFormat:
    def __init__(self, proxy_string: str):
        """
        Parse proxy string in format: scheme://ip:port@username:password
        or ip:port@username:password (default to http)
        """
        try:
            # Split scheme if exists
            if "://" in proxy_string:
                self.scheme, remainder = proxy_string.split("://", 1)
            else:
                self.scheme = "http"
                remainder = proxy_string
            
            # Split address and auth
            if "@" in remainder:
                address, auth = remainder.split("@", 1)
                self.ip, self.port = address.split(":", 1)
                self.username, self.password = auth.split(":", 1)
            else:
                self.ip, self.port = remainder.split(":", 1)
                self.username = self.password = None
                
        except Exception as e:
            raise ValueError(f"Invalid proxy format: {proxy_string}") from e
    
    def get_formatted_url(self) -> str:
        """Return formatted proxy URL"""
        if self.username and self.password:
            return f"{self.scheme}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.scheme}://{self.ip}:{self.port}"

class AigaeaPinger:
    def __init__(self, token: str, user_uid: str, proxy_file: str):
        """
        Initialize the AigaeaPinger
        
        Args:
            token: API token
            user_uid: User UID
            proxy_file: Path to proxy file
        """
        self.token = token
        self.user_uid = user_uid
        self.proxy_file = proxy_file
        self.running = False
        self.threads = []
        
        self.headers = {
            "authorization": f"Bearer {self.token}",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://app.aigaea.net",
            "referer": "https://app.aigaea.net/",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i"
        }

    def _load_proxies(self) -> List[str]:
        """Load proxies from file"""
        try:
            with open(self.proxy_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error loading proxy file: {str(e)}")
            return []

    def _format_proxy(self, proxy_string: str) -> Optional[Dict[str, str]]:
        """Format proxy string into proxy dict with auth"""
        try:
            proxy = ProxyFormat(proxy_string)
            formatted_url = proxy.get_formatted_url()
            
            # Return both http and https for http proxies
            if proxy.scheme == "http":
                return {
                    "http": formatted_url,
                    "https": formatted_url
                }
            # Return only matching scheme for socks proxies
            else:
                return {
                    proxy.scheme: formatted_url
                }
                
        except Exception as e:
            logger.error(f"Error formatting proxy {proxy_string}: {str(e)}")
            return None

    def _worker(self, proxy_string: str):
        """Worker thread function for each proxy"""
        proxies = self._format_proxy(proxy_string)
        if not proxies:
            logger.error(f"Invalid proxy format: {proxy_string}")
            return
            
        browser_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_string))
        
        while self.running:
            try:
                payload = {
                    "uid": self.user_uid,
                    "browser_id": browser_id,
                    "timestamp": int(time.time()),
                    "version": "1.0.0"
                }
                
                response = requests.post(
                    url="https://api.aigaea.net/api/network/ping",
                    data=json.dumps(payload),
                    headers=self.headers,
                    proxies=proxies,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Success - Proxy: {proxy_string} - Response: {data}")
                    sleep_time = data["data"]["interval"]
                    logger.info(f"Sleeping for {sleep_time} seconds")
                    time.sleep(int(sleep_time))
                else:
                    logger.error(f"Error - Proxy: {proxy_string} - Status Code: {response.status_code}")
                    time.sleep(60)  # Default sleep on error
                    
            except requests.RequestException as e:
                logger.error(f"Request Error - Proxy: {proxy_string} - Error: {str(e)}")
                time.sleep(60)  # Default sleep on error
                
            except Exception as e:
                logger.error(f"General Error - Proxy: {proxy_string} - Error: {str(e)}")
                time.sleep(60)  # Default sleep on error

    def start(self):
        """Start all worker threads"""
        self.running = True
        
        # Load proxies from file
        proxies = self._load_proxies()
        if not proxies:
            logger.error("No valid proxies found in file")
            return
            
        # Create and start a thread for each proxy
        for proxy in proxies:
            try:
                proxy_format = ProxyFormat(proxy)
                thread_name = f"Worker-{proxy_format.ip}"
                if proxy_format.username:
                    thread_name += f"-{proxy_format.username}"
                
                thread = threading.Thread(
                    target=self._worker,
                    args=(proxy,),
                    name=thread_name
                )
                thread.daemon = True
                thread.start()
                self.threads.append(thread)
            except ValueError as e:
                logger.error(f"Skipping invalid proxy: {str(e)}")
                continue
            
        logger.info(f"Started {len(self.threads)} worker threads")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Stopping all workers...")
            self.stop()

    def stop(self):
        """Stop all worker threads"""
        self.running = False
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join()
            
        logger.info("All workers stopped")

def main():
    # Get environment variables
    token = os.getenv("TOKEN")
    user_uid = os.getenv("UID")
    
    if not token or not user_uid:
        logger.error("Missing required environment variables")
        return
    
    # Create and start pinger
    pinger = AigaeaPinger(token, user_uid, "proxy.txt")
    pinger.start()

if __name__ == "__main__":
    main()