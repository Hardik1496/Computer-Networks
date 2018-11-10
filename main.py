import os,sys,thread,socket
import argparse

argparser  = argparse.ArgumentParser(description="HTTP Proxy")
argparser.add_argument('-p', '--port', help='Port Number', default=8080)
# argparser.add_argument('-u', '--userff', help='user based filter file', default='dict.txt')
# argparser.add_argument('-f', '--filter', help='Domain Names to Filter', nargs='+', default=[])
args = argparser.parse_args()
port = args.port

BACKLOG = 50            # how many pending connections queue will hold
MAX_DATA_RECV = 999999  # max number of bytes we receive at once
DEBUG = True            # set to True to see the debug msgs
BLOCKED = ["bjp"]            # just an example. Remove with [""] for no blocking at all.


def printout(type,request,address):
	if "Block" in type or "Blacklist" in type:
		colornum = 91
	elif "Request" in type:
		colornum = 92
	elif "Reset" in type:
		colornum = 93

	# print "\033[",colornum,"m",address[0],"\t",type,"\t",request,"\033[0m"
	print type, request

def proxy_thread(conn, client_addr):

	# get the request from browser
	request = conn.recv(MAX_DATA_RECV)
	
	# parse the first line
	first_line = request.split('\n')[0]

	# get url
	url = first_line.split(' ')[1]

	for i in range(0,len(BLOCKED)):
		if BLOCKED[i] in url:
			printout("Blacklisted",first_line,client_addr)
			conn.close()
			sys.exit(1)


	printout("Request",first_line,client_addr)
	
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
		s.send(request)         # send request to webserver
		
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
	except socket.error, (value, message):
		if s:
			s.close()
		if conn:
			conn.close()
		# printout("Peer Reset",first_line,client_addr)
		sys.exit(1)

if __name__ == '__main__':

	# create a socket
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
	
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
		thread.start_new_thread(proxy_thread, (conn, client_addr))
		
	s.close()