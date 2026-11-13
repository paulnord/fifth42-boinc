#!/usr/bin/env python3
"""Refuse live loopback listeners while permitting normal TCP TIME_WAIT reuse."""
import argparse
import socket


def check_ports(ports):
    for port in ports:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as exc:
                raise RuntimeError(f'Loopback port {port} is unavailable: {exc}') from exc


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ports', type=int, nargs='+')
    check_ports(parser.parse_args().ports)
