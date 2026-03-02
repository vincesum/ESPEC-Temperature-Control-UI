import serial
import serial.rs485
import serial.tools.list_ports
import time

'''
UART Master class for serial communication
Baudrate: 9600
Data bits: 8
Parity: None
Stop bits: 1
'''
class UARTMaster:
    def __init__(self, port='COM3', baudrate=9600, timeout=1, use_rs485=False, device_address=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.use_rs485 = use_rs485
        self.address = device_address  # Store the target device address
        self.oven_connected = False

    def CreateDeviceInfoList(self):
        pass

    def GetDeviceInfoList(self):
        pass

    #Opens the serial port
    def Open(self):
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
                # This tells the driver to toggle RTS high while sending
                # Note: Not all drivers support this. If yours fails, you need a hardware
                # adapter with "Automatic Send Data Control".
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

    def Close(self):
        if self.ser:
            self.ser.close()

    def Purge(self):
        if self.ser:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

    def Write(self, cmd):
        if self.ser and self.ser.is_open:
            # FIX #2: Add Address for RS-485
            # RS-485 commands MUST start with "Address," (e.g., "1,TEMP?")
            if self.use_rs485:
                full_command = f"{self.address},{cmd}\r\n"
            else:
                full_command = f"{cmd}\r\n"

            self.ser.write(full_command.encode('ascii'))
        else:
            print("Error: Port not open")

    def Read(self):
        if self.ser and self.ser.is_open:
            # Read until newline
            return self.ser.readline().decode('ascii').strip()
        return None
    
    def autodetect_oven_port():
        print("Scanning for oven controller...")
        
        # 1. Get a list of ALL hardware ports plugged into the laptop
        available_ports = serial.tools.list_ports.comports()
        
        if not available_ports:
            print("No serial cables detected. Plug in the USB adapter!")
            return None

        # 2. Test them one by one
        for port_info in available_ports:
            test_port = port_info.device # e.g., 'COM3', 'COM4'
            print(f"Pinging {test_port}...")
            
            try:
                # Open the port temporarily with a very short timeout
                temp_connection = serial.Serial(test_port, baudrate=9600, timeout=1)
                
                # Send a harmless Espec command (like asking for the monitor status)
                temp_connection.write(b'MON?,1\r\n')
                
                # Wait a split second, then read the response
                time.sleep(0.1) 
                response = temp_connection.readline().decode('ascii').strip()
                
                # Always close the temporary connection!
                temp_connection.close()
                
                # 3. If we get text back, we found the winner!
                if response:
                    print(f"SUCCESS: Oven detected on {test_port}!")
                    return test_port

            except serial.SerialException:
                # If the port is locked by another program (Access Denied), 
                # or isn't actually RS-232, Python silently skips it and tries the next one.
                pass
                
        print("Scan complete. Oven did not respond on any port.")
        return None
        
