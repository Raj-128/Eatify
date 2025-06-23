from django.contrib import admin
from .models import *
from django.utils.html import format_html

admin.site.register(Category)
admin.site.register(Food)
admin.site.register(FoodMetaInformation)
admin.site.register(FoodImages)
admin.site.register(Cart)
admin.site.register(OrderItem)
admin.site.register(Address)
admin.site.register(Review)
@admin.register(Order)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_price', 'colored_status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'uid')

    def colored_status(self, obj):
        color = {
            'PENDING': 'orange',
            'CONFIRMED': 'blue',
            'DELIVERED': 'green',
            'CANCELLED': 'red'
        }.get(obj.status, 'black')

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    colored_status.short_description = 'Status'