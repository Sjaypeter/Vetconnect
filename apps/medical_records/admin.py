from django.contrib import admin
from .models import MedicalRecord, Vaccination, Prescription


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['pet', 'vet', 'date', 'diagnosis', 'follow_up_required']
    list_filter = ['follow_up_required', 'date', 'vet']
    search_fields = ['pet__name', 'vet__username', 'diagnosis', 'treatment']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = ['pet', 'vaccine_name', 'date_administered', 'next_due_date', 'reminder_sent']
    list_filter = ['vaccine_name', 'date_administered', 'reminder_sent']
    search_fields = ['pet__name', 'vaccine_name', 'batch_number']
    date_hierarchy = 'date_administered'


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['medication_name', 'medical_record', 'dosage', 'frequency', 'start_date']
    list_filter = ['start_date']
    search_fields = ['medication_name', 'medical_record__pet__name']


