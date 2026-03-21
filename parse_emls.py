import os
import email
from email import policy
from email.parser import BytesParser
import pandas as pd

def parse_eml_file(filepath):
    """Extrait les métadonnées et le corps d'un fichier .eml."""
    with open(filepath, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    return {
        'message_id': msg.get('Message-ID', ''),
        'date': msg.get('Date', ''),
        'subject': msg.get('Subject', ''),
        'from': msg.get('From', ''),
        'to': msg.get('To', ''),
        'cc': msg.get('Cc', ''),
        'bcc': msg.get('Bcc', ''),
        'body': msg.get_body().get_content() if msg.get_body() else '',
    }

def parse_enron_corpus(root_dir):
    """Parcourt l'arborescence et retourne un DataFrame."""
    data = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.eml'):
                full_path = os.path.join(root, file)
                try:
                    data.append(parse_eml_file(full_path))
                except Exception as e:
                    print(f"Erreur avec {full_path}: {e}")
    return pd.DataFrame(data)

if __name__ == '__main__':
    # Remplace par le chemin vers ton dossier maildir (relatif ou absolu)
    # Exemple : "../maildir" si maildir est dans le dossier parent
    corpus_path = r"C:\Users\Bahissou TCHAGNAO\Desktop\MES COURS DS\TP SQL\PROJET_DJANGO\maildir"   # <--- À modifier selon ton répertoire réel
    df = parse_enron_corpus(corpus_path)
    df.to_csv('emails_parsed.csv', index=False)
    print(f"Export terminé : {len(df)} emails parsés.")