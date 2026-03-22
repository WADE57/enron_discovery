# Enron Discovery - Projet 2026

Plateforme d'e-Discovery construite avec Django + PostgreSQL pour analyser le corpus Enron (plus de 500 000 emails).

## 1. Contexte et objectif

L'objectif est de transformer un corpus d'emails non structure en application web d'investigation permettant de:

- naviguer dans les echanges,
- rechercher des informations critiques,
- identifier des acteurs cles,
- reconstruire des conversations (threads).

Source des donnees: Enron Email Dataset (CMU)  
https://www.cs.cmu.edu/~enron/

## 2. Stack technique

- Backend et interface: Django 5.2
- Base de donnees: PostgreSQL 16 (Docker)
- Recherche plein texte: PostgreSQL FTS (SearchVector + index GIN)
- Parsing/ingestion: Python (`email`, `re`, `datetime`)
- Environnement Python: `venv`
- Versionnage: Git

## 3. Architecture du projet

```text
enron_discovery/
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── enron_mail_20150507.tar.gz
├── data/
├── maildir/                               # non versionne (corpus)
├── scripts/
│   ├── import_enron.py                    # scripts exploratoires
│   └── parse_email.ipynb                  # usage Pandas exploratoire
├── polls/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   ├── tests.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_...
│   │   ├── 0003_...
│   │   └── 0004_...
│   ├── management/
│   │   └── commands/
│   │       └── import_enron.py            # commande principale d'import
│   └── templates/
│       ├── dashboard.html
│       ├── search.html
│       ├── thread_detail.html
│       └── influence.html                 # optionnel
└── enron_discovery/
	├── settings.py
	├── urls.py
	├── asgi.py
	└── wsgi.py
```

## 4. Modelisation SQL (MCD logique)

### 4.1 Entites

#### Employee
- `email` (unique)
- `name`

#### Folder
- `name`

#### Email
- `message_id` (unique)
- `date`
- `subject`
- `body`
- `from_employee` (FK -> Employee)
- `to_employees` (M2M -> Employee)
- `cc_employees` (M2M -> Employee)
- `bcc_employees` (M2M -> Employee)
- `in_reply_to` (FK recursive -> Email)
- `folder` (FK -> Folder)
- `search_vector` (FTS)

#### Attachment
- `email` (FK -> Email)
- `filename`
- `content_type`
- `size`

### 4.2 Contraintes et integrite
- unicite: `Employee.email`, `Email.message_id`
- cles etrangeres: expediteur, dossier, pieces jointes, thread parent
- tables M2M dediees pour To/Cc/Bcc

### 4.3 Optimisation
- index B-tree sur `date`
- index B-tree sur `message_id`
- index GIN sur `search_vector` (FTS)

## 5. Ingestion et parsing

Commande principale: `polls/management/commands/import_enron.py`

Fonctionnalites:
- parcours recursif des `.eml`
- extraction `From`, `To`, `Cc`, `Bcc`, `Date`, `Subject`, `Message-ID`, `In-Reply-To`
- nettoyage du corps (encodage + suppression basique signatures/disclaimers)
- creation des dossiers, collaborateurs, emails, pieces jointes
- reconstruction des threads (`in_reply_to`)
- mise a jour FTS (`search_vector`)
- import idempotent/incremental (pas de reimport inutile)

## 6. Installation et execution

### Prerequis

- Python 3.12+
- Docker + Docker Compose

### 1) Creer et activer l'environnement virtuel

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Demarrer PostgreSQL (Docker)

```bash
docker compose up -d
docker compose ps
```

### 3) Appliquer les migrations Django

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4) Importer les emails

```bash
python manage.py import_enron --path /chemin/vers/maildir
```

### 5) Lancer le serveur

```bash
python manage.py runserver
```

Configuration PostgreSQL (`docker-compose.yml` + `settings.py`) :
- DB: `enron_db`
- User: `enron`
- Password: `enron2026`
- Host: `127.0.0.1`
- Port hote: `5433`

## 7. URLs principales

- Dashboard: `http://127.0.0.1:8000/dashboard/`
- Recherche avancee: `http://127.0.0.1:8000/search/`
- Thread detail: `http://127.0.0.1:8000/thread/<email_id>/`
- Graphe d'influence (optionnel): `http://127.0.0.1:8000/influence/`
- Admin Django: `http://127.0.0.1:8000/admin/`

## 8. Fonctionnalites web (cahier des charges)

### Dashboard global
- volume des emails par mois
- top 10 expediteurs les plus actifs

### Moteur de recherche avancee
- recherche par mots-cles (FTS PostgreSQL)
- filtre expediteur
- filtre plage de dates
- pagination des resultats

### Explorateur de threads
- affichage d'un email
- reconstitution chronologique de la conversation (racine + reponses)

### Graphe d'influence (optionnel)
- connexions expediteur -> destinataire les plus frequentes
- filtre optionnel par utilisateur

## 9. Verification rapide post-import

Compter les emails importes:

```bash
python3 manage.py shell -c "from polls.models import Email,Employee,Attachment; print('Emails:', Email.objects.count(), 'Employees:', Employee.objects.count(), 'Attachments:', Attachment.objects.count())"
```

Compter les fichiers source:

```bash
find ./maildir -type f | wc -l
```

<!-- ## 10. Couverture des objectifs du sujet

- Modelisation SQL normalisee: OK
- Contraintes (FK, unicite): OK
- Optimisation FTS (GIN): OK
- Ingestion/parsing des `.eml`: OK
- Gestion `In-Reply-To`: OK
- Dashboard: OK
- Recherche avancee: OK
- Explorateur de threads: OK
- Graphe d'influence: optionnel, implemente

## 11. Remarques de rendu

- ne pas versionner la base de donnees
- ne pas versionner `maildir/`
- conserver un historique Git propre (commits atomiques)
- inclure une courte modelisation (MCD) dans le document demande -->

## 12. Auteur(s)

Projet realise dans le cadre du cours de Structuration des Donnees (2026).

Redige par [WADE Abdou](https://github.com/WADE57) et [TCHAGANO Bahissou](https://github.com/TCHAGANO).
