from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('products/', views.product_list_view, name='product_list'),
    path('category/<slug:category_slug>/', views.category_products_view, name='category_products'),
    path('product/<slug:category_slug>/<slug:product_slug>/', views.product_detail_view, name='product_detail'),

    # Savat
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.cart_add_view, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove_view, name='cart_remove'),
    path('cart/update/<int:item_id>/', views.cart_update_view, name='cart_update'),

    # Buyurtma
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success_view, name='order_success'),
    path('my-orders/', views.my_orders_view, name='my_orders'),

    # wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/', views.wishlist_add_view, name='wishlist_add'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove_view, name='wishlist_remove'),
    path('wishlist/status/', views.get_wishlist_status, name='wishlist_status'),

    path('review/add/<int:product_id>/', views.add_review_view, name='add_review'),
    path('review/edit/<int:review_id>/', views.edit_review_view, name='edit_review'),
    path('review/delete/<int:review_id>/', views.delete_review_view, name='delete_review'),


    # Kuponlar
    path('apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon_view, name='remove_coupon'),

    path('api/get-sizes/', views.get_sizes_api, name='get_sizes_api'),


    #categories
    path('categories/', views.categories_view, name='categories'),

    path('telegram-settings/', views.telegram_settings_view, name='telegram_settings'),
]