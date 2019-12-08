#!/usr/bin/env python3

import os, sys
import socketserver
from http.server import BaseHTTPRequestHandler
import shutil
from urllib.parse import urlparse
import pathlib
import jinja2
from collections import namedtuple


TEMPLATES_DIRS = [pathlib.Path('templates/'), ]

jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=TEMPLATES_DIRS))


def switch(handler):
    p = pathlib.Path('/sys/class/gpio/gpio1/value') 
    if p.read_text().strip() == '1':
        p.write_text('0')
    else:
        p.write_text('1')
    handler.send_response(301)
    handler.send_header('Location', '/')
    handler.end_headers()


class Switch(namedtuple('Switch', 'id name gpio_pin')):
    @property
    def value_file(self):
        return pathlib.Path('/sys/class/gpio/gpio{}/value'.format(self.gpio_pin))

    @property
    def value(self):
        return int(self.value_file.read_text())

    @property
    def state(self):
        try:
            v = self.value
        except OSError:
            return 'unconfigured'
        except ValueError:
            return 'unknown'

        if v == 0:
            return 'on'
        elif v == 1:
            return 'off'
        else: 
            return 'unknown'


def get_switches():
    return [
            Switch(1, 'Lamp #1', 1),
            Switch(2, 'Lamp #2', 2),
            ]


def index(handler):
    body = jinja2_env.get_template('index.html').render(switches=get_switches()).encode()
    
    headers = {
        'Content-Type': 'text/html',
	'Content-Length': len(body),
    }
    handler.send_response(200)

    for h, v in headers.items():
        handler.send_header(h, v)
    handler.end_headers()
    handler.wfile.write(body) 


def handle_404(handler):
    handler.send_response(404)
    handler.end_headers()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith('/switch'):
            switch(self)
        else:
            handle_404(self)
	
    def do_GET(self):
        if self.path.startswith('/'):
            index(self)
        else:
            handle_404(self)
	

def main():
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8000

    bind_address = '0.0.0.0'
    httpd = socketserver.TCPServer((bind_address, port), Handler)
    print('Running server on {}:{}...'.format(bind_address, port))
    httpd.serve_forever()


if __name__ == '__main__':
    main()

