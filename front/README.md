# Transaction Risk Viewer

Interface web Vue.js pour visualiser et filtrer les résultats d'analyse de risque des transactions.

## Fonctionnalités

- 📊 Chargement automatique de tous les fichiers JSON dans `scripts/results/`
- 🔍 Filtrage par niveau de risque (low, medium, high, critical)
- 🏷️ Filtrage par type de transaction
- 📋 Copie des IDs de transactions (individuelle ou en masse)
- 📈 Statistiques en temps réel

## Développement local

```bash
cd front
npm install
npm run dev
```

L'application sera accessible sur http://localhost:5173

## Production avec Docker

Le frontend est inclus dans le `docker-compose.yml` à la racine du projet :

```bash
docker-compose up front
```

L'application sera accessible sur http://localhost:3000

## Structure

```
front/
├── src/
│   ├── App.vue          # Composant principal
│   ├── main.js          # Point d'entrée
│   └── style.css        # Styles globaux
├── api_server.py        # Serveur API Python pour servir les JSON
├── Dockerfile           # Configuration Docker
├── nginx.conf          # Configuration Nginx
└── package.json        # Dépendances Node.js
```

## API

Le serveur API expose les endpoints suivants :

- `GET /api/results` - Liste tous les fichiers JSON disponibles
- `GET /api/results/{filename}` - Charge un fichier de résultats spécifique
- `GET /api/transactions` - Charge le dataset des transactions pour récupérer les types
