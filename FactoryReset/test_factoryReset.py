from commonLib.CommonLib_IPC import CommonLibIPC
import logging
import time

class TestFactoryReset:

    def __init__(self, commonLib: CommonLibIPC):
        self.comLib = commonLib
        self.logger = logging.getLogger(self.__class__.__name__)

    def test_factory_reset(self) -> list:
        result = [False, False, False]
        """ precondition: DUT is available """

        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return result
        
        # get token to authenticate API requests
        token = self.comLib.get_token()
        if not token:
            self.logger.error("Failed to obtain authentication token. Aborting test.")
            return result
        
        """ step 1: execute factory reset """
        status_code = self.comLib.factory_reset(token)
        if status_code == 200:
            logging.debug(f"factory reset successful. Response: {str(status_code)}")
            result[0] = True
        else:
            logging.error(f"factory reset failed. Response: {str(status_code)}")

        """ step 2: check that Controller restarts after ~3 seconds """
        exp_time = 3.0
        if self.comLib.check_time_before_restart(within_sec=exp_time):
            logging.debug(f"Controller restarted within {exp_time} seconds after factory reset.")
            result[1] = True
        else:
            self.logger.error(f"Controller did not restart within {exp_time} seconds after factory reset.")
            #return result  

        # wait for controller to reboot
        if not self.comLib.is_controller_reachable():
            self.logger.error("Controller is not reachable after power cycle.")
            return result

        """ step 3: check if the DUT has restartet """
        status_code, response = self.comLib.get_initial_user(token)
        if status_code == 200 and response == True:
            logging.debug(f"Request is-initial-user success")
            result[2] = True
        else:
            logging.error(f"Request is-initial-user failed: status code: {status_code}, response: {response}")
            return result
        
        """ step 4: Check that IPC is set with default settings """
        return result
        


