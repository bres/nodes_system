import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Updated to point correctly to the repository root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Quick-start development settings - unsuitable for production
# See https://djangoproject.com

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-local-fallback-key-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# ALLOWED DOMAINS: Updated to include Render (.onrender.com) for production
ALLOWED_HOSTS = ['nodes-system.onrender.com', '.onrender.com', 'localhost', '127.0.0.1']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Forms and Extensions
    "crispy_forms",
    "crispy_bootstrap5",
    'watson',
    
    # Main Application Configuration (Fires the ready() search hooks)
    'nodes.apps.NodesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'watson.middleware.SearchContextMiddleware',
]

# Automatically inject WhiteNoise middleware when DEBUG is False (Production on Render)
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Configured to look inside your 'core' directory
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'nodes.context_processors.page_header',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Configured to run your 'core' WSGI script
WSGI_APPLICATION = 'core.wsgi.application'


# Database
# Defaults to local PostgreSQL for development. Switches automatically on Render via DATABASE_URL.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'my_db',
        'USER': 'george',
        'PASSWORD': '1234',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=True)


# Password validation
# https://djangoproject.com

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://djangoproject.com

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://djangoproject.com

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Clear custom manual directory mapping so Django uses AppDirectoriesFinder automatically
STATICFILES_DIRS = [
    BASE_DIR / 'nodes' / 'nodes' / 'static',
]

# The directory where WhiteNoise looks for collected files to serve in production
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Enable WhiteNoise compression and caching for production
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}


# Default primary key field type
# https://djangoproject.com

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'