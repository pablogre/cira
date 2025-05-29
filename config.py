# requirements.txt
Flask==2.3.3
mysql-connector-python==8.1.0

# setup.py (opcional)
from setuptools import setup, find_packages

setup(
    name="cira-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.3.3",
        "mysql-connector-python==8.1.0",
    ],
)

# config.py (configuración separada)
import os

class Config:
    # Configuración de la base de datos
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('', '')
    DB_NAME = os.environ.get('DB_NAME', 'cira')
    
    # Configuración de Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tu-clave-secreta-aqui')
    DEBUG = os.environ.get('DEBUG', True)