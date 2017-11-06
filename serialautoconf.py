import glob
import os
import serial
from time import sleep
from serial import SerialException

def porttest():
	if os.name == 'nt':
		p = ['COM%s' % i for i in range(0, 256)]
	elif os.name == 'posix':
		p = glob.glob('/dev/tty[A-Za-z]*')
	for port in p:
		try:
			serial.Serial(port)
		except SerialException:
			pass
		else:
			print("Found port: {}".format(port))
			return port 	# Returns the first serial port found and uses it

def timer(c):
	a = console.read(console.inWaiting())
	time = 0
	while not "[OK]" in str(a):
		a = console.read(console.inWaiting())
		sleep(0.5) # Checks after the [OK] string in the output every .5 second
		time += 1
		if "crypto key generate rsa" in c:
			if time == 1:
				print("Generating RSA key..")
			elif time == 60:	# If not [OK] in the response after 30 sec, program will exit
				print("Error in 'crypto key generate rsa modulus 2048'")
				exit()
		elif c == "wr mem\n" or c == "write memory\n" or c == "do wr mem\n":
			if time == 1:
				print("Writing memory..")
			elif time == 20:	# If not [OK] in the response after 10 sec, program will exit
				print("Error in 'write memory'")
				exit()
	print(c.strip('\n'))

def check(i):
	if not '\n' in i[-1:]:
			i = i+'\n'
	if "[nr]" in str(i):
		rplc = input(str(i).strip('\n')+": ")
		i = str(i).replace("[nr]", rplc)
	elif "[adr]" in str(i):
		rplc = input(str(i).strip('\n')+": ")
		i = str(i).replace("[adr]", rplc)
	ien = i.encode()
	ide = ien.decode()
	console.write(ien)
	sleep(0.3)		# If many commands fails, try 0.5 or 0.7. Depends on how fast your router/switch/firewall is
	a = console.read(console.inWaiting())
	if "crypto key generate rsa" in ide:
		timer(ide)
	elif ide == "wr mem\n" or ide == "write memory\n" or ide == "do wr mem\n":
		timer(ide)
	elif "Extended VLAN(s) not allowed in current VTP mode." in str(a):
		console.write(b'end\n')
		sleep(0.5)
		console.write(b'\r\n\r\n')
		sleep(0.5)
		console.write(b'conf t\n')
		sleep(0.5)
		console.write(b'vtp mode transparent\n')
		sleep(0.5)
		console.write(ien)
	elif "\\n% " in str(a):
		print("\nThe '{}' command failed..".format(str(ide).strip('\n'))
			+"\nERROR:"+str(a.decode()).strip(str(i)))
		exit()
	elif "%" in str(a):
		print(a.decode())
	else:
		print(ide.strip('\n'))

def exec(commands):
	linenr = 0
	for i in commands:
		check(i)
		linenr += 1
	if i != 'conf t' and i != swprio and linenr == len(commands):
		print(">"*33+"\nThe config was succesfully loaded!\n"+"<"*33)

def firstcheck():
	console.write(b'show vers | include UNIVERSAL\n')
	sleep(0.7)
	a = console.read(console.inWaiting())
	b = str(a.decode()).split('\n')
	print("Checking firmware version..")
	for i in b:
		for fw in b[2:-1]:
			if not "15.2(2)E5" in fw[39:48]:
				print("Wrong firmware version")
				console.write(b'show vers | include UNIVERSAL\n')
				exit()
			else:
				print("Firmware version OK!")
		if "WS-C2960X-24PS-L" in i:
			sw = str(i)[5:6]
			print("PoE switch found, choosing switch {}".format(sw))
			swprio = "switch {} priority 14\n\n".format(sw)
			return swprio
		else:
			pass
	print(a.decode()+'\n')
	sw = input("Couldnt find PoE switch, choose manually as listed above: ")
	swprio = "switch {} priority 14\n\n".format(sw)
	return swprio

if __name__ == '__main__':
	print("Finding serial port..")
	port = porttest()	# To check if you have an serial port connected
	
	if port == None:
		port = input("No serial connection found, enter it manually: ")		# If not found you will have to enter it manually
		try:
			serial.Serial(port)		# Checks the port you entered 
		except SerialException:
			print("Did not found connection on the '{}' port".format(port))
			exit()
	console = serial.Serial(port)
	console.read(console.inWaiting())

	commands = []	# Add commands here to use a list instead of a config file

	if len(commands) == 0:
		if os.path.exists("config.txt") == True:
			commands = "config.txt"			# Config name, can be changed to whatever
		else:
			commands = input("Couldn't find config file, enter it manually: ")
		console.write(b'\r\n\r\n')
		sleep(0.5)
		with open(commands, "r") as f:
				commands = f.readlines()
	console.write(b'!\n')
	sleep(0.5)
	a = console.read(console.inWaiting())
	hostname = a.split(b'\n')[1]

	if '>' in str(hostname):	# Checks which mode the prompt is in and goes in privileged mode if possible
		console.write(b'en\n')
		sleep(0.3)
	elif '(config' in str(hostname):
		console.write(b'end\n')
		sleep(0.3)
	elif '#' in str(hostname):
		pass
	else:
		print("Couldn't find prompt mode")
		exit()
	swprio = firstcheck() #	Checks for the PoE switch in the stack and makes it master
	init = {'!','conf t'}
	exec(init)	# Goes in to config mode and ready for the config file
	exec({swprio})	# Sets the PoE switch as master in the stack
	print("Initialization OK, running config file..")
	sleep(0.5)
	exec(commands)	# Writing the config line by line, command by command
