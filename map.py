import pygame
import random
import math
from sprites import Tile
import settings

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
        num_rooms = 30
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
                        # Add some random cover objects
                        if random.random() < 0.1:
                            tiles[i][j].is_cover = True

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
                tiles[x][y1].is_wall = False; tiles[x][y1].is_cover = False
            for y in range(min(y1, y2), max(y1, y2) + 1):
                tiles[x2][y].is_wall = False; tiles[x2][y].is_cover = False
        else:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                tiles[x1][y].is_wall = False; tiles[x1][y].is_cover = False
            for x in range(min(x1, x2), max(x1, x2) + 1):
                tiles[x][y2].is_wall = False; tiles[x][y2].is_cover = False

    def draw(self, surface, camera):
        """Draws the visible and explored parts of the map."""
        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                if tile.is_explored:
                    pos_x, pos_y = camera.apply_coords(x, y)
                    rect = pygame.Rect(pos_x, pos_y, settings.TILE_SIZE, settings.TILE_SIZE)
                    if tile.is_visible:
                        color = settings.COLOR_WALL if tile.is_wall else settings.COLOR_FLOOR_VISIBLE
                        if tile.is_cover:
                           color = settings.COLOR_COVER
                    else:
                        color = settings.COLOR_WALL if tile.is_wall else settings.COLOR_FLOOR_EXPLORED
                        if tile.is_cover:
                           color = settings.COLOR_DARK_GRAY
                    
                    pygame.draw.rect(surface, color, rect)
                    if tile.is_cover: # Draw a smaller rect to indicate cover
                        cover_rect = pygame.Rect(pos_x + 5, pos_y + 5, settings.TILE_SIZE - 10, settings.TILE_SIZE - 10)
                        pygame.draw.rect(surface, settings.COLOR_GRAY, cover_rect, 3)


    def is_in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_line_of_sight(self, shooter, target_pos, all_units):
        x1, y1 = shooter.x, shooter.y
        x2, y2 = target_pos
        dx, dy = x2 - x1, y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0: return []
        x_inc, y_inc = dx / steps, dy / steps
        
        line = []
        unit_positions = { (unit.x, unit.y): unit for unit in all_units if unit.is_alive and unit is not shooter }

        for i in range(int(steps) + 1):
            x, y = int(round(x1 + i * x_inc)), int(round(y1 + i * y_inc))
            current_pos = (x, y)
            if not self.is_in_bounds(x,y): break
            line.append(current_pos)
            
            if current_pos == target_pos: continue
            
            tile = self.tiles[x][y]
            if tile.is_wall: return line # Blocked by high wall
            if tile.is_cover and shooter.posture == 'prone': return line # Prone shooter can't shoot over cover

            if current_pos in unit_positions:
                blocking_unit = unit_positions[current_pos]
                if tile.is_cover and blocking_unit.posture == 'prone':
                    continue # Can shoot over a prone unit in cover
                return line # Blocked by another unit
        return line

    def update_fov(self, units):
        for row in self.tiles:
            for tile in row:
                tile.is_visible = False
        
        visible_tiles = self.calculate_visible_tiles(units)
        for x, y in visible_tiles:
            if self.is_in_bounds(x, y):
                self.tiles[x][y].is_visible = True
                self.tiles[x][y].is_explored = True

    def calculate_visible_tiles(self, units):
        visible_coords = set()
        for unit in units:
            if not unit.is_alive: continue
            for x in range(unit.x - settings.UNIT_VISION_RADIUS, unit.x + settings.UNIT_VISION_RADIUS + 1):
                for y in range(unit.y - settings.UNIT_VISION_RADIUS, unit.y + settings.UNIT_VISION_RADIUS + 1):
                    if self.is_in_bounds(x,y) and math.dist((unit.x, unit.y), (x,y)) <= settings.UNIT_VISION_RADIUS:
                        line = self.get_line_of_sight(unit, (x, y), [])
                        if line and line[-1] == (x,y):
                            for lx, ly in line:
                                visible_coords.add((lx, ly))
        return visible_coords
