import pygame
import random
import math
import heapq
import numpy
import time

# --- Pygame Initialization ---
pygame.mixer.pre_init(44100, -16, 2, 512) # Setup mixer for less latency
pygame.init()
pygame.font.init()

# --- Game Constants ---
# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
# Map dimensions
MAP_WIDTH = 50
MAP_HEIGHT = 40
# Tile and unit sizes
TILE_SIZE = 40
UNIT_RADIUS = TILE_SIZE // 2 - 5
# Minimap dimensions
MINIMAP_SCALE = 5
MINIMAP_WIDTH = MAP_WIDTH * MINIMAP_SCALE
MINIMAP_HEIGHT = MAP_HEIGHT * MINIMAP_SCALE
# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 100, 100)
COLOR_DARK_GRAY = (40, 40, 40)
COLOR_PLAYER = (60, 140, 255)
COLOR_ENEMY = (255, 80, 80)
COLOR_PLAYER_LIGHT = (120, 180, 255)
COLOR_ENEMY_LIGHT = (255, 140, 140)
COLOR_WALL = (140, 140, 140)
COLOR_FLOOR_EXPLORED = (70, 70, 70)
COLOR_FLOOR_VISIBLE = (110, 110, 110)
COLOR_LASER = (255, 255, 0)
COLOR_UI_BG = (20, 20, 20)
COLOR_UI_BORDER = (80, 80, 80)
COLOR_BUTTON = (50, 50, 90)
COLOR_BUTTON_HOVER = (80, 80, 130)
COLOR_BUTTON_TEXT = (200, 200, 255)

# --- Game Settings ---
SQUAD_SIZE = 4
UNIT_MAX_HP = 100
UNIT_MAX_AP = 10
UNIT_VISION_RADIUS = 8
MOVE_COST = 1
SHOOT_COST = 5
LASER_DAMAGE = 35

# --- Pygame Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tactical Squad Game")
clock = pygame.time.Clock()
FONT_S = pygame.font.SysFont('Consolas', 16)
FONT_M = pygame.font.SysFont('Consolas', 20)
FONT_L = pygame.font.SysFont('Consolas', 32, bold=True)

# --- Sound Generation ---
def generate_sound(frequency, duration, attack_time=0.01, decay_time=0.1, sound_type='sine'):
    """Generates a pygame sound object with an ADSR-like envelope."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    t = numpy.linspace(0, duration, num_samples, False)

    # Generate wave
    if sound_type == 'sine':
        wave = numpy.sin(frequency * t * 2 * numpy.pi)
    elif sound_type == 'square':
        wave = numpy.sign(numpy.sin(frequency * t * 2 * numpy.pi))
    elif sound_type == 'noise':
        wave = numpy.random.uniform(-1, 1, num_samples)
    else: # Sawtooth
        wave = 2 * (t * frequency - numpy.floor(0.5 + t * frequency))

    # Envelope
    attack_samples = int(sample_rate * attack_time)
    decay_samples = int(sample_rate * decay_time)

    if attack_samples > 0:
        attack = numpy.linspace(0, 1, attack_samples)
        wave[:attack_samples] *= attack
    
    if decay_samples > 0:
        sustain_samples = num_samples - attack_samples
        decay = numpy.exp(-numpy.linspace(0, 5, sustain_samples))
        wave[attack_samples:] *= decay

    # Ensure max amplitude is 1
    wave *= 32767 / numpy.max(numpy.abs(wave))
    wave = wave.astype(numpy.int16)

    # Convert to stereo
    stereo_wave = numpy.array([wave, wave]).T
    
    # Ensure the array is C-contiguous
    stereo_wave_contiguous = numpy.ascontiguousarray(stereo_wave)
    return pygame.sndarray.make_sound(stereo_wave_contiguous)


# --- Create Sound Effects ---
SOUNDS = {
    'laser': generate_sound(1200, 0.2, decay_time=0.2, sound_type='sawtooth'),
    'hit': generate_sound(400, 0.3, decay_time=0.3, sound_type='noise'),
    'death': generate_sound(200, 0.8, decay_time=0.8, sound_type='noise'),
    'move': generate_sound(800, 0.05, decay_time=0.05, sound_type='square')
}
SOUNDS['move'].set_volume(0.5)

# --- Classes ---

class Tile:
    """Represents a single tile on the map."""
    def __init__(self, x, y, is_wall=False):
        self.x = x
        self.y = y
        self.is_wall = is_wall
        self.is_visible = False
        self.is_explored = False

class Unit:
    """Represents a player or enemy unit."""
    def __init__(self, x, y, team, game_map):
        self.x = x
        self.y = y
        self.team = team
        self.hp = UNIT_MAX_HP
        self.ap = UNIT_MAX_AP
        self.is_selected = False
        self.is_alive = True
        self.game_map = game_map
        self.path = []

    def draw(self, surface, camera):
        """Draws the unit on the main game surface."""
        if not self.is_alive or not self.game_map.tiles[self.x][self.y].is_visible:
            return

        pos_x, pos_y = camera.apply_coords(self.x, self.y)
        center = (pos_x + TILE_SIZE // 2, pos_y + TILE_SIZE // 2)
        
        color = COLOR_PLAYER if self.team == 'player' else COLOR_ENEMY
        
        pygame.draw.circle(surface, color, center, UNIT_RADIUS)
        if self.is_selected:
            pygame.draw.circle(surface, COLOR_WHITE, center, UNIT_RADIUS + 2, 2)
        
        # Health bar
        hp_rect_bg = pygame.Rect(pos_x, pos_y + TILE_SIZE - 8, TILE_SIZE, 6)
        hp_percent = max(0, self.hp / UNIT_MAX_HP)
        hp_rect_fg = pygame.Rect(pos_x, pos_y + TILE_SIZE - 8, TILE_SIZE * hp_percent, 6)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, hp_rect_bg)
        pygame.draw.rect(surface, COLOR_PLAYER_LIGHT if self.team == 'player' else COLOR_ENEMY_LIGHT, hp_rect_fg)

    def draw_path(self, surface, camera):
        """Draws the unit's intended movement path."""
        if self.path and len(self.path) > 1:
            points = []
            for node in self.path:
                pos_x, pos_y = camera.apply_coords(node[0], node[1])
                points.append((pos_x + TILE_SIZE // 2, pos_y + TILE_SIZE // 2))
            pygame.draw.lines(surface, COLOR_PLAYER_LIGHT, False, points, 2)

    def move_along_path(self):
        """Moves the unit one step along its path if it has AP."""
        if self.path and self.ap >= MOVE_COST:
            next_pos = self.path.pop(0)
            self.x, self.y = next_pos
            self.ap -= MOVE_COST
            SOUNDS['move'].play()
            return True
        self.path = []
        return False
    
    def take_damage(self, amount):
        """Applies damage and plays hit sound."""
        self.hp -= amount
        SOUNDS['hit'].play()
        if self.hp <= 0:
            self.hp = 0
            self.die()

    def die(self):
        """Handles the unit's death."""
        if self.is_alive:
            self.is_alive = False
            self.is_selected = False
            SOUNDS['death'].play()

class GameMap:
    """Manages the map grid and tile properties."""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = self._generate_map()

    def _generate_map(self):
        """Generates a random map with rooms and corridors."""
        tiles = [[Tile(x, y, is_wall=True) for y in range(self.height)] for x in range(self.width)]
        rooms = []
        num_rooms = 15
        for _ in range(num_rooms):
            w = random.randint(5, 10)
            h = random.randint(5, 10)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)
            new_room = pygame.Rect(x, y, w, h)
            failed = False
            for other_room in rooms:
                if new_room.colliderect(other_room.inflate(2, 2)):
                    failed = True
                    break
            if not failed:
                for i in range(new_room.left, new_room.right):
                    for j in range(new_room.top, new_room.bottom):
                        tiles[i][j].is_wall = False
                if rooms:
                    prev_room = rooms[-1]
                    self._create_tunnel(tiles, prev_room.centerx, prev_room.centery, new_room.centerx, new_room.centery)
                rooms.append(new_room)
        self.spawn_points = [room.center for room in rooms] if rooms else [(self.width//2, self.height//2)]
        return tiles

    def _create_tunnel(self, tiles, x1, y1, x2, y2):
        """Carves a tunnel between two points."""
        if random.random() < 0.5:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                tiles[x][y1].is_wall = False
            for y in range(min(y1, y2), max(y1, y2) + 1):
                tiles[x2][y].is_wall = False
        else:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                tiles[x1][y].is_wall = False
            for x in range(min(x1, x2), max(x1, x2) + 1):
                tiles[x][y2].is_wall = False

    def draw(self, surface, camera):
        """Draws the visible and explored parts of the map."""
        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                if tile.is_explored:
                    pos_x, pos_y = camera.apply_coords(x, y)
                    rect = pygame.Rect(pos_x, pos_y, TILE_SIZE, TILE_SIZE)
                    if tile.is_visible:
                        color = COLOR_WALL if tile.is_wall else COLOR_FLOOR_VISIBLE
                    else:
                        color = COLOR_WALL if tile.is_wall else COLOR_FLOOR_EXPLORED
                    pygame.draw.rect(surface, color, rect)

    def is_in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_line_of_sight(self, start_x, start_y, end_x, end_y):
        """Bresenham's line algorithm to check for line of sight."""
        x1, y1, x2, y2 = start_x, start_y, end_x, end_y
        dx, dy = x2 - x1, y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0: return []
        x_inc, y_inc = dx / steps, dy / steps
        line = []
        for i in range(int(steps) + 1):
            x, y = int(round(x1 + i * x_inc)), int(round(y1 + i * y_inc))
            if not self.is_in_bounds(x,y): break
            line.append((x,y))
            if self.tiles[x][y].is_wall: break
        return line

    def update_fov(self, units):
        """Updates the field of view for all units of a team."""
        for row in self.tiles:
            for tile in row:
                tile.is_visible = False
        for unit in units:
            if not unit.is_alive: continue
            for x in range(unit.x - UNIT_VISION_RADIUS, unit.x + UNIT_VISION_RADIUS + 1):
                for y in range(unit.y - UNIT_VISION_RADIUS, unit.y + UNIT_VISION_RADIUS + 1):
                    if self.is_in_bounds(x,y) and math.dist((unit.x, unit.y), (x,y)) <= UNIT_VISION_RADIUS:
                        line = self.get_line_of_sight(unit.x, unit.y, x, y)
                        if line and line[-1] == (x,y):
                            for lx, ly in line:
                                self.tiles[lx][ly].is_visible = True
                                self.tiles[lx][ly].is_explored = True

class Camera:
    """Manages the game's viewport."""
    def __init__(self, map_pixel_width, map_pixel_height):
        self.x, self.y = 0, 0
        self.width, self.height = SCREEN_WIDTH, SCREEN_HEIGHT
        self.map_pixel_width, self.map_pixel_height = map_pixel_width, map_pixel_height
    
    def apply_coords(self, x, y):
        return x * TILE_SIZE - self.x, y * TILE_SIZE - self.y

    def center_on(self, unit):
        target_x = unit.x * TILE_SIZE - self.width // 2
        target_y = unit.y * TILE_SIZE - self.height // 2
        self.x = max(0, min(target_x, self.map_pixel_width - self.width))
        self.y = max(0, min(target_y, self.map_pixel_height - self.height))
        
class AStar:
    """A* pathfinding algorithm implementation."""
    def __init__(self, game_map):
        self.game_map = game_map
        self.neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start, end):
        frontier = [(0, start)]
        came_from, cost_so_far = {start: None}, {start: 0}
        while frontier:
            _, current = heapq.heappop(frontier)
            if current == end: break
            for dx, dy in self.neighbors:
                next_node = (current[0] + dx, current[1] + dy)
                if not self.game_map.is_in_bounds(next_node[0], next_node[1]) or self.game_map.tiles[next_node[0]][next_node[1]].is_wall: continue
                new_cost = cost_so_far[current] + 1
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + self.heuristic(end, next_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current
        path = []
        current = end
        while current != start:
            if current not in came_from: return []
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path

class Game:
    """Main game class that manages state, turns, and drawing."""
    def __init__(self):
        # Loop until a map with enough spawn points is generated.
        while True:
            self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
            if len(self.game_map.spawn_points) >= SQUAD_SIZE * 2:
                break
        
        self.camera = Camera(MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE)
        self.astar = AStar(self.game_map)
        self.player_squad, self.enemy_squad = [], []
        self._spawn_units()
        self.game_state = 'PLAYER_TURN'
        self.selected_unit = None
        self.laser_effects = []
        self.turn_number = 1
        self.minimap_surface = pygame.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT))
        self.end_turn_button = pygame.Rect(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 70, 200, 50)
        self.game_over_message = ""
        self.start_player_turn()

        # After the first turn starts, select the first player unit and center the camera.
        # This ensures the player starts with their squad visible and ready to command.
        if self.player_squad:
            self.selected_unit = self.player_squad[0]
            self.selected_unit.is_selected = True
            self.camera.center_on(self.selected_unit)

    def _find_spawn_tiles(self, start_x, start_y, count):
        """Finds a number of valid, non-wall spawn tiles around a starting point."""
        spawn_tiles = []
        # Check the starting tile itself first
        if self.game_map.is_in_bounds(start_x, start_y) and not self.game_map.tiles[start_x][start_y].is_wall:
            spawn_tiles.append((start_x, start_y))
            if len(spawn_tiles) == count:
                return spawn_tiles

        # Search in an expanding radius for the rest
        for radius in range(1, max(self.game_map.width, self.game_map.height)):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Check only the perimeter of the current search box
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    
                    x, y = start_x + dx, start_y + dy
                    
                    tile_pos = (x, y)
                    if self.game_map.is_in_bounds(x, y) and not self.game_map.tiles[x][y].is_wall and tile_pos not in spawn_tiles:
                        spawn_tiles.append(tile_pos)
                        if len(spawn_tiles) == count:
                            return spawn_tiles
        return spawn_tiles # Return what was found, even if less than count

    def _spawn_units(self):
        """Spawns units for each team, clustered in their own starting rooms."""
        # Get the center of the first room for the player squad
        player_start_center = self.game_map.spawn_points[0]
        # Find valid spawn tiles around that center
        player_spawns = self._find_spawn_tiles(player_start_center[0], player_start_center[1], SQUAD_SIZE)
        # Spawn player units
        for x, y in player_spawns:
            self.player_squad.append(Unit(x, y, 'player', self.game_map))

        # Get the center of the last (likely most distant) room for the enemy squad
        enemy_start_center = self.game_map.spawn_points[-1]
        # Find valid spawn tiles for them
        enemy_spawns = self._find_spawn_tiles(enemy_start_center[0], enemy_start_center[1], SQUAD_SIZE)
        # Spawn enemy units
        for x, y in enemy_spawns:
            self.enemy_squad.append(Unit(x, y, 'enemy', self.game_map))


    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_input(event)
            self.update()
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    def handle_input(self, event):
        if self.game_state != 'PLAYER_TURN' or self.game_over_message: return
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.end_turn_button.collidepoint(mouse_pos):
                self.end_player_turn()
                return
            map_x, map_y = (mouse_pos[0] + self.camera.x) // TILE_SIZE, (mouse_pos[1] + self.camera.y) // TILE_SIZE
            if not self.game_map.is_in_bounds(map_x, map_y): return
            if event.button == 1:
                clicked_unit = self.get_unit_at(map_x, map_y, self.player_squad)
                if self.selected_unit: self.selected_unit.is_selected = False
                self.selected_unit = clicked_unit
                if self.selected_unit:
                    self.selected_unit.is_selected = True
                    self.camera.center_on(self.selected_unit)
            elif event.button == 3 and self.selected_unit:
                target_unit = self.get_unit_at(map_x, map_y, self.enemy_squad)
                if target_unit and self.game_map.tiles[map_x][map_y].is_visible:
                    self.handle_attack(self.selected_unit, target_unit)
                elif not self.game_map.tiles[map_x][map_y].is_wall:
                    path = self.astar.find_path((self.selected_unit.x, self.selected_unit.y), (map_x, map_y))
                    if path: self.selected_unit.path = path[1:]

    def get_unit_at(self, x, y, squad):
        for unit in squad:
            if unit.is_alive and unit.x == x and unit.y == y:
                return unit
        return None

    def handle_attack(self, attacker, target):
        if attacker.ap >= SHOOT_COST:
            los_path = self.game_map.get_line_of_sight(attacker.x, attacker.y, target.x, target.y)
            if los_path and los_path[-1] == (target.x, target.y):
                attacker.ap -= SHOOT_COST
                SOUNDS['laser'].play()
                target.take_damage(LASER_DAMAGE)
                self.laser_effects.append(((attacker.x, attacker.y), (target.x, target.y), 30))
                self.check_game_over()

    def check_game_over(self):
        if not any(u.is_alive for u in self.player_squad): self.game_over_message = "DEFEAT"
        elif not any(u.is_alive for u in self.enemy_squad): self.game_over_message = "VICTORY"

    def update(self):
        if self.game_state == 'PLAYER_TURN' and self.selected_unit and self.selected_unit.path:
            if self.selected_unit.move_along_path():
                self.game_map.update_fov(self.player_squad)
                self.camera.center_on(self.selected_unit)
        self.laser_effects = [(s, e, t - 1) for s, e, t in self.laser_effects if t > 1]
        if self.game_state == 'ENEMY_TURN' and not self.game_over_message:
            self.run_enemy_ai()

    def run_enemy_ai(self):
        time.sleep(0.1) # Small delay to make AI turn observable
        for unit in self.enemy_squad:
            if unit.is_alive and unit.ap > 0:
                visible_players = [p for p in self.player_squad if p.is_alive and self.game_map.tiles[p.x][p.y].is_visible]
                if visible_players and unit.ap >= SHOOT_COST:
                    target = min(visible_players, key=lambda p: math.dist((unit.x, unit.y), (p.x, p.y)))
                    self.handle_attack(unit, target)
                elif unit.ap >= MOVE_COST:
                    target = None
                    if visible_players:
                        target = min(visible_players, key=lambda p: math.dist((unit.x, unit.y), (p.x, p.y)))
                    if target:
                        path = self.astar.find_path((unit.x, unit.y), (target.x, target.y))
                        if path and len(path) > 1:
                            unit.x, unit.y = path[1]
                            unit.ap -= MOVE_COST
                    else: # Explore
                        unit.ap = 0 # Simple AI: just wait if no target
                else: unit.ap = 0
                self.game_map.update_fov(self.enemy_squad)
                return
        self.end_enemy_turn()

    def start_player_turn(self):
        self.game_state = 'PLAYER_TURN'
        if self.selected_unit: self.selected_unit.is_selected = False
        self.selected_unit = None
        for unit in self.player_squad:
            if unit.is_alive: unit.ap = UNIT_MAX_AP
        self.game_map.update_fov(self.player_squad)

    def end_player_turn(self):
        self.game_state = 'ENEMY_TURN'
        for unit in self.enemy_squad:
            if unit.is_alive: unit.ap = UNIT_MAX_AP
        self.game_map.update_fov(self.enemy_squad)

    def end_enemy_turn(self):
        self.turn_number += 1
        self.start_player_turn()

    def draw(self):
        screen.fill(COLOR_BLACK)
        self.game_map.draw(screen, self.camera)
        for unit in self.player_squad + self.enemy_squad:
            unit.draw(screen, self.camera)
        if self.selected_unit:
            self.selected_unit.draw_path(screen, self.camera)
        for start, end, timer in self.laser_effects:
            start_pos = self.camera.apply_coords(start[0], start[1])
            end_pos = self.camera.apply_coords(end[0], end[1])
            start_center = (start_pos[0] + TILE_SIZE // 2, start_pos[1] + TILE_SIZE // 2)
            end_center = (end_pos[0] + TILE_SIZE // 2, end_pos[1] + TILE_SIZE // 2)
            pygame.draw.line(screen, COLOR_LASER, start_center, end_center, 3)
        self.draw_ui()
        if self.game_over_message: self.draw_game_over()
    
    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        text = FONT_L.render(self.game_over_message, True, COLOR_WHITE)
        text_rect = text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        overlay.blit(text, text_rect)
        screen.blit(overlay, (0,0))
    
    def draw_minimap(self):
        self.minimap_surface.fill(COLOR_UI_BG)
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                if self.game_map.tiles[x][y].is_explored:
                    color = COLOR_WALL if self.game_map.tiles[x][y].is_wall else COLOR_FLOOR_EXPLORED
                    pygame.draw.rect(self.minimap_surface, color, (x*MINIMAP_SCALE, y*MINIMAP_SCALE, MINIMAP_SCALE, MINIMAP_SCALE))
        for unit in self.player_squad + self.enemy_squad:
            if unit.is_alive and self.game_map.tiles[unit.x][unit.y].is_visible:
                color = COLOR_PLAYER_LIGHT if unit.team == 'player' else COLOR_ENEMY_LIGHT
                pygame.draw.rect(self.minimap_surface, color, (unit.x*MINIMAP_SCALE, unit.y*MINIMAP_SCALE, MINIMAP_SCALE, MINIMAP_SCALE))
        pygame.draw.rect(self.minimap_surface, COLOR_UI_BORDER, self.minimap_surface.get_rect(), 2)
        screen.blit(self.minimap_surface, (SCREEN_WIDTH - MINIMAP_WIDTH - 10, 10))

    def draw_ui(self):
        ui_panel = pygame.Rect(0, SCREEN_HEIGHT - 100, SCREEN_WIDTH, 100)
        pygame.draw.rect(screen, COLOR_UI_BG, ui_panel)
        pygame.draw.rect(screen, COLOR_UI_BORDER, ui_panel, 2)
        turn_text_str = f"Turn {self.turn_number}: {self.game_state.replace('_', ' ')}"
        turn_text = FONT_M.render(turn_text_str, True, COLOR_WHITE)
        screen.blit(turn_text, (20, SCREEN_HEIGHT - 85))
        if self.selected_unit:
            info_text_hp = FONT_M.render(f"HP: {self.selected_unit.hp}/{UNIT_MAX_HP}", True, COLOR_PLAYER_LIGHT)
            info_text_ap = FONT_M.render(f"AP: {self.selected_unit.ap}/{UNIT_MAX_AP}", True, COLOR_PLAYER_LIGHT)
            screen.blit(info_text_hp, (20, SCREEN_HEIGHT - 60))
            screen.blit(info_text_ap, (20, SCREEN_HEIGHT - 35))
        mouse_pos = pygame.mouse.get_pos()
        button_color = COLOR_BUTTON_HOVER if self.end_turn_button.collidepoint(mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(screen, button_color, self.end_turn_button, border_radius=5)
        button_text = FONT_M.render("End Turn", True, COLOR_BUTTON_TEXT)
        text_rect = button_text.get_rect(center=self.end_turn_button.center)
        screen.blit(button_text, text_rect)
        self.draw_minimap()

if __name__ == '__main__':
    game = Game()
    game.run()
