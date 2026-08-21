from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from . import telegram_bot
from .forms import AdminLoginForm, AdminRegistrationForm
from .models import TelegramVerificationToken


def register_view(request):
    if request.method == "POST":
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            token = TelegramVerificationToken.objects.create(
                admin_user=user,
                phone_number=form.cleaned_data["phone_number"],
            )
            request.session["pending_token"] = str(token.token)
            return redirect("accounts:pending_activation")
    else:
        form = AdminRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def pending_activation_view(request):
    token_str = request.session.get("pending_token")
    token = None
    deep_link = None
    if token_str:
        token = TelegramVerificationToken.objects.filter(token=token_str).first()
        if token:
            deep_link = telegram_bot.build_deep_link(str(token.token))
    return render(request, "accounts/pending_activation.html", {
        "token": token,
        "deep_link": deep_link,
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
    })


def activation_status_json(request, token):
    """Polled by the pending-activation page so it can redirect to login
    automatically the moment Telegram confirms the phone number."""
    from django.http import JsonResponse
    obj = get_object_or_404(TelegramVerificationToken, token=token)
    return JsonResponse({
        "activated": obj.admin_user.is_active,
        "used": obj.is_used,
        "expired": obj.is_expired(),
    })


class AdminLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = AdminLoginForm
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, _("Invalid phone number, password, or your account is not yet Telegram-verified."))
        return super().form_invalid(form)


def logout_view(request):
    auth_logout(request)
    return redirect("accounts:login")
