# Stratégie d'Optimisation du Prompt

## Problème

Le prompt actuel (`Agent/system_prompt.md`) fait 478 lignes, ce qui est trop long et peut :
- Confondre l'agent avec trop d'informations
- Rendre les mises à jour difficiles
- Augmenter les coûts de tokens
- Réduire la clarté des instructions

## Solution : Approche Minimal → Extended

### Principe

**Commencer avec le minimum nécessaire et étendre seulement si nécessaire.**

### Version Optimisée

Une version optimisée a été créée : `Agent/system_prompt_optimized.md` (80 lignes)

**Contenu minimal** :
1. Identité (2-3 phrases)
2. Mission (1 phrase)
3. Workflow (4-5 étapes)
4. Patterns de fraude (4 patterns, format compact)
5. Règles critiques (5-6 items)
6. Ce qui n'est PAS de la fraude (5 items)

### Critères d'Expansion

Ajouter des détails SEULEMENT si :
- L'agent échoue de manière répétée (>3 fois) sur un pattern spécifique
- Des faux positifs apparaissent (>2) pour un scénario spécifique
- L'agent demande clarification de manière répétée (3+ fois)
- De nouveaux outils sont ajoutés qui nécessitent une explication
- Les métriques de performance montrent une dégradation

### Processus

1. **Tester la version optimisée** d'abord
2. **Mesurer les performances** (précision, rappel, F1)
3. **Identifier les problèmes** spécifiques
4. **Ajouter des détails ciblés** seulement pour ces problèmes
5. **Documenter** pourquoi chaque ajout a été fait

### Avantages

- **Clarté** : Instructions plus faciles à comprendre
- **Maintenabilité** : Plus facile à mettre à jour
- **Coûts** : Moins de tokens utilisés
- **Performance** : Moins de confusion pour l'agent
- **Outils** : Les outils font le travail, pas le prompt

### Migration

Pour utiliser la version optimisée :

1. Renommer le prompt actuel :
   ```bash
   mv Agent/system_prompt.md Agent/system_prompt_full.md
   ```

2. Utiliser la version optimisée :
   ```bash
   mv Agent/system_prompt_optimized.md Agent/system_prompt.md
   ```

3. Tester et ajuster si nécessaire

### Règle Cursor

Une règle a été ajoutée dans `.cursorrules` pour documenter cette approche et guider les futures modifications.
