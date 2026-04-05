from django.contrib import admin
from .models import MeetingRoom, MeetingBooking, MeetingAttendance, MeetingDocument, MeetingAgreement

@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_unlimited']

@admin.register(MeetingBooking)
class MeetingBookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'booked_by', 'scheduled_at', 'status', 'month_year']
    list_filter = ['status', 'room']
    readonly_fields = ['month_year']

admin.site.register(MeetingAttendance)
admin.site.register(MeetingDocument)
admin.site.register(MeetingAgreement)
