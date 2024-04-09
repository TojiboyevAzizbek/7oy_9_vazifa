from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from main import models
from django.core.paginator import Paginator, PageNotAnInteger,EmptyPage


def paginator_page(List,num,request):
    paginator = Paginator(List,num)
    page = request.GET.get('page')
    try:
        List = paginator.page(page)
    except PageNotAnInteger:
        List = paginator.page(1)
    except EmptyPage:
        List = paginator.page(paginator.num_pages)
    return List

def index(request):
    categories = models.Category.objects.all()[:5:]
    products = []
    reviews = models.Review.objects.all()
    new_products = models.Product.objects.all().values()[::-1][:10:]
    if request.user.is_authenticated:
        for i in models.Product.objects.all():
            if models.WishList.objects.filter(product=i,user=request.user):
                i.is_like = True
            else:
                i.is_like = False
            products.append(i)
    else:
        products = models.Product.objects.all()

    
    mark = 0
    for i in reviews:
        mark += i.mark
    
    mark = int(mark/len(reviews)) if reviews else 0

    context = {
        'categories':categories,
        'products':products,
        'rating':range(1,6),
        'mark':mark,
        'new_products':new_products,
        'reviews':reviews.filter(mark__gte=4),
        }
    return render(request, 'front/index.html',context)


def product_detail(request,code):
    product = models.Product.objects.get(code=code)
    reviews = models.Review.objects.filter(product=product)
    images = models.ProductImg.objects.filter(product=product)
    liked = models.WishList.objects.filter(product=product,user=request.user).count() > 0
    mark = 0

    for i in reviews:
        mark += i.mark

    mark = int(mark/len(reviews)) if reviews else 0

    context = {
        'product':product,
        'mark':mark,
        'rating':range(1,6),
        'images':images,
        'reviews':reviews,
        'liked':liked,
    }
    return render(request, 'front/product/detail.html',context)



def product_list(request,code):
    products = []
    categories = models.Category.objects.all()
    if request.user.is_authenticated:
        for i in models.Product.objects.filter(category__code=code):
            if models.WishList.objects.filter(product=i,user=request.user):
                i.is_like = True
            else:
                i.is_like = False
            products.append(i)
    else:
        products = models.Product.objects.filter(category__code=code)
    paginators = paginator_page(products,2,request)
    context = {
        'products':paginator_page(products,2,request),
        'categories':categories,
        }
    return render(request, 'front/category/product_list.html',context)

def all_products(request):
    products = models.Product.objects.all()
    categories = models.Category.objects.all()
    filter_items = dict()
    if request.method == 'GET':
        for key, value in request.GET.items():
            if value and not value == '0':
                if key == 'category_code':
                    key = 'category__code'
                elif key == 'price':
                    value = value.split(';')
                    filter_items['price__gte'] = value[0]
                    filter_items['price__lte'] = value[1]
                    continue
                elif key == 'mark':
                    value = value.split(';')
                    filter_items['review__mark__gte'] = value[0]
                    filter_items['review__mark__lte'] = value[1]
                    continue
                elif key == 'name':
                    key = 'name__icontains'
                else:
                    continue
                filter_items[key] = value
        products = models.Product.objects.filter(**filter_items)
    context = {
        'products':paginator_page(products,2,request),
        'categories':categories,
        }
    return render(request, 'front/product/list.html',context)

def product_delete(request,id):
    models.CartProduct.objects.get(id=id).delete()
    return redirect('front:active_cart')


def carts(request):
    queryset = models.Cart.objects.filter(user=request.user, status=4)
    context = {'queryset':queryset}
    return render(request, 'front/carts/list.html', context)


@login_required(login_url='auth:login')
def active_cart(request):
    queryset , _ = models.Cart.objects.get_or_create(user=request.user, status=1)
    return redirect('front:cart_detail', queryset.code)


@login_required(login_url='auth:login')
def cart_detail(request, code):
    cart = models.Cart.objects.get(code=code)
    queryset = models.CartProduct.objects.filter(cart=cart)
    if request.method == 'POST':
        data = list(request.POST.items())[1::]
        for id,value in data:
            cart_product = models.CartProduct.objects.get(id=id)
            cart_product.count = value
            cart_product.product.quantity -= int(value)
            cart.status = 2
            cart_product.product.save()
            cart.save()
            cart_product.save()
    context = {
        'cart': cart,
        'queryset':queryset
        }
    return render(request, 'front/carts/detail.html', context)


def add_to_cart(request,code):
    if models.Product.objects.filter(code=code):
        product = models.Product.objects.get(code=code)
        cart = models.Cart.objects.get(status=1, user=request.user)
        is_product = models.CartProduct.objects.filter(product=product,cart__status=1,cart__user=request.user).first()
        if is_product:
            is_product.count += 1
            is_product.save()
            return redirect('front:active_cart')
        if not cart:
            cart = models.Cart.objects.create(
                user=request.user,
                is_active=True
            )
        
        models.CartProduct.objects.create(
            product=product,
            cart=cart,
            count=1
        )
        return redirect('front:active_cart')
        
    return redirect('front:index')


@login_required(login_url='auth:login')
def list_wishlist(request):
    wishlists = models.WishList.objects.filter(user=request.user)
    context = {
        'wishlists':wishlists,
        }
    return render(request, 'front/wishlist/list.html',context) 

@login_required(login_url='auth:login')
def remove_wishlist(request,code):
    models.WishList.objects.get(user=request.user,product__code=code).delete()
    return redirect('front:wishlist')

@login_required(login_url='auth:login')
def add_wishlist(request,code):
    product = models.Product.objects.get(code=code)
    wish = models.WishList.objects.filter(product=product,user=request.user)
    if wish.count():
        return redirect('front:remove_wishlist',product.code)
    models.WishList.objects.create(product=product,user= request.user)
    return redirect('front:wishlist')


@login_required(login_url='auth:login')
def order_list(request):
    ordered = models.CartProduct.objects.filter(cart__user=request.user,cart__status=2)
    returned = models.CartProduct.objects.filter(cart__user=request.user,cart__status=3)

    if request.method == 'POST':
        if request.POST.get('accept'):
            cart = models.Cart.objects.get(status=2,user=request.user)
            cart.status = 4
            product = models.Cart.objects.filter(status=4,user=request.user)
            # cart.save()
        elif request.POST.get('cancel'):
            product = models.CartProduct.objects.get(cart__status=2)
            product.cart.status = 3
            # product.cart.save()
    
    context = {
        'ordered':ordered,
        'returned':returned,
        }
    return render(request, 'front/order/list.html',context)


def create_review(request,code):
    product = models.CartProduct.objects.filter(cart__code=code)
    print(product.last())
    # if request.method == 'POST':
    #     models.Review.objects.create(
    #         product=product,
    #         user=request.user,
    #         mark=request.POST.get('mark'),
    #         text=request.POST.get('text'),
    #     )
        # redirect('front:product_detail',product.code)
    return render(request, 'front/review/create.html')