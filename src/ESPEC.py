# -*- coding: utf-8 -*-
"""
ESPEC.py: Control ESPEC temperature chambers via RS-485/RS-232.

This module provides the SH241 class for interfacing with ESPEC environmental 
test chambers. It manages serial communication, task queuing, asynchronous 
temperature monitoring, and executing multi-step thermal cycles.
"""

import time
import threading
from datetime import datetime
from typing import List, Tuple, Optional, Union

from UART import UARTMaster
from Tasks import Task
from Tasks import LinkedList
from Cycle import Cycle


class SH241:
    """
    Controller class for the ESPEC SH241 temperature chamber.

    Manages hardware communication, maintains a queue of thermal tasks 
    (Linked List), and runs asynchronous threads to monitor and regulate 
    chamber temperature against a set schedule.

    Attributes:
        temperature (Union[float, str]): The last read temperature of the chamber.
        mode (str): The current operation mode (e.g., 'STANDBY', 'CYCLE').
        state (str): The current thermal state (e.g., 'IDLE', 'HEATING', 'SOAKING').
        task_done (bool): Flag indicating if the current task has completed.
        stop_task (bool): Flag to trigger an emergency stop of the task queue.
    """

    def __init__(self, address: int = 1) -> None:
        """Initializes the SH241 controller and connects to the hardware."""
        self._address = address
        self._instr = UARTMaster(use_rs485=False, device_address=address)
        self._instr.CreateDeviceInfoList()
        self._instr.GetDeviceInfoList()
        self._tasklist = LinkedList()
        
        self.timer1: Optional[threading.Timer] = None
        self.timer2: Optional[threading.Timer] = None
        self.startSoaking: bool = False
        
        # Variables for cycling
        self.currentCycle: int = 1
        self.halfCycle: int = 0
        
        # Status variables
        self.temperature: Union[float, str] = 0.0
        self.mode: str = "STANDBY" 
        self.state: str = "IDLE" 
        self.task_done: bool = False
        self.stop_task: bool = False
        
    def SetRS485(self) -> None:
        """Reconfigures the serial connection to use RS-485."""
        self._instr = UARTMaster(use_rs485=True)
        self.OpenChannel()
        
    def SetRS232(self) -> None:
        """Reconfigures the serial connection to use RS-232."""
        self._instr = UARTMaster(use_rs485=False)
        self.OpenChannel()

    def OpenChannel(self) -> None:
        """Opens the serial port, purges buffers, and starts the monitor thread."""
        self._instr.Open()
        self._instr.Purge()
        self.SetModeStandby()
        threading.Thread(target=self.tempCheckerLoop, daemon=True).start()

    def GetMode(self) -> str:
        """Queries and returns the current operation mode of the chamber."""
        self._instr.Write('%i,MODE?' % self._address)
        time.sleep(1)   
        self._mode = self._instr.Read().strip('\r\n')
        print(f"Mode: {self._mode}")
        return self._mode

    def GetCondition(self) -> str:
        """Queries and prints the overall condition of the chamber (Temp, Mode, Alarms)."""
        self._instr.Write('%i,MON?' % self._address)
        time.sleep(1)   
        self._cond = self._instr.Read().strip('\r\n')
        print(f"Temperature: {self._cond.split(',')[0]}")
        print(f"Mode: {self._cond.split(',')[1]}")
        print(f"Number of Alarms: {self._cond.split(',')[2]}")
        return self._cond
        
    def GetTemp(self) -> str:
        """Queries and prints the present, target, and limit temperatures."""
        self._instr.Write('%i,TEMP?' % self._address)
        time.sleep(1)   
        self._temp = self._instr.Read().strip('\r\n')
        print(f"Present Temperature: {self._temp.split(',')[0]}")
        print(f"Target Temperature: {self._temp.split(',')[1]}")
        print(f"High Limit Temperature: {self._temp.split(',')[2]}")
        print(f"Low Limit Temperature: {self._temp.split(',')[3]}")
        return self._temp           
    
    def GetTempSilent(self) -> str:
        """Queries the temperature without printing to the console."""
        self._instr.Write('%i,TEMP?' % self._address)
        self._instr.Purge()
        time.sleep(1)
        self._temp = self._instr.Read().strip('\r\n')
        return self._temp.split(',')[0]
         
    def SetPowerOn(self) -> None:
        self._instr.Write('%i,POWER,ON' % self._address)  
        time.sleep(5)   
         
    def SetPowerOff(self) -> None:
        self._instr.Write('%i,POWER,OFF' % self._address)     
        time.sleep(5)   
                  
    def SetTemp(self, temp: float) -> None:
        """Sets the target temperature for the chamber."""
        self._instr.Write('%i,TEMP,S%.1f' % (self._address, temp)) 
        time.sleep(1)   
        
    def SetModeOff(self) -> None:
        self._instr.Write('%i,MODE,OFF' % self._address) 
        time.sleep(2)   
         
    def SetModeStandby(self) -> None:
        self._instr.Write('%i,MODE,STANDBY' % self._address) 
        time.sleep(2)       
         
    def SetModeConstant(self) -> None:
        self._instr.Write('%i,MODE,CONSTANT' % self._address) 
        time.sleep(2)   
         
    def SetModeProgram(self) -> None:
        self._instr.Write('%i,MODE,RUN 1' % self._address)  
        time.sleep(2)   
         
    def ProgramWrite(self, program: List[Tuple[float, str, str]] = [(30.0, 'TRAMPON', '00:01')], cycles: int = 1) -> None:
        """
        Writes a multi-step thermal program to the chamber's memory.

        Args:
            program (List[Tuple]): A list of steps where each step is (Temp, RampMode, TimeString).
            cycles (int): The number of times to loop the program.
        """
        # Original code dynamic write
        self._instr.Write('%i,PRGM DATA WRITE,PGM:1,EDIT START' % self._address)
        time.sleep(1)           
        for idx, step in enumerate(program):
            self._instr.Write('%i,PRGM DATA WRITE,PGM:1,STEP%i,TEMP%.1f,%s,TIME%s,' % (self._address, idx+1, step[0], step[1], step[2]))
            time.sleep(1)   
            self._msg = ''.join(map(chr, self._instr.Read())).strip('\r\n')
            print(self._msg)

        self._instr.Write('%i,PRGM DATA WRITE,PGM:1,COUNT,(1.1.%i)' % (self._address, cycles))                       
        time.sleep(1)   
        self._instr.Write('%i,PRGM DATA WRITE,PGM:1,END,HOLD' % self._address)       
        time.sleep(1)   
        self._instr.Write('%i,PRGM DATA WRITE,PGM:1,EDIT END' % self._address)
        time.sleep(1)   
        
        # Hardcoded verification/override
        # 1. Open the edit session
        self.ProgramErase()
        self._instr.Write('PRGM DATA WRITE, PGM:1, EDIT START')
        time.sleep(0.5)

        # 2. Write the step
        self._instr.Write('PRGM DATA WRITE, PGM:1, STEP1, TEMP12.0, TRAMPOFF, TIME02:40')
        time.sleep(0.5)

        # 3. Close and save the session
        self._instr.Write('PRGM DATA WRITE, PGM:1, EDIT END')
        time.sleep(0.5)

        # 4. Check status
        self._instr.Write('PRGM DATA?')
        response = self._instr.Read()
        print(f"Chamber Status: {response}")

    def ProgramErase(self) -> None:
        self._instr.Write('%i,PRGM ERASE,PGM:1' % self._address)
        time.sleep(1)   

    def ProgramAdvance(self) -> None:
        self._instr.Write('%i,PRGM,ADVANCE' % self._address)                
        time.sleep(1)   
         
    def ProgramEnd(self) -> None:
        self._instr.Write('%i,PRGM,END,HOLD' % self._address)
        time.sleep(1)   
         
    def AddTask(self, temp: float, hours: int, minutes: int, seconds: int, taskname: str = "Task", db_id: Optional[int] = None) -> None:
        """Adds a standard soak task to the chamber queue."""
        if not hasattr(self, '_tasklist'):
            self._tasklist = LinkedList()
        task = Task(temp, hours, minutes, seconds, taskname, db_id)
        self._tasklist.enqueue(task)
        
    def AddCycle(self, temp1: float, temp2: float, hours: int, minutes: int, seconds: int, totalCycles: int, taskname: str = "Cycle", db_id: Optional[int] = None) -> None:
        """Adds an alternating temperature cycle task to the chamber queue."""
        if not hasattr(self, '_tasklist'):
            self._tasklist = LinkedList()
        task = Cycle(temp1, temp2, hours, minutes, seconds, totalCycles, taskname, db_id)
        self._tasklist.enqueue(task)
        
    def AddIdle(self, hours: int, minutes: int, seconds: int) -> None:
        """Adds a standby/idle delay to the queue."""
        self.AddTask(0, hours, minutes, seconds, taskname="Idle")
        
    def WaitTillDateTime(self, year: int, month: int, day: int, hour: int, minute: int) -> None:
        """
        Calculates the time delta between now and a target datetime, 
        then queues an Idle task for that duration.
        """
        target_dt = datetime(year, month, day, hour, minute)
        now = datetime.now()
        duration = target_dt - now
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        self.AddIdle(hours, minutes, seconds)

    def stopTask(self) -> None:
        """Cancels all running timers, clears current progress, and puts the chamber in Standby."""
        self.timer1 = None
        self.timer2 = None
        self.currentCycle = 1
        self.halfCycle = 0
        self.stop_task = True
        self.SetModeStandby()
        print("Task stopped. Clearing timers and putting chamber in Standby.")
        if not self._tasklist.head:
            self.SetModeStandby()
            print("No Tasks in queue. Putting chamber in Standby.")
            return
    
    def startNextTask(self) -> None:
        """Helper to advance the queue when a soak is finished."""
        if self.mode != "CYCLE":
            self.task_done = True
        self.startTask()
    
    def startTask(self) -> None:
        """
        Pulls the next task from the queue and executes it based on its type.
        Supports standard tasks, idle timers, and cycles.
        """
        # Cancel existing timers
        self.timer1 = None
        self.timer2 = None
        
        if not self._tasklist.head:
            self.SetModeStandby()
            print("All tasks completed. Putting chamber in Standby.")
            return

        # Pops the current task to execute
        node = self._tasklist.head
        task = node.data
        
        # Converting total seconds to hours, minutes and seconds
        hours = task.durationInSeconds // 3600
        minutes = (task.durationInSeconds % 3600) // 60
        seconds = task.durationInSeconds % 60
        
        self.stop_task = False
        
        # For task
        if task.taskName == "Task":
            self._tasklist.pop_head()
            print(f"Starting {task.taskName}: Soak at {task.temp}°C for {hours}hr {minutes}min {seconds}s")
            self.startTemperatureSoak(task.temp, task.durationInSeconds)
            
        # For Idling process
        elif task.taskName == "Idle":
            self._tasklist.pop_head()
            print(f"Idling for {hours}hr {minutes}min {seconds}s")
            self.SetModeStandby()
            durationInSeconds = hours * 3600 + minutes * 60 + seconds
            try:
                self.timer1 = threading.Timer(durationInSeconds, self.startTask)
                self.timer1.start()
            except Exception as e:
                print(f"CRASHED while setting timer: {e}")
                
        # For Cycling process
        else:
            # Half cycle refers to the period where temperature goes to either temp1 or temp2 and soaks
            # Full cycle is the process of soaking at both temperatures for one entire duration
            self.state = "CYCLE"
            if self.halfCycle >= 2:
                self.currentCycle += 1
                self.halfCycle = 0
                
            if self.halfCycle == 0:
                print(f"Starting cycle {self.currentCycle}: Soak at {task.temp1}°C for {hours}hr {minutes}min {seconds}s")
                self.startCycle(self.currentCycle, task.totalCycles, task.temp1, task.temp2, hours, minutes, seconds, state=0)
            else:
                print(f"Starting cycle {self.currentCycle}: Soak at {task.temp2}°C for {hours}hr {minutes}min {seconds}s")
                self.startCycle(self.currentCycle, task.totalCycles, task.temp1, task.temp2, hours, minutes, seconds, state=1)
            self.halfCycle += 1
    
    def startCycle(self, currentCycle: int, totalCycles: int, temp1: float, temp2: float, hours: int, minutes: int, seconds: int, state: int = 0) -> None:
        """
        Executes one half of a thermal cycle (heating or cooling).

        Args:
            currentCycle (int): Current cycle count.
            totalCycles (int): Total cycles required.
            temp1 (float): Target temperature for state 0.
            temp2 (float): Target temperature for state 1.
            hours (int): Time to soak in hours.
            minutes (int): Time to soak in minutes.
            seconds (int): Time to soak in seconds.
            state (int): 0 for temp1, 1 for temp2.
        """
        if currentCycle > totalCycles:
            self._tasklist.pop_head()
            self.currentCycle = 1
            self.halfCycle = 0
            self.task_done = True
            self.startNextTask()
            return
            
        self.mode = "CYCLE"
        durationInSeconds = hours * 3600 + minutes * 60 + seconds
        
        if state == 0:
            print(f"Starting cycle {self.currentCycle}: Soak at {temp1}°C for {hours}hr {minutes}min {seconds}s")
            self.startTemperatureSoak(temp1, durationInSeconds)
        else: 
            self.startTemperatureSoak(temp2, durationInSeconds)
            print(f"Starting cycle {self.currentCycle}: Soak at {temp2}°C for {hours}hr {minutes}min {seconds}s")
    
    def tempCheckerLoop(self) -> None:
        """Background thread loop that polls the chamber temperature every 3 seconds."""
        while True:
            try:
                time.sleep(3.0) 
                self.temperature = self.GetTempSilent()
            except Exception as e:
                print(f"Error occurred while checking temperature: {e}")

    def deleteTask(self, target_db_id: int) -> None:
        """
        Searches the queue for a task with a matching database ID and removes it.

        Args:
            target_db_id (int): The database ID of the task to delete.
        """
        if not self._tasklist.head:
            print("List is empty.")
            return

        current = self._tasklist.head
        previous = None

        while current:
            if current.data.db_id == target_db_id:
                if previous is None:
                    # Deleting the head
                    self._tasklist.head = current.next
                else:
                    # Deleting a middle or last item
                    previous.next = current.next
                
                print(f"Successfully deleted Task with DB ID {target_db_id}")
                return

            previous = current
            current = current.next
            
        print(f"Task with DB ID {target_db_id} was not found in the Oven.")
        
    def temperatureQuerySchedule(self, target: float, durationInSeconds: int) -> None:
        """
        Schedules a background callback to evaluate if the chamber has reached 
        the target temperature yet.
        """
        if self.stop_task:
            return
        self.timer2 = threading.Timer(3.0, self.checkTempCallback, args=[target, durationInSeconds])
        self.timer2.start()
        
    def checkTempCallback(self, target: float, durationInSeconds: int) -> None:
        """
        Evaluates the current temperature against the target. 
        If reached, starts the soak timer. If missed, reschedules itself.
        """
        hours = durationInSeconds // 3600
        minutes = (durationInSeconds % 3600) // 60
        seconds = durationInSeconds % 60
        
        # When target temperature is reached, start soaking for specified duration
        if abs(float(self.temperature) - target) <= 1.0:
            dateTime = datetime.now()
            self.state = "SOAKING"  
            print(f"Target {target}°C Reached at {dateTime}. Starting Soak for {hours}hr {minutes}min {seconds}s.")
            try:
                self.timer1 = threading.Timer(durationInSeconds, self.startNextTask)
                self.timer1.start()
            except Exception as e:
                print(f"CRASHED while setting timer: {e}")
        else:
            # Target missed. Schedule the next check.
            self.temperatureQuerySchedule(target, durationInSeconds)
            self.state = "HEATING" if float(self.temperature) < target else "COOLING"
            print(f"Target Temperature = {target}°C, Current Temperature = {self.temperature}°C, rechecking in 3 seconds.")
            
    def startTemperatureSoak(self, target_temp: float, durationInSeconds: int) -> None:
        """
        Sets the chamber to CONSTANT mode and initiates the temperature 
        monitoring loop to wait for the target temperature.
        """
        if self.stop_task:
            return
        self.SetTemp(target_temp)
        self.SetModeConstant()
        self.temperatureQuerySchedule(target_temp, durationInSeconds)
        
    def returnToAmbient(self) -> None:
        """Resets the chamber to a safe 25.0°C."""
        ambientTemp = 25.0
        self.SetTemp(ambientTemp)
    
    def PrintTaskList(self) -> None:
        """Prints the current contents of the task queue."""
        self._tasklist.print_list()

    def CloseChannel(self) -> None:
        """Closes the underlying serial communication channel."""
        self._instr.Close()