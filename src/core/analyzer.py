import librosa
import os
import json
import csv

class Analyzer:
    def __init__(self, db_instance):
        self.db = db_instance

    def analyze_audio_file(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            y, sr = librosa.load(file_path, duration=30.0)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = float(tempo[0]) if isinstance(tempo, (list, tuple, type(librosa.util.utils.np.ndarray))) else float(tempo)
            title = os.path.splitext(os.path.basename(file_path))[0]
            return {
                "file_path": file_path,
                "title": title,
                "bpm": round(bpm, 2),
                "key_tag": None
            }
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def scan_directory(self, directory_path):
        supported_formats = ('.mp3', '.wav', '.flac', '.ogg')
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(supported_formats):
                    file_path = os.path.join(root, file)
                    analysis = self.analyze_audio_file(file_path)
                    if analysis:
                        self.db.add_track(
                            file_path=analysis["file_path"],
                            title=analysis["title"],
                            bpm=analysis["bpm"]
                        )

    def import_external_metadata(self, file_path):
        if not os.path.exists(file_path): return
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    filename = item.get("filename")
                    if filename:
                        for track in self.db.get_all_tracks():
                            if os.path.basename(track['file_path']) == filename:
                                self.db.add_track(
                                    file_path=track['file_path'], title=track['title'],
                                    bpm=track['bpm'], key_tag=track['key_tag'],
                                    mood=item.get('mood', track['mood']), energy=item.get('energy', track['energy'])
                                )
        elif file_path.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    filename = row.get("filename")
                    if filename:
                        for track in self.db.get_all_tracks():
                            if os.path.basename(track['file_path']) == filename:
                                self.db.add_track(
                                    file_path=track['file_path'], title=track['title'],
                                    bpm=track['bpm'], key_tag=track['key_tag'],
                                    mood=row.get('mood', track['mood']), energy=row.get('energy', track['energy'])
                                )
