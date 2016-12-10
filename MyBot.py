import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square, logger
import random
from math import sqrt

logger.open()
logger.log("Beginning of initialization.")

myID, game_map = hlt.get_init()
hlt.send_init("Risibot")

logger.log(game_map.player_ids)
logger.log(game_map.player_productions)

objective = game_map.get_good_starting_zone(myID)
get_move = None

logger.log("First objective: " + str(objective))
logger.log("Initialization ended.")
logger.close()

max_rent_reached = 0
critical_rent = 0
current_army = 0
aggro_radius = 1


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
    if square.strength > 200:
        return find_nearest_border_direction(square)
    ennemy, d = None, 0
    neighborhood = (n for n in game_map.neighbors(square, n=aggro_radius) if n.owner and n.owner != myID)
    for n in neighborhood:
        d_p = game_map.get_distance(square, n)
        if not ennemy or d_p < d:
            ennemy = n
            d = d_p
    if not ennemy:
        return find_nearest_border_direction(square)
    return game_map.get_direction(square, ennemy)


def find_nearest_border_direction(square):
    direction = NORTH
    max_distance = min(game_map.width, game_map.height) / 2
    for d in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        current = square
        t = game_map.get_target(square, d)
        while current.owner == myID and distance < max_distance:
            distance += 1
            current = game_map.get_target(current, d)
        if distance < max_distance:
            direction = d
            max_distance = distance
    return direction
    
def find_most_prolific_direction(square):
    direction = NORTH
    max_distance = min(game_map.width, game_map.height) / 2
    max_prod = 0
    for d in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        current = square
        s = 0
        while current.owner == myID and distance < max_distance:
            distance += 1
            current = game_map.get_target(current, d)
        k = 1 # The further we are, the less important resources are
        while distance < max_distance:
            distance += 1
            current = game_map.get_target(current, d)
            s += current.production / (max(1, current.strength) * 0.5 * k)
            k += 1
        if s > max_prod:
            s = max_prod
            direction = d
    return direction
    
def heuristic(square):
    if square.owner == 0 and square.strength > 0:
        return square.production / square.strength
    # return total potential damage caused by overkill when attacking this square
    return sum( neighbor.strength for neighbor in game_map.neighbors(square) if neighbor.owner not in (0, myID))

def get_move_after_settling(square):
    if square.strength >= 255:
        return Move(square, find_nearest_border_direction(square))
        
    target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                if neighbor.owner != myID or neighbor.strength > square.strength),
                                default = (None, None),
                                key = lambda t: heuristic(t[0]))
    if target is not None and target.strength < square.strength:
        return Move(square, direction)
    elif square.strength < square.production * 5:
        return Move(square, STILL)

    border = any(neighbor.owner != myID for neighbor in game_map.neighbors(square))
    if not border:
        return Move(square, expansion_function(square))
    else:
        #wait until we are strong enough to attack
        return Move(square, STILL)

# Global functions used to manage all units in once without if ... else
get_move = get_move_before_settling
expansion_function = find_most_prolific_direction
    
while True:
    logger.open()
    game_map.get_frame()
    
    global aggro_radius
    aggro_radius = int(sqrt( game_map.player_armies[0] / (2 * 3.14) )) + 1
    logger.log("Radius: " + str(aggro_radius))
    
    if get_move != get_move_before_settling and expansion_function == find_most_prolific_direction:
        if game_map.player_interests[0] > max_rent_reached:
            max_rent_reached = game_map.player_interests[0]
            critical_rent = 0.92 * max_rent_reached
        elif game_map.player_interests[0] <= critical_rent or current_army > game_map.player_armies[0]:
            global expansion_function
            global tempo
            expansion_function = find_nearest_enemy_direction
            logger.log("Switching strategy !")
    current_army = game_map.player_armies[0]
    
        
    moves = [get_move(square) for square in game_map if square.owner == myID]
    hlt.send_frame(moves)
    logger.close()