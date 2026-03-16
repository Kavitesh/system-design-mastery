"""
TCP Handshake Demo
==================
Demonstrates the TCP three-way handshake by creating a real
TCP server and client, logging every step of the connection.

Run: python tcp_handshake_demo.py
"""

import socket
import threading
import time


HOST = "127.0.0.1"
PORT = 9999


def tcp_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(1)
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    print(f"[SERVER] Waiting for TCP SYN from client...\n")

    conn, addr = server_sock.accept()
    print(f"[SERVER] <<< SYN received from {addr}")
    print(f"[SERVER] >>> Sending SYN-ACK back to {addr}")
    print(f"[SERVER] <<< ACK received - handshake complete!")
    print(f"[SERVER] Connection established with {addr}\n")

    # Receive data
    data = conn.recv(1024)
    print(f"[SERVER] <<< Received: {data.decode()}")

    # Send response
    response = "Hello from server! Connection is working."
    conn.sendall(response.encode())
    print(f"[SERVER] >>> Sent: {response}")

    conn.close()
    server_sock.close()
    print(f"[SERVER] Connection closed.\n")


def tcp_client():
    time.sleep(0.5)  # let server start first

    print(f"[CLIENT] Creating TCP socket...")
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"[CLIENT] >>> Sending SYN to {HOST}:{PORT}")
    start = time.time()
    client_sock.connect((HOST, PORT))
    elapsed = (time.time() - start) * 1000
    print(f"[CLIENT] <<< Received SYN-ACK from server")
    print(f"[CLIENT] >>> Sending ACK - handshake complete!")
    print(f"[CLIENT] Handshake took {elapsed:.2f}ms\n")

    # Send data
    message = "Hello from client! The TCP handshake worked."
    client_sock.sendall(message.encode())
    print(f"[CLIENT] >>> Sent: {message}")

    # Receive response
    data = client_sock.recv(1024)
    print(f"[CLIENT] <<< Received: {data.decode()}")

    client_sock.close()
    print(f"[CLIENT] Connection closed.")


def main():
    print("=" * 60)
    print("  TCP THREE-WAY HANDSHAKE DEMO")
    print("=" * 60)
    print()
    print("The TCP handshake establishes a connection in 3 steps:")
    print("  1. Client sends SYN (synchronize)")
    print("  2. Server responds with SYN-ACK (synchronize-acknowledge)")
    print("  3. Client sends ACK (acknowledge)")
    print()
    print("After the handshake, data flows in both directions.")
    print("-" * 60)
    print()

    # Run server and client in separate threads
    server_thread = threading.Thread(target=tcp_server)
    client_thread = threading.Thread(target=tcp_client)

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()

    print()
    print("=" * 60)
    print("KEY TAKEAWAYS:")
    print("  - Every TCP connection costs 1 round trip (SYN -> SYN-ACK -> ACK)")
    print("  - Localhost: < 1ms overhead")
    print("  - Same datacenter: ~0.5ms overhead")
    print("  - Cross-continent: ~150ms overhead")
    print("  - This is why connection pooling and keep-alive matter!")
    print("=" * 60)


if __name__ == "__main__":
    main()
