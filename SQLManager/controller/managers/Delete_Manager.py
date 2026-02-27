''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''

from functools import wraps
from typing    import Optional, Union, Callable, TYPE_CHECKING

from ._conditions_Managers import FieldCondition, BinaryExpression

if TYPE_CHECKING:
    from ..TableController import TableController

class AutoExecuteDeleteWrapper:
    '''Wrapper para DeleteRecordsetManager que auto-executa'''
    
    def __init__(self, delete_manager):
        self._delete_manager = delete_manager
        self._executed       = False
    
    def __del__(self):
        """Auto-executa quando não há mais referência"""
        if not self._executed:
            try:
                self._delete_manager.execute()
                self._executed = True
            except:
                pass
    
    def execute(self):
        """Executa explicitamente"""
        if not self._executed:
            result = self._delete_manager.execute()
            self._executed = True
            return result
        return self._delete_manager._result_cache
    
    def __int__(self):
        """Permite conversão para int"""
        return self.execute()

class DeleteRecordsetManager:
    '''Gerencia operações DELETE em massa com API fluente - Auto-executa quando a cadeia termina'''
    
    def __init__(self, table_controller: 'TableController'):
        self._where_conditions: Optional[Union[FieldCondition, BinaryExpression]] = None

        self._controller   = table_controller        
        self._executed     = False
        self._result_cache = None
    
    def where(self, condition: Union[FieldCondition, BinaryExpression]) -> 'AutoExecuteDeleteWrapper':
        '''Adiciona condições WHERE e retorna wrapper que auto-executa'''
        self._where_conditions = condition
        return AutoExecuteDeleteWrapper(self)
    
    def execute(self) -> int:
        """Executa a operação DELETE e retorna o número de registros deletados"""
        if self._executed:
            return self._result_cache if self._result_cache is not None else 0
        
        self._executed = True
        
        validate = self._controller.validate_fields()
        if not validate['valid']:
            raise Exception(validate['error'])
        
        query = f"DELETE FROM {self._controller.table_name}"
        values = []
        
        if self._where_conditions is None:
            raise Exception("DELETE sem WHERE não é permitido. Use where=True explicitamente se desejar deletar tudo.")
        
        where_sql, where_values = self._where_conditions.to_sql()
        query += f" WHERE {where_sql}"
        values.extend(where_values if isinstance(where_values, list) else [where_values])        
                
        try:            
            with self._controller.db.transaction() as trs:            
                cursor              = trs.executeCommand(query, tuple(values))
                affected_rows       = cursor.rowcount if hasattr(cursor, 'rowcount') else 0            
                self._result_cache  = affected_rows
                return affected_rows    
        except Exception as error:            
            raise Exception(f"Erro ao deletar registros em massa: {error}")

class DeleteManager:
    """
    Gerencia operações DELETE com validação automática
    """
    
    @staticmethod
    def validate_delete(func: Callable) -> Callable:
        '''Decorator para validar operações de DELETE'''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            validate = self.validate_fields()
            if not validate['valid']:
                raise Exception(validate['error'])
            
            if not hasattr(self, 'RECID') or self._get_field_instance('RECID').value is None:
                raise Exception("Exclusão sem chave primaria, preencha o campo RECID")
            
            recid_instance = self._get_field_instance('RECID')
            if not self._check_exists(recid_instance == recid_instance.value):
                raise Exception(f"Registro com RECID {recid_instance.value} não existe na tabela {self.table_name}")
            
            return func(self, *args, **kwargs)
        return wrapper

    @validate_delete
    def delete(controller: 'TableController') -> bool:
        """
        Exclui um registro da tabela
        Returns:
            bool: True se excluído com sucesso
        """
        query = f"DELETE FROM {controller.table_name} WHERE RECID = ?"
        
        try:
            with controller.db.transaction() as trs:            
                trs.executeCommand(query, (controller._get_field_instance('RECID').value,))
        except Exception as error:
            raise Exception(f"Erro ao excluir registro: {error}")
        
        controller.clear()
        if hasattr(controller, 'RECID'):
            controller._get_field_instance('RECID').value = None
        
        return True
    
    @staticmethod
    def delete_from(controller: 'TableController') -> 'DeleteRecordsetManager':
        """
        Deleta múltiplos registros em massa com API fluente
        Uso: table.delete_from().where(table.CAMPO == valor)
        Returns:
            DeleteRecordsetManager: Manager para construir a query de deleção
        """
        return DeleteRecordsetManager(controller)

''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''