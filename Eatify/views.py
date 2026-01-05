from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Food, Cart, Order, OrderItem, Category, Address, Wishlist, Review
import random ,hashlib, hmac, base64
from django.db.models import Q
from decouple import config
import requests , uuid
# Home / Food Browsing
# 🏠 Home Page View
def home(request):
    query = request.GET.get("q","")
    selected_category = request.GET.get("category", "")
    categories = Category.objects.all()

    if selected_category:
        foods = Food.objects.filter(category__slug=selected_category)
    else:
        foods = Food.objects.all()

    if query:
        foods = foods.filter(
            Q(food_name__icontains=query) |
            Q(food_description__icontains=query) |
            Q(category__name__icontains=query)
        )

    show_welcome = request.session.pop('show_welcome', False)

    return render(request, 'home.html', {
        'categories': categories,
        'foods': foods,
        'selected_category': selected_category,
        'query': query,
        'show_welcome': show_welcome,
    })

# Food Detail + Reviews
@login_required
def food_detail(request, slug):
    food = get_object_or_404(Food, food_slug=slug)
    wishlist_items = Wishlist.objects.filter(user=request.user).values_list('food', flat=True)
    reviews = Review.objects.filter(food=food).order_by('-created_at')
    return render(request, 'food_detail.html', {
        'food': food,
        'wishlist_items': wishlist_items,
        'reviews': reviews
    })

@login_required
def add_review(request, uid):
    food = get_object_or_404(Food, uid=uid)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        Review.objects.create(
            user=request.user,
            food=food,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Review submitted successfully!")
    return redirect('food_detail', slug=food.food_slug)

# Cart Management
@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.food.food_price * item.quantity for item in cart_items)
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def add_to_cart(request, uid):
    food = get_object_or_404(Food, uid=uid)
    cart_item, created = Cart.objects.get_or_create(user=request.user, food=food)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('view_cart')

@login_required
def increase_cart_quantity(request, uid):
    cart_item = get_object_or_404(Cart, user=request.user, food__uid=uid)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('view_cart')

@login_required
def decrease_cart_quantity(request, uid):
    cart_item = get_object_or_404(Cart, user=request.user, food__uid=uid)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('view_cart')

@login_required
def remove_from_cart(request, food_slug):
    food = get_object_or_404(Food, food_slug=food_slug)
    cart_item = Cart.objects.filter(user=request.user, food=food).first()
    if cart_item:
        cart_item.delete()
    return redirect('view_cart')

# Wishlist Management
@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, uid):
    food = get_object_or_404(Food, uid=uid)
    Wishlist.objects.get_or_create(user=request.user, food=food)
    return redirect('wishlist_view')

@login_required
def remove_from_wishlist(request, uid):
    food = get_object_or_404(Food, uid=uid)
    Wishlist.objects.filter(user=request.user, food=food).delete()
    return redirect('wishlist_view')

# Checkout & Payment Flow
@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    total = sum(item.food.food_price * item.quantity for item in cart_items)

    if not addresses.exists():
        messages.info(request, "Please add an address before checking out.")
        return redirect('add_address')

    phone = request.session.get('checkout_phone', '')

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        phone = request.POST.get("phone")

        if not address_id or not phone:
            messages.error(request, "Address or Phone is required.")
            return redirect('checkout')

        request.session['checkout_address_id'] = address_id
        request.session['checkout_phone'] = phone

        return redirect('start_payment')

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'addresses': addresses,
        'total': total,
        'phone': phone
    })

@login_required
def add_address(request):
    if request.method == "POST":
        address_line = request.POST.get("address_line")
        city = request.POST.get("city")
        pincode = request.POST.get("pincode")

        Address.objects.create(
            user=request.user,
            address_line=address_line,
            city=city,
            pincode=pincode
        )
        messages.success(request, "Address added successfully!")
        return redirect('checkout')

    return render(request, 'add_address.html')

@login_required
def start_payment(request):
    print("---- START PAYMENT ----")

    phone = request.session.get("checkout_phone")
    address_id = request.session.get("checkout_address_id")

    print("PHONE:", phone)
    print("ADDRESS ID:", address_id)
    print("USER:", request.user)

    if not phone or not address_id:
        messages.error(request, "Invalid session data")
        return redirect("checkout")

    cart_items = Cart.objects.filter(user=request.user)
    print("CART COUNT:", cart_items.count())

    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect("view_cart")

    address = get_object_or_404(Address, uid=address_id)
    total = sum(item.food.food_price * item.quantity for item in cart_items)

    order = Order.objects.create(
        user=request.user,
        total_price=total,
        address=address,
        phone=phone,
        is_paid=False,
        status="PENDING"
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            food=item.food,
            quantity=item.quantity,
            price=item.food.food_price
        )

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY,
        "x-api-version": "2022-09-01",
    }




    payload = {
        "order_id": str(order.uid),
        "order_amount": float(total),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": str(request.user.id),
            "customer_email": request.user.email or "test@test.com",
            "customer_phone": phone
        },
        "order_meta": {
            "return_url": f"{settings.CASHFREE_RETURN_URL}?orderId={order.uid}"
        }
    }

    response = requests.post(settings.CASHFREE_API_URL, headers=headers, json=payload)

    print("CASHFREE STATUS:", response.status_code)
    print("CASHFREE BODY:", response.text)

    if response.status_code != 200:
        messages.error(request, "Payment initiation failed.")
        return redirect("view_cart")

    data = response.json()
    payment_session_id = data.get("payment_session_id")

    if not payment_session_id:
        messages.error(request, "Payment session not created.")
        return redirect("view_cart")

    return render(request, "cashfree_redirect.html", {
        "payment_session_id": payment_session_id
    })


@login_required
def payment_success(request):
    order_id = request.GET.get("orderId")

    if not order_id:
        messages.error(request, "Invalid payment response")
        return redirect("view_cart")

    url = f"{settings.CASHFREE_API_URL}/{order_id}"


    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY,
        "x-api-version": "2022-09-01",
    }


    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        messages.error(request, "Unable to verify payment. Please contact support.")
        return redirect("view_cart")
    data = response.json()

    order_status = data.get("order_status")

    if order_status == "PAID":
        order = Order.objects.filter(uid=order_id, user=request.user).first()
        if order and not order.is_paid:
            order.is_paid = True
            order.status = "PLACED"
            order.save()
            Cart.objects.filter(user=request.user).delete()
        return redirect("order_success")

    messages.error(request, "Payment not confirmed yet.")
    return redirect("view_cart")

@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})


# Authentication (Login/Register/Logout)
def eatify_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            request.session['show_welcome'] = True
            return redirect('eatify_home')
        else:
            messages.error(request, "Invalid credentials")
    return render(request, "login.html")

def eatify_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("eatify_register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("eatify_register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("eatify_register")

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registration successful! Please log in.")
        return redirect("eatify_login")

    return render(request, "register.html")

def eatify_logout(request):
    logout(request)
    return redirect("eatify_home")

