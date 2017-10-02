from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import logging
import json
import threading
import re

logger=logging.getLogger(__name__)

def parse_results(response_data):
    regex_pattern = re.compile('^\s+Test\s([A-Za-z0-9\-\_]+)\s+:\s([A-Za-z]+)')

    test_results = {}
    for line in response_data:
        result = regex_pattern.search(line)
        if result:
            test_results[result.group(1)] = result.group(2)

    return test_results


class PatchServerHandler(object):
    post_request_count = 0
    results = {}
    expected_requests = 0

    @staticmethod
    def update(results, headers):
        PatchServerHandler.results[headers['DISTRO']] = results
        
        PatchServerHandler.post_request_count += 1
        logger.info(PatchServerHandler.results)
        

    @staticmethod
    def check():
        if PatchServerHandler.post_request_count == PatchServerHandler.expected_requests:
            return True
        return False 

class PatchServer(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write("<html><body><h1>Hello</h1></body></html>")

    def do_HEAD(self):
        self._set_headers()
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        is_valid = self.check_request_data(post_data, self.headers)
        if not is_valid:
            self.send_error(400, 'Invalid message body')
        else:
            try:
                post_data = post_data.split('\r\n')
                test_results = parse_results(post_data)
                if test_results: PatchServerHandler.update(test_results, self.headers)
                self._set_headers()
            except KeyError:
                self.send_error('400', 'Invalid message structure')

    @staticmethod
    def check_request_data(data, headers):
        if headers['Content-Type'] != 'text/plain':
            return False
        return True

def start_server(handler, close_server, host='0.0.0.0', port=80):
    http_server = HTTPServer((host, port), handler)
    logger.info("Starting server on %s:%s" % (host, port))

    try:
        threading.Thread(target=http_server.serve_forever).start()
        while(not close_server()):
            pass
        http_server.shutdown()
    except KeyboardInterrupt:
        http_server.shutdown()

    http_server.server_close()
    logger.info("Stopping server on %s:%s" % (host, port))
