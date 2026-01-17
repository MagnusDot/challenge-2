"""Agent LangGraph pour la détection de fraude - Point d'entrée principal."""

from .graph import create_fraud_detection_graph

# Export de l'agent principal
__all__ = ["create_fraud_detection_graph"]
