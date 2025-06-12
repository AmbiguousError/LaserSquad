# LaserSquad: Tactical Turn-Based Game

![LaserSquad Screenshot](./Laser%20Squad%20Screenshot.jpg)

LaserSquad is a turn-based tactical squad game built with Python and Pygame. Command a 4-person squad through procedurally generated levels, engage in strategic combat, and lead your team to victory against hostile forces, or challenge a friend in two-player mode.

## Features

* **Single-Player & Two-Player Hotseat:** Battle against intelligent AI squads or go head-to-head against another player.
* **Turn-Based Tactical Combat:** Carefully plan your moves and actions. Each unit has a limited number of Action Points (AP) per turn.
* **Squad Management:** Control a 4-person squad, each with unique names, numbers, and persistent stats.
* **Procedurally Generated Maps:** Every mission features a unique, randomly generated map with rooms, corridors, and low cover.
* **Fog of War & True Line of Sight:** The map is hidden until explored. Enemies are only visible if a squad member has a direct line of sight, which is blocked by walls, cover, and other units.
* **D20 Skill-Based Combat:** Every attack, whether ranged or melee, is decided by a D20 roll plus the unit's skill modifier.
* **Posture & Cover System:** Units can stand or go prone. Prone units are harder to hit and can hide behind low cover, but cannot fire over it.
* **Reaction Fire (Overwatch):** Set your units to automatically fire on an enemy that performs *any action* within their line of sight, making it a powerful area-denial tool.
* **Healing Mechanic:** Use your squad's action points to heal injured teammates who are in an adjacent tile.
* **Intelligent Enemy AI:** In single-player mode, face off against multiple enemy squads that actively search the map for your team and work together to attack.
* **Post-Mission Stats & Awards:** After each game, review detailed statistics for each squad member and see who earns awards for top performance in categories like "Commando," "Marksman," and "Medic."

## How to Play

### Main Menu
* Press **1** for Single-Player mode.
* Press **2** for Two-Player mode.

### Controls

* **Select Unit:** Left-click on a unit or press the corresponding number key (**1, 2, 3, 4**).
* **Move Unit:** With a unit selected, right-click on a valid floor tile to set a path.
* **Attack (Ranged):** Right-click on a visible enemy from a distance.
* **Attack (Melee):** Right-click on an **adjacent** enemy.
* **Set Overwatch:** Press the **'O'** key or click the "Overwatch" button (3 AP).
* **Heal Friendly:** Press the **'H'** key or click the "Heal" button when next to an injured teammate (5 AP).
* **Change Posture:** Press the **'C'** key or click the "Prone"/"Stand" button to toggle posture (1 AP).
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
* `ai.py`: Contains the logic for the enemy AI's turn.
* `ui.py`: Handles drawing all UI elements, including the home screen, side panel, and buttons.
* `settings.py`: Contains all global constants like colors, screen dimensions, and game balance variables.
* `sprites.py`: Defines the `Unit` and `Tile` classes, which are the main objects in the game.
* `map.py`: Handles the procedural generation of the game map and line-of-sight calculations.
* `camera.py`: Manages the game's camera and viewport.
* `pathfinding.py`: Contains the A* pathfinding algorithm for unit movement.
* `sounds.py`: Handles the generation of all sound effects.
