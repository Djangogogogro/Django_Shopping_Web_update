from django.urls import path
from user_system.views import (
    Register_View,
    Login_View,
    logout_view,
    Add_To_Cart_View,
    Shopping_Cart_View,
    My_Products_View,
    Add_Products,
    Buy_View,
    Edit_Product,
    Forget_Passwords,
    Verify_Code,
    Reset_Password,
    DeleteFromCartView,
)

urlpatterns = [
    path("new/<str:model_type>", Register_View.as_view(), name="New User"),
    path("login/<str:model_type>", Login_View.as_view(), name="Login"),

    path("ForgetPasswords/<str:model_type>", Forget_Passwords.as_view(), name="Forget Passwords"),
    path('VerifyCode/<str:model_type>', Verify_Code.as_view(), name='Verify Code'),
    path('ResetPassword/<str:model_type>', Reset_Password.as_view(), name='Reset Password'),

    path('logout/', logout_view, name='logout'),
    
    path('product/<int:pk>/add/', Add_To_Cart_View.as_view(), name='Add To Cart'),
    path('ShoppingCart', Shopping_Cart_View.as_view(), name='Shopping Cart'),
    path('ShoppingCart/buy', Buy_View.as_view(), name='Buy'),
    path('cart/delete/<int:pk>/', DeleteFromCartView.as_view(), name='DeleteFromCart'),


    path('MyProducts', My_Products_View.as_view(), name='My Products'),
    path('MyProducts/add', Add_Products.as_view(), name='Add Products'),
    path('product/<int:pk>/edit', Edit_Product.as_view(), name='Edit Products'),
]
