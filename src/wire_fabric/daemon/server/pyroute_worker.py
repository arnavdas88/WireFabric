from multiprocessing import Process, Pipe
from pyroute2 import IPRoute
import traceback
import sys

class IPRouteWorker:
    def __init__(self):
        self.parent_conn, self.child_conn = Pipe()
        self.process = Process(target=self._worker, args=(self.child_conn,))
        self.process.start()

    def _worker(self, conn):
        ipr = IPRoute()
        while True:
            try:
                msg = conn.recv()
                if msg == 'exit':
                    break
                method_name, args, kwargs = msg
                method = getattr(ipr, method_name)
                result = method(*args, **kwargs)
                conn.send(("ok", result))
            except Exception as e:
                tb = traceback.format_exc()
                conn.send(("error", (str(e), tb)))
        ipr.close()

    def call(self, method_name, *args, **kwargs):
        self.parent_conn.send((method_name, args, kwargs))
        status, data = self.parent_conn.recv()
        if status == 'ok':
            return data
        else:
            err_msg, traceback_str = data
            raise RuntimeError(f"{err_msg}\nTraceback:\n{traceback_str}")

    # def poll(self, *args, **kwargs):
    #     return self.call("poll", *args, **kwargs)

    def addr(self, *args, **kwargs):
        return self.call("addr", *args, **kwargs)

    def link(self, *args, **kwargs):
        return self.call("link", *args, **kwargs)

    def link_lookup(self, *args, **kwargs):
        return self.call("link_lookup", *args, **kwargs)

    def close(self):
        self.parent_conn.send('exit')
        self.process.join()
