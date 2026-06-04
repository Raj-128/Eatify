from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views  

urlpatterns = [
    path('', home, name='eatify_home'),

    path('food/<slug:slug>/', food_detail, name='food_detail'),

    # Cart
    path('add-to-cart/<uuid:uid>/', add_to_cart, name='add_to_cart'),
    path('increase-cart/<uuid:uid>/', increase_cart_quantity, name='increase_cart'),
    path('decrease-cart/<uuid:uid>/', decrease_cart_quantity, name='decrease_cart'),
    path('remove-from-cart/<slug:food_slug>/', remove_from_cart, name='remove_from_cart'),
    path('cart/', view_cart, name='view_cart'),

    # Checkout & Orders
    path('checkout/', checkout, name='checkout'),
    path('order-success/', order_success, name='order_success'),
    path('start-payment/', start_payment, name='start_payment'),
    path('payment-success/', payment_success, name='payment_success'),
    path('order-history/', order_history, name='order_history'),

    # Authentication
    path('login/', eatify_login, name='eatify_login'),
    path('register/', eatify_register, name='eatify_register'),
    path('logout/', eatify_logout, name='eatify_logout'),

    # Address
    path('add-address/', add_address, name='add_address'),

    # Wishlist
    path('wishlist/', wishlist_view, name='wishlist_view'),
    path('add-to-wishlist/<uuid:uid>/', add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<uuid:uid>/', remove_from_wishlist, name='remove_from_wishlist'),

    # Reviews
    path('add-review/<uuid:uid>/', add_review, name='add_review'),

    # Forgot Password System
    path('forgot-password/', 
         auth_views.PasswordResetView.as_view(template_name="forgot_password.html"), 
         name='password_reset'),

    path('forgot-password/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name="forgot_password_done.html"), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name="reset_password.html"), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name="reset_password_complete.html"), 
         name='password_reset_complete'),
]

