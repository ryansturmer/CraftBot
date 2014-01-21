from craftbot import CraftBot, PLANTS, MATERIALS
from numpy import array,round as around
import math

OFFSETS = [
    (-0.5, -0.5, -0.5),
    (-0.5, -0.5, 0.5),
    (-0.5, 0.5, -0.5),
    (-0.5, 0.5, 0.5),
    (0.5, -0.5, -0.5),
    (0.5, -0.5, 0.5),
    (0.5, 0.5, -0.5),
    (0.5, 0.5, 0.5),
]

CRAFT_USER = 'ryansturmer'

def get_neighbors(x,y,z, xz=False, xy=False, yz=False):
    n = [(x+1,y,z), (x-1,y,z), (x,y+1,z), (x,y-1,z), (x,y,z+1),(x,y,z-1),
                        (x+1,y+1,z),(x+1,y-1,z),(x-1,y+1,z),(x-1,y-1,z), 
                       (x+1,y,z+1),(x+1,y,z-1),(x-1,y,z+1),(x-1,y,z-1),
                       (x,y+1,z+1),(x,y+1,z-1),(x,y-1,z+1),(x,y-1,z-1)]
    if(xz):
        return [(px,py,pz) for (px,py,pz) in n if py == y]
    if(xy):
        return [(px,py,pz) for (px,py,pz) in n if pz == z]
    if(yz):
        return [(px,py,pz) for (px,py,pz) in n if px == x]
    
    return n

def dist(a,b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)

def xzdist(a,b):
    return dist((a[0],a[2]),(b[0],b[2]))

class TerraformBot(CraftBot):

    def on_you(self, id, position):
        self.material = 3
        self.signs = []
        self.walls = []
        self.blockflood = set()

    def terraform_flood(self, x,y,z,radius):
        empty_blocks = PLANTS.keys() + [0]

        # Start block
        block_type = self.get_block(x,y,z)
        
        # Simplest case
        if block_type == 0:
            return set()

        fill_blocks = set()

        # Seed stack with start block
        stack = [(x,y,z)]

        def is_trapped(x,y,z):
            neighbors = get_neighbors(x,y,z)
            return not any(map(lambda x : self.get_block(*x) in empty_blocks, neighbors))

        while stack:
            # Block to examine
            point = stack.pop()
            fill_blocks.add(point)

            neighbors = get_neighbors(*point)
            for neighbor in neighbors:
                if neighbor not in fill_blocks and not is_trapped(*neighbor) and xzdist(neighbor, (x,y,z)) <= radius and self.get_block(*neighbor) != 0:
                    stack.append(neighbor)

        return fill_blocks

    def on_talk(self, text):
        if text.startswith(CRAFT_USER + '>'):
            text = text.lstrip(CRAFT_USER + '>').strip().lower()
            if text.startswith('craftbot'):
                text = text.lstrip('craftbot').strip().replace(',',' ')
                args = text.split()
                cmd = args[0]            
                if cmd == 'goto':
                    try:
                        x,z = map(int,args[1:])
                    except Exception, e:
                        self.talk('goto command requires 2 numeric arguments')
                        print e
                        return
                    x,y,z = self.find_ground(x,200,z)
                    self.talk('moving player to %d,%d' % (x,z))
                    self.move_player(x,y+2,z)        

                    
    def on_sign(self, x,y,z,face,text):
        print "SIGN: %s,%s,%s,%s,%s" % (x,y,z,face,text)
        args = text.lower().split()
        cmd = args[0]
        block_type = self.get_block(x,y,z)
        if cmd == 'snow':
            self.remove_sign(x,y,z,face)
            radius = int(args[1])
            self.do_terraform(x,y,z,radius,{1:9,7:60,2:61,17:0,18:22,19:22,20:22,21:22,23:22,15:60})
        if cmd == 'lake':
            self.remove_sign(x,y,z,face)
            radius = int(args[1])
            self.do_terraform(x,y,z,radius,{1:7,2:56,5:0,15:0,19:18,20:18,21:18,22:18,23:18})

    def find_ground(self, x,y,z):
        for y in range(y,0,-1):
            bt = self.get_block(x,y,z)
            if bt not in (0,16,17,18,19,20,21,22,23):
                return x,y,z

    def do_terraform(self, x,y,z, radius, material_map):
            self.talk('is calculating a terraform...')
            blocks = self.terraform_flood(x,y,z,radius)
            self.talk('is terraforming...')
            for x,y,z in blocks:
                type = self.get_block(x,y,z)
                if type in material_map:
                    material = material_map[type]
                    self.remove_block(x,y,z)
                    if material != 0:
                        self.add_block(x,y,z,material, check=False)
            self.talk('is done.')
import sys

bot = TerraformBot(host=sys.argv[1])
bot.run()
