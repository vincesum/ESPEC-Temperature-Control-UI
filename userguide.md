# Espec Temperature Control Chamber UI User Guide

This user guide provides instructions for the setup and the usage of the user interface of the ESPEC Temperature Control Chamber (SH-241 / SH641)

## Installation and set up

### Setup for accessing modules in codebase
FTDI Driver Installation
Go to https://ftdichip.com/drivers/ and install FTDI driver

Virtual Environment setup

(If on Powershell, run this to give permission to run scripts and press y: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

1. Go to terminal and navigate to the working directory(where the project files are located)

2. Create a brand new virtual environment named 'venv' in directory
`python -m venv venv`

3. Activate the virtual environment (Windows command)
`venv\Scripts\activate`

(If you are on Mac/Linux, use this to activate instead: source venv/bin/activate)

4. Install all the packages from your list
`pip install -r requirements.txt`

Packing app into executable file

1. Install pyinstaller with: `pip install pyinstaller`

2. Navigate to the folder containing app.py and run this: `pyinstaller --onefile --noconsole --add-data "templates;templates" --add-data "static;static" app.py`

### Setup for using executable (App)
1. Download FTDI Driver
2. Run the app

## Usage of the User Interface

### Soaking Tasks:
1. For soaking tasks, input the temperature and duration of soaking into the input fields.
* Do note that the duration only begins after the set temperature has been reached. The duration fields need not be fully filled up. For example, you can leave certain duration fields blank as long as the duration is valid.
![image info](./images/UI%20image%201.png)

2. Once the details of the tasks have been filled up, press the green `Add Task` button to add the task into the queue in the tasklist.
![image info](./images/UI%20image%202.png)

3. The task will then pop up in the tasklist.
* The tasklist allows you to maintain a list of tasks to be executed sequentially.
![image info](./images/UI%20image%203.png)

4. Click the green `Start` button when you are ready to start the tasks
* Once started, the remaining tasks in the tasklist will be queued up such that the next task will begin when the current tasks finishes until they are stopped or there is no task left in the list.
![image info](./images/UI%20image%204.png)

5. The Bold text displays the information regarding the current task.
* Do note that the Time Left display only starts counting down once the targetted temperature has been reached when soaking begins so do not be alarmed if it is zero.
![image info](./images/UI%20image%205.png)

6. The buttons at the top of the page allows you to switch between soaking and cycling modes.
* You are able to freely add soaking and cycling tasks after each other.
![image info](./images/UI%20image%206.png)