#!/bin/env/python

import netmiko
from tqdm import tqdm
import csv
from multiprocessing import Pool
from getpass import getpass

def getRouterData(routerIP):
	with open('inputdata.csv', 'rb') as csvfile:
		paramReader = csv.reader(csvfile)
		headers=next(paramReader)
		commands=next(paramReader)
	
	thisRouterOutput={}
	router= {
		"device_type": "cisco_xe",
		"ip": routerIP,
		"username": "admin",
		"password": "cisco",
		}
	
	thisRouterOutput["deviceIP"]=routerIP
	
	try:
		rtrConnection = netmiko.ConnectHandler(**router)
	except (netmiko.ssh_exception.NetMikoAuthenticationException, netmiko.ssh_exception.NetMikoTimeoutException) as e:
		return

	try:
		thisRouterOutput["deviceHostname"]=rtrConnection.find_prompt().replace(">","").replace("#","")
	except IOError:
		pass
		
	for parameter,command in zip(headers,commands):	
		try:
			thisRouterOutput[parameter]=rtrConnection.send_command(command)
		except IOError:
			pass
		
	rtrConnection.disconnect()
	
	return thisRouterOutput

if __name__ == '__main__':
	routerList = []
	outputResult=[]
			
	with open('inputdata.csv', 'rb') as csvfile:
		paramReader = csv.reader(csvfile)
		headers=next(paramReader)
		commands=next(paramReader)
	
	headers.insert(0,"deviceIP")
	headers.insert(0,"deviceHostname")
	
	
	print 'This script will grab data from routers asynchronously and output it to a CSV.'
	print ''
	print 'Paste in a list of IPs to connect to - one per line. Finish your input with a blank line to process'
	print ''

	while True:
		line = raw_input()
		if line:
			routerList.append(line.strip())
		else:
			break
	
	#username = raw_input("Username: ")
	#password = getpass()
	
	
	msg = 'Enter the filename to save output to. \r\nAny existing file will be overwritten'
	fileName = raw_input('%s: ' % msg)

	# Does the file have a suffix already?
	# If not, add one
	if fileName.rfind('.csv') ==  -1:
		fileName+='.csv'




	#headers=["waasNode","serial","model"]
	#commands=["show service-insertion config service-node-group | i \ \ service-node", "show version | i board ID", "show inventory | i PID: ISR"]
	#print headers
	#print commands
	
	
	pool = Pool(processes=20)

	#for routerIP in tqdm(routerList):	
	for routerOutput in tqdm(pool.imap_unordered(getRouterData, routerList), total=len(routerList)):
		outputResult.append(routerOutput)

	with open(fileName,"wb") as fileOut:
		csvWriter=csv.DictWriter(fileOut,fieldnames=headers)
		csvWriter.writeheader()
		try:
			for router in outputResult:
				csvWriter.writerow(router)
		except TypeError:
			pass
