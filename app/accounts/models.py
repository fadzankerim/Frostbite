from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **fields):
        if not email:
            raise ValueError('Email je obavezan.')
        user = self.model(email=self.normalize_email(email).lower(), **fields)
        user.set_password(password)
        user.full_clean(exclude=['password'])
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **fields):
        fields['is_system_admin'] = False
        return self._create(email, password, **fields)

    def create_system_admin(self, email, password, **fields):
        """Sistemski admin se kreira samo iz komandne linije (manage.py create_system_admin)."""
        fields['is_system_admin'] = True
        return self._create(email, password, **fields)


class User(AbstractBaseUser):
    """Korisnički nalog (tabela users). Uloge vodiča i admina društva proizlaze iz tabela
    club_guides i club_admins, a ne iz polja na korisniku."""

    email = models.EmailField('email', max_length=254, unique=True)
    first_name = models.CharField('ime', max_length=60)
    last_name = models.CharField('prezime', max_length=60)
    phone = models.CharField('telefon', max_length=30, blank=True)
    emergency_contact_name = models.CharField('hitni kontakt (ime)', max_length=120, blank=True)
    emergency_contact_phone = models.CharField('hitni kontakt (telefon)', max_length=30, blank=True)
    health_notes = models.TextField('zdravstvene napomene', max_length=1000, blank=True)

    is_system_admin = models.BooleanField(default=False)
    is_active = models.BooleanField('aktivan', default=True)   # False = BLOKIRAN
    date_joined = models.DateTimeField(default=timezone.now)

    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'korisnik'
        verbose_name_plural = 'korisnici'

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def is_locked(self, now=None):
        return self.locked_until is not None and self.locked_until > (now or timezone.now())
