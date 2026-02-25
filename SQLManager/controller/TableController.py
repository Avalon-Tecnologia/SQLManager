''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''

from __future__ import annotations
from typing              import Any, List, Dict, Optional, Union

from ..connection        import database_connection as data, Transaction
from .EDTController      import EDTController
from .BaseEnumController import BaseEnumController

class TableController():
    """
    Classe de controle de tabelas do banco de dados (SQL Server) - REFATORADA
    
    SELECT:
    - tabela.select().where(tabela.CAMPO == 5)  # Auto-executa!
    - tabela.select().where((tabela.CAMPO == 5) & (tabela.OUTRO > 10))
    - tabela.select().where(tabela.CAMPO == 5).order_by(tabela.NOME)
    - tabela.select().columns(tabela.ID, tabela.NOME).where(tabela.ATIVO == True)
    - tabela.select().where(tabela.ID > 100).limit(10)
    
    INSERT/UPDATE/DELETE em massa:
    - tabela.insert_recordset(['CAMPO1', 'CAMPO2'], [(val1, val2), (val3, val4)]).where('CAMPO1').execute()
    - tabela.update_recordset(where=tabela.CAMPO == 5, NOME='Novo', ATIVO=True)
    - tabela.delete_from().where(tabela.CAMPO < 10)  # Auto-executa!
    
    Operadores suportados: ==, !=, <, <=, >, >=, in_(), like()
    Operadores lógicos: & (AND), | (OR)
    
    IMPORTANTES:
    - USE CAMPOS (tabela.CAMPO) em vez de strings ("CAMPO") nos métodos
    - Sem .execute(): auto-executa quando a linha termina
    - Sem result =: instância é atualizada automaticamente
    - Sem .value: use tabela.CAMPO = valor (setter automático)
    
    Herda de 4 managers:
    - SelectManager: operações SELECT (auto-executa)
    - InsertManager: operações INSERT (com decorator @validate_insert)
    - UpdateManager: operações UPDATE (com decorator @validate_update)
    - DeleteManager: operações DELETE (com decorator @validate_delete)
    """
    
    # Cache estático de colunas com DEFAULT por tabela
    _defaults_cache: Dict[str, set] = {}
    
    def __init__(self, db: Union[data, Transaction], table_name: Optional[str] = None):
        '''
        Inicializa o controlador de tabela.
        Args:
            db (Union[data, Transaction]): Instância de conexão ou transação.
            table_name (str): Nome da tabela no banco de dados.
        '''
        #SelectManager.__init__(self, self)
        
        self.db         = db
        self.table_name = (table_name or self.__class__.__name__).upper()

        self.records:     List[Dict[str, Any]]           = []
        self.Columns:     Optional[List[List[Any]]]      = None
        self.Indexes:     Optional[List[str]]            = None
        self.ForeignKeys: Optional[List[Dict[str, Any]]] = None

        self.isUpdate = False
        self._pending_wrapper = None  # Rastreia wrapper pendente de execução

        from .managers import SelectManager
        self.__select_manager = SelectManager(self)

    def __getattribute__(self, name: str):
        '''
        Intercepta acesso aos campos:
        - Em contexto de query: retorna EDT/Enum (para operadores)
        - Em contexto normal: retorna o VALOR
        - Se houver query pendente, executa antes de retornar o campo
        '''
        protected_attrs = {
            'db', 'table_name', 'records', 'Columns', 'Indexes', 'ForeignKeys',
            '_where_conditions', '_columns', '_joins', '_order_by', '_limit',
            '_offset', '_group_by', '_having_conditions', '_distinct', '_do_update',
            'controller', '__class__', '__dict__', 'isUpdate', '_pending_wrapper',
            '__select_manager', 'field', 'select', 'insert', 'update', 'delete',
            'insert_recordset', 'update_recordset', 'delete_from', 'set_current',
            'clear', 'validate_fields', 'validate_write', 'get_table_columns',
            'get_columns_with_defaults', 'get_table_index', 'get_table_foreign_keys',
            'get_table_total', 'exists', '_get_field_instance', '_is_aggregate_function',
            '_extract_field_from_aggregate', 'SelectForUpdate'
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
        if name in ('db', 'table_name', 'records', 'Columns', 'Indexes', 'ForeignKeys',
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
        
        # Se está criando um novo EDT/Enum, armazena o nome do campo nele
        if isinstance(value, (EDTController, BaseEnumController)):
            value._field_name = name
        
        object.__setattr__(self, name, value)    

    def insert(self) -> bool:
        """Insere um novo registro na tabela"""
        from .managers import InsertManager
        return InsertManager.insert(self)
    
    def insert_recordset(self, source_data: Union[List[tuple], List[Dict], List[Any]], columns: Optional[List[str]] = None) -> InsertRecordsetWrapper:
        """Insere múltiplos registros em massa (auto-executa ou use .where())"""
        from .managers import InsertManager
        return InsertManager.insert_recordset(self, source_data, columns)

    def update(self) -> bool:
        """Atualiza um registro existente na tabela"""
        if(not self.isUpdate):
            raise Exception("Registro não definido para atualização.")
        
        values = [{}]
        for key in self.__dict__:
            attr = self._get_field_instance(key)
            if not (isinstance(attr, (EDTController, BaseEnumController, BaseEnumController.Enum))) or key == 'RECID':
                continue
            values[0][key] = attr.value

        from .managers import UpdateManager
        ret = UpdateManager.update(self, values)

        self.isUpdate = False

        return ret  
    
    def SelectForUpdate(self, _update: bool):
        '''Marca o Registro para ser atualizado após um select()
        Uso: table.SelectForUpdate(True) antes de fazer modificações
        '''
        self.isUpdate = _update        

    def update_recordset(self, where: Optional[Union[FieldCondition, BinaryExpression]] = None, **fields) -> int:
        """Atualiza múltiplos registros em massa"""
        from .managers import UpdateManager
        return UpdateManager.update_recordset(self, where, **fields)

    def delete(self) -> bool:
        """Exclui um registro da tabela"""
        from .managers import DeleteManager
        return DeleteManager.delete(self)
    
    def delete_from(self) -> 'DeleteRecordsetManager':
        """Deleta múltiplos registros em massa com API fluente (auto-executa ou use .where())
        
        Uso:
            # Auto-executa quando termina a linha
            table.delete_from().where(table.CAMPO == valor)
            
            # Ou armazene e execute explicitamente
            result = table.delete_from().where(table.CAMPO == valor).execute()
        
        Returns:
            DeleteRecordsetManager: Manager para construir a query de deleção
        """
        from .managers import DeleteManager
        return DeleteManager.delete_from(self)
    
    def select(self) -> "SelectManager":
        # Retorna o SelectManager diretamente, sem wrapper
        from .managers import SelectManager
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
            rows = self.db.doQuery(query, (self.table_name,))
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
        if self.table_name in TableController._defaults_cache:
            return TableController._defaults_cache[self.table_name]
        
        query = f"""
        SELECT c.name
        FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id
        WHERE t.name = ? AND c.default_object_id > 0
        """
        defaults_result      = self.db.doQuery(query, (self.table_name,))
        columns_with_default = set(row[0] for row in defaults_result) if defaults_result else set()
        
        # Cachear resultado
        TableController._defaults_cache[self.table_name] = columns_with_default
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
        rows  = self.db.doQuery(query, (self.table_name,))

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
        rows = self.db.doQuery(query, (self.table_name, self.table_name))

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

    def _check_exists(self, where: Union[FieldCondition, BinaryExpression]) -> bool:
        '''
        MÉTODO INTERNO: Verifica se existem registros (usado por decorators).
        Args:
            where: Condição WHERE usando operadores sobrecarregados
        Returns:
            bool: True se existir pelo menos um registro, False caso contrário.
        '''
        from .managers import SelectManager
        select_mgr = self.select().where(where).limit(1).do_update(False)
        select_mgr.execute()

        return len(select_mgr._last_results) > 0
    
    def exists(self, where: Union[FieldCondition, BinaryExpression]) -> bool:
        '''
        Verifica se existem registros que atendem aos critérios especificados.
        Args:
            where: Condição WHERE usando operadores sobrecarregados
                   Ex: tabela.RECID == 5
                   Ex: (tabela.CAMPO == 5) & (tabela.OUTRO > 10)
        Returns:
            bool: True se existir pelo menos um registro, False caso contrário.
        '''
        return self._check_exists(where)

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
                'error': f"Campo(s) inválido(s) na instância: [{', '.join(invalid_fields)}] não existem na tabela [{self.table_name}]"
            }
            
        return ret

    def validate_write(self) -> Dict[str, Any]:
        '''
        Validação antes do insert ou update.
        Verifica se campos obrigatórios estão preenchidos (exceto os que têm DEFAULT no banco).
        Returns:
            Dict[str, Any]: {'valid': True/False, 'error': mensagem}
        '''
        ret = {'valid': True, 'error': ''}

        columns              = self.get_table_columns()
        columns_with_default = self.get_columns_with_defaults()
        
        # Filtrar campos NOT NULL que NÃO têm DEFAULT (esses são realmente obrigatórios)
        required_fields = [
            col[0] for col in columns 
            if col[2] == 'NO' and col[0] != 'RECID' and col[0] not in columns_with_default
        ]
        
        instance_fields = {k: self._get_field_instance(k) for k in self.__dict__ if isinstance(self._get_field_instance(k), (EDTController, BaseEnumController, BaseEnumController.Enum))}
        
        # Validar apenas campos obrigatórios que NÃO têm DEFAULT
        for field in required_fields:
            if field not in instance_fields:
                ret = {'valid': False, 'error': f"Campo obrigatório '{field}' não existe na instância"}
                return ret
            attr = instance_fields[field]
            if attr.value is None or attr.value == '':
                ret = {'valid': False, 'error': f"Campo obrigatório '{field}' não pode ser vazio (campo sem DEFAULT no banco)"}
                return ret
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
        Preenche os campos da tabela com os valores do banco.
        Args:
            record (Dict[str, Any] | TableController): Linha vinda do banco (SELECT) ou outra instância
        Returns:
            self: Instância preenchida ou None se record for None
        '''
        if record is None:
            return self
        
        if isinstance(record, TableController):
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
            if key.startswith('_') or key in ('db', 'table_name', 'records', 'Columns', 'Indexes', 'ForeignKeys', 'isUpdate'):
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
    
''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''