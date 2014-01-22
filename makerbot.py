from craftbot import CraftBot
from numpy import array,round as around

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
def sphere(cx, cy, cz, r, fill=False, fx=False, fy=False, fz=False):
    result = set()
    for x in range(cx - r, cx + r + 1):
        if fx and x != cx:
            continue
        for y in range(cy - r, cy + r + 1):
            # if y < cy:
            #     continue # top hemisphere only
            if fy and y != cy:
                continue
            for z in range(cz - r, cz + r + 1):
                if fz and z != cz:
                    continue
                inside = False
                outside = fill
                for dx, dy, dz in OFFSETS:
                    ox, oy, oz = x + dx, y + dy, z + dz
                    d2 = (ox - cx) ** 2 + (oy - cy) ** 2 + (oz - cz) ** 2
                    d = d2 ** 0.5
                    if d < r:
                        inside = True
                    else:
                        outside = True
                if inside and outside:
                    result.add((x, y, z))
    return result

def line(a,b):
    a = array(a).astype(float)
    b = array(b).astype(float)
    d = b-a
    N = int(max(abs(d)))
    s = d/N
    print "a: ", a
    print "b: ", b
    print "d: ", d
    print "N: ", N
    print "s: ", s
    rnd = lambda r : tuple(around(r).astype(int))
    retval = [rnd(a)]
    for i in range(N):
        a = a+s
        retval.append(rnd(a))
    return retval

def polyline(points, closed=False):
    if len(points) <2:
        return []

    if closed:
        if points[-1] != points[0]:
            points.append(points[0])

    retval = []
    for i in range(len(points)-1):
        retval.extend(line(points[i], points[i+1]))

    return retval

def neighbors(x,y,z, xz=False, xy=False, yz=False):
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

class MakerBot(CraftBot):

    def on_you(self, id, position):
        self.material = 3
        self.signs = []
        self.walls = []
        self.blockflood = set()

    def flood(self, x,y,z,xz=False,xy=False,yz=False):
        block_type = self.get_block(x,y,z)
        if block_type == 0:
            return set()
        fill_blocks = set()
        stack = [(x,y,z)]
        while stack:
            point = stack.pop()
            fill_blocks.add(point)
            n = [x for x in neighbors(*point, xz=xz,yz=yz,xy=xy) if (x not in fill_blocks) and (self.get_block(*x) == block_type)]
            stack.extend(n)

        print "flooding %d blocks" % len(fill_blocks)
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
        if cmd == 'sphere':
            self.remove_sign(x,y,z,face)
            r = int(args[1])
            fill = 'fill' in args
            do_sphere(x,y,z,block_type,r,fill)
        elif cmd == 'build':
            try:
                p = args[1]
            except IndexError:
                p = None
            if p == 'start':
                for sign in self.signs:
                    self.remove_sign(*sign)
                self.talk('is starting a build at %s' % str((x,y,z)))
                self.walls = [(x,y,z)]
                self.signs = [(x,y,z,face)]
                try:
                    self.height = int(args[2])
                except:
                    self.height = 1
            elif p == 'finish':
                self.walls.append((x,y,z))
                self.signs.append((x,y,z,face))
                self.talk('is finishing build with %d points' % len(self.walls))
                self.do_building()
            else:
                self.talk('is continuing build at %s' % str((x,y,z)))
                self.walls.append((x,y,z))
                self.signs.append((x,y,z,face))
        elif cmd == 'column':
            try:
                height = int(args[1])
            except:
                self.talk('Column command needs a numeric argument')
                return
            do_column(self, x,y,z, height)
        elif cmd == '-column':
            print 'removing column'
            blocks_to_remove = []
            while True:
                block_type = self.get_block(x,y,z)
                if block_type == 0:
                    break
                else:
                    blocks_to_remove.append((x,y,z))
                y += 1
            print len(blocks_to_remove)
            for block in blocks_to_remove:
                self.remove_block(*block)
        elif cmd == 'goto':
            try:
                x,z = map(int,args[1:])
            except:
                self.talk('goto command requires 2 numeric arguments')
            x,y,z = self.find_ground(x,200,z)
            self.talk('is going to %d,%d' % (x,z))
            self.move_player(x,y+2,z)

        elif cmd == 'acid':
            self.remove_sign(x,y,z,face)
            block_type = self.get_block(x,y,z)
            self.talk('is destroying a structure of block type %s' % block_type)
            blocks = self.flood(x,y,z)
            for b in blocks:
                self.remove_block(*b)

        elif cmd == 'fill':
            print "filling up!"
            self.remove_sign(x,y,z,face)
            blocks = self.flood(x,y,z)
            for x,y,z in blocks:
                self.remove_block(x,y,z)
                self.add_block(x,y,z,self.material, check=False)

        elif cmd == 'fillxz':
            self.remove_sign(x,y,z,face)
            blocks = self.flood(x,y,z, xz=True)
            for x,y,z in blocks:
                self.remove_block(x,y,z)
                self.add_block(x,y,z,self.material, check=False)

        elif cmd == 'material':
            self.remove_sign(x,y,z,face)
            self.talk('is setting material to %d' % block_type)
            self.material = block_type

        elif cmd == 'test':
            self.remove_sign(x,y,z,face)
            self.talk(face)

        elif cmd == 'excavate':
            try:
                radius = int(args[1])
                depth = int(args[2])
            except:
                return

            self.remove_sign(x,y,z,face)
            blocks = set()
            if face == 6:
                for i in range(depth):
                    blocks.update(sphere(x,y+i,z,5,fill=True,fy=True))
            elif face in (2,3):
                s = {2:1,3:-1}
                for i in range(depth):
                    blocks.update(sphere(x,y,z+i*s[face],radius,fill=True,fz=True))
            elif face in (0,1):
                s = {1:1,0:-1}
                for i in range(depth):
                    blocks.update(sphere(x+i*s[face],y,z,radius,fill=True,fx=True))

            self.talk('is cuttin %s blocks DEAL WITH IT' % len(blocks))
            for x,y,z in blocks:
                self.remove_block(x,y,z)
                #self.add_block(x,y,z,self.material, check=False)

    def do_sphere(self, x,y,z, type, r, fill=False):
            blocks = sphere(x,y,z,r,fill=fill)
            if type != 0:
                for x,y,z in blocks:
                    self.add_block(x,y,z,block_type)

    def do_column(self,x,y,z,height):
        #x,y,z = find_ground(x,y+1,z)
        blocks = []
        for y in range(y+1,y+height+1):
            blocks.append((x,y,z))
        for x,y,z in blocks:
            self.add_block(x,y,z,self.material)

    def do_building(self):
        # Clear all the markers used to indicate the walls
        for sign in self.signs:
            self.remove_sign(*sign)

        # Calculate wall boundaries in 3d
        points = polyline(self.walls, closed=True)

        # Determine the ultimate height of the building
        height = max([y for x,y,z in points]) + self.height

        # Derive the foundation of the building from the wall path
        base = [self.find_ground(x,height+1,z) for x,y,z in points]    

        # Generate the blocks that will form the walls
        blocks = []
        for x,y,z in base:
            for y in range(y,height):
                blocks.append((x,y,z))

        self.talk('is building a structure of %d blocks.' % len(blocks))
        # Commit them to the universe
        for x,y,z in blocks:
            self.move_player(x,y+1.5,z, 3.1415/2)
            self.add_block(x,y,z,type=self.material)

    def find_ground(self, x,y,z):
        for y in range(y,0,-1):
            bt = self.get_block(x,y,z)
            if bt not in (0,16,17,18,19,20,21,22,23):
                return x,y,z


import sys

bot = MakerBot(host=sys.argv[1])
bot.run()
