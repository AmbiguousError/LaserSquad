import pygame
import random
import math
import time
import settings
from map import GameMap
from camera import Camera
from pathfinding import AStar
from sprites import Unit
import sounds
import ai
import ui

class Game:
    """Main game class that manages state, turns, and drawing."""
    def __init__(self):
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Tactical Squad Game")
        self.clock = pygame.time.Clock()
        self.FONT_S = pygame.font.SysFont('Consolas', 16)
        self.FONT_M = pygame.font.SysFont('Consolas', 20)
        self.FONT_L = pygame.font.SysFont('Consolas', 32, bold=True)
        
        self.game_surface = pygame.Surface((settings.SCREEN_WIDTH - settings.SIDE_PANEL_WIDTH, settings.SCREEN_HEIGHT))
        
        self.minimap_rect = pygame.Rect(settings.SCREEN_WIDTH - settings.MINIMAP_WIDTH - 10, 10, settings.MINIMAP_WIDTH, settings.MINIMAP_HEIGHT)
        self.minimap_surface = pygame.Surface((settings.MINIMAP_WIDTH, settings.MINIMAP_HEIGHT))
        self.end_turn_button = pygame.Rect(settings.SCREEN_WIDTH - 220, settings.SCREEN_HEIGHT - 70, 200, 50)
        self.overwatch_button = pygame.Rect(settings.SCREEN_WIDTH - 440, settings.SCREEN_HEIGHT - 70, 200, 50)
        self.prone_button = pygame.Rect(settings.SCREEN_WIDTH - 660, settings.SCREEN_HEIGHT - 70, 200, 50)
        self.heal_button = pygame.Rect(settings.SCREEN_WIDTH - 880, settings.SCREEN_HEIGHT - 70, 200, 50)

        self.reset_game()


    def reset_game(self):
        """Resets the game to its initial state to play again."""
        while True:
            self.game_map = GameMap(settings.MAP_WIDTH, settings.MAP_HEIGHT)
            if len(self.game_map.spawn_points) >= settings.NUM_ENEMY_SQUADS + 1:
                break
        
        self.camera = Camera(settings.MAP_WIDTH * settings.TILE_SIZE, 
                             settings.MAP_HEIGHT * settings.TILE_SIZE,
                             settings.SCREEN_WIDTH - settings.SIDE_PANEL_WIDTH,
                             settings.SCREEN_HEIGHT)
        self.astar = AStar(self.game_map)
        self.player_squad, self.enemy_squads = [], []
        self.squad_ai_states = []
        self._spawn_units()
        
        self.game_state = 'HOME_SCREEN'
        self.selected_unit = None
        self.laser_effects = []
        self.skill_check_messages = []
        self.turn_number = 1
        
        self.game_over_message = ""

    @property
    def all_enemies(self):
        """Returns a flattened list of all enemy units."""
        return [unit for squad in self.enemy_squads for unit in squad]

    def _find_spawn_tiles(self, start_x, start_y, count):
        spawn_tiles = []
        occupied_tiles = set((u.x, u.y) for u in self.player_squad + self.all_enemies)

        def is_valid_spawn(x, y):
            return (self.game_map.is_in_bounds(x, y) and
                    not self.game_map.tiles[x][y].is_wall and
                    (x, y) not in occupied_tiles)

        if is_valid_spawn(start_x, start_y):
            spawn_tiles.append((start_x, start_y)); occupied_tiles.add((start_x, start_y))
        for radius in range(1, 10):
            if len(spawn_tiles) >= count: break
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius: continue
                    x, y = start_x + dx, start_y + dy
                    if is_valid_spawn(x, y):
                        spawn_tiles.append((x, y)); occupied_tiles.add((x, y))
                        if len(spawn_tiles) >= count: break
                if len(spawn_tiles) >= count: break
        return spawn_tiles

    def _spawn_units(self):
        spawn_points = random.sample(self.game_map.spawn_points, settings.NUM_ENEMY_SQUADS + 1)
        player_start_center = spawn_points.pop(0)
        player_spawns = self._find_spawn_tiles(player_start_center[0], player_start_center[1], settings.SQUAD_SIZE)
        for i, (x, y) in enumerate(player_spawns[:settings.SQUAD_SIZE]):
            name = settings.PHONETIC_ALPHABET[i]
            self.player_squad.append(Unit(x, y, 'player', self.game_map, name=name, number=i+1))

        for sp in spawn_points:
            new_squad = []
            enemy_spawns = self._find_spawn_tiles(sp[0], sp[1], settings.SQUAD_SIZE)
            for x, y in enemy_spawns:
                new_squad.append(Unit(x, y, 'enemy', self.game_map))
            self.enemy_squads.append(new_squad)
            self.squad_ai_states.append({'target': None, 'last_known_pos': None, 'search_pos': None})

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                self.handle_input(event)
            
            self.screen.fill(settings.COLOR_BLACK)
            if self.game_state == 'HOME_SCREEN': ui.draw_home_screen(self)
            else: self.update(); ui.draw_game_world(self)
            pygame.display.flip()
            self.clock.tick(60)

    def handle_input(self, event):
        if self.game_state == 'HOME_SCREEN':
            if event.type == pygame.KEYDOWN:
                self.start_player_turn()
            return
        if self.game_state == 'GAME_OVER':
            if event.type == pygame.KEYDOWN: self.reset_game()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: self.camera.scroll(dy=-settings.CAMERA_SCROLL_SPEED)
            if event.key == pygame.K_DOWN: self.camera.scroll(dy=settings.CAMERA_SCROLL_SPEED)
            if event.key == pygame.K_LEFT: self.camera.scroll(dx=-settings.CAMERA_SCROLL_SPEED)
            if event.key == pygame.K_RIGHT: self.camera.scroll(dx=settings.CAMERA_SCROLL_SPEED)
            if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                num_to_select = event.key - pygame.K_0
                for unit in self.player_squad:
                    if unit.number == num_to_select and unit.is_alive:
                        if self.selected_unit: self.selected_unit.is_selected = False
                        self.selected_unit = unit; self.selected_unit.is_selected = True
                        self.camera.center_on(self.selected_unit); break
            if event.key == pygame.K_o: self.try_overwatch()
            if event.key == pygame.K_h: self.try_heal()
            if event.key == pygame.K_c: self.try_change_posture()
        if self.game_state != 'PLAYER_TURN': return
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.end_turn_button.collidepoint(mouse_pos): self.end_player_turn(); return
            if self.overwatch_button.collidepoint(mouse_pos): self.try_overwatch(); return
            if self.prone_button.collidepoint(mouse_pos): self.try_change_posture(); return
            if self.heal_button.collidepoint(mouse_pos): self.try_heal(); return
            if self.minimap_rect.collidepoint(mouse_pos):
                mini_x = (mouse_pos[0] - self.minimap_rect.x) / settings.MINIMAP_SCALE
                mini_y = (mouse_pos[1] - self.minimap_rect.y) / settings.MINIMAP_SCALE
                self.camera.center_on_coords(mini_x, mini_y); return
            if mouse_pos[0] < settings.SIDE_PANEL_WIDTH: return
            game_world_x = mouse_pos[0] - settings.SIDE_PANEL_WIDTH
            map_x, map_y = int((game_world_x + self.camera.x) / settings.TILE_SIZE), int((mouse_pos[1] + self.camera.y) / settings.TILE_SIZE)
            if not self.game_map.is_in_bounds(map_x, map_y): return
            if event.button == 1:
                clicked_unit = self.get_unit_at(map_x, map_y, self.player_squad)
                if clicked_unit:
                    if self.selected_unit: self.selected_unit.is_selected = False
                    self.selected_unit = clicked_unit; self.selected_unit.is_selected = True
            elif event.button == 3 and self.selected_unit:
                target_unit = self.get_unit_at(map_x, map_y, self.all_enemies)
                if target_unit and self.game_map.tiles[map_x][map_y].is_visible:
                    if math.dist((self.selected_unit.x, self.selected_unit.y), (target_unit.x, target_unit.y)) < 1.5: self.handle_melee_attack(self.selected_unit, target_unit)
                    else: self.handle_ranged_attack(self.selected_unit, target_unit)
                elif not self.game_map.tiles[map_x][map_y].is_wall and not self.game_map.tiles[map_x][map_y].is_cover:
                    occupied_nodes = { (u.x, u.y) for u in self.player_squad if u is not self.selected_unit }
                    if (map_x, map_y) in occupied_nodes: return
                    path = self.astar.find_path((self.selected_unit.x, self.selected_unit.y), (map_x, map_y), occupied_nodes)
                    if path: self.selected_unit.path = path[1:]

    def handle_camera_edge_scroll(self):
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > settings.SCREEN_WIDTH - 20: self.camera.scroll(dx=settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[0] < settings.SIDE_PANEL_WIDTH + 20 and mouse_pos[0] > settings.SIDE_PANEL_WIDTH: self.camera.scroll(dx=-settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[1] < 20: self.camera.scroll(dy=-settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[1] > settings.SCREEN_HEIGHT - 20: self.camera.scroll(dy=settings.CAMERA_SCROLL_SPEED)

    def try_overwatch(self):
        if self.selected_unit and self.selected_unit.ap >= settings.OVERWATCH_COST and not self.selected_unit.is_on_overwatch:
            self.selected_unit.is_on_overwatch = True; self.selected_unit.ap -= settings.OVERWATCH_COST
    def try_heal(self):
        if self.can_selected_unit_heal():
            for unit in self.player_squad:
                if unit is not self.selected_unit and unit.is_alive and unit.hp < settings.UNIT_MAX_HP:
                     if math.dist((self.selected_unit.x, self.selected_unit.y), (unit.x, unit.y)) < 1.5: self.handle_heal(self.selected_unit, unit); break
    def try_change_posture(self):
        if self.selected_unit: self.selected_unit.change_posture()

    def can_selected_unit_heal(self):
        if self.selected_unit and self.selected_unit.ap >= settings.HEAL_COST:
            for unit in self.player_squad:
                if unit is not self.selected_unit and unit.is_alive and unit.hp < settings.UNIT_MAX_HP:
                     if math.dist((self.selected_unit.x, self.selected_unit.y), (unit.x, unit.y)) < 1.5:
                        return True
        return False

    def handle_heal(self, healer, target):
        healer.ap -= settings.HEAL_COST; healer.heals_given += 1; target.heal(settings.HEAL_AMOUNT)
    def get_unit_at(self, x, y, squad):
        for unit in squad:
            if unit.is_alive and unit.x == x and unit.y == y: return unit
        return None

    def perform_skill_check(self, attacker, target, skill_bonus):
        roll = random.randint(1, 20); total = roll + skill_bonus
        dc = settings.TARGET_DC_BASE
        if target.posture == 'prone': dc += settings.TARGET_DC_MOD_PRONE
        if total >= dc: self.display_skill_check("Success!", (target.x, target.y), settings.COLOR_SUCCESS); return True
        else: self.display_skill_check("Miss!", (target.x, target.y), settings.COLOR_FAIL); return False
    def display_skill_check(self, message, pos, color):
        self.skill_check_messages.append({'text': message, 'pos': pos, 'timer': 60, 'color': color})

    def handle_ranged_attack(self, attacker, target):
        if self.handle_reaction_fire(attacker): return
        if attacker.ap < settings.SHOOT_COST: return
        attacker.shots_taken += 1; attacker.is_on_overwatch = False; attacker.has_fired_overwatch = False; attacker.ap -= settings.SHOOT_COST
        los_path = self.game_map.get_line_of_sight(attacker, (target.x, target.y), self.player_squad + self.all_enemies)
        if los_path and los_path[-1] == (target.x, target.y):
            if self.perform_skill_check(attacker, target, attacker.ranged_skill):
                attacker.shots_hit += 1; damage = settings.LASER_DAMAGE if attacker.team == 'player' else settings.ENEMY_LASER_DAMAGE
                sounds.SOUNDS['laser'].play(); was_alive = target.is_alive; target.take_damage(damage)
                if was_alive and not target.is_alive: attacker.kills += 1
                self.laser_effects.append(((attacker.x, attacker.y), (target.x, target.y), 30)); self.check_game_over()
    
    def handle_melee_attack(self, attacker, target):
        if self.handle_reaction_fire(attacker): return
        if attacker.ap < settings.MELEE_COST: return
        attacker.shots_taken += 1; attacker.is_on_overwatch = False; attacker.has_fired_overwatch = False; attacker.ap -= settings.MELEE_COST
        if self.perform_skill_check(attacker, target, attacker.melee_skill):
             attacker.shots_hit += 1; was_alive = target.is_alive; target.take_damage(settings.MELEE_DAMAGE)
             if was_alive and not target.is_alive: attacker.kills += 1
             self.check_game_over()

    def check_game_over(self):
        if not any(u.is_alive for u in self.player_squad): self.game_over_message = "DEFEAT"; self.game_state = 'GAME_OVER'
        elif not any(u.is_alive for u in self.all_enemies): self.game_over_message = "VICTORY"; self.game_state = 'GAME_OVER'

    def update(self):
        if self.game_state in ['HOME_SCREEN', 'GAME_OVER']: return
        self.handle_camera_edge_scroll()
        if self.game_state == 'PLAYER_TURN':
            if self.selected_unit and self.selected_unit.path:
                visible_enemies_before_move = {e for e in self.all_enemies if e.is_alive and self.game_map.tiles[e.x][e.y].is_visible}
                moved = self.selected_unit.move_along_path()
                if moved:
                    self.game_map.update_fov(self.player_squad)
                    visible_enemies_after_move = {e for e in self.all_enemies if e.is_alive and self.game_map.tiles[e.x][e.y].is_visible}
                    if visible_enemies_after_move - visible_enemies_before_move: self.selected_unit.path = [] 
        elif self.game_state == 'ENEMY_TURN': ai.run_enemy_ai(self)
        self.skill_check_messages = [m for m in self.skill_check_messages if m['timer'] > 0]
        for m in self.skill_check_messages: m['timer'] -= 1
        self.laser_effects = [(s, e, t - 1) for s, e, t in self.laser_effects if t > 1]
    
    def handle_reaction_fire(self, acting_unit):
        opposing_squad = self.player_squad
        for unit in opposing_squad:
            if unit.is_alive and unit.is_on_overwatch and not unit.has_fired_overwatch:
                los_path = self.game_map.get_line_of_sight(unit, (acting_unit.x, acting_unit.y), self.player_squad + self.all_enemies)
                if los_path and los_path[-1] == (acting_unit.x, acting_unit.y):
                    unit.shots_taken += 1
                    if self.perform_skill_check(unit, acting_unit, unit.ranged_skill):
                        unit.shots_hit += 1; sounds.SOUNDS['laser'].play(); was_alive = acting_unit.is_alive
                        acting_unit.take_damage(settings.LASER_DAMAGE)
                        if was_alive and not acting_unit.is_alive: unit.kills += 1
                        self.laser_effects.append(((unit.x, unit.y), (acting_unit.x, acting_unit.y), 30))
                        unit.has_fired_overwatch = True; unit.is_on_overwatch = False; self.check_game_over()
                        if not acting_unit.is_alive: return True 
        return False

    def start_player_turn(self):
        self.game_state = 'PLAYER_TURN'
        if self.player_squad:
            first_alive = next((u for u in self.player_squad if u.is_alive), None)
            if first_alive:
                self.selected_unit = first_alive
                self.selected_unit.is_selected = True
                self.camera.center_on(self.selected_unit)
            else:
                 self.selected_unit = None

        for unit in self.player_squad:
            if unit.is_alive: unit.ap = settings.UNIT_MAX_AP; unit.has_fired_overwatch = False
        self.game_map.update_fov(self.player_squad)

    def end_player_turn(self):
        self.game_state = 'ENEMY_TURN'
        for unit in self.all_enemies:
            if unit.is_alive: unit.ap = settings.UNIT_MAX_AP

    def end_enemy_turn(self):
        self.turn_number += 1; self.start_player_turn()
