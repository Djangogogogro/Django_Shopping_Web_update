# blog/views.py
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views import View
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import redirect, get_object_or_404, render
from user_system.forms import CustomerLoginForm
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from sentence_transformers import SentenceTransformer
from user_system.function.forget_passwords import send_email
import faiss
import numpy as np
import os
from user_system.models import (
    Customer,
    Seller,
    Shopping_Cart,
    Order,
)
from showitem.models import (
    Product,
    ProductImage
)
from .forms import ProductFormWithImages

class Register_View(CreateView):
    template_name = "new.html"
    fields = ["user_name", "user_mail", "user_password"]
    success_url = reverse_lazy('product_list')

    def get_model_class(self):
        self.model_type = self.kwargs.get('model_type')
        if self.model_type == 'customer':
            return Customer
        elif self.model_type == 'seller':
            return Seller
        else:
            raise ValueError("Invalid model type")
        
    def dispatch(self, request, *args, **kwargs):
        self.model = self.get_model_class()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_type'] = self.kwargs.get('model_type')
        return context

    def form_valid(self, form):
        model = self.get_model_class()
        all_user = model.objects
        count = all_user.count() + 1
        
        form.instance.user_ID = f'{(self.model_type[0]).upper()}{str(count)}'

        form.instance.user_password = make_password(form.instance.user_password)

        try:
            customer = model.objects.get(user_mail = form.instance.user_mail)
            form.add_error(None, "帳號已存在")
            return self.form_invalid(form)
        except:
            return super().form_valid(form)

    
class Login_View(FormView):
    template_name = 'login.html'
    form_class = CustomerLoginForm
    success_url = reverse_lazy('product_list')

    def get_model_class(self):
        self.model_type = self.kwargs.get('model_type')
        if self.model_type == 'customer':
            return Customer
        elif self.model_type == 'seller':
            return Seller
        else:
            raise ValueError("Invalid model type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_type'] = self.kwargs.get('model_type')
        return context

    def form_valid(self, form):
        email = form.cleaned_data['user_mail']
        password = form.cleaned_data['user_password']
        model = self.get_model_class()

        try:
            customer = model.objects.get(user_mail=email)
            if check_password(password, customer.user_password):
                self.request.session['user_ID'] = customer.user_ID
                self.request.session['user_name'] = customer.user_name

                return super().form_valid(form)
            else:
                form.add_error(None, "password error")
                return self.form_invalid(form)
        except model.DoesNotExist:
            form.add_error('user_mail', "帳號不存在")
            return self.form_invalid(form)




class Forget_Passwords(View):
    template_name = 'forget_passwords_enter_email.html'

    def get(self, request, model_type):
        return render(request, self.template_name, {'model_type': model_type})

    def get_model_class(self):
        self.model_type = self.kwargs.get('model_type')
        if self.model_type == 'customer':
            return Customer
        elif self.model_type == 'seller':
            return Seller
        else:
            raise ValueError("Invalid model type")

    def post(self, request, model_type):
        email = request.POST.get('email')
        model = self.get_model_class()
        try:
            user = model.objects.get(user_mail=email)
        except model.DoesNotExist:
            messages.error(request, "查無此 Email")
            return redirect('Forget Passwords', model_type=model_type)

        verification_code = send_email(email)
        request.session['reset_email'] = email
        request.session['verification_code'] = verification_code

        return redirect('Verify Code', model_type=model_type)

class Verify_Code(View):
    template_name = 'forget_passwords_verify_code.html'

    def get(self, request, model_type):
        return render(request, self.template_name)

    def post(self, request, model_type):
        input_code = request.POST.get('code')
        saved_code = request.session.get('verification_code')

        if input_code == saved_code:
            return redirect('Reset Password', model_type=model_type)
        else:
            messages.error(request, "驗證碼錯誤")
            return redirect('Verify Code', model_type=model_type)
        
class Reset_Password(View):
    template_name = 'forget_passwords_reset_password.html'

    def get_model_class(self, model_type):
        if model_type == 'customer':
            return Customer
        elif model_type == 'seller':
            return Seller
        else:
            raise ValueError("Invalid model type")

    def get(self, request, model_type):
        return render(request, self.template_name, {'model_type': model_type})

    def post(self, request, model_type):
        new_password = request.POST.get('new_password')
        email = request.session.get('reset_email')
        model = self.get_model_class(model_type)

        try:
            user = model.objects.get(user_mail=email)
            user.user_password = make_password(new_password)
            user.save()

            # 清理 session
            del request.session['reset_email']
            del request.session['verification_code']

            return redirect('Login', model_type=model_type)
        except model.DoesNotExist:
            return render(request, self.template_name, {
                'error': '使用者不存在',
                'model_type': model_type
            })



def logout_view(request):
    request.session.flush()
    return redirect('product_list')

class Shopping_Cart_View(View):
    template_name = "shopping_cart.html"

    def get(self, request):
        user_ID = request.session.get('user_ID')
        cart_items = Shopping_Cart.objects.filter(user_ID__user_ID=user_ID)
        total = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, self.template_name, {"cart_items": cart_items, "total": total})

    def post(self, request):
        user_ID = request.session.get('user_ID')
        cart_items = Shopping_Cart.objects.filter(user_ID__user_ID=user_ID)

        # 處理刪除
        delete_id = request.POST.get("delete_item")
        if delete_id:
            Shopping_Cart.objects.filter(id=delete_id, user_ID__user_ID=user_ID).delete()

        # 更新數量
        for item in cart_items:
            qty_key = f"quantity_{item.id}"
            if qty_key in request.POST:
                try:
                    new_qty = int(request.POST[qty_key])
                    item.quantity = max(1, new_qty)  # 最小數量為 1
                    item.save()
                except ValueError:
                    pass  # 忽略非整數輸入

        return redirect("Shopping Cart")
    
class DeleteFromCartView(DeleteView):
    model = Shopping_Cart
    success_url = reverse_lazy('Shopping Cart')

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class Add_To_Cart_View(View):
    def post(self, request, pk):
        customer_id = request.session.get('user_ID')
        if not customer_id:
            return redirect(reverse('Login', args=['customer']))

        product = get_object_or_404(Product, pk=pk)
        quantity = int(request.POST.get('quantity', 1))
        customer = get_object_or_404(Customer, user_ID=customer_id)


        if quantity <= product.quantity:

            cart_item, created = Shopping_Cart.objects.get_or_create(
                user_ID=customer,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

        else:
            messages.error(self.request, "Not enough product")


        return redirect('product_list')
    
class Buy_View(View):
    def post(self, request):
        user_id = request.session.get('user_ID')
        customer = get_object_or_404(Customer, user_ID = user_id)
        shopping_carts = Shopping_Cart.objects.filter(user_ID=customer)

        for item in shopping_carts:
            qty_key = f'quantities_{item.id}'
            new_qty = request.POST.get(qty_key)
            if new_qty:
                item.quantity = int(new_qty)
                item.save()

        order_seller_is_available = []
        for cart in shopping_carts:
            if cart.quantity <= cart.product.quantity:
                cart.product.quantity -= cart.quantity
                cart.product.save()

                seller = get_object_or_404(Seller, products = cart.product)
                if not (seller.user_ID in order_seller_is_available):
                    Order.objects.create(
                        order_ID = f'ESTD-{Order.objects.count()}',
                        customer_ID = customer,
                        seller_ID = seller,
                    )
                    order_seller_is_available.append(seller.user_ID)
            else:
                messages.error(self.request, f"{cart.product.name} is NOT nough")

        for cart in shopping_carts:
            seller = get_object_or_404(Seller, products = cart.product)
            order = Order.objects.filter(seller_ID=seller).order_by('-id').first()
            order.products += f'{cart.product.name}|{cart.product.price}|{cart.quantity},'
            order.save()
            cart.delete()
            print(order.products)
               
        return redirect('Shopping Cart')


class My_Products_View(ListView):
    model = Product
    template_name = "my_products.html"
    context_object_name = "products"

    def get_queryset(self):
        user_id = self.request.session.get('user_ID')
        if not user_id:
            return redirect('Login')
        try:
            seller = Seller.objects.get(user_ID=user_id)
            return seller.products.all()
        except Seller.DoesNotExist:
            return Product.objects.none()

class Add_Products(CreateView):
    model = Product
    template_name = "add_products.html"
    form_class = ProductFormWithImages
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        current_user_id = self.request.session.get('user_ID')
        if not current_user_id:
            return redirect('Login')

        product = form.save()
        self.object = product

        # 關聯賣家
        try:
            seller = Seller.objects.get(user_ID=current_user_id)
            seller.products.add(product)
        except Seller.DoesNotExist:
            product.delete()
            return redirect('Login')

        # 上傳圖片
        images = self.request.FILES.getlist('images')
        for img in images:
            ProductImage.objects.create(
                product=product,
                image_file=img,
                image_path=' ',
            )

        # 🧠 向量化語意內容（語意搜尋使用）
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            vector = model.encode([product.name])  # 可加其他欄位
            vector = np.array(vector).astype('float32')

            # 載入/建立向量索引
            index_path = "vector_store/product_index.faiss"
            id_path = "vector_store/product_ids.npy"
            os.makedirs("vector_store", exist_ok=True)

            if os.path.exists(index_path) and os.path.exists(id_path):
                index = faiss.read_index(index_path)
                id_array = np.load(id_path)
            else:
                index = faiss.IndexFlatL2(vector.shape[1])
                id_array = np.array([], dtype=np.int32)

            # 將向量新增進索引
            index.add(vector)
            id_array = np.append(id_array, product.id)

            # 儲存索引與ID
            faiss.write_index(index, index_path)
            np.save(id_path, id_array)
        except Exception as e:
            print(f"[FAISS Error] 商品向量化失敗：{e}")

        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)
    
class Edit_Product(UpdateView):
    model = Product
    template_name = "product_edit.html"
    form_class = ProductFormWithImages
    success_url = reverse_lazy('My Products')
    