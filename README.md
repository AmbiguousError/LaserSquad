# LaserSquad: Tactical Turn-Based Game

LaserSquad is a turn-based tactical squad game built with Python and Pygame. Command a 4-person squad through procedurally generated levels, engage in strategic combat, and lead your team to victory against hostile forces.

## Features

* **Turn-Based Tactical Combat:** Carefully plan your moves and actions. Each unit has a limited number of Action Points (AP) per turn.
* **Squad Management:** Control a 4-person squad, each with unique names, numbers, and persistent stats.
* **Procedurally Generated Maps:** Every mission features a unique, randomly generated map with rooms and corridors.
* **Fog of War & Line of Sight:** The map is hidden until explored. Enemies are only visible if a squad member has a direct line of sight, which is blocked by walls and other units.
* **D20 Skill-Based Combat:** Every attack, whether ranged or melee, is decided by a D20 roll plus the unit's skill modifier.
* **Ranged & Melee Attacks:** Engage enemies from a distance with powerful laser weapons or get up close for a deadly one-hit-kill melee attack.
* **Overwatch System:** Set your units to automatically fire on the first enemy that moves into their line of sight during the opponent's turn.
* **Healing Mechanic:** Use your squad's action points to heal injured teammates who are in an adjacent tile.
* **Intelligent Enemy AI:** Face off against multiple enemy squads that actively search the map for your team and work together to attack.
* **Post-Mission Stats & Awards:** After each game, review detailed statistics for each squad member and see who earns awards for top performance in categories like "Commando," "Marksman," and "Medic."

## How to Play

### Controls

* **Select Unit:** Left-click on a unit or press the corresponding number key (**1, 2, 3, 4**).
* **Move Unit:** With a unit selected, right-click on a valid floor tile to set a path.
* **Attack (Ranged):** Right-click on a visible enemy from a distance.
* **Attack (Melee):** Right-click on an **adjacent** enemy.
* **Set Overwatch:** Press the **'O'** key or click the "Overwatch" button.
* **Heal Friendly:** Move a unit next to an injured teammate and press the **'H'** key.
* **End Turn:** Click the "End Turn" button.
* **Scroll Map:** Use the **Arrow Keys** or move your mouse to the edges of the game window.
* **Jump to Location:** Click on the minimap to instantly move the camera's view.

## Installation & Running the Game

### Prerequisites

* Python 3.x
* Pygame
* NumPy

### 1. Install Dependencies

You can install the required libraries using pip:

```bash
pip install pygame numpy
```

### 2. Run the Game

Navigate to the project's root directory in your terminal and run the main file:

```bash
python main.py
```

## Project Structure

The game is organized into several modules to keep the code clean and manageable:

* `main.py`: The main entry point of the application. Handles game initialization and the main loop.
* `game.py`: The core game class that manages game states, turns, input, and drawing.
* `settings.py`: Contains all global constants like colors, screen dimensions, and game balance variables.
* `sprites.py`: Defines the `Unit` and `Tile` classes, which are the main objects in the game.
* `map.py`: Handles the procedural generation of the game map and line-of-sight calculations.
* `camera.py`: Manages the game's camera and viewport.
* `pathfinding.py`: Contains the A* pathfinding algorithm for unit movement.
* `sounds.py`: Handles the generation of all sound effects.
