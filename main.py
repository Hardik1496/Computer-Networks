import os,sys,_thread,socket
import argparse, time
import base64
from adblockparser import AdblockRules

argparser  = argparse.ArgumentParser(description="Proxy Server")
argparser.add_argument('-p', '--port', help='Port Number', default=8080)
argparser.add_argument('-u', '--userfile', help='authentication file', default='pass.txt')
args = argparser.parse_args()

port = args.port		
auth_file = args.userfile
prev_authentication = ""

# importing rules for adblocker from easylist.txt
raw_rules = []
with open('easylist.txt') as f:
	raw_rules = f.read().splitlines()
rules = AdblockRules(raw_rules)

BACKLOG = 50            		# how many pending connections queue will hold
MAX_DATA_RECV = 999999 		 	# max number of bytes we receive at once
BLOCKED = ["bjp"]            	# just an example. Remove with [""] for no blocking at all.
msg_dict = {407: '407 Proxy Authentication Required', 405: 'Method Not Allowed' , 403: 'Forbidden', 404: 'Not Found'}
auth_dict = {}

def authStrings(authFile):

	try:
		with open(authFile, 'rb') as f:
			lines = f.read().splitlines()

		authList = []
		for line in lines:
			authList.append((base64.b64encode(bytes(line.split()[0]))).decode('utf_8'))
			auth_dict[(base64.b64encode(bytes(line.split()[0]))).decode('utf_8')] = (line.decode('ascii'))[:(line.decode('ascii')).find(':')]
		return authList

	except IOError:
		print("Authentication File:  %s Does not Exist" %(authFile))
		exit()
		return None

def proxy_thread(conn, client_addr):

	global prev_authentication
	# get the request from client
	request = (conn.recv(MAX_DATA_RECV)).decode('utf_8')
	
	# parse the first line
	first_line = request.split('\n')[0]
	
	# getting type of request
	try:
		req_type = first_line.split()[0]
	except :
		return 0

	# checking for validity of request type 
	if req_type not in ['CONNECT', 'GET', 'HEAD', 'POST']:
		print(msg_dict[405])
		return 0

	authentication =  request[request.find(': Basic ')+8:].split('\n')[0][:-1]
	if authentication != prev_authentication:
		if authentication not in authKeys:
			print(msg_dict[407])
			return 0
		else:
			prev_authentication = authentication
			print("Authentication done by ", auth_dict[authentication])

	try:
		# get url
		url = first_line.split(' ')[1]
	except socket.gaierror:
		print(msg_dict[404])
		return 0

	# searching for blacklisted url
	for i in range(0,len(BLOCKED)):
		if BLOCKED[i] in url:
			print("Blacklisted", first_line)
			conn.close()
			sys.exit(1)

	if rules.should_block(url):
		print("Ad Blocked")
		conn.close()
		sys.exit(1)
	
	# find the webserver and port
	http_pos = url.find("://")          # find pos of ://
	if (http_pos==-1):
		temp = url
	else:
		temp = url[(http_pos+3):]       # get the rest of url
	
	port_pos = temp.find(":")           # find the port pos (if any)

	# find end of web server
	webserver_pos = temp.find("/")
	if webserver_pos == -1:
		webserver_pos = len(temp)

	webserver = ""
	port = -1
	if (port_pos==-1 or webserver_pos < port_pos):      # default port
		port = 80
		webserver = temp[:webserver_pos]
	else:       # specific port
		port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
		webserver = temp[:port_pos]

	try:
		# create a socket to connect to the web server
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
		s.connect((webserver, port))
		s.send(request.encode('utf_8'))         # send request to webserver
		
		while 1:
			# receive data from web server
			data = s.recv(MAX_DATA_RECV)
			
			if (len(data) > 0):
				# send to browser
				conn.send(data)
			else:
				break

		s.close()
		conn.close()
	except(socket.error):
		if s:
			s.close()
		if conn:
			conn.close()
		# print "Reset", first_line
		sys.exit(1)

if __name__ == '__main__':

	# create a socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
	authKeys = authStrings(auth_file)

	#Trying ports till success
	while True:
		try:
			s.bind(('', port))
			break
		except:
			port += 1

	print("Server running on port %d" % (port))

	# listenning
	s.listen(BACKLOG)
	
	# get the connection from client
	while 1:

		conn, client_addr = s.accept()

		# create a thread to handle request
		_thread.start_new_thread(proxy_thread, (conn, client_addr))
		
	# close socket
	s.close()