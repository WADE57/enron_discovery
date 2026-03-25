import os
import re
import email
from email.utils import parsedate_to_datetime, getaddresses

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector

from polls.models import Employee, Email, Folder, Attachment


class Command(BaseCommand):
    help = "Import des emails du corpus Enron"
    MIN_VALID_YEAR = 1990
    MAX_VALID_YEAR = 2010

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Chemin vers le dossier maildir (racine du corpus Enron)",
        )

    # ---------- Helpers modèle ----------

    def get_or_create_employee(self, addr):
        """
        Crée ou récupère un Employee à partir d'une adresse email.
        """
        if not addr:
            return None

        addr = addr.lower().strip()

        employee, _ = Employee.objects.get_or_create(
            email=addr,
            defaults={"name": addr.split("@")[0]},
        )
        return employee

    def parse_addresses(self, header):
        """
        Transforme un header (To, Cc, Bcc, From) en liste d'adresses normalisées.
        """
        if not header:
            return []

        addresses = getaddresses([header])
        return [addr.lower().strip() for name, addr in addresses if addr]

    # ---------- Nettoyage du corps du mail ----------

    def clean_body(self, body):
        """
        Nettoie le corps du texte et limite sa taille pour le FTS.
        """
        if not body:
            return ""

        body = body.strip()

        # couper à "Original Message" qui répète souvent tout l'historique
        body = re.split(
            r"\n[- ]*Original Message[- ]*\n",
            body,
            flags=re.IGNORECASE,
        )[0]

        # couper à partir d'une signature type "--" en fin de mail
        body = re.split(r"\n--\s*\n", body)[0]

        # supprimer quelques disclaimers très verbeux (pattern simplifié)
        disclaimer_patterns = [
            r"This e-mail.*?may contain confidential information.*",
            r"Ce message et toutes les pièces jointes sont confidentiels.*",
        ]
        for pattern in disclaimer_patterns:
            body = re.sub(pattern, "", body, flags=re.IGNORECASE | re.DOTALL)

        body = body.strip()

        # Limiter la taille pour rester sous la limite tsvector (~1 Mo)
        MAX_BODY_LEN = 500000  # 500k caractères, ajustable
        if len(body) > MAX_BODY_LEN:
            body = body[:MAX_BODY_LEN]

        return body

    def extract_body(self, msg):
        """
        Extraction du body texte brut à partir d'un objet email.message.Message,
        puis nettoyage basique.
        """
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(
                            "utf-8", errors="ignore"
                        )
                        break
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode(
                    "utf-8", errors="ignore"
                )
            except Exception:
                body = ""

        return self.clean_body(body)

    def parse_email_date(self, date_str):
        if not date_str:
            return None
        try:
            date = parsedate_to_datetime(date_str)
        except Exception:
            return None

        # Some malformed 2-digit years can be interpreted in the future (e.g. 2044).
        if not date or date.year < self.MIN_VALID_YEAR or date.year > self.MAX_VALID_YEAR:
            return None
        return date

    # ---------- Commande principale ----------

    def handle(self, *args, **options):
        root_path = options.get("path")

        if not root_path:
            self.stdout.write("❌ Veuillez fournir --path vers le dossier maildir")
            return

        if not os.path.isdir(root_path):
            self.stdout.write(f"❌ Chemin invalide : {root_path}")
            return

        self.stdout.write(f"✅ Début de l'import depuis : {root_path}")

        # Comptage des fichiers pour la progression
        total_files = 0
        for _root, _dirs, files in os.walk(root_path):
            total_files += len(files)
        self.stdout.write(f"📄 Fichiers détectés : {total_files}")

        processed = 0
        imported = 0
        errors = 0
        skipped = 0
        invalid_dates = 0

        for root, dirs, files in os.walk(root_path):

            # nom de dossier (ex: inbox, sent, discussion_threads, etc.)
            folder_name = os.path.basename(root) or "root"
            folder, _ = Folder.objects.get_or_create(name=folder_name)

            for file in files:
                processed += 1
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, "rb") as f:
                        msg = email.message_from_binary_file(f)

                    # --------- Métadonnées principales ---------
                    message_id = msg.get("Message-ID", file)
                    subject = msg.get("Subject", "") or ""
                    date_str = msg.get("Date")

                    date = self.parse_email_date(date_str)
                    if date_str and date is None:
                        invalid_dates += 1

                    from_header = msg.get("From")

                    to_addrs = self.parse_addresses(msg.get("To"))
                    cc_addrs = self.parse_addresses(msg.get("Cc"))
                    bcc_addrs = self.parse_addresses(msg.get("Bcc"))

                    in_reply_to = msg.get("In-Reply-To")

                    body = self.extract_body(msg)

                    # --------- Expéditeur ---------
                    sender_email = self.parse_addresses(from_header)
                    sender = None
                    if sender_email:
                        sender = self.get_or_create_employee(sender_email[0])

                    # si pas d'expéditeur valide, on ignore le mail
                    if not sender:
                        skipped += 1
                        continue

                    # --------- Création / récupération de l'Email ---------
                    email_obj, created = Email.objects.get_or_create(
                        message_id=message_id,
                        defaults={
                            "subject": subject,
                            "body": body,
                            "date": date,
                            "from_employee": sender,
                            "folder": folder,
                        },
                    )

                    if created:
                        imported += 1

                    # --------- Destinataires ---------
                    for addr in to_addrs:
                        emp = self.get_or_create_employee(addr)
                        if emp:
                            email_obj.to_employees.add(emp)

                    for addr in cc_addrs:
                        emp = self.get_or_create_employee(addr)
                        if emp:
                            email_obj.cc_employees.add(emp)

                    for addr in bcc_addrs:
                        emp = self.get_or_create_employee(addr)
                        if emp:
                            email_obj.bcc_employees.add(emp)

                    # --------- Thread (In-Reply-To) ---------
                    if in_reply_to:
                        try:
                            parent = Email.objects.get(message_id=in_reply_to)
                            email_obj.in_reply_to = parent
                            email_obj.save(update_fields=["in_reply_to"])
                        except Email.DoesNotExist:
                            # parent pas encore importé : on ignore silencieusement
                            pass

                    # --------- Pièces jointes ---------
                    for part in msg.walk():
                        if part.get_content_disposition() == "attachment":
                            filename = part.get_filename()
                            if filename:
                                payload = part.get_payload(decode=True) or b""
                                Attachment.objects.create(
                                    email=email_obj,
                                    filename=filename,
                                    content_type=part.get_content_type() or "",
                                    size=len(payload),
                                )

                    # --------- Mise à jour du champ de recherche plein texte ---------
                    try:
                        Email.objects.filter(id=email_obj.id).update(
                            search_vector=SearchVector("subject", "body")
                        )
                    except Exception as e:
                        errors += 1
                        self.stdout.write(
                            f"⚠️ Erreur FTS (email importé sans index FTS) : "
                            f"{filepath} → {e}"
                        )

                except Exception as e:
                    errors += 1
                    self.stdout.write(f"⚠️ Erreur : {filepath} → {e}")

                # log de progression périodique
                if processed % 10000 == 0:
                    self.stdout.write(
                        f"Progression : {processed}/{total_files} fichiers, "
                        f"{imported} importés, {skipped} ignorés, {errors} erreurs"
                    )

        # Résumé final
        self.stdout.write(
            f"Résumé : {processed} fichiers traités, "
            f"{imported} emails importés, {skipped} ignorés, {errors} erreurs, "
            f"{invalid_dates} dates invalides."
        )
        self.stdout.write("✅ Import terminé.")