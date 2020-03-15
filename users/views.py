from django.views import View
from django.shortcuts import render, redirect, reverse

# https://ccbv.co.uk/projects/Django/3.0/django.views.generic.edit/FormView/
from django.views.generic import FormView

# reverse_lazy to prevent circular import
from django.urls import reverse_lazy

# https://docs.djangoproject.com/en/3.0/topics/auth/default/#authenticating-users
from django.contrib.auth import authenticate, login, logout

# import users app's login forms and models
from . import forms, models
import os
import requests


class LoginView(FormView):

    """ Login View """

    # Using inherited FormView class instead of LoginView: https://ccbv.co.uk/projects/Django/3.0/django.views.generic.edit/FormView/
    template_name = "users/login.html"
    form_class = forms.LoginForm
    success_url = reverse_lazy("core:home")

    # if login form is valid, proceed to LoginForm at forms.py
    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")
        user = authenticate(self.request, username=email, password=password)
        if user is not None:
            login(self.request, user)
        return super().form_valid(form)

    """
    # function based view for post request
    def post(self, request):
        form = forms.LoginForm(request.POST)
        # print(form)

        # print(form.is_valid())
        if form.is_valid():
            # cleaned data is the cleaned result of all fields
            # print(form.cleaned_data)
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse("core:home"))
        return render(request, "users/login.html", {"form": form})
    """


# Logout function: https://docs.djangoproject.com/en/3.0/topics/auth/default/#how-to-log-a-user-out
# LogoutView class: https://docs.djangoproject.com/en/3.0/topics/auth/default/#django.contrib.auth.views.LogoutView
def log_out(request):
    logout(request)
    return redirect(reverse("core:home"))


class SignUpView(FormView):
    # Using inherited FormView class: https://ccbv.co.uk/projects/Django/3.0/django.views.generic.edit/FormView/
    template_name = "users/signup.html"
    form_class = forms.SignUpForm
    success_url = reverse_lazy("core:home")
    # intially providing an example to users for signup
    initial = {
        "first_name": "Gildong",
        "last_name": "Hong",
        "email": "honggildong@gmail.com",
    }

    # to see where "form" came from, CMD + Click on FormView inherited class
    # if Sign up form is valid, proceed to SignUpForm at forms.py
    def form_valid(self, form):
        form.save()
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")
        user = authenticate(self.request, username=email, password=password)
        if user is not None:
            login(self.request, user)
        # getting function from models.py users app, verify user by sending randomly genearated string
        user.verify_email()
        return super().form_valid(form)


# completing verification process when user clicks href at his/her email
def complete_verification(request, verification_key):
    print(verification_key)
    # if designated verification key matches verification key given through views.py, proceed.
    try:
        # get queryset matching designated random email verification key from models.py
        user = models.User.objects.get(email_verification_key=verification_key)
        # changing a single user queryset object's boolean field email_confirmed from False to True
        user.email_confirmed = True
        # since user is verified, empty a single user queryset object's email_verification charfield.
        user.email_verification_key = ""
        # save information on database
        user.save()
    # if designated verification key does not match verification key given through views.py, raise error.
    except models.User.DoesNotExist:
        # to do : add error message
        pass
    # redirecting to home when successful
    return redirect(reverse("core:home"))


# https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/
def github_login(request):
    client_id = os.environ.get("GITHUB_ID")
    redirect_uri = "http://127.0.0.1:8000/users/login/github/callback"
    # get request to github: https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#1-request-a-users-github-identity
    # check for parameter arguments like scope of user action: https://developer.github.com/apps/building-oauth-apps/understanding-scopes-for-oauth-apps/
    return redirect(
        f"https://github.com/login/oauth/authorize?client_id={client_id}&{redirect_uri}&scope=read:user"
    )


def github_callback(request):
    client_id = os.environ.get("GITHUB_ID")
    client_secret = os.environ.get("GITHUB_SECRET")
    # print(request.GET)
    # <QueryDict: {'code': ['123921039102adf']}>
    github_callback_code = request.GET.get("code")
    if github_callback_code is not None:
        # post request to github api
        # https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#2-users-are-redirected-back-to-your-site-by-github
        request_to_github_api = requests.post(
            f"https://github.com/login/oauth/access_token?client_id={client_id}&client_secret={client_secret}&code={github_callback_code}",
            # getting response which is in json format
            headers={"Accept": "application/json"},
        )
        response_json = request_to_github_api.json()
        error = response_json.get("error", None)  # default=None
        if error is not None:
            return redirect(reverse("core:home"))
        else:
            # https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/#3-use-the-access-token-to-access-the-api
            access_token = response_json.get("access_token")
            profile_request = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/json",
                },
            )
            profile_info_json = profile_request.json()
            username = profile_info_json.get("login", None)
            # if user exists, get name, email and bio information
            if username is not None:
                name = profile_info_json.get("name")
                email = profile_info_json.get("email")
                bio = profile_info_json.get("bio")
                # lookup user information on database
                user_in_db = models.User.objects.get(email=email)
                # if there is user in database == email received from github,
                if user_in_db is not None:
                    # proceed to login
                    return redirect(reverse("users:login"))
                else:
                    # create queryset object in database with username, first_name, bio, email fields
                    user_in_db = models.User.objects.create(
                        username=email, first_name=name, bio=bio, email=email
                    )
                    # login user
                    login(request, user_in_db)
                    # redirect to home
                    return redirect(reverse("core:home"))
            # if user does not exist, redirect to login panel
            else:
                return redirect(reverse("users:login"))
    else:
        return redirect(reverse("core:home"))
