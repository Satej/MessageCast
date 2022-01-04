from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.models import User, APIProduct, Subscription
from api.serializers import APIProductSerializer, SubscriptionSerializer
from api.utils import send_email
from django.contrib.auth import (
    logout as auth_logout
)


class Login(LoginView):
    login_url = '/login/'
    redirect_authenticated_user = True
    redirect_field_name = '/home/'


class Logout(LogoutView):
    next_page = '/login/'
    redirect_field_name = '/login/'

    # @method_decorator(never_cache)
    # def dispatch(self, request, *args, **kwargs):
    #     request.user
    #     auth_logout(request)
    #     next_page = self.get_next_page()
    #     if next_page:
    #         # Redirect to this page until the session has been cleared.
    #         return HttpResponseRedirect(next_page)
    #     return super().dispatch(request, *args, **kwargs)


class Register(TemplateView):
    template_name = 'register.html'

    def get(self, request):
        return render(request, 'register.html', {})

    def post(self, request):

        # fetching request parameters

        # username = email
        username = request.POST['username']
        # email = request.POST['email']
        phone = request.POST['phone']
        usage = request.POST['usage']
        address = request.POST['address']
        city = request.POST['city']
        state = request.POST['state']
        country = request.POST['country']
        password = request.POST['password']

        # typical registration protocol
        try:
            try:
                User.objects.get(email=username)
                return render(request, self.template_name, {'errors': 'Email already exists.'})
            except User.DoesNotExist:
                User.objects.create_user(username=username, password=password, email=username,
                                         phone=phone, usage=usage, address=address, city=city,
                                         state=state, country=country)
        except Exception as e:
            if str(e) == 'UNIQUE constraint failed: users_user.username':
                return render(request, self.template_name, {'errors': 'Username already taken.'})
            return render(request, self.template_name, {'errors': e})

        # send confirmation email
        # twilio integration

        return render(request, self.template_name, {'success': 'New User created', 'title': 'Register'})


class HomeView(TemplateView, LoginRequiredMixin, APIView):
    template_name = "home.html"
    login_url = '/login/'
    permission_classes = [IsAuthenticated]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # fetching all api product objects from database
        objs = APIProduct.objects.all()
        context['api_products'] = APIProductSerializer(objs, many=True).data

        # preparing context for template
        context['title'] = 'Home'
        return context


class ConfirmationPageView(TemplateView, APIView):
    template_name = "confirmation_page.html"
    permission_classes = [IsAuthenticated]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # fetching all api product objects from database
        objs = APIProduct.objects.all()
        context['api_products'] = APIProductSerializer(objs, many=True).data

        # preparing context for template
        context['title'] = 'ConfirmationPage'
        return context

    def get(self, request):
        # getting request parameters
        user = request.user
        prod_id = request.GET.get('product_id')
        obj_api_product = APIProduct.objects.filter(id=prod_id).first()

        # creating or fetching subscription object
        obj_subscription, created = Subscription.objects.get_or_create(user=user, api_product=obj_api_product)

        # preparing context for template
        context = {
            'product': APIProductSerializer(obj_api_product).data,
            'subscription': SubscriptionSerializer(obj_subscription).data,
            'title': 'ConfirmationPage',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # getting request parameters
        user = request.user
        prod_id = request.POST.get('product_id')
        # unsubscribe = request.POST.get('unsubscribe')
        subscribe = request.POST.get('subscribe')
        subscription = 'subcribed' if subscribe else 'unsubscribed'

        obj_api_product = APIProduct.objects.filter(id=prod_id).first()
        if obj_api_product is not None:
            # updating the subscription status
            obj_subscription, created = Subscription.objects.get_or_create(user=user, api_product=obj_api_product)
            obj_subscription.status = True if subscribe else False
            obj_subscription.save()

            # sending email notification of the subscription
            msg = f"""You have {subscription} to {obj_api_product.name} API, please go to URL: \n\n www.agstack.org/?{obj_subscription.name}&lat={obj_subscription.latitude}&lon={obj_subscription.longitude}&uuid={obj_subscription.token}"""
            send_email(msg, user)

        # preparing context for template
        context = {
            'title': 'ConfirmationPage',
            'product': APIProductSerializer(obj_api_product).data,
            'status': 'Your subscription status has been updated',
        }
        return render(request, self.template_name, context)
