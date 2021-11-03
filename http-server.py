'''
    HTTP Server Implementation
'''

import socket
import sys
import os
import threading

# request methods
valid_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

# maximum allowed connections
MAX_CONNECTIONS = 100

# status codes
status_codes = {'100': 'Continue', '200' : 'OK', '201': 'Created', '204': 'No Content', '301': 'Moved Permanently', '304': 'Not Modified', '400': 'Bad Request', '404': 'Not Found', '501': 'Not Implemented'}


def get_segregated_data(client_socket=None, request=None):

    # parameters in request
    request_method = None
    request_path = None
    request_http_version = None
    request_headers = dict()

    # separating out request + request headers from request body
    request_line_headers = request.split('\r\n\r\n')[0]
    # request body (if present) is separated by a blank line
    request_body = request.split('\r\n\r\n')[1:]

    request_line_headers = request_line_headers.split('\r\n')
    # print(request)

    # list of contents of request line (first line of request)
    request_line = request_line_headers[0].split()

    # checking the length of request line
    if len(request_line) == 3:
        request_method, request_path, request_http_version = request_line
    elif len(request_line) == 2:
        request_method, request_path = request_line
    elif len(request_line) == 1:
        request_method = request_line[0]

    for data in request_line_headers[1:]:
        key, value = data.split(':', 1)
        request_headers[key.strip()] = value.strip()
    
    # print(request_method)
    # print(request_path)
    # print(request_http_version)
    # print(request_headers)
    # print(request_body)
    return request_method, request_path, request_http_version, request_headers, request_body


def manage_request(client_request):
    # parse the request
    request_line = client_request.split('\n')[0].split()

    request_method = None
    request_path = None
    http_version = None

    # checking the length of request line
    if len(request_line) == 3:
        request_method = request_line[0]
        request_path = request_line[1]
        http_version = request_line[2]
    elif len(request_line) == 2:
        request_method = request_line[0]
        request_path = request_line[1]
    else:
        request_method = request_line[0]

    # method validation
    if request_method.upper() not in valid_methods:
        print("Method is not valid")
        sys.exit(1)

    file_name = request_path
    
    # create response with headers and content body

    # check file_name and create response accordingly
    if file_name == '/':
        fp = open("htdocs/index.html", 'r')
        content = fp.read()
        fp.close()
        response = http_version + " 200 " + status_codes['200'] + "\nServer: myServer\n\n" + content
    else:
        try:
            # if client any how requests for notfound.html, then raise exception
            if file_name == "/notfound.html":
                raise Exception
            fp = open("htdocs"+file_name, 'r')
            content = fp.read()
            fp.close()
            response = http_version + " 200 " + status_codes['200'] + "\nServer: myServer\n\n" + content
        except:
            fp = open("htdocs/notfound.html", 'r')
            content = fp.read()
            fp.close()
            response = http_version + " 404 " + status_codes['404'] + "\nServer: myServer\n\n" + content

    print(response)

    # return the created response    
    return response

def client_thread(client_socket):

    # recieve the request from client and decode it
    request = client_socket.recv(1024).decode()

    if request == "":
        client_socket.close()
        return

    print(request)

    # create the response
    response = manage_request(request)

    # parse the request and get segregated data (methods, version, headers, request-body, etc)
    request_method, request_path, request_http_version, request_headers, request_body = get_segregated_data(client_socket, request)
    
    '''
        response, isvalid = validate_request(...)

        if isvalid:
            if request_method == "GET":
                manage_GET()
            elif request_method == "HEAD":
                manage_HEAD()
            elif request_method == "POST":
                manage_POST()
            elif request_method == "PUT":
                manage_PUT()
            elif request_method == "DELETE":
                manage_DELETE()
        

    '''
    # send the encoded response to client
    client_socket.send(response.encode())

    # close the connection with the client
    client_socket.close()
    print("Connection closed " + '*'*30 +"\n\n\n")


def start_server(server_socket):
    while True:
        try:
            if threading.active_count() <= MAX_CONNECTIONS:
                # initiate the connection with the client
                client_socket, client_address = server_socket.accept()
                # print("Connected to", client_address)

                # create different thread for different client
                client_th = threading.Thread(target=client_thread, args=(client_socket,))

                # start the thread’s activity
                client_th.start()

        except Exception as err:
            # calling sys functions to get error details
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type)
            print("Error occured in", fname, "at line no.", exc_tb.tb_lineno, ":")
            print("\t", err)
            sys.exit(1)
        
        

def create_server_socket():
    # create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # assign server name and server port
    # here it is localhost
    SERVER_NAME = ''
    SERVER_PORT = 12001

    try:
        # set the condition for port reusability whenever server is restarted
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind the server socket with port number
        server_socket.bind((SERVER_NAME, SERVER_PORT))

        # allow the server to listen to incoming connections
        server_socket.listen(1)
        print("Listening on port", SERVER_PORT)
    except Exception as err:
        # calling sys functions to get error details
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type)
        print("Error occured in", fname, "at line no.", exc_tb.tb_lineno, ":")
        print("\t", err)
        sys.exit(1)
    
    # return the server socket created
    return server_socket


if __name__ == "__main__":

    # make the server socket
    server_socket = create_server_socket()

    # start the server
    start_server(server_socket)

    print(server_socket)