from django.contrib import admin

# Register your models here.

from .models import Employee, Email

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'from_employee', 'date')
    list_filter = ('date',)
    search_fields = ('subject', 'body')