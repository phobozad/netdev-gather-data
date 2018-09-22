#!/usr/bin/env python3

# We need to run in python 3.3+

import netmiko
from tqdm import tqdm
import csv
from multiprocessing import Pool
from getpass import getpass

import signal
import time
import sys

def getRouterData(routerIP):

	# This function is called in each data collection process that we spawn

	signal.signal(signal.SIGINT, signal.SIG_IGN)

	# Read the commands and header names we should use to capture the output

	# TODO: Don't open a file on every single thread every time - pass this into the function
	# 	or access via a shared memory location
	with open('inputdata.csv', 'rt') as csvfile:
		paramReader = csv.reader(csvfile)
		headers=next(paramReader)
		commands=next(paramReader)

	# Initialize all parameters so that if there is no output we still
	# have an empty string to write to the CSV file rather than not writing the output at all
	thisRouterOutput={"deviceIP": "", "deviceHostname": "", "collectionResult": ""}
	for header in headers:
		thisRouterOutput[header]=""

	router= {
		"device_type": "cisco_xe",
		"ip": routerIP,
		"username": "admin",
		"password": "cisco",
		}
	
	# Add the device IP we are connecting to into the output for identification
	thisRouterOutput["deviceIP"]=routerIP
	
	try:
		rtrConnection = netmiko.ConnectHandler(**router)
	except netmiko.ssh_exception.NetMikoAuthenticationException:
		thisRouterOutput["collectionResult"]="Authentication Failure"
		return thisRouterOutput
	except netmiko.ssh_exception.NetMikoTimeoutException:
		thisRouterOutput["collectionResult"]="Timeout while connecting"
		return thisRouterOutput

	# Grab the router hostname if possible to also put in the output for ID
	# If this fails, no big deal, just carry on
	try:
		# Netmiko returns the entire prompt which includes hostname & the trailing # or >
		# Remove this trailing character for the hostname we report in the output
		
		# TODO: Make this more reliable.  Have seen some issues where this doesn't get pulled
		#	or it still has trailing character
		thisRouterOutput["deviceHostname"]=rtrConnection.find_prompt().replace(">","").replace("#","")
	except IOError:
		pass
	
	# Run each of the data gathering commands specified in the input CSV file			
	for parameter,command in zip(headers,commands):	
		try:
			thisRouterOutput[parameter]=rtrConnection.send_command(command)
		except IOError:
			pass
		
	rtrConnection.disconnect()
	
	# If we get to this point without bailing, assume everything was a success
	# TODO: Add some beter error detection/handling to determine if this was 100%
	#	success or only partial success.  e.g. we got 2/3 of the command outputs
	#	but had IOError for one of them.
	thisRouterOutput["collectionResult"]="Success"
	return thisRouterOutput



def processOutput(data):
	# Add the data we got from the worker process to the output buffer variable
	outputResult.append(data)

	# Let the progress bar know that one more device was completed so it updates accordingly
	progressBar.update()

def sigIntHandler(sig, frame):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		print ()
		print ('Interrupted by user...exiting.  Please wait up to 30 seconds while the system cleans up.')
		progressBar.close()
		saveData()
		pool.terminate()
		pool.join()
		sys.exit(1)
	

def saveData():
	global fileName
	global headers
	global outputResult

	with open(fileName,"wt") as fileOut:
		csvWriter=csv.DictWriter(fileOut,fieldnames=headers)
		csvWriter.writeheader()
		try:
			for router in outputResult:
				csvWriter.writerow(router)
		# Just in case one of the router dictionaries is empty or has missing columns
		# we continue on outputting the rest and just skip that one.  Should be less
		# of an issue now that we write empty strings to all columns even if we didn't
		# get any output
		except TypeError:
			pass

	print ('Output saved as {}.  Open in Excel for viewing.'.format(fileName))

# The following code only runs on the parent process the user runs
# When we launch a bunch of worker processes, the run this same code file
# and we need to ensure they don't run the "main" routine or else things get
# very broken and weird
# Its possible this isn't needed now that we moved off of using pool.imap_unordered, but need to test
if __name__ == '__main__':
	routerList = []
	outputResult=[]

	signal.signal(signal.SIGINT, sigIntHandler)	

	# Read the inputdata.csv file in the working directory to determine what commands to run
	# and what to label that column in the output CSV.
	# TODO: Test/fix what happens if user-specifed column name collides with the common
	#	ones we hard-code below (e.g. device IP)		
	with open('inputdata.csv', 'rt') as csvfile:
		paramReader = csv.reader(csvfile)
		headers=next(paramReader)
		commands=next(paramReader)

	# In addition to the columns the user specified in the CSV file, we also
	# write some common values for each device.  Ensure these are added to the
	# CSV header at the beginning for ease of sorting/parsing the output
	headers.insert(0,"deviceHostname")
	headers.insert(1,"deviceIP")
	headers.insert(2,"collectionResult")
	
	print ('This script will grab data from routers asynchronously and output it to a CSV.')
	print ('')
	print ('Paste in a list of IPs to connect to - one per line. Finish your input with a blank line to process')
	print ('')

	while True:
		line = input()
		if line:
			routerList.append(line.strip())
		else:
			break

	# TODO: Don't hardcode a username/password in the program.
	#	Next step after prompting for same username for all devices is to be able to specify this per-device
	#	Potentially could use a CSV with IP, username, password.  Could be extended to device type too in the future (e.g. Juniper, catalyst?)

	#username = input("Username: ")
	#password = getpass()
	
	
	msg = 'Enter the filename to save output to. \r\nAny existing file will be overwritten'
	fileName = input('%s: ' % msg)

	# Does the file have a suffix already?
	# If not, add one
	if fileName.rfind('.csv') ==  -1:
		fileName+='.csv'

	deviceQty = len(routerList)
	# Create a process pool of up to 20 workers
	# This means 20 devices will be logged into at once
	# If we didn't specify more than 20 devices, just start processes for
	# however many we have
	pool = Pool(processes=20 if deviceQty >= 20 else deviceQty)
	
	# Use the tqdm library to generate a progress bar.
	# By specifying how many devices it will also automatically predict completion time
	progressBar = tqdm(total=deviceQty)
	
	# Iterate through all the routers specified.  For each one, submit its IP
	# to the pool of worker processes to be processed.  When each process completes
	# the device it was given, take the output and send it to the processOutput function
	jobList = []
	for router in routerList:
		# We append the output object from apply_sync so we can later track its state
		jobList.append(pool.apply_async(getRouterData,args=(router,),callback=processOutput))

	# Don't accept any more jobs to be submitted to the processing pool
	pool.close()

	# Wait for all the submitted jobs to complete before continuing.
	# As soon as a worker process completes one device, it will grab
	# the next one in the list we sent to the pool
	pool.join()
	#try:
	#	while True:
	#		if all(job.ready() for job in jobList):
				# We completed all jobs successfully
	#			break
	#		time.sleep(1)

	#except KeyboardInterrupt:
		#sys.exit(1)
	
	# We're done with the progress bar.  Need to cleanly remove it.
	progressBar.close()

	
