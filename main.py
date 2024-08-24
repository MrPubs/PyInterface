
# IO Interface
import socket
import multiprocessing as mp
import threading
# import pandas as pd
import numpy as np
import yaml
import serial
# import sys
import keyboard
import serial.tools.list_ports
from datetime import datetime, timedelta
from writer import DBHandler

from time import sleep
from time import time

class Interface_IO:
    '''
    The Interface IO Serves as the Communicating Component of the Interface
    Which Encapsulates all the Functionality regarding Receiving and
    Transmitting Packets Through the Interface. The Interface IO Knows
    to Set up based on the added project yaml file which specifies how
    to set up the communicators & Their Addresses.
    '''
    reset = "\033[0m"

    # Initialize
    def __init__(self, sess_controller, inq, outq, endpoint1: str='', endpoint2: str='', endpoint3: str='') -> None:

        # Read & Set Datasheet
        with open('Communication.yaml','r') as yamlf:
            self.datasheet = yaml.safe_load(yamlf)

        # Connections
        self.open_sockets = {

            'clients': [],
            'servers': []

        }
        self.clients = []
        self.servers = []
        self.inputs = inq
        self.outputs = outq

        # Server Params
        self.interface_server_ip = "127.0.0.1"
        self.sess = sess_controller
        self.socket_timeout = 3
        self.codec = 'utf-8'

        # Endpoints
        self.endpoint1 = endpoint1
        self.endpoint2 = endpoint2
        self.endpoint3 = endpoint3

        print("[InterfaceIO] Initialized successfully!")

    def work(self) -> None:
        '''

        :return: Nothing!

        The Purpose of this Function is to fulfill the main body of the Interface IO - Handling Inputs Output &
        Host the Session Loop. Here Worker Threads Start, Run, Close, Restart and Everything
        that Happens between those states.
        '''
        while True:

            # Initialize Session..
            if self.sess.value:


                # Get Engine Started..
                print(f"[InterfaceIO] Firing Engine!")
                for worker in self.clients + self.servers:
                    worker[0].start()  # index 0 -> thread, index 1 -> socket

                # Session Started!
                print(f"[InterfaceIO] Session Live! [{self.interface_server_ip}]")

                # Session Loop
                while self.sess.value:

                    sleep(0.001)

                    # Restart Dead Threads
                    dead_workers = [dead_listener for dead_listener in self.clients if not dead_listener[0].is_alive()]
                    if dead_workers and self.sess.value:

                        for dead_thread, sock in dead_workers:
                            relevant_list = self.servers if (dead_thread, sock) in self.servers else self.clients

                            # Get Thread Params
                            protocol = 'UDP' if 'UDP' in dead_thread.name.upper() else 'TCP'
                            thread_index = relevant_list.index((dead_thread, sock))

                            # Make New Thread, Replace Old Thread, Start New Thread, Delete Old Thread
                            func = self._handle_client_udp if protocol == 'UDP' else self._handle_client_tcp
                            new_thread = threading.Thread(target=func, args=(sock, None), daemon=True, name=f'Thread #{thread_index}-{func.__name__}')
                            relevant_list[thread_index] = (new_thread, sock)
                            new_thread.start()

                            print(f"[InterfaceIO] Reopened New Thread [{dead_thread} -> {new_thread}]!")

                print('[InterfaceIO] Ending Session..')
                # Close Workers
                for worker in self.clients + self.servers:

                    # Exhaust thread
                    while worker[0].is_alive():
                        sleep(0.1)

                    # Close Sockets
                    if worker[1]:
                        worker[1].close()

                # Restart
                self.open_sockets = {

                    'clients': [],
                    'servers': []

                }
                self.clients = []
                self.servers = []
                self.__enter__()

            sleep(0.01)

    # Helpers --------------------------------------------------------------------------------------------------------
    def _open_socket(self,category: str, protocol=socket.SOCK_STREAM, ip: str=None, port: int=12000, remark: str =''):
        '''

        :param category: Category Selector for Either 'Clients' Or 'Servers'.
                         Clients: A Collective of Clients that are Sending Data To The Interface, Defines Local Listen Port.
                         Servers: A Collective of Servers that are Receiving Data From the Interface. Defines Networks Listen Port.
        :param protocol: Defines What Protocol the Socket is Using from either 'TCP' or 'UDP'.
                         UDP: Defined by entering the Value 'socket.SOCK_DGRAM'.
                         TCP: Defined by entering the Value 'socket.SOCK_STREAM'.
        :param ip: Defines IP Address of the Listen Port for the Socket.
        :param port: Defines Port on the Machine with the defined IP Address for the Socket.
        :param remark: Contains a Remark for What is the Socket's Purpose.
        :return: Newly Opened Socket & Its Coupled Address.
        '''

        protocol_str: str = 'UDP' if protocol == socket.SOCK_DGRAM else 'TCP'

        # IP, Port combination -> Destination
        ip = self.interface_server_ip if not ip else ip
        address: tuple = (ip, port)

        # Create a Socket
        new_socket: socket.socket = socket.socket(socket.AF_INET, protocol)
        new_socket.settimeout(self.socket_timeout)

        # Add To open sockets Dict
        self.open_sockets[category].append((new_socket,address))
        print(f"[InterfaceIO] Opened Socket: {ip}:{port} Using {protocol_str} Protocol Succesfuly!! ({remark})")

        return new_socket,address

    def _iterate_open_sock(self, sock_lst: list, category: str) -> list[socket]:
        '''

        :param sock_lst: List Of Sockets where every Member of the List contains the following Data Structure:
                         [port, protocol, remark, color, host]
        :param category: Category Selector for Either 'Clients' Or 'Servers'.
                         Clients: A Collective of Clients that are Sending Data To The Interface, Defines Local Listen Port.
                         Servers: A Collective of Servers that are Receiving Data From the Interface. Defines Networks Listen Port.
        :return: List of Newly Opened Sockets

        Iterates Open Sock Function Over List
        '''

        open_socks = []
        for sock in sock_lst:

            # Params
            port, protocol, remark, _, host, *_ = list(sock.values())
            protocol = socket.SOCK_STREAM if protocol == 'TCP' else socket.SOCK_DGRAM if protocol == 'UDP' else 'UART' if protocol == 'UART' else None
            host = self.interface_server_ip if host == 'local' else self.endpoint2 if host == 'endpoint2' else self.endpoint1 if host == 'endpoint1' else self.endpoint3
            # TODO: Make Dynamic host selector with infinite support

            # Open Every Socket and save to class
            open_sock = self._open_socket(category=category,ip=host, port=port, protocol=protocol, remark=remark)
            open_socks.append(open_sock)

        return open_socks

    # Handlers --------------------------------------------------------------------------------------------------------
    def _handle_client_uart(self, port: str, baudrate: int, flag: list, packet_size: int,tickrate: int = 0.001) -> None:
        '''

        :param port: Port definition for what to Listen to.
        :param baudrate: Bus Size for the Port Communication.
        :param flag: Flag to look for before a Message.
        :param packet_size: Size of the Message that comes after a Flag.
        :param tickrate: Frequency of Message Pick up.
        :param color: Color of the Message printed by thread.
        :return: Nothing!

        Function to handle all Message Pickup through Port using UART (Serial Data) - Used Via Threading.
        Supports crc Validation
        '''

        def verify_crc(packet: list, size: int) -> bool:
            '''

            :param packet: String Packet for the Receive Message
            :param size: Length of the Expect Packet (Including Flag)
            :return: True or False if Verified by crc.

            Function for Verifying Packet Using crc.
            '''

            data_arr = [np.uint8(0) for i in range(size)]
            crc = np.uint8(0)

            for i in range(size):

                # Convert to Workable Data..
                hex_format = [str(format(x, '#04x')).split('0x')[-1] for x in packet]
                packet_string = (''.join(hex_format))
                data_arr[i] = int(packet_string[i * 2:i * 2 + 2], 16)

            # Calculate crc
            for i in range(size - 1):
                crc ^= data_arr[i]

            # Match
            result = crc == data_arr[-1]
            return result

        def validate_splitted_flag(mem_cell: list, parsed: list, flag: list) -> bool:
            '''

            :param mem_cell: Memory Cell Containing the Old parsed raw data
            :param parsed: The Current Cell Containing the Current parsed raw data
            :param flag: The Flag That Signifies a Hit
            :return: Bool stating whether the Flag has ended in the current cell, and started in the old cell

            this function relays on assumptions!
            1. the cell size is the same size as the flag - the size of the cell is defined as the length of the flag..
            2. by that assumption, we can infer that the flag can either be found completely in one cell, or split over 2 cells
            '''

            # Get Flag Split Index
            if flag[0] in mem_cell:
                mc_i = mem_cell.index(flag[0])  # mc = mem_cell
                mem_cell_slice = mem_cell[mc_i:]

                # Slice Parsed
                p_i = len(flag) - len(mem_cell_slice)  # p = parsed
                parsed_slice = parsed[:p_i]

                # Check Candidate for Match
                candidate = mem_cell_slice + parsed_slice
                match = candidate == flag
                result = (match, p_i)

            else:
                result = (False, None)

            return result

        # Setup
        flag_size = len(flag)
        thread_id = int(threading.current_thread().name[8]) # Steal index from thread name!

        # Try to get Port if not given! # TODO: Set Low Latency on Port if not already low latency!
        if not port:
            for item in list(serial.tools.list_ports.comports()):
                if item.serial_number == 'FT0EJ4YTA':
                    port = item.name

        # Establish Connection
        conn = serial.Serial(port, baudrate=baudrate, bytesize=8, parity='N', stopbits=1, timeout=None)

        # Start Listening
        parsed = [None, None]
        while self.sess.value:  # Make Session & Thread Condition
            # Tick
            sleep(tickrate)

            # Receive
            raw = conn.read(flag_size)

            # Validate Input length
            if len(raw) == flag_size:

                mem_cell = parsed
                parsed = [x for x in raw]

                # Full Flag
                if parsed == flag:
                    packet = [x for x in conn.read(packet_size)]

                elif validate_splitted_flag(mem_cell=mem_cell, parsed=parsed, flag=flag):
                    packet = [parsed[1]] + [x for x in conn.read(packet_size - 1)]

                # No Flag Found
                else:
                    packet = None

                # Handle Packet
                if packet:

                    # Get Packet Time
                    ts = datetime.utcnow()

                    # Verify Packet Using crc
                    if verify_crc(flag + packet, packet_size + flag_size):
                        self.inputs[thread_id].put((ts, packet))
                        # print(f"\033{color} Port: {port} | Packet: {packet}{self.reset}")

                    else:
                        print(f'BAD PACKET!: {parsed} | {packet} | {len(packet)}')
                        pass

    def _handle_client_udp(self, sock:socket.socket, address: tuple[str,int]) -> None:
        '''

        :param sock: Socket Object.
        :param address: Address Coupling of IP & Port.
        :return: Nothing!

        Binds UDP Socket to an Address and Listens to All Communication through Port - Used Via Threading.
        '''

        # Setup
        thread_id = int(threading.current_thread().name[8])
        if address:
            sock.bind(address)
            port = address[1]

        # Port Determination for Thread Restart
        else:
            port = threading.current_thread()._args[0].getsockname()[1]

        # Get Color
        for item in (list(self.datasheet['clients'].values())):

            ds_port, _, _, color, *_ = item.values()
            if ds_port == port:
                break

        # Listen..
        connected = True
        while connected and self.sess.value:

            # Try To Receive Packet
            try:
                packet = sock.recvfrom(1024)[0].decode(self.codec)
                self.inputs[thread_id].put(packet)
                # print(f"\033{color} Port: {port} | Packet: {packet}{self.reset}")

            # Timeout
            except socket.timeout:
                pass

            # Client Died
            except ConnectionResetError:
                print("Error Code: 0")

                # Exit
                connected = False

        print(f'[InterfaceIO] Done with UDP Listener! [Thread: {threading.current_thread()}]')

    def _handle_client_tcp(self, sock:socket.socket, address: str) -> None:
        '''

        :param sock: Socket Object.
        :param address: Address Coupling of IP & Port.
        :return: Nothing!

        Binds TCP Socket to an Address and Listens to All Communication through Port - Used Via Threading.
        '''

        # Setup
        thread_id = int(threading.current_thread().name[8])
        if address:
            sock.bind(address)
            sock.listen(5)
            port = address[1]

        # Port Determination for Thread Restart
        else:
            port = threading.current_thread()._args[0].getsockname()[1]

        # Get Color
        for item in (list(self.datasheet['clients'].values())):

            ds_port, _, _, color, *_ = item.values()
            if ds_port == port:
                break

        while True:

            # Establish Communication
            try:
                sock.listen()
                conn, addr = sock.accept()
                break

            # Timeout
            except socket.timeout:
                if not self.sess.value:
                    break
        # Listen..
        connected = True
        while connected and self.sess.value:

            # Try To Receive Packet
            try:
                packet = conn.recv(1024).decode(self.codec)
                self.inputs[thread_id].put(packet)
                # print(f"\033{color} Port: {port} | Packet: {packet}{self.reset}")

            # Timeout
            except socket.timeout:
                pass

            # Client Died
            except ConnectionResetError:
                print(f"[InterfaceIO] Port [{port}] Has Stopped Broadcasting..")

                # Exit
                connected = False

    def _handle_server_udp(self, sock:socket.socket, address:str, tickrate: int or float=0.001) -> None:
        '''

        :param sock: Socket Object.
        :param address: Address Coupling of IP & Port.
        :return: Nothing!

        Binds UDP Socket to an Address and Listens to All Communication through Port - Used Via Threading.
        '''

        # Setup
        thread_id = int(threading.current_thread().name[8])

        # Get Color
        port = address[1]
        for item in (list(self.datasheet['servers'].values())):

            ds_port, _, remark, color, _, _ = item.values()
            if ds_port == port:
                break

        # Try to Connect to endpoint..
        connected = False
        a = time()
        while not connected and self.sess.value:

            # Try to Establish Connection..
            try:
                sock.connect(address)
                connected = True

            except:
                print("@!CANT CONNECT UDP!@")
                pass

        # Listen..
        while connected and self.sess.value:
            # sleep(tickrate) # PACE!
            sleep(tickrate)

            # Try to Receive Message..
            try:

                if not self.outputs[thread_id].empty():
                    packet = str(self.outputs[thread_id].get()).encode(self.codec)
                    sock.sendto(packet, address)

            except:
                # print("UDP send failed")
                pass

    def _handle_server_tcp(self, sock:socket.socket, address:str, tickrate: int or float=0.001):
        '''

        :param sock: Socket Object.
        :param address: Address Coupling of IP & Port.
        :return: Nothing!

        Binds TCP Socket to an Address and Listens to All Communication through Port - Used Via Threading.
        '''

        # Setup
        thread_id = int(threading.current_thread().name[8])

        # Get Color
        port = address[1]
        for item in (list(self.datasheet['servers'].values())):

            ds_port, _, _, color, *_ = item.values()
            if ds_port == port:
                break

        # Try to Connect to endpoint..
        connected = False
        while not connected and self.sess.value:
            # Try to Establish Connection..
            try:
                sock.connect(address)
                connected = True

            except:
                # print("@!CANT CONNECT TCP!@")
                pass

        # Listen..
        while connected and self.sess.value:
            sleep(tickrate) # PACE!

            # Try to Receive Message..
            try:

                if not self.outputs[thread_id].empty():
                    packet = str(self.outputs[thread_id].get()).encode(self.codec)
                    sock.sendall(packet)

            except:
                print("TCP send failed")
                pass

    # Dunders --------------------------------------------------------------------------------------------------------
    def __enter__(self) -> None:
        '''

        :return: Nothing!

        Become Session Ready. Initial Socket Opening & Thread Assigning,
         to be recalled in the main Session Loop as a Reboot Method Between Sessions.
        '''
        print('[InterfaceIO] Starting Session..')
        print("[InterfaceIO] Preparing Communicators..")
        # Get Communicators from Datasheet..
        input_communicators_ds = list(self.datasheet['clients'].values()) # Input
        input_sockets = []
        input_uarts = []
        for com in input_communicators_ds:

            # Append to correct List
            match com['protocol']:

                case 'TCP' | "UDP":
                    input_sockets.append(com)

                case 'UART':
                    input_uarts.append(com)

        output_communicators_ds = list(self.datasheet['servers'].values()) # Output
        output_sockets = []
        output_uarts = []
        for com in output_communicators_ds:

            # Append to correct List
            match com['protocol']:

                case 'TCP' | "UDP":
                    output_sockets.append(com)

                case 'UART':
                    output_uarts.append(com)

        # Open Sockets for Communication..
        self._iterate_open_sock(input_sockets, category='clients')
        self._iterate_open_sock(output_sockets, category='servers')

        # Sort Sockets into Clients & Servers
        client_socks = self.open_sockets['clients'].copy()
        servers = self.open_sockets['servers'].copy()

        # Combine UART and Sockets According to Datasheet order
        clients = []
        for com in input_communicators_ds:

            # Append to correct List
            match com['protocol']:

                case 'TCP' | "UDP":
                    clients.append(client_socks.pop(0))

                case 'UART':
                    clients.append((input_uarts.pop(0),None))

        print("[InterfaceIO] Sending Handlers to Threads..")
        # Start Clients
        if clients:

            for i,(client,address) in enumerate(clients):

                match type(client):

                    # Socket Type
                    case socket.socket:
                        func = self._handle_client_udp if client.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == 2 else self._handle_client_tcp
                        args = (client,address)
                        self.clients.append((threading.Thread(target=func, args=args, daemon=True, name=f'Thread #{i}-{func.__name__}'), client))

                    # Dictionary (UART!) Type
                    case dict:
                        func = self._handle_client_uart
                        port, _, _, color, baudrate, packet_size, flag, tickrate = client.values()
                        args = (port, baudrate, flag, packet_size, tickrate, color)
                        self.clients.append((threading.Thread(target=func, args=args, daemon=True, name=f'Thread #{i}-{func.__name__}'), None))

        # Start Servers
        if servers:
            for i,(server,address) in enumerate(servers):

                func = self._handle_server_udp if server.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == 2 else self._handle_server_tcp
                port, _, _, color, _, tickrate = output_communicators_ds[i].values()
                args = (server, address, tickrate)
                self.servers.append((threading.Thread(target=func, args=args, daemon=True, name=f'Thread #{i}-{func.__name__}'), server))


        print(f"[InterfaceIO] Ready for Session!")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        if self.clients + self.servers:
            for worker in self.clients + self.servers:

                while worker[0].is_alive():
                    sleep(0.1)

                if worker[1]:
                    worker[1].close()


        pass

class Interface_Brain:
    '''
    The Interface Brain Serves as an Interface Component Whose purpose is to look
    inside the Queues of the Clients, Read, Parse, and Link The Parsed data to Outward
    Ports. In Addition, the Interface will be in charge of Writing the Data to the
    Logging Database.
    '''
    reset = "\033[0m"

    # Initialize
    def __init__(self, sess_controller, run_no, inq, outq, writeq):

        # Params
        self.sess = sess_controller
        self.run_no = run_no
        self.inputs = inq
        self.outputs = outq
        self.write_queue = writeq
        self.threads = []

    def _link(origin: int, destination: int or list, dblink: bool=False) -> None:
        '''

        :param destination: Destination Server Index in the Spec Sheet
               origin: Destination Client Index in the Spec Sheet
        :return: Nothing!

        A Decorator that Decorates Parsing Pipes to link between
        Origin Communicator Index and Destination Communicator Index.
        The Input Packet can be Accessed by pointing to args[0]

        '''

        def outer(func):
            def inner(self, *args, **kwargs):
                # _ = origin,destination

                # Session Controller
                while self.sess:

                    # Pull Parse Push
                    if not self.inputs[origin].empty():
                        packet = (self.inputs[origin].get(),) # Pull
                        parsed,towrite = func(self, *packet+args, **kwargs) # Parse

                        # Push Parsed
                        match destination:

                            case None:
                                pass

                            case int():
                                self.outputs[destination].put(parsed) # Push

                            case list():
                                for sp,sd in zip(parsed,destination): # S - Single | P - Parsed | D - Destination
                                    self.outputs[sd].put(sp)

                        # Write
                        if towrite and dblink:
                            self.write_queue.put(towrite)

            return inner
        return outer


    @_link(origin=0, destination=0)
    def foo(self, *args):
        '''
        Example Basic Pipeline
        '''
        # Example..
        result = args[0]+" And ive been proccessed"

        return result,[]

    @_link(origin=1, destination=[1,2], dblink=True)
    def bar(self, *args) -> tuple[list,list]:
        '''
        Example Multi output Pipeline With DB Writing Enabled
        '''

        # Example Results
        result1 = args[0] + " And ive been proccessed too!! (1)"
        result2 = args[0] + " And ive been proccessed too!! (2)"

        # Example Result JSONs for DB Write - Requires Config[logging] = True!!
        result1_json = None # Appropriate JSONification of result1
        result2_json = None # Appropriate JSONification of result2

        return [result1, result2],[result1_json,result2_json]

    def work(self) -> None:
        '''

        :return: Nothing!

        This Function is The InterfaceBrain Main Body, this is the main
        Session Loop where all the Pipes are executed by Using Threads.
        '''

        while True:

            # If Session Started..
            if self.sess.value:

                # Worker Threads Assignment
                self.threads.append(threading.Thread(target=self.foo, args=(), daemon=True, name='Thread #1 - {foo}'))
                self.threads.append(threading.Thread(target=self.bar, args=(), daemon=True, name='Thread #1 - {bar}'))

                # Start Worker Threads
                for thread in self.threads:
                    thread.start()

                # Session Loop
                while self.sess.value:
                    sleep(0.01)

                # Clear
                self.threads = []

            sleep(0.1)

    def __enter__(self):
        pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class Keyboard_Handler:
    '''
    Class to Define all Keeb Related Functionality
    '''

    def __init__(self, sess_controller, online_controller):
        self.sess = sess_controller
        self.online = online_controller

    def keyhit(self, event) -> None:
        '''

        :param event: Event Hook
        :return: Nothing!
        Responsible for Handling Inputs/Outputs of the Keyboard.
        '''

        if event.name.lower() == 's':
            print(f"[KeebHandler] Updating Session Status! [{'ON' if self.sess.value else 'OFF'} -> {'OFF' if self.sess.value else 'ON'}]")
            self.sess.value = not self.sess.value


        if event.name.lower() == 'q':
            print('[KeebHandler] Quitting Interface!')
            keyboard.unhook_all()
            self.online.value = False

class Interface_App:
    '''
    Master Interface Class which is in Charge of Synchronizing, and controlling
    Every Component under it.
    '''

    # Initialize
    def __init__(self):

        # Port DataSheet
        with open('Communication.yaml', 'r') as yamlf:
            self.datasheet = yaml.safe_load(yamlf)

        # Interface States
        self.sess = mp.Value('b', False)
        self.online = mp.Value('b', True)
        self.run_no = mp.Value('i', 0) # 0 unassigned run number
        self.interface_server_ip = socket.gethostbyname(socket.gethostname())
        self.endpoint1 ,self.endpoint2 ,self.endpoint3 = self.datasheet['settings']['hosts'].values()
        self.logging = self.datasheet['settings']['logging']
        # sys.setswitchinterval(0.002)

        # Keyboard Handling
        self.keeb_handler = Keyboard_Handler(sess_controller=self.sess, online_controller=self.online)

        # Datasheet
        self.client_count = len(self.datasheet['clients'].keys())
        self.server_count = len(self.datasheet['servers'].keys())

    def _operate_io(self, obj) -> None:
        '''

        :param obj: InterfaceIO Class
        :return: Nothing!

        The Functions Entire Purpose is to live on a core, and fulfill
        InterfaceIO's Purpose of Serving as an Input Output Component.
        Every Open Connection Has a Queue where it Puts, Pushes information
        to and from appropriately to whether its a Server or a Client Destination.
        '''

        with obj(sess_controller=self.sess, inq=self.inputs, outq=self.outputs, endpoint1=self.endpoint1, endpoint2=self.endpoint2, endpoint3=self.endpoint3) as io:
            io.work()

    def _operate_brain(self, obj) -> None:
        '''

        :param obj: InterfaceBrain Class
        :return: Nothing!

        The Functions Entire Purpose is to live on a core, and fulfill
        InterfaceBrain's Purpose of Serving as a Parser which Pulls and Puts
        Information in chosen Queues of Clients and Server Destinations Appropriately.
        '''

        with obj(sess_controller=self.sess, run_no=self.run_no, inq=self.inputs, outq=self.outputs, writeq=self.writes) as brain:
            brain.work()

    def _operate_db(self, obj):

        with obj(sess_controller=self.sess, run_no=self.run_no, write_queue=self.writes) as dbhandler:
            dbhandler.work()

    def start(self) -> None:
        '''

        :return: Nothing!
        The Functions Entire Purpose is to Get the Interface going,
        it sets interface state to online, sets up Queues,
        and Sends Components To Cores.
        '''


        print('[InterfaceApp] Starting Application..')
        keyboard.on_press(self.keeb_handler.keyhit)
        self.online.value = True

        # Start Processes With Manager
        with mp.Manager() as manager:

            # Queues
            self.inputs = [manager.Queue() for _ in range(self.client_count)]
            self.outputs = [manager.Queue() for _ in range(self.server_count)]
            self.writes = manager.Queue()

            # Create Processes
            io = mp.Process(target=self._operate_io, args=(Interface_IO,))
            brain = mp.Process(target=self._operate_brain, args=(Interface_Brain,))

            # Create Conditional Processes
            if self.logging:
                db_handler = mp.Process(target=self._operate_db, args=(DBHandler,))

            # Start Processes
            io.start()
            brain.start()

            # Start Conditional Processes
            if self.logging:
                db_handler.start()

            # Interface Loop
            print('[InterfaceApp] Application Running!')
            while self.online.value:
                sleep(0.01)

            print('[InterfaceApp] Closing Application..')
            # Close Processes
            io.terminate()
            brain.terminate()

            # Close Conditional Processes
            if self.logging:
                db_handler.terminate()

            print('[InterfaceApp] Done Closing..')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == '__main__':


    # Session Shared Variable as Controller
    with Interface_App() as interface:

        interface.start()
        pass

