from dotenv import load_dotenv
import os
import requests
import uuid
import time
import json
import threading
import logging
import socket
import socks
from typing import List, Dict, Optional
from requests.exceptions import RequestException
from urllib3.contrib.socks import SOCKSProxyManager
import urllib3

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
            
            # Convert port to integer
            self.port = int(self.port)
                
        except Exception as e:
            raise ValueError(f"Invalid proxy format: {proxy_string}") from e

class AigaeaPinger:
    def __init__(self, token: str, user_uid: str, proxy_file: str):
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
            "referer": "chrome-extension://cpjicfogbgognnifjgmenmaldnmeeeib",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i"
        }

    def _load_proxies(self) -> List[str]:
        try:
            with open(self.proxy_file, 'r') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception as e:
            logger.error(f"Error loading proxy file: {str(e)}")
            return []

    def _setup_socks_session(self, proxy: ProxyFormat) -> requests.Session:
        """Create a session with SOCKS proxy configuration"""
        # Create new session
        session = requests.Session()
        
        if proxy.scheme.lower() in ['socks5', 'socks4']:
            # Determine SOCKS version
            socks_version = socks.SOCKS5 if proxy.scheme.lower() == 'socks5' else socks.SOCKS4
            
            # Create a new socket
            socks_socket = socks.socksocket()
            
            # Configure the SOCKS proxy
            socks_socket.set_proxy(
                proxy_type=socks_version,
                addr=proxy.ip,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                rdns=True
            )
            
            # Create an adapter with the SOCKS proxy
            adapter = requests.adapters.HTTPAdapter(max_retries=3)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # Set the socket options
            session.proxies = {
                'http': f'{proxy.scheme}://{proxy.ip}:{proxy.port}',
                'https': f'{proxy.scheme}://{proxy.ip}:{proxy.port}'
            }
            
            if proxy.username and proxy.password:
                session.proxies = {
                    'http': f'{proxy.scheme}://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}',
                    'https': f'{proxy.scheme}://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}'
                }
            
            # Bind the socket to the session
            socks.set_default_proxy(
                proxy_type=socks_version,
                addr=proxy.ip,
                port=proxy.port,
                username=proxy.username,
                password=proxy.password,
                rdns=True
            )
            socket.socket = socks.socksocket
            
        return session

    def _worker(self, proxy_string: str):
        try:
            proxy = ProxyFormat(proxy_string)
            session = self._setup_socks_session(proxy) if proxy.scheme.lower() in ['socks5', 'socks4'] else requests.Session()
            
            browser_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_string))
            
            while self.running:
                try:
                    payload = {
                        "uid": str(self.user_uid),
                        "browser_id": browser_id,
                        "timestamp": int(time.time()),
                        "version": "1.0.0"
                    }
                    
                    if proxy.scheme.lower() in ['socks5', 'socks4']:
                        # For SOCKS proxies, use the configured session
                        response = session.post(
                            url="https://api.aigaea.net/api/network/ping",
                            json=payload,
                            headers=self.headers,
                            timeout=30,
                            verify=True
                        )
                    else:
                        # For HTTP proxies, use proxies parameter
                        proxies = {
                            "http": f"{proxy.scheme}://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}",
                            "https": f"{proxy.scheme}://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
                        } if proxy.username and proxy.password else {
                            "http": f"{proxy.scheme}://{proxy.ip}:{proxy.port}",
                            "https": f"{proxy.scheme}://{proxy.ip}:{proxy.port}"
                        }
                        
                        response = session.post(
                            url="https://api.aigaea.net/api/network/ping",
                            json=payload,
                            headers=self.headers,
                            proxies=proxies,
                            timeout=30,
                            verify=True
                        )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Success - Proxy: {proxy_string} - Response: {data}")
                        sleep_time = data["data"]["interval"]
                        logger.info(f"Sleeping for {sleep_time} seconds")
                        time.sleep(int(sleep_time))
                    else:
                        logger.error(f"Error - Proxy: {proxy_string} - Status Code: {response.status_code}")
                        time.sleep(60)
                        
                except RequestException as e:
                    logger.error(f"Request Error - Proxy: {proxy_string} - Error: {str(e)}")
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"General Error - Proxy: {proxy_string} - Error: {str(e)}")
                    time.sleep(60)
                    
        except Exception as e:
            logger.error(f"Worker Error - Proxy: {proxy_string} - Error: {str(e)}")
            return

    def start(self):
        self.running = True
        
        proxies = self._load_proxies()
        if not proxies:
            logger.error("No valid proxies found in file")
            return
            
        for proxy in proxies:
            try:
                proxy_format = ProxyFormat(proxy)
                thread_name = f"Worker-{proxy_format.ip}"
                
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
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Stopping all workers...")
            self.stop()

    def stop(self):
        self.running = False
        for thread in self.threads:
            thread.join()
        logger.info("All workers stopped")

def main():
    token = os.getenv("TOKEN")
    user_uid = os.getenv("UID")
    
    if not token or not user_uid:
        logger.error("Missing required environment variables")
        return
    
    pinger = AigaeaPinger(token, user_uid, "proxy.txt")
    pinger.start()

if __name__ == "__main__":
    main()