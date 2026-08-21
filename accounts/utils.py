from django.db.models import Max
from oauth2_provider.models import get_application_model


def get_oauth2_clients_for_user(user):
    return (
        get_application_model()
        .objects.filter(accesstoken__user=user)
        .annotate(connected_at=Max('accesstoken__created'))
        .order_by('-connected_at')
    )
