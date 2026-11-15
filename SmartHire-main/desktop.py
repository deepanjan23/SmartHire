
import threading
import time
import socket
import urllib.request
import urllib.error

import webview
from werkzeug.serving import make_server

from app import app


HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}/"


def run_flask():
    server = make_server(HOST, PORT, app)
    print(f"SmartHire server running at {URL}")
    server.serve_forever()


def wait_for_server():
    # Bypass system HTTP/HTTPS proxies for localhost
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({})
    )

    for attempt in range(50):
        try:
            response = opener.open(URL, timeout=2)
            response.close()
            print("SmartHire server is ready!")
            return

        except urllib.error.HTTPError as error:
            # An HTTP response means the server is reachable
            print(f"Server responded with HTTP {error.code}")
            return

        except Exception as error:
            print(f"Waiting for server: {error}")
            time.sleep(0.2)

    raise RuntimeError(
        "SmartHire server did not respond on HTTP localhost."
    )


if __name__ == "__main__":

    server_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    server_thread.start()

    wait_for_server()

    print("Opening SmartHire desktop application...")

    webview.create_window(
        title="SmartHire | Resume Intelligence",
        url=URL,
        width=1280,
        height=800,
        min_size=(900, 600)
    )

    webview.start(
        debug=False
    )
