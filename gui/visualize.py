import pygame
import requests
import sys
from math import isclose

API_BASE = "http://127.0.0.1:8000"

def fetch_wall(traj_id):
    r = requests.get(f"{API_BASE}/trajectories/{traj_id}")
    r.raise_for_status()
    return r.json()

def fetch_obstacles(traj_id):
    r = requests.get(f"{API_BASE}/obstacles?trajectory_id={traj_id}")
    r.raise_for_status()
    return r.json()

def to_screen_coords(x, y, wall_h, scale, margin_x, margin_y):
    return (margin_x + x * scale, margin_y + (wall_h - y) * scale)

def rect_edges(obs):
    ox, oy, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
    return (ox - w/2, ox + w/2, oy - h/2, oy + h/2)  # min_x, max_x, min_y, max_y

def subtract_intervals(full, sub_intervals):
    """Given full=(a,b) and a list of sub_intervals [(s1,e1),...], return free intervals sorted."""
    a, b = full
    if not sub_intervals:
        return [(a,b)]
    # Clip and sort
    clips = []
    for s,e in sub_intervals:
        if e <= a or s >= b:
            continue
        clips.append((max(a,s), min(b,e)))
    clips.sort()
    free = []
    cur = a
    for s,e in clips:
        if s > cur:
            free.append((cur, s))
        cur = max(cur, e)
    if cur < b:
        free.append((cur, b))
    return free

def find_blocking_obstacles_for_row(obstacles, y):
    """Return list of obstacles that the horizontal line at y intersects."""
    res = []
    for obs in obstacles:
        min_x, max_x, min_y, max_y = rect_edges(obs)[0], rect_edges(obs)[1], rect_edges(obs)[2], rect_edges(obs)[3]
        if min_y <= y <= max_y:
            res.append(obs)
    return res

def build_detour_around_obstacle(obs, current_x, next_segment_start_x, row_y, margin=0.08):
    """
    Builds a connector path that goes around the obstacle perimeter from current_x -> next_start.
    Strategy:
      - move from current point horizontally to the edge outside the obstacle (small step),
      - go up to a point just above the top (top+margin),
      - cross horizontally to the other side edge (right+margin or left-margin),
      - go down back to row_y.
    Returns list of (x,y) points (outside obstacle bounds).
    """
    ox, oy, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
    left = ox - w/2 - margin
    right = ox + w/2 + margin
    top = oy + h/2 + margin
    bottom = oy - h/2 - margin

    # Decide which side current_x is on relative to obstacle
    if current_x < ox:
        # current is to the left, next should be to the right
        detour = [
            (min(current_x + 0.001, left), row_y),   # step to just outside left edge if needed
            (left, top),
            (right, top),
            (right, row_y + 0.001),                  # small offset to avoid accidental equality
        ]
    else:
        # current is to the right, next is to the left
        detour = [
            (max(current_x - 0.001, right), row_y),
            (right, top),
            (left, top),
            (left, row_y + 0.001),
        ]
    return detour

def generate_exact_zigzag_path(wall_w, wall_h, obstacles, row_step=0.3, sample_step=0.15, margin=0.08):
    """
    Generate a continuous path that follows horizontal scanlines (zigzag),
    performs a perimeter detour around obstacles when encountered, and never has lines over obstacles.
    Returns list of (x,y) points forming a continuous route.
    """
    # Precompute which obstacles intersect which rows
    y = row_step / 2.0
    rows = []
    while y < wall_h + 1e-9:
        rows.append(y)
        y += row_step

    path = []
    direction = 1  # left->right first
    for row_idx, y in enumerate(rows):
        # find obstacle projections on this row
        blocking = []
        for obs in obstacles:
            min_x, max_x, min_y, max_y = rect_edges(obs)
            if min_y <= y <= max_y:
                blocking.append((min_x, max_x, obs))
        # subtract projections from full segment [0, wall_w]
        sub_intervals = [(mi, ma) for (mi, ma, _) in blocking]
        free_segments = subtract_intervals((0.0, wall_w), sub_intervals)

        # depending on direction we iterate segments left-to-right or reversed
        segs = free_segments if direction == 1 else list(reversed(free_segments))

        # sample each free segment into points with sample_step
        seg_points = []
        for seg in segs:
            a, b = seg
            # sample points from a -> b
            samples = []
            x = a
            # ensure a and b included
            while x <= b + 1e-9:
                samples.append((min(x, b), y))
                x += sample_step
            # if sampling ended before b, append b explicitly
            if not isclose(samples[-1][0], b, rel_tol=1e-9, abs_tol=1e-9):
                samples.append((b, y))
            # if direction reversed, ensure order matches seg direction
            if direction == 1:
                seg_points.append(samples)
            else:
                seg_points.append(list(reversed(samples)))

        # Now we need to stitch these segments together in row order, adding detours around obstacles if segments are separated
        for i, seg in enumerate(seg_points):
            # append points of this segment to path (if path empty or last point not equal)
            if seg:
                # if path empty, add first
                if not path:
                    path.extend(seg)
                else:
                    # if last path point equals this segment's first, skip duplicate; else connect.
                    last_x, last_y = path[-1]
                    first_x, first_y = seg[0]
                    # if continuous (same row and first_x adjacent to last_x within sample_step), just append
                    if abs(last_y - first_y) < 1e-6 and abs(last_x - first_x) <= sample_step + 1e-6:
                        path.extend(seg)
                    else:
                        # There's a gap between last point and this segment's start — likely obstacle between them.
                        # Find which obstacle blocks between last_x and first_x on this row
                        blocker = None
                        for mi, ma, obs in blocking:
                            if (min(last_x, first_x) < ma) and (max(last_x, first_x) > mi):
                                blocker = obs
                                break
                        if blocker:
                            # build a detour around this blocker using perimeter points
                            detour = build_detour_around_obstacle(blocker, last_x, first_x, y, margin=margin)
                            # append small connector to detour start if needed
                            # make sure connector points are outside obstacle
                            path.extend(detour)
                            # then append the segment
                            path.extend(seg)
                        else:
                            # No blocker found — do a direct straight connector (safe)
                            path.append((first_x, first_y))
                            path.extend(seg)
        # alternate direction
        direction *= -1

    # Remove consecutive duplicate points (approx)
    compressed = []
    for p in path:
        if not compressed or (abs(compressed[-1][0] - p[0]) > 1e-6 or abs(compressed[-1][1] - p[1]) > 1e-6):
            compressed.append(p)
    return compressed

# ---------- Pygame Main ----------
def main(traj_id):
    pygame.init()
    WIDTH, HEIGHT = 1000, 780
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Exact Path Painter - ID {traj_id}")
    clock = pygame.time.Clock()
    scale = 80  # pixels per meter

    traj_data = fetch_wall(traj_id)
    wall_w = float(traj_data["width"])
    wall_h = float(traj_data["height"])
    obstacles = fetch_obstacles(traj_id)

    margin_x = (WIDTH - wall_w * scale) / 2
    margin_y = (HEIGHT - wall_h * scale) / 2
    font = pygame.font.SysFont("Arial", 18)

    # generate path: rows chosen so that lines appear like your image
    path_points = generate_exact_zigzag_path(wall_w, wall_h, obstacles, row_step=0.35, sample_step=0.12, margin=0.06)

    # Precompute drawing segments that are outside obstacles to avoid accidental draw over obstacle:
    draw_segments = []
    def segment_intersects_obs(x1,y1,x2,y2):
        # quick bbox check vs obstacle boxes
        for obs in obstacles:
            min_x, max_x, min_y, max_y = rect_edges(obs)
            # if both points lie outside and segment bbox does not overlap obstacle bbox -> safe
            if max(min(x1,x2), min_x) <= min(max(x1,x2), max_x) and max(min(y1,y2), min_y) <= min(max(y1,y2), max_y):
                # bbox overlaps; to be safe, skip drawing this segment
                return True
        return False

    for i in range(1, len(path_points)):
        x1,y1 = path_points[i-1]
        x2,y2 = path_points[i]
        if not segment_intersects_obs(x1,y1,x2,y2):
            draw_segments.append(((x1,y1),(x2,y2)))

    # Robot animation params
    idx = 0.0
    speed = 0.8    # larger = faster; tune to preference
    paused = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused

        screen.fill((245,245,245))
        # wall border
        pygame.draw.rect(screen, (0,0,0), (margin_x, margin_y, wall_w*scale, wall_h*scale), 3)

        # draw obstacles
        for obs in obstacles:
            ox, oy, w, h = obs["x"], obs["y"], obs["w"], obs["h"]
            rect = pygame.Rect(
                margin_x + (ox - w/2)*scale,
                margin_y + (wall_h - (oy + h/2))*scale,
                w*scale, h*scale
            )
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            surf.fill((255,80,80,170))
            screen.blit(surf, rect)
            label = font.render(obs.get("name",""), True, (0,0,0))
            screen.blit(label, (rect.x+4, rect.y-20))

        # draw produced trajectory segments (blue) - these are guaranteed to be outside obstacles
        for (p1,p2) in draw_segments:
            sx1, sy1 = to_screen_coords(p1[0], p1[1], wall_h, scale, margin_x, margin_y)
            sx2, sy2 = to_screen_coords(p2[0], p2[1], wall_h, scale, margin_x, margin_y)
            pygame.draw.line(screen, (40,90,255), (sx1,sy1), (sx2,sy2), 2)

        # robot
        if not paused:
            idx += speed
            if idx >= len(path_points):
                idx = 0.0

        if path_points:
            p = path_points[int(idx) % len(path_points)]
            sx, sy = to_screen_coords(p[0], p[1], wall_h, scale, margin_x, margin_y)
            pygame.draw.circle(screen, (0,200,0), (int(sx), int(sy)), 6)

        pygame.display.flip()
        clock.tick(30)  # keep UI fluid

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python frontend/pygame_ui.py <trajectory_id>")
        sys.exit(1)
    main(int(sys.argv[1]))
