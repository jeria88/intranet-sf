from django.contrib import admin
from .models import (
    MeetingRoom, MeetingBooking, MeetingAttendance,
    MeetingDocument, MeetingAgreement, MeetingParticipant
)


# ── Inlines ───────────────────────────────────────────────────────────────────

class MeetingParticipantInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0
    readonly_fields = ['name', 'joined_at', 'left_at', 'duration_seconds']
    verbose_name = 'Participante (Daily)'
    can_delete = False


class MeetingAgreementInline(admin.TabularInline):
    model = MeetingAgreement
    extra = 1
    fields = ['description', 'responsible', 'deadline', 'status']


# ── ModelAdmins ───────────────────────────────────────────────────────────────

@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'room_type', 'daily_identifier', 'target_establishment', 'target_role', 'is_unlimited']
    list_filter = ['room_type', 'is_unlimited']
    search_fields = ['name', 'daily_identifier', 'target_establishment', 'target_role']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MeetingBooking)
class MeetingBookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'booked_by', 'scheduled_at', 'duration_minutes', 'status', 'processing_status', 'month_year']
    list_filter = ['status', 'processing_status', 'room', 'month_year']
    search_fields = [
        'booked_by__first_name', 'booked_by__last_name',
        'booked_by__username', 'room__name', 'agenda'
    ]
    readonly_fields = ['month_year', 'transcript', 'acta', 'acuerdos_text']
    date_hierarchy = 'scheduled_at'
    inlines = [MeetingParticipantInline, MeetingAgreementInline]
    fieldsets = (
        ('Información de la Reunión', {
            'fields': ('room', 'booked_by', 'scheduled_at', 'duration_minutes', 'status', 'agenda', 'calendar_event')
        }),
        ('Grabación & Procesamiento IA', {
            'fields': ('recording_url', 'recording_id', 'processing_status', 'transcript', 'acta', 'acuerdos_text'),
            'classes': ('collapse',),
        }),
        ('Metadatos', {
            'fields': ('month_year',),
            'classes': ('collapse',),
        }),
    )


@admin.register(MeetingAttendance)
class MeetingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['booking', 'user', 'joined_at', 'left_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'booking__room__name']
    list_filter = ['booking__room']


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    list_display = ['name', 'booking', 'joined_at', 'left_at', 'duration_seconds']
    search_fields = ['name', 'booking__room__name']
    list_filter = ['booking__room']


@admin.register(MeetingDocument)
class MeetingDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'booking', 'uploaded_by', 'uploaded_at']
    search_fields = ['title', 'booking__room__name', 'uploaded_by__username']


@admin.register(MeetingAgreement)
class MeetingAgreementAdmin(admin.ModelAdmin):
    list_display = ['description', 'booking', 'responsible', 'deadline', 'status']
    list_filter = ['status']
    search_fields = ['description', 'responsible__username']
