"""
UARTMaster.py

Implements a UART Master class for RS-232 and RS-485 serial communication.
Specifically tailored to interface with ESPEC oven controllers, including 
automated COM port detection and hardware-level RS-485 RTS toggling.
"""

import serial
import serial.rs485
import serial.tools.list_ports
import time
from typing import Optional


class UARTMaster:
    """
    Manages serial communication for hardware controllers over UART.

    Features automatic COM port polling for ESPEC controllers and optional 
    RS-485 mode for half-duplex communication requiring RTS line control.

    Attributes:
        port (str): The active COM port (e.g., 'COM3').
        baudrate (int): Communication speed in bits per second.
        timeout (float): Read timeout in seconds.
        use_rs485 (bool): Flag enabling RS-485 RTS hardware toggling.
        address (int): The target device network address (for RS-485/multiplexing).
        ser (serial.Serial | None): The underlying pyserial object.
        oven_connected (bool): Status flag indicating a successful open connection.
    """

    def __init__(
        self, 
        port: str = 'COM3', 
        baudrate: int = 9600, 
        timeout: float = 1.0, 
        use_rs485: bool = False, 
        device_address: int = 1
    ) -> None:
        """
        Initializes the UART settings and attempts to auto-detect the hardware.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.use_rs485 = use_rs485
        self.address = device_address  
        self.oven_connected = False
        
        # Attempt to auto-detect the oven port on initialization
        self.autodetect_oven_port()  

    def CreateDeviceInfoList(self) -> None:
        pass

    def GetDeviceInfoList(self) -> None:
        pass

    def Open(self) -> None:
        """
        Opens the serial port and applies RS-485 configurations if required.

        If `use_rs485` is True, configures the driver to toggle RTS high during 
        transmission (Tx) and low during reception (Rx). Sets `oven_connected` 
        to True upon success.
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            if self.use_rs485:
                # Requires a hardware adapter with "Automatic Send Data Control".
                rs485_conf = serial.rs485.RS485Settings(
                    rts_level_for_tx=True, 
                    rts_level_for_rx=False,
                    loopback=False,
                    delay_before_tx=None,
                    delay_before_rx=None,
                )
                self.ser.rs485_mode = rs485_conf
                
            self.oven_connected = True
            
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            self.ser = None
            self.oven_connected = False

    def Close(self) -> None:
        if self.ser:
            self.ser.close()

    def Purge(self) -> None:
        """Clears all unread data in the physical input and output buffers."""
        if self.ser:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

    def Write(self, cmd: str) -> None:
        """
        Appends carriage return/line feed (`\\r\\n`), encodes to ASCII, 
        and transmits the command over the serial bus.

        Args:
            cmd (str): The raw command string to send.
        """
        if self.ser and self.ser.is_open:
            full_command = f"{cmd}\r\n"
            self.ser.write(full_command.encode('ascii'))
        else:
            print("Error: Port not open")

    def Read(self) -> Optional[str]:
        """Reads a single line from the serial buffer, decoded from ASCII."""
        if self.ser and self.ser.is_open:
            return self.ser.readline().decode('ascii').strip()
        return None
    
    def autodetect_oven_port(self) -> None:
        """
        Scans all available hardware COM ports to locate the ESPEC controller.

        Temporarily opens each available port, sends an ESPEC 'TYPE?' identification 
        query, and listens for a response. If a valid response is received, 
        overwrites `self.port` with the discovered COM port.
        """
        print("Scanning for oven controller...")
        
        # Get a list of ALL hardware ports plugged into the machine
        available_ports = serial.tools.list_ports.comports()
        
        if not available_ports:
            print("No serial cables detected. Plug in the USB adapter!")
            return None

        for port_info in available_ports:
            test_port = port_info.device 
            print(f"Pinging {test_port}...")
            
            try:
                # Open the port temporarily with a very short timeout
                temp_connection = serial.Serial(test_port, baudrate=self.baudrate, timeout=1)
                
                # Send a harmless Espec command asking for the controller type
                command = f"{self.address},TYPE?\r\n"
                temp_connection.write(command.encode('ascii'))
                
                # Wait a split second, then read the response
                time.sleep(0.5) 
                response = temp_connection.readline().decode('ascii').strip()
                
                # Always close the temporary connection to prevent locking
                temp_connection.close()
                
                # If we get text back, the ESPEC controller is on this port
                if response:
                    print(f"SUCCESS: Oven detected on {test_port}!")
                    self.port = test_port  
                    return

            except serial.SerialException:
                # If the port is locked by another program (Access Denied), 
                # or isn't actually RS-232, silently skip and try the next one.
                pass
                
        print("Scan complete. Oven did not respond on any port.")