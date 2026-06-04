from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Food, Cart, Order, OrderItem, Category, Address, Wishlist, Review ,Coupon
import random ,hashlib, hmac, base64
from django.db.models import Q ,Avg, Count, Sum
from decouple import config
import requests , uuid
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)
# Home / Food Browsing
# 🏠 Home Page View
def home(request):
    query = request.GET.get("q","")
    selected_category = request.GET.get("category", "")
    categories = Category.objects.all()

    if selected_category:
        foods = Food.objects.filter(
            category__slug=selected_category
        )
    else:
        foods = Food.objects.all()

    foods = foods.annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews")
    )

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
    food = get_object_or_404(
        Food.objects.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews")
        ),
        food_slug=slug
    )
    recommended_foods = Food.objects.filter(
    category=food.category
).exclude(
    uid=food.uid
)[:4]
    wishlist_items = Wishlist.objects.filter(user=request.user).values_list('food', flat=True)
    reviews = Review.objects.filter(food=food).order_by('-created_at')
    return render(request, 'food_detail.html', {
        'food': food,
        'wishlist_items': wishlist_items,
        'reviews': reviews,
        'recommended_foods': recommended_foods,
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
    total = sum(
    item.food.food_price * item.quantity
    for item in cart_items
)

    discount = 0

    if not addresses.exists():
        messages.info(request, "Please add an address before checking out.")
        return redirect('add_address')

    phone = request.session.get('checkout_phone', '')

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        phone = request.POST.get("phone")
        coupon_code = request.POST.get("coupon_code", "").strip()

        if not address_id or not phone:
            messages.error(request, "Address or Phone is required.")
            return redirect('checkout')

        discount = 0

        if coupon_code:

            coupon = Coupon.objects.filter(
                code__iexact=coupon_code,
                is_active=True
            ).first()

            if coupon:

                discount = (
                    total * coupon.discount_percentage
                ) / 100

                total -= discount

                request.session["discount"] = float(discount)
                request.session["final_total"] = float(total)

                messages.success(
                    request,
                    f"{coupon.discount_percentage}% discount applied!"
                )

            else:

                messages.error(
                request,
                "Invalid Coupon Code"
                )

                return redirect("checkout")
    
        request.session['checkout_address_id'] = address_id
        request.session['checkout_phone'] = phone
        request.session["final_total"] = float(total)
        return redirect('start_payment')

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'addresses': addresses,
        'total': total,
        'phone': phone,
        'discount': discount,
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
    total = request.session.get("final_total")

    if not total:
        total = sum(
            item.food.food_price * item.quantity
            for item in cart_items
    )
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
            order.status = "CONFIRMED"
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

# views.py

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from .models import Order


# ── Colour palette ───────────────────────────────────────────────────────────
DARK        = colors.HexColor("#1a1a1a")
WHITE       = colors.white
LIGHT_GRAY  = colors.HexColor("#f5f5f5")
MID_GRAY    = colors.HexColor("#888780")
BORDER_GRAY = colors.HexColor("#e0ddd6")
GREEN_BG    = colors.HexColor("#eaf3de")
GREEN_TEXT  = colors.HexColor("#3b6d11")


# ── Helper functions (module-level, reusable) ────────────────────────────────

def draw_rounded_rect(c, x, y, w, h, radius=6, fill_color=None, stroke_color=None):
    p = c.beginPath()
    p.moveTo(x + radius, y)
    p.lineTo(x + w - radius, y)
    p.arcTo(x + w - radius, y, x + w, y + radius, -90, 90)
    p.lineTo(x + w, y + h - radius)
    p.arcTo(x + w - radius, y + h - radius, x + w, y + h, 0, 90)
    p.lineTo(x + radius, y + h)
    p.arcTo(x, y + h - radius, x + radius, y + h, 90, 90)
    p.lineTo(x, y + radius)
    p.arcTo(x, y, x + radius, y + radius, 180, 90)
    p.close()
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def draw_header(c, width, height, order):
    c.setFillColor(DARK)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 38, "EATIFY")

    c.setFillColor(colors.HexColor("#aaaaaa"))
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 56, "Premium Food Ordering Platform")

    pill_x, pill_y, pill_w, pill_h = width - 120, height - 55, 80, 22
    draw_rounded_rect(c, pill_x, pill_y, pill_w, pill_h, radius=11, fill_color=colors.HexColor("#333333"))
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 9)
    c.drawCentredString(pill_x + pill_w / 2, pill_y + 7, "INVOICE")


def draw_section_label(c, x, y, text):
    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(x, y, text.upper())


def draw_info_cards(c, x, y, left_label, left_value, right_label, right_value, card_w=230, card_h=50):
    gap = 10
    for i, (label, value) in enumerate([(left_label, left_value), (right_label, right_value)]):
        cx = x + i * (card_w + gap)
        draw_rounded_rect(c, cx, y, card_w, card_h, radius=6, fill_color=LIGHT_GRAY)
        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(cx + 12, y + card_h - 16, label.upper())
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(cx + 12, y + 14, value)


def draw_divider(c, x, y, width):
    c.setStrokeColor(BORDER_GRAY)
    c.setLineWidth(0.5)
    c.line(x, y, x + width, y)


def draw_status_pill(c, x, y, status):
    pill_w, pill_h = 70, 18
    draw_rounded_rect(c, x, y, pill_w, pill_h, radius=9, fill_color=GREEN_BG)
    c.setFillColor(GREEN_TEXT)
    c.circle(x + 12, y + 9, 3, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 20, y + 6, status.upper())


def draw_items_table(c, x, y, items, usable_width):
    table_data = [["Item", "Qty", "Price"]]
    for item in items:
        table_data.append([
            item.food.food_name,
            str(item.quantity),
            f"Rs. {item.price * item.quantity:.2f}",
        ])

    col_widths = [usable_width - 120, 60, 60]
    tbl = Table(table_data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  LIGHT_GRAY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  MID_GRAY),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, 0),  8),
        ("TOPPADDING",    (0, 0), (-1, 0),  8),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  8),
        ("LEFTPADDING",   (0, 0), (0, 0),   10),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 11),
        ("TEXTCOLOR",     (0, 1), (-1, -1), DARK),
        ("FONTNAME",      (0, 1), (0, -1),  "Helvetica-Bold"),
        ("TOPPADDING",    (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
        ("LEFTPADDING",   (0, 1), (0, -1),  10),
        ("ALIGN",         (2, 0), (2, -1),  "RIGHT"),
        ("ALIGN",         (1, 0), (1, -1),  "CENTER"),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, BORDER_GRAY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))

    tbl_w, tbl_h = tbl.wrap(usable_width, 400)
    tbl.drawOn(c, x, y - tbl_h)
    return tbl_h


def draw_total_block(c, x, y, total, usable_width):
    draw_rounded_rect(c, x, y, usable_width, 50, radius=8, fill_color=LIGHT_GRAY)
    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(x + 16, y + 18, "Total amount")
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(x + usable_width - 16, y + 14, f"Rs. {total:.2f}")


def draw_footer(c, width, margin):
    draw_divider(c, margin, 70, width - 2 * margin)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, 50, "Thank you for your order!")
    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 9)
    c.drawString(margin, 35, "We hope you enjoy your meal.")



@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, uid=order_id, user=request.user)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.uid}.pdf"'

    page_w, page_h = A4
    margin = 40
    usable_w = page_w - 2 * margin

    c = canvas.Canvas(response, pagesize=A4)
    c.setTitle(f"Eatify Invoice - {order.uid}")

    draw_header(c, page_w, page_h, order)

    cursor = page_h - 100

    draw_section_label(c, margin, cursor, "Customer")
    cursor -= 14
    draw_info_cards(
        c, margin, cursor - 50,
        "Name", order.user.username,
        "Phone", order.phone,
        card_w=(usable_w - 10) / 2,
    )
    cursor -= 68

    draw_divider(c, margin, cursor, usable_w)
    cursor -= 20

    draw_section_label(c, margin, cursor, "Order details")
    cursor -= 18

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(margin, cursor, "ORDER ID")
    cursor -= 14
    c.setFillColor(DARK)
    c.setFont("Courier", 9)
    c.drawString(margin, cursor, str(order.uid))
    cursor -= 22

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(margin, cursor, "Date")
    c.setFillColor(DARK)
    c.setFont("Helvetica", 10)
    c.drawRightString(margin + usable_w, cursor, order.created_at.strftime("%d %b %Y · %I:%M %p"))
    cursor -= 22

    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica", 10)
    c.drawString(margin, cursor, "Status")
    draw_status_pill(c, margin + usable_w - 70, cursor - 4, order.status)
    cursor -= 28

    draw_divider(c, margin, cursor, usable_w)
    cursor -= 20

    draw_section_label(c, margin, cursor, "Ordered items")
    cursor -= 14

    items_h = draw_items_table(c, margin, cursor, list(order.items.all()), usable_w)
    cursor -= items_h + 20

    draw_total_block(c, margin, cursor - 50, float(order.total_price), usable_w)

    draw_footer(c, page_w, margin)

    c.save()
    return response

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

@login_required
def admin_dashboard(request):

    if not request.user.is_superuser:
        messages.error(
            request,
            "Access Denied"
        )
        return redirect("eatify_home")

    total_orders = Order.objects.count()

    total_users = User.objects.count()

    total_revenue = (
        Order.objects
        .filter(is_paid=True)
        .aggregate(
            total=Sum("total_price")
        )["total"]
        or 0
    )

    recent_orders = (
        Order.objects
        .select_related("user")
        .order_by("-created_at")[:5]
    )
    top_foods = (
    OrderItem.objects
    .values("food__food_name")
    .annotate(
        total_sold=Sum("quantity")
    )
    .order_by("-total_sold")[:5]
)
    pending_orders = Order.objects.filter(
    status="PENDING"
).count()

    confirmed_orders = Order.objects.filter(
    status="CONFIRMED"
).count()

    delivered_orders = Order.objects.filter(
    status="DELIVERED"
).count()

    cancelled_orders = Order.objects.filter(
    status="CANCELLED"
).count()

    return render(
        request,
        "admin_dashboard.html",
        {
            "total_orders": total_orders,
            "total_users": total_users,
            "total_revenue": total_revenue,
            "recent_orders": recent_orders,
            "top_foods":top_foods,

            "pending_orders": pending_orders,
            "confirmed_orders": confirmed_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
        }
    )

from django.db.models import Count

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

