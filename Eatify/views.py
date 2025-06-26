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

# 🏠 Home Page View
def home(request):
    query = request.GET.get("q")
    selected_category = request.GET.get("category")
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

    return render(request, 'home.html', {
        'categories': categories,
        'foods': foods,
        'selected_category': selected_category,
        'query': query
    })

@login_required
def start_payment(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        address_id = request.POST.get('address_id')

        if not phone or not address_id:
            return redirect('checkout')

        address = get_object_or_404(Address, uid=address_id)
        cart_items = Cart.objects.filter(user=request.user)
        total = sum(item.food.food_price * item.quantity for item in cart_items)

        if not cart_items.exists():
            return redirect('view_cart')

        # 🔸 Order Creation
        order = Order.objects.create(
            user=request.user,
            total_price=total,
            address=address,
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

        # 🔸 Cashfree Payment Params
        order_id = str(order.uid)
        amount = str(total)
        currency = "INR"
        return_url = settings.CASHFREE_RETURN_URL

        data = {
            "orderId": order_id,
            "orderAmount": amount,
            "orderCurrency": currency,
            "customerPhone": phone,
            "customerEmail": request.user.email,
            "customerName": request.user.username,
            "returnUrl": return_url,
            "notifyUrl": return_url,
            "appId": settings.CASHFREE_APP_ID,
        }

        # 🔸 Signature Generation
        signature_data = f"{data['appId']}{data['orderId']}{data['orderAmount']}{data['orderCurrency']}{data['customerEmail']}{data['returnUrl']}{settings.CASHFREE_SECRET_KEY}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()

        data["signature"] = signature
        data["gateway_url"] = settings.CASHFREE_API_URL

        # 🔸 Empty Cart
        cart_items.delete()

        return render(request, 'cashfree_payment.html', {'payment_data': data})

    return redirect('checkout')
@login_required
def generate_signature(data, secret_key):
    sorted_data = sorted(data.items())
    data_string = ''.join(key + str(value) for key, value in sorted_data)
    return base64.b64encode(
        hmac.new(secret_key.encode(), data_string.encode(), digestmod=hashlib.sha256).digest()
    ).decode()
# 🥘 Food Detail View
@login_required
def start_payment(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')  # user entered phone
        order = Order.objects.create(user=request.user, total_price=999.00)  # 👈 use your real cart total here

        data = {
            "appId": settings.CASHFREE_APP_ID,
            "orderId": str(order.uid),
            "orderAmount": str(order.total_price),
            "orderCurrency": "INR",
            "customerName": request.user.username,
            "customerEmail": request.user.email,
            "customerPhone": phone,
            "returnUrl": settings.CASHFREE_RETURN_URL,
            "notifyUrl": settings.CASHFREE_RETURN_URL,
        }

        signature = generate_signature(data, settings.CASHFREE_SECRET_KEY)

        payment_data = {
            "gateway_url": settings.CASHFREE_API_URL,
            "app_id": data["appId"],
            "order_id": data["orderId"],
            "order_amount": data["orderAmount"],
            "customer_name": data["customerName"],
            "customer_email": data["customerEmail"],
            "customer_phone": data["customerPhone"],
            "return_url": data["returnUrl"],
            "signature": signature
        }

        return render(request, 'cashfree_payment.html', {'payment_data': payment_data})

    return redirect('checkout') 
@login_required
def food_detail(request, slug):
    food = get_object_or_404(Food, food_slug=slug)
    return render(request, 'food_detail.html', {'food': food})

# ➕ Add to Cart
@login_required
def add_to_cart(request, uid):
    food = get_object_or_404(Food, uid=uid)
    cart_item, created = Cart.objects.get_or_create(user=request.user, food=food)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('view_cart')

# 🔼 Increase Quantity
@login_required
def increase_cart_quantity(request, uid):
    cart_item = get_object_or_404(Cart, user=request.user, food__uid=uid)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('view_cart')

# 🔽 Decrease Quantity
@login_required
def decrease_cart_quantity(request, uid):
    cart_item = get_object_or_404(Cart, user=request.user, food__uid=uid)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('view_cart')

# ❌ Remove from Cart
@login_required
def remove_from_cart(request, food_slug):
    food = get_object_or_404(Food, food_slug=food_slug)
    cart_item = Cart.objects.filter(user=request.user, food=food).first()
    if cart_item:
        cart_item.delete()
    return redirect('view_cart')

# 🛒 View Cart
@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total = sum(item.food.food_price * item.quantity for item in cart_items)
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total': total
    })

# ✅ Checkout
@login_required
def checkout(request):
    cart_items = Cart.objects.filter(user=request.user)
    addresses = Address.objects.filter(user=request.user)
    total = sum(item.food.food_price * item.quantity for item in cart_items)

    # 👉 If no address found for user, redirect to add address page
    if not addresses.exists():
        messages.info(request, "Please add an address before checking out.")
        return redirect('add_address')

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        phone = request.POST.get("phone")

        if not address_id or not phone:
            messages.error(request, "Address or Phone is required.")
            return redirect('checkout')

        address = get_object_or_404(Address, uid=address_id)

        # ✅ Create Order
        order = Order.objects.create(
            user=request.user,
            total_price=total,
            address=address,
            status="PENDING"
        )

        # ✅ Create Order Items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                food=item.food,
                quantity=item.quantity,
                price=item.food.food_price
            )

        # ✅ Clear cart
        cart_items.delete()

        # ✅ Redirect to success page
        return redirect('order_success')  # or 'start_payment' if payment flow is needed

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'addresses': addresses,
        'total': total
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

    return render(request, 'add_address.html')  # 👈 ye line bilkul sahi aligned honi chahiye


# ✅ Order Success
@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})


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

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

# 🔐 Login View
def eatify_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('eatify_home')
        else:
            messages.error(request, "Invalid credentials")
    return render(request, "login.html")

# 🔐 Register View
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

        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registration successful! Please log in.")
        return redirect("eatify_login")

    return render(request, "register.html")

# 🔐 Logout View
def eatify_logout(request):
    logout(request)
    return redirect("eatify_home")
