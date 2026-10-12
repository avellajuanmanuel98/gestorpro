"""
Da o quita acceso a la consola de plataforma a un usuario EXISTENTE.

    python manage.py platform_admin persona@gestorpro.co
    python manage.py platform_admin persona@gestorpro.co --revoke

Nunca crea usuarios ni contraseñas: la persona debe tener ya su cuenta.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Da o quita acceso a la consola de plataforma (personal de GestorPro).'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--revoke', action='store_true')

    def handle(self, *args, email, revoke=False, **options):
        user = get_user_model().objects.filter(email__iexact=email.strip()).first()
        if user is None:
            raise CommandError('No existe un usuario con ese email. Debe crear su cuenta primero.')
        user.is_platform_admin = not revoke
        user.is_staff = not revoke  # admin de Django de la plataforma
        user.save(update_fields=['is_platform_admin', 'is_staff'])
        verb = 'ya no tiene' if revoke else 'ahora tiene'
        self.stdout.write(self.style.SUCCESS(f'{user.email} {verb} acceso a la consola de plataforma.'))
