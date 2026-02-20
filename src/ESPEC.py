# -*- coding: utf-8 -*-
"""ESPEC.py: Control ESPEC temperature chambers via RS-485 
"""

import time
from datetime import datetime

from UART import UARTMaster

from Tasks import Task
from Tasks import LinkedList
from Cycle import Cycle
from Timer import ProgTimer
from Timer import PyTimer
import threading

class SH241():

    def __init__(self, address=1):
        self._address = address
        self._instr = UARTMaster(use_rs485=False)
        self._instr.CreateDeviceInfoList()
        self._instr.GetDeviceInfoList()
        self._tasklist = LinkedList()
        self.timer1 = None
        self.timer2 = None
        self.startSoaking = False
        #Variables for cycling
        self.currentCycle = 1
        self.halfCycle = 0
        #Status variables
        self.temperature = 0
        self.mode = "STANDBY" #Modes: STANDBY, RAMPING, SOAKING, CYCLE_RAMPING, CYCLE_SOAKING
        self.state = "IDLE" #States: IDLE, HEATING, COOLING, SOAKING
        self.task_done = False
        self.stop_task = False

    def OpenChannel(self):
        self._instr.Open()
        self._instr.Purge()
        

    def GetROMVersion(self):
        self._instr.Write('%i,ROM?' % self._address)
        time.sleep(1)   
        self._romver = self._instr.Read().strip(' \r\n').replace(' ', '') 
        print ('ROM Version: %s' % self._romver)
        return self._romver

    def GetIntStatus(self):
        self._instr.Write('%i,SRQ?' % self._address)
        time.sleep(1)   
        self._intstat = self._instr.Read().strip('\r\n')
        print ('Chamber Alarm: %s' % ('TRUE' if (int(self._intstat, 2) & 0b01000000) == 64 else 'FALSE'))
        print ('Program Start: %s' % ('TRUE' if (int(self._intstat, 2) & 0b00100000) == 32 else 'FALSE'))
        print ('Power Cycle: %s' % ('TRUE' if (int(self._intstat, 2) & 0b00010000) == 16 else 'FALSE'))
        return self._intstat
        
    def GetIntMask(self):
        self._instr.Write('%i,MASK?' % self._address)
        time.sleep(1)   
        self._intmask = self._instr.Read().strip('\r\n')
        print ('Chamber Alarm Interrupts: %s' % ('ON' if (int(self._intmask, 2) & 0b01000000) == 64 else 'OFF'))
        print ('Program Start Interrupts: %s' % ('ON' if (int(self._intmask, 2) & 0b00100000) == 32 else 'OFF'))
        print ('Power Cycle Interrupts: %s' % ('ON' if (int(self._intmask, 2) & 0b00010000) == 16 else 'OFF'))
        return self._intmask

    def GetAlarmStat(self):
        self._instr.Write('%i,ALARM?' % self._address)
        time.sleep(1)   
        self._alarmstat = self._instr.Read().strip('\r\n')
        print ('Number of Alarms: %s' % self._alarmstat.split(',')[0])
        for alarm in self._alarmstat.split(',')[1:]:
            print ('Alarm Code: %s' % alarm)
        return self._alarmstat

    def GetKeyProtStat(self):
        self._instr.Write('%i,KEYPROTECT?' % self._address)
        time.sleep(1)   
        self._keyprotstat = self._instr.Read().strip('\r\n')
        print ('Key Protection Status: %s' % self._keyprotstat)
        return self._keyprotstat

    def GetType(self):
        self._instr.Write('%i,TYPE?' % self._address)
        time.sleep(1)   
        self._type = self._instr.Read().strip('\r\n')
        print ('Dry-bulb Sensor: %s' % self._type.split(',')[0])
        #print ('Wet-bulb Sensor: %s' % self._type.split(',')[1])
        print ('Temperature Controller: %s' % self._type.split(',')[1])
        print ('Maximum Temperature: %s' % self._type.split(',')[2]) 
        return self._type

    def GetMode(self):
        self._instr.Write('%i,MODE?' % self._address)
        time.sleep(1)   
        self._mode = self._instr.Read().strip('\r\n')
        print ('Mode: %s' % self._mode)
        return self._mode

    def GetCondition(self):
        self._instr.Write('%i,MON?' % self._address)
        time.sleep(1)   
        self._cond = self._instr.Read().strip('\r\n')
        print ('Temperature: %s' % self._cond.split(',')[0])
        print ('Humidity: %s' % self._cond.split(',')[1])
        print ('Mode: %s' % self._cond.split(',')[2])
        print ('Number of Alarms: %s' % self._cond.split(',')[3])
        return self._cond
        
    def GetTemp(self):
        self._instr.Write('%i,TEMP?' % self._address)
        time.sleep(1)   
        self._temp = self._instr.Read().strip('\r\n')
        print ('Present Temperature: %s' % self._temp.split(',')[0])
        print ('Target Temperature: %s' % self._temp.split(',')[1])
        print ('High Limit Temperature: %s' % self._temp.split(',')[2])
        print ('Low Limit Temperature: %s' % self._temp.split(',')[3])
        return self._temp           
    
    def GetTempSilent(self):
        self._instr.Write('%i,TEMP?' % self._address)
        self._instr.Purge()
        time.sleep(1)
        self._temp = self._instr.Read().strip('\r\n')
        return self._temp.split(',')[0]

    def GetHumid(self):
        self._instr.Write('%i,HUMI?' % self._address)
        time.sleep(1)       
        self._humi = self._instr.Read().strip('\r\n')
        print ('Present Humidity: %s' % self._humi.split(',')[0])
        print ('Target Humidity: %s' % self._humi.split(',')[1])
        print ('High Limit Humidity: %s' % self._humi.split(',')[2])
        print ('Low Limit Humidity: %s' % self._humi.split(',')[3])
        return self._humi

    def GetRefrigeCtl(self):
        self._instr.Write('%i,SET?' % self._address)
        time.sleep(1)     
        self._refrigectl = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        if self._refrigectl == 'REF9':
            print ('Refrigerator Control: AUTO')
        elif self._refrigectl == 'REF1':
            print ('Refrigerator Control: MANUAL (FIXED)')
        elif self._refrigectl == 'REF0':
            print ('Refrigerator Control: MANUAL (OFF)') 
        else:
            print ('Chamber is not equipped with a refrigerator')
        return self._refrigectl

    def GetRefrigeStat(self):
        self._instr.Write('%i,REF?' % self._address)
        time.sleep(1)   
        self._refrigestat = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        if self._refrigestat == '0':
            print ('Refrigerator Status: OFF')
        elif self._refrigestat == '1,ON1':
            print ('Refrigerator Status: ACTIVE')
        else:
            print ('Chamber is not equipped with a refrigerator')
        return self._refrigestat

    def GetRelayStat(self):
        self._instr.Write('%i,RELAY?' % self._address)
        time.sleep(1)   
        self._relaystat = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        print ('Number of Active Relays: %s' % self._relaystat.split(',')[0])
        for relay in self._relaystat.split(',')[1:]:
            print ('Relay Number: %s' % relay)
        return self._relaystat

    def GetHeaterStat(self):
        self._instr.Write('%i,%%?' % self._address)
        time.sleep(1)   
        self._heaterstat = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        print ('Number of Heaters: %s' % self._heaterstat.split(',')[0])
        print ('Heater Output: %s' % self._heaterstat.split(',')[1])        
        print ('Humidifying Heater Output: %s' % self._heaterstat.split(',')[2])        
        return self._heaterstat

    def GetProgStat(self):
        self._instr.Write('%i,PRGM MON?' % self._address)
        time.sleep(1)   
        self._progstat = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        if self._progstat[:2] != 'NA':
            print ('Program Number: %s' % self._progstat.split(',')[0])
            print ('Step Number: %s' % self._progstat.split(',')[1])
            print ('Target Temperature: %s' % self._progstat.split(',')[2])
            print ('Target Humidity: %s' % self._progstat.split(',')[3])        
            print ('Step Time Remaining: %s' % self._progstat.split(',')[4])        
            print ('Cycles Remaining: %s' % self._progstat.split(',')[5])        
        else:
            print ('No program data exists')            
        return self._progstat

    def GetProgData(self):
        self._instr.Write('%i,PRGM DATA,PGM:1?' % self._address)
        time.sleep(1)   
        self._progdata = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        if self._progdata[:2] != 'NA':
            print ('Total Steps: %s' % self._progdata.split(',')[0])
            print ('Start Repetitions: %s' % self._progdata.split(',')[1].split('.')[0])
            print ('End Repetitions: %s' % self._progdata.split(',')[1].split('.')[1])            
            print ('Cycle Repetitions: %s' % self._progdata.split(',')[1].split('.')[2])            
            print ('End Step: %s' % self._progdata.split(',')[2].split('(')[1].strip(')'))
        else:
            print ('No program data exists')
        return self._progdata

    def GetProgStepData(self, step):
        self._instr.Write('%i,PRGM DATA,PGM:1,STEP%i?' % (self._address, step))
        time.sleep(1)   
        self._progstepdata = ''.join(map(chr, self._instr.Read())).strip('\r\n')
        if self._progstepdata[:2] != 'NA':
            print ('Step Number: %s' % self._progstepdata.split(',')[0])
            print ('Target Temperature: %s' % self._progstepdata.split(',')[1][4:])
            print ('Temperature Ramp: %s' % self._progstepdata.split(',')[2][10:])          
            print ('Target Humidity: %s' % self._progstepdata.split(',')[4])          
            print ('Humidity Ramp: %s' % self._progstepdata.split(',')[5][10:])
            print ('Soak Time: %s' % self._progstepdata.split(',')[6][4:])
            print ('Soak Guarantee: %s' % self._progstepdata.split(',')[7][7:])
            if self._progstepdata.split(',')[8] == 'REF9':
                print ('Refrigerator Control: AUTO')
            elif self._progstepdata.split(',')[8] == 'REF1':
                print ('Refrigerator Control: MANUAL (FIXED)')
            elif self._progstepdata.split(',')[8] == 'REF0':    
                print ('Refrigerator Control: MANUAL (OFF)')             
            print ('Relay Status: %s' % self._progstepdata.split(',')[9][:2])
        else:
            print ('No program step data exists')
        return self._progdata
        
    def SetIntMask(self, mask=0b01000000):
        self._instr.Write('%i,MASK,%s' % (self._address, bin(mask)[2:]))
        time.sleep(1)   
        
    def ResetIntStatus(self):
        self._instr.Write('%i,SRQ,RESET' % self._address)
        time.sleep(1)   
        
    def SetKeyProtectOn(self):
        self._instr.Write('%i,KEYPROTECT,ON' % self._address) 
        time.sleep(1)   
        
    def SetKeyProtectOff(self):
        self._instr.Write('%i,KEYPROTECT,OFF' % self._address)    
        time.sleep(1)   
         
    def SetPowerOn(self):
        self._instr.Write('%i,POWER,ON' % self._address)  
        time.sleep(5)   
         
    def SetPowerOff(self):
        self._instr.Write('%i,POWER,OFF' % self._address)     
        time.sleep(5)   
                 
    def SetTemp(self, temp):
        self._instr.Write('%i,TEMP,S%.1f' % (self._address, temp)) 
        time.sleep(1)   
         
    def SetHighTemp(self, temp):
        self._instr.Write('%i,TEMP,H%.1f' % (self._address, temp))  
        time.sleep(1)   
         
    def SetLowTemp(self, temp):
        self._instr.Write('%i,TEMP,L%.1f' % (self._address, temp))  
        time.sleep(1)   
         
    def SetHumid(self, humi):
        self._instr.Write('%i,HUMI,S%i' % (self._address, humi)) 
        time.sleep(1)   
         
    def SetHighHumid(self, humi):
        self._instr.Write('%i,HUMI,H%i' % (self._address, humi))  
        time.sleep(1)   
         
    def SetLowHumid(self, humi):
        self._instr.Write('%i,HUMI,L%i' % (self._address, humi)) 
        time.sleep(1)   
                 
    def SetHumidOff(self):
        self._instr.Write('%i,HUMI,SOFF' % (self._address))         
        time.sleep(1)   
                 
    def SetRefrigeCtl(self, refcode):
        self._instr.Write('%i,SET,REF%i?' % (self._address, refcode))
        time.sleep(1)   

    def SetRelayOn(self, relay):
        self._instr.Write('%i,RELAY,ON,%i?' % (self._address, relay))
        time.sleep(1)   

    def SetRelayOff(self, relay):
        self._instr.Write('%i,RELAY,OFF,%i?' % (self._address, relay))
        time.sleep(1)   
        
    def SetModeOff(self):
        self._instr.Write('%i,MODE,OFF' % self._address) 
        time.sleep(2)   
         
    def SetModeStandby(self):
        self._instr.Write('%i,MODE,STANDBY' % self._address) 
        time.sleep(2)   
         
    def SetModeConstant(self):
        self._instr.Write('%i,MODE,CONSTANT' % self._address) 
        time.sleep(2)   
         
    def SetModeProgram(self):
        self._instr.Write('%i,MODE,RUN 1' % self._address)  
        time.sleep(2)   
         
    def ProgramWrite(self, program=[(30.0, 'TRAMPON', '00:01')], cycles=1):
        #original code
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
        #this works
            # 1. Open the edit session
        self.ProgramErase()
        self._instr.Write('PRGM DATA WRITE, PGM:1, EDIT START')
        time.sleep(0.5)

        # 2. Write the step (Note: removed the trailing comma from your original string)
        self._instr.Write('PRGM DATA WRITE, PGM:1, STEP1, TEMP12.0, TRAMPOFF, TIME02:40')
        time.sleep(0.5)

        # 3. Close and save the session
        self._instr.Write('PRGM DATA WRITE, PGM:1, EDIT END')
        time.sleep(0.5)

        # 4. Check status
        self._instr.Write('PRGM DATA?')
        response = self._instr.Read()
        print(f"Chamber Status: {response}")

    def ProgramErase(self):
        self._instr.Write('%i,PRGM ERASE,PGM:1' % self._address)
        time.sleep(1)   

    def ProgramAdvance(self):
        self._instr.Write('%i,PRGM,ADVANCE' % self._address)                 
        time.sleep(1)   
         
    def ProgramEnd(self):
        self._instr.Write('%i,PRGM,END,HOLD' % self._address)
        time.sleep(1)   
         
    def AddTask(self, temp, hours, minutes, seconds, taskname="Task", db_id="None"):
        if not hasattr(self, '_tasklist'):
            self._tasklist = LinkedList()
        task = Task(temp, hours, minutes, seconds, taskname, db_id)
        self._tasklist.enqueue(task)
        
    def AddCycle(self, temp1, temp2, hours, minutes, seconds, totalCycles, db_id="None"):
        if not hasattr(self, '_tasklist'):
            self._tasklist = LinkedList()
        task = Cycle(temp1, temp2, hours, minutes, seconds, totalCycles, "Cycle", db_id)
        self._tasklist.enqueue(task)
        
    def AddIdle(self, hours, minutes, seconds):
        self.AddTask(0, hours, minutes, seconds, taskname="Idle")
        
    '''
    Function to add an idling task to tasklist to wait till a specific datetime.
    Format of datetime is YYYY-MM-DD HH:MM:SS
    '''
    def WaitTillDateTime(self, year, month, day, hour, minute):
        target_dt = datetime(year, month, day, hour, minute)
        now = datetime.now()
        duration = target_dt - now
        total_seconds = duration.total_seconds()
        hours = total_seconds // 3600
        minutes = total_seconds % 3600 // 60
        seconds = total_seconds % 60
        self.AddIdle(hours, minutes, seconds)

    def stopTask(self):
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
    
    def startNextTask(self):
        self.task_done = True
        self.startTask()    
    
    def startTask(self):
        #Cancel existing timers
        self.timer1 = None
        self.timer2 = None
        
        if not self._tasklist.head:
            self.SetModeStandby()
            print("All tasks completed. Putting chamber in Standby.")
            return

        #Pops the current task to execute
        node = self._tasklist.head
        task = node.data
        
        #Converting total seconds to hours, minutes and seconds
        hours = task.durationInSeconds // 3600
        minutes = (task.durationInSeconds % 3600) // 60
        seconds = task.durationInSeconds % 60
        
        self.stop_task = False
        #For task
        if (task.taskName == "Task"):
            self._tasklist.pop_head()
            print(f"Starting {task.taskName}: Soak at {task.temp}°C for {hours}hr {minutes}min {seconds}s")
            self.startTemperatureSoak(task.temp, task.durationInSeconds)
        #For Idling process
        elif (task.taskName == "Idle"):
            self._tasklist.pop_head()
            print(f"Idling for {hours}hr {minutes}min {seconds}s")
            self.SetModeStandby()
            durationInSeconds = hours*3600 + minutes*60 + seconds
            try:
                self.timer1 = threading.Timer(durationInSeconds, self.startTask)
                self.timer1.start()
            except Exception as e:
                print(f"CRASHED while setting timer: {e}")
        #For Cycling process
        else:
            #Half cycle refers to the period where temperature goes to either temp1 or temp2 and soaks
            #Full cycle is the process of soaking at both temperatures for one entire duration
            
            if (self.halfCycle >= 2):
                self.currentCycle += 1
                self.halfCycle = 0
            if (self.halfCycle == 0):
                print(f"Starting cycle {self.currentCycle}: Soak at {task.temp1}°C for {hours}hr {minutes}min {seconds}s")
                self.startCycle(self.currentCycle, task.totalCycles, task.temp1, task.temp2, hours, minutes, seconds, state=0)
            else:
                print(f"Starting cycle {self.currentCycle}: Soak at {task.temp2}°C for {hours}hr {minutes}min {seconds}s")
                self.startCycle(self.currentCycle, task.totalCycles, task.temp1, task.temp2, hours, minutes, seconds, state=1)
            self.halfCycle += 1
    
    '''
    Function to start cycle based on state
    @params:
    currentCycle: Current cycle count
    totalCycle: Total cycle count
    temp1, temp2: temperatures 1 and 2 to alternate between
    state: 0 if going to temp 1, 1 if going to temp 2
    hours, minutes, seconds: time to soak in each temperature for
    '''
    def startCycle(self, currentCycle, totalCycles, temp1, temp2, hours, minutes, seconds, state=0):
        if (currentCycle > totalCycles):
            self._tasklist.pop_head()
            self.currentCycle = 1
            self.halfCycle = 0
            self.startNextTask()
            return
        durationInSeconds = hours * 3600 + minutes * 60 + seconds
        if (state == 0):
            print(f"Starting cycle {self.currentCycle}: Soak at {temp1}°C for {hours}hr {minutes}min {seconds}s")
            self.startTemperatureSoak(temp1, durationInSeconds)
        else: 
            self.startTemperatureSoak(temp2, durationInSeconds)
            print(f"Starting cycle {self.currentCycle}: Soak at {temp2}°C for {hours}hr {minutes}min {seconds}s")
    
    
    def deleteTask(self, target_db_id):
        # Safety check
        if not self._tasklist.head:
            print("List is empty.")
            return

        current = self._tasklist.head
        previous = None

        #Loop through the whole list
        while current:
            #Check for matching id
            if current.data.db_id == target_db_id:
                
                if previous is None:
                    #Case: Deleting the very first item (Head)
                    self._tasklist.head = current.next
                else:
                    #Case: Deleting a middle or last item
                    previous.next = current.next
                
                print(f"Successfully deleted Task with DB ID {target_db_id}")
                return

            previous = current
            current = current.next
        #Exiting while loop means id not found
        print(f"Task with DB ID {target_db_id} was not found in the Oven.")
        

    #queries the temperature at intervals of 3 seconds and sets a timer once it reaches target
    def temperatureQuerySchedule(self, target, durationInSeconds):
        if self.stop_task:
            return
        self.timer2 = threading.Timer(3.0, self.checkTempCallback, args=[target, durationInSeconds])
        self.timer2.start()
        

    #Function called every 3 seconds to check temperature
    #Sets a timer for a certain duration after timer has reached target temperature
    #Then sets chamber to standby after timer ends
    def checkTempCallback(self, target, durationInSeconds):
        
        current_temp = self.GetTempSilent()
        hours = durationInSeconds // 3600
        minutes = (durationInSeconds % 3600) // 60
        seconds = durationInSeconds % 60
        self.temperature = current_temp
        
        #When target temperature is reached, start soaking for specified duration
        if abs(float(current_temp) - target) <= 1:
            dateTime = datetime.now()
            self.state = "SOAKING"  # Indicate soaking state started
            print(f"Target {target}°C Reached at {dateTime}. Starting Soak for {hours}hr {minutes}min {seconds}s.")
            try:
                self.timer1 = threading.Timer(durationInSeconds, self.startNextTask)
                self.timer1.start()
            except Exception as e:
                print(f"CRASHED while setting timer: {e}")
        else:
            # Target missed. Schedule the next check.
            self.temperatureQuerySchedule(target, durationInSeconds)
            self.state = "HEATING" if float(current_temp) < target else "COOLING"
            print(f"Target Temperature= {target}°C, Current Temperature= {current_temp}°C, rechecking in 3 seconds.")
            
    #Sets the oven to soak at a target temperature for a specified duration
    def startTemperatureSoak(self, target_temp, durationInSeconds):
        if self.stop_task:
            return
        self.mode = "SOAKING"
        self.SetTemp(target_temp)
        self.SetModeConstant()
        self.temperatureQuerySchedule(target_temp, durationInSeconds)
        
    def returnToAmbient(self):
        ambientTemp = 25.0
        self.setTemp(ambientTemp)
    
    def PrintTaskList(self):
        self._tasklist.print_list()

    def CloseChannel(self):
        self._instr.Close()
         
