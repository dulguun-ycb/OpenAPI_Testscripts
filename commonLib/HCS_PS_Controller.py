"""Manson HCS-3202 Remote Programming Power Supply module.

This module is an implementation of the remote serial control for the HCS-3202
power supply module.

This file is part of the monorepo library of the MeTestingDepartment
(https://github.com/MeTestingDepartment/Repo)

Initial Author: Pascal Markowski (pascal.markowski@yacoub.de)
Author: Sami-Vincent Tondl (sami.tondl@yacoub.de)

Version History:
    v0.1:
        initial version
        only output_control supported
    v0.2:
        set and get power supply voltage
    v0.3:
        add voltage max and min as constants
        add powercycle function
        change print instructions to logging instructions
"""

import logging
import sys
import time
from typing import Union

import serial
from serial.tools import list_ports

__version__ = 0.3

VOLTAGE_MAX = 36.0
VOLTAGE_MIN = 1.0


class Singleton(type):
    """Singleton class to ensure only one instance of child class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        index = cls, args
        if index not in cls._instances:
            cls._instances[index] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[index]


class HCSControl(metaclass=Singleton):
    """Manson HCS-3202 Remote Programming Power Supply class.

    Implements commands for serial communication specified inside the service
    manual.

    Attributes:
        comport (str):
            Serial port, on which the connection is established.
        serial_inst (obj):
            Serial port connection object.

    Raises:
        ValueError:
            Raised when more or less than one device is found.
    """

    _vendor_id = 0x10C4
    _product_id = 0xEA60
    _manufacturer = "Silicon Labs"
    _description = "CP2102 USB to UART Bridge Controller"

    def __init__(
        self,
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: int = 1,
        timeout: float = 1,
    ):
        """Initializes the class and serial port settings."""

        device_signature = f"{self._vendor_id:x}:{self._product_id:x}"
        device_match = list(list_ports.grep(device_signature))

        if not device_match:
            raise ValueError(f"No device with signature {device_signature} found.")
        if len(device_match) > 1:
            raise ValueError("More than one device with signature" f" {device_signature} found.")

        self.comport = device_match[0].device
        self.serial_inst = serial.Serial(
            port=None,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
        )

    def __del__(self):
        """Decontructs the class instance."""

        if self.serial_inst:
            if self.serial_inst.is_open:
                try:
                    self.__close()
                except ConnectionError:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        if self.serial_inst.is_open:
            self.__close()

    def __open(self) -> bool:
        """Opens the port and clears buffers."""

        self.serial_inst.port = self.comport

        try:
            self.serial_inst.open()
            self.serial_inst.reset_input_buffer()
            self.serial_inst.reset_output_buffer()
            return True

        except serial.SerialException as ex:
            logging.exception(
                "Serial Port on %s could not be opened: %s\n",
                self.serial_inst.port,
                ex,
            )
            return False

    def __close(self):
        """Closes port immediately."""

        self.serial_inst.reset_input_buffer()
        self.serial_inst.reset_output_buffer()
        self.serial_inst.close()
        self.serial_inst.port = None

        if self.serial_inst.is_open:
            raise ConnectionError(f"Serial Port on {self.serial_inst.port} could not be closed.")

    def set_output_control(self, set_output: bool = True) -> bool:
        """Sets output on power supply on or off.

        Sets the output control of the power supply remotely to either 'on' or
        'off'.

        Args:
            set_output: A bool that if True enables the output of the power
                supply. False disables the output.

        Returns:
            bool:
                True if succesful, False otherwise.
        """

        if set_output is True:
            val = 0
        else:
            val = 1

        cmd = f"SOUT{val}\r"

        try:
            if self.__open():
                self.serial_inst.write(bytes(cmd, encoding="utf-8"))
                response = self.serial_inst.read_until(expected=b"\r").decode("ascii")
                self.__close()

                if response != "OK\r":
                    return False
                return True
            return False
        except ConnectionError as ex:
            logging.exception("Exception when calling set_output_control: %s\n", ex)
            return False

    def set_voltage(self, voltage: float) -> bool:
        """Sets volt level on power supply.

        Args:
            voltage:
                Input value for setting the voltage level. The value must be
                between VOLTAGE_MIN (1.0) and VOLTAGE_MAX (36.0).

        Returns:
            bool:
                True if succesful, False otherwise.

        Raises:
            ValueError:
                Raised if voltage parameter is out of range.
        """

        if voltage < VOLTAGE_MIN or voltage > VOLTAGE_MAX:
            raise ValueError(f"Voltage out of range ({VOLTAGE_MIN}-{VOLTAGE_MAX}):" f" {voltage}")

        if voltage < 10:
            voltage_str = "0" + str(int(voltage * 10))
        else:
            voltage_str = int(voltage * 10)

        cmd = f"VOLT{voltage_str}\r"

        try:
            if self.__open():
                self.serial_inst.write(bytes(cmd, encoding="utf-8"))
                response = self.serial_inst.read_until(expected=b"\r").decode("ascii")
                self.__close()
                if response != "OK\r":
                    return False
                return True
            return False
        except ConnectionError as ex:
            logging.exception("Exception when calling set_voltage: %s\n", ex)
            return False

    def get_voltage(self) -> Union[float, bool]:
        """Gets display voltage of power supply.

        Returns:
            float: current display voltage.
            bool: False if reading voltage is not possible.
        """

        cmd = "GETD\r"

        try:
            if self.__open():
                self.serial_inst.write(bytes(cmd, encoding="utf-8"))
                response = self.serial_inst.read_until(expected=b"\r").decode("ascii")
                self.__close()
                voltage = int(response[0:4]) / float(100)
                return voltage
            return False
        except ConnectionError as ex:
            logging.exception("Exception when calling get_voltage: %s\n", ex)
            return False

    def powercycle(self, wait_sec: int = 5) -> bool:
        """Powercycle function to turn powersupply off and on.

        Args:
            wait_sec (int, optional): Time to wait between switching
            off and on. Defaults to 5.

        Returns:
            bool:
                True if succesful, False otherwise.
        """

        logging.debug("Turning off powersupply")
        if self.set_output_control(set_output=False) is False:
            logging.error("### Error while turning off powersupply ###")
            return False

        logging.debug("Wait for %s seconds", wait_sec)
        time.sleep(wait_sec)

        logging.debug("Turning on powersupply")
        if self.set_output_control(set_output=True) is False:
            logging.error("### Error while turning on powersupply ###")
            return False

        return True

def powercycle():
    with HCSControl() as hcs:
        hcs.powercycle()


# for using powercycle as script: python hcs_control.py powercycle
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    globals()[sys.argv[1]]()
    #powercycle()