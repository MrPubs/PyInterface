import socket
import sys
import time


def create_socket(protocol):
    if protocol.lower() == 'tcp':
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif protocol.lower() == 'udp':
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    else:
        raise ValueError("Protocol must be 'tcp' or 'udp'")


def main():

    ip = sys.argv[1]
    port = int(sys.argv[2])
    protocol = sys.argv[3]
    message = sys.argv[4]

    sock = create_socket(protocol)

    connected = False
    while not connected:
        try:
            if protocol.lower() == 'tcp':
                sock.connect((ip, port))
                connected = True

            else:
                connected = True

        except:
            print('failed to connect, retrying..')

    while True:
        try:
            if protocol.lower() == 'tcp':
                sock.sendall(message.encode())

            elif protocol.lower() == 'udp':
                sock.sendto(message.encode(), (ip, port))
            print(f"Sent: {message}")
            time.sleep(1)  # Wait a second before sending the next message

        except Exception as e:
            print(e)
            pass


if __name__ == "__main__":
    main()
