from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.bookings.models import Booking
from apps.listings.models import Amenity, Listing, ListingImage
from apps.reviews.models import Review

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "••••••••"}),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    username = forms.CharField(
        label="Имя пользователя",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        label="Я хочу",
        choices=User.Role.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("email", "username", "role", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update({"class": "form-control"})


class SearchForm(forms.Form):
    q = forms.CharField(
        label="Куда едете?",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Город, район или название"}),
    )
    check_in = forms.DateField(
        label="Заезд",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    check_out = forms.DateField(
        label="Выезд",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    guests = forms.IntegerField(
        label="Гости",
        min_value=1,
        initial=2,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title",
            "description",
            "country",
            "city",
            "postal_code",
            "street",
            "house_number",
            "floor",
            "apartment_number",
            "price",
            "currency",
            "rooms",
            "max_guests",
            "beds",
            "bathrooms",
            "housing_type",
            "parking_type",
            "amenities",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "street": forms.TextInput(attrs={"class": "form-control"}),
            "house_number": forms.TextInput(attrs={"class": "form-control"}),
            "floor": forms.TextInput(attrs={"class": "form-control"}),
            "apartment_number": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "currency": forms.Select(attrs={"class": "form-control"}),
            "rooms": forms.NumberInput(attrs={"class": "form-control"}),
            "max_guests": forms.NumberInput(attrs={"class": "form-control"}),
            "beds": forms.NumberInput(attrs={"class": "form-control"}),
            "bathrooms": forms.NumberInput(attrs={"class": "form-control"}),
            "housing_type": forms.Select(attrs={"class": "form-control"}),
            "parking_type": forms.Select(attrs={"class": "form-control"}),
            "amenities": forms.CheckboxSelectMultiple(),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("date_from", "date_to", "guests")
        widgets = {
            "date_from": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_to": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "guests": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def __init__(self, *args, listing=None, **kwargs):
        self.listing = listing
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        guests = cleaned.get("guests", 1)

        if not self.listing:
            return cleaned

        if date_from and date_to:
            if date_from >= date_to:
                raise ValidationError("Дата выезда должна быть позже даты заезда.")
            if date_from < timezone.localdate():
                raise ValidationError("Дата заезда не может быть в прошлом.")

        if guests > self.listing.max_guests:
            raise ValidationError(f"Максимум гостей для этого жилья: {self.listing.max_guests}.")

        overlap = Booking.objects.filter(
            listing_id=self.listing.id,
            status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
            date_from__lt=date_to,
            date_to__gt=date_from,
        ).exists()
        if overlap:
            raise ValidationError("Выбранные даты заняты. Выберите другие даты.")

        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "text")
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{i} ★") for i in range(5, 0, -1)],
                attrs={"class": "form-control"},
            ),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Расскажите о проживании..."}),
        }
