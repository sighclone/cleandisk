import os
import shutil
import sys
import time
import pygame
import threading

# Get details about the disk space
def get_free_space_bytes(path):
    total, used, free = shutil.disk_usage(path)
    return total, used, free

# Write random data to a dummy file until the disk is full
def write_until_full(filename, chunk_size=1024*1024, ui_callback=None):
    path = os.path.dirname(os.path.abspath(filename)) or '.'
    _, _, free_space = get_free_space_bytes(path)
    written = 0
    bar_length = 40
    try:
        with open(filename, 'wb') as f:
            while True:
                if written + chunk_size > free_space:
                    to_write = free_space - written
                    if to_write > 0:
                        f.write(os.urandom(to_write))
                        written += to_write
                        progress = written / free_space if free_space else 1
                        if ui_callback:
                            ui_callback(progress)
                        else:
                            
                            # Console progress bar
                            filled = int(bar_length * progress)
                            bar = '=' * filled + '-' * (bar_length - filled)
                            print(f"\r[{bar}] {progress*100:.2f}%", end='', flush=True)
                    break
                f.write(os.urandom(chunk_size))
                written += chunk_size
                progress = written / free_space if free_space else 1
                if ui_callback:
                    ui_callback(progress)
                else:
                    
                    # Console progress bar
                    filled = int(bar_length * progress)
                    bar = '=' * filled + '-' * (bar_length - filled)
                    print(f"\r[{bar}] {progress*100:.2f}%", end='', flush=True)
    except OSError as e:
        if ui_callback:
            ui_callback(1, error=str(e))
        else:
            print(f"\nStopped writing: {e}")
    if not ui_callback:
        print(f"\nTotal bytes written: {written}")

def format_size(val):
    for unit in ['B', 'kB', 'MB', 'GB', 'TB', 'PB']:
        if val < 1024:
            return f"{val:.2f} {unit}"
        val /= 1024
    return f"{val:.2f} PB"

def main(disk_path):
    pygame.init()
    WIDTH, HEIGHT = 700, 350
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Disk Free Space Cleaner")
    font = pygame.font.SysFont(None, 28)
    bigfont = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()

    # Get disk stats
    path = disk_path
    total, used, free = get_free_space_bytes(path)
    total_str = format_size(total)
    used_str = format_size(used)
    free_str = format_size(free)

    # UI states
    state = 'prompt'  # prompt, writing, done, error, countdown, deleted, interrupted
    progress = 0
    error_msg = ''
    countdown = 5
    filename = "filled_disk.bin"
    running = True
    proceed = None

    def draw_prompt():
        screen.fill((30, 30, 30))
        y = 40
        screen.blit(bigfont.render("Disk Stats", True, (255,255,255)), (30, y))
        y += 40
        screen.blit(font.render(f"Total: {total_str}", True, (200,200,200)), (30, y))
        y += 30
        screen.blit(font.render(f"Used: {used_str}", True, (200,200,200)), (30, y))
        y += 30
        screen.blit(font.render(f"Free: {free_str}", True, (200,200,200)), (30, y))
        y += 50
        screen.blit(font.render("Proceed with clean delete free space?", True, (255,255,0)), (30, y))
        yes_rect = pygame.Rect(60, y+50, 100, 40)
        no_rect = pygame.Rect(220, y+50, 100, 40)
        pygame.draw.rect(screen, (0,200,0), yes_rect)
        pygame.draw.rect(screen, (200,0,0), no_rect)
        screen.blit(font.render("Yes", True, (0,0,0)), (yes_rect.x+30, yes_rect.y+8))
        screen.blit(font.render("No", True, (0,0,0)), (no_rect.x+35, no_rect.y+8))
        return yes_rect, no_rect

    def draw_progress():
        screen.fill((30, 30, 30))
        screen.blit(bigfont.render("Wiping free space...", True, (255,255,255)), (30, 40))
        bar_x, bar_y, bar_w, bar_h = 30, 120, 500, 40
        pygame.draw.rect(screen, (80,80,80), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * progress)
        # screen.blit(font.render(f"{progress*100:.2f}%", True, (255,255,255)), (bar_x+bar_w+10, bar_y))
        screen.blit(font.render(f"{progress*100:.2f}%", True, (255,255,255)), (bar_x, bar_y-25))
        pygame.draw.rect(screen, (0,200,0), (bar_x, bar_y, fill_w, bar_h))

    def draw_done():
        screen.fill((30, 30, 30))
        screen.blit(bigfont.render("Wipe complete!", True, (0,255,0)), (30, 40))
        screen.blit(font.render("Checking file existence...", True, (255,255,255)), (30, 100))
        exists = os.path.exists(filename)
        msg = f"File '{filename}' exists." if exists else f"File '{filename}' does not exist."
        screen.blit(font.render(msg, True, (255,255,0)), (30, 140))
        screen.blit(font.render("File will be deleted in 5 seconds.", True, (255,255,255)), (30, 200))
        screen.blit(font.render("Press ESC to interrupt deletion.", True, (255,100,100)), (30, 230))
        screen.blit(font.render(f"Deleting in {countdown} seconds...", True, (255,255,255)), (30, 270))

    def draw_deleted():
        screen.fill((30, 30, 30))
        screen.blit(bigfont.render("File deleted.", True, (0,255,0)), (30, 100))
        screen.blit(font.render("Press any key to exit.", True, (255,255,255)), (30, 160))

    def draw_interrupted():
        screen.fill((30, 30, 30))
        screen.blit(bigfont.render("Deletion interrupted!", True, (255,100,100)), (30, 100))
        screen.blit(font.render("File not deleted.", True, (255,255,0)), (30, 160))
        screen.blit(font.render("Press any key to exit.", True, (255,255,255)), (30, 200))

    def draw_error():
        screen.fill((30, 30, 30))
        screen.blit(bigfont.render("Error!", True, (255,0,0)), (30, 100))
        screen.blit(font.render(error_msg, True, (255,255,0)), (30, 160))
        screen.blit(font.render("Press any key to exit.", True, (255,255,255)), (30, 200))

    def ui_progress_callback(p, error=None):
        nonlocal progress, state, error_msg
        progress = p
        if error:
            error_msg = error
            state = 'error'

    def start_wipe():
        nonlocal state, countdown, last_countdown_tick
        state = 'writing'
        write_until_full(filename, ui_callback=ui_progress_callback)
        if state != 'error':
            state = 'done'
            countdown = 5
            last_countdown_tick = time.time()

    yes_rect, no_rect = None, None
    last_countdown_tick = None
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if state == 'prompt' and event.type == pygame.MOUSEBUTTONDOWN:
                if yes_rect and yes_rect.collidepoint(event.pos):
                    # Start file wipe in a separate thread
                    threading.Thread(target=start_wipe, daemon=True).start()
                elif no_rect and no_rect.collidepoint(event.pos):
                    running = False
            elif state in ('deleted', 'interrupted', 'error') and event.type == pygame.KEYDOWN:
                running = False
            elif state == 'done' and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state = 'interrupted'

        if state == 'prompt':
            yes_rect, no_rect = draw_prompt()
        elif state == 'writing':
            draw_progress()
        elif state == 'done':
            draw_done()

            # Countdown logic
            now = time.time()
            if last_countdown_tick and now - last_countdown_tick >= 1:
                countdown -= 1
                last_countdown_tick = now
                if countdown <= 0:
                    try:
                        os.remove(filename)
                        state = 'deleted'
                    except Exception as e:
                        error_msg = str(e)
                        state = 'error'
        elif state == 'deleted':
            draw_deleted()
        elif state == 'interrupted':
            draw_interrupted()
        elif state == 'error':
            draw_error()
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()
    sys.exit()

# if sys arg available, use it as disk path, else use current directory
if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)) or '.')
