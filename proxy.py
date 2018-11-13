
import os,sys,_thread,socket
# from PyQt4.QtNetwork import QNetworkAccessManager
# from abpy import Filter
from adblockparser import AdblockRules

#********* CONSTANT VARIABLES *********
BACKLOG = 50            # how many pending connections queue will hold
MAX_DATA_RECV = 999999  # max number of bytes we receive at once
DEBUG = True            # set to True to see the debug msgs
BLOCKED = []            # just an example. Remove with [""] for no blocking at all.

#**************************************
#********* MAIN PROGRAM ***************
#**************************************
def main():
    

    raw_rules = [    "||ads.example.com^",    "@@||ads.example.com/notbanner^$~script" ]
    with open('easylist.txt') as f:
        raw_rules = f.read().splitlines()
    # check the length of command running
    if (len(sys.argv)<2):
        print ("No port given, using :8080 (http-alt)" )
        port = 8080
    else:
        port = int(sys.argv[1]) # port from argument

    # host and port info.
    host = ''               # blank for localhost
    
    print ("Proxy Server Running on ",host,":",port)

    try:
        # create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # associate the socket to host and port
        s.bind((host, port))

        # listenning
        s.listen(BACKLOG)
    
    except (socket.error, (value, message)):
        if s:
            s.close()
        print ("Could not open socket:", message)
        sys.exit(1)


    # get the connection from client
    while 1:
        conn, client_addr = s.accept()

        # create a thread to handle request
        _thread.start_new_thread(proxy_thread, (conn, client_addr, raw_rules))
        
    s.close()
#************** END MAIN PROGRAM ***************

def printout(type,request,address):
    if "Block" in type or "Blacklist" in type:
        colornum = 91
    elif "Request" in type:
        colornum = 92
    elif "Reset" in type:
        colornum = 93

    print ("\033[",colornum,"m",address[0],"\t",type,"\t",request,"\033[0m")

#*******************************************
#********* PROXY_THREAD FUNC ***************
# A thread to handle request from browser
#*******************************************
def proxy_thread(conn, client_addr,raw_rules):

    # get the request from browser
    request = conn.recv(MAX_DATA_RECV)
    # type(request)
    # request= bytes(request, 'utf-8')
    # print("raw_rules",raw_rules)

    # parse the first line
    first_line = request.decode('utf8').split('\n')[0]

    # get url
    url = first_line.split(' ')[1]
    # adblockFilter = Filter(file("easylist.txt"))
    # rules = AdblockRules(raw_rules)

    for i in range(0,len(BLOCKED)):
        if BLOCKED[i] in url:
            printout("Blacklisted",first_line,client_addr)
            conn.close()
            sys.exit(1)
        if rules.should_block(first_line):
            printout("Blocked\nBlocked\nBlocked\nBlocked\nBlocked\nBlocked\nBlocked\nBlocked\nBlocked\nBlocked\n\n\n\n\n\n\n\n\n\n",first_line,client_addr)
            conn.close()
            sys.exit(1)
        # if adblockFilter.match(url):
        #     printout("Blocked",first_line,client_addr)
        #     conn.close()
        #     sys.exit(1)

    printout("Request",first_line,client_addr)
    # print "URL:",url
    # print
    
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
        
        print ("request ",request)
        i=0
        while i<10:
            # receive data from web server
            data = s.recv(MAX_DATA_RECV)
            
            if (len(data) > 0):
                # send to browser
                print ("data ",data)
                conn.send(data)
            else:
                break
            i=i+1
            print(i,"  =========================================")
        s.close()
        conn.close()
    except (socket.error, (value, message)):
        if s:
            s.close()
        if conn:
            conn.close()
        printout("Peer Reset",first_line,client_addr)
        sys.exit(1)
#********** END PROXY_THREAD ***********
    
if __name__ == '__main__':
    main()