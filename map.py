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
                    rect = pygame.Rect(pos_x, pos_y, settings.TILE_SIZE, settings.TILE_SIZE)
                    if tile.is_visible:
                        color = settings.COLOR_WALL if tile.is_wall else settings.COLOR_FLOOR_VISIBLE
                    else:
                        color = settings.COLOR_WALL if tile.is_wall else settings.COLOR_FLOOR_EXPLORED
                    pygame.draw.rect(surface, color, rect)

    def is_in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_line_of_sight(self, start_pos, end_pos, all_units):
        """
        Bresenham's line algorithm. Checks for walls and other units.
        `all_units` should be a list of all units on the map.
        """
        x1, y1 = start_pos
        x2, y2 = end_pos
        dx, dy = x2 - x1, y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0: return []
        x_inc, y_inc = dx / steps, dy / steps
        
        line = []
        unit_positions = { (unit.x, unit.y) for unit in all_units if unit.is_alive }

        for i in range(int(steps) + 1):
            x, y = int(round(x1 + i * x_inc)), int(round(y1 + i * y_inc))
            current_pos = (x, y)
            if not self.is_in_bounds(x,y): break
            
            line.append(current_pos)
            
            # Check for obstacles (walls or units), ignoring start and end points
            if current_pos != start_pos and current_pos != end_pos:
                if self.tiles[x][y].is_wall or current_pos in unit_positions:
                    break # Line is blocked
        return line

    def update_fov(self, units):
        """Updates the VISIBLE and EXPLORED state of tiles based on a squad's vision."""
        for row in self.tiles:
            for tile in row:
                tile.is_visible = False
        
        visible_tiles = self.calculate_visible_tiles(units)
        for x, y in visible_tiles:
            if self.is_in_bounds(x, y):
                self.tiles[x][y].is_visible = True
                self.tiles[x][y].is_explored = True

    def calculate_visible_tiles(self, units):
        """Calculates and returns a set of tile coordinates visible to a squad."""
        visible_coords = set()
        # For FOV calculation, we only care about walls, not other units blocking sight
        empty_unit_list = [] 
        for unit in units:
            if not unit.is_alive: continue
            for x in range(unit.x - settings.UNIT_VISION_RADIUS, unit.x + settings.UNIT_VISION_RADIUS + 1):
                for y in range(unit.y - settings.UNIT_VISION_RADIUS, unit.y + settings.UNIT_VISION_RADIUS + 1):
                    if self.is_in_bounds(x,y) and math.dist((unit.x, unit.y), (x,y)) <= settings.UNIT_VISION_RADIUS:
                        # Pass an empty list so other units don't block general vision
                        line = self.get_line_of_sight((unit.x, unit.y), (x, y), empty_unit_list)
                        if line and line[-1] == (x,y):
                            for lx, ly in line:
                                visible_coords.add((lx, ly))
        return visible_coords
