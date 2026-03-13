from django.db import models

# Create your models here.

class Employee(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200, unique=True)
    
    def __str__(self):
        return self.email

class Email(models.Model):
    message_id = models.CharField(max_length=500, unique=True)
    date = models.DateTimeField(null=True, blank=True)
    from_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sent_emails')
    to_employees = models.ManyToManyField(Employee, related_name='received_emails')
    subject = models.TextField(blank=True)
    body = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.subject[:50]}..."