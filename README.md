# Eatify
Eatify is a feature-rich online food ordering platform built using Django. It allows users to browse food items, add them to cart, place orders, and pay securely using an integrated payment gateway (Cashfree). The app includes wishlist, address management, order history, and admin food control.

# 🍽️ Eatify - Django Based Food Ordering System

Eatify is a full-stack food ordering web application built using Django. It allows users to browse delicious food items, manage cart, place orders with address and phone number, and make payments via the **Cashfree** payment gateway.

## 🚀 Features

- 🔍 **Search Functionality** to find food by name or description
- 📦 **Add to Cart, Update Quantity, Remove Items**
- 🧾 **Checkout with Address & Phone Input**
- 💳 **Integrated Cashfree Payment Gateway**
- ✅ **Order Status Tracking** (Pending, Confirmed, Delivered, Cancelled)
- 🧾 **Order History Page**
- ❤️ **Wishlist Functionality**
- ✉️ **Email Notifications** (SMTP)
- 📱 **Responsive UI** (Mobile Friendly)
- 🗃️ Admin panel to manage food items, orders, and users

## 🛠️ Tech Stack

- **Backend**: Django, SQLite3
- **Frontend**: HTML, CSS, Bootstrap (or custom styling)
- **Payment Integration**: [Cashfree API](https://www.cashfree.com/)
- **Authentication**: Django's built-in auth
- **Email Service**: Gmail SMTP

## 🔐 Environment Variables

All sensitive keys are stored in a `.env` file using `python-decouple`.

`.env.example` file is provided. Create your own `.env` with:

```env
SECRET_KEY=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
CASHFREE_APP_ID=
CASHFREE_SECRET_KEY=
CASHFREE_API_URL=
CASHFREE_RETURN_URL=
