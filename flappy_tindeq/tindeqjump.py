import pygame
import random
import asyncio
from tindeq_backend.tindeq import TindeqProgressor

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Bird properties
bird_x = 50
bird_y = HEIGHT // 2
bird_velocity = 0
gravity = 0.5
jump_strength = -10

# Pipe properties
pipe_width = 100
pipe_gap = 200
pipe_speed = 5
pipe_frequency = 1500  # milliseconds
last_pipe = pygame.time.get_ticks() - pipe_frequency

pipes = []

def draw_bird():
    pygame.draw.circle(screen, BLACK, (bird_x, int(bird_y)), 20)

def draw_pipes():
    for pipe in pipes:
        pygame.draw.rect(screen, BLACK, pipe)

def update_pipes():
    global pipes
    for pipe in pipes:
        pipe.x -= pipe_speed
    pipes = [pipe for pipe in pipes if pipe.x + pipe_width > 0]

def create_pipe():
    height = random.randint(100, HEIGHT - 100 - pipe_gap)
    top_pipe = pygame.Rect(WIDTH, 0, pipe_width, height)
    bottom_pipe = pygame.Rect(WIDTH, height + pipe_gap, pipe_width, HEIGHT - height - pipe_gap)
    pipes.append(top_pipe)
    pipes.append(bottom_pipe)

def check_collision():
    return False;
    bird_rect = pygame.Rect(bird_x - 20, bird_y - 20, 40, 40)
    for pipe in pipes:
        if bird_rect.colliderect(pipe):
            return True
    if bird_y <= 0 or bird_y >= HEIGHT:
        return True
    return False

class Wrapper:
    def __init__(self, weight_queue):
        self.weight_queue = weight_queue

    def log_force_sample(self, time, weight):
        self.weight_queue.put_nowait(weight)

async def initialize_tindeq(tindeq):
    await tindeq.get_batt()
    await asyncio.sleep(0.5)
    await tindeq.get_fw_info()
    await asyncio.sleep(0.5)
    await tindeq.get_err()
    await asyncio.sleep(0.5)
    await tindeq.clear_err()
    await asyncio.sleep(0.5)
    await tindeq.soft_tare()
    await asyncio.sleep(1)

async def log_weight(tindeq, weight_queue):
    while True:
        try:
            await tindeq.start_logging_weight()
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(1)

async def tindeq_task(weight_queue, initialization_complete):
    wrap = Wrapper(weight_queue)
    async with TindeqProgressor(wrap) as tindeq:
        await initialize_tindeq(tindeq)
        initialization_complete.set()  # Signal that initialization is complete
        await log_weight(tindeq, weight_queue)

async def main_game(weight_queue, initialization_complete):
    await initialization_complete.wait()  # Wait for initialization to complete

    global bird_y, bird_velocity, last_pipe, pipes  # Ensure these are global

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Check weight input
        while not weight_queue.empty():
            weight = await weight_queue.get()
            if weight > 10:
                bird_velocity = jump_strength

        # Bird physics
        bird_velocity += gravity
        bird_y += bird_velocity

        # Pipe management
        current_time = pygame.time.get_ticks()
        if current_time - last_pipe > pipe_frequency:
            create_pipe()
            last_pipe = current_time

        update_pipes()

        # Drawing
        screen.fill(WHITE)
        draw_bird()
        draw_pipes()
        pygame.display.flip()

        if check_collision():
            running = False

        await asyncio.sleep(0.03)  # Use asyncio.sleep for non-blocking delay

    pygame.quit()

async def main():
    weight_queue = asyncio.Queue()
    initialization_complete = asyncio.Event()

    # Run the Tindeq task and game loop concurrently
    tindeq_future = asyncio.ensure_future(tindeq_task(weight_queue, initialization_complete))
    game_future = asyncio.ensure_future(main_game(weight_queue, initialization_complete))

    await asyncio.gather(tindeq_future, game_future)

if __name__ == "__main__":
    asyncio.run(main())
