#!/usr/bin/env python3
"""Private stream relay for an authenticated SSH Unix-socket forwarding tunnel."""
import argparse,os,socket,socketserver,threading

def serve(listen_unix=None,listen_port=None,target_unix=None,target_port=None):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            peer=socket.socket(socket.AF_UNIX if target_unix else socket.AF_INET,socket.SOCK_STREAM)
            try:
                peer.connect(target_unix if target_unix else ('127.0.0.1',target_port))
                def pump(source,destination):
                    try:
                        while True:
                            data=source.recv(65536)
                            if not data:break
                            destination.sendall(data)
                    except OSError:pass
                    finally:
                        try:destination.shutdown(socket.SHUT_WR)
                        except OSError:pass
                thread=threading.Thread(target=pump,args=(self.request,peer))
                thread.start();pump(peer,self.request);thread.join()
            finally:peer.close()
    cls=socketserver.ThreadingUnixStreamServer if listen_unix else socketserver.ThreadingTCPServer
    cls.daemon_threads=True;cls.allow_reuse_address=True
    address=listen_unix if listen_unix else ('127.0.0.1',listen_port)
    os.umask(0o077)
    with cls(address,Handler) as server:
        if listen_unix:os.chmod(listen_unix,0o600)
        try:server.serve_forever(poll_interval=.2)
        finally:
            if listen_unix:os.unlink(listen_unix)

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--listen-unix');g.add_argument('--listen-port',type=int)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--target-unix');g.add_argument('--target-port',type=int)
    serve(**vars(p.parse_args()))
