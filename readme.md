# ESPEC Temperature Control Chamber UI (SH241/SH641)

## Introduction
This is an easy-to-use web-based UI application that allows users to control the SH241 / SH641 ESPEC Temperature Chambers via UART with an RS-232C / RS-485 connection.

## Setup for accessing modules in codebase
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

## Setup for using executable (App)
1. Download FTDI Driver
2. Run the app