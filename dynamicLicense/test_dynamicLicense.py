from commonLib.CommonLib_IPC import CommonLibIPC
import logging
import os

class TestDynamicLicense:

    def __init__(self, commonLib: CommonLibIPC):
        self.comLib = commonLib
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_license_info(self, lic_path, name_hdr):
        try:
            with open(lic_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith(name_hdr + ":"):
                        _, value = line.split(":", 1)
                        return value.strip()
        except Exception as e:
            print(f"An unexpected error occurred: {e}", flush=True)
            return None
   
    def test_activate_valid_license(self, license_file: str, restart_codesys: bool) -> bool:
        """ precondition: 
        * DUT is reachable 
        * remove existing license files 
        """
        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return False
        
        if not self.comLib.remove_license():
            self.logger.error("Failed to remove existing license files. Aborting test.")
            return False
        
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return False

        """ step 1: activate license """
        status_code, response = self.comLib.activate_license(token, license_file, restart_codesys)
        if status_code == 200:
            if response.get("errCode") == 0 and response.get("AlreadyActivated") == False:
                self.logger.debug(f"License activation successful. Response: {response}")
            else:
                self.logger.error(f"License activation failed. Response: {response}")
                return False
        else:
            self.logger.error(f"License activation failed with status code {status_code}. Response: {response}")
            return False
        
        """ step 2: power cycle the controller """
        if not self.comLib.power_cycle():
            self.logger.error("Failed to power cycle the controller.")
            return False
        
        # wait for controller to reboot
        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return False

        """ step 3: activate the license again """
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return False
        
        status_code, response = self.comLib.activate_license(token, license_file, restart_codesys)
        if status_code == 200:
            if response.get("errCode") == 0 and response.get("AlreadyActivated") == True:
                self.logger.debug(f"License activation successful. Response: {response}")
            else:
                self.logger.error(f"License activation failed. Response: {response}")
                return False
        else:
            self.logger.error(f"License activation failed with status code {status_code}. Response: {response}")
            return False
        
        return True
    
    def test_activate_invalid_license(self, license_base_path: str, license_file: list, restart_codesys: bool) -> bool:
        """ precondition: 
        * DUT is reachable 
        * remove existing license files 
        """

        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return False
        
        if not self.comLib.remove_license():
            self.logger.error("Failed to remove existing license files. Aborting test.")
            return False
        
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return False

        for license in license_file:
            logging.debug(f"Testing with license file: {license}")
            license_path = os.path.join(license_base_path, license)

            """ step 1: activate license """
            status_code, response = self.comLib.activate_license(token, license_path, restart_codesys, True)
            if status_code != 200:
                # TODO: check response 
                self.logger.debug(f"License activation failed as expected")
            else:
                self.logger.error(f"License activation successfully. It should be failed! Response code: {status_code}")
                return False
    
        return True
    
    def test_get_status(self, license_base_path: str, license_file: list, restart_codesys: bool) -> bool:
        """ precondition: 
        * DUT is reachable 
        * remove existing license files 
        """

        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return False
        
        if not self.comLib.remove_license():
            self.logger.error("Failed to remove existing license files. Aborting test.")
            return False
        
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return False
        
        """ step 1: get status """
        status_code, response = self.comLib.get_license_status(token)
        if status_code == 200:
            if isinstance(response, list) and len(response) == 0:
                self.logger.debug(f"Response is an empty list as expected.")
            else:
                print("Response has data:", response)
                return False
        else:
            self.logger.error(f"Getting license status failed: {status_code}. Response: {response}")
            return False
        
        exp_response = []
        # test for every license in the list
        for license in license_file:

            logging.debug(f"Testing with license file: {license}")
            license_path = os.path.join(license_base_path, license)

            # get me_order from license file
            order_number = self._get_license_info(license_path, 'me_order_number')
            if not order_number:
                logging.error("ME ordernumber not found in the license file")
                return False
            
            # get license name from license file
            license_name = self._get_license_info(license_path, 'codesys_feature_name')
            if not license_name:
                logging.error("Codesys feature name not found in the license file")
                return False
            
            # update the expected response
            lic = {
                "name": license_name,
                "me_order": order_number
            }
            exp_response.append(lic)
                    
            """ step 2: activate a valid license """
            status_code, response = self.comLib.activate_license(token, license_path, restart_codesys)
            if status_code == 200:
                if response.get("errCode") == 0 and response.get("AlreadyActivated") == False:
                    self.logger.debug(f"License activation successful. Response: {response}")
                else:
                    self.logger.error(f"License activation failed. Response: {response}")
                    return False
            else:
                self.logger.error(f"License activation failed with status code {status_code}. Response: {response}")
                return False
            
            """ step 3: get status again """
            status_code, response = self.comLib.get_license_status(token)
            if status_code == 200:
                if all(elem in exp_response for elem in response):
                    self.logger.debug(f"License found in response: {response}")
                else:
                    self.logger.error(f"Expected license {exp_response} not found in response: {response}.")
                    return False
            else:
                self.logger.error(f"Getting license status failed: {status_code}. Response: {response}")
                return False
            
        return True
        


    