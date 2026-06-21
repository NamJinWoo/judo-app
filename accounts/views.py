from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from .forms import RegisterForm
from .models import UserProfile


def login_view(request):
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password', '')
        standalone = request.POST.get('standalone') == '1'
        user = authenticate(request, username=name, password=password)
        if user is None:
            error = '이름 또는 비밀번호가 올바르지 않습니다.'
        else:
            login(request, user)
            if standalone:
                return HttpResponse('<script>window.location.replace("/")</script>')
            return redirect('schedule:home')
    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


def register_view(request):
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            belt = form.cleaned_data['belt']
            password = form.cleaned_data['password1']
            user = User.objects.create_user(
                username=name,
                password=password,
                is_active=True,
            )
            user.first_name = name
            user.save()
            UserProfile.objects.create(user=user, belt=belt)
            login(request, user)
            return redirect('schedule:home')
    return render(request, 'accounts/register.html', {'form': form})
