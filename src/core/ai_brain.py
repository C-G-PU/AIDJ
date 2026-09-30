import json
import requests

class AIBrain:
    def __init__(self, db_instance, api_url="http://localhost:1234/v1", api_key="lm-studio"):
        self.db = db_instance
        self.api_url = api_url
        self.api_key = api_key

    def _build_prompt(self, user_prompt, available_tracks):
        catalog = []
        for t in available_tracks:
            catalog.append(f"ID: {t['id']}, Title: {t['title']}, BPM: {t['bpm']}, Mood: {t.get('mood', 'N/A')}")
        catalog_str = "\n".join(catalog)

        system_msg = (
            "You are an expert AI DJ. Respond ONLY with JSON:\n"
            "- \"next_track_id\": (integer) ID of the track to play.\n"
            "- \"transition_duration\": (integer) seconds for crossfade.\n"
            "- \"explanation\": (string) message to the user.\n\n"
            f"Catalog:\n{catalog_str}\n\n"
        )
        return system_msg

    def generate_next_action(self, user_prompt):
        tracks = self.db.get_all_tracks()
        if not tracks: return {"error": "Track catalog is empty."}

        system_prompt = self._build_prompt(user_prompt, tracks)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 150
        }
        try:
            response = requests.post(f"{self.api_url}/chat/completions", headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            llm_text = data["choices"][0]["message"]["content"].strip()
            if llm_text.startswith("```json"): llm_text = llm_text[7:]
            if llm_text.endswith("```"): llm_text = llm_text[:-3]
            return json.loads(llm_text.strip())
        except Exception as e:
            return {"error": str(e)}
