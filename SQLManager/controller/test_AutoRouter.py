''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 '''

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adiciona o diretório raiz ao path para permitir importação dos módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.controller.RouterController import AutoRouter
from SQLManager.CoreConfig import CoreConfig
from SQLManager.controller.TableController import TableController

class TestAutoRouter(unittest.TestCase):
    
    def setUp(self):
        # Reseta configurações antes de cada teste
        CoreConfig.reset()
        
        # Mock da conexão com banco de dados
        self.mock_db = MagicMock()
        
        # Configuração padrão para os testes
        self.router_config = {
            "enable_dynamic_routes": True,
            "exclude_tables": ["SecretTable"],
            "tables": {
                "Products": {
                    "allowed_methods": ["GET", "POST", "PATCH", "DELETE"]
                }
            }
        }
        CoreConfig.configure_router(self.router_config)
        
        # Instancia o Router
        self.router = AutoRouter(self.mock_db)

    def test_router_disabled(self):
        """Testa se o router retorna 404 quando desabilitado"""
        print("\n[TESTE] Router Desabilitado")
        CoreConfig.configure_router({"enable_dynamic_routes": False})
        # Reinstancia para pegar nova config
        router = AutoRouter(self.mock_db)
        
        response = router.handle_request("GET", "Products")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("disabled", response["error"])

    def test_table_excluded(self):
        """Testa acesso a tabela excluída/restrita"""
        print("\n[TESTE] Tabela Excluída")
        response = self.router.handle_request("GET", "SecretTable")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("restricted", response["error"])

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    def test_table_not_found(self, mock_get_class):
        """Testa acesso a tabela inexistente"""
        print("\n[TESTE] Tabela Não Encontrada")
        mock_get_class.return_value = None
        
        response = self.router.handle_request("GET", "NonExistent")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 404)
        self.assertIn("not found", response["error"])

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    def test_method_not_allowed(self, mock_get_class):
        """Testa método HTTP não permitido para a tabela"""
        print("\n[TESTE] Método Não Permitido")
        mock_table_cls = MagicMock()
        mock_get_class.return_value = mock_table_cls
        
        # Configura tabela ReadOnly
        config = self.router_config.copy()
        config["tables"]["ReadOnly"] = {"allowed_methods": ["GET"]}
        CoreConfig.configure_router(config)
        router = AutoRouter(self.mock_db)
        
        response = router.handle_request("POST", "ReadOnly")
        print(f"Resultado: {response}")
        self.assertEqual(response["status"], 405)

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_field_map")
    def test_get_list_success(self, mock_get_field_map, mock_get_class):
        """Testa listagem GET com paginação"""
        print("\n[TESTE] Listagem GET (Simulando 'TESTE')")
        # Mock da Instância da Tabela
        mock_table = MagicMock()
        mock_table.table_name = "Products"
        
        # Mock da cadeia de Select
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.where.return_value = mock_select
        mock_select.limit.return_value = mock_select
        mock_select.offset.return_value = mock_select
        
        # Mock dos Resultados
        record1 = MagicMock()
        record1.RECID = 1
        record1.NAME = "TESTE 1"
        
        record2 = MagicMock()
        record2.RECID = 2
        record2.NAME = "TESTE 2"
        
        mock_select.execute.return_value = [record1, record2]
        
        # Configura Mocks
        mock_table_cls = MagicMock(return_value=mock_table)
        mock_get_class.return_value = mock_table_cls
        
        # Mock do Mapa de Campos
        mock_get_field_map.return_value = {"RECID": "RECID", "NAME": "NAME"}
        
        # Executa
        response = self.router.handle_request("GET", "Products", query_params={"page": 1, "limit": 10})
        print(f"Resultado: {response}")
        
        self.assertEqual(response["status"], 200)
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(response["data"][0]["NAME"], "TESTE 1")
        self.assertEqual(response["meta"]["page"], 1)

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_field_map")
    def test_get_by_id_success(self, mock_get_field_map, mock_get_class):
        """Testa busca de registro único por ID"""
        print("\n[TESTE] GET por ID (Simulando 'TESTE')")
        mock_table = MagicMock()
        mock_table.exists.return_value = True
        
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.where.return_value = mock_select
        
        record = MagicMock()
        record.RECID = 1
        record.NAME = "TESTE"
        mock_select.execute.return_value = [record]
        
        mock_table_cls = MagicMock(return_value=mock_table)
        mock_get_class.return_value = mock_table_cls
        mock_get_field_map.return_value = {"RECID": "RECID", "NAME": "NAME"}
        
        response = self.router.handle_request("GET", "Products", path_parts=["1"])
        print(f"Resultado: {response}")
        
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["data"]["NAME"], "TESTE")

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_field_map")
    def test_post_create_success(self, mock_get_field_map, mock_get_class):
        """Testa criação de registro via POST"""
        print("\n[TESTE] POST Create (Simulando 'TESTE')")
        mock_table = MagicMock()
        mock_table.insert.return_value = True
        mock_table.RECID = 123
        
        mock_table_cls = MagicMock(return_value=mock_table)
        mock_get_class.return_value = mock_table_cls
        mock_get_field_map.return_value = {"NAME": "NAME", "PRICE": "PRICE"}
        
        body = {"NAME": "TESTE", "PRICE": 50.0}
        response = self.router.handle_request("POST", "Products", body=body)
        print(f"Resultado: {response}")
        print(f"Valor atribuído ao mock: {mock_table.NAME}")
        
        self.assertEqual(response["status"], 201)
        self.assertEqual(response["data"]["RECID"], 123)
        
        # Verifica se os atributos foram setados na instância
        self.assertEqual(mock_table.NAME, "TESTE")
        self.assertEqual(mock_table.PRICE, 50.0)

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_field_map")
    def test_patch_update_success(self, mock_get_field_map, mock_get_class):
        """Testa atualização parcial via PATCH"""
        print("\n[TESTE] PATCH Update (Simulando 'TESTE ATUALIZADO')")
        mock_table = MagicMock()
        mock_table.exists.return_value = True
        mock_table.update_recordset.return_value = 1
        
        mock_table_cls = MagicMock(return_value=mock_table)
        mock_get_class.return_value = mock_table_cls
        mock_get_field_map.return_value = {"NAME": "NAME", "RECID": "RECID"}
        
        body = {"NAME": "TESTE ATUALIZADO"}
        response = self.router.handle_request("PATCH", "Products", path_parts=["1"], body=body)
        print(f"Resultado: {response}")
        
        self.assertEqual(response["status"], 200)
        mock_table.update_recordset.assert_called()

    @patch("SQLManager.controller.AutoRouter.AutoRouter._get_table_class")
    def test_delete_success(self, mock_get_class):
        """Testa deleção de registro via DELETE"""
        print("\n[TESTE] DELETE")
        mock_table = MagicMock()
        mock_table.exists.return_value = True
        
        mock_delete_mgr = MagicMock()
        mock_table.delete_from.return_value = mock_delete_mgr
        mock_delete_mgr.where.return_value = mock_delete_mgr
        
        mock_table_cls = MagicMock(return_value=mock_table)
        mock_get_class.return_value = mock_table_cls
        
        response = self.router.handle_request("DELETE", "Products", path_parts=["1"])
        print(f"Resultado: {response}")
        
        self.assertEqual(response["status"], 200)
        mock_delete_mgr.execute.assert_called()

if __name__ == '__main__':
    unittest.main()

''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 '''