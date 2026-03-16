from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Employee(models.Model):
    """
    Collaborateur de l'entreprise (une ligne par adresse email).
    """
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email


class Folder(models.Model):
    """
    Dossier / répertoire dans la boîte mail (inbox, sent, etc.).
    """
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Email(models.Model):
    """
    Message email principal.
    """
    # identifiant technique unique provenant du corpus (.eml)
    message_id = models.CharField(max_length=500, unique=True)

    # métadonnées principales
    date = models.DateTimeField(null=True, blank=True)
    subject = models.TextField(blank=True)
    body = models.TextField(blank=True)

    # expéditeur (un seul)
    from_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="sent_emails",
    )

    # destinataires (To, Cc, Bcc)
    to_employees = models.ManyToManyField(
        Employee,
        related_name="received_emails",
        blank=True,
    )
    cc_employees = models.ManyToManyField(
        Employee,
        related_name="cc_emails",
        blank=True,
    )
    bcc_employees = models.ManyToManyField(
        Employee,
        related_name="bcc_emails",
        blank=True,
    )

    # relation de thread (In-Reply-To)
    in_reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )

    # dossier de classement
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # champ dédié à la recherche plein texte PostgreSQL
    # (de type tsvector côté PostgreSQL)
    search_vector = SearchVectorField(null=True, blank=True)

    def __str__(self):
        return self.subject[:50] if self.subject else "No subject"

    class Meta:
        ordering = ["-date"]
        indexes = [
            # utile pour filtrer/ordonner par date (dashboard, timeline)
            models.Index(fields=["date"]),
            # on garde aussi un index classique sur l'identifiant fonctionnel
            models.Index(fields=["message_id"]),
            # index GIN pour le Full Text Search sur search_vector
            GinIndex(fields=["search_vector"], name="email_fts_gin_idx"),
        ]


class Attachment(models.Model):
    """
    Pièce jointe associée à un email.
    """
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    filename = models.CharField(max_length=500)
    content_type = models.CharField(max_length=200, blank=True)
    size = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.filename