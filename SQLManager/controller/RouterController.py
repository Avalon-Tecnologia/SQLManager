''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 '''

from typing import Any, Dict, List, Optional, Union
import importlib
import json

from ..CoreConfig import CoreConfig
from ..connection import database_connection
from .TableController import TableController

class AutoRouter:
    """
    Controladora de Rotas Automáticas (AutoRouter)
    
    Responsável por processar requisições dinâmicas para tabelas do banco de dados,
    eliminando a necessidade de criar controllers manuais para CRUD padrão.
    
    Uso:
        router = AutoRouter(db_connection)
        response = router.handle_request('GET', 'Products', path_parts=['1'])
    """
    
    def __init__(self, db: database_connection):
        self.db = db
        self.config = CoreConfig.get_router_config()
        self.enabled = self.config.get('enable_dynamic_routes', False)
        
        # Otimização: Cache de configurações normalizadas (Upper Case)
        self._exclude_tables = {t.upper() for t in self.config.get('exclude_tables', [])}
        self._tables_config = {k.upper(): v for k, v in self.config.get('tables', {}).items()}
        
        # Cache de classes e metadados para evitar reflection repetitivo
        self._class_cache: Dict[str, Any] = {}
        self._field_map_cache: Dict[str, Dict[str, str]] = {}

    def _get_table_class(self, table_name: str):
        """
        Tenta importar a classe da tabela dinamicamente a partir do TablePack.
        Utiliza cache para evitar imports repetitivos.
        """
        table_upper = table_name.upper()
        if table_upper in self._class_cache:
            return self._class_cache[table_upper]

        module = None
        possible_modules = ["model.TablePack", "src.model.TablePack"]
        
        for mod_name in possible_modules:
            try:
                module = importlib.import_module(mod_name)
                break
            except ImportError:
                continue
        
        if not module:
            return None
        
        # Busca case-insensitive pela classe da tabela
        for name in dir(module):
            if name.upper() == table_upper:
                cls = getattr(module, name)
                self._class_cache[table_upper] = cls
                return cls
        return None

    def _get_field_map(self, table: TableController) -> Dict[str, str]:
        """
        Retorna um mapa {NOME_CAMPO_UPPER: NomeRealDoAtributo} para a tabela.
        Cacheado por nome da tabela.
        """
        t_name = table.table_name.upper()
        if t_name in self._field_map_cache:
            return self._field_map_cache[t_name]
        
        field_map = {}
        # Atributos internos a ignorar
        ignore = {
            'db', 'table_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 
            'isUpdate', 'controller', 'select', 'insert', 'update', 'delete',
            'insert_recordset', 'update_recordset', 'delete_from', 'field',
            'exists', 'validate_fields', 'validate_write', 'clear', 'set_current',
            'get_table_columns', 'get_table_index', 'get_table_foreign_keys', 'get_table_total'
        }
        
        # Inspeciona a instância para encontrar campos válidos (EDTs/Enums/Values)
        for attr in dir(table):
            if attr.startswith('_') or attr in ignore:
                continue
            
            try:
                val = getattr(table, attr)
                if callable(val): continue
                field_map[attr.upper()] = attr
            except:
                pass
        
        self._field_map_cache[t_name] = field_map
        return field_map

    def _evaluate_condition(self, table: TableController, condition_str: str):
        """
        Avalia uma string de condição (ex: 'ACTIVE == 1') no contexto da tabela.
        Retorna um FieldCondition ou BinaryExpression.
        """
        context = {}
        field_map = self._get_field_map(table)
        for real_name in field_map.values():
            context[real_name] = getattr(table, real_name)
        
        try:
            return eval(condition_str, {"__builtins__": {}}, context)
        except Exception as e:
            raise ValueError(f"Invalid condition syntax: {str(e)}")

    def handle_request(self, method: str, table_name: str, path_parts: List[str] = [], 
                       query_params: Dict[str, Any] = {}, body: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Processa a requisição dinâmica e retorna o resultado padronizado.
        
        Args:
            method (str): Método HTTP (GET, POST, PATCH, DELETE)
            table_name (str): Nome da tabela alvo
            path_parts (List[str]): Segmentos da URL após a tabela (ex: ['1'] ou ['active'])
            query_params (Dict): Parâmetros de query string (filtros, paginação)
            body (Dict): Corpo da requisição (JSON)
            
        Returns:
            Dict: {status: int, data: Any, error: str, meta: Dict}
        """
        if not self.enabled:
            return {"status": 404, "error": "AutoRouter is disabled in CoreConfig"}

        table_upper = table_name.upper()

        # 1. Verificar se tabela está excluída (Segurança - O(1))
        if table_upper in self._exclude_tables:
            return {"status": 404, "error": f"Table '{table_name}' access is restricted"}

        # 2. Obter Classe da Tabela (Cacheado)
        TableClass = self._get_table_class(table_name)
        if not TableClass:
            return {"status": 404, "error": f"Table '{table_name}' not found in TablePack"}

        # 3. Instanciar Tabela
        try:
            table = TableClass(self.db)
        except Exception as e:
            return {"status": 500, "error": f"Error instantiating table: {str(e)}"}

        # 4. Verificar Configuração Específica da Tabela (O(1))
        table_config = self._tables_config.get(table_upper, {})
        
        allowed = table_config.get('allowed_methods', ["GET", "POST", "PATCH", "DELETE"])
        if method.upper() not in allowed:
            return {"status": 405, "error": f"Method {method} not allowed for table {table_name}"}

        # 5. Roteamento por Método
        try:
            method = method.upper()
            if method == "GET":
                return self._handle_get(table, path_parts, query_params, table_config)
            elif method == "POST":
                return self._handle_post(table, body)
            elif method == "PATCH":
                if not path_parts:
                    return {"status": 400, "error": "Missing ID for PATCH"}
                return self._handle_patch(table, path_parts[0], body)
            elif method == "DELETE":
                if not path_parts:
                    return {"status": 400, "error": "Missing ID for DELETE"}
                return self._handle_delete(table, path_parts[0], table_config)
            else:
                return {"status": 405, "error": "Method not supported"}
        except Exception as e:
            return {"status": 500, "error": f"Internal Server Error: {str(e)}"}

    def _handle_get(self, table: TableController, path_parts: List[str], params: Dict, config: Dict):
        field_map = self._get_field_map(table)

        # Rota: GET /{table}/{id}
        if path_parts and path_parts[0].isdigit():
            recid = int(path_parts[0])
            if table.exists(table.RECID == recid):
                result = table.select().where(table.RECID == recid).execute()
                if result:
                    return {"status": 200, "data": self._serialize(result[0], field_map)}
            return {"status": 404, "error": "Record not found"}

        # Rota: GET /{table}/{custom_route}
        if path_parts:
            route_name = path_parts[0]
            custom_routes = config.get('custom_get', [])
            for route in custom_routes:
                if route.get('route') == route_name:
                    try:
                        condition = self._evaluate_condition(table, route.get('where', '1==1'))
                        query = table.select().where(condition)
                        
                        if 'columns' in route:
                            cols = [getattr(table, c) for c in route['columns'] if hasattr(table, c)]
                            query.columns(*cols)
                            
                        results = query.execute()
                        data = [self._serialize(r, field_map) for r in results]
                        return {"status": 200, "data": data, "meta": {"count": len(data)}}
                    except Exception as e:
                        return {"status": 500, "error": f"Custom route error: {str(e)}"}
            return {"status": 404, "error": f"Custom route '{route_name}' not found"}

        # Rota: GET /{table} (Listagem com filtros)
        try:
            page = int(params.get('page', 1))
            limit = int(params.get('limit', 20))
        except ValueError:
            return {"status": 400, "error": "Invalid pagination parameters"}

        offset = (page - 1) * limit
        
        query = table.select()
        
        # Filtros dinâmicos (ex: PRICE_gt=100)
        for key, value in params.items():
            if key in ['page', 'limit']: continue
            
            field_name_raw = key
            operator = 'eq'
            
            # Separa operador (ex: PRICE_gt -> field: PRICE, op: gt)
            if '_' in key:
                parts = key.rsplit('_', 1)
                if parts[1] in ['gt', 'gte', 'lt', 'lte', 'neq', 'like', 'in']:
                    field_name_raw = parts[0]
                    operator = parts[1]
            
            # Busca campo no mapa (O(1))
            real_field_name = field_map.get(field_name_raw.upper())
            
            if real_field_name:
                field_attr = getattr(table, real_field_name)
                
                # Aplica filtro
                if operator == 'eq': query.where(field_attr == value)
                elif operator == 'gt': query.where(field_attr > value)
                elif operator == 'gte': query.where(field_attr >= value)
                elif operator == 'lt': query.where(field_attr < value)
                elif operator == 'lte': query.where(field_attr <= value)
                elif operator == 'neq': query.where(field_attr != value)
                elif operator == 'like': query.where(field_attr.like(str(value)))

        # Executa query paginada
        query.limit(limit).offset(offset)
        results = query.execute()
        
        data = [self._serialize(r, field_map) for r in results]
        
        return {
            "status": 200, 
            "data": data,
            "meta": {"page": page, "limit": limit, "count": len(data)}
        }

    def _handle_post(self, table: TableController, body: Dict):
        field_map = self._get_field_map(table)
        
        for key, value in body.items():
            real_field_name = field_map.get(key.upper())
            if real_field_name:
                setattr(table, real_field_name, value)
        
        try:
            if table.insert():
                return {"status": 201, "data": {"RECID": table.RECID}, "message": "Created"}
            else:
                return {"status": 400, "error": "Failed to insert record"}
        except Exception as e:
            return {"status": 400, "error": str(e)}

    def _handle_patch(self, table: TableController, recid: str, body: Dict):
        if not recid.isdigit(): return {"status": 400, "error": "Invalid ID"}
        recid = int(recid)
        
        if not table.exists(table.RECID == recid):
            return {"status": 404, "error": "Record not found"}
        
        try:
            field_map = self._get_field_map(table)
            valid_fields = {}
            
            for key, value in body.items():
                real_field_name = field_map.get(key.upper())
                if real_field_name and real_field_name != 'RECID':
                    valid_fields[real_field_name] = value
            
            if not valid_fields:
                return {"status": 400, "error": "No valid fields provided for update"}

            affected = table.update_recordset(where=table.RECID == recid, **valid_fields)
            
            if affected > 0:
                return {"status": 200, "message": "Updated successfully"}
            else:
                return {"status": 304, "message": "No changes made"}
        except Exception as e:
            return {"status": 400, "error": str(e)}

    def _handle_delete(self, table: TableController, recid: str, config: Dict):
        # Verifica rotas customizadas de DELETE (ex: /Manager/Products/clear_inactive)
        if not recid.isdigit():
            custom_routes = config.get('custom_delete', [])
            for route in custom_routes:
                if route.get('route') == recid:
                    try:
                        condition = self._evaluate_condition(table, route.get('where', '0==1'))
                        affected = table.delete_from().where(condition).execute()
                        return {"status": 200, "message": f"Deleted {affected} records"}
                    except Exception as e:
                        return {"status": 500, "error": f"Custom delete error: {str(e)}"}
            return {"status": 400, "error": "Invalid ID or custom route"}
        
        recid = int(recid)
        
        if not table.exists(table.RECID == recid):
            return {"status": 404, "error": "Record not found"}

        behavior = config.get('delete_behavior', {'mode': 'physical'})
        
        try:
            if behavior.get('mode') == 'logical':
                field = behavior.get('field', 'IS_DELETED')
                value = behavior.get('value', 1)
                table.update_recordset(where=table.RECID == recid, **{field: value})
            else:
                table.delete_from().where(table.RECID == recid).execute()
            
            return {"status": 200, "message": "Deleted successfully"}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    def _serialize(self, record_obj, field_map: Dict[str, str]) -> Dict:
        """Serializa uma instância de TableController para dict usando mapa de campos"""
        if isinstance(record_obj, dict):
            return record_obj
            
        data = {}
        # Itera apenas sobre os campos mapeados da tabela
        for real_name in field_map.values():
            try:
                val = getattr(record_obj, real_name)
                if callable(val): continue
                data[real_name] = val
            except:
                pass
        return data
''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 '''