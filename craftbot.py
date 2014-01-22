import socket, threading, select
from Queue import Queue, Empty
from world import World
from math import floor
import requests
import json

CHUNK_SIZE = 32
CREDENTIALS = {'USERNAME':'USER', 'IDENTITY_TOKEN':'TOKEN'}

try:
    with open('settings.json') as fp:
        CREDENTIALS = json.load(fp)
except Exception, e:
    print ('Loading settings.json failed: %s' % e)

MATERIALS = {   0: 'EMPTY', 
                1: 'GRASS', 
                2: 'SAND', 
                3: 'STONE', 
                4: 'BRICK', 
                5: 'WOOD', 
                6: 'CEMENT', 
                7: 'DIRT', 
                8: 'PLANK', 
                9: 'SNOW', 
                10: 'GLASS', 
                11: 'COBBLE', 
                12: 'LIGHT_STONE', 
                13: 'DARK_STONE', 
                14: 'CHEST', 
                15: 'LEAVES', 
                16: 'CLOUD', 
                17: 'TALL_GRASS',
                18: 'YELLOW_FLOWER', 
                19: 'RED_FLOWER', 
                20: 'PURPLE_FLOWER', 
                21: 'SUN_FLOWER', 
                22: 'WHITE_FLOWER', 
                23: 'BLUE_FLOWER', 
                32: 'COLOR_00', 
                33: 'COLOR_01', 
                34: 'COLOR_02', 
                35: 'COLOR_03', 
                36: 'COLOR_04', 
                37: 'COLOR_05', 
                38: 'COLOR_06', 
                39: 'COLOR_07', 
                40: 'COLOR_08', 
                41: 'COLOR_09', 
                42: 'COLOR_10', 
                43: 'COLOR_11', 
                44: 'COLOR_12', 
                45: 'COLOR_13', 
                46: 'COLOR_14', 
                47: 'COLOR_15', 
                48: 'COLOR_16', 
                49: 'COLOR_17', 
                50: 'COLOR_18', 
                51: 'COLOR_19', 
                52: 'COLOR_20', 
                53: 'COLOR_21', 
                54: 'COLOR_22', 
                55: 'COLOR_23', 
                56: 'COLOR_24', 
                57: 'COLOR_25', 
                58: 'COLOR_26', 
                59: 'COLOR_27', 
                60: 'COLOR_28', 
                61: 'COLOR_29', 
                62: 'COLOR_30', 
                63: 'COLOR_31'}

PLANTS = dict([(x,MATERIALS[x]) for x in range(17,24)])

class TwoWayDict(dict):
    def __init__(self, d={}):
        super(TwoWayDict, self).__init__()
        for key, value in d.items():
            self[key] = value
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        return int(dict.__len__(self) / 2)

MATERIALS = TwoWayDict(MATERIALS)
PLANTS = TwoWayDict(PLANTS) 

def material(x):
    return x if isinstance(x,int) else MATERIALS[x]


def thread(f):
    def run(*k, **kw):
        t = threading.Thread(target=f, args=k, kwargs=kw)
        t.setDaemon(True)
        t.start()
        return t
    return run

def chunked(x):
    return int(floor(round(x) / CHUNK_SIZE))

class Player(object):
    def __init__(self, id=None, nick=None, position=None):
        self.position = position or [0.0]*5
        self.id = id
        self.nick = nick
    def __repr__(self):
        return '<Player id=%s "%s">' % (self.id, self.nick)
    def __str__(self):
        return repr(self)

class CraftBot(object):
    def __init__(self, host='localhost', port=4080):
        self.lock = threading.RLock()
        self.host = host
        self.port = port
        self.input_buffer = ''
        self.handlers = {
            'T' : self.handle_talk,
            'K' : self.handle_key,
            'B' : self.handle_block,
            'C' : self.handle_chunk,
            'U' : self.handle_you,
            'P' : self.handle_position,
            'N' : self.handle_nick,
            'D' : self.handle_disconnect,
            'S' : self.handle_sign,
            'R' : self.handle_redraw
        }
        self.players = {}
        self.world = World()
        self.id = None
        self.queue = Queue()
        self.handler_queue = Queue()
        self.chunk_keys = {}


    # Commands the player can do
    def talk(self, text):
        self.queue.put('T,%s\n' % text)
    def add_block(self, x,y,z, type, check=True):
        existing_block = self.get_block(x,y,z)
        if not check or not existing_block:
            self.queue.put('B,%d,%d,%d,%d\n' % (x,y,z,type))
    def remove_block(self, x,y,z):
        self.queue.put('B,%d,%d,%d,%d\n' % (x,y,z,0))   
    def get_block(self,x,y,z):
        p,q = chunked(x),chunked(z)
        if (p,q) not in self.world.cache:
            self.request_chunk(p,q)
            '''
            self.request_chunk(p-1,q)
            self.request_chunk(p+1,q)
            self.request_chunk(p,q-1)
            self.request_chunk(p,q+1)
            self.request_chunk(p+1,q-1)
            self.request_chunk(p+1,q+1)
            self.request_chunk(p-1,q+1)
            self.request_chunk(p-1,q-1)
            '''
            while (p,q) not in self.chunk_keys:
                pass
        return self.world.get_chunk(p,q).get((x,y,z),0)
    def add_sign(self, x,y,z, face, text):
        self.queue.put('S,%d,%d,%d,%d,%s\n' % (x,y,z,face,text))
    def remove_sign(self, x,y,z, face):
        self.add_sign(x,y,z,face,'')
    def move_player(self, x=None,y=None,z=None, rx=None, ry=None):
        x = x or self.player.position[0]
        y = y or self.player.position[1]
        z = z or self.player.position[2]
        rx = rx or self.player.position[3]
        ry = ry or self.player.position[4]
        self.queue.put('P,%d,%d,%d,%d,%d\n' % (x,y,z,rx,ry))
    def get_player(self, nick):
        for player in self.players.items():
            if player.id == nick or player.nick == nick:
                return player
            return self.players[nickname]
    def request_chunk(self, p,q):
        print "requesting chunk"
        key = self.chunk_keys.get((p,q),0)
        self.queue.put('C,%d,%d,%d\n' % (p,q,key))

    @property
    def ready(self):
        return self.player != None

    def authenticate(self, username, identity_token):
        url = 'https://craft.michaelfogleman.com/api/1/identity'
        payload = {
            'username': username,
            'identity_token': identity_token,
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200 and response.text.isalnum():
            access_token = response.text
            self.queue.put('A,%s,%s\n' % (username, access_token))
        else:
            raise Exception('Failed to authenticate.')
    @property
    def player(self):
        return self.players.get(self.id, None)

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.setblocking(0)

    def handle_command(self, command):
        args = command.strip().split(',')
        if args:
            cmd = args[0]
            handler = self.handlers.get(cmd, self.handle_unhandled)
            callback, args = handler(*args)
            self.handler_queue.put((callback,args))

    def handle_talk(self, *args):
        return self.on_talk, (args[1],)

    def handle_position(self, *args):
        id = int(args[1])
        x,y,z,rx,ry = map(float, args[2:])
        with self.lock:
            player = self.players.get(id, Player(id=id))
            player.position = (x,y,z,rx,ry)
            self.players[id] = player
        return self.on_position, (player,)

    def handle_nick(self, *args):
        id = int(args[1])
        nick = str(args[2])
        with self.lock:
            player = self.players.get(id, Player(id=id))
            player.nick = nick
            self.players[id] = player
        return self.on_nick, (player,)

    def handle_you(self, *args):
        id = int(args[1])
        position = map(float, args[2:])
        with self.lock:
            self.id = id
            player = self.players.get(id, Player(id=id))            
            player.position = position
        return self.on_you, (id,position)

    def handle_block(self, *args):
        p,q,x,y,z,type = map(int, args[1:])
        chunk = self.world.get_chunk(p,q)
        chunk[x,y,z] = type
        return self.on_block, (x,y,z,type)

    def handle_sign(self, *args):
        p,q,x,y,z,face = map(int, args[1:7])
        text = args[7]
        return self.on_sign, (x,y,z,face,text)

    def handle_key(self, *args):
        p,q,key = map(int, args[1:])
        self.chunk_keys[(p,q)] = key
        return self.on_key, (p,q,key)

    def handle_chunk(self, *args):
        p,q = map(int, args[1:])
        self.chunk_keys[(p,q)] = 0
        return self.on_chunk, (p,q)

    def handle_disconnect(self, *args):
        return self.on_disconnect, (int(args[1]),)

    def handle_unhandled(self, *args):
        print "Unhandled command: %s" % (str(args),)
        return self.on_unhandled, []

    def handle_redraw(self, *args):
        p,q = map(int, args[1:])
        return self.on_redraw, (p,q)

    def on_talk(self, text):
        pass
    def on_position(self, p):
        pass
    def on_nick(self, player):
        pass
    def on_you(self, id, position):
        pass
    def on_disconnect(self, id):
        pass
    def on_block(self, x,y,z,type):
        pass
    def on_sign(self, x,y,z,face,text):
        pass
    def on_key(self, p,q,key):
        pass
    def on_unhandled(self):
        pass
    def on_chunk(self, p, q):
        pass
    def on_redraw(self, p, q):
        pass

    @thread
    def handler_loop(self):
        while True:
            try:
                handler, args = self.handler_queue.get(False)
                handler(*args)
            except Empty:
                pass
            except Exception, e:
                print "Exception in player handler: ", e

    def run(self):
        self.connect()
        self.authenticate(CREDENTIALS['USERNAME'], CREDENTIALS['IDENTITY_TOKEN'])
        self.handler_loop()
        while True:
            readers, writers, errorers = select.select([self.socket], [self.socket], [self.socket], 60)
            # Deal with errors first
            for socket in errorers:
                # Deal with total existence failure
                pass

            # Inbound: Data coming from server
            for socket in readers:
                data = self.input_buffer + socket.recv(4096)
                lines = data.split('\n')
                if not lines[-1].endswith('\n'):
                    self.input_buffer = lines.pop(-1)
                for line in lines:
                    #print '<- %s' % line
                    self.handle_command(line)
                    
            # Outbound: Commands going to server
            for socket in writers:
                try:
                    command = self.queue.get(False)
                    #print '-> %s' % command,
                    socket.send(command)
                    self.queue.task_done()
                except Empty:
                    pass
                except Exception, e:
                    print e