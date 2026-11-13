"""Real TCP regression checks for the preflight used by initialize/with_stack."""
import errno
from pathlib import Path
import socket
import subprocess
import sys
import unittest

CHECK = Path(__file__).resolve().parents[1] / 'stock' / 'check_ports.py'


class StockPorts(unittest.TestCase):
    def check(self, port):
        return subprocess.run([sys.executable, str(CHECK), str(port)],
                              capture_output=True, text=True)

    def test_live_listener_is_refused_even_with_reuseaddr(self):
        with socket.socket() as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 0))
            server.listen()
            port = server.getsockname()[1]
            result = self.check(port)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(f'Loopback port {port} is unavailable', result.stderr)

    def test_clean_shutdown_time_wait_is_allowed(self):
        with socket.socket() as server, socket.socket() as client:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 0))
            server.listen()
            port = server.getsockname()[1]
            client.connect(('127.0.0.1', port))
            connection, _ = server.accept()
            # The server actively closes, leaving its listening port in TIME_WAIT.
            connection.shutdown(socket.SHUT_WR)
            self.assertEqual(client.recv(1), b'')
            client.close()
            self.assertEqual(connection.recv(1), b'')
            connection.close()
        with socket.socket() as bare_probe:
            with self.assertRaises(OSError) as raised:
                bare_probe.bind(('127.0.0.1', port))
            self.assertEqual(raised.exception.errno, errno.EADDRINUSE)
        result = self.check(port)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
