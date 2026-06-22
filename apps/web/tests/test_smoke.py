import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page(client):
    response = client.get(reverse("web:home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_api_schema(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
