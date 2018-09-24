NetDev Gather Data
==================

# Overview
This is a basic network device automation app designed for pulling data from many remote devices for use in validating configs, checking licenses, capturing routing tables, or any other show command that a device can output.  The program will process up to 20 devices in parallel to speed capture in large environments.

The initial work has been focused around Cisco Routers, though the underlying NetMiko library supports many other platforms.

Note that this code is very basic right now and has a lot of room for improvements and modularization.

# Requirements
The following extra modules are used in this project:

 - NetMiko (and paramiko by extension)
 - tqdm

# Usage
Create a CSV file called "inputdata.csv" in the working directory of the app.  In the first row of this file, each column should have a description for the data output that will be collected.  The second row should contain the command to run on the device to get the output that will be placed in that column name in the output.

Once you have this file setup with all the commands you want to run (unlimited number of commands - one per column), run the app.  It will prompt for a list of IP addresses of the devices you want to run the command in.  You can paste into this window and it will accept all IPs, one per line.  When you have entered all device IPs, enter a blank line and it will move to the next step.  You will be prompted for the username and password to use to login to the devices.  Currently the app is hard-coded to use SSH.  After entering the login credentials, enter the name of the CSV file you want to save the output to.  This file will contain the device IP, hostname (if available), success/failure indiciation of data collection, and the output of the command specified in the inputdata.csv file for each device.

To summarize:
1. Create/edit inputdata.csv file with the commands you want to run
2. Run app and enter the IPs you want to run the commands on
3. Enter the username and password to use to log into all the devices (one login/pass for all)
4. Enter the name of the output file to create.
5. Wait for the process to complete.  A progress bar will show current progress as well as estimated time to complete.

Note that technically any command may be run based on what is in the inputdata.csv file, so ensure you don't push anything dumb.  But for example, you could potentially use this to clear IPSec SAs, routing sessions, etc.

Note also that currently no logging of the sessions is done - only the requested output is gathered along with the device hostname.  Issues connecting to the devices or authenticating will be noted in the output CSV file.


# License
This software is provided under the Zlib license as detailed in the "LICENSE" file.
