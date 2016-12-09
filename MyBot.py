import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square, logger
import random

logger.open()
logger.log("Beginning of initialization.")

myID, game_map = hlt.get_init()
hlt.send_init("Risibot")

objective = game_map.get_good_starting_zone(myID)
get_move = None

logger.log("First objective: " + str(objective))
logger.log("Initialization ended.")
logger.close()

################# SETTLING TIME #######################
        
def get_move_before_settling(square):
        
    # Yes, it can occur oO
    if square.production == 0:
        if any(n.owner == myID for n in game_map.neighbors(s)): # We have already settle somewhere else
            return Move(square, STILL)
        return Move(square, max([(n, d) for d, n in enumerate(game_map.neighbors(square)) if n.strength <= square.strength], key=lambda t: t[0].production)[1])
        
    # We have reached our objective
    if game_map.get_square(objective.x, objective.y).owner == myID:
        logger.log("Objective reached !")
        global get_move
        get_move = get_move_after_settling
        return get_move(square)
        
    direction = game_map.get_direction(square, objective)
    target = game_map.get_target(square, direction)
    if square.strength > 0 and (target.owner == myID or target.strength < square.strength):
        return Move(square, direction)
    return Move(square, STILL)

############### BATTLE TIME ####################


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
        return sum(neighbor.strength for neighbor in game_map.neighbors(square) if neighbor.owner not in (0, myID))

def get_move_after_settling(square):
    target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                if neighbor.owner != myID),
                                default = (None, None),
                                key = lambda t: heuristic(t[0]))
    if target is not None and target.strength < square.strength:
        return Move(square, direction)
    elif square.strength < square.production * 5:
        return Move(square, STILL)

    border = any(neighbor.owner != myID for neighbor in game_map.neighbors(square))
    if not border:
        return Move(square, find_nearest_enemy_direction(square))
    else:
        #wait until we are strong enough to attack
        return Move(square, STILL)

get_move = get_move_before_settling
    
while True:
    logger.open()
    game_map.get_frame()
    moves = [get_move(square) for square in game_map if square.owner == myID]
    hlt.send_frame(moves)
    logger.close()