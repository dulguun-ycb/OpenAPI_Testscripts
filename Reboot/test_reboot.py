import logging
import time
from commonLib.CommonLib_IPC import CommonLibIPC

class TestReboot:

    def __init__(self, commonLib: CommonLibIPC):
        self.comLib = commonLib
        self.logger = logging.getLogger(__name__)

    def test_reboot(self) -> bool:
        """ precondition: DUT is available """

        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable before reboot.")
            return False
        
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return False
        
        """ step 1: execute reboot """
        status_code = self.comLib.reboot(token)
        if status_code == 200:
            logging.debug(f"Reboot successful. Response: {str(status_code)}")
        else:
            logging.error(f"Reboot failed. Response: {str(status_code)}")
            return False

        time.sleep(5)

        # wait for controller to reboot
        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after reboot.")
            return False

        return True
