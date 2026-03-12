''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 '''

from functools import wraps
from typing    import Any, Dict, List, Optional, Union

import importlib
import inspect
import json
import os
import time
import traceback
from unittest import case

from ..CoreConfig import CoreConfig
from ..connection import database_connection

from .TableController   import TableController
from .ViewController    import ViewController
from .SystemController  import SystemController

try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

class AutoRouter:
    """
    Controladora de Rotas Automáticas (AutoRouter)
    
    Responsável por processar requisições dinâmicas para tabelas do banco de dados,
    eliminando a necessidade de criar controllers manuais para CRUD padrão.
    
    Uso:
        # Modo tradicional:
        router = AutoRouter(db_connection)
        response = router.handle_request('GET', 'Products', path_parts=['1'])
        
        # Modo Flask (auto-registro de rotas):
        app = Flask(__name__)
        router = AutoRouter(db_connection, app=app)
        # Rotas são registradas automaticamente
    """    
    
    def __init__(self, db: database_connection, app: Optional[Any] = None):
        self.db      = db
        self.app     = app
        self.config  = CoreConfig.get_router_config()
        self.enabled = self.config.get('enable_dynamic_routes', False)
        
        # Otimização: Cache de configurações normalizadas (Upper Case)
        self._exclude_tables = {t.upper() for t in self.config.get('exclude_tables', [])}                        
        
        # Cache de configurações específicas por tabela (Upper Case)
        self._tables_config = {}
        for table_name, table_cfg in self.config.get('tables', {}).items():
            self._tables_config[table_name.upper()] = table_cfg
        
        # Variaiveis de Execução
        self.current_method = None
        self.current_table  = TableController(None)

        # Cache de classes e metadados para evitar reflection repetitivo
        self._class_cache:     Dict[str, Any]            = {}
        self._field_map_cache: Dict[str, Dict[str, str]] = {}
        self._is_view_cache:   Dict[str, bool]           = {}  # Cache para saber se é View
        self._table_count_cache: Dict[str, tuple]        = {}  # Cache de total: {table_name: (timestamp, count)}
        
        # Registra rotas Flask automaticamente se app foi fornecido
        if self.app and self.enabled:
            if not FLASK_AVAILABLE:
                raise ImportError("Flask não está disponível. Instale com: pip install flask")
            self._register_routes()        

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    def _pre_handle(func):
        """
        Decorator para validação e setup antes de processar requisições.
        Usa inspect.signature para mapear argumentos de forma robusta.
        """
        sig = inspect.signature(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:                
                # Mapeia argumentos usando inspect.signature
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                # Extrai self (instância do AutoRouter)
                self = bound.arguments.get('self')

                if not self:
                    return {"status": 500, "error": "Internal error: missing self reference"}                                
                
                # Extrai argumentos necessários
                method = bound.arguments.get('method', '').upper()
                table_name = bound.arguments.get('table_name', '')
                
                # Armazena no estado da instância
                self.current_method = method
                
                # 1. Verificar se AutoRouter está habilitado
                if not self.enabled:
                    return {"status": 404, "error": "AutoRouter is disabled in CoreConfig"}
                
                table_upper = table_name.upper()
                
                # 2. Verificar se tabela está excluída (Segurança - O(1))
                if table_upper in self._exclude_tables:
                    return {"status": 404, "error": f"Table '{table_name}' access is restricted"}
                
                # 3. Obter Classe da Tabela (Cacheado)
                TableClass = self._get_table_class_by_name(table_name)
                if not TableClass:
                    return {"status": 404, "error": f"Table '{table_name}' not found in TablePack"}
                
                # 4. Instanciar Tabela
                try:
                    table = TableClass(self.db)
                    self.current_table = table
                except Exception as e:
                    return {"status": 500, "error": f"Error instantiating table: {str(e)}"}
                
                # 5. Verificar Configuração Específica da Tabela (O(1))
                table_config = self._tables_config.get(table_upper, {})
                
                # Views: apenas GET permitido
                is_view = self._is_view_cache.get(table_upper, False)
                if is_view:
                    allowed = ["GET"]
                else:
                    allowed = table_config.get('allowed_methods', ["GET", "POST", "PATCH", "DELETE"])
                
                if method not in allowed:
                    return {"status": 405, "error": f"Method {method} not allowed for {('view' if is_view else 'table')} {table_name}"}
                
                bound.arguments['_table'] = table
                bound.arguments['_table_config'] = table_config

                return func(**bound.arguments)
            except Exception as e:                                                
                print(f"{SystemController.custom_text("PRE_HANDLE", 'red')}\n{e}")
                traceback.print_exc()
                return {"status": 500, "error": f"Decorator error: {str(e)}"}
        
        return wrapper
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''    
    def _get_table_class_by_name(self, table_name: str):
        """
        Tenta importar a classe da tabela dinamicamente a partir do TablePack.
        Utiliza cache para evitar imports repetitivos.
        
        Args:
            table_name: Nome da tabela a ser buscada
            
        Returns:
            Classe da tabela ou None se não encontrada
        """
        table_upper = table_name.upper()
        if table_upper in self._class_cache:
            return self._class_cache[table_upper]

        module = None
        is_view = False
        
        # Busca em TablePack e ViewPack
        possible_modules = [
            ("model.TablePack", False),
            ("src.model.TablePack", False),
            ("model.tables", False),
            ("src.model.tables", False),
            ("model.ViewPack", True),
            ("src.model.ViewPack", True),
            ("model.views", True),
            ("src.model.views", True),
        ]

        for mod_name, is_view_module in possible_modules:
            try:
                module = importlib.import_module(mod_name)
                is_view = is_view_module
                break
            except ImportError:
                continue
        
        if not module:
            return None
        
        # Busca case-insensitive pela classe da tabela
        # Primeiro tenta __all__ se existir
        if hasattr(module, '__all__'):
            for name in module.__all__:
                if name.upper() == table_upper:
                    try:
                        cls = getattr(module, name)
                        self._class_cache[table_upper] = cls
                        self._is_view_cache[table_upper] = is_view
                        return cls
                    except AttributeError:
                        continue
        
        # Fallback: busca em dir(module)
        for name in dir(module):
            if name.upper() == table_upper:
                cls = getattr(module, name)
                self._class_cache[table_upper] = cls
                self._is_view_cache[table_upper] = is_view
                return cls
            
        return None
    
    def _get_table_class(self):
        """
        Wrapper para compatibilidade - retorna classe baseada em current_table.
        """
        if not self.current_table or not self.current_table.source_name:
            return None
        
        return self._get_table_class_by_name(self.current_table.source_name)
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 27/02/2026 '''
    def _should_print_logs(self) -> bool:
        """
        Verifica se devemos imprimir logs de inicialização.
        Evita duplicação quando Flask está em modo debug (reloader).
        
        Returns:
            True se devemos imprimir, False caso contrário
        """
        # Se WERKZEUG_RUN_MAIN não existe, estamos fora do Flask ou em produção
        # Neste caso, sempre imprimimos
        werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN')
        if werkzeug_main is None:
            return True
        
        # Se WERKZEUG_RUN_MAIN == 'true', estamos no processo recarregado
        # Este é o processo que realmente executa a aplicação
        return werkzeug_main == 'true'
    
    def _register_routes(self):
        """
        Registra automaticamente todas as rotas Flask para as tabelas descobertas.
        """
        if not self.app:
            return
        
        suffix = self.config.get('url_suffix', 'manager').strip('/')
        tables = self._discover_tables()
        
        if not tables:
            return
        
        total_routes = 0
        
        # Registra rota de múltiplas tabelas: GET /manager?tbls=Products,Categories
        @self.app.route(f"/{suffix}", methods=['GET'], endpoint="multi_table_get")
        def multi_get():
            query_params = request.args.to_dict(flat=False)  # Preserva múltiplos valores
            # Converte para dict simples se necessário
            params_dict = {}
            for k, v in query_params.items():
                params_dict[k] = v[0] if len(v) == 1 else v
            
            result = self.handle_multi_get(params_dict)
            status = result.pop('status', 200)
            return jsonify(result), status
        
        total_routes += 1
        
        for table_name in tables:
            table_upper = table_name.upper()
            table_config = self._tables_config.get(table_upper, {})
            
            # Views: apenas GET permitido
            is_view = self._is_view_cache.get(table_upper, False)
            if is_view:
                allowed_methods = ["GET"]
            else:
                allowed_methods = table_config.get('allowed_methods', ["GET", "POST", "PATCH", "DELETE"])
            
            # Cria closures para cada tabela (evita problema de binding tardio)
            routes_count = self._register_table_routes(table_name, allowed_methods, suffix)
            total_routes += routes_count
        
        # Imprime apenas no processo recarregado do Flask (evita duplicação)
        if self._should_print_logs():
            print(f"{SystemController.custom_text('[AutoRouter]', 'green')} {total_routes} rotas registradas (/{suffix}/)")
    
    def _register_table_routes(self, table_name: str, allowed_methods: List[str], suffix: str) -> int:
        """
        Registra rotas Flask para uma tabela específica.
        Retorna o número de rotas criadas.
        """
        routes_created = 0
        # Rota para lista/criação: /{suffix}/{table}
        base_route = f"/{suffix}/{table_name}"
        list_methods = [m for m in ['GET', 'POST'] if m in allowed_methods]
        
        if list_methods:
            @self.app.route(base_route, methods=list_methods, endpoint=f"{table_name}_list")
            def table_list():
                method = request.method
                query_params = request.args.to_dict()
                body = request.get_json() if request.is_json else {}
                
                result = self.handle_request(
                    method=method,
                    table_name=table_name,
                    path_parts=[],
                    query_params=query_params,
                    body=body
                )
                
                status = result.pop('status', 200)
                return jsonify(result), status
            
            routes_created += len(list_methods)
        
        # Rota para operações com ID: /{suffix}/{table}/{id}
        detail_route = f"{base_route}/<path:resource_path>"
        detail_methods = [m for m in ['GET', 'PATCH', 'DELETE'] if m in allowed_methods]
        
        if detail_methods:
            @self.app.route(detail_route, methods=detail_methods, endpoint=f"{table_name}_detail")
            def table_detail(resource_path):
                method = request.method
                query_params = request.args.to_dict()
                body = request.get_json() if request.is_json else {}
                
                # Divide o path (pode ser ID ou rota customizada)
                path_parts = resource_path.split('/') if resource_path else []
                
                result = self.handle_request(
                    method=method,
                    table_name=table_name,
                    path_parts=path_parts,
                    query_params=query_params,
                    body=body
                )
                
                status = result.pop('status', 200)
                return jsonify(result), status
            
            routes_created += len(detail_methods)
        
        return routes_created
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 27/02/2026 '''

    def _get_field_map(self) -> Dict[str, str]:
        """
        Retorna um mapa {NOME_CAMPO_UPPER: NomeRealDoAtributo} para a tabela.
        Cacheado por nome da tabela.
        """
        t_name = self.current_table.source_name.upper()
        if t_name in self._field_map_cache:
            return self._field_map_cache[t_name]
        
        field_map = {}
        # Atributos internos a ignorar
        ignore = {
            'db', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 
            'isUpdate', 'controller', 'select', 'insert', 'update', 'delete',
            'insert_recordset', 'update_recordset', 'delete_from', 'field',
            'exists', 'validate_fields', 'validate_write', 'clear', 'set_current',
            'get_table_columns', 'get_table_index', 'get_table_foreign_keys', 'get_table_total',

            'SelectForUpdate', 'get_columns_with_defaults'
        }
        
        # Inspeciona a instância para encontrar campos válidos (EDTs/Enums/Values)
        for attr, val in self.current_table.__dict__.items():
            if attr.startswith('_') or attr in ignore:
                continue
            
            try:
                if callable(val): continue
                field_map[attr.upper()] = attr
            except:
                pass
        
        self._field_map_cache[t_name] = field_map
        return field_map

    def _evaluate_condition(self, condition_str: str):
        """
        Avalia uma string de condição (ex: 'ACTIVE == 1') no contexto da tabela.
        Retorna um FieldCondition ou BinaryExpression.
        """
        context = {}
        field_map = self._get_field_map()
        for real_name in field_map.values():
            context[real_name] = getattr(self.current_table, real_name)
        
        try:
            return eval(condition_str, {"__builtins__": {}}, context)
        except Exception as e:
            raise ValueError(f"Invalid condition syntax: {str(e)}")

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    @_pre_handle
    def handle_request(self, method: str, table_name: str, path_parts: List[str] = [], 
                       query_params: Dict[str, Any] = {}, body: Dict[str, Any] = {}, 
                       _table: TableController = None, _table_config: Dict = None) -> Dict[str, Any]:
        """
        Processa a requisição dinâmica e retorna o resultado padronizado.
        
        Args:
            method (str): Método HTTP (GET, POST, PATCH, DELETE)
            table_name (str): Nome da tabela alvo
            path_parts (List[str]): Segmentos da URL após a tabela (ex: ['1'] ou ['active'])
            query_params (Dict): Parâmetros de query string (filtros, paginação)
            body (Dict): Corpo da requisição (JSON)
            _table (TableController): Injetado pelo decorator _pre_handle
            _table_config (Dict): Injetado pelo decorator _pre_handle
            
        Returns:
            Dict: {status: int, data: Any, error: str, meta: Dict}
        """
        table        = _table
        table_config = _table_config if _table_config else {}
        
        try:
            match method.upper():
                case "GET":            
                    return self._handle_get(table, path_parts, query_params, table_config)
                case "POST":
                    return self._handle_post(table, body)
                case "PATCH":
                    if not path_parts:
                        return {"status": 400, "error": "Missing ID for PATCH"}
                
                    return self._handle_patch(table, path_parts[0], body)
                case "DELETE":

                    if not path_parts:
                        return {"status": 400, "error": "Missing ID for DELETE"}
                
                    return self._handle_delete(table, path_parts[0], table_config)
                case _:
                    return {"status": 405, "error": "Method not supported"}
        except Exception as e:                        
            print(f"{SystemController.custom_text("HANDLE_REQUEST", 'red')}\n{e}")
            traceback.print_exc()
            return {"status": 500, "error": f"Internal Server Error: {str(e)}"}
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
    def _get_relation_names(self, table: TableController) -> List[str]:
        """Retorna lista de nomes de relations se a tabela tiver relations definidas"""
        if hasattr(table, 'relations') and table.relations:
            return list(table.relations.keys())
        return []
    
    def _get_table_total(self, table: TableController, where_condition=None) -> int:
        """Retorna o total de registros na tabela (com ou sem filtro)"""
        try:
            # Cache apenas para totais SEM filtro (mais comum)
            if where_condition is None:
                table_name = table.source_name
                cache_ttl = 60  # 60 segundos de cache
                
                # Verifica cache
                if table_name in self._table_count_cache:
                    cached_time, cached_count = self._table_count_cache[table_name]
                    if time.time() - cached_time < cache_ttl:
                        return cached_count
                
                # Calcula e cacheia
                total = table.get_table_total()
                self._table_count_cache[table_name] = (time.time(), total)
                return total
            else:
                # Com filtro: sempre recalcula
                from ..controller.managers import Select_Manager
                select = Select_Manager.SelectQuery(table)
                select.where(where_condition)
                query = select._build_count_query()
                result = table.db.execute(query)
                return result[0][0] if result else 0
        except:
            return 0
        
    def _handle_get(self, table: TableController, path_parts: List[str], params: Dict, config: Dict):        
        try:
            # Debug timing (remover depois)
            import time as time_module
            start_time = time_module.time()
            
            field_map = self._get_field_map()
            relation_names = self._get_relation_names(table)
            
            # Verifica se deve incluir relations (opt-in para performance)
            include_relations = params.get('include_relations', '').lower() in ('true', '1', 'yes')
            
            print(f"[DEBUG] Field map took: {time_module.time() - start_time:.3f}s")

            # Rota: GET /{table}/{id}
            if path_parts and path_parts[0].isdigit():                                
                recid = int(path_parts[0])
                if table.exists(table.RECID == recid):
                    select_query = table.select().where(table.RECID == recid)
                    
                    # Adiciona relations APENAS se requisitado
                    if include_relations and relation_names:
                        select_query.with_relations(*relation_names)
                    
                    select_query.execute()

                    if table.records:
                        return {"status": 200, "data": self._serialize(table.records[0], field_map)}
                        
                return {"status": 404, "error": "Record not found"}
            
        except Exception as e:
            print(f"{SystemController.custom_text("HANDLE_GET", 'red')}\n{e}")
            traceback.print_exc()            
            raise    

        # Rota: GET /{table}/{custom_route}
        if path_parts:
            route_name = path_parts[0]
            custom_routes = config.get('custom_get', [])
            for route in custom_routes:
                if route.get('route') == route_name:
                    try:
                        condition = self._evaluate_condition(route.get('where', '1==1'))

                        select_query = table.select().where(condition)
                        
                        if 'columns' in route:
                            cols = [getattr(table, c) for c in route['columns'] if hasattr(table, c)]
                            select_query.columns(cols)
                        
                        # Adiciona relations APENAS se requisitado
                        if include_relations and relation_names:
                            select_query.with_relations(*relation_names)
                        
                        select_query.execute()

                        data = [self._serialize(r, field_map) for r in table.records]
                        return {"status": 200, "data": data, "meta": {"count": len(data)}}                    
                    except Exception as e:
                        return {"status": 500, "error": f"Custom route error: {str(e)}"}
            return {"status": 404, "error": f"Custom route '{route_name}' not found"}

        # Rota: GET /{table} (Listagem com filtros)
        try:
            page  = int(params.get('page', 1))
            limit = int(params.get('limit', 20))
        except ValueError:
            return {"status": 400, "error": "Invalid pagination parameters"}

        offset = (page - 1) * limit
        where_condition = None
        
        if params and len(params) > 0 and any(k not in ('page', 'limit') for k in params):
            for key, value in params.items():
                if key in ('page', 'limit'):
                    continue
            
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
                field_attr = table.field(real_field_name)
                
                # Aplica operador específico
                match operator:
                    case 'eq':   where_condition = (field_attr == value)
                    case 'gt':   where_condition = (field_attr > value)
                    case 'gte':  where_condition = (field_attr >= value)
                    case 'lt':   where_condition = (field_attr < value)
                    case 'lte':  where_condition = (field_attr <= value)
                    case 'neq':  where_condition = (field_attr != value)
                    case 'like': where_condition = field_attr.like(str(value))
                
                # Monta query com ordem CORRETA: select -> where -> relations -> limit/offset
                select_query = table.select().where(where_condition)
                
                # Relations APENAS se requisitado (performance!)
                if include_relations and relation_names:
                    select_query = select_query.with_relations(*relation_names)
                
                select_query = select_query.limit(limit).offset(offset)
                select_query.execute()
                print(f"[DEBUG] Query execution (with filter) took: {time_module.time() - start_time:.3f}s")
        else:
            # Monta query com ordem CORRETA: select -> relations -> limit/offset
            query_start = time_module.time()
            select_query = table.select()
            
            # Relations APENAS se requisitado (performance!)
            if include_relations and relation_names:
                select_query = select_query.with_relations(*relation_names)
            
            select_query = select_query.limit(limit).offset(offset)
            select_query.execute()
            print(f"[DEBUG] Query execution (no filter) took: {time_module.time() - query_start:.3f}s")

        # SLICE DEFENSIVO: garante que NUNCA retorna mais que o limit
        serialize_start = time_module.time()
        records_to_serialize = table.records[:limit] if len(table.records) > limit else table.records
        data = [self._serialize(r, field_map) for r in records_to_serialize]
        print(f"[DEBUG] Serialization took: {time_module.time() - serialize_start:.3f}s")
        
        # Total é DESABILITADO por padrão (performance em tabelas grandes!)
        # Use ?include_total=true se precisar do count total
        if params.get('include_total', '').lower() in ('true', '1', 'yes'):
            count_start = time_module.time()
            total = self._get_table_total(table, where_condition)
            print(f"[DEBUG] Count query took: {time_module.time() - count_start:.3f}s")
            meta = {"page": page, "limit": limit, "count": len(data), "total": total}
        else:
            meta = {"page": page, "limit": limit, "count": len(data)}
        
        print(f"[DEBUG] TOTAL request took: {time_module.time() - start_time:.3f}s")
        return {
            "status": 200, 
            "data": data,
            "meta": meta
        }
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #5 / made by: Nicolas Santos / created: 09/03/2026 '''
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 12/03/2026 '''
    def handle_multi_get(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna múltiplas tabelas de uma só vez.
        Rota: GET /manager?tbls=Products,Categories&limit=10
        
        Args:
            query_params: {'tbls': 'Products,Categories', 'limit': '10'}
            
        Returns:
            Dict com formato: {
                'status': 200,
                'data': {
                    'Products': [...],
                    'Categories': [...]
                },
                'meta': {'tables_count': 2}
            }
        """
        if not self.enabled:
            return {"status": 404, "error": "AutoRouter is disabled"}
        
        # Extrai lista de tabelas
        tbls_param = query_params.get('tbls', '')
        if not tbls_param:
            return {"status": 400, "error": "Missing 'tbls' parameter"}
        
        # Suporta tanto ?tbls=usr&tbls=sup quanto ?tbls=usr,sup
        table_names = []
        if isinstance(tbls_param, list):
            for t in tbls_param:
                table_names.extend([x.strip() for x in str(t).split(',') if x.strip()])
        else:
            table_names = [x.strip() for x in str(tbls_param).split(',') if x.strip()]
        
        if not table_names:
            return {"status": 400, "error": "No valid table names provided"}
        
        # Limites globais
        try:
            limit = int(query_params.get('limit', 50))  # Default menor para múltiplas tabelas
        except ValueError:
            limit = 50
        
        results = {}
        errors = {}
        
        for table_name in table_names:
            try:
                # Verifica se tabela existe e não está excluída
                table_upper = table_name.upper()
                if table_upper in self._exclude_tables:
                    errors[table_name] = "Access restricted"
                    continue
                
                TableClass = self._get_table_class_by_name(table_name)
                if not TableClass:
                    errors[table_name] = "Table not found"
                    continue
                
                # Instancia e executa select
                table = TableClass(self.db)
                select_query = table.select()
                select_query = select_query.limit(limit)
                select_query.execute()
                
                # Serializa usando field map (COM SLICE DEFENSIVO)
                temp_table = self.current_table
                self.current_table = table
                field_map = self._get_field_map()
                
                records_to_serialize = table.records[:limit] if len(table.records) > limit else table.records
                results[table_name] = [self._serialize_simple(r, field_map) for r in records_to_serialize]
                self.current_table = temp_table
                
            except Exception as e:
                errors[table_name] = str(e)
        
        response = {
            "status": 200 if results else 404,
            "data": results,
            "meta": {"tables_count": len(results), "limit_per_table": limit}
        }
        
        if errors:
            response["errors"] = errors
        
        return response
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 12/03/2026 '''

    def _handle_post(self, table: TableController, body: Dict):
        field_map = self._get_field_map()
        
        try:
            for key, value in body.items():
                real_field_name = field_map.get(key.upper())
                if real_field_name:
                    setattr(table, real_field_name, value)
        except Exception as e:
            return {"status": 400, "error": str(e)}
        
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
            field_map = self._get_field_map()
            valid_fields = {}
            
            for key, value in body.items():
                real_field_name = field_map.get(key.upper())
                if real_field_name and real_field_name != 'RECID':
                    # Valida o valor usando o setter do EDTController (lança erro se inválido)
                    setattr(table, real_field_name, value)
                    valid_fields[real_field_name] = value
            
            if not valid_fields:
                return {"status": 400, "error": "No valid fields provided for update"}
            
            affected = table.update_recordset(where=(table.RECID == recid), **valid_fields)
            
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
                        condition = self._evaluate_condition(route.get('where', '0==1'))
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
                table.update_recordset(where=(table.RECID == recid), **{field: value})
            else:
                table.delete_from().where(table.RECID == recid).execute()
            
            return {"status": 200, "message": "Deleted successfully"}
        except Exception as e:
            return {"status": 500, "error": str(e)}

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #5 / made by: Nicolas Santos / created: 09/03/2026 '''
    def _serialize(self, record_obj, field_map: Dict[str, str], max_relations: int = 100) -> Dict:
        """
        Serializa uma instância de TableController para dict usando mapa de campos.
        Inclui automaticamente relations se houver (COM LIMITE).
        
        Args:
            max_relations: Máximo de records de relations a incluir (evita sobrecarga)
        """
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
        
        # Serializa relations automaticamente se houver (COM LIMITE!)
        if hasattr(self.current_table, 'relations') and self.current_table.relations:
            relations_data = {}
            for rel_name, relation_manager in self.current_table.relations.items():
                # Pega os records da relation
                if hasattr(relation_manager, 'records') and relation_manager.records:
                    # Pega o field_map da tabela relacionada
                    rel_instance = relation_manager.get_instance()
                    rel_field_map = {}
                    
                    ignore = {
                        'db', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 
                        'isUpdate', 'controller', 'select', 'insert', 'update', 'delete',
                        'insert_recordset', 'update_recordset', 'delete_from', 'field',
                        'exists', 'validate_fields', 'validate_write', 'clear', 'set_current',
                        'get_table_columns', 'get_table_index', 'get_table_foreign_keys', 'get_table_total',
                        'SelectForUpdate', 'get_columns_with_defaults', 'relations'
                    }
                    
                    for attr, val in rel_instance.__dict__.items():
                        if attr not in ignore and not attr.startswith('_') and not callable(val):
                            rel_field_map[attr.upper()] = attr
                    
                    # LIMITA relations para não explodir o response!
                    limited_records = relation_manager.records[:max_relations]
                    relations_data[rel_name] = [
                        self._serialize_simple(rec, rel_field_map) 
                        for rec in limited_records
                    ]
                    
                    # Indica se houve truncamento
                    if len(relation_manager.records) > max_relations:
                        relations_data[f"{rel_name}_truncated"] = True
                        relations_data[f"{rel_name}_total"] = len(relation_manager.records)
            
            if relations_data:
                data['relations'] = relations_data
        
        return data
    
    def _serialize_simple(self, record_obj, field_map: Dict[str, str]) -> Dict:
        """Serializa um record simples sem processar relations recursivamente"""
        if isinstance(record_obj, dict):
            return record_obj
            
        data = {}
        for real_name in field_map.values():
            try:
                val = getattr(record_obj, real_name)
                if callable(val): continue
                data[real_name] = val
            except:
                pass
        return data
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #5 / made by: Nicolas Santos / created: 09/03/2026 '''

    def _discover_tables(self) -> List[str]:
        """
        Descobre todas as tabelas disponíveis no TablePack para geração de documentação.
        """
        tables = set()  # Usa set para evitar duplicatas
        # Tenta diferentes estruturas de projeto (Tables e Views)
        possible_modules = [
            ("model.TablePack", False),      # Estrutura padrão SQLManager
            ("src.model.TablePack", False),  # Estrutura com src/
            ("model.tables", False),         # TablePack via import as
            ("src.model.tables", False),     # src/ + tables
            ("model.ViewPack", True),        # ViewPack
            ("src.model.ViewPack", True),    # ViewPack com src/
            ("model.views", True),           # ViewPack via import as
            ("src.model.views", True),       # src/ + views
        ]
        
        # Busca em todos os módulos (Tables e Views)
        all_items = []
        found_modules = []
        
        for mod_name, is_view_module in possible_modules:
            try:
                module = importlib.import_module(mod_name)
                found_modules.append((module, mod_name, is_view_module))
            except ImportError:
                continue
        
        if not found_modules:
            if self._should_print_logs():
                print(f"{SystemController.custom_text('[AutoRouter]', 'yellow')} Nenhum módulo TablePack/ViewPack encontrado.")
            return []
        
        # Processa cada módulo encontrado
        excluded_count = 0
        total_count = 0
        
        for module, mod_name, is_view_module in found_modules:
            items_to_check = module.__all__ if hasattr(module, '__all__') else [n for n in dir(module) if not n.startswith('_')]
            
            for name in items_to_check:
                if name.startswith('_'):
                    continue
                if name.upper() in self._exclude_tables:
                    excluded_count += 1
                    continue
                
                try:
                    attr = getattr(module, name)
                    if isinstance(attr, type) and name not in tables:  # Evita duplicatas
                        tables.add(name)
                        total_count += 1
                        # Armazena no cache se é view (prioriza ViewPack se houver duplicata)
                        if is_view_module or name.upper() not in self._is_view_cache:
                            self._is_view_cache[name.upper()] = is_view_module
                except AttributeError:
                    continue
        
        if not tables:
            if self._should_print_logs():
                print(f"{SystemController.custom_text('[AutoRouter]', 'yellow')} Nenhuma tabela/view encontrada.")
        else:
            if self._should_print_logs():
                msg = f"{total_count} tabela(s)/view(s) descoberta(s)"
                if excluded_count > 0:
                    msg += f" ({excluded_count} excluída(s))"
                print(f"{SystemController.custom_text('[AutoRouter]', 'green')} {msg}")
        
        return sorted(list(tables))  # Converte set para lista ordenada
    
    def get_registered_routes(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Retorna informações sobre todas as rotas registradas.
        
        Returns:
            Dict com formato: {
                'table_name': [
                    {'method': 'GET', 'endpoint': '/manager/table_name'},
                    {'method': 'POST', 'endpoint': '/manager/table_name'},
                    ...
                ]
            }
        """
        if not self.enabled:
            return {}
        
        suffix = self.config.get('url_suffix', 'manager').strip('/')
        tables = self._discover_tables()
        routes_info = {}
        
        for table_name in tables:
            table_upper = table_name.upper()
            table_config = self._tables_config.get(table_upper, {})
            
            # Views: apenas GET permitido
            is_view = self._is_view_cache.get(table_upper, False)
            if is_view:
                allowed_methods = ["GET"]
            else:
                allowed_methods = table_config.get('allowed_methods', ["GET", "POST", "PATCH", "DELETE"])
            
            routes = []
            base_endpoint = f"/{suffix}/{table_name}"
            
            if "GET" in allowed_methods:
                routes.append({"method": "GET", "endpoint": base_endpoint, "description": f"Listar {table_name}"})
                routes.append({"method": "GET", "endpoint": f"{base_endpoint}/{{id}}", "description": f"Obter {table_name} por ID"})
            
            if "POST" in allowed_methods:
                routes.append({"method": "POST", "endpoint": base_endpoint, "description": f"Criar {table_name}"})
            
            if "PATCH" in allowed_methods:
                routes.append({"method": "PATCH", "endpoint": f"{base_endpoint}/{{id}}", "description": f"Atualizar {table_name}"})
            
            if "DELETE" in allowed_methods:
                routes.append({"method": "DELETE", "endpoint": f"{base_endpoint}/{{id}}", "description": f"Deletar {table_name}"})
            
            # Rotas customizadas GET
            for custom_route in table_config.get('custom_get', []):
                route_name = custom_route.get('route')
                routes.append({
                    "method": "GET", 
                    "endpoint": f"{base_endpoint}/{route_name}", 
                    "description": f"Rota customizada: {route_name}"
                })
            
            # Rotas customizadas DELETE
            for custom_route in table_config.get('custom_delete', []):
                route_name = custom_route.get('route')
                routes.append({
                    "method": "DELETE", 
                    "endpoint": f"{base_endpoint}/{route_name}", 
                    "description": f"Rota customizada: {route_name}"
                })
            
            routes_info[table_name] = routes
        
        return routes_info

    def generate_collection(self, base_url: str = "http://localhost:5000", collection_name: str = "SQLManager_API") -> Dict[str, Any]:
        """
        Gera uma coleção do Postman (v2.1) com todas as rotas disponíveis.
        
        Args:
            base_url: URL base da API (ex: http://localhost:5000)
            collection_name: Nome da coleção
            
        Returns:
            Dict: JSON da coleção Postman
        """
        # Define o sufixo (padrão 'manager' se não configurado)
        suffix = self.config.get('url_suffix', 'manager')
        suffix = suffix.strip('/')
        
        # Prepara partes da URL
        host_parts = base_url.replace("http://", "").replace("https://", "").split(":")
        host = host_parts[0]
        port = host_parts[1] if len(host_parts) > 1 else ""
        
        path_prefix = suffix.split('/') if suffix else []
        full_base = f"{base_url}/{suffix}" if suffix else base_url

        item_list = []
        tables = self._discover_tables()
        
        for table_name in tables:
            table_upper = table_name.upper()
            table_config = self._tables_config.get(table_upper, {})
            
            # Views: apenas GET permitido
            is_view = self._is_view_cache.get(table_upper, False)
            if is_view:
                allowed = ["GET"]
            else:
                allowed = table_config.get('allowed_methods', ["GET", "POST", "PATCH", "DELETE"])
            
            table_items = []
            
            # Helper para criar objeto URL do Postman
            def make_url(path_segments, query=None):
                u = {
                    "raw": f"{full_base}/{'/'.join(path_segments)}" + (f"?{query}" if query else ""),
                    "protocol": "http",
                    "host": host.split('.'),
                    "path": path_prefix + path_segments
                }

                if port: 
                    u["port"] = port

                if query:
                    q_list = []
                    for pair in query.split('&'):
                        k, v = pair.split('=')
                        q_list.append({"key": k, "value": v})
                    u["query"] = q_list
                return u

            # Adiciona requisições para cada método permitido
            if "GET" in allowed:
                table_items.append({
                    "name": f"List {table_name}",
                    "request": {
                        "method": "GET", 
                        "header": [], 
                        "url": make_url([table_name], "page=1&limit=10")
                    }
                })
                table_items.append({
                    "name": f"Get {table_name} by ID",
                    "request": {
                        "method": "GET", 
                        "header": [], 
                        "url": make_url([table_name, "1"])
                    }
                })
                
                # Adiciona rotas customizadas GET
                for custom_route in table_config.get('custom_get', []):
                    route_name = custom_route.get('route')
                    table_items.append({
                        "name": f"Get {table_name} - {route_name}",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": make_url([table_name, route_name])
                        }
                    })
            
            if "POST" in allowed:
                table_items.append({
                    "name": f"Create {table_name}",
                    "request": {
                        "method": "POST", 
                        "header": [{"key": "Content-Type", "value": "application/json"}], 
                        "body": {
                            "mode": "raw", 
                            "raw": json.dumps({"FIELD": "VALUE"}, indent=4)
                        }, 
                        "url": make_url([table_name])
                    }
                })
            
            if "PATCH" in allowed:
                table_items.append({
                    "name": f"Update {table_name}",
                    "request": {
                        "method": "PATCH", 
                        "header": [{"key": "Content-Type", "value": "application/json"}], 
                        "body": {
                            "mode": "raw", 
                            "raw": json.dumps({"FIELD": "NEW_VALUE"}, indent=4)
                        }, 
                        "url": make_url([table_name, "1"])
                    }
                })
            
            if "DELETE" in allowed:
                table_items.append({
                    "name": f"Delete {table_name}",
                    "request": {
                        "method": "DELETE", 
                        "header": [], 
                        "url": make_url([table_name, "1"])
                    }
                })
                
                # Adiciona rotas customizadas DELETE
                for custom_route in table_config.get('custom_delete', []):
                    route_name = custom_route.get('route')
                    table_items.append({
                        "name": f"Delete {table_name} - {route_name}",
                        "request": {
                            "method": "DELETE",
                            "header": [],
                            "url": make_url([table_name, route_name])
                        }
                    })
            
            if table_items:
                item_list.append({"name": table_name, "item": table_items})

        collection = {
            "info": {
                "name": collection_name,
                "_postman_id": "auto-generated",
                "description": "Auto-generated API collection from SQLManager AutoRouter",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": item_list
        }
        
        return collection
''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Matheus / created: 25/02/2026 ''' 