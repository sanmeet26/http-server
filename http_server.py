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
from shutil import rmtree
import json
from types import resolve_bases
import uuid

# request methods
implemented_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']

# # maximum allowed connections
# MAX_CONNECTIONS = 100

# status codes
status_codes = {'100': 'Continue', '200' : 'OK', '201': 'Created', '204': 'No Content', '301': 'Moved Permanently', '304': 'Not Modified', '400': 'Bad Request', '404': 'Not Found','405': 'Method Not Allowed', '411': 'Length Required', '415':'Unsupported Media Type', '501': 'Not Implemented', '505': 'HTTP Version Not Supported'}

# image file extensions
image_files = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico"]

STATUS_CODE = None
CLIENT_IP = None
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


def clear_logs(access=True, error=True):
    global CONFIG_DATA
    try:
        access_log_path = CONFIG_DATA['LOGS']['DIRECTORY'] + '/' + CONFIG_DATA['LOGS']['ACCESS']
        error_log_path = CONFIG_DATA['LOGS']['DIRECTORY'] + '/' + CONFIG_DATA['LOGS']['ERROR']
        if access:
            # check if file is present
            # if present clear if size exceeds limit
            if(os.path.isfile(access_log_path) and os.path.getsize(access_log_path) > 10**9):
                os.unlink(access_log_path)
        if error:
            # check if file is present
            # if present clear if size exceeds limit
            if(os.path.isfile(error_log_path) and os.path.getsize(error_log_path) > 10**9):
                os.unlink(error_log_path)
    except Exception as err:
        create_error_log("error", err)


def create_error_log(code="", err=""):
    global CONFIG_DATA, CLIENT_IP
    # clear error log for flooded data
    clear_logs(access=False, error=True)

    # follow defined log format

    date_time = get_current_localtime()
    p_id = str(os.getpid())
    t_id = str(threading.current_thread().ident)
    log = "[" + date_time + "]" + " "
    log += "[core: " + code + "]" + " "
    log += "[pid " + p_id + ":tid " + t_id + "]" + " "
    if CLIENT_IP != None:
        log += "[client " + CLIENT_IP + "]" + " "
    log += str(err)
    log += "\n"
    try:
        if not os.path.isdir(CONFIG_DATA['LOGS']['DIRECTORY']):
            os.mkdir(CONFIG_DATA['LOGS']['DIRECTORY'])
        fp = open(CONFIG_DATA['LOGS']['DIRECTORY'] + '/' + CONFIG_DATA['LOGS']['ERROR'], "a")
        fp.write(log)
        fp.close()
    except:
        fp = open("error.log", "a")
        fp.write(log)
        fp.close()


def create_access_log(request_method="", request_path="", request_http_version="", request_headers={}, response_body_size="-"):
    global STATUS_CODE, CONFIG_DATA, CLIENT_IP
    # clear access log for flooded data
    clear_logs(access=True, error=False)
    date_time = get_current_localtime()

    # follow defined log format

    if CLIENT_IP != None:
        log = CLIENT_IP + " "
    else:
        log = "- "
    log += "[" + date_time + "]" + " "
    log += "\"" + request_method + " " + request_path + " " + request_http_version + "\"" + " "
    log += str(STATUS_CODE) + " "
    log += str(response_body_size) + " "
    if "Referer" in request_headers:
        log += "\"" + request_headers["Referer"] + "\"" + " "
    else:
        log += "\"-\"" + " "
    if "User-Agent" in request_headers:
        log += "\"" + request_headers["User-Agent"] + "\""
    else:
        log += "\"-\"" + " "
    log += "\n"
    try:
        if not os.path.isdir(CONFIG_DATA['LOGS']['DIRECTORY']):
            os.mkdir(CONFIG_DATA['LOGS']['DIRECTORY'])
        fp = open(CONFIG_DATA['LOGS']['DIRECTORY'] + '/' + CONFIG_DATA['LOGS']['ACCESS'], "a")
        fp.write(log)
        fp.close()
    except Exception as err:
        create_error_log("error", err)

# this function checks the values in request body for POST/PUT requests
def examine_request_body_values(value=None):
    i = 0
    decoded_value = ""
    while i < len(value):
        try:
            # if '%' is encountered then get next two characters (hex), convert them into bytes, decode them and store into decoded_value
            if value[i] == "%":
                p_enc = value[i+1:i+3]
                bytesdata = bytes.fromhex(p_enc)
                decoded_value += bytesdata.decode("ASCII")
                i += 2
            # if '+' is encountered then add a space into decoded_value
            elif value[i] == "+":
                decoded_value += " "
            # otherwise just add alphanumeric character as it is
            else:
                decoded_value += value[i]
            i += 1
        except Exception as err:
            create_error_log("debug", err)
    return decoded_value

def get_segregated_data(client_socket=None, request=None):

    # parameters in request
    request_method = None
    request_path = None
    request_http_version = None
    request_headers = dict()
    request_body = dict()
    total_headers = 0

    # separating out request + request headers from request body
    request_line_headers = request.split('\r\n\r\n')[0]
    # request body (if present) is separated by a blank line
    

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
        total_headers += 1
        try:
            key, value = data.split(':', 1)
            request_headers[key.strip()] = value.strip()
        except Exception as err:
            create_error_log("debug", err)
            break

    parsed_data = request.split("\r\n")
    if request_method == "POST" or request_method == "PUT":
        original_length = int(request_headers["Content-Length"])
        recieved_body = request.split('\r\n\r\n')[1:]
        recieved_length = len("\r\n\r\n".join(recieved_body))

        if original_length > 1024 or (original_length - recieved_length) > 0:
            extra_data = original_length - recieved_length
            
            try:
                while extra_data > 0:
                    new_data = client_socket.recv(1024).decode('ISO-8859-1')
                    request = str(request) + str(new_data)
                    extra_data -= len(new_data)
            except Exception as err:
                create_error_log("debug", err)

            parsed_data = request.split("\r\n")
    
        if "Content-Type" in request_headers:
            if "application/x-www-form-urlencoded" in request_headers["Content-Type"]:
                # handle application form body ahead of header count
                tempBody = parsed_data[total_headers + 2].split("&")
                for tbody in tempBody:
                    try:
                        key, value = tbody.split("=")
                        # get valid value after hex decoding
                        request_body[key] = examine_request_body_values(value)
                    except Exception as err:
                        create_error_log("debug", err)
            elif "text/plain" in request_headers["Content-Type"]:
                # handle text plain body ahead of header count
                req_body = parsed_data[total_headers + 1:]
                index = 0
                for body in req_body:
                    index += 1
                    try:
                        key, value = body.split("=")
                        request_body[key] = value
                    except Exception as err:
                        create_error_log("debug", err)
                        request_body["body" + str(index)] = body
            elif "multipart/form-data" in request_headers["Content-Type"]:
                # handle multipart form body ahead of header count
                reqBody = parsed_data[total_headers + 1:]
                for i in range(1, len(reqBody) - 4):
                    if ";" in reqBody[i]:
                        try:
                            tbody = reqBody[i].split(";")
                            if len(tbody) == 2:
                                tkey = tbody[1].split("name=")[1].strip("\"")
                                request_body[tkey] = reqBody[i + 2]
                            elif len(tbody) == 3:
                                tkey = tbody[2].split("filename=")[
                                    1].strip("\"")
                                request_body[tkey] = str(reqBody[i + 3])
                                if str(tkey).endswith(tuple(image_files)):
                                    request_body[tkey] += "\r\n" + \
                                        str(reqBody[i + 4])
                                request_body["filename"] = tkey
                        except Exception as err:
                            create_error_log("debug", err)
                            # print(err)

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
        return response, RESPONSE_HEADERS["Content-Length"], False

    elif request_http_version != "HTTP/1.1":
        STATUS_CODE = 505
        response = "HTTP/1.1" + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        file_content = "<!DOCTYPE html><head><title>Error</title></head><body><h1>505 HTTP Version Not Supported</h1><p>The HTTP version in the request is not supported</p><p>Supported version : HTTP/1.1</p></body></html>"

        RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
        # RESPONSE_HEADERS["Content-Type"] = "text/html"
        RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        if request_method != "HEAD":
            response += "\r\n" + file_content

        response = response.encode()
        return response, RESPONSE_HEADERS["Content-Length"], False

    elif "Host" not in request_headers or (request_method in ["POST", "PUT"] and "Content-Type" not in request_headers):
        STATUS_CODE = 400
        response = "HTTP/1.1" + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
        file_content = "<!DOCTYPE html><head><title>Error</title></head><body><h1>400 Bad Request</h1><p>HTTP server detected bad request</p></body></html>"

        RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
        RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)

        for key, value in RESPONSE_HEADERS.items():
            response += key + ": " + value + "\r\n"

        if request_method != "HEAD":
            response += "\r\n" + file_content
        response = response.encode()
        return response, RESPONSE_HEADERS["Content-Length"], False
    elif request_method in ["POST", "PUT"]:
        if "Content-Length" not in request_headers:
            STATUS_CODE = 411
            # response html file
            file_content = "<!DOCTYPE html><html><head><title>HTTP Response</title></head><body><h1>411 Length Required</h1><p>Server received a request without Content Length</p></body></html>"
            response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes(str(STATUS_CODE))+ "\r\n"
            RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
            RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
            for key, value in RESPONSE_HEADERS.items():
                response += key + ": " + value + "\r\n"
            response += "\r\n" + file_content
            response = response.encode()
            return response, RESPONSE_HEADERS["Content-Length"], False
        elif "Content-Type" in request_headers:
            actual_type = request_headers["Content-Type"].strip().split(";")[0]
            if actual_type not in ["application/x-www-form-urlencoded", "text/plain", "multipart/form-data"]:
                STATUS_CODE = 415
                # response html file
                finalFile = "<!DOCTYPE html><html><head><title>Delta-Server</title></head><body><h1>415</h1><h2>Server received a request with unsupported media type</h2></body></html>"
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes(str(STATUS_CODE))+ "\r\n"
                RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
                RESPONSE_HEADERS["Content-Length"] = str(len(finalFile))
                for key, value in RESPONSE_HEADERS.items():
                    response += key + ": " + value + "\r\n"
                response += "\r\n" + finalFile
                response = response.encode('')
                return response, RESPONSE_HEADERS["Content-Length"], False
    
    # response = response.encode()
    return response, "0", True


# function to set and get cookie value
def set_cookie(client_IP=None):
    global CONFIG_DATA
    cookie_file = CONFIG_DATA['COOKIE']['FILE']
    try:
        # check whether cookie file is present or not. If not, then create a new json file
        if not os.path.isfile(cookie_file):
            fp = open(cookie_file, "w")
            # write into cookie file using json.dump()
            # indent attribute is for indentation purpose 
            json.dump([], fp, indent=4)
            fp.close()
        
        cookie_data = []
        # read the cookie file using json.load() and get the data
        fp = open(cookie_file, "r")
        cookie_data = json.load(fp)
        fp.close()

        # check whether this cookie entry is already present in cookie file. If yes then return it
        for cookie in cookie_data:
            if cookie["client_IP"] == str(client_IP) and "cookie" in cookie:
                return "session_id=" + cookie['cookie'] + "; SameSite=Strict"
        
        # otherwise create a new cookie for new user using uuid.uuid4()
        new_cookie = uuid.uuid4()
        new_entry = {
            'client_IP': str(client_IP),
            'cookie': str(new_cookie)
        }
        cookie_data.append(new_entry)

        # store this new created cookie
        fp = open(cookie_file, "w")
        json.dump(cookie_data, fp, indent=4)
        fp.close()

        return "session_id=" + new_entry['cookie'] + "; SameSite=Strict"
    except Exception as err:
        create_error_log("debug", err)


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

    try:
        # get file extension
        if os.path.isfile(CONFIG_DATA['DOCUMENT_ROOT']['PATH'] + request_path):
            file_extension = request_path.split('.')[-1]
        else:
            file_extension = "html"
    except Exception as err:
        create_error_log("debug", err)

    try:
        # get valid file path 
        valid_request_path = get_file_path(request_path)
    except Exception as err:
        create_error_log("debug", err)
    
    try:
        # get last modification time of file
        last_mod_time = get_last_modified_time(valid_request_path)
    except Exception as err:
        create_error_log("debug", err)
    
    #return details
    return file_extension, valid_request_path, last_mod_time

# make forbidden response with status code
def get_forbidden_response(http_version="", request_headers={}, file_extension="html"):
    global STATUS_CODE, CLIENT_IP
    STATUS_CODE = 403

    file_content = "<!DOCTYPE html><html><head><title>Error</title></head><body><h1>403 Forbidden</h1><p>The server understood the request, but is refusing to fulfill it. (restricted resource access)<p></body></html>"

    response = http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Content-Length"] = str(len(file_content))

    # set the cookie for this client
    RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

    for key, value in RESPONSE_HEADERS.items():
        response += str(key) + ": " + str(value) + "\r\n"
    response += "\r\n" + file_content
    # return response and body size
    return response, RESPONSE_HEADERS["Content-Length"]


def manage_GET(request_http_version, request_headers, request_path):
    global STATUS_CODE, RESPONSE_HEADERS, image_files, status_codes, CLIENT_IP
    response = ""
    file_content = ""
    response_body_size = "-"
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

                # set the cookie for this client
                RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response = response.encode()

            # if without conditional GET
            else:
                try:
                    # open and read the file
                    fp = open(valid_request_path, "rb")
                    file_content = fp.read()
                    fp.close()
                except Exception as err:
                    create_error_log("error", err)

                # create the response
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
                RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
                RESPONSE_HEADERS["Last-Modified"] = last_mod_time
                # set the cookie for this client
                RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response += "\r\n"
                response_body_size = RESPONSE_HEADERS["Content-Length"]
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
                
                # set the cookie for this client
                RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"

            # if without conditional GET
            else:
                try:
                    # open and read the file
                    fp = open(valid_request_path, "r")
                    file_content = fp.read()
                    fp.close()
                except Exception as err:
                    create_error_log("error", err)

                # create the response
                response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
                RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
                RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
                RESPONSE_HEADERS["Last-Modified"] = last_mod_time

                # set the cookie for this client
                RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

                for key, value in RESPONSE_HEADERS.items():
                    response += str(key) + ": " + str(value) + "\r\n"
                response += "\r\n" + file_content
                response_body_size = RESPONSE_HEADERS["Content-Length"]
        response = response.encode()

    create_access_log("GET", request_path, request_http_version, request_headers, response_body_size)
    return response


def manage_HEAD(request_http_version, request_headers, request_path):
    global STATUS_CODE, RESPONSE_HEADERS, status_codes, CLIENT_IP
    response = ""
    file_extension = ""
    response_body_size = "-"

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
    
    # set the cookie for this client
    RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

    # make response and return
    response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"

    for key, value in RESPONSE_HEADERS.items():
        response += str(key) + ": " + str(value) + "\r\n"
    response += "\r\n"
    response = response.encode()
    response_body_size = RESPONSE_HEADERS["Content-Length"]
    create_access_log("HEAD", request_path, request_http_version, request_headers, response_body_size)
    return response

def manage_POST(request_http_version, request_headers, request_path, request_body={}):
    global CONFIG_DATA, STATUS_CODE, RESPONSE_HEADERS, image_files, status_codes, CLIENT_IP

    response = ""
    file_extension = "html"
    response_body_size = "-"
    # set date and status code
    RESPONSE_HEADERS["Date"] = get_current_GMTtime()
    STATUS_CODE = 201

    # response html to be sent after successful POST request
    file_content = "<!DOCTYPE html><html><head><title>POST Response</title></head><body><h1>POST request succeeded</h1><p>Data recieved<p></body></html>"
    # print(request_body)
    # storing request body of POST request in a file
    if "filename" in request_body:
        client_file = request_body["filename"]
        file_mode = "w"
        try:
            client_file_content = request_body[request_body["filename"]]
            
            if str(request_body["filename"]).endswith(tuple(image_files)):
                file_mode = "wb"
                client_file_content = client_file_content.encode()

            # checking whether the client folder exist or not. If not then create it
            if not os.path.isdir(CONFIG_DATA['DOCUMENT_ROOT']['PATH'] + '/' + CONFIG_DATA['CLIENT_DATA']['DIRECTORY']):
                os.mkdir(CONFIG_DATA['DOCUMENT_ROOT']['PATH'] + '/' + CONFIG_DATA['CLIENT_DATA']['DIRECTORY'])
            # write file in that client folder 
            fp = open(CONFIG_DATA['DOCUMENT_ROOT']['PATH'] + '/' + CONFIG_DATA['CLIENT_DATA']['DIRECTORY'] + "/" + client_file, file_mode)
            fp.write(client_file_content)
        except Exception as err:
            create_error_log("error", err)

        if request_body["filename"] in request_body:
            del request_body[request_body["filename"]]

    # keep record of POST request for our server
    post_data = "POST\n"
    post_data = "Date: " + RESPONSE_HEADERS["Date"] + "\n" + "POST DATA:\n"
    for key, value in request_body.items():
        post_data += "\t" + str(key) + " = " + str(value) + "\n"
    post_data += "\n\n"

    # if not os.path.isdir(CONFIG_DATA['CLIENT_DATA']['DIRECTORY']):
    #     os.mkdir(CONFIG_DATA['CLIENT_DATA']['DIRECTORY'])
    try:
        # write data into POST location
        fp = open(CONFIG_DATA['CLIENT_DATA']['POST_FILE'], "a")
        fp.write(post_data)
        fp.close()
    except Exception as err:
        create_error_log("error", err)

    # create the response
    response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
    if "filename" in request_body:
        RESPONSE_HEADERS["Location"] = "http://localhost:" + CONFIG_DATA['DEFAULT_VALS']['PORT'] + "/Client_Folder/" + request_body["filename"]

    # set the cookie for this client
    RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

    for key, value in RESPONSE_HEADERS.items():
        response += key + ": " + value + "\r\n"
    response += "\r\n"
    response += file_content
    response = response.encode()
    response_body_size = RESPONSE_HEADERS["Content-Length"]
    create_access_log("POST", request_path, request_http_version, request_headers, response_body_size)
        
    return response


def manage_PUT(request_http_version="", request_headers={}, request_path="", request_body={}):
    global RESPONSE_HEADERS, STATUS_CODE, image_files, CLIENT_IP
    # response html file
    file_content = "<!DOCTYPE html><html><head><title>PUT Response</title></head><body><h1>PUT request succeeded</h1></body></html>"
    response = ""
    file_extension = "html"
    response_body_size = "-"
    # set date in response with valid format
    RESPONSE_HEADERS["Date"] = get_current_GMTtime()
    STATUS_CODE = 200
    path = "dump.txt"
    file_data_output = ""
    exists = True
    # check if file exists
    if not os.path.exists(request_path[1:]) and request_path != "/":
        STATUS_CODE = 201
        # necessary string path handling
        sep = request_path.split("/")
        expected_file = sep[-1].split(".")
        if len(expected_file) > 1:
            if sep[0] == "":
                path = "/".join(sep[1:-1])
            else:
                path = "/".join(sep[:-1])
            try:
                # create resource if absent
                os.makedirs(path)
            except Exception as error:
                create_error_log("error", error)
            path += "/" + sep[-1]
        else:
            # create resource if path doesn't have any file
            # and folder is our resource
            try:
                if sep[0] == "" and len(sep) > 1:
                    new_req_path = "/".join(sep[1:])
                else:
                    new_req_path = "/".join(sep)
                os.makedirs(new_req_path)
            except Exception as error:
                create_error_log("error", error)
            path = new_req_path + "/dump.txt"
        exists = False
    # if path exists and user doesn't have appropriate file permission
    if os.path.exists(request_path[1:]) and not os.access(request_path[1:], os.W_OK):
        # send forbidden
        response, msgbody_size = get_forbidden_response(request_http_version, request_headers)
        response_body_size = msgbody_size
        response = response.encode('ISO-8859-1')
        create_access_log("PUT", request_path, request_http_version, request_headers, response_body_size)
        return response
    # handle if request contains a file to be PUT
    if "filename" in request_body:
        resultFile = request_body["filename"]
        new_path = ""
        # necessary path manipulations in form of string
        if not exists:
            new_path = "/".join(path.rsplit("/", 1)) + "/"
        elif request_path[1:] != "":
            new_path = "/".join(request_path[1:].rsplit("/", 1)) + "/"
        try:
            file_mode = "a"
            file_data = request_body[request_body["filename"]]
            # check if file is image or not and change read mode accordingly
            if str(request_body["filename"]).endswith(tuple(image_files)):
                file_mode = "wb"
                file_data = file_data.encode()
            # write into file contents
            with open(new_path + resultFile, file_mode) as writeFile:
                writeFile.write(file_data)
        except Exception as error:
            create_error_log("error", error)

        if request_body["filename"] in request_body:
            del request_body[request_body["filename"]]

    for key, value in request_body.items():
        file_data_output += str(key) + " = " + str(value) + "\n"

    try:
        # if requested resource is not a file or is a folder
        # dump data into a dummy server created file
        if exists and request_path[1:] != "" and not os.path.isfile(request_path[1:]):
            path = request_path[1:] + "/dump.txt"
        with open(path, "w") as outputFile:
            outputFile.write(file_data_output)
    except Exception as error:
        create_error_log("error", error)
    # Once all necessary conditions satisfied
    # form a proper response message
    # combine necessary lines and send after encoding
    response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes(str(STATUS_CODE)) + "\r\n"
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Content-Length"] = str(len(file_content))
    RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)
    for key, value in RESPONSE_HEADERS.items():
        response += key + ": " + value + "\r\n"
    response += "\r\n" + file_content
    response = response.encode()
    response_body_size = RESPONSE_HEADERS["Content-Length"]
    # log request
    create_access_log("PUT", request_path, request_http_version, request_headers, response_body_size)
    return response


def manage_DELETE(request_http_version, request_headers, request_path, request_body):
    global STATUS_CODE, status_codes, RESPONSE_HEADERS, CONFIG_DATA, CLIENT_IP

    # make file content to send on success
    file_content = "<!DOCTYPE html><html><head><title>DELETE Response</title></head><body><h1>Specified Resource Deleted</h1></body></html>"
    file_extension = "html"
    response = ""
    response_body_size = "-"

    try:
        # if request_path is a file
        if os.path.isfile(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path) and request_path != "/notfound.html":
            # check for write access, if yes then remove/delete file
            if os.access(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path, os.W_OK):
                STATUS_CODE = 200
                os.remove(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path)
            # otherwise make forbidden response
            else:
                response, msgbody_size = get_forbidden_response(request_http_version, request_headers, file_extension)
                response = response.encode()
                response_body_size = msgbody_size
                create_access_log("DELETE", request_path, request_http_version, request_headers, response_body_size)
                return response
        # if request_path is a direcory
        elif os.path.isdir(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path):
            # check for write access, if yes then delete directory using shutil.rmtree()
            if os.access(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path, os.W_OK):
                STATUS_CODE = 200
                rmtree(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+request_path)
            # otherwise make forbidden response
            else:
                response, msgbody_size = get_forbidden_response(request_http_version, request_headers, file_extension)
                response = response.encode()
                response_body_size = msgbody_size
                create_access_log("DELETE", request_path, request_http_version, request_headers, response_body_size)
                return response
        # otherwise resource is not found
        else:
            STATUS_CODE = 404
            fp = open(CONFIG_DATA['DOCUMENT_ROOT']['PATH']+"/notfound.html")
            file_content = fp.read()
            fp.close()
    except Exception as err:
        create_error_log("error", err)
    
    # create the response and return it
    response = request_http_version + " " + str(STATUS_CODE) + " " + status_codes[str(STATUS_CODE)] + "\r\n"
    RESPONSE_HEADERS["Content-Type"] = get_content_type(file_extension)
    RESPONSE_HEADERS["Content-Length"] = str(len(file_content))

    # set the cookie for this client
    RESPONSE_HEADERS["Set-Cookie"] = set_cookie(CLIENT_IP)

    for key, value in RESPONSE_HEADERS.items():
        response += key + ": " + value + "\r\n"
    response += "\r\n" + file_content
    response = response.encode()

    response_body_size = RESPONSE_HEADERS["Content-Length"]
    create_access_log("DELETE", request_path, request_http_version, request_headers, response_body_size)

    return response


def client_thread(client_socket):

    try:
        # recieve the request from client and decode it
        request = client_socket.recv(1024).decode()

        if request == "":
            client_socket.close()
            return

        # print(request)

        # parse the request and get segregated data (methods, version, headers, request-body, etc)
        request_method, request_path, request_http_version, request_headers, request_body = get_segregated_data(client_socket, request)

        # check/examine request for validation
        response, response_body_size, is_valid = examine_request(request_method, request_http_version, request_headers)

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
        else:
            create_access_log(request_method, request_path, request_http_version, request_headers, response_body_size)

        # send the encoded response to client
        client_socket.send(response)

        # close the connection with the client
        client_socket.close()
        # print("Connection closed " + '*'*30 +"\n\n\n")
    except Exception as err:
        create_error_log("error", err)


def start_server(server_socket):
    global CONFIG_DATA, CLIENT_IP
    MAX_CONNECTIONS = int(CONFIG_DATA['MAX_CONNECTIONS_ALLOWED']['CONNECTIONS'])
    while True:
        try:
            if threading.active_count() <= MAX_CONNECTIONS:
                # initiate the connection with the client
                client_socket, client_address = server_socket.accept()
                # print("Connected to", client_address)

                CLIENT_IP = str(client_address[0])

                # create different thread for different client
                client_th = threading.Thread(target=client_thread, args=(client_socket,))

                # start the thread’s activity
                client_th.start()
        except Exception as err:
            create_error_log("error", err)
        # except Exception as err:
        #     # calling sys functions to get error details
        #     exc_type, exc_obj, exc_tb = sys.exc_info()
        #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        #     print(exc_type)
        #     print("Error occured in", fname, "at line no.", exc_tb.tb_lineno, ":")
        #     print("\t", err)
        #     sys.exit(1)
        
        

def create_server_socket():
    global CONFIG_DATA
    # create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # assign server name and server port
    # here it is localhost
    # SERVER_NAME = ''
    # SERVER_PORT = 12001
    try:
        SERVER_NAME = str(CONFIG_DATA['DEFAULT_VALS']['NAME'])
        SERVER_PORT = int(CONFIG_DATA['DEFAULT_VALS']['PORT'])
    except Exception as err:
        create_error_log("error", err)
        print("Invalid data in config file")
        sys.exit(1)

    try:
        # set the condition for port reusability whenever server is restarted
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind the server socket with port number
        server_socket.bind((SERVER_NAME, SERVER_PORT))

        # allow the server to listen to incoming connections
        server_socket.listen(1)
        # print("Listening on port", SERVER_PORT)
    except Exception as err:
        create_error_log("error", err)
    # except Exception as err:
    #     # calling sys functions to get error details
    #     exc_type, exc_obj, exc_tb = sys.exc_info()
    #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    #     print(exc_type)
    #     print("Error occured in", fname, "at line no.", exc_tb.tb_lineno, ":")
    #     print("\t", err)
    #     sys.exit(1)
    
    # return the server socket created
    return server_socket

def read_config_file():
    global CONFIG_DATA
    # declare configparser object
    CONFIG_DATA = configparser.ConfigParser()
    try:
        # read the config file
        CONFIG_DATA.read('config.ini')
        clear_logs()
    except Exception as err:
        create_error_log("error", err)
        sys.exit(1)

if __name__ == "__main__":
    try:
        # read config file
        read_config_file()

        # make the server socket
        server_socket = create_server_socket()

        # start the server
        start_server(server_socket)
    # when forcefully program execution is stopped using Ctrl+C key 
    except KeyboardInterrupt:
        print()
        sys.exit(1)
    print(server_socket)