# Diagramme du graphe LangGraph - Détection de fraude

```mermaid
graph TD
    START([START]) --> fetch_all_transaction_ids[fetch_all_transaction_ids<br/>Charger les IDs de transactions]
    
    fetch_all_transaction_ids --> process_single_transaction[process_single_transaction<br/>Sélectionner une transaction]
    
    process_single_transaction --> fetch_all_data[fetch_all_data<br/>Charger toutes les données]
    
    fetch_all_data --> analyze_amount_merchant[analyze_amount_merchant<br/>Analyser montant et marchand]
    fetch_all_data --> analyze_country_travel[analyze_country_travel<br/>Analyser pays et voyage]
    fetch_all_data --> analyze_sms_email[analyze_sms_email<br/>Analyser SMS et emails]
    
    analyze_amount_merchant --> merge_prescoring_results[merge_prescoring_results<br/>Fusionner les résultats]
    analyze_country_travel --> merge_prescoring_results
    analyze_sms_email --> merge_prescoring_results
    
    merge_prescoring_results --> aggregate_features_and_score[aggregate_features_and_score<br/>Agréger les features et scorer]
    
    aggregate_features_and_score --> decision_ok[decision_ok<br/>Décision OK]
    
    decision_ok --> save_result_to_json[save_result_to_json<br/>Sauvegarder le résultat]
    
    save_result_to_json --> get_next_transaction[get_next_transaction<br/>Obtenir la transaction suivante]
    
    get_next_transaction -->|continue| process_single_transaction
    get_next_transaction -->|end| analyze_frauds_with_agent[analyze_frauds_with_agent<br/>Analyser les fraudes avec l'agent LLM]
    
    analyze_frauds_with_agent --> END([END])
    
    style START fill:#90EE90
    style END fill:#FFB6C1
    style fetch_all_transaction_ids fill:#87CEEB
    style process_single_transaction fill:#DDA0DD
    style fetch_all_data fill:#F0E68C
    style analyze_amount_merchant fill:#FFA07A
    style analyze_country_travel fill:#FFA07A
    style analyze_sms_email fill:#FFA07A
    style merge_prescoring_results fill:#98FB98
    style aggregate_features_and_score fill:#87CEFA
    style decision_ok fill:#DDA0DD
    style save_result_to_json fill:#F0E68C
    style get_next_transaction fill:#DDA0DD
    style analyze_frauds_with_agent fill:#FF6347
```

## Description des nœuds

### Phase d'initialisation
- **fetch_all_transaction_ids**: Charge tous les IDs de transactions depuis `fraud.json`
- **process_single_transaction**: Sélectionne une transaction à traiter

### Phase de collecte de données
- **fetch_all_data**: Charge toutes les données nécessaires (transaction, profil utilisateur, SMS, emails, locations)

### Phase d'analyse parallèle (prescoring)
- **analyze_amount_merchant**: Analyse les anomalies de montant et de marchand
- **analyze_country_travel**: Analyse les anomalies de pays et de voyage
- **analyze_sms_email**: Analyse les SMS et emails pour détecter des signaux de phishing

### Phase de fusion et scoring
- **merge_prescoring_results**: Fusionne les résultats des 3 analyses parallèles
- **aggregate_features_and_score**: Agrège toutes les features et calcule un score de risque

### Phase de décision et sauvegarde
- **decision_ok**: Prend une décision basée sur le score
- **save_result_to_json**: Sauvegarde le résultat dans `fraud.json`

### Boucle de traitement
- **get_next_transaction**: Obtient la transaction suivante
  - Si `continue`: Retourne à `process_single_transaction` pour traiter la transaction suivante
  - Si `end`: Passe à l'analyse finale avec l'agent LLM

### Phase d'analyse finale
- **analyze_frauds_with_agent**: Analyse toutes les transactions suspectes avec l'agent LLM (LangGraph) pour confirmation finale

## Flux de données

Le graphe traite les transactions de manière séquentielle dans une boucle :
1. Pour chaque transaction, il collecte les données
2. Effectue 3 analyses en parallèle
3. Fusionne les résultats et calcule un score
4. Sauvegarde le résultat
5. Passe à la transaction suivante
6. Une fois toutes les transactions traitées, lance l'analyse finale avec l'agent LLM
