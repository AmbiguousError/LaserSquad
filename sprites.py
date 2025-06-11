import pygame
import settings
import sounds
import math

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
    def __init__(self, x, y, team, game_map, name=None, number=None):
        self.x = x
        self.y = y
        self.team = team
        self.hp = settings.UNIT_MAX_HP
        self.ap = settings.UNIT_MAX_AP
        self.is_selected = False
        self.is_alive = True
        self.game_map = game_map
        self.path = []
        self.is_on_overwatch = False
        self.has_fired_overwatch = False
        self.name = name
        self.number = number
        
        # Stats
        self.distance_travelled = 0
        self.shots_taken = 0
        self.shots_hit = 0
        self.kills = 0
        self.heals_given = 0

        if self.team == 'player':
            self.ranged_skill = settings.PLAYER_RANGED_SKILL
            self.melee_skill = settings.PLAYER_MELEE_SKILL
        else:
            self.ranged_skill = settings.ENEMY_RANGED_SKILL
            self.melee_skill = settings.ENEMY_MELEE_SKILL

    def draw(self, surface, camera, font, game_time):
        """Draws the unit on the main game surface."""
        if not self.is_alive or not self.game_map.tiles[self.x][self.y].is_visible:
            return

        pos_x, pos_y = camera.apply_coords(self.x, self.y)
        center = (pos_x + settings.TILE_SIZE // 2, pos_y + settings.TILE_SIZE // 2)
        
        if self.is_on_overwatch:
             pygame.draw.circle(surface, settings.COLOR_OVERWATCH, center, settings.UNIT_RADIUS + 6, 3)

        if self.is_selected:
            pulse = 1 + abs(math.sin(game_time * 0.005) * 2)
            pygame.draw.circle(surface, settings.COLOR_LASER, center, settings.UNIT_RADIUS + 3, int(pulse)+1)

        color = settings.COLOR_PLAYER if self.team == 'player' else settings.COLOR_ENEMY
        pygame.draw.circle(surface, color, center, settings.UNIT_RADIUS)
        
        if self.number is not None:
            num_text = font.render(str(self.number), True, settings.COLOR_WHITE)
            num_rect = num_text.get_rect(center=center)
            surface.blit(num_text, num_rect)

        hp_rect_bg = pygame.Rect(pos_x, pos_y + settings.TILE_SIZE - 8, settings.TILE_SIZE, 6)
        hp_percent = max(0, self.hp / settings.UNIT_MAX_HP)
        hp_rect_fg = pygame.Rect(pos_x, pos_y + settings.TILE_SIZE - 8, settings.TILE_SIZE * hp_percent, 6)
        pygame.draw.rect(surface, settings.COLOR_DARK_GRAY, hp_rect_bg)
        pygame.draw.rect(surface, settings.COLOR_PLAYER_LIGHT if self.team == 'player' else settings.COLOR_ENEMY_LIGHT, hp_rect_fg)

    def draw_path(self, surface, camera):
        """Draws the unit's intended movement path."""
        if self.path and len(self.path) > 1:
            points = []
            for node in self.path:
                pos_x, pos_y = camera.apply_coords(node[0], node[1])
                points.append((pos_x + settings.TILE_SIZE // 2, pos_y + settings.TILE_SIZE // 2))
            pygame.draw.lines(surface, settings.COLOR_PLAYER_LIGHT, False, points, 2)

    def move_along_path(self):
        """Moves the unit one step along its path if it has AP."""
        if self.path and self.ap >= settings.MOVE_COST:
            self.is_on_overwatch = False
            self.has_fired_overwatch = False

            next_pos = self.path.pop(0)
            self.x, self.y = next_pos
            self.ap -= settings.MOVE_COST
            self.distance_travelled += 2
            sounds.SOUNDS['move'].play()
            return True
        self.path = []
        return False
    
    def take_damage(self, amount):
        """Applies damage and plays hit sound."""
        self.hp -= amount
        sounds.SOUNDS['hit'].play()
        if self.hp <= 0:
            self.hp = 0
            self.die()

    def heal(self, amount):
        """Restores health to the unit."""
        self.hp += amount
        if self.hp > settings.UNIT_MAX_HP:
            self.hp = settings.UNIT_MAX_HP

    def die(self):
        """Handles the unit's death."""
        if self.is_alive:
            self.is_alive = False
            self.is_selected = False
            sounds.SOUNDS['death'].play()
