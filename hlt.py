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

##############################################
# Unique logger, has to be created only once #
##############################################

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


Square = namedtuple('Square', 'x y owner strength production')

Move = namedtuple('Move', 'square direction')


class GameMap:
    def __init__(self, size_string, production_string, map_string=None):
        self.width, self.height = tuple(map(int, size_string.split()))
        self.production = tuple(tuple(map(int, substring)) for substring in grouper(production_string.split(), self.width))
        self.contents = None
        self.get_frame(map_string)
        self.starting_player_count = len(set(square.owner for square in self)) - 1
        self.average_production = sum([square.production for square in self]) / (self.width * self.height)

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
        
    def get_direction(self, sq1, sq2):
        "Returns the best direction to follow from sq1 to sq2"
        dx, dy = sq1.x - sq2.x, sq1.y - sq2.y
        dir_x, dir_y = (WEST if dx > 0 else EAST if dx < 0 else STILL), (NORTH if dy > 0 else SOUTH if dy < 0 else STILL) # Where have we to go ?
        dir_x, dir_y = (dir_x if dx < self.width / 2 else opposite_cardinal(dir_x)), (dir_y if dy < self.height / 2 else opposite_cardinal(dir_y))
        if dir_x == STILL:
            return dir_y
        if dir_y == STILL:
            return dir_x
        
        # We take the easiest way if we have two choices
        t_x = self.get_target(sq1, dir_x)
        if t_x.owner == sq1.owner:
            return dir_x
        t_y = self.get_target(sq1, dir_y)
        if t_y.owner == sq1.owner:
            return dir_y
            
        f = lambda t: dir_x if t == t_x else dir_y
        return f(min( (t_x, t_y), key=(lambda sq: sq.strength) ))
        
    def get_good_starting_zone(self, player_id):
        "Returns an interesting zone to conquer first (labyrinthic search)"
        squares = chain([c for c in self if c.owner == player_id])
        best = (None, -1)
        s, start = None, None
        
        try:
            s = next(squares)
        except StopIteration:
            logger.log("Can't find any ally square.")
            raise StopIteration
        
        start, f_rent = s, lambda x: 1 if x < 3 else 2/3 if x < 4 else 1/2 if x < 5 else 1/3 if x < 6 else 0
        while s:
            d = self.get_distance(start, s)
            squares = chain(squares, [n for n in self.neighbors(s) if f_rent(self.get_distance(start, n)) * n.production >= s.production and self.get_distance(start, n) > d])
            best = (s, s.production) if s.production > best[1] else best
            s = next(squares, None)
        return best[0]
        
    def get_square(self, x, y):
        "Sometimes it's necessary"
        return self.contents[y % self.height][x % self.width]
          

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
    
