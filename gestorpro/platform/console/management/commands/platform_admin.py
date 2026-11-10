"""
Da o quita acceso a la consola de plataforma a un usuario EXISTENTE.

    python manage.py platform_admin persona@gestorpro.co              # da acceso (y crea su clave 2FA)
    python manage.py platform_admin persona@gestorpro.co --reset-2fa  # perdió el celular: clave nueva
    python manage.py platform_admin persona@gestorpro.co --revoke
    python manage.py platform_admin persona@gestorpro.co --create     # la cuenta no existe: la crea

Sin --create no crea usuarios. Con --create, la contraseña la escribe quien ejecuta el
comando (no se ve al escribir) y debe cumplir las reglas de contraseñas. Nunca es superusuario.

El personal de la plataforma entra con contraseña + código de una app
autenticadora (core/identity/mfa.py). La clave de esa app se crea AQUÍ, en el
servidor, y se muestra una sola vez: escanéala o escríbela en la app en ese
momento. Por seguridad, el login nunca ofrece crearla.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from gestorpro.core.audit import services as audit
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.identity import mfa


class Command(BaseCommand):
    help = 'Da o quita acceso a la consola de plataforma (personal de GestorPro), con verificación en dos pasos.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument('--revoke', action='store_true')
        parser.add_argument('--reset-2fa', action='store_true',
                            help='Clave nueva para la app autenticadora (la anterior deja de servir).')
        parser.add_argument('--create', action='store_true',
                            help='Si la cuenta no existe, la crea (pide nombre y contraseña).')

    def handle(self, *args, email, revoke=False, reset_2fa=False, create=False, **options):
        user = get_user_model().objects.filter(email__iexact=email.strip()).first()
        if user is None and create and not revoke:
            user = self._create(email.strip().lower())
        if user is None:
            raise CommandError('No existe un usuario con ese email. Créalo con --create o crea su cuenta primero.')
        if revoke:
            user.is_platform_admin = user.is_staff = False
            user.save(update_fields=['is_platform_admin', 'is_staff'])
            mfa.reset(user)
            self.stdout.write(self.style.SUCCESS(f'{user.email} ya no tiene acceso a la consola de plataforma.'))
            return
        user.is_platform_admin = True
        user.is_staff = True  # admin de Django de la plataforma (también exige el código)
        user.save(update_fields=['is_platform_admin', 'is_staff'])
        self.stdout.write(self.style.SUCCESS(f'{user.email} ahora tiene acceso a la consola de plataforma.'))
        if user.totp_secret and not reset_2fa:
            self.stdout.write('Su verificación en dos pasos ya está configurada '
                              '(usa --reset-2fa si perdió el celular).')
            return
        key = mfa.enroll(user)
        audit.security_event(SecurityEvent.Kind.MFA_ENROLLED, user=user)
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('VERIFICACIÓN EN DOS PASOS: esto se muestra UNA sola vez.'))
        self.stdout.write('En la app autenticadora del celular: "Agregar cuenta" > "Ingresar clave" y escribe:')
        self.stdout.write(f'    Cuenta: {user.email}')
        self.stdout.write(f'    Clave:  {key["secret"]}')
        self.stdout.write('    Tipo:   basada en el tiempo (6 dígitos)')
        self.stdout.write(f'O abre este enlace en el celular: {key["uri"]}')
        self.stdout.write('Desde ahora, al entrar se pide la contraseña y luego el código de la app.')

    def _create(self, email):
        import getpass

        from django.contrib.auth import password_validation
        from django.core.exceptions import ValidationError

        User = get_user_model()
        if '@' not in email:
            raise CommandError('Escribe un email válido.')
        first_name = input('Nombre: ').strip() or 'Soporte'
        candidate = User(email=email, first_name=first_name, last_name='GestorPro')
        for _ in range(3):
            password = getpass.getpass('Contraseña (mínimo 12 caracteres, no se ve al escribir): ')
            if password != getpass.getpass('Repítela: '):
                self.stdout.write('No coinciden. Intenta de nuevo.')
                continue
            try:
                password_validation.validate_password(password, candidate)
            except ValidationError as exc:
                self.stdout.write(' '.join(exc.messages))
                continue
            user = User.objects.create_user(email=email, password=password, first_name=first_name,
                                            last_name='GestorPro')
            self.stdout.write(self.style.SUCCESS(f'Cuenta {email} creada.'))
            return user
        raise CommandError('No se creó la cuenta.')
