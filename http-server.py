'''
	Implementation of simple HTTP server
'''

from socket import *

# this function takes request and gives response to it
def handle_request(request):
	# find filename from headers
	headers = request.split("\n")
	filename = headers[0].split()[1]
	#print(filename)
	
	# if browser requests root of server, then index.html content will be there in response
	if filename == '/':
		filename = "/index.html"
	
	# try to open the requested file from htdocs folder
	# if file not found, then open notfound.html file and complete the response
	try:
		fp = open("htdocs" + filename, "r")
		content = fp.read()
		fp.close()
		response = "HTTP/1.1 200 OK\n\n" + content
		
	except FileNotFoundError:
		#response = "HTTP/1.1 404 NOT FOUND\n\nFile not found"
		fp = open("htdocs/notfound.html", "r")
		content = fp.read()
		fp.close()
		response = "HTTP/1.1 404 NOT FOUND\n\n" + content
		
	return response


# server name and port number
SERVER_NAME = '0.0.0.0'
SERVER_PORT = 12001

# creating socket and binding it to the port
server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.bind((SERVER_NAME, SERVER_PORT))

# server keeps on listening
server_socket.listen(4)
print("Listening on port %s ..."%SERVER_PORT)

while True:
	# keep accepting connection for any client 
	client_socket, client_address = server_socket.accept()
	
	# recieve and print the request by client
	request = client_socket.recv(2048).decode()
	print(request)
	
	# make the response

	# if request is empty string, then go to next iteration (i.e. look for next client)
	if request == "":
		continue

	# call function for handling request
	response = handle_request(request)
	
	# send created response to client
	client_socket.send(response.encode())
	
	# close client connection
	client_socket.close()

# close server socket
server_socket.close()


