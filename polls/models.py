# from django.db import models

# # Create your models here.

# class Employee(models.Model):
#     name = models.CharField(max_length=200)
#     email = models.CharField(max_length=200, unique=True)
    
#     def __str__(self):
#         return self.email

# class Email(models.Model):
#     message_id = models.CharField(max_length=500, unique=True)
#     date = models.DateTimeField(null=True, blank=True)
#     from_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sent_emails')
#     to_employees = models.ManyToManyField(Employee, related_name='received_emails')
#     subject = models.TextField(blank=True)
#     body = models.TextField(blank=True)
    
#     def __str__(self):
#         return f"{self.subject[:50]}..."

from django.db import models

class Employee(models.Model):
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email


class Folder(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Email(models.Model):

    message_id = models.CharField(max_length=500, unique=True)

    date = models.DateTimeField(null=True, blank=True)

    subject = models.TextField(blank=True)

    body = models.TextField(blank=True)

    # expéditeur
    from_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="sent_emails"
    )

    # destinataires
    to_employees = models.ManyToManyField(
        Employee,
        related_name="received_emails",
        blank=True
    )

    cc_employees = models.ManyToManyField(
        Employee,
        related_name="cc_emails",
        blank=True
    )

    bcc_employees = models.ManyToManyField(
        Employee,
        related_name="bcc_emails",
        blank=True
    )

    # threads
    in_reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies"
    )

    # dossier
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.subject[:50] if self.subject else "No subject"
    
    # class Meta:
    #     ordering = ['-date']
    #     indexes = [
    #         models.Index(fields=['message_id']),
    #         models.Index(fields=['date']),
    #     ]

    class Meta:
        indexes = [
            models.Index(fields=["date"]),
        ]


class Attachment(models.Model):

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    filename = models.CharField(max_length=500)

    content_type = models.CharField(max_length=200, blank=True)

    size = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.filename