import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class AnalysisState:
    def __init__(self, total_transactions: int, start_time: datetime, output_file: Path, text_output_file: Optional[Path] = None):
        self.total_transactions = total_transactions
        self.start_time = start_time
        self.output_file = output_file
        self.text_output_file = text_output_file
        self.completed = 0
        self.results = []
        self.frauds = []  # Liste des fraudes pour le fichier texte
        self.lock = threading.Lock()

    def add_result(self, result: Dict[str, Any]) -> int:
        with self.lock:
            self.results.append(result)
            self.completed += 1
            
            # Si c'est une fraude (high/critical), l'ajouter au fichier texte
            risk_level = result.get("risk_level", "low")
            if risk_level in ["high", "critical"]:
                transaction_id = result.get("transaction_id", "")
                anomalies = result.get("anomalies", [])
                if isinstance(anomalies, str):
                    anomalies = [anomalies] if anomalies else []
                elif not isinstance(anomalies, list):
                    anomalies = []
                risk_score = result.get("risk_score", 0)
                
                # Vérifier si cette fraude n'est pas déjà dans la liste (éviter les doublons)
                if not any(f.get("transaction_id") == transaction_id for f in self.frauds):
                    fraud_entry = {
                        "transaction_id": transaction_id,
                        "anomalies": anomalies,
                        "risk_score": risk_score
                    }
                    self.frauds.append(fraud_entry)
                    
                    # Mettre à jour le fichier texte immédiatement
                    if self.text_output_file:
                        self._update_text_file()
            
            return self.completed

    def _update_text_file(self):
        """Met à jour le fichier texte avec toutes les fraudes actuelles."""
        if not self.text_output_file:
            return
        
        try:
            # Réécrire tout le fichier avec toutes les fraudes
            with open(self.text_output_file, 'w', encoding='utf-8') as f:
                for fraud in self.frauds:
                    transaction_id = fraud.get("transaction_id", "")
                    anomalies = fraud.get("anomalies", [])
                    risk_score = fraud.get("risk_score", 0)
                    
                    # Formater les anomalies comme [reason1, reason2, ...]
                    reasons_str = "[" + ", ".join(anomalies) + "]" if anomalies else "[]"
                    
                    # Format: uuid | [reasons] | score/100
                    f.write(f"{transaction_id} | {reasons_str} | {risk_score}/100\n")
        except Exception as e:
            # Ne pas bloquer l'exécution si l'écriture échoue
            print(f"⚠️  Erreur lors de la mise à jour du fichier texte: {e}")

    def get_results(self) -> List[Dict[str, Any]]:
        with self.lock:
            return self.results.copy()

    def save_results(self):
        # Ne plus sauvegarder les JSON - seulement le fichier texte est mis à jour
        pass