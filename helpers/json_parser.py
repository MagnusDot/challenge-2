import json
import re

def parse_json_response(response_text: str) -> str:
    """Nettoie et extrait le JSON d'une réponse qui peut contenir du markdown ou du texte supplémentaire.
    
    Args:
        response_text: La réponse brute qui peut contenir du JSON
        
    Returns:
        Le JSON nettoyé prêt à être parsé
    """
    if not response_text:
        return "{}"
    
    response_text = response_text.strip()

    # Extraire le JSON des blocs de code markdown
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        if json_end > json_start:
            response_text = response_text[json_start:json_end].strip()
    elif response_text.startswith("```"):
        json_start = response_text.find("```") + 3
        json_end = response_text.rfind("```")
        if json_end > json_start:
            response_text = response_text[json_start:json_end].strip()
    
    # Chercher un objet JSON valide dans la réponse
    # Chercher le premier { ou [ qui commence un objet/array JSON
    first_brace = response_text.find('{')
    first_bracket = response_text.find('[')
    
    if first_brace >= 0 and (first_bracket < 0 or first_brace < first_bracket):
        # Commence par un objet JSON
        start_pos = first_brace
        # Trouver la dernière accolade correspondante
        brace_count = 0
        for i in range(start_pos, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    response_text = response_text[start_pos:i+1]
                    break
    elif first_bracket >= 0:
        # Commence par un array JSON
        start_pos = first_bracket
        # Trouver le dernier crochet correspondant
        bracket_count = 0
        for i in range(start_pos, len(response_text)):
            if response_text[i] == '[':
                bracket_count += 1
            elif response_text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    response_text = response_text[start_pos:i+1]
                    break
    
    # Nettoyer les caractères de contrôle et les espaces en fin de ligne
    response_text = response_text.strip()
    
    # Supprimer les commentaires JSON potentiels (non standard mais parfois présents)
    response_text = re.sub(r'//.*?$', '', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
    
    return response_text