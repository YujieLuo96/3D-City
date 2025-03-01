from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import numpy as np
import math

app = Ursina()

# Global configuration
CHUNK_SIZE = 5  # Size of each chunk
MAX_VISIBLE_CHUNKS = 2  # Reduced number of visible chunks for better performance
BUILDING_TYPES = ['modern', 'classic', 'asian', 'european', 'futuristic']
TIME_CYCLE_DURATION = 240  # Duration of a day-night cycle in seconds
INITIAL_TIME = 0.5  # Start at midday (noon) for better visibility
SPAWN_POSITION = (3, 0.5, 3)  # Ensure this is on a road in the first chunk

# Scale configuration - based on realistic proportions
STREET_WIDTH = 3.5  # Width of streets (approximately 12 meters) - WIDENED
SIDEWALK_WIDTH = 0.8  # Width of sidewalks (approximately 2.5 meters) - WIDENED
BUILDING_WIDTH = 3.0  # Width of buildings (approximately 10 meters)
PLAYER_HEIGHT = 1.8  # Height of player (approximately 1.8 meters)
STORY_HEIGHT = 1.0  # Height of one story (approximately 3 meters)
VEHICLE_LENGTH = 1.5  # Length of vehicles (approximately 5 meters)

# Enhanced texture color definitions - realistic urban color palette
temp_textures = {
    'grass': color.rgb(76, 120, 40),  # Richer grass green
    'road': color.rgb(50, 50, 50),  # Darker asphalt
    'asphalt': color.rgb(40, 40, 40),  # Deeper asphalt for better contrast
    'sidewalk': color.rgb(210, 210, 210),  # Lighter concrete gray
    'crosswalk': color.rgb(250, 250, 250),  # Bright white markings
    'modern': color.rgb(120, 170, 195),  # Steel blue glass - more saturated
    'modern_accent': color.rgb(200, 200, 200),  # Brighter steel/aluminum accents
    'classic': color.rgb(180, 90, 70),  # Brighter brick red
    'classic_accent': color.rgb(225, 205, 165),  # Warmer sandstone/limestone
    'asian': color.rgb(160, 40, 40),  # Richer deep red
    'asian_accent': color.rgb(235, 195, 65),  # Brighter gold accent
    'european': color.rgb(240, 220, 185),  # Warmer cream stucco
    'european_accent': color.rgb(135, 100, 85),  # Richer brown trim
    'futuristic': color.rgb(235, 240, 250),  # Brighter white/silver
    'futuristic_accent': color.rgb(125, 215, 245),  # Brighter light blue accent
    'tree': color.rgb(45, 105, 35),  # Deep foliage green
    'tree_trunk': color.rgb(100, 75, 40),  # Natural bark brown
    'flower': color.rgb(245, 100, 135),  # Brighter pink blossoms
    'car1': color.rgb(40, 65, 130),  # Richer dark blue
    'car2': color.rgb(160, 160, 160),  # Brighter silver/gray
    'car3': color.rgb(195, 50, 50),  # Brighter red
    'car4': color.rgb(40, 85, 60),  # Richer deep green
    'roof': color.rgb(80, 80, 90),  # Darker slate roof
    'roof_light': color.rgb(135, 125, 115),  # Lighter roof tiles
}

# Global variables
loaded_chunks = {}
current_time = INITIAL_TIME  # Start at midday for better visibility
vehicles = []
trees = []
flowers = []

# Road network information
road_network = {}  # Store road segment information (key: tuple(x,z), value: list of directions)


class Chunk:
    """Represents a chunk of the city"""

    def __init__(self, position):
        self.position = position  # (chunk_x, chunk_z)
        self.entities = []
        self.city_plan = self.generate_city_plan()
        self.generate_terrain()
        self.generate_streets()
        self.generate_buildings()
        self.generate_nature()
        self.spawn_traffic()

    def generate_city_plan(self):
        """Generate a city plan for this chunk"""
        # Use a fixed seed to ensure the same layout is generated for the same position
        seed = abs(hash(self.position)) % (2 ** 32 - 1)
        random.seed(seed)
        np.random.seed(seed)

        # Create a grid representing the chunk
        grid = np.zeros((CHUNK_SIZE, CHUNK_SIZE))

        # Create a regular grid of streets
        # Street grid with improved spacing for wider streets
        for i in range(CHUNK_SIZE):
            for j in range(CHUNK_SIZE):
                # Mark streets - we'll use a grid where every third cell is a street
                if i % 3 == 0 or j % 3 == 0:
                    grid[i, j] = 1  # Street

                # Intersections get marked specially
                if i % 3 == 0 and j % 3 == 0:
                    grid[i, j] = 2  # Intersection

        # Add parks (only in non-street areas)
        park_chance = 0.15
        for i in range(CHUNK_SIZE):
            for j in range(CHUNK_SIZE):
                if grid[i, j] == 0 and random.random() < park_chance:
                    # Create a small park
                    park_size = 1  # Since our grid is now more dense, we'll use smaller parks
                    if i + park_size < CHUNK_SIZE and j + park_size < CHUNK_SIZE:
                        grid[i:i + park_size + 1, j:j + park_size + 1] = 3  # Park

        return grid

    def generate_terrain(self):
        """Generate basic terrain"""
        chunk_x, chunk_z = self.position
        world_x = chunk_x * CHUNK_SIZE
        world_z = chunk_z * CHUNK_SIZE

        # Create ground for the entire chunk with proper collider
        ground = Entity(
            model='plane',
            scale=(CHUNK_SIZE, 1, CHUNK_SIZE),
            position=(world_x + CHUNK_SIZE / 2 - 0.5, 0, world_z + CHUNK_SIZE / 2 - 0.5),
            color=temp_textures['grass'],
            collider='box'  # Ensure collider is set
        )
        self.entities.append(ground)

        # Add ground texture detail to make orientation more obvious
        detail_size = 0.3
        for i in range(3):
            for j in range(3):
                detail = Entity(
                    model='quad',
                    scale=(detail_size, detail_size),
                    position=(
                        world_x + CHUNK_SIZE / 2 - 0.5 + (i - 1) * CHUNK_SIZE * 0.25,
                        0.01,
                        world_z + CHUNK_SIZE / 2 - 0.5 + (j - 1) * CHUNK_SIZE * 0.25
                    ),
                    rotation_x=90,
                    color=color.rgba(0, 90, 0, 128)
                )
                self.entities.append(detail)

        # Check if this is the spawn chunk and create a special marker
        spawn_chunk_x = math.floor(SPAWN_POSITION[0] / CHUNK_SIZE)
        spawn_chunk_z = math.floor(SPAWN_POSITION[2] / CHUNK_SIZE)

        if chunk_x == spawn_chunk_x and chunk_z == spawn_chunk_z:
            # Create a small visible marker at spawn point
            spawn_marker = Entity(
                model='sphere',
                scale=0.2,
                position=(SPAWN_POSITION[0], 0.1, SPAWN_POSITION[2]),
                color=color.yellow
            )
            self.entities.append(spawn_marker)
            print(f"Created spawn marker at {SPAWN_POSITION}")

    def generate_streets(self):
        """Generate streets, sidewalks, and crosswalks"""
        chunk_x, chunk_z = self.position
        world_x = chunk_x * CHUNK_SIZE
        world_z = chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                cell_type = self.city_plan[x, z]

                if cell_type == 1 or cell_type == 2:  # Street or intersection
                    # Main road surface - WIDENED
                    road = Entity(
                        model='cube',
                        scale=(1.5, 0.1, 1.5),  # Widened from (1, 0.1, 1)
                        position=(world_x + x, 0.05, world_z + z),
                        color=temp_textures['asphalt'],
                    )
                    self.entities.append(road)

                    # Add road markings
                    if cell_type == 1:  # Street segment
                        # Determine road direction (horizontal or vertical)
                        is_horizontal = False
                        is_vertical = False

                        # Check neighboring cells to determine road direction
                        if x > 0 and x < CHUNK_SIZE - 1:
                            if self.city_plan[x - 1, z] in [1, 2] and self.city_plan[x + 1, z] in [1, 2]:
                                is_horizontal = True

                        if z > 0 and z < CHUNK_SIZE - 1:
                            if self.city_plan[x, z - 1] in [1, 2] and self.city_plan[x, z + 1] in [1, 2]:
                                is_vertical = True

                        # Add to road network for vehicle pathfinding
                        road_key = (world_x + x, world_z + z)
                        road_network[road_key] = []

                        if is_horizontal:
                            # Add horizontal road markings - WIDENED
                            marking = Entity(
                                model='cube',
                                scale=(1.4, 0.11, 0.08),  # Widened from (0.9, 0.11, 0.05)
                                position=(world_x + x, 0.1, world_z + z),
                                color=temp_textures['crosswalk']
                            )
                            self.entities.append(marking)

                            # Add road network connections
                            road_network[road_key].append(Vec3(1, 0, 0))
                            road_network[road_key].append(Vec3(-1, 0, 0))

                        if is_vertical:
                            # Add vertical road markings - WIDENED
                            marking = Entity(
                                model='cube',
                                scale=(0.08, 0.11, 1.4),  # Widened from (0.05, 0.11, 0.9)
                                position=(world_x + x, 0.1, world_z + z),
                                color=temp_textures['crosswalk']
                            )
                            self.entities.append(marking)

                            # Add road network connections
                            road_network[road_key].append(Vec3(0, 0, 1))
                            road_network[road_key].append(Vec3(0, 0, -1))

                    elif cell_type == 2:  # Intersection
                        # Crosswalk at intersection - WIDENED
                        crosswalk = Entity(
                            model='cube',
                            scale=(1.4, 0.12, 1.4),  # Widened from (0.9, 0.12, 0.9)
                            position=(world_x + x, 0.1, world_z + z),
                            color=color.light_gray
                        )
                        self.entities.append(crosswalk)

                        # Add to road network - intersections connect in all directions
                        road_key = (world_x + x, world_z + z)
                        road_network[road_key] = [
                            Vec3(1, 0, 0), Vec3(-1, 0, 0),
                            Vec3(0, 0, 1), Vec3(0, 0, -1)
                        ]

                    # Add sidewalks beside roads
                    self.add_sidewalks(world_x + x, world_z + z, cell_type)

    def add_sidewalks(self, x, z, cell_type):
        """Add sidewalks around roads and intersections"""
        # Check all 8 surrounding cells to add sidewalks where appropriate
        for dx, dz in [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                       (0, 1), (1, -1), (1, 0), (1, 1)]:
            nx, nz = int(x - self.position[0] * CHUNK_SIZE + dx), int(z - self.position[1] * CHUNK_SIZE + dz)

            # Skip if outside chunk bounds
            if nx < 0 or nx >= CHUNK_SIZE or nz < 0 or nz >= CHUNK_SIZE:
                continue

            # Add sidewalk if this is a non-road cell next to a road
            if self.city_plan[nx, nz] == 0 and cell_type in [1, 2]:
                sidewalk = Entity(
                    model='cube',
                    scale=(0.8, 0.2, 0.8),  # Widened from (0.5, 0.2, 0.5)
                    position=(x + dx * 0.5, 0.1, z + dz * 0.5),
                    color=temp_textures['sidewalk']
                )
                self.entities.append(sidewalk)

    def generate_buildings(self):
        """Generate buildings"""
        chunk_x, chunk_z = self.position
        world_x = chunk_x * CHUNK_SIZE
        world_z = chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                cell_type = self.city_plan[x, z]

                # Generate buildings in non-street, non-park areas
                if cell_type == 0:
                    # Randomly decide whether to generate a building
                    if random.random() < 0.8:  # Higher probability for more urban density
                        self.place_building(world_x + x, world_z + z)

    def place_building(self, x, z):
        """Place a building at the specified position"""
        # Randomly select building type
        building_type = random.choice(BUILDING_TYPES)

        # Determine building size
        num_stories = random.randint(1, 12)  # Between 1 and 12 stories
        building_height = num_stories * STORY_HEIGHT
        building_width = random.uniform(0.8, 1.0)  # Slight variation in building footprint

        # Choose different shapes based on building type
        if building_type == 'modern':
            # Modern building - tall glass skyscraper
            building = Entity(
                model='cube',
                scale=(building_width, building_height, building_width),
                position=(x, building_height / 2, z),
                color=temp_textures[building_type]
            )

            # Add window details - horizontal bands for modern style
            for floor in range(1, num_stories):
                window_y = floor * STORY_HEIGHT - building_height / 2

                # Add window bands on all four sides
                for rotation in [0, 90, 180, 270]:
                    window = Entity(
                        model='quad',
                        scale=(building_width * 0.8, 0.3),
                        position=(x, building_height / 2 + window_y, z),
                        rotation=(0, rotation, 0),
                        color=color.rgba(210, 240, 255, 200),  # Enhanced blue glass windows
                        double_sided=True
                    )
                    self.entities.append(window)

            self.entities.append(building)

        elif building_type == 'classic':
            # Classic building - brick or stone with details
            building = Entity(
                model='cube',
                scale=(building_width, building_height * 0.7, building_width),
                position=(x, building_height * 0.35, z),
                color=temp_textures['classic']
            )

            # Add stone foundation
            foundation = Entity(
                model='cube',
                scale=(building_width + 0.05, building_height * 0.1, building_width + 0.05),
                position=(x, building_height * 0.05, z),
                color=temp_textures['classic_accent']
            )

            # Add a small roof structure
            roof = Entity(
                model='cube',
                scale=(building_width + 0.1, building_height * 0.1, building_width + 0.1),
                position=(x, building_height * 0.75, z),
                color=temp_textures['roof_light']
            )

            # Add decorative cornice
            cornice = Entity(
                model='cube',
                scale=(building_width + 0.15, building_height * 0.05, building_width + 0.15),
                position=(x, building_height * 0.7, z),
                color=temp_textures['classic_accent']
            )

            # Add windows in a grid pattern
            window_width = 0.15
            window_height = 0.25
            windows_per_side = max(1, int(building_width / 0.3))

            for floor in range(max(1, int(building_height * 0.7 / STORY_HEIGHT))):
                window_y = floor * STORY_HEIGHT - building_height * 0.35 + STORY_HEIGHT * 0.3

                for side in range(4):  # 4 sides of the building
                    rotation_y = side * 90

                    for i in range(windows_per_side):
                        # Calculate window position
                        offset = (i - (windows_per_side - 1) / 2) * (building_width / windows_per_side)

                        if side % 2 == 0:  # Front and back
                            window_x = offset
                            window_z = building_width / 2 * (1 if side == 0 else -1)
                        else:  # Left and right sides
                            window_x = building_width / 2 * (1 if side == 1 else -1)
                            window_z = offset

                        # Window frame
                        frame = Entity(
                            model='quad',
                            scale=(window_width + 0.03, window_height + 0.03),
                            position=(x + window_x, building_height * 0.35 + window_y, z + window_z),
                            rotation=(0, rotation_y, 0),
                            color=temp_textures['classic_accent'],
                            double_sided=True
                        )

                        # Window glass
                        window = Entity(
                            model='quad',
                            scale=(window_width, window_height),
                            position=(x + window_x, building_height * 0.35 + window_y, z + window_z + 0.01),
                            rotation=(0, rotation_y, 0),
                            color=color.rgba(255, 255, 230, 180),  # Warm-tinted glass
                            double_sided=True
                        )

                        self.entities.extend([frame, window])

            self.entities.extend([building, foundation, roof, cornice])

        elif building_type == 'asian':
            # Asian style - pagoda inspired
            base_height = building_height * 0.6
            base = Entity(
                model='cube',
                scale=(building_width, base_height, building_width),
                position=(x, base_height / 2, z),
                color=temp_textures['asian']
            )

            # Pagoda-style roof sections
            roof_layers = min(3, num_stories)
            for i in range(roof_layers):
                layer_size = building_width * (1 - i * 0.2)
                roof_layer = Entity(
                    model='cube',
                    scale=(layer_size + 0.2, building_height * 0.1, layer_size + 0.2),
                    position=(x, base_height + i * STORY_HEIGHT * 0.3, z),
                    color=temp_textures['roof_light']
                )

                # Add decorative edges to roof
                if i < roof_layers - 1:
                    edge_size = layer_size + 0.3
                    roof_edge = Entity(
                        model='cube',
                        scale=(edge_size, building_height * 0.02, edge_size),
                        position=(x, base_height + i * STORY_HEIGHT * 0.3 + building_height * 0.06, z),
                        color=temp_textures['asian_accent']
                    )
                    self.entities.append(roof_edge)

                self.entities.append(roof_layer)

            # Add decorative windows - curved and ornate for Asian style
            window_height = 0.4
            window_width = 0.3

            for floor in range(max(1, int(base_height / STORY_HEIGHT))):
                window_y = floor * STORY_HEIGHT - base_height / 2 + STORY_HEIGHT * 0.3

                for side in range(4):
                    rotation_y = side * 90

                    # Central window on each side
                    window_x = 0
                    window_z = building_width / 2 * (1 if side == 0 else -1)

                    if side % 2 == 1:  # Left and right sides
                        window_x = building_width / 2 * (1 if side == 1 else -1)
                        window_z = 0

                    # Window frame - slightly darker than the building
                    frame = Entity(
                        model='quad',
                        scale=(window_width + 0.05, window_height + 0.05),
                        position=(x + window_x, base_height / 2 + window_y, z + window_z),
                        rotation=(0, rotation_y, 0),
                        color=color.rgb(110, 25, 25),  # Darker red frame
                        double_sided=True
                    )

                    # Window glass
                    window = Entity(
                        model='quad',
                        scale=(window_width, window_height),
                        position=(x + window_x, base_height / 2 + window_y, z + window_z + 0.01),
                        rotation=(0, rotation_y, 0),
                        color=color.rgba(210, 210, 255, 180),  # Enhanced window glass
                        double_sided=True
                    )

                    # Decorative horizontal bars - Asian style
                    for j in range(3):
                        bar_y = window_y - window_height / 2 + (j + 1) * window_height / 4
                        bar = Entity(
                            model='quad',
                            scale=(window_width, 0.02),
                            position=(x + window_x, base_height / 2 + bar_y, z + window_z + 0.02),
                            rotation=(0, rotation_y, 0),
                            color=temp_textures['asian_accent'],
                            double_sided=True
                        )
                        self.entities.append(bar)

                    self.entities.extend([frame, window])

            self.entities.append(base)

        elif building_type == 'european':
            # European style - older architecture with pitched roof
            base_height = building_height * 0.7
            base = Entity(
                model='cube',
                scale=(building_width, base_height, building_width),
                position=(x, base_height / 2, z),
                color=temp_textures['european']
            )

            # Create a pitched roof using two cubes
            roof_front = Entity(
                model='cube',
                scale=(building_width, building_height * 0.15, building_width / 2),
                position=(x, base_height + building_height * 0.075, z - building_width / 4),
                color=temp_textures['roof']
            )

            roof_back = Entity(
                model='cube',
                scale=(building_width, building_height * 0.15, building_width / 2),
                position=(x, base_height + building_height * 0.075, z + building_width / 4),
                color=temp_textures['roof']
            )

            # Add chimney
            if random.random() < 0.7:
                chimney = Entity(
                    model='cube',
                    scale=(0.1, building_height * 0.2, 0.1),
                    position=(x + building_width * 0.3, base_height + building_height * 0.2, z + building_width * 0.3),
                    color=temp_textures['classic']  # Brick chimney
                )
                self.entities.append(chimney)

            # Add European-style windows with frames
            window_height = 0.35
            window_width = 0.2
            windows_per_floor = max(2, int(building_width / 0.3))

            for floor in range(max(1, int(base_height / STORY_HEIGHT))):
                window_y = floor * STORY_HEIGHT - base_height / 2 + STORY_HEIGHT * 0.3

                for side in range(4):
                    rotation_y = side * 90
                    side_width = building_width if side % 2 == 0 else building_width

                    for i in range(windows_per_floor):
                        # Calculate window position
                        offset = (i - (windows_per_floor - 1) / 2) * (side_width / windows_per_floor)

                        if side % 2 == 0:  # Front and back
                            window_x = offset
                            window_z = building_width / 2 * (1 if side == 0 else -1)
                        else:  # Left and right sides
                            window_x = building_width / 2 * (1 if side == 1 else -1)
                            window_z = offset

                        # Window frame
                        frame = Entity(
                            model='quad',
                            scale=(window_width + 0.04, window_height + 0.04),
                            position=(x + window_x, base_height / 2 + window_y, z + window_z),
                            rotation=(0, rotation_y, 0),
                            color=temp_textures['european_accent'],
                            double_sided=True
                        )

                        # Window glass
                        window = Entity(
                            model='quad',
                            scale=(window_width, window_height),
                            position=(x + window_x, base_height / 2 + window_y, z + window_z + 0.01),
                            rotation=(0, rotation_y, 0),
                            color=color.rgba(225, 235, 255, 170),  # Enhanced window glass
                            double_sided=True
                        )

                        # Window crossbar
                        crossbar_h = Entity(
                            model='quad',
                            scale=(window_width, 0.02),
                            position=(x + window_x, base_height / 2 + window_y, z + window_z + 0.02),
                            rotation=(0, rotation_y, 0),
                            color=temp_textures['european_accent'],
                            double_sided=True
                        )

                        crossbar_v = Entity(
                            model='quad',
                            scale=(0.02, window_height),
                            position=(x + window_x, base_height / 2 + window_y, z + window_z + 0.02),
                            rotation=(0, rotation_y, 0),
                            color=temp_textures['european_accent'],
                            double_sided=True
                        )

                        self.entities.extend([frame, window, crossbar_h, crossbar_v])

            self.entities.extend([base, roof_front, roof_back])

        elif building_type == 'futuristic':
            # Futuristic style - irregular shapes and glass

            # Core tower
            main_tower = Entity(
                model='cube',
                scale=(building_width * 0.8, building_height, building_width * 0.8),
                position=(x, building_height / 2, z),
                color=temp_textures['futuristic']
            )

            # Add large glass panels
            window_width = building_width * 0.6
            window_height = building_height * 0.8

            for side in range(4):
                rotation_y = side * 90

                # Full height glass panel on each side
                window_x = 0
                window_z = building_width * 0.41

                if side % 2 == 1:
                    window_x = building_width * 0.41
                    window_z = 0

                if side == 2:
                    window_x = 0
                    window_z = -building_width * 0.41

                if side == 3:
                    window_x = -building_width * 0.41
                    window_z = 0

                # Glass panel with slight offset
                glass_panel = Entity(
                    model='quad',
                    scale=(window_width, window_height),
                    position=(x + window_x, building_height / 2, z + window_z),
                    rotation=(0, rotation_y, 0),
                    color=color.rgba(120, 200, 235, 200),  # Enhanced blue tinted glass
                    double_sided=True
                )

                # Add horizontal lines to the glass panels
                lines_count = max(3, int(window_height / 0.5))
                for i in range(1, lines_count):
                    line_y = -window_height / 2 + i * (window_height / lines_count)

                    line = Entity(
                        model='quad',
                        scale=(window_width, 0.03),
                        position=(x + window_x, building_height / 2 + line_y, z + window_z + 0.01),
                        rotation=(0, rotation_y, 0),
                        color=temp_textures['futuristic_accent'],
                        double_sided=True
                    )
                    self.entities.append(line)

                self.entities.append(glass_panel)

            # Random additional structures - asymmetric extensions
            for _ in range(random.randint(1, 3)):
                dx = random.uniform(-0.3, 0.3)
                dz = random.uniform(-0.3, 0.3)
                height_factor = random.uniform(0.3, 0.8)
                width_factor = random.uniform(0.2, 0.5)

                # Create unique angles for futuristic look
                rotation_y = random.uniform(0, 15)

                extension = Entity(
                    model='cube',
                    scale=(
                    building_width * width_factor, building_height * height_factor, building_width * width_factor),
                    position=(x + dx, building_height * height_factor / 2, z + dz),
                    rotation=(0, rotation_y, 0),
                    color=temp_textures['futuristic_accent']
                )

                # Add windows to extensions too
                ext_window_height = building_height * height_factor * 0.6
                ext_window_width = building_width * width_factor * 0.6

                for side in range(4):
                    ext_rotation_y = side * 90 + rotation_y

                    # Position depends on the side
                    ext_window_x = dx
                    ext_window_z = dz + building_width * width_factor * 0.51

                    if side % 2 == 1:
                        ext_window_x = dx + building_width * width_factor * 0.51
                        ext_window_z = dz

                    if side == 2:
                        ext_window_x = dx
                        ext_window_z = dz - building_width * width_factor * 0.51

                    if side == 3:
                        ext_window_x = dx - building_width * width_factor * 0.51
                        ext_window_z = dz

                    # Apply rotation offset
                    pos_x = ext_window_x * math.cos(math.radians(rotation_y)) - ext_window_z * math.sin(
                        math.radians(rotation_y))
                    pos_z = ext_window_x * math.sin(math.radians(rotation_y)) + ext_window_z * math.cos(
                        math.radians(rotation_y))

                    ext_window = Entity(
                        model='quad',
                        scale=(ext_window_width, ext_window_height),
                        position=(x + pos_x, building_height * height_factor / 2, z + pos_z),
                        rotation=(0, ext_rotation_y, 0),
                        color=color.rgba(140, 230, 255, 180),  # Enhanced window color
                        double_sided=True
                    )
                    self.entities.append(ext_window)

                self.entities.append(extension)

            # Top feature - either a sphere or an antenna
            if random.random() < 0.5 and building_height > 5:
                sphere = Entity(
                    model='sphere',
                    scale=(building_width * 0.5, building_width * 0.5, building_width * 0.5),
                    position=(x, building_height + building_width * 0.25, z),
                    color=temp_textures['futuristic']
                )
                self.entities.append(sphere)
            else:
                antenna = Entity(
                    model='cube',
                    scale=(0.05, building_height * 0.3, 0.05),
                    position=(x, building_height + building_height * 0.15, z),
                    color=temp_textures['modern_accent']
                )
                antenna_top = Entity(
                    model='sphere',
                    scale=(0.1, 0.1, 0.1),
                    position=(x, building_height + building_height * 0.3, z),
                    color=temp_textures['futuristic_accent']
                )
                self.entities.extend([antenna, antenna_top])

            self.entities.append(main_tower)

    def generate_nature(self):
        """Generate natural elements like trees and flowers"""
        chunk_x, chunk_z = self.position
        world_x = chunk_x * CHUNK_SIZE
        world_z = chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                cell_type = self.city_plan[x, z]

                if cell_type == 3:  # Park area
                    # Add trees
                    for _ in range(random.randint(1, 2)):
                        tree_x = world_x + x + random.uniform(-0.3, 0.3)
                        tree_z = world_z + z + random.uniform(-0.3, 0.3)
                        self.place_tree(tree_x, tree_z)

                    # Add flowers
                    for _ in range(random.randint(2, 5)):
                        flower_x = world_x + x + random.uniform(-0.4, 0.4)
                        flower_z = world_z + z + random.uniform(-0.4, 0.4)
                        self.place_flower(flower_x, flower_z)

    def place_tree(self, x, z):
        """Place a tree"""
        trunk_height = random.uniform(0.8, 1.2)
        trunk = Entity(
            model='cube',
            scale=(0.1, trunk_height, 0.1),
            position=(x, trunk_height / 2, z),
            color=temp_textures['tree_trunk']
        )

        leaves_size = random.uniform(0.4, 0.6)
        leaves = Entity(
            model='sphere',
            scale=(leaves_size, leaves_size, leaves_size),
            position=(x, trunk_height + leaves_size / 2, z),
            color=temp_textures['tree']
        )

        self.entities.extend([trunk, leaves])
        trees.append((trunk, leaves))

    def place_flower(self, x, z):
        """Place a flower"""
        stem = Entity(
            model='cube',
            scale=(0.03, 0.15, 0.03),
            position=(x, 0.075, z),
            color=color.green
        )

        blossom = Entity(
            model='sphere',
            scale=(0.08, 0.08, 0.08),
            position=(x, 0.2, z),
            color=random.choice([temp_textures['flower'], color.red, color.yellow, color.white])
        )

        self.entities.extend([stem, blossom])
        flowers.append((stem, blossom))

    def spawn_traffic(self):
        """Spawn vehicles on roads"""
        chunk_x, chunk_z = self.position
        world_x = chunk_x * CHUNK_SIZE
        world_z = chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                cell_type = self.city_plan[x, z]

                # Only spawn on streets, not intersections (to avoid congestion)
                if cell_type == 1 and random.random() < 0.15:  # 15% chance for each road segment
                    road_pos = (world_x + x, world_z + z)
                    if road_pos in road_network and road_network[road_pos]:
                        self.spawn_vehicle(road_pos)

    def spawn_vehicle(self, road_pos):
        """Spawn a vehicle on the road with appropriate direction"""
        x, z = road_pos

        # Get available directions from road network
        if not road_network[road_pos]:
            return

        # Choose a direction
        direction = random.choice(road_network[road_pos])

        # Choose vehicle type and color
        car_type = random.choice(['car1', 'car2', 'car3', 'car4'])

        # Determine vehicle orientation based on direction
        rotation = 0
        scale = (VEHICLE_LENGTH * 0.7, 0.4, 0.5)  # Default size for vehicles

        if direction.x != 0:  # Horizontal road
            rotation = 90 if direction.x > 0 else 270
            scale = (0.5, 0.4, VEHICLE_LENGTH * 0.7)  # Rotate dimensions for horizontal roads

        # Minor offset to avoid spawning in center of road
        offset_x = 0.0
        offset_z = 0.0
        if direction.x != 0:
            offset_z = 0.3 if random.random() > 0.5 else -0.3  # Left or right lane - widened offset for wider streets
        else:
            offset_x = 0.3 if random.random() > 0.5 else -0.3  # Left or right lane - widened offset for wider streets

        # Create vehicle
        vehicle = Entity(
            model='cube',
            scale=scale,
            position=(x + offset_x, 0.2, z + offset_z),
            color=temp_textures[car_type],
            rotation=(0, rotation, 0)
        )

        # Store vehicle with its direction and speed
        speed = random.uniform(0.5, 1.5)
        vehicles.append({
            'entity': vehicle,
            'direction': direction,
            'speed': speed,
            'road_pos': road_pos,
            'target_pos': None,
            'current_direction': direction,
        })

        self.entities.append(vehicle)

    def unload(self):
        """Unload all entities in this chunk"""
        for entity in self.entities:
            try:
                destroy(entity)
            except:
                pass  # Catch any errors if entity already destroyed
        self.entities.clear()


def get_chunk_coords(position):
    """Convert world coordinates to chunk coordinates"""
    # Handle case where position might be a tuple or Vec3
    try:
        if isinstance(position, tuple):
            chunk_x = math.floor(position[0] / CHUNK_SIZE)
            chunk_z = math.floor(position[2] / CHUNK_SIZE)
        else:  # Assume it's a Vec3 or similar object with x,z attributes
            chunk_x = math.floor(position.x / CHUNK_SIZE)
            chunk_z = math.floor(position.z / CHUNK_SIZE)
    except Exception as e:
        print(f"Error in get_chunk_coords: {e}")
        # Default to origin chunk if there's an error
        return (0, 0)

    return chunk_x, chunk_z


def get_nearest_road(position):
    """Find the nearest road point to the given position"""
    nearest_dist = float('inf')
    nearest_point = None

    for road_point in road_network.keys():
        dist = (position.x - road_point[0]) ** 2 + (position.z - road_point[1]) ** 2
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_point = road_point

    return nearest_point


def update_visible_chunks():
    """Update visible chunks based on player position"""
    player_chunk = get_chunk_coords(player.position)
    player_chunk_x, player_chunk_z = player_chunk

    # Determine which chunks should be visible
    visible_chunks = set()
    for dx in range(-MAX_VISIBLE_CHUNKS, MAX_VISIBLE_CHUNKS + 1):
        for dz in range(-MAX_VISIBLE_CHUNKS, MAX_VISIBLE_CHUNKS + 1):
            chunk_coords = (player_chunk_x + dx, player_chunk_z + dz)
            if math.sqrt(dx ** 2 + dz ** 2) <= MAX_VISIBLE_CHUNKS:
                visible_chunks.add(chunk_coords)

    # Unload chunks that are no longer visible
    for chunk_coords in list(loaded_chunks.keys()):
        if chunk_coords not in visible_chunks:
            loaded_chunks[chunk_coords].unload()
            del loaded_chunks[chunk_coords]

    # Load new visible chunks
    for chunk_coords in visible_chunks:
        if chunk_coords not in loaded_chunks:
            loaded_chunks[chunk_coords] = Chunk(chunk_coords)


def update_day_night_cycle():
    """Update day-night cycle"""
    global current_time

    # Update time
    current_time = (current_time + time.dt / TIME_CYCLE_DURATION) % 1.0

    # Calculate sun and sky colors
    if current_time < 0.25:  # Midnight to sunrise
        intensity = current_time / 0.25
        sky_color = color.rgb(0, 0, 40 * intensity)
        sun_position = Vec3(500 * math.cos(current_time * 2 * math.pi),
                            -300 + 600 * intensity,
                            500 * math.sin(current_time * 2 * math.pi))
        sun_color = color.rgb(255 * intensity, 100 * intensity, 50 * intensity)
        scene.fog_density = max(0.005, 0.015 - intensity * 0.01)  # Reduce fog at dawn
    elif current_time < 0.75:  # Sunrise to sunset
        intensity = 1.0
        sky_color = color.rgb(135 * intensity, 206 * intensity, 235 * intensity)
        progress = (current_time - 0.25) / 0.5
        sun_position = Vec3(500 * math.cos(current_time * 2 * math.pi),
                            300,
                            500 * math.sin(current_time * 2 * math.pi))
        sun_color = color.rgb(255, 255 * intensity, 50 * intensity)
        scene.fog_density = 0.005  # Minimum fog during daylight
    else:  # Sunset to midnight
        intensity = (1.0 - current_time) / 0.25
        sky_color = color.rgb(0, 0, 40 * intensity)
        sun_position = Vec3(500 * math.cos(current_time * 2 * math.pi),
                            -300 + 600 * intensity,
                            500 * math.sin(current_time * 2 * math.pi))
        sun_color = color.rgb(255 * intensity, 100 * intensity, 50 * intensity)
        scene.fog_density = max(0.005, 0.015 - intensity * 0.01)  # Increase fog at dusk

    # Update sky and sunlight
    scene.fog_color = sky_color
    sun.position = sun_position
    sun.color = sun_color


def update_vehicles():
    """Update vehicle positions along the road network"""
    global vehicles
    vehicles_to_keep = []

    for vehicle_data in vehicles:
        try:
            vehicle = vehicle_data['entity']
            if not vehicle.enabled:
                continue

            current_pos = Vec3(vehicle.position)
            direction = vehicle_data['direction']
            speed = vehicle_data['speed']

            # Determine target position (if not set or reached)
            if not vehicle_data['target_pos'] or distance_2d(current_pos, vehicle_data['target_pos']) < 0.1:
                # Current road position
                road_pos = vehicle_data['road_pos']

                # Calculate next road position
                next_x = road_pos[0] + direction.x
                next_z = road_pos[1] + direction.z
                next_pos = (next_x, next_z)

                # Check if next position exists in road network
                if next_pos in road_network and road_network[next_pos]:
                    # Update road position
                    vehicle_data['road_pos'] = next_pos
                    vehicle_data['target_pos'] = Vec3(next_pos[0], 0.2, next_pos[1])

                    # At intersections, possibly change direction
                    if len(road_network[next_pos]) > 2:  # It's an intersection or junction
                        # Don't reverse direction immediately
                        possible_dirs = [d for d in road_network[next_pos]
                                         if not (d.x == -direction.x and d.z == -direction.z)]

                        if possible_dirs:
                            new_dir = random.choice(possible_dirs)
                            vehicle_data['direction'] = new_dir

                            # Update rotation based on new direction
                            if new_dir.x > 0:
                                vehicle.rotation = (0, 90, 0)
                                vehicle.scale = (0.5, 0.4, VEHICLE_LENGTH * 0.7)
                            elif new_dir.x < 0:
                                vehicle.rotation = (0, 270, 0)
                                vehicle.scale = (0.5, 0.4, VEHICLE_LENGTH * 0.7)
                            elif new_dir.z > 0:
                                vehicle.rotation = (0, 180, 0)
                                vehicle.scale = (VEHICLE_LENGTH * 0.7, 0.4, 0.5)
                            else:  # new_dir.z < 0
                                vehicle.rotation = (0, 0, 0)
                                vehicle.scale = (VEHICLE_LENGTH * 0.7, 0.4, 0.5)
                else:
                    # We've reached a dead end, destroy the vehicle
                    try:
                        destroy(vehicle)
                    except:
                        pass
                    continue

            # Move toward target position
            if vehicle_data['target_pos']:
                # Calculate direction to target
                to_target = vehicle_data['target_pos'] - current_pos
                if to_target.length() > 0:
                    to_target = to_target.normalized()

                # Move vehicle
                vehicle.position += to_target * speed * time.dt

                # Check for other vehicles - implement simple traffic rules
                for other_data in vehicles:
                    if other_data != vehicle_data and other_data['entity'].enabled:
                        # If vehicles are too close, slow down
                        dist = distance_3d(vehicle.position, other_data['entity'].position)
                        if dist < 0.7:  # Slow down to avoid collision
                            speed_factor = max(0.1, dist / 0.7)  # Reduce speed proportionally
                            vehicle.position += to_target * speed * time.dt * speed_factor

            # Check if vehicle is out of visible range
            player_chunk = get_chunk_coords(player.position)
            vehicle_chunk = get_chunk_coords(vehicle.position)

            if abs(vehicle_chunk[0] - player_chunk[0]) > MAX_VISIBLE_CHUNKS + 1 or \
                    abs(vehicle_chunk[1] - player_chunk[1]) > MAX_VISIBLE_CHUNKS + 1:
                try:
                    destroy(vehicle)
                except:
                    pass
                continue

            # Keep valid vehicles
            vehicles_to_keep.append(vehicle_data)

        except Exception as e:
            # If any error occurs, remove the vehicle
            try:
                destroy(vehicle_data['entity'])
            except:
                pass

    # Update our vehicle list to only contain valid vehicles
    vehicles = vehicles_to_keep


def distance_2d(pos1, pos2):
    """Calculate 2D distance between positions (ignoring y)"""
    return math.sqrt((pos1.x - pos2.x) ** 2 + (pos1.z - pos2.z) ** 2)


def distance_3d(pos1, pos2):
    """Calculate 3D distance between positions"""
    return math.sqrt((pos1.x - pos2.x) ** 2 + (pos1.y - pos2.y) ** 2 + (pos1.z - pos2.z) ** 2)


def update():
    """Update each frame"""
    try:
        # Ensure player is defined before updating
        if 'player' in globals():
            update_visible_chunks()
            update_day_night_cycle()
            update_vehicles()

            # Check if player has fallen below safety level
            if player.y < -10:
                print("Player fell through the world - respawning")
                player.position = SPAWN_POSITION
                player.y = PLAYER_HEIGHT / 2

            # Display current time and info (only update every 3 seconds to save performance)
            if int(time.time()) % 3 == 0:
                hours = int(current_time * 24)
                minutes = int((current_time * 24 * 60) % 60)
                debug_text.text = f"Time: {hours:02d}:{minutes:02d}\nPosition: {player.position}\nChunks: {len(loaded_chunks)}"
    except Exception as e:
        print(f"Error in update: {e}")
        if 'debug_text' in globals():
            debug_text.text = f"Error: {e}"


def input(key):
    """Handle input"""
    if key == 'escape':
        quit()


# Set window properties
window.title = '3D Infinite City'
window.borderless = False
window.exit_button.visible = True

# Create safety floor to prevent falling into void
safety_floor = Entity(
    model='plane',
    scale=1000,
    y=-1,
    collider='box',
    visible=False
)

# Create initial loading message
loading_text = Text(
    text="Loading city...",
    origin=(0, 0),
    position=(0, 0),
    scale=2,
    color=color.white
)


# Pre-generate initial chunks before spawning player
def initialize_city():
    """Force the initial chunk loading to ensure the city is visible at startup"""
    # Calculate the chunk where the player will spawn
    spawn_chunk_x = math.floor(SPAWN_POSITION[0] / CHUNK_SIZE)
    spawn_chunk_z = math.floor(SPAWN_POSITION[2] / CHUNK_SIZE)

    print(f"Initializing city around spawn point {SPAWN_POSITION}")
    print(f"Spawn chunk: ({spawn_chunk_x}, {spawn_chunk_z})")

    # Pre-load the chunks around spawn point
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            chunk_coords = (spawn_chunk_x + dx, spawn_chunk_z + dz)
            loaded_chunks[chunk_coords] = Chunk(chunk_coords)

    print(f"Loaded {len(loaded_chunks)} initial chunks")

    # Hide loading text once chunks are ready
    loading_text.visible = False

    # Now that the environment is ready, create the player
    create_player()


def create_player():
    """Create the player after the city has been initialized"""
    global player

    # Set up player with the defined spawn position
    player = FirstPersonController(
        position=SPAWN_POSITION,
        y=PLAYER_HEIGHT / 2,
        origin_y=-0.5  # Adjust origin to ensure feet are on ground
    )

    # Create sun
    global sun
    sun = DirectionalLight()
    sun.look_at(Vec3(0, -1, 0))

    # Create debug text
    global debug_text
    debug_text = Text(
        text=f"Position: {SPAWN_POSITION}",
        position=(0, 0.45),
        origin=(0, 0),
        scale=1.5
    )

    # Game instructions
    global game_instructions
    game_instructions = Text(
        text="WASD to move, Space to jump, Mouse to look around, ESC to quit",
        origin=(0, 0),
        position=(0, -0.45),
    )

    # Set up fog for atmosphere (lighter fog for better visibility)
    scene.fog_density = 0.005
    scene.fog_color = color.rgb(135, 206, 235)  # Sky blue color for daytime


# Call initialization before running the game
initialize_city()

# Run the game
app.run()