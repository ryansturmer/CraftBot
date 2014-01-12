from craftbot import CraftBot, thread
import time, random
from math import pi

HEIGHT = 35
LENGTH = 10
NORTH,EAST,SOUTH,WEST = (0,1,2,3)

TALL_GRASS = 17
YELLOW_FLOWER = 18
RED_FLOWER = 19
PURPLE_FLOWER = 20
BLUE_FLOWER = 23
WHITE_FLOWER = 22

FOOD = {YELLOW_FLOWER:32, RED_FLOWER:43, BLUE_FLOWER:57, WHITE_FLOWER:61, PURPLE_FLOWER:42}
FACE = {NORTH: pi, SOUTH: 0, EAST: pi/2, WEST :3*pi/2}

SNAKE_USER = 'ryansturmer'

class SnakeBot(CraftBot):
    def __init__(self, *args, **kwargs):
        super(SnakeBot, self).__init__(*args, **kwargs)
        self.kill_flag = False
        self.snakes = []

    def on_talk(self, text):
        if text.startswith(SNAKE_USER + '>'):
            if text.lstrip(SNAKE_USER + '>').strip().lower() == 'kill snakes':
                self.kill_snakes()

    def on_sign(self, x,y,z,face,text):
        print "SIGN: %s,%s,%s,%s,%s" % (x,y,z,face,text)
        try:
            args = text.lower().split()
            cmd = args[0]
            if cmd == 'snake':
                self.remove_sign(x,y,z,face)
                try:
                    length = int(args[1])
                except:
                    length = 10
                self.snakes.append(self.snake(x,y,z,length, 33, player=len(self.snakes)==0))
        except Exception, e:
            print e

    def kill_snakes(self):
        self.kill_flag = True
        while self.snakes:
            any_alive = False
            for snake in self.snakes:
                if snake.is_alive():
                    any_alive = True
            if not any_alive:
                break
        self.kill_flag = False
        self.snakes = []

    @thread
    def snake(self, x,y, z, length, material, player=False):
        # Calculate a start location.  The first free space on above ground at (X,Z)
        for y in range(y, 256):
            block = self.get_block(x,y,z)
            if block == 0:
                hx,hy,hz = (x,y,z)
                break
            
        blocks = []
        direction = NORTH
        try:
            while True:

                # Change directions at random
                if random.random() < 0.025:
                    direction = (direction + 1)%4
                
                # Remove the tail block
                if len(blocks) == length:
                    block = blocks.pop(0)
                    if block not in blocks:
                        self.remove_block(*block)

                # Add the head block
                blocks.append((hx,hy,hz))
                self.add_block(hx,hy,hz,material)

                # Move the rider
                if len(blocks) > 1:
                    px,py,pz = blocks[-2]
                    if player:
                        self.move_player(x=px,y=py+1,z=pz,rx=FACE[direction])
                
                # Compute the next head block
                stuck = True
                next_locs = [(hx,hy,hz+1),(hx+1,hy,hz),(hx,hy,hz-1),(hx-1,hy,hz)]
                for d in (direction, (direction + 1) % 4, (direction-1) %4):
                    next_loc = next_locs[d]                
                    block = self.get_block(*next_loc)

                    if block in (0,TALL_GRASS,YELLOW_FLOWER,RED_FLOWER,PURPLE_FLOWER,BLUE_FLOWER,WHITE_FLOWER):
                        # Flowers and grass are good for snakes to eat
                        if block != 0:
                            self.remove_block(*next_loc) 
                        # Grass makes snake longer
                        if block == TALL_GRASS:
                            length += 1
                        # Flowers change snake color
                        elif block in (YELLOW_FLOWER, RED_FLOWER, BLUE_FLOWER, WHITE_FLOWER, PURPLE_FLOWER):
                            material = FOOD[block]
                        direction = d
                        hx,hy,hz = next_loc
                        stuck = False
                        break

                # Turn around if stuck
                if stuck:
                    blocks.reverse()
                    direction = (direction + 2) % 4

                # Limit snake speed
                time.sleep(0.1)

                # Honor the kill flag
                if self.kill_flag:
                    break
        finally:
            self.move_player(0,0,0)
            for block in blocks:
                self.remove_block(*block)


s = SnakeBot('michaelfogleman.com')
#s = SnakeBot('localhost')

try:
    s.run()
except:
    s.kill_snakes()
    raise
