#!/usr/bin/env python3

import os, sys
import socketserver
from http.server import BaseHTTPRequestHandler
import shutil
from urllib.parse import urlparse, parse_qs
import pathlib
import jinja2
from collections import namedtuple


TEMPLATES_DIRS = [pathlib.Path('templates/'), ]

jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=TEMPLATES_DIRS))


class Switch(namedtuple('Switch', 'id name gpio_pin reversed')):
    @property
    def value_file(self):
        return pathlib.Path('/sys/class/gpio/gpio{}/value'.format(self.gpio_pin))

    @property
    def value(self):
        return int(self.value_file.read_text())

    @value.setter
    def value(self, v):
        return self.value_file.write_text(str(v))

    def toggle_value(self):
        self.value = abs(self.value - 1)

    @property
    def state(self):
        try:
            v = self.value
        except OSError:
            return 'misconfigured'
        except ValueError:
            return 'unknown'

        combs_on = ((1, False), (0, True))
        val_rev = (v, self.reversed)

        if v in (1, 0):
            return 'on' if val_rev in combs_on else 'off'
        else: 
            return 'unknown'


def get_switches():
    return [
            Switch(1, 'Lamp', 1, False),
            Switch(2, 'LED', 10, False),
            Switch(-1, 'Kek', -1, False),
            ]


def toggle_switch(handler):
    clen = int(handler.headers.get('Content-Length'))
    req_body = handler.rfile.read(clen)
    p = parse_qs(req_body)
    
    sw_id = int(p.get(b'switch_id', [-1, ])[0])
    switch = next(filter(lambda s: s.id == sw_id, get_switches()), None)
    if not switch:
        return handle_404(handler)

    switch.toggle_value()

    handler.send_response(301)
    handler.send_header('Location', '/')
    handler.end_headers()


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
    msg = b'Not Found\n'
    handler.send_response(404)
    handler.send_header('Content-Type', 'text/html')
    handler.send_header('Content-Length', len(msg))
    handler.end_headers()
    handler.wfile.write(msg)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.startswith('/toggle/'):
            toggle_switch(self)
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

