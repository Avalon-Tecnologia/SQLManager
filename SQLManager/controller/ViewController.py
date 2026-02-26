''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''
from typing              import Any, List, Dict, Optional, Union

from ..connection        import database_connection as data, Transaction
from .EDTController      import EDTController
from .BaseEnumController import BaseEnumController

from .managers           import *

class ViewController:
    '''
    Classe de Controle de Views do banco de dados (SQL Server).

    assim como a classe TableController, esta classe é responsável por gerenciar as operações relacionadas às views do banco de dados a consulta de views.
    '''
    _default_cache: Dict[str, set] = {}

    def __init__(self, db: Union[data, Transaction], source_name: Optional[str] = None):
        '''
        Inicializa uma instância do ViewController.
        Args:
            db: Conexão com o banco de dados ou transação.
            source_name: Nome da view a ser gerenciada (opcional).
        '''
        self.db        = db
        self.source_name = (source_name or self.__class__.__name__).upper()

        self.records:     List[Dict[str, Any]]           = []
        self.Columns:     Optional[List[List[Any]]]      = None
        self.Indexes:     Optional[List[str]]            = None
        self.ForeignKeys: Optional[List[Dict[str, Any]]] = None
        
        self._pending_wrapper = None  # Rastreia wrapper pendente de execução

        self.__select_manager = SelectManager(self) 

    def __getattribute__(self, name: str):
        '''
        Intercepta acesso aos campos:
        - Em contexto de query: retorna EDT/Enum (para operadores)
        - Em contexto normal: retorna o VALOR
        - Se houver query pendente, executa antes de retornar o campo
        '''
        protected_attrs = {
            'db', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys',
            '_where_conditions', '_columns', '_joins', '_order_by', '_limit',
            '_offset', '_group_by', '_having_conditions', '_distinct',
            'controller', '__class__', '__dict__', '_pending_wrapper',
            '__select_manager', 'field', 'select','set_current',
            'clear', 'validate_fields', 'get_table_columns', 'get_columns_with_defaults', 
            'get_table_index', 'get_table_foreign_keys', 'get_table_total', 
            'exists', '_get_field_instance', '_is_aggregate_function', '_extract_field_from_aggregate'
        }
        
        if name in protected_attrs or name.startswith('_'):
            return object.__getattribute__(self, name)
        
        # Se estiver acessando um campo e houver wrapper pendente, executa
        if not name.startswith('_'):
            pending = object.__getattribute__(self, '_pending_wrapper')
            if pending is not None:
                try:
                    pending._finalize()  # Força execução
                    object.__setattr__(self, '_pending_wrapper', None)
                except:
                    pass
        
        attr = object.__getattribute__(self, name)
        
        # Retorna métodos normalmente
        if callable(attr):
            return attr
        
        # Se é EDT/Enum, SEMPRE retorna o EDT para permitir operadores
        # O valor é acessado via .value explícito
        if isinstance(attr, (EDTController, BaseEnumController)):
            return attr
        
        return attr
  
    def __setattr__(self, name: str, value: Any):
        '''Intercepta atribuições para validar EDT/Enum'''
        if name in ('db', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys',
                    '_where_conditions', '_columns', '_joins', '_order_by', '_limit', 
                    '_offset', '_group_by', '_having_conditions', '_distinct', '_do_update',
                    'controller', '_pending_wrapper', '__select_manager'):
            object.__setattr__(self, name, value)
            return

        if hasattr(self, name):            
            attr = object.__getattribute__(self, name)
            if isinstance(attr, (EDTController, BaseEnumController)):
                if isinstance(value, EDTController):
                    attr.value = value.value
                elif isinstance(value, (BaseEnumController, BaseEnumController.Enum)):
                    if isinstance(value, BaseEnumController):
                        attr.value = value.value
                    else:
                        attr.value = value.value
                else:
                    attr.value = value
                return
        
        # Se está criando um novo EDT/Enum, armazena o nome do campo e alias da tabela nele
        if isinstance(value, (EDTController, BaseEnumController)):
            value._field_name = name
            ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
            value._table_alias = self.source_name  # Injeta o alias da tabela
            ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
        
        object.__setattr__(self, name, value)    

    def select(self) -> "SelectManager":
        # Retorna o SelectManager diretamente, sem wrapper        
        return SelectManager(self)
    
    def field(self, name: str):
        '''
        Retorna a instância EDT/Enum real de um campo (para construir queries).
        Use quando precisar construir condições WHERE.
        
        Exemplo:
            table.field('RECID') == 5  # Para queries
            table.RECID            # Para acessar valor
        '''
        return object.__getattribute__(self, name)

    def _get_field_instance(self, name: str):
        '''
        Retorna a instância EDT/Enum real de um campo (não o valor).
        Use quando precisar acessar métodos do EDT/Enum ou criar queries.
        '''
        return object.__getattribute__(self, name)
    
    def _is_aggregate_function(self, column: str) -> bool:
        '''
        Verifica se a coluna contém uma função de agregação SQL.
        Args:
            column (str): Nome da coluna ou expressão SQL
        Returns:
            bool: True se for uma função de agregação
        '''
        aggregate_functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT', 'STRING_AGG']
        column_upper = column.upper().strip()
        return any(func in column_upper for func in aggregate_functions)
    
    def _extract_field_from_aggregate(self, column: str) -> Optional[str]:
        '''
        Extrai o nome do campo de dentro de uma função de agregação.
        Ex: 'SUM(PRICE)' -> 'PRICE', 'COUNT(*)' -> 'RECID', 'COUNT(1)' -> 'RECID'
        Args:
            column (str): Expressão SQL com função de agregação
        Returns:
            Optional[str]: Nome do campo ou None se não for possível extrair
        '''
        import re
        match = re.search(r'\([\s]*([A-Za-z_][A-Za-z0-9_]*|\*|\d+)[\s]*\)', column)
        if match:
            field = match.group(1).upper()
            if field in ('*', '1'):
                return 'RECID'
            return field
        return None
    
    def get_table_columns(self) -> List[List[Any]]:
        '''
        Retorna as colunas da tabela (nome, tipo, se aceita nulo).
        Returns:
            List[List[Any]]: Lista de colunas, cada uma como [nome, tipo, is_nullable].
        '''
        if self.Columns:
            return self.Columns
        
        try:
            query = f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
            rows = self.db.doQuery(query, (self.source_name,))
            self.Columns = [[row[0], row[1], row[2]] for row in rows]
        except:
            # Fallback: usa os campos EDT/Enum da própria classe (útil para mocks)
            columns = []
            for key in self.__dict__:
                if not key.startswith('_') and key not in ('db', 'table_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 'isUpdate'):
                    attr = self._get_field_instance(key)
                    if isinstance(attr, (EDTController, BaseEnumController)):
                        # [nome, tipo genérico, nullable]
                        columns.append([key, 'nvarchar', 'YES'])
            self.Columns = columns
        
        return self.Columns
    
    def get_columns_with_defaults(self) -> set:
        '''
        Retorna conjunto de colunas que possuem DEFAULT definido no banco.
        Usa cache estático para evitar múltiplas queries.
        Returns:
            set: Conjunto com nomes das colunas que têm DEFAULT
        '''
        if self.source_name in ViewController._defaults_cache:
            return ViewController._defaults_cache[self.source_name]
        
        query = f"""
        SELECT c.name
        FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id
        WHERE t.name = ? AND c.default_object_id > 0
        """
        defaults_result      = self.db.doQuery(query, (self.source_name,))
        columns_with_default = set(row[0] for row in defaults_result) if defaults_result else set()
        
        # Cachear resultado
        ViewController._defaults_cache[self.source_name] = columns_with_default
        return columns_with_default

    def get_table_index(self) -> List[str]:
        '''
        Retorna os índices da tabela.
        Returns:
            List[str]: Lista com os nomes dos índices.
        '''
        if self.Indexes:
            return self.Indexes
        
        query = f"SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID(?)"        
        rows  = self.db.doQuery(query, (self.source_name,))

        self.Indexes = [row[0] for row in rows]

        return self.Indexes

    def get_table_foreign_keys(self) -> List[Dict[str, Any]]:
        '''
        Retorna as chaves estrangeiras relacionadas à tabela.
        Returns:
            List[Dict[str, Any]]: Lista de dicionários com informações das FKs.
        '''
        if self.ForeignKeys:
            return self.ForeignKeys
        
        query = '''
            SELECT
                fk.name AS f_key,
                tp.name AS t_origin,
                cp.name AS c_origin,
                tr.name AS t_reference,
                cr.name AS c_reference
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            WHERE tp.name = ? OR tr.name = ?
        '''
        rows = self.db.doQuery(query, (self.source_name, self.source_name))

        self.ForeignKeys = [
            {
                'f_key': row[0],
                't_origin': row[1],
                'c_origin': row[2],
                't_reference': row[3],
                'c_reference': row[4],
            } for row in rows
        ]

        return self.ForeignKeys

    def get_table_total(self) -> int:
        '''
        Retorna o total de registros atualmente carregados na instância.
        Returns:
            int: Total de registros.
        '''        
        return len(self.records)
    
    def validate_fields(self) -> Dict[str, Any]:
        '''
        Valida se os campos da instância existem na tabela.
        Returns:
            Dict[str, Any]: {'valid': True/False, 'error': mensagem}
        '''
        return self.__validate_fields()
    
    def __validate_fields(self) -> Dict[str, Any]:
        '''
        Valida se os campos da instância existem na tabela.
        Returns:
            Dict[str, Any]: {'valid': True/False, 'error': mensagem}
        '''
        ret             = {'valid': True, 'error': ''}
        instance_fields = [k for k in self.__dict__ if isinstance(self._get_field_instance(k), (EDTController, BaseEnumController, BaseEnumController.Enum))]
        table_columns   = self.get_table_columns()
        field_names     = [col[0].upper() for col in table_columns]
        invalid_fields  = [f for f in instance_fields if f.upper() not in field_names]

        if invalid_fields:
            ret = {
                'valid': False,
                'error': f"Campo(s) inválido(s) na instância: [{', '.join(invalid_fields)}] não existem na tabela [{self.source_name}]"
            }
            
        return ret

    def clear(self):
        '''
        Limpa os campos da tabela (seta todos para None/valor padrão) e limpa os registros.
        '''
        for key in self.__dict__:
            attr = self._get_field_instance(key)
            if isinstance(attr, (EDTController, BaseEnumController, BaseEnumController.Enum)):
                # Seta como None, o property .value vai retornar o padrão
                attr._value = None
        self.records = []

    def set_current(self, record):
        '''
        Preenche os campos da view com os valores do banco.
        Args:
            record (Dict[str, Any] | ViewController): Linha vinda do banco (SELECT) ou outra instância
        Returns:
            self: Instância preenchida ou None se record for None
        '''
        if record is None:
            return self
        
        if isinstance(record, ViewController):
            for key in self.__dict__:
                self_attr = self._get_field_instance(key)
                if isinstance(self_attr, (EDTController, BaseEnumController, BaseEnumController.Enum)):
                    if hasattr(record, key):
                        source_attr = record._get_field_instance(key)
                        if isinstance(source_attr, (EDTController, BaseEnumController, BaseEnumController.Enum)):
                            self_attr.value = source_attr.value
            return self
        
        # Criar mapeamento case-insensitive
        record_upper = {k.upper(): v for k, v in record.items()}    
                    
        for key in self.__dict__:
            # Pular atributos especiais
            if key.startswith('_') or key in ('db', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 'isUpdate'):
                continue
                
            attr = self._get_field_instance(key)
            if isinstance(attr, (EDTController, BaseEnumController, BaseEnumController.Enum)):
                # Busca o valor no dict com case-insensitive
                key_upper = key.upper()
                if key_upper in record_upper:
                    try:                        
                        attr.value = record_upper[key_upper]
                    except (ValueError, TypeError):
                        # Se falhar ao setar, mantém None
                        pass
        
        return self
    
''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''