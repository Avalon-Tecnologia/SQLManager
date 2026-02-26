''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''
import weakref
import sys

from typing import Any, List, Dict, Optional, Union, TYPE_CHECKING

from ..BaseEnumController  import BaseEnumController
from ..EDTController       import EDTController

from ._conditions_Managers import FieldCondition, BinaryExpression

if TYPE_CHECKING:
    from ..TableController import TableController
    from ..ViewController  import ViewController

class AutoExecuteWrapper:
    '''Wrapper que delega métodos para SelectManager mas auto-executa quando não há mais encadeamento'''
    
    _pending_executions = []  # Lista de wrappers pendentes de execução
    
    def __init__(self, select_manager):
        self._select_manager = select_manager
        self._executed       = False
        self._result_cache   = None
        self._finalized      = False
        
        # Registra para execução automática no próximo ciclo
        AutoExecuteWrapper._pending_executions.append(weakref.ref(self, self._cleanup_callback))
    
    @staticmethod
    def _cleanup_callback(ref):
        """Callback chamado quando o wrapper é garbage collected"""
        pass
    
    @staticmethod
    def _execute_pending():
        """Executa todos os wrappers pendentes"""
        while AutoExecuteWrapper._pending_executions:
            ref     = AutoExecuteWrapper._pending_executions.pop(0)
            wrapper = ref()
            if wrapper and not wrapper._executed:
                try:
                    wrapper._select_manager.execute()
                    wrapper._executed = True
                except:
                    pass
    
    def __del__(self):
        """Auto-executa quando não há mais referência ao wrapper"""
        # DESABILITADO: Execução em __del__ causa problemas com GC durante construção da cadeia
        # Use .execute() explícito ou acesse métodos mágicos (__len__, __bool__, etc)
        pass
    
    def _finalize(self):
        """Finaliza e executa se necessário (chamado apenas em contextos seguros)"""
        if not self._finalized:
            self._finalized = True
            if not self._executed and not self._select_manager._executed:
                try:
                    self._select_manager.execute()
                    self._executed = True
                except:
                    pass
    
    def __getattr__(self, name):
        """Delega todos os métodos para o SelectManager"""
        attr = getattr(self._select_manager, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                if result is self._select_manager:
                    return self  # Retorna o próprio wrapper para manter o encadeamento
                return result
            return wrapper
        return attr
    
    def _ensure_executed(self):
        """Garante que a query foi executada e retorna o resultado"""
        if not self._executed:
            self._result_cache = self._select_manager.execute()
            self._executed     = True
        return self._result_cache
    
    def execute(self):
        """Executa explicitamente e retorna o controller para acesso aos campos"""
        self._ensure_executed()
        return self._select_manager._controller
    
    def __len__(self):
        """Permite usar len() - auto-executa se necessário"""
        return len(self._ensure_executed())
    
    def __bool__(self):
        """Permite usar em contextos booleanos - auto-executa se necessário"""
        return bool(self._ensure_executed())
    
    def __iter__(self):
        """Permite iterar - auto-executa se necessário"""
        return iter(self._ensure_executed())
    
    def __getitem__(self, index):
        """Permite acesso por índice - auto-executa se necessário"""
        return self._ensure_executed()[index]

class SelectManager:
    '''Gerencia operações SELECT com API fluente - Auto-executa quando a cadeia termina'''
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
    def __init__(self, ref_controller: Union['TableController', 'ViewController']):
        self._controller = ref_controller        

        self._where_conditions:  Optional[Union[FieldCondition, BinaryExpression]]  = None
        self._columns:           Optional[List[str]]                                = None
        self._joins:             List[Dict[str, Any]]                               = []
        self._order_by:          Optional[str]                                      = None
        self._limit:             Optional[int]                                      = None
        self._offset:            Optional[int]                                      = None
        self._group_by:          Optional[List[str]]                                = None
        self._having_conditions: Optional[List[Dict[str, Any]]]                     = None
        self._distinct:          bool                                               = False
        self._do_update:         bool                                               = True
        self._executed                                                              = False
        self._last_results                                                          = []        

    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''

    @staticmethod
    def _extract_field_name(field: Union[str, EDTController, 'BaseEnumController']) -> str:
        '''Extrai o nome do campo de um EDT/Enum ou retorna a string'''
        if isinstance(field, (EDTController, BaseEnumController)):
            return field._get_field_name()
        # Se vier como string já, retorna direto
        return str(field)

    def __get__(self, instance, owner=None):
        self._controller = instance
        self._executed   = False
        return self

    def _should_auto_execute(self):
        """Verifica se deve executar automaticamente baseado no contexto de chamada"""
        try:
            frame = sys._getframe(2)  
            import dis
            code = frame.f_code
            return True
        except:
            return True

    def __iter__(self):
        """Permite iterar sobre os resultados"""
        return iter(self.execute())
    
    def __len__(self):
        """Retorna o total de resultados"""
        return len(self.execute())
    
    def __getitem__(self, index):
        """Permite acesso por índice"""
        return self.execute()[index]

    def where(self, condition: Union[FieldCondition, BinaryExpression]) -> 'SelectManager':
        '''Adiciona condições WHERE e permite encadeamento'''
        self._where_conditions = condition
        return self
    
    def columns(self, *cols: Union[str, EDTController, 'BaseEnumController']) -> 'SelectManager':
        '''Define as colunas a serem retornadas - Aceita campos EDT/Enum ou strings'''
        extracted_cols = []
        for col in cols:
            if isinstance(col, (EDTController, BaseEnumController)):
                extracted_cols.append(self._extract_field_name(col))
            else:
                extracted_cols.append(str(col))
        self._columns = extracted_cols
        return self
    
    def join(self, other_table, join_type: str = 'INNER') -> 'JoinBuilder':
        '''Inicia um JOIN com outra tabela'''
        return JoinBuilder(self, other_table, join_type)
    
    def order_by(self, column: Union[str, EDTController, 'BaseEnumController']) -> 'SelectManager':
        '''Define ordenação - Aceita campo ou string'''
        self._order_by = self._extract_field_name(column)
        return self
    
    def limit(self, count: int) -> 'SelectManager':
        '''Define limite de registros'''
        self._limit = count
        return self
    
    def offset(self, count: int) -> 'SelectManager':
        '''Define offset'''
        self._offset = count
        return self
    
    def group_by(self, *columns: Union[str, EDTController, 'BaseEnumController']) -> 'SelectManager':
        '''Define GROUP BY - Aceita campos ou strings'''
        self._group_by = [self._extract_field_name(col) for col in columns]
        return self
    
    def having(self, conditions: List[Dict[str, Any]]) -> 'SelectManager':
        '''Define HAVING para usar com GROUP BY'''
        self._having_conditions = conditions
        return self
    
    def distinct(self) -> 'SelectManager':
        '''Adiciona DISTINCT'''
        self._distinct = True
        return self
    
    def do_update(self, update: bool = True) -> 'SelectManager':
        '''Define se deve atualizar a instância com o resultado'''
        self._do_update = update
        return self
    
    def execute(self):
        """Executa a query SELECT e atualiza a instância automaticamente - Retorna o controller"""
        if self._executed:
            return self._controller
        
        self._executed = True

        validate = self._controller.validate_fields()

        if not validate['valid']:
            raise Exception(validate['error'])
        
        columns = self._columns or ['*']
        limit   = self._limit or 100
        offset  = self._offset or 0        
        
        table_columns  = self._controller.get_table_columns()
        has_aggregates = any(self._controller._is_aggregate_function(col) for col in columns) if columns != ['*'] else False
        
        if columns != ['*']:
            col_names = [col[0] for col in table_columns]
            for col in columns:
                if self._controller._is_aggregate_function(col):
                    field_name = self._controller._extract_field_from_aggregate(col)
                    if field_name and field_name not in col_names:
                        raise Exception(f"Campo '{field_name}' na agregação '{col}' não existe na tabela")
                elif col not in col_names:
                    raise Exception(f"Coluna inválida: {col}")                

        ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
        main_alias = self._controller.source_name
        ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''        

        select_columns = []        
        
        if columns == ['*']:            
            select_columns += [f"{main_alias}.{col[0]} AS {main_alias}_{col[0]}" for col in table_columns]
        else:
            for col in columns:
                if self._controller._is_aggregate_function(col):
                    alias_name = col.replace('(', '_').replace(')', '').replace('*', 'ALL').replace('.', '_').replace(' ', '')
                    select_columns.append(f"{col} AS {alias_name}")
                else:
                    select_columns.append(f"{main_alias}.{col} AS {main_alias}_{col}")                

        join_clauses     = []
        join_controllers = []        

        for join in self._joins:
            ctrl       = join['controller']
            alias      = join['alias']
            join_type  = join['type']
            join_on    = join['on']
            index_hint = join.get('index_hint')
            
            join_columns = ctrl.get_table_columns()
            join_controllers.append((ctrl, alias))
            
            if join['columns']:
                select_columns += [f"{alias}.{col} AS {alias}_{col}" for col in join['columns']]
            else:
                select_columns += [f"{alias}.{col[0]} AS {alias}_{col[0]}" for col in join_columns]
            
            ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
            hint = f" WITH (INDEX({index_hint}))" if index_hint else ""
            join_clauses.append(f" {join_type} JOIN {ctrl.source_name} AS {alias}{hint} ON {join_on} ")
            ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
                
        distinct_keyword = "DISTINCT " if self._distinct else ""

        ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''
        query = f"SELECT {distinct_keyword}{', '.join(select_columns)} FROM {self._controller.source_name} AS {main_alias}" + ''.join(join_clauses)
        ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 25/02/2026 '''

        values = []        
        
        if self._where_conditions or self._where_conditions is not None:
            where_sql, where_values = self._where_conditions.to_sql()
            query += f" WHERE {where_sql}"
            values.extend(where_values if isinstance(where_values, list) else [where_values])
        
        if self._group_by or self._group_by is not None:
            group_clauses = [f"{main_alias}.{field}" for field in self._group_by]
            query += " GROUP BY " + ", ".join(group_clauses)
        
        if self._having_conditions or self._having_conditions is not None:
            having_clauses = []

            for h in self._having_conditions:
                operator = h.get('operator', '=')
                having_clauses.append(f"{h['field']} {operator} ?")
                values.append(h['value'])

            query += " HAVING " + " AND ".join(having_clauses)
        
        if self._order_by or self._order_by is not None:
            query += f" ORDER BY {main_alias}.{self._order_by}"
            query += f" OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
        
        # Executa a query usando o método apropriado do banco
        if hasattr(self._controller.db, 'doQuery'):
            rows = self._controller.db.doQuery(query, tuple(values))
        elif hasattr(self._controller.db, 'execute'):
            result = self._controller.db.execute(query, tuple(values))
            # Se retornar cursor, faz fetchall, senão assume que já é a lista
            rows = result.fetchall() if hasattr(result, 'fetchall') else result
        elif hasattr(self._controller.db, 'executeCommand'):
            cursor = self._controller.db.executeCommand(query, tuple(values))
            rows = cursor.fetchall() if cursor else []
        else:
            raise Exception(f"Objeto de conexão não possui método compatível (doQuery, execute ou executeCommand)")
        
        if has_aggregates or self._group_by or self._group_by is not None:
            results = self._process_aggregate_results(rows, columns, table_columns)
            join_records_map = None
        elif self._joins:
            ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
            results, join_records_map = self._process_join_results(rows, table_columns, join_controllers)
            ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
        else:
            results = self._process_simple_results(rows, table_columns)
            join_records_map = None
        
        # SEMPRE armazena results no SelectManager para que exists() possa acessar
        self._last_results = results        
        
        if self._do_update:
            if results:
                if self._joins:
                    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''                    
                    self._controller.records = [r[0] for r in results]
                    
                    # Popula os records de cada controller de JOIN
                    for join_idx, join_info in enumerate(self._joins):
                        join_ctrl         = join_info['controller']
                        join_ctrl.records = join_records_map[join_idx]                        

                        if join_ctrl.records:
                            join_ctrl.set_current(join_ctrl.records[0])
                                        
                    if self._controller.records:
                        self._controller.set_current(self._controller.records[0])
                    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
                else:                    
                    self._controller.records = results
                    if results and isinstance(results[0], dict):
                        self._controller.set_current(results[0])
            else:                
                self._controller.clear()
                self._controller.records = []                
                if self._joins:
                    for join_info in self._joins:
                        join_ctrl = join_info['controller']
                        join_ctrl.clear()
                        join_ctrl.records = []
        else:            
            self._controller.records = results
                
        if hasattr(self._controller, '_pending_wrapper'):
            self._controller._pending_wrapper = None
        
        return self._controller
    
    def _process_aggregate_results(self, rows, columns, table_columns):
        """Processa resultados com agregações"""
        column_mapping = []
        sql_idx        = 0
        
        if columns == ['*']:
            for col in table_columns:
                column_mapping.append((sql_idx, col[0], False))
                sql_idx += 1
        else:
            for col in columns:
                if self._controller._is_aggregate_function(col):
                    field_name = self._controller._extract_field_from_aggregate(col)
                    if field_name:
                        column_mapping.append((sql_idx, field_name, True))
                    else:
                        alias_name = col.replace('(', '_').replace(')', '').replace('*', 'ALL').replace('.', '_').replace(' ', '')
                        column_mapping.append((sql_idx, alias_name, True))
                    sql_idx += 1
                else:
                    column_mapping.append((sql_idx, col, False))
                    sql_idx += 1
        
        results = []
        for row in rows:
            main_instance    = self._controller.__class__(self._controller.db)
            aggregate_extras = {}
            
            for sql_idx, field_name, is_agg in column_mapping:
                value = row[sql_idx]
                if hasattr(main_instance, field_name):
                    getattr(main_instance, field_name).value = value
                else:
                    aggregate_extras[field_name] = value
            
            if aggregate_extras:
                main_instance._aggregate_results = aggregate_extras
            
            results.append(main_instance)
        
        return results
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def _process_join_results(self, rows, table_columns, join_controllers):
        """Processa resultados com JOINs - Retorna dados separados por controller"""
        results = []
                
        join_records_by_controller = {i: [] for i in range(len(join_controllers))}

        for row in rows:
            idx = 0
                        
            main_data = {}
            for col in table_columns:
                main_data[col[0]] = row[idx]
                idx += 1
                        
            row_data = [main_data]  
            
            for join_idx, (ctrl, alias) in enumerate(join_controllers):
                join_cols = ctrl.get_table_columns()
                join_data = {}

                for col in join_cols:
                    join_data[col[0]] = row[idx]
                    idx += 1
                
                row_data.append(join_data)
                join_records_by_controller[join_idx].append(join_data)
            
            results.append(row_data)
        
        # Retorna tanto os resultados quanto os registros separados
        return results, join_records_by_controller
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    
    def _process_simple_results(self, rows, table_columns):
        """Processa resultados simples sem JOINs"""
        result = [dict(zip([col[0] for col in table_columns], row)) for row in rows]
        return result

    def records(self) -> List[Any]:
        """Retorna os registros obtidos (após execução)"""
        return self._controller.records if hasattr(self._controller, 'records') else []

class JoinBuilder:
    """
    Builder para construir JOINs de forma fluente
    Ex: .join(outra).on(tabela.c.id == outra.c.id)
    """
    def __init__(self, select_manager: SelectManager, other_table, join_type: str):
        self.select_manager = select_manager
        self.other_table    = other_table
        self.join_type      = join_type
    
    def on(self, condition: Union[FieldCondition, BinaryExpression], columns: Optional[List[str]] = None, alias: Optional[str] = None,index_hint: Optional[str] = None) -> SelectManager:
        """
        Define a condição ON do JOIN
        Ex: .on(tabela.c.id == outra.c.id)
        """

        ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
        other_alias = alias or self.other_table.source_name
        ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
        
        on_sql, _ = condition.to_sql()
        
        self.select_manager._joins.append({
            'controller': self.other_table,
            'on':         on_sql,
            'type':       self.join_type.upper(),
            'columns':    columns,
            'alias':      other_alias,
            'index_hint': index_hint
        })
        
        return self.select_manager

''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''