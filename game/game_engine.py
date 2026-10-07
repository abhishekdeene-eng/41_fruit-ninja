import pygame
import random
import math
import io
import wave

from .fruit import Fruit


# Game Engine

WHITE = (255, 255, 255)
BOMB_BLACK = (30, 30, 30)

FRUIT_COLORS = [
    (220, 60, 60),
    (230, 140, 40),
    (230, 200, 40),
    (90, 180, 90)
]


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.fruits = []
        self.trail = []

        # Default difficulty
        self.difficulty = "Medium"

        self.spawn_interval = 55
        self._spawn_timer = 0
        self.bomb_chance = 0.15
        self.speed_scale = 1.0

        self.lives = 3
        self.score = 0

        self.font = pygame.font.SysFont("Arial", 28)
        self.game_over = False

        # Sound effects
        self.slice_sound = None
        self.bomb_sound = None
        self._setup_sounds()

    def _create_tone(self, frequency, duration, volume):
        """
        Create a simple WAV tone in memory and return it
        as a Pygame Sound object.
        """

        sample_rate = 44100
        number_of_samples = int(sample_rate * duration)

        audio_data = bytearray()

        for i in range(number_of_samples):
            time = i / sample_rate

            # Fade the sound out toward the end.
            fade = 1.0 - (i / number_of_samples)

            sample = int(
                32767
                * volume
                * fade
                * math.sin(2 * math.pi * frequency * time)
            )

            audio_data += sample.to_bytes(
                2,
                byteorder="little",
                signed=True
            )

        audio_file = io.BytesIO()

        with wave.open(audio_file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        audio_file.seek(0)

        return pygame.mixer.Sound(file=audio_file)

    def _setup_sounds(self):
        """Create the sound effects used by the game."""

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # Short high-pitched sound for slicing fruit.
            self.slice_sound = self._create_tone(
                frequency=900,
                duration=0.10,
                volume=0.30
            )

            # Lower sound for bombs/game over.
            self.bomb_sound = self._create_tone(
                frequency=180,
                duration=0.35,
                volume=0.40
            )

        except pygame.error:
            # If audio is unavailable, the game can still run normally.
            self.slice_sound = None
            self.bomb_sound = None

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty

        if difficulty == "Easy":
            self.spawn_interval = 70
            self.speed_scale = 0.8
            self.bomb_chance = 0.08

        elif difficulty == "Hard":
            self.spawn_interval = 40
            self.speed_scale = 1.2
            self.bomb_chance = 0.25

        else:
            # Medium
            self.spawn_interval = 55
            self.speed_scale = 1.0
            self.bomb_chance = 0.15

    def reset_game(self, difficulty):
        # Clear the old game state
        self.fruits = []
        self.trail = []

        self._spawn_timer = 0
        self.lives = 3
        self.score = 0
        self.game_over = False

        # Apply selected difficulty
        self.set_difficulty(difficulty)

    def spawn_fruit(self):
        x = random.randint(60, self.width - 60)

        vy = -random.uniform(13, 16) * self.speed_scale
        vx = random.uniform(-2, 2)
        gravity = 0.35

        kind = (
            "bomb"
            if random.random() < self.bomb_chance
            else "fruit"
        )

        fruit = Fruit(
            x,
            self.height + 30,
            vx,
            vy,
            gravity,
            kind=kind
        )

        fruit.color = (
            BOMB_BLACK
            if kind == "bomb"
            else random.choice(FRUIT_COLORS)
        )

        self.fruits.append(fruit)

    def handle_event(self, event):
        # Mouse movement for slicing
        if event.type == pygame.MOUSEMOTION:
            self._handle_motion(event.pos)

        # Keyboard controls after Game Over
        elif event.type == pygame.KEYDOWN and self.game_over:

            # E = Easy
            if event.key == pygame.K_e:
                self.reset_game("Easy")

            # M = Medium
            elif event.key == pygame.K_m:
                self.reset_game("Medium")

            # H = Hard
            elif event.key == pygame.K_h:
                self.reset_game("Hard")

    def _handle_motion(self, pos):
        previous_pos = self.trail[-1] if self.trail else pos

        x1, y1 = previous_pos
        x2, y2 = pos

        for fruit in self.fruits:
            if fruit.sliced:
                continue

            # Check several points along the swipe segment
            # so fast mouse movements cannot skip over a fruit.
            steps = max(abs(x2 - x1), abs(y2 - y1), 1)

            for i in range(steps + 1):
                t = i / steps

                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t

                if fruit.contains_point(x, y):
                    self._slice(fruit)
                    break

        self.trail.append(pos)

        if len(self.trail) > 15:
            self.trail.pop(0)

    def _slice(self, fruit):
        fruit.sliced = True

        if fruit.kind == "bomb":
            # Play bomb sound
            if self.bomb_sound:
                self.bomb_sound.play()

            self.game_over = True

        else:
            # Play fruit slicing sound
            if self.slice_sound:
                self.slice_sound.play()

            self.score += 1

    def handle_input(self):
        # Reserved for continuously-held-key input.
        pass

    def update(self):
        if self.game_over:
            return

        self._spawn_timer += 1

        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.spawn_fruit()

        still_alive = []

        for fruit in self.fruits:
            fruit.update()

            if fruit.sliced:
                continue

            if fruit.off_screen(self.height):
                if fruit.kind == "fruit":
                    self.lives -= 1

                continue

            still_alive.append(fruit)

        self.fruits = still_alive

        if self.lives <= 0:
            self.lives = 0
            self.game_over = True

            # Play game-over sound when all lives are lost.
            if self.bomb_sound:
                self.bomb_sound.play()

    def render(self, screen):
        # Draw fruits
        for fruit in self.fruits:
            color = getattr(fruit, "color", WHITE)

            pygame.draw.circle(
                screen,
                color,
                (int(fruit.x), int(fruit.y)),
                fruit.radius
            )

        # Draw swipe trail
        if len(self.trail) >= 2:
            pygame.draw.lines(
                screen,
                WHITE,
                False,
                self.trail,
                3
            )

        # Draw score
        score_text = self.font.render(
            f"Score: {self.score}",
            True,
            WHITE
        )

        screen.blit(
            score_text,
            (10, 10)
        )

        # Draw lives
        lives_text = self.font.render(
            f"Lives: {self.lives}",
            True,
            WHITE
        )

        screen.blit(
            lives_text,
            (self.width - 130, 10)
        )

        # Show current difficulty
        difficulty_text = self.font.render(
            f"Difficulty: {self.difficulty}",
            True,
            WHITE
        )

        screen.blit(
            difficulty_text,
            (10, 45)
        )

        # Game Over screen
        if self.game_over:

            # Dark transparent overlay
            overlay = pygame.Surface(
                (self.width, self.height),
                pygame.SRCALPHA
            )

            overlay.fill(
                (0, 0, 0, 180)
            )

            screen.blit(
                overlay,
                (0, 0)
            )

            # GAME OVER title
            game_over_font = pygame.font.SysFont(
                "Arial",
                64,
                bold=True
            )

            game_over_text = game_over_font.render(
                "GAME OVER",
                True,
                WHITE
            )

            game_over_rect = game_over_text.get_rect(
                center=(
                    self.width // 2,
                    self.height // 2 - 110
                )
            )

            screen.blit(
                game_over_text,
                game_over_rect
            )

            # Final score
            final_score_font = pygame.font.SysFont(
                "Arial",
                32
            )

            final_score_text = final_score_font.render(
                f"Final Score: {self.score}",
                True,
                WHITE
            )

            final_score_rect = final_score_text.get_rect(
                center=(
                    self.width // 2,
                    self.height // 2 - 40
                )
            )

            screen.blit(
                final_score_text,
                final_score_rect
            )

            # Difficulty selection
            choose_text = self.font.render(
                "Choose difficulty:",
                True,
                WHITE
            )

            choose_rect = choose_text.get_rect(
                center=(
                    self.width // 2,
                    self.height // 2 + 10
                )
            )

            screen.blit(
                choose_text,
                choose_rect
            )

            # Difficulty options
            options_text = self.font.render(
                "E - Easy     M - Medium     H - Hard",
                True,
                WHITE
            )

            options_rect = options_text.get_rect(
                center=(
                    self.width // 2,
                    self.height // 2 + 55
                )
            )

            screen.blit(
                options_text,
                options_rect
            )

            # Replay instruction
            instruction_text = self.font.render(
                "Press a key to replay",
                True,
                WHITE
            )

            instruction_rect = instruction_text.get_rect(
                center=(
                    self.width // 2,
                    self.height // 2 + 100
                )
            )

            screen.blit(
                instruction_text,
                instruction_rect
            )