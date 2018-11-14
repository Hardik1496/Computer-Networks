import os,sys,_thread,socket
import argparse, time
import base64
from adblockparser import AdblockRules

argparser  = argparse.ArgumentParser(description="HTTP Proxy")
argparser.add_argument('-p', '--port', help='Port Number', default=8080)
argparser.add_argument('-u', '--userff', help='user based filter file', default='pass.txt')
argparser.add_argument('-f', '--filter', help='Domain Names to Filter', nargs='+', default=[])
args = argparser.parse_args()

port = args.port		
filter_hostnames_args = args.filter
userff = args.userff

BACKLOG = 50            # how many pending connections queue will hold
MAX_DATA_RECV = 999999  # max number of bytes we receive at once
DEBUG = True            # set to True to see the debug msgs
BLOCKED = ["bjp"]            # just an example. Remove with [""] for no blocking at all.
weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None,
				 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
				 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
msg_dict = {407: '407 Proxy Authentication Required', 405: 'Method Not Allowed' , 403: 'Forbidden', 404: 'Not Found'}
auth_dict = {}

def userFilter(userFp):

	try:
		with open(userFp, 'r') as f:
			lines = f.read().splitlines()

		filter_hostnames = {}
		for line in lines:
			cred = line.split(' ')[0]
			this_hostnames = []
			for item in line.split()[1:]:
				this_hostnames.append(item)

			filter_hostnames[base64.b64encode(bytes(cred, "utf-8"))] = this_hostnames

		return filter_hostnames

	except IOError:
		print("User Filtering File:  %s Does not Exist" %(userFp))
		exit()
		return None

def authStrings(authFp):

	try:
		with open(authFp, 'rb') as f:
			lines = f.read().splitlines()

		authList = []
		for line in lines:
			authList.append((base64.b64encode(bytes(line.split()[0]))).decode('utf_8'))
			auth_dict[(base64.b64encode(bytes(line.split()[0]))).decode('utf_8')] = (line.decode('ascii'))[:(line.decode('ascii')).find(':')]
		return authList

	except IOError:
		print("Authentication File:  %s Does not Exist" %(authFp))
		exit()
		return None

def send_error(code, client):

	version_string = 'HTTP/1.1'
	msg = msg_dict[code]

	year, month, day, hh, mm, ss, wd, y, z = time.gmtime(time.time())
	date_header = "%s, %02d %3s %4d %02d:%02d:%02d GMT\r\n" % (
				weekdayname[wd],
				day, monthname[month], year,
				hh, mm, ss)

	if code != 407:
		# response_string = version_string+ '  '+ str(code) + ' ' + msg+ '\r\nDate: '+date_header#+'Content-Type: text/html\r\nConnection: close\r\n'
		response_string = "%d %s" % (code, msg)
	else:
		response_string = version_string+ '  '+ str(code) + ' ' + msg+ '\r\nDate: '+date_header+'Proxy-Authenticate: Basic realm=\"Access to internal site\"\r\n'

	print(response_string)
	client.send(response_string.encode('utf-8'))

	return 0

def proxy_thread(conn, client_addr):

	# get the request from browser
	request = (conn.recv(MAX_DATA_RECV)).decode('utf_8')
	
	# parse the first line
	first_line = request.split('\n')[0]
	
	try:
		option = first_line.split()[0]
	except :
		return 0

	if option not in ['CONNECT', 'GET', 'HEAD', 'POST']:
		send_error(405, conn)
		return 0

	authentication =  request[request.find(': Basic ')+8:].split('\n')[0][:-1]
	if authentication not in authKeys:
		print('[AUTH ERROR]')
		send_error(407, conn)
		return 0
	print("Authentication done by ", auth_dict[authentication])

	try:
		# get url
		url = first_line.split(' ')[1]
	except socket.gaierror:
		print('[ERROR]')
		send_error(404, conn)
		return 0

	for i in range(0,len(BLOCKED)):
		if BLOCKED[i] in url:
			print("Blacklisted", first_line)
			conn.close()
			sys.exit(1)

	rules = AdblockRules(raw_rules)
	if rules.should_block(url):
                printout("Blocked\n",first_line,client_addr)
                conn.close()
                sys.exit(1)
	# print "Request", first_line
	
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

	rules = AdblockRules(raw_rules)

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
	raw_rules = []
    with open('easylist.txt') as f:
        raw_rules = f.read().splitlines()


	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
	authKeys = authStrings(userff)
	filter_hostnames = userFilter(userff)

	while True:
		try:
			s.bind(('', port))
			print("Server running on port %d" % (port))
			break
		except:
			port += 1

	# listenning
	s.listen(BACKLOG)
	
	# get the connection from client
	while 1:

		conn, client_addr = s.accept()

		# create a thread to handle request
		_thread.start_new_thread(proxy_thread, (conn, client_addr))
		
	s.close()