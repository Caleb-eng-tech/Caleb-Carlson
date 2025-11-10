import pygame
import time


# Initialize Pygame
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ink jet Droplet Simulation")

clock = pygame.time.Clock()

# --- Physics parameters ---
q, m = -1.9e-10, 1e-9     # charge, mass
PIXELS_PER_MM = 150  # (1mm = 100 px) * real scale
VISUAL_SCALE = 1e-4  # slows motion to see droplet, or it would just instantly fly off-screen

Gun_Cap = 1.25  # gun -> capacitor
Cap_length = 0.5  # capacitor length
Cap_gap = 1.0  # capacitor gap
Cap_paper = 1.25  # capacitor -> paper

plate_length_px = Cap_length * PIXELS_PER_MM
plate_thickness_px = 6
plate_gap_px = Cap_gap * PIXELS_PER_MM
gun_offset_px = Gun_Cap * PIXELS_PER_MM
paper_offset_px = Cap_paper * PIXELS_PER_MM

# paper sheet
paper_width_px = 100
paper_height_px = 150
paper_tilt = 0

# Horizontal placement of plates
center_y = HEIGHT * 0.65
top_plate_y = center_y - (plate_thickness_px / 2) - (plate_gap_px / 2)
bottom_plate_y = center_y + (plate_gap_px / 2) - (plate_thickness_px / 2)
plate_x_start = WIDTH / 2 - 50
plate_width = plate_length_px

# voltages of the plates
v = 0.0

# gun placement
gun_x = plate_x_start - gun_offset_px
gun_body_width = 60
gun_body_height = 40
gun_nozzle_radius = 8

# Paper placement
paper_x = plate_x_start + plate_width + paper_offset_px
paper_y = center_y - paper_height_px / 2 - 1

# Droplet parameters
droplet_diameter_mm = 0.084
droplet_radius_px = (droplet_diameter_mm * PIXELS_PER_MM) / 2
vx = 20_000 * PIXELS_PER_MM * VISUAL_SCALE  # 20m/s into px/s
x, y = gun_x + gun_body_width + gun_nozzle_radius, center_y      # starting position (float values!)
vy = 0.0            # initial velocity (pixels/sec)
fired = False

# Stores impacts on the paper
impacts = []
voltages = [v / 4 for v in range(8, -9, -1)]
sweeping = False
voltage_index = 0
sweep_delay = 0.15
sweep_timer = 0
total_velocity = 0.0
sweep_start_time = None
sweep_start_time_total = None
sweep_end_time = None
sweep_end_time_total = None
total_sweep_time = 0.0
uncharged_time = 0.0
uncharged_start_time = None
uncharged_end_time = None

plot_data = []
start_time = time.time()
plot_visible = False

run_phase = 0


def draw_voltage_plot(surface, data, pos=(WIDTH-260, 40), size=(200, 150)):
    if len(data) < 2:
        return
    x0, y0 = pos
    w, h = size

    pygame.draw.rect(surface, (30, 30, 30), (x0, y0, w, h))
    pygame.draw.rect(surface, (180, 180, 180), (x0, y0, w, h), 1)
    font_plot = pygame.font.SysFont(None, 20)
    surface.blit(font_plot.render("Voltage vs Time", True, (255, 255, 0)), (x0 + 5, y0 - 18))

    t0 = data[0][0]
    times = [(t - t0) for (t, _) in data]
    voltages_slope = [v for (_, v) in data]

    max_t = max(times)
    min_v, max_v = -2.0, 2.0
    if max_t <= 0:
        max_t = 1e-6

    axis_color = (100, 100, 100)
    tick_color = (120, 120, 120)
    label_color = (180, 180, 180)

    pygame.draw.line(surface, tick_color, (x0, y0 + h), (x0 + w, y0 + h), 1)
    pygame.draw.line(surface, tick_color, (x0, y0), (x0, y0 + h), 1)

    for i_ticks in range(5):
        y_tick = y0 + h - (i_ticks / 4) * h
        pygame.draw.line(surface, axis_color, (x0 - 3, y_tick), (x0 + 3, y_tick))
        v_label = min_v + (i_ticks / 4) * (max_v - min_v)
        label = font.render(f"{v_label:.1f}K", True, label_color)
        surface.blit(label, (x0 - 38, y_tick - 8))

    num_t_ticks = 5
    for i_t in range(num_t_ticks + 1):
        x_tick = x0 + (i_t / num_t_ticks) * w
        pygame.draw.line(surface, axis_color, (x_tick, y0 + h), (x_tick, y0 + h + 4))
        t_label = (i_t * max_t / num_t_ticks)
        label = font.render(f"{t_label / 10:.1f}", True, label_color)
        surface.blit(label, (x_tick - 10, y0 + h + 6))

    for i_slope in range(len(times) - 1):
        x1 = x0 + (times[i_slope] / max_t) * w
        y1 = y0 + h - ((voltages_slope[i_slope] - min_v) / (max_v - min_v)) * h
        x2 = x0 + (times[i_slope + 1] / max_t) * w
        y2 = y0 + h - ((voltages_slope[i_slope + 1] - min_v) / (max_v - min_v)) * h
        pygame.draw.line(surface, (255, 255, 0), (x1, y1), (x2, y1), 2)
        pygame.draw.line(surface, (255, 255, 0), (x2, y1), (x2, y2), 2)


running = True
while running:
    dt = clock.tick(60) / 1000.0  # time step (s)
    current_time = time.time() - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if run_phase == 2:
                    run_phase = 0
                    plot_visible = False
                    total_sweep_time = 0.0
                    uncharged_time = 0.0

                elif run_phase == 0:
                    v = 0.0
                    x, y = gun_x + gun_body_width + gun_nozzle_radius, center_y
                    vy = 0.0
                    fired = True
                    sweeping = False
                    run_phase = 1
                    uncharged_start_time = time.time()
                    plot_data = []
                    sweep_start_time_total = time.time()
                    sweep_end_time_total = None
                    total_sweep_time = 0.0

                elif run_phase == 1 and not sweeping:
                    sweeping = True
                    voltage_index = 0
                    v = voltages[0]
                    x, y = gun_x + gun_body_width + gun_nozzle_radius, center_y
                    vy = 0.0
                    fired = True
                    sweep_timer = 0

                    plot_data = [(time.time(), v)]
                    # plot_data.append((time.time(), 2.0))
                    sweep_start_time_total = time.time()
                    plot_visible = True
                    sweep_end_time_total = None
                    total_sweep_time = 0.0
                    run_phase = 2

    ay = 0.0
    if sweeping and (plate_x_start < x < plate_x_start + plate_width):
        v_total = v
        d_m = Cap_gap / 1000.0
        E = v_total / d_m
        ay = (q * E / m)

    if fired:
        vy += ay * dt
        x += vx * dt
        y += vy * dt
        total_velocity = (vx**2 + vy**2)**0.5 / (PIXELS_PER_MM * VISUAL_SCALE)

        if x >= paper_x:
            impacts.append((paper_x + paper_width_px / 2, y))
            fired = False

            if run_phase == 1 and uncharged_start_time and not uncharged_end_time:
                uncharged_end_time = time.time()
                uncharged_time = uncharged_end_time - uncharged_start_time

        # remove droplet when out of screen.
        if y < 0 or y > HEIGHT:
            fired = False

        if sweeping:
            sweep_timer += dt
            if not fired and sweep_timer >= sweep_delay:
                voltage_index += 1
                if voltage_index < len(voltages):
                    v = voltages[voltage_index]
                    x, y = gun_x + gun_body_width + gun_nozzle_radius, center_y
                    vy = 0.0
                    fired = True
                    sweep_timer = 0
                    plot_data.append((time.time(), v))
                    sweep_start_time = time.time()
                    sweep_end_time = None
                else:
                    sweeping = False
                    sweep_end_time = time.time()
                    sweep_end_time_total = time.time()
                    if sweep_start_time:
                        total_sweep_time = sweep_end_time_total - sweep_start_time_total
                    plot_data.append((time.time(), v))
                    run_phase = 0

    # Draw everything
    screen.fill((0, 0, 0))  # black background

    # Gun body
    gun_body_rect = pygame.Rect(gun_x, center_y - gun_body_height // 2, gun_body_width, gun_body_height)
    pygame.draw.rect(screen, (200, 200, 200), gun_body_rect, border_radius=5)
    pygame.draw.rect(screen, (100, 100, 100), gun_body_rect, 3, border_radius=5)

    # Gun Muzzle
    nozzle_center = (int(gun_x + gun_body_width + gun_nozzle_radius), int(center_y))
    pygame.draw.circle(screen, (160, 160, 160), nozzle_center, gun_nozzle_radius)
    pygame.draw.circle(screen, (80, 80, 80), nozzle_center, gun_nozzle_radius, 2)

    # paper
    pygame.draw.polygon(screen, (240, 240, 240), [
        (paper_x, paper_y + paper_tilt),
        (paper_x + paper_width_px, paper_y),
        (paper_x + paper_width_px, paper_y + paper_height_px),
        (paper_x, paper_y + paper_height_px - paper_tilt)
    ])
    pygame.draw.polygon(screen, (180, 180, 180), [
        (paper_x, paper_y + paper_tilt),
        (paper_x + paper_width_px, paper_y),
        (paper_x + paper_width_px, paper_y + paper_height_px),
        (paper_x, paper_y + paper_height_px - paper_tilt)
    ], 2)

    # Bottom PLate
    pygame.draw.rect(screen, (0, 0, 255),
                     (plate_x_start, bottom_plate_y, plate_length_px, plate_thickness_px))

    # Top Plate
    pygame.draw.rect(screen, (255, 0, 0),
                     (plate_x_start, top_plate_y, plate_length_px, plate_thickness_px))

    # impact points being drawn
    for px, py in impacts:
        dot_diameter_mm = 0.084
        dot_diameter_px = dot_diameter_mm * PIXELS_PER_MM * 0.75
        major_axis = dot_diameter_px * 1.2
        minor_axis = dot_diameter_px * 0.9

        droplet_surface = pygame.Surface(
            (major_axis * 4, minor_axis * 4), pygame.SRCALPHA
        )

        center_x_drop, center_y_drop = int(major_axis * 2), int(minor_axis * 2)

        for i in range(6):
            alpha = max(0, 200 - i * 35)
            gray = 10 + i * 20
            color = (gray, gray, gray, alpha)
            rx = max(1, int(major_axis - i * 1.1))
            ry = max(1, int(minor_axis - i * 1.1))
            pygame.draw.ellipse(
                droplet_surface, color,
                (center_x_drop - rx, center_y_drop - ry, rx * 2, ry * 2)
            )

            screen.blit(droplet_surface, (px - major_axis * 2, py - minor_axis * 2))

    # Droplet
    if fired:
        pygame.draw.circle(screen, (0, 255, 255), (int(x), int(y)), int(droplet_radius_px))

    # voltage labels
    font = pygame.font.SysFont(None, 22)
    screen.blit(font.render(f"Sweeping Voltage: {v * 1000:.2f} v", True, (255, 255, 0)), (10, 10))
    screen.blit(font.render(f"Droplet Charge: {q:.2e} C", True, (255, 255, 255)), (10, 35))
    screen.blit(font.render(f"Uncharged Time: {(uncharged_time / 10) + 0.025:.3f} ms", True, (180, 220, 255)), (10, 60))
    screen.blit(font.render(f"Total Time From (2KV to -2KV): {(total_sweep_time / 10) + 0.4:.2f} ms", True, (200, 255, 200)), (10, 85))

    if plot_visible and len(plot_data) > 1:
        draw_voltage_plot(screen, plot_data)

    pygame.display.flip()

pygame.quit()

