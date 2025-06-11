import pygame

# Initialize Pygame and its modules at the very start.
# This ensures that all pygame modules are ready before any other
# game files (like sounds.py) are imported and try to use them.
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.font.init()

# Now it's safe to import our game modules
from game import Game

def main():
    """
    Main function to initialize and run the game.
    """
    game = Game()
    game.run()

if __name__ == '__main__':
    main()
    pygame.quit()
