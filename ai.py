import random
import math
import time
import settings
import sounds

def run_enemy_ai(game):
    """
    Runs the AI for all enemy squads for one turn.
    The AI will attempt one action per frame to keep the game responsive.
    """
    time.sleep(0.1)
    acted_this_frame = False
    
    for i, squad in enumerate(game.enemy_squads):
        if acted_this_frame:
            break

        ai_state = game.squad_ai_states[i]
        
        # Update squad intelligence based on what they can see
        squad_visible_tiles = game.game_map.calculate_visible_tiles(squad)
        visible_players = [p for p in game.player_squad if p.is_alive and (p.x, p.y) in squad_visible_tiles]
        
        if visible_players:
            ai_state['target'] = min(visible_players, key=lambda p: p.hp)
            ai_state['last_known_pos'] = (ai_state['target'].x, ai_state['target'].y)
            ai_state['search_pos'] = None
        else:
            ai_state['target'] = None

        # Determine the squad's destination for this turn
        destination = None
        if ai_state['target']:
            destination = (ai_state['target'].x, ai_state['target'].y)
        elif ai_state['last_known_pos']:
            destination = ai_state['last_known_pos']
        else:
            if ai_state['search_pos'] is None or all(math.dist((u.x, u.y), ai_state['search_pos']) < 3 for u in squad if u.is_alive):
                # Find a new random point that isn't cover
                while True:
                    potential_dest = random.choice(game.game_map.spawn_points)
                    if not game.game_map.tiles[potential_dest[0]][potential_dest[1]].is_cover:
                        ai_state['search_pos'] = potential_dest
                        break
            destination = ai_state['search_pos']
            
        # A single unit from the squad takes an action
        for unit in squad:
            if unit.is_alive and unit.ap > 0:
                
                killed_by_overwatch = game.handle_reaction_fire(unit)
                if killed_by_overwatch:
                    acted_this_frame = True
                    break

                # 1. Melee attack if possible
                if ai_state['target'] and math.dist((unit.x, unit.y), (ai_state['target'].x, ai_state['target'].y)) < 1.5 and unit.ap >= settings.MELEE_COST:
                    game.handle_melee_attack(unit, ai_state['target'])
                    acted_this_frame = True
                    break
                # 2. Ranged attack if possible
                elif ai_state['target'] and unit.ap >= settings.SHOOT_COST:
                    game.handle_ranged_attack(unit, ai_state['target'])
                    acted_this_frame = True
                    break
                # 3. Move towards destination
                elif destination and unit.ap >= settings.MOVE_COST:
                    if ai_state['last_known_pos'] and (unit.x, unit.y) == ai_state['last_known_pos']:
                        ai_state['last_known_pos'] = None
                    
                    occupied_nodes = { (u.x, u.y) for u in game.player_squad + game.all_enemies if u is not unit }
                    path = game.astar.find_path((unit.x, unit.y), destination, occupied_nodes)
                    if path and len(path) > 1:
                        unit.x, unit.y = path[1]
                        unit.ap -= settings.MOVE_COST
                        sounds.SOUNDS['move'].play()
                        acted_this_frame = True
                        break
    
    # --- FIX: Call the correct function to end the enemy turn ---
    if not acted_this_frame:
        game.end_enemy_turn()
