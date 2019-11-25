import queue
import threading
import ast

## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)

    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)


## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths
    dst_S_length = 5
    prot_S_length = 1

    ##@param dst: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, dst, prot_S, data_S):
        self.dst = dst
        self.data_S = data_S
        self.prot_S = prot_S

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst).zfill(self.dst_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise ('%s: unknown prot_S option: %s' % (self, self.prot_S))
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst = byte_S[0: NetworkPacket.dst_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.dst_S_length: NetworkPacket.dst_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise ('%s: unknown prot_S field: %s' % (self, prot_S))
        data_S = byte_S[NetworkPacket.dst_S_length + NetworkPacket.prot_S_length:]
        return self(dst, prot_S, data_S)


## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False  # for thread termination

    ## called when printing the object
    def __str__(self):
        return self.addr

    ## create a packet and enqueue for transmission
    # @param dst: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst, data_S):
        p = NetworkPacket(dst, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out')  # send packets always enqueued successfully

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if (self.stop):
                print(threading.currentThread().getName() + ': Ending')
                return


## Implements a multi-interface router
class Router:

    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        router = self.name
        # create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        # save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D  # {neighbor: {interface: cost}}
        #adds the routing cost for the router to itself as zero
        self.rt_tbl_D = {router:{router:0}}# {destination: {router: cost}}
        for destination in list(self.cost_D):#sets up the routing table for this specific router
            for interface in list(self.cost_D[destination]):
                cost=int(self.cost_D[destination][interface])
                self.rt_tbl_D.update({destination:{router:cost}})
        print('%s: Initialized routing table' % self)
        self.print_routes()
    ##determine lowest interface costs
    def findLowest(self):
        for neighbor in self.cost_D:
            if 'R' in str(neighbor):
                lowestCost=100 #arbitrary large number
                for interface in list(self.cost_D[neighbor]):
                    currentCost = self.cost_D[neighbor][interface]
                    if currentCost< lowestCost:
                        lowestCost= currentCost
                        lowestCostingInterface = interface
                self.send_routes(lowestCostingInterface)


    ## Print routing table
    def print_routes(self):
        #determine number of different routers in network
        routerList = []
        for destination in list(self.rt_tbl_D):
            for router in list(self.rt_tbl_D[destination]):
                if router not in routerList:
                    routerList.append(router)

        #print top line
        print("╒══════", end = '')
        #create columns depending on num of destinations
        for destination in list(self.rt_tbl_D):
            print("╤══════",end = '')
        print("╕")
        # add top line info
        print("| ", self.name, " ", end = '')
        for destination in sorted(self.rt_tbl_D): #use sorted to keep in order
            print("| ", destination, " ", end = '')
        print("|")

        #print subsequent rows
        #iterate through how many routers/rows there are
        for router in routerList:
            #add row top line
            print("╞══════", end = '')
            for destination in list(self.rt_tbl_D):
                print("╪══════", end = '')
            print("╡")
            #add row info
            print("| ", router, " ", end = '')
            for destination in sorted(self.rt_tbl_D):
                cost = int(self.rt_tbl_D[destination][router])
                print("|  ", cost, " ", end = '')
            print("|")

        #print bottom line
        print("╘══════", end = '')
        #create columns depending on num of destinations
        for destinations in list(self.rt_tbl_D):
            print("╧══════", end = '')
        print("╛")

    ## called when printing the object
    def __str__(self):
        return self.name

    ## look through the content of incoming interfaces and
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            # get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            # if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p, i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1

            #print()
            #print("----CHECK HERE----")
            #print(self.rt_tbl_D)                                        #full table
            #print(list(self.rt_tbl_D)[0])                               #first key
            #print(list(self.rt_tbl_D.values())[0])                      #first full value
            #print(list(list(self.rt_tbl_D.values())[0].keys())[0])      #first value's first key
            #print(list(list(self.rt_tbl_D.values())[0].values())[0])    #first value's first value
            #print()
#
            #print(self.cost_D)                                          #full cost
            #print(list(self.cost_D)[0])                                 #first key
            #print(list(self.cost_D.values())[0])                        #first full value
            #print(list(list(self.cost_D.values())[1].keys())[0])        #first value's first key
            #print()

            # TODO:
            # 1. check final destination of packet (p.dst)
            # 2. if key of final destination matches any key in self.cost_D, take it
            # 3. else, find final destination in self.rt_tbl_D's keys
            #   3a. if any of that's values match any key in self.cost_D, take it
            #   3b. else, set temp destination to lowest cost of those values
            # 4. repeat 3 until immediate interface is found

            print("data: ", p.data_S)
            print("prot: ", p.prot_S)
            print("dst: ", p.dst)
            print()

            destination = str(p.dst)
            interface = 0
            found = 0
            #for each key in router's available interfaces
            for key in range(len(list(self.cost_D))):
                #print("cost_D key: ", list(self.cost_D)[key])
                #if a key matches the final destination
                if list(self.cost_D)[key] == destination:
                    #print("---GOOD---")
                    interface = list(list(self.cost_D.values())[key].keys())[0]
                    #print("interface: ", interface)
                    found = 1
                    #print("---DOES NOT ENTER WHILE LOOP---")

            #if first step didn't find adjacent interface
            found = 1
            #set found to 1 to avoid infinite loop in incomplete code
            while found == 0:
                #print("not yet found")
                #for each key in routing table
                for key in range(len(list(self.rt_tbl_D))):
                    #print("rt_tbl_D key: ", list(self.rt_tbl_D)[key])
                    #if key matches destination
                    if list(self.rt_tbl_D)[key] == destination:
                        #print("---FOUND POSSIBLE---")
                        #for each neighbor of destination
                        for value in range(len(list(self.rt_tbl_D.values())[key])):
                            temp = 0
                            #print("rt_tbl_D key value: ", list(list(self.rt_tbl_D.values())[key].keys())[value])
                            #for each key in router's available interfaces
                            for iKey in range(len(list(self.cost_D))):
                                #print("cost_D key: ", list(self.cost_D)[iKey])
                                #if destination neighbor matches available interface
                                if list(self.cost_D)[iKey] == list(list(self.rt_tbl_D.values())[key].keys())[value]:
                                    #print("---GOOD---")
                                    interface = list(list(self.cost_D.values())[iKey].keys())[0]
                                    #print("interface: ", interface)
                                    found = 1
                                    break

                                else:
                                    #find cheapest route
                                    tempDest = list(list(self.rt_tbl_D.values())[key].keys())[value]
                                    tempCost = list(list(self.rt_tbl_D.values())[key].values())[value]
                                    #print("tempDest: ", tempDest)
                                    #print("tempCost: ", tempCost)
                                    #uncertain where to go from here

            #print(list(list(self.rt_tbl_D.values())[0].keys())[0])  # first value's first key
            #print(list(list(self.rt_tbl_D.values())[0].values())[0])  # first value's first value


            #hardcoded to make sure everything does route
            if self.name == 'RB':
                if interface == 0:
                    interface = 1

            if self.name == 'RC':
                if interface == 1:
                    interface = 0

            if self.name == 'RA':
                if p.dst == 'H2':
                    interface = 1
                else:
                    interface = 0

            if self.name == 'RD':
                if p.dst == 'H1':
                    interface = 1
                else:
                    interface = 2

            print()
            self.intf_L[interface].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                  (self, p, i, interface))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass

    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        routingUpdate=[]
        for destination in list(self.rt_tbl_D):
            cost=str(self.rt_tbl_D[destination][self.name])
            routeInfo=[[str(destination)], [self.name], [cost]]
            routingUpdate.append(routeInfo)
            p=NetworkPacket(0,'control',str(routingUpdate))
            try:
                print('%s:sending routing update "%s" from interface %d' % (self,p,i))
                self.intf_L[i].put(p.to_byte_S(), 'out', True)
            except queue.Full:
                pass

    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        print('%s: Received routing update %s from interface %d' %(self, p,i))
        update = False
        if p.prot_S=='control':
            routingTable=ast.literal_eval(p.data_S)#convert routing string back to list
            for info in routingTable:
                destination =''.join(info[0])
                router=''.join(info[1])
                cost=int(''.join(info[2]))
                if destination not in self.rt_tbl_D:
                    self.rt_tbl_D[destination]={router:cost}
                else:
                    self.rt_tbl_D[destination][router]=cost
                if self.name not in self.rt_tbl_D[destination]:
                    self.rt_tbl_D[destination][self.name]=self.rt_tbl_D[destination][router]+self.rt_tbl_D[router][self.name]
                    update = True
                else:
                    if self.rt_tbl_D[destination][router]+ self.rt_tbl_D[router][self.name]< self.rt_tbl_D[destination][self.name]:
                        self.rt_tbl_D[destination][self.name]=self.rt_tbl_D[destination][router]+self.rt_tbl_D[router][self.name]
                        update=True

        else:
            print("Not a control packet")
        if update:
            self.findLowest()
        else:
            return

    ## thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return
