import os
import email
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Employee, Email

class Command(BaseCommand):
    help = 'Importe les emails du dataset Enron'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, default='enron_mail_20150507', 
                          help='Chemin vers le dossier des emails Enron')

    def extract_email_address(self, email_string):
        """Extrait l'adresse email d'une chaîne comme 'Nom <email@domain.com>'"""
        if not email_string:
            return None
        # Cherche un pattern d'email entre < >
        match = re.search(r'<(.+?)>', email_string)
        if match:
            return match.group(1).lower()
        # Sinon, vérifie si la chaîne elle-même est un email
        if '@' in email_string:
            return email_string.lower().strip()
        return None

    def get_or_create_employee(self, email_string):
        """Crée ou récupère un employé à partir d'une adresse email"""
        email_addr = self.extract_email_address(email_string)
        if not email_addr:
            return None
        
        employee, created = Employee.objects.get_or_create(
            email=email_addr,
            defaults={'name': email_string[:200]}  # On stocke le nom complet si disponible
        )
        return employee

    def parse_date(self, date_str):
        """Tente de parser une date email dans différents formats"""
        if not date_str:
            return None
        
        # Formats courants dans les emails
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%d %b %Y %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S%z',
            '%a, %d %b %Y %H:%M:%S %z (UTC)',
        ]
        
        for fmt in formats:
            try:
                # Nettoie la chaîne de date
                clean_date = date_str.strip()
                return datetime.strptime(clean_date, fmt)
            except (ValueError, TypeError):
                continue
        return None

    def parse_email_file(self, filepath):
        """Parse un fichier email et retourne ses composants"""
        try:
            with open(filepath, 'rb') as f:
                msg = email.message_from_binary_file(f)
            
            # Extraction des métadonnées
            from_addr = msg.get('from', '')
            to_addr = msg.get('to', '')
            cc_addr = msg.get('cc', '')
            subject = msg.get('subject', '')
            date_str = msg.get('date', '')
            message_id = msg.get('message-id', '') or msg.get('Message-ID', '') or os.path.basename(filepath)
            
            # Extraction du corps
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except:
                            continue
                    elif content_type == "text/html" and not body:
                        # Fallback sur HTML si pas de texte
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            continue
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = msg.get_payload()
            
            return {
                'message_id': message_id.strip('<>'),
                'from': from_addr,
                'to': to_addr,
                'cc': cc_addr,
                'subject': subject,
                'date': self.parse_date(date_str),
                'body': body[:50000]  # Limite la taille pour éviter les problèmes
            }
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Erreur lors du parsing de {filepath}: {e}"))
            return None

    def walk_directory(self, path):
        """Parcourt récursivement un dossier et retourne tous les fichiers"""
        email_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if not file.startswith('.'):  # Ignore les fichiers cachés
                    email_files.append(os.path.join(root, file))
        return email_files

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Le dossier {path} n'existe pas"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"Recherche des emails dans {path}..."))
        
        # Trouve tous les fichiers email
        email_files = self.walk_directory(path)
        total_files = len(email_files)
        
        self.stdout.write(f"Trouvé {total_files} fichiers à traiter")
        
        # Compteurs pour le rapport
        imported = 0
        skipped = 0
        errors = 0
        
        # Traite chaque fichier
        for i, filepath in enumerate(email_files, 1):
            if i % 1000 == 0:
                self.stdout.write(f"Progression: {i}/{total_files} fichiers traités")
            
            try:
                # Parse l'email
                email_data = self.parse_email_file(filepath)
                if not email_data:
                    errors += 1
                    continue
                
                # Récupère ou crée l'expéditeur
                from_employee = self.get_or_create_employee(email_data['from'])
                if not from_employee:
                    skipped += 1
                    continue
                
                # Crée l'email
                email_obj, created = Email.objects.get_or_create(
                    message_id=email_data['message_id'],
                    defaults={
                        'from_employee': from_employee,
                        'subject': email_data['subject'][:500],  # Limite la longueur
                        'body': email_data['body'],
                        'date': email_data['date']
                    }
                )
                
                if created:
                    # Traite les destinataires TO
                    if email_data['to']:
                        for to_addr in email_data['to'].split(','):
                            to_employee = self.get_or_create_employee(to_addr.strip())
                            if to_employee:
                                email_obj.to_employees.add(to_employee)
                    
                    # Traite les destinataires CC
                    if email_data['cc']:
                        for cc_addr in email_data['cc'].split(','):
                            cc_employee = self.get_or_create_employee(cc_addr.strip())
                            if cc_employee:
                                email_obj.to_employees.add(cc_employee)
                    
                    imported += 1
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Erreur sur {filepath}: {e}"))
                errors += 1
        
        # Rapport final
        self.stdout.write(self.style.SUCCESS(f"""
        ========== RAPPORT D'IMPORTATION ==========
        Fichiers trouvés : {total_files}
        Emails importés  : {imported}
        Ignorés          : {skipped}
        Erreurs          : {errors}
        ==========================================
        """))