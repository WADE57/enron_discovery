import os
import re
import email
from email.utils import parsedate_to_datetime, getaddresses

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector

from polls.models import Employee, Email, Folder, Attachment


class Command(BaseCommand):
    help = "Import des emails du corpus Enron (mode incremental/idempotent)"
    MIN_VALID_YEAR = 1990
    MAX_VALID_YEAR = 2010

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            required=True,
            help="Chemin vers le dossier maildir (racine du corpus Enron)",
        )

    def get_or_create_employee(self, addr):
        if not addr:
            return None
        addr = addr.lower().strip()
        employee, _ = Employee.objects.get_or_create(
            email=addr,
            defaults={"name": addr.split("@")[0]},
        )
        return employee

    def parse_addresses(self, header):
        if not header:
            return []
        addresses = getaddresses([header])
        return [addr.lower().strip() for _name, addr in addresses if addr]

    def clean_body(self, body):
        if not body:
            return ""
        body = body.strip()
        body = re.split(r"\n[- ]*Original Message[- ]*\n", body, flags=re.IGNORECASE)[0]
        body = re.split(r"\n--\s*\n", body)[0]

        disclaimer_patterns = [
            r"This e-mail.*?may contain confidential information.*",
            r"Ce message et toutes les pieces jointes sont confidentiels.*",
        ]
        for pattern in disclaimer_patterns:
            body = re.sub(pattern, "", body, flags=re.IGNORECASE | re.DOTALL)

        return body.strip()

    def extract_body(self, msg):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
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

    def handle(self, *args, **options):
        root_path = options["path"]

        if not os.path.isdir(root_path):
            self.stdout.write(f"Chemin invalide: {root_path}")
            return

        self.stdout.write(f"Debut import: {root_path}")

        total_files = 0
        for _root, _dirs, files in os.walk(root_path):
            total_files += len(files)
        self.stdout.write(f"Fichiers detectes: {total_files}")

        # Set des message_id deja en base -> reprise rapide sans reimport
        existing_ids = set(
            Email.objects.values_list("message_id", flat=True)
        )
        self.stdout.write(f"Message-ID deja en base: {len(existing_ids)}")

        processed = 0
        imported = 0
        already_exists = 0
        skipped = 0
        errors = 0
        fts_skipped = 0
        invalid_dates = 0

        unknown_sender, _ = Employee.objects.get_or_create(
            email="unknown@enron.local",
            defaults={"name": "Unknown Sender"},
        )

        for root, _dirs, files in os.walk(root_path):
            folder_name = os.path.basename(root) or "root"
            folder, _ = Folder.objects.get_or_create(name=folder_name)

            for filename in files:
                processed += 1
                filepath = os.path.join(root, filename)

                try:
                    with open(filepath, "rb") as f:
                        msg = email.message_from_binary_file(f)

                    message_id = msg.get("Message-ID", filename)
                    subject = msg.get("Subject", "") or ""
                    date_str = msg.get("Date")

                    # Skip rapide si deja importe
                    if message_id in existing_ids:
                        already_exists += 1
                        if processed % 10000 == 0:
                            self.stdout.write(
                                f"Progression: {processed}/{total_files} | "
                                f"importes={imported} deja={already_exists} "
                                f"ignores={skipped} erreurs={errors}"
                            )
                        continue

                    date = self.parse_email_date(date_str)
                    if date_str and date is None:
                        invalid_dates += 1

                    from_header = msg.get("From")
                    to_addrs = self.parse_addresses(msg.get("To"))
                    cc_addrs = self.parse_addresses(msg.get("Cc"))
                    bcc_addrs = self.parse_addresses(msg.get("Bcc"))
                    in_reply_to = msg.get("In-Reply-To")
                    body = self.extract_body(msg)

                    sender_email = self.parse_addresses(from_header)
                    sender = self.get_or_create_employee(sender_email[0]) if sender_email else unknown_sender
                    if not sender:
                        skipped += 1
                        continue

                    email_obj = Email.objects.create(
                        message_id=message_id,
                        subject=subject,
                        body=body,  # body complet conserve
                        date=date,
                        from_employee=sender,
                        folder=folder,
                    )
                    imported += 1
                    existing_ids.add(message_id)

                    # Destinataires
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

                    # Thread
                    if in_reply_to:
                        try:
                            parent = Email.objects.get(message_id=in_reply_to)
                            email_obj.in_reply_to = parent
                            email_obj.save(update_fields=["in_reply_to"])
                        except Email.DoesNotExist:
                            pass

                    # Pieces jointes (sans doublon)
                    for part in msg.walk():
                        if part.get_content_disposition() == "attachment":
                            filename_att = part.get_filename()
                            if not filename_att:
                                continue
                            payload = part.get_payload(decode=True) or b""
                            size = len(payload)
                            content_type = part.get_content_type() or ""

                            Attachment.objects.get_or_create(
                                email=email_obj,
                                filename=filename_att,
                                content_type=content_type,
                                size=size,
                            )

                    # FTS: on essaye, sinon on garde l'email sans index FTS
                    try:
                        Email.objects.filter(id=email_obj.id).update(
                            search_vector=SearchVector("subject", "body")
                        )
                    except Exception:
                        fts_skipped += 1

                except Exception as e:
                    errors += 1
                    self.stdout.write(f"Erreur: {filepath} -> {e}")

                if processed % 10000 == 0:
                    self.stdout.write(
                        f"Progression: {processed}/{total_files} | "
                        f"importes={imported} deja={already_exists} "
                        f"ignores={skipped} erreurs={errors}"
                    )

        self.stdout.write(
            f"Resume: traites={processed}, importes={imported}, deja={already_exists}, "
            f"ignores={skipped}, erreurs={errors}, fts_non_indexes={fts_skipped}, "
            f"dates_invalides={invalid_dates}"
        )
        self.stdout.write("Import termine")