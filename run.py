from commonLib.CommonLib_IPC import CommonLibIPC
from dynamicLicense.test_dynamicLicense import TestDynamicLicense
from FactoryReset.test_factoryReset import TestFactoryReset
from Reboot.test_reboot import TestReboot
import logging
from datetime import datetime
import random
import os

# IPC credentials
ipc_ip = "192.168.0.1"
ipc_usr = "variox"
ipc_pwd = "variox"

valid_license_path = 'C:\\Users\\Dulguun\\Desktop\\Test_WS\\scripts\\TestSkripts\\dynamicLicense\\license\\valid'
valid_license_files = [
    'license_09800202xxxxx_V000-SWCDS-PNM0001.lic',
    'license_09800202xxxxx_V000-SWCDS-PNS0001.lic',
    # Add more license files if needed
]

invalid_license_path = 'C:\\Users\\Dulguun\\Desktop\\Test_WS\\scripts\\TestSkripts\\dynamicLicense\\license\\invalid'
invalid_license_files = [
    'license_09800202xxxxx_V000-SWCDS-PNM0001.lic',
    'license_09800202xxxxx_V000-SWCDS-PNS0001.lic',
    # Add more license files if needed
]

if __name__ == "__main__":

    # configure log file
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"log_{timestamp}.txt")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    # Create CommonLibIPC instance
    try:
        comLib = CommonLibIPC(ipc_ip, ipc_usr, ipc_pwd)
    except ValueError as e:
        # Invalid Controller IP address
        logging.error(f"Failed to create CommonLibIPC instance: {e}. Exiting test!")
        exit(1)

    # Check controller reachability
    if not comLib.is_controller_reachable(timeout=2):
        logging.error(f"Controller with IP {ipc_ip} is not reachable. Exiting test!")
        exit(1)

    # check license file existence
    for lic_file in valid_license_files:
        full_path = os.path.join(valid_license_path, lic_file)
        if not os.path.isfile(full_path):
            logging.error(f"License file not found: {full_path}.")
            exit(1)

    
    """ ------------------------------------- Codesys Dynamic License test ------------------------------------- """

    logging.info("Starting test: CODESYS DYNAMIC LICENSE")
    dyn_lic = TestDynamicLicense(comLib)

    # ---------------------------------------- testcase ID: 376402 ----------------------------------------
    # OpenAPI supports Dynamic Licensing with Codesys restart (valid license key)

    testcase_id = 376402
    random_license_file = os.path.join(valid_license_path, random.choice(valid_license_files)) # randomly choose a license file
    if dyn_lic.test_activate_valid_license(random_license_file, restart_codesys=True):  
        logging.info(f"Testcase ID {str(testcase_id)} PASSED.")
    else:
        logging.error(f"Testcase ID {str(testcase_id)} FAILED.")

    # ---------------------------------------- testcase ID: 492516 ----------------------------------------
    # OpenAPI supports Dynamic Licensing without Codesys restart (valid licence key)

    testcase_id = 492516
    random_license_file = os.path.join(valid_license_path, random.choice(valid_license_files)) # randomly choose a license file
    if dyn_lic.test_activate_valid_license(random_license_file, restart_codesys=False):  
        logging.info(f"Testcase ID {str(testcase_id)} PASSED.")
    else:
        logging.error(f"Testcase ID {str(testcase_id)} FAILED.")

    # ---------------------------------------- testcase ID: 473617 ----------------------------------------
    # OpenAPI: Dynamic Licensing shows list of active licenses

    testcase_id = 473617
    if dyn_lic.test_get_status(valid_license_path, valid_license_files, restart_codesys=True):  
        logging.info(f"Testcase ID {str(testcase_id)} PASSED.")
    else:
        logging.error(f"Testcase ID {str(testcase_id)} FAILED.")


    # ---------------------------------------- testcase ID: 376405 ----------------------------------------
    # OpenAPI supports Dynamic Licensing (negative test: invalid licence key)

    testcase_id = 376405
    if dyn_lic.test_activate_invalid_license(invalid_license_path, invalid_license_files, restart_codesys=False):  
        logging.info(f"Testcase ID {str(testcase_id)} PASSED.")
    else:
        logging.error(f"Testcase ID {str(testcase_id)} FAILED.")


    """ ------------------------------------------ Reboot test ------------------------------------------ """

    logging.info("Starting test: REBOOT")
    reboot = TestReboot(comLib)

    # ---------------------------------------- testcase ID: 376413 ----------------------------------------
    # OpenAPI: Reboot is available
    testcase_id = 376413
    if reboot.test_reboot():
        logging.info(f"Testcase ID {str(testcase_id)} PASSED.")
    else:
        logging.error(f"Testcase ID {str(testcase_id)} FAILED.")


    """ ------------------------------------- Factory Reset tests ------------------------------------- """

    logging.info("Starting test: FACTORY RESET")
    fac_res = TestFactoryReset(comLib)

    # ---------------------------------------- testcase ID: X ----------------------------------------
    # 376432: OpenAPI: Reset Factory Default is available
    # 492537: OpenAPI: Software Restart starts within 3s
    # 376434: OpenAPI: System restarts after Reset Factory Default

    testcase_id = [376432, 492537, 376434]
    res = fac_res.test_factory_reset()
    for i in range(len(testcase_id)):
        if res[i]:
            logging.info(f"Testcase ID {str(testcase_id[i])} PASSED.")
        else:
            logging.error(f"Testcase ID {str(testcase_id[i])} FAILED.")

    





    
    
