import random
import sys
from dataclasses import dataclass

import pygame


WIDTH, HEIGHT = 960, 640
FPS = 60
LANE_COUNT = 4
HIT_LINE_Y = HEIGHT - 140
NOTE_SPEED = 320  # pixels per second
SPAWN_AHEAD_TIME = 2.0
HIT_WINDOW = 0.16
GREAT_WINDOW = 0.08

LANE_KEYS = [pygame.K_LEFT, pygame.K_DOWN, pygame.K_UP, pygame.K_RIGHT]
LANE_LABELS = ["LEFT", "DOWN", "UP", "RIGHT"]
LANE_COLORS = [
    (93, 173, 226),
    (88, 214, 141),
    (245, 176, 65),
    (236, 112, 99),
]

BG_COLOR = (15, 15, 28)
GRID_COLOR = (60, 60, 86)
TEXT_COLOR = (235, 235, 242)


@dataclass
class Note:
    lane: int
    time: float
    judged: bool = False


class RhythmGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Overdriven: Basic Rhythm Demo")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 28)
        self.small_font = pygame.font.SysFont("consolas", 20)

        self.bpm = 112
        self.beat_interval = 60.0 / self.bpm
        self.song_length = 45.0

        self.notes = self.generate_chart()
        self.next_note_idx = 0

        self.song_time = 0.0
        self.running = True
        self.started = False

        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hits = 0
        self.greats = 0
        self.misses = 0
        self.feedback = "Press SPACE to start the beat"
        self.feedback_timer = 0.0

    def generate_chart(self) -> list[Note]:
        notes: list[Note] = []
        start_time = 2.0
        beat_count = int((self.song_length - start_time) / self.beat_interval)

        pattern = [0, 1, 2, 3, 2, 1]
        for beat in range(beat_count):
            t = start_time + beat * self.beat_interval

            if beat % 8 in (6, 7):
                lane = random.randint(0, LANE_COUNT - 1)
            else:
                lane = pattern[beat % len(pattern)]

            notes.append(Note(lane=lane, time=t))

            if beat % 16 == 12:
                extra_lane = (lane + random.randint(1, 3)) % LANE_COUNT
                notes.append(Note(lane=extra_lane, time=t + self.beat_interval * 0.5))

        notes.sort(key=lambda n: n.time)
        return notes

    def lane_x(self, lane: int) -> float:
        lane_width = WIDTH // LANE_COUNT
        return lane * lane_width + lane_width / 2

    def note_y(self, note_time: float) -> float:
        dt = note_time - self.song_time
        return HIT_LINE_Y - (SPAWN_AHEAD_TIME - dt) * NOTE_SPEED

    def judge_note(self, lane: int) -> None:
        candidate = None
        candidate_delta = 999.0

        for note in self.notes:
            if note.judged or note.lane != lane:
                continue
            delta = abs(note.time - self.song_time)
            if delta < candidate_delta:
                candidate = note
                candidate_delta = delta
            if note.time - self.song_time > HIT_WINDOW:
                break

        if candidate and candidate_delta <= HIT_WINDOW:
            candidate.judged = True
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

            if candidate_delta <= GREAT_WINDOW:
                self.score += 350
                self.greats += 1
                self.feedback = "GREAT!"
            else:
                self.score += 200
                self.hits += 1
                self.feedback = "GOOD"
            self.feedback_timer = 0.4
        else:
            self.combo = 0
            self.misses += 1
            self.feedback = "MISS"
            self.feedback_timer = 0.4

    def auto_miss_old_notes(self) -> None:
        for note in self.notes:
            if note.judged:
                continue
            if self.song_time - note.time > HIT_WINDOW:
                note.judged = True
                self.combo = 0
                self.misses += 1

    def draw(self) -> None:
        self.screen.fill(BG_COLOR)
        lane_width = WIDTH // LANE_COUNT

        for lane in range(LANE_COUNT):
            x = lane * lane_width
            color = tuple(min(255, c + 20) for c in LANE_COLORS[lane])
            pygame.draw.rect(self.screen, color, (x + 4, 0, lane_width - 8, HEIGHT), width=2)

            label = self.small_font.render(LANE_LABELS[lane], True, TEXT_COLOR)
            self.screen.blit(label, (x + lane_width / 2 - label.get_width() / 2, HEIGHT - 45))

        pygame.draw.line(self.screen, GRID_COLOR, (0, HIT_LINE_Y), (WIDTH, HIT_LINE_Y), 4)

        for note in self.notes:
            if note.judged:
                continue
            y = self.note_y(note.time)
            if -30 <= y <= HEIGHT + 30:
                x = self.lane_x(note.lane)
                pygame.draw.circle(self.screen, LANE_COLORS[note.lane], (int(x), int(y)), 22)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), 22, width=3)

        score_text = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        combo_text = self.font.render(f"Combo: {self.combo}", True, TEXT_COLOR)
        miss_text = self.small_font.render(
            f"Great: {self.greats}  Good: {self.hits}  Miss: {self.misses}", True, TEXT_COLOR
        )

        self.screen.blit(score_text, (20, 20))
        self.screen.blit(combo_text, (20, 56))
        self.screen.blit(miss_text, (20, 96))

        if self.feedback_timer > 0:
            fb = self.font.render(self.feedback, True, (255, 245, 157))
            self.screen.blit(fb, (WIDTH / 2 - fb.get_width() / 2, 20))

        if not self.started:
            prompt = self.font.render("SPACE: Start  |  ESC: Quit", True, TEXT_COLOR)
            self.screen.blit(prompt, (WIDTH / 2 - prompt.get_width() / 2, HEIGHT / 2 - 20))

        if self.started and self.song_time >= self.song_length:
            end_text = self.font.render("Song complete! Press R to restart", True, TEXT_COLOR)
            self.screen.blit(end_text, (WIDTH / 2 - end_text.get_width() / 2, HEIGHT / 2 - 20))
            max_combo_text = self.small_font.render(f"Max Combo: {self.max_combo}", True, TEXT_COLOR)
            self.screen.blit(max_combo_text, (WIDTH / 2 - max_combo_text.get_width() / 2, HEIGHT / 2 + 20))

        pygame.display.flip()

    def restart(self) -> None:
        self.notes = self.generate_chart()
        self.song_time = 0.0
        self.started = False
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hits = 0
        self.greats = 0
        self.misses = 0
        self.feedback = "Press SPACE to start the beat"
        self.feedback_timer = 0.0

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE and not self.started:
                        self.started = True
                    elif event.key == pygame.K_r and self.song_time >= self.song_length:
                        self.restart()
                    elif self.started and self.song_time < self.song_length:
                        if event.key in LANE_KEYS:
                            self.judge_note(LANE_KEYS.index(event.key))

            if self.started and self.song_time < self.song_length:
                self.song_time += dt
                self.auto_miss_old_notes()

            if self.feedback_timer > 0:
                self.feedback_timer -= dt

            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    RhythmGame().run()
