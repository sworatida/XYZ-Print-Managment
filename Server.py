import time
import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 1242        # Port to listen on (non-privileged ports are > 1023)

i = 0
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            i+=1
            time.sleep(0.7)
            conn.sendall(b'Ready')
            print(f"Sending {i}")
            # data = conn.recv(1024)
            # print(data)
            # if not data:
            #     break