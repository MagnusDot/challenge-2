import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class AnalysisState:
    def __init__(self, total_transactions: int, start_time: datetime, output_file: Path):
        self.total_transactions = total_transactions
        self.start_time = start_time
        self.output_file = output_file
        self.completed = 0
        self.results = []
        self.lock = threading.Lock()

    def add_result(self, result: Dict[str, Any]) -> int:
        with self.lock:
            self.results.append(result)
            self.completed += 1
            return self.completed

    def get_results(self) -> List[Dict[str, Any]]:
        with self.lock:
            return self.results.copy()

    def save_results(self):
        with self.lock:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)