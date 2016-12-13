import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square, logger
import random

logger.open()

myID, game_map = hlt.get_init()
hlt.send_init("Risibotator")

starting_point = next(s for s in game_map if s.owner == myID)
interesting_zones = game_map.get_productive_squares()
objective = min( ( (s, game_map.estimate_duration(starting_point, s)) for s in interesting_zones), key=lambda x: x[1] )[0]
settling_time = game_map.estimate_duration(starting_point, objective)

logger.log(interesting_zones)
logger.log(objective)
logger.log(settling_time)
logger.close()


def find_nearest_enemy_direction(square):
    direction = NORTH
    max_distance = min(game_map.width, game_map.height) / 2
    for d in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        current = square
        while current.owner == myID and distance < max_distance:
            distance += 1
            current = game_map.get_target(current, d)
        if distance < max_distance:
            direction = d
            max_distance = distance
    return direction

def heuristic(square):
    if square.owner == 0 and square.strength > 0:
        return square.production / square.strength
    else:
        # return total potential damage caused by overkill when attacking this square
        return sum( min(square.strength, neighbor.strength) for neighbor in game_map.neighbors(square) if neighbor.owner not in (0, myID))

def expansionist_strategy(square):
    target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                if neighbor.owner != myID),
                                default = (None, None),
                                key = lambda t: heuristic(t[0]))
    if target is not None and target.strength < square.strength:
        return direction
    elif square.strength < square.production * 5:
        return STILL

    border = any(neighbor.owner != myID for neighbor in game_map.neighbors(square))
    if not border:
        return find_nearest_enemy_direction(square)
    else:
        #wait until we are strong enough to attack
        return STILL
        
def rush_strategy(square):
    if square.strength < square.production * 5:
        return STILL
    d = game_map.get_best_direction(square, objective)
    target = game_map.get_target(square, d)
    if target.owner == myID or target.strength < square.strength:
        if target == objective:
            global current_strategy
            current_strategy = expansionist_strategy
        return d
    return STILL

current_strategy = rush_strategy

def get_move(square):
    return Move(square, current_strategy(square))
    
def avoid_collisions(move):
    return move
    
while True:
    game_map.get_frame()
    moves = map(avoid_collisions, [get_move(square) for square in game_map if square.owner == myID])
    hlt.send_frame(moves)
