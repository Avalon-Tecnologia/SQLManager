#[BEGIN CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {03/03/2026}
from typing import Self
from .BaseEnumController import *

class NumberSequenceController:

    def __init__(self, Head, Line):
        self.Header = Head
        self.Lines  = Line
        self.limit  = 20


    def getNextNum(self, reference:int ):
        """
            Função para buscar o proximo numero da sequencia

            :param reference: O RECID para fazer a busca do próximo numero da sequencia
            :type  reference: int
        """
        if reference == 0:
            return {"message": "Reference cannot be zero"}
        
        self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).execute()
        if not self.Header.records or not self.Lines.records:
            return {"message": "Sequence not found"}
        
        pad = len(str(self.Header.MAXNUM))

        return self.formatSequence(self.Lines.records, self.Header.CURNUM.value, pad)
    
    def confirmUse(self, reference:int):
        """
            Função para confimar o uso da sequencia

            :param reference: O RECID para confirmar o uso da sequencia
            :type  reference: int
        """

        if reference == 0:
            return {"message": "Reference cannot be zero"}
        
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines).on(self.Header.RECID == self.Lines.REFRECID).order_by(self.Lines.LINENUM).execute()
            if not self.Header.records or not self.Lines.records:
                return {"message": "Sequence not found"}
            
            nextNum = self.Header.NEXTNUM.value
            self.Header.SelectForUpdate(True)

            self.Header.PREVNUM = self.Header.CURNUM.value
            self.Header.CURNUM = nextNum
            self.Header.NEXTNUM = nextNum + 1

            self.Header.update()

            return {"status": True, "message": "Sequence use confirmed"}
        except Exception as e:
            print("error: ", e)
            return {"status": False, "message": f"Unable to use due to: {e}"}

    def formatSequence(self, parts=None, number=1, padding=4):
        """
            Função para formatar a sequencia numerica

            :param parts: Dicionario com as partes em ordem da sequencia numerica
            :type parts: dict
        """
        if parts == None:
            if not self.Lines.records:
                return {"message": "Unable to find a suitable sequence to formar"}
            print("formating stored sequence")    

        parts = self.Lines.records
        ret = [""] * len(parts)
        for each in parts:
            if each["PIECETYPE"] == SequenceTypes.NUMERIC.value: 
                ret[each["LINENUM"]-1] = str(number).rjust(padding, "0")
            else:
                ret[each["LINENUM"]-1] = each["SEQPIECE"]
        
        return "".join(ret)

    def createNumberSequence(self, header:dict, lines:list):
        """
            Função para criar uma nova sequencia numerica

            header: dict
                Dicionario com os valores do cabeçalho da sequencia
                ``seqId``   : str
                    O indentificador da sequencia
                ``name``    : str
                    O nome da sequencia
                ``desc``    : str
                    A descrição da sequencia, caso necessario
                ``isdis``   : bool
                    1 caso a sequencia esteja desativado, 0 caso não esteja
                ``minnum``  : int
                    A quantidade numerica minima da sequencia
                ``maxnum``  : int
                    A quantidade numerica maxima da sequencia
            lines: list
                Lista contendo os dicionarios para as linhas que contem as partes da sequencia
                ``pieceType``: int
                    Tipo da parte da sequencia
                ``piece``: str
                    Parte da sequencia
                ``place``: int
                    Posição dentro da sequencia
                
        """
        try:
            self.Header.SEQUENCEID  = header["seqId"]
            self.Header.NAMEALIAS   = header["name"]
            self.Header.DESCRIPTION = header["desc"]
            self.Header.ISDISABLE   = header["isdis"]
            self.Header.MINNUM      = header["minnum"]
            self.Header.MAXNUM      = header["maxnum"]
            self.Header.PREVNUM     = header["minnum"] - 1
            self.Header.CURNUM      = header["minnum"]
            self.Header.NEXTNUM     = header["minnum"] + 1
            self.Header.insert()
            #self.Header.select().where(self.Header.SEQUENCEID == header["seqId"] and self.Header.NAMEALIAS == header["name"]).execute()

            for each in lines:
                self.Lines.REFRECID  = self.Header.RECID.value
                if each["pieceType"] == SequenceTypes.NUMERIC.value: #TODO: colocar o ENUM pra usar de alfaNum para poder arrumar o padding
                    self.Lines.PIECETYPE = each["pieceType"]
                    self.Lines.SEQPIECE  = None
                    self.Lines.LINENUM   = each["place"]
                else:
                    self.Lines.PIECETYPE = each["pieceType"]
                    self.Lines.SEQPIECE  = each["piece"]
                    self.Lines.LINENUM   = each["place"]
                self.Lines.insert()

            return {"status": True, "message": "Sequence created suscefully"}    
        except Exception as e:
            print("error: ", e)
            return {"status": False, "message": f"Unable to create due to: {e}"}
    
    def updateNumberSequence(self, reference:int, changes: dict):
        """
            Função para atualizar um ou mais valores de uma sequencia numerica

            :param reference: O RECID da Header que será atualizada
            :type reference: int
            :param changes: A mudanças que serão feitas, a chave deve ter o nome maiusculo. Não é recomendado fazer mudanças à ordem da sequencia.
            :param changes: dict
        """
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines, 'INNER').on(self.Header.RECID == self.Lines.REFRECID)
            if not self.Header.records or not self.Lines.records:
                return {"status": False, "message": "No sequence found"}
            
            return {"status": True, "message": "update made suscessfully"}
        except Exception as e:
            print("erro: ", e)
            return {"status": False, "message": f"Unable to update due to: {e}"}

    def deleteNumberSequence(self, reference:int):
        """
            Função para excluir a sequencia numerica 

            :param reference: A referencia da sequencia que será removida do banco de dados
            :type reference: int
        """
        if reference == 0 or not reference:
            return {"status": False, "message": "invalid reference"}
        
        try:
            self.Header.select().where(self.Header.RECID == reference).join(self.Lines, 'INNER').on(self.Header.RECID == self.Lines.REFRECID)
            if not self.Header.records or not self.Lines.records:
                return{"status": False, "message": "no sequence found"}
            
            for each in self.Lines.records:
                self.Lines.set_current(each)
                self.Lines.delete()

            self.Header.delete()
            return {"status": True, "message": "sequence deleted from database"}
        except Exception as e:
            print("erro: ", e)
            return {"status": False, "message": f"Unable to delete due to: {e}"}

    def resetNumberSequence(self):
        """
            Função para reiniciar os valores da sequencia numerica
        """
        print("placeholder")

class SequenceTypes(BaseEnumController.Enum):
    """
    Enumeração de status da inspeção (int/texto), com label descritivo.
    """
    UNDEFINED       : Self = (0, "Indefinido")
    CONSTANT        : Self = (1, "Constante")
    SEPARATOR       : Self = (2, "Separador")
    NUMERIC         : Self = (3, "Numeric")
#[END CODE] Project: SQLManager / Issue #2 / made by: {Heitor Rolim} / created: {03/03/2026}