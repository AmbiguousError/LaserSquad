import heapq

class AStar:
    """A* pathfinding algorithm implementation."""
    def __init__(self, game_map):
        self.game_map = game_map
        self.neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start, end, occupied_nodes=None):
        """
        Finds a path from start to end using A*.
        occupied_nodes is a set of (x, y) tuples that are considered blocked.
        """
        if occupied_nodes is None:
            occupied_nodes = set()

        frontier = [(0, start)]
        came_from, cost_so_far = {start: None}, {start: 0}
        
        if end in occupied_nodes:
            return []

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == end: break
            for dx, dy in self.neighbors:
                next_node = (current[0] + dx, current[1] + dy)
                
                # --- MODIFICATION: Check against walls, cover, and occupied nodes ---
                if (not self.game_map.is_in_bounds(next_node[0], next_node[1]) or 
                        self.game_map.tiles[next_node[0]][next_node[1]].is_wall or
                        self.game_map.tiles[next_node[0]][next_node[1]].is_cover or
                        next_node in occupied_nodes):
                    continue

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
