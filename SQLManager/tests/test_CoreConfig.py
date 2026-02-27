''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 26/02/2026 '''

import unittest
from unittest.mock import patch
import os
import sys

# Adiciona o diretório raiz ao path para permitir importação dos módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.CoreConfig import CoreConfig

class TestCoreConfig(unittest.TestCase):

    def setUp(self):
        """Reseta a configuração antes de cada teste para garantir isolamento."""
        CoreConfig.reset()

    def test_is_configured_flag(self):
        """Testa se a flag is_configured funciona corretamente."""
        print("\n[TESTE] CoreConfig - Flag de Configuração")
        try:
            self.assertFalse(CoreConfig.is_configured())
            CoreConfig.configure(db_server="test")
            self.assertTrue(CoreConfig.is_configured())
            CoreConfig.reset()
            self.assertFalse(CoreConfig.is_configured())
            print("Status: Ok")
        except:
            print("Status: Error")
            raise

    @patch.dict(os.environ, {
        'DB_SERVER': 'env_server',
        'DB_DATABASE': 'env_db',
        'DB_USER': 'env_user',
        'DB_PASSWORD': 'env_password'
    })
    def test_configure_from_env(self):
        """Testa o carregamento de configuração puramente de variáveis de ambiente."""
        print("\n[TESTE] CoreConfig - Carregamento via .env")
        try:
            CoreConfig.configure(load_from_env=True)
            config = CoreConfig.get_db_config()

            self.assertEqual(config['server'], 'env_server')
            self.assertEqual(config['database'], 'env_db')
            self.assertEqual(config['user'], 'env_user')
            self.assertEqual(config['password'], 'env_password')
            self.assertTrue(CoreConfig.is_configured())
            print("Status: Ok")
        except:
            print("Status: Error")
            raise

    def test_configure_from_args_only(self):
        """Testa o carregamento de configuração de argumentos diretos, ignorando o .env."""
        print("\n[TESTE] CoreConfig - Carregamento via argumentos")
        try:
            CoreConfig.configure(
                db_server='arg_server',
                db_database='arg_db',
                db_user='arg_user',
                db_password='arg_password',
                load_from_env=False
            )
            config = CoreConfig.get_db_config()

            self.assertEqual(config['server'], 'arg_server')
            self.assertEqual(config['database'], 'arg_db')
            self.assertEqual(config['user'], 'arg_user')
            self.assertEqual(config['password'], 'arg_password')
            print("Status: Ok")
        except:
            print("Status: Error")
            raise

    @patch.dict(os.environ, {
        'DB_SERVER': 'env_server',
        'DB_DATABASE': 'env_db',
        'DB_USER': 'env_user',
        'DB_PASSWORD': 'env_password'
    })
    def test_configure_args_override_env(self):
        """Testa se os argumentos diretos sobrescrevem as variáveis de ambiente."""
        print("\n[TESTE] CoreConfig - Argumentos sobrescrevendo .env")
        try:
            CoreConfig.configure(
                db_server='arg_server',  # Deve sobrescrever 'env_server'
                db_user='arg_user',      # Deve sobrescrever 'env_user'
                load_from_env=True
            )
            config = CoreConfig.get_db_config()

            # Estes devem vir dos argumentos
            self.assertEqual(config['server'], 'arg_server')
            self.assertEqual(config['user'], 'arg_user')

            # Estes devem vir do ambiente
            self.assertEqual(config['database'], 'env_db')
            self.assertEqual(config['password'], 'env_password')
            print("Status: Ok")
        except:
            print("Status: Error")
            raise

    def test_configure_from_dict(self):
        """Testa o método utilitário configure_from_dict."""
        print("\n[TESTE] CoreConfig - Carregamento via dicionário")
        try:
            full_config = {
                "db_server": "dict_server",
                "db_database": "dict_db",
                "custom_regex": {
                    "DictRegex": r"^[A-Z]+$"
                },
                "router_config": {
                    "enable_dynamic_routes": False
                }
            }
            CoreConfig.configure_from_dict(full_config)

            db_conf = CoreConfig.get_db_config()
            self.assertEqual(db_conf['server'], 'dict_server')
            self.assertEqual(db_conf['database'], 'dict_db')

            self.assertTrue(CoreConfig.has_regex('DictRegex'))
            router_conf = CoreConfig.get_router_config()
            self.assertFalse(router_conf['enable_dynamic_routes'])
            print("Status: Ok")
        except:
            print("Status: Error")
            raise

if __name__ == '__main__':
    unittest.main()
    
''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 26/02/2026 '''