import requests
import logging
import ipaddress
from typing import Optional
import subprocess
import paramiko
import sys
import os
import time
sys.path.append(os.path.dirname(__file__))
from HCS_PS_Controller import HCSControl 

import urllib3

# Disable only InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CommonLibIPC:

    def __init__(self, ip, usr, passwd) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.lic_file_path = '/license/dynamicLicense'
        try:
            # Validate IP address
            ipaddress.ip_address(ip)
            self.ip = ip
            self.logger.debug(f"Controller-IP is valid: {ip}")
        except ValueError:
            err = f"Controller-IP is invalid!: {ip}"
            self.logger.error(err)
            raise ValueError(err)
        
        self.usr = usr
        self.passwd = passwd
        self.api_base_url = f'https://{self.ip}/api/v1'
        
    def get_token(self) -> Optional[str]:
        try:
            response = requests.post(
                self.api_base_url + '/auth',
                json={"username": self.usr, "password": self.passwd},
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("accessToken")
        except requests.RequestException as e:
            self.logger.error(f"Failed to get token: {e}")
            return None
        
    def is_controller_reachable(self, timeout=2, attempts=15, delay=3) -> bool:

        for attempt in range(1, attempts + 1):
            try:
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', str(timeout * 1000), str(self.ip)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    self.logger.debug(f"Ping succeeded on attempt {attempt}. Controller is reachable")
                    return True
                else:
                    self.logger.debug(f"Ping attempt {attempt} failed. Retrying...")

            except Exception as e:
                self.logger.error(f"Error during ping attempt {attempt}: {e}")
                return False

            if attempt < attempts:
                time.sleep(delay)  # wait before next attempt

        self.logger.error(f"Controller with IP {self.ip} is not reachable after {attempts} attempts.")
        return False
    
    def check_time_before_restart(self, within_sec:float = 3.0, timeout=2, attempts=50, delay=0.1) -> bool:

        start_time = time.perf_counter()

        for attempt in range(1, attempts + 1):
            try:
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', str(timeout * 1000), str(self.ip)],  # Windows-Ping
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    self.logger.debug(f"Attempt {attempt}: Controller is reachable. Retrying...")
                else:
                    elapsed = time.perf_counter() - start_time
                    self.logger.debug(f"Controller is unreachable after {elapsed:.2f} seconds.")
                    if elapsed <= within_sec:
                        self.logger.debug(f"Restart within {within_sec} confirmed.")
                        return True
                    else:
                        self.logger.error(f"Restart took too long: {elapsed:.2f} seconds.")
                        return False
                
                time.sleep(delay)  # wait before next attempt

            except Exception as e:
                self.logger.error(f"Error during ping attempt {attempt}: {e}")
                return False

            if attempt < attempts:
                time.sleep(delay)  # wait before next attempt

        self.logger.error(f"Controller with IP {self.ip} is still reachable after {attempts} attempts with {delay} delay.")
        return False
    
    def get_license_status(self, token) -> tuple[int, list]:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(
                f"{self.api_base_url}/codesys_license/status",
                headers=headers,
                verify=False
            )
            response.raise_for_status()
            return response.status_code, response.json()
                
        except requests.RequestException as e:
            self.logger.error(f"Request 'license status' failed: {e}")
            return 0, [None]
        except ValueError:
            self.logger.error("Invalid JSON in response.")
            return 0, [None]

    def activate_license(self, token, license_file: str, restart_codesys: bool, expected_failed :bool = False) -> tuple[int, list]:
        headers = {"Authorization": f"Bearer {token}"}
        data = {"restart_codesys": str(restart_codesys).lower()}
        try:
            with open(license_file, "rb") as f:
                files = {"codesys_license": f}

                response = requests.post(
                    f"{self.api_base_url}/codesys_license/activate",
                    headers=headers,
                    data=data,
                    files=files,
                    verify=False,
                    timeout=10
                )
                response.raise_for_status()

            return response.status_code, response.json()
                
        except requests.RequestException as e:
            if expected_failed:
                self.logger.debug(f"Request 'activate' failed as expected: {e}")
            else:
                self.logger.error(f"Request 'activate' failed: {e}")
            return 0, []
        except ValueError:
            self.logger.error("Invalid JSON in response.")
            return 0, []
        
    def remove_license(self) -> bool:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(self.ip, username=self.usr, password=self.passwd)
            remove_cmd = f"sudo rm -f {self.lic_file_path}/*"
            stdin, stdout, stderr = ssh.exec_command(remove_cmd, get_pty=True)
            time.sleep(1)  # wait for sudo prompt
            stdin.write(self.passwd + "\n")  # send sudo password

            # Wait for command to finish
            exit_status = stdout.channel.recv_exit_status()

            if exit_status == 0:
                self.logger.debug("License files removed successfully.")
                return True
            else:
                err = stderr.read().decode().strip()
                self.logger.error(f"Failed to remove license files. Exit status {exit_status}, Error: {err}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove license files: {e}")
            return False
        finally:
            ssh.close()

    def get_initial_user(self, token) -> tuple[int, bool]:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(
                f"{self.api_base_url}/users/is-initial-user",
                headers=headers,
                verify=False
            )
            response.raise_for_status()
            return response.status_code, response.json()
                
        except requests.RequestException as e:
            self.logger.error(f"Request 'is-initial-user' failed: {e}")
            return 0, False
        except ValueError:
            self.logger.error("Invalid JSON in response.")
            return 0, False

    def factory_reset(self, token) -> int:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(
                f"{self.api_base_url}/reset/factory_reset",
                headers=headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.status_code
                
        except requests.RequestException as e:
            self.logger.error(f"Request 'factory_reset' failed: {e}")
            return 0
        except ValueError:
            self.logger.error("Invalid JSON in response.")
            return 0
        
    def reboot(self, token) -> int:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(
                f"{self.api_base_url}/reset/restart",
                headers=headers,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.status_code
                
        except requests.RequestException as e:
            self.logger.error(f"Request 'restart' failed: {e}")
            return 0
        except ValueError:
            self.logger.error("Invalid JSON in response.")
            return 0

    def power_cycle(self) -> bool:
        with HCSControl() as hcs:
            return hcs.powercycle()

