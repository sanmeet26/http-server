'''
    HTTP Server Implementation
'''

import socket
import sys
import os
import threading
import datetime
from email.utils import formatdate

# request methods
implemented_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

# maximum allowed connections
MAX_CONNECTIONS = 100

# status codes
status_codes = {'100': 'Continue', '200' : 'OK', '201': 'Created', '204': 'No Content', '301': 'Moved Permanently', '304': 'Not Modified', '400': 'Bad Request', '404': 'Not Found', '501': 'Not Implemented', '505': 'HTTP Version Not Supported'}

STATUS_CODE = None

# minimal response headers
RESPONSE_HEADERS = {
    "Date": "",
    "Connection": "close",
    "Server": "Spax/0.0.1 (Ubuntu)",
    "Content-length":"0",
    "Content-Language": "en-US"
}

# get local/GMT time
def get_datetime(local_time=False):
    return str(formatdate(timeval=None, localtime=local_time, usegmt=True))

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

def examine_request(request_method, request_http_version, request_headers):
    global STATUS_CODE, RESPONSE_HEADERS
    response = ""
    file_content = ""

    RESPONSE_HEADERS["Date"] = get_datetime()

    if request_method not in implemented_methods:
        STATUS_CODE = 501
        http_version = "HTTP/1.1"
        response = http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"
        return response, False
    if request_http_version != "HTTP/1.1":
        STATUS_CODE = 505
        response = "HTTP/1.1" + " " + STATUS_CODE + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        file_content = "<!DOCTYPE html><head><title>Error</title></head><body><h1>505 HTTP Version Not Supported</h1><p>The HTTP version in the request is not supported</p><p>Supported version : HTTP/1.1</p></body></html>"

        RESPONSE_HEADERS["Content-length"] = len(file_content)
        RESPONSE_HEADERS["Content-Type"] = "text/html"

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        if request_method != "HEAD":
            response += "\r\n" + file_content
        return response, False
         

    return response, True

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
    if request_method.upper() not in implemented_methods:
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

def manage_GET(request_http_version, request_headers, request_path):
    pass

def manage_HEAD(request_http_version, request_headers, request_path):
    pass

def manage_POST(request_http_version, request_headers, request_path, request_body):
    pass

def manage_PUT(request_http_version, request_headers, request_path, request_body):
    pass

def manage_DELETE(request_http_version, request_headers, request_path, request_body):
    pass


def client_thread(client_socket):

    # recieve the request from client and decode it
    request = client_socket.recv(1024).decode()

    if request == "":
        client_socket.close()
        return

    print(request)

    # parse the request and get segregated data (methods, version, headers, request-body, etc)
    request_method, request_path, request_http_version, request_headers, request_body = get_segregated_data(client_socket, request)

    # check/examine request for validation
    response, is_valid = examine_request(request_method, request_http_version, request_headers)

    if is_valid:
        if request_method == "GET":
            response = manage_GET(request_http_version, request_headers, request_path)
        elif request_method == "HEAD":
            response = manage_HEAD(request_http_version, request_headers, request_path)
        elif request_method == "POST":
            response = manage_POST(request_http_version, request_headers, request_path, request_body)
        elif request_method == "PUT":
            response = manage_PUT(request_http_version, request_headers, request_path, request_body)
        elif request_method == "DELETE":
            response = manage_DELETE(request_http_version, request_headers, request_path, request_body)

    #####################
    # create the response
    response = manage_request(request)
    #####################

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