from django.urls import path
from .views import *
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
path('', home, name='eatify_home'),
path('food/<slug:slug>/', food_detail, name='food_detail'),
path('add-to-cart/<uuid:uid>/', add_to_cart, name='add_to_cart'),
path('increase-cart/<uuid:uid>/', increase_cart_quantity, name='increase_cart'),
path('decrease-cart/<uuid:uid>/', decrease_cart_quantity, name='decrease_cart'),
path('remove-from-cart/<slug:food_slug>/', remove_from_cart, name='remove_from_cart'),
path('cart/', view_cart, name='view_cart'),
path('checkout/', checkout, name='checkout'),
path('order-success/', order_success, name='order_success'),
path('login/', eatify_login, name='eatify_login'),
path('register/', eatify_register, name='eatify_register'),
path('logout/',eatify_logout, name='eatify_logout'),
path('add-address/', add_address, name='add_address'),
path('wishlist/', wishlist_view, name='wishlist_view'),
path('add-to-wishlist/<uuid:uid>/', add_to_wishlist, name='add_to_wishlist'),
path('remove-from-wishlist/<uuid:uid>/', remove_from_wishlist, name='remove_from_wishlist'),
path('order-history/', order_history, name='order_history'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)