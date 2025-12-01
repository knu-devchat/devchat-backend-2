from django.contrib import admin
from .models import AiChatSession


@admin.register(AiChatSession)
class AiChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'base_room', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id', 'base_room__room_name']
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('base_room')
