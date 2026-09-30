import pygame
import time
import threading

class AudioEngine:
    def __init__(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        self.deck_a = pygame.mixer.Channel(0)
        self.deck_b = pygame.mixer.Channel(1)
        self.deck_a_sound = None
        self.deck_b_sound = None
        self.current_deck = 'A'
        self.deck_a.set_volume(1.0)
        self.deck_b.set_volume(0.0)

    def load_track(self, deck_name, file_path):
        try:
            sound = pygame.mixer.Sound(file_path)
            if deck_name == 'A': self.deck_a_sound = sound
            elif deck_name == 'B': self.deck_b_sound = sound
            return True
        except Exception as e:
            print(f"Failed to load track {file_path}: {e}")
            return False

    def play_deck(self, deck_name):
        if deck_name == 'A' and self.deck_a_sound: self.deck_a.play(self.deck_a_sound)
        elif deck_name == 'B' and self.deck_b_sound: self.deck_b.play(self.deck_b_sound)

    def stop_deck(self, deck_name):
        if deck_name == 'A': self.deck_a.stop()
        elif deck_name == 'B': self.deck_b.stop()

    def set_volume(self, deck_name, volume):
        volume = max(0.0, min(1.0, volume))
        if deck_name == 'A': self.deck_a.set_volume(volume)
        elif deck_name == 'B': self.deck_b.set_volume(volume)

    def crossfade(self, duration_sec):
        def fade_task(fade_out_deck, fade_in_deck, next_deck_name):
            steps = 50
            sleep_time = duration_sec / steps

            self.play_deck(next_deck_name)
            fade_in_deck.set_volume(0.0)

            for i in range(steps + 1):
                progress = i / steps
                fade_out_deck.set_volume(1.0 - progress)
                fade_in_deck.set_volume(progress)
                time.sleep(sleep_time)

            fade_out_deck.stop()
            self.current_deck = next_deck_name

        fade_out_deck = self.deck_a if self.current_deck == 'A' else self.deck_b
        fade_in_deck = self.deck_b if self.current_deck == 'A' else self.deck_a
        next_deck_name = 'B' if self.current_deck == 'A' else 'A'

        # Only one fade task at a time for MVP
        thread = threading.Thread(target=fade_task, args=(fade_out_deck, fade_in_deck, next_deck_name))
        thread.start()

    def execute_plan(self, next_file_path, transition_duration):
        target_deck = 'B' if self.current_deck == 'A' else 'A'
        self.stop_deck(target_deck)
        if self.load_track(target_deck, next_file_path):
            self.crossfade(transition_duration)
        else:
            print("Plan execution failed.")

    def cleanup(self):
        pygame.mixer.quit()
