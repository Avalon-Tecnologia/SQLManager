from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ..TableController import FieldCondition


class OperationManager:
    '''
    Mixin que adiciona operadores sobrecarregados para construção de queries
    Permite usar operadores Python (==, !=, <, <=, >, >=) diretamente nos campos
    '''
    
    def _get_field_condition(self):
        '''Import lazy de FieldCondition para evitar importação circular'''
        from ..TableController import FieldCondition
        return FieldCondition
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def __eq__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        table_alias = self._get_table_alias()
        
        # Verifica se 'other' é um campo (EDT/Enum)
        field_info = self._extract_field_info(other)
        if field_info:
            # Comparação campo-com-campo (para JOINs)
            return FieldCondition(
                field_name, '=', None, 
                table_alias=table_alias,
                right_field_name=field_info['field_name'],
                right_table_alias=field_info['table_alias']
            )
        else:
            # Comparação campo-com-valor (para WHERE)
            value = self._extract_value(other)
            left_value = self.value if hasattr(self, 'value') else getattr(self, '_value', None)
            return FieldCondition(field_name, '=', value, table_alias=table_alias, left_value=left_value)
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def __ne__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        table_alias = self._get_table_alias()
        
        # Verifica se 'other' é um campo (EDT/Enum)
        field_info = self._extract_field_info(other)
        if field_info:
            return FieldCondition(
                field_name, '!=', None,
                table_alias=table_alias,
                right_field_name=field_info['field_name'],
                right_table_alias=field_info['table_alias']
            )
        else:
            value = self._extract_value(other)
            left_value = self.value if hasattr(self, 'value') else getattr(self, '_value', None)
            return FieldCondition(field_name, '!=', value, table_alias=table_alias, left_value=left_value)
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    
    def __lt__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        value = self._extract_value(other)
        return FieldCondition(field_name, '<', value)
    
    def __le__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        value = self._extract_value(other)
        return FieldCondition(field_name, '<=', value)
    
    def __gt__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        value = self._extract_value(other)
        return FieldCondition(field_name, '>', value)
    
    def __ge__(self, other) -> 'FieldCondition':
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        value = self._extract_value(other)
        return FieldCondition(field_name, '>=', value)
    
    def in_(self, values: list) -> 'FieldCondition':
        '''Operador IN para listas de valores'''
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        return FieldCondition(field_name, 'IN', values)
    
    def like(self, pattern: str) -> 'FieldCondition':
        '''Operador LIKE para pattern matching'''
        FieldCondition = self._get_field_condition()
        field_name = self._get_field_name()
        return FieldCondition(field_name, 'LIKE', pattern)
    
    def _extract_value(self, other):
        '''Extrai o valor de EDT, Enum ou retorna o valor direto'''
        from ..EDTController import EDTController
        from ..BaseEnumController import BaseEnumController, Enum
        
        if isinstance(other, EDTController):
            return other.value
        elif isinstance(other, (BaseEnumController, Enum)):
            return other.value if hasattr(other, 'value') else other._value_
        return other
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def _extract_field_info(self, other):
        '''Extrai informações do campo se other for um EDT/Enum, None caso contrário'''
        from ..EDTController import EDTController
        from ..BaseEnumController import BaseEnumController, Enum
        
        if isinstance(other, (EDTController, BaseEnumController, Enum)):
            field_name = other._get_field_name() if hasattr(other, '_get_field_name') else getattr(other, '_field_name', None)
            table_alias = other._get_table_alias() if hasattr(other, '_get_table_alias') else getattr(other, '_table_alias', None)
            if field_name:
                return {'field_name': field_name, 'table_alias': table_alias}
        return None
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    
    def _get_field_name(self) -> str:
        '''
        Retorna o nome do campo armazenado no EDT/Enum
        '''
        # O nome do campo é injetado pelo TableController.__setattr__
        if hasattr(self, '_field_name'):
            return self._field_name
        
        # Fallback: retorna um nome genérico
        return 'FIELD'
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
    def _get_table_alias(self) -> str:
        '''
        Retorna o alias da tabela associada ao campo
        '''
        if hasattr(self, '_table_alias'):
            return self._table_alias
        return None
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 26/02/2026 '''
