from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
import uuid
from django.utils import timezone
from src.core.models import AbstractBaseModel


# Create models.
class UserManager(BaseUserManager):
    def create_user(self,email,password=None,**extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email) # Makes email lowercase and clean
        user = self.model(email=email, **extra_fields)
        user.set_password(password) #Hashes password
        user.save(using=self._db)
        return user

    def create_staff(self,email,password=None,**extra_fields):
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',False)
        if not extra_fields.get('is_staff'):
            raise ValueError('Users must have is_staff=True')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Users')
        return self.create_user(email,password,**extra_fields)

    def create_superuser(self,email,password=None, **extra_fields):
        # If 'is_staff' is already set, it will not overwrite it.
        extra_fields.setdefault('is_staff', True) #Can log into admin
        extra_fields.setdefault('is_superuser', True) #Has all permissions
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email,password,**extra_fields)

#Custom user model
class User(AbstractBaseModel,AbstractBaseUser,PermissionsMixin):
   # Core identification fields
   uuid=models.UUIDField(default=uuid.uuid4, editable=False)
   email = models.EmailField(unique=True)

   #Authentication and status field
   is_active = models.BooleanField(default=True) #Account active status
   is_staff = models.BooleanField(default=False) #Admin access
   date_joined = models.DateTimeField(default=timezone.now)

   # Detailed user fields
   first_name = models.CharField(max_length=50)
   last_name = models.CharField(max_length=50)
   contact_number = models.CharField(max_length=15, blank=True, null=True)
   profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
   address = models.TextField(blank=True, null=True)
   date_of_birth = models.DateField(null=True)

   # Sets the default manager to your custom logic (create_user, etc.)
   objects = UserManager()


   USERNAME_FIELD = 'email'
   REQUIRED_FIELDS = []

   def __str__(self):
       return self.email
