import socket
import sys


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

    sock = create_socket(protocol)

    try:
        sock.bind((ip, port))
        print(f"Server started on {ip}:{port} using {protocol.upper()} protocol")

        if protocol.lower() == 'tcp':
            sock.listen(1)
            conn, addr = sock.accept()
            print(f"Connected by {addr}")

            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"Received: {data.decode()}")

            conn.close()

        elif protocol.lower() == 'udp':
            while True:
                data, addr = sock.recvfrom(1024)
                print(f"Received from {addr}: {data.decode()}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
