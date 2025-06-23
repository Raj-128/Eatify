from django.db import models
from django.contrib.auth.models import User
import uuid

class BaseModel(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Category(BaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Food(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='foods')
    food_name = models.CharField(max_length=100)
    food_slug = models.SlugField(unique=True)
    food_description = models.TextField()
    food_price = models.IntegerField(default=0)
    food_demo_price = models.IntegerField(default=0)
    quantity = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.food_name

class FoodMetaInformation(BaseModel):
    food = models.OneToOneField(Food, on_delete=models.CASCADE, related_name="meta_info")
    food_quantity = models.CharField(max_length=50, null=True, blank=True)
    food_measure = models.CharField(
        max_length=100, null=True, blank=True,
        choices=(("GM","GM"),("KG", "KG"), ("ML", "ML"), ("L", "L"))
    )
    is_restrict = models.BooleanField(default=False)
    restrict_quantity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Meta Info of {self.food.food_name}"

class FoodImages(BaseModel):
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="images")
    food_image = models.ImageField(upload_to="products")

    def __str__(self):
        return f"Image for {self.food.food_name}"

class Cart(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.food.food_name} in cart of {self.user.username}"

class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True)  # 👈 Add this line
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(
        max_length=50, choices=(
            ("PENDING", "Pending"),
            ("CONFIRMED", "Confirmed"),
            ("DELIVERED", "Delivered"),
            ("CANCELLED", "Cancelled")
        ), default="PENDING"
    )

    def __str__(self):
        return f"Order #{self.uid} by {self.user.username}"

class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.IntegerField()

    def __str__(self):
        return f"{self.food.food_name} x{self.quantity}"

class Address(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.user.username} Address"

class Review(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s review on {self.food.food_name}"

class Wishlist(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.food.food_name} in wishlist of {self.user.username}"
