"""
A Python-based Halite starter-bot framework.

This module contains a Pythonic implementation of a Halite starter-bot framework.
In addition to a class (GameMap) containing all information about the game world
and some helper methods, the module also imeplements the functions necessary for
communicating with the Halite game environment.
"""

import sys
from collections import namedtuple
from itertools import chain, zip_longest
from random import randint

class Logger:
  
    def __init__(self, file_name):
        self.file_name = ".".join( ("_".join( (file_name, str(randint(0, 100000))) ), "log") )
        self.stream = None
        self.turn = -1
    
    def open(self):
        self.stream = open(self.file_name, "a")
        assert self.stream
        self.turn += 1
    
    def close(self):
        assert self.stream
        self.stream.close()
    
    def log(self, msg):
        assert self.stream
        self.stream.write("".join( (" ".join( ("Turn", str(self.turn), ":", str(msg) ) ), "\n") ))

logger = Logger("Risibot")


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

# Because Python uses zero-based indexing, the cardinal directions have a different mapping in this Python starterbot
# framework than that used by the Halite game environment.  This simplifies code in several places.  To accommodate
# this difference, the translation to the indexing system used by the game environment is done automatically by
# the send_frame function when communicating with the Halite game environment.

NORTH, EAST, SOUTH, WEST, STILL = range(5)

def opposite_cardinal(direction):
    "Returns the opposing cardinal direction."
    return (direction + 2) % 4 if direction != STILL else STILL
   
def cardinal_to_step(direction):
    return 0 if direction == STILL else 1 if (direction - 1) % 3 == 2 else -1


Square = namedtuple('Square', 'x y owner strength production')

Move = namedtuple('Move', 'square direction')

class GameMap:
    def __init__(self, size_string, production_string, map_string=None):
        self.width, self.height = tuple(map(int, size_string.split()))
        self.production = tuple(tuple(map(int, substring)) for substring in grouper(production_string.split(), self.width))
        self.contents = None
        self.get_frame(map_string)
        
        self.starting_player_count = len(set(square.owner for square in self)) - 1
        
    def get_frame(self, map_string=None):
        "Updates the map information from the latest frame provided by the Halite game environment."
        if map_string is None:
            map_string = get_string()
        split_string = map_string.split()
        owners = list()
        while len(owners) < self.width * self.height:
            counter = int(split_string.pop(0))
            owner = int(split_string.pop(0))
            owners.extend([owner] * counter)
        assert len(owners) == self.width * self.height
        assert len(split_string) == self.width * self.height
        self.contents = [[Square(x, y, owner, strength, production)
                          for x, (owner, strength, production)
                          in enumerate(zip(owner_row, strength_row, production_row))]
                         for y, (owner_row, strength_row, production_row)
                         in enumerate(zip(grouper(owners, self.width),
                                          grouper(map(int, split_string), self.width),
                                          self.production))]
            

    def __iter__(self):
        "Allows direct iteration over all squares in the GameMap instance."
        return chain.from_iterable(self.contents)

    def neighbors(self, square, n=1, include_self=False):
        "Iterable over the n-distance neighbors of a given square.  For single-step neighbors, the enumeration index provides the direction associated with the neighbor."
        assert isinstance(include_self, bool)
        assert isinstance(n, int) and n > 0
        if n == 1:
            combos = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))   # NORTH, EAST, SOUTH, WEST, STILL ... matches indices provided by enumerate(game_map.neighbors(square))
        else:
            combos = ((dx, dy) for dy in range(-n, n+1) for dx in range(-n, n+1) if abs(dx) + abs(dy) <= n)
        return (self.contents[(square.y + dy) % self.height][(square.x + dx) % self.width] for dx, dy in combos if include_self or dx or dy)

    def get_target(self, square, direction):
        "Returns a single, one-step neighbor in a given direction."
        dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))[direction]
        return self.contents[(square.y + dy) % self.height][(square.x + dx) % self.width]

    def get_distance(self, sq1, sq2):
        "Returns Manhattan distance between two squares."
        dx = min(abs(sq1.x - sq2.x), sq1.x + self.width - sq2.x, sq2.x + self.width - sq1.x)
        dy = min(abs(sq1.y - sq2.y), sq1.y + self.height - sq2.y, sq2.y + self.height - sq1.y)
        return dx + dy
        
    def get_directions(self, sq1, sq2):
        "Returns viable directions to go from sq1 to sq2"
        dx, dy = sq2.x - sq1.x, sq2.y - sq1.y
        dir_x, dir_y = EAST if dx > 0 else STILL if dx == 0 else WEST, SOUTH if dy > 0 else STILL if dy == 0 else NORTH
        dir_x, dir_y = opposite_cardinal(dir_x) if abs(dx) > self.width / 2 else dir_x, opposite_cardinal(dir_y) if abs(dy) > self.height / 2 else dir_y
        return dir_x, dir_y
        
    def viscosity(self, square, player_id):
        "Returns how easy crossing a square is"
        if square.owner == player_id:
            return 1
        
        return square.strength / max(1, square.production)
        
    def get_best_direction(self, sq1, sq2):
        "Returns best direction to go from sq1 to sq2"
        dx, dy = self.get_directions(sq1, sq2)
        return dy if dx == STILL else dx if dy == STILL else min( ( (d, self.get_target(sq1, d)) for d in (dx, dy)), key=lambda t: self.viscosity(t[1], sq1.owner) )[0]
        
    def get_productive_squares(self):
        "Returns a list of interesting zones"
        max_production = int(0.85 * max( (square.production for square in self) ))
        candidates = [square for square in self if square.production >= max_production ]
        squares = []
        for square in candidates:
            if not any(self.get_distance(square, c) < 6 for c in squares):
                squares.append(max( ((s, s.production) for s in self.neighbors(square, 4, True)), key=lambda t: t[1] )[0])
        return squares
        
    def estimate_duration(self, sq1, sq2):
        "How man turns does it take to go from sq1 to sq2"
        t = 0
        cursor, target = sq1, self.get_target(sq1, self.get_best_direction(sq1, sq2))
        
        if sq1.production == 0:
            target = max( ((s, s.production) for s in self.neighbors(sq1) if s.strength < sq1.strength), key=lambda x: x[1] )[0]
            
        my_strength, production, remaining_strength = sq1.strength, sq1.production, int(1.2*target.strength)
        
        while cursor != sq2:
            my_strength += production
            if remaining_strength <= my_strength:
                my_strength -= remaining_strength
                cursor = target
                production += cursor.production
                target = self.get_target(cursor, self.get_best_direction(cursor, sq2))
                remaining_strength = int(1.2*target.strength)
            t += 1
        return t

#####################################################################################################################
# Functions for communicating with the Halite game environment (formerly contained in separate module networking.py #
#####################################################################################################################


def send_string(s):
    sys.stdout.write(s)
    sys.stdout.write('\n')
    sys.stdout.flush()


def get_string():
    return sys.stdin.readline().rstrip('\n')


def get_init():
    playerID = int(get_string())
    m = GameMap(get_string(), get_string())
    return playerID, m


def send_init(name):
    send_string(name)


def translate_cardinal(direction):
    "Translate direction constants used by this Python-based bot framework to that used by the official Halite game environment."
    # Cardinal indexing used by this bot framework is
    #~ NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3, STILL = 4
    # Cardinal indexing used by official Halite game environment is
    #~ STILL = 0, NORTH = 1, EAST = 2, SOUTH = 3, WEST = 4
    #~ >>> list(map(lambda x: (x+1) % 5, range(5)))
    #~ [1, 2, 3, 4, 0]
    return (direction + 1) % 5


def send_frame(moves):
    send_string(' '.join(str(move.square.x) + ' ' + str(move.square.y) + ' ' + str(translate_cardinal(move.direction)) for move in moves))
    
