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

def dist(a,b):
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)

def xzdist(a,b):
    return dist((a[0],a[2]),(b[0],b[2]))

class TerraformBot(CraftBot):

    def on_you(self, id, position):
        self.material = 3
        self.clear_memo()
        self.talk("Terraformbot ready for action.")        

    def get_neighbors(self,x,y,z, xz=False, xy=False, yz=False):
        # warning memoziation breaks if you try to mix fixed-plane and full neighbor functions!
        if (x,y,z) in self.NEIGHBORS_MEMO:
            return self.NEIGHBORS_MEMO[(x,y,z)]

        n = [(x+1,y,z), (x-1,y,z), (x,y+1,z), (x,y-1,z), (x,y,z+1),(x,y,z-1),
                            (x+1,y+1,z),(x+1,y-1,z),(x-1,y+1,z),(x-1,y-1,z), 
                           (x+1,y,z+1),(x+1,y,z-1),(x-1,y,z+1),(x-1,y,z-1),
                           (x,y+1,z+1),(x,y+1,z-1),(x,y-1,z+1),(x,y-1,z-1)]
        if(xz):
            n =  [(px,py,pz) for (px,py,pz) in n if py == y]
        if(xy):
            n =  [(px,py,pz) for (px,py,pz) in n if pz == z]
        if(yz):
            n =  [(px,py,pz) for (px,py,pz) in n if px == x]

        self.NEIGHBORS_MEMO[(x,y,z)] = n
        return n

    def flood(self, x,y,z,xz=False,xy=False,yz=False):
        self.clear_memo()
        block_type = self.get_block(x,y,z)
        if block_type == 0:
            return set()
        fill_blocks = set()
        stack = [(x,y,z)]
        while stack:
            point = stack.pop()
            fill_blocks.add(point)
            n = [x for x in self.get_neighbors(*point, xz=xz,yz=yz,xy=xy) if (x not in fill_blocks) and (self.get_block(*x) == block_type)]
            stack.extend(n)
        return fill_blocks

    def clear_memo(self):
        self.TRAP_MEMO = {}
        self.NEIGHBORS_MEMO = {}

    def terraform_flood(self, x,y,z,radius,plants=False):
        self.clear_memo()
        if plants:
            empty_blocks = set(PLANTS.keys() + [0])
        else:
            empty_blocks = set([0])

        # Start block
        block_type = self.get_block(x,y,z)
        
        # Simplest case
        if block_type == 0:
            return set()

        fill_blocks = set()

        # Seed stack with start block
        stack = [(x,y,z)]

        def is_trapped(x,y,z):
            if (x,y,z) in self.TRAP_MEMO:
                return self.TRAP_MEMO[(x,y,z)]
            neighbors = self.get_neighbors(x,y,z)
            trapped = not any(map(lambda x : self.get_block(*x) in empty_blocks, neighbors))
            self.TRAP_MEMO[(x,y,z)] = trapped
            return trapped

        while stack:
            # Block to examine
            point = stack.pop()
            fill_blocks.add(point)

            neighbors = self.get_neighbors(*point)
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
        elif cmd == 'fillxz':
            self.remove_sign(x,y,z,face)
            self.do_fillxz(x,y,z)
        elif cmd == 'material':
            self.remove_sign(x,y,z,face)
            self.talk('is setting material to %s' % MATERIALS.get(block_type, block_type))
            self.material = block_type

    def find_ground(self, x,y,z):
        for y in range(y,0,-1):
            bt = self.get_block(x,y,z)
            if bt not in (0,16,17,18,19,20,21,22,23):
                return x,y,z

    def do_terraform(self, x,y,z, radius, material_map):
            self.clear_memo()
            self.talk('is calculating a terraform...')
            blocks = self.terraform_flood(x,y,z,radius,plants=True)
            self.talk('is terraforming...')
            for x,y,z in blocks:
                type = self.get_block(x,y,z)
                if type in material_map:
                    material = material_map[type]
                    self.remove_block(x,y,z)
                    if material != 0:
                        self.add_block(x,y,z,material, check=False)
            self.talk('is done.  Processed %s blocks.' % len(blocks))

    def do_fillxz(self, x,y,z):
        self.clear_memo()
        self.talk('is calculating a fill...')
        blocks = self.flood(x,y,z, xz=True)
        for x,y,z in blocks:
            self.remove_block(x,y,z)
            self.add_block(x,y,z,self.material, check=False)
        self.talk('is done.  Processed %s blocks.' % len(blocks))


import sys

bot = TerraformBot(host=sys.argv[1])
bot.run()
