from django import forms
from django.contrib.auth.models import User
from schedule.models import Member


class RegisterForm(forms.Form):
    name = forms.CharField(label='이름', max_length=50)
    belt = forms.ChoiceField(label='띠/단', choices=Member.BELT_CHOICES)
    password1 = forms.CharField(label='비밀번호', widget=forms.PasswordInput)
    password2 = forms.CharField(label='비밀번호 확인', widget=forms.PasswordInput)

    def clean_name(self):
        name = self.cleaned_data['name']
        if User.objects.filter(username=name).exists():
            raise forms.ValidationError('이미 등록된 이름입니다.')
        return name

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('비밀번호가 일치하지 않습니다.')
        return cleaned
