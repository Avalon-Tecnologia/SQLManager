''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''

from functools import wraps
from typing    import Any, Optional, Union, Callable, List, Dict, TYPE_CHECKING

from ..BaseEnumController  import BaseEnumController
from ..EDTController       import EDTController

if TYPE_CHECKING:
    from ..TableController import TableController

class InsertRecordsetWrapper:
    """Wrapper que permite uso com ou sem .where()"""
    def __init__(self, manager):
        self._manager = manager
        self._result  = None
        
    def where(self, key_column: Union[str, EDTController, Any]) -> int:
        """Executa com filtro WHERE"""
        return self._manager.where(key_column)
    
    def __del__(self):
        """Auto-executa se não chamou .where()"""
        if self._result is None and not self._manager._executed:
            try:
                self._result = self._manager._execute_insert()
            except:
                pass  

class InsertRecordsetManager:
    """
    Gerencia operações INSERT em massa com suporte a WHERE (filtro condicional)
    """
    def __init__(self, controller: 'TableController', source_data: Union[List[tuple], List[Dict], List[Any]], columns: Optional[List[str]] = None):
        self._controller        = controller
        self._raw_data          = source_data
        self._columns           = columns
        self._source_data       = None
        self._where_condition   = None
        self._key_column        = None
        self._executed          = False
        
        self._process_data()
    
    def _process_data(self):
        """Processa os dados de entrada e extrai colunas e tuplas"""
        if not self._raw_data:
            raise Exception("Dados vazios fornecidos para insert_recordset")
        
        first_item = self._raw_data[0]
        
        if self._columns:
            self._source_data = self._raw_data
            return
        
        if isinstance(first_item, dict): #Dict            
            all_cols = list(first_item.keys())
                        
            self._columns = []
            for col in all_cols:
                has_value = any(item.get(col) is not None for item in self._raw_data)
                if has_value:
                    self._columns.append(col)
                        
            self._source_data = []
            for item in self._raw_data:
                row = tuple(item.get(col) for col in self._columns)
                self._source_data.append(row)

        elif hasattr(first_item, '__dataclass_fields__'): #dataclass            
            all_cols = list(first_item.__dataclass_fields__.keys())
                        
            self._columns = []
            for col in all_cols:
                has_value = any(getattr(item, col, None) is not None for item in self._raw_data)
                if has_value:
                    self._columns.append(col)
                        
            self._source_data = []
            for item in self._raw_data:
                row = tuple(getattr(item, col) for col in self._columns)
                self._source_data.append(row)

        elif hasattr(first_item, '__dict__'): #Objeto comum

            self._columns     = list(first_item.__dict__.keys())
            self._source_data = [tuple(getattr(item, col) for col in self._columns) for item in self._raw_data]
        else:
            raise Exception("Formato de dados não suportado. Use dict, dataclass ou tuplas com colunas definidas")
    
    def where(self, key_column: Union[str, EDTController, Any]) -> int:
        """
        Define a coluna de chave para comparação e executa (insere apenas se não existir)
        Args:
            key_column: Nome da coluna como STRING (ex: 'ITEMID')
        Returns:
            int: Número de registros inseridos
        """        
        # Sempre converter para string
        if isinstance(key_column, str):
            self._key_column = key_column.upper()
        else:
            found = False
            for attr_name in self._controller.__dict__.keys():
                if attr_name.startswith('_'):
                    continue
                try:
                    attr = getattr(self._controller, attr_name)
                    if attr is key_column:
                        self._key_column = attr_name.upper()
                        found = True
                        break
                except:
                    continue
            
            if not found:
                raise Exception(f"Erro ao identificar coluna de chave: {key_column}. Forneça o nome da coluna como string ou um campo do controller.")
        
        if not self._key_column:
            raise Exception("Coluna não identificada para comparação. Use uma string com o nome da coluna ou um campo do controller.")
            
        if self._key_column not in [col.upper() for col in self._columns]:
            raise Exception(f"Coluna '{self._key_column}' não está na lista de colunas fornecidas: {self._columns}")
                
        self._executed = True
        return self._execute_insert()
    
    def _execute_insert(self) -> int:
        """
        Executa a inserção em massa, filtrando registros existentes se WHERE foi definido
        Returns:
            int: Número de registros inseridos
        """
        validate = self._controller.validate_fields()
        if not validate['valid']:
            raise Exception(validate['error'])
        
        if not self._columns or not self._source_data:
            raise Exception("Colunas e dados são obrigatórios para insert_recordset")
        
        table_columns = self._controller.get_table_columns()
        col_names     = [col[0] for col in table_columns]
        
        for col in self._columns:
            if col.upper() not in col_names:
                raise Exception(f"Campo '{col}' não existe na tabela {self._controller.table_name}")
        
        expected_len = len(self._columns)
        for idx, row in enumerate(self._source_data):
            if len(row) != expected_len:
                raise Exception(f"Linha {idx} tem {len(row)} valores, esperado {expected_len}")
        
        try:
            with self._controller.db.transaction() as trs:                        
                # Se WHERE foi definido, usa CTE com NOT EXISTS
                if self._key_column:
                    affected_rows = self._insert_with_not_exists()
                else:
                    # Inserção normal sem filtro
                    affected_rows = self._insert_all()
                        
            return affected_rows
        except Exception as error:            
            raise Exception(f"Erro ao inserir registros em massa: {error}")
    
    def _insert_all(self) -> int:
        """Insere todos os registros sem filtro usando bulk insert otimizado"""
        placeholders = ', '.join(['?'] * len(self._columns))
        query = f"INSERT INTO {self._controller.table_name} ({', '.join(self._columns)}) VALUES ({placeholders})"
        
        with self._controller.db.transaction() as trs:
            cursor = trs.connection.cursor()
            cursor.fast_executemany = True
            cursor.executemany(query, self._source_data)
            total_inserted = cursor.rowcount if hasattr(cursor, 'rowcount') else len(self._source_data)
            cursor.close()
        
        return total_inserted
    
    def _insert_with_not_exists(self) -> int:
        """Insere apenas registros que NÃO existem usando estratégia otimizada em lotes"""
        key_idx       = [col.upper() for col in self._columns].index(self._key_column)
        input_keys    = [row[key_idx] for row in self._source_data]
        batch_size    = 5000  # Aumente conforme o banco suportar
        existing_keys = set()
        for i in range(0, len(input_keys), batch_size):
            batch_keys      = input_keys[i:i + batch_size]
            placeholders    = ', '.join(['?'] * len(batch_keys))
            check_query     = f"SELECT {self._key_column} FROM {self._controller.table_name} WHERE {self._key_column} IN ({placeholders})"
            existing_result = self._controller.db.doQuery(check_query, tuple(batch_keys))

            if existing_result:
                existing_keys.update(row[0] for row in existing_result)

        new_data = [row for row in self._source_data if row[key_idx] not in existing_keys]

        if not new_data:
            return 0
            
        placeholders = ', '.join(['?'] * len(self._columns))
        query        = f"INSERT INTO {self._controller.table_name} ({', '.join(self._columns)}) VALUES ({placeholders})"

        with self._controller.db.transaction() as trs:
            cursor = trs.connection.cursor()
            cursor.fast_executemany = True
            cursor.executemany(query, new_data)
            total_inserted = cursor.rowcount if hasattr(cursor, 'rowcount') else len(new_data)
            cursor.close()

        return total_inserted
    
    def __await__(self):
        """Permite uso com await se necessário"""
        async def _async_exec():
            return self._execute_insert()
        return _async_exec().__await__()
    
    def __int__(self):
        """Permite conversão direta para int (auto-executa se não executou ainda)"""
        if not self._executed:
            self._executed = True
            return self._execute_insert()
        return 0
    
    def __index__(self):
        """Permite uso em contextos que esperam int"""
        return self.__int__()

class InsertManager:
    """
    Gerencia operações INSERT com validação automática
    """
    
    @staticmethod
    def validate_insert(func: Callable) -> Callable:
        '''Decorator para validar operações de INSERT'''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            validate = self.validate_fields()

            if not validate['valid']:
                raise Exception(validate['error'])
            
            validate_write = self.validate_write()

            if not validate_write['valid']:
                raise Exception(validate_write['error'])
            
            return func(self, *args, **kwargs)
        return wrapper

    @validate_insert
    def insert(controller: 'TableController') -> bool:
        """
        Insere um novo registro na tabela
        Returns:
            bool: True se inserido com sucesso
        """
        # Obter colunas com DEFAULT (usando cache)
        columns_with_default = controller.get_columns_with_defaults()
        
        fields = []
        values = []
        
        for key in controller.__dict__:
            attr = controller._get_field_instance(key)
            if not (isinstance(attr, (EDTController, BaseEnumController, BaseEnumController.Enum))) or key == 'RECID':
                continue
            
            # Pular campos com DEFAULT que estão None (permite DB aplicar default)
            if key in columns_with_default and attr.value is None:
                continue
                
            fields.append(key)
            values.append(attr.value)
        
        if not fields:
            raise Exception("Nenhum campo para inserir")
        
        query = f"INSERT INTO {controller.table_name} (" + ", ".join(fields) + ") OUTPUT INSERTED.RECID VALUES (" + ", ".join(['?'] * len(fields)) + ")"
        
        try:
            with controller.db.transaction() as trs:            
                result    = controller.db.doQuery(query, tuple(values))            
                new_recid = int(result[0][0]) if result and result[0][0] else None            
            
            if new_recid is not None:
                recid_instance = controller._get_field_instance('RECID')
                results        = controller.select().where(recid_instance == new_recid).limit(1).do_update(True).execute()
            
            return True
        except Exception as error:            
            raise Exception(f"Erro ao inserir registro: {error}")
    
    def insert_recordset(controller, source_data: Union[List[tuple], List[Dict], List[Any]], columns: Optional[List[str]] = None) -> InsertRecordsetWrapper:
        """
        Insere múltiplos registros em massa (com suporte a WHERE condicional)
        Args:
            source_data: Lista de dicts, dataclasses ou tuplas
            columns: Lista de colunas (opcional, extraído automaticamente de dicts/dataclasses)
        Returns:
            InsertRecordsetWrapper: Use .where() para filtrar, ou deixe auto-executar
        """
        manager = InsertRecordsetManager(controller, source_data, columns)
        return InsertRecordsetWrapper(manager)

''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''