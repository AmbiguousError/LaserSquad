import settings

class Camera:
    """Manages the game's viewport."""
    def __init__(self, map_pixel_width, map_pixel_height, viewport_width, viewport_height):
        self.x, self.y = 0, 0
        self.width, self.height = viewport_width, viewport_height
        self.map_pixel_width, self.map_pixel_height = map_pixel_width, map_pixel_height
    
    def apply_coords(self, x, y):
        """Converts map coordinates to screen coordinates."""
        return x * settings.TILE_SIZE - self.x, y * settings.TILE_SIZE - self.y
    
    def apply_rect(self, rect):
        """Applies camera offset to a pygame.Rect."""
        return rect.move(-self.x, -self.y)

    def center_on(self, unit):
        """Centers the camera on a specific unit."""
        target_x = unit.x * settings.TILE_SIZE - self.width // 2
        target_y = unit.y * settings.TILE_SIZE - self.height // 2
        self.x = max(0, min(target_x, self.map_pixel_width - self.width))
        self.y = max(0, min(target_y, self.map_pixel_height - self.height))
        
    def center_on_coords(self, map_x, map_y):
        """Centers the camera on specific map coordinates."""
        target_x = map_x * settings.TILE_SIZE - self.width // 2
        target_y = map_y * settings.TILE_SIZE - self.height // 2
        self.x = max(0, min(target_x, self.map_pixel_width - self.width))
        self.y = max(0, min(target_y, self.map_pixel_height - self.height))

    def scroll(self, dx=0, dy=0):
        """Scrolls the camera by a delta value."""
        self.x += dx
        self.y += dy
        # Clamp camera to map boundaries
        self.x = max(0, min(self.x, self.map_pixel_width - self.width))
        self.y = max(0, min(self.y, self.map_pixel_height - self.height))
