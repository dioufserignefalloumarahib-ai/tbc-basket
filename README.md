# TBC — Thiadiaye Basket Club

Application web Flask de gestion du club : dashboard, joueurs, équipes, matchs, terrain, réservations, statistiques, tableau de score et préparation NBA.

## Lancer

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://127.0.0.1:5000.

Compte de démonstration : `admin` / `admin123`. Changez le mot de passe avant une mise en production et définissez `SECRET_KEY` dans `.env`.

La base SQLite est créée dans `database/tbc.db` au premier lancement. Les joueurs, équipes et matchs initiaux sont explicitement des données de démonstration. Les scores NBA ne sont pas inventés : la section reste vide tant qu'une source API légale n'est pas configurée via `NBA_API_KEY` et `NBA_API_BASE_URL`.
