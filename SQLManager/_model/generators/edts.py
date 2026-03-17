
"""
Por meio deste arquivo adicionar todos os EDTs (Extended Data Types) que são chaves do SQLManager, como Recid, TransDate, etc.
Esses EDTs são usados para garantir a consistência dos dados para a controladora
"""

__all__ = [
    'Ensures',
]

Ensures = {
    "Recid": '''
from SQLManager import EDTController
from model.enum import DataType

class Recid(EDTController):
    """
    Identificador numérico exclusivo.
    Args:
        value number: Identificador a ser validado
    """
    def __init__(self, value: EDTController.any_type = 0):
        super().__init__("onlyNumbers", DataType.Number, value)
''',
    "RefRecid": '''
from SQLManager import EDTController
from model.enum import DataType

class RefRecid(EDTController):
    """
    Identificador numérico exclusivo.
    Args:
        value number: Identificador a ser validado
    """
    def __init__(self, value: EDTController.any_type = 0):
        super().__init__("onlyNumbers", DataType.Number, value)
''',
    "TransDate": '''
from SQLManager import EDTController
from model.enum import DataType

class TransDate(EDTController):
    """
    Data de transação.
    Args:
        value date: Data a ser validada
    """
    def __init__(self, value: EDTController.any_type = 0):
        super().__init__("date", DataType.Date, value)
''',
    "CreateDateTime": '''
from SQLManager import EDTController
from model.enum import DataType

class CreateDateTime(EDTController):
    """
    Data de criação.
    Args:
        value datetime: Data e hora a ser validada
    """
    def __init__(self, value: EDTController.any_type = 0):
        super().__init__("datetime", DataType.DateTime, value)
''',
}