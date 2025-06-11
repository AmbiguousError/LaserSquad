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

class Game:
    """Main game class that manages state, turns, and drawing."""
    def __init__(self):
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Tactical Squad Game")
        self.clock = pygame.time.Clock()
        self.FONT_S = pygame.font.SysFont('Consolas', 16)
        self.FONT_M = pygame.font.SysFont('Consolas', 20)
        self.FONT_L = pygame.font.SysFont('Consolas', 32, bold=True)
        
        # --- FIX: Create a dedicated surface for the game world ---
        self.game_surface = pygame.Surface((settings.SCREEN_WIDTH - settings.SIDE_PANEL_WIDTH, settings.SCREEN_HEIGHT))
        
        self.reset_game(initial_setup=True)


    def reset_game(self, initial_setup=False):
        """Resets the game to its initial state to play again."""
        while True:
            self.game_map = GameMap(settings.MAP_WIDTH, settings.MAP_HEIGHT)
            if len(self.game_map.spawn_points) >= settings.NUM_ENEMY_SQUADS + 1:
                break
        
        # --- FIX: Initialize camera with the correct viewport dimensions ---
        self.camera = Camera(settings.MAP_WIDTH * settings.TILE_SIZE, 
                             settings.MAP_HEIGHT * settings.TILE_SIZE,
                             settings.SCREEN_WIDTH - settings.SIDE_PANEL_WIDTH,
                             settings.SCREEN_HEIGHT)
        self.astar = AStar(self.game_map)
        self.player_squad, self.enemy_squad = [], []
        self._spawn_units()
        
        self.game_state = 'HOME_SCREEN'
        self.selected_unit = None
        self.laser_effects = []
        self.skill_check_messages = []
        self.turn_number = 1
        
        if initial_setup:
             self.minimap_rect = pygame.Rect(settings.SCREEN_WIDTH - settings.MINIMAP_WIDTH - 10, 10, settings.MINIMAP_WIDTH, settings.MINIMAP_HEIGHT)
             self.minimap_surface = pygame.Surface((settings.MINIMAP_WIDTH, settings.MINIMAP_HEIGHT))
             self.end_turn_button = pygame.Rect(settings.SCREEN_WIDTH - 220, settings.SCREEN_HEIGHT - 70, 200, 50)
             self.overwatch_button = pygame.Rect(settings.SCREEN_WIDTH - 440, settings.SCREEN_HEIGHT - 70, 200, 50)

        self.game_over_message = ""
        self.enemy_squad_target = None
        self.last_known_player_pos = None
        self.enemy_search_pos = None

    def _find_spawn_tiles(self, start_x, start_y, count):
        spawn_tiles = []
        occupied_tiles = set()
        for x, y in [(u.x, u.y) for u in self.player_squad + self.enemy_squad]:
            occupied_tiles.add((x, y))

        def is_valid_spawn(x, y):
            return (self.game_map.is_in_bounds(x, y) and
                    not self.game_map.tiles[x][y].is_wall and
                    (x, y) not in occupied_tiles)

        if is_valid_spawn(start_x, start_y):
            spawn_tiles.append((start_x, start_y))
            occupied_tiles.add((start_x, start_y))

        for radius in range(1, 10):
            if len(spawn_tiles) >= count: break
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius: continue
                    x, y = start_x + dx, start_y + dy
                    if is_valid_spawn(x, y):
                        spawn_tiles.append((x, y))
                        occupied_tiles.add((x, y))
                        if len(spawn_tiles) >= count: break
                if len(spawn_tiles) >= count: break
        return spawn_tiles

    def _spawn_units(self):
        spawn_points = random.sample(self.game_map.spawn_points, settings.NUM_ENEMY_SQUADS + 1)
        
        player_start_center = spawn_points.pop(0)
        player_spawns = self._find_spawn_tiles(player_start_center[0], player_start_center[1], settings.SQUAD_SIZE)
        for i, (x, y) in enumerate(player_spawns[:settings.SQUAD_SIZE]):
            name = settings.PHONETIC_ALPHABET[i] if i < len(settings.PHONETIC_ALPHABET) else f"Unit {i+1}"
            self.player_squad.append(Unit(x, y, 'player', self.game_map, name=name, number=i+1))

        for sp in spawn_points:
            enemy_spawns = self._find_spawn_tiles(sp[0], sp[1], settings.SQUAD_SIZE)
            for x, y in enemy_spawns[:settings.SQUAD_SIZE]:
                self.enemy_squad.append(Unit(x, y, 'enemy', self.game_map))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                self.handle_input(event)
            
            self.screen.fill(settings.COLOR_BLACK)
            if self.game_state == 'HOME_SCREEN':
                self.draw_home_screen()
            else:
                self.update()
                self.draw_game_world()

            pygame.display.flip()
            self.clock.tick(60)

    def handle_input(self, event):
        if self.game_state == 'HOME_SCREEN':
            if event.type == pygame.KEYDOWN:
                self.start_player_turn()
                if self.player_squad:
                    self.selected_unit = self.player_squad[0]
                    self.selected_unit.is_selected = True
                    self.camera.center_on(self.selected_unit)
            return

        if self.game_state == 'GAME_OVER':
            if event.type == pygame.KEYDOWN:
                self.reset_game()
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
                        self.selected_unit = unit
                        self.selected_unit.is_selected = True
                        self.camera.center_on(self.selected_unit)
                        break
            if event.key == pygame.K_o: self.try_overwatch()
            if event.key == pygame.K_h: self.try_heal()

        if self.game_state != 'PLAYER_TURN': return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            # Check UI clicks first
            if self.end_turn_button.collidepoint(mouse_pos): self.end_player_turn(); return
            if self.overwatch_button.collidepoint(mouse_pos): self.try_overwatch(); return
            if self.minimap_rect.collidepoint(mouse_pos):
                mini_x = (mouse_pos[0] - self.minimap_rect.x) / settings.MINIMAP_SCALE
                mini_y = (mouse_pos[1] - self.minimap_rect.y) / settings.MINIMAP_SCALE
                self.camera.center_on_coords(mini_x, mini_y); return

            # --- FIX: Only process game world clicks if outside the side panel ---
            if mouse_pos[0] < settings.SIDE_PANEL_WIDTH: return

            game_world_x = mouse_pos[0] - settings.SIDE_PANEL_WIDTH
            map_x = int((game_world_x + self.camera.x) / settings.TILE_SIZE)
            map_y = int((mouse_pos[1] + self.camera.y) / settings.TILE_SIZE)

            if not self.game_map.is_in_bounds(map_x, map_y): return
            
            if event.button == 1:
                clicked_unit = self.get_unit_at(map_x, map_y, self.player_squad)
                if clicked_unit:
                    if self.selected_unit: self.selected_unit.is_selected = False
                    self.selected_unit = clicked_unit
                    self.selected_unit.is_selected = True
            elif event.button == 3 and self.selected_unit:
                target_unit = self.get_unit_at(map_x, map_y, self.enemy_squad)
                if target_unit and self.game_map.tiles[map_x][map_y].is_visible:
                    if math.dist((self.selected_unit.x, self.selected_unit.y), (target_unit.x, target_unit.y)) < 1.5:
                        self.handle_melee_attack(self.selected_unit, target_unit)
                    else:
                        self.handle_ranged_attack(self.selected_unit, target_unit)
                elif not self.game_map.tiles[map_x][map_y].is_wall:
                    occupied_nodes = { (u.x, u.y) for u in self.player_squad if u is not self.selected_unit }
                    if (map_x, map_y) in occupied_nodes: return
                    path = self.astar.find_path((self.selected_unit.x, self.selected_unit.y), (map_x, map_y), occupied_nodes)
                    if path: self.selected_unit.path = path[1:]

    def handle_camera_edge_scroll(self):
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > settings.SCREEN_WIDTH - 20: self.camera.scroll(dx=settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[0] < settings.SIDE_PANEL_WIDTH + 20 and mouse_pos[0] > settings.SIDE_PANEL_WIDTH:
            self.camera.scroll(dx=-settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[1] < 20: self.camera.scroll(dy=-settings.CAMERA_SCROLL_SPEED)
        if mouse_pos[1] > settings.SCREEN_HEIGHT - 20: self.camera.scroll(dy=settings.CAMERA_SCROLL_SPEED)

    def try_overwatch(self):
        if self.selected_unit and self.selected_unit.ap >= settings.OVERWATCH_COST and not self.selected_unit.is_on_overwatch:
            self.selected_unit.is_on_overwatch = True
            self.selected_unit.ap -= settings.OVERWATCH_COST

    def try_heal(self):
        if self.selected_unit and self.selected_unit.ap >= settings.HEAL_COST:
            for unit in self.player_squad:
                if unit is not self.selected_unit and unit.is_alive and unit.hp < settings.UNIT_MAX_HP:
                     if math.dist((self.selected_unit.x, self.selected_unit.y), (unit.x, unit.y)) < 1.5:
                        self.handle_heal(self.selected_unit, unit)
                        break
    
    def handle_heal(self, healer, target):
        healer.ap -= settings.HEAL_COST
        healer.heals_given += 1
        target.heal(settings.HEAL_AMOUNT)

    def get_unit_at(self, x, y, squad):
        for unit in squad:
            if unit.is_alive and unit.x == x and unit.y == y: return unit
        return None

    def perform_skill_check(self, attacker, skill_bonus, target_pos):
        roll = random.randint(1, 20)
        total = roll + skill_bonus
        if total >= settings.TARGET_DC_BASE:
            self.display_skill_check("Success!", target_pos, settings.COLOR_SUCCESS)
            return True
        else:
            self.display_skill_check("Miss!", target_pos, settings.COLOR_FAIL)
            return False

    def display_skill_check(self, message, pos, color):
        self.skill_check_messages.append({
            'text': message, 'pos': pos, 'timer': 60, 'color': color
        })

    def handle_ranged_attack(self, attacker, target):
        if attacker.ap < settings.SHOOT_COST: return
        attacker.shots_taken += 1
        attacker.is_on_overwatch = False; attacker.has_fired_overwatch = False
        attacker.ap -= settings.SHOOT_COST
        all_units = self.player_squad + self.enemy_squad
        los_path = self.game_map.get_line_of_sight((attacker.x, attacker.y), (target.x, target.y), all_units)
        if los_path and los_path[-1] == (target.x, target.y):
            if self.perform_skill_check(attacker, attacker.ranged_skill, (target.x, target.y)):
                attacker.shots_hit += 1
                damage = settings.LASER_DAMAGE if attacker.team == 'player' else settings.ENEMY_LASER_DAMAGE
                sounds.SOUNDS['laser'].play()
                was_alive = target.is_alive
                target.take_damage(damage)
                if was_alive and not target.is_alive:
                    attacker.kills += 1
                self.laser_effects.append(((attacker.x, attacker.y), (target.x, target.y), 30))
                self.check_game_over()
    
    def handle_melee_attack(self, attacker, target):
        if attacker.ap < settings.MELEE_COST: return
        attacker.shots_taken += 1
        attacker.is_on_overwatch = False; attacker.has_fired_overwatch = False
        attacker.ap -= settings.MELEE_COST
        if self.perform_skill_check(attacker, attacker.melee_skill, (target.x, target.y)):
             attacker.shots_hit += 1
             was_alive = target.is_alive
             target.take_damage(settings.MELEE_DAMAGE)
             if was_alive and not target.is_alive:
                 attacker.kills += 1
             self.check_game_over()

    def check_game_over(self):
        if not any(u.is_alive for u in self.player_squad):
            self.game_over_message = "DEFEAT"
            self.game_state = 'GAME_OVER'
        elif not any(u.is_alive for u in self.enemy_squad):
            self.game_over_message = "VICTORY"
            self.game_state = 'GAME_OVER'

    def update(self):
        if self.game_state in ['HOME_SCREEN', 'GAME_OVER']: return
        self.handle_camera_edge_scroll()

        if self.game_state == 'PLAYER_TURN':
            if self.selected_unit and self.selected_unit.path:
                visible_enemies_before_move = {e for e in self.enemy_squad if e.is_alive and self.game_map.tiles[e.x][e.y].is_visible}
                moved = self.selected_unit.move_along_path()
                if moved:
                    self.game_map.update_fov(self.player_squad)
                    visible_enemies_after_move = {e for e in self.enemy_squad if e.is_alive and self.game_map.tiles[e.x][e.y].is_visible}
                    if visible_enemies_after_move - visible_enemies_before_move:
                        self.selected_unit.path = [] 
        
        elif self.game_state == 'ENEMY_TURN' and not self.game_over_message:
            self.run_enemy_ai()

        self.skill_check_messages = [m for m in self.skill_check_messages if m['timer'] > 0]
        for m in self.skill_check_messages: m['timer'] -= 1
        self.laser_effects = [(s, e, t - 1) for s, e, t in self.laser_effects if t > 1]
    
    def check_overwatch(self, moved_enemy):
        for player_unit in self.player_squad:
            if player_unit.is_alive and player_unit.is_on_overwatch and not player_unit.has_fired_overwatch:
                if self.game_map.tiles[moved_enemy.x][moved_enemy.y].is_visible:
                    all_units = self.player_squad + self.enemy_squad
                    los_path = self.game_map.get_line_of_sight((player_unit.x, player_unit.y), (moved_enemy.x, moved_enemy.y), all_units)
                    if los_path and los_path[-1] == (moved_enemy.x, moved_enemy.y):
                        player_unit.shots_taken += 1
                        if self.perform_skill_check(player_unit, player_unit.ranged_skill, (moved_enemy.x, moved_enemy.y)):
                            player_unit.shots_hit += 1
                            sounds.SOUNDS['laser'].play()
                            was_alive = moved_enemy.is_alive
                            moved_enemy.take_damage(settings.LASER_DAMAGE)
                            if was_alive and not moved_enemy.is_alive:
                                player_unit.kills += 1
                            self.laser_effects.append(((player_unit.x, player_unit.y), (moved_enemy.x, moved_enemy.y), 30))
                            player_unit.has_fired_overwatch = True; player_unit.is_on_overwatch = False
                            self.check_game_over()
                        
    def run_enemy_ai(self):
        time.sleep(0.1)
        enemy_visible_tiles = self.game_map.calculate_visible_tiles(self.enemy_squad)
        visible_players = [p for p in self.player_squad if p.is_alive and (p.x, p.y) in enemy_visible_tiles]
        if visible_players:
            self.enemy_squad_target = min(visible_players, key=lambda p: p.hp)
            self.last_known_player_pos = (self.enemy_squad_target.x, self.enemy_squad_target.y)
            self.enemy_search_pos = None
        else: 
            self.enemy_squad_target = None

        destination = None
        if self.enemy_squad_target:
            destination = (self.enemy_squad_target.x, self.enemy_squad_target.y)
        elif self.last_known_player_pos:
            destination = self.last_known_player_pos
        else:
            if self.enemy_search_pos is None or all(math.dist((u.x, u.y), self.enemy_search_pos) < 3 for u in self.enemy_squad if u.is_alive):
                self.enemy_search_pos = random.choice(self.game_map.spawn_points)
            destination = self.enemy_search_pos

        acted = False
        for unit in self.enemy_squad:
            if unit.is_alive and unit.ap > 0:
                if self.enemy_squad_target and math.dist((unit.x, unit.y), (self.enemy_squad_target.x, self.enemy_squad_target.y)) < 1.5 and unit.ap >= settings.MELEE_COST:
                    self.handle_melee_attack(unit, self.enemy_squad_target); acted = True; break
                elif self.enemy_squad_target and unit.ap >= settings.SHOOT_COST:
                    self.handle_ranged_attack(unit, self.enemy_squad_target); acted = True; break
                elif destination and unit.ap >= settings.MOVE_COST:
                    if self.last_known_player_pos and (unit.x, unit.y) == self.last_known_player_pos: self.last_known_player_pos = None
                    occupied_nodes = { (u.x, u.y) for u in self.enemy_squad if u is not unit }
                    path = self.astar.find_path((unit.x, unit.y), destination, occupied_nodes)
                    if path and len(path) > 1:
                        unit.x, unit.y = path[1]; unit.ap -= settings.MOVE_COST; sounds.SOUNDS['move'].play()
                        self.check_overwatch(unit); acted = True; break
                unit.ap = 0
        if not acted: self.end_enemy_turn()

    def start_player_turn(self):
        self.game_state = 'PLAYER_TURN'; self.selected_unit = None
        for unit in self.player_squad:
            if unit.is_alive: unit.ap = settings.UNIT_MAX_AP; unit.has_fired_overwatch = False
        self.game_map.update_fov(self.player_squad)

    def end_player_turn(self):
        self.game_state = 'ENEMY_TURN'; self.enemy_squad_target = None
        for unit in self.enemy_squad:
            if unit.is_alive: unit.ap = settings.UNIT_MAX_AP

    def end_enemy_turn(self):
        self.turn_number += 1; self.start_player_turn()
    
    def draw_home_screen(self):
        self.screen.fill(settings.COLOR_DARK_GRAY)
        title_text = self.FONT_L.render("Tactical Squad Game", True, settings.COLOR_WHITE)
        title_rect = title_text.get_rect(center=(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2 - 200))
        self.screen.blit(title_text, title_rect)
        instructions = ["INSTRUCTIONS", "", "Select Unit: Left-Click or Press Keys 1-4", "Move Unit: Right-Click on a valid floor tile",
                        "Attack: Right-Click on a visible enemy", "Melee: Right-Click an ADJACENT enemy", "Heal: Press 'H' next to a friendly",
                        "Overwatch: Click button or Press 'O' (costs 3 AP)", "End Turn: Click the End Turn button",
                        "Scroll Map: Arrow Keys or move mouse to screen edge", "Jump to Map Location: Click on the minimap", "", "Press any key to start..."]
        for i, line in enumerate(instructions):
            line_text = self.FONT_M.render(line, True, settings.COLOR_WHITE)
            line_rect = line_text.get_rect(center=(settings.SCREEN_WIDTH / 2, settings.SCREEN_HEIGHT / 2 - 80 + i * 25))
            self.screen.blit(line_text, line_rect)

    def draw_game_world(self):
        # --- FIX: Draw all game world elements to the game_surface ---
        self.game_surface.fill(settings.COLOR_BLACK)
        game_time = pygame.time.get_ticks()

        self.game_map.draw(self.game_surface, self.camera)
        for unit in self.player_squad + self.enemy_squad:
            unit.draw(self.game_surface, self.camera, self.FONT_S, game_time)
        if self.selected_unit: self.selected_unit.draw_path(self.game_surface, self.camera)
        
        for start, end, timer in self.laser_effects:
            start_pos = self.camera.apply_coords(start[0], start[1]); end_pos = self.camera.apply_coords(end[0], end[1])
            start_center = (start_pos[0] + settings.TILE_SIZE // 2, start_pos[1] + settings.TILE_SIZE // 2)
            end_center = (end_pos[0] + settings.TILE_SIZE // 2, end_pos[1] + settings.TILE_SIZE // 2)
            pygame.draw.line(self.game_surface, settings.COLOR_LASER, start_center, end_center, 3)
        
        for msg in self.skill_check_messages:
            pos_x, pos_y = self.camera.apply_coords(msg['pos'][0], msg['pos'][1])
            text = self.FONT_M.render(msg['text'], True, msg['color'])
            alpha = int(255 * (msg['timer'] / 60))
            text.set_alpha(alpha)
            text_rect = text.get_rect(center=(pos_x + settings.TILE_SIZE // 2, pos_y - 20))
            self.game_surface.blit(text, text_rect)

        # --- FIX: Blit the game surface to the main screen, offset by the panel width ---
        self.screen.blit(self.game_surface, (settings.SIDE_PANEL_WIDTH, 0))

        self.draw_squad_ui(); self.draw_bottom_ui()

        if self.game_state == 'GAME_OVER': self.draw_game_over()
    
    def draw_game_over(self):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180));
        text = self.FONT_L.render(self.game_over_message, True, settings.COLOR_WHITE)
        text_rect = text.get_rect(center=(settings.SCREEN_WIDTH/2, settings.SCREEN_HEIGHT/2 - 150))
        overlay.blit(text, text_rect)
        
        # Awards
        awards = []
        if any(u.kills > 0 for u in self.player_squad):
            killer = max(self.player_squad, key=lambda u: u.kills)
            if killer.kills > 0: awards.append(f"Commando: {killer.name} ({killer.kills} kills)")
        if any(u.distance_travelled > 0 for u in self.player_squad):
            runner = max(self.player_squad, key=lambda u: u.distance_travelled)
            if runner.distance_travelled > 0: awards.append(f"Marathoner: {runner.name} ({int(runner.distance_travelled)}m)")
        if any(u.heals_given > 0 for u in self.player_squad):
            medic = max(self.player_squad, key=lambda u: u.heals_given)
            if medic.heals_given > 0: awards.append(f"Medic: {medic.name} ({medic.heals_given} heals)")
        best_marksman = None; best_accuracy = -1
        for u in self.player_squad:
            if u.shots_taken > 0:
                accuracy = u.shots_hit / u.shots_taken
                if accuracy > best_accuracy: best_accuracy = accuracy; best_marksman = u
        if best_marksman: awards.append(f"Marksman: {best_marksman.name} ({best_accuracy:.0%})")
        
        y_offset = settings.SCREEN_HEIGHT/2 - 80
        if awards:
            award_title_text = self.FONT_M.render("--- AWARDS ---", True, settings.COLOR_WHITE)
            award_title_rect = award_title_text.get_rect(center=(settings.SCREEN_WIDTH/2, y_offset))
            overlay.blit(award_title_text, award_title_rect)
            y_offset += 40
            for i, award_str in enumerate(awards):
                award_text = self.FONT_M.render(award_str, True, settings.COLOR_LASER)
                award_rect = award_text.get_rect(center=(settings.SCREEN_WIDTH/2, y_offset + i * 30))
                overlay.blit(award_text, award_rect)

        prompt_text = self.FONT_M.render("Press any key to return to the main menu.", True, settings.COLOR_WHITE)
        prompt_rect = prompt_text.get_rect(center=(settings.SCREEN_WIDTH/2, settings.SCREEN_HEIGHT - 150))
        overlay.blit(prompt_text, prompt_rect)

        self.screen.blit(overlay, (0,0))
    
    def draw_squad_ui(self):
        panel_rect = pygame.Rect(0, 0, settings.SIDE_PANEL_WIDTH, settings.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, settings.COLOR_UI_BG, panel_rect)
        pygame.draw.rect(self.screen, settings.COLOR_UI_BORDER, panel_rect, 2)
        start_y = 20
        for unit in self.player_squad:
            box_height = 80
            unit_box_rect = pygame.Rect(10, start_y, settings.SIDE_PANEL_WIDTH - 20, box_height)
            box_color = (40, 40, 70) if unit.is_selected else settings.COLOR_DARK_GRAY
            pygame.draw.rect(self.screen, box_color, unit_box_rect, border_radius=5)
            pygame.draw.rect(self.screen, settings.COLOR_UI_BORDER, unit_box_rect, 1, border_radius=5)
            name_text = self.FONT_M.render(f"{unit.number}. {unit.name}", True, settings.COLOR_WHITE)
            self.screen.blit(name_text, (20, start_y + 5))
            hp_text = self.FONT_S.render(f"HP: {unit.hp}/{settings.UNIT_MAX_HP}", True, settings.COLOR_PLAYER_LIGHT)
            self.screen.blit(hp_text, (20, start_y + 30))
            ap_text = self.FONT_S.render(f"AP: {unit.ap}/{settings.UNIT_MAX_AP}", True, settings.COLOR_PLAYER_LIGHT)
            self.screen.blit(ap_text, (120, start_y + 30))
            if not unit.is_alive: status_text = self.FONT_M.render("KIA", True, settings.COLOR_ENEMY)
            elif unit.is_on_overwatch: status_text = self.FONT_M.render("Overwatch", True, settings.COLOR_OVERWATCH)
            else: status_text = None
            if status_text: self.screen.blit(status_text, (20, start_y + 50))
            start_y += box_height + 10

    def draw_minimap(self):
        self.minimap_surface.fill(settings.COLOR_UI_BG)
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                if self.game_map.tiles[x][y].is_explored:
                    color = settings.COLOR_WALL if self.game_map.tiles[x][y].is_wall else settings.COLOR_FLOOR_EXPLORED
                    pygame.draw.rect(self.minimap_surface, color, (x*settings.MINIMAP_SCALE, y*settings.MINIMAP_SCALE, settings.MINIMAP_SCALE, settings.MINIMAP_SCALE))
        for unit in self.player_squad + self.enemy_squad:
            if unit.is_alive and self.game_map.tiles[unit.x][unit.y].is_visible:
                color = settings.COLOR_PLAYER_LIGHT if unit.team == 'player' else settings.COLOR_ENEMY_LIGHT
                pygame.draw.rect(self.minimap_surface, color, (unit.x*settings.MINIMAP_SCALE, unit.y*settings.MINIMAP_SCALE, settings.MINIMAP_SCALE, settings.MINIMAP_SCALE))
        pygame.draw.rect(self.minimap_surface, settings.COLOR_UI_BORDER, self.minimap_surface.get_rect(), 2)
        self.screen.blit(self.minimap_surface, self.minimap_rect)

    def draw_bottom_ui(self):
        ui_panel = pygame.Rect(0, settings.SCREEN_HEIGHT - 100, settings.SCREEN_WIDTH, 100)
        pygame.draw.rect(self.screen, settings.COLOR_UI_BG, ui_panel); pygame.draw.rect(self.screen, settings.COLOR_UI_BORDER, ui_panel, 2)
        turn_text_str = f"Turn {self.turn_number}: {self.game_state.replace('_', ' ')}"; turn_text = self.FONT_M.render(turn_text_str, True, settings.COLOR_WHITE)
        self.screen.blit(turn_text, (settings.SIDE_PANEL_WIDTH + 20, settings.SCREEN_HEIGHT - 85))
        
        enemies_left = len([u for u in self.enemy_squad if u.is_alive])
        enemy_text = self.FONT_M.render(f"Enemies Remaining: {enemies_left}", True, settings.COLOR_WHITE)
        self.screen.blit(enemy_text, (settings.SIDE_PANEL_WIDTH + 20, settings.SCREEN_HEIGHT - 45))

        mouse_pos = pygame.mouse.get_pos()
        button_color = settings.COLOR_BUTTON_HOVER if self.end_turn_button.collidepoint(mouse_pos) else settings.COLOR_BUTTON
        pygame.draw.rect(self.screen, button_color, self.end_turn_button, border_radius=5)
        button_text = self.FONT_M.render("End Turn", True, settings.COLOR_BUTTON_TEXT)
        text_rect = button_text.get_rect(center=self.end_turn_button.center); self.screen.blit(button_text, text_rect)
        can_overwatch = self.selected_unit and self.selected_unit.ap >= settings.OVERWATCH_COST and not self.selected_unit.is_on_overwatch
        button_color = settings.COLOR_BUTTON_HOVER if self.overwatch_button.collidepoint(mouse_pos) and can_overwatch else settings.COLOR_BUTTON
        pygame.draw.rect(self.screen, button_color, self.overwatch_button, border_radius=5)
        text_color = settings.COLOR_BUTTON_TEXT if can_overwatch else settings.COLOR_GRAY
        button_text = self.FONT_M.render("Overwatch", True, text_color)
        text_rect = button_text.get_rect(center=self.overwatch_button.center); self.screen.blit(button_text, text_rect)
        self.draw_minimap()
