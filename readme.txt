Instructions to port over program:


FTDI Driver Installation
Go to https://ftdichip.com/drivers/ and install FTDI driver


Virtual Environment setup
# 1. Create a brand new virtual environment named 'venv' in directory
python -m venv venv

# 2. Activate the virtual environment (Windows command)
venv\Scripts\activate

# (If you are on Mac/Linux, use this to activate instead: source venv/bin/activate)

# 3. Install all the packages from your list
pip install -r requirements.txt