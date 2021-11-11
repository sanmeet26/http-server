'''
    HTTP Server Implementation
'''

import socket
import sys
import os
import threading
import time
import datetime
from email.utils import formatdate
import configparser

# request methods
implemented_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

# # maximum allowed connections
# MAX_CONNECTIONS = 100

# status codes
status_codes = {'100': 'Continue', '200' : 'OK', '201': 'Created', '204': 'No Content', '301': 'Moved Permanently', '304': 'Not Modified', '400': 'Bad Request', '404': 'Not Found','405': 'Method Not Allowed', '501': 'Not Implemented', '505': 'HTTP Version Not Supported'}

# image file extensions
image_files = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico"]

STATUS_CODE = None

CONFIG_DATA = None

# minimal response headers
RESPONSE_HEADERS = {
    "Date": "",
    "Connection": "close",
    "Server": "Spax/0.0.1 (Ubuntu)",
    "Content-Length":"0",
    "Content-Language": "en-US"
}

def get_content_type(extension=None):
    # switch case table for mime types
    content_types = {
        "txt": "text/plain",
        "html": "text/html",
        "php": "text/html",
        "pdf": "application/pdf",
        "css": "text/css",
        "csv": "text/csv",
        "apng": "image/apng",
        "bmp": "image/bmp",
        "gif": "image/gif",
        "ico": "image/x-icon",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "json": "application/json",
        "js": "application/javascript",
        "bin": "application/octet-stream",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "mpeg": "video/mpeg",
        "webm": "video/webm",
        "3gp": "video/3gpp"
    }
    # if nothing gets matched return text plain
    return content_types.get(extension, "text/plain") + "; charset=ISO-8859-1"

# get local/GMT time
def get_datetime(local_time=False):
    return str(formatdate(timeval=None, localtime=local_time, usegmt=True))

# get current GMT time (in HTTP format - rfc1123)
def get_current_GMTtime():
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

# get current local time (in HTTP format)
def get_current_localtime():
    return time.strftime('%a, %d %b %Y %H:%M:%S +0530', time.localtime())

# get last modification time of file with given path
def get_last_modified_time(path=""):
    try:
        # For Unix, the epoch is January 1, 1970, 00:00:00 (UTC)
        seconds_since_epoch = os.path.getmtime(path)
        return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(seconds_since_epoch))
    except OSError:
        # print("Path '%s' does not exists or is inaccessible" % path)
        # sys.exit()
        return "Thu, 01 Jan 1970 00:00:00 GMT"

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
    file_extension = "html"

    # RESPONSE_HEADERS["Date"] = get_datetime()
    RESPONSE_HEADERS["Date"] = get_current_GMTtime()

    if request_method not in implemented_methods:
        # STATUS_CODE = 501
        STATUS_CODE = 405
        http_version = "HTTP/1.1"
        response = http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        # RESPONSE_HEADERS["Date"] = get_current_GMTtime()
        RESPONSE_HEADERS["Allow"] = "GET, HEAD, PUT, POST, DELETE"
        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        response = response.encode()
        return response, False

    elif request_http_version != "HTTP/1.1":
        STATUS_CODE = 505
        response = "HTTP/1.1" + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        file_content = "<!DOCTYPE html><head><title>Error</title></head><body><h1>505 HTTP Version Not Supported</h1><p>The HTTP version in the request is not supported</p><p>Supported version : HTTP/1.1</p></body></html>"

        RESPONSE_HEADERS["Content-Length"] = len(file_content)
        # RESPONSE_HEADERS["Content-Type"] = "text/html"
        RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        if request_method != "HEAD":
            response += "\r\n" + file_content

        response = response.encode()
        return response, False

    elif "Host" not in request_headers:
        STATUS_CODE = 400
        response = "HTTP/1.1" + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        file_content = "<!DOCTYPE html><head><title>Error</title></head><body><h1>400 Bad Request</h1><p>HTTP server detected bad request</p></body></html>"

        RESPONSE_HEADERS["Content-Length"] = len(file_content)
        RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        if request_method != "HEAD":
            response += "\r\n" + file_content
        response = response.encode()
        return response, False

    response = response.encode()
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
    response = response.encode()
    return response

def get_file_path(request_path=""):
    global CONFIG_DATA, STATUS_CODE

    # try to get document root, otherwise return notfound.html file path
    try:
        document_root = CONFIG_DATA['DOCUMENT_ROOT']['PATH']
    except:
        STATUS_CODE = 404
        return "htdocs/notfound.html"

    # if request file path is notfound.html then set STATUS_CODE to 404 and return notfound.html file path
    if request_path == "/notfound.html":
        STATUS_CODE = 404
        return "htdocs/notfound.html"

    valid_file_path = ""

    # check request path for dir, file and make valid_file_path
    if os.path.isdir(document_root + request_path):
        if request_path.endswith('/'):
            valid_file_path = document_root + request_path + "index.html"
        else:
            valid_file_path = document_root + '/' + "index.html"
    elif os.path.isfile(document_root + request_path):
        valid_file_path = document_root + request_path
    else:
        # if requested file/dir not found, then control will come here
        STATUS_CODE = 404
        valid_file_path = document_root + "/notfound.html"
    return valid_file_path

# returns validpath, file extension and last modification time
def get_file_details(request_path=""):
    global STATUS_CODE, CONFIG_DATA
    file_extension = ""

    # get file extension
    if os.path.isfile(CONFIG_DATA['DOCUMENT_ROOT']['PATH'] + request_path):
        file_extension = request_path.split('.')[-1]
    else:
        file_extension = "html"

    # get valid file path 
    valid_request_path = get_file_path(request_path)
    # get last modification time of file
    last_mod_time = get_last_modified_time(valid_request_path)
    
    #return details
    return file_extension, valid_request_path, last_mod_time

# make forbidden response with status code
def get_forbidden_response(http_version="", request_headers={}, file_extension="html"):
    global STATUS_CODE
    STATUS_CODE = 403

    file_content = "<!DOCTYPE html><html><head><title>Error</title></head><body><h1>403 Forbidden</h1><p>The server understood the request, but is refusing to fulfill it. (restricted resource access)<p></body></html>"

    response = http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Content-Length"] = str(len(file_content))

    for key, value in RESPONSE_HEADERS.items():
        response += str(key) + ": " + str(value) + "\r\n"
    response += "\r\n" + file_content
    # return response and body size
    return response, RESPONSE_HEADERS["Content-Length"]


def manage_GET(request_http_version, request_headers, request_path):
    global STATUS_CODE, RESPONSE_HEADERS, image_files, status_codes
    response = ""
    file_content = ""
    STATUS_CODE = 200

    # set the Date header
    RESPONSE_HEADERS["Date"] = get_current_GMTtime()

    # get required file data
    file_extension, valid_request_path, last_mod_time = get_file_details(request_path)

    # if requested file is image file
    if file_extension in image_files:
        # check whether file has read permission or not
        if not os.access(valid_request_path, os.R_OK):
            # if not then send forbidden response
            response, msgbody_size = get_forbidden_response(request_http_version, request_headers, file_extension)
            response = response.encode()
            response_body_size = msgbody_size
        else:
            # check for conditional GET requests
            if "If-Modified-Since" in request_headers:
                # time.strptime() parse a string representing a time according to a format. 
                # The return value is a struct_time as returned by gmtime() or localtime().
                time1 = time.strptime(request_headers["If-Modified-Since"].strip(), "%a, %d %b %Y %H:%M:%S GMT")
                time2 = time.strptime(last_mod_time.strip(), "%a, %d %b %Y %H:%M:%S GMT")
            
            # if last modification time of file is less than "If-Modified-Since" time then respond with 304 status code
            if STATUS_CODE != 404 and "If-Modified-Since" in request_headers and time1 > time2:
                STATUS_CODE = 304
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                if "Content-Type" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Content-Type"]
                if "Content-Length" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Content-Length"]
                if "Last-Modified" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Last-Modified"]

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response = response.encode()

            # if without conditional GET
            else:
                # open and read the file
                fp = open(valid_request_path, "rb")
                file_content = fp.read()

                # create the response
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
                RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
                RESPONSE_HEADERS["Last-Modified"] = last_mod_time

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response += "\r\n"
                response = response.encode()
                response += file_content
    
    # if requested file is not image file
    else:
        # check whether file has read permission or not
        if not os.access(valid_request_path, os.R_OK):
            # if not then send forbidden response
            response, msgbody_size = get_forbidden_response(request_http_version, request_headers, file_extension)
            response_body_size = msgbody_size
        else:
            # check for conditional GET requests
            if "If-Modified-Since" in request_headers:
                # time.strptime() parse a string representing a time according to a format. 
                # The return value is a struct_time as returned by gmtime() or localtime().
                time1 = time.strptime(request_headers["If-Modified-Since"].strip(), "%a, %d %b %Y %H:%M:%S GMT")
                time2 = time.strptime(last_mod_time.strip(), "%a, %d %b %Y %H:%M:%S GMT")
            
            # if last modification time of file is less than "If-Modified-Since" time then respond with 304 status code
            if STATUS_CODE != 404 and "If-Modified-Since" in request_headers and time1 > time2:
                STATUS_CODE = 304
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                if "Content-Type" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Content-Type"]
                if "Content-Length" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Content-Length"]
                if "Last-Modified" in RESPONSE_HEADERS:
                    del RESPONSE_HEADERS["Last-Modified"]

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"

            # if without conditional GET
            else:
                # open and read the file
                fp = open(valid_request_path, "r")
                file_content = fp.read()

                # create the response
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
                RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
                RESPONSE_HEADERS["Last-Modified"] = last_mod_time

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response += "\r\n" + file_content
        response = response.encode()

    return response


    # # create response with headers and content body
    # file_name = request_path
    # # check file_name and create response accordingly
    # if file_name == '/':
    #     fp = open("htdocs/index.html", 'r')
    #     content = fp.read()
    #     fp.close()
    #     response = request_http_version + " 200 " + status_codes['200'] + "\nServer: myServer\n\n" + content
    # else:
    #     try:
    #         # if client any how requests for notfound.html, then raise exception
    #         if file_name == "/notfound.html":
    #             raise Exception
    #         fp = open("htdocs"+file_name, 'r')
    #         content = fp.read()
    #         fp.close()
    #         response = request_http_version + " 200 " + status_codes['200'] + "\nServer: myServer\n\n" + content
    #     except:
    #         fp = open("htdocs/notfound.html", 'r')
    #         content = fp.read()
    #         fp.close()
    #         response = request_http_version + " 404 " + status_codes['404'] + "\nServer: myServer\n\n" + content

    # response = response.encode()
    # return response

def manage_HEAD(request_http_version, request_headers, request_path):
    global STATUS_CODE, RESPONSE_HEADERS, status_codes
    response = ""
    file_extension = ""

    STATUS_CODE = 200

    # set the Date header
    RESPONSE_HEADERS["Date"] = get_current_GMTtime()

    # get required file data
    file_extension, valid_request_path, last_mod_time = get_file_details(request_path)

    # set Content-Type and Last-Modified headers
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Last-Modified"] = last_mod_time

    # check file access permission
    if not os.access(valid_request_path, os.R_OK):
        STATUS_CODE = 403
        # make for forbidden response file content
        file_content = "<!DOCTYPE html><html><head><title>Error</title></head><body><h1>403 Forbidden</h1><p>The server understood the request, but is refusing to fulfill it. (restricted resource access)<p></body></html>"
        RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
    else:
        # if not forbidden then set Content-Length of requested resource 
        RESPONSE_HEADERS["Content-Length"] = str(os.path.getsize(valid_request_path))
    
    # make response and return
    response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"

    for key, value in RESPONSE_HEADERS.items():
        response += str(key) + ": " + str(value) + "\r\n"
    response += "\r\n"
    response = response.encode()

    return response    

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
    # response = manage_request(request)
    #####################

    # send the encoded response to client
    client_socket.send(response)

    # close the connection with the client
    client_socket.close()
    print("Connection closed " + '*'*30 +"\n\n\n")


def start_server(server_socket):
    global CONFIG_DATA
    MAX_CONNECTIONS = int(CONFIG_DATA['MAX_CONNECTIONS_ALLOWED']['CONNECTIONS'])
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
    global CONFIG_DATA
    # create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # assign server name and server port
    # here it is localhost
    # SERVER_NAME = ''
    # SERVER_PORT = 12001

    SERVER_NAME = str(CONFIG_DATA['DEFAULT_VALS']['NAME'])
    SERVER_PORT = int(CONFIG_DATA['DEFAULT_VALS']['PORT'])

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

def read_config_file():
    global CONFIG_DATA
    # declare configparser object
    CONFIG_DATA = configparser.ConfigParser()
    # read the config file
    CONFIG_DATA.read('config.ini')


if __name__ == "__main__":

    # read config file
    read_config_file()

    # make the server socket
    server_socket = create_server_socket()

    # start the server
    start_server(server_socket)

    print(server_socket)