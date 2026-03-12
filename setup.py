# Setup para o Core como pacote instalável

from setuptools import setup, find_packages
from setuptools.command.install import install
import os

class CustomInstallCommand(install):
    '''Atua como um start no pip install'''
    def run(self):                        
        install.run(self)
        os.system("python -m SQLManager._model._model_update")

setup(
    name="SQLManager",
    version="4.1.1",
    description="Sistema para gerenciamento de banco de dados e validações",
    author="Avalon Tecnologia",
    author_email="nicolas.santos@avalontecnologia.com.br",
    url="https://github.com/nickzsd/SQLManager",
    packages=find_packages(include=["SQLManager", "SQLManager.*"]),
    include_package_data=True,
    #''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
    package_data={
        "SQLManager": [
            "_model/*.py",
            "EDTs/*.py",
            "enum/*.py",
            "tables/*.py",
            "views/*.py",
        ]
    },
    #''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
    python_requires=">=3.8",
    install_requires=[
        "pyodbc>=4.0.0",
        "python-dotenv>=0.19.0",
        
        #''' [BEGIN CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
        "flask-socketio>=5.0.0",  # Para WebSocketManager
        #''' [END CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    cmdclass={
        'install': CustomInstallCommand,        
        'force_reinstall': CustomInstallCommand,
    },
    license="MIT",
    license_file="LICENSE",
)
