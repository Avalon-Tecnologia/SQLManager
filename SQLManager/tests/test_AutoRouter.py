''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 26/02/2026 '''

import unittest
from unittest.mock import patch
import sys
import os

# Ajuste de path para importar o SQLManager corretamente
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.controller.RouterController import AutoRouter
from SQLManager.CoreConfig import CoreConfig
from SQLManager.controller.TableController import TableController
from SQLManager.controller.EDTController import EDTController
from SQLManager.connection import database_connection

# Definição da Tabela de Teste (Mapeia a tabela SQL criada no banco)
class AutoRouterTestTable(TableController):
    def __init__(self, db):
        super().__init__(db, "AutoRouterTest")
        self.RECID = EDTController("onlyNumbers", int)
        self.NAME = EDTController("any", str)
        self.PRICE = EDTController("float", float)
        self.ACTIVE = EDTController("bool", bool)

class TestAutoRouterIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Configura a conexão com o banco de dados uma única vez"""
        print("\n[SETUP] Iniciando conexão com Banco de Dados...")
        
        # Configuração de Conexão
        CoreConfig.configure(
            load_from_env=False,                    
            db_user="Matheus_Salvagno",
            db_password="AvT@Matheus",
            db_server="100.108.119.125,15433",
            db_database="Seller_Center"
        )
        
        cls.db = database_connection()
        try:
            cls.db.connect()
            print("[SETUP] Conectado com sucesso!")
        except Exception as e:
            print(f"[SETUP] FALHA AO CONECTAR: {e}")
            raise e

    @classmethod
    def tearDownClass(cls):
        """Fecha a conexão ao terminar todos os testes"""
        if hasattr(cls, 'db'):
            cls.db.disconnect()
            print("\n[TEARDOWN] Conexão encerrada.")

    def setUp(self):
        """Prepara o ambiente antes de CADA teste"""
        # 1. Reseta e Reconfigura o CoreConfig (pois o reset limpa tudo)
        CoreConfig.reset()
        CoreConfig.configure(
            load_from_env=False,                    
            db_user="Matheus_Salvagno",
            db_password="AvT@Matheus",
            db_server="100.108.119.125,15433",
            db_database="Seller_Center"
        )
        
        # 2. Configura o Router para aceitar nossa tabela de teste
        router_config = {
            "enable_dynamic_routes": True,
            "tables": {
                "AutoRouterTest": {
                    "allowed_methods": ["GET", "POST", "PATCH", "DELETE"]
                }
            }
        }
        CoreConfig.configure_router(router_config)
        
        # 3. Instancia o Router com a conexão real
        self.router = AutoRouter(self.db)
        
        # 4. Mock para o Router encontrar nossa classe AutoRouterTestTable
        # Isso evita ter que criar o arquivo físico em src/model/TablePack.py
        self.patcher = patch("SQLManager.controller.RouterController.AutoRouter._get_table_class")
        self.mock_get_class = self.patcher.start()
        
        def side_effect(table_name):
            if table_name.upper() == "AUTOROUTERTEST":
                return AutoRouterTestTable
            return None
        self.mock_get_class.side_effect = side_effect

        # 5. Limpa a tabela no banco para garantir teste limpo
        try:
            # Garante que não há transações pendentes travando a tabela
            if hasattr(self.db, 'rollback'):
                try: self.db.rollback()
                except: pass
            self.db.executeCommand("DELETE FROM AutoRouterTest")
        except Exception as e:
            print(f"[SETUP] Aviso: Erro ao limpar tabela: {e}")

    def tearDown(self):
        """Limpeza após cada teste"""
        self.patcher.stop()
        # Rollback para liberar locks caso o teste falhe no meio
        if hasattr(self.db, 'rollback'):
            try: self.db.rollback()
            except: pass


    def test_1_insert_success(self):
        """Teste de Inserção (POST)"""
        print("\n[TESTE] 1. Inserção (POST)")
        
        payload = {
            "NAME": "Produto Teste Insert",
            "PRICE": 100.50,
            "ACTIVE": True
        }
        
        response = self.router.handle_request("POST", "AutoRouterTest", body=payload)
        print(f"Response: {response}")
        
        self.assertEqual(response['status'], 201, f"Erro no Insert: {response.get('error')}")
        self.assertIn('RECID', response['data'])
        self.assertTrue(str(response['data']['RECID']).isdigit())

        self.assertIn('RECID', response['data'])
        self.assertTrue(str(response['data']['RECID']).isdigit())

    def test_2_update_active_false(self):
        """Teste de Atualização de ACTIVE para False (PATCH)"""
        print("\n[TESTE] 2. Atualização ACTIVE -> False")
        
        # Passo 1: Inserir dado inicial
        payload = {
            "NAME": "Produto Ativo",
            "PRICE": 50.00,
            "ACTIVE": True
        }
        create_resp = self.router.handle_request("POST", "AutoRouterTest", body=payload)
        recid = str(create_resp['data']['RECID'])
        
        # Passo 2: Atualizar ACTIVE para False
        update_payload = {"ACTIVE": False}
        response = self.router.handle_request("PATCH", "AutoRouterTest", path_parts=[recid], body=update_payload)
        print(f"Response: {response}")
        
        self.assertEqual(response['status'], 200, f"Erro no Update: {response.get('error')}")
        
        # Passo 3: Verificar no banco se mudou
        get_resp = self.router.handle_request("GET", "AutoRouterTest", path_parts=[recid])
        self.assertFalse(get_resp['data']['ACTIVE'])
    
if __name__ == '__main__':
    unittest.main()


